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

Until the owning changes (P2-P5) land, no gameplay module may import this
rulebook; a structural test enforces that inertness, with server bootstrap
validation as the only sanctioned startup consumer.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import yaml

from world.lore.items import ITEM_REGISTRY, EquipmentModifierKey, ItemDefinition, ItemRarity
from world.rules.buffs import BUFF_DEFINITIONS

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
    buff_keys: frozenset[str],
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
        unresolved = [key for key in keys if key not in buff_keys]
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
    buff_keys: frozenset[str],
) -> dict[EquipmentModifierKey, EquipmentEffectRule]:
    """Validate a parsed rulebook document against an equipment registry.

    Registry and buff-key set are injectable so rejection tests (including
    the duplicate-binding case, unreachable through the production dict) run
    against synthetic registries without mutating ``ITEM_REGISTRY``. Budget
    lookup uses each entry key's registry rarity; an override document can
    therefore never redefine rarity semantics.
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
            item_key, raw_effects[modifier_key.value], budgets, rarity, buff_keys
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
_PRODUCTION_BUFF_KEYS = frozenset(BUFF_DEFINITIONS)


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
        document, _PRODUCTION_EQUIPMENT, _PRODUCTION_BUFF_KEYS
    )


_loaded = load_equipment_effect_rules()

# Immutable equipment-effect rulebook keyed by the closed registry vocabulary.
EQUIPMENT_EFFECT_RULES: dict[EquipmentModifierKey, EquipmentEffectRule] = _loaded


def reload_equipment_effect_rules(path: Path | None = None) -> None:
    """Re-validate and re-mirror the rulebook (idempotent startup sync)."""
    global EQUIPMENT_EFFECT_RULES
    EQUIPMENT_EFFECT_RULES = load_equipment_effect_rules(path)
