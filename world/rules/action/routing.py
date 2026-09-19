"""Effect routing: audience planning, context binding, step-5 dispatch.

Turns validated targets into per-effect recipient subsets, binds each
occurrence's authored policy into a trusted context, and dispatches every
declared effect to its registered handler.
"""

from dataclasses import replace
from typing import Any

from world.rules.targeting import ActionContext, Relation
from world.skills.effects import EffectAudience, ResolvedEffect
from world.skills.registry import SkillDef

from world.rules.action.contracts import (
    _EFFECT_HANDLERS,
    _EFFECT_HANDLER_REQUIRED_CONTEXT,
    _EFFECT_HANDLER_SURFACES,
    _effect_prefix,
    _entity_key,
    _event_context,
    ActionRequest,
    PendingEffect,
    RejectedAction,
    RejectReason,
)
from world.rules.action.gates import _stored_trait_value, stored_gauge_pair


def _occurrence_scale(context: dict[str, Any]) -> float:
    """Return the occurrence's declared scale (its ``EffectPolicy.coefficient``).

    The resolution pipeline binds the occurrence's own policy into the
    reserved ``resolved_effect`` context key; a direct caller without a
    bound policy falls back to the identity scale so the handlers stay
    deterministic outside the pipeline too.
    """
    resolved = context.get("resolved_effect")
    policy = resolved.policy if resolved is not None else None
    return float(policy.coefficient) if policy is not None else 1.0


def _require_context(context: dict[str, Any], prefix: str) -> dict[str, Any]:
    """Return the declared event-context values for one effect-handler prefix.

    Reads the handler's registration declaration so resolution-time
    requirements can never drift from preflight (design D1).
    """
    declared = _EFFECT_HANDLER_REQUIRED_CONTEXT[prefix]
    missing = declared - set(context)
    if missing:
        raise RejectedAction(
            RejectReason.MISSING_EFFECT_CONTEXT,
            f"missing event_context key {sorted(missing)[0]!r}",
        )
    return {key: context[key] for key in declared}


def _bind_resolved_effect(
    base_context: dict[str, Any],
    skill: SkillDef,
    ordinal: int,
    actor: Any = None,
    targets: list[Any] | None = None,
) -> dict[str, Any]:
    """Synthesize trusted effect context for one effect execution ordinal.

    Deliberately creates a shallow copy of ``base_context`` with the reserved
    ``resolved_effect`` key bound to that ordinal's authored policy, isolating
    effects from cross-effect mutations and overriding any caller-supplied
    forgery without mutating the request dictionary.
    """
    effect_context = dict(base_context)
    policy = skill.effect_policies[ordinal]
    if policy.magnitude is not None and actor is not None:
        from world.skills.effects import StateMagnitudeSubject

        target_entity = targets[0] if targets else None
        entity = (
            actor
            if policy.magnitude.subject == StateMagnitudeSubject.ACTOR
            else target_entity
        )
        if entity is not None:
            try:
                from world.rules.state_reactions import compute_state_magnitude

                computed_magnitude = compute_state_magnitude(
                    policy.magnitude, entity, actor=actor
                )
                policy = replace(policy, coefficient=computed_magnitude)
            except Exception as error:
                raise RejectedAction(
                    RejectReason.EFFECT_RESOLUTION_FAILED,
                    f"state magnitude computation failed for {policy.magnitude}: {error}",
                ) from error
    effect_context["resolved_effect"] = ResolvedEffect(
        policy=policy,
        source_skill=skill,
    )
    return effect_context


def _matches_audience_condition(target: Any, condition: str | None) -> bool:
    """Evaluate one declarative audience condition against a target entity.

    Closed gauge-state vocabulary:
    - 'mp_max_zero': target has an MP gauge whose maximum is 0
    - 'mp_positive': target has an MP gauge whose maximum is > 0

    An entity lacking traits or an MP gauge matches neither condition.
    """
    if condition is None:
        return True
    traits = getattr(target, "traits", None)
    if traits is None or not hasattr(traits, "mp"):
        return False
    trait = getattr(traits, "mp")
    if trait is None:
        return False
    _, maximum = stored_gauge_pair(target, "mp")
    if condition == "mp_max_zero":
        return maximum == 0
    if condition == "mp_positive":
        return maximum > 0
    return False


def plan_effect_audiences(
    actor: Any,
    context: ActionContext,
    skill: SkillDef,
    targets: list[Any],
) -> tuple[list[Any], ...]:
    """Derive the per-effect recipient subsets over the validated target pool.

    Shared pure audience planning used by ``ActionResolver.preflight()``,
    final resolution, and preview validation. Returns one target list per
    declared effect in ``skill.effects``, matching ``skill.effect_policies``.

    - ``SELECTED``: returns a shallow copy of the validated target pool.
    - ``ALLIES``: filters validated targets to those with ``relation_to`` in
      ``(Relation.SELF, Relation.ALLY)``; never adds unselected entities.
    - ``ENEMIES``: filters validated targets to those with ``relation_to == Relation.ENEMY``;
      never adds unselected entities.
    - ``SELF``: binds ``[actor]`` after presence, alive, and range checks;
      never duplicates the actor.

    If a skill declares at least one non-``SELECTED`` audience and every
    effect's routed audience is empty, raises
    ``RejectedAction(RejectReason.NO_VALID_TARGETS_IN_AREA, skill.key)``.
    """
    routed: list[list[Any]] = []
    actor_valid: bool | None = None

    for policy in skill.effect_policies:
        aud = policy.audience
        if aud is EffectAudience.SELECTED:
            candidate = list(targets)
        elif aud is EffectAudience.ALLIES:
            candidate = [
                t for t in targets
                if context.relation_to(actor, t) in (Relation.SELF, Relation.ALLY)
            ]
        elif aud is EffectAudience.ENEMIES:
            candidate = [
                t for t in targets
                if context.relation_to(actor, t) in (Relation.ENEMY,)
            ]
        elif aud is EffectAudience.SELF:
            if actor_valid is None:
                alive = False
                try:
                    alive = _stored_trait_value(actor.traits.hp) > 0
                except (AttributeError, KeyError):  # observability: ignore R2: actor has no hp trait or lacks traits container, treating as not alive
                    pass
                actor_valid = (
                    context.is_present(actor, actor)
                    and alive
                    and context.is_in_range(actor, actor)
                )
            candidate = [actor] if actor_valid else []
        else:
            candidate = list(targets)

        if policy.audience_condition is not None:
            candidate = [
                t for t in candidate
                if _matches_audience_condition(t, policy.audience_condition)
            ]

        routed.append(candidate)

    if any(
        p.audience is not EffectAudience.SELECTED or p.audience_condition is not None
        for p in skill.effect_policies
    ):
        if not any(routed):
            raise RejectedAction(
                RejectReason.NO_VALID_TARGETS_IN_AREA,
                skill.key,
            )

    return tuple(routed)


def _step5_effect_resolution(
    request: ActionRequest,
    skill: SkillDef,
    targets: list[Any],
    routed_targets: tuple[list[Any], ...] | None = None,
) -> list[PendingEffect]:
    pending: list[PendingEffect] = []
    base_context = _event_context(request)
    for i, effect_id in enumerate(skill.effects):
        prefix = _effect_prefix(effect_id)
        handler = _EFFECT_HANDLERS.get(prefix)
        if handler is None:
            raise RejectedAction(RejectReason.UNKNOWN_EFFECT_ID, effect_id)
        effect_targets = (
            routed_targets[i] if routed_targets is not None else targets
        )
        policy = skill.effect_policies[i]
        if policy.audience is not EffectAudience.SELECTED and not effect_targets:
            continue
        effect_context = _bind_resolved_effect(
            base_context, skill, i, actor=request.actor, targets=effect_targets
        )
        try:
            effects = handler(
                request.actor,
                effect_targets,
                effect_id,
                effect_context,
                request.scale,
            )
            surfaces = _EFFECT_HANDLER_SURFACES[prefix]
            for effect in effects:
                if not isinstance(effect, PendingEffect):
                    raise TypeError(
                        "effect handler returned a non-PendingEffect value"
                    )
                pending.append(replace(effect, surfaces=surfaces))
        except RejectedAction:
            raise
        except Exception as error:
            raise RejectedAction(
                RejectReason.EFFECT_RESOLUTION_FAILED,
                f"{effect_id}: {error}",
            ) from error
    return pending
