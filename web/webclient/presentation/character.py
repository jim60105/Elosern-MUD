"""Exact schema-version-1 ``character`` panel and presenter (webclient-exploration-menu).

The presenter serializes the read-only expanded character surface opened by the
exploration dock's Character root. It shares the same canonical
trait/equipment/disguise source the compact ``status`` panel builds from
through ``world.rules.status_query`` so the two panels can never drift apart,
and it never substitutes a disguised value for a true trait.

The payload shape and the exact shared bounds (design D10) are mirrored by the
client validator in ``web/static/webclient/js/elosern/protocol.js`` and guarded
by a dual-direction parity test.
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
from world.lore.items import ITEM_REGISTRY
from world.rules.status_query import (
    CharacterReadModel,
    StatusQueryError,
    TRAIT_LABELS,
    build_character_read_model,
)
from world.skills.registry import SKILL_REGISTRY

CHARACTER_SCHEMA_VERSION = 1

# Exact shared bounds (design D10) -- must stay equal in the JS validator.
MAX_TRAIT_ROWS = 32
MAX_PASSIVE_ROWS = 32
MAX_EQUIPMENT_ROWS = 32
MAX_DISPLAYED_ROWS = 32
MAX_KEY_CODE_POINTS = 64
MAX_LABEL_CODE_POINTS = 128
MAX_DESCRIPTION_CODE_POINTS = 256
MAX_SLOT_CODE_POINTS = 32

_DISGUISE_DESCRIPTION = (
    "目前以偽裝的外貌示人，以下是他人所見的數值。真實數值不因此改變。"
)


class CharacterPanelError(ProtocolValidationError):
    """The available character payload violates its exact bounded schema."""


def _validate_key(value: Any, field: str) -> str:
    key = _validate_identifier(value, field)
    if len(key) > MAX_KEY_CODE_POINTS:
        raise ProtocolValidationError(f"{field} exceeds its bound")
    return key


def _validate_trait_row(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "trait row", {"key", "label", "current", "max"}, {})
    key = _validate_key(value["key"], "trait key")
    label = _require_str(value, "label", maximum=MAX_LABEL_CODE_POINTS)
    if not label.strip():
        raise ProtocolValidationError("trait label must be non-empty")
    current = _require_int(value, "current", minimum=0, maximum=MAX_SAFE_INTEGER)
    maximum = value["max"]
    if maximum is not None:
        maximum = _require_int(value, "max", minimum=1, maximum=MAX_SAFE_INTEGER)
        if current > maximum:
            raise ProtocolValidationError("trait current must not exceed maximum")
    return {"key": key, "label": label, "current": current, "max": maximum}


def _validate_passive_row(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "passive row", {"key", "label"}, {})
    key = _validate_key(value["key"], "passive key")
    label = _require_str(value, "label", maximum=MAX_LABEL_CODE_POINTS)
    if not label.strip():
        raise ProtocolValidationError("passive label must be non-empty")
    return {"key": key, "label": label}


def _validate_equipment_row(value: Any) -> dict[str, Any]:
    _require_exact_fields(
        value, "equipment row", {"slot", "item_key", "display_name"}, {}
    )
    slot = _require_str(value, "slot", maximum=MAX_SLOT_CODE_POINTS)
    if not slot.strip():
        raise ProtocolValidationError("slot must be non-empty")
    item_key = _validate_key(value["item_key"], "item_key")
    display_name = _require_str(value, "display_name", maximum=MAX_LABEL_CODE_POINTS)
    if not display_name.strip():
        raise ProtocolValidationError("equipment display_name must be non-empty")
    return {"slot": slot, "item_key": item_key, "display_name": display_name}


def _validate_displayed_row(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "displayed row", {"key", "label", "value"}, {})
    key = _validate_key(value["key"], "displayed key")
    label = _require_str(value, "label", maximum=MAX_LABEL_CODE_POINTS)
    if not label.strip():
        raise ProtocolValidationError("displayed label must be non-empty")
    display_value = _require_int(value, "value", minimum=0, maximum=MAX_SAFE_INTEGER)
    return {"key": key, "label": label, "value": display_value}


def _validate_disguise(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "disguise", {"active", "description", "displayed"}, {})
    active = _require_bool(value, "active")
    description = _require_str(value, "description", maximum=MAX_DESCRIPTION_CODE_POINTS)
    displayed = value["displayed"]
    if not isinstance(displayed, list) or len(displayed) > MAX_DISPLAYED_ROWS:
        raise ProtocolValidationError(
            f"displayed must be a list of at most {MAX_DISPLAYED_ROWS} rows"
        )
    displayed = [_validate_displayed_row(row) for row in displayed]
    if not active and displayed:
        raise ProtocolValidationError("an undisguised actor must have an empty displayed list")
    if active and not description.strip():
        raise ProtocolValidationError("disguise description must be non-empty when active")
    return {"active": active, "description": description, "displayed": displayed}


def _validate_guild(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "guild", {"rank", "merit"}, {})
    rank = value["rank"]
    if rank is not None:
        rank = _require_str(value, "rank", maximum=MAX_KEY_CODE_POINTS)
        if not rank.strip():
            raise ProtocolValidationError("rank must be non-empty when set")
    merit = _require_int(value, "merit", minimum=0, maximum=MAX_SAFE_INTEGER)
    return {"rank": rank, "merit": merit}


def validate_character(payload: Any) -> dict[str, Any]:
    """Validate one exact available ``character`` payload.

    Returns a normalized payload or raises :class:`CharacterPanelError`. The
    common unavailable form is NOT accepted here; the registry handles it.
    """
    _require_exact_fields(
        payload,
        "character panel",
        {
            "schema_version",
            "available",
            "kind",
            "traits",
            "passives",
            "equipment",
            "disguise",
            "guild",
            "wallet",
        },
        {},
    )
    if _require_int(
        payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER
    ) != CHARACTER_SCHEMA_VERSION:
        raise CharacterPanelError("unsupported character schema_version")
    if not _require_bool(payload, "available"):
        raise CharacterPanelError("available must be true for the character form")
    if payload["kind"] != "character":
        raise CharacterPanelError("character panel kind must be character")

    traits = payload["traits"]
    if not isinstance(traits, list) or len(traits) > MAX_TRAIT_ROWS:
        raise CharacterPanelError(f"traits must be a list of at most {MAX_TRAIT_ROWS} rows")
    traits = [_validate_trait_row(row) for row in traits]
    trait_keys = [row["key"] for row in traits]
    if len(set(trait_keys)) != len(trait_keys):
        raise CharacterPanelError("trait keys must be unique")

    passives = payload["passives"]
    if not isinstance(passives, list) or len(passives) > MAX_PASSIVE_ROWS:
        raise CharacterPanelError(f"passives must be a list of at most {MAX_PASSIVE_ROWS} rows")
    passives = [_validate_passive_row(row) for row in passives]

    equipment = payload["equipment"]
    if not isinstance(equipment, list) or len(equipment) > MAX_EQUIPMENT_ROWS:
        raise CharacterPanelError(
            f"equipment must be a list of at most {MAX_EQUIPMENT_ROWS} rows"
        )
    equipment = [_validate_equipment_row(row) for row in equipment]

    disguise = _validate_disguise(payload["disguise"])
    guild = _validate_guild(payload["guild"])
    wallet = _require_int(payload, "wallet", minimum=0, maximum=MAX_SAFE_INTEGER)

    result = {
        "schema_version": CHARACTER_SCHEMA_VERSION,
        "available": True,
        "kind": "character",
        "traits": traits,
        "passives": passives,
        "equipment": equipment,
        "disguise": disguise,
        "guild": guild,
        "wallet": wallet,
    }
    # Envelope guarantee (design D10): a conforming payload must serialize
    # within the OOB envelope limit; an over-limit payload fails closed.
    if json_byte_size(result) > MAX_CANONICAL_JSON_BYTES:
        raise CharacterPanelError("character payload exceeds the OOB envelope limit")
    return result


# ---------------------------------------------------------------------------
# Serialization from the frozen read model.
# ---------------------------------------------------------------------------


def _trait_label(key: str) -> str:
    return TRAIT_LABELS.get(key, key)


def _item_display_name(item_key: str) -> str:
    definition = ITEM_REGISTRY.get(item_key)
    if definition is None:
        return item_key
    return getattr(definition, "display_name_zh", item_key)


def _in_exploration_mode(actor: Any) -> bool:
    from world.rules.combat_session import is_in_active_session

    if bool(getattr(actor, "creation_pending", False)):
        return False
    if is_in_active_session(actor):
        return False
    return True


def _serialize(model: CharacterReadModel) -> dict[str, Any]:
    disguise_description = _DISGUISE_DESCRIPTION if model.disguise_active else ""
    return {
        "schema_version": CHARACTER_SCHEMA_VERSION,
        "available": True,
        "kind": "character",
        "traits": [
            {"key": view.key, "label": _trait_label(view.key), "current": view.current, "max": view.maximum}
            for view in model.traits
        ],
        "passives": [
            {"key": key, "label": _skill_label(key)}
            for key in model.passive_keys
        ],
        "equipment": [
            {
                "slot": view.slot,
                "item_key": view.item_key,
                "display_name": _item_display_name(view.item_key),
            }
            for view in model.equipment
        ],
        "disguise": {
            "active": model.disguise_active,
            "description": disguise_description,
            "displayed": [
                {"key": key, "label": _trait_label(key), "value": value}
                for key, value in model.disguise_displayed
            ],
        },
        "guild": {"rank": model.guild_rank, "merit": model.guild_merit},
        "wallet": model.wallet,
    }


def _skill_label(key: str) -> str:
    skill = SKILL_REGISTRY.get(key)
    if skill is None:
        return key
    return skill.label


def character_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``character`` panel for the authenticated puppet."""
    actor = context.actor
    if not _in_exploration_mode(actor):
        raise PanelUnavailableError
    try:
        model = build_character_read_model(actor)
    except StatusQueryError:
        raise PanelUnavailableError
    return validate_character(_serialize(model))


__all__ = [
    "CHARACTER_SCHEMA_VERSION",
    "CharacterPanelError",
    "MAX_DISPLAYED_ROWS",
    "MAX_EQUIPMENT_ROWS",
    "MAX_LABEL_CODE_POINTS",
    "MAX_PASSIVE_ROWS",
    "MAX_TRAIT_ROWS",
    "TRAIT_LABELS",
    "character_presenter",
    "validate_character",
]
