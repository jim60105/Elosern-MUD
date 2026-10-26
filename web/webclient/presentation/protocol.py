"""Exact version-1 OOB envelope schema, bounds, and JSON-safety checks.

Every Elosern OOB message travels as exactly one JSON object in the first
positional argument of Evennia's ``["command", args, kwargs]`` transport
triple. This module is the single source of truth for the envelope field sets
and the global bound table described in the WebClient OOB design. It is pure
Python: it never touches a Session, an actor, or persistent state.
"""

from base64 import urlsafe_b64encode
from dataclasses import dataclass
from functools import partial
import json
import math
import os
import re
from typing import Any

# Message names on the wire.
UI_SYNC = "ui_sync"
UI_ACTION = "ui_action"
UI_SNAPSHOT = "ui_snapshot"
UI_UPDATE = "ui_update"
UI_ACTION_RESULT = "ui_action_result"
UI_PROTOCOL_ERROR = "ui_protocol_error"
# One bounded part of a logical snapshot/delta that cannot travel intact.
UI_PUBLICATION_PART = "ui_publication_part"

# The only protocol schema shipped by this delivery unit.
PROTOCOL_VERSION = 1

# Global JSON-safety and bound table (design D1). Field-specific limits must be
# equal or smaller than these ceilings. Depth 12 accommodates the nested
# ``context_actions`` v3 shape (envelope → panels → panel → skills → category
# → groups → skill group → skills → descriptor → cost/freeform_scales), whose
# deepest legitimate leaf sits at depth 11. The list-item ceiling clears the
# largest legitimate flat panel list: the ``context_actions`` exploration
# form's affordance array (at most ``MAX_CONTEXT_AFFORDANCES`` = 320 entries).
MAX_CANONICAL_JSON_BYTES = 65_536
MAX_DEPTH = 12
MAX_FIELDS = 64
MAX_LIST_ITEMS = 320
MAX_STRING_CODE_POINTS = 2_048
MAX_SAFE_INTEGER = 9_007_199_254_740_991

# Envelope-level bounds.
MAX_REQUEST_ID = 64
MAX_IDENTIFIER = 64
MAX_PANEL_NAME = 64
MAX_PANEL_COUNT = 32
# The update-only removal list is bounded by the same panel ceiling.
MAX_REMOVED_PANELS = MAX_PANEL_COUNT
MAX_MESSAGE_CODE_POINTS = 512
MAX_CORRELATION_ID = 32
CORRELATION_ID_LENGTH = 32
MAX_LAYOUT_VERSION = 65_535

# Dialogue v3 panel and envelope publication bounds.
DIALOGUE_PANEL = "dialogue"
DIALOGUE_PANEL_MAX_BYTES = 24_576
DIALOGUE_ENVELOPE_MAX_BYTES = 98_304
DIALOGUE_SCENE_MAX_BYTES = 8_192
DIALOGUE_DELIVERY_BUNDLE_MAX_BYTES = 16_384
DIALOGUE_BUNDLE_MAX_BYTES = 16_384

# Adapter data slot (ui_action_result success only): a result value is not a
# panel, so it caps at eight fields. The byte budget is the global canonical
# envelope ceiling minus the reserve RESULT_DATA_STANDARD_RESERVE, the exact
# worst-case serialized size of a seven-field success envelope at its field
# maximums (2,345 bytes: a 512-code-point message of 4-byte code points is
# 2,048 UTF-8 bytes alone) plus the 8-byte `,"data":` delimiter. A
# budget-legal slot therefore can never push an emitted envelope over
# MAX_CANONICAL_JSON_BYTES; the bound tests pin both terms.
RESULT_DATA_STANDARD_RESERVE = 2_345 + 8
MAX_RESULT_DATA_FIELDS = 8
MAX_RESULT_DATA_BYTES = MAX_CANONICAL_JSON_BYTES - RESULT_DATA_STANDARD_RESERVE

# State-identity and diagnostic key names an adapter data slot must never
# carry, at any nesting level. The forbidden-content guarantee is enforced as
# (1) this recursive reserved-key rule, (2) JSON-safety rejecting live objects
# and exceptions structurally, and (3) the reserved rule matching dot-segment
# heads so ``session.id``-style nesting cannot smuggle a reserved head either.
FORBIDDEN_RESULT_DATA_KEYS = frozenset(
    {
        "actor",
        "session",
        "epoch",
        "revision",
        "presentation_epoch",
        "presentation_revision",
        "correlation_id",
        "exception",
        "traceback",
        "local_path",
    }
)

# Epoch form: exactly 22 URL-safe ASCII characters from 128 random bits.
EPOCH_LENGTH = 22

MODES = ("creation", "exploration", "combat", "dialogue")
OUTCOMES = ("success", "rejected", "stale", "error")
PROTOCOL_ERROR_CODES = (
    "unsupported_version",
    "presentation_unavailable",
    "internal_error",
    "malformed_envelope",
    "no_puppet",
)
# Codes whose protocol error envelope must carry a correlation ID.
PROTOCOL_ERROR_CORRELATED_CODES = ("internal_error",)

SEASON_LABEL_MAX = 32
SEASON_INDEX_MIN, SEASON_INDEX_MAX = 0, 3
DAY_IN_SEASON_MIN, DAY_IN_SEASON_MAX = 1, 90
HOUR_MIN, HOUR_MAX = 0, 23
MINUTE_MIN, MINUTE_MAX = 0, 59
SECOND_MIN, SECOND_MAX = 0, 59

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9:_-]{1,64}$")
_IDENTIFIER_RE = re.compile(r"^[a-z0-9._]{1,64}$")
_PANEL_NAME_RE = re.compile(r"^[a-z0-9_]{1,64}$")
_CORRELATION_RE = re.compile(r"^[0-9a-f]{32}$")
_SEASON_LABEL_RE = re.compile(r"^[\s\S]{1,32}$")

# The server messages that a client may synchronize or act against, and the
# client messages the server accepts. Used by the input-function boundary.
CLIENT_MESSAGES = frozenset({UI_SYNC, UI_ACTION})
SERVER_MESSAGES = frozenset(
    {UI_SNAPSHOT, UI_UPDATE, UI_ACTION_RESULT, UI_PROTOCOL_ERROR, UI_PUBLICATION_PART}
)


class ProtocolError(ValueError):
    """Raised when an envelope violates the exact version-1 schema."""


class ProtocolValidationError(ProtocolError):
    """A single envelope field violates its exact schema or a global bound."""


class JSONSafetyError(ProtocolValidationError):
    """The payload exceeds the global depth, count, length, or size bounds."""


def _code_points(value: str) -> int:
    return sum(1 for _ in value)


def json_byte_size(payload: Any) -> int:
    """Return the UTF-8 canonical JSON byte size of a payload."""
    encoded = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    return len(encoded.encode("utf-8"))


def check_json_safety(
    value: Any,
    *,
    depth: int = 0,
    max_depth: int = MAX_DEPTH,
    max_fields: int = MAX_FIELDS,
    max_items: int = MAX_LIST_ITEMS,
    max_string: int = MAX_STRING_CODE_POINTS,
    max_bytes: int = MAX_CANONICAL_JSON_BYTES,
) -> None:
    """Recursively enforce the global JSON-safety bound table.

    Rejects nesting deeper than ``max_depth``, objects with more than
    ``max_fields`` keys, lists with more than ``max_items`` entries, strings
    longer than ``max_string`` code points, non-finite numbers, booleans
    standing in for integers, and integers outside the JavaScript-safe range.
    The byte-size ceiling applies to the canonical serialization of the whole
    payload, so it is checked by the caller through :func:`check_envelope`.
    """
    if depth > max_depth:
        raise JSONSafetyError(f"nesting exceeds maximum depth {max_depth}")
    if isinstance(value, dict):
        if len(value) > max_fields:
            raise JSONSafetyError(f"object exceeds maximum of {max_fields} fields")
        for key, child in value.items():
            if not isinstance(key, str):
                raise JSONSafetyError("object keys must be strings")
            if _code_points(key) > max_string:
                raise JSONSafetyError("object key exceeds the maximum string length")
            check_json_safety(
                child,
                depth=depth + 1,
                max_depth=max_depth,
                max_fields=max_fields,
                max_items=max_items,
                max_string=max_string,
            )
    elif isinstance(value, (list, tuple)):
        if len(value) > max_items:
            raise JSONSafetyError(f"list exceeds maximum of {max_items} items")
        for child in value:
            check_json_safety(
                child,
                depth=depth + 1,
                max_depth=max_depth,
                max_fields=max_fields,
                max_items=max_items,
                max_string=max_string,
            )
    elif isinstance(value, bool):
        # bool is a subclass of int in Python; enforce integer-bool separation.
        return
    elif isinstance(value, int):
        if not -MAX_SAFE_INTEGER <= value <= MAX_SAFE_INTEGER:
            raise JSONSafetyError(
                f"integer {value} is outside the JavaScript-safe range"
            )
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise JSONSafetyError("non-finite numbers are forbidden")
    elif isinstance(value, str):
        if _code_points(value) > max_string:
            raise JSONSafetyError(
                f"string exceeds the maximum of {max_string} code points"
            )
    elif value is None:
        return
    else:
        raise JSONSafetyError(f"unsupported JSON value type {type(value).__name__}")


def carries_available_dialogue(payload: Any) -> bool:
    """Whether an envelope carries an available version-3 dialogue panel."""
    if not isinstance(payload, dict):
        return False
    panels = payload.get("panels")
    if not isinstance(panels, dict):
        return False
    dialogue = panels.get(DIALOGUE_PANEL)
    if not isinstance(dialogue, dict):
        return False
    schema_version = dialogue.get("schema_version")
    if type(schema_version) is not int or schema_version != 3:
        return False
    return dialogue.get("available") is True and dialogue.get("kind") == "dialogue"


def check_envelope_bytes(payload: Any, byte_size: int | None = None) -> None:
    """Enforce the envelope byte allowances over one JSON-safe payload.

    ``byte_size`` may carry the already-computed canonical UTF-8 size of the
    whole payload, so a caller that owns those bytes never serializes the
    document twice. A dialogue-carrying envelope additionally measures its
    dialogue panel and its dialogue-removed form, exactly as before.
    """
    size = json_byte_size(payload) if byte_size is None else byte_size
    if carries_available_dialogue(payload):
        if size > DIALOGUE_ENVELOPE_MAX_BYTES:
            raise JSONSafetyError(
                f"canonical JSON exceeds {DIALOGUE_ENVELOPE_MAX_BYTES} bytes"
            )
        dialogue = payload["panels"][DIALOGUE_PANEL]
        if json_byte_size(dialogue) > DIALOGUE_PANEL_MAX_BYTES:
            raise JSONSafetyError(
                f"dialogue panel canonical JSON exceeds {DIALOGUE_PANEL_MAX_BYTES} bytes"
            )
        stripped_panels = {
            k: v for k, v in payload["panels"].items() if k != DIALOGUE_PANEL
        }
        stripped_envelope = {**payload, "panels": stripped_panels}
        if json_byte_size(stripped_envelope) > MAX_CANONICAL_JSON_BYTES:
            raise JSONSafetyError(
                f"dialogue-removed envelope canonical JSON exceeds {MAX_CANONICAL_JSON_BYTES} bytes"
            )
    else:
        if size > MAX_CANONICAL_JSON_BYTES:
            raise JSONSafetyError(
                f"canonical JSON exceeds {MAX_CANONICAL_JSON_BYTES} bytes"
            )


def check_envelope(payload: Any) -> None:
    """Enforce the global bounds over one whole envelope, including byte size."""
    check_json_safety(payload)
    check_envelope_bytes(payload)


def _require_exact_fields(payload: Any, name: str, required: set[str], conditional: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ProtocolValidationError(f"{name} must be a JSON object")
    known = required | set(conditional)
    unknown = set(payload) - known
    if unknown:
        raise ProtocolValidationError(f"{name} has unknown fields {sorted(unknown)}")
    missing = required - set(payload)
    if missing:
        raise ProtocolValidationError(f"{name} is missing required fields {sorted(missing)}")
    for field, requirement in conditional.items():
        present = field in payload
        if requirement == "required" and not present:
            raise ProtocolValidationError(f"{name} requires {field!r}")
        if requirement == "forbidden" and present:
            raise ProtocolValidationError(f"{name} must not contain {field!r}")
        if requirement not in {"required", "forbidden", "optional", "conditional"}:
            raise ProtocolValidationError(
                f"{name} declares unknown requirement {requirement!r} for {field!r}"
            )


def _require_int(payload: dict[str, Any], field: str, *, minimum: int, maximum: int) -> int:
    value = payload[field]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProtocolValidationError(f"{field} must be an integer")
    if not minimum <= value <= maximum:
        raise ProtocolValidationError(
            f"{field} must be within {minimum}..{maximum}"
        )
    return value


def _require_bool(payload: dict[str, Any], field: str) -> bool:
    value = payload[field]
    if not isinstance(value, bool):
        raise ProtocolValidationError(f"{field} must be a boolean")
    return value


def _require_str(payload: dict[str, Any], field: str, *, maximum: int) -> str:
    value = payload[field]
    if not isinstance(value, str):
        raise ProtocolValidationError(f"{field} must be a string")
    if _code_points(value) > maximum:
        raise ProtocolValidationError(
            f"{field} exceeds the maximum of {maximum} code points"
        )
    return value


def _validate_request_id(value: Any) -> str:
    if not isinstance(value, str) or not _REQUEST_ID_RE.fullmatch(value):
        raise ProtocolValidationError(
            "request_id must be 1..64 characters of ASCII letters, digits, colon, "
            "underscore, or hyphen"
        )
    return value


def _validate_identifier(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER_RE.fullmatch(value):
        raise ProtocolValidationError(
            f"{field} must be a 1..64 lowercase dotted or underscored identifier"
        )
    return value


def _validate_panel_name(value: Any) -> str:
    if not isinstance(value, str) or not _PANEL_NAME_RE.fullmatch(value):
        raise ProtocolValidationError(
            "panel names must be 1..64 lowercase identifier characters"
        )
    return value


def _validate_message(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ProtocolValidationError(f"{field} must be a string")
    if not 1 <= _code_points(value) <= MAX_MESSAGE_CODE_POINTS:
        raise ProtocolValidationError(
            f"{field} must be 1..{MAX_MESSAGE_CODE_POINTS} Unicode code points"
        )
    return value


def _validate_correlation_id(value: Any) -> str:
    if not isinstance(value, str) or not _CORRELATION_RE.fullmatch(value):
        raise ProtocolValidationError(
            "correlation_id must be exactly 32 lowercase hexadecimal characters"
        )
    return value


def _validate_epoch(value: Any) -> str:
    if not isinstance(value, str) or len(value) != EPOCH_LENGTH:
        raise ProtocolValidationError(
            f"presentation_epoch must be exactly {EPOCH_LENGTH} URL-safe ASCII characters"
        )
    if not all((char.isascii() and (char.isalnum() or char in "-_")) for char in value):
        raise ProtocolValidationError("presentation_epoch contains a non URL-safe character")
    return value


def new_presentation_epoch() -> str:
    """Return one bounded, cryptographically unpredictable presentation epoch.

    Exactly 22 URL-safe ASCII characters derived from 128 random bits. The
    coordinator owns the lifetime of an epoch; this helper only produces the
    opaque token.
    """
    return urlsafe_b64encode(os.urandom(16)).decode("ascii").rstrip("=")


def validate_server_time(value: Any) -> dict[str, Any]:
    """Validate and normalize one exact ``server_time`` object."""
    _require_exact_fields(
        value,
        "server_time",
        {"year", "season_index", "season_label", "day_in_season", "hour", "minute", "second"},
        {},
    )
    year = _require_int(value, "year", minimum=0, maximum=MAX_SAFE_INTEGER)
    season_index = _require_int(
        value, "season_index", minimum=SEASON_INDEX_MIN, maximum=SEASON_INDEX_MAX
    )
    season_label = _require_str(value, "season_label", maximum=SEASON_LABEL_MAX)
    if not season_label.strip():
        raise ProtocolValidationError("season_label must be non-empty")
    day_in_season = _require_int(
        value, "day_in_season", minimum=DAY_IN_SEASON_MIN, maximum=DAY_IN_SEASON_MAX
    )
    hour = _require_int(value, "hour", minimum=HOUR_MIN, maximum=HOUR_MAX)
    minute = _require_int(value, "minute", minimum=MINUTE_MIN, maximum=MINUTE_MAX)
    second = _require_int(value, "second", minimum=SECOND_MIN, maximum=SECOND_MAX)
    return {
        "year": year,
        "season_index": season_index,
        "season_label": season_label,
        "day_in_season": day_in_season,
        "hour": hour,
        "minute": minute,
        "second": second,
    }


def _validate_revision(value: Any, field: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProtocolValidationError(f"{field} must be an integer")
    if not minimum <= value <= MAX_SAFE_INTEGER:
        raise ProtocolValidationError(
            f"{field} must be within {minimum}..{MAX_SAFE_INTEGER}"
        )
    return value


def _validate_panels(value: Any, field: str, *, nonempty: bool, known_panels: set[str] | None) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProtocolValidationError(f"{field} must be a JSON object")
    if nonempty and not value:
        raise ProtocolValidationError(f"{field} must not be empty")
    if len(value) > MAX_PANEL_COUNT:
        raise ProtocolValidationError(
            f"{field} exceeds the maximum of {MAX_PANEL_COUNT} panels"
        )
    names = {_validate_panel_name(name) for name in value}
    if known_panels is not None:
        unknown = names - known_panels
        if unknown:
            raise ProtocolValidationError(
                f"{field} contains unknown panel names {sorted(unknown)}"
            )
    return value


# The exact top-level field sets of the two presentation envelopes.
_SNAPSHOT_FIELDS = (
    "protocol_version",
    "presentation_epoch",
    "revision",
    "mode",
    "panels",
    "layout_version",
    "server_time",
)
_UPDATE_FIELDS = (*_SNAPSHOT_FIELDS, "base_revision", "removed_panels")


def _validate_common_metadata(
    payload: dict[str, Any],
    name: str,
    *,
    known_panels: set[str] | None,
    panels_nonempty: bool,
    required_fields: set[str],
) -> dict[str, Any]:
    _require_exact_fields(payload, name, required_fields, {})
    if _require_int(payload, "protocol_version", minimum=1, maximum=1) != PROTOCOL_VERSION:
        raise ProtocolValidationError("unsupported protocol_version")
    epoch = _validate_epoch(payload["presentation_epoch"])
    revision = _validate_revision(payload["revision"], "revision", minimum=1)
    mode = payload["mode"]
    if mode not in MODES:
        raise ProtocolValidationError(f"mode must be one of {MODES}")
    layout_version = _require_int(
        payload, "layout_version", minimum=1, maximum=MAX_LAYOUT_VERSION
    )
    panels = _validate_panels(
        payload["panels"], "panels", nonempty=panels_nonempty, known_panels=known_panels
    )
    server_time = validate_server_time(payload["server_time"])
    return {
        "protocol_version": PROTOCOL_VERSION,
        "presentation_epoch": epoch,
        "revision": revision,
        "mode": mode,
        "panels": panels,
        "layout_version": layout_version,
        "server_time": server_time,
    }


def _on_demand_panel_names() -> frozenset[str]:
    """Return the panel names delivered only on demand (never eager).

    Imported lazily: ``map_panels`` builds on this module, so a module-level
    import would be circular. The set mirrors the JavaScript validator's
    ``MAP_PANEL_SCHEMAS`` check in ``protocol/envelope.js``.
    """
    from web.webclient.presentation.map_panels import MAP_PANEL_SCHEMAS

    return frozenset(MAP_PANEL_SCHEMAS)


def _validate_removed_panels(
    value: Any,
    *,
    panels: dict[str, Any],
    known_panels: set[str] | None,
) -> list[str]:
    """Validate the exact ``removed_panels`` list of one ``ui_update``."""
    if not isinstance(value, list):
        raise ProtocolValidationError("removed_panels must be a JSON array")
    if len(value) > MAX_REMOVED_PANELS:
        raise ProtocolValidationError(
            f"removed_panels exceeds the maximum of {MAX_REMOVED_PANELS} panels"
        )
    removed: list[str] = []
    seen: set[str] = set()
    for item in value:
        name = _validate_panel_name(item)
        if name in seen:
            raise ProtocolValidationError(
                f"removed_panels contains the duplicate name {name!r}"
            )
        seen.add(name)
        removed.append(name)
    on_demand = seen & _on_demand_panel_names()
    if on_demand:
        raise ProtocolValidationError(
            f"removed_panels never names an on-demand panel {sorted(on_demand)}"
        )
    if known_panels is not None:
        unknown = seen - known_panels
        if unknown:
            raise ProtocolValidationError(
                f"removed_panels contains unknown panel names {sorted(unknown)}"
            )
    overlap = seen & set(panels)
    if overlap:
        raise ProtocolValidationError(
            f"removed_panels overlaps replaced panels {sorted(overlap)}"
        )
    return removed


def validate_ui_snapshot(payload: Any, *, known_panels: set[str] | None = None) -> dict[str, Any]:
    """Validate a full snapshot envelope, returning a normalized dict."""
    return _validate_common_metadata(
        payload,
        UI_SNAPSHOT,
        known_panels=known_panels,
        panels_nonempty=True,
        required_fields=set(_SNAPSHOT_FIELDS),
    )


def validate_ui_update(payload: Any, *, known_panels: set[str] | None = None) -> dict[str, Any]:
    """Validate one exact-base delta envelope, returning a normalized dict.

    A ``ui_update`` carries the seven snapshot fields plus the exact committed
    ``base_revision`` and the explicit ``removed_panels`` list. ``panels`` may
    be empty (a metadata-only delta); removals are disjoint from the replaced
    names and never name an on-demand map panel.
    """
    meta = _validate_common_metadata(
        payload,
        UI_UPDATE,
        known_panels=known_panels,
        panels_nonempty=False,
        required_fields=set(_UPDATE_FIELDS),
    )
    base_revision = _validate_revision(
        payload["base_revision"], "base_revision", minimum=1
    )
    if base_revision >= meta["revision"]:
        raise ProtocolValidationError("base_revision must be older than revision")
    meta["base_revision"] = base_revision
    meta["removed_panels"] = _validate_removed_panels(
        payload["removed_panels"], panels=meta["panels"], known_panels=known_panels
    )
    return meta


def _validate_result_data(value: Any) -> dict[str, Any]:
    """Validate one adapter ``data`` slot, returning the validated object.

    The slot must be a plain object of at most ``MAX_RESULT_DATA_FIELDS``
    fields with 1..64-character lowercase identifier names. Reserved state
    keys are forbidden at every nesting level, both as object keys and as the
    dot-segment heads of composite keys, so no shape smuggles one in. Values
    are JSON-safe within the global bound table, checked on the whole object
    at envelope depth 1 so a data leaf can never sit deeper than
    ``MAX_DEPTH`` measured from the envelope root, and the canonical
    serialization of the object must fit the result-data byte budget.
    """
    if not isinstance(value, dict):
        raise ProtocolValidationError("data must be a JSON object")
    if len(value) > MAX_RESULT_DATA_FIELDS:
        raise ProtocolValidationError(
            f"data exceeds the maximum of {MAX_RESULT_DATA_FIELDS} fields"
        )

    def reject_reserved(name: Any) -> None:
        _validate_identifier(name, "data field name")
        if name in FORBIDDEN_RESULT_DATA_KEYS or any(
            segment in FORBIDDEN_RESULT_DATA_KEYS for segment in name.split(".")
        ):
            raise ProtocolValidationError(
                f"data field name {name!r} carries a reserved state key"
            )

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                reject_reserved(key)
                walk(child)
        elif isinstance(node, (list, tuple)):
            for child in node:
                walk(child)

    walk(value)
    # Depth 1 is the slot's own position inside the envelope; the recursion
    # below enforces the global depth, count, and string ceilings on every
    # nested value relative to the envelope root.
    check_json_safety(value, depth=1)
    if json_byte_size(value) > MAX_RESULT_DATA_BYTES:
        raise JSONSafetyError(
            f"data canonical JSON exceeds {MAX_RESULT_DATA_BYTES} bytes"
        )
    return value


def validate_ui_action_result(payload: Any) -> dict[str, Any]:
    """Validate an exact version-1 ``ui_action_result`` envelope."""
    _require_exact_fields(
        payload,
        UI_ACTION_RESULT,
        {"protocol_version", "presentation_epoch", "request_id", "outcome", "code", "message", "presentation_revision"},
        {"correlation_id": "conditional", "data": "conditional"},
    )
    if _require_int(payload, "protocol_version", minimum=1, maximum=1) != PROTOCOL_VERSION:
        raise ProtocolValidationError("unsupported protocol_version")
    epoch = _validate_epoch(payload["presentation_epoch"])
    request_id = _validate_request_id(payload["request_id"])
    outcome = payload["outcome"]
    if outcome not in OUTCOMES:
        raise ProtocolValidationError(f"outcome must be one of {OUTCOMES}")
    code = _validate_identifier(payload["code"], "code")
    message = _validate_message(payload["message"], "message")
    presentation_revision = _validate_revision(
        payload["presentation_revision"], "presentation_revision", minimum=0
    )
    correlation_id = None
    if outcome == "error":
        correlation_id = _validate_correlation_id(payload.get("correlation_id"))
    elif "correlation_id" in payload:
        raise ProtocolValidationError(
            "correlation_id is forbidden for a non-error result"
        )
    data = None
    has_data = "data" in payload
    if has_data:
        if outcome != "success":
            raise ProtocolValidationError(
                "data is forbidden for a non-success result"
            )
        data = _validate_result_data(payload["data"])
    result: dict[str, Any] = {
        "protocol_version": PROTOCOL_VERSION,
        "presentation_epoch": epoch,
        "request_id": request_id,
        "outcome": outcome,
        "code": code,
        "message": message,
        "presentation_revision": presentation_revision,
        "correlation_id": correlation_id,
    }
    if has_data:
        result["data"] = data
    return result


def validate_ui_protocol_error(payload: Any) -> dict[str, Any]:
    """Validate an exact version-1 ``ui_protocol_error`` envelope."""
    _require_exact_fields(
        payload,
        UI_PROTOCOL_ERROR,
        {"protocol_version", "code", "message", "reload_required"},
        {"correlation_id": "conditional"},
    )
    if _require_int(payload, "protocol_version", minimum=1, maximum=1) != PROTOCOL_VERSION:
        raise ProtocolValidationError("unsupported protocol_version")
    code = _validate_identifier(payload["code"], "code")
    if code not in PROTOCOL_ERROR_CODES:
        raise ProtocolValidationError(f"unknown protocol error code {code!r}")
    message = _validate_message(payload["message"], "message")
    reload_required = _require_bool(payload, "reload_required")
    correlation_id = None
    if code in PROTOCOL_ERROR_CORRELATED_CODES:
        correlation_id = _validate_correlation_id(payload.get("correlation_id"))
    elif "correlation_id" in payload:
        raise ProtocolValidationError(
            "correlation_id is forbidden outside internal_error"
        )
    return {
        "protocol_version": PROTOCOL_VERSION,
        "code": code,
        "message": message,
        "reload_required": reload_required,
        "correlation_id": correlation_id,
    }


def validate_ui_sync(payload: Any) -> dict[str, Any]:
    """Validate the only accepted ``ui_sync`` body: ``{protocol_version: 1}``."""
    _require_exact_fields(payload, UI_SYNC, {"protocol_version"}, {})
    version = payload["protocol_version"]
    if isinstance(version, bool) or not isinstance(version, int) or version != PROTOCOL_VERSION:
        raise ProtocolValidationError("unsupported protocol_version")
    return {"protocol_version": PROTOCOL_VERSION}


def validate_ui_action(payload: Any) -> dict[str, Any]:
    """Validate the global ``ui_action`` envelope before action lookup.

    Action-specific payload validation happens in the action registry after
    epoch/revision admission; this function enforces only the exact global
    field set and global bounds.
    """
    _require_exact_fields(
        payload,
        UI_ACTION,
        {"protocol_version", "presentation_epoch", "request_id", "base_revision", "action_id", "payload"},
        {},
    )
    if _require_int(payload, "protocol_version", minimum=1, maximum=1) != PROTOCOL_VERSION:
        raise ProtocolValidationError("unsupported protocol_version")
    epoch = _validate_epoch(payload["presentation_epoch"])
    request_id = _validate_request_id(payload["request_id"])
    base_revision = _validate_revision(payload["base_revision"], "base_revision", minimum=0)
    action_id = _validate_identifier(payload["action_id"], "action_id")
    action_payload = payload["payload"]
    if not isinstance(action_payload, dict):
        raise ProtocolValidationError("payload must be a JSON object")
    return {
        "protocol_version": PROTOCOL_VERSION,
        "presentation_epoch": epoch,
        "request_id": request_id,
        "base_revision": base_revision,
        "action_id": action_id,
        "payload": action_payload,
    }


def validate_ui_publication_part(payload: Any) -> dict[str, Any]:
    """Validate one ``ui_publication_part`` frame through its owning codec.

    The part wire belongs to :mod:`web.webclient.presentation.publication_parts`,
    which imports this module; dispatch stays lazy so registration never
    depends on import order. Field shape, header consistency, canonical base64
    chunks and the generic frame ceiling all apply.
    """
    from web.webclient.presentation.publication_parts import validate_publication_part

    header, _raw = validate_publication_part(payload)
    return header


# Per-message validator table used by input functions and the dispatcher.
VALIDATORS: dict[str, Any] = {
    UI_SYNC: validate_ui_sync,
    UI_ACTION: validate_ui_action,
    UI_SNAPSHOT: validate_ui_snapshot,
    UI_UPDATE: validate_ui_update,
    UI_ACTION_RESULT: validate_ui_action_result,
    UI_PROTOCOL_ERROR: validate_ui_protocol_error,
    UI_PUBLICATION_PART: validate_ui_publication_part,
}


def unavailable_payload(
    schema_version: int,
    reason_code: str,
    message: str,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Return the exact common unavailable panel discriminator.

    The reason carries a bounded stable ``code`` and a safe Traditional
    Chinese ``message``; ``correlation_id`` appears only for an internal
    presenter failure.
    """
    if not isinstance(schema_version, int) or isinstance(schema_version, bool):
        raise ProtocolValidationError("schema_version must be an integer")
    if schema_version < 1:
        raise ProtocolValidationError("schema_version must be positive")
    reason_code = _validate_identifier(reason_code, "reason.code")
    message = _validate_message(message, "reason.message")
    reason: dict[str, Any] = {"code": reason_code, "message": message}
    if correlation_id is not None:
        reason["correlation_id"] = _validate_correlation_id(correlation_id)
    return {"schema_version": schema_version, "available": False, "reason": reason}
