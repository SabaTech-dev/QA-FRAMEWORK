"""
Tests for Annex IV Exporter.

Covers:
- Document generation with defaults
- Custom overrides
- Evaluation metrics computation from test data
- JSON/dict export
- Schema validation
"""

import pytest
import json
from datetime import datetime

from domain.compliance.annex_iv_exporter import (
    AnnexIVExporter,
    export_annex_iv,
)
from infrastructure.compliance.annex_iv_requirements import (
    AnnexIVDocument,
    SystemDescription,
    SystemCapabilities,
    DataTrainingSummary,
    RiskAssessment,
    EvaluationResult,
    HumanOversight,
    TransparencyInfo,
    RiskLevel,
)


class TestAnnexIVExporter:
    """Tests for AnnexIVExporter class."""

    def test_generate_with_defaults(self):
        """Generate document using QA-FRAMEWORK defaults."""
        exporter = AnnexIVExporter()
        doc = exporter.generate()

        assert isinstance(doc, AnnexIVDocument)
        assert doc.system_description.name == "QA-FRAMEWORK"
        assert doc.schema_version == "1.0.0"
        assert len(doc.system_description.intended_users) > 0

    def test_generate_with_custom_name_version(self):
        """Override system name and version."""
        exporter = AnnexIVExporter()
        doc = exporter.generate(system_name="Custom QA", version="2.0.0")

        assert doc.system_description.name == "Custom QA"
        assert doc.system_description.version == "2.0.0"

    def test_to_json_output_is_valid_json(self):
        """JSON output is valid JSON string."""
        exporter = AnnexIVExporter()
        doc = exporter.generate()
        json_str = exporter.to_json(doc)

        parsed = json.loads(json_str)
        assert parsed["system_description"]["name"] == "QA-FRAMEWORK"
        assert "generated_at" in parsed

    def test_to_dict_returns_dict(self):
        """Dict output is a dictionary."""
        exporter = AnnexIVExporter()
        doc = exporter.generate()
        d = exporter.to_dict(doc)

        assert isinstance(d, dict)
        assert d["system_description"]["name"] == "QA-FRAMEWORK"

    def test_evaluation_results_from_stats(self):
        """Compute evaluation metrics from aggregated stats."""
        exporter = AnnexIVExporter()
        doc = exporter.generate(
            execution_stats={
                "total_executions": 100,
                "passed": 85,
                "failed": 15,
            }
        )

        assert len(doc.evaluation_results) == 3
        pass_rate = [r for r in doc.evaluation_results if r.metric_name == "pass_rate"]
        assert len(pass_rate) == 1
        assert pass_rate[0].metric_value == 85.0

    def test_evaluation_results_from_test_data(self):
        """Compute AI test pass rate from individual results."""
        exporter = AnnexIVExporter()
        test_results = [
            {"status": "passed", "ai_generated": True},
            {"status": "passed", "ai_generated": True},
            {"status": "failed", "ai_generated": True},
            {"status": "passed", "ai_generated": False},
        ]
        doc = exporter.generate(test_results=test_results)

        ai_metric = [r for r in doc.evaluation_results if r.metric_name == "ai_test_pass_rate"]
        assert len(ai_metric) == 1
        assert ai_metric[0].metric_value == pytest.approx(66.67, abs=0.1)

    def test_evaluation_results_empty_data(self):
        """Empty test data returns placeholder metric."""
        exporter = AnnexIVExporter()
        doc = exporter.generate()

        assert len(doc.evaluation_results) == 1
        assert doc.evaluation_results[0].metric_name == "placeholder"

    def test_custom_overrides(self):
        """Custom overrides merge into document."""
        exporter = AnnexIVExporter()
        doc = exporter.generate(
            custom_overrides={
                "system_description": {"name": "Overridden Name"},
            }
        )

        assert doc.system_description.name == "Overridden Name"

    def test_convenience_function(self):
        """export_annex_iv convenience function returns JSON string."""
        json_str = export_annex_iv(system_name="Test System")

        parsed = json.loads(json_str)
        assert parsed["system_description"]["name"] == "Test System"


class TestAnnexIVSchema:
    """Tests for Annex IV schema models."""

    def test_system_description_required_fields(self):
        """SystemDescription requires name, version, purpose, deployment_context."""
        with pytest.raises(Exception):
            SystemDescription()

    def test_system_description_valid(self):
        """Valid SystemDescription construction."""
        desc = SystemDescription(
            name="Test",
            version="1.0",
            purpose="Testing",
            deployment_context="CI/CD",
        )
        assert desc.interaction_mode == "api"  # default

    def test_risk_level_enum(self):
        """RiskLevel enum values."""
        assert RiskLevel.minimal.value == "minimal"
        assert RiskLevel.high.value == "high"

    def test_risk_assessment_defaults(self):
        """RiskAssessment has sensible defaults."""
        ra = RiskAssessment()
        assert ra.residual_risk_level == RiskLevel.minimal
        assert ra.identified_risks == []

    def test_evaluation_result(self):
        """EvaluationResult construction."""
        er = EvaluationResult(
            metric_name="accuracy",
            metric_value=0.95,
            metric_description="Model accuracy",
        )
        assert er.metric_value == 0.95

    def test_annex_iv_document_serialization(self):
        """Full document can be serialized to dict."""
        doc = AnnexIVDocument(
            system_description=SystemDescription(
                name="Test", version="1.0", purpose="Test", deployment_context="Test"
            ),
            capabilities=SystemCapabilities(),
            data_training=DataTrainingSummary(),
            risk_assessment=RiskAssessment(),
            human_oversight=HumanOversight(),
            transparency=TransparencyInfo(),
        )
        d = doc.model_dump()
        assert "generated_at" in d
        assert d["schema_version"] == "1.0.0"

    def test_annex_iv_document_json_roundtrip(self):
        """Document survives JSON roundtrip."""
        doc = AnnexIVDocument(
            system_description=SystemDescription(
                name="Roundtrip", version="1.0", purpose="Test", deployment_context="Test"
            ),
            capabilities=SystemCapabilities(),
            data_training=DataTrainingSummary(),
            risk_assessment=RiskAssessment(),
            human_oversight=HumanOversight(),
            transparency=TransparencyInfo(),
        )
        json_str = doc.model_dump_json()
        restored = AnnexIVDocument.model_validate_json(json_str)
        assert restored.system_description.name == "Roundtrip"
