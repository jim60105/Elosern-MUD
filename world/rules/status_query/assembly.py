"""One read's shared, fully validated inputs (design D3: assembled once)."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from world.rules.buffs import BUFF_DEFINITIONS
from world.rules.combat_modifiers import combat_modifier_predicates, matched_combat_modifiers
from world.rules.equipment import normalized_equipment
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
    combat: tuple[str, int] | None


def _assemble(entity: Any) -> _Assembly:
    """Parse every read-model input once, fail-closed, with no handler mounted."""
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
    raw_equipment = entity.db.equipment
    captured = SimpleNamespace(db=SimpleNamespace(equipment=raw_equipment))
    equipment = normalized_equipment(captured)
    dual_wielding = dual_wielding_from_storage(captured)
    if equipment is None:
        equipment = {"weapon_main": None, "weapon_off": None, "armor": None, "accessories": []}
    labels, biases = condition_equipment_inputs(equipment)
    buffs = buff_provenances(buff_entries, equipment, labels)
    # The positional subject must be the facade too: ``matched_combat_modifiers``
    # reads ``entity.skills.owned_keys()`` directly for the ``skill_owned``
    # grant fallback, in addition to ``context["entity"]``.
    context, comparison = _sexual_condition_context(entity, buff_entries, equipment, biases, dual_wielding)
    comparison["active_buffs"] = {
        cache["definition_key"] for instance, cache in buff_entries
        if buffs[instance].kind != "equipment"
    }
    matches = matched_combat_modifiers(context["entity"], context=context)
    independent = matched_combat_modifiers(comparison["entity"], context=comparison)
    rules = rule_provenances(
        matches, {rule_id for rule_id, _ in independent}, combat_modifier_predicates(),
        context, comparison, buff_entries, buffs, equipment, labels, biases,
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
        combat=_read_combat(entity),
    )
