"""Authored scripted-dialogue snapshot loaded from YAML content.

``DIALOGUE_SNAPSHOT`` is immutable authored dialogue keyed by a stable
identifier (``dialogue_key``). The rows are loaded from scanner-discovered
per-profile YAML files under ``world/lore/dialogue/content/<profile_key>.yaml``
using canonical place bindings.
"""

from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from world.lore.dialogue.loader import load_dialogue_snapshot
from world.lore.dialogue.shape import (
    AuthoredDialogue,
    AuthoredTopic,
    DialogueDefinition,
    KeywordResponse,
    SceneVariant,
)
from world.lore.npc_profiles import NPC_PROFILE_REGISTRY
from world.lore.settlements.places import PLACE_REGISTRY, place_dialogue_keys

CONTENT_DIR = Path(__file__).resolve().parent / "content"


def canonical_dialogue_bindings() -> dict[str, str]:
    """Derive canonical dialogue_key -> profile_key mappings from PLACE_REGISTRY."""
    bindings: dict[str, str] = {}
    for place in PLACE_REGISTRY.values():
        if not place.host_profile_key:
            continue
        for dialogue_key in place_dialogue_keys(place):
            bindings[dialogue_key] = place.host_profile_key
    return bindings


def _load_snapshot() -> Mapping[str, AuthoredDialogue]:
    # Function-local import (the guild.py/names.py/shops.py precedent): lore
    # stays import-light, and the catalog is composed from the canonical
    # registries by its rules-side owner. The builder itself imports nothing
    # from ``world.lore`` at module scope, so this call is also safe when
    # ``world.rules.dialogue_references`` was imported first.
    from world.rules.dialogue_references import static_dialogue_references

    bindings = canonical_dialogue_bindings()
    profiles = frozenset(NPC_PROFILE_REGISTRY.keys())
    return load_dialogue_snapshot(
        CONTENT_DIR,
        profiles=profiles,
        bindings=bindings,
        references=static_dialogue_references(),
    )


DIALOGUE_SNAPSHOT: MappingProxyType[str, AuthoredDialogue] = MappingProxyType(
    _load_snapshot()
)
DIALOGUE_ROWS: MappingProxyType[str, AuthoredDialogue] = DIALOGUE_SNAPSHOT

__all__ = [
    "CONTENT_DIR",
    "DIALOGUE_ROWS",
    "DIALOGUE_SNAPSHOT",
    "canonical_dialogue_bindings",
]
