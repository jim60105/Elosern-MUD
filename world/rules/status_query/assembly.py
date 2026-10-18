"""One read's shared, fully validated inputs (design D3: assembled once)."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from world.rules.buffs import BUFF_DEFINITIONS
from world.rules.combat_modifiers import combat_modifier_predicates, matched_combat_modifiers
from world.rules.equipment import normalize_equipment_mapping, normalized_equipment
from world.rules.equipment_effects import condition_equipment_inputs
from world.skills.equipment import dual_wielding_from_storage

from .context import _sexual_condition_context
from .models import (
    _COUNTER_KEYS,
    _GAUGE_KEYS,
    _STATIC_KEYS,
    CharacterEquipmentView,
    ConditionProvenance,
    GaugeValue,
    StatusQueryError,
)
from .provenance import buff_provenances, rule_provenances
from .readers import (
    _active_buff_entries,
    _read_attribute,
    _read_combat,
    _read_equipment,
    _require_gauge_record,
    _require_static_trait,
)


@dataclass(frozen=True)
class _Assembly:
    """One read's shared, fully validated inputs (design D3: assembled once)."""

    entity: Any
    traits_data: dict[str, Any]
    gauges: dict[str, GaugeValue]
    gauge_records: dict[str, tuple[Any, Any]]
    trait_values: dict[str, int]
    buff_entries: tuple[tuple[str, dict[str, Any]], ...]
    matches: tuple[tuple[str, dict[str, Any]], ...]
    buff_provenance: dict[str, ConditionProvenance]
    rule_provenance: dict[str, ConditionProvenance]
    equipment: tuple[CharacterEquipmentView, ...]
    #: The normalized mapping every equipment-derived value in this read used.
    #: Canonical storage by default; the hypothetical after mapping for the
    #: item-holdings preview.
    equipment_mapping: dict[str, Any]
    combat: tuple[str, int] | None


def _hypothetical_gauges(
    entity: Any, traits_data: dict[str, Any], equipment_mapping: dict[str, Any]
) -> tuple[dict[str, GaugeValue], dict[str, tuple[Any, Any]]]:
    """Project the gauge ceilings a real toggle would sync for this mapping.

    ``sync_equipment_gauge_limits`` rewrites ``mod`` from the worn caps and
    clamps the current value to the new ceiling; the injected read must do the
    same in memory or the breakdown's fail-closed decomposition would compare
    hypothetical gear layers against canonical stored modifiers. A non-unit
    multiplier has no attributable layer and stays rejected here, exactly as
    the gauge breakdown rejects it.
    """
    from world.rules.equipment import normalized_equipment
    from world.rules.equipment_effects import equipment_gauge_caps_for
    from world.skills.restrictions import exam_restriction

    caps = equipment_gauge_caps_for(equipment_mapping)
    canonical_mapping = normalized_equipment(entity)
    if canonical_mapping is None:
        canonical_mapping = {
            "weapon_main": None,
            "weapon_off": None,
            "armor": None,
            "accessories": [],
        }
    canonical_caps = equipment_gauge_caps_for(canonical_mapping)
    record = exam_restriction(entity)
    gauges: dict[str, GaugeValue] = {}
    records: dict[str, tuple[Any, Any]] = {}
    for key in _GAUGE_KEYS:
        gauge, mod, mult = _require_gauge_record(traits_data, key)
        if mult != 1:
            raise StatusQueryError(
                f"gauge {key!r} multiplier is not attributable to any named layer"
            )
        base = traits_data[key]["base"]
        # The hypothetical read must not launder unexplained canonical
        # accounting: the stored modifier has to be attributable to canonical
        # equipment first, exactly as the canonical breakdown requires.
        canonical_total = int(canonical_caps.get(key, 0))
        if record is not None and key in record["ceilings"]:
            canonical_total = min(base + canonical_total, record["ceilings"][key]) - base
        if canonical_total != mod:
            raise StatusQueryError(
                f"gauge {key!r} stored modifier is not explained by worn equipment caps"
            )
        total = int(caps.get(key, 0))
        if record is not None and key in record["ceilings"]:
            total = min(base + total, record["ceilings"][key]) - base
        maximum = int(round((base + total) * mult))
        if traits_data[key].get("current") is None:
            # An unset current defaults to the NEW maximum after settlement,
            # not to the canonical maximum the reader substituted.
            current = maximum
        else:
            current = min(gauge.current, maximum)
        gauges[key] = GaugeValue(current=current, maximum=maximum)
        records[key] = (total, mult)
    return gauges, records


def _assemble(entity: Any, *, equipment: Any = None) -> _Assembly:
    """Parse every read-model input once, fail-closed, with no handler mounted.

    ``equipment`` is the item-holdings hypothetical seam: a normalized
    mapping replacing canonical storage for every equipment-derived input
    (condition context, worn gear, gear adjustments, gauge ceilings) while
    everything else is read from ``entity`` unchanged. ``None`` keeps the
    canonical path byte-identical.
    """
    traits_data = _read_attribute(entity, "traits", default=None, category="traits")
    if not isinstance(traits_data, Mapping):
        raise StatusQueryError("trait storage is unavailable")
    traits_data = dict(traits_data)
    gauges: dict[str, GaugeValue] = {}
    gauge_records: dict[str, tuple[Any, Any]] = {}
    for key in _GAUGE_KEYS:
        gauges[key], mod, mult = _require_gauge_record(traits_data, key)
        gauge_records[key] = (mod, mult)
    trait_values = {
        key: _require_static_trait(traits_data, key) for key in _STATIC_KEYS + _COUNTER_KEYS
    }
    buff_entries = tuple(_active_buff_entries(entity))
    for instance, cache in buff_entries:
        definition = cache.get("definition_key")
        if not isinstance(definition, str) or definition not in BUFF_DEFINITIONS:
            raise StatusQueryError(f"buff {instance!r} has an unknown definition")
    if equipment is None:
        captured = SimpleNamespace(db=SimpleNamespace(equipment=entity.db.equipment))
        equipment_mapping = normalized_equipment(captured)
        dual_wielding = dual_wielding_from_storage(captured)
    else:
        equipment_mapping = normalize_equipment_mapping(equipment)
        if equipment_mapping is None:
            raise StatusQueryError("injected equipment mapping is malformed")
        dual_wielding = (
            equipment_mapping["weapon_main"] is not None
            and equipment_mapping["weapon_off"] is not None
        )
    if equipment_mapping is None:
        equipment_mapping = {
            "weapon_main": None,
            "weapon_off": None,
            "armor": None,
            "accessories": [],
        }
    if equipment is not None:
        gauges, gauge_records = _hypothetical_gauges(
            entity, traits_data, equipment_mapping
        )
    labels, biases = condition_equipment_inputs(equipment_mapping)
    buffs = buff_provenances(buff_entries, equipment_mapping, labels)
    # The positional subject must be the facade too: ``matched_combat_modifiers``
    # reads ``entity.skills.owned_keys()`` directly for the ``skill_owned``
    # grant fallback, in addition to ``context["entity"]``.
    context, comparison = _sexual_condition_context(
        entity, buff_entries, equipment_mapping, biases, dual_wielding
    )
    comparison["active_buffs"] = {
        cache["definition_key"] for instance, cache in buff_entries
        if buffs[instance].kind != "equipment"
    }
    matches = matched_combat_modifiers(context["entity"], context=context)
    independent = matched_combat_modifiers(comparison["entity"], context=comparison)
    rules = rule_provenances(
        matches, {rule_id for rule_id, _ in independent}, combat_modifier_predicates(),
        context, comparison, buff_entries, buffs, equipment_mapping, labels, biases,
    )
    return _Assembly(
        entity=entity,
        traits_data=traits_data,
        gauges=gauges,
        gauge_records=gauge_records,
        trait_values=trait_values,
        buff_entries=buff_entries,
        matches=matches,
        buff_provenance=buffs,
        rule_provenance=rules,
        equipment=_read_equipment(entity),
        equipment_mapping=equipment_mapping,
        combat=_read_combat(entity),
    )
