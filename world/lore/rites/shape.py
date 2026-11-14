"""Immutable value shapes of the authored landmark rite document.

This module is part of the pure data layer in ``world.lore``: it stores values
and validates nothing. ``world.lore.rites.loader`` owns every bound, so a shape
constructed directly (as the later settlement and panel tests do) is never
re-checked here.

One rite document is one snapshot of ritual archetypes -- each owning a guardian
and two or three options, each option owning a ``self`` scene and an optional
``watch`` scene -- plus the assignment of every map district to exactly one
archetype. Consumers read the snapshot installed by :mod:`world.lore.rites`; the
rules layer never parses the YAML source.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from world.lore.scenes import Scene

__all__ = [
    "RiteArchetype",
    "RiteOption",
    "RiteSnapshot",
    "art_subject_key",
]


@dataclass(frozen=True, slots=True)
class RiteOption:
    """One authored ritual story within an archetype.

    ``watch_scene`` is the companion's perspective; ``None`` marks a solo-only
    ritual that refuses companion performance.
    """

    key: str
    label_zh: str
    seconds: int
    shame: int
    exposure: int
    self_scene: Scene
    watch_scene: Scene | None


@dataclass(frozen=True, slots=True)
class RiteArchetype:
    """One authored ritual family: its guardian and its options in authored order."""

    key: str
    guardian_name_zh: str
    guardian_form_zh: str
    options: tuple[RiteOption, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "options", tuple(self.options))

    def option(self, key: str) -> RiteOption | None:
        """The option authored under ``key``, or ``None``."""

        for option in self.options:
            if option.key == key:
                return option
        return None


@dataclass(frozen=True, slots=True)
class RiteSnapshot:
    """One immutable rite world: the archetypes and the district assignment."""

    archetypes: Mapping[str, RiteArchetype]
    districts: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "archetypes", MappingProxyType(dict(self.archetypes)))
        object.__setattr__(self, "districts", MappingProxyType(dict(self.districts)))

    def archetype_for(self, district_key: str) -> RiteArchetype | None:
        """The archetype assigned to ``district_key``, or ``None``."""

        archetype_key = self.districts.get(district_key)
        if archetype_key is None:
            return None
        return self.archetypes.get(archetype_key)


def art_subject_key(archetype_key: str) -> str:
    """The ``scene:`` art subject key of one archetype (derived, never stored)."""

    return f"rite_{archetype_key}"