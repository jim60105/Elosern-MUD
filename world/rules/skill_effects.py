"""Deterministic state writes for skill effects.

The future ``ActionResolver`` calls these core primitives only after it has
validated ownership, resources, and targets. Keeping writes under
``world.rules`` preserves the project's single-writer boundary.
"""

from typing import Any

from world.lore.races import RACE_REGISTRY
from world.skills.effects import (
    DisguiseEffect,
    RuleTableEffect,
    SexualMasteryEffect,
    StatMultiplyEffect,
)
from world.skills.handler import ConferredSkillGrant
from world.skills.registry import SKILL_REGISTRY

# Gate-type (binary) effect classes that cannot be fractionally conferred:
# "partial spell unlock" or "partial disguise" has no defined meaning. The
# exclusion is structural — matching on class, not on a maintained list of
# forbidden skill keys — so a future gate-type effect class is automatically
# excluded without anyone remembering to update a blocklist. The retired
# ``element_mastery_rank`` prefix left this tuple together with the cast gate
# (magic-xp-engine-retirement); mastery skills now carry flavor effects and
# fall to the no-continuous-effect rejection below.
GATE_TYPE_EFFECT_CLASSES = (SexualMasteryEffect, DisguiseEffect)
# Continuous-valued effect classes that the grant consumers can resolve at a
# fractional scale (``SkillHandler.effective_value`` and the ``skill_owned``
# rule-table builder). A skill whose effects none of these classes recognize
# would be recorded as a silent no-op grant, so it is rejected too.
CONTINUOUS_EFFECT_CLASSES = (StatMultiplyEffect, RuleTableEffect)


def validate_conferrable_skill(skill_key: str) -> None:
    """Reject conferral of a skill that cannot be fractionally conferred.

    Raises ``RejectedAction(EFFECT_RESOLUTION_FAILED)`` when the referenced
    skill exists and either carries a gate-type (binary) effect or carries no
    continuous-valued effect any grant consumer can resolve. Unknown skill
    keys are allowed to pass here (the resolver validates the source's actual
    ownership); a nonexistent definition simply contributes nothing.
    """
    skill = SKILL_REGISTRY.get(skill_key)
    if skill is None:
        return
    from world.rules.action import RejectReason, RejectedAction

    if any(
        isinstance(effect, GATE_TYPE_EFFECT_CLASSES)
        for effect in skill.parsed_effects
    ):
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            f"skill {skill_key!r} carries a gate-type effect that cannot be "
            "partially conferred",
        )
    if not any(
        isinstance(effect, CONTINUOUS_EFFECT_CLASSES)
        for effect in skill.parsed_effects
    ):
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            f"skill {skill_key!r} has no continuous-valued effect to confer",
        )


def record_conferred_grant(
    entity: Any,
    source_key: str,
    skill_key: str,
    scale: float,
) -> None:
    """Persist one grant, replacing any earlier grant for the same pair.

    The store is keyed by ``(source_key, skill_key)``: a repeated conferral
    refreshes the scale instead of appending a second row that would compound
    the read-side multiplier, while grants from other sources for the same
    skill are preserved. Existing rows keep their relative order so the
    stored representation stays deterministic.
    """
    validate_conferrable_skill(skill_key)
    grants = list(entity.db.skill_grants or [])
    identity = (source_key, skill_key)
    for index, grant in enumerate(grants):
        if (grant.source_key, grant.skill_key) == identity:
            grants[index] = ConferredSkillGrant(source_key, skill_key, scale)
            break
    else:
        grants.append(ConferredSkillGrant(source_key, skill_key, scale))
    entity.db.skill_grants = grants


def revoke_conferred_grants(entity: Any) -> None:
    """Clear every conferral on one target: all skill grants and every
    conferred growth-rate buff instance, whatever their source.

    Total by design (design D1/D2): both writes ride one call so no caller
    can clear half the conferral vocabulary. The grant write is skipped when
    the store holds nothing — an absent attribute stays absent and an
    already-empty list stays untouched — and the buff clear writes nothing
    when no conferred instance is live, so revocation of a target with
    nothing conferred is a clean no-op that changes no stored state.
    """
    from world.rules.buffs import clear_conferred_growth_rates

    if entity.db.skill_grants:
        entity.db.skill_grants = []
    clear_conferred_growth_rates(entity)


def validate_source_owns_skill(actor: Any, skill_key: str) -> None:
    """Reject conferral of a skill the source does not directly own.

    Raises ``RejectedAction(EFFECT_RESOLUTION_FAILED)`` when ``skill_key``
    is absent from the actor's directly owned keys, so a conferred grant
    can never exceed — or be chained onward from — what its source holds.
    """
    from world.rules.action import RejectReason, RejectedAction

    if skill_key not in actor.skills.owned_keys():
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            f"source does not directly own skill {skill_key!r}",
        )


def derive_conferrable_skills(actor: Any) -> list[str]:
    """Derive the conferred set from the actor's direct ownership.

    One key per skill the actor directly owns that passes the conferrability
    shape validation, in owned order. The set is derived, never chosen: no
    caller names a skill, and ownership is read from ``owned_keys()`` only —
    the predicate ``_step1_ownership`` trusts — so a skill held merely as a
    conferred grant can never be re-conferred onward. The ownership
    precondition is enforced per candidate where the actor exists, keeping
    the whole conferral contract readable in this module.
    """
    from world.rules.action import RejectedAction

    conferrable: list[str] = []
    for skill_key in actor.skills.owned_keys():
        try:
            validate_conferrable_skill(skill_key)
        except RejectedAction:
            continue
        validate_source_owns_skill(actor, skill_key)
        conferrable.append(skill_key)
    return conferrable


def apply_disguise_effect(entity: Any, overrides: dict[str, int]) -> None:
    """Persist display-only overrides after deterministic resolution."""
    entity.db.disguised_stats = dict(overrides)


def mundane_veil_values() -> dict[str, int]:
    """The deterministic displayed combat five at the mundane ceilings.

    Each of the five keys a veil displays renders at the top of the
    corresponding mundane band the race registry declares for ``human``: the
    four static axes read ``static_baseline`` and ``hp`` reads the
    ``vital_baseline`` ceiling. No balance constant is duplicated here — a
    registry retune flows into every fresh veil automatically.
    """
    human = RACE_REGISTRY["human"]
    static = human.static_baseline
    return {
        "atk_phys": static.atk_phys[1],
        "agility": static.agility[1],
        "defense": static.defense[1],
        "magic_power": static.magic_power[1],
        "hp": human.vital_baseline.hp[1],
    }


def was_cast_placed(entity: Any) -> bool:
    """Whether the veil verb itself wrote the layer this entity carries.

    Absent-is-False: a record is written only by the veil verb, so no record
    means the layer came from an authored origin (an import record, preset
    activation, or the companion builder) or predates the record's
    introduction — every one of which reads the same as "not placed by the
    verb", with no migration required.
    """
    return bool(entity.db.disguise_placed_by_cast)


def record_cast_placement(entity: Any) -> None:
    """Record that the veil verb itself just wrote this entity's layer."""
    entity.db.disguise_placed_by_cast = True


def clear_disguise_effect(entity: Any) -> None:
    """Lift a disguise layer and its placement record in one operation."""
    del entity.db.disguised_stats
    del entity.db.disguise_placed_by_cast


def apply_divine_disguise(entity: Any) -> None:
    """Write a divine veil: the derived mapping plus its placement record.

    Composes the narrow display write with the placement record so the
    single-staged effect keeps ``apply_disguise_effect``'s own source free of
    trait expressions while still writing the record beside the mapping.
    """
    apply_disguise_effect(entity, mundane_veil_values())
    record_cast_placement(entity)


def reveal_can_pierce(entity: Any) -> bool:
    """Whether the entity carries a veil a reveal can lift.

    This world admits exactly one grade of veil, because only the
    bloodline-gated divine mystery can write one, so a reveal either lifts
    the veil it finds or finds none — there is no provenance to consult.
    This predicate is the single source of that answer, shared by the reveal
    write and the handler's stage-time outcome report.
    """
    return entity.db.disguised_stats is not None


def reveal_disguise_effect(entity: Any) -> bool:
    """Lift whatever veil the entity carries.

    Clears the display layer and its placement record in the same operation
    (``clear_disguise_effect``), so a reveal that finds a veil never leaves
    the record behind. Returns True when a veil was cleared and False for a
    reported no-op — nothing to reveal — so a failed reveal costs the action
    without leaking the veil's existence through a rejection.
    """
    if not reveal_can_pierce(entity):
        return False
    clear_disguise_effect(entity)
    return True
