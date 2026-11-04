"""Synthetic monster placement slice (monster-site-placement).

One authored ecology zone, the complete encounter compositions that zone and
the sites name, and three authored sites, built from the real definition
classes, so scopes that read the placement registries (and the lore-sync
capture that mirrors them) have a complete synthetic stand-in. Every region
key, composition key and site key is ``t_``-prefixed and every referenced
variant is a synthetic one, so no shipped key appears here.
"""

from __future__ import annotations

from world.lore.monster_activity import (
    ActivityArea,
    AggressionCondition,
    MonsterActivity,
)
from world.lore.monster_placement import (
    CompositionMember,
    EcologyZone,
    EncounterComposition,
    MonsterSite,
    WeightedComposition,
)

SYNTH_ACTIVITY_AREAS: dict[str, ActivityArea] = {
    # One region extent matching the synthetic habitat's authored rectangle, so
    # a scope can resolve ordinary activity against the synthetic candidate.
    "t_bramble_ground": ActivityArea(
        "t_bramble_ground", "t_bramble_wold", ((500, 519, 700, 719),)
    ),
    # The synthetic manual sites all sit at one cell; a zero-radius home extent
    # expresses a stationary site without any further geometry.
    "t_site_home": ActivityArea("t_site_home", home_radius=0),
}

SYNTH_MONSTER_ACTIVITIES: dict[str, MonsterActivity] = {
    "t_whisper_quail_solitary_activity": MonsterActivity(
        "t_whisper_quail_solitary_activity",
        "solitary_roaming",
        "t_bramble_ground",
        60,
        AggressionCondition("passive"),
    ),
    "t_whisper_quail_group_activity": MonsterActivity(
        "t_whisper_quail_group_activity",
        "cohesive_group",
        "t_bramble_ground",
        90,
        AggressionCondition("contact"),
    ),
    "t_whisper_quail_stationary": MonsterActivity(
        "t_whisper_quail_stationary",
        "stationary",
        "t_site_home",
        120,
        AggressionCondition("passive"),
    ),
}

SYNTH_ENCOUNTER_COMPOSITIONS: dict[str, EncounterComposition] = {
    "t_whisper_quail_solitary": EncounterComposition(
        "t_whisper_quail_solitary",
        "t_whisper_quail_solitary_activity",
        (CompositionMember("t_whisper_quail_ordinary", 1, 1),),
    ),
    "t_whisper_quail_pair": EncounterComposition(
        "t_whisper_quail_pair",
        "t_whisper_quail_group_activity",
        (
            CompositionMember("t_whisper_quail_ordinary", 1, 1),
            CompositionMember("t_whisper_quail_stronger", 1, 1),
        ),
    ),
    "t_whisper_quail_group": EncounterComposition(
        "t_whisper_quail_group",
        "t_whisper_quail_group_activity",
        (
            CompositionMember("t_whisper_quail_ordinary", 2, 2),
            CompositionMember("t_whisper_quail_stronger", 1, 1),
        ),
    ),
    "t_whisper_quail_flock": EncounterComposition(
        "t_whisper_quail_flock",
        "t_whisper_quail_group_activity",
        (CompositionMember("t_whisper_quail_ordinary", 1, 3),),
    ),
}

SYNTH_ECOLOGY_ZONES: dict[str, EcologyZone] = {
    # One bounded habitat in the first synthetic region. Its pool places the
    # ordinary and stronger quail together or alone, so a synthetic regional
    # hunt has a lawful authored source.
    "t_bramble_wold_habitat": EcologyZone(
        "t_bramble_wold_habitat",
        "t_bramble_wold",
        ((500, 519, 700, 719),),
        (
            WeightedComposition("t_whisper_quail_solitary", 1),
            WeightedComposition("t_whisper_quail_pair", 1),
            WeightedComposition("t_whisper_quail_group", 1),
        ),
        1,
        3,
        3,
        3600,
        600,
        3,
    ),
}

SYNTH_MONSTER_SITES: dict[str, MonsterSite] = {
    # A valid wilderness surface in the shared test world: scopes that settle
    # the registry register each site's individuals through the placing owner's
    # surface validation, so a site may not sit on an unwalkable cell.
    "t_breakwater_nest": MonsterSite(
        "t_breakwater_nest",
        "nest",
        "t_bramble_wold",
        (500, 700),
        "t_whisper_quail_pair",
        "t_whisper_quail_stationary",
        2,
        True,
    ),
    "t_shoreward_camp": MonsterSite(
        "t_shoreward_camp",
        "camp",
        "t_glassmere",
        (500, 700),
        "t_whisper_quail_solitary",
        "t_whisper_quail_stationary",
        1,
        False,
        3600,
    ),
    "t_glassmere_boss": MonsterSite(
        "t_glassmere_boss",
        "boss_site",
        "t_glassmere",
        (500, 700),
        "t_whisper_quail_solitary",
        "t_whisper_quail_stationary",
        1,
        True,
    ),
}
