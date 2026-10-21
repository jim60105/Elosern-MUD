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
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from django.db import transaction

from world.observability import log_info
from world.rules.clock import (
    AdvanceSource,
    CLOCK_YAML,
    ScheduledEvent,
    get_world_clock,
)
from world.rules.party_scope import (
    PURPOSE_ACT,
    authorize_member,
    party_in_combat,
    present_party_scope,
    resolve_commander,
)
from world.rules.progression import proficiency_cap, skill_proficiency_level
from world.rules.skip_safety import SkipRejectReason, evaluate_skip_safety
from world.rules.traits import GAUGE_KEYS
from world.rules.unlock_notices import PRACTICE_UNLOCK_EVENT
from world.skills.registry import SKILL_REGISTRY, SkillKind


class DurationParseError(ValueError):
    """Raised for an explicit rest duration with unsupported syntax."""


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


BOOKING_IN_COMBAT_MESSAGE = "戰鬥中無法排入修煉。"
_BOOKING_MESSAGE = "{member}將在下次休息時修煉「{skill}」。"


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
    """Return the bounded seconds to fully regenerate every gauge."""
    seconds = 0
    for key in GAUGE_KEYS:
        gauge = getattr(entity.traits, key)
        rate = float(getattr(gauge, "rate", 0))
        if rate > 0 and gauge.value < gauge.max:
            seconds = max(seconds, math.ceil((gauge.max - gauge.value) / rate))
    return min(seconds, CLOCK_YAML["max_sleep_seconds"])


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


def advance_skip(
    actor: Any, seconds: int, *, practice_skill: str | None = None
) -> list[ScheduledEvent]:
    """Advance the world clock exactly like ``rest``/``sleep``/``wait``.

    ``seconds`` must already be safe and validated; this call performs the
    single ``AdvanceSource.SKIP`` advance and returns the settled events.
    The settled scope is the acting commander's present party
    (``present_party_scope``), so a companion resting in the same room
    regenerates, expires buffs, and settles its own practice booking in the
    same advance (party-rest-move-settlement). A companion in another room is
    never settled. Scope resolution happens before any booking write, so an
    authority refusal cannot half-apply the declaration.
    A declared skill must pass ``preflight_practice_booking`` before entry.
    A declared skill replaces the caller's standing booking before the
    advance; an unlabeled skip writes no booking and leaves every member's
    standing booking for the clock's practice settlement, which stays the
    sole progression writer. A failed combined book-and-skip restores the
    caller's previous booking, while a failed unlabeled skip is restored by
    the clock's own snapshot.
    """
    entities = present_party_scope(actor)
    previous_booking = None
    if practice_skill is not None:
        previous_booking = actor.db.practice_booking
        actor.db.practice_booking = practice_skill
    try:
        return get_world_clock().advance(seconds, AdvanceSource.SKIP, entities)
    except Exception:
        # Clock rollback already restored its entry snapshot, which contains
        # this declaration; restoring the previous booking here keeps a failed
        # combined book-and-skip from leaving a declaration behind.
        if practice_skill is not None:
            actor.db.practice_booking = previous_booking
        raise


__all__ = [
    "BOOKING_IN_COMBAT_MESSAGE",
    "DAYPARTS",
    "DurationParseError",
    "MAX_SKIP_SECONDS",
    "MAX_WEB_SKIP_SECONDS",
    "PracticeBooking",
    "PracticeReject",
    "PracticeRejectReason",
    "advance_skip",
    "book_member_practice",
    "parse_duration",
    "preflight_practice_booking",
    "rejection_message",
    "render_skip_summary",
    "seconds_to_full_regen",
    "unsafe_rejection",
]
