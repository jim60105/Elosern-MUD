"""One read's shared, fully validated inputs (design D3: assembled once)."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from world.rules.combat_modifiers import matched_combat_modifiers

from .context import _sexual_condition_context
from .models import (
    _COUNTER_KEYS,
    _GAUGE_KEYS,
    _STATIC_KEYS,
    CharacterEquipmentView,
    GaugeValue,
    StatusQueryError,
)
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
    # The positional subject must be the facade too: ``matched_combat_modifiers``
    # reads ``entity.skills.owned_keys()`` directly for the ``skill_owned``
    # grant fallback, in addition to ``context["entity"]``.
    context = _sexual_condition_context(entity)
    matches = matched_combat_modifiers(context["entity"], context=context)
    return _Assembly(
        entity=entity,
        traits_data=traits_data,
        gauges=gauges,
        gauge_records=gauge_records,
        trait_values=trait_values,
        buff_entries=buff_entries,
        matches=matches,
        equipment=_read_equipment(entity),
        combat=_read_combat(entity),
    )
