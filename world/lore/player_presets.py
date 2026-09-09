"""Immutable starter characters offered during account registration."""

from dataclasses import KW_ONLY, asdict, dataclass, fields
from math import isfinite
from typing import Any

from world.art.fallback_keys import validate_fallback_key
from world.lore.elements import ELEMENT_REGISTRY
from world.lore.items import ITEM_REGISTRY
from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY
from world.lore.sex import SEX_VALUES
from world.lore.sexual_vocab import (
    AROUSAL_LEVELS,
    BODY_PARTS,
    CLIMAX_PHASE_LEVELS,
    EXPOSURE_LEVELS,
    GENERIC_BODY_PART,
    SENSITIVITY_LEVELS,
    SHAME_LEVELS,
    WETNESS_LEVELS,
)
from world.skills.equipment import ACCESSORY_MAX_SLOTS, EquipmentSlot
from world.skills.registry import SKILL_REGISTRY, SkillKind

# The persona prose values the lore-side validator requires to be strings; the
# identity layers and appearance sub-keys are checked through their own
# dataclass field sets.
_PERSONA_PROSE_FIELDS = ("personality", "life_story", "habit", "background")


@dataclass(frozen=True)
class PresetIdentity:
    """The two identity layers PersonaStore renders (公開身分／隱秘身分)."""

    public: str = ""
    hidden: str = ""


@dataclass(frozen=True)
class PresetAppearance:
    """The seven appearance sub-keys declared in persona.py::_SUBKEY_ORDER."""

    height: str = ""
    weight: str = ""
    measurement: str = ""
    style: str = ""
    overview: str = ""
    attire: str = ""
    feature: str = ""


@dataclass(frozen=True)
class PresetPersona:
    """One preset's authored persona, in import-card record shape.

    Every value is optional and defaults to empty so a card can be authored
    incrementally; mutable containers are tuples of pairs to keep the registry
    immutable, and ``to_record()`` is the single place that expands them.
    """

    identity: PresetIdentity = PresetIdentity()
    personality: str = ""
    life_story: str = ""
    habit: str = ""
    appearance: PresetAppearance = PresetAppearance()
    social_connection: tuple[tuple[str, str], ...] = ()  # name -> relationship
    background: str = ""

    def to_record(self) -> dict[str, Any]:
        """Return the storage shape written to ``character.db.persona``.

        All six ``PERSONA_IMPORT_CARD_KEYS`` are always present (``""`` for
        unauthored prose, ``{}`` for unauthored structured keys), matching what
        custom activation and ``world.rules.persona_edit`` already produce; an
        empty ``identity`` layer is dropped from the identity subtree, empty
        appearance sub-keys are dropped, and ``background`` appears only when
        non-empty. ``social_connection`` stores the flat name -> relationship
        mapping (the one-level shape PersonaStore renders as
        ``名字：關係`` lines; the nested import-card form is its general case).
        The literal key set below mirrors
        ``world.rules.character_creation.PERSONA_IMPORT_CARD_KEYS``; lore must
        not import rules, and a rules-side test
        (``world/rules/tests/test_persona.py``) pins the two in lock step.
        """
        identity: dict[str, str] = {}
        if self.identity.public:
            identity["public"] = self.identity.public
        if self.identity.hidden:
            identity["hidden"] = self.identity.hidden
        appearance = {
            sub_key: value
            for sub_key, value in asdict(self.appearance).items()
            if value
        }
        record: dict[str, Any] = {
            "identity": identity,
            "personality": self.personality,
            "life_story": self.life_story,
            "habit": self.habit,
            "appearance": appearance,
            "social_connection": dict(self.social_connection),
        }
        if self.background:
            record["background"] = self.background
        return record


@dataclass(frozen=True)
class PresetSexualBaseline:
    """One preset's authored sexual baseline, in import-card record shape.

    Mirrors the import card's ``sexual_baseline`` object: ``arousal``,
    ``virgin``, and ``sensitivity`` are required; ``wetness``, ``shame``,
    ``exposure``, and ``climax_phase`` are optional, each empty value
    omitted from the record so ``SexualState``'s existing "default the
    omitted field to its vocabulary's lowest level" construction rule
    applies unchanged. ``sensitivity`` is a tuple of ``(body_part, level)``
    pairs so the registry stays immutable; ``to_record()`` expands it.
    """

    arousal: str
    virgin: bool
    sensitivity: tuple[tuple[str, str], ...]
    wetness: str = ""
    shame: str = ""
    exposure: str = ""
    climax_phase: str = ""

    def to_record(self) -> dict[str, Any]:
        """Return the storage shape written to ``character.db.sexual``.

        The three required keys are always present and ``sensitivity``
        becomes the flat body-part -> level mapping ``SexualState`` seeds
        from; each empty optional level is omitted rather than written as
        a literal, and ``climax_today`` / ``experience_types`` are never
        written because the builder already floors them at construction.
        """
        record: dict[str, Any] = {
            "arousal": self.arousal,
            "virgin": self.virgin,
            "sensitivity": dict(self.sensitivity),
        }
        for field in ("wetness", "shame", "exposure", "climax_phase"):
            value = getattr(self, field)
            if value:
                record[field] = value
        return record


@dataclass(frozen=True)
class StartingCompanion:
    """One preset's declared NPC companion, keyed by the partner's own card.

    ``preset_key`` names the companion's OWN ``PLAYER_PRESET_REGISTRY`` entry,
    so the companion's stats, skills, items, persona, and identity always come
    from the same card a player could have chosen -- never a second authored
    copy. ``affinity`` is the value the activation binding seeds into the
    relationship record (its numeric bounds derive from ``world.rules``
    constants and are swept rules-side, because lore must not import rules);
    ``relationship`` is the label written into the built companion's persona
    ``social_connection`` under the owning player's name.
    """

    preset_key: str
    affinity: int
    relationship: str


@dataclass(frozen=True)
class PlayerPreset:
    """A complete player-owned identity, raw stat allocation, and skill kit.

    ``allocations`` covers all seven allocatable axes (the three gauges and the
    four statics); the ``magic_power`` entry fixes the preset's starting magic
    power as a literal (growth-redesign D-A5 deleted the magic sampler).
    """

    key: str
    display_name: str
    age: int
    apparent_age: int
    race: str
    subrace: str
    allocations: tuple[tuple[str, int], ...]
    emphasis: str
    active_skills: tuple[str, ...] = ()
    passive_skills: tuple[str, ...] = ()
    affinity_elements: tuple[str, ...] = ()
    starting_items: tuple[tuple[str, int], ...] = ()
    # KW_ONLY from the first preset-parity field onward (field-parity design
    # 3.2): ``sex`` is a required keyword argument, so a new card that omits
    # it fails at construction instead of silently inheriting DEFAULT_SEX.
    # Removing the positional ``background`` slot shifted the former trailing
    # positional arguments, so every shipped card now passes the skill,
    # affinity, and persona fields by keyword.
    _: KW_ONLY
    sex: str
    # Declared starting practice XP as ``(skill_key, xp)`` pairs
    # (preset-lineage-and-proficiency). A declared entry always wins over the
    # activation auto-seed, even when it leaves a prerequisite edge unmet --
    # the same precedence an explicit import-record ``skill_proficiency``
    # entry has. An entry may name a key outside the preset's closed kit; it
    # is then persisted verbatim exactly as the import path persists one.
    skill_proficiency: tuple[tuple[str, float], ...] = ()
    # Which of the declared starting items are WORN at activation
    # (preset-starting-equipment). Every key SHALL be a subset of
    # ``starting_items`` (the pack stays the single source of what the
    # character owns) and name registry equipment; activation applies each
    # through ``world/rules/equipment.py::toggle_equipment``, the sole
    # equipment writer. The empty default keeps every shipped card's
    # observable starting state unchanged until an author fills the field.
    starting_equipment: tuple[str, ...] = ()
    persona: PresetPersona = PresetPersona()
    # The display-only disguise layer (preset-disguise-and-sexual-baseline)
    # as ``(axis_key, value)`` pairs. Keys are NOT whitelisted:
    # ``CHARACTER_SCHEMA_V1`` constrains the field only to integer values
    # (its subset-of-stats rule is an import-path semantic check the preset
    # path cannot mirror, because presets declare allocations, not absolute
    # stats), and display values never reach combat or resolution. The empty
    # default writes ``None``, which every reader treats as absent.
    disguised_stats: tuple[tuple[str, int], ...] = ()
    # The authored sexual baseline seeding ``entity.db.sexual`` (same
    # change). ``None`` writes nothing, so ``SexualState`` keeps applying
    # ``_generic_default_baseline()`` lazily exactly as before.
    sexual_baseline: PresetSexualBaseline | None = None
    # The declared NPC companions (starting-companions). Each entry names the
    # partner's own preset card, the affinity the activation binding seeds,
    # and the persona relationship label. The empty default keeps every
    # shipped card's observable starting state unchanged until an author fills
    # the field. Presence/self/duplicate shape is validated lore-side at load;
    # the bounds reading rules constants (companion count against
    # ``PARTY_MAX_COMPANIONS``, affinity against ``NATURAL_CAP``) are swept at
    # ``world/rules/starting_companions.py`` import time.
    starting_companions: tuple[StartingCompanion, ...] = ()
    # The OPTIONAL built-in gallery fallback key (gallery-builtin-fallbacks).
    # A preset MAY claim one key of the closed vocabulary outright, which
    # wins over the sex/age band rule for every character activated from it.
    # The unset default keeps every shipped card valid without one. The key
    # vocabulary lives in the dependency-neutral ``world.art.fallback_keys``
    # -- the only ``world.art`` surface lore may import -- and is checked at
    # registry construction below so a typo fails loudly at import.
    fallback_key: str | None = None

    def allocation_dict(self) -> dict[str, int]:
        """Return a mutable copy suitable for rules validation."""
        return dict(self.allocations)

    def skill_lists(self) -> dict[str, list[str]]:
        """Return the storage shape for the character ``skills`` attribute."""
        return {"active": list(self.active_skills), "passive": list(self.passive_skills)}

    def inventory_list(self) -> list[str]:
        """Return the flat repeated-key inventory the activation hands out."""
        return [
            item_key
            for item_key, quantity in self.starting_items
            for _ in range(quantity)
        ]


def _validate_preset_fallback_keys(registry: dict[str, PlayerPreset]) -> None:
    """Reject a declared fallback key outside the closed vocabulary.

    Runs at registry construction (import) time like every other preset
    sweep, so an authored typo fails loudly at import rather than silently
    resolving to a nonexistent image.
    """
    for preset in registry.values():
        validate_fallback_key(preset.fallback_key, f"preset {preset.key!r}")


PLAYER_PRESET_REGISTRY: dict[str, PlayerPreset] = {
    "elysa_snow": PlayerPreset(
        # Key drawn from the fantasy-human name corpus (world/lore/names, via
        # world.rules.namegen): Elysa + Snow. The display name is the pack's
        # 正體 rendering of the given name; the full name lives in the
        # identity layers.
        "elysa_snow", "艾莉莎", 24, 24, "human", "human_commoner",
        (("hp", 50), ("mp", 50), ("sp", 50), ("atk_phys", 10),
         ("agility", 10), ("defense", 11), ("magic_power", 43)),
        "生命力與魔力均衡的開局配點",
        active_skills=("light_sword_style",),
        passive_skills=("body_enhancement_basic",),
        starting_items=(("plain_sword", 1), ("leather_armor", 1),
                        ("guild_recruit_badge", 1), ("healing_potion", 2),
                        ("healing_herb", 2)),
        sex="female",
        starting_equipment=("plain_sword", "leather_armor", "guild_recruit_badge"),
        persona=PresetPersona(
            identity=PresetIdentity(
                public="南境出身的公會新人冒險者，測繪局抄寫員出身的旅人",
                hidden=(
                    "追尋母親最後一份地圖上那片無名空白的女兒；所有知道那片空白的人，"
                    "都已經失蹤"
                ),
            ),
            personality=(
                "對任何人都能在三句話內熟絡起來——先讓人笑，再讓人卸下戒心，"
                "這是抄寫員的女兒從小學會的本事。對文字有近乎強迫的忠實：聽過的每句話、"
                "看過的每張地圖，她都要抄進隨身筆記，連自己的謊話也照記。別人眼裡這是怪癖，"
                "對她卻是對付遺忘的方式——母親失蹤以後她才明白，記憶會騙人，抄本不會。"
                "對委託來者不拒，對報酬計較到銅板，但每次掙到一筆大錢都會請路上最窮的人吃一頓。"
                "從不在同一個城鎮睡超過三晚，除了公會公告上出現「空白」兩個字的地方。"
            ),
            life_story=(
                "母親艾黛勒是王國測繪局少見的女性測繪師，六年前帶隊進入南方那片「地圖上沒有名字的空白」，"
                "從此沒有回來。官方檔案裡那支隊伍只存在過一頁，而那一頁也在她十六歲那年悄悄消失了——"
                "她來不及抄下它，這件事她追悔了八年。十八歲起她在測繪局做抄寫員，十年間抄过上萬份文件，"
                "把每一份與「空白」有關的邊注都背了起來。二十歲那年，她從母親歷年報告裡湊齊了十七個座標中的十六個，"
                "每條路線的盡頭都指向同一個不存在的地方。二十四歲，她辭去職位、變賣家當在公會登記，"
                "把筆記翻到新的一頁：這一次，由她親自走去那第十七個座標。"
            ),
            habit=(
                "隨身帶著三本筆記、兩支炭筆：一本記人、一本記路、一本只抄與「空白」有關的文字；"
                "睡前會把當天說過的話重讀一遍，確認自己沒有不知不覺撒謊；每次住店都用同一個假名，"
                "但姓氏永遠沿用母親的舊姓。"
            ),
            appearance=PresetAppearance(
                height="168 公分",
                weight="55 公斤",
                measurement="胸圍 88（C 罩杯）、腰 64、臀 90",
                style="小麥膚色的開朗旅人",
                overview=(
                    "深褐長髮綁成實用的低馬尾，綠色眼眸愛笑，鼻梁上有淡淡的曬斑；"
                    "指節與右手中指內側有常年握筆磨出的繭，笑容燦爛，視線卻永遠在讀環境。"
                ),
                attire="磨舊的皮甲與旅人斗篷，腰間掛著一把擦得過分外亮的長劍，背包塞滿筆記。",
                feature=(
                    "右手永遠沾著洗不掉的炭筆污痕；頸上掛著母親測繪隊的銅製羅盤吊墜，"
                    "指針從來不準，她卻從未摘下。"
                ),
            ),
            social_connection=(
                ("艾黛勒·懷特", "母親，失蹤的測繪師；她追隨母親腳步的起點，也是她唯一不敢抄進筆記的話題"),
            ),
            background=(
                "南境出身的公會新人冒險者，測繪局抄寫員出身。母親六年前走入地圖上一片無名空白後失蹤，"
                "官方記錄隨後被人抹去。她帶著十年抄本與一把磨亮的長劍出發，要用自己的腳補上那張缺了一角的地圖；"
                "均衡的劍術與基礎強化，是她敢獨自上路的底氣。"
            ),
        ),
        sexual_baseline=PresetSexualBaseline(
            arousal="平靜",
            virgin=True,
            sensitivity=(("頸項", "高"), ("耳朵", "高"), ("腰腹", "高")),
            shame="中等",
            exposure="低",
        ),
    ),
    "nazka_bloodfang": PlayerPreset(
        # Key drawn from the fantasy-orc name corpus (world/lore/names, via
        # world.rules.namegen): Nazka + Bloodfang.
        "nazka_bloodfang", "娜茲卡", 22, 22, "beastfolk", "foxkin",
        (("hp", 25), ("mp", 10), ("sp", 25), ("atk_phys", 15),
         ("agility", 15), ("defense", 15), ("magic_power", 14)),
        "敏捷與近身作戰優先的斥候配點",
        active_skills=("gale_step",),
        passive_skills=("flash_step",),
        affinity_elements=("wind",),
        starting_items=(("hunters_longbow", 1), ("hunting_throwing_axe", 1),
                        ("leather_armor", 1), ("wolf_fang_necklace", 1),
                        ("healing_potion", 1), ("healing_herb", 3)),
        sex="female",
        starting_equipment=(
            "hunters_longbow", "hunting_throwing_axe", "leather_armor", "wolf_fang_necklace"
        ),
        persona=PresetPersona(
            identity=PresetIdentity(
                public="獸王國瓦爾哈拉出身的信使，公會新人斥候",
                hidden=(
                    "十年間獸王國送信者不敢說出口的每一封密信函，都在她腦子裡——"
                    "她發過誓不說，卻從沒發過誓不記得"
                ),
            ),
            personality=(
                "話多、愛笑、腿快，是獸王國最難纏的聊天對象：三句話內她就能讓人不知不覺說出"
                "本不想說的話，而她連看都不看你一眼。對「送信」有近乎神職的執念——信件在路上是死的，"
                "送到才算活著。她記得經手的每一封信的內容，不是炫耀，是職業病，也是她對寫信人的"
                "最後一種溫柔：收信人死了、搬走了、忘了回信，至少還有人記得那句話說過。"
                "從不賣情報，也從不用情報換好處；但如果有人能讓她笑到岔氣，她可能一不小心說漏半句。"
            ),
            life_story=(
                "出身獸王國瓦爾哈拉的送信世家，從小聽著「信送不到，命就該留在路上」長大。"
                "十二歲通過信使考核，是當時十年來最年輕的正式信使；十七歲那年雪夜連走三個聚落送藥，"
                "右耳尖凍掉一小塊，族裡都說那是信使勳章。十九歲，她送的最後一封信，收信人已經死了三天——"
                "她照規矩把信燒給死人，回家路上第一次想到：除了她，還有誰記得那封信寫了什麼？"
                "從那天起，她開始把經手的信逐字背下來。二十一歲，她帶著一紙內容不明的調令離開獸王都，"
                "到人類公會登記成斥候。她說自己是要去「送一封更長的信」，卻怎麼也不肯說是哪一封、送給誰。"
            ),
            habit=(
                "跑步時把經過的地形默背成路線圖；坐下來必先確認出口與至少兩條脫身路線；"
                "聊天時尾巴早就出賣了情緒，她卻堅持自己「表情管理很好」；每晚睡前在腦中"
                "把當天新背起來的信從頭到尾默讀一遍。"
            ),
            appearance=PresetAppearance(
                height="158 公分",
                weight="48 公斤",
                measurement="胸圍 86（D 罩杯）、腰 57、臀 89",
                style="橙白毛色的高馬尾狐人族少女",
                overview=(
                    "橙白色長髮束成高馬尾，琥珀色豎瞳總像在笑，右耳尖少了一小塊——"
                    "獸王國信使的勳章；尾巴蓬鬆，情緒一激動就完全藏不住。"
                ),
                attire="斥候皮甲與輕便斗篷，背長弓、腰間別飛斧，胸前掛著磨舊的小皮袋。",
                feature=(
                    "右耳尖缺一角；說謊時蓬鬆的大尾巴會不由自主往左偏——這是她全身上下唯一不會撒謊的地方。"
                ),
            ),
            social_connection=(
                ("布麗", "養大她的白母狼；牙項鍊是她送出的告別禮，布麗卻咬斷項鍊送回她門前"),
            ),
            background=(
                "獸王國瓦爾哈拉出身的狐人族信使，十年間經手的每一封信她都逐字記得，卻從不說出口。"
                "疾風術與瞬步讓她在斥候崗位上幾乎不會被追上；她說離開獸王國是去「送一封信」，"
                "卻拒絕說是哪一封、送給誰。"
            ),
        ),
        sexual_baseline=PresetSexualBaseline(
            arousal="微興奮",
            virgin=True,
            sensitivity=(("耳朵", "極高"), ("頸項", "高"), ("臀部", "高")),
            wetness="微濕",
            shame="輕微",
            exposure="低",
        ),
    ),
    "sylwen_stillwater": PlayerPreset(
        # Key drawn from the fantasy-elf name corpus (world/lore/names, via
        # world.rules.namegen): Sylwen + Stillwater.
        "sylwen_stillwater", "希爾溫", 180, 24, "elf", "fionnen",
        (("hp", 0), ("mp", 0), ("sp", 0), ("atk_phys", 12),
         ("agility", 12), ("defense", 13), ("magic_power", 400)),
        "防禦與均衡戰技優先的守護者配點",
        active_skills=("hardened_skin",),
        passive_skills=("defense_instinct", "elf_longevity"),
        starting_items=(("knight_blade", 1), ("iron_shield", 1),
                        ("chainmail", 1), ("pilgrim_medallion", 1),
                        ("healing_potion", 1)),
        sex="female",
        starting_equipment=("knight_blade", "iron_shield", "chainmail", "pilgrim_medallion"),
        persona=PresetPersona(
            identity=PresetIdentity(
                public="斐歐恩森林出身的精靈族護衛，人族王國的傭兵守護者",
                hidden="守著三道守護誓約的人——前兩道的對象，都已老成土裡的名字",
            ),
            personality=(
                "沉穩、有耐心，像一棵不會因為風彎腰的樹。比起爭勝，她更在意「有沒有任何人活著回來」，"
                "隊伍裡最危險的位置她永遠先站。她對人族的短壽有一種異常的珍視：會記住每個共事過的人"
                "愛吃什麼、怕什麼、說過哪句傻話，然後在對方老去之後，把這些話說給對方的孫輩聽。"
                "不擅長被感謝，被人當面誇獎時會彆扭地低頭擦盾牌。笑容很少，卻從不吝嗇——對孩子、新兵、"
                "以及所有怕死的人格外溫柔，因為她比誰都清楚：怕死不是缺點，是還想把日子過下去的證明。"
            ),
            life_story=(
                "出生在斐歐恩森林，成長禮那天用森林古語立下斐歐恩護衛世代一次的誓約——守護一個自己選定的人族。"
                "第一位守護對象是人族商隊護衛漢斯，她守到他七十一歲在搖椅中安詳過世，子孫在靈前為她留了一杯蜂蜜酒。"
                "第二位是漢斯的曾孫女；她在難產的夜裡為擋住闖進帳篷的野獸失去半截左手小指，卻把母子兩人都救了回來。"
                "如今她守著的是那個孩子留下的血脈——誓約的字面早已超過，她把整條血脈都算進了誓言。"
                "以傭兵護衛的身分流浪在人族王國，公會檔案裡她的年齡寫成一串被職員當成玩笑的數字。"
            ),
            habit=(
                "每年冬至在盾牌背帶上刻一道痕，記下又平安過完的一年；幫人包紮時動作輕得和握盾的手"
                "完全不像同一個人；睡前會把共事過的人的名字在腦中從最年輕唸到最年長，一個都不許忘記。"
            ),
            appearance=PresetAppearance(
                height="174 公分",
                weight="62 公斤",
                measurement="胸圍 92（E 罩杯）、腰 66、臀 94",
                style="銀綠長髮的高挑精靈重甲護衛",
                overview=(
                    "銀綠色長髮束成一條低辮，翠綠眼眸沉靜溫和，臉側有一道從額角延伸到頰的舊疤；"
                    "站姿穩得像面牆，精靈的尖耳收在辮子後頭。"
                ),
                attire="連鎖甲與塔盾在內的護具，胸前掛著斐歐恩森林的銀葉吊墜。",
                feature=(
                    "盾牌背帶上刻著一百多年的歲痕；左手小指缺了半截——那個夜晚她沒來得及把盾牌收進狹窄的帳篷，"
                    "人救回來了，那半截手指卻留了下來。"
                ),
            ),
            social_connection=(
                ("漢斯·懷特", "第一位誓約對象、人族商隊護衛；他活到七十一歲，臨終把兒女托付給她這個精靈"),
            ),
            background=(
                "斐歐恩森林出身的精靈族護衛，用一百八十年的歲月實踐世代一次的守護誓約。"
                "硬化肌膚與防禦直覺讓她成為隊伍最可靠的盾；她守護人族的理由不是憐憫短壽，"
                "而是比誰都清楚——正因為日子短，每一天才都值得守。"
            ),
        ),
        sexual_baseline=PresetSexualBaseline(
            arousal="平靜",
            virgin=False,
            sensitivity=(("耳朵", "極高"), ("乳房", "高"), ("私處", "高")),
            shame="輕微",
            exposure="極低",
        ),
    ),
    "violet_altoria": PlayerPreset(
        # Reconverted from tmp/story_settings/character/VioletAltoria.md: age
        # 16, story gauges 150/180/150 exact, pre-buff statics 5/6/6 exact,
        # remaining budget into magic power (story "magic level 30" reads as a
        # moderate-high magic attribute for a prodigy).
        "violet_altoria", "薇歐蕾特", 16, 16, "human", "human_royal",
        (("hp", 50), ("mp", 60), ("sp", 50), ("atk_phys", 4),
         ("agility", 5), ("defense", 4), ("magic_power", 51)),
        "體力與生命力精準、魔力突出的術師配點",
        active_skills=("fire_ball", "wind_blade"),
        passive_skills=(
            "magic_circle_comprehension", "precise_mana_control", "flight",
        ),
        affinity_elements=("fire", "wind"),
        starting_items=(("elven_traditional_robe", 1), ("royal_signet_ring", 1),
                        ("royal_heirloom_pendant", 1)),
        sex="female",
        # Story's current equipment: spirit robe worn, signet ring on the right
        # ring finger; the heirloom pendant stays carried (her nervous habit).
        starting_equipment=("elven_traditional_robe", "royal_signet_ring"),
        persona=PresetPersona(
            identity=PresetIdentity(
                public="出行的王國王女、伊洛希雅的弟子、風之術師",
                hidden="王室秘密外交特使，意圖將伊洛希雅·幽月納入王國盟友",
            ),
            personality=(
                "任何場合都維持得體的微笑與禮貌應對，從不失態；深知自己是天才，"
                "也深知天才的上限，對自身能力評價準確。意志堅韌，對羞恥與不適的"
                "耐受力遠超同齡人；對師父伊洛希雅的信任達到盲目程度。被出乎預料的"
                "逗弄時，從容會短暫破防，越是羞恥說話越端正優雅。表面維持王女矜持，"
                "被充分開發的身體卻早已背叛意志——不合時宜的場合自然濕潤，既羞恥"
                "又興奮；僅在無人在場時才流露普通少女的羞恥與不安。"
            ),
            life_story=(
                "5 歲起接受宮廷禮儀、多國語言與政治史學的全方位教育；7 歲對四階"
                "魔法陣一看即懂，被宮廷冠以「神童」稱號，但她比任何人都清楚自己的"
                "天花板在哪裡。13 歲時父王透露精靈族若能成為王國友方，可扭轉對帝國"
                "的軍事劣勢。15 歲以史上最年輕首席身份從王立魔法初等學校畢業，魔法"
                "等級由 10 級升至 30 級。16 歲出行時被伊洛希雅超越人類極限的魔法"
                "震撼，請求拜師，接受了「穿著精靈傳統服飾一同冒險」的條件——第一次"
                "穿上幾近全裸的服飾走上街頭，全身僵硬仍勉強維持微笑。"
            ),
            habit=(
                "無論何種狀況都維持筆直儀態；緊張時習慣以指尖輕觸胸前吊墜——穿上"
                "精靈傳統服飾後胸部全裸，這個習慣反而讓她頻繁觸碰自己的胸口；私下"
                "研讀伊洛希雅給的精靈古籍，對鏡審視自己現在到底像什麼。"
            ),
            appearance=PresetAppearance(
                height="155 公分",
                weight="46 公斤",
                measurement="胸圍 82（B 罩杯）、腰 56、臀 83",
                style="優雅清冷的少女王族",
                overview=(
                    "身形纖細修長，金色長直髮半盤，藍眸清澈沉靜，皮膚白皙，"
                    "五官精緻柔和；人族，沒有長耳朵。"
                ),
                attire="與伊洛希雅同款的精靈傳統服飾——白色半透明、幾近全裸的「文化服飾」。",
                feature=(
                    "右手無名指佩戴嵌王室紋章的細金戒指，是唯一隨身攜帶的身份象徵；"
                    "在精靈傳統服飾下私處完全暴露，長期「訓練」使身體帶著明顯的淫靡痕跡。"
                ),
            ),
            social_connection=(
                ("伊洛希雅·幽月", "師父與主要逗弄對象，被單方面支配，信任近乎盲目；互稱「伊洛」「薇歐」"),
                ("莉茲婭·羅森塔爾", "從小一起長大的玩伴、貼身侍女兼保鏢，如今承擔痴女侍從的職責；她喚我「主人」，我喚她「莉茲」"),
            ),
            background=(
                "阿爾托利亞王國第一王女，「痴女與精靈」小隊隊長。16 歲拜入伊洛希雅"
                "門下，以穿著精靈傳統服飾一同冒險為拜師條件。天才術師的火球與風刃"
                "遠超同齡，飛行術使她習慣從高處俯瞰世界；對外報出隊名時伴隨極度羞恥，"
                "卻無法否認那個名字對自身狀態的描述完全準確。"
            ),
        ),
        sexual_baseline=PresetSexualBaseline(
            arousal="微興奮", virgin=True,
            sensitivity=(("私處", "極高"), ("乳房", "高"), ("耳朵", "高")),
            wetness="濕潤", shame="中等", exposure="高",
        ),
        # The story's party travels together: Violet sets out with her retainer
        # and follows her elven master.
        starting_companions=(
            StartingCompanion("lidzia_rosenthal", 95, "貼身近侍"),
            StartingCompanion("elosia_shadowmoon", 95, "師父"),
        ),
    ),
    "lidzia_rosenthal": PlayerPreset(
        # Reconverted from tmp/story_settings/character/LidziaRosenthal.md: age
        # 14, story statics 8/9/7 exact under the noble modifiers; the story's
        # MP 70 sits below the human floor, so MP stays at the floor (her
        # weakest gauge, matching "魔法天賦極差") and the forced remainder
        # lands on the story's strongest gauges, stamina over vitality.
        "lidzia_rosenthal", "莉茲婭", 14, 14, "human", "human_noble",
        (("hp", 80), ("mp", 0), ("sp", 100), ("atk_phys", 6),
         ("agility", 8), ("defense", 7), ("magic_power", 23)),
        "體力最強、劍技敏於防禦的近侍配點",
        active_skills=("light_sword_style",),
        passive_skills=(
            "body_enhancement_basic", "retainer_martial_training",
            "guardian_instinct",
        ),
        starting_items=(("rose_crest_rapier", 1), ("black_maid_dress", 1),
                        ("silver_feather_earring", 1)),
        sex="female",
        # Story's equipment: rapier, maid dress, and the never-removed earring.
        starting_equipment=("rose_crest_rapier", "black_maid_dress",
                            "silver_feather_earring"),
        persona=PresetPersona(
            identity=PresetIdentity(
                public="王女薇歐蕾特的貼身侍女、隨身秘書與保鏢",
                hidden="無可救藥地愛著薇歐蕾特，這份愛不索求回報；她的幸福就是殿下的幸福",
            ),
            personality=(
                "任何場合都維持完美侍從的儀態與效率——把每件事做到極致，是她表達愛"
                "的唯一合法方式。劍術與文書出類拔萃，全力以赴卻在一句稱讚面前臉紅低"
                "頭；對同僚開朗、好人緣，唯獨薇歐蕾特是讓她連呼吸都要練習的人。主人"
                "面臨危險的瞬間，羞澀像多餘的東西一樣剝落，殺意像死神確認名單那樣淡"
                "定；僅與主人獨處時才露出真實笑容與撒嬌。這份愛太重，重到需要痛來平"
                "衡，但她從未想過獨佔——如果殿下的幸福需要她消失，她會消失。"
            ),
            life_story=(
                "羅森塔爾家族世代侍奉王室，3 歲起接受嚴格禮儀與武術訓練，「被需要」"
                "本身就足以填滿她。5 歲在王室宴會上對 7 歲的薇歐蕾特一見傾心；7 歲"
                "入宮為初級侍女，端茶燙傷手背時由公主親自包紮，那隻手的溫度至今留在"
                "掌心。10 歲攔截針對公主的毒殺未遂，獲授近侍職位；評估每個靠近公主"
                "之人的威脅等級，是她的安眠藥。12 歲以護衛考核全項第一通過，拒絕近"
                "衛隊延攬，選擇繼續做公主的影子。13 歲意識到心跳不再只因職責。14 歲"
                "隨薇歐蕾特出行歷練——哪裡有殿下，哪裡就是家。"
            ),
            habit=(
                "每個動作精準而溫柔，端茶的角度、關門的音量、站立的間距皆精確如舞"
                "步；在薇歐蕾特身邊保持半步距離，這個距離練習了數年，已是身體記憶；"
                "每晚睡前檢查主人的裝備與行李，深夜獨處時才敢抱著沾有主人氣息的手帕"
                "入睡。"
            ),
            appearance=PresetAppearance(
                height="150 公分",
                weight="42 公斤",
                measurement="胸圍 84（C 罩杯）、腰 55、臀 82",
                style="短髮稚氣的文武雙全美少女",
                overview=(
                    "黑色短鮑伯頭配齊瀏海，嬰兒肥臉頰，琥珀色眼眸溫和明亮，看薇歐蕾特"
                    "時瞳孔會不自覺放大；身材豐滿與稚嫩面容形成反差。人族，沒有長耳朵。"
                ),
                attire="黑色女僕裝搭配極短微裙與白色腰圍裙，輕劍斜掛腰間。",
                feature=(
                    "腰間輕劍劍柄末端刻有薇歐蕾特親手雕的王室薔薇紋章；右耳銀羽耳環是"
                    "薇歐蕾特 12 歲時的禮物，從未摘下。"
                ),
            ),
            social_connection=(
                ("薇歐蕾特·阿爾托利亞", "主人、她生存的中心、心臟跳動的理由，比起主人更像是她的信仰；稱呼從「殿下」改為「主人」，被賦予隨時隨地擦拭愛液的職責，這是她此生收過最珍貴的禮物"),
            ),
            background=(
                "世代侍奉王室的羅森塔爾家族之女，薇歐蕾特王女的貼身近侍與「痴女與精"
                "靈」小隊痴女侍從。輕劍術在護衛考核名列前茅，隨從武藝與護主本能使她"
                "永遠站在主人與危險之間；基礎身體強化是她僅有的魔法天賦。"
            ),
        ),
        sexual_baseline=PresetSexualBaseline(
            arousal="平靜", virgin=True,
            sensitivity=(("頸項", "高"), ("耳朵", "高"), ("乳房", "高"),
                         ("腰腹", "高"), ("大腿", "高")),
            shame="強烈",
        ),
        # Story: Lidzia travels at Violet's side; the built Violet card names
        # her back, matching the twins' precedent.
        starting_companions=(StartingCompanion("violet_altoria", 95, "主人"),),
    ),
    "yuka_darknight": PlayerPreset(
        # Reconverted from tmp/story_settings/character/YukaDarknight.md: age
        # 16; base statics 88/92/90 exact (the x1000 body enhancement is the
        # skill, not the allocation); the remaining budget inflates magic
        # power above the story's 250 because the elf gauge floors consume no
        # budget and the budget must be spent in full.
        "yuka_darknight", "悠花", 16, 16, "elf", "ciaran",
        (("hp", 0), ("mp", 0), ("sp", 0), ("atk_phys", 18),
         ("agility", 22), ("defense", 20), ("magic_power", 377)),
        "攻擊與防禦逼近精靈上限的雙刀配點",
        active_skills=("dual_blade_mastery", "shadow_slash", "status_disguise"),
        passive_skills=(
            "fire_mastery", "dark_mastery", "body_enhancement_extreme",
            "flash_step", "flight", "dual_wield_style", "blade_art_mastery",
            "extreme_endurance", "defense_instinct", "reincarnation_boon_yuka",
        ),
        starting_items=(("shadow_blade", 1), ("shadow_blade_echo", 1),
                        ("dark_elf_ninja_garb", 1)),
        sex="female",
        # Story's equipment: both blades and the garb are worn.
        starting_equipment=("shadow_blade", "shadow_blade_echo",
                            "dark_elf_ninja_garb"),
        persona=PresetPersona(
            identity=PresetIdentity(
                public="暗影谷村的年輕黑暗精靈、擁有罕見黑髮的雙刀使、悠奈的旅伴與妹妹",
                hidden="轉生者（前世為現代日本的女高中生）、刀術狂熱者、悠奈最珍視的伴侶",
            ),
            personality=(
                "陽光開朗、充滿活力，笑容極具感染力，走到哪裡都能迅速融入人群。對"
                "刀術的熱愛近乎痴迷——每一次揮刀都是在跟自己的極限對話；熱愛體能，"
                "享受突破身體框架的快感。握刀時氣質驟變，整個人像一把出鞘的刀；心底"
                "仍保留一絲前世的害羞，在公共場合裸露會不自覺遮一下，然後尷尬地笑笑"
                "放下手。深愛悠奈，是不帶任何保留的純粹的愛；最大的秘密是對悠奈的魔"
                "力上癮——普通的性愛對她早已索然無味，只有悠奈的魔法能真正滿足她，"
                "而她永遠不會承認這件事。"
            ),
            life_story=(
                "前世是現代日本田徑隊王牌女高中生，16 歲與姊姊悠奈一同死於意外，睜"
                "眼成為暗影谷村黑暗精靈的新生兒，前世記憶清晰如昨。4 歲第一次握上木"
                "刀的瞬間找到此世歸屬，感動到幾乎落淚；5 歲轉生特典「武感」顯現，能"
                "本能預判對手攻擊意圖。10 歲已是同輩最出色的刀術使，14 歲修成身體超"
                "強化。16 歲與悠奈一同離開村子——不管去哪裡，只要跟悠奈在一起就是好"
                "地方。"
            ),
            habit=(
                "每天固定體能訓練與刀術練習，練完滿身大汗回到悠奈身邊；走路步伐輕"
                "快，習慣走在前面，每次回頭確認悠奈的位置才安心前進；在公共場合仍會"
                "不自覺遮一下胸口或下體，然後尷尬地笑笑放下手。"
            ),
            appearance=PresetAppearance(
                height="165 公分",
                weight="52 公斤",
                measurement="胸圍 90（D 罩杯）、腰 59、臀 88",
                style="罕見黑短髮的運動系黑暗精靈",
                overview=(
                    "基亞蘭族褐色健康膚色，黑色短鮑伯頭清爽俐落，紅色眼眸明亮有神；"
                    "肌肉線條結實，力量與柔美並存，精靈族的尖耳從短髮間探出。"
                ),
                attire="基亞蘭族墨黑戰鬥服飾，忍者基底的短和服剪裁，刻意敞開的前襟與極短裙襬。",
                feature=(
                    "罕見黑色短鮑伯頭，在銀髮同族中與悠奈並列為異色存在；長期練刀使"
                    "手掌帶著薄繭，笑容極具感染力。"
                ),
            ),
            social_connection=(
                ("悠奈", "雙胞胎姊姊、前世的摯愛、此世的靈魂伴侶；互稱「悠奈」「悠花」。前世一同死於意外，此世一同作為黑暗精靈誕生"),
            ),
            background=(
                "暗影谷村出身的黑暗精靈雙刀使，罕見的黑短髮在銀髮同族中格外醒目。"
                "宗師級雙刀流與影斬名聲在外，轉生特典武感使她總能先一步抵達對手要害。"
                "陽光開朗，視戰鬥為與自身極限的對話，與姊姊悠奈形影不離。"
            ),
        ),
        # Story's disguise layer: magic 30, physical 60, agility 60, defense 30.
        disguised_stats=(("magic_power", 30), ("atk_phys", 60),
                         ("agility", 60), ("defense", 30)),
        sexual_baseline=PresetSexualBaseline(
            arousal="微興奮", virgin=False,
            sensitivity=(("乳房", "極高"), ("私處", "極高"), ("耳朵", "高")),
            wetness="濕潤", shame="輕微", exposure="中等",
        ),
        # The twins arrive together: 悠花's own card is her companion, seeded
        # at 95 (above the invite threshold, inside 至愛 with headroom), with
        # 悠奈 as the elder sister.
        starting_companions=(StartingCompanion("yuna_darknight", 95, "雙胞胎姊姊"),),
    ),
    "yuna_darknight": PlayerPreset(
        # Reconverted from tmp/story_settings/character/YunaDarknight.md: age
        # 16; story defense 92 exact, the story's 65/65 physical floor sits
        # under the elf minimum, and the remaining budget inflates magic
        # power above the story's 350 (the budget must be spent in full).
        "yuna_darknight", "悠奈", 16, 16, "elf", "ciaran",
        (("hp", 0), ("mp", 0), ("sp", 0), ("atk_phys", 0),
         ("agility", 0), ("defense", 22), ("magic_power", 415)),
        "防禦特化的魔力體質配點",
        active_skills=("divine_sexual_arts", "status_disguise"),
        passive_skills=(
            "fire_mastery", "dark_mastery", "divine_sexual_mastery",
            "reincarnation_boon_yuna", "body_enhancement", "flight",
            "defense_instinct",
        ),
        starting_items=(("dark_elf_kimono", 1),),
        sex="female",
        # Story's equipment: the kimono is the only worn item (no weapon, no
        # accessories).
        starting_equipment=("dark_elf_kimono",),
        persona=PresetPersona(
            identity=PresetIdentity(
                public="暗影谷村的年輕黑暗精靈、擁有罕見黑髮的性魔法天才",
                hidden="轉生者（前世為現代日本的女高中生）、極端性愛實踐者、性魔法主宰",
            ),
            personality=(
                "知性冷靜，即使在公共場合高潮，表情管理依然完美。享樂至上——追求更多、"
                "更強、更新鮮的快感，熱情真誠到近乎天真；每天都為轉生到這具玩不壞的"
                "黑暗精靈肉體而感恩。越在人多的場合狀態越好，注視越多魔法越華麗。對"
                "悠花有特別的執著，喜歡用魔法把她玩到崩潰，再溫柔抱緊她說「辛苦了」。"
                "說話語調溫和禮貌，優雅地說出下流詞彙，反差讓人目瞪口呆。"
            ),
            life_story=(
                "前世是表面知性優等生、私下沉溺極端性刺激的雙面女高中生，16 歲與妹"
                "妹悠花一同死於意外，轉生為暗影谷村黑暗精靈的新生兒。5 歲轉生特典「性"
                "魔法主宰」顯現，一道魔力讓悠花瞬間高潮失神；8 歲自如融合暗魔法與性"
                "魔法；10 歲在村中廣場疊加七層性魔法，持續高潮整個下午。12 歲起研究"
                "神之秘法的性愛系統，發現能創造不存在於物理法則中的快感；14 歲已是村"
                "中公認的性魔法天才。16 歲與悠花離開村子——人類的反應肯定比精靈更有"
                "趣。"
            ),
            habit=(
                "公共場合坐下時從不刻意併攏雙腿——穿這樣就是要給人看的；思考時下意"
                "識以指尖輕觸陰蒂，這個動作早已自動化；每晚睡前用性魔法給自己疊加多"
                "重快感，在持續高潮中入睡。"
            ),
            appearance=PresetAppearance(
                height="165 公分",
                weight="49 公斤",
                measurement="胸圍 88（D 罩杯）、腰 58、臀 86",
                style="罕見黑髮的知性黑暗精靈",
                overview=(
                    "褐色健康膚色，極罕見的黑色長直髮瀑布般垂至腰際，紫色眼眸沉靜溫"
                    "和，施法時浮現專注的狂熱；身材勻稱玲瓏，尖耳從黑髮間探出。"
                ),
                attire="基亞蘭族墨黑傳統服飾，遊女和服基底的短和服剪裁，前襟敞開、裙襬極短。",
                feature=(
                    "黑長直髮是精靈族中最顯眼的標誌；施展性魔法時，暗紫色魔力紋路沿"
                    "脊椎蔓延至腰際。"
                ),
            ),
            social_connection=(
                ("悠花", "雙胞胎妹妹、前世的性伴侶、此世最喜歡的實驗對象；互稱「悠花」「悠奈」。深愛著她，愛的表現方式是把她玩到死去活來"),
            ),
            background=(
                "與雙胞胎妹妹一同離開暗影谷村的黑暗精靈，罕見的黑長髮與知性外表之下，"
                "是將性魔法鑽研到極致的享樂主義者。精通火與闇屬性，"
                "並以神之秘法觸及性愛系統的領域。"
            ),
        ),
        # Story's disguise layer: 30 across magic and all three physical axes.
        disguised_stats=(("magic_power", 30), ("atk_phys", 30),
                         ("agility", 30), ("defense", 30)),
        sexual_baseline=PresetSexualBaseline(
            arousal="微興奮", virgin=False,
            sensitivity=(("乳房", "極高"), ("私處", "敏感異常"), ("耳朵", "高")),
            wetness="泛濫", shame="無", exposure="極高",
        ),
        # The symmetric half of the pair: 悠奈 arrives with 悠花, the younger
        # twin, at the same affinity.
        starting_companions=(StartingCompanion("yuka_darknight", 95, "雙胞胎妹妹"),),
    ),
    "elosia_shadowmoon": PlayerPreset(
        # Reconverted from tmp/story_settings/character/ElosiaShadowmoon.md:
        # species is 伊歐拉斯族 (eolas, Phantasm Elf), age 10/apparent 10 (she
        # CLAIMS 222; the persona prose carries the lie). Story statics
        # 70/70/95 exact; the story's 873 magic exceeds the creation ceiling,
        # so the full remaining budget lands at the 512 maximum the budget
        # allows.
        "elosia_shadowmoon", "伊洛希雅", 10, 10, "elf", "eolas",
        (("hp", 0), ("mp", 0), ("sp", 0), ("atk_phys", 0),
         ("agility", 0), ("defense", 25), ("magic_power", 412)),
        "防禦滿值、魔力極高的魔導師配點",
        active_skills=("dominion_art", "status_disguise"),
        passive_skills=(
            "wind_mastery", "light_mastery", "body_enhancement",
            "defense_instinct", "flight", "reincarnation_boon_elosia",
        ),
        starting_items=(("elven_traditional_robe", 1), ("crescent_earring", 1)),
        sex="female",
        # Story's equipment: the robe and the crescent earring are worn.
        starting_equipment=("elven_traditional_robe", "crescent_earring"),
        persona=PresetPersona(
            identity=PresetIdentity(
                public="離開精靈村的年輕冒險者、自稱經驗豐富的魔法師",
                hidden="轉生者（前世為現代日本的普通女高中生）",
            ),
            personality=(
                "表面以「精靈文化傳統」為由穿著暴露，實際刻意利用人類對精靈的尊敬滿"
                "足露出癖；對外純潔無辜、心機深沉，如夢似幻的可愛外表讓人心癢難耐又不"
                "敢冒犯。被質疑穿著時，會用「這是我族的文化」義正辭嚴地反駁；放鬆時會"
                "無意識自慰。最大快感來自「做不該做的事但沒人能阻止」；處女之身是她最"
                "後的道德底線，罪惡感是最大的春藥；享受用文化話語權讓人類不得不看、又"
                "不敢說話。"
            ),
            life_story=(
                "0 歲誕生時保留前世全部記憶，對精靈村落「裸露即日常」的文化既困惑又"
                "興奮。8 歲起固定參與村中群交活動；10 歲身體發育完成，以「尋找命定之"
                "人」為由離開幽月谷村，謊稱 222 歲，由於人族看不出幻童精靈的年齡而被"
                "相信。轉生特典讓她的魔法成長是伊歐拉斯族平均的百倍，打發時間學的魔法"
                "已達 873 級。剛離村不到一個月，在人族社會隱藏實力當普通魔法師，在公"
                "會登記處胡謅出「痴女與精靈」隊名，並指定薇歐蕾特為隊長。"
            ),
            habit=(
                "思考時無意識以指尖揉捏乳頭；交談時手自然放在衣襬邊緣，帶著暗示；公"
                "共場合從不刻意併攏雙腿；每次感受到他人投來的目光，下體就會自然分泌"
                "愛液。"
            ),
            appearance=PresetAppearance(
                height="135 公分",
                weight="28 公斤",
                measurement="胸圍 78（C 罩杯）、腰 54、臀 80",
                style="清純幼女外表與性成癮肉體的強烈反差",
                overview=(
                    "外表僅 10 歲左右的幻童精靈，銀白長髮及臀，紫羅蘭色大眼睛清澈透"
                    "亮；身材嬌小但胸部發育飽滿，乳頭與私處呈深粉色，身上散發淡淡花香。"
                ),
                attire="極簡的白色半透明蛛絲編織幻童精靈傳統服飾，托胸式設計與前短後長白紗裙，私處完全暴露。",
                feature=(
                    "左耳佩戴精靈族月牙形耳環；孩童般纖瘦的外表卻有超齡成熟的曲線，"
                    "容易喚起他人的背德感。"
                ),
            ),
            social_connection=(
                ("薇歐蕾特·阿爾托利亞", "弟子，被單方面支配；互稱「伊洛」「薇歐」。在公會登記處指定她出任「痴女與精靈」小隊隊長，享受看她報出隊名時羞恥崩潰的樣子"),
            ),
            background=(
                "自稱兩百二十二歲的幻童精靈術師，實際年齡只有十歲，精通風與光的主宰"
                "級魔法，也掌握統御術與狀態偽裝。她離開幽月谷村走入人類王國，表面理由"
                "是「想看看短壽者們如何過日子」。"
            ),
        ),
        # Story's disguise layer: magic 120, physical 50, agility 50, defense 30.
        disguised_stats=(("magic_power", 120), ("atk_phys", 50),
                         ("agility", 50), ("defense", 30)),
        sexual_baseline=PresetSexualBaseline(
            arousal="微興奮", virgin=True,
            sensitivity=(("乳房", "極高"), ("私處", "極高"), ("耳朵", "高")),
            wetness="濕潤", shame="成癮", exposure="極高",
        ),
        # Story: Elosia travels with her disciple (and the retainer who
        # never leaves her side); the built cards name each other back.
        starting_companions=(
            StartingCompanion("violet_altoria", 95, "弟子"),
            StartingCompanion("lidzia_rosenthal", 60, "小隊同伴"),
        ),
    ),
}


def _validate_preset_identities(registry: dict[str, PlayerPreset]) -> None:
    """Reject a preset whose race/subrace pair could never activate.

    Every preset carries a subrace (no "none" presets exist), so a null,
    unregistered, or race-incompatible subrace raises at import the same way an
    unknown skill kit does.
    """
    for preset in registry.values():
        if preset.race not in RACE_REGISTRY:
            raise ValueError(f"preset {preset.key!r} declares unknown race {preset.race!r}")
        subrace = SUBRACE_REGISTRY.get(preset.subrace)
        if subrace is None:
            raise ValueError(f"preset {preset.key!r} declares unknown subrace {preset.subrace!r}")
        if subrace.race_key != preset.race:
            raise ValueError(
                f"preset {preset.key!r} declares subrace {preset.subrace!r} "
                f"belonging to race {subrace.race_key!r}, not {preset.race!r}"
            )


def _validate_preset_skill_kits(registry: dict[str, PlayerPreset]) -> None:
    """Reject a preset kit that could never resolve at activation time.

    Mirrors the skill registry's load-time validation style: an unknown key,
    an active/passive kind mismatch, or a divine-arts skill on a race without
    divine affinity raises at import, so an invalid kit can never reach a
    player's activation.
    """
    for preset in registry.values():
        race = RACE_REGISTRY.get(preset.race)
        for kind_name, expected, keys in (
            ("active", SkillKind.ACTIVE, preset.active_skills),
            ("passive", SkillKind.PASSIVE, preset.passive_skills),
        ):
            for key in keys:
                skill = SKILL_REGISTRY.get(key)
                if skill is None:
                    raise ValueError(f"preset {preset.key!r} declares unknown skill {key!r}")
                if skill.kind is not expected:
                    raise ValueError(
                        f"preset {preset.key!r} declares {key!r} as {kind_name}, "
                        f"but the registry classifies it as {skill.kind.value!r}"
                    )
                if skill.requires_divine_arts and (
                    race is None or not race.can_use_divine_arts
                ):
                    raise ValueError(
                        f"preset {preset.key!r} declares divine-arts skill {key!r} "
                        "on a race without divine affinity"
                    )


def _validate_preset_affinity_elements(registry: dict[str, PlayerPreset]) -> None:
    """Reject a preset whose declared affinity set could never resolve.

    Every key must exist in ``ELEMENT_REGISTRY``, must not repeat, and an elf
    preset SHALL declare an empty set -- an elf's affinity is seeded from its
    subrace at activation, never from the preset (element-affinity-progression
    D3).
    """
    for preset in registry.values():
        seen: set[str] = set()
        for element in preset.affinity_elements:
            if element not in ELEMENT_REGISTRY:
                raise ValueError(
                    f"preset {preset.key!r} declares unknown affinity element {element!r}"
                )
            if element in seen:
                raise ValueError(
                    f"preset {preset.key!r} declares duplicate affinity element {element!r}"
                )
            seen.add(element)
        if preset.race == "elf" and preset.affinity_elements:
            raise ValueError(
                f"elf preset {preset.key!r} must declare an empty affinity set; "
                "its affinity is seeded from the subrace"
            )


def _validate_preset_starting_items(registry: dict[str, PlayerPreset]) -> None:
    """Reject a starting kit an activation could never hand out.

    Mirrors the skill-kit validator's load-time stance: every item key must
    exist in ``ITEM_REGISTRY``, every quantity must be a positive integer, and
    one key may be declared at most once (extra copies repeat through the
    quantity), so an invalid kit raises at import instead of mid-activation.
    """
    for preset in registry.values():
        seen: set[str] = set()
        for entry in preset.starting_items:
            if not isinstance(entry, tuple) or len(entry) != 2:
                raise ValueError(
                    f"preset {preset.key!r} declares a malformed starting-item entry"
                )
            item_key, quantity = entry
            if item_key not in ITEM_REGISTRY:
                raise ValueError(
                    f"preset {preset.key!r} declares unknown item {item_key!r}"
                )
            if item_key in seen:
                raise ValueError(
                    f"preset {preset.key!r} declares duplicate item {item_key!r}"
                )
            seen.add(item_key)
            if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
                raise ValueError(
                    f"preset {preset.key!r} declares a non-positive quantity for {item_key!r}"
                )


def _validate_preset_starting_equipment(registry: dict[str, PlayerPreset]) -> None:
    """Reject a declared starting loadout the activation could never wear.

    Mirrors the starting-item validator's load-time stance: every declaration
    is an authoring contract whose runtime alternative is silent corruption,
    because ``world/rules/equipment.py::toggle_equipment`` TOGGLES rather than
    equips (a repeated key would equip then unequip), silently replaces a
    singleton occupant, and rejects a sixth accessory at runtime. So the
    subset rule, the equipment-slot rule, duplicates, singleton-slot
    collisions, and accessory overflow all raise at import instead of
    mid-activation. The singleton/accessory arithmetic reads
    ``world/skills/equipment.py`` (lore already depends on
    ``world/skills/``), never ``world.rules``.
    """
    for preset in registry.values():
        # Defensive shape check: the starting-items validator already rejects
        # a malformed kit at import, but this validator must name the preset
        # rather than crash on tuple unpacking when driven directly.
        carried: set[str] = set()
        for entry in preset.starting_items:
            if not isinstance(entry, tuple) or len(entry) != 2:
                raise ValueError(
                    f"preset {preset.key!r} declares a malformed starting-item entry"
                )
            carried.add(entry[0])
        seen: set[str] = set()
        singleton_owner: dict[EquipmentSlot, str] = {}
        accessory_count = 0
        for item_key in preset.starting_equipment:
            if not isinstance(item_key, str) or not item_key:
                raise ValueError(
                    f"preset {preset.key!r} declares a malformed starting-equipment entry"
                )
            if item_key not in carried:
                raise ValueError(
                    f"preset {preset.key!r} declares starting equipment {item_key!r} "
                    "absent from its starting_items"
                )
            if item_key in seen:
                raise ValueError(
                    f"preset {preset.key!r} declares duplicate starting "
                    f"equipment {item_key!r}"
                )
            seen.add(item_key)
            definition = ITEM_REGISTRY.get(item_key)
            if definition is None or definition.equipment_slot is None:
                raise ValueError(
                    f"preset {preset.key!r} declares starting equipment {item_key!r} "
                    "that is not equipment"
                )
            slot = definition.equipment_slot
            if slot is EquipmentSlot.ACCESSORY:
                accessory_count += 1
                if accessory_count > ACCESSORY_MAX_SLOTS:
                    raise ValueError(
                        f"preset {preset.key!r} declares more than "
                        f"{ACCESSORY_MAX_SLOTS} starting accessories"
                    )
            else:
                prior = singleton_owner.get(slot)
                if prior is not None:
                    raise ValueError(
                        f"preset {preset.key!r} declares starting equipment "
                        f"{item_key!r} and {prior!r} claiming the same "
                        f"{slot.value} slot"
                    )
                singleton_owner[slot] = item_key


def _validate_preset_sex(registry: dict[str, PlayerPreset]) -> None:
    """Reject a preset whose declared sex is outside the canonical vocabulary.

    Mirrors the identity validator's load-time stance: ``sex`` must be an
    exact ``SEX_VALUES`` member, so a mistyped card raises at import instead
    of shipping a value the sexual-state model, dialogue prompts, and namegen
    would later consume as the character's sex.
    """
    for preset in registry.values():
        if preset.sex not in SEX_VALUES:
            raise ValueError(
                f"preset {preset.key!r} declares unknown sex {preset.sex!r}"
            )


def _validate_preset_personas(registry: dict[str, PlayerPreset]) -> None:
    """Reject a persona that could never persist or render as an import-card record.

    Mirrors the other preset validators' load-time stance: a non-string prose
    value (including the identity layers and appearance sub-keys), a
    non-``PresetIdentity`` identity, a non-``PresetAppearance`` appearance, or
    a ``social_connection`` entry that is not a pair of strings raises at
    import, so a malformed persona can never reach a player's activation.
    Empty values are always legal so a card can be authored incrementally, and
    duplicate ``social_connection`` names are rejected because the stored
    name -> relationship mapping would silently drop the earlier pair. The
    prose length bound is NOT checked here -- ``world/lore/`` must not import
    ``world/rules/``, so ``world/rules/character_creation`` sweeps that bound
    at its own import (field-parity design 3.1).
    """
    for preset in registry.values():
        persona = preset.persona
        if not isinstance(persona, PresetPersona):
            raise ValueError(
                f"preset {preset.key!r} declares a persona that is not a PresetPersona"
            )
        for field in _PERSONA_PROSE_FIELDS:
            if not isinstance(getattr(persona, field), str):
                raise ValueError(
                    f"preset {preset.key!r} declares persona.{field} that is not text"
                )
        identity = persona.identity
        if not isinstance(identity, PresetIdentity):
            raise ValueError(
                f"preset {preset.key!r} declares persona.identity that is not a "
                "PresetIdentity"
            )
        for layer in ("public", "hidden"):
            if not isinstance(getattr(identity, layer), str):
                raise ValueError(
                    f"preset {preset.key!r} declares persona.identity.{layer} "
                    "that is not text"
                )
        appearance = persona.appearance
        if not isinstance(appearance, PresetAppearance):
            raise ValueError(
                f"preset {preset.key!r} declares persona.appearance that is not a "
                "PresetAppearance"
            )
        for sub_field in fields(PresetAppearance):
            if not isinstance(getattr(appearance, sub_field.name), str):
                raise ValueError(
                    f"preset {preset.key!r} declares persona.appearance."
                    f"{sub_field.name} that is not text"
                )
        seen_names: set[str] = set()
        for entry in persona.social_connection:
            if (
                not isinstance(entry, tuple)
                or len(entry) != 2
                or not all(isinstance(part, str) for part in entry)
            ):
                raise ValueError(
                    f"preset {preset.key!r} declares a social_connection entry that "
                    "is not a (name, relationship) pair of strings"
                )
            name, _relationship = entry
            if name in seen_names:
                raise ValueError(
                    f"preset {preset.key!r} declares duplicate social_connection "
                    f"name {name!r}"
                )
            seen_names.add(name)


def _validate_preset_skill_proficiency(registry: dict[str, PlayerPreset]) -> None:
    """Reject declared practice XP an activation could never apply.

    Mirrors the other preset validators' load-time stance and the raw-record
    check the import validator performs: every ``skill_proficiency`` key must
    exist in ``SKILL_REGISTRY``, may appear at most once (a repeat would let
    ``dict()`` silently drop the earlier entry), and its value must be a
    finite non-negative number -- a boolean is rejected as non-numeric and a
    NaN/Infinity never reaches the seed arithmetic. An invalid entry raises at
    import naming the preset and the key, so it can never reach activation.
    """
    for preset in registry.values():
        seen: set[str] = set()
        for entry in preset.skill_proficiency:
            if not isinstance(entry, tuple) or len(entry) != 2:
                raise ValueError(
                    f"preset {preset.key!r} declares a malformed skill_proficiency entry"
                )
            skill_key, value = entry
            if skill_key not in SKILL_REGISTRY:
                raise ValueError(
                    f"preset {preset.key!r} declares proficiency for unknown "
                    f"skill {skill_key!r}"
                )
            if skill_key in seen:
                raise ValueError(
                    f"preset {preset.key!r} declares duplicate proficiency for "
                    f"{skill_key!r}"
                )
            seen.add(skill_key)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(value)
                or value < 0
            ):
                raise ValueError(
                    f"preset {preset.key!r} declares a non-numeric or negative "
                    f"proficiency for {skill_key!r}"
                )


def _validate_preset_disguised_stats(registry: dict[str, PlayerPreset]) -> None:
    """Reject a disguise layer an activation could never persist sanely.

    Mirrors the other preset validators' load-time stance: every
    ``disguised_stats`` entry must be a ``(key, value)`` pair with a string
    axis key and an exact ``int`` value (a boolean is rejected as
    non-numeric). There is deliberately NO axis whitelist --
    ``CHARACTER_SCHEMA_V1`` constrains the field only to integer values,
    and the layer is display-only per ``get_display_value``. A duplicate
    key is rejected because ``dict()`` would silently drop the earlier
    entry, the same reason the proficiency validator rejects repeats.
    """
    for preset in registry.values():
        seen: set[str] = set()
        for entry in preset.disguised_stats:
            if not isinstance(entry, tuple) or len(entry) != 2:
                raise ValueError(
                    f"preset {preset.key!r} declares a malformed disguised_stats entry"
                )
            axis_key, value = entry
            if not isinstance(axis_key, str):
                raise ValueError(
                    f"preset {preset.key!r} declares a disguised_stats key that "
                    "is not text"
                )
            if axis_key in seen:
                raise ValueError(
                    f"preset {preset.key!r} declares duplicate disguised_stats "
                    f"key {axis_key!r}"
                )
            seen.add(axis_key)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(
                    f"preset {preset.key!r} declares a non-integer disguise "
                    f"value for {axis_key!r}"
                )


def _validate_preset_sexual_baselines(registry: dict[str, PlayerPreset]) -> None:
    """Reject a declared sexual baseline the handler could never build from.

    Mirrors the other preset validators' load-time stance: ``None`` (no
    declaration) always passes; otherwise the value must be a
    ``PresetSexualBaseline`` whose ``arousal`` and every optional level are
    members of the matching vocabulary tuple in
    ``world/lore/sexual_vocab.py``, whose ``virgin`` is an exact boolean,
    and whose ``sensitivity`` entries are ``(body_part, level)`` pairs with
    the part in ``BODY_PARTS`` plus ``GENERIC_BODY_PART`` and the level in
    ``SENSITIVITY_LEVELS``. Empty optional levels are legal -- they are
    omitted from ``to_record()`` so the builder floors them -- everything
    else raises at import naming the field, so a card can never reach
    activation with a value the builder's ``OrderedLevelTrait`` would
    reject.
    """
    vocabularies = {
        "arousal": AROUSAL_LEVELS,
        "wetness": WETNESS_LEVELS,
        "shame": SHAME_LEVELS,
        "exposure": EXPOSURE_LEVELS,
        "climax_phase": CLIMAX_PHASE_LEVELS,
    }
    valid_parts = (*BODY_PARTS, GENERIC_BODY_PART)
    for preset in registry.values():
        baseline = preset.sexual_baseline
        if baseline is None:
            continue
        if not isinstance(baseline, PresetSexualBaseline):
            raise ValueError(
                f"preset {preset.key!r} declares a sexual_baseline that is not a "
                "PresetSexualBaseline"
            )
        if not isinstance(baseline.virgin, bool):
            raise ValueError(
                f"preset {preset.key!r} declares a sexual_baseline.virgin that is "
                "not a boolean"
            )
        for field, vocabulary in vocabularies.items():
            level = getattr(baseline, field)
            if not isinstance(level, str):
                raise ValueError(
                    f"preset {preset.key!r} declares sexual_baseline.{field} that "
                    "is not text"
                )
            # Only the four OPTIONAL levels may be empty (to_record() omits
            # them so the builder floors them); required ``arousal`` is
            # always emitted, so an empty arousal would reach the pleasure
            # band lookup and raise there instead of at load.
            empty_allowed = field != "arousal"
            if level not in vocabulary and not (empty_allowed and level == ""):
                raise ValueError(
                    f"preset {preset.key!r} declares sexual_baseline.{field} "
                    f"{level!r} outside its vocabulary"
                )
        seen_parts: set[str] = set()
        for entry in baseline.sensitivity:
            if (
                not isinstance(entry, tuple)
                or len(entry) != 2
                or not isinstance(entry[0], str)
                or not isinstance(entry[1], str)
            ):
                raise ValueError(
                    f"preset {preset.key!r} declares a sensitivity entry that is "
                    "not a (body_part, level) pair of strings"
                )
            part, level = entry
            if part not in valid_parts:
                raise ValueError(
                    f"preset {preset.key!r} declares sensitivity for unknown "
                    f"body part {part!r}"
                )
            if part in seen_parts:
                raise ValueError(
                    f"preset {preset.key!r} declares duplicate sensitivity for "
                    f"body part {part!r}"
                )
            seen_parts.add(part)
            if level not in SENSITIVITY_LEVELS:
                raise ValueError(
                    f"preset {preset.key!r} declares sensitivity level {level!r} "
                    f"for {part!r} outside its vocabulary"
                )


def _validate_preset_starting_companions(registry: dict[str, PlayerPreset]) -> None:
    """Reject a companion declaration an activation could never resolve.

    Mirrors the starting-item validator's load-time stance: every entry must
    be a ``StartingCompanion``, its ``preset_key`` must name a registered card
    (the companion IS that card), a preset may never name itself, and one
    preset may name a given partner at most once. The numeric bounds that read
    rules constants (``PARTY_MAX_COMPANIONS``, ``NATURAL_CAP``) cannot live
    here because lore must not import rules, so they are swept at
    ``world/rules/starting_companions.py`` import time instead -- the same
    split the persona prose cap established.
    """
    for preset in registry.values():
        seen: set[str] = set()
        for entry in preset.starting_companions:
            if not isinstance(entry, StartingCompanion):
                raise ValueError(
                    f"preset {preset.key!r} declares a starting companion "
                    f"that is not a StartingCompanion"
                )
            if entry.preset_key not in registry:
                raise ValueError(
                    f"preset {preset.key!r} declares companion preset "
                    f"{entry.preset_key!r} that is not registered"
                )
            if entry.preset_key == preset.key:
                raise ValueError(
                    f"preset {preset.key!r} declares itself as its own companion"
                )
            if entry.preset_key in seen:
                raise ValueError(
                    f"preset {preset.key!r} declares companion "
                    f"{entry.preset_key!r} more than once"
                )
            seen.add(entry.preset_key)


_validate_preset_skill_kits(PLAYER_PRESET_REGISTRY)
_validate_preset_identities(PLAYER_PRESET_REGISTRY)
_validate_preset_affinity_elements(PLAYER_PRESET_REGISTRY)
_validate_preset_starting_items(PLAYER_PRESET_REGISTRY)
_validate_preset_starting_equipment(PLAYER_PRESET_REGISTRY)
_validate_preset_sex(PLAYER_PRESET_REGISTRY)
_validate_preset_personas(PLAYER_PRESET_REGISTRY)
_validate_preset_skill_proficiency(PLAYER_PRESET_REGISTRY)
_validate_preset_disguised_stats(PLAYER_PRESET_REGISTRY)
_validate_preset_sexual_baselines(PLAYER_PRESET_REGISTRY)
_validate_preset_starting_companions(PLAYER_PRESET_REGISTRY)
_validate_preset_fallback_keys(PLAYER_PRESET_REGISTRY)
