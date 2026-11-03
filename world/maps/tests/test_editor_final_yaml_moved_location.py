"""A moved location keeps the occupied anchor room and moves every derived
geometry."""


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

from world.maps.tests._editor_adoption_fixtures import (
    REPOSITORY_ROOT,
    _CandidateCase,
    _node_dependents,
    _room_of,
    _yaml,
)


class FinalYamlMovedLocationTests(_CandidateCase):
    """A moved location keeps the anchor room and moves every derived geometry."""

    @covers_requirement(
        "map-runtime-adoption::runtime-adoption-publishes-one-complete-validated-world"
    )
    def test_a_moved_location_keeps_the_occupied_anchor_and_moves_all_geometry(self):
        """A location-only candidate, adopted with a genuinely regenerated artifact."""

        # As above: the no-creation assertion is a whole-candidate claim.
        runtime.synchronize()
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

