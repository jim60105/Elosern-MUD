"""Exact schema-version-5 ``character`` panel and presenter (webclient-exploration-menu).

The presenter serializes the read-only expanded character surface opened by the
exploration dock's Character root. It shares the same canonical
trait/equipment/disguise source the compact ``status`` panel builds from
through ``world.rules.status_query`` so the two panels can never drift apart,
and it never substitutes a disguised value for a true trait. Version 2 added
the display-only ``persona`` section carrying the character's own background
flavor text; it is never used to infer any mechanical value. Version 3 adds
the ``actives`` field and regroups both ``actives`` and ``passives`` by the
skill-category taxonomy — which makes the innate
``flee`` and ``basic_attack`` skills visible out of combat. Version 4 adds the
nullable ``intimate`` object: the 親密狀態 (intimate status) level words from the
canonical sexual state (arousal, wetness, shame, exposure, climax phase) plus the
daily climax count; it is ``null`` when the actor has no sexual-state record at
all. The skill-ownership read is handler-free: base keys come from the stored
``entity.db.skills`` lists plus the innate grants, and the unlocked intimate acts
are computed by ``world.skills.sexual_acts.unlocked_act_keys_for`` from the
materialized counters (zeros when unmaterialized), so building the panel no longer
mounts the ``entity.skills`` or ``entity.sexual`` handlers.
Version 5 (expose-stat-breakdown-read-model) rewrites every trait row into the
breakdown shape ``{key, label, base, current, max, effective, layers}`` —
``current`` stays the total-display field on every row — and adds the P3
server-formatted ``adjustment`` summary to equipment rows. Version 5 is the
only accepted schema version (render-equipment-breakdown-webclient closed the
P6 transitional v4 tolerance window): the validator accepts v5 exactly and
rejects every other version.

The payload shape and the exact shared bounds (design D10) are mirrored by the
client validator in ``web/static/webclient/js/elosern/protocol.js`` and guarded
by a dual-direction parity test.
"""

import math
from typing import Any

from web.webclient.presentation.combat_panel import (
    MAX_COST_KEYS,
    TARGET_SPECS,
    validate_freeform_scales,
)
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
from world.lore.sexual_vocab import (
    AROUSAL_LEVELS,
    CLIMAX_PHASE_LEVELS,
    EXPOSURE_LEVELS,
    SHAME_LEVELS,
    WETNESS_LEVELS,
)
from world.rules.equipment_effects import equipment_adjustment_text
from world.rules.progression import freeform_scale_entries_for
from world.rules.status_query import (
    CharacterReadModel,
    StatusQueryError,
    TRAIT_LABELS,
    build_character_read_model,
    group_skill_keys,
)
from world.skills.registry import SKILL_REGISTRY, SkillCategory

CHARACTER_SCHEMA_VERSION = 5

# Exact shared bounds (design D10) -- must stay equal in the JS validator.
MAX_TRAIT_ROWS = 32
# The per-stat breakdown-layer bound mirrored by the wire validators (the
# read model's own bound lives in ``world.rules.status_query``).
MAX_LAYERS_PER_STAT = 16
MAX_ACTIVE_ROWS = 32
MAX_PASSIVE_ROWS = 32
# The category-group count bound equals the number of SkillCategory members
# plus one: the extra slot is the presentation-only synthetic fallback group
# (category ``"unknown"``) that holds keys absent from SKILL_REGISTRY. The
# flattened skill-row bound is tracked independently (design D-6).
MAX_CATEGORY_GROUPS = len(SkillCategory) + 1
MAX_EQUIPMENT_ROWS = 32
MAX_DISPLAYED_ROWS = 32
MAX_KEY_CODE_POINTS = 64
MAX_LABEL_CODE_POINTS = 128
MAX_DESCRIPTION_CODE_POINTS = 256
MAX_SLOT_CODE_POINTS = 32
# The equipment adjustment summary bound (P3 formatter output; 「｜」-joined
# segments of the fixed vocabulary).
MAX_ADJUSTMENT_CODE_POINTS = MAX_DESCRIPTION_CODE_POINTS
# The display-only persona background bound mirrors the persona-field cap
# (``world.rules.character_creation.MAX_PERSONA_FIELD_LENGTH``); the parity
# contract pins the JS validator to this same number.
MAX_PERSONA_BACKGROUND_CODE_POINTS = 600

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


def _require_number(value: Any, field: str, *, minimum: float, maximum: float) -> int | float:
    """Return a non-boolean, finite int/float within bounds.

    The v5 breakdown fields are the exact read-model values, which may be
    fractional (a scaled rule-table grant produces a ``2.5`` defense layer),
    so the wire accepts JSON numbers but never booleans, NaN, or infinities.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProtocolValidationError(f"{field} must be a number")
    if isinstance(value, float) and not math.isfinite(value):
        raise ProtocolValidationError(f"{field} must be finite")
    if value < minimum or value > maximum:
        raise ProtocolValidationError(f"{field} is out of bounds")
    return value


# The closed breakdown alphabets, mirrored from ``world.rules.status_query``.
LAYER_SOURCES = ("skill", "condition", "equipment")
LAYER_KINDS = ("mult", "flat", "pct")


def _validate_breakdown_layer(value: Any) -> dict[str, Any]:
    """Validate one exact ``{source, name, kind, amount}`` layer."""
    _require_exact_fields(value, "breakdown layer", {"source", "name", "kind", "amount"}, {})
    source = value["source"]
    if source not in LAYER_SOURCES:
        raise CharacterPanelError("breakdown layer source is not a stable value")
    name = _require_str(value, "name", maximum=MAX_LABEL_CODE_POINTS)
    if not name.strip():
        raise ProtocolValidationError("breakdown layer name must be non-empty")
    kind = value["kind"]
    if kind not in LAYER_KINDS:
        raise CharacterPanelError("breakdown layer kind is not a stable value")
    amount = _require_number(
        value["amount"], "breakdown layer amount", minimum=-MAX_SAFE_INTEGER, maximum=MAX_SAFE_INTEGER
    )
    if amount == 0:
        raise ProtocolValidationError("breakdown layer amount must be non-zero")
    return {"source": source, "name": name, "kind": kind, "amount": amount}


def _validate_trait_row(value: Any) -> dict[str, Any]:
    """Validate one exact breakdown trait row with base/effective/layers.

    ``current`` remains the total-display field (it may be fractional when a
    scaled rule-table grant makes the effective value fractional — the wire
    accepts numbers, not just integers). Gauge rows carry the persisted
    remainder as ``current`` and an ``effective`` equal to ``max`` whose
    layers decompose the maximum.
    """
    _require_exact_fields(
        value,
        "trait row",
        {"key", "label", "base", "current", "max", "effective", "layers"},
        {},
    )
    key = _validate_key(value["key"], "trait key")
    label = _require_str(value, "label", maximum=MAX_LABEL_CODE_POINTS)
    if not label.strip():
        raise ProtocolValidationError("trait label must be non-empty")
    base = _require_int(value, "base", minimum=0, maximum=MAX_SAFE_INTEGER)
    current = _require_number(
        value["current"], "current", minimum=0, maximum=MAX_SAFE_INTEGER
    )
    maximum = value["max"]
    if maximum is not None:
        maximum = _require_int(value, "max", minimum=1, maximum=MAX_SAFE_INTEGER)
        if current > maximum:
            raise ProtocolValidationError("trait current must not exceed maximum")
    effective = _require_number(
        value["effective"], "effective", minimum=0, maximum=MAX_SAFE_INTEGER
    )
    # The defining row contract: a gauge row's effective value IS its
    # maximum; a static row exposes its authoritative effective total through
    # the total-display field. A payload contradicting either is rejected at
    # the boundary instead of letting two incompatible totals diverge.
    if maximum is not None:
        if effective != maximum:
            raise ProtocolValidationError("gauge trait effective must equal its maximum")
    elif current != effective:
        raise ProtocolValidationError("static trait current must equal effective")
    layers = value["layers"]
    if not isinstance(layers, list) or len(layers) > MAX_LAYERS_PER_STAT:
        raise CharacterPanelError(
            f"layers must be a list of at most {MAX_LAYERS_PER_STAT} rows"
        )
    layers = [_validate_breakdown_layer(layer) for layer in layers]
    return {
        "key": key,
        "label": label,
        "base": base,
        "current": current,
        "max": maximum,
        "effective": effective,
        "layers": layers,
    }


def _validate_passive_row(value: Any) -> dict[str, Any]:
    _require_exact_fields(value, "passive row", {"key", "label"}, {})
    key = _validate_key(value["key"], "passive key")
    label = _require_str(value, "label", maximum=MAX_LABEL_CODE_POINTS)
    if not label.strip():
        raise ProtocolValidationError("passive label must be non-empty")
    return {"key": key, "label": label}


def _validate_active_skill_row(value: Any) -> dict[str, Any]:
    """Validate one active skill row of the ``character`` payload.

    The row is the display subset of the ``context_actions`` v5 skill
    descriptor: the required ``key``/``label`` plus the optional, omittable
    ``cost`` (a bounded resource-key mapping, validated with the same
    bounded-identifier-key and non-negative-int checks the combat panel uses),
    ``target_spec`` (validated against the combat panel's stable values),
    ``usable_out_of_combat`` (a boolean the character panel serves for the
    first time), and ``freeform_scales`` (validated by the combat panel's
    shared ``validate_freeform_scales``). A skill without an ``mp`` cost can
    never carry ``freeform_scales``.
    """
    _require_exact_fields(
        value,
        "active skill row",
        {"key", "label"},
        {
            "cost": "optional",
            "target_spec": "optional",
            "usable_out_of_combat": "optional",
            "freeform_scales": "optional",
        },
    )
    key = _validate_key(value["key"], "active key")
    label = _require_str(value, "label", maximum=MAX_LABEL_CODE_POINTS)
    if not label.strip():
        raise ProtocolValidationError("active skill label must be non-empty")
    cost = value.get("cost")
    if "cost" in value and cost is None:
        raise ProtocolValidationError("skill cost must be a bounded object")
    if cost is not None:
        if not isinstance(cost, dict) or len(cost) > MAX_COST_KEYS:
            raise ProtocolValidationError("skill cost must be a bounded object")
        for resource, amount in cost.items():
            _validate_identifier(resource, "cost resource key")
            if isinstance(amount, bool) or not isinstance(amount, int):
                raise ProtocolValidationError("skill cost amount must be an integer")
            if amount < 0 or amount > MAX_SAFE_INTEGER:
                raise ProtocolValidationError("skill cost amount is out of bounds")
    target_spec = value.get("target_spec")
    if "target_spec" in value and target_spec is None:
        raise ProtocolValidationError("skill target_spec is not a stable value")
    if target_spec is not None and target_spec not in TARGET_SPECS:
        raise ProtocolValidationError("skill target_spec is not a stable value")
    usable_out_of_combat = value.get("usable_out_of_combat")
    if "usable_out_of_combat" in value and usable_out_of_combat is None:
        raise ProtocolValidationError("skill usable_out_of_combat must be a boolean")
    if usable_out_of_combat is not None and not isinstance(usable_out_of_combat, bool):
        raise ProtocolValidationError("skill usable_out_of_combat must be a boolean")
    raw_mp = cost.get("mp") if isinstance(cost, dict) else None
    base_mp = raw_mp if isinstance(raw_mp, int) and not isinstance(raw_mp, bool) else None
    scales = validate_freeform_scales(value.get("freeform_scales"), base_mp)
    row = {"key": key, "label": label}
    if cost is not None:
        row["cost"] = dict(cost)
    if target_spec is not None:
        row["target_spec"] = target_spec
    if usable_out_of_combat is not None:
        row["usable_out_of_combat"] = usable_out_of_combat
    if scales:
        row["freeform_scales"] = scales
    return row


def _validate_character_skill_group(
    value: Any, row_validator: Any = _validate_passive_row
) -> dict[str, Any]:
    """Validate one ``{group, label, skills}`` sub-group of a category group."""
    _require_exact_fields(value, "skill group", {"group", "label", "skills"}, {})
    group = value["group"]
    if group is not None:
        group = _require_str(value, "group", maximum=MAX_KEY_CODE_POINTS)
        if not group.strip():
            raise ProtocolValidationError("group must be non-empty when set")
    label = value["label"]
    if label is not None:
        label = _require_str(value, "label", maximum=MAX_LABEL_CODE_POINTS)
        if not label.strip():
            raise ProtocolValidationError("label must be non-empty when set")
    if (group is None) != (label is None):
        raise ProtocolValidationError(
            "group and label must both be set or both be null"
        )
    skills = value["skills"]
    if not isinstance(skills, list):
        raise ProtocolValidationError("skills must be a list")
    skills = [row_validator(row) for row in skills]
    return {"group": group, "label": label, "skills": skills}


def _validate_character_category_group(
    value: Any, row_validator: Any = _validate_passive_row
) -> dict[str, Any]:
    """Validate one ``{category, label, groups}`` category-group entry."""
    _require_exact_fields(value, "category group", {"category", "label", "groups"}, {})
    category = _validate_key(value["category"], "category key")
    label = _require_str(value, "label", maximum=MAX_LABEL_CODE_POINTS)
    if not label.strip():
        raise ProtocolValidationError("category label must be non-empty")
    groups = value["groups"]
    if not isinstance(groups, list) or not groups:
        raise ProtocolValidationError(
            "a category group must carry a non-empty groups list"
        )
    groups = [
        _validate_character_skill_group(group, row_validator) for group in groups
    ]
    return {"category": category, "label": label, "groups": groups}


def _flattened_skill_count(category_groups: list[dict[str, Any]]) -> int:
    """Count every skill row across all category groups of one payload field."""
    return sum(
        len(group["skills"])
        for category in category_groups
        for group in category["groups"]
    )


def _validate_equipment_row(value: Any) -> dict[str, Any]:
    """Validate one equipment row: identity fields plus the bounded P3
    ``adjustment`` summary.

    The summary is the server-formatted Traditional-Chinese text of the
    equipment rulebook; items without a bound modifier carry the empty
    string, so the field is required and may be empty.
    """
    _require_exact_fields(
        value,
        "equipment row",
        {"slot", "item_key", "display_name", "adjustment"},
        {},
    )
    slot = _require_str(value, "slot", maximum=MAX_SLOT_CODE_POINTS)
    if not slot.strip():
        raise ProtocolValidationError("slot must be non-empty")
    item_key = _validate_key(value["item_key"], "item_key")
    display_name = _require_str(value, "display_name", maximum=MAX_LABEL_CODE_POINTS)
    if not display_name.strip():
        raise ProtocolValidationError("equipment display_name must be non-empty")
    adjustment = _require_str(value, "adjustment", maximum=MAX_ADJUSTMENT_CODE_POINTS)
    return {
        "slot": slot,
        "item_key": item_key,
        "display_name": display_name,
        "adjustment": adjustment,
    }


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


def _validate_persona(value: Any) -> dict[str, Any]:
    """Validate the display-only ``persona`` section of the character panel.

    Carries exactly ``background`` (a nullable bounded string from the
    character's persona record). The section is presentation data and is never
    used to infer any mechanical value.
    """
    _require_exact_fields(value, "persona", {"background"}, {})
    background = value["background"]
    if background is None:
        return {"background": None}
    if not isinstance(background, str):
        raise ProtocolValidationError("persona.background must be text or null")
    text = background.strip()
    if not text:
        return {"background": None}
    if sum(1 for _ in text) > MAX_PERSONA_BACKGROUND_CODE_POINTS:
        raise ProtocolValidationError("persona.background exceeds its bound")
    return {"background": text}


def _validate_intimate_level(
    value: Any, field: str, vocabulary: tuple[str, ...]
) -> str:
    level = _require_str(value, field, maximum=MAX_LABEL_CODE_POINTS)
    if level not in vocabulary:
        raise CharacterPanelError(f"intimate.{field} is not a member of its fixed vocabulary")
    return level


def _validate_intimate(value: Any) -> dict[str, Any] | None:
    """Validate the nullable ``intimate`` section of the character payload.

    ``None`` is valid (no sexual-state record); otherwise the section carries
    exactly the six intimate fields, each level field checked against its fixed
    vocabulary and ``climax_today`` as a non-negative safe integer.
    """
    if value is None:
        return None
    _require_exact_fields(
        value,
        "intimate",
        {
            "arousal",
            "wetness",
            "shame",
            "exposure",
            "climax_phase",
            "climax_today",
        },
        {},
    )
    return {
        "arousal": _validate_intimate_level(value, "arousal", AROUSAL_LEVELS),
        "wetness": _validate_intimate_level(value, "wetness", WETNESS_LEVELS),
        "shame": _validate_intimate_level(value, "shame", SHAME_LEVELS),
        "exposure": _validate_intimate_level(value, "exposure", EXPOSURE_LEVELS),
        "climax_phase": _validate_intimate_level(value, "climax_phase", CLIMAX_PHASE_LEVELS),
        "climax_today": _require_int(value, "climax_today", minimum=0, maximum=MAX_SAFE_INTEGER),
    }


def _serialize_intimate(view: Any) -> dict[str, Any] | None:
    """Serialize the read model's intimate view into the payload section."""
    if view is None:
        return None
    return {
        "arousal": view.arousal,
        "wetness": view.wetness,
        "shame": view.shame,
        "exposure": view.exposure,
        "climax_phase": view.climax_phase,
        "climax_today": view.climax_today,
    }


def _validate_available(payload: Any) -> dict[str, Any]:
    """Validate one exact available version-5 character payload."""
    _require_exact_fields(
        payload,
        "character panel",
        {
            "schema_version",
            "available",
            "kind",
            "traits",
            "actives",
            "passives",
            "equipment",
            "disguise",
            "guild",
            "wallet",
            "persona",
            "intimate",
        },
        {},
    )
    if (
        _require_int(payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER)
        != CHARACTER_SCHEMA_VERSION
    ):
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

    actives = payload["actives"]
    if not isinstance(actives, list) or len(actives) > MAX_CATEGORY_GROUPS:
        raise CharacterPanelError(
            f"actives must be a list of at most {MAX_CATEGORY_GROUPS} category groups"
        )
    actives = [
        _validate_character_category_group(row, _validate_active_skill_row) for row in actives
    ]
    if _flattened_skill_count(actives) > MAX_ACTIVE_ROWS:
        raise CharacterPanelError(
            f"actives must contain at most {MAX_ACTIVE_ROWS} skill rows in total"
        )

    passives = payload["passives"]
    if not isinstance(passives, list) or len(passives) > MAX_CATEGORY_GROUPS:
        raise CharacterPanelError(
            f"passives must be a list of at most {MAX_CATEGORY_GROUPS} category groups"
        )
    passives = [
        _validate_character_category_group(row, _validate_passive_row) for row in passives
    ]
    if _flattened_skill_count(passives) > MAX_PASSIVE_ROWS:
        raise CharacterPanelError(
            f"passives must contain at most {MAX_PASSIVE_ROWS} skill rows in total"
        )

    equipment = payload["equipment"]
    if not isinstance(equipment, list) or len(equipment) > MAX_EQUIPMENT_ROWS:
        raise CharacterPanelError(
            f"equipment must be a list of at most {MAX_EQUIPMENT_ROWS} rows"
        )
    equipment = [_validate_equipment_row(row) for row in equipment]

    disguise = _validate_disguise(payload["disguise"])
    guild = _validate_guild(payload["guild"])
    wallet = _require_int(payload, "wallet", minimum=0, maximum=MAX_SAFE_INTEGER)
    persona = _validate_persona(payload["persona"])

    result = {
        "schema_version": CHARACTER_SCHEMA_VERSION,
        "available": True,
        "kind": "character",
        "traits": traits,
        "actives": actives,
        "passives": passives,
        "equipment": equipment,
        "disguise": disguise,
        "guild": guild,
        "wallet": wallet,
        "persona": persona,
        "intimate": _validate_intimate(payload["intimate"]),
    }
    # Envelope guarantee (design D10): a conforming payload must serialize
    # within the OOB envelope limit; an over-limit payload fails closed.
    if json_byte_size(result) > MAX_CANONICAL_JSON_BYTES:
        raise CharacterPanelError("character payload exceeds the OOB envelope limit")
    return result


def validate_character(payload: Any) -> dict[str, Any]:
    """Validate one exact available version-5 ``character`` payload.

    Returns a normalized payload or raises :class:`CharacterPanelError`. The
    common unavailable form is NOT accepted here; the registry handles it.
    """
    if not isinstance(payload, dict):
        raise CharacterPanelError("character panel must be a JSON object")
    version = payload.get("schema_version")
    if isinstance(version, bool) or not isinstance(version, int):
        raise CharacterPanelError("unsupported character schema_version")
    if version != CHARACTER_SCHEMA_VERSION:
        raise CharacterPanelError("unsupported character schema_version")
    return _validate_available(payload)


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


def _serialize_passive_skill_groups(keys: tuple[str, ...]) -> list[dict[str, Any]]:
    """Serialize grouped skill keys into the payload's ``{category, groups}`` shape."""
    return [
        {
            "category": category.category,
            "label": category.label,
            "groups": [
                {
                    "group": group.group,
                    "label": group.label,
                    "skills": [
                        {"key": row.key, "label": row.label}
                        for row in group.skills
                    ],
                }
                for group in category.groups
            ],
        }
        for category in group_skill_keys(keys)
    ]


def _active_skill_row(row: Any, actor: Any) -> dict[str, Any]:
    """Build one active skill row, enriching registry-resolvable keys.

    A key the ``SKILL_REGISTRY`` cannot resolve keeps the bare ``{key,
    label}`` shape (the unregistered-key fallback); a resolvable key gains
    the registry-backed ``cost``, ``target_spec``, ``usable_out_of_combat``,
    and — for a freeform-eligible skill the actor has mastery to scale —
    ``freeform_scales``.
    """
    skill = SKILL_REGISTRY.get(row.key)
    entry = {"key": row.key, "label": row.label}
    if skill is None:
        return entry
    entry["cost"] = dict(skill.cost)
    entry["target_spec"] = skill.target_spec.value
    entry["usable_out_of_combat"] = skill.usable_out_of_combat
    scales = freeform_scale_entries_for(actor, skill)
    if scales:
        entry["freeform_scales"] = [
            {"scale": s, "label": l, "mp_cost": c} for s, l, c in scales
        ]
    return entry


def _serialize_active_skill_groups(keys: tuple[str, ...], actor: Any) -> list[dict[str, Any]]:
    """Serialize grouped active skill keys, enriched per row via the registry."""
    return [
        {
            "category": category.category,
            "label": category.label,
            "groups": [
                {
                    "group": group.group,
                    "label": group.label,
                    "skills": [
                        _active_skill_row(row, actor)
                        for row in group.skills
                    ],
                }
                for group in category.groups
            ],
        }
        for category in group_skill_keys(keys)
    ]


def _serialize(
    model: CharacterReadModel, background: str | None, actor: Any
) -> dict[str, Any]:
    """Serialize the frozen read model into the v5 available payload.

    Trait rows come from ``model.breakdown`` (the single assembly the whole
    read shares); labels stay the shared ``TRAIT_LABELS`` map; equipment rows
    gain the P3 adjustment summary. Every other section is byte-identical to
    v4.
    """
    disguise_description = _DISGUISE_DESCRIPTION if model.disguise_active else ""
    return {
        "schema_version": CHARACTER_SCHEMA_VERSION,
        "available": True,
        "kind": "character",
        "traits": [
            {
                "key": row.key,
                "label": _trait_label(row.key),
                "base": row.base,
                "current": row.current,
                "max": row.effective if row.key in ("hp", "mp", "sp") else None,
                "effective": row.effective,
                "layers": [
                    {
                        "source": layer.source,
                        "name": layer.name,
                        "kind": layer.kind,
                        "amount": layer.amount,
                    }
                    for layer in row.layers
                ],
            }
            for row in model.breakdown
        ],
        "actives": _serialize_active_skill_groups(model.active_keys, actor),
        "passives": _serialize_passive_skill_groups(model.passive_keys),
        "equipment": [
            {
                "slot": view.slot,
                "item_key": view.item_key,
                "display_name": _item_display_name(view.item_key),
                "adjustment": equipment_adjustment_text(view.item_key),
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
        "persona": {"background": background},
        "intimate": _serialize_intimate(model.intimate),
    }


def character_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``character`` panel for the authenticated puppet."""
    actor = context.actor
    if not _in_exploration_mode(actor):
        raise PanelUnavailableError
    try:
        model = build_character_read_model(actor)
    except StatusQueryError:
        raise PanelUnavailableError
    background = actor.persona.get("background")
    if background is not None and not isinstance(background, str):
        background = None
    if background is not None and not background.strip():
        background = None
    return validate_character(_serialize(model, background, actor))


__all__ = [
    "CHARACTER_SCHEMA_VERSION",
    "CharacterPanelError",
    "MAX_ACTIVE_ROWS",
    "MAX_CATEGORY_GROUPS",
    "MAX_DISPLAYED_ROWS",
    "MAX_EQUIPMENT_ROWS",
    "MAX_LABEL_CODE_POINTS",
    "MAX_LAYERS_PER_STAT",
    "MAX_ADJUSTMENT_CODE_POINTS",
    "MAX_PASSIVE_ROWS",
    "MAX_PERSONA_BACKGROUND_CODE_POINTS",
    "MAX_SLOT_CODE_POINTS",
    "MAX_TRAIT_ROWS",
    "TRAIT_LABELS",
    "character_presenter",
    "validate_character",
]
