"""The JSON-safe persistent combat-session record (guild-economy D-6).

One ``CombatSessionRecord`` lives under ``PlayerCharacter.db.active_combat``
and stores participant dbrefs plus fled/knockout identity and the accumulated
round count -- never live objects. This module owns strict parsing,
serialization, session identity, and the active-session read predicates.
"""

import dataclasses
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
        "round_revision",
        "draft_version",
        "draft_entries",
        "confirmed_actors",
    }
)
# Optional fields: ``settled_tick`` is written only when the terminal
# settlement committed; ``martyr_key`` carries the durable session-id stamps
# of the martyrdom-vow casts made during this session (church design §5.8);
# ``opening_first_actor`` is the encounter's explicit opening-order policy --
# the roster key engagement granted the first action of the first complete
# round (``None`` for every ordinary engagement). Older durable records
# without them stay valid, so none is required.
_OPTIONAL_RECORD_FIELDS = frozenset(
    {
        "settled_tick",
        "martyr_key",
        "opening_first_actor",
        "initial_sleep_ids",
        "sleep_transitions",
    }
)


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
    round_revision: int = 0
    draft_version: int = 0
    draft_entries: dict[int, dict[str, Any]] = dataclasses.field(default_factory=dict)
    confirmed_actors: tuple[int, ...] = ()
    settled_tick: int | None = None
    martyr_key: tuple[str, ...] | None = None
    opening_first_actor: str | None = None
    # Sleep is a live posture, never a stored knockout: ``initial_sleep_ids``
    # records the posture the roster carried at engagement and
    # ``sleep_transitions`` the explicit posture changes observed at completed
    # round boundaries. Together they are the terminal accounting evidence;
    # no round reads them back as a gate and none of them mutates physiology.
    initial_sleep_ids: tuple[int, ...] = ()
    sleep_transitions: tuple["SleepTransition", ...] = ()


@dataclass(frozen=True)
class SleepTransition:
    """One explicit sleep posture observed at a completed-round boundary.

    ``round_index`` is the number of completed rounds at which the posture was
    observed, ``actor_id`` a session participant, and ``asleep`` the observed
    posture. The entries let a terminal consumer reconstruct each body's sleep
    intervals without any per-round reserve mutation.
    """

    round_index: int
    actor_id: int
    asleep: bool


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


def _validate_draft_entry(actor_id: int, entry: Any) -> dict[str, Any]:
    """Strictly validate one draft entry dictionary; reject malformed kinds/IDs/live objects."""
    if not hasattr(entry, "items") or isinstance(entry, (str, bytes)):
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION,
            f"draft entry for actor {actor_id} must be a dict",
        )
    allowed_keys = {"kind", "payload"}
    unknown = set(entry) - allowed_keys
    if unknown:
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION,
            f"draft entry has unknown keys {sorted(unknown)}",
        )
    if "kind" not in entry or "payload" not in entry:
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION,
            "draft entry requires 'kind' and 'payload'",
        )
    kind = entry["kind"]
    payload = entry["payload"]
    if not hasattr(payload, "items") or isinstance(payload, (str, bytes)):
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION,
            "draft entry payload must be a dict",
        )
    if kind == "skill":
        skill_keys = {"skill_key", "targets_or_shorthand", "scale"}
        if set(payload) != skill_keys:
            raise CombatSessionError(
                SessionReason.MALFORMED_SESSION,
                f"skill draft payload fields mismatch: {sorted(payload)}",
            )
        if not isinstance(payload["skill_key"], str) or not payload["skill_key"]:
            raise CombatSessionError(SessionReason.MALFORMED_SESSION, "invalid skill_key in draft")
        t = payload["targets_or_shorthand"]
        if isinstance(t, str):
            if t not in {"all-enemies", "all-allies", "all"}:
                raise CombatSessionError(SessionReason.MALFORMED_SESSION, "invalid target shorthand")
        elif isinstance(t, (list, tuple)):
            if any(isinstance(x, bool) or not isinstance(x, int) for x in t):
                raise CombatSessionError(SessionReason.MALFORMED_SESSION, "skill draft target IDs must be ints")
        elif not hasattr(t, "__iter__"):
            raise CombatSessionError(SessionReason.MALFORMED_SESSION, "skill draft targets must be list or shorthand str")
        scale = payload["scale"]
        if isinstance(scale, bool) or not isinstance(scale, (int, float)):
            raise CombatSessionError(SessionReason.MALFORMED_SESSION, "skill draft scale must be float")
        import math
        if not math.isfinite(float(scale)):
            raise CombatSessionError(SessionReason.MALFORMED_SESSION, "skill draft scale must be finite")
    elif kind == "item":
        item_keys = {"item_key", "target_id"}
        if set(payload) != item_keys:
            raise CombatSessionError(SessionReason.MALFORMED_SESSION, f"item draft payload fields mismatch: {sorted(payload)}")
        if not isinstance(payload["item_key"], str) or not payload["item_key"]:
            raise CombatSessionError(SessionReason.MALFORMED_SESSION, "invalid item_key in draft")
        target_id = payload["target_id"]
        if target_id is not None and (isinstance(target_id, bool) or not isinstance(target_id, int)):
            raise CombatSessionError(SessionReason.MALFORMED_SESSION, "item target_id must be int or None")
    elif kind == "tactical":
        tactical_keys = {"tactical_key", "target_id"}
        if set(payload) != tactical_keys:
            raise CombatSessionError(SessionReason.MALFORMED_SESSION, f"tactical draft payload fields mismatch: {sorted(payload)}")
        if payload["tactical_key"] not in {"defend", "dodge", "taunt"}:
            raise CombatSessionError(SessionReason.MALFORMED_SESSION, f"unknown tactical key: {payload['tactical_key']!r}")
        target_id = payload["target_id"]
        if target_id is not None and (isinstance(target_id, bool) or not isinstance(target_id, int)):
            raise CombatSessionError(SessionReason.MALFORMED_SESSION, "tactical target_id must be int or None")
    else:
        raise CombatSessionError(SessionReason.MALFORMED_SESSION, f"unknown draft command kind {kind!r}")
    return {"kind": str(kind), "payload": dict(payload)}


def _parse_draft_entries(raw: Any) -> dict[int, dict[str, Any]]:
    """Parse and validate draft_entries mapping (actor_id -> draft entry)."""
    if not hasattr(raw, "items") or isinstance(raw, (str, bytes)):
        raise CombatSessionError(SessionReason.MALFORMED_SESSION, "draft_entries must be a dict")
    result: dict[int, dict[str, Any]] = {}
    for k, v in raw.items():
        try:
            actor_id = int(k)
        except (TypeError, ValueError) as err:
            raise CombatSessionError(SessionReason.MALFORMED_SESSION, f"invalid actor_id key in draft_entries: {k!r}") from err
        if isinstance(k, bool):
            raise CombatSessionError(SessionReason.MALFORMED_SESSION, "draft_entries actor_id cannot be bool")
        result[actor_id] = _validate_draft_entry(actor_id, v)
    return result


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


def _parse_sleep_transitions(raw: Any) -> tuple[SleepTransition, ...]:
    """Parse and validate the optional boundary-posture evidence list."""
    if raw is None:
        return ()
    if isinstance(raw, (str, bytes)) or not hasattr(raw, "__iter__"):
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION,
            "record field 'sleep_transitions' must be a list",
        )
    transitions: list[SleepTransition] = []
    seen: set[tuple[int, int]] = set()
    for item in raw:
        if not hasattr(item, "get") or isinstance(item, (str, bytes)):
            raise CombatSessionError(
                SessionReason.MALFORMED_SESSION,
                "a sleep transition must be a dict",
            )
        if set(item) != {"round", "actor", "asleep"}:
            raise CombatSessionError(
                SessionReason.MALFORMED_SESSION,
                "a sleep transition carries exactly round, actor and asleep",
            )
        round_index = _require_int(item["round"], "sleep transition round")
        actor_id = _require_int(item["actor"], "sleep transition actor")
        asleep = item["asleep"]
        if not isinstance(asleep, bool):
            raise CombatSessionError(
                SessionReason.MALFORMED_SESSION,
                "a sleep transition's asleep value must be a boolean",
            )
        key = (round_index, actor_id)
        if key in seen:
            raise CombatSessionError(
                SessionReason.MALFORMED_SESSION,
                f"duplicate sleep transition for round {round_index} actor {actor_id}",
            )
        if transitions and key <= (
            transitions[-1].round_index,
            transitions[-1].actor_id,
        ):
            raise CombatSessionError(
                SessionReason.MALFORMED_SESSION,
                "sleep transitions must be ordered by round then actor",
            )
        seen.add(key)
        transitions.append(
            SleepTransition(round_index, actor_id, asleep)
        )
    return tuple(transitions)


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
    round_revision = _require_int(data.get("round_revision", 0), "round_revision")
    if round_revision < 0:
        raise CombatSessionError(SessionReason.MALFORMED_SESSION, "round_revision must be non-negative")
    draft_version = _require_int(data.get("draft_version", 0), "draft_version")
    if draft_version < 0:
        raise CombatSessionError(SessionReason.MALFORMED_SESSION, "draft_version must be non-negative")
    draft_entries = _parse_draft_entries(data.get("draft_entries", {}))
    confirmed_actors = _parse_id_list(data.get("confirmed_actors", []), "confirmed_actors")
    martyr_key = _parse_stamp_list(data.get("martyr_key"), "martyr_key")
    opening_first_actor = data.get("opening_first_actor")
    if opening_first_actor is not None and (
        not isinstance(opening_first_actor, str) or not opening_first_actor
    ):
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION,
            "opening_first_actor must be a non-empty string or None",
        )
    initial_sleep_ids = _parse_id_list(
        data.get("initial_sleep_ids", []), "initial_sleep_ids"
    )
    sleep_transitions = _parse_sleep_transitions(data.get("sleep_transitions"))
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
        round_revision=round_revision,
        draft_version=draft_version,
        draft_entries=draft_entries,
        confirmed_actors=confirmed_actors,
        settled_tick=settled_tick,
        martyr_key=martyr_key,
        opening_first_actor=opening_first_actor,
        initial_sleep_ids=initial_sleep_ids,
        sleep_transitions=sleep_transitions,
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
    for field in ("fled_ids", "knocked_out_ids", "initial_sleep_ids"):
        allowed = set(record.player_ids) | set(record.enemy_ids)
        stray = set(getattr(record, field)) - allowed
        if stray:
            raise CombatSessionError(
                SessionReason.MALFORMED_SESSION,
                f"{field} references unknown dbrefs {sorted(stray)}",
            )
    if len(set(record.initial_sleep_ids)) != len(record.initial_sleep_ids):
        raise CombatSessionError(
            SessionReason.DUPLICATE_PARTICIPANT, "duplicate initial sleep dbref"
        )
    for transition in record.sleep_transitions:
        if transition.actor_id not in set(record.player_ids) | set(record.enemy_ids):
            raise CombatSessionError(
                SessionReason.MALFORMED_SESSION,
                f"sleep transition references unknown dbref {transition.actor_id}",
            )
        if not 1 <= transition.round_index <= record.rounds_elapsed:
            raise CombatSessionError(
                SessionReason.MALFORMED_SESSION,
                "a sleep transition must name a completed round",
            )
    if record.draft_entries:
        stray_draft = set(record.draft_entries) - set(record.player_ids)
        if stray_draft:
            raise CombatSessionError(
                SessionReason.MALFORMED_SESSION,
                f"draft_entries reference unknown player dbrefs {sorted(stray_draft)}",
            )
    stray_confirmed = set(record.confirmed_actors) - set(record.player_ids)
    if stray_confirmed:
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION,
            f"confirmed_actors reference unknown player dbrefs {sorted(stray_confirmed)}",
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
        "round_revision": record.round_revision,
        "draft_version": record.draft_version,
        "draft_entries": {
            str(k): {"kind": v["kind"], "payload": dict(v["payload"])}
            for k, v in (record.draft_entries or {}).items()
        },
        "confirmed_actors": list(record.confirmed_actors),
        "settled_tick": record.settled_tick,
        "martyr_key": (
            None if record.martyr_key is None else list(record.martyr_key)
        ),
        "opening_first_actor": record.opening_first_actor,
        "initial_sleep_ids": list(record.initial_sleep_ids),
        "sleep_transitions": [
            {
                "round": transition.round_index,
                "actor": transition.actor_id,
                "asleep": transition.asleep,
            }
            for transition in record.sleep_transitions
        ],
    }


def participant_sleep_state(battlefield: Any) -> dict[int, bool]:
    """Return every roster participant's live sleep posture, keyed by dbref.

    A no-create read: it consults the persisted posture directly through
    :func:`world.rules.fatigue.sleep_blocks_actions` and never materializes or
    repairs physiology, so an ordinary round cannot tick reserve or time.
    """
    from world.rules.fatigue import sleep_blocks_actions

    state: dict[int, bool] = {}
    for entity in battlefield.roster.values():
        pk = getattr(entity, "pk", None)
        if isinstance(pk, int) and not isinstance(pk, bool):
            state[pk] = sleep_blocks_actions(entity)
    return state


def recorded_sleep_state(record: CombatSessionRecord) -> dict[int, bool]:
    """Return the sleep posture the record's own evidence currently declares."""
    state = {pk: True for pk in record.initial_sleep_ids}
    for transition in record.sleep_transitions:
        state[transition.actor_id] = transition.asleep
    return state


def boundary_sleep_evidence(
    record: CombatSessionRecord,
    battlefield: Any,
    round_index: int,
) -> tuple[SleepTransition, ...]:
    """Return the record's transitions with this boundary's changes appended.

    The completed round observes every present participant's posture once and
    records an explicit transition only where it differs from the last
    recorded posture, so the evidence stays a sparse timeline and a quiet
    round adds nothing. Reading is the only thing this does: no reserve,
    projected status or clock value is written.
    """
    observed = participant_sleep_state(battlefield)
    known = recorded_sleep_state(record)
    transitions = list(record.sleep_transitions)
    for actor_id in sorted(observed):
        asleep = observed[actor_id]
        if known.get(actor_id, False) != asleep:
            transitions.append(SleepTransition(round_index, actor_id, asleep))
    return tuple(transitions)


def format_session_id(actor: Any, mode: str, tick: int) -> str:
    """The one session-ID format (also used by read-only candidate previews)."""
    return f"{mode}:{actor.pk}:{int(tick)}"


def session_id_for(actor: Any, mode: str) -> str:
    """Return a deterministic session ID for one player and mode."""
    from world.rules.clock import get_world_clock

    return format_session_id(actor, mode, get_world_clock().tick)


def read_session(actor: Any) -> CombatSessionRecord | None:
    """Strictly parse ``actor.db.active_combat`` or return ``None``."""
    return _parse_raw_active_combat(actor.db.active_combat)


def read_session_uncached(actor: Any) -> CombatSessionRecord | None:
    """Read and parse the raw persistent active_combat record directly from the database bypassing idmapper."""
    return _parse_raw_active_combat(_raw_active_combat(actor))


def _parse_raw_active_combat(raw: Any) -> CombatSessionRecord | None:
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


def _raw_active_combat(actor: Any) -> Any:
    """Query the database directly for actor's active_combat attribute value bypassing in-process cache."""
    if not hasattr(actor, "db_attributes") or not hasattr(actor, "pk") or actor.pk is None:
        return getattr(getattr(actor, "db", None), "active_combat", None)
    row = (
        actor.db_attributes.through.objects.filter(
            objectdb_id=actor.pk, attribute__db_key="active_combat"
        )
        .values_list("attribute__db_value", flat=True)
        .first()
    )
    return row


def read_last_combat_receipt(actor: Any) -> dict[str, Any] | None:
    """Query actor's last_combat_receipt directly from database bypassing in-process cache."""
    if not hasattr(actor, "db_attributes") or not hasattr(actor, "pk") or actor.pk is None:
        val = getattr(getattr(actor, "db", None), "last_combat_receipt", None)
    else:
        val = (
            actor.db_attributes.through.objects.filter(
                objectdb_id=actor.pk, attribute__db_key="last_combat_receipt"
            )
            .values_list("attribute__db_value", flat=True)
            .first()
        )
    if val is None or not isinstance(val, dict):
        return None
    return dict(val)


def write_last_combat_receipt(actor: Any, receipt: dict[str, Any]) -> None:
    """Persist last_combat_receipt on actor."""
    actor.db.last_combat_receipt = dict(receipt)


def is_in_active_session(actor: Any) -> bool:
    """Return whether ``actor`` carries a valid active combat session."""
    try:
        return read_session(actor) is not None
    except CombatSessionError:  # observability: ignore R2: the predicate deliberately reports an unreadable session as inactive; the caller branches on the bool
        return False


def session_owner(acting: Any) -> Any:
    """The character whose ``active_combat`` holds ``acting``'s session.

    ``acting`` itself whenever it owns a readable session. A possessed puppet
    owns none: the party's encounter is persisted under its commander (a
    companion's field cast opens the commander's session), so the puppet
    operates that commander's session while it remains possessed. Possession
    is barred while either side is in a session, so a puppet can only ever
    find a session its commander opened, and a non-party or unbound acting
    character is its own owner.

    Read-only: it never writes, engages or advances anything.
    """
    try:
        if read_session(acting) is not None:
            return acting
    except CombatSessionError:  # observability: ignore R2: an unreadable own record reports no own session; the caller's is_in_active_session predicate fails closed
        return acting
    from world.rules.party_scope import PartyScopeError, resolve_commander

    try:
        commander = resolve_commander(acting)
    except PartyScopeError:  # observability: ignore R2: a non-party acting character owns only its own session; the caller's own read already reported absence
        return acting
    if commander is acting:
        return acting
    try:
        return commander if read_session(commander) is not None else acting
    except CombatSessionError:  # observability: ignore R2: an unreadable commander record reports no session; the caller's is_in_active_session predicate fails closed
        return acting
