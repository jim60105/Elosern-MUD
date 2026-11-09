"""Exact schema-version-2 ``lore_codex`` panel, presenter, and validator.

The presenter serializes the player's lore codex as a tile wall: the eight
``CODE_CATEGORIES`` in mapping order, each with its registry ``total``, its
``discovered`` count and its groups of slots. Every registry entry owns one
slot in registry order. A discovered entry is an entry slot carrying its key,
display title, research stage, art descriptor, canonical card and locked
field names; an undiscovered entry is exactly ``{"placeholder": true}``.

Non-disclosure: an undiscovered entry discloses only its count and its
ordinal position within its group, never a key, title, art, stage or field.
The monster category groups its species by the default variant's threat tier
in ``MONSTER_TIER_REGISTRY`` order (empty tiers are absent); every other
category carries one group with a null label.

Cards come from the canonical renderers only: ``species_card`` for a monster
(stage-gated by the defeated record) and ``lore_card`` for everything else.
Art reflects whatever the existing art pipelines already recorded: monster
entries carry their ``portrait:monster:<species>`` descriptor, region and
anchor entries their declared scene archetype's scene descriptor, other
entries ``null``. Building art is a pure read; a failure nulls that slot's
art only.

A recorded entry whose registry key vanished produces no slot. A corrupt
stored record (``LoreRecordError`` from a reader) degrades the whole panel to
the registry-owned common unavailable form. Over the OOB envelope limit the
presenter drops trailing placeholders first, then entry art from the last
slot backwards, and fails closed when neither is left; counts stay untrimmed.

The presenter is host-independent and read-only. Bounds are mirrored by the
client validator in ``web/static/webclient/js/elosern/protocol/panels/exotic.js``
and guarded by a dual-direction parity test.
"""

from typing import Any

from web.webclient.presentation.artwork import validate_artwork
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    MAX_SAFE_INTEGER,
    ProtocolValidationError,
    _require_bool,
    _require_exact_fields,
    _require_int,
    _require_str,
    json_byte_size,
)
from web.webclient.presentation.registry import PanelUnavailableError
from world.art.presenter import describe_portrait, describe_scene
from world.art.subjects import monster_subject_for
from world.lore import scene_archetypes
from world.lore.monster_species import MONSTER_VARIANT_REGISTRY
from world.lore.monster_visuals import is_registered_monster_visual_key
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.observability import log_warn
from world.rules.art_view import SceneTarget
from world.rules.lore_knowledge import (
    CATEGORY_LABELS,
    CODE_CATEGORIES,
    LoreRecordError,
    list_discovered,
    list_species_defeated,
    lore_card,
    species_card,
)

LORE_CODEX_SCHEMA_VERSION = 2

# Exact shared bounds -- must stay equal in the JS validator.
LORE_CODEX_MAX_SLOTS_PER_CATEGORY = 128
LORE_CODEX_MAX_TOTAL_SLOTS = 512
LORE_CODEX_MAX_GROUPS_PER_CATEGORY = 16
LORE_CODEX_MAX_CARD_FIELDS = 8
LORE_CODEX_MAX_VARIANT_LINES = 8
LORE_CODEX_MAX_KEY_CODE_POINTS = 64
LORE_CODEX_MAX_TITLE_CODE_POINTS = 64
LORE_CODEX_MAX_LABEL_CODE_POINTS = 32
LORE_CODEX_MAX_FIELD_NAME_CODE_POINTS = 64
LORE_CODEX_MAX_FIELD_VALUE_CODE_POINTS = 1024

# The eight codex categories in CODE_CATEGORIES mapping order.
LORE_CODEX_CATEGORIES = tuple(CODE_CATEGORIES.keys())

# The one category whose groups are threat tiers and whose entries carry a stage.
MONSTER_CATEGORY = "monster"
SPECIES_STAGES = ("sighted", "defeated")
VARIANTS_FIELD = "variants"

PLACEHOLDER_SLOT_FIELDS = {"placeholder"}
ENTRY_SLOT_FIELDS = {"key", "title", "stage", "art", "card", "locked_fields"}


class LoreCodexPanelError(ProtocolValidationError):
    """The available lore_codex payload violates its exact bounded schema."""


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------


def _reject_lone_surrogates(value: str, field: str) -> str:
    """Reject strings carrying unpaired UTF-16 surrogate code points."""
    for char in value:
        if 0xD800 <= ord(char) <= 0xDFFF:
            raise LoreCodexPanelError(f"{field} contains an unpaired surrogate code point")
    return value


def _validated_key(value: Any, field: str, label: str) -> str:
    """An opaque registry identifier: non-empty, bounded, colon-free."""
    key = _require_str(value, field, maximum=LORE_CODEX_MAX_KEY_CODE_POINTS)
    if not key or ":" in key:
        raise LoreCodexPanelError(f"{label} {field} must be non-empty and contain no colon")
    return _reject_lone_surrogates(key, f"{label} {field}")


def _validated_label(value: Any, field: str, label: str) -> str:
    text = _require_str(value, field, maximum=LORE_CODEX_MAX_LABEL_CODE_POINTS)
    if not text.strip():
        raise LoreCodexPanelError(f"{label} {field} must be non-empty")
    return _reject_lone_surrogates(text, f"{label} {field}")


def _validate_card_field(value: Any, index: int) -> dict[str, str]:
    label = f"card field[{index}]"
    _require_exact_fields(value, label, {"name", "value"}, {})
    name = _require_str(value, "name", maximum=LORE_CODEX_MAX_FIELD_NAME_CODE_POINTS)
    if not name.strip():
        raise LoreCodexPanelError(f"{label} name must be non-empty")
    _reject_lone_surrogates(name, f"{label} name")

    val = _require_str(value, "value", maximum=LORE_CODEX_MAX_FIELD_VALUE_CODE_POINTS)
    _reject_lone_surrogates(val, f"{label} value")
    if name == VARIANTS_FIELD and len(val.split("\n")) > LORE_CODEX_MAX_VARIANT_LINES:
        raise LoreCodexPanelError(
            f"{label} {VARIANTS_FIELD} must hold at most {LORE_CODEX_MAX_VARIANT_LINES} lines"
        )
    return {"name": name, "value": val}


def _validate_locked_fields(value: Any, label: str, card_names: set[str]) -> list[str]:
    if not isinstance(value, list):
        raise LoreCodexPanelError(f"{label} locked_fields must be a list")
    if len(value) > LORE_CODEX_MAX_CARD_FIELDS:
        raise LoreCodexPanelError(
            f"{label} locked_fields must hold at most {LORE_CODEX_MAX_CARD_FIELDS} items"
        )
    locked: list[str] = []
    for index, name in enumerate(value):
        field = f"{label} locked_fields[{index}]"
        if not isinstance(name, str):
            raise LoreCodexPanelError(f"{field} must be a string")
        if not name.strip() or len(name) > LORE_CODEX_MAX_FIELD_NAME_CODE_POINTS:
            raise LoreCodexPanelError(
                f"{field} must be non-empty and at most "
                f"{LORE_CODEX_MAX_FIELD_NAME_CODE_POINTS} code points"
            )
        _reject_lone_surrogates(name, field)
        if name in locked:
            raise LoreCodexPanelError(f"{field} duplicates {name!r}")
        if name in card_names:
            raise LoreCodexPanelError(f"{field} {name!r} is also a card field")
        locked.append(name)
    return locked


def _validate_entry_slot(value: dict, label: str, monster: bool) -> dict[str, Any]:
    _require_exact_fields(value, label, ENTRY_SLOT_FIELDS, {})
    # Registry keys are opaque domain identities, not protocol action identifiers.
    key = _validated_key(value, "key", label)

    title = _require_str(value, "title", maximum=LORE_CODEX_MAX_TITLE_CODE_POINTS)
    if not title.strip():
        raise LoreCodexPanelError(f"{label} title must be non-empty")
    _reject_lone_surrogates(title, f"{label} title")

    stage = value["stage"]
    if monster:
        if stage not in SPECIES_STAGES:
            raise LoreCodexPanelError(f"{label} stage must be one of {SPECIES_STAGES}")
    elif stage is not None:
        raise LoreCodexPanelError(f"{label} stage must be null outside the monster category")

    art = value["art"]
    if art is not None:
        art = validate_artwork(art)

    card = value["card"]
    if not isinstance(card, list):
        raise LoreCodexPanelError(f"{label} card must be a list")
    if len(card) > LORE_CODEX_MAX_CARD_FIELDS:
        raise LoreCodexPanelError(
            f"{label} card must hold at most {LORE_CODEX_MAX_CARD_FIELDS} fields"
        )
    validated_card = [_validate_card_field(field, idx) for idx, field in enumerate(card)]
    card_names = [field["name"] for field in validated_card]
    if len(set(card_names)) != len(card_names):
        raise LoreCodexPanelError(f"{label} card field names must be unique")

    locked = _validate_locked_fields(value["locked_fields"], label, set(card_names))
    if locked and stage != "sighted":
        raise LoreCodexPanelError(f"{label} locked_fields must be empty unless the stage is sighted")
    return {
        "key": key,
        "title": title,
        "stage": stage,
        "art": art,
        "card": validated_card,
        "locked_fields": locked,
    }


def _validate_slot(value: Any, label: str, monster: bool) -> dict[str, Any]:
    if isinstance(value, dict) and "placeholder" in value:
        # A placeholder carries nothing that could identify its entry.
        _require_exact_fields(value, label, PLACEHOLDER_SLOT_FIELDS, {})
        if value["placeholder"] is not True:
            raise LoreCodexPanelError(f"{label} placeholder must be true")
        return {"placeholder": True}
    return _validate_entry_slot(value, label, monster)


def _validate_group(value: Any, label: str, monster: bool) -> dict[str, Any]:
    _require_exact_fields(value, label, {"key", "label", "slots"}, {})
    key = _validated_key(value, "key", label)
    group_label = value["label"]
    if monster:
        group_label = _validated_label(value, "label", label)
    elif group_label is not None:
        raise LoreCodexPanelError(f"{label} label must be null outside the monster category")
    slots = value["slots"]
    if not isinstance(slots, list):
        raise LoreCodexPanelError(f"{label} slots must be a list")
    return {
        "key": key,
        "label": group_label,
        "slots": [
            _validate_slot(slot, f"{label} slot[{idx}]", monster)
            for idx, slot in enumerate(slots)
        ],
    }


def _validate_category(value: Any, index: int, expected_key: str) -> tuple[dict[str, Any], int]:
    label = f"category[{index}]"
    _require_exact_fields(value, label, {"key", "label", "discovered", "total", "groups"}, {})
    key = _require_str(value, "key", maximum=LORE_CODEX_MAX_KEY_CODE_POINTS)
    if key != expected_key:
        raise LoreCodexPanelError(f"{label} key must be {expected_key!r}, got {key!r}")
    monster = key == MONSTER_CATEGORY
    category_label = _validated_label(value, "label", label)

    groups = value["groups"]
    if not isinstance(groups, list):
        raise LoreCodexPanelError(f"{label} groups must be a list")
    if monster:
        if len(groups) > LORE_CODEX_MAX_GROUPS_PER_CATEGORY:
            raise LoreCodexPanelError(
                f"{label} groups must hold at most {LORE_CODEX_MAX_GROUPS_PER_CATEGORY} items"
            )
    elif len(groups) != 1:
        raise LoreCodexPanelError(f"{label} must hold exactly one group")
    validated_groups = [
        _validate_group(group, f"{label} group[{idx}]", monster)
        for idx, group in enumerate(groups)
    ]
    group_keys = [group["key"] for group in validated_groups]
    if len(set(group_keys)) != len(group_keys):
        raise LoreCodexPanelError(f"{label} group keys must be unique")

    slots = [slot for group in validated_groups for slot in group["slots"]]
    entry_keys = [slot["key"] for slot in slots if "key" in slot]
    if len(set(entry_keys)) != len(entry_keys):
        raise LoreCodexPanelError(f"{label} entry keys must be unique")

    total = _require_int(value, "total", minimum=0, maximum=MAX_SAFE_INTEGER)
    if total > LORE_CODEX_MAX_SLOTS_PER_CATEGORY:
        raise LoreCodexPanelError(
            f"{label} must hold at most {LORE_CODEX_MAX_SLOTS_PER_CATEGORY} slots"
        )
    if len(slots) > total:
        raise LoreCodexPanelError(
            f"{label} holds {len(slots)} slots, more than its total ({total})"
        )
    discovered = _require_int(value, "discovered", minimum=0, maximum=MAX_SAFE_INTEGER)
    if discovered != len(entry_keys):
        raise LoreCodexPanelError(
            f"{label} discovered ({discovered}) does not match its entry slots ({len(entry_keys)})"
        )
    return (
        {
            "key": key,
            "label": category_label,
            "discovered": discovered,
            "total": total,
            "groups": validated_groups,
        },
        len(slots),
    )


def validate_lore_codex(payload: Any) -> dict[str, Any]:
    """Validate one exact available ``lore_codex`` payload.

    Returns a normalized payload or raises :class:`LoreCodexPanelError`. The
    common unavailable form is NOT accepted here; the registry handles it.
    """
    _require_exact_fields(
        payload,
        "lore_codex panel",
        {"schema_version", "available", "discovered_total", "total", "categories"},
        {},
    )
    if (
        _require_int(payload, "schema_version", minimum=1, maximum=MAX_SAFE_INTEGER)
        != LORE_CODEX_SCHEMA_VERSION
    ):
        raise LoreCodexPanelError("unsupported lore_codex schema_version")
    if not _require_bool(payload, "available"):
        raise LoreCodexPanelError("available must be true for the codex form")

    categories = payload["categories"]
    if not isinstance(categories, list) or len(categories) != len(LORE_CODEX_CATEGORIES):
        raise LoreCodexPanelError(
            f"categories must be a list of exactly {len(LORE_CODEX_CATEGORIES)} categories"
        )
    validated_categories = []
    slot_count = 0
    for idx, (category, expected_key) in enumerate(zip(categories, LORE_CODEX_CATEGORIES)):
        validated, slots = _validate_category(category, idx, expected_key)
        validated_categories.append(validated)
        slot_count += slots

    discovered_total = _require_int(
        payload, "discovered_total", minimum=0, maximum=MAX_SAFE_INTEGER
    )
    expected_discovered = sum(category["discovered"] for category in validated_categories)
    if discovered_total != expected_discovered:
        raise LoreCodexPanelError(
            f"discovered_total ({discovered_total}) does not equal the sum of "
            f"category discovered counts ({expected_discovered})"
        )
    total = _require_int(payload, "total", minimum=0, maximum=MAX_SAFE_INTEGER)
    expected_total = sum(category["total"] for category in validated_categories)
    if total != expected_total:
        raise LoreCodexPanelError(
            f"total ({total}) does not equal the sum of category totals ({expected_total})"
        )
    # The top-level total bounds the untrimmed slot count, and therefore the
    # shipped slot count as well (each category holds at most its total).
    if total > LORE_CODEX_MAX_TOTAL_SLOTS or slot_count > LORE_CODEX_MAX_TOTAL_SLOTS:
        raise LoreCodexPanelError(
            f"the codex must hold at most {LORE_CODEX_MAX_TOTAL_SLOTS} slots in total"
        )

    result = {
        "schema_version": LORE_CODEX_SCHEMA_VERSION,
        "available": True,
        "discovered_total": discovered_total,
        "total": total,
        "categories": validated_categories,
    }
    if json_byte_size(result) > MAX_CANONICAL_JSON_BYTES:
        raise LoreCodexPanelError("lore_codex payload exceeds the OOB envelope limit")
    return result


# ---------------------------------------------------------------------------
# Presenter
# ---------------------------------------------------------------------------


def _scene_archetype_for(category: str, key: str) -> str | None:
    """The declared scene archetype of one region or anchor, or ``None``."""
    from world.maps.geography import current

    snapshot = current()
    if category == "region":
        region = snapshot.regions.get(key)
        return region.scene_archetype if region is not None else None
    declaration = snapshot.locations.locations.get(key)
    return declaration.scene_archetype if declaration is not None else None


def _build_art(category: str, key: str) -> dict | None:
    if category == MONSTER_CATEGORY:
        if not is_registered_monster_visual_key(key):
            return None
        return describe_portrait(monster_subject_for(key))
    if category in ("region", "anchor"):
        archetype = _scene_archetype_for(category, key)
        if archetype is None or archetype not in scene_archetypes.SCENE_ARCHETYPE_REGISTRY:
            return None
        # An untrusted codex identity never authorizes retained room content.
        return describe_scene(
            SceneTarget(
                identity=f"codex:{category}:{key}",
                trusted_identity=False,
                archetype=archetype,
                room_art_key=None,
                room_binding_invalid=False,
            )
        )
    return None


def _slot_art(actor: Any, category: str, key: str) -> dict | None:
    """The existing art descriptor of one discovered entry, or ``None``.

    A pure read of whatever the art pipelines already recorded: nothing is
    enqueued or written. Any failure, including a descriptor the shared
    artwork validator rejects, nulls this slot's art only and is logged.
    """
    try:
        art = _build_art(category, key)
        return validate_artwork(art) if art is not None else None
    except Exception as error:
        log_warn(
            "lore_codex_art_failed",
            exc=error,
            context={"char": str(getattr(actor, "pk", "?")), "category": category, "key": key},
        )
        return None


def _entry_slot(actor: Any, category: str, key: str, defeated: set[str]) -> dict[str, Any]:
    if category == MONSTER_CATEGORY:
        stage = "defeated" if key in defeated else "sighted"
        card, locked = species_card(key, stage)
    else:
        stage = None
        card, locked = lore_card(category, key), ()
    return {
        "key": key,
        "title": card["display_name_zh"],
        "stage": stage,
        "art": _slot_art(actor, category, key),
        "card": [{"name": name, "value": value} for name, value in card.items()],
        "locked_fields": list(locked),
    }


def _monster_groups(registry: Any, slots: dict[str, dict]) -> list[dict[str, Any]]:
    """Group species slots by default variant tier in tier registry order."""
    by_tier: dict[str, list[dict]] = {}
    for key, species in registry.items():
        tier = MONSTER_VARIANT_REGISTRY[species.default_variant_key].threat_tier
        if tier not in MONSTER_TIER_REGISTRY:
            raise LoreCodexPanelError(f"species {key!r} names unknown threat tier {tier!r}")
        by_tier.setdefault(tier, []).append(slots[key])
    return [
        {"key": tier_key, "label": tier.display_name_zh, "slots": by_tier[tier_key]}
        for tier_key, tier in MONSTER_TIER_REGISTRY.items()
        if tier_key in by_tier
    ]


def _trim_to_envelope(payload: dict[str, Any]) -> None:
    """Drop trailing placeholders, then entry art, until the payload fits.

    Placeholders go first, scanning categories, groups and slots in reverse;
    then ``art`` becomes null on entry slots from the last one backwards.
    Counts are never touched. The size is measured once and maintained
    incrementally (compact JSON: an element plus its separating comma).
    """
    size = json_byte_size(payload)
    if size <= MAX_CANONICAL_JSON_BYTES:
        return
    placeholders: list[tuple[list, int]] = []
    entries: list[dict] = []
    for category in payload["categories"]:
        for group in category["groups"]:
            for index, slot in enumerate(group["slots"]):
                if "placeholder" in slot:
                    placeholders.append((group["slots"], index))
                else:
                    entries.append(slot)
    placeholder_bytes = json_byte_size({"placeholder": True})
    while size > MAX_CANONICAL_JSON_BYTES and placeholders:
        slots, index = placeholders.pop()
        size -= placeholder_bytes + (1 if len(slots) > 1 else 0)
        del slots[index]
    null_bytes = json_byte_size(None)
    while size > MAX_CANONICAL_JSON_BYTES and entries:
        slot = entries.pop()
        if slot["art"] is None:
            continue
        size -= json_byte_size(slot["art"]) - null_bytes
        slot["art"] = None
    if size > MAX_CANONICAL_JSON_BYTES:
        raise LoreCodexPanelError("lore_codex payload exceeds the OOB envelope limit")


def lore_codex_presenter(context: PresentationContext) -> dict[str, Any]:
    """Return the exact available ``lore_codex`` panel for the puppet.

    Host-independent and read-only. Reads the discovered and defeated
    records tolerantly, so a vanished key produces no slot, and degrades to
    the unavailable form on a corrupt record without rewriting stored data.
    """
    actor = context.actor
    if actor is None:
        raise PanelUnavailableError

    try:
        discovered = list_discovered(actor, tolerant=True)
        defeated = set(list_species_defeated(actor, tolerant=True))
    except LoreRecordError:
        raise PanelUnavailableError from None

    by_category: dict[str, set[str]] = {cat: set() for cat in LORE_CODEX_CATEGORIES}
    for cat, key in discovered:
        by_category[cat].add(key)

    categories: list[dict[str, Any]] = []
    for cat in LORE_CODEX_CATEGORIES:
        registry = CODE_CATEGORIES[cat].registry
        # Only registry keys are iterated: a recorded key absent from the
        # registry produces nothing, and art is built for entries only.
        slots = {
            key: (
                _entry_slot(actor, cat, key, defeated)
                if key in by_category[cat]
                else {"placeholder": True}
            )
            for key in registry
        }
        if cat == MONSTER_CATEGORY:
            groups = _monster_groups(registry, slots)
        else:
            groups = [{"key": cat, "label": None, "slots": list(slots.values())}]
        categories.append(
            {
                "key": cat,
                "label": CATEGORY_LABELS[cat],
                "discovered": sum(1 for slot in slots.values() if "key" in slot),
                "total": len(slots),
                "groups": groups,
            }
        )

    payload = {
        "schema_version": LORE_CODEX_SCHEMA_VERSION,
        "available": True,
        "discovered_total": sum(category["discovered"] for category in categories),
        "total": sum(category["total"] for category in categories),
        "categories": categories,
    }
    _trim_to_envelope(payload)
    return validate_lore_codex(payload)
