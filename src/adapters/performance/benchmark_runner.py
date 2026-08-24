"""Benchmark runner for performance testing"""

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from src.adapters.performance.metrics_collector import MetricsCollector


@dataclass
class BenchmarkResult:
    """
    Results from a benchmark test.

    Attributes:
        name: Benchmark name
        iterations: Number of iterations executed
        total_time: Total execution time in seconds
        avg_time: Average time per iteration in milliseconds
        min_time: Minimum time per iteration in milliseconds
        max_time: Maximum time per iteration in milliseconds
        metadata: Additional benchmark metadata
    """

    name: str
    iterations: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def throughput(self) -> float:
        """Calculate throughput (iterations per second)."""
        if self.total_time == 0:
            return 0.0
        return self.iterations / self.total_time

    def to_dict(self) -> dict[str, Any]:
        """Convert benchmark result to dictionary."""
        return {
            "name": self.name,
            "iterations": self.iterations,
            "total_time": round(self.total_time, 4),
            "avg_time": round(self.avg_time, 4),
            "min_time": round(self.min_time, 4),
            "max_time": round(self.max_time, 4),
            "throughput": round(self.throughput, 2),
            "metadata": self.metadata,
        }


class BenchmarkRunner:
    """
    Runner for benchmark tests.

    This class provides methods to run benchmark tests on functions
    or HTTP endpoints, measuring execution time and throughput.

    Example:
        runner = BenchmarkRunner()

        async def test_function():
            return await some_async_operation()

        result = await runner.benchmark_async(test_function, iterations=1000)
        print(result.avg_time)
    """

    def __init__(self) -> None:
        """Initialize benchmark runner."""
        self._collector = MetricsCollector()

    async def benchmark_async(
        self,
        func: Callable,
        iterations: int = 100,
        warmup_iterations: int = 10,
        name: str | None = None,
    ) -> BenchmarkResult:
        """
        Benchmark an async function.

        Args:
            func: Async function to benchmark
            iterations: Number of iterations to run
            warmup_iterations: Number of warmup iterations (not measured)
            name: Optional benchmark name

        Returns:
            BenchmarkResult with timing statistics
        """
        benchmark_name = name or func.__name__
        times: list[float] = []

        # Warmup
        for _ in range(warmup_iterations):
            try:
                await func()
            except Exception:
                pass

        # Actual benchmark
        start_time = time.time()

        for i in range(iterations):
            iteration_start = time.time()
            try:
                await func()
                iteration_end = time.time()
                times.append((iteration_end - iteration_start) * 1000)  # Convert to ms
            except Exception:
                iteration_end = time.time()
                times.append((iteration_end - iteration_start) * 1000)

        end_time = time.time()
        total_time = end_time - start_time

        return BenchmarkResult(
            name=benchmark_name,
            iterations=iterations,
            total_time=total_time,
            avg_time=sum(times) / len(times) if times else 0,
            min_time=min(times) if times else 0,
            max_time=max(times) if times else 0,
            metadata={"function": func.__name__},
        )

    def benchmark_sync(
        self,
        func: Callable,
        iterations: int = 100,
        warmup_iterations: int = 10,
        name: str | None = None,
    ) -> BenchmarkResult:
        """
        Benchmark a synchronous function.

        Args:
            func: Synchronous function to benchmark
            iterations: Number of iterations to run
            warmup_iterations: Number of warmup iterations (not measured)
            name: Optional benchmark name

        Returns:
            BenchmarkResult with timing statistics
        """
        benchmark_name = name or func.__name__
        times: list[float] = []

        # Warmup
        for _ in range(warmup_iterations):
            try:
                func()
            except Exception:
                pass

        # Actual benchmark
        start_time = time.time()

        for i in range(iterations):
            iteration_start = time.time()
            try:
                func()
                iteration_end = time.time()
                times.append((iteration_end - iteration_start) * 1000)
            except Exception:
                iteration_end = time.time()
                times.append((iteration_end - iteration_start) * 1000)

        end_time = time.time()
        total_time = end_time - start_time

        return BenchmarkResult(
            name=benchmark_name,
            iterations=iterations,
            total_time=total_time,
            avg_time=sum(times) / len(times) if times else 0,
            min_time=min(times) if times else 0,
            max_time=max(times) if times else 0,
            metadata={"function": func.__name__},
        )

    async def benchmark_endpoint(
        self,
        client: Any,
        method: str,
        url: str,
        iterations: int = 100,
        payload: dict | None = None,
    ) -> BenchmarkResult:
        """
        Benchmark an HTTP endpoint.

        Args:
            client: HTTP client with async methods
            method: HTTP method (get, post, put, delete)
            url: Endpoint URL
            iterations: Number of requests to make
            payload: Optional request payload for POST/PUT

        Returns:
            BenchmarkResult with timing statistics
        """
        times: list[float] = []
        errors = 0

        start_time = time.time()

        for i in range(iterations):
            iteration_start = time.time()
            try:
                if method.lower() == "get":
                    _response = await client.get(url)
                elif method.lower() == "post":
                    _response = await client.post(url, data=payload)
                elif method.lower() == "put":
                    _response = await client.put(url, data=payload)
                elif method.lower() == "delete":
                    _response = await client.delete(url)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                iteration_end = time.time()
                times.append((iteration_end - iteration_start) * 1000)

            except Exception:
                iteration_end = time.time()
                times.append((iteration_end - iteration_start) * 1000)
                errors += 1

        end_time = time.time()
        total_time = end_time - start_time

        return BenchmarkResult(
            name=f"{method.upper()} {url}",
            iterations=iterations,
            total_time=total_time,
            avg_time=sum(times) / len(times) if times else 0,
            min_time=min(times) if times else 0,
            max_time=max(times) if times else 0,
            metadata={
                "method": method,
                "url": url,
                "errors": errors,
                "error_rate": errors / iterations if iterations > 0 else 0,
            },
        )

    def compare_benchmarks(self, results: list[BenchmarkResult]) -> dict[str, Any]:
        """
        Compare multiple benchmark results.

        Args:
            results: List of BenchmarkResult objects

        Returns:
            Dictionary with comparison analysis
        """
        if not results:
            return {}

        fastest = min(results, key=lambda r: r.avg_time)
        slowest = max(results, key=lambda r: r.avg_time)
        highest_throughput = max(results, key=lambda r: r.throughput)

        comparison = {
            "benchmarks": [r.to_dict() for r in results],
            "fastest": {"name": fastest.name, "avg_time_ms": round(fastest.avg_time, 4)},
            "slowest": {"name": slowest.name, "avg_time_ms": round(slowest.avg_time, 4)},
            "highest_throughput": {
                "name": highest_throughput.name,
                "throughput": round(highest_throughput.throughput, 2),
            },
            "summary": {
                "total_benchmarks": len(results),
                "avg_time_range_ms": {
                    "min": round(min(r.avg_time for r in results), 4),
                    "max": round(max(r.avg_time for r in results), 4),
                },
            },
        }

        return comparison
