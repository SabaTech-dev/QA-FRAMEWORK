"""Redis-backed state for refresh token rotation and reuse detection.

Self-contained module (no repo-level config dependencies) so it can be
vendored verbatim into the dashboard backend build context, mirroring the
``qa_visual`` vendor pattern.
"""

from .store import DEFAULT_PREFIX, RefreshTokenStore, TokenStoreUnavailableError

__all__ = [
    "DEFAULT_PREFIX",
    "RefreshTokenStore",
    "TokenStoreUnavailableError",
]
