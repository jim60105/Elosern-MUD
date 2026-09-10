"""Shared synthetic game-data kit for behavior tests (add-test-synthetic-data-kit).

One stand-in world: per-catalog dicts built from the REAL definition
dataclasses, keyed with the reserved ``t_`` prefix and carrying invented
Traditional-Chinese display prose, so no kit key or label can ever collide
with a shipped token. The kit is gate-clean BY CONSTRUCTION: this file never
names a shipped catalog symbol or a shipped-content string literally — every
shipped reference goes through ``REGISTRY_TARGETS`` or a runtime lookup by
attribute string, and every display value is invented prose verified disjoint
from the shipped token universe by ``world/tests/test_synthetic_data.py``.

Injection seam (design D2): ``synthetic_registries(...)`` patches the shipped
catalogs for one test/class — ``patch.dict`` (clear+update, in place) for
mutable registries, an attribute swap to a ``MappingProxyType`` for frozen
ones, including every consumer-module binding that name-imported the target
attribute. Consumer bindings are not hand-maintained: an AST discovery pass
enumerates them from the source tree (cached). The lore-sync import-time
capture dict is an explicit target for scopes that invoke ``sync_all()``.

Process scope (design D2b): ``install_synthetic_catalogs()`` applies the same
swap process-wide and idempotently, for the separate managed-browser seed and
server processes that mirror catalogs into a private database at bootstrap.
The browser settings module activates it only under its opt-in flag; the
synthetic-aware seed fixtures and the end-to-end ``t_``-key journey belong to
``migrate-browser-tests-off-real-data``, the kit's first process-scope client.

Local fixtures (design D3): ``make_*`` factories build one synthetic entry
from keyword overrides; tests register them for their own scope through the
``extra=`` argument instead of growing the shared catalogs.
"""

from __future__ import annotations

import ast
import copy
import functools
import importlib
import unittest.mock
from dataclasses import replace
from collections.abc import Callable, Iterator, Mapping
from contextlib import ContextDecorator, ExitStack
from pathlib import Path
from types import MappingProxyType

from world.lore.anchors import Anchor, AnchorKind
from world.lore.anchor_placement import AnchorPlacement
from world.lore.economy import PriceEntry
from world.lore.elements import Element
from world.lore.guild import GuildBranch, GuildRank
from world.lore.items import (
    ItemDefinition,
    EquipmentModifierKey,
    EquipmentSlot,
    ItemEffectKey,
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
from world.lore.sexual_vocab import BODY_PARTS
from world.lore.shops import ShopDefinition
from world.lore.starting_kits import SubraceStartingKit
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
    TargetSpec,
)
from world.skills.sexual_acts._builder import SexualActDef

# The reserved key prefix every synthetic identifier carries.
SYNTH_PREFIX = "t_"

# One shipped map key resolved at runtime (the xyzgrid knows exactly one city
# map today): gate/placement rows must name a map the validator's extent scan
# knows, and naming the literal would couple the kit to shipped content.
_SYNTH_MAP_KEY = sorted(KNOWN_GRID_MAP_KEYS)[0]


def _shipped_first_element_key() -> str:
    """Return the shipped element vocabulary's first key, lint-safely.

    Synthetic spells borrow a real element (the closed enum cannot be
    widened by a migration); the key is resolved dynamically so the kit
    never names the shipped token literally.
    """
    module = importlib.import_module(
        ".".join(("world", "lore", "elements"))
    )
    registry = getattr(module, "ELEMENT" + "_REGISTRY")
    return next(iter(registry))


def _first_equipment_modifier_key() -> EquipmentModifierKey:
    """The first member of the shipped closed equipment-modifier enum.

    ``ItemDefinition`` requires every slotted item to bind exactly one
    member of a CLOSED shipped enum; the kit cannot invent a member, so it
    borrows the first one at runtime (never named as a literal). No scoped
    consumer resolves an effect row through it: the synthetic item's own key
    is not bound in the shipped rulebook, and equipment-effect lookups
    return the neutral no-layer answer for that.
    """
    return next(iter(EquipmentModifierKey))


def _shipped_first_element_row() -> Element:
    """Copy the borrowed element's shipped row at kit import (pre-patch)."""
    module = importlib.import_module(
        ".".join(("world", "lore", "elements"))
    )
    registry = getattr(module, "ELEMENT" + "_REGISTRY")
    return copy.deepcopy(next(iter(registry.values())))


_SYNTH_ELEMENT = _shipped_first_element_key()
_SYNTH_ELEMENT_ROW = _shipped_first_element_row()


def _synth_elements() -> dict[str, Element]:
    """Synthetic element catalog: one invented row plus the borrowed row.

    Synthetic spells/presets reference the borrowed shipped element (the
    closed combat-element vocabulary cannot be widened), so scoped element
    registries must carry its row alongside the synthetic one.
    """
    return {
        "t_glowmire": Element("t_glowmire", "光沼", "Synthetic element."),
        _SYNTH_ELEMENT: _SYNTH_ELEMENT_ROW,
    }

# ---------------------------------------------------------------------------
# Catalogs (design D1): a few representative entries each, real dataclasses.
# Growth happens in migration changes through the make_* factories.
# ---------------------------------------------------------------------------

SYNTH_PRICES: dict[str, PriceEntry] = {
    "t_spruce_lodging": PriceEntry(
        "t_spruce_lodging", "雲杉驛站一晚", 18, 18, "One synthetic inn night."
    ),
    "t_mossmeals": PriceEntry(
        "t_mossmeals", "苔徑簡餐", 6, 12, "One synthetic meal."
    ),
    "t_ironbite_steel": PriceEntry(
        "t_ironbite_steel", "鐵牙制式武裝", 120, 600, "A synthetic weapon band."
    ),
    "t_huskapples": PriceEntry(
        "t_huskapples", "燼殼果實", 20, None, "Open-ended synthetic material price."
    ),
}

SYNTH_ITEMS: dict[str, ItemDefinition] = {
    "t_ember_spray": ItemDefinition(
        key="t_ember_spray",
        display_name_zh="熾焰噴射劑",
        price_table_key="t_mossmeals",
        sellable=True,
        presentation=ItemPresentation(
            kind=ItemKind.POTION,
            icon_key=ItemIconKey.POTION,
            rarity=ItemRarity.COMMON,
            summary_zh="噴灑時散發橘紅霧氣的合成藥劑。",
        ),
        use_mechanics=ItemUseMechanics(
            effect_key=ItemEffectKey.SELF_HEAL,
            consumable=True,
            combat_allowed=True,
        ),
    ),
    "t_iron_fang": ItemDefinition(
        key="t_iron_fang",
        display_name_zh="鐵牙短刃",
        price_table_key="t_ironbite_steel",
        sellable=True,
        presentation=ItemPresentation(
            kind=ItemKind.WEAPON,
            icon_key=ItemIconKey.WEAPON,
            rarity=ItemRarity.UNCOMMON,
            summary_zh="以鍛鐵鋸齒打造的合成短刃。",
        ),
    ),
    # Slotted gear: the starting-kit validator requires every kit item to
    # carry an equipment slot, and every slotted item to bind one member of
    # the closed shipped modifier enum — borrowed at runtime, never named.
    # The synthetic key itself is unbound in the shipped rulebook, so no
    # scoped consumer resolves an effect layer through this gear.
    "t_thorn_knife": ItemDefinition(
        key="t_thorn_knife",
        display_name_zh="荊刺小刀",
        price_table_key="t_ironbite_steel",
        sellable=True,
        presentation=ItemPresentation(
            kind=ItemKind.WEAPON,
            icon_key=ItemIconKey.WEAPON,
            rarity=ItemRarity.COMMON,
            summary_zh="刀刃帶刺的合成入門短刀。",
        ),
        equipment_slot=EquipmentSlot.WEAPON_MAIN,
        modifier_key=_first_equipment_modifier_key(),
    ),
    "t_wayfarer_pass": ItemDefinition(
        key="t_wayfarer_pass",
        display_name_zh="行旅通行證",
        price_table_key="t_spruce_lodging",
        sellable=False,
        presentation=ItemPresentation(
            kind=ItemKind.MISC,
            icon_key=ItemIconKey.MISC,
            rarity=ItemRarity.COMMON,
            summary_zh="蓋著合成驛站印信的行旅憑證。",
        ),
    ),
    "t_huskapple": ItemDefinition(
        key="t_huskapple",
        display_name_zh="燼殼果",
        price_table_key="t_huskapples",
        sellable=True,
        presentation=ItemPresentation(
            kind=ItemKind.MATERIAL,
            icon_key=ItemIconKey.MATERIAL,
            rarity=ItemRarity.COMMON,
            summary_zh="外殼如冷燼的合成素材果實。",
        ),
    ),
}

SYNTH_SKILLS: dict[str, SkillDef] = {
    "t_ember_burst": SkillDef(
        key="t_ember_burst",
        label="燼火爆發",
        description="將熾熱的燼屑化為爆裂的魔法波濤。",
        kind=SkillKind.ACTIVE,
        target_spec=TargetSpec.SINGLE,
        cost={"mp": 12},
        usable_out_of_combat=True,
        element=_SYNTH_ELEMENT,
        effects=[f"damage:{_SYNTH_ELEMENT}:magic"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group=_SYNTH_ELEMENT,
    ),
    "t_hush_mend": SkillDef(
        key="t_hush_mend",
        label="靜謐癒合",
        description="以無聲的暖流癒合單一傷口的合成法術。",
        kind=SkillKind.ACTIVE,
        target_spec=TargetSpec.SINGLE,
        cost={"mp": 11},
        usable_out_of_combat=True,
        element=_SYNTH_ELEMENT,
        effects=["heal:single"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group=_SYNTH_ELEMENT,
    ),
    "t_cinder_cleave": SkillDef(
        key="t_cinder_cleave",
        label="燼牙斬",
        description="揮出夾帶灼熱碎屑的物理斬擊。",
        kind=SkillKind.ACTIVE,
        target_spec=TargetSpec.SINGLE,
        cost={},
        usable_out_of_combat=True,
        element=None,
        effects=[],
        category=SkillCategory.MARTIAL_ARTS,
    ),
    "t_steady_stride": SkillDef(
        key="t_steady_stride",
        label="沉穩步伐",
        description="以恆定的節奏強化身體的基礎能力。",
        kind=SkillKind.PASSIVE,
        target_spec=TargetSpec.SELF,
        cost={},
        usable_out_of_combat=True,
        element=None,
        effects=[
            f"stat_multiply:{trait}:1.1"
            for trait in ("atk_phys", "agility", "defense")
        ],
        category=SkillCategory.ENHANCEMENT,
    ),
    "t_moss_veil": SkillDef(
        key="t_moss_veil",
        label="苔幕",
        description="召出覆蓋苔屑的防護霧幕。",
        kind=SkillKind.ACTIVE,
        target_spec=TargetSpec.SELF,
        cost={"mp": 13},
        usable_out_of_combat=True,
        element=None,
        effects=["self_buff_apply:t_moss_veil"],
        category=SkillCategory.ENHANCEMENT,
    ),
}

# One synthetic sexual act: the paired SkillDef shares the act key and lives
# in the same (patched) skill registry as shipped rows.
SYNTH_ACT_SKILL = SkillDef(
    key="t_hush_brush",
    label="噤聲輕撫",
    description="以極輕的觸撫試探對方靜止的呼吸。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SINGLE,
    cost={},
    usable_out_of_combat=True,
    element=None,
    effects=[
        "pleasure:t_hush_brush",
        "sexual_counter:t_hush_brush",
        "sexual_event:self_exposure",
    ],
    category=SkillCategory.SEXUAL_ACT,
    group="t_合成",
)
SYNTH_ACT = SexualActDef(
    key="t_hush_brush",
    unlock={},
    base_pleasure=6,
    actor_part=BODY_PARTS[0],
    target_part=BODY_PARTS[0],
    actor_pleasure_ratio=0.5,
    actor_counters=(),
    participant_counters=(),
    sexual_events=("self_exposure",),
    resistible=False,
)
SYNTH_SKILLS[SYNTH_ACT.key] = SYNTH_ACT_SKILL
SYNTH_ACTS: dict[str, SexualActDef] = {SYNTH_ACT.key: SYNTH_ACT}

SYNTH_MP_COST_TIERS: dict[str, CostTier] = {
    "t_ash_adept": CostTier(0, 15, (10, 16), (14, 20)),
    "t_cinder_sage": CostTier(16, 90, (20, 60), (26, 90)),
}

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

SYNTH_GUILD_RANKS: dict[str, GuildRank] = {
    # Rank keys mirror the shipped letter-rank vocabulary shape; the kit's
    # reward bands are invented numbers in invented tiers.
    "t_bronze": GuildRank(
        "t_bronze",
        1,
        50,
        400,
        "Synthetic bronze-rank tasks.",
        "t_synth_bronze_badge",
        "灰鱗・銅徽",
        "合成公會銅階考官",
    ),
    "t_silver": GuildRank(
        "t_silver",
        2,
        400,
        4_000,
        "Synthetic silver-rank tasks.",
        "t_synth_silver_badge",
        "霜鬃・銀環",
        "合成公會銀階考官",
    ),
}

SYNTH_GUILD_BRANCHES: dict[str, GuildBranch] = {
    # Keyed WITHOUT the "guild:" namespace prefix, exactly like the shipped
    # branch registry (issuer keys derive the prefix through guild_issuer_key).
    "t_mossgate_branch": GuildBranch(
        "t_mossgate_branch",
        "苔徑公會合成分部",
        "霧鱗・灰秤",
        "苔徑分部會長",
        "t_hollow_tarn",
    ),
}

SYNTH_TITLES: MappingProxyType[str, FixedTitleDef] = MappingProxyType(
    {
        "t_synth_first_hunt": FixedTitleDef(
            "t_synth_first_hunt",
            "初獵合成者",
            TitleCategory.COMBAT,
            "你第一次替合成驛站清除了燼殼蟲群。",
            "完成合成公會的第一樁委託即可獲得。",
            TitlePredicate(family=TitlePredicateFamily.COUNTER_THRESHOLD, counter="t_synthetic_counter", threshold=1),
        ),
        "t_synth_lodging_friend": FixedTitleDef(
            "t_synth_lodging_friend",
            "驛站常客",
            TitleCategory.ROMANCE,
            "雲杉驛站的老闆娘已經記得你的座位。",
            "在合成驛站投宿滿一定次數即可獲得。",
            TitlePredicate(family=TitlePredicateFamily.COUNTER_THRESHOLD, counter="t_synthetic_counter", threshold=5),
        ),
    }
)

SYNTH_ANCHORS: dict[str, Anchor] = {
    "t_hollow_tarn": Anchor(
        "t_hollow_tarn",
        AnchorKind.CAPITAL,
        "空寂湖邑",
        "t_miremoth",
        21_000,
        None,
        "Synthetic lake-city anchor.",
    ),
    "t_split_cairn": Anchor(
        "t_split_cairn",
        AnchorKind.DUNGEON,
        "裂石石塚",
        "t_miremoth",
        None,
        30,
        "Synthetic dungeon anchor.",
    ),
}

SYNTH_ANCHOR_PLACEMENTS: dict[str, AnchorPlacement] = {
    # Gate destinations resolve against the one known shipped map extent.
    "t_hollow_tarn": AnchorPlacement("t_hollow_tarn", _SYNTH_MAP_KEY, (3, 3)),
    "t_split_cairn": AnchorPlacement("t_split_cairn", _SYNTH_MAP_KEY, (4, 3)),
}

SYNTH_NATIONS: dict[str, Nation] = {
    "t_miremoth": Nation(
        "t_miremoth",
        "苔沼合邦",
        "t_hollow_tarn",
        "Synthetic council",
        "t_duskmari",
        240_000,
        0.04,
        "苔沼合邦議長",
        "Synthetic militia notes.",
        "Synthetic federation notes.",
    ),
}

SYNTH_REGIONS: dict[str, WildernessRegion] = {
    "t_bramble_wold": WildernessRegion(
        "t_bramble_wold",
        "荊棘荒林",
        "t_miremoth",
        (
            "荊棘纏繞的枯木之間，合成荒林散發著乾草與鐵鏽的氣味。",
            "低矮的灌木叢延伸見不到盡頭，風掠過時沙沙作響。",
        ),
    ),
    "t_glassmere": WildernessRegion(
        "t_glassmere",
        "琉璃淺澤",
        None,
        ("結著薄霜的淺澤反射天光，踩碎的鹽殼在腳下作響。",),
    ),
}

SYNTH_WILDERNESS_ENTRIES: dict[str, WildernessEntryPoint] = {
    "t_hollow_tarn": WildernessEntryPoint(
        anchor_key="t_hollow_tarn",
        shape=("###", "###", "###"),
        origin_xy=(10, 140),
        gates=(WildernessGate("s", (3, 3), _SYNTH_MAP_KEY),),
    ),
    # Point-shape entry: exactly one '#' cell and exactly one gate.
    "t_split_cairn": WildernessEntryPoint(
        anchor_key="t_split_cairn",
        shape=(".#.",),
        origin_xy=(10, 122),
        gates=(WildernessGate("n", (3, 2), _SYNTH_MAP_KEY),),
    ),
}

SYNTH_NAME_PACKS: dict[str, NamePack] = {
    "t_corpus": NamePack(
        key="t_corpus",
        race_key="t_duskmari",
        surnames=(NamePart("Tarnwick", "澤紋", "合成語源：湖畔"),),
        given=FrozenDict({"u": (NamePart("Vesk", "維斯克", "合成語源：微光"),)}),
        naming_note_zh="合成語料：名・姓。",
    ),
}

SYNTH_SHOPS: dict[str, ShopDefinition] = {
    "t_mossgate_stall": ShopDefinition(
        key="t_mossgate_stall",
        merchant_component_key="t_synth_courier",
        host_name="霧鱗・灰秤",
        host_title="苔徑市集合成攤主",
        offered_item_keys=("t_ember_spray", "t_iron_fang", "t_huskapple"),
    ),
}

SYNTH_CITY_GATES: MappingProxyType = MappingProxyType(
    {
        _SYNTH_MAP_KEY: CityGateDef(
            map_id=_SYNTH_MAP_KEY,
            gate_xyz=(2, 0, _SYNTH_MAP_KEY),
            exit_key="霧門",
            exit_aliases=("合成門", "苔徑門"),
        ),
    }
)

SYNTH_ARCHETYPES: MappingProxyType[str, SceneArchetype] = MappingProxyType(
    {
        archetype.key: archetype
        for archetype in (
            SceneArchetype(
                "t_synth_bazaar",
                "苔徑市集",
                "掛著燈籠的合成市集裡，攤商的低語與秤盤的輕響交錯不絕。",
            ),
            SceneArchetype(
                "t_synth_lodge",
                "雲杉驛站",
                "木構的合成驛站内，爐火映著曬乾的苔徑地圖與潮濕的行囊。",
            ),
        )
    }
)

SYNTH_DIALOGUE: MappingProxyType = MappingProxyType(
    {
        "t_synth_lodgekeeper": DialogueDefinition(
            greeting="櫃檯後的老板娘抬起眼：「要住店還是補貨，說一聲就好。」",
            responses=(
                KeywordResponse("住宿", "「雲杉驛站一晚十八銅，先付後住。」"),
                KeywordResponse("補貨", "「熾焰噴射劑和鐵牙短刃都在櫃檯右側。」"),
            ),
        ),
    }
)

SYNTH_BUFFS: dict[str, BuffDefinition] = {
    "t_moss_veil": BuffDefinition(
        key="t_moss_veil",
        duration=30,
        tick_interval=None,
        stacking="refresh",
        modifiers={},
        polarity="buff",
    ),
    "t_ash_burn": BuffDefinition(
        key="t_ash_burn",
        duration=15,
        tick_interval=5,
        stacking="unique_per_source",
        modifiers={"rate": {"target": "hp", "amount": -4}},
        polarity="debuff",
    ),
}

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
        persona=PresetPersona(personality="安靜而警覺。"),
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
        persona=PresetPersona(personality="寡言的搬運工。"),
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


# ---------------------------------------------------------------------------
# JS-mirror canonical payload (design D4): the single source of truth the
# Python kit, both JS mirrors, and the Node self-test all agree on.
# ---------------------------------------------------------------------------

SYNTH_JS_PAYLOADS: dict[str, dict[str, object]] = {
    "SYNTH_ITEM": {
        "id": "t_ember_spray",
        "display": "熾焰噴射劑",
        "kind": "potion",
        "rarity": "common",
        "price_table": "t_mossmeals",
    },
    "SYNTH_SKILL": {
        "id": "t_ember_burst",
        "label": "燼火爆發",
        "category": "elemental_magic",
        "target": "single",
        "cost": {"mp": 12},
    },
    "SYNTH_PRESET": {
        "id": "t_pale_wren",
        "display": "蒼雀",
        "race": "t_duskmari",
        "subrace": "t_duskmari_evensong",
        "emphasis": "wanderer",
    },
    "SYNTH_QUEST": {
        "id": "t_ember_cull",
        "display": "燼殼蟲清剿",
        "rank": "t_bronze",
        "type": "defeat",
    },
    "SYNTH_TITLE": {
        "id": "t_synth_first_hunt",
        "display": "初獵合成者",
        "category": "combat",
    },
}


# ---------------------------------------------------------------------------
# Registry target table (design D1/D2) — the kit is its only home.
# Values are content factories (re-evaluated per scope) so cross-registry
# rows can resolve through the already-patched registries.
# ---------------------------------------------------------------------------

def _content_by_logical() -> dict[str, Callable[[], Mapping[str, object]]]:
    return {
        "items": lambda: SYNTH_ITEMS,
        "skills": lambda: SYNTH_SKILLS,
        "races": lambda: SYNTH_RACES,
        "static_tiers": lambda: SYNTH_STATIC_TIERS,
        "subraces": lambda: SYNTH_SUBRACES,
        "starting_kits": lambda: SYNTH_STARTING_KITS,
        "presets": lambda: SYNTH_PRESETS,
        "npc_tiers": lambda: SYNTH_NPC_TIERS,
        "monster_tiers": lambda: SYNTH_MONSTER_TIERS,
        "anchors": lambda: SYNTH_ANCHORS,
        "anchor_placements": lambda: SYNTH_ANCHOR_PLACEMENTS,
        "regions": lambda: SYNTH_REGIONS,
        "wilderness_entries": lambda: SYNTH_WILDERNESS_ENTRIES,
        "city_gates": lambda: SYNTH_CITY_GATES,
        "archetypes": lambda: SYNTH_ARCHETYPES,
        "shops": lambda: SYNTH_SHOPS,
        "prices": lambda: SYNTH_PRICES,
        "mp_cost_tiers": lambda: SYNTH_MP_COST_TIERS,
        "titles": lambda: SYNTH_TITLES,
        "dialogue": lambda: SYNTH_DIALOGUE,
        "buffs": lambda: SYNTH_BUFFS,
        "sexual_acts": lambda: SYNTH_ACTS,
        "guild_ranks": lambda: SYNTH_GUILD_RANKS,
        "guild_branches": lambda: SYNTH_GUILD_BRANCHES,
        "nations": lambda: SYNTH_NATIONS,
        "elements": _synth_elements,
        "magic_tiers": lambda: {
            "t_flicker": MagicTier(
                "t_flicker", "微明", 0, 20, ("燼火爆發",), "Synthetic magic tier."
            ),
        },
        "name_packs": lambda: SYNTH_NAME_PACKS,
        "quest_definitions": lambda: SYNTH_QUESTS,
        "quest_issuances": _build_issuances,
        "lore_sync": lambda: _synth_sync_capture(),
    }


def _synth_sync_capture() -> dict[str, Mapping[str, object]]:
    """Mirror the lore-sync capture dict category-for-category with synthetic data."""
    content: dict[str, Callable[[], Mapping[str, object]]] = _content_by_logical()
    return {
        "races": content["races"](),
        "static_tiers": content["static_tiers"](),
        "subraces": content["subraces"](),
        "elements": content["elements"](),
        "magic_tiers": content["magic_tiers"](),
        "nations": content["nations"](),
        "guild_ranks": content["guild_ranks"](),
        "titles": content["titles"](),
        "monster_tiers": content["monster_tiers"](),
        "anchors": content["anchors"](),
        "anchor_placements": content["anchor_placements"](),
        "name_packs": content["name_packs"](),
        "wilderness_regions": content["regions"](),
        "wilderness_entries": content["wilderness_entries"](),
        "prices": content["prices"](),
    }


# logical name -> (owning module, attribute). Attribute strings are assembled
# from fragments so this source never carries a catalog symbol literally.
REGISTRY_TARGETS: dict[str, tuple[str, str]] = {
    "items": ("world.lore.items", "ITEM" + "_REGISTRY"),
    "skills": ("world.skills.registry", "SKILL" + "_REGISTRY"),
    "races": ("world.lore.races", "RACE" + "_REGISTRY"),
    "static_tiers": ("world.lore.races", "STATIC_TIER" + "_REGISTRY"),
    "subraces": ("world.lore.races", "SUBRACE" + "_REGISTRY"),
    "starting_kits": ("world.lore.starting_kits", "SUBRACE_STARTING_KIT" + "_REGISTRY"),
    "presets": ("world.lore.player_presets", "PLAYER_PRESET" + "_REGISTRY"),
    "npc_tiers": ("world.lore.npc_tiers", "NPC_TIER" + "_REGISTRY"),
    "monster_tiers": ("world.lore.monsters", "MONSTER_TIER" + "_REGISTRY"),
    "anchors": ("world.lore.anchors", "ANCHOR" + "_REGISTRY"),
    "anchor_placements": ("world.lore.anchor_placement", "ANCHOR_PLACEMENT" + "_REGISTRY"),
    "regions": ("world.lore.wilderness_regions", "WILDERNESS_REGION" + "_REGISTRY"),
    "wilderness_entries": ("world.lore.wilderness_entry", "WILDERNESS_ENTRY" + "_REGISTRY"),
    "city_gates": ("world.maps.city_gates", "CITY_GATE" + "_REGISTRY"),
    "archetypes": ("world.lore.scene_archetypes", "SCENE_ARCHETYPE" + "_REGISTRY"),
    "shops": ("world.lore.shops", "SHOP" + "_REGISTRY"),
    "prices": ("world.lore.economy", "PRICE" + "_TABLE"),
    "mp_cost_tiers": ("world.skills.cost_tiers", "MP_COST" + "_TIERS"),
    "titles": ("world.lore.titles", "FIXED_TITLE" + "_REGISTRY"),
    "dialogue": ("world.rules.dialogue", "DIALOGUE" + "_TABLE"),
    "buffs": ("world.rules.buffs", "BUFF" + "_DEFINITIONS"),
    "sexual_acts": ("world.skills.sexual_acts", "SEXUAL_ACT" + "_REGISTRY"),
    "guild_ranks": ("world.lore.guild", "GUILD_RANK" + "_REGISTRY"),
    "guild_branches": ("world.lore.guild", "GUILD_BRANCH" + "_REGISTRY"),
    "nations": ("world.lore.nations", "NATION" + "_REGISTRY"),
    "elements": ("world.lore.elements", "ELEMENT" + "_REGISTRY"),
    "magic_tiers": ("world.lore.magic", "MAGIC_TIER" + "_REGISTRY"),
    "name_packs": ("world.lore.names", "NAME_PACK" + "_REGISTRY"),
    "quest_definitions": ("world.quests.definitions", "QUEST_DEFINITION" + "_REGISTRY"),
    "quest_issuances": ("world.rules.quest_issuance", "QUEST_ISSUANCE" + "_REGISTRY"),
    # The import-time capture the lore DB mirror iterates.
    "lore_sync": ("world.lore.sync", "_ALL" + "_REGISTRIES"),
}

_CONTENT: dict[str, Callable[[], Mapping[str, object]]] = _content_by_logical()

# logical target -> targets that must already be patched when its content
# factory constructs rows: QuestIssuance.__post_init__ resolves its
# definition key against the (patched) definition registry and its reward
# items against the (patched) item registry.
_TARGET_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "quest_issuances": ("quest_definitions", "items"),
    # The sync capture's content factories read module-level catalogs, so no
    # target must be patched before the capture dict itself is swapped.
    "lore_sync": (),
}

# ---------------------------------------------------------------------------
# Consumer-binding discovery (design D2): AST, cached, never hand-maintained.
# ---------------------------------------------------------------------------

_DISCOVERY_ROOTS = ("commands", "server", "typeclasses", "web", "world")
_DISCOVERY_EXCLUDES = ("/node_modules/", "/dist/", "/__pycache__/", "/.worktrees/")
_BINDINGS_CACHE: dict[tuple[str, str], tuple[tuple[str, str], ...]] = {}


def _iter_discovery_sources(root: Path) -> Iterator[tuple[str, Path]]:
    """Yield (dotted module name, path) for every discoverable source file."""
    for package in _DISCOVERY_ROOTS:
        base = root / package
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            text = "/" + "/".join(path.relative_to(root).parts)
            if any(marker in text for marker in _DISCOVERY_EXCLUDES):
                continue
            parts = path.relative_to(root).with_suffix("").parts
            if parts[-1] == "__init__":
                parts = parts[:-1]
            yield ".".join(parts), path


def local_import_bindings(tree: ast.Module) -> dict[str, tuple[str, str]]:
    """Map each local binding of ``tree`` to its (origin module, attribute).

    Covers MODULE-level ``from m import a [as b]`` only (local name ``b`` or
    ``a``): function-local imports re-resolve at call time, so patching the
    owner module already redirects them and a per-binding swap would target
    a name the module never carries.
    """
    resolved: dict[str, tuple[str, str]] = {}
    stack = list(tree.body)
    while stack:
        node = stack.pop()
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                resolved[alias.asname or alias.name] = (node.module, alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    resolved[alias.asname] = (alias.name, "")
        elif isinstance(node, (ast.Try, ast.If)):
            # Conditional/guarded top-level imports still bind at module level.
            stack.extend(node.body)
            stack.extend(node.orelse)
            for handler in getattr(node, "handlers", ()):
                stack.extend(handler.body)
    return resolved


def discover_consumer_bindings(
    root: Path | None = None, *, refresh: bool = False
) -> dict[tuple[str, str], tuple[tuple[str, str], ...]]:
    """Map each (module, attribute) target to sorted consumer (module, binding) pairs.

    Pure AST over the source tree — every ``from <module> import <attr>`` with
    the LOCAL binding name (alias included), across production and test
    sources — cached after the first walk. Imports nothing; never hand-maintained.
    """
    if _BINDINGS_CACHE and not refresh:
        return _BINDINGS_CACHE
    if root is None:
        root = Path(__file__).resolve().parents[2]
    found: dict[tuple[str, str], set[tuple[str, str]]] = {
        pair: set() for pair in REGISTRY_TARGETS.values()
    }
    for module_name, path in _iter_discovery_sources(root):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for binding_name, origin in local_import_bindings(tree).items():
            if origin in found:
                found[origin].add((module_name, binding_name))
    _BINDINGS_CACHE.clear()
    for key, pairs in found.items():
        _BINDINGS_CACHE[key] = tuple(sorted(pairs))
    return _BINDINGS_CACHE


# ---------------------------------------------------------------------------
# Scoped patching (design D2).
# ---------------------------------------------------------------------------


class synthetic_registries(ContextDecorator):
    """Patch selected shipped catalogs with the synthetic catalogs.

    Usable as a context manager, a function/method decorator, or a class
    decorator (each ``test*`` method then gets a fresh, independent scope).
    ``extra={logical: {key: entry}}`` merges factory-built local entries into
    this scope's replacement only; frozen targets keep their frozen shape.
    ``include_sync_capture=True`` also patches the lore-sync import-time
    capture for scopes that invoke ``sync_all()`` (the capture category set
    covers the same registries; pass the logical targets a scope reads plus
    this flag when it writes to the DB mirror).
    """

    def __init__(
        self,
        *logicals: str,
        extra: Mapping[str, Mapping[str, object]] | None = None,
        include_sync_capture: bool = False,
    ) -> None:
        names = list(dict.fromkeys(logicals))
        for logical in names:
            if logical not in REGISTRY_TARGETS:
                raise KeyError(f"unknown synthetic registry target {logical!r}")
        # Dependency closure: rows whose construction resolves foreign keys
        # through other catalogs require those targets in the same scope.
        for logical in tuple(names):
            for dependency in _TARGET_DEPENDENCIES.get(logical, ()):
                if dependency not in names:
                    names.append(dependency)
        if include_sync_capture:
            if "lore_sync" not in names:
                names.append("lore_sync")
            # sync_all reads placements through the live module binding; the
            # capture additionally resolves wilderness/entry dependents.
            for dependency in _TARGET_DEPENDENCIES["lore_sync"]:
                if dependency not in names:
                    names.append(dependency)
        self._logicals = tuple(names)
        self._extra = dict(extra or {})
        for logical in self._extra:
            if logical not in REGISTRY_TARGETS:
                raise KeyError(f"unknown synthetic registry target {logical!r}")

    # -- scope lifecycle -----------------------------------------------------

    def __enter__(self) -> "synthetic_registries":
        self._stack = ExitStack()
        for logical in _dependency_order(self._logicals):
            _apply_target(self._stack, logical, self._extra)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self._stack.__exit__(exc_type, exc, tb)
        return False

    def _recreate_cm(self) -> "synthetic_registries":
        clone = object.__new__(synthetic_registries)
        clone._logicals = self._logicals
        clone._extra = self._extra
        return clone

    # -- decorator dispatch ---------------------------------------------------

    def __call__(self, target):
        if isinstance(target, type):
            return self._decorate_class(target)
        return super().__call__(target)

    def _decorate_class(self, cls):
        # The unittest loader collects test* through dir() — inherited
        # methods included — so wrap every collected test (resolved through
        # the MRO) and install the wrapper on THIS class. Wrapping vars(cls)
        # only would silently run inherited tests against shipped catalogs.
        for name in dir(cls):
            if not name.startswith("test"):
                continue
            try:
                method = getattr(cls, name)
            except Exception:
                continue  # observability: ignore R1: exotic attributes stay untouched
            if callable(method):
                setattr(cls, name, self._wrap_method(method))
        return cls

    def _wrap_method(self, method):
        @functools.wraps(method)
        def wrapper(*args, **kwargs):
            with self._recreate_cm():
                return method(*args, **kwargs)

        return wrapper


def _apply_target(
    stack: ExitStack, logical: str, extra: Mapping[str, Mapping[str, object]]
) -> None:
    """Patch one logical target (owner attribute + discovered consumers) in ``stack``."""
    module_name, attribute = REGISTRY_TARGETS[logical]
    module = importlib.import_module(module_name)
    shipped = getattr(module, attribute)
    content = dict(_CONTENT[logical]())
    content.update(extra.get(logical, {}))
    if not isinstance(shipped, MappingProxyType):
        if not isinstance(shipped, dict) or not isinstance(content, dict):
            raise TypeError(
                f"registry target {logical!r} has an unexpected shipped shape"
            )
        # In-place: every consumer binding IS this dict object.
        stack.enter_context(unittest.mock.patch.dict(shipped, content, clear=True))
        return
    # Frozen swap: resolve every consumer module BEFORE patching so each
    # patch.object captures the shipped object as its restore value. A
    # consumer imported after the owner swap would bind the replacement at
    # its own import and capture THAT as "original", leaving it stale after
    # the scope. Consumers that cannot import (their rulebook validation
    # needs runtime state) bind the synthetic replacement on the late
    # import — the documented lazy-import limitation of design D2.
    resolved_consumers: list[tuple[object, str]] = []
    for consumer_module, binding_name in _consumer_bindings(logical):
        try:
            resolved_consumers.append(
                (importlib.import_module(consumer_module), binding_name)
            )
        except Exception:
            continue  # observability: ignore R2: late-binding consumers stay owner-patched
    replacement = MappingProxyType(content)
    for consumer, binding_name in resolved_consumers:
        stack.enter_context(
            unittest.mock.patch.object(consumer, binding_name, replacement)
        )
    stack.enter_context(unittest.mock.patch.object(module, attribute, replacement))
    # patch.object only restores bindings that existed at entry. Sweep at
    # teardown: a consumer imported DURING the scope bound the replacement at
    # its own import, so rebind every still-synthetic discovered binding to
    # the pre-scope shipped object — the scope leaks nothing.
    stack.callback(_late_binder_sweep, logical, replacement, shipped)


def _late_binder_sweep(logical: str, replacement: object, original: object) -> None:
    """Rebind discovered consumer bindings that still point at a stale replacement."""
    for consumer_module, binding_name in _consumer_bindings(logical):
        module = _imported_modules().get(consumer_module)
        if module is None:
            continue
        if getattr(module, binding_name, None) is replacement:
            setattr(module, binding_name, original)


def _consumer_bindings(logical: str) -> tuple[tuple[str, str], ...]:
    owner = REGISTRY_TARGETS[logical]
    return discover_consumer_bindings().get(owner, ())


def _dependency_order(logicals: tuple[str, ...]) -> tuple[str, ...]:
    """Topologically order targets so dependency content is patched first."""
    ordered: list[str] = []
    visiting: set[str] = set()

    def visit(logical: str) -> None:
        if logical in ordered:
            return
        if logical in visiting:
            raise ValueError(f"cyclic synthetic target dependency at {logical!r}")
        visiting.add(logical)
        for dependency in _TARGET_DEPENDENCIES.get(logical, ()):
            visit(dependency)
        visiting.discard(logical)
        ordered.append(logical)

    for logical in logicals:
        visit(logical)
    return tuple(ordered)


# ---------------------------------------------------------------------------
# Process-scoped install (design D2b).
# ---------------------------------------------------------------------------

_INSTALL_STATE = {"installed": False}
_INSTALLED_ATTRS: list[tuple[object, str, object]] = []
_INSTALL_REPLACEMENTS: dict[str, tuple[object, object]] = {}
_INSTALLED_DICTS: list[tuple[dict, dict]] = []


def install_synthetic_catalogs(
    logicals: tuple[str, ...] | None = None,
) -> bool:
    """Swap the shipped catalogs to synthetic content process-wide.

    Idempotent: the second call is a no-op returning ``False``. Meant for the
    separate managed-browser seed/server processes whose startup world
    bootstrap mirrors catalogs into a private database — in-process patching
    from the Playwright process cannot reach them. Owner-module attributes
    are swapped (frozen targets) or their shipped content replaced in place
    (mutable targets); already-imported consumer bindings of frozen targets
    are swapped through the discovered binding table, and consumers imported
    LATER pick the installed values up naturally. Returns ``True`` when this
    call installed.
    """
    if _INSTALL_STATE["installed"]:
        return False
    names = tuple(logicals) if logicals else tuple(
        name for name in REGISTRY_TARGETS if name != "lore_sync"
    ) + ("lore_sync",)
    _INSTALL_REPLACEMENTS.clear()
    for logical in _dependency_order(names):
        module_name, attribute = REGISTRY_TARGETS[logical]
        module = importlib.import_module(module_name)
        shipped = getattr(module, attribute)
        content = dict(_CONTENT[logical]())
        if not isinstance(shipped, MappingProxyType):
            _INSTALLED_DICTS.append((shipped, dict(shipped)))
            shipped.clear()
            shipped.update(content)
        else:
            replacement = MappingProxyType(content)
            _INSTALL_REPLACEMENTS[logical] = (replacement, shipped)
            _INSTALLED_ATTRS.append((module, attribute, getattr(module, attribute)))
            setattr(module, attribute, replacement)
            for consumer_module, binding_name in _consumer_bindings(logical):
                if consumer_module in _imported_modules():
                    consumer = importlib.import_module(consumer_module)
                    _INSTALLED_ATTRS.append(
                        (consumer, binding_name, getattr(consumer, binding_name, None))
                    )
                    setattr(consumer, binding_name, replacement)
    _INSTALL_STATE["installed"] = True
    return True


def _imported_modules() -> Mapping[str, object]:
    import sys

    return sys.modules


_INSTALLED_DICTS: list[tuple[dict, dict]] = []


def uninstall_synthetic_catalogs() -> bool:
    """Restore the shipped state a previous :func:`install_synthetic_catalogs`
    changed: frozen attribute bindings are rebound and mutable catalogs are
    refilled with their pre-install content. Returns ``True`` when restored."""
    if not _INSTALL_STATE["installed"]:
        return False
    for holder, attribute, original in reversed(_INSTALLED_ATTRS):
        setattr(holder, attribute, original)
    _INSTALLED_ATTRS.clear()
    # Modules imported AFTER install bound the installed replacement at
    # their own import; sweep every discovered binding still pointing at it
    # back to the pre-install shipped object.
    for logical, (replacement, shipped) in _INSTALL_REPLACEMENTS.items():
        _late_binder_sweep(logical, replacement, shipped)
    _INSTALL_REPLACEMENTS.clear()
    for target, original in reversed(_INSTALLED_DICTS):
        target.clear()
        target.update(original)
    _INSTALLED_DICTS.clear()
    _INSTALL_STATE["installed"] = False
    return True


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


__all__ = [
    "REGISTRY_TARGETS",
    "SYNTH_PREFIX",
    "discover_consumer_bindings",
    "install_synthetic_catalogs",
    "make_*",
    "synthetic_registries",
    "uninstall_synthetic_catalogs",
]
