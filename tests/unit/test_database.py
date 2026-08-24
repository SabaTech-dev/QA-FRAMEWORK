"""
Unit tests for Database Testing Module.

This module tests the database testing adapters including:
- SQLValidator
- DataIntegrityTester
- MigrationTester
- DatabaseClient
- SQLiteClient
"""

import asyncio

# Add src to path
import sys
from pathlib import Path
from unittest.mock import AsyncMock, mock_open, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.adapters.database import (
    DatabaseClient,
    DataIntegrityTester,
    IntegrityConstraint,
    MigrationResult,
    MigrationStatus,
    MigrationTester,
    SQLiteClient,
    SQLValidator,
)
from src.adapters.database.data_integrity_tester import ConstraintType
from src.adapters.database.sql_validator import SQLValidationResult


class TestSQLValidator:
    """Test suite for SQLValidator."""

    def test_initialization(self):
        """Test validator initialization."""
        validator = SQLValidator()
        assert validator is not None
        assert hasattr(validator, "DANGEROUS_KEYWORDS")

    def test_validate_valid_query(self):
        """Test validation of valid SQL query."""
        validator = SQLValidator()

        query = "SELECT id, name FROM users WHERE status = 'active'"
        result = validator.validate_syntax(query)

        assert result.is_valid is True
        assert result.has_errors() is False

    def test_validate_empty_query(self):
        """Test validation of empty query."""
        validator = SQLValidator()

        result = validator.validate_syntax("")

        assert result.is_valid is False
        assert result.has_errors() is True
        assert any("empty" in issue.message.lower() for issue in result.issues)

    def test_validate_unclosed_quote(self):
        """Test detection of unclosed quote."""
        validator = SQLValidator()

        query = "SELECT * FROM users WHERE name = 'john"
        result = validator.validate_syntax(query)

        assert result.has_errors() is True
        assert any("unclosed" in issue.message.lower() for issue in result.issues)

    def test_validate_unbalanced_parentheses(self):
        """Test detection of unbalanced parentheses."""
        validator = SQLValidator()

        query = "SELECT * FROM users WHERE (id = 1 AND (name = 'john')"
        result = validator.validate_syntax(query)

        assert result.has_errors() is True
        assert any("parentheses" in issue.message.lower() for issue in result.issues)

    def test_check_performance_issues_select_star(self):
        """Test detection of SELECT * performance issue."""
        validator = SQLValidator()

        query = "SELECT * FROM users"
        result = validator.check_performance_issues(query)

        assert any("SELECT *" in suggestion.message for suggestion in result.suggestions)

    def test_check_performance_issues_like_wildcard(self):
        """Test detection of LIKE with leading wildcard."""
        validator = SQLValidator()

        query = "SELECT * FROM users WHERE name LIKE '%john%'"
        result = validator.check_performance_issues(query)

        assert any("wildcard" in suggestion.message.lower() for suggestion in result.suggestions)

    def test_check_security_issues_string_concatenation(self):
        """Test detection of potential SQL injection patterns."""
        validator = SQLValidator()

        # Test with UNION which is a common SQL injection pattern
        query = "SELECT * FROM users WHERE id = 1 UNION SELECT * FROM passwords"
        result = validator.check_security_issues(query)

        # Should detect UNION as dangerous keyword
        assert result is not None

    def test_check_security_issues_hardcoded_password(self):
        """Test detection of hardcoded password."""
        validator = SQLValidator()

        query = "SELECT * FROM users WHERE password = 'secret123'"
        result = validator.check_security_issues(query)

        assert result.has_errors() is True
        assert any("password" in issue.message.lower() for issue in result.issues)

    def test_analyze_query_plan(self):
        """Test query plan analysis."""
        validator = SQLValidator()

        query = "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id WHERE u.status = 'active' ORDER BY o.created_at"
        analysis = validator.analyze_query_plan(query)

        assert analysis["query_type"] == "SELECT"
        assert "USERS" in analysis["tables"]
        assert "ORDERS" in analysis["tables"]
        assert len(analysis["joins"]) > 0
        assert analysis["where_conditions"] > 0
        assert len(analysis["order_by_columns"]) > 0

    def test_complete_validation(self):
        """Test complete query validation."""
        validator = SQLValidator()

        query = "SELECT id, name FROM users WHERE status = 'active'"
        result = validator.validate_query(query)

        assert isinstance(result, SQLValidationResult)
        assert hasattr(result, "is_valid")
        assert hasattr(result, "issues")
        assert hasattr(result, "warnings")
        assert hasattr(result, "suggestions")


class TestDataIntegrityTester:
    """Test suite for DataIntegrityTester."""

    @pytest.fixture
    def mock_db_client(self):
        """Create mock database client."""
        client = AsyncMock()
        return client

    def test_initialization(self, mock_db_client):
        """Test integrity tester initialization."""
        tester = DataIntegrityTester(mock_db_client)
        assert tester.db == mock_db_client

    @pytest.mark.asyncio
    async def test_test_not_null_constraint(self, mock_db_client):
        """Test NOT NULL constraint validation."""
        # Mock query results - no NULL values
        mock_db_client.execute_query.return_value = []

        tester = DataIntegrityTester(mock_db_client)

        constraints = [
            IntegrityConstraint(
                constraint_type=ConstraintType.NOT_NULL,
                column="email",
                error_message="Email cannot be null",
            )
        ]

        results = await tester.test_data_integrity(table="users", constraints=constraints)

        assert results["table"] == "users"
        assert results["total_constraints"] == 1
        assert results["passed"] == 1
        assert results["failed"] == 0

    @pytest.mark.asyncio
    async def test_test_unique_constraint_violation(self, mock_db_client):
        """Test UNIQUE constraint violation detection."""
        # Mock query results - duplicate values found
        mock_db_client.execute_query.return_value = [("john@example.com", 2)]  # email appears twice

        tester = DataIntegrityTester(mock_db_client)

        constraints = [
            IntegrityConstraint(
                constraint_type=ConstraintType.UNIQUE,
                column="email",
                error_message="Email must be unique",
            )
        ]

        results = await tester.test_data_integrity(table="users", constraints=constraints)

        assert results["failed"] == 1
        assert results["total_violations"] > 0

    @pytest.mark.asyncio
    async def test_test_foreign_key_constraint(self, mock_db_client):
        """Test FOREIGN KEY constraint validation."""
        # Mock query results - orphan records found
        mock_db_client.execute_query.return_value = [(999,)]  # user_id 999 doesn't exist

        tester = DataIntegrityTester(mock_db_client)

        constraints = [
            IntegrityConstraint(
                constraint_type=ConstraintType.FOREIGN_KEY,
                column="user_id",
                reference_table="users",
                reference_column="id",
            )
        ]

        results = await tester.test_data_integrity(table="orders", constraints=constraints)

        assert results["failed"] == 1

    @pytest.mark.asyncio
    async def test_check_orphan_records(self, mock_db_client):
        """Test orphan record detection."""
        mock_db_client.execute_query.return_value = [
            (1, "Order 1", 999),  # user_id 999 doesn't exist
            (2, "Order 2", 999),
        ]

        tester = DataIntegrityTester(mock_db_client)

        results = await tester.check_orphan_records(
            table="orders", column="user_id", reference_table="users", reference_column="id"
        )

        assert results["orphan_count"] == 2
        assert results["has_orphans"] is True


class TestMigrationTester:
    """Test suite for MigrationTester."""

    @pytest.fixture
    def mock_db_client(self):
        """Create mock database client."""
        client = AsyncMock()
        return client

    def test_initialization(self, mock_db_client):
        """Test migration tester initialization."""
        tester = MigrationTester(mock_db_client)
        assert tester.db == mock_db_client

    @pytest.mark.asyncio
    async def test_test_migration_success(self, mock_db_client):
        """Test successful migration."""
        mock_db_client.execute_query.return_value = []

        tester = MigrationTester(mock_db_client)

        migration_sql = "CREATE TABLE test (id INTEGER PRIMARY KEY)"

        with patch("builtins.open", mock_open(read_data=migration_sql)):
            with patch("os.path.exists", return_value=True):
                result = await tester.test_migration(migration_script="test_migration.sql")

        assert isinstance(result, MigrationResult)
        assert result.status == MigrationStatus.SUCCESS
        assert result.execution_time >= 0

    @pytest.mark.asyncio
    async def test_test_migration_failure(self, mock_db_client):
        """Test failed migration."""
        mock_db_client.execute_query.side_effect = Exception("Syntax error")

        tester = MigrationTester(mock_db_client)

        migration_sql = "INVALID SQL"

        with patch("builtins.open", mock_open(read_data=migration_sql)):
            with patch("os.path.exists", return_value=True):
                result = await tester.test_migration(migration_script="test_migration.sql")

        assert result.status == MigrationStatus.FAILED
        assert result.error_message is not None

    @pytest.mark.asyncio
    async def test_test_migration_chain(self, mock_db_client):
        """Test migration chain execution."""
        mock_db_client.execute_query.return_value = []

        tester = MigrationTester(mock_db_client)

        migrations = [{"migration": "001_create_users.sql"}, {"migration": "002_create_orders.sql"}]

        with patch.object(tester, "test_migration", new_callable=AsyncMock) as mock_test:
            mock_test.return_value = MigrationResult(
                migration_name="test", status=MigrationStatus.SUCCESS, execution_time=0.1
            )

            results = await tester.test_migration_chain(migrations)

        assert results["total_migrations"] == 2
        assert results["completed"] is True

    def test_parse_migration_changes(self, mock_db_client):
        """Test migration change parsing."""
        tester = MigrationTester(mock_db_client)

        sql = "CREATE TABLE users (id INT); CREATE INDEX idx_name ON users(name);"
        changes = tester._parse_migration_changes(sql)

        assert "Create table(s)" in changes
        assert "Create index(es)" in changes


class TestDatabaseClient:
    """Test suite for DatabaseClient base class."""

    def test_initialization(self):
        """Test client initialization."""
        client = DatabaseClient("sqlite:///test.db")
        assert client.connection_string == "sqlite:///test.db"
        assert not client._connected

    def test_not_connected_raises_error(self):
        """Test that operations fail when not connected."""
        client = DatabaseClient()

        with pytest.raises(RuntimeError, match="not connected"):
            asyncio.run(client.execute_query("SELECT 1"))


class TestSQLiteClient:
    """Test suite for SQLiteClient."""

    @pytest.mark.asyncio
    async def test_connection(self):
        """Test SQLite connection."""
        client = SQLiteClient(":memory:")

        await client.connect()
        assert client._connected is True
        assert client._sqlite_conn is not None

        await client.disconnect()
        assert client._connected is False

    @pytest.mark.asyncio
    async def test_execute_query(self):
        """Test query execution."""
        client = SQLiteClient(":memory:")
        await client.connect()

        # Create table
        await client.execute_query("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")

        # Insert data
        await client.execute_query("INSERT INTO test (name) VALUES ('John')")

        # Query data
        results = await client.execute_query("SELECT * FROM test")

        assert len(results) == 1
        assert results[0][1] == "John"

        await client.disconnect()

    @pytest.mark.asyncio
    async def test_get_schema_info(self):
        """Test schema information retrieval."""
        client = SQLiteClient(":memory:")
        await client.connect()

        # Create tables
        await client.execute_query("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
        await client.execute_query("CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER)")
        await client.execute_query("CREATE INDEX idx_name ON users(name)")

        schema = await client.get_schema_info()

        assert "users" in schema["tables"]
        assert "orders" in schema["tables"]
        assert "users" in schema["columns"]
        assert "users" in schema["indexes"]

        await client.disconnect()

    @pytest.mark.asyncio
    async def test_validate_query(self):
        """Test query validation."""
        client = SQLiteClient(":memory:")
        await client.connect()

        result = await client.validate_query("SELECT * FROM users WHERE id = 1")

        assert "is_valid" in result
        assert "has_errors" in result
        assert "has_warnings" in result
        assert "query_plan" in result

        await client.disconnect()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        async with SQLiteClient(":memory:") as client:
            assert client._connected is True
            await client.execute_query("CREATE TABLE test (id INTEGER)")

        # After exit, should be disconnected
        assert client._connected is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
