"""Authored scripted-dialogue snapshot loaded from YAML content.

``DIALOGUE_SNAPSHOT`` is immutable authored dialogue keyed by a stable
identifier (``dialogue_key``). The rows are loaded from scanner-discovered
per-profile YAML files under ``world/lore/dialogue/content/<profile_key>.yaml``
using canonical place bindings.
"""

from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from world.lore.dialogue.conditions import DialogueReferences
from world.lore.dialogue.loader import load_dialogue_snapshot
from world.lore.dialogue.shape import (
    AuthoredDialogue,
    AuthoredTopic,
    DialogueDefinition,
    KeywordResponse,
    SceneVariant,
)
from world.lore.npc_profiles import NPC_PROFILE_REGISTRY
from world.lore.settlements.places import PLACE_REGISTRY

CONTENT_DIR = Path(__file__).resolve().parent / "content"


def canonical_dialogue_bindings() -> dict[str, str]:
    """Derive canonical dialogue_key -> profile_key mappings from PLACE_REGISTRY."""
    bindings: dict[str, str] = {}
    for place in PLACE_REGISTRY.values():
        diag_key = None
        for k, v in place.authored_kwargs:
            if k == "dialogue_key":
                diag_key = v
                break
        if diag_key and place.host_profile_key:
            bindings[diag_key] = place.host_profile_key
    return bindings


def _load_snapshot() -> Mapping[str, AuthoredDialogue]:
    bindings = canonical_dialogue_bindings()
    profiles = frozenset(NPC_PROFILE_REGISTRY.keys())
    return load_dialogue_snapshot(
        CONTENT_DIR,
        profiles=profiles,
        bindings=bindings,
        references=DialogueReferences.empty(),
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
