"""Main performance testing client"""

from typing import Any, Dict, List, Optional

from src.adapters.performance.benchmark_runner import BenchmarkRunner
from src.adapters.performance.load_test_runner import (
    ApacheBenchAdapter,
    K6Adapter,
    LoadTestRunner,
    LocustAdapter,
)
from src.adapters.performance.metrics_collector import MetricsCollector
from src.core.interfaces import IPerformanceClient


class PerformanceClient(IPerformanceClient):
    """
    Main client for performance and load testing.

    This class provides a unified interface for various performance testing
    tools and methods, following the Facade design pattern.

    It supports:
    - Load testing with locust, k6, or Apache Bench
    - Benchmark testing
    - Stress testing
    - Metrics collection and analysis

    Example:
        client = PerformanceClient(tool="k6")

        # Run load test
        results = await client.load_test(
            target_url="http://localhost:8000/api",
            users=100,
            duration=60
        )

        # Run benchmark
        benchmark = await client.benchmark(
            target_url="http://localhost:8000/api",
            requests=1000
        )

        await client.close()
    """

    def __init__(self, tool: str = "auto", http_client: Optional[Any] = None):
        """
        Initialize performance client.

        Args:
            tool: Load testing tool to use ('locust', 'k6', 'ab', or 'auto')
            http_client: Optional HTTP client for benchmark tests
        """
        self.tool = tool
        self.http_client = http_client
        self._load_runner: Optional[LoadTestRunner] = None
        self._benchmark_runner = BenchmarkRunner()
        self._metrics_collector = MetricsCollector()
        self._closed = False

        if tool != "auto":
            self._load_runner = self._create_load_runner(tool)

    def _create_load_runner(self, tool: str) -> LoadTestRunner:
        """
        Create a load test runner based on tool name.

        Args:
            tool: Tool name ('locust', 'k6', 'ab')

        Returns:
            LoadTestRunner instance
        """
        tool = tool.lower()
        if tool in ["locust", "locustio"]:
            return LocustAdapter()
        elif tool == "k6":
            return K6Adapter()
        elif tool in ["ab", "apache_bench", "apachebench"]:
            return ApacheBenchAdapter()
        else:
            raise ValueError(f"Unsupported tool: {tool}. Use 'locust', 'k6', or 'ab'.")

    async def _detect_best_tool(self) -> str:
        """
        Detect the best available load testing tool.

        Returns:
            Name of the best available tool
        """
        # Priority: k6 > locust > ab
        tools = [("k6", K6Adapter()), ("locust", LocustAdapter()), ("ab", ApacheBenchAdapter())]

        for name, adapter in tools:
            if await adapter.is_available():
                return name

        raise RuntimeError(
            "No load testing tool found. Please install k6, locust, or Apache Bench."
        )

    async def load_test(
        self, target_url: str, users: int, duration: int, ramp_up: int = 0
    ) -> Dict[str, Any]:
        """
        Execute a load test against a target URL.

        Args:
            target_url: URL to test
            users: Number of concurrent users
            duration: Test duration in seconds
            ramp_up: Ramp-up time in seconds (default: 0)

        Returns:
            Dictionary with load test results including metrics
        """
        if self._closed:
            raise RuntimeError("Performance client is closed")

        if self.tool == "auto" and self._load_runner is None:
            detected_tool = await self._detect_best_tool()
            self._load_runner = self._create_load_runner(detected_tool)

        if self._load_runner is None:
            raise RuntimeError("No load test runner configured")

        return await self._load_runner.run_load_test(
            target_url=target_url, users=users, duration=duration, ramp_up=ramp_up
        )

    async def benchmark(self, target_url: str, requests: int) -> Dict[str, Any]:
        """
        Execute a benchmark test with fixed number of requests.

        Args:
            target_url: URL to test
            requests: Number of requests to send

        Returns:
            Dictionary with benchmark results
        """
        if self._closed:
            raise RuntimeError("Performance client is closed")

        if self.http_client is None:
            raise RuntimeError(
                "HTTP client required for benchmark. Provide http_client in constructor."
            )

        result = await self._benchmark_runner.benchmark_endpoint(
            client=self.http_client, method="GET", url=target_url, iterations=requests
        )
        return result.to_dict()

    async def stress_test(
        self, target_url: str, start_users: int, max_users: int, step_users: int, step_duration: int
    ) -> Dict[str, Any]:
        """
        Execute a stress test with gradually increasing load.

        Args:
            target_url: URL to test
            start_users: Initial number of users
            max_users: Maximum number of users
            step_users: User increment per step
            step_duration: Duration of each step in seconds

        Returns:
            Dictionary with stress test results
        """
        if self._closed:
            raise RuntimeError("Performance client is closed")

        if self.tool == "auto" and self._load_runner is None:
            detected_tool = await self._detect_best_tool()
            self._load_runner = self._create_load_runner(detected_tool)

        if self._load_runner is None:
            raise RuntimeError("No load test runner configured")

        results = []
        current_users = start_users

        while current_users <= max_users:
            step_result = await self._load_runner.run_load_test(
                target_url=target_url, users=current_users, duration=step_duration, ramp_up=0
            )

            results.append({"users": current_users, "result": step_result})

            # Check if test is still successful
            if not step_result.get("success", False):
                break

            current_users += step_users

        return {
            "stress_test": True,
            "target_url": target_url,
            "steps": results,
            "max_users_reached": current_users - step_users,
            "break_point": current_users if current_users > max_users else None,
        }

    async def run_comparison(
        self, target_url: str, configs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Run multiple load tests and compare results.

        Args:
            target_url: URL to test
            configs: List of configuration dicts with 'users' and 'duration'

        Returns:
            Dictionary with comparison results
        """
        results = []

        for config in configs:
            result = await self.load_test(
                target_url=target_url,
                users=config["users"],
                duration=config["duration"],
                ramp_up=config.get("ramp_up", 0),
            )
            results.append(result)

        # Analyze results
        successful_tests = [r for r in results if r.get("success", False)]

        comparison = {
            "target_url": target_url,
            "total_tests": len(results),
            "successful_tests": len(successful_tests),
            "failed_tests": len(results) - len(successful_tests),
            "results": results,
        }

        return comparison

    def get_metrics_collector(self) -> MetricsCollector:
        """
        Get the metrics collector instance.

        Returns:
            MetricsCollector instance
        """
        return self._metrics_collector

    async def close(self) -> None:
        """
        Close the performance client and cleanup resources.

        This method should be called when done with the client
        to release any resources.
        """
        self._closed = True

        # Cleanup any resources held by load runner
        if self._load_runner:
            # Load runners don't typically hold persistent resources
            pass

        # Cleanup HTTP client if we created it
        if self.http_client and hasattr(self.http_client, "close"):
            await self.http_client.close()

    async def __aenter__(self) -> "PerformanceClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
