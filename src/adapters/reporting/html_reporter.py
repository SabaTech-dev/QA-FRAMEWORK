"""
HTML Reporter for QA Framework

Simple HTML test report generator.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional


class HTMLReporter:
    """
    HTML report generator for test results.

    Generates simple HTML reports with test results summary.
    """

    def __init__(self, config: Optional[Any] = None) -> None:
        """
        Initialize HTML reporter.

        Args:
            config: Optional configuration (not used in basic implementation)
        """
        self.config = config
        self.results: List[Any] = []

    def report(self, result: Any, output_dir: str) -> str:
        """
        Generate HTML report for a test result.

        Args:
            result: TestResult object or similar
            output_dir: Directory to save the report

        Returns:
            Path to the generated report
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        report_file = output_path / "report.html"

        # Generate simple HTML report
        html_content = self._generate_html(result)

        with open(report_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        return str(report_file)

    def _generate_html(self, result: Any) -> str:
        """
        Generate HTML content for the report.

        Args:
            result: Test result object

        Returns:
            HTML string
        """
        test_name = getattr(result, "test_name", "Unknown Test")
        status = getattr(result, "status", "unknown")
        duration = getattr(result, "duration", 0)
        message = getattr(result, "message", "")

        status_color = {
            "passed": "green",
            "failed": "red",
            "skipped": "orange",
            "broken": "purple",
        }.get(str(status).lower(), "gray")

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Test Report - {test_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background: #333; color: white; padding: 20px; }}
        .result {{ margin: 20px 0; padding: 15px; border-left: 4px solid {status_color}; }}
        .status {{ font-weight: bold; color: {status_color}; }}
        .meta {{ color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>QA Framework Test Report</h1>
        <p>Generated: {datetime.now().isoformat()}</p>
    </div>
    <div class="result">
        <h2>{test_name}</h2>
        <p class="status">Status: {status}</p>
        <p class="meta">Duration: {duration}s</p>
        <p>{message}</p>
    </div>
</body>
</html>"""

        return html
