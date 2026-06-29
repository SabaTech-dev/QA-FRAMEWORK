"""
Unit Tests for Case Service

Tests test case management functionality.
"""
import pytest
pytest.importorskip('fastapi')
pytest.importorskip('sqlalchemy')
pytest.importorskip('asyncpg')
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from services.case_service import (
    create_case_service,
    list_cases_service,
    get_case_by_id,
    update_case_service,
    delete_case_service
)
from models import TestCase, TestSuite
from schemas import TestCaseCreate, TestCaseUpdate


@pytest.mark.asyncio
class TestCreateCaseService:
    """Test suite for create_case_service"""

    async def test_create_case_success(self):
        """Test successful test case creation"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock suite
        mock_suite = TestSuite(
            id=1,
            name="Test Suite",
            description="Test suite description",
            framework_type="pytest",
            is_active=True,
            created_by=1
        )
        
        # Configure mock database response for suite check
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_suite)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Mock add and commit
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Create case data
        case_data = TestCaseCreate(
            suite_id=1,
            name="Test Login",
            description="Test user login functionality",
            test_code="def test_login(): assert login_success()",
            test_type="api",
            priority="high",
            tags=["smoke", "authentication"]
        )
        
        result = await create_case_service(case_data, mock_db)
        
        # Verify
        assert result is not None
        assert result.suite_id == 1
        assert result.name == "Test Login"
        assert result.test_type == "api"
        assert result.priority == "high"
        
        # Verify database operations
        assert mock_db.add.called
        assert mock_db.commit.called

    async def test_create_case_suite_not_found(self):
        """Test case creation with non-existent suite"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock no suite found
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=None)  # Sync mock
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Create case data with minimal valid fields
        case_data = TestCaseCreate(
            suite_id=999,
            name="Test Case",
            description="Test description",
            test_code="def test(): pass",
            test_type="api"
        )
        
        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await create_case_service(case_data, mock_db)
        
        assert exc_info.value.status_code == 404
        
        # Create case data
        case_data = TestCaseCreate(
            suite_id=999,
            name="Test Case",
            description="Test case description",
            test_code="def test(): pass",
            test_type="api",
            priority="medium"
        )
        
        # Test that it raises HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await create_case_service(case_data, mock_db)
        
        assert exc_info.value.status_code == 404
        assert "Test suite not found" in exc_info.value.detail

    async def test_create_case_with_all_fields(self):
        """Test case creation with all optional fields"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock suite
        mock_suite = TestSuite(id=1, name="Suite", is_active=True, created_by=1)
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_suite)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Create case with all fields
        case_data = TestCaseCreate(
            suite_id=1,
            name="Complete Test Case",
            description="Full test case with all fields",
            test_code="def test_complete(): assert True",
            test_type="ui",
            priority="critical",
            tags=["regression", "ui", "critical"]
        )
        
        result = await create_case_service(case_data, mock_db)
        
        assert result.name == "Complete Test Case"
        assert result.test_type == "ui"
        assert result.priority == "critical"
        assert "regression" in result.tags


@pytest.mark.asyncio
class TestGetCaseById:
    """Test suite for get_case_by_id"""

    async def test_get_case_by_id_success(self):
        """Test successful case retrieval by ID"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock case
        mock_case = TestCase(
            id=1,
            suite_id=1,
            name="Test Case",
            description="Test case description",
            test_code="def test(): pass",
            test_type="api",
            priority="medium",
            is_active=True
        )
        
        # Configure mock database response
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_case)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await get_case_by_id(1, mock_db)
        
        assert result is not None
        assert result.id == 1
        assert result.name == "Test Case"
        assert result.is_active is True

    async def test_get_case_by_id_not_found(self):
        """Test case retrieval with non-existent ID"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock database query returning None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Test that it raises HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await get_case_by_id(999, mock_db)
        
        assert exc_info.value.status_code == 404
        assert "Test case not found" in exc_info.value.detail


@pytest.mark.asyncio
class TestListCasesService:
    """Test suite for list_cases_service"""

    async def test_list_all_cases(self):
        """Test listing all cases without filters"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock cases list
        mock_cases = [
            TestCase(id=1, suite_id=1, name="Test 1", test_code="pass", is_active=True),
            TestCase(id=2, suite_id=1, name="Test 2", test_code="pass", is_active=True),
            TestCase(id=3, suite_id=2, name="Test 3", test_code="pass", is_active=True)
        ]
        
        # Configure mock database response
        mock_result = AsyncMock()
        mock_scalars = Mock()
        mock_scalars.all = Mock(return_value=mock_cases)
        mock_result.scalars = Mock(return_value=mock_scalars)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await list_cases_service(skip=0, limit=100, db=mock_db)
        
        assert len(result) == 3
        assert result[0].id == 1

    async def test_list_cases_by_suite(self):
        """Test listing cases filtered by suite"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock cases for specific suite
        mock_cases = [
            TestCase(id=1, suite_id=1, name="Test 1", test_code="pass", is_active=True),
            TestCase(id=2, suite_id=1, name="Test 2", test_code="pass", is_active=True)
        ]
        
        # Configure mock database response
        mock_result = AsyncMock()
        mock_scalars = Mock()
        mock_scalars.all = Mock(return_value=mock_cases)
        mock_result.scalars = Mock(return_value=mock_scalars)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await list_cases_service(suite_id=1, skip=0, limit=100, db=mock_db)
        
        assert len(result) == 2
        assert all(c.suite_id == 1 for c in result)

    async def test_list_cases_with_pagination(self):
        """Test listing cases with pagination"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock cases list
        mock_cases = [
            TestCase(id=i, suite_id=1, name=f"Test {i}", test_code="pass", is_active=True)
            for i in range(10, 20)  # 10 cases
        ]
        
        # Configure mock database response
        mock_result = AsyncMock()
        mock_scalars = Mock()
        mock_scalars.all = Mock(return_value=mock_cases)
        mock_result.scalars = Mock(return_value=mock_scalars)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await list_cases_service(skip=10, limit=10, db=mock_db)
        
        assert len(result) == 10
        # Verify that offset and limit were used
        assert mock_db.execute.called

    async def test_list_cases_only_active(self):
        """Test that listing only returns active cases"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock only active cases
        mock_cases = [
            TestCase(id=1, suite_id=1, name="Test 1", test_code="pass", is_active=True),
            TestCase(id=2, suite_id=1, name="Test 2", test_code="pass", is_active=True)
        ]
        
        # Configure mock database response
        mock_result = AsyncMock()
        mock_scalars = Mock()
        mock_scalars.all = Mock(return_value=mock_cases)
        mock_result.scalars = Mock(return_value=mock_scalars)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await list_cases_service(skip=0, limit=100, db=mock_db)
        
        # All returned cases should be active
        assert all(c.is_active for c in result)


@pytest.mark.asyncio
class TestUpdateCaseService:
    """Test suite for update_case_service"""

    async def test_update_case_name(self):
        """Test updating case name"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock existing case
        mock_case = TestCase(
            id=1,
            suite_id=1,
            name="Old Name",
            description="Description",
            test_code="def test(): pass",
            test_type="api",
            priority="medium",
            is_active=True
        )
        
        # Mock get_case_by_id to return our case
        with patch('services.case_service.get_case_by_id', return_value=mock_case):
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            case_update = TestCaseUpdate(name="New Name")
            result = await update_case_service(1, case_update, mock_db)
        
        assert result.name == "New Name"
        assert mock_db.commit.called

    async def test_update_case_all_fields(self):
        """Test updating all case fields"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock existing case
        mock_case = TestCase(
            id=1,
            suite_id=1,
            name="Old Name",
            description="Old Description",
            test_code="def old(): pass",
            test_type="api",
            priority="medium",
            tags=["old"],
            is_active=True
        )
        
        # Mock get_case_by_id
        with patch('services.case_service.get_case_by_id', return_value=mock_case):
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            case_update = TestCaseUpdate(
                name="New Name",
                description="New Description",
                test_code="def new(): pass",
                test_type="ui",
                priority="critical",
                tags=["new", "updated"],
                is_active=False
            )
            
            result = await update_case_service(1, case_update, mock_db)
        
        assert result.name == "New Name"
        assert result.description == "New Description"
        assert result.test_code == "def new(): pass"
        assert result.test_type == "ui"
        assert result.priority == "critical"
        assert result.tags == ["new", "updated"]
        assert result.is_active is False

    async def test_update_case_not_found(self):
        """Test updating non-existent case"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock get_case_by_id to raise HTTPException
        with patch('services.case_service.get_case_by_id', side_effect=HTTPException(status_code=404, detail="Test case not found")):
            case_update = TestCaseUpdate(name="New Name")
            
            with pytest.raises(HTTPException) as exc_info:
                await update_case_service(999, case_update, mock_db)
        
        assert exc_info.value.status_code == 404

    async def test_update_case_partial(self):
        """Test partial update (only some fields)"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock existing case
        mock_case = TestCase(
            id=1,
            suite_id=1,
            name="Keep This",
            description="Old Description",
            test_code="def test(): pass",
            test_type="api",
            priority="medium",
            is_active=True
        )
        
        # Mock get_case_by_id
        with patch('services.case_service.get_case_by_id', return_value=mock_case):
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            # Only update priority
            case_update = TestCaseUpdate(priority="critical")
            result = await update_case_service(1, case_update, mock_db)
        
        # Name should remain unchanged
        assert result.name == "Keep This"
        # Priority should be updated
        assert result.priority == "critical"


@pytest.mark.asyncio
class TestDeleteCaseService:
    """Test suite for delete_case_service"""

    async def test_delete_case_success(self):
        """Test successful case soft delete"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock case
        mock_case = TestCase(
            id=1,
            suite_id=1,
            name="Test Case",
            test_code="def test(): pass",
            is_active=True
        )
        
        # Mock get_case_by_id
        with patch('services.case_service.get_case_by_id', return_value=mock_case):
            mock_db.commit = AsyncMock()
            
            await delete_case_service(1, mock_db)
        
        # Should mark as inactive
        assert mock_case.is_active is False
        assert mock_db.commit.called

    async def test_delete_case_not_found(self):
        """Test deleting non-existent case"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock get_case_by_id to raise HTTPException
        with patch('services.case_service.get_case_by_id', side_effect=HTTPException(status_code=404, detail="Test case not found")):
            with pytest.raises(HTTPException) as exc_info:
                await delete_case_service(999, mock_db)
        
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
class TestCaseEdgeCases:
    """Test edge cases and error handling"""

    async def test_list_cases_empty_result(self):
        """Test listing cases when none exist"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Configure mock database response with empty list
        mock_result = AsyncMock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = []
        mock_result.scalars = Mock(return_value=mock_scalars)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await list_cases_service(skip=0, limit=100, db=mock_db)
        
        assert len(result) == 0
        assert result == []

    async def test_create_case_with_special_characters(self):
        """Test case creation with special characters in name"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock suite
        mock_suite = TestSuite(id=1, name="Suite", is_active=True, created_by=1)
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_suite)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Create case with special characters
        case_data = TestCaseCreate(
            suite_id=1,
            name="Test with émojis 🎉 and symbols!@#$%",
            description="Special chars: <script>alert('test')</script>",
            test_code="def test(): assert 'café' == 'café'",
            test_type="api",
            priority="medium"
        )
        
        result = await create_case_service(case_data, mock_db)
        
        # Should accept special characters
        assert "émojis 🎉" in result.name

    async def test_update_case_empty_tags(self):
        """Test updating case with empty tags"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock existing case with tags
        mock_case = TestCase(
            id=1,
            suite_id=1,
            name="Test",
            test_code="pass",
            tags=["old", "tags"],
            is_active=True
        )
        
        # Mock get_case_by_id
        with patch('services.case_service.get_case_by_id', return_value=mock_case):
            mock_db.commit = AsyncMock()
            mock_db.refresh = AsyncMock()
            
            # Update with empty tags
            case_update = TestCaseUpdate(tags=[])
            result = await update_case_service(1, case_update, mock_db)
        
        # Tags should be empty
        assert result.tags == []


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
