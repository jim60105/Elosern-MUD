"""Deterministic, rulebook-driven monster combat decisions."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from world.rules import combat, dice
from world.rules.action import ActionRequest, _stored_trait_value
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.skills.registry import (
    SKILL_REGISTRY,
    SkillDef,
    SkillKind,
    TargetSpec,
)


MONSTER_BEHAVIOUR_YAML = yaml.safe_load(
    (Path(__file__).parent / "rulebook" / "monster_behaviour.yaml").read_text(
        encoding="utf-8"
    )
)


@dataclass(frozen=True)
class BehaviourProfile:
    """Tunable leaves for the shared monster decision tree."""

    target_strategy: str
    skill_choice: str
    prefer_area_when_multiple_enemies: bool


BEHAVIOUR_PROFILES = {
    key: BehaviourProfile(**values)
    for key, values in MONSTER_BEHAVIOUR_YAML["archetypes"].items()
}


def resolve_behaviour_profile(monster: Any) -> BehaviourProfile:
    """Resolve an instance override or its threat tier's default profile."""
    archetype_key = getattr(monster, "behaviour_tree", None)
    if not archetype_key:
        archetype_key = MONSTER_BEHAVIOUR_YAML["tier_default_archetype"][
            monster.threat_tier
        ]
    return BEHAVIOUR_PROFILES[archetype_key]


def _owned_damage_skills(entity: Any) -> list[SkillDef]:
    """Return affordable active damage skills in owned-key order."""
    return [
        SKILL_REGISTRY[key]
        for key in entity.skills.owned_keys()
        if key in SKILL_REGISTRY
        and SKILL_REGISTRY[key].kind is SkillKind.ACTIVE
        and any(
            effect.startswith("damage:")
            for effect in SKILL_REGISTRY[key].effects
        )
        and all(
            _stored_trait_value(getattr(entity.traits, resource)) >= amount
            for resource, amount in SKILL_REGISTRY[key].cost.items()
        )
    ]


def _damage_school(skill: SkillDef) -> str:
    """Return the physical or magic school from a damage effect."""
    effect = next(
        effect for effect in skill.effects if effect.startswith("damage:")
    )
    _, school = combat._parse_damage_effect(effect)
    return school


def _living_enemies(
    battlefield: Battlefield,
    actor: Any,
) -> list[Any]:
    """Return living, non-fled members of the opposing team."""
    actor_team = battlefield.team_of(str(actor.key))
    enemy_keys = next(
        (
            members
            for team, members in battlefield.teams.items()
            if team != actor_team
        ),
        frozenset(),
    )
    return [
        battlefield.roster[key]
        for key in enemy_keys
        if key in battlefield.roster
        and key not in battlefield.fled
        and combat._stored_hp(battlefield.roster[key]) > 0
    ]


def _choose_target(
    entity: Any,
    enemies: list[Any],
    strategy: str,
) -> Any:
    """Choose one enemy by the configured metric and seeded tie-break."""
    del entity
    if strategy == "lowest_hp":
        metric = lambda enemy: combat._stored_hp(enemy)
        best = min(metric(enemy) for enemy in enemies)
    elif strategy == "highest_effective_power":
        metric = combat.effective_power
        best = max(metric(enemy) for enemy in enemies)
    else:
        raise ValueError(f"unknown target_strategy: {strategy!r}")
    tied = sorted(
        (enemy for enemy in enemies if metric(enemy) == best),
        key=lambda enemy: str(enemy.key),
    )
    if len(tied) == 1:
        return tied[0]
    return tied[dice.roll_d100() % len(tied)]


def _choose_skill(
    entity: Any,
    candidates: list[SkillDef],
    strategy: str,
    target: Any | None,
) -> SkillDef:
    """Choose an eligible skill without consuming resolution dice."""
    if strategy == "first_owned":
        return candidates[0]
    if strategy != "highest_expected_damage":
        raise ValueError(f"unknown skill_choice: {strategy!r}")

    def expected_damage(skill: SkillDef) -> float:
        attack_key = (
            "atk_phys"
            if _damage_school(skill) == "physical"
            else "magic_level"
        )
        expected = float(entity.skills.effective_value(attack_key))
        if target is not None:
            expected -= float(target.skills.effective_value("defense"))
        return expected

    best = max(expected_damage(skill) for skill in candidates)
    tied = [
        skill for skill in candidates if expected_damage(skill) == best
    ]
    if len(tied) == 1:
        return tied[0]
    return tied[dice.roll_d100() % len(tied)]


def monster_behaviour_policy(
    entity: Any,
    battlefield: Battlefield,
) -> ActionRequest | None:
    """Return one resolver-ready monster action for the current turn."""
    if not hasattr(entity, "threat_tier"):
        return combat.default_attack_policy(entity, battlefield)

    enemies = _living_enemies(battlefield, entity)
    if not enemies:
        return None
    profile = resolve_behaviour_profile(entity)
    damage_skills = _owned_damage_skills(entity)
    single_skills = [
        skill
        for skill in damage_skills
        if skill.target_spec is TargetSpec.SINGLE
    ]
    area_skills = [
        skill
        for skill in damage_skills
        if skill.target_spec is TargetSpec.AREA
    ]
    use_area = (
        profile.prefer_area_when_multiple_enemies
        and len(enemies) > 1
        and bool(area_skills)
    ) or (not single_skills and bool(area_skills))
    context = BattlefieldActionContext(battlefield)
    if use_area:
        skill = _choose_skill(
            entity,
            area_skills,
            profile.skill_choice,
            target=None,
        )
        return ActionRequest(entity, skill.key, "all-enemies", context)
    if not single_skills:
        return None
    target = _choose_target(entity, enemies, profile.target_strategy)
    skill = _choose_skill(
        entity,
        single_skills,
        profile.skill_choice,
        target,
    )
    return ActionRequest(entity, skill.key, [target], context)
