"""Map-owned operator lifecycle operations, distinct from raw location edits."""

from django.db import transaction
from evennia.objects.models import ObjectDB

from server.console.errors import ConsoleError
from server.console.validation import resolve_target, text
from world.rules.clock import _flush_deleted_instance
from world.rules.surfaces import (
    flush_orphan_instances,
    restore_attributes,
    snapshot_attributes,
)


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
    from world.maps.regional_population import (
        current_population_tick,
        register_explicit_individual,
        restore_population_surfaces,
        snapshot_population_surfaces,
        wilderness_registration_target,
    )
    from world.rules.monster_individual import construct_species_individual

    from world.maps.monster_activity import STAGED_STATIONARY_ACTIVITY

    destination = resolve_target(room, {"rooms"})
    text(species)
    text(variant)
    if species not in MONSTER_SPECIES_REGISTRY or variant not in MONSTER_VARIANT_REGISTRY:
        raise ConsoleError("registry_key_not_found")
    if MONSTER_VARIANT_REGISTRY[variant].species_key != species:
        raise ConsoleError("invalid_argument")
    # A wilderness destination is an explicit placement: the actual individual
    # is registered by the map population owner at the room's real coordinate
    # (it may sit inside an automatic birth buffer). Any other room keeps the
    # ordinary move.
    target = wilderness_registration_target(destination)
    surfaces = snapshot_population_surfaces(target[0]) if target is not None else {}
    try:
        with transaction.atomic():
            monster = construct_species_individual(species, variant)
            if target is not None:
                wilderness, coordinates = target
                register_explicit_individual(
                    wilderness,
                    monster,
                    coordinates,
                    tick=current_population_tick(),
                    owner_kind="explicit",
                    owner_key=f"gm:{monster.pk}",
                    activity_key=STAGED_STATIONARY_ACTIVITY,
                )
            elif not monster.move_to(destination, quiet=True, move_type="spawn"):
                raise RuntimeError("monster placement refused")
    except Exception:
        if target is not None:
            restore_population_surfaces(surfaces)
        flush_orphan_instances()
        raise
    return {"target": f"#{monster.pk}", "room": room}


def delete_entity(target):
    from typeclasses.characters import PlayerCharacter
    from world.maps import regional_population
    from world.rules import skip_safety
    from world.rules.combat_session.lifecycle import clear_session
    from world.rules.combat_session.records import read_session

    entity = resolve_target(target, {"monsters"})
    pk = entity.pk
    location = entity.location
    # Capture the complete pre-removal presence before deletion destroys the
    # object: a deleted away-home member must still consume its historical
    # home headroom, and the local cell it occupied stays a truthful fact.
    wilderness = regional_population.live_wilderness()
    before_presence = (
        regional_population.presence_of(wilderness, entity)
        if wilderness is not None
        else None
    )
    population_surfaces = (
        regional_population.snapshot_population_surfaces(wilderness)
        if wilderness is not None
        else {}
    )
    removal_tick = regional_population.current_population_tick()
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
            if wilderness is not None and before_presence is not None:
                regional_population.record_population_transition(
                    wilderness,
                    regional_population.PopulationTransition(
                        source_id=f"operator-delete:{pk}:{removal_tick}",
                        individual_id=pk,
                        occurred_tick=removal_tick,
                        before=before_presence,
                        after=regional_population.PopulationPresence(
                            alive=False,
                            position=None,
                            home_zone=before_presence.home_zone,
                            site_key=before_presence.site_key,
                        ),
                    ),
                )
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
        if wilderness is not None:
            regional_population.restore_population_surfaces(population_surfaces)
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
