"""Tenant entity - Domain model for multi-tenancy support"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


class TenantPlan(Enum):
    """Tenant subscription plan types"""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class TenantStatus(Enum):
    """Tenant account status"""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"


@dataclass
class Tenant:
    """
    Entity representing a tenant in the multi-tenant system.

    This is a domain entity following Clean Architecture principles.
    It represents a customer/organization in the SaaS platform.

    Attributes:
        id: Unique identifier (UUID)
        name: Display name of the tenant/organization
        slug: URL-friendly identifier (e.g., "acme-corp")
        plan: Subscription plan (FREE, PRO, ENTERPRISE)
        status: Account status (ACTIVE, SUSPENDED, TRIAL)
        settings: JSON configuration specific to tenant
        created_at: When the tenant was created
        updated_at: When the tenant was last updated
    """

    id: UUID = field(default_factory=uuid4)
    name: str = ""
    slug: str = ""
    plan: TenantPlan = TenantPlan.FREE
    status: TenantStatus = TenantStatus.TRIAL
    settings: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Initialize default values"""
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)
        if self.settings is None:
            self.settings = {}

    def is_active(self) -> bool:
        """Check if tenant account is active"""
        return self.status == TenantStatus.ACTIVE

    def is_suspended(self) -> bool:
        """Check if tenant account is suspended"""
        return self.status == TenantStatus.SUSPENDED

    def is_trial(self) -> bool:
        """Check if tenant is in trial period"""
        return self.status == TenantStatus.TRIAL

    def is_enterprise(self) -> bool:
        """Check if tenant has enterprise plan"""
        return self.plan == TenantPlan.ENTERPRISE

    def is_pro(self) -> bool:
        """Check if tenant has pro plan or higher"""
        return self.plan in [TenantPlan.PRO, TenantPlan.ENTERPRISE]

    def update_settings(self, key: str, value: Any) -> None:
        """
        Update a specific setting.

        Args:
            key: Setting key
            value: Setting value
        """
        self.settings[key] = value
        self.updated_at = datetime.now(timezone.utc)

    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a specific setting value.

        Args:
            key: Setting key
            default: Default value if key doesn't exist

        Returns:
            Setting value or default
        """
        return self.settings.get(key, default)

    def activate(self) -> None:
        """Activate tenant account"""
        self.status = TenantStatus.ACTIVE
        self.updated_at = datetime.now(timezone.utc)

    def suspend(self) -> None:
        """Suspend tenant account"""
        self.status = TenantStatus.SUSPENDED
        self.updated_at = datetime.now(timezone.utc)

    def upgrade_plan(self, new_plan: TenantPlan) -> None:
        """
        Upgrade tenant plan.

        Args:
            new_plan: New subscription plan
        """
        self.plan = new_plan
        self.updated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert tenant entity to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "slug": self.slug,
            "plan": self.plan.value,
            "status": self.status.value,
            "settings": self.settings,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Tenant":
        """
        Create a Tenant instance from a dictionary.

        Args:
            data: Dictionary with tenant data

        Returns:
            Tenant instance
        """
        return cls(
            id=UUID(data["id"]) if isinstance(data.get("id"), str) else data.get("id", uuid4()),
            name=data.get("name", ""),
            slug=data.get("slug", ""),
            plan=TenantPlan(data.get("plan", TenantPlan.FREE.value)),
            status=TenantStatus(data.get("status", TenantStatus.TRIAL.value)),
            settings=data.get("settings", {}),
            created_at=(
                datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
            ),
            updated_at=(
                datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None
            ),
        )

    def __repr__(self) -> str:
        """String representation of Tenant"""
        return f"Tenant(id={self.id}, name={self.name}, slug={self.slug}, plan={self.plan.value}, status={self.status.value})"

    def __eq__(self, other: object) -> bool:
        """Check equality based on ID"""
        if not isinstance(other, Tenant):
            return False
        return self.id == other.id
