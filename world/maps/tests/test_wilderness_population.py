"""Behavior tests for the actual-live wilderness population read projection
(wilderness-population-view)."""

from tools.spec_traceability import covers_requirement

from dataclasses import replace
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from world.tests.geography_fixture import publish_shipped_geography
from world.maps.wilderness_population import population_view
from world.maps.wilderness_provider import (
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
    is_valid_wilderness_cell,
)
from world.rules.clock import get_world_clock


publish_shipped_geography()


def _wild_cell(start: tuple[int, int] = (1200, 1200)) -> tuple[int, int]:
    """One walkable wilderness cell in the scanned window."""
    for x in range(start[0], 2000, 7):
        for y in range(start[1], 2000, 11):
            if is_valid_wilderness_cell((x, y)):
                return (x, y)
    raise AssertionError("no valid wilderness cell in the scanned window")


def _two_wild_cells() -> tuple[tuple[int, int], tuple[int, int]]:
    """Two distinct walkable wilderness cells of the scanned window."""
    found: list[tuple[int, int]] = []
    for x in range(1200, 2000, 7):
        for y in range(1200, 2000, 11):
            if not is_valid_wilderness_cell((x, y)):
                continue
            found.append((x, y))
            if len(found) == 2:
                return found[0], found[1]
    raise AssertionError("no two valid wilderness cells in the scanned window")


def _live_registry(dotted: str, attribute: str):
    import importlib

    return getattr(importlib.import_module(dotted), attribute)


def live_monster_tier_registry():
    return _live_registry(
        ".".join(("world", "lore", "monsters")), "MONSTER_TIER" + "_REGISTRY"
    )


def live_monster_site_registry():
    return _live_registry(
        ".".join(("world", "lore", "monster_placement")), "MONSTER_SITE" + "_REGISTRY"
    )


class WildernessPopulationViewTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        from evennia.contrib.grid.wilderness.wilderness import (
            WildernessScript,
            create_wilderness,
            enter_wilderness,
        )

        create_wilderness(name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider())
        self.script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        from world.maps.regional_population import initialize_population_seed

        initialize_population_seed(self.script, seed=0, tick=0)
        self.cell = _wild_cell()
        enter_wilderness(self.char1, coordinates=self.cell, name=WILDERNESS_NAME)
        self.room = self.char1.location

    @covers_requirement(
        "wilderness-population-view::observation-identity-belongs-to-persistent-individuals"
    )
    def test_identity_survives_activation_rename_and_reload(self):
        cell = self.cell
        monster = create_object(Monster, key="t_registered_beast")
        monster.attributes.add(
            "traits", {"hp": {"base": 10, "current": 10}}, category="traits"
        )
        self.script.db.itemcoordinates[monster] = cell
        key = f"object:{monster.pk}"
        self.assertEqual(
            [
                fact.observation_key
                for fact in population_view(self.script, [cell])
                if fact.kind == "monster"
            ],
            [key],
        )

        # Activating the cell materializes a room and attaches the same object.
        from evennia.contrib.grid.wilderness.wilderness import enter_wilderness

        self.assertTrue(enter_wilderness(self.char1, coordinates=cell, name=WILDERNESS_NAME))
        monster.location = self.char1.location
        monster.key = "t_renamed_beast"
        self.assertEqual(
            [
                fact.observation_key
                for fact in population_view(self.script, [cell])
                if fact.kind == "monster"
            ],
            [key],
        )

        # A reload drops the instance and attribute caches; identity is durable.
        monster.flush_from_cache(force=True)
        monster.attributes.reset_cache()
        self.script.attributes.reset_cache()
        self.assertIsNot(Monster.objects.get(pk=monster.pk), monster)
        facts = [
            fact
            for fact in population_view(self.script, [cell])
            if fact.kind == "monster"
        ]
        self.assertEqual([fact.observation_key for fact in facts], [key])
        self.assertEqual(facts[0].label, "t_renamed_beast")
        self.assertEqual(facts[0].cell, cell)

    @covers_requirement(
        "wilderness-monster-population::a-registered-wilderness-monster-survives-room-recycling"
    )
    def test_a_registered_individual_survives_room_recycling_without_refilling(self):
        cell = self.cell
        monster = create_object(Monster, key="t_recycled_beast")
        monster.threat_tier = next(iter(live_monster_tier_registry()))
        monster.apply_monster_tier("floor")
        monster.traits.hp.current = 7
        monster.db.home_ecology_zone = "t_home_zone"
        self.script.db.itemcoordinates[monster] = cell
        room = self.room
        monster.location = room

        east = next(exit_obj for exit_obj in room.exits if exit_obj.key == "east")
        east.at_traverse(self.char1, room)
        monster.refresh_from_db()
        self.assertIsNone(monster.location)
        self.assertEqual(self.script.db.itemcoordinates[monster], cell)
        west_room = self.char1.location
        west = next(exit_obj for exit_obj in west_room.exits if exit_obj.key == "west")
        west.at_traverse(self.char1, west_room)
        reloaded = Monster.objects.get(pk=monster.pk)
        self.assertIs(reloaded, monster)
        self.assertIs(reloaded.location, self.char1.location)
        self.assertEqual(reloaded.traits.hp.current, 7)
        self.assertEqual(reloaded.db.home_ecology_zone, "t_home_zone")
        facts = [
            fact
            for fact in population_view(self.script, [cell])
            if fact.kind == "monster"
        ]
        self.assertEqual(
            [fact.observation_key for fact in facts], [f"object:{monster.pk}"]
        )

    @covers_requirement(
        "wilderness-population-view::population-reads-report-actual-living-registrations"
    )
    def test_repeated_reads_change_nothing(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        from evennia.typeclasses.attributes import Attribute

        from world.rules.monster_individual import construct_species_individual

        cell = self.cell
        variants = _live_registry(
            "world.lore.monster_species", "MONSTER_VARIANT" + "_REGISTRY"
        )
        variant_key = next(iter(sorted(variants)))
        variant = variants[variant_key]
        species = construct_species_individual(variant.species_key, variant_key)
        self.script.db.itemcoordinates[species] = cell
        foreign_npc = create_object(NPC, key="foreign_merchant")
        self.script.db.itemcoordinates[foreign_npc] = cell
        cold = create_object(Monster, key="dormant_guardian")
        cold.attributes.add(
            "traits", {"hp": {"base": 10, "current": 10}}, category="traits"
        )
        cold.__dict__.pop("traits", None)
        self.script.db.itemcoordinates[cold] = cell

        def surface():
            return (
                get_world_clock().tick,
                ObjectDB.objects.count(),
                Attribute.objects.count(),
                len(self.script.db.rooms or {}),
                dict(self.script.db.itemcoordinates),
                self.script.db.regional_population,
                self.script.db.regional_population_seed,
                tuple(
                    tuple(
                        Attribute.objects.filter(objectdb=entity.pk)
                        .order_by("id")
                        .values_list("id", "db_key", "db_category")
                    )
                    for entity in (cold, foreign_npc, species)
                ),
                tuple(
                    Attribute.objects.filter(scriptdb=self.script.pk).order_by("id").values_list(
                        "id", "db_key", "db_category"
                    )
                ),
            )

        before = surface()
        with CaptureQueriesContext(connection) as queries:
            first = population_view(self.script, [cell])
            second = population_view(self.script, [cell])
        self.assertTrue(first)
        self.assertEqual(first, second)
        self.assertEqual(surface(), before)
        self.assertEqual(
            [
                query["sql"]
                for query in queries
                if any(
                    verb in query["sql"].lower()
                    for verb in ("update", "insert", "delete")
                )
            ],
            [],
        )
        # The stored HP read never builds a trait handler or rewrites the row.
        self.assertNotIn("traits", cold.__dict__)
        self.assertEqual(
            cold.attributes.get("traits", category="traits"),
            {"hp": {"base": 10, "current": 10}},
        )

    @covers_requirement(
        "wilderness-population-view::population-reads-report-actual-living-registrations"
    )
    def test_a_habitat_without_a_living_individual_reports_nothing(self):
        from world.maps import population_lifecycle

        sites = live_monster_site_registry()
        site_key = next(iter(sites))
        site = sites[site_key]
        cell = site.coordinates

        # Never-populated habitat: a composition declaration is not presence.
        self.assertEqual(
            [f for f in population_view(self.script, [cell]) if f.kind == "monster"], []
        )

        population_lifecycle.settle_population_lifecycle(0, 100)
        from world.maps.monster_sites import site_living_members, site_state

        self.assertEqual(site_state(site_key, wilderness=self.script).state, "populated")
        living = site_living_members(site_key, wilderness=self.script)
        self.assertTrue(living.available)
        self.assertEqual(
            {
                f.observation_key
                for f in population_view(self.script, [cell])
                if f.kind == "monster"
            },
            {f"object:{member.pk}" for member in living.members},
        )

        for member in living.members:
            member.traits.hp.current = 0
        population_lifecycle.settle_population_lifecycle(100, 200)
        self.assertEqual(site_state(site_key, wilderness=self.script).state, "cleared")
        # A cleared habitat is absent.
        self.assertEqual(
            [f for f in population_view(self.script, [cell]) if f.kind == "monster"], []
        )

        # A due recovery whose clock stage has not settled is still only a
        # schedule: it stays a cleared, empty habitat. The recovery delay is
        # synthetic because the site's authored lifecycle is not this test's
        # subject.
        site = sites[site_key]
        states = {key: dict(value) for key, value in self.script.db.monster_sites.items()}
        cleared_at = 199
        states[site_key]["cleared_at_tick"] = cleared_at
        self.script.db.monster_sites = states
        import world.maps.monster_sites as monster_sites_module

        with patch.object(
            monster_sites_module,
            "MONSTER_SITE_REGISTRY",
            {**sites, site_key: replace(site, recover_after_ticks=1)},
        ):
            due = site_state(site_key, wilderness=self.script)
            self.assertEqual((due.state, due.cleared_at_tick), ("cleared", cleared_at))
            self.assertEqual(
                [f for f in population_view(self.script, [cell]) if f.kind == "monster"],
                [],
            )
            unchanged = site_state(site_key, wilderness=self.script)
            self.assertEqual(
                (unchanged.state, unchanged.cleared_at_tick), ("cleared", cleared_at)
            )

    @covers_requirement(
        "wilderness-population-view::population-reads-report-actual-living-registrations"
    )
    def test_population_view_does_not_construct_traits(self):
        # Create a Monster object with stored HP attributes but NO constructed trait handler
        monster = create_object(Monster, key="dormant_guardian")
        # Set raw attribute directly without touching monster.traits
        monster.attributes.add("traits", {"hp": {"base": 10, "current": 10}}, category="traits")
        self.script.db.itemcoordinates[monster] = self.cell

        # Force the trait handler cold as in test_the_read_modifies_nothing_even_from_a_cold_trait_handler
        monster.__dict__.pop("traits", None)
        self.assertNotIn("traits", monster.__dict__)

        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as queries:
            facts = population_view(self.script, [self.cell])

        guardian_fact = next((f for f in facts if f.observation_key == f"object:{monster.pk}"), None)
        self.assertIsNotNone(guardian_fact)
        self.assertEqual(guardian_fact.label, "dormant_guardian")

        # Verify monster.traits was NOT constructed in instance __dict__
        self.assertNotIn("traits", monster.__dict__)
        # And raw attribute was not mutated
        raw_traits = monster.attributes.get("traits", category="traits")
        self.assertEqual(raw_traits, {"hp": {"base": 10, "current": 10}})

        # Assert no SQL writes occurred during the read
        writes = [
            query["sql"]
            for query in queries
            if any(verb in query["sql"].lower() for verb in ("update", "insert", "delete"))
        ]
        self.assertEqual(writes, [])

    def test_foreign_and_character_entities_distinct_identities(self):
        cell = self.cell
        from typeclasses.characters import PlayerCharacter

        char = create_object(PlayerCharacter, key="traveler_bob")
        self.script.db.itemcoordinates[char] = cell

        foreign_monster = create_object(Monster, key="wandering_beast")
        foreign_monster.attributes.add("traits", {"hp": {"current": 25}}, category="traits")
        self.script.db.itemcoordinates[foreign_monster] = cell

        facts = population_view(self.script, [cell])
        char_fact = next((f for f in facts if f.observation_key == f"object:{char.pk}"), None)
        monster_fact = next((f for f in facts if f.observation_key == f"object:{foreign_monster.pk}"), None)

        self.assertIsNotNone(char_fact)
        self.assertEqual(char_fact.kind, "character")
        self.assertFalse(char_fact.hostile)

        self.assertIsNotNone(monster_fact)
        self.assertEqual(monster_fact.kind, "monster")
        self.assertTrue(monster_fact.hostile)
        self.assertNotEqual(char_fact.observation_key, monster_fact.observation_key)

    # -- actual individuals of every owner ---------------------------------

    def _registered(self, entity: Any, cell: tuple[int, int]):
        self.script.db.itemcoordinates[entity] = cell
        return entity

    def _living_tier_monster(self, key: str, tier: str) -> Monster:
        monster = create_object(Monster, key=key)
        monster.threat_tier = tier
        monster.apply_monster_tier("floor")
        return monster

    @covers_requirement(
        "wilderness-population-view::population-reads-report-actual-living-registrations"
    )
    def test_every_actual_living_owner_is_reported_once_with_canonical_facts(self):
        from typeclasses.characters import PlayerCharacter
        from world.rules.monster_individual import construct_species_individual

        cell = self.cell
        tier = next(iter(live_monster_tier_registry()))
        variants = _live_registry(
            "world.lore.monster_species", "MONSTER_VARIANT" + "_REGISTRY"
        )

        # Explicit, site-owned (its site state is absent), foreign and an
        # explicitly placed individual are all ordinary actual facts.
        explicit = self._living_tier_monster("t_drifted_explicit", tier)
        self._registered(explicit, cell)
        site_member = self._living_tier_monster("t_ownerless_site_member", tier)
        site_member.db.site_key = next(iter(live_monster_site_registry()))
        self._registered(site_member, cell)
        foreign = self._living_tier_monster("t_foreign_witness", tier)
        self._registered(foreign, cell)
        twin = self._living_tier_monster(explicit.key, tier)
        self._registered(twin, cell)

        variant_key = next(
            key for key in sorted(variants) if variants[key].danger_grade is not None
        )
        variant = variants[variant_key]
        species = construct_species_individual(variant.species_key, variant_key)
        self._registered(species, cell)

        # A dead individual, an unregistered living one and one standing on a
        # different cell are not present here.
        dead = create_object(Monster, key="t_dead_sentinel")
        dead.attributes.add("traits", {"hp": {"current": 0}}, category="traits")
        self._registered(dead, cell)
        unregistered = create_object(Monster, key="t_unregistered_wanderer")
        unregistered.attributes.add("traits", {"hp": {"current": 5}}, category="traits")
        elsewhere = self._living_tier_monster("t_elsewhere_beast", tier)
        self._registered(elsewhere, (cell[0] + 40, cell[1]))

        char = create_object(PlayerCharacter, key="t_traveller")
        self._registered(char, cell)
        npc = create_object(NPC, key="t_merchant")
        self._registered(npc, cell)

        facts = population_view(self.script, [cell])
        monsters = [fact for fact in facts if fact.kind == "monster"]
        living = (explicit, site_member, foreign, twin, species)
        self.assertEqual(
            {fact.observation_key for fact in monsters},
            {f"object:{monster.pk}" for monster in living},
        )
        self.assertEqual(len(monsters), len(living))
        by_key = {fact.observation_key: fact for fact in monsters}
        for monster in (explicit, site_member, foreign, twin):
            fact = by_key[f"object:{monster.pk}"]
            self.assertTrue(fact.hostile)
            self.assertEqual(fact.cell, cell)
            self.assertEqual(fact.threat_tier, tier)
            self.assertIsNone(fact.danger_grade)
        species_fact = by_key[f"object:{species.pk}"]
        self.assertEqual(
            (species_fact.threat_tier, species_fact.danger_grade),
            (variant.threat_tier, variant.danger_grade),
        )
        self.assertEqual(by_key[f"object:{twin.pk}"].label, explicit.key)
        self.assertEqual(
            {
                (fact.observation_key, fact.kind, fact.hostile, fact.label)
                for fact in facts
                if fact.kind != "monster"
            },
            {
                (f"object:{char.pk}", "character", False, "t_traveller"),
                (f"object:{npc.pk}", "npc", False, "t_merchant"),
                (
                    f"object:{self.char1.pk}",
                    "character",
                    False,
                    self.char1.key,
                ),
            },
        )
        for absent in (dead, unregistered, elsewhere):
            self.assertNotIn(f"object:{absent.pk}", by_key)

    @covers_requirement(
        "wilderness-population-view::population-reads-report-actual-living-registrations"
    )
    def test_a_moved_individual_is_absent_from_its_former_cell(self):
        from evennia.contrib.grid.wilderness.wilderness import enter_wilderness

        first = self.cell
        second = next(candidate for candidate in _two_wild_cells() if candidate != first)
        monster = self._living_tier_monster(
            "t_mover", next(iter(live_monster_tier_registry()))
        )
        self._registered(monster, first)
        key = f"object:{monster.pk}"
        self.assertEqual(
            [
                fact.observation_key
                for fact in population_view(self.script, [first, second])
                if fact.kind == "monster"
            ],
            [key],
        )

        # The room it stands in now reports the first cell; the registration is
        # the authoritative current position.
        self.assertTrue(enter_wilderness(self.char1, coordinates=first, name=WILDERNESS_NAME))
        monster.location = self.char1.location
        self.script.db.itemcoordinates[monster] = second
        self.assertEqual(
            {
                fact.cell: fact.observation_key
                for fact in population_view(self.script, [first, second])
                if fact.kind == "monster"
            },
            {second: key},
        )

    @covers_requirement(
        "wilderness-population-view::observation-identity-belongs-to-persistent-individuals"
    )
    def test_a_same_label_birth_gets_a_fresh_identity(self):
        cell = self.cell
        first = create_object(Monster, key="t_repeated_beast")
        first.attributes.add("traits", {"hp": {"current": 4}}, category="traits")
        self._registered(first, cell)
        survivor = create_object(Monster, key="t_repeated_beast")
        survivor.attributes.add("traits", {"hp": {"current": 4}}, category="traits")
        self._registered(survivor, cell)
        first_key, survivor_key = f"object:{first.pk}", f"object:{survivor.pk}"
        self.assertEqual(
            {
                fact.observation_key
                for fact in population_view(self.script, [cell])
                if fact.kind == "monster"
            },
            {first_key, survivor_key},
        )

        self.script.db.itemcoordinates.pop(first)
        first.delete()
        replacement = create_object(Monster, key="t_repeated_beast")
        replacement.attributes.add("traits", {"hp": {"current": 4}}, category="traits")
        self._registered(replacement, cell)
        replacement_key = f"object:{replacement.pk}"
        self.assertNotIn(replacement_key, {first_key, survivor_key})
        self.assertEqual(
            {
                fact.observation_key
                for fact in population_view(self.script, [cell])
                if fact.kind == "monster"
            },
            {survivor_key, replacement_key},
        )

    def test_a_hostile_interrupt_needs_an_actual_living_individual(self):
        from world.rules.travel_interrupts import (
            MovementFacts,
            live_hostile_facts,
            movement_flags,
        )

        location = SimpleNamespace(wilderness=self.script)
        before = MovementFacts(
            cell=self.cell,
            tick=0,
            landmarks=frozenset(),
            lit_districts=frozenset(),
            distant_sources=frozenset(),
            hostiles=frozenset(),
            travellers=(),
        )

        # A due authored habitat with no living member is a schedule, not an
        # entity, so it can neither be sighted nor interrupt a step.
        site = live_monster_site_registry()[next(iter(live_monster_site_registry()))]
        self.assertEqual(live_hostile_facts(location, [site.coordinates]), ())
        self.assertEqual(movement_flags(before, before), ())

        monster = self._living_tier_monster(
            "t_sighted_beast", next(iter(live_monster_tier_registry()))
        )
        self._registered(monster, before.cell)
        facts = live_hostile_facts(location, [before.cell])
        self.assertEqual(
            [fact.observation_key for fact in facts], [f"object:{monster.pk}"]
        )
        after = replace(
            before, cell=(before.cell[0] + 1, before.cell[1]),
            hostiles=frozenset(fact.observation_key for fact in facts),
        )
        self.assertEqual(movement_flags(before, after), ("hostile_in_sight",))
        # The same existing individual in the same room adds nothing.
        self.assertEqual(movement_flags(after, after), ())

        monster.traits.hp.current = 0
        self.assertEqual(live_hostile_facts(location, [before.cell]), ())
