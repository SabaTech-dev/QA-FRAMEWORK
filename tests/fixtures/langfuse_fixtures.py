"""
Langfuse Tracing Fixtures for QA Framework.

Provides pytest fixtures that automatically trace LLM calls during tests.
These fixtures integrate with the Langfuse observability platform to capture:
  - LLM generation traces
  - Confidence scores
  - Test metadata
  - Performance metrics

Usage:
    def test_my_generation(llm_tracer):
        generator = LLMTestGenerator()
        result = generator.generate_test(...)
        # Trace is automatically recorded

Environment:
    Set LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
    to enable tracing. Without credentials, tracing degrades gracefully.
"""

import os
import pytest
from typing import Any, Dict, Generator

from src.infrastructure.observability import LangfuseTracer, get_tracer, reset_tracer


@pytest.fixture(scope="session")
def langfuse_config() -> Dict[str, str]:
    """
    Load Langfuse configuration from environment.

    Returns:
        Dictionary with Langfuse connection settings.

    Reads:
        LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY,
        LANGFUSE_HOST, LANGFUSE_PROJECT
    """
    return {
        "public_key": os.environ.get("LANGFUSE_PUBLIC_KEY", ""),
        "secret_key": os.environ.get("LANGFUSE_SECRET_KEY", ""),
        "host": os.environ.get("LANGFUSE_HOST", "http://localhost:3001"),
        "project": os.environ.get("LANGFUSE_PROJECT", "QA-Framework"),
    }


@pytest.fixture(scope="session")
def llm_tracer(langfuse_config: Dict[str, str]) -> Generator[LangfuseTracer, None, None]:
    """
    Session-scoped Langfuse tracer for LLM call observability.

    The tracer is automatically used by LLMTestGenerator and other
    LLM-related components. When Langfuse is not configured (missing
    credentials), the tracer degrades gracefully and becomes a no-op.

    Args:
        langfuse_config: Langfuse connection configuration.

    Yields:
        LangfuseTracer instance (enabled or no-op).

    Example:
        def test_generation(llm_tracer):
            assert llm_tracer.enabled  # True if credentials configured
            generator = LLMTestGenerator()
            result = generator.generate_test(...)
            # Trace automatically recorded in Langfuse
    """
    # Create tracer with explicit config
    tracer = LangfuseTracer(
        public_key=langfuse_config["public_key"] or None,
        secret_key=langfuse_config["secret_key"] or None,
        host=langfuse_config["host"],
        project=langfuse_config["project"],
    )

    # Override singleton so all components use this configured instance
    import src.infrastructure.observability.langfuse_tracer as lt_mod
    lt_mod._tracer_instance = tracer

    yield tracer

    # Flush any pending traces at session end
    tracer.flush()


@pytest.fixture(scope="function")
def traced_llm_generator(llm_tracer: LangfuseTracer):
    """
    Provide an LLMTestGenerator with Langfuse tracing active.

    Args:
        llm_tracer: Session-scoped Langfuse tracer fixture.

    Yields:
        LLMTestGenerator instance with tracing enabled.

    Example:
        def test_generate_test(traced_llm_generator):
            requirement = {"title": "Login", "description": "User can log in"}
            result = traced_llm_generator.generate_test(
                requirement=requirement,
                framework=TestFramework.PYTEST,
                context={},
            )
            assert result is not None
            # Check trace was recorded in Langfuse
            assert llm_tracer.enabled
    """
    from src.infrastructure.test_generation.llm_adapter import LLMTestGenerator

    generator = LLMTestGenerator()
    yield generator

    # Flush traces after each test function
    if llm_tracer.enabled:
        llm_tracer.flush()


@pytest.fixture(scope="function", autouse=True)
def langfuse_trace_context(request, llm_tracer: LangfuseTracer) -> Generator[None, None, None]:
    """
    Auto-applied fixture that creates a Langfuse trace for each test.

    This wraps every test in a top-level Langfuse trace, so even
    non-LLM tests appear in the observability dashboard with test
    metadata.

    Args:
        request: pytest request fixture for test metadata.
        llm_tracer: Session-scoped tracer.
    """
    test_name = request.node.name
    test_file = str(request.fspath.basename)
    test_markers = [m.name for m in request.node.iter_markers()]

    metadata = {
        "test_name": test_name,
        "test_file": test_file,
        "test_markers": test_markers,
        "pytest_worker": os.environ.get("PYTEST_XDIST_WORKER", "master"),
    }

    with llm_tracer.trace_generation(
        name=f"test:{test_name}",
        metadata=metadata,
    ):
        yield
