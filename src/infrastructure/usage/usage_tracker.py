"""
Usage Tracking Service
======================

Service for tracking, aggregating, and reporting resource usage.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.domain.usage.entities import (
    BillingPeriod,
    ResourceType,
    UsageRecord,
    UsageSummary,
    get_plan_limits,
)

logger = logging.getLogger(__name__)


class UsageTracker:
    """Service for tracking and managing resource usage."""

    def __init__(self):
        # In-memory storage (replace with database in production)
        self._records: Dict[str, List[UsageRecord]] = defaultdict(list)
        self._summaries: Dict[str, UsageSummary] = {}

    def track_usage(
        self,
        user_id: str,
        resource_type: ResourceType,
        quantity: float = 1.0,
        organization_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> UsageRecord:
        """
        Track a usage event.

        Args:
            user_id: User ID
            resource_type: Type of resource being used
            quantity: Amount of resource consumed
            organization_id: Optional organization ID
            metadata: Additional metadata about the usage

        Returns:
            UsageRecord: The created usage record
        """
        record = UsageRecord(
            user_id=user_id,
            organization_id=organization_id,
            resource_type=resource_type,
            quantity=quantity,
            unit=self._get_unit(resource_type),
            metadata=metadata or {},
        )

        self._records[user_id].append(record)
        logger.info(f"Tracked usage: {user_id} - {resource_type.value} - {quantity}")

        return record

    def get_usage(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        resource_type: Optional[ResourceType] = None,
    ) -> List[UsageRecord]:
        """
        Get usage records for a user.

        Args:
            user_id: User ID
            start_date: Optional start date filter
            end_date: Optional end date filter
            resource_type: Optional resource type filter

        Returns:
            List of usage records
        """
        records = self._records.get(user_id, [])

        # Apply filters
        if start_date:
            records = [r for r in records if r.timestamp >= start_date]
        if end_date:
            records = [r for r in records if r.timestamp <= end_date]
        if resource_type:
            records = [r for r in records if r.resource_type == resource_type]

        return records

    def get_usage_summary(
        self,
        user_id: str,
        period: BillingPeriod = BillingPeriod.MONTHLY,
        organization_id: Optional[str] = None,
    ) -> UsageSummary:
        """
        Get aggregated usage summary for the current billing period.

        Args:
            user_id: User ID
            period: Billing period type
            organization_id: Optional organization ID

        Returns:
            UsageSummary: Aggregated usage summary
        """
        period_start, period_end = self._get_period_dates(period)

        records = self.get_usage(
            user_id=user_id,
            start_date=period_start,
            end_date=period_end,
        )

        # Aggregate by resource type
        summary = UsageSummary(
            user_id=user_id,
            organization_id=organization_id,
            period_start=period_start,
            period_end=period_end,
            billing_period=period,
        )

        for record in records:
            if record.resource_type == ResourceType.API_CALLS:
                summary.api_calls += int(record.quantity)
            elif record.resource_type == ResourceType.TEST_EXECUTIONS:
                summary.test_executions += int(record.quantity)
            elif record.resource_type == ResourceType.AI_GENERATIONS:
                summary.ai_generations += int(record.quantity)
            elif record.resource_type == ResourceType.STORAGE_MB:
                summary.storage_mb += record.quantity
            elif record.resource_type == ResourceType.BANDWIDTH_MB:
                summary.bandwidth_mb += record.quantity

        return summary

    def calculate_costs(
        self,
        summary: UsageSummary,
        plan_name: str = "free",
    ) -> UsageSummary:
        """
        Calculate costs for a usage summary based on plan pricing.

        Args:
            summary: Usage summary to calculate costs for
            plan_name: Subscription plan name

        Returns:
            UsageSummary: Summary with calculated costs
        """
        limits = get_plan_limits(plan_name)

        # Calculate overage costs (if usage exceeds plan limits)
        summary.api_calls_cost = self._calculate_overage_cost(
            summary.api_calls, limits.max_api_calls, limits.api_call_price
        )
        summary.test_executions_cost = self._calculate_overage_cost(
            summary.test_executions, limits.max_test_executions, limits.test_execution_price
        )
        summary.ai_generations_cost = self._calculate_overage_cost(
            summary.ai_generations, limits.max_ai_generations, limits.ai_generation_price
        )
        summary.storage_cost = self._calculate_overage_cost(
            summary.storage_mb, limits.max_storage_mb, limits.storage_price_per_mb
        )
        summary.bandwidth_cost = self._calculate_overage_cost(
            summary.bandwidth_mb, limits.max_bandwidth_mb, limits.bandwidth_price_per_mb
        )

        summary.calculate_total()
        summary.updated_at = datetime.now(timezone.utc)

        return summary

    def check_usage_limit(
        self,
        user_id: str,
        resource_type: ResourceType,
        plan_name: str = "free",
    ) -> Dict[str, Any]:
        """
        Check if user is within usage limits for a resource type.

        Args:
            user_id: User ID
            resource_type: Type of resource to check
            plan_name: Subscription plan name

        Returns:
            Dict with limit status information
        """
        limits = get_plan_limits(plan_name)
        summary = self.get_usage_summary(user_id)

        current_usage = self._get_current_usage(summary, resource_type)
        limit = limits.get_limit(resource_type)

        # -1 means unlimited
        is_unlimited = limit == -1
        is_within_limit = is_unlimited or current_usage < limit
        remaining = -1 if is_unlimited else max(0, limit - current_usage)
        percentage = (
            0 if is_unlimited else min(100, (current_usage / limit) * 100) if limit > 0 else 100
        )

        return {
            "resource_type": resource_type.value,
            "current_usage": current_usage,
            "limit": limit,
            "remaining": remaining,
            "is_within_limit": is_within_limit,
            "is_unlimited": is_unlimited,
            "percentage_used": percentage,
            "plan_name": plan_name,
        }

    def get_usage_report(
        self,
        user_id: str,
        plan_name: str = "free",
    ) -> Dict[str, Any]:
        """
        Get a comprehensive usage report for a user.

        Args:
            user_id: User ID
            plan_name: Subscription plan name

        Returns:
            Dict with full usage report
        """
        summary = self.get_usage_summary(user_id)
        summary_with_costs = self.calculate_costs(summary, plan_name)
        limits = get_plan_limits(plan_name)

        # Get limit checks for all resource types
        limit_checks = {}
        for resource_type in ResourceType:
            limit_checks[resource_type.value] = self.check_usage_limit(
                user_id, resource_type, plan_name
            )

        return {
            "user_id": user_id,
            "plan_name": plan_name,
            "billing_period": summary_with_costs.billing_period.value,
            "period_start": summary_with_costs.period_start.isoformat(),
            "period_end": summary_with_costs.period_end.isoformat(),
            "usage": summary_with_costs.to_dict(),
            "limits": limits.to_dict(),
            "limit_status": limit_checks,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _get_unit(self, resource_type: ResourceType) -> str:
        """Get the unit for a resource type."""
        units = {
            ResourceType.API_CALLS: "calls",
            ResourceType.TEST_EXECUTIONS: "executions",
            ResourceType.AI_GENERATIONS: "generations",
            ResourceType.STORAGE_MB: "MB",
            ResourceType.BANDWIDTH_MB: "MB",
        }
        return units.get(resource_type, "count")

    def _get_period_dates(self, period: BillingPeriod) -> tuple:
        """Get start and end dates for a billing period."""
        now = datetime.now(timezone.utc)

        if period == BillingPeriod.DAILY:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        elif period == BillingPeriod.WEEKLY:
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(weeks=1)
        elif period == BillingPeriod.MONTHLY:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if now.month == 12:
                end = start.replace(year=now.year + 1, month=1)
            else:
                end = start.replace(month=now.month + 1)
        elif period == BillingPeriod.YEARLY:
            start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end = start.replace(year=now.year + 1)
        else:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if now.month == 12:
                end = start.replace(year=now.year + 1, month=1)
            else:
                end = start.replace(month=now.month + 1)

        return start, end

    def _calculate_overage_cost(
        self,
        usage: float,
        limit: int,
        price_per_unit: int,
    ) -> int:
        """Calculate cost for usage over the limit."""
        if limit == -1:  # Unlimited
            return 0
        overage = max(0, usage - limit)
        return int(overage * price_per_unit)

    def _get_current_usage(self, summary: UsageSummary, resource_type: ResourceType) -> float:
        """Get current usage for a resource type from summary."""
        usage_map = {
            ResourceType.API_CALLS: summary.api_calls,
            ResourceType.TEST_EXECUTIONS: summary.test_executions,
            ResourceType.AI_GENERATIONS: summary.ai_generations,
            ResourceType.STORAGE_MB: summary.storage_mb,
            ResourceType.BANDWIDTH_MB: summary.bandwidth_mb,
        }
        return usage_map.get(resource_type, 0)


# Singleton instance
_usage_tracker: Optional[UsageTracker] = None


def get_usage_tracker() -> UsageTracker:
    """Get the singleton usage tracker instance."""
    global _usage_tracker
    if _usage_tracker is None:
        _usage_tracker = UsageTracker()
    return _usage_tracker
