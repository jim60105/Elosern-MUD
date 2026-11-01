"""Whole-party wilderness camping (OpenSpec change wilderness-camping).

One camp is one wake-target decision for the present party: enter every
eligible body's sleep at zero time, answer the owner's dream question in the
same transaction (enter on explicit opt-in, otherwise an explicit decline),
then continue the selected accepted plans until the slowest of them wakes or a
real interaction/safety boundary interrupts.

Nothing here owns physiology, the clock or receipts. Selection, eligibility
and targets come from ``world.rules.time_skip`` (``plan_party_entry``) and
``world.rules.sleep_control`` (``_party_status``, ``begin_all_party_sleep``);
every interval is ``time_skip.continue_sleep``; the dream answer is the guarded
``server.dream_service.answer_sleep_dream``. This module adds the read-only
projection (:func:`plan_camp`, :func:`preview_camp`), the atomic entry seam
(:func:`commit_sleep_entry`), the camp continuation (:func:`continue_camp`)
and the durable progress/result bookkeeping (:func:`record_camp_interval`,
:func:`finalize_camp`, :func:`reconcile_camp`).

The wire names the two camp modes ``until-dawn`` and ``until-recovered``; the
internal recovery mode keeps its existing ``recovery`` value and is
translated once here.
"""

from __future__ import annotations

from typing import Any

from world.rules.fatigue import (
    FatigueActivity,
    FatigueState,
    SleepPosture,
    get_policy,
    predict_interval,
    read_optional_fatigue_state,
    reserve_percent,
)
from world.rules.time_skip import SleepRefused
from world.rules.sleep_receipt import (
    MODE_RECOVERY,
    MODE_UNTIL_DAWN,
    forced_wake_seconds,
    recovery_target_tick,
)

#: The two wire camp modes, in their fixed presentation order.
WIRE_DAWN = "until-dawn"
WIRE_RECOVERED = "until-recovered"
WIRE_MODES = (WIRE_DAWN, WIRE_RECOVERED)
_INTERNAL_MODES = {WIRE_DAWN: MODE_UNTIL_DAWN, WIRE_RECOVERED: MODE_RECOVERY}
_WIRE_FOR_INTERNAL = {value: key for key, value in _INTERNAL_MODES.items()}

#: Stable refusal codes beyond the reused gate values.
CODE_PARTY_UNAVAILABLE = "party_unavailable"
CODE_DREAM_NOT_OFFERABLE = "dream_not_offerable"
DREAM_NOT_OFFERABLE_MESSAGE = "目前無法在入睡時進入夢境協作。"

_MAX_NAME = 256
_MAX_MEMBER_ID = 64
_PREDICTION_STEPS = 64


def internal_mode(wire_mode: str) -> str:
    """The internal sleep mode of one wire camp mode (KeyError when unknown)."""
    return _INTERNAL_MODES[wire_mode]


def wire_mode(mode: str) -> str:
    """The wire camp mode of one internal sleep mode."""
    return _WIRE_FOR_INTERNAL[mode]


def display_time(tick: int) -> str:
    """The bounded server display text of one tick (``第 N 日 HH:MM``)."""
    from world.rules.travel_events import day_and_time

    day, clock_text = day_and_time(int(tick))
    return f"第 {day} 日 {clock_text}"[:32]


def read_tick() -> int:
    """The committed world tick without creating the clock singleton."""
    from world.rules.clock import read_world_clock

    clock = read_world_clock()
    return 0 if clock is None else int(clock.tick)


def default_wire_mode(tick: int) -> str:
    """Dawn during the dusk/night light phases, recovery during dawn/day."""
    from world.rules.clock import WorldDateTime
    from world.rules.sight import light_phase

    phase = light_phase(WorldDateTime.from_tick(int(tick)))
    return WIRE_DAWN if phase in ("dusk", "night") else WIRE_RECOVERED


def camp_preflight(actor: Any, mode: str, seconds: int | None = None) -> dict[str, Any]:
    """The one shared camp gate: safety, then the all-party admission.

    Preview and the committed camp both call this, before and again under the
    entry lock, so their refusal code and message cannot drift: skip safety
    keeps its stable ``in_combat``/``hostile_present`` value, the all-party
    wrapper its ``party_unavailable`` code with the member/possession reason,
    and a deeper receipt failure its own ``SleepRefused`` code. Nothing is
    written.
    """
    from world.rules.party_scope import (
        PartyScopeError,
        present_party_scope,
        resolve_commander,
    )
    from world.rules.skip_safety import evaluate_skip_safety
    from world.rules.sleep_control import REASON_NOT_CONTROLLING, _party_status
    from world.rules.time_skip import (
        SleepRefused,
        _validate_sleep_request,
        plan_party_entry,
        rejection_message,
    )

    duration = _validate_sleep_request(mode, seconds)
    reason = evaluate_skip_safety(actor)
    if reason is not None:
        raise SleepRefused(reason.value, rejection_message(reason) or "目前無法紮營。")
    try:
        commander = resolve_commander(actor)
    except PartyScopeError as error:
        raise SleepRefused(CODE_PARTY_UNAVAILABLE, REASON_NOT_CONTROLLING) from error
    enabled, message = _party_status(
        commander, actor=actor, mode=mode, seconds=duration
    )
    if not enabled:
        raise SleepRefused(CODE_PARTY_UNAVAILABLE, message or REASON_NOT_CONTROLLING)
    members = tuple(
        member
        for member in present_party_scope(commander)
        if not getattr(member, "_is_deleted", False)
    )
    tick = read_tick()
    entry = plan_party_entry(members, mode, duration, tick=tick)
    return {
        "commander": commander,
        "members": members,
        "tick": tick,
        "duration": duration,
        "entry": entry,
    }


def _owner_can_opt_in(actor: Any, commander: Any, planned: tuple[Any, ...]) -> bool:
    """Whether a ``dream: true`` request would be accepted now.

    The requester must be the authenticated owner itself (never a possessed
    companion), with no possession binding, selected for a new voluntary
    receipt under this mode.
    """
    from typeclasses.characters import PlayerCharacter
    from world.rules.possession import current_possession

    if actor is not commander or not isinstance(commander, PlayerCharacter):
        return False
    if current_possession(commander) is not None:
        return False
    if getattr(getattr(commander, "db", None), "possessed_by", None) is not None:
        return False
    return any(member is commander for member in planned)


def _predict_reserve(state: FatigueState, wake_tick: int, tick: int, endpoint: int) -> int:
    """Predict one body's reserve at ``endpoint`` with the canonical policy.

    The body sleeps until its own accepted wake target, then spends awake
    reserve until the camp endpoint. Each segment advances through
    ``predict_interval`` boundary by boundary, so a threshold, a depletion
    into forced sleep or a forced natural wake follow the same rules the
    settlement applies.
    """
    cursor = int(tick)
    current = state
    wake = int(wake_tick)
    for _ in range(_PREDICTION_STEPS):
        if cursor >= endpoint:
            break
        if current.posture is SleepPosture.VOLUNTARY and cursor < wake:
            seconds = min(wake, endpoint) - cursor
            prediction = predict_interval(current, FatigueActivity.SLEEP, seconds)
            step = seconds
            end = prediction.end
            if cursor + step >= wake:
                # The accepted target wakes the voluntary sleeper.
                end = FatigueState(end.reserve_units, SleepPosture.AWAKE)
        elif current.posture is SleepPosture.FORCED:
            prediction = predict_interval(
                current, FatigueActivity.SLEEP, endpoint - cursor
            )
            if prediction.applicable_seconds == 0 and prediction.end.posture is SleepPosture.AWAKE:
                # Already at the natural wake threshold: it wakes at once.
                current = FatigueState(current.reserve_units, SleepPosture.AWAKE)
                continue
            step = prediction.applicable_seconds or (endpoint - cursor)
            if step < endpoint - cursor:
                prediction = predict_interval(current, FatigueActivity.SLEEP, step)
            end = prediction.end
        else:
            awake = FatigueState(current.reserve_units, SleepPosture.AWAKE)
            prediction = predict_interval(
                awake, FatigueActivity.AWAKE, endpoint - cursor
            )
            step = prediction.applicable_seconds or (endpoint - cursor)
            if step < endpoint - cursor:
                prediction = predict_interval(awake, FatigueActivity.AWAKE, step)
            end = prediction.end
        cursor += step
        current = end
    else:
        if cursor < endpoint:
            from world.observability import log_warn

            log_warn(
                "camp_prediction_bound",
                context={"tick": int(tick), "endpoint": int(endpoint), "cursor": int(cursor)},
            )
    return int(current.reserve_units)


def plan_camp(actor: Any, *, mode: str, seconds: int | None = None) -> dict[str, Any]:
    """Project one camp mode without writing anything.

    Returns ``{owner, members, mode, entry_tick, target_tick, targets,
    dream_offerable, rows}``: ``targets`` holds one entry per selected
    sleeper (new voluntary entries and existing accepted plans alike) with
    ``{member, mode, target_tick, accepted_seconds, existing}``; the endpoint
    ``target_tick`` is the latest of them (or the entry tick). ``rows`` are
    the per-member predictions at that endpoint. Refusals raise the shared
    ``SleepRefused`` of :func:`camp_preflight`. Entities stay internal.
    """
    gate = camp_preflight(actor, mode, seconds)
    commander = gate["commander"]
    tick = gate["tick"]
    entry = gate["entry"]
    targets: list[dict[str, Any]] = []
    own_wake: dict[int, int] = {}
    for member, accepted, _partial in entry.planned:
        target = tick + int(accepted)
        own_wake[id(member)] = target
        targets.append(
            {
                "member": member,
                "mode": mode,
                "target_tick": target,
                "accepted_seconds": int(accepted),
                "existing": False,
            }
        )
    for member, receipt in entry.existing:
        if receipt is not None and receipt.sleeping:
            target = int(recovery_target_tick(member, receipt, tick))
            receipt_mode = receipt.mode
            accepted = int(receipt.accepted_seconds)
        else:
            target = tick + int(forced_wake_seconds(member))
            receipt_mode = "forced_threshold"
            accepted = target - tick
        own_wake[id(member)] = target
        targets.append(
            {
                "member": member,
                "mode": receipt_mode,
                "target_tick": max(tick, target),
                "accepted_seconds": accepted,
                "existing": True,
            }
        )
    endpoint = max([tick] + [item["target_tick"] for item in targets])
    policy = get_policy()
    rows: list[dict[str, Any]] = []
    planned_ids = {id(member) for member, *_ in entry.planned}
    for member in gate["members"]:
        state = read_optional_fatigue_state(member)
        if state is None:
            continue
        if id(member) in planned_ids:
            # A new voluntary entry sleeps from the entry tick.
            state = FatigueState(state.reserve_units, SleepPosture.VOLUNTARY)
        wake = own_wake.get(id(member), tick)
        predicted = _predict_reserve(state, wake, tick, endpoint)
        rows.append(
            {
                "member": member,
                "current_reserve": int(state.reserve_units),
                "predicted_reserve": predicted,
                "reserve_max": int(policy.max_units),
                "current_percent": reserve_percent(
                    FatigueState(state.reserve_units, SleepPosture.AWAKE), policy
                ),
                "predicted_percent": reserve_percent(
                    FatigueState(predicted, SleepPosture.AWAKE), policy
                ),
                "wake_tick": wake,
            }
        )
    return {
        "owner": commander,
        "members": gate["members"],
        "mode": mode,
        "entry_tick": tick,
        "target_tick": endpoint,
        "targets": tuple(targets),
        "dream_offerable": _owner_can_opt_in(
            actor, commander, tuple(member for member, *_ in entry.planned)
        ),
        "rows": tuple(rows),
    }


def _name(member: Any) -> str:
    """A bounded, never-blank display name (the identity when keyless)."""
    name = str(getattr(member, "key", "") or "").strip()
    return (name or str(member.pk))[:_MAX_NAME]


def _refusal(error: Any) -> dict[str, str]:
    code = str(getattr(error, "code", None) or CODE_PARTY_UNAVAILABLE)[:64]
    message = str(getattr(error, "message", None) or "目前無法紮營。")[:512]
    return {"code": code, "message": message}


def _member_wire(row: dict[str, Any]) -> dict[str, Any]:
    member = row["member"]
    return {
        "member_id": str(member.pk)[:_MAX_MEMBER_ID],
        "name": _name(member),
        "current_reserve": row["current_reserve"],
        "predicted_reserve": row["predicted_reserve"],
        "reserve_max": row["reserve_max"],
        "current_percent": row["current_percent"],
        "predicted_percent": row["predicted_percent"],
        "wake_tick": row["wake_tick"],
        "wake_time": display_time(row["wake_tick"]),
    }


def preview_camp(actor: Any) -> dict[str, Any]:
    """The exact read-only ``explore.camp_preview`` result data.

    Both modes are always present, dawn first. A mode that refuses carries
    its stable refusal, a null wake and no members; the global refusal is the
    default mode's when no mode is available. Nothing is written: no clock,
    fatigue record, receipt, room or reveal state is created.
    """
    from world.rules.party_scope import PartyScopeError
    from world.rules.time_skip import SkipRefused, SleepRefused

    tick = read_tick()
    default = default_wire_mode(tick)
    modes: list[dict[str, Any]] = []
    refusals: dict[str, dict[str, str]] = {}
    for wire in WIRE_MODES:
        try:
            plan = plan_camp(actor, mode=internal_mode(wire))
        except (SleepRefused, SkipRefused, PartyScopeError) as error:  # observability: ignore R2: the stable refusal IS the preview's per-mode answer
            refusal = _refusal(error)
            refusals[wire] = refusal
            modes.append(
                {
                    "mode": wire,
                    "available": False,
                    "refusal": refusal,
                    "dream_offerable": False,
                    "wake_tick": None,
                    "wake_time": None,
                    "members": [],
                }
            )
            continue
        modes.append(
            {
                "mode": wire,
                "available": True,
                "refusal": None,
                "dream_offerable": bool(plan["dream_offerable"]),
                "wake_tick": plan["target_tick"],
                "wake_time": display_time(plan["target_tick"]),
                "members": [_member_wire(row) for row in plan["rows"]],
            }
        )
    available = any(item["available"] for item in modes)
    default_entry = next(item for item in modes if item["mode"] == default)
    return {
        "available": available,
        "refusal": None if available else refusals.get(default),
        "dream_offerable": bool(default_entry["dream_offerable"]),
        "default_mode": default,
        "current_tick": tick,
        "current_time": display_time(tick),
        "modes": modes,
    }


# -- atomic entry ------------------------------------------------------------

SCOPES = ("self", "party")
ANSWERS = (None, "enter", "decline")


def _require_opt_in(actor: Any, commander: Any, mode: str, seconds: int | None) -> None:
    """Refuse ``dream: true`` unless the owner would enter a new voluntary sleep."""
    from world.rules.time_skip import SleepRefused, _accepted_sleep_seconds

    planned = ()
    state = read_optional_fatigue_state(commander)
    if state is not None and state.posture is SleepPosture.AWAKE:
        accepted, _partial = _accepted_sleep_seconds(
            commander, mode, seconds, tick=read_tick()
        )
        if accepted > 0:
            planned = (commander,)
    if not _owner_can_opt_in(actor, commander, planned):
        raise SleepRefused(CODE_DREAM_NOT_OFFERABLE, DREAM_NOT_OFFERABLE_MESSAGE)


def _unique(bodies: Any) -> tuple[Any, ...]:
    seen: dict[int, Any] = {}
    for body in bodies:
        if body is not None and id(body) not in seen:
            seen[id(body)] = body
    return tuple(seen.values())


def _entry_result(commander: Any, outcome: Any, *, dream_entered: bool) -> dict[str, Any]:
    from world.rules.sleep_receipt import read_sleep_receipt, read_sleep_view_generation

    entries = tuple(getattr(outcome, "entries", ()) or ())
    if not entries and getattr(outcome, "entry", None) is not None:
        entries = (outcome.entry,)
    try:
        receipt = read_sleep_receipt(commander)
    except Exception:  # observability: ignore R2: a corrupt owner receipt simply names no owner sleep in this read-only summary
        receipt = None
    return {
        "owner": commander,
        "outcome": outcome,
        "members": tuple(entry.member for entry in entries),
        "owner_sleep_id": receipt.sleep_id if receipt is not None and receipt.sleeping else None,
        "generation": read_sleep_view_generation(commander),
        "dream_entered": dream_entered,
    }


def commit_sleep_entry(
    actor: Any,
    *,
    scope: str,
    mode: str,
    seconds: int | None,
    answer: str | None,
    operation_id: str,
    session: Any = None,
) -> dict[str, Any]:
    """Commit one accepted sleep entry and its optional owner dream answer.

    ``scope`` is exactly ``self`` (the existing self entry; companions are
    untouched) or ``party`` (``begin_all_party_sleep``). ``answer`` is
    ``None`` (ordinary false/absent: no answer, the question policy is
    unchanged), ``enter`` (explicit opt-in, validated before any write and
    again under the lock) or ``decline`` (the camp's explicit decline,
    recorded only when an owner sleeping receipt exists). Entry and answer
    commit together or not at all. Returns ``{owner, outcome, members,
    owner_sleep_id, generation, dream_entered}``.
    """
    return _commit_entry(
        actor,
        scope=scope,
        mode=mode,
        seconds=seconds,
        answer=answer,
        operation_id=operation_id,
        session=session,
    )


def _commit_entry(
    actor: Any,
    *,
    scope: str,
    mode: str,
    seconds: int | None,
    answer: str | None,
    operation_id: str,
    session: Any = None,
    camp: Any = None,
) -> dict[str, Any]:
    from django.db import transaction

    from server.dream_service import answer_sleep_dream
    from world.narrative.dream_surface import reset_cache
    from world.rules.party_scope import present_party_scope, resolve_commander
    from world.rules.possession import (
        _restore_owner_control,
        _snapshot_owner_control,
        restore_party_control,
        snapshot_party_control,
    )
    from world.rules.sleep_control import begin_all_party_sleep
    from world.rules.sleep_receipt import (
        KIND_VOLUNTARY,
        read_sleep_receipt,
        read_sleep_view_generation,
        write_camp_operation,
    )
    from world.rules.surfaces import attribute_snapshot, restore_attribute_best_effort
    from world.rules.time_skip import (
        INVALID_SLEEP_MODE_MESSAGE,
        SleepOutcome,
        SleepRefused,
        _lock_members,
        _restore_sleep_surfaces,
        _sleep_surface_snapshot,
        begin_sleep,
        enter_sleep,
    )

    if scope not in SCOPES:
        raise SleepRefused("invalid_scope", INVALID_SLEEP_MODE_MESSAGE)
    if answer not in ANSWERS:
        raise SleepRefused("invalid_decision", INVALID_SLEEP_MODE_MESSAGE)
    commander = resolve_commander(actor)
    if answer is None and camp is None:
        # Ordinary false/absent: the existing entries, unchanged.
        if scope == "self":
            outcome = begin_sleep(
                actor,
                mode=mode,
                seconds=seconds,
                scope="self",
                operation_id=operation_id,
                allow_continue=False,
            )
        else:
            outcome = begin_all_party_sleep(
                actor,
                mode=mode,
                seconds=seconds,
                session=session,
                operation_id=operation_id,
            )
        return _entry_result(commander, outcome, dream_entered=False)

    if answer == "enter":
        _require_opt_in(actor, commander, mode, seconds)
    if camp is not None:
        camp_preflight(actor, mode, seconds)
    possessed = actor is not commander
    bodies = _unique((commander, actor, *present_party_scope(commander)))
    snapshots = [(body, _sleep_surface_snapshot(body)) for body in bodies]
    dream_before = attribute_snapshot(commander, "dream_surface")
    control_before = snapshot_party_control(commander, actor) if possessed else None
    owner_before = _snapshot_owner_control(commander) if possessed else None
    dream_entered = False
    try:
        with transaction.atomic():
            _lock_members(bodies)
            gate = camp_preflight(actor, mode, seconds) if camp is not None else None
            if answer == "enter":
                _require_opt_in(actor, commander, mode, seconds)
            if scope == "self":
                entry = enter_sleep(
                    actor, operation_id=operation_id, mode=mode, seconds=seconds
                )
                outcome = SleepOutcome(
                    entry,
                    None,
                    None,
                    entries=(entry,) if entry.receipt is not None else (),
                    receipts=(entry.receipt,) if entry.receipt is not None else (),
                )
            else:
                outcome = begin_all_party_sleep(
                    actor,
                    mode=mode,
                    seconds=seconds,
                    session=session,
                    operation_id=operation_id,
                )
            receipt = read_sleep_receipt(commander)
            sleeping = receipt is not None and receipt.sleeping
            if answer == "enter":
                if not (
                    sleeping
                    and receipt.kind == KIND_VOLUNTARY
                    and receipt.entry_operation_id == operation_id
                ):
                    raise SleepRefused(
                        CODE_DREAM_NOT_OFFERABLE, DREAM_NOT_OFFERABLE_MESSAGE
                    )
            if answer is not None and sleeping:
                # The guarded answer, as the authenticated owner, against the
                # receipt and view generation this very entry committed.
                answered = answer_sleep_dream(
                    commander,
                    decision=answer,
                    sleep_id=receipt.sleep_id,
                    revision=receipt.revision,
                    generation=read_sleep_view_generation(commander),
                    session=session if answer == "enter" else None,
                    defer_continuation=True,
                )
                if answered.get("outcome") != "success":
                    raise SleepRefused(
                        str(answered.get("code") or "dream_refused"),
                        str(answered.get("message") or DREAM_NOT_OFFERABLE_MESSAGE),
                    )
                dream_entered = answer == "enter"
            if camp is not None:
                write_camp_operation(
                    commander,
                    camp(commander=commander, gate=gate, receipt=receipt if sleeping else None),
                )
    except Exception:
        # The outer transaction rolled the durable rows back; the Attribute
        # caches, the dream association and the non-transactional control
        # effects are restored here, physiology first and control last.
        for body, body_snapshots in snapshots:
            _restore_sleep_surfaces(body, body_snapshots)
        restore_attribute_best_effort(commander, "dream_surface", dream_before)
        if possessed and control_before is not None:
            if owner_before is not None:
                _restore_owner_control(commander, owner_before)
            restore_party_control(commander, actor, control_before)
        reset_cache(commander)
        raise
    return _entry_result(commander, outcome, dream_entered=dream_entered)


# -- durable camp progress -----------------------------------------------------

_INTERVAL_BOUND = 64

REASON_TEXT = {
    "interactive_event": "途中發生了需要留意的事",
    "in_combat": "隊伍陷入了戰鬥",
    "hostile_present": "附近出現了敵人",
    "stale_sleep": "睡眠的狀態已經改變",
    "not_sleeping": "有成員已不在睡眠中",
    "control_changed": "控制權已經改變",
    "interval_bound": "睡眠尚未結束，可再繼續睡眠",
    "no_progress": "睡眠尚未結束，可再繼續睡眠",
    "event_bound": "途中事件過多，先行停下",
    "member_absent": "有成員已不在營地",
    "continuation_failed": "睡眠被打斷，可稍後繼續",
    "dream_interrupted": "夢醒後的睡眠被打斷",
}


class CampStorageFull(SleepRefused):
    """One interval's due events would exceed the camp's durable event bound.

    A ``SleepRefused`` so every interval owner (the camp loop, the owner
    dream-departure continuation) stops on it as an ordinary pause.
    """

    def __init__(self) -> None:
        super().__init__("event_bound", "途中事件過多，先行停下。")


def _event_text(event: Any) -> str | None:
    from world.rules.unlock_notices import PRACTICE_UNLOCK_EVENT

    kind = getattr(event, "kind", None)
    if kind == "daily_reset":
        return "新的一天開始了。"
    if kind == PRACTICE_UNLOCK_EVENT:
        line = (getattr(event, "payload", None) or {}).get("line")
        return str(line)[:_MAX_NAME] if line else None
    return None


def serialize_due_event(event: Any) -> dict[str, Any]:
    """The bounded wire form of one committed due event."""
    kind = str(getattr(event, "kind", "event"))
    if not kind.isascii():
        kind = "event"
    return {
        "kind": kind[:64],
        "due_tick": max(0, int(getattr(event, "due_tick", 0) or 0)),
        "interactive": bool(getattr(event, "interactive", False)),
        "text": _event_text(event),
    }


def record_camp_interval(actor: Any, result: Any, events: Any) -> None:
    """Record one committed interval into the owner's pending camp.

    Called inside ``time_skip.continue_sleep``'s interval transaction, after
    the interval result is built: the elapsed cursor and the full bounded
    due-event facts commit (or roll back) with the interval itself. It is a
    no-op unless the actor is the authenticated owner of a pending camp whose
    selected targets include the interval's sleep identity, so ordinary sleep
    continuation is unaffected. Facts are never dropped: an interval whose
    events would exceed the bound raises :class:`CampStorageFull` and rolls
    back.
    """
    from world.rules.party_scope import PartyScopeError, resolve_commander
    from world.rules.sleep_receipt import (
        CAMP_STATUS_PENDING,
        MAX_CAMP_EVENTS,
        read_camp_operation,
        write_camp_operation,
    )

    try:
        commander = resolve_commander(actor)
    except PartyScopeError:  # observability: ignore R2: a non-player body owns no camp
        return
    if commander is not actor:
        return
    meta = read_camp_operation(commander)
    if meta is None or meta["result"] is not None:
        return
    progress = meta["progress"]
    if progress["status"] != CAMP_STATUS_PENDING:
        return
    sleep_ids = {row["sleep_id"] for row in meta["targets"]}
    if str(result.get("sleep_id")) not in sleep_ids:
        return
    facts = [serialize_due_event(event) for event in events or ()]
    if len(progress["events"]) + len(facts) > MAX_CAMP_EVENTS:
        raise CampStorageFull()
    progress["events"].extend(facts)
    progress["elapsed_seconds"] += int(result.get("elapsed_seconds", 0))
    progress["interval_index"] += 1
    write_camp_operation(commander, meta)


def _body(member_id: str) -> Any:
    from evennia.objects.models import ObjectDB

    try:
        return ObjectDB.objects.filter(pk=int(member_id)).first()
    except (TypeError, ValueError):  # observability: ignore R2: a malformed stored id resolves no body
        return None


def _next_target(commander: Any, meta: dict[str, Any]) -> tuple[Any, Any, str | None]:
    """The still-sleeping selected sleeper with the latest retained target.

    Returns ``(member, receipt, None)``, ``(None, None, None)`` when every
    selected plan has woken, or ``(None, None, reason)`` when a still-sleeping
    selected body left the camp.
    """
    from world.rules.party_scope import present_party_scope
    from world.rules.sleep_receipt import read_sleep_receipt

    present = {int(member.pk): member for member in present_party_scope(commander)}
    best = None
    for row in meta["targets"]:
        member = present.get(int(row["member_id"])) if row["member_id"].isdigit() else None
        body = member or _body(row["member_id"])
        if body is None:
            continue
        try:
            receipt = read_sleep_receipt(body)
        except Exception:  # observability: ignore R2: a corrupt receipt is not this camp's plan any more; finalization reports it unfinished
            continue
        if receipt is None or receipt.sleep_id != row["sleep_id"] or not receipt.sleeping:
            continue
        if member is None:
            return None, None, "member_absent"
        key = (int(receipt.target_tick), -int(member.pk))
        if best is None or key > best[0]:
            best = (key, member, receipt)
    if best is None:
        return None, None, None
    return best[1], best[2], None


def continue_camp(actor: Any, *, camp_id: str) -> dict[str, Any]:
    """Continue the camp's selected accepted plans, then finalize it.

    The authenticated owner remains the acting body for every interval; the
    entry names the selected sleeper with the latest retained target, so a
    full awake owner needs no receipt of its own. Each interval is the
    existing ``continue_sleep`` boundary, truncated at the earliest wake,
    event or safety boundary of the whole present party. A real interaction,
    the safety gate, a stale receipt, no progress or the interval bound
    stops it with an explicit interruption reason; the safe prefix stays
    committed.
    """
    from world.rules.party_scope import resolve_commander
    from world.rules.sleep_receipt import read_camp_operation
    from world.rules.time_skip import (
        SkipRefused,
        SleepEntry,
        SleepRefused,
        _party_progress_signature,
        continue_sleep,
    )

    commander = resolve_commander(actor)
    meta = read_camp_operation(commander)
    if meta is None or meta["camp_id"] != camp_id:
        raise SleepRefused("stale_sleep", "這次紮營已經更新，請重新查看。")
    if meta["result"] is not None or meta["progress"]["status"] != "pending":
        return finalize_camp(commander)
    reason = None
    for _ in range(_INTERVAL_BOUND):
        meta = read_camp_operation(commander)
        if meta is None:
            break
        member, receipt, absent = _next_target(commander, meta)
        if absent is not None:
            reason = absent
            break
        if member is None:
            break
        index = int(meta["progress"]["interval_index"])
        before = _party_progress_signature(commander)
        tick_before = read_tick()
        try:
            interval = continue_sleep(
                commander,
                SleepEntry(
                    operation_id=f"{camp_id}:{index}",
                    member=member,
                    requested_seconds=0,
                    handoff_offered=False,
                ),
                operation_id=f"{camp_id}:{index}",
                expected_sleep_id=receipt.sleep_id,
                expected_revision=receipt.revision,
            )
        except SkipRefused as error:  # observability: ignore R2: the stable safety refusal IS the camp's interruption reason
            reason = str(error.reason.value)
            break
        except CampStorageFull:  # observability: ignore R2: the bounded storage stop IS the camp's interruption reason
            reason = "event_bound"
            break
        except SleepRefused as error:  # observability: ignore R2: the stable sleep refusal IS the camp's interruption reason
            reason = "stale_sleep" if error.code == "stale_sleep" else "not_sleeping"
            break
        if interval.interrupted:
            follow, _receipt, _absent = _next_target(commander, read_camp_operation(commander) or meta)
            if follow is not None:
                reason = "interactive_event"
                break
        if (
            interval.elapsed_seconds <= 0
            and read_tick() == tick_before
            and _party_progress_signature(commander) == before
        ):
            reason = "no_progress"
            break
    else:
        reason = "interval_bound"
    return finalize_camp(commander, reason=reason)


def _wake_of(body: Any, sleep_id: str) -> tuple[bool, int | None]:
    """``(still sleeping, actual wake tick)`` of one selected plan."""
    from world.rules.sleep_receipt import STATE_COMPLETED, read_sleep_receipt

    try:
        receipt = read_sleep_receipt(body) if body is not None else None
    except Exception:  # observability: ignore R2: an unreadable receipt reports the plan as unfinished
        return False, None
    if receipt is None or receipt.sleep_id != sleep_id:
        return False, None
    if receipt.sleeping:
        return True, None
    if receipt.state == STATE_COMPLETED:
        return False, int(receipt.settled_through_tick)
    return False, None


def _summary(result: dict[str, Any], reason: str | None, mode: str | None = None) -> str:
    if result["phase"] == "complete":
        lowest = min(
            (member["after_percent"] for member in result["members"]),
            default=100,
        )
        quiet = not any(event["interactive"] for event in result["events"])
        # Only a camp to dawn spent the night.
        prefix = "夜裡無事。" if quiet and mode == MODE_UNTIL_DAWN else ""
        text = (
            f"{prefix}全隊精力恢復至 {lowest}%，"
            f"{result['timing']['wake_time']} 醒來。"
        )
    else:
        cause = REASON_TEXT.get(reason or "", REASON_TEXT["continuation_failed"])
        text = f"紮營在{result['timing']['result_time']}中斷：{cause}。"
    return text[:_MAX_NAME]


def _result_data(commander: Any, meta: dict[str, Any], *, phase: str, reason: str | None) -> dict[str, Any]:
    """Build the exact wire camp result from durable progress and receipts."""
    targets = {row["member_id"]: row for row in meta["targets"]}
    members = []
    wake_ticks = []
    for row in meta["before"]:
        body = _body(row["member_id"])
        state = read_optional_fatigue_state(body) if body is not None else None
        after = int(state.reserve_units) if state is not None else int(row["reserve"])
        reserve_max = int(row["reserve_max"]) or 1
        target = targets.get(row["member_id"])
        sleeping = bool(
            state is not None and state.posture in (SleepPosture.VOLUNTARY, SleepPosture.FORCED)
        )
        wake_tick = None
        if target is not None and phase != "dream":
            _still, wake_tick = _wake_of(body, target["sleep_id"])
            if wake_tick is not None:
                wake_ticks.append(wake_tick)
        members.append(
            {
                "member_id": row["member_id"],
                "name": row["name"],
                "reserve_before": int(row["reserve"]),
                "reserve_after": max(0, min(after, reserve_max)),
                "reserve_max": reserve_max,
                "before_percent": int(row["percent"]),
                "after_percent": reserve_percent(
                    FatigueState(max(0, min(after, reserve_max)), SleepPosture.AWAKE)
                ),
                "sleeping": sleeping,
                "wake_tick": wake_tick,
            }
        )
    tick = read_tick()
    complete = phase == "complete"
    wake = max(wake_ticks) if complete and wake_ticks else (tick if complete else None)
    elapsed = 0 if phase == "dream" else int(meta["progress"]["elapsed_seconds"])
    return {
        "camp_id": meta["camp_id"],
        "phase": phase,
        "timing": {
            "elapsed_seconds": elapsed,
            "result_tick": tick,
            "result_time": display_time(tick),
            "wake_tick": wake,
            "wake_time": display_time(wake) if wake is not None else None,
        },
        "members": members,
        "events": [] if phase == "dream" else list(meta["progress"]["events"]),
        "interrupted": phase == "interrupted",
        "interruption_reason": reason if phase == "interrupted" else None,
    }


def dream_result(commander: Any) -> dict[str, Any] | None:
    """The pending zero-elapsed result of a camp that entered the dream."""
    from world.rules.sleep_receipt import read_camp_operation

    meta = read_camp_operation(commander)
    if meta is None:
        return None
    return _result_data(commander, meta, phase="dream", reason=None)


def _deliver(commander: Any, event: dict[str, Any]) -> None:
    """Hand the stored camp_result fact to the travel log on commit.

    The identity was assigned once, at finalization; a replay or reconnect
    redelivers the very same fact id, which the travel log deduplicates.
    """
    from types import MappingProxyType

    from world.rules.presentation_events import (
        current_publication_group,
        new_publication_group,
        on_publication_commit,
        publication_group,
    )
    from world.rules.travel_events import TravelEvent, TravelLogFact, emit_travel_fact

    actor_id = getattr(commander, "pk", None)
    if isinstance(actor_id, bool) or not isinstance(actor_id, int):
        return
    with publication_group():
        group = current_publication_group() or new_publication_group()
        travel_event = TravelEvent(
            id=event["id"],
            kind=event["kind"],
            params=MappingProxyType(dict(event["params"])),
            text=event["text"],
            tick=int(event["tick"]),
            day=int(event["day"]),
            time=event["time"],
        )
        fact = TravelLogFact(
            actor_id=actor_id,
            group_id=group.id,
            fact_id=event["id"].rsplit(".", 1)[0],
            events=(travel_event,),
        )
        on_publication_commit(lambda: emit_travel_fact(fact))


def finalize_camp(actor: Any, *, reason: str | None = None) -> dict[str, Any] | None:
    """Store (once) and publish (once per delivery) the camp's final result.

    The result is rebuilt only from durable progress and the current selected
    receipts, under the owner/party locks: every selected plan woke ->
    ``complete``; otherwise ``interrupted`` with the stable reason. The
    complete result and one stable travel fact are stored before commit; an
    already-finalized camp returns its stored result and redelivers the same
    fact without settling anything.
    """
    from django.db import transaction

    from world.observability import log_info
    from world.rules.party_scope import present_party_scope, resolve_commander
    from world.rules.sleep_receipt import (
        CAMP_STATUS_COMPLETE,
        CAMP_STATUS_PAUSED,
        read_camp_operation,
        write_camp_operation,
    )
    from world.rules.time_skip import _lock_members
    from world.rules.travel_events import day_and_time

    commander = resolve_commander(actor)
    meta = read_camp_operation(commander)
    if meta is None:
        return None
    if meta["result"] is not None:
        if meta["event"] is not None:
            _deliver(commander, meta["event"])
        return meta["result"]
    with transaction.atomic():
        _lock_members(_unique((commander, *present_party_scope(commander))))
        meta = read_camp_operation(commander)
        if meta is None:
            return None
        if meta["result"] is not None:
            return meta["result"]
        unfinished = any(
            _wake_of(_body(row["member_id"]), row["sleep_id"])[1] is None
            for row in meta["targets"]
        )
        phase = "interrupted" if unfinished else "complete"
        if phase == "interrupted" and reason is None:
            reason = "continuation_failed"
        result = _result_data(commander, meta, phase=phase, reason=reason)
        summary = _summary(result, reason, meta["mode"])
        tick = int(result["timing"]["result_tick"])
        day, clock_text = day_and_time(tick)
        event = {
            "id": f"camp:{meta['camp_id']}.0"[:80],
            "kind": "camp_result",
            "tick": tick,
            "day": day,
            "time": clock_text,
            "text": summary,
            "params": {"summary": summary},
        }
        meta["result"] = result
        meta["event"] = event
        meta["progress"]["status"] = (
            CAMP_STATUS_COMPLETE if phase == "complete" else CAMP_STATUS_PAUSED
        )
        write_camp_operation(commander, meta)
        _deliver(commander, event)
    location = getattr(commander, "location", None)
    log_info(
        "camp_result",
        context={
            "char": int(commander.pk),
            "room": getattr(location, "pk", None),
            "tick": tick,
            "camp_id": meta["camp_id"],
            "mode": meta["mode"],
            "dream": meta["dream"],
            "elapsed": result["timing"]["elapsed_seconds"],
            "interrupted": result["interrupted"],
            "reason": result["interruption_reason"],
        },
    )
    return result


def reconcile_camp(owner: Any) -> dict[str, Any] | None:
    """Resume or finalize a pending camp after a dream departure or reconnect.

    Runs after the ordinary owner continuation (even when that returned
    early). A camp still in its dream, or whose owner continuation is still
    pending, waits; a paused owner continuation finalizes the camp as
    interrupted; otherwise the remaining selected sleepers continue under the
    camp's retained authorization. Paused or complete camps never run again.
    """
    from world.narrative import dream_session as lifecycle
    from world.narrative.dream_surface import associated_session
    from world.observability import log_warn
    from world.rules.sleep_receipt import (
        CONTINUATION_PAUSED,
        CONTINUATION_PENDING,
        read_camp_operation,
        read_sleep_receipt,
        read_sleep_view_decision,
    )

    try:
        meta = read_camp_operation(owner)
        if meta is None:
            return None
        if meta["result"] is not None:
            return None
        if meta["progress"]["status"] != "pending":
            return None
        if meta["dream"]:
            session = associated_session(owner)
            if session is not None and session.state == lifecycle.STATE_OPEN:
                return None
            receipt = read_sleep_receipt(owner)
            decision = read_sleep_view_decision(owner)
            if receipt is not None and receipt.sleeping and decision is not None:
                if decision["continuation"] == CONTINUATION_PENDING:
                    return None
                if decision["continuation"] == CONTINUATION_PAUSED:
                    return finalize_camp(owner, reason="dream_interrupted")
        return continue_camp(owner, camp_id=meta["camp_id"])
    except Exception as error:
        log_warn(
            "camp_reconcile_failed",
            context={"char": str(getattr(owner, "pk", "?"))},
            exc=error,
        )
        return None


def camp_metadata(*, camp_id: str, mode: str, dream: bool):
    """Build the camp metadata writer used inside the entry transaction."""
    from world.rules.sleep_receipt import CAMP_STATUS_PENDING, read_sleep_receipt

    def build(*, commander: Any, gate: dict[str, Any], receipt: Any) -> dict[str, Any]:
        policy = get_policy()
        before = []
        targets = []
        for member in gate["members"]:
            state = read_optional_fatigue_state(member)
            if state is None:
                continue
            before.append(
                {
                    "member_id": str(member.pk),
                    "name": _name(member),
                    "reserve": int(state.reserve_units),
                    "reserve_max": int(policy.max_units),
                    "percent": reserve_percent(
                        FatigueState(state.reserve_units, SleepPosture.AWAKE), policy
                    ),
                }
            )
            member_receipt = read_sleep_receipt(member)
            if member_receipt is not None and member_receipt.sleeping:
                targets.append(
                    {
                        "member_id": str(member.pk),
                        "sleep_id": member_receipt.sleep_id,
                        "target_tick": int(member_receipt.target_tick),
                    }
                )
        return {
            "camp_id": camp_id,
            "owner_sleep_id": receipt.sleep_id if receipt is not None else None,
            "mode": mode,
            "dream": bool(dream),
            "entry_tick": int(gate["tick"]),
            "before": before,
            "targets": targets,
            "progress": {
                "elapsed_seconds": 0,
                "interval_index": 0,
                "events": [],
                "status": CAMP_STATUS_PENDING,
            },
            "result": None,
            "event": None,
        }

    return build


__all__ = [
    "CampStorageFull",
    "CODE_DREAM_NOT_OFFERABLE",
    "CODE_PARTY_UNAVAILABLE",
    "WIRE_DAWN",
    "WIRE_MODES",
    "WIRE_RECOVERED",
    "camp_metadata",
    "camp_preflight",
    "commit_sleep_entry",
    "continue_camp",
    "dream_result",
    "finalize_camp",
    "reconcile_camp",
    "record_camp_interval",
    "serialize_due_event",
    "default_wire_mode",
    "display_time",
    "internal_mode",
    "plan_camp",
    "preview_camp",
    "wire_mode",
]
