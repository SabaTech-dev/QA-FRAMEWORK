"""Security primitives for the accuracy_testing API (card c9825844).

Implements the two wiring contracts:

- L-1 (salt per-tenant): ``derive_tenant_salt`` derives a server-side,
  tenant-scoped split salt via HMAC-SHA256. The salt is never transmitted
  to clients and never client-chosen. Rotating ``split_secret`` changes
  holdout membership platform-wide — rotate only with that caveat in mind.
- L-2 (principal): ``AccuracyPrincipal`` carries the requesting owner and
  admin flag. Owner-scoping mirrors the QAVisualPrincipal pattern from
  PR #118 (pattern reused, code independent).
"""

from __future__ import annotations

import hashlib
import hmac

from pydantic import BaseModel


class AccuracyPrincipal(BaseModel):
    """Authenticated caller of the accuracy API (owner + role)."""

    owner: str
    is_admin: bool = False


def derive_tenant_salt(split_secret: str, tenant_id: str) -> str:
    """Derive a deterministic per-tenant split salt (L-1).

    HMAC ensures tenants cannot infer each other's holdout membership even
    though membership is a deterministic function of the salt: without the
    server secret the salt cannot be recomputed.

    Args:
        split_secret: platform-side secret (env ``ACCURACY_SPLIT_SECRET``).
        tenant_id: identity of the owning tenant.

    Returns:
        Hex digest used as the ``SplitPolicy.salt`` namespace.
    """
    if not split_secret or not split_secret.strip():
        raise ValueError("split_secret must be a non-empty server-side secret")
    if not tenant_id or not tenant_id.strip():
        raise ValueError("tenant_id must be a non-empty tenant identifier")
    return hmac.new(
        split_secret.encode("utf-8"),
        tenant_id.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
