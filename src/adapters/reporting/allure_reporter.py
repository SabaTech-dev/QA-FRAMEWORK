"""Allure Reporter adapter for test reporting (async-compatible).

This module provides an Allure-based reporting adapter that implements
the IReporter interface, following Clean Architecture and SOLID principles.
"""

import json
import os
import shutil
import subprocess
from enum import Enum
from pathlib import Path
from typing import Any

import allure
from allure_commons.types import AttachmentType

from src.core.interfaces import IReporter


class ReportFormat(Enum):
    """Supported report formats."""

    HTML = "html"
    JSON = "json"
    XML = "xml"


class TestStatus(Enum):
    """Test status values for Allure."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BROKEN = "broken"


class SeverityLevel(Enum):
    """Severity levels for Allure reports."""

    BLOCKER = "blocker"
    CRITICAL = "critical"
    NORMAL = "normal"
    MINOR = "minor"
    TRIVIAL = "trivial"


class AllureReporter(IReporter):
    """
    Allure reporting adapter implementing IReporter interface.

    This adapter provides comprehensive test reporting capabilities using
    Allure Framework, supporting multiple output formats (HTML, JSON, XML)
    and automatic screenshot capture on test failures.

    Features:
        - Multi-format report generation (HTML, JSON, XML)
        - Automatic screenshot capture on failure
        - Step-by-step test documentation
        - Attachment support (screenshots, text, JSON)
        - Tag and severity classification
        - Pytest integration support

    Example:
        >>> reporter = AllureReporter(results_dir="allure-results")
        >>> reporter.start_test("test_login", "Test user login functionality")
        >>> reporter.add_step("Enter credentials")
        >>> reporter.add_step("Click login button")
        >>> reporter.end_test("passed")
        >>> reporter.generate_report("reports", "html")

    Attributes:
        results_dir: Directory for Allure result files
        screenshots_on_failure: Whether to auto-capture screenshots on failure
        current_test: Name of the currently executing test
    """

    def __init__(
        self,
        results_dir: str = "allure-results",
        screenshots_on_failure: bool = True,
        clean_results: bool = True,
    ):
        """
        Initialize Allure reporter.

        Args:
            results_dir: Directory to store Allure result files
            screenshots_on_failure: Enable automatic screenshot capture on failure
            clean_results: Clean results directory on initialization
        """
        self.results_dir = Path(results_dir)
        self.screenshots_on_failure = screenshots_on_failure
        self.current_test: str | None = None
        self._steps: list[dict[str, Any]] = []
        self._tags: list[str] = []

        # Create results directory
        if clean_results and self.results_dir.exists():
            shutil.rmtree(self.results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Set Allure environment variable
        os.environ["ALLURE_RESULTS_DIR"] = str(self.results_dir.absolute())

    def start_test(self, test_name: str, description: str | None = None) -> None:
        """
        Start reporting for a test case.

        Args:
            test_name: Name of the test case
            description: Optional test description
        """
        self.current_test = test_name
        self._steps = []
        self._tags = []

        # Use allure.title and allure.description decorators via dynamic attachment
        allure.dynamic.title(test_name)
        if description:
            allure.dynamic.description(description)

    def end_test(self, status: str, message: str | None = None) -> None:
        """
        End reporting for current test case.

        Args:
            status: Test status (passed, failed, skipped, broken)
            message: Optional status message or error details
        """
        if not self.current_test:
            return

        # Map status to Allure status
        allure_status = self._map_status(status)

        # Add status label
        allure.dynamic.label("status", allure_status.value)

        # Add failure details if present
        if message and status in ("failed", "broken"):
            allure.dynamic.description_html(f"<b>Error:</b> {message}")

        self.current_test = None
        self._steps = []

    def add_step(self, step_name: str, status: str | None = None) -> None:
        """
        Add a step to the current test.

        Args:
            step_name: Name of the step
            status: Optional step status
        """
        step_info = {"name": step_name, "status": status or "passed"}
        self._steps.append(step_info)

        # Use allure.step context manager via dynamic step
        with allure.step(step_name):
            if status and status != "passed":
                allure.dynamic.label("step_status", status)

    def attach_screenshot(self, screenshot_path: str, name: str | None = None) -> None:
        """
        Attach a screenshot to the current test report.

        Args:
            screenshot_path: Path to the screenshot file
            name: Optional name for the attachment
        """
        attachment_name = name or "screenshot"
        file_path = Path(screenshot_path)

        if file_path.exists():
            allure.attach.file(
                str(file_path.absolute()),
                name=attachment_name,
                attachment_type=AttachmentType.PNG,
            )

    def attach_text(self, content: str, name: str) -> None:
        """
        Attach text content to the current test report.

        Args:
            content: Text content to attach
            name: Name of the attachment
        """
        allure.attach(content, name=name, attachment_type=AttachmentType.TEXT)

    def attach_json(self, data: dict[str, Any], name: str) -> None:
        """
        Attach JSON data to the current test report.

        Args:
            data: Dictionary to serialize as JSON
            name: Name of the attachment
        """
        json_content = json.dumps(data, indent=2, default=str)
        allure.attach(json_content, name=name, attachment_type=AttachmentType.JSON)

    def add_tag(self, tag: str) -> None:
        """
        Add a tag/label to the current test.

        Args:
            tag: Tag to add
        """
        self._tags.append(tag)
        allure.dynamic.tag(tag)

    def add_severity(self, level: str) -> None:
        """
        Set severity level for the current test.

        Args:
            level: Severity level (blocker, critical, normal, minor, trivial)
        """
        severity = self._map_severity(level)
        allure.dynamic.severity(severity)

    def generate_report(self, output_dir: str, report_format: str = "html") -> str:
        """
        Generate the final report in specified format.

        Args:
            output_dir: Directory to save the report
            report_format: Report format (html, json, xml)

        Returns:
            Path to the generated report

        Raises:
            ValueError: If report format is not supported
            RuntimeError: If report generation fails
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        report_format_enum = ReportFormat(report_format.lower())

        if report_format_enum == ReportFormat.HTML:
            return self._generate_html_report(output_path)
        elif report_format_enum == ReportFormat.JSON:
            return self._generate_json_report(output_path)
        elif report_format_enum == ReportFormat.XML:
            return self._generate_xml_report(output_path)
        else:
            raise ValueError(f"Unsupported report format: {report_format}")

    def capture_failure_screenshot(
        self, screenshot_func: Any, *args: Any, **kwargs: Any
    ) -> str | None:
        """
        Capture screenshot on test failure.

        This method should be called in exception handlers to automatically
        capture and attach screenshots when tests fail.

        Args:
            screenshot_func: Function that captures and saves screenshot
            *args: Arguments for screenshot function
            **kwargs: Keyword arguments for screenshot function

        Returns:
            Path to saved screenshot or None if capture failed
        """
        if not self.screenshots_on_failure:
            return None

        try:
            screenshot_path = screenshot_func(*args, **kwargs)
            if screenshot_path and Path(screenshot_path).exists():
                self.attach_screenshot(screenshot_path, name="failure_screenshot")
                return str(screenshot_path)
        except Exception:
            # Silently fail if screenshot capture fails
            pass

        return None

    def add_feature(self, feature_name: str) -> None:
        """
        Add feature classification to current test.

        Args:
            feature_name: Name of the feature
        """
        allure.dynamic.feature(feature_name)

    def add_story(self, story_name: str) -> None:
        """
        Add story classification to current test.

        Args:
            story_name: Name of the story
        """
        allure.dynamic.story(story_name)

    def add_link(self, url: str, name: str | None = None, link_type: str = "link") -> None:
        """
        Add a link to the test report.

        Args:
            url: URL to link
            name: Display name for the link
            link_type: Type of link (link, issue, test_case)
        """
        allure.dynamic.link(url, name=name, link_type=link_type)

    def cleanup(self) -> None:
        """Cleanup resources and close reporter."""
        self.current_test = None
        self._steps = []
        self._tags = []

    def _map_status(self, status: str) -> TestStatus:
        """
        Map string status to TestStatus enum.

        Args:
            status: Status string

        Returns:
            TestStatus enum value
        """
        status_map = {
            "passed": TestStatus.PASSED,
            "failed": TestStatus.FAILED,
            "error": TestStatus.BROKEN,
            "broken": TestStatus.BROKEN,
            "skipped": TestStatus.SKIPPED,
        }
        return status_map.get(status.lower(), TestStatus.BROKEN)

    def _map_severity(self, level: str) -> str:
        """
        Map string severity to Allure severity level.

        Args:
            level: Severity string

        Returns:
            Allure severity level string
        """
        severity_map = {
            "blocker": "blocker",
            "critical": "critical",
            "normal": "normal",
            "minor": "minor",
            "trivial": "trivial",
        }
        return severity_map.get(level.lower(), "normal")

    def _generate_html_report(self, output_path: Path) -> str:
        """
        Generate HTML report using Allure CLI.

        Args:
            output_path: Directory to save the report

        Returns:
            Path to generated HTML report

        Raises:
            RuntimeError: If Allure CLI is not installed or generation fails
        """
        report_dir = output_path / "html-report"

        try:
            # Try to use allure command line tool
            _result = subprocess.run(
                [
                    "allure",
                    "generate",
                    str(self.results_dir),
                    "-o",
                    str(report_dir),
                    "--clean",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            index_file = report_dir / "index.html"
            if index_file.exists():
                return str(index_file.absolute())
            else:
                return str(report_dir.absolute())

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to generate HTML report: {e.stderr}")
        except FileNotFoundError:
            # Fallback: create a basic HTML report manually
            return self._generate_fallback_html(output_path)

    def _generate_json_report(self, output_path: Path) -> str:
        """
        Generate JSON report from Allure results.

        Args:
            output_path: Directory to save the report

        Returns:
            Path to generated JSON report
        """
        report_file = output_path / "report.json"

        # Collect all result files
        results = []
        for result_file in self.results_dir.glob("*-result.json"):
            with open(result_file, "r", encoding="utf-8") as f:
                results.append(json.load(f))

        # Write combined JSON report
        report_data = {
            "report_name": "QA Framework Test Report",
            "results": results,
            "total_tests": len(results),
        }

        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, default=str)

        return str(report_file.absolute())

    def _generate_xml_report(self, output_path: Path) -> str:
        """
        Generate JUnit-style XML report.

        Args:
            output_path: Directory to save the report

        Returns:
            Path to generated XML report
        """
        report_file = output_path / "report.xml"

        # Collect results and convert to JUnit XML format
        import xml.etree.ElementTree as ET

        testsuites = ET.Element("testsuites")

        # Group by feature (simple approach)
        testsuite = ET.SubElement(
            testsuites,
            "testsuite",
            {
                "name": "QA Framework Tests",
                "tests": "0",
                "failures": "0",
                "errors": "0",
                "skipped": "0",
            },
        )

        test_count = 0
        failure_count = 0
        error_count = 0
        skipped_count = 0

        for result_file in self.results_dir.glob("*-result.json"):
            with open(result_file, "r", encoding="utf-8") as f:
                result = json.load(f)

            testcase = ET.SubElement(testsuite, "testcase", {"name": result.get("name", "Unknown")})

            status = result.get("status", "passed")
            test_count += 1

            if status == "failed":
                failure = ET.SubElement(
                    testcase,
                    "failure",
                    {"message": result.get("statusDetails", {}).get("message", "")},
                )
                failure.text = result.get("statusDetails", {}).get("trace", "")
                failure_count += 1
            elif status == "broken":
                error = ET.SubElement(
                    testcase,
                    "error",
                    {"message": result.get("statusDetails", {}).get("message", "")},
                )
                error.text = result.get("statusDetails", {}).get("trace", "")
                error_count += 1
            elif status == "skipped":
                ET.SubElement(testcase, "skipped")
                skipped_count += 1

        # Update counts
        testsuite.set("tests", str(test_count))
        testsuite.set("failures", str(failure_count))
        testsuite.set("errors", str(error_count))
        testsuite.set("skipped", str(skipped_count))

        # Write XML
        tree = ET.ElementTree(testsuites)
        ET.indent(tree, space="  ", level=0)
        tree.write(report_file, encoding="unicode", xml_declaration=True)

        return str(report_file.absolute())

    def _generate_fallback_html(self, output_path: Path) -> str:
        """
        Generate a basic HTML report without Allure CLI.

        Args:
            output_path: Directory to save the report

        Returns:
            Path to generated HTML report
        """
        report_file = output_path / "fallback-report.html"

        # Collect results
        results = []
        for result_file in self.results_dir.glob("*-result.json"):
            with open(result_file, "r", encoding="utf-8") as f:
                results.append(json.load(f))

        # Generate basic HTML
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>QA Framework Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .test {{ margin: 10px 0; padding: 10px; border-radius: 5px; }}
        .passed {{ background-color: #d4edda; border: 1px solid #c3e6cb; }}
        .failed {{ background-color: #f8d7da; border: 1px solid #f5c6cb; }}
        .skipped {{ background-color: #fff3cd; border: 1px solid #ffeeba; }}
        .broken {{ background-color: #f8d7da; border: 1px solid #f5c6cb; }}
        .status {{ font-weight: bold; }}
        .summary {{ margin: 20px 0; padding: 15px; background-color: #e9ecef; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>QA Framework Test Report</h1>
    <div class="summary">
        <h2>Summary</h2>
        <p>Total Tests: {len(results)}</p>
        <p>Passed: {sum(1 for r in results if r.get("status") == "passed")}</p>
        <p>Failed: {sum(1 for r in results if r.get("status") == "failed")}</p>
        <p>Broken: {sum(1 for r in results if r.get("status") == "broken")}</p>
        <p>Skipped: {sum(1 for r in results if r.get("status") == "skipped")}</p>
    </div>
    <h2>Test Results</h2>
"""

        for result in results:
            status = result.get("status", "unknown")
            name = result.get("name", "Unknown")
            description = result.get("description", "")

            html_content += f"""
    <div class="test {status}">
        <span class="status">[{status.upper()}]</span> <strong>{name}</strong>
        {f"<br><small>{description}</small>" if description else ""}
    </div>
"""

        html_content += """
</body>
</html>
"""

        with open(report_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        return str(report_file.absolute())

    async def __aenter__(self) -> "AllureReporter":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        self.cleanup()
