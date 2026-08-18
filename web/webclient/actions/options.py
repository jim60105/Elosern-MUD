"""Exact ``options.dismiss`` action: payload validator and thin eviction adapter.

``options.dismiss`` is the player-facing "clear AI 建議" control: the payload is
exactly the empty object, and the adapter calls the trigger service's
``evict(session, actor)`` with the dispatcher-held session (the unified
three-parameter adapter ABI). The adapter never sends: it declares
``affected_panels=("context_actions",)`` so the normal dispatcher completion
publication — the single send — renders ``suggestions.status="unavailable"``
from the mutated session state. ``evict`` itself is state-only by contract
(design D1); duplicating eviction semantics here would create a second writer
of options state.
"""

from typing import Any

from server import option_proposal_service as _options_service

# Stable rejection for an eviction failure; the adapter never raises.
_EVICT_REJECTED_CODE = "dismiss_failed"
_EVICT_REJECTED_MESSAGE = "無法清除建議，請稍後再試"


class OptionsActionError(ValueError):
    """An options action payload violates its exact bounded schema."""


def validate_options_dismiss_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate the exact empty ``options.dismiss`` payload."""
    if not isinstance(payload, dict):
        raise OptionsActionError("options.dismiss payload must be an object")
    if payload:
        raise OptionsActionError("options.dismiss requires an empty payload")
    return {}


def _dismiss_adapter(
    actor: Any, payload: dict[str, Any], session: Any = None
) -> dict[str, Any]:
    """Dismiss the session's displayed suggestions through the trigger service.

    Calls ``evict(session, actor)`` with the dispatcher-held session and
    declares ``context_actions`` affected so the completion publication renders
    the now-``unavailable`` options state exactly once. A failing eviction maps
    to a stable rejection, never raises.
    """
    del payload
    try:
        evicted = _options_service.evict(session, actor)
    except Exception:
        return {
            "outcome": "rejected",
            "code": _EVICT_REJECTED_CODE,
            "message": _EVICT_REJECTED_MESSAGE,
        }
    if not evicted:
        # evict is failure-silent by contract; a False result means the
        # session's state was not cleared and must not report success.
        return {
            "outcome": "rejected",
            "code": _EVICT_REJECTED_CODE,
            "message": _EVICT_REJECTED_MESSAGE,
        }
    return {
        "outcome": "success",
        "code": "dismissed",
        "message": "已清除 AI 建議",
        "affected_panels": ("context_actions",),
    }
