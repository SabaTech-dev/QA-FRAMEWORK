"""
Entities for Adversarial Robustness Testing Domain

Core entities for robustness evaluation sessions, attack results,
and comprehensive robustness reporting.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from uuid import uuid4
import json

from .value_objects import (
    AttackType,
    RobustnessLevel,
    AdversarialExample,
    validate_attack_epsilon,
    validate_confidence_score,
)


@dataclass
class AttackResult:
    """
    Result of a single adversarial attack attempt.

    Captures the attack configuration, outcomes, and
    accuracy degradation measurements.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    attack_type: AttackType = AttackType.CHAR_SWAP
    epsilon: float = 0.1
    iterations: int = 1

    # Input
    original_text: str = ""
    adversarial_examples: List[AdversarialExample] = field(default_factory=list)

    # Outcomes
    original_prediction: str = ""
    adversarial_prediction: str = ""
    original_confidence: float = 0.0
    adversarial_confidence: float = 0.0
    prediction_changed: bool = False
    attack_successful: bool = False

    # Aggregate metrics
    total_samples: int = 0
    successful_attacks: int = 0
    accuracy_before_attack: float = 0.0
    accuracy_after_attack: float = 0.0
    accuracy_degradation: float = 0.0
    mean_confidence_drop: float = 0.0

    # Metadata
    model_name: str = ""
    evaluation_time_ms: int = 0
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        validate_attack_epsilon(self.epsilon)
        validate_confidence_score(self.original_confidence, "original_confidence")
        validate_confidence_score(self.adversarial_confidence, "adversarial_confidence")

    @property
    def success_rate(self) -> float:
        """Fraction of attacks that succeeded."""
        if self.total_samples == 0:
            return 0.0
        return self.successful_attacks / self.total_samples

    @property
    def robustness_score(self) -> float:
        """
        Overall robustness score (0-1).

        1.0 = fully robust, 0.0 = fully vulnerable.
        Based on accuracy retention after attack.
        """
        return max(0.0, 1.0 - self.accuracy_degradation)

    @property
    def robustness_level(self) -> RobustnessLevel:
        """Classify robustness based on degradation."""
        degradation = self.accuracy_degradation
        if degradation < 0.10:
            return RobustnessLevel.ROBUST
        elif degradation < 0.25:
            return RobustnessLevel.MODERATELY_ROBUST
        elif degradation < 0.50:
            return RobustnessLevel.WEAK
        else:
            return RobustnessLevel.VULNERABLE

    def compute_metrics(self) -> None:
        """Recompute aggregate metrics from adversarial examples."""
        if not self.adversarial_examples:
            return

        self.total_samples = len(self.adversarial_examples)
        self.successful_attacks = sum(
            1 for ex in self.adversarial_examples
            if ex.has_perturbation
        )

        # Accuracy degradation
        self.accuracy_degradation = max(
            0.0,
            self.accuracy_before_attack - self.accuracy_after_attack
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "attack_type": self.attack_type.value,
            "epsilon": self.epsilon,
            "iterations": self.iterations,
            "original_text": self.original_text[:500],
            "adversarial_examples_count": len(self.adversarial_examples),
            "outcomes": {
                "original_prediction": self.original_prediction,
                "adversarial_prediction": self.adversarial_prediction,
                "original_confidence": round(self.original_confidence, 4),
                "adversarial_confidence": round(self.adversarial_confidence, 4),
                "prediction_changed": self.prediction_changed,
                "attack_successful": self.attack_successful,
            },
            "aggregate": {
                "total_samples": self.total_samples,
                "successful_attacks": self.successful_attacks,
                "success_rate": round(self.success_rate, 4),
                "accuracy_before_attack": round(self.accuracy_before_attack, 4),
                "accuracy_after_attack": round(self.accuracy_after_attack, 4),
                "accuracy_degradation": round(self.accuracy_degradation, 4),
                "mean_confidence_drop": round(self.mean_confidence_drop, 4),
                "robustness_score": round(self.robustness_score, 4),
                "robustness_level": self.robustness_level.value,
            },
            "model_name": self.model_name,
            "evaluation_time_ms": self.evaluation_time_ms,
            "evaluated_at": self.evaluated_at.isoformat(),
        }


@dataclass
class RobustnessTestSession:
    """
    A session for batch adversarial robustness evaluation.

    Groups multiple attack results against a model/system.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    tenant_id: Optional[str] = None

    # Config
    name: str = ""
    description: str = ""
    system_id: str = ""
    model_name: str = ""

    # Contents
    attack_results: List[AttackResult] = field(default_factory=list)

    # Timing
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    total_time_ms: int = 0

    status: str = "pending"
    error_message: Optional[str] = None

    @property
    def attack_count(self) -> int:
        return len(self.attack_results)

    @property
    def average_robustness_score(self) -> float:
        if not self.attack_results:
            return 0.0
        return sum(a.robustness_score for a in self.attack_results) / len(self.attack_results)

    @property
    def worst_robustness_score(self) -> float:
        if not self.attack_results:
            return 0.0
        return min(a.robustness_score for a in self.attack_results)

    @property
    def is_completed(self) -> bool:
        return self.status in ("completed", "failed", "partial")

    def add_attack_result(self, result: AttackResult) -> None:
        """Add an attack result to the session."""
        self.attack_results.append(result)

    def complete(self, status: str = None, error: str = None) -> None:
        """Mark session as completed."""
        self.status = status or "completed"
        self.completed_at = datetime.now(timezone.utc)
        self.total_time_ms = int(
            (self.completed_at - self.started_at).total_seconds() * 1000
        )
        if error:
            self.error_message = error
            self.status = "failed"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary (excludes tenant_id)."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "system_id": self.system_id,
            "model_name": self.model_name,
            "attack_results": [a.to_dict() for a in self.attack_results],
            "aggregate": {
                "attack_count": self.attack_count,
                "average_robustness_score": round(self.average_robustness_score, 4),
                "worst_robustness_score": round(self.worst_robustness_score, 4),
            },
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_time_ms": self.total_time_ms,
        }


@dataclass
class RobustnessReport:
    """
    Complete robustness evaluation report.

    Aggregates attack results into a comprehensive robustness
    assessment with recommendations.
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    system_id: str = ""
    model_name: str = ""

    # Results
    attack_results: List[AttackResult] = field(default_factory=list)

    # Aggregate metrics
    overall_robustness_score: float = 0.0
    overall_robustness_level: RobustnessLevel = RobustnessLevel.ROBUST
    average_degradation: float = 0.0
    worst_degradation: float = 0.0
    attacks_tested: int = 0

    # Thresholds
    robustness_threshold: float = 0.8  # minimum acceptable score

    # Metadata
    assessment_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    assessor: str = ""
    methodology: str = ""
    notes: List[str] = field(default_factory=list)
    tenant_id: Optional[str] = None

    @property
    def attack_type_count(self) -> int:
        return len(set(a.attack_type for a in self.attack_results))

    def compute_overall_robustness(self) -> RobustnessLevel:
        """
        Determine overall robustness from all attack results.

        Uses worst-case approach across attack types.
        """
        if not self.attack_results:
            self.overall_robustness_level = RobustnessLevel.ROBUST
            return self.overall_robustness_level

        self.attacks_tested = len(self.attack_results)
        scores = [a.robustness_score for a in self.attack_results]
        degradations = [a.accuracy_degradation for a in self.attack_results]

        self.overall_robustness_score = sum(scores) / len(scores)
        self.average_degradation = sum(degradations) / len(degradations)
        self.worst_degradation = max(degradations)

        # Worst-case level
        levels = [a.robustness_level for a in self.attack_results]
        level_order = [
            RobustnessLevel.ROBUST,
            RobustnessLevel.MODERATELY_ROBUST,
            RobustnessLevel.WEAK,
            RobustnessLevel.VULNERABLE,
        ]
        worst = max(levels, key=lambda l: level_order.index(l))
        self.overall_robustness_level = worst

        return self.overall_robustness_level

    def add_attack_result(self, result: AttackResult) -> None:
        """Add an attack result to the report."""
        self.attack_results.append(result)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary (excludes tenant_id)."""
        return {
            "id": self.id,
            "system_id": self.system_id,
            "model_name": self.model_name,
            "attack_results": [a.to_dict() for a in self.attack_results],
            "aggregate": {
                "overall_robustness_score": round(self.overall_robustness_score, 4),
                "overall_robustness_level": self.overall_robustness_level.value,
                "average_degradation": round(self.average_degradation, 4),
                "worst_degradation": round(self.worst_degradation, 4),
                "attacks_tested": self.attacks_tested,
                "attack_type_count": self.attack_type_count,
            },
            "thresholds": {
                "robustness_threshold": self.robustness_threshold,
            },
            "assessment_date": self.assessment_date.isoformat(),
            "assessor": self.assessor,
            "methodology": self.methodology,
            "notes": self.notes,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
