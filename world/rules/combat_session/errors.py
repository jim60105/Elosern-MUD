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
    FORBIDDEN_ACTOR = "forbidden_actor"
    # Party-exit confirmation (party-combat-confirmed-surrender): the exit
    # operations' own stable reasons. A token that does not verify for the
    # claimed commander/session/round/operation, a round revision that moved
    # past the confirmation, an operation whose dispatch change has not landed
    # yet, and an allied personal flee route all report distinctly.
    STALE_ROUND_REVISION = "stale_round_revision"
    UNKNOWN_PARTY_EXIT_OPERATION = "unknown_party_exit_operation"
    INVALID_CONFIRMATION_TOKEN = "invalid_confirmation_token"
    PARTY_EXIT_UNAVAILABLE = "party_exit_unavailable"
    PERSONAL_FLEE_FORBIDDEN = "personal_flee_forbidden"
