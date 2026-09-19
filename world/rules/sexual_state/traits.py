"""Ordered-level trait primitives for the sexual-state subsystem.

Owns :class:`OrderedLevelTrait` (registered in
``settings.TRAIT_CLASS_PATHS``), the lazy ``sensitivity`` mapping proxy,
the generic/monster baselines, and the derived arousal view.
"""

from collections.abc import ItemsView
from typing import Any

from evennia.contrib.rpg.traits import Trait, TraitHandler

from world.lore.sexual_vocab import (
    AROUSAL_LEVELS,
    CLIMAX_PHASE_LEVELS,
    EXPOSURE_LEVELS,
    SHAME_LEVELS,
    SENSITIVITY_LEVELS,
    WETNESS_LEVELS,
)

_STATE_CATEGORY = "sexual_state"
_ORDERED_FIELDS = {
    "wetness": WETNESS_LEVELS,
    "shame": SHAME_LEVELS,
    "exposure": EXPOSURE_LEVELS,
    "climax_phase": CLIMAX_PHASE_LEVELS,
}


class OrderedLevelTrait(Trait):
    """A bounded ordinal into a fixed tuple of level names."""

    trait_type = "ordered_level"
    default_keys = {
        "value": 0,
        "levels": (),
        "min": 0,
        "max": None,
    }
    allow_extra_properties = False

    @staticmethod
    def validate_input(cls, trait_data):
        """Validate and normalize the fixed vocabulary and ordinal bounds."""
        trait_data = Trait.validate_input(cls, trait_data)
        levels = tuple(trait_data["levels"])
        if not levels or not all(isinstance(level, str) for level in levels):
            raise ValueError("levels must be a non-empty tuple of strings")
        trait_data["levels"] = levels
        lower = int(trait_data["min"])
        upper = (
            len(levels) - 1
            if trait_data["max"] is None
            else int(trait_data["max"])
        )
        if not 0 <= lower <= upper < len(levels):
            raise ValueError(
                f"ordered-level bounds must satisfy 0 <= min <= max < {len(levels)}"
            )
        trait_data["min"] = lower
        trait_data["max"] = upper
        value = trait_data["value"]
        if isinstance(value, str):
            try:
                value = levels.index(value)
            except ValueError as error:
                raise ValueError(f"invalid ordered level {value!r}") from error
        trait_data["value"] = max(0, min(int(value), len(levels) - 1))
        return trait_data

    @property
    def value(self) -> int:
        """Return the stored ordinal."""
        return self._data["value"]

    @value.setter
    def value(self, value: int | str) -> None:
        """Store an ordinal or vocabulary label, clamped to valid bounds."""
        ordinal = self._ordinal_of(value)
        self._data["value"] = max(self.min, min(ordinal, self.max))

    @property
    def min(self) -> int:
        """Return the inclusive lower ordinal bound."""
        return self._data["min"]

    @min.setter
    def min(self, value: int) -> None:
        value = int(value)
        if not 0 <= value <= self.max:
            raise ValueError(
                f"ordered-level min must be between 0 and current max {self.max}"
            )
        self._data["min"] = value
        self.value = self.value

    @property
    def max(self) -> int:
        """Return the inclusive upper ordinal bound."""
        return self._data["max"]

    @max.setter
    def max(self, value: int) -> None:
        value = int(value)
        vocabulary_max = len(self.levels) - 1
        if not self.min <= value <= vocabulary_max:
            raise ValueError(
                "ordered-level max must be between "
                f"current min {self.min} and vocabulary max {vocabulary_max}"
            )
        self._data["max"] = value
        self.value = self.value

    @property
    def level(self) -> str:
        """Return the current vocabulary label."""
        return self.levels[self.value]

    def _ordinal_of(self, other: Any) -> int:
        """Resolve a comparable trait, label, or integer to an ordinal."""
        if isinstance(other, OrderedLevelTrait):
            return other.value
        if isinstance(other, str):
            try:
                return self.levels.index(other)
            except ValueError as error:
                raise ValueError(f"invalid ordered level {other!r}") from error
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


class _SensitivityProxy:
    """Persistent mapping of body-part names to ordered sensitivity traits."""

    def __init__(self, traits: TraitHandler):
        self._traits = traits

    @staticmethod
    def _key(part: str) -> str:
        return f"sensitivity__{part}"

    def __getitem__(self, part: str) -> OrderedLevelTrait:
        key = self._key(part)
        if key not in self._traits.all():
            self._traits.add(
                key,
                trait_type="ordered_level",
                levels=SENSITIVITY_LEVELS,
            )
        return self._traits[key]

    def __setitem__(self, part: str, level: str | int) -> None:
        self[part].value = level

    def items(self) -> ItemsView[str, OrderedLevelTrait]:
        values = {
            key.removeprefix("sensitivity__"): self._traits[key]
            for key in self._traits.all()
            if key.startswith("sensitivity__")
        }
        return values.items()


def build_monster_sexual_baseline() -> dict[str, Any]:
    """Return the flat baseline used by monsters without imported state."""
    return _generic_default_baseline()


def _generic_default_baseline() -> dict[str, Any]:
    """Return floor levels for an entity without an imported baseline."""
    return {
        "arousal": AROUSAL_LEVELS[0],
        "wetness": WETNESS_LEVELS[0],
        "shame": SHAME_LEVELS[0],
        "exposure": EXPOSURE_LEVELS[0],
        "climax_phase": CLIMAX_PHASE_LEVELS[0],
        "sensitivity": {},
        "climax_today": 0,
        "virgin": True,
        "experience_types": frozenset(),
    }


class _DerivedArousal:
    """Read-only arousal view computed from the pleasure gauge.

    Exposes the comparison surface ``OrderedLevelTrait`` exposes (``.value``,
    ``.levels``, ``.level``, and the five comparison dunders) so existing
    readers keep working unchanged. All three attributes are read-only
    properties: direct assignment raises ``AttributeError`` rather than
    silently no-op'ing.
    """

    def __init__(self, value: int, levels: tuple[str, ...]):
        self._data = {"value": int(value), "levels": tuple(levels)}

    @property
    def value(self) -> int:
        """Return the derived arousal ordinal."""
        return self._data["value"]

    @property
    def levels(self) -> tuple[str, ...]:
        """Return the arousal vocabulary tuple."""
        return self._data["levels"]

    @property
    def level(self) -> str:
        """Return the current arousal level name."""
        return self.levels[self.value]

    def _ordinal_of(self, other: Any) -> int:
        """Resolve a comparable trait, label, or integer to an ordinal."""
        if isinstance(other, OrderedLevelTrait):
            return other.value
        if isinstance(other, _DerivedArousal):
            return other.value
        if isinstance(other, str):
            try:
                return self.levels.index(other)
            except ValueError as error:
                raise ValueError(f"invalid ordered level {other!r}") from error
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
