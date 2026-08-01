"""Persistent player combat-session orchestration (guild-economy D-6).

One JSON-safe ``CombatSessionRecord`` lives under
``PlayerCharacter.db.active_combat`` and stores participant dbrefs plus
fled/knockout identity and the accumulated round count -- never live objects.
``engage`` creates a session and waits for player input; each preflight-valid
player action drives exactly one ordinary round (or the resolver-backed
overwhelm compression), and the accumulated round time settles exactly once at
a terminal outcome through ``settle_combat_result``.
"""

from dataclasses import dataclass, replace
from enum import StrEnum
from types import SimpleNamespace
from typing import Any

from evennia.objects.models import ObjectDB

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from world.rules.action import ActionRequest, ActionResolver, _stored_trait_value
from world.rules.combat import (
    COMBAT_YAML,
    Battlefield,
    BattlefieldActionContext,
    is_battle_over,
    run_round,
)
from world.rules.clock import settle_combat_result
from world.rules.monster_behaviour import monster_behaviour_policy
from world.rules.overwhelm import classify_overwhelm, resolve_overwhelm
from world.rules.skip_safety import (
    register_active_battlefield,
    unregister_active_battlefield,
)
from world.skills.registry import SKILL_REGISTRY

BASIC_ATTACK_KEY = "basic_attack"
_ROUND_SECONDS = int(COMBAT_YAML["round"]["seconds"])


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


def from_storage(data: dict[str, Any]) -> CombatSessionRecord:
    """Strictly parse one storage dict, raising ``CombatSessionError`` on violations."""
    if not isinstance(data, dict):
        raise CombatSessionError(
            SessionReason.MALFORMED_SESSION, "active_combat must be a dict"
        )
    unknown = set(data) - _RECORD_FIELDS
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


def is_in_active_session(actor: Any) -> bool:
    """Return whether ``actor`` carries a valid active combat session."""
    try:
        return read_session(actor) is not None
    except CombatSessionError:
        return False


def reconstruct_battlefield(actor: Any, record: CombatSessionRecord) -> Battlefield:
    """Resolve a session's dbrefs into a live battlefield for one action."""
    room = ObjectDB.objects.filter(id=record.room_id).first()
    if room is None:
        raise CombatSessionError(SessionReason.ROOM_MISSING)
    if actor.location is not room:
        raise CombatSessionError(SessionReason.MOVED)
    player_ids = list(record.player_ids)
    if actor.pk not in player_ids:
        raise CombatSessionError(SessionReason.UNKNOWN_SESSION_ID)
    player_id = actor.pk

    def resolve(dbref):
        return ObjectDB.objects.filter(id=dbref).first()

    entities = {}
    key_by_pk = {}
    for dbref in player_ids:
        entity = resolve(dbref)
        if entity is None:
            raise CombatSessionError(
                SessionReason.MISSING_PARTICIPANT, f"player dbref {dbref} missing"
            )
        if str(entity.key) in entities:
            raise CombatSessionError(
                SessionReason.DUPLICATE_PARTICIPANT,
                f"participant key {entity.key!r} is not unique",
            )
        entities[entity.key] = entity
        key_by_pk[dbref] = entity.key
    for dbref in record.enemy_ids:
        entity = resolve(dbref)
        if entity is None:
            raise CombatSessionError(
                SessionReason.MISSING_PARTICIPANT, f"enemy dbref {dbref} missing"
            )
        if str(entity.key) in entities:
            raise CombatSessionError(
                SessionReason.DUPLICATE_PARTICIPANT,
                f"participant key {entity.key!r} is not unique",
            )
        entities[entity.key] = entity
        key_by_pk[dbref] = entity.key

    player_entity = resolve(player_id)
    if player_entity is None or _stored_trait_value(player_entity.traits.hp) <= 0:
        raise CombatSessionError(SessionReason.INVALID_RECOVERY)
    teams = {
        "party": frozenset(key_by_pk[dbref] for dbref in player_ids),
        "foes": frozenset(key_by_pk[dbref] for dbref in record.enemy_ids),
    }
    battlefield = Battlefield(teams, entities)
    battlefield.fled = {
        key_by_pk[dbref]
        for dbref in record.fled_ids
        if dbref in key_by_pk
    }
    return battlefield


def _context_for(battlefield: Battlefield, record: CombatSessionRecord) -> BattlefieldActionContext:
    event_context: dict[str, Any] = {"battlefield": battlefield}
    if record.mode == "guild_exam":
        event_context["nonlethal"] = True
    return BattlefieldActionContext(battlefield, event_context=event_context)


def _basic_attack_request(
    entity: Any,
    battlefield: Battlefield,
    record: CombatSessionRecord,
) -> ActionRequest | None:
    """Return a deterministic ``basic_attack`` against the lowest-HP living enemy."""
    enemy_keys = next(
        (
            members
            for team, members in battlefield.teams.items()
            if team != battlefield.team_of(str(entity.key))
        ),
        frozenset(),
    )
    candidates = [
        battlefield.roster[key]
        for key in enemy_keys
        if key in battlefield.roster
        and key not in battlefield.fled
        and _stored_trait_value(battlefield.roster[key].traits.hp) > 0
    ]
    if not candidates:
        return None
    target = min(
        candidates,
        key=lambda enemy: (_stored_trait_value(enemy.traits.hp), str(enemy.key)),
    )
    context = _context_for(battlefield, record)
    return ActionRequest(entity, BASIC_ATTACK_KEY, [target], context)


def _enemy_policy(
    entity: Any,
    battlefield: Battlefield,
    record: CombatSessionRecord,
):
    """Return one deterministic enemy action with the session's combat context.

    ``monster_behaviour_policy`` falls back to ``default_attack_policy`` for
    non-Monster combatants, so a guild-examination NPC opponent (which has no
    ``threat_tier``) still acts through its profile skills. The request context
    is rebuilt with the session's nonlethal policy so examination opponents can
    knock out but never kill the candidate.
    """
    request = monster_behaviour_policy(entity, battlefield)
    if request is None:
        return None
    return ActionRequest(
        actor=request.actor,
        skill_key=request.skill_key,
        targets=list(request.targets),
        context=_context_for(battlefield, record),
    )


def _round_provider(actor: Any, request: ActionRequest, battlefield: Battlefield, record: CombatSessionRecord):
    """Supply the queued player request exactly once and deterministic enemy policies."""
    used = False

    def provider(entity, field):
        nonlocal used
        if entity.key == actor.key:
            if used:
                return None
            used = True
            return request
        return _enemy_policy(entity, field, record)

    return provider


def _overwhelm_provider(actor: Any, first_request: ActionRequest, battlefield: Battlefield, record: CombatSessionRecord):
    """Supply the selected request once, then deterministic basic attacks."""
    used = False

    def provider(entity, field):
        nonlocal used
        if entity.key == actor.key:
            if not used:
                used = True
                return first_request
            return _basic_attack_request(entity, field, record)
        return _enemy_policy(entity, field, record)

    return provider


def _persist(actor: Any, record: CombatSessionRecord) -> None:
    actor.db.active_combat = to_storage(record)


def clear_session(actor: Any, battlefield: Battlefield | None = None) -> None:
    """Clear session/context state and skip-safety registration."""
    actor.db.active_combat = None
    actor.ndb.action_context = None
    unregister_active_battlefield(actor)
    if battlefield is not None:
        for key in list(battlefield.roster):
            unregister_active_battlefield(battlefield.roster[key])


def engage(actor: Any, target: Any) -> dict[str, Any]:
    """Create one persistent hostile session for a present living monster.

    Validates a PlayerCharacter with no active session and a living hostile
    ``Monster`` in the same room. Registers the reconstructed battlefield with
    skip safety and records the initial overwhelm classification, but runs no
    action before the player chooses one.
    """
    if not isinstance(actor, PlayerCharacter):
        raise CombatSessionError(SessionReason.NOT_A_PLAYER)
    if read_session(actor) is not None:
        raise CombatSessionError(SessionReason.ALREADY_IN_COMBAT)
    if not isinstance(target, Monster):
        raise CombatSessionError(SessionReason.NOT_HOSTILE)
    if actor.location is None or target.location is not actor.location:
        raise CombatSessionError(SessionReason.NOT_PRESENT)
    if _stored_trait_value(target.traits.hp) <= 0:
        raise CombatSessionError(SessionReason.TARGET_DEAD)

    record = CombatSessionRecord(
        session_id=session_id_for(actor, "hostile"),
        mode="hostile",
        room_id=int(actor.location.pk),
        player_ids=(int(actor.pk),),
        enemy_ids=(int(target.pk),),
        fled_ids=(),
        knocked_out_ids=(),
        rounds_elapsed=0,
        exam_id=None,
    )
    battlefield = reconstruct_battlefield(actor, record)
    _persist(actor, record)
    register_active_battlefield(battlefield)
    return {
        "record": record,
        "overwhelming_team": classify_overwhelm(battlefield),
    }


def _knocked_out_ids(logs, battlefield) -> tuple[int, ...]:
    """Return the dbrefs of entities marked knocked out by the round's logs."""
    knocked = set()
    for event_log in logs:
        for entry in event_log.entries:
            if entry.kind != "target_knocked_out":
                continue
            target_id = entry.data.get("target_id")
            if isinstance(target_id, int):
                knocked.add(target_id)
    return tuple(sorted(knocked))


def submit_player_action(actor: Any, skill_key: str, target: Any) -> dict[str, Any]:
    """Run one ordinary round (or overwhelm compression) for one player action.

    ``target`` may be ``None`` for self-target skills; otherwise it must be a
    live roster member. A preflight rejection returns before initiative and
    consumes no round or world time.
    """
    record = read_session(actor)
    if record is None:
        raise CombatSessionError(SessionReason.NO_ACTIVE_SESSION)
    battlefield = reconstruct_battlefield(actor, record)
    if _stored_trait_value(actor.traits.hp) <= 0:
        raise CombatSessionError(SessionReason.INVALID_RECOVERY)
    if target is not None and str(target.key) not in battlefield.roster:
        raise CombatSessionError(SessionReason.NOT_PRESENT)

    request = ActionRequest(
        actor=actor,
        skill_key=skill_key,
        targets=[] if target is None else [target],
        context=_context_for(battlefield, record),
    )
    preflight = ActionResolver.preflight(request)
    if preflight.outcome == "rejected":
        return {
            "outcome": "rejected",
            "reason": preflight.reason,
            "detail": preflight.detail,
        }

    overwhelming = classify_overwhelm(battlefield)
    player_team = battlefield.team_of(str(actor.key))
    if overwhelming == player_team:
        provider = _overwhelm_provider(actor, request, battlefield, record)
        result = resolve_overwhelm(battlefield, provider, max_rounds=12)
        logs = result.event_logs
        gained = result.rounds_elapsed
    else:
        provider = _round_provider(actor, request, battlefield, record)
        logs = run_round(battlefield, provider)
        gained = 1

    knocked = _knocked_out_ids(logs, battlefield)
    new_record = replace(
        record,
        fled_ids=tuple(
            sorted(
                int(battlefield.roster[key].pk)
                for key in battlefield.fled
                if key in battlefield.roster
            )
        ),
        knocked_out_ids=tuple(sorted(set(record.knocked_out_ids) | set(knocked))),
        rounds_elapsed=record.rounds_elapsed + gained,
    )
    _persist(actor, new_record)
    return _continue_or_settle(actor, new_record, battlefield, logs)


def _team_living(battlefield: Battlefield, team: str, record: CombatSessionRecord | None = None) -> bool:
    knocked = set(record.knocked_out_ids) if record is not None else set()
    return any(
        key in battlefield.roster
        and key not in battlefield.fled
        and battlefield.roster[key].pk not in knocked
        and _stored_trait_value(battlefield.roster[key].traits.hp) > 0
        for key in battlefield.teams[team]
    )


def _terminal_outcome(
    actor: Any,
    battlefield: Battlefield,
    record: CombatSessionRecord,
) -> str | None:
    """Return the deterministic terminal outcome, or ``None`` to continue."""
    player_team = battlefield.team_of(str(actor.key))
    foe_team = next(team for team in battlefield.teams if team != player_team)
    if str(actor.key) in battlefield.fled:
        return "fled"
    if not _team_living(battlefield, player_team, record):
        return "defeat" if record.mode == "hostile" else "exam_failed"
    if not _team_living(battlefield, foe_team, record):
        return "victory" if record.mode == "hostile" else "exam_passed"
    if record.rounds_elapsed >= _round_cap():
        return "cap"
    return None


def _round_cap() -> int:
    return int(COMBAT_YAML.get("max_rounds", 100))


def _continue_or_settle(
    actor: Any,
    record: CombatSessionRecord,
    battlefield: Battlefield,
    logs,
) -> dict[str, Any]:
    outcome = _terminal_outcome(actor, battlefield, record)
    if outcome is None:
        return {
            "outcome": "round",
            "rounds_elapsed": record.rounds_elapsed,
            "logs": tuple(logs),
            "overwhelming_team": classify_overwhelm(battlefield),
        }
    return settle_session(actor, record, battlefield, outcome, logs)


def settle_session(
    actor: Any,
    record: CombatSessionRecord,
    battlefield: Battlefield | None,
    outcome: str,
    logs=(),
) -> dict[str, Any]:
    """Settle accumulated round time once and clear session state (D-6).

    Exam sessions persist their PASS/FAIL terminal state and close the active
    session FIRST; only after that does combat time settle exactly once. A
    failure before the exam write leaves the session intact so a retry cannot
    advance the clock twice for the same rounds. Hostile sessions settle time
    then clear.
    """
    exam_result = None
    if record.mode == "guild_exam":
        from world.rules.guild_exams import settle_exam_outcome

        exam_result = settle_exam_outcome(actor, record, battlefield, outcome)
        # The exam terminal state is persisted and idempotent by exam ID; clear
        # the session before advancing time so a clock failure cannot cause a
        # second advance for the same rounds on a retry.
        clear_session(actor, battlefield)
    events = settle_combat_result(
        SimpleNamespace(total_seconds=record.rounds_elapsed * _ROUND_SECONDS),
        [actor],
    )
    clear_session(actor, battlefield)
    return {
        "outcome": outcome,
        "rounds_elapsed": record.rounds_elapsed,
        "logs": tuple(logs),
        "events": tuple(events),
        "exam": exam_result,
    }


def forfeit(actor: Any) -> dict[str, Any]:
    """Settle accumulated time, record defeat/exam FAIL, and clean up."""
    record = read_session(actor)
    if record is None:
        raise CombatSessionError(SessionReason.NO_ACTIVE_SESSION)
    battlefield = None
    try:
        battlefield = reconstruct_battlefield(actor, record)
    except CombatSessionError:
        battlefield = None
    outcome = "defeat" if record.mode == "hostile" else "exam_failed"
    return settle_session(actor, record, battlefield, outcome)


def restore_active_session(actor: Any) -> None:
    """Reconstruct a valid persisted session or terminate it diagnostically.

    Missing, deleted, moved, duplicated, or malformed participants close the
    session deterministically: hostile sessions settle as defeat, examinations
    as FAIL, leaving no orphan opponent and no blocked player.
    """
    record = read_session(actor)
    if record is None:
        return
    try:
        battlefield = reconstruct_battlefield(actor, record)
        outcome = _terminal_outcome(actor, battlefield, record)
        if outcome is not None:
            settle_session(actor, record, battlefield, outcome)
            return
        register_active_battlefield(battlefield)
    except Exception as error:
        from evennia.utils.logger import log_warn

        log_warn(
            f"combat_session: terminating invalid session for {actor.key}: {error}"
        )
        settle_session(
            actor,
            record,
            None,
            "defeat" if record.mode == "hostile" else "exam_failed",
        )