"""
DeepEval LLM Evaluation Tests.

Pytest-style test suite for evaluating LLM outputs using DeepEval metrics.
Integrates with the QA-FRAMEWORK infrastructure for logging and configuration.

Clean Architecture: Testing layer (LLM evaluation)
"""

# Register llm marker if not already registered
import pytest

def pytest_configure(config):
    """Register custom pytest markers for LLM tests."""
    config.addinivalue_line("markers", "llm: LLM evaluation tests using DeepEval")
    config.addinivalue_line("markers", "llm_answer_relevancy: Answer relevancy metric tests")
    config.addinivalue_line("markers", "llm_faithfulness: Faithfulness metric tests")
    config.addinivalue_line("markers", "llm_toxicity: Toxicity metric tests")
    config.addinivalue_line("markers", "llm_geval: GEval (custom criteria) metric tests")
    config.addinivalue_line("markers", "llm_integration: Full pipeline LLM integration tests")
