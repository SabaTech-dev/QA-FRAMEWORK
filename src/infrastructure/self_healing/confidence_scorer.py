"""
Confidence Scorer Implementation

Calculates confidence scores for selector candidates based on multiple factors.
"""

from typing import Any

from src.domain.self_healing.entities import Selector
from src.domain.self_healing.value_objects import HealingContext, SelectorType


class ConfidenceScorer:
    """
    Calculates confidence scores for selectors.

    Factors considered:
    - Selector specificity (more specific = higher confidence)
    - Historical success rate
    - Selector type reliability
    - Context match quality
    - Uniqueness on page
    """

    # Type reliability scores (empirically determined)
    TYPE_RELIABILITY = {
        SelectorType.ID: 0.95,
        SelectorType.DATA_ATTRIBUTE: 0.90,
        SelectorType.ARIA: 0.85,
        SelectorType.NAME: 0.80,
        SelectorType.CSS: 0.75,
        SelectorType.XPATH: 0.70,
        SelectorType.CLASS: 0.60,
        SelectorType.ATTRIBUTE: 0.55,
        SelectorType.TAG: 0.30,
        SelectorType.TEXT: 0.25,
        SelectorType.COMPOSITE: 0.65,
    }

    def __init__(
        self,
        type_weights: dict[SelectorType, float] = None,
        specificity_weight: float = 0.25,
        history_weight: float = 0.35,
        context_weight: float = 0.20,
        uniqueness_weight: float = 0.20,
    ):
        self.type_weights = type_weights or self.TYPE_RELIABILITY
        self.specificity_weight = specificity_weight
        self.history_weight = history_weight
        self.context_weight = context_weight
        self.uniqueness_weight = uniqueness_weight

    def score(
        self,
        selector: Selector,
        context: HealingContext,
    ) -> float:
        """
        Calculate confidence score for a selector.

        Returns a score between 0.0 and 1.0.
        """
        scores = []

        # 1. Type reliability score
        type_score = self._score_type(selector.selector_type)
        scores.append(type_score)

        # 2. Specificity score
        specificity_score = self._score_specificity(selector)
        scores.append(specificity_score * self.specificity_weight)

        # 3. Historical success score
        history_score = self._score_history(selector)
        scores.append(history_score * self.history_weight)

        # 4. Context match score
        context_score = self._score_context(selector, context)
        scores.append(context_score * self.context_weight)

        # 5. Uniqueness score (from context if available)
        uniqueness_score = self._score_uniqueness(selector, context)
        scores.append(uniqueness_score * self.uniqueness_weight)

        # Combine scores with weights
        total_weight = (
            1.0
            + self.specificity_weight
            + self.history_weight
            + self.context_weight
            + self.uniqueness_weight
        )

        final_score = sum(scores) / total_weight

        # Clamp to [0, 1]
        return max(0.0, min(1.0, final_score))

    def score_candidates(
        self,
        selectors: list[Selector],
        context: HealingContext,
    ) -> list[tuple]:
        """
        Score multiple candidates and return sorted by score.

        Returns list of (selector, score) tuples.
        """
        scored = [(selector, self.score(selector, context)) for selector in selectors]

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        return scored

    def _score_type(self, selector_type: SelectorType) -> float:
        """Score based on selector type reliability."""
        return self.type_weights.get(selector_type, 0.5)

    def _score_specificity(self, selector: Selector) -> float:
        """Score based on selector specificity/precision."""
        value = selector.value

        if not value:
            return 0.0

        score = 0.5  # Base score

        # ID selector is most specific
        if selector.selector_type == SelectorType.ID or value.startswith("#"):
            return 1.0

        # Data attributes are very specific
        if "[data-" in value:
            score += 0.3

        # Multiple classes increase specificity
        class_count = value.count(".") + value.count("[class")
        score += min(0.2, class_count * 0.05)

        # Attribute selectors add specificity
        attr_count = value.count("[") - value.count("[data-")
        score += min(0.15, attr_count * 0.05)

        # Direct child combinator is more specific
        if ">" in value:
            score += 0.1

        # Long selectors tend to be brittle
        length_penalty = max(0, (len(value) - 50) * 0.002)
        score -= length_penalty

        # nth-child is often brittle
        if ":nth-child" in value or ":nth-of-type" in value:
            score -= 0.15

        return max(0.0, min(1.0, score))

    def _score_history(self, selector: Selector) -> float:
        """Score based on historical success rate."""
        if selector.metadata is None:
            return 0.5  # Neutral score for new selectors

        # Weight by number of observations
        usage_count = selector.metadata.usage_count
        success_rate = selector.metadata.success_rate

        # Apply Bayesian smoothing
        prior_weight = 5  # Equivalent to 5 prior observations
        prior_rate = 0.7  # Prior success rate

        smoothed_rate = (success_rate * usage_count + prior_rate * prior_weight) / (
            usage_count + prior_weight
        )

        return smoothed_rate

    def _score_context(
        self,
        selector: Selector,
        context: HealingContext,
    ) -> float:
        """Score based on how well selector matches context."""
        if not context.element_attributes:
            return 0.5

        score = 0.0
        value = selector.value.lower()
        attrs = {k.lower(): v.lower() for k, v in context.element_attributes.items()}

        # Check if selector uses attributes from context
        for attr_name, attr_value in attrs.items():
            if attr_value and attr_value in value:
                # ID match
                if attr_name == "id":
                    score += 0.4
                # Data attribute match
                elif attr_name.startswith("data-"):
                    score += 0.35
                # Name match
                elif attr_name == "name":
                    score += 0.3
                # Class match
                elif attr_name == "class":
                    score += 0.2
                # Other attribute match
                else:
                    score += 0.15

        # Check surrounding text match
        if context.surrounding_text:
            text_lower = context.surrounding_text.lower()
            # Text-based selectors
            if selector.selector_type == SelectorType.TEXT:
                if text_lower in value or value in text_lower:
                    score += 0.3

        # Parent selector match
        if context.parent_selector and context.parent_selector in value:
            score += 0.1

        return min(1.0, score)

    def _score_uniqueness(
        self,
        selector: Selector,
        context: HealingContext,
    ) -> float:
        """Score based on selector uniqueness on page."""
        # This would ideally be computed from actual page analysis
        # For now, we estimate from selector characteristics

        value = selector.value

        # ID selectors are unique by definition
        if selector.selector_type == SelectorType.ID or value.startswith("#"):
            return 1.0

        # Estimate based on specificity
        # More specific selectors are more likely to be unique
        specificity = self._score_specificity(selector)

        # Adjust based on selector type
        type_factor = self.type_weights.get(selector.selector_type, 0.5)

        return (specificity + type_factor) / 2


class AIConfidenceScorer(ConfidenceScorer):
    """
    Enhanced confidence scorer using AI/ML for better predictions.

    This version can learn from past healing results and adapt
    its scoring based on observed patterns.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._learning_data: dict[str, Any] = {}

    def record_outcome(
        self,
        selector: Selector,
        predicted_score: float,
        actual_success: bool,
    ):
        """Record the outcome of a healing attempt for learning."""
        key = f"{selector.selector_type.value}:{selector.value[:50]}"

        if key not in self._learning_data:
            self._learning_data[key] = {
                "predictions": [],
                "outcomes": [],
            }

        self._learning_data[key]["predictions"].append(predicted_score)
        self._learning_data[key]["outcomes"].append(1.0 if actual_success else 0.0)

    def get_calibration_adjustment(self, selector: Selector) -> float:
        """Get adjustment factor based on calibration data."""
        key = f"{selector.selector_type.value}:{selector.value[:50]}"

        if key not in self._learning_data:
            return 0.0

        data = self._learning_data[key]
        if len(data["predictions"]) < 5:
            return 0.0

        # Calculate calibration error
        avg_predicted = sum(data["predictions"]) / len(data["predictions"])
        avg_actual = sum(data["outcomes"]) / len(data["outcomes"])

        # Return adjustment to correct bias
        return avg_actual - avg_predicted
