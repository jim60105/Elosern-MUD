"""Game adoption of final editor YAML at the existing map owners.

The standalone editor writes YAML only; the game adopts it through
``world.maps.runtime`` and converges the persistent world in
``world.maps.bootstrap``. These tests start from the shipped world, write a
candidate source tree the way the editor would (one document changed, YAML
round-tripped), and check the committed effects:

* a moved, occupied and observed settlement node keeps its room, exits,
  occupant, home, inbound references and knowledge ticks, and every static
  declaration that names it resolves to the new position; a repeated
  synchronization changes nothing;
* a stale partition, a structural error or an invalid external reference
  rejects the candidate with the published registry and the persistent
  baseline unchanged;
* removing a node whose room is still live (occupied, and the destination of
  persisted road exits) is still refused by the live-dependent prune guard,
  and the prior bundle is restored.

The node and the interior under test are chosen from the published bundle by
their dependents, never by shipped name, so the checks follow the data.

The committed partition artifact lives in the repository, and its signature
covers every settlement document, so a moved node always makes it stale. The
editor's regeneration is stood in for by the committed artifact metadata
signed for the candidate's inputs; ``partition_freshness`` itself still runs
(it compares exactly the format, algorithm and source signature). The stale
case uses the committed artifact unchanged.
"""

from __future__ import annotations

import dataclasses
import io
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from ruamel.yaml import YAML

from elosern_map_core.documents import QualifiedRef
from tools.spec_traceability import covers_requirement

from typeclasses.characters import PlayerCharacter
from typeclasses.exits import Exit
from typeclasses.rooms import GridRoom, Room
from world.maps import bootstrap, district_partition, runtime
from world.maps.bootstrap import SparseGraphError
from world.maps.limbo import LIMBO_KEY
from world.maps.static_references import (
    binding_signature,
    published_static_world,
    settlement_node_xyz,
)
from world.rules.map_knowledge import KNOWLEDGE_ATTR, SCHEMA_VERSION, encode_grid

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _yaml() -> YAML:
    yaml = YAML(typ="rt", pure=True)
    yaml.preserve_quotes = True
    yaml.width = 4096
    return yaml


def _node_dependents() -> dict[tuple[str, str], set[str]]:
    """Each settlement node's dependent declaration families, from the bundle."""

    dependents: dict[tuple[str, str], set[str]] = {}

    def add(reference: QualifiedRef, family: str) -> None:
        if reference is not None and reference.domain == "settlement_node":
            dependents.setdefault((reference.map_id, reference.object_id), set()).add(family)

    static = published_static_world()
    for row in static.city_gates.values():
        add(row.gate, "city_gate")
    for placement in static.anchor_placements.values():
        add(placement.node, "anchor")
    for entry in static.wilderness_entries.values():
        for gate in entry.gates:
            add(gate.destination, "wilderness_gate")
    for landmark in static.district_landmarks.values():
        add(landmark, "landmark")
    for reference in static.grid_art:
        add(reference, "art")
    for exterior in runtime.current().interiors.exteriors.values():
        dependents.setdefault((exterior.settlement, exterior.node), set()).add("interior")
    return dependents


def _room_of(map_id: str, node_id: str):
    node = runtime.current().settlements.graphs[map_id].nodes[node_id]
    room = GridRoom.objects.filter_xyz(xyz=(node.x, node.y, map_id)).first()
    return node, room


class _CandidateCase(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        create_object(Room, key=LIMBO_KEY, location=None)
        self.baseline = runtime.adopt()
        bootstrap.sync_grid()
        bootstrap.sync_interiors()
        runtime.commit_adoption()
        directory = tempfile.mkdtemp(prefix="editor-final-yaml-")
        self.addCleanup(shutil.rmtree, directory, True)
        self.root = Path(directory)
        shutil.copytree(REPOSITORY_ROOT / "content/maps", self.root / "content/maps")

    def tearDown(self):
        runtime.publish(self.baseline)
        super().tearDown()

    # -- candidate editing (what the editor writes) -----------------------
    def settlement_path(self, map_id: str) -> Path:
        for path in sorted((self.root / "content/maps/settlements").glob("*.yaml")):
            if _yaml().load(path.read_text(encoding="utf-8")).get("id") == map_id:
                return path
        self.fail(f"no settlement document declares {map_id}")

    def edit(self, path: Path, change) -> None:
        yaml = _yaml()
        data = yaml.load(path.read_text(encoding="utf-8"))
        change(data)
        output = io.StringIO()
        yaml.dump(data, output)
        path.write_text(output.getvalue(), encoding="utf-8")

    @contextmanager
    def regenerated_partition(self):
        """The committed artifact metadata, signed for the candidate inputs."""

        committed = district_partition.artifact_metadata()
        signed = dataclasses.replace(
            committed, source_signature=district_partition.current_source_signature(self.root)
        )
        with patch.object(district_partition, "artifact_metadata", return_value=signed):
            yield

    @contextmanager
    def generated_partition(self):
        """An artifact genuinely generated from the candidate sources.

        The real generator runs over the candidate world and the runtime reads
        that document's own metadata, so the freshness gate is satisfied by
        real generation rather than a re-signed committed artifact. A
        location move changes the district seed, so a metadata-only
        replacement would describe a world that no longer exists.
        """

        from elosern_map_core.authoring import load_authoring_world
        from elosern_map_core.partition import (
            generate_partition,
            partition_input,
            world_snapshot,
        )
        from elosern_map_core.partition_codec import read_partition_metadata
        from elosern_map_core.sources import discover_source_documents

        world = load_authoring_world(discover_source_documents(self.root))
        text = generate_partition(partition_input(world_snapshot(world)))
        self.generated_artifact = text
        with patch.object(
            district_partition,
            "artifact_metadata",
            return_value=read_partition_metadata(text),
        ):
            yield text

    # -- persistent baseline ----------------------------------------------
    def persistent(self) -> dict:
        return {
            "rooms": sorted(
                (obj.pk, tuple(obj.xyz) if isinstance(obj, GridRoom) else None)
                for obj in ObjectDB.objects.all()
                if isinstance(obj, (Room, GridRoom))
            ),
            "exits": sorted(
                (obj.pk, obj.db_location_id, obj.db_destination_id)
                for obj in ObjectDB.objects.all()
                if isinstance(obj, Exit)
            ),
        }

    def assert_baseline(self, bundle, signature, persistent) -> None:
        self.assertIs(runtime.current(), bundle)
        self.assertEqual(binding_signature(), signature)
        self.assertEqual(self.persistent(), persistent)


class FinalYamlAdoptionTests(_CandidateCase):
    def choose_node(self):
        """The occupied-capable node with the most dependent families."""

        ranked = sorted(
            (
                (-len(families), map_id, node_id, families)
                for (map_id, node_id), families in _node_dependents().items()
                if "interior" in families
            ),
        )
        for _, map_id, node_id, families in ranked:
            node, room = _room_of(map_id, node_id)
            if room is not None:
                return map_id, node, room, families
        self.fail("no materialized settlement node has an interior entrance")

    def free_position(self, map_id: str, node) -> tuple[int, int]:
        taken = {other.coordinate for other in runtime.current().settlements.graphs[map_id].nodes.values()}
        for dx in (-7, 7, -13, 13):
            candidate = (node.x + dx, node.y)
            if candidate not in taken and candidate[0] >= 0:
                return candidate
        self.fail("no free coordinate beside the node")

    def test_a_moved_occupied_node_keeps_rooms_exits_homes_and_knowledge(self):
        map_id, node, room, families = self.choose_node()
        # The chosen node exercises more than its interior entrance.
        self.assertGreaterEqual(len(families), 2, families)
        walker = create_object(PlayerCharacter, key="測試編纂旅人", location=room)
        walker.home = room
        walker.save()
        walker.attributes.add(KNOWLEDGE_ATTR, {
            "schema_version": SCHEMA_VERSION,
            "visited": {encode_grid(map_id, node.x, node.y): {"first_seen_tick": 4, "last_seen_tick": 9}},
            "wilderness": {},
        })
        outbound = sorted(exit_obj.pk for exit_obj in room.exits)
        inbound = sorted(ObjectDB.objects.filter(db_destination=room.id).values_list("pk", flat=True))
        self.assertTrue(outbound and inbound)
        before = self.persistent()
        signature = binding_signature()

        x, y = self.free_position(map_id, node)
        self.edit(self.settlement_path(map_id), lambda data: data["nodes"][node.node_id].update(x_m=x, y_m=y))
        with self.regenerated_partition():
            runtime.adopt(self.root)
        runtime.synchronize()

        moved = ObjectDB.objects.get(pk=room.pk)
        self.assertEqual(tuple(moved.xyz), (x, y, map_id))
        self.assertEqual(sorted(exit_obj.pk for exit_obj in moved.exits), outbound)
        self.assertEqual(
            sorted(ObjectDB.objects.filter(db_destination=room.id).values_list("pk", flat=True)), inbound
        )
        walker = ObjectDB.objects.get(pk=walker.pk)
        self.assertEqual((walker.db_location_id, walker.db_home_id), (room.pk, room.pk))
        self.assertEqual(
            walker.attributes.get(KNOWLEDGE_ATTR)["visited"],
            {encode_grid(map_id, x, y): {"first_seen_tick": 4, "last_seen_tick": 9}},
        )
        # Every static declaration naming the node resolves to its new place.
        reference = QualifiedRef(domain="settlement_node", map_id=map_id, object_id=node.node_id)
        self.assertEqual(tuple(settlement_node_xyz(reference, source="test")), (x, y, map_id))
        self.assertNotEqual(binding_signature(), signature)
        for exterior in runtime.current().interiors.exteriors.values():
            if (exterior.settlement, exterior.node) == (map_id, node.node_id):
                self.assertIn(exterior.doorway_key, {exit_obj.key for exit_obj in moved.exits})
        # Nothing was created or deleted; only the moved room's coordinate changed.
        after = self.persistent()
        self.assertEqual([pk for pk, _ in after["rooms"]], [pk for pk, _ in before["rooms"]])
        self.assertEqual(
            {pk for (pk, xyz), (_, old) in zip(after["rooms"], before["rooms"]) if xyz != old}, {room.pk}
        )
        self.assertEqual([pk for pk, *_ in after["exits"]], [pk for pk, *_ in before["exits"]])

        # A repeated synchronization of the same sources changes nothing.
        runtime.synchronize()
        self.assertEqual(self.persistent(), after)

    @covers_requirement(
        "map-runtime-adoption::runtime-adoption-publishes-one-complete-validated-world"
    )
    def test_a_moved_location_keeps_the_occupied_anchor_and_moves_all_geometry(self):
        """A location-only candidate, adopted with a genuinely regenerated artifact."""

        from elosern_map_core.partition_codec import read_partition_metadata

        from world.lore.anchors import anchor_geography, world_position_m

        # The centred point-entry settlement of the published world: its mask
        # is a single hash, so the marker and the wilderness entrance must be
        # one cell.
        point_entries = [
            (map_id, settlement)
            for map_id, settlement in sorted(
                runtime.current().settlements.settlements.items()
            )
            if settlement.wilderness_entry is not None
            and settlement.wilderness_entry.is_point_shape
        ]
        self.assertTrue(point_entries, "no shipped settlement has a point entry")
        map_id, settlement = point_entries[0]
        location_ref = settlement.location_ref
        anchor = settlement.anchor_node
        self.assertIsNotNone(anchor)
        authored_gate = settlement.wilderness_entry.gates[0]
        _, anchor_room = _room_of(map_id, anchor.node_id)
        self.assertIsNotNone(anchor_room, "the anchor room must be materialized")
        self.assertTrue(list(anchor_room.exits))
        walker = create_object(PlayerCharacter, key="測試錨點居民", location=anchor_room)
        walker.home = anchor_room
        walker.save()
        outbound = sorted(exit_obj.pk for exit_obj in anchor_room.exits)
        inbound = sorted(
            ObjectDB.objects.filter(db_destination=anchor_room.id).values_list("pk", flat=True)
        )

        locations_path = self.root / "content/maps/locations.yaml"
        document = _yaml().load(locations_path.read_text(encoding="utf-8"))
        old_cell = (
            document["locations"][location_ref]["cell"]["cell_x"],
            document["locations"][location_ref]["cell"]["cell_y"],
        )
        delta = (5, 7)
        new_cell = (old_cell[0] + delta[0], old_cell[1] + delta[1])
        # One document changes: the location cell. The settlement document is
        # byte-identical, so every derived value must follow the location.
        self.edit(
            locations_path,
            lambda data: data["locations"][location_ref]["cell"].update(
                cell_x=new_cell[0], cell_y=new_cell[1]
            ),
        )
        before_world = {
            node_id: world_position_m(location_ref, node.coordinate)
            for node_id, node in settlement.nodes.items()
        }
        before = self.persistent()

        with self.generated_partition() as generated:
            self.assertEqual(
                read_partition_metadata(generated).source_signature,
                district_partition.current_source_signature(self.root),
                "the generated artifact must describe the candidate inputs",
            )
            self.assertNotEqual(
                generated,
                district_partition.DATA_PATH.read_text(encoding="utf-8"),
                "a metadata-only re-signing of the committed artifact is not evidence",
            )
            runtime.adopt(self.root)
        runtime.synchronize()

        adopted = runtime.current().settlements
        entry = adopted.wilderness_entries[location_ref]
        # ADOPT-POINT: a centred point entry's wilderness entrance and the
        # world-map marker both equal the moved location cell.
        self.assertEqual(entry.anchor_cell, new_cell)
        self.assertEqual(entry.origin_xy, new_cell)
        self.assertEqual(anchor_geography()[location_ref].cell, new_cell)
        self.assertEqual(
            entry.gate_for(authored_gate.return_direction).destination.object_id,
            authored_gate.destination_node,
        )
        # The frame stays the derived location cell plus the anchor node.
        self.assertEqual(
            adopted.local_frame_anchors[location_ref].local_anchor_m, anchor.coordinate
        )
        after_world = {
            node_id: world_position_m(location_ref, node.coordinate)
            for node_id, node in adopted.settlements[map_id].nodes.items()
        }
        for node_id, position in before_world.items():
            self.assertEqual(
                after_world[node_id],
                (
                    position[0] + delta[0] * 1000,
                    position[1] + delta[1] * 1000,
                ),
                node_id,
            )

        # The occupied anchor room keeps its database identity, its local
        # coordinate (the settlement frame did not change) and its exits and
        # resident; only the derived world position moved.
        moved = ObjectDB.objects.get(pk=anchor_room.pk)
        self.assertEqual(tuple(moved.xyz), (anchor.x_m, anchor.y_m, map_id))
        self.assertEqual(sorted(exit_obj.pk for exit_obj in moved.exits), outbound)
        self.assertEqual(
            sorted(
                ObjectDB.objects.filter(db_destination=anchor_room.id).values_list(
                    "pk", flat=True
                )
            ),
            inbound,
        )
        resident = ObjectDB.objects.get(pk=walker.pk)
        self.assertEqual(
            (resident.db_location_id, resident.db_home_id),
            (anchor_room.pk, anchor_room.pk),
        )

        # Nothing was created or deleted, and a second synchronization of the
        # same sources duplicates nothing.
        after = self.persistent()
        self.assertEqual([pk for pk, _ in after["rooms"]], [pk for pk, _ in before["rooms"]])
        self.assertEqual([pk for pk, *_ in after["exits"]], [pk for pk, *_ in before["exits"]])
        runtime.synchronize()
        self.assertEqual(self.persistent(), after)

    def test_failed_candidates_leave_the_registry_and_persistent_baseline(self):
        bundle = runtime.current()
        signature = binding_signature()
        persistent = self.persistent()
        map_id, node, _, _ = self.choose_node()
        settlement = self.settlement_path(map_id)
        original = settlement.read_text(encoding="utf-8")

        # A moved node without a regenerated artifact: the partition is stale.
        x, y = self.free_position(map_id, node)
        self.edit(settlement, lambda data: data["nodes"][node.node_id].update(x_m=x, y_m=y))
        with self.assertRaises(runtime.MapWorldError) as caught:
            runtime.adopt(self.root)
        self.assertTrue(any("partition" in problem.lower() for problem in caught.exception.problems))
        self.assert_baseline(bundle, signature, persistent)

        # A structural error: a road to a node the document does not declare.
        settlement.write_text(original, encoding="utf-8")
        def undeclared_road(data):
            used = {road["direction"] for road in data["roads"] if road["source"] == node.node_id}
            direction = next(d for d in ("n", "ne", "e", "se", "s", "sw", "w", "nw") if d not in used)
            data["roads"].append(
                {"source": node.node_id, "destination": "t_undeclared_node", "direction": direction, "bends": []}
            )

        self.edit(settlement, undeclared_road)
        with self.regenerated_partition(), self.assertRaises(runtime.MapWorldError) as caught:
            runtime.adopt(self.root)
        self.assertTrue(any("t_undeclared_node" in problem for problem in caught.exception.problems),
                        caught.exception.problems)
        self.assert_baseline(bundle, signature, persistent)

        # An invalid external reference: an interior whose room a service
        # place joins disappears from the candidate (interiors are not
        # partition inputs, so the committed artifact stays current).
        settlement.write_text(original, encoding="utf-8")
        joined = {reference.object_id for reference in published_static_world().place_rooms.values()}
        linked = {link.target_interior for link in runtime.current().interiors.interior_links}
        documents = runtime.current().interiors.documents
        target = next(
            (identity for identity, document in sorted(documents.items())
             if joined & set(document.rooms) and identity not in linked),
            None,
        )
        self.assertIsNotNone(target, "no unlinked interior hosts a service place")
        (self.root / documents[target].relative_path).unlink()
        missing = joined & set(documents[target].rooms)
        with self.assertRaises(runtime.MapWorldError) as caught:
            runtime.adopt(self.root)
        # The service place join names the room the candidate no longer authors.
        self.assertTrue(
            any(room in problem for problem in caught.exception.problems for room in missing),
            caught.exception.problems,
        )
        self.assert_baseline(bundle, signature, persistent)

    def test_removing_a_live_referenced_node_is_refused_and_rolls_back(self):
        dependents = _node_dependents()
        candidates = sorted(
            (map_id, node_id)
            for map_id, graph in runtime.current().settlements.graphs.items()
            for node_id in graph.nodes
            # Grid art rides the node's own declaration and leaves with it.
            if dependents.get((map_id, node_id), set()) <= {"art"}
            and _room_of(map_id, node_id)[1] is not None
        )
        self.assertTrue(candidates, "no settlement node is free of other declarations")
        map_id, node_id = candidates[0]
        _, room = _room_of(map_id, node_id)
        resident = create_object(PlayerCharacter, key="測試留守者", location=room)
        bundle = runtime.current()
        signature = binding_signature()
        persistent = self.persistent()

        def remove(data):
            del data["nodes"][node_id]
            data["roads"] = [road for road in data["roads"]
                             if node_id not in (road["source"], road["destination"])]

        self.edit(self.settlement_path(map_id), remove)
        with self.regenerated_partition():
            runtime.adopt(self.root)
            with self.assertRaises(SparseGraphError):
                runtime.synchronize()
        self.assert_baseline(bundle, signature, persistent)
        self.assertEqual(ObjectDB.objects.get(pk=resident.pk).db_location_id, room.pk)
