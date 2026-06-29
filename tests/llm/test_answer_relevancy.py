"""
Answer Relevancy Metric Tests.

Tests that evaluate whether LLM-generated answers are relevant
to the questions/prompts they respond to.

DeepEval's AnswerRelevancyMetric uses a technique where it generates
verifier questions from the answer and checks semantic similarity
between those and the original question.

Clean Architecture: Testing layer (LLM evaluation — Answer Relevancy)
"""

import pytest
from deepeval.test_case import LLMTestCase


class TestAnswerRelevancy:
    """
    Test suite for Answer Relevancy metric.

    Answer Relevancy measures how relevant the generated answer is
    to the original question. A high score (closer to 1.0) means the
    answer directly addresses what was asked.
    """

    @pytest.mark.llm
    @pytest.mark.llm_answer_relevancy
    def test_direct_answer_high_relevancy(
        self, answer_relevancy_metric, sample_qa_pairs
    ):
        """
        Direct, factual answers should score high on Answer Relevancy.

        Given a clear question and a direct factual answer,
        the answer relevancy score should be >= configured threshold.
        """
        qa = sample_qa_pairs[0]

        test_case = LLMTestCase(
            input=qa["question"],
            actual_output=qa["answer"],
            context=[qa["context"]] if qa.get("context") else None,
        )

        answer_relevancy_metric.measure(test_case)
        assert answer_relevancy_metric.is_passed(), (
            f"Answer Relevancy score {answer_relevancy_metric.score:.2f} "
            f"is below threshold {answer_relevancy_metric.threshold:.2f}. "
            f"Reason: {answer_relevancy_metric.reason}"
        )

    @pytest.mark.llm
    @pytest.mark.llm_answer_relevancy
    def test_technical_answer_relevancy(
        self, answer_relevancy_metric, sample_qa_pairs
    ):
        """
        Technical/scientific answers should be relevant to technical questions.

        Tests that the metric correctly evaluates technical content.
        """
        qa = sample_qa_pairs[1]  # Photosynthesis

        test_case = LLMTestCase(
            input=qa["question"],
            actual_output=qa["answer"],
            context=[qa["context"]] if qa.get("context") else None,
        )

        answer_relevancy_metric.measure(test_case)
        assert answer_relevancy_metric.is_passed(), (
            f"Answer Relevancy score {answer_relevancy_metric.score:.2f} "
            f"is below threshold {answer_relevancy_metric.threshold:.2f}. "
            f"Reason: {answer_relevancy_metric.reason}"
        )

    @pytest.mark.llm
    @pytest.mark.llm_answer_relevancy
    def test_mathematical_answer_relevancy(
        self, answer_relevancy_metric, sample_qa_pairs
    ):
        """
        Mathematical answers should be relevant to math questions.

        Tests that the metric handles formulas and notation correctly.
        """
        qa = sample_qa_pairs[2]  # Pythagorean theorem

        test_case = LLMTestCase(
            input=qa["question"],
            actual_output=qa["answer"],
            context=[qa["context"]] if qa.get("context") else None,
        )

        answer_relevancy_metric.measure(test_case)
        assert answer_relevancy_metric.is_passed(), (
            f"Answer Relevancy score {answer_relevancy_metric.score:.2f} "
            f"is below threshold {answer_relevancy_metric.threshold:.2f}. "
            f"Reason: {answer_relevancy_metric.reason}"
        )

    @pytest.mark.llm
    @pytest.mark.llm_answer_relevancy
    def test_no_answer_fails_relevancy(self, answer_relevancy_metric):
        """
        An empty or irrelevant answer should fail Answer Relevancy.

        This negative test verifies the metric catches poor responses.
        """
        test_case = LLMTestCase(
            input="What is the capital of Spain?",
            actual_output="I like pizza.",
        )

        answer_relevancy_metric.measure(test_case)
        # With an irrelevant answer, this SHOULD fail (score < threshold)
        assert not answer_relevancy_metric.is_passed(), (
            f"Expected low relevancy for irrelevant answer, but got score "
            f"{answer_relevancy_metric.score:.2f}. The metric may be too lenient."
        )
