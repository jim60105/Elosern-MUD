"""Validated equipment-effect rulebook (add-equipment-effect-rulebook D1-D4).

One entry per registered equipment item, keyed by the item key, holding the
closed field vocabulary of the parent design (§5/§6). The lore registry owns
identity (the ``EquipmentModifierKey`` binding); this rulebook owns every
magnitude. The loader mirrors ``world.rules.items.load_item_effect_rules``:

- a single ``load_equipment_effect_rules`` with a path override for deviant
  rulebook tests, idempotent ``reload_equipment_effect_rules`` re-validation;
- closed vocabularies everywhere (entry fields, adjustment fields, gauge
  targets, budget rarities and columns) — unknown keys fail the load;
- per-column budgets keyed by the item's registry rarity, consulted ONLY at
  load time; rarity is never read by any runtime resolution path;
- the triple bijection equipment key ↔ modifier key ↔ rulebook entry,
  validated over an injectable registry so duplicate-binding rejection is
  testable without mutating production data;
- ``immune`` / ``attached_buffs`` keys must resolve in the buff rulebook, and
  one entry may never immunise a buff it also attaches.

P2 (wire-equipment-combat-modifiers) makes the combat adjustment fields and
gauge caps live through exactly two pure read accessors —
:func:`equipment_adjustments` and :func:`equipment_gauge_caps` — so no
consumer re-implements equipment math. P3 (add-equipment-immunity-and-attached-buffs)
owns the immunity predicate, the attached-instance projection, and the
adjustment-prose formatter. P4 (add-equipment-sexual-effects) lands the
sexual overlay accessors: :func:`equipment_exposure_bias`,
:func:`effective_exposure`, and :func:`equipment_pleasure_gain`. A structural
inertness test allowlists the change-authorized consumers; every rulebook
field now has its owning consumer, so no field may be folded into an
accessor outside its owner's surface.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import yaml

from world.lore.items import ITEM_REGISTRY, EquipmentModifierKey, ItemDefinition, ItemRarity
from world.rules.buffs import BUFF_DEFINITIONS, BuffDefinition

_RULEBOOK_PATH = Path(__file__).parent / "rulebook" / "equipment_effects.yaml"

# One gauge cap may not exceed this absurd ceiling regardless of the budgets
# table; the loader rejects larger magnitudes so a malformed rulebook can
# never smuggle an unbounded gear ceiling into a future consumer.
MAX_GAUGE_CAP = 9_999

# Budget cells are sanity-bounded the same way: they are authored balance, so
# an unbounded budget cell is malformed data, not a balance opinion.
MAX_BUDGET_CEILING = 1_000

# Signed percent strings carry an explicit sign: "-10%", "+15%". Bare digits,
# unsigned percents, and floats are all malformed by construction. The digit
# class is ASCII-only on purpose: Unicode decimal digits are a different
# vocabulary and int() would silently accept them.
_PERCENT_RE = re.compile(r"^[+-][0-9]+%$")

_ENTRY_FIELDS = frozenset(
    {"adjustments", "gauge_caps", "immune", "attached_buffs", "exposure_bias"}
)
_ADJUSTMENT_FIELDS = frozenset(
    {
        "atk_phys",
        "defense",
        "magic_level",
        "agility",
        "mp_cost",
        "sp_cost",
        "pleasure_gain",
        "heal_gain",
    }
)
# Adjustment fields whose value is a percent string ONLY; `agility` (in
# _ADJUSTMENT_FIELDS) alone accepts either kind, and the kind selects the
# budget column.
_PERCENT_FIELDS = frozenset({"mp_cost", "sp_cost", "pleasure_gain", "heal_gain"})
_SOFT_PERCENT_FIELDS = frozenset({"pleasure_gain", "heal_gain"})
_GAUGE_TARGETS = frozenset({"hp", "mp", "sp"})
_BUDGET_RARITIES = frozenset(rarity.value for rarity in ItemRarity)
_BUDGET_COLUMNS = frozenset({"flat", "percent", "soft_percent", "bias", "gauge"})


class EquipmentEffectsRulebookError(ValueError):
    """The equipment-effect rulebook is malformed, unknown, or out of bounds."""


@dataclass(frozen=True)
class EquipmentEffectRule:
    """One validated equipment entry.

    ``adjustments`` values keep their authored kind: ``int`` for flat values
    and ``str`` for percent strings. All collections are read-only mirrors so
    a consumer can never mutate the loaded rulebook.
    """

    adjustments: Mapping[str, int | str]
    gauge_caps: Mapping[str, int]
    immune: tuple[str, ...]
    attached_buffs: tuple[str, ...]
    exposure_bias: int


def _require_int(
    value: Any, field: str, *, minimum: int, maximum: int
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise EquipmentEffectsRulebookError(
            f"{field} must be an integer in [{minimum}, {maximum}], got {value!r}"
        )
    if not minimum <= value <= maximum:
        raise EquipmentEffectsRulebookError(
            f"{field} must be an integer in [{minimum}, {maximum}], got {value!r}"
        )
    return value


def _require_percent(value: Any, field: str) -> int:
    """Validate a signed percent string and return its integer magnitude."""
    if not isinstance(value, str) or not _PERCENT_RE.fullmatch(value):
        raise EquipmentEffectsRulebookError(
            f"{field} must be a signed percent string like '+5%', got {value!r}"
        )
    return int(value[:-1])


def _require_string_list(value: Any, field: str) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, list):
        raise EquipmentEffectsRulebookError(
            f"{field} must be a list of buff keys, got {value!r}"
        )
    for member in value:
        if not isinstance(member, str):
            raise EquipmentEffectsRulebookError(
                f"{field} must contain only buff-key strings, got {member!r}"
            )
    return tuple(value)



def _validate_budgets(raw: Any) -> dict[str, dict[str, int]]:
    """Validate the budgets table: five rarities, five non-negative columns.

    The `bias` column may be 0 (common gear grants no exposure at all);
    every other column is a positive ceiling.
    """
    if not isinstance(raw, dict):
        raise EquipmentEffectsRulebookError(
            f"budgets must be a mapping of rarity to columns, got {raw!r}"
        )
    unknown = set(raw) - _BUDGET_RARITIES
    if unknown:
        raise EquipmentEffectsRulebookError(
            f"budgets name unknown rarities: {sorted(unknown)}"
        )
    missing = _BUDGET_RARITIES - set(raw)
    if missing:
        raise EquipmentEffectsRulebookError(
            f"budgets are missing rarities: {sorted(missing)}"
        )
    budgets: dict[str, dict[str, int]] = {}
    for rarity in sorted(raw):
        columns = raw[rarity]
        if not isinstance(columns, dict):
            raise EquipmentEffectsRulebookError(
                f"budgets.{rarity} must be a mapping of columns, got {columns!r}"
            )
        unknown = set(columns) - _BUDGET_COLUMNS
        if unknown:
            raise EquipmentEffectsRulebookError(
                f"budgets.{rarity} name unknown columns: {sorted(unknown)}"
            )
        missing = _BUDGET_COLUMNS - set(columns)
        if missing:
            raise EquipmentEffectsRulebookError(
                f"budgets.{rarity} are missing columns: {sorted(missing)}"
            )
        budgets[rarity] = {
            column: _require_int(
                columns[column],
                f"budgets.{rarity}.{column}",
                minimum=0 if column == "bias" else 1,
                maximum=MAX_BUDGET_CEILING,
            )
            for column in _BUDGET_COLUMNS
        }
    return budgets


def _validate_entry(
    item_key: str,
    raw: Any,
    budgets: Mapping[str, Mapping[str, int]],
    rarity: str,
    buff_definitions: Mapping[str, BuffDefinition],
) -> EquipmentEffectRule:
    """Validate one entry and budget-check every value against its column."""
    if not isinstance(raw, dict):
        raise EquipmentEffectsRulebookError(
            f"effects.{item_key} must be a mapping, got {raw!r}"
        )
    unknown = set(raw) - _ENTRY_FIELDS
    if unknown:
        raise EquipmentEffectsRulebookError(
            f"effects.{item_key} contains unknown fields: {sorted(unknown)}"
        )

    ceilings = budgets[rarity]

    adjustments: dict[str, int | str] = {}
    raw_adjustments = raw.get("adjustments", {})
    if not isinstance(raw_adjustments, dict):
        raise EquipmentEffectsRulebookError(
            f"effects.{item_key}.adjustments must be a mapping, "
            f"got {raw_adjustments!r}"
        )
    unknown = set(raw_adjustments) - _ADJUSTMENT_FIELDS
    if unknown:
        raise EquipmentEffectsRulebookError(
            f"effects.{item_key}.adjustments contain unknown fields: "
            f"{sorted(unknown)}"
        )
    for field in sorted(raw_adjustments):
        value = raw_adjustments[field]
        if field in _PERCENT_FIELDS:
            magnitude = _require_percent(value, f"effects.{item_key}.{field}")
            column = "soft_percent" if field in _SOFT_PERCENT_FIELDS else "percent"
        elif field == "agility":
            if isinstance(value, str):
                magnitude = _require_percent(value, f"effects.{item_key}.agility")
                column = "percent"
            else:
                magnitude = _require_int(
                    value,
                    f"effects.{item_key}.agility",
                    minimum=-MAX_BUDGET_CEILING,
                    maximum=MAX_BUDGET_CEILING,
                )
                column = "flat"
        else:
            magnitude = _require_int(
                value,
                f"effects.{item_key}.{field}",
                minimum=-MAX_BUDGET_CEILING,
                maximum=MAX_BUDGET_CEILING,
            )
            column = "flat"
        if abs(magnitude) > ceilings[column]:
            raise EquipmentEffectsRulebookError(
                f"effects.{item_key}.{field} value {value!r} exceeds the "
                f"{rarity} {column} budget of {ceilings[column]}"
            )
        adjustments[field] = value

    raw_caps = raw.get("gauge_caps", {})
    if not isinstance(raw_caps, dict):
        raise EquipmentEffectsRulebookError(
            f"effects.{item_key}.gauge_caps must be a mapping, got {raw_caps!r}"
        )
    unknown = set(raw_caps) - _GAUGE_TARGETS
    if unknown:
        raise EquipmentEffectsRulebookError(
            f"effects.{item_key}.gauge_caps target unknown gauges: {sorted(unknown)}"
        )
    gauge_caps: dict[str, int] = {}
    for target in sorted(raw_caps):
        cap = _require_int(
            raw_caps[target],
            f"effects.{item_key}.gauge_caps.{target}",
            minimum=1,
            maximum=MAX_GAUGE_CAP,
        )
        if cap > ceilings["gauge"]:
            raise EquipmentEffectsRulebookError(
                f"effects.{item_key}.gauge_caps.{target} cap {cap} exceeds "
                f"the {rarity} gauge budget of {ceilings['gauge']}"
            )
        gauge_caps[target] = cap

    immune = _require_string_list(
        raw.get("immune", []), f"effects.{item_key}.immune"
    )
    attached = _require_string_list(
        raw.get("attached_buffs", []), f"effects.{item_key}.attached_buffs"
    )
    for label, keys in (("immune", immune), ("attached_buffs", attached)):
        unresolved = [key for key in keys if key not in buff_definitions]
        if unresolved:
            raise EquipmentEffectsRulebookError(
                f"effects.{item_key}.{label} name buff keys absent from the "
                f"buff rulebook: {unresolved}"
            )
        if len(set(keys)) != len(keys):
            raise EquipmentEffectsRulebookError(
                f"effects.{item_key}.{label} list duplicate buff keys: {list(keys)}"
            )
    contradicted = set(immune) & set(attached)
    if contradicted:
        raise EquipmentEffectsRulebookError(
            f"effects.{item_key} both immunises and attaches: {sorted(contradicted)}"
        )
    for buff_key in attached:
        buff_definition = buff_definitions.get(buff_key)
        if buff_definition is None:
            continue
        bounds = buff_definition.modifiers.get("bounds", ())
        bound_items = bounds if isinstance(bounds, list) else [bounds]
        for modifier in bound_items:
            if not isinstance(modifier, Mapping):
                continue
            target = modifier.get("target")
            if target in _GAUGE_TARGETS:
                raise EquipmentEffectsRulebookError(
                    f"effects.{item_key}.attached_buffs buff {buff_key!r} carries "
                    f"a gauge-bound modifier ({target}); attached instances must "
                    "never carry gauge-ceiling modifiers (design D2)"
                )

    bias = _require_int(
        raw.get("exposure_bias", 0),
        f"effects.{item_key}.exposure_bias",
        minimum=-MAX_BUDGET_CEILING,
        maximum=MAX_BUDGET_CEILING,
    )
    if abs(bias) > ceilings["bias"]:
        raise EquipmentEffectsRulebookError(
            f"effects.{item_key}.exposure_bias {bias} exceeds the {rarity} "
            f"bias budget of {ceilings['bias']}"
        )

    return EquipmentEffectRule(
        adjustments=MappingProxyType(adjustments),
        gauge_caps=MappingProxyType(gauge_caps),
        immune=immune,
        attached_buffs=attached,
        exposure_bias=bias,
    )


def validate_equipment_effect_rules(
    document: Any,
    registry: Mapping[str, ItemDefinition],
    buff_definitions: Mapping[str, BuffDefinition],
) -> dict[EquipmentModifierKey, EquipmentEffectRule]:
    """Validate a parsed rulebook document against an equipment registry.

    Registry and buff-definition mapping are injectable so rejection tests
    (including the duplicate-binding case, unreachable through the production
    dict) run against synthetic registries without mutating
    ``ITEM_REGISTRY``. Budget lookup uses each entry key's registry rarity; an
    override document can therefore never redefine rarity semantics. The
    definition mapping backs the immune/attached reference checks and the P3
    gauge-bound guard for attached buffs.
    """
    if not isinstance(document, dict):
        raise EquipmentEffectsRulebookError(
            f"rulebook must be a mapping, got {document!r}"
        )
    unknown = set(document) - {"budgets", "effects"}
    if unknown:
        raise EquipmentEffectsRulebookError(
            f"rulebook contains unknown top-level keys: {sorted(unknown)}"
        )
    if set(document) != {"budgets", "effects"}:
        raise EquipmentEffectsRulebookError(
            "rulebook must carry exactly the 'budgets' and 'effects' keys, "
            f"got {sorted(document)}"
        )
    budgets = _validate_budgets(document["budgets"])
    raw_effects = document["effects"]
    if not isinstance(raw_effects, dict):
        raise EquipmentEffectsRulebookError(
            f"effects must be a mapping, got {raw_effects!r}"
        )

    # Triple bijection: equipment item key ↔ modifier key ↔ entry key.
    bindings: dict[EquipmentModifierKey, list[str]] = {}
    for item_key, definition in registry.items():
        if definition.equipment_slot is None:
            if definition.modifier_key is not None:
                raise EquipmentEffectsRulebookError(
                    f"item {item_key!r} is not equipment but binds "
                    f"{definition.modifier_key!r}"
                )
            continue
        if definition.modifier_key is None:
            raise EquipmentEffectsRulebookError(
                f"equipment item {item_key!r} has no modifier key"
            )
        # Identity is enforced at load, not construction: the constructor
        # accepts any canonical enum member so test fixtures may reuse one
        # (design.md D-policy), but a REGISTERED item may not borrow another
        # item's binding — that would hijack the other item's effects (and
        # its budget row) once consumers arrive.
        if definition.modifier_key.value != item_key:
            raise EquipmentEffectsRulebookError(
                f"equipment item {item_key!r} binds {definition.modifier_key!r} "
                f"whose value {definition.modifier_key.value!r} is not its own key"
            )
        bindings.setdefault(definition.modifier_key, []).append(item_key)
    collapsed = {
        key.value: sorted(owners)
        for key, owners in bindings.items()
        if len(owners) > 1
    }
    if collapsed:
        raise EquipmentEffectsRulebookError(
            f"modifier keys bound by more than one equipment item: {collapsed}"
        )
    bound_keys = set(bindings)
    entry_keys = set(raw_effects)
    unbound = sorted(bound_keys - entry_keys, key=str)
    if unbound:
        raise EquipmentEffectsRulebookError(
            f"equipment modifier keys without a rulebook entry: {unbound}"
        )
    orphaned = sorted(entry_keys - bound_keys, key=str)
    if orphaned:
        raise EquipmentEffectsRulebookError(
            f"rulebook entries without an equipment binding: {orphaned}"
        )

    rules: dict[EquipmentModifierKey, EquipmentEffectRule] = {}
    for modifier_key in bound_keys:
        item_key = bindings[modifier_key][0]
        definition = registry[item_key]
        rarity = definition.presentation.rarity.value
        rules[modifier_key] = _validate_entry(
            item_key,
            raw_effects[modifier_key.value],
            budgets,
            rarity,
            buff_definitions,
        )
    return {key: rules[key] for key in sorted(rules, key=str)}


_equipped = {
    definition.key: definition
    for definition in ITEM_REGISTRY.values()
    if definition.equipment_slot is not None
}

# The canonical registry projection used by every production load: equipment
# definitions only, built once from the live registry.
_PRODUCTION_EQUIPMENT: Mapping[str, ItemDefinition] = MappingProxyType(_equipped)
# The canonical buff-definition projection for production loads: the
# validator checks immune/attached references and the P3 gauge-bound guard
# against the same definitions every gameplay read uses.
_PRODUCTION_BUFF_DEFINITIONS: Mapping[str, BuffDefinition] = MappingProxyType(
    BUFF_DEFINITIONS
)


class _UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate mapping keys at any nesting level.

    PyYAML's default mapping constructor silently keeps the LAST duplicate,
    so a rulebook reviewed by a human and the data actually loaded could
    disagree. Fail-loud contract: duplicates are malformed data.
    """

    def construct_mapping(self, node: Any, deep: bool = False) -> Any:
        seen: set[Any] = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise EquipmentEffectsRulebookError(
                    "duplicate YAML mapping key "
                    f"{key!r} at line {key_node.start_mark.line + 1}"
                )
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def load_equipment_effect_rules(
    path: Path | None = None,
) -> dict[EquipmentModifierKey, EquipmentEffectRule]:
    """Validate the canonical equipment-effect rulebook, or an override copy.

    An override path replaces rulebook DATA only; rarity and bindings still
    come from the live registry, so a deviant table can never redefine
    identity semantics. Fails loud with
    ``EquipmentEffectsRulebookError`` on any deviation.
    """
    source = _RULEBOOK_PATH if path is None else path
    document = yaml.load(source.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    return validate_equipment_effect_rules(
        document, _PRODUCTION_EQUIPMENT, _PRODUCTION_BUFF_DEFINITIONS
    )


_loaded = load_equipment_effect_rules()

# Immutable equipment-effect rulebook keyed by the closed registry vocabulary.
EQUIPMENT_EFFECT_RULES: dict[EquipmentModifierKey, EquipmentEffectRule] = _loaded


# The bundle vocabulary this change activates. ``pleasure_gain`` /
# ``exposure_bias`` / ``immune`` / ``attached_buffs`` stay dormant until their
# owning changes (P3/P4) land and must NOT be folded here. ``agility`` splits
# by authored kind: a percent string merges under ``agility`` and a flat
# integer under ``agility_flat``, because the shared merge in
# ``combat_modifiers._merge_adjustments`` silently replaces values of
# different kinds and the percent consumers reject flat ints.
_BUNDLE_FLAT_FIELDS = frozenset({"atk_phys", "defense", "magic_level"})
_BUNDLE_PERCENT_FIELDS = frozenset({"mp_cost", "sp_cost", "heal_gain"})


def _worn_item_keys(equipment: Mapping) -> list[str]:
    """Return every worn item key of one normalized equipment mapping."""
    keys: list[str] = []
    for slot_key in ("weapon_main", "weapon_off", "armor"):
        value = equipment[slot_key]
        if value is not None:
            keys.append(value)
    keys.extend(equipment["accessories"])
    return keys


def _worn_rules(entity: Any) -> list[EquipmentEffectRule]:
    """Resolve one entity's worn equipment to its loaded effect rules.

    Fail-closed: malformed equipment storage (``normalized_equipment`` →
    ``None``) reads as "nothing worn". A registry-validated mapping only ever
    holds equipment keys with bound modifier keys (the normalization checks
    registry membership and slot fit), so every lookup resolves.
    """
    from world.rules.equipment import normalized_equipment

    equipment = normalized_equipment(entity)
    if equipment is None:
        return []
    rules: list[EquipmentEffectRule] = []
    for item_key in _worn_item_keys(equipment):
        definition = ITEM_REGISTRY[item_key]
        modifier_key = definition.modifier_key
        if modifier_key is None:  # pragma: no cover - registry invariant
            continue
        rules.append(EQUIPMENT_EFFECT_RULES[modifier_key])
    return rules


def equipment_adjustments(entity: Any) -> Mapping[str, int | str]:
    """Return the pure additive adjustment bundle of one entity's worn gear.

    The single accessor converting worn equipment into combat adjustments
    (wire-equipment-combat-modifiers): every consumer reads the merged
    bundle from ``combat_modifiers`` — none may compute a parallel equipment
    formula. Flat fields sum as integers; percent fields sum and re-render as
    signed percent strings; flat ``agility`` lands under ``agility_flat``
    (see ``_BUNDLE_FLAT_FIELDS``). Malformed storage yields the empty bundle.
    Writes nothing.
    """
    flats: dict[str, int] = {}
    percents: dict[str, int] = {}
    agility_flat_total = 0
    for rule in _worn_rules(entity):
        for field, value in rule.adjustments.items():
            if field in _BUNDLE_FLAT_FIELDS:
                flats[field] = flats.get(field, 0) + int(value)
            elif field in _BUNDLE_PERCENT_FIELDS:
                percents[field] = percents.get(field, 0) + int(value[:-1])
            elif field == "agility":
                if isinstance(value, str):
                    percents["agility"] = percents.get("agility", 0) + int(value[:-1])
                else:
                    agility_flat_total += int(value)
            # pleasure_gain never rides the combat bundle (P4 folds it
            # through equipment_pleasure_gain); every other adjustment
            # field is already covered by the branches above.
    bundle: dict[str, int | str] = dict(flats)
    if agility_flat_total:
        bundle["agility_flat"] = agility_flat_total
    for field, total in percents.items():
        bundle[field] = f"{total:+d}%"
    return MappingProxyType(bundle)


def equipment_gauge_caps(entity: Any) -> Mapping[str, int]:
    """Return the additive per-gauge caps of one entity's worn gear.

    The single accessor for gauge-cap reads (the ceiling sync in
    ``world.rules.equipment`` is its only consumer). Positive-only by loader
    contract; malformed storage yields the empty mapping. Writes nothing.
    """
    caps: dict[str, int] = {}
    for rule in _worn_rules(entity):
        for target, cap in rule.gauge_caps.items():
            caps[target] = caps.get(target, 0) + int(cap)
    return MappingProxyType(caps)


def reload_equipment_effect_rules(path: Path | None = None) -> None:
    """Re-validate and re-mirror the rulebook (idempotent startup sync)."""
    global EQUIPMENT_EFFECT_RULES
    EQUIPMENT_EFFECT_RULES = load_equipment_effect_rules(path)

def equipment_modifier_layers(modifier_key: Any) -> Mapping[str, tuple[str, int]] | None:
    """Break one modifier key into per-stat named-layer contributions.

    The sanctioned single-source surface for the stat-breakdown read model:
    returns ``stat_key -> (kind, amount)`` for one loaded rule — ``flat`` for
    authored integer adjustments and gauge caps, ``pct`` for authored agility
    percent strings — or ``None`` when the modifier key has no rulebook
    entry. Zero contributions are omitted. Pure and read-only.
    """
    rule = EQUIPMENT_EFFECT_RULES.get(modifier_key)
    if rule is None:
        return None
    layers: dict[str, tuple[str, int]] = {}
    for stat_key, value in rule.adjustments.items():
        if isinstance(value, str):
            layers[stat_key] = ("pct", int(value[:-1]))
        elif isinstance(value, int) and value:
            layers[stat_key] = ("flat", value)
    for stat_key, cap in rule.gauge_caps.items():
        if cap:
            layers[stat_key] = ("flat", cap)
    return MappingProxyType(layers)


def worn_item_keys(entity: Any) -> frozenset[str]:
    """Pure fail-closed read of the currently worn item keys.

    Malformed equipment storage yields no keys (broken storage never grants
    protection). The equipment import stays function-local so this module's
    module-level dependencies remain lore/rulebook-only.
    """
    from world.rules.equipment import normalized_equipment

    equipment = normalized_equipment(entity)
    if equipment is None:
        return frozenset()
    worn: set[str] = set()
    for slot in ("weapon_main", "weapon_off", "armor"):
        value = equipment.get(slot)
        if isinstance(value, str) and value:
            worn.add(value)
    worn.update(
        value for value in equipment.get("accessories", ()) if isinstance(value, str)
    )
    return frozenset(worn)


def equipment_immune_buff_keys(entity: Any) -> frozenset[str]:
    """Union of ``immune`` keys over the entity's currently worn equipment.

    Pure: reads stored state without materializing handlers and writes
    nothing. Grant-time-only semantics: already-applied debuffs are never
    paused, removed, or altered by this predicate.
    """
    immune: set[str] = set()
    for item_key in worn_item_keys(entity):
        definition = ITEM_REGISTRY.get(item_key)
        if definition is None or definition.modifier_key is None:
            continue
        rule = EQUIPMENT_EFFECT_RULES.get(definition.modifier_key)
        if rule is not None:
            immune.update(rule.immune)
    return frozenset(immune)


def equipment_exposure_bias(entity: Any) -> int:
    """Sum the signed ``exposure_bias`` of the entity's currently worn gear.

    Pure: reads stored state through the fail-closed normalization without
    materializing handlers and writes nothing. Malformed storage contributes
    zero bias (broken storage never rewrites how exposed the actor looks).
    """
    return sum(rule.exposure_bias for rule in _worn_rules(entity))


def equipment_pleasure_gain(entity: Any) -> int:
    """Sum the signed ``pleasure_gain`` percents of the worn equipment.

    The single equipment-only pleasure source (P4 design D3): the pleasure
    funnel receives this integer as its ``pleasure_percent`` parameter and
    nothing else. It deliberately does NOT ride the combat bundle — the
    evaluator's key-set stays combat-only. Pure; malformed storage yields 0.
    """
    total = 0
    for rule in _worn_rules(entity):
        value = rule.adjustments.get("pleasure_gain")
        if value is not None:
            total += int(value[:-1])
    return total


def effective_exposure(entity: Any) -> Any:
    """Return the entity's effective exposure: stored ordinal + worn bias, clamped.

    One pure read-time overlay (P4 design D1): the stored ``EXPOSURE_LEVELS``
    ordinal — read through the neutral shared reader, so no ``entity.sexual``
    handler is ever materialized and nothing is written — shifted by
    :func:`equipment_exposure_bias` and clamped to the vocabulary bounds.
    Malformed storage contributes zero bias, so the result is the stored
    level itself. A level that cannot be resolved at all is passed through
    unchanged (the condition builders skip unresolvable fields exactly as
    before), and a stored record whose vocabulary differs from
    ``EXPOSURE_LEVELS`` is passed through with its OWN vocabulary — corrupt
    storage is never reinterpreted as a canonical band; rule matching
    rejects it exactly as the pre-overlay evaluator did (fail-loud on a
    threshold lookup), instead of silently firing on a relabeled ordinal.
    The returned view is the shared immutable ``StoredLevel``, the
    same comparison-parity type both context builders use.
    """
    from world.lore.sexual_vocab import EXPOSURE_LEVELS
    from world.rules.stored_sexual_reads import StoredLevel, stored_sexual_level

    stored = stored_sexual_level(entity, "exposure")
    if isinstance(stored, str):
        if stored not in EXPOSURE_LEVELS:
            return stored
        stored = StoredLevel(EXPOSURE_LEVELS.index(stored), EXPOSURE_LEVELS)
    if not isinstance(stored, StoredLevel):
        return stored
    if tuple(stored.levels) != EXPOSURE_LEVELS:
        # Fail-closed on a corrupt vocabulary: never relabel the ordinal
        # into the canonical bands (see docstring).
        return stored
    ordinal = min(
        len(EXPOSURE_LEVELS) - 1,
        max(0, stored.value + equipment_exposure_bias(entity)),
    )
    return StoredLevel(ordinal, EXPOSURE_LEVELS)


def attached_buff_instances(
    equipment: Mapping[str, Any],
) -> dict[str, tuple[str, str]]:
    """Map one normalized equipment mapping to its required attached instances.

    Returns ``{f"{buff_key}:{item_key}": (buff_key, item_key)}`` for every
    worn item whose rulebook entry declares attached buffs. Pure dictionary
    math over the canonical equipment shape (three singleton slots plus the
    accessory list), so ``toggle_equipment`` can compute added/removed
    instance-key sets from its before/after plans while owning every write.
    """
    instances: dict[str, tuple[str, str]] = {}

    def collect(item_key: str) -> None:
        definition = ITEM_REGISTRY.get(item_key)
        if definition is None or definition.modifier_key is None:
            return
        rule = EQUIPMENT_EFFECT_RULES.get(definition.modifier_key)
        if rule is None or not rule.attached_buffs:
            return
        for buff_key in rule.attached_buffs:
            instances[f"{buff_key}:{item_key}"] = (buff_key, item_key)

    for slot in ("weapon_main", "weapon_off", "armor"):
        value = equipment.get(slot)
        if isinstance(value, str) and value:
            collect(value)
    for value in equipment.get("accessories", ()):
        if isinstance(value, str) and value:
            collect(value)
    return instances


# Adjustment-prose vocabulary in one fixed order (P3 design D4): combat
# adjustments first, then gauge ceilings, then immunity. Fields whose
# presentation lands in later changes (sp_cost, pleasure_gain,
# exposure_bias) are deliberately absent from this list.
_PROSE_ADJUSTMENTS = (
    ("atk_phys", "攻擊"),
    ("defense", "防禦"),
    ("agility", "敏捷"),
    ("magic_level", "魔力"),
    ("mp_cost", "施法消耗"),
    ("heal_gain", "治療"),
)
_PROSE_GAUGES = (("hp", "生命上限"), ("mp", "法力上限"), ("sp", "體力上限"))


def _signed_number_text(value: int) -> str:
    """Render a signed flat integer with the U+2212 minus convention."""
    if value > 0:
        return f"+{value}"
    if value < 0:
        return f"−{abs(value)}"
    return ""


def _percent_text(value: str) -> str:
    """Render an authored signed percent string with the U+2212 minus."""
    if value.startswith("-") and not value.startswith("−"):
        return f"−{value[1:]}"
    return value


def equipment_adjustment_text(item_key: str) -> str:
    """Return one deterministic 正體中文 adjustment summary for an item.

    Segments are joined with 「｜」 in the fixed D4 vocabulary order; every
    number comes verbatim from the rulebook (no effective value is ever
    recomputed). Zero-valued numeric fields are omitted, immunity renders
    through the registered display labels, and non-equipment items, unknown
    keys, and entries with nothing displayable all return ``""``.
    """
    definition = ITEM_REGISTRY.get(item_key)
    if definition is None or definition.modifier_key is None:
        return ""
    rule = EQUIPMENT_EFFECT_RULES.get(definition.modifier_key)
    if rule is None:
        return ""
    segments: list[str] = []
    for field, label in _PROSE_ADJUSTMENTS:
        value = rule.adjustments.get(field)
        if value is None:
            continue
        if isinstance(value, str):
            if int(value[:-1]) == 0:
                continue
            segments.append(f"{label} {_percent_text(value)}")
        else:
            rendered = _signed_number_text(value)
            if rendered:
                segments.append(f"{label} {rendered}")
    for target, label in _PROSE_GAUGES:
        cap = rule.gauge_caps.get(target)
        if cap is not None and cap > 0:
            segments.append(f"{label} +{cap}")
    if rule.immune:
        # Function-local: status_display reaches this module's consumers
        # through combat_modifiers, so a module-level import would close a
        # cycle now that P2 made the adjustment accessor live.
        from world.rules.status_display import display_for

        labels = "、".join(display_for(key).label for key in rule.immune)
        segments.append(f"免疫{labels}")
    return "｜".join(segments)
