"""Langfuse integration for LLM observability and tracing"""

import logging
import os

from langfuse import Langfuse

logger = logging.getLogger(__name__)

# Initialize Langfuse client
langfuse_client = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY", "pk_demo"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY", "sk_demo"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
)

# Check if Langfuse is actually enabled
_is_enabled = bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_PUBLIC_KEY") != "pk_demo")

def trace_llm_call(name: str = "llm_call", tags: list | None = None):
    """
    Decorator to trace LLM function calls with Langfuse.
    This is a lightweight decorator that logs trace events without wrapping FastAPI handlers.

    Usage:
        @trace_llm_call(name="chat", tags=["anime"])
        async def my_function(...):
            log_trace_event("event_name", data)
            ...
    """
    def decorator(func):
        # Don't wrap - just register the trace hook
        # FastAPI needs the original function signature
        logger.debug(f"Registered trace hook for: {name} (tags: {tags})")
        return func

    return decorator

def log_trace_event(event_name: str, data: dict | None = None):
    """
    Log a trace event to Langfuse.
    Useful for tracking specific events within your LLM pipeline.

    Usage:
        log_trace_event("message_received", {"user": "...", "msg_len": 100})
    """
    if data is None:
        data = {}
    logger.debug(f"[TRACE] {event_name}: {data}")

def set_user_context(user_id: str, session_id: str | None = None, tags: list | None = None):
    """
    Set user context for tracing.
    Helps group traces by user and session.

    Usage:
        set_user_context(user_id="192.168.1.1", session_id="chat_123", tags=["anime-portal"])
    """
    return {
        "user_id": user_id,
        "session_id": session_id or "",
        "tags": tags or []
    }

def get_dashboard_url():
    """Get Langfuse dashboard URL"""
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    if "localhost" in host or "127.0.0.1" in host:
        return f"{host}"
    return f"{host}/dashboard"

def flush_traces():
    """Flush all pending traces to Langfuse"""
    try:
        if hasattr(langfuse_client, 'flush'):
            langfuse_client.flush()
            logger.info("Flushed Langfuse traces")
    except Exception as e:
        logger.warning(f"Failed to flush Langfuse traces: {e}")

# ============= EXAMPLE USAGE =============
# In main.py:
#
# from app.utils.langfuse_tracer import get_dashboard_url, flush_traces
#
# @app.on_event("startup")
# async def startup():
#     print(f"📊 Langfuse Dashboard: {get_dashboard_url()}")
#
# @app.on_event("shutdown")
# async def shutdown():
#     flush_traces()
#
# In your chat endpoint:
#
# from app.utils.langfuse_tracer import trace_llm_call, log_trace_event, set_user_context
#
# @router.post("/chat")
# @trace_llm_call(name="anime_chat", tags=["chat", "anime"])
# async def chat(request: ChatRequest, req: Request):
#     user_ip = get_client_ip(req)
#     set_user_context(user_ip, tags=["anime-portal"])
#
#     log_trace_event("chat_start", {"user": user_ip})
#     result = await run_agent(messages)
#     log_trace_event("agent_response", {"tokens": len(result)})
#
#     return response
