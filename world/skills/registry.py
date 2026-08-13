"""Skill definitions from design section 5.2 and ``skills-equipment``.

``SkillKind`` and ``TargetSpec`` are forward declarations for change 8's
action resolver to import rather than redefine. Every ``effects`` string is
parsed into a typed dataclass by ``world.skills.effects.parse_effect`` at
construction; see that module for the recognized effect-ID conventions.
"""

from dataclasses import dataclass
from enum import StrEnum

from world.lore.elements import ELEMENT_REGISTRY, Element
from world.skills.effects import HealEffect, parse_effect


class _FrozenDict(dict):
    """A ``dict`` preserving the exact field contract without mutation."""

    def _immutable(self, *args, **kwargs):
        raise TypeError("skill definition collections are immutable")

    __delitem__ = _immutable
    __ior__ = _immutable
    __setitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable


class _FrozenList(list):
    """A ``list`` preserving the exact field contract without mutation."""

    def _immutable(self, *args, **kwargs):
        raise TypeError("skill definition collections are immutable")

    __delitem__ = _immutable
    __iadd__ = _immutable
    __imul__ = _immutable
    __setitem__ = _immutable
    append = _immutable
    clear = _immutable
    extend = _immutable
    insert = _immutable
    pop = _immutable
    remove = _immutable
    reverse = _immutable
    sort = _immutable


class SkillKind(StrEnum):
    """Whether a skill is invoked or continuously owned."""

    ACTIVE = "active"
    PASSIVE = "passive"


class TargetSpec(StrEnum):
    """The target cardinality expected by the future action resolver."""

    NONE = "none"
    SELF = "self"
    SINGLE = "single"
    AREA = "area"


class FactionConstraint(StrEnum):
    """Relations a skill permits the resolver to target.

    ``ANY`` (the default) and ``SELF_ONLY`` are the only constraints shipped
    content may declare: every attack and recovery skill is freely targetable
    among enemies and allies, while a self-only effect restricts its target to
    the actor. ``ALLY`` and ``ENEMY`` are retained as enum values for legacy
    test data; no skill declares them.
    """

    ANY = "any"
    ALLY = "ally"
    ENEMY = "enemy"
    SELF_ONLY = "self_only"


# Presentation metadata bounds shared by every immutable skill definition.
LABEL_MAX = 128
DESCRIPTION_MAX = 512


@dataclass(frozen=True)
class SkillDef:
    """Immutable definition of a skill known to deterministic consumers."""

    key: str
    label: str
    description: str
    kind: SkillKind
    target_spec: TargetSpec
    cost: dict[str, int]
    usable_out_of_combat: bool
    element: Element | None
    effects: list[str]
    faction_constraint: FactionConstraint = FactionConstraint.ANY
    requires_divine_arts: bool = False
    parsed_effects: tuple = ()

    def __post_init__(self) -> None:
        """Enforce the registry invariants for every constructor path.

        Direct ``SkillDef(...)`` construction (for example the production
        ``flee`` definition) must observe the same bounded presentation
        metadata and the same immutable collection contract as the seed
        builder, so no runtime code can mutate a registered definition.
        Every effect string must parse under the typed dispatch table; an
        unrecognized prefix raises here (registry-load time), not at use.
        """
        _validate_metadata(self.label, self.description)
        object.__setattr__(self, "cost", _FrozenDict(self.cost))
        object.__setattr__(self, "effects", _FrozenList(self.effects))
        object.__setattr__(
            self,
            "parsed_effects",
            tuple(parse_effect(effect_id) for effect_id in self.effects),
        )
        self._validate_heal_shape()

    def _validate_heal_shape(self) -> None:
        """Reject a heal shape that contradicts the skill's target spec.

        ``heal:<shape>`` names the cardinality the skill may declare: a single
        heal fits SINGLE or SELF skills, an area heal only AREA skills. Without
        this check the two shapes behave identically (the handler heals whatever
        the pipeline resolved), silently ignoring the declared shape at use time
        — the same class of failure the typed-effect dispatch eliminates.
        """
        for effect in self.parsed_effects:
            if not isinstance(effect, HealEffect):
                continue
            if effect.shape == "single" and self.target_spec not in (
                TargetSpec.SINGLE,
                TargetSpec.SELF,
            ):
                raise ValueError(
                    f"heal:single requires a SINGLE or SELF skill, "
                    f"{self.key!r} declares {self.target_spec.value!r}"
                )
            if effect.shape == "area" and self.target_spec is not TargetSpec.AREA:
                raise ValueError(
                    f"heal:area requires an AREA skill, "
                    f"{self.key!r} declares {self.target_spec.value!r}"
                )


def _validate_metadata(label: str, description: str) -> None:
    """Reject empty or oversized player-facing presentation metadata."""
    if not isinstance(label, str) or not label.strip():
        raise ValueError("skill label must be a non-empty string")
    if not isinstance(description, str) or not description.strip():
        raise ValueError("skill description must be a non-empty string")
    if sum(1 for _ in label) > LABEL_MAX:
        raise ValueError(f"skill label exceeds {LABEL_MAX} code points")
    if sum(1 for _ in description) > DESCRIPTION_MAX:
        raise ValueError(f"skill description exceeds {DESCRIPTION_MAX} code points")


def _skill(
    key: str,
    label: str,
    description: str,
    kind: SkillKind,
    target_spec: TargetSpec,
    *,
    cost: dict[str, int] | None = None,
    usable_out_of_combat: bool = False,
    element: str | None = None,
    effects: list[str] | None = None,
    faction_constraint: FactionConstraint = FactionConstraint.ANY,
    requires_divine_arts: bool = False,
) -> SkillDef:
    """Build seed data without duplicating empty collection literals."""
    _validate_metadata(label, description)
    return SkillDef(
        key=key,
        label=label,
        description=description,
        kind=kind,
        target_spec=target_spec,
        cost=_FrozenDict({} if cost is None else cost),
        usable_out_of_combat=usable_out_of_combat,
        element=None if element is None else ELEMENT_REGISTRY[element],
        effects=_FrozenList([] if effects is None else effects),
        faction_constraint=faction_constraint,
        requires_divine_arts=requires_divine_arts,
    )


def _spell(
    key: str,
    label: str,
    description: str,
    target_spec: TargetSpec,
    *,
    mp: int,
    element: str,
    effects: tuple[str, ...],
    usable_out_of_combat: bool = False,
) -> SkillDef:
    """Build one ACTIVE elemental spell — the design doc §4.4 catalog shape.

    Every catalog spell is an ACTIVE skill freely targetable among enemies
    and allies at an integer MP cost, so this helper fixes exactly that
    shape instead of repeating it in each entry.
    """
    return _skill(
        key,
        label,
        description,
        SkillKind.ACTIVE,
        target_spec,
        cost={"mp": mp},
        usable_out_of_combat=usable_out_of_combat,
        element=element,
        effects=list(effects),
        faction_constraint=FactionConstraint.ANY,
    )


def _elemental_spells(
    element: str,
    *spells: tuple[str, str, str, TargetSpec, int, tuple[str, ...]],
) -> tuple[SkillDef, ...]:
    """Build one element's full ACTIVE spell set (design doc §4.4).

    Each row is ``(key, label, description, target_spec, mp, effects)`` in
    the exact order of the design doc's catalog table. The element is written
    once for the whole set. A spell's tier is deliberately NOT a stored
    field: it stays derivable from the set's grouping and each row's MP cost
    band (``spell_tier_for``), per the skill-registry spec.
    """
    if element not in ELEMENT_REGISTRY:
        raise ValueError(f"unknown element {element!r} for elemental spell set")
    return tuple(
        _spell(
            key,
            label,
            description,
            target_spec,
            mp=mp,
            element=element,
            effects=effects,
        )
        for key, label, description, target_spec, mp, effects in spells
    )


_BODY_TRAITS = ("atk_phys", "agility", "defense")


def _body_multiplier(key: str, label: str, multiplier: float) -> SkillDef:
    """Build one passive physical-stat multiplier tier."""
    return _skill(
        key,
        label,
        "以體內能量強化自身的物理能力，提升攻擊、敏捷與防禦。",
        SkillKind.PASSIVE,
        TargetSpec.SELF,
        usable_out_of_combat=True,
        effects=[
            f"stat_multiply:{trait_key}:{multiplier:g}"
            for trait_key in _BODY_TRAITS
        ],
    )


SKILL_REGISTRY: dict[str, SkillDef] = {
    skill.key: skill
    for skill in (
        _skill(
            "basic_attack",
            "基本攻擊",
            "以普通攻擊對單一目標造成物理傷害。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            element="fire",
            faction_constraint=FactionConstraint.ANY,
            effects=["damage:fire:physical"],
        ),
        _body_multiplier("body_enhancement", "身體強化", 100),
        _body_multiplier("body_enhancement_extreme", "身體超強化", 1000),
        _body_multiplier("body_enhancement_basic", "身體強化·初階", 1.2),
        _skill(
            "fire_mastery",
            "火焰精通",
            "被動提昇火焰系魔法的掌握程度與威力。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            element="fire",
            effects=["element_mastery_rank:主宰"],
        ),
        _skill(
            "dark_mastery",
            "闇屬性精通",
            "被動提昇闇屬性魔法的掌握程度與威力。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            element="dark",
            effects=["element_mastery_rank:主宰"],
        ),
        _skill(
            "wind_mastery",
            "風屬性精通",
            "被動提昇風屬性魔法的掌握程度與威力。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            element="wind",
            effects=["element_mastery_rank:主宰"],
        ),
        _skill(
            "light_mastery",
            "光屬性精通",
            "被動提昇光屬性魔法的掌握程度與威力。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            element="light",
            effects=["element_mastery_rank:主宰"],
        ),
        _skill(
            "water_mastery",
            "水屬性精通",
            "被動提昇水系魔法的掌握程度與威力。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            element="water",
            effects=["element_mastery_rank:主宰"],
        ),
        _skill(
            "earth_mastery",
            "土屬性精通",
            "被動提昇土系魔法的掌握程度與威力。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            element="earth",
            effects=["element_mastery_rank:主宰"],
        ),
        _skill(
            "lightning_mastery",
            "雷屬性精通",
            "被動提昇雷系魔法的掌握程度與威力。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            element="lightning",
            effects=["element_mastery_rank:主宰"],
        ),
        _skill(
            "ice_mastery",
            "冰屬性精通",
            "被動提昇冰系魔法的掌握程度與威力。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            element="ice",
            effects=["element_mastery_rank:主宰"],
        ),
        *_elemental_spells(
            "fire",
            # 火 — 學徒
            ("fire_ball", "火球術", "凝聚火焰魔力，對單一目標造成魔法傷害。", TargetSpec.SINGLE, 14, ("damage:fire:magic",)),
            ("fire_arrow", "火焰箭", "射出火焰凝聚的箭矢，以低耗能對單一目標造成魔法傷害。", TargetSpec.SINGLE, 10, ("damage:fire:magic",)),
            # 火 — 術師
            ("firestorm", "火焰風暴", "召喚覆蓋範圍的火焰風暴，對範圍內所有目標造成魔法傷害。", TargetSpec.AREA, 30, ("damage:fire:magic",)),
            ("scorching_wave", "灼熱波動", "釋放灼熱的波動，對單一目標造成魔法傷害並使其灼燒。", TargetSpec.SINGLE, 24, ("damage:fire:magic", "buff_apply:fire_scorch")),
            # 火 — 大師
            ("lava_burst", "熔岩術", "使地面迸裂噴出熔岩，對範圍內所有目標造成魔法傷害。", TargetSpec.AREA, 52, ("damage:fire:magic",)),
            ("infernal_wrap", "業火纏繞", "以業火纏繞單一目標，造成高額魔法傷害。", TargetSpec.SINGLE, 42, ("damage:fire:magic",)),
            # 火 — 賢者
            ("dragon_flame", "龍炎術", "喚起龍之吐息，對範圍內所有目標造成高額魔法傷害。", TargetSpec.AREA, 95, ("damage:fire:magic",)),
            ("hellfire", "煉獄業火", "召喚煉獄的業火，對單一目標造成極高魔法傷害。", TargetSpec.SINGLE, 78, ("damage:fire:magic",)),
            # 火 — 主宰
            ("phoenix_eternal_flame", "不滅鳳凰焰", "召喚不滅的鳳凰之焰，對範圍內所有目標造成極高魔法傷害，並治癒自身。", TargetSpec.AREA, 150, ("damage:fire:magic", "self_heal")),
            ("world_ending_blaze", "焚世終焰", "召喚足以焚盡世界的終焰，對單一目標造成毀滅級魔法傷害。", TargetSpec.SINGLE, 130, ("damage:fire:magic",)),
        ),
        _skill(
            "wind_blade",
            "風刃術",
            "颳起銳利風刃，對範圍內所有目標造成魔法傷害。",
            SkillKind.ACTIVE,
            TargetSpec.AREA,
            cost={"mp": 24},
            element="wind",
            faction_constraint=FactionConstraint.ANY,
            effects=["damage:wind:magic"],
        ),
        _skill(
            "flight",
            "飛行術",
            "操控風元素飛行，可前往遠處的場合。",
            SkillKind.PASSIVE,
            TargetSpec.SELF,
            cost={"mp": 10},
            usable_out_of_combat=True,
            element="wind",
            effects=["movement:flight"],
        ),
        _skill(
            "dual_wield_style",
            "雙持劍術",
            "同時揮舞兩把武器進行戰鬥的架式。",
            SkillKind.ACTIVE,
            TargetSpec.SELF,
            cost={"sp": 8},
            effects=["weapon_style:dual_wield"],
        ),
        _skill(
            "dual_blade_mastery",
            "雙刀流·宗師級",
            "以宗師級的雙刀連擊，對單一目標造成物理傷害。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            cost={"sp": 30},
            element="dark",
            faction_constraint=FactionConstraint.ANY,
            effects=["damage:dark:physical"],
        ),
        _skill(
            "light_sword_style",
            "光劍架式",
            "以光之劍的架式對單一目標造成物理傷害。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            cost={"sp": 6},
            element="light",
            faction_constraint=FactionConstraint.ANY,
            effects=["damage:light:physical"],
        ),
        _skill(
            "shadow_slash",
            "影斬",
            "潛入闇影後對單一目標斬出一記物理攻擊。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            cost={"sp": 18},
            element="dark",
            faction_constraint=FactionConstraint.ANY,
            effects=["damage:dark:physical"],
        ),
        _skill(
            "flash_step",
            "瞬步",
            "以高速步伐瞬間移動，可前往較近的場合。",
            SkillKind.PASSIVE,
            TargetSpec.SELF,
            cost={"sp": 12},
            usable_out_of_combat=True,
            effects=["movement:flash_step"],
        ),
        _skill(
            "status_disguise",
            "神之秘法：狀態偽裝",
            "以神之秘法偽裝自身的外貌與部分能力數值。",
            SkillKind.ACTIVE,
            TargetSpec.SELF,
            usable_out_of_combat=True,
            effects=["set_disguise"],
        ),
        _skill(
            "concentration",
            "集中",
            "凝聚精神，暫時提升自身的專注與準確度。",
            SkillKind.ACTIVE,
            TargetSpec.NONE,
            cost={"mp": 5},
            effects=["self_buff_apply:focus"],
        ),
        _skill(
            "dominion_art",
            "統御術",
            "授予目標一部分自身技能的效果。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            effects=["confer_skill_partial"],
        ),
        _skill(
            "defense_instinct",
            "防禦直覺",
            "被動強化自身的防禦能力。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["passive_buff:defense_small"],
        ),
        _skill(
            "blade_art_mastery",
            "劍術精通",
            "被動提昇劍術與刀術相關技能的效果。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["passive_buff:blade_arts"],
        ),
        _skill(
            "extreme_endurance",
            "極限耐力",
            "被動強化自身的耐力上限。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["passive_buff:endurance_extreme"],
        ),
        _skill(
            "magic_circle_comprehension",
            "魔法陣理解",
            "被動提昇對魔法陣的理解與運用。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["passive_buff:magic_circle_comprehension"],
        ),
        _skill(
            "precise_mana_control",
            "精準魔力控制",
            "被動強化對魔力的精準控制。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["passive_buff:mana_precision"],
        ),
        _skill(
            "retainer_martial_training",
            "隨從武藝訓練",
            "被動提昇隨從角色的武藝水準。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["passive_buff:retainer_training"],
        ),
        _skill(
            "guardian_instinct",
            "護主本能",
            "被動強化守護主人、忠誠護衛的本能。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["passive_buff:guardian_instinct"],
        ),
        _skill(
            "elf_longevity",
            "精靈長壽",
            "被動延長生命週期，是精靈種族的特質。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["passive_trait:elf_longevity"],
        ),
        _skill(
            "reincarnation_boon_elosia",
            "轉生祝福·艾露西亞",
            "轉生帶來的祝福，被動加速魔力成長。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["growth_rate:magic:100"],
        ),
        _skill(
            "reincarnation_boon_yuka",
            "轉生祝福·由花",
            "轉生帶來的祝福，被動強化戰鬥預感。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["combat_prediction:武感"],
        ),
        _skill(
            "reincarnation_boon_yuna",
            "轉生祝福·由奈",
            "轉生帶來的祝福，被動精通性魔法的掌握。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["sexual_magic_mastery"],
        ),
        _skill(
            "divine_sexual_mastery",
            "性魔法主宰",
            "以神性掌握性魔法精髓的至高境界，被動證明對性魔法領域的絕對理解。",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            requires_divine_arts=True,
            effects=["sexual_magic_mastery"],
        ),
        _skill(
            "divine_sexual_arts",
            "神之秘法：性愛系統",
            "以神之秘法引導的性愛技法，直接刺激目標的感官與慾望。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["sexual_event:stimulus_applied"],
        ),
        _skill(
            "divine_time_dilation",
            "神之秘法：時間加速",
            "以神性加速或減緩時間流動的秘法。",
            SkillKind.ACTIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["divine_mystery:時間加速"],
        ),
        _skill(
            "divine_space_distortion",
            "神之秘法：空間扭曲",
            "以神性扭曲空間，使存在與景物移位重組的秘法。",
            SkillKind.ACTIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["divine_mystery:空間扭曲"],
        ),
        _skill(
            "divine_matter_transmutation",
            "神之秘法：物質轉換",
            "以神性改變物質本質，將萬物轉化為其他形態的秘法。",
            SkillKind.ACTIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["divine_mystery:物質轉換"],
        ),
        _skill(
            "divine_life_extension",
            "神之秘法：生命延續",
            "以神性延續生命與壽命的秘法，據說能超越種族的極限。",
            SkillKind.ACTIVE,
            TargetSpec.NONE,
            usable_out_of_combat=True,
            requires_divine_arts=True,
            effects=["divine_mystery:生命延續"],
        ),
    )
}
