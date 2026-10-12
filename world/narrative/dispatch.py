"""Durable dream-dispatch work: one record per confirmed request version.

This module owns the mutable execution state of a confirmed dream direction.
The confirmed direction itself stays immutable in
:class:`~world.narrative.models.CreativeRequest`; everything the background pump
needs to claim, checkpoint, publish, recover or exhaust one request lives in
:class:`~world.narrative.models.DreamDispatch`.

Determinism and durability rules implemented here:

* **Identity is a constraint, not a scan.** ``submission_key`` is
  database-unique, so a duplicate confirmation, a reconnect replay or a stale
  callback can only ever find the one existing work record.
* **A notification is a hint.** :func:`notify_pump` wakes the composed pump; the
  row is authoritative, so a lost hint costs a delay, never the request.
* **Every write is fenced.** A checkpoint, a settlement or a terminal reason
  compares both the per-execution ``execution_token`` and the owning
  ``claimed_by`` process fence, so an interrupted, superseded or post-shutdown
  callback mutates nothing.
* **Recovery is exclusive and never a reroll.** :func:`recover_interrupted`
  invalidates a previous process's unfinished claim under the current process's
  exclusive ownership; a terminal failure is never silently regenerated, while a
  player may confirm a new reviewed version normally.
* **No clock charge.** Nothing here advances game time or awaits a model; the
  caller runs the model stage outside every transaction.

The module imports no generated content and no capability registry: the pump
passes an injected capability predicate in, so this file stays deterministic.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable, Mapping
from typing import Any, Optional
from uuid import uuid4

from django.db import IntegrityError, transaction

from world.narrative.models import CreativeRequest, DreamDispatch
from world.observability import log_info, log_warn

# Work states. A row is in exactly one, and `arranged`/`failed` are terminal.
STATE_QUEUED = "queued"
STATE_GENERATING_STORY = "generating_story"
STATE_GENERATING_SCENE = "generating_scene"
STATE_PUBLISHING = "publishing"
STATE_WAITING_SERVICE = "waiting_service"
STATE_ARRANGED = "arranged"
STATE_FAILED = "failed"

TERMINAL_STATES = frozenset({STATE_ARRANGED, STATE_FAILED})
# Every state a pump may consider on its next pass, in no particular order: the
# queue order is the durable confirmation sequence (ascending primary key).
CONSIDERED_STATES = frozenset(
    {
        STATE_QUEUED,
        STATE_WAITING_SERVICE,
        STATE_GENERATING_STORY,
        STATE_GENERATING_SCENE,
        STATE_PUBLISHING,
    }
)

# The stage currently in flight, or the next stage to run.
STAGE_STORY = "story"
STAGE_SCENE = "scene"
STAGE_PUBLISH = "publish"

CAPABILITY_STORY = "story_director"
CAPABILITY_SCENE = "scenario_director"
CAPABILITY_BY_STAGE: dict[str, str] = {
    STAGE_STORY: CAPABILITY_STORY,
    STAGE_SCENE: CAPABILITY_SCENE,
}

# Structured, bounded reasons. ``no_capability`` is the only waiting reason; the
# rest are terminal and map to distinct player-facing messages.
REASON_NO_CAPABILITY = "no_capability"
REASON_STALE_SOURCE = "stale_source"
REASON_MODEL_UNAVAILABLE = "model_unavailable"
REASON_INVALID_OUTPUT = "invalid_output"
REASON_UNSUPPORTED_EFFECT = "unsupported_effect"
REASON_INSUFFICIENT_ARRANGEMENT = "insufficient_arrangement"
REASON_CONFLICT = "conflict"
REASON_PUBLICATION_FAILED = "publication_failed"
REASON_EXECUTION_FAILED = "execution_failed"

REASONS = frozenset(
    {
        REASON_NO_CAPABILITY,
        REASON_STALE_SOURCE,
        REASON_MODEL_UNAVAILABLE,
        REASON_INVALID_OUTPUT,
        REASON_UNSUPPORTED_EFFECT,
        REASON_INSUFFICIENT_ARRANGEMENT,
        REASON_CONFLICT,
        REASON_PUBLICATION_FAILED,
        REASON_EXECUTION_FAILED,
    }
)

# Director settlement outcomes -> durable dispatch reasons.
REASON_BY_OUTCOME: dict[str, str] = {
    "no_content": REASON_INSUFFICIENT_ARRANGEMENT,
    "invalid_proposal": REASON_INVALID_OUTPUT,
    "unsupported_effect": REASON_UNSUPPORTED_EFFECT,
    "unauthorized_write": REASON_INVALID_OUTPUT,
    "unsupported_target": REASON_UNSUPPORTED_EFFECT,
    "stale": REASON_STALE_SOURCE,
    "thread_unavailable": REASON_STALE_SOURCE,
    "conflict": REASON_CONFLICT,
}

MAX_TOKEN_LENGTH = 64
MAX_PROCESS_LENGTH = 64


class DispatchError(Exception):
    """Base exception for dream-dispatch work records."""


class DispatchTokenStale(DispatchError):
    """A (possibly late) write did not hold the work's current execution fence."""


class PumpNotRegistered(DispatchError):
    """A notification arrived while no pump is composed."""


_PUMP: Optional[Callable[[], None]] = None
_PROCESS: Optional[str] = None


def process_identity() -> str:
    """This game-server process's fence identity, created once per process.

    Every claim records it, so a later process can fence an interrupted claim
    without racing a live model call: only the process that owns the row may
    write to it.
    """
    global _PROCESS
    if _PROCESS is None:
        _PROCESS = f"{uuid4().hex[:24]}"
    return _PROCESS


def new_execution_token() -> str:
    """A fresh per-execution token; a claim's writes must carry it."""
    return uuid4().hex


def dispatch_id_for(submission_key: Any) -> str:
    """The deterministic work identity of one confirmed request version."""
    key = str(submission_key).strip()
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return f"dispatch:{digest[:48]}"


def register_pump(callback: Optional[Callable[[], None]]) -> None:
    """Install (or clear) the composed pump's wake-up callback.

    Composition does this at the game-server boundary; a portal or a bare unit
    test registers nothing, and every notification then becomes a documented
    no-op. The callback is only ever a hint, so this seam never owns identity.
    """
    global _PUMP
    _PUMP = callback


def notify_pump() -> bool:
    """Wake the composed pump. Returns whether a pump was registered."""
    callback = _PUMP
    if callback is None:
        return False
    callback()
    return True


def pump_registered() -> bool:
    """Whether a pump is currently composed (tests and composition assert this)."""
    return _PUMP is not None


def _announce(event: str, boundary: Mapping[str, Any]) -> None:
    payload = dict(boundary)
    transaction.on_commit(lambda: log_info(event, context=payload))


# -- creation ------------------------------------------------------------------


def create_or_get_work(
    request: CreativeRequest, *, tick: int = 0, process: Optional[str] = None
) -> DreamDispatch:
    """Create the unique work record for one confirmed request, or return it.

    Called inside the confirmation transaction, so the request, the work record
    and the session closure commit or roll back together. The unique
    ``submission_key`` constraint is the real identity guarantee: a concurrent
    creation loses the race and reads back the winner's row.
    """
    submission_key = str(request.submission_key).strip()
    if not submission_key:
        raise DispatchError("a dispatch work record requires a submission key.")
    owner_id = str(request.owner_id).strip()
    handle = dispatch_id_for(submission_key)
    fence = process or process_identity()
    try:
        with transaction.atomic():
            work, created = DreamDispatch.objects.get_or_create(
                submission_key=submission_key,
                defaults={
                    "dispatch_id": handle,
                    "owner_id": owner_id,
                    "draft_id": str(getattr(request, "draft_id", "") or ""),
                    "request_version": int(request.version),
                    "source_key": submission_key,
                    "state": STATE_QUEUED,
                    "tick": int(tick),
                },
            )
    except IntegrityError:
        work = DreamDispatch.objects.filter(submission_key=submission_key).first()
        if work is None:
            raise
        created = False
    if created:
        _announce(
            "dream_dispatch_confirmed",
            {
                "dispatch": work.dispatch_id,
                "request": submission_key,
                "owner": owner_id,
                "version": int(request.version),
                "work_state": work.state,
                "process": fence,
                "tick": int(tick),
            },
        )
    return work


def find_work(dispatch_id: Any) -> Optional[DreamDispatch]:
    """The work record for one dispatch identity, or ``None``."""
    clean = str(dispatch_id).strip()
    if not clean:
        return None
    return DreamDispatch.objects.filter(dispatch_id=clean).first()


def find_by_submission(submission_key: Any) -> Optional[DreamDispatch]:
    """The work record for one confirmed request version, or ``None``."""
    clean = str(submission_key).strip()
    if not clean:
        return None
    return DreamDispatch.objects.filter(submission_key=clean).first()


def work_for_owner(owner_id: Any) -> list[DreamDispatch]:
    """The owner's work records in durable confirmation order (indexed read)."""
    clean = str(owner_id).strip()
    if not clean:
        return []
    return list(DreamDispatch.objects.filter(owner_id=clean).order_by("id"))


def latest_status(owner_id: Any) -> Optional[DreamDispatch]:
    """The owner's most recently confirmed non-terminal work, else the newest.

    A reconnect reads this: latest status plus the authoritative scene. The
    durable record, not a notice, is the truth.
    """
    ordered = work_for_owner(owner_id)
    if not ordered:
        return None
    for work in reversed(ordered):
        if work.state not in TERMINAL_STATES:
            return work
    return ordered[-1]


# -- queue and claim -----------------------------------------------------------


def pending_stage(work: DreamDispatch) -> Optional[str]:
    """The next stage for one work record, or ``None`` when it is terminal.

    Derived from the durable checkpoints, so a restart recomputes exactly the
    same next stage the interrupted execution was about to run.
    """
    if work.state in TERMINAL_STATES:
        return None
    story = work.story_checkpoint or None
    if not story:
        return STAGE_STORY
    if story.get("scene_required"):
        if not work.scene_checkpoint:
            return STAGE_SCENE
    return STAGE_PUBLISH


def required_capability(work: DreamDispatch) -> Optional[str]:
    """The configured capability the work's next stage needs, if any."""
    stage = pending_stage(work)
    return CAPABILITY_BY_STAGE.get(stage) if stage else None


def next_considered(process: Optional[str] = None) -> list[DreamDispatch]:
    """Every non-terminal work record in stable confirmation order."""
    return list(
        DreamDispatch.objects.filter(state__in=CONSIDERED_STATES).order_by("id")
    )


def claim(work: DreamDispatch, *, process: Optional[str] = None, tick: int = 0) -> Optional[tuple[DreamDispatch, str]]:
    """Claim one work record for one execution, or return ``None``.

    The claim is a short transaction that re-reads the row, refuses a terminal
    one, and writes a fresh execution token plus the current process fence. The
    returned token is the only key that may checkpoint or settle this work, so a
    previous execution's late callback can never mutate it.
    """
    fence = process or process_identity()
    stage = pending_stage(work)
    if stage is None:
        return None
    token = new_execution_token()
    with transaction.atomic():
        row = (
            DreamDispatch.objects.select_for_update()
            .filter(pk=work.pk)
            .first()
        )
        if row is None or row.state in TERMINAL_STATES:
            return None
        expected = pending_stage(row)
        if expected is None:
            return None
        row.execution_token = token
        row.claimed_by = fence
        row.stage = expected
        row.state = _state_for_stage(expected)
        row.attempts = int(row.attempts) + 1
        row.tick = int(tick) if tick else int(row.tick)
        row.save(
            update_fields=[
                "execution_token",
                "claimed_by",
                "stage",
                "state",
                "attempts",
                "tick",
                "updated_at",
            ]
        )
    _announce(
        "dream_dispatch_claimed",
        {
            "dispatch": row.dispatch_id,
            "owner": row.owner_id,
            "work_state": row.state,
            "stage": row.stage,
            "process": fence,
            "attempt": int(row.attempts),
            "tick": int(row.tick),
        },
    )
    return row, token


def _state_for_stage(stage: str) -> str:
    return {
        STAGE_STORY: STATE_GENERATING_STORY,
        STAGE_SCENE: STATE_GENERATING_SCENE,
        STAGE_PUBLISH: STATE_PUBLISHING,
    }[stage]


def _fenced(
    work: DreamDispatch, token: str, fence: Optional[str]
) -> Optional[DreamDispatch]:
    """Re-read the row and return it only when the execution fence still holds."""
    row = DreamDispatch.objects.filter(pk=work.pk).first()
    if row is None or row.state in TERMINAL_STATES:
        return None
    if not token or row.execution_token != token:
        return None
    if fence is not None and row.claimed_by != fence:
        return None
    return row


def _stale(work: DreamDispatch, token: str, action: str) -> None:
    log_warn(
        "dream_dispatch_write_stale",
        context={
            "dispatch": work.dispatch_id,
            "owner": work.owner_id,
            "work_state": work.state,
            "action": action,
        },
    )


def checkpoint_story(
    work: DreamDispatch,
    token: str,
    *,
    checkpoint: Mapping[str, Any],
    tick: int = 0,
    process: Optional[str] = None,
) -> bool:
    """Persist the validated story stage output before advancing the stage."""
    payload = dict(checkpoint)
    with transaction.atomic():
        row = _fenced(work, token, process)
        if row is None:
            _stale(work, token, "checkpoint_story")
            return False
        row.story_checkpoint = payload
        row.stage = STAGE_SCENE if payload.get("scene_required") else STAGE_PUBLISH
        row.state = _state_for_stage(row.stage)
        row.tick = int(tick) if tick else int(row.tick)
        row.save(
            update_fields=[
                "story_checkpoint",
                "stage",
                "state",
                "tick",
                "updated_at",
            ]
        )
    return True


def checkpoint_scene(
    work: DreamDispatch,
    token: str,
    *,
    checkpoint: Mapping[str, Any],
    tick: int = 0,
    process: Optional[str] = None,
) -> bool:
    """Persist the validated blueprint before advancing to publication."""
    payload = dict(checkpoint)
    with transaction.atomic():
        row = _fenced(work, token, process)
        if row is None:
            _stale(work, token, "checkpoint_scene")
            return False
        row.scene_checkpoint = payload
        row.stage = STAGE_PUBLISH
        row.state = STATE_PUBLISHING
        row.tick = int(tick) if tick else int(row.tick)
        row.save(
            update_fields=["scene_checkpoint", "stage", "state", "tick", "updated_at"]
        )
    return True


def mark_arranged(
    work: DreamDispatch,
    token: str,
    *,
    decision_id: str,
    thread_id: str,
    beat_id: str,
    package_id: str = "",
    tick: int = 0,
    process: Optional[str] = None,
) -> bool:
    """Record durable publication references and become ``arranged``.

    Runs inside the publication transaction, so the accepted decision, thread
    linkage, scheduled beat, published package and this work state commit
    together: ``arranged`` exists only once every reference is durable.
    """
    with transaction.atomic():
        row = _fenced(work, token, process)
        if row is None:
            _stale(work, token, "mark_arranged")
            return False
        row.decision_id = str(decision_id or "")
        row.thread_id = str(thread_id or "")
        row.beat_id = str(beat_id or "")
        row.package_id = str(package_id or "")
        row.reason_code = ""
        row.stage = ""
        row.state = STATE_ARRANGED
        row.tick = int(tick) if tick else int(row.tick)
        row.save(
            update_fields=[
                "decision_id",
                "thread_id",
                "beat_id",
                "package_id",
                "reason_code",
                "stage",
                "state",
                "tick",
                "updated_at",
            ]
        )
        _announce(
            "dream_dispatch_published",
            {
                "dispatch": row.dispatch_id,
                "owner": row.owner_id,
                "decision": row.decision_id,
                "thread_id": row.thread_id,
                "beat_id": row.beat_id,
                "package": row.package_id,
                "work_state": row.state,
                "tick": int(row.tick),
            },
        )
    return True


def mark_failed(
    work: DreamDispatch,
    token: str,
    reason: str,
    *,
    tick: int = 0,
    process: Optional[str] = None,
) -> bool:
    """Record a bounded terminal reason; a failed direction is never rerolled."""
    code = str(reason) if str(reason) in REASONS else REASON_EXECUTION_FAILED
    with transaction.atomic():
        row = _fenced(work, token, process)
        if row is None:
            _stale(work, token, "mark_failed")
            return False
        row.reason_code = code
        row.stage = ""
        row.state = STATE_FAILED
        row.tick = int(tick) if tick else int(row.tick)
        row.save(
            update_fields=["reason_code", "stage", "state", "tick", "updated_at"]
        )
        _announce(
            "dream_dispatch_failed",
            {
                "dispatch": row.dispatch_id,
                "owner": row.owner_id,
                "reason": code,
                "work_state": row.state,
                "tick": int(row.tick),
            },
        )
    return True


def mark_waiting(
    work: DreamDispatch,
    reason: str = REASON_NO_CAPABILITY,
    *,
    tick: int = 0,
    process: Optional[str] = None,
) -> bool:
    """Record that a required capability is absent; the work stays reconsiderable.

    A waiting record does not block any other eligible source: the pump simply
    moves on to the next record in confirmation order and reconsiders this one on
    startup, configuration activation/reload or a later notification.
    """
    code = str(reason) if str(reason) in REASONS else REASON_NO_CAPABILITY
    fence = process or process_identity()
    with transaction.atomic():
        row = (
            DreamDispatch.objects.select_for_update()
            .filter(pk=work.pk)
            .first()
        )
        if row is None or row.state in TERMINAL_STATES:
            return False
        row.stage = pending_stage(row) or ""
        row.state = STATE_WAITING_SERVICE
        row.reason_code = code
        row.execution_token = ""
        row.claimed_by = fence
        row.tick = int(tick) if tick else int(row.tick)
        row.save(
            update_fields=[
                "stage",
                "state",
                "reason_code",
                "execution_token",
                "claimed_by",
                "tick",
                "updated_at",
            ]
        )
        _announce(
            "dream_dispatch_waiting",
            {
                "dispatch": row.dispatch_id,
                "owner": row.owner_id,
                "reason": code,
                "stage": row.stage,
                "work_state": row.state,
                "process": fence,
                "tick": int(row.tick),
            },
        )
    return True


def recover_interrupted(
    *, process: Optional[str] = None, tick: int = 0
) -> list[str]:
    """Fence a previous process's unfinished claims under exclusive ownership.

    Called once at game-server startup, after registrations and restoration are
    ready. Every non-terminal record whose claim belongs to another process (or
    to an execution whose token never settled) is re-armed: the stale token is
    invalidated, the row keeps its stage and its saved checkpoints, and the pump
    will re-run only its still-uncommitted stage. A committed result is never
    regenerated because an ``arranged`` row is terminal and untouched.
    """
    fence = process or process_identity()
    recovered: list[str] = []
    for work in next_considered():
        if work.claimed_by == fence and work.execution_token:
            # A claim owned by this live process is still running; never race it.
            continue
        with transaction.atomic():
            row = (
                DreamDispatch.objects.select_for_update()
                .filter(pk=work.pk)
                .first()
            )
            if row is None or row.state in TERMINAL_STATES:
                continue
            previous = row.execution_token
            row.execution_token = ""
            row.claimed_by = fence
            row.state = STATE_QUEUED
            row.reason_code = ""
            row.tick = int(tick) if tick else int(row.tick)
            row.save(
                update_fields=[
                    "execution_token",
                    "claimed_by",
                    "state",
                    "reason_code",
                    "tick",
                    "updated_at",
                ]
            )
            recovered.append(row.dispatch_id)
            _announce(
                "dream_dispatch_recovered",
                {
                    "dispatch": row.dispatch_id,
                    "owner": row.owner_id,
                    "work_state": row.state,
                    "stage": row.stage,
                    "previous_token": bool(previous),
                    "process": fence,
                    "tick": int(row.tick),
                },
            )
    return recovered


def consider_waiting(*, process: Optional[str] = None) -> int:
    """Re-arm every waiting record for reconsideration (startup/config/reload).

    Nothing generates here; the pump's capability check decides on the next pass
    whether a waiting record has become eligible.
    """
    fence = process or process_identity()
    count = 0
    for work in list(
        DreamDispatch.objects.filter(state=STATE_WAITING_SERVICE).order_by("id")
    ):
        with transaction.atomic():
            row = (
                DreamDispatch.objects.select_for_update()
                .filter(pk=work.pk)
                .first()
            )
            if row is None or row.state != STATE_WAITING_SERVICE:
                continue
            row.state = STATE_QUEUED
            row.reason_code = ""
            row.claimed_by = fence
            row.save(update_fields=["state", "reason_code", "claimed_by", "updated_at"])
            count += 1
    return count


def release_claim(
    work: DreamDispatch, token: str, *, process: Optional[str] = None
) -> bool:
    """Invalidate one execution's ownership without changing its progress.

    Shutdown calls this for an in-flight execution so a late callback from it
    cannot write: the stored token is cleared, and every later fenced write with
    that token is refused.
    """
    with transaction.atomic():
        row = (
            DreamDispatch.objects.select_for_update()
            .filter(pk=work.pk)
            .first()
        )
        if row is None or row.state in TERMINAL_STATES:
            return False
        if token and row.execution_token != token:
            return False
        row.execution_token = ""
        row.save(update_fields=["execution_token", "updated_at"])
    return True


def fence_all(process: Optional[str] = None) -> int:
    """Invalidate every outstanding claim (server shutdown).

    Stopping the pump stops new claims via the pump's own flag; this call makes
    the invalidation durable, so an unfinished callback that outlives the stop
    cannot mutate work, publication or dialogue.
    """
    fence = process or process_identity()
    count = 0
    for work in next_considered():
        if not work.execution_token:
            continue
        with transaction.atomic():
            row = (
                DreamDispatch.objects.select_for_update()
                .filter(pk=work.pk)
                .first()
            )
            if row is None or not row.execution_token:
                continue
            row.execution_token = ""
            row.claimed_by = fence
            row.save(update_fields=["execution_token", "claimed_by", "updated_at"])
            count += 1
    return count


def summarize(works: Iterable[DreamDispatch]) -> dict[str, int]:
    """Counts per state; the cheap shape a test or a status read asserts."""
    counts: dict[str, int] = {}
    for work in works:
        counts[work.state] = counts.get(work.state, 0) + 1
    return counts
