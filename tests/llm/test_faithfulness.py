"""
Faithfulness Metric Tests.

Tests that evaluate whether LLM-generated answers are faithful to
(i.e., entailed by) the provided retrieval context.

Faithfulness is critical for RAG (Retrieval-Augmented Generation) systems
where answers should only contain information present in the source context.

Clean Architecture: Testing layer (LLM evaluation — Faithfulness)
"""

import pytest
from deepeval.test_case import LLMTestCase


class TestFaithfulness:
    """
    Test suite for Faithfulness metric.

    Faithfulness measures whether all claims in the generated answer
    are supported by the provided context. A high score means minimal
    hallucination — the model sticks to the provided facts.
    """

    @pytest.mark.llm
    @pytest.mark.llm_faithfulness
    def test_faithful_answer_within_context(
        self, faithfulness_metric, sample_qa_pairs
    ):
        """
        Answers that only use information from the context should pass.

        Given context that fully supports the answer, faithfulness
        should be high.
        """
        qa = sample_qa_pairs[0]

        test_case = LLMTestCase(
            input=qa["question"],
            actual_output=qa["answer"],
            context=[qa["context"]],
        )

        faithfulness_metric.measure(test_case)
        assert faithfulness_metric.is_passed(), (
            f"Faithfulness score {faithfulness_metric.score:.2f} "
            f"is below threshold {faithfulness_metric.threshold:.2f}. "
            f"Reason: {faithfulness_metric.reason}"
        )

    @pytest.mark.llm
    @pytest.mark.llm_faithfulness
    def test_faithful_technical_answer(
        self, faithfulness_metric, sample_qa_pairs
    ):
        """
        Technical answers grounded in context should be faithful.

        Tests faithfulness with scientific/technical content.
        """
        qa = sample_qa_pairs[1]  # Photosynthesis

        test_case = LLMTestCase(
            input=qa["question"],
            actual_output=qa["answer"],
            context=[qa["context"]],
        )

        faithfulness_metric.measure(test_case)
        assert faithfulness_metric.is_passed(), (
            f"Faithfulness score {faithfulness_metric.score:.2f} "
            f"is below threshold {faithfulness_metric.threshold:.2f}. "
            f"Reason: {faithfulness_metric.reason}"
        )

    @pytest.mark.llm
    @pytest.mark.llm_faithfulness
    def test_hallucinated_answer_fails_faithfulness(self, faithfulness_metric):
        """
        Answers containing information NOT in the context should fail.

        This negative test verifies the metric catches hallucinations.
        """
        context = "The sky is blue during the day because of Rayleigh scattering."

        test_case = LLMTestCase(
            input="Why is the sky blue?",
            actual_output=(
                "The sky is blue during the day because of Rayleigh scattering. "
                "Additionally, NASA confirmed in 2025 that aliens prefer blue skies, "
                "which is why Earth was chosen as their vacation destination."
            ),
            context=[context],
        )

        faithfulness_metric.measure(test_case)
        # The hallucinated second sentence should cause a failure
        assert not faithfulness_metric.is_passed(), (
            f"Expected low faithfulness for hallucinated content, but got score "
            f"{faithfulness_metric.score:.2f}. The metric may not be detecting hallucinations."
        )

    @pytest.mark.llm
    @pytest.mark.llm_faithfulness
    def test_partial_hallucination_detected(self, faithfulness_metric):
        """
        Partial hallucinations (mixing facts with fabrications) should be detected.

        Tests that the metric can catch subtle hallucinations mixed with
        factual content.
        """
        context = (
            "Paris is the capital of France. It has a population of about 2 million "
            "within the city limits. The Seine river flows through the city."
        )

        test_case = LLMTestCase(
            input="Tell me about Paris.",
            actual_output=(
                "Paris is the capital of France with a population of about 2 million. "
                "The Seine river flows through it. The Eiffel Tower was built in 1887 "
                "by aliens from Mars to serve as a communication antenna."
            ),
            context=[context],
        )

        faithfulness_metric.measure(test_case)
        # The fabricated alien claim should cause faithfulness to drop
        assert not faithfulness_metric.is_passed(), (
            f"Expected low faithfulness for partially hallucinated content, "
            f"but got score {faithfulness_metric.score:.2f}."
        )
