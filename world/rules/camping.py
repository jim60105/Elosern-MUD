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


def _refusal(error: Any) -> dict[str, str]:
    code = str(getattr(error, "code", None) or CODE_PARTY_UNAVAILABLE)[:64]
    message = str(getattr(error, "message", None) or "目前無法紮營。")[:512]
    return {"code": code, "message": message}


def _member_wire(row: dict[str, Any]) -> dict[str, Any]:
    member = row["member"]
    return {
        "member_id": str(member.pk)[:_MAX_MEMBER_ID],
        "name": str(getattr(member, "key", member.pk))[:_MAX_NAME],
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


__all__ = [
    "CODE_DREAM_NOT_OFFERABLE",
    "CODE_PARTY_UNAVAILABLE",
    "WIRE_DAWN",
    "WIRE_MODES",
    "WIRE_RECOVERED",
    "camp_preflight",
    "default_wire_mode",
    "display_time",
    "internal_mode",
    "plan_camp",
    "preview_camp",
    "wire_mode",
]
