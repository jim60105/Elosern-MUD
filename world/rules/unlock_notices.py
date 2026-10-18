"""Session-scoped party unlock marks and the post-commit unlock delivery.

The notices themselves are produced by the practice award path
(:mod:`world.rules.progression`); this module owns what happens once a grant
commits: the commander's notification line and the session-only unread state
the party window reads.

Design §4.7 of the party member management UI design: the rail's unread dot is
session-scoped ``ndb`` state cleared by opening that member's skill tab and
dropped on reconnect, so viewing never writes persistent state. Nothing here
touches ``db`` or the database — ``session.ndb.party_unlocks`` is an in-memory
mapping of member identity to :class:`MemberUnlocks`, and a new connection
simply starts empty.

The delivery helper resolves the commander's live sessions rather than
messaging the commander object: during possession the commander's body is
unpuppeted (Evennia drops its account link), so only the account's sessions —
then attached to the possessed companion — can receive the line and hold the
marks.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

#: The session ``ndb`` attribute holding every member's session unlock state.
NDB_ATTRIBUTE = "party_unlocks"

#: The scheduled-event kind an advance uses to stage an unlock after commit.
PRACTICE_UNLOCK_EVENT = "practice_unlock"

#: The companion-learner line form; the commander keeps ``unlock_line``.
COMPANION_UNLOCK_LINE = "{member} 學會了 {skill}"


@dataclass(frozen=True)
class UnlockNotice:
    """One committed practice grant that made a skill usable for one learner.

    ``learner_id`` is the learner's dbid, or ``None`` for an unsaved pure
    fixture stub. ``line`` is the already-rendered player-facing line, so a
    caller that only needs text never re-renders it.
    """

    learner_id: int | None
    learner_name: str
    skill_key: str
    line: str


@dataclass(frozen=True)
class MemberUnlocks:
    """One member's session unlock state: the unread dot and the recent set."""

    unread: bool
    recent: frozenset[str]


_EMPTY = MemberUnlocks(False, frozenset())


def commander_of(acting: Any) -> Any:
    """The commander behind ``acting``, or ``acting`` when no party resolves.

    ``resolve_commander`` only resolves a *possessed* companion, so a plain
    NPC (or a fixture stub) falls back to itself: the caller is then its own
    commander and the delivery has nothing else to key on.
    """
    from world.rules.party_scope import PartyScopeError, resolve_commander

    try:
        return resolve_commander(acting)
    except PartyScopeError:
        return acting


def commander_sessions(acting: Any) -> tuple[Any, ...]:
    """Every live session of the account behind ``acting``'s commander."""
    commander = commander_of(acting)
    for entity in (acting, commander):
        account = getattr(entity, "account", None)
        sessions = getattr(account, "sessions", None)
        if sessions is not None:
            return tuple(sessions.all())
    return _possession_sessions(commander)


def _possession_sessions(commander: Any) -> tuple[Any, ...]:
    """Sessions puppeting the commander's possessed companion.

    A possessed commander body is unpuppeted, so Evennia removes its account
    link; the account's sessions then belong to the possessed companion. The
    possession mirror (``db.possessed_by``, whose single writer is
    :mod:`world.rules.possession`) is the read-only way back to them.
    """
    commander_id = getattr(commander, "pk", None)
    if not isinstance(commander_id, int) or isinstance(commander_id, bool):
        return ()
    from evennia.server.sessionhandler import SESSION_HANDLER

    return tuple(
        session
        for session in SESSION_HANDLER.values()
        if getattr(getattr(getattr(session, "puppet", None), "db", None), "possessed_by", None)
        == commander_id
    )


def record_unlocks(acting: Any, notices: Iterable[UnlockNotice]) -> None:
    """Mark every learner unread on every session of the commander's account.

    Copy-on-write: the stored mapping is replaced, never mutated in place, so
    a snapshot a presenter already copied can never observe a later change.
    """
    pending = tuple(notices)
    if not pending:
        return
    for session in commander_sessions(acting):
        state = dict(unlock_flags(session))
        for notice in pending:
            if notice.learner_id is None:
                # An unsaved learner has no identity the party window could
                # key on; only pure fixtures reach this.
                continue
            entry = state.get(notice.learner_id, _EMPTY)
            state[notice.learner_id] = MemberUnlocks(
                unread=True, recent=entry.recent | {notice.skill_key}
            )
        session.ndb.party_unlocks = state


def deliver_unlocks(
    acting: Any, notices: Iterable[UnlockNotice], *, announce: bool = True
) -> None:
    """Deliver committed unlock notices: the commander's line, then the marks.

    ``announce=False`` is for the owners that already deliver the rendered
    line through their own post-commit channel (the resolver's notification
    tuple, the combat round delivery, or the skip summary): the line then
    reaches the commander exactly once and this call only records the marks.
    """
    pending = tuple(notices)
    if not pending:
        return
    if announce:
        for session in commander_sessions(acting):
            for notice in pending:
                session.msg(notice.line)
    record_unlocks(acting, pending)


def mark_unlocks_seen(session: Any, member_id: int) -> None:
    """Clear one member's unread dot in this session, keeping the recent set."""
    state = dict(unlock_flags(session))
    entry = state.get(member_id)
    if entry is None or not entry.unread:
        return
    state[member_id] = MemberUnlocks(unread=False, recent=entry.recent)
    session.ndb.party_unlocks = state


def unlock_flags(session: Any) -> Mapping[int, MemberUnlocks]:
    """The session's immutable unlock-state copy (never the live ``ndb`` object)."""
    raw = getattr(getattr(session, "ndb", None), NDB_ATTRIBUTE, None)
    if not isinstance(raw, Mapping):
        return MappingProxyType({})
    return MappingProxyType(
        {
            key: value
            for key, value in raw.items()
            if isinstance(key, int) and isinstance(value, MemberUnlocks)
        }
    )


def notices_from_events(events: Iterable[Any]) -> tuple[UnlockNotice, ...]:
    """Rebuild the unlock notices an advance staged as scheduled events.

    A committed advance returns its ``practice_unlock`` events; a rolled-back
    advance raises and returns none, so this read can never resurrect a
    discarded unlock.
    """
    return tuple(
        UnlockNotice(
            learner_id=event.payload.get("learner_id"),
            learner_name=str(event.payload.get("learner_name", "")),
            skill_key=str(event.payload.get("skill_key", "")),
            line=str(event.payload.get("line", "")),
        )
        for event in events
        if event.kind == PRACTICE_UNLOCK_EVENT
    )


__all__ = [
    "COMPANION_UNLOCK_LINE",
    "NDB_ATTRIBUTE",
    "PRACTICE_UNLOCK_EVENT",
    "MemberUnlocks",
    "UnlockNotice",
    "commander_of",
    "commander_sessions",
    "deliver_unlocks",
    "mark_unlocks_seen",
    "notices_from_events",
    "record_unlocks",
    "unlock_flags",
]
