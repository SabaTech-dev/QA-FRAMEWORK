"""
Unit tests for Security Testing Module.

This module tests the security testing adapters including:
- SQLInjectionTester
- XSSTester
- AuthTester
- RateLimitTester
- SecurityClient
"""

# Add src to path
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.adapters.security import (
    AuthTester,
    RateLimitTester,
    SecurityClient,
    SQLInjectionTester,
    XSSTester,
)
from src.adapters.security.auth_tester import AuthTestCase, AuthTestType
from src.adapters.security.sql_injection_tester import InjectionType, SQLInjectionPayload
from src.adapters.security.xss_tester import XSSPayload, XSSType


class TestSQLInjectionTester:
    """Test suite for SQLInjectionTester."""

    def test_initialization(self):
        """Test SQL injection tester initialization."""
        tester = SQLInjectionTester()
        assert tester is not None
        assert len(tester.payloads) > 0

    def test_custom_payloads(self):
        """Test initialization with custom payloads."""
        custom_payloads = [
            SQLInjectionPayload(
                payload="'",
                injection_type=InjectionType.ERROR_BASED,
                description="Test",
                expected_patterns=["error"],
                database_types=["mysql"],
            )
        ]

        tester = SQLInjectionTester(payloads=custom_payloads)
        assert len(tester.payloads) == 1
        assert tester.payloads[0].payload == "'"

    @pytest.mark.asyncio
    async def test_test_parameter(self):
        """Test parameter testing."""
        tester = SQLInjectionTester()

        # Mock HTTP client
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "normal response"
        mock_response.headers = {}
        mock_client.get.return_value = mock_response

        results = await tester.test_parameter(
            http_client=mock_client,
            target_url="http://example.com/search",
            parameter="q",
            method="GET",
        )

        assert results["parameter"] == "q"
        assert "vulnerable" in results
        assert "all_tests" in results
        assert len(results["all_tests"]) > 0

    @pytest.mark.asyncio
    async def test_detect_sql_error(self):
        """Test detection of SQL error in response."""
        tester = SQLInjectionTester()

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "mysql_fetch_array(): SQL syntax error"
        mock_response.headers = {}
        mock_client.get.return_value = mock_response

        results = await tester.test_parameter(
            http_client=mock_client,
            target_url="http://example.com/search",
            parameter="id",
            method="GET",
        )

        # Should detect vulnerability due to SQL error message
        assert results["vulnerable"] is True
        assert results["vulnerabilities_count"] > 0

    def test_add_payload(self):
        """Test adding custom payload."""
        tester = SQLInjectionTester()
        initial_count = len(tester.payloads)

        new_payload = SQLInjectionPayload(
            payload="; DROP TABLE users; --",
            injection_type=InjectionType.STACKED_QUERIES,
            description="Drop table",
            expected_patterns=[],
            database_types=["mysql"],
        )

        tester.add_payload(new_payload)
        assert len(tester.payloads) == initial_count + 1

    def test_get_payloads_by_type(self):
        """Test filtering payloads by type."""
        tester = SQLInjectionTester()

        error_payloads = tester.get_payloads_by_type(InjectionType.ERROR_BASED)
        assert len(error_payloads) > 0

        for payload in error_payloads:
            assert payload.injection_type == InjectionType.ERROR_BASED


class TestXSSTester:
    """Test suite for XSSTester."""

    def test_initialization(self):
        """Test XSS tester initialization."""
        tester = XSSTester()
        assert tester is not None
        assert len(tester.payloads) > 0

    @pytest.mark.asyncio
    async def test_test_parameter(self):
        """Test parameter testing for XSS."""
        tester = XSSTester()

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "<p>search results</p>"
        mock_response.headers = {}
        mock_client.get.return_value = mock_response

        results = await tester.test_parameter(
            http_client=mock_client,
            target_url="http://example.com/search",
            parameter="q",
            method="GET",
        )

        assert results["parameter"] == "q"
        assert "vulnerable" in results
        assert "all_tests" in results

    @pytest.mark.asyncio
    async def test_detect_xss_vulnerability(self):
        """Test detection of XSS vulnerability."""
        tester = XSSTester()

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        # Reflect payload without encoding
        mock_response.text = '<script>alert("XSS")</script>'
        mock_response.headers = {}
        mock_client.get.return_value = mock_response

        results = await tester.test_parameter(
            http_client=mock_client,
            target_url="http://example.com/search",
            parameter="q",
            method="GET",
        )

        # Should detect vulnerability due to unencoded payload
        assert results["vulnerable"] is True

    @pytest.mark.asyncio
    async def test_url_reflection_test(self):
        """Test URL reflection detection."""
        tester = XSSTester()

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "XSS_TEST_12345"
        mock_response.headers = {}
        mock_client.get.return_value = mock_response

        result = await tester.test_url_reflection(
            http_client=mock_client, target_url="http://example.com/page"
        )

        assert result["url_reflection"] is True
        assert result["severity"] == "medium"

    def test_add_payload(self):
        """Test adding custom XSS payload."""
        tester = XSSTester()
        initial_count = len(tester.payloads)

        new_payload = XSSPayload(
            payload="<svg onload=alert('xss')>",
            xss_type=XSSType.REFLECTED,
            description="SVG payload",
            expected_tags=["<svg", "onload"],
            expected_events=["onload"],
        )

        tester.add_payload(new_payload)
        assert len(tester.payloads) == initial_count + 1


class TestAuthTester:
    """Test suite for AuthTester."""

    def test_initialization(self):
        """Test auth tester initialization."""
        tester = AuthTester()
        assert tester is not None
        assert len(tester.COMMON_CREDENTIALS) > 0

    @pytest.mark.asyncio
    async def test_test_authentication(self):
        """Test authentication testing."""
        tester = AuthTester()

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Invalid credentials"
        mock_response.headers = {}
        mock_client.post.return_value = mock_response

        test_cases = [
            AuthTestCase(
                name="Test invalid login",
                test_type=AuthTestType.CREDENTIAL_STUFFING,
                username="admin",
                password="wrong",
                expected_success=False,
                description="Test with wrong password",
            )
        ]

        results = await tester.test_authentication(
            http_client=mock_client, login_url="http://example.com/login", test_cases=test_cases
        )

        assert results["total_tests"] == 1
        assert "results" in results

    @pytest.mark.asyncio
    async def test_brute_force_protection(self):
        """Test brute force protection detection."""
        tester = AuthTester()

        mock_client = AsyncMock()

        # Simulate responses without rate limiting
        responses = []
        for i in range(10):
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Invalid"
            responses.append(mock_response)

        mock_client.post.side_effect = responses

        results = await tester.test_brute_force_protection(
            http_client=mock_client,
            login_url="http://example.com/login",
            valid_username="admin",
            attempts=10,
        )

        assert results["test_type"] == "brute_force_protection"
        assert results["attempts"] == 10
        assert "has_rate_limiting" in results
        assert "avg_response_time" in results

    @pytest.mark.asyncio
    async def test_password_policy(self):
        """Test password policy validation."""
        tester = AuthTester()

        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200  # Weak password accepted
        mock_response.text = "Registration successful"
        mock_response.headers = {}
        mock_client.post.return_value = mock_response

        results = await tester.test_password_policy(
            http_client=mock_client, registration_url="http://example.com/register"
        )

        assert results["test_type"] == "password_policy"
        assert results["weak_passwords_accepted"] > 0
        assert results["vulnerable"] is True


class TestRateLimitTester:
    """Test suite for RateLimitTester."""

    def test_initialization(self):
        """Test rate limit tester initialization."""
        tester = RateLimitTester()
        assert tester is not None

    @pytest.mark.asyncio
    async def test_test_rate_limiting(self):
        """Test rate limiting detection."""
        tester = RateLimitTester()

        mock_client = AsyncMock()

        # Simulate responses - no rate limiting
        responses = []
        for i in range(20):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {}
            responses.append(mock_response)

        mock_client.get.side_effect = responses

        results = await tester.test_rate_limiting(
            http_client=mock_client,
            target_url="http://api.example.com/data",
            requests_count=20,
            time_window=5,
        )

        assert results["target_url"] == "http://api.example.com/data"
        assert results["requests_sent"] == 20
        assert "properly_configured" in results
        assert "analysis" in results

    @pytest.mark.asyncio
    async def test_detect_rate_limiting(self):
        """Test detection of rate limiting."""
        tester = RateLimitTester()

        mock_client = AsyncMock()

        # Simulate rate limited responses
        responses = []
        for i in range(10):
            mock_response = Mock()
            if i < 5:
                mock_response.status_code = 200
            else:
                mock_response.status_code = 429  # Too Many Requests
                mock_response.headers = {"Retry-After": "60"}
            responses.append(mock_response)

        mock_client.get.side_effect = responses

        results = await tester.test_rate_limiting(
            http_client=mock_client,
            target_url="http://api.example.com/data",
            requests_count=10,
            time_window=2,
        )

        assert results["blocked_requests"] > 0
        assert results["properly_configured"] is True

    @pytest.mark.asyncio
    async def test_burst_capacity_test(self):
        """Test burst capacity detection."""
        tester = RateLimitTester()

        mock_client = AsyncMock()

        responses = []
        for i in range(10):
            mock_response = Mock()
            mock_response.status_code = 200
            responses.append(mock_response)

        mock_client.get.side_effect = responses

        results = await tester.test_burst_capacity(
            http_client=mock_client, target_url="http://api.example.com/data", burst_size=10
        )

        assert results["test_type"] == "burst_capacity"
        assert results["burst_size"] == 10
        assert "successful_requests" in results


class TestSecurityClient:
    """Test suite for SecurityClient."""

    def test_initialization(self):
        """Test security client initialization."""
        mock_http_client = Mock()
        client = SecurityClient(mock_http_client)

        assert client.http_client == mock_http_client
        assert client._sql_tester is not None
        assert client._xss_tester is not None
        assert client._auth_tester is not None
        assert client._rate_limit_tester is not None

    @pytest.mark.asyncio
    async def test_test_sql_injection(self):
        """Test SQL injection testing through client."""
        mock_http_client = AsyncMock()
        client = SecurityClient(mock_http_client)

        with patch.object(
            client._sql_tester, "test_parameter", new_callable=AsyncMock
        ) as mock_test:
            mock_test.return_value = {
                "parameter": "id",
                "vulnerable": False,
                "vulnerabilities_count": 0,
                "all_tests": [],
            }

            results = await client.test_sql_injection(
                target_url="http://example.com/search", parameter="id"
            )

            assert results["parameter"] == "id"
            mock_test.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_xss(self):
        """Test XSS testing through client."""
        mock_http_client = AsyncMock()
        client = SecurityClient(mock_http_client)

        with patch.object(
            client._xss_tester, "test_parameter", new_callable=AsyncMock
        ) as mock_test:
            mock_test.return_value = {"parameter": "search", "vulnerable": False, "all_tests": []}

            results = await client.test_xss(
                target_url="http://example.com/search", parameter="search"
            )

            assert results["parameter"] == "search"
            mock_test.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_security_headers(self):
        """Test security headers checking."""
        mock_http_client = AsyncMock()
        mock_response = Mock()
        mock_response.headers = {
            "Strict-Transport-Security": "max-age=31536000",
            "X-Frame-Options": "DENY",
        }
        mock_http_client.get.return_value = mock_response

        client = SecurityClient(mock_http_client)

        results = await client.test_security_headers("http://example.com")

        assert results["target_url"] == "http://example.com"
        assert "score" in results
        assert "grade" in results
        assert "header_results" in results

    @pytest.mark.asyncio
    async def test_run_full_security_scan(self):
        """Test full security scan."""
        mock_http_client = AsyncMock()
        client = SecurityClient(mock_http_client)

        with patch.object(client, "test_security_headers", new_callable=AsyncMock) as mock_headers:
            mock_headers.return_value = {"score": 80, "grade": "B"}

            results = await client.run_full_security_scan(
                target_url="http://example.com", parameters=["id", "search"]
            )

            assert "target_url" in results
            assert "overall_score" in results
            assert "tests" in results

    @pytest.mark.asyncio
    async def test_close(self):
        """Test client cleanup."""
        mock_http_client = AsyncMock()
        client = SecurityClient(mock_http_client)

        await client.close()

        assert client._closed is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
