"""Mechanism tests for qualified static map references (P03).

Static declarations hold identities; the game boundary derives the current
coordinate, wire id and room form. These tests use synthetic declarations and
a synthetic settlement graph, never shipped geography or copy.
"""

from __future__ import annotations

import unittest
from contextlib import ExitStack
from unittest import mock

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from elosern_map_core.references import (
    DUPLICATE_REFERENCE,
    UNKNOWN_REFERENCE,
    WRONG_DOMAIN,
    ReferenceError,
    ReferenceIndex,
    interior_room_ref,
    location_ref,
    resolve_reference,
    settlement_node_ref,
    wilderness_cell_ref,
)
from elosern_map_core.sparse import SparseGraphError, build_sparse_graph
from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.exits import Exit
from typeclasses.rooms import GridRoom, Room

from elosern_map_core.documents import DistrictDeclaration
from world.lore.map_districts import landmark_node_id, landmark_node_ids
from world.lore.settlements.places import PlaceDefinition, PlaceKind
from world.maps import map_data
from world.maps.bootstrap import (
    sync_grid,
    sync_interiors,
    sync_settlement_graph,
)
from world.maps.city_gates import CityGateDef
from world.maps.limbo import LIMBO_KEY
from world.maps.room_art import grid_scene_identity
from world.maps.static_references import (
    StaticReferenceError,
    binding_signature,
    place_exterior_xyz,
    settlement_node_xyz,
    validate_static_references,
)
from world.rules.map_district_lighting import lit_district_keys
from world.rules.map_knowledge import KNOWLEDGE_ATTR, encode_grid, parse_knowledge
from world.tests.geography_fixture import publish_shipped_geography


def setUpModule():
    publish_shipped_geography()

MAP = "t_ref_map"


def _prototype(key):
    return {
        "prototype_parent": "grid_room",
        "key": key,
        "desc": f"synthetic {key}",
    }


def _graph(x=10, y=10):
    """Two authored nodes whose identities never change across a move."""

    return build_sparse_graph(
        map_id=MAP,
        prototypes={(x, y): _prototype("Anchor"), (x + 10, y): _prototype("Shop")},
        node_ids={(x, y): "anchor", (x + 10, y): "shop"},
        roads=[("anchor", "shop", "e"), ("shop", "anchor", "w")],
    )


class ReferenceResolutionTests(unittest.TestCase):
    def _index(self):
        return ReferenceIndex.build(
            settlement_nodes=[(MAP, "anchor", (10, 10)), (MAP, "shop", (20, 10))],
            interior_rooms=[("t_interior", "room")],
            locations=[("t_location", (30, 30))],
            frame_cells=64,
        )

    @covers_requirement("map-object-references::static-references-resolve-by-authored-identity")
    def test_absent_wrong_domain_and_duplicate_are_named(self):
        index = self._index()

        with self.assertRaises(ReferenceError) as captured:
            resolve_reference(
                index,
                settlement_node_ref(MAP, "nowhere"),
                source="district t_probe",
            )
        self.assertEqual(captured.exception.code, UNKNOWN_REFERENCE)
        self.assertIn("district t_probe: ", str(captured.exception))
        self.assertIn(f"settlement_node:{MAP}:nowhere", str(captured.exception))

        with self.assertRaises(ReferenceError) as captured:
            resolve_reference(index, settlement_node_ref(MAP, "room"), source="place t")
        self.assertEqual(captured.exception.code, WRONG_DOMAIN)
        self.assertIn("authored interior_room", str(captured.exception))

        with self.assertRaises(ReferenceError) as captured:
            ReferenceIndex.build(
                settlement_nodes=[(MAP, "anchor", (10, 10)), (MAP, "anchor", (11, 10))]
            )
        self.assertEqual(captured.exception.code, DUPLICATE_REFERENCE)

    def test_every_domain_and_the_explicit_cell_form_resolve(self):
        index = self._index()
        self.assertEqual(
            resolve_reference(index, settlement_node_ref(MAP, "anchor")).position_m,
            (10, 10),
        )
        self.assertEqual(
            resolve_reference(index, interior_room_ref("t_interior", "room")).object_id,
            "room",
        )
        self.assertEqual(resolve_reference(index, location_ref("t_location")).cell, (30, 30))
        self.assertEqual(resolve_reference(index, wilderness_cell_ref((63, 1))).cell, (63, 1))


class StaticFamilyMovementTests(EvenniaTest):
    """Every migrated family resolves the same identity at a new coordinate."""

    def _declarations(self):
        district = DistrictDeclaration(
            "t_district", "測試區", "測試碑", settlement_node_ref(MAP, "anchor"), "voronoi", None
        )
        place = mock.Mock(key="t_place", exterior=settlement_node_ref(MAP, "shop"))
        return district, place

    @covers_requirement("map-object-references::static-references-resolve-by-authored-identity")
    def test_gates_places_districts_and_art_follow_the_moved_node(self):
        district, place = self._declarations()

        with mock.patch.object(map_data, "SETTLEMENT_GRAPHS", {MAP: _graph(10, 10)}):
            self.assertEqual(settlement_node_xyz(settlement_node_ref(MAP, "anchor")), (10, 10, MAP))
            self.assertEqual(place_exterior_xyz(place), (20, 10, MAP))
            self.assertEqual(landmark_node_id(district), encode_grid(MAP, 10, 10))
            self.assertEqual(
                landmark_node_ids({"t_district": district}),
                {"t_district": encode_grid(MAP, 10, 10)},
            )

        with mock.patch.object(map_data, "SETTLEMENT_GRAPHS", {MAP: _graph(40, 40)}):
            # Declarations are untouched; only the current binding moved.
            self.assertEqual(district.landmark, settlement_node_ref(MAP, "anchor"))
            self.assertEqual(place.exterior, settlement_node_ref(MAP, "shop"))
            self.assertEqual(settlement_node_xyz(settlement_node_ref(MAP, "anchor")), (40, 40, MAP))
            self.assertEqual(place_exterior_xyz(place), (50, 40, MAP))
            self.assertEqual(landmark_node_id(district), encode_grid(MAP, 40, 40))
            # The wire grammar is unchanged: grid:<map>:<x>:<y>.
            self.assertTrue(landmark_node_id(district).startswith(f"grid:{MAP}:"))

    def test_validate_static_references_rejects_an_absent_authored_target(self):
        with mock.patch.object(map_data, "SETTLEMENT_GRAPHS", {MAP: _graph()}):
            import world.lore.anchor_placement as anchor_placement
            import world.lore.map_districts as map_districts
            import world.lore.settlements.places as places
            import world.lore.wilderness_entry as wilderness_entry
            import world.maps.city_gates as city_gates
            import world.maps.room_art as room_art

            with (
                mock.patch.object(
                    city_gates,
                    "CITY_GATE_REGISTRY",
                    {"t_broken": mock.Mock(gate=settlement_node_ref(MAP, "nowhere"))},
                ),
                mock.patch.object(anchor_placement, "ANCHOR_PLACEMENT_REGISTRY", {}),
                mock.patch.object(wilderness_entry, "WILDERNESS_ENTRY_REGISTRY", {}),
                mock.patch.object(places, "PLACE_REGISTRY", {}),
                mock.patch.object(
                    map_districts,
                    "current",
                    return_value=mock.Mock(districts={}, identity="t_identity"),
                ),
                mock.patch.object(room_art, "GRID_NODE_SCENE_ARCHETYPES", {}),
            ):
                with self.assertRaises(StaticReferenceError) as captured:
                    validate_static_references()
        self.assertIn("city gate t_broken", str(captured.exception))
        self.assertIn("no authored node", str(captured.exception))

    def test_binding_signature_tracks_geography_and_road_geometry(self):
        from elosern_map_core.sparse import SparseRoad

        graph = _graph(10, 10)
        bent = build_sparse_graph(
            map_id=MAP,
            prototypes={(10, 10): _prototype("Anchor"), (20, 10): _prototype("Shop")},
            node_ids={(10, 10): "anchor", (20, 10): "shop"},
            roads=[
                SparseRoad("anchor>shop", "anchor", "shop", bend_points=((15, 12),)),
                ("shop", "anchor", "w"),
            ],
        )
        with mock.patch.object(map_data, "SETTLEMENT_GRAPHS", {MAP: graph}):
            straight = binding_signature()
        with mock.patch.object(map_data, "SETTLEMENT_GRAPHS", {MAP: bent}):
            self.assertNotEqual(binding_signature(), straight)


class SyncPreservationTests(EvenniaTest):
    def test_repeated_synchronization_creates_no_duplicate_objects(self):
        first = sync_settlement_graph(_graph(10, 10))
        second = sync_settlement_graph(_graph(10, 10))
        self.assertEqual(first.created, 4)
        self.assertEqual(second.created, 0)
        self.assertEqual(second.updated, 0)
        self.assertEqual(
            GridRoom.objects.filter_xyz(xyz=("*", "*", MAP)).count(), 2
        )

    def test_failure_before_write_leaves_prior_state_untouched(self):
        sync_settlement_graph(_graph(10, 10))
        observer = create_object(PlayerCharacter, key="observer")
        observer.attributes.add(
            KNOWLEDGE_ATTR,
            {
                "schema_version": 1,
                "visited": {
                    encode_grid(MAP, 10, 10): {"first_seen_tick": 2, "last_seen_tick": 7}
                },
            },
        )
        # A moved identity may not land on an unbound room: the plan refuses
        # before any write.
        unbound, errors = GridRoom.create(key="legacy", xyz=(40, 40, MAP))
        self.assertFalse(errors)
        self.assertIsNotNone(
            GridRoom.objects.filter_xyz(xyz=(40, 40, MAP)).first()
        )

        with self.assertRaises(SparseGraphError):
            sync_settlement_graph(_graph(40, 40))

        self.assertEqual(
            observer.attributes.get(KNOWLEDGE_ATTR)["visited"],
            {encode_grid(MAP, 10, 10): {"first_seen_tick": 2, "last_seen_tick": 7}},
        )

    def test_moved_node_keeps_identity_home_inbound_and_knowledge(self):
        sync_settlement_graph(_graph(10, 10))
        room = GridRoom.objects.filter_xyz(xyz=(10, 10, MAP)).first()
        other = create_object(Room, key="inbound source")
        inbound = create_object(Exit, key="in", location=other, destination=room)
        traveller = create_object(PlayerCharacter, key="traveller", location=room)
        traveller.home = room
        traveller.attributes.add(
            KNOWLEDGE_ATTR,
            {
                "schema_version": 1,
                "visited": {
                    encode_grid(MAP, 10, 10): {"first_seen_tick": 3, "last_seen_tick": 9}
                },
            },
        )

        moved_graph = _graph(20, 20)
        with mock.patch.object(map_data, "SETTLEMENT_GRAPHS", {MAP: moved_graph}):
            sync_settlement_graph(moved_graph)

            moved = GridRoom.objects.get(pk=room.pk)
            self.assertEqual(moved.xyz, (20, 20, MAP))
            self.assertEqual(moved.sparse_node_id, "anchor")
            self.assertEqual(inbound.destination.pk, room.pk)
            self.assertEqual(traveller.home.pk, room.pk)
            visits = parse_knowledge(traveller)
        self.assertEqual([visit.node_id for visit in visits], [encode_grid(MAP, 20, 20)])
        self.assertEqual(visits[0].first_seen_tick, 3)
        self.assertEqual(visits[0].last_seen_tick, 9)


class PreflightPolicyTests(EvenniaTest):
    @covers_requirement("map-object-references::static-references-resolve-by-authored-identity")
    def test_a_wrong_domain_target_is_rejected_before_any_write(self):
        from world.lore.settlements import places
        from world.maps import city_gates
        from world.maps import room_art

        broken = {
            "t_wrong_domain": CityGateDef(
                gate=wilderness_cell_ref((1, 2)),
                exit_key="測試門",
                exit_aliases=(),
            )
        }
        with (
            mock.patch.object(city_gates, "CITY_GATE_REGISTRY", broken),
            mock.patch.object(places, "PLACE_REGISTRY", {}),
            mock.patch.object(room_art, "GRID_NODE_SCENE_ARCHETYPES", {}),
        ):
            with self.assertRaises(StaticReferenceError) as captured:
                validate_static_references()
        self.assertIn("city gate t_wrong_domain", str(captured.exception))
        self.assertIn("not a settlement_node", str(captured.exception))

    def test_sync_all_rejects_before_mirroring_any_registry(self):
        from evennia.objects.models import ObjectDB
        from evennia.utils.search import search_script
        from world.lore import sync
        from world.maps import city_gates

        broken = {
            "t_broken": CityGateDef(
                gate=settlement_node_ref(MAP, "nowhere"), exit_key="x", exit_aliases=()
            )
        }
        before = (ObjectDB.objects.count(), len(search_script("lore:anchor_placements:capital_altoria")))
        with (
            mock.patch.object(city_gates, "CITY_GATE_REGISTRY", broken),
            mock.patch.object(sync, "sync_one") as sync_one,
        ):
            with self.assertRaises(StaticReferenceError):
                sync.sync_all()
        sync_one.assert_not_called()
        self.assertEqual(
            (ObjectDB.objects.count(), len(search_script("lore:anchor_placements:capital_altoria"))),
            before,
        )

    def test_startup_rejects_before_creating_the_world_clock(self):
        from evennia.objects.models import ObjectDB
        from server.conf.at_server_startstop import at_server_start
        from world.maps import city_gates

        broken = {
            "t_broken": CityGateDef(
                gate=settlement_node_ref(MAP, "nowhere"), exit_key="x", exit_aliases=()
            )
        }
        before = ObjectDB.objects.count()
        with (
            mock.patch.object(city_gates, "CITY_GATE_REGISTRY", broken),
            mock.patch("world.rules.clock.get_world_clock") as clock,
        ):
            with self.assertRaises(StaticReferenceError):
                at_server_start()
        clock.assert_not_called()
        self.assertEqual(ObjectDB.objects.count(), before)


class IntegratedMovedNodeTests(EvenniaTest):
    """One moved identity reaches every synchronizer and cached consumer."""

    def _place(self):
        return PlaceDefinition(
            key="t_ref_place",
            settlement_key="t_settlement",
            kind=PlaceKind.HOME,
            room_name_zh="合成參照室",
            room_desc_zh="Synthetic reference interior.",
            exterior=settlement_node_ref(MAP, "shop"),
            doorway_key_zh="測試門",
            doorway_aliases=(),
        )

    def _district(self):
        return DistrictDeclaration(
            district_id="t_ref_district",
            district_name_zh="測試區",
            landmark_name_zh="測試碑",
            landmark=settlement_node_ref(MAP, "anchor"),
            kind="voronoi",
            region_key=None,
        )

    def _apply(self, graph, place, district):
        import world.maps.bootstrap as bootstrap_module
        import world.lore.map_districts as districts_module
        import world.maps.city_gates as gates_module
        import world.maps.room_art as room_art
        from world.lore import anchor_placement, wilderness_entry

        gates = {
            "t_gate": CityGateDef(
                gate=settlement_node_ref(MAP, "anchor"),
                exit_key="測試門",
                exit_aliases=(),
            )
        }
        art = {settlement_node_ref(MAP, "anchor"): "t_synthetic_scene"}
        stack = ExitStack()
        for entry in (
            (map_data, "SETTLEMENT_GRAPHS", {MAP: graph}),
            (bootstrap_module, "SETTLEMENT_GRAPHS", {MAP: graph}),
            (gates_module, "CITY_GATE_REGISTRY", gates),
            (bootstrap_module, "CITY_GATE_REGISTRY", gates),
            (anchor_placement, "ANCHOR_PLACEMENT_REGISTRY", {}),
            (wilderness_entry, "WILDERNESS_ENTRY_REGISTRY", {}),
            (
                "world.lore.settlements.places.PLACE" + "_REGISTRY",
                {place.key: place},
            ),
            (bootstrap_module, "PLACE" + "_REGISTRY", {place.key: place}),
            (
                districts_module,
                "current",
                mock.Mock(
                    return_value=mock.Mock(
                        districts={district.district_id: district},
                        identity="t_identity",
                    )
                ),
            ),
            (room_art, "GRID_NODE_SCENE_ARCHETYPES", art),
            (bootstrap_module, "GRID_NODE_SCENE_ARCHETYPES", art),
        ):
            if isinstance(entry[0], str):
                path, value = entry
                stack.enter_context(mock.patch(path, value))
                continue
            target, attribute, value = entry
            if isinstance(target, str):
                stack.enter_context(mock.patch(target, value))
            else:
                stack.enter_context(mock.patch.object(target, attribute, value))
        return stack

    @covers_requirement("map-object-references::static-references-resolve-by-authored-identity")
    def test_moved_node_follows_gate_art_service_and_lighting(self):
        place, district = self._place(), self._district()
        create_object(Room, key=LIMBO_KEY)
        traveller = create_object(PlayerCharacter, key="traveller")
        traveller.attributes.add(
            KNOWLEDGE_ATTR,
            {
                "schema_version": 1,
                "visited": {encode_grid(MAP, 10, 10): {"first_seen_tick": 1, "last_seen_tick": 2}},
            },
        )

        with self._apply(_graph(10, 10), place, district):
            sync_grid()
            sync_interiors()
            anchor = GridRoom.objects.filter_xyz(xyz=(10, 10, MAP)).first()
            shop = GridRoom.objects.filter_xyz(xyz=(20, 10, MAP)).first()
            self.assertEqual(anchor.scene_archetype, "t_synthetic_scene")
            self.assertEqual(anchor.scene_identity, grid_scene_identity(MAP, 10, 10))
            limbo = Room.objects.filter(db_key=LIMBO_KEY).first()
            self.assertEqual(
                [exit_obj.destination.pk for exit_obj in limbo.exits],
                [anchor.pk],
            )
            from evennia.utils.search import search_object_by_tag

            interiors = search_object_by_tag(place.key)
            self.assertEqual(len(interiors), 1)
            interior = interiors[0]
            self.assertTrue(
                any(exit_obj.destination.pk == shop.pk for exit_obj in interior.exits)
            )
            self.assertEqual(
                lit_district_keys(traveller, {district.district_id: district}),
                frozenset({district.district_id}),
            )
            first_signature = binding_signature()

            moved = _graph(40, 40)
            with self._apply(moved, place, district):
                sync_grid()
                sync_interiors()
                # The declarations never changed; every consumer followed the
                # same stable node to its new binding.
                self.assertNotEqual(binding_signature(), first_signature)
                moved_anchor = GridRoom.objects.get(pk=anchor.pk)
                moved_shop = GridRoom.objects.get(pk=shop.pk)
                self.assertEqual(moved_anchor.xyz, (40, 40, MAP))
                self.assertEqual(moved_shop.xyz, (50, 40, MAP))
                self.assertEqual(
                    moved_anchor.scene_identity, grid_scene_identity(MAP, 40, 40)
                )
                self.assertEqual(
                    [exit_obj.destination.pk for exit_obj in limbo.exits],
                    [moved_anchor.pk],
                )
                self.assertTrue(
                    any(
                        exit_obj.destination.pk == moved_shop.pk
                        for exit_obj in interior.exits
                    )
                )
                self.assertEqual(
                    [visit.node_id for visit in parse_knowledge(traveller)],
                    [encode_grid(MAP, 40, 40)],
                )
                self.assertEqual(
                    lit_district_keys(traveller, {district.district_id: district}),
                    frozenset({district.district_id}),
                )
