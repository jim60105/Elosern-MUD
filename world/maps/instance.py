"""Instance-layer accommodation: spawn, TTL reclamation, and the pin/ownership
seams that keep a due room alive or resolve its non-player occupants
(map-instance)."""

from pathlib import Path

import yaml
from django.conf import settings
from django.db import transaction
from evennia.objects.models import ObjectDB
from evennia.prototypes.spawner import spawn

from typeclasses.characters import PlayerCharacter
from typeclasses.entities import LivingEntity
from typeclasses.exits import Exit
from typeclasses.rooms import InstanceRoom
from world.rules.clock import ScheduledEvent, get_world_clock, register_event_source

INSTANCE_PROTOTYPE_WHITELIST: tuple[str, ...] = ("instance_room",)

INSTANCE_YAML = yaml.safe_load(
    (Path(__file__).parent.parent / "rules" / "rulebook" / "instance.yaml").read_text(
        encoding="utf-8"
    )
)


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
) -> InstanceRoom:
    """Create one ``InstanceRoom`` reached from ``origin_room`` via a plain Exit pair.

    Validates the prototype before ``spawner.spawn()`` runs, so a bad
    prototype or a nested-instance origin can never create a partial room plus
    a dangling exit. The whole spawn-plus-attach sequence is one transaction:
    a failure in any step rolls back the room and both exits together, so a
    caller never observes or leaves a half-wired instance. ``expire_tick`` is
    set from the rulebook default TTL unless ``ttl_seconds`` overrides it
    (map-instance design.md D-2/D-7/D-9).
    """
    if ttl_seconds is not None and (
        not isinstance(ttl_seconds, int) or isinstance(ttl_seconds, bool) or ttl_seconds < 0
    ):
        raise ValueError(
            f"ttl_seconds must be a non-negative int, got {ttl_seconds!r}"
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
    """
    owned = {obj for obj in (room.db.owned_entities or []) if obj and obj.pk}
    for entity in list(room.contents):
        if not isinstance(entity, LivingEntity):
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
            except KnowledgePruneError:
                transaction.set_rollback(True)
                prune_deferred = True
            else:
                _clear_non_player_entities(room)
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
        if prune_deferred:
            events.append(
                ScheduledEvent("instance_reclaim_deferred", end_tick, {"room": room.key})
            )
    return events


def register_instance_reclamation() -> None:
    """Register this module's reclamation as the live boundary-stage source."""
    register_event_source("instance_reclamation", reclaim_due_instances)