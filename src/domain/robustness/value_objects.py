"""
Value Objects for Adversarial Robustness Testing Domain

Core types for attack simulation and robustness evaluation.
"""

from enum import Enum
import re
from dataclasses import dataclass
from typing import Optional, List

# Security: limits to prevent resource exhaustion
MAX_PERTURBATION_RATIO = 0.5  # max 50% of tokens perturbed
MAX_TEXT_LENGTH = 100_000
MAX_ATTACK_ITERATIONS = 100


class AttackType(str, Enum):
    """
    Adversarial attack methods.

    Each attack type represents a different strategy for
    generating adversarial examples.
    """
    FGSM = "fgsm"              # Fast Gradient Sign Method (text-adapted)
    PGD = "pgd"                # Projected Gradient Descent
    TEXT_FGSM = "text_fgsm"    # Text-specific FGSM
    CHAR_SWAP = "char_swap"    # Character-level swap
    CHAR_INSERT = "char_insert"  # Character-level insert
    CHAR_DELETE = "char_delete"  # Character-level delete
    WORD_SUBSTITUTION = "word_substitution"  # Synonym/word replacement
    SENTENCE_REORDER = "sentence_reorder"    # Sentence reordering
    KEYWORD_INJECTION = "keyword_injection"  # Adversarial keyword injection
    COMBINED = "combined"      # Multiple attack methods combined


class PerturbationMethod(str, Enum):
    """Methods for perturbing text inputs."""
    CHAR_SWAP = "char_swap"
    CHAR_INSERT = "char_insert"
    CHAR_DELETE = "char_delete"
    WORD_SYNONYM = "word_synonym"
    WORD_EMBEDDING = "word_embedding"
    SENTENCE_PARAPHRASE = "sentence_paraphrase"


class RobustnessLevel(str, Enum):
    """Robustness assessment classification."""
    ROBUST = "robust"              # <10% accuracy degradation
    MODERATELY_ROBUST = "moderately_robust"  # 10-25% degradation
    WEAK = "weak"                  # 25-50% degradation
    VULNERABLE = "vulnerable"      # >50% degradation


def validate_attack_epsilon(value: float) -> float:
    """
    Validate attack strength (epsilon).

    Must be in (0.0, 1.0]. Controls perturbation magnitude.
    """
    if not isinstance(value, (int, float)):
        raise ValueError(f"epsilon must be a number, got {type(value).__name__}")
    if value != value:  # NaN
        raise ValueError("epsilon must not be NaN")
    if value == float('inf') or value == float('-inf'):
        raise ValueError("epsilon must not be infinite")
    if not 0.0 < value <= 1.0:
        raise ValueError(f"epsilon must be in (0.0, 1.0], got {value}")
    return value


def validate_confidence_score(value: float, name: str = "confidence") -> float:
    """
    Validate a confidence/probability score is in [0.0, 1.0].

    Args:
        value: The score to validate
        name: Field name for error messages

    Returns:
        The validated value

    Raises:
        ValueError if value is out of range
    """
    if not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number, got {type(value).__name__}")
    if value != value:  # NaN
        raise ValueError(f"{name} must not be NaN")
    if value == float('inf') or value == float('-inf'):
        raise ValueError(f"{name} must not be infinite")
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be in [0.0, 1.0], got {value}")
    return value


@dataclass(frozen=True)
class AdversarialExample:
    """A single adversarial example: original input → perturbed input."""
    original_text: str = ""
    perturbed_text: str = ""
    attack_type: AttackType = AttackType.CHAR_SWAP
    perturbation_count: int = 0
    perturbation_ratio: float = 0.0

    def __post_init__(self):
        if self.perturbation_ratio < 0 or self.perturbation_ratio > MAX_PERTURBATION_RATIO:
            raise ValueError(
                f"perturbation_ratio must be in [0, {MAX_PERTURBATION_RATIO}], "
                f"got {self.perturbation_ratio}"
            )

    @property
    def has_perturbation(self) -> bool:
        return self.perturbation_count > 0

    def to_dict(self) -> dict:
        return {
            "original_text": self.original_text[:500],  # truncate for reports
            "perturbed_text": self.perturbed_text[:500],
            "attack_type": self.attack_type.value,
            "perturbation_count": self.perturbation_count,
            "perturbation_ratio": round(self.perturbation_ratio, 4),
        }
