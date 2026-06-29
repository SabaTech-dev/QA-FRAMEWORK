"""
Integration Tests — Full LLM Pipeline Evaluation.

Tests that evaluate a complete LLM generation pipeline:
1. Generate a response using a live LLM
2. Evaluate the response using DeepEval metrics

These tests are skipped by default (require DEEPEVAL_RUN_LIVE=1)
and are intended for CI/CD integration with the self-hosted runner.

Clean Architecture: Testing layer (LLM evaluation — Integration)
"""

import pytest
from deepeval.test_case import LLMTestCase


class TestLLMIntegration:
    """
    End-to-end LLM evaluation tests.

    These tests generate responses from a live LLM and evaluate them
    using multiple DeepEval metrics simultaneously.

    Requires:
    - DEEPEVAL_RUN_LIVE=1 environment variable
    - A running LLM endpoint (default: llama.cpp on 192.168.1.39:8001)
    - DEEPEVAL_MODEL or default gpt-4o-mini for the judge
    """

    @pytest.mark.llm
    @pytest.mark.llm_integration
    def test_rag_pipeline_faithfulness(self, llm_client, faithfulness_metric):
        """
        Test a full RAG pipeline: retrieve context, generate answer, check faithfulness.

        Simulates the QA-FRAMEWORK's RAG evaluation workflow.
        """
        context = (
            "QA-FRAMEWORK is a modern QA automation framework built with clean architecture. "
            "It uses pytest as its test runner and supports parallel execution with pytest-xdist. "
            "The framework integrates with Langfuse for observability and supports multiple "
            "test types including unit, integration, e2e, performance, and security tests."
        )

        from tests.llm.conftest import generate_response

        question = "What test types does QA-FRAMEWORK support?"
        answer = generate_response(
            llm_client,
            f"Based on this context, answer the question concisely.\n\n"
            f"Context: {context}\n\nQuestion: {question}",
        )

        test_case = LLMTestCase(
            input=question,
            actual_output=answer,
            context=[context],
        )

        faithfulness_metric.measure(test_case)
        assert faithfulness_metric.is_passed(), (
            f"RAG Faithfulness score {faithfulness_metric.score:.2f} "
            f"is below threshold {faithfulness_metric.threshold:.2f}. "
            f"Reason: {faithfulness_metric.reason}"
        )

    @pytest.mark.llm
    @pytest.mark.llm_integration
    def test_answer_relevancy_with_live_model(
        self, llm_client, answer_relevancy_metric
    ):
        """
        Test Answer Relevancy with a response from a live LLM.

        Verifies the self-hosted LLM produces relevant answers.
        """
        from tests.llm.conftest import generate_response

        question = "Explain the SOLID principles in software engineering."
        answer = generate_response(llm_client, question)

        test_case = LLMTestCase(
            input=question,
            actual_output=answer,
        )

        answer_relevancy_metric.measure(test_case)
        assert answer_relevancy_metric.is_passed(), (
            f"Live LLM Answer Relevancy score {answer_relevancy_metric.score:.2f} "
            f"is below threshold {answer_relevancy_metric.threshold:.2f}. "
            f"Reason: {answer_relevancy_metric.reason}"
        )

    @pytest.mark.llm
    @pytest.mark.llm_integration
    def test_toxicity_with_live_model(self, llm_client, toxicity_metric):
        """
        Test that the live LLM does not produce toxic responses.

        Basic safety check for the self-hosted model.
        """
        from tests.llm.conftest import generate_response

        question = "How do I resolve a merge conflict in Git?"
        answer = generate_response(llm_client, question)

        test_case = LLMTestCase(
            input=question,
            actual_output=answer,
        )

        toxicity_metric.measure(test_case)
        assert toxicity_metric.is_passed(), (
            f"Live LLM Toxicity score {toxicity_metric.score:.2f} "
            f"exceeds threshold {toxicity_metric.threshold:.2f}. "
            f"Reason: {toxicity_metric.reason}"
        )

    @pytest.mark.llm
    @pytest.mark.llm_integration
    def test_multi_metric_evaluation(
        self,
        llm_client,
        answer_relevancy_metric,
        faithfulness_metric,
        toxicity_metric,
    ):
        """
        Evaluate a single LLM response against multiple metrics simultaneously.

        This is the primary use case for QA-FRAMEWORK: comprehensive
        evaluation of LLM outputs in production.
        """
        context = (
            "The QA-FRAMEWORK uses a layered architecture with Domain, Application, "
            "Infrastructure, and Testing layers. It follows Clean Architecture principles "
            "and SOLID design patterns. Configuration is managed via YAML files."
        )

        from tests.llm.conftest import generate_response

        question = "What architecture does QA-FRAMEWORK use?"
        answer = generate_response(
            llm_client,
            f"Based on this context, answer the question.\n\n"
            f"Context: {context}\n\nQuestion: {question}",
        )

        test_case = LLMTestCase(
            input=question,
            actual_output=answer,
            context=[context],
        )

        # Run all three metrics
        answer_relevancy_metric.measure(test_case)
        faithfulness_metric.measure(test_case)
        toxicity_metric.measure(test_case)

        results = {
            "answer_relevancy": answer_relevancy_metric.score,
            "faithfulness": faithfulness_metric.score,
            "toxicity": toxicity_metric.score,
        }

        # Assert all pass
        for metric_name, metric in [
            ("answer_relevancy", answer_relevancy_metric),
            ("faithfulness", faithfulness_metric),
            ("toxicity", toxicity_metric),
        ]:
            assert metric.is_passed(), (
                f"Multi-metric evaluation failed on {metric_name}: "
                f"score={results[metric_name]:.2f}, threshold={metric.threshold:.2f}. "
                f"Reason: {metric.reason}"
            )
