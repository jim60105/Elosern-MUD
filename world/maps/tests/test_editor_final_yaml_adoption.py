"""A moved node keeps its rooms, exits, homes and knowledge."""


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


class FinalYamlAdoptionTests(_CandidateCase):
    """A moved node keeps its rooms, exits, homes and knowledge."""

    @covers_requirement(
        "map-runtime-adoption::runtime-adoption-publishes-one-complete-validated-world"
    )
    def test_a_moved_occupied_node_keeps_rooms_exits_homes_and_knowledge(self):
        # The no-creation assertion below is a whole-candidate claim, so the
        # complete world is converged (unscoped) before the baseline is read.
        runtime.synchronize()
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

