"""Shared outbound HTTP identity helper.

Provides the single source of truth for the User-Agent header across all
server outbound HTTP transports (prompt translation fetch, sd-webui worker,
and LLM client).
"""

from django.conf import settings

# Literal parity with HTTP_USER_AGENT code default in server/conf/settings.py
DEFAULT_USER_AGENT = "elosern-mud/1.0"


def http_user_agent() -> str:
    """Return the effective HTTP User-Agent string.

    Reads django.conf.settings.HTTP_USER_AGENT per-call so runtime overrides
    take effect immediately. If the setting is absent, empty, or whitespace-only,
    falls back to DEFAULT_USER_AGENT (the header must never ship empty).
    Non-blank values are returned verbatim.
    """
    value = getattr(settings, "HTTP_USER_AGENT", None)
    if not value or not str(value).strip():
        return DEFAULT_USER_AGENT
    return str(value)


def user_agent_headers() -> dict[str, str]:
    """Return a fresh header dict carrying the effective User-Agent."""
    return {"User-Agent": http_user_agent()}
