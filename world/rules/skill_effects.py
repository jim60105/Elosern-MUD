"""Deterministic state writes for skill effects.

The future ``ActionResolver`` calls these core primitives only after it has
validated ownership, resources, and targets. Keeping writes under
``world.rules`` preserves the project's single-writer boundary.
"""

from typing import Any

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
    """Persist grant data after the resolver has validated the action."""
    validate_conferrable_skill(skill_key)
    grants = list(entity.db.skill_grants or [])
    grants.append(ConferredSkillGrant(source_key, skill_key, scale))
    entity.db.skill_grants = grants


def apply_disguise_effect(entity: Any, overrides: dict[str, int]) -> None:
    """Persist display-only overrides after deterministic resolution."""
    entity.db.disguised_stats = dict(overrides)
