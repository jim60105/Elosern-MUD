"""A rejected candidate leaves the published and persistent baseline intact."""


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


class FinalYamlRejectionTests(_CandidateCase):
    """A rejected candidate leaves the published and persistent baseline intact."""

    @classmethod
    def _materialization_scope(cls, bundle) -> tuple[str, ...]:
        # Every probe here compares a rejected adoption against the baseline;
        # no write happens, so only the settlements carrying the lookup
        # targets need persistent rows.
        return tuple(
            sorted(
                {exterior.settlement for exterior in bundle.interiors.exteriors.values()}
                | {
                    map_id
                    for map_id, settlement in bundle.settlements.settlements.items()
                    if settlement.wilderness_entry is not None
                    and settlement.wilderness_entry.is_point_shape
                }
            )
        )

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
