"""Durable six-exchange dream collaboration session accounting.

This module owns the W3 dream-session boundary: the durable record of a
collaborative dream conversation, its six-exchange budget, and the
deterministic confirm/draft/awaken choices. It stores identifiers, counts and
references only — never generated prose, never explicit content, and never a
sleep settlement. Opening the dream, presenting the scene and advancing the
server-computed arousal track belong to other capabilities; this module imports
nothing from ``world.ai`` and opens no transport, so every operation works with
all generation services offline.

Budget semantics (design section 6.3)
-------------------------------------

- One exchange is one player message plus one successfully delivered validated
  response. :func:`begin_turn` records the player message and its identity but
  consumes nothing; only :func:`settle_exchange`, given a delivery identity
  already committed to a recoverable response record, increments the persisted
  count and appends an immutable
  :class:`~world.narrative.models.DreamExchange`.
- The count is capped at six and never reset by reconnect
  (:func:`open_session_for` returns the same durable row). Opening text,
  confirmation actions, transport failures, validation retries, abandoned turns
  and duplicate submissions never consume an exchange.
- Rendered input has its own independent hard bound
  (:data:`MAX_RENDERED_INPUT_CHARS`) applied before any state change, so one
  oversized message cannot bypass the session budget.
- Exchange five begins convergence; exchange six summarizes and closes free
  text. This module owns counting and the availability of the choices; the
  presentation capability owns what the converging and summarizing responses
  must say.
- :func:`preserve_draft` and :func:`confirm_session` are deterministic and
  available even while a pending turn is failing; :func:`confirm_session`
  delegates validation and single submission to ``world.narrative.authoring``,
  and :func:`awaken_session` closes the session without any model call.

Accounting durability
---------------------

- :func:`settle_exchange` is idempotent by ``delivery_id`` (restart replay) and
  by ``(session, submission_id)`` (duplicate submission); both return the
  existing row without a second increment. Idempotency does not depend on the
  row lock (SQLite ignores ``select_for_update``): the unique constraints are
  the durable backstop, and an ``IntegrityError`` race resolves to the row that
  won it.
- The session count never advances further than the durable exchange rows,
  because the exchange insert and the count update commit in one transaction.
- A failed or abandoned turn releases the pending slot through
  :func:`abandon_turn` while keeping ``saved_input`` recoverable; the terminal
  choices and awakening clear the pending slot.

Boundary events carry session/submission/delivery identifiers, counts, ticks and
stable reason codes only. Player prose, direction summaries and reason messages
never enter logs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional
from uuid import uuid4

from django.db import IntegrityError, transaction

from world.narrative.authoring import (
    AuthoringDraft,
    CreativeRequest,
    confirm_draft,
    get_request,
    save_draft,
)
from world.narrative.models import DreamExchange, DreamSession
from world.observability import log_info, log_warn

# One exchange is one player message plus one successfully delivered validated
# response; the session is capped at six and exchange five begins convergence.
MAX_EXCHANGES = 6
CONVERGENCE_EXCHANGE = 5
# The ingress bound owned here: the rendered player message accepted per turn,
# inclusive. The model-side rendered-response bound belongs to the presentation
# capability and is independent of this one.
MAX_RENDERED_INPUT_CHARS = 4000
MAX_SESSION_ID_LENGTH = 64
MAX_SUBMISSION_ID_LENGTH = 64
MAX_DELIVERY_ID_LENGTH = 160
MAX_RESPONSE_REF_LENGTH = 255
MAX_OWNER_ID_LENGTH = 255
MAX_DRAFT_ID_LENGTH = 128
MAX_REASON_CODE_LENGTH = 64
MAX_TICK = 2**63 - 1

STATE_OPEN = "open"
STATE_ENDED = "ended"
OUTCOME_DRAFT = "draft"
OUTCOME_CONFIRMED = "confirmed"

# Stable rejection reason codes; player-facing prose never enters logs and the
# codes are the identifiers callers and tests assert on.
REASON_EMPTY_INPUT = "empty_input"
REASON_OVERSIZED_INPUT = "oversized_input"
REASON_OUTSTANDING_TURN = "outstanding_turn"
REASON_DIFFERENT_MESSAGE = "different_message"
REASON_CLOSED = "closed"
REASON_AT_CAP = "at_cap"
REASON_NO_OUTSTANDING_TURN = "no_outstanding_turn"
REASON_NOT_DRAFTED = "not_drafted"
REASON_DUPLICATE_DELIVERY = "duplicate_delivery"


class DreamSessionError(Exception):
    """Base exception for dream-session accounting."""


class DreamSessionAccessError(DreamSessionError):
    """Raised when the actor does not own the requested dream session."""


class DreamSessionClosedError(DreamSessionError):
    """Raised when an ended session or the completed cap refuses free text."""


class DreamOutstandingTurnError(DreamSessionError):
    """Raised when a different turn is already outstanding for the session."""


class DreamInputRejected(DreamSessionError):
    """A bounded-input refusal: a stable code, no durable state change."""

    def __init__(self, code: str):
        self.code = str(code)
        super().__init__(f"Dream input rejected: {self.code!r}.")


class DreamExchangeConflictError(DreamSessionError):
    """Raised when a delivery/submission identity does not match the session."""


class DreamSessionNotDraftedError(DreamSessionError):
    """Raised when confirmation is asked for before any direction was drafted."""


class DreamSessionConflictError(DreamSessionError):
    """Raised when a concurrent draft save on the session's handle was lost."""


@dataclass(frozen=True)
class DreamSessionProgress:
    """Deterministic counting view of one session; no model, no side effects."""

    session_id: str
    completed: int
    remaining: int
    converging: bool
    at_cap: bool
    free_text_allowed: bool


@dataclass(frozen=True)
class DreamSessionChoices:
    """Which actions a surface may offer; derived from the durable count only.

    ``can_confirm``/``can_preserve_draft`` are offered for every open session —
    they are the cap and early-departure choices — and ``can_awaken`` is always
    available because ending requires no model call.
    """

    session_id: str
    can_input: bool
    can_confirm: bool
    can_preserve_draft: bool
    can_awaken: bool


@dataclass(frozen=True)
class DreamTurn:
    """One accepted-but-unsettled player turn."""

    session_id: str
    submission_id: str
    message_length: int
    progress: DreamSessionProgress


def _clean_owner(owner_id: Any) -> str:
    clean = str(owner_id).strip()
    if not clean or len(clean) > MAX_OWNER_ID_LENGTH:
        raise DreamSessionAccessError("Unknown dream session.")
    return clean


def _clean_id(
    value: Any,
    *,
    label: str,
    max_length: int,
    error_cls: type[DreamSessionError] = DreamSessionError,
) -> str:
    """Validate an identity at ingress; never truncate and never touch the DB."""
    clean = str(value).strip()
    if not clean or len(clean) > max_length:
        raise error_cls(f"Invalid dream-session {label}.")
    return clean


def _clean_tick(tick: Any) -> int:
    try:
        value = int(tick)
    except (TypeError, ValueError) as error:
        raise DreamSessionError("tick must be an integer.") from error
    if value < 0 or value > MAX_TICK:
        raise DreamSessionError("tick is out of range.")
    return value


def _announce(event: str, boundary: dict[str, Any]) -> None:
    transaction.on_commit(lambda: log_info(event, context=boundary))


def _reject(event: str, *, reason: str, boundary: dict[str, Any]) -> None:
    """Emit a rejection trace synchronously: a rollback skips ``on_commit``."""
    log_warn(event, context={**boundary, "reason": reason})


def _locked_session(session_id: str, owner_id: str) -> DreamSession:
    """Owner-scoped re-read inside the current transaction; the row-lock hint
    is kept for backends that support it (SQLite ignores it and the unique
    constraints below are the real guarantee)."""
    session = (
        DreamSession.objects.select_for_update().filter(session_id=session_id).first()
    )
    if session is None or session.owner_id != owner_id:
        raise DreamSessionAccessError("Unknown dream session.")
    return session


def get_session(session_id: Any, owner_id: Any) -> DreamSession:
    """Owner-scoped read; a foreign or missing session is not visible."""
    clean_owner = _clean_owner(owner_id)
    handle = _clean_id(
        session_id,
        label="session identity",
        max_length=MAX_SESSION_ID_LENGTH,
        error_cls=DreamSessionAccessError,
    )
    session = DreamSession.objects.filter(session_id=handle).first()
    if session is None or session.owner_id != clean_owner:
        raise DreamSessionAccessError("Unknown dream session.")
    return session


def open_session(
    owner_id: Any,
    *,
    session_id: Any = None,
    tick: int = 0,
) -> DreamSession:
    """Create a zero-count open session, or return an existing same-owner one.

    A caller-supplied ``session_id`` is the resume handle, so re-entering with
    the same identity returns the same durable row and never resets the count.
    ``open_session_for`` is the ordinary resume path; use ``list_open_sessions``
    to see every still-open session an owner has.
    """
    clean_owner = _clean_owner(owner_id)
    clean_tick = _clean_tick(tick)
    handle = (
        _clean_id(session_id, label="session identity", max_length=MAX_SESSION_ID_LENGTH)
        if session_id is not None
        else uuid4().hex
    )
    existing = DreamSession.objects.filter(session_id=handle).first()
    if existing is not None:
        if existing.owner_id != clean_owner:
            raise DreamSessionAccessError("Unknown dream session.")
        return existing

    try:
        with transaction.atomic():
            session = DreamSession.objects.create(
                session_id=handle,
                owner_id=clean_owner,
                completed_exchanges=0,
                revision=1,
                state=STATE_OPEN,
                outcome="",
                pending_submission_id="",
                saved_input="",
                draft_id="",
                request_key="",
                created_tick=clean_tick,
            )
    except IntegrityError:
        # A concurrent open won the unique constraint; the first durable row
        # stands and replay returns it.
        log_warn(
            "dream_session_open_raced",
            context={"session_id": handle, "owner": clean_owner, "tick": clean_tick},
        )
        raced = DreamSession.objects.filter(session_id=handle).first()
        if raced is None or raced.owner_id != clean_owner:
            raise DreamSessionAccessError("Unknown dream session.")
        return raced

    _announce(
        "dream_session_opened",
        {"session_id": session.session_id, "owner": clean_owner, "tick": clean_tick},
    )
    return session


def open_session_for(owner_id: Any) -> Optional[DreamSession]:
    """The owner's newest still-open session, or None (the resume read)."""
    return (
        DreamSession.objects.filter(owner_id=_clean_owner(owner_id), state=STATE_OPEN)
        .order_by("-id")
        .first()
    )


def list_open_sessions(owner_id: Any) -> list[DreamSession]:
    """Every still-open session for the owner, in durable creation order."""
    return list(
        DreamSession.objects.filter(
            owner_id=_clean_owner(owner_id), state=STATE_OPEN
        ).order_by("id")
    )


def list_exchanges(session_id: Any, owner_id: Any) -> list[DreamExchange]:
    """The session's delivered exchanges, in durable exchange order."""
    session = get_session(session_id, owner_id)
    return list(
        DreamExchange.objects.filter(session=session).order_by("exchange_number")
    )


def progress(session: DreamSession) -> DreamSessionProgress:
    """The deterministic counting view: completed, remaining and phase flags.

    Convergence begins at exchange five, so a session is converging once its
    upcoming exchange is number five or later (``completed + 1 >= 5``). The cap
    is reached after the sixth exchange; only then does free text stop.
    """
    completed = int(session.completed_exchanges)
    open_state = session.state == STATE_OPEN
    at_cap = completed >= MAX_EXCHANGES
    return DreamSessionProgress(
        session_id=session.session_id,
        completed=completed,
        remaining=max(0, MAX_EXCHANGES - completed),
        converging=completed + 1 >= CONVERGENCE_EXCHANGE,
        at_cap=at_cap,
        free_text_allowed=open_state and not at_cap,
    )


def remaining_exchanges(session: DreamSession) -> int:
    """The count a surface displays as remaining."""
    return progress(session).remaining


def choices(session: DreamSession) -> DreamSessionChoices:
    """The deterministic set of actions the surface may offer."""
    view = progress(session)
    open_state = session.state == STATE_OPEN
    return DreamSessionChoices(
        session_id=session.session_id,
        can_input=view.free_text_allowed,
        can_confirm=open_state,
        can_preserve_draft=open_state,
        can_awaken=True,
    )


def begin_turn(
    session_id: Any,
    owner_id: Any,
    message: Any,
    *,
    submission_id: Any = None,
    tick: int = 0,
) -> DreamTurn:
    """Accept one bounded player message as the single outstanding turn.

    Rejects blank or oversized input before any state change (no generation, no
    budget consumption). A repeated ``submission_id`` with the same message is
    an idempotent retry returning the same identity; a second, different
    identity while one turn is outstanding raises
    :class:`DreamOutstandingTurnError`. Free text is refused once the session is
    ended or the six-exchange budget is complete.
    """
    clean_owner = _clean_owner(owner_id)
    clean_tick = _clean_tick(tick)
    session = get_session(session_id, clean_owner)

    text = "" if message is None else str(message)
    if not text.strip():
        _reject(
            "dream_session_input_rejected",
            reason=REASON_EMPTY_INPUT,
            boundary={
                "session_id": session.session_id,
                "owner": clean_owner,
                "message_length": len(text),
                "tick": clean_tick,
            },
        )
        raise DreamInputRejected(REASON_EMPTY_INPUT)
    if len(text) > MAX_RENDERED_INPUT_CHARS:
        _reject(
            "dream_session_input_rejected",
            reason=REASON_OVERSIZED_INPUT,
            boundary={
                "session_id": session.session_id,
                "owner": clean_owner,
                "message_length": len(text),
                "bound": MAX_RENDERED_INPUT_CHARS,
                "tick": clean_tick,
            },
        )
        raise DreamInputRejected(REASON_OVERSIZED_INPUT)

    handle = (
        _clean_id(
            submission_id,
            label="submission identity",
            max_length=MAX_SUBMISSION_ID_LENGTH,
        )
        if submission_id is not None
        else uuid4().hex
    )

    view = progress(session)
    if not view.free_text_allowed:
        reason = REASON_AT_CAP if view.at_cap else REASON_CLOSED
        _reject(
            "dream_session_closed",
            reason=reason,
            boundary={
                "session_id": session.session_id,
                "owner": clean_owner,
                "completed": view.completed,
                "tick": clean_tick,
            },
        )
        raise DreamSessionClosedError("The dream session is closed to free text.")

    with transaction.atomic():
        locked = _locked_session(session.session_id, clean_owner)
        if locked.state != STATE_OPEN or int(locked.completed_exchanges) >= MAX_EXCHANGES:
            _reject(
                "dream_session_closed",
                reason=REASON_CLOSED,
                boundary={
                    "session_id": locked.session_id,
                    "owner": clean_owner,
                    "completed": int(locked.completed_exchanges),
                    "tick": clean_tick,
                },
            )
            raise DreamSessionClosedError("The dream session is closed to free text.")

        pending = locked.pending_submission_id
        if pending and pending != handle:
            _reject(
                "dream_session_turn_conflict",
                reason=REASON_OUTSTANDING_TURN,
                boundary={
                    "session_id": locked.session_id,
                    "owner": clean_owner,
                    "submission_id": handle,
                    "tick": clean_tick,
                },
            )
            raise DreamOutstandingTurnError("Another dream turn is in flight.")
        if pending == handle and locked.saved_input != text:
            _reject(
                "dream_session_turn_conflict",
                reason=REASON_DIFFERENT_MESSAGE,
                boundary={
                    "session_id": locked.session_id,
                    "owner": clean_owner,
                    "submission_id": handle,
                    "tick": clean_tick,
                },
            )
            raise DreamOutstandingTurnError(
                "Submission identity already belongs to a different message."
            )
        if pending != handle:
            locked.pending_submission_id = handle
            locked.saved_input = text
            locked.revision = int(locked.revision) + 1
            locked.save(
                update_fields=[
                    "pending_submission_id",
                    "saved_input",
                    "revision",
                    "updated_at",
                ]
            )
            _announce(
                "dream_session_submission_accepted",
                {
                    "session_id": locked.session_id,
                    "submission_id": handle,
                    "owner": clean_owner,
                    "completed": int(locked.completed_exchanges),
                    "remaining": max(0, MAX_EXCHANGES - int(locked.completed_exchanges)),
                    "tick": clean_tick,
                },
            )
        return DreamTurn(
            session_id=locked.session_id,
            submission_id=handle,
            message_length=len(text),
            progress=progress(locked),
        )


def settle_exchange(
    session_id: Any,
    owner_id: Any,
    submission_id: Any,
    delivery_id: Any,
    *,
    response_ref: Any = "",
    tick: int = 0,
) -> DreamExchange:
    """Count one delivered validated response, at most once.

    Lookup order is the contract: (1) an existing row for ``delivery_id`` is the
    restart replay and returns it; (2) an existing row for
    ``(session, submission_id)`` is a duplicate submission and returns the first
    delivery without consuming again; (3) the submission must be the outstanding
    turn; (4) the budget must not be complete. The exchange row and the count
    update commit in the same transaction, so the persisted count never
    advances without the durable evidence.
    """
    clean_owner = _clean_owner(owner_id)
    clean_tick = _clean_tick(tick)
    clean_submission = _clean_id(
        submission_id, label="submission identity", max_length=MAX_SUBMISSION_ID_LENGTH
    )
    clean_delivery = _clean_id(
        delivery_id, label="delivery identity", max_length=MAX_DELIVERY_ID_LENGTH
    )
    clean_ref = str(response_ref or "").strip()
    if len(clean_ref) > MAX_RESPONSE_REF_LENGTH:
        raise DreamExchangeConflictError("Invalid delivered response reference.")

    session = get_session(session_id, clean_owner)

    with transaction.atomic():
        locked = _locked_session(session.session_id, clean_owner)

        # (1) Restart replay of the same delivery identity.
        replayed = DreamExchange.objects.filter(delivery_id=clean_delivery).first()
        if replayed is not None:
            if (
                replayed.session_id != locked.pk
                or replayed.owner_id != clean_owner
                or replayed.submission_id != clean_submission
            ):
                _reject(
                    "dream_session_exchange_conflict",
                    reason=REASON_DUPLICATE_DELIVERY,
                    boundary={
                        "session_id": locked.session_id,
                        "owner": clean_owner,
                        "submission_id": clean_submission,
                        "delivery_id": clean_delivery,
                        "tick": clean_tick,
                    },
                )
                raise DreamExchangeConflictError(
                    "Delivery identity already belongs to a different exchange."
                )
            return replayed

        # (2) Duplicate submission: the first delivered response stands and the
        # budget is untouched.
        settled = DreamExchange.objects.filter(
            session=locked, submission_id=clean_submission
        ).first()
        if settled is not None:
            _reject(
                "dream_session_delivery_duplicate",
                reason=REASON_DUPLICATE_DELIVERY,
                boundary={
                    "session_id": locked.session_id,
                    "owner": clean_owner,
                    "submission_id": clean_submission,
                    "delivery_id": clean_delivery,
                    "tick": clean_tick,
                },
            )
            return settled

        # (3) Only the outstanding turn can settle; an ended session has none.
        if (
            locked.state != STATE_OPEN
            or not locked.pending_submission_id
            or locked.pending_submission_id != clean_submission
        ):
            _reject(
                "dream_session_exchange_conflict",
                reason=REASON_NO_OUTSTANDING_TURN,
                boundary={
                    "session_id": locked.session_id,
                    "owner": clean_owner,
                    "submission_id": clean_submission,
                    "tick": clean_tick,
                },
            )
            raise DreamExchangeConflictError(
                "No outstanding dream turn for this submission."
            )

        # (4) The six-exchange cap.
        completed = int(locked.completed_exchanges)
        if completed >= MAX_EXCHANGES:
            _reject(
                "dream_session_closed",
                reason=REASON_AT_CAP,
                boundary={
                    "session_id": locked.session_id,
                    "owner": clean_owner,
                    "completed": completed,
                    "tick": clean_tick,
                },
            )
            raise DreamSessionClosedError("The six-exchange budget is complete.")

        exchange_number = completed + 1
        try:
            with transaction.atomic():
                exchange = DreamExchange.objects.create(
                    delivery_id=clean_delivery,
                    session=locked,
                    owner_id=clean_owner,
                    exchange_number=exchange_number,
                    submission_id=clean_submission,
                    response_ref=clean_ref,
                    tick=clean_tick,
                )
        except IntegrityError:
            # A concurrent settlement won the unique constraint. The winning
            # durable row stands; this call must not count a second exchange.
            log_warn(
                "dream_session_exchange_raced",
                context={
                    "session_id": locked.session_id,
                    "owner": clean_owner,
                    "submission_id": clean_submission,
                    "exchange_number": exchange_number,
                    "tick": clean_tick,
                },
            )
            winner = (
                DreamExchange.objects.filter(
                    session=locked, exchange_number=exchange_number
                ).first()
                or DreamExchange.objects.filter(delivery_id=clean_delivery).first()
            )
            if winner is None:
                raise DreamExchangeConflictError(
                    "Concurrent dream exchange settlement lost the race."
                )
            return winner

        locked.completed_exchanges = exchange_number
        locked.pending_submission_id = ""
        locked.saved_input = ""
        locked.revision = int(locked.revision) + 1
        locked.save(
            update_fields=[
                "completed_exchanges",
                "pending_submission_id",
                "saved_input",
                "revision",
                "updated_at",
            ]
        )
        _announce(
            "dream_session_exchange_completed",
            {
                "session_id": locked.session_id,
                "submission_id": clean_submission,
                "delivery_id": clean_delivery,
                "owner": clean_owner,
                "completed": exchange_number,
                "remaining": max(0, MAX_EXCHANGES - exchange_number),
                "tick": clean_tick,
            },
        )
        return exchange


def abandon_turn(
    session_id: Any,
    owner_id: Any,
    submission_id: Any,
    *,
    reason: str = "",
    tick: int = 0,
) -> DreamSessionProgress:
    """Release the outstanding turn without consuming an exchange.

    Transport failure, cancellation and validation retries call this so the
    single-turn slot is usable again; ``saved_input`` is kept so a re-entry can
    resume the player's unfinished message. Repeating the call for a turn that
    is no longer outstanding is a silent no-op.
    """
    clean_owner = _clean_owner(owner_id)
    clean_tick = _clean_tick(tick)
    clean_submission = _clean_id(
        submission_id, label="submission identity", max_length=MAX_SUBMISSION_ID_LENGTH
    )
    code = str(reason or "").strip() or "unspecified"
    if len(code) > MAX_REASON_CODE_LENGTH:
        raise DreamSessionError("Invalid dream-session reason code.")

    session = get_session(session_id, clean_owner)
    with transaction.atomic():
        locked = _locked_session(session.session_id, clean_owner)
        if locked.pending_submission_id == clean_submission:
            locked.pending_submission_id = ""
            locked.revision = int(locked.revision) + 1
            locked.save(
                update_fields=["pending_submission_id", "revision", "updated_at"]
            )
            _announce(
                "dream_session_turn_abandoned",
                {
                    "session_id": locked.session_id,
                    "owner": clean_owner,
                    "submission_id": clean_submission,
                    "reason": code,
                    "completed": int(locked.completed_exchanges),
                    "tick": clean_tick,
                },
            )
        return progress(locked)


def _save_session_draft(
    session: DreamSession,
    owner_id: str,
    direction: Any,
    sources: Optional[Iterable[Any]],
    tick: int,
) -> AuthoringDraft:
    """Save or update the session's deterministic private draft handle."""
    handle = session.draft_id or f"dream:{session.session_id}"
    if len(handle) > MAX_DRAFT_ID_LENGTH:
        raise DreamSessionError("Invalid dream-session draft identity.")
    try:
        with transaction.atomic():
            return save_draft(
                owner_id=owner_id,
                direction=direction,
                sources=sources,
                tick=tick,
                draft_id=handle,
            )
    except IntegrityError:
        # A concurrent same-handle save lost the unique race; the durable draft
        # row stands. The single-player owner serializes this path, so a lost
        # race is a caller retry, never a lost draft.
        log_warn(
            "dream_session_draft_raced",
            context={
                "session_id": session.session_id,
                "owner": owner_id,
                "draft_id": handle,
                "tick": tick,
            },
        )
        existing = AuthoringDraft.objects.filter(draft_id=handle).first()
        if existing is None or existing.owner_id != owner_id:
            raise DreamSessionConflictError(
                "Concurrent dream draft preservation conflicted."
            )
        return existing


def _record_draft_handle(
    session: DreamSession,
    owner_id: str,
    draft_id: str,
    tick: int,
    *,
    outcome: Optional[str] = None,
) -> DreamSession:
    """Durably attach the preserved draft handle, and optionally the outcome."""
    with transaction.atomic():
        locked = _locked_session(session.session_id, owner_id)
        changed = []
        if locked.draft_id != draft_id:
            locked.draft_id = draft_id
            changed.append("draft_id")
        if outcome is not None and locked.outcome != outcome:
            locked.outcome = outcome
            changed.append("outcome")
        if changed:
            locked.revision = int(locked.revision) + 1
            changed.append("revision")
            changed.append("updated_at")
            locked.save(update_fields=changed)
        return locked


def preserve_draft(
    session_id: Any,
    owner_id: Any,
    direction: Any,
    *,
    sources: Optional[Iterable[Any]] = None,
    tick: int = 0,
) -> AuthoringDraft:
    """Save or update the session's private draft; it schedules nothing.

    Deterministic and offline: it delegates to
    :func:`world.narrative.authoring.save_draft`, creates no
    :class:`~world.narrative.models.CreativeRequest`, and leaves the session
    open and resumable with ``outcome`` marked as a draft.
    """
    clean_owner = _clean_owner(owner_id)
    clean_tick = _clean_tick(tick)
    session = get_session(session_id, clean_owner)
    if session.state != STATE_OPEN:
        _reject(
            "dream_session_closed",
            reason=REASON_CLOSED,
            boundary={
                "session_id": session.session_id,
                "owner": clean_owner,
                "completed": int(session.completed_exchanges),
                "tick": clean_tick,
            },
        )
        raise DreamSessionClosedError("The dream session is closed.")

    draft = _save_session_draft(session, clean_owner, direction, sources, clean_tick)
    _record_draft_handle(
        session, clean_owner, draft.draft_id, clean_tick, outcome=OUTCOME_DRAFT
    )
    _announce(
        "dream_session_draft_preserved",
        {
            "session_id": session.session_id,
            "owner": clean_owner,
            "draft_id": draft.draft_id,
            "revision": int(draft.revision),
            "tick": clean_tick,
        },
    )
    return draft


def confirm_session(
    session_id: Any,
    owner_id: Any,
    *,
    direction: Any = None,
    sources: Optional[Iterable[Any]] = None,
    tick: int = 0,
) -> CreativeRequest:
    """Confirm the session's direction and submit it exactly once.

    ``direction`` may be supplied to save-and-confirm in one step, otherwise the
    session's preserved draft is confirmed. Validation and single submission are
    owned by :func:`world.narrative.authoring.confirm_draft`: an invalid
    direction raises there, leaves the draft unconfirmed and the session open,
    and no request is created. Confirmation requires a preserved draft; asking
    without one raises :class:`DreamSessionNotDraftedError`. Repeating the
    confirmation of an already-confirmed session returns the same durable
    request (the authoring boundary's submit-once guarantee), so reconnect can
    never submit twice.
    """
    clean_owner = _clean_owner(owner_id)
    clean_tick = _clean_tick(tick)
    session = get_session(session_id, clean_owner)
    if session.state != STATE_OPEN:
        if session.outcome == OUTCOME_CONFIRMED and session.request_key:
            return get_request(session.request_key, clean_owner)
        _reject(
            "dream_session_closed",
            reason=REASON_CLOSED,
            boundary={
                "session_id": session.session_id,
                "owner": clean_owner,
                "completed": int(session.completed_exchanges),
                "tick": clean_tick,
            },
        )
        raise DreamSessionClosedError("The dream session is closed.")

    handle = session.draft_id
    if direction is not None:
        draft = _save_session_draft(session, clean_owner, direction, sources, clean_tick)
        handle = _record_draft_handle(
            session, clean_owner, draft.draft_id, clean_tick
        ).draft_id
    if not handle:
        _reject(
            "dream_session_not_drafted",
            reason=REASON_NOT_DRAFTED,
            boundary={
                "session_id": session.session_id,
                "owner": clean_owner,
                "tick": clean_tick,
            },
        )
        raise DreamSessionNotDraftedError(
            "Preserve a draft direction before confirming."
        )

    # Deterministic validation and "submit once" live in the authoring boundary;
    # a refused direction raises DirectionValidationError here and changes no
    # durable state, so the session stays open and unconfirmed.
    request = confirm_draft(draft_id=handle, owner_id=clean_owner, tick=clean_tick)

    with transaction.atomic():
        locked = _locked_session(session.session_id, clean_owner)
        locked.draft_id = handle
        locked.request_key = request.submission_key
        locked.outcome = OUTCOME_CONFIRMED
        locked.state = STATE_ENDED
        locked.pending_submission_id = ""
        locked.saved_input = ""
        locked.revision = int(locked.revision) + 1
        locked.save(
            update_fields=[
                "draft_id",
                "request_key",
                "outcome",
                "state",
                "pending_submission_id",
                "saved_input",
                "revision",
                "updated_at",
            ]
        )
        _announce(
            "dream_session_confirmed",
            {
                "session_id": locked.session_id,
                "owner": clean_owner,
                "draft_id": handle,
                "submission_key": request.submission_key,
                "version": int(request.version),
                "tick": clean_tick,
            },
        )
        return request


def awaken_session(session_id: Any, owner_id: Any, *, tick: int = 0) -> DreamSessionProgress:
    """End the session deterministically; no model call and no sleep write.

    Idempotent: awakening an already-ended session is a pure no-op returning the
    same progress, with no event and no revision change, so a reconnect or a
    repeated awakening can never double-settle anything.
    """
    clean_owner = _clean_owner(owner_id)
    clean_tick = _clean_tick(tick)
    session = get_session(session_id, clean_owner)
    with transaction.atomic():
        locked = _locked_session(session.session_id, clean_owner)
        if locked.state != STATE_ENDED:
            locked.state = STATE_ENDED
            locked.pending_submission_id = ""
            locked.saved_input = ""
            locked.revision = int(locked.revision) + 1
            locked.save(
                update_fields=[
                    "state",
                    "pending_submission_id",
                    "saved_input",
                    "revision",
                    "updated_at",
                ]
            )
            _announce(
                "dream_session_awakened",
                {
                    "session_id": locked.session_id,
                    "owner": clean_owner,
                    "completed": int(locked.completed_exchanges),
                    "outcome": locked.outcome,
                    "tick": clean_tick,
                },
            )
        return progress(locked)
