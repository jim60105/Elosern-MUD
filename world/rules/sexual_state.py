"""Deterministic sexual state from design section 6.4 and change 7.

The event rules in ``rulebook/sexual.yaml``, ``apply_event()``, and their
per-rule tests belong to the follow-on ``sexual-transition-rules`` change.
"""

from collections.abc import ItemsView
from typing import Any

from evennia.contrib.rpg.traits import Trait, TraitHandler

from world.lore.sexual_vocab import (
    AROUSAL_LEVELS,
    CLIMAX_PHASE_LEVELS,
    EXPOSURE_LEVELS,
    SENSITIVITY_LEVELS,
    SHAME_LEVELS,
    WETNESS_LEVELS,
)


_STATE_CATEGORY = "sexual_state"
_ORDERED_FIELDS = {
    "arousal": AROUSAL_LEVELS,
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


class SexualState:
    """Persistent live handler mounted separately from an entity's base traits."""

    def __init__(self, entity):
        self._entity = entity
        self._traits = TraitHandler(entity, db_attribute_key="sexual_traits")
        self._sensitivity = _SensitivityProxy(self._traits)
        required = {*_ORDERED_FIELDS, "climax_today"}
        if required.issubset(self._traits.all()):
            return

        baseline = entity.db.sexual
        if baseline is not None:
            self._build_from_baseline(baseline)
        else:
            from typeclasses.monsters import Monster

            if isinstance(entity, Monster):
                self._build_from_baseline(build_monster_sexual_baseline())
                self.shame.min = 0
                self.shame.max = 0
                self.shame.value = 0
            else:
                self._build_from_baseline(_generic_default_baseline())

    def _build_from_baseline(self, baseline: dict[str, Any]) -> None:
        for field, levels in _ORDERED_FIELDS.items():
            level = baseline.get(field, levels[0])
            self._traits.add(
                field,
                trait_type="ordered_level",
                levels=levels,
                value=level,
            )
        self._traits.add(
            "climax_today",
            trait_type="counter",
            base=int(baseline.get("climax_today", 0)),
            min=0,
        )
        for part, level in baseline.get("sensitivity", {}).items():
            self.sensitivity[part] = level
        self._entity.attributes.add(
            "virgin",
            bool(baseline.get("virgin", True)),
            category=_STATE_CATEGORY,
        )
        self._entity.attributes.add(
            "experience_types",
            frozenset(baseline.get("experience_types", ())),
            category=_STATE_CATEGORY,
        )

    @property
    def arousal(self) -> OrderedLevelTrait:
        return self._traits.arousal

    @property
    def wetness(self) -> OrderedLevelTrait:
        return self._traits.wetness

    @property
    def shame(self) -> OrderedLevelTrait:
        return self._traits.shame

    @property
    def exposure(self) -> OrderedLevelTrait:
        return self._traits.exposure

    @property
    def climax_phase(self) -> OrderedLevelTrait:
        return self._traits.climax_phase

    @property
    def climax_today(self) -> int:
        return int(self._traits.climax_today.value)

    def record_climax(self) -> None:
        """Increment the daily climax counter."""
        self._traits.climax_today.base += 1

    @property
    def sensitivity(self) -> _SensitivityProxy:
        return self._sensitivity

    @property
    def virgin(self) -> bool:
        return self._entity.attributes.get(
            "virgin",
            default=True,
            category=_STATE_CATEGORY,
        )

    @virgin.setter
    def virgin(self, value: bool) -> None:
        if not self.virgin:
            return
        self._entity.attributes.add(
            "virgin",
            bool(value),
            category=_STATE_CATEGORY,
        )

    @property
    def experience_types(self) -> frozenset[str]:
        return frozenset(
            self._entity.attributes.get(
                "experience_types",
                default=(),
                category=_STATE_CATEGORY,
            )
        )

    def add_experience_type(self, key: str) -> None:
        """Add one experience key without permitting replacement or removal."""
        self._entity.attributes.add(
            "experience_types",
            self.experience_types | {key},
            category=_STATE_CATEGORY,
        )


_VALID_CLIMAX_TRANSITIONS = {
    "未達": {"接近"},
    "接近": {"進行中", "未達"},
    "進行中": {"餘韻"},
    "餘韻": {"未達", "接近"},
}


def _apply_climax_phase_set(entity, target_level: str) -> str | None:
    """Apply a valid edge in the climax cycle, otherwise leave state unchanged."""
    current = entity.sexual.climax_phase.level
    if target_level not in _VALID_CLIMAX_TRANSITIONS.get(current, set()):
        return None
    entity.sexual.climax_phase.value = target_level
    return "cycle"


DECAY_CONFIG = {
    "arousal": {"interval_seconds": 1800, "floor": "平靜"},
    "wetness": {"interval_seconds": 900, "floor": "乾燥"},
    "shame": {"interval_seconds": 1800, "floor": "無"},
    "climax_phase": {
        "interval_seconds": 300,
        "floor": "未達",
        "only_from": "餘韻",
    },
}


def decay_tick(entity, elapsed_seconds: int) -> None:
    """Apply at most one decay step per configured field.

    Future buffs may address a field by its ``DECAY_CONFIG`` key, or a
    sensitivity entry as ``sensitivity__<part>``. Their rate, bounds, and
    decay levers are intentionally not implemented by this change.
    """
    if elapsed_seconds < 0:
        raise ValueError("elapsed_seconds must be non-negative")

    for field, config in DECAY_CONFIG.items():
        accumulator_key = f"decay_elapsed__{field}"
        trait = getattr(entity.sexual, field)
        only_from = config.get("only_from")
        if only_from is not None and trait.level != only_from:
            entity.attributes.add(
                accumulator_key,
                0,
                category=_STATE_CATEGORY,
            )
            continue
        accumulated = entity.attributes.get(
            accumulator_key,
            default=0,
            category=_STATE_CATEGORY,
        )
        accumulated += elapsed_seconds
        interval = config["interval_seconds"]
        if accumulated < interval:
            entity.attributes.add(
                accumulator_key,
                accumulated,
                category=_STATE_CATEGORY,
            )
            continue

        if field == "climax_phase":
            _apply_climax_phase_set(entity, config["floor"])
        else:
            floor = trait._ordinal_of(config["floor"])
            trait.value = max(floor, trait.value - 1)
        entity.attributes.add(
            accumulator_key,
            0,
            category=_STATE_CATEGORY,
        )


def reset_daily_counters(entity) -> None:
    """Reset the daily climax count without changing any other field."""
    entity.sexual._traits.climax_today.base = 0


__all__ = [
    "DECAY_CONFIG",
    "OrderedLevelTrait",
    "SexualState",
    "_VALID_CLIMAX_TRANSITIONS",
    "_apply_climax_phase_set",
    "build_monster_sexual_baseline",
    "decay_tick",
    "reset_daily_counters",
]
