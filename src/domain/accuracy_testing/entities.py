"""
Entities for AI Accuracy Testing Domain

Core entities for accuracy evaluations, benchmarks, and test sessions.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from uuid import uuid4

from .value_objects import (
    EvaluationCriterion,
    AccuracyLevel,
    EvaluationStatus,
    LegalDomain,
    ResponseVerdict,
    CriterionScore,
    validate_jurisdiction,
    validate_threshold,
)


@dataclass
class AccuracyBenchmark:
    """
    A benchmark case for accuracy testing.

    Contains the ground-truth data (question, expected answer, criteria)
    against which AI responses are evaluated.

    German AI Liability ruling (BGH 2025):
    - AI systems can be held liable under product liability law
    - Developers must ensure AI outputs meet safety requirements
    - Burden of proof may be reversed in AI-caused damages
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    legal_domain: LegalDomain = LegalDomain.AI_LIABILITY
    jurisdiction: str = "DE"  # ISO 3166-1 alpha-2

    # Benchmark content
    question: str = ""
    ground_truth: str = ""
    key_points: List[str] = field(default_factory=list)
    legal_references: List[str] = field(default_factory=list)

    # Evaluation config
    criteria: List[EvaluationCriterion] = field(default_factory=lambda: [
        EvaluationCriterion.FACTUAL_ACCURACY,
        EvaluationCriterion.LEGAL_REASONING,
        EvaluationCriterion.CITATION_CORRECTNESS,
        EvaluationCriterion.COMPLETENESS,
        EvaluationCriterion.NUANCE_HANDLING,
    ])
    passing_threshold: float = 0.6

    # Metadata
    source: str = ""  # e.g., "BGH Urteil vom 28.01.2025 - VI ZR 67/24"
    difficulty: str = "medium"  # easy, medium, hard
    tags: List[str] = field(default_factory=list)
    tenant_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        # F-ACC-002: Validate jurisdiction (ISO 3166-1 alpha-2)
        validate_jurisdiction(self.jurisdiction)
        # F-ACC-002: Validate threshold range
        validate_threshold(self.passing_threshold)

    @property
    def is_german_ai_liability(self) -> bool:
        """Check if this is a German AI liability benchmark."""
        return (
            self.legal_domain == LegalDomain.AI_LIABILITY
            and self.jurisdiction == "DE"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary (public view — sensitive fields excluded)."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "legal_domain": self.legal_domain.value,
            "jurisdiction": self.jurisdiction,
            "question": self.question,
            # F-ACC-004: ground_truth excluded from public output
            "key_points": self.key_points,
            "legal_references": self.legal_references,
            "criteria": [c.value for c in self.criteria],
            "passing_threshold": self.passing_threshold,
            "source": self.source,
            "difficulty": self.difficulty,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
        }

    def to_dict_full(self) -> Dict[str, Any]:
        """Serialize with all fields including sensitive data (for admin/internal use)."""
        d = self.to_dict()
        d["ground_truth"] = self.ground_truth
        d["tenant_id"] = self.tenant_id
        return d


@dataclass
class AccuracyEvaluation:
    """
    Result of evaluating a single AI response against a benchmark.

    Contains the AI's response, scores per criterion, and an overall verdict.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    benchmark_id: str = ""
    session_id: Optional[str] = None

    # Input
    prompt: str = ""
    ai_response: str = ""

    # Results
    criterion_scores: List[CriterionScore] = field(default_factory=list)
    overall_score: float = 0.0
    accuracy_level: AccuracyLevel = AccuracyLevel.FAILING
    verdict: ResponseVerdict = ResponseVerdict.INACCURATE
    passed: bool = False

    # Analysis
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    missing_points: List[str] = field(default_factory=list)
    hallucinations: List[str] = field(default_factory=list)

    # Metadata
    ai_model: str = ""
    evaluation_time_ms: int = 0
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tenant_id: Optional[str] = None

    @property
    def score_count(self) -> int:
        return len(self.criterion_scores)

    @property
    def has_hallucinations(self) -> bool:
        return len(self.hallucinations) > 0

    def compute_overall(self) -> "AccuracyEvaluation":
        """F-ACC-005: Compute overall score, returning a new object (no mutation)."""
        if not self.criterion_scores:
            return self

        new_overall = sum(s.score for s in self.criterion_scores) / len(self.criterion_scores)
        new_level = AccuracyLevel.from_score(new_overall)
        new_passed = new_overall >= 0.6

        # Determine verdict
        if new_overall >= 0.8:
            new_verdict = ResponseVerdict.ACCURATE
        elif new_overall >= 0.6:
            new_verdict = ResponseVerdict.PARTIALLY_ACCURATE
        elif new_overall >= 0.3:
            new_verdict = ResponseVerdict.INACCURATE
        else:
            new_verdict = ResponseVerdict.MISLEADING

        return AccuracyEvaluation(
            id=self.id,
            benchmark_id=self.benchmark_id,
            session_id=self.session_id,
            prompt=self.prompt,
            ai_response=self.ai_response,
            criterion_scores=self.criterion_scores,
            overall_score=new_overall,
            accuracy_level=new_level,
            verdict=new_verdict,
            passed=new_passed,
            strengths=self.strengths,
            weaknesses=self.weaknesses,
            missing_points=self.missing_points,
            hallucinations=self.hallucinations,
            ai_model=self.ai_model,
            evaluation_time_ms=self.evaluation_time_ms,
            evaluated_at=self.evaluated_at,
            tenant_id=self.tenant_id,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary (public view — tenant_id excluded)."""
        return {
            "id": self.id,
            "benchmark_id": self.benchmark_id,
            "session_id": self.session_id,
            "prompt": self.prompt,
            "ai_response": self.ai_response[:500],  # truncate for reports
            "criterion_scores": [s.to_dict() for s in self.criterion_scores],
            "overall_score": self.overall_score,
            "accuracy_level": self.accuracy_level.value,
            "verdict": self.verdict.value,
            "passed": self.passed,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "missing_points": self.missing_points,
            "hallucinations": self.hallucinations,
            "has_hallucinations": self.has_hallucinations,
            "ai_model": self.ai_model,
            "evaluation_time_ms": self.evaluation_time_ms,
            "evaluated_at": self.evaluated_at.isoformat(),
            # F-ACC-004: tenant_id excluded from public output
        }


@dataclass
class AccuracyTestSession:
    """
    A session for batch accuracy evaluation.

    Groups multiple evaluations against a set of benchmarks,
    tracking aggregate statistics.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    tenant_id: Optional[str] = None

    # Config
    name: str = ""
    description: str = ""
    legal_domain: LegalDomain = LegalDomain.AI_LIABILITY
    ai_model: str = ""

    # Contents
    benchmarks: List[AccuracyBenchmark] = field(default_factory=list)
    evaluations: List[AccuracyEvaluation] = field(default_factory=list)

    # Stats
    total_benchmarks: int = 0
    evaluations_completed: int = 0
    evaluations_passed: int = 0

    # Timing
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    total_time_ms: int = 0

    status: EvaluationStatus = EvaluationStatus.PENDING
    error_message: Optional[str] = None

    @property
    def pass_rate(self) -> float:
        if self.evaluations_completed == 0:
            return 0.0
        return self.evaluations_passed / self.evaluations_completed

    @property
    def average_score(self) -> float:
        completed = [e for e in self.evaluations if e.overall_score > 0]
        if not completed:
            return 0.0
        return sum(e.overall_score for e in completed) / len(completed)

    @property
    def hallucination_count(self) -> int:
        return sum(1 for e in self.evaluations if e.has_hallucinations)

    @property
    def overall_level(self) -> AccuracyLevel:
        return AccuracyLevel.from_score(self.average_score)

    @property
    def is_completed(self) -> bool:
        return self.status in (
            EvaluationStatus.COMPLETED,
            EvaluationStatus.FAILED,
            EvaluationStatus.PARTIAL,
        )

    def add_evaluation(self, evaluation: AccuracyEvaluation) -> "AccuracyTestSession":
        """Return new session with added evaluation (immutable pattern)."""
        new_evals = self.evaluations + [evaluation]
        completed = [e for e in new_evals if e.overall_score > 0]
        passed = sum(1 for e in completed if e.passed)
        return AccuracyTestSession(
            id=self.id,
            tenant_id=self.tenant_id,
            name=self.name,
            description=self.description,
            legal_domain=self.legal_domain,
            ai_model=self.ai_model,
            benchmarks=self.benchmarks,
            evaluations=new_evals,
            total_benchmarks=self.total_benchmarks,
            evaluations_completed=len(completed),
            evaluations_passed=passed,
            started_at=self.started_at,
            completed_at=self.completed_at,
            total_time_ms=self.total_time_ms,
            status=self.status,
            error_message=self.error_message,
        )

    def complete(self, status: EvaluationStatus = None, error: str = None) -> "AccuracyTestSession":
        """Mark session as completed (returns new object)."""
        final_status = status or (
            EvaluationStatus.COMPLETED
            if self.evaluations_passed == self.evaluations_completed
            else EvaluationStatus.PARTIAL
            if self.evaluations_completed > 0
            else EvaluationStatus.FAILED
        )
        total_time = int((datetime.now(timezone.utc) - self.started_at).total_seconds() * 1000)
        return AccuracyTestSession(
            id=self.id,
            tenant_id=self.tenant_id,
            name=self.name,
            description=self.description,
            legal_domain=self.legal_domain,
            ai_model=self.ai_model,
            benchmarks=self.benchmarks,
            evaluations=self.evaluations,
            total_benchmarks=self.total_benchmarks,
            evaluations_completed=self.evaluations_completed,
            evaluations_passed=self.evaluations_passed,
            started_at=self.started_at,
            completed_at=datetime.now(timezone.utc),
            total_time_ms=total_time,
            status=final_status,
            error_message=error or self.error_message,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary (public view — tenant_id excluded)."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "legal_domain": self.legal_domain.value,
            "ai_model": self.ai_model,
            "total_benchmarks": self.total_benchmarks,
            "evaluations_completed": self.evaluations_completed,
            "evaluations_passed": self.evaluations_passed,
            "pass_rate": self.pass_rate,
            "average_score": self.average_score,
            "overall_level": self.overall_level.value,
            "hallucination_count": self.hallucination_count,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_time_ms": self.total_time_ms,
            "evaluations": [e.to_dict() for e in self.evaluations],
            # F-ACC-004: tenant_id excluded from public output
        }

    def to_dict_full(self) -> Dict[str, Any]:
        """Serialize with all fields including tenant_id (for admin/internal use)."""
        d = self.to_dict()
        d["tenant_id"] = self.tenant_id
        return d
