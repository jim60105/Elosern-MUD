"""Shared deterministic time-skip helper (webclient-exploration-menu D7).

The ``rest``/``sleep``/``wait`` commands and the WebClient ``explore.wait``
adapter share one helper so duration parsing, the bounded full-regen
computation, the safety gate, and clock advancement can never diverge. This
module owns the ``clock.yaml`` bounds, the ``evaluate_skip_safety`` gate, and
the ``AdvanceSource.SKIP`` execution; callers never advance time themselves.

``rest`` caps its parsed duration at ``MAX_SKIP_SECONDS``
(``CLOCK_YAML["max_sleep_seconds"]``), the same bound ``sleep`` uses for its
computed full-regen duration. The WebClient ``explore.wait`` ``seconds``
payload is bounded by the documented protocol-level ``MAX_WEB_SKIP_SECONDS``,
which equals ``MAX_SKIP_SECONDS``; none of the bounds change command behavior
beyond the configured maximum.
"""

import math
import re
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any
from uuid import uuid4

from django.db import transaction

from world.observability import log_info, log_warn
from world.rules.clock import (
    AdvanceSource,
    CLOCK_YAML,
    ScheduledEvent,
    _restore_advance_registry,
    _restore_clock_tick,
    _snapshot_clock_tick,
    build_advance_snapshot_registry,
    get_world_clock,
)
from world.rules.fatigue import (
    FATIGUE_ATTRIBUTE_SURFACES,
    FatigueActivity,
    SleepPosture,
    get_policy,
    project_fatigue_status,
    read_optional_fatigue_state,
    sleep_blocks_actions,
    write_fatigue_state,
)
from world.rules.mental_time import (
    plan_for,
    planned_seconds,
)
from world.rules.party_scope import (
    PURPOSE_ACT,
    PartyScopeError,
    authorize_member,
    party_in_combat,
    present_party_scope,
    resolve_commander,
)
from world.rules.progression import proficiency_cap, skill_proficiency_level
from world.rules.skip_safety import SkipRejectReason, evaluate_skip_safety
from world.rules.surfaces import (
    attribute_snapshot,
    restore_attribute_best_effort,
)
from world.rules.traits import GAUGE_KEYS
from world.rules.unlock_notices import PRACTICE_UNLOCK_EVENT
from world.skills.registry import SKILL_REGISTRY, SkillKind


class DurationParseError(ValueError):
    """Raised for an explicit rest duration with unsupported syntax."""


class SkipRefused(RuntimeError):
    """One accepted-operation admission was refused by the shared safety gate."""

    def __init__(self, reason: SkipRejectReason) -> None:
        super().__init__(reason.value)
        self.reason = reason


class SleepRefused(RuntimeError):
    """One voluntary sleep entry or continuation is not eligible."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(code)
        self.code = code
        self.message = message


ALREADY_ASLEEP_MESSAGE = "你正在沉睡，無法重新入睡。"
NOT_SLEEPING_MESSAGE = "你並不在自願睡眠中。"
MISSING_PHYSIOLOGY_MESSAGE = "你的身心狀態尚未建立，無法入睡。"
FORCED_SLEEP_MESSAGE = "你正處於強制沉睡，無法主動入睡；可等待至甦醒。"
HANDOFF_OFFERED_MESSAGE = "你進入睡眠；可先交接控制權，再繼續恢復。"


def render_handoff_offer_message(candidates: Any) -> str:
    """Render the textual handoff choices: fatigue percent and return/possess."""
    from world.rules.possession import SLEEP_HANDOFF_RETURN

    parts: list[str] = []
    for candidate in candidates:
        fatigue = (
            ""
            if candidate.reserve_percent is None
            else f"（精神儲備 {candidate.reserve_percent}%）"
        )
        if candidate.kind == SLEEP_HANDOFF_RETURN:
            parts.append(f"回到自己的身體{fatigue}")
        else:
            parts.append(f"接手 {candidate.name}{fatigue}")
    if not parts:
        return HANDOFF_OFFERED_MESSAGE
    return f"{HANDOFF_OFFERED_MESSAGE}可交接：{'、'.join(parts)}。"


# The four named dayparts accepted by ``wait`` and ``explore.wait``.
DAYPARTS = ("midnight", "dawn", "noon", "dusk")

# Cap for explicit ``rest`` durations and the full-regen ``sleep`` duration.
MAX_SKIP_SECONDS = CLOCK_YAML["max_sleep_seconds"]

# Protocol-level bound for the WebClient ``explore.wait`` ``seconds`` value.
MAX_WEB_SKIP_SECONDS = MAX_SKIP_SECONDS

_DURATION_RE = re.compile(r"^(?P<amount>\d+)\s*(?P<unit>[smhd])$")
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}
_REJECTION_MESSAGES = {
    SkipRejectReason.IN_COMBAT: "你仍在戰鬥中，無法跳過時間。",
    SkipRejectReason.HOSTILE_PRESENT: "附近有活著的怪物，這裡不安全。",
}


class PracticeRejectReason(StrEnum):
    """Stable declared-practice booking rejection codes (D7)."""

    SKILL_UNKNOWN = "PRACTICE_SKILL_UNKNOWN"
    SKILL_CAPPED = "PRACTICE_SKILL_CAPPED"
    IN_COMBAT = "booking_in_combat"
    ASLEEP = "PRACTICE_ASLEEP"


@dataclass(frozen=True)
class PracticeReject:
    """One rejected practice booking: stable code plus player-facing text."""

    reason: PracticeRejectReason
    message: str


@dataclass(frozen=True)
class PracticeBooking:
    """One accepted standing practice booking: its member and confirmation."""

    member: Any
    skill_key: str
    message: str


@dataclass(frozen=True)
class SkipResult:
    """One immutable accepted player-driven skip receipt.

    ``requested_seconds`` is the explicit request limit, ``elapsed_seconds``
    the actual committed interval after the earliest relevant boundary, and
    the unperformed remainder is discarded. ``operation_id`` makes a retried
    receipt idempotent without replaying time.
    """

    operation_id: str
    requested_seconds: int
    elapsed_seconds: int
    events: tuple[ScheduledEvent, ...]
    fatigue_commits: tuple[Any, ...] = ()
    voluntary: bool = False
    woke: bool = False


@dataclass(frozen=True)
class SleepEntry:
    """One committed voluntary-sleep posture entry at zero elapsed time."""

    operation_id: str
    member: Any
    requested_seconds: int
    handoff_offered: bool
    handoff_candidates: tuple[Any, ...] = ()


@dataclass(frozen=True)
class SleepOutcome:
    """One explicit sleep request's accepted entry and/or committed result."""

    entry: SleepEntry | None
    result: SkipResult | None
    message: str | None = None


BOOKING_IN_COMBAT_MESSAGE = "戰鬥中無法排入修煉。"
_BOOKING_MESSAGE = "{member}將在下次休息時修煉「{skill}」。"

# A bounded in-process ledger of accepted results. A retried operation
# identity returns its recorded receipt instead of replaying elapsed time;
# a new explicit action always carries a new identity. The project has no
# durable skip-operation model, so this deliberately does not invent one.
_RESULT_LEDGER: dict[str, SkipResult] = {}
_LEDGER_LIMIT = 64


def _recorded(operation_id: str | None) -> SkipResult | None:
    if operation_id is None:
        return None
    return _RESULT_LEDGER.get(operation_id)


def _record(result: SkipResult) -> None:
    _RESULT_LEDGER[result.operation_id] = result
    while len(_RESULT_LEDGER) > _LEDGER_LIMIT:
        _RESULT_LEDGER.pop(next(iter(_RESULT_LEDGER)))


def preflight_practice_booking(
    actor: Any, skill_key: str
) -> PracticeReject | None:
    """Return the booking rejection for a declared-practice clause, or None.

    Checked BEFORE any clock advance (the skip never half-applies): the skill
    must be registered, ACTIVE (nothing practises a passive), owned, and not
    saturated at its derived tip cap (D6). Reasons are the stable codes
    ``PRACTICE_SKILL_UNKNOWN`` / ``PRACTICE_SKILL_CAPPED`` / ``PRACTICE_ASLEEP``.
    """
    from world.rules.fatigue import sleep_blocks_actions

    if sleep_blocks_actions(actor):
        return PracticeReject(
            PracticeRejectReason.ASLEEP,
            "你正在沉睡，無法排入修煉。",
        )
    skill = SKILL_REGISTRY.get(skill_key)
    if (
        skill is None
        or skill.kind is not SkillKind.ACTIVE
        or skill.key not in actor.skills.owned_keys()
    ):
        return PracticeReject(
            PracticeRejectReason.SKILL_UNKNOWN,
            f"你無法宣告修煉「{skill_key}」（{PracticeRejectReason.SKILL_UNKNOWN}）："
            "技能不存在、無法主動使用，或你尚未學會它。",
        )
    if skill_proficiency_level(actor, skill_key) >= proficiency_cap(skill_key):
        return PracticeReject(
            PracticeRejectReason.SKILL_CAPPED,
            f"「{skill.label}」的熟練度已見頂（{PracticeRejectReason.SKILL_CAPPED}），"
            "無需再宣告修煉。",
        )
    return None


def book_member_practice(
    acting: Any, member_id: Any, skill_key: str
) -> PracticeBooking | PracticeReject:
    """Book one present party member's standing practice; never advances time.

    The named member is re-derived through the party boundary for the acting
    purpose, so a forged, absent, or knocked-out id is refused (the exception
    propagates and each transport renders it) and the authenticated puppet is
    never substituted for it. An active combat session involving the acting
    figure, its commander, or the member refuses with ``booking_in_combat``;
    the skill then passes the same preflight the skip clause uses, against
    that member. Only ``db.practice_booking`` is written: the clock's practice
    stage stays the sole progression writer, and the standing booking is
    settled by the next SKIP advance that covers the member.
    """
    member = authorize_member(
        resolve_commander(acting), member_id, PURPOSE_ACT, anchor=acting
    )
    if party_in_combat(acting, member):
        return PracticeReject(
            PracticeRejectReason.IN_COMBAT, BOOKING_IN_COMBAT_MESSAGE
        )
    reject = preflight_practice_booking(member, skill_key)
    if reject is not None:
        return reject
    member.db.practice_booking = skill_key
    skill = SKILL_REGISTRY[skill_key]
    message = _BOOKING_MESSAGE.format(member=member.key, skill=skill.label)
    transaction.on_commit(
        lambda: log_info(
            "practice_booked",
            context={"member": int(member.pk), "skill": skill_key},
        )
    )
    return PracticeBooking(member, skill_key, message)


def parse_duration(text: str) -> int:
    """Parse an explicit ``<number><s|m|h|d>`` rest duration into seconds.

    The result is clamped to ``MAX_SKIP_SECONDS`` so ``rest`` can never drive
    an unbounded clock advance; durations at or under the cap parse exactly.
    """
    match = _DURATION_RE.fullmatch(text.strip())
    if match is None:
        raise DurationParseError("duration must use <number><s|m|h|d>")
    # Strip leading zeros before measuring the magnitude: Python refuses to
    # convert an absurdly long digit string, and any twelve-digit amount
    # already exceeds every configured cap in every unit, so the cap is exact.
    digits = match["amount"].lstrip("0") or "0"
    if len(digits) > 12:
        return MAX_SKIP_SECONDS
    return min(int(digits) * _UNIT_SECONDS[match["unit"]], MAX_SKIP_SECONDS)


def seconds_to_full_regen(entity: Any) -> int:
    """Return the bounded seconds to fully regenerate gauges and mental reserve.

    Voluntary sleep targets full HP/MP/SP and full reserve. The mental target
    is the ceiling of the exact remaining reserve divided by the authored
    sleep rate, so full gauges with a half-empty reserve still need 15,000
    seconds (180,000 units at 12 units per second) rather than zero.
    """
    seconds = 0
    for key in GAUGE_KEYS:
        gauge = getattr(entity.traits, key)
        rate = float(getattr(gauge, "rate", 0))
        if rate > 0 and gauge.value < gauge.max:
            seconds = max(seconds, math.ceil((gauge.max - gauge.value) / rate))
    state = read_optional_fatigue_state(entity)
    if state is not None:
        policy = get_policy()
        gap = max(0, policy.max_units - state.reserve_units)
        seconds = max(seconds, math.ceil(gap / policy.rates[FatigueActivity.SLEEP]))
    return min(seconds, CLOCK_YAML["max_sleep_seconds"])


def seconds_to_natural_wake(entity: Any) -> int | None:
    """Return a forced sleeper's bounded seconds to its natural wake, else None."""
    state = read_optional_fatigue_state(entity)
    if state is None or state.posture is not SleepPosture.FORCED:
        return None
    policy = get_policy()
    gap = max(0, policy.wake_units - state.reserve_units)
    return math.ceil(gap / policy.rates[FatigueActivity.SLEEP])


def render_skip_summary(seconds: int, events: list[ScheduledEvent]) -> str:
    """Render the stable skip summary from the settled events.

    A committed booked-study unlock rides the summary as its own line, so the
    commander reads the member's unlock exactly once, after the advance
    committed; the caller records the session marks from the same events.
    """
    message = f"時間經過了 {seconds} 秒。"
    if any(event.kind == "daily_reset" for event in events):
        message += " 新的一天開始了。"
    for event in events:
        if event.kind == PRACTICE_UNLOCK_EVENT:
            message += f" {event.payload['line']}"
    return message


def rejection_message(reason: SkipRejectReason) -> str | None:
    """Return the safe rejection message for one skip-safety reason."""
    return _REJECTION_MESSAGES.get(reason)


def unsafe_rejection(actor: Any) -> str | None:
    """Return the skip-safety rejection message when skipping is unsafe.

    Returns ``None`` when the actor may skip; otherwise the exact safe
    Traditional Chinese rejection for the current reason (active combat or a
    co-located living monster).
    """
    reason = evaluate_skip_safety(actor)
    if reason is None:
        return None
    return _REJECTION_MESSAGES[reason]


def advance_wait(
    actor: Any,
    seconds: int,
    *,
    practice_skill: str | None = None,
    operation_id: str | None = None,
) -> SkipResult:
    """Admit and settle one ordinary awake wait/rest/wait-until interval.

    The shared safety gate is rechecked here, once. The present party is
    resolved before any booking write, the request is truncated to the
    earliest relevant forced-sleep/wake/registered-event boundary, and one
    ``AdvanceSource.SKIP`` advance settles the actual elapsed interval. The
    unperformed remainder is discarded. A declared skill replaces the caller's
    standing booking before the advance; an unlabeled wait writes no booking
    and leaves every member's standing booking to the clock's practice stage,
    which settles only members whose sampled initial activity was awake.
    """
    recorded = _recorded(operation_id)
    if recorded is not None:
        return recorded
    if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds < 0:
        raise ValueError("seconds must be a non-negative integer")
    # The caller owns the request bound: explicit durations are parsed/capped,
    # the browser validates its protocol bound, and a daypart wait may legally
    # span up to one full game day (MAX_ADVANCE_SECONDS). Applying the
    # twelve-hour rest cap here would silently truncate a next-day daypart.
    limit = seconds
    reason = evaluate_skip_safety(actor)
    if reason is not None:
        raise SkipRefused(reason)
    entities = present_party_scope(actor)
    clock = get_world_clock()
    elapsed = planned_seconds(entities, limit, tick=clock.tick)
    commits: list[Any] = []
    mental = replace(plan_for(entities), record=commits)
    previous_booking = None
    if practice_skill is not None:
        previous_booking = actor.db.practice_booking
        actor.db.practice_booking = practice_skill
    try:
        events = clock.advance(elapsed, AdvanceSource.SKIP, entities, mental=mental)
    except Exception:
        # Clock rollback already restored its entry snapshot, which contains
        # this declaration; restoring the previous booking here keeps a failed
        # combined book-and-skip from leaving a declaration behind.
        if practice_skill is not None:
            actor.db.practice_booking = previous_booking
        raise
    result = SkipResult(
        operation_id=operation_id or uuid4().hex,
        requested_seconds=limit,
        elapsed_seconds=elapsed,
        events=tuple(events),
        fatigue_commits=tuple(commits),
    )
    _record(result)
    return result


def _sleep_member(actor: Any, member_id: int | None) -> Any:
    """Resolve the explicitly selected sleep body (default: the acting body)."""
    if member_id is None:
        return actor
    return authorize_member(
        resolve_commander(actor), member_id, PURPOSE_ACT, anchor=actor
    )


def _handoff_candidates(member: Any) -> tuple[Any, ...]:
    """Offer sleep-driven handoff choices after the commit, for the controlled body.

    Only the body a live session currently controls can hand control over: the
    owner body itself, or a possessed companion. An explicitly selected but
    uncontrolled companion, a stale possession flag, or a missing account
    yields no offer rather than an exception. Because this runs after the
    zero-time posture commit, a technical query failure must not turn an
    accepted sleep entry into a refusal: it is logged and reported as no offer.
    """
    try:
        commander = resolve_commander(member)
    except PartyScopeError:  # observability: ignore R2: a non-player-driven body simply has no controlling handoff candidate; this read writes nothing
        return ()
    from world.rules.possession import _resolve_account, begin_sleep_handoff

    # The unpuppeted owner body no longer reports a live ``account`` link; the
    # possession writer's canonical resolver reads the recorded account identity
    # instead of guessing from sessions.
    account = _resolve_account(commander, member)
    if account is None:
        return ()
    try:
        options = begin_sleep_handoff(account, commander, member)
    except Exception as error:  # observability: ignore R2: the committed sleep stays accepted; the failed offer is logged here and reports no candidates
        log_warn(
            "sleep_handoff_offer_failed",
            context={
                "char": str(getattr(commander, "pk", "?")),
                "member": str(getattr(member, "pk", "?")),
            },
            exc=error,
        )
        return ()
    return options.candidates


def enter_sleep(
    actor: Any, *, member_id: int | None = None, operation_id: str | None = None
) -> SleepEntry:
    """Commit one voluntary sleep posture at zero elapsed time.

    Only the explicitly selected body (default: the acting body) enters.
    Handoff candidates are reported, never transferred: the dependent
    control component owns the offer. A refusal commits neither posture nor
    time.
    """
    reason = evaluate_skip_safety(actor)
    if reason is not None:
        raise SkipRefused(reason)
    member = _sleep_member(actor, member_id)
    if sleep_blocks_actions(member):
        raise SleepRefused("already_asleep", ALREADY_ASLEEP_MESSAGE)
    state = read_optional_fatigue_state(member)
    if state is None:
        raise SleepRefused("missing_physiology", MISSING_PHYSIOLOGY_MESSAGE)
    requested = seconds_to_full_regen(member)
    snapshots = {
        (key, category): attribute_snapshot(member, key, category)
        for key, category in FATIGUE_ATTRIBUTE_SURFACES
    }
    try:
        with transaction.atomic():
            write_fatigue_state(member, state.reserve_units, SleepPosture.VOLUNTARY)
            project_fatigue_status(member)
    except Exception:
        # The projection requires its caller to own the transaction; restore
        # the durable and cached physiology so a failed entry leaves no
        # partially committed sleep posture behind.
        for (key, category), snapshot in snapshots.items():
            restore_attribute_best_effort(member, key, snapshot)
        raise
    candidates = _handoff_candidates(member)
    return SleepEntry(
        operation_id=operation_id or uuid4().hex,
        member=member,
        requested_seconds=requested,
        handoff_offered=bool(candidates),
        handoff_candidates=candidates,
    )


def _wake_voluntary(member: Any) -> bool:
    """Return a still-voluntary body to waking posture with its current reserve."""
    state = read_optional_fatigue_state(member)
    if state is None or state.posture is not SleepPosture.VOLUNTARY:
        return False
    write_fatigue_state(member, state.reserve_units, SleepPosture.AWAKE)
    project_fatigue_status(member)
    return True


def continue_sleep(
    actor: Any, entry: SleepEntry, *, operation_id: str | None = None
) -> SkipResult:
    """Explicitly continue one entered voluntary sleep up to its first boundary.

    The entry identity names the accepted sleep; the continuation rechecks
    safety and the selected body, truncates the recovery target at the
    earliest relevant boundary, settles gauges plus per-member mental time,
    and returns the body to waking posture only after the committed interval.
    The wake write shares the enclosing transaction with the advance, so a
    late failure restores the mental members and the tick together.
    """
    recorded = _recorded(operation_id)
    if recorded is not None:
        return recorded
    reason = evaluate_skip_safety(actor)
    if reason is not None:
        raise SkipRefused(reason)
    member = entry.member
    state = read_optional_fatigue_state(member)
    if state is None:
        raise SleepRefused("missing_physiology", MISSING_PHYSIOLOGY_MESSAGE)
    if state.posture is not SleepPosture.VOLUNTARY:
        raise SleepRefused("not_sleeping", NOT_SLEEPING_MESSAGE)
    entities = present_party_scope(actor)
    clock = get_world_clock()
    requested = seconds_to_full_regen(member)
    elapsed = planned_seconds(entities, requested, tick=clock.tick)
    commits: list[Any] = []
    mental = replace(plan_for(entities), record=commits)
    registry = build_advance_snapshot_registry(
        clock, elapsed, AdvanceSource.SKIP, entities, mental_scope=entities
    )
    tick_snapshot = _snapshot_clock_tick(clock)
    woke = False
    try:
        with transaction.atomic():
            events = clock.advance(
                elapsed, AdvanceSource.SKIP, entities, mental=mental
            )
            woke = _wake_voluntary(member)
            if woke:
                from typeclasses.characters import PlayerCharacter
                from world.rules.fatigue import _notify_wake_transition_observers

                if isinstance(member, PlayerCharacter):
                    occ_id = f"wake:voluntary:{getattr(member, 'pk', '')}:{operation_id or entry.operation_id}"
                    transaction.on_commit(
                        lambda ent=member, oid=occ_id: _notify_wake_transition_observers(
                            ent, occurrence_id=oid, in_combat=False
                        )
                    )
    except Exception:
        _restore_clock_tick(clock, tick_snapshot)
        _restore_advance_registry(registry, entities)
        raise
    result = SkipResult(
        operation_id=operation_id or entry.operation_id,
        requested_seconds=requested,
        elapsed_seconds=elapsed,
        events=tuple(events),
        fatigue_commits=tuple(commits),
        voluntary=True,
        woke=woke,
    )
    _record(result)
    return result


def begin_sleep(actor: Any) -> SleepOutcome:
    """Run the shared voluntary sleep request for either transport.

    A forced sleeper cannot volunteer. An already-voluntary body continues its
    entered sleep. A fresh entry with an awake controlling body to hand off to
    commits posture at zero elapsed time and stops; the player cancels by
    doing nothing or continues with another explicit request. Every other
    fresh entry continues immediately.
    """
    state = read_optional_fatigue_state(actor)
    if state is not None and state.posture is SleepPosture.FORCED:
        raise SleepRefused("forced_sleep", FORCED_SLEEP_MESSAGE)
    if state is not None and state.posture is SleepPosture.VOLUNTARY:
        entry = SleepEntry(
            operation_id=uuid4().hex,
            member=actor,
            requested_seconds=seconds_to_full_regen(actor),
            handoff_offered=False,
        )
        return SleepOutcome(entry, continue_sleep(actor, entry))
    entry = enter_sleep(actor)
    if entry.handoff_offered:
        return SleepOutcome(
            entry, None, render_handoff_offer_message(entry.handoff_candidates)
        )
    return SleepOutcome(entry, continue_sleep(actor, entry))


def accepted_wait_handoff_offer(actor: Any) -> str | None:
    """The contextual offer after an accepted wait, or ``None``.

    A wait can settle the controlled body into forced sleep mid-interval. The
    accepted operation is already committed, so the offer is recomputed from
    that committed state; an unselected or unpossessed body yields nothing.
    """
    candidates = _handoff_candidates(actor)
    if not candidates:
        return None
    return render_handoff_offer_message(candidates)


__all__ = [
    "BOOKING_IN_COMBAT_MESSAGE",
    "DAYPARTS",
    "DurationParseError",
    "MAX_SKIP_SECONDS",
    "MAX_WEB_SKIP_SECONDS",
    "PracticeBooking",
    "PracticeReject",
    "PracticeRejectReason",
    "SkipRefused",
    "SkipResult",
    "SleepEntry",
    "SleepOutcome",
    "SleepRefused",
    "advance_wait",
    "accepted_wait_handoff_offer",
    "begin_sleep",
    "book_member_practice",
    "continue_sleep",
    "enter_sleep",
    "parse_duration",
    "preflight_practice_booking",
    "rejection_message",
    "render_handoff_offer_message",
    "render_skip_summary",
    "seconds_to_full_regen",
    "seconds_to_natural_wake",
    "unsafe_rejection",
]
