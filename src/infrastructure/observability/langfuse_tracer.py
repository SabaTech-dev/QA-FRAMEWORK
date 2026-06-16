"""
Langfuse Tracing Wrapper for LLM Calls.

Provides transparent tracing of all LLM interactions in the QA Framework
via Langfuse observability platform. Each LLM call (generation, evaluation,
improvement suggestion) is automatically captured as a trace with:
  - Input prompt
  - Output response
  - Model metadata
  - Latency metrics
  - Custom metadata (test name, framework, tags)

Supports Langfuse SDK v2.x (direct API).

Usage (automatic via fixture):
    def test_my_llm_call(llm_tracer):
        generator = LLMTestGenerator()
        # Tracer is auto-injected; all generate_test calls are traced

Usage (manual):
    tracer = get_tracer()
    with tracer.trace_generation("test_gen_001") as span:
        result = generator.generate_test(...)
        span.set_output(result)

Environment variables:
    LANGFUSE_PUBLIC_KEY - Langfuse public key
    LANGFUSE_SECRET_KEY - Langfuse secret key
    LANGFUSE_HOST       - Langfuse server URL (default: http://localhost:3001)
    LANGFUSE_PROJECT    - Project name for metadata
"""

import os
import time
import uuid
import logging
from contextlib import contextmanager
from functools import wraps
from typing import Any, Dict, Generator, Optional

logger = logging.getLogger(__name__)

# Singleton tracer instance
_tracer_instance: Optional["LangfuseTracer"] = None


class LangfuseTracer:
    """
    Wrapper around Langfuse SDK v2 for tracing LLM calls in QA Framework.

    This class provides:
    1. Automatic trace creation for LLM generations
    2. Generation-level observations with I/O recording
    3. Score recording for quality metrics
    4. Graceful degradation when Langfuse is unavailable

    Attributes:
        client: Langfuse client instance (None if not initialized)
        enabled: Whether tracing is active
        project: Langfuse project name
    """

    def __init__(
        self,
        public_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        host: Optional[str] = None,
        project: Optional[str] = None,
    ):
        """
        Initialize Langfuse tracer.

        Args:
            public_key: Langfuse public key. Defaults to LANGFUSE_PUBLIC_KEY env var.
            secret_key: Langfuse secret key. Defaults to LANGFUSE_SECRET_KEY env var.
            host: Langfuse host URL. Defaults to LANGFUSE_HOST env var.
            project: Project name for metadata. Defaults to LANGFUSE_PROJECT env var.
        """
        self.public_key = public_key or os.environ.get("LANGFUSE_PUBLIC_KEY")
        self.secret_key = secret_key or os.environ.get("LANGFUSE_SECRET_KEY")
        self.host = host or os.environ.get("LANGFUSE_HOST", "http://localhost:3001")
        self.project = project or os.environ.get("LANGFUSE_PROJECT", "QA-Framework")
        self.client = None
        self.enabled = False

        self._init_client()

    def _init_client(self) -> None:
        """Initialize Langfuse client if credentials are available."""
        if not self.public_key or not self.secret_key:
            logger.warning(
                "Langfuse credentials not found. "
                "Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY to enable tracing."
            )
            return

        try:
            from langfuse import Langfuse

            self.client = Langfuse(
                public_key=self.public_key,
                secret_key=self.secret_key,
                host=self.host,
            )
            self.enabled = True
            logger.info(
                "Langfuse tracing initialized: host=%s project=%s",
                self.host,
                self.project,
            )
        except ImportError:
            logger.warning(
                "langfuse package not installed. "
                "Install with: pip install langfuse"
            )
        except Exception as exc:
            logger.warning("Failed to initialize Langfuse client: %s", exc)

    @contextmanager
    def trace_generation(
        self,
        name: str = "llm_generation",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Generator["_TraceContext", None, None]:
        """
        Context manager for tracing an LLM generation call.

        Creates a Langfuse trace with a nested generation observation.

        Args:
            name: Name for the trace (e.g., test name or operation).
            metadata: Additional metadata to attach.

        Yields:
            _TraceContext: Context object for recording I/O.

        Example:
            with tracer.trace_generation("test_login") as ctx:
                ctx.set_input(prompt)
                result = llm_generate(prompt)
                ctx.set_output(result)
        """
        ctx = _TraceContext(self, name, metadata)
        start_time = time.time()

        try:
            yield ctx
        except Exception as exc:
            ctx.set_error(exc)
            raise
        finally:
            elapsed = time.time() - start_time
            ctx._finish(elapsed)

    def trace_llm_call(
        self,
        operation: str = "generate_test",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Decorator for automatic tracing of LLM methods.

        Args:
            operation: Operation name for the trace.
            metadata: Additional static metadata.

        Returns:
            Decorator that wraps the function with tracing.
        """

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                trace_name = f"{operation}:{func.__name__}"
                func_meta = {"operation": operation, "function": func.__name__}

                if args and isinstance(args, dict):
                    func_meta["requirement_title"] = args.get("title", "unknown")

                func_meta.update(metadata or {})

                with self.trace_generation(trace_name, func_meta) as ctx:
                    ctx.set_input({
                        "args": _safe_serialize(args[1:] if args else []),
                        "kwargs": _safe_serialize(kwargs),
                    })

                    result = func(*args, **kwargs)

                    ctx.set_output(_safe_serialize(result))

                    return result

            return wrapper

        return decorator

    def record_score(
        self,
        trace_id: Optional[str],
        name: str,
        value: float,
        comment: Optional[str] = None,
    ) -> None:
        """
        Record a quality score for a trace.

        Args:
            trace_id: Langfuse trace ID.
            name: Score name (e.g., "confidence", "quality").
            value: Score value (0.0 to 1.0).
            comment: Optional comment.
        """
        if not self.enabled or not self.client or not trace_id:
            return

        try:
            self.client.score(
                trace_id=trace_id,
                name=name,
                value=value,
                comment=comment or "",
            )
        except Exception as exc:
            logger.debug("Failed to record Langfuse score: %s", exc)

    def flush(self) -> None:
        """Flush any pending traces to Langfuse."""
        if self.enabled and self.client:
            try:
                self.client.flush()
            except Exception as exc:
                logger.debug("Failed to flush Langfuse: %s", exc)


class _TraceContext:
    """Internal context for a single trace + generation observation."""

    def __init__(
        self,
        tracer: LangfuseTracer,
        name: str,
        metadata: Optional[Dict[str, Any]],
    ):
        self._tracer = tracer
        self._name = name
        self._input: Any = None
        self._output: Any = None
        self._error: Optional[Exception] = None
        self._trace = None
        self._generation = None

        full_meta = {
            "project": tracer.project,
            "source": "qa-framework",
            **(metadata or {}),
        }

        if tracer.enabled and tracer.client:
            try:
                self._trace = tracer.client.trace(
                    id=str(uuid.uuid4()),
                    name=name,
                    metadata=full_meta,
                )
                self._generation = self._trace.generation(
                    name=name,
                    model="mock-gpt-4",
                )
            except Exception as exc:
                logger.debug("Failed to create Langfuse trace: %s", exc)

    def set_input(self, data: Any) -> None:
        """Record input data for this generation."""
        self._input = data
        if self._generation:
            try:
                self._generation.update(input=_safe_serialize(data))
            except Exception:
                pass

    def set_output(self, data: Any) -> None:
        """Record output data for this generation."""
        self._output = data
        if self._generation:
            try:
                self._generation.update(output=_safe_serialize(data))
            except Exception:
                pass

    def set_error(self, exc: Exception) -> None:
        """Record an error for this generation."""
        self._error = exc
        if self._generation:
            try:
                self._generation.update(
                    level="ERROR",
                    status_message=str(exc),
                    metadata={"error_type": type(exc).__name__},
                )
            except Exception:
                pass

    def set_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the trace."""
        if self._trace:
            try:
                self._trace.update(metadata={key: _safe_serialize(value)})
            except Exception:
                pass

    @property
    def trace_id(self) -> Optional[str]:
        """Get the Langfuse trace ID."""
        if self._trace:
            return getattr(self._trace, "id", None)
        return None

    def _finish(self, elapsed_seconds: float) -> None:
        """Finish the generation with timing info."""
        if self._generation:
            try:
                self._generation.update(
                    metadata={
                        "elapsed_seconds": elapsed_seconds,
                        "status": "error" if self._error else "success",
                    }
                )
            except Exception:
                pass


def _safe_serialize(obj: Any) -> Any:
    """Safely serialize an object for Langfuse recording."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _safe_serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe_serialize(item) for item in obj]
    if hasattr(obj, "__dict__"):
        try:
            return {
                k: _safe_serialize(v)
                for k, v in vars(obj).items()
                if not k.startswith("_")
            }
        except Exception:
            pass
    return str(obj)


def get_tracer() -> LangfuseTracer:
    """
    Get the singleton LangfuseTracer instance.

    Returns:
        LangfuseTracer instance (enabled or disabled based on env vars).
    """
    global _tracer_instance
    if _tracer_instance is None:
        _tracer_instance = LangfuseTracer()
    return _tracer_instance


def reset_tracer() -> None:
    """Reset the singleton tracer (useful for testing)."""
    global _tracer_instance
    if _tracer_instance:
        _tracer_instance.flush()
    _tracer_instance = None
