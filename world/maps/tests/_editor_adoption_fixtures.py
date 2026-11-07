"""Shared candidate case, source helpers and the complete-candidate fixture
for the split final-YAML adoption suites. This module holds no tests of its own.
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
from elosern_map_core.roads_codec import ROAD_ALGORITHM_VERSION, RoadFreshness
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
    @classmethod
    def _materialization_scope(cls, bundle) -> tuple[str, ...]:
        """The settlements seeded before the first method.

        A method whose subject is the complete candidate settles every
        settlement itself (unscoped) before it reads its baseline, so this
        seed only needs the lookup targets: the settlements carrying interiors
        and the point entrances.
        """

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

    @classmethod
    def setUpTestData(cls):
        # The baseline is built once per class and every method's writes still
        # roll back with its own transaction.
        super().setUpTestData()
        create_object(Room, key=LIMBO_KEY, location=None)
        cls.baseline = runtime.adopt()
        from world.tests.geography_fixture import sync_test_settlements

        sync_test_settlements(cls._materialization_scope(cls.baseline))
        bootstrap.sync_interiors()
        runtime.commit_adoption()

    def setUp(self):
        super().setUp()
        self.baseline = type(self).baseline
        # Every method edits its own writable source copy (a move, a removal,
        # an invalid reference); the materialized world above is shared.
        directory = tempfile.mkdtemp(prefix="editor-final-yaml-")
        self.addCleanup(shutil.rmtree, directory, True)
        self.root = Path(directory)
        shutil.copytree(REPOSITORY_ROOT / "content/maps", self.root / "content/maps")

    def tearDown(self):
        runtime.publish(type(self).baseline)
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
        with patch.object(
            district_partition, "artifact_metadata", return_value=signed
        ), patch.object(
            runtime,
            "road_freshness_for",
            return_value=RoadFreshness(ROAD_ALGORITHM_VERSION, "t", True),
        ):
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
        ), patch.object(
            runtime,
            "road_freshness_for",
            return_value=RoadFreshness(ROAD_ALGORITHM_VERSION, "t", True),
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

