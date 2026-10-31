"""The eager ``travel_log`` panel (wilderness-travel-log-ui).

The panel carries the immutable travel notices of the causal publication group
being published (or, on a replay, the latest published batch) exactly as the
deterministic owner identified them: ``{schema_version, available, entries}``
with one closed ``{id, kind, tick, day, time, text, params}`` record per
notice. The kind/params union is closed, every bound is enforced here and in
the browser mirror (``web/static/webclient/js/elosern/protocol/panels/
travel_log.js``), and a malformed or oversize batch renders the ordinary
unavailable form instead of being trimmed into apparent validity.
"""

from typing import Any

from web.webclient.presentation.artwork import validate_artwork
from web.webclient.presentation.protocol import (
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    _require_exact_fields,
    _require_int,
    _require_str,
    json_byte_size,
)
from web.webclient.presentation.registry import PanelUnavailableError

TRAVEL_LOG_SCHEMA_VERSION = 1
MAX_ENTRIES = 64
MAX_BYTES = 65_536
MAX_ID = 80
MAX_TIME = 32
MAX_TEXT = 1_024
MAX_NAME = 256
MAX_MEMBER_ID = 64
MAX_PROSE = 2_048
MAX_NODE_ID = 128
FATIGUE_STAGES = ("normal", "light", "moderate", "severe", "sleeping", "forced_sleep")

#: The closed kind -> exact params union.
PARAM_FIELDS: dict[str, frozenset[str]] = {
    "region_entered": frozenset({"name"}),
    "woodland_entered": frozenset({"name"}),
    "ford_crossed": frozenset({"name"}),
    "hostile_sighted": frozenset({"name", "count", "threat"}),
    "landmark_sighted": frozenset({"name", "bearing", "distance_km"}),
    "landmark_reached": frozenset({"arrival_node", "name", "lit_district", "prose", "artwork"}),
    "fatigue_stage": frozenset({"member_id", "name", "stage", "label"}),
    "dusk": frozenset(),
    "nightfall": frozenset(),
    "camp_result": frozenset({"summary"}),
    "look": frozenset({"prose"}),
}

_ENTRY_FIELDS = {"id", "kind", "tick", "day", "time", "text", "params"}


def _nonblank(payload: dict[str, Any], field: str, maximum: int) -> str:
    value = _require_str(payload, field, maximum=maximum)
    if not value.strip():
        raise ProtocolValidationError(f"{field} must not be blank")
    return value


def _ascii(value: Any, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= maximum or not value.isascii():
        raise ProtocolValidationError(f"{field} must be 1..{maximum} ASCII characters")
    return value


def _optional_str(params: dict[str, Any], field: str) -> None:
    if params[field] is not None:
        _require_str(params, field, maximum=MAX_NAME)


def _validate_params(kind: str, params: Any) -> None:
    if not isinstance(params, dict) or set(params) != PARAM_FIELDS[kind]:
        raise ProtocolValidationError(f"{kind} params must be exactly {sorted(PARAM_FIELDS[kind])}")
    if kind in ("region_entered", "woodland_entered", "ford_crossed"):
        _require_str(params, "name", maximum=MAX_NAME)
    elif kind == "hostile_sighted":
        _require_str(params, "name", maximum=MAX_NAME)
        _require_int(params, "count", minimum=1, maximum=MAX_SAFE_INTEGER)
        _optional_str(params, "threat")
    elif kind == "landmark_sighted":
        _optional_str(params, "name")
        _require_str(params, "bearing", maximum=MAX_NAME)
        _require_int(params, "distance_km", minimum=0, maximum=MAX_SAFE_INTEGER)
    elif kind == "landmark_reached":
        from world.rules.map_knowledge import validate_node

        node = params["arrival_node"]
        if not isinstance(node, str) or len(node) > MAX_NODE_ID or not validate_node(node):
            raise ProtocolValidationError("arrival_node must be a canonical node id")
        _require_str(params, "name", maximum=MAX_NAME)
        _optional_str(params, "lit_district")
        _require_str(params, "prose", maximum=MAX_PROSE)
        if params["artwork"] is not None:
            validate_artwork(params["artwork"])
    elif kind == "fatigue_stage":
        _ascii(params["member_id"], "member_id", MAX_MEMBER_ID)
        _require_str(params, "name", maximum=MAX_NAME)
        if params["stage"] not in FATIGUE_STAGES:
            raise ProtocolValidationError("stage must be a canonical fatigue stage")
        _require_str(params, "label", maximum=MAX_NAME)
    elif kind == "camp_result":
        _require_str(params, "summary", maximum=MAX_NAME)
    elif kind == "look":
        _require_str(params, "prose", maximum=MAX_PROSE)


def validate_travel_log(payload: Any) -> dict[str, Any]:
    """Validate the exact available version-1 ``travel_log`` payload."""
    if not isinstance(payload, dict):
        raise ProtocolValidationError("travel_log payload must be an object")
    _require_exact_fields(payload, "travel_log", {"schema_version", "available", "entries"}, {})
    if payload["schema_version"] != TRAVEL_LOG_SCHEMA_VERSION or isinstance(payload["schema_version"], bool):
        raise ProtocolValidationError(f"schema_version must be {TRAVEL_LOG_SCHEMA_VERSION}")
    if payload["available"] is not True:
        raise ProtocolValidationError("available must be True")
    entries = payload["entries"]
    if not isinstance(entries, list) or len(entries) > MAX_ENTRIES:
        raise ProtocolValidationError("entries exceed their bound")
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != _ENTRY_FIELDS:
            raise ProtocolValidationError("travel_log entry shape is invalid")
        identity = _ascii(entry["id"], "id", MAX_ID)
        if identity in seen:
            raise ProtocolValidationError("travel_log entry ids must be unique")
        seen.add(identity)
        kind = entry["kind"]
        if kind not in PARAM_FIELDS:
            raise ProtocolValidationError("travel_log entry kind is unknown")
        _require_int(entry, "tick", minimum=0, maximum=MAX_SAFE_INTEGER)
        _require_int(entry, "day", minimum=0, maximum=MAX_SAFE_INTEGER)
        _nonblank(entry, "time", MAX_TIME)
        _nonblank(entry, "text", MAX_TEXT)
        _validate_params(kind, entry["params"])
    if json_byte_size(payload) > MAX_BYTES:
        raise ProtocolValidationError(f"travel_log exceeds {MAX_BYTES} canonical bytes")
    return payload


def travel_log_presenter(context: Any) -> dict[str, Any]:
    """Render the context's notices, or the ordinary unavailable form.

    Off the wilderness the batch is empty: a replayed earlier trip never rides
    a town snapshot.
    """
    from world.rules.travel_interrupts import wilderness_cell

    events = tuple(getattr(context, "travel_events", ()) or ())
    if events and wilderness_cell(getattr(context.actor, "location", None)) is None:
        events = ()
    payload = {
        "schema_version": TRAVEL_LOG_SCHEMA_VERSION,
        "available": True,
        "entries": [event.as_wire() for event in events],
    }
    try:
        return validate_travel_log(payload)
    except ProtocolValidationError as error:
        raise PanelUnavailableError(str(error)) from error


__all__ = [
    "FATIGUE_STAGES",
    "MAX_BYTES",
    "MAX_ENTRIES",
    "PARAM_FIELDS",
    "TRAVEL_LOG_SCHEMA_VERSION",
    "travel_log_presenter",
    "validate_travel_log",
]
