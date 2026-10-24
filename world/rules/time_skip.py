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
from world.rules.sleep_receipt import (
    CONTINUATION_COMPLETE,
    CONTINUATION_NONE,
    CONTINUATION_PAUSED,
    CONTINUATION_PENDING,
    DECISION_DECLINED,
    DECISION_ENTERED,
    KIND_FORCED,
    KIND_VOLUNTARY,
    MISSING_RECEIPT_CODE,
    MISSING_RECEIPT_MESSAGE,
    MODE_DURATION,
    MODE_RECOVERY,
    SLEEP_RECEIPT_SURFACES,
    STATE_COMPLETED,
    STATE_SLEEPING,
    SleepReceipt,
    SleepReceiptError,
    bump_sleep_view_generation,
    full_recovery_seconds,
    next_sleep_offset,
    read_sleep_view_decision,
    read_sleep_view_generation,
    read_party_operation,
    read_sleep_receipt,
    write_sleep_view_decision,
    write_party_operation,
    write_sleep_receipt,
)
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
CONTINUE_SLEEP_MESSAGE = "你仍在自願睡眠中；若要繼續，請使用 sleep continue。"
ALREADY_RECOVERED_MESSAGE = "身體已完全恢復，無需入睡。"
PARTIAL_RECOVERY_MESSAGE = "已達睡眠上限，尚未完全恢復。"
PARTY_SLEEP_ACCEPTED_MESSAGE = "在場成員已進入睡眠。"
PARTY_SLEEP_NOTHING_MESSAGE = "在場成員都已入睡或已完全恢復。"
INVALID_SLEEP_MODE_MESSAGE = "睡眠模式無效；請使用 until-recovered 或明確時長。"
MISSING_DURATION_MESSAGE = "指定時長的睡眠需要一個時長，例如 sleep 2h。"
STALE_SLEEP_MESSAGE = "這次睡眠已經更新，請依目前狀態重新操作。"
PARTY_MEMBER_INELIGIBLE_MESSAGE = "隊伍中有成員目前無法入睡：{member}。"
PARTY_MEMBER_MISSING_RECEIPT_MESSAGE = "隊伍中有成員的睡眠紀錄缺失：{member}。"


def render_handoff_offer_message(candidates: Any) -> str:
    """Render the textual handoff choices: fatigue percent and return/possess."""
    from world.rules.possession import handoff_candidate_label

    parts = [handoff_candidate_label(candidate) for candidate in candidates]
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
    body_id: int | None = None
    sleep_id: str | None = None
    completed: bool = False
    partial: bool = False
    summary: str | None = None
    replayed: bool = False
    interrupted: bool = False
    continuation: str = CONTINUATION_NONE


@dataclass(frozen=True)
class SleepEntry:
    """One committed voluntary-sleep posture entry at zero elapsed time."""

    operation_id: str
    member: Any
    requested_seconds: int
    handoff_offered: bool
    handoff_candidates: tuple[Any, ...] = ()
    sleep_id: str = ""
    mode: str = MODE_RECOVERY
    target_tick: int = 0
    accepted_seconds: int = 0
    partial: bool = False
    receipt: SleepReceipt | None = None


@dataclass(frozen=True)
class SleepOutcome:
    """One explicit sleep request's accepted entry and/or committed result."""

    entry: SleepEntry | None
    result: SkipResult | None
    message: str | None = None
    entries: tuple[SleepEntry, ...] = ()
    receipts: tuple[SleepReceipt, ...] = ()


BOOKING_IN_COMBAT_MESSAGE = "戰鬥中無法排入修煉。"
_BOOKING_MESSAGE = "{member}將在下次休息時修煉「{skill}」。"

# A bounded in-process ledger of accepted results. A retried operation
# identity returns its recorded receipt instead of replaying elapsed time;
# a new explicit action always carries a new identity. The project has no
# durable skip-operation model, so this deliberately does not invent one.
_RESULT_LEDGER: dict[str, SkipResult] = {}
_LEDGER_LIMIT = 64


def _recorded(operation_id: str | None, body: Any = None) -> SkipResult | None:
    if operation_id is None:
        return None
    result = _RESULT_LEDGER.get(operation_id)
    if result is None:
        return None
    if body is not None and result.body_id is not None:
        if result.body_id != getattr(body, "pk", None):
            return None
    return result


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
    return min(full_recovery_seconds(entity), MAX_SKIP_SECONDS)


def _uncapped_recovery_seconds(entity: Any) -> int:
    """The uncapped recovery requirement used to report a truthful partial."""
    return full_recovery_seconds(entity)


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


def _validate_sleep_request(mode: Any, seconds: Any) -> int | None:
    """Validate one declared sleep mode/seconds pair without touching state."""
    if mode not in (MODE_RECOVERY, MODE_DURATION):
        raise SleepRefused("invalid_mode", INVALID_SLEEP_MODE_MESSAGE)
    if mode == MODE_DURATION:
        if seconds is None:
            raise SleepRefused("missing_duration", MISSING_DURATION_MESSAGE)
        if (
            isinstance(seconds, bool)
            or not isinstance(seconds, int)
            or seconds < 1
        ):
            raise SleepRefused("invalid_duration", MISSING_DURATION_MESSAGE)
        return min(int(seconds), MAX_SKIP_SECONDS)
    if seconds is not None:
        raise SleepRefused("invalid_mode", INVALID_SLEEP_MODE_MESSAGE)
    return None


def _accepted_sleep_seconds(
    member: Any, mode: str, duration_seconds: int | None
) -> tuple[int, bool]:
    """Return ``(bounded accepted seconds, capped-partial flag)`` for one entry."""
    if mode == MODE_DURATION:
        return int(duration_seconds or 0), False
    raw = _uncapped_recovery_seconds(member)
    return min(raw, MAX_SKIP_SECONDS), raw > MAX_SKIP_SECONDS


def _owner_id_for(member: Any) -> int | None:
    """The authenticated owner behind one body, when one resolves."""
    try:
        return int(resolve_commander(member).pk)
    except (PartyScopeError, TypeError, ValueError):  # observability: ignore R2: a non-player-driven body has no authenticated owner; this read writes nothing
        return None


def _sleep_surface_snapshot(member: Any) -> dict[str, tuple[bool, Any]]:
    """Snapshot every durable surface one sleep entry/interval can write."""
    surfaces = tuple(FATIGUE_ATTRIBUTE_SURFACES) + tuple(SLEEP_RECEIPT_SURFACES)
    return {
        f"{key}::{category}": attribute_snapshot(member, key, category)
        for key, category in surfaces
    }


def _restore_sleep_surfaces(
    member: Any, snapshots: dict[str, tuple[bool, Any]]
) -> None:
    """Restore one body's snapshotted physiology, projection and receipt."""
    surfaces = {
        f"{key}::{category}": (key, category)
        for key, category in (
            tuple(FATIGUE_ATTRIBUTE_SURFACES) + tuple(SLEEP_RECEIPT_SURFACES)
        )
    }
    for marker, snapshot in snapshots.items():
        key, category = surfaces[marker]
        restore_attribute_best_effort(member, key, snapshot, category)


def _lock_members(entities: tuple[Any, ...]) -> None:
    """Lock the selected body rows in stable primary-key order."""
    from evennia.objects.models import ObjectDB

    ids = sorted(
        {
            int(entity.pk)
            for entity in entities
            if getattr(entity, "pk", None) is not None
        }
    )
    if ids:
        list(
            ObjectDB.objects.select_for_update()
            .filter(id__in=ids)
            .order_by("id")
            .values_list("id", flat=True)
        )


def _receipt_for(member: Any) -> SleepReceipt | None:
    """Read one body's receipt, surfacing a corrupt record as a refusal."""
    try:
        return read_sleep_receipt(member)
    except SleepReceiptError as error:
        raise SleepRefused(error.code, error.message) from error


def enter_sleep(
    actor: Any,
    *,
    member_id: int | None = None,
    operation_id: str | None = None,
    mode: str = MODE_RECOVERY,
    seconds: int | None = None,
) -> SleepEntry:
    """Commit one accepted voluntary sleep posture at zero elapsed time.

    Only the explicitly selected body (default: the acting body) enters. The
    durable receipt is written in the same transaction as the posture and its
    projection. An active accepted receipt is never replaced; a fresh request
    is refused with the continuation instruction. A recovery target that is
    already met reconciles awake inside this transaction without claiming any
    completed elapsed sleep.
    """
    duration = _validate_sleep_request(mode, seconds)
    reason = evaluate_skip_safety(actor)
    if reason is not None:
        raise SkipRefused(reason)
    member = _sleep_member(actor, member_id)
    state = read_optional_fatigue_state(member)
    if state is None:
        raise SleepRefused("missing_physiology", MISSING_PHYSIOLOGY_MESSAGE)
    if state.posture is SleepPosture.FORCED:
        raise SleepRefused("forced_sleep", FORCED_SLEEP_MESSAGE)
    if state.posture is SleepPosture.VOLUNTARY:
        receipt = _receipt_for(member)
        if receipt is None:
            raise SleepRefused(MISSING_RECEIPT_CODE, MISSING_RECEIPT_MESSAGE)
        raise SleepRefused("already_asleep", CONTINUE_SLEEP_MESSAGE)
    tick = int(get_world_clock().tick)
    snapshots = None
    try:
        with transaction.atomic():
            # Lock and re-read the authoritative posture before constructing
            # the receipt: a concurrent accepted entry must win, never be
            # silently replaced by this request.
            _lock_members((member,))
            current = read_optional_fatigue_state(member)
            if current is None:
                raise SleepRefused(
                    "missing_physiology", MISSING_PHYSIOLOGY_MESSAGE
                )
            if current.posture is SleepPosture.FORCED:
                raise SleepRefused("forced_sleep", FORCED_SLEEP_MESSAGE)
            if current.posture is SleepPosture.VOLUNTARY:
                _receipt_for(member)
                raise SleepRefused("already_asleep", CONTINUE_SLEEP_MESSAGE)
            accepted, partial = _accepted_sleep_seconds(member, mode, duration)
            if accepted <= 0:
                # An already-met recovery target must not invent elapsed sleep
                # or a sleeping posture that would re-enter a completed episode.
                return SleepEntry(
                    operation_id=operation_id or uuid4().hex,
                    member=member,
                    requested_seconds=0,
                    handoff_offered=False,
                    sleep_id="",
                    mode=mode,
                    target_tick=tick,
                    accepted_seconds=0,
                    partial=False,
                    receipt=None,
                )
            # Snapshot only after admission revalidation: a refusal that wrote
            # nothing must never restore (and thereby erase) a competing
            # committed plan.
            snapshots = _sleep_surface_snapshot(member)
            sleep_id = uuid4().hex
            receipt = SleepReceipt(
                sleep_id=sleep_id,
                body_id=int(member.pk),
                owner_id=_owner_id_for(member),
                kind=KIND_VOLUNTARY,
                mode=mode,
                entry_tick=tick,
                target_tick=tick + accepted,
                limit_tick=tick + accepted,
                settled_through_tick=tick,
                revision=0,
                state=STATE_SLEEPING,
                accepted_seconds=accepted,
                partial=partial,
                entry_operation_id=operation_id or sleep_id,
            )
            write_fatigue_state(
                member, current.reserve_units, SleepPosture.VOLUNTARY
            )
            write_sleep_receipt(member, receipt)
            project_fatigue_status(member)
            if _owner_id_for(member) == int(member.pk):
                bump_sleep_view_generation(member)
    except Exception:
        # The projection requires its caller to own the transaction; restore
        # the durable and cached physiology so a failed write leaves no
        # partially committed sleep posture or receipt behind.
        if snapshots is not None:
            _restore_sleep_surfaces(member, snapshots)
        raise
    candidates = _handoff_candidates(member)
    return SleepEntry(
        operation_id=receipt.entry_operation_id or sleep_id,
        member=member,
        requested_seconds=accepted,
        handoff_offered=bool(candidates),
        handoff_candidates=candidates,
        sleep_id=sleep_id,
        mode=mode,
        target_tick=receipt.target_tick,
        accepted_seconds=accepted,
        partial=partial,
        receipt=receipt,
    )


def _replayed_result(receipt: SleepReceipt, body: Any) -> SkipResult:
    """Reconstruct one durable committed interval result without settlement."""
    stored = receipt.last_result or {}
    kinds = tuple(str(kind) for kind in stored.get("event_kinds", ()))
    interactive = bool(stored.get("interactive", False))
    return SkipResult(
        operation_id=str(stored.get("operation_id") or receipt.sleep_id),
        requested_seconds=int(stored.get("requested_seconds", 0)),
        elapsed_seconds=int(stored.get("elapsed_seconds", 0)),
        events=tuple(
            ScheduledEvent(
                kind,
                int(stored.get("tick_to", 0)),
                {},
                interactive=interactive,
            )
            for kind in kinds
        ),
        voluntary=True,
        woke=bool(stored.get("woke")),
        body_id=getattr(body, "pk", None),
        sleep_id=receipt.sleep_id,
        completed=bool(stored.get("completed")),
        partial=bool(stored.get("partial")),
        summary=stored.get("summary"),
        replayed=True,
        interrupted=interactive,
    )


def continue_sleep(
    actor: Any,
    entry: SleepEntry | None = None,
    *,
    operation_id: str | None = None,
    expected_sleep_id: str | None = None,
    expected_revision: int | None = None,
    continuation: dict[str, Any] | None = None,
) -> SkipResult:
    """Explicitly continue one accepted sleep up to its first boundary.

    The durable receipt is the identity: a continuation rechecks safety and the
    selected body, compares the caller's expected sleep/revision when one is
    supplied, settles the remaining accepted interval through the ordinary
    clock (which truncates at the earliest relevant boundary), and records the
    interval result on the receipt in the same transaction. A retried identity
    returns the committed result without replaying time, including after a
    reload and after the receipt's own revision advanced with that same
    operation. A receipt that has not reached its target stays sleeping with
    its remaining plan intact.

    ``continuation`` is the owner-target executor's bounded disposition
    record. When supplied it is committed in the same transaction as the
    interval receipt, so a crash after an interactive interval cannot leave
    an authorization that would continue past the interruption.

    A forced sleep is an accepted receipt too: its existing threshold target
    is continued without inventing a voluntary posture or a new plan.
    """
    recorded = _recorded(operation_id)
    if recorded is not None:
        return recorded
    interval_operation = operation_id or uuid4().hex
    reason = evaluate_skip_safety(actor)
    if reason is not None:
        raise SkipRefused(reason)
    member = entry.member if entry is not None else actor
    clock = get_world_clock()
    ticks_before = int(clock.tick)
    entities = present_party_scope(actor)
    commits: list[Any] = []
    mental = replace(plan_for(entities), record=commits)
    registry = build_advance_snapshot_registry(
        clock, 0, AdvanceSource.SKIP, entities, mental_scope=entities
    )
    tick_snapshot = _snapshot_clock_tick(clock)
    elapsed = 0
    events: list[ScheduledEvent] = []
    try:
        with transaction.atomic():
            _lock_members(entities)
            state = read_optional_fatigue_state(member)
            if state is None:
                raise SleepRefused(
                    "missing_physiology", MISSING_PHYSIOLOGY_MESSAGE
                )
            receipt = _receipt_for(member)
            if receipt is None:
                raise SleepRefused(MISSING_RECEIPT_CODE, MISSING_RECEIPT_MESSAGE)
            if (
                expected_sleep_id is not None
                and receipt.sleep_id != expected_sleep_id
            ):
                raise SleepRefused("stale_sleep", STALE_SLEEP_MESSAGE)
            if receipt.last_operation_id == interval_operation:
                return _replayed_result(receipt, member)
            if (
                expected_revision is not None
                and receipt.revision != expected_revision
            ):
                raise SleepRefused("stale_sleep", STALE_SLEEP_MESSAGE)
            if not receipt.sleeping:
                raise SleepRefused("not_sleeping", NOT_SLEEPING_MESSAGE)
            if state.posture not in (SleepPosture.VOLUNTARY, SleepPosture.FORCED):
                raise SleepRefused("not_sleeping", NOT_SLEEPING_MESSAGE)
            if receipt.kind == KIND_VOLUNTARY and state.posture is not SleepPosture.VOLUNTARY:
                raise SleepRefused("not_sleeping", NOT_SLEEPING_MESSAGE)
            if receipt.kind == KIND_FORCED and state.posture is not SleepPosture.FORCED:
                raise SleepRefused("not_sleeping", NOT_SLEEPING_MESSAGE)
            remaining = next_sleep_offset(member, receipt, int(clock.tick))
            assert remaining is not None
            elapsed = planned_seconds(
                entities, remaining, tick=int(clock.tick)
            )
            events = clock.advance(
                elapsed, AdvanceSource.SKIP, entities, mental=mental
            )
            updated = read_sleep_receipt(member)
            summary = render_skip_summary(elapsed, list(events))
            if updated is not None and updated.sleeping and updated.target_tick >= updated.limit_tick:
                summary = f"{summary} {PARTIAL_RECOVERY_MESSAGE}"
            result_payload = {
                "operation_id": interval_operation,
                "sleep_id": receipt.sleep_id,
                "revision": updated.revision if updated is not None else receipt.revision,
                "requested_seconds": remaining,
                "elapsed_seconds": elapsed,
                "tick_from": ticks_before,
                "tick_to": ticks_before + elapsed,
                "woke": bool(updated is not None and not updated.sleeping),
                "completed": bool(
                    updated is not None and updated.state == STATE_COMPLETED
                ),
                "partial": bool(updated.partial if updated is not None else receipt.partial),
                "summary": summary,
                "interactive": any(event.interactive for event in events),
                "event_kinds": [str(event.kind) for event in events],
            }
            if updated is not None:
                write_sleep_receipt(member, updated.with_result(result_payload))
            if continuation is not None:
                disposition = dict(continuation)
                disposition["continuation"] = (
                    CONTINUATION_COMPLETE
                    if not (updated is not None and updated.sleeping)
                    else CONTINUATION_PAUSED
                    if result_payload["interactive"]
                    else CONTINUATION_PENDING
                )
                disposition["last_operation_id"] = interval_operation
                write_sleep_view_decision(member, disposition)
    except Exception:
        _restore_clock_tick(clock, tick_snapshot)
        _restore_advance_registry(registry, entities)
        raise
    final = read_sleep_receipt(member)
    result = SkipResult(
        operation_id=interval_operation,
        requested_seconds=remaining,
        elapsed_seconds=elapsed,
        events=tuple(events),
        fatigue_commits=tuple(commits),
        voluntary=True,
        woke=bool(final is not None and not final.sleeping),
        body_id=getattr(member, "pk", None),
        sleep_id=final.sleep_id if final is not None else None,
        completed=bool(final is not None and final.state == STATE_COMPLETED),
        partial=bool(final.partial if final is not None else False),
        summary=(
            render_skip_summary(elapsed, list(events))
            + (
                f" {PARTIAL_RECOVERY_MESSAGE}"
                if final is not None and final.partial and not final.sleeping
                else ""
            )
        ),
        interrupted=any(event.interactive for event in events),
    )
    _record(result)
    return result


def _operable_if_awake(member: Any) -> bool:
    """Whether one present body could act if it were awake.

    Dead, knocked-out and buff/modifier-incapable bodies cannot substitute for
    an awake controller, so they neither require sleep nor block the all-asleep
    owner continuation.
    """
    from world.rules.action.gates import capability_failure
    from world.rules.buffs import blocks_action
    from world.rules.party_scope import is_knocked_out

    if is_knocked_out(member):
        return False
    try:
        hp = float(getattr(member.traits.hp, "current", member.traits.hp.value))
    except Exception:  # observability: ignore R2: an unreadable gauge is not an operable body; this display read writes nothing
        return False
    if hp <= 0:
        return False
    attributes = getattr(member, "attributes", None)
    blocked = bool(
        attributes is not None
        and attributes.has("buffs")
        and blocks_action(member)
    )
    return capability_failure(member, blocked, asleep=False) is None


def all_operable_asleep(actor: Any) -> bool:
    """Whether every operable present party body is currently asleep."""
    try:
        members = present_party_scope(actor)
    except PartyScopeError:  # observability: ignore R2: a non-player body has no party scope and therefore no automatic continuation
        return False
    operable = 0
    for member in members:
        if getattr(member, "_is_deleted", False):
            continue
        if not _operable_if_awake(member):
            continue
        operable += 1
        if not sleep_blocks_actions(member):
            return False
    return operable > 0


def _owner_sleep_receipt(actor: Any) -> tuple[Any, SleepReceipt]:
    """Resolve the authenticated owner and its accepted sleeping receipt."""
    commander = resolve_commander(actor)
    if commander is not actor:
        raise SleepRefused("not_owner_control", NOT_SLEEPING_MESSAGE)
    receipt = _receipt_for(commander)
    if receipt is None:
        raise SleepRefused(MISSING_RECEIPT_CODE, MISSING_RECEIPT_MESSAGE)
    if not receipt.sleeping:
        raise SleepRefused("not_sleeping", NOT_SLEEPING_MESSAGE)
    return commander, receipt


def owner_sleep_view_state(actor: Any) -> dict[str, Any] | None:
    """The current no-possession owner-sleep decision state, or ``None``.

    Reads only committed state: the owner body, its accepted sleeping receipt,
    the control-view generation and the durable answer. It never writes.
    """
    from world.rules.possession import current_possession

    try:
        commander = resolve_commander(actor)
    except PartyScopeError:  # observability: ignore R2: a non-player body has no owner-sleep view
        return None
    if commander is not actor or current_possession(commander) is not None:
        return None
    if getattr(getattr(commander, "db", None), "possessed_by", None) is not None:
        return None
    try:
        receipt = _receipt_for(commander)
    except SleepRefused:  # observability: ignore R2: a corrupt receipt is reported by the authoritative continuation, not the pure view
        return None
    if receipt is None or not receipt.sleeping:
        return None
    generation = read_sleep_view_generation(commander)
    decision = read_sleep_view_decision(commander)
    answered = bool(
        decision is not None
        and decision["generation"] == generation
        and decision["sleep_id"] == receipt.sleep_id
    )
    return {
        "owner": commander,
        "sleep_id": receipt.sleep_id,
        "revision": receipt.revision,
        "generation": generation,
        "decision": decision,
        "pending": not answered,
        "continuation": (
            decision["continuation"] if answered else CONTINUATION_NONE
        ),
        "receipt": receipt,
    }


def record_owner_sleep_decision(
    actor: Any,
    *,
    sleep_id: str,
    revision: int,
    generation: int,
    decision: str,
    continuation: str = CONTINUATION_NONE,
) -> dict[str, Any]:
    """Record one explicit owner dream answer against the offered view.

    Every identity is rechecked under the owner row lock: the authenticated
    owner body, no active possession, the accepted sleeping receipt and its
    revision, and the control-view generation the player actually answered.
    A stale answer writes nothing.
    """
    from world.rules.possession import current_possession

    if decision not in (DECISION_ENTERED, DECISION_DECLINED):
        raise SleepRefused("invalid_decision", STALE_SLEEP_MESSAGE)
    commander, receipt = _owner_sleep_receipt(actor)
    if current_possession(commander) is not None:
        raise SleepRefused("not_owner_control", NOT_SLEEPING_MESSAGE)
    with transaction.atomic():
        _lock_members((commander,))
        if current_possession(commander) is not None:
            raise SleepRefused("not_owner_control", NOT_SLEEPING_MESSAGE)
        receipt = _receipt_for(commander)
        if (
            receipt is None
            or not receipt.sleeping
            or receipt.sleep_id != sleep_id
            or receipt.revision != int(revision)
            or read_sleep_view_generation(commander) != int(generation)
        ):
            raise SleepRefused("stale_sleep", STALE_SLEEP_MESSAGE)
        value = {
            "generation": int(generation),
            "sleep_id": receipt.sleep_id,
            "decision": decision,
            "continuation": continuation,
            "last_operation_id": None,
        }
        write_sleep_view_decision(commander, value)
    return value


def decline_owner_sleep_dream(
    actor: Any,
    *,
    sleep_id: str,
    revision: int,
    generation: int,
) -> tuple[dict[str, Any], bool]:
    """Record a decline and its automatic-continuation authorization atomically.

    The all-asleep precondition is evaluated while the owner row and the
    present party rows are locked, so an awake operable companion observed here
    is the same fact the continuation authorization commits. Returns the
    durable decision and whether the caller must run the rules continuation.
    """
    from world.rules.possession import current_possession

    commander, receipt = _owner_sleep_receipt(actor)
    if current_possession(commander) is not None:
        raise SleepRefused("not_owner_control", NOT_SLEEPING_MESSAGE)
    with transaction.atomic():
        members = present_party_scope(commander)
        _lock_members((commander, *members))
        if current_possession(commander) is not None:
            raise SleepRefused("not_owner_control", NOT_SLEEPING_MESSAGE)
        receipt = _receipt_for(commander)
        if (
            receipt is None
            or not receipt.sleeping
            or receipt.sleep_id != sleep_id
            or receipt.revision != int(revision)
            or read_sleep_view_generation(commander) != int(generation)
        ):
            raise SleepRefused("stale_sleep", STALE_SLEEP_MESSAGE)
        auto = all_operable_asleep(commander)
        value = {
            "generation": int(generation),
            "sleep_id": receipt.sleep_id,
            "decision": DECISION_DECLINED,
            "continuation": (
                CONTINUATION_PENDING if auto else CONTINUATION_NONE
            ),
            "last_operation_id": None,
        }
        write_sleep_view_decision(commander, value)
    return value, auto


def authorize_owner_sleep_continuation(
    actor: Any,
    *,
    sleep_id: str,
    revision: int,
    generation: int,
) -> dict[str, Any] | None:
    """Commit same-receipt departure intent without advancing time.

    Called inside the narrative owner's transaction so a confirmed/awakened
    dream and its continuation authorization commit together. A draft save,
    failed generation and rejected confirmation never call this.
    """
    from world.rules.possession import current_possession

    try:
        commander = resolve_commander(actor)
    except PartyScopeError:  # observability: ignore R2: a non-player body cannot authorize an owner continuation
        return None
    if commander is not actor or current_possession(commander) is not None:
        return None
    with transaction.atomic():
        _lock_members((commander,))
        receipt = _receipt_for(commander)
        if (
            receipt is None
            or not receipt.sleeping
            or receipt.sleep_id != sleep_id
            or receipt.revision != int(revision)
            or read_sleep_view_generation(commander) != int(generation)
        ):
            return None
        current = read_sleep_view_decision(commander)
        value = {
            "generation": int(generation),
            "sleep_id": receipt.sleep_id,
            "decision": (
                current["decision"]
                if current is not None
                and current["generation"] == int(generation)
                else DECISION_ENTERED
            ),
            "continuation": CONTINUATION_PENDING,
            "last_operation_id": None,
        }
        write_sleep_view_decision(commander, value)
    return value


def _party_progress_signature(commander: Any) -> tuple[tuple[int, str | None, int | None], ...]:
    """One pure snapshot of present bodies' posture/receipt progress."""
    signature: list[tuple[int, str | None, int | None]] = []
    for member in present_party_scope(commander):
        try:
            state = read_optional_fatigue_state(member)
        except Exception:  # observability: ignore R2: malformed physiology only weakens the progress comparison; no state is written
            state = None
        try:
            receipt = read_sleep_receipt(member)
        except SleepReceiptError:  # observability: ignore R2: a corrupt receipt is a no-progress marker; the interval owner reports it
            receipt = None
        signature.append(
            (
                int(member.pk),
                state.posture.value if state is not None else None,
                receipt.revision if receipt is not None else None,
            )
        )
    return tuple(signature)


_CONTINUATION_INTERVAL_BOUND = 64


def continue_owner_sleep(
    actor: Any,
    *,
    sleep_id: str | None = None,
    expected_revision: int | None = None,
    expected_generation: int | None = None,
    operation_id: str | None = None,
) -> SkipResult:
    """Continue the owner's accepted sleep past intermediate companion wakes.

    The owner's receipt target is the terminal goal; each iteration delegates
    one boundary-sized interval to :func:`continue_sleep`, so a companion
    waking earlier commits that boundary and the next iteration keeps the
    owner's retained authorization. A real registered interactive event, the
    safety gate, a control change or a corrupt/stale receipt pauses the
    continuation with its remaining target intact. A retried interval replays
    from its receipt identity instead of settling again.
    """
    from world.rules.possession import current_possession

    recorded = _recorded(operation_id)
    if recorded is not None:
        return recorded
    commander, receipt = _owner_sleep_receipt(actor)
    if sleep_id is not None and receipt.sleep_id != sleep_id:
        raise SleepRefused("stale_sleep", STALE_SLEEP_MESSAGE)
    if expected_revision is not None and receipt.revision != int(expected_revision):
        raise SleepRefused("stale_sleep", STALE_SLEEP_MESSAGE)
    generation = read_sleep_view_generation(commander)
    if expected_generation is not None and generation != int(expected_generation):
        raise SleepRefused("stale_sleep", STALE_SLEEP_MESSAGE)
    decision = read_sleep_view_decision(commander)
    base_decision = (
        decision["decision"]
        if decision is not None
        and decision["generation"] == generation
        and decision["sleep_id"] == receipt.sleep_id
        else DECISION_DECLINED
    )
    base_operation = operation_id or (
        f"owner:{receipt.sleep_id[:48]}:{generation}:{uuid4().hex[:12]}"
    )
    total_elapsed = 0
    all_events: list[ScheduledEvent] = []
    summaries: list[str] = []
    continuation = CONTINUATION_PENDING
    interrupted = False
    pause_message: str | None = None
    for index in range(_CONTINUATION_INTERVAL_BOUND):
        if current_possession(commander) is not None:
            continuation = CONTINUATION_PAUSED
            pause_message = "控制權已改變，保留剩餘睡眠。"
            break
        receipt = _receipt_for(commander)
        if receipt is None or not receipt.sleeping:
            continuation = CONTINUATION_COMPLETE
            break
        if read_sleep_view_generation(commander) != generation:
            continuation = CONTINUATION_PAUSED
            pause_message = STALE_SLEEP_MESSAGE
            break
        before = _party_progress_signature(commander)
        interval_operation = f"{base_operation}:{index}"
        try:
            interval = continue_sleep(
                commander,
                operation_id=interval_operation,
                expected_sleep_id=receipt.sleep_id,
                expected_revision=receipt.revision,
                continuation={
                    "generation": generation,
                    "sleep_id": receipt.sleep_id,
                    "decision": base_decision,
                },
            )
        except SkipRefused as error:
            continuation = CONTINUATION_PAUSED
            pause_message = rejection_message(error.reason)
            break
        except SleepRefused as error:
            continuation = CONTINUATION_PAUSED
            pause_message = error.message
            break
        total_elapsed += interval.elapsed_seconds
        all_events.extend(interval.events)
        if interval.summary:
            summaries.append(interval.summary)
        if interval.interrupted:
            continuation = CONTINUATION_PAUSED
            interrupted = True
            break
        after_receipt = _receipt_for(commander)
        if after_receipt is None or not after_receipt.sleeping:
            continuation = CONTINUATION_COMPLETE
            break
        if interval.elapsed_seconds <= 0 and (
            _party_progress_signature(commander) == before
        ):
            # A zero-offset boundary that changed nothing cannot make progress;
            # retain the plan instead of looping forever.
            continuation = CONTINUATION_PAUSED
            break
    else:
        # The safety bound is a progress guard, never a completion claim.
        continuation = CONTINUATION_PAUSED
        pause_message = "睡眠仍在進行；可再次使用 sleep continue。"

    if continuation != CONTINUATION_COMPLETE:
        _mark_owner_continuation(
            commander,
            generation=generation,
            sleep_id=receipt.sleep_id,
            decision=base_decision,
            continuation=continuation,
            last_operation_id=f"{base_operation}:last",
        )
    else:
        _mark_owner_continuation(
            commander,
            generation=generation,
            sleep_id=receipt.sleep_id,
            decision=base_decision,
            continuation=CONTINUATION_COMPLETE,
            last_operation_id=f"{base_operation}:last",
        )
    if pause_message:
        summaries.append(pause_message)
    summary = " ".join(part for part in summaries if part)
    result = SkipResult(
        operation_id=base_operation,
        requested_seconds=int(receipt.accepted_seconds),
        elapsed_seconds=total_elapsed,
        events=tuple(all_events),
        voluntary=receipt.kind == KIND_VOLUNTARY,
        woke=continuation == CONTINUATION_COMPLETE,
        body_id=int(commander.pk),
        sleep_id=receipt.sleep_id,
        completed=continuation == CONTINUATION_COMPLETE,
        partial=bool(receipt.partial),
        summary=summary or None,
        interrupted=interrupted,
        continuation=continuation,
    )
    _record(result)
    return result


def _mark_owner_continuation(
    commander: Any,
    *,
    generation: int,
    sleep_id: str,
    decision: str,
    continuation: str,
    last_operation_id: str,
) -> None:
    """Persist the executor's final disposition under the owner row lock."""
    with transaction.atomic():
        _lock_members((commander,))
        write_sleep_view_decision(
            commander,
            {
                "generation": int(generation),
                "sleep_id": sleep_id,
                "decision": decision,
                "continuation": continuation,
                "last_operation_id": last_operation_id,
            },
        )


def resume_pending_owner_continuation(actor: Any) -> SkipResult | None:
    """Resume one durable pending owner continuation after reconnect/login.

    A paused or completed intent is never auto-resumed; a pending one runs
    once and advances only the receipt's uncommitted target.
    """
    from world.rules.possession import current_possession

    try:
        decision = read_sleep_view_decision(actor)
    except Exception:  # observability: ignore R2: an unreadable intent resumes nothing
        return None
    if decision is None or decision["continuation"] != CONTINUATION_PENDING:
        return None
    if current_possession(actor) is not None:
        return None
    if read_sleep_view_generation(actor) != decision["generation"]:
        return None
    try:
        return continue_owner_sleep(
            actor,
            sleep_id=decision["sleep_id"],
            expected_generation=decision["generation"],
        )
    except (SkipRefused, SleepRefused) as error:
        log_warn(
            "owner_sleep_continuation_paused",
            context={
                "char": str(getattr(actor, "pk", "?")),
                "sleep_id": decision["sleep_id"],
                "reason": getattr(error, "reason", None)
                or getattr(error, "code", "refused"),
            },
        )
        return None


def begin_sleep(
    actor: Any,
    *,
    mode: str = MODE_RECOVERY,
    seconds: int | None = None,
    scope: str = "self",
    operation_id: str | None = None,
    allow_continue: bool = True,
) -> SleepOutcome:
    """Run one shared voluntary sleep request for either transport.

    ``scope='party'`` is the explicit all-present-effective-party entry: it
    commits every awake physiological body at zero elapsed time and never
    transfers control. ``allow_continue`` is false for an explicit
    mode/duration request, which must not replace an active accepted plan.
    """
    duration = _validate_sleep_request(mode, seconds)
    if scope == "party":
        return enter_party_sleep(
            actor, mode=mode, seconds=duration, operation_id=operation_id
        )
    if scope != "self":
        raise SleepRefused("invalid_scope", INVALID_SLEEP_MODE_MESSAGE)
    state = read_optional_fatigue_state(actor)
    if state is not None and state.posture is SleepPosture.FORCED:
        raise SleepRefused("forced_sleep", FORCED_SLEEP_MESSAGE)
    if state is not None and state.posture is SleepPosture.VOLUNTARY:
        receipt = _receipt_for(actor)
        if receipt is None:
            raise SleepRefused(MISSING_RECEIPT_CODE, MISSING_RECEIPT_MESSAGE)
        if not allow_continue:
            raise SleepRefused("already_asleep", CONTINUE_SLEEP_MESSAGE)
        return SleepOutcome(
            None,
            continue_sleep(actor, operation_id=operation_id),
            receipts=(receipt,),
        )
    entry = enter_sleep(
        actor, operation_id=operation_id, mode=mode, seconds=duration
    )
    if entry.receipt is None:
        result = SkipResult(
            operation_id=entry.operation_id,
            requested_seconds=0,
            elapsed_seconds=0,
            events=(),
            voluntary=True,
            woke=False,
            body_id=getattr(actor, "pk", None),
            summary=ALREADY_RECOVERED_MESSAGE,
        )
        return SleepOutcome(entry, result, ALREADY_RECOVERED_MESSAGE)
    if entry.handoff_offered:
        return SleepOutcome(
            entry, None, render_handoff_offer_message(entry.handoff_candidates)
        )
    if _owner_id_for(entry.member) == int(entry.member.pk):
        # The owner's accepted sleep must first offer its owner-only dream
        # decision; no recovery interval may commit before that answer.
        return SleepOutcome(entry, None, None)
    return SleepOutcome(entry, continue_sleep(actor, entry))


def _party_member_eligible(member: Any) -> None:
    """Validate one present member can accept voluntary sleep, or refuse."""
    name = str(getattr(member, "key", getattr(member, "pk", "?")))
    if getattr(member, "_is_deleted", False):
        raise SleepRefused(
            "party_member_ineligible",
            PARTY_MEMBER_INELIGIBLE_MESSAGE.format(member=name),
        )
    state = read_optional_fatigue_state(member)
    if state is None:
        raise SleepRefused("missing_physiology", MISSING_PHYSIOLOGY_MESSAGE)
    try:
        hp = float(getattr(member.traits.hp, "current", member.traits.hp.value))
    except Exception:  # observability: ignore R2: a body without readable traits is a synthetic non-physiological fixture already refused above; this read writes nothing
        return
    if hp <= 0:
        raise SleepRefused(
            "party_member_ineligible",
            PARTY_MEMBER_INELIGIBLE_MESSAGE.format(member=name),
        )


def enter_party_sleep(
    actor: Any,
    *,
    mode: str = MODE_RECOVERY,
    seconds: int | None = None,
    operation_id: str | None = None,
) -> SleepOutcome:
    """Commit the explicit all-present-effective-party sleep entry.

    Every present effective member (the owner included) is validated before
    any write. Awake physiological bodies receive a new voluntary receipt;
    existing voluntary and forced sleepers retain their accepted target and
    identity. Remote companions are untouched. Failure restores every touched
    member's physiology, projection and receipt together. No time passes and
    no possession changes.
    """
    duration = _validate_sleep_request(mode, seconds)
    reason = evaluate_skip_safety(actor)
    if reason is not None:
        raise SkipRefused(reason)
    commander = resolve_commander(actor)
    members = present_party_scope(actor)
    tick = int(get_world_clock().tick)
    planned: list[tuple[Any, SleepReceipt, int, bool]] = []
    for member in members:
        if getattr(member, "_is_deleted", False):
            continue
        _party_member_eligible(member)
        state = read_optional_fatigue_state(member)
        if state is None:  # pragma: no cover - guarded above
            continue
        if state.posture in (SleepPosture.FORCED, SleepPosture.VOLUNTARY):
            receipt = _receipt_for(member)
            if state.posture is SleepPosture.VOLUNTARY and receipt is None:
                name = str(getattr(member, "key", member.pk))
                raise SleepRefused(
                    MISSING_RECEIPT_CODE,
                    PARTY_MEMBER_MISSING_RECEIPT_MESSAGE.format(member=name),
                )
            # An existing accepted plan (or a forced threshold plan) keeps its
            # own target and identity.
            continue
        accepted, partial = _accepted_sleep_seconds(member, mode, duration)
        if accepted <= 0:
            continue
        sleep_id = uuid4().hex
        receipt = SleepReceipt(
            sleep_id=sleep_id,
            body_id=int(member.pk),
            owner_id=int(commander.pk),
            kind=KIND_VOLUNTARY,
            mode=mode,
            entry_tick=tick,
            target_tick=tick + accepted,
            limit_tick=tick + accepted,
            settled_through_tick=tick,
            revision=0,
            state=STATE_SLEEPING,
            accepted_seconds=accepted,
            partial=partial,
            entry_operation_id=operation_id or sleep_id,
        )
        planned.append((member, receipt, accepted, partial))
    operation = operation_id or uuid4().hex
    try:
        prior = read_party_operation(commander)
    except SleepReceiptError as error:
        raise SleepRefused(error.code, error.message) from error
    if prior is not None and prior["operation_id"] == operation:
        stored_ids = set(prior["body_ids"])
        stored = [
            (member, _receipt_for(member))
            for member in members
            if int(member.pk) in stored_ids
        ]
        if stored and all(receipt is not None for _, receipt in stored):
            entries = tuple(
                SleepEntry(
                    operation_id=operation,
                    member=member,
                    requested_seconds=(
                        receipt.accepted_seconds if receipt is not None else 0
                    ),
                    handoff_offered=False,
                    sleep_id=receipt.sleep_id if receipt is not None else "",
                    mode=receipt.mode if receipt is not None else mode,
                    target_tick=receipt.target_tick if receipt is not None else tick,
                    accepted_seconds=(
                        receipt.accepted_seconds if receipt is not None else 0
                    ),
                    partial=receipt.partial if receipt is not None else False,
                    receipt=receipt,
                )
                for member, receipt in stored
            )
            return SleepOutcome(
                None,
                None,
                PARTY_SLEEP_ACCEPTED_MESSAGE,
                entries=entries,
                receipts=tuple(
                    receipt for _, receipt in stored if receipt is not None
                ),
            )
    if not planned:
        raise SleepRefused("already_asleep", PARTY_SLEEP_NOTHING_MESSAGE)
    body_ids = [int(member.pk) for member, *_ in planned]
    snapshots = None
    try:
        with transaction.atomic():
            _lock_members(members)
            admission: list[tuple[Any, Any, Any, int, bool]] = []
            for member, receipt, accepted, partial in planned:
                current = read_optional_fatigue_state(member)
                if current is None:  # pragma: no cover - preflight checked it
                    raise SleepRefused(
                        "missing_physiology", MISSING_PHYSIOLOGY_MESSAGE
                    )
                # Re-read under the lock: a sleep posture another request
                # committed first keeps its own accepted identity.
                if current.posture is SleepPosture.VOLUNTARY:
                    raise SleepRefused("already_asleep", CONTINUE_SLEEP_MESSAGE)
                if current.posture is SleepPosture.FORCED:
                    raise SleepRefused("forced_sleep", FORCED_SLEEP_MESSAGE)
                admission.append(
                    (member, receipt, current.reserve_units, accepted, partial)
                )
            # Snapshot only after every admission revalidation: a refusal that
            # wrote nothing must never restore a competing committed plan.
            snapshots = {
                id(member): (member, _sleep_surface_snapshot(member))
                for member in members
            }
            snapshots[id(commander)] = (
                commander,
                _sleep_surface_snapshot(commander),
            )
            for member, receipt, reserve_units, _, _ in admission:
                write_fatigue_state(
                    member, reserve_units, SleepPosture.VOLUNTARY
                )
                write_sleep_receipt(member, receipt)
                project_fatigue_status(member)
            write_party_operation(commander, operation, body_ids)
            bump_sleep_view_generation(commander)
    except Exception:
        for member, member_snapshots in (snapshots or {}).values():
            _restore_sleep_surfaces(member, member_snapshots)
        raise
    entries = tuple(
        SleepEntry(
            operation_id=operation,
            member=member,
            requested_seconds=accepted,
            handoff_offered=False,
            sleep_id=receipt.sleep_id,
            mode=mode,
            target_tick=receipt.target_tick,
            accepted_seconds=accepted,
            partial=partial,
            receipt=receipt,
        )
        for member, receipt, accepted, partial in planned
    )
    return SleepOutcome(
        None,
        None,
        PARTY_SLEEP_ACCEPTED_MESSAGE,
        entries=entries,
        receipts=tuple(receipt for _, receipt, _, _ in planned),
    )


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
    "SleepReceipt",
    "SleepRefused",
    "advance_wait",
    "accepted_wait_handoff_offer",
    "all_operable_asleep",
    "authorize_owner_sleep_continuation",
    "begin_sleep",
    "book_member_practice",
    "continue_sleep",
    "continue_owner_sleep",
    "decline_owner_sleep_dream",
    "enter_party_sleep",
    "enter_sleep",
    "owner_sleep_view_state",
    "parse_duration",
    "preflight_practice_booking",
    "read_sleep_receipt",
    "record_owner_sleep_decision",
    "rejection_message",
    "render_handoff_offer_message",
    "render_skip_summary",
    "resume_pending_owner_continuation",
    "seconds_to_full_regen",
    "seconds_to_natural_wake",
    "unsafe_rejection",
]
