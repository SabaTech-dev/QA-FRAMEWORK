"""Allure Reporting Example - Comprehensive usage demonstration.

This module demonstrates how to use the AllureReporter for comprehensive
test reporting with multiple formats, screenshots, and metadata.

Features demonstrated:
    - Basic Allure reporting with steps
    - Screenshot capture on failure
    - Test categorization (features, stories, tags)
    - Severity levels
    - Multiple report formats (HTML, JSON, XML)
    - Attachments (text, JSON, screenshots)
    - Integration with pytest
    - Async test support

Usage:
    # Run with Allure reporting
    pytest examples/allure_reporting_example.py -v --alluredir=allure-results

    # Generate HTML report
    allure serve allure-results

    # Or generate and open report
    allure generate allure-results -o reports/allure-report --clean
    allure open reports/allure-report
"""

import asyncio
import json
from pathlib import Path

import pytest
import allure

from src.adapters.reporting.allure_reporter import AllureReporter
from src.adapters.http.httpx_client import HTTPXClient


class TestAllureBasicReporting:
    """Basic Allure reporting examples."""

    @pytest.mark.asyncio
    @allure.feature("Authentication")
    @allure.story("User Login")
    @allure.severity(allure.severity_level.CRITICAL)
    async def test_allure_basic_reporting(self):
        """Test demonstrating basic Allure reporting features."""
        # Initialize reporter
        reporter = AllureReporter(
            results_dir="allure-results",
            screenshots_on_failure=True,
            clean_results=False,  # Don't clean to accumulate results
        )

        try:
            # Start test with description
            reporter.start_test(
                test_name="test_user_authentication",
                description="Verify user can authenticate with valid credentials",
            )

            # Add metadata
            reporter.add_tag("regression")
            reporter.add_tag("smoke")
            reporter.add_severity("critical")

            # Add steps
            reporter.add_step("Navigate to login page")
            reporter.add_step("Enter valid username")
            reporter.add_step("Enter valid password")
            reporter.add_step("Click login button")

            # Attach test data
            test_data = {"username": "test_user", "password": "***masked***"}
            reporter.attach_json(test_data, name="login_credentials")

            # Attach text log
            reporter.attach_text("User authentication completed successfully", name="execution_log")

            # End test with success
            reporter.end_test(status="passed", message="Authentication successful")

        finally:
            reporter.cleanup()

    @pytest.mark.asyncio
    @allure.feature("API Testing")
    @allure.story("User Management")
    @allure.severity(allure.severity_level.NORMAL)
    async def test_allure_api_reporting(self):
        """Test demonstrating API testing with Allure reporting."""
        reporter = AllureReporter(
            results_dir="allure-results", screenshots_on_failure=True, clean_results=False
        )

        client = HTTPXClient(base_url="https://jsonplaceholder.typicode.com")

        try:
            reporter.start_test(
                test_name="test_api_user_retrieval",
                description="Verify API returns user data correctly",
            )

            reporter.add_tag("api")
            reporter.add_tag("integration")

            # Step 1: Make API request
            reporter.add_step("Send GET request to /users endpoint")
            response = await client.get("/users")

            # Attach request details
            request_info = {
                "method": "GET",
                "url": "https://jsonplaceholder.typicode.com/users",
                "headers": dict(response.request.headers),
            }
            reporter.attach_json(request_info, name="request_details")

            # Step 2: Verify response
            reporter.add_step("Verify response status code is 200")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"

            # Attach response data
            response_data = response.json()
            reporter.attach_json(
                {"status_code": response.status_code, "user_count": len(response_data)},
                name="response_summary",
            )

            # Step 3: Validate user data structure
            reporter.add_step("Validate user data structure")
            first_user = response_data[0]
            required_fields = ["id", "name", "email", "username"]
            for field in required_fields:
                assert field in first_user, f"Missing required field: {field}"

            reporter.attach_text(
                f"Validated {len(response_data)} users. First user: {first_user['name']}",
                name="validation_results",
            )

            reporter.end_test(
                status="passed", message=f"Successfully retrieved {len(response_data)} users"
            )

        except Exception as e:
            reporter.end_test(status="failed", message=str(e))
            raise
        finally:
            await client.close()
            reporter.cleanup()


class TestAllureFailureReporting:
    """Examples of Allure reporting with failures and screenshots."""

    @pytest.mark.asyncio
    @allure.feature("Error Handling")
    @allure.story("Failure Documentation")
    @allure.severity(allure.severity_level.BLOCKER)
    async def test_allure_failure_with_screenshot(self, tmp_path):
        """Test demonstrating failure reporting with attachments."""
        reporter = AllureReporter(
            results_dir="allure-results", screenshots_on_failure=True, clean_results=False
        )

        try:
            reporter.start_test(
                test_name="test_with_failure_documentation",
                description="Demonstrate how failures are documented in Allure",
            )

            reporter.add_tag("error-handling")
            reporter.add_severity("critical")

            reporter.add_step("Setup test environment")
            reporter.add_step("Execute test logic")

            # Simulate a failure with screenshot
            try:
                # Create a mock screenshot
                screenshot_path = tmp_path / "failure_screenshot.png"
                screenshot_path.write_text("Mock screenshot data")

                # Simulate failure
                raise ValueError("Simulated test failure for demonstration")

            except Exception as e:
                # Capture and attach screenshot on failure
                reporter.capture_failure_screenshot(
                    lambda path: str(screenshot_path), str(screenshot_path)
                )

                # Attach error details
                error_details = {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "stack_trace": "Exception occurred in test execution",
                }
                reporter.attach_json(error_details, name="error_details")

                reporter.end_test(status="failed", message=str(e))
                raise

        finally:
            reporter.cleanup()


class TestAllureReportGeneration:
    """Examples of generating different report formats."""

    @pytest.mark.asyncio
    @allure.feature("Reporting")
    @allure.story("Report Generation")
    async def test_generate_html_report(self):
        """Test generating HTML report from Allure results."""
        reporter = AllureReporter(
            results_dir="allure-results", screenshots_on_failure=True, clean_results=False
        )

        try:
            # Create some test results first
            reporter.start_test(
                test_name="test_html_report_generation",
                description="Generate HTML format report",
            )
            reporter.add_tag("reporting")
            reporter.add_step("Collect test results")
            reporter.add_step("Generate HTML report")
            reporter.end_test(status="passed")

            # Generate HTML report
            report_path = reporter.generate_report(output_dir="reports", report_format="html")

            reporter.start_test(
                test_name="verify_html_report",
                description="Verify HTML report was generated",
            )
            reporter.attach_text(f"HTML report generated at: {report_path}", name="report_path")
            reporter.end_test(status="passed")

            assert Path(report_path).exists(), "HTML report file should exist"

        finally:
            reporter.cleanup()

    @pytest.mark.asyncio
    @allure.feature("Reporting")
    @allure.story("Report Generation")
    async def test_generate_json_report(self):
        """Test generating JSON report from Allure results."""
        reporter = AllureReporter(
            results_dir="allure-results", screenshots_on_failure=True, clean_results=False
        )

        try:
            reporter.start_test(
                test_name="test_json_report_generation",
                description="Generate JSON format report",
            )
            reporter.add_tag("reporting")
            reporter.add_step("Collect test results")
            reporter.add_step("Generate JSON report")
            reporter.end_test(status="passed")

            # Generate JSON report
            report_path = reporter.generate_report(output_dir="reports", report_format="json")

            reporter.start_test(
                test_name="verify_json_report",
                description="Verify JSON report was generated",
            )
            reporter.attach_text(f"JSON report generated at: {report_path}", name="report_path")
            reporter.end_test(status="passed")

            assert Path(report_path).exists(), "JSON report file should exist"

            # Verify it's valid JSON
            with open(report_path, "r") as f:
                report_data = json.load(f)
                assert "results" in report_data

        finally:
            reporter.cleanup()

    @pytest.mark.asyncio
    @allure.feature("Reporting")
    @allure.story("Report Generation")
    async def test_generate_xml_report(self):
        """Test generating XML (JUnit) report from Allure results."""
        reporter = AllureReporter(
            results_dir="allure-results", screenshots_on_failure=True, clean_results=False
        )

        try:
            reporter.start_test(
                test_name="test_xml_report_generation",
                description="Generate XML (JUnit) format report",
            )
            reporter.add_tag("reporting")
            reporter.add_step("Collect test results")
            reporter.add_step("Generate XML report")
            reporter.end_test(status="passed")

            # Generate XML report
            report_path = reporter.generate_report(output_dir="reports", report_format="xml")

            reporter.start_test(
                test_name="verify_xml_report",
                description="Verify XML report was generated",
            )
            reporter.attach_text(f"XML report generated at: {report_path}", name="report_path")
            reporter.end_test(status="passed")

            assert Path(report_path).exists(), "XML report file should exist"

            # Verify it's valid XML
            import xml.etree.ElementTree as ET

            tree = ET.parse(report_path)  # nosec B314 — parses the Allure XML generated above in this example
            root = tree.getroot()
            assert root.tag == "testsuites"

        finally:
            reporter.cleanup()


class TestAllureAdvancedFeatures:
    """Advanced Allure reporting features."""

    @pytest.mark.asyncio
    @allure.feature("Advanced Features")
    @allure.story("Links and References")
    @allure.issue("https://github.com/example/project/issues/123", "Related Issue")
    @allure.testcase("https://testcase.manager/tc/456", "Test Case Reference")
    @allure.link("https://confluence.company.com/docs", name="Documentation")
    async def test_allure_links_and_references(self):
        """Test demonstrating links and external references."""
        reporter = AllureReporter(
            results_dir="allure-results", screenshots_on_failure=True, clean_results=False
        )

        try:
            reporter.start_test(
                test_name="test_with_links",
                description="Demonstrate link attachments and references",
            )

            reporter.add_tag("documentation")

            # Add various link types
            reporter.add_link(
                "https://github.com/example/project", name="Source Code", link_type="link"
            )
            reporter.add_link(
                "https://github.com/example/project/issues/123",
                name="Bug #123",
                link_type="issue",
            )
            reporter.add_link(
                "https://testcase.manager/tc/456",
                name="Test Case TC-456",
                link_type="test_case",
            )

            reporter.add_step("Verify links are accessible")
            reporter.attach_text(
                "Links provide traceability to requirements, issues, and documentation",
                name="link_purpose",
            )

            reporter.end_test(status="passed", message="Links documented successfully")

        finally:
            reporter.cleanup()

    @pytest.mark.asyncio
    @allure.feature("Advanced Features")
    @allure.story("Classification and Organization")
    @allure.epic("User Management")
    async def test_allure_classification(self):
        """Test demonstrating test classification and organization."""
        reporter = AllureReporter(
            results_dir="allure-results", screenshots_on_failure=True, clean_results=False
        )

        try:
            reporter.start_test(
                test_name="test_classification",
                description="Organize tests with features, stories, and epics",
            )

            # Add classification
            reporter.add_feature("User Management")
            reporter.add_story("Account Creation")

            # Multiple tags for filtering
            tags = ["user-management", "account", "create", "regression", "api"]
            for tag in tags:
                reporter.add_tag(tag)

            reporter.add_step("Create user account")
            reporter.add_step("Verify account exists")
            reporter.add_step("Verify email sent")

            # Attach business rules
            business_rules = """
            Business Rules:
            1. User must provide valid email
            2. Password must be at least 8 characters
            3. Username must be unique
            4. Account activation email must be sent
            """
            reporter.attach_text(business_rules, name="business_rules")

            reporter.end_test(status="passed")

        finally:
            reporter.cleanup()


class TestAllureIntegrationPatterns:
    """Integration patterns with QA-FRAMEWORK."""

    @pytest.mark.asyncio
    @allure.feature("Integration")
    @allure.story("Configuration-Based Reporting")
    async def test_allure_with_configuration(self, qa_config):
        """Test using Allure with framework configuration."""
        from src.infrastructure.config.config_manager import ConfigManager

        # Get configuration
        config_manager = ConfigManager()
        config = config_manager.get_config()

        reporter = AllureReporter(
            results_dir=config.reporting.allure.results_dir,
            screenshots_on_failure=config.reporting.allure.screenshots_on_failure,
            clean_results=config.reporting.allure.clean_results,
        )

        try:
            reporter.start_test(
                test_name="test_config_integration",
                description="Use framework configuration for Allure reporting",
            )

            reporter.add_tag("configuration")

            # Attach configuration summary
            config_summary = {
                "allure_enabled": config.reporting.allure.enabled,
                "results_dir": config.reporting.allure.results_dir,
                "report_dir": config.reporting.allure.report_dir,
                "screenshots_on_failure": config.reporting.allure.screenshots_on_failure,
                "clean_results": config.reporting.allure.clean_results,
            }
            reporter.attach_json(config_summary, name="allure_configuration")

            reporter.add_step("Load framework configuration")
            reporter.add_step("Initialize Allure reporter with config")
            reporter.add_step("Execute test with reporting")

            reporter.end_test(status="passed", message="Configuration integration successful")

        finally:
            reporter.cleanup()

    @pytest.mark.asyncio
    @allure.feature("Integration")
    @allure.story("Context Manager Pattern")
    async def test_allure_context_manager(self):
        """Test using Allure reporter with async context manager."""
        async with AllureReporter(
            results_dir="allure-results", screenshots_on_failure=True, clean_results=False
        ) as reporter:
            reporter.start_test(
                test_name="test_context_manager",
                description="Use Allure reporter with context manager for automatic cleanup",
            )

            reporter.add_tag("pattern")
            reporter.add_step("Enter context")
            reporter.add_step("Perform test operations")
            reporter.attach_text("Context manager ensures cleanup", name="pattern_benefit")
            reporter.end_test(status="passed")

            # Cleanup happens automatically on context exit


if __name__ == "__main__":
    # Run tests with Allure reporting
    pytest.main([__file__, "-v", "--alluredir=allure-results"])
