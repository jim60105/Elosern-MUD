"""The sole state-writing gateway for skill invocation.

``ActionResolver`` orchestrates the pipeline steps owned by the sibling
modules: validation gates (steps 1-4b), effect routing (step 5), cost and
practice staging (steps 6/8), event-log construction (step 7), and the single
transactional commit. Importing this module registers the action-evidence
planner exactly once, mirroring the historical module tail.
"""

from dataclasses import replace
from typing import Any

from world.rules.progression import practice_claim_key, release_practice_claims

from world.rules.action.contracts import (
    _EFFECT_HANDLERS,
    _EFFECT_HANDLER_REQUIRED_CONTEXT,
    _EVENT_EFFECT_PLANNERS,
    _effect_prefix,
    _entity_key,
    _event_context,
    ActionRequest,
    ActionResult,
    CommitFailed,
    PendingEffect,
    RejectedAction,
    RejectReason,
)
from world.rules.action.costs import (
    _step6_resource_deduction,
    _step6_skill_practice,
    _step8_time_cost,
)
from world.rules.action.event_log import _step7_build_event_log
from world.rules.action.gates import (
    _step1_ownership,
    _step2_resource_check,
    _step3_targeting,
    _step4_capability,
    _step4a_spell_conditions,
    _step4b_sexual_resist_gate,
)
from world.rules.action.routing import (
    _bind_resolved_effect,
    _step5_effect_resolution,
    plan_effect_audiences,
)
from world.rules.action.transaction import _commit
from world.rules.action.effects.conferral import _conferral_empty_set_failure


class ActionResolver:
    """The sole state-writing gateway for skill invocation."""

    @staticmethod
    def preflight(request: ActionRequest) -> ActionResult:
        """Side-effect-free validation of one action before initiative.

        Runs the deterministic checks that never roll, stage effects, emit an
        ``EventLog``, mutate state, or advance world time: skill ownership,
        resource availability, target resolution, action capability, effect
        handler availability, and time-cost metadata. Returns the same named
        rejection categories as ``resolve()`` for those checks. A successful
        preflight does not guarantee the state survives earlier initiative
        actions; final resolution must still run the complete pipeline.
        """
        try:
            skill = _step1_ownership(request)
            _step2_resource_check(request.actor, skill, request.scale)
            targets = _step3_targeting(request, skill)
            _step4_capability(request.actor)
            _step4a_spell_conditions(request, skill, targets)
            base_context = _event_context(request)
            for i, effect_id in enumerate(skill.effects):
                prefix = _effect_prefix(effect_id)
                if prefix not in _EFFECT_HANDLERS:
                    raise RejectedAction(
                        RejectReason.UNKNOWN_EFFECT_ID,
                        effect_id,
                    )
                effect_context = _bind_resolved_effect(
                    base_context, skill, i, actor=request.actor, targets=targets
                )
                missing = _EFFECT_HANDLER_REQUIRED_CONTEXT[prefix] - effect_context.keys()
                if missing:
                    raise RejectedAction(
                        RejectReason.MISSING_EFFECT_CONTEXT,
                        f"missing event_context key {sorted(missing)[0]!r}",
                    )
                failure = _conferral_empty_set_failure(request.actor, skill)
                if failure is not None:
                    raise RejectedAction(failure[0], failure[1])
            plan_effect_audiences(request.actor, request.context, skill, targets)
            _step8_time_cost(request, skill)
        except RejectedAction as rejection:  # observability: ignore R2: the rejection is returned to the caller as ActionResult.rejected; it is reported, not swallowed
            return ActionResult.rejected(rejection.reason, rejection.detail)
        return ActionResult.success(None, None)

    @staticmethod
    def resolve(request: ActionRequest) -> ActionResult:
        try:
            skill = _step1_ownership(request)
            _step2_resource_check(request.actor, skill, request.scale)
            targets = _step3_targeting(request, skill)
            _step4_capability(request.actor)
            _step4a_spell_conditions(request, skill, targets)
            targets, resist_pending, generic_resisted = _step4b_sexual_resist_gate(
                request,
                skill,
                targets,
            )
            if generic_resisted:
                pending = list(resist_pending)
                routed_targets = ()
            else:
                routed_targets = plan_effect_audiences(
                    request.actor,
                    request.context,
                    skill,
                    targets,
                )
                pending = resist_pending + _step5_effect_resolution(
                    request,
                    skill,
                    targets,
                    routed_targets=routed_targets,
                )
            from world.rules.buffs import (
                has_positional_marker,
                remove_positional_markers,
            )
            from world.rules.spell_conditions import is_strike_class

            if is_strike_class(skill) and has_positional_marker(request.actor):
                # Design D4: the self-return clear is staged BEFORE the
                # strike's damage leg, on the ``buffs`` surface only —
                # ``_commit`` snapshots that surface before any pending
                # effect applies, so a failed settlement restores it.
                pending.insert(
                    0,
                    PendingEffect(
                        request.actor,
                        f"self_return_clear|{_entity_key(request.actor)}",
                        frozenset({"buffs"}),
                        lambda actor=request.actor: remove_positional_markers(actor),
                    ),
                )
            pending += _step6_resource_deduction(request.actor, skill, request.scale)
            delivered_recipients: list[Any] = []
            practice_claims: list[tuple[Any, str, Any]] = []
            unlock_lines: list[str] = []
            if not generic_resisted:
                seen_delivered_keys: set[Any] = set()
                for eff_targets in routed_targets:
                    for target in eff_targets:
                        t_key = practice_claim_key(request.actor, skill.key, target)[2]
                        if t_key not in seen_delivered_keys:
                            seen_delivered_keys.add(t_key)
                            delivered_recipients.append(target)
                pending += _step6_skill_practice(
                    request,
                    skill,
                    delivered_recipients,
                    practice_claims,
                    unlock_lines,
                )
            event_log = _step7_build_event_log(request, skill, pending)
            try:
                for planner in _EVENT_EFFECT_PLANNERS.values():
                    for effect in planner(request, event_log):
                        if not isinstance(effect, PendingEffect):
                            raise TypeError(
                                "event-effect planner returned a non-PendingEffect value",
                            )
                        pending.append(effect)
            except RejectedAction:
                raise
            except Exception as error:
                raise RejectedAction(
                    RejectReason.EVENT_LOG_CONSTRUCTION_FAILED,
                    f"event-effect planner failed: {error}",
                ) from error
            time_cost = _step8_time_cost(request, skill)
            event_log = replace(event_log, time_cost_seconds=time_cost)
        except RejectedAction as rejection:  # observability: ignore R2: the rejection is returned to the caller as ActionResult.rejected; it is reported, not swallowed
            return ActionResult.rejected(rejection.reason, rejection.detail)
        try:
            _commit(
                pending,
                # Design context convention: char is the pk, never the
                # user-controlled display key (stable join, no PII retention).
                char=str(request.actor.pk),
                action=request.skill_key,
            )
        except CommitFailed as failure:  # observability: ignore R2: the commit failure is returned as ActionResult.rejected after the rollback/restore path logged every failed surface restore
            # The staged practice awards rolled back with everything else; the
            # dedupe claims they took must be released so a legitimate
            # same-tick retry still accrues (rubber-duck DC3 finding).
            release_practice_claims(practice_claims)
            return ActionResult.rejected(failure.reason, failure.detail)
        notifications = tuple(effect.notify for effect in pending if effect.notify)
        # Unlock lines ride the same post-commit channel: appended here only
        # because the commit above succeeded. A rolled-back action returns at
        # the CommitFailed branch above and its sink lines die with the result.
        if unlock_lines:
            notifications = notifications + tuple(unlock_lines)
        return ActionResult.success(event_log, time_cost, notifications)

