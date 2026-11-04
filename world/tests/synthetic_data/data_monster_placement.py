"""Synthetic monster placement slice (monster-site-placement).

One region-keyed ambient rule per synthetic region, the complete encounter
compositions those rules and the synthetic sites name, and three authored
sites, built from the real definition classes, so scopes that read the
placement registries (and the lore-sync capture that mirrors them) have a
complete synthetic stand-in. Every region key, composition key and site key is
``t_``-prefixed and every referenced variant is a synthetic one, so no shipped
key appears here.
"""

from __future__ import annotations

from world.lore.monster_placement import (
    AmbientPlacementRule,
    CompositionMember,
    EncounterComposition,
    MonsterSite,
)

SYNTH_ENCOUNTER_COMPOSITIONS: dict[str, EncounterComposition] = {
    "t_whisper_quail_solitary": EncounterComposition(
        "t_whisper_quail_solitary",
        (CompositionMember("t_whisper_quail_ordinary", 1, 1),),
    ),
    "t_whisper_quail_pair": EncounterComposition(
        "t_whisper_quail_pair",
        (
            CompositionMember("t_whisper_quail_ordinary", 1, 1),
            CompositionMember("t_whisper_quail_stronger", 1, 1),
        ),
    ),
    "t_whisper_quail_group": EncounterComposition(
        "t_whisper_quail_group",
        (
            CompositionMember("t_whisper_quail_ordinary", 2, 2),
            CompositionMember("t_whisper_quail_stronger", 1, 1),
        ),
    ),
    "t_whisper_quail_flock": EncounterComposition(
        "t_whisper_quail_flock",
        (CompositionMember("t_whisper_quail_ordinary", 1, 3),),
    ),
}

SYNTH_AMBIENT_PLACEMENTS: dict[str, AmbientPlacementRule] = {
    "t_bramble_wold": AmbientPlacementRule(
        "t_bramble_wold",
        ("t_whisper_quail_ordinary", "t_whisper_quail_stronger"),
        2,
        3,
        1,
    ),
    "t_glassmere": AmbientPlacementRule(
        "t_glassmere",
        ("t_whisper_quail_ordinary",),
        1,
        2,
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
        2,
        True,
    ),
    "t_shoreward_camp": MonsterSite(
        "t_shoreward_camp",
        "camp",
        "t_glassmere",
        (500, 700),
        "t_whisper_quail_solitary",
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
        1,
        True,
    ),
}
