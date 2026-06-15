"""
Tests for Bias/Fairness Testing Module

Covers:
- Value objects: enum coverage, validation, SubgroupMetric
- Entities: SubgroupAnalysis, FairnessReport, BiasTestSession
- Infrastructure: StatisticalFairnessAnalyzer
- SARIF integration: ComplianceSARIFExporter fairness
- Edge cases: empty data, single group, unicode
"""

import json
import pytest
from datetime import datetime, timezone

from src.domain.bias_fairness.value_objects import (
    FairnessMetric,
    Subgroup,
    BiasTestStatus,
    FairnessLevel,
    SubgroupMetric,
    validate_group_name,
    validate_metric_value,
    MAX_GROUP_NAME_LENGTH,
    MAX_SUBGROUPS,
)
from src.domain.bias_fairness.entities import (
    SubgroupAnalysis,
    FairnessReport,
    BiasTestSession,
)
from src.infrastructure.bias_fairness.fairness_analyzer import StatisticalFairnessAnalyzer
from src.infrastructure.compliance.compliance_sarif_exporter import ComplianceSARIFExporter
from src.domain.compliance.entities import SystemDescription, SARIFReport


# ========================================================================
# Value Objects
# ========================================================================

class TestFairnessMetric:
    def test_all_values(self):
        assert FairnessMetric.DEMOGRAPHIC_PARITY.value == "demographic_parity"
        assert FairnessMetric.EQUAL_OPPORTUNITY.value == "equal_opportunity"
        assert FairnessMetric.EQUALIZED_ODDS.value == "equalized_odds"
        assert FairnessMetric.PREDICTIVE_PARITY.value == "predictive_parity"
        assert FairnessMetric.DISPARATE_IMPACT.value == "disparate_impact"
        assert FairnessMetric.CALIBORATION.value == "calibration"

    def test_str_enum(self):
        assert isinstance(FairnessMetric.DEMOGRAPHIC_PARITY, str)


class TestSubgroup:
    def test_all_values(self):
        assert Subgroup.GENDER.value == "gender"
        assert Subgroup.AGE.value == "age"
        assert Subgroup.RACE_ETHNICITY.value == "race_ethnicity"

    def test_str_enum(self):
        assert isinstance(Subgroup.GENDER, str)


class TestBiasTestStatus:
    def test_all_values(self):
        assert BiasTestStatus.PENDING.value == "pending"
        assert BiasTestStatus.RUNNING.value == "running"
        assert BiasTestStatus.COMPLETED.value == "completed"
        assert BiasTestStatus.FAILED.value == "failed"
        assert BiasTestStatus.PARTIAL.value == "partial"


class TestFairnessLevel:
    def test_all_values(self):
        assert FairnessLevel.FAIR.value == "fair"
        assert FairnessLevel.MARGINAL.value == "marginal"
        assert FairnessLevel.BIASED.value == "biased"
        assert FairnessLevel.SEVERELY_BIASED.value == "severely_biased"


# ========================================================================
# Input Validation
# ========================================================================

class TestValidateGroupName:
    def test_valid_simple(self):
        assert validate_group_name("male") == "male"

    def test_valid_with_underscores(self):
        assert validate_group_name("age_18-25") == "age_18-25"

    def test_valid_with_spaces(self):
        assert validate_group_name("middle income") == "middle income"

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            validate_group_name("")

    def test_none_raises(self):
        with pytest.raises((ValueError, TypeError)):
            validate_group_name(None)

    def test_special_chars_rejected(self):
        with pytest.raises(ValueError, match="must start with alphanumeric"):
            validate_group_name("-invalid")

    def test_exceeds_max_length(self):
        with pytest.raises(ValueError, match="exceeds max length"):
            validate_group_name("a" * (MAX_GROUP_NAME_LENGTH + 1))

    def test_max_length_boundary(self):
        assert validate_group_name("a" * MAX_GROUP_NAME_LENGTH)


class TestValidateMetricValue:
    def test_valid_range(self):
        assert validate_metric_value(0.5) == 0.5
        assert validate_metric_value(0.0) == 0.0
        assert validate_metric_value(1.0) == 1.0

    def test_above_one_raises(self):
        with pytest.raises(ValueError, match="must be in"):
            validate_metric_value(1.5)

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="must be in"):
            validate_metric_value(-0.1)

    def test_nan_raises(self):
        with pytest.raises(ValueError, match="must not be NaN"):
            validate_metric_value(float('nan'))

    def test_inf_raises(self):
        with pytest.raises(ValueError, match="must not be infinite"):
            validate_metric_value(float('inf'))

    def test_string_raises(self):
        with pytest.raises(ValueError, match="must be a number"):
            validate_metric_value("abc")


class TestSubgroupMetric:
    def test_construction(self):
        m = SubgroupMetric(
            metric=FairnessMetric.DEMOGRAPHIC_PARITY,
            value=0.55,
            sample_size=100,
        )
        assert m.value == 0.55
        assert m.sample_size == 100

    def test_is_fair(self):
        m_fair = SubgroupMetric(metric=FairnessMetric.DEMOGRAPHIC_PARITY, value=0.5)
        m_biased = SubgroupMetric(metric=FairnessMetric.DEMOGRAPHIC_PARITY, value=0.8)
        assert m_fair.is_fair is True
        assert m_biased.is_fair is False

    def test_disparity_from_parity(self):
        m = SubgroupMetric(metric=FairnessMetric.DEMOGRAPHIC_PARITY, value=0.7)
        assert m.disparity_from_parity == pytest.approx(0.2)

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            SubgroupMetric(
                metric=FairnessMetric.DEMOGRAPHIC_PARITY,
                value=1.5,
            )

    def test_negative_sample_size_raises(self):
        with pytest.raises(ValueError, match="sample_size must be >= 0"):
            SubgroupMetric(
                metric=FairnessMetric.DEMOGRAPHIC_PARITY,
                value=0.5,
                sample_size=-1,
            )

    def test_to_dict(self):
        m = SubgroupMetric(
            metric=FairnessMetric.DEMOGRAPHIC_PARITY,
            value=0.6,
            sample_size=50,
        )
        d = m.to_dict()
        assert d["metric"] == "demographic_parity"
        assert d["sample_size"] == 50


# ========================================================================
# Entities
# ========================================================================

class TestSubgroupAnalysis:
    def test_construction(self):
        a = SubgroupAnalysis(
            subgroup_name="male",
            protected_attribute=Subgroup.GENDER,
            sample_size=500,
        )
        assert a.subgroup_name == "male"
        assert a.sample_size == 500
        assert a.bias_detected is False

    def test_compute_fairness_all_fair(self):
        a = SubgroupAnalysis(
            subgroup_name="test",
            metrics=[
                SubgroupMetric(metric=FairnessMetric.DEMOGRAPHIC_PARITY, value=0.5),
                SubgroupMetric(metric=FairnessMetric.EQUAL_OPPORTUNITY, value=0.52),
            ],
        )
        level = a.compute_fairness()
        assert level == FairnessLevel.FAIR
        assert a.bias_detected is False

    def test_compute_fairness_biased(self):
        a = SubgroupAnalysis(
            subgroup_name="test",
            metrics=[
                SubgroupMetric(metric=FairnessMetric.DEMOGRAPHIC_PARITY, value=0.85),
            ],
        )
        level = a.compute_fairness()
        assert level in (FairnessLevel.BIASED, FairnessLevel.SEVERELY_BIASED)
        assert a.bias_detected is True

    def test_compute_fairness_empty_metrics(self):
        a = SubgroupAnalysis(subgroup_name="empty")
        level = a.compute_fairness()
        assert level == FairnessLevel.FAIR

    def test_worst_metric(self):
        a = SubgroupAnalysis(
            metrics=[
                SubgroupMetric(metric=FairnessMetric.DEMOGRAPHIC_PARITY, value=0.5),
                SubgroupMetric(metric=FairnessMetric.EQUAL_OPPORTUNITY, value=0.9),
            ],
        )
        worst = a.worst_metric
        assert worst.metric == FairnessMetric.EQUAL_OPPORTUNITY

    def test_worst_metric_empty(self):
        a = SubgroupAnalysis()
        assert a.worst_metric is None

    def test_average_metric_value(self):
        a = SubgroupAnalysis(
            metrics=[
                SubgroupMetric(metric=FairnessMetric.DEMOGRAPHIC_PARITY, value=0.4),
                SubgroupMetric(metric=FairnessMetric.EQUAL_OPPORTUNITY, value=0.6),
            ],
        )
        assert a.average_metric_value == pytest.approx(0.5)

    def test_to_dict(self):
        a = SubgroupAnalysis(
            subgroup_name="female",
            protected_attribute=Subgroup.GENDER,
            sample_size=200,
        )
        d = a.to_dict()
        assert d["subgroup_name"] == "female"
        assert d["protected_attribute"] == "gender"
        assert d["sample_size"] == 200


class TestFairnessReport:
    def test_empty_report(self):
        r = FairnessReport()
        assert r.overall_fairness_level == FairnessLevel.FAIR
        assert r.subgroup_count == 0

    def test_add_subgroup(self):
        r = FairnessReport()
        a = SubgroupAnalysis(subgroup_name="test")
        r.add_subgroup_analysis(a)
        assert r.subgroup_count == 1

    def test_compute_overall_fair(self):
        r = FairnessReport()
        r.add_subgroup_analysis(SubgroupAnalysis(
            subgroup_name="g1",
            metrics=[SubgroupMetric(metric=FairnessMetric.DEMOGRAPHIC_PARITY, value=0.5)],
        ))
        r.add_subgroup_analysis(SubgroupAnalysis(
            subgroup_name="g2",
            metrics=[SubgroupMetric(metric=FairnessMetric.DEMOGRAPHIC_PARITY, value=0.52)],
        ))
        level = r.compute_overall_fairness()
        assert level == FairnessLevel.FAIR

    def test_compute_overall_biased(self):
        r = FairnessReport()
        r.add_subgroup_analysis(SubgroupAnalysis(
            subgroup_name="g1",
            metrics=[SubgroupMetric(metric=FairnessMetric.DEMOGRAPHIC_PARITY, value=0.5)],
        ))
        r.add_subgroup_analysis(SubgroupAnalysis(
            subgroup_name="g2",
            metrics=[SubgroupMetric(metric=FairnessMetric.DEMOGRAPHIC_PARITY, value=0.9)],
        ))
        level = r.compute_overall_fairness()
        assert level in (FairnessLevel.BIASED, FairnessLevel.SEVERELY_BIASED)
        assert r.bias_detected is True

    def test_worst_subgroup(self):
        r = FairnessReport()
        r.add_subgroup_analysis(SubgroupAnalysis(
            subgroup_name="g1",
            metrics=[SubgroupMetric(metric=FairnessMetric.DEMOGRAPHIC_PARITY, value=0.5)],
        ))
        r.add_subgroup_analysis(SubgroupAnalysis(
            subgroup_name="g2",
            metrics=[SubgroupMetric(metric=FairnessMetric.DEMOGRAPHIC_PARITY, value=0.9)],
        ))
        worst = r.worst_subgroup
        assert worst.subgroup_name == "g2"

    def test_worst_subgroup_empty(self):
        r = FairnessReport()
        assert r.worst_subgroup is None

    def test_to_dict(self):
        r = FairnessReport(system_id="sys-001")
        d = r.to_dict()
        assert d["system_id"] == "sys-001"
        assert "tenant_id" not in d

    def test_to_json(self):
        r = FairnessReport(system_id="sys-001")
        j = r.to_json()
        parsed = json.loads(j)
        assert parsed["system_id"] == "sys-001"

    def test_tenant_id_not_in_dict(self):
        r = FairnessReport(tenant_id="secret")
        d = r.to_dict()
        assert "tenant_id" not in d


class TestBiasTestSession:
    def test_construction(self):
        s = BiasTestSession(name="test session")
        assert s.name == "test session"
        assert s.status == "pending"

    def test_add_analysis(self):
        s = BiasTestSession()
        a = SubgroupAnalysis(subgroup_name="g1")
        s.add_analysis(a)
        assert s.analysis_count == 1

    def test_complete(self):
        s = BiasTestSession()
        s.complete()
        assert s.status == "completed"
        assert s.completed_at is not None

    def test_complete_with_error(self):
        s = BiasTestSession()
        s.complete(error="something broke")
        assert s.status == "failed"
        assert s.error_message == "something broke"

    def test_is_completed(self):
        s = BiasTestSession()
        assert s.is_completed is False
        s.complete()
        assert s.is_completed is True

    def test_total_samples(self):
        s = BiasTestSession()
        s.add_analysis(SubgroupAnalysis(sample_size=100))
        s.add_analysis(SubgroupAnalysis(sample_size=200))
        assert s.total_samples == 300

    def test_to_dict(self):
        s = BiasTestSession(name="test")
        d = s.to_dict()
        assert d["name"] == "test"
        assert "tenant_id" not in d


# ========================================================================
# Infrastructure: StatisticalFairnessAnalyzer
# ========================================================================

class TestStatisticalFairnessAnalyzer:
    def test_init(self):
        a = StatisticalFairnessAnalyzer()
        assert a.fairness_threshold == 0.1

    def test_init_custom_threshold(self):
        a = StatisticalFairnessAnalyzer(fairness_threshold=0.2)
        assert a.fairness_threshold == 0.2

    def test_init_invalid_threshold(self):
        with pytest.raises(ValueError, match="fairness_threshold"):
            StatisticalFairnessAnalyzer(fairness_threshold=1.5)

    def test_demographic_parity_balanced(self):
        a = StatisticalFairnessAnalyzer()
        preds = [True, True, False, False, True, True, False, False]
        groups = ["A", "A", "A", "A", "B", "B", "B", "B"]
        metrics = a.compute_demographic_parity(preds, groups)
        assert len(metrics) == 2
        for m in metrics:
            assert m.value == pytest.approx(0.5)

    def test_demographic_parity_biased(self):
        a = StatisticalFairnessAnalyzer()
        # Group A: all positive, Group B: all negative
        preds = [True, True, True, True, False, False, False, False]
        groups = ["A", "A", "A", "A", "B", "B", "B", "B"]
        metrics = a.compute_demographic_parity(preds, groups)
        assert len(metrics) == 2
        values = {m.value for m in metrics}
        assert 0.0 in values
        assert 1.0 in values

    def test_demographic_parity_length_mismatch(self):
        a = StatisticalFairnessAnalyzer()
        with pytest.raises(ValueError, match="same length"):
            a.compute_demographic_parity([True], ["A", "B"])

    def test_demographic_parity_empty(self):
        a = StatisticalFairnessAnalyzer()
        metrics = a.compute_demographic_parity([], [])
        assert metrics == []

    def test_equal_opportunity(self):
        a = StatisticalFairnessAnalyzer()
        preds = [True, True, False, True, True, False]
        labels = [True, True, True, True, False, False]
        groups = ["A", "A", "A", "B", "B", "B"]
        metrics = a.compute_equal_opportunity(preds, labels, groups)
        assert len(metrics) == 2
        for m in metrics:
            assert 0.0 <= m.value <= 1.0

    def test_equalized_odds(self):
        a = StatisticalFairnessAnalyzer()
        preds = [True, True, False, True, True, False]
        labels = [True, True, True, True, False, False]
        groups = ["A", "A", "A", "B", "B", "B"]
        metrics = a.compute_equalized_odds(preds, labels, groups)
        assert len(metrics) == 2

    def test_disparate_impact(self):
        a = StatisticalFairnessAnalyzer()
        preds = [True, True, True, True, False, False, False, False]
        groups = ["A", "A", "A", "A", "B", "B", "B", "B"]
        metrics = a.compute_disparate_impact(preds, groups)
        assert len(metrics) == 2
        # One group should have ratio 1.0 (reference)
        values = [m.value for m in metrics]
        assert 1.0 in values

    def test_per_subgroup_accuracy(self):
        a = StatisticalFairnessAnalyzer()
        preds = [True, True, False, False]
        labels = [True, True, False, False]
        groups = ["A", "A", "B", "B"]
        metrics = a.compute_per_subgroup_accuracy(preds, labels, groups)
        assert len(metrics) == 2
        for m in metrics:
            assert m.value == pytest.approx(1.0)  # perfect accuracy

    def test_analyze_session(self):
        a = StatisticalFairnessAnalyzer()
        preds = [True, True, False, False, True, True, False, False]
        labels = [True, True, False, False, True, False, False, True]
        groups = ["A", "A", "A", "A", "B", "B", "B", "B"]
        report = a.analyze_session(
            preds, labels, groups,
            protected_attribute=Subgroup.GENDER,
            system_id="test-sys",
        )
        assert report.system_id == "test-sys"
        assert report.subgroup_count == 2
        assert report.total_samples == 8

    def test_create_session(self):
        a = StatisticalFairnessAnalyzer()
        preds = [True, True, False, False]
        labels = [True, True, False, False]
        groups = ["A", "A", "B", "B"]
        session = a.create_session(
            preds, labels, groups,
            protected_attribute=Subgroup.GENDER,
            name="test",
        )
        assert session.status == "completed"
        assert session.analysis_count == 2

    def test_create_session_error(self):
        a = StatisticalFairnessAnalyzer()
        # Mismatched lengths should trigger error
        session = a.create_session(
            [True], [True, False], ["A", "B"],
            protected_attribute=Subgroup.GENDER,
        )
        assert session.status == "failed"

    def test_wilson_ci_balanced(self):
        lower, upper = StatisticalFairnessAnalyzer._wilson_ci(50, 100)
        assert lower < 0.5 < upper
        assert 0.0 <= lower <= upper <= 1.0

    def test_wilson_ci_zero_trials(self):
        lower, upper = StatisticalFairnessAnalyzer._wilson_ci(0, 0)
        assert lower == 0.0
        assert upper == 1.0


# ========================================================================
# SARIF Integration
# ========================================================================

class TestComplianceSARIFFairness:
    def _make_fair_report(self):
        """Create a fairness report with fair subgroups."""
        report = FairnessReport(system_id="test-sys")
        report.add_subgroup_analysis(SubgroupAnalysis(
            subgroup_name="male",
            protected_attribute=Subgroup.GENDER,
            sample_size=500,
            metrics=[
                SubgroupMetric(metric=FairnessMetric.DEMOGRAPHIC_PARITY, value=0.52),
                SubgroupMetric(metric=FairnessMetric.EQUAL_OPPORTUNITY, value=0.48),
            ],
        ))
        report.add_subgroup_analysis(SubgroupAnalysis(
            subgroup_name="female",
            protected_attribute=Subgroup.GENDER,
            sample_size=480,
            metrics=[
                SubgroupMetric(metric=FairnessMetric.DEMOGRAPHIC_PARITY, value=0.48),
                SubgroupMetric(metric=FairnessMetric.EQUAL_OPPORTUNITY, value=0.52),
            ],
        ))
        report.compute_overall_fairness()
        return report

    def _make_biased_report(self):
        """Create a fairness report with biased subgroups."""
        report = FairnessReport(system_id="test-sys")
        report.add_subgroup_analysis(SubgroupAnalysis(
            subgroup_name="majority",
            metrics=[
                SubgroupMetric(metric=FairnessMetric.DEMOGRAPHIC_PARITY, value=0.85),
            ],
        ))
        report.add_subgroup_analysis(SubgroupAnalysis(
            subgroup_name="minority",
            metrics=[
                SubgroupMetric(metric=FairnessMetric.DEMOGRAPHIC_PARITY, value=0.2),
            ],
        ))
        report.compute_overall_fairness()
        return report

    def test_export_returns_report(self):
        exporter = ComplianceSARIFExporter()
        report = exporter.export_fairness(self._make_fair_report())
        assert isinstance(report, SARIFReport)

    def test_version_2_1_0(self):
        exporter = ComplianceSARIFExporter()
        report = exporter.export_fairness(self._make_fair_report())
        assert report.version == "2.1.0"

    def test_has_one_run(self):
        exporter = ComplianceSARIFExporter()
        report = exporter.export_fairness(self._make_fair_report())
        assert len(report.runs) == 1

    def test_fair_report_passing(self):
        exporter = ComplianceSARIFExporter()
        report = exporter.export_fairness(self._make_fair_report())
        run = report.runs[0]
        # Should have overall pass
        overall = [r for r in run.results if r["ruleId"] == "QA-FAIR-OVERALL"]
        assert len(overall) == 1
        assert overall[0]["kind"] == "pass"

    def test_biased_report_failing(self):
        exporter = ComplianceSARIFExporter()
        report = exporter.export_fairness(self._make_biased_report())
        run = report.runs[0]
        overall = [r for r in run.results if r["ruleId"] == "QA-FAIR-OVERALL"]
        assert len(overall) == 1
        assert overall[0]["kind"] == "fail"

    def test_has_taxonomy(self):
        exporter = ComplianceSARIFExporter()
        report = exporter.export_fairness(self._make_fair_report())
        run = report.runs[0]
        assert len(run.taxonomy) >= 6  # 5 metrics + overall + subgroup

    def test_has_invocation(self):
        exporter = ComplianceSARIFExporter()
        report = exporter.export_fairness(self._make_fair_report())
        run = report.runs[0]
        assert len(run.invocations) >= 1

    def test_to_json_valid(self):
        exporter = ComplianceSARIFExporter()
        report = exporter.export_fairness(self._make_fair_report())
        j = report.to_json()
        parsed = json.loads(j)
        assert parsed["version"] == "2.1.0"

    def test_with_system_description(self):
        exporter = ComplianceSARIFExporter()
        sys = SystemDescription(system_id="ai-001", provider_name="Corp")
        report = exporter.export_fairness(self._make_fair_report(), sys)
        run = report.runs[0]
        # Check system in locations
        for r in run.results[:1]:
            if "locations" in r:
                locs = r["locations"][0].get("logicalLocations", [])
                system_locs = [l for l in locs if l.get("kind") == "aiSystem"]
                assert len(system_locs) >= 1

    def test_subgroup_results_exist(self):
        exporter = ComplianceSARIFExporter()
        report = exporter.export_fairness(self._make_fair_report())
        run = report.runs[0]
        subgroup_results = [r for r in run.results if r["ruleId"] == "QA-FAIR-SUBGROUP"]
        assert len(subgroup_results) == 2
