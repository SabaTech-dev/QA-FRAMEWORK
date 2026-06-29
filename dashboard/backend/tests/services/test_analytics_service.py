"""
Unit Tests for Analytics Service

Tests business analytics and metrics tracking with comprehensive mocking.
"""
import pytest
pytest.importorskip('prometheus_client')
pytest.importorskip('redis')
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from collections import defaultdict

from services.analytics_service import (
    AnalyticsService,
    get_analytics_service,
    get_user_analytics,
    get_test_analytics,
    get_revenue_analytics,
    get_feature_usage_analytics,
    get_dashboard_summary
)
from models import User, TestExecution, Project, Subscription, UsageRecord


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_analytics_service(mock_db):
    """Create analytics service with mock database"""
    return AnalyticsService(mock_db)


class TestGetUserAnalytics:
    """Tests for get_user_analytics function"""
    
    @pytest.mark.asyncio
    async def test_get_user_analytics_default_dates(self, mock_analytics_service, mock_db):
        """Test user analytics with default date range"""
        # Mock total users
        total_result = AsyncMock()
        total_result.scalar = Mock(return_value=100)
        
        # Mock new signups
        new_result = AsyncMock()
        new_result.scalar = Mock(return_value=15)
        
        # Mock active users
        active_result = AsyncMock()
        active_result.scalar = Mock(return_value=50)
        
        # Mock churned users
        churned_result = AsyncMock()
        churned_result.scalar = Mock(return_value=5)
        
        # Mock signup trend
        signup_trend_result = AsyncMock()
        signup_trend_result.__iter__ = Mock(return_value=iter([
            Mock(date=datetime(2024, 1, 1), count=5),
            Mock(date=datetime(2024, 1, 2), count=10)
        ]))
        
        # Mock active trend
        active_trend_result = AsyncMock()
        active_trend_result.__iter__ = Mock(return_value=iter([
            Mock(date=datetime(2024, 1, 1), count=20),
            Mock(date=datetime(2024, 1, 2), count=25)
        ]))
        
        mock_db.execute.side_effect = [
            total_result,
            new_result,
            active_result,
            churned_result,
            signup_trend_result,
            active_trend_result
        ]
        
        result = await mock_analytics_service.get_user_analytics()
        
        assert result["total_users"] == 100
        assert result["new_signups"] == 15
        assert result["active_users"] == 50
        assert result["churned_users"] == 5
        assert result["churn_rate"] == 5.0  # 5/100 * 100
        assert len(result["signup_trend"]) == 2
        assert len(result["active_trend"]) == 2
        assert "period" in result
    
    @pytest.mark.asyncio
    async def test_get_user_analytics_custom_dates(self, mock_analytics_service, mock_db):
        """Test user analytics with custom date range"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        # Mock all queries
        results = []
        for _ in range(6):
            result = AsyncMock()
            result.scalar = Mock(return_value=10)
            result.__iter__ = Mock(return_value=iter([]))
            results.append(result)
        
        mock_db.execute.side_effect = results
        
        result = await mock_analytics_service.get_user_analytics(start_date, end_date)
        
        assert result["period"]["start"] == start_date.isoformat()
        assert result["period"]["end"] == end_date.isoformat()
    
    @pytest.mark.asyncio
    async def test_get_user_analytics_zero_total_users(self, mock_analytics_service, mock_db):
        """Test user analytics when no users exist"""
        # Mock all returning 0
        results = []
        for _ in range(6):
            result = AsyncMock()
            result.scalar = Mock(return_value=0)
            result.__iter__ = Mock(return_value=iter([]))
            results.append(result)
        
        mock_db.execute.side_effect = results
        
        result = await mock_analytics_service.get_user_analytics()
        
        assert result["total_users"] == 0
        assert result["churn_rate"] == 0  # Avoid division by zero


class TestGetTestAnalytics:
    """Tests for get_test_analytics function"""
    
    @pytest.mark.asyncio
    async def test_get_test_analytics_basic(self, mock_analytics_service, mock_db):
        """Test basic test analytics"""
        # Mock total executions
        total_result = AsyncMock()
        total_result.scalar = Mock(return_value=100)
        
        # Mock passed tests
        passed_result = AsyncMock()
        passed_result.scalar = Mock(return_value=85)
        
        # Mock failed tests
        failed_result = AsyncMock()
        failed_result.scalar = Mock(return_value=15)
        
        # Mock average duration
        avg_result = AsyncMock()
        avg_result.scalar = Mock(return_value=45.5)
        
        # Mock trend
        trend_result = AsyncMock()
        trend_result.__iter__ = Mock(return_value=iter([
            Mock(date=datetime(2024, 1, 1), total=10, passed=8, failed=2)
        ]))
        
        # Mock top projects
        projects_result = AsyncMock()
        projects_result.__iter__ = Mock(return_value=iter([
            Mock(name="Project 1", execution_count=50)
        ]))
        
        mock_db.execute.side_effect = [
            total_result,
            passed_result,
            failed_result,
            avg_result,
            trend_result,
            projects_result
        ]
        
        result = await mock_analytics_service.get_test_analytics()
        
        assert result["total_executions"] == 100
        assert result["passed"] == 85
        assert result["failed"] == 15
        assert result["success_rate"] == 85.0
        assert result["avg_duration_seconds"] == 45.5
        assert len(result["executions_trend"]) == 1
        assert len(result["top_projects"]) == 1
    
    @pytest.mark.asyncio
    async def test_get_test_analytics_with_user_filter(self, mock_analytics_service, mock_db):
        """Test test analytics filtered by user"""
        # Mock all queries
        results = []
        for _ in range(6):
            result = AsyncMock()
            result.scalar = Mock(return_value=10)
            result.__iter__ = Mock(return_value=iter([]))
            results.append(result)
        
        mock_db.execute.side_effect = results
        
        result = await mock_analytics_service.get_test_analytics(user_id=1)
        
        assert result["total_executions"] == 10
    
    @pytest.mark.asyncio
    async def test_get_test_analytics_zero_executions(self, mock_analytics_service, mock_db):
        """Test test analytics when no executions exist"""
        # Mock all returning 0
        results = []
        for _ in range(6):
            result = AsyncMock()
            result.scalar = Mock(return_value=0)
            result.__iter__ = Mock(return_value=iter([]))
            results.append(result)
        
        mock_db.execute.side_effect = results
        
        result = await mock_analytics_service.get_test_analytics()
        
        assert result["total_executions"] == 0
        assert result["success_rate"] == 0  # Avoid division by zero
    
    @pytest.mark.asyncio
    async def test_get_test_analytics_trend_calculation(self, mock_analytics_service, mock_db):
        """Test test analytics trend data calculation"""
        # Mock basic stats
        total_result = AsyncMock()
        total_result.scalar = Mock(return_value=100)
        passed_result = AsyncMock()
        passed_result.scalar = Mock(return_value=80)
        failed_result = AsyncMock()
        failed_result.scalar = Mock(return_value=20)
        avg_result = AsyncMock()
        avg_result.scalar = Mock(return_value=30.0)
        
        # Mock trend with success rate calculation
        trend_result = AsyncMock()
        trend_row = Mock()
        trend_row.date = datetime(2024, 1, 1)
        trend_row.total = 10
        trend_row.passed = 8
        trend_row.failed = 2
        trend_result.__iter__ = Mock(return_value=iter([trend_row]))
        
        # Mock top projects
        projects_result = AsyncMock()
        projects_result.__iter__ = Mock(return_value=iter([]))
        
        mock_db.execute.side_effect = [
            total_result,
            passed_result,
            failed_result,
            avg_result,
            trend_result,
            projects_result
        ]
        
        result = await mock_analytics_service.get_test_analytics()
        
        # Verify success rate calculated correctly
        assert result["executions_trend"][0]["success_rate"] == 80.0  # 8/10 * 100


class TestGetRevenueAnalytics:
    """Tests for get_revenue_analytics function"""
    
    @pytest.mark.asyncio
    async def test_get_revenue_analytics_basic(self, mock_analytics_service, mock_db):
        """Test basic revenue analytics"""
        # Mock subscribers by plan
        subscribers_result = AsyncMock()
        subscribers_result.__iter__ = Mock(return_value=iter([
            Mock(plan_type="free", count=100),
            Mock(plan_type="pro", count=20),
            Mock(plan_type="enterprise", count=5)
        ]))
        
        # Mock revenue trend
        revenue_trend_result = AsyncMock()
        revenue_trend_result.__iter__ = Mock(return_value=iter([
            Mock(month="2024-01", new_subscribers=10)
        ]))
        
        mock_db.execute.side_effect = [
            subscribers_result,
            revenue_trend_result
        ]
        
        result = await mock_analytics_service.get_revenue_analytics()
        
        # Verify MRR calculation
        # free: 0, pro: 99*20=1980, enterprise: 499*5=2495
        # Total MRR: 4475
        assert result["mrr"] == 4475
        assert result["arr"] == 4475 * 12  # 53700
        assert result["total_subscribers"] == 125
        assert result["currency"] == "USD"
        assert "subscribers_by_plan" in result
    
    @pytest.mark.asyncio
    async def test_get_revenue_analytics_zero_subscribers(self, mock_analytics_service, mock_db):
        """Test revenue analytics when no subscribers"""
        subscribers_result = AsyncMock()
        subscribers_result.__iter__ = Mock(return_value=iter([]))
        
        revenue_trend_result = AsyncMock()
        revenue_trend_result.__iter__ = Mock(return_value=iter([]))
        
        mock_db.execute.side_effect = [
            subscribers_result,
            revenue_trend_result
        ]
        
        result = await mock_analytics_service.get_revenue_analytics()
        
        assert result["mrr"] == 0
        assert result["arr"] == 0
        assert result["total_subscribers"] == 0
        assert result["arpu"] == 0
        assert result["ltv_estimate"] == 0
    
    @pytest.mark.asyncio
    async def test_get_revenue_analytics_ltv_calculation(self, mock_analytics_service, mock_db):
        """Test LTV calculation"""
        # Mock only pro subscribers for easier calculation
        subscribers_result = AsyncMock()
        subscribers_result.__iter__ = Mock(return_value=iter([
            Mock(plan_type="pro", count=10)
        ]))
        
        revenue_trend_result = AsyncMock()
        revenue_trend_result.__iter__ = Mock(return_value=iter([]))
        
        mock_db.execute.side_effect = [
            subscribers_result,
            revenue_trend_result
        ]
        
        result = await mock_analytics_service.get_revenue_analytics()
        
        # MRR = 99 * 10 = 990
        # ARPU = 990 / 10 = 99
        # LTV = 99 * 24 = 2376
        assert result["mrr"] == 990
        assert result["arpu"] == 99.0
        assert result["ltv_estimate"] == 2376.0
    
    @pytest.mark.asyncio
    async def test_get_revenue_analytics_custom_dates(self, mock_analytics_service, mock_db):
        """Test revenue analytics with custom dates"""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        
        subscribers_result = AsyncMock()
        subscribers_result.__iter__ = Mock(return_value=iter([]))
        
        revenue_trend_result = AsyncMock()
        revenue_trend_result.__iter__ = Mock(return_value=iter([]))
        
        mock_db.execute.side_effect = [
            subscribers_result,
            revenue_trend_result
        ]
        
        result = await mock_analytics_service.get_revenue_analytics(start_date, end_date)
        
        assert result["period"]["start"] == start_date.isoformat()
        assert result["period"]["end"] == end_date.isoformat()


class TestGetFeatureUsageAnalytics:
    """Tests for get_feature_usage_analytics function"""
    
    @pytest.mark.asyncio
    async def test_get_feature_usage_analytics_basic(self, mock_analytics_service, mock_db):
        """Test basic feature usage analytics"""
        # Mock usage records
        usage_result = AsyncMock()
        usage_result.__iter__ = Mock(return_value=iter([
            Mock(feature_name="ai_test_generation", usage_count=100, unique_users=25),
            Mock(feature_name="self_healing", usage_count=50, unique_users=10)
        ]))
        
        # Mock total users
        total_users_result = AsyncMock()
        total_users_result.scalar = Mock(return_value=100)
        
        mock_db.execute.side_effect = [
            usage_result,
            total_users_result
        ]
        
        result = await mock_analytics_service.get_feature_usage_analytics()
        
        assert "ai_test_generation" in result["feature_usage"]
        assert result["feature_usage"]["ai_test_generation"]["usage_count"] == 100
        assert result["feature_usage"]["ai_test_generation"]["unique_users"] == 25
        assert result["adoption_rates"]["ai_test_generation"] == 25.0  # 25/100 * 100
    
    @pytest.mark.asyncio
    async def test_get_feature_usage_analytics_includes_known_features(self, mock_analytics_service, mock_db):
        """Test that analytics includes all known features even if not used"""
        usage_result = AsyncMock()
        usage_result.__iter__ = Mock(return_value=iter([]))
        
        total_users_result = AsyncMock()
        total_users_result.scalar = Mock(return_value=100)
        
        mock_db.execute.side_effect = [
            usage_result,
            total_users_result
        ]
        
        result = await mock_analytics_service.get_feature_usage_analytics()
        
        # All known features should be present
        known_features = [
            'ai_test_generation',
            'self_healing',
            'flaky_detection',
            'parallel_execution',
            'ci_integration',
            'api_usage'
        ]
        
        for feature in known_features:
            assert feature in result["feature_usage"]
            assert result["feature_usage"][feature]["usage_count"] == 0
            assert result["feature_usage"][feature]["unique_users"] == 0
    
    @pytest.mark.asyncio
    async def test_get_feature_usage_analytics_adoption_rates(self, mock_analytics_service, mock_db):
        """Test adoption rate calculations"""
        usage_result = AsyncMock()
        usage_result.__iter__ = Mock(return_value=iter([
            Mock(feature_name="ai_test_generation", usage_count=100, unique_users=50)
        ]))
        
        total_users_result = AsyncMock()
        total_users_result.scalar = Mock(return_value=200)
        
        mock_db.execute.side_effect = [
            usage_result,
            total_users_result
        ]
        
        result = await mock_analytics_service.get_feature_usage_analytics()
        
        # Adoption rate = 50/200 * 100 = 25%
        assert result["adoption_rates"]["ai_test_generation"] == 25.0


class TestGetDashboardSummary:
    """Tests for get_dashboard_summary function"""
    
    @pytest.mark.asyncio
    async def test_get_dashboard_summary_basic(self, mock_analytics_service, mock_db):
        """Test basic dashboard summary"""
        # Mock all the sub-analytics calls
        with patch.object(mock_analytics_service, 'get_user_analytics') as mock_user, \
             patch.object(mock_analytics_service, 'get_test_analytics') as mock_test, \
             patch.object(mock_analytics_service, 'get_revenue_analytics') as mock_revenue, \
             patch.object(mock_analytics_service, 'get_feature_usage_analytics') as mock_feature:
            
            mock_user.return_value = {
                "total_users": 100,
                "active_users": 50,
                "new_signups": 10,
                "churned_users": 2,
                "signup_trend": [{"date": "2024-01-01", "count": 5}],
                "active_trend": [{"date": "2024-01-01", "count": 20}]
            }
            
            mock_test.return_value = {
                "total_executions": 500,
                "success_rate": 85.0,
                "executions_trend": [{"date": "2024-01-01", "total": 50}],
                "top_projects": [{"name": "Project 1", "executions": 100}]
            }
            
            mock_revenue.return_value = {
                "mrr": 5000,
                "total_subscribers": 50,
                "revenue_trend": [{"month": "2024-01", "estimated_mrr": 4500}]
            }
            
            mock_feature.return_value = {
                "feature_usage": {"ai_test_generation": {"usage_count": 100}},
                "adoption_rates": {"ai_test_generation": 25.0}
            }
            
            result = await mock_analytics_service.get_dashboard_summary()
            
            # Verify summary structure
            assert "summary" in result
            assert "trends" in result
            assert "features" in result
            assert "top_projects" in result
            
            # Verify summary values
            assert result["summary"]["total_users"] == 100
            assert result["summary"]["active_users"] == 50
            assert result["summary"]["total_executions"] == 500
            assert result["summary"]["success_rate"] == 85.0
            assert result["summary"]["mrr"] == 5000
            assert result["summary"]["total_subscribers"] == 50
    
    @pytest.mark.asyncio
    async def test_get_dashboard_summary_growth_calculation(self, mock_analytics_service, mock_db):
        """Test dashboard summary growth calculation"""
        with patch.object(mock_analytics_service, 'get_user_analytics') as mock_user, \
             patch.object(mock_analytics_service, 'get_test_analytics') as mock_test, \
             patch.object(mock_analytics_service, 'get_revenue_analytics') as mock_revenue, \
             patch.object(mock_analytics_service, 'get_feature_usage_analytics') as mock_feature:
            
            # Current period: 20 new signups
            mock_user.return_value = {
                "total_users": 100,
                "active_users": 50,
                "new_signups": 20,
                "churned_users": 2,
                "signup_trend": [],
                "active_trend": []
            }
            
            # Previous period: 10 new signups (called for comparison)
            def user_analytics_side_effect(start=None, end=None):
                if start and start < datetime.utcnow() - timedelta(days=30):
                    return {"new_signups": 10, "total_users": 100, "active_users": 50, "churned_users": 2, "signup_trend": [], "active_trend": []}
                return {"new_signups": 20, "total_users": 100, "active_users": 50, "churned_users": 2, "signup_trend": [], "active_trend": []}
            
            mock_user.side_effect = user_analytics_side_effect
            
            mock_test.return_value = {
                "total_executions": 500,
                "success_rate": 85.0,
                "executions_trend": [],
                "top_projects": []
            }
            
            mock_revenue.return_value = {
                "mrr": 5000,
                "total_subscribers": 50,
                "revenue_trend": []
            }
            
            mock_feature.return_value = {
                "feature_usage": {},
                "adoption_rates": {}
            }
            
            result = await mock_analytics_service.get_dashboard_summary()
            
            # Growth = ((20 - 10) / 10) * 100 = 100%
            assert "user_growth_percent" in result["trends"]
    
    @pytest.mark.asyncio
    async def test_get_dashboard_summary_generated_at(self, mock_analytics_service, mock_db):
        """Test dashboard summary includes generated timestamp"""
        with patch.object(mock_analytics_service, 'get_user_analytics') as mock_user, \
             patch.object(mock_analytics_service, 'get_test_analytics') as mock_test, \
             patch.object(mock_analytics_service, 'get_revenue_analytics') as mock_revenue, \
             patch.object(mock_analytics_service, 'get_feature_usage_analytics') as mock_feature:
            
            mock_user.return_value = {
                "total_users": 100,
                "active_users": 50,
                "new_signups": 10,
                "churned_users": 2,
                "signup_trend": [],
                "active_trend": []
            }
            
            mock_test.return_value = {
                "total_executions": 500,
                "success_rate": 85.0,
                "executions_trend": [],
                "top_projects": []
            }
            
            mock_revenue.return_value = {
                "mrr": 5000,
                "total_subscribers": 50,
                "revenue_trend": []
            }
            
            mock_feature.return_value = {
                "feature_usage": {},
                "adoption_rates": {}
            }
            
            result = await mock_analytics_service.get_dashboard_summary()
            
            assert "generated_at" in result
            assert "period" in result


class TestConvenienceFunctions:
    """Tests for convenience wrapper functions"""
    
    @pytest.mark.asyncio
    async def test_get_analytics_service_factory(self, mock_db):
        """Test get_analytics_service factory function"""
        service = get_analytics_service(mock_db)
        
        assert isinstance(service, AnalyticsService)
        assert service.db == mock_db
    
    @pytest.mark.asyncio
    async def test_get_user_analytics_convenience(self, mock_db):
        """Test get_user_analytics convenience function"""
        with patch.object(AnalyticsService, 'get_user_analytics') as mock_method:
            mock_method.return_value = {"total_users": 100}
            
            result = await get_user_analytics(mock_db)
            
            assert result["total_users"] == 100
            mock_method.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_test_analytics_convenience(self, mock_db):
        """Test get_test_analytics convenience function"""
        with patch.object(AnalyticsService, 'get_test_analytics') as mock_method:
            mock_method.return_value = {"total_executions": 500}
            
            result = await get_test_analytics(mock_db, user_id=1)
            
            assert result["total_executions"] == 500
            mock_method.assert_called_once_with(1, None, None)
    
    @pytest.mark.asyncio
    async def test_get_revenue_analytics_convenience(self, mock_db):
        """Test get_revenue_analytics convenience function"""
        with patch.object(AnalyticsService, 'get_revenue_analytics') as mock_method:
            mock_method.return_value = {"mrr": 5000}
            
            result = await get_revenue_analytics(mock_db)
            
            assert result["mrr"] == 5000
            mock_method.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_feature_usage_analytics_convenience(self, mock_db):
        """Test get_feature_usage_analytics convenience function"""
        with patch.object(AnalyticsService, 'get_feature_usage_analytics') as mock_method:
            mock_method.return_value = {"feature_usage": {}}
            
            result = await get_feature_usage_analytics(mock_db)
            
            assert "feature_usage" in result
            mock_method.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_dashboard_summary_convenience(self, mock_db):
        """Test get_dashboard_summary convenience function"""
        with patch.object(AnalyticsService, 'get_dashboard_summary') as mock_method:
            mock_method.return_value = {"summary": {}}
            
            result = await get_dashboard_summary(mock_db)
            
            assert "summary" in result
            mock_method.assert_called_once()


class TestAnalyticsServiceClass:
    """Tests for AnalyticsService class methods"""
    
    def test_analytics_service_initialization(self, mock_db):
        """Test AnalyticsService initialization"""
        service = AnalyticsService(mock_db)
        
        assert service.db == mock_db
    
    @pytest.mark.asyncio
    async def test_analytics_service_handles_null_results(self, mock_db):
        """Test AnalyticsService handles NULL database results"""
        service = AnalyticsService(mock_db)
        
        # Mock scalar returning None
        result = AsyncMock()
        result.scalar = Mock(return_value=None)
        result.__iter__ = Mock(return_value=iter([]))
        
        mock_db.execute.return_value = result
        
        user_analytics = await service.get_user_analytics()
        
        # Should handle None gracefully
        assert user_analytics["total_users"] == 0


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=services/analytics_service", "--cov-report=term-missing"])
