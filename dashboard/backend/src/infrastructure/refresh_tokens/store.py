"""Redis-backed refresh token store (card 3ae2e5c1, finding F-2, OWASP API2).

Holds the server-side state required for secure refresh token rotation:

- **jti denylist**: every consumed refresh token is denied by its unique
  ``jti`` until the token itself would have expired (TTL = remaining
  lifetime), so replaying a rotated token is detected and rejected.
- **family tombstones**: when reuse is detected the whole token family is
  revoked, killing every descendant minted by later rotations.

The store is deliberately dependency-light: a Redis client is either
injected (tests, alternate wiring) or lazily created from a URL. It never
reads configuration itself, so no credentials can be hardcoded here and
each deployment decides where the connection details come from.

All Redis failures surface as :class:`TokenStoreUnavailableError` so
callers can fail closed (refuse the refresh) instead of accidentally
accepting a token whose denylist could not be checked.
"""

from redis import asyncio as aioredis
from redis.exceptions import RedisError

DEFAULT_PREFIX = "qa:auth:rt"


class TokenStoreUnavailableError(RuntimeError):
    """The token store (Redis) is unreachable or failed mid-operation."""


class RefreshTokenStore:
    """Denylist + family-revocation store for rotating refresh tokens."""

    def __init__(
        self,
        client: "aioredis.Redis | None" = None,
        url: str | None = None,
        prefix: str = DEFAULT_PREFIX,
    ) -> None:
        if client is None and url is None:
            raise ValueError("either a redis client or a redis url is required")
        if client is None:
            assert url is not None  # narrowed by the check above
            client = aioredis.from_url(url)
        self.client = client
        self.prefix = prefix

    def _jti_key(self, jti: str) -> str:
        return f"{self.prefix}:jti:{jti}"

    def _fam_key(self, family_id: str) -> str:
        return f"{self.prefix}:fam:{family_id}"

    async def deny_jti(self, jti: str, ttl_seconds: int) -> None:
        """Deny a refresh token by ``jti`` until its own expiry passes."""
        ttl = max(1, int(ttl_seconds))
        try:
            await self.client.setex(self._jti_key(jti), ttl, "1")
        except RedisError as exc:
            raise TokenStoreUnavailableError(f"redis setex failed: {exc}") from exc

    async def try_consume_jti(self, jti: str, ttl_seconds: int) -> bool:
        """Atomically deny ``jti`` unless it was already consumed.

        Returns True when this call consumed the token (first use) and
        False when the jti was already denied (replay). The SET-NX-EX
        round-trip makes the check-and-deny step atomic, closing the
        race where two concurrent refreshes with the same token both
        pass a separate exists() check and both rotate.
        """
        ttl = max(1, int(ttl_seconds))
        try:
            was_set = await self.client.set(self._jti_key(jti), "1", ex=ttl, nx=True)
        except RedisError as exc:
            raise TokenStoreUnavailableError(f"redis set(nx) failed: {exc}") from exc
        return bool(was_set)

    async def is_denied(self, jti: str) -> bool:
        try:
            return bool(await self.client.exists(self._jti_key(jti)))
        except RedisError as exc:
            raise TokenStoreUnavailableError(f"redis exists failed: {exc}") from exc

    async def revoke_family(self, family_id: str, ttl_seconds: int) -> None:
        """Tombstone a token family; every member is rejected afterwards.

        The TTL bounds the tombstone to the maximum possible refresh token
        lifetime so the key self-cleans once the family could no longer be
        alive anyway.
        """
        ttl = max(1, int(ttl_seconds))
        try:
            await self.client.setex(self._fam_key(family_id), ttl, "1")
        except RedisError as exc:
            raise TokenStoreUnavailableError(f"redis setex failed: {exc}") from exc

    async def is_family_revoked(self, family_id: str) -> bool:
        try:
            return bool(await self.client.exists(self._fam_key(family_id)))
        except RedisError as exc:
            raise TokenStoreUnavailableError(f"redis exists failed: {exc}") from exc

    async def ping(self) -> bool:
        try:
            return bool(await self.client.ping())
        except RedisError as exc:
            raise TokenStoreUnavailableError(f"redis ping failed: {exc}") from exc

    async def aclose(self) -> None:
        try:
            await self.client.aclose()
        except AttributeError:
            # Older redis-py versions name the close method differently.
            close = getattr(self.client, "close", None)
            if close is not None:
                result = close()
                if result is not None and hasattr(result, "__await__"):
                    await result
        except RedisError:
            pass
