"""Subject-scoped cast conditions and interaction policy validation (light-sacrament-casting).

Pure, side-effect-free validation of state thresholds and contact-ritual
semantics for spell casting, evaluated before initiative and rechecked at
final resolution.
"""

from typing import TYPE_CHECKING, Any

from world.skills.cast_conditions import CastCondition, CastConditionSubject
from world.rules.rulebook.schema import evaluate_condition

if TYPE_CHECKING:
    from world.rules.targeting import ActionContext

def build_no_create_condition_context(entity: Any) -> dict[str, Any]:
    """Build condition context from stored state only without materializing handlers.

    Reuses the combat_modifiers builder directly so evaluation is strictly
    pure and never materialization-history dependent.
    """
    from world.rules.combat_modifiers import (
        build_no_create_condition_context as _base_builder,
    )

    return _base_builder(entity)


def evaluate_cast_conditions(actor: Any, targets: list[Any], skill: Any) -> None:
    """Evaluate all declared SkillDef.cast_conditions.

    Raises RejectedAction(RejectReason.CAST_CONDITION_UNMET) if any condition is unsatisfied.
    """
    from world.rules.action import RejectReason, RejectedAction

    conditions = getattr(skill, "cast_conditions", ())
    if not conditions:
        return

    actor_context: dict[str, Any] | None = None

    for cond in conditions:
        if cond.subject is CastConditionSubject.ACTOR:
            if actor_context is None:
                actor_context = build_no_create_condition_context(actor)
            if not evaluate_condition(cond.condition, actor_context):
                raise RejectedAction(
                    RejectReason.CAST_CONDITION_UNMET,
                    f"actor condition unmet: {cond.condition}",
                )
        elif cond.subject is CastConditionSubject.EACH_TARGET:
            for target in targets:
                target_context = build_no_create_condition_context(target)
                if not evaluate_condition(cond.condition, target_context):
                    raise RejectedAction(
                        RejectReason.CAST_CONDITION_UNMET,
                        f"target {getattr(target, 'key', repr(target))} condition unmet: {cond.condition}",
                    )


def evaluate_interaction_policy(
    actor: Any,
    targets: list[Any],
    context: Any,
    skill: Any,
) -> None:
    """Evaluate SkillDef.interaction (InteractionPolicy) contact and capability requirements.

    Raises RejectedAction(RejectReason.CAST_CONDITION_UNMET) on contact or capability failure.
    """
    from world.rules.action import RejectReason, RejectedAction, _stored_trait_value
    from world.rules.buffs import blocks_action

    interaction = getattr(skill, "interaction", None)
    if interaction is None:
        return

    if interaction.contact:
        for target in targets:
            if interaction.distinct_participants and target is actor:
                raise RejectedAction(
                    RejectReason.CAST_CONDITION_UNMET,
                    "contact ritual requires distinct participants",
                )
            if not context.is_present(actor, target):
                raise RejectedAction(
                    RejectReason.CAST_CONDITION_UNMET,
                    f"target {getattr(target, 'key', repr(target))} is not present for contact",
                )
            if not context.is_in_range(actor, target):
                raise RejectedAction(
                    RejectReason.CAST_CONDITION_UNMET,
                    f"target {getattr(target, 'key', repr(target))} is out of range for contact",
                )
            try:
                alive = _stored_trait_value(target.traits.hp) > 0
            except (AttributeError, KeyError):
                alive = False
            if not alive:
                raise RejectedAction(
                    RejectReason.CAST_CONDITION_UNMET,
                    f"target {getattr(target, 'key', repr(target))} is dead",
                )
            battlefield = getattr(context, "battlefield", None)
            if battlefield is not None:
                fled = getattr(battlefield, "fled", ())
                target_key = getattr(target, "key", "")
                if target_key in fled or target in fled:
                    raise RejectedAction(
                        RejectReason.CAST_CONDITION_UNMET,
                        f"target {getattr(target, 'key', repr(target))} has fled",
                    )
            if interaction.target_capable:
                if (
                    getattr(target, "attributes", None) is not None
                    and target.attributes.has("buffs")
                    and blocks_action(target)
                ):
                    raise RejectedAction(
                        RejectReason.CAST_CONDITION_UNMET,
                        f"target {getattr(target, 'key', repr(target))} is not action capable",
                    )
