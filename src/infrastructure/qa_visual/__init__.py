"""QA Visual module — vision-model screenshot analysis for the QA framework.

Validated in Fase A (score 95/100, $0.000428/screenshot, 4.37s latency,
0 hallucinations) and productized here per the GO-NOGO Fase B decision.

Quick start:
    from fastapi import FastAPI
    from src.infrastructure.qa_visual import create_qa_visual_router

    app = FastAPI()
    app.include_router(create_qa_visual_router())  # config from env

Spike conditions C1-C5 are enforced in config/gateway_client:
thinking disabled, max_tokens >= 4000 when thinking on, browser UA,
model id via env (QA_VISUAL_MODEL), pricing pinned 2026-08-22.
"""

from src.infrastructure.qa_visual.analyzer import (
    QAVisualAnalysisError,
    QAVisualAnalyzer,
    build_trend_report,
)
from src.infrastructure.qa_visual.config import QAVisualConfig
from src.infrastructure.qa_visual.endpoint import create_qa_visual_router
from src.infrastructure.qa_visual.gateway_client import (
    VisionGatewayClient,
    VisionGatewayError,
    VisionResult,
)
from src.infrastructure.qa_visual.models import (
    Accessibility,
    AnalyzeResponse,
    IssueCategory,
    LayoutInfo,
    QAIssue,
    QAAnalysis,
    Severity,
    TrendAlert,
    TrendPoint,
    VisualRegression,
)
from src.infrastructure.qa_visual.parser import ParseResult, parse_qa_analysis
from src.infrastructure.qa_visual.playwright_hook import QAVisualHook
from src.infrastructure.qa_visual.storage import QAVisualReportStore, new_report_id

__all__ = [
    "QAVisualConfig",
    "QAVisualAnalyzer",
    "QAVisualAnalysisError",
    "QAVisualReportStore",
    "QAVisualHook",
    "VisionGatewayClient",
    "VisionGatewayError",
    "VisionResult",
    "create_qa_visual_router",
    "build_trend_report",
    "parse_qa_analysis",
    "ParseResult",
    "new_report_id",
    "QAAnalysis",
    "QAIssue",
    "Accessibility",
    "LayoutInfo",
    "VisualRegression",
    "AnalyzeResponse",
    "TrendPoint",
    "TrendAlert",
    "Severity",
    "IssueCategory",
]
