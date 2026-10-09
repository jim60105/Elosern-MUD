"""Pure shared qualification for authored records and stored runtime identity."""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY
if TYPE_CHECKING:
    from world.skills.registry.vocab import SkillEligibility

ACTOR_KINDS = frozenset(("player", "npc", "monster"))
CAPABILITIES = frozenset(("can_use_divine_arts",))


def closed_skill_keys(keys, registry):
    """Yield declared and prerequisite-added keys once, without constructing actors."""
    seen = set()
    frontier = list(keys)
    while frontier:
        key = frontier.pop(0)
        if key in seen:
            continue
        seen.add(key)
        yield key
        skill = registry.get(key)
        if skill is not None:
            frontier.extend(edge.skill_key for edge in skill.prerequisites)


def record_identity_eligible(
    eligibility: SkillEligibility,
    actor_kind: str | None,
    *,
    race: str | None = None,
    subrace: str | None = None,
    species_key: str | None = None,
    variant_key: str | None = None,
) -> bool:
    """Evaluate identity only, never ownership, resources or proficiency."""
    if eligibility.allowed_actor_kinds is not None:
        if actor_kind not in eligibility.allowed_actor_kinds:
            return False
    character_restricted = (
        eligibility.allowed_races is not None
        or eligibility.allowed_subraces is not None
        or bool(eligibility.required_capabilities)
    )
    if character_restricted:
        if actor_kind not in ("player", "npc") or race not in RACE_REGISTRY:
            return False
        if eligibility.allowed_races is not None and race not in eligibility.allowed_races:
            return False
        if subrace is not None:
            branch = SUBRACE_REGISTRY.get(subrace)
            if branch is None or branch.race_key != race:
                return False
        if eligibility.allowed_subraces is not None:
            if subrace not in eligibility.allowed_subraces:
                return False
        profile = RACE_REGISTRY[race]
        if any(
            capability not in CAPABILITIES or not getattr(profile, capability, False)
            for capability in eligibility.required_capabilities
        ):
            return False
    if eligibility.allowed_species is not None:
        if actor_kind != "monster" or species_key not in eligibility.allowed_species:
            return False
        from world.lore.monster_species import (
            MONSTER_SPECIES_REGISTRY, MONSTER_VARIANT_REGISTRY,
        )

        variant = MONSTER_VARIANT_REGISTRY.get(variant_key)
        if species_key not in MONSTER_SPECIES_REGISTRY:
            return False
        if variant is None or variant.species_key != species_key:
            return False
    return True


def actor_kind_for(entity: Any) -> str | None:
    """Typeclass identity, not incidental race/species attributes, is authority."""
    from typeclasses.monsters import Monster
    from typeclasses.npcs import NPC
    from typeclasses.characters import PlayerCharacter

    if isinstance(entity, Monster):
        return "monster"
    if isinstance(entity, NPC):
        return "npc"
    if isinstance(entity, PlayerCharacter):
        return "player"
    return None


def skill_identity_eligible(entity: Any, skill: Any) -> bool:
    """Read stored identity without mounting handlers or materializing attributes."""
    eligibility = skill.eligibility
    if (
        eligibility.allowed_actor_kinds is None
        and eligibility.allowed_races is None
        and eligibility.allowed_subraces is None
        and eligibility.allowed_species is None
        and not eligibility.required_capabilities
    ):
        return True
    # Read-model facades explicitly delegate identity to their stored subject.
    entity = getattr(entity, "_skill_identity_subject", entity)
    stored = getattr(entity, "db", None)
    return record_identity_eligible(
        eligibility, actor_kind_for(entity),
        race=getattr(stored, "race", None),
        subrace=getattr(stored, "subrace", None),
        species_key=getattr(stored, "species_key", None),
        variant_key=getattr(stored, "variant_key", None),
    )


def validate_skill_eligibility(eligibility: SkillEligibility) -> None:
    """Reject unknown references and unsatisfiable declarations before play."""
    faces = (
        ("allowed_actor_kinds", ACTOR_KINDS),
        ("allowed_races", RACE_REGISTRY),
        ("allowed_subraces", SUBRACE_REGISTRY),
        ("required_capabilities", CAPABILITIES),
    )
    for name, face in faces:
        values = getattr(eligibility, name)
        if values is not None and any(key not in face for key in values):
            raise ValueError(f"eligibility {name} contains an unknown identifier")
    if eligibility.allowed_species is not None:
        from world.lore.monster_species import MONSTER_SPECIES_REGISTRY

        if any(key not in MONSTER_SPECIES_REGISTRY for key in eligibility.allowed_species):
            raise ValueError("eligibility allowed_species contains an unknown identifier")
    if eligibility.allowed_races is not None and eligibility.allowed_subraces is not None:
        if any(
            SUBRACE_REGISTRY[key].race_key not in eligibility.allowed_races
            for key in eligibility.allowed_subraces
        ):
            raise ValueError("eligibility subrace parent is not an allowed race")
    character_restricted = (
        eligibility.allowed_races is not None
        or eligibility.allowed_subraces is not None
        or bool(eligibility.required_capabilities)
    )
    kinds = set(eligibility.allowed_actor_kinds or ACTOR_KINDS)
    if character_restricted:
        kinds.intersection_update(("player", "npc"))
    if eligibility.allowed_species is not None:
        kinds.intersection_update(("monster",))
    if not kinds:
        raise ValueError("eligibility has contradictory actor identities")
    if character_restricted:
        races = eligibility.allowed_races or tuple(RACE_REGISTRY)
        branches = eligibility.allowed_subraces or (None,)
        if not any(
            record_identity_eligible(eligibility, kind, race=race, subrace=branch)
            for kind in kinds for race in races for branch in branches
        ):
            raise ValueError("eligibility has no satisfiable character identity")
