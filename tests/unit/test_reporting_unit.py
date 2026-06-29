"""
Unit tests for Reporting System (Allure, HTML, JSON)
"""

import pytest
import tempfile
import os
from pathlib import Path

# Skip all tests in this file if allure module is not available
pytest.importorskip("allure", reason="allure not installed. Install with: pip install allure-pytest")

from src.core.entities.test_result import TestResult, TestStatus
from src.adapters.reporting.allure_reporter import AllureReporter
from src.adapters.reporting.html_reporter import HTMLReporter
from src.adapters.reporting.json_reporter import JSONReporter


class TestAllureReporter:
    """Unit tests for AllureReporter"""
    
    def test_allure_reporter_initialization(self):
        """Test that AllureReporter can be initialized"""
        from src.infrastructure.config.config_manager import ConfigManager
        
        reporter = AllureReporter(results_dir="allure-results")
        
        assert reporter is not None
        assert str(reporter.results_dir) == "allure-results"
    
    def test_allure_report_report(self):
        """Test that AllureReporter has correct interface"""
        reporter = AllureReporter(results_dir="allure-results")
        
        # Verify it has the expected methods
        assert hasattr(reporter, 'start_test')
        assert hasattr(reporter, 'end_test')
        assert hasattr(reporter, 'generate_report')


class TestHTMLReporter:
    """Unit tests for HTMLReporter"""
    
    def test_html_reporter_initialization(self):
        """Test that HTMLReporter can be initialized"""
        reporter = HTMLReporter()
        assert reporter is not None
    
    def test_html_report_generation(self):
        """Test that HTMLReporter can generate an HTML report"""
        from src.core.entities.test_result import TestResult
        from src.infrastructure.config.config_manager import ConfigManager
        
        reporter = HTMLReporter()
        
        result = TestResult(
            test_name="test_html",
            status=TestStatus.PASSED,
            execution_time=1.5,
            metadata={"feature": "reporting"}
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            reporter.report(result, output_dir=str(tmpdir_path))
            
            # Verify that HTML file was created
            html_files = list(tmpdir_path.glob("*.html"))
            assert len(html_files) > 0


class TestJSONReporter:
    """Unit tests for JSONReporter"""
    
    def test_json_reporter_initialization(self):
        """Test that JSONReporter can be initialized"""
        reporter = JSONReporter()
        assert reporter is not None
    
    def test_json_report_generation(self):
        """Test that JSONReporter can generate a JSON report"""
        from src.core.entities.test_result import TestResult
        from src.infrastructure.config.config_manager import ConfigManager
        
        reporter = JSONReporter()
        
        result = TestResult(
            test_name="test_json",
            status=TestStatus.PASSED,
            execution_time=1.5,
            metadata={"feature": "reporting"}
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            reporter.report(result, output_dir=str(tmpdir_path))
            
            # Verify that JSON file was created
            json_files = list(tmpdir_path.glob("*.json"))
            assert len(json_files) > 0


class TestReportingIntegration:
    """Tests for reporting integration"""
    
    def test_reporters_can_be_created(self):
        """Test that all reporter types can be instantiated"""
        allure = AllureReporter()
        html = HTMLReporter()
        json = JSONReporter()
        
        assert allure is not None
        assert html is not None
        assert json is not None
    
    def test_allure_reporter_has_correct_interface(self):
        """Test that AllureReporter has expected methods"""
        reporter = AllureReporter()
        
        assert hasattr(reporter, 'start_test')
        assert hasattr(reporter, 'end_test')
        assert hasattr(reporter, 'generate_report')
        assert hasattr(reporter, 'add_step')
