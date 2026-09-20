"""Local fixture factories (design D3): one synthetic entry per call, keyword overrides.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from world.lore.anchors import Anchor, AnchorKind
from world.lore.economy import PriceEntry
from world.lore.elements import Element
from world.lore.guild import GuildBranch, GuildRank
from world.lore.items import (
    ItemDefinition,
    EquipmentModifierKey,
    EquipmentSlot,
    ItemIconKey,
    ItemKind,
    ItemPresentation,
    ItemRarity,
    ItemUseMechanics,
)
from world.lore.magic import MagicTier
from world.lore.monsters import MonsterTier
from world.lore.names import FrozenDict, NamePack, NamePart
from world.lore.nations import Nation
from world.lore.npc_tiers import NPCTier
from world.lore.player_presets import PlayerPreset, PresetPersona, StartingCompanion
from world.lore.races import (
    RaceProfile,
    StaticBand,
    StaticTier,
    StatModifiers,
    Subrace,
    Vitals,
)
from world.lore.scene_archetypes import SceneArchetype
from world.lore.shops import ShopDefinition
from world.lore.titles import (
    FixedTitleDef,
    TitleCategory,
    TitlePredicate,
    TitlePredicateFamily,
)
from world.lore.wilderness_entry import WildernessEntryPoint, WildernessGate
from world.lore.wilderness_regions import WildernessRegion
from world.maps.city_gates import CityGateDef
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
from world.rules.buffs import BuffDefinition
from world.rules.dialogue import DialogueDefinition, KeywordResponse
from world.rules.guild_offers import ItemQuantity, QuestReward
from world.rules.quest_issuance import QuestIssuance, Settlement
from world.skills.cost_tiers import CostTier
from world.skills.registry import (
    SkillCategory,
    SkillDef,
    SkillKind,
    SkillPrerequisite,
    TargetSpec,
)
from world.skills.sexual_acts._builder import SexualActDef

from world.tests.synthetic_data.vocab import SYNTH_PREFIX, _SYNTH_MAP_KEY
from world.tests.synthetic_data.data_items import SYNTH_ITEMS, SYNTH_PRICES
from world.tests.synthetic_data.data_skills import SYNTH_ACT, SYNTH_ACT_SKILL, SYNTH_SKILLS
from world.tests.synthetic_data.data_characters import (
    SYNTH_MONSTER_TIERS,
    SYNTH_NPC_TIERS,
    SYNTH_RACES,
    SYNTH_STATIC_TIERS,
    SYNTH_SUBRACES,
)
from world.tests.synthetic_data.data_world import (
    SYNTH_ANCHORS,
    SYNTH_ARCHETYPES,
    SYNTH_BUFFS,
    SYNTH_CITY_GATES,
    SYNTH_DIALOGUE,
    SYNTH_GUILD_RANKS,
    SYNTH_NAME_PACKS,
    SYNTH_NATIONS,
    SYNTH_REGIONS,
    SYNTH_SHOPS,
    SYNTH_TITLES,
    SYNTH_WILDERNESS_ENTRIES,
)
from world.tests.synthetic_data.data_presets_quests import (
    SYNTH_COMMISSIONER_KEY,
    SYNTH_GUILD_BRANCH_KEY,
    SYNTH_PRESETS,
    SYNTH_QUESTS,
    SYNTH_QUEST_REWARDS,
)

# ---------------------------------------------------------------------------
# Factories (design D3): one synthetic entry, keyword overrides, local scope.
# ---------------------------------------------------------------------------
def _derive(base: object, **overrides: object) -> object:
    """Copy one frozen synthetic entry with keyword overrides."""
    merged = {
        field.name: getattr(base, field.name)
        for field in _dataclass_fields(base)
    }
    merged.update(overrides)
    return type(base)(**merged)


def _dataclass_fields(instance: object):
    import dataclasses

    return dataclasses.fields(instance)


def _make(key: str, base: object, overrides: Mapping[str, object]) -> object:
    if not key.startswith(SYNTH_PREFIX):
        raise ValueError(f"synthetic keys must start with {SYNTH_PREFIX!r}, got {key!r}")
    return _derive(base, key=key, **{k: v for k, v in overrides.items() if k != "key"})


def make_item(key: str = "t_made_item", **overrides: object) -> ItemDefinition:
    """One synthetic item; overrides may carry presentation/use_mechanics/etc."""
    return _make(key, SYNTH_ITEMS["t_iron_fang"], overrides)


def make_skill(key: str = "t_made_skill", **overrides: object) -> SkillDef:
    """One synthetic skill definition from the martial template."""
    return _make(key, SYNTH_SKILLS["t_cinder_cleave"], overrides)


def make_price(key: str = "t_made_price", **overrides: object) -> PriceEntry:
    """One synthetic price-table entry."""
    return _make(key, SYNTH_PRICES["t_mossmeals"], overrides)


def make_npc_tier(key: str = "t_made_tier", **overrides: object) -> NPCTier:
    """One synthetic NPC role tier."""
    return _make(key, SYNTH_NPC_TIERS["t_synth_courier"], overrides)


def make_monster_tier(key: str = "t_made_monster_tier", **overrides: object) -> MonsterTier:
    """One synthetic monster threat tier."""
    return _make(key, SYNTH_MONSTER_TIERS["t_faint"], overrides)


def make_anchor(key: str = "t_made_anchor", **overrides: object) -> Anchor:
    """One synthetic geographic anchor."""
    return _make(key, SYNTH_ANCHORS["t_hollow_tarn"], overrides)


def make_region(key: str = "t_made_region", **overrides: object) -> WildernessRegion:
    """One synthetic wilderness region."""
    return _make(key, SYNTH_REGIONS["t_glassmere"], overrides)


def make_city_gate(key: str = "t_made_gate", **overrides: object) -> CityGateDef:
    """One synthetic city-gate row (the registry key IS the map id)."""
    if not key.startswith(SYNTH_PREFIX):
        raise ValueError(f"synthetic keys must start with {SYNTH_PREFIX!r}, got {key!r}")
    overrides.setdefault("map_id", key)
    overrides.setdefault("gate_xyz", (2, 0, key))
    base = SYNTH_CITY_GATES[_SYNTH_MAP_KEY]
    merged = {field.name: getattr(base, field.name) for field in _dataclass_fields(base)}
    merged.update(overrides)
    return CityGateDef(**merged)


def make_archetype(key: str = "t_made_archetype", **overrides: object) -> SceneArchetype:
    """One synthetic scene archetype."""
    return _make(key, SYNTH_ARCHETYPES["t_synth_bazaar"], overrides)


def make_price_entry(key: str = "t_made_price", **overrides: object) -> PriceEntry:
    """Alias of :func:`make_price` mirroring the catalog noun."""
    return make_price(key, **overrides)


def make_shop(key: str = "t_made_shop", **overrides: object) -> ShopDefinition:
    """One synthetic shop identity."""
    return _make(key, SYNTH_SHOPS["t_mossgate_stall"], overrides)


def make_title(key: str = "t_made_title", **overrides: object) -> FixedTitleDef:
    """One synthetic fixed-title row."""
    return _make(key, SYNTH_TITLES["t_synth_first_hunt"], overrides)


def make_buff(key: str = "t_made_buff", **overrides: object) -> BuffDefinition:
    """One synthetic buff definition."""
    return _make(key, SYNTH_BUFFS["t_moss_veil"], overrides)


def make_dialogue(key: str = "t_made_dialogue", **overrides: object) -> DialogueDefinition:
    """One synthetic dialogue table."""
    return _make(key, SYNTH_DIALOGUE["t_synth_lodgekeeper"], overrides)


def make_act(key: str = "t_made_act", **overrides: object) -> SexualActDef:
    """One synthetic sexual act (build the paired SkillDef via make_act_skill)."""
    return _make(key, SYNTH_ACT, overrides)


def make_act_skill(key: str = "t_made_act", **overrides: object) -> SkillDef:
    """The SkillDef half of a synthetic act row (same key contract)."""
    return _make(key, SYNTH_ACT_SKILL, overrides)


def make_quest(key: str = "t_made_quest", **overrides: object) -> QuestDefinition:
    """One synthetic quest definition (defeat template)."""
    return _make(key, SYNTH_QUESTS["t_ember_cull"], overrides)


def make_preset(key: str = "t_made_preset", **overrides: object) -> PlayerPreset:
    """One synthetic player-preset card."""
    return _make(key, SYNTH_PRESETS["t_pale_wren"], overrides)


def make_race(key: str = "t_made_race", **overrides: object) -> RaceProfile:
    """One synthetic race profile."""
    return _make(key, SYNTH_RACES["t_duskmari"], overrides)


def make_subrace(key: str = "t_made_subrace", **overrides: object) -> Subrace:
    """One synthetic subrace."""
    return _make(key, SYNTH_SUBRACES["t_duskmari_evensong"], overrides)


def make_static_tier(key: str = "t_made_static_tier", **overrides: object) -> StaticTier:
    """One synthetic static tier."""
    return _make(key, SYNTH_STATIC_TIERS["t_duskmari_wanderer"], overrides)


def make_nation(key: str = "t_made_nation", **overrides: object) -> Nation:
    """One synthetic nation row."""
    return _make(key, SYNTH_NATIONS["t_miremoth"], overrides)


def make_guild_rank(key: str = "t_made_rank", **overrides: object) -> GuildRank:
    """One synthetic guild rank row."""
    return _make(key, SYNTH_GUILD_RANKS["t_bronze"], overrides)


def make_element(key: str = "t_made_element", **overrides: object) -> Element:
    """One synthetic element row."""
    return _make(key, Element("t_made_element", "灰燼", "Synthetic element."), overrides)


def make_magic_tier(key: str = "t_made_magic_tier", **overrides: object) -> MagicTier:
    """One synthetic magic tier row."""
    return _make(
        key,
        MagicTier("t_made_magic_tier", "微明", 0, 20, (), "Synthetic magic tier."),
        overrides,
    )


def make_name_pack(key: str = "t_made_pack", **overrides: object) -> NamePack:
    """One synthetic name pack."""
    return _make(key, SYNTH_NAME_PACKS["t_corpus"], overrides)


def make_wilderness_entry(
    key: str = "t_made_entry", **overrides: object
) -> WildernessEntryPoint:
    """One synthetic wilderness entry point."""
    return _make(key, SYNTH_WILDERNESS_ENTRIES["t_hollow_tarn"], overrides)


def make_wilderness_gate(
    return_direction: str = "s",
    grid_xy: tuple[int, int] = (3, 3),
    z_map_key: str | None = None,
) -> WildernessGate:
    """One synthetic wilderness gate against the known map extent."""
    return WildernessGate(return_direction, grid_xy, z_map_key or _SYNTH_MAP_KEY)


def make_quest_reward(
    copper: int = 100,
    items: tuple[ItemQuantity, ...] = (),
    merit: int = 5,
) -> QuestReward:
    """One synthetic quest reward."""
    return QuestReward(copper=copper, items=items, merit=merit)


def make_issuance(
    definition_key: str,
    issuer_key: str = SYNTH_COMMISSIONER_KEY,
    reward: QuestReward | None = None,
    settlement: Settlement = Settlement.AUTO,
) -> QuestIssuance:
    """One synthetic issuance (construction resolves inside a synthetic quest scope)."""
    return QuestIssuance(
        definition_key=definition_key,
        issuer_key=issuer_key,
        reward=reward or SYNTH_QUEST_REWARDS[definition_key],
        settlement=settlement,
    )


def make_cost_tier(
    min_level: int = 0,
    max_level: int | None = 15,
    single_mp: tuple[int, int] = (10, 16),
    area_mp: tuple[int, int] = (14, 20),
) -> CostTier:
    """One synthetic MP cost tier."""
    return CostTier(min_level, max_level, single_mp, area_mp)


def make_guild_offer(
    definition_key: str,
    issuer_branch_key: str = SYNTH_GUILD_BRANCH_KEY,
    reward: QuestReward | None = None,
):
    """One synthetic guild offer (import deferred to avoid rules coupling at import)."""
    from world.rules.guild_offers import GuildQuestOffer

    return GuildQuestOffer(
        definition_key=definition_key,
        issuer_branch_key=issuer_branch_key,
        reward=reward
        or QuestReward(copper=100, items=(), merit=5),
    )


def make_item_quantity(item_key: str = "t_ember_spray", quantity: int = 1) -> ItemQuantity:
    """One synthetic reward item quantity."""
    return ItemQuantity(item_key=item_key, quantity=quantity)


def make_objective(**overrides: object) -> QuestObjective:
    """One synthetic quest objective (defeat template)."""
    return _derive(
        QuestObjective(kind=ObjectiveKind.DEFEAT, quantity=2, monster_tier="t_faint"),
        **overrides,
    )


def make_stage(index: int = 0, objective: QuestObjective | None = None) -> QuestStage:
    """One synthetic quest stage."""
    return QuestStage(index=index, objective=objective or make_objective())
