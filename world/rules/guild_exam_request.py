"""Presence-first guild examination requests (guild-exam-appointment-surface).

``request_guild_exam`` is the single request coordinator shared by the text
command, the WebClient ``guild.exam_request`` action and the validated
``request_guild_exam`` NPC intent. Its decision order is fixed (design
2026-10-08 §7.2):

1. Resolve the actor's registration, the local examination counter (or the
   speaking NPC's server-validated counter/direct-host access), the branch,
   the exact next-rank target and the branch-qualified persistent host. No
   merit, battle or host-service check happens here.
2. Inspect the host's actual presence at the counter's room.
3. An absent host yields read-only planned attendance from
   ``world.rules.service_windows`` -- or a named inability to confirm it --
   with zero writes: no attempt, resources, affinity, hold or session.
4. A present host delegates to ``start_guild_exam``, which revalidates every
   authoritative gate (host service state, true merit, active battle/exam)
   and is the only mutation-capable start.

No reservation, queue, wait, summon or automatic start exists: an
``exam_schedule`` outcome is information, never a booking.

The module name is deliberately singular: the guild-economy import guard
(``world/rules/tests/test_guild_economy_guards.py``) rejects the substring
``requests`` in the command modules that import it.
"""

from dataclasses import dataclass
from typing import Any

from typeclasses.characters import PlayerCharacter
from world.observability import log_debug
from world.rules.guild_exams import (
    ExamReason,
    GuildExamError,
    GuildExamRecord,
    resolve_exam_request_target,
    start_guild_exam,
)
from world.rules.service_windows import (
    PlannedServiceInterval,
    read_next_planned_service_interval,
)

OUTCOME_SCHEDULE = "exam_schedule"
OUTCOME_STARTED = "exam_started"


@dataclass(frozen=True)
class ExamRequestOutcome:
    """The successful result of one examination request.

    ``kind`` is ``exam_schedule`` (planned attendance information; nothing
    was written) or ``exam_started`` (the authoritative start committed).
    ``interval`` is set only for a schedule outcome and ``record`` only for
    a started examination.
    """

    kind: str
    target_rank: str
    host_name: str
    interval: PlannedServiceInterval | None = None
    record: GuildExamRecord | None = None


def request_guild_exam(
    actor: Any,
    target_rank: str,
    *,
    speaker: Any = None,
    requested_by: str,
) -> ExamRequestOutcome:
    """Answer one exam request: planned attendance or an authoritative start.

    ``speaker`` is the NPC voicing a ``request_guild_exam`` intent; it grants
    no authority beyond being the co-located counter or the qualified host.
    Raises :class:`GuildExamError` with a stable :class:`ExamReason` for every
    rejection; a rejected request leaves canonical state untouched.
    """
    if not isinstance(actor, PlayerCharacter):
        raise GuildExamError(ExamReason.NOT_A_PLAYER)
    target = resolve_exam_request_target(actor, target_rank, speaker=speaker)
    host = target.host
    room = target.counter.location
    if host.location is None or room is None or host.location.pk != room.pk:
        window = read_next_planned_service_interval(host, room)
        if window.interval is None:
            log_debug(
                "guild_exam_request_attendance_unknown",
                context={
                    "char": actor.pk, "host": host.pk, "branch": target.branch_key,
                    "target": target_rank, "reason": window.reason,
                },
            )
            raise GuildExamError(ExamReason.ATTENDANCE_UNKNOWN, window.reason)
        log_debug(
            "guild_exam_request_scheduled",
            context={
                "char": actor.pk, "host": host.pk, "branch": target.branch_key,
                "target": target_rank, "start": window.interval.start_tick,
                "end": window.interval.end_tick, "requested_by": requested_by,
            },
        )
        return ExamRequestOutcome(
            kind=OUTCOME_SCHEDULE,
            target_rank=target_rank,
            host_name=str(host.key),
            interval=window.interval,
        )
    record = start_guild_exam(
        actor, host, target_rank, requested_by=requested_by, counter=target.counter
    )
    return ExamRequestOutcome(
        kind=OUTCOME_STARTED,
        target_rank=record.target_rank,
        host_name=str(host.key),
        record=record,
    )


def next_exam_rank(actor: Any) -> str | None:
    """Return the actor's exact next rank key, or ``None`` at the top rank."""
    from world.lore.guild import GUILD_RANK_REGISTRY

    rank = GUILD_RANK_REGISTRY.get(getattr(actor, "guild_rank", None))
    if rank is None:
        return None
    return next(
        (member.key for member in GUILD_RANK_REGISTRY.values() if member.order == rank.order + 1),
        None,
    )


__all__ = [
    "OUTCOME_SCHEDULE",
    "OUTCOME_STARTED",
    "ExamRequestOutcome",
    "next_exam_rank",
    "request_guild_exam",
]
