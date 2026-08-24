"""Load test runner with support for multiple tools"""

import asyncio
import os
import subprocess
import tempfile
from abc import ABC, abstractmethod
from typing import Any

from src.adapters.performance.metrics_collector import MetricsCollector


class LoadTestRunner(ABC):
    """
    Abstract base class for load test runners.

    This class defines the interface for load testing adapters,
    following the Strategy pattern from GoF design patterns.
    """

    @abstractmethod
    async def run_load_test(
        self, target_url: str, users: int, duration: int, ramp_up: int = 0
    ) -> dict[str, Any]:
        """
        Run load test.

        Args:
            target_url: URL to test
            users: Number of concurrent users
            duration: Test duration in seconds
            ramp_up: Ramp-up time in seconds

        Returns:
            Dictionary with test results
        """

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the load testing tool is available."""


class LocustAdapter(LoadTestRunner):
    """
    Adapter for Locust load testing tool.

    Locust is a scalable load testing tool written in Python.
    """

    def __init__(self, locustfile: str | None = None):
        """
        Initialize Locust adapter.

        Args:
            locustfile: Path to locustfile.py (optional)
        """
        self.locustfile = locustfile
        self._collector = MetricsCollector()

    async def is_available(self) -> bool:
        """Check if locust is installed."""
        try:
            result = subprocess.run(
                ["locust", "--version"], capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    async def run_load_test(
        self, target_url: str, users: int, duration: int, ramp_up: int = 0
    ) -> dict[str, Any]:
        """
        Run load test using Locust.

        Args:
            target_url: URL to test
            users: Number of concurrent users
            duration: Test duration in seconds
            ramp_up: Ramp-up time in seconds

        Returns:
            Dictionary with test results
        """
        if not await self.is_available():
            raise RuntimeError("Locust is not installed. Install with: pip install locust")

        # Create temporary locustfile if not provided
        locustfile_path = self.locustfile or self._create_temp_locustfile(target_url)

        try:
            cmd = [
                "locust",
                "-f",
                locustfile_path,
                "--host",
                target_url,
                "-u",
                str(users),
                "-t",
                f"{duration}s",
                "--headless",
                "--csv",
                "/tmp/locust_results",
            ]

            if ramp_up > 0:
                cmd.extend(["-r", str(max(1, users // ramp_up))])

            self._collector.start_collection()
            start_time = asyncio.get_event_loop().time()

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            end_time = asyncio.get_event_loop().time()
            self._collector.stop_collection()

            # Parse results from CSV or stdout
            results = self._parse_results(stdout.decode(), end_time - start_time)

            return {
                "tool": "locust",
                "target_url": target_url,
                "users": users,
                "duration": duration,
                "success": process.returncode == 0,
                "results": results,
                "output": stdout.decode(),
                "errors": stderr.decode() if stderr else None,
            }

        finally:
            if not self.locustfile and os.path.exists(locustfile_path):
                os.remove(locustfile_path)

    def _create_temp_locustfile(self, target_url: str) -> str:
        """Create a temporary locustfile."""
        content = """
from locust import HttpUser, task, between

class QuickstartUser(HttpUser):
    wait_time = between(1, 2)
    
    @task
    def index_page(self):
        self.client.get("/")
"""
        fd, path = tempfile.mkstemp(suffix=".py")
        with os.fdopen(fd, "w") as f:
            f.write(content)
        return path

    def _parse_results(self, output: str, duration: float) -> dict[str, Any]:
        """Parse locust output to extract metrics."""
        # This is a simplified parser - in production, you'd parse CSV files
        return {
            "duration": duration,
            "raw_output": output[:1000],  # First 1000 chars for debugging
        }


class K6Adapter(LoadTestRunner):
    """
    Adapter for k6 load testing tool.

    k6 is a modern load testing tool built with Go and JavaScript.
    """

    def __init__(self, script: str | None = None):
        """
        Initialize k6 adapter.

        Args:
            script: Path to k6 script (optional)
        """
        self.script = script
        self._collector = MetricsCollector()

    async def is_available(self) -> bool:
        """Check if k6 is installed."""
        try:
            result = subprocess.run(["k6", "version"], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    async def run_load_test(
        self, target_url: str, users: int, duration: int, ramp_up: int = 0
    ) -> dict[str, Any]:
        """
        Run load test using k6.

        Args:
            target_url: URL to test
            users: Number of concurrent users
            duration: Test duration in seconds
            ramp_up: Ramp-up time in seconds

        Returns:
            Dictionary with test results
        """
        if not await self.is_available():
            raise RuntimeError(
                "k6 is not installed. Visit: https://k6.io/docs/getting-started/installation/"
            )

        script_path = self.script or self._create_temp_script(target_url)

        try:
            cmd = [
                "k6",
                "run",
                "--vus",
                str(users),
                "--duration",
                f"{duration}s",
                "--summary-export",
                "/tmp/k6_summary.json",
            ]

            if ramp_up > 0:
                cmd.extend(["--ramp-up", f"{ramp_up}s"])

            cmd.append(script_path)

            self._collector.start_collection()
            _start_time = asyncio.get_event_loop().time()

            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            _end_time = asyncio.get_event_loop().time()
            self._collector.stop_collection()

            # Try to load k6 summary if available
            results = self._load_k6_summary()

            return {
                "tool": "k6",
                "target_url": target_url,
                "users": users,
                "duration": duration,
                "success": process.returncode == 0,
                "results": results,
                "output": stdout.decode(),
                "errors": stderr.decode() if stderr else None,
            }

        finally:
            if not self.script and os.path.exists(script_path):
                os.remove(script_path)

    def _create_temp_script(self, target_url: str) -> str:
        """Create a temporary k6 script."""
        content = f"""
import http from 'k6/http';
import {{ check, sleep }} from 'k6';

export default function() {{
    let response = http.get("{target_url}");
    check(response, {{'status is 200': (r) => r.status === 200}});
    sleep(1);
}}
"""
        fd, path = tempfile.mkstemp(suffix=".js")
        with os.fdopen(fd, "w") as f:
            f.write(content)
        return path

    def _load_k6_summary(self) -> dict[str, Any]:
        """Load k6 summary JSON if available."""
        try:
            import json
            from typing import cast

            with open("/tmp/k6_summary.json", "r") as f:
                data = json.load(f)
                return cast(dict[str, Any], data)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}


class ApacheBenchAdapter(LoadTestRunner):
    """
    Adapter for Apache Bench (ab) load testing tool.

    ab is a simple command-line tool for benchmarking HTTP servers.
    """

    def __init__(self) -> None:
        """Initialize Apache Bench adapter."""
        self._collector = MetricsCollector()

    async def is_available(self) -> bool:
        """Check if ab is installed."""
        try:
            result = subprocess.run(["ab", "-V"], capture_output=True, text=True, timeout=5)
            return result.returncode == 0 or "ApacheBench" in result.stderr
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    async def run_load_test(
        self, target_url: str, users: int, duration: int, ramp_up: int = 0
    ) -> dict[str, Any]:
        """
        Run load test using Apache Bench.

        Note: Apache Bench uses concurrency (-c) instead of users and
        requests (-n) instead of duration. We approximate duration.

        Args:
            target_url: URL to test
            users: Number of concurrent connections
            duration: Test duration in seconds (approximated via request count)
            ramp_up: Not supported by ab

        Returns:
            Dictionary with test results
        """
        if not await self.is_available():
            raise RuntimeError(
                "Apache Bench (ab) is not installed. Install with: sudo apt-get install apache2-utils"
            )

        # Estimate total requests based on duration (assuming 1 req/sec per user)
        total_requests = users * duration

        cmd = [
            "ab",
            "-n",
            str(total_requests),
            "-c",
            str(users),
            "-e",
            "/tmp/ab_results.csv",
            target_url,
        ]

        self._collector.start_collection()
        _start_time = asyncio.get_event_loop().time()

        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        _end_time = asyncio.get_event_loop().time()
        self._collector.stop_collection()

        results = self._parse_ab_output(stdout.decode())

        return {
            "tool": "apache_bench",
            "target_url": target_url,
            "users": users,
            "duration": duration,
            "success": process.returncode == 0,
            "results": results,
            "output": stdout.decode(),
            "errors": stderr.decode() if stderr else None,
        }

    def _parse_ab_output(self, output: str) -> dict[str, Any]:
        """Parse Apache Bench output to extract metrics."""
        results = {}

        lines = output.split("\n")
        for line in lines:
            if "Requests per second:" in line:
                try:
                    results["requests_per_second"] = float(line.split(":")[1].split("[")[0].strip())
                except (ValueError, IndexError):
                    pass
            elif "Time per request:" in line and "mean" not in line:
                try:
                    results["time_per_request_ms"] = float(line.split(":")[1].split("[")[0].strip())
                except (ValueError, IndexError):
                    pass
            elif "Failed requests:" in line:
                try:
                    results["failed_requests"] = int(line.split(":")[1].strip())
                except (ValueError, IndexError):
                    pass
            elif "Total transferred:" in line:
                try:
                    results["total_transferred_bytes"] = int(line.split(":")[1].strip().split()[0])
                except (ValueError, IndexError):
                    pass

        return results
