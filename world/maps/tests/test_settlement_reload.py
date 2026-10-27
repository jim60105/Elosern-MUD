"""Data-contract test: settlement reload convergence contract

The settlement synchronizer is the one persistent adapter: a document edit must
re-bind the same room and exit objects (never respawn them), keep the authored
travel direction, and charge the distance of the new authored metres. The
candidate is a synthetic document published through the real publication seam,
so the test exercises the whole source-to-persistence path.
"""

from __future__ import annotations

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.rooms import GridRoom, Room
from world.maps import map_data
from world.maps.bootstrap import sync_settlement_graph
from world.maps.limbo import LIMBO_KEY
from world.tests.geography_fixture import publish_shipped_geography

publish_shipped_geography()

_DOCUMENT = """
version: 1
kind: settlement
id: t_reload
location_ref: village_eolas
binding:
  anchor_cell:
    cell_x: 1410
    cell_y: 2150
  local_anchor_m:
    east_m: 100
    north_m: 100
options:
  map_visual_range: 2
  map_mode: nodes
exit_prototype:
  prototype_parent: xyz_exit
  typeclass: typeclasses.exits.CostedXYZExit
nodes:
  plaza:
    x_m: 100
    y_m: 100
    prototype_parent: anchor_room
    key: 廣場
    desc: 合成廣場。
    anchor_key: village_eolas
    typeclass:
    scene_archetype: city_street
  gate:
    x_m: 400
    y_m: 100
    prototype_parent: grid_room
    key: 門前
    desc: 合成門前。
    anchor_key:
    typeclass:
    scene_archetype: city_street
roads:
  - source: plaza
    destination: gate
    direction: e
  - source: gate
    destination: plaza
    direction: w
wilderness_entry:
city_gate:
""".lstrip()

#: The same map with the ``gate`` node moved 300 m further east.
_MOVED = _DOCUMENT.replace("    x_m: 400\n", "    x_m: 700\n")

_LOCATIONS = (map_data.REPOSITORY_ROOT / "content" / "maps" / "locations.yaml").read_text(
    encoding="utf-8"
)
_CONTINENT = (map_data.REPOSITORY_ROOT / "content" / "maps" / "continent.yaml").read_text(
    encoding="utf-8"
)


def _snapshot(text: str):
    """Build one candidate settlement world from document text."""

    from elosern_map_core.codec import parse_document
    from elosern_map_core.sources import make_source_document

    sources = [
        make_source_document("content/maps/settlements/t_reload.yaml", text)
    ]
    documents, locations, fingerprints = map_data.parse_settlement_documents(
        sources, _LOCATIONS
    )
    continent = parse_document("content/maps/continent.yaml", _CONTINENT)
    return map_data.build_settlements(
        documents,
        locations,
        frame_cells=continent.document.terrain.frame_cells,
        fingerprints=fingerprints,
    )


class SettlementReloadTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.previous = map_data.current()
        create_object(Room, key=LIMBO_KEY, location=None)

    def tearDown(self):
        map_data.publish(self.previous)
        super().tearDown()

    def _sync(self, text):
        snapshot = _snapshot(text)
        map_data.publish(snapshot)
        report = sync_settlement_graph(snapshot.graphs["t_reload"])
        return report

    def test_a_moved_node_keeps_identity_and_the_authored_direction(self):
        first = self._sync(_DOCUMENT)
        # Two rooms and two directed roads.
        self.assertEqual(first.created, 2 + len(_snapshot(_DOCUMENT).graphs["t_reload"].edges))
        from evennia.contrib.grid.xyzgrid.xyzroom import XYZExit

        plaza = GridRoom.objects.filter_xyz(xyz=(100, 100, "t_reload")).first()
        gate = GridRoom.objects.filter_xyz(xyz=(400, 100, "t_reload")).first()
        self.assertIsNotNone(plaza)
        self.assertIsNotNone(gate)
        exit_obj = XYZExit.objects.filter_xyz(xyz=(400, 100, "t_reload")).first()
        self.assertIsNotNone(exit_obj)
        authored = map_data.current().graphs["t_reload"].edge("gate", "plaza")
        self.assertEqual(authored.direction, "w")

        # The authored edit is published and converged a second time.
        self._sync(_MOVED)

        moved_gate = GridRoom.objects.filter_xyz(xyz=(700, 100, "t_reload")).first()
        self.assertIsNotNone(moved_gate)
        self.assertEqual(moved_gate.pk, gate.pk)
        self.assertEqual(moved_gate.sparse_node_id, "gate")
        self.assertIsNone(GridRoom.objects.filter_xyz(xyz=(400, 100, "t_reload")).first())
        self.assertEqual(
            GridRoom.objects.filter_xyz(xyz=(100, 100, "t_reload")).first().pk,
            plaza.pk,
        )

        # The exit object is reused and re-bound, and its authored direction is
        # unchanged (the metre delta never renames an exit).
        rebound = XYZExit.objects.filter_xyz(xyz=(700, 100, "t_reload")).first()
        self.assertIsNotNone(rebound)
        self.assertEqual(rebound.pk, exit_obj.pk)
        self.assertEqual(rebound.key, exit_obj.key)
        self.assertEqual(rebound.destination.xyz, (100, 100, "t_reload"))

    def test_the_converged_checkout_is_idempotent(self):
        self._sync(_DOCUMENT)
        first_rooms = set(GridRoom.objects.all_family().values_list("pk", flat=True))
        from evennia.contrib.grid.xyzgrid.xyzroom import XYZExit

        first_exits = set(XYZExit.objects.all_family().values_list("pk", flat=True))

        # Re-publishing the same document and syncing again changes nothing.
        report = self._sync(_DOCUMENT)

        self.assertEqual(report.created + report.deleted, 0)
        self.assertEqual(
            set(GridRoom.objects.all_family().values_list("pk", flat=True)),
            first_rooms,
        )
        self.assertEqual(
            set(XYZExit.objects.all_family().values_list("pk", flat=True)),
            first_exits,
        )

    def test_the_charge_follows_the_authored_metres(self):
        from world.rules.travel_cost import distance_traversal_cost

        self._sync(_DOCUMENT)
        before = map_data.current().graphs["t_reload"].edge("plaza", "gate").length
        self._sync(_MOVED)
        after = map_data.current().graphs["t_reload"].edge("plaza", "gate").length
        # 300 m further east: the edge and its charge grow by that distance.
        self.assertAlmostEqual(after - before, 300.0, places=6)
        self.assertGreater(
            distance_traversal_cost(after, "settlement", [_Probe()]).seconds,
            distance_traversal_cost(before, "settlement", [_Probe()]).seconds,
        )


class _Probe:
    """An uninitialized body: the base speed, no fatigue attributes."""
