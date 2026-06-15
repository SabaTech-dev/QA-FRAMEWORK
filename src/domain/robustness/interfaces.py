"""
Interfaces for Adversarial Robustness Testing Domain

Abstract interfaces defining contracts for attack simulation.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Protocol, Tuple

from .entities import AttackResult, AdversarialExample
from .value_objects import AttackType


class IAttackSimulator(Protocol):
    """Protocol for simulating adversarial attacks on text inputs."""

    def generate_adversarial_examples(
        self,
        text: str,
        attack_type: AttackType,
        epsilon: float = 0.1,
        max_perturbations: int = 10,
    ) -> List[AdversarialExample]:
        """
        Generate adversarial examples from an original text.

        Args:
            text: Original input text
            attack_type: Type of attack to simulate
            epsilon: Attack strength (0.0, 1.0]
            max_perturbations: Maximum number of perturbations

        Returns:
            List of adversarial examples
        """
        ...

    def evaluate_attack(
        self,
        original_text: str,
        adversarial_text: str,
        original_prediction: str,
        original_confidence: float,
    ) -> Tuple[str, float, bool]:
        """
        Evaluate a single adversarial example against the model.

        Args:
            original_text: Original input
            adversarial_text: Perturbed input
            original_prediction: Model's original prediction
            original_confidence: Model's original confidence

        Returns:
            Tuple of (new_prediction, new_confidence, prediction_changed)
        """
        ...


class IModelPredictor(Protocol):
    """Protocol for getting predictions from the AI model under test."""

    def predict(self, text: str) -> Tuple[str, float]:
        """
        Get model prediction and confidence for input text.

        Args:
            text: Input text to classify

        Returns:
            Tuple of (prediction_label, confidence_score)
        """
        ...

    def predict_batch(self, texts: List[str]) -> List[Tuple[str, float]]:
        """
        Get predictions for a batch of inputs.

        Args:
            texts: List of input texts

        Returns:
            List of (prediction_label, confidence_score) tuples
        """
        ...
