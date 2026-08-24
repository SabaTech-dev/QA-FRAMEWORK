"""Authentication and authorization testing module"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class AuthTestType(Enum):
    """Types of authentication tests."""

    BRUTE_FORCE = "brute_force"
    CREDENTIAL_STUFFING = "credential_stuffing"
    SESSION_MANAGEMENT = "session_management"
    PASSWORD_POLICY = "password_policy"
    MFA_BYPASS = "mfa_bypass"
    ACCOUNT_LOCKOUT = "account_lockout"


@dataclass
class AuthTestCase:
    """
    Authentication test case.

    Attributes:
        name: Test case name
        test_type: Type of authentication test
        username: Username to test
        password: Password to test
        expected_success: Whether authentication should succeed
        description: Description of the test case
    """

    name: str
    test_type: AuthTestType
    username: str
    password: str
    expected_success: bool
    description: str


class AuthTester:
    """
    Tester for authentication and authorization mechanisms.

    This class provides methods to test authentication systems for
    common vulnerabilities like weak passwords, brute force protection,
    and session management issues.

    Example:
        tester = AuthTester()

        test_cases = [
            AuthTestCase(
                name="Valid credentials",
                test_type=AuthTestType.CREDENTIAL_STUFFING,
                username="admin",
                password="admin",
                expected_success=False,
                description="Test default/weak credentials"
            )
        ]

        results = await tester.test_authentication(
            http_client=client,
            login_url="http://example.com/login",
            test_cases=test_cases
        )
    """

    # Common weak/default credentials
    COMMON_CREDENTIALS: list[dict[str, str]] = [
        {"username": "admin", "password": "admin"},
        {"username": "admin", "password": "password"},
        {"username": "admin", "password": "123456"},
        {"username": "admin", "password": "admin123"},
        {"username": "root", "password": "root"},
        {"username": "root", "password": "password"},
        {"username": "user", "password": "user"},
        {"username": "user", "password": "password"},
        {"username": "test", "password": "test"},
        {"username": "guest", "password": "guest"},
        {"username": "administrator", "password": "administrator"},
        {"username": "admin", "password": ""},
        {"username": "", "password": "admin"},
    ]

    def __init__(self) -> None:
        """Initialize authentication tester."""
        self._results: list[dict[str, Any]] = []

    async def test_authentication(
        self,
        http_client: Any,
        login_url: str,
        test_cases: list[AuthTestCase],
        username_field: str = "username",
        password_field: str = "password",
    ) -> dict[str, Any]:
        """
        Test authentication mechanism with multiple test cases.

        Args:
            http_client: HTTP client with async request methods
            login_url: URL of the login endpoint
            test_cases: List of AuthTestCase to test
            username_field: Form field name for username
            password_field: Form field name for password

        Returns:
            Dictionary with test results
        """
        self._results = []

        for test_case in test_cases:
            result = await self._run_test_case(
                http_client, login_url, test_case, username_field, password_field
            )
            self._results.append(result)

        # Analyze results
        successful_logins = [r for r in self._results if r.get("login_successful")]
        unexpected_success = [r for r in self._results if r.get("unexpected_success")]

        return {
            "login_url": login_url,
            "total_tests": len(test_cases),
            "successful_logins": len(successful_logins),
            "vulnerabilities_found": len(unexpected_success),
            "results": self._results,
            "security_issues": self._identify_security_issues(self._results),
            "recommendations": self._get_recommendations(self._results),
        }

    async def test_common_credentials(
        self,
        http_client: Any,
        login_url: str,
        username_field: str = "username",
        password_field: str = "password",
    ) -> dict[str, Any]:
        """
        Test for common/default credentials.

        Args:
            http_client: HTTP client
            login_url: URL of the login endpoint
            username_field: Form field name for username
            password_field: Form field name for password

        Returns:
            Dictionary with test results
        """
        test_cases = [
            AuthTestCase(
                name=f"Common creds: {creds['username']}/{creds['password']}",
                test_type=AuthTestType.CREDENTIAL_STUFFING,
                username=creds["username"],
                password=creds["password"],
                expected_success=False,
                description=f"Test common credentials: {creds['username']}/{creds['password']}",
            )
            for creds in self.COMMON_CREDENTIALS
        ]

        return await self.test_authentication(
            http_client, login_url, test_cases, username_field, password_field
        )

    async def test_brute_force_protection(
        self,
        http_client: Any,
        login_url: str,
        valid_username: str,
        attempts: int = 10,
        username_field: str = "username",
        password_field: str = "password",
    ) -> dict[str, Any]:
        """
        Test for brute force protection mechanisms.

        Args:
            http_client: HTTP client
            login_url: URL of the login endpoint
            valid_username: A valid username to test
            attempts: Number of failed login attempts
            username_field: Form field name for username
            password_field: Form field name for password

        Returns:
            Dictionary with test results
        """
        results = []
        response_times = []

        for i in range(attempts):
            import time

            start = time.time()

            response = await self._attempt_login(
                http_client,
                login_url,
                valid_username,
                f"wrong_password_{i}",
                username_field,
                password_field,
            )

            elapsed = time.time() - start
            response_times.append(elapsed)

            results.append(
                {
                    "attempt": i + 1,
                    "response_time": elapsed,
                    "status_code": response.get("status_code"),
                }
            )

        # Analyze for rate limiting
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)

        has_rate_limiting = max_time > (avg_time * 2)  # Significant delay indicates rate limiting

        return {
            "test_type": "brute_force_protection",
            "login_url": login_url,
            "attempts": attempts,
            "has_rate_limiting": has_rate_limiting,
            "avg_response_time": round(avg_time, 3),
            "max_response_time": round(max_time, 3),
            "vulnerable": not has_rate_limiting,
            "results": results,
            "recommendations": [
                (
                    "Implement account lockout after failed attempts"
                    if not has_rate_limiting
                    else "Rate limiting appears to be implemented"
                ),
                "Consider CAPTCHA after multiple failed attempts",
                "Implement exponential backoff for failed logins",
            ],
        }

    async def test_password_policy(
        self,
        http_client: Any,
        registration_url: str,
        username_field: str = "username",
        password_field: str = "password",
    ) -> dict[str, Any]:
        """
        Test password policy enforcement.

        Args:
            http_client: HTTP client
            registration_url: URL of the registration endpoint
            username_field: Form field name for username
            password_field: Form field name for password

        Returns:
            Dictionary with test results
        """
        weak_passwords = [
            ("123456", "Sequential numbers"),
            ("password", "Common dictionary word"),
            ("qwerty", "Keyboard pattern"),
            ("abc", "Too short"),
            ("user", "Username as password"),
        ]

        results = []

        for password, description in weak_passwords:
            response = await self._attempt_registration(
                http_client,
                registration_url,
                f"testuser_{hash(password) % 10000}",
                password,
                username_field,
                password_field,
            )

            accepted = (
                response.get("status_code") == 200 or "success" in response.get("text", "").lower()
            )

            results.append(
                {
                    "password": password,
                    "description": description,
                    "accepted": accepted,
                    "vulnerable": accepted,  # If weak password is accepted, it's vulnerable
                }
            )

        weak_accepted = [r for r in results if r["accepted"]]

        return {
            "test_type": "password_policy",
            "registration_url": registration_url,
            "weak_passwords_accepted": len(weak_accepted),
            "vulnerable": len(weak_accepted) > 0,
            "results": results,
            "recommendations": [
                (
                    "Enforce minimum password length (8+ characters)"
                    if any(r["description"] == "Too short" and r["accepted"] for r in results)
                    else None
                ),
                "Require mixed case, numbers, and special characters",
                "Check against common password dictionaries",
                "Implement password strength meter",
            ],
        }

    async def _run_test_case(
        self,
        http_client: Any,
        login_url: str,
        test_case: AuthTestCase,
        username_field: str,
        password_field: str,
    ) -> dict[str, Any]:
        """Run a single authentication test case."""
        response = await self._attempt_login(
            http_client,
            login_url,
            test_case.username,
            test_case.password,
            username_field,
            password_field,
        )

        # Determine if login was successful
        # This is a simplified check - real implementation would be more sophisticated
        login_successful = self._is_login_successful(response)

        return {
            "name": test_case.name,
            "test_type": test_case.test_type.value,
            "username": test_case.username,
            "password": "***REDACTED***",
            "expected_success": test_case.expected_success,
            "login_successful": login_successful,
            "unexpected_success": login_successful and not test_case.expected_success,
            "description": test_case.description,
            "status_code": response.get("status_code"),
            "vulnerable": login_successful and not test_case.expected_success,
        }

    async def _attempt_login(
        self,
        http_client: Any,
        login_url: str,
        username: str,
        password: str,
        username_field: str,
        password_field: str,
    ) -> dict[str, Any]:
        """Attempt to login with given credentials."""
        try:
            data = {username_field: username, password_field: password}

            response = await http_client.post(login_url, data=data)

            response_text = ""
            if hasattr(response, "text"):
                response_text = response.text
            elif hasattr(response, "content"):
                response_text = response.content.decode("utf-8", errors="ignore")

            return {
                "status_code": getattr(response, "status_code", 0),
                "text": response_text,
                "headers": dict(getattr(response, "headers", {})),
                "error": None,
            }
        except Exception as e:
            return {"status_code": 0, "text": "", "headers": {}, "error": str(e)}

    async def _attempt_registration(
        self,
        http_client: Any,
        registration_url: str,
        username: str,
        password: str,
        username_field: str,
        password_field: str,
    ) -> dict[str, Any]:
        """Attempt to register with given credentials."""
        try:
            data = {username_field: username, password_field: password}

            response = await http_client.post(registration_url, data=data)

            response_text = ""
            if hasattr(response, "text"):
                response_text = response.text
            elif hasattr(response, "content"):
                response_text = response.content.decode("utf-8", errors="ignore")

            return {
                "status_code": getattr(response, "status_code", 0),
                "text": response_text,
                "headers": dict(getattr(response, "headers", {})),
                "error": None,
            }
        except Exception as e:
            return {"status_code": 0, "text": "", "headers": {}, "error": str(e)}

    def _is_login_successful(self, response: dict[str, Any]) -> bool:
        """
        Determine if login was successful based on response.

        This is a heuristic and may need customization for specific applications.
        """
        status_code = response.get("status_code", 0)
        text = response.get("text", "").lower()

        # Check for common success indicators
        success_indicators = [
            "welcome",
            "dashboard",
            "profile",
            "logout",
            "success",
            "redirect",
            "home",
            "account",
            "authenticated",
        ]

        # Check for common failure indicators
        failure_indicators = [
            "invalid",
            "error",
            "failed",
            "incorrect",
            "wrong",
            "denied",
            "unauthorized",
            "login failed",
            "authentication failed",
        ]

        has_success = any(indicator in text for indicator in success_indicators)
        has_failure = any(indicator in text for indicator in failure_indicators)

        # Heuristic: 200 status without failure indicators likely means success
        if status_code == 200 and not has_failure:
            return True

        # If we see success indicators but no failure indicators
        if has_success and not has_failure:
            return True

        return False

    def _identify_security_issues(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Identify security issues from test results."""
        issues = []

        for result in results:
            if result.get("unexpected_success"):
                issues.append(
                    {
                        "severity": "critical",
                        "type": result.get("test_type"),
                        "description": f"Unexpected successful login with: {result.get('username')}",
                        "recommendation": "Review and strengthen authentication mechanism",
                    }
                )

        return issues

    def _get_recommendations(self, results: list[dict[str, Any]]) -> list[str]:
        """Generate recommendations based on test results."""
        vulnerabilities = [r for r in results if r.get("vulnerable")]

        if not vulnerabilities:
            return ["Authentication mechanism appears secure against tested attack vectors."]

        recommendations = [
            "CRITICAL: Authentication vulnerabilities detected!",
            "",
            "Immediate Actions Required:",
        ]

        # Add specific recommendations based on findings
        cred_stuffing = [
            r
            for r in vulnerabilities
            if r.get("test_type") == AuthTestType.CREDENTIAL_STUFFING.value
        ]
        if cred_stuffing:
            recommendations.extend(
                [
                    "1. Disable default/weak credentials",
                    "2. Enforce strong password policies",
                    "3. Implement account lockout after failed attempts",
                ]
            )

        brute_force = [
            r for r in vulnerabilities if r.get("test_type") == AuthTestType.BRUTE_FORCE.value
        ]
        if brute_force:
            recommendations.extend(
                [
                    "4. Implement rate limiting on login endpoints",
                    "5. Add CAPTCHA after multiple failed attempts",
                    "6. Consider implementing MFA",
                ]
            )

        recommendations.extend(
            [
                "",
                "Additional Recommendations:",
                "7. Implement secure session management",
                "8. Use HTTPS for all authentication traffic",
                "9. Log and monitor authentication attempts",
                "10. Consider implementing OAuth/SAML for enterprise applications",
            ]
        )

        return recommendations
