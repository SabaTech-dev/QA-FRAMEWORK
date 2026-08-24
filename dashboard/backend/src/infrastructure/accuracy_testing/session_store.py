"""Owner-scoped in-memory session store for the accuracy API.

Mirrors the storage scoping of the qa-visual owner-scoping pattern
(PR #118): every record carries its owner; retrieval is filtered by the
requesting principal (owners see their own records, admins see everything).

The store also runs evaluation sessions: eval-set items keep detailed
``AccuracyEvaluation`` results (the eval set is the legitimate development
surface), while holdout items go through ``HoldoutEvaluationService`` which
discards per-item results and keeps aggregates only (F-ACC-006 / AC2).
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional, Tuple

from src.domain.accuracy_testing.entities import AccuracyBenchmark, AccuracyTestSession
from src.domain.accuracy_testing.holdout_service import HoldoutEvaluationService
from src.domain.accuracy_testing.interfaces import IAccuracyEvaluator, IResponseProvider
from src.domain.accuracy_testing.splitting import BenchmarkSplit, HoldoutSummary, split_benchmarks
from src.domain.accuracy_testing.value_objects import EvaluationStatus
from src.infrastructure.accuracy_testing.security import AccuracyPrincipal


def run_accuracy_session(
    benchmarks: List[AccuracyBenchmark],
    split: BenchmarkSplit,
    evaluator: IAccuracyEvaluator,
    response_provider: IResponseProvider,
    ai_model: str,
    tenant_id: Optional[str],
) -> AccuracyTestSession:
    """Evaluate the eval subset in detail and the holdout in aggregates.

    AC2 contract: only ``split.eval_benchmarks`` produce serialized
    evaluations; holdout items flow exclusively through
    ``HoldoutEvaluationService`` and leave a ``HoldoutSummary``.
    """
    session = AccuracyTestSession(
        tenant_id=tenant_id,
        ai_model=ai_model,
        benchmarks=list(benchmarks),
        total_benchmarks=len(benchmarks),
        status=EvaluationStatus.RUNNING,
    )

    # Eval set: detailed evaluations (legitimate development surface).
    for benchmark in split.eval_benchmarks:
        response = response_provider.get_response(benchmark.question, ai_model)
        evaluation = evaluator.evaluate(benchmark, response, ai_model)
        session = session.add_evaluation(evaluation)

    # Holdout: aggregates only — per-item results discarded inside the service.
    holdout_summary: HoldoutSummary = HoldoutEvaluationService(evaluator).run_holdout(
        split, response_provider, ai_model
    )

    session = session.with_holdout_summary(holdout_summary)
    return session.complete()


class AccuracySessionStore:
    """Thread-safe, in-memory, owner-scoped session records."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: Dict[str, Tuple[str, AccuracyTestSession, BenchmarkSplit]] = {}

    def save(self, owner: str, session: AccuracyTestSession, split: BenchmarkSplit) -> None:
        with self._lock:
            self._records[session.id] = (owner, session, split)

    def get(
        self, session_id: str, principal: AccuracyPrincipal
    ) -> Optional[Tuple[AccuracyTestSession, BenchmarkSplit]]:
        """Owner-scoped retrieval: owners see their own, admins see all."""
        with self._lock:
            record = self._records.get(session_id)
        if record is None:
            return None
        owner, session, split = record
        if not principal.is_admin and owner != principal.owner:
            return None
        return session, split


def split_for_tenant(
    benchmarks: List[AccuracyBenchmark],
    split_secret: str,
    tenant_id: str,
    holdout_ratio: float = 0.2,
) -> BenchmarkSplit:
    """Split the catalog with the server-derived per-tenant salt (L-1)."""
    from src.domain.accuracy_testing.splitting import SplitPolicy
    from src.infrastructure.accuracy_testing.security import derive_tenant_salt

    policy = SplitPolicy(
        salt=derive_tenant_salt(split_secret, tenant_id),
        holdout_ratio=holdout_ratio,
    )
    return split_benchmarks(benchmarks, policy)
