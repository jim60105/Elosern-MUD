"""Contract test: the road parameters and the frozen road artifact format.

The authored ``content/maps/road_network.yaml`` document joins the shared source
set as an optional singleton: a world without it loads unchanged, and a supplied
one is validated with no default substitution.

The artifact itself is frozen data read by the offline generator and, later, by
the game. Encoding, decoding, metadata and freshness therefore live in the
standard-library-only ``elosern_map_core.roads_codec``: decoding must work with
the generation extra absent, so a stale artifact is reported instead of
silently recomputed. That claim is only meaningful in a fresh interpreter with
the forbidden namespaces blocked before they are imported, so it runs in its own
subprocess.

Requirement annotations belong to the archive sync: the delta requirements are
not in ``openspec/specs`` yet, so tests here carry none.
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

from elosern_map_core.authoring import load_authoring_world
from elosern_map_core.diagnostics import AuthoringError
from elosern_map_core.elevation_codec import elevation_source_signature
from elosern_map_core.partition_codec import partition_source_signature
from elosern_map_core.roads_codec import (
    FORMAT_VERSION,
    ROAD_ALGORITHM_VERSION,
    RoadDocumentError,
    RoadMetadata,
    decode_road_network,
    encode_road_document,
    read_road_metadata,
    road_fingerprint,
    road_freshness,
    road_source_signature,
)
from elosern_map_core.schema import LOCATION_KINDS
from elosern_map_core.sources import SourceDocument, make_source_document
from elosern_map_core.terrain import REGION_KEYS

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_TESTS = REPO_ROOT / "packages" / "map-core" / "tests"
ROAD_PATH = "content/maps/road_network.yaml"

if str(PACKAGE_TESTS) not in sys.path:
    sys.path.insert(0, str(PACKAGE_TESTS))

import authoring_fixtures as fixtures  # noqa: E402

#: A synthetic region key: never a shipped region name.
REGION_A = "region_a"


def road_network_data(**overrides) -> dict:
    """One valid synthetic road parameter document."""
    data = {
        "version": 1,
        "kind": "road_network",
        "id": "road_network",
        "node_kinds": sorted(LOCATION_KINDS)[:2],
        "forbidden_regions": [],
        "slope_factor_per_band": 0.15,
        "noise_amplitude": 0.1,
        "noise_wavelength_cells": 8,
        "noise_seed": 7,
        "detour_limit": 1.5,
        "reuse_factor": 0.5,
    }
    data.update(overrides)
    return data


def _road_source(**overrides) -> SourceDocument:
    return make_source_document(ROAD_PATH, fixtures.yaml_text(road_network_data(**overrides)))


def _world(**overrides):
    return load_authoring_world(fixtures.source_documents() + (_road_source(**overrides),))


def _network_text(
    *,
    frame_cells: int = 8,
    source_signature: str = "signature",
) -> str:
    return encode_road_document(
        frame_cells=frame_cells,
        source_signature=source_signature,
        nodes=["bravo", "alpha", "charlie"],
        roads=[
            ("alpha", "charlie", ((0, 0), (1, 0))),
            ("alpha", "bravo", ((2, 0), (2, 1), (3, 1))),
        ],
    )


def _recompute_fingerprint(document: dict) -> None:
    """Re-sign a hand-edited document so only its ordering can be wrong."""
    rows = [
        (
            row["first"],
            row["second"],
            tuple(zip(row["cells"][::2], row["cells"][1::2])),
        )
        for row in document["roads"]
    ]
    document["fingerprint"] = road_fingerprint(document["nodes"], rows)


class RoadParameterDocumentTests(unittest.TestCase):
    def test_invalid_content_is_rejected(self):
        cases = (
            ({"mystery": 1}, "unknown_field", "mystery"),
            ({"node_kinds": ["castle"]}, "invalid_field_value", "node_kinds[0]"),
            ({"reuse_factor": 2.0}, "invalid_field_value", "reuse_factor"),
        )
        for overrides, code, field_path in cases:
            with self.subTest(code=code, overrides=overrides):
                with self.assertRaises(AuthoringError) as captured:
                    _world(**overrides)
                diagnostics = captured.exception.diagnostics
                matched = [item for item in diagnostics if item.code == code]
                self.assertTrue(
                    any(item.field_path == field_path for item in matched),
                    [item.field_path for item in diagnostics],
                )
                naming = next(item for item in matched if item.field_path == field_path)
                self.assertEqual(naming.category, "structure")
                self.assertEqual(naming.relative_path, ROAD_PATH)

    def test_unknown_forbidden_region_is_rejected(self):
        with self.assertRaises(AuthoringError) as captured:
            _world(forbidden_regions=["no_such_region"])
        diagnostic = next(
            item
            for item in captured.exception.diagnostics
            if item.code == "unknown_road_region"
        )
        self.assertEqual(diagnostic.category, "structure")
        self.assertEqual(diagnostic.field_path, "forbidden_regions")
        self.assertEqual(diagnostic.object_id, "no_such_region")
        self.assertEqual(diagnostic.relative_path, ROAD_PATH)

        declared = sorted(REGION_KEYS)[0]
        world = _world(forbidden_regions=[declared])
        self.assertEqual(world.diagnostics, ())
        self.assertEqual(world.road_network.forbidden_regions, (declared,))

    def test_a_missing_field_has_no_default(self):
        data = road_network_data()
        del data["reuse_factor"]
        sources = fixtures.source_documents() + (
            make_source_document(ROAD_PATH, fixtures.yaml_text(data)),
        )
        with self.assertRaises(AuthoringError) as captured:
            load_authoring_world(sources)
        diagnostic = next(
            item
            for item in captured.exception.diagnostics
            if item.code == "missing_field"
        )
        self.assertEqual(diagnostic.field_path, "reuse_factor")
        self.assertEqual(diagnostic.relative_path, ROAD_PATH)

    def test_an_absent_document_loads(self):
        world = fixtures.loaded_world()
        self.assertEqual(world.diagnostics, ())
        self.assertIsNone(world.road_network)
        self.assertNotIn(
            "missing_document", {item.code for item in world.diagnostics}
        )

        supplied = _world()
        self.assertEqual(supplied.diagnostics, ())
        road = supplied.road_network
        self.assertIsNotNone(road)
        self.assertEqual(road.node_kinds, tuple(sorted(LOCATION_KINDS)[:2]))
        self.assertEqual(road.forbidden_regions, ())
        self.assertEqual(road.noise_seed, 7)
        self.assertIsInstance(road.slope_factor_per_band, float)
        self.assertIsInstance(road.detour_limit, float)
        self.assertIsInstance(road.reuse_factor, float)

    def test_tuning_leaves_other_artifacts_current(self):
        baseline = _world(detour_limit=1.5)
        tuned = _world(detour_limit=1.7)
        self.assertEqual(baseline.partition_signature, tuned.partition_signature)
        self.assertEqual(
            partition_source_signature(baseline.documents),
            partition_source_signature(tuned.documents),
        )
        self.assertNotEqual(baseline.fingerprint, tuned.fingerprint)
        self.assertEqual(
            baseline.continent.fingerprint, tuned.continent.fingerprint
        )
        self.assertEqual(
            elevation_source_signature(baseline.continent.fingerprint),
            elevation_source_signature(tuned.continent.fingerprint),
        )


class RoadCodecTests(unittest.TestCase):
    def _sources(self) -> dict[str, str]:
        return {
            "content/maps/continent.yaml": "continent-1",
            "content/maps/locations.yaml": "locations-1",
            "content/maps/settlements/demo_map.yaml": "settlement-1",
            ROAD_PATH: "road-1",
        }

    def _metadata(self, signature: str) -> RoadMetadata:
        return RoadMetadata(
            format_version=FORMAT_VERSION,
            algorithm_version=ROAD_ALGORITHM_VERSION,
            source_signature=signature,
            fingerprint="0" * 64,
        )

    def test_round_trip_is_canonical(self):
        text = _network_text()
        network = decode_road_network(text)
        self.assertEqual(network.nodes, ("alpha", "bravo", "charlie"))
        self.assertEqual(
            network.roads,
            (
                ("alpha", "bravo", ((2, 0), (2, 1), (3, 1))),
                ("alpha", "charlie", ((0, 0), (1, 0))),
            ),
        )
        self.assertEqual(
            network.cells,
            frozenset({(0, 0), (1, 0), (2, 0), (2, 1), (3, 1)}),
        )
        metadata = read_road_metadata(text)
        self.assertEqual(metadata.fingerprint, network.fingerprint)
        self.assertEqual(metadata.algorithm_version, ROAD_ALGORITHM_VERSION)
        self.assertEqual(metadata.source_signature, "signature")
        self.assertEqual(
            encode_road_document(
                frame_cells=8,
                source_signature="signature",
                nodes=network.nodes,
                roads=network.roads,
            ),
            text,
        )
        # One road per line, so a diff of the artifact names the changed road.
        self.assertEqual(
            sum(1 for line in text.splitlines() if line.startswith("    {")), 2
        )

    def test_changed_input_reads_as_stale(self):
        sources = self._sources()
        speeds = {REGION_A: 1000}
        signature = road_source_signature(
            sources, elevation_fingerprint="elevation-1", region_speeds=speeds
        )
        metadata = self._metadata(signature)
        self.assertTrue(road_freshness(metadata, signature).current)

        for path in tuple(sources):
            with self.subTest(changed=path):
                changed = {**sources, path: sources[path] + "-changed"}
                changed_signature = road_source_signature(
                    changed, elevation_fingerprint="elevation-1", region_speeds=speeds
                )
                self.assertNotEqual(changed_signature, signature)
                self.assertFalse(road_freshness(metadata, changed_signature).current)

        raised_elevation = road_source_signature(
            sources, elevation_fingerprint="elevation-2", region_speeds=speeds
        )
        self.assertNotEqual(raised_elevation, signature)
        self.assertFalse(road_freshness(metadata, raised_elevation).current)

        repriced = road_source_signature(
            sources,
            elevation_fingerprint="elevation-1",
            region_speeds={REGION_A: 1250},
        )
        self.assertNotEqual(repriced, signature)
        self.assertFalse(road_freshness(metadata, repriced).current)

        self.assertFalse(
            road_freshness(
                self._metadata(signature), signature, ROAD_ALGORITHM_VERSION + 1
            ).current
        )

    def test_unrelated_sources_stay_current(self):
        sources = self._sources()
        signature = road_source_signature(
            sources,
            elevation_fingerprint="elevation-1",
            region_speeds={REGION_A: 1000},
        )
        unrelated = {
            **sources,
            "content/maps/interiors/demo_interior.yaml": "interior-2",
            "content/maps/districts.yaml": "districts-2",
        }
        unchanged = road_source_signature(
            unrelated,
            elevation_fingerprint="elevation-1",
            region_speeds={REGION_A: 1000},
        )
        self.assertEqual(unchanged, signature)
        self.assertTrue(road_freshness(self._metadata(signature), unchanged).current)

    def test_a_missing_signature_is_never_current(self):
        metadata = self._metadata("signature")
        self.assertFalse(road_freshness(metadata, None).current)
        self.assertFalse(road_freshness(metadata, "").current)

    def test_corrupt_artifact_is_rejected(self):
        document = json.loads(_network_text())

        def _set(path, value):
            def mutate(candidate):
                candidate[path] = value

            return mutate

        def _mutate_road(mutate):
            def apply(candidate):
                mutate(candidate["roads"][0])

            return apply

        cases = (
            ("version", _set("version", 2)),
            ("algorithm version", _set("algorithm_version", 0)),
            ("missing signature", _set("source_signature", None)),
            ("missing frame", _set("frame_cells", 0)),
            ("fingerprint", _set("fingerprint", "0" * 64)),
            ("nodes", _set("nodes", [1, 2])),
            ("roads", _set("roads", {})),
            ("odd cells", _mutate_road(_set("cells", [0, 0, 1]))),
            ("empty cells", _mutate_road(_set("cells", []))),
            ("cell outside frame", _mutate_road(_set("cells", [8, 0, 9, 0]))),
            ("boolean coordinate", _mutate_road(_set("cells", [True, 0, 1, 0]))),
            ("non-string endpoint", _mutate_road(_set("first", 1))),
            ("unordered endpoints", _mutate_road(_set("first", "zulu"))),
            ("road not a mapping", _set("roads", ["alpha"])),
        )
        for name, mutate in cases:
            with self.subTest(corrupt=name):
                candidate = copy.deepcopy(document)
                mutate(candidate)
                with self.assertRaises(RoadDocumentError):
                    decode_road_network(candidate)

        unsorted_nodes = copy.deepcopy(document)
        unsorted_nodes["nodes"] = list(reversed(unsorted_nodes["nodes"]))
        _recompute_fingerprint(unsorted_nodes)
        with self.assertRaises(RoadDocumentError):
            decode_road_network(unsorted_nodes)

        unsorted_roads = copy.deepcopy(document)
        unsorted_roads["roads"] = list(reversed(unsorted_roads["roads"]))
        _recompute_fingerprint(unsorted_roads)
        with self.assertRaises(RoadDocumentError):
            decode_road_network(unsorted_roads)

        with self.assertRaises(RoadDocumentError):
            decode_road_network("{ not json")
        with self.assertRaises(RoadDocumentError):
            decode_road_network("[]")
        with self.assertRaises(RoadDocumentError):
            encode_road_document(
                frame_cells=8,
                source_signature="signature",
                nodes=["bravo", "charlie"],
                roads=[("charlie", "bravo", ((0, 0),))],
            )
        for name, kwargs in (
            ("boolean frame", {"frame_cells": True}),
            ("empty signature", {"source_signature": ""}),
            ("non-string node", {"nodes": [1]}),
            ("out-of-frame cell", {"roads": [("alpha", "charlie", ((8, 0),))]}),
            ("boolean coordinate", {"roads": [("alpha", "charlie", ((True, 0),))]}),
        ):
            with self.subTest(invalid_encode=name):
                arguments = {
                    "frame_cells": 8,
                    "source_signature": "signature",
                    "nodes": ["bravo", "alpha"],
                    "roads": [("alpha", "bravo", ((0, 0),))],
                }
                arguments.update(kwargs)
                with self.assertRaises(RoadDocumentError):
                    encode_road_document(**arguments)


def run_with_numpy_blocked(source: str) -> subprocess.CompletedProcess:
    """Run ``source`` in a fresh interpreter with the generation extra blocked."""
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}
    env.pop("DJANGO_SETTINGS_MODULE", None)
    return subprocess.run(
        [sys.executable, "-c", source],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )


_INDEPENDENCE_PROBE = textwrap.dedent(
    """
    import json
    import sys

    BLOCKED = {"numpy", "scipy", "tools", "elosern_map_core.roads"}

    class Blocker:
        def find_spec(self, name, path=None, target=None):
            root = (
                name
                if name == "elosern_map_core.roads"
                else name.split(".")[0]
            )
            if root in BLOCKED:
                raise AssertionError(f"road codec imported forbidden namespace {name}")
            return None

    sys.meta_path.insert(0, Blocker())
    loaded = {name.split(".")[0] for name in sys.modules}
    assert not (BLOCKED & loaded), sorted(BLOCKED & loaded)

    from elosern_map_core.roads_codec import (
        ROAD_ALGORITHM_VERSION,
        decode_road_network,
        encode_road_document,
        read_road_metadata,
        road_freshness,
        road_source_signature,
    )

    signature = road_source_signature(
        {
            "content/maps/continent.yaml": "c",
            "content/maps/locations.yaml": "l",
            "content/maps/settlements/demo_map.yaml": "s",
            "content/maps/road_network.yaml": "r",
        },
        elevation_fingerprint="e",
        region_speeds={"region_a": 1000, "region_b": 2500},
    )
    text = encode_road_document(
        frame_cells=4,
        source_signature=signature,
        nodes=["alpha", "bravo"],
        roads=[("alpha", "bravo", ((0, 0), (1, 0)))],
    )
    network = decode_road_network(text)
    assert network.cells == frozenset({(0, 0), (1, 0)})
    metadata = read_road_metadata(text)
    assert metadata.algorithm_version == ROAD_ALGORITHM_VERSION
    assert road_freshness(metadata, signature).current is True
    assert road_freshness(metadata, signature + "x").current is False
    leaked = sorted(
        name
        for name in sys.modules
        if name.split(".")[0] in {"numpy", "scipy", "tools"}
        or name == "elosern_map_core.roads"
    )
    print(json.dumps(leaked))
    """
)


class IndependentDecodingTests(unittest.TestCase):
    def test_the_codec_decodes_and_reports_freshness_without_numpy_or_scipy(self):
        result = run_with_numpy_blocked(_INDEPENDENCE_PROBE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "[]")


if __name__ == "__main__":
    unittest.main()
