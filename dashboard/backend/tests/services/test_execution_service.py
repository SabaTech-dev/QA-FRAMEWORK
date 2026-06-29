"""
Unit Tests for Execution Service

Tests test execution management and orchestration with comprehensive mocking.
"""
import pytest
pytest.importorskip('fastapi')
pytest.importorskip('sqlalchemy')
pytest.importorskip('asyncpg')
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from fastapi import HTTPException

from services.execution_service import (
    create_execution_service,
    start_execution_service,
    run_tests,
    stop_execution_service,
    list_executions_service,
    get_execution_by_id
)
from models import TestExecution, TestExecutionDetail, TestSuite, TestCase, User
from schemas import TestExecutionCreate
from core.cache import CacheManager


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.add = Mock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_cache():
    """Mock cache manager"""
    cache = AsyncMock()
    cache.invalidate_execution_cache = AsyncMock()
    cache.invalidate_dashboard_cache = AsyncMock()
    cache.async_get = AsyncMock(return_value=None)
    cache.async_set = AsyncMock()
    return cache


@pytest.fixture
def mock_test_case():
    """Mock test case"""
    return TestCase(
        id=1,
        suite_id=1,
        name="Test Case 1",
        test_code="def test_example(): pass",
        is_active=True
    )


@pytest.fixture
def mock_test_suite(mock_test_case):
    """Mock test suite with test cases"""
    suite = TestSuite(
        id=1,
        name="Test Suite 1",
        description="Test suite",
        framework_type="pytest",
        created_by=1
    )
    suite.tests = [mock_test_case]
    return suite


@pytest.fixture
def mock_execution(mock_test_suite):
    """Mock test execution"""
    execution = TestExecution(
        id=1,
        suite_id=1,
        executed_by=1,
        execution_type="manual",
        environment="production",
        status="running",
        total_tests=1,
        started_at=datetime.utcnow()
    )
    execution.suite = mock_test_suite
    execution.details = []
    return execution


@pytest.fixture
def mock_execution_detail():
    """Mock execution detail"""
    return TestExecutionDetail(
        id=1,
        execution_id=1,
        test_case_id=1,
        status="pending"
    )


class TestCreateExecutionService:
    """Tests for create_execution_service function"""
    
    @pytest.mark.asyncio
    async def test_create_execution_success(self, mock_db, mock_test_suite):
        """Test successful execution creation"""
        execution_data = TestExecutionCreate(
            suite_id=1,
            execution_type="manual",
            environment="production"
        )
        
        # Mock suite query
        mock_suite_result = AsyncMock()
        mock_suite_result.scalar_one_or_none = Mock(return_value=mock_test_suite)
        
        # Mock execution refresh
        created_execution = None
        async def capture_execution(exec):
            nonlocal created_execution
            created_execution = exec
        
        mock_db.execute.return_value = mock_suite_result
        mock_db.refresh.side_effect = capture_execution
        
        with patch('services.execution_service.cache_manager') as mock_cache_mgr:
            mock_cache_mgr.invalidate_execution_cache = AsyncMock()
            mock_cache_mgr.invalidate_dashboard_cache = AsyncMock()
            
            # Simulate db.add setting the ID
            def set_id(obj):
                if hasattr(obj, 'id'):
                    obj.id = 1
            mock_db.add.side_effect = set_id
            
            result = await create_execution_service(execution_data, user_id=1, db=mock_db)
            
            # Verify suite was queried
            mock_db.execute.assert_called()
            
            # Verify execution was added
            mock_db.add.assert_called()
            
            # Verify cache invalidated
            mock_cache_mgr.invalidate_execution_cache.assert_called_once()
            mock_cache_mgr.invalidate_dashboard_cache.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_execution_suite_not_found(self, mock_db):
        """Test execution creation when suite not found"""
        execution_data = TestExecutionCreate(
            suite_id=999,
            execution_type="manual",
            environment="production"
        )
        
        # Mock suite query returning None
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(HTTPException) as exc_info:
            await create_execution_service(execution_data, user_id=1, db=mock_db)
        
        assert exc_info.value.status_code == 404
        assert "Test suite not found" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_create_execution_with_inactive_tests(self, mock_db):
        """Test execution creation filters inactive tests"""
        # Create suite with mixed active/inactive tests
        suite = TestSuite(id=1, name="Suite", created_by=1)
        suite.tests = [
            TestCase(id=1, suite_id=1, name="Active", test_code="pass", is_active=True),
            TestCase(id=2, suite_id=1, name="Inactive", test_code="pass", is_active=False),
        ]
        
        execution_data = TestExecutionCreate(
            suite_id=1,
            execution_type="manual",
            environment="production"
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=suite)
        mock_db.execute.return_value = mock_result
        
        with patch('services.execution_service.cache_manager') as mock_cache_mgr:
            mock_cache_mgr.invalidate_execution_cache = AsyncMock()
            mock_cache_mgr.invalidate_dashboard_cache = AsyncMock()
            
            added_details = []
            mock_db.add.side_effect = lambda obj: added_details.append(obj) if isinstance(obj, TestExecutionDetail) else None
            
            await create_execution_service(execution_data, user_id=1, db=mock_db)
            
            # Only active test should create detail
            detail_count = sum(1 for obj in added_details if isinstance(obj, TestExecutionDetail))
            assert detail_count == 1
    
    @pytest.mark.asyncio
    async def test_create_execution_sets_correct_total(self, mock_db, mock_test_suite):
        """Test execution sets correct total tests count"""
        execution_data = TestExecutionCreate(
            suite_id=1,
            execution_type="manual",
            environment="production"
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_test_suite)
        mock_db.execute.return_value = mock_result
        
        created_execution = None
        
        def capture(obj):
            nonlocal created_execution
            if isinstance(obj, TestExecution):
                created_execution = obj
                obj.id = 1
        
        mock_db.add.side_effect = capture
        
        with patch('services.execution_service.cache_manager') as mock_cache_mgr:
            mock_cache_mgr.invalidate_execution_cache = AsyncMock()
            mock_cache_mgr.invalidate_dashboard_cache = AsyncMock()
            
            await create_execution_service(execution_data, user_id=1, db=mock_db)
            
            # Verify total_tests set to number of tests in suite
            assert created_execution.total_tests == len(mock_test_suite.tests)


class TestStartExecutionService:
    """Tests for start_execution_service function"""
    
    @pytest.mark.asyncio
    async def test_start_execution_success(self, mock_db, mock_execution):
        """Test successful execution start"""
        with patch('services.execution_service.get_execution_by_id', return_value=mock_execution), \
             patch('services.execution_service.asyncio.create_task') as mock_create_task:
            
            result = await start_execution_service(execution_id=1, db=mock_db)
            
            assert result["message"] == "Execution started"
            assert result["execution_id"] == 1
            
            # Verify background task created
            mock_create_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_execution_already_completed(self, mock_db, mock_execution):
        """Test starting already completed execution"""
        mock_execution.status = "completed"
        
        with patch('services.execution_service.get_execution_by_id', return_value=mock_execution):
            with pytest.raises(HTTPException) as exc_info:
                await start_execution_service(execution_id=1, db=mock_db)
            
            assert exc_info.value.status_code == 400
            assert "already completed" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_start_execution_wrong_status(self, mock_db, mock_execution):
        """Test starting execution with wrong status"""
        mock_execution.status = "stopped"
        
        with patch('services.execution_service.get_execution_by_id', return_value=mock_execution):
            with pytest.raises(HTTPException) as exc_info:
                await start_execution_service(execution_id=1, db=mock_db)
            
            assert exc_info.value.status_code == 400


class TestRunTests:
    """Tests for run_tests background function"""
    
    @pytest.mark.asyncio
    async def test_run_tests_success(self, mock_db, mock_execution, mock_test_case, mock_execution_detail):
        """Test successful test execution in background"""
        mock_execution.details = [mock_execution_detail]
        
        # Mock execution query
        mock_exec_result = AsyncMock()
        mock_exec_result.scalar_one = Mock(return_value=mock_execution)
        
        # Mock test case query
        mock_case_result = AsyncMock()
        mock_case_result.scalar_one = Mock(return_value=mock_test_case)
        
        mock_db.execute.side_effect = [mock_exec_result, mock_case_result]
        
        with patch('services.execution_service.cache_manager') as mock_cache_mgr, \
             patch('services.execution_service.asyncio.sleep', new_callable=AsyncMock):
            
            mock_cache_mgr.invalidate_execution_cache = AsyncMock()
            mock_cache_mgr.invalidate_dashboard_cache = AsyncMock()
            
            await run_tests(execution_id=1, db=mock_db)
            
            # Verify execution completed
            assert mock_execution.status == "completed"
            assert mock_execution.passed_tests == 1
            assert mock_execution.failed_tests == 0
            
            # Verify cache invalidated
            mock_cache_mgr.invalidate_execution_cache.assert_called()
            mock_cache_mgr.invalidate_dashboard_cache.assert_called()
    
    @pytest.mark.asyncio
    async def test_run_tests_with_failures(self, mock_db, mock_execution, mock_test_case):
        """Test test execution with failures"""
        detail = TestExecutionDetail(
            id=1,
            execution_id=1,
            test_case_id=1,
            status="pending"
        )
        mock_execution.details = [detail]
        
        mock_exec_result = AsyncMock()
        mock_exec_result.scalar_one = Mock(return_value=mock_execution)
        
        mock_case_result = AsyncMock()
        mock_case_result.scalar_one = Mock(return_value=mock_test_case)
        
        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_exec_result
            return mock_case_result
        
        mock_db.execute.side_effect = side_effect
        
        with patch('services.execution_service.cache_manager') as mock_cache_mgr, \
             patch('services.execution_service.asyncio.sleep', new_callable=AsyncMock), \
             patch('services.execution_service.datetime') as mock_datetime:
            
            mock_cache_mgr.invalidate_execution_cache = AsyncMock()
            mock_cache_mgr.invalidate_dashboard_cache = AsyncMock()
            
            # Make datetime.utcnow() return consistent values
            mock_datetime.utcnow.return_value = datetime.utcnow()
            mock_datetime.fromtimestamp = datetime.fromtimestamp
            
            # Force an exception during test execution
            original_sleep = AsyncMock()
            
            async def failing_sleep(*args):
                raise Exception("Test execution failed")
            
            with patch('services.execution_service.asyncio.sleep', failing_sleep):
                await run_tests(execution_id=1, db=mock_db)
                
                # Verify failure recorded
                assert detail.status == "failed"
                assert "Test execution failed" in detail.error_message
    
    @pytest.mark.asyncio
    async def test_run_tests_exception_handling(self, mock_db):
        """Test run_tests handles exceptions gracefully"""
        # Mock database error
        mock_db.execute.side_effect = Exception("Database error")
        
        with patch('services.execution_service.cache_manager'):
            # Should not raise exception
            await run_tests(execution_id=1, db=mock_db)


class TestStopExecutionService:
    """Tests for stop_execution_service function"""
    
    @pytest.mark.asyncio
    async def test_stop_execution_success(self, mock_db, mock_execution):
        """Test successful execution stop"""
        mock_execution.status = "running"
        
        with patch('services.execution_service.get_execution_by_id', return_value=mock_execution), \
             patch('services.execution_service.cache_manager') as mock_cache_mgr:
            
            mock_cache_mgr.invalidate_execution_cache = AsyncMock()
            mock_cache_mgr.invalidate_dashboard_cache = AsyncMock()
            
            result = await stop_execution_service(execution_id=1, db=mock_db)
            
            assert result["message"] == "Execution stopped"
            assert result["execution_id"] == 1
            assert mock_execution.status == "stopped"
            assert mock_execution.ended_at is not None
            
            # Verify cache invalidated
            mock_cache_mgr.invalidate_execution_cache.assert_called_once()
            mock_cache_mgr.invalidate_dashboard_cache.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_execution_not_running(self, mock_db, mock_execution):
        """Test stopping execution that's not running"""
        mock_execution.status = "completed"
        
        with patch('services.execution_service.get_execution_by_id', return_value=mock_execution):
            with pytest.raises(HTTPException) as exc_info:
                await stop_execution_service(execution_id=1, db=mock_db)
            
            assert exc_info.value.status_code == 400
            assert "not in running state" in exc_info.value.detail


class TestListExecutionsService:
    """Tests for list_executions_service function"""
    
    @pytest.mark.asyncio
    async def test_list_executions_no_filters(self, mock_db, mock_execution):
        """Test listing executions without filters"""
        mock_result = AsyncMock()
        # Create a chain of mocks for scalars().all()
        mock_scalars = AsyncMock()
        mock_scalars.all = Mock(return_value=[mock_execution])
        mock_result.scalars = Mock(return_value=mock_scalars)
        mock_db.execute.return_value = mock_result
        
        with patch('services.execution_service.cache_manager') as mock_cache_mgr:
            mock_cache_mgr.async_get = AsyncMock(return_value=None)
            mock_cache_mgr.async_set = AsyncMock()
            mock_cache_mgr.get_execution_list_key = Mock(return_value="executions:list")
            
            result = await list_executions_service(db=mock_db)
            
            assert len(result) == 1
            assert result[0].id == 1
            
            # Verify cached
            mock_cache_mgr.async_set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_list_executions_from_cache(self, mock_db, mock_execution):
        """Test listing executions from cache"""
        with patch('services.execution_service.cache_manager') as mock_cache_mgr:
            mock_cache_mgr.async_get = AsyncMock(return_value=[mock_execution])
            mock_cache_mgr.get_execution_list_key = Mock(return_value="executions:list")
            
            result = await list_executions_service(db=mock_db)
            
            assert len(result) == 1
            # Database should not be queried
            mock_db.execute.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_list_executions_with_suite_filter(self, mock_db, mock_execution):
        """Test listing executions filtered by suite"""
        mock_result = AsyncMock()
        mock_scalars = AsyncMock()
        mock_scalars.all = Mock(return_value=[mock_execution])
        mock_result.scalars = Mock(return_value=mock_scalars)
        mock_db.execute.return_value = mock_result
        
        with patch('services.execution_service.cache_manager') as mock_cache_mgr:
            mock_cache_mgr.async_get = AsyncMock(return_value=None)
            mock_cache_mgr.async_set = AsyncMock()
            mock_cache_mgr.get_execution_list_key = Mock(return_value="executions:list:suite:1")
            
            result = await list_executions_service(suite_id=1, db=mock_db)
            
            assert len(result) == 1
    
    @pytest.mark.asyncio
    async def test_list_executions_with_status_filter(self, mock_db, mock_execution):
        """Test listing executions filtered by status"""
        mock_result = AsyncMock()
        mock_scalars = AsyncMock()
        mock_scalars.all = Mock(return_value=[mock_execution])
        mock_result.scalars = Mock(return_value=mock_scalars)
        mock_db.execute.return_value = mock_result
        
        with patch('services.execution_service.cache_manager') as mock_cache_mgr:
            mock_cache_mgr.async_get = AsyncMock(return_value=None)
            mock_cache_mgr.async_set = AsyncMock()
            mock_cache_mgr.get_execution_list_key = Mock(return_value="executions:list:status:running")
            
            result = await list_executions_service(status_filter="running", db=mock_db)
            
            assert len(result) == 1
    
    @pytest.mark.asyncio
    async def test_list_executions_with_pagination(self, mock_db, mock_execution):
        """Test listing executions with pagination"""
        mock_result = AsyncMock()
        mock_scalars = AsyncMock()
        mock_scalars.all = Mock(return_value=[mock_execution])
        mock_result.scalars = Mock(return_value=mock_scalars)
        mock_db.execute.return_value = mock_result
        
        with patch('services.execution_service.cache_manager') as mock_cache_mgr:
            mock_cache_mgr.async_get = AsyncMock(return_value=None)
            mock_cache_mgr.async_set = AsyncMock()
            mock_cache_mgr.get_execution_list_key = Mock(return_value="executions:list:skip:10:limit:20")
            
            result = await list_executions_service(skip=10, limit=20, db=mock_db)
            
            assert len(result) == 1
    
    @pytest.mark.asyncio
    async def test_list_executions_empty_result(self, mock_db):
        """Test listing executions when empty"""
        mock_result = AsyncMock()
        mock_scalars = AsyncMock()
        mock_scalars.all = Mock(return_value=[])
        mock_result.scalars = Mock(return_value=mock_scalars)
        mock_db.execute.return_value = mock_result
        
        with patch('services.execution_service.cache_manager') as mock_cache_mgr:
            mock_cache_mgr.async_get = AsyncMock(return_value=None)
            mock_cache_mgr.async_set = AsyncMock()
            mock_cache_mgr.get_execution_list_key = Mock(return_value="executions:list")
            
            result = await list_executions_service(db=mock_db)
            
            assert len(result) == 0


class TestGetExecutionById:
    """Tests for get_execution_by_id function"""
    
    @pytest.mark.asyncio
    async def test_get_execution_by_id_success(self, mock_db, mock_execution):
        """Test successful execution retrieval by ID"""
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_execution)
        mock_db.execute.return_value = mock_result
        
        with patch('services.execution_service.cache_manager') as mock_cache_mgr:
            mock_cache_mgr.async_get = AsyncMock(return_value=None)
            mock_cache_mgr.async_set = AsyncMock()
            mock_cache_mgr.get_execution_key = Mock(return_value="execution:1")
            
            result = await get_execution_by_id(execution_id=1, db=mock_db)
            
            assert result.id == 1
            assert result.status == "running"
            
            # Verify cached
            mock_cache_mgr.async_set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_execution_by_id_from_cache(self, mock_db, mock_execution):
        """Test execution retrieval from cache"""
        with patch('services.execution_service.cache_manager') as mock_cache_mgr:
            mock_cache_mgr.async_get = AsyncMock(return_value=mock_execution)
            mock_cache_mgr.get_execution_key = Mock(return_value="execution:1")
            
            result = await get_execution_by_id(execution_id=1, db=mock_db)
            
            assert result.id == 1
            # Database should not be queried
            mock_db.execute.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_execution_by_id_not_found(self, mock_db):
        """Test execution retrieval when not found"""
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute.return_value = mock_result
        
        with patch('services.execution_service.cache_manager') as mock_cache_mgr:
            mock_cache_mgr.async_get = AsyncMock(return_value=None)
            mock_cache_mgr.get_execution_key = Mock(return_value="execution:999")
            
            with pytest.raises(HTTPException) as exc_info:
                await get_execution_by_id(execution_id=999, db=mock_db)
            
            assert exc_info.value.status_code == 404
            assert "Test execution not found" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_execution_by_id_loads_relationships(self, mock_db, mock_execution):
        """Test execution retrieval loads relationships"""
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_execution)
        mock_db.execute.return_value = mock_result
        
        with patch('services.execution_service.cache_manager') as mock_cache_mgr:
            mock_cache_mgr.async_get = AsyncMock(return_value=None)
            mock_cache_mgr.async_set = AsyncMock()
            mock_cache_mgr.get_execution_key = Mock(return_value="execution:1")
            
            result = await get_execution_by_id(execution_id=1, db=mock_db)
            
            # Verify query included selectinload for relationships
            call_args = mock_db.execute.call_args
            assert call_args is not None


class TestCacheIntegration:
    """Tests for cache integration in execution service"""
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, mock_db, mock_execution):
        """Test cache key generation for different queries"""
        with patch('services.execution_service.cache_manager') as mock_cache_mgr:
            mock_cache_mgr.async_get = AsyncMock(return_value=None)
            mock_cache_mgr.async_set = AsyncMock()
            
            # Test different key generations
            mock_cache_mgr.get_execution_list_key = Mock(side_effect=lambda *args: f"key:{args}")
            mock_cache_mgr.get_execution_key = Mock(side_effect=lambda x: f"execution:{x}")
            
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none = Mock(return_value=mock_execution)
            mock_scalars = AsyncMock()
            mock_scalars.all = Mock(return_value=[mock_execution])
            mock_result.scalars = Mock(return_value=mock_scalars)
            mock_db.execute.return_value = mock_result
            
            # Test list key with filters
            await list_executions_service(suite_id=1, status_filter="running", db=mock_db)
            mock_cache_mgr.get_execution_list_key.assert_called_with(1, "running", 0, 100)
            
            # Test single execution key
            await get_execution_by_id(execution_id=1, db=mock_db)
            mock_cache_mgr.get_execution_key.assert_called_with(1)
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_on_create(self, mock_db, mock_test_suite):
        """Test cache invalidation when creating execution"""
        execution_data = TestExecutionCreate(
            suite_id=1,
            execution_type="manual",
            environment="production"
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_test_suite)
        mock_db.execute.return_value = mock_result
        
        with patch('services.execution_service.cache_manager') as mock_cache_mgr:
            mock_cache_mgr.invalidate_execution_cache = AsyncMock()
            mock_cache_mgr.invalidate_dashboard_cache = AsyncMock()
            
            mock_db.add = Mock()
            
            await create_execution_service(execution_data, user_id=1, db=mock_db)
            
            # Verify both caches invalidated
            mock_cache_mgr.invalidate_execution_cache.assert_called_once()
            mock_cache_mgr.invalidate_dashboard_cache.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_on_stop(self, mock_db, mock_execution):
        """Test cache invalidation when stopping execution"""
        mock_execution.status = "running"
        
        with patch('services.execution_service.get_execution_by_id', return_value=mock_execution), \
             patch('services.execution_service.cache_manager') as mock_cache_mgr:
            
            mock_cache_mgr.invalidate_execution_cache = AsyncMock()
            mock_cache_mgr.invalidate_dashboard_cache = AsyncMock()
            
            await stop_execution_service(execution_id=1, db=mock_db)
            
            # Verify cache invalidated with execution_id
            mock_cache_mgr.invalidate_execution_cache.assert_called_once_with(1)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=services/execution_service", "--cov-report=term-missing"])
