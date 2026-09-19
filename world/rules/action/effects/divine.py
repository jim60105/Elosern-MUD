"""Divine-arts mutator effect handlers (divine sexual arts).

Every handler excludes the acting entity explicitly and stages one
``PendingEffect`` per remaining target; defensive eager rejections (a Monster
target of ``divine_clamp_shame``) run in the handler body, never inside a
staged ``apply()`` closure. Registrations live next to their handlers.
"""

from typing import Any, Callable

from typeclasses.monsters import Monster
from world.rules.pleasure import apply_pleasure_gain, zero_pleasure

from world.rules.action.contracts import (
    _entity_key,
    register_effect_handler,
    PendingEffect,
    RejectedAction,
    RejectReason,
)


def _stage_non_actor_targets(
    targets: list[Any],
    actor: Any,
    tag: Callable[[Any], str],
    apply_for: Callable[[Any], Callable[[], None]],
) -> list[PendingEffect]:
    """Stage one divine mutator per non-actor target.

    The actor is excluded explicitly even when present in the resolved
    ``targets`` list: the ``"all"`` AREA shorthand has no self-exclusion, and
    the resist gate keeps an actor present without rolling a contest for it.
    ``apply_for`` is invoked at staging time so each staged effect closes over
    its own target.
    """
    return [
        PendingEffect(target, tag(target), frozenset(), apply_for(target))
        for target in targets
        if target is not actor
    ]


def _handle_divine_pleasure_max(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Set every non-actor target's pleasure to its ceiling in one cast.

    Stages one ``PendingEffect`` per remaining target whose ``apply()`` calls
    the shipped :func:`world.rules.pleasure.apply_pleasure_gain` twice in sequence — ``gain=100``
    (sets ``pleasure`` to its clamped ceiling and walks at most one climax
    cycle edge) then ``gain=0`` (re-runs the pre/post-mutation check, which
    now observes the already-updated phase and walks the second edge into
    進行中). Two calls, not one, because ``apply_pleasure_gain`` deliberately
    advances ``climax_phase`` by at most one cycle edge per call
    (divine-sexual-arts-reuse design D-2).

    The actor is excluded explicitly even when present in the resolved
    ``targets`` list: the ``"all"`` AREA shorthand has no self-exclusion, and
    ``_step4b_sexual_resist_gate`` keeps an actor present in ``targets``
    without rolling a contest for it. An empty or shrunken ``targets`` list
    (a fully or partially resisted cast) is an ordinary outcome.
    """
    del context, scale, effect_id
    return _stage_non_actor_targets(
        targets,
        actor,
        lambda target: f"divine_pleasure_max|{_entity_key(target)}|100",
        lambda target: lambda: (
            apply_pleasure_gain(target, 100),
            apply_pleasure_gain(target, 0),
        ),
    )


def _handle_pleasure_peak(
    actor: Any,
    targets: list[Any],
    effect_id: str,
    context: dict[str, Any],
    scale: float,
) -> list[PendingEffect]:
    """Advance every recipient's pleasure through positive-gain then zero-gain.

    Stages one PendingEffect per recipient calling apply_pleasure_gain(100)
    then apply_pleasure_gain(0), advancing climax phase through canonical
    cycle edges without direct phase assignment or artificial extension.
    """
    del effect_id, context, scale
    pending: list[PendingEffect] = []
    seen_ids: set[int] = set()
    for recipient in targets:
        if id(recipient) in seen_ids:
            continue
        seen_ids.add(id(recipient))
        pending.append(
            PendingEffect(
                recipient,
                f"pleasure_peak|{_entity_key(recipient)}|100",
                frozenset({"sexual", "traits", "buffs"}),
                lambda r=recipient: (
                    apply_pleasure_gain(r, 100),
                    apply_pleasure_gain(r, 0),
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
            lambda target=target: zero_pleasure(target),
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
    return _stage_non_actor_targets(
        targets,
        actor,
        lambda target: f"divine_saturate_sensitivity|{_entity_key(target)}",
        lambda target: lambda: target.sexual.saturate_sensitivity(),
    )


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
    return _stage_non_actor_targets(
        targets,
        actor,
        lambda target: f"divine_mark_submission|{_entity_key(target)}",
        lambda target: lambda: target.sexual.mark_submission(str(actor.id)),
    )


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
    return _stage_non_actor_targets(
        targets,
        actor,
        lambda target: f"divine_restore_purity|{_entity_key(target)}",
        lambda target: lambda: target.sexual.restore_purity(),
    )


def _drain_resources(actor: Any, amount: int) -> None:
    """Add ``amount`` to the caster's MP, SP, and HP, clamped per trait."""
    for key in ("mp", "sp", "hp"):
        trait = getattr(actor.traits, key)
        trait.current = trait.current + amount


register_effect_handler(
    "divine_pleasure_max",
    _handle_divine_pleasure_max,
    frozenset({"sexual", "traits", "buffs"}),
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
    "pleasure_peak",
    _handle_pleasure_peak,
    frozenset({"sexual", "traits", "buffs"}),
    requires_event_context=frozenset(),
)
