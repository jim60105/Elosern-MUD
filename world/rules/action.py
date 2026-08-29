"""Atomic, deterministic skill-action resolution."""

from copy import deepcopy
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any, Callable, Literal

from django.db import transaction

from typeclasses.monsters import Monster
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.lore.races import RACE_REGISTRY
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    _add_buff,
    _handle_cleanse,
    _is_damaging_rate,
    blocks_action,
    entity_active_buffs,
    grant_conferred_growth_rate,
)
from world.rules.combat_modifiers import apply_cost_modifier, evaluate_combat_modifiers
from world.rules.dice import roll_d100
from world.rules.equipment_effects import equipment_immune_buff_keys
from world.rules.event_log import EventEntry, EventLog
from world.rules.progression import (
    FREEFORM_SCALE_VALUES,
    can_cast_skill,
    freeform_scales_for,
    grant_combat_kill_xp,
    grant_skill_practice_xp,
    scaled_mp_cost,
)
from world.rules.sexual_act_effects import (
    _COUNTER_MUTATORS,
    _EFFECTS_CONFIG,
    _OBSERVER_GATED_COUNTERS,
    _OBSERVER_GATED_EVENTS,
    compute_pleasure_gain,
    observers_present,
    pair_event_name,
    participants,
    resolve_part,
)
from world.rules.sexual_state import _apply_climax_phase_set
from world.rules.skill_effects import (
    apply_disguise_effect,
    record_conferred_grant,
    validate_conferrable_skill,
)
from world.rules.targeting import (
    ActionContext,
    expand_target_shorthand,
    resolve_targets,
)
from world.skills.cost_tiers import is_freeform_eligible
from world.skills.effects import parse_effect
from world.skills.registry import SKILL_REGISTRY, SkillDef, SkillKind, TargetSpec
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY
from world.skills.sexual_acts._builder import _LEGACY_TARGET_SCOPED_EVENTS


class RejectReason(StrEnum):
    """Stable rejection identifiers for every action-pipeline failure."""

    UNKNOWN_SKILL = "unknown_skill"
    SKILL_NOT_ACTIVE = "skill_not_active"
    SKILL_NOT_USABLE_OUT_OF_COMBAT = "skill_not_usable_out_of_combat"
    INSUFFICIENT_RESOURCE = "insufficient_resource"
    TARGET_SPEC_MISMATCH = "target_spec_mismatch"
    TARGET_NOT_PRESENT = "target_not_present"
    TARGET_DEAD = "target_dead"
    TARGET_OUT_OF_RANGE = "target_out_of_range"
    TARGET_FACTION_FORBIDDEN = "target_faction_forbidden"
    NO_VALID_TARGETS_IN_AREA = "no_valid_targets_in_area"
    ACTION_FORBIDDEN = "action_forbidden"
    DIVINE_ARTS_FORBIDDEN = "divine_arts_forbidden"
    SCALED_CAST_FORBIDDEN = "scaled_cast_forbidden"
    UNKNOWN_EFFECT_ID = "unknown_effect_id"
    EFFECT_RESOLUTION_FAILED = "effect_resolution_failed"
    MISSING_EFFECT_CONTEXT = "missing_effect_context"
    RESOURCE_DEDUCTION_FAILED = "resource_deduction_failed"
    EVENT_LOG_CONSTRUCTION_FAILED = "event_log_construction_failed"
    TIME_COST_LOOKUP_FAILED = "time_cost_lookup_failed"
    UNSNAPSHOTTED_EFFECT_SURFACE = "unsnapshotted_effect_surface"
    COMMIT_FAILED = "commit_failed"


class RejectedAction(Exception):
    """A pre-commit action rejection."""

    def __init__(self, reason: RejectReason, detail: str = ""):
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


class CommitFailed(Exception):
    """A commit rejection after state has been restored."""

    def __init__(self, reason: RejectReason, detail: str = ""):
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class ActionRequest:
    """One caller-neutral request to invoke a skill.

    ``scale`` is the optional freeform magnitude modifier (element-mastery-
    freeform-casting): ``1.0`` is the behavior-preserving default and is
    always allowed; any other value must pass the step-1 freeform gate.
    """

    actor: Any
    skill_key: str
    targets: list[Any] | Literal["all-enemies", "all-allies", "all"]
    context: ActionContext
    scale: float = 1.0


@dataclass(frozen=True)
class ActionResult:
    """Success or rejection returned without leaking pipeline exceptions."""

    outcome: Literal["success", "rejected"]
    event_log: EventLog | None
    time_cost_seconds: int | None
    reason: RejectReason | None
    detail: str | None

    @classmethod
    def success(cls, event_log: EventLog, time_cost: int) -> "ActionResult":
        return cls("success", event_log, time_cost, None, None)

    @classmethod
    def rejected(
        cls,
        reason: RejectReason,
        detail: str = "",
    ) -> "ActionResult":
        return cls("rejected", None, None, reason, detail)


@dataclass(frozen=True)
class PendingEffect:
    """A state mutation staged for the single commit point."""

    entity: Any
    description: str
    surfaces: frozenset[str]
    apply: Callable[[], None]


class UnsnapshottedSurfaceError(Exception):
    """A handler declared state that the commit mechanism cannot restore."""


EffectHandler = Callable[
    [Any, list[Any], str, dict[str, Any], float],
    list[PendingEffect],
]
SNAPSHOTTED_SURFACES = frozenset(
    {
        "traits",
        "sexual",
        "buffs",
        "skill_grants",
        "progression",
        "battlefield",
        "quest_log",
        "instance_pin",
    }
)
_EFFECT_HANDLERS: dict[str, EffectHandler] = {}
_EFFECT_HANDLER_SURFACES: dict[str, frozenset[str]] = {}
_EFFECT_HANDLER_REQUIRED_CONTEXT: dict[str, frozenset[str]] = {}
_EVENT_EFFECT_PLANNERS: dict[str, Callable[[ActionRequest, "EventLog"], list[PendingEffect]]] = {}
DEFAULT_CAST_SECONDS = 6
SKILL_TIME_OVERRIDES: dict[str, int] = {}


def register_event_effect_planner(
    name: str,
    planner: Callable[[ActionRequest, "EventLog"], list[PendingEffect]],
) -> None:
    """Register or replace one event-effect planner by name (idempotent).

    Planners derive additional ``PendingEffect`` values from a completed
    ``EventLog``; they never write while planning. Re-registering the same name
    replaces the earlier planner rather than duplicating progress on every
    server start.
    """
    _EVENT_EFFECT_PLANNERS[name] = planner


def register_effect_handler(
    prefix: str,
    handler: EffectHandler,
    surfaces: frozenset[str],
    requires_event_context: frozenset[str],
) -> None:
    """Register an effect prefix only when all mutations are restorable.

    ``requires_event_context`` SHALL name every ``event_context`` key the
    handler needs to resolve; an explicit (possibly empty) frozenset is
    required so no handler can silently skip the contract. Preflight and
    preview reject an action whose session context cannot supply every
    declared key, before any round cost.
    """
    unsupported = surfaces - SNAPSHOTTED_SURFACES
    if unsupported:
        raise UnsnapshottedSurfaceError(
            f"{prefix!r} declares unsupported surfaces {sorted(unsupported)}"
        )
    _EFFECT_HANDLERS[prefix] = handler
    _EFFECT_HANDLER_SURFACES[prefix] = surfaces
    _EFFECT_HANDLER_REQUIRED_CONTEXT[prefix] = frozenset(requires_event_context)


def _entity_key(entity: Any) -> str:
    return str(entity.key)


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


def _event_context(request: ActionRequest) -> dict[str, Any]:
    return getattr(request.context, "event_context", {})


def _step1_freeform_gate(request: ActionRequest, skill: SkillDef) -> None:
    """Reject a scaled cast that fails the freeform-casting entitlement.

    Fires only when ``request.scale != 1.0`` (scale one is always permitted
    and never rejected here). The check order is fixed and crash-safe: scale
    membership in the closed table first, then ``is_freeform_eligible``
    (which itself requires an element and an ``mp`` cost), and only then
    ``freeform_scales_for(actor, skill.element.key)`` — so a non-elemental MP
    skill like ``concentration`` rejects cleanly instead of dereferencing a
    missing element.
    """
    if request.scale == 1.0:
        return
    if request.scale not in FREEFORM_SCALE_VALUES:
        raise RejectedAction(RejectReason.SCALED_CAST_FORBIDDEN, request.skill_key)
    if not is_freeform_eligible(skill):
        raise RejectedAction(RejectReason.SCALED_CAST_FORBIDDEN, request.skill_key)
    if not freeform_scales_for(request.actor, skill.element.key):
        raise RejectedAction(RejectReason.SCALED_CAST_FORBIDDEN, request.skill_key)


def _step1_ownership(request: ActionRequest) -> SkillDef:
    skill = SKILL_REGISTRY.get(request.skill_key)
    if skill is None or skill.key not in request.actor.skills.owned_keys():
        raise RejectedAction(RejectReason.UNKNOWN_SKILL, request.skill_key)
    if skill.kind is not SkillKind.ACTIVE:
        raise RejectedAction(RejectReason.SKILL_NOT_ACTIVE, request.skill_key)
    # The ONE sanctioned combat-context read in this entire module — see design.md D-3.
    if not skill.usable_out_of_combat and request.context.battlefield is None:
        raise RejectedAction(
            RejectReason.SKILL_NOT_USABLE_OUT_OF_COMBAT,
            request.skill_key,
        )
    # Elemental spells are additionally gated by the caster's magic tier
    # through the shared cast-eligibility predicate
    # (``progression.can_cast_skill``), unless the caster directly owns the
    # element's mastery skill. An unmet gate — or a malformed elemental spell
    # that the predicate fails closed on — rejects like an unowned-skill cast
    # (no new RejectReason member).
    if not can_cast_skill(request.actor, skill):
        raise RejectedAction(RejectReason.UNKNOWN_SKILL, request.skill_key)
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
    bundle = evaluate_combat_modifiers(actor)
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
    return resolve_targets(request, skill, candidates)


def _step4_capability(actor: Any) -> None:
    if actor.attributes.has("buffs") and blocks_action(actor):
        raise RejectedAction(RejectReason.ACTION_FORBIDDEN, _entity_key(actor))


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
) -> tuple[list[Any], list[PendingEffect]]:
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
    if act is None or not act.resistible:
        return targets, []
    from world.rules.sexual_resist import resist_verdict

    surviving: list[Any] = []
    pending: list[PendingEffect] = []
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
        if not verdict.resisted:
            surviving.append(target)
    return surviving, pending


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


def _handle_confer_skill_partial(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    del scale
    values = _require_context(context, "confer_skill_partial")
    skill_key = values["confer_skill_key"]
    scale = values["confer_scale"]
    validate_conferrable_skill(skill_key)
    target = targets[0]
    source_key = _entity_key(actor)
    return [
        PendingEffect(
            target,
            f"skill_granted|{_entity_key(target)}|{skill_key}|{scale}",
            frozenset(),
            lambda: record_conferred_grant(
                target,
                source_key,
                skill_key,
                float(scale),
            ),
        )
    ]


def _handle_set_disguise(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    del scale
    values = _require_context(context, "set_disguise")
    overrides = values["disguise"]
    if not isinstance(overrides, dict):
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            "set_disguise requires event_context.disguise",
        )
    target = targets[0]
    return [
        PendingEffect(
            target,
            f"disguise_set|{_entity_key(target)}",
            frozenset(),
            lambda: apply_disguise_effect(target, overrides),
        )
    ]


def _handle_buff_apply(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    del scale
    try:
        key = effect_id.split(":", 1)[1]
    except IndexError as error:
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            effect_id,
        ) from error
    kwargs = dict(context.get("buff_kwargs", {}))
    definition = BUFF_DEFINITIONS.get(key)
    rate = definition.modifiers.get("rate") if definition is not None else None
    if _is_damaging_rate(rate):
        # Attribution is authoritative-actor-derived and cannot be spoofed: a
        # caller-supplied ``source_pk`` is popped and replaced by the actor's
        # dbref, and an actor without a resolvable positive-int dbref rejects
        # the action before commit (fix-dot-kill-credit D1).
        kwargs.pop("source_pk", None)
        pk = getattr(actor, "pk", None)
        if isinstance(pk, bool) or not isinstance(pk, int) or pk <= 0:
            raise RejectedAction(
                RejectReason.EFFECT_RESOLUTION_FAILED,
                f"buff {key!r} requires a caster with a positive-int dbref",
            )
        kwargs["source_pk"] = int(pk)
    pending: list[PendingEffect] = []
    for target in targets:
        if (
            definition is not None
            and definition.polarity == "debuff"
            and key in equipment_immune_buff_keys(target)
        ):
            # Worn-equipment immunity is decided at STAGING time so the event
            # tag is fixed here, in the ordinary replayable-entry path: a
            # neutralized roll is never silently lied about (P3 design D1).
            # Like ``_resist_pending_effect``, the staged effect is
            # non-mutating; ``_add_buff`` still carries an independent
            # no-write backstop for every direct caller.
            pending.append(
                PendingEffect(
                    target,
                    f"equipment_immune|{_entity_key(target)}|{key}",
                    frozenset(),
                    lambda: None,
                )
            )
            continue
        pending.append(
            PendingEffect(
                target,
                f"buff_applied|{_entity_key(target)}|{key}",
                frozenset(),
                lambda target=target: _add_buff(target, key, **kwargs),
            )
        )
    return pending


def _handle_self_buff_apply(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Apply one definition-keyed buff to the caster without a target.

    ``TargetSpec.NONE`` skills resolve to an empty target list, so this handler
    binds the actor directly instead of iterating targets. This keeps a NONE
    skill meaningful (a concentration-style self effect) while still never
    accepting a caller-supplied target. A debuff grant the actor's worn
    equipment immunises stages the same non-mutating neutralization event as
    the target-scoped handler.
    """
    del targets, context, scale
    try:
        key = effect_id.split(":", 1)[1]
    except IndexError as error:
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            effect_id,
        ) from error
    definition = BUFF_DEFINITIONS.get(key)
    if (
        definition is not None
        and definition.polarity == "debuff"
        and key in equipment_immune_buff_keys(actor)
    ):
        return [
            PendingEffect(
                actor,
                f"equipment_immune|{_entity_key(actor)}|{key}",
                frozenset(),
                lambda: None,
            )
        ]
    return [
        PendingEffect(
            actor,
            f"self_buff_applied|{_entity_key(actor)}|{key}",
            frozenset({"buffs"}),
            lambda: _add_buff(actor, key),
        )
    ]


def _handle_confer_growth_rate(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    del scale
    values = _require_context(context, "confer_growth_rate")
    scale = values["confer_scale"]
    target = targets[0]
    source_key = _entity_key(actor)
    return [
        PendingEffect(
            target,
            f"buff_applied|{_entity_key(target)}|conferred_growth_rate",
            frozenset(),
            lambda: grant_conferred_growth_rate(
                target,
                source_key,
                float(scale),
            ),
        )
    ]


def _handle_divine_mystery(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Resolve one divine-mystery effect; unmechanized entries stay inert.

    ``DivineMysteryEffect(mechanized=False)`` is a deliberately declared
    flavor category: the cast is accepted but stages no state change. A
    mechanized entry has no cast path yet and must reject rather than
    silently doing nothing.
    """
    del actor, targets, context, scale
    if parse_effect(effect_id).mechanized:
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            "mechanized divine mysteries have no cast path yet",
        )
    return []


def _handle_sexual_event(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Apply one act's declared event to its participants.

    The event fires for **every participant** of the cast —
    ``participants(actor, targets)`` — mirroring the pleasure and counter
    handlers, except that an event name in ``_LEGACY_TARGET_SCOPED_EVENTS``
    (exactly the legacy ``divine_sexual_arts`` skill's ``stimulus_applied``)
    keeps the historic target-scoped iteration so the divine-arts exemption
    from self-pleasure (D-9) holds. Resisted targets were already excluded
    from ``targets`` by ``_step4b_sexual_resist_gate``, so a partially
    resisted cast reaches only its surviving participants.
    """
    del scale
    event_name = effect_id.partition(":")[2]
    if not event_name:
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            "sexual_event requires an event name",
        )
    try:
        from world.rules.sexual_transitions import apply_event
    except ImportError as error:
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            "sexual-transition rules are unavailable (change 7b)",
        ) from error
    sexual_context = dict(context.get("sexual", {}))
    recipients = (
        targets
        if event_name in _LEGACY_TARGET_SCOPED_EVENTS
        else participants(actor, targets)
    )
    return [
        PendingEffect(
            target,
            f"sexual_transition|{_entity_key(target)}|{event_name}",
            frozenset(),
            lambda target=target: apply_event(
                target,
                event_name,
                **sexual_context,
            ),
        )
        for target in recipients
    ]


def _handle_actor_sexual_event(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Apply one performer-scoped event to the acting entity alone.

    The actor-scoped twin of ``_handle_sexual_event``: an act declaring a
    ``_ACTOR_SCOPED_EVENTS`` member (``self_exposure``, ``public_exposure``,
    ``watched_during_activity``, ``public_sexual_activity``) emits it through
    the ``sexual_event_actor:<name>`` prefix so the resolved event lands on
    the performing actor and never on a target — a spectator's observation
    does not expose the spectator. The apply path, error shape, and description
    kind mirror the participant handler; an event name in
    ``_OBSERVER_GATED_EVENTS`` (``watched_during_activity``) is staged only
    when :func:`observers_present` reads a co-located observer, and an
    observer-less cast stays silent.
    """
    del scale
    event_name = effect_id.partition(":")[2]
    if not event_name:
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            "sexual_event_actor requires an event name",
        )
    if (
        event_name in _OBSERVER_GATED_EVENTS
        and not observers_present(actor, targets, context)
    ):
        return []
    try:
        from world.rules.sexual_transitions import apply_event
    except ImportError as error:
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            "sexual-transition rules are unavailable (change 7b)",
        ) from error
    sexual_context = dict(context.get("sexual", {}))
    return [
        PendingEffect(
            actor,
            f"sexual_transition|{_entity_key(actor)}|{event_name}",
            frozenset(),
            lambda: apply_event(
                actor,
                event_name,
                **sexual_context,
            ),
        )
    ]


def _handle_act_pair_event(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Resolve one sex-conditional event and apply it to every participant.

    Resolves the acting act through ``_resolve_act`` (rejecting an absent
    key defensively), selects the emitted event from the cast's participant
    pair through :func:`pair_event_name`, and stages one ``PendingEffect``
    per participant when an event matched — the D-12 symmetric ``virgin``
    break for an opposite-sex cast. A ``None`` resolution (an ``other``/
    unknown participant, or a single-participant surviving cast) stages no
    effect. Like ``_handle_sexual_event``, the ``apply_event`` import stays
    deferred to match the module's existing cycle-avoidance discipline.
    """
    del scale
    sexual_context = dict(context.get("sexual", {}))
    act = _resolve_act(effect_id)
    event_name = pair_event_name(actor, targets, act)
    if event_name is None:
        return []
    try:
        from world.rules.sexual_transitions import apply_event
    except ImportError as error:
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            "sexual-transition rules are unavailable (change 7b)",
        ) from error
    return [
        PendingEffect(
            participant,
            f"sexual_transition|{_entity_key(participant)}|{event_name}",
            frozenset(),
            lambda participant=participant: apply_event(
                participant,
                event_name,
                **sexual_context,
            ),
        )
        for participant in participants(actor, targets)
    ]


def _resolve_act(effect_id: str) -> Any:
    """Return the registered ``SexualActDef`` an effect string names.

    Defensive lookup only: ``_act_family()`` is the sole producer of
    ``pleasure:``/``sexual_counter:`` strings and always pairs the effect with
    a registered act, but a hand-written ``SkillDef`` could name an absent
    key, which must reject the action rather than silently doing nothing.
    """
    act_key = effect_id.partition(":")[2]
    act = SEXUAL_ACT_REGISTRY.get(act_key)
    if act is None:
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            f"{effect_id} names an act absent from SEXUAL_ACT_REGISTRY",
        )
    return act


def _handle_pleasure_effect(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Stage one pleasure gain per participant of a sexual act's cast.

    The acting entity uses ``actor_part``/``actor_pleasure_ratio`` and every
    other participant uses ``target_part``/``1.0`` (design D-5); the
    participant count is computed once per cast and reused for every
    participant's gain. Each staged ``PendingEffect`` applies that
    participant's own computed gain through :func:`_apply_pleasure_gain`.
    """
    del context, scale
    act = _resolve_act(effect_id)
    everyone = participants(actor, targets)
    count = len(everyone)
    pending: list[PendingEffect] = []
    for participant in everyone:
        is_actor = participant is actor
        part = resolve_part(
            participant,
            act.actor_part if is_actor else act.target_part,
        )
        ratio = act.actor_pleasure_ratio if is_actor else 1.0
        gain = compute_pleasure_gain(participant, part, act.base_pleasure, ratio, count)
        pending.append(
            PendingEffect(
                participant,
                f"pleasure_gain|{_entity_key(participant)}|{gain}",
                frozenset(),
                lambda participant=participant, gain=gain: _apply_pleasure_gain(
                    participant, gain
                ),
            )
        )
    return pending


def _apply_pleasure_gain(entity: Any, gain: int) -> None:
    """Apply one participant's pleasure gain and the arousal-coupled cascade.

    Replicates two ``sexual.yaml`` rules directly — ``wetness_follows_arousal``
    and the ``climax_gate``/``climax_phase_critical_point_to_in_progress``
    pair — because both are conditioned on a change ``apply_event()``'s own
    snapshot must observe within its own call, which a pleasure gain applied
    outside ``apply_event()`` cannot produce. The captures below must stay the
    first statements: the wetness bump compares the arousal ordinal before and
    after the mutation, the two-step 未達→接近→進行中 semantic depends on
    reading the pre-mutation climax phase before either transition runs, and
    the extension trigger fires only for a participant already in 進行中 when
    the effect applies — a participant this very call pushes from 接近 into
    進行中 has just started climaxing, it has not received a qualifying
    extension stimulus (pleasure-model design §3.2/§3.4).

    The extension trigger compares against ``gain``, the uncapped computed
    value, not the clamped applied delta: ``pleasure`` self-clamps at 100, so
    an entity already in 進行中 would almost never stage an extension if the
    post-clamp delta were the gate. ``_apply_climax_phase_set`` no-ops on any
    edge outside ``_VALID_CLIMAX_TRANSITIONS``, so both transition calls are
    unconditionally safe to attempt.
    """
    pre_arousal_ordinal = entity.sexual.arousal.value
    was_at_critical_point = entity.sexual.climax_phase.level == "接近"
    was_in_progress = entity.sexual.climax_phase.level == "進行中"

    entity.sexual.pleasure.base += gain

    if entity.sexual.arousal.value > pre_arousal_ordinal:
        entity.sexual.wetness.value += 1
    if entity.sexual.arousal.level == "極限":
        _apply_climax_phase_set(entity, "接近")
    if was_at_critical_point:
        _apply_climax_phase_set(entity, "進行中")

    if was_in_progress and gain >= _EFFECTS_CONFIG.climax_extension_threshold:
        entity.sexual.stage_climax_extension()


def _counter_pending_effect(entity: Any, counter_name: str) -> PendingEffect:
    """Stage one sanctioned counter increment on one participant.

    The mutator name is looked up through the explicit
    ``_COUNTER_MUTATORS`` table — never a derived string transform — and an
    unrecognized counter name rejects the action at resolution time.
    """
    mutator = _COUNTER_MUTATORS.get(counter_name)
    if mutator is None:
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            f"unknown lifetime counter {counter_name!r}",
        )
    return PendingEffect(
        entity,
        f"sexual_counter|{_entity_key(entity)}|{counter_name}",
        frozenset(),
        lambda entity=entity, mutator=mutator: getattr(entity.sexual, mutator)(),
    )


def _handle_sexual_counter_effect(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Stage one counter increment per declared name, per applicable role.

    ``actor_counters`` land on the acting entity; ``participant_counters``
    land on every other participant. A counter name present in both tuples is
    applied once per side through two independent grants — the schema's way of
    crediting both parties of a symmetric two-person act.

    A counter name in ``_OBSERVER_GATED_COUNTERS`` (``watched_count``) is
    staged only when :func:`observers_present` reads a co-located observer
    for the cast; an unobserved cast silently skips that single name while
    every other declared counter still stages — the "被觀看次數" ladder cannot
    climb without an audience.
    """
    act = _resolve_act(effect_id)
    observed = observers_present(actor, targets, context)
    all_participants = participants(actor, targets)
    others = [participant for participant in all_participants if participant is not actor]
    pending: list[PendingEffect] = []
    for name in act.actor_counters:
        if name in _OBSERVER_GATED_COUNTERS and not observed:
            continue
        pending.append(_counter_pending_effect(actor, name))
    for other in others:
        for name in act.participant_counters:
            pending.append(_counter_pending_effect(other, name))
    return pending


def _handle_divine_pleasure_max(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Set every non-actor target's pleasure to its ceiling in one cast.

    Stages one ``PendingEffect`` per remaining target whose ``apply()`` calls
    the shipped :func:`_apply_pleasure_gain` twice in sequence — ``gain=100``
    (sets ``pleasure`` to its clamped ceiling and walks at most one climax
    cycle edge) then ``gain=0`` (re-runs the pre/post-mutation check, which
    now observes the already-updated phase and walks the second edge into
    進行中). Two calls, not one, because ``_apply_pleasure_gain`` deliberately
    advances ``climax_phase`` by at most one cycle edge per call
    (divine-sexual-arts-reuse design D-2).

    The actor is excluded explicitly even when present in the resolved
    ``targets`` list: the ``"all"`` AREA shorthand has no self-exclusion, and
    ``_step4b_sexual_resist_gate`` keeps an actor present in ``targets``
    without rolling a contest for it. An empty or shrunken ``targets`` list
    (a fully or partially resisted cast) is an ordinary outcome.
    """
    del context, scale, effect_id
    pending: list[PendingEffect] = []
    for target in targets:
        if target is actor:
            continue
        pending.append(
            PendingEffect(
                target,
                f"divine_pleasure_max|{_entity_key(target)}|100",
                frozenset(),
                lambda target=target: (
                    _apply_pleasure_gain(target, 100),
                    _apply_pleasure_gain(target, 0),
                ),
            )
        )
    return pending


def _handle_climax_extension_stage(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Stage ``count`` climax extensions on every non-actor target.

    The ``count`` is parsed from the effect string
    (``divine_climax_extension_stage:<count>``) and applied through the
    already-shipped ``SexualState.stage_climax_extension`` — which validates
    the count and accumulates rather than overwrites. The actor is excluded
    explicitly, and an empty or shrunken ``targets`` list (a resisted cast)
    is an ordinary outcome. A target not currently 進行中 has the staged count
    silently discarded at the next settlement point — accepted, unchanged
    shipped behaviour (divine-sexual-arts-reuse design D-5).
    """
    del context, scale
    try:
        count = int(effect_id.partition(":")[2])
    except ValueError as error:
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            f"divine_climax_extension_stage requires an integer count, "
            f"got {effect_id!r}",
        ) from error
    pending: list[PendingEffect] = []
    for target in targets:
        if target is actor:
            continue
        pending.append(
            PendingEffect(
                target,
                f"divine_climax_extension|{_entity_key(target)}|{count}",
                frozenset(),
                lambda target=target, count=count: target.sexual.stage_climax_extension(
                    count
                ),
            )
        )
    return pending


def _stored_pleasure_value(entity: Any) -> int:
    """Read the stored pleasure base without materializing the sexual handler.

    Constructing ``entity.sexual`` writes the ``sexual_traits`` attribute on
    first access — a storage write at effect-planning time, before the commit
    snapshot, so a cast rejected after planning would leave the created trait
    behind and break the action workflow's all-or-nothing boundary. The same
    no-create discipline ``_sensitivity_level`` (``sexual_act_effects.py``)
    and ``_stored_sexual_level`` (``combat_modifiers.py``) follow. An entity
    whose sexual state was never touched has no ``pleasure`` entry, and its
    baseline floor is 0 (the 平靜 band) — draining it is a no-op.
    """
    from collections.abc import Mapping

    traits = entity.attributes.get("sexual_traits", default=None, category="traits")
    if isinstance(traits, Mapping):
        raw = traits.get("pleasure")
        if isinstance(raw, Mapping):
            base = raw.get("base")
            if isinstance(base, int) and not isinstance(base, bool):
                return min(100, max(0, base))
    return 0


def _handle_sexual_drain(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Drain one target's pleasure into the caster's MP, SP, and HP.

    Reads the resolved target's stored ``pleasure`` value once (no-create —
    see :func:`_stored_pleasure_value`), stages one ``PendingEffect`` on the
    actor (adding that amount to ``mp``, ``sp``, and ``hp`` — each trait's own
    existing bound enforcement clamps at its own maximum) and one on the
    target (setting ``pleasure.base`` to ``0``), so the commit's per-entity
    snapshot/rollback covers both mutated entities. The commit-time apply
    closures may materialize ``entity.sexual``; that happens inside the
    snapshot's coverage and is rolled back by ``_restore_entity_state``.

    ``TargetSpec.SINGLE``'s "exactly one target" guarantee is enforced at
    targeting time, before the resist gate runs; a successfully-resisted sole
    target legitimately empties ``targets`` by the time this handler executes,
    which is an ordinary no-op — never a rejection. Only ``len(targets) > 1``
    rejects, and that case stays structurally unreachable.
    """
    del context, scale, effect_id
    if not targets:
        return []
    if len(targets) > 1:
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            "divine_drain requires exactly one target",
        )
    target = targets[0]
    if target is actor:
        return []
    amount = _stored_pleasure_value(target)
    return [
        PendingEffect(
            actor,
            f"divine_drain_actor|{_entity_key(actor)}|{amount}",
            frozenset(),
            lambda actor=actor, amount=amount: _drain_resources(actor, amount),
        ),
        PendingEffect(
            target,
            f"divine_drain|{_entity_key(target)}|{amount}",
            frozenset(),
            lambda target=target: _zero_pleasure(target),
        ),
    ]


def _handle_saturate_sensitivity(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Pin every non-actor target's resolvable body parts to 敏感異常.

    Stages one ``PendingEffect`` per remaining target whose ``apply()`` calls
    the shipped ``SexualState.saturate_sensitivity()``. The actor is excluded
    explicitly (matching ``_handle_divine_pleasure_max``'s discipline), and an
    empty or shrunken ``targets`` list (a fully or partially resisted cast) is
    an ordinary outcome, never a rejection.
    """
    del context, scale, effect_id
    pending: list[PendingEffect] = []
    for target in targets:
        if target is actor:
            continue
        pending.append(
            PendingEffect(
                target,
                f"divine_saturate_sensitivity|{_entity_key(target)}",
                frozenset(),
                lambda target=target: target.sexual.saturate_sensitivity(),
            )
        )
    return pending


def _handle_clamp_shame(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Pin every non-actor target's shame at 成癮, eagerly rejecting a Monster.

    The ``isinstance(target, Monster)`` check runs eagerly inside the handler
    body, before any ``PendingEffect`` is staged, and raises
    ``RejectedAction(RejectReason.EFFECT_RESOLUTION_FAILED, ...)`` directly.
    It deliberately does not rely on ``clamp_shame_to()``'s defensive
    ``ValueError``: an exception raised from inside a staged
    ``PendingEffect.apply()`` closure is caught by ``_commit()`` and reported
    as ``RejectReason.COMMIT_FAILED`` — a different, and here incorrect, code
    path from the synchronous ``RejectedAction`` this file's other defensive
    rejections produce (divine-sexual-arts-mutators D-3). ``isinstance()`` is
    a pure read, so the eager check introduces no atomicity risk.

    The actor is excluded explicitly, and an empty or shrunken ``targets``
    list (a resisted cast) is an ordinary outcome.
    """
    del context, scale, effect_id
    for target in targets:
        if target is actor:
            continue
        if isinstance(target, Monster):
            raise RejectedAction(
                RejectReason.EFFECT_RESOLUTION_FAILED,
                "divine_clamp_shame cannot target a Monster: "
                f"{_entity_key(target)}",
            )
    pending: list[PendingEffect] = []
    for target in targets:
        if target is actor:
            continue
        pending.append(
            PendingEffect(
                target,
                f"divine_clamp_shame|{_entity_key(target)}",
                frozenset(),
                lambda target=target: target.sexual.clamp_shame_to("成癮"),
            )
        )
    return pending


def _handle_mark_submission(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Mark every non-actor target as auto-complying toward the actor.

    Stages one ``PendingEffect`` per remaining target whose ``apply()`` calls
    ``SexualState.mark_submission(str(actor.id))`` — the actor's
    guaranteed-unique database id, never ``_entity_key(actor)``/``.key``,
    which is shared across same-species ``Monster`` spawns and would
    misattribute the permanent, unremovable mark (divine-sexual-arts-mutators
    D-5). The actor is excluded explicitly, and an empty or shrunken
    ``targets`` list (a resisted cast) is an ordinary outcome.
    """
    del context, scale, effect_id
    pending: list[PendingEffect] = []
    for target in targets:
        if target is actor:
            continue
        pending.append(
            PendingEffect(
                target,
                f"divine_mark_submission|{_entity_key(target)}",
                frozenset(),
                lambda target=target: target.sexual.mark_submission(
                    str(actor.id)
                ),
            )
        )
    return pending


def _handle_restore_purity(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Restore every non-actor target's virgin flag without clearing experience.

    Stages one ``PendingEffect`` per remaining target whose ``apply()`` calls
    the shipped ``SexualState.restore_purity()``. The actor is excluded
    explicitly, and an empty or shrunken ``targets`` list (a resisted cast)
    is an ordinary outcome, never a rejection.
    """
    del context, scale, effect_id
    pending: list[PendingEffect] = []
    for target in targets:
        if target is actor:
            continue
        pending.append(
            PendingEffect(
                target,
                f"divine_restore_purity|{_entity_key(target)}",
                frozenset(),
                lambda target=target: target.sexual.restore_purity(),
            )
        )
    return pending


def _drain_resources(actor: Any, amount: int) -> None:
    """Add ``amount`` to the caster's MP, SP, and HP, clamped per trait."""
    for key in ("mp", "sp", "hp"):
        trait = getattr(actor.traits, key)
        trait.current = trait.current + amount


def _zero_pleasure(target: Any) -> None:
    """Set the target's pleasure gauge to zero."""
    target.sexual.pleasure.base = 0


register_effect_handler(
    "confer_skill_partial",
    _handle_confer_skill_partial,
    frozenset({"skill_grants"}),
    requires_event_context=frozenset({"confer_skill_key", "confer_scale"}),
)
register_effect_handler(
    "set_disguise",
    _handle_set_disguise,
    frozenset({"traits"}),
    requires_event_context=frozenset({"disguise"}),
)
register_effect_handler(
    "buff_apply",
    _handle_buff_apply,
    frozenset({"buffs"}),
    requires_event_context=frozenset(),
)
register_effect_handler(
    "self_buff_apply",
    _handle_self_buff_apply,
    frozenset({"buffs"}),
    requires_event_context=frozenset(),
)
register_effect_handler(
    "confer_growth_rate",
    _handle_confer_growth_rate,
    frozenset({"buffs"}),
    requires_event_context=frozenset({"confer_scale"}),
)
register_effect_handler(
    "sexual_event",
    _handle_sexual_event,
    frozenset({"sexual", "traits"}),
    requires_event_context=frozenset(),
)
register_effect_handler(
    "sexual_event_actor",
    _handle_actor_sexual_event,
    frozenset({"sexual"}),
    requires_event_context=frozenset(),
)
register_effect_handler(
    "pleasure",
    _handle_pleasure_effect,
    frozenset({"sexual"}),
    requires_event_context=frozenset(),
)
register_effect_handler(
    "sexual_counter",
    _handle_sexual_counter_effect,
    frozenset({"sexual"}),
    requires_event_context=frozenset(),
)
register_effect_handler(
    "act_pair_event",
    _handle_act_pair_event,
    frozenset({"sexual"}),
    requires_event_context=frozenset(),
)
register_effect_handler(
    "divine_pleasure_max",
    _handle_divine_pleasure_max,
    frozenset({"sexual"}),
    requires_event_context=frozenset(),
)
register_effect_handler(
    "divine_climax_extension_stage",
    _handle_climax_extension_stage,
    frozenset({"sexual"}),
    requires_event_context=frozenset(),
)
register_effect_handler(
    "divine_drain",
    _handle_sexual_drain,
    frozenset({"traits", "sexual"}),
    requires_event_context=frozenset(),
)
register_effect_handler(
    "divine_saturate_sensitivity",
    _handle_saturate_sensitivity,
    frozenset({"sexual"}),
    requires_event_context=frozenset(),
)
register_effect_handler(
    "divine_clamp_shame",
    _handle_clamp_shame,
    frozenset({"sexual"}),
    requires_event_context=frozenset(),
)
register_effect_handler(
    "divine_mark_submission",
    _handle_mark_submission,
    frozenset({"sexual"}),
    requires_event_context=frozenset(),
)
register_effect_handler(
    "divine_restore_purity",
    _handle_restore_purity,
    frozenset({"sexual"}),
    requires_event_context=frozenset(),
)
register_effect_handler(
    "cleanse",
    _handle_cleanse,
    frozenset({"buffs"}),
    requires_event_context=frozenset(),
)
register_effect_handler(
    "divine_mystery",
    _handle_divine_mystery,
    frozenset(),
    requires_event_context=frozenset(),
)


def _effect_prefix(effect_id: str) -> str:
    return effect_id.partition(":")[0]


def _step5_effect_resolution(
    request: ActionRequest,
    skill: SkillDef,
    targets: list[Any],
) -> list[PendingEffect]:
    pending: list[PendingEffect] = []
    context = _event_context(request)
    for effect_id in skill.effects:
        prefix = _effect_prefix(effect_id)
        handler = _EFFECT_HANDLERS.get(prefix)
        if handler is None:
            raise RejectedAction(RejectReason.UNKNOWN_EFFECT_ID, effect_id)
        try:
            effects = handler(
                request.actor,
                targets,
                effect_id,
                context,
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


def _deduct_resource(trait: Any, amount: int) -> None:
    if hasattr(trait, "current"):
        trait.current = trait.current - amount
    else:
        trait.value = trait.value - amount


def _step6_resource_deduction(
    actor: Any,
    skill: SkillDef,
    scale: float = 1.0,
) -> list[PendingEffect]:
    pending = []
    for resource_key, amount in _adjusted_costs(actor, skill, scale).items():
        trait = getattr(actor.traits, resource_key)
        if _stored_trait_value(trait) < amount:
            raise RejectedAction(
                RejectReason.RESOURCE_DEDUCTION_FAILED,
                resource_key,
            )
        pending.append(
            PendingEffect(
                actor,
                f"resource_spend|{_entity_key(actor)}|{resource_key}|{amount}",
                frozenset({"traits"}),
                lambda trait=trait, amount=amount: _deduct_resource(trait, amount),
            )
        )
    return pending


def _step6_skill_practice(actor: Any, skill: SkillDef) -> PendingEffect:
    """Stage one practice award inside the action's transactional commit."""
    return PendingEffect(
        actor,
        f"skill_practice|{_entity_key(actor)}|{skill.key}",
        frozenset({"progression"}),
        lambda: grant_skill_practice_xp(actor, skill.key),
    )


def _step6_combat_kill_xp(
    request: ActionRequest,
    targets: list[Any],
) -> list[PendingEffect]:
    """Stage one post-damage kill award per initially living tiered monster."""
    if request.context.battlefield is None:
        return []
    pending: list[PendingEffect] = []
    seen: set[int] = set()
    for target in targets:
        if id(target) in seen:
            continue
        seen.add(id(target))
        if not isinstance(target, Monster):
            continue
        tier_key = target.threat_tier
        if tier_key not in MONSTER_TIER_REGISTRY or _stored_trait_value(target.traits.hp) <= 0:
            continue
        pending.append(
            PendingEffect(
                request.actor,
                f"combat_kill_xp|{_entity_key(target)}|{tier_key}",
                frozenset({"progression"}),
                lambda target=target, tier_key=tier_key: (
                    grant_combat_kill_xp(request.actor, tier_key)
                    if _stored_trait_value(target.traits.hp) <= 0
                    else None
                ),
            )
        )
    return pending


_ENTRY_TEMPLATES = {
    "resource_spend": "{actor} 消耗了資源。",
    "skill_granted": "{actor} 對 {target} 施展了「統御術」的部分效果。",
    "disguise_set": "{actor} 改變了 {target} 的偽裝狀態。",
    "buff_applied": "{actor} 對 {target} 施加了狀態效果。",
    "self_buff_applied": "{actor} 凝聚精神，狀態獲得提升。",
    "buffs_cleansed": "{actor} 淨化了 {target} 的異常狀態。",
    "equipment_immune": "{target} 的裝備抵銷了{actor} 施加的負面效果——{target} 對此免疫。",
    "sexual_transition": "{target} 的狀態發生了變化。",
    "sexual_resist": "{target} 面對 {actor} 的意圖，做出了自己的選擇。",
    "pleasure_gain": "{target} 的快感提升了。",
    "sexual_counter": "{target} 的性行為計數提升了。",
    "trait_delta": "{target} 的能力值發生了變化。",
    "roll": "{actor} 對 {target} 的攻擊擲出了 {data[raw_roll]}。",
    "damage": "{actor} 對 {target} 造成了 {data[amount]} 點傷害。",
    "heal": "{actor} 對 {target} 恢復了 {data[amount]} 點生命。",
    "self_heal": "{actor} 恢復了 {data[amount]} 點生命。",
    "target_defeated": "{actor} 擊敗了 {target}。",
    "target_knocked_out": "{actor} 擊倒了 {target}。",
    "disengage_attempt": "{actor} 嘗試脫離戰鬥。",
    "skill_practice": "{actor} 累積了技能熟練度。",
    "combat_kill_xp": "",
    "knocked_out_mark": "",
    "divine_pleasure_max": "{actor} 以神之律令，將 {target} 的快感推至頂點。",
    "divine_climax_extension": "{actor} 以神之律令，延續了 {target} 的絕頂。",
    "divine_drain": "{actor} 從 {target} 身上汲取了神域之力。",
    "divine_drain_actor": "",
    "divine_saturate_sensitivity": "{actor} 以神之律令，重塑了 {target} 的感官。",
    "divine_clamp_shame": "{actor} 以神之律令，剝奪了 {target} 的羞恥。",
    "divine_mark_submission": "{actor} 以神之律令，將 {target} 化為絕對從屬。",
    "divine_restore_purity": "{actor} 以神之律令，使 {target} 回歸純淨。",
}


def _entries_from_effect(
    actor_key: str,
    effect: PendingEffect,
) -> tuple[EventEntry, ...]:
    parts = effect.description.split("|")
    if len(parts) < 2 or parts[0] not in _ENTRY_TEMPLATES:
        raise ValueError(f"malformed pending-effect description {effect.description!r}")
    kind, target, *values = parts
    if kind == "resource_spend":
        data = {
            "resource_key": values[0],
            "amount": int(values[1]),
        }
    elif kind == "skill_granted":
        data = {
            "skill_key": values[0],
            "scale": float(values[1]),
        }
    elif kind == "buff_applied":
        data = {"buff_key": values[0]}
    elif kind == "self_buff_applied":
        data = {"buff_key": values[0]}
    elif kind == "equipment_immune":
        if len(values) != 1:
            raise ValueError(
                f"malformed equipment_immune pending effect {effect.description!r}"
            )
        data = {"buff_key": values[0]}
    elif kind == "buffs_cleansed":
        if len(values) != 1:
            raise ValueError(
                f"malformed buffs_cleansed pending effect {effect.description!r}"
            )
        data = {"count": int(values[0])}
    elif kind == "sexual_transition":
        data = {"event": values[0]}
    elif kind == "pleasure_gain":
        if len(values) != 1:
            raise ValueError(
                f"malformed pleasure_gain pending effect {effect.description!r}"
            )
        data = {"amount": int(values[0])}
    elif kind == "sexual_counter":
        if len(values) != 1:
            raise ValueError(
                f"malformed sexual_counter pending effect {effect.description!r}"
            )
        data = {"counter": values[0]}
    elif kind == "sexual_resist":
        if len(values) != 3:
            raise ValueError(
                f"malformed sexual_resist pending effect {effect.description!r}"
            )
        data = {
            "resisted": bool(int(values[0])),
            "auto_comply": bool(int(values[1])),
            "roll": None if values[2] == "none" else int(values[2]),
        }
    elif kind == "damage":
        if len(values) != 3:
            raise ValueError(
                f"malformed damage pending effect {effect.description!r}"
            )
        raw_roll, hit_flag, amount = map(int, values)
        roll_entry = EventEntry(
            kind="roll",
            actor=actor_key,
            target=target,
            data={"raw_roll": raw_roll, "hit": bool(hit_flag)},
            text_template=_ENTRY_TEMPLATES["roll"],
        )
        if not hit_flag:
            return (roll_entry,)
        return (
            roll_entry,
            EventEntry(
                kind="damage",
                actor=actor_key,
                target=target,
                data={"amount": amount},
                text_template=_ENTRY_TEMPLATES["damage"],
            ),
        )
    elif kind == "disengage_attempt":
        if len(values) != 4:
            raise ValueError(
                f"malformed disengage pending effect {effect.description!r}"
            )
        success_flag, raw_roll, actor_agility, pursuer_agility = values
        data = {
            "success": bool(int(success_flag)),
            "roll": None if raw_roll == "none" else int(raw_roll),
            "actor_agility": float(actor_agility),
            "pursuer_agility": (
                None
                if pursuer_agility == "none"
                else float(pursuer_agility)
            ),
        }
    elif kind in ("heal", "self_heal"):
        if len(values) != 1:
            raise ValueError(
                f"malformed heal pending effect {effect.description!r}"
            )
        data = {"amount": int(values[0])}
    elif kind == "combat_kill_xp":
        return ()
    elif kind == "knocked_out_mark":
        return ()
    elif kind == "divine_drain_actor":
        # Internal actor-side drain effect: the resource gain is rolled back
        # with the cast, and the logged narration is the single target-side
        # divine_drain entry — an actor entry would misnarrate as the caster
        # draining themselves.
        return ()
    else:
        data = {}
    entry = EventEntry(
        kind=kind,
        actor=actor_key,
        target=target,
        data=data,
        text_template=_ENTRY_TEMPLATES[kind],
    )
    if kind != "resource_spend":
        return (entry,)
    return (
        entry,
        EventEntry(
            kind="trait_delta",
            actor=actor_key,
            target=target,
            data={
                "trait_key": data["resource_key"],
                "delta": -data["amount"],
            },
            text_template=_ENTRY_TEMPLATES["trait_delta"],
        ),
    )


def _defeated_entry(
    actor_key: str,
    entity: Any,
    amount: int,
    projected: dict[int, float],
    defeated_ids: set[int],
    nonlethal: bool = False,
    simulated: bool = False,
) -> EventEntry | None:
    """Emit one ``target_defeated`` or ``target_knocked_out`` crossing entry.

    Pending damage is applied in order over shared projected HP, so two damage
    effects against one target neither use stale HP nor duplicate the defeat.
    Under a nonlethal policy a positive-to-non-positive crossing emits a
    ``target_knocked_out`` identity instead of ``target_defeated``, giving
    kill-credit/quest/loot consumers no defeat entry to observe. A simulated
    battle (guild examination) keeps the ordinary lethal ``target_defeated``
    entry but tags it ``simulated``, so kill-credit consumers can skip the
    defeat without hiding that the HP really crossed zero
    (exam-simulated-battle-redesign D4).
    """
    if amount <= 0:
        return None
    trait = getattr(entity, "traits", None)
    hp = getattr(trait, "hp", None)
    if hp is None:
        return None
    dbref = getattr(entity, "pk", None)
    if dbref is None:
        return None
    identity = id(entity)
    current = projected.get(identity, _stored_trait_value(hp))
    projected[identity] = current - amount
    if not (current > 0 and projected[identity] <= 0):
        return None
    if dbref in defeated_ids:
        return None
    defeated_ids.add(dbref)
    kind = "target_knocked_out" if nonlethal else "target_defeated"
    data: dict[str, Any] = {"target_id": int(dbref)}
    if not nonlethal:
        data["monster_tier"] = getattr(entity, "threat_tier", None)
    if simulated:
        data["simulated"] = True
    return EventEntry(
        kind=kind,
        actor=actor_key,
        target=str(entity.key),
        data=data,
        text_template=(
            _ENTRY_TEMPLATES["target_knocked_out"]
            if nonlethal
            else _ENTRY_TEMPLATES["target_defeated"]
        ),
    )


def _step7_build_event_log(
    request: ActionRequest,
    skill: SkillDef,
    pending: list[PendingEffect],
) -> EventLog:
    try:
        entries: list[EventEntry] = []
        projected: dict[int, float] = {}
        defeated_ids: set[int] = set()
        event_context = _event_context(request)
        nonlethal = bool(event_context.get("nonlethal", False))
        nonlethal_keys = frozenset(event_context.get("nonlethal_keys", ()))
        simulated = bool(event_context.get("simulated", False))
        for effect in pending:
            entries.extend(
                _entries_from_effect(
                    _entity_key(request.actor),
                    effect,
                )
            )
            if not effect.description.startswith("damage|"):
                continue
            parts = effect.description.split("|")
            defeated = _defeated_entry(
                _entity_key(request.actor),
                effect.entity,
                int(parts[4]),
                projected,
                defeated_ids,
                nonlethal=nonlethal or str(effect.entity.key) in nonlethal_keys,
                simulated=simulated,
            )
            if defeated is not None:
                entries.append(defeated)
    except Exception as error:
        raise RejectedAction(
            RejectReason.EVENT_LOG_CONSTRUCTION_FAILED,
            str(error),
        ) from error
    return EventLog(
        actor=_entity_key(request.actor),
        skill_key=skill.key,
        targets=_logged_targets(pending),
        entries=tuple(entries),
        time_cost_seconds=0,
    )


def _logged_targets(pending: list[PendingEffect]) -> tuple[str, ...]:
    targets: list[str] = []
    for effect in pending:
        if effect.description.startswith(
            ("resource_spend|", "combat_kill_xp|", "knocked_out_mark|")
        ):
            continue
        key = effect.description.split("|", 2)[1]
        if key not in targets:
            targets.append(key)
    return tuple(targets)


def _step8_time_cost(request: ActionRequest, skill: SkillDef) -> int:
    seconds = SKILL_TIME_OVERRIDES.get(skill.key, DEFAULT_CAST_SECONDS)
    if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds < 0:
        raise RejectedAction(
            RejectReason.TIME_COST_LOOKUP_FAILED,
            f"{skill.key}: {seconds!r}",
        )
    return seconds


def _stored_trait_value(trait: Any) -> float:
    """Read deterministic stored state without advancing a wall-clock gauge."""
    data = trait._data
    if trait.trait_type == "gauge":
        return data.get(
            "current",
            (data["base"] + data["mod"]) * data["mult"],
        )
    return data.get("value", (data.get("base", 0) + data.get("mod", 0)) * data.get("mult", 1))


def _attribute_snapshot(
    entity: Any,
    key: str,
    category: str | None = None,
) -> tuple[bool, Any]:
    exists = entity.attributes.has(key, category=category)
    value = (
        deepcopy(entity.attributes.get(key, category=category))
        if exists
        else None
    )
    return exists, value


def _snapshot_entity_state(entity: Any) -> dict[str, Any]:
    return {
        "traits": _attribute_snapshot(entity, "traits", "traits"),
        "disguised_stats": _attribute_snapshot(entity, "disguised_stats"),
        "sexual_traits": _attribute_snapshot(
            entity,
            "sexual_traits",
            "traits",
        ),
        "virgin": _attribute_snapshot(entity, "virgin", "sexual_state"),
        "experience_types": _attribute_snapshot(
            entity,
            "experience_types",
            "sexual_state",
        ),
        "climax_turns": _attribute_snapshot(entity, "climax_turns", "sexual_state"),
        "pending_climax_extension": _attribute_snapshot(
            entity,
            "pending_climax_extension",
            "sexual_state",
        ),
        "buffs": _attribute_snapshot(entity, "buffs"),
        "skill_grants": _attribute_snapshot(entity, "skill_grants"),
        "magic_xp": _attribute_snapshot(entity, "magic_xp"),
        "skill_proficiency": _attribute_snapshot(entity, "skill_proficiency"),
    }


def _restore_attribute(
    entity: Any,
    key: str,
    snapshot: tuple[bool, Any],
    category: str | None = None,
) -> None:
    existed, value = snapshot
    if existed:
        entity.attributes.add(key, deepcopy(value), category=category)
    else:
        entity.attributes.remove(key, category=category)


def _restore_entity_state(entity: Any, snapshot: dict[str, Any]) -> None:
    _restore_attribute(entity, "traits", snapshot["traits"], "traits")
    _restore_attribute(entity, "disguised_stats", snapshot["disguised_stats"])
    _restore_attribute(
        entity,
        "sexual_traits",
        snapshot["sexual_traits"],
        "traits",
    )
    _restore_attribute(entity, "virgin", snapshot["virgin"], "sexual_state")
    _restore_attribute(
        entity,
        "experience_types",
        snapshot["experience_types"],
        "sexual_state",
    )
    _restore_attribute(
        entity,
        "climax_turns",
        snapshot["climax_turns"],
        "sexual_state",
    )
    _restore_attribute(
        entity,
        "pending_climax_extension",
        snapshot["pending_climax_extension"],
        "sexual_state",
    )
    _restore_attribute(entity, "buffs", snapshot["buffs"])
    _restore_attribute(entity, "skill_grants", snapshot["skill_grants"])
    _restore_attribute(entity, "magic_xp", snapshot["magic_xp"])
    _restore_attribute(entity, "skill_proficiency", snapshot["skill_proficiency"])
    entity.traits.trait_data = entity.attributes.get(
        "traits",
        default={},
        category="traits",
    )
    entity.traits._cache.clear()
    entity.__dict__.pop("sexual", None)


def _is_battlefield_like(obj: Any) -> bool:
    """Return whether an object exposes the encounter state this resolver owns."""
    return hasattr(obj, "fled") and hasattr(obj, "roster")


_ENTITY_SURFACES = frozenset({"traits", "sexual", "buffs", "skill_grants", "progression"})


def _snapshot_touched(obj: Any, surfaces: frozenset[str]) -> dict[str, Any]:
    """Snapshot the aggregated declared surfaces of one touched object."""
    if _is_battlefield_like(obj):
        return {
            "battlefield": (
                frozenset(obj.fled),
                frozenset(getattr(obj, "knocked_out", ())),
            )
        }
    snapshot: dict[str, Any] = {}
    if surfaces & _ENTITY_SURFACES:
        snapshot["entity"] = _snapshot_entity_state(obj)
    if "quest_log" in surfaces:
        snapshot["quest_log"] = _attribute_snapshot(obj, "quest_log")
    if "instance_pin" in surfaces:
        snapshot["instance_pin"] = _attribute_snapshot(obj, "pin_reasons")
    return snapshot


def _restore_touched(
    obj: Any,
    snapshot: dict[str, Any],
    surfaces: frozenset[str],
) -> None:
    """Restore an object's aggregated declared surfaces by shape."""
    if _is_battlefield_like(obj):
        fled, knocked_out = snapshot.get(
            "battlefield",
            (
                frozenset(obj.fled),
                frozenset(getattr(obj, "knocked_out", ())),
            ),
        )
        obj.fled = set(fled)
        if hasattr(obj, "knocked_out"):
            obj.knocked_out = set(knocked_out)
        return
    if "entity" in snapshot:
        _restore_entity_state(obj, snapshot["entity"])
    if "quest_log" in surfaces and "quest_log" in snapshot:
        _restore_attribute(obj, "quest_log", snapshot["quest_log"])
    if "instance_pin" in surfaces and "instance_pin" in snapshot:
        _restore_attribute(obj, "pin_reasons", snapshot["instance_pin"])


def _restore_touched_best_effort(
    obj: Any,
    snapshot: dict[str, Any],
    surfaces: frozenset[str],
) -> None:
    """Restore one touched object without letting a second failure escape.

    After a commit failure the database is rolled back; if restoring the
    pre-operation value also raises, invalidating Evennia's attribute cache
    leaves the next read consistent with persistence instead of serving a
    stale value.
    """
    from evennia.utils.logger import log_warn

    try:
        _restore_touched(obj, snapshot, surfaces)
    except Exception as error:
        try:
            obj.attributes.reset_cache()
        except Exception:
            pass
        log_warn(f"action commit could not restore {obj}: {error}")


def _commit(pending: list[PendingEffect]) -> None:
    for effect in pending:
        unsupported = effect.surfaces - SNAPSHOTTED_SURFACES
        if unsupported:
            raise CommitFailed(
                RejectReason.UNSNAPSHOTTED_EFFECT_SURFACE,
                f"{effect.description}: {sorted(unsupported)}",
            )
    touched: list[Any] = []
    touched_ids: set[int] = set()
    surfaces_of: dict[int, frozenset[str]] = {}
    for effect in pending:
        identity = id(effect.entity)
        surfaces_of[identity] = surfaces_of.get(identity, frozenset()) | frozenset(
            effect.surfaces
        )
        if identity not in touched_ids:
            touched.append(effect.entity)
            touched_ids.add(identity)
    snapshots = {
        id(entity): _snapshot_touched(entity, surfaces_of[id(entity)])
        for entity in touched
    }
    try:
        with transaction.atomic():
            for effect in pending:
                effect.apply()
    except Exception as error:
        for entity in touched:
            _restore_touched_best_effort(entity, snapshots[id(entity)], surfaces_of[id(entity)])
        raise CommitFailed(RejectReason.COMMIT_FAILED, str(error)) from error


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
            _step3_targeting(request, skill)
            _step4_capability(request.actor)
            context = _event_context(request)
            for effect_id in skill.effects:
                prefix = _effect_prefix(effect_id)
                if prefix not in _EFFECT_HANDLERS:
                    raise RejectedAction(
                        RejectReason.UNKNOWN_EFFECT_ID,
                        effect_id,
                    )
                missing = _EFFECT_HANDLER_REQUIRED_CONTEXT[prefix] - context.keys()
                if missing:
                    raise RejectedAction(
                        RejectReason.MISSING_EFFECT_CONTEXT,
                        f"missing event_context key {sorted(missing)[0]!r}",
                    )
            _step8_time_cost(request, skill)
        except RejectedAction as rejection:
            return ActionResult.rejected(rejection.reason, rejection.detail)
        return ActionResult.success(None, None)

    @staticmethod
    def resolve(request: ActionRequest) -> ActionResult:
        try:
            skill = _step1_ownership(request)
            _step2_resource_check(request.actor, skill, request.scale)
            targets = _step3_targeting(request, skill)
            _step4_capability(request.actor)
            targets, resist_pending = _step4b_sexual_resist_gate(
                request,
                skill,
                targets,
            )
            pending = resist_pending + _step5_effect_resolution(
                request,
                skill,
                targets,
            )
            pending += _step6_resource_deduction(request.actor, skill, request.scale)
            pending.append(_step6_skill_practice(request.actor, skill))
            pending += _step6_combat_kill_xp(request, targets)
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
        except RejectedAction as rejection:
            return ActionResult.rejected(rejection.reason, rejection.detail)
        try:
            _commit(pending)
        except CommitFailed as failure:
            return ActionResult.rejected(failure.reason, failure.detail)
        return ActionResult.success(event_log, time_cost)
