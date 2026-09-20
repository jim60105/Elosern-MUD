"""Preset- and quest-domain catalogs plus the lazily built issuance rows.
"""

from __future__ import annotations

from dataclasses import replace
from world.lore.player_presets import PlayerPreset, PresetPersona, StartingCompanion
from world.quests.definitions import (
    KNOWN_GRID_MAP_KEYS,
    DestinationKind,
    ObjectiveKind,
    QuestDefinition,
    QuestObjective,
    QuestStage,
    QuestType,
    RoomLocator,
)
from world.rules.guild_offers import ItemQuantity, QuestReward
from world.rules.quest_issuance import QuestIssuance, Settlement

from world.tests.synthetic_data.vocab import _SYNTH_ELEMENT

SYNTH_PRESETS: dict[str, PlayerPreset] = {
    "t_pale_wren": PlayerPreset(
        key="t_pale_wren",
        display_name="蒼雀",
        age=21,
        apparent_age=20,
        race="t_duskmari",
        subrace="t_duskmari_evensong",
        # Sums exactly to the t_duskmari_evensong profile budget (218) within
        # the per-axis spans, so preset activation validates against the
        # patched race registry (seed base-character path).
        allocations=(
            ("hp", 45),
            ("mp", 38),
            ("sp", 40),
            ("atk_phys", 20),
            ("agility", 20),
            ("defense", 15),
            ("magic_power", 40),
        ),
        emphasis="Synthetic wanderer card.",
        active_skills=("t_ember_burst", "t_cinder_cleave"),
        passive_skills=("t_steady_stride",),
        affinity_elements=(_SYNTH_ELEMENT,),
        starting_items=(("t_ember_spray", 2), ("t_iron_fang", 1)),
        sex="female",
        skill_proficiency=(("t_ember_burst", 10.0),),
        # The creation presenter validates every preset card's background as
        # non-empty (every shipped card authors one), so the kit cards carry
        # synthetic persona prose of their own.
        persona=PresetPersona(
            personality="安靜而警覺。",
            background="Synthetic wanderer preset persona background.",
        ),
    ),
    "t_ash_finch": PlayerPreset(
        key="t_ash_finch",
        display_name="燼雀",
        age=24,
        apparent_age=23,
        race="t_duskmari",
        subrace="t_duskmari_evensong",
        allocations=(
            ("hp", 35),
            ("mp", 45),
            ("sp", 45),
            ("atk_phys", 22),
            ("agility", 18),
            ("defense", 18),
            ("magic_power", 35),
        ),
        emphasis="Synthetic porter card.",
        active_skills=("t_cinder_cleave",),
        passive_skills=("t_steady_stride",),
        starting_items=(("t_huskapple", 3),),
        sex="male",
        persona=PresetPersona(
            personality="寡言的搬運工。",
            background="Synthetic porter preset persona background.",
        ),
    ),
}

# t_pale_wren's companion chain points at the other synthetic card, so a
# scope patching presets resolves the whole chain without shipped data.
SYNTH_PRESETS["t_pale_wren"] = replace(
    SYNTH_PRESETS["t_pale_wren"],
    starting_companions=(
        StartingCompanion(
            preset_key="t_ash_finch", affinity=1, relationship="同行搬運工"
        ),
    ),
)

SYNTH_QUESTS: dict[str, QuestDefinition] = {
    "t_ember_cull": QuestDefinition(
        key="t_ember_cull",
        display_name="燼殼蟲清剿",
        quest_type=QuestType.DEFEAT,
        rank="t_bronze",
        stages=(
            QuestStage(
                0,
                QuestObjective(
                    kind=ObjectiveKind.DEFEAT, quantity=2, monster_tier="t_faint"
                ),
            ),
        ),
        deadline_hours=48,
    ),
    "t_tarn_messenger": QuestDefinition(
        key="t_tarn_messenger",
        display_name="湖邑送證",
        quest_type=QuestType.EXPLORE,
        rank="t_bronze",
        stages=(
            QuestStage(
                0,
                QuestObjective(
                    kind=ObjectiveKind.REACH,
                    destination=RoomLocator(
                        kind=DestinationKind.ANCHOR, anchor_key="t_hollow_tarn"
                    ),
                ),
            ),
        ),
    ),
}

SYNTH_QUEST_REWARDS: dict[str, QuestReward] = {
    "t_ember_cull": QuestReward(
        copper=120,
        items=(ItemQuantity(item_key="t_ember_spray", quantity=1),),
        merit=10,
    ),
    "t_tarn_messenger": QuestReward(copper=80, items=(), merit=5),
}

SYNTH_GUILD_BRANCH_KEY = "t_mossgate_branch"
SYNTH_COMMISSIONER_KEY = "npc:t_grey_lantern"
SYNTH_GUILD_ISSUER_KEY = "guild:" + SYNTH_GUILD_BRANCH_KEY


def _build_issuances() -> dict[tuple[str, str], QuestIssuance]:
    """Build the synthetic issuance rows against the registered definitions.

    ``QuestIssuance`` resolves its definition key through the (patched)
    definition registry, so this is called lazily when a scope installs the
    quest targets, not at kit import.
    """
    issuances: dict[tuple[str, str], QuestIssuance] = {}
    for definition_key, reward in SYNTH_QUEST_REWARDS.items():
        issuances[(definition_key, SYNTH_GUILD_ISSUER_KEY)] = QuestIssuance(
            definition_key=definition_key,
            issuer_key=SYNTH_GUILD_ISSUER_KEY,
            reward=reward,
            settlement=Settlement.COUNTER,
        )
        issuances[(definition_key, SYNTH_COMMISSIONER_KEY)] = QuestIssuance(
            definition_key=definition_key,
            issuer_key=SYNTH_COMMISSIONER_KEY,
            reward=QuestReward(
                copper=reward.copper, items=reward.items, merit=0
            ),
            settlement=Settlement.AUTO,
        )
    return issuances
