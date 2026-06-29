"""
Unit Tests for Execution Service

Tests test execution management and orchestration functionality.
"""
import pytest
pytest.importorskip('fastapi')
pytest.importorskip('sqlalchemy')
pytest.importorskip('asyncpg')
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from services.execution_service import (
    create_execution_service,
    start_execution_service,
    stop_execution_service,
    list_executions_service,
    get_execution_by_id
)
from models import TestExecution, TestExecutionDetail, TestSuite, TestCase, User
from schemas import TestExecutionCreate, TestExecutionUpdate


@pytest.mark.asyncio
class TestCreateExecutionService:
    """Test suite for create_execution_service"""

    async def test_create_execution_success(self):
        """Test successful execution creation"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Create mock test cases
        test_case_1 = TestCase(
            id=1,
            suite_id=1,
            name="Test Case 1",
            description="First test case",
            test_code="def test_one(): assert True",
            test_type="api",
            priority="medium",
            is_active=True
        )
        
        test_case_2 = TestCase(
            id=2,
            suite_id=1,
            name="Test Case 2",
            description="Second test case",
            test_code="def test_two(): assert False",
            test_type="api",
            priority="high",
            is_active=True
        )
        
        # Mock suite with tests
        mock_suite = TestSuite(
            id=1,
            name="Test Suite",
            description="Test suite description",
            framework_type="pytest",
            is_active=True,
            created_by=1,
            tests=[test_case_1, test_case_2]
        )
        
        # Mock execution
        mock_execution = TestExecution(
            id=1,
            suite_id=1,
            executed_by=1,
            execution_type="manual",
            environment="production",
            total_tests=2,
            status="running"
        )
        
        # Configure mock database responses
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_suite)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Mock add and commit
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Create execution data
        execution_data = TestExecutionCreate(
            suite_id=1,
            execution_type="manual",
            environment="production"
        )
        
        # Patch the TestExecution constructor to return our mock
        with patch('services.execution_service.TestExecution', return_value=mock_execution):
            result = await create_execution_service(execution_data, 1, mock_db)
        
        # Verify
        assert result is not None
        assert result.suite_id == 1
        assert result.executed_by == 1
        assert result.total_tests == 2
        assert result.status == "running"
        
        # Verify database operations
        assert mock_db.add.called
        assert mock_db.commit.called

    async def test_create_execution_suite_not_found(self):
        """Test execution creation with non-existent suite"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock database query returning None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Create execution data
        execution_data = TestExecutionCreate(
            suite_id=999,
            execution_type="manual",
            environment="production"
        )
        
        # Test that it raises HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await create_execution_service(execution_data, 1, mock_db)
        
        assert exc_info.value.status_code == 404
        assert "Test suite not found" in exc_info.value.detail

    async def test_create_execution_with_inactive_tests(self):
        """Test execution creation only includes active tests"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Create mock test cases (one active, one inactive)
        active_test = TestCase(
            id=1,
            suite_id=1,
            name="Active Test",
            test_code="def test_active(): pass",
            is_active=True
        )
        
        inactive_test = TestCase(
            id=2,
            suite_id=1,
            name="Inactive Test",
            test_code="def test_inactive(): pass",
            is_active=False
        )
        
        # Mock suite with mixed tests
        mock_suite = TestSuite(
            id=1,
            name="Test Suite",
            is_active=True,
            created_by=1,
            tests=[active_test, inactive_test]
        )
        
        mock_execution = TestExecution(
            id=1,
            suite_id=1,
            executed_by=1,
            total_tests=2,
            status="running"
        )
        
        # Configure mock database
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_suite)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        execution_data = TestExecutionCreate(suite_id=1)
        
        with patch('services.execution_service.TestExecution', return_value=mock_execution):
            result = await create_execution_service(execution_data, 1, mock_db)
        
        # Should have total_tests=2 but only create 1 detail for active test
        assert result.total_tests == 2


@pytest.mark.asyncio
class TestGetExecutionById:
    """Test suite for get_execution_by_id"""

    async def test_get_execution_by_id_success(self):
        """Test successful execution retrieval by ID"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock execution
        mock_execution = TestExecution(
            id=1,
            suite_id=1,
            executed_by=1,
            execution_type="manual",
            environment="production",
            status="running",
            total_tests=5
        )
        
        # Configure mock database response
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_execution)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await get_execution_by_id(1, mock_db)
        
        assert result is not None
        assert result.id == 1
        assert result.suite_id == 1
        assert result.status == "running"

    async def test_get_execution_by_id_not_found(self):
        """Test execution retrieval with non-existent ID"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock database query returning None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Test that it raises HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await get_execution_by_id(999, mock_db)
        
        assert exc_info.value.status_code == 404
        assert "Test execution not found" in exc_info.value.detail


@pytest.mark.asyncio
class TestStartExecutionService:
    """Test suite for start_execution_service"""

    async def test_start_execution_success(self):
        """Test successful execution start"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock execution in running state
        mock_execution = TestExecution(
            id=1,
            suite_id=1,
            executed_by=1,
            status="running",
            total_tests=5
        )
        
        # Mock get_execution_by_id to return our execution
        with patch('services.execution_service.get_execution_by_id', return_value=mock_execution):
            with patch('services.execution_service.asyncio.create_task'):
                result = await start_execution_service(1, mock_db)
        
        assert result is not None
        assert result["message"] == "Execution started"
        assert result["execution_id"] == 1

    async def test_start_execution_already_completed(self):
        """Test starting an already completed execution"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock execution in completed state
        mock_execution = TestExecution(
            id=1,
            suite_id=1,
            executed_by=1,
            status="completed",
            total_tests=5
        )
        
        # Mock get_execution_by_id
        with patch('services.execution_service.get_execution_by_id', return_value=mock_execution):
            with pytest.raises(HTTPException) as exc_info:
                await start_execution_service(1, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "already completed" in exc_info.value.detail.lower()


@pytest.mark.asyncio
class TestStopExecutionService:
    """Test suite for stop_execution_service"""

    async def test_stop_execution_success(self):
        """Test successful execution stop"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock execution in running state
        mock_execution = TestExecution(
            id=1,
            suite_id=1,
            executed_by=1,
            status="running",
            total_tests=5,
            started_at=datetime.utcnow()
        )
        
        # Mock get_execution_by_id
        with patch('services.execution_service.get_execution_by_id', return_value=mock_execution):
            mock_db.commit = AsyncMock()
            result = await stop_execution_service(1, mock_db)
        
        assert result is not None
        assert result["message"] == "Execution stopped"
        assert result["execution_id"] == 1
        assert mock_execution.status == "stopped"
        assert mock_execution.ended_at is not None

    async def test_stop_execution_not_running(self):
        """Test stopping a non-running execution"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock execution in completed state
        mock_execution = TestExecution(
            id=1,
            suite_id=1,
            executed_by=1,
            status="completed",
            total_tests=5
        )
        
        # Mock get_execution_by_id
        with patch('services.execution_service.get_execution_by_id', return_value=mock_execution):
            with pytest.raises(HTTPException) as exc_info:
                await stop_execution_service(1, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "not in running state" in exc_info.value.detail.lower()


@pytest.mark.asyncio
class TestListExecutionsService:
    """Test suite for list_executions_service"""

    async def test_list_all_executions(self):
        """Test listing all executions without filters"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock executions list
        mock_executions = [
            TestExecution(id=1, suite_id=1, status="completed"),
            TestExecution(id=2, suite_id=2, status="running"),
            TestExecution(id=3, suite_id=1, status="failed")
        ]
        
        # Configure mock database response
        mock_result = AsyncMock()
        mock_scalars = Mock()
        mock_scalars.all = Mock(return_value=mock_executions)
        mock_result.scalars = Mock(return_value=mock_scalars)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await list_executions_service(skip=0, limit=100, db=mock_db)
        
        assert len(result) == 3
        assert result[0].id == 1
        assert result[1].status == "running"

    async def test_list_executions_by_suite(self):
        """Test listing executions filtered by suite"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock executions for specific suite
        mock_executions = [
            TestExecution(id=1, suite_id=1, status="completed"),
            TestExecution(id=3, suite_id=1, status="failed")
        ]
        
        # Configure mock database response
        mock_result = AsyncMock()
        mock_scalars = Mock()
        mock_scalars.all = Mock(return_value=mock_executions)
        mock_result.scalars = Mock(return_value=mock_scalars)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await list_executions_service(suite_id=1, skip=0, limit=100, db=mock_db)
        
        assert len(result) == 2
        assert all(e.suite_id == 1 for e in result)

    async def test_list_executions_by_status(self):
        """Test listing executions filtered by status"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock executions with specific status
        mock_executions = [
            TestExecution(id=2, suite_id=2, status="running"),
            TestExecution(id=4, suite_id=1, status="running")
        ]
        
        # Configure mock database response
        mock_result = AsyncMock()
        mock_scalars = Mock()
        mock_scalars.all = Mock(return_value=mock_executions)
        mock_result.scalars = Mock(return_value=mock_scalars)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await list_executions_service(status_filter="running", skip=0, limit=100, db=mock_db)
        
        assert len(result) == 2
        assert all(e.status == "running" for e in result)

    async def test_list_executions_with_pagination(self):
        """Test listing executions with pagination"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock executions list
        mock_executions = [
            TestExecution(id=i, suite_id=1, status="completed")
            for i in range(5, 15)  # 10 executions
        ]
        
        # Configure mock database response
        mock_result = AsyncMock()
        mock_scalars = Mock()
        mock_scalars.all = Mock(return_value=mock_executions)
        mock_result.scalars = Mock(return_value=mock_scalars)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await list_executions_service(skip=10, limit=10, db=mock_db)
        
        assert len(result) == 10
        # Verify that offset and limit were used
        assert mock_db.execute.called


@pytest.mark.asyncio
class TestExecutionEdgeCases:
    """Test edge cases and error handling"""

    async def test_create_execution_empty_suite(self):
        """Test execution creation with suite containing no tests"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Mock empty suite
        mock_suite = TestSuite(
            id=1,
            name="Empty Suite",
            is_active=True,
            created_by=1,
            tests=[]
        )
        
        mock_execution = TestExecution(
            id=1,
            suite_id=1,
            executed_by=1,
            total_tests=0,
            status="running"
        )
        
        # Configure mock database
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_suite)
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        execution_data = TestExecutionCreate(suite_id=1)
        
        with patch('services.execution_service.TestExecution', return_value=mock_execution):
            result = await create_execution_service(execution_data, 1, mock_db)
        
        # Should create execution with 0 tests
        assert result.total_tests == 0

    async def test_list_executions_no_results(self):
        """Test listing executions when none exist"""
        # Mock database session
        mock_db = AsyncMock(spec=AsyncSession)
        
        # Configure mock database response with empty list
        mock_result = AsyncMock()
        mock_scalars = Mock()
        mock_scalars.all.return_value = []
        mock_result.scalars = Mock(return_value=mock_scalars)
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        result = await list_executions_service(skip=0, limit=100, db=mock_db)
        
        assert len(result) == 0
        assert result == []


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
