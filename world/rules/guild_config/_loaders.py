"""Rulebook loading and the base validators.

Owns the named-error helpers and the YAML loaders; the rulebook path anchor
shifts one level (``parents[1]``) for the package directory.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any, Mapping

import yaml

from world.lore.races import STATIC_TIER_REGISTRY
from world.skills.registry import SKILL_REGISTRY

from ._types import EXAM_RANKS, RANK_TO_TIER, ExamProfile, GuildConfigError


def _error(message: str) -> GuildConfigError:
    return GuildConfigError(f"guild_economy.yaml: {message}")


def _commerce_error(message: str) -> GuildConfigError:
    return GuildConfigError(f"commerce.yaml: {message}")


def _require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _error(f"{field} must be a non-empty string")
    return value


def _require_int(
    value: Any,
    field: str,
    *,
    minimum: int | None = None,
    raise_error: Callable[[str], GuildConfigError] = _error,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise raise_error(f"{field} must be an integer")
    if minimum is not None and value < minimum:
        raise raise_error(f"{field} must be at least {minimum}")
    return value


def load_config() -> dict[str, Any]:
    raw = yaml.safe_load(
        (Path(__file__).parents[1] / "rulebook" / "guild_economy.yaml").read_text(encoding="utf-8")
    )
    if not isinstance(raw, Mapping):
        raise _error("rulebook must be a mapping")
    return dict(raw)


def load_commerce_config() -> dict[str, Any]:
    raw = yaml.safe_load(
        (Path(__file__).parents[1] / "rulebook" / "commerce.yaml").read_text(encoding="utf-8")
    )
    if not isinstance(raw, Mapping):
        raise _commerce_error("rulebook must be a mapping")
    return dict(raw)


def validate_merit_thresholds(raw: Mapping[str, Any]) -> dict[str, int]:
    """Require strictly increasing non-negative E-through-S thresholds."""
    for rank in EXAM_RANKS:
        if rank not in raw:
            raise _error(f"merit_thresholds missing rank {rank!r}")
    unknown = set(raw) - set(EXAM_RANKS)
    if unknown:
        raise _error(f"merit_thresholds has unknown ranks {sorted(unknown)}")
    values = {
        rank: _require_int(raw[rank], f"merit_thresholds.{rank}", minimum=0)
        for rank in EXAM_RANKS
    }
    for lower_rank, upper_rank in zip(EXAM_RANKS, EXAM_RANKS[1:]):
        if not values[lower_rank] < values[upper_rank]:
            raise _error(
                f"merit_thresholds must be strictly increasing: "
                f"{lower_rank}={values[lower_rank]} is not below "
                f"{upper_rank}={values[upper_rank]}"
            )
    return values


def validate_exam_profiles(raw: Mapping[str, Any]) -> dict[str, ExamProfile]:
    """Validate every target-rank profile against its required lore band."""
    if not isinstance(raw, Mapping):
        raise _error("exam_profiles must be a mapping")
    for rank in EXAM_RANKS:
        if rank not in raw:
            raise _error(f"exam_profiles missing rank {rank!r}")
    unknown = set(raw) - set(EXAM_RANKS)
    if unknown:
        raise _error(f"exam_profiles has unknown ranks {sorted(unknown)}")

    profiles: dict[str, ExamProfile] = {}
    for rank in EXAM_RANKS:
        entry = raw[rank]
        if not isinstance(entry, Mapping):
            raise _error(f"exam_profiles.{rank} must be a mapping")
        static_tier_key = entry.get("static_tier")
        if static_tier_key != RANK_TO_TIER[rank]:
            raise _error(
                f"exam_profiles.{rank} must use tier {RANK_TO_TIER[rank]!r}, "
                f"got {static_tier_key!r}"
            )
        tier = STATIC_TIER_REGISTRY[static_tier_key]
        if tier.race_key != "human":
            raise _error(f"exam_profiles.{rank} tier must belong to the human race")
        physical = {
            axis: _require_int(
                entry.get(axis), f"exam_profiles.{rank}.{axis}", minimum=0
            )
            for axis in ("atk_phys", "agility", "defense")
        }
        band = tier.band
        band_floor, band_ceiling = band
        for axis, value in physical.items():
            if not band_floor <= value <= (band_ceiling if band_ceiling is not None else value):
                raise _error(
                    f"exam_profiles.{rank}.{axis}={value} is outside tier "
                    f"{static_tier_key!r} band {(band_floor, band_ceiling)}"
                )
        skills = entry.get("skills")
        if not isinstance(skills, list) or not skills:
            raise _error(f"exam_profiles.{rank}.skills must be a non-empty list")
        if any(not isinstance(key, str) or key not in SKILL_REGISTRY for key in skills):
            raise _error(f"exam_profiles.{rank} references an unknown skill key")
        profiles[rank] = ExamProfile(
            target_rank=rank,
            static_tier_key=static_tier_key,
            hp=_require_int(entry.get("hp"), f"exam_profiles.{rank}.hp", minimum=1),
            mp=_require_int(entry.get("mp"), f"exam_profiles.{rank}.mp", minimum=0),
            sp=_require_int(entry.get("sp"), f"exam_profiles.{rank}.sp", minimum=0),
            atk_phys=physical["atk_phys"],
            agility=physical["agility"],
            defense=physical["defense"],
            magic_power=_require_int(
                entry.get("magic_power"), f"exam_profiles.{rank}.magic_power", minimum=0
            ),
            skills=tuple(skills),
        )
    return profiles
