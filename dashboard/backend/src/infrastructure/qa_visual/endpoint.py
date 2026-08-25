"""FastAPI router for the QA Visual module (same pattern as health/endpoint.py).

Endpoints:
- POST /analyze          — upload a screenshot, get the full QA report
- GET  /reports          — list stored reports (filter by target, limit)
- GET  /reports/{id}     — one stored report (owner or admin only)
- GET  /trends           — score history + degradation alerts
- GET  /baselines/{t}    — baseline report for a target

Owner scoping (S-1R): pass a ``get_current_principal`` dependency
returning a QAVisualPrincipal (owner + is_admin) and every endpoint
scopes reports to that owner; admins see everything. Without it the
router keeps its legacy unscoped behaviour for standalone mounts.

Example:
    from fastapi import FastAPI
    from src.infrastructure.qa_visual import create_qa_visual_router

    app = FastAPI()
    app.include_router(create_qa_visual_router())
"""

import logging
from collections.abc import Callable, Sequence
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status

from src.infrastructure.qa_visual.analyzer import (
    QAVisualAnalysisError,
    QAVisualAnalyzer,
    build_trend_report,
)
from src.infrastructure.qa_visual.models import AnalyzeResponse, QAVisualPrincipal
from src.infrastructure.qa_visual.storage import ReportAccessDenied

logger = logging.getLogger(__name__)

MAX_SCREENSHOT_BYTES = 10 * 1024 * 1024  # 10 MB safety cap
# Headroom for multipart boundaries and form fields when pre-checking
# Content-Length, so a legitimate 10 MB image is never rejected early.
MULTIPART_OVERHEAD_ALLOWANCE = 64 * 1024
PNG_MAGIC_BYTES = b"\x89PNG\r\n\x1a\n"
CHUNK_SIZE = 64 * 1024


def _no_principal() -> None:
    """Default principal dependency: no owner scoping (standalone mounts)."""
    return


def _owner_scope(principal: QAVisualPrincipal | None) -> str | None:
    """Owner a non-admin principal is scoped to; None sees everything."""
    if principal is None or principal.is_admin:
        return None
    # JWT edge (b): a blank identity must never become a report scope.
    if not principal.owner or not principal.owner.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Principal owner must be a non-empty string",
        )
    return principal.owner


def _stamp_owner(principal: QAVisualPrincipal | None) -> str | None:
    """Owner stamped on newly created reports (analyze).

    Admins without a usable identity produce unowned reports (admin-only
    reads) instead of reports scoped to a blank owner.
    """
    if principal is None:
        return None
    if not principal.owner or not principal.owner.strip():
        if principal.is_admin:
            return None
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Principal owner must be a non-empty string",
        )
    return principal.owner


async def _read_capped(upload: UploadFile) -> bytes:
    """Read the upload in chunks, aborting as soon as the size cap is exceeded.

    Never loads an oversized file fully into memory (S-2b).
    """
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_SCREENSHOT_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Screenshot exceeds {MAX_SCREENSHOT_BYTES // (1024 * 1024)} MB",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def create_qa_visual_router(
    analyzer: QAVisualAnalyzer | None = None,
    prefix: str = "/api/v1/qa-visual",
    dependencies: Sequence[Any] | None = None,
    get_current_principal: Callable[..., Any] | None = None,
) -> APIRouter:
    """Create the QA Visual API router.

    Args:
        analyzer: pre-configured analyzer (built from env when None)
        prefix: router prefix
        dependencies: router-level FastAPI dependencies (e.g. auth).
            Applied to every endpoint; empty by default so the module
            stays decoupled from any concrete auth service.
        get_current_principal: dependency returning a QAVisualPrincipal
            (owner + is_admin) used for owner scoping (S-1R). When None
            the router keeps its legacy unscoped behaviour for
            standalone mounts.

    Returns:
        FastAPI router with the QA Visual endpoints.
    """
    router = APIRouter(
        prefix=prefix,
        tags=["qa-visual"],
        dependencies=list(dependencies) if dependencies else [],
    )
    _analyzer = analyzer
    principal_dependency = get_current_principal or _no_principal

    def get_analyzer() -> QAVisualAnalyzer:
        nonlocal _analyzer
        if _analyzer is None:
            _analyzer = QAVisualAnalyzer()  # config from env
        return _analyzer

    @router.post("/analyze", response_model=AnalyzeResponse)
    async def analyze_screenshot(
        request: Request,
        screenshot: UploadFile = File(..., description="PNG screenshot to analyze"),
        # S-5R: storage derives the filename as target + 29 bytes of suffix;
        # 200 + 29 = 229 stays under the 255-byte filesystem name cap. A 255
        # limit here would let targets of 227-255 chars pass the Form and
        # then fail with OSError Errno 36 when the report is saved.
        target: str = Form(
            ..., max_length=200, description="Target name (page/feature identifier)"
        ),
        principal: QAVisualPrincipal | None = Depends(principal_dependency),
    ) -> AnalyzeResponse:
        """Analyze one screenshot with the vision model and store the report."""
        # S-2a: reject oversized uploads before reading the body.
        content_length = request.headers.get("content-length", "")
        if content_length.isdigit() and int(content_length) > (
            MAX_SCREENSHOT_BYTES + MULTIPART_OVERHEAD_ALLOWANCE
        ):
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Screenshot exceeds {MAX_SCREENSHOT_BYTES // (1024 * 1024)} MB",
            )
        # S-2c: only PNG screenshots are accepted (no paid API calls on junk).
        if screenshot.content_type != "image/png":
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Screenshot must be image/png",
            )
        image_bytes = await _read_capped(screenshot)
        if not image_bytes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Empty screenshot upload",
            )
        if not image_bytes.startswith(PNG_MAGIC_BYTES):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Screenshot is not a valid PNG",
            )
        try:
            response = await get_analyzer().analyze(
                image_bytes,
                target=target,
                owner=_stamp_owner(principal),
            )
        except QAVisualAnalysisError as exc:
            # S-3 (CWE-209): full detail goes to server logs only; the HTTP
            # client gets a generic message.
            excerpt = (exc.raw_content or "")[:200]
            logger.error(
                "QA Visual analysis failed (target=%s): %s%s",
                target,
                exc,
                f" | raw output excerpt: {excerpt}" if excerpt else "",
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Vision gateway error; see server logs",
            ) from exc
        return response

    @router.get("/reports")
    def list_reports(
        target: str | None = None,
        limit: int = 50,
        principal: QAVisualPrincipal | None = Depends(principal_dependency),
    ) -> list:
        """List stored QA Visual reports (newest first).

        Scoped to the caller's reports unless the principal is an admin.
        """
        return get_analyzer().store.list_reports(
            target=target,
            limit=limit,
            owner=_owner_scope(principal),
        )

    @router.get("/reports/{report_id}")
    def get_report(
        report_id: str,
        principal: QAVisualPrincipal | None = Depends(principal_dependency),
    ) -> dict:
        """Return one stored report by id (owner or admin only)."""
        try:
            report = get_analyzer().store.get_report(
                report_id,
                owner=_owner_scope(principal),
                # Standalone mounts (no principal) keep their documented
                # legacy unscoped behaviour: an explicit privileged read.
                is_admin=principal is None or principal.is_admin,
            )
        except ReportAccessDenied:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not allowed to access this report",
            )
        if report is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report '{report_id}' not found",
            )
        return report

    @router.get("/trends")
    def get_trends(
        target: str | None = None,
        limit: int = 50,
        principal: QAVisualPrincipal | None = Depends(principal_dependency),
    ) -> dict:
        """Score history and degradation alerts (dashboard data source).

        Points and alerts are scoped to the caller's reports unless the
        principal is an admin.
        """
        analyzer = get_analyzer()
        points, alerts = build_trend_report(
            analyzer.store,
            target=target,
            limit=limit,
            degradation_points=analyzer.config.degradation_alert_points,
            owner=_owner_scope(principal),
        )
        return {
            "points": [p.model_dump() for p in points],
            "alerts": [a.model_dump() for a in alerts],
        }

    @router.get("/baselines/{target}")
    def get_baseline(
        target: str,
        principal: QAVisualPrincipal | None = Depends(principal_dependency),
    ) -> dict:
        """Return the baseline (earliest) report for a target.

        The baseline is scoped to the caller's reports for that target
        unless the principal is an admin.
        """
        baseline = get_analyzer().store.get_baseline(target, owner=_owner_scope(principal))
        if baseline is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No baseline found for target '{target}'",
            )
        return baseline

    return router
