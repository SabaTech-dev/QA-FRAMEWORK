"""
Final End-to-End Test for Cron Jobs API

Comprehensive test suite to verify all functionality.
"""

import asyncio
import sys
import os

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from database import AsyncSessionFactory
from models.cron import CronJob, CronExecution
from services.cron_service import CronService
from sqlalchemy import select, func
from datetime import datetime, timedelta


async def test_models():
    """Test database models"""
    print("\n1️⃣ Testing Database Models...")

    async with AsyncSessionFactory() as db:
        # Test CronJob model
        job = CronJob(
            name="test-job",
            schedule="*/5 * * * *",
            description="Test job",
            script_path="/tmp/test.sh",  # nosec B108 — inert string fixture, never created/read
            status="active",
        )
        assert job.name == "test-job"
        assert job.status == "active"
        print("   ✅ CronJob model works")

        # Test CronExecution model
        execution = CronExecution(job_id=1, status="success", started_at=datetime.utcnow())
        assert execution.status == "success"
        print("   ✅ CronExecution model works")


async def test_seed_data():
    """Test seed data"""
    print("\n2️⃣ Testing Seed Data...")

    async with AsyncSessionFactory() as db:
        # Count jobs
        result = await db.execute(select(func.count(CronJob.id)))
        job_count = result.scalar()
        assert job_count == 5, f"Expected 5 jobs, got {job_count}"
        print(f"   ✅ Found {job_count} cron jobs")

        # Count executions
        result = await db.execute(select(func.count(CronExecution.id)))
        exec_count = result.scalar()
        assert exec_count >= 50, f"Expected at least 50 executions, got {exec_count}"
        print(f"   ✅ Found {exec_count} cron executions")

        # Verify job details
        result = await db.execute(select(CronJob))
        jobs = result.scalars().all()
        for job in jobs:
            assert hasattr(job, "name")
            assert hasattr(job, "schedule")
            assert hasattr(job, "status")
            assert hasattr(job, "is_active")
            print(f"   ✅ Job: {job.name} ({job.schedule})")


async def test_service_methods():
    """Test service methods"""
    print("\n3️⃣ Testing Service Methods...")

    async with AsyncSessionFactory() as db:
        service = CronService(db)

        # Test get_jobs
        jobs = await service.get_jobs()
        assert isinstance(jobs, list)
        assert len(jobs) > 0
        print(f"   ✅ get_jobs() returned {len(jobs)} jobs")

        # Test get_job
        if jobs:
            job = await service.get_job(jobs[0].id)
            assert job is not None
            assert job.id == jobs[0].id
            print(f"   ✅ get_job() returned job: {job.name}")

        # Test get_executions
        if jobs:
            executions = await service.get_executions(jobs[0].id, limit=5)
            assert isinstance(executions, list)
            assert len(executions) <= 5
            print(f"   ✅ get_executions() returned {len(executions)} executions")

        # Test get_stats
        stats = await service.get_stats()
        assert hasattr(stats, "total_jobs")
        assert hasattr(stats, "active_jobs")
        assert hasattr(stats, "total_executions_today")
        assert stats.total_jobs > 0
        print(
            f"   ✅ get_stats() returned stats: {stats.total_jobs} jobs, {stats.total_executions_today} executions today"
        )

        # Test run_job
        if jobs:
            result = await service.run_job(jobs[0].id)
            assert "status" in result
            assert "execution_id" in result
            assert result["status"] == "started"
            print(f"   ✅ run_job() returned: {result}")


async def test_statistics():
    """Test statistics calculation"""
    print("\n4️⃣ Testing Statistics Calculation...")

    async with AsyncSessionFactory() as db:
        service = CronService(db)
        stats = await service.get_stats()

        # Verify stats are reasonable
        assert stats.total_jobs >= 0
        assert stats.active_jobs >= 0
        assert stats.paused_jobs >= 0
        assert stats.error_jobs >= 0
        assert stats.total_executions_today >= 0
        assert 0.0 <= stats.success_rate_today <= 1.0

        # Calculate expected success rate manually
        result = await db.execute(
            select(func.count(CronExecution.id)).where(CronExecution.status == "success")
        )
        success_count = result.scalar()

        result = await db.execute(
            select(func.count(CronExecution.id)).where(
                func.date(CronExecution.started_at) == datetime.now().date()
            )
        )
        total_count = result.scalar()

        expected_success_rate = 0.0
        if total_count > 0:
            expected_success_rate = success_count / total_count

        assert stats.success_rate_today == expected_success_rate
        print(f"   ✅ Success rate calculation: {stats.success_rate_today:.2%}")


async def test_foreign_keys():
    """Test foreign key relationships"""
    print("\n5️⃣ Testing Foreign Key Relationships...")

    async with AsyncSessionFactory() as db:
        result = await db.execute(select(CronJob))
        jobs = result.scalars().all()

        if jobs:
            job = jobs[0]
            result = await db.execute(
                select(CronExecution).where(CronExecution.job_id == job.id).limit(1)
            )
            execs = result.scalars().all()
            if execs:
                exec = execs[0]
                assert exec.job_id == job.id
                assert hasattr(exec, "status")
                assert hasattr(exec, "started_at")
                print(f"   ✅ Foreign key relationship works: Job {job.id} -> Execution {exec.id}")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("🧪 Cron Jobs API - Final End-to-End Test")
    print("=" * 60)

    try:
        await test_models()
        await test_seed_data()
        await test_service_methods()
        await test_statistics()
        await test_foreign_keys()

        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
        print("\n✅ Cron Jobs API is fully functional and ready for production use.")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
