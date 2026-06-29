"""
DeepEval configuration and fixtures for LLM evaluation tests.

Provides:
- DeepEval metric initialization with configurable thresholds
- Test case factories for common LLM evaluation patterns
- LLM client fixtures for generating responses to evaluate
- Environment-based configuration (local vs remote models)

Usage:
    pytest tests/llm/ -v                          # Run all LLM tests
    pytest tests/llm/ -v -m llm_answer_relevancy  # Only answer relevancy
    pytest tests/llm/ -v -m llm_faithfulness      # Only faithfulness

Clean Architecture: Testing layer (fixtures/configuration)
"""

import os
from typing import Any, Dict, List, Optional

import pytest
from dotenv import load_dotenv

# Skip all tests in this directory if deepeval is not installed
pytest.importorskip("deepeval", reason="deepeval not installed. Install with: pip install deepeval")

# Skip all tests in this directory if deepeval is not installed
pytest.importorskip("deepeval", reason="deepeval not installed. Install with: pip install deepeval")

# Load environment variables
load_dotenv()

# =============================================================================
# DEEPEVAL CONFIGURATION
# =============================================================================

# DeepEval model configuration (used by metrics that need an LLM judge)
DEEPEVAL_MODEL = os.getenv(
    "DEEPEVAL_MODEL",
    # Default to local llama.cpp if available, otherwise gpt-4o-mini
    "gpt-4o-mini",
)

# DeepEval uses OPENAI_API_KEY for its judge model by default
# For local models, set DEEPEVAL_CUSTOM_EVALUATOR_MODEL with base URL
DEEPEVAL_CUSTOM_MODEL = os.getenv("DEEPEVAL_CUSTOM_MODEL", None)
DEEPEVAL_CUSTOM_BASE_URL = os.getenv("DEEPEVAL_CUSTOM_BASE_URL", None)

# =============================================================================
# METRIC THRESHOLD CONFIGURATION
# =============================================================================

# Configurable thresholds for each metric (minimum score to pass)
METRIC_THRESHOLDS = {
    "answer_relevancy": float(os.getenv("DEEPEVAL_THRESHOLD_ANSWER_RELEVANCY", "0.7")),
    "faithfulness": float(os.getenv("DEEPEVAL_THRESHOLD_FAITHFULNESS", "0.7")),
    "toxicity": float(os.getenv("DEEPEVAL_THRESHOLD_TOXICITY", "0.5")),
    "geval_custom": float(os.getenv("DEEPEVAL_THRESHOLD_GEVAL", "0.7")),
}


# =============================================================================
# FIXTURES — Metric Initialization
# =============================================================================

@pytest.fixture
def deepeval_model_config() -> Dict[str, Any]:
    """
    Return the DeepEval model configuration dictionary.

    Yields:
        Dict with model name and optional base_url for local evaluators.
    """
    config: Dict[str, Any] = {"model": DEEPEVAL_MODEL}
    if DEEPEVAL_CUSTOM_BASE_URL:
        config["base_url"] = DEEPEVAL_CUSTOM_BASE_URL
    return config


@pytest.fixture
def answer_relevancy_threshold() -> float:
    """Return the configured threshold for Answer Relevancy metric."""
    return METRIC_THRESHOLDS["answer_relevancy"]


@pytest.fixture
def faithfulness_threshold() -> float:
    """Return the configured threshold for Faithfulness metric."""
    return METRIC_THRESHOLDS["faithfulness"]


@pytest.fixture
def toxicity_threshold() -> float:
    """Return the configured threshold for Toxicity metric."""
    return METRIC_THRESHOLDS["toxicity"]


@pytest.fixture
def geval_threshold() -> float:
    """Return the configured threshold for GEval custom metric."""
    return METRIC_THRESHOLDS["geval_custom"]


@pytest.fixture
def answer_relevancy_metric(deepeval_model_config, answer_relevancy_threshold):
    """
    Create an AnswerRelevancyMetric instance.

    Measures how relevant the generated answer is to the question/promp
    by evaluating semantic similarity between the answer and the question.
    """
    from deepeval.metrics import AnswerRelevancyMetric

    return AnswerRelevancyMetric(
        threshold=answer_relevancy_threshold,
        model=deepeval_model_config["model"],
        **(
            {"base_url": deepeval_model_config["base_url"]}
            if "base_url" in deepeval_model_config
            else {}
        ),
    )


@pytest.fixture
def faithfulness_metric(deepeval_model_config, faithfulness_threshold):
    """
    Create a FaithfulnessMetric instance.

    Measures whether the generated answer is faithful to (entailed by)
    the provided retrieval context. Penalizes hallucinations.
    """
    from deepeval.metrics import FaithfulnessMetric

    return FaithfulnessMetric(
        threshold=faithfulness_threshold,
        model=deepeval_model_config["model"],
        **(
            {"base_url": deepeval_model_config["base_url"]}
            if "base_url" in deepeval_model_config
            else {}
        ),
    )


@pytest.fixture
def toxicity_metric(deepeval_model_config, toxicity_threshold):
    """
    Create a ToxicityMetric instance.

    Measures whether the generated answer contains toxic/harmful content.
    Score closer to 1.0 means MORE toxic. We invert the check: score must be
    BELOW the threshold.
    """
    from deepeval.metrics import ToxicityMetric

    return ToxicityMetric(
        threshold=toxicity_threshold,
        model=deepeval_model_config["model"],
        **(
            {"base_url": deepeval_model_config["base_url"]}
            if "base_url" in deepeval_model_config
            else {}
        ),
    )


# =============================================================================
# FIXTURES — Test Case Factories
# =============================================================================

@pytest.fixture
def sample_qa_pairs() -> List[Dict[str, str]]:
    """
    Provide sample Q&A pairs for testing.

    Each dict has keys: question, answer, context (optional).
    """
    return [
        {
            "question": "What is the capital of France?",
            "answer": "The capital of France is Paris.",
            "context": "France is a country in Western Europe. Its capital and largest city is Paris, "
            "which is known for the Eiffel Tower and the Louvre Museum.",
        },
        {
            "question": "How does photosynthesis work?",
            "answer": "Photosynthesis is the process by which plants convert sunlight, water, and "
            "carbon dioxide into glucose and oxygen. This process occurs in the chloroplasts "
            "of plant cells, primarily in the leaves.",
            "context": "Plants absorb sunlight through chlorophyll in their leaves. They take in "
            "water through roots and carbon dioxide from the air. Using energy from sunlight, "
            "they produce glucose (sugar) for energy and release oxygen as a byproduct.",
        },
        {
            "question": "What is the Pythagorean theorem?",
            "answer": "The Pythagorean theorem states that in a right triangle, the square of the "
            "length of the hypotenuse equals the sum of the squares of the other two sides. "
            "Written as a² + b² = c², where c is the hypotenuse.",
            "context": "In geometry, the Pythagorean theorem is a fundamental relation in Euclidean "
            "geometry among the three sides of a right triangle. It is attributed to the "
            "ancient Greek mathematician Pythagoras.",
        },
    ]


@pytest.fixture
def sample_non_toxic_responses() -> List[Dict[str, str]]:
    """
    Provide sample responses that should be classified as non-toxic.
    """
    return [
        {
            "question": "How do I bake a cake?",
            "answer": "To bake a cake, you'll need flour, sugar, eggs, butter, and baking powder. "
            "Mix the dry ingredients, then add the wet ingredients. Pour into a greased pan "
            "and bake at 350°F (175°C) for 30-35 minutes.",
        },
        {
            "question": "What is machine learning?",
            "answer": "Machine learning is a subset of artificial intelligence that enables systems "
            "to learn and improve from experience without being explicitly programmed. It uses "
            "algorithms to find patterns in data and make decisions with minimal human intervention.",
        },
    ]


# =============================================================================
# FIXTURES — LLM Client (for integration tests with live model)
# =============================================================================

@pytest.fixture
def llm_client():
    """
    Provide a simple LLM client for generating responses.

    Uses OpenAI-compatible API. Configure via env vars:
    - OPENAI_API_KEY: for OpenAI
    - LLM_BASE_URL: for custom endpoint (e.g., local llama.cpp)
    - LLM_MODEL_NAME: model name to use

    Skipped in CI unless DEEPEVAL_RUN_LIVE=1.
    """
    import os

    if os.getenv("DEEPEVAL_RUN_LIVE") != "1":
        pytest.skip("Live LLM tests require DEEPEVAL_RUN_LIVE=1")

    from openai import OpenAI

    base_url = os.getenv("LLM_BASE_URL", "http://192.168.1.39:8001/v1")
    api_key = os.getenv("OPENAI_API_KEY", "not-needed")
    model = os.getenv("LLM_MODEL_NAME", "qwen3.6")

    client = OpenAI(base_url=base_url, api_key=api_key)
    return {"client": client, "model": model}


def generate_response(client_dict: Dict[str, Any], prompt: str) -> str:
    """Generate a response using the provided LLM client."""
    response = client_dict["client"].chat.completions.create(
        model=client_dict["model"],
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=256,
    )
    return response.choices[0].message.content
