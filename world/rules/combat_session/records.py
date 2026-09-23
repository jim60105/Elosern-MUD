"""The JSON-safe persistent combat-session record (guild-economy D-6).

One ``CombatSessionRecord`` lives under ``PlayerCharacter.db.active_combat``
and stores participant dbrefs plus fled/knockout identity and the accumulated
round count -- never live objects. This module owns strict parsing,
serialization, session identity, and the active-session read predicates.
"""

from dataclasses import dataclass
from typing import Any

from world.rules.combat_session.errors import CombatSessionError, SessionReason

_RECORD_FIELDS = frozenset(
    {
        "session_id",
        "mode",
        "room_id",
        "player_ids",
        "enemy_ids",
        "fled_ids",
        "knocked_out_ids",
        "rounds_elapsed",
        "exam_id",
    }
)
# Optional fields: ``settled_tick`` is written only when the terminal
# settlement committed; ``martyr_key`` carries the durable session-id stamps
# of the martyrdom-vow casts made during this session (church design §5.8).
# Older durable records without them stay valid, so neither is required.
_OPTIONAL_RECORD_FIELDS = frozenset({"settled_tick", "martyr_key"})


@dataclass(frozen=True)
class CombatSessionRecord:
    """One deterministic, JSON-safe persistent combat session record."""

    session_id: str
    mode: str
    room_id: int
    player_ids: tuple[int, ...]
    enemy_ids: tuple[int, ...]
    fled_ids: tuple[int, ...]
    knocked_out_ids: tuple[int, ...]
    rounds_elapsed: int
    exam_id: str | None
    settled_tick: int | None = None
    martyr_key: tuple[str, ...] | None = None


def _parse_id_list(values: Any, field: str) -> tuple[int, ...]:
    if isinstance(values, (str, bytes)) or not hasattr(values, "__iter__"):
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION, f"record field {field!r} must be a list"
        )
    items = list(values)
    if not all(isinstance(item, int) and not isinstance(item, bool) for item in items):
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION, f"record field {field!r} must be int dbrefs"
        )
    return tuple(items)


def _require_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION, f"record field {field!r} must be an integer"
        )
    return value


def _parse_stamp_list(values: Any, field: str) -> tuple[str, ...] | None:
    """Parse the optional martyr-stamp list: None or a list of non-empty ids."""
    if values is None:
        return None
    if isinstance(values, (str, bytes)) or not hasattr(values, "__iter__"):
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION,
            f"record field {field!r} must be a list of session id strings",
        )
    items = list(values)
    if not all(isinstance(item, str) and item for item in items):
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION,
            f"record field {field!r} must hold non-empty session id strings",
        )
    return tuple(items)


def from_storage(data: dict[str, Any]) -> CombatSessionRecord:
    """Strictly parse one storage dict, raising ``CombatSessionError`` on violations."""
    if not isinstance(data, dict):
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION, "active_combat must be a dict"
        )
    unknown = set(data) - _RECORD_FIELDS - _OPTIONAL_RECORD_FIELDS
    if unknown:
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION,
            f"active_combat has unknown fields {sorted(unknown)}",
        )
    missing = _RECORD_FIELDS - set(data)
    if missing:
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION,
            f"active_combat is missing fields {sorted(missing)}",
        )
    session_id = data["session_id"]
    mode = data["mode"]
    if not isinstance(session_id, str) or not session_id:
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION, "session_id must be a non-empty string"
        )
    if mode not in {"hostile", "guild_exam"}:
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION, f"unknown session mode {mode!r}"
        )
    exam_id = data["exam_id"]
    if exam_id is not None and not isinstance(exam_id, str):
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION, "exam_id must be a string or None"
        )
    if mode == "guild_exam" and not exam_id:
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION,
            "guild_exam sessions require an exam_id",
        )
    rounds_elapsed = _require_int(data["rounds_elapsed"], "rounds_elapsed")
    if rounds_elapsed < 0:
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION, "rounds_elapsed must be non-negative"
        )
    settled_tick = data.get("settled_tick")
    if settled_tick is not None:
        settled_tick = _require_int(settled_tick, "settled_tick")
        if settled_tick < 0:
            raise CombatSessionError(
                SessionReason.MALFORMED_SESSION, "settled_tick must be non-negative"
            )
    martyr_key = _parse_stamp_list(data.get("martyr_key"), "martyr_key")
    record = CombatSessionRecord(
        session_id=session_id,
        mode=mode,
        room_id=_require_int(data["room_id"], "room_id"),
        player_ids=_parse_id_list(data["player_ids"], "player_ids"),
        enemy_ids=_parse_id_list(data["enemy_ids"], "enemy_ids"),
        fled_ids=_parse_id_list(data["fled_ids"], "fled_ids"),
        knocked_out_ids=_parse_id_list(data["knocked_out_ids"], "knocked_out_ids"),
        rounds_elapsed=rounds_elapsed,
        exam_id=exam_id,
        settled_tick=settled_tick,
        martyr_key=martyr_key,
    )
    _validate_participant_shape(record)
    return record


def _validate_participant_shape(record: CombatSessionRecord) -> None:
    if not record.player_ids or not record.enemy_ids:
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION, "a session needs player and enemy dbrefs"
        )
    overlap = set(record.player_ids) & set(record.enemy_ids)
    if overlap:
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION,
            f"dbrefs {sorted(overlap)} cannot be both player and enemy",
        )
    if len(set(record.player_ids)) != len(record.player_ids):
        raise CombatSessionError(
            SessionReason.DUPLICATE_PARTICIPANT, "duplicate player dbref"
        )
    if len(set(record.enemy_ids)) != len(record.enemy_ids):
        raise CombatSessionError(
            SessionReason.DUPLICATE_PARTICIPANT, "duplicate enemy dbref"
        )
    for field in ("fled_ids", "knocked_out_ids"):
        allowed = set(record.player_ids) | set(record.enemy_ids)
        stray = set(getattr(record, field)) - allowed
        if stray:
            raise CombatSessionError(
                SessionReason.MALFORMED_SESSION,
                f"{field} references unknown dbrefs {sorted(stray)}",
            )


def to_storage(record: CombatSessionRecord) -> dict[str, Any]:
    """Serialize one record into a JSON-safe storage dict with no live refs."""
    return {
        "session_id": record.session_id,
        "mode": record.mode,
        "room_id": record.room_id,
        "player_ids": list(record.player_ids),
        "enemy_ids": list(record.enemy_ids),
        "fled_ids": list(record.fled_ids),
        "knocked_out_ids": list(record.knocked_out_ids),
        "rounds_elapsed": record.rounds_elapsed,
        "exam_id": record.exam_id,
        "settled_tick": record.settled_tick,
        "martyr_key": (
            None if record.martyr_key is None else list(record.martyr_key)
        ),
    }


def session_id_for(actor: Any, mode: str) -> str:
    """Return a deterministic session ID for one player and mode."""
    from world.rules.clock import get_world_clock

    return f"{mode}:{actor.pk}:{int(get_world_clock().tick)}"


def read_session(actor: Any) -> CombatSessionRecord | None:
    """Strictly parse ``actor.db.active_combat`` or return ``None``."""
    raw = actor.db.active_combat
    if raw is None:
        return None
    try:
        return from_storage(dict(raw))
    except CombatSessionError:
        raise
    except (TypeError, ValueError) as error:
        # Raw-conversion shape failures (a string or an integer payload, or
        # an exotic iterable that from_storage cannot read) normalize to the
        # malformed-session contract instead of leaking a bare conversion
        # error to active-session queries and commands.
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION,
            "active_combat could not be converted to a session record",
        ) from error


def is_in_active_session(actor: Any) -> bool:
    """Return whether ``actor`` carries a valid active combat session."""
    try:
        return read_session(actor) is not None
    except CombatSessionError:  # observability: ignore R2: the predicate deliberately reports an unreadable session as inactive; the caller branches on the bool
        return False
