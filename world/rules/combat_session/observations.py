"""In-process, transaction-safe observation memory for one combat session.

The monster AI's cross-round tactical memory is deliberately volatile
(monster-ai-observation-lifecycle, tactics design sections 6-8). This module
owns the session-scoped half of that contract, beside
:mod:`world.rules.combat_session.ai_tuning`:

* A bounded session ring holds one compact, already-settled public
  observation per settled action/upkeep boundary. It retains at most
  :data:`MAX_RETAINED_ROUNDS` actual rounds and :data:`MAX_RETAINED_RECORDS`
  records per session, whichever expires first, and at most
  :data:`MAX_RECORD_RECIPIENTS` recipients per record.
* Each observation is recorded inside the enclosing database transaction, so
  an earlier resolved action is visible to a later decision in the same round
  before anything is committed. Publication happens only when the outermost
  transaction commits; a rolled-back transaction publishes nothing and leaves
  the prior committed memory intact.
* A terminal cleanup request (normal victory/defeat, flee, forfeit, recovery,
  missing participants) supersedes every earlier publication callback in the
  same transaction: the session's committed memory and its recorded tuning
  are discarded after commit, and a rolled-back cleanup keeps both.

Nothing here is durable. The committed mapping is module state, so a restart
clears every session's history by construction; the explicit
:func:`clear_session_memory` seam lets a focused test simulate one.

Savepoint correctness. Every journalled observation or terminal request
registers two ``on_commit`` callbacks at the savepoint level active when it
was written: a *mark* that records its index as survived, and a *fold* that
recomputes the committed ring from the journal's base plus every survived
entry. Django discards both callbacks when that savepoint rolls back, so a
failed inner savepoint leaves no trace even when it is the last event before
the enclosing commit -- the surviving marks never include it. Recomputing
from the base on every fold makes interleaved marks and folds order-safe: the
last fold (belonging to the last surviving entry) sees every survived mark.
Terminal requests are folded the same way and win whatever their position,
because a fold that sees a survived terminal discards instead of publishing.

A per-journal *token* callback (a no-op ``on_commit`` registered at the
journal's own level) identifies the transaction that owns the journal: once
that transaction commits or rolls back, Django drops the token, so the next
access never reuses a stale journal -- including when one ``Atomic`` instance
is deliberately reused for two sequential transactions. Terminal cleanup
outside any transaction applies immediately.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from django.db import transaction

from world.observability import log_info
from world.rules.action import _stored_trait_value
from world.rules.combat.decision_scope import stable_actor_id
from world.rules.combat_session.ai_tuning import discard_session_ai_tuning
from world.rules.monster_ai.models import PublicObservation

#: Retain at most this many actual rounds per session ...
MAX_RETAINED_ROUNDS = 3
#: ... and at most this many compact records, whichever expires first.
MAX_RETAINED_RECORDS = 128
#: At most this many recipients are named in one compact record; a larger
#: group is summarized to the first recipients in observed order.
MAX_RECORD_RECIPIENTS = 8


@dataclass
class _Memory:
    """One session's committed, bounded observation ring."""

    records: list[PublicObservation] = field(default_factory=list)
    generation: int = 0
    next_sequence: int = 0
    token: Any = None


@dataclass
class _Entry:
    """One journalled observation (``None`` = terminal request).

    ``savepoints`` is the set of savepoint ids active when the entry was
    written (empty for the outermost transaction level), and ``mark`` is the
    callback that records the entry as survived at commit.
    """

    observation: PublicObservation | None
    savepoints: frozenset[int]
    mark: Any = None


@dataclass
class _Journal:
    """One transaction's pending observations and terminal requests."""

    session_id: str
    base_generation: int
    base_records: list[PublicObservation]
    base_next_sequence: int
    token: Any
    entries: list[_Entry] = field(default_factory=list)
    survived: set[int] = field(default_factory=set)


#: session id -> committed memory. Module state: a restart clears it.
_COMMITTED: dict[str, _Memory] = {}
#: session id -> the current transaction's journal.
_JOURNALS: dict[str, _Journal] = {}


def _connection() -> Any:
    return transaction.get_connection()


def _open_savepoints(conn: Any) -> frozenset[int]:
    return frozenset(getattr(conn, "savepoint_ids", ()) or ())


def _sentinel_alive(sentinel: Any, conn: Any) -> bool:
    if sentinel is None:
        return True
    return any(
        function is sentinel for _, function, _ in getattr(conn, "run_on_commit", ())
    )


def _drop_stale_journals(conn: Any) -> None:
    """Forget journals whose owning transaction has ended."""
    for session_id, journal in list(_JOURNALS.items()):
        if not _sentinel_alive(journal.token, conn):
            del _JOURNALS[session_id]


def _journal_for(session_id: str, conn: Any) -> _Journal:
    existing = _JOURNALS.get(session_id)
    if existing is not None and _sentinel_alive(existing.token, conn):
        return existing
    memory = _COMMITTED.get(session_id)
    token = lambda: None  # noqa: E731 - a bare, side-effect-free transaction token
    transaction.on_commit(token)
    journal = _Journal(
        session_id=session_id,
        base_generation=0 if memory is None else memory.generation,
        base_records=[] if memory is None else list(memory.records),
        base_next_sequence=0 if memory is None else memory.next_sequence,
        token=token,
    )
    _JOURNALS[session_id] = journal
    return journal


def _entry_alive(entry: _Entry, conn: Any) -> bool:
    return not entry.savepoints or _sentinel_alive(entry.mark, conn)


def _schedule(conn: Any, journal: _Journal, index: int) -> Any:
    """Register one entry's survival mark and its fold at the current level."""
    mark = lambda current=journal, at=index: current.survived.add(at)  # noqa: E731
    transaction.on_commit(mark)
    transaction.on_commit(lambda current=journal: _fold(current))
    return mark


def _bound(records: list[PublicObservation]) -> tuple[list[PublicObservation], int]:
    """Return the retained prefix of one record list and the evicted count."""
    if not records:
        return [], 0
    retained_rounds: list[int] = []
    for record in reversed(records):
        if record.round_index not in retained_rounds:
            retained_rounds.append(record.round_index)
            if len(retained_rounds) >= MAX_RETAINED_ROUNDS:
                break
    keep = set(retained_rounds)
    kept = [record for record in records if record.round_index in keep]
    if len(kept) > MAX_RETAINED_RECORDS:
        kept = kept[-MAX_RETAINED_RECORDS:]
    return kept, len(records) - len(kept)


def _eligible(
    records: list[PublicObservation], battlefield: Any
) -> tuple[PublicObservation, ...]:
    """Project records through the battlefield's current membership and faction."""
    live: dict[str, str] = {}
    for key, entity in battlefield.roster.items():
        if key in battlefield.fled or battlefield.is_knocked_out(key):
            continue
        if _stored_trait_value(entity.traits.hp) <= 0:
            continue
        faction = battlefield.team_of(key)
        if faction is not None:
            live[stable_actor_id(entity)] = faction
    projected: list[PublicObservation] = []
    for record in records:
        current_faction = live.get(record.source_id)
        if current_faction is None or current_faction != record.source_faction:
            continue
        recipients = tuple(
            identity for identity in record.recipient_ids if identity in live
        )
        magnitudes = tuple(
            (identity, magnitude)
            for identity, magnitude in record.magnitudes
            if identity in live
        )
        projected.append(
            replace(record, recipient_ids=recipients, magnitudes=magnitudes)
        )
    return tuple(projected)


def _fold(journal: _Journal) -> None:
    """Recompute one journal's committed ring from its base plus survived entries.

    Idempotent and order-safe: every fold recomputes from the same base and the
    survived set accumulated so far, so the last fold to run -- belonging to the
    last surviving entry -- is authoritative. A live terminal request discards
    the ring and the session's recorded tuning instead.
    """
    if _JOURNALS.get(journal.session_id) is journal:
        # The journal has reached commit time: committed memory is now the
        # only read source, so stop offering its pending entries to decisions.
        del _JOURNALS[journal.session_id]
    memory = _COMMITTED.get(journal.session_id)
    if memory is None:
        if journal.base_generation != 0:
            # A newer transaction already replaced or discarded this base.
            return
    elif (
        memory.generation != journal.base_generation
        and memory.token is not journal.token
    ):
        # An older journal's fold must never overwrite newer committed memory.
        return
    survived = [journal.entries[index].observation for index in sorted(journal.survived)]
    if any(observation is None for observation in survived):
        _COMMITTED.pop(journal.session_id, None)
        discard_session_ai_tuning(journal.session_id)
        return
    records = journal.base_records + [observation for observation in survived if observation]
    bounded, evicted = _bound(records)
    _COMMITTED[journal.session_id] = _Memory(
        records=bounded,
        generation=journal.base_generation + 1,
        next_sequence=journal.base_next_sequence + len(survived),
        token=journal.token,
    )
    if evicted:
        log_info(
            "monster_ai_observation_evicted",
            context={
                "session": journal.session_id,
                "evicted": evicted,
                "retained": len(bounded),
            },
        )


def record_observation(session_id: str, observation: PublicObservation) -> bool:
    """Append one settled public observation to the transaction-local journal.

    A no-op -- returning ``False`` -- when there is no session id or no real
    transaction boundary: a standalone direct round can never mutate shared
    session memory. Returns ``True`` when the observation was journalled.
    """
    if not session_id:
        return False
    conn = _connection()
    if not conn.in_atomic_block:
        return False
    _drop_stale_journals(conn)
    journal = _journal_for(session_id, conn)
    index = len(journal.entries)
    sequenced = replace(observation, sequence=journal.base_next_sequence + index)
    mark = _schedule(conn, journal, index)
    journal.entries.append(_Entry(sequenced, _open_savepoints(conn), mark))
    return True


def _health_magnitude(entry: Any) -> float | None:
    """Return one entry's signed health delta for a named recipient, or None."""
    data = entry.data if isinstance(entry.data, Mapping) else {}
    if entry.kind == "damage":
        sign = -1.0
    elif entry.kind in ("heal", "self_heal"):
        sign = 1.0
    elif entry.kind == "item_used" and data.get("stat") == "hp":
        # The item pipeline's ``amount`` is the signed gauge delta actually
        # applied, so it already carries the healing/draining direction.
        sign = 1.0
    else:
        return None
    amount = data.get("amount")
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        return None
    return sign * float(amount)


def observe_action(
    session_id: str,
    round_index: int,
    event_log: Any,
    *,
    roster: Mapping[str, Any],
    battlefield: Any,
) -> bool:
    """Record one resolved action/upkeep boundary from its event log.

    The compact record names the source's stable identity and faction, the
    resolved skill or item identity, the observed recipients in order (bounded
    to :data:`MAX_RECORD_RECIPIENTS`), the signed per-recipient health
    magnitudes and the distinct observable status facts (a skill's entry kinds,
    an item's applied status keys). It carries no entity reference, pending
    request, callback or prose.
    """
    if not session_id:
        return False
    source_key = str(event_log.actor)
    source_entity = roster.get(source_key)
    source_id = (
        stable_actor_id(source_entity)
        if source_entity is not None
        else f"key:{source_key}"
    )
    faction = battlefield.team_of(source_key) or ""
    recipients: list[str] = []
    magnitudes: dict[str, float] = {}
    statuses: list[str] = []

    def note(key: str | None) -> str | None:
        if key is None or key not in roster:
            return None
        identity = stable_actor_id(roster[key])
        if identity not in recipients:
            recipients.append(identity)
        return identity

    for key in event_log.targets:
        note(str(key))
    for entry in event_log.entries:
        if entry.kind == "item_used":
            keys = entry.data.get("status_keys") if isinstance(entry.data, Mapping) else None
            if isinstance(keys, (list, tuple)):
                for key in keys:
                    if str(key) not in statuses:
                        statuses.append(str(key))
        elif entry.kind not in statuses:
            statuses.append(entry.kind)
        magnitude = _health_magnitude(entry)
        if magnitude is None or entry.target is None:
            continue
        identity = note(str(entry.target))
        if identity is not None:
            magnitudes[identity] = magnitudes.get(identity, 0.0) + magnitude
    omitted = max(0, len(recipients) - MAX_RECORD_RECIPIENTS)
    if omitted:
        recipients = recipients[:MAX_RECORD_RECIPIENTS]
    named = [identity for identity in recipients if identity in magnitudes]
    return record_observation(
        session_id,
        PublicObservation(
            round_index=round_index,
            sequence=0,
            source_id=source_id,
            action_key=str(event_log.skill_key),
            recipient_ids=tuple(recipients),
            statuses=tuple(statuses),
            source_faction=faction,
            magnitudes=tuple((identity, magnitudes[identity]) for identity in named),
        ),
    )


def reconcile_session_memory(session_id: str) -> None:
    """Forget stale journals before a transaction closes (housekeeping seam)."""
    if not session_id:
        return
    conn = _connection()
    _drop_stale_journals(conn)


def project_observations(
    session_id: str, battlefield: Any
) -> tuple[PublicObservation, ...]:
    """Return one session's committed and pending observations for a decision.

    The projection combines the committed ring with the current transaction's
    live journal entries, then drops any record whose source is no longer a
    live participant with its recorded faction and filters stale recipients
    through the battlefield's current membership.
    """
    if not session_id or battlefield is None:
        return ()
    conn = _connection()
    _drop_stale_journals(conn)
    journal = _JOURNALS.get(session_id)
    records: list[PublicObservation] = []
    memory = _COMMITTED.get(session_id)
    if memory is not None:
        records.extend(memory.records)
    if journal is not None and conn.in_atomic_block:
        records.extend(
            entry.observation
            for entry in journal.entries
            if entry.observation is not None and _entry_alive(entry, conn)
        )
    return _eligible(records, battlefield)


def session_observations(session_id: str) -> tuple[PublicObservation, ...]:
    """Return one session's committed records in order (no eligibility)."""
    memory = _COMMITTED.get(session_id)
    return tuple(memory.records) if memory is not None else ()


def discard_session_memory(session_id: str) -> None:
    """Request terminal cleanup of one session's memory and recorded tuning.

    Inside a transaction the request is a journal entry, so it takes effect
    only when the outermost transaction commits; a rollback -- including a
    rolled-back savepoint nested in a successful outer transaction -- keeps
    the committed memory and the recorded tuning. Outside a transaction it
    applies immediately.
    """
    if not session_id:
        return
    conn = _connection()
    if not conn.in_atomic_block:
        _COMMITTED.pop(session_id, None)
        _JOURNALS.pop(session_id, None)
        discard_session_ai_tuning(session_id)
        return
    _drop_stale_journals(conn)
    journal = _journal_for(session_id, conn)
    index = len(journal.entries)
    mark = _schedule(conn, journal, index)
    journal.entries.append(_Entry(None, _open_savepoints(conn), mark))


def clear_session_memory() -> None:
    """Drop every committed ring and journal -- the restart seam.

    A restart clears the store by construction (module state); this explicit
    seam lets a focused test simulate one without a new interpreter.
    """
    _COMMITTED.clear()
    _JOURNALS.clear()
