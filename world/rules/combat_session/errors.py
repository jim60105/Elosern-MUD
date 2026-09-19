"""Combat-session error type and stable rejection reasons.

Shared by every combat-session layer: the record parser, targeting,
battlefield reconstruction, and the lifecycle/settlement writers all raise
``CombatSessionError`` with one of these ``SessionReason`` values.
"""

from enum import StrEnum


class CombatSessionError(ValueError):
    """A combat-session operation violates the persistent-session contract."""


class SessionReason(StrEnum):
    NOT_A_PLAYER = "not_a_player"
    ALREADY_IN_COMBAT = "already_in_combat"
    NO_ACTIVE_SESSION = "no_active_session"
    NOT_HOSTILE = "not_hostile"
    NOT_PRESENT = "not_present"
    TARGET_DEAD = "target_dead"
    ROOM_MISSING = "room_missing"
    MOVED = "moved"
    MISSING_PARTICIPANT = "missing_participant"
    DUPLICATE_PARTICIPANT = "duplicate_participant"
    MALFORMED_SESSION = "malformed_session"
    INVALID_RECOVERY = "invalid_recovery"
    UNKNOWN_SESSION_ID = "unknown_session_id"
