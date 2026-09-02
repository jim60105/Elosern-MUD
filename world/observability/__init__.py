"""Observability log facade — the sole game-code log entry point.

Named-import convention (AGENTS.md): production code imports the four
functions directly (``from world.observability import log_warn``); event
assertions in tests patch the call-site module binding or capture the sink,
never ``world.observability.*``.
"""

from world.observability.api import log_debug, log_error, log_info, log_warn

__all__ = ["log_debug", "log_error", "log_info", "log_warn"]
