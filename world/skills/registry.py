"""Skill definitions from design section 5.2 and ``skills-equipment``.

``SkillKind`` and ``TargetSpec`` are forward declarations for change 8's
action resolver to import rather than redefine. Every ``effects`` string is
parsed into a typed dataclass by ``world.skills.effects.parse_effect`` at
construction; see that module for the recognized effect-ID conventions.
"""

from dataclasses import dataclass
from enum import StrEnum

from world.lore.elements import ELEMENT_REGISTRY, Element
from world.skills.effects import parse_effect


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
            "fire_ball",
            "火球術",
            "凝聚火焰魔力，對單一目標造成魔法傷害。",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            cost={"mp": 20},
            element="fire",
            faction_constraint=FactionConstraint.ANY,
            effects=["damage:fire:magic"],
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
            SkillKind.ACTIVE,
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
            faction_constraint=FactionConstraint.ANY,
            effects=["weapon_style:light_sword"],
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
            SkillKind.ACTIVE,
            TargetSpec.SELF,
            cost={"sp": 12},
            usable_out_of_combat=True,
            effects=["movement:flash_step"],
        ),
        _skill(
            "status_disguise",
            "狀態偽裝",
            "偽裝自身的外貌與部分能力數值。",
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
    )
}
