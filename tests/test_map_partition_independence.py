"""Contract test: partition generation is game-free and runtime decoding is extra-free.

The district partition has two deliberately separate halves:

* the offline generator in ``elosern_map_core.partition`` depends on the
  ``generation`` extra (NumPy/SciPy) and must import no game module; and
* runtime decoding, artifact metadata and freshness live in
  ``elosern_map_core.partition_codec`` behind the game adapter
  ``world.maps.district_partition`` and must work with the generation extra
  absent, so a stale artifact is reported instead of silently recomputed.

Both claims are only meaningful in a fresh interpreter with the forbidden
namespaces blocked before they are imported, so every check here runs in its
own subprocess.

Mechanism coverage for the algorithm and the freshness signature lives in
``packages/map-core/tests/test_partition.py``; the shipped artifact and the
runtime lookup are covered by ``world.maps.tests.test_map_district_partition``.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

from elosern_map_core.partition_codec import (
    FORMAT_VERSION,
    PARTITION_ALGORITHM_VERSION,
    PartitionMetadata,
    partition_freshness,
    partition_source_signature,
)
from elosern_map_core.sources import make_source_document
from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[1]

_RUNTIME_PROBE = textwrap.dedent(
    """
    import json
    import sys

    BLOCKED = {"numpy", "scipy", "tools", "elosern_map_core.partition"}

    class Blocker:
        def find_spec(self, name, path=None, target=None):
            root = name if name == "elosern_map_core.partition" else name.split(".")[0]
            if root in BLOCKED:
                raise AssertionError(f"runtime imported forbidden namespace {name}")
            return None

    sys.meta_path.insert(0, Blocker())
    loaded = {name.split(".")[0] for name in sys.modules}
    assert not ({"numpy", "scipy", "tools"} & loaded), sorted(loaded)

    from world.maps import district_partition as adapter

    document = json.loads(adapter.DATA_PATH.read_text(encoding="utf-8"))
    # The land rule is an injectable boundary, so decoding needs no published
    # geography; the exact shipped geography belongs to the data-contract test.
    partition = adapter.decode_partition(document, is_land=lambda cell: True)
    assert partition.district_keys == tuple(document["districts"])
    assert partition.district_at((-1, -1)) is None
    metadata = adapter.artifact_metadata()
    assert metadata.algorithm_version == 1
    assert metadata.source_signature
    freshness = adapter.freshness()
    assert freshness.current is True, freshness
    leaked = sorted(
        name for name in sys.modules
        if name.split(".")[0] in {"numpy", "scipy", "tools"}
        or name == "elosern_map_core.partition"
    )
    print(json.dumps(leaked))
    """
)

_GENERATION_PROBE = textwrap.dedent(
    """
    import json
    import sys

    BLOCKED = {"world", "evennia", "django", "twisted", "typeclasses"}

    class Blocker:
        def find_spec(self, name, path=None, target=None):
            if name.split(".")[0] in BLOCKED:
                raise AssertionError(f"generation imported forbidden namespace {name}")
            return None

    sys.meta_path.insert(0, Blocker())
    loaded = {name.split(".")[0] for name in sys.modules}
    assert not (BLOCKED & loaded), sorted(BLOCKED & loaded)

    import numpy as np

    from elosern_map_core.partition import (
        DistrictSeed,
        PartitionInput,
        compute_partition,
        generate_partition,
    )

    size = 10
    land = np.ones((size, size), dtype=bool)
    inp = PartitionInput(
        size,
        land,
        land.copy(),
        np.ones((size, size), dtype=np.uint8),
        ("a",),
        np.full((size, size), 2, dtype=np.uint8),
        ("plain",),
        (DistrictSeed("only", "voronoi", (0, 0)),),
        tile=5,
        source_signature="probe",
    )
    text = generate_partition(inp)
    document = json.loads(text)
    assert document["source_signature"] == "probe"
    assert document["algorithm_version"] == 1
    assert compute_partition(inp).owner_at((9, 9)) == "only"
    leaked = sorted(
        name for name in sys.modules if name.split(".")[0] in BLOCKED
    )
    print(json.dumps(leaked))
    """
)


_AUTHORING_PARITY_PROBE = textwrap.dedent(
    """
    import json
    import sys
    from pathlib import Path

    BLOCKED = {"world", "evennia", "django", "twisted", "typeclasses", "tools"}

    class Blocker:
        def find_spec(self, name, path=None, target=None):
            if name.split(".")[0] in BLOCKED:
                raise AssertionError(f"authoring input imported forbidden namespace {name}")
            return None

    sys.meta_path.insert(0, Blocker())

    from elosern_map_core import discover_source_documents, load_authoring_world
    from elosern_map_core.partition import generate_partition, partition_input, world_snapshot

    root = Path.cwd()
    world = load_authoring_world(discover_source_documents(root))
    text = generate_partition(partition_input(world_snapshot(world)))
    committed = (root / "world" / "maps" / "data" / "district_partition.json").read_text(encoding="utf-8")
    print(json.dumps(text == committed))
    """
)


def _run_probe(source: str) -> subprocess.CompletedProcess:
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


def _sources() -> list:
    return [
        make_source_document("content/maps/continent.yaml", "continent: 1\n"),
        make_source_document("content/maps/locations.yaml", "locations: 1\n"),
        make_source_document("content/maps/districts.yaml", "districts: 1\n"),
        make_source_document("content/maps/settlements/a.yaml", "settlement: 1\n"),
        make_source_document("content/maps/interiors/a.yaml", "interior: 1\n"),
    ]


class RuntimeWithoutGenerationExtraTests(unittest.TestCase):
    @covers_requirement(
        "map-district-partition::frozen-partition-and-outlines-reproduce-deterministically-offline"
    )
    def test_runtime_decode_and_freshness_work_without_numpy_or_scipy(self):
        result = _run_probe(_RUNTIME_PROBE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "[]")


class GenerationIsGameFreeTests(unittest.TestCase):
    @covers_requirement(
        "map-district-partition::offline-partition-assigns-every-land-cell-once-without-crossing-barriers"
    )
    def test_core_generation_runs_with_every_game_namespace_blocked(self):
        result = _run_probe(_GENERATION_PROBE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "[]")


class AuthoringInputParityTests(unittest.TestCase):
    """The editor's input binding and the game adapter produce one artifact.

    ``world_snapshot`` (the map editor's partition-job input, from the
    authoring documents alone) and ``tools.map_district_partition`` (the
    game's adapter, from the published registries) are two bindings of the
    same seed rules. Over the current sources the authoring binding must
    regenerate the committed artifact byte for byte, so an editor job on
    unchanged sources is a no-op and the two can never drift silently. This
    compares two producers over the same inputs; it records no shipped value.
    """

    @covers_requirement(
        "map-district-partition::frozen-partition-and-outlines-reproduce-deterministically-offline"
    )
    def test_authoring_world_input_regenerates_the_committed_artifact(self):
        result = _run_probe(_AUTHORING_PARITY_PROBE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "true")


class FreshnessSignatureTests(unittest.TestCase):
    def _metadata(self, source_signature: str, algorithm: int) -> PartitionMetadata:
        return PartitionMetadata(
            format_version=FORMAT_VERSION,
            algorithm_version=algorithm,
            source_signature=source_signature,
            fingerprint="0" * 64,
        )

    @covers_requirement(
        "map-district-partition::frozen-partition-and-outlines-reproduce-deterministically-offline"
    )
    def test_only_partition_sources_invalidate_freshness(self):
        baseline = partition_source_signature(_sources())
        self.assertTrue(
            partition_freshness(self._metadata(baseline, PARTITION_ALGORITHM_VERSION), baseline).current
        )
        # An interior-only change is not a partition input.
        interior_only = [
            make_source_document("content/maps/interiors/a.yaml", "interior: 2\n")
            if document.relative_path == "content/maps/interiors/a.yaml"
            else document
            for document in _sources()
        ]
        self.assertEqual(baseline, partition_source_signature(interior_only))
        # A geometry source edit is not.
        geometry_edit = [
            make_source_document("content/maps/continent.yaml", "continent: 2\n")
            if document.relative_path == "content/maps/continent.yaml"
            else document
            for document in _sources()
        ]
        self.assertFalse(
            partition_freshness(
                self._metadata(baseline, PARTITION_ALGORITHM_VERSION),
                partition_source_signature(geometry_edit),
            ).current
        )

    @covers_requirement(
        "map-district-partition::frozen-partition-and-outlines-reproduce-deterministically-offline"
    )
    def test_an_algorithm_version_change_or_missing_source_set_is_stale(self):
        baseline = partition_source_signature(_sources())
        bumped = self._metadata(baseline, PARTITION_ALGORITHM_VERSION + 1)
        self.assertFalse(partition_freshness(bumped, baseline).current)
        self.assertFalse(
            partition_freshness(self._metadata(baseline, PARTITION_ALGORITHM_VERSION), None).current
        )
