"""
DeepEval basic test suite — answer relevance, faithfulness, semantic similarity.
Uses deepeval metrics with mock LLM outputs for initial setup validation.
"""
import pytest
from deepeval import evaluate
from deepeval.test_case import LLMTestCase
from deepeval.metrics import (
    AnswerRelevancyMetric,
    FaithfulnessMetric,
    HallucinationMetric,
)


# ── Fixtures ────────────────────────────────────────────────────────
@pytest.fixture
def sample_input():
    return "What are the key benefits of automated QA testing?"


@pytest.fixture
def sample_actual_output():
    return (
        "Automated QA testing provides several key benefits: "
        "faster feedback loops, consistent test execution, "
        "reduced manual effort, broader test coverage, "
        "and early defect detection in the development pipeline."
    )


@pytest.fixture
def sample_expected_output():
    return (
        "The main advantages of automated testing include "
        "speed, consistency, reduced human error, "
        "comprehensive coverage, and catching bugs earlier."
    )


@pytest.fixture
def sample_retrieval_context():
    return [
        "Automated QA testing accelerates the feedback loop by running tests on every commit.",
        "Consistency is improved because automated tests execute the same steps every time.",
        "Manual testing is time-consuming and error-prone compared to automated approaches.",
        "Test coverage increases when automation handles repetitive regression suites.",
        "Early defect detection reduces the cost of fixing bugs in production.",
    ]


# ── Test Cases ──────────────────────────────────────────────────────
def test_answer_relevancy(sample_input, sample_actual_output):
    """Output should be relevant to the input question."""
    test_case = LLMTestCase(
        input=sample_input,
        actual_output=sample_actual_output,
    )
    metric = AnswerRelevancyMetric(
        threshold=0.5,
        model="openai/gpt-4o-mini",
    )
    metric.measure(test_case)
    assert metric.is_successful(), f"Answer relevancy score: {metric.score}"


def test_faithfulness(
    sample_input, sample_actual_output, sample_retrieval_context
):
    """Output should be faithful to the retrieval context (no hallucinations)."""
    test_case = LLMTestCase(
        input=sample_input,
        actual_output=sample_actual_output,
        retrieval_context=sample_retrieval_context,
    )
    metric = FaithfulnessMetric(
        threshold=0.5,
        model="openai/gpt-4o-mini",
    )
    metric.measure(test_case)
    assert metric.is_successful(), f"Faithfulness score: {metric.score}"


def test_hallucination(
    sample_input, sample_actual_output, sample_retrieval_context
):
    """Output should not contain hallucinated information beyond context."""
    test_case = LLMTestCase(
        input=sample_input,
        actual_output=sample_actual_output,
        retrieval_context=sample_retrieval_context,
    )
    metric = HallucinationMetric(
        threshold=0.5,
        model="openai/gpt-4o-mini",
    )
    metric.measure(test_case)
    assert metric.is_successful(), f"Hallucination score: {metric.score}"


# ── Integration: run all metrics together ──────────────────────────
def test_deepeval_evaluate_pipeline(
    sample_input,
    sample_actual_output,
    sample_expected_output,
    sample_retrieval_context,
):
    """Run deepeval evaluate() with multiple metrics on a single test case."""
    test_case = LLMTestCase(
        input=sample_input,
        actual_output=sample_actual_output,
        expected_output=sample_expected_output,
        retrieval_context=sample_retrieval_context,
    )
    metrics = [
        AnswerRelevancyMetric(threshold=0.5, model="openai/gpt-4o-mini"),
        HallucinationMetric(threshold=0.5, model="openai/gpt-4o-mini"),
    ]
    # evaluate returns test results; we just verify it runs without error
    results = evaluate(
        test_cases=[test_case],
        metrics=metrics,
    )
    assert results is not None
