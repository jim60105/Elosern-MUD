"""Tests for the deterministic wilderness monster population
(wilderness-monster-population): pure model tests and spawn-service integration
tests."""

from tools.spec_traceability import covers_requirement

import inspect
import unittest
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
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.lore.sync import sync_all
from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
from world.lore.wilderness_regions import WILDERNESS_REGION_REGISTRY
from world.maps.bootstrap import NORTH_GATE_XYZ, GUILD_HALL_TAG, sync_grid, sync_wilderness
from world.maps.wilderness_population import (
    CAPITAL_ENTRY_XY,
    MonsterPopulation,
    ensure_population,
    population_for_coordinates,
)
from world.maps.wilderness_provider import (
    WILDERNESS_MAX_X,
    WILDERNESS_MAX_Y,
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
    region_for_coordinates,
)
from world.quests.bootstrap import sync_quest_runtime
from world.quests.catalog import register_catalog
from world.quests.runtime import QuestState, read_records
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.rules.combat_session import engage
from world.rules.guild_economy import sync_guild_economy
from world.rules.tests.combat_fixtures import BattlefieldIsolation

ENTRY_XY = WILDERNESS_ENTRY_REGISTRY["capital_altoria"].wilderness_xy


class TerrainPopulationModelTests(unittest.TestCase):
    @covers_requirement("wilderness-monster-population::population-for-coordinates-is-a-pure-deterministic-function-over-the-bounded-map")
    def test_same_input_returns_same_output(self):
        for x, y in ((0, 0), (60, 100), (111, 189), (203, 30), (223, 223)):
            self.assertEqual(
                population_for_coordinates(x, y),
                population_for_coordinates(x, y),
            )

    @covers_requirement("wilderness-monster-population::population-for-coordinates-is-a-pure-deterministic-function-over-the-bounded-map")
    def test_returned_tiers_and_names_are_known(self):
        for x in range(WILDERNESS_MAX_X + 1):
            for y in range(WILDERNESS_MAX_Y + 1):
                population = population_for_coordinates(x, y)
                if population is None:
                    continue
                self.assertIn(population.tier, MONSTER_TIER_REGISTRY)
                self.assertIn(
                    population.name_zh,
                    MONSTER_TIER_REGISTRY[population.tier].example_monsters_zh,
                )

    @covers_requirement("wilderness-monster-population::population-for-coordinates-is-a-pure-deterministic-function-over-the-bounded-map")
    def test_entry_coordinate_resolves_to_spec_pinned_goblin(self):
        # The entry literal pin ties the fixed CAPITAL_ENTRY_XY constant, the
        # registered wilderness entry point, and the tier registry together.
        self.assertEqual(ENTRY_XY, (60, 100))
        self.assertEqual(CAPITAL_ENTRY_XY, (60, 100))
        self.assertEqual(
            population_for_coordinates(60, 100),
            MonsterPopulation(tier="low", name_zh="哥布林"),
        )

    @covers_requirement("wilderness-monster-population::a-hunting-band-around-the-capital-entry-always-hosts-a-low-tier-monster")
    def test_hunting_band_is_contiguous_low_tier(self):
        entry_x, entry_y = CAPITAL_ENTRY_XY
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                population = population_for_coordinates(entry_x + dx, entry_y + dy)
                self.assertIsNotNone(population)
                self.assertEqual(population.tier, "low")

    @covers_requirement("wilderness-monster-population::population-for-coordinates-is-a-pure-deterministic-function-over-the-bounded-map")
    def test_mid_and_high_tier_region_coordinates(self):
        # (50, 160) is inside northwest_highland_forest (mid tier, density 7)
        # and far from the entry band: the presence formula yields a monster.
        self.assertEqual(
            population_for_coordinates(50, 160).tier,
            "mid",
        )
        # (50, 200) is inside north_deep_forest (high tier, density 8).
        self.assertEqual(
            population_for_coordinates(50, 200).tier,
            "high",
        )
        # (110, 50) is inside the central mountain band (high tier, density 8).
        self.assertEqual(
            population_for_coordinates(110, 50).tier,
            "high",
        )

    @covers_requirement("wilderness-monster-population::population-for-coordinates-is-a-pure-deterministic-function-over-the-bounded-map")
    def test_low_density_coordinate_can_be_unpopulated(self):
        # (203, 30) is southeast_coast (density 3); its presence hash is 3, so
        # it falls outside the presence band and the model returns None.
        self.assertIsNone(population_for_coordinates(203, 30))
        self.assertEqual(region_for_coordinates(203, 30), "southeast_coast")

    @covers_requirement("wilderness-monster-population::population-for-coordinates-is-a-pure-deterministic-function-over-the-bounded-map")
    def test_region_tables_cover_every_registry_key(self):
        self.assertEqual(
            set(wilderness_population_module._REGION_TIER),
            set(WILDERNESS_REGION_REGISTRY),
        )
        self.assertEqual(
            set(wilderness_population_module._REGION_DENSITY),
            set(WILDERNESS_REGION_REGISTRY),
        )

    def test_region_tables_are_immutable(self):
        # The spec calls the region tables immutable mappings; a same-process
        # consumer must not be able to rebalance the closed deterministic model.
        with self.assertRaises(TypeError):
            wilderness_population_module._REGION_TIER["western_hills_valleys"] = "high"
        with self.assertRaises(TypeError):
            wilderness_population_module._REGION_DENSITY["western_hills_valleys"] = 0

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
        enter_wilderness(self.char1, coordinates=(60, 100), name=WILDERNESS_NAME)
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
    def test_empty_coordinate_is_populated_once(self):
        # (61, 100) is inside the hunting band but unvisited so far: the first
        # ensure_population creates exactly one living monster there.
        ensure_population(self.script, (61, 100))
        monsters = [
            obj for obj in self._monsters_at((61, 100)) if isinstance(obj, Monster)
        ]
        self.assertEqual(len(monsters), 1)
        monster = monsters[0]
        self.assertEqual(monster.threat_tier, "low")
        self.assertEqual(monster.db.population_key, "wilderness:61:100")
        self.assertEqual(self.script.db.itemcoordinates[monster], (61, 100))
        self.assertGreater(monster.traits.hp.current, 0)

    @covers_requirement("wilderness-monster-population::ensure-population-idempotently-places-and-respawns-monsters-at-a-coordinate")
    def test_repeated_calls_create_no_duplicates(self):
        ensure_population(self.script, (61, 100))
        first = [obj for obj in self._monsters_at((61, 100)) if isinstance(obj, Monster)]
        ensure_population(self.script, (61, 100))
        second = [obj for obj in self._monsters_at((61, 100)) if isinstance(obj, Monster)]
        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 1)
        self.assertEqual(first[0].pk, second[0].pk)

    @covers_requirement("wilderness-monster-population::ensure-population-idempotently-places-and-respawns-monsters-at-a-coordinate")
    def test_dead_monster_is_replaced_on_next_call(self):
        monsters = [
            obj for obj in self._monsters_at((60, 100)) if isinstance(obj, Monster)
        ]
        self.assertEqual(len(monsters), 1)
        original = monsters[0]
        original.traits.hp.current = 0
        ensure_population(self.script, (60, 100))
        monsters = [
            obj for obj in self._monsters_at((60, 100)) if isinstance(obj, Monster)
        ]
        self.assertEqual(len(monsters), 1)
        replacement = monsters[0]
        self.assertNotEqual(replacement.pk, original.pk)
        self.assertEqual(replacement.threat_tier, "low")
        self.assertEqual(replacement.db.population_key, "wilderness:60:100")
        self.assertGreater(replacement.traits.hp.current, 0)

    @covers_requirement("wilderness-monster-population::ensure-population-idempotently-places-and-respawns-monsters-at-a-coordinate")
    def test_coordinate_the_model_no_longer_populates_is_cleaned_up(self):
        # (203, 30) resolves to None (see the pure model tests). A lingering
        # marker monster there is deleted and dropped from itemcoordinates.
        monster = self._spawn_foreign_monster((203, 30), key="stale")
        monster.db.population_key = "wilderness:203:30"
        ensure_population(self.script, (203, 30))
        remaining = [
            obj for obj in self._monsters_at((203, 30)) if isinstance(obj, Monster)
        ]
        self.assertEqual(remaining, [])

    @covers_requirement("wilderness-monster-population::ensure-population-idempotently-places-and-respawns-monsters-at-a-coordinate")
    def test_foreign_monster_at_coordinate_is_never_reconciled(self):
        foreign = self._spawn_foreign_monster((60, 100), key="scripted-encounter")
        foreign.traits.hp.current = 7
        ensure_population(self.script, (60, 100))
        monsters = [
            obj for obj in self._monsters_at((60, 100)) if isinstance(obj, Monster)
        ]
        self.assertIn(foreign, monsters)
        self.assertEqual(foreign.traits.hp.current, 7)
        self.assertIsNone(foreign.db.population_key)

    @covers_requirement("wilderness-monster-population::ensure-population-idempotently-places-and-respawns-monsters-at-a-coordinate")
    def test_surplus_dead_matching_monster_is_cleaned_to_exactly_one(self):
        # The populated coordinate already holds its living population monster.
        original = [
            obj for obj in self._monsters_at((60, 100)) if isinstance(obj, Monster)
        ][0]
        self.assertGreater(original.traits.hp.current, 0)
        # Add a dead matching monster; reconciliation must drop it so exactly
        # one living matching monster remains (dead extras are not idempotent).
        dead = self._spawn_foreign_monster((60, 100), key="dead-duplicate")
        dead.db.population_key = "wilderness:60:100"
        dead.traits.hp.current = 0
        ensure_population(self.script, (60, 100))
        monsters = [
            obj for obj in self._monsters_at((60, 100)) if isinstance(obj, Monster)
        ]
        matching = [obj for obj in monsters if obj.db.population_key == "wilderness:60:100"]
        self.assertEqual(len(matching), 1)
        self.assertGreater(matching[0].traits.hp.current, 0)

    @covers_requirement("wilderness-monster-population::ensure-population-idempotently-places-and-respawns-monsters-at-a-coordinate")
    def test_stale_model_drift_is_reconciled_to_current_model(self):
        # A living matching monster whose tier no longer matches the model (a
        # model/registry fix after spawn) must be replaced, not kept stale.
        stale = self._spawn_foreign_monster((60, 100), key="drifted")
        stale.db.population_key = "wilderness:60:100"
        stale.threat_tier = "high"
        stale.apply_monster_tier("floor")
        ensure_population(self.script, (60, 100))
        monsters = [
            obj for obj in self._monsters_at((60, 100)) if isinstance(obj, Monster)
        ]
        matching = [obj for obj in monsters if obj.db.population_key == "wilderness:60:100"]
        self.assertEqual(len(matching), 1)
        self.assertNotEqual(matching[0].pk, stale.pk)
        self.assertEqual(matching[0].threat_tier, "low")
        self.assertEqual(matching[0].key, "哥布林")

    @covers_requirement("wilderness-monster-population::a-registered-wilderness-monster-survives-room-recycling")
    def test_registered_monster_survives_room_recycling(self):
        monsters = [
            obj for obj in self._monsters_at((60, 100)) if isinstance(obj, Monster)
        ]
        self.assertEqual(len(monsters), 1)
        monster = monsters[0]
        self.assertIs(monster.location, self.room)

        # Step east: the contrib vacates and recycles the (60, 100) room (the
        # only account has left and preserve_items is False). The monster stays
        # registered in itemcoordinates with its location cleared, not deleted.
        east = [exit_obj for exit_obj in self.room.exits if exit_obj.key == "east"][0]
        east.at_traverse(self.char1, self.room)
        monster.refresh_from_db()
        self.assertIsNone(monster.location)
        self.assertEqual(self.script.db.itemcoordinates[monster], (60, 100))

        # Step back west: a room is activated again at (60, 100) and the
        # contrib re-attaches the registered monster to it.
        west_room = self.char1.location
        west = [exit_obj for exit_obj in west_room.exits if exit_obj.key == "west"][0]
        west.at_traverse(self.char1, west_room)
        reattached = [
            obj for obj in self._monsters_at((60, 100)) if isinstance(obj, Monster)
        ]
        self.assertEqual(len(reattached), 1)
        self.assertEqual(reattached[0].pk, monster.pk)
        self.assertIs(reattached[0].location, self.char1.location)

    @covers_requirement("wilderness-monster-population::a-registered-wilderness-monster-survives-room-recycling")
    def test_sync_wilderness_rerun_does_not_duplicate_or_replace(self):
        from world.maps.bootstrap import sync_wilderness

        monsters = [
            obj for obj in self._monsters_at((60, 100)) if isinstance(obj, Monster)
        ]
        self.assertEqual(len(monsters), 1)
        original = monsters[0]

        # The startup sync path re-runs at_prepare_room for retained rooms; the
        # living population monster must survive unchanged.
        sync_wilderness()
        monsters = [
            obj for obj in self._monsters_at((60, 100)) if isinstance(obj, Monster)
        ]
        self.assertEqual(len(monsters), 1)
        self.assertEqual(monsters[0].pk, original.pk)
        self.assertIs(monsters[0].location, original.location)


class OnboardingHuntIntegrationTests(BattlefieldIsolation, RegistryIsolationMixin, EvenniaCommandTestMixin, EvenniaTest):
    """End-to-end onboarding hunt: register, accept, walk out the North Gate,
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
        sync_grid()
        sync_wilderness()
        register_catalog()
        sync_quest_runtime()
        sync_guild_economy()
        self.north_gate = GridRoom.objects.filter_xyz(xyz=NORTH_GATE_XYZ).first()
        self.gate = [e for e in self.north_gate.exits if isinstance(e, WildernessGateExit)][0]
        self.guild_hall = search_object_by_tag(GUILD_HALL_TAG)[0]
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

        # Walk to the North Gate and through it into the wilderness.
        self.player.location = self.north_gate
        self.gate.at_traverse(self.player, self.north_gate)
        self.assertIsInstance(self.player.location, TerrainRoom)
        self.assertEqual(self.player.location.coordinates, (60, 100))

        # A living low-tier population monster is present at the entry.
        from evennia.contrib.grid.wilderness.wilderness import WildernessScript

        script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        monsters = [
            obj for obj in script.get_objs_at_coordinates((60, 100)) if isinstance(obj, Monster)
        ]
        self.assertEqual(len(monsters), 1)
        monster = monsters[0]
        self.assertEqual(monster.threat_tier, "low")
        self.assertEqual(monster.db.population_key, "wilderness:60:100")
        self.assertGreater(monster.traits.hp.current, 0)

        # Decisive deterministic combat: a boosted adventurer lands a critical
        # basic_attack (roll patched to 100) that defeats the monster.
        for key in ("atk_phys", "agility", "defense"):
            getattr(self.player.traits, key).base = 60
        self.player.traits.hp.base = 500
        self.player.traits.hp.current = 500
        self.call(CmdEngage(), monster.key, "戰鬥開始")
        self.assertIsNotNone(self.player.db.active_combat)
        with patch("world.rules.combat.roll_d100", return_value=100):
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
        enter_wilderness(self.char1, coordinates=(60, 100), name=WILDERNESS_NAME)
        self.room = self.char1.location
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.monster = next(
            obj
            for obj in self.script.get_objs_at_coordinates((60, 100))
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
        sync_wilderness()
        surviving = [
            obj
            for obj in self.script.get_objs_at_coordinates((60, 100))
            if isinstance(obj, Monster)
        ]
        self.assertEqual([obj.pk for obj in surviving], [self.monster.pk])
        self.assertEqual(self.monster.traits.hp.current, 0)

        # Session restoration settles the committed victory, not a defeat.
        settled: dict[str, str] = {}

        def spy(actor, record, battlefield, outcome, logs=()):
            settled["outcome"] = outcome
            return settle_session(actor, record, battlefield, outcome, logs)

        with patch("world.rules.combat_session.settle_session", side_effect=spy):
            restore_persisted_sessions()
        self.assertEqual(settled["outcome"], "victory")
        self.assertIsNone(self.player.db.active_combat)

        # Only afterwards does reconciliation respawn the defeated monster.
        sync_wilderness()
        respawned = [
            obj
            for obj in self.script.get_objs_at_coordinates((60, 100))
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
        ensure_population(self.script, (60, 100))
        respawned = [
            obj
            for obj in self.script.get_objs_at_coordinates((60, 100))
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
        ensure_population(self.script, (61, 100))
        other = next(
            obj
            for obj in self.script.get_objs_at_coordinates((61, 100))
            if isinstance(obj, Monster)
        )
        other.traits.hp.current = 0
        ensure_population(self.script, (61, 100))
        respawned = [
            obj
            for obj in self.script.get_objs_at_coordinates((61, 100))
            if isinstance(obj, Monster)
        ]
        self.assertEqual(len(respawned), 1)
        self.assertNotEqual(respawned[0].pk, other.pk)
        self.assertGreater(respawned[0].traits.hp.current, 0)