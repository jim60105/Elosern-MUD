"""Integration tests for the authored permanent interiors (sample-city spec).

Interiors are synchronized from the interior documents, independently of the
service registry: each authored room exists once (tagged by its stable room
id), carries its authored prose and scene facts, and owns its connections and
its exterior doorway pair. A service place only *joins* such a room, so a
standalone interior needs no service record at all. A room whose authored
exterior has no materialized street warns (naming the room, its interior and
the joined place) and is skipped alone.
"""

from tools.spec_traceability import covers_requirement

import importlib
from unittest.mock import patch

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.search import search_object_by_tag
from evennia.utils.test_resources import EvenniaTestCase

from elosern_map_core.references import interior_room_ref
from elosern_map_core.references import settlement_node_ref
from typeclasses.exits import Exit
from typeclasses.rooms import GridRoom, Room
from world.maps import interiors
from world.maps.bootstrap import sync_grid, sync_interiors
from world.maps.static_references import settlement_node_xyz
from world.tests.geography_fixture import publish_shipped_map_world
from world.tests.interior_fixture import (
    interior_document,
    interior_exterior,
    interior_room,
    published_interiors,
)

# The catalogs are read through the owning module (the shared probes helpers'
# binding-safe accessor: the attribute is assembled at call time, never bound
# by name), and every assertion below iterates the CURRENT live rows — the
# test follows the registry instead of naming a shipped row.


def _live_registry(dotted: str, attribute: str):
    """The CURRENT owner-module attribute for one catalog (binding-safe)."""

    return getattr(importlib.import_module(dotted), attribute)


def _places():
    """The CURRENT place-registry mapping."""

    return _live_registry("world.lore.settlements.places", "PLACE" + "_REGISTRY")


def _authored_rooms():
    """The CURRENT published interior rooms, keyed by identity."""

    return interiors.current().rooms


class ServiceInteriorTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        publish_shipped_map_world()
        create_object(Room, key="虛境", location=None)
        sync_grid()

    def _count_grid_rooms(self):
        return GridRoom.objects.all_family().count()

    def _interior(self, room_id):
        rooms = search_object_by_tag(room_id)
        return rooms[0] if rooms else None

    def _frontage(self, room_id):
        exterior = interiors.current().exteriors[room_id]
        return GridRoom.objects.filter_xyz(
            xyz=settlement_node_xyz(
                _settlement_ref(exterior.settlement, exterior.node)
            )
        ).first()

    def test_fresh_sync_creates_one_room_per_authored_interior(self):
        sync_interiors()
        for room_id, authored in _authored_rooms().items():
            room = self._interior(room_id)
            self.assertIsNotNone(room, room_id)
            self.assertIsInstance(room, Room)
            self.assertEqual(room.key, authored.name_zh)
            self.assertIsNone(room.db.expire_tick)
            self.assertIsNone(room.location)
            self.assertEqual(room.db.desc, authored.desc_zh)

    def test_interiors_converge_onto_the_authored_scene_metadata(self):
        # A permanent interior is a plain Room carrying readable scene facts:
        # the archetype and artwork key the room's own document declares, and a
        # logical identity derived from its authored room id. A second sync
        # re-applies the same facts in place without duplicating a room.
        from world.art.scene_definitions import (
            is_registered_room_art_key,
            is_registered_scene_key,
        )
        from world.maps.room_art import place_scene_identity

        sync_interiors()
        for room_id, authored in _authored_rooms().items():
            room = self._interior(room_id)
            self.assertEqual(room.scene_archetype, authored.scene_archetype)
            self.assertTrue(is_registered_scene_key(room.scene_archetype), room_id)
            self.assertEqual(room.room_art_key, authored.art_key)
            if authored.art_key is not None:
                self.assertTrue(is_registered_room_art_key(room.room_art_key))
            self.assertEqual(room.scene_identity, place_scene_identity(room_id))

        room_count = Room.objects.all_family().count()
        for room_id in _authored_rooms():
            room = self._interior(room_id)
            room.scene_archetype = None
            room.room_art_key = None
            room.scene_identity = "drifted"
            room.save()

        sync_interiors()

        self.assertEqual(Room.objects.all_family().count(), room_count)
        for room_id, authored in _authored_rooms().items():
            room = self._interior(room_id)
            self.assertEqual(room.scene_archetype, authored.scene_archetype)
            self.assertEqual(room.room_art_key, authored.art_key)
            self.assertEqual(room.scene_identity, place_scene_identity(room_id))

    def test_interiors_have_bidirectional_doorways_to_documented_exteriors(self):
        sync_interiors()
        for room_id in interiors.current().exteriors:
            interior = self._interior(room_id)
            exterior = self._frontage(room_id)
            self.assertIsNotNone(exterior, room_id)
            self.assertIn(
                interior, {exit_obj.destination for exit_obj in exterior.exits}
            )
            self.assertIn(
                exterior, {exit_obj.destination for exit_obj in interior.exits}
            )

    @covers_requirement(
        "sample-city-altoria::the-sample-city-s-declared-exterior-topology-remains-unchanged-while-permanent-service-interiors-are-attached"
    )
    def test_grid_topology_is_unchanged(self):
        grid_before = self._count_grid_rooms()
        sync_interiors()
        self.assertEqual(self._count_grid_rooms(), grid_before)

    def test_interiors_are_not_xyzgrid_nodes(self):
        sync_interiors()
        grid_keys = {room.key for room in GridRoom.objects.all_family()}
        for room_id, authored in _authored_rooms().items():
            self.assertNotIn(authored.name_zh, grid_keys, room_id)

    @covers_requirement(
        "sample-city-altoria::altoria-service-content-synchronizes-idempotently-without-resetting-live-state"
    )
    def test_repeated_sync_reuses_tags_reapplies_desc_and_duplicates_no_doorway(self):
        sync_interiors()

        def snapshot():
            return {
                room_id: (room.pk, sorted(e.key for e in room.exits))
                for room_id in _authored_rooms()
                for room in search_object_by_tag(room_id)
            }

        first = snapshot()
        room_count = Room.objects.all_family().count()
        exit_count = Exit.objects.all().count()
        for room_id in _authored_rooms():
            room = search_object_by_tag(room_id)[0]
            room.db.desc = "drifted description"
            room.save()

        sync_interiors()

        self.assertEqual(snapshot(), first)
        self.assertEqual(Room.objects.all_family().count(), room_count)
        self.assertEqual(Exit.objects.all().count(), exit_count)
        for room_id, authored in _authored_rooms().items():
            self.assertEqual(
                search_object_by_tag(room_id)[0].db.desc, authored.desc_zh
            )

    def test_doorway_keys_and_aliases_are_the_authored_pair(self):
        sync_interiors()
        for room_id, exterior in interiors.current().exteriors.items():
            interior = self._interior(room_id)
            street = self._frontage(room_id)
            forward = [
                exit_obj
                for exit_obj in street.exits
                if exit_obj.destination == interior
            ]
            self.assertEqual(len(forward), 1)
            self.assertEqual(forward[0].key, exterior.doorway_key)
            self.assertEqual(
                set(forward[0].aliases.all()), set(exterior.doorway_aliases)
            )
            back = [
                exit_obj
                for exit_obj in interior.exits
                if exit_obj.destination == street
            ]
            self.assertEqual(len(back), 1)
            self.assertEqual(back[0].key, "外")

    def test_interior_reachable_from_and_back_to_exterior(self):
        sync_interiors()
        for room_id in interiors.current().exteriors:
            interior = self._interior(room_id)
            street = self._frontage(room_id)
            self.assertTrue(interior.access(street, "traverse", default=True), room_id)
            self.assertIn(street, {e.destination for e in interior.exits})

    @covers_requirement(
        "sample-city-altoria::the-sample-city-s-declared-exterior-topology-remains-unchanged-while-permanent-service-interiors-are-attached"
    )
    def test_one_exterior_carrying_two_places_yields_two_doorways(self):
        # The shared-alley scenario: one exterior with two interiors is one
        # street with two doors. Discovered dynamically from the published
        # interiors — this suite follows the authored rows, never names one.
        sync_interiors()
        grouped: dict[tuple, list[str]] = {}
        for room_id, exterior in interiors.current().exteriors.items():
            grouped.setdefault((exterior.settlement, exterior.node), []).append(room_id)
        shared = [row for row in grouped.values() if len(row) >= 2]
        self.assertTrue(shared, "no exterior carries two interiors for the scenario")
        for room_ids in shared:
            street = self._frontage(room_ids[0])
            rooms = [self._interior(room_id) for room_id in room_ids]
            forward = [
                exit_obj
                for exit_obj in street.exits
                if exit_obj.destination in rooms
            ]
            self.assertEqual(len(forward), len(room_ids))
            self.assertEqual(
                sorted(exit_obj.key for exit_obj in forward),
                sorted(
                    interiors.current().exteriors[room_id].doorway_key
                    for room_id in room_ids
                ),
            )
            for room in rooms:
                back = [
                    exit_obj
                    for exit_obj in room.exits
                    if exit_obj.destination == street and exit_obj.key == "外"
                ]
                self.assertEqual(len(back), 1)

    @covers_requirement(
        "place-driven-service-sync::interiors-are-created-by-iterating-the-place-registry"
    )
    def test_one_unresolvable_exterior_warns_and_skips_only_that_room(self):
        # One authored room whose exterior resolves but whose grid room is
        # absent must warn and skip alone; every other room still synchronizes.
        shared = {}
        for room_id, exterior in interiors.current().exteriors.items():
            shared.setdefault((exterior.settlement, exterior.node), []).append(room_id)
        room_id = next(
            room_ids[0] for room_ids in shared.values() if len(room_ids) == 1
        )
        shared_exterior = interiors.current().exteriors[room_id]
        xyz = settlement_node_xyz(
            _settlement_ref(shared_exterior.settlement, shared_exterior.node)
        )
        GridRoom.objects.filter_xyz(xyz).first().delete()
        with patch("world.maps.bootstrap.log_warn") as warned:
            sync_interiors()
        events = [
            call
            for call in warned.call_args_list
            if call.args and call.args[0] == "bootstrap_interior_exterior_missing"
        ]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kwargs["context"]["room"], room_id)
        self.assertEqual(events[0].kwargs["context"]["exterior_xyz"], xyz)
        self.assertIsNone(self._interior(room_id))
        for other_id in interiors.current().rooms:
            if other_id == room_id:
                continue
            self.assertIsNotNone(self._interior(other_id), other_id)

    @covers_requirement(
        "place-driven-service-sync::interiors-are-created-by-iterating-the-place-registry"
    )
    def test_two_synthetic_rooms_on_one_exterior_get_their_own_doorways(self):
        # A newly authored pair sharing one exterior under different doorway
        # names (the shape every content change writes) yields one doorway exit
        # per room on the street, not one shared exit.
        anchor_room = next(iter(interiors.current().exteriors))
        anchor = interiors.current().exteriors[anchor_room]
        document = interior_document(
            "t_alley_a_doc",
            {"t_alley_a": interior_room("測試巷道室甲", "Synthetic shared-exterior room A.")},
            exterior=interior_exterior(
                anchor.settlement, anchor.node, "t_alley_a", "測試巷門甲"
            ),
        )
        partner = interior_document(
            "t_alley_b_doc",
            {"t_alley_b": interior_room("測試巷道室乙", "Synthetic shared-exterior room B.")},
            exterior=interior_exterior(
                anchor.settlement, anchor.node, "t_alley_b", "測試巷門乙"
            ),
        )
        with published_interiors(document, partner):
            sync_interiors()
            street = self._frontage("t_alley_a")
            rooms = [self._interior("t_alley_a"), self._interior("t_alley_b")]
            self.assertTrue(all(room is not None for room in rooms))
            forward = [
                exit_obj
                for exit_obj in street.exits
                if exit_obj.destination in rooms
            ]
            self.assertEqual(len(forward), 2)
            self.assertEqual(
                sorted(exit_obj.key for exit_obj in forward),
                ["測試巷門乙", "測試巷門甲"],
            )

    def test_a_declared_interior_link_supplies_both_doors_and_retires_cleanly(self):
        # One authored relationship supplies both endpoint and return meanings,
        # and withdrawing it removes exactly its own two doors.
        house = interior_document(
            "t_link_house",
            {"t_link_house_room": interior_room("測試連通宅", "A synthetic house.")},
        )
        neighbour = interior_document(
            "t_link_neighbour",
            {"t_link_neighbour_room": interior_room("測試鄰居", "A synthetic neighbour.")},
            interior_links=(
                {
                    "source_room": "t_link_neighbour_room",
                    "target_interior": "t_link_house",
                    "target_room": "t_link_house_room",
                    "label": "敲門",
                    "return_label": "回鄰居",
                },
            ),
        )
        with published_interiors(house, neighbour):
            sync_interiors()
            house_room = self._interior("t_link_house_room")
            neighbour_room = self._interior("t_link_neighbour_room")
            self.assertEqual(
                [(e.key, e.destination.pk) for e in neighbour_room.exits],
                [("敲門", house_room.pk)],
            )
            self.assertEqual(
                [(e.key, e.destination.pk) for e in house_room.exits],
                [("回鄰居", neighbour_room.pk)],
            )
            with published_interiors(
                house,
                interior_document(
                    "t_link_neighbour",
                    {
                        "t_link_neighbour_room": interior_room(
                            "測試鄰居", "A synthetic neighbour."
                        )
                    },
                ),
            ):
                sync_interiors()
            self.assertEqual(self._interior("t_link_neighbour_room").exits, [])
            self.assertEqual(self._interior("t_link_house_room").exits, [])

    def test_retargeting_an_exterior_retires_the_old_doorway(self):
        # Moving an interior to another exterior is one authored edit: the old
        # doorway and its return exit disappear, and the unrelated doors on
        # both streets survive.
        first_room = next(iter(interiors.current().exteriors))
        first = interiors.current().exteriors[first_room]
        other_node = self._another_node(first)
        declaration = interiors.current().rooms[first_room]
        moved = interior_document(
            first_room,
            {
                first_room: interior_room(
                    declaration.name_zh,
                    declaration.desc_zh,
                    scene_archetype=declaration.scene_archetype,
                    art_key=declaration.art_key,
                )
            },
            exterior=interior_exterior(
                first.settlement, other_node, first_room, first.doorway_key
            ),
        )
        with published_interiors(moved):
            sync_interiors()
            interior = self._interior(first_room)
            old_street = GridRoom.objects.filter_xyz(
                xyz=settlement_node_xyz(
                    _settlement_ref(first.settlement, first.node)
                )
            ).first()
            self.assertIsNotNone(old_street)
            self.assertNotIn(
                interior,
                {exit_obj.destination for exit_obj in old_street.exits},
                "the retired doorway is still on the old street",
            )
            self.assertNotIn(
                old_street,
                {exit_obj.destination for exit_obj in interior.exits},
            )
            new_street = GridRoom.objects.filter_xyz(
                xyz=settlement_node_xyz(
                    _settlement_ref(first.settlement, other_node)
                )
            ).first()
            self.assertIn(
                interior, {exit_obj.destination for exit_obj in new_street.exits}
            )

    def _another_node(self, exterior) -> str:
        """Another authored settlement node of the same settlement."""

        graph = _live_registry("world.maps.map_data", "SETTLEMENT" + "_GRAPHS")[
            exterior.settlement
        ]
        occupied = {exterior.node}
        return next(
            node_id for node_id in graph.nodes if node_id not in occupied
        )

    def test_a_transiently_unavailable_frontage_keeps_the_interior_topology(self):
        # Retargeting a room onto a statically valid but not-yet-materialized
        # street must not destroy the room or its internal topology: the
        # dependent interior is skipped, and only the doorway to the vanished
        # street (now a dangling exit) retires.
        anchor_room = next(iter(interiors.current().exteriors))
        anchor_exterior = interiors.current().exteriors[anchor_room]
        settlement = anchor_exterior.settlement
        other_node = self._another_node(anchor_exterior)
        rooms = {
            "t_hold_hall": interior_room("測試門廳", "A synthetic hall."),
            "t_hold_inner": interior_room("測試內室", "A synthetic inner room."),
        }
        connections = (
            {"source": "t_hold_hall", "destination": "t_hold_inner", "label": "往內"},
        )
        settled = interior_document(
            "t_hold_house",
            rooms,
            connections=connections,
            exterior=interior_exterior(
                settlement, anchor_exterior.node, "t_hold_hall", "測試門廳門"
            ),
        )
        retargeted = interior_document(
            "t_hold_house",
            rooms,
            connections=connections,
            exterior=interior_exterior(
                settlement, other_node, "t_hold_hall", "測試門廳門"
            ),
        )
        with published_interiors(settled):
            sync_interiors()
            hall = self._interior("t_hold_hall")
            inner = self._interior("t_hold_inner")
            self.assertTrue(any(exit_obj.key == "外" for exit_obj in hall.exits))
            before = (
                hall.pk,
                hall.db.desc,
                sorted((exit_obj.key, exit_obj.destination.pk) for exit_obj in hall.exits),
                inner.pk,
                inner.db.desc,
            )

            # The new frontage is authored but not materialized.
            prettier = GridRoom.objects.filter_xyz(
                xyz=settlement_node_xyz(_settlement_ref(settlement, other_node))
            ).first()
            prettier.delete()

            with published_interiors(retargeted), patch("world.maps.bootstrap.log_warn"):
                sync_interiors()

            hall = self._interior("t_hold_hall")
            inner = self._interior("t_hold_inner")
            self.assertEqual(
                (
                    hall.pk,
                    hall.db.desc,
                    sorted(
                        (exit_obj.key, exit_obj.destination.pk)
                        for exit_obj in hall.exits
                    ),
                    inner.pk,
                    inner.db.desc,
                ),
                before,
                "a skipped dependent interior lost its room or its topology",
            )
            # No partial doorway was created on the absent street.
            self.assertFalse(
                [
                    exit_obj
                    for exit_obj in hall.exits
                    if exit_obj.destination is None
                ]
            )
            self.assertIsNone(
                GridRoom.objects.filter_xyz(
                    xyz=settlement_node_xyz(
                        _settlement_ref(settlement, other_node)
                    )
                ).first()
            )

    def test_two_rooms_sharing_one_tag_raise_the_integrity_error(self):
        from world.maps.bootstrap import InteriorSyncError

        with published_interiors(
            interior_document(
                "t_ambiguous_room",
                {"t_ambiguous_room": interior_room("測試曖昧室", "A synthetic room.")},
            )
        ):
            sync_interiors()
            create_object(Room, key="duplicate", tags=["t_ambiguous_room"], location=None)
            with self.assertRaises(InteriorSyncError):
                sync_interiors()

    def test_a_standalone_room_needs_no_service_record(self):
        document = interior_document(
            "t_standalone_room_doc",
            {"t_standalone_room": interior_room("測試獨立空屋", "A standalone room.")},
        )
        places = _places()
        with published_interiors(document):
            self.assertNotIn("t_standalone_room", places)
            sync_interiors()
            room = self._interior("t_standalone_room")
            self.assertIsNotNone(room)
            self.assertEqual(room.db.desc, "A standalone room.")
            self.assertEqual(room.exits, [])

    def test_a_service_place_only_joins_an_authored_room(self):
        # The service record declares no geometry: its room is the interior's,
        # and the place key is the join identity.
        for key, place in _places().items():
            with self.subTest(place=key):
                self.assertEqual(place.room, interior_room_ref(key, key))
                self.assertIn(key, interiors.current().rooms)
                self.assertEqual(place.room_name_zh, interiors.current().room(key).name_zh)


def _settlement_ref(settlement: str, node: str):
    return settlement_node_ref(settlement, node)


if __name__ == "__main__":
    import unittest

    unittest.main()
