"""World-domain catalogs: guilds, titles, geography, economy identities, dialogue, and buffs.
"""

from __future__ import annotations

from types import MappingProxyType
from elosern_map_core.references import interior_room_ref
from world.lore.anchors import Anchor, AnchorKind
from world.lore.dialogue.conditions import All, Carries, Exposure, RaceIs
from world.lore.dialogue.shape import AuthoredDialogue, AuthoredTopic, SceneVariant
from world.lore.scenes import Narration, Scene, Speech
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
    StarterEpithet,
    TitleCategory,
    TitlePredicate,
    TitlePredicateFamily,
)
from world.lore.wilderness_entry import WildernessEntryPoint, WildernessGate
from world.lore.wilderness_regions import WildernessRegion
from world.maps.city_gates import CityGateDef
from world.rules.buffs import BuffDefinition, PHYSIOLOGICAL_PROTECTION
from world.rules.fatigue import PROJECTION_BUFF_KEYS
from world.rules.dialogue import DialogueDefinition, KeywordResponse
from typeclasses.components import GuildStaff, Merchant
from world.lore.settlements.capability_declarations import capability, place_bound

from world.tests.synthetic_data.vocab import (
    _SYNTH_GATE_XY,
    _SYNTH_GATE_REF,
    _SYNTH_MAP_KEY,
    _SYNTH_SECOND_GATE_XY,
    _SYNTH_SECOND_GATE_REF,
)

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
    ),
    "t_silver": GuildRank(
        "t_silver",
        2,
        400,
        4_000,
        "Synthetic silver-rank tasks.",
        "t_synth_silver_badge",
    ),
}

SYNTH_GUILD_BRANCHES: dict[str, GuildBranch] = {
    # Keyed WITHOUT the "guild:" namespace prefix, exactly like the shipped
    # branch registry (issuer keys derive the prefix through guild_issuer_key).
    "t_mossgate_branch": GuildBranch(
        "t_mossgate_branch",
        "苔徑公會合成分部",
        "霧鱗‧灰秤",
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


#: The stand-in starter epithet every behavior test patches over the shipped
#: ``world.lore.titles.STARTER_EPITHET`` seam: the claim path banks whatever
#: declaration the seam holds, so tests assert this authored display/origin
#: instead of pinning the shipped spelling. Not a catalog mapping, so the
#: kit's catalog self-tests skip it; the kit file scan still proves its prose
#: never collides with a shipped token.
SYNTH_STARTER_EPITHET = StarterEpithet(
    "苔徑新旅",
    "你在合成公會完成第一次任務回報。",
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
    # Gate destinations borrow shipped node identities so they resolve.
    "t_hollow_tarn": AnchorPlacement("t_hollow_tarn", _SYNTH_GATE_REF),
    "t_split_cairn": AnchorPlacement("t_split_cairn", _SYNTH_SECOND_GATE_REF),
    # The stand-in settlement's coordinate space is declared by its own
    # placement, exactly like a shipped settlement's.
    "t_mossgate": AnchorPlacement("t_mossgate", _SYNTH_GATE_REF),
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
        9_600,
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
        origin_xy=(500, 500),
        # Gate cells are borrowed shipped grid cells: a synthetic gate must
        # name a cell the shipped map materializes, never a stale literal.
        gates=(WildernessGate("w", _SYNTH_SECOND_GATE_REF),),
    ),
    # Point-shape entry: exactly one '#' cell and exactly one gate.
    "t_split_cairn": WildernessEntryPoint(
        anchor_key="t_split_cairn",
        shape=(".#.",),
        origin_xy=(520, 520),
        gates=(WildernessGate("n", _SYNTH_GATE_REF),),
    ),
}

SYNTH_NAME_PACKS: dict[str, NamePack] = {
    "t_corpus": NamePack(
        key="t_corpus",
        race_key="t_duskmari",
        surnames=(NamePart("Tarnwick", "澤紋", "合成語源：湖畔"),),
        given=FrozenDict({"u": (NamePart("Vesk", "維斯克", "合成語源：微光"),)}),
        naming_note_zh="合成語料：名‧姓。",
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
    ),
}

SYNTH_PLACES: dict[str, PlaceDefinition] = {
    "t_mossgate_guild_hall": PlaceDefinition(
        key="t_mossgate_guild_hall",
        settlement_key="t_mossgate",
        kind=PlaceKind.GUILD_HALL,
        room=interior_room_ref("t_mossgate_guild_hall", "t_mossgate_guild_hall"),
        host_name="合成苔徑會長",
        host_race="human",
        host_subrace=None,
        host_sex="other",
        assortment_keys=(),
        components=(
            capability(
                GuildStaff.name,
                binding=place_bound("t_mossgate_guild_hall"),
                service_id="t_mossgate_guild_master",
                branch_key="t_mossgate_branch",
            ),
            capability(
                "scripted_dialogue",
                binding=place_bound("t_mossgate_guild_hall"),
                dialogue_key="t_mossgate_staff",
            ),
        ),
    ),
    "t_mossgate_store": PlaceDefinition(
        key="t_mossgate_store",
        settlement_key="t_mossgate",
        kind=PlaceKind.GENERAL_STORE,
        room=interior_room_ref("t_mossgate_store", "t_mossgate_store"),
        host_name="合成苔徑店主",
        host_race="human",
        host_subrace=None,
        host_sex="other",
        assortment_keys=("t_mossgate_goods",),
        components=(
            capability(
                Merchant.name,
                binding=place_bound("t_mossgate_store"),
                service_id="t_mossgate_merchant",
                shop_key="t_mossgate_stall",
            ),
        ),
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
        room=interior_room_ref("t_mossgate_plaza", "t_mossgate_plaza"),
    ),
}

SYNTH_SHOPS: dict[str, ShopDefinition] = {
    "t_mossgate_stall": ShopDefinition(
        key="t_mossgate_stall",
        host_name="霧鱗‧灰秤",
        assortment_keys=("t_mossgate_goods",),
    ),
}

SYNTH_CITY_GATES: MappingProxyType = MappingProxyType(
    {
        _SYNTH_MAP_KEY: CityGateDef(
            # The borrowed shipped gate identity (vocab resolver): the kit
            # row must land on a node the shipped map data actually contains,
            # or the registry-probing fixtures resolve no room and silently
            # no-op.
            gate=_SYNTH_GATE_REF,
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
                "木構的合成驛站內，爐火映著曬乾的苔徑地圖與潮濕的行囊。",
            ),
        )
    }
)

SYNTH_DIALOGUE: MappingProxyType = MappingProxyType(
    {
        "t_synth_lodgekeeper": DialogueDefinition(
            greeting="櫃檯後的老闆娘抬起眼：「要住店還是補貨，說一聲就好。」",
            responses=(
                KeywordResponse("住宿", "「雲杉驛站一晚十八銅，先付後住。」"),
                KeywordResponse("補貨", "「熾焰噴射劑和鐵牙短刃都在櫃檯右側。」"),
            ),
        ),
        # The authored-scene playback fixture (authored-dialogue-playback): one
        # complete static scene with actor speech, two consecutive host
        # lines, one host line long enough to span pages, and narration.
        "t_synth_storyteller": AuthoredDialogue(
            greeting="爐火邊的說書人放下杯子：「想聽故事就說一聲。」",
            topics=(
                AuthoredTopic(
                    topic_id="t_synth_storyteller.tale",
                    keyword="故事",
                    label="故事",
                    fallback=Scene(
                        scene_id="t_synth_storyteller.tale_scene",
                        revision="r1",
                        lines=(
                            Speech(speaker="actor", text="說個故事吧。"),
                            Speech(speaker="host", text="「好，就說雲杉驛站的冬天。」"),
                            Speech(speaker="host", text="「你可得聽到最後。」"),
                            Speech(speaker="host", text='「那年冬天，苔徑上的雪積得比門檻還高，驛站裡只剩一盞油燈。旅人們圍著爐火，一個接一個說起自己走過的路：有人說北岸的霧會吞掉腳印，有人說雲杉林深處有座無人看守的石橋，橋下的水從不結冰。我在櫃檯後聽了整整一夜，把每一段路都記在帳本的背面，直到天亮時才發現，那些故事拼起來，正好是一張從這裡通往山口的地圖。後來帳本被雨水泡爛了，地圖也只剩我記得的那一半。春天來的時候，有個年輕的獵人在門口停下，問我山口的路怎麼走。我把記得的那一半說給他聽，他點點頭，背起弓就往苔徑上去了。那之後我每年冬天都會在爐火邊等，想聽他回來說另一半的路，可是雪化了又積，積了又化，門口的腳印換了一批又一批，就是沒有他的。所以呀，如果你哪天走到山口，記得替我看看那座石橋還在不在。」'),
                            Narration(text="爐火劈啪一響，說書人的影子在牆上晃了晃。"),
                        ),
                    ),
                ),
            ),
        ),
        # The authored-dialogue physical-conditions fixture: two complete
        # topics whose variants are keyed on the acting body's race and its
        # canonical effective exposure. The possessed browser journey opts in
        # to this table, wears the kit's exposure-bias accessory and asserts a
        # qualified variant rather than the fallback; every other journey
        # keeps its own table and prose.
        "t_synth_conditioned": AuthoredDialogue(
            greeting="簾後的合成商人壓低聲音：「問吧，我只說一遍。」",
            topics=(
                AuthoredTopic(
                    topic_id="t_synth_conditioned.lineage",
                    keyword="簾後",
                    label="簾後",
                    fallback=Scene(
                        scene_id="t_synth_conditioned.lineage_scene",
                        revision="r1",
                        lines=(
                            Speech(speaker="actor", text="簾後是誰？"),
                            Speech(speaker="host", text="「簾後只是個做買賣的人。」"),
                        ),
                    ),
                    variants=(
                        SceneVariant(
                            variant_id="duskborn_lineage",
                            priority=10,
                            when=RaceIs(race_key="t_duskmari"),
                            scene=Scene(
                                scene_id="t_synth_conditioned.lineage_variant_scene",
                                revision="r1",
                                lines=(
                                    Speech(speaker="actor", text="簾後是誰？"),
                                    Speech(
                                        speaker="host",
                                        text="「暮民的眼睛瞞不過我，坐下說話。」",
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
                AuthoredTopic(
                    topic_id="t_synth_conditioned.attire",
                    keyword="紗影",
                    label="紗影",
                    fallback=Scene(
                        scene_id="t_synth_conditioned.attire_scene",
                        revision="r1",
                        lines=(
                            Speech(speaker="actor", text="這身裝束如何？"),
                            Speech(speaker="host", text="「行人打扮，沒什麼好說的。」"),
                        ),
                    ),
                    variants=(
                        SceneVariant(
                            variant_id="veiled_attire",
                            priority=10,
                            when=Exposure(minimum=2),
                            scene=Scene(
                                scene_id="t_synth_conditioned.attire_variant_scene",
                                revision="r1",
                                lines=(
                                    Speech(speaker="actor", text="這身裝束如何？"),
                                    Speech(
                                        speaker="host",
                                        text="「這層薄紗…你倒是很敢穿。」",
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
        # The locked-topic UI fixture (authored-dialogue-locked-ui): one open
        # topic and one visibly locked topic whose requirement (two kit items
        # the browser journey's player never carries) renders a canonical
        # hint, with an authored refusal scene the journey plays instead of
        # the protected formal body.
        "t_synth_gatekeeper": AuthoredDialogue(
            greeting="霧門前的守門人抬起燈：「要過門，先說來意。」",
            topics=(
                AuthoredTopic(
                    topic_id="t_synth_gatekeeper.road",
                    keyword="路況",
                    label="路況",
                    fallback=Scene(
                        scene_id="t_synth_gatekeeper.road_scene",
                        revision="r1",
                        lines=(
                            Speech(speaker="actor", text="門外的路好走嗎？"),
                            Speech(speaker="host", text="「霧散了就好走。」"),
                        ),
                    ),
                ),
                AuthoredTopic(
                    topic_id="t_synth_gatekeeper.passage",
                    keyword="霧門",
                    label="霧門後",
                    fallback=Scene(
                        scene_id="t_synth_gatekeeper.passage_scene",
                        revision="r1",
                        lines=(
                            Speech(speaker="actor", text="霧門後是什麼地方？"),
                            Speech(speaker="host", text="「門後是舊渡口，只有帶著證物的人能過。」"),
                        ),
                    ),
                    requires=All(
                        children=(
                            Carries(item_key="t_wayfarer_pass"),
                            Carries(item_key="t_veil_charm"),
                        )
                    ),
                    unavailable="locked",
                    refusal=Scene(
                        scene_id="t_synth_gatekeeper.passage_refusal",
                        revision="r1",
                        lines=(
                            Speech(speaker="actor", text="霧門後是什麼地方？"),
                            Speech(speaker="host", text="「這不是你現在該問的。」"),
                            Narration(text="守門人把燈壓低，霧又合攏了。"),
                        ),
                    ),
                ),
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

#: The physiological projection's own buff keys. They are production
#: *mechanism* keys, not authored content: mental settlement validates every
#: projection key against the live buff catalog and fails closed when one is
#: absent, so a scoped catalog must still carry the four protected,
#: modifier-free rows. ``world/tests/test_synthetic_data.py`` lists them as a
#: documented borrowed seam beside the map key and the element vocabulary.
PHYSIOLOGICAL_PROJECTION_KEYS: frozenset[str] = frozenset(
    PROJECTION_BUFF_KEYS.values()
)

# The physiological projection is deterministic mechanics, not authored lore:
# a scoped buff catalog must still carry its protected, indefinite rows so
# mental settlement can project a stage during a synthetic-scope test.
SYNTH_BUFFS.update(
    {
        key: BuffDefinition(
            key=key,
            duration=None,
            tick_interval=None,
            stacking="refresh",
            modifiers={},
            polarity="debuff",
            protection=PHYSIOLOGICAL_PROTECTION,
        )
        for key in PHYSIOLOGICAL_PROJECTION_KEYS
    }
)
