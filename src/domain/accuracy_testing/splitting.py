"""
Benchmark Splitting for AI Accuracy Testing (F-ACC-006)

Deterministic eval-set / holdout-set split with anti-overfitting guarantees.

Motivation (card ca3090d5): observable benchmarks can be gamed — an agent or
team can iterate against the eval set until memorizing it (Dan Luu: agent
overfit the benchmark up to the holdout; HF study: 6/11 ASR models memorize
public test sets). This module keeps holdout CONTENT (questions, ground truth,
per-item results) out of every serialized output: only aggregate counts and
metrics ever leave the domain.

Guarantees:
1. Determinism: the split is a pure function of (benchmark ids, policy).
   SHA-256 is used instead of Python's builtin hash(), which is salted per
   process and would not be reproducible across runs.
2. Redaction: BenchmarkSplit.to_dict()/__repr__ expose counts only.
3. Aggregation: HoldoutSummary carries aggregate metrics only — no ids,
   questions, responses, or per-item scores.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from .value_objects import AccuracyLevel, validate_threshold

if TYPE_CHECKING:  # pragma: no cover - import for type hints only
    from .entities import AccuracyBenchmark


# ========================================================================
# Split Policy
# ========================================================================


@dataclass(frozen=True)
class SplitPolicy:
    """
    Configuration for the eval/holdout split.

    Attributes:
        salt: REQUIRED namespace making splits distinct per tenant/deployment.
            Knowing the salt reveals WHICH items are holdout, never their
            content or per-item feedback — hence it must never be empty,
            shared, or client-chosen.
        holdout_ratio: target fraction of benchmarks assigned to the holdout
            set, in the open interval (0.0, 1.0).
        min_eval_size: minimum number of eval benchmarks (>= 1).
        min_holdout_size: minimum number of holdout benchmarks (>= 1).
    """

    salt: str
    holdout_ratio: float = 0.2
    min_eval_size: int = 1
    min_holdout_size: int = 1

    def __post_init__(self):
        # L-1 (card c9825844): a shared or empty salt collapses every tenant
        # into one namespace — knowing it reveals holdout membership. The
        # salt is therefore REQUIRED and must be non-empty; per-tenant salts
        # are derived server-side (see infrastructure.accuracy_testing.security).
        if not isinstance(self.salt, str) or not self.salt.strip():
            raise ValueError(
                "salt must be a non-empty per-tenant value: derive it server-side "
                "(e.g. HMAC(secret, tenant_id)) instead of relying on a shared default"
            )
        if not 0.0 < self.holdout_ratio < 1.0:
            raise ValueError(f"holdout_ratio must be in (0.0, 1.0), got {self.holdout_ratio}")
        if self.min_eval_size < 1:
            raise ValueError(f"min_eval_size must be >= 1, got {self.min_eval_size}")
        if self.min_holdout_size < 1:
            raise ValueError(f"min_holdout_size must be >= 1, got {self.min_holdout_size}")


# ========================================================================
# Split
# ========================================================================


@dataclass
class BenchmarkSplit:
    """
    Result of splitting a benchmark set into eval and holdout subsets.

    F-ACC-006 redaction: serialization and __repr__ expose COUNTS ONLY.
    Holdout questions, ground truth, ids, and per-item results must never
    appear in UI payloads or execution logs.
    """

    eval_benchmarks: list[AccuracyBenchmark] = field(default_factory=list)
    holdout_benchmarks: list[AccuracyBenchmark] = field(default_factory=list)
    # L-1: no secure default policy exists — required, keyword-only.
    policy: SplitPolicy = field(kw_only=True)

    def __post_init__(self):
        eval_ids = [b.id for b in self.eval_benchmarks]
        holdout_ids = [b.id for b in self.holdout_benchmarks]

        if len(set(eval_ids)) != len(eval_ids):
            raise ValueError("Duplicate benchmark ids in eval set")
        if len(set(holdout_ids)) != len(holdout_ids):
            raise ValueError("Duplicate benchmark ids in holdout set")
        if set(eval_ids) & set(holdout_ids):
            raise ValueError("Eval and holdout sets must be disjoint")

        # Size constraints apply only to non-degenerate splits. An empty
        # holdout is allowed (e.g. fewer than 2 benchmarks: nothing to hide).
        if holdout_ids:
            if len(holdout_ids) < self.policy.min_holdout_size:
                raise ValueError(
                    f"Holdout size {len(holdout_ids)} below policy minimum "
                    f"{self.policy.min_holdout_size}"
                )
            if len(eval_ids) < self.policy.min_eval_size:
                raise ValueError(
                    f"Eval size {len(eval_ids)} below policy minimum {self.policy.min_eval_size}"
                )

    @property
    def eval_count(self) -> int:
        return len(self.eval_benchmarks)

    @property
    def holdout_count(self) -> int:
        return len(self.holdout_benchmarks)

    def to_dict(self) -> dict:
        """Serialize redacted view: counts only, never content (F-ACC-006).

        The salt is intentionally excluded — exposing it would help
        reconstruct which items belong to the holdout set.
        """
        return {
            "eval_count": self.eval_count,
            "holdout_count": self.holdout_count,
            "holdout_ratio": self.policy.holdout_ratio,
        }

    def __repr__(self) -> str:
        """Redacted repr: counts only, safe for accidental logging."""
        return f"BenchmarkSplit(eval_count={self.eval_count}, holdout_count={self.holdout_count})"


def _sort_key(benchmark: AccuracyBenchmark, salt: str):
    """Deterministic sort key: SHA-256 of salted id (process-stable)."""
    digest = hashlib.sha256(f"{salt}:{benchmark.id}".encode()).hexdigest()
    return (digest, benchmark.id)


def split_benchmarks(
    benchmarks: list[AccuracyBenchmark],
    policy: SplitPolicy,
) -> BenchmarkSplit:
    """
    Split benchmarks into eval and holdout sets deterministically.

    The split is a pure function of (benchmark ids, policy): same input,
    same output — across runs and processes (SHA-256 bucketing, not the
    per-process-salted builtin hash()).

    Rules:
    - Fewer than 2 benchmarks: everything goes to eval, holdout stays empty.
    - Otherwise: holdout size k = clamp(round(N * ratio), min_holdout_size,
      N - min_eval_size). Infeasible constraints raise ValueError.

    Args:
        benchmarks: benchmark set to split (ids must be unique).
        policy: split configuration. REQUIRED (L-1): there is no secure
            default salt, so callers must pass an explicit per-tenant policy.

    Returns:
        BenchmarkSplit with holdout = first k benchmarks in hash order.
    """
    p = policy

    ids = [b.id for b in benchmarks]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate benchmark ids in input set")

    if len(benchmarks) < 2:
        return BenchmarkSplit(
            eval_benchmarks=list(benchmarks),
            holdout_benchmarks=[],
            policy=p,
        )

    n = len(benchmarks)
    lower = p.min_holdout_size
    upper = n - p.min_eval_size
    if lower > upper:
        raise ValueError(
            f"Cannot split {n} benchmarks with min_eval_size={p.min_eval_size} "
            f"and min_holdout_size={p.min_holdout_size}"
        )

    target = round(n * p.holdout_ratio)
    k = max(lower, min(upper, target))

    ordered = sorted(benchmarks, key=lambda b: _sort_key(b, p.salt))
    holdout = ordered[:k]
    eval_set = ordered[k:]

    return BenchmarkSplit(
        eval_benchmarks=eval_set,
        holdout_benchmarks=holdout,
        policy=p,
    )


# ========================================================================
# Holdout Summary (aggregate-only)
# ========================================================================


@dataclass(frozen=True)
class HoldoutSummary:
    """
    Aggregate results of a holdout evaluation run (F-ACC-006).

    By design this object CANNOT leak holdout content: it holds only
    counts and rates. No benchmark ids, questions, responses, or
    per-item scores are kept — those are discarded after aggregation.
    """

    holdout_count: int = 0
    pass_rate: float = 0.0
    average_score: float = 0.0
    hallucination_count: int = 0
    evaluated_at: datetime | None = None

    def __post_init__(self):
        validate_threshold(self.pass_rate)
        validate_threshold(self.average_score)
        if self.holdout_count < 0:
            raise ValueError("holdout_count must be >= 0")
        if self.hallucination_count < 0:
            raise ValueError("hallucination_count must be >= 0")

    @property
    def accuracy_level(self) -> AccuracyLevel:
        return AccuracyLevel.from_score(self.average_score)

    @property
    def is_empty(self) -> bool:
        return self.holdout_count == 0

    @classmethod
    def empty(cls) -> HoldoutSummary:
        """Summary for an empty holdout run."""
        return cls(
            holdout_count=0,
            pass_rate=0.0,
            average_score=0.0,
            hallucination_count=0,
            evaluated_at=datetime.now(UTC),
        )

    def to_dict(self) -> dict:
        """Serialize aggregates only — safe for UI and logs (F-ACC-006)."""
        return {
            "holdout_count": self.holdout_count,
            "pass_rate": self.pass_rate,
            "average_score": self.average_score,
            "hallucination_count": self.hallucination_count,
            "accuracy_level": self.accuracy_level.value,
            "evaluated_at": self.evaluated_at.isoformat() if self.evaluated_at else None,
        }
