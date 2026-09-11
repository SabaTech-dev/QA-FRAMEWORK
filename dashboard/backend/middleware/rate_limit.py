"""
Rate Limiting Middleware

Implements granular rate limiting:
- Per-plan limits (Free: 100/hr, Pro: 1,000/hr, Enterprise: 10,000/hr)
- Per-endpoint limits (login: 20/min, executions: 60/min)
- Burst protection
- Redis-backed for distributed rate limiting

card e8a6b3a7:
- F-1: this middleware runs PRE-auth (Starlette order: the LAST
  add_middleware runs FIRST, so request.state.user never exists here).
  Identity/plan are extracted by decoding the JWT directly (light decode,
  no DB), falling back to ip:* for anonymous requests.
- F-3: all tier checks run in ONE atomic Lua script (previously up to ~12
  non-atomic Redis round-trips per request), and Redis failure fails
  CLOSED for anonymous requests (fail-open only for authenticated users).

card 5025917d (advisory e8a6b3a7 follow-up):
- XFF spoofing: the bucket identity NEVER trusts raw X-Forwarded-For.
  Client IP is derived from XFF only when the direct TCP peer is a
  configured trusted proxy (settings.trusted_proxies, IPs/CIDRs), walking
  the header right-to-left (the right side is appended by our own
  proxies; invariant: trusted proxies append the real client IP — nginx
  $remote_addr, cf. card 215398dd). Any other peer is bucketed by its
  socket address, so rotating XFF cannot mint fresh buckets.
- ZSET cardinality caps: endpoint:* keys are keyed by the matched RULE
  pattern (not the raw path, which prefix-matches attacker junk), and
  every bucket has a hard member cap (ZREMRANGEBYRANK trim inside the
  atomic script) so no bucket can grow without limit even if a plan limit
  is misconfigured huge.
"""

import ipaddress
import time
from uuid import uuid4
from typing import Optional, Callable
from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from jose import jwt as jose_jwt
import structlog

from config import settings
from core.rate_limit_config import (
    get_rate_limit,
    get_burst_limit,
    get_endpoint_rule,
    MAX_BUCKET_MEMBERS,
)
from services.auth_service import ACCESS_TOKEN_TYPES
from services.cache_service import get_redis_client

logger = structlog.get_logger()

# Atomic sliding-window check across all tiers in a single round-trip.
# ARGV layout: [limit_1, window_1, now, limit_2, window_2, now, ..., nonce,
#               max_bucket_members]
# Returns: {denied_index (0=allowed), limit, remaining, reset} of the
# failing check, or of the last (hourly) check when allowed.
_SLIDING_WINDOW_LUA = """
local denied = 0
local counts = {}
for i = 1, #KEYS do
    local key = KEYS[i]
    local limit = tonumber(ARGV[i * 3 - 2])
    local window = tonumber(ARGV[i * 3 - 1])
    local now = tonumber(ARGV[i * 3])
    redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
    local count = redis.call('ZCARD', key)
    counts[i] = count
    if count >= limit and denied == 0 then
        denied = i
    end
end
if denied == 0 then
    local nonce = ARGV[#KEYS * 3 + 1]
    local cap = tonumber(ARGV[#KEYS * 3 + 2])
    for i = 1, #KEYS do
        local key = KEYS[i]
        local window = tonumber(ARGV[i * 3 - 1])
        local now = tonumber(ARGV[i * 3])
        redis.call('ZADD', key, now, nonce .. ':' .. i)
        -- Hard member cap: keep the newest `cap` members only, so a
        -- misconfigured huge limit cannot grow a bucket unbounded.
        redis.call('ZREMRANGEBYRANK', key, 0, -(cap + 1))
        redis.call('EXPIRE', key, window)
    end
end
local idx = denied
if idx == 0 then idx = #KEYS end
local limit = tonumber(ARGV[idx * 3 - 2])
local window = tonumber(ARGV[idx * 3 - 1])
local now = tonumber(ARGV[idx * 3])
local used = counts[idx]
if denied == 0 then used = used + 1 end
return {denied, limit, math.max(0, limit - used), math.floor(now + window)}
"""

# MAX_BUCKET_MEMBERS lives in core.rate_limit_config.py next to the limits
# it must cover (W1 guard validates it at import/boot).


class RateLimiter:
    """
    Redis-backed rate limiter with sliding window algorithm

    All tiers (endpoint / burst / hourly) are checked and incremented
    atomically by a single Lua script per request.
    """

    def __init__(self, redis_client=None, max_bucket_members: int = MAX_BUCKET_MEMBERS):
        self.redis = redis_client or get_redis_client()
        self.prefix = "ratelimit:"
        self.max_bucket_members = max(1, max_bucket_members)

    async def is_allowed(
        self,
        identifier: str,
        plan: str,
        endpoint: str,
        authenticated: bool = False,
    ) -> tuple[bool, dict]:
        """
        Check if request is allowed

        Args:
            identifier: Unique identifier (user:{sub} or ip:{addr})
            plan: User's subscription plan
            endpoint: API endpoint path
            authenticated: whether the request carries a valid access JWT.
                On Redis failure, authenticated requests degrade to
                fail-open; anonymous ones fail CLOSED (F-3).
        """
        checks = []  # (key, limit, window_seconds)
        rule = get_endpoint_rule(endpoint)
        if rule:
            pattern, endpoint_limit = rule
            checks.append(
                (
                    # Key by the RULE pattern, never the raw path: rules
                    # prefix-match, so raw-path keys would let path junk
                    # mint one bucket per request (card 5025917d).
                    f"{self.prefix}endpoint:{identifier}:{pattern}",
                    endpoint_limit,
                    60,
                )
            )
        checks.append(
            (
                f"{self.prefix}burst:{identifier}",
                get_burst_limit(plan),
                60,
            )
        )
        checks.append(
            (
                f"{self.prefix}hourly:{identifier}",
                get_rate_limit(plan),
                3600,
            )
        )

        now = time.time()
        keys = [c[0] for c in checks]
        args: list = []
        for _, limit, window in checks:
            args.extend([limit, window, now])
        args.append(uuid4().hex)  # unique member nonce: same-timestamp requests must not collide
        args.append(self.max_bucket_members)  # hard per-bucket member cap (card 5025917d)

        try:
            res = await self.redis.eval(_SLIDING_WINDOW_LUA, len(keys), *(keys + args))
        except Exception as e:
            logger.error("Rate limit check failed", error=str(e), identifier=identifier)
            if authenticated:
                # Degraded mode: never lock out authenticated users
                return True, {"limit": 0, "remaining": 0, "reset": 0, "error": str(e)}
            # F-3: fail CLOSED for anonymous traffic when Redis is down.
            # Flagged so the middleware answers 503 (outage), not 429 (abuse).
            return False, {
                "limit": 0,
                "remaining": 0,
                "reset": 0,
                "redis_outage": True,
                "error": str(e),
            }

        denied, limit, remaining, reset = (int(res[0]), int(res[1]), int(res[2]), int(res[3]))
        return denied == 0, {
            "limit": limit,
            "remaining": remaining,
            "reset": reset,
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI

    Usage:
        app.add_middleware(RateLimitMiddleware)
    """

    def __init__(
        self,
        app,
        rate_limiter: Optional[RateLimiter] = None,
        trusted_proxies: Optional[str] = None,
    ):
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimiter()

        # Trusted reverse proxies (IPs/CIDRs, comma-separated). Default:
        # none -> X-Forwarded-For is never trusted (card 5025917d).
        trusted = (
            trusted_proxies
            if trusted_proxies is not None
            else (getattr(settings, "trusted_proxies", "") or "")
        )
        self._trusted_networks = self._parse_trusted_proxies(trusted)

        # Paths to skip rate limiting.
        # NOTE (card f90a8079): FastAPI redirect_slashes 307-redirects /metrics to
        # /metrics/, so this middleware sees the TRAILING-SLASH variant. Compare
        # with trailing slashes stripped on BOTH sides; the request path itself
        # is never mutated.
        self.skip_paths = {
            "/metrics",
            "/health",
            "/api/v1/health",
            "/docs",
            "/redoc",
            "/openapi.json",
        }
        self._skip_paths_norm = {p.rstrip("/") for p in self.skip_paths}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting"""

        # Skip rate limiting for certain paths (trailing-slash tolerant)
        if request.url.path.rstrip("/") in self._skip_paths_norm:
            return await call_next(request)

        # CORS preflight must never consume rate-limit budget (a 429 on
        # OPTIONS breaks the app in the browser; login at 20/min would
        # otherwise cost ~2 requests per attempt)
        if request.method == "OPTIONS":
            return await call_next(request)

        identifier, plan, authenticated = self._get_identity(request)

        is_allowed, rate_info = await self.rate_limiter.is_allowed(
            identifier=identifier,
            plan=plan,
            endpoint=request.url.path,
            authenticated=authenticated,
        )

        # Add rate limit headers
        headers = {
            "X-RateLimit-Limit": str(rate_info.get("limit", 0)),
            "X-RateLimit-Remaining": str(rate_info.get("remaining", 0)),
            "X-RateLimit-Reset": str(rate_info.get("reset", 0)),
        }

        if not is_allowed:
            # Redis outage (fail-closed anonymous): honest 503 with a
            # generic body — never claim "rate limit exceeded" (limit=0)
            # for an infrastructure failure, and never leak the error.
            if rate_info.get("redis_outage"):
                logger.error(
                    "Rate limiter Redis outage: failing closed for anonymous",
                    identifier=identifier,
                    endpoint=request.url.path,
                )
                return JSONResponse(
                    status_code=503,
                    content={"detail": "Service temporarily unavailable"},
                    headers={"Retry-After": "30"},
                )

            # Rate limit exceeded
            logger.warning(
                "Rate limit exceeded",
                identifier=identifier,
                endpoint=request.url.path,
                limit=rate_info.get("limit"),
            )

            reset = rate_info.get("reset", 0)
            headers["Retry-After"] = str(max(1, int(reset - time.time())))

            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "limit": rate_info.get("limit"),
                    "reset": rate_info.get("reset"),
                },
                headers=headers,
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        for key, value in headers.items():
            response.headers[key] = value

        return response

    def _get_identity(self, request: Request) -> tuple[str, str, bool]:
        """
        F-1: this middleware runs PRE-auth, so request.state.user is never
        set here. Decode the access JWT lightly (no DB): valid token ->
        (user:{sub}, token plan claim, True); otherwise -> (ip:{addr},
        free, False).
        """
        auth = request.headers.get("Authorization") or ""
        if auth.startswith("Bearer "):
            try:
                payload = jose_jwt.decode(
                    auth[len("Bearer ") :],
                    settings.secret_key.get_secret_value(),
                    algorithms=[settings.algorithm],
                )
                sub = payload.get("sub")
                if sub and payload.get("type") in ACCESS_TOKEN_TYPES:
                    plan = payload.get("plan") or "free"
                    return f"user:{sub}", plan, True
            except Exception:
                pass  # invalid/expired token -> treat as anonymous
        return self._ip_identity(request), "free", False

    @staticmethod
    def _parse_trusted_proxies(trusted_proxies: str) -> list:
        """Parse comma-separated IPs/CIDRs; unparseable entries are skipped
        (fail-closed: a bad config never widens trust)."""
        networks = []
        for entry in trusted_proxies.split(","):
            entry = entry.strip()
            if not entry:
                continue
            try:
                networks.append(ipaddress.ip_network(entry, strict=False))
            except ValueError:
                logger.warning("Invalid trusted proxy entry ignored", entry=entry)
        return networks

    def _addr_is_trusted(self, addr) -> bool:
        return any(addr in net for net in self._trusted_networks)

    def _ip_identity(self, request: Request) -> str:
        """
        Card 5025917d: derive the bucket IP WITHOUT trusting raw XFF.

        - Direct peer not in trusted_proxies -> use the socket address and
          IGNORE X-Forwarded-For entirely (it is attacker-controlled).
        - Peer is a trusted proxy -> walk XFF right-to-left (hops on the
          right are appended by our own proxies; the left side is
          client-controlled noise). Skip junk entries and trusted hops;
          the first valid non-trusted IP is the real client. Invariant:
          trusted proxies must append the real client IP (nginx
          $remote_addr, cf. card 215398dd).
        - Fallback (no XFF, all hops trusted, or junk-only) -> the peer.
        """
        peer = request.client.host if request.client else "unknown"
        try:
            peer_addr = ipaddress.ip_address(peer)
        except ValueError:
            peer_addr = None
        if peer_addr is None or not self._addr_is_trusted(peer_addr):
            return f"ip:{peer}"

        forwarded = request.headers.get("X-Forwarded-For") or ""
        for hop in reversed(forwarded.split(",")):
            hop = hop.strip()
            if not hop:
                continue
            try:
                addr = ipaddress.ip_address(hop)
            except ValueError:
                continue  # client-injected junk, left of the appended chain
            if not self._addr_is_trusted(addr):
                # str(addr) canonicalizes: textual IPv6 variants of the
                # same address ("2001:db8::1" vs "2001:0db8::1") must not
                # mint distinct buckets (S1, card 5025917d review iter 1).
                return f"ip:{str(addr)}"
        return f"ip:{peer}"


# Dependency for manual rate limiting
async def check_rate_limit(request: Request, plan: str = "free"):
    """
    Dependency to check rate limit manually

    Usage:
        @router.get("/endpoint")
        async def endpoint(request: Request, _: None = Depends(check_rate_limit)):
            ...
    """
    limiter = RateLimiter()
    identifier = (
        f"user:{request.state.user.id}"
        if hasattr(request.state, "user")
        else f"ip:{request.client.host}"
    )

    is_allowed, rate_info = await limiter.is_allowed(
        identifier=identifier, plan=plan, endpoint=request.url.path
    )

    if not is_allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Rate limit exceeded",
                "limit": rate_info.get("limit"),
                "reset": rate_info.get("reset"),
            },
        )

    return rate_info
