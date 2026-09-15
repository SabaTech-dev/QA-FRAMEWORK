"""
W1 guard (card 5025917d, review iteration 1).

MAX_BUCKET_MEMBERS is the ZREMRANGEBYRANK trim cap per rate-limit bucket.
If it were configured BELOW the largest hourly limit in RATE_LIMITS, a
legitimate client could never reach its plan limit: the bucket gets
trimmed first. The guard in core.rate_limit_config.py fails fast at
import/boot with a clear ValueError instead of silently breaking the
plan contract.
"""

import pytest

from core.rate_limit_config import MAX_BUCKET_MEMBERS, RATE_LIMITS, validate_bucket_cap


def test_bucket_cap_covers_largest_plan_limit():
    # Shipped config satisfies the invariant (module import would have
    # raised ValueError otherwise, so reaching here is already proof).
    assert MAX_BUCKET_MEMBERS >= max(RATE_LIMITS.values())

    # A cap below the largest configured limit must fail fast.
    with pytest.raises(ValueError, match="MAX_BUCKET_MEMBERS"):
        validate_bucket_cap(max(RATE_LIMITS.values()) - 1)
