"""
GEval (Custom Criteria) Metric Tests.

Tests that use DeepEval's GEval metric to evaluate LLM outputs
against custom evaluation criteria defined in natural language.

GEval is flexible — you define WHAT to evaluate and HOW, and the
LLM judge assesses the output accordingly.

Clean Architecture: Testing layer (LLM evaluation — GEval custom criteria)
"""

import pytest
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase


class TestGEval:
    """
    Test suite for GEval custom evaluation criteria.

    GEval allows defining arbitrary evaluation criteria. Each test
    here defines a specific quality aspect to evaluate.
    """

    @pytest.fixture
    def clarity_metric(self, deepeval_model_config, geval_threshold):
        """GEval metric for evaluating response clarity."""
        return GEval(
            name="Clarity",
            criteria="The response should be clear, well-structured, and easy to understand. "
            "It should avoid jargon when simple words suffice, use proper grammar, "
            "and be logically organized.",
            evaluation_params=[
                LLMTestCase(
                    input="What is the capital of France?",
                    actual_output="Paris.",
                ),
                LLMTestCase(
                    input="What is the capital of France?",
                    actual_output=(
                        "Well, you know, France has this city, and it might be Paris, "
                        "or maybe not, it's hard to say really, depends on what you mean "
                        "by capital anyway, so yeah."
                    ),
                ),
            ],
            model=deepeval_model_config["model"],
            threshold=geval_threshold,
            **(
                {"base_url": deepeval_model_config["base_url"]}
                if "base_url" in deepeval_model_config
                else {}
            ),
        )

    @pytest.fixture
    def conciseness_metric(self, deepeval_model_config, geval_threshold):
        """GEval metric for evaluating response conciseness."""
        return GEval(
            name="Conciseness",
            criteria="The response should be concise and to the point without unnecessary "
            "repetition or filler content. It should provide the essential information "
            "efficiently.",
            evaluation_params=[
                LLMTestCase(
                    input="Is water wet?",
                    actual_output="Yes.",
                ),
                LLMTestCase(
                    input="Is water wet?",
                    actual_output=(
                        "Well, let me think about this. Water, as a substance, when it "
                        "comes into contact with surfaces, tends to make those surfaces "
                        "wet. So, in that sense, one could say that water is indeed wet. "
                        "The scientific community generally agrees that water exhibits "
                        "wetting properties."
                    ),
                ),
            ],
            model=deepeval_model_config["model"],
            threshold=geval_threshold,
            **(
                {"base_url": deepeval_model_config["base_url"]}
                if "base_url" in deepeval_model_config
                else {}
            ),
        )

    @pytest.mark.llm
    @pytest.mark.llm_geval
    def test_clear_explanation_passes_clarity(
        self, clarity_metric, sample_qa_pairs
    ):
        """
        A clear, well-structured explanation should pass the clarity metric.
        """
        qa = sample_qa_pairs[0]

        test_case = LLMTestCase(
            input=qa["question"],
            actual_output=qa["answer"],
        )

        clarity_metric.measure(test_case)
        assert clarity_metric.is_passed(), (
            f"Clarity score {clarity_metric.score:.2f} "
            f"is below threshold {clarity_metric.threshold:.2f}. "
            f"Reason: {clarity_metric.reason}"
        )

    @pytest.mark.llm
    @pytest.mark.llm_geval
    def test_concise_response_passes_conciseness(
        self, conciseness_metric, sample_qa_pairs
    ):
        """
        A concise, factual response should pass the conciseness metric.
        """
        qa = sample_qa_pairs[2]  # Pythagorean theorem (concise answer)

        test_case = LLMTestCase(
            input=qa["question"],
            actual_output=qa["answer"],
        )

        conciseness_metric.measure(test_case)
        assert conciseness_metric.is_passed(), (
            f"Conciseness score {conciseness_metric.score:.2f} "
            f"is below threshold {conciseness_metric.threshold:.2f}. "
            f"Reason: {conciseness_metric.reason}"
        )

    @pytest.mark.llm
    @pytest.mark.llm_geval
    def test_accuracy_custom_metric(self, deepeval_model_config, geval_threshold):
        """
        Custom GEval metric for factual accuracy.

        Tests that the model correctly evaluates factual claims.
        """
        accuracy_metric = GEval(
            name="Factual Accuracy",
            criteria="The response should contain only factually accurate information. "
            "Any incorrect claims, wrong numbers, or false attributions should result "
            "in a low score.",
            evaluation_params=[
                LLMTestCase(
                    input="What is 2+2?",
                    actual_output="4",
                ),
                LLMTestCase(
                    input="What is 2+2?",
                    actual_output="5",
                ),
            ],
            model=deepeval_model_config["model"],
            threshold=geval_threshold,
            **(
                {"base_url": deepeval_model_config["base_url"]}
                if "base_url" in deepeval_model_config
                else {}
            ),
        )

        test_case = LLMTestCase(
            input="What is 2+2?",
            actual_output="The sum of 2 and 2 is 4.",
        )

        accuracy_metric.measure(test_case)
        assert accuracy_metric.is_passed(), (
            f"Accuracy score {accuracy_metric.score:.2f} "
            f"is below threshold {accuracy_metric.threshold:.2f}. "
            f"Reason: {accuracy_metric.reason}"
        )
