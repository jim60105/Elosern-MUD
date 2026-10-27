"""Mechanism tests for qualified static map references (P03).

Static declarations hold identities; the game boundary derives the current
coordinate, wire id and room form. These tests use synthetic declarations and
a synthetic settlement graph, never shipped geography or copy.
"""

from __future__ import annotations

import unittest
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
from typeclasses.characters import PlayerCharacter
from typeclasses.exits import Exit
from typeclasses.rooms import GridRoom, Room

from world.lore.map_districts import MapDistrict, landmark_node_id, landmark_node_ids
from world.maps import map_data
from world.maps.bootstrap import (
    sync_grid,
    sync_service_interiors,
    sync_settlement_graph,
)
from world.maps.static_references import (
    StaticReferenceError,
    place_exterior_xyz,
    settlement_node_xyz,
    validate_static_references,
)
from world.rules.map_knowledge import KNOWLEDGE_ATTR, encode_grid, parse_knowledge

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
        district = MapDistrict(
            "t_district", "測試區", "測試碑", settlement_node_ref(MAP, "anchor"), "voronoi"
        )
        place = mock.Mock(key="t_place", exterior=settlement_node_ref(MAP, "shop"))
        return district, place

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
                mock.patch.object(map_districts, "MAP_DISTRICT_REGISTRY", {}),
                mock.patch.object(room_art, "GRID_NODE_SCENE_ARCHETYPES", {}),
            ):
                with self.assertRaises(StaticReferenceError) as captured:
                    validate_static_references()
        self.assertIn("city gate t_broken", str(captured.exception))
        self.assertIn("no authored node", str(captured.exception))


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
