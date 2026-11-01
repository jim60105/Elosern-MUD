"""Orchestrate one whole-party camp for both transports (wilderness-camping).

The browser ``explore.camp`` adapter and the text ``camp`` alias share this
single operation: the read-only preflight, the atomic party entry with the
owner's dream answer (enter on explicit opt-in, otherwise an explicit
decline), then either the existing dream stage or the camp continuation to
the slowest selected wake. Every state change happens in
``world.rules.camping`` and the rules owners it delegates to; this service
never writes physiology, receipts or the clock itself.

``operation_id`` is the transport-derived identity (see
:func:`operation_identity`): a repeated identity replays the stored camp and
never settles time again.
"""

import hashlib
import json
from typing import Any
from uuid import uuid4

from world.observability import log_error, log_info

DREAM_PENDING_MESSAGE = "你進入了夢境；隊伍的睡眠會在夢境結束後繼續。"
CODE_CAMP_PENDING = "camp_pending"
CAMP_PENDING_MESSAGE = "上一次紮營的夢境尚未結束。"


def _dream_open(commander: Any) -> bool:
    """Whether the owner's associated dream session is still open."""
    from world.narrative import dream_session as lifecycle
    from world.narrative.dream_surface import associated_session

    session = associated_session(commander)
    return session is not None and session.state == lifecycle.STATE_OPEN
_FALLBACK_MESSAGE = "紮營已結束。"


def operation_identity(owner_dbid: int, *parts: Any) -> str:
    """The SHA-256 hex camp identity of an unambiguously serialized tuple.

    The browser passes ``(owner_dbid, presentation_epoch, request_id)``, text
    ``(owner_dbid, uuid4 hex)``, so two owners or a retired/reconnected epoch
    can never collide on a locally repeated request id.
    """
    payload = json.dumps([int(owner_dbid), *[str(part) for part in parts]], ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def text_operation_identity(owner_dbid: int) -> str:
    """A fresh text-command camp identity."""
    return operation_identity(owner_dbid, uuid4().hex)


def _boundary(commander: Any, *, camp_id: str, mode: str, dream: bool) -> dict[str, Any]:
    from world.rules.camping import read_tick

    location = getattr(commander, "location", None)
    return {
        "char": int(commander.pk),
        "room": getattr(location, "pk", None),
        "tick": read_tick(),
        "camp_id": camp_id,
        "mode": mode,
        "dream": bool(dream),
    }


def _message(commander: Any, data: dict[str, Any]) -> str:
    from world.rules.sleep_receipt import read_camp_operation

    if data.get("phase") == "dream":
        return DREAM_PENDING_MESSAGE
    meta = read_camp_operation(commander)
    if meta is not None and meta["event"] is not None:
        return str(meta["event"]["text"])
    return _FALLBACK_MESSAGE


def camp(
    actor: Any,
    *,
    mode: str,
    dream: bool,
    operation_id: str,
    seconds: int | None = None,
    session: Any = None,
) -> dict[str, Any]:
    """Run one camp; returns ``{"data": <camp result>, "message": str}``.

    ``mode`` is the wire mode (``until-dawn``/``until-recovered``) or, for the
    text alias's explicit duration, ``duration`` with ``seconds``. A refusal
    raises the shared ``SleepRefused``/``SkipRefused`` before any write; true
    when the dream is not offerable refuses without silently declining. An
    unexpected failure after the entry committed keeps the accepted state
    resumable and reports an interrupted result.
    """
    from world.rules.camping import (
        CODE_DREAM_NOT_OFFERABLE,
        DREAM_NOT_OFFERABLE_MESSAGE,
        _commit_entry,
        camp_metadata,
        continue_camp,
        dream_result,
        finalize_camp,
        internal_mode,
        plan_camp,
        reconcile_camp,
    )
    from world.rules.party_scope import resolve_commander
    from world.rules.sleep_receipt import MODE_DURATION, read_camp_operation
    from world.rules.time_skip import INVALID_SLEEP_MODE_MESSAGE, SleepRefused

    if mode == MODE_DURATION:
        internal = MODE_DURATION
    else:
        try:
            internal = internal_mode(mode)
        except KeyError as error:
            raise SleepRefused("invalid_mode", INVALID_SLEEP_MODE_MESSAGE) from error
    if not isinstance(dream, bool):
        raise SleepRefused("invalid_mode", INVALID_SLEEP_MODE_MESSAGE)
    commander = resolve_commander(actor)
    stored = read_camp_operation(commander)
    if stored is not None and stored["camp_id"] == operation_id:
        # A replayed request: the stored result, or the retained progress.
        if stored["result"] is not None:
            data = finalize_camp(commander)
        elif stored["dream"]:
            # A dream that already closed but whose reconciliation did not
            # finish is reconciled now; an open dream stays pending.
            data = reconcile_camp(commander) or dream_result(commander)
        else:
            data = continue_camp(commander, camp_id=operation_id)
        return {"data": data, "message": _message(commander, data)}
    if stored is not None and stored["result"] is None and stored["dream"] and _dream_open(commander):
        # The earlier camp's dream is still open: its departure owns the
        # rest of that camp, so a new camp waits instead of cutting it off.
        raise SleepRefused(CODE_CAMP_PENDING, CAMP_PENDING_MESSAGE)
    plan = plan_camp(actor, mode=internal, seconds=seconds)
    if dream and not plan["dream_offerable"]:
        raise SleepRefused(CODE_DREAM_NOT_OFFERABLE, DREAM_NOT_OFFERABLE_MESSAGE)
    if stored is not None and stored["result"] is None:
        # An earlier camp that never finished is closed with its own
        # truthful result before a new one replaces its record.
        finalize_camp(commander, reason="continuation_failed")
    _commit_entry(
        actor,
        scope="party",
        mode=internal,
        seconds=seconds,
        answer="enter" if dream else "decline",
        operation_id=operation_id,
        session=session,
        camp=camp_metadata(camp_id=operation_id, mode=internal, dream=dream),
    )
    log_info(
        "camp_entry",
        context=_boundary(commander, camp_id=operation_id, mode=internal, dream=dream),
    )
    if dream:
        data = dream_result(commander)
        return {"data": data, "message": DREAM_PENDING_MESSAGE}
    try:
        data = continue_camp(commander, camp_id=operation_id)
    except Exception as error:
        log_error(
            "camp_continuation_failed",
            context=_boundary(commander, camp_id=operation_id, mode=internal, dream=dream),
            exc=error,
        )
        data = finalize_camp(commander, reason="continuation_failed")
    return {"data": data, "message": _message(commander, data)}


__all__ = [
    "DREAM_PENDING_MESSAGE",
    "camp",
    "operation_identity",
    "text_operation_identity",
]
