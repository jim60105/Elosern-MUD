"""Instance-layer accommodation: spawn, TTL reclamation, and the pin/ownership
seams that keep a due room alive or resolve its non-player occupants
(map-instance)."""

from pathlib import Path
from typing import Any

import yaml
from django.conf import settings
from django.db import transaction
from evennia.objects.models import ObjectDB
from evennia.prototypes.spawner import spawn
from evennia.utils.idmapper.models import flush_cache

from typeclasses.characters import PlayerCharacter
from typeclasses.entities import LivingEntity
from typeclasses.exits import Exit
from typeclasses.rooms import InstanceRoom
from world.art.scene_definitions import is_registered_room_art_key
from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY
from world.maps.room_art import instance_scene_identity
from world.observability import log_warn
from world.rules.clock import (
    ScheduledEvent,
    SurfaceSnapshot,
    get_world_clock,
    register_event_source,
)
from world.rules.map_knowledge import KNOWLEDGE_ATTR
from world.rules.surfaces import attribute_snapshot

INSTANCE_PROTOTYPE_WHITELIST: tuple[str, ...] = ("instance_room",)

INSTANCE_YAML = yaml.safe_load(
    (Path(__file__).parent.parent / "rules" / "rulebook" / "instance.yaml").read_text(
        encoding="utf-8"
    )
)

_INSTANCE_ROOM_SURFACES: tuple[str, ...] = (
    "expire_tick",
    "named",
    "interacted",
    "pin_reasons",
    "owned_entities",
)


def _db_safe_attribute_snapshot(obj: Any, key: str) -> tuple[bool, Any]:
    """Snapshot one attribute whose value may embed live database objects.

    ``owned_entities`` unpacks to live ``LivingEntity`` instances, which a
    plain ``deepcopy`` cannot copy (Evennia objects carry a ``DbHolder`` in
    their instance dict); the ``dbserialize`` round-trip is the established
    deepcopy for values that may embed database objects.
    """
    from evennia.utils.dbserialize import from_pickle, to_pickle

    exists = obj.attributes.has(key)
    value = (
        from_pickle(to_pickle(obj.attributes.get(key))) if exists else None
    )
    return exists, value


def _validate_prototype_parent(prototype: dict) -> None:
    """Reject any ``prototype_parent`` outside the change-21 seam whitelist, and
    reject an explicit ``typeclass`` override so the whitelist gates the actual
    spawned type, not merely the claimed parentage."""
    parent = prototype.get("prototype_parent")
    if parent not in INSTANCE_PROTOTYPE_WHITELIST:
        raise ValueError(f"prototype_parent {parent!r} is not in INSTANCE_PROTOTYPE_WHITELIST")
    typeclass = prototype.get("typeclass")
    if typeclass is not None and typeclass != "typeclasses.rooms.InstanceRoom":
        raise ValueError(
            f"prototype typeclass {typeclass!r} overrides instance_room; "
            "a whitelisted instance prototype must not override the typeclass"
        )


def spawn_instance_room(
    origin_room,
    prototype,
    *,
    exit_key,
    return_key,
    ttl_seconds=None,
    named=False,
    caller=None,
    scene_archetype=None,
    room_art_key=None,
    scene_identity=None,
) -> InstanceRoom:
    """Create one ``InstanceRoom`` reached from ``origin_room`` via a plain Exit pair.

    Validates the prototype before ``spawner.spawn()`` runs, so a bad
    prototype or a nested-instance origin can never create a partial room plus
    a dangling exit. The whole spawn-plus-attach sequence is one transaction:
    a failure in any step rolls back the room and both exits together, so a
    caller never observes or leaves a half-wired instance. ``expire_tick`` is
    set from the rulebook default TTL unless ``ttl_seconds`` overrides it
    (map-instance design.md D-2/D-7/D-9).

    ``scene_archetype`` is the explicitly authored registered scene archetype
    the instance renders (``None`` for a dynamic undeclared instance, which
    then has no room-art key and uses no scene art). ``room_art_key`` is the
    explicitly authored registered room-art key an operator override may
    address. Both are validated here, BEFORE any object is spawned, so a bad
    declaration can never leave a partial room behind. ``scene_identity`` is
    the stable non-pooled logical identity; it defaults to the room's own
    stable identity and is never inferred from the art key
    (unified-room-art-metadata design).
    """
    if ttl_seconds is not None and (
        not isinstance(ttl_seconds, int) or isinstance(ttl_seconds, bool) or ttl_seconds < 0
    ):
        raise ValueError(
            f"ttl_seconds must be a non-negative int, got {ttl_seconds!r}"
        )
    if scene_archetype is not None and scene_archetype not in SCENE_ARCHETYPE_REGISTRY:
        raise ValueError(
            f"scene_archetype {scene_archetype!r} is not a registered scene archetype"
        )
    if room_art_key is not None and not is_registered_room_art_key(room_art_key):
        raise ValueError(
            f"room_art_key {room_art_key!r} is not a registered room-art key"
        )
    if isinstance(origin_room, InstanceRoom):
        raise ValueError(
            "origin_room must not itself be an InstanceRoom -- nested instances are not "
            "supported (see design.md Fix 2 / Risks)"
        )
    _validate_prototype_parent(prototype)
    with transaction.atomic():
        spawned = spawn(prototype, caller=caller)
        if not spawned:
            # spawner.spawn()'s internal `if not prot: continue` branch is
            # unreachable for a prototype that has already passed
            # _validate_prototype_parent(), but a validated dict is not a
            # formal guarantee spawn() makes -- fail loudly instead of an
            # opaque IndexError on [0] (map-instance design.md D-2 Fix 4).
            raise RuntimeError(
                "spawner.spawn() returned no object for a validated instance prototype"
            )
        room = spawned[0]
        if not isinstance(room, InstanceRoom):
            # Defense in depth: the whitelist gates spawner.spawn()'s input,
            # but the object it actually creates is the authority on its own
            # typeclass. A prototype that somehow produced a non-InstanceRoom
            # object is a reclamation-gap bug -- roll back the whole attach.
            raise ValueError(
                f"spawned object {room!r} is not an InstanceRoom; "
                "rejecting it rather than leaving an unreclaimable room"
            )
        room.db.expire_tick = get_world_clock().tick + (
            ttl_seconds if ttl_seconds is not None else INSTANCE_YAML["default_ttl_seconds"]
        )
        room.db.named = named
        room.db.origin_room = origin_room
        room.db.scene_archetype = scene_archetype
        room.db.room_art_key = room_art_key
        room.db.scene_identity = (
            scene_identity
            if scene_identity is not None
            else instance_scene_identity(room.pk)
        )
        Exit.create(key=exit_key, location=origin_room, destination=room)
        Exit.create(key=return_key, location=room, destination=origin_room)
    return room


def pin_instance_room(room, reason: str) -> None:
    """Hold ``reason`` (de-duplicated) on the room so reclamation defers it."""
    reasons = list(room.db.pin_reasons or [])
    if reason not in reasons:
        reasons.append(reason)
        room.db.pin_reasons = reasons


def unpin_instance_room(room, reason: str) -> None:
    """Release ``reason``; a no-op when the reason was never held."""
    reasons = list(room.db.pin_reasons or [])
    if reason in reasons:
        reasons.remove(reason)
        room.db.pin_reasons = reasons


def register_owned_entity(room, entity) -> None:
    """Mark ``entity`` as owned by ``room`` so reclamation despawns it (D-6/D-8)."""
    owned = list(room.db.owned_entities or [])
    if entity not in owned:
        owned.append(entity)
        room.db.owned_entities = owned


def _relocate_to_default_home(entity) -> None:
    """Relocate ``entity`` to ``settings.DEFAULT_HOME`` without destroying it.

    Mirrors the lookup ``DefaultObject.clear_contents()`` itself uses so an
    unowned occupant survives reclamation, merely moved (map-instance design.md
    D-6).
    """
    home = ObjectDB.objects.get(id=int(settings.DEFAULT_HOME.lstrip("#")))
    entity.move_to(home, quiet=True)


def _clear_non_player_entities(room) -> None:
    """Empty ``room`` of every ``LivingEntity`` before its delete.

    Called only on the reclaim branch, never the promote branch. Registered
    (owned) entities are despawned; everything else is relocated to
    ``settings.DEFAULT_HOME``, matching the non-destructive policy Evennia's own
    ``clear_contents()`` applies to items (map-instance design.md D-6).

    A retained named story role takes precedence over both (quest-scene-
    encounters design §7): its package declares a validated permanent retention
    destination, so it is transferred there through the shared movement hook and
    its ephemeral ownership is dropped instead of being deleted. Every retention
    destination is validated *before* any movement or deletion, so an
    unavailable destination can never leave a half-cleared room; the transfer
    raises ``RetentionTransferError`` and the caller rolls the reclaim back.
    """
    from world.quests.retention import (
        RetentionTransferError,
        retained_role_for,
        transfer_retained_role,
        validate_retention_destination,
    )

    owned = {obj for obj in (room.db.owned_entities or []) if obj and obj.pk}
    living = [obj for obj in list(room.contents) if isinstance(obj, LivingEntity)]
    retained = {}
    for entity in living:
        record = retained_role_for(entity.pk)
        if record is not None:
            validate_retention_destination(record)
            retained[entity.pk] = record
    destinations: list[Any] = []
    for entity in living:
        record = retained.get(entity.pk)
        if record is not None:
            destination = validate_retention_destination(record)
            try:
                transfer_retained_role(
                    entity, record, room=destination, source_room=room
                )
            except RetentionTransferError as error:  # observability: ignore R2: the failure is re-raised (wrapped with the destinations already written) and reported by the caller's instance_reclaim_retention_failed event
                # Attach the destinations already written, so the caller can
                # reconcile their cached contents after the rollback.
                raise RetentionTransferError(
                    str(error), destinations=tuple(destinations)
                ) from error
            destinations.append(destination)
            # The move updated this room's cached contents; re-reading from the
            # database after a rollback then shows the true (unmoved) contents.
            destination.contents_cache.clear()
            continue
        if entity in owned:
            entity.delete()
        else:
            _relocate_to_default_home(entity)
    room.db.owned_entities = []


def reclaim_due_instances(start_tick, end_tick) -> list[ScheduledEvent]:
    """Settle every due ``InstanceRoom`` into defer / promote / reclaim.

    Registered as the ``instance_reclamation`` boundary-stage source. Occupancy
    gates on ``PlayerCharacter`` specifically -- an NPC or Monster present and
    unpinned does not block reclamation (map-instance design.md D-6's corrected
    rule, not the earlier any-``LivingEntity`` draft).

    The reclaim branch consults the typeclass safety net (``at_object_delete``,
    D-1) *before* clearing any entity, so a room the safety net would refuse
    never loses its own NPCs to a half-completed clear -- deferral is
    side-effect-free by construction, rather than requiring an unreliable
    database rollback (rubber-duck review, map-instance design.md).
    """
    from world.quests.retention import RetentionTransferError

    events = []
    for room in InstanceRoom.objects.all():
        expire_tick = room.db.expire_tick
        if expire_tick is None or expire_tick > end_tick:
            continue
        blocking_player = any(isinstance(o, PlayerCharacter) for o in room.contents)
        if room.db.pin_reasons or blocking_player:
            events.append(ScheduledEvent("instance_reclaim_deferred", end_tick, {"room": room.key}))
            continue
        if room.db.named and room.db.interacted:
            room.db.expire_tick = None
            events.append(ScheduledEvent("instance_promoted", end_tick, {"room": room.key}))
            continue
        if not room.at_object_delete():
            # The typeclass-level safety net refuses this room right now (an
            # active pin or a PlayerCharacter). Defer with no entity clearing.
            events.append(ScheduledEvent("instance_reclaim_deferred", end_tick, {"room": room.key}))
            continue
        prune_deferred = False
        retained_deferred = False
        # Compensation for a retention failure must run AFTER the atomic block:
        # a rolled-back transaction refuses further queries, and re-reading the
        # destination's cached contents both clears the phantom occupant and is
        # a query.
        retention_failure: RetentionTransferError | None = None
        # ``_clear_non_player_entities`` mutates the room's owned-entity registry
        # as it transfers; the snapshot lets a rolled-back pass reinstate the
        # pre-clear value in memory (the database value is already reverted).
        had_owned, owned_snapshot = _db_safe_attribute_snapshot(room, "owned_entities")
        with transaction.atomic():
            # Prune the reclaimed room's room:<dbref> from every affected
            # player BEFORE any entity or room mutation (map-knowledge-minimap
            # design D4). On a genuine knowledge-persistence failure the whole
            # transaction is rolled back and the room stays eligible for a
            # later pass; the deferred event is appended only after leaving the
            # atomic block, so emitted events always agree with the committed
            # database state.
            from world.rules.map_knowledge import (
                KnowledgePruneError,
                prune_reclaimed_room,
            )
            try:
                prune_reclaimed_room(room.id)
            except KnowledgePruneError:  # observability: ignore R2: the deferral is reported by the instance_reclaim_deferred event this branch appends after leaving the atomic block
                transaction.set_rollback(True)
                prune_deferred = True
            else:
                try:
                    _clear_non_player_entities(room)
                except RetentionTransferError as error:  # observability: ignore R2: the failure is reported by the instance_reclaim_retention_failed warning and the instance_reclaim_deferred event, both emitted after the atomic block
                    # A retained named role could not reach its validated
                    # destination: the whole reclaim rolls back and the room
                    # survives with its actors, contents and ownership intact.
                    transaction.set_rollback(True)
                    retained_deferred = True
                    retention_failure = error
                else:
                    if room.delete():
                        events.append(
                            ScheduledEvent("instance_reclaimed", end_tick, {"room": room.key})
                        )
                    else:
                        # Unreachable in the deterministic settlement pass: the
                        # pre-flight check above and this call see the same pins and
                        # contents, and nothing between them can change either. Kept as
                        # a defensive no-raise branch in case a future override changes
                        # that; the entity clears it would leave behind are the
                        # accept-once-and-audit cost of that hypothetical, not a normal
                        # path.
                        events.append(
                            ScheduledEvent(
                                "instance_reclaim_deferred", end_tick, {"room": room.key}
                            )
                        )
        if retention_failure is not None:
            if had_owned:
                room.db.owned_entities = owned_snapshot
            # A disposable occupant earlier in the pass may already have been
            # deleted; its row is restored by the rollback while the idmapper
            # still holds the deleted instance, so the cache is flushed. Like
            # the activation boundary's rollback, this runs only on the rare
            # failure path.
            flush_cache()
            for destination in retention_failure.destinations:
                destination.contents_cache.clear()
            log_warn(
                "instance_reclaim_retention_failed",
                context={"room": room.key},
                exc=retention_failure,
            )
        if prune_deferred or retained_deferred:
            events.append(
                ScheduledEvent("instance_reclaim_deferred", end_tick, {"room": room.key})
            )
    return events


def snapshot_instance_reclamation_surfaces(
    start_tick: int, end_tick: int
) -> dict[int, SurfaceSnapshot]:
    """Snapshot the durable surfaces ``reclaim_due_instances`` may write.

    The advance-surface contract for the ``instance_reclamation`` source:
    every ``InstanceRoom``'s reclaimable fields, every player's
    ``map_knowledge`` record (which ``prune_reclaimed_room`` may rewrite),
    and the ``location`` of every non-owned ``LivingEntity`` occupant (the
    ``_clear_non_player_entities`` relocation set, stored as a plain pk so a
    reclaimed room can be re-fetched fresh after rollback). Pure read: no
    attribute, location, or tag changes.
    """
    registry: dict[int, SurfaceSnapshot] = {}
    from world.quests.retention import retained_role_for

    for room in InstanceRoom.objects.all():
        attributes = {
            (key, None): attribute_snapshot(room, key)
            for key in _INSTANCE_ROOM_SURFACES
            if key != "owned_entities"
        }
        attributes[("owned_entities", None)] = _db_safe_attribute_snapshot(
            room, "owned_entities"
        )
        registry[id(room)] = SurfaceSnapshot(attributes=attributes)
    for character in _characters_with_map_knowledge():
        snapshot = registry.get(id(character))
        if snapshot is None:
            registry[id(character)] = SurfaceSnapshot(
                attributes={("map_knowledge", None): attribute_snapshot(character, "map_knowledge")}
            )
        else:
            snapshot.attributes[("map_knowledge", None)] = attribute_snapshot(
                character, "map_knowledge"
            )
    for room in InstanceRoom.objects.all():
        owned = {obj for obj in (room.db.owned_entities or []) if obj and obj.pk}
        for entity in list(room.contents):
            if not isinstance(entity, LivingEntity):
                continue
            if entity in owned and retained_role_for(entity.pk) is None:
                # An owned disposable occupant is deleted, never moved, so its
                # location needs no snapshot; a retained role is *moved*, so it
                # does -- including when it is still registered as owned.
                continue
            registry[id(entity)] = SurfaceSnapshot(
                attributes={},
                location=(True, int(room.pk)),
            )
    return registry


def _characters_with_map_knowledge() -> list[Any]:
    """Every ``PlayerCharacter`` that already carries ``map_knowledge``."""
    return list(
        PlayerCharacter.objects.all_family().filter(
            db_attributes__db_key=KNOWLEDGE_ATTR
        )
    )


def register_instance_reclamation() -> None:
    """Register this module's reclamation as the live boundary-stage source."""
    register_event_source(
        "instance_reclamation",
        reclaim_due_instances,
        snapshot_instance_reclamation_surfaces,
    )