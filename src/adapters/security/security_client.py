"""Main security testing client"""

from typing import Any

from src.adapters.security.auth_tester import AuthTester
from src.adapters.security.rate_limit_tester import RateLimitTester
from src.adapters.security.sql_injection_tester import SQLInjectionTester
from src.adapters.security.xss_tester import XSSTester
from src.core.interfaces import ISecurityClient


class SecurityClient(ISecurityClient):
    """
    Main client for security testing.

    This class provides a unified interface for various security testing
    capabilities including SQL injection, XSS, authentication, and rate
    limiting tests.

    It follows the Facade design pattern to provide simplified access
    to all security testing functionality.

    Example:
        client = SecurityClient(http_client)

        # Test for SQL injection
        sql_results = await client.test_sql_injection(
            target_url="http://example.com/search",
            parameter="q"
        )

        # Test for XSS
        xss_results = await client.test_xss(
            target_url="http://example.com/search",
            parameter="q"
        )

        # Test security headers
        headers_results = await client.test_security_headers(
            target_url="http://example.com"
        )

        await client.close()
    """

    def __init__(self, http_client: Any):
        """
        Initialize security client.

        Args:
            http_client: HTTP client with async request methods
        """
        self.http_client = http_client
        self._sql_tester = SQLInjectionTester()
        self._xss_tester = XSSTester()
        self._auth_tester = AuthTester()
        self._rate_limit_tester = RateLimitTester()
        self._closed = False

    async def test_sql_injection(
        self, target_url: str, parameter: str, method: str = "GET"
    ) -> dict[str, Any]:
        """
        Test for SQL injection vulnerabilities.

        Args:
            target_url: URL to test
            parameter: Parameter name to test
            method: HTTP method (GET or POST)

        Returns:
            Dictionary with test results including vulnerabilities found
        """
        if self._closed:
            raise RuntimeError("Security client is closed")

        return await self._sql_tester.test_parameter(
            http_client=self.http_client, target_url=target_url, parameter=parameter, method=method
        )

    async def test_xss(
        self, target_url: str, parameter: str, method: str = "GET"
    ) -> dict[str, Any]:
        """
        Test for Cross-Site Scripting (XSS) vulnerabilities.

        Args:
            target_url: URL to test
            parameter: Parameter name to test
            method: HTTP method (GET or POST)

        Returns:
            Dictionary with test results including vulnerabilities found
        """
        if self._closed:
            raise RuntimeError("Security client is closed")

        return await self._xss_tester.test_parameter(
            http_client=self.http_client, target_url=target_url, parameter=parameter, method=method
        )

    async def test_authentication(self, target_url: str, test_cases: list) -> dict[str, Any]:
        """
        Test authentication mechanisms.

        Args:
            target_url: URL to test (login endpoint)
            test_cases: List of authentication test cases

        Returns:
            Dictionary with authentication test results
        """
        if self._closed:
            raise RuntimeError("Security client is closed")

        return await self._auth_tester.test_authentication(
            http_client=self.http_client, login_url=target_url, test_cases=test_cases
        )

    async def test_common_credentials(
        self, login_url: str, username_field: str = "username", password_field: str = "password"
    ) -> dict[str, Any]:
        """
        Test for common/default credentials.

        Args:
            login_url: URL of the login endpoint
            username_field: Form field name for username
            password_field: Form field name for password

        Returns:
            Dictionary with test results
        """
        if self._closed:
            raise RuntimeError("Security client is closed")

        return await self._auth_tester.test_common_credentials(
            http_client=self.http_client,
            login_url=login_url,
            username_field=username_field,
            password_field=password_field,
        )

    async def test_brute_force_protection(
        self, login_url: str, valid_username: str, attempts: int = 10
    ) -> dict[str, Any]:
        """
        Test for brute force protection.

        Args:
            login_url: URL of the login endpoint
            valid_username: A valid username to test
            attempts: Number of failed login attempts

        Returns:
            Dictionary with test results
        """
        if self._closed:
            raise RuntimeError("Security client is closed")

        return await self._auth_tester.test_brute_force_protection(
            http_client=self.http_client,
            login_url=login_url,
            valid_username=valid_username,
            attempts=attempts,
        )

    async def test_rate_limiting(
        self, target_url: str, requests_count: int, time_window: int
    ) -> dict[str, Any]:
        """
        Test rate limiting implementation.

        Args:
            target_url: URL to test
            requests_count: Number of requests to send
            time_window: Time window in seconds

        Returns:
            Dictionary with rate limiting test results
        """
        if self._closed:
            raise RuntimeError("Security client is closed")

        return await self._rate_limit_tester.test_rate_limiting(
            http_client=self.http_client,
            target_url=target_url,
            requests_count=requests_count,
            time_window=time_window,
        )

    async def test_security_headers(self, target_url: str) -> dict[str, Any]:
        """
        Test for security headers presence and configuration.

        Args:
            target_url: URL to test

        Returns:
            Dictionary with security headers analysis
        """
        if self._closed:
            raise RuntimeError("Security client is closed")

        try:
            response = await self.http_client.get(target_url)
            headers = dict(getattr(response, "headers", {}))

            # Define security headers to check
            security_headers = {
                "Strict-Transport-Security": {
                    "required": True,
                    "description": "HSTS - Forces HTTPS connections",
                    "recommendation": "max-age=31536000; includeSubDomains",
                },
                "Content-Security-Policy": {
                    "required": True,
                    "description": "CSP - Prevents XSS and data injection",
                    "recommendation": "default-src 'self'; script-src 'self'",
                },
                "X-Content-Type-Options": {
                    "required": True,
                    "description": "Prevents MIME type sniffing",
                    "recommendation": "nosniff",
                },
                "X-Frame-Options": {
                    "required": True,
                    "description": "Prevents clickjacking",
                    "recommendation": "DENY or SAMEORIGIN",
                },
                "X-XSS-Protection": {
                    "required": False,
                    "description": "Legacy XSS protection (modern browsers use CSP)",
                    "recommendation": "1; mode=block",
                },
                "Referrer-Policy": {
                    "required": True,
                    "description": "Controls referrer information",
                    "recommendation": "strict-origin-when-cross-origin",
                },
                "Permissions-Policy": {
                    "required": False,
                    "description": "Controls browser features",
                    "recommendation": "camera=(), microphone=(), geolocation=()",
                },
            }

            # Check each header
            header_results = []
            missing_required = []

            for header_name, config in security_headers.items():
                header_value = headers.get(header_name) or headers.get(header_name.lower())

                present = header_value is not None
                result = {
                    "header": header_name,
                    "present": present,
                    "value": header_value,
                    "required": config["required"],
                    "description": config["description"],
                    "recommendation": config["recommendation"],
                }

                if config["required"] and not present:
                    missing_required.append(header_name)
                    result["status"] = "missing_required"
                elif present:
                    result["status"] = "present"
                else:
                    result["status"] = "missing_optional"

                header_results.append(result)

            # Calculate score
            total_required = sum(1 for h in security_headers.values() if h["required"])
            present_required = total_required - len(missing_required)
            score = (present_required / total_required * 100) if total_required > 0 else 100

            return {
                "target_url": target_url,
                "score": round(score, 1),
                "grade": self._calculate_grade(score),
                "headers_present": present_required,
                "headers_required": total_required,
                "missing_required": missing_required,
                "header_results": header_results,
                "recommendations": self._get_header_recommendations(missing_required),
            }

        except Exception as e:
            return {
                "target_url": target_url,
                "error": str(e),
                "score": 0,
                "grade": "F",
                "recommendations": ["Unable to test security headers due to error"],
            }

    async def run_full_security_scan(
        self, target_url: str, parameters: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Run a comprehensive security scan.

        Args:
            target_url: Base URL to scan
            parameters: List of parameters to test (optional)

        Returns:
            Dictionary with complete security scan results
        """
        results: dict[str, Any] = {
            "target_url": target_url,
            "scan_timestamp": None,  # Would be datetime.now()
            "tests": {},
        }

        # Test security headers
        results["tests"]["security_headers"] = await self.test_security_headers(target_url)

        # Test for SQL injection on common parameters
        if parameters:
            sql_results = []
            for param in parameters:
                result = await self.test_sql_injection(target_url, param)
                sql_results.append(result)
            results["tests"]["sql_injection"] = sql_results

        # Test for XSS on common parameters
        if parameters:
            xss_results = []
            for param in parameters:
                result = await self.test_xss(target_url, param)
                xss_results.append(result)
            results["tests"]["xss"] = xss_results

        # Calculate overall security score
        scores = []
        if "security_headers" in results["tests"]:
            scores.append(results["tests"]["security_headers"].get("score", 0))

        results["overall_score"] = round(sum(scores) / len(scores), 1) if scores else 0
        results["overall_grade"] = self._calculate_grade(results["overall_score"])

        return results

    def _calculate_grade(self, score: float) -> str:
        """Calculate letter grade from score."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def _get_header_recommendations(self, missing_required: list[str]) -> list[str]:
        """Generate recommendations for missing headers."""
        if not missing_required:
            return ["All required security headers are present. Good job!"]

        recommendations = [
            f"Missing required security headers: {', '.join(missing_required)}",
            "",
            "Add the following headers to your server configuration:",
        ]

        header_examples = {
            "Strict-Transport-Security": "Strict-Transport-Security: max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "Content-Security-Policy: default-src 'self'; script-src 'self'",
            "X-Content-Type-Options": "X-Content-Type-Options: nosniff",
            "X-Frame-Options": "X-Frame-Options: DENY",
            "Referrer-Policy": "Referrer-Policy: strict-origin-when-cross-origin",
        }

        for header in missing_required:
            if header in header_examples:
                recommendations.append(f"  {header_examples[header]}")

        return recommendations

    async def close(self) -> None:
        """
        Close the security client and cleanup resources.

        This method should be called when done with the client
        to release any resources.
        """
        self._closed = True

        # Close HTTP client if we created it
        if self.http_client and hasattr(self.http_client, "close"):
            await self.http_client.close()

    async def __aenter__(self) -> "SecurityClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
