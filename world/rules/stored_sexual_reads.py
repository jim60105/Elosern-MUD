"""Neutral stored sexual-level reader (add-equipment-sexual-effects D1).

One handler-free, write-free reader for the persisted ordered-level sexual
fields (``exposure``, ``climax_phase``, ``wetness``, ``shame``) plus the
immutable ordinal comparison view they resolve into. The module imports
nothing from the project: it reads only Evennia attribute storage and the
levels tuple carried inside the stored record itself, which keeps the module
graph acyclic for both of its consumers — ``world.rules.combat_modifiers``
(condition contexts) and ``world.rules.equipment_effects`` (the effective-
exposure overlay).

Arousal is deliberately NOT served here: it is derived from the stored
pleasure counter through ``PLEASURE_CONFIG``, and that conversion belongs to
the rules layer (``combat_modifiers`` keeps the arousal branch of its
wrapper). Only genuinely stored ordered levels cross this boundary.
"""

from collections.abc import Mapping
from typing import Any

_SEXUAL_TRAITS_KEY = "sexual_traits"
_SEXUAL_TRAITS_CATEGORY = "traits"
_SEXUAL_BASELINE_KEY = "sexual"


class StoredLevel:
    """Read-only ordinal mirror for stored sexual-level comparisons.

    Carries the resolved ``value`` ordinal and the fixed ``levels``
    vocabulary, and implements ``gte``/``lte``/equality comparison parity
    against another ``StoredLevel``, a vocabulary label, or a raw ordinal —
    the same comparison contract the materialized ``OrderedLevelTrait``
    offers, so rule matching cannot tell the two views apart.
    """

    def __init__(self, value: int, levels: tuple[str, ...]):
        self.value = value
        self.levels = tuple(levels)

    def _ordinal_of(self, other: Any) -> int:
        if isinstance(other, StoredLevel):
            return other.value
        if isinstance(other, str):
            return self.levels.index(other)
        return int(other)

    def __eq__(self, other: object) -> bool:
        return self.value == self._ordinal_of(other)

    def __ge__(self, other: object) -> bool:
        return self.value >= self._ordinal_of(other)

    def __gt__(self, other: object) -> bool:
        return self.value > self._ordinal_of(other)

    def __le__(self, other: object) -> bool:
        return self.value <= self._ordinal_of(other)

    def __lt__(self, other: object) -> bool:
        return self.value < self._ordinal_of(other)

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        levels = ",".join(self.levels)
        return f"StoredLevel({self.levels[self.value]} [{self.value}] of {levels})"


def stored_sexual_level(entity: Any, field: str) -> Any:
    """Read one stored ordered sexual level without materializing the handler.

    Resolves a materialized ``sexual_traits`` entry to a :class:`StoredLevel`
    when its record carries a usable ordinal (or a label the record's own
    vocabulary resolves), falls back to the import-time ``sexual`` baseline
    string, and returns ``None`` when neither exists. Never creates
    ``entity.sexual`` and never writes.
    """
    # Fail closed for entities without attribute storage (pure in-memory
    # combat fakes): no storage means no stored level, never a crash.
    attributes = getattr(entity, "attributes", None)
    if attributes is None:
        return None
    traits = attributes.get(
        _SEXUAL_TRAITS_KEY, default=None, category=_SEXUAL_TRAITS_CATEGORY
    )
    if isinstance(traits, Mapping) and field in traits:
        raw = traits[field]
        if isinstance(raw, Mapping):
            value = raw.get("value")
            levels = raw.get("levels") or ()
            if isinstance(value, str):
                if levels:
                    try:
                        return StoredLevel(levels.index(value), tuple(levels))
                    except ValueError:
                        return value
                return value
            if (
                isinstance(value, int)
                and isinstance(levels, (list, tuple))
                and 0 <= value < len(levels)
            ):
                return StoredLevel(value, tuple(levels))
            return value

    baseline = attributes.get(_SEXUAL_BASELINE_KEY, default=None)
    if isinstance(baseline, Mapping) and isinstance(baseline.get(field), str):
        return baseline[field]
    return None
