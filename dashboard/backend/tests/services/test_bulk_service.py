"""
Unit tests for bulk_service.py

Tests all bulk operations on test suites with mocked DB and cache.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


@pytest.fixture
def mock_cache_manager():
    """Mock cache_manager for all bulk service tests."""
    with patch("services.bulk_service.cache_manager") as mock_cache:
        mock_cache.invalidate_suite_cache = AsyncMock()
        yield mock_cache


class TestBulkDeleteSuites:
    """Tests for bulk_delete_suites function."""

    @pytest.mark.asyncio
    async def test_bulk_delete_success(self, mock_cache_manager):
        """Test successful bulk delete of multiple suites."""
        from services.bulk_service import bulk_delete_suites

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()

        # Mock suite 1
        mock_suite1 = MagicMock()
        mock_suite1.id = 1
        mock_suite1.name = "Test Suite 1"
        mock_suite1.is_active = True

        # Mock suite 2
        mock_suite2 = MagicMock()
        mock_suite2.id = 2
        mock_suite2.name = "Test Suite 2"
        mock_suite2.is_active = True

        # Setup execute to return suites
        async def mock_execute_side_effect(query):
            result = AsyncMock()
            if "1" in str(query):
                result.scalar_one_or_none.return_value = mock_suite1
            elif "2" in str(query):
                result.scalar_one_or_none.return_value = mock_suite2
            return result

        mock_db.execute = AsyncMock(side_effect=mock_execute_side_effect)

        result = await bulk_delete_suites([1, 2], mock_db, user_id=1)

        assert result["total_requested"] == 2
        assert len(result["successful"]) == 2
        assert len(result["failed"]) == 0
        assert len(result["not_found"]) == 0
        mock_db.commit.assert_called_once()
        assert mock_cache_manager.invalidate_suite_cache.call_count == 2

    @pytest.mark.asyncio
    async def test_bulk_delete_empty_list(self, mock_cache_manager):
        """Test bulk delete with empty suite_ids list."""
        from services.bulk_service import bulk_delete_suites

        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await bulk_delete_suites([], mock_db, user_id=1)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "No suite IDs provided" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_bulk_delete_exceeds_limit(self, mock_cache_manager):
        """Test bulk delete with more than 100 suites."""
        from services.bulk_service import bulk_delete_suites

        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await bulk_delete_suites(list(range(101)), mock_db, user_id=1)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot delete more than 100 suites" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_bulk_delete_duplicate_ids(self, mock_cache_manager):
        """Test bulk delete with duplicate suite IDs."""
        from services.bulk_service import bulk_delete_suites

        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await bulk_delete_suites([1, 2, 1, 3], mock_db, user_id=1)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Duplicate suite IDs detected" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_bulk_delete_mixed_results(self, mock_cache_manager):
        """Test bulk delete with mixed success and failure results."""
        from services.bulk_service import bulk_delete_suites

        mock_db = AsyncMock()

        # Mock suite 1 - success
        mock_suite1 = MagicMock()
        mock_suite1.id = 1
        mock_suite1.name = "Test Suite 1"
        mock_suite1.is_active = True

        # Mock suite 2 - not found
        mock_suite2 = MagicMock()
        mock_suite2.id = 2
        mock_suite2.is_active = False

        # Mock suite 3 - already deleted
        mock_suite3 = MagicMock()
        mock_suite3.id = 3
        mock_suite3.name = "Test Suite 3"
        mock_suite3.is_active = False

        async def mock_execute_side_effect(query):
            result = AsyncMock()
            suite_id_str = str(query)
            if "1" in suite_id_str:
                result.scalar_one_or_none.return_value = mock_suite1
            elif "2" in suite_id_str:
                result.scalar_one_or_none.return_value = None
            elif "3" in suite_id_str:
                result.scalar_one_or_none.return_value = mock_suite3
            return result

        mock_db.execute = AsyncMock(side_effect=mock_execute_side_effect)

        result = await bulk_delete_suites([1, 2, 3], mock_db, user_id=1)

        assert result["total_requested"] == 3
        assert len(result["successful"]) == 1
        assert len(result["not_found"]) == 1
        assert len(result["failed"]) == 1
        assert "already deleted" in result["failed"][0]["reason"]


class TestBulkExecuteSuites:
    """Tests for bulk_execute_suites function."""

    @pytest.mark.asyncio
    async def test_bulk_execute_success(self, mock_cache_manager):
        """Test successful bulk execute of multiple suites."""
        from services.bulk_service import bulk_execute_suites
        from models import TestSuite

        mock_db = AsyncMock()

        # Mock suite
        mock_suite = MagicMock()
        mock_suite.id = 1
        mock_suite.name = "Test Suite"
        mock_suite.is_active = True

        async def mock_execute_side_effect(query):
            result = AsyncMock()
            result.scalar_one_or_none.return_value = mock_suite
            return result

        mock_db.execute = AsyncMock(side_effect=mock_execute_side_effect)

        # Mock create_execution_service
        with patch("services.bulk_service.create_execution_service") as mock_create_exec:
            mock_execution = MagicMock()
            mock_execution.id = 101
            mock_execution.status = "pending"
            mock_create_exec.return_value = mock_execution

            result = await bulk_execute_suites(
                [1], mock_db, user_id=1,
                execution_type="manual",
                environment="production"
            )

            assert result["total_requested"] == 1
            assert len(result["successful"]) == 1
            assert result["successful"][0]["execution_id"] == 101
            assert len(result["failed"]) == 0

    @pytest.mark.asyncio
    async def test_bulk_execute_empty_list(self, mock_cache_manager):
        """Test bulk execute with empty suite_ids list."""
        from services.bulk_service import bulk_execute_suites

        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await bulk_execute_suites([], mock_db, user_id=1)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "No suite IDs provided" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_bulk_execute_exceeds_limit(self, mock_cache_manager):
        """Test bulk execute with more than 50 suites."""
        from services.bulk_service import bulk_execute_suites

        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await bulk_execute_suites(list(range(51)), mock_db, user_id=1)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot execute more than 50 suites" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_bulk_execute_invalid_execution_type(self, mock_cache_manager):
        """Test bulk execute with invalid execution_type."""
        from services.bulk_service import bulk_execute_suites

        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await bulk_execute_suites([1], mock_db, user_id=1, execution_type="invalid")

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid execution_type" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_bulk_execute_invalid_environment(self, mock_cache_manager):
        """Test bulk execute with invalid environment."""
        from services.bulk_service import bulk_execute_suites

        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await bulk_execute_suites([1], mock_db, user_id=1, environment="invalid")

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid environment" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_bulk_execute_not_found_suite(self, mock_cache_manager):
        """Test bulk execute with non-existent suite."""
        from services.bulk_service import bulk_execute_suites

        mock_db = AsyncMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        result = await bulk_execute_suites([999], mock_db, user_id=1)

        assert result["total_requested"] == 1
        assert len(result["successful"]) == 0
        assert len(result["not_found"]) == 1
        assert "not found or inactive" in result["not_found"][0]["reason"]


class TestBulkArchiveSuites:
    """Tests for bulk_archive_suites function."""

    @pytest.mark.asyncio
    async def test_bulk_archive_success(self, mock_cache_manager):
        """Test successful bulk archive of multiple suites."""
        from services.bulk_service import bulk_archive_suites

        mock_db = AsyncMock()

        # Mock suite
        mock_suite = MagicMock()
        mock_suite.id = 1
        mock_suite.name = "Test Suite"
        mock_suite.is_active = True
        mock_suite.config = {}

        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_suite
        mock_db.execute.return_value.scalars.return_value.all.return_value = []  # No active executions

        result = await bulk_archive_suites([1], mock_db, user_id=1)

        assert result["total_requested"] == 1
        assert len(result["successful"]) == 1
        assert result["successful"][0]["suite_id"] == 1
        assert mock_suite.is_active is False
        assert mock_suite.config.get("archived") is True
        assert mock_cache_manager.invalidate_suite_cache.call_count == 1

    @pytest.mark.asyncio
    async def test_bulk_archive_empty_list(self, mock_cache_manager):
        """Test bulk archive with empty suite_ids list."""
        from services.bulk_service import bulk_archive_suites

        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await bulk_archive_suites([], mock_db, user_id=1)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "No suite IDs provided" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_bulk_archive_exceeds_limit(self, mock_cache_manager):
        """Test bulk archive with more than 100 suites."""
        from services.bulk_service import bulk_archive_suites

        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await bulk_archive_suites(list(range(101)), mock_db, user_id=1)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot archive more than 100 suites" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_bulk_archive_duplicate_ids(self, mock_cache_manager):
        """Test bulk archive with duplicate suite IDs."""
        from services.bulk_service import bulk_archive_suites

        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await bulk_archive_suites([1, 2, 1], mock_db, user_id=1)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Duplicate suite IDs detected" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_bulk_archive_with_active_executions(self, mock_cache_manager):
        """Test bulk archive fails when suite has active executions."""
        from services.bulk_service import bulk_archive_suites

        mock_db = AsyncMock()

        # Mock suite
        mock_suite = MagicMock()
        mock_suite.id = 1
        mock_suite.name = "Test Suite"
        mock_suite.is_active = True
        mock_suite.config = {}

        # Mock active execution
        mock_execution = MagicMock()

        async def mock_execute_side_effect(query):
            result = AsyncMock()
            if "executions" in str(query):  # Active executions query
                result.scalars.return_value.all.return_value = [mock_execution]
            else:  # Suite query
                result.scalar_one_or_none.return_value = mock_suite
            return result

        mock_db.execute = AsyncMock(side_effect=mock_execute_side_effect)

        result = await bulk_archive_suites([1], mock_db, user_id=1)

        assert result["total_requested"] == 1
        assert len(result["successful"]) == 0
        assert len(result["failed"]) == 1
        assert "active execution" in result["failed"][0]["reason"].lower()

    @pytest.mark.asyncio
    async def test_bulk_archive_already_archived(self, mock_cache_manager):
        """Test bulk archive with already archived suite."""
        from services.bulk_service import bulk_archive_suites

        mock_db = AsyncMock()

        # Mock suite - already archived
        mock_suite = MagicMock()
        mock_suite.id = 1
        mock_suite.name = "Old Suite"
        mock_suite.is_active = False

        mock_db.execute.return_value.scalar_one_or_none.return_value = mock_suite

        result = await bulk_archive_suites([1], mock_db, user_id=1)

        assert result["total_requested"] == 1
        assert len(result["already_archived"]) == 1
        assert result["already_archived"][0]["suite_id"] == 1
        assert len(result["successful"]) == 0
