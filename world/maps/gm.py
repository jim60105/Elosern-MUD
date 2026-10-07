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
    from world.rules.movement_settlement import _snapshot_movement_state, _compensate
    from world.rules.map_knowledge import record_arrival
    from world.rules.party import follow_companions
    from world.quests.room_observation import observe_arrival_lore
    from world.rules.city_gates import reanchor_home_on_gate_arrival
    from world.rules.dialogue import clear_dialogue_session
    from typeclasses.characters import PlayerCharacter

    source = entity.location
    before = _snapshot_movement_state(entity, source, destination=destination, wilderness_coordinates=None, wilderness_source_coordinates=None)
    attrs = snapshot_attributes(entity, ("dialogue_session",))
    try:
        with transaction.atomic():
            if not entity.move_to(destination, quiet=True, move_type="teleport"):
                raise ConsoleError("invalid_argument", "movement_refused")
            record_arrival(entity)
            follow_companions(entity, source, destination=destination)
            observe_arrival_lore(entity, destination)
            reanchor_home_on_gate_arrival(entity, destination)
            if isinstance(entity, PlayerCharacter) and source is not destination:
                clear_dialogue_session(entity)
    except Exception:
        _compensate(before)
        restore_attributes(entity, attrs)
        raise
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
        # The original battlefield object survives; rebind its roster to real
        # restored objects instead of reviving a deleted Python instance.
        for field, ids in battlefields.values():
            field.roster.clear()
            field.roster.update({key: ObjectDB.objects.get(pk=identity) for key, identity in ids.items()})
        skip_safety._BATTLEFIELDS.clear()
        skip_safety._BATTLEFIELDS.update(registrations)
        for obj, before in surfaces:
            live = ObjectDB.objects.get(pk=pk) if obj is entity else obj
            restore_attributes(live, before)
        for actor, _, _, context in sessions:
            actor.ndb.action_context = context
        if location is not None:
            location.contents_cache.init()
        raise
    return {"target": target, "deleted": True, "room": f"#{location.pk}" if location is not None else None}
