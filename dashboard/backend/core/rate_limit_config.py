"""
Rate Limit Configuration

Defines rate limits per plan and endpoint
"""

from typing import Dict, List
from enum import Enum


class PlanType(str, Enum):
    """Subscription plan types"""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


# Rate limits per plan (requests per hour)
RATE_LIMITS: Dict[PlanType, int] = {
    PlanType.FREE: 100,
    PlanType.PRO: 1_000,
    PlanType.ENTERPRISE: 10_000,
}

# Safety net for member cardinality per bucket (card 5025917d). Highest
# legit plan limit is 10k/hour; anything above this gets trimmed by
# ZREMRANGEBYRANK inside the atomic Lua script.
MAX_BUCKET_MEMBERS = 10_000


def validate_bucket_cap(max_bucket_members: int) -> None:
    """
    W1 guard (card 5025917d, review iteration 1), runs at import/boot.

    A bucket cap below the largest configured hourly limit would trim a
    bucket before a legitimate client can reach its plan limit, silently
    breaking the plan contract — fail fast instead.
    """
    largest = max(RATE_LIMITS.values())
    if max_bucket_members < largest:
        raise ValueError(
            f"MAX_BUCKET_MEMBERS ({max_bucket_members}) must be >= the largest "
            f"configured RATE_LIMITS value ({largest}): a smaller cap trims "
            "rate-limit buckets before a client can reach its plan limit."
        )


validate_bucket_cap(MAX_BUCKET_MEMBERS)

# Endpoint-specific rate limits (requests per minute)
ENDPOINT_LIMITS: Dict[str, int] = {
    "/api/v1/auth/login": 20,  # Prevent brute force
    "/api/v1/auth/register": 10,
    "/api/v1/executions": 60,  # Expensive operation
    "/api/v1/billing/webhook": 1_000,  # Stripe webhooks
}

# Burst limits (requests per minute)
BURST_LIMITS: Dict[PlanType, int] = {
    PlanType.FREE: 20,
    PlanType.PRO: 100,
    PlanType.ENTERPRISE: 500,
}


def get_rate_limit(plan: str) -> int:
    """
    Get rate limit for a plan

    Args:
        plan: Plan name

    Returns:
        Rate limit (requests per hour)
    """
    try:
        plan_type = PlanType(plan.lower())
        return RATE_LIMITS.get(plan_type, RATE_LIMITS[PlanType.FREE])
    except ValueError:
        return RATE_LIMITS[PlanType.FREE]


def get_burst_limit(plan: str) -> int:
    """
    Get burst limit for a plan

    Args:
        plan: Plan name

    Returns:
        Burst limit (requests per minute)
    """
    try:
        plan_type = PlanType(plan.lower())
        return BURST_LIMITS.get(plan_type, BURST_LIMITS[PlanType.FREE])
    except ValueError:
        return BURST_LIMITS[PlanType.FREE]


def get_endpoint_rule(endpoint: str):
    """
    Get the matching endpoint rule: (pattern, limit) or None.

    The PATTERN (config key), not the raw request path, is what rate-limit
    bucket keys must be built from: rules prefix-match, so keying on the
    raw path would let attacker-controlled path junk mint one bucket per
    request (card 5025917d, unbounded ZSET cardinality).
    """
    # Check exact match
    if endpoint in ENDPOINT_LIMITS:
        return endpoint, ENDPOINT_LIMITS[endpoint]

    # Check prefix match
    for pattern, limit in ENDPOINT_LIMITS.items():
        if endpoint.startswith(pattern):
            return pattern, limit

    return None


def get_endpoint_limit(endpoint: str) -> int:
    """
    Get endpoint-specific rate limit (requests per minute) or None
    """
    rule = get_endpoint_rule(endpoint)
    return rule[1] if rule else None


def get_all_limits() -> Dict[str, any]:
    """Get all rate limit configuration"""
    return {
        "plans": {
            plan.value: {"hourly_limit": RATE_LIMITS[plan], "burst_limit": BURST_LIMITS[plan]}
            for plan in PlanType
        },
        "endpoints": ENDPOINT_LIMITS,
    }
