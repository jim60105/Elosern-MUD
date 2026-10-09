"""Synthetic monster species/variant slice (monster-species-registry).

One invented species with its ordinary and stronger variant, built from the
real definition classes, so scopes that read the species/variant registries
(and the lore-sync capture that mirrors them) have a complete synthetic stand-in.
No shipped key, display string, or author note appears here.
"""

from __future__ import annotations

from world.lore.monster_species import (
    MonsterCombatProfile,
    MonsterSpecies,
    MonsterVariant,
)

SYNTH_MONSTER_SPECIES: dict[str, MonsterSpecies] = {
    "t_whisper_quail": MonsterSpecies(
        "t_whisper_quail",
        "試音鶉",
        "合成物種描述：棲息於合成荊棘荒林的合成鳴禽。",
        "合成物種外觀：小型合成鳴禽。",
        "合成物種生態：以合成氣流震落合成穀粒，能力邊界僅供測試使用。",
        ("t_bramble_wold", "t_glassmere"),
        "（合成作者私有：隱秘真相）合成列沒有已定的起源真相。",
        "（合成作者私有：作者解釋）供行為測試使用的合成物種列。",
        "（合成作者私有：尚未證實的猜想）合成居民相信牠們受合成魔力吸引。",
        "t_whisper_quail_ordinary",
        True,
    ),
}

SYNTH_MONSTER_VARIANTS: dict[str, MonsterVariant] = {
    "t_whisper_quail_ordinary": MonsterVariant(
        "t_whisper_quail_ordinary",
        "t_whisper_quail",
        "試音普通型",
        "合成普通變體，分散覓食。",
        "t_faint",
        True,
        None,
        None,
    ),
    "t_whisper_quail_stronger": MonsterVariant(
        "t_whisper_quail_stronger",
        "t_whisper_quail",
        "試音強勢型",
        "合成較強變體，占據合成隘口。",
        "t_riven",
        False,
        MonsterCombatProfile(
            hp=9,
            mp=1,
            sp=1,
            atk_phys=2,
            agility=2,
            defense=2,
            magic_power=1,
        ),
        "t_bronze",
    ),
    "t_whisper_quail_poor": MonsterVariant(
        "t_whisper_quail_poor",
        "t_whisper_quail",
        "試音貧弱型",
        "合成貧弱變體，無魔力與精力儲備。",
        "t_faint",
        False,
        MonsterCombatProfile(
            hp=6,
            mp=0,
            sp=0,
            atk_phys=1,
            agility=1,
            defense=1,
            magic_power=0,
        ),
        "t_faint",
    ),
}
