"""Ephemeral puppet → live-session watcher registry for the room-entry hook.

The OOB ingress maintains this registry: every live webclient session is
registered under its current puppet on ``ui_sync`` and command settlement
(idempotent per session — repeated settlements update the entry, never
append), and stale entries are pruned at every registration and query. The
room-entry hook (a typeclass call site with no session context) resolves the
watching sessions through :func:`watchers_for`, which returns each watcher
with its *current* coordinator epoch read at query time, so a post-reset epoch
is never stale. A disconnected or repuppeted leftover is harmless by
construction: the push's epoch guard silently drops anything the live
coordinator no longer matches, no disconnect hook is required, and the
session-keyed maps keep growth bounded by live sessions.

Nothing here is persisted; the registry disappears with the process, which is
exactly the scope the trigger service needs.
"""

from typing import Any

from web.webclient.presentation.ingress import is_webclient

__all__ = ["clear_watchers", "register_watcher", "watchers_for"]

# actor id (primary key, string form) -> {id(session): session}
_watchers: dict[str, dict[int, Any]] = {}


def _is_live(session: Any) -> bool:
    """Whether ``session`` is still a live session on the evennia handler."""
    try:
        import evennia

        return any(
            candidate is session
            for candidate in evennia.SESSION_HANDLER.get_sessions(include_unloggedin=True)
        )
    except Exception:
        return False


def _puppet_id(session: Any) -> str:
    puppet = getattr(session, "puppet", None)
    if puppet is None:
        return ""
    return str(getattr(puppet, "pk", ""))


def _prune_stale() -> None:
    """Drop entries whose session disconnected or repuppeted elsewhere."""
    for actor_id in list(_watchers):
        entries = _watchers[actor_id]
        for session_id in list(entries):
            if not _is_live(entries[session_id]) or _puppet_id(entries[session_id]) != actor_id:
                del entries[session_id]
        if not entries:
            del _watchers[actor_id]


def register_watcher(session: Any) -> None:
    """Register one live webclient session under its current puppet.

    Idempotent per session: a repeated ``ui_sync`` or command settlement
    updates the existing entry (moving it if the puppet changed) and never
    appends a duplicate. Non-webclient sessions and sessions without a puppet
    are never registered.
    """
    if not is_webclient(session):
        return
    actor_id = _puppet_id(session)
    if not actor_id:
        return
    _prune_stale()
    for entries in _watchers.values():
        for session_id in list(entries):
            if entries[session_id] is session:
                del entries[session_id]
    _watchers.setdefault(actor_id, {})[id(session)] = session


def watchers_for(actor: Any) -> tuple[tuple[Any, str], ...]:
    """The live webclient sessions watching ``actor``, each with its current
    coordinator epoch.

    A session that registered but has since disconnected, repuppeted, or lost
    its attached coordinator is pruned or skipped on the spot: the epoch is
    read from the live coordinator at query time, and a watcher with no
    attached coordinator has no live transport to push to.
    """
    actor_id = str(getattr(actor, "pk", ""))
    if not actor_id:
        return ()
    entries = _watchers.get(actor_id, {})
    watchers: list[tuple[Any, str]] = []
    for session in list(entries.values()):
        if not _is_live(session) or _puppet_id(session) != actor_id:
            continue
        ndb = getattr(session, "ndb", None)
        coordinator = getattr(ndb, "elosern_coordinator", None) if ndb is not None else None
        if coordinator is None:
            continue
        watchers.append((session, coordinator.epoch))
    watchers.sort(key=lambda pair: str(getattr(pair[0], "sessid", "")))
    return tuple(watchers)


def clear_watchers() -> None:
    """Empty the registry (test seam)."""
    _watchers.clear()
