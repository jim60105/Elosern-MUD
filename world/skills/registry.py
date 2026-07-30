"""Skill definitions from design section 5.2 and ``skills-equipment``.

``SkillKind`` and ``TargetSpec`` are forward declarations for change 8's
action resolver to import rather than redefine. ``stat_multiply`` is the only
effect-ID convention interpreted by this package; all other effects remain
opaque for the future rulebook engine.
"""

from dataclasses import dataclass
from enum import StrEnum

from world.lore.elements import ELEMENT_REGISTRY, Element


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
    """Relations a skill permits the resolver to target."""

    ANY = "any"
    ALLY = "ally"
    ENEMY = "enemy"
    SELF_ONLY = "self_only"


@dataclass(frozen=True)
class SkillDef:
    """Immutable definition of a skill known to deterministic consumers."""

    key: str
    kind: SkillKind
    target_spec: TargetSpec
    cost: dict[str, int]
    usable_out_of_combat: bool
    element: Element | None
    effects: list[str]
    faction_constraint: FactionConstraint = FactionConstraint.ANY


def _skill(
    key: str,
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
    return SkillDef(
        key=key,
        kind=kind,
        target_spec=target_spec,
        cost=_FrozenDict({} if cost is None else cost),
        usable_out_of_combat=usable_out_of_combat,
        element=None if element is None else ELEMENT_REGISTRY[element],
        effects=_FrozenList([] if effects is None else effects),
        faction_constraint=faction_constraint,
    )


_BODY_TRAITS = ("atk_phys", "agility", "defense")


def _body_multiplier(key: str, multiplier: float) -> SkillDef:
    """Build one active physical-stat multiplier tier."""
    return _skill(
        key,
        SkillKind.ACTIVE,
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
        _body_multiplier("body_enhancement", 100),
        _body_multiplier("body_enhancement_extreme", 1000),
        _body_multiplier("body_enhancement_basic", 1.2),
        _skill(
            "fire_mastery",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            element="fire",
            effects=["element_mastery_rank:主宰"],
        ),
        _skill(
            "dark_mastery",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            element="dark",
            effects=["element_mastery_rank:主宰"],
        ),
        _skill(
            "wind_mastery",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            element="wind",
            effects=["element_mastery_rank:主宰"],
        ),
        _skill(
            "light_mastery",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            element="light",
            effects=["element_mastery_rank:主宰"],
        ),
        _skill(
            "fire_ball",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            cost={"mp": 20},
            element="fire",
            effects=["damage:fire:magic"],
            faction_constraint=FactionConstraint.ENEMY,
        ),
        _skill(
            "wind_blade",
            SkillKind.ACTIVE,
            TargetSpec.AREA,
            cost={"mp": 24},
            element="wind",
            effects=["damage:wind:magic"],
            faction_constraint=FactionConstraint.ENEMY,
        ),
        _skill(
            "flight",
            SkillKind.ACTIVE,
            TargetSpec.SELF,
            cost={"mp": 10},
            usable_out_of_combat=True,
            element="wind",
            effects=["movement:flight"],
        ),
        _skill(
            "dual_wield_style",
            SkillKind.ACTIVE,
            TargetSpec.SELF,
            cost={"sp": 8},
            effects=["weapon_style:dual_wield"],
        ),
        _skill(
            "light_sword_style",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            cost={"sp": 6},
            effects=["weapon_style:light_sword"],
            faction_constraint=FactionConstraint.ENEMY,
        ),
        _skill(
            "shadow_slash",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            cost={"sp": 18},
            element="dark",
            effects=["damage:dark:physical"],
            faction_constraint=FactionConstraint.ENEMY,
        ),
        _skill(
            "flash_step",
            SkillKind.ACTIVE,
            TargetSpec.SELF,
            cost={"sp": 12},
            usable_out_of_combat=True,
            effects=["movement:flash_step"],
        ),
        _skill(
            "status_disguise",
            SkillKind.ACTIVE,
            TargetSpec.SELF,
            usable_out_of_combat=True,
            effects=["set_disguise"],
        ),
        _skill(
            "dominion_art",
            SkillKind.ACTIVE,
            TargetSpec.SINGLE,
            usable_out_of_combat=True,
            effects=["confer_skill_partial"],
        ),
        _skill(
            "defense_instinct",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["passive_buff:defense_small"],
        ),
        _skill(
            "blade_art_mastery",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["passive_buff:blade_arts"],
        ),
        _skill(
            "extreme_endurance",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["passive_buff:endurance_extreme"],
        ),
        _skill(
            "magic_circle_comprehension",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["passive_buff:magic_circle_comprehension"],
        ),
        _skill(
            "precise_mana_control",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["passive_buff:mana_precision"],
        ),
        _skill(
            "retainer_martial_training",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["passive_buff:retainer_training"],
        ),
        _skill(
            "guardian_instinct",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["passive_buff:guardian_instinct"],
        ),
        _skill(
            "elf_longevity",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["passive_trait:elf_longevity"],
        ),
        _skill(
            "reincarnation_boon_elosia",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["growth_rate:magic:100"],
        ),
        _skill(
            "reincarnation_boon_yuka",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["combat_prediction:武感"],
        ),
        _skill(
            "reincarnation_boon_yuna",
            SkillKind.PASSIVE,
            TargetSpec.NONE,
            effects=["element_mastery_rank:性魔法:主宰"],
        ),
    )
}
