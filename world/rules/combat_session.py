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
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    SNAPSHOTTED_SURFACES,
    _restore_touched_best_effort,
    _snapshot_touched,
    _stored_trait_value,
)
from world.rules.action_preview import revalidate_submission
from world.rules.combat import (
    COMBAT_YAML,
    Battlefield,
    BattlefieldActionContext,
    is_battle_over,
    run_round,
)
from world.rules.clock import get_world_clock, settle_combat_result
from world.rules.monster_behaviour import monster_behaviour_policy
from world.rules.overwhelm import classify_overwhelm, resolve_overwhelm
from world.rules.skip_safety import (
    register_active_battlefield,
    unregister_active_battlefield,
)
from world.skills.registry import SKILL_REGISTRY

BASIC_ATTACK_KEY = "basic_attack"
_ROUND_SECONDS = int(COMBAT_YAML["round"]["seconds"])

# Surfaces the outer round-and-settlement transaction snapshots on every
# participant. ``instance_pin`` is excluded because it lives on rooms, not
# combatants; the session room is snapshotted with it separately.
_ROUND_ENTITY_SURFACES = frozenset(SNAPSHOTTED_SURFACES - {"instance_pin"})
_ROOM_SURFACES = frozenset({"instance_pin"})


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
# Optional field: written only when the terminal settlement committed. Older
# durable records without it stay valid, so it is never a required field.
_OPTIONAL_RECORD_FIELDS = frozenset({"settled_tick"})


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


_TOKEN_RE = None


def _token_pattern() -> str:
    return r"^(a|e)(\d+)$"


def resolve_target_token(
    actor: Any,
    token: str,
) -> Any:
    """Resolve one session-local ``aN``/``eN`` token to a live participant.

    Tokens stay bound to the same dbref for the session lifetime because the
    persisted ``player_ids`` then ``enemy_ids`` tuples are immutable. The token
    is a presentation alias; it is never persisted separately.
    """
    import re

    record = read_session(actor)
    if record is None:
        raise CombatSessionError(SessionReason.NO_ACTIVE_SESSION)
    match = re.fullmatch(_token_pattern(), token.strip())
    if match is None:
        raise CombatSessionError(SessionReason.UNKNOWN_SESSION_ID)
    prefix, raw_index = match.groups()
    index = int(raw_index)
    if prefix == "a":
        if not 1 <= index <= len(record.player_ids):
            raise CombatSessionError(SessionReason.UNKNOWN_SESSION_ID)
        dbref = record.player_ids[index - 1]
    else:
        if not 1 <= index <= len(record.enemy_ids):
            raise CombatSessionError(SessionReason.UNKNOWN_SESSION_ID)
        dbref = record.enemy_ids[index - 1]
    from evennia.objects.models import ObjectDB

    entity = ObjectDB.objects.filter(id=dbref).first()
    if entity is None:
        raise CombatSessionError(
            SessionReason.MISSING_PARTICIPANT, f"token dbref {dbref} missing"
        )
    return entity


def parse_session_targets(
    actor: Any,
    target_value: str,
    *,
    search: Any | None = None,
) -> list[Any] | str:
    """Parse an active-session target value into facade input.

    Accepts one ``aN``/``eN`` token, a comma-separated list of tokens only, or
    one complete approved AREA shorthand. A one-target display-name search is
    retained for backward Telnet parity. Rejects duplicate tokens, token/name
    mixtures, and shorthand/token mixtures before preview.
    """
    from world.rules.targeting import AREA_SHORTHANDS

    stripped = target_value.strip()
    if not stripped:
        return []
    if stripped in AREA_SHORTHANDS:
        if "," in stripped:
            raise CombatSessionError(SessionReason.UNKNOWN_SESSION_ID)
        return stripped
    parts = [part.strip() for part in stripped.split(",")]
    if any(part in AREA_SHORTHANDS for part in parts):
        raise CombatSessionError(SessionReason.UNKNOWN_SESSION_ID)
    is_token = lambda part: bool(__import__("re").fullmatch(_token_pattern(), part))
    if all(is_token(part) for part in parts):
        seen: set[str] = set()
        resolved: list[Any] = []
        for part in parts:
            if part in seen:
                raise CombatSessionError(SessionReason.DUPLICATE_PARTICIPANT)
            seen.add(part)
            resolved.append(resolve_target_token(actor, part))
        return resolved
    if any(is_token(part) for part in parts) or len(parts) > 1:
        raise CombatSessionError(SessionReason.UNKNOWN_SESSION_ID)
    if search is None:
        raise CombatSessionError(SessionReason.UNKNOWN_SESSION_ID)
    target = search(stripped)
    if target is None:
        raise CombatSessionError(SessionReason.UNKNOWN_SESSION_ID)
    return [target]


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
    battlefield.knocked_out = {
        key_by_pk[dbref]
        for dbref in record.knocked_out_ids
        if dbref in key_by_pk
    }
    return battlefield


def _session_policy(
    battlefield: Battlefield,
    record: CombatSessionRecord,
) -> tuple[bool, frozenset[str]]:
    """Return the session's ``(simulated, nonlethal_keys)`` combat policy.

    Guild examinations run as simulated combat (no companion protection);
    hostile sessions with companions carry the per-entity ``nonlethal_keys``
    set naming the allied companions (party-combat D-3). ``_context_for``
    and the round/overwhelm entry points derive the same policy from this
    one helper (fix-dot-kill-credit D4).
    """
    if record.mode == "guild_exam":
        return True, frozenset()
    if len(record.player_ids) > 1:
        companion_pks = set(record.player_ids[1:])
        return False, frozenset(
            key
            for key, entity in battlefield.roster.items()
            if int(entity.pk) in companion_pks
        )
    return False, frozenset()


def _context_for(battlefield: Battlefield, record: CombatSessionRecord) -> BattlefieldActionContext:
    """Build the session's action context with its damage and reward policy.

    Hostile sessions carry ``nonlethal_keys`` naming the allied companions, so
    damage floors companions at 1 HP and marks them knocked out per target
    while monsters stay lethal (party-combat D-3). Guild examinations run as
    ordinary lethal combat with a ``simulated`` marker instead of a nonlethal
    policy: defeats are real HP crossings, but kill-credit consumers treat
    them as simulation outcomes (exam-simulated-battle-redesign D1/D4).
    """
    simulated, nonlethal_keys = _session_policy(battlefield, record)
    event_context: dict[str, Any] = {"battlefield": battlefield}
    if simulated:
        event_context["simulated"] = True
    elif nonlethal_keys:
        event_context["nonlethal_keys"] = nonlethal_keys
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
        and not battlefield.is_knocked_out(key)
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
    is rebuilt from the session record, so examination opponents fight with
    ordinary lethal semantics inside the simulated battle.
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


def clear_session(
    actor: Any,
    battlefield: Battlefield | None = None,
    record: CombatSessionRecord | None = None,
) -> None:
    """Clear session/context state and skip-safety registration.

    Every persisted participant is unregistered (party-combat D-5): when the
    battlefield cannot be reconstructed, the record's participant dbrefs still
    release surviving companions and monsters from skip safety, and the
    participant scan purges even a deleted participant's stale key, so no
    registration of the session survives settlement.
    """
    from world.rules.skip_safety import unregister_participants

    actor.db.active_combat = None
    actor.ndb.action_context = None
    unregister_active_battlefield(actor)
    if battlefield is not None:
        for key in list(battlefield.roster):
            unregister_active_battlefield(battlefield.roster[key])
    if record is not None:
        unregister_participants((*record.player_ids, *record.enemy_ids))


def engage(actor: Any, target: Any) -> dict[str, Any]:
    """Create one persistent hostile session for a present living monster.

    Validates a PlayerCharacter with no active session and a living hostile
    ``Monster`` in the same room. Every bound companion that is co-located,
    living, and not knocked out joins the session's allied team in
    deterministic party order (party-combat D-1). Registers the reconstructed
    battlefield with skip safety and records the initial overwhelm
    classification, but runs no action before the player chooses one.
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

    from world.rules.party import combat_companions

    companions = [
        int(companion.pk) for companion in combat_companions(actor)
    ]
    record = CombatSessionRecord(
        session_id=session_id_for(actor, "hostile"),
        mode="hostile",
        room_id=int(actor.location.pk),
        player_ids=(int(actor.pk), *companions),
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
    """Return the dbrefs of entities marked knocked out by the round.

    Merges the round's ``target_knocked_out`` log identities with the
    battlefield's in-round ``knocked_out`` markings, so exam-flag knockouts
    (persisted from logs only) and per-entity companion knockouts (marked at
    damage-commit time) both survive the round-end persistence.
    """
    knocked = set()
    for event_log in logs:
        for entry in event_log.entries:
            if entry.kind != "target_knocked_out":
                continue
            target_id = entry.data.get("target_id")
            if isinstance(target_id, int):
                knocked.add(target_id)
    for key in battlefield.knocked_out:
        entity = battlefield.roster.get(key)
        if entity is not None:
            knocked.add(int(entity.pk))
    return tuple(sorted(knocked))


def _snapshot_round_touched(
    actor: Any,
    battlefield: Battlefield,
    record: CombatSessionRecord,
) -> tuple[
    tuple[tuple[Any, frozenset[str], dict[str, Any]], ...],
    dict[str, tuple[bool, Any]],
]:
    """Snapshot every entity the round-and-settlement chain may touch.

    Covers all participants (entity surfaces plus ``quest_log`` so quest
    transitions credited or failed from combat defeats roll back), the
    battlefield's own in-process ``fled``/``knocked_out`` state, the session
    room's ``pin_reasons``, and the actor's session/exam attributes that the
    settlement chain writes (``active_combat``, and ``guild_rank``/
    ``guild_exams`` for examinations). The entity surfaces come from the
    shared snapshot handler registration, so a new effect surface raises at
    registration time instead of silently escaping the outer rollback
    (fix-combat-settlement-recovery D1). Returns ``(obj, surfaces, snapshot)``
    tuples plus the actor's extra attribute snapshots for restoration; the
    caller additionally snapshots the party and relations surfaces the
    friendly-fire scan writes.
    """
    from world.rules.action import _attribute_snapshot

    touched = [
        (
            entity,
            _ROUND_ENTITY_SURFACES,
            _snapshot_touched(entity, _ROUND_ENTITY_SURFACES),
        )
        for entity in battlefield.roster.values()
    ]
    touched.append(
        (
            battlefield,
            _ROUND_ENTITY_SURFACES,
            _snapshot_touched(battlefield, _ROUND_ENTITY_SURFACES),
        )
    )
    room = actor.location
    if room is not None:
        touched.append(
            (
                room,
                _ROOM_SURFACES,
                _snapshot_touched(room, _ROOM_SURFACES),
            )
        )
    room_pk = getattr(room, "pk", None)
    # Quest DEFEAT transitions release the stage pin of every active quest
    # stage, which may live in a room outside the session; snapshot those
    # rooms too so an outer rollback restores their in-process pins.
    raw_quests = actor.db.quest_log
    if raw_quests:
        for quest in raw_quests:
            room_id = quest.get("stage_room_id") if isinstance(quest, dict) else None
            if not isinstance(room_id, int) or room_id == room_pk:
                continue
            stage_room = ObjectDB.objects.filter(id=room_id).first()
            if stage_room is not None:
                touched.append(
                    (
                        stage_room,
                        _ROOM_SURFACES,
                        _snapshot_touched(stage_room, _ROOM_SURFACES),
                    )
                )
    extra: dict[str, tuple[bool, Any]] = {
        "active_combat": _attribute_snapshot(actor, "active_combat"),
    }
    if record.mode == "guild_exam":
        extra["guild_rank"] = _attribute_snapshot(actor, "guild_rank")
        extra["guild_exams"] = _attribute_snapshot(actor, "guild_exams")
    return tuple(touched), extra


def _snapshot_party_surfaces(
    actor: Any,
    battlefield: Battlefield,
) -> tuple[list[Any], dict[int, Any], dict[int, Any]]:
    """Snapshot the party/relations surfaces the friendly-fire scan writes."""
    from world.rules.party import party_ids

    party_before = list(actor.db.party or ())
    members_before: dict[int, Any] = {}
    relations_before: dict[int, Any] = {}
    companion_pks = set(party_ids(actor))
    if companion_pks:
        for entity in battlefield.roster.values():
            pk = getattr(entity, "pk", None)
            if isinstance(pk, int) and pk in companion_pks:
                members_before[pk] = entity.db.party_member
                relations_before[pk] = entity.db.relations_data
    return party_before, members_before, relations_before


def _restore_round_touched(
    actor: Any,
    touched: tuple[tuple[Any, frozenset[str], dict[str, Any]], ...],
    extra: dict[str, tuple[bool, Any]],
    party_before: list[Any],
    members_before: dict[int, Any],
    relations_before: dict[int, Any],
) -> None:
    """Restore every snapshotted surface after a rolled-back round."""
    from world.rules.action import _restore_attribute

    for obj, surfaces, snapshot in touched:
        _restore_touched_best_effort(obj, snapshot, surfaces)
    for key, snapshot in extra.items():
        _restore_attribute(actor, key, snapshot)
    if party_before or members_before:
        from world.rules.affinity import restore_relations_surfaces
        from world.rules.party import restore_membership_surfaces

        restore_membership_surfaces(actor, party_before, members_before)
        restore_relations_surfaces(relations_before)


def _scan_friendly_fire(
    actor: Any,
    battlefield: Battlefield,
    logs: list[Any],
) -> tuple[str, ...]:
    """Apply per-hit friendly-fire penalties for one resolved player round.

    Scans the round's damage events produced by the player's own action
    (EventLogs whose ``actor`` is the player) against ally-side companion
    NPCs: a hit qualifies when the target is an NPC in the snapshotted
    ``player.db.party`` set and present on the battlefield. Each qualifying
    hit calls the sole affinity writer once with the ``friendly_fire`` source
    and the rulebook penalty, inside one transaction that also covers every
    resulting auto-leave -- a failure rolls the whole round's affinity effects
    back. Returns the auto-leave notification lines; the caller delivers them
    only after the transaction commits (the writer never notifies).
    """
    from django.db import transaction

    from typeclasses.npcs import NPC
    from world.rules.affinity import AffinitySource, apply_affinity_change
    from world.rules.affinity_config import get_config
    from world.rules.party import party_ids

    companion_pks = set(party_ids(actor))
    if not companion_pks:
        return ()
    player_key = str(actor.key)
    hits: list[Any] = []
    for event_log in logs:
        if event_log.actor != player_key:
            continue
        for entry in event_log.entries:
            if entry.kind != "damage":
                continue
            target = battlefield.roster.get(entry.target)
            if (
                target is None
                or not isinstance(target, NPC)
                or int(target.pk) not in companion_pks
            ):
                continue
            hits.append(target)
    if not hits:
        return ()
    penalty = get_config().friendly_fire_penalty_per_hit
    notifications: list[str] = []
    party_before = list(actor.db.party or ())
    members_before = {
        int(target.pk): target.db.party_member for target in hits
    }
    relations_before = {
        int(target.pk): target.db.relations_data for target in hits
    }
    try:
        with transaction.atomic():
            for target in hits:
                outcome = apply_affinity_change(
                    target, actor, AffinitySource.FRIENDLY_FIRE, -penalty
                )
                if outcome.auto_leave_notification is not None:
                    notifications.append(outcome.auto_leave_notification)
    except Exception:
        # The round's transaction rolled the database back; restore the
        # in-process attribute surfaces so readers never observe the
        # rolled-back values (the idmapper cache is not transaction-aware).
        from world.rules.affinity import restore_relations_surfaces
        from world.rules.party import restore_membership_surfaces

        restore_membership_surfaces(actor, party_before, members_before)
        restore_relations_surfaces(relations_before)
        raise
    return tuple(notifications)


def submit_player_action(
    actor: Any,
    skill_key: str,
    targets_or_shorthand: list[Any] | str,
) -> dict[str, Any]:
    """Run one ordinary round (or overwhelm compression) for one player action.

    ``targets_or_shorthand`` is either a concrete list of live participant
    objects or one approved AREA shorthand (``all-enemies``, ``all-allies``,
    ``all``). Player-facing NONE and SELF input must be an empty list; SELF is
    bound to the actor inside the rules layer. The facade revalidates the
    submitted target value through the shared side-effect-free preview, runs
    ``ActionResolver.preflight()``, and only then starts one round (or the
    resolver-backed overwhelm compression). A rejection returns before
    initiative and consumes no round or world time.
    """
    record = read_session(actor)
    if record is None:
        raise CombatSessionError(SessionReason.NO_ACTIVE_SESSION)
    battlefield = reconstruct_battlefield(actor, record)
    if _stored_trait_value(actor.traits.hp) <= 0:
        raise CombatSessionError(SessionReason.INVALID_RECOVERY)
    if not isinstance(targets_or_shorthand, (list, str)):
        raise TypeError("submit_player_action requires an explicit target list or shorthand")
    if not isinstance(targets_or_shorthand, str) and not all(
        str(target.key) in battlefield.roster
        for target in targets_or_shorthand
    ):
        raise CombatSessionError(SessionReason.NOT_PRESENT)

    context = _context_for(battlefield, record)
    preview = revalidate_submission(
        actor, skill_key, context, targets_or_shorthand
    )
    if not preview.enabled:
        return {
            "outcome": "rejected",
            "reason": preview.reason,
            "detail": preview.detail,
        }

    request = ActionRequest(
        actor=actor,
        skill_key=skill_key,
        targets=targets_or_shorthand,
        context=context,
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
    touched, extra = _snapshot_round_touched(actor, battlefield, record)
    party_before, members_before, relations_before = _snapshot_party_surfaces(
        actor, battlefield
    )
    from django.db import transaction

    notifications: tuple[str, ...] = ()
    simulated, nonlethal_keys = _session_policy(battlefield, record)
    try:
        with transaction.atomic():
            # Shared outer transaction (fix-combat-settlement-recovery D1):
            # round effects, friendly-fire penalties, session metadata, and
            # the terminal settlement commit (or roll back) as one unit, so a
            # process termination can never leave half-round durable state.
            # Later combat changes that edit this seam (roster-and-overwhelm,
            # friendly-fire reachability) must keep edits inside this block.
            # Compression is player-direction only (fix-combat-session-roster-
            # and-overwhelm D2). ``classify_overwhelm`` can return the foe
            # team (reverse overwhelm) or None (contested); neither verdict
            # ever dispatches the resolver. A foe-overwhelming encounter
            # deliberately plays out one ordinary round per player submission
            # so the player keeps full per-round agency (skill choice and
            # flee) and is never forced into an unavoidable compressed defeat;
            # the informational ``overwhelming_team`` output value is
            # unchanged. The session's simulated/nonlethal policy threads
            # into the round and overwhelm compression so upkeep-settled
            # ticks honor the same credit rules as direct damage
            # (fix-dot-kill-credit D4).
            if overwhelming == player_team:
                provider = _overwhelm_provider(actor, request, battlefield, record)
                result = resolve_overwhelm(
                    battlefield,
                    provider,
                    max_rounds=12,
                    commanded_actor=str(actor.key),
                    commanded_skill=skill_key,
                    simulated=simulated,
                    nonlethal_keys=nonlethal_keys,
                )
                logs = result.event_logs
                gained = result.rounds_elapsed
            else:
                # Foe-overwhelming and contested verdicts: one ordinary round.
                provider = _round_provider(actor, request, battlefield, record)
                logs = run_round(
                    battlefield,
                    provider,
                    simulated=simulated,
                    nonlethal_keys=nonlethal_keys,
                )
                gained = 1

            notifications = _scan_friendly_fire(actor, battlefield, logs)

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
            result = _continue_or_settle(actor, new_record, battlefield, logs)
    except Exception:
        # The outer transaction rolled the database back; restore the
        # in-process attribute surfaces so readers never observe the
        # rolled-back values (the idmapper cache is not transaction-aware),
        # and re-register skip safety because clear_session ran in-process.
        _restore_round_touched(
            actor,
            touched,
            extra,
            party_before,
            members_before,
            relations_before,
        )
        register_active_battlefield(battlefield)
        raise
    # Deliver auto-leave notices only after the whole round committed, so a
    # rolled-back round never shows a fake disengagement notification.
    for line in notifications:
        actor.msg(line)
    return result


def _team_living(
    battlefield: Battlefield,
    team: str,
    record: CombatSessionRecord,
) -> bool:
    """Return whether a team has any living, present, active member.

    The persisted ``knocked_out_ids`` (exam knockouts and the previous round's
    markings) and the battlefield's in-round ``knocked_out`` set (marked at
    damage-commit time) both count, so a knocked-out member is never "living"
    through either source (party-combat D-2).
    """
    knocked = set(record.knocked_out_ids) | {
        int(entity.pk)
        for key, entity in battlefield.roster.items()
        if key in battlefield.knocked_out and key in battlefield.roster
    }
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
    """Return the deterministic terminal outcome, or ``None`` to continue.

    Player-centric (party-combat D-4): the session ends on the player's flee,
    knockout, or death even when companions stand; only the foes team decides
    victory. A knocked-out companion is battlefield state, never a terminal
    condition.
    """
    player_team = battlefield.team_of(str(actor.key))
    foe_team = next(team for team in battlefield.teams if team != player_team)
    if str(actor.key) in battlefield.fled:
        return "fled"
    player_key = str(actor.key)
    player_defeated = (
        _stored_trait_value(actor.traits.hp) <= 0
        or player_key in battlefield.knocked_out
        or int(actor.pk) in record.knocked_out_ids
    )
    if player_defeated:
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

    The whole terminal settlement is one durable transaction (fix-combat-
    settlement-recovery D2): the exam outcome (guild-exam mode), the combat
    clock advance, the durable ``settled_tick`` marker, the session clear,
    and the simulated-battle gauge restoration commit or roll back together.
    A crash mid-settlement therefore never loses exam time, never double-
    counts hostile time, never leaves a half-settled session, and never
    strands a defeated exam candidate; the marker additionally lets a
    restart skip re-settlement for any durable record already marked
    settled. The session clear is the last step inside the transaction
    (followed by the exam gauge restoration), so a failure of any earlier
    step leaves the durable session intact for exactly one retry. Exam
    opponents are deleted only after the transaction commits: a rolled-back
    settlement must leave the temporary opponent alive for the retry, and
    deleting inside the transaction could strand a stale deleted instance
    in the idmapper cache.
    """
    from django.db import transaction

    exam_result = None
    with transaction.atomic():
        if record.mode == "guild_exam":
            from world.rules.guild_exams import settle_exam_outcome

            exam_result = settle_exam_outcome(actor, record, battlefield, outcome)
        # Settlement regenerates every living, non-fled roster member
        # (fix-combat-session-roster-and-overwhelm D1): companions and any
        # non-defeated foe still present recover for the accumulated combat
        # seconds, so a knocked-out companion can rise above the nonlethal
        # HP floor and rejoin a later engagement. A member at 0 HP is dead
        # and excluded (kill semantics). The actor alone keeps the historical
        # scope only when the actor is still living (recovery fallback with a
        # live actor, or a solo flee whose actor is alive); a dead actor is
        # never passed, so settlement can never revive a defeated player.
        participants = (
            [
                entity
                for key, entity in battlefield.roster.items()
                if key not in battlefield.fled
                and _stored_trait_value(entity.traits.hp) > 0
            ]
            if battlefield is not None
            else []
        )
        if not participants and _stored_trait_value(actor.traits.hp) > 0:
            participants = [actor]
        events = settle_combat_result(
            SimpleNamespace(total_seconds=record.rounds_elapsed * _ROUND_SECONDS),
            participants,
        )
        # Record the world tick at which the settlement committed; a non-None
        # value marks the session as settled for any later reader.
        _persist(
            actor,
            replace(record, settled_tick=get_world_clock().tick),
        )
        clear_session(actor, battlefield, record)
        if record.mode == "guild_exam":
            # Simulated battle: restore both sides inside the settlement
            # transaction, so the full-restoration guarantee commits or rolls
            # back with the exam outcome and can never strand a defeated
            # candidate (exam-simulated-battle-redesign D3). Opponent deletion
            # stays post-commit so a rolled-back settlement keeps it alive.
            _restore_exam_participants(actor, record, battlefield)
    if record.mode == "guild_exam":
        _delete_exam_opponent(actor, record)
    return {
        "outcome": outcome,
        "rounds_elapsed": record.rounds_elapsed,
        "logs": tuple(logs),
        "events": tuple(events),
        "exam": exam_result,
    }


def _find_exam_opponent(actor: Any, record: CombatSessionRecord) -> Any | None:
    """Return the settled exam's temporary opponent, if it still exists."""
    from world.rules.guild_exams import _read_exams

    exam_record = next(
        (r for r in _read_exams(actor) if r.exam_id == record.exam_id),
        None,
    )
    if exam_record is None:
        return None
    return ObjectDB.objects.filter(id=exam_record.opponent_id).first()


def _restore_exam_participants(
    actor: Any,
    record: CombatSessionRecord,
    battlefield: Battlefield | None,
) -> None:
    """Restore both exam sides' gauges to full inside the settlement.

    Runs as the last step of the settlement transaction, after the session
    clears and before the temporary opponent is deleted post-commit
    (exam-simulated-battle-redesign D3): the candidate and examiner walk away
    from the simulated battle fully healed regardless of outcome, and the
    restoration commits or rolls back with the exam outcome. The battlefield
    roster is preferred when available; a degraded path (or a roster that
    lacks the opponent) falls back to the durable exam record lookup.
    """
    from world.rules.traits import restore_gauges_to_full

    restore_gauges_to_full(actor)
    opponent = None
    if battlefield is not None:
        opponent = next(
            (
                entity
                for key, entity in battlefield.roster.items()
                if int(entity.pk) in record.enemy_ids
            ),
            None,
        )
    if opponent is None:
        opponent = _find_exam_opponent(actor, record)
    if opponent is not None:
        restore_gauges_to_full(opponent)


def _delete_exam_opponent(actor: Any, record: CombatSessionRecord) -> None:
    """Delete the settled exam's temporary opponent, best effort.

    Runs after the settlement transaction committed, so a failed settlement
    keeps the opponent alive for exactly one retry. An already-missing
    opponent (or a delete error) is logged and never raises.
    """
    from evennia.utils.logger import log_warn

    opponent = _find_exam_opponent(actor, record)
    if opponent is None:
        return
    try:
        opponent.delete()
    except Exception as error:
        log_warn(f"guild_exam: could not delete opponent {opponent}: {error}")


def _settle_with_restore(
    actor: Any,
    record: CombatSessionRecord,
    battlefield: Battlefield | None,
    outcome: str,
    logs=(),
) -> dict[str, Any]:
    """Settle a session outside a round, restoring actor surfaces on failure.

    ``settle_session`` runs its own durable transaction; when it fails (for
    example a clock write error during forfeit or startup restoration), the
    database keeps the session but the in-process ``active_combat``/exam
    attributes were already reassigned by the settlement steps. Restoring
    them keeps the retry path consistent without waiting for a reload
    (the idmapper attribute cache is not transaction-aware).
    """
    from world.rules.action import _attribute_snapshot, _restore_attribute

    extra: dict[str, tuple[bool, Any]] = {
        "active_combat": _attribute_snapshot(actor, "active_combat"),
    }
    trait_snapshots: list[tuple[Any, tuple[bool, Any]]] = []
    if record.mode == "guild_exam":
        extra["guild_rank"] = _attribute_snapshot(actor, "guild_rank")
        extra["guild_exams"] = _attribute_snapshot(actor, "guild_exams")
        # The settlement transaction restores the exam sides' gauges; when it
        # rolls back, restore the in-process trait surfaces too (the idmapper
        # cache is not transaction-aware), for the actor and the opponent.
        from world.rules.surfaces import snapshot_traits

        trait_snapshots.append((actor, snapshot_traits(actor)))
        opponent = _find_exam_opponent(actor, record)
        if opponent is not None:
            trait_snapshots.append((opponent, snapshot_traits(opponent)))
    try:
        return settle_session(actor, record, battlefield, outcome, logs)
    except Exception:
        for key, snapshot in extra.items():
            _restore_attribute(actor, key, snapshot)
        for entity, snapshot in trait_snapshots:
            from world.rules.surfaces import restore_traits

            restore_traits(entity, snapshot)
        raise


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
    return _settle_with_restore(actor, record, battlefield, outcome)


def restore_active_session(actor: Any) -> None:
    """Reconstruct a valid persisted session or terminate it diagnostically.

    The strict parse runs inside the recovery boundary: a record that cannot
    be parsed at all (for example ``{"not": "a valid record"}``) is cleared
    with a diagnostic and never settled, because its untrusted fields must
    not drive a time settlement or participant effects. Missing, deleted,
    moved, duplicated, or malformed participants of a well-formed record
    close the session deterministically: hostile sessions settle as defeat,
    examinations as FAIL, leaving no orphan opponent and no blocked player.
    A record that already carries a durable ``settled_tick`` marker is never
    settled again: its time already committed, so restoration only clears the
    leftover session state (fix-combat-settlement-recovery D2). Unrelated
    restoration or settlement failures propagate with the durable record
    intact for retry.
    """
    from evennia.utils.logger import log_warn

    try:
        record = read_session(actor)
    except CombatSessionError as error:
        # Unparseable payload: clear without settlement. The actor's own
        # skip-safety registration is the only key gating the actor's skips,
        # and untrusted ids must never drive participant cleanup.
        log_warn(
            f"combat_session: clearing unparseable session for {actor.key}: {error}"
        )
        clear_session(actor, None, None)
        return
    if record is None:
        return
    if record.settled_tick is not None:
        log_warn(
            f"combat_session: skipping settlement of already-settled session "
            f"{record.session_id} (settled at tick {record.settled_tick})"
        )
        clear_session(actor, None, record)
        return
    try:
        battlefield = reconstruct_battlefield(actor, record)
    except CombatSessionError as error:
        log_warn(
            f"combat_session: terminating invalid session for {actor.key}: {error}"
        )
        _settle_with_restore(
            actor,
            record,
            None,
            "defeat" if record.mode == "hostile" else "exam_failed",
        )
        return
    outcome = _terminal_outcome(actor, battlefield, record)
    if outcome is not None:
        _settle_with_restore(actor, record, battlefield, outcome)
        return
    register_active_battlefield(battlefield)