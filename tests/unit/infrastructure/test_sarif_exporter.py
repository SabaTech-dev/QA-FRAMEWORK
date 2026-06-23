"""
Tests for SARIF 2.1.0 Exporter.

Covers:
- Finding to SARIF conversion
- Rule building and deduplication
- Severity mapping
- Fingerprint computation
- JSON output validation
- Schema compliance checks
"""

import pytest
import json
import hashlib

from infrastructure.compliance.sarif_exporter import (
    SarifExporter,
    SarifLevel,
    SarifSeverityMapping,
    SecurityFinding,
    SarifRule,
    SarifResult,
    SarifLocation,
    export_sarif,
)


class TestSarifSeverityMapping:
    """Tests for severity to SARIF level mapping."""

    def test_critical_maps_to_error(self):
        assert SarifSeverityMapping.to_sarif("critical") == SarifLevel.error

    def test_high_maps_to_error(self):
        assert SarifSeverityMapping.to_sarif("high") == SarifLevel.error

    def test_medium_maps_to_warning(self):
        assert SarifSeverityMapping.to_sarif("medium") == SarifLevel.warning

    def test_low_maps_to_note(self):
        assert SarifSeverityMapping.to_sarif("low") == SarifLevel.note

    def test_info_maps_to_note(self):
        assert SarifSeverityMapping.to_sarif("info") == SarifLevel.note

    def test_unknown_maps_to_warning(self):
        assert SarifSeverityMapping.to_sarif("bogus") == SarifLevel.warning


class TestSarifExporter:
    """Tests for SARIF export functionality."""

    def test_empty_findings(self):
        """Empty findings produce valid SARIF with no results."""
        exporter = SarifExporter()
        sarif = exporter.export([])

        assert sarif["version"] == "2.1.0"
        assert len(sarif["runs"]) == 1
        assert sarif["runs"][0]["results"] == []

    def test_single_finding(self):
        """Single finding produces valid SARIF."""
        finding = SecurityFinding(
            rule_id="zap-WASC-1",
            scanner="zap",
            title="XSS Vulnerability",
            description="Reflected XSS found",
            severity="high",
            url="https://example.com/search",
            method="GET",
        )
        exporter = SarifExporter()
        sarif = exporter.export([finding])

        assert len(sarif["runs"][0]["results"]) == 1
        result = sarif["runs"][0]["results"][0]
        assert result["ruleId"] == "zap-WASC-1"
        assert result["level"] == "error"  # high → error

    def test_multiple_findings_share_rules(self):
        """Multiple findings with same rule_id share a single rule definition."""
        findings = [
            SecurityFinding(rule_id="xss-001", scanner="zap", title="XSS", severity="high", url="https://a.com"),
            SecurityFinding(rule_id="xss-001", scanner="zap", title="XSS", severity="high", url="https://b.com"),
        ]
        exporter = SarifExporter()
        sarif = exporter.export(findings)

        rules = sarif["runs"][0]["tool"]["driver"]["rules"]
        assert len(rules) == 1  # deduplicated
        assert len(sarif["runs"][0]["results"]) == 2

    def test_fingerprint_deduplication(self):
        """Same finding at same URL produces same fingerprint."""
        finding = SecurityFinding(
            rule_id="sql-inj", scanner="nuclei", title="SQLi",
            severity="critical", url="https://example.com/login", method="POST",
        )
        exporter = SarifExporter()
        fp = exporter._compute_fingerprint(finding)

        expected = hashlib.sha256(b"nuclei:sql-inj:https://example.com/login:POST").hexdigest()[:32]
        assert fp == expected

    def test_json_output_is_valid(self):
        """JSON output is parseable."""
        findings = [
            SecurityFinding(rule_id="r1", scanner="trivy", title="CVE", severity="medium"),
        ]
        json_str = export_sarif(findings)

        parsed = json.loads(json_str)
        assert parsed["version"] == "2.1.0"
        assert "$schema" in parsed

    def test_tool_metadata_in_output(self):
        """Tool name and version appear in output."""
        exporter = SarifExporter(tool_name="CustomScanner", tool_version="3.0.0")
        sarif = exporter.export([])

        driver = sarif["runs"][0]["tool"]["driver"]
        assert driver["name"] == "CustomScanner"
        assert driver["version"] == "3.0.0"

    def test_locations_built_from_url(self):
        """URL in finding creates location in result."""
        finding = SecurityFinding(
            rule_id="r1", scanner="zap", title="Test",
            severity="low", url="https://example.com/api",
        )
        exporter = SarifExporter()
        sarif = exporter.export([finding])

        result = sarif["runs"][0]["results"][0]
        assert len(result["locations"]) == 1
        assert result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "https://example.com/api"

    def test_cwe_in_rule_tags(self):
        """CWE appears in rule tags."""
        finding = SecurityFinding(
            rule_id="r1", scanner="zap", title="XSS",
            severity="high", cwe="CWE-79",
        )
        exporter = SarifExporter()
        sarif = exporter.export([finding])

        rule = sarif["runs"][0]["tool"]["driver"]["rules"][0]
        assert "cwe:CWE-79" in rule["tags"]

    def test_convenience_function(self):
        """export_sarif returns JSON string."""
        json_str = export_sarif([
            SecurityFinding(rule_id="r1", scanner="test", title="T", severity="info"),
        ])
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert len(parsed["runs"][0]["results"]) == 1


class TestSecurityFindingModel:
    """Tests for SecurityFinding model."""

    def test_defaults(self):
        """SecurityFinding has sensible defaults."""
        f = SecurityFinding(rule_id="r1", scanner="test", title="Test")
        assert f.severity == "medium"
        assert f.confidence == "medium"
        assert f.references == []

    def test_metadata_dict(self):
        """Custom metadata preserved."""
        f = SecurityFinding(
            rule_id="r1", scanner="test", title="Test",
            metadata={"custom_field": "value"},
        )
        assert f.metadata["custom_field"] == "value"
