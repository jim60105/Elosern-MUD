"""Data-contract test: settlement source discovery and composition contract

Discovery, composition and candidate rejection over the authored local-map
documents.

The authored local maps are discovered YAML documents under
``content/maps/settlements/<map_id>.yaml``. These tests establish the mechanisms
the game adapter must keep: sorted discovery with no Python registration, a
reverse location link derived from ``location_ref`` alone, exact graph fidelity
with the validated sparse graph, immutable publication, candidate isolation and
the named rejections. Shipped prose and magnitudes are never pinned here.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from elosern_map_core.codec import parse_document
from elosern_map_core.diagnostics import AuthoringError
from elosern_map_core.sources import make_source_document
from tools.spec_traceability import covers_requirement
from world.maps import map_data, runtime
from world.tests.geography_fixture import (
    clear_published_map_world,
    publish_settlements,
    restore_published_map_world,
)
from world.tests.geography_fixture import publish_shipped_settlements

publish_shipped_settlements()

#: A synthetic third settlement bound to an authored location that has no
#: shipped local map. Its ids deliberately differ from the location it binds, so
#: the location-derived (not identity-derived) reverse navigation is exercised.
_THIRD = """
version: 1
kind: settlement
id: t_third
location_ref: village_eolas
binding:
  anchor_cell:
    cell_x: 1410
    cell_y: 2150
  local_anchor_m:
    east_m: 20
    north_m: 30
options:
  map_visual_range: 2
  map_mode: nodes
exit_prototype:
  prototype_parent: xyz_exit
  typeclass: typeclasses.exits.CostedXYZExit
nodes:
  plaza:
    x_m: 20
    y_m: 30
    prototype_parent: anchor_room
    key: 廣場
    desc: 合成廣場。
    anchor_key: village_eolas
    typeclass:
    scene_archetype: city_street
  path:
    x_m: 120
    y_m: 30
    prototype_parent: grid_room
    key: 小徑
    desc: 合成小徑。
    anchor_key:
    typeclass:
    scene_archetype: forest_path
roads:
  - source: plaza
    destination: path
    direction: e
  - source: path
    destination: plaza
    direction: w
wilderness_entry:
  shape:
    - "#"
  origin:
    cell_x: 1410
    cell_y: 2150
  gates:
    - return_direction: n
      destination_node: plaza
city_gate:
  node: plaza
  exit_key: 廣場
  exit_aliases: [幽月谷]
""".lstrip()

_THIRD_PATH = "content/maps/settlements/t_third.yaml"
_LOCATIONS_TEXT = (map_data.REPOSITORY_ROOT / "content" / "maps" / "locations.yaml").read_text(
    encoding="utf-8"
)
_CONTINENT_TEXT = (map_data.REPOSITORY_ROOT / "content" / "maps" / "continent.yaml").read_text(
    encoding="utf-8"
)
_FRAME_CELLS = parse_document(
    "content/maps/continent.yaml", _CONTINENT_TEXT
).document.terrain.frame_cells


def _document(text: str = _THIRD, *, path: str = _THIRD_PATH):
    return make_source_document(path, text)


def _build(sources, locations_text: str = _LOCATIONS_TEXT):
    documents, locations, fingerprints = map_data.parse_settlement_documents(
        sources, locations_text
    )
    return map_data.build_settlements(
        documents,
        locations,
        frame_cells=_FRAME_CELLS,
        fingerprints=fingerprints,
    )


def _write_root(directory: str, settlement_text: str) -> Path:
    root = Path(directory)
    for relative_path, text in (
        ("content/maps/locations.yaml", _LOCATIONS_TEXT),
        ("content/maps/continent.yaml", _CONTINENT_TEXT),
        (_THIRD_PATH, settlement_text),
    ):
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


class ThirdSettlementTests(unittest.TestCase):
    @covers_requirement(
        "map-settlement-sources::settlement-documents-own-complete-local-map-declarations"
    )
    def test_a_third_document_is_discovered_and_composed_without_registration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = _write_root(directory, _THIRD)
            snapshot = runtime.compose_settlements(root)

        self.assertEqual(sorted(snapshot.graphs), ["t_third"])
        self.assertEqual(sorted(snapshot.settlements), ["t_third"])
        # Reverse navigation comes from location_ref alone: the document id and
        # the location id are different, and no Python row names either.
        self.assertEqual(sorted(snapshot.anchor_placements), ["village_eolas"])
        self.assertEqual(sorted(snapshot.local_frame_anchors), ["village_eolas"])
        self.assertEqual(sorted(snapshot.city_gates), ["t_third"])
        # Entry rows are keyed by the anchor identity the gate exits persist,
        # which is the document's location_ref (never its own id).
        self.assertEqual(sorted(snapshot.wilderness_entries), ["village_eolas"])
        self.assertEqual(
            snapshot.anchor_placements["village_eolas"].node.map_id, "t_third"
        )
        self.assertEqual(
            snapshot.anchor_placements["village_eolas"].node.object_id, "plaza"
        )
        self.assertEqual(
            snapshot.local_frame_anchors["village_eolas"].local_anchor_m, (20, 30)
        )
        entry = snapshot.wilderness_entries["village_eolas"]
        self.assertEqual(entry.anchor_key, "village_eolas")
        self.assertEqual(entry.gate_for("n").destination.map_id, "t_third")
        # The exact lookup a gate exit performs (``db.anchor_key`` holds the
        # entry's own anchor identity) resolves the entry.
        self.assertIs(snapshot.wilderness_entries.get(entry.anchor_key), entry)
        self.assertNotIn("t_third", snapshot.wilderness_entries)
        self.assertIn(entry.anchor_key, snapshot.anchor_placements)

    @covers_requirement(
        "map-settlement-sources::settlement-documents-own-complete-local-map-declarations"
    )
    def test_the_discovered_document_is_the_only_local_map_of_its_location(self):
        with tempfile.TemporaryDirectory() as directory:
            root = _write_root(directory, _THIRD)
            snapshot = runtime.compose_settlements(root)

        self.assertEqual(set(snapshot.graphs), {"t_third"})
        # The shipped world is untouched: discovery and publication are
        # separate, so a candidate never replaces what is already published.
        published = set(map_data.current().graphs)
        self.assertTrue(published)
        self.assertNotIn("t_third", published)


class SettlementGraphFidelityTests(unittest.TestCase):
    @covers_requirement(
        "map-settlement-sources::settlement-documents-own-complete-local-map-declarations"
    )
    def test_shipped_documents_compose_exactly_their_declared_graph(self):
        snapshot = map_data.current()
        self.assertTrue(snapshot.settlements)
        for settlement_id, document in snapshot.settlements.items():
            with self.subTest(settlement=settlement_id):
                graph = snapshot.graphs[settlement_id]
                self.assertEqual(set(graph.nodes), set(document.nodes))
                self.assertEqual(len(graph.edges), len(document.roads))
                for node_id, declaration in document.nodes.items():
                    node = graph.node(node_id)
                    self.assertEqual(node.coordinate, declaration.coordinate)
                    self.assertEqual(
                        node.prototype["prototype_parent"],
                        declaration.prototype_parent,
                    )
                    self.assertEqual(node.prototype["key"], declaration.key)
                    self.assertEqual(node.prototype["desc"], declaration.desc)
                for road in document.roads:
                    edge = graph.edge(road.source, road.destination)
                    self.assertIsNotNone(edge)
                    self.assertEqual(edge.direction, road.direction)
                self.assertEqual(dict(graph.options), dict(document.options))
                self.assertEqual(
                    dict(graph.exit_prototype), dict(document.exit_prototype)
                )

    @covers_requirement(
        "map-settlement-sources::settlement-documents-own-complete-local-map-declarations"
    )
    def test_moving_a_bound_node_changes_the_binding_not_the_identity(self):
        moved = _THIRD.replace("x_m: 120", "x_m: 220")
        snapshot = _build([_document(moved)])
        graph = snapshot.graphs["t_third"]
        self.assertEqual(graph.node("path").coordinate, (220, 30))
        edge = graph.edge("plaza", "path")
        self.assertEqual(edge.source.node_id, "plaza")
        self.assertEqual(edge.destination.node_id, "path")
        # The authored direction is kept, never recomputed from the delta.
        self.assertEqual(edge.direction, "e")
        # The anchor binding is untouched by a non-anchor node move.
        self.assertEqual(
            snapshot.local_frame_anchors["village_eolas"].local_anchor_m, (20, 30)
        )


class SettlementCandidateRejectionTests(unittest.TestCase):
    def _rejected(self, sources, fragment: str):
        with self.assertRaises((map_data.SettlementError, AuthoringError)) as caught:
            _build(sources)
        self.assertIn(fragment, str(caught.exception))
        return caught.exception

    def test_identity_must_equal_the_file_stem(self):
        with self.assertRaises(AuthoringError) as caught:
            _build([_document(_THIRD.replace("id: t_third", "id: t_other"))])
        self.assertIn(
            "identity_mismatch", {item.code for item in caught.exception.diagnostics}
        )

    def test_a_non_settlement_kind_is_refused(self):
        with self.assertRaises(AuthoringError) as caught:
            _build(
                [
                    make_source_document(
                        _THIRD_PATH,
                        _THIRD.replace("kind: settlement", "kind: interior"),
                    )
                ]
            )
        self.assertIn(
            "identity_mismatch", {item.code for item in caught.exception.diagnostics}
        )

    def test_the_same_path_supplied_twice_is_refused(self):
        self._rejected([_document(), _document()], "supplied more than once")

    def test_two_documents_bound_to_one_location_are_refused(self):
        second = _THIRD.replace("id: t_third", "id: t_other")
        self._rejected(
            [
                _document(),
                _document(second, path="content/maps/settlements/t_other.yaml"),
            ],
            "bound by more than one settlement",
        )

    def test_an_unknown_location_reference_is_refused(self):
        self._rejected(
            [
                _document(
                    _THIRD.replace(
                        "location_ref: village_eolas", "location_ref: t_absent"
                    )
                )
            ],
            "is not an authored location",
        )

    def test_a_missing_anchor_node_is_refused(self):
        no_anchor = _THIRD.replace(
            "prototype_parent: anchor_room", "prototype_parent: grid_room"
        ).replace("    anchor_key: village_eolas", "    anchor_key:")
        self._rejected([_document(no_anchor)], "anchor_room nodes")

    def test_a_binding_that_disagrees_with_the_anchor_node_is_refused(self):
        self._rejected(
            [_document(_THIRD.replace("east_m: 20", "east_m: 21"))],
            "disagrees with anchor node",
        )

    def test_a_binding_that_disagrees_with_the_location_cell_is_refused(self):
        self._rejected(
            [
                _document(
                    _THIRD.replace(
                        "    cell_y: 2150\n  local_anchor_m",
                        "    cell_y: 2160\n  local_anchor_m",
                    )
                )
            ],
            "disagrees with location",
        )

    def test_an_unregistered_scene_archetype_is_refused(self):
        self._rejected(
            [
                _document(
                    _THIRD.replace(
                        "scene_archetype: forest_path", "scene_archetype: t_nowhere"
                    )
                )
            ],
            "unregistered scene archetype",
        )

    def test_a_gate_to_an_absent_node_is_refused(self):
        self._rejected(
            [
                _document(
                    _THIRD.replace(
                        "destination_node: plaza", "destination_node: absent"
                    )
                )
            ],
            "is not an authored node",
        )

    def test_a_duplicate_road_identity_or_direction_is_refused(self):
        self._rejected(
            [
                _document(
                    _THIRD.replace(
                        "  - source: path\n    destination: plaza\n    direction: w",
                        "  - source: plaza\n    destination: path\n    direction: e",
                    )
                )
            ],
            "duplicate_outgoing_direction",
        )

    def test_an_invalid_wilderness_gate_set_is_refused(self):
        two_gates = _THIRD.replace(
            "  gates:\n    - return_direction: n\n      destination_node: plaza",
            "  gates:\n"
            "    - return_direction: n\n"
            "      destination_node: plaza\n"
            "    - return_direction: s\n"
            "      destination_node: path",
        )
        self._rejected([_document(two_gates)], "exactly one gate")


class SettlementPublicationIsolationTests(unittest.TestCase):
    def test_a_failed_candidate_leaves_the_previous_snapshot_published(self):
        before = map_data.current()
        with self.assertRaises(map_data.SettlementError):
            publish_settlements(
                _build(
                    [
                        _document(
                            _THIRD.replace(
                                "location_ref: village_eolas",
                                "location_ref: t_absent",
                            )
                        )
                    ]
                )
            )
        self.assertIs(map_data.current(), before)

    def test_publication_is_immutable_and_keeps_its_identity(self):
        before = map_data.current()
        with self.assertRaises(TypeError):
            before.graphs["t_absent"] = None
        with self.assertRaises(TypeError):
            before.anchor_placements["t_absent"] = None
        self.assertEqual(runtime.compose_settlements().identity, before.identity)
        self.assertIs(map_data.current(), before)

    def test_reading_before_publication_raises(self):
        from world.maps.published import PublishedView

        saved = clear_published_map_world()
        try:
            with self.assertRaises(map_data.SettlementNotLoaded):
                len(PublishedView("graphs"))
            with self.assertRaises(map_data.SettlementNotLoaded):
                map_data.current()
        finally:
            restore_published_map_world(saved)
