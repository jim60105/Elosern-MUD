"""Frozen side-effect-free action preview shared by presentation and adapters.

This module factors the resolver's pure ownership, resource, target,
capability, effect-prefix, and time-metadata checks into a read-only preview
query. It reports enabled state, the exact stable rejection reason and resource
detail when disabled, and the valid targets or applicable AREA shorthands for a
menu. Modifier evaluation reads a no-create context from stored buff and
sexual-state data and never materializes ``entity.buffs``, ``entity.sexual``, or
any other lazy handler.

The preview never rolls randomness, stages or applies effects, constructs
EventLogs, invokes event-effect planners, mutates any persistent or
nonpersistent state, or advances world time. ``ActionResolver.preflight()`` and
``resolve()`` remain authoritative and rerun their required checks.
"""

from dataclasses import dataclass
from typing import Any

from world.rules.action import (
    DEFAULT_CAST_SECONDS,
    SKILL_TIME_OVERRIDES,
    ActionRequest,
    RejectReason,
    RejectedAction,
    _EFFECT_HANDLERS,
    _EFFECT_HANDLER_REQUIRED_CONTEXT,
    _effect_prefix,
    _step1_divine_arts_gate,
    _stored_trait_value,
)
from world.rules.buffs import BLOCKING_BUFF_KEYS, active_buff_keys_from_storage
from world.rules.combat_modifiers import (
    apply_cost_modifier,
    evaluate_combat_modifiers_no_create,
)
from world.rules.targeting import (
    AREA_SHORTHANDS,
    _target_identity,
    candidate_rejection,
    expand_target_shorthand,
)
from world.skills.registry import SKILL_REGISTRY, SkillKind, TargetSpec


@dataclass(frozen=True)
class ActionPreview:
    """One frozen, side-effect-free availability report for an owned skill.

    Attributes:
        skill_key: The stable skill key being previewed.
        enabled: Whether the skill can currently be used at all.
        reason: The first stable rejection reason when disabled, else ``None``.
        detail: The exact rejected resource or target key when disabled.
        valid_targets: Participant entities that pass the ordered candidate
            checks, or an empty tuple when none were provided or none survived.
        shorthands: Approved AREA shorthands that expand to at least one valid
            candidate for this skill, or an empty tuple for non-AREA skills.
    """

    skill_key: str
    enabled: bool
    reason: RejectReason | None
    detail: str | None
    valid_targets: tuple[Any, ...]
    shorthands: tuple[str, ...]


def _disabled(
    skill_key: str,
    reason: RejectReason,
    detail: str | None,
) -> ActionPreview:
    return ActionPreview(skill_key, False, reason, detail, (), ())


def _skill_wide_failure(
    actor: Any,
    skill_key: str,
    context: Any,
) -> tuple[RejectReason, str] | None:
    """Return the first skill-wide rejection ``(reason, detail)`` or ``None``.

    Mirrors ``ActionResolver.preflight()``'s ordering: ownership and active
    kind, resources, capability (including ``actions_per_turn == 0``),
    registered effect prefixes, and time metadata.
    """
    skill = SKILL_REGISTRY.get(skill_key)
    if skill is None or skill_key not in actor.skills.owned_keys():
        return RejectReason.UNKNOWN_SKILL, skill_key
    if skill.kind is not SkillKind.ACTIVE:
        return RejectReason.SKILL_NOT_ACTIVE, skill_key
    if not skill.usable_out_of_combat and context.battlefield is None:
        return RejectReason.SKILL_NOT_USABLE_OUT_OF_COMBAT, skill_key
    try:
        _step1_divine_arts_gate(actor, skill)
    except RejectedAction as rejection:
        return rejection.reason, rejection.detail
    bundle = evaluate_combat_modifiers_no_create(actor)
    for resource_key, amount in skill.cost.items():
        adjusted = apply_cost_modifier(amount, bundle.get(f"{resource_key}_cost"))
        if _stored_trait_value(getattr(actor.traits, resource_key)) < adjusted:
            return RejectReason.INSUFFICIENT_RESOURCE, resource_key
    active_keys = active_buff_keys_from_storage(actor)
    if active_keys & BLOCKING_BUFF_KEYS:
        return RejectReason.ACTION_FORBIDDEN, str(getattr(actor, "key", "?"))
    if bundle.get("actions_per_turn", 1) == 0:
        return RejectReason.ACTION_FORBIDDEN, str(getattr(actor, "key", "?"))
    for effect_id in skill.effects:
        if _effect_prefix(effect_id) not in _EFFECT_HANDLERS:
            return RejectReason.UNKNOWN_EFFECT_ID, effect_id
    event_keys = set(getattr(context, "event_context", None) or {})
    for effect_id in skill.effects:
        prefix = _effect_prefix(effect_id)
        missing = _EFFECT_HANDLER_REQUIRED_CONTEXT[prefix] - event_keys
        if missing:
            return (
                RejectReason.MISSING_EFFECT_CONTEXT,
                f"missing event_context key {sorted(missing)[0]!r}",
            )
    seconds = SKILL_TIME_OVERRIDES.get(skill.key, DEFAULT_CAST_SECONDS)
    if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds < 0:
        return RejectReason.TIME_COST_LOOKUP_FAILED, f"{skill.key}: {seconds!r}"
    return None


def _request_for(actor: Any, skill_key: str, context: Any) -> ActionRequest:
    """Build a lightweight frozen request for candidate validation."""
    return ActionRequest(actor=actor, skill_key=skill_key, targets=[], context=context)


def _valid_candidates(
    actor: Any,
    skill_key: str,
    context: Any,
    skill: Any,
    candidates: list[Any],
) -> tuple[tuple[Any, ...], tuple[RejectReason, str] | None]:
    """Filter candidates through the ordered target checks.

    Returns ``(valid_targets, first_failure)``. NONE never accepts candidates;
    SELF binds the actor; SINGLE keeps passing candidates for the menu; AREA
    keeps passing candidates and reports a failure only when none survive.
    """
    request = _request_for(actor, skill_key, context)
    if skill.target_spec is TargetSpec.NONE:
        # A NONE skill never accepts targets: the panel passes the whole roster
        # as a candidate pool, so preview must ignore it rather than treat it
        # as caller-supplied input. Submitted NONE targets are rejected by
        # ``revalidate_submission`` and ``resolve_targets``.
        return (), None
    if skill.target_spec is TargetSpec.SELF:
        # SELF binds the actor regardless of the menu candidate pool; the
        # player-facing facade and wire schema accept no SELF target field.
        failure = candidate_rejection(request, actor, skill)
        if failure is not None:
            return (), failure
        return (actor,), None
    valid: list[Any] = []
    first_failure: tuple[RejectReason, str] | None = None
    for target in candidates:
        failure = candidate_rejection(request, target, skill)
        if failure is None:
            valid.append(target)
        elif first_failure is None:
            first_failure = failure
    if skill.target_spec is TargetSpec.SINGLE and not valid and first_failure is not None:
        return (), first_failure
    return tuple(valid), None


def _applicable_shorthands(
    actor: Any,
    skill_key: str,
    context: Any,
    skill: Any,
) -> tuple[str, ...]:
    """Return approved AREA shorthands that expand to a valid target."""
    if skill.target_spec is not TargetSpec.AREA or context.battlefield is None:
        return ()
    applicable: list[str] = []
    for shorthand in AREA_SHORTHANDS:
        try:
            expanded = expand_target_shorthand(actor, context, shorthand)
        except RejectedAction:
            continue
        valid, _ = _valid_candidates(
            actor, skill_key, context, skill, list(expanded)
        )
        if valid:
            applicable.append(shorthand)
    return tuple(applicable)


def preview_skill(
    actor: Any,
    skill_key: str,
    context: Any,
    candidates: list[Any] | None = None,
) -> ActionPreview:
    """Build a frozen availability preview for one owned skill.

    ``candidates`` is an optional pool of participant entities to validate as
    targets (for example the active session roster). When omitted, only the
    skill-wide checks run and ``valid_targets`` stays empty.
    """
    failure = _skill_wide_failure(actor, skill_key, context)
    if failure is not None:
        return _disabled(skill_key, *failure)
    skill = SKILL_REGISTRY[skill_key]
    if candidates is None:
        shorthands = _applicable_shorthands(actor, skill_key, context, skill)
        return ActionPreview(skill_key, True, None, None, (), shorthands)
    valid, target_failure = _valid_candidates(
        actor, skill_key, context, skill, list(candidates)
    )
    if target_failure is not None:
        return _disabled(skill_key, *target_failure)
    shorthands = _applicable_shorthands(actor, skill_key, context, skill)
    if skill.target_spec in (TargetSpec.SINGLE, TargetSpec.AREA) and not valid:
        reason = (
            RejectReason.NO_VALID_TARGETS_IN_AREA
            if skill.target_spec is TargetSpec.AREA
            else RejectReason.TARGET_SPEC_MISMATCH
        )
        return _disabled(skill_key, reason, skill_key)
    return ActionPreview(skill_key, True, None, None, tuple(valid), shorthands)


def revalidate_submission(
    actor: Any,
    skill_key: str,
    context: Any,
    targets: list[Any] | str,
) -> ActionPreview:
    """Revalidate one submitted target value against current canonical state.

    Used by adapters and the combat-session facade immediately before
    initiative. Applies the exact shape and candidate rules shared with final
    target resolution so a stale or tampered request rejects with a matching
    stable reason before any round begins.
    """
    failure = _skill_wide_failure(actor, skill_key, context)
    if failure is not None:
        return _disabled(skill_key, *failure)
    skill = SKILL_REGISTRY[skill_key]
    request = _request_for(actor, skill_key, context)
    try:
        if skill.target_spec is TargetSpec.NONE:
            if isinstance(targets, str) or targets:
                raise RejectedAction(RejectReason.TARGET_SPEC_MISMATCH, skill_key)
            resolved: list[Any] = []
        elif skill.target_spec is TargetSpec.SELF:
            if isinstance(targets, str) or targets:
                raise RejectedAction(RejectReason.TARGET_SPEC_MISMATCH, skill_key)
            resolved = [actor]
        elif skill.target_spec is TargetSpec.SINGLE:
            if isinstance(targets, str):
                raise RejectedAction(RejectReason.TARGET_SPEC_MISMATCH, skill_key)
            if len(targets) != 1:
                raise RejectedAction(RejectReason.TARGET_SPEC_MISMATCH, skill_key)
            failure = candidate_rejection(request, targets[0], skill)
            if failure is not None:
                raise RejectedAction(*failure)
            resolved = list(targets)
        else:  # AREA
            if isinstance(targets, str):
                expanded = expand_target_shorthand(actor, context, targets)
                resolved, _ = _valid_candidates(
                    actor, skill_key, context, skill, list(expanded)
                )
                if not resolved:
                    raise RejectedAction(
                        RejectReason.NO_VALID_TARGETS_IN_AREA, skill_key
                    )
            elif not targets:
                raise RejectedAction(RejectReason.NO_VALID_TARGETS_IN_AREA, skill_key)
            else:
                # Mirror final target resolution: an explicit AREA list must be
                # unique by identity, so preview never drifts from preflight.
                seen: set[tuple[str, int]] = set()
                for target in targets:
                    identity = _target_identity(target)
                    if identity in seen:
                        raise RejectedAction(
                            RejectReason.TARGET_SPEC_MISMATCH, skill_key
                        )
                    seen.add(identity)
                resolved, _ = _valid_candidates(
                    actor, skill_key, context, skill, list(targets)
                )
                if not resolved:
                    raise RejectedAction(
                        RejectReason.NO_VALID_TARGETS_IN_AREA, skill_key
                    )
    except RejectedAction as rejection:
        return _disabled(skill_key, rejection.reason, rejection.detail)
    return ActionPreview(skill_key, True, None, None, tuple(resolved), ())


# Public read-only shapes accepted by preview and revalidation consumers.
SHAPES = tuple(TargetSpec)
