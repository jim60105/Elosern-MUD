"""World-domain catalogs: guilds, titles, geography, economy identities, dialogue, and buffs.
"""

from __future__ import annotations

from types import MappingProxyType
from world.lore.anchors import Anchor, AnchorKind
from world.lore.anchor_placement import AnchorPlacement
from world.lore.guild import GuildBranch, GuildRank
from world.lore.names import FrozenDict, NamePack, NamePart
from world.lore.nations import Nation
from world.lore.scene_archetypes import SceneArchetype
from world.lore.settlements.assortments import AssortmentDefinition
from world.lore.settlements.places import PlaceDefinition, PlaceKind
from world.lore.settlements.settlements import (
    SettlementArchetype,
    SettlementDefinition,
)
from world.lore.settlements.shops import ShopDefinition
from world.lore.titles import (
    FixedTitleDef,
    TitleCategory,
    TitlePredicate,
    TitlePredicateFamily,
)
from world.lore.wilderness_entry import WildernessEntryPoint, WildernessGate
from world.lore.wilderness_regions import WildernessRegion
from world.maps.city_gates import CityGateDef
from world.rules.buffs import BuffDefinition
from world.rules.dialogue import DialogueDefinition, KeywordResponse

from world.tests.synthetic_data.vocab import _SYNTH_GATE_XY, _SYNTH_MAP_KEY

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
        # A deliberately hard row: the browser title-codex fixture banks the
        # two easy rows and keeps this one unbanked, so the codex still
        # renders a locked row under the synthetic install.
        "t_synth_deep_walker": FixedTitleDef(
            "t_synth_deep_walker",
            "深霧行者",
            TitleCategory.EXPLORE,
            "苔徑深處的霧只為走得夠久的人讓路。",
            "在合成荒野深處留下足夠多的到訪紀錄即可獲得。",
            TitlePredicate(family=TitlePredicateFamily.COUNTER_THRESHOLD, counter="t_synthetic_counter", threshold=99),
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

SYNTH_ASSORTMENTS: dict[str, AssortmentDefinition] = {
    "t_mossgate_goods": AssortmentDefinition(
        key="t_mossgate_goods",
        display_name_zh="苔徑市集合成商品",
        item_keys=("t_ember_spray", "t_iron_fang", "t_huskapple"),
    ),
}

SYNTH_SETTLEMENTS: dict[str, SettlementDefinition] = {
    "t_mossgate": SettlementDefinition(
        key="t_mossgate",
        archetype=SettlementArchetype.TOWN,
        zcoord="t_mossgate",
    ),
}

SYNTH_PLACES: dict[str, PlaceDefinition] = {
    "t_mossgate_guild_hall": PlaceDefinition(
        key="t_mossgate_guild_hall",
        settlement_key="t_mossgate",
        kind=PlaceKind.GUILD_HALL,
        room_name_zh="合成苔徑公會廳",
        room_desc_zh="A synthetic guild hall for the mossgate stand-in world.",
        exterior_xy=(0, 0),
        doorway_key_zh="合成公會廳入口",
        doorway_aliases=("synthetic hall",),
        host_name="合成苔徑會長",
        host_title="合成苔徑分會館長",
        host_race="human",
        host_subrace=None,
        host_sex="other",
        profession="t_mossgate_staff",
        service_id="t_mossgate_guild_master",
        assortment_keys=(),
        authored_kwargs=(
            ("branch_key", "t_mossgate_branch"),
            ("dialogue_key", "t_mossgate_staff"),
        ),
    ),
    "t_mossgate_store": PlaceDefinition(
        key="t_mossgate_store",
        settlement_key="t_mossgate",
        kind=PlaceKind.GENERAL_STORE,
        room_name_zh="合成苔徑雜貨店",
        room_desc_zh="A synthetic general store for the mossgate stand-in world.",
        exterior_xy=(1, 1),
        doorway_key_zh="合成雜貨店入口",
        doorway_aliases=("synthetic store",),
        host_name="合成苔徑店主",
        host_title="合成苔徑雜貨店主",
        host_race="human",
        host_subrace=None,
        host_sex="other",
        profession="t_mossgate_merchant",
        service_id="t_mossgate_merchant",
        assortment_keys=("t_mossgate_goods",),
        authored_kwargs=(("shop_key", "t_mossgate_stall"),),
    ),
    # A host-less place (hostless-places): every host field keeps its default,
    # so this row is the kit fixture for "a place that simply exists" — the
    # validation-side probe downstream changes build on. Its exterior has no
    # synthetic grid map (the t_ settlement is validation-only space), so a
    # database-backed sync probe clones a live resolvable row instead.
    "t_mossgate_plaza": PlaceDefinition(
        key="t_mossgate_plaza",
        settlement_key="t_mossgate",
        kind=PlaceKind.HOME,
        room_name_zh="合成苔徑村中廣場",
        room_desc_zh="A synthetic gathering clearing: a place that exists with no host.",
        exterior_xy=(2, 2),
        doorway_key_zh="合成廣場入口",
        doorway_aliases=("synthetic plaza",),
    ),
}

SYNTH_SHOPS: dict[str, ShopDefinition] = {
    "t_mossgate_stall": ShopDefinition(
        key="t_mossgate_stall",
        host_name="霧鱗・灰秤",
        host_title="苔徑市集合成攤主",
        assortment_keys=("t_mossgate_goods",),
    ),
}

SYNTH_CITY_GATES: MappingProxyType = MappingProxyType(
    {
        _SYNTH_MAP_KEY: CityGateDef(
            map_id=_SYNTH_MAP_KEY,
            # The borrowed shipped gate cell (vocab resolver): the kit row
            # must land on a cell the shipped map data actually contains,
            # or the registry-probing fixtures resolve no room and silently
            # no-op.
            gate_xyz=(_SYNTH_GATE_XY[0], _SYNTH_GATE_XY[1], _SYNTH_MAP_KEY),
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
        # Mirrors the shipped damaging-buff cadence (10s per tick): the
        # inventory-actions fixture heals a 20-point gap with a 6-second
        # item-use clock advance, and a sub-6s tick interval would drain the
        # fresh heal inside the use's own settlement — the hp_full story
        # would never commit.
        tick_interval=10,
        stacking="unique_per_source",
        modifiers={"rate": {"target": "hp", "delta": -4}},
        polarity="debuff",
    ),
}
