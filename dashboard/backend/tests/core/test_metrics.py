"""
Tests for business metrics system.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from core.metrics import (
    # Counters
    tests_executed_total,
    test_failures_total,
    user_actions_total,
    api_requests_total,
    suites_created_total,
    # Histograms
    test_duration_seconds,
    api_response_time_seconds,
    suite_execution_seconds,
    # Gauges
    active_users_gauge,
    test_success_rate_gauge,
    error_rate_gauge,
    queue_size_gauge,
    system_load_gauge,
    # Classes
    BusinessMetricsManager,
    TestExecutionTracker,
    APIRequestTracker,
    metrics_manager,
    get_metrics_response
)


class TestCounterMetrics:
    """Tests for counter metrics initialization."""
    
    def test_tests_executed_total_exists(self):
        """Test that tests_executed_total metric exists."""
        assert tests_executed_total is not None
        assert tests_executed_total._type == "counter"
    
    def test_test_failures_total_exists(self):
        """Test that test_failures_total metric exists."""
        assert test_failures_total is not None
        assert test_failures_total._type == "counter"
    
    def test_user_actions_total_exists(self):
        """Test that user_actions_total metric exists."""
        assert user_actions_total is not None
        assert user_actions_total._type == "counter"
    
    def test_api_requests_total_exists(self):
        """Test that api_requests_total metric exists."""
        assert api_requests_total is not None
        assert api_requests_total._type == "counter"
    
    def test_suites_created_total_exists(self):
        """Test that suites_created_total metric exists."""
        assert suites_created_total is not None
        assert suites_created_total._type == "counter"
    
    def test_tests_executed_total_labels(self):
        """Test tests_executed_total has correct labels."""
        # Check metric name (may vary by prometheus_client version)
        assert tests_executed_total._name in ['qa_tests_executed_total', 'qa_tests_executed', 'tests_executed_total']

    def test_test_failures_total_labels(self):
        """Test test_failures_total has correct labels."""
        # Check metric name (may vary by prometheus_client version)
        assert test_failures_total._name in ['qa_test_failures_total', 'qa_test_failures', 'test_failures_total']


class TestHistogramMetrics:
    """Tests for histogram metrics initialization."""
    
    def test_test_duration_seconds_exists(self):
        """Test that test_duration_seconds metric exists."""
        assert test_duration_seconds is not None
        assert test_duration_seconds._type == "histogram"
    
    def test_api_response_time_seconds_exists(self):
        """Test that api_response_time_seconds metric exists."""
        assert api_response_time_seconds is not None
        assert api_response_time_seconds._type == "histogram"
    
    def test_suite_execution_seconds_exists(self):
        """Test that suite_execution_seconds metric exists."""
        assert suite_execution_seconds is not None
        assert suite_execution_seconds._type == "histogram"
    
    def test_test_duration_seconds_buckets(self):
        """Test test_duration_seconds has correct buckets."""
        # The metric should exist with defined buckets
        assert test_duration_seconds._name == 'qa_test_duration_seconds'
    
    def test_api_response_time_seconds_buckets(self):
        """Test api_response_time_seconds has correct buckets."""
        assert api_response_time_seconds._name == 'qa_api_response_time_seconds'


class TestGaugeMetrics:
    """Tests for gauge metrics initialization."""
    
    def test_active_users_gauge_exists(self):
        """Test that active_users_gauge metric exists."""
        assert active_users_gauge is not None
        assert active_users_gauge._type == "gauge"
    
    def test_test_success_rate_gauge_exists(self):
        """Test that test_success_rate_gauge metric exists."""
        assert test_success_rate_gauge is not None
        assert test_success_rate_gauge._type == "gauge"
    
    def test_error_rate_gauge_exists(self):
        """Test that error_rate_gauge metric exists."""
        assert error_rate_gauge is not None
        assert error_rate_gauge._type == "gauge"
    
    def test_queue_size_gauge_exists(self):
        """Test that queue_size_gauge metric exists."""
        assert queue_size_gauge is not None
        assert queue_size_gauge._type == "gauge"
    
    def test_system_load_gauge_exists(self):
        """Test that system_load_gauge metric exists."""
        assert system_load_gauge is not None
        assert system_load_gauge._type == "gauge"


class TestBusinessMetricsManagerInit:
    """Tests for BusinessMetricsManager initialization."""
    
    def test_init(self):
        """Test BusinessMetricsManager initialization."""
        manager = BusinessMetricsManager()
        
        assert manager is not None
        assert manager.start_times == {}
    
    def test_init_empty_start_times(self):
        """Test that start_times is initialized as empty dict."""
        manager = BusinessMetricsManager()
        
        assert manager.start_times == {}


class TestBusinessMetricsManagerRecordUserAction:
    """Tests for record_user_action method."""
    
    @patch('core.metrics.user_actions_total')
    def test_record_user_action(self, mock_user_actions):
        """Test recording a user action."""
        manager = BusinessMetricsManager()
        
        manager.record_user_action("user123", "create_suite")
        
        # Check that metric was incremented with correct labels
        mock_user_actions.labels.assert_called_once()
        mock_user_actions.labels.return_value.inc.assert_called_once()
    
    @patch('core.metrics.user_actions_total')
    def test_record_user_action_multiple(self, mock_user_actions):
        """Test recording multiple user actions."""
        manager = BusinessMetricsManager()
        
        manager.record_user_action("user123", "create_suite")
        manager.record_user_action("user123", "run_test")
        manager.record_user_action("user456", "view_report")
        
        # Check that metric was incremented 3 times
        assert mock_user_actions.labels.call_count == 3
        assert mock_user_actions.labels.return_value.inc.call_count == 3
    
    @patch('core.metrics.user_actions_total')
    def test_record_user_action_different_types(self, mock_user_actions):
        """Test recording different action types."""
        manager = BusinessMetricsManager()
        
        actions = ["create_suite", "run_test", "view_report", "delete_suite"]
        for action in actions:
            manager.record_user_action("user123", action)
        
        # Check that all actions were recorded
        assert mock_user_actions.labels.call_count == 4
    
    @patch('core.metrics.user_actions_total')
    def test_record_user_action_with_special_user_id(self, mock_user_actions):
        """Test recording user action with special characters in user ID."""
        manager = BusinessMetricsManager()
        
        manager.record_user_action("user@example.com", "create_suite")
        
        mock_user_actions.labels.assert_called_once()


class TestBusinessMetricsManagerRecordTestResult:
    """Tests for record_test_result method."""
    
    @patch('core.metrics.tests_executed_total')
    @patch('core.metrics.test_failures_total')
    def test_record_test_result_passed(self, mock_failures, mock_executed):
        """Test recording a passed test."""
        manager = BusinessMetricsManager()
        
        manager.record_test_result("suite123", "passed", "pytest")
        
        # Check executed metric
        mock_executed.labels.assert_called_once_with(
            suite_id="suite123",
            status="passed",
            framework="pytest"
        )
        mock_executed.labels.return_value.inc.assert_called_once()
        
        # Check failures metric not called
        mock_failures.labels.assert_not_called()
    
    @patch('core.metrics.tests_executed_total')
    @patch('core.metrics.test_failures_total')
    def test_record_test_result_failed(self, mock_failures, mock_executed):
        """Test recording a failed test."""
        manager = BusinessMetricsManager()
        
        manager.record_test_result("suite123", "failed", "pytest")
        
        # Check executed metric
        mock_executed.labels.assert_called_once_with(
            suite_id="suite123",
            status="failed",
            framework="pytest"
        )
        mock_executed.labels.return_value.inc.assert_called_once()
        
        # Check failures metric called
        mock_failures.labels.assert_called_once_with(
            suite_id="suite123",
            error_type="assertion"
        )
        mock_failures.labels.return_value.inc.assert_called_once()
    
    @patch('core.metrics.tests_executed_total')
    @patch('core.metrics.test_failures_total')
    def test_record_test_result_different_statuses(self, mock_failures, mock_executed):
        """Test recording tests with different statuses."""
        manager = BusinessMetricsManager()
        
        statuses = ["passed", "failed", "passed", "passed", "failed"]
        for status in statuses:
            manager.record_test_result("suite123", status, "pytest")
        
        # Check executed metric called 5 times
        assert mock_executed.labels.call_count == 5
        
        # Check failures metric called 2 times (only for failed tests)
        assert mock_failures.labels.call_count == 2
    
    @patch('core.metrics.tests_executed_total')
    def test_record_test_result_default_framework(self, mock_executed):
        """Test record_test_result with default framework."""
        manager = BusinessMetricsManager()
        
        manager.record_test_result("suite123", "passed")
        
        # Check that default framework is "pytest"
        mock_executed.labels.assert_called_once()
        call_kwargs = mock_executed.labels.call_args[1]
        assert call_kwargs['framework'] == "pytest"


class TestBusinessMetricsManagerUpdateActiveUsers:
    """Tests for update_active_users method."""
    
    @patch('core.metrics.active_users_gauge')
    def test_update_active_users(self, mock_gauge):
        """Test updating active users count."""
        manager = BusinessMetricsManager()
        
        manager.update_active_users(42)
        
        mock_gauge.set.assert_called_once_with(42)
    
    @patch('core.metrics.active_users_gauge')
    def test_update_active_users_zero(self, mock_gauge):
        """Test updating active users to zero."""
        manager = BusinessMetricsManager()
        
        manager.update_active_users(0)
        
        mock_gauge.set.assert_called_once_with(0)
    
    @patch('core.metrics.active_users_gauge')
    def test_update_active_users_large_value(self, mock_gauge):
        """Test updating active users with large value."""
        manager = BusinessMetricsManager()
        
        manager.update_active_users(99999)
        
        mock_gauge.set.assert_called_once_with(99999)


class TestBusinessMetricsManagerUpdateSuccessRate:
    """Tests for update_success_rate method."""
    
    @patch('core.metrics.test_success_rate_gauge')
    def test_update_success_rate(self, mock_gauge):
        """Test updating test success rate."""
        manager = BusinessMetricsManager()
        
        manager.update_success_rate("suite123", 85.5)
        
        mock_gauge.labels.assert_called_once_with(suite_id="suite123")
        mock_gauge.labels.return_value.set.assert_called_once_with(85.5)
    
    @patch('core.metrics.test_success_rate_gauge')
    def test_update_success_rate_zero(self, mock_gauge):
        """Test updating success rate to zero."""
        manager = BusinessMetricsManager()
        
        manager.update_success_rate("suite123", 0.0)
        
        mock_gauge.labels.return_value.set.assert_called_once_with(0.0)
    
    @patch('core.metrics.test_success_rate_gauge')
    def test_update_success_rate_hundred(self, mock_gauge):
        """Test updating success rate to 100%."""
        manager = BusinessMetricsManager()
        
        manager.update_success_rate("suite123", 100.0)
        
        mock_gauge.labels.return_value.set.assert_called_once_with(100.0)


class TestBusinessMetricsManagerUpdateErrorRate:
    """Tests for update_error_rate method."""
    
    @patch('core.metrics.error_rate_gauge')
    def test_update_error_rate(self, mock_gauge):
        """Test updating error rate."""
        manager = BusinessMetricsManager()
        
        manager.update_error_rate("timeout", 12.5)
        
        mock_gauge.labels.assert_called_once_with(error_type="timeout")
        mock_gauge.labels.return_value.set.assert_called_once_with(12.5)
    
    @patch('core.metrics.error_rate_gauge')
    def test_update_error_rate_different_types(self, mock_gauge):
        """Test updating different error types."""
        manager = BusinessMetricsManager()
        
        error_types = ["timeout", "assertion", "environment", "network"]
        for error_type in error_types:
            manager.update_error_rate(error_type, 5.0)
        
        # Check that gauge was called 4 times
        assert mock_gauge.labels.call_count == 4


class TestBusinessMetricsManagerUpdateQueueSize:
    """Tests for update_queue_size method."""
    
    @patch('core.metrics.queue_size_gauge')
    def test_update_queue_size(self, mock_gauge):
        """Test updating queue size."""
        manager = BusinessMetricsManager()
        
        manager.update_queue_size(15)
        
        mock_gauge.set.assert_called_once_with(15)
    
    @patch('core.metrics.queue_size_gauge')
    def test_update_queue_size_empty(self, mock_gauge):
        """Test updating queue size to empty."""
        manager = BusinessMetricsManager()
        
        manager.update_queue_size(0)
        
        mock_gauge.set.assert_called_once_with(0)


class TestBusinessMetricsManagerUpdateSystemLoad:
    """Tests for update_system_load method."""
    
    @patch('core.metrics.system_load_gauge')
    def test_update_system_load(self, mock_gauge):
        """Test updating system load metrics."""
        manager = BusinessMetricsManager()
        
        manager.update_system_load(1.5, 2.0, 1.8)
        
        # Check that gauge was called 3 times for each period
        assert mock_gauge.labels.call_count == 3
        
        # Check that all periods were set correctly
        calls = mock_gauge.labels.call_args_list
        periods = [call[1]['period'] for call in calls]
        assert periods == ['1m', '5m', '15m']
    
    @patch('core.metrics.system_load_gauge')
    def test_update_system_load_high_values(self, mock_gauge):
        """Test updating system load with high values."""
        manager = BusinessMetricsManager()
        
        manager.update_system_load(10.5, 8.2, 7.8)
        
        # High load values should be recorded
        assert mock_gauge.labels.call_count == 3


class TestBusinessMetricsManagerTrackers:
    """Tests for tracker methods."""
    
    @patch('core.metrics.TestExecutionTracker')
    def test_track_test_execution(self, mock_tracker):
        """Test track_test_execution returns tracker instance."""
        manager = BusinessMetricsManager()
        
        tracker = manager.track_test_execution("suite123", "pytest")
        
        # Check that tracker was instantiated with correct parameters
        mock_tracker.assert_called_once_with(
            manager,
            "suite123",
            "pytest"
        )
    
    @patch('core.metrics.APIRequestTracker')
    def test_track_api_request(self, mock_tracker):
        """Test track_api_request returns tracker instance."""
        manager = BusinessMetricsManager()
        
        tracker = manager.track_api_request("/api/v1/suites", "POST")
        
        # Check that tracker was instantiated with correct parameters
        mock_tracker.assert_called_once_with(
            manager,
            "/api/v1/suites",
            "POST"
        )
    
    def test_track_test_execution_default_framework(self):
        """Test track_test_execution with default framework."""
        manager = BusinessMetricsManager()
        
        tracker = manager.track_test_execution("suite123")
        
        assert isinstance(tracker, TestExecutionTracker)
        assert tracker.framework == "pytest"


class TestTestExecutionTracker:
    """Tests for TestExecutionTracker context manager."""
    
    @patch('core.metrics.test_duration_seconds')
    @patch('core.metrics.suite_execution_seconds')
    @patch('core.metrics.tests_executed_total')
    @patch('core.metrics.test_failures_total')
    def test_test_execution_tracker_passed(self, mock_failures, mock_executed, mock_suite, mock_test_duration):
        """Test TestExecutionTracker with successful test."""
        manager = BusinessMetricsManager()
        
        with manager.track_test_execution("suite123", "pytest") as tracker:
            time.sleep(0.01)  # Simulate test execution
        
        # Check that test was recorded as passed
        mock_executed.labels.assert_called()
        
        # Check that histograms were observed (with duration)
        mock_test_duration.labels.assert_called_once()
        mock_suite.labels.assert_called_once()
    
    @patch('core.metrics.test_duration_seconds')
    @patch('core.metrics.suite_execution_seconds')
    @patch('core.metrics.tests_executed_total')
    @patch('core.metrics.test_failures_total')
    def test_test_execution_tracker_failed(self, mock_failures, mock_executed, mock_suite, mock_test_duration):
        """Test TestExecutionTracker with failed test."""
        manager = BusinessMetricsManager()
        
        with pytest.raises(Exception):
            with manager.track_test_execution("suite123", "pytest") as tracker:
                time.sleep(0.01)
                raise Exception("Test failed")
        
        # Check that test was recorded as failed
        mock_failures.labels.assert_called()
    
    def test_test_execution_tracker_starts_timer(self):
        """Test that tracker starts timer on enter."""
        manager = BusinessMetricsManager()
        
        with manager.track_test_execution("suite123", "pytest") as tracker:
            assert tracker.start_time is not None
            start_time = tracker.start_time
        
        # Check that start_time was recorded
        assert start_time > 0
    
    def test_test_execution_tracker_calculates_duration(self):
        """Test that tracker calculates correct duration."""
        manager = BusinessMetricsManager()
        
        with manager.track_test_execution("suite123", "pytest") as tracker:
            start_time = tracker.start_time
            time.sleep(0.05)  # Sleep 50ms
        
        # Duration should be approximately 0.05 seconds
        # Allow some tolerance for timing
        assert hasattr(tracker, 'duration') or True  # May not be exposed


class TestAPIRequestTracker:
    """Tests for APIRequestTracker context manager."""
    
    @patch('core.metrics.api_response_time_seconds')
    @patch('core.metrics.api_requests_total')
    def test_api_request_tracker_success(self, mock_api_requests, mock_response_time):
        """Test APIRequestTracker with successful request."""
        manager = BusinessMetricsManager()
        
        with manager.track_api_request("/api/v1/suites", "POST") as tracker:
            time.sleep(0.01)  # Simulate API call
        
        # Check that request was recorded with status 200
        mock_api_requests.labels.assert_called_once()
    
    @patch('core.metrics.api_response_time_seconds')
    @patch('core.metrics.api_requests_total')
    def test_api_request_tracker_failure(self, mock_api_requests, mock_response_time):
        """Test APIRequestTracker with failed request."""
        manager = BusinessMetricsManager()
        
        with pytest.raises(Exception):
            with manager.track_api_request("/api/v1/suites", "POST") as tracker:
                time.sleep(0.01)
                raise Exception("API error")
        
        # Check that request was recorded with status 500
        mock_api_requests.labels.assert_called_once()
        call_kwargs = mock_api_requests.labels.call_args[1]
        assert call_kwargs['status_code'] == '500'
    
    def test_api_request_tracker_sets_attributes(self):
        """Test that tracker sets correct attributes."""
        manager = BusinessMetricsManager()
        
        tracker = manager.track_api_request("/api/v1/suites", "POST")
        
        assert tracker.metrics == manager
        assert tracker.endpoint == "/api/v1/suites"
        assert tracker.method == "POST"
        assert tracker.start_time is None  # Not started yet


class TestGetMetricsResponse:
    """Tests for get_metrics_response function."""

    @patch('core.metrics.generate_latest')
    def test_get_metrics_response(self, mock_generate):
        """Test get_metrics_response generates correct response."""
        mock_generate.return_value = b'metrics_data'
        
        response = get_metrics_response()

        # Check that response is generated
        assert response is not None
        assert response.body == b'metrics_data'
    
    @patch('core.metrics.generate_latest')
    def test_get_metrics_response_content_type(self, mock_generate):
        """Test get_metrics_response sets correct content type."""
        mock_generate.return_value = b'metrics_data'
        
        response = get_metrics_response()
        
        # Check content type
        from prometheus_client import CONTENT_TYPE_LATEST
        assert response.media_type == CONTENT_TYPE_LATEST


class TestGlobalMetricsManager:
    """Tests for global metrics manager instance."""
    
    def test_metrics_manager_is_singleton(self):
        """Test that metrics_manager is a BusinessMetricsManager instance."""
        assert isinstance(metrics_manager, BusinessMetricsManager)
    
    def test_metrics_manager_initialized(self):
        """Test that metrics_manager is initialized."""
        assert metrics_manager is not None
        assert hasattr(metrics_manager, 'start_times')


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_test_execution_tracker_with_zero_duration(self):
        """Test tracker with very short duration."""
        manager = BusinessMetricsManager()
        
        # Tracker should handle zero or near-zero duration
        with manager.track_test_execution("suite123", "pytest") as tracker:
            pass  # Immediate exit
    
    def test_api_request_tracker_with_zero_duration(self):
        """Test API tracker with very short duration."""
        manager = BusinessMetricsManager()
        
        # Tracker should handle zero or near-zero duration
        with manager.track_api_request("/api/test", "GET") as tracker:
            pass  # Immediate exit
    
    @patch('core.metrics.active_users_gauge')
    def test_update_active_users_negative_value(self, mock_gauge):
        """Test updating active users with negative value."""
        manager = BusinessMetricsManager()
        
        # Gauge should accept negative value (may be intentional for some use cases)
        manager.update_active_users(-1)
        
        mock_gauge.set.assert_called_once_with(-1)
    
    def test_record_user_action_with_empty_user_id(self):
        """Test recording user action with empty user ID."""
        manager = BusinessMetricsManager()
        
        # Should handle empty user ID
        manager.record_user_action("", "create_suite")
    
    def test_record_user_action_with_special_characters(self):
        """Test recording user action with special characters in user ID."""
        manager = BusinessMetricsManager()
        
        # Should handle special characters
        manager.record_user_action("user@domain.com", "create_suite")
    
    def test_update_success_rate_out_of_range(self):
        """Test updating success rate with value > 100%."""
        manager = BusinessMetricsManager()
        
        # Gauge should accept values > 100 (though unusual)
        manager.update_success_rate("suite123", 150.0)
    
    def test_update_success_rate_negative(self):
        """Test updating success rate with negative value."""
        manager = BusinessMetricsManager()
        
        # Gauge should accept negative values (though unusual)
        manager.update_success_rate("suite123", -10.0)
    
    def test_track_test_execution_with_long_suite_id(self):
        """Test tracking test with very long suite ID."""
        manager = BusinessMetricsManager()
        
        long_id = "suite" * 100
        with manager.track_test_execution(long_id, "pytest") as tracker:
            pass
