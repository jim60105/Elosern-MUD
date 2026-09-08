"""Immutable starter characters offered during account registration."""

from dataclasses import KW_ONLY, asdict, dataclass, fields
from math import isfinite
from typing import Any

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


PLAYER_PRESET_REGISTRY: dict[str, PlayerPreset] = {
    "human_wanderer": PlayerPreset(
        "human_wanderer", "艾琳", 24, 24, "human", "human_commoner",
        (("hp", 50), ("mp", 50), ("sp", 50), ("atk_phys", 10),
         ("agility", 10), ("defense", 11), ("magic_power", 43)),
        "生命力與魔力均衡的開局配點",
        active_skills=("light_sword_style",),
        passive_skills=("body_enhancement_basic",),
        starting_items=(("plain_sword", 1), ("leather_armor", 1),
                        ("guild_recruit_badge", 1), ("healing_potion", 2),
                        ("healing_herb", 2)),
        sex="female",
        persona=PresetPersona(
            background=(
                "來自南境的年輕旅人，腰間掛著一把磨亮的長劍，追逐著地圖邊緣未標記的空白。"
                "剛在公會登記為新人冒險者，均衡的劍術與基礎強化讓她對什麼委託都躍躍欲試。"
            ),
        ),
    ),
    "foxkin_scout": PlayerPreset(
        "foxkin_scout", "露芙", 22, 22, "beastfolk", "foxkin",
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
        persona=PresetPersona(
            background=(
                "出身獸王國瓦爾哈拉的狐人斥候，身手矯健，習慣走在隊伍前方探路。"
                "疾風術與瞬步是她的雙腿，總能在危險降臨之前，先把消息帶回夥伴身邊。"
            ),
        ),
    ),
    "elf_guardian": PlayerPreset(
        "elf_guardian", "瑟芮雅", 180, 24, "elf", "fionnen",
        (("hp", 0), ("mp", 0), ("sp", 0), ("atk_phys", 12),
         ("agility", 12), ("defense", 13), ("magic_power", 400)),
        "防禦與均衡戰技優先的守護者配點",
        active_skills=("hardened_skin",),
        passive_skills=("defense_instinct", "elf_longevity"),
        starting_items=(("knight_blade", 1), ("iron_shield", 1),
                        ("chainmail", 1), ("pilgrim_medallion", 1),
                        ("healing_potion", 1)),
        sex="female",
        persona=PresetPersona(
            background=(
                "斐歐恩森林出身的精靈族護衛，以長壽的眼光看待短暫的人類王國。"
                "硬化肌膚與防禦直覺讓她成為隊伍最可靠的盾，守護他人的意志遠勝於爭勝之心。"
            ),
        ),
    ),
    "violet_altoria": PlayerPreset(
        "violet_altoria", "薇歐蕾特", 18, 18, "human", "human_royal",
        (("hp", 50), ("mp", 67), ("sp", 50), ("atk_phys", 4),
         ("agility", 5), ("defense", 5), ("magic_power", 43)),
        "魔力優先、體力與生命力兼顧的術師配點",
        active_skills=("fire_ball", "wind_blade"),
        passive_skills=(
            "magic_circle_comprehension", "precise_mana_control", "flight",
        ),
        affinity_elements=("fire", "wind"),
        starting_items=(("elven_traditional_robe", 1), ("royal_signet_ring", 1),
                        ("royal_heirloom_pendant", 1)),
        sex="female",
        persona=PresetPersona(
            background=(
                "阿爾托利亞王國的第一王女，成年禮後以風之術師的身份離開宮廷歷練。"
                "過人的魔法陣理解與精準魔力控制，讓她的火球與風刃遠超同齡術師，"
                "飛行術則使她習慣從高處俯瞰世界。"
            ),
        ),
    ),
    "lidzia_rosenthal": PlayerPreset(
        "lidzia_rosenthal", "莉茲婭", 18, 18, "human", "human_noble",
        (("hp", 55), ("mp", 39), ("sp", 60), ("atk_phys", 9),
         ("agility", 10), ("defense", 8), ("magic_power", 43)),
        "體力與生命力優先、均衡的近侍劍術配點",
        active_skills=("light_sword_style",),
        passive_skills=("retainer_martial_training", "guardian_instinct"),
        starting_items=(("rose_crest_rapier", 1), ("black_maid_dress", 1),
                        ("silver_feather_earring", 1)),
        sex="female",
        persona=PresetPersona(
            background=(
                "世代侍奉王室的羅森塔爾家族之女，薇歐蕾特王女的貼身近侍。"
                "輕劍術在護衛考核名列前茅，隨從武藝與護主本能，使她永遠站在主人與危險之間。"
            ),
        ),
    ),
    "yuka_darknight": PlayerPreset(
        "yuka_darknight", "悠花", 18, 18, "elf", "ciaran",
        (("hp", 0), ("mp", 0), ("sp", 0), ("atk_phys", 11),
         ("agility", 14), ("defense", 12), ("magic_power", 400)),
        "敏捷與攻擊優先的雙刀配點",
        active_skills=("dual_blade_mastery", "shadow_slash"),
        passive_skills=(
            "dual_wield_style", "blade_art_mastery", "extreme_endurance",
            "body_enhancement_extreme", "reincarnation_boon_yuka",
        ),
        starting_items=(("shadow_blade", 1), ("shadow_blade_echo", 1),
                        ("dark_elf_ninja_garb", 1)),
        sex="female",
        persona=PresetPersona(
            background=(
                "暗影谷村出身的黑暗精靈雙刀使，罕見的黑短髮在銀髮同族中格外醒目。"
                "宗師級雙刀流與影斬令她名聲在外，轉生祝福的武感使她總能先一步抵達對手要害。"
                "陽光開朗，視戰鬥為與自身極限的對話。"
            ),
        ),
        # The twins arrive together: 悠花's own card is her companion, seeded
        # at 95 (above the invite threshold, inside 至愛 with headroom), with
        # 悠奈 as the elder sister.
        starting_companions=(StartingCompanion("yuna_darknight", 95, "雙胞胎姊姊"),),
    ),
    "yuna_darknight": PlayerPreset(
        "yuna_darknight", "悠奈", 18, 18, "elf", "ciaran",
        (("hp", 0), ("mp", 0), ("sp", 0), ("atk_phys", 6),
         ("agility", 6), ("defense", 25), ("magic_power", 400)),
        "防禦特化的魔力體質配點",
        active_skills=("divine_sexual_arts",),
        passive_skills=(
            "fire_mastery", "dark_mastery", "divine_sexual_mastery",
            "reincarnation_boon_yuna",
        ),
        starting_items=(("dark_elf_kimono", 1),),
        sex="female",
        persona=PresetPersona(
            background=(
                "與雙胞胎妹妹一同離開暗影谷村的黑暗精靈，罕見的黑長髮與知性外表之下，"
                "是將性魔法鑽研到極致的享樂主義者。精通火與闇屬性，"
                "並以神之秘法觸及性愛系統的領域。"
            ),
        ),
        # The symmetric half of the pair: 悠奈 arrives with 悠花, the younger
        # twin, at the same affinity.
        starting_companions=(StartingCompanion("yuka_darknight", 95, "雙胞胎妹妹"),),
    ),
    "elosia_shadowmoon": PlayerPreset(
        "elosia_shadowmoon", "伊洛希雅", 222, 24, "elf", "fionnen",
        (("hp", 0), ("mp", 0), ("sp", 0), ("atk_phys", 10),
         ("agility", 10), ("defense", 17), ("magic_power", 400)),
        "防禦紮實、攻守均衡的魔導師配點",
        active_skills=("dominion_art", "status_disguise"),
        passive_skills=(
            "wind_mastery", "light_mastery", "body_enhancement",
            "reincarnation_boon_elosia",
        ),
        starting_items=(("elven_traditional_robe", 1), ("crescent_earring", 1)),
        sex="female",
        persona=PresetPersona(
            background=(
                "自稱兩百二十二歲的森林精靈術師，精通風與光的主宰級魔法，"
                "也掌握統御術與狀態偽裝。她離開斐歐恩村落走入人類王國，"
                "理由是「想看看短壽者們如何過日子」。"
            ),
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
