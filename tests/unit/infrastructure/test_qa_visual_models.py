"""Unit tests for QA Visual domain models."""

import pytest
from pydantic import ValidationError

from src.infrastructure.qa_visual.models import (
    QAIssue,
    QAAnalysis,
    VisualRegression,
    Accessibility,
    LayoutInfo,
    AnalyzeResponse,
    TrendPoint,
    TrendAlert,
    Severity,
    IssueCategory,
)


class TestEnums:
    def test_severity_values(self):
        assert Severity.CRITICAL == "critical"
        assert Severity.HIGH == "high"
        assert Severity.MEDIUM == "medium"
        assert Severity.LOW == "low"
        assert Severity.INFO == "info"

    def test_issue_category_values(self):
        assert IssueCategory.CONTRAST == "contrast"
        assert IssueCategory.ALIGNMENT == "alignment"
        assert IssueCategory.OVERFLOW == "overflow"
        assert IssueCategory.MISSING == "missing"
        assert IssueCategory.TEXT == "text"
        assert IssueCategory.SPACING == "spacing"
        assert IssueCategory.OTHER == "other"


class TestQAAnalysis:
    """The structured JSON contract the vision model must return."""

    def test_full_analysis_from_model_output(self):
        analysis = QAAnalysis(
            page_title="SabaTech Dashboard",
            visible_texts=["Login", "Password", "Submit"],
            layout=LayoutInfo(
                description="Centered card layout",
                colors={"background": "#ffffff", "primary_accent": "#4f46e5", "text": "#111827"},
            ),
            qa_issues=[
                QAIssue(
                    severity=Severity.MEDIUM,
                    category=IssueCategory.CONTRAST,
                    description="Low contrast on footer link",
                    element="footer a",
                )
            ],
            accessibility=Accessibility(
                contrast_issues=["footer link 2.1:1"],
                missing_alt=False,
                missing_labels=[],
            ),
            visual_regression=VisualRegression(
                unexpected_whitespace=False,
                overlapping_elements=False,
                cut_off_content=False,
                misaligned=True,
            ),
            overall_score=95,
            summary="Solid page with one contrast issue.",
        )
        assert analysis.overall_score == 95
        assert analysis.page_title == "SabaTech Dashboard"
        assert len(analysis.qa_issues) == 1
        assert analysis.visual_regression.misaligned is True

    def test_score_bounds(self):
        with pytest.raises(ValidationError):
            QAAnalysis(overall_score=101)
        with pytest.raises(ValidationError):
            QAAnalysis(overall_score=-1)

    def test_minimal_analysis(self):
        analysis = QAAnalysis(overall_score=88, summary="ok")
        assert analysis.qa_issues == []
        assert analysis.visible_texts == []
        assert analysis.accessibility.missing_alt is False

    def test_layout_colors_optional(self):
        analysis = QAAnalysis(overall_score=50, summary="s")
        assert analysis.layout is None


class TestAnalyzeResponse:
    def test_response_passes_threshold(self):
        analysis = QAAnalysis(overall_score=95, summary="great")
        response = AnalyzeResponse(
            report_id="r1",
            target="amc",
            analysis=analysis,
            passed=True,
            score=95,
            threshold=80,
            cost_usd=0.000428,
            latency_s=4.37,
            model="deepseek-v4-flash-vision-exp",
            regression_detected=False,
        )
        assert response.passed is True
        assert response.score == 95

    def test_response_requires_report_id_and_target(self):
        analysis = QAAnalysis(overall_score=10, summary="bad")
        with pytest.raises(ValidationError):
            AnalyzeResponse(
                analysis=analysis,
                passed=False,
                score=10,
                threshold=80,
                cost_usd=0.0,
                latency_s=1.0,
                model="m",
                regression_detected=False,
            )


class TestTrendModels:
    def test_trend_point(self):
        point = TrendPoint(report_id="r1", target="amc", score=90, cost_usd=0.0005, passed=True)
        assert point.score == 90

    def test_trend_alert_degradation(self):
        alert = TrendAlert(
            type="degradation",
            target="amc",
            message="Score dropped 15 points vs previous run",
            current_score=70,
            previous_score=85,
        )
        assert alert.type == "degradation"
        assert alert.current_score == 70

    def test_trend_alert_requires_scores_for_degradation(self):
        with pytest.raises(ValidationError):
            TrendAlert(type="degradation", target="amc", message="dropped")
