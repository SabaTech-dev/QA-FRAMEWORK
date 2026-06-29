"""Unit tests for migration system."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# Skip all tests in this file if migration module is not available
pytest.importorskip("src.infrastructure.migration", reason="src.infrastructure.migration module not available. This test requires the migration system.")

from src.infrastructure.migration import (
    DataMigrator,
    UserMigrator,
    TestMigrator,
    MigrationReportGenerator,
)


class TestDataMigrator:
    """Test cases for DataMigrator base class."""

    @pytest.mark.asyncio
    async def test_create_default_tenant(self):
        """Test creating default tenant."""
        mock_session = AsyncMock()
        migrator = DataMigrator(mock_session, dry_run=False)

        # Mock tenant already exists
        with patch.object(
            migrator.db_session, "execute", new_callable=AsyncMock
        ) as mock_execute:
            mock_result = MagicMock()  # Use MagicMock for result (scalar_one_or_none is sync)
            mock_result.scalar_one_or_none.return_value = MagicMock(
                slug="default", id="default-id"
            )
            mock_execute.return_value = mock_result

            tenant = await migrator.create_default_tenant()

            assert tenant is not None
            assert tenant.slug == "default"

    @pytest.mark.asyncio
    async def test_create_default_tenant_creates_new(self):
        """Test creating a new default tenant when none exists."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        migrator = DataMigrator(mock_session, dry_run=False)

        # Mock tenant doesn't exist
        with patch.object(
            migrator.db_session, "execute", new_callable=AsyncMock
        ) as mock_execute:
            mock_result = MagicMock()  # Use MagicMock for result
            mock_result.scalar_one_or_none.return_value = None
            mock_execute.return_value = mock_result

            tenant = await migrator.create_default_tenant()

            assert tenant is not None
            assert tenant.slug == "default"
            mock_session.add.assert_called_once()
            mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_dry_run_creates_tenant(self):
        """Test that dry run mode simulates tenant creation."""
        mock_session = AsyncMock()
        migrator = DataMigrator(mock_session, dry_run=True)

        with patch.object(
            migrator.db_session, "execute", new_callable=AsyncMock
        ) as mock_execute:
            mock_result = MagicMock()  # Use MagicMock for result
            mock_result.scalar_one_or_none.return_value = None
            mock_execute.return_value = mock_result

            tenant = await migrator.create_default_tenant()

            assert tenant is None  # Dry run returns None
            # Execute is called once to check if tenant exists
            mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_stats_initialization(self):
        """Test that stats are initialized correctly."""
        mock_session = AsyncMock()
        migrator = DataMigrator(mock_session)

        assert migrator.stats["status"] == DataMigrator.MigrationStatus.PENDING
        assert migrator.stats["total_records"] == 0
        assert migrator.stats["migrated_records"] == 0
        assert migrator.stats["failed_records"] == 0
        assert migrator.stats["errors"] == []
        assert migrator.stats["warnings"] == []
        assert migrator.stats["started_at"] is None
        assert migrator.stats["completed_at"] is None

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test getting migration statistics."""
        mock_session = AsyncMock()
        migrator = DataMigrator(mock_session)

        stats = migrator.get_stats()

        assert isinstance(stats, dict)
        assert "status" in stats
        assert "total_records" in stats

    def test_add_warning(self):
        """Test adding a warning."""
        mock_session = AsyncMock()
        migrator = DataMigrator(mock_session)

        migrator.add_warning("Test warning")

        assert "Test warning" in migrator.stats["warnings"]

    def test_add_error(self):
        """Test adding an error."""
        mock_session = AsyncMock()
        migrator = DataMigrator(mock_session)

        migrator.add_error("Test error")

        assert "Test error" in migrator.stats["errors"]
        assert migrator.stats["failed_records"] == 1


class TestUserMigrator:
    """Test cases for UserMigrator class."""

    @pytest.mark.asyncio
    async def test_migrate_users_success(self):
        """Test successful user migration."""
        mock_session = AsyncMock()

        # Create mock user without tenant
        mock_user = MagicMock()
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.tenant_id = None
        mock_user.id = 1

        # Mock user migration
        with patch.object(
            mock_session, "execute", new_callable=AsyncMock
        ) as mock_execute:
            mock_result = MagicMock()  # Use MagicMock for result
            mock_result.scalars.return_value.all.return_value = [mock_user]
            mock_execute.return_value = mock_result

            migrator = UserMigrator(mock_session, dry_run=False)

            # Mock tenant
            default_tenant = MagicMock(slug="default", id="default-id")

            await migrator.migrate_users(default_tenant)

            assert migrator.stats["migrated_records"] == 1
            assert mock_user.tenant_id == "default-id"
            mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_migrate_users_dry_run(self):
        """Test user migration in dry-run mode."""
        mock_session = AsyncMock()

        # Create mock user without tenant
        mock_user = MagicMock()
        mock_user.username = "testuser"
        mock_user.tenant_id = None

        # Mock user migration
        with patch.object(
            mock_session, "execute", new_callable=AsyncMock
        ) as mock_execute:
            mock_result = MagicMock()  # Use MagicMock for result
            mock_result.scalars.return_value.all.return_value = [mock_user]
            mock_execute.return_value = mock_result

            migrator = UserMigrator(mock_session, dry_run=True)

            # Mock tenant
            default_tenant = MagicMock(slug="default", id="default-id")

            await migrator.migrate_users(default_tenant)

            assert migrator.stats["migrated_records"] == 1
            assert mock_user.tenant_id is None  # Should not be set in dry-run
            mock_session.commit.assert_not_awaited()

    def test_get_migrated_users(self):
        """Test getting migrated users."""
        mock_session = AsyncMock()
        migrator = UserMigrator(mock_session)

        test_users = [MagicMock(username="user1"), MagicMock(username="user2")]
        migrator.migrated_users = test_users

        result = migrator.get_migrated_users()

        assert result == test_users
        assert len(result) == 2


class TestTestMigrator:
    """Test cases for TestMigrator class."""

    @pytest.mark.asyncio
    async def test_migrate_tests_success(self):
        """Test successful test migration."""
        mock_session = AsyncMock()

        # Create mock test suite
        mock_suite = MagicMock()
        mock_suite.name = "Test Suite 1"
        mock_suite.id = 1

        # Create mock test case
        mock_case = MagicMock()
        mock_case.name = "Test Case 1"
        mock_case.id = 1

        # Mock migrations
        with patch.object(
            mock_session, "execute", new_callable=AsyncMock
        ) as mock_execute:
            mock_result = MagicMock()  # Use MagicMock for result
            mock_result.scalars.return_value.all.return_value = [mock_suite]
            mock_execute.return_value = mock_result

            migrator = TestMigrator(mock_session, dry_run=False)

            # Mock tenant
            default_tenant = MagicMock(slug="default", id="default-id")

            await migrator.migrate_tests(default_tenant)

            assert migrator.stats["migrated_records"] == 1
            assert len(migrator.migrated_suites) == 1
            mock_session.commit.assert_awaited_once()

    def test_get_migrated_suites(self):
        """Test getting migrated suites."""
        mock_session = AsyncMock()
        migrator = TestMigrator(mock_session)

        test_suites = [MagicMock(name="Suite 1"), MagicMock(name="Suite 2")]
        migrator.migrated_suites = test_suites

        result = migrator.get_migrated_suites()

        assert result == test_suites
        assert len(result) == 2


class TestMigrationReportGenerator:
    """Test cases for MigrationReportGenerator class."""

    def test_generate_report(self):
        """Test generating a migration report."""
        generator = MigrationReportGenerator()

        # Create mock migrators
        mock_migrator1 = MagicMock()
        mock_migrator1.__class__.__name__ = "UserMigrator"
        mock_migrator1.get_stats.return_value = {
            "total_records": 10,
            "migrated_records": 10,
            "failed_records": 0,
            "warnings": [],
            "errors": [],
        }

        mock_migrator2 = MagicMock()
        mock_migrator2.__class__.__name__ = "TestMigrator"
        mock_migrator2.get_stats.return_value = {
            "total_records": 5,
            "migrated_records": 5,
            "failed_records": 0,
            "warnings": [],
            "errors": [],
        }

        report = generator.generate(
            migrators=[mock_migrator1, mock_migrator2],
            overall_status=DataMigrator.MigrationStatus.COMPLETED,
            execution_time=10.5,
        )

        assert report["summary"]["overall_status"] == "completed"
        assert report["total_records"] == 15
        assert report["migrated_records"] == 15
        # Component names have "Migrator" suffix removed by _group_by_component
        assert report["by_component"]["User"]["total"] == 10
        assert report["by_component"]["Test"]["total"] == 5

    def test_save_to_file(self, tmp_path):
        """Test saving report to file."""
        generator = MigrationReportGenerator()

        mock_migrator = MagicMock()
        mock_migrator.__class__.__name__ = "UserMigrator"
        mock_migrator.get_stats.return_value = {
            "total_records": 10,
            "migrated_records": 10,
            "failed_records": 0,
        }

        report = generator.generate(
            migrators=[mock_migrator],
            overall_status=DataMigrator.MigrationStatus.COMPLETED,
            execution_time=5.0,
        )

        output_file = tmp_path / "report.json"
        generator.save_to_file(report, str(output_file))

        assert output_file.exists()

        # Verify content
        import json
        with open(output_file) as f:
            loaded = json.load(f)
            assert loaded["summary"]["overall_status"] == "completed"
            assert loaded["total_records"] == 10

    def test_print_console(self, capsys):
        """Test printing report to console."""
        generator = MigrationReportGenerator()

        mock_migrator = MagicMock()
        mock_migrator.__class__.__name__ = "TestMigrator"
        mock_migrator.get_stats.return_value = {
            "total_records": 5,
            "migrated_records": 5,
            "failed_records": 0,
        }

        report = generator.generate(
            migrators=[mock_migrator],
            overall_status=DataMigrator.MigrationStatus.COMPLETED,
            execution_time=3.2,
        )

        generator.print_console(report)

        captured = capsys.readouterr()
        assert "MIGRATION REPORT" in captured.out
        assert "completed" in captured.out
        assert "5" in captured.out

    def test_generate_recommendations_success(self):
        """Test generating recommendations for successful migration."""
        generator = MigrationReportGenerator()

        mock_migrator = MagicMock()
        mock_migrator.get_stats.return_value = {
            "warnings": [],
            "errors": [],
        }

        recommendations = generator._generate_recommendations(
            DataMigrator.MigrationStatus.COMPLETED, [mock_migrator]
        )

        assert len(recommendations) > 0
        assert any("completed successfully" in rec.lower() for rec in recommendations)

    def test_generate_recommendations_failure(self):
        """Test generating recommendations for failed migration."""
        generator = MigrationReportGenerator()

        mock_migrator = MagicMock()
        mock_migrator.get_stats.return_value = {
            "warnings": [],
            "errors": ["Database connection failed"],
        }

        recommendations = generator._generate_recommendations(
            DataMigrator.MigrationStatus.FAILED, [mock_migrator]
        )

        assert len(recommendations) > 0
        assert any("failed" in rec.lower() for rec in recommendations)
        assert any("database connection" in rec.lower() for rec in recommendations)

    def test_get_summary(self):
        """Test getting migration summary."""
        generator = MigrationReportGenerator()

        mock_migrator = MagicMock()
        mock_migrator.get_stats.return_value = {
            "total_records": 10,
            "migrated_records": 10,
        }

        report = generator.generate(
            migrators=[mock_migrator],
            overall_status=DataMigrator.MigrationStatus.COMPLETED,
            execution_time=5.0,
        )

        summary = generator.get_summary(report)

        assert "COMPLETED" in summary  # Status is uppercase in summary
        assert "10" in summary  # migrated_records
        assert "10" in summary  # total_records
        assert "5.0" in summary  # execution_time
