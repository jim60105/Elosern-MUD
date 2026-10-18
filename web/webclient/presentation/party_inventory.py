"""Exact version-1 ``party_inventory`` panel for the party window's bag tab.

The presenter serializes the frozen no-mutation member inventory view owned by
``world.rules.party_inventory.inventory_view`` and validates its own output
against the exact bounded schema before returning it to the presentation
registry. The panel follows the session's viewed member (``party.view_member``)
and falls back to the commander exactly like ``party`` and ``party_member``. It
is available in exploration and combat; a member whose canonical inventory,
equipment, or commander wallet cannot be read truthfully takes the common
unavailable form rather than inventing rows, counts, or descriptors.

The payload shape and the exact shared bounds are mirrored by the client
validator in ``web/static/webclient/js/elosern/protocol/panels/
party_inventory.js`` and guarded by a dual-direction parity test.
"""

from typing import Any

from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.party_view_selection import resolve_viewed_member
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
from web.webclient.presentation.services import serialize_item_presentation
from world.rules.party import bound_owner_of
from world.rules.party_inventory import (
    MAX_MEMBER_INVENTORY_ROWS,
    ROUTE_COMBAT_DRAFT,
    ROUTE_FIELD_USE,
    ROUTE_TOGGLE,
    PartyInventoryViewError,
    inventory_view,
)
from world.rules.party_scope import party_in_combat

PARTY_INVENTORY_SCHEMA_VERSION = 1
PARTY_INVENTORY_KIND = "party_inventory"

# Exact shared bounds -- must stay equal in the JS validator.
MAX_ROWS = MAX_MEMBER_INVENTORY_ROWS
MAX_KEY_CODE_POINTS = 64
MAX_DISPLAY_NAME_CODE_POINTS = 128
MAX_PRESENTATION_KEY_CODE_POINTS = 32
MAX_PRESENTATION_SUMMARY_CODE_POINTS = 240
MAX_REASON_CODE_POINTS = MAX_MESSAGE_CODE_POINTS

#: The rule's accessory cap; the panel publishes the same value as
#: ``equipment.accessory_limit`` and accepts no other.
PARTY_INVENTORY_ACCESSORY_LIMIT = 5

#: The closed descriptor routes and row slots.
USE_ROUTES = frozenset({ROUTE_FIELD_USE, ROUTE_COMBAT_DRAFT})
TOGGLE_ROUTES = frozenset({ROUTE_TOGGLE})
SLOT_NAMES = frozenset({"weapon_main", "weapon_off", "armor", "accessory"})


class PartyInventoryPanelError(ProtocolValidationError):
    """The available ``party_inventory`` payload violates its exact schema."""


#: The explicit blank-string vocabulary shared with the JS mirror. Python's
#: ``str.strip`` and JavaScript's ``String.trim`` disagree on Unicode
#: whitespace (U+0085, U+FEFF), so both validators use this closed ASCII set.
_BLANK_CHARS = " \t\n\r\v\f"


def _is_blank(value: str) -> bool:
    return not value.strip(_BLANK_CHARS)


def _presentation_key(value: Any, field: str) -> str:
    if (
        not isinstance(value, str)
        or not 1 <= len(value) <= MAX_PRESENTATION_KEY_CODE_POINTS
        or not all(ch.isascii() and (ch.islower() or ch == "_") for ch in value)
    ):
        raise PartyInventoryPanelError(
            f"{field} must be 1..{MAX_PRESENTATION_KEY_CODE_POINTS} "
            "lowercase ASCII letters or underscores"
        )
    return value


def _validate_presentation(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    _require_exact_fields(
        value, "presentation", {"kind", "icon_key", "rarity", "summary"}, {}
    )
    kind = _presentation_key(value["kind"], "presentation.kind")
    icon_key = _presentation_key(value["icon_key"], "presentation.icon_key")
    rarity = _presentation_key(value["rarity"], "presentation.rarity")
    summary = value["summary"]
    if not isinstance(summary, str):
        raise PartyInventoryPanelError("presentation.summary must be a string")
    if not 1 <= sum(1 for _ in summary) <= MAX_PRESENTATION_SUMMARY_CODE_POINTS:
        raise PartyInventoryPanelError(
            "presentation.summary must be 1.."
            f"{MAX_PRESENTATION_SUMMARY_CODE_POINTS} Unicode code points"
        )
    return {
        "kind": kind,
        "icon_key": icon_key,
        "rarity": rarity,
        "summary": summary,
    }


def _validate_reason(value: dict[str, Any], name: str) -> str | None:
    reason = value["reason"]
    if reason is None:
        return None
    reason = _require_str(value, "reason", maximum=MAX_REASON_CODE_POINTS)
    if _is_blank(reason):
        raise PartyInventoryPanelError(f"{name} reason must be non-empty")
    if any(0xD800 <= ord(ch) <= 0xDFFF for ch in reason):
        raise PartyInventoryPanelError(
            f"{name} reason must not carry lone surrogates"
        )
    return reason


def _validate_descriptor(
    value: Any, name: str, routes: frozenset[str]
) -> dict[str, Any]:
    _require_exact_fields(value, name, {"route", "enabled", "reason"}, {})
    route = value["route"]
    if not isinstance(route, str) or route not in routes:
        raise PartyInventoryPanelError(
            f"{name} route must be one of {sorted(routes)}"
        )
    enabled = _require_bool(value, "enabled")
    reason = _validate_reason(value, name)
    if enabled and reason is not None:
        raise PartyInventoryPanelError(f"an enabled {name} carries no reason")
    if not enabled and reason is None:
        raise PartyInventoryPanelError(f"a disabled {name} carries its reason")
    return {"route": route, "enabled": enabled, "reason": reason}


def _validate_give(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "give", {"enabled", "reason", "max_quantity"}, {})
    enabled = _require_bool(value, "enabled")
    reason = _validate_reason(value, "give")
    max_quantity = _require_int(
        value, "max_quantity", minimum=0, maximum=MAX_SAFE_INTEGER
    )
    if enabled and reason is not None:
        raise PartyInventoryPanelError("an enabled give carries no reason")
    if not enabled and reason is None:
        raise PartyInventoryPanelError("a disabled give carries its reason")
    return {
        "enabled": enabled,
        "reason": reason,
        "max_quantity": max_quantity,
    }


def _validate_slot_key(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise PartyInventoryPanelError(f"{field} must be a string or null")
    if not 1 <= sum(1 for _ in value) <= MAX_KEY_CODE_POINTS:
        raise PartyInventoryPanelError(
            f"{field} must be 1..{MAX_KEY_CODE_POINTS} characters"
        )
    if _is_blank(value):
        raise PartyInventoryPanelError(f"{field} must be non-empty")
    if any(0xD800 <= ord(ch) <= 0xDFFF for ch in value):
        raise PartyInventoryPanelError(f"{field} must not carry lone surrogates")
    return value


def _validate_display_name(value: Any) -> str:
    if not isinstance(value, str):
        raise PartyInventoryPanelError("display_name must be a string")
    if not 1 <= sum(1 for _ in value) <= MAX_DISPLAY_NAME_CODE_POINTS:
        raise PartyInventoryPanelError(
            f"display_name must be 1..{MAX_DISPLAY_NAME_CODE_POINTS} characters"
        )
    if _is_blank(value):
        raise PartyInventoryPanelError("display_name must be non-empty")
    if any(0xD800 <= ord(ch) <= 0xDFFF for ch in value):
        raise PartyInventoryPanelError(
            "display_name must not carry lone surrogates"
        )
    return value


def _validate_equipment(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value,
        "equipment",
        {
            "weapon_main",
            "weapon_off",
            "armor",
            "accessories",
            "accessory_limit",
        },
        {},
    )
    slots = {
        field: _validate_slot_key(value[field], field)
        for field in ("weapon_main", "weapon_off", "armor")
    }
    accessories = value["accessories"]
    if not isinstance(accessories, list):
        raise PartyInventoryPanelError("equipment.accessories must be a list")
    if len(accessories) > PARTY_INVENTORY_ACCESSORY_LIMIT:
        raise PartyInventoryPanelError(
            "equipment.accessories exceeds the accessory cap"
        )
    ordered: list[str] = []
    for index, entry in enumerate(accessories):
        entry = _validate_slot_key(entry, f"accessories[{index}]")
        if entry is None:
            raise PartyInventoryPanelError(
                "equipment.accessories entries must be item keys"
            )
        if entry in ordered:
            raise PartyInventoryPanelError(
                "equipment.accessories must not repeat a key"
            )
        ordered.append(entry)
    limit = _require_int(
        value,
        "accessory_limit",
        minimum=PARTY_INVENTORY_ACCESSORY_LIMIT,
        maximum=PARTY_INVENTORY_ACCESSORY_LIMIT,
    )
    worn = [key for key in slots.values() if key is not None]
    if len(set(worn)) != len(worn) or set(worn) & set(ordered):
        raise PartyInventoryPanelError(
            "equipment keys must occupy exactly one slot"
        )
    return {
        "weapon_main": slots["weapon_main"],
        "weapon_off": slots["weapon_off"],
        "armor": slots["armor"],
        "accessories": ordered,
        "accessory_limit": limit,
    }


def _worn_slots(equipment: dict[str, Any]) -> dict[str, str]:
    worn: dict[str, str] = {}
    for field in ("weapon_main", "weapon_off", "armor"):
        key = equipment[field]
        if key is not None:
            worn[key] = field
    for key in equipment["accessories"]:
        worn[key] = "accessory"
    return worn


def _validate_row(
    value: Any, name: str, worn: dict[str, str], seen: set[str]
) -> dict[str, Any]:
    _require_exact_fields(
        value,
        name,
        {
            "item_key",
            "display_name",
            "held",
            "equipped_count",
            "slot",
            "presentation",
            "use",
            "toggle",
            "give",
        },
        {},
    )
    item_key = _validate_slot_key(value["item_key"], f"{name}.item_key")
    if item_key is None:  # pragma: no cover - the exact-field rule forbids null
        raise PartyInventoryPanelError(f"{name}.item_key must be non-null")
    if item_key in seen:
        raise PartyInventoryPanelError(f"{name}.item_key must be unique")
    seen.add(item_key)
    display_name = _validate_display_name(value["display_name"])
    held = _require_int(value, "held", minimum=1, maximum=MAX_SAFE_INTEGER)
    equipped_count = _require_int(
        value, "equipped_count", minimum=0, maximum=1
    )
    slot = value["slot"]
    if slot is not None and (
        not isinstance(slot, str) or slot not in SLOT_NAMES
    ):
        raise PartyInventoryPanelError(
            f"{name}.slot must be null or one of {sorted(SLOT_NAMES)}"
        )
    use = (
        None
        if value["use"] is None
        else _validate_descriptor(value["use"], f"{name}.use", USE_ROUTES)
    )
    toggle = (
        None
        if value["toggle"] is None
        else _validate_descriptor(
            value["toggle"], f"{name}.toggle", TOGGLE_ROUTES
        )
    )
    give = _validate_give(value["give"])
    if (slot is None) != (toggle is None):
        raise PartyInventoryPanelError(
            f"{name} must carry a toggle exactly when it has a slot"
        )
    expected_slot = worn.get(item_key)
    if expected_slot is None:
        if equipped_count != 0:
            raise PartyInventoryPanelError(
                f"{name} is not worn but reports equipped state"
            )
    elif equipped_count != 1 or slot != expected_slot:
        raise PartyInventoryPanelError(
            f"{name} equipped state must match the equipment section"
        )
    return {
        "item_key": item_key,
        "display_name": display_name,
        "held": held,
        "equipped_count": equipped_count,
        "slot": slot,
        "presentation": _validate_presentation(value["presentation"]),
        "use": use,
        "toggle": toggle,
        "give": give,
    }


def validate_party_inventory(payload: Any) -> dict[str, Any]:
    """Validate one exact available version-1 ``party_inventory`` payload."""
    _require_exact_fields(
        payload,
        "party_inventory panel",
        {
            "schema_version",
            "available",
            "kind",
            "member_id",
            "purse",
            "equipment",
            "rows",
        },
        {},
    )
    _require_int(payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER)
    if payload["schema_version"] != PARTY_INVENTORY_SCHEMA_VERSION:
        raise PartyInventoryPanelError("unsupported party_inventory schema_version")
    if payload["available"] is not True:
        raise PartyInventoryPanelError("party_inventory panel must be available")
    if payload["kind"] != PARTY_INVENTORY_KIND:
        raise PartyInventoryPanelError(
            f"kind must be {PARTY_INVENTORY_KIND!r}"
        )
    member_id = _require_int(
        payload, "member_id", minimum=1, maximum=MAX_SAFE_INTEGER
    )
    purse = _require_int(payload, "purse", minimum=0, maximum=MAX_SAFE_INTEGER)
    equipment = _validate_equipment(payload["equipment"])
    rows = payload["rows"]
    if not isinstance(rows, list):
        raise PartyInventoryPanelError("rows must be a list")
    if len(rows) > MAX_ROWS:
        raise PartyInventoryPanelError(
            f"rows must hold at most {MAX_ROWS} entries"
        )
    worn = _worn_slots(equipment)
    seen: set[str] = set()
    normalized_rows = [
        _validate_row(row, f"row {index + 1}", worn, seen)
        for index, row in enumerate(rows)
    ]
    result = {
        "schema_version": PARTY_INVENTORY_SCHEMA_VERSION,
        "available": True,
        "kind": PARTY_INVENTORY_KIND,
        "member_id": member_id,
        "purse": purse,
        "equipment": equipment,
        "rows": normalized_rows,
    }
    if json_byte_size(result) > MAX_CANONICAL_JSON_BYTES:
        raise PartyInventoryPanelError(
            "party_inventory payload exceeds the OOB envelope limit"
        )
    return result


def _serialize_equipment(equipment: Any) -> dict[str, Any]:
    return {
        "weapon_main": equipment.weapon_main,
        "weapon_off": equipment.weapon_off,
        "armor": equipment.armor,
        "accessories": list(equipment.accessories),
        "accessory_limit": equipment.accessory_limit,
    }


def _serialize_descriptor(descriptor: Any) -> dict[str, Any]:
    return {
        "route": descriptor.route,
        "enabled": descriptor.enabled,
        "reason": descriptor.reason,
    }


def _serialize_row(row: Any) -> dict[str, Any]:
    return {
        "item_key": row.item_key,
        "display_name": row.display_name[:MAX_DISPLAY_NAME_CODE_POINTS],
        "held": row.held,
        "equipped_count": row.equipped_count,
        "slot": row.slot,
        "presentation": serialize_item_presentation(row.presentation),
        "use": None if row.use is None else _serialize_descriptor(row.use),
        "toggle": (
            None if row.toggle is None else _serialize_descriptor(row.toggle)
        ),
        "give": {
            "enabled": row.give.enabled,
            "reason": row.give.reason,
            "max_quantity": row.give.max_quantity,
        },
    }


def party_inventory_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``party_inventory`` panel for the viewed member."""
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
    try:
        view = inventory_view(
            member, in_combat=party_in_combat(actor, member)
        )
    except PartyInventoryViewError:
        raise PanelUnavailableError
    return validate_party_inventory(
        {
            "schema_version": PARTY_INVENTORY_SCHEMA_VERSION,
            "available": True,
            "kind": PARTY_INVENTORY_KIND,
            "member_id": int(member.pk),
            "purse": view.purse,
            "equipment": _serialize_equipment(view.equipment),
            "rows": [_serialize_row(row) for row in view.rows],
        }
    )


__all__ = [
    "MAX_DISPLAY_NAME_CODE_POINTS",
    "MAX_KEY_CODE_POINTS",
    "MAX_PRESENTATION_KEY_CODE_POINTS",
    "MAX_PRESENTATION_SUMMARY_CODE_POINTS",
    "MAX_REASON_CODE_POINTS",
    "MAX_ROWS",
    "PARTY_INVENTORY_ACCESSORY_LIMIT",
    "PARTY_INVENTORY_KIND",
    "PARTY_INVENTORY_SCHEMA_VERSION",
    "PartyInventoryPanelError",
    "party_inventory_presenter",
    "validate_party_inventory",
]
