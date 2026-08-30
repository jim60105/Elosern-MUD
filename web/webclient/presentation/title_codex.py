"""Exact schema-version-1 ``title_codex`` panel and presenter (title-codex-removal).

The presenter serializes the pure ``TitleCodexView`` owned by
``world/rules/title_view.py`` and validates its own output against the exact
bounded schema before returning it to the presentation registry. Malformed
title state (``TitleDataError`` from the strict read) maps to the registry's
stable unavailable payload — the codex never renders a guessed row set; the
pending ballot inside the view already degrades to empty on its own malformed
state without contaminating the title rows.

The payload shape and the exact shared bounds are mirrored by the client
validator in ``web/static/webclient/js/elosern/protocol.js``; the bounds are
owned by ``world.rules.title_view`` and mirrored here.

Envelope trimming (declared order): the view already clips each row list to
``TITLE_MAX_ROWS``; if the serialized payload still exceeds the OOB envelope,
trailing EPITHET rows drop first (newest-first keeps the head), then trailing
fixed rows. Header counters, the equipped dict, and ``full_title`` always
describe the FULL untruncated view.
"""

from typing import Any

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    _require_bool,
    _require_exact_fields,
    _require_int,
    _require_str,
    _validate_identifier,
    json_byte_size,
)
from web.webclient.presentation.registry import PanelUnavailableError
from world.lore.titles import TitleCategory
from world.rules.title_view import (
    TITLE_MAX_BASIS_CHARS,
    TITLE_MAX_DISPLAY_CHARS,
    TITLE_MAX_ROWS,
    TitleDataError,
    build_title_codex_view,
)
from world.rules.titles import MAX_FULL_TITLE_CODE_POINTS

TITLE_CODEX_SCHEMA_VERSION = 1

# Exact shared bounds -- must stay equal in the JS validator. The values are
# owned by world/rules/title_view.py; the panel only mirrors them.
TITLE_CODEX_MAX_ROWS = TITLE_MAX_ROWS
TITLE_CODEX_MAX_DISPLAY_CODE_POINTS = TITLE_MAX_DISPLAY_CHARS
TITLE_CODEX_MAX_BASIS_CODE_POINTS = TITLE_MAX_BASIS_CHARS
TITLE_CODEX_MAX_FULL_TITLE_CODE_POINTS = MAX_FULL_TITLE_CODE_POINTS

# Closed category vocabulary (TitleCategory); a row outside it is a bug.
TITLE_CODEX_CATEGORIES = frozenset(member.value for member in TitleCategory)

# The pending ballot rides inside the codex; its bounds mirror the writer's.
TITLE_CODEX_MAX_BALLOT = 3
TITLE_CODEX_BASIS_WIRE_MAX = 80

_TITLE_CODEX_MAX_KEY = 64


class TitleCodexPanelError(ProtocolValidationError):
    """The available title_codex payload violates its exact bounded schema."""


def _validate_nullable_display(value: Any, field: str) -> str | None:
    """An epithet-slot identifier: a display string (CJK), or null."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise TitleCodexPanelError(f"{field} must be a string or null")
    if not 1 <= sum(1 for _ in value) <= TITLE_CODEX_MAX_DISPLAY_CODE_POINTS:
        raise TitleCodexPanelError(f"{field} exceeds its display bound")
    return value


def _validate_fixed_row(value: Any, position: int) -> dict[str, Any]:
    label = f"title codex fixed row[{position}]"
    _require_exact_fields(
        value,
        label,
        {
            "key",
            "display",
            "category",
            "hint",
            "flavor",
            "unlocked",
            "granted_tick",
        },
        {},
    )
    key = _validate_identifier(value["key"], f"{label} key")
    if len(key) > _TITLE_CODEX_MAX_KEY:
        raise TitleCodexPanelError(f"{label} key exceeds its bound")
    display = _require_str(
        value, "display", maximum=TITLE_CODEX_MAX_DISPLAY_CODE_POINTS
    )
    if not display.strip():
        raise TitleCodexPanelError(f"{label} display must be non-empty")
    category = _require_str(value, "category", maximum=32)
    if category not in TITLE_CODEX_CATEGORIES:
        raise TitleCodexPanelError(f"{label} category is outside the closed set")
    # Locked rows carry the authored hint and no flavor; unlocked rows carry
    # flavor and no hint (view-enforced exclusivity, re-asserted on the wire).
    unlocked = _require_bool(value, "unlocked")
    hint = _require_str(value, "hint", maximum=TITLE_CODEX_MAX_BASIS_CODE_POINTS)
    flavor = _require_str(value, "flavor", maximum=TITLE_CODEX_MAX_BASIS_CODE_POINTS)
    if unlocked and hint:
        raise TitleCodexPanelError(f"{label} unlocked row must not carry a hint")
    if not unlocked and flavor:
        raise TitleCodexPanelError(f"{label} locked row must not carry flavor")
    return {
        "key": key,
        "display": display,
        "category": category,
        "hint": hint,
        "flavor": flavor,
        "unlocked": unlocked,
        "granted_tick": _require_int(
            value, "granted_tick", minimum=0, maximum=MAX_SAFE_INTEGER
        ),
    }


def _validate_epithet_row(value: Any, position: int) -> dict[str, Any]:
    label = f"title codex epithet row[{position}]"
    _require_exact_fields(
        value,
        label,
        {"display", "basis", "granted_tick", "equipped", "can_remove"},
        {},
    )
    display = _require_str(
        value, "display", maximum=TITLE_CODEX_MAX_DISPLAY_CODE_POINTS
    )
    if not display.strip():
        raise TitleCodexPanelError(f"{label} display must be non-empty")
    return {
        "display": display,
        "basis": _require_str(
            value, "basis", maximum=TITLE_CODEX_MAX_BASIS_CODE_POINTS
        ),
        "granted_tick": _require_int(
            value, "granted_tick", minimum=0, maximum=MAX_SAFE_INTEGER
        ),
        "equipped": _require_bool(value, "equipped"),
        # Server gate verdict; the client renders the flag, no client rules.
        "can_remove": _require_bool(value, "can_remove"),
    }


def _validate_ballot_entry(value: Any, position: int) -> dict[str, Any]:
    label = f"title codex pending ballot[{position}]"
    _require_exact_fields(value, label, {"display", "basis"}, {})
    display = _require_str(
        value, "display", maximum=TITLE_CODEX_MAX_DISPLAY_CODE_POINTS
    )
    if not display.strip():
        raise TitleCodexPanelError(f"{label} display must be non-empty")
    return {
        "display": display,
        "basis": _require_str(
            value, "basis", maximum=TITLE_CODEX_BASIS_WIRE_MAX
        ),
    }


def validate_title_codex(payload: Any) -> dict[str, Any]:
    """Validate one exact available ``title_codex`` payload.

    Returns a normalized payload or raises :class:`TitleCodexPanelError`. The
    common unavailable form is NOT accepted here; the registry handles it.
    """
    _require_exact_fields(
        payload,
        "title_codex panel",
        {
            "schema_version",
            "available",
            "kind",
            "fixed_rows",
            "epithet_rows",
            "equipped",
            "full_title",
            "unlocked",
            "total",
            "pending_ballot",
        },
        {},
    )
    if _require_int(
        payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER
    ) != TITLE_CODEX_SCHEMA_VERSION:
        raise TitleCodexPanelError("unsupported title_codex schema_version")
    if not _require_bool(payload, "available"):
        raise TitleCodexPanelError("available must be true for the codex form")
    if payload["kind"] != "title_codex":
        raise TitleCodexPanelError("title_codex panel kind must be title_codex")

    fixed_rows = payload["fixed_rows"]
    if not isinstance(fixed_rows, list) or len(fixed_rows) > TITLE_CODEX_MAX_ROWS:
        raise TitleCodexPanelError(
            f"fixed_rows must be a list of at most {TITLE_CODEX_MAX_ROWS} entries"
        )
    epithet_rows = payload["epithet_rows"]
    if not isinstance(epithet_rows, list) or len(epithet_rows) > TITLE_CODEX_MAX_ROWS:
        raise TitleCodexPanelError(
            f"epithet_rows must be a list of at most {TITLE_CODEX_MAX_ROWS} entries"
        )

    equipped = payload["equipped"]
    _require_exact_fields(equipped, "title codex equipped", {"fixed", "epithet"}, {})
    fixed_slot = equipped["fixed"]
    if fixed_slot is not None:
        fixed_slot = _validate_identifier(fixed_slot, "equipped.fixed")
        if len(fixed_slot) > _TITLE_CODEX_MAX_KEY:
            raise TitleCodexPanelError("equipped.fixed exceeds its bound")
    epithet_slot = _validate_nullable_display(
        equipped["epithet"], "equipped.epithet"
    )

    unlocked = _require_int(
        payload, "unlocked", minimum=0, maximum=MAX_SAFE_INTEGER
    )
    total = _require_int(payload, "total", minimum=0, maximum=MAX_SAFE_INTEGER)
    if unlocked > total:
        raise TitleCodexPanelError("unlocked must not exceed total")
    full_title = _require_str(
        payload, "full_title", maximum=TITLE_CODEX_MAX_FULL_TITLE_CODE_POINTS
    )

    ballot = payload["pending_ballot"]
    if not isinstance(ballot, list) or len(ballot) > TITLE_CODEX_MAX_BALLOT:
        raise TitleCodexPanelError(
            f"pending_ballot must be a list of at most {TITLE_CODEX_MAX_BALLOT} entries"
        )

    result = {
        "schema_version": TITLE_CODEX_SCHEMA_VERSION,
        "available": True,
        "kind": "title_codex",
        "fixed_rows": [
            _validate_fixed_row(row, index) for index, row in enumerate(fixed_rows)
        ],
        "epithet_rows": [
            _validate_epithet_row(row, index)
            for index, row in enumerate(epithet_rows)
        ],
        "equipped": {"fixed": fixed_slot, "epithet": epithet_slot},
        "full_title": full_title,
        "unlocked": unlocked,
        "total": total,
        "pending_ballot": [
            _validate_ballot_entry(entry, index)
            for index, entry in enumerate(ballot)
        ],
    }
    # Envelope guarantee: the presenter trims until a real payload fits; the
    # validator enforces the serialized size directly, so a hand-built
    # all-ceilings payload fails closed rather than being emitted.
    if json_byte_size(result) > MAX_CANONICAL_JSON_BYTES:
        raise TitleCodexPanelError("title_codex payload exceeds the OOB envelope limit")
    return result


def title_codex_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``title_codex`` panel for the puppet.

    Trailing epithet rows drop first, then trailing fixed rows, until the
    serialized payload fits the envelope; header data always describes the
    full view. Malformed title state maps to the unavailable form.
    """

    try:
        if context.actor is None:
            raise PanelUnavailableError
        view = build_title_codex_view(context.actor)
    except TitleDataError:
        raise PanelUnavailableError from None
    fixed = [
        {
            "key": row.key,
            "display": row.display,
            "category": row.category,
            "hint": row.hint,
            "flavor": row.flavor,
            "unlocked": row.unlocked,
            "granted_tick": row.granted_tick,
        }
        for row in view.fixed_rows
    ]
    epithets = [
        {
            "display": row.display,
            "basis": row.basis,
            "granted_tick": row.granted_tick,
            "equipped": row.equipped,
            "can_remove": row.can_remove,
        }
        for row in view.epithet_rows
    ]

    def payload(fixed_kept: int, epithet_kept: int) -> dict[str, Any]:
        return {
            "schema_version": TITLE_CODEX_SCHEMA_VERSION,
            "available": True,
            "kind": "title_codex",
            "fixed_rows": fixed[:fixed_kept],
            "epithet_rows": epithets[:epithet_kept],
            "equipped": dict(view.equipped),
            "full_title": view.full_title,
            "unlocked": view.unlocked,
            "total": view.total,
            "pending_ballot": [dict(entry) for entry in view.pending_ballot],
        }

    fixed_kept, epithet_kept = len(fixed), len(epithets)
    while json_byte_size(payload(fixed_kept, epithet_kept)) > MAX_CANONICAL_JSON_BYTES:
        if epithet_kept > 0:
            epithet_kept -= 1
        elif fixed_kept > 1:
            fixed_kept -= 1
        else:
            # Caps-bounded fixed rows plus the header cannot exceed the
            # envelope; anything else is a bug, and the panel fails closed.
            raise PanelUnavailableError from None
    return validate_title_codex(payload(fixed_kept, epithet_kept))
