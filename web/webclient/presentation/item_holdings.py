"""Exact version-1 ``item_holdings`` panel for the bag and shop holdings strip.

The presenter serializes the frozen no-mutation holdings view owned by
``world.rules.party_inventory.item_holdings``: for one selected item, every
party member's held count and, for equipment, each member's server-computed
stat delta against that member's current slot occupant, plus the transfer
verdict for giving the item to that member. The client computes neither the
counts nor the deltas.

The panel follows the session's viewed member (``party.view_member``) and its
selected item, and falls back to the commander exactly like ``party`` and
``party_inventory``. It is available in exploration and combat; an unreadable
canonical inventory, equipment, or trait record takes the common unavailable
form rather than inventing rows, counts, or deltas.

The payload shape and the exact shared bounds are mirrored by the client
validator in ``web/static/webclient/js/elosern/protocol/panels/
item_holdings.js`` and guarded by a dual-direction parity test.
"""

import math
from typing import Any

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.party_view_selection import (
    resolve_viewed_member,
    selected_item_key_for,
)
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    MAX_MESSAGE_CODE_POINTS,
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    _require_bool,
    _require_exact_fields,
    _require_int,
    _require_str,
    json_byte_size,
)
from web.webclient.presentation.registry import PanelUnavailableError
from world.lore.items import ITEM_REGISTRY
from world.rules.party import bound_owner_of
from world.rules.party_inventory import (
    MAX_EQUIPMENT_DELTA_CHANGES,
    MAX_ITEM_HOLDINGS_ROWS,
    PartyInventoryViewError,
    item_holdings,
)
from world.rules.party_scope import party_in_combat

ITEM_HOLDINGS_SCHEMA_VERSION = 1
ITEM_HOLDINGS_KIND = "item_holdings"

# Exact shared bounds -- must stay equal in the JS validator.
MAX_ROWS = MAX_ITEM_HOLDINGS_ROWS
MAX_CHANGES = MAX_EQUIPMENT_DELTA_CHANGES
MAX_KEY_CODE_POINTS = 64
MAX_LABEL_CODE_POINTS = 32
MAX_REASON_CODE_POINTS = MAX_MESSAGE_CODE_POINTS

#: The character panel's canonical breakdown row order. Delta changes are a
#: subsequence of it, so the client never re-sorts server arithmetic.
TRAIT_ORDER = (
    "hp",
    "mp",
    "sp",
    "atk_phys",
    "agility",
    "defense",
    "magic_power",
    "guild_merit",
)


class ItemHoldingsPanelError(ProtocolValidationError):
    """The available ``item_holdings`` payload violates its exact schema."""


#: The explicit blank-string vocabulary shared with the JS mirror. Python's
#: ``str.strip`` and JavaScript's ``String.trim`` disagree on Unicode
#: whitespace (U+0085, U+FEFF), so both validators use this closed ASCII set.
_BLANK_CHARS = " \t\n\r\v\f"


def _is_blank(value: str) -> bool:
    return not value.strip(_BLANK_CHARS)


def _code_points(value: str) -> int:
    return sum(1 for _ in value)


def _bounded_text(value: Any, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ItemHoldingsPanelError(f"{field} must be a string")
    if not 1 <= _code_points(value) <= maximum:
        raise ItemHoldingsPanelError(
            f"{field} must be 1..{maximum} Unicode code points"
        )
    if _is_blank(value):
        raise ItemHoldingsPanelError(f"{field} must be non-empty")
    if any(0xD800 <= ord(ch) <= 0xDFFF for ch in value):
        raise ItemHoldingsPanelError(f"{field} must not carry lone surrogates")
    return value


def _item_key(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _bounded_text(value, field, MAX_KEY_CODE_POINTS)


def _amount(value: Any, field: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ItemHoldingsPanelError(f"{field} must be a number")
    if isinstance(value, float) and not math.isfinite(value):
        raise ItemHoldingsPanelError(f"{field} must be finite")
    if value == 0:
        raise ItemHoldingsPanelError(f"{field} must be non-zero")
    if abs(value) > MAX_SAFE_INTEGER:
        raise ItemHoldingsPanelError(f"{field} exceeds the safe integer bound")
    return value


def _validate_change(value: Any, name: str) -> dict[str, Any]:
    _require_exact_fields(value, name, {"key", "label", "amount"}, {})
    return {
        "key": _bounded_text(value["key"], f"{name}.key", MAX_KEY_CODE_POINTS),
        "label": _bounded_text(
            value["label"], f"{name}.label", MAX_LABEL_CODE_POINTS
        ),
        "amount": _amount(value["amount"], f"{name}.amount"),
    }


def _validate_delta(value: Any, name: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ItemHoldingsPanelError(f"{name} must be a JSON object or null")
    equippable = value.get("equippable")
    if not isinstance(equippable, bool):
        raise ItemHoldingsPanelError(f"{name}.equippable must be a boolean")
    if equippable:
        _require_exact_fields(value, name, {"equippable", "changes"}, {})
        changes = value["changes"]
        if not isinstance(changes, list):
            raise ItemHoldingsPanelError(f"{name}.changes must be a list")
        if len(changes) > MAX_CHANGES:
            raise ItemHoldingsPanelError(
                f"{name}.changes must hold at most {MAX_CHANGES} entries"
            )
        return {
            "equippable": True,
            "changes": _validated_changes(
                [
                    _validate_change(change, f"{name}.changes[{index}]")
                    for index, change in enumerate(changes)
                ],
                name,
            ),
        }
    _require_exact_fields(value, name, {"equippable", "reason"}, {})
    return {
        "equippable": False,
        "reason": _bounded_text(
            value["reason"], f"{name}.reason", MAX_REASON_CODE_POINTS
        ),
    }


def _validated_changes(
    changes: list[dict[str, Any]], name: str
) -> list[dict[str, Any]]:
    """Enforce unique, canonically ordered trait keys on one delta."""
    indexes: list[int] = []
    for change in changes:
        try:
            indexes.append(TRAIT_ORDER.index(change["key"]))
        except ValueError:
            raise ItemHoldingsPanelError(
                f"{name}.changes key {change['key']!r} is not a canonical trait"
            ) from None
    if indexes != sorted(set(indexes)):
        raise ItemHoldingsPanelError(
            f"{name}.changes must name unique traits in canonical order"
        )
    return changes


def _validate_receive(
    value: Any, name: str, *, own_row: bool
) -> dict[str, Any]:
    _require_exact_fields(value, name, {"enabled", "reason"}, {})
    enabled = _require_bool(value, "enabled")
    reason = value["reason"]
    if reason is not None:
        reason = _bounded_text(reason, f"{name}.reason", MAX_REASON_CODE_POINTS)
    if own_row and enabled:
        raise ItemHoldingsPanelError(
            f"{name} on the viewed member's own row must be disabled"
        )
    if enabled and reason is not None:
        raise ItemHoldingsPanelError(f"an enabled {name} carries no reason")
    if not enabled and reason is None and not own_row:
        raise ItemHoldingsPanelError(f"a disabled {name} carries its reason")
    return {"enabled": enabled, "reason": reason}


def _validate_row(value: Any, name: str, giver_id: int) -> dict[str, Any]:
    _require_exact_fields(
        value, name, {"member_id", "held", "equipped", "delta", "receive"}, {}
    )
    member_id = _require_int(value, "member_id", minimum=1, maximum=MAX_SAFE_INTEGER)
    held = _require_int(value, "held", minimum=0, maximum=MAX_SAFE_INTEGER)
    equipped = _require_bool(value, "equipped")
    return {
        "member_id": member_id,
        "held": held,
        "equipped": equipped,
        "delta": _validate_delta(value["delta"], f"{name}.delta"),
        "receive": _validate_receive(
            value["receive"], f"{name}.receive", own_row=member_id == giver_id
        ),
    }


def validate_item_holdings(payload: Any) -> dict[str, Any]:
    """Validate one exact available version-1 ``item_holdings`` payload."""
    _require_exact_fields(
        payload,
        "item_holdings panel",
        {"schema_version", "available", "kind", "item_key", "giver_id", "rows"},
        {},
    )
    _require_int(payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER)
    if payload["schema_version"] != ITEM_HOLDINGS_SCHEMA_VERSION:
        raise ItemHoldingsPanelError("unsupported item_holdings schema_version")
    if payload["available"] is not True:
        raise ItemHoldingsPanelError("item_holdings panel must be available")
    if payload["kind"] != ITEM_HOLDINGS_KIND:
        raise ItemHoldingsPanelError(f"kind must be {ITEM_HOLDINGS_KIND!r}")
    item_key = _item_key(payload["item_key"], "item_key")
    giver_id = _require_int(
        payload, "giver_id", minimum=1, maximum=MAX_SAFE_INTEGER
    )
    rows = payload["rows"]
    if not isinstance(rows, list):
        raise ItemHoldingsPanelError("rows must be a list")
    if len(rows) > MAX_ROWS:
        raise ItemHoldingsPanelError(f"rows must hold at most {MAX_ROWS} entries")
    normalized_rows = [
        _validate_row(row, f"row {index + 1}", giver_id)
        for index, row in enumerate(rows)
    ]
    seen: set[int] = set()
    for row in normalized_rows:
        if row["member_id"] in seen:
            raise ItemHoldingsPanelError("rows must name each member once")
        seen.add(row["member_id"])
    if (item_key is None) != (not normalized_rows):
        raise ItemHoldingsPanelError(
            "no selected item must publish no rows, and a selected item must name its members"
        )
    if normalized_rows and giver_id not in seen:
        raise ItemHoldingsPanelError("rows must include the viewed member")
    delta_nullable = {row["delta"] is None for row in normalized_rows}
    if len(delta_nullable) > 1:
        raise ItemHoldingsPanelError(
            "delta must be null for every row or for none"
        )
    for row in normalized_rows:
        if not row["equipped"]:
            continue
        delta = row["delta"]
        if (
            delta is None
            or not delta["equippable"]
            or delta["changes"]
        ):
            raise ItemHoldingsPanelError(
                "an equipped row carries an equippable empty delta"
            )
    result = {
        "schema_version": ITEM_HOLDINGS_SCHEMA_VERSION,
        "available": True,
        "kind": ITEM_HOLDINGS_KIND,
        "item_key": item_key,
        "giver_id": giver_id,
        "rows": normalized_rows,
    }
    if json_byte_size(result) > MAX_CANONICAL_JSON_BYTES:
        raise ItemHoldingsPanelError(
            "item_holdings payload exceeds the OOB envelope limit"
        )
    return result


def _serialize_delta(delta: Any) -> dict[str, Any] | None:
    if delta is None:
        return None
    if not delta.equippable:
        return {"equippable": False, "reason": delta.reason}
    return {
        "equippable": True,
        "changes": [
            {
                "key": change.key,
                "label": change.label,
                "amount": change.amount,
            }
            for change in delta.changes
        ],
    }


#: Public aliases shared with the ``services`` shop rows, whose ``viewed.delta``
#: is the same server equipment delta for the viewed member
#: (services-shop-structured-rows).
validate_equipment_delta = _validate_delta
serialize_equipment_delta = _serialize_delta


def item_holdings_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``item_holdings`` panel for the selection."""
    actor = context.actor
    if bool(getattr(actor, "creation_pending", False)):
        raise PanelUnavailableError
    if getattr(actor, "location", None) is None:
        raise PanelUnavailableError
    from typeclasses.npcs import NPC

    commander = bound_owner_of(actor) if isinstance(actor, NPC) else actor
    if commander is None:
        raise PanelUnavailableError
    member = resolve_viewed_member(context)
    if member is None:  # pragma: no cover - the commander resolved above
        raise PanelUnavailableError
    item_key = selected_item_key_for(context, member)
    if item_key is not None and item_key not in ITEM_REGISTRY:
        item_key = None
    try:
        view = item_holdings(
            actor, member, item_key, in_combat=party_in_combat(actor, member)
        )
    except PartyInventoryViewError:
        raise PanelUnavailableError
    return validate_item_holdings(
        {
            "schema_version": ITEM_HOLDINGS_SCHEMA_VERSION,
            "available": True,
            "kind": ITEM_HOLDINGS_KIND,
            "item_key": view.item_key,
            "giver_id": int(view.giver.pk),
            "rows": [
                {
                    "member_id": row.member_id,
                    "held": row.held,
                    "equipped": row.equipped,
                    "delta": _serialize_delta(row.delta),
                    "receive": {
                        "enabled": row.receive.enabled,
                        "reason": row.receive.reason,
                    },
                }
                for row in view.rows
            ],
        }
    )


__all__ = [
    "ITEM_HOLDINGS_KIND",
    "ITEM_HOLDINGS_SCHEMA_VERSION",
    "ItemHoldingsPanelError",
    "MAX_CHANGES",
    "MAX_KEY_CODE_POINTS",
    "MAX_LABEL_CODE_POINTS",
    "MAX_REASON_CODE_POINTS",
    "MAX_ROWS",
    "item_holdings_presenter",
    "serialize_equipment_delta",
    "validate_equipment_delta",
    "validate_item_holdings",
]
