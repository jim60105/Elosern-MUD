"""The static permitted-reference catalog for authored dialogue conditions.

``static_dialogue_references()`` is the ONE place that composes a
:class:`world.lore.dialogue.conditions.DialogueReferences` from the canonical
lore registries plus the world-clock daypart vocabulary and the affinity
rulebook's stage table. Every family this slice evaluates (``race``,
``social_identity``, ``item``, ``skill``, ``preset``, ``profile``, ``daypart``,
``guild_rank``, ``quest`` and ``affinity_stage``) is built here. No slice keeps
a second hand-written key copy.

The catalog is rebuilt on every call rather than cached, because a canonical
registry is read-only game data that the synthetic test-data kit swaps per
scope: a memoized copy would keep answering with the shipped keys and labels
inside a patched scope. Building it is a bounded dictionary projection over
the loaded registries, so the pure read stays cheap.

This module deliberately imports nothing from ``world.lore`` at module scope:
``world.lore.dialogue`` calls :func:`static_dialogue_references` while its own
package initializes its YAML snapshot, and a module-scope lore import would
make ``world.rules.dialogue_references`` unusable in the reverse import order.
Every registry (and the frozen catalog type) is resolved inside the function,
exactly as the lore-side function-local import precedent does.

The daypart family reads the canonical clock rulebook data file directly
instead of importing :mod:`world.rules.clock`: the clock module pulls the
Evennia/Django settlement stack, which must not load while the lore snapshot
is being built. The keys stay the clock rulebook's own, so there is no second
hand-written key copy; only their player-facing labels live here.

The affinity-stage family follows the same rule for the same reason: the stage
ids and their authored display names come from ``rulebook/affinity.yaml``
itself, while the evaluator still compares through the validated
:func:`world.rules.affinity_config.get_config` boundary.

The quest family is the canonical declaration tuple plus every definition the
runtime has registered. The declaration tuple is always readable, so the
import-time lore snapshot validates a shipped quest reference in a cold
process (the registry is populated by the startup composition root); the live
registry adds the compiled package definitions the runtime can resolve.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType

import yaml

CLOCK_RULEBOOK_PATH = Path(__file__).resolve().parent / "rulebook" / "clock.yaml"
AFFINITY_RULEBOOK_PATH = (
    Path(__file__).resolve().parent / "rulebook" / "affinity.yaml"
)

#: The player-facing daypart wording the time-skip surfaces use. These are the
#: canonical labels requirement hints render; a clock rulebook daypart without
#: one fails the catalog build instead of publishing an unrenderable key.
DAYPART_LABELS = MappingProxyType(
    {
        "midnight": "午夜",
        "dawn": "黎明",
        "noon": "正午",
        "dusk": "黃昏",
    }
)


def _daypart_table() -> dict[str, str]:
    """Return the clock rulebook's daypart keys mapped to their canonical labels."""
    document = yaml.safe_load(CLOCK_RULEBOOK_PATH.read_text(encoding="utf-8"))
    dayparts = document.get("dayparts") if isinstance(document, Mapping) else None
    if not isinstance(dayparts, Mapping) or not dayparts:
        raise ValueError(
            f"clock rulebook {CLOCK_RULEBOOK_PATH} declares no dayparts mapping"
        )
    table: dict[str, str] = {}
    for key, hour in dayparts.items():
        if not isinstance(key, str) or not key:
            raise ValueError(
                f"clock rulebook daypart key must be a nonempty string, got {key!r}"
            )
        if isinstance(hour, bool) or not isinstance(hour, int):
            raise ValueError(
                f"clock rulebook daypart {key!r} must declare an integer hour, got {hour!r}"
            )
        label = DAYPART_LABELS.get(key)
        if label is None:
            raise ValueError(
                f"clock rulebook daypart {key!r} has no canonical label; "
                f"add it to DAYPART_LABELS in {__name__}"
            )
        table[key] = label
    return table


def _profile_names() -> dict[str, set[str]]:
    """Map each registered profile key to its canonical authored public names.

    A profile's public name is authored by the sources that materialize it, so
    the catalog reads exactly those rows: a place's service-host name and a
    persistent adventurer's own name. Persona cards and display names are
    never consulted -- a profile whose name is unregistered or whose rows
    disagree is not a resolvable companion reference.
    """
    from world.lore.guild_adventurers import ADVENTURER_REGISTRY
    from world.lore.settlements.places import PLACE_REGISTRY, place_is_hostless

    names: dict[str, set[str]] = {}

    def _add(profile_key: object, name: object) -> None:
        if not isinstance(profile_key, str) or not profile_key:
            return
        if not isinstance(name, str) or not name.strip():
            return
        names.setdefault(profile_key, set()).add(name)

    for place in PLACE_REGISTRY.values():
        if place_is_hostless(place):
            continue
        if not place.host_profile_key:
            continue
        _add(place.host_profile_key, place.host_name)
    for row in ADVENTURER_REGISTRY.values():
        _add(row.profile_key, row.name)
    return names


def _profile_table(registry_keys: Mapping[str, object]) -> dict[str, str]:
    """Return profile keys whose canonical public name resolves uniquely."""
    names = _profile_names()
    table: dict[str, str] = {}
    for key in registry_keys:
        resolved = names.get(key, set())
        if len(resolved) != 1:
            # Missing or ambiguous canonical labels never enter the catalog:
            # an authored condition naming one fails publication instead of
            # shipping a hint no canonical source can render.
            continue
        table[key] = next(iter(resolved))
    return table


def _affinity_stage_table() -> dict[str, str]:
    """Return the affinity rulebook's stage ids mapped to their display names."""
    document = yaml.safe_load(AFFINITY_RULEBOOK_PATH.read_text(encoding="utf-8"))
    stages = document.get("stages") if isinstance(document, Mapping) else None
    if not isinstance(stages, list) or not stages:
        raise ValueError(
            f"affinity rulebook {AFFINITY_RULEBOOK_PATH} declares no stages list"
        )
    table: dict[str, str] = {}
    for position, entry in enumerate(stages, start=1):
        if not isinstance(entry, Mapping):
            raise ValueError(
                f"affinity rulebook stage {position} must be a mapping"
            )
        stage_id = entry.get("id")
        name = entry.get("name")
        if not isinstance(stage_id, str) or not stage_id:
            raise ValueError(
                f"affinity rulebook stage {position} id must be a nonempty string"
            )
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                f"affinity rulebook stage {stage_id!r} name must be a nonempty string"
            )
        if stage_id in table:
            raise ValueError(f"affinity rulebook stage id {stage_id!r} is duplicated")
        table[stage_id] = name
    return table


def _quest_table() -> dict[str, str]:
    """Return every canonical or currently registered quest key and display name."""
    from world.quests.catalog import QUEST_CATALOG
    from world.quests.definitions import QUEST_DEFINITION_REGISTRY

    table = {definition.key: definition.display_name for definition in QUEST_CATALOG}
    table.update(
        {
            key: definition.display_name
            for key, definition in QUEST_DEFINITION_REGISTRY.items()
        }
    )
    return table


def permitted_quest_definition(definition_key: str) -> bool:
    """Whether ``definition_key`` names a canonical or registered quest definition."""
    return definition_key in _quest_table()


def static_dialogue_references() -> "DialogueReferences":
    """Compose the static permitted-reference catalog from canonical registries."""
    from world.lore.dialogue.conditions import DialogueReferences
    from world.lore.guild import GUILD_RANK_REGISTRY
    from world.lore.items import ITEM_REGISTRY
    from world.lore.npc_profiles import NPC_PROFILE_REGISTRY
    from world.lore.player_presets import PLAYER_PRESET_REGISTRY
    from world.lore.races import RACE_REGISTRY
    from world.lore.social_identities import SOCIAL_IDENTITY_REGISTRY
    from world.skills.registry import SKILL_REGISTRY

    catalog = DialogueReferences.empty()
    catalog = catalog.child(
        "race", {key: row.display_name_zh for key, row in RACE_REGISTRY.items()}
    )
    catalog = catalog.child(
        "social_identity",
        {key: row.display_name_zh for key, row in SOCIAL_IDENTITY_REGISTRY.items()},
    )
    catalog = catalog.child(
        "item", {key: row.display_name_zh for key, row in ITEM_REGISTRY.items()}
    )
    catalog = catalog.child(
        "skill", {key: row.label for key, row in SKILL_REGISTRY.items()}
    )
    catalog = catalog.child(
        "preset", {key: row.display_name for key, row in PLAYER_PRESET_REGISTRY.items()}
    )
    catalog = catalog.child("profile", _profile_table(NPC_PROFILE_REGISTRY))
    catalog = catalog.child("daypart", _daypart_table())
    catalog = catalog.child(
        "guild_rank",
        {key: row.display_name_zh for key, row in GUILD_RANK_REGISTRY.items()},
    )
    catalog = catalog.child("quest", _quest_table())
    catalog = catalog.child("affinity_stage", _affinity_stage_table())
    return catalog


__all__ = [
    "AFFINITY_RULEBOOK_PATH",
    "CLOCK_RULEBOOK_PATH",
    "DAYPART_LABELS",
    "permitted_quest_definition",
    "static_dialogue_references",
]
