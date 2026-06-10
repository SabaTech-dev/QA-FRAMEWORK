"""
Rule-Based Accuracy Evaluator

Evaluates AI responses against benchmarks using keyword matching,
coverage analysis, and structural comparison.

This is a deterministic evaluator that does not require an LLM.
For production use, consider integrating an LLM-based evaluator.
"""

import re
import time
from datetime import datetime, timezone
from typing import List

from src.domain.accuracy_testing.entities import AccuracyEvaluation, AccuracyBenchmark
from src.domain.accuracy_testing.value_objects import (
    EvaluationCriterion,
    ResponseVerdict,
    CriterionScore,
    MAX_EVAL_INPUT_LENGTH,
)


class RuleBasedAccuracyEvaluator:
    """
    Evaluates AI response accuracy using rule-based heuristics.

    Scoring strategy per criterion:
    - FACTUAL_ACCURACY: checks key points coverage + hallucination detection
    - LEGAL_REASONING: checks for legal argumentation structure
    - CITATION_CORRECTNESS: validates legal references are mentioned
    - COMPLETENESS: ratio of key points addressed
    - NUANCE_HANDLING: checks for qualifying language and caveats
    - HARMFULNESS_SAFETY: checks response doesn't give harmful advice
    """

    # Qualifying language that indicates nuance awareness
    NUANCE_PATTERNS = [
        r"\bhowever\b", r"\balthough\b", r"\bdepends?\b", r"\bmay\b",
        r"\bmight\b", r"\bin\s+some\s+cases\b", r"\bgenerally\b",
        r"\btypically\b", r"\busually\b", r"\bunder\s+certain\b",
        r"\bsubject\s+to\b", r"\b caveat", r"\blimitation",
        r"\bno obstante\b", r"\bdepend", r"\bpuede\b", r"\bsin\s+embargo\b",
    ]

    # Patterns suggesting harmful/absolute legal advice
    HARMFUL_PATTERNS = [
        r"\byou\s+should\s+definitely\b",
        r"\bthis\s+is\s+definitely\s+legal\b",
        r"\byou\s+have\s+no\s+liability\b",
        r"\bthere\s+is\s+no\s+risk\b",
        r"\bguaranteed\s+to\s+win\b",
    ]

    # Legal argumentation indicators
    LEGAL_REASONING_PATTERNS = [
        r"\b§\s*\d+",  # § references
        r"\barticle\s+\d+", r"\bart\.\s*\d+",
        r"\baccording\s+to\b", r"\bpursuant\s+to\b",
        r"\bthe\s+(court|ruling|decision|judgment)\b",
        r"\bliable\b", r"\bliability\b",
        r"\bburden\s+of\s+proof\b", r"\bBeweislast\b",
        r"\bproducer\b", r"\bHersteller\b",
        r"\bdefect\b", r"\bdefective\b",
        r"\bnegligence\b", r"\bfault\b",
        r"\bstatute\b", r"\bact\b", r"\blaw\b",
        r"\bregulation\b", r"\bdirective\b",
    ]

    def evaluate(
        self,
        benchmark: AccuracyBenchmark,
        ai_response: str,
        ai_model: str = "",
    ) -> AccuracyEvaluation:
        """Evaluate an AI response against a benchmark."""
        start = time.monotonic()

        # F-ACC-003: Truncate inputs to prevent ReDoS / excessive regex work
        response_truncated = ai_response[:MAX_EVAL_INPUT_LENGTH]
        response_lower = response_truncated.lower()
        truth_truncated = benchmark.ground_truth[:MAX_EVAL_INPUT_LENGTH]
        truth_lower = truth_truncated.lower()

        # Compute per-criterion scores
        scores: List[CriterionScore] = []
        strengths: List[str] = []
        weaknesses: List[str] = []
        missing_points: List[str] = []
        hallucinations: List[str] = []

        for criterion in benchmark.criteria:
            if criterion == EvaluationCriterion.FACTUAL_ACCURACY:
                score, expl = self._score_factual_accuracy(response_lower, truth_lower, benchmark)
            elif criterion == EvaluationCriterion.LEGAL_REASONING:
                score, expl = self._score_legal_reasoning(response_lower)
            elif criterion == EvaluationCriterion.CITATION_CORRECTNESS:
                score, expl = self._score_citations(response_lower, benchmark)
            elif criterion == EvaluationCriterion.COMPLETENESS:
                score, expl, missing = self._score_completeness(response_lower, benchmark)
                missing_points.extend(missing)
            elif criterion == EvaluationCriterion.NUANCE_HANDLING:
                score, expl = self._score_nuance(response_lower)
            elif criterion == EvaluationCriterion.HARMFULNESS_SAFETY:
                score, expl, harms = self._score_safety(response_lower)
                hallucinations.extend(harms)
            else:
                score, expl = 0.5, f"Unknown criterion: {criterion.value}"

            scores.append(CriterionScore(
                criterion=criterion,
                score=score,
                explanation=expl,
            ))

        # Build evaluation
        elapsed_ms = int((time.monotonic() - start) * 1000)

        evaluation = AccuracyEvaluation(
            benchmark_id=benchmark.id,
            prompt=benchmark.question,
            ai_response=ai_response,
            criterion_scores=scores,
            ai_model=ai_model,
            evaluation_time_ms=elapsed_ms,
            evaluated_at=datetime.now(timezone.utc),
        )

        # Identify strengths and weaknesses
        for s in scores:
            if s.score >= 0.7:
                strengths.append(f"{s.criterion.value}: {s.explanation}")
            elif s.score < 0.4:
                weaknesses.append(f"{s.criterion.value}: {s.explanation}")

        evaluation.strengths = strengths
        evaluation.weaknesses = weaknesses
        evaluation.missing_points = missing_points
        evaluation.hallucinations = hallucinations

        # F-ACC-005: compute_overall returns new object (no mutation)
        evaluation = evaluation.compute_overall()

        return evaluation

    def _score_factual_accuracy(
        self, response: str, truth: str, benchmark: AccuracyBenchmark
    ) -> tuple[float, str]:
        """Score factual accuracy by checking key point coverage."""
        if not benchmark.key_points:
            return 0.5, "No key points defined for comparison"

        covered = 0
        for point in benchmark.key_points:
            point_keywords = self._extract_keywords(point.lower())
            if any(kw in response for kw in point_keywords if len(kw) > 3):
                covered += 1

        ratio = covered / len(benchmark.key_points)
        return ratio, f"Covered {covered}/{len(benchmark.key_points)} key points ({ratio:.0%})"

    def _score_legal_reasoning(
        self, response: str
    ) -> tuple[float, str]:
        """Score legal reasoning by detecting legal argumentation patterns."""
        matches = sum(1 for p in self.LEGAL_REASONING_PATTERNS if re.search(p, response))
        max_expected = len(self.LEGAL_REASONING_PATTERNS)
        # Normalize: 5+ patterns = excellent, 3 = adequate, 0-1 = poor
        score = min(1.0, matches / max(min(max_expected * 0.4, 8), 1))
        return score, f"Found {matches} legal reasoning indicators"

    def _score_citations(
        self, response: str, benchmark: AccuracyBenchmark
    ) -> tuple[float, str]:
        """Score citation correctness by checking if legal references are mentioned."""
        if not benchmark.legal_references:
            return 0.5, "No legal references to verify"

        found = 0
        for ref in benchmark.legal_references:
            # Check partial matches (e.g., "ProdHaftG", "§ 1", "2024/1689")
            ref_parts = [p for p in re.split(r'[\s,;.()-]+', ref) if len(p) > 2]
            if any(part.lower() in response for part in ref_parts):
                found += 1

        ratio = found / len(benchmark.legal_references)
        return ratio, f"Referenced {found}/{len(benchmark.legal_references)} legal sources"

    def _score_completeness(
        self, response: str, benchmark: AccuracyBenchmark
    ) -> tuple[float, str, list[str]]:
        """Score completeness by checking which key points are addressed."""
        if not benchmark.key_points:
            return 0.5, "No key points defined", []

        missing = []
        covered = 0
        for point in benchmark.key_points:
            keywords = self._extract_keywords(point.lower())
            if any(kw in response for kw in keywords if len(kw) > 3):
                covered += 1
            else:
                missing.append(point)

        ratio = covered / len(benchmark.key_points)
        return ratio, f"{covered}/{len(benchmark.key_points)} points addressed", missing

    def _score_nuance(self, response: str) -> tuple[float, str]:
        """Score nuance handling by detecting qualifying language."""
        matches = sum(1 for p in self.NUANCE_PATTERNS if re.search(p, response))
        score = min(1.0, matches / 3)  # 3+ nuance markers = full score
        return score, f"Found {matches} nuance/qualifying markers"

    def _score_safety(self, response: str) -> tuple[float, str, list[str]]:
        """Score safety by detecting harmful absolute statements."""
        found_harms = []
        for pattern in self.HARMFUL_PATTERNS:
            match = re.search(pattern, response)
            if match:
                found_harms.append(match.group())

        score = 1.0 if not found_harms else max(0.0, 1.0 - 0.3 * len(found_harms))
        expl = "No harmful patterns detected" if not found_harms else f"Found {len(found_harms)} harmful patterns"
        return score, expl, found_harms

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        """Extract meaningful keywords from text, filtering stop words."""
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "shall",
            "can", "need", "dare", "ought", "used", "to", "of", "in",
            "for", "on", "with", "at", "by", "from", "as", "into",
            "through", "during", "before", "after", "above", "below",
            "between", "out", "off", "over", "under", "again", "further",
            "then", "once", "and", "but", "or", "nor", "not", "so", "yet",
            "both", "either", "neither", "each", "every", "all", "any",
            "few", "more", "most", "other", "some", "such", "no", "only",
            "own", "same", "than", "too", "very", "just", "because",
            "this", "that", "these", "those", "it", "its",
        }
        words = re.findall(r'[a-zäöüß]{3,}', text.lower())
        return [w for w in words if w not in stop_words]
