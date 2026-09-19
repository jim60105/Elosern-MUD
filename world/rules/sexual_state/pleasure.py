"""Pleasure-gauge rulebook config for the sexual-state subsystem.

Owns ``sexual_pleasure.yaml`` validation: the band table, the gain
multiplier tables, and the process-wide ``PLEASURE_CONFIG`` singleton.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any

import yaml

from world.lore.sexual_vocab import AROUSAL_LEVELS, SENSITIVITY_LEVELS, SHAME_LEVELS

_PLEASURE_RULEBOOK = (
    Path(__file__).parent.parent / "rulebook" / "sexual_pleasure.yaml"
)


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
