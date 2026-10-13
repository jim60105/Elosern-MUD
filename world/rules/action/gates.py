"""Steps 1-4b of the action pipeline: validation gates before staging.

All ownership, entitlement, cost-availability, targeting, capability, spell-
condition, and sexual-resist checks live here. The resource-cost arithmetic
(``_adjusted_costs``) is defined once in this module and shared by the step-2
check and the step-6 deduction so preflight and deduction can never drift.

Every *deterministic* gate is also exposed as a pair-returning twin
(``ownership_failure``, ``resource_failure``, ``capability_failure``,
``spell_condition_failure``) so a side-effect-free
reader -- the frozen action preview and the monster-AI decision inputs -- gets
the identical ordered conditions and the identical ``(reason, detail)`` pair
the resolver raises, instead of a hand-mirrored copy that can drift. The
resolver's steps stay the authority: they raise from the same bodies. Only the
stochastic sexual-resist contest stays resolver-only.

Each pair-returning twin accepts an optional ``readings`` object -- the
decision-local, non-mutating stored reads a caller may reuse across several
plan validations (see ``world.rules.targeting.StoredReadings``). When it is
omitted, every read happens exactly where it happened before this twin
existed, so the resolver's own path is unchanged.
"""

from typing import Any

from world.skills.eligibility import skill_identity_eligible
from world.rules.action_gates import damage_requires_battlefield
from world.rules.buffs import blocks_action
from world.rules.combat_modifiers import (
    apply_cost_modifier,
    evaluate_combat_modifiers_no_create,
)
from world.rules.dice import roll_d100
from world.rules.progression import (
    can_use_skill,
    FREEFORM_SCALE_VALUES,
    freeform_scales_for,
    missing_prerequisite,
    scaled_mp_cost,
)
from world.rules.targeting import (
    expand_target_shorthand,
    forbidden_self_failure,
    requirement_for,
    resolve_targets,
)
from world.skills.cost_tiers import is_freeform_eligible
from world.skills.registry import SKILL_REGISTRY, SkillDef, SkillKind, TargetSpec
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY
from world.skills.restrictions import skill_effect_allowed

from world.rules.action.contracts import (
    ActionRequest,
    PendingEffect,
    RejectedAction,
    RejectReason,
    _entity_key,
)


def _stored_trait_value(trait: Any) -> float:
    """Read deterministic stored state without advancing a wall-clock gauge."""
    data = trait._data
    if trait.trait_type == "gauge":
        return data.get(
            "current",
            (data["base"] + data["mod"]) * data["mult"],
        )
    return data.get("value", (data.get("base", 0) + data.get("mod", 0)) * data.get("mult", 1))


def stored_gauge_pair(entity: Any, key: str) -> tuple[int, int]:
    """The entity's stored gauge as a clamped ``(current, maximum)`` int pair.

    A read-only rules/presentation helper: it resolves the gauge from stored
    trait state only (never a time-advancing accessor), clamps both terms to
    zero, and falls back to the computed stored value when a gauge carries no
    stored maximum. Shared by ``combat_view`` participant rows and the
    ``party`` presentation panel so companion HP can never drift between the
    two surfaces.
    """
    trait = getattr(entity.traits, key)
    maximum = getattr(trait, "max", None)
    if maximum is None:
        maximum = getattr(trait, "max_value", None)
    if maximum is None:
        maximum = _stored_trait_value(trait)
    return max(int(_stored_trait_value(trait)), 0), max(int(maximum), 0)


def _freeform_gate_failure(
    actor: Any,
    skill: SkillDef,
    scale: float,
    *,
    proficiency: Any = None,
    owned_keys: Any = None,
) -> tuple[RejectReason, str] | None:
    """Return the freeform-casting rejection ``(reason, detail)`` or ``None``.

    Fires only when ``scale != 1.0`` (scale one is always permitted and never
    rejected here). The check order is fixed and crash-safe: scale membership
    in the closed table first, then ``is_freeform_eligible`` (which itself
    requires an element and an ``mp`` cost), and only then the skill-anchored
    ``freeform_scales_for(actor, skill)`` ladder — so a non-elemental MP skill
    like ``concentration`` rejects cleanly instead of dereferencing a missing
    element, and the rung set is the one the panel advertises
    (use-driven-skill-lineage DC5).
    """
    if scale == 1.0:
        return None
    if scale not in FREEFORM_SCALE_VALUES:
        return RejectReason.SCALED_CAST_FORBIDDEN, skill.key
    if not is_freeform_eligible(skill):
        return RejectReason.SCALED_CAST_FORBIDDEN, skill.key
    if scale not in freeform_scales_for(
        actor, skill, proficiency=proficiency, owned_keys=owned_keys
    ):
        return RejectReason.SCALED_CAST_FORBIDDEN, skill.key
    return None


def _step1_freeform_gate(request: ActionRequest, skill: SkillDef) -> None:
    """Reject a scaled cast that fails the freeform-casting entitlement.

    The raising face of :func:`_freeform_gate_failure`, which the shared
    preview and the monster-AI decision inputs consume through
    :func:`ownership_failure`.
    """
    failure = _freeform_gate_failure(request.actor, skill, request.scale)
    if failure is not None:
        raise RejectedAction(*failure)


def ownership_failure(
    actor: Any,
    skill_key: str,
    context: Any,
    scale: float = 1.0,
    *,
    readings: Any = None,
) -> tuple[RejectReason, str] | None:
    """Return the first ordered ownership rejection, or ``None``.

    The ONE expression of resolver step 1: registry resolution and ownership,
    identity eligibility, the exam seal, the lineage prerequisite
    (``can_use_skill`` is the boolean authority; ``missing_prerequisite`` only
    reconstructs the named edge for the detail), active kind, the two
    sanctioned combat-state gates and the freeform-casting entitlement.
    ``readings`` may pre-supply registry resolution and the owned-key set.
    """
    skill = (
        SKILL_REGISTRY.get(skill_key)
        if readings is None
        else readings.skill(skill_key)
    )
    owned = (
        actor.skills.owned_keys()
        if readings is None
        else readings.owned_keys(actor)
    )
    if skill is None or skill.key not in owned:
        return RejectReason.UNKNOWN_SKILL, skill_key
    if not skill_identity_eligible(actor, skill):
        return RejectReason.IDENTITY_INELIGIBLE, skill.key
    if not skill_effect_allowed(actor, skill.key):
        return RejectReason.EXAM_SKILL_SEALED, skill.key
    if not can_use_skill(actor, skill, owned_keys=owned):
        unmet = missing_prerequisite(actor, skill, owned_keys=owned)
        required = SKILL_REGISTRY.get(unmet.skill_key)
        name = required.label if required is not None else unmet.skill_key
        return (
            RejectReason.UNKNOWN_SKILL,
            f"{skill.key}:需先精通「{name}」至 Lv.{unmet.min_proficiency}",
        )
    if skill.kind is not SkillKind.ACTIVE:
        return RejectReason.SKILL_NOT_ACTIVE, skill_key
    # Sanctioned combat-state gate 1 of 2 (usable_out_of_combat): the flagged
    # out-of-combat gate — see design.md D-3. Both sanctioned gates read the
    # context's battlefield, never a combat-state token.
    if not skill.usable_out_of_combat and context.battlefield is None:
        return RejectReason.SKILL_NOT_USABLE_OUT_OF_COMBAT, skill_key
    # Sanctioned combat-state gate site 2 of 2 (damaging-action gate): the
    # reason names the player-facing rule (a damaging skill must be aimed at a
    # co-located monster), while the shared condition in
    # action_gates.damage_requires_battlefield tests for the battlefield's
    # absence — the only way to obtain one is to open combat on a monster.
    # Fires before step 2, so nothing is deducted, rolled, staged, or timed.
    if damage_requires_battlefield(skill, context):
        return RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET, skill_key
    # The "proficiency" gate of the same order: the freeform rung ladder the
    # actor's current proficiency unlocks (use-driven-skill-lineage DC5).
    return _freeform_gate_failure(
        actor,
        skill,
        scale,
        proficiency=None if readings is None else readings.proficiency(actor),
        owned_keys=None if readings is None else owned,
    )


def _step1_ownership(request: ActionRequest) -> SkillDef:
    failure = ownership_failure(
        request.actor, request.skill_key, request.context, request.scale
    )
    if failure is not None:
        raise RejectedAction(*failure)
    return SKILL_REGISTRY[request.skill_key]


def _adjusted_costs(
    actor: Any,
    skill: SkillDef,
    scale: float = 1.0,
    modifiers: dict[str, Any] | None = None,
) -> dict[str, int]:
    """Return the skill's resource costs after bundle adjustments and scaling.

    One ``evaluate_combat_modifiers(actor)`` read maps every declared resource
    key through :func:`apply_cost_modifier` with the ``f"{resource_key}_cost"``
    bundle key, so the step-2 check, the step-6 recheck, and the staged
    ``resource_spend`` amount can never drift. A resource key with no matching
    bundle entry keeps its declared cost unchanged. Bundle adjustments apply
    to the unscaled base amounts first, then a positive ``mp`` amount is
    replaced with ``scaled_mp_cost(base, scale)`` (never below 1); a
    bundle-adjusted ``mp`` amount of zero — a deliberate free-cast modifier
    such as ``-100%`` — stays zero and is never scaled. Other resource keys
    keep their unscaled amounts. Both step 2 and step 6 pass the request's
    scale, so preflight and deduction always compare and deduct the same
    scaled amount.

    ``modifiers`` is the already-read bundle; a decision-local reader passes
    the value it read once for this decision instead of rebuilding it per plan.
    """
    bundle = (
        evaluate_combat_modifiers_no_create(actor)
        if modifiers is None
        else modifiers
    )
    costs = {
        resource_key: apply_cost_modifier(amount, bundle.get(f"{resource_key}_cost"))
        for resource_key, amount in skill.cost.items()
    }
    if costs.get("mp", 0) > 0:
        costs["mp"] = scaled_mp_cost(costs["mp"], scale)
    return costs


def resource_failure(
    actor: Any,
    skill: SkillDef,
    scale: float = 1.0,
    *,
    modifiers: dict[str, Any] | None = None,
    readings: Any = None,
) -> tuple[RejectReason, str] | None:
    """Return the first insufficient resource key, or ``None``.

    The ONE expression of resolver step 2: the adjusted costs of
    :func:`_adjusted_costs` compared against the actor's stored trait values.
    ``readings`` may pre-supply both the adjusted costs and the stored values.
    """
    if readings is None:
        costs = _adjusted_costs(actor, skill, scale, modifiers)
    else:
        costs = readings.costs(actor, skill, scale)
    for resource_key, amount in costs.items():
        if readings is None:
            current = _stored_trait_value(getattr(actor.traits, resource_key))
        else:
            current = readings.trait_value(actor, resource_key)
        if current < amount:
            return RejectReason.INSUFFICIENT_RESOURCE, resource_key
    return None


def _step2_resource_check(actor: Any, skill: SkillDef, scale: float = 1.0) -> None:
    failure = resource_failure(actor, skill, scale)
    if failure is not None:
        raise RejectedAction(*failure)


def _step3_targeting(
    request: ActionRequest,
    skill: SkillDef,
) -> list[Any]:
    if isinstance(request.targets, str):
        # Shorthand is approved only for AREA-target skills; SINGLE shorthands
        # are rejected even when expansion would yield exactly one entity.
        if skill.target_spec is not TargetSpec.AREA:
            raise RejectedAction(
                RejectReason.TARGET_SPEC_MISMATCH,
                "target shorthand requires an area skill",
            )
        candidates = expand_target_shorthand(
            request.actor,
            request.context,
            request.targets,
        )
    else:
        candidates = list(request.targets)
    if skill.target_spec is TargetSpec.SELF and not candidates:
        candidates = [request.actor]
    return resolve_targets(
        request.actor, request.context, requirement_for(skill), candidates
    )


def capability_failure(
    actor: Any,
    blocked_by_buff: bool,
    *,
    modifiers: dict[str, Any] | None = None,
) -> tuple[RejectReason, str] | None:
    """Return the action-capability rejection, or ``None``.

    The ONE expression of resolver step 4: a blocking buff forbids the action,
    and so does an ``actions_per_turn`` of zero. ``blocked_by_buff`` is the
    caller's own read of the blocking-buff fact — the resolver keeps its
    handler-backed read (``actor.attributes.has("buffs") and
    blocks_action(actor)``, whose stored-attribute guard short-circuits before
    any handler access), while the no-create readers project it from the
    persisted buff cache.
    """
    if blocked_by_buff:
        return RejectReason.ACTION_FORBIDDEN, _entity_key(actor)
    bundle = (
        evaluate_combat_modifiers_no_create(actor)
        if modifiers is None
        else modifiers
    )
    if bundle.get("actions_per_turn", 1) == 0:
        return RejectReason.ACTION_FORBIDDEN, _entity_key(actor)
    return None


def _step4_capability(actor: Any) -> None:
    failure = capability_failure(
        actor, actor.attributes.has("buffs") and blocks_action(actor)
    )
    if failure is not None:
        raise RejectedAction(*failure)


def _spell_condition_gates(
    actor: Any,
    skill: SkillDef,
    context: Any,
    targets: list[Any],
    readings: Any = None,
) -> None:
    """Run the ordered target-dependent gates of resolver step 4a.

    ``readings`` is the optional decision-local read set: the interaction and
    displacement gates reuse its stored facts instead of re-reading a
    participant per plan.
    """
    from world.rules.spell_conditions import (
        evaluate_cast_conditions,
        evaluate_displaced_gate,
        evaluate_interaction_policy,
    )

    evaluate_cast_conditions(actor, targets, skill, readings=readings)
    evaluate_interaction_policy(
        actor, targets, context, skill, readings=readings
    )
    evaluate_displaced_gate(actor, targets, skill, readings=readings)


def _step4a_spell_conditions(
    request: ActionRequest,
    skill: SkillDef,
    targets: list[Any],
) -> None:
    _spell_condition_gates(request.actor, skill, request.context, targets)


def spell_condition_failure(
    actor: Any,
    skill: SkillDef,
    context: Any,
    targets: list[Any],
    readings: Any = None,
) -> tuple[RejectReason, str] | None:
    """Return the first cast, interaction or displacement rejection, or ``None``.

    The pair-returning face of resolver step 4a, shared by the preview, the
    submission revalidation and the monster-AI plan validation so a skill
    which passes the older preview subset but fails a real cast or
    interaction prerequisite is excluded before scoring with the identical
    deterministic rejection settlement raises.
    """
    try:
        _spell_condition_gates(actor, skill, context, targets, readings)
    except RejectedAction as rejection:  # observability: ignore R2: the rejection is returned to the caller as a (reason, detail) pair; it is reported, not swallowed
        return rejection.reason, rejection.detail
    return None


def _resist_pending_effect(target: Any, verdict: Any) -> PendingEffect:
    """Stage one logged resist verdict as a non-mutating pending effect.

    ``resist_verdict()`` has already executed when this helper runs — the
    dice roll and every state read happened during the gate, before the
    transactional commit — and the verdict mutates no entity state, so
    ``apply`` is a no-op. The ``PendingEffect`` exists solely so the verdict
    becomes a logged, replayable ``EventEntry`` through the ordinary
    ``_entries_from_effect`` path. The description uses the
    ``"none"``-sentinel convention for an absent roll (auto-complied verdicts
    never roll), mirroring ``disengage_attempt``'s optional-field handling.
    """
    roll_field = "none" if verdict.roll is None else str(verdict.roll)
    return PendingEffect(
        target,
        f"sexual_resist|{_entity_key(target)}|{int(verdict.resisted)}|"
        f"{int(verdict.auto_comply)}|{roll_field}",
        frozenset(),
        lambda: None,
    )


def _step4b_sexual_resist_gate(
    request: ActionRequest,
    skill: SkillDef,
    targets: list[Any],
) -> tuple[list[Any], list[PendingEffect], bool]:
    """Resolve one resist contest per non-actor target of a resistible act.

    Fires only when the cast skill's key is present in
    ``SEXUAL_ACT_REGISTRY`` and the act declares ``resistible=True``; any
    other skill returns ``(targets, [])`` unchanged with no behavioral or
    performance cost beyond one dict lookup. ``resist_verdict()`` is imported
    lazily inside the guard: a module-level import would create an import
    cycle (``action -> sexual_resist -> combat -> action``), and the gate's
    per-call lookup is the same fresh-name pattern the module-level
    ``roll_d100`` binding provides for testability (design D-6).
    """
    act = SEXUAL_ACT_REGISTRY.get(skill.key)
    is_catalog_act = act is not None and act.resistible
    is_generic_resistible = not is_catalog_act and (
        skill.interaction is not None and skill.interaction.resistible
    )
    if not is_catalog_act and not is_generic_resistible:
        return targets, [], False
    from world.rules.sexual_resist import resist_verdict

    surviving: list[Any] = []
    pending: list[PendingEffect] = []
    generic_resisted = False
    for target in targets:
        if target is request.actor:
            # The actor never resists their own act (design D-2); without
            # this guard a future resistible SELF-target act would roll a
            # contest against its own caster and could silently withhold
            # their own D-4 pleasure share.
            surviving.append(target)
            continue
        verdict = resist_verdict(request.actor, target, rng=roll_d100)
        pending.append(_resist_pending_effect(target, verdict))
        if verdict.resisted:
            if is_generic_resistible:
                generic_resisted = True
        else:
            surviving.append(target)
    if generic_resisted:
        return [], pending, True
    return surviving, pending, False
