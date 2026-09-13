"""Shared combat-state gates for deterministic action pipelines.

This module exists so a skill-effect combat-state gate does not live in the
targeting module: ``damage_requires_battlefield()`` answers "may this skill's
effects run outside combat", which is neither presence, alive, range, nor
faction — it was in ``targeting.py`` only because that is where it was
written. Keeping it here rather than inside one of its two callers preserves
the spec's "ONE shared expression" property: ``world.rules.action`` and
``world.rules.action_preview`` both import the identical condition, and
neither one's private helpers become the other's dependency. Importing it
from the targeting module would instead force non-targeting callers to depend
on the target resolver to ask a question the resolver never answers.
"""

from typing import Any

from world.skills.effects import DamageEffect
from world.skills.registry import SkillDef


def damage_requires_battlefield(skill: SkillDef, context: Any) -> bool:
    """Return whether a damaging skill is being attempted without a battlefield.

    The ONE shared expression of the damaging-action gate's condition
    (sanctioned combat-state gate body, gate 2 of 2): true when the resolved
    skill's typed ``parsed_effects`` carry at least one
    ``world.skills.effects.DamageEffect`` **and** the caller's context carries
    no battlefield. Consumed by ``ActionResolver``'s step 1 and by the shared
    preview, so resolution, preview, and combat-session submission
    revalidation can never disagree. Computed per request from the skill
    definition's own effects — never from a registry-key enumeration.

    Indirect hp movement is deliberately NOT damage for this gate: a
    ``SexualDrainEffect`` moves the target's pleasure into the caster's own
    pools, never subtracting hp, matching ``overwhelm-threshold``'s
    ``commanded_damage_reaches_enemy()`` so both damage-shaped questions in
    the codebase read the same definition.
    """
    # Sanctioned combat-state gate body (damaging-action gate): the reason at
    # each call site names the player-facing rule; this condition tests for
    # the battlefield's absence.
    if context.battlefield is None:
        return any(isinstance(effect, DamageEffect) for effect in skill.parsed_effects)
    return False
