"""Synthetic monster placement slice (monster-site-placement).

One region-keyed ambient rule per synthetic region plus three authored sites,
built from the real definition classes, so scopes that read the placement
registries (and the lore-sync capture that mirrors them) have a complete
synthetic stand-in. Every region key and site key is ``t_``-prefixed and every
referenced variant is a synthetic one, so no shipped key appears here.
"""

from __future__ import annotations

from world.lore.monster_placement import AmbientPlacementRule, MonsterSite

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
    "t_breakwater_nest": MonsterSite(
        "t_breakwater_nest",
        "nest",
        "t_bramble_wold",
        (5, 5),
        ("t_whisper_quail_ordinary", "t_whisper_quail_stronger"),
        2,
        True,
    ),
    "t_shoreward_camp": MonsterSite(
        "t_shoreward_camp",
        "camp",
        "t_glassmere",
        (6, 5),
        ("t_whisper_quail_stronger",),
        1,
        False,
        3600,
    ),
    "t_glassmere_boss": MonsterSite(
        "t_glassmere_boss",
        "boss_site",
        "t_glassmere",
        (7, 5),
        ("t_whisper_quail_stronger",),
        1,
        True,
    ),
}
