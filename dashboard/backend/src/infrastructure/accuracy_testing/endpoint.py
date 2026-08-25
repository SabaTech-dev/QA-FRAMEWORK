"""FastAPI router for the accuracy_testing module (card c9825844 wiring).

Endpoints (prefix ``/accuracy``):
- GET  /benchmarks            — catalog, tenant-filtered to the eval set
- GET  /benchmarks/{id}       — detail; ``to_dict_full()`` for admins only (L-2)
- POST /sessions              — run an evaluation session (split + eval + holdout)
- GET  /sessions/{id}         — session view (eval-set detail + holdout aggregates)
- GET  /sessions/{id}/holdout — ``HoldoutSummary`` aggregates only

Security contracts:
- L-1: the split salt is derived server-side per tenant (HMAC of a platform
  secret); request bodies cannot carry a salt (``extra="forbid"``).
- L-2: ``to_dict_full()`` (ground_truth + tenant_id) is served to admins
  only; every resource is owner-scoped.
- AC2: responses serialise benchmarks via ``to_dict()`` and holdout results
  via ``HoldoutSummary`` — never ``split.holdout_benchmarks`` nor
  ``to_dict_full()`` for non-admins.

Example:
    from fastapi import FastAPI

    from src.infrastructure.accuracy_testing.endpoint import create_accuracy_router
    from src.infrastructure.accuracy_testing.security import AccuracyPrincipal

    app = FastAPI()
    app.include_router(
        create_accuracy_router(
            principal_dependency=lambda: AccuracyPrincipal(owner="t1"),
            split_secret=os.environ["ACCURACY_SPLIT_SECRET"],
        )
    )
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict

from src.domain.accuracy_testing.entities import AccuracyBenchmark, AccuracyTestSession
from src.domain.accuracy_testing.interfaces import IAccuracyEvaluator, IResponseProvider
from src.domain.accuracy_testing.splitting import BenchmarkSplit
from src.infrastructure.accuracy_testing.german_ai_liability_benchmarks import (
    create_german_ai_liability_benchmarks,
)
from src.infrastructure.accuracy_testing.llm_gateway_provider import LLMGatewayProviderError
from src.infrastructure.accuracy_testing.rule_based_evaluator import RuleBasedAccuracyEvaluator
from src.infrastructure.accuracy_testing.security import AccuracyPrincipal
from src.infrastructure.accuracy_testing.session_store import (
    AccuracySessionStore,
    run_accuracy_session,
    split_for_tenant,
)

logger = logging.getLogger(__name__)


class SessionCreateRequest(BaseModel):
    """Session creation payload.

    L-1: there is deliberately NO salt field — the split namespace is
    derived server-side from the authenticated tenant. ``extra="forbid"``
    rejects any client attempt to smuggle one (422).
    """

    model_config = ConfigDict(extra="forbid")

    ai_model: str = ""
    benchmark_ids: list[str] | None = None


def create_accuracy_router(
    principal_dependency: Callable[[], AccuracyPrincipal],
    benchmarks: Sequence[AccuracyBenchmark] | None = None,
    response_provider: IResponseProvider | None = None,
    split_secret: str = "",
    evaluator: IAccuracyEvaluator | None = None,
    holdout_ratio: float = 0.2,
    prefix: str = "/accuracy",
) -> APIRouter:
    """Build the accuracy API router.

    Args:
        principal_dependency: auth dependency returning an ``AccuracyPrincipal``
            (may raise 401 — standard FastAPI dependency semantics).
        benchmarks: benchmark catalog; defaults to the built-in German AI
            liability benchmarks.
        response_provider: server-side AI response source. Sessions cannot
            run without it (POST /sessions returns 503).
        split_secret: platform secret for per-tenant salt derivation.
            REQUIRED and fail-closed: an empty secret raises at mount time
            rather than collapsing tenants into a shared namespace (L-1).
        evaluator: evaluator implementation; defaults to the rule-based one.
        holdout_ratio: fraction of the catalog sealed as holdout per tenant.
        prefix: router prefix.
    """
    if not split_secret or not split_secret.strip():
        raise ValueError(
            "split_secret is required (ACCURACY_SPLIT_SECRET): an empty secret would "
            "collapse every tenant into a shared holdout namespace (L-1)"
        )

    catalog: list[AccuracyBenchmark] = (
        list(benchmarks) if benchmarks is not None else create_german_ai_liability_benchmarks()
    )
    evaluator = evaluator or RuleBasedAccuracyEvaluator()
    store = AccuracySessionStore()

    router = APIRouter(prefix=prefix, tags=["accuracy"])

    def _split(principal: AccuracyPrincipal) -> BenchmarkSplit:
        """Tenant-scoped split of the catalog (admins use their own namespace)."""
        return split_for_tenant(catalog, split_secret, principal.owner, holdout_ratio)

    def _visible_benchmark(
        benchmark_id: str, principal: AccuracyPrincipal
    ) -> AccuracyBenchmark | None:
        by_id = {b.id: b for b in catalog}
        if principal.is_admin:
            return by_id.get(benchmark_id)
        split = _split(principal)
        eval_ids = {b.id for b in split.eval_benchmarks}
        benchmark = by_id.get(benchmark_id)
        if benchmark is None or benchmark.id not in eval_ids:
            # 404 (not 403): holdout membership must not be confirmable.
            return None
        return benchmark

    @router.get("/benchmarks")
    def list_benchmarks(
        principal: AccuracyPrincipal = Depends(principal_dependency),
    ) -> list[dict]:
        if principal.is_admin:
            return [b.to_dict() for b in catalog]
        split = _split(principal)
        return [b.to_dict() for b in split.eval_benchmarks]

    @router.get("/benchmarks/{benchmark_id}")
    def get_benchmark(
        benchmark_id: str,
        principal: AccuracyPrincipal = Depends(principal_dependency),
    ) -> dict:
        benchmark = _visible_benchmark(benchmark_id, principal)
        if benchmark is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Benchmark not found")
        # L-2: full view (ground_truth + tenant_id) is admin-only.
        if principal.is_admin:
            return benchmark.to_dict_full()
        return benchmark.to_dict()

    @router.post("/sessions")
    def create_session(
        request: SessionCreateRequest,
        principal: AccuracyPrincipal = Depends(principal_dependency),
    ) -> dict:
        if response_provider is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No response provider configured for accuracy sessions",
            )

        split = _split(principal)
        selected: list[AccuracyBenchmark] = split.eval_benchmarks + split.holdout_benchmarks
        if request.benchmark_ids is not None:
            visible_ids = {b.id for b in split.eval_benchmarks}
            unknown = [bid for bid in request.benchmark_ids if bid not in visible_ids]
            if unknown:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Benchmark not found",
                )
            selected = [b for b in split.eval_benchmarks if b.id in set(request.benchmark_ids)]

        session_split = (
            split
            if request.benchmark_ids is None
            else _restrict_split(split, set(request.benchmark_ids))
        )

        try:
            session = run_accuracy_session(
                benchmarks=selected,
                split=session_split,
                evaluator=evaluator,
                response_provider=response_provider,
                ai_model=request.ai_model,
                tenant_id=principal.owner,
            )
        except LLMGatewayProviderError as exc:
            # CWE-209: generic detail only; the provider error (and the
            # upstream body it logged) never reaches the HTTP client.
            logger.error("Accuracy response provider failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Response provider unavailable; see server logs",
            ) from exc
        store.save(principal.owner, session, session_split)
        return _session_view(session, session_split)

    @router.get("/sessions/{session_id}")
    def get_session(
        session_id: str,
        principal: AccuracyPrincipal = Depends(principal_dependency),
    ) -> dict:
        record = store.get(session_id, principal)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        session, split = record
        return _session_view(session, split)

    @router.get("/sessions/{session_id}/holdout")
    def get_session_holdout(
        session_id: str,
        principal: AccuracyPrincipal = Depends(principal_dependency),
    ) -> dict:
        record = store.get(session_id, principal)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        session, _split_obj = record
        summary = session.holdout_summary
        if summary is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Holdout summary not available"
            )
        # AC2: HoldoutSummary aggregates only.
        return summary.to_dict()

    def _session_view(session: AccuracyTestSession, split: BenchmarkSplit) -> dict:
        """AC2: eval-set detail + aggregate holdout; split as counts only."""
        view: dict = session.to_dict()
        view["split"] = split.to_dict()
        return view

    def _restrict_split(split: BenchmarkSplit, keep_ids: set) -> BenchmarkSplit:
        """Re-split semantics for a benchmark subset: keep only selected eval items.

        A client-chosen subset must not shrink the sealed holdout (that would
        let a tenant drain the holdout set item by item via 404 probing), so
        the restriction keeps the ORIGINAL split membership untouched and
        only narrows the eval set that is evaluated in detail.
        """
        from dataclasses import replace as _replace

        selected_eval = [b for b in split.eval_benchmarks if b.id in keep_ids]
        return _replace(split, eval_benchmarks=selected_eval)

    return router
