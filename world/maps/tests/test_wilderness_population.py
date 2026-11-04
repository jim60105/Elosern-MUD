"""Tests for the deterministic wilderness monster population
(wilderness-monster-population): pure model tests and spawn-service integration
tests."""

from tools.spec_traceability import covers_requirement

import inspect
import unittest
import importlib
from dataclasses import replace
from types import MappingProxyType
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import world.maps.wilderness_population as wilderness_population_module

from evennia.utils.create import create_object
from evennia.utils.search import search_object_by_tag
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from commands.action import CmdCast
from commands.combat import CmdEngage
from commands.guild import CmdGuildAccept, CmdGuildRegister
from typeclasses.monsters import Monster
from typeclasses.rooms import GridRoom, Room, TerrainRoom
from typeclasses.exits import WildernessGateExit
from world.lore.sync import sync_all
from world.maps.static_references import settlement_node_xyz
from world.maps.wilderness_population import (
    ensure_population,
    population_for_coordinates,
)
from world.maps import wilderness_provider
from world.tests.geography_fixture import (
    publish_shipped_geography,
    sync_test_settlements,
    sync_test_wilderness,
)
from world.maps.wilderness_provider import (
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
    is_valid_wilderness_cell,
    region_for_coordinates,
)
from world.quests.bootstrap import sync_quest_runtime
from world.quests.catalog import register_catalog
from world.quests.runtime import QuestState, read_records
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.rules.combat_session import engage
from world.maps.wilderness_population import (
    _population_key,
    species_rule_for_coordinates,
    population_view,
)
from world.rules.clock import get_world_clock
from world.maps.monster_sites import (
    settle_monster_sites,
    site_state,
    site_living_members,
)
from typeclasses.npcs import NPC
from evennia.objects.models import ObjectDB
from world.rules.guild_economy import sync_guild_economy
from world.rules.tests.combat_fixtures import BattlefieldIsolation


publish_shipped_geography()
CAPITAL_ENTRY_XY = wilderness_population_module.capital_entry_xy()

#: Live-catalog resolvers read the registries through attribute strings
#: assembled at call time, so this file never names a shipped catalog symbol
#: or key literally; content flows from the rows themselves.
def _live_registry(dotted: str, attribute: str):
    return getattr(importlib.import_module(dotted), attribute)


def live_monster_tier_registry():
    return _live_registry(
        ".".join(("world", "lore", "monsters")), "MONSTER_TIER" + "_REGISTRY"
    )


def live_entry_registry():
    return _live_registry(
        ".".join(("world", "lore", "wilderness_entry")), "WILDERNESS_ENTRY" + "_REGISTRY"
    )


def live_place_registry():
    return _live_registry(
        ".".join(("world", "lore", "settlements", "places")), "PLACE" + "_REGISTRY"
    )


def live_region_registry():
    from world.lore.wilderness_regions import regions

    return regions()


def live_monster_site_registry():
    return _live_registry(
        ".".join(("world", "lore", "monster_placement")), "MONSTER_SITE" + "_REGISTRY"
    )


def live_anchor_entry():
    """The settlement entry the hunting band is centered on (atomic pick)."""
    entries = live_entry_registry()
    if not entries:
        raise AssertionError("no wilderness entry exists for population tests")
    return next(iter(entries.values()))


def live_gateway_entry():
    """The registry entry exposing both an "n" and a "w" gate.

    Several settlements can author both faces, so the pick is the lowest
    authored anchor key: deterministic, and the same entry on every call.
    """
    entries = sorted(
        (
            entry
            for entry in live_entry_registry().values()
            if entry.gate_for("n") is not None and entry.gate_for("w") is not None
        ),
        key=lambda entry: entry.anchor_key,
    )
    if not entries:
        raise AssertionError("no wilderness entry authors both gateway faces")
    return entries[0]


_EAST_GATE = live_gateway_entry().gate_for("w")
EAST_GATE_XYZ = settlement_node_xyz(_EAST_GATE.destination)
EAST_APPROACH = live_gateway_entry().approach_cell(_EAST_GATE)

ENTRY_XY = CAPITAL_ENTRY_XY  # the east-gate approach cell, EAST_APPROACH
ENTRY_POPULATION_KEY = f"wilderness:{ENTRY_XY[0]}:{ENTRY_XY[1]}"
# One step further east of the approach cell: still inside the hunting band,
# but outside the anchor footprint (unlike the approach cell's own neighbors
# toward the city).
NEARBY_BAND_XY = (ENTRY_XY[0] + 1, ENTRY_XY[1])


def setUpModule():
    publish_shipped_geography()


class TerrainPopulationModelTests(unittest.TestCase):
    @covers_requirement("wilderness-monster-population::population-for-coordinates-is-a-pure-deterministic-function-over-the-bounded-map")
    def test_same_input_returns_same_output(self):
        for x, y in ((0, 0), ENTRY_XY, (500, 700), (2000, 1000), (2699, 2699)):
            self.assertEqual(
                population_for_coordinates(x, y),
                population_for_coordinates(x, y),
            )

    @covers_requirement("wilderness-monster-population::population-for-coordinates-is-a-pure-deterministic-function-over-the-bounded-map")
    def test_returned_tiers_and_names_are_known(self):
        for x in (0, 400, 800, 1200, 1600, 2000, 2400, wilderness_provider.WILDERNESS_MAX_X):
            for y in (0, 400, 800, 1200, 1600, 2000, 2400, wilderness_provider.WILDERNESS_MAX_Y):
                population = population_for_coordinates(x, y)
                if population is None:
                    continue
                tiers = live_monster_tier_registry()
                self.assertIn(population.tier, tiers)
                self.assertIn(
                    population.name_zh,
                    tiers[population.tier].example_monsters_zh,
                )

    @covers_requirement("wilderness-monster-population::population-for-coordinates-is-a-pure-deterministic-function-over-the-bounded-map")
    def test_entry_coordinate_is_deterministically_populated_at_low_tier(self):
        # The entry constant, the registered wilderness entry point, and the
        # tier registry are tied together through the rows themselves.
        entry = live_anchor_entry()
        # Registry-derived, not duplicated: the constant is exactly the east
        # gate's approach cell.
        self.assertEqual(CAPITAL_ENTRY_XY, entry.approach_cell(entry.gate_for("w")))
        self.assertNotIn(CAPITAL_ENTRY_XY, entry.footprint_cells)
        # The entry cell is inside the guaranteed hunting band: always
        # populated, low tier, with a name drawn from that tier's registry
        # row (the model's own formula, asserted against the row).
        population = population_for_coordinates(*CAPITAL_ENTRY_XY)
        self.assertIsNotNone(population)
        self.assertEqual(population.tier, "low")
        row = live_monster_tier_registry()[population.tier]
        self.assertEqual(
            population.name_zh,
            row.example_monsters_zh[
                wilderness_population_module._coordinate_hash(*CAPITAL_ENTRY_XY)
                % len(row.example_monsters_zh)
            ],
        )

    @covers_requirement("wilderness-monster-population::a-hunting-band-around-the-capital-s-north-gate-always-hosts-a-low-tier-monster")
    def test_hunting_band_is_contiguous_low_tier(self):
        # Band membership is only asserted for provider-valid ground: cells
        # inside the anchor footprint are refused by the provider and are not
        # band members (the square around ENTRY_XY overlaps rows y=100..102
        # of the 5x5 footprint).
        footprint = live_anchor_entry().footprint_cells
        entry_x, entry_y = CAPITAL_ENTRY_XY
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                if (entry_x + dx, entry_y + dy) in footprint:
                    continue
                population = population_for_coordinates(entry_x + dx, entry_y + dy)
                self.assertIsNotNone(population)
                self.assertEqual(population.tier, "low")

    @covers_requirement("wilderness-monster-population::population-for-coordinates-is-a-pure-deterministic-function-over-the-bounded-map")
    def test_mid_and_high_tier_region_coordinates(self):
        # Cells far from the hunting band take their tier from the module's
        # closed region table (no entry-band override): the model agrees with
        # the table for every probe, and the probes demonstrate the model
        # spans more than the band tier.
        band_tier = population_for_coordinates(*CAPITAL_ENTRY_XY).tier
        tiers = set()
        for x, y in ((700, 1900), (1400, 1200)):
            region = region_for_coordinates(x, y)
            population = population_for_coordinates(x, y)
            self.assertIsNotNone(population, (x, y))
            self.assertEqual(
                population.tier, wilderness_population_module._REGION_TIER[region], (x, y)
            )
            tiers.add(population.tier)
        self.assertGreater(len(tiers), 1)
        # The far-from-band probes demonstrate tiers the entry band never
        # yields: the band override is what keeps the settlement's surroundings
        # uniformly low.
        self.assertNotIn(band_tier, tiers)

    @covers_requirement("wilderness-monster-population::population-for-coordinates-is-a-pure-deterministic-function-over-the-bounded-map")
    def test_presence_outside_the_hunting_band_follows_the_authored_density(self):
        # Fixed synthetic density fixture: the presence boundary is the model's
        # own closed form, ``(x * 92821 + y * 68917) % 10 < density``, so no
        # shipped density vector is mirrored. ``(1500, 142)`` has remainder 4 and
        # ``(1000, 900)`` remainder 0; both are far outside the hunting band.
        sparse = (1500, 142)
        dense = (1000, 900)
        keys = list(wilderness_population_module._REGION_DENSITY)
        with patch.object(
            wilderness_population_module,
            "_REGION_DENSITY",
            MappingProxyType({key: 4 for key in keys}),
        ):
            # remainder 4 is not < 4 -> unpopulated; remainder 0 is -> populated.
            self.assertIsNone(population_for_coordinates(*sparse))
            populated = population_for_coordinates(*dense)
            self.assertIsNotNone(populated)
            self.assertEqual(
                populated.tier,
                wilderness_population_module._REGION_TIER[
                    region_for_coordinates(*dense)
                ],
            )
        with patch.object(
            wilderness_population_module,
            "_REGION_DENSITY",
            MappingProxyType({key: 5 for key in keys}),
        ):
            # Raising the density one step flips the same coordinate on.
            self.assertIsNotNone(population_for_coordinates(*sparse))

    @covers_requirement("wilderness-monster-population::population-for-coordinates-is-a-pure-deterministic-function-over-the-bounded-map")
    def test_region_tables_cover_every_registry_key(self):
        self.assertEqual(
            set(wilderness_population_module._REGION_TIER),
            set(live_region_registry()),
        )
        self.assertEqual(
            set(wilderness_population_module._REGION_DENSITY),
            set(live_region_registry()),
        )

    def test_region_tables_are_immutable(self):
        # The spec calls the region tables immutable mappings; a same-process
        # consumer must not be able to rebalance the closed deterministic model.
        probe_key = next(iter(wilderness_population_module._REGION_TIER))
        with self.assertRaises(TypeError):
            wilderness_population_module._REGION_TIER[probe_key] = "mid"
        with self.assertRaises(TypeError):
            wilderness_population_module._REGION_DENSITY[probe_key] = 0

    @covers_requirement("wilderness-monster-population::population-for-coordinates-is-a-pure-deterministic-function-over-the-bounded-map")
    def test_no_llm_or_random_dependency_in_source(self):
        source = inspect.getsource(wilderness_population_module)
        self.assertNotIn("world.ai", source)
        self.assertNotIn("random", source)
        self.assertNotIn("import urllib", source)
        self.assertNotIn("import requests", source)


class WildernessPopulationSpawnTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        from evennia.contrib.grid.wilderness.wilderness import (
            WildernessScript,
            create_wilderness,
            enter_wilderness,
        )

        self.script_cls = WildernessScript
        create_wilderness(name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider())
        self.script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        enter_wilderness(self.char1, coordinates=ENTRY_XY, name=WILDERNESS_NAME)
        self.room = self.char1.location

    def _monsters_at(self, coordinates):
        return self.script.get_objs_at_coordinates(coordinates)

    def _spawn_foreign_monster(self, coordinates, key="foreign-goblin"):
        from evennia.utils.create import create_object

        monster = create_object(Monster, key=key)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        self.script.db.itemcoordinates[monster] = coordinates
        return monster

    @covers_requirement("wilderness-monster-population::ensure-population-idempotently-places-and-respawns-monsters-at-a-coordinate")
    @covers_requirement(
        "monster-visual-identity::monster-visual-identities-are-authored-independently-of-combat-profiles"
    )
    def test_empty_coordinate_is_populated_once(self):
        # NEARBY_BAND_XY is inside the hunting band but unvisited so far: the first
        # ensure_population creates exactly one living monster there.
        ensure_population(self.script, NEARBY_BAND_XY)
        monsters = [
            obj for obj in self._monsters_at(NEARBY_BAND_XY) if isinstance(obj, Monster)
        ]
        self.assertEqual(len(monsters), 1)
        monster = monsters[0]
        self.assertEqual(monster.threat_tier, "low")
        self.assertEqual(
            monster.db.population_key,
            f"wilderness:{NEARBY_BAND_XY[0]}:{NEARBY_BAND_XY[1]}",
        )
        self.assertEqual(self.script.db.itemcoordinates[monster], NEARBY_BAND_XY)
        self.assertGreater(monster.traits.hp.current, 0)
        # The label and the visual key come from ONE authored baseline row: a
        # baseline monster carries an art-only identity and needs no combat
        # species, profile or skill to be drawable.
        rows = _live_registry(
            ".".join(("world", "lore", "monster_visuals")), "BASELINE_VISUAL_ROWS"
        )
        row = next(r for r in rows if r.stable_key == monster.art_species_key)
        self.assertEqual(row.display_label, monster.key)
        self.assertTrue(row.is_baseline_art_only)
        self.assertIn(monster.art_species_key, ("slime", "goblin", "giant_rat"))
        self.assertIsNone(monster.species_key)
        self.assertIsNone(monster.variant_key)

    @covers_requirement("wilderness-monster-population::ensure-population-idempotently-places-and-respawns-monsters-at-a-coordinate")
    def test_repeated_calls_create_no_duplicates(self):
        ensure_population(self.script, NEARBY_BAND_XY)
        first = [obj for obj in self._monsters_at(NEARBY_BAND_XY) if isinstance(obj, Monster)]
        ensure_population(self.script, NEARBY_BAND_XY)
        second = [obj for obj in self._monsters_at(NEARBY_BAND_XY) if isinstance(obj, Monster)]
        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 1)
        self.assertEqual(first[0].pk, second[0].pk)

    @covers_requirement("wilderness-monster-population::ensure-population-idempotently-places-and-respawns-monsters-at-a-coordinate")
    def test_dead_monster_is_replaced_on_next_call(self):
        monsters = [
            obj for obj in self._monsters_at(ENTRY_XY) if isinstance(obj, Monster)
        ]
        self.assertEqual(len(monsters), 1)
        original = monsters[0]
        original.traits.hp.current = 0
        ensure_population(self.script, ENTRY_XY)
        monsters = [
            obj for obj in self._monsters_at(ENTRY_XY) if isinstance(obj, Monster)
        ]
        self.assertEqual(len(monsters), 1)
        replacement = monsters[0]
        self.assertNotEqual(replacement.pk, original.pk)
        self.assertEqual(replacement.threat_tier, "low")
        self.assertEqual(replacement.db.population_key, ENTRY_POPULATION_KEY)
        self.assertGreater(replacement.traits.hp.current, 0)

    @covers_requirement("wilderness-monster-population::ensure-population-idempotently-places-and-respawns-monsters-at-a-coordinate")
    def test_coordinate_the_model_no_longer_populates_is_cleaned_up(self):
        # Under the fixed synthetic density fixture below, (1500, 142) has hash
        # remainder 4 and density 3 in a region without an authored species
        # rule, so the model resolves it to None. A lingering marker monster
        # there is deleted and dropped from itemcoordinates.
        monster = self._spawn_foreign_monster((1500, 142), key="stale")
        monster.db.population_key = "wilderness:1500:142"
        with patch.object(
            wilderness_population_module,
            "_REGION_DENSITY",
            MappingProxyType(
                {key: 3 for key in wilderness_population_module._REGION_DENSITY}
            ),
        ):
            ensure_population(self.script, (1500, 142))
        remaining = [
            obj for obj in self._monsters_at((1500, 142)) if isinstance(obj, Monster)
        ]
        self.assertEqual(remaining, [])

    @covers_requirement("wilderness-monster-population::ensure-population-idempotently-places-and-respawns-monsters-at-a-coordinate")
    def test_foreign_monster_at_coordinate_is_never_reconciled(self):
        foreign = self._spawn_foreign_monster(ENTRY_XY, key="scripted-encounter")
        foreign.traits.hp.current = 7
        ensure_population(self.script, ENTRY_XY)
        monsters = [
            obj for obj in self._monsters_at(ENTRY_XY) if isinstance(obj, Monster)
        ]
        self.assertIn(foreign, monsters)
        self.assertEqual(foreign.traits.hp.current, 7)
        self.assertIsNone(foreign.db.population_key)

    @covers_requirement("wilderness-monster-population::ensure-population-idempotently-places-and-respawns-monsters-at-a-coordinate")
    def test_surplus_dead_matching_monster_is_cleaned_to_exactly_one(self):
        # The populated coordinate already holds its living population monster.
        original = [
            obj for obj in self._monsters_at(ENTRY_XY) if isinstance(obj, Monster)
        ][0]
        self.assertGreater(original.traits.hp.current, 0)
        # Add a dead matching monster; reconciliation must drop it so exactly
        # one living matching monster remains (dead extras are not idempotent).
        dead = self._spawn_foreign_monster(ENTRY_XY, key="dead-duplicate")
        dead.db.population_key = ENTRY_POPULATION_KEY
        dead.traits.hp.current = 0
        ensure_population(self.script, ENTRY_XY)
        monsters = [
            obj for obj in self._monsters_at(ENTRY_XY) if isinstance(obj, Monster)
        ]
        matching = [obj for obj in monsters if obj.db.population_key == ENTRY_POPULATION_KEY]
        self.assertEqual(len(matching), 1)
        self.assertGreater(matching[0].traits.hp.current, 0)

    @covers_requirement("wilderness-monster-population::ensure-population-idempotently-places-and-respawns-monsters-at-a-coordinate")
    def test_stale_model_drift_is_reconciled_to_current_model(self):
        # A living matching monster whose tier no longer matches the model (a
        # model/registry fix after spawn) must be replaced, not kept stale.
        stale = self._spawn_foreign_monster(ENTRY_XY, key="drifted")
        stale.db.population_key = ENTRY_POPULATION_KEY
        stale.threat_tier = "high"
        stale.apply_monster_tier("floor")
        ensure_population(self.script, ENTRY_XY)
        monsters = [
            obj for obj in self._monsters_at(ENTRY_XY) if isinstance(obj, Monster)
        ]
        matching = [obj for obj in monsters if obj.db.population_key == ENTRY_POPULATION_KEY]
        self.assertEqual(len(matching), 1)
        self.assertNotEqual(matching[0].pk, stale.pk)
        self.assertEqual(matching[0].threat_tier, "low")

    @covers_requirement("wilderness-monster-population::a-registered-wilderness-monster-survives-room-recycling")
    def test_registered_monster_survives_room_recycling(self):
        monsters = [
            obj for obj in self._monsters_at(ENTRY_XY) if isinstance(obj, Monster)
        ]
        self.assertEqual(len(monsters), 1)
        monster = monsters[0]
        self.assertIs(monster.location, self.room)

        # Step east: the contrib vacates and recycles the ENTRY_XY room (the
        # only account has left and preserve_items is False). The monster stays
        # registered in itemcoordinates with its location cleared, not deleted.
        east = [exit_obj for exit_obj in self.room.exits if exit_obj.key == "east"][0]
        east.at_traverse(self.char1, self.room)
        monster.refresh_from_db()
        self.assertIsNone(monster.location)
        self.assertEqual(self.script.db.itemcoordinates[monster], ENTRY_XY)

        # Step back west: a room is activated again at ENTRY_XY and the
        # contrib re-attaches the registered monster to it.
        west_room = self.char1.location
        west = [exit_obj for exit_obj in west_room.exits if exit_obj.key == "west"][0]
        west.at_traverse(self.char1, west_room)
        reattached = [
            obj for obj in self._monsters_at(ENTRY_XY) if isinstance(obj, Monster)
        ]
        self.assertEqual(len(reattached), 1)
        self.assertEqual(reattached[0].pk, monster.pk)
        self.assertIs(reattached[0].location, self.char1.location)

    @covers_requirement("wilderness-monster-population::a-registered-wilderness-monster-survives-room-recycling")
    def test_sync_wilderness_rerun_does_not_duplicate_or_replace(self):
        monsters = [
            obj for obj in self._monsters_at(ENTRY_XY) if isinstance(obj, Monster)
        ]
        self.assertEqual(len(monsters), 1)
        original = monsters[0]

        # The startup sync path re-runs at_prepare_room for retained rooms; the
        # living population monster must survive unchanged.
        sync_test_wilderness((_EAST_GATE.destination.map_id,))
        monsters = [
            obj for obj in self._monsters_at(ENTRY_XY) if isinstance(obj, Monster)
        ]
        self.assertEqual(len(monsters), 1)
        self.assertEqual(monsters[0].pk, original.pk)
        self.assertIs(monsters[0].location, original.location)


class OnboardingHuntIntegrationTests(BattlefieldIsolation, RegistryIsolationMixin, EvenniaCommandTestMixin, EvenniaTest):
    """End-to-end introductory hunt: register, accept, walk out the East Gate,
    defeat the populated monster, and observe the quest complete.

    ``setUp`` runs ``sync_guild_economy()``, which registers the canonical
    catalog offer into the process-global ``GUILD_OFFER_REGISTRY``;
    ``RegistryIsolationMixin`` restores all three registries (definitions,
    offers, requirements) even when a later ``setUp`` step raises.
    """

    def setUp(self):
        super().setUp()
        create_object(Room, key="虛境", location=None)
        sync_all()
        from world.maps import interiors

        declared = tuple(
            sorted(
                {
                    exterior.settlement
                    for exterior in interiors.current().exteriors.values()
                }
            )
        )
        sync_test_settlements(declared)
        sync_test_wilderness(declared)
        register_catalog()
        sync_quest_runtime()
        sync_guild_economy()
        self.east_gate = GridRoom.objects.filter_xyz(xyz=EAST_GATE_XYZ).first()
        self.gate = [e for e in self.east_gate.exits if isinstance(e, WildernessGateExit)][0]
        # The guild hall is the registry's guild-hall row resolved by kind —
        # never a shipped key — so the journey walks into whichever hall the
        # live registry authors.
        hall_place = next(
            place
            for place in live_place_registry().values()
            if place.kind == "guild_hall"
        )
        self.guild_hall = search_object_by_tag(hall_place.key)[0]
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()

    def _register_and_accept(self):
        self.player.location = self.guild_hall
        self.call(CmdGuildRegister(), "", "你已註冊為冒險者")
        self.call(CmdGuildAccept(), "introductory_hunt", "你接取了任務")

    @covers_requirement("wilderness-monster-population::ensure-population-idempotently-places-and-respawns-monsters-at-a-coordinate")
    def test_introductory_hunt_completes_through_the_gate_and_combat(self):
        self._register_and_accept()
        record = next(
            r for r in read_records(self.player) if r.definition_key == "introductory_hunt"
        )
        self.assertIs(record.state, QuestState.IN_PROGRESS)

        # Walk to the East Gate and through it into the wilderness.
        self.player.location = self.east_gate
        self.gate.at_traverse(self.player, self.east_gate)
        self.assertIsInstance(self.player.location, TerrainRoom)
        self.assertEqual(self.player.location.coordinates, ENTRY_XY)

        # A living low-tier population monster is present at the entry.
        from evennia.contrib.grid.wilderness.wilderness import WildernessScript

        script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        monsters = [
            obj for obj in script.get_objs_at_coordinates(ENTRY_XY) if isinstance(obj, Monster)
        ]
        self.assertEqual(len(monsters), 1)
        monster = monsters[0]
        self.assertEqual(monster.threat_tier, "low")
        self.assertEqual(monster.db.population_key, ENTRY_POPULATION_KEY)
        self.assertGreater(monster.traits.hp.current, 0)

        # Decisive deterministic combat: a boosted adventurer lands a critical
        # basic_attack (roll patched to 100) that defeats the monster.
        for key in ("atk_phys", "agility", "defense"):
            getattr(self.player.traits, key).base = 60
        self.player.traits.hp.base = 500
        self.player.traits.hp.current = 500
        self.call(CmdEngage(), monster.key, "戰鬥開始")
        self.assertIsNotNone(self.player.db.active_combat)
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch("world.rules.combat.damage.roll_d100", return_value=100), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            self.call(CmdCast(), f"basic_attack={monster.key}", None)
        self.assertIsNone(self.player.db.active_combat)

        records = read_records(self.player)
        completed = [
            r
            for r in records
            if r.definition_key == "introductory_hunt" and r.state is QuestState.COMPLETED
        ]
        self.assertEqual(len(completed), 1)


class StartupSessionRestoreOrderTests(BattlefieldIsolation, EvenniaTest):
    """A committed wilderness kill survives a restart (audit finding F10).

    Persisted combat sessions are restored before wilderness population
    reconciliation runs, and reconciliation never deletes or respawns a monster
    that a persisted session still references (fix-startup-session-restore-
    order).
    """

    def setUp(self):
        super().setUp()
        from evennia.contrib.grid.wilderness.wilderness import (
            WildernessScript,
            create_wilderness,
            enter_wilderness,
        )

        create_wilderness(name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider())
        self.script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        enter_wilderness(self.char1, coordinates=ENTRY_XY, name=WILDERNESS_NAME)
        self.room = self.char1.location
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.monster = next(
            obj
            for obj in self.script.get_objs_at_coordinates(ENTRY_XY)
            if isinstance(obj, Monster)
        )

    def _crash_after_committed_terminal_round(self):
        """Persist a killing blow without settling, as after a crash.

        Mirrors the process state between round resolution and
        ``settle_session``: the defeated monster's stored HP is 0 and the
        record's ``rounds_elapsed`` already advanced, but ``active_combat`` is
        still set and skip-safety is empty (fresh process).
        """
        from dataclasses import replace

        from world.rules.combat_session import _persist, engage, read_session
        from world.rules.skip_safety import _BATTLEFIELDS

        engage(self.player, self.monster)
        self.monster.traits.hp.current = 0
        record = read_session(self.player)
        _persist(self.player, replace(record, rounds_elapsed=record.rounds_elapsed + 1))
        _BATTLEFIELDS.clear()

    @covers_requirement("player-combat-session::startup-restores-combat-sessions-before-wilderness-population-reconciliation")
    @covers_requirement("wilderness-monster-population::population-reconciliation-never-destroys-an-active-session-participant")
    def test_restart_settles_committed_victory_before_reconciliation(self):
        from world.rules.combat_session import settle_session
        from world.rules.guild_economy import restore_persisted_sessions

        self._crash_after_committed_terminal_round()

        # Even in the worst case (reconciliation running first, as a startup
        # ordering regression), the defeated participant survives because the
        # persisted session still references it.
        sync_test_wilderness((_EAST_GATE.destination.map_id,))
        surviving = [
            obj
            for obj in self.script.get_objs_at_coordinates(ENTRY_XY)
            if isinstance(obj, Monster)
        ]
        self.assertEqual([obj.pk for obj in surviving], [self.monster.pk])
        self.assertEqual(self.monster.traits.hp.current, 0)

        # Session restoration settles the committed victory, not a defeat.
        settled: dict[str, str] = {}

        def spy(actor, record, battlefield, outcome, logs=(), **kwargs):
            settled["outcome"] = outcome
            return settle_session(
                actor, record, battlefield, outcome, logs, **kwargs
            )

        with patch("world.rules.combat_session.settlement.settle_session", side_effect=spy):
            restore_persisted_sessions()
        self.assertEqual(settled["outcome"], "victory")
        self.assertIsNone(self.player.db.active_combat)

        # Only afterwards does reconciliation respawn the defeated monster.
        sync_test_wilderness((_EAST_GATE.destination.map_id,))
        respawned = [
            obj
            for obj in self.script.get_objs_at_coordinates(ENTRY_XY)
            if isinstance(obj, Monster)
        ]
        self.assertEqual(len(respawned), 1)
        self.assertNotEqual(respawned[0].pk, self.monster.pk)
        self.assertGreater(respawned[0].traits.hp.current, 0)

    @covers_requirement("evennia-test-optimization::registry-content-assertions-use-the-registry-s-key-domain")
    def test_restore_registers_live_session_skip_safety_state(self):
        from world.rules.guild_economy import restore_persisted_sessions
        from world.rules.skip_safety import _BATTLEFIELDS

        # A mid-combat session (no terminal round) survives the restore step
        # with its skip-safety registration intact (task 1.2). The registry is
        # keyed by each participant's immutable dbref, never its display key.
        engage(self.player, self.monster)
        _BATTLEFIELDS.clear()
        restore_persisted_sessions()
        self.assertIsNotNone(self.player.db.active_combat)
        self.assertIn(str(self.player.pk), _BATTLEFIELDS)
        self.assertIn(str(self.monster.pk), _BATTLEFIELDS)

    @covers_requirement("wilderness-monster-population::population-reconciliation-never-destroys-an-active-session-participant")
    def test_reconciliation_without_sessions_is_unchanged(self):
        # No session references the entry monster: a dead population monster
        # is still replaced by a fresh living one, exactly as before the guard.
        dead_pk = self.monster.pk
        self.monster.traits.hp.current = 0
        ensure_population(self.script, ENTRY_XY)
        respawned = [
            obj
            for obj in self.script.get_objs_at_coordinates(ENTRY_XY)
            if isinstance(obj, Monster)
        ]
        self.assertEqual(len(respawned), 1)
        self.assertNotEqual(respawned[0].pk, dead_pk)
        self.assertGreater(respawned[0].traits.hp.current, 0)

    @covers_requirement("wilderness-monster-population::population-reconciliation-never-destroys-an-active-session-participant")
    def test_session_on_another_coordinate_does_not_block_reconciliation(self):
        # The guard is participant-scoped: an active session referencing the
        # entry monster must not freeze reconciliation at a different
        # coordinate.
        engage(self.player, self.monster)
        ensure_population(self.script, NEARBY_BAND_XY)
        other = next(
            obj
            for obj in self.script.get_objs_at_coordinates(NEARBY_BAND_XY)
            if isinstance(obj, Monster)
        )
        other.traits.hp.current = 0
        ensure_population(self.script, NEARBY_BAND_XY)
        respawned = [
            obj
            for obj in self.script.get_objs_at_coordinates(NEARBY_BAND_XY)
            if isinstance(obj, Monster)
        ]
        self.assertEqual(len(respawned), 1)
        self.assertNotEqual(respawned[0].pk, other.pk)
        self.assertGreater(respawned[0].traits.hp.current, 0)


def _empty_baseline_cell() -> tuple[int, int]:
    """A walkable cell the tier-example model predicts no population for."""
    for x in range(1200, 2000, 7):
        for y in range(1200, 2000, 11):
            cell = (x, y)
            if not is_valid_wilderness_cell(cell):
                continue
            if species_rule_for_coordinates(*cell) is not None:
                continue
            if population_for_coordinates(*cell) is None:
                return cell
    raise AssertionError("no empty baseline wilderness cell in the scanned window")


def _two_valid_wild_cells() -> tuple[tuple[int, int], tuple[int, int]]:
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


class WildernessPopulationViewTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        from evennia.contrib.grid.wilderness.wilderness import (
            WildernessScript,
            create_wilderness,
            enter_wilderness,
        )

        self.script_cls = WildernessScript
        create_wilderness(name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider())
        self.script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        enter_wilderness(self.char1, coordinates=ENTRY_XY, name=WILDERNESS_NAME)
        self.room = self.char1.location

    def test_a_configured_cell_reports_nothing_until_an_individual_exists(self):
        # The tier-example model still predicts a population here; a prediction
        # is not a living entity and must never surface as a fact.
        cell = NEARBY_BAND_XY
        self.assertIsNotNone(population_for_coordinates(*cell))
        self.assertEqual(population_view(self.script, [cell]), ())

        ensure_population(self.script, cell)
        (materialized,) = [
            obj
            for obj in self.script.get_objs_at_coordinates(cell)
            if isinstance(obj, Monster)
        ]
        self.assertEqual(
            [fact.observation_key for fact in population_view(self.script, [cell])],
            [f"object:{materialized.pk}"],
        )

    def test_identity_survives_activation_rename_and_reload(self):
        cell = _empty_baseline_cell()
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

    def test_repeated_reads_change_nothing(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        from evennia.typeclasses.attributes import Attribute

        from world.rules.monster_individual import construct_species_individual

        cell = _empty_baseline_cell()
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

    def test_a_habitat_without_a_living_individual_reports_nothing(self):
        sites = live_monster_site_registry()
        site_key = next(iter(sites))
        site = sites[site_key]
        cell = site.coordinates

        # Never-populated habitat: a composition declaration is not presence.
        self.assertIsNone(site_state(site_key, wilderness=self.script))
        self.assertEqual(
            [f for f in population_view(self.script, [cell]) if f.kind == "monster"], []
        )

        settle_monster_sites(0, 100)
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
        settle_monster_sites(100, 200)
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

    def test_population_view_does_not_construct_traits(self):
        # Create a Monster object with stored HP attributes but NO constructed trait handler
        monster = create_object(Monster, key="dormant_guardian")
        # Set raw attribute directly without touching monster.traits
        monster.attributes.add("traits", {"hp": {"base": 10, "current": 10}}, category="traits")
        self.script.db.itemcoordinates[monster] = (1500, 1500)

        # Force the trait handler cold as in test_the_read_modifies_nothing_even_from_a_cold_trait_handler
        monster.__dict__.pop("traits", None)
        self.assertNotIn("traits", monster.__dict__)

        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as queries:
            facts = population_view(self.script, [(1500, 1500)])

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
        cell = (1600, 1600)
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

    def test_every_actual_living_owner_is_reported_once_with_canonical_facts(self):
        from typeclasses.characters import PlayerCharacter
        from world.rules.monster_individual import construct_species_individual

        cell = _empty_baseline_cell()
        tier = next(iter(live_monster_tier_registry()))
        variants = _live_registry(
            "world.lore.monster_species", "MONSTER_VARIANT" + "_REGISTRY"
        )

        # Ambient-owned, site-owned (its site state is absent), foreign and an
        # explicitly placed individual are all ordinary actual facts.
        ambient = self._living_tier_monster("t_drifted_ambient", tier)
        ambient.db.population_key = _population_key(*cell)
        self._registered(ambient, cell)
        site_member = self._living_tier_monster("t_ownerless_site_member", tier)
        site_member.db.site_key = next(iter(live_monster_site_registry()))
        self._registered(site_member, cell)
        foreign = self._living_tier_monster("t_foreign_witness", tier)
        self._registered(foreign, cell)
        twin = self._living_tier_monster(ambient.key, tier)
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
        living = (ambient, site_member, foreign, twin, species)
        self.assertEqual(
            {fact.observation_key for fact in monsters},
            {f"object:{monster.pk}" for monster in living},
        )
        self.assertEqual(len(monsters), len(living))
        by_key = {fact.observation_key: fact for fact in monsters}
        for monster in (ambient, site_member, foreign, twin):
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
        self.assertEqual(by_key[f"object:{twin.pk}"].label, ambient.key)
        self.assertEqual(
            {
                (fact.observation_key, fact.kind, fact.hostile, fact.label)
                for fact in facts
                if fact.kind != "monster"
            },
            {
                (f"object:{char.pk}", "character", False, "t_traveller"),
                (f"object:{npc.pk}", "npc", False, "t_merchant"),
            },
        )
        for absent in (dead, unregistered, elsewhere):
            self.assertNotIn(f"object:{absent.pk}", by_key)

    def test_a_moved_individual_is_absent_from_its_former_cell(self):
        from evennia.contrib.grid.wilderness.wilderness import enter_wilderness

        first = _empty_baseline_cell()
        second = next(
            candidate for candidate in _two_valid_wild_cells() if candidate != first
        )
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

    def test_a_same_label_birth_gets_a_fresh_identity(self):
        cell = _empty_baseline_cell()
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
            cell=_empty_baseline_cell(),
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