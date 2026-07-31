"""Deterministic, rulebook-driven monster combat decisions."""

from collections.abc import Mapping
from dataclasses import dataclass
from numbers import Real
from pathlib import Path
from typing import Any

import yaml

from world.rules import combat, dice
from world.rules.action import ActionRequest, _stored_trait_value
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.disengage import FLEE_SKILL_KEY
from world.skills.registry import (
    SKILL_REGISTRY,
    SkillDef,
    SkillKind,
    TargetSpec,
)


class MonsterBehaviourConfigError(ValueError):
    """Raised when monster behaviour tuning violates its rulebook contract."""


def _configuration_error(detail: str) -> MonsterBehaviourConfigError:
    return MonsterBehaviourConfigError(
        f"invalid monster behaviour rulebook: {detail}"
    )


def _load_rulebook(path: Path) -> Any:
    """Load YAML while preserving the stable rulebook-error contract."""
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise _configuration_error("could not parse YAML") from error


MONSTER_BEHAVIOUR_YAML = _load_rulebook(
    Path(__file__).parent / "rulebook" / "monster_behaviour.yaml"
)


@dataclass(frozen=True)
class BehaviourProfile:
    """Tunable leaves for the shared monster decision tree."""

    target_strategy: str
    skill_choice: str
    prefer_area_when_multiple_enemies: bool
    flee_hp_fraction: float | None


_PROFILE_FIELDS = frozenset(
    {
        "target_strategy",
        "skill_choice",
        "prefer_area_when_multiple_enemies",
        "flee_hp_fraction",
    }
)
_TARGET_STRATEGIES = frozenset({"lowest_hp", "highest_effective_power"})
_SKILL_CHOICES = frozenset({"first_owned", "highest_expected_damage"})


def _load_behaviour_profiles(
    rulebook: Any,
) -> dict[str, BehaviourProfile]:
    """Validate rulebook tuning and build immutable behaviour profiles."""
    if not isinstance(rulebook, Mapping):
        raise _configuration_error("rulebook must be a mapping")
    archetypes = rulebook.get("archetypes")
    defaults = rulebook.get("tier_default_archetype")
    if not isinstance(archetypes, Mapping):
        raise _configuration_error("archetypes must be a mapping")
    if not isinstance(defaults, Mapping):
        raise _configuration_error("tier_default_archetype must be a mapping")

    profiles: dict[str, BehaviourProfile] = {}
    for key, values in archetypes.items():
        if not isinstance(key, str) or not isinstance(values, Mapping):
            raise _configuration_error("each archetype must be a named mapping")
        if set(values) != _PROFILE_FIELDS:
            raise _configuration_error(
                f"archetype {key!r} must declare exactly {sorted(_PROFILE_FIELDS)}"
        )
        target_strategy = values["target_strategy"]
        if (
            not isinstance(target_strategy, str)
            or target_strategy not in _TARGET_STRATEGIES
        ):
            raise _configuration_error(
                f"archetype {key!r} has unknown target_strategy {target_strategy!r}"
        )
        skill_choice = values["skill_choice"]
        if (
            not isinstance(skill_choice, str)
            or skill_choice not in _SKILL_CHOICES
        ):
            raise _configuration_error(
                f"archetype {key!r} has unknown skill_choice {skill_choice!r}"
            )
        prefer_area = values["prefer_area_when_multiple_enemies"]
        if type(prefer_area) is not bool:
            raise _configuration_error(
                f"archetype {key!r} has non-boolean area preference"
            )
        flee_fraction = values["flee_hp_fraction"]
        if flee_fraction is not None and (
            isinstance(flee_fraction, bool)
            or not isinstance(flee_fraction, Real)
            or not 0 <= flee_fraction <= 1
        ):
            raise _configuration_error(
                f"archetype {key!r} has invalid flee_hp_fraction"
            )
        profiles[key] = BehaviourProfile(
            target_strategy=target_strategy,
            skill_choice=skill_choice,
            prefer_area_when_multiple_enemies=prefer_area,
            flee_hp_fraction=(
                None if flee_fraction is None else float(flee_fraction)
            ),
        )

    for tier, archetype_key in defaults.items():
        if (
            not isinstance(tier, str)
            or not isinstance(archetype_key, str)
            or archetype_key not in profiles
        ):
            raise _configuration_error(
                f"tier default {tier!r} references unknown archetype {archetype_key!r}"
            )
    return profiles


BEHAVIOUR_PROFILES = _load_behaviour_profiles(MONSTER_BEHAVIOUR_YAML)


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


def _should_flee(entity: Any, profile: BehaviourProfile) -> bool:
    """Return whether stored true HP has reached this profile's flee boundary."""
    threshold = profile.flee_hp_fraction
    maximum = combat._max_hp(entity)
    return (
        threshold is not None
        and maximum > 0
        and combat._stored_hp(entity) / maximum <= threshold
    )


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
    if _should_flee(entity, profile):
        return ActionRequest(
            actor=entity,
            skill_key=FLEE_SKILL_KEY,
            targets=[entity],
            context=BattlefieldActionContext(
                battlefield,
                event_context={"battlefield": battlefield},
            ),
        )
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
