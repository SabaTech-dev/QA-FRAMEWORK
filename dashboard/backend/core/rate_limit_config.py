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

# Endpoint-specific rate limits (requests per minute).
# Values are matched by get_endpoint_limit(): exact match first, then
# prefix match (first hit wins), so an entry also covers its subpaths.
ENDPOINT_LIMITS: Dict[str, int] = {
    "/api/v1/auth/login": 20,  # Prevent brute force
    "/api/v1/auth/register": 10,
    "/api/v1/executions": 60,  # Expensive operation
    "/api/v1/billing/webhook": 1_000,  # Stripe webhooks
    # F-6 (card 044bde0e): expensive routes need their own ceiling below the
    # plan burst (post-mortem lesson: adaptive attackers target costly paths).
    "/api/v1/browser-use/execute": 10,  # Spawns LLM+browser task (browser_use_routes.py)
    "/api/v1/suites/bulk": 20,  # Prefix: bulk-delete/bulk-execute/bulk-archive (bulk_routes.py)
    "/api/v1/search": 30,  # Prefix: global search + /suggestions (search.py)
    "/api/v1/analytics": 30,  # Prefix: dashboard/users/tests/revenue/features/export (analytics_routes.py)
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


def get_endpoint_limit(endpoint: str) -> int:
    """
    Get endpoint-specific rate limit

    Args:
        endpoint: API endpoint path

    Returns:
        Rate limit (requests per minute) or None
    """
    # Check exact match
    if endpoint in ENDPOINT_LIMITS:
        return ENDPOINT_LIMITS[endpoint]

    # Check prefix match
    for pattern, limit in ENDPOINT_LIMITS.items():
        if endpoint.startswith(pattern):
            return limit

    return None


def get_all_limits() -> Dict[str, any]:
    """Get all rate limit configuration"""
    return {
        "plans": {
            plan.value: {"hourly_limit": RATE_LIMITS[plan], "burst_limit": BURST_LIMITS[plan]}
            for plan in PlanType
        },
        "endpoints": ENDPOINT_LIMITS,
    }
