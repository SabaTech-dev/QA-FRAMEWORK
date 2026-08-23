"""Rate limiting testing module"""

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class RateLimitType(Enum):
    """Types of rate limiting."""

    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


@dataclass
class RateLimitResult:
    """
    Result from rate limiting test.

    Attributes:
        request_number: Request sequence number
        status_code: HTTP status code
        response_time: Response time in seconds
        blocked: Whether request was blocked by rate limiter
        retry_after: Seconds to wait before retry (if blocked)
    """

    request_number: int
    status_code: int
    response_time: float
    blocked: bool
    retry_after: Optional[int] = None


class RateLimitTester:
    """
    Tester for rate limiting mechanisms.

    This class provides methods to test API endpoints for proper
    rate limiting implementation and configuration.

    Example:
        tester = RateLimitTester()

        results = await tester.test_rate_limiting(
            http_client=client,
            target_url="http://api.example.com/data",
            requests_count=100,
            time_window=10
        )

        if not results["properly_configured"]:
            print("Rate limiting needs improvement")
    """

    def __init__(self) -> None:
        """Initialize rate limit tester."""
        self._results: List[RateLimitResult] = []

    async def test_rate_limiting(
        self,
        http_client: Any,
        target_url: str,
        requests_count: int,
        time_window: int,
        method: str = "GET",
        payload: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Test rate limiting implementation.

        Args:
            http_client: HTTP client with async request methods
            target_url: URL to test
            requests_count: Number of requests to send
            time_window: Time window in seconds
            method: HTTP method (GET, POST, etc.)
            payload: Optional request payload

        Returns:
            Dictionary with rate limiting test results
        """
        self._results = []

        # Calculate delay between requests
        delay = time_window / requests_count if requests_count > 0 else 0

        start_time = time.time()

        for i in range(requests_count):
            result = await self._send_request(http_client, target_url, method, payload, i + 1)
            self._results.append(result)

            # Small delay between requests
            if delay > 0 and i < requests_count - 1:
                await asyncio.sleep(delay)

        end_time = time.time()
        total_duration = end_time - start_time

        # Analyze results
        analysis = self._analyze_results()

        return {
            "target_url": target_url,
            "requests_sent": requests_count,
            "time_window": time_window,
            "total_duration": round(total_duration, 3),
            "properly_configured": analysis["has_rate_limiting"],
            "analysis": analysis,
            "blocked_requests": analysis["blocked_count"],
            "allowed_requests": analysis["allowed_count"],
            "results": [self._result_to_dict(r) for r in self._results],
            "recommendations": self._get_recommendations(analysis),
        }

    async def test_burst_capacity(
        self, http_client: Any, target_url: str, burst_size: int = 20, method: str = "GET"
    ) -> Dict[str, Any]:
        """
        Test burst handling capacity.

        Sends multiple requests simultaneously to test
        how the system handles burst traffic.

        Args:
            http_client: HTTP client
            target_url: URL to test
            burst_size: Number of simultaneous requests
            method: HTTP method

        Returns:
            Dictionary with burst test results
        """
        self._results = []

        # Send requests concurrently
        tasks = [
            self._send_request(http_client, target_url, method, None, i + 1)
            for i in range(burst_size)
        ]

        self._results = await asyncio.gather(*tasks, return_exceptions=True)  # type: ignore

        # Filter out exceptions
        valid_results = [r for r in self._results if isinstance(r, RateLimitResult)]

        analysis = self._analyze_burst_results(valid_results)

        return {
            "test_type": "burst_capacity",
            "target_url": target_url,
            "burst_size": burst_size,
            "successful_requests": analysis["successful"],
            "blocked_requests": analysis["blocked"],
            "error_requests": analysis["errors"],
            "analysis": analysis,
            "results": [self._result_to_dict(r) for r in valid_results],
            "recommendations": self._get_burst_recommendations(analysis),
        }

    async def test_rate_limit_recovery(
        self, http_client: Any, target_url: str, limit: int = 10, recovery_time: int = 60
    ) -> Dict[str, Any]:
        """
        Test rate limit recovery time.

        Args:
            http_client: HTTP client
            target_url: URL to test
            limit: Number of requests to trigger rate limit
            recovery_time: Expected recovery time in seconds

        Returns:
            Dictionary with recovery test results
        """
        # First, trigger the rate limit
        for i in range(limit):
            await self._send_request(http_client, target_url, "GET", None, i + 1)

        # Wait for recovery
        await asyncio.sleep(recovery_time)

        # Try another request
        recovery_result = await self._send_request(http_client, target_url, "GET", None, limit + 1)

        recovered = not recovery_result.blocked

        return {
            "test_type": "rate_limit_recovery",
            "target_url": target_url,
            "limit": limit,
            "recovery_time": recovery_time,
            "recovered": recovered,
            "recovery_successful": recovered,
            "recommendations": [
                (
                    "Rate limit properly resets after window"
                    if recovered
                    else "Rate limit may not be resetting correctly"
                )
            ],
        }

    async def _send_request(
        self, http_client: Any, url: str, method: str, payload: Optional[Dict], request_number: int
    ) -> RateLimitResult:
        """Send a single request and capture result."""
        start = time.time()

        try:
            if method.upper() == "GET":
                response = await http_client.get(url)
            elif method.upper() == "POST":
                response = await http_client.post(url, data=payload)
            elif method.upper() == "PUT":
                response = await http_client.put(url, data=payload)
            elif method.upper() == "DELETE":
                response = await http_client.delete(url)
            else:
                raise ValueError(f"Unsupported method: {method}")

            elapsed = time.time() - start
            status_code = getattr(response, "status_code", 0)
            headers = dict(getattr(response, "headers", {}))

            # Check if blocked (429 = Too Many Requests)
            blocked = status_code == 429

            # Check for Retry-After header
            retry_after = None
            if blocked:
                retry_after_str = headers.get("Retry-After") or headers.get("retry-after")
                if retry_after_str:
                    try:
                        retry_after = int(retry_after_str)
                    except ValueError:
                        pass

            return RateLimitResult(
                request_number=request_number,
                status_code=status_code,
                response_time=elapsed,
                blocked=blocked,
                retry_after=retry_after,
            )

        except Exception:
            elapsed = time.time() - start
            return RateLimitResult(
                request_number=request_number, status_code=0, response_time=elapsed, blocked=False
            )

    def _analyze_results(self) -> Dict[str, Any]:
        """Analyze rate limiting results."""
        if not self._results:
            return {}

        blocked = [r for r in self._results if r.blocked]
        allowed = [r for r in self._results if not r.blocked]

        response_times = [r.response_time for r in self._results]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

        # Check for rate limiting headers
        has_rate_limiting = len(blocked) > 0

        # Check for increasing response times (backoff)
        has_backoff = self._detect_backoff()

        return {
            "has_rate_limiting": has_rate_limiting,
            "has_backoff": has_backoff,
            "blocked_count": len(blocked),
            "allowed_count": len(allowed),
            "avg_response_time": round(avg_response_time, 3),
            "max_response_time": round(max(response_times), 3) if response_times else 0,
            "min_response_time": round(min(response_times), 3) if response_times else 0,
            "first_blocked_at": blocked[0].request_number if blocked else None,
            "block_rate": len(blocked) / len(self._results) if self._results else 0,
        }

    def _analyze_burst_results(self, results: List[RateLimitResult]) -> Dict[str, Any]:
        """Analyze burst test results."""
        successful = [r for r in results if r.status_code == 200]
        blocked = [r for r in results if r.blocked]
        errors = [r for r in results if r.status_code not in [200, 429]]

        return {
            "successful": len(successful),
            "blocked": len(blocked),
            "errors": len(errors),
            "success_rate": len(successful) / len(results) if results else 0,
            "block_rate": len(blocked) / len(results) if results else 0,
        }

    def _detect_backoff(self) -> bool:
        """Detect if exponential backoff is implemented."""
        if len(self._results) < 5:
            return False

        # Check if response times increase significantly
        first_half = self._results[: len(self._results) // 2]
        second_half = self._results[len(self._results) // 2 :]

        avg_first = sum(r.response_time for r in first_half) / len(first_half)
        avg_second = sum(r.response_time for r in second_half) / len(second_half)

        # If second half is significantly slower, might indicate backoff
        return avg_second > (avg_first * 1.5)

    def _result_to_dict(self, result: RateLimitResult) -> Dict[str, Any]:
        """Convert RateLimitResult to dictionary."""
        return {
            "request_number": result.request_number,
            "status_code": result.status_code,
            "response_time": round(result.response_time, 3),
            "blocked": result.blocked,
            "retry_after": result.retry_after,
        }

    def _get_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []

        if not analysis.get("has_rate_limiting"):
            recommendations.extend(
                [
                    "CRITICAL: No rate limiting detected!",
                    "1. Implement rate limiting on all API endpoints",
                    "2. Return 429 status code when limit is exceeded",
                    "3. Include Retry-After header in rate limit responses",
                ]
            )
        else:
            recommendations.extend(
                [
                    "Rate limiting appears to be implemented",
                    "1. Ensure rate limits are appropriate for your use case",
                    "2. Consider implementing tiered rate limits for different users",
                ]
            )

        if not analysis.get("has_backoff"):
            recommendations.append(
                "3. Consider implementing exponential backoff for repeated violations"
            )

        recommendations.extend(
            [
                "4. Log rate limit events for monitoring",
                "5. Provide clear documentation about rate limits to API consumers",
            ]
        )

        return recommendations

    def _get_burst_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations for burst test."""
        if analysis["block_rate"] < 0.5:
            return [
                "System may not handle burst traffic well",
                "Consider implementing queue-based rate limiting",
                "Add circuit breaker pattern for overload protection",
            ]
        else:
            return [
                "System appears to handle burst traffic appropriately",
                "Monitor burst patterns for potential DDoS attacks",
            ]
