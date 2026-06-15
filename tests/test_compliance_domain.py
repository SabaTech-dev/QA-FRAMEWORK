"""
Tests for AI Act Compliance Domain — Value Objects & Entities

Covers:
- Value object enum coverage and validation
- Entity construction, serialization, business logic
- Security: input validation, injection prevention
- Serialization correctness (to_dict, to_json)
"""

import json
import pytest
from datetime import datetime, timezone

from src.domain.compliance.value_objects import (
    RiskTier,
    SystemType,
    ComplianceStatus,
    AnnexIVSection,
    SARIFLevel,
    SARIFResultKind,
    AnnexIVRequirement,
    validate_system_id,
    validate_provider_name,
    MAX_SYSTEM_ID_LENGTH,
    MAX_PROVIDER_NAME_LENGTH,
)
from src.domain.compliance.entities import (
    SystemDescription,
    TestingMethodology,
    ComplianceEvidence,
    AnnexIVReport,
    SARIFRun,
    SARIFReport,
)


# ========================================================================
# Value Object Enums
# ========================================================================

class TestRiskTier:
    def test_all_values(self):
        assert RiskTier.PROHIBITED.value == "prohibited"
        assert RiskTier.HIGH_RISK.value == "high_risk"
        assert RiskTier.LIMITED_RISK.value == "limited_risk"
        assert RiskTier.MINIMAL_RISK.value == "minimal_risk"

    def test_str_enum(self):
        assert isinstance(RiskTier.HIGH_RISK, str)


class TestSystemType:
    def test_all_values(self):
        assert SystemType.STANDALONE.value == "standalone"
        assert SystemType.GPAI.value == "gpai"

    def test_str_enum(self):
        assert isinstance(SystemType.EMBEDDED, str)


class TestComplianceStatus:
    def test_all_values(self):
        assert ComplianceStatus.COMPLIANT.value == "compliant"
        assert ComplianceStatus.NON_COMPLIANT.value == "non_compliant"
        assert ComplianceStatus.PARTIALLY_COMPLIANT.value == "partially_compliant"
        assert ComplianceStatus.PENDING_REVIEW.value == "pending_review"


class TestAnnexIVSection:
    def test_all_16_sections(self):
        assert len(AnnexIVSection) == 16

    def test_section_values_are_strings(self):
        for section in AnnexIVSection:
            assert isinstance(section.value, str)

    def test_key_sections(self):
        assert AnnexIVSection.SYSTEM_DESCRIPTION.value == "1"
        assert AnnexIVSection.ACCURACY_ROBUSTNESS.value == "11"
        assert AnnexIVSection.CYBERSECURITY.value == "12"
        assert AnnexIVSection.POST_MARKET.value == "16"


class TestSARIFLevel:
    def test_values(self):
        assert SARIFLevel.NONE.value == "none"
        assert SARIFLevel.NOTE.value == "note"
        assert SARIFLevel.WARNING.value == "warning"
        assert SARIFLevel.ERROR.value == "error"

    def test_str_enum(self):
        assert isinstance(SARIFLevel.ERROR, str)


class TestSARIFResultKind:
    def test_values(self):
        assert SARIFResultKind.PASS.value == "pass"
        assert SARIFResultKind.FAIL.value == "fail"
        assert SARIFResultKind.REVIEW.value == "review"

    def test_str_enum(self):
        assert isinstance(SARIFResultKind.PASS, str)


# ========================================================================
# Input Validation
# ========================================================================

class TestValidateSystemId:
    def test_valid_simple(self):
        assert validate_system_id("my-system") == "my-system"

    def test_valid_with_dots(self):
        assert validate_system_id("com.example.ai") == "com.example.ai"

    def test_valid_alphanumeric(self):
        assert validate_system_id("AI001") == "AI001"

    def test_valid_colon(self):
        assert validate_system_id("org:system:v1") == "org:system:v1"

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            validate_system_id("")

    def test_none_raises(self):
        with pytest.raises((ValueError, TypeError)):
            validate_system_id(None)

    def test_starts_with_special_char_raises(self):
        with pytest.raises(ValueError, match="must start with alphanumeric"):
            validate_system_id("-invalid")

    def test_spaces_not_allowed(self):
        with pytest.raises(ValueError, match="must start with alphanumeric"):
            validate_system_id("has space")

    def test_exceeds_max_length_raises(self):
        long_id = "a" * (MAX_SYSTEM_ID_LENGTH + 1)
        with pytest.raises(ValueError, match="exceeds max length"):
            validate_system_id(long_id)

    def test_max_length_boundary(self):
        boundary_id = "a" * MAX_SYSTEM_ID_LENGTH
        assert validate_system_id(boundary_id) == boundary_id

    def test_injection_attempt_blocked(self):
        with pytest.raises(ValueError):
            validate_system_id("system;<script>alert(1)</script>")


class TestValidateProviderName:
    def test_valid_name(self):
        assert validate_provider_name("Acme Corp") == "Acme Corp"

    def test_valid_unicode(self):
        assert validate_provider_name("SabaTech España") == "SabaTech España"

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            validate_provider_name("")

    def test_control_chars_rejected(self):
        with pytest.raises(ValueError, match="forbidden characters"):
            validate_provider_name("name\nwith\nnewlines")

    def test_angle_brackets_rejected(self):
        with pytest.raises(ValueError, match="forbidden characters"):
            validate_provider_name("<script>injection</script>")

    def test_exceeds_max_length_raises(self):
        long_name = "a" * (MAX_PROVIDER_NAME_LENGTH + 1)
        with pytest.raises(ValueError, match="exceeds max length"):
            validate_provider_name(long_name)

    def test_max_length_boundary(self):
        boundary_name = "a" * MAX_PROVIDER_NAME_LENGTH
        assert validate_provider_name(boundary_name) == boundary_name


class TestAnnexIVRequirement:
    def test_basic_construction(self):
        req = AnnexIVRequirement(
            section=AnnexIVSection.ACCURACY_ROBUSTNESS,
            title="Test Requirement",
            description="A test description",
        )
        assert req.is_satisfied is False
        assert req.status == "not documented"

    def test_satisfied_status(self):
        req = AnnexIVRequirement(
            section=AnnexIVSection.SYSTEM_DESCRIPTION,
            title="Done",
            description="Complete",
            is_satisfied=True,
        )
        assert req.status == "satisfied"

    def test_gap_status(self):
        req = AnnexIVRequirement(
            section=AnnexIVSection.CYBERSECURITY,
            title="Gap",
            description="Missing",
            gap_description="Not tested yet",
        )
        assert "gap" in req.status

    def test_title_too_long_raises(self):
        with pytest.raises(ValueError, match="title must be 1-300"):
            AnnexIVRequirement(
                section=AnnexIVSection.SYSTEM_DESCRIPTION,
                title="x" * 301,
                description="ok",
            )

    def test_empty_title_raises(self):
        with pytest.raises(ValueError, match="title must be 1-300"):
            AnnexIVRequirement(
                section=AnnexIVSection.SYSTEM_DESCRIPTION,
                title="",
                description="ok",
            )

    def test_description_too_long_raises(self):
        with pytest.raises(ValueError, match="description exceeds 5000"):
            AnnexIVRequirement(
                section=AnnexIVSection.SYSTEM_DESCRIPTION,
                title="ok",
                description="x" * 5001,
            )

    def test_to_dict(self):
        req = AnnexIVRequirement(
            section=AnnexIVSection.ACCURACY_ROBUSTNESS,
            title="Accuracy Test",
            description="Verify accuracy",
            is_satisfied=True,
            evidence_ref="eval-001",
        )
        d = req.to_dict()
        assert d["section"] == "11"
        assert d["title"] == "Accuracy Test"
        assert d["is_satisfied"] is True
        assert d["evidence_ref"] == "eval-001"


# ========================================================================
# Entities — SystemDescription
# ========================================================================

class TestSystemDescription:
    def test_default_construction(self):
        s = SystemDescription()
        assert s.risk_tier == RiskTier.HIGH_RISK
        assert s.system_type == SystemType.STANDALONE

    def test_validates_system_id_on_init(self):
        s = SystemDescription(system_id="my-ai-system", provider_name="Acme")
        assert s.system_id == "my-ai-system"

    def test_invalid_system_id_raises(self):
        with pytest.raises(ValueError):
            SystemDescription(system_id="-bad")

    def test_invalid_provider_name_raises(self):
        with pytest.raises(ValueError):
            SystemDescription(provider_name="<script>")

    def test_to_dict(self):
        s = SystemDescription(
            system_id="test-001",
            name="TestAI",
            provider_name="TestCorp",
            risk_tier=RiskTier.HIGH_RISK,
            version="1.0.0",
            description="A test AI system",
            intended_purpose="Legal advice",
            target_users="Lawyers",
            likely_affected_persons="Clients",
        )
        d = s.to_dict()
        assert d["system_id"] == "test-001"
        assert d["name"] == "TestAI"
        assert d["provider_name"] == "TestCorp"
        assert d["risk_tier"] == "high_risk"
        assert d["version"] == "1.0.0"


# ========================================================================
# Entities — TestingMethodology
# ========================================================================

class TestTestingMethodology:
    def test_default(self):
        m = TestingMethodology()
        assert m.passing_threshold == 0.6

    def test_invalid_threshold_raises(self):
        with pytest.raises(ValueError, match="passing_threshold"):
            TestingMethodology(passing_threshold=1.5)

    def test_negative_threshold_raises(self):
        with pytest.raises(ValueError, match="passing_threshold"):
            TestingMethodology(passing_threshold=-0.1)

    def test_to_dict(self):
        m = TestingMethodology(
            methodology_name="Rule-based Eval",
            description="Keyword matching evaluation",
            test_categories=["accuracy", "robustness"],
            benchmarks_used=["BGH-AI-001"],
            evaluation_metrics=["factual_accuracy", "completeness"],
            passing_threshold=0.7,
        )
        d = m.to_dict()
        assert d["methodology_name"] == "Rule-based Eval"
        assert d["passing_threshold"] == 0.7
        assert "accuracy" in d["test_categories"]


# ========================================================================
# Entities — ComplianceEvidence
# ========================================================================

class TestComplianceEvidence:
    def test_construction(self):
        e = ComplianceEvidence(
            annex_section=AnnexIVSection.ACCURACY_ROBUSTNESS,
            evidence_type="accuracy_test",
            title="Test",
            description="Evidence",
            metric_value=0.85,
            metric_target=0.6,
            passed=True,
        )
        assert e.meets_target is True
        assert e.id  # auto-generated

    def test_does_not_meet_target(self):
        e = ComplianceEvidence(
            metric_value=0.3,
            metric_target=0.6,
        )
        assert e.meets_target is False

    def test_to_dict(self):
        e = ComplianceEvidence(
            annex_section=AnnexIVSection.CYBERSECURITY,
            evidence_type="safety_finding",
            title="Hallucination",
            metric_value=2.0,
            metric_target=0.0,
            passed=False,
        )
        d = e.to_dict()
        assert d["annex_section"] == "12"
        assert d["passed"] is False
        assert "id" in d
        assert "generated_at" in d


# ========================================================================
# Entities — AnnexIVReport
# ========================================================================

class TestAnnexIVReport:
    def test_empty_report(self):
        r = AnnexIVReport()
        assert r.compliance_status == ComplianceStatus.PENDING_REVIEW
        assert len(r.evidence) == 0

    def test_add_evidence(self):
        r = AnnexIVReport()
        e = ComplianceEvidence(title="test", description="test")
        r.add_evidence(e)
        assert len(r.evidence) == 1

    def test_compute_compliance_no_data(self):
        r = AnnexIVReport()
        status = r.compute_compliance()
        assert status == ComplianceStatus.PENDING_REVIEW

    def test_compute_compliance_all_pass(self):
        from .annex_iv_requirements_helper import make_satisfied_requirements, make_passing_evidence
        r = AnnexIVReport(
            requirements=make_satisfied_requirements(),
            evidence=make_passing_evidence(),
        )
        status = r.compute_compliance()
        assert status == ComplianceStatus.COMPLIANT

    def test_compute_compliance_partial(self):
        from .annex_iv_requirements_helper import make_mixed_requirements, make_passing_evidence
        r = AnnexIVReport(
            requirements=make_mixed_requirements(),
            evidence=make_passing_evidence(),
        )
        status = r.compute_compliance()
        assert status == ComplianceStatus.NON_COMPLIANT

    def test_to_dict(self):
        r = AnnexIVReport(
            system=SystemDescription(system_id="test-001", provider_name="Corp"),
        )
        d = r.to_dict()
        assert "system" in d
        assert "methodology" in d
        assert "evidence" in d
        assert "requirements" in d
        assert "compliance_status" in d
        assert "tenant_id" not in d  # no tenant leak

    def test_to_json(self):
        r = AnnexIVReport(
            system=SystemDescription(system_id="test-001", provider_name="Corp"),
        )
        json_str = r.to_json()
        parsed = json.loads(json_str)
        assert parsed["system"]["system_id"] == "test-001"

    def test_tenant_id_not_in_dict(self):
        r = AnnexIVReport(tenant_id="secret-tenant")
        d = r.to_dict()
        assert "tenant_id" not in d


# ========================================================================
# Entities — SARIFRun & SARIFReport
# ========================================================================

class TestSARIFRun:
    def test_default(self):
        run = SARIFRun()
        assert run.tool_name == "qa-framework"
        assert len(run.results) == 0

    def test_add_result(self):
        run = SARIFRun()
        run.add_result(
            rule_id="QA-001",
            level=SARIFLevel.ERROR,
            kind=SARIFResultKind.FAIL,
            message="Test failure",
        )
        assert len(run.results) == 1
        r = run.results[0]
        assert r["ruleId"] == "QA-001"
        assert r["level"] == "error"
        assert r["kind"] == "fail"

    def test_add_result_with_location(self):
        run = SARIFRun()
        run.add_result(
            rule_id="QA-001",
            level=SARIFLevel.WARNING,
            kind=SARIFResultKind.REVIEW,
            message="Review needed",
            locations=[{"logicalLocations": [{"name": "bench-001"}]}],
        )
        assert len(run.results[0]["locations"]) == 1

    def test_add_result_with_properties(self):
        run = SARIFRun()
        run.add_result(
            rule_id="QA-001",
            level=SARIFLevel.NONE,
            kind=SARIFResultKind.PASS,
            message="All good",
            properties={"score": 0.95},
        )
        assert run.results[0]["properties"]["score"] == 0.95

    def test_to_dict(self):
        run = SARIFRun(
            tool_name="test-tool",
            tool_version="2.0.0",
        )
        d = run.to_dict()
        assert d["tool"]["driver"]["name"] == "test-tool"
        assert d["tool"]["driver"]["version"] == "2.0.0"


class TestSARIFReport:
    def test_default(self):
        r = SARIFReport()
        assert r.version == "2.1.0"
        assert len(r.runs) == 0

    def test_add_run(self):
        r = SARIFReport()
        run = SARIFRun()
        r.add_run(run)
        assert len(r.runs) == 1

    def test_to_dict(self):
        r = SARIFReport()
        d = r.to_dict()
        assert d["version"] == "2.1.0"
        assert "$schema" in d
        assert "runs" in d
        assert "tenant_id" not in d

    def test_to_json(self):
        r = SARIFReport(runs=[SARIFRun()])
        json_str = r.to_json()
        parsed = json.loads(json_str)
        assert parsed["version"] == "2.1.0"
        assert len(parsed["runs"]) == 1

    def test_schema_uri_valid(self):
        r = SARIFReport()
        d = r.to_dict()
        assert d["$schema"].startswith("https://")

    def test_tenant_id_not_in_dict(self):
        r = SARIFReport(tenant_id="secret")
        d = r.to_dict()
        assert "tenant_id" not in d


# ========================================================================
# Module Import Paths
# ========================================================================

class TestModuleImports:
    def test_import_domain_package(self):
        import src.domain.compliance as pkg
        expected = [
            "SystemType", "RiskTier", "ComplianceStatus", "AnnexIVSection",
            "SARIFLevel", "SARIFResultKind", "validate_system_id",
            "validate_provider_name", "SystemDescription", "TestingMethodology",
            "ComplianceEvidence", "AnnexIVReport", "SARIFRun", "SARIFReport",
            "IAnnexIVExporter", "ISARIFExporter", "IComplianceRepository",
        ]
        for name in expected:
            assert hasattr(pkg, name), f"Missing export: {name}"

    def test_import_infrastructure_package(self):
        import src.infrastructure.compliance as pkg
        assert hasattr(pkg, "AnnexIVExporter")
        assert hasattr(pkg, "SARIFExporter")
        assert hasattr(pkg, "create_default_requirements")

    def test_import_from_domain_entities(self):
        from src.domain.compliance.entities import (
            SystemDescription, TestingMethodology,
            ComplianceEvidence, AnnexIVReport,
            SARIFRun, SARIFReport,
        )
        assert all(cls is not None for cls in [
            SystemDescription, TestingMethodology,
            ComplianceEvidence, AnnexIVReport,
            SARIFRun, SARIFReport,
        ])

    def test_import_from_domain_value_objects(self):
        from src.domain.compliance.value_objects import (
            RiskTier, SystemType, ComplianceStatus, AnnexIVSection,
            SARIFLevel, SARIFResultKind,
        )
        assert all(v is not None for v in [
            RiskTier, SystemType, ComplianceStatus, AnnexIVSection,
            SARIFLevel, SARIFResultKind,
        ])

    def test_value_object_enums_are_str_enums(self):
        assert isinstance(RiskTier.HIGH_RISK, str)
        assert isinstance(SystemType.STANDALONE, str)
        assert isinstance(ComplianceStatus.COMPLIANT, str)
        assert isinstance(SARIFLevel.ERROR, str)
