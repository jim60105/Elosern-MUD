"""Mechanism tests for resolving a subrace's start room.

The subrace, its start row and its anchor placement all come from the
synthetic kit. The kit placement borrows a shipped node identity that the
real settlement synchronizer materializes, so the resolver is exercised
against real grid rooms without naming shipped content.
"""

from __future__ import annotations

from elosern_map_core.references import settlement_node_ref
from evennia.utils.test_resources import EvenniaTest

from typeclasses.rooms import GridRoom
from world.lore.anchor_placement import AnchorPlacement
from world.lore.start_locations import SubraceStartLocation
from world.maps.static_references import anchor_entrance_xyz
from world.rules.start_location import StartLocationError, resolve_start_room
from world.tests.geography_fixture import (
    publish_shipped_map_world,
    sync_test_settlements,
)
from world.tests.synthetic_data import (
    SYNTH_ANCHOR_PLACEMENTS,
    SYNTH_START_LOCATIONS,
    synthetic_registries,
)
from world.tests.synthetic_data.vocab import _SYNTH_SECOND_GATE_REF

SUBRACE = sorted(SYNTH_START_LOCATIONS)[0]
ANCHOR = SYNTH_START_LOCATIONS[SUBRACE].anchor_key
PLACEMENT = SYNTH_ANCHOR_PLACEMENTS[ANCHOR]
MOVED_PLACEMENT = AnchorPlacement(ANCHOR, _SYNTH_SECOND_GATE_REF)
_SCOPE = ("subraces", "start_locations", "anchor_placements")


def setUpModule():
    publish_shipped_map_world()


def _scope(**extra):
    return synthetic_registries(*_SCOPE, extra=extra or None)


def _room_at(placement):
    """The grid room the synchronizer built at one placement's node."""

    return GridRoom.objects.filter_xyz(xyz=anchor_entrance_xyz(placement)).first()


class ResolveStartRoomTests(EvenniaTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Runs outside any synthetic scope: the shipped registries are live
        # and consistent while the two borrowed settlements are materialized.
        sync_test_settlements(
            sorted({PLACEMENT.node.map_id, MOVED_PLACEMENT.node.map_id})
        )

    def test_resolution_returns_the_anchor_room_of_the_start_settlement(self):
        expected = _room_at(PLACEMENT)
        self.assertIsNotNone(expected, "the borrowed node was not materialized")

        with _scope():
            self.assertEqual(resolve_start_room(SUBRACE), expected)

    def test_a_moved_anchor_node_moves_the_start_room(self):
        original = _room_at(PLACEMENT)
        moved = _room_at(MOVED_PLACEMENT)
        self.assertIsNotNone(moved, "the second borrowed node was not materialized")
        self.assertNotEqual(moved, original)

        with _scope(anchor_placements={ANCHOR: MOVED_PLACEMENT}):
            self.assertEqual(resolve_start_room(SUBRACE), moved)

    def test_a_subrace_without_a_start_row_raises(self):
        with _scope():
            for subrace_key in ("t_unlisted_subrace", None, ""):
                with self.subTest(subrace_key=subrace_key):
                    with self.assertRaisesRegex(
                        StartLocationError, "has no start location"
                    ):
                        resolve_start_room(subrace_key)

    def test_a_start_anchor_without_a_placement_raises(self):
        row = SubraceStartLocation("t_wayfarer", "t_nowhere")

        with _scope(start_locations={row.subrace_key: row}):
            with self.assertRaisesRegex(StartLocationError, "has no map placement"):
                resolve_start_room(row.subrace_key)

    def test_a_placement_node_that_does_not_resolve_raises(self):
        broken = AnchorPlacement(
            ANCHOR, settlement_node_ref(PLACEMENT.node.map_id, "t_absent_node")
        )

        with _scope(anchor_placements={ANCHOR: broken}):
            with self.assertRaisesRegex(StartLocationError, "does not resolve"):
                resolve_start_room(SUBRACE)

    def test_a_placement_whose_room_was_deleted_raises(self):
        room = _room_at(PLACEMENT)
        self.assertIsNotNone(room, "the borrowed node was not materialized")
        # A queryset delete leaves the shared identity-map entry alone; the
        # surrounding test transaction restores the row for later methods.
        GridRoom.objects.filter(pk=room.pk).delete()

        with _scope():
            with self.assertRaisesRegex(StartLocationError, "is not built"):
                resolve_start_room(SUBRACE)
