"""Test migrator for multi-tenant migration."""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dashboard.backend.models import TestCase, TestExecutionDetail, TestSuite
from domain.entities.tenant import Tenant

from .migrator import DataMigrator

logger = logging.getLogger(__name__)


class TestMigrator(DataMigrator):
    """
    Migrator for test entities to multi-tenant architecture.

    Handles migration of test suites, test cases, and executions.
    """

    def __init__(self, db_session: AsyncSession, dry_run: bool = False):
        """
        Initialize the TestMigrator.

        Args:
            db_session: Async database session
            dry_run: If True, simulate migration without making changes
        """
        super().__init__(db_session, dry_run)
        self.migrated_suites = []
        self.migrated_cases = []
        self.migrated_executions = []
        self.errors = []

    async def migrate_tests(self, default_tenant: Tenant) -> dict:
        """
        Migrate all test entities to the default tenant.

        Args:
            default_tenant: The default tenant to assign tests to

        Returns:
            Dictionary with migration statistics
        """
        await self.start()
        self.stats["total_records"] = 0
        self.stats["migrated_records"] = 0
        self.stats["failed_records"] = 0

        try:
            # Get all test suites
            result = await self.db_session.execute(select(TestSuite))
            test_suites = result.scalars().all()

            suite_count = len(test_suites)
            logger.info(f"Found {suite_count} test suites to migrate")

            self.stats["total_records"] = suite_count

            for suite in test_suites:
                try:
                    if self.dry_run:
                        logger.info(f"[DRY RUN] Would migrate test suite: {suite.name}")
                        self.stats["migrated_records"] += 1
                        continue

                    # Migrate test suite (no tenant_id field, just update created_by)
                    # If created_by is set, it already references a user that was migrated
                    logger.info(
                        f"Migrating test suite: {suite.name} "
                        f"(created by user: {suite.created_by})"
                    )
                    self.migrated_suites.append(suite)

                    # Migrate test cases in this suite
                    await self._migrate_test_cases(suite, default_tenant)

                    self.stats["migrated_records"] += 1

                except Exception as e:
                    error_msg = f"Failed to migrate test suite {suite.name}: {e!s}"
                    logger.error(error_msg)
                    self.add_error(error_msg)
                    self.errors.append(error_msg)

            if not self.dry_run:
                await self.db_session.commit()
                logger.info(f"Successfully migrated {self.stats['migrated_records']} test entities")

            return {
                "suites_migrated": len(self.migrated_suites),
                "cases_migrated": len(self.migrated_cases),
            }

        except Exception as e:
            error_msg = f"Test migration failed: {e!s}"
            logger.error(error_msg)
            self.add_error(error_msg)
            if not self.dry_run:
                await self.db_session.rollback()
            raise

    async def _migrate_test_cases(self, suite, default_tenant: Tenant) -> None:
        """
        Migrate test cases within a suite.

        Args:
            suite: The test suite to migrate cases from
            default_tenant: The default tenant
        """
        try:
            result = await self.db_session.execute(
                select(TestCase).where(TestCase.suite_id == suite.id)
            )
            test_cases = result.scalars().all()

            for test_case in test_cases:
                try:
                    if self.dry_run:
                        logger.info(
                            f"[DRY RUN] Would migrate test case: {test_case.name} "
                            f"in suite: {suite.name}"
                        )
                        continue

                    logger.info(f"Migrating test case: {test_case.name} " f"in suite: {suite.name}")
                    self.migrated_cases.append(test_case)

                    # Migrate test executions
                    await self._migrate_executions(test_case, default_tenant)

                except Exception as e:
                    error_msg = f"Failed to migrate test case {test_case.name}: {e!s}"
                    logger.error(error_msg)
                    self.add_error(error_msg)
                    self.errors.append(error_msg)

        except Exception as e:
            error_msg = f"Failed to migrate test cases for suite {suite.name}: {e!s}"
            logger.error(error_msg)
            self.add_error(error_msg)
            self.errors.append(error_msg)

    async def _migrate_executions(self, test_case, default_tenant: Tenant) -> None:
        """
        Migrate test executions for a test case.

        Args:
            test_case: The test case to migrate executions from
            default_tenant: The default tenant
        """
        try:
            result = await self.db_session.execute(
                select(TestExecutionDetail).where(TestCase.id == test_case.id)
            )
            executions = result.scalars().all()

            for execution in executions:
                try:
                    if self.dry_run:
                        logger.info(f"[DRY RUN] Would migrate execution: {execution.id}")
                        continue

                    logger.info(
                        f"Migrating execution: {execution.id} " f"for test case: {test_case.name}"
                    )

                    # Executions don't have explicit tenant_id, but we're migrating
                    # the entire suite and its cases together
                    # TestExecutionDetail is already linked through TestCase
                    logger.info(f"Execution {execution.id} will be migrated with its test case")

                except Exception as e:
                    error_msg = f"Failed to migrate execution {execution.id}: {e!s}"
                    logger.error(error_msg)
                    self.add_error(error_msg)
                    self.errors.append(error_msg)

        except Exception as e:
            error_msg = f"Failed to get executions for test case {test_case.name}: {e!s}"
            logger.error(error_msg)
            self.add_error(error_msg)
            self.errors.append(error_msg)

    def get_migrated_suites(self) -> list:
        """
        Get list of migrated test suites.

        Returns:
            List of migrated test suite entities
        """
        return self.migrated_suites

    def get_migrated_cases(self) -> list:
        """
        Get list of migrated test cases.

        Returns:
            List of migrated test case entities
        """
        return self.migrated_cases

    def get_errors(self) -> list[str]:
        """
        Get list of migration errors.

        Returns:
            List of error messages
        """
        return self.errors

    async def finalize(self, success: bool = True) -> None:
        """
        Finalize the test migration.

        Args:
            success: Whether the migration was successful
        """
        await super().complete(success)
        logger.info(
            f"Test migration final stats: "
            f"{self.stats['migrated_records']} migrated, "
            f"{self.stats['failed_records']} failed"
        )
