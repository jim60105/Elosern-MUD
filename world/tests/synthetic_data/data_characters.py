"""Character-domain catalogs: races, static tiers, subraces, kits, and NPC/monster tiers.
"""

from __future__ import annotations

from types import MappingProxyType
from world.lore.monsters import MonsterTier
from world.lore.npc_tiers import NPCTier
from world.lore.races import (
    RaceProfile,
    StaticBand,
    StaticTier,
    StatModifiers,
    Subrace,
    Vitals,
)
from world.lore.starting_kits import SubraceStartingKit

from world.tests.synthetic_data.vocab import _SYNTH_ELEMENT

SYNTH_RACES: dict[str, RaceProfile] = {
    "t_duskmari": RaceProfile(
        key="t_duskmari",
        lifespan=(70, 90),
        vital_baseline=Vitals(hp=(110, 210), mp=(90, 180), sp=(105, 200)),
        static_baseline=StaticBand(
            atk_phys=(2, 24), agility=(2, 24), defense=(2, 24), magic_power=(6, 92)
        ),
        learning_multiplier=1.0,
        can_use_divine_arts=False,
        description="壽命略長於人族、習慣在暮色中行動的合成種族。",
    ),
}

SYNTH_STATIC_TIERS: dict[str, StaticTier] = {
    "t_duskmari_wanderer": StaticTier(
        "t_duskmari_wanderer",
        "t_duskmari",
        "漫遊的合成民",
        1,
        (1, 6),
        None,
        "Synthetic wanderer tier.",
        (6, 30),
    ),
    "t_duskmari_warden": StaticTier(
        "t_duskmari_warden",
        "t_duskmari",
        "守夜的合成民",
        2,
        (7, 18),
        "t_bronze",
        "Synthetic warden tier.",
        (31, 60),
    ),
}

SYNTH_SUBRACES: dict[str, Subrace] = {
    "t_duskmari_evensong": Subrace(
        key="t_duskmari_evensong",
        race_key="t_duskmari",
        display_name_zh="暮歌支系",
        common_name_zh="暮歌者",
        population=900,
        home_anchor_key="t_hollow_tarn",
        affinity_elements=(_SYNTH_ELEMENT,),
        specialty="在暮色中吟唱導引的合成支系。",
        static_modifiers=StatModifiers(atk_phys=0.05, agility=0.05, defense=0.0),
    ),
}

# One basic starting-equipment kit per synthetic subrace, so a scoped custom
# activation hands out exactly what the synthetic kit declares instead of
# falling back to a shipped per-subrace loadout.
SYNTH_STARTING_KITS: dict[str, SubraceStartingKit] = {
    kit.subrace_key: kit
    for kit in (
        SubraceStartingKit("t_duskmari_evensong", (("t_thorn_knife", 1),)),
    )
}

SYNTH_NPC_TIERS: MappingProxyType[str, NPCTier] = MappingProxyType(
    {
        tier.key: tier
        for tier in (
            NPCTier(
                "t_synth_courier",
                "合成信差",
                "奔走於合成聚落之間送信的平民。",
                "t_duskmari",
                "t_duskmari_wanderer",
            ),
            NPCTier(
                "t_synth_ward",
                "合成巡守",
                "維持苔徑市集秩序的巡守人員。",
                "t_duskmari",
                "t_duskmari_warden",
            ),
        )
    }
)

SYNTH_MONSTER_TIERS: dict[str, MonsterTier] = {
    "t_faint": MonsterTier(
        "t_faint",
        "微光級",
        ("t_bronze", "t_bronze"),
        StaticBand(
            atk_phys=(3, 9), agility=(3, 9), defense=(3, 9), magic_power=(0, 0)
        ),
        (40, 120),
        ("燼殼蟲", "薄暮狐"),
        "Synthetic faint threat band.",
    ),
    "t_riven": MonsterTier(
        "t_riven",
        "裂光級",
        ("t_bronze", "t_silver"),
        StaticBand(
            atk_phys=(12, 22), agility=(12, 22), defense=(12, 22), magic_power=(0, 0)
        ),
        (210, 420),
        ("鐵牙猔", "灰霧角獸"),
        "Synthetic riven threat band.",
    ),
}
