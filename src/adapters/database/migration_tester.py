"""Database migration testing module"""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class MigrationStatus(Enum):
    """Status of migration test."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class MigrationResult:
    """
    Result from migration test.

    Attributes:
        migration_name: Name or identifier of migration
        status: Migration status
        execution_time: Time taken to execute in seconds
        error_message: Error message if failed
        warnings: List of warnings
        changes_applied: List of changes that were applied
        rollback_successful: Whether rollback succeeded (if applicable)
    """

    migration_name: str
    status: MigrationStatus
    execution_time: float
    error_message: Optional[str] = None
    warnings: Optional[List[str]] = None
    changes_applied: Optional[List[str]] = None
    rollback_successful: Optional[bool] = None

    def __post_init__(self) -> None:
        if self.warnings is None:
            self.warnings = []
        if self.changes_applied is None:
            self.changes_applied = []


class MigrationTester:
    """
    Tester for database migration scripts.

    This class provides methods to test database migrations including
    forward migration execution, rollback capability, and integrity checks.

    Example:
        tester = MigrationTester(database_client)

        result = await tester.test_migration(
            migration_script="migrations/001_add_users_table.sql",
            rollback_script="migrations/001_add_users_table_rollback.sql"
        )

        if result.status == MigrationStatus.SUCCESS:
            print("Migration successful!")
        else:
            print(f"Migration failed: {result.error_message}")
    """

    def __init__(self, database_client: Any):
        """
        Initialize migration tester.

        Args:
            database_client: Database client with query execution capability
        """
        self.db = database_client
        self._results: List[MigrationResult] = []

    async def test_migration(
        self,
        migration_script: str,
        rollback_script: Optional[str] = None,
        test_data_script: Optional[str] = None,
        validate_after: bool = True,
    ) -> MigrationResult:
        """
        Test a database migration script.

        Args:
            migration_script: Path to migration script or SQL content
            rollback_script: Optional path to rollback script
            test_data_script: Optional path to test data script
            validate_after: Whether to validate schema after migration

        Returns:
            MigrationResult with test details
        """
        import time

        start_time = time.time()

        migration_name = (
            os.path.basename(migration_script)
            if os.path.exists(migration_script)
            else "inline_migration"
        )
        warnings = []
        changes_applied = []

        try:
            # Check if migration file exists or if it's inline SQL
            if os.path.exists(migration_script):
                with open(migration_script, "r") as f:
                    migration_sql = f.read()
            else:
                migration_sql = migration_script  # Assume it's SQL content
                migration_name = "inline_migration"

            # Parse migration to identify changes
            changes_applied = self._parse_migration_changes(migration_sql)

            # Create backup point for rollback testing
            await self._create_backup_point()

            # Execute migration
            await self._execute_sql(migration_sql)

            # Apply test data if provided
            if test_data_script and os.path.exists(test_data_script):
                with open(test_data_script, "r") as f:
                    await self._execute_sql(f.read())

            # Validate migration
            if validate_after:
                validation_result = await self._validate_migration(migration_sql)
                warnings.extend(validation_result.get("warnings", []))

            execution_time = time.time() - start_time

            # Test rollback if provided
            rollback_successful = None
            if rollback_script:
                rollback_successful = await self._test_rollback(rollback_script)

            result = MigrationResult(
                migration_name=migration_name,
                status=MigrationStatus.SUCCESS,
                execution_time=execution_time,
                warnings=warnings,
                changes_applied=changes_applied,
                rollback_successful=rollback_successful,
            )

            self._results.append(result)
            return result

        except Exception as e:
            execution_time = time.time() - start_time

            # Try to rollback on failure
            rollback_successful = None
            if rollback_script:
                try:
                    await self._test_rollback(rollback_script)
                    rollback_successful = True
                except Exception:
                    rollback_successful = False

            result = MigrationResult(
                migration_name=migration_name,
                status=MigrationStatus.FAILED,
                execution_time=execution_time,
                error_message=str(e),
                warnings=warnings,
                changes_applied=changes_applied,
                rollback_successful=rollback_successful,
            )

            self._results.append(result)
            return result

    async def test_migration_chain(self, migrations: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Test a chain of dependent migrations.

        Args:
            migrations: List of migration configs with 'migration' and optional 'rollback' keys

        Returns:
            Dictionary with chain test results
        """
        results = []
        successful = []
        failed = []

        for i, migration_config in enumerate(migrations):
            migration_script = migration_config.get("migration")
            rollback_script = migration_config.get("rollback")

            if not migration_script:
                continue  # Skip if no migration script provided

            result = await self.test_migration(
                migration_script=migration_script, rollback_script=rollback_script
            )

            results.append({"order": i + 1, "result": result})

            if result.status == MigrationStatus.SUCCESS:
                successful.append(result)
            else:
                failed.append(result)
                # Stop chain on failure
                break

        return {
            "total_migrations": len(migrations),
            "successful": len(successful),
            "failed": len(failed),
            "completed": len(failed) == 0,
            "results": results,
        }

    async def validate_migration_idempotency(self, migration_script: str) -> Dict[str, Any]:
        """
        Test if migration is idempotent (can be run multiple times safely).

        Args:
            migration_script: Path to migration script

        Returns:
            Dictionary with idempotency test results
        """
        try:
            # Run migration first time
            result1 = await self.test_migration(migration_script)

            if result1.status != MigrationStatus.SUCCESS:
                return {
                    "is_idempotent": False,
                    "error": "Initial migration failed",
                    "first_run": result1.status.value,
                    "second_run": None,
                }

            # Run migration second time
            result2 = await self.test_migration(migration_script)

            is_idempotent = result2.status == MigrationStatus.SUCCESS or (
                result2.status == MigrationStatus.FAILED
                and "already exists" in str(result2.error_message).lower()
            )

            return {
                "is_idempotent": is_idempotent,
                "first_run": result1.status.value,
                "second_run": result2.status.value,
                "recommendations": [
                    (
                        "Use IF NOT EXISTS for CREATE statements"
                        if not is_idempotent
                        else "Migration appears to be idempotent"
                    ),
                    "Use IF EXISTS for DROP statements" if not is_idempotent else "",
                    (
                        "Consider adding guards to prevent duplicate execution"
                        if not is_idempotent
                        else ""
                    ),
                ],
            }

        except Exception as e:
            return {"is_idempotent": False, "error": str(e)}

    async def check_migration_compatibility(
        self, migration_script: str, existing_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if migration is compatible with existing schema.

        Args:
            migration_script: Path to migration script
            existing_schema: Current database schema

        Returns:
            Dictionary with compatibility analysis
        """
        try:
            if os.path.exists(migration_script):
                with open(migration_script, "r") as f:
                    migration_sql = f.read()
            else:
                migration_sql = migration_script

            issues = []
            warnings = []

            # Check for table creation conflicts
            tables_to_create = self._extract_tables_from_migration(migration_sql)
            for table in tables_to_create:
                if table in existing_schema.get("tables", []):
                    issues.append(f"Table '{table}' already exists")

            # Check for column modifications
            column_changes = self._extract_column_changes(migration_sql)
            for change in column_changes:
                if change["table"] in existing_schema.get("tables", []):
                    if change["action"] == "drop" and change["column"] in existing_schema.get(
                        "columns", {}
                    ).get(change["table"], []):
                        warnings.append(
                            f"Column '{change['column']}' will be dropped from '{change['table']}'"
                        )

            return {
                "compatible": len(issues) == 0,
                "issues": issues,
                "warnings": warnings,
                "tables_affected": tables_to_create,
                "recommendations": (
                    [
                        "Review existing schema before applying migration",
                        "Create backup before running destructive changes",
                    ]
                    if issues or warnings
                    else ["Migration appears compatible with existing schema"]
                ),
            }

        except Exception as e:
            return {"compatible": False, "error": str(e)}

    async def _execute_sql(self, sql: str) -> None:
        """Execute SQL script."""
        # Split by semicolons to execute statements separately
        statements = [s.strip() for s in sql.split(";") if s.strip()]

        for statement in statements:
            await self.db.execute_query(statement)

    async def _create_backup_point(self) -> bool:
        """Create a backup point for rollback testing."""
        # This is a simplified version - real implementation would use
        # database-specific backup mechanisms
        try:
            # For testing purposes, we'll just return True
            # In production, this would create a transaction savepoint or backup
            return True
        except Exception:
            return False

    async def _test_rollback(self, rollback_script: str) -> bool:
        """Test rollback script execution."""
        try:
            if os.path.exists(rollback_script):
                with open(rollback_script, "r") as f:
                    rollback_sql = f.read()
            else:
                rollback_sql = rollback_script

            await self._execute_sql(rollback_sql)
            return True
        except Exception:
            return False

    async def _validate_migration(self, migration_sql: str) -> Dict[str, Any]:
        """Validate migration results."""
        warnings = []

        # Check for common issues
        if "DROP TABLE" in migration_sql.upper() and "CREATE TABLE" not in migration_sql.upper():
            warnings.append("Migration only contains DROP statements - data will be lost")

        if "ALTER TABLE" in migration_sql.upper():
            warnings.append("ALTER TABLE operations may lock tables - consider maintenance window")

        return {"warnings": warnings}

    def _parse_migration_changes(self, sql: str) -> List[str]:
        """Parse migration SQL to identify changes."""
        changes = []
        sql_upper = sql.upper()

        if "CREATE TABLE" in sql_upper:
            changes.append("Create table(s)")
        if "DROP TABLE" in sql_upper:
            changes.append("Drop table(s)")
        if "ALTER TABLE" in sql_upper:
            changes.append("Alter table(s)")
        if "CREATE INDEX" in sql_upper:
            changes.append("Create index(es)")
        if "DROP INDEX" in sql_upper:
            changes.append("Drop index(es)")
        if "INSERT" in sql_upper:
            changes.append("Insert data")
        if "UPDATE" in sql_upper:
            changes.append("Update data")
        if "DELETE" in sql_upper:
            changes.append("Delete data")

        return changes

    def _extract_tables_from_migration(self, sql: str) -> List[str]:
        """Extract table names from migration SQL."""
        import re

        tables = []

        # Match CREATE TABLE statements
        create_matches = re.findall(
            r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)", sql, re.IGNORECASE
        )
        tables.extend(create_matches)

        return list(set(tables))

    def _extract_column_changes(self, sql: str) -> List[Dict[str, str]]:
        """Extract column modifications from migration."""
        import re

        changes = []

        # Match ALTER TABLE ... DROP COLUMN
        drop_matches = re.findall(
            r"ALTER\s+TABLE\s+(\w+)\s+DROP\s+COLUMN\s+(\w+)", sql, re.IGNORECASE
        )
        for table, column in drop_matches:
            changes.append({"table": table, "column": column, "action": "drop"})

        return changes

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of all migration tests.

        Returns:
            Dictionary with test summary
        """
        if not self._results:
            return {
                "total_migrations": 0,
                "successful": 0,
                "failed": 0,
                "average_execution_time": 0,
            }

        successful = [r for r in self._results if r.status == MigrationStatus.SUCCESS]
        failed = [r for r in self._results if r.status == MigrationStatus.FAILED]

        total_time = sum(r.execution_time for r in self._results)

        return {
            "total_migrations": len(self._results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(self._results),
            "average_execution_time": round(total_time / len(self._results), 3),
            "total_warnings": sum(len(r.warnings) if r.warnings else 0 for r in self._results),
            "total_changes": sum(
                len(r.changes_applied) if r.changes_applied else 0 for r in self._results
            ),
        }
