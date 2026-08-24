"""
Selector Healer Implementation

AI-powered selector healing that automatically repairs broken selectors.
"""

import asyncio
import time
from typing import List, Optional

from src.domain.self_healing.entities import HealingResult, Selector
from src.domain.self_healing.interfaces import (
    IConfidenceScorer,
    IPageAnalyzer,
    ISelectorGenerator,
    ISelectorRepository,
)
from src.domain.self_healing.value_objects import ConfidenceLevel, HealingContext, HealingStatus


class SelectorHealer:
    """
    Main implementation of the selector healing algorithm.

    Uses a multi-strategy approach:
    1. Try existing alternatives
    2. Generate new candidates from context
    3. Score and rank candidates
    4. Validate best candidate
    5. Return result with confidence score
    """

    def __init__(
        self,
        confidence_scorer: IConfidenceScorer,
        selector_generator: ISelectorGenerator,
        page_analyzer: IPageAnalyzer,
        selector_repository: Optional[ISelectorRepository] = None,
        max_attempts: int = 5,
        min_confidence: float = 0.5,
    ):
        self.confidence_scorer = confidence_scorer
        self.selector_generator = selector_generator
        self.page_analyzer = page_analyzer
        self.selector_repository = selector_repository
        self.max_attempts = max_attempts
        self.min_confidence = min_confidence

    def heal(
        self,
        broken_selector: Selector,
        context: HealingContext,
    ) -> HealingResult:
        """
        Attempt to heal a broken selector.

        This is the main entry point for healing operations.
        """
        start_time = time.time()

        result = HealingResult(
            original_selector=broken_selector,
            status=HealingStatus.IN_PROGRESS,
            context=context,
        )

        candidates_evaluated = 0

        # Strategy 1: Try existing alternatives
        healed, confidence, attempts = self._try_alternatives(broken_selector, context)
        candidates_evaluated += attempts

        # Strategy 2: Generate new candidates if alternatives failed
        if healed is None or confidence < self.min_confidence:
            generated, gen_confidence, gen_attempts = self._generate_candidates(
                broken_selector, context
            )
            candidates_evaluated += gen_attempts

            if generated is not None and gen_confidence > confidence:
                healed = generated
                confidence = gen_confidence

        # Strategy 3: Try composite selectors
        if healed is None or confidence < self.min_confidence:
            composite, comp_confidence, comp_attempts = self._try_composite(
                broken_selector, context
            )
            candidates_evaluated += comp_attempts

            if composite is not None and comp_confidence > confidence:
                healed = composite
                confidence = comp_confidence

        # Build final result
        healing_time_ms = int((time.time() - start_time) * 1000)

        if healed is not None and confidence >= self.min_confidence:
            result.healed_selector = healed
            result.status = HealingStatus.SUCCESS
            result.confidence_score = confidence
            result.confidence_level = ConfidenceLevel.from_score(confidence)

            # Store the healed selector as an alternative
            if self.selector_repository:
                asyncio.create_task(
                    self.selector_repository.save_alternative(broken_selector.id, healed)
                )
        else:
            result.status = HealingStatus.FAILED
            result.confidence_score = confidence if confidence > 0 else 0.0
            result.confidence_level = ConfidenceLevel.from_score(confidence)
            result.error_message = (
                f"Could not find suitable replacement with confidence >= {self.min_confidence}"
            )

        result.healing_time_ms = healing_time_ms
        result.attempts = min(attempts + (1 if healed else 0), self.max_attempts)
        result.candidates_evaluated = candidates_evaluated

        return result

    def _try_alternatives(
        self,
        broken_selector: Selector,
        context: HealingContext,
    ) -> tuple[Optional[Selector], float, int]:
        """Try existing alternative selectors."""
        best_selector = None
        best_confidence = 0.0
        attempts = 0

        for alt in broken_selector.alternatives[: self.max_attempts]:
            attempts += 1

            # Validate the alternative works
            if self.page_analyzer.validate_selector(alt):
                confidence = self.confidence_scorer.score(alt, context)

                if confidence > best_confidence:
                    best_selector = alt
                    best_confidence = confidence

                    # Early exit on high confidence
                    if confidence >= 0.9:
                        break

        return best_selector, best_confidence, attempts

    def _generate_candidates(
        self,
        broken_selector: Selector,
        context: HealingContext,
    ) -> tuple[Optional[Selector], float, int]:
        """Generate and evaluate new candidate selectors."""
        # Generate from attributes
        attr_candidates = self.selector_generator.generate_from_attributes(
            context.element_attributes,
            context.surrounding_text,
        )

        # Generate from page context
        context_candidates = self.selector_generator.generate_from_context(context)

        all_candidates = attr_candidates + context_candidates
        attempts = len(all_candidates)

        if not all_candidates:
            return None, 0.0, 0

        # Score all candidates
        scored = self.confidence_scorer.score_candidates(all_candidates, context)

        # Find best valid candidate
        for selector, score in scored:
            if self.page_analyzer.validate_selector(selector):
                if score >= self.min_confidence:
                    return selector, score, attempts

        # Return best even if below threshold
        if scored:
            best_selector, best_score = scored[0]
            return best_selector, best_score, attempts

        return None, 0.0, attempts

    def _try_composite(
        self,
        broken_selector: Selector,
        context: HealingContext,
    ) -> tuple[Optional[Selector], float, int]:
        """Try generating composite selectors."""
        # Get similar elements from page
        similar = self.page_analyzer.find_similar_elements(context)
        attempts = len(similar)

        if not similar:
            return None, 0.0, 0

        # Generate composite selectors
        candidates = []
        for element in similar[:5]:
            attrs = element.get("attributes", {})
            text = element.get("text")

            generated = self.selector_generator.generate_from_attributes(attrs, text)
            candidates.extend(generated)

        if not candidates:
            return None, 0.0, attempts

        # Try composite combinations
        composites = self.selector_generator.generate_composite(candidates[:10])
        attempts += len(composites)

        # Score and find best
        scored = self.confidence_scorer.score_candidates(composites, context)

        for selector, score in scored:
            if self.page_analyzer.validate_selector(selector):
                return selector, score, attempts

        return None, 0.0, attempts

    def batch_heal(
        self,
        selectors: List[Selector],
        context_factory: callable,
    ) -> List[HealingResult]:
        """
        Heal multiple selectors in batch.

        Args:
            selectors: List of broken selectors to heal
            context_factory: Function that creates context for each selector

        Returns:
            List of healing results
        """
        results = []

        for selector in selectors:
            context = context_factory(selector)
            result = self.heal(selector, context)
            results.append(result)

        return results
