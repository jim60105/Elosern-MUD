"""The pure condition-evaluation surface: stored-snapshot facade plus context.

Both read models evaluate combat conditions through these objects so the panel
can never disagree with combat resolution while never mounting any handler.
"""

from collections.abc import Mapping
from typing import Any

from world.lore.sexual_vocab import AROUSAL_LEVELS, CLIMAX_PHASE_LEVELS, EXPOSURE_LEVELS
from world.rules.equipment_effects import effective_exposure, worn_item_keys
from world.rules.sexual_state import _LIFETIME_COUNTER_KEYS
from world.rules.stored_sexual_reads import StoredLevel
from world.skills.equipment import dual_wielding_from_storage
from world.skills.handler import INNATE_SKILL_ORDER
from world.skills.sexual_acts import unlocked_act_keys_for

from .models import (
    _SEXUAL_TRAITS_CATEGORY,
    _SEXUAL_TRAITS_KEY,
    StatusQueryError,
    _LevelRef,
)
from .readers import _active_buff_entries, _is_list_like, _read_attribute
from .sexual import _ordinal_of, _sexual_level


class _StoredSkillsFacade:
    """Pure ``skills``-view facade over stored snapshots (design D4).

    Exposes exactly the ``owned_keys()``/``conferred_grants()`` surface
    ``matched_combat_modifiers``, ``_conferred_rule_scale`` and
    ``evaluate_condition`` consume, computed from ``entity.db`` and the
    registries with the same no-create discipline as
    ``_split_active_passive_keys``. ``db`` delegates to the real entity so the
    pure storage readers (``dual_wielding_from_storage``, ``worn_item_keys``)
    keep working on the facade. Never mounts ``entity.skills`` (or any other
    handler) and never writes.
    """

    __slots__ = ("entity",)

    def __init__(self, entity: Any):
        self.entity = entity

    @property
    def db(self) -> Any:
        return self.entity.db

    @property
    def skills(self) -> "_StoredSkillsFacade":
        return self

    def _stored_list(self, field: str) -> tuple[str, ...]:
        raw = self.entity.db.skills
        if not isinstance(raw, Mapping):
            return ()
        value = raw.get(field)
        if not _is_list_like(value):
            return ()
        return tuple(key for key in value if isinstance(key, str) and key)

    def base_owned_keys(self) -> list[str]:
        """Stored active+passive keys plus innate grants, in stored order."""
        return [*self._stored_list("active"), *self._stored_list("passive"), *INNATE_SKILL_ORDER]

    def _counter_values(self) -> dict[str, int]:
        """Lifetime counters from storage, or empty when unmaterialized.

        Mirrors ``_split_active_passive_keys`` exactly: a materialized
        ``sexual_traits`` record supplies ``climax_today`` and the lifetime
        counters (``current`` wins over ``base``); a present-but-malformed
        entry fails closed; no record means every counter is zero, which is
        what the shipped handler assumes for an unmaterialized state.
        """
        traits = _read_attribute(
            self.entity, _SEXUAL_TRAITS_KEY, default=None, category=_SEXUAL_TRAITS_CATEGORY
        )
        counters: dict[str, int] = {}
        if isinstance(traits, Mapping):
            for field in ("climax_today", *_LIFETIME_COUNTER_KEYS):
                entry = traits.get(field)
                if entry is None:
                    continue
                if not isinstance(entry, Mapping):
                    raise StatusQueryError(f"sexual counter {field!r} is malformed")
                value = entry.get("current", entry.get("base"))
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise StatusQueryError(f"sexual counter {field!r} is malformed")
                counters[field] = value
        return counters

    def owned_keys(self) -> list[str]:
        """Base keys plus unlocked acts — the materialization-aware handler rule.

        The shipped ``SkillHandler.owned_keys`` derives unlocked acts from a
        zero-counter baseline while ``sexual`` is unmaterialized and from the
        live handler afterwards; the live handler's counters are exactly the
        materialized record, so reading every counter from storage reproduces
        both branches without mounting one.
        """
        base = self.base_owned_keys()
        return [*base, *sorted(unlocked_act_keys_for(base, self._counter_values()))]

    def conferred_grants(self) -> list[Any]:
        """Stored grants verbatim (``list(entity.db.skill_grants or [])``)."""
        return list(self.entity.db.skill_grants or [])


def _sexual_condition_context(entity: Any) -> dict[str, Any]:
    """Build the combat-modifier condition context from read-only state.

    The exposure slot carries the EFFECTIVE level (stored plus worn equipment
    bias, clamped) as this module's own immutable ``_LevelRef`` view, so the
    panel's condition chips can never disagree with what combat resolution
    actually matches (add-equipment-sexual-effects D4).
    """
    context: dict[str, Any] = {"active_buffs": {key for key, _ in _active_buff_entries(entity)}}
    for field, levels in (
        ("arousal", AROUSAL_LEVELS),
        ("climax_phase", CLIMAX_PHASE_LEVELS),
    ):
        value = _sexual_level(entity, field)
        if isinstance(value, str) and value in levels:
            context[field] = _LevelRef(_ordinal_of(levels, value), levels)
        elif isinstance(value, _LevelRef):
            context[field] = value
    exposure = effective_exposure(entity)
    if isinstance(exposure, StoredLevel) and exposure.levels == EXPOSURE_LEVELS:
        context["exposure"] = _LevelRef(exposure.value, EXPOSURE_LEVELS)
    # Neither read model may materialize ``entity.skills``: every
    # condition-evaluation consumer reads skills through the positional
    # subject or ``context["entity"]``, and both are always the pure
    # stored-snapshot facade (expose-stat-breakdown-read-model D4). The two
    # pre-set equipment facts keep ``matched_combat_modifiers``' setdefaults
    # away from the real entity as well.
    facade = _StoredSkillsFacade(entity)
    context["entity"] = facade
    context["dual_wielding"] = dual_wielding_from_storage(facade)
    context["worn_item_keys"] = worn_item_keys(facade)
    return context
