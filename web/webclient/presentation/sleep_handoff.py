"""Read-only contextual sleep-control panel (one sleeping controlled body).

The payload is the browser's authoritative selection/decision surface. Every
row is derived from committed state by ``world.rules.sleep_control``; this
presenter only freezes it into a bounded wire object. It never writes, never
chooses a candidate and never advances time.
"""

from typing import Any

from web.webclient.presentation.protocol import (
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    _require_bool,
    _require_exact_fields,
    _require_int,
    _require_str,
)
from web.webclient.presentation.registry import PanelUnavailableError

SLEEP_HANDOFF_SCHEMA_VERSION = 1
MAX_NAME_CODE_POINTS = 128
MAX_LABEL_CODE_POINTS = 256
MAX_REASON_CODE_POINTS = 256
MAX_SLEEP_ID_CODE_POINTS = 64
MAX_ROWS = 16

_ROW_FIELDS = {
    "kind",
    "identity",
    "name",
    "reserve_percent",
    "stage",
    "label",
    "enabled",
    "reason",
}


def _require_optional_str(payload: dict[str, Any], field: str, maximum: int) -> None:
    value = payload.get(field)
    if value is not None and (not isinstance(value, str) or len(value) > maximum):
        raise ProtocolValidationError(f"{field} must be bounded text or null")


def validate_sleep_handoff(payload: Any) -> dict[str, Any]:
    """Validate the exact available version-1 payload."""
    if not isinstance(payload, dict):
        raise ProtocolValidationError("sleep_handoff payload must be an object")
    _require_exact_fields(
        payload,
        "sleep_handoff",
        {
            "schema_version",
            "available",
            "owner_id",
            "controlled_body_id",
            "transition_id",
            "selection",
            "party",
            "controlled_sleep",
            "owner_sleep",
        },
        {},
    )
    version = _require_int(payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER)
    if version != SLEEP_HANDOFF_SCHEMA_VERSION:
        raise ProtocolValidationError(
            f"schema_version must be {SLEEP_HANDOFF_SCHEMA_VERSION}"
        )
    if not _require_bool(payload, "available"):
        raise ProtocolValidationError("available must be True")
    _require_int(payload, "owner_id", minimum=1, maximum=MAX_SAFE_INTEGER)
    _require_int(payload, "controlled_body_id", minimum=1, maximum=MAX_SAFE_INTEGER)
    _require_str(payload, "transition_id", maximum=MAX_SLEEP_ID_CODE_POINTS)

    selection = payload["selection"]
    if not isinstance(selection, dict):
        raise ProtocolValidationError("selection must be an object")
    _require_exact_fields(selection, "selection", {"available", "rows"}, {})
    _require_bool(selection, "available")
    rows = selection["rows"]
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        raise ProtocolValidationError("selection.rows exceeds its bound")
    for row in rows:
        if not isinstance(row, dict) or set(row) != _ROW_FIELDS:
            raise ProtocolValidationError("selection row shape is invalid")
        if row["kind"] not in ("return", "possess"):
            raise ProtocolValidationError("selection row kind is invalid")
        _require_int(row, "identity", minimum=1, maximum=MAX_SAFE_INTEGER)
        _require_str(row, "name", maximum=MAX_NAME_CODE_POINTS)
        _require_str(row, "stage", maximum=64)
        _require_str(row, "label", maximum=MAX_LABEL_CODE_POINTS)
        _require_bool(row, "enabled")
        reserve = row["reserve_percent"]
        if reserve is not None and (
            not isinstance(reserve, int) or isinstance(reserve, bool) or not 0 <= reserve <= 100
        ):
            raise ProtocolValidationError("row reserve_percent is invalid")
        _require_optional_str(row, "reason", MAX_REASON_CODE_POINTS)

    party = payload["party"]
    if not isinstance(party, dict):
        raise ProtocolValidationError("party must be an object")
    _require_exact_fields(party, "party", {"label", "enabled", "reason"}, {})
    _require_str(party, "label", maximum=MAX_LABEL_CODE_POINTS)
    _require_bool(party, "enabled")
    _require_optional_str(party, "reason", MAX_REASON_CODE_POINTS)

    controlled = payload["controlled_sleep"]
    if controlled is not None:
        if not isinstance(controlled, dict):
            raise ProtocolValidationError("controlled_sleep must be an object or null")
        _require_exact_fields(controlled, "controlled_sleep", {"sleep_id", "revision"}, {})
        _require_str(controlled, "sleep_id", maximum=MAX_SLEEP_ID_CODE_POINTS)
        _require_int(controlled, "revision", minimum=0, maximum=MAX_SAFE_INTEGER)

    owner_sleep = payload["owner_sleep"]
    if owner_sleep is not None:
        if not isinstance(owner_sleep, dict):
            raise ProtocolValidationError("owner_sleep must be an object or null")
        _require_exact_fields(
            owner_sleep,
            "owner_sleep",
            {
                "sleep_id",
                "revision",
                "generation",
                "dream_pending",
                "continuation",
                "continuation_available",
                "continuation_reason",
            },
            {},
        )
        _require_str(owner_sleep, "sleep_id", maximum=MAX_SLEEP_ID_CODE_POINTS)
        _require_int(owner_sleep, "revision", minimum=0, maximum=MAX_SAFE_INTEGER)
        _require_int(owner_sleep, "generation", minimum=0, maximum=MAX_SAFE_INTEGER)
        _require_bool(owner_sleep, "dream_pending")
        if owner_sleep["continuation"] not in (
            "none",
            "pending",
            "paused",
            "complete",
        ):
            raise ProtocolValidationError("continuation is invalid")
        _require_bool(owner_sleep, "continuation_available")
        _require_optional_str(
            owner_sleep, "continuation_reason", MAX_REASON_CODE_POINTS
        )
    return payload


def sleep_handoff_presenter(context: Any) -> dict[str, Any]:
    """Return the exact available payload while a controlled body sleeps."""
    from world.narrative.dream_surface import dream_state
    from world.rules.sleep_control import ALL_PARTY_SLEEP_LABEL, build_sleep_control_view

    view = build_sleep_control_view(context.actor)
    if view is None:
        raise PanelUnavailableError
    state = dream_state(context.actor)
    if state is not None and state.get("open"):
        # The active dream stage owns the single modal focus.
        raise PanelUnavailableError
    rows = [
        {
            "kind": row.kind,
            "identity": int(row.identity),
            "name": row.name[:MAX_NAME_CODE_POINTS],
            "reserve_percent": row.reserve_percent,
            "stage": str(row.stage)[:64],
            "label": row.label[:MAX_LABEL_CODE_POINTS],
            "enabled": bool(row.enabled),
            "reason": None if row.reason is None else str(row.reason)[:MAX_REASON_CODE_POINTS],
        }
        for row in view.rows[:MAX_ROWS]
    ]
    payload = {
        "schema_version": SLEEP_HANDOFF_SCHEMA_VERSION,
        "available": True,
        "owner_id": int(view.owner_id),
        "controlled_body_id": int(view.controlled_body_id),
        "transition_id": str(view.transition_id)[:MAX_SLEEP_ID_CODE_POINTS],
        "selection": {
            "available": bool(view.selection_available),
            "rows": rows,
        },
        "party": {
            "label": ALL_PARTY_SLEEP_LABEL,
            "enabled": bool(view.party_enabled),
            "reason": (
                None
                if view.party_reason is None
                else str(view.party_reason)[:MAX_REASON_CODE_POINTS]
            ),
        },
        "controlled_sleep": (
            None
            if view.controlled_sleep is None
            else {
                "sleep_id": view.controlled_sleep.sleep_id[:MAX_SLEEP_ID_CODE_POINTS],
                "revision": int(view.controlled_sleep.revision),
            }
        ),
        "owner_sleep": (
            None
            if view.owner_sleep is None
            else {
                "sleep_id": view.owner_sleep.sleep_id[:MAX_SLEEP_ID_CODE_POINTS],
                "revision": int(view.owner_sleep.revision),
                "generation": int(view.owner_sleep.generation),
                "dream_pending": bool(view.owner_sleep.dream_pending),
                "continuation": view.owner_sleep.continuation,
                "continuation_available": bool(
                    view.owner_sleep.continuation_available
                ),
                "continuation_reason": (
                    None
                    if view.owner_sleep.continuation_reason is None
                    else str(view.owner_sleep.continuation_reason)[
                        :MAX_REASON_CODE_POINTS
                    ]
                ),
            }
        ),
    }
    return validate_sleep_handoff(payload)


__all__ = [
    "MAX_LABEL_CODE_POINTS",
    "MAX_NAME_CODE_POINTS",
    "MAX_REASON_CODE_POINTS",
    "MAX_ROWS",
    "MAX_SLEEP_ID_CODE_POINTS",
    "SLEEP_HANDOFF_SCHEMA_VERSION",
    "sleep_handoff_presenter",
    "validate_sleep_handoff",
]
