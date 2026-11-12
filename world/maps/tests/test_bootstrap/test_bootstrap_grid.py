"""Data-contract test: map bootstrap/gate data contract
Integration tests for idempotent grid and wilderness bootstrap (map-anchor-grid, map-wilderness)."""

from tools.spec_traceability import covers_requirement

import inspect
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.search import search_object
from evennia.utils.test_resources import EvenniaTest

from server.conf.at_server_startstop import at_server_start
from typeclasses.exits import Exit, WildernessGateExit
from typeclasses.rooms import AnchorRoom, GridRoom, Room
from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
from world.quests.tests._fixtures import RegistryIsolationMixin
from world.maps.city_gates import CITY_GATE_REGISTRY, CityGateDef
from world.maps.bootstrap import SyncReport, sync_grid, sync_limbo, sync_wilderness
from world.maps.limbo import LIMBO_ALIAS, LIMBO_DESC, LIMBO_KEY, LIMBO_LEGACY_KEY
from world.maps.map_data import SETTLEMENT_GRAPHS
from world.maps.static_references import (
    StaticReferenceError,
    anchor_entrance_xyz,
    place_exterior_xyz,
    settlement_node_xyz,
)
from elosern_map_core.references import settlement_node_ref
from world.maps.wilderness_provider import WILDERNESS_NAME
from world.rules.tests.combat_fixtures import BattlefieldIsolation
from world.tests.geography_fixture import (
    publish_shipped_geography,
    selected_startup_settlements,
    sync_test_settlements,
    sync_test_wilderness,
)
from world.maps.tests._bootstrap_fixtures import (
    ANCHOR_PLACEMENT_MAP_IDS,
    CAPITAL_MAP_IDS,
    CAPITAL_VILLAGE_MAP_IDS,
    CITY_GATE_MAP_IDS,
    EAST_GATE_XYZ,
    SELECTED_GATE_ROW_COUNT,
    SOUTH_GATE_XYZ,
    VILLAGE_MAP_IDS,
    WILDERNESS_GATE_MAP_IDS,
    _GridBootstrapCase,
    _WildernessBootstrapCase,
    _approach,
    _declared_node_count,
    _declared_road_count,
)


class GridBootstrapTests(_GridBootstrapCase):
    """Spawn, update and first-pass convergence cases."""

    @covers_requirement("sample-city-altoria::the-sample-city-has-the-declared-rooms-in-a-connected-sparse-topology")
    @covers_requirement("grid-room-sync::a-single-authored-idempotent-exit-bridges-limbo-and-the-sample-city")
    def test_sync_grid_spawns_both_settlements_rooms_and_exits(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CAPITAL_VILLAGE_MAP_IDS)

        # The declared pair's authored topology, with no unrelated graph work.
        self.assertEqual(
            self._count_grid_rooms(), _declared_node_count(CAPITAL_VILLAGE_MAP_IDS)
        )
        self.assertEqual(
            self._count_city_exits(), _declared_road_count(CAPITAL_VILLAGE_MAP_IDS)
        )
        # One forward Limbo bridge per CITY_GATE_REGISTRY row.
        self.assertEqual(len(self._bridging_exits()), 2)
        self.assertEqual(
            len(self._bridging_exits()) + self._count_city_exits(),
            _declared_road_count(CAPITAL_VILLAGE_MAP_IDS) + SELECTED_GATE_ROW_COUNT,
        )

    def test_sync_grid_is_idempotent_and_preserves_dbid(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CAPITAL_VILLAGE_MAP_IDS)
        first_ids = {
            room.xyz: room.id
            for room in GridRoom.objects.all_family()
        }

        sync_test_settlements(CAPITAL_VILLAGE_MAP_IDS)
        second_ids = {
            room.xyz: room.id
            for room in GridRoom.objects.all_family()
        }

        self.assertEqual(
            self._count_grid_rooms(), _declared_node_count(CAPITAL_VILLAGE_MAP_IDS)
        )
        self.assertEqual(
            self._count_city_exits(), _declared_road_count(CAPITAL_VILLAGE_MAP_IDS)
        )
        self.assertEqual(len(self._bridging_exits()), 2)
        self.assertEqual(first_ids, second_ids)

    def test_single_call_on_fresh_grid_spawns_every_declared_room(self):
        from evennia.contrib.grid.xyzgrid.xyzgrid import XYZGrid

        self.assertEqual(XYZGrid.objects.all().count(), 0)
        sync_test_settlements(CAPITAL_VILLAGE_MAP_IDS)
        self.assertEqual(
            self._count_grid_rooms(), _declared_node_count(CAPITAL_VILLAGE_MAP_IDS)
        )

    def test_in_place_update_changes_desc_without_new_room(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CAPITAL_MAP_IDS)

        # zhtw-room-prose: the spawn pin asserts the mechanism (the room's desc
        # equals its authored prototype), not the sentence — the prototype's
        # prose is Traditional Chinese like every other shipped room text.
        from world.maps.map_data import current

        declared = current().settlements["capital_altoria"].nodes["south_gate"]
        # A node key is unique inside one map, never across the settled world:
        # several settlements have their own 南門. Resolve the room by the
        # authored coordinate that identifies it.
        xyz = (*declared.coordinate, "capital_altoria")
        south_gate = GridRoom.objects.filter_xyz(xyz=xyz).first()
        self.assertIsNotNone(south_gate)
        self.assertEqual(south_gate.xyz, (*declared.coordinate, "capital_altoria"))
        self.assertEqual(south_gate.db.desc, declared.desc)

        from dataclasses import replace

        from elosern_map_core.sparse import SparseSettlementGraph

        capital = SETTLEMENT_GRAPHS["capital_altoria"]
        nodes = [
            replace(
                node,
                prototype={**node.prototype, "desc": "A rebuilt southern gate."},
            )
            if node.node_id == "south_gate"
            else node
            for node in capital.nodes.values()
        ]
        changed_graph = SparseSettlementGraph(
            capital.map_id,
            nodes,
            capital.roads,
            options=capital.options,
            exit_prototype=capital.exit_prototype,
        )
        changed = dict(SETTLEMENT_GRAPHS)
        changed["capital_altoria"] = changed_graph
        with patch("world.maps.bootstrap.SETTLEMENT_GRAPHS", changed):
            sync_test_settlements(CAPITAL_MAP_IDS)

        self.assertEqual(self._count_grid_rooms(), _declared_node_count(CAPITAL_MAP_IDS))
        south_gate = GridRoom.objects.filter_xyz(xyz=xyz).first()
        self.assertIsNotNone(south_gate)
        self.assertEqual(south_gate.db.desc, "A rebuilt southern gate.")


class GridBootstrapStartupTests(_GridBootstrapCase):
    """The real startup step converges lore and grid in the authored order."""

    @covers_requirement("grid-room-sync::sync-grid-runs-automatically-at-server-start-after-sync-all")
    @covers_requirement("grid-room-sync::the-evennia-xyzgrid-cli-remains-available-but-is-not-required-for-boot", "lore-startup-sync::sync-runs-automatically-at-evennia-server-start")
    def test_at_server_start_calls_sync_grid_after_sync_all(self):
        from server.conf.at_server_startstop import STARTUP_STEP_ORDER

        # The map world (starting room, grid, interiors) converges in the one
        # map-sync step; the lore mirror runs only after it committed.
        self.assertLess(
            STARTUP_STEP_ORDER.index("sync_map_world"),
            STARTUP_STEP_ORDER.index("sync_all"),
        )

    def test_at_server_start_without_limbo_syncs_lore_and_grid(self):
        with selected_startup_settlements(
            CAPITAL_VILLAGE_MAP_IDS,
            # These contracts cover the grid, the bridges and the lore mirror;
            # the ambient monster population is not part of them.
            zone_keys=(),
        ):
            at_server_start()

        self.assertEqual(
            self._count_grid_rooms(), _declared_node_count(CAPITAL_VILLAGE_MAP_IDS)
        )
        self.assertEqual(
            self._count_city_exits(), _declared_road_count(CAPITAL_VILLAGE_MAP_IDS)
        )
        self.assertEqual(len(self._bridging_exits()), 0)
        from evennia.utils.search import search_script

        self.assertEqual(len(search_script("lore:anchor_placements:capital_altoria")), 1)

    def test_at_server_start_with_limbo_creates_bridging_exits(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        with selected_startup_settlements(
            CAPITAL_VILLAGE_MAP_IDS,
            # These contracts cover the grid, the bridges and the lore mirror;
            # the ambient monster population is not part of them.
            zone_keys=(),
        ):
            at_server_start()

        self.assertEqual(
            self._count_grid_rooms(), _declared_node_count(CAPITAL_VILLAGE_MAP_IDS)
        )
        self.assertEqual(
            self._count_city_exits(), _declared_road_count(CAPITAL_VILLAGE_MAP_IDS)
        )
        self.assertEqual(len(self._bridging_exits()), SELECTED_GATE_ROW_COUNT)


class WildernessBootstrapTests(_WildernessBootstrapCase):
    """Localized gate, approach and startup cases."""

    @covers_requirement("wilderness-map-provider::the-continent-remains-virtual-with-bounded-local-lookup")
    def test_sync_wilderness_materializes_no_frame_rooms(self):
        # The 2700x2700 frame is virtual: boot creates the script and the
        # registered gate exits, never a room per cell.
        from typeclasses.rooms import TerrainRoom

        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CAPITAL_MAP_IDS)
        sync_test_wilderness(CAPITAL_MAP_IDS)

        script, _ = self._gate_exits()
        self.assertEqual(TerrainRoom.objects.count(), 0)
        self.assertEqual(dict(script.db.rooms), {})

    @covers_requirement("wilderness-gateway::physical-footprints-and-concealed-point-entries-preserve-approaches")
    def test_gate_approach_segments_follow_the_authored_physical_geometry(self):
        # The south and east gates measure their own exterior approach segment
        # from the transformed metre position to the approach cell centre; the
        # crossing is one segment, not a full wilderness cell plus a city hop.
        from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
        from world.maps.wilderness_destination import gate_approach_distance_m

        import math

        from elosern_map_core.authoring import gate_approach_cell

        from world.maps import geography
        from world.maps.map_data import current

        entry = WILDERNESS_ENTRY_REGISTRY["capital_altoria"]
        document = current().settlements[entry.anchor_key]
        cell = geography.current().locations.locations[document.location_ref].cell
        anchor_x, anchor_y = document.local_anchor_m

        def authored_segment(return_direction):
            gate = entry.gate_for(return_direction)
            gate_x, gate_y = document.nodes[gate.destination.object_id].coordinate
            gate_world = (
                1000 * cell[0] + 500 + gate_x - anchor_x,
                1000 * cell[1] + 500 + gate_y - anchor_y,
            )
            approach = gate_approach_cell(
                document.wilderness_geometry(cell), return_direction
            )
            return math.dist(
                gate_world, (1000 * approach[0] + 500, 1000 * approach[1] + 500)
            )

        south = gate_approach_distance_m(entry, entry.gate_for("n"))
        east = gate_approach_distance_m(entry, entry.gate_for("w"))
        self.assertAlmostEqual(south, authored_segment("n"))
        self.assertAlmostEqual(east, authored_segment("w"))
        self.assertNotEqual(south, east)
        # Both directions of a crossing measure the single authored segment.
        self.assertEqual(
            gate_approach_distance_m(entry, entry.gate_for("n")), south
        )

    @covers_requirement("wilderness-gateway::physical-footprints-and-concealed-point-entries-preserve-approaches")
    def test_village_point_entrance_has_no_wilderness_footprint(self):
        from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
        from world.maps.wilderness_provider import WILDERNESS_NAME as NAME

        village = WILDERNESS_ENTRY_REGISTRY["village_ciaran"]
        self.assertTrue(village.is_point_shape)
        self.assertEqual(village.footprint_cells, frozenset())
        # The anchor cell itself is walkable ground; the point entry is not a
        # village-wide obstacle (only a registered gateway consumes the step).
        from evennia.contrib.grid.wilderness.wilderness import (
            create_wilderness,
            enter_wilderness,
        )

        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(VILLAGE_MAP_IDS)
        sync_test_wilderness(VILLAGE_MAP_IDS)
        provider = __import__(
            "world.maps.wilderness_provider", fromlist=["ElosernWildernessMapProvider"]
        ).ElosernWildernessMapProvider()
        create_wilderness(name=NAME, mapprovider=provider)
        self.assertTrue(
            enter_wilderness(self.char1, coordinates=village.anchor_cell, name=NAME)
        )

    def test_sync_wilderness_without_east_gate_degrades_gracefully(self):
        sync_test_wilderness(CAPITAL_VILLAGE_MAP_IDS)

        from evennia.contrib.grid.wilderness.wilderness import WildernessScript

        scripts = WildernessScript.objects.filter(db_key=WILDERNESS_NAME)
        self.assertEqual(len(scripts), 1)
        self.assertEqual(WildernessGateExit.objects.all().count(), 0)

    @covers_requirement(
        "regional-population::shared-population-seed-and-explicit-registrations-are-owner-supplied"
    )
    @covers_requirement(
        "wilderness-monster-population::runtime-population-uses-authored-regions-without-implicit-fallback"
    )
    def test_fresh_wilderness_provisioning_initializes_population_once(self):
        from evennia.contrib.grid.wilderness.wilderness import WildernessScript
        from typeclasses.monsters import Monster

        from world.lore.monster_placement import ECOLOGY_ZONE_REGISTRY
        from world.maps.regional_population import (
            INITIAL_POPULATION_SEED,
            initialized_zone_keys,
            read_population_seed,
        )
        from world.maps.bootstrap import sync_wilderness

        # "Every authored zone" is the production entry point's claim; a test
        # declaration bounds its world and is covered separately.
        sync_wilderness(settlement_ids=CAPITAL_VILLAGE_MAP_IDS)
        script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        # A genuinely new script is seeded and every authored zone is
        # initialized before any reader or boundary can observe it.
        self.assertEqual(read_population_seed(script), INITIAL_POPULATION_SEED)
        self.assertEqual(
            initialized_zone_keys(script), tuple(sorted(ECOLOGY_ZONE_REGISTRY))
        )
        living = {
            obj.pk: obj.traits.hp.current
            for obj in script.db.itemcoordinates
            if isinstance(obj, Monster)
        }
        self.assertTrue(living)

        # A rerun never reseeds, rerolls, refills or replaces a living ID.
        sync_wilderness(settlement_ids=CAPITAL_VILLAGE_MAP_IDS)
        self.assertEqual(read_population_seed(script), INITIAL_POPULATION_SEED)
        self.assertEqual(
            {
                obj.pk: obj.traits.hp.current
                for obj in script.db.itemcoordinates
                if isinstance(obj, Monster)
            },
            living,
        )

    def test_a_bounded_declaration_records_and_verifies_its_own_zone_scope(self):
        from evennia.contrib.grid.wilderness.wilderness import WildernessScript

        from world.lore.monster_placement import ECOLOGY_ZONE_REGISTRY
        from world.maps.bootstrap import sync_wilderness
        from world.maps.regional_population import (
            POPULATION_ZONE_SCOPE_ATTRIBUTE,
            PopulationStateUninitialized,
            initialized_zone_keys,
            read_population_zone_scope,
            require_initialized_population,
        )

        scope = (sorted(ECOLOGY_ZONE_REGISTRY)[0],)
        sync_wilderness(settlement_ids=CAPITAL_VILLAGE_MAP_IDS, zone_keys=scope)
        script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        self.assertEqual(read_population_zone_scope(script), scope)
        self.assertEqual(initialized_zone_keys(script), scope)
        self.assertEqual(
            tuple(script.attributes.get(POPULATION_ZONE_SCOPE_ATTRIBUTE)), scope
        )
        # A later boot verifies the scope this world recorded, so the bounded
        # world is complete and any record outside it is the named refusal.
        require_initialized_population(script)
        outside = sorted(set(ECOLOGY_ZONE_REGISTRY) - set(scope))[0]
        states = dict(script.db.regional_population)
        states[outside] = dict(states[scope[0]])
        script.db.regional_population = states
        with self.assertRaises(PopulationStateUninitialized):
            require_initialized_population(script)

    @covers_requirement(
        "wilderness-monster-population::runtime-population-uses-authored-regions-without-implicit-fallback"
    )
    def test_preexisting_world_without_population_state_refuses(self):
        from evennia.contrib.grid.wilderness.wilderness import WildernessScript

        from world.lore.monster_placement import ECOLOGY_ZONE_REGISTRY
        from world.maps.regional_population import (
            POPULATION_SEED_ATTRIBUTE,
            PopulationStateUninitialized,
            REGIONAL_POPULATION_ATTRIBUTE,
        )

        sync_test_wilderness(CAPITAL_VILLAGE_MAP_IDS)
        script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        self.assertTrue(ECOLOGY_ZONE_REGISTRY)

        # Missing seed: the named operator refusal, never an implicit reset.
        saved_seed = script.attributes.get(POPULATION_SEED_ATTRIBUTE)
        script.attributes.remove(POPULATION_SEED_ATTRIBUTE)
        with self.assertRaises(PopulationStateUninitialized):
            sync_test_wilderness(CAPITAL_VILLAGE_MAP_IDS)
        script.attributes.add(POPULATION_SEED_ATTRIBUTE, saved_seed)

        # Missing zone state: the same refusal, and the surviving state is
        # neither filled in nor converted.
        saved_zones = dict(script.db.regional_population)
        partial = dict(saved_zones)
        partial.pop(sorted(partial)[0])
        script.db.regional_population = partial
        with self.assertRaises(PopulationStateUninitialized):
            sync_test_wilderness(CAPITAL_VILLAGE_MAP_IDS)
        self.assertEqual(dict(script.db.regional_population), partial)
        self.assertIsNotNone(script.attributes.get(REGIONAL_POPULATION_ATTRIBUTE))
        script.db.regional_population = saved_zones

        # A malformed saved seed and a missing timeline are the same refusal.
        saved_seed = script.attributes.get(POPULATION_SEED_ATTRIBUTE)
        script.attributes.add(POPULATION_SEED_ATTRIBUTE, "not-an-integer")
        with self.assertRaises(PopulationStateUninitialized):
            sync_test_wilderness(CAPITAL_VILLAGE_MAP_IDS)
        script.attributes.add(POPULATION_SEED_ATTRIBUTE, saved_seed)
        from world.maps.regional_population import POPULATION_TIMELINE_ATTRIBUTE

        saved_timeline = script.attributes.get(POPULATION_TIMELINE_ATTRIBUTE)
        script.attributes.remove(POPULATION_TIMELINE_ATTRIBUTE)
        with self.assertRaises(PopulationStateUninitialized):
            sync_test_wilderness(CAPITAL_VILLAGE_MAP_IDS)
        script.attributes.add(POPULATION_TIMELINE_ATTRIBUTE, saved_timeline)

    def test_startup_preflight_refuses_before_restoration(self):
        from server.conf.at_server_startstop import (
            STARTUP_STEP_ORDER,
            _verify_population_state,
        )

        self.assertLess(
            STARTUP_STEP_ORDER.index("verify_population_state"),
            STARTUP_STEP_ORDER.index("restore_persisted_sessions"),
        )
        sync_test_wilderness(CAPITAL_VILLAGE_MAP_IDS)
        from evennia.contrib.grid.wilderness.wilderness import WildernessScript

        from world.maps.regional_population import PopulationStateUninitialized

        script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        states = dict(script.db.regional_population)
        states.pop(sorted(states)[0])
        script.db.regional_population = states
        with self.assertRaises(PopulationStateUninitialized):
            _verify_population_state()

    def test_a_later_zone_failure_rolls_back_the_fresh_provisioning(self):
        from evennia.contrib.grid.wilderness.wilderness import WildernessScript
        from typeclasses.monsters import Monster

        from world.maps import bootstrap
        from world.maps import regional_population

        # Provisioning initializes the whole roster in one pass, so the
        # failure is injected at the wave commit of the SECOND zone: the first
        # zone has already created individuals by then, which is what the
        # rollback assertions prove are gone.
        real_commit = regional_population._commit_planned_wave
        committed_zones: list[str] = []

        def commit_until_the_second_zone(wilderness, plan, **kwargs):
            if plan.zone_key not in committed_zones:
                committed_zones.append(plan.zone_key)
                if len(committed_zones) == 2:
                    raise RuntimeError("injected later-zone failure")
            return real_commit(wilderness, plan, **kwargs)

        with patch.object(
            regional_population,
            "_commit_planned_wave",
            commit_until_the_second_zone,
        ):
            with self.assertRaises(RuntimeError):
                bootstrap._provision_wilderness_script()

        self.assertEqual(len(committed_zones), 2)
        self.assertNotEqual(committed_zones[0], committed_zones[1])
        self.assertFalse(WildernessScript.objects.filter(db_key=WILDERNESS_NAME).exists())
        self.assertEqual(Monster.objects.count(), 0)

    def test_sync_grid_body_is_unmodified(self):
        source = inspect.getsource(sync_grid)
        # The sparse synchronizer is the spawn path; the xyzgrid contrib's
        # dense ``reload()``/``spawn()`` pipeline must not come back.
        self.assertIn("_apply_graph_plan(plan, knowledge_journal)", source)
        self.assertNotIn("grid.spawn()", source)
        self.assertNotIn("get_xyzgrid()", source)
        self.assertNotIn("sync_wilderness", source)

    @covers_requirement("wilderness-gateway::sync-wilderness-idempotently-provisions-the-wilderness-map-and-one-grid-side-gate-per-registered-gate")
    def test_at_server_start_calls_sync_wilderness_after_sync_grid(self):
        from server.conf.at_server_startstop import STARTUP_STEP_ORDER

        self.assertLess(
            STARTUP_STEP_ORDER.index("sync_map_world"),
            STARTUP_STEP_ORDER.index("sync_wilderness"),
        )

    def test_at_server_start_provisions_wilderness_too(self):
        with selected_startup_settlements(
            CAPITAL_VILLAGE_MAP_IDS,
            # The wilderness map and its gate exits are this contract; the
            # ambient monster population is covered by its own owner tests.
            zone_keys=(),
        ):
            at_server_start()

        self.assertEqual(
            self._count_grid_rooms(), _declared_node_count(CAPITAL_VILLAGE_MAP_IDS)
        )
        from evennia.contrib.grid.wilderness.wilderness import WildernessScript

        scripts = WildernessScript.objects.filter(db_key=WILDERNESS_NAME)
        self.assertEqual(len(scripts), 1)
        gates = self._gate_exits()[1]
        self.assertEqual(len(gates), 1)

    @covers_requirement("wilderness-gateway::sync-wilderness-idempotently-provisions-the-wilderness-map-and-one-grid-side-gate-per-registered-gate")
    def test_village_gate_roundtrips_to_the_entrance_node(self):
        # A traveler on 隱密小徑 steps into the wilderness at the village's
        # approach cell, and a traveler standing there and moving in the
        # gate's return direction ("n") arrives back at 隱密小徑 (task 3.3).
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(VILLAGE_MAP_IDS)
        sync_test_wilderness(VILLAGE_MAP_IDS)

        entrance_room = GridRoom.objects.filter_xyz(
            xyz=(
                *settlement_node_xyz(
                    WILDERNESS_ENTRY_REGISTRY["village_ciaran"].gate_for("n").destination
                ),
            )
        ).first()
        gate_exit = [
            e for e in entrance_room.exits if isinstance(e, WildernessGateExit)
        ][0]

        gate_exit.at_traverse(self.char1, entrance_room)
        self.assertEqual(self.char1.location.coordinates, (1366, 554))

        north = [e for e in self.char1.location.exits if e.key == "north"][0]
        north.at_traverse(self.char1, self.char1.location)
        self.assertIs(self.char1.location, entrance_room)

    def test_sync_wilderness_restores_retained_room_descriptions(self):
        # Simulate a server restart: provision the wilderness, walk in to
        # create a retained room, wipe its non-persistent description (as a
        # restart does -- ndb values are not stored), then re-run
        # sync_wilderness() and confirm the deterministic description returns.
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CAPITAL_MAP_IDS)
        sync_test_wilderness(CAPITAL_MAP_IDS)
        from evennia.contrib.grid.wilderness.wilderness import (  # noqa: F811
            WildernessScript,
            enter_wilderness,
        )

        from world.maps.room_art import wilderness_scene_identity
        from world.lore.wilderness_regions import regions
        from world.maps.wilderness_provider import (
            region_for_coordinates,
            terrain_description,
        )

        script = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        x, y = _approach("w")
        ok = enter_wilderness(self.char1, coordinates=(x, y), name=WILDERNESS_NAME)
        self.assertTrue(ok)
        room = self.char1.location
        self.assertEqual(room.ndb.active_desc, terrain_description(x, y))
        room.ndb.active_desc = None  # wipe like a restart would
        room.ndb.someother = 1
        # The returned room is retained (account still present); re-running
        # sync_wilderness must re-prepare it.
        sync_test_wilderness(CAPITAL_MAP_IDS)
        self.assertEqual(room.ndb.active_desc, terrain_description(x, y))
        self.assertEqual(
            room.scene_archetype,
            regions()[region_for_coordinates(x, y)].scene_archetype,
        )
        self.assertEqual(
            room.scene_identity,
            wilderness_scene_identity(WILDERNESS_NAME, x, y),
        )

    def test_sync_wilderness_heals_miskeyed_gate(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CAPITAL_MAP_IDS)
        sync_test_wilderness(CAPITAL_MAP_IDS)
        # Misconfigure the gate's anchor_key, then re-run and confirm it heals.
        script, gates = self._gate_exits()
        self.assertEqual(len(gates), 1)
        gate = gates[0]
        gate.db.anchor_key = "wrong_anchor"
        sync_test_wilderness(CAPITAL_MAP_IDS)
        script, gates = self._gate_exits()
        self.assertEqual(len(gates), 1)
        self.assertEqual(gates[0].db.anchor_key, "capital_altoria")
        self.assertEqual(gates[0].db.gate_direction, "w")

    def test_sync_wilderness_heals_misdirected_gate(self):
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CAPITAL_MAP_IDS)
        sync_test_wilderness(CAPITAL_MAP_IDS)
        gate = self._gate_exits()[1][0]
        gate.db.gate_direction = "e"
        sync_test_wilderness(CAPITAL_MAP_IDS)
        gates = self._gate_exits()[1]
        self.assertEqual(len(gates), 1)
        self.assertEqual(gates[0].db.gate_direction, "w")

    def test_sync_wilderness_heals_a_misattributed_single_gate_exit(self):
        # A lone WildernessGateExit with foreign attrs on a gate room IS that
        # room's gate slot: sync heals its (anchor, gate) pair in place rather
        # than stacking a second gate (spec scenario "a mis-provisioned gate
        # is healed").
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CAPITAL_MAP_IDS)
        foreign = create_object(
            WildernessGateExit,
            key="荒野",
            location=self._south_gate(),
            destination=self._south_gate(),
        )
        foreign.db.anchor_key = "wrong_anchor"
        foreign.db.gate_direction = "w"
        sync_test_wilderness(CAPITAL_MAP_IDS)
        south_gates = self._gate_exits(self._south_gate())[1]
        self.assertEqual(len(south_gates), 1)
        self.assertIs(south_gates[0], foreign)
        self.assertEqual(foreign.db.anchor_key, "capital_altoria")
        self.assertEqual(foreign.db.gate_direction, "n")

    def test_sync_wilderness_skips_an_ambiguous_multi_row_gate_room(self):
        # Two WildernessGateExit rows on one room are ambiguous: sync warns and
        # provisions nothing there, but still heals/provisions the other gate.
        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CAPITAL_MAP_IDS)
        south_gate = self._south_gate()
        create_object(WildernessGateExit, key="荒野", location=south_gate, destination=south_gate)
        create_object(WildernessGateExit, key="荒野二", location=south_gate, destination=south_gate)
        sync_test_wilderness(CAPITAL_MAP_IDS)
        self.assertEqual(len(self._gate_exits(south_gate)[1]), 2)
        # The unaffected east gate provisions to exactly one exit.
        self.assertEqual(len(self._gate_exits()[1]), 1)

    def test_sync_wilderness_leaves_same_key_foreign_exit_alone(self):
        from typeclasses.exits import Exit

        create_object(Room, key=LIMBO_KEY, location=None)
        sync_test_settlements(CAPITAL_MAP_IDS)
        sync_test_wilderness(CAPITAL_MAP_IDS)
        # Plant a plain Exit that occupies the gate key.
        east_gate = self._east_gate()
        create_object(
            Exit,
            key="荒野",
            location=east_gate,
            destination=east_gate,
        )
        sync_test_wilderness(CAPITAL_MAP_IDS)
        script, gates = self._gate_exits()
        self.assertEqual(len(gates), 1)
        self.assertEqual(gates[0].db.anchor_key, "capital_altoria")
        # The foreign exit is untouched (not replaced, not duplicated), and the
        # gate count stays at exactly one WildernessGateExit.
        foreign = [e for e in east_gate.exits if isinstance(e, Exit) and not isinstance(e, WildernessGateExit)]
        self.assertEqual(len(foreign), 1)
        self.assertEqual(foreign[0].key, "荒野")


