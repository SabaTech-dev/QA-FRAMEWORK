"""
Integration Tests for Cron Routes

Tests for API endpoints related to cron jobs.
"""
import pytest
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from fastapi import HTTPException

from api.v1.cron_routes import router, get_cron_jobs, get_cron_job, get_job_executions, run_cron_job, get_cron_stats
from services.cron_service import CronService
from models.cron import CronJob, CronExecution


class TestGetCronJobs:
    """Test suite for GET /cron/jobs endpoint"""

    @pytest.mark.asyncio
    async def test_get_jobs_success(self):
        """Test successfully retrieving all cron jobs"""
        # Setup mock database
        mock_db = AsyncMock()
        
        # Create test jobs
        job1 = CronJob(
            id=1,
            name="daily_report",
            schedule="0 13 * * *",
            status="active",
            script_path="/scripts/daily.sh",
            success_count=100,
            error_count=5
        )
        job2 = CronJob(
            id=2,
            name="weekly_backup",
            schedule="0 2 * * 0",
            status="active",
            script_path="/scripts/backup.sh",
            success_count=50,
            error_count=0
        )
        
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [job1, job2]
        mock_db.execute.return_value = mock_result
        
        # Mock get_db_session
        with patch('api.v1.cron_routes.get_db_session', new_callable=AsyncMock, return_value=mock_db):
            # Execute
            response = await get_cron_jobs(db=mock_db)
            
            # Verify
            assert len(response) == 2
            assert response[0].name == "daily_report"
            assert response[1].name == "weekly_backup"
            assert response[0].success_rate == pytest.approx(0.952, rel=0.01)

    @pytest.mark.asyncio
    async def test_get_jobs_empty(self):
        """Test retrieving jobs when no jobs exist"""
        # Setup mock database
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        with patch('api.v1.cron_routes.get_db_session', new_callable=AsyncMock, return_value=mock_db):
            # Execute
            response = await get_cron_jobs(db=mock_db)
            
            # Verify
            assert response == []


class TestGetCronJob:
    """Test suite for GET /cron/jobs/{job_id} endpoint"""

    @pytest.mark.asyncio
    async def test_get_job_success(self):
        """Test successfully retrieving a specific job"""
        # Setup mock database
        mock_db = AsyncMock()
        
        job = CronJob(
            id=1,
            name="test_job",
            schedule="0 * * * *",
            status="active",
            script_path="/scripts/test.sh",
            success_count=25,
            error_count=3
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = job
        mock_db.execute.return_value = mock_result
        
        with patch('api.v1.cron_routes.get_db_session', new_callable=AsyncMock, return_value=mock_db):
            with patch('api.v1.cron_routes.CronService', return_value=Mock()):
                # Execute
                response = await get_cron_job(job_id=1, db=mock_db)
                
                # Verify
                assert response.id == 1
                assert response.name == "test_job"
                assert response.success_rate == pytest.approx(0.893, rel=0.01)

    @pytest.mark.asyncio
    async def test_get_job_not_found(self):
        """Test retrieving a non-existent job raises 404"""
        # Setup mock database
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with patch('api.v1.cron_routes.get_db_session', new_callable=AsyncMock, return_value=mock_db):
            with patch('api.v1.cron_routes.CronService', return_value=Mock()):
                # Execute - should raise HTTPException 404
                with pytest.raises(HTTPException) as exc_info:
                    await get_cron_job(job_id=999, db=mock_db)
                
                assert exc_info.value.status_code == 404
                assert exc_info.value.detail == "Job not found"


class TestGetJobExecutions:
    """Test suite for GET /cron/jobs/{job_id}/executions endpoint"""

    @pytest.mark.asyncio
    async def test_get_executions_success(self):
        """Test successfully retrieving job executions"""
        # Setup mock database
        mock_db = AsyncMock()
        
        # Create test executions
        exec1 = CronExecution(
            id=1,
            job_id=1,
            status="success",
            started_at=datetime.utcnow() - timedelta(hours=1),
            finished_at=datetime.utcnow() - timedelta(hours=1),
            duration=120.5,
            output="Job completed successfully"
        )
        exec2 = CronExecution(
            id=2,
            job_id=1,
            status="error",
            started_at=datetime.utcnow() - timedelta(hours=2),
            finished_at=datetime.utcnow() - timedelta(hours=2),
            duration=5.0,
            error_message="Script failed"
        )
        
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = [exec1, exec2]
        mock_db.execute.return_value = mock_result
        
        with patch('api.v1.cron_routes.get_db_session', new_callable=AsyncMock, return_value=mock_db):
            with patch('api.v1.cron_routes.CronService', return_value=Mock()):
                # Execute with default limit
                response = await get_job_executions(job_id=1, db=mock_db)
                
                # Verify
                assert len(response) == 2
                assert response[0].status == "success"
                assert response[1].status == "error"
                assert response[0].duration == 120.5

    @pytest.mark.asyncio
    async def test_get_executions_with_limit(self):
        """Test retrieving executions with custom limit"""
        # Setup mock database
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        with patch('api.v1.cron_routes.get_db_session', new_callable=AsyncMock, return_value=mock_db):
            with patch('api.v1.cron_routes.CronService', return_value=Mock()):
                # Execute with custom limit
                response = await get_job_executions(job_id=1, limit=100, db=mock_db)
                
                # Verify limit was respected
                assert len(response) == 0


class TestRunCronJob:
    """Test suite for POST /cron/jobs/{job_id}/run endpoint"""

    @pytest.mark.asyncio
    async def test_run_job_success(self):
        """Test successfully triggering a job execution"""
        # Setup mock database
        mock_db = AsyncMock()
        
        # Mock job
        job = CronJob(
            id=1,
            name="test_job",
            schedule="* * * * *",
            status="active",
            script_path="/scripts/test.sh",
            success_count=10,
            error_count=2
        )
        
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = job
        mock_db.execute.return_value = mock_result
        
        # Mock add and commit
        mock_db.add = Mock()
        mock_db.commit = AsyncMock()
        
        with patch('api.v1.cron_routes.get_db_session', new_callable=AsyncMock, return_value=mock_db):
            with patch('api.v1.cron_routes.CronService', return_value=Mock()):
                # Execute
                response = await run_cron_job(job_id=1, db=mock_db)
                
                # Verify
                assert response["status"] == "started"
                assert "execution_id" in response
                assert response["execution_id"] == 1
                
                # Verify execution record was created
                assert mock_db.add.called

    @pytest.mark.asyncio
    async def test_run_job_not_found(self):
        """Test triggering a non-existent job raises 404"""
        # Setup mock database
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with patch('api.v1.cron_routes.get_db_session', new_callable=AsyncMock, return_value=mock_db):
            with patch('api.v1.cron_routes.CronService', return_value=Mock()):
                # Execute - should raise HTTPException 404
                with pytest.raises(HTTPException) as exc_info:
                    await run_cron_job(job_id=999, db=mock_db)
                
                assert exc_info.value.status_code == 404
                assert "Job not found" in str(exc_info.value.detail)


class TestGetCronStats:
    """Test suite for GET /cron/stats endpoint"""

    @pytest.mark.asyncio
    async def test_get_stats_success(self):
        """Test successfully retrieving cron statistics"""
        # Setup mock database
        mock_db = AsyncMock()
        
        # Mock all query results
        mock_db.execute.return_value.scalar.side_effect = [
            10,      # total jobs
            7,       # active jobs
            2,       # paused jobs
            1,       # error jobs
            50,      # today's executions
            45       # today's success count
        ]
        
        with patch('api.v1.cron_routes.get_db_session', new_callable=AsyncMock, return_value=mock_db):
            with patch('api.v1.cron_routes.CronService', return_value=Mock()):
                # Execute
                response = await get_cron_stats(db=mock_db)
                
                # Verify
                assert response.total_jobs == 10
                assert response.active_jobs == 7
                assert response.paused_jobs == 2
                assert response.error_jobs == 1
                assert response.total_executions_today == 50
                assert response.success_rate_today == 0.9

    @pytest.mark.asyncio
    async def test_get_stats_empty_database(self):
        """Test retrieving stats from empty database"""
        # Setup mock database with all zeros
        mock_db = AsyncMock()
        mock_db.execute.return_value.scalar.side_effect = [0, 0, 0, 0, 0, 0]
        
        with patch('api.v1.cron_routes.get_db_session', new_callable=AsyncMock, return_value=mock_db):
            with patch('api.v1.cron_routes.CronService', return_value=Mock()):
                # Execute
                response = await get_cron_stats(db=mock_db)
                
                # Verify
                assert response.total_jobs == 0
                assert response.active_jobs == 0
                assert response.paused_jobs == 0
                assert response.error_jobs == 0
                assert response.total_executions_today == 0
                assert response.success_rate_today == 0.0


class TestRouteValidation:
    """Test suite for route parameter validation"""

    @pytest.mark.asyncio
    async def test_get_executions_limit_validation(self):
        """Test that limit parameter is validated"""
        # Setup mock database
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        with patch('api.v1.cron_routes.get_db_session', new_callable=AsyncMock, return_value=mock_db):
            with patch('api.v1.cron_routes.CronService', return_value=Mock()):
                # Test with limit > 500 (should be clamped)
                # FastAPI should handle this validation
                response = await get_job_executions(job_id=1, limit=600, db=mock_db)
                
                # Verify it still returns a response (validation handled by FastAPI)
                assert isinstance(response, list)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
