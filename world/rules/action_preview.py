"""Frozen side-effect-free action preview shared by presentation and adapters.

This module factors the resolver's pure ownership, resource, target,
capability, cast, interaction, effect-prefix, and time-metadata checks into a
read-only preview query. It reports enabled state, the exact stable rejection
reason and resource detail when disabled, and the valid targets or applicable
AREA shorthands for a menu. The ordered skill-wide gates and the target-
dependent cast/interaction/displacement gates are not mirrored here: they are
the resolver's own shared bodies in :mod:`world.rules.action.gates`, so the
preview, the submission revalidation and settlement can never disagree about
which cast is legal. Modifier evaluation reads a no-create context from stored
buff and sexual-state data and never materializes ``entity.buffs``,
``entity.sexual``, or any other lazy handler.

The preview never rolls randomness, stages or applies effects, constructs
EventLogs, invokes event-effect planners, mutates any persistent or
nonpersistent state, or advances world time. ``ActionResolver.preflight()`` and
``resolve()`` remain authoritative and rerun their required checks.

One decision may pass a decision-local read set (``readings``) that was read
once for that decision -- the monster-AI decision inputs do exactly that -- so
validating many plans reuses one read of the registry, the owned-skill
metadata, the adjusted costs, the participant traits and the buff projections
instead of re-reading them per candidate. The reads are never carried across
decisions.
"""

from dataclasses import dataclass
from typing import Any

from world.rules.action import (
    DEFAULT_CAST_SECONDS,
    SKILL_TIME_OVERRIDES,
    RejectReason,
    RejectedAction,
    _EFFECT_HANDLERS,
    _EFFECT_HANDLER_REQUIRED_CONTEXT,
    _conferral_empty_set_failure,
    _effect_prefix,
    plan_effect_audiences,
)
from world.rules.action.gates import (
    skill_wide_failure,
    spell_condition_failure,
)
from world.rules.targeting import (
    AREA_SHORTHANDS,
    _target_identity,
    candidate_rejection,
    expand_target_shorthand,
    forbidden_self_failure,
    requirement_for,
)
from world.skills.effects import EffectAudience
from world.skills.registry import SKILL_REGISTRY, TargetSpec


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


def adjusted_cost(actor: Any, skill: Any, scale: float = 1.0) -> dict[str, int]:
    """Return one skill's current adjusted cost for ``actor`` at ``scale``.

    Delegates to the resolver's own step-2/step-6 cost formula so a preview
    displays exactly the amounts the resolver checks and deducts. Modifiers
    are read through the no-create context only.
    """
    from world.rules.action.gates import _adjusted_costs

    return dict(_adjusted_costs(actor, skill, scale))


def _skill_wide_failure(
    actor: Any,
    skill_key: str,
    context: Any,
    scale: float = 1.0,
    readings: Any = None,
) -> tuple[RejectReason, str] | None:
    """Return the first skill-wide rejection ``(reason, detail)`` or ``None``.

    The ordered shared gates of ``world.rules.action.gates`` -- ownership,
    active kind, identity, lineage, out-of-combat availability, the damaging
    gate, the freeform (proficiency) gate, resources checked against the
    scaled ``mp`` cost, and capability including ``actions_per_turn == 0`` --
    followed by the presentation-side completeness checks: registered effect
    prefixes, the event context each handler requires, an empty conferral set
    and time metadata. The retired numeric cast gate
    (``magic-xp-engine-retirement``) has no preview-side counterpart any more.
    """
    failure = skill_wide_failure(
        actor, skill_key, context, scale, readings=readings
    )
    if failure is not None:
        return failure
    skill = (
        SKILL_REGISTRY[skill_key]
        if readings is None
        else readings.skill(skill_key)
    )
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
    failure = _conferral_empty_set_failure(actor, skill)
    if failure is not None:
        return failure
    seconds = SKILL_TIME_OVERRIDES.get(skill.key, DEFAULT_CAST_SECONDS)
    if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds < 0:
        return RejectReason.TIME_COST_LOOKUP_FAILED, f"{skill.key}: {seconds!r}"
    return None


def _valid_candidates(
    actor: Any,
    context: Any,
    skill: Any,
    candidates: list[Any],
    readings: Any = None,
) -> tuple[tuple[Any, ...], tuple[RejectReason, str] | None]:
    """Filter candidates through the ordered checks of a complete plan.

    Returns ``(valid_targets, first_failure)``. NONE never accepts candidates;
    SELF binds the actor; SINGLE keeps passing candidates for the menu; AREA
    keeps passing candidates and reports a failure only when none survive.

    A SINGLE candidate is a complete plan on its own, so it must also pass the
    target-dependent cast, interaction and displacement gates the resolver runs
    after target resolution: a candidate failing only those is not an
    alternative the menu may advertise. An AREA or SELF plan is validated as
    the whole group it forms, by the caller that knows the plan.
    """
    if skill.target_spec is TargetSpec.NONE:
        # A NONE skill never accepts targets: the panel passes the whole roster
        # as a candidate pool, so preview must ignore it rather than treat it
        # as caller-supplied input. Submitted NONE targets are rejected by
        # ``revalidate_submission`` and ``resolve_targets``.
        return (), None
    if skill.target_spec is TargetSpec.SELF:
        # SELF binds the actor regardless of the menu candidate pool; the
        # player-facing facade and wire schema accept no SELF target field.
        failure = candidate_rejection(
            actor, context, requirement_for(skill), actor, readings=readings
        )
        if failure is None:
            failure = spell_condition_failure(
                actor, skill, context, [actor], readings
            )
        if failure is not None:
            return (), failure
        return (actor,), None
    valid: list[Any] = []
    first_failure: tuple[RejectReason, str] | None = None
    requirement = requirement_for(skill)
    for target in candidates:
        failure = candidate_rejection(
            actor, context, requirement, target, readings=readings
        )
        if failure is None and skill.target_spec is TargetSpec.SINGLE:
            failure = spell_condition_failure(
                actor, skill, context, [target], readings
            )
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
    readings: Any = None,
) -> tuple[str, ...]:
    """Return approved AREA shorthands that expand to a legal plan."""
    if skill.target_spec is not TargetSpec.AREA or context.battlefield is None:
        return ()
    applicable: list[str] = []
    for shorthand in AREA_SHORTHANDS:
        try:
            expanded = expand_target_shorthand(actor, context, shorthand)
        except RejectedAction:
            continue
        valid, _ = _valid_candidates(
            actor, context, skill, list(expanded), readings
        )
        if valid:
            if spell_condition_failure(
                actor, skill, context, list(valid), readings
            ) is not None:
                continue
            if any(p.audience is not EffectAudience.SELECTED for p in skill.effect_policies):
                try:
                    plan_effect_audiences(actor, context, skill, list(valid))
                except RejectedAction:
                    continue
            applicable.append(shorthand)
    return tuple(applicable)


def preview_skill(
    actor: Any,
    skill_key: str,
    context: Any,
    candidates: list[Any] | None = None,
    scale: float = 1.0,
    readings: Any = None,
) -> ActionPreview:
    """Build a frozen availability preview for one owned skill.

    ``candidates`` is an optional pool of participant entities to validate as
    targets (for example the active session roster). When omitted, only the
    skill-wide checks run and ``valid_targets`` stays empty. ``scale`` applies
    the step-1 freeform gate and the scaled resource check, so the preview
    reports the same availability the resolver will enforce. ``readings`` is
    the optional decision-local read set every plan of this preview reuses;
    omitting it re-reads live state per plan.
    """
    failure = _skill_wide_failure(actor, skill_key, context, scale, readings)
    if failure is not None:
        return _disabled(skill_key, *failure)
    skill = (
        SKILL_REGISTRY[skill_key]
        if readings is None
        else readings.skill(skill_key)
    )
    if candidates is None:
        # Without a candidate pool only the actor-scoped halves of the
        # target-dependent gates can be answered: an actor cast condition that
        # no target can satisfy still disables the skill, while every
        # per-target condition and the interaction/displacement gates have no
        # plan to reject yet.
        failure = spell_condition_failure(actor, skill, context, [], readings)
        if failure is not None:
            return _disabled(skill_key, *failure)
        shorthands = _applicable_shorthands(
            actor, skill_key, context, skill, readings
        )
        return ActionPreview(skill_key, True, None, None, (), shorthands)
    valid, target_failure = _valid_candidates(
        actor, context, skill, list(candidates), readings
    )
    if target_failure is not None:
        return _disabled(skill_key, *target_failure)
    shorthands = _applicable_shorthands(
        actor, skill_key, context, skill, readings
    )
    if skill.target_spec in (TargetSpec.SINGLE, TargetSpec.AREA) and not valid:
        reason = (
            RejectReason.NO_VALID_TARGETS_IN_AREA
            if skill.target_spec is TargetSpec.AREA
            else RejectReason.TARGET_SPEC_MISMATCH
        )
        return _disabled(skill_key, reason, skill_key)
    if skill.target_spec is TargetSpec.AREA and valid:
        # The group this menu advertises IS the plan an AREA action submits, so
        # it has to pass the same target-dependent gates settlement applies to
        # it before the audience routing below ever runs.
        failure = spell_condition_failure(
            actor, skill, context, list(valid), readings
        )
        if failure is not None:
            return _disabled(skill_key, *failure)
    if valid and any(p.audience is not EffectAudience.SELECTED for p in skill.effect_policies):
        try:
            plan_effect_audiences(actor, context, skill, list(valid))
        except RejectedAction as rejection:
            return _disabled(skill_key, rejection.reason, rejection.detail)
    return ActionPreview(skill_key, True, None, None, tuple(valid), shorthands)


def revalidate_submission(
    actor: Any,
    skill_key: str,
    context: Any,
    targets: list[Any] | str,
    scale: float = 1.0,
    readings: Any = None,
) -> ActionPreview:
    """Revalidate one submitted target value against current canonical state.

    Used by adapters and the combat-session facade immediately before
    initiative. Applies the exact shape and candidate rules shared with final
    target resolution so a stale or tampered request rejects with a matching
    stable reason before any round begins. ``scale`` applies the same step-1
    freeform gate and scaled resource check as ``preview_skill``, and the
    resolved plan then passes the same target-dependent cast, interaction and
    displacement gates final resolution applies to it. ``readings`` is the
    optional decision-local read set reused for this one submission.
    """
    failure = _skill_wide_failure(actor, skill_key, context, scale, readings)
    if failure is not None:
        return _disabled(skill_key, *failure)
    skill = (
        SKILL_REGISTRY[skill_key]
        if readings is None
        else readings.skill(skill_key)
    )
    try:
        if skill.target_spec is TargetSpec.NONE:
            if isinstance(targets, str) or targets:
                raise RejectedAction(RejectReason.TARGET_SPEC_MISMATCH, skill_key)
            resolved: list[Any] = []
        elif skill.target_spec is TargetSpec.SELF:
            if isinstance(targets, str) or targets:
                raise RejectedAction(RejectReason.TARGET_SPEC_MISMATCH, skill_key)
            # Final resolution normalizes an empty SELF submission to the actor
            # and then validates it through the same candidate pipeline, so a
            # submission may not accept a bound actor the resolver would reject
            # on presence, aliveness, range or faction.
            failure = candidate_rejection(
                actor, context, requirement_for(skill), actor, readings=readings
            )
            if failure is not None:
                raise RejectedAction(*failure)
            resolved = [actor]
        elif skill.target_spec is TargetSpec.SINGLE:
            if isinstance(targets, str):
                raise RejectedAction(RejectReason.TARGET_SPEC_MISMATCH, skill_key)
            if len(targets) != 1:
                raise RejectedAction(RejectReason.TARGET_SPEC_MISMATCH, skill_key)
            requirement = requirement_for(skill)
            # The requirement's own forbid-self rule is part of the SHAPE in
            # final resolution, so it is checked in the same position here.
            forbidden = forbidden_self_failure(actor, requirement, targets[0])
            if forbidden is not None:
                raise RejectedAction(*forbidden)
            failure = candidate_rejection(
                actor, context, requirement, targets[0], readings=readings
            )
            if failure is not None:
                raise RejectedAction(*failure)
            resolved = list(targets)
        else:  # AREA
            if isinstance(targets, str):
                expanded = expand_target_shorthand(actor, context, targets)
                resolved, _ = _valid_candidates(
                    actor, context, skill, list(expanded), readings
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
                    actor, context, skill, list(targets), readings
                )
                if not resolved:
                    raise RejectedAction(
                        RejectReason.NO_VALID_TARGETS_IN_AREA, skill_key
                    )
        plan_failure = spell_condition_failure(
            actor, skill, context, list(resolved), readings
        )
        if plan_failure is not None:
            raise RejectedAction(*plan_failure)
        plan_effect_audiences(actor, context, skill, list(resolved))
    except RejectedAction as rejection:
        return _disabled(skill_key, rejection.reason, rejection.detail)
    return ActionPreview(skill_key, True, None, None, tuple(resolved), ())


# Public read-only shapes accepted by preview and revalidation consumers.
SHAPES = tuple(TargetSpec)
