"""Map-owned operator lifecycle operations, distinct from raw location edits."""

from django.db import transaction
from evennia.objects.models import ObjectDB

from server.console.errors import ConsoleError
from server.console.validation import resolve_target, text
from world.rules.clock import _flush_deleted_instance, _flush_rolled_back_instances
from world.rules.surfaces import snapshot_attributes, restore_attributes


def teleport(target, room):
    entity = resolve_target(target, {"characters", "monsters"})
    destination = resolve_target(room, {"rooms"})
    from world.rules.movement_settlement import settle_relocation

    # The verb only resolves and validates its arguments: the arrival
    # knowledge, party, lore, home and dialogue consequences of the move are
    # written by the deterministic settlement (map-knowledge D4 keeps the
    # map-knowledge write helpers out of this adapter).
    settle_relocation(entity, destination)
    return {"target": target, "room": room}


def spawn_monster(species, variant, room):
    from world.lore.monster_species import MONSTER_SPECIES_REGISTRY, MONSTER_VARIANT_REGISTRY
    from world.rules.monster_individual import construct_species_individual

    destination = resolve_target(room, {"rooms"})
    text(species)
    text(variant)
    if species not in MONSTER_SPECIES_REGISTRY or variant not in MONSTER_VARIANT_REGISTRY:
        raise ConsoleError("registry_key_not_found")
    if MONSTER_VARIANT_REGISTRY[variant].species_key != species:
        raise ConsoleError("invalid_argument")
    try:
        with transaction.atomic():
            monster = construct_species_individual(species, variant)
            if not monster.move_to(destination, quiet=True, move_type="spawn"):
                raise RuntimeError("monster placement refused")
    except Exception:
        _flush_rolled_back_instances()
        destination.contents_cache.init()
        raise
    return {"target": f"#{monster.pk}", "room": room}


def delete_entity(target):
    from typeclasses.characters import PlayerCharacter
    from world.rules import skip_safety
    from world.rules.combat_session.lifecycle import clear_session
    from world.rules.combat_session.records import read_session

    entity = resolve_target(target, {"monsters"})
    pk = entity.pk
    location = entity.location
    registrations = dict(skip_safety._BATTLEFIELDS)
    battlefields = {id(field): (field, {key: obj.pk for key, obj in field.roster.items()}) for field in registrations.values()}
    sessions = []
    participants = {entity}
    for actor in PlayerCharacter.objects.all_family():
        record = read_session(actor)
        if record is not None and pk in (*record.player_ids, *record.enemy_ids):
            field = registrations.get(str(actor.pk))
            sessions.append((actor, record, field, actor.ndb.action_context))
            participants.add(actor)
            participants.update(ObjectDB.objects.filter(pk__in=(*record.player_ids, *record.enemy_ids)))
    surfaces = [(obj, snapshot_attributes(obj, ("active_combat", "buffs"))) for obj in participants]
    try:
        with transaction.atomic():
            for actor, record, field, _ in sessions:
                clear_session(actor, field, record)
            skip_safety.unregister_participants((pk,))
            skip_safety.unregister_active_battlefield(entity)
            if not entity.delete():
                raise RuntimeError("entity deletion refused")
    except Exception:
        _flush_deleted_instance(entity)
        # Restore the registration map before touching rosters: neither a stale
        # roster entry nor any other roster problem may leave a live entity
        # deregistered or mask the failure that opened this compensation.
        skip_safety._BATTLEFIELDS.clear()
        skip_safety._BATTLEFIELDS.update(registrations)
        _rebind_battlefield_rosters(battlefields)
        for obj, before in surfaces:
            live = ObjectDB.objects.get(pk=pk) if obj is entity else obj
            restore_attributes(live, before)
        for actor, _, _, context in sessions:
            actor.ndb.action_context = context
        if location is not None:
            location.contents_cache.init()
        raise
    return {"target": target, "deleted": True, "room": f"#{location.pk}" if location is not None else None}


def _rebind_battlefield_rosters(battlefields) -> None:
    """Rebind every surviving roster to real restored objects.

    The original battlefield object outlives the rollback, so its roster must
    hold re-fetched objects rather than revoked Python instances. An entry whose
    dbref is already gone carries no object to restore (``skip_safety`` itself
    tolerates such a stale participant), so it is dropped exactly as the landed
    advance compensation skips a vanished target, instead of raising inside the
    compensation and abandoning the rest of it.
    """
    for field, identities in battlefields.values():
        field.roster.clear()
        for key, identity in identities.items():
            if type(identity) is not int:
                continue
            member = ObjectDB.objects.filter(pk=identity).first()
            if member is not None:
                field.roster[key] = member
