"""
SARIF 2.1.0 Exporter — Security findings serialization.

Converts security scan findings (ZAP, Nuclei, Trivy, custom) to
SARIF (Static Analysis Results Interchange Format) 2.1.0 JSON format.

Spec: https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html
"""

import json
import hashlib
from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class SarifLevel(str, Enum):
    """SARIF result severity levels."""
    none = "none"
    note = "note"
    warning = "warning"
    error = "error"


class SarifSeverityMapping:
    """Maps tool-specific severity to SARIF levels."""
    MAPPING = {
        "critical": SarifLevel.error,
        "high": SarifLevel.error,
        "medium": SarifLevel.warning,
        "moderate": SarifLevel.warning,
        "low": SarifLevel.note,
        "info": SarifLevel.note,
        "informational": SarifLevel.note,
    }

    @classmethod
    def to_sarif(cls, severity: str) -> SarifLevel:
        """Convert tool severity to SARIF level."""
        return cls.MAPPING.get(severity.lower(), SarifLevel.warning)


class SarifLocation(BaseModel):
    """SARIF physical location."""
    uri: str = Field(..., description="File or endpoint URI")
    start_line: Optional[int] = Field(default=None, description="Start line number")
    end_line: Optional[int] = Field(default=None)
    start_column: Optional[int] = Field(default=None)
    end_column: Optional[int] = Field(default=None)


class SarifResult(BaseModel):
    """SARIF result entry."""
    rule_id: str = Field(..., description="Rule identifier")
    level: SarifLevel = Field(default=SarifLevel.warning)
    message: str = Field(..., description="Finding description")
    locations: List[SarifLocation] = Field(default_factory=list)
    fingerprint: Optional[str] = Field(default=None, description="Unique finding hash")
    partial_fingerprints: Optional[Dict[str, str]] = None
    code_flows: Optional[List[dict]] = None


class SarifRule(BaseModel):
    """SARIF rule metadata."""
    id: str = Field(..., description="Unique rule ID")
    name: str = Field(..., description="Human-readable rule name")
    short_description: Optional[str] = None
    full_description: Optional[str] = None
    help_uri: Optional[str] = Field(default=None, description="URL to rule documentation")
    default_level: SarifLevel = SarifLevel.warning
    tags: List[str] = Field(default_factory=list)


class SecurityFinding(BaseModel):
    """Normalized security finding from any scanner."""
    rule_id: str = Field(..., description="Rule/vulnerability ID (e.g., zap-WASC-1, nuclei-cve-2024-1234)")
    scanner: str = Field(..., description="Source scanner (zap, nuclei, trivy, custom)")
    title: str = Field(..., description="Finding title")
    description: str = Field(default="", description="Detailed description")
    severity: str = Field(default="medium", description="critical, high, medium, low, info")
    url: Optional[str] = Field(default=None, description="Affected URL")
    endpoint: Optional[str] = Field(default=None, description="Affected endpoint path")
    method: Optional[str] = Field(default=None, description="HTTP method")
    evidence: Optional[str] = Field(default=None, description="Proof of concept")
    confidence: Optional[str] = Field(default="medium", description="Finding confidence")
    cwe: Optional[str] = Field(default=None, description="CWE identifier")
    references: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SarifExporter:
    """
    Serializes security findings to SARIF 2.1.0 format.

    Usage:
        exporter = SarifExporter(tool_name="ZAP", tool_version="2.14.0")
        sarif = exporter.export(findings=[finding1, finding2])
        json_str = exporter.to_json(sarif)
    """

    SARIF_VERSION = "2.1.0"
    SARIF_SCHEMA = (
        "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/"
        "Schemata/sarif-schema-2.1.0.json"
    )

    def __init__(self, tool_name: str = "QA-FRAMEWORK", tool_version: str = "0.1.0"):
        self.tool_name = tool_name
        self.tool_version = tool_version

    def export(self, findings: List[SecurityFinding]) -> dict:
        """
        Convert findings to SARIF 2.1.0 dictionary.

        Args:
            findings: List of normalized security findings

        Returns:
            SARIF 2.1.0 compliant dictionary
        """
        rules = self._build_rules(findings)
        results = self._build_results(findings)

        return {
            "$schema": self.SARIF_SCHEMA,
            "version": self.SARIF_VERSION,
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": self.tool_name,
                            "version": self.tool_version,
                            "informationUri": "https://github.com/SabaTech-dev/QA-FRAMEWORK",
                            "rules": [r.model_dump(exclude_none=True) for r in rules],
                        }
                    },
                    "results": [r for r in results],
                }
            ],
        }

    def to_json(self, sarif: dict, indent: int = 2) -> str:
        """Serialize SARIF dict to JSON string."""
        return json.dumps(sarif, indent=indent, default=str)

    def _build_rules(self, findings: List[SecurityFinding]) -> List[SarifRule]:
        """Build unique rules from findings."""
        seen = {}
        for f in findings:
            if f.rule_id not in seen:
                tags = []
                if f.cwe:
                    tags.append(f"cwe:{f.cwe}")
                tags.append(f"scanner:{f.scanner}")

                seen[f.rule_id] = SarifRule(
                    id=f.rule_id,
                    name=f.title[:200],
                    short_description=f.description[:500] if f.description else None,
                    default_level=SarifSeverityMapping.to_sarif(f.severity),
                    help_uri=f.references[0] if f.references else None,
                    tags=tags,
                )
        return list(seen.values())

    def _build_results(self, findings: List[SecurityFinding]) -> List[dict]:
        """Build SARIF result objects from findings."""
        results = []
        for f in findings:
            locations = []
            if f.url or f.endpoint:
                loc_uri = f.url or f.endpoint
                locations.append({"physicalLocation": {"artifactLocation": {"uri": loc_uri}}})
                if f.method:
                    locations[0]["physicalLocation"]["address"] = {"method": f.method}

            fingerprint = self._compute_fingerprint(f)

            result = {
                "ruleId": f.rule_id,
                "level": SarifSeverityMapping.to_sarif(f.severity).value,
                "message": {"text": f.description or f.title},
                "locations": locations,
                "fingerprints": {"primary": fingerprint},
                "partialFingerprints": {
                    "scanner": f.scanner,
                    "severity": f.severity,
                    "confidence": f.confidence or "unknown",
                },
                "properties": {
                    "scanner": f.scanner,
                    "severity": f.severity,
                    "evidence": f.evidence,
                    "cwe": f.cwe,
                },
            }

            # Remove None values
            result["properties"] = {k: v for k, v in result["properties"].items() if v is not None}

            results.append(result)
        return results

    def _compute_fingerprint(self, finding: SecurityFinding) -> str:
        """Compute unique fingerprint for deduplication."""
        raw = f"{finding.scanner}:{finding.rule_id}:{finding.url or finding.endpoint or ''}:{finding.method or ''}"
        return hashlib.sha256(raw.encode()).hexdigest()[:32]


def export_sarif(
    findings: List[SecurityFinding],
    tool_name: str = "QA-FRAMEWORK",
    tool_version: str = "0.1.0",
) -> str:
    """
    Convenience function: export findings as SARIF JSON string.

    Args:
        findings: List of security findings
        tool_name: Scanning tool name
        tool_version: Tool version

    Returns:
        SARIF 2.1.0 JSON string
    """
    exporter = SarifExporter(tool_name=tool_name, tool_version=tool_version)
    sarif = exporter.export(findings)
    return exporter.to_json(sarif)
