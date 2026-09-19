"""Steps 1-4b of the action pipeline: validation gates before staging.

All ownership, entitlement, cost-availability, targeting, capability, spell-
condition, and sexual-resist checks live here. The resource-cost arithmetic
(``_adjusted_costs``) is defined once in this module and shared by the step-2
check and the step-6 deduction so preflight and deduction can never drift.
"""

from typing import Any

from world.lore.races import RACE_REGISTRY
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
    requirement_for,
    resolve_targets,
)
from world.skills.cost_tiers import is_freeform_eligible
from world.skills.registry import SKILL_REGISTRY, SkillDef, SkillKind, TargetSpec
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY

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


def _step1_divine_arts_gate(actor: Any, skill: SkillDef) -> None:
    """Reject divine-mystery casts for races without divine affinity.

    The gate is data-driven: only skills declaring
    ``SkillDef.requires_divine_arts`` are checked, and the check reuses the
    already-landed ``RaceProfile.can_use_divine_arts`` field (no new race
    surface). An actor without a resolvable race is also rejected so the
    gate never silently opens.
    """
    if not skill.requires_divine_arts:
        return
    race = RACE_REGISTRY.get(getattr(actor, "race", None))
    if race is None or not race.can_use_divine_arts:
        raise RejectedAction(RejectReason.DIVINE_ARTS_FORBIDDEN, skill.key)


def _step1_freeform_gate(request: ActionRequest, skill: SkillDef) -> None:
    """Reject a scaled cast that fails the freeform-casting entitlement.

    Fires only when ``request.scale != 1.0`` (scale one is always permitted
    and never rejected here). The check order is fixed and crash-safe: scale
    membership in the closed table first, then ``is_freeform_eligible``
    (which itself requires an element and an ``mp`` cost), and only then
    the skill-anchored ``freeform_scales_for(actor, skill)`` ladder — so a
    non-elemental MP skill like ``concentration`` rejects cleanly instead of
    dereferencing a missing element, and the rung set is the one the panel
    advertises (use-driven-skill-lineage DC5).
    """
    if request.scale == 1.0:
        return
    if request.scale not in FREEFORM_SCALE_VALUES:
        raise RejectedAction(RejectReason.SCALED_CAST_FORBIDDEN, request.skill_key)
    if not is_freeform_eligible(skill):
        raise RejectedAction(RejectReason.SCALED_CAST_FORBIDDEN, request.skill_key)
    if request.scale not in freeform_scales_for(request.actor, skill):
        raise RejectedAction(RejectReason.SCALED_CAST_FORBIDDEN, request.skill_key)


def _step1_ownership(request: ActionRequest) -> SkillDef:
    skill = SKILL_REGISTRY.get(request.skill_key)
    if skill is None or skill.key not in request.actor.skills.owned_keys():
        raise RejectedAction(RejectReason.UNKNOWN_SKILL, request.skill_key)
    # The lineage gate (use-driven-skill-lineage DC2): an owned skill whose
    # prerequisite chain is unmet is rejected with the SAME reason, its detail
    # deterministically naming the first unmet edge. Detail stays the bare
    # skill key for the registry-miss/unowned case, so every pre-existing
    # matcher keeps working. can_use_skill is the boolean authority (the ONE
    # shared predicate); missing_prerequisite only reconstructs the named
    # edge for the message.
    if not can_use_skill(request.actor, skill):
        unmet = missing_prerequisite(request.actor, skill)
        required = SKILL_REGISTRY.get(unmet.skill_key)
        name = required.label if required is not None else unmet.skill_key
        raise RejectedAction(
            RejectReason.UNKNOWN_SKILL,
            f"{skill.key}:需先精通「{name}」至 Lv.{unmet.min_proficiency}",
        )
    if skill.kind is not SkillKind.ACTIVE:
        raise RejectedAction(RejectReason.SKILL_NOT_ACTIVE, request.skill_key)
    # Sanctioned combat-state gate 1 of 2 (usable_out_of_combat): the flagged
    # out-of-combat gate — see design.md D-3. Both sanctioned gates read the
    # context's battlefield, never a combat-state token.
    if not skill.usable_out_of_combat and request.context.battlefield is None:
        raise RejectedAction(
            RejectReason.SKILL_NOT_USABLE_OUT_OF_COMBAT,
            request.skill_key,
        )
    # Sanctioned combat-state gate site 2 of 2 (damaging-action gate): the
    # reason names the player-facing rule (a damaging skill must be aimed at a
    # co-located monster), while the shared condition in
    # action_gates.damage_requires_battlefield tests for the battlefield's
    # absence — the only way to obtain one is to open combat on a monster.
    # Fires before step 2, so nothing is deducted, rolled, staged, or timed.
    if damage_requires_battlefield(skill, request.context):
        raise RejectedAction(
            RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET,
            request.skill_key,
        )
    _step1_divine_arts_gate(request.actor, skill)
    _step1_freeform_gate(request, skill)
    return skill


def _adjusted_costs(
    actor: Any,
    skill: SkillDef,
    scale: float = 1.0,
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
    """
    bundle = evaluate_combat_modifiers_no_create(actor)
    costs = {
        resource_key: apply_cost_modifier(amount, bundle.get(f"{resource_key}_cost"))
        for resource_key, amount in skill.cost.items()
    }
    if costs.get("mp", 0) > 0:
        costs["mp"] = scaled_mp_cost(costs["mp"], scale)
    return costs


def _step2_resource_check(actor: Any, skill: SkillDef, scale: float = 1.0) -> None:
    for resource_key, amount in _adjusted_costs(actor, skill, scale).items():
        if _stored_trait_value(getattr(actor.traits, resource_key)) < amount:
            raise RejectedAction(
                RejectReason.INSUFFICIENT_RESOURCE,
                resource_key,
            )


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


def _step4_capability(actor: Any) -> None:
    if actor.attributes.has("buffs") and blocks_action(actor):
        raise RejectedAction(RejectReason.ACTION_FORBIDDEN, _entity_key(actor))
    mods = evaluate_combat_modifiers_no_create(actor)
    if mods.get("actions_per_turn", 1) == 0:
        raise RejectedAction(RejectReason.ACTION_FORBIDDEN, _entity_key(actor))


def _step4a_spell_conditions(
    request: ActionRequest,
    skill: SkillDef,
    targets: list[Any],
) -> None:
    from world.rules.spell_conditions import (
        evaluate_cast_conditions,
        evaluate_displaced_gate,
        evaluate_interaction_policy,
    )

    evaluate_cast_conditions(request.actor, targets, skill)
    evaluate_interaction_policy(request.actor, targets, request.context, skill)
    evaluate_displaced_gate(request.actor, targets, skill)


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
