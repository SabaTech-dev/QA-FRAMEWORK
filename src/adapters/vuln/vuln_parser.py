"""Unified Vulnerability Parser

Parses and normalizes vulnerability scan results from Nuclei and WSTG-Scan
into a common format for reporting and analysis.

Supports multiple input formats:
- Nuclei JSON output
- WSTG JSON/HTML output
- Generic vulnerability finding format
"""

import json
import re
import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


class VulnSeverity(str, Enum):
    """Severity levels standardized across all scanners."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    UNKNOWN = "unknown"

    @classmethod
    def from_nuclei(cls, severity: str) -> "VulnSeverity":
        """Map Nuclei severity to unified severity."""
        mapping = {
            "critical": cls.CRITICAL,
            "high": cls.HIGH,
            "medium": cls.MEDIUM,
            "low": cls.LOW,
            "info": cls.INFO,
            "unknown": cls.UNKNOWN,
        }
        return mapping.get(severity.lower(), cls.UNKNOWN)

    @classmethod
    def from_wstg(cls, risk: str) -> "VulnSeverity":
        """Map WSTG risk level to unified severity."""
        mapping = {
            "critical": cls.CRITICAL,
            "high": cls.HIGH,
            "medium": cls.MEDIUM,
            "low": cls.LOW,
            "informational": cls.INFO,
        }
        return mapping.get(risk.lower(), cls.UNKNOWN)

    @classmethod
    def from_cvss(cls, score: float) -> "VulnSeverity":
        """Map CVSS score to severity level."""
        if score >= 9.0:
            return cls.CRITICAL
        elif score >= 7.0:
            return cls.HIGH
        elif score >= 4.0:
            return cls.MEDIUM
        elif score > 0.0:
            return cls.LOW
        return cls.UNKNOWN


class VulnCategory(str, Enum):
    """Vulnerability categories based on OWASP Top 10 + extensions."""

    # OWASP Top 10 (2021)
    BROKEN_ACCESS_CONTROL = "broken-access-control"
    CRYPTOGRAPHIC_FAILURES = "cryptographic-failures"
    INJECTION = "injection"
    INSECURE_DESIGN = "insecure-design"
    SECURITY_MISCONFIGURATION = "security-misconfiguration"
    VULNERABLE_COMPONENTS = "vulnerable-components"
    AUTH_FAILURES = "authentication-failures"
    DATA_INTEGRITY_FAILURES = "data-integrity-failures"
    LOGGING_MONITORING_FAILURES = "logging-monitoring-failures"
    SSRF = "ssrf"

    # Network
    NETWORK_EXPOSURE = "network-exposure"
    OPEN_PORTS = "open-ports"
    TLS_ISSUES = "tls-issues"
    DNS_ISSUES = "dns-issues"

    # Information Disclosure
    INFO_DISCLOSURE = "information-disclosure"
    DIRECTORY_LISTING = "directory-listing"
    SERVER_INFO_LEAK = "server-info-leak"

    # Other
    CORS_MISCONFIG = "cors-misconfiguration"
    CSRF = "csrf"
    CLICKJACKING = "clickjacking"
    RATE_LIMITING = "rate-limiting"
    UNKNOWN = "unknown"

    @classmethod
    def from_nuclei_template(cls, template_name: str, tags: List[str]) -> "VulnCategory":
        """Map Nuclei template info to a vulnerability category."""
        template_lower = template_name.lower()
        tags_lower = [t.lower() for t in tags]

        # Injection-based patterns
        if any(t in tags_lower for t in ["sqli", "sql-injection", "injection", "ldap", "command-injection"]):
            return cls.INJECTION
        if "xss" in tags_lower or "cross-site" in template_lower:
            return cls.INJECTION

        # Auth patterns
        if any(t in tags_lower for t in ["auth", "authentication", "oauth", "jwt", "session"]):
            return cls.AUTH_FAILURES

        # Access control
        if any(t in tags_lower for t in ["idor", "access-control", "lfi", "rfi", "path-traversal"]):
            return cls.BROKEN_ACCESS_CONTROL

        # Config
        if any(t in tags_lower for t in ["misconfig", "misconfiguration", "cors", "hdr", "header"]):
            return cls.SECURITY_MISCONFIGURATION

        # Network
        if any(t in tags_lower for t in ["network", "port", "dns", "ssl", "tls", "exposure"]):
            if "tls" in tags_lower or "ssl" in tags_lower:
                return cls.TLS_ISSUES
            if "dns" in tags_lower:
                return cls.DNS_ISSUES
            return cls.NETWORK_EXPOSURE

        # Info disclosure
        if any(t in tags_lower for t in ["exposure", "disclosure", "leak", "debug", "info"]):
            return cls.INFO_DISCLOSURE

        # SSRF
        if "ssrf" in tags_lower:
            return cls.SSRF

        # Components
        if any(t in tags_lower for t in ["cve", "cpe", "component", "dependency", "package"]):
            return cls.VULNERABLE_COMPONENTS

        return cls.UNKNOWN


@dataclass
class VulnerabilityFinding:
    """A single vulnerability finding from any scanner."""

    # Core (required first — no defaults before required fields)
    id: str
    title: str
    description: str
    severity: VulnSeverity
    category: VulnCategory
    scanner: str  # "nuclei", "wstg", "custom"
    target: str  # URL or IP

    # Location (optional)
    endpoint: Optional[str] = None  # Specific path or parameter
    method: Optional[str] = None  # HTTP method if applicable
    port: Optional[int] = None

    # Source details
    template_name: Optional[str] = None
    template_id: Optional[str] = None

    # Evidence
    evidence: Optional[str] = None  # Proof of vulnerability
    request: Optional[str] = None  # HTTP request used
    response: Optional[str] = None  # HTTP response received
    curl_command: Optional[str] = None

    # Remediation
    remediation: Optional[str] = None
    references: List[str] = field(default_factory=list)
    cve_id: Optional[str] = None
    cwe_id: Optional[str] = None
    cvss_score: Optional[float] = None

    # Metadata
    raw_data: Optional[Dict[str, Any]] = None
    tags: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {}
        for k, v in asdict(self).items():
            if isinstance(v, Enum):
                result[k] = v.value
            else:
                result[k] = v
        return result


@dataclass
class VulnScanResult:
    """Complete vulnerability scan result."""

    scan_id: str
    scanner: str  # "nuclei", "wstg", "combined"
    scan_type: str  # "web", "network"
    target: str
    start_time: str
    end_time: str
    duration_seconds: float
    findings: List[VulnerabilityFinding] = field(default_factory=list)
    total_findings: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0
    raw_output: Optional[str] = None
    error: Optional[str] = None
    scan_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Auto-calculate counts from findings."""
        self._recalc_counts()

    def _recalc_counts(self):
        """Recompute severity counts."""
        self.total_findings = len(self.findings)
        self.critical_count = sum(1 for f in self.findings if f.severity == VulnSeverity.CRITICAL)
        self.high_count = sum(1 for f in self.findings if f.severity == VulnSeverity.HIGH)
        self.medium_count = sum(1 for f in self.findings if f.severity == VulnSeverity.MEDIUM)
        self.low_count = sum(1 for f in self.findings if f.severity == VulnSeverity.LOW)
        self.info_count = sum(1 for f in self.findings if f.severity == VulnSeverity.INFO)

    def add_finding(self, finding: VulnerabilityFinding):
        """Add a finding and recalculate counts."""
        self.findings.append(finding)
        self._recalc_counts()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "scan_id": self.scan_id,
            "scanner": self.scanner,
            "scan_type": self.scan_type,
            "target": self.target,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "total_findings": self.total_findings,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "info_count": self.info_count,
            "findings": [f.to_dict() for f in self.findings],
            "scan_metadata": self.scan_metadata,
        }
        if self.raw_output:
            result["raw_output"] = self.raw_output
        if self.error:
            result["error"] = self.error
        return result

    def get_findings_by_severity(self, severity: VulnSeverity) -> List[VulnerabilityFinding]:
        """Get findings filtered by severity level."""
        return [f for f in self.findings if f.severity == severity]

    def get_findings_by_category(self, category: VulnCategory) -> List[VulnerabilityFinding]:
        """Get findings filtered by category."""
        return [f for f in self.findings if f.category == category]


class UnifiedVulnParser:
    """Parser that normalizes scanner output to VulnScanResult."""

    @staticmethod
    def parse_nuclei_json(
        json_data: Union[str, List[Dict], Dict],
        scan_id: str,
        target: str,
        scan_type: str = "web",
    ) -> VulnScanResult:
        """Parse Nuclei JSON output into unified format.

        Args:
            json_data: Nuclei JSON output (string, list, or dict)
            scan_id: Unique scan identifier
            target: Target URL or IP
            scan_type: "web" or "network"

        Returns:
            VulnScanResult with normalized findings
        """
        start_time = datetime.utcnow().isoformat() + "Z"

        # Parse input
        if isinstance(json_data, str):
            try:
                raw = json.loads(json_data)
            except json.JSONDecodeError as e:
                return VulnScanResult(
                    scan_id=scan_id,
                    scanner="nuclei",
                    scan_type=scan_type,
                    target=target,
                    start_time=start_time,
                    end_time=datetime.utcnow().isoformat() + "Z",
                    duration_seconds=0.0,
                    error=f"Failed to parse Nuclei JSON: {e}",
                )
        else:
            raw = json_data

        # Handle both single result and array
        if isinstance(raw, dict):
            items = [raw]
        else:
            items = raw

        findings = []
        for item in items:
            # Skip informational matcher-status lines
            if item.get("template-id") == "" or item.get("type") == "":
                continue

            template_id = item.get("template-id", "") or item.get("templateID", "")
            template_name_raw = item.get("info", {}).get("name", template_id)
            severity_raw = item.get("info", {}).get("severity", "unknown")
            tags = item.get("info", {}).get("tags", [])
            if isinstance(tags, str):
                tags = [tags]

            finding_id = f"NUC-{template_id}-{len(item.get('matched-at', target)[:32])}" if template_id else f"NUC-{hash(str(item)) % 1000000:06d}"

            description = item.get("info", {}).get("description", "No description provided")
            remediation = item.get("info", {}).get("remediation")
            references_raw = item.get("info", {}).get("reference", [])
            if isinstance(references_raw, str):
                references = [references_raw]
            else:
                references = references_raw or []

            # Extract CVE/CWE from tags or info
            cve_id = None
            cwe_id = None
            for t in tags:
                if t.startswith("cve-") or t.startswith("CVE-"):
                    cve_id = t
                if t.startswith("cwe-") or t.startswith("CWE-"):
                    cwe_id = t
            if not cve_id:
                for ref in references:
                    if "cve" in ref.lower():
                        parts = ref.split("/")
                        for p in parts:
                            if p.startswith("CVE-") or p.startswith("cve-"):
                                cve_id = p.upper()
                                break

            # CVSS score from info
            cvss_score = item.get("info", {}).get("classification", {}).get("cvss-score")
            if cvss_score is not None:
                try:
                    cvss_score = float(cvss_score)
                except (ValueError, TypeError):
                    cvss_score = None

            # Evidence from matched info
            matched_at = item.get("matched-at", "")
            extracted_results = item.get("extracted-results", [])
            request = item.get("request", "")
            response = item.get("response", "")

            evidence_parts = []
            if extracted_results:
                evidence_parts.extend(str(r) for r in extracted_results[:3])
            if matched_at:
                evidence_parts.append(f"Matched at: {matched_at}")

            finding = VulnerabilityFinding(
                id=finding_id,
                title=template_name_raw or f"Nuclei finding: {template_id}",
                description=description,
                severity=VulnSeverity.from_nuclei(severity_raw),
                category=VulnCategory.from_nuclei_template(template_name_raw or "", tags),
                scanner="nuclei",
                template_name=template_name_raw,
                template_id=template_id,
                target=target,
                endpoint=matched_at or target,
                method=item.get("type", "GET") if item.get("type") else None,
                port=item.get("port"),
                evidence="\n".join(evidence_parts) if evidence_parts else None,
                request=str(request)[:2000] if request else None,
                response=str(response)[:2000] if response else None,
                remediation=remediation,
                references=references,
                cve_id=cve_id,
                cwe_id=cwe_id,
                cvss_score=cvss_score,
                tags=tags,
                raw_data=item,
            )
            findings.append(finding)

        end_time = datetime.utcnow().isoformat() + "Z"
        return VulnScanResult(
            scan_id=scan_id,
            scanner="nuclei",
            scan_type=scan_type,
            target=target,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=0.0,
            findings=findings,
            scan_metadata={"scanner_version": "2.x", "templates_count": len(items)},
        )

    @staticmethod
    def parse_wstg_json(
        json_data: Union[str, List[Dict], Dict],
        scan_id: str,
        target: str,
        scan_type: str = "web",
    ) -> VulnScanResult:
        """Parse WSTG-Scan JSON output into unified format.

        Args:
            json_data: WSTG scan JSON output
            scan_id: Unique scan identifier
            target: Target URL
            scan_type: "web" (WSTG is web-focused)

        Returns:
            VulnScanResult with normalized findings
        """
        start_time = datetime.utcnow().isoformat() + "Z"

        if isinstance(json_data, str):
            try:
                raw = json.loads(json_data)
            except json.JSONDecodeError as e:
                return VulnScanResult(
                    scan_id=scan_id,
                    scanner="wstg",
                    scan_type=scan_type,
                    target=target,
                    start_time=start_time,
                    end_time=datetime.utcnow().isoformat() + "Z",
                    duration_seconds=0.0,
                    error=f"Failed to parse WSTG JSON: {e}",
                )
        else:
            raw = json_data

        # WSTG output can be a dict with test results or a list
        if isinstance(raw, dict):
            # Try common WSTG output structures
            tests = raw.get("tests", raw.get("results", raw.get("findings", [raw])))
            if isinstance(tests, dict):
                items = []
                for test_name, test_data in tests.items():
                    if isinstance(test_data, list):
                        for item in test_data:
                            item["_test_name"] = test_name
                            items.append(item)
                    elif isinstance(test_data, dict):
                        test_data["_test_name"] = test_name
                        items.append(test_data)
            else:
                items = tests if isinstance(tests, list) else [raw]
        else:
            items = raw

        findings = []
        for item in items:
            test_name = item.get("_test_name", item.get("test", item.get("name", "WSTG test")))
            status = item.get("status", item.get("result", item.get("passed", "unknown")))
            risk = item.get("risk", item.get("severity", item.get("impact", "info")))

            # Only include actual findings (not passed tests)
            if isinstance(status, bool):
                if status is True:  # Passed
                    continue
            elif isinstance(status, str) and status.lower() in ("pass", "passed", "none", "not-vulnerable"):
                continue

            description = item.get("description", item.get("detail", "No description"))
            remediation = item.get("remediation", item.get("recommendation"))
            evidence = item.get("evidence", item.get("proof", item.get("detail")))

            finding_id = f"WSTG-{test_name[:32]}-{len(item.get('url', target)[:16])}" if test_name else f"WSTG-{hash(str(item)) % 1000000:06d}"

            references = item.get("references", [])
            if isinstance(references, str):
                references = [references]

            finding = VulnerabilityFinding(
                id=finding_id,
                title=f"WSTG: {test_name}",
                description=description,
                severity=VulnSeverity.from_wstg(risk),
                category=UnifiedVulnParser._wstg_to_category(item.get("wstg_id", ""), test_name),
                scanner="wstg",
                template_id=item.get("wstg_id"),
                target=target,
                endpoint=item.get("url", item.get("endpoint", target)),
                method=item.get("method", "GET"),
                evidence=evidence,
                remediation=remediation,
                references=references,
                tags=item.get("tags", []),
                raw_data=item,
            )
            findings.append(finding)

        end_time = datetime.utcnow().isoformat() + "Z"
        return VulnScanResult(
            scan_id=scan_id,
            scanner="wstg",
            scan_type=scan_type,
            target=target,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=0.0,
            findings=findings,
            scan_metadata={"wstg_version": "4.2", "tests_executed": len(items)},
        )

    @staticmethod
    def _wstg_to_category(wstg_id: str, test_name: str) -> VulnCategory:
        """Map WSTG test ID/category to unified category."""
        wstg_patterns = {
            "WSTG-INFO": VulnCategory.INFO_DISCLOSURE,
            "WSTG-CONF": VulnCategory.SECURITY_MISCONFIGURATION,
            "WSTG-IDNT": VulnCategory.AUTH_FAILURES,
            "WSTG-ATHN": VulnCategory.AUTH_FAILURES,
            "WSTG-ATHZ": VulnCategory.BROKEN_ACCESS_CONTROL,
            "WSTG-SESS": VulnCategory.AUTH_FAILURES,
            "WSTG-INPV": VulnCategory.INJECTION,
            "WSTG-CRYP": VulnCategory.CRYPTOGRAPHIC_FAILURES,
            "WSTG-ERRH": VulnCategory.LOGGING_MONITORING_FAILURES,
            "WSTG-BUSL": VulnCategory.INSECURE_DESIGN,
        }

        for prefix, category in wstg_patterns.items():
            if (wstg_id and wstg_id.startswith(prefix)) or (test_name and prefix in test_name):
                return category

        return VulnCategory.UNKNOWN

    @staticmethod
    def merge_results(results: List[VulnScanResult]) -> VulnScanResult:
        """Merge multiple scan results into one combined result.

        Useful for combining Nuclei + WSTG results.
        """
        if not results:
            raise ValueError("Cannot merge empty results list")

        base = results[0]
        all_findings = list(base.findings)
        for r in results[1:]:
            all_findings.extend(r.findings)

        # Deduplicate by (target, title, severity)
        seen = set()
        unique_findings = []
        for f in all_findings:
            key = (f.target, f.title, f.severity.value)
            if key not in seen:
                seen.add(key)
                unique_findings.append(f)

        merged = VulnScanResult(
            scan_id=f"merged-{base.scan_id}",
            scanner="combined",
            scan_type=base.scan_type,
            target=base.target,
            start_time=base.start_time,
            end_time=results[-1].end_time,
            duration_seconds=sum(r.duration_seconds for r in results),
            findings=unique_findings,
            scan_metadata={
                "merged_from": [r.scanner for r in results],
                "original_scan_ids": [r.scan_id for r in results],
            },
        )
        return merged

    @staticmethod
    def to_owasp_format(result: VulnScanResult) -> Dict[str, Any]:
        """Convert to OWASP Risk Rating format.

        Suitable for generating OWASP-compatible reports.
        """
        category_counts = {}
        for f in result.findings:
            cat = f.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1

        severity_breakdown = {
            "critical": result.critical_count,
            "high": result.high_count,
            "medium": result.medium_count,
            "low": result.low_count,
            "info": result.info_count,
        }

        # Calculate risk score (weighted)
        risk_score = (
            result.critical_count * 10
            + result.high_count * 7
            + result.medium_count * 4
            + result.low_count * 1
        )
        max_possible = max(result.total_findings * 10, 1) if result.total_findings > 0 else 1
        risk_percentage = min(100, (risk_score / max_possible) * 100)

        return {
            "scan_id": result.scan_id,
            "target": result.target,
            "scanner": result.scanner,
            "scan_type": result.scan_type,
            "timestamp": result.end_time,
            "risk_score": round(risk_percentage, 1),
            "risk_level": (
                "Critical" if risk_percentage >= 75
                else "High" if risk_percentage >= 50
                else "Medium" if risk_percentage >= 25
                else "Low"
            ),
            "severity_breakdown": severity_breakdown,
            "category_breakdown": category_counts,
            "total_findings": result.total_findings,
            "top_critical": [
                f.to_dict() for f in result.findings
                if f.severity in (VulnSeverity.CRITICAL, VulnSeverity.HIGH)
            ][:10],
            "metadata": result.scan_metadata,
        }
