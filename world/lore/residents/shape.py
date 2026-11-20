"""The authored resident vocabulary: a stable key, literal stats, a home and a schedule.

A resident is a chat-only persistent NPC: it carries an authored ``NpcProfile``
(card, ages, voice lines), lives in its own interior room, and walks between its
home and the village's shared public space on the existing ``resident`` schedule
template. The vocabulary is closed and frozen; content slices own the rows.

All rows are validated when they are constructed: keys are lowercase slugs, the
race/subrace/sex triple resolves in the live race registries, and every literal
stat lies inside the race band the importer uses for authored characters.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY
from world.lore.sex import SEX_VALUES

_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")

#: The seven literal combat values every resident row author carries.
STAT_KEYS: tuple[str, ...] = (
    "hp",
    "mp",
    "sp",
    "atk_phys",
    "agility",
    "defense",
    "magic_power",
)


class ResidentRegistryError(ValueError):
    """An authored resident row or registry violates the resident contract."""


def _require_slug(field: str, value: object) -> str:
    if not isinstance(value, str) or not _KEY_RE.match(value):
        raise ResidentRegistryError(
            f"Resident.{field} {value!r} must be a lowercase snake identifier "
            "(1..64 chars, starting with a letter)"
        )
    return value


def _require_text(field: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ResidentRegistryError(f"Resident.{field} must be non-empty text")
    return value


def _stat_bands(race_key: str, subrace_key: str) -> dict[str, tuple[int, int]]:
    """The authoritative band of every literal stat for one race/subrace."""
    race = RACE_REGISTRY.get(race_key)
    if race is None:
        raise ResidentRegistryError(f"Resident.race {race_key!r} is not registered")
    subrace = SUBRACE_REGISTRY.get(subrace_key)
    if subrace is None:
        raise ResidentRegistryError(
            f"Resident.subrace {subrace_key!r} is not registered"
        )
    if subrace.race_key != race.key:
        raise ResidentRegistryError(
            f"Resident.subrace {subrace_key!r} belongs to race {subrace.race_key!r}, "
            f"not {race_key!r}"
        )
    bands: dict[str, tuple[int, int]] = {
        "hp": race.vital_baseline.hp,
        "mp": race.vital_baseline.mp,
        "sp": race.vital_baseline.sp,
        "atk_phys": race.static_baseline.atk_phys,
        "agility": race.static_baseline.agility,
        "defense": race.static_baseline.defense,
        "magic_power": race.static_baseline.magic_power,
    }
    if subrace.vital_overrides:
        for stat_key, band in subrace.vital_overrides.items():
            if stat_key in bands:
                bands[stat_key] = band
    return bands


def _validated_stats(
    key: str, race_key: str, subrace_key: str, stats: object
) -> Mapping[str, int]:
    if not isinstance(stats, Mapping):
        raise ResidentRegistryError(f"Resident {key!r} stats must be a mapping")
    if set(stats) != set(STAT_KEYS):
        raise ResidentRegistryError(
            f"Resident {key!r} stats must carry exactly {list(STAT_KEYS)}"
        )
    bands = _stat_bands(race_key, subrace_key)
    values: dict[str, int] = {}
    for stat_key in STAT_KEYS:
        value = stats[stat_key]
        if type(value) is not int or value < 0:
            raise ResidentRegistryError(
                f"Resident {key!r} stats.{stat_key} must be a non-negative integer"
            )
        lower, upper = bands[stat_key]
        if not lower <= value <= upper:
            raise ResidentRegistryError(
                f"Resident {key!r} stats.{stat_key}={value} outside "
                f"{race_key!r} band {lower}..{upper}"
            )
        values[stat_key] = value
    return MappingProxyType(values)


@dataclass(frozen=True)
class Resident:
    """One authored chat-only persistent resident."""

    key: str
    name: str
    profile_key: str
    race: str
    subrace: str
    sex: str
    stats: Mapping[str, int]
    home_room: str
    schedule_template: str = "resident"
    dialogue_key: str | None = None

    def __post_init__(self) -> None:
        _require_slug("key", self.key)
        _require_slug("profile_key", self.profile_key)
        _require_text("name", self.name)
        _require_text("home_room", self.home_room)
        _require_text("schedule_template", self.schedule_template)
        if self.dialogue_key is not None and (
            not isinstance(self.dialogue_key, str) or not self.dialogue_key.strip()
        ):
            raise ResidentRegistryError(
                f"Resident {self.key!r} dialogue_key must be non-empty text or None"
            )
        race = RACE_REGISTRY.get(self.race)
        if race is None:
            raise ResidentRegistryError(
                f"Resident {self.key!r} race {self.race!r} is not registered"
            )
        if self.sex not in SEX_VALUES:
            raise ResidentRegistryError(
                f"Resident {self.key!r} sex {self.sex!r} is not a sex value"
            )
        if self.sex not in race.allowed_sexes:
            raise ResidentRegistryError(
                f"Resident {self.key!r} sex {self.sex!r} is not available "
                f"for race {self.race!r}"
            )
        object.__setattr__(
            self,
            "stats",
            _validated_stats(self.key, self.race, self.subrace, self.stats),
        )


def assemble_resident_registry(
    slices: Sequence[tuple[str, Sequence[Resident]]],
) -> dict[str, Resident]:
    """Concatenate owned slices into one keyed registry, rejecting duplicates."""
    registry: dict[str, Resident] = {}
    declared_by: dict[str, str] = {}
    for slice_label, rows in slices:
        for row in rows:
            if not isinstance(row, Resident):
                raise ResidentRegistryError(
                    f"residents slice {slice_label!r} declares a non-Resident row: {row!r}"
                )
            if row.key in registry:
                raise ResidentRegistryError(
                    f"resident key {row.key!r} is declared by both "
                    f"{declared_by[row.key]!r} and {slice_label!r}"
                )
            registry[row.key] = row
            declared_by[row.key] = slice_label
    return registry


def assemble_public_nodes(
    slices: Sequence[tuple[str, str, str | None]],
) -> dict[str, str]:
    """Map each settlement to the authored public node its residents visit.

    A slice may leave the node undeclared while its resident rows are still
    empty. Two slices may share one public node, but they must not disagree
    about the same settlement's node.
    """
    nodes: dict[str, str] = {}
    for slice_label, settlement_key, public_node in slices:
        if not isinstance(settlement_key, str) or not settlement_key.strip():
            raise ResidentRegistryError(
                f"residents slice {slice_label!r} declares no settlement key"
            )
        if public_node is None:
            continue
        if not isinstance(public_node, str) or not public_node.strip():
            raise ResidentRegistryError(
                f"residents slice {slice_label!r} public node must be non-empty text or None"
            )
        existing = nodes.get(settlement_key)
        if existing is not None and existing != public_node:
            raise ResidentRegistryError(
                f"settlement {settlement_key!r} declares two public nodes "
                f"{existing!r} and {public_node!r}"
            )
        nodes[settlement_key] = public_node
    return nodes


__all__ = [
    "Resident",
    "ResidentRegistryError",
    "STAT_KEYS",
    "assemble_public_nodes",
    "assemble_resident_registry",
]
