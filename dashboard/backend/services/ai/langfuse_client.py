"""Langfuse Tracing Client — Central configuration for LLM observability."""
import os
from typing import Optional
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler as LangchainCallbackHandler
import structlog

logger = structlog.get_logger()

_langfuse_client: Optional[Langfuse] = None
_langchain_handler: Optional[LangchainCallbackHandler] = None


def get_langfuse_client() -> Optional[Langfuse]:
    """Get or create Langfuse client singleton."""
    global _langfuse_client
    if _langfuse_client is None:
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        host = os.getenv("LANGFUSE_HOST", "http://localhost:3001")
        
        if not public_key or not secret_key:
            logger.warning("langfuse_keys_missing_tracing_disabled")
            return None
        
        _langfuse_client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )
        logger.info("langfuse_client_initialized", host=host)
    
    return _langfuse_client


def get_langchain_handler() -> Optional[LangchainCallbackHandler]:
    """Get Langchain callback handler for Langfuse tracing."""
    global _langchain_handler
    if _langchain_handler is None:
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        host = os.getenv("LANGFUSE_HOST", "http://localhost:3001")
        
        if not public_key or not secret_key:
            return None
        
        _langchain_handler = LangchainCallbackHandler(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )
    
    return _langchain_handler


def is_tracing_enabled() -> bool:
    """Check if Langfuse tracing is configured."""
    return (
        os.getenv("LANGFUSE_PUBLIC_KEY") is not None
        and os.getenv("LANGFUSE_SECRET_KEY") is not None
    )
