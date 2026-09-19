"""Sexual act event, pleasure, counter, and stimulus effect handlers.

Handlers for the act-catalog verbs (events, pleasure, counters, pair events,
stimulus). The ``apply_event`` and transition-rule imports stay deferred to
match the pipeline's cycle-avoidance discipline. Registrations live next to
their handlers.
"""

import random
from typing import Any

from world.rules.equipment_effects import equipment_pleasure_gain
from world.rules.pleasure import apply_pleasure_gain
from world.rules.sexual_act_effects import (
    _COUNTER_MUTATORS,
    _OBSERVER_GATED_COUNTERS,
    _OBSERVER_GATED_EVENTS,
    compute_pleasure_gain,
    observers_present,
    pair_event_name,
    participants,
    resolve_part,
)
from world.skills.effects import ResolvedEffect
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY

from world.rules.action.contracts import (
    _entity_key,
    register_effect_handler,
    PendingEffect,
    RejectedAction,
    RejectReason,
)


def _stage_apply_event(
    recipients: list[Any],
    event_name: str,
    sexual_context: dict[str, Any],
) -> list[PendingEffect]:
    """Stage one deferred ``apply_event`` call per recipient.

    The ``apply_event`` import stays deferred to match the module's existing
    cycle-avoidance discipline; an unavailable rules module rejects the action
    rather than staging a commit-time crash. ``sexual_context`` is built by
    each caller so the pair-event handler's resolution order — act resolution
    before any context read — stays byte-identical.
    """
    try:
        from world.rules.sexual_transitions import apply_event
    except ImportError as error:
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            "sexual-transition rules are unavailable (change 7b)",
        ) from error
    return [
        PendingEffect(
            r,
            f"sexual_transition|{_entity_key(r)}|{event_name}",
            frozenset(),
            lambda r=r: apply_event(r, event_name, **sexual_context),
        )
        for r in recipients
    ]


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
    handlers, with no name-based recipient exception: recipient scope is
    decided statically by the effect prefix (``sexual_event:`` participant-,
    ``sexual_event_actor:`` actor-, ``sexual_event_target:`` target-scoped),
    never by an event-name lookup. Resisted targets were already excluded
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
    return _stage_apply_event(
        participants(actor, targets),
        event_name,
        dict(context.get("sexual", {})),
    )


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
    return _stage_apply_event([actor], event_name, dict(context.get("sexual", {})))


def _handle_target_sexual_event(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Apply one target-scoped event to the cast's resolved targets only.

    The target-scoped twin of ``_handle_sexual_event`` and
    ``_handle_actor_sexual_event``: a hand-built row declaring a target-only
    event (``divine_sexual_arts``'s ``stimulus_applied``) emits it through
    the ``sexual_event_target:<name>`` prefix so the resolved event lands on
    every surviving target and never on the acting entity — the divine-arts
    exemption from self-pleasure (D-9) is carried by the prefix, not by an
    event-name exception table. Resisted targets were already excluded from
    ``targets`` by ``_step4b_sexual_resist_gate``, so a fully resisted cast
    stages nothing and stays an ordinary success. A missing event name never
    reaches this handler: the prefix fails closed at ``SkillDef``
    construction through ``_parse_single_arg``. No observer gating applies —
    ``watched_during_activity`` remains reachable only through the
    actor-scoped channel's gated vocabulary. The self-exclusion is explicit:
    AREA resolution's ``"all"`` shorthand has no self-exclusion (see
    ``_step4b_sexual_resist_gate``'s actor guard for the same route), so a
    future AREA target-scoped row could otherwise deliver its event to the
    caster — matching the divine target-only handlers' per-target skip.
    """
    del scale
    event_name = effect_id.partition(":")[2]
    if not event_name:
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            "sexual_event_target requires an event name",
        )
    return _stage_apply_event(
        [target for target in targets if target is not actor],
        event_name,
        dict(context.get("sexual", {})),
    )


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
    return _stage_apply_event(participants(actor, targets), event_name, sexual_context)


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
    participant's gain. Each participant's gain carries that
    participant's OWN equipment ``pleasure_gain`` percent (the pure
    accessor is evaluated per participant, never shared across the cast).
    Each staged ``PendingEffect`` applies that participant's own computed
    gain through :func:`world.rules.pleasure.apply_pleasure_gain`.
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
        gain = compute_pleasure_gain(
            participant,
            part,
            act.base_pleasure,
            ratio,
            count,
            pleasure_percent=equipment_pleasure_gain(participant),
        )
        pending.append(
            PendingEffect(
                participant,
                f"pleasure_gain|{_entity_key(participant)}|{gain}",
                frozenset(),
                lambda participant=participant, gain=gain: apply_pleasure_gain(
                    participant, gain
                ),
            )
        )
    return pending


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


def _get_stimulus_interval() -> tuple[int, int]:
    from world.rules.sexual_transitions import _RULES, _parse_delta

    for rule in _RULES:
        if rule.when.get("event") == "stimulus_applied" and rule.then.get("field") == "pleasure":
            parsed = _parse_delta(rule.then["delta"])
            if isinstance(parsed, tuple):
                return parsed
            return (parsed, parsed)
    return (8, 14)


_stimulus_rng = random.Random()


def _handle_stimulus(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    del scale
    prefix, _, scope = effect_id.partition(":")
    if scope not in ("actor", "target", "both"):
        raise RejectedAction(
            RejectReason.EFFECT_RESOLUTION_FAILED,
            f"invalid stimulus scope {scope!r}",
        )

    resolved = context.get("resolved_effect")
    policy = resolved.policy if isinstance(resolved, ResolvedEffect) else None
    stimulus_bonus = getattr(policy, "stimulus_bonus", None)

    recipients: list[Any] = []
    seen_ids: set[int] = set()

    def _add_recipient(obj: Any) -> None:
        if id(obj) not in seen_ids:
            seen_ids.add(id(obj))
            recipients.append(obj)

    if scope in ("actor", "both"):
        _add_recipient(actor)
    if scope in ("target", "both"):
        for target in targets:
            if target is not actor:
                _add_recipient(target)

    lo, hi = _get_stimulus_interval()
    pending: list[PendingEffect] = []

    for recipient in recipients:
        base_delta = _stimulus_rng.randint(lo, hi)
        bonus = 0.0
        if recipient is not actor and stimulus_bonus is not None:
            from world.rules.state_reactions import compute_state_magnitude

            bonus = compute_state_magnitude(stimulus_bonus, actor, actor=actor)

        pleasure_pct = equipment_pleasure_gain(recipient)
        total_gain = max(0, round((base_delta + bonus) * (1 + pleasure_pct / 100)))

        pending.append(
            PendingEffect(
                recipient,
                f"pleasure_gain|{_entity_key(recipient)}|{total_gain}",
                frozenset({"sexual", "traits", "buffs"}),
                lambda r=recipient, g=total_gain: apply_pleasure_gain(r, g),
            )
        )
    return pending


register_effect_handler(
    "sexual_event",
    _handle_sexual_event,
    frozenset({"sexual", "traits", "buffs"}),
    requires_event_context=frozenset(),
)
register_effect_handler(
    "sexual_event_actor",
    _handle_actor_sexual_event,
    frozenset({"sexual", "traits", "buffs"}),
    requires_event_context=frozenset(),
)
register_effect_handler(
    "sexual_event_target",
    _handle_target_sexual_event,
    frozenset({"sexual", "traits", "buffs"}),
    requires_event_context=frozenset(),
)
register_effect_handler(
    "pleasure",
    _handle_pleasure_effect,
    frozenset({"sexual", "traits", "buffs"}),
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
    "stimulus",
    _handle_stimulus,
    frozenset({"sexual", "traits", "buffs"}),
    requires_event_context=frozenset(),
)
