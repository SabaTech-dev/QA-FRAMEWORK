"""
Annex IV Exporter — EU AI Act compliance evidence export.

Generates structured Annex IV technical documentation from QA-FRAMEWORK
test execution data and system metadata.
"""

import json
from typing import Optional, Dict, Any, List
from datetime import datetime

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
    QA_FRAMEWORK_DEFAULTS,
)


class AnnexIVExporter:
    """
    Exports Annex IV compliant technical documentation.

    Usage:
        exporter = AnnexIVExporter()
        doc = exporter.generate(test_results=[...], execution_stats={...})
        json_str = exporter.to_json(doc)
    """

    def __init__(self, defaults: Optional[dict] = None):
        """Initialize with optional custom defaults."""
        self.defaults = defaults or QA_FRAMEWORK_DEFAULTS

    def generate(
        self,
        system_name: Optional[str] = None,
        version: Optional[str] = None,
        test_results: Optional[List[dict]] = None,
        execution_stats: Optional[dict] = None,
        custom_overrides: Optional[Dict[str, Any]] = None,
    ) -> AnnexIVDocument:
        """
        Generate Annex IV document from system data.

        Args:
            system_name: Override system name
            version: Override version
            test_results: Test execution results for metrics
            execution_stats: Aggregated execution statistics
            custom_overrides: Override any section of the document

        Returns:
            AnnexIVDocument ready for JSON export
        """
        # Build from defaults
        config = dict(self.defaults)

        # Override system description if provided
        if system_name or version:
            desc = dict(config.get("system_description", {}))
            if system_name:
                desc["name"] = system_name
            if version:
                desc["version"] = version
            config["system_description"] = desc

        # Compute evaluation results from test data
        evaluation_results = self._compute_evaluation_results(
            test_results or [], execution_stats or {}
        )

        # Build document
        doc = AnnexIVDocument(
            system_description=SystemDescription(**config["system_description"]),
            capabilities=SystemCapabilities(**config["capabilities"]),
            data_training=DataTrainingSummary(**config["data_training"]),
            risk_assessment=RiskAssessment(**config["risk_assessment"]),
            evaluation_results=evaluation_results,
            human_oversight=HumanOversight(**config["human_oversight"]),
            transparency=TransparencyInfo(**config["transparency"]),
        )

        # Apply custom overrides
        if custom_overrides:
            doc = self._apply_overrides(doc, custom_overrides)

        return doc

    def to_json(self, doc: AnnexIVDocument, indent: int = 2) -> str:
        """Export document as JSON string."""
        return doc.model_dump_json(indent=indent)

    def to_dict(self, doc: AnnexIVDocument) -> dict:
        """Export document as dictionary."""
        return doc.model_dump()

    def _compute_evaluation_results(
        self,
        test_results: List[dict],
        execution_stats: dict,
    ) -> List[EvaluationResult]:
        """Compute evaluation metrics from test execution data."""
        results = []

        if execution_stats:
            # From aggregated stats
            total = execution_stats.get("total_executions", 0)
            passed = execution_stats.get("passed", 0)
            failed = execution_stats.get("failed", 0)
            if total > 0:
                pass_rate = (passed / total) * 100
                results.append(EvaluationResult(
                    metric_name="pass_rate",
                    metric_value=round(pass_rate, 2),
                    metric_description="Percentage of test executions that passed",
                ))
                results.append(EvaluationResult(
                    metric_name="total_executions",
                    metric_value=float(total),
                    metric_description="Total number of test executions",
                ))
                results.append(EvaluationResult(
                    metric_name="failure_rate",
                    metric_value=round((failed / total) * 100, 2),
                    metric_description="Percentage of test executions that failed",
                ))

        # From individual test results
        if test_results:
            ai_generated = [t for t in test_results if t.get("ai_generated", False)]
            if ai_generated:
                ai_passed = [t for t in ai_generated if t.get("status") == "passed"]
                ai_pass_rate = (len(ai_passed) / len(ai_generated)) * 100
                results.append(EvaluationResult(
                    metric_name="ai_test_pass_rate",
                    metric_value=round(ai_pass_rate, 2),
                    metric_description="Pass rate for AI-generated tests specifically",
                ))

        # Default metrics if no data
        if not results:
            results.append(EvaluationResult(
                metric_name="placeholder",
                metric_value=0.0,
                metric_description="No evaluation data available yet",
            ))

        return results

    def _apply_overrides(self, doc: AnnexIVDocument, overrides: Dict[str, Any]) -> AnnexIVDocument:
        """Apply custom overrides to document sections."""
        doc_dict = doc.model_dump()

        for key, value in overrides.items():
            if key in doc_dict and isinstance(doc_dict[key], dict) and isinstance(value, dict):
                doc_dict[key].update(value)
            else:
                doc_dict[key] = value

        return AnnexIVDocument(**doc_dict)


def export_annex_iv(
    system_name: Optional[str] = None,
    version: Optional[str] = None,
    test_results: Optional[List[dict]] = None,
    execution_stats: Optional[dict] = None,
) -> str:
    """
    Convenience function: generate and return Annex IV JSON.

    Args:
        system_name: System name override
        version: Version override
        test_results: Test execution results
        execution_stats: Aggregated execution statistics

    Returns:
        JSON string of Annex IV document
    """
    exporter = AnnexIVExporter()
    doc = exporter.generate(
        system_name=system_name,
        version=version,
        test_results=test_results,
        execution_stats=execution_stats,
    )
    return exporter.to_json(doc)
