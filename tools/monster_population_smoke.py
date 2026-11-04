"""Retained developer smoke for the regional population runtime cutover.

Run only against a disposable configured database (see
``server/conf/monster_population_smoke_settings.py``)::

    MUD_SMOKE_DB=/tmp/mud-population-smoke.sqlite3 \
        uv run --locked evennia migrate \
        --settings server.conf.monster_population_smoke_settings --noinput
    MUD_SMOKE_DB=/tmp/mud-population-smoke.sqlite3 \
        uv run --locked evennia shell \
        --settings server.conf.monster_population_smoke_settings --plain \
        -c "from tools.monster_population_smoke import run; run()"

The script uses the real wilderness script, the real regional/site owners, the
synthetic-data kit's catalogs and real ``Monster`` construction. It observes
actual births, one recorded defeat, the delayed recovery wave, the read
projections, a fresh-object reload and an owner-compensated fault/retry. Every
claim in the printed report is an observed value; a failed boundary raises and
exits nonzero.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from evennia.contrib.grid.wilderness.wilderness import (
    WildernessScript,
    create_wilderness,
    enter_wilderness,
)
from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from world.lore.monster_placement import (
    CompositionMember,
    EcologyZone,
    EncounterComposition,
    WeightedComposition,
    variant_species_key,
)
from world.lore.wilderness_regions import regions
from world.maps import population_lifecycle
from world.maps import regional_population as owner
from world.maps import monster_sites
from world.maps.population_geometry import eligible_birth_cells
from world.maps.wilderness_population import population_view
from world.maps.wilderness_provider import (
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
    is_valid_wilderness_cell,
    region_for_coordinates,
)
from world.observability import log_info
from world.rules.clock import AdvanceSource, get_world_clock
from world.rules.travel_interrupts import live_hostile_facts
from world.tests.synthetic_data import SYNTH_MONSTER_VARIANTS, synthetic_registries


def _candidate_cells():
    """Real, walkable cells spread across the frame."""
    candidates = []
    for x in range(200, 2200, 37):
        for y in range(200, 2200, 41):
            if is_valid_wilderness_cell((x, y)):
                region = region_for_coordinates(x, y)
                if region in regions():
                    candidates.append((x, y))
                    if len(candidates) >= 12:
                        break
        if len(candidates) >= 12:
            break
    if not candidates:
        raise RuntimeError("smoke: no valid wilderness cell found")
    return candidates


def _geometry_for(cell):
    """A bounded rectangle around ``cell`` with eligible birth cells."""
    region = region_for_coordinates(*cell)
    rectangle = (cell[0] - 7, cell[0] + 7, cell[1] - 7, cell[1] + 7)
    zone = EcologyZone(
        "smoke_probe_zone",
        region,
        (rectangle,),
        (),
        1,
        2,
        1,
        100,
        100,
        1,
    )
    cells = eligible_birth_cells(
        zone,
        geography=owner._published_geography(),
        entries=owner.WILDERNESS_ENTRY_REGISTRY,
        policies={},
    )
    if len(cells) < 40:
        raise RuntimeError("smoke: rectangle has too few eligible birth cells")
    return region, rectangle, tuple(cells)


def _live_ids(wilderness):
    return sorted(
        int(obj.pk)
        for obj in (wilderness.db.itemcoordinates or {})
        if isinstance(obj, Monster) and obj.traits.hp.current > 0
    )


def _registration():
    from world.rules import clock as clock_module

    registration = clock_module._EVENT_SOURCES[population_lifecycle.STAGE_KIND]
    return (
        registration.settle is population_lifecycle.settle_population_lifecycle
        and registration.next_boundary
        is population_lifecycle.next_population_lifecycle_boundary
    )


def run() -> dict:
    """Execute the real smoke and print one bounded observed report."""
    from django.conf import settings

    from typeclasses.rooms import Room

    # A fresh disposable database has no Evennia first-boot default objects.
    # Create one real room as the default home so real construction works
    # exactly as it does on a configured world.
    if not ObjectDB.objects.filter(pk=2).exists():
        home = create_object(Room, key="smoke home", nohome=True)
        settings.DEFAULT_HOME = f"#{home.pk}"

    variant_key = next(iter(SYNTH_MONSTER_VARIANTS))
    composition = EncounterComposition(
        "smoke_composition",
        "t_whisper_quail_solitary_activity",
        (CompositionMember(variant_key, 1, 1),),
    )
    candidates = _candidate_cells()
    region, rectangle, birth_cells = _geometry_for(candidates[0])
    failure_region, failure_rectangle, _failure_cells = _geometry_for(candidates[-1])

    scopes = synthetic_registries(
        "races",
        "subraces",
        "static_tiers",
        "monster_species",
        "monster_variants",
        "monster_tiers",
        "activity_areas",
        "monster_activities",
        "ecology_zones",
        "encounter_compositions",
        extra={
            "encounter_compositions": {"smoke_composition": composition},
        },
    )
    with scopes:
        species_key = variant_species_key(variant_key)
        zone = EcologyZone(
            "smoke_zone",
            region,
            (rectangle,),
            (WeightedComposition("smoke_composition", 1),),
            1,
            2,
            1,
            100,
            100,
            1,
        )
        failure_zone = EcologyZone(
            "smoke_rollback_zone",
            failure_region,
            (failure_rectangle,),
            (WeightedComposition("smoke_composition", 1),),
            1,
            2,
            1,
            5,
            5,
            1,
        )
        with patch.object(
            owner,
            "ECOLOGY_ZONE_REGISTRY",
            {zone.key: zone, failure_zone.key: failure_zone},
        ), patch.object(monster_sites, "MONSTER_SITE_REGISTRY", {}):
            create_wilderness(
                name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider()
            )
            script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
            tick = owner.current_population_tick()
            owner.initialize_population_seed(script, seed=0, tick=tick)

            # The startup registration is idempotent and installs exactly the
            # merged coordinator, never the retired site-only interval helper.
            population_lifecycle.register_regional_population()
            population_lifecycle.register_regional_population()
            registered_once = _registration()

            created = owner.initialize_zone(script, zone.key, seed=0, tick=tick)
            state_after_init = owner.zone_state(script, zone.key)
            birth_pks = sorted(created)
            view = population_view(script, birth_cells)
            view_birth_ids = sorted(
                int(fact.observation_key.split(":")[1])
                for fact in view
                if fact.kind == "monster"
            )
            if not birth_pks or view_birth_ids != birth_pks:
                raise RuntimeError(
                    f"smoke: births/view mismatch {birth_pks!r} vs {view_birth_ids!r}"
                )

            # Kill one individual through the real committed combat resolver.
            target = Monster.objects.get(pk=birth_pks[0])
            from world.rules.combat_session import (
                BASIC_ATTACK_KEY,
                engage_group,
                read_session,
                submit_player_action,
            )
            from world.rules.tests._combat_session_helpers import (
                _player,
                complete_party_draft,
            )

            fighter = _player("smoke fighter")
            fighter.traits.hp.base = 100000
            fighter.traits.hp.current = 100000
            enter_wilderness(fighter, coordinates=birth_cells[0], name=WILDERNESS_NAME)
            target.location = fighter.location
            fighter.location.contents_cache.add(target)
            target.traits.hp.base = 1
            target.traits.hp.current = 1
            before = owner.presence_of(script, target)
            from world.rules import monster_behaviour

            rulebook = dict(monster_behaviour.MONSTER_BEHAVIOUR_YAML)
            tier_defaults = dict(rulebook["tier_default_archetype"])
            tier_defaults[target.threat_tier] = next(iter(tier_defaults.values()))
            rulebook["tier_default_archetype"] = tier_defaults
            with patch.object(
                monster_behaviour, "MONSTER_BEHAVIOUR_YAML", rulebook
            ):
                engage_group(fighter, [target])
                result = None
                for _round in range(20):
                    if read_session(fighter) is None:
                        break
                    admitted = submit_player_action(
                        fighter, BASIC_ATTACK_KEY, [target]
                    )
                    result = complete_party_draft(fighter, target, admitted)
                    if result.get("outcome") == "victory":
                        break
            if read_session(fighter) is not None:
                raise RuntimeError(
                    f"smoke: combat did not settle the target: {result!r}"
                )
            if target.traits.hp.current > 0:
                raise RuntimeError("smoke: target survived the committed defeat")
            clock = get_world_clock()
            now = clock.tick
            population_lifecycle.settle_population_lifecycle(now, now)
            due = owner.zone_state(script, zone.key).recovery_due_tick
            before_due_ids = _live_ids(script)

            if due is None or due <= now:
                raise RuntimeError(f"smoke: no future due tick after {now}")
            clock.advance(due - now - 1, AdvanceSource.SKIP, [])
            before_exact_due_ids = _live_ids(script)
            if before_exact_due_ids != before_due_ids:
                raise RuntimeError(
                    "smoke: a birth happened before the due tick "
                    f"{due!r}: {before_due_ids!r} -> {before_exact_due_ids!r}"
                )
            clock.advance(1, AdvanceSource.SKIP, [])
            after_due_ids = _live_ids(script)
            state_after_due = owner.zone_state(script, zone.key)
            new_ids = sorted(set(after_due_ids) - set(before_due_ids))
            if not new_ids:
                raise RuntimeError(
                    f"smoke: no delayed wave at due {due!r} "
                    f"(ids {before_due_ids!r} -> {after_due_ids!r})"
                )
            due_view = population_view(script, birth_cells)
            due_view_ids = sorted(
                int(fact.observation_key.split(":")[1])
                for fact in due_view
                if fact.kind == "monster"
            )
            if due_view_ids != after_due_ids:
                raise RuntimeError(
                    f"smoke: view shows stale/dead ids {due_view_ids!r} "
                    f"vs living {after_due_ids!r}"
                )

            # Interrupt surface sees only living actual individuals.
            witness = create_object(PlayerCharacter, key="smoke witness")
            enter_wilderness(witness, coordinates=birth_cells[0], name=WILDERNESS_NAME)
            hostiles = live_hostile_facts(witness.location, birth_cells)
            hostile_ids = sorted(
                int(fact.observation_key.split(":")[1]) for fact in hostiles
            )
            if not set(hostile_ids) <= set(after_due_ids):
                raise RuntimeError(
                    f"smoke: interrupt view leaked {hostile_ids!r}"
                )

            # Fresh-object reload: identity, resources and home ownership hold.
            survivor = Monster.objects.get(pk=after_due_ids[0])
            survivor_pk = int(survivor.pk)
            survivor_hp = survivor.traits.hp.current
            survivor_home = survivor.db.home_ecology_zone
            survivor.flush_from_cache(force=True)
            survivor.attributes.reset_cache()
            script.attributes.reset_cache()
            reloaded = Monster.objects.get(pk=survivor_pk)
            reloaded_view_ids = sorted(
                int(fact.observation_key.split(":")[1])
                for fact in population_view(script, birth_cells)
                if fact.kind == "monster"
            )
            reload_facts = {
                "id": int(reloaded.pk),
                "hp": reloaded.traits.hp.current,
                "home_zone": reloaded.db.home_ecology_zone,
            }
            if (
                reload_facts["hp"] != survivor_hp
                or reload_facts["home_zone"] != survivor_home
                or reloaded_view_ids != after_due_ids
            ):
                raise RuntimeError(f"smoke: reload mismatch {reload_facts!r}")

            # Fault after real construction/registration, then same-plan retry.
            before_fault = Monster.objects.count()

            def fail_after_construction(*args, **kwargs):
                raise RuntimeError("smoke injected post-construction failure")

            try:
                with patch.object(owner, "_wave_context", fail_after_construction):
                    owner.initialize_zone(
                        script, failure_zone.key, seed=0, tick=clock.tick
                    )
            except RuntimeError:
                pass
            else:
                raise RuntimeError("smoke: fault boundary did not raise")
            rolled_back_count = Monster.objects.count()
            rolled_back_state = owner.zone_state(script, failure_zone.key)
            if rolled_back_count != before_fault or rolled_back_state is not None:
                raise RuntimeError(
                    "smoke: fault left state "
                    f"{rolled_back_count} vs {before_fault}, {rolled_back_state!r}"
                )
            retried = owner.initialize_zone(
                script, failure_zone.key, seed=0, tick=clock.tick
            )
            if not retried:
                raise RuntimeError("smoke: retry created nothing")

            log_info(
                "monster_population_smoke",
                context={
                    "zone": zone.key,
                    "births": len(birth_pks),
                    "wave": len(new_ids),
                },
            )

            report = {
                "seed": owner.read_population_seed(script),
                "zone": zone.key,
                "region": region,
                "birth_cells": len(birth_cells),
                "coordinator_registered_once": registered_once,
                "initial_pks": birth_pks,
                "initial_state": {
                    "generation_sequence": state_after_init.generation_sequence,
                    "recovery_due_tick": state_after_init.recovery_due_tick,
                },
                "view_initial_ids": view_birth_ids,
                "defeat": {
                    "pk": int(target.pk),
                    "was_alive": before.alive,
                    "now_alive": owner.presence_of(script, target).alive,
                    "due_tick": due,
                },
                "before_due_living": before_due_ids,
                "before_exact_due_living": before_exact_due_ids,
                "at_due_living": after_due_ids,
                "delayed_wave_pks": new_ids,
                "state_after_due": {
                    "generation_sequence": state_after_due.generation_sequence,
                    "recovery_due_tick": state_after_due.recovery_due_tick,
                },
                "view_due_ids": due_view_ids,
                "interrupt_hostile_ids": hostile_ids,
                "reload": reload_facts,
                "rollback": {
                    "before_count": before_fault,
                    "after_count": rolled_back_count,
                    "state": rolled_back_state,
                    "retry_created": list(retried),
                },
                "legacy_absent": {
                    "ensure_population": not hasattr(
                        __import__(
                            "world.maps.wilderness_population",
                            fromlist=["ensure_population"],
                        ),
                        "ensure_population",
                    ),
                    "ambient_registry": not hasattr(
                        __import__(
                            "world.lore.monster_placement",
                            fromlist=["AMBIENT_PLACEMENT_REGISTRY"],
                        ),
                        "AMBIENT_PLACEMENT_REGISTRY",
                    ),
                },
                "species": species_key,
                "variant": variant_key,
            }
            if not all(report["legacy_absent"].values()):
                raise RuntimeError("smoke: legacy symbol still reachable")
            print("MONSTER_POPULATION_SMOKE " + json.dumps(report, ensure_ascii=False))
            return report
