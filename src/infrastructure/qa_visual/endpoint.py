"""FastAPI router for the QA Visual module (same pattern as health/endpoint.py).

Endpoints:
- POST /analyze          — upload a screenshot, get the full QA report
- GET  /reports          — list stored reports (filter by target, limit)
- GET  /reports/{id}     — one stored report
- GET  /trends           — score history + degradation alerts
- GET  /baselines/{t}    — baseline report for a target

Example:
    from fastapi import FastAPI
    from src.infrastructure.qa_visual import create_qa_visual_router

    app = FastAPI()
    app.include_router(create_qa_visual_router())
"""

import logging
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from src.infrastructure.qa_visual.analyzer import (
    QAVisualAnalysisError,
    QAVisualAnalyzer,
    build_trend_report,
)
from src.infrastructure.qa_visual.models import AnalyzeResponse

logger = logging.getLogger(__name__)

MAX_SCREENSHOT_BYTES = 10 * 1024 * 1024  # 10 MB safety cap


def create_qa_visual_router(
    analyzer: Optional[QAVisualAnalyzer] = None,
    prefix: str = "/api/v1/qa-visual",
) -> APIRouter:
    """Create the QA Visual API router.

    Args:
        analyzer: pre-configured analyzer (built from env when None)
        prefix: router prefix

    Returns:
        FastAPI router with the QA Visual endpoints.
    """
    router = APIRouter(prefix=prefix, tags=["qa-visual"])
    _analyzer = analyzer

    def get_analyzer() -> QAVisualAnalyzer:
        nonlocal _analyzer
        if _analyzer is None:
            _analyzer = QAVisualAnalyzer()  # config from env
        return _analyzer

    @router.post("/analyze", response_model=AnalyzeResponse)
    async def analyze_screenshot(
        screenshot: UploadFile = File(..., description="PNG screenshot to analyze"),
        target: str = Form(..., description="Target name (page/feature identifier)"),
    ) -> AnalyzeResponse:
        """Analyze one screenshot with the vision model and store the report."""
        image_bytes = await screenshot.read()
        if not image_bytes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Empty screenshot upload",
            )
        if len(image_bytes) > MAX_SCREENSHOT_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Screenshot exceeds {MAX_SCREENSHOT_BYTES // (1024 * 1024)} MB",
            )
        try:
            response = await get_analyzer().analyze(image_bytes, target=target)
        except QAVisualAnalysisError as exc:
            detail = str(exc)
            excerpt = (exc.raw_content or "")[:200]
            if excerpt:
                detail = f"{detail}. Raw output excerpt: {excerpt}"
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=detail) from exc
        return response

    @router.get("/reports")
    def list_reports(target: Optional[str] = None, limit: int = 50) -> list:
        """List stored QA Visual reports (newest first)."""
        return get_analyzer().store.list_reports(target=target, limit=limit)

    @router.get("/reports/{report_id}")
    def get_report(report_id: str) -> dict:
        """Return one stored report by id."""
        report = get_analyzer().store.get_report(report_id)
        if report is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report '{report_id}' not found",
            )
        return report

    @router.get("/trends")
    def get_trends(target: Optional[str] = None, limit: int = 50) -> dict:
        """Score history and degradation alerts (dashboard data source)."""
        analyzer = get_analyzer()
        points, alerts = build_trend_report(
            analyzer.store,
            target=target,
            limit=limit,
            degradation_points=analyzer.config.degradation_alert_points,
        )
        return {
            "points": [p.model_dump() for p in points],
            "alerts": [a.model_dump() for a in alerts],
        }

    @router.get("/baselines/{target}")
    def get_baseline(target: str) -> dict:
        """Return the baseline (earliest) report for a target."""
        baseline = get_analyzer().store.get_baseline(target)
        if baseline is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No baseline found for target '{target}'",
            )
        return baseline

    return router
