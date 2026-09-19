"""Stat breakdown read model (expose-stat-breakdown-read-model).

Composes each panel stat from named layers while replaying the shipped
authoritative operations bit-for-bit; every unattributable accounting amount
fails the whole read closed.
"""

import math
from collections.abc import Mapping
from typing import Any

from world.lore.items import ITEM_REGISTRY
from world.rules.combat_modifiers import (
    _merge_adjustments,
    _PERCENT_RE,
)
from world.rules.equipment_effects import (
    equipment_adjustments,
    equipment_modifier_layers,
)
from world.rules.status_display import display_for
from world.skills.effects import StatMultiplyEffect
from world.skills.registry import SKILL_REGISTRY, SkillDef

from .assembly import _Assembly
from .models import (
    _BREAKDOWN_ROW_ORDER,
    _EQUIPMENT_SLOTS,
    _GAUGE_KEYS,
    _LAYER_KINDS,
    _LAYER_SOURCES,
    MAX_BREAKDOWN_ROWS,
    MAX_LAYERS_PER_STAT,
    StatusQueryError,
    StatBreakdownRow,
    StatLayer,
)
from .readers import _buff_active_rule_ids, _is_list_like, _read_guild_merit

# ---------------------------------------------------------------------------
# Stat breakdown (expose-stat-breakdown-read-model)
#
# This section composes each panel stat FROM its named layers while replaying
# the shipped authoritative operations bit-for-bit:
# ``SkillHandler.effective_value`` (stored-list skill fold + single final
# ``round``), ``combat._adjusted_attack``/``_adjusted_defense`` (skill
# effective value + merged rule-table flats), ``combat_modifiers``' agility
# pipeline (percent merge through ``_merge_adjustments``, then percent, then
# flat, floored at 0 — the ``adjusted_agility`` shape), and the gauge-ceiling
# reader ``_require_gauge``. ``_merge_adjustments`` and ``_PERCENT_RE`` are
# imported from their shipped homes as the parity anchors — never a parallel
# reimplementation.
# ---------------------------------------------------------------------------


def _stored_skill_fold(entity: Any) -> tuple[str, ...]:
    """Stored ownership keys in the shipped fold order (``effective_value``).

    Deliberately the raw ``db.skills`` lists only — NOT ``owned_keys()`` and
    NOT the innate keys: the shipped skill fold iterates ``dict.fromkeys``
    over the stored active+passive lists alone, so the replay can never drift
    even if an unlocked act or innate key were to carry a stat multiplier.
    """
    raw = entity.db.skills
    if not isinstance(raw, Mapping):
        raw = {}
    active = raw.get("active")
    passive = raw.get("passive")
    if not _is_list_like(active):
        active = ()
    if not _is_list_like(passive):
        passive = ()
    return tuple(dict.fromkeys((*active, *passive)))


def _matching_stat_multiplier(skill: SkillDef, stat_key: str) -> float | None:
    """The skill's single matching stat multiplier, fail-loud on duplicates.

    The ``StatusQueryError`` wrapper over the shipped handler's ``ValueError``
    keeps the duplicate-definition failure on the panel's fail-closed path.
    """
    multipliers = [
        effect.multiplier
        for effect in skill.parsed_effects
        if isinstance(effect, StatMultiplyEffect) and effect.trait == stat_key
    ]
    if not multipliers:
        return None
    if len(multipliers) > 1:
        raise StatusQueryError(
            f"skill {skill.key!r} defines duplicate stat multipliers for trait {stat_key!r}"
        )
    return multipliers[0]


def _grant_fields(grant: Any) -> tuple[str, str, float] | None:
    """Read one grant's ``(source_key, skill_key, scale)`` from dataclass or mapping.

    The shipped writer stores ``ConferredSkillGrant`` dataclasses; mapping
    fixtures ride the same fields. A malformed grant returns ``None`` so the
    fold skips it exactly as the shipped fold skips an unknown skill key.
    """
    source_key = getattr(grant, "source_key", None)
    skill_key = getattr(grant, "skill_key", None)
    scale = getattr(grant, "scale", None)
    if isinstance(grant, Mapping):
        source_key = grant.get("source_key", source_key)
        skill_key = grant.get("skill_key", skill_key)
        scale = grant.get("scale", scale)
    if not isinstance(source_key, str) or not isinstance(skill_key, str):
        return None
    if isinstance(scale, bool) or not isinstance(scale, (int, float)):
        return None
    return source_key, skill_key, float(scale)


def _merged_bundle(assembly: _Assembly) -> dict[str, Any]:
    """Merge matched rule bundles then the equipment bundle, shipped order.

    Byte-identical to ``combat_modifiers.evaluate_combat_modifiers`` for the
    same storage: ``_merge_adjustments`` (the shipped merge) over
    ``assembly.matches`` (the shipped matches) plus
    ``equipment_adjustments`` (the shipped pure gear read).
    """
    merged: dict[str, Any] = {}
    for _, adjustments in assembly.matches:
        merged = _merge_adjustments(merged, dict(adjustments))
    return _merge_adjustments(merged, dict(equipment_adjustments(assembly.entity)))


def _skill_layers(entity: Any, stat_key: str) -> tuple[list[StatLayer], float]:
    """Replay the shipped ``effective_value`` fold as named layers.

    Factors multiply into the running product in the shipped fold order; the
    returned DISPLAY list is sorted by ``(skill_key, source_key)`` (design D2)
    after the product is complete, which never moves a factor across the
    single final ``round``. A grant's layer carries ``（scale）`` so two grants
    of one skill stay distinct and non-zero-summing.
    """
    product = 1.0
    keyed: list[tuple[str, str, StatLayer]] = []
    for skill_key in _stored_skill_fold(entity):
        skill = SKILL_REGISTRY.get(skill_key)
        if skill is None:
            continue
        multiplier = _matching_stat_multiplier(skill, stat_key)
        if multiplier is not None:
            product *= multiplier
            keyed.append(
                (skill_key, "", StatLayer("skill", skill.label, "mult", multiplier))
            )
    for grant in entity.db.skill_grants or []:
        fields = _grant_fields(grant)
        if fields is None:
            continue
        source_key, skill_key, scale = fields
        source_skill = SKILL_REGISTRY.get(skill_key)
        if source_skill is None:
            continue
        source_multiplier = _matching_stat_multiplier(source_skill, stat_key)
        if source_multiplier is None:
            continue
        factor = source_multiplier * scale
        product *= factor
        name = f"{source_skill.label}（{scale:g}）"
        keyed.append(
            (skill_key, source_key, StatLayer("skill", name, "mult", factor))
        )
    keyed.sort(key=lambda entry: (entry[0], entry[1]))
    return [layer for _, _, layer in keyed], product


def _condition_layers(
    assembly: _Assembly, stat_key: str
) -> list[StatLayer]:
    """Per-rule named layers for one stat's matched rule-table contributions.

    Buff cache entries never feed stat layers directly (buff modifiers are
    rate/bounds/decay only); a buff reaches a stat row exclusively through a
    ``buff_active`` rule-table row, whose id classifies the layer's source
    kind as ``buff`` (sorted before ``rule``). Amounts ride exactly as the
    bundle holds them — already grant-scaled by ``matched_combat_modifiers``.
    """
    buff_rules = _buff_active_rule_ids()
    if stat_key == "agility":
        fields: tuple[str, ...] = ("agility", "agility_flat")
    elif stat_key in ("atk_phys", "defense", "magic_power"):
        fields = (stat_key,)
    else:
        return []
    entries: list[tuple[str, str, int | float, str]] = []
    for rule_id, adjustments in assembly.matches:
        for field in fields:
            value = adjustments.get(field)
            if value is None:
                continue
            kind = "pct" if isinstance(value, str) else "flat"
            entries.append(
                (
                    "buff" if rule_id in buff_rules else "rule",
                    rule_id,
                    float(value[:-1]) if kind == "pct" else value,
                    kind,
                )
            )
    entries.sort()
    layers: list[StatLayer] = []
    for _source_kind, rule_id, amount, kind in entries:
        try:
            label = display_for(rule_id).label
        except ValueError as error:
            # MissingDisplayMetadataError is a ValueError subclass; an
            # unresolvable label makes the row not accounting-complete.
            raise StatusQueryError(
                f"combat modifier rule {rule_id!r} has no display label"
            ) from error
        layers.append(StatLayer("condition", label, kind, amount))
    return layers


def _worn_gear(assembly: _Assembly) -> list[tuple[int, str, Any, Any]]:
    """Resolved ``(slot-order index, item_key, definition, layers)`` for worn gear.

    Mirrors the shipped fold's source exactly (``_worn_rules``): the pure
    ``normalized_equipment`` read, whose malformed-storage branch reads as
    "nothing worn" — the same zero contribution the combat bundle takes, so
    layers and effective can never disagree. Normalization also guarantees
    registry membership and slot fit; a missing definition or effect rule
    past that guard is an invariant break and fails closed. Per-item effect
    data comes exclusively through the capability's
    ``equipment_modifier_layers`` accessor (single-source guard). Rows sort
    by ``(slot order, item key)`` for display.
    """
    from world.rules.equipment import normalized_equipment

    equipment = normalized_equipment(assembly.entity)
    if equipment is None:
        return []
    worn: list[tuple[str, str]] = [
        (slot, equipment[slot])
        for slot in _EQUIPMENT_SLOTS
        if equipment[slot] is not None
    ]
    worn.extend(("accessory", key) for key in equipment["accessories"])
    resolved: list[tuple[int, str, Any, Mapping[str, tuple[str, int]]]] = []
    slot_index = {slot: index for index, slot in enumerate((*_EQUIPMENT_SLOTS, "accessory"))}
    for slot, item_key in worn:
        definition = ITEM_REGISTRY.get(item_key)
        if definition is None:
            raise StatusQueryError(f"worn equipment {item_key!r} is not registry-declared")
        if not definition.display_name_zh:
            raise StatusQueryError(f"equipment {item_key!r} has no display name")
        modifier_key = definition.modifier_key
        if modifier_key is None:
            continue
        layers = equipment_modifier_layers(modifier_key)
        if layers is None:  # pragma: no cover - loader/registry cross invariant
            raise StatusQueryError(
                f"equipment {item_key!r} effect rule {modifier_key!r} is missing"
            )
        resolved.append((slot_index[slot], item_key, definition, layers))
    resolved.sort(key=lambda entry: (entry[0], entry[1]))
    return resolved


def _equipment_layers(assembly: _Assembly, stat_key: str) -> list[StatLayer]:
    """Named layers for one stat's worn-equipment contributions (slot order)."""
    layers: list[StatLayer] = []
    for _index, _item_key, definition, item_layers in _worn_gear(assembly):
        contribution = item_layers.get(stat_key)
        if contribution is not None:
            kind, amount = contribution
            layers.append(StatLayer("equipment", definition.display_name_zh, kind, amount))
    return layers


def _require_number(value: Any, label: str) -> None:
    """Fail closed on a non-finite or zero numeric layer amount."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise StatusQueryError(f"{label} amount is not numeric")
    if isinstance(value, float) and not math.isfinite(value):
        raise StatusQueryError(f"{label} amount is not finite")
    if value == 0:
        raise StatusQueryError(f"{label} amount must be non-zero")


def _validated_row(row: StatBreakdownRow) -> StatBreakdownRow:
    """Enforce the closed alphabets and per-stat bound, fail-closed."""
    for layer in row.layers:
        if layer.source not in _LAYER_SOURCES:  # pragma: no cover - builder invariant
            raise StatusQueryError(f"breakdown layer source {layer.source!r} is invalid")
        if layer.kind not in _LAYER_KINDS:  # pragma: no cover - builder invariant
            raise StatusQueryError(f"breakdown layer kind {layer.kind!r} is invalid")
        if not isinstance(layer.name, str) or not layer.name:
            raise StatusQueryError("breakdown layer name is missing")
        _require_number(layer.amount, f"breakdown layer {layer.name!r}")
    if len(row.layers) > MAX_LAYERS_PER_STAT:
        raise StatusQueryError(
            f"stat {row.key!r} exceeds the {MAX_LAYERS_PER_STAT}-layer bound"
        )
    return row


def _stored_literal(traits_data: dict[str, Any], key: str, fallback: int) -> int:
    """The literal stored ``base`` when valid, else the reader's value.

    The breakdown ``base`` is the never-skill-baked import value; every
    shipped writer leaves the static/counter ``base`` key intact, so the
    fallback only matters for hand-forced fixtures.
    """
    raw = traits_data.get(key)
    if isinstance(raw, Mapping):
        base = raw.get("base")
        if not isinstance(base, bool) and isinstance(base, int):
            return base
    return fallback


def _require_untouched_modifiers(traits_data: dict[str, Any], key: str) -> None:
    """Fail closed when a static/counter carries unattributable modifiers.

    No shipped writer sets ``mod``/``mult`` on a static or counter trait
    (the gauge sync owns gauge ``mod`` alone), and no consumer of these two
    read models folds them in — so a nonzero value is storage drift the panel
    must not silently display as if it were the effective value.
    """
    raw = traits_data[key]
    if raw.get("mod", 0) != 0 or raw.get("mult", 1) != 1:
        raise StatusQueryError(f"trait {key!r} carries unattributable storage modifiers")


def _gauge_breakdown(assembly: _Assembly, key: str) -> StatBreakdownRow:
    """Decompose one gauge maximum; the ceiling reader stays authoritative.

    Skill layers are structurally impossible for gauges (stat multipliers
    exist only on body traits — ``world/skills/registry._BODY_TRAITS``), and
    ``sync_equipment_gauge_limits`` is the sole writer of gauge ``mod``, so
    the equipment flats must explain it exactly. Anything else is unexplained
    storage and fails closed, keeping the panel maximum identical to the
    heal-clamp ceiling the shipped reader computes.
    """
    gauge = assembly.gauges[key]
    mod, mult = assembly.gauge_records[key]
    base = _stored_literal(assembly.traits_data, key, gauge.maximum)
    if mult != 1:
        raise StatusQueryError(
            f"gauge {key!r} multiplier is not attributable to any named layer"
        )
    layers = _equipment_layers(assembly, key)
    equipment_total = sum(layer.amount for layer in layers)
    if equipment_total != mod:
        raise StatusQueryError(
            f"gauge {key!r} stored modifier is not explained by worn equipment caps"
        )
    if round(base + equipment_total) != gauge.maximum:
        raise StatusQueryError(
            f"gauge {key!r} maximum decomposition disagrees with the ceiling reader"
        )
    return StatBreakdownRow(
        key=key,
        base=base,
        current=gauge.current,
        effective=gauge.maximum,
        layers=tuple(layers),
    )


def _flat_stat_breakdown(assembly: _Assembly, stat_key: str) -> StatBreakdownRow:
    """attack/defense/magic_power: shipped skill fold, then merged flats.

    Parity anchor ``combat._adjusted_attack``/``_adjusted_defense``:
    ``float(effective_value(key)) + merged flat``, where the merged flat is
    the shipped merge of matched rule-table amounts and the equipment bucket
    — the exact merged-bundle read, so associativity cannot drift either. A
    percentage-shaped bundle for these stats has no shipped consumer and
    fails closed.
    """
    base = assembly.trait_values[stat_key]
    _require_untouched_modifiers(assembly.traits_data, stat_key)
    base_literal = _stored_literal(assembly.traits_data, stat_key, base)
    skill_layers, product = _skill_layers(assembly.entity, stat_key)
    after_skill = round(base * product)
    condition_layers = _condition_layers(assembly, stat_key)
    equipment_layers = _equipment_layers(assembly, stat_key)
    merged_flat = _merged_bundle(assembly).get(stat_key, 0)
    if isinstance(merged_flat, str):
        raise StatusQueryError(
            f"bundle percentage for {stat_key!r} has no shipped consumer"
        )
    if merged_flat != sum(layer.amount for layer in condition_layers) + sum(
        layer.amount for layer in equipment_layers
    ):  # pragma: no cover - per-source layering is exhaustive by construction
        raise StatusQueryError(
            f"stat {stat_key!r} flat amounts are not accounting-complete"
        )
    effective = float(after_skill) + merged_flat
    return StatBreakdownRow(
        key=stat_key,
        base=base_literal,
        current=effective,
        effective=effective,
        layers=(*skill_layers, *condition_layers, *equipment_layers),
    )


def _agility_breakdown(assembly: _Assembly) -> StatBreakdownRow:
    """Agility replays the shipped pipeline exactly, floor at zero included.

    ``combat_modifiers.adjusted_agility`` shape: percent first (the merged
    ``+g`` percent string — rule-table matches merged in ``_RULES`` order,
    then the gear bucket's ``:+d%`` rendering, all through the shipped
    ``_merge_adjustments``), then the flat addend, then ``max(0.0, …)``.

    The static row's total-display ``current`` equals ``effective`` even when
    a percent scale leaves it fractional — the shipped ``adjusted_agility``
    returns a float, and the v5 wire rejects any static row where the two
    diverge.
    """
    base = assembly.trait_values["agility"]
    _require_untouched_modifiers(assembly.traits_data, "agility")
    base_literal = _stored_literal(assembly.traits_data, "agility", base)
    skill_layers, product = _skill_layers(assembly.entity, "agility")
    after_skill = round(base * product)
    bundle = _merged_bundle(assembly)
    agility = float(after_skill)
    percent = bundle.get("agility")
    if percent is not None:
        if not isinstance(percent, str) or _PERCENT_RE.fullmatch(percent) is None:
            raise StatusQueryError(f"invalid agility percentage {percent!r}")
        agility *= 1 + float(percent[:-1]) / 100
    agility += float(bundle.get("agility_flat", 0))
    effective = max(0.0, agility)
    condition_layers = _condition_layers(assembly, "agility")
    equipment_layers = _equipment_layers(assembly, "agility")
    return StatBreakdownRow(
        key="agility",
        base=base_literal,
        current=effective,
        effective=effective,
        layers=(*skill_layers, *condition_layers, *equipment_layers),
    )


def _merit_breakdown(assembly: _Assembly) -> StatBreakdownRow:
    """guild_merit: an integer counter with no shipped modifier source at all."""
    merit = _read_guild_merit(assembly.traits_data)
    _require_untouched_modifiers(assembly.traits_data, "guild_merit")
    return StatBreakdownRow(
        key="guild_merit",
        base=_stored_literal(assembly.traits_data, "guild_merit", merit),
        current=merit,
        effective=merit,
        layers=(),
    )


def build_stat_breakdown(
    entity: Any, assembly: _Assembly | None = None
) -> tuple[StatBreakdownRow, ...]:
    """Return the eight breakdown rows composed from named sources (tasks 1.1–1.4).

    Composition replays the shipped operations exactly (design D1): gauges
    decompose the ceiling reader's ``(base + mod) × mult`` form; skill stats
    fold ``round(base × Π mults)`` in shipped order; attack/defense and
    magic_power add merged rule-table flats after the skill fold; agility
    replays the percent-then-flat pipeline floored at zero. Every accounting
    amount that cannot be attributed to a named, registry-labelled layer
    fails the whole read closed.
    """
    if assembly is None:
        from .assembly import _assemble

        assembly = _assemble(entity)
    rows: list[StatBreakdownRow] = []
    for key in _BREAKDOWN_ROW_ORDER:
        if key in _GAUGE_KEYS:
            rows.append(_gauge_breakdown(assembly, key))
        elif key == "agility":
            rows.append(_agility_breakdown(assembly))
        elif key in ("atk_phys", "defense", "magic_power"):
            rows.append(_flat_stat_breakdown(assembly, key))
        else:
            rows.append(_merit_breakdown(assembly))
    if len(rows) > MAX_BREAKDOWN_ROWS:  # pragma: no cover - closed 8-key vocabulary
        raise StatusQueryError("breakdown exceeds the row bound")
    return tuple(_validated_row(row) for row in rows)
