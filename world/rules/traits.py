"""Deterministic entity-trait construction from design section 5.2."""

from typing import Any

from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.lore.races import (
    RACE_REGISTRY,
    STATIC_TIER_REGISTRY,
    SUBRACE_REGISTRY,
    RaceProfile,
)

GAUGE_REGEN_RATE_PCT = 0.01
GAUGE_KEYS = ("hp", "mp", "sp")
STATIC_KEYS = ("atk_phys", "agility", "defense")
COUNTER_KEYS = ("magic_level", "guild_merit")
TRAIT_KEYS = GAUGE_KEYS + STATIC_KEYS + COUNTER_KEYS


def race_floor(race: RaceProfile) -> dict[str, int]:
    """Read the documented floor of each race-owned axis."""
    return {
        "hp": race.vital_baseline.hp[0],
        "mp": race.vital_baseline.mp[0],
        "sp": race.vital_baseline.sp[0],
        "atk_phys": race.static_baseline.atk_phys[0],
        "agility": race.static_baseline.agility[0],
        "defense": race.static_baseline.defense[0],
        "magic_level": 0,
        "guild_merit": 0,
    }


def build_initial_traits(
    race_key: str,
    subrace_key: str | None = None,
    tier: str | None = None,
) -> dict[str, int]:
    """Build base values from race, optional static tier, then optional subrace."""
    race = RACE_REGISTRY[race_key]
    values = race_floor(race)

    if tier is not None:
        static_tier = STATIC_TIER_REGISTRY[tier]
        if static_tier.race_key != race_key:
            raise ValueError(
                f"tier {tier!r} belongs to race {static_tier.race_key!r}, "
                f"not {race_key!r}"
            )
        for axis in STATIC_KEYS:
            values[axis] = static_tier.band[0]

    if subrace_key is not None:
        subrace = SUBRACE_REGISTRY[subrace_key]
        if subrace.race_key != race_key:
            raise ValueError(
                f"subrace {subrace_key!r} belongs to race {subrace.race_key!r}, "
                f"not {race_key!r}"
            )
        for axis in STATIC_KEYS:
            delta = getattr(subrace.static_modifiers, axis)
            values[axis] = round(values[axis] * (1 + delta))
        if subrace.vital_overrides:
            for stat_key, band in subrace.vital_overrides.items():
                values[stat_key] = band[0]

    return values


def _trait_config(values: dict[str, int], magic_cap: int) -> dict[str, dict[str, Any]]:
    """Convert raw base values to Evennia 6.1 ``TraitHandler.add`` kwargs."""
    config: dict[str, dict[str, Any]] = {}
    for key in GAUGE_KEYS:
        maximum = values[key]
        config[key] = {
            "trait_type": "gauge",
            "base": maximum,
            "min": 0,
            "rate": maximum * GAUGE_REGEN_RATE_PCT,
        }
    for key in STATIC_KEYS:
        config[key] = {"trait_type": "static", "base": values[key], "mod": 0}
    config["magic_level"] = {
        "trait_type": "counter",
        "base": values["magic_level"],
        "min": 0,
        "max": magic_cap,
    }
    config["guild_merit"] = {
        "trait_type": "counter",
        "base": values["guild_merit"],
        "min": 0,
        "max": None,
    }
    return config


def initial_trait_config(
    race_key: str,
    subrace_key: str | None = None,
    tier: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Return race construction data ready for ``TraitHandler.add``."""
    values = build_initial_traits(race_key, subrace_key, tier)
    return _trait_config(values, RACE_REGISTRY[race_key].magic_cap)


def _resolve_band_position(
    band: tuple[int, int | None], position: str
) -> int:
    """Resolve one deterministic point inside a documented band."""
    floor, ceiling = band
    if position == "floor":
        return floor
    if position not in {"mid", "ceiling"}:
        raise ValueError(f"unknown position {position!r}")
    if ceiling is None:
        raise ValueError(
            f"position {position!r} requires a closed band; {band!r} is open-ended"
        )
    if position == "ceiling":
        return ceiling
    return (floor + ceiling) // 2


def build_initial_traits_for_monster_tier(
    tier_key: str, position: str = "floor"
) -> dict[str, int]:
    """Build base monster values directly from the named tier's bands."""
    tier = MONSTER_TIER_REGISTRY[tier_key]
    return {
        "hp": _resolve_band_position(tier.hp_band, position),
        "mp": 0,
        "sp": 0,
        "atk_phys": _resolve_band_position(tier.static_band.atk_phys, position),
        "agility": _resolve_band_position(tier.static_band.agility, position),
        "defense": _resolve_band_position(tier.static_band.defense, position),
        "magic_level": 0,
        "guild_merit": 0,
    }


def initial_trait_config_for_monster_tier(
    tier_key: str, position: str = "floor"
) -> dict[str, dict[str, Any]]:
    """Return monster construction data ready for ``TraitHandler.add``."""
    values = build_initial_traits_for_monster_tier(tier_key, position)
    return _trait_config(values, 0)


def get_display_value(entity: Any, trait_key: str) -> int:
    """Read a possibly disguised base stat for exactly three display consumers.

    The only permitted callers are appearance rendering (``look``), guild
    registration records, and appraisal items. Combat, resolution, and damage
    must read true traits directly and must never call this function.
    """
    disguised = entity.db.disguised_stats or {}
    if trait_key in disguised:
        return disguised[trait_key]
    return getattr(entity.traits, trait_key).value
