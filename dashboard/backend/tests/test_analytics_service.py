"""
Unit tests for Analytics Service
"""

import pytest
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from services.analytics_service import (
    AnalyticsService,
    get_analytics_service,
    get_user_analytics,
    get_test_analytics,
    get_revenue_analytics,
    get_feature_usage_analytics,
    get_dashboard_summary
)


@pytest.fixture
def mock_db():
    """Create mock database session"""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def analytics_service(mock_db):
    """Create analytics service instance"""
    return AnalyticsService(mock_db)


class TestGetUserAnalytics:
    """Test user analytics methods"""
    
    @pytest.mark.asyncio
    async def test_get_user_analytics_default_period(self, analytics_service, mock_db):
        """Test user analytics with default period (last 30 days)"""
        # Mock database responses
        mock_db.execute = AsyncMock()
        
        # Mock total users
        total_result = MagicMock()
        total_result.scalar.return_value = 100
        mock_db.execute.side_effect = [
            total_result,  # total users
            MagicMock(scalar=MagicMock(return_value=20)),  # new signups
            MagicMock(scalar=MagicMock(return_value=50)),  # active users
            MagicMock(scalar=MagicMock(return_value=5)),  # churned users
            MagicMock(__iter__=MagicMock(return_value=iter([]))),  # signup trend
            MagicMock(__iter__=MagicMock(return_value=iter([])))  # active trend
        ]
        
        result = await analytics_service.get_user_analytics()
        
        assert result['total_users'] == 100
        assert result['new_signups'] == 20
        assert result['active_users'] == 50
        assert result['churned_users'] == 5
        assert 'churn_rate' in result
        assert 'signup_trend' in result
        assert 'active_trend' in result
    
    @pytest.mark.asyncio
    async def test_get_user_analytics_custom_period(self, analytics_service, mock_db):
        """Test user analytics with custom period"""
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()
        
        mock_db.execute = AsyncMock()
        mock_db.execute.side_effect = [
            MagicMock(scalar=MagicMock(return_value=50)),
            MagicMock(scalar=MagicMock(return_value=10)),
            MagicMock(scalar=MagicMock(return_value=30)),
            MagicMock(scalar=MagicMock(return_value=2)),
            MagicMock(__iter__=MagicMock(return_value=iter([]))),
            MagicMock(__iter__=MagicMock(return_value=iter([])))
        ]
        
        result = await analytics_service.get_user_analytics(start_date, end_date)
        
        assert 'period' in result
        assert result['period']['start'] == start_date.isoformat()
        assert result['period']['end'] == end_date.isoformat()
    
    @pytest.mark.asyncio
    async def test_get_user_analytics_zero_users(self, analytics_service, mock_db):
        """Test user analytics when no users exist"""
        mock_db.execute = AsyncMock()
        mock_db.execute.side_effect = [
            MagicMock(scalar=MagicMock(return_value=0)),
            MagicMock(scalar=MagicMock(return_value=0)),
            MagicMock(scalar=MagicMock(return_value=0)),
            MagicMock(scalar=MagicMock(return_value=0)),
            MagicMock(__iter__=MagicMock(return_value=iter([]))),
            MagicMock(__iter__=MagicMock(return_value=iter([])))
        ]
        
        result = await analytics_service.get_user_analytics()
        
        assert result['total_users'] == 0
        assert result['churn_rate'] == 0.0


class TestGetTestAnalytics:
    """Test test analytics methods"""
    
    @pytest.mark.asyncio
    async def test_get_test_analytics_basic(self, analytics_service, mock_db):
        """Test basic test analytics"""
        mock_db.execute = AsyncMock()
        mock_db.execute.side_effect = [
            MagicMock(scalar=MagicMock(return_value=1000)),  # total
            MagicMock(scalar=MagicMock(return_value=850)),  # passed
            MagicMock(scalar=MagicMock(return_value=150)),  # failed
            MagicMock(scalar=MagicMock(return_value=45.5)),  # avg duration
            MagicMock(__iter__=MagicMock(return_value=iter([]))),  # trend
            MagicMock(__iter__=MagicMock(return_value=iter([])))  # top projects
        ]
        
        result = await analytics_service.get_test_analytics()
        
        assert result['total_executions'] == 1000
        assert result['passed'] == 850
        assert result['failed'] == 150
        assert result['success_rate'] == 85.0
        assert result['avg_duration_seconds'] == 45.5
    
    @pytest.mark.asyncio
    async def test_get_test_analytics_with_user_filter(self, analytics_service, mock_db):
        """Test test analytics filtered by user"""
        mock_db.execute = AsyncMock()
        mock_db.execute.side_effect = [
            MagicMock(scalar=MagicMock(return_value=100)),
            MagicMock(scalar=MagicMock(return_value=90)),
            MagicMock(scalar=MagicMock(return_value=10)),
            MagicMock(scalar=MagicMock(return_value=30.0)),
            MagicMock(__iter__=MagicMock(return_value=iter([]))),
            MagicMock(__iter__=MagicMock(return_value=iter([])))
        ]
        
        result = await analytics_service.get_test_analytics(user_id=1)
        
        assert result['total_executions'] == 100
        assert result['success_rate'] == 90.0
    
    @pytest.mark.asyncio
    async def test_get_test_analytics_zero_executions(self, analytics_service, mock_db):
        """Test test analytics when no executions exist"""
        mock_db.execute = AsyncMock()
        mock_db.execute.side_effect = [
            MagicMock(scalar=MagicMock(return_value=0)),
            MagicMock(scalar=MagicMock(return_value=0)),
            MagicMock(scalar=MagicMock(return_value=0)),
            MagicMock(scalar=MagicMock(return_value=0.0)),
            MagicMock(__iter__=MagicMock(return_value=iter([]))),
            MagicMock(__iter__=MagicMock(return_value=iter([])))
        ]
        
        result = await analytics_service.get_test_analytics()
        
        assert result['total_executions'] == 0
        assert result['success_rate'] == 0.0


class TestGetRevenueAnalytics:
    """Test revenue analytics methods"""
    
    @pytest.mark.asyncio
    async def test_get_revenue_analytics_basic(self, analytics_service, mock_db):
        """Test basic revenue analytics"""
        # Mock subscribers by plan
        subscribers_mock = MagicMock()
        subscribers_mock.__iter__ = MagicMock(return_value=iter([
            MagicMock(plan_type='free', count=50),
            MagicMock(plan_type='pro', count=30),
            MagicMock(plan_type='enterprise', count=5)
        ]))
        
        mock_db.execute = AsyncMock()
        mock_db.execute.side_effect = [
            subscribers_mock,
            MagicMock(__iter__=MagicMock(return_value=iter([])))  # revenue trend
        ]
        
        result = await analytics_service.get_revenue_analytics()
        
        # MRR = (30 * 99) + (5 * 499) = 2970 + 2495 = 5465
        assert result['mrr'] == 5465
        assert result['arr'] == 5465 * 12
        assert result['total_subscribers'] == 85
        assert result['subscribers_by_plan']['pro'] == 30
        assert result['subscribers_by_plan']['enterprise'] == 5
    
    @pytest.mark.asyncio
    async def test_get_revenue_analytics_no_subscribers(self, analytics_service, mock_db):
        """Test revenue analytics when no subscribers exist"""
        mock_db.execute = AsyncMock()
        mock_db.execute.side_effect = [
            MagicMock(__iter__=MagicMock(return_value=iter([]))),
            MagicMock(__iter__=MagicMock(return_value=iter([])))
        ]
        
        result = await analytics_service.get_revenue_analytics()
        
        assert result['mrr'] == 0
        assert result['total_subscribers'] == 0
        assert result['arpu'] == 0


class TestGetFeatureUsageAnalytics:
    """Test feature usage analytics methods"""
    
    @pytest.mark.asyncio
    async def test_get_feature_usage_analytics_basic(self, analytics_service, mock_db):
        """Test basic feature usage analytics"""
        usage_mock = MagicMock()
        usage_mock.__iter__ = MagicMock(return_value=iter([
            MagicMock(feature_name='ai_test_generation', usage_count=100, unique_users=25),
            MagicMock(feature_name='self_healing', usage_count=50, unique_users=10)
        ]))
        
        mock_db.execute = AsyncMock()
        mock_db.execute.side_effect = [
            usage_mock,
            MagicMock(scalar=MagicMock(return_value=100))  # total users
        ]
        
        result = await analytics_service.get_feature_usage_analytics()
        
        assert result['feature_usage']['ai_test_generation']['usage_count'] == 100
        assert result['feature_usage']['ai_test_generation']['unique_users'] == 25
        assert result['feature_usage']['self_healing']['usage_count'] == 50
        assert 'adoption_rates' in result
    
    @pytest.mark.asyncio
    async def test_get_feature_usage_analytics_empty(self, analytics_service, mock_db):
        """Test feature usage analytics when no usage data exists"""
        mock_db.execute = AsyncMock()
        mock_db.execute.side_effect = [
            MagicMock(__iter__=MagicMock(return_value=iter([]))),
            MagicMock(scalar=MagicMock(return_value=100))
        ]
        
        result = await analytics_service.get_feature_usage_analytics()
        
        # Should have default values for known features
        assert 'ai_test_generation' in result['feature_usage']
        assert result['feature_usage']['ai_test_generation']['usage_count'] == 0


class TestGetDashboardSummary:
    """Test dashboard summary method"""
    
    @pytest.mark.asyncio
    async def test_get_dashboard_summary(self, analytics_service, mock_db):
        """Test comprehensive dashboard summary"""
        # Mock the internal methods instead of all database queries
        with patch.object(analytics_service, 'get_user_analytics', new_callable=AsyncMock) as mock_user:
            with patch.object(analytics_service, 'get_test_analytics', new_callable=AsyncMock) as mock_test:
                with patch.object(analytics_service, 'get_revenue_analytics', new_callable=AsyncMock) as mock_revenue:
                    with patch.object(analytics_service, 'get_feature_usage_analytics', new_callable=AsyncMock) as mock_feature:
                        # Setup mock returns
                        mock_user.return_value = {
                            'total_users': 100,
                            'new_signups': 20,
                            'active_users': 50,
                            'churned_users': 5,
                            'signup_trend': [],
                            'active_trend': []
                        }
                        mock_test.return_value = {
                            'total_executions': 1000,
                            'success_rate': 85.0,
                            'executions_trend': [],
                            'top_projects': []
                        }
                        mock_revenue.return_value = {
                            'mrr': 5000,
                            'total_subscribers': 35,
                            'revenue_trend': []
                        }
                        mock_feature.return_value = {
                            'feature_usage': {'ai_test_generation': {'usage_count': 100, 'unique_users': 25}},
                            'adoption_rates': {}
                        }
                        
                        result = await analytics_service.get_dashboard_summary()
                        
                        assert 'summary' in result
                        assert 'trends' in result
                        assert 'features' in result
                        assert 'top_projects' in result
                        assert 'period' in result
                        assert 'generated_at' in result


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    @pytest.mark.asyncio
    async def test_get_analytics_service_factory(self, mock_db):
        """Test analytics service factory function"""
        service = get_analytics_service(mock_db)
        assert isinstance(service, AnalyticsService)
    
    @pytest.mark.asyncio
    async def test_get_user_analytics_function(self, mock_db):
        """Test user analytics convenience function"""
        with patch.object(AnalyticsService, 'get_user_analytics', new_callable=AsyncMock) as mock:
            mock.return_value = {'total_users': 100}
            
            result = await get_user_analytics(mock_db)
            
            assert result['total_users'] == 100
    
    @pytest.mark.asyncio
    async def test_get_test_analytics_function(self, mock_db):
        """Test test analytics convenience function"""
        with patch.object(AnalyticsService, 'get_test_analytics', new_callable=AsyncMock) as mock:
            mock.return_value = {'total_executions': 1000}
            
            result = await get_test_analytics(mock_db)
            
            assert result['total_executions'] == 1000
    
    @pytest.mark.asyncio
    async def test_get_revenue_analytics_function(self, mock_db):
        """Test revenue analytics convenience function"""
        with patch.object(AnalyticsService, 'get_revenue_analytics', new_callable=AsyncMock) as mock:
            mock.return_value = {'mrr': 5000}
            
            result = await get_revenue_analytics(mock_db)
            
            assert result['mrr'] == 5000
    
    @pytest.mark.asyncio
    async def test_get_feature_usage_analytics_function(self, mock_db):
        """Test feature usage analytics convenience function"""
        with patch.object(AnalyticsService, 'get_feature_usage_analytics', new_callable=AsyncMock) as mock:
            mock.return_value = {'feature_usage': {}}
            
            result = await get_feature_usage_analytics(mock_db)
            
            assert 'feature_usage' in result
    
    @pytest.mark.asyncio
    async def test_get_dashboard_summary_function(self, mock_db):
        """Test dashboard summary convenience function"""
        with patch.object(AnalyticsService, 'get_dashboard_summary', new_callable=AsyncMock) as mock:
            mock.return_value = {'summary': {}}
            
            result = await get_dashboard_summary(mock_db)
            
            assert 'summary' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
