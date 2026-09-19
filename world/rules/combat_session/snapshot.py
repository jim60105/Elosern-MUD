"""Round-and-settlement transaction snapshots (fix-combat-settlement-recovery D1).

Snapshots every entity surface the outer round transaction may touch and
restores them best-effort after a rolled-back round, so readers never observe
values the database rolled back (the idmapper cache is not transaction-aware).
"""

from typing import Any

from evennia.objects.models import ObjectDB

from world.rules.action import (
    SNAPSHOTTED_SURFACES,
    _restore_touched_best_effort,
    _snapshot_touched,
)
from world.rules.combat import Battlefield
from world.rules.combat_session.records import CombatSessionRecord

# Surfaces the outer round-and-settlement transaction snapshots on every
# participant. ``instance_pin`` is excluded because it lives on rooms, not
# combatants; the session room is snapshotted with it separately.
_ROUND_ENTITY_SURFACES = frozenset(SNAPSHOTTED_SURFACES - {"instance_pin"})
_ROOM_SURFACES = frozenset({"instance_pin"})


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
    """Snapshot the party/relations surfaces the post-round scans write.

    ``relations_before`` covers every ``NPC`` on the battlefield roster, not
    only declared party companions: the coercion scan can write any present
    NPC's relations record (a forced sexual act is not restricted to
    companions), so the rollback restore must be able to reach them all. The
    roster loop always runs, even when the actor has zero declared companions
    (sexual-resist-turn-cost B6b Decision 3). ``members_before`` stays scoped
    to companions -- party membership is only meaningful for them.
    """
    from typeclasses.npcs import NPC
    from world.rules.party import party_ids

    party_before = list(actor.db.party or ())
    members_before: dict[int, Any] = {}
    relations_before: dict[int, Any] = {}
    companion_pks = set(party_ids(actor))
    for entity in battlefield.roster.values():
        pk = getattr(entity, "pk", None)
        if not isinstance(pk, int):
            continue
        if isinstance(entity, NPC):
            relations_before[pk] = entity.db.relations_data
        if pk in companion_pks:
            members_before[pk] = entity.db.party_member
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
    if party_before or members_before or relations_before:
        from world.rules.affinity import restore_relations_surfaces
        from world.rules.party import restore_membership_surfaces

        restore_membership_surfaces(actor, party_before, members_before)
        restore_relations_surfaces(relations_before)
