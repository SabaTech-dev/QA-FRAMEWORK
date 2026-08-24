"""Orchestrates the QA Visual pipeline: gateway -> parse -> threshold -> store.

The analyzer owns two policy decisions from the GO-NOGO Fase B scope:
- Threshold: ``score < threshold`` marks the report as failed.
- Baseline regression: compares against the earliest report of the target;
  a drop of ``degradation_alert_points`` or any visual_regression flag marks
  the report as a regression.
"""

import logging
from typing import List, Optional, Tuple

from src.infrastructure.qa_visual.config import QAVisualConfig
from src.infrastructure.qa_visual.gateway_client import VisionGatewayClient, VisionGatewayError
from src.infrastructure.qa_visual.models import AnalyzeResponse, TrendAlert, TrendPoint
from src.infrastructure.qa_visual.parser import parse_qa_analysis
from src.infrastructure.qa_visual.storage import QAVisualReportStore, new_report_id

logger = logging.getLogger(__name__)


class QAVisualAnalysisError(Exception):
    """Raised when the analysis pipeline fails end to end."""

    def __init__(self, message: str, raw_content: Optional[str] = None):
        super().__init__(message)
        self.raw_content = raw_content


class QAVisualAnalyzer:
    """Runs one screenshot through the vision pipeline."""

    def __init__(
        self,
        config: Optional[QAVisualConfig] = None,
        gateway_client: Optional[VisionGatewayClient] = None,
        store: Optional[QAVisualReportStore] = None,
    ):
        self._config = config or QAVisualConfig.from_env()
        self._gateway = gateway_client or VisionGatewayClient(self._config)
        self._store = store or QAVisualReportStore(reports_dir=self._config.reports_dir)

    @property
    def store(self) -> QAVisualReportStore:
        return self._store

    @property
    def config(self) -> QAVisualConfig:
        return self._config

    async def analyze(self, image_bytes: bytes, target: str) -> AnalyzeResponse:
        """Analyze one screenshot and persist the report."""
        try:
            result = await self._gateway.analyze_image(image_bytes)
        except VisionGatewayError as exc:
            raise QAVisualAnalysisError(f"Vision gateway failed: {exc}") from exc

        parsed = parse_qa_analysis(result.content)
        if parsed.parse_error or parsed.analysis is None:
            raise QAVisualAnalysisError(
                "Model output could not be parsed into the QA contract",
                raw_content=result.content,
            )

        analysis = parsed.analysis
        baseline = self._store.get_baseline(target)
        regression_detected = self._detect_regression(analysis, baseline)

        response = AnalyzeResponse(
            report_id=new_report_id(),
            target=target,
            analysis=analysis,
            passed=analysis.overall_score >= self._config.score_threshold,
            score=analysis.overall_score,
            threshold=self._config.score_threshold,
            cost_usd=result.cost_usd,
            latency_s=result.latency_s,
            model=result.model_reported,
            regression_detected=regression_detected,
        )
        self._store.save(response)
        logger.info(
            "qa-visual analysis target=%s score=%s passed=%s regression=%s cost=%.6f",
            target,
            response.score,
            response.passed,
            response.regression_detected,
            response.cost_usd,
        )
        return response

    def _detect_regression(self, analysis, baseline_report: Optional[dict]) -> bool:
        """Regression = big score drop vs baseline OR regression flags."""
        if analysis.visual_regression.has_any():
            return True
        if not baseline_report:
            return False
        baseline_score = baseline_report.get("score")
        if not isinstance(baseline_score, (int, float)):
            return False
        drop = baseline_score - analysis.overall_score
        return drop >= self._config.degradation_alert_points

    async def close(self) -> None:
        await self._gateway.close()


def build_trend_report(
    store: QAVisualReportStore,
    target: Optional[str] = None,
    limit: int = 50,
    degradation_points: int = 10,
) -> Tuple[List[TrendPoint], List[TrendAlert]]:
    """Build score history and degradation alerts from stored reports.

    Points are returned newest first (mirroring store ordering); alerts are
    raised whenever consecutive scores drop by ``degradation_points`` or more.
    """
    reports = store.list_reports(target=target, limit=limit)
    points = [
        TrendPoint(
            report_id=r.get("report_id", ""),
            target=r.get("target", ""),
            timestamp=r.get("timestamp"),
            score=r.get("score", 0),
            cost_usd=r.get("cost_usd", 0.0),
            passed=r.get("passed"),
        )
        for r in reports
    ]

    alerts: List[TrendAlert] = []
    # reports are newest-first; walk chronologically to compare consecutive runs
    chronological = list(reversed(reports))
    for previous, current in zip(chronological, chronological[1:]):
        previous_score = previous.get("score")
        current_score = current.get("score")
        if not isinstance(previous_score, (int, float)) or not isinstance(
            current_score, (int, float)
        ):
            continue
        if current.get("regression_detected") or (
            previous_score - current_score >= degradation_points
        ):
            alerts.append(
                TrendAlert(
                    type="degradation",
                    target=current.get("target", ""),
                    message=(
                        f"Score dropped {int(previous_score - current_score)} points "
                        f"vs previous run ({int(previous_score)} -> {int(current_score)})"
                    ),
                    current_score=int(current_score),
                    previous_score=int(previous_score),
                )
            )
    return points, alerts
