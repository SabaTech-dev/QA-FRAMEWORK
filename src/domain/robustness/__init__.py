"""
Adversarial Robustness Testing Domain Module

Evaluates AI system robustness against adversarial attacks,
providing evidence for EU AI Act Art. 15 compliance.

Provides:
- FGSM attack simulation (text-based)
- PGD attack simulation
- Text perturbation attacks
- Robustness scoring and degradation measurement
"""

from .value_objects import (
    AttackType,
    RobustnessLevel,
    PerturbationMethod,
    validate_attack_epsilon,
    validate_confidence_score,
    MAX_PERTURBATION_RATIO,
)
from .entities import (
    AttackResult,
    RobustnessTestSession,
    RobustnessReport,
    AdversarialExample,
)
from .interfaces import (
    IAttackSimulator,
    IModelPredictor,
)

__all__ = [
    # Value Objects
    "AttackType",
    "RobustnessLevel",
    "PerturbationMethod",
    "validate_attack_epsilon",
    "validate_confidence_score",
    "MAX_PERTURBATION_RATIO",
    # Entities
    "AttackResult",
    "RobustnessTestSession",
    "RobustnessReport",
    "AdversarialExample",
    # Interfaces
    "IAttackSimulator",
    "IModelPredictor",
]
