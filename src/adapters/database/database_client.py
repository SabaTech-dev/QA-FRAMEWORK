"""Main database testing client"""

from typing import Any

from src.adapters.database.data_integrity_tester import DataIntegrityTester, IntegrityConstraint
from src.adapters.database.migration_tester import MigrationTester
from src.adapters.database.sql_validator import SQLValidator
from src.core.interfaces import IDatabaseClient


class DatabaseClient(IDatabaseClient):
    """
    Main client for database testing.

    This class provides a unified interface for database testing including
    SQL validation, data integrity testing, and migration testing.

    It follows the Facade design pattern to provide simplified access
    to all database testing functionality.

    Note: This is a generic base class. You should use database-specific
    implementations like PostgreSQLClient, MySQLClient, etc.

    Example:
        client = DatabaseClient(connection_string)
        await client.connect()

        # Validate SQL
        validation = await client.validate_query("SELECT * FROM users")

        # Test data integrity
        integrity = await client.test_data_integrity(
            table="users",
            constraints=[...]
        )

        # Test migration
        migration = await client.test_migration("migrations/001.sql")

        await client.disconnect()
    """

    def __init__(self, connection_string: str | None = None):
        """
        Initialize database client.

        Args:
            connection_string: Database connection string (optional)
        """
        self.connection_string = connection_string
        self._connection: Any | None = None
        self._validator = SQLValidator()
        self._integrity_tester: DataIntegrityTester | None = None
        self._migration_tester: MigrationTester | None = None
        self._connected = False

    async def connect(self) -> None:
        """
        Establish database connection.

        Note: This base class method should be overridden by
        database-specific implementations.
        """
        raise NotImplementedError(
            "DatabaseClient is a base class. Use a specific implementation like "
            "PostgreSQLClient, MySQLClient, SQLiteClient, etc."
        )

    async def disconnect(self) -> None:
        """Close database connection."""
        self._connected = False
        self._connection = None

    async def execute_query(self, query: str, params: dict | None = None) -> Any:
        """
        Execute a SQL query.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Query results
        """
        if not self._connected:
            raise RuntimeError("Database not connected. Call connect() first.")

        # This should be implemented by subclasses
        raise NotImplementedError("execute_query must be implemented by subclass")

    async def validate_query(self, query: str) -> dict[str, Any]:
        """
        Validate a SQL query for syntax and performance issues.

        Args:
            query: SQL query to validate

        Returns:
            Dictionary with validation results
        """
        # Run validation
        result = self._validator.validate_query(query)

        # Get query plan analysis
        plan_analysis = self._validator.analyze_query_plan(query)

        return {
            "is_valid": result.is_valid,
            "has_errors": result.has_errors(),
            "has_warnings": result.has_warnings(),
            "issues": [
                {
                    "severity": i.severity.value,
                    "message": i.message,
                    "line": i.line_number,
                    "suggestion": i.suggestion,
                }
                for i in result.issues
            ],
            "warnings": [
                {
                    "severity": i.severity.value,
                    "message": i.message,
                    "line": i.line_number,
                    "suggestion": i.suggestion,
                }
                for i in result.warnings
            ],
            "suggestions": [
                {
                    "severity": i.severity.value,
                    "message": i.message,
                    "line": i.line_number,
                    "suggestion": i.suggestion,
                }
                for i in result.suggestions
            ],
            "query_plan": plan_analysis,
        }

    async def test_data_integrity(
        self, table: str, constraints: list[IntegrityConstraint]
    ) -> dict[str, Any]:
        """
        Test data integrity constraints.

        Args:
            table: Table name to test
            constraints: List of constraints to validate

        Returns:
            Dictionary with integrity test results
        """
        if not self._connected:
            raise RuntimeError("Database not connected. Call connect() first.")

        if self._integrity_tester is None:
            self._integrity_tester = DataIntegrityTester(self)

        return await self._integrity_tester.test_data_integrity(table, constraints)

    async def test_migration(
        self, migration_script: str, rollback_script: str | None = None
    ) -> dict[str, Any]:
        """
        Test database migration script.

        Args:
            migration_script: Path to migration script or SQL content
            rollback_script: Optional path to rollback script

        Returns:
            Dictionary with migration test results
        """
        if not self._connected:
            raise RuntimeError("Database not connected. Call connect() first.")

        if self._migration_tester is None:
            self._migration_tester = MigrationTester(self)

        result = await self._migration_tester.test_migration(
            migration_script=migration_script, rollback_script=rollback_script
        )

        return {
            "migration_name": result.migration_name,
            "status": result.status.value,
            "execution_time": round(result.execution_time, 3),
            "error_message": result.error_message,
            "warnings": result.warnings,
            "changes_applied": result.changes_applied,
            "rollback_successful": result.rollback_successful,
        }

    async def get_schema_info(self) -> dict[str, Any]:
        """
        Get database schema information.

        Returns:
            Dictionary with schema details including tables, columns, indexes
        """
        if not self._connected:
            raise RuntimeError("Database not connected. Call connect() first.")

        # This should be implemented by subclasses
        raise NotImplementedError("get_schema_info must be implemented by subclass")

    async def check_orphan_records(
        self, table: str, column: str, reference_table: str, reference_column: str
    ) -> dict[str, Any]:
        """
        Check for orphan records in foreign key relationships.

        Args:
            table: Table to check
            column: Foreign key column
            reference_table: Referenced table
            reference_column: Referenced column

        Returns:
            Dictionary with orphan record analysis
        """
        if not self._connected:
            raise RuntimeError("Database not connected. Call connect() first.")

        if self._integrity_tester is None:
            self._integrity_tester = DataIntegrityTester(self)

        return await self._integrity_tester.check_orphan_records(
            table=table,
            column=column,
            reference_table=reference_table,
            reference_column=reference_column,
        )

    async def run_full_database_scan(self) -> dict[str, Any]:
        """
        Run a comprehensive database scan.

        Returns:
            Dictionary with complete database analysis
        """
        if not self._connected:
            raise RuntimeError("Database not connected. Call connect() first.")

        schema_info = await self.get_schema_info()

        results = {
            "schema": schema_info,
            "table_integrity": {},
            "orphan_records": {},
            "recommendations": [],
        }

        # Check integrity for all tables
        for table in schema_info.get("tables", []):
            # This would need to be customized based on schema
            pass

        return results

    def is_connected(self) -> bool:
        """
        Check if database is connected.

        Returns:
            True if connected, False otherwise
        """
        return self._connected

    async def __aenter__(self) -> "DatabaseClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()


class SQLiteClient(DatabaseClient):
    """
    SQLite-specific database client implementation.

    Example:
        client = SQLiteClient("test.db")
        await client.connect()

        results = await client.execute_query("SELECT * FROM users")

        await client.disconnect()
    """

    def __init__(self, database_path: str = ":memory:"):
        """
        Initialize SQLite client.

        Args:
            database_path: Path to SQLite database file (default: in-memory)
        """
        super().__init__(database_path)
        self.database_path = database_path
        self._sqlite_conn = None

    async def connect(self) -> None:
        """Establish SQLite connection."""
        import aiosqlite

        self._sqlite_conn = await aiosqlite.connect(self.database_path)
        self._connected = True

    async def disconnect(self) -> None:
        """Close SQLite connection."""
        if self._sqlite_conn:
            await self._sqlite_conn.close()
            self._sqlite_conn = None
        self._connected = False

    async def execute_query(self, query: str, params: dict | None = None) -> Any:
        """
        Execute SQL query on SQLite database.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Query results
        """
        if not self._connected or not self._sqlite_conn:
            raise RuntimeError("Database not connected")

        cursor = await self._sqlite_conn.execute(query, params or {})

        # For SELECT queries, fetch results
        if query.strip().upper().startswith("SELECT"):
            rows = await cursor.fetchall()
            await cursor.close()
            return rows
        else:
            await self._sqlite_conn.commit()
            await cursor.close()
            return []

    async def get_schema_info(self) -> dict[str, Any]:
        """
        Get SQLite database schema information.

        Returns:
            Dictionary with schema details
        """
        if not self._connected:
            raise RuntimeError("Database not connected")

        # Get list of tables
        tables_result = await self.execute_query(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in tables_result]

        schema: dict[str, Any] = {"tables": tables, "columns": {}, "indexes": {}}

        # Get columns for each table
        for table in tables:
            columns_result = await self.execute_query(f"PRAGMA table_info({table})")
            schema["columns"][table] = [
                {
                    "name": row[1],
                    "type": row[2],
                    "nullable": not row[3],
                    "default": row[4],
                    "primary_key": bool(row[5]),
                }
                for row in columns_result
            ]

            # Get indexes for each table
            indexes_result = await self.execute_query(f"PRAGMA index_list({table})")
            schema["indexes"][table] = [
                {"name": row[1], "unique": bool(row[2])} for row in indexes_result
            ]

        return schema
