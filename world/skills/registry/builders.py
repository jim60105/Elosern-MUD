"""Seed-data builders shared by every registry data slice.

Moved verbatim from ``world/skills/registry.py``: ``_skill``/``_spell``/
``_elemental_spells``/``_body_multiplier`` produce the immutable rows the
domain data modules list in global construction order.
"""

from typing import Any

from world.lore.elements import ELEMENT_REGISTRY
from world.skills.cast_conditions import CastCondition
from world.skills.effects import EffectPolicy, InteractionPolicy
from world.skills.registry.vocab import (
    FactionConstraint,
    SkillCategory,
    SkillDef,
    SkillKind,
    SkillPrerequisite,
    TargetSpec,
    _FrozenDict,
    _FrozenList,
    _validate_metadata,
)

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
    category: SkillCategory,
    group: str | None = None,
    prerequisites: tuple[SkillPrerequisite, ...] = (),
    effect_policies: tuple[EffectPolicy, ...] | None = None,
    cast_conditions: tuple[CastCondition, ...] = (),
    interaction: InteractionPolicy | None = None,
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
        category=category,
        group=group,
        prerequisites=prerequisites,
        effect_policies=() if effect_policies is None else tuple(effect_policies),
        cast_conditions=tuple(cast_conditions),
        interaction=interaction,
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
    faction_constraint: FactionConstraint = FactionConstraint.ANY,
    category: SkillCategory,
    group: str | None = None,
    prerequisites: tuple[SkillPrerequisite, ...] = (),
    effect_policies: tuple[EffectPolicy, ...] | None = None,
    cast_conditions: tuple[CastCondition, ...] = (),
    interaction: InteractionPolicy | None = None,
) -> SkillDef:
    """Build one ACTIVE elemental spell — the design doc §4.4 catalog shape.

    Every catalog spell is an ACTIVE skill at an integer MP cost. By default,
    spells are freely targetable among enemies and allies (FactionConstraint.ANY);
    self-targeted buffs (e.g. water_shield) declare FactionConstraint.SELF_ONLY.
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
        faction_constraint=faction_constraint,
        category=category,
        group=group,
        prerequisites=prerequisites,
        effect_policies=effect_policies,
        cast_conditions=cast_conditions,
        interaction=interaction,
    )


def _elemental_spells(
    element: str,
    *spells: tuple[Any, ...],
) -> tuple[SkillDef, ...]:
    """Build one element's full ACTIVE spell set (design doc §4.4).

    Each row is ``(key, label, description, target_spec, mp, effects)``, with
    an optional seventh ``prerequisites`` entry carrying this skill's lineage
    edges (``()`` when absent). The element is written once for the whole set. A spell's tier is
    deliberately NOT a stored field: it stays derivable from the set's
    grouping and each row's MP cost band (``spell_tier_for``), per the
    skill-registry spec.
    """
    if element not in ELEMENT_REGISTRY:
        raise ValueError(f"unknown element {element!r} for elemental spell set")

    def _row(row: tuple[Any, ...]) -> tuple[Any, ...]:
        if len(row) == 6:
            return (*row, ())
        if len(row) == 7:
            return row
        raise ValueError(
            "elemental spell rows carry 6 or 7 fields, got "
            f"{len(row)}: {row[0] if row else '?'}"
        )

    return tuple(
        _spell(
            key,
            label,
            description,
            target_spec,
            usable_out_of_combat=True,
            mp=mp,
            element=element,
            effects=effects,
            category=SkillCategory.ELEMENTAL_MAGIC,
            group=element,
            prerequisites=prerequisites,
        )
        for key, label, description, target_spec, mp, effects, prerequisites in (
            _row(row) for row in spells
        )
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
        category=SkillCategory.ENHANCEMENT,
    )
