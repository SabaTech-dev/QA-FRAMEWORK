"""
Tests for card 5025917d: XFF spoofing + ZSET cardinality caps.

Advisory e8a6b3a7 follow-up (review of f7ec83f):
- A) _ip_identity must NOT trust raw X-Forwarded-For: bucket keys derived
  from a client-controlled header let an attacker mint unlimited rate-limit
  buckets (and unbounded Redis key cardinality) by rotating the header.
- B) Rate-limit ZSET keys must have bounded cardinality: endpoint:* keys
  are built from the matched RULE pattern (not the raw request path), so
  path junk under a prefix-matched rule cannot mint new buckets either.

Decision under test (A): the client IP is derived hop-by-hop ONLY when the
direct TCP peer is a configured trusted proxy (TRUSTED_PROXIES env,
IPs/CIDRs). For any other peer the XFF header is ignored entirely. Behind a
trusted proxy we walk XFF right-to-left (the right side is appended by our
own proxies), skipping trusted hops and junk, and take the first valid
non-trusted IP. Invariant: trusted proxies MUST append the real client IP
(nginx $remote_addr, cf. card 215398dd).
"""

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("redis")
pytest.importorskip("asyncpg")
from unittest.mock import Mock, AsyncMock, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from middleware.rate_limit import RateLimiter, RateLimitMiddleware


def _request(xff=None, peer="203.0.113.9"):
    """Minimal Request stand-in for _ip_identity (headers + client.host)"""
    request = MagicMock()
    request.headers = {"X-Forwarded-For": xff} if xff is not None else {}
    request.client.host = peer
    return request


def _mw(trusted=None):
    kwargs = {"app": Mock(), "rate_limiter": Mock()}
    if trusted is not None:
        kwargs["trusted_proxies"] = trusted
    return RateLimitMiddleware(**kwargs)


class TestXffNotTrustedByDefault:
    """No trusted proxies configured -> XFF is never consulted"""

    def test_no_trust_config_ignores_xff(self):
        mw = _mw()
        assert mw._ip_identity(_request(xff="1.2.3.4")) == "ip:203.0.113.9"

    def test_untrusted_peer_ignores_xff(self):
        mw = _mw(trusted="10.0.0.1")
        req = _request(xff="1.2.3.4", peer="203.0.113.9")
        assert mw._ip_identity(req) == "ip:203.0.113.9"


class TestXffTrustedProxyDerivation:
    def test_peer_trusted_uses_rightmost_hop(self):
        """Single proxy: rightmost XFF hop is the proxy-appended real IP"""
        mw = _mw(trusted="10.0.0.1")
        req = _request(xff="1.2.3.4, 5.6.7.8", peer="10.0.0.1")
        assert mw._ip_identity(req) == "ip:5.6.7.8"

    def test_walk_skips_trusted_hops_right_to_left(self):
        """Proxy chains: trusted hops (added by our own infra) are skipped"""
        mw = _mw(trusted="10.0.0.0/8")
        req = _request(xff="9.9.9.9, 10.0.0.5", peer="10.0.0.1")
        assert mw._ip_identity(req) == "ip:9.9.9.9"

    def test_junk_hops_are_skipped(self):
        """Client-injected junk left of the proxy-appended chain is noise"""
        mw = _mw(trusted="10.0.0.1")
        req = _request(xff="evil-junk, 5.6.7.8", peer="10.0.0.1")
        assert mw._ip_identity(req) == "ip:5.6.7.8"

    def test_cidr_trusted_proxy(self):
        mw = _mw(trusted="192.168.0.0/16")
        req = _request(xff="8.8.8.8", peer="192.168.5.5")
        assert mw._ip_identity(req) == "ip:8.8.8.8"

    def test_all_hops_trusted_falls_back_to_peer(self):
        mw = _mw(trusted="10.0.0.0/8")
        req = _request(xff="10.0.0.5, 10.0.0.6", peer="10.0.0.1")
        assert mw._ip_identity(req) == "ip:10.0.0.1"

    def test_empty_xff_trusted_peer_uses_peer(self):
        mw = _mw(trusted="10.0.0.1")
        assert mw._ip_identity(_request(peer="10.0.0.1")) == "ip:10.0.0.1"

    def test_xff_junk_only_falls_back_to_peer(self):
        """Bounded fallback: junk-only XFF cannot mint new identifiers"""
        mw = _mw(trusted="10.0.0.1")
        req = _request(xff="garbage-value", peer="10.0.0.1")
        assert mw._ip_identity(req) == "ip:10.0.0.1"


class TestXffRotationCannotMintBuckets:
    """The exact attack from the advisory, end to end through dispatch"""

    def test_rotated_xff_maps_to_single_identity(self):
        limiter = Mock()
        limiter.is_allowed = AsyncMock(
            return_value=(True, {"limit": 100, "remaining": 99, "reset": 0})
        )
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware, rate_limiter=limiter)

        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        client = TestClient(app)
        for xff in ("1.1.1.1", "2.2.2.2", "3.3.3.3", "<script>", "junk-xyz"):
            client.get("/test", headers={"X-Forwarded-For": xff})

        identifiers = {call.kwargs["identifier"] for call in limiter.is_allowed.await_args_list}
        # testclient is not a trusted proxy -> every rotated request buckets
        # on the SAME peer identity, so limits apply and 429 arrives.
        assert identifiers == {"ip:testclient"}


class TestEndpointKeyUsesRulePattern:
    """
    B) endpoint:* keys must be keyed by the matched RULE pattern, not the
    raw request path: get_endpoint_limit prefix-matches, so the key must
    not embed attacker-controlled path junk.
    """

    @pytest.mark.asyncio
    async def test_path_junk_shares_one_endpoint_key(self):
        redis = AsyncMock()
        redis.eval = AsyncMock(return_value=[0, 100, 99, 9999999])
        limiter = RateLimiter(redis_client=redis)

        await limiter.is_allowed(
            identifier="ip:1.2.3.4", plan="free", endpoint="/api/v1/executions/junk-AAA"
        )
        keys_a = redis.eval.await_args.args[2:5]

        await limiter.is_allowed(
            identifier="ip:1.2.3.4", plan="free", endpoint="/api/v1/executions/junk-BBB"
        )
        keys_b = redis.eval.await_args.args[2:5]

        assert keys_a == keys_b
        assert any(k == "ratelimit:endpoint:ip:1.2.3.4:/api/v1/executions" for k in keys_a)
        assert not any("junk" in k for k in keys_a)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
