"""Base DataMigrator class for multi-tenant migration."""

import logging
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.tenant import Tenant

logger = logging.getLogger(__name__)


class DataMigrator:
    """
    Base class for data migration from single-tenant to multi-tenant architecture.

    This migrator handles the migration of existing data to the new multi-tenant
    system, creating a default tenant and migrating all related entities.
    """

    class MigrationStatus(Enum):
        """Migration status types"""

        PENDING = "pending"
        IN_PROGRESS = "in_progress"
        COMPLETED = "completed"
        FAILED = "failed"

    def __init__(self, db_session: AsyncSession, dry_run: bool = False):
        """
        Initialize the DataMigrator.

        Args:
            db_session: Async database session
            dry_run: If True, simulate migration without making changes
        """
        self.db_session = db_session
        self.dry_run = dry_run
        self.stats: dict[str, Any] = {
            "status": self.MigrationStatus.PENDING,
            "started_at": None,
            "completed_at": None,
            "total_records": 0,
            "migrated_records": 0,
            "failed_records": 0,
            "errors": [],
            "warnings": [],
        }
        self._started = False

    async def start(self) -> None:
        """Start the migration process."""
        if self._started:
            logger.warning("Migration already started")
            return

        self._started = True
        self.stats["started_at"] = datetime.now(UTC).isoformat()
        self.stats["status"] = self.MigrationStatus.IN_PROGRESS
        logger.info("Starting multi-tenant data migration")

    async def complete(self, success: bool = True) -> None:
        """
        Complete the migration process.

        Args:
            success: Whether the migration was successful
        """
        self.stats["completed_at"] = datetime.now(UTC).isoformat()
        self.stats["status"] = (
            self.MigrationStatus.COMPLETED if success else self.MigrationStatus.FAILED
        )
        logger.info(
            f"Migration completed: {self.stats['status'].value} "
            f"- {self.stats['migrated_records']} records migrated"
        )

    async def create_default_tenant(self):
        """
        Create the default tenant for existing data.

        Returns:
            The created TenantModel or None if it already exists

        Raises:
            Exception: If tenant creation fails
        """
        try:
            logger.info("Creating default tenant...")

            # Check if default tenant already exists
            from dashboard.backend.models import TenantModel

            default_tenant_slug = "default"
            result = await self.db_session.execute(
                select(TenantModel).where(TenantModel.slug == default_tenant_slug)
            )
            existing_tenant = result.scalar_one_or_none()

            if existing_tenant:
                logger.info("Default tenant already exists")
                return existing_tenant

            if self.dry_run:
                logger.info(f"[DRY RUN] Would create default tenant: {default_tenant_slug}")
                return None

            # Create default tenant

            default_tenant = TenantModel(
                id="default-id",
                name="Default Organization",
                slug=default_tenant_slug,
                plan="free",
                status="active",
                settings={"description": "Default tenant for migrated data"},
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

            self.db_session.add(default_tenant)
            await self.db_session.commit()
            await self.db_session.refresh(default_tenant)

            logger.info(f"Created default tenant: {default_tenant.name}")
            return default_tenant

        except Exception as e:
            error_msg = f"Failed to create default tenant: {e!s}"
            logger.error(error_msg)
            self.stats["errors"].append(error_msg)
            if not self.dry_run:
                await self.db_session.rollback()
            raise

    async def get_existing_record_count(self) -> int:
        """
        Get total count of existing records that need migration.

        Returns:
            Total number of records across all entities
        """
        try:
            count_query = select(func.count(Tenant.id))
            total = await self.db_session.scalar(count_query)
            self.stats["total_records"] = total or 0
            return total or 0
        except Exception as e:
            error_msg = f"Failed to get record count: {e!s}"
            logger.error(error_msg)
            self.stats["errors"].append(error_msg)
            raise

    def add_warning(self, warning: str) -> None:
        """
        Add a warning to the migration stats.

        Args:
            warning: Warning message
        """
        self.stats["warnings"].append(warning)

    def add_error(self, error: str) -> None:
        """
        Add an error to the migration stats.

        Args:
            error: Error message
        """
        self.stats["errors"].append(error)
        self.stats["failed_records"] += 1

    def get_stats(self) -> dict[str, Any]:
        """
        Get current migration statistics.

        Returns:
            Dictionary with migration statistics
        """
        return self.stats.copy()

    async def __aenter__(self):
        """Context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if exc_type is not None:
            self.stats["status"] = self.MigrationStatus.FAILED
            self.stats["errors"].append(f"Migration failed with exception: {exc_val!s}")
            logger.error(f"Migration failed: {exc_val!s}")
        else:
            await self.complete(success=True)
