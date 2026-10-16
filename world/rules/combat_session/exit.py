"""Revision-bound confirmation and settlement of one party exit (§6).

Retreat and surrender are session-level party operations, available
independently of which member's personal menu is selected. Neither mutates
anything on its own: :func:`request_party_exit` returns the party scope, the
operation's consequences and a bounded server-issued confirmation token bound
to the commander, the session, the round revision and the operation, and
:func:`confirm_party_exit` verifies that token at this rules boundary before it
admits exactly one operation. Cancelling is discarding the prompt — nothing
moves and no time advances — and a stale, forged, replayed or competing
confirmation cannot reach another session or round, because the token verifies
by recomputation and the admission rereads the durable session/revision inside
the same serialized writer every round uses.

The token is not a truthy flag: its digest covers the four bound values, so a
token issued for another commander, session, revision or operation never
verifies. It is derived from ``settings.SECRET_KEY`` so it stays stable across a
process restart (a retry after a restart still verifies) and is compact enough
for a typed confirmation; it is not a secret-bearing credential, and the
authority it carries is the binding, not the concealment.

Surrender clears the pending draft and enters the existing hostile-defeat or
guild-exam FAIL settlement: it rolls no success check, runs no extra enemy
attack and adds no artificial round. Whatever fails inside that unit — the
settlement body itself, the durable commit, or the operation receipt written
after it — restores the draft and every touched durable/cache surface, so a
later valid retry completes. The retreat operation's dispatch is supplied by
``party-combat-retreat-resolution``; until that handler is registered,
confirming a retreat token rejects deterministically with
``party_exit_unavailable`` before any write, so no placeholder retreat ships.
Enemy individual disengagement keeps its own resolver and AI policy.
"""

import hashlib
import hmac
from dataclasses import dataclass
from typing import Any, Callable

from django.conf import settings

from world.rules.combat import Battlefield
from world.rules.combat_session.battlefield import reconstruct_battlefield
from world.rules.combat_session.errors import CombatSessionError, SessionReason
from world.rules.combat_session.records import (
    CombatSessionRecord,
    read_last_combat_receipt,
    read_session,
    read_session_uncached,
    write_last_combat_receipt,
)
from world.rules.combat_session.settlement import (
    _settle_with_restore,
)
from world.rules.combat_session.snapshot import (
    _restore_exam_host,
    _restore_round_clock,
    _restore_round_touched,
    _snapshot_exam_host,
    _snapshot_party_surfaces,
    _snapshot_round_clock,
    _snapshot_round_touched,
)
from world.rules.combat_session.writer import (
    durable_combat_atomic,
    serialized_combat_write,
)
from world.rules.player_messages import (
    PARTY_EXIT_CONSEQUENCE_LINES,
    PARTY_EXIT_OPERATION_LABELS,
)

PARTY_EXIT_RETREAT = "retreat"
PARTY_EXIT_SURRENDER = "surrender"
#: The closed operation vocabulary a confirmation token may bind to.
PARTY_EXIT_OPERATIONS = (PARTY_EXIT_RETREAT, PARTY_EXIT_SURRENDER)

# One readable opcode per operation, so a confirmation prompt's token names the
# operation it binds and the boundary can compare a caller's claim against it.
_OPCODE_BY_OPERATION = {PARTY_EXIT_RETREAT: "R", PARTY_EXIT_SURRENDER: "S"}
_OPERATION_BY_OPCODE = {opcode: op for op, opcode in _OPCODE_BY_OPERATION.items()}

# Bounded token shape: "<opcode>-<round_revision>-<digest>".
_DIGEST_LENGTH = 20
_TOKEN_MAX_CODE_POINTS = 32
_MAX_SESSION_ID_CODE_POINTS = 128
_HEX_DIGITS = frozenset("0123456789ABCDEF")


def _token_digest(
    commander: Any, session_id: str, round_revision: int, operation: str
) -> str:
    """Return the confirmation digest binding the four authoritative values.

    The key is read at call time (never at import time, which runs before
    ``django.setup()`` on some import paths). An unreleased single-player
    deployment keeps Evennia's default key, so the digest's job is the binding
    above, not concealment.
    """
    payload = f"{int(commander.pk)}|{session_id}|{int(round_revision)}|{operation}"
    digest = hmac.new(
        str(settings.SECRET_KEY).encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest().upper()
    return digest[:_DIGEST_LENGTH]


def party_exit_token(
    commander: Any, session_id: str, round_revision: int, operation: str
) -> str:
    """Return the bounded confirmation token for one bound party exit."""
    if operation not in PARTY_EXIT_OPERATIONS:
        raise CombatSessionError(SessionReason.UNKNOWN_PARTY_EXIT_OPERATION)
    digest = _token_digest(commander, session_id, round_revision, operation)
    return f"{_OPCODE_BY_OPERATION[operation]}-{int(round_revision)}-{digest}"


def _parse_token(confirmation_token: Any) -> tuple[str, int, str]:
    """Parse and shape-check one token; every malformation is invalid."""
    if not isinstance(confirmation_token, str):
        raise CombatSessionError(SessionReason.INVALID_CONFIRMATION_TOKEN)
    token = confirmation_token.strip().upper()
    if not 1 <= len(token) <= _TOKEN_MAX_CODE_POINTS:
        raise CombatSessionError(SessionReason.INVALID_CONFIRMATION_TOKEN)
    opcode, separator, rest = token.partition("-")
    revision_token, separator2, digest = rest.partition("-")
    if not separator or not separator2 or not opcode:
        raise CombatSessionError(SessionReason.INVALID_CONFIRMATION_TOKEN)
    if not revision_token.isdigit():
        raise CombatSessionError(SessionReason.INVALID_CONFIRMATION_TOKEN)
    if (
        len(digest) != _DIGEST_LENGTH
        or not digest
        or any(character not in _HEX_DIGITS for character in digest)
    ):
        raise CombatSessionError(SessionReason.INVALID_CONFIRMATION_TOKEN)
    return opcode, int(revision_token), digest


def party_exit_operation_of_token(confirmation_token: Any) -> str | None:
    """Return the operation one confirmation token names, or ``None``.

    A prompt's token names the operation it binds, so a confirmation entry
    point can route an opaque token to the right party exit without knowing
    which route issued it. The answer is only a routing hint: the boundary
    still recomputes the digest over the operation it dispatches.
    """
    try:
        opcode, _, _ = _parse_token(confirmation_token)
    except CombatSessionError:  # observability: ignore R2: a malformed token is reported as "no operation" by this routing hint; the boundary raises the exact reason
        return None
    return _OPERATION_BY_OPCODE.get(opcode)


def _verify_confirmation_token(
    commander: Any,
    session_id: Any,
    round_revision: Any,
    operation: Any,
    confirmation_token: Any,
) -> str:
    """Return the verified operation, or raise the exact rejection reason.

    Only caller-supplied values are compared until the digest verifies, so no
    server state is disclosed by which check failed. A token whose revision no
    longer matches the claimed round is stale; a token that does not verify for
    the claimed commander/session/round/operation is invalid.
    """
    if not isinstance(operation, str) or operation not in PARTY_EXIT_OPERATIONS:
        raise CombatSessionError(SessionReason.UNKNOWN_PARTY_EXIT_OPERATION)
    if not isinstance(session_id, str) or not session_id:
        raise CombatSessionError(SessionReason.INVALID_CONFIRMATION_TOKEN)
    if len(session_id) > _MAX_SESSION_ID_CODE_POINTS:
        raise CombatSessionError(SessionReason.INVALID_CONFIRMATION_TOKEN)
    if isinstance(round_revision, bool) or not isinstance(round_revision, int):
        raise CombatSessionError(SessionReason.INVALID_CONFIRMATION_TOKEN)
    opcode, token_revision, digest = _parse_token(confirmation_token)
    if _OPERATION_BY_OPCODE.get(opcode) != operation:
        raise CombatSessionError(SessionReason.INVALID_CONFIRMATION_TOKEN)
    if token_revision != round_revision:
        raise CombatSessionError(SessionReason.STALE_ROUND_REVISION)
    expected = _token_digest(commander, session_id, round_revision, operation)
    if not hmac.compare_digest(expected, digest):
        raise CombatSessionError(SessionReason.INVALID_CONFIRMATION_TOKEN)
    return operation


def request_party_exit(
    commander: Any,
    session_id: str,
    round_revision: int,
    operation: str,
) -> dict[str, Any]:
    """Return the party-scope prompt and confirmation token for one exit.

    Runs no action and changes nothing: no draft entry is touched, no time
    advances and no settlement is reached. The caller's view must already name
    the active session and revision; a view of another or an advanced session
    rejects before any prompt exists.
    """
    if not isinstance(operation, str) or operation not in PARTY_EXIT_OPERATIONS:
        raise CombatSessionError(SessionReason.UNKNOWN_PARTY_EXIT_OPERATION)
    record = read_session(commander)
    if record is None:
        raise CombatSessionError(SessionReason.NO_ACTIVE_SESSION)
    if not isinstance(session_id, str) or record.session_id != session_id:
        raise CombatSessionError(SessionReason.UNKNOWN_SESSION_ID)
    if (
        isinstance(round_revision, bool)
        or not isinstance(round_revision, int)
        or record.round_revision != round_revision
    ):
        raise CombatSessionError(SessionReason.STALE_ROUND_REVISION)
    return {
        "outcome": "prompt",
        "operation": operation,
        "operation_label": PARTY_EXIT_OPERATION_LABELS[operation],
        "session_id": record.session_id,
        "round_revision": record.round_revision,
        "confirmation_token": party_exit_token(
            commander, record.session_id, record.round_revision, operation
        ),
        "party_scope": tuple(sorted(record.player_ids)),
        "consequences": tuple(PARTY_EXIT_CONSEQUENCE_LINES[operation]),
    }


@dataclass(frozen=True)
class _ExitSnapshots:
    """Every in-process surface one confirmed exit's durable unit may touch.

    The round path's own snapshot set (the clock stage registry, every
    participant surface, party/relations, the persistent exam host) plus the
    two surfaces a terminal exit clears in-process but a round does not: the
    caller's action context and the battlefield's skip-safety registration.
    Taken before the unit's first write and restored on any failure inside it
    — including one after the settlement body returned, such as the operation
    receipt's own write — so no reader ever observes a settlement the
    database rolled back.
    """

    clock_snapshot: Any
    touched: tuple
    extra: dict[str, tuple[bool, Any]]
    party: tuple[Any, Any, Any]
    exam_host: Any
    battlefield: Battlefield | None
    skip_safety: tuple[tuple[str, Any], ...]

    def restore(self, actor: Any, action_context: Any) -> None:
        """Reinstate every snapshotted surface, in the round path's order."""
        from world.rules.skip_safety import register_active_battlefield

        _restore_round_clock(self.clock_snapshot)
        _restore_round_touched(actor, self.touched, self.extra, *self.party)
        _restore_exam_host(self.exam_host)
        actor.ndb.action_context = action_context
        if self.skip_safety:
            # An unreconstructable battlefield has no roster to re-register
            # from, so the registry entries themselves are restored: a
            # rolled-back live session must keep blocking time skips.
            from world.rules.skip_safety import _BATTLEFIELDS

            for key, battlefield in self.skip_safety:
                if battlefield is None:
                    _BATTLEFIELDS.pop(key, None)
                else:
                    _BATTLEFIELDS[key] = battlefield
        if self.battlefield is not None:
            register_active_battlefield(self.battlefield)


def _snapshot_exit_surfaces(
    commander: Any,
    record: CombatSessionRecord,
    battlefield: Battlefield | None,
) -> _ExitSnapshots:
    """Snapshot every in-process surface the exit unit may touch.

    An unreconstructable battlefield cannot carry a roster, so the settlement
    regenerates nothing but the actor (exactly as the direct forfeit path
    does): the clock stage registry is built for the actor alone and the
    skip-safety registry entries of the actor and the record's participants are
    snapshotted directly, since there is no battlefield object to re-register
    from.
    """
    from world.rules.action import _attribute_snapshot, _snapshot_touched
    from world.rules.clock import (
        AdvanceSource,
        WorldClock,
        _snapshot_clock_tick,
        build_advance_snapshot_registry,
        read_world_clock,
    )
    from world.rules.combat_session.snapshot import _ROUND_ENTITY_SURFACES
    from world.rules.combat_session.settlement import _ROUND_SECONDS
    from world.rules.skip_safety import _BATTLEFIELDS

    if battlefield is None:
        clock = read_world_clock()
        clock_snapshot = (
            clock,
            _snapshot_clock_tick(clock) if clock is not None else None,
            build_advance_snapshot_registry(
                clock if clock is not None else WorldClock(),
                record.rounds_elapsed * _ROUND_SECONDS,
                AdvanceSource.COMBAT,
                (commander,),
            ),
            (commander,),
        )
        participant_keys = (
            str(commander.pk),
            *(str(dbref) for dbref in (*record.player_ids, *record.enemy_ids)),
        )
        skip_safety = tuple(
            (key, _BATTLEFIELDS.get(key)) for key in participant_keys
        )
        extra: dict[str, tuple[bool, Any]] = {
            "active_combat": _attribute_snapshot(commander, "active_combat"),
            "last_combat_receipt": _attribute_snapshot(
                commander, "last_combat_receipt"
            ),
        }
        if record.mode == "guild_exam":
            extra["guild_rank"] = _attribute_snapshot(commander, "guild_rank")
            extra["guild_exams"] = _attribute_snapshot(commander, "guild_exams")
        return _ExitSnapshots(
            clock_snapshot=clock_snapshot,
            touched=(
                (
                    commander,
                    _ROUND_ENTITY_SURFACES,
                    _snapshot_touched(commander, _ROUND_ENTITY_SURFACES),
                ),
            ),
            extra=extra,
            party=([], {}, {}),
            exam_host=_snapshot_exam_host(record),
            battlefield=None,
            skip_safety=skip_safety,
        )
    touched, extra = _snapshot_round_touched(commander, battlefield, record)
    return _ExitSnapshots(
        clock_snapshot=_snapshot_round_clock(record, battlefield),
        touched=touched,
        extra=extra,
        party=_snapshot_party_surfaces(commander, battlefield),
        exam_host=_snapshot_exam_host(record),
        battlefield=battlefield,
        skip_safety=(),
    )


def _confirm_surrender(
    commander: Any,
    record: CombatSessionRecord,
    battlefield: Battlefield | None,
) -> dict[str, Any]:
    """Discard the draft and enter the existing defeat/FAIL settlement once.

    ``nested_round`` marks the settlement as committing through the confirmed
    exit's own durable unit, so the aftermath arms its undo for that unit;
    ``discard_draft`` clears the pending selections inside the settlement's own
    write, so the draft is discarded atomically with the terminal outcome and a
    failed unit keeps it.
    """
    outcome = "defeat" if record.mode == "hostile" else "exam_failed"
    return _settle_with_restore(
        commander,
        record,
        battlefield,
        outcome,
        nested_round=True,
        discard_draft=True,
    )


#: One dispatch per operation. ``retreat`` is registered together with the
#: confirmed retreat's resolution (``party-combat-retreat-resolution``); until
#: then a retreat confirmation rejects with ``party_exit_unavailable`` before
#: any write, so no placeholder retreat behaviour ships.
_OPERATION_HANDLERS: dict[
    str, Callable[[Any, CombatSessionRecord, "Battlefield | None"], dict[str, Any]]
] = {
    PARTY_EXIT_SURRENDER: _confirm_surrender,
}


def _reconstruct(commander: Any, record: CombatSessionRecord) -> Battlefield | None:
    """Reconstruct the session's battlefield, or ``None`` when it cannot be.

    A confirmed surrender still settles when participants are
    unreconstructable (exactly as the direct forfeit path does), so the exit can
    never be blocked by a missing or deleted participant.
    """
    try:
        return reconstruct_battlefield(commander, record)
    except CombatSessionError:  # observability: ignore R2: a confirmed surrender deliberately settles without a battlefield when participants are unreconstructable
        return None


def _revision_already_consumed(
    receipt: dict[str, Any] | None,
    record: CombatSessionRecord,
) -> bool:
    """Whether this session id already consumed the live record's revision.

    The session id is ``mode:pk:tick`` and a settlement that advances no time
    leaves the tick unchanged, so a later engagement in the same tick can share
    this id and the same initial revision. A durable receipt on that exact pair
    therefore means a previous instance of this session id already spent the
    revision, and the replay is refused.

    The guard is deliberately blunt: it cannot tell a replayed token from a
    genuine first confirmation of such a same-tick twin, so a player who
    surrenders an engagement that settled zero accumulated seconds and
    re-engages in the same tick is refused (as ``stale_round_revision``) until
    a round advances the revision. Making the session identity unambiguous
    needs a per-session nonce in the record, which is a schema change this
    slice deliberately does not make; the window is narrow (zero accumulated
    seconds and a zero-second aftermath recovery) and self-limiting (one round
    restores the ability to surrender).
    """
    if receipt is None:
        return False
    return (
        receipt.get("session_id") == record.session_id
        and receipt.get("round_revision") == record.round_revision
    )


def _settled_receipt_result(
    commander: Any,
    session_id: str,
    round_revision: int,
    operation: str,
) -> dict[str, Any]:
    """Return the recorded outcome of an already-committed identical exit.

    A confirmation retried after its settlement committed (for example after a
    restart, or a duplicate submission) must not settle again: the durable
    operation receipt is the record that this session/revision/operation is
    spent, and its outcome is returned unchanged. Any other absent session —
    including another operation's or another revision's receipt — is simply no
    active session.

    This is the boundary's own contract: the entry points that must first read
    a live record to name the session and revision (the text command and this
    slice's browser adapter) report ``no_active_session`` before reaching it,
    so the replay is reachable today through the confirmation API and by the
    token-carrying route the party-exit client ships
    (``webclient-party-exit-confirmation``).
    """
    receipt = read_last_combat_receipt(commander)
    if (
        receipt is None
        or receipt.get("session_id") != session_id
        or receipt.get("round_revision") != round_revision
        or receipt.get("operation") != operation
    ):
        raise CombatSessionError(SessionReason.NO_ACTIVE_SESSION)
    return {
        "outcome": receipt.get("outcome"),
        "rounds_elapsed": receipt.get("rounds_elapsed", 0),
        "logs": (),
        "receipt": dict(receipt),
        "operation": operation,
        "idempotent": True,
    }


@serialized_combat_write
def confirm_party_exit(
    commander: Any,
    session_id: str,
    round_revision: int,
    operation: str,
    confirmation_token: str,
) -> dict[str, Any]:
    """Admit one confirmed party exit and settle it exactly once.

    The token verifies first (a pure computation over the caller's claims), the
    operation's dispatch must exist, and only then does the admission open the
    session's durable unit: rereading the uncached session, revalidating the
    session/revision the token binds, running the operation's handler, and
    recording the operation receipt — all as one unit, so a round and an exit
    (or two exits) racing for the same revision admit only one.

    A failure anywhere inside that unit restores every touched in-process
    surface from the pre-unit snapshot and drops the armed aftermath undo, so
    the durable session and the pending draft both survive for a valid retry.
    """
    verified = _verify_confirmation_token(
        commander, session_id, round_revision, operation, confirmation_token
    )
    handler = _OPERATION_HANDLERS.get(verified)
    if handler is None:
        raise CombatSessionError(SessionReason.PARTY_EXIT_UNAVAILABLE)
    from world.rules.defeat_aftermath import drain_pending_undos

    action_context = commander.ndb.action_context
    snapshots: _ExitSnapshots | None = None
    result: dict[str, Any] = {}
    try:
        with durable_combat_atomic():
            record = read_session_uncached(commander)
            if record is None:
                return _settled_receipt_result(
                    commander, session_id, round_revision, verified
                )
            if record.session_id != session_id:
                raise CombatSessionError(SessionReason.UNKNOWN_SESSION_ID)
            if record.round_revision != round_revision:
                raise CombatSessionError(SessionReason.STALE_ROUND_REVISION)
            if _revision_already_consumed(
                read_last_combat_receipt(commander), record
            ):
                raise CombatSessionError(SessionReason.STALE_ROUND_REVISION)
            battlefield = _reconstruct(commander, record)
            snapshots = _snapshot_exit_surfaces(commander, record, battlefield)
            result = handler(commander, record, battlefield)
            receipt = {
                "session_id": record.session_id,
                "round_revision": record.round_revision,
                "rounds_elapsed": result.get("rounds_elapsed"),
                "outcome": result.get("outcome"),
                "operation": verified,
            }
            write_last_combat_receipt(commander, receipt)
            result["receipt"] = receipt
            result["operation"] = verified
    except Exception:
        # The durable unit rolled back: run the undo the settlement armed
        # inside it first (it restores the writer's own post-settlement entry
        # state), then put every snapshotted in-process surface back, so no
        # reader observes a settlement the database never committed.
        for undo in drain_pending_undos():
            undo()
        if snapshots is not None:
            snapshots.restore(commander, action_context)
        raise
    # The unit committed: any armed aftermath undo is moot (the physical
    # departure is scheduled via on_commit), so it is dropped.
    drain_pending_undos()
    return result
