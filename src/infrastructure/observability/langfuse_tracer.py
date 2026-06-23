"""
Langfuse Tracer — Singleton wrapper for Langfuse LLM observability.

Provides:
- LangfuseTracer: singleton managing the Langfuse client
- get_langfuse_handler: returns a LangChain CallbackHandler for LLM tracing
- get_langfuse_tracer: returns the singleton tracer instance

Usage:
    from src.infrastructure.observability import get_langfuse_handler, get_langfuse_tracer

    tracer = get_langfuse_tracer()
    handler = get_langfuse_handler()

    # LangChain integration:
    llm.invoke(prompt, config={"callbacks": [handler]})

    # Manual span:
    with tracer.span(name="qa-evaluation", input={"query": query}) as span:
        result = evaluate(query)
        span.update(output={"result": result})

Environment variables (LANGFUSE_*):
    LANGFUSE_PUBLIC_KEY  — public key from Langfuse project settings
    LANGFUSE_SECRET_KEY  — secret key from Langfuse project settings
    LANGFUSE_HOST        — Langfuse base URL (default: http://localhost:3001)
    LANGFUSE_PROJECT     — project name (default: default)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional
from contextlib import contextmanager
from functools import lru_cache

logger = logging.getLogger(__name__)


class _NullContext:
    """No-op context manager when Langfuse is disabled."""

    def __init__(self, **kwargs: Any) -> None:
        pass

    def __enter__(self) -> "_NullContext":
        return self

    def __exit__(self, *args: Any) -> None:
        pass

    def update(self, **kwargs: Any) -> None:
        pass


class LangfuseTracer:
    """
    Singleton wrapper around the Langfuse client.

    Activates when both LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY
    are present in the environment. Otherwise operates in no-op mode
    so the application does not crash when keys are missing.
    """

    _instance: Optional["LangfuseTracer"] = None
    _client: Optional[Any] = None
    _handler: Optional[Any] = None
    _active: bool = False

    def __new__(cls) -> "LangfuseTracer":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if self._client is not None:
            return
        self._initialize()

    def _initialize(self) -> None:
        """Initialize the Langfuse client from environment variables."""
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        host = os.getenv("LANGFUSE_HOST", "http://localhost:3001")

        if not public_key or not secret_key:
            logger.warning(
                "Langfuse tracing disabled — LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY not set"
            )
            return

        try:
            from langfuse import Langfuse  # type: ignore[import-untyped]

            self._client = Langfuse(
                public_key=public_key,
                secret_key=secret_key,
                host=host,
                enabled=True,
            )
            self._active = True
            logger.info("Langfuse tracing initialized — host=%s", host)
        except ImportError:
            logger.warning(
                "Langfuse tracing disabled — 'langfuse' package not installed. "
                "Add 'langfuse' to requirements.txt"
            )
        except Exception as exc:
            logger.error("Langfuse initialization failed: %s", exc, exc_info=True)

    @property
    def is_active(self) -> bool:
        return self._active and self._client is not None

    @property
    def client(self) -> Any:
        return self._client

    def get_handler(self) -> Any:
        """
        Return a LangChain CallbackHandler for automatic LLM call tracing.

        Returns a no-op handler if Langfuse is not active.
        """
        if not self.is_active:
            return _NullContext()

        if self._handler is None:
            try:
                from langfuse.langchain import CallbackHandler  # type: ignore[import-untyped]

                self._handler = CallbackHandler()
            except ImportError:
                logger.warning(
                    "Langfuse LangChain integration not available — "
                    "install 'langfuse' >= 2.0 for CallbackHandler"
                )
                return _NullContext()
        return self._handler

    @contextmanager
    def span(
        self,
        *,
        name: str,
        input: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """
        Create a Langfuse span for manual tracing.

        Usage:
            with tracer.span(name="qa-eval", input={"q": question}) as span:
                result = process(question)
                span.update(output={"result": result})
        """
        if not self.is_active:
            yield _NullContext()
            return

        trace = self._client.trace(
            name=name,
            input=input,
            metadata=metadata,
            session_id=session_id,
            user_id=user_id,
        )
        span_obj = trace.span(name=name, input=input)
        try:
            yield span_obj
        except Exception as exc:
            span_obj.update(output={"error": str(exc)}, level="ERROR")
            raise
        finally:
            span_obj.end()

    def flush(self) -> None:
        """Flush pending events to Langfuse."""
        if self.is_active and self._client is not None:
            self._client.flush()

    def shutdown(self) -> None:
        """Flush and shutdown the Langfuse client."""
        self.flush()
        if self.is_active and self._client is not None:
            try:
                self._client.shutdown()
            except Exception:
                pass
        self._active = False
        LangfuseTracer._instance = None
        LangfuseTracer._client = None
        LangfuseTracer._handler = None


@lru_cache(maxsize=1)
def get_langfuse_tracer() -> LangfuseTracer:
    """Get the LangfuseTracer singleton."""
    return LangfuseTracer()


def get_langfuse_handler() -> Any:
    """Get the LangChain CallbackHandler (convenience wrapper)."""
    return get_langfuse_tracer().get_handler()
