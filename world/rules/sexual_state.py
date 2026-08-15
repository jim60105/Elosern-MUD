"""Deterministic sexual state from design section 6.4 and change 7.

The event rules in ``rulebook/sexual.yaml``, ``apply_event()``, and their
per-rule tests belong to the follow-on ``sexual-transition-rules`` change.
"""

from collections.abc import ItemsView, Mapping
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any

import yaml

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
    "wetness": WETNESS_LEVELS,
    "shame": SHAME_LEVELS,
    "exposure": EXPOSURE_LEVELS,
    "climax_phase": CLIMAX_PHASE_LEVELS,
}
_LIFETIME_COUNTER_KEYS = (
    "masturbation_count",
    "toy_use_count",
    "exposure_act_count",
    "watched_count",
    "duo_act_count",
    "group_act_count",
    "hostile_act_count",
    "restraint_count",
    "interspecies_act_count",
    "climax_count",
    "climax_extension_count",
)
_PLEASURE_RULEBOOK = Path(__file__).with_name("rulebook") / "sexual_pleasure.yaml"


class PleasureConfigError(ValueError):
    """The sexual_pleasure.yaml rulebook violates the canonical contract."""


@dataclass(frozen=True)
class PleasureBand:
    """One contiguous pleasure band mapping to one arousal level."""

    level: str
    floor: int
    ceiling: int


@dataclass(frozen=True)
class PleasureConfig:
    """The validated pleasure-to-arousal band table and gain multipliers.

    ``pleasure_bands`` covers ``0..100`` exactly with five contiguous,
    ascending bands, one per ``AROUSAL_LEVELS`` member in order.
    ``sensitivity_multipliers`` and ``shame_multipliers`` are keyed by the
    canonical vocabulary levels and consumed by the later act-effects
    proposal; they are validated here so malformed balance data fails closed
    at load.
    """

    bands: tuple[PleasureBand, ...]
    sensitivity_multipliers: Mapping[str, float]
    shame_multipliers: Mapping[str, float]

    def ordinal_for(self, pleasure_value: int) -> int:
        """Resolve one pleasure value to its arousal level ordinal."""
        for ordinal, band in enumerate(self.bands):
            if band.floor <= pleasure_value <= band.ceiling:
                return ordinal
        raise PleasureConfigError(
            f"pleasure value {pleasure_value} is outside the configured bands"
        )

    def floor_for_level(self, level: str) -> int:
        """Return the band floor for one arousal level name."""
        for band in self.bands:
            if band.level == level:
                return band.floor
        raise PleasureConfigError(f"no pleasure band declares level {level!r}")

    def floor_for(self, pleasure_value: int) -> int:
        """Return the floor of the band containing one pleasure value."""
        return self.bands[self.ordinal_for(pleasure_value)].floor


def _error(message: str) -> PleasureConfigError:
    return PleasureConfigError(f"sexual_pleasure.yaml: {message}")


def _require_positive_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _error(f"{field} must be a positive number")
    if not isfinite(value) or value <= 0:
        raise _error(f"{field} must be a finite positive number")
    return float(value)


def _load_multiplier_table(
    raw: Any,
    levels: tuple[str, ...],
    name: str,
) -> dict[str, float]:
    if not isinstance(raw, Mapping):
        raise _error(f"{name} must be a mapping")
    raw = dict(raw)
    if set(raw) != set(levels):
        raise _error(
            f"{name} must carry exactly the levels {list(levels)}, "
            f"got {sorted(raw)}"
        )
    return {
        level: _require_positive_number(raw[level], f"{name}.{level}")
        for level in levels
    }


def load_pleasure_config(path: Path | None = None) -> PleasureConfig:
    """Load and validate the pleasure rulebook, failing closed on deviation.

    ``path`` overrides the canonical rulebook location so tests can exercise
    deviant tables through a temporary copy, keeping the shared source file
    untouched.
    """
    rulebook = _PLEASURE_RULEBOOK if path is None else path
    raw = yaml.safe_load(rulebook.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise _error("rulebook must be a mapping")
    raw = dict(raw)
    unknown = set(raw) - {"pleasure_bands", "sensitivity_multipliers", "shame_multipliers"}
    if unknown:
        raise _error(f"unknown top-level fields {sorted(unknown)}")
    missing = {"pleasure_bands", "sensitivity_multipliers", "shame_multipliers"} - set(raw)
    if missing:
        raise _error(f"missing top-level fields {sorted(missing)}")

    bands_raw = raw["pleasure_bands"]
    if not isinstance(bands_raw, list):
        raise _error("pleasure_bands must be a list")
    if len(bands_raw) != len(AROUSAL_LEVELS):
        raise _error(
            f"exactly {len(AROUSAL_LEVELS)} pleasure bands are required, "
            f"got {len(bands_raw)}"
        )
    bands: list[PleasureBand] = []
    for position, entry in enumerate(bands_raw, start=1):
        if not isinstance(entry, Mapping):
            raise _error(f"pleasure_bands[{position}] must be a mapping")
        entry = dict(entry)
        if set(entry) != {"level", "floor", "ceiling"}:
            raise _error(
                f"pleasure_bands[{position}] must carry exactly "
                "level/floor/ceiling"
            )
        level = entry["level"]
        floor = entry["floor"]
        ceiling = entry["ceiling"]
        if isinstance(floor, bool) or not isinstance(floor, int):
            raise _error(f"pleasure_bands[{position}].floor must be an integer")
        if isinstance(ceiling, bool) or not isinstance(ceiling, int):
            raise _error(f"pleasure_bands[{position}].ceiling must be an integer")
        if floor > ceiling:
            raise _error(
                f"pleasure_bands[{position}] floor must not exceed ceiling"
            )
        bands.append(PleasureBand(level=level, floor=floor, ceiling=ceiling))

    levels = [band.level for band in bands]
    if levels != list(AROUSAL_LEVELS):
        raise _error(
            f"pleasure_bands must list exactly {list(AROUSAL_LEVELS)} in order, "
            f"got {levels}"
        )
    if bands[0].floor != 0:
        raise _error("pleasure_bands must start at floor 0")
    if bands[-1].ceiling != 100:
        raise _error("pleasure_bands must end at ceiling 100")
    for lower, upper in zip(bands, bands[1:]):
        if lower.ceiling + 1 != upper.floor:
            raise _error(
                "pleasure_bands must be contiguous with no gap and no overlap: "
                f"{lower.level} ends at {lower.ceiling} but {upper.level} "
                f"starts at {upper.floor}"
            )

    return PleasureConfig(
        bands=tuple(bands),
        sensitivity_multipliers=_load_multiplier_table(
            raw["sensitivity_multipliers"], SENSITIVITY_LEVELS, "sensitivity_multipliers"
        ),
        shame_multipliers=_load_multiplier_table(
            raw["shame_multipliers"], SHAME_LEVELS, "shame_multipliers"
        ),
    )


PLEASURE_CONFIG = load_pleasure_config()


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
        baseline_level = baseline.get("arousal", AROUSAL_LEVELS[0])
        pleasure_floor = PLEASURE_CONFIG.floor_for_level(baseline_level)
        self._traits.add(
            "pleasure",
            trait_type="counter",
            base=pleasure_floor,
            min=0,
            max=100,
        )
        self._traits.add(
            "climax_today",
            trait_type="counter",
            base=int(baseline.get("climax_today", 0)),
            min=0,
        )
        for key in _LIFETIME_COUNTER_KEYS:
            self._traits.add(
                key,
                trait_type="counter",
                base=0,
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
    def arousal(self) -> _DerivedArousal:
        ordinal = PLEASURE_CONFIG.ordinal_for(self.pleasure.value)
        return _DerivedArousal(ordinal, AROUSAL_LEVELS)

    @property
    def pleasure(self):
        """Return the bounded pleasure gauge counter trait (0..100)."""
        return self._traits.pleasure

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
    def climax_turns(self) -> int:
        """Return the consecutive settlement points spent in 進行中."""
        return int(
            self._entity.attributes.get(
                "climax_turns",
                default=0,
                category=_STATE_CATEGORY,
            )
        )

    @property
    def pending_climax_extension(self) -> int:
        """Return the staged-but-unconsumed climax-extension count."""
        return int(
            self._entity.attributes.get(
                "pending_climax_extension",
                default=0,
                category=_STATE_CATEGORY,
            )
        )

    def stage_climax_extension(self, count: int = 1) -> None:
        """Add ``count`` to the pending extension stage. The sole write path.

        ``count`` must be a positive integer; any other value raises
        ``ValueError`` without changing the counter, so a future act-effect
        caller cannot stage a value the settlement decision would silently
        treat as "no extension staged".
        """
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise ValueError("count must be a positive integer")
        self._entity.attributes.add(
            "pending_climax_extension",
            self.pending_climax_extension + count,
            category=_STATE_CATEGORY,
        )

    @property
    def masturbation_count(self) -> int:
        """Return the lifetime masturbation occurrence counter."""
        return int(self._traits.masturbation_count.value)

    @property
    def toy_use_count(self) -> int:
        """Return the lifetime toy-use occurrence counter."""
        return int(self._traits.toy_use_count.value)

    @property
    def exposure_act_count(self) -> int:
        """Return the lifetime exposure-act occurrence counter."""
        return int(self._traits.exposure_act_count.value)

    @property
    def watched_count(self) -> int:
        """Return the lifetime watched-while-active occurrence counter."""
        return int(self._traits.watched_count.value)

    @property
    def duo_act_count(self) -> int:
        """Return the lifetime two-person act occurrence counter."""
        return int(self._traits.duo_act_count.value)

    @property
    def group_act_count(self) -> int:
        """Return the lifetime group act occurrence counter."""
        return int(self._traits.group_act_count.value)

    @property
    def hostile_act_count(self) -> int:
        """Return the lifetime act-against-opponent occurrence counter."""
        return int(self._traits.hostile_act_count.value)

    @property
    def restraint_count(self) -> int:
        """Return the lifetime restraint-endurance occurrence counter."""
        return int(self._traits.restraint_count.value)

    @property
    def interspecies_act_count(self) -> int:
        """Return the lifetime interspecies act occurrence counter."""
        return int(self._traits.interspecies_act_count.value)

    @property
    def climax_count(self) -> int:
        """Return the lifetime climax occurrence counter."""
        return int(self._traits.climax_count.value)

    @property
    def climax_extension_count(self) -> int:
        """Return the lifetime climax-extension occurrence counter."""
        return int(self._traits.climax_extension_count.value)

    def record_masturbation(self) -> None:
        """Increment the lifetime masturbation counter by exactly one."""
        self._traits.masturbation_count.base += 1

    def record_toy_use(self) -> None:
        """Increment the lifetime toy-use counter by exactly one."""
        self._traits.toy_use_count.base += 1

    def record_exposure_act(self) -> None:
        """Increment the lifetime exposure-act counter by exactly one."""
        self._traits.exposure_act_count.base += 1

    def record_watched(self) -> None:
        """Increment the lifetime watched-while-active counter by exactly one."""
        self._traits.watched_count.base += 1

    def record_duo_act(self) -> None:
        """Increment the lifetime two-person act counter by exactly one."""
        self._traits.duo_act_count.base += 1

    def record_group_act(self) -> None:
        """Increment the lifetime group act counter by exactly one."""
        self._traits.group_act_count.base += 1

    def record_hostile_act(self) -> None:
        """Increment the lifetime act-against-opponent counter by exactly one."""
        self._traits.hostile_act_count.base += 1

    def record_restraint(self) -> None:
        """Increment the lifetime restraint-endurance counter by exactly one."""
        self._traits.restraint_count.base += 1

    def record_interspecies_act(self) -> None:
        """Increment the lifetime interspecies act counter by exactly one."""
        self._traits.interspecies_act_count.base += 1

    def record_climax_count(self) -> None:
        """Increment the lifetime climax counter by exactly one."""
        self._traits.climax_count.base += 1

    def record_climax_extension(self) -> None:
        """Increment the lifetime climax-extension counter by exactly one."""
        self._traits.climax_extension_count.base += 1

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

    def unlocked_act_keys(self) -> frozenset[str]:
        """Return every act whose counter thresholds this entity has met.

        Direct ownership of any skill carrying ``SexualMasteryEffect``
        instead returns the entire catalogue. Ownership is read through
        ``base_owned_keys()``, never through ``owned_keys()`` — which would
        recurse — and never through ``conferred_grants()``, matching
        ``can_cast_spell_tier``'s mastery-override discipline. The rule
        implementation lives in the catalogue package so the no-create
        ``owned_keys()`` read shares it exactly.
        """
        from world.skills.sexual_acts import unlocked_act_keys_for

        return unlocked_act_keys_for(
            self._entity.skills.base_owned_keys(),
            {name: getattr(self, name) for name in _LIFETIME_COUNTER_KEYS},
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
    "pleasure": {"interval_seconds": 1800, "floor": "平靜"},
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
        elif field == "pleasure":
            current_band_floor = PLEASURE_CONFIG.floor_for(trait.value)
            trait.base = max(0, current_band_floor - 1)
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


def climax_settlement_action(entity) -> str | None:
    """Advance climax-turn bookkeeping and report which settlement action to take.

    Returns ``"extend"`` when a staged extension is consumed, ``"end"`` when
    the entity must resolve its climax normally, or ``None`` when
    ``climax_phase`` is not 進行中 (``climax_turns`` is reset to ``0`` in this
    case, if it was nonzero).

    This performs every mutation that does not require the ``sexual.yaml``
    rule cascade: ``climax_turns`` and ``pending_climax_extension``
    bookkeeping, and the two lifetime counter increments. It does NOT call
    ``apply_event()`` — the caller (``combat.py`` or ``clock.py``) does that,
    using the returned action to choose between ``"climax_extended"`` and
    ``"climax_ends"``.
    """
    sexual = getattr(entity, "sexual", None)
    if sexual is None:
        return None
    if sexual.climax_phase.level != "進行中":
        if sexual.climax_turns != 0:
            entity.attributes.add(
                "climax_turns",
                0,
                category=_STATE_CATEGORY,
            )
        if sexual.pending_climax_extension != 0:
            entity.attributes.add(
                "pending_climax_extension",
                0,
                category=_STATE_CATEGORY,
            )
        return None
    entity.attributes.add(
        "climax_turns",
        sexual.climax_turns + 1,
        category=_STATE_CATEGORY,
    )
    if sexual.pending_climax_extension > 0:
        entity.attributes.add(
            "pending_climax_extension",
            sexual.pending_climax_extension - 1,
            category=_STATE_CATEGORY,
        )
        sexual.record_climax_extension()
        return "extend"
    sexual.record_climax_count()
    return "end"


__all__ = [
    "DECAY_CONFIG",
    "PLEASURE_CONFIG",
    "OrderedLevelTrait",
    "PleasureBand",
    "PleasureConfig",
    "PleasureConfigError",
    "SexualState",
    "_VALID_CLIMAX_TRANSITIONS",
    "_apply_climax_phase_set",
    "build_monster_sexual_baseline",
    "climax_settlement_action",
    "decay_tick",
    "load_pleasure_config",
    "reset_daily_counters",
]
