"""Tests for Vulnerability Scanning Module

Tests the unified vuln parser, report generator, and scanner wrappers.
Uses mock data to avoid requiring Docker.
"""

import json
import pytest
from datetime import datetime
from typing import Dict, List, Any
from pathlib import Path

from src.adapters.vuln import (
    VulnSeverity,
    VulnCategory,
    VulnerabilityFinding,
    VulnScanResult,
    UnifiedVulnParser,
    VulnReportGenerator,
)


# ─── Fixtures ────────────────────────────────────────────────


@pytest.fixture
def sample_nuclei_output() -> List[Dict[str, Any]]:
    """Sample Nuclei JSONL output."""
    return [
        {
            "template-id": "missing-security-headers",
            "type": "http",
            "info": {
                "name": "Missing Security Headers",
                "description": "The target is missing important security headers",
                "severity": "medium",
                "tags": ["security", "headers", "misconfig"],
                "remediation": "Add security headers",
                "reference": ["https://owasp.org/www-project-secure-headers/"],
            },
            "matched-at": "https://example.com/",
            "host": "example.com",
            "port": 443,
        },
        {
            "template-id": "CVE-2023-1234",
            "type": "http",
            "info": {
                "name": "Example CVE Detection",
                "description": "Detected vulnerable library",
                "severity": "critical",
                "tags": ["cve-2023-1234", "cwe-79", "injection"],
                "classification": {"cvss-score": 9.8},
                "reference": [
                    "https://nvd.nist.gov/vuln/detail/CVE-2023-1234",
                ],
            },
            "matched-at": "https://example.com/js/lib.js",
            "extracted-results": ["jquery-1.7.2.min.js"],
            "request": "GET /js/lib.js HTTP/1.1",
            "response": "HTTP/1.1 200 OK\nContent-Type: application/javascript\n\n...jquery...",
        },
        {
            "template-id": "xss-detection",
            "type": "http",
            "info": {
                "name": "Reflected XSS",
                "description": "Parameter 'q' reflects unencoded input",
                "severity": "high",
                "tags": ["xss", "injection"],
                "remediation": "Encode output properly",
            },
            "matched-at": "https://example.com/search?q=<script>alert(1)</script>",
        },
    ]


@pytest.fixture
def sample_nuclei_json_string() -> str:
    """Sample Nuclei JSON output as string."""
    return json.dumps(
        [
            {
                "template-id": "test-template",
                "info": {
                    "name": "Test Finding",
                    "description": "A test vulnerability",
                    "severity": "low",
                    "tags": ["test"],
                },
                "matched-at": "https://test.com/",
            }
        ]
    )


@pytest.fixture
def sample_wstg_output() -> Dict[str, Any]:
    """Sample WSTG scanner output."""
    return {
        "tests": {
            "WSTG-INPV-01": {
                "name": "SQL Injection Testing",
                "status": "vulnerable",
                "risk": "high",
                "description": "SQL injection found in search parameter",
                "url": "https://example.com/search",
                "method": "GET",
                "evidence": "Error: You have an error in your SQL syntax",
                "remediation": "Use parameterized queries",
                "wstg_id": "WSTG-INPV-01",
            },
            "WSTG-CONF-01": {
                "name": "Security Headers Check",
                "status": "vulnerable",
                "risk": "medium",
                "description": "Missing X-Frame-Options header",
                "url": "https://example.com/",
                "method": "GET",
                "remediation": "Add X-Frame-Options: DENY",
                "wstg_id": "WSTG-CONF-01",
            },
            "WSTG-ATHN-02": {
                "name": "Authentication Bypass",
                "status": "pass",
                "risk": "none",
                "description": "Authentication is properly enforced",
                "url": "https://example.com/admin",
                "wstg_id": "WSTG-ATHN-02",
            },
        }
    }


# ─── Severity Tests ──────────────────────────────────────────


class TestVulnSeverity:
    def test_from_nuclei(self):
        assert VulnSeverity.from_nuclei("critical") == VulnSeverity.CRITICAL
        assert VulnSeverity.from_nuclei("high") == VulnSeverity.HIGH
        assert VulnSeverity.from_nuclei("medium") == VulnSeverity.MEDIUM
        assert VulnSeverity.from_nuclei("low") == VulnSeverity.LOW
        assert VulnSeverity.from_nuclei("info") == VulnSeverity.INFO
        assert VulnSeverity.from_nuclei("unknown") == VulnSeverity.UNKNOWN
        assert VulnSeverity.from_nuclei("CRITICAL") == VulnSeverity.CRITICAL

    def test_from_wstg(self):
        assert VulnSeverity.from_wstg("high") == VulnSeverity.HIGH
        assert VulnSeverity.from_wstg("informational") == VulnSeverity.INFO
        assert VulnSeverity.from_wstg("none") == VulnSeverity.UNKNOWN

    def test_from_cvss(self):
        assert VulnSeverity.from_cvss(9.5) == VulnSeverity.CRITICAL
        assert VulnSeverity.from_cvss(7.5) == VulnSeverity.HIGH
        assert VulnSeverity.from_cvss(5.0) == VulnSeverity.MEDIUM
        assert VulnSeverity.from_cvss(2.0) == VulnSeverity.LOW
        assert VulnSeverity.from_cvss(0.0) == VulnSeverity.UNKNOWN


# ─── Category Tests ──────────────────────────────────────────


class TestVulnCategory:
    def test_from_nuclei_tags(self):
        assert VulnCategory.from_nuclei_template("test", ["sqli"]) == VulnCategory.INJECTION
        assert VulnCategory.from_nuclei_template("test", ["xss"]) == VulnCategory.INJECTION
        assert VulnCategory.from_nuclei_template("test", ["auth"]) == VulnCategory.AUTH_FAILURES
        assert (
            VulnCategory.from_nuclei_template("test", ["idor"])
            == VulnCategory.BROKEN_ACCESS_CONTROL
        )
        assert (
            VulnCategory.from_nuclei_template("test", ["cors"])
            == VulnCategory.SECURITY_MISCONFIGURATION
        )
        assert VulnCategory.from_nuclei_template("test", ["ssl", "tls"]) == VulnCategory.TLS_ISSUES
        assert VulnCategory.from_nuclei_template("test", ["dns"]) == VulnCategory.DNS_ISSUES
        assert (
            VulnCategory.from_nuclei_template("test", ["cve"]) == VulnCategory.VULNERABLE_COMPONENTS
        )
        assert (
            VulnCategory.from_nuclei_template("test", ["exposure"]) == VulnCategory.INFO_DISCLOSURE
        )
        assert VulnCategory.from_nuclei_template("test", ["ssrf"]) == VulnCategory.SSRF
        assert VulnCategory.from_nuclei_template("test", ["unknown_tag"]) == VulnCategory.UNKNOWN


# ─── VulnerabilityFinding Tests ──────────────────────────────


class TestVulnerabilityFinding:
    def test_create_minimal(self):
        finding = VulnerabilityFinding(
            id="TEST-001",
            title="Test Finding",
            description="A test",
            severity=VulnSeverity.HIGH,
            category=VulnCategory.INJECTION,
            scanner="test",
            target="https://example.com",
        )
        assert finding.id == "TEST-001"
        assert finding.severity == VulnSeverity.HIGH
        assert finding.category == VulnCategory.INJECTION

    def test_create_full(self):
        finding = VulnerabilityFinding(
            id="TEST-002",
            title="Full Test",
            description="Full description",
            severity=VulnSeverity.CRITICAL,
            category=VulnCategory.SSRF,
            scanner="nuclei",
            template_name="ssrf-test",
            template_id="SSRF-001",
            target="https://example.com",
            endpoint="/api/fetch",
            method="POST",
            port=443,
            evidence="Response contained internal IP",
            remediation="Validate redirect URLs",
            references=["https://owasp.org/SSRF"],
            cve_id="CVE-2024-0001",
            cvss_score=9.5,
            tags=["ssrf", "server-side"],
        )
        assert finding.cve_id == "CVE-2024-0001"
        assert finding.cvss_score == 9.5
        assert finding.port == 443

    def test_to_dict(self):
        finding = VulnerabilityFinding(
            id="TEST-003",
            title="Dict Test",
            description="Testing to_dict",
            severity=VulnSeverity.LOW,
            category=VulnCategory.INFO_DISCLOSURE,
            scanner="test",
            target="https://example.com",
        )
        d = finding.to_dict()
        assert d["id"] == "TEST-003"
        assert d["severity"] == "low"
        assert d["category"] == "information-disclosure"


# ─── VulnScanResult Tests ────────────────────────────────────


class TestVulnScanResult:
    def test_empty_result(self):
        result = VulnScanResult(
            scan_id="test-001",
            scanner="nuclei",
            scan_type="web",
            target="https://example.com",
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-01-01T00:01:00Z",
            duration_seconds=60.0,
        )
        assert result.total_findings == 0
        assert result.critical_count == 0

    def test_finding_counts(self):
        findings = [
            VulnerabilityFinding(
                id="1",
                title="C1",
                description="",
                severity=VulnSeverity.CRITICAL,
                category=VulnCategory.INJECTION,
                scanner="test",
                target="https://example.com",
            ),
            VulnerabilityFinding(
                id="2",
                title="H1",
                description="",
                severity=VulnSeverity.HIGH,
                category=VulnCategory.AUTH_FAILURES,
                scanner="test",
                target="https://example.com",
            ),
            VulnerabilityFinding(
                id="3",
                title="M1",
                description="",
                severity=VulnSeverity.MEDIUM,
                category=VulnCategory.SECURITY_MISCONFIGURATION,
                scanner="test",
                target="https://example.com",
            ),
            VulnerabilityFinding(
                id="4",
                title="M2",
                description="",
                severity=VulnSeverity.MEDIUM,
                category=VulnCategory.CORS_MISCONFIG,
                scanner="test",
                target="https://example.com",
            ),
            VulnerabilityFinding(
                id="5",
                title="L1",
                description="",
                severity=VulnSeverity.LOW,
                category=VulnCategory.INFO_DISCLOSURE,
                scanner="test",
                target="https://example.com",
            ),
            VulnerabilityFinding(
                id="6",
                title="I1",
                description="",
                severity=VulnSeverity.INFO,
                category=VulnCategory.DIRECTORY_LISTING,
                scanner="test",
                target="https://example.com",
            ),
        ]
        result = VulnScanResult(
            scan_id="test-002",
            scanner="nuclei",
            scan_type="web",
            target="https://example.com",
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-01-01T00:01:00Z",
            duration_seconds=60.0,
            findings=findings,
        )
        assert result.total_findings == 6
        assert result.critical_count == 1
        assert result.high_count == 1
        assert result.medium_count == 2
        assert result.low_count == 1
        assert result.info_count == 1

    def test_add_finding(self):
        result = VulnScanResult(
            scan_id="test-003",
            scanner="nuclei",
            scan_type="web",
            target="https://example.com",
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-01-01T00:01:00Z",
            duration_seconds=60.0,
        )
        assert result.total_findings == 0

        f = VulnerabilityFinding(
            id="new",
            title="New",
            description="",
            severity=VulnSeverity.CRITICAL,
            category=VulnCategory.INJECTION,
            scanner="test",
            target="https://example.com",
        )
        result.add_finding(f)
        assert result.total_findings == 1
        assert result.critical_count == 1

    def test_to_dict(self):
        result = VulnScanResult(
            scan_id="test-004",
            scanner="nuclei",
            scan_type="web",
            target="https://example.com",
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-01-01T00:01:00Z",
            duration_seconds=60.0,
        )
        d = result.to_dict()
        assert d["scan_id"] == "test-004"
        assert d["total_findings"] == 0
        assert "findings" in d

    def test_get_findings_by_severity(self):
        findings = [
            VulnerabilityFinding(
                id="c1",
                title="C1",
                description="",
                severity=VulnSeverity.CRITICAL,
                category=VulnCategory.INJECTION,
                scanner="test",
                target="t",
            ),
            VulnerabilityFinding(
                id="h1",
                title="H1",
                description="",
                severity=VulnSeverity.HIGH,
                category=VulnCategory.AUTH_FAILURES,
                scanner="test",
                target="t",
            ),
            VulnerabilityFinding(
                id="c2",
                title="C2",
                description="",
                severity=VulnSeverity.CRITICAL,
                category=VulnCategory.INJECTION,
                scanner="test",
                target="t",
            ),
        ]
        result = VulnScanResult(
            scan_id="test-005",
            scanner="nuclei",
            scan_type="web",
            target="t",
            start_time="S",
            end_time="E",
            duration_seconds=0,
            findings=findings,
        )
        crit = result.get_findings_by_severity(VulnSeverity.CRITICAL)
        assert len(crit) == 2
        high = result.get_findings_by_severity(VulnSeverity.HIGH)
        assert len(high) == 1

    def test_get_findings_by_category(self):
        findings = [
            VulnerabilityFinding(
                id="i1",
                title="I1",
                description="",
                severity=VulnSeverity.HIGH,
                category=VulnCategory.INJECTION,
                scanner="test",
                target="t",
            ),
            VulnerabilityFinding(
                id="a1",
                title="A1",
                description="",
                severity=VulnSeverity.HIGH,
                category=VulnCategory.AUTH_FAILURES,
                scanner="test",
                target="t",
            ),
        ]
        result = VulnScanResult(
            scan_id="test-006",
            scanner="nuclei",
            scan_type="web",
            target="t",
            start_time="S",
            end_time="E",
            duration_seconds=0,
            findings=findings,
        )
        inject = result.get_findings_by_category(VulnCategory.INJECTION)
        assert len(inject) == 1


# ─── UnifiedVulnParser Tests ─────────────────────────────────


class TestUnifiedVulnParser:
    def test_parse_nuclei_json_list(self, sample_nuclei_output):
        result = UnifiedVulnParser.parse_nuclei_json(
            json_data=sample_nuclei_output,
            scan_id="test-nuclei-001",
            target="https://example.com",
            scan_type="web",
        )
        assert result.scanner == "nuclei"
        assert result.total_findings == 3
        assert result.critical_count == 1  # CVE
        assert result.high_count == 1  # XSS
        assert result.medium_count == 1  # Headers

    def test_parse_nuclei_json_string(self, sample_nuclei_json_string):
        result = UnifiedVulnParser.parse_nuclei_json(
            json_data=sample_nuclei_json_string,
            scan_id="test-nuclei-002",
            target="https://test.com",
            scan_type="web",
        )
        assert result.total_findings == 1
        assert result.findings[0].title == "Test Finding"

    def test_parse_nuclei_json_empty(self):
        result = UnifiedVulnParser.parse_nuclei_json(
            json_data="",
            scan_id="test-nuclei-003",
            target="https://example.com",
            scan_type="web",
        )
        assert "Failed to parse" in (result.error or "")

    def test_parse_nuclei_json_single_dict(self):
        data = {
            "template-id": "single-test",
            "info": {
                "name": "Single",
                "description": "Single test",
                "severity": "high",
                "tags": ["test"],
            },
            "matched-at": "https://example.com/",
        }
        result = UnifiedVulnParser.parse_nuclei_json(
            json_data=data,
            scan_id="test-nuclei-004",
            target="https://example.com",
        )
        assert result.total_findings == 1

    def test_parse_wstg_json(self, sample_wstg_output):
        result = UnifiedVulnParser.parse_wstg_json(
            json_data=sample_wstg_output,
            scan_id="test-wstg-001",
            target="https://example.com",
        )
        # Should have 2 findings (3rd test passed)
        assert result.total_findings == 2
        assert result.high_count == 1  # SQL injection
        assert result.medium_count == 1  # Headers

    def test_parse_wstg_json_string(self, sample_wstg_output):
        result = UnifiedVulnParser.parse_wstg_json(
            json_data=json.dumps(sample_wstg_output),
            scan_id="test-wstg-002",
            target="https://example.com",
        )
        assert result.total_findings == 2

    def test_merge_results(self, sample_nuclei_output):
        r1 = UnifiedVulnParser.parse_nuclei_json(
            sample_nuclei_output, "n1", "https://example.com", "web"
        )
        r2 = UnifiedVulnParser.parse_nuclei_json(
            sample_nuclei_output, "n2", "https://example.com", "web"
        )
        merged = UnifiedVulnParser.merge_results([r1, r2])
        assert merged.scanner == "combined"
        # Should have deduplicated
        assert merged.total_findings == 3  # Not 6

    def test_to_owasp_format(self, sample_nuclei_output):
        result = UnifiedVulnParser.parse_nuclei_json(
            sample_nuclei_output, "owasp-test", "https://example.com"
        )
        owasp = UnifiedVulnParser.to_owasp_format(result)
        assert "risk_score" in owasp
        assert "risk_level" in owasp
        assert "severity_breakdown" in owasp
        assert owasp["severity_breakdown"]["critical"] >= 1
        assert len(owasp["top_critical"]) > 0


# ─── VulnReportGenerator Tests ───────────────────────────────


class TestVulnReportGenerator:
    @pytest.fixture
    def sample_result(self):
        return VulnScanResult(
            scan_id="report-test",
            scanner="nuclei",
            scan_type="web",
            target="https://example.com",
            start_time="2024-01-01T00:00:00Z",
            end_time="2024-01-01T00:01:00Z",
            duration_seconds=60.0,
            findings=[
                VulnerabilityFinding(
                    id="RPT-001",
                    title="Critical Vuln",
                    description="A critical vulnerability",
                    severity=VulnSeverity.CRITICAL,
                    category=VulnCategory.INJECTION,
                    scanner="nuclei",
                    target="https://example.com",
                    endpoint="/login",
                    evidence="SQL error shown",
                    remediation="Use prepared statements",
                    cve_id="CVE-2024-0002",
                ),
                VulnerabilityFinding(
                    id="RPT-002",
                    title="Info Finding",
                    description="Informational",
                    severity=VulnSeverity.INFO,
                    category=VulnCategory.INFO_DISCLOSURE,
                    scanner="nuclei",
                    target="https://example.com",
                ),
            ],
        )

    def test_generate_json(self, sample_result, tmp_path):
        reporter = VulnReportGenerator(output_dir=str(tmp_path))
        path = reporter.generate_json(sample_result, filename="test.json")
        assert Path(path).exists()
        with open(path) as f:
            data = json.load(f)
        assert data["summary"]["total"] == 2
        assert data["summary"]["critical"] == 1

    def test_generate_html(self, sample_result, tmp_path):
        reporter = VulnReportGenerator(output_dir=str(tmp_path))
        path = reporter.generate_html(sample_result, filename="test.html")
        assert Path(path).exists()
        content = Path(path).read_text()
        assert "Critical Vuln" in content
        assert "Vulnerability Scan Report" in content

    def test_generate_markdown(self, sample_result, tmp_path):
        reporter = VulnReportGenerator(output_dir=str(tmp_path))
        path = reporter.generate_markdown(sample_result, filename="test.md")
        assert Path(path).exists()
        content = Path(path).read_text()
        assert "# 🔍 Vulnerability Scan Report" in content

    def test_generate_all(self, sample_result, tmp_path):
        reporter = VulnReportGenerator(output_dir=str(tmp_path))
        paths = reporter.generate_all(sample_result, base_name="full_test")
        assert "json" in paths
        assert "html" in paths
        assert "md" in paths
        for p in paths.values():
            assert Path(p).exists()

    def test_empty_result_report(self, tmp_path):
        result = VulnScanResult(
            scan_id="empty",
            scanner="nuclei",
            scan_type="web",
            target="https://example.com",
            start_time="S",
            end_time="E",
            duration_seconds=0,
        )
        reporter = VulnReportGenerator(output_dir=str(tmp_path))
        path = reporter.generate_html(result, filename="empty.html")
        content = Path(path).read_text()
        assert "0" in content  # Should show zero counts


# ─── ZAP Scanner Tests ─────────────────────────────────────────


class TestZAPScanner:
    """Tests for OWASP ZAP Scanner adapter."""

    @pytest.mark.asyncio
    async def test_zap_scanner_initialization(self):
        """Test that ZAPScanner can be initialized with default config."""
        from src.adapters.vuln.zap_scanner import ZAPScanner

        scanner = ZAPScanner()
        assert scanner is not None
        assert scanner.config.docker_image == "ghcr.io/zaproxy/zaproxy:stable"
        assert scanner.config.network == "qa-network"
        await scanner.close()

    @pytest.mark.asyncio
    async def test_zap_scanner_custom_config(self):
        """Test that ZAPScanner accepts custom configuration."""
        from src.adapters.vuln.zap_scanner import ZAPScanner, ZAPScannerConfig

        config = ZAPScannerConfig(
            proxy_host="127.0.0.1",
            proxy_port=8080,
            api_key="test-key",
            spider_duration=60,
            active_scan_duration=120,
        )
        scanner = ZAPScanner(config=config)
        assert scanner.config.proxy_host == "127.0.0.1"
        assert scanner.config.api_key == "test-key"
        await scanner.close()

    @pytest.mark.asyncio
    async def test_zap_health_check(self):
        """Test that health_check returns expected structure."""
        from src.adapters.vuln.zap_scanner import ZAPScanner

        scanner = ZAPScanner()
        health = await scanner.health_check()
        assert "status" in health
        assert "scanner" in health
        assert health["scanner"] == "zap"
        await scanner.close()

    @pytest.mark.asyncio
    async def test_zap_scan_web_returns_result(self):
        """Test that scan_web returns a VulnScanResult."""
        from src.adapters.vuln.zap_scanner import ZAPScanner

        scanner = ZAPScanner()
        # This will fail because ZAP daemon won't be available, but should return proper error structure
        result = await scanner.scan_web("https://example.com", scan_id="test-zap-001")
        assert result is not None
        assert isinstance(result, VulnScanResult)
        assert result.scanner == "zap"
        assert result.scan_type == "web"
        assert result.target == "https://example.com"
        await scanner.close()

    @pytest.mark.asyncio
    async def test_zap_async_context_manager(self):
        """Test that ZAPScanner works as async context manager."""
        from src.adapters.vuln.zap_scanner import ZAPScanner

        async with ZAPScanner() as scanner:
            assert scanner is not None
            health = await scanner.health_check()
            assert "status" in health
        # Should auto-close

    @pytest.mark.asyncio
    async def test_zap_scan_with_policy(self):
        """Test that scan_with_policy accepts policy parameter."""
        from src.adapters.vuln.zap_scanner import ZAPScanner

        scanner = ZAPScanner()
        result = await scanner.scan_with_policy(
            "https://example.com", policy_name="default-policy", scan_id="test-zap-policy-001"
        )
        assert result is not None
        assert isinstance(result, VulnScanResult)
        await scanner.close()
