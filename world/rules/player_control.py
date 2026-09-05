"""Unified player-driven entity predicate (companion-possession-rules).

Cites design D4 of the world-clock line ('the world advances only on player action')
and companion-possession design D5: possession widens WHO counts as a player actor
for clock and room-entry trigger purposes, never WHEN.

This module is the project's single source of truth for whether an entity is
player-driven. Movement charging, room-entry action-options scheduling, and any
future player-actor gates import :func:`is_player_driven` rather than
re-implementing the OR.
"""

from typing import Any


def is_player_driven(entity: Any) -> bool:
    """Decide whether ``entity`` counts as a player actor.

    True exactly when:
    1. ``entity`` is a ``PlayerCharacter`` (the existing check, unchanged).
    2. ``entity`` is an ``NPC`` whose ``db.possessed_by`` is non-null AND which
       is currently puppeted (``entity.sessions.count() > 0``).

    An NPC whose ``db.possessed_by`` is set but which currently has no live
    session (e.g. during the disconnect window before cleanup completes) reads
    ``False``.
    """
    if entity is None:
        return False

    from typeclasses.characters import PlayerCharacter
    from typeclasses.npcs import NPC

    if isinstance(entity, PlayerCharacter):
        return True

    if isinstance(entity, NPC):
        if getattr(getattr(entity, "db", None), "possessed_by", None) is None:
            return False
        sessions = getattr(entity, "sessions", None)
        return bool(sessions and sessions.count() > 0)

    return False
