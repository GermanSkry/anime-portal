"""Product events to PostHog.

One module so every call site looks the same and none of them can break a
request: analytics is never worth a 500.
"""
import logging
import os
from contextvars import ContextVar

from fastapi import Request
from posthog import Posthog

logger = logging.getLogger(__name__)

_api_key = os.getenv("POSTHOG_API_KEY", "")
_region = os.getenv("POSTHOG_REGION", "us")
# POSTHOG_HOST overrides the region, for a self-hosted instance or a local sink
_host = os.getenv("POSTHOG_HOST") or (
    "https://eu.i.posthog.com" if _region == "eu" else "https://us.i.posthog.com"
)
_client = Posthog(_api_key, host=_host) if _api_key else None

ANONYMOUS = "anonymous"

# Who the request belongs to, so code several layers below a route — the agent,
# the web search — can attribute its events without threading a parameter down.
_visitor: ContextVar[str] = ContextVar("visitor", default=ANONYMOUS)


def set_visitor(distinct_id: str) -> None:
    """Called once per request, as early as possible."""
    _visitor.set(distinct_id or ANONYMOUS)


def current_visitor() -> str:
    return _visitor.get()


def track(distinct_id: str, event: str, **properties) -> None:
    """Send one product event. Swallows every failure, including a missing client."""
    if _client is None:
        return
    try:
        _client.capture(
            distinct_id=distinct_id or ANONYMOUS,
            event=event,
            properties={"environment": os.getenv("ENVIRONMENT", "development"), **properties},
        )
    except Exception as e:
        logger.warning(f"PostHog capture failed for {event}: {e}")


def client_id(request: Request) -> str:
    """Who to attribute an event to.

    The browser sends PostHog's own anonymous id as X-Client-Id, so a visitor's
    frontend and backend events land on the same person. Without it we fall back
    to the IP, which is what chat history is already keyed on.
    """
    header = request.headers.get("x-client-id", "").strip()
    if header:
        return header[:200]
    if request.client:
        return request.client.host
    return request.headers.get("x-forwarded-for", "unknown").split(",")[0].strip()
