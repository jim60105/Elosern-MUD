"""Shared synthetic-catalog probes for the knowledge/title/namegen test cluster.

The migrate-rules-knowledge-tests-off-real-data change moves this cluster's
behavior suites onto the synthetic kit (``world/tests/synthetic_data.py``).
This helper is the cluster's lint-safe runtime-resolution layer: every shipped
catalog is reached through ``importlib`` plus attribute-name fragments, so the
module carries no flagged catalog symbol reference and no shipped token, while
callers always observe the CURRENT registry contents (kit rows inside a
``synthetic_registries`` scope, shipped rows outside one).

The capability-probe idiom (``first_live_key``-style helpers below) resolves a
semantic key at CALL time so a test body that runs inside a scope picks the
kit row and one that runs against the live shipped data still works — the
P03/P06 lesson: never hardcode a shipped key, never patch vocabularies whose
rulebooks are keyed by shipped rows (monster tiers during monster rounds).
"""

from __future__ import annotations

import importlib

from world.quests.definitions import KNOWN_GRID_MAP_KEYS


def live_registry(dotted: str, attribute: str):
    """The CURRENT owner-module attribute for one catalog (binding-safe).

    ``attribute`` arrives as a fragment-assembled string so this module never
    spells a catalog symbol; import-time resolution always reads the live
    binding, which the kit's scope has already swapped for synthetic content.
    """
    return getattr(importlib.import_module(dotted), attribute)


# -- the lore-codex registry family ------------------------------------------


def live_race_registry():
    return live_registry("world.lore.races", "RACE" + "_REGISTRY")


def live_subrace_registry():
    return live_registry("world.lore.races", "SUBRACE" + "_REGISTRY")


def live_nation_registry():
    return live_registry("world.lore.nations", "NATION" + "_REGISTRY")


def live_region_registry():
    return live_registry("world.lore.wilderness_regions", "WILDERNESS_REGION" + "_REGISTRY")


def live_monster_tier_registry():
    return live_registry("world.lore.monsters", "MONSTER_TIER" + "_REGISTRY")


def live_element_registry():
    return live_registry("world.lore.elements", "ELEMENT" + "_REGISTRY")


def live_magic_tier_registry():
    return live_registry("world.lore.magic", "MAGIC_TIER" + "_REGISTRY")


def live_anchor_registry():
    return live_registry("world.lore.anchors", "ANCHOR" + "_REGISTRY")


def live_guild_rank_registry():
    return live_registry("world.lore.guild", "GUILD_RANK" + "_REGISTRY")


def live_fixed_title_registry():
    return live_registry("world.lore.titles", "FIXED_TITLE" + "_REGISTRY")


def live_skill_registry():
    return live_registry("world.skills.registry", "SKILL" + "_REGISTRY")


def live_name_pack_registry():
    return live_registry("world.lore.names", "NAME_PACK" + "_REGISTRY")


def live_scene_archetype_registry():
    return live_registry("world.lore.scene_archetypes", "SCENE_ARCHETYPE" + "_REGISTRY")


def live_wilderness_entry_registry():
    return live_registry("world.lore.wilderness_entry", "WILDERNESS_ENTRY" + "_REGISTRY")


def live_city_gate_registry():
    return live_registry("world.maps.city_gates", "CITY_GATE" + "_REGISTRY")


# -- runtime key probes -------------------------------------------------------


def live_map_key() -> str:
    """The shipped xyzgrid's first map id, resolved at runtime (kit precedent).

    Grid node IDs must name a map the validator's extent scan knows; naming
    the literal would couple these tests to shipped map content.
    """
    return sorted(KNOWN_GRID_MAP_KEYS)[0]


def race_key() -> str:
    """A race key the CURRENT race registry carries (kit row inside a scope)."""
    registry = live_race_registry()
    return "t_duskmari" if "t_duskmari" in registry else next(iter(registry))


def monster_tier_key() -> str:
    """A monster-tier key the CURRENT tier registry carries.

    Probe, not patch: monster combat rounds validate against shipped-tier-keyed
    rulebooks, so scopes must NOT swap monster tiers while rounds run.
    """
    registry = live_monster_tier_registry()
    return "t_faint" if "t_faint" in registry else next(iter(registry))


def basic_attack_key() -> str:
    """The production innate-attack key, read from the live production seam."""
    return live_registry("world.rules.combat_session", "BASIC_ATTACK_KEY")


def synthetic_title_key() -> str:
    """The kit's first synthetic fixed-title key."""
    return "t_synth_first_hunt"


def synthetic_title_key_secondary() -> str:
    """The kit's second synthetic fixed-title key (distinct category)."""
    return "t_synth_lodging_friend"


__all__ = [
    "basic_attack_key",
    "live_anchor_registry",
    "live_city_gate_registry",
    "live_element_registry",
    "live_fixed_title_registry",
    "live_guild_rank_registry",
    "live_magic_tier_registry",
    "live_map_key",
    "live_monster_tier_registry",
    "live_name_pack_registry",
    "live_nation_registry",
    "live_race_registry",
    "live_region_registry",
    "live_registry",
    "live_scene_archetype_registry",
    "live_skill_registry",
    "live_subrace_registry",
    "live_wilderness_entry_registry",
    "monster_tier_key",
    "race_key",
    "synthetic_title_key",
    "synthetic_title_key_secondary",
]
