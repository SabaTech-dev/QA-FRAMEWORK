"""
Unit Tests for Suite Service

Tests test suite management operations.
"""
import pytest
pytest.importorskip('asyncpg')
pytest.importorskip('redis')
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from services.suite_service import (
    create_suite_service,
    list_suites_service,
    get_suite_by_id,
    update_suite_service,
    delete_suite_service
)
from models import TestSuite
from schemas import TestSuiteCreate, TestSuiteUpdate


@pytest.mark.asyncio
class TestSuiteService:
    """Test suite for suite service operations"""

    async def test_create_suite_success(self):
        """Test successful suite creation"""
        # Mock database
        mock_db = AsyncMock()
        
        # Create suite data
        suite_data = TestSuiteCreate(
            name="Test Suite 1",
            description="A test suite",
            framework_type="pytest",
            config={"timeout": 300}
        )
        
        # Mock database operations
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Create suite
        result = await create_suite_service(suite_data, 1, mock_db)
        
        # Verify database operations were called
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    async def test_list_suites_empty(self):
        """Test listing suites when none exist"""
        # Mock database
        mock_db = AsyncMock()
        
        # Mock scalars result
        mock_scalars = Mock()
        mock_scalars.all = Mock(return_value=[])
        
        # Mock query result
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=mock_scalars)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # List suites
        suites = await list_suites_service(0, 100, mock_db)
        
        # Verify empty list
        assert suites == []

    async def test_list_suites_with_data(self):
        """Test listing suites with data"""
        # Mock database
        mock_db = AsyncMock()
        
        # Mock suites
        mock_suites = [
            TestSuite(id=1, name="Suite 1", framework_type="pytest", created_by=1),
            TestSuite(id=2, name="Suite 2", framework_type="pytest", created_by=1),
        ]
        
        # Mock scalars result
        mock_scalars = Mock()
        mock_scalars.all = Mock(return_value=mock_suites)
        
        # Mock query result
        mock_result = Mock()
        mock_result.scalars = Mock(return_value=mock_scalars)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # List suites
        suites = await list_suites_service(0, 100, mock_db)
        
        # Verify results
        assert len(suites) == 2
        assert suites[0].name == "Suite 1"
        assert suites[1].name == "Suite 2"

    async def test_get_suite_by_id_success(self):
        """Test getting a suite by ID"""
        # Mock database
        mock_db = AsyncMock()
        
        # Mock suite
        mock_suite = TestSuite(
            id=1,
            name="Test Suite",
            description="Description",
            framework_type="pytest",
            created_by=1
        )
        
        # Mock query result
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_suite)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Get suite
        suite = await get_suite_by_id(1, mock_db)
        
        # Verify result
        assert suite.id == 1
        assert suite.name == "Test Suite"

    async def test_get_suite_by_id_not_found(self):
        """Test getting a non-existent suite"""
        # Mock database
        mock_db = AsyncMock()
        
        # Mock query result returning None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Try to get suite
        with pytest.raises(Exception) as exc_info:
            await get_suite_by_id(999, mock_db)
        
        assert "not found" in str(exc_info.value)

    async def test_update_suite_success(self):
        """Test updating a suite"""
        # Mock database
        mock_db = AsyncMock()
        
        # Mock existing suite
        existing_suite = TestSuite(
            id=1,
            name="Old Name",
            description="Old Description",
            framework_type="pytest",
            created_by=1
        )
        
        # Mock get_suite_by_id to return existing suite
        with patch(
            'services.suite_service.get_suite_by_id',
            return_value=existing_suite
        ):
            # Update data
            update_data = TestSuiteUpdate(
                name="New Name",
                description="New Description"
            )
            
            # Mock database operations
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            # Update suite
            result = await update_suite_service(1, update_data, mock_db)
            
            # Verify database operations were called
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()

    async def test_delete_suite_soft_delete(self):
        """Test soft deleting a suite"""
        # Mock database
        mock_db = AsyncMock()
        
        # Mock existing suite
        existing_suite = TestSuite(
            id=1,
            name="Test Suite",
            description="Description",
            framework_type="pytest",
            created_by=1,
            is_active=True
        )
        
        # Mock get_suite_by_id to return existing suite
        with patch(
            'services.suite_service.get_suite_by_id',
            return_value=existing_suite
        ):
            # Mock database operations
            mock_db.commit = AsyncMock()
            
            # Delete suite
            await delete_suite_service(1, mock_db)
            
            # Verify soft delete
            assert existing_suite.is_active is False
            mock_db.commit.assert_called_once()


@pytest.mark.asyncio
class TestSuiteValidation:
    """Test suite data validation"""

    def test_suite_create_valid_data(self):
        """Test creating suite with valid data"""
        suite_data = TestSuiteCreate(
            name="Valid Suite",
            description="Valid description",
            framework_type="pytest",
            config={"key": "value"}
        )
        
        assert suite_data.name == "Valid Suite"
        assert suite_data.framework_type == "pytest"

    def test_suite_create_invalid_name_too_long(self):
        """Test creating suite with name too long"""
        with pytest.raises(Exception):
            TestSuiteCreate(
                name="x" * 101,  # Exceeds max_length=100
                description="Description",
                framework_type="pytest"
            )

    def test_suite_create_empty_name(self):
        """Test creating suite with empty name"""
        with pytest.raises(Exception):
            TestSuiteCreate(
                name="",  # Empty name
                description="Description",
                framework_type="pytest"
            )


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])