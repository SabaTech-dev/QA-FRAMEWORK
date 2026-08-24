"""User migrator for multi-tenant migration."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dashboard.backend.models import User as UserModel
from domain.entities.tenant import Tenant

from .migrator import DataMigrator

logger = logging.getLogger(__name__)


class UserMigrator(DataMigrator):
    """
    Migrator for user entities to multi-tenant architecture.

    Handles migration of users from single-tenant to multi-tenant system.
    """

    def __init__(self, db_session: AsyncSession, dry_run: bool = False):
        """
        Initialize the UserMigrator.

        Args:
            db_session: Async database session
            dry_run: If True, simulate migration without making changes
        """
        super().__init__(db_session, dry_run)
        self.migrated_users = []
        self.skipped_users = []
        self.errors = []

    async def migrate_users(self, default_tenant: Tenant) -> list[str]:
        """
        Migrate all existing users to the default tenant.

        Args:
            default_tenant: The default tenant to assign users to

        Returns:
            List of migrated user IDs
        """
        await self.start()
        self.stats["total_records"] = 0
        self.stats["migrated_records"] = 0
        self.stats["failed_records"] = 0

        try:
            # Get all users without tenant_id
            result = await self.db_session.execute(
                select(UserModel).where(UserModel.tenant_id.is_(None))
            )
            users = result.scalars().all()

            count = len(users)
            logger.info(f"Found {count} users to migrate")

            self.stats["total_records"] = count
            migrated_ids = []

            for user in users:
                try:
                    if self.dry_run:
                        logger.info(
                            f"[DRY RUN] Would migrate user: {user.username} "
                            f"(email: {user.email})"
                        )
                        self.stats["migrated_records"] += 1
                        migrated_ids.append(str(user.id))
                        continue

                    # Assign user to default tenant
                    user.tenant_id = default_tenant.id
                    self.db_session.add(user)

                    logger.info(
                        f"Migrated user: {user.username} (email: {user.email}) "
                        f"to tenant: {default_tenant.slug}"
                    )

                    migrated_ids.append(str(user.id))
                    self.stats["migrated_records"] += 1
                    self.migrated_users.append(user)

                except Exception as e:
                    error_msg = f"Failed to migrate user {user.username}: {e!s}"
                    logger.error(error_msg)
                    self.add_error(error_msg)
                    self.errors.append(error_msg)
                    self.skipped_users.append(user.username)

            if not self.dry_run:
                await self.db_session.commit()
                logger.info(f"Successfully migrated {self.stats['migrated_records']} users")

            return migrated_ids

        except Exception as e:
            error_msg = f"User migration failed: {e!s}"
            logger.error(error_msg)
            self.add_error(error_msg)
            if not self.dry_run:
                await self.db_session.rollback()
            raise

    def get_migrated_users(self) -> list:
        """
        Get list of migrated users.

        Returns:
            List of migrated user entities
        """
        return self.migrated_users

    def get_skipped_users(self) -> list:
        """
        Get list of users that were skipped.

        Returns:
            List of skipped user usernames
        """
        return self.skipped_users

    def get_errors(self) -> list[str]:
        """
        Get list of migration errors.

        Returns:
            List of error messages
        """
        return self.errors

    async def finalize(self, success: bool = True) -> None:
        """
        Finalize the user migration.

        Args:
            success: Whether the migration was successful
        """
        await super().complete(success)
        logger.info(
            f"User migration final stats: "
            f"{self.stats['migrated_records']} migrated, "
            f"{self.stats['failed_records']} failed"
        )
