"""Immutable starter characters offered during account registration."""

from dataclasses import dataclass

from world.lore.elements import ELEMENT_REGISTRY
from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY
from world.skills.registry import SKILL_REGISTRY, SkillKind


@dataclass(frozen=True)
class PlayerPreset:
    """A complete player-owned identity, raw stat allocation, and skill kit."""

    key: str
    display_name: str
    age: int
    apparent_age: int
    race: str
    subrace: str
    allocations: tuple[tuple[str, int], ...]
    emphasis: str
    background: str
    active_skills: tuple[str, ...] = ()
    passive_skills: tuple[str, ...] = ()
    affinity_elements: tuple[str, ...] = ()

    def allocation_dict(self) -> dict[str, int]:
        """Return a mutable copy suitable for rules validation."""
        return dict(self.allocations)

    def skill_lists(self) -> dict[str, list[str]]:
        """Return the storage shape for the character ``skills`` attribute."""
        return {"active": list(self.active_skills), "passive": list(self.passive_skills)}


PLAYER_PRESET_REGISTRY: dict[str, PlayerPreset] = {
    "human_wanderer": PlayerPreset(
        "human_wanderer", "艾琳", 24, 24, "human", "human_commoner",
        (("hp", 50), ("mp", 50), ("sp", 50), ("atk_phys", 10),
         ("agility", 10), ("defense", 11)),
        "生命力與魔力均衡的開局配點",
        "來自南境的年輕旅人，腰間掛著一把磨亮的長劍，追逐著地圖邊緣未標記的空白。"
        "剛在公會登記為新人冒險者，均衡的劍術與基礎強化讓她對什麼委託都躍躍欲試。",
        ("light_sword_style",),
        ("body_enhancement_basic",),
    ),
    "foxkin_scout": PlayerPreset(
        "foxkin_scout", "露芙", 22, 22, "beastfolk", "foxkin",
        (("hp", 25), ("mp", 10), ("sp", 25), ("atk_phys", 15),
         ("agility", 15), ("defense", 15)),
        "敏捷與近身作戰優先的斥候配點",
        "出身獸王國瓦爾哈拉的狐人斥候，身手矯健，習慣走在隊伍前方探路。"
        "疾風術與瞬步是她的雙腿，總能在危險降臨之前，先把消息帶回夥伴身邊。",
        ("gale_step",),
        ("flash_step",),
        ("wind",),
    ),
    "elf_guardian": PlayerPreset(
        "elf_guardian", "瑟芮雅", 180, 24, "elf", "fionnen",
        (("hp", 0), ("mp", 0), ("sp", 0), ("atk_phys", 12),
         ("agility", 12), ("defense", 13)),
        "防禦與均衡戰技優先的守護者配點",
        "斐歐恩森林出身的精靈族護衛，以長壽的眼光看待短暫的人類王國。"
        "硬化肌膚與防禦直覺讓她成為隊伍最可靠的盾，守護他人的意志遠勝於爭勝之心。",
        ("hardened_skin",),
        ("defense_instinct", "elf_longevity"),
    ),
    "violet_altoria": PlayerPreset(
        "violet_altoria", "薇歐蕾特", 18, 18, "human", "human_royal",
        (("hp", 50), ("mp", 67), ("sp", 50), ("atk_phys", 4),
         ("agility", 5), ("defense", 5)),
        "魔力優先、體力與生命力兼顧的術師配點",
        "阿爾托利亞王國的第一王女，成年禮後以風之術師的身份離開宮廷歷練。"
        "過人的魔法陣理解與精準魔力控制，讓她的火球與風刃遠超同齡術師，"
        "飛行術則使她習慣從高處俯瞰世界。",
        ("fire_ball", "wind_blade"),
        ("magic_circle_comprehension", "precise_mana_control", "flight"),
        ("fire", "wind"),
    ),
    "lidzia_rosenthal": PlayerPreset(
        "lidzia_rosenthal", "莉茲婭", 18, 18, "human", "human_noble",
        (("hp", 55), ("mp", 39), ("sp", 60), ("atk_phys", 9),
         ("agility", 10), ("defense", 8)),
        "體力與生命力優先、均衡的近侍劍術配點",
        "世代侍奉王室的羅森塔爾家族之女，薇歐蕾特王女的貼身近侍。"
        "輕劍術在護衛考核名列前茅，隨從武藝與護主本能，使她永遠站在主人與危險之間。",
        ("light_sword_style",),
        ("retainer_martial_training", "guardian_instinct"),
    ),
    "yuka_darknight": PlayerPreset(
        "yuka_darknight", "悠花", 18, 18, "elf", "ciaran",
        (("hp", 0), ("mp", 0), ("sp", 0), ("atk_phys", 11),
         ("agility", 14), ("defense", 12)),
        "敏捷與攻擊優先的雙刀配點",
        "暗影谷村出身的黑暗精靈雙刀使，罕見的黑短髮在銀髮同族中格外醒目。"
        "宗師級雙刀流與影斬令她名聲在外，轉生祝福的武感使她總能先一步抵達對手要害。"
        "陽光開朗，視戰鬥為與自身極限的對話。",
        ("dual_wield_style", "dual_blade_mastery", "shadow_slash"),
        ("blade_art_mastery", "extreme_endurance", "body_enhancement_extreme",
         "reincarnation_boon_yuka"),
    ),
    "yuna_darknight": PlayerPreset(
        "yuna_darknight", "悠奈", 18, 18, "elf", "ciaran",
        (("hp", 0), ("mp", 0), ("sp", 0), ("atk_phys", 6),
         ("agility", 6), ("defense", 25)),
        "防禦特化的魔力體質配點",
        "與雙胞胎妹妹一同離開暗影谷村的黑暗精靈，罕見的黑長髮與知性外表之下，"
        "是將性魔法鑽研到極致的享樂主義者。精通火與闇屬性，"
        "並以神之秘法觸及性愛系統的領域。",
        ("divine_sexual_arts",),
        ("fire_mastery", "dark_mastery", "divine_sexual_mastery",
         "reincarnation_boon_yuna"),
    ),
    "elosia_shadowmoon": PlayerPreset(
        "elosia_shadowmoon", "伊洛希雅", 222, 24, "elf", "fionnen",
        (("hp", 0), ("mp", 0), ("sp", 0), ("atk_phys", 10),
         ("agility", 10), ("defense", 17)),
        "防禦紮實、攻守均衡的魔導師配點",
        "自稱兩百二十二歲的森林精靈術師，精通風與光的主宰級魔法，"
        "也掌握統御術與狀態偽裝。她離開斐歐恩村落走入人類王國，"
        "理由是「想看看短壽者們如何過日子」。",
        ("dominion_art", "status_disguise"),
        ("wind_mastery", "light_mastery", "body_enhancement",
         "reincarnation_boon_elosia"),
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
                        f"on a race without divine affinity"
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


_validate_preset_skill_kits(PLAYER_PRESET_REGISTRY)
_validate_preset_identities(PLAYER_PRESET_REGISTRY)
_validate_preset_affinity_elements(PLAYER_PRESET_REGISTRY)
