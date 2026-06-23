"""
Integration tests for AI Act Compliance module.

End-to-end pipeline: Security scan → SARIF report → Annex IV export → Validation.

Tests the full compliance workflow:
1. Simulate security scan findings
2. Serialize to SARIF 2.1.0 format
3. Generate Annex IV evidence document
4. Validate both outputs against schema requirements
5. Verify cross-references between documents
"""

import pytest
import json
from datetime import datetime

from infrastructure.compliance.sarif_exporter import (
    SarifExporter,
    SecurityFinding,
    SarifLevel,
)
from infrastructure.compliance.annex_iv_requirements import (
    AnnexIVDocument,
    RiskLevel,
)
from domain.compliance.annex_iv_exporter import AnnexIVExporter


class TestCompliancePipeline:
    """End-to-end compliance pipeline integration tests."""

    def test_full_pipeline_scan_to_compliance(self):
        """
        Full pipeline: simulated scan → SARIF → Annex IV → validation.

        This simulates a real compliance workflow:
        1. Security scanner produces findings
        2. Findings serialized to SARIF
        3. Metrics extracted for Annex IV
        4. Annex IV document generated
        5. Both outputs validated
        """
        # Step 1: Simulate scan findings
        findings = [
            SecurityFinding(
                rule_id="zap-WASC-8/Cross-Site-Scripting",
                scanner="zap",
                title="Reflected XSS in search parameter",
                description="User input reflected without encoding in /search endpoint",
                severity="high",
                url="https://staging.qa-framework.sabatech.dev/search",
                method="GET",
                cwe="CWE-79",
                evidence="<script>alert(1)</script>",
                references=["https://owasp.org/www-community/attacks/xss/"],
            ),
            SecurityFinding(
                rule_id="nuclei-cve-2024-1234",
                scanner="nuclei",
                title="Known vulnerability in dependency",
                description="Outdated library version detected",
                severity="medium",
                url="https://staging.qa-framework.sabatech.dev/api/health",
                method="GET",
            ),
            SecurityFinding(
                rule_id="trivy-CVE-2024-5678",
                scanner="trivy",
                title="Container vulnerability",
                description="Vulnerable package in Docker image",
                severity="low",
            ),
        ]

        # Step 2: Serialize to SARIF
        sarif_exporter = SarifExporter(tool_name="QA-FRAMEWORK-Scan", tool_version="0.1.0")
        sarif = sarif_exporter.export(findings)

        # Step 3: Extract metrics for Annex IV
        execution_stats = {
            "total_executions": 150,
            "passed": 130,
            "failed": 20,
        }

        test_results = [
            {"status": "passed", "ai_generated": True},
            {"status": "passed", "ai_generated": True},
            {"status": "passed", "ai_generated": True},
            {"status": "passed", "ai_generated": False},
            {"status": "failed", "ai_generated": True},
        ]

        # Step 4: Generate Annex IV
        annex_exporter = AnnexIVExporter()
        annex_doc = annex_exporter.generate(
            execution_stats=execution_stats,
            test_results=test_results,
        )

        # Step 5: Validate SARIF output
        assert sarif["version"] == "2.1.0"
        assert len(sarif["runs"][0]["results"]) == 3
        assert sarif["runs"][0]["tool"]["driver"]["name"] == "QA-FRAMEWORK-Scan"

        # Verify rule deduplication
        rules = sarif["runs"][0]["tool"]["driver"]["rules"]
        assert len(rules) == 3  # all unique rule_ids

        # Verify severity mapping
        results = sarif["runs"][0]["results"]
        high_result = [r for r in results if r["level"] == "error"]
        assert len(high_result) == 1  # the XSS finding

        # Step 6: Validate Annex IV output
        assert annex_doc.system_description.name == "QA-FRAMEWORK"
        assert len(annex_doc.evaluation_results) > 0

        # Verify metrics computed
        pass_rate = [r for r in annex_doc.evaluation_results if r.metric_name == "pass_rate"]
        assert len(pass_rate) == 1
        assert pass_rate[0].metric_value == pytest.approx(86.67, abs=0.1)

        # Verify risk assessment
        assert len(annex_doc.risk_assessment.identified_risks) > 0
        assert annex_doc.risk_assessment.residual_risk_level in [
            RiskLevel.minimal,
            RiskLevel.limited,
            RiskLevel.high,
        ]

    def test_sarif_json_serialization_roundtrip(self):
        """SARIF output survives JSON roundtrip without data loss."""
        findings = [
            SecurityFinding(
                rule_id="test-rule",
                scanner="test",
                title="Test Finding",
                description="Test description",
                severity="critical",
                url="https://example.com",
            )
        ]
        exporter = SarifExporter()
        sarif = exporter.export(findings)
        json_str = exporter.to_json(sarif)

        # Roundtrip
        restored = json.loads(json_str)

        assert restored["version"] == sarif["version"]
        assert len(restored["runs"][0]["results"]) == len(sarif["runs"][0]["results"])
        assert restored["runs"][0]["results"][0]["ruleId"] == "test-rule"

    def test_annex_iv_json_serialization_roundtrip(self):
        """Annex IV output survives JSON roundtrip without data loss."""
        exporter = AnnexIVExporter()
        doc = exporter.generate(
            execution_stats={"total_executions": 10, "passed": 8, "failed": 2},
        )
        json_str = exporter.to_json(doc)

        restored = json.loads(json_str)

        assert restored["system_description"]["name"] == "QA-FRAMEWORK"
        assert restored["schema_version"] == "1.0.0"
        assert len(restored["evaluation_results"]) > 0

    def test_cross_reference_sarif_to_annex(self):
        """SARIF findings count can be referenced in Annex IV risk assessment."""
        findings = [
            SecurityFinding(rule_id=f"rule-{i}", scanner="test", title=f"Finding {i}", severity="high")
            for i in range(5)
        ]

        sarif_exporter = SarifExporter()
        sarif = sarif_exporter.export(findings)
        finding_count = len(sarif["runs"][0]["results"])

        annex_exporter = AnnexIVExporter()
        doc = annex_exporter.generate(
            custom_overrides={
                "risk_assessment": {
                    "identified_risks": [
                        f"{finding_count} security vulnerabilities identified in latest scan"
                    ],
                }
            }
        )

        assert f"{finding_count} security vulnerabilities" in doc.risk_assessment.identified_risks[0]

    def test_empty_scan_results(self):
        """Empty scan produces valid (empty) SARIF and valid Annex IV."""
        sarif_exporter = SarifExporter()
        sarif = sarif_exporter.export([])

        assert sarif["runs"][0]["results"] == []
        assert sarif["runs"][0]["tool"]["driver"]["rules"] == []

        annex_exporter = AnnexIVExporter()
        doc = annex_exporter.generate()

        assert doc.system_description.name == "QA-FRAMEWORK"
        assert len(doc.evaluation_results) == 1  # placeholder

    def test_multi_scanner_findings(self):
        """Findings from multiple scanners in one SARIF report."""
        findings = [
            SecurityFinding(rule_id="zap-1", scanner="zap", title="ZAP Finding", severity="high"),
            SecurityFinding(rule_id="nuclei-1", scanner="nuclei", title="Nuclei Finding", severity="medium"),
            SecurityFinding(rule_id="trivy-1", scanner="trivy", title="Trivy Finding", severity="low"),
        ]

        sarif = SarifExporter().export(findings)
        results = sarif["runs"][0]["results"]

        scanners = {r["properties"]["scanner"] for r in results}
        assert scanners == {"zap", "nuclei", "trivy"}

    def test_compliance_workflow_summary(self):
        """Generate a summary combining SARIF and Annex IV data."""
        findings = [
            SecurityFinding(rule_id="critical-1", scanner="zap", title="Critical", severity="critical"),
            SecurityFinding(rule_id="high-1", scanner="nuclei", title="High", severity="high"),
            SecurityFinding(rule_id="low-1", scanner="trivy", title="Low", severity="low"),
        ]

        sarif = SarifExporter().export(findings)
        annex = AnnexIVExporter().generate()

        # Build summary
        results = sarif["runs"][0]["results"]
        summary = {
            "scan_date": datetime.utcnow().isoformat(),
            "total_findings": len(results),
            "critical_findings": sum(1 for r in results if r["level"] == "error"),
            "warning_findings": sum(1 for r in results if r["level"] == "warning"),
            "system_name": annex.system_description.name,
            "risk_level": annex.risk_assessment.residual_risk_level.value,
            "compliant": len(results) == 0 or annex.risk_assessment.residual_risk_level in [
                RiskLevel.minimal,
                RiskLevel.limited,
            ],
        }

        assert summary["total_findings"] == 3
        assert summary["critical_findings"] == 2  # critical + high both map to error
        assert summary["warning_findings"] == 1  # medium maps to warning
        assert summary["system_name"] == "QA-FRAMEWORK"
