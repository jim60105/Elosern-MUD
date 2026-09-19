"""Battlefield reconstruction and the session's combat policy.

Resolves one session's persisted dbrefs into a live ``Battlefield`` for one
action, and derives the ``(simulated, nonlethal_keys)`` policy every round
entry point shares (fix-dot-kill-credit D4, party-combat D-3).
"""

from typing import Any

from evennia.objects.models import ObjectDB

from world.rules.action import _stored_trait_value
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.combat_session.errors import CombatSessionError, SessionReason
from world.rules.combat_session.records import CombatSessionRecord


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
