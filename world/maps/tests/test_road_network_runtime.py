"""Adoption of the committed road network and the published road-cell lookup.

The runtime never computes a road: it accepts the committed artifact only when
its source signature matches the candidate's inputs, publishes the decoded
network with the map bundle, and answers every road lookup from that bundle.
"""

from __future__ import annotations

import unittest
from dataclasses import replace
from unittest import mock

from elosern_map_core.roads_codec import (
    FORMAT_VERSION,
    ROAD_ALGORITHM_VERSION,
    RoadDocumentError,
    RoadMetadata,
    RoadNetwork,
)
from tools.spec_traceability import covers_requirement
from world.maps import bootstrap, road_network, runtime
from world.tests.geography_fixture import (
    clear_published_map_world,
    publish_geography,
    publish_shipped_map_world,
)


def _network(fingerprint: str, cells) -> RoadNetwork:
    """One synthetic network: never a shipped road cell."""
    return RoadNetwork(
        fingerprint=fingerprint,
        nodes=(),
        roads=(),
        cells=frozenset(tuple(cell) for cell in cells),
    )


class RoadNetworkAdoptionTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self._saved_bundle = runtime._BUNDLE
        publish_shipped_map_world()

    def tearDown(self):
        if self._saved_bundle is not None:
            runtime.publish(self._saved_bundle)
        else:
            clear_published_map_world()
        super().tearDown()

    @covers_requirement(
        "wilderness-roads::adoption-requires-a-current-road-network"
    )
    def test_a_stale_artifact_rejects_the_candidate_and_keeps_the_bundle(self):
        baseline = runtime.current()
        stale = RoadMetadata(
            format_version=FORMAT_VERSION,
            algorithm_version=ROAD_ALGORITHM_VERSION,
            source_signature="t_stale_signature",
            fingerprint="t_artifact_fingerprint",
        )

        with mock.patch.object(
            road_network, "artifact_metadata", return_value=stale
        ):
            with self.assertRaises(runtime.MapWorldError) as caught:
                runtime.adopt()

        self.assertIn("tools.road_network", str(caught.exception))
        self.assertIs(runtime.current(), baseline)

    @covers_requirement(
        "wilderness-roads::adoption-requires-a-current-road-network"
    )
    def test_a_missing_or_corrupt_artifact_rejects_the_candidate(self):
        baseline = runtime.current()
        committed = road_network.artifact_metadata()

        with self.subTest(failure="missing"):
            with mock.patch.object(
                road_network,
                "artifact_metadata",
                side_effect=FileNotFoundError("t_missing_artifact"),
            ):
                with self.assertRaises(runtime.MapWorldError) as caught:
                    runtime.adopt()
            self.assertIn("rejected", str(caught.exception))
            self.assertIs(runtime.current(), baseline)

        with self.subTest(failure="corrupt"):
            with mock.patch.object(
                road_network, "artifact_metadata", return_value=committed
            ), mock.patch.object(
                road_network,
                "source_signature",
                return_value=committed.source_signature,
            ), mock.patch.object(
                road_network,
                "frozen_network",
                side_effect=RoadDocumentError("t_corrupt_artifact"),
            ):
                with self.assertRaises(runtime.MapWorldError) as caught:
                    runtime.adopt()
            self.assertIn("rejected", str(caught.exception))
            self.assertIs(runtime.current(), baseline)

    @covers_requirement(
        "wilderness-roads::adoption-requires-a-current-road-network"
    )
    def test_a_candidate_without_a_road_document_is_not_current(self):
        baseline = runtime.current()
        composed = runtime.compose()
        without_document = replace(composed.world, road_network=None)
        self.assertIsNone(
            road_network.source_signature(without_document, "t_elevation")
        )

        with mock.patch.object(
            runtime,
            "compose",
            return_value=replace(composed, world=without_document),
        ):
            with self.assertRaises(runtime.MapWorldError) as caught:
                runtime.adopt()

        self.assertIn("not current", str(caught.exception))
        self.assertIn("tools.road_network", str(caught.exception))
        self.assertIs(runtime.current(), baseline)

    @covers_requirement(
        "wilderness-roads::adoption-requires-a-current-road-network"
    )
    def test_an_interior_edit_keeps_the_artifact_current(self):
        composed = runtime.compose()
        fingerprints = dict(composed.world.fingerprints)
        fingerprints["content/maps/interiors/t_extra.yaml"] = "f" * 64
        edited = replace(composed.world, fingerprints=fingerprints)

        with mock.patch.object(
            runtime, "compose", return_value=replace(composed, world=edited)
        ):
            adopted = runtime.adopt()

        self.assertIs(runtime.current(), adopted)
        self.assertIs(road_network.current(), adopted.roads)
        self.assertTrue(
            runtime.road_freshness_for(edited, adopted.elevation.fingerprint).current
        )

    @covers_requirement(
        "wilderness-roads::adoption-requires-a-current-road-network"
    )
    def test_offline_producers_stay_ungated(self):
        with mock.patch.object(
            road_network,
            "artifact_metadata",
            side_effect=AssertionError("an offline producer read the road artifact"),
        ), mock.patch.object(
            road_network,
            "frozen_network",
            side_effect=AssertionError("an offline producer read the road artifact"),
        ):
            composed = runtime.compose()
            published = runtime.preview(composed)

        self.assertIs(published.roads, None)
        self.assertEqual(road_network.road_cells(), frozenset())


class RoadCellLookupTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self._saved_bundle = runtime._BUNDLE
        publish_shipped_map_world()

    def tearDown(self):
        if self._saved_bundle is not None:
            runtime.publish(self._saved_bundle)
        else:
            clear_published_map_world()
        super().tearDown()

    @covers_requirement(
        "wilderness-roads::road-cell-lookup-reads-the-published-bundle"
    )
    def test_lookup_reads_the_published_bundle(self):
        network = _network("t_published", {(3, 4), (4, 4)})

        runtime.publish(replace(runtime.current(), roads=network))

        self.assertIs(road_network.current(), network)
        self.assertTrue(road_network.is_road_cell((3, 4)))
        self.assertTrue(road_network.is_road_cell((4, 4)))
        self.assertFalse(road_network.is_road_cell((9, 9)))
        self.assertEqual(road_network.road_cells(), frozenset({(3, 4), (4, 4)}))

        runtime.publish(replace(runtime.current(), roads=None))

        self.assertIsNone(road_network.current())
        self.assertFalse(road_network.is_road_cell((3, 4)))
        self.assertEqual(road_network.road_cells(), frozenset())

    @covers_requirement(
        "wilderness-roads::road-cell-lookup-reads-the-published-bundle"
    )
    def test_a_failed_synchronization_restores_the_network(self):
        first = _network("t_first", {(1, 1), (2, 2)})
        baseline = runtime.publish(replace(runtime.current(), roads=first))
        second = _network("t_second", {(5, 5)})

        with mock.patch.object(
            road_network, "frozen_network", return_value=second
        ):
            adopted = runtime.adopt()
        self.assertIs(runtime.current(), adopted)
        self.assertIs(road_network.current(), second)

        with mock.patch.object(
            bootstrap, "sync_limbo", side_effect=RuntimeError("t_sync_failure")
        ):
            with self.assertRaises(RuntimeError):
                runtime.synchronize()

        self.assertIs(runtime.current(), baseline)
        self.assertIs(road_network.current(), first)
        self.assertTrue(road_network.is_road_cell((1, 1)))
        self.assertFalse(road_network.is_road_cell((5, 5)))

    @covers_requirement(
        "wilderness-roads::road-cell-lookup-reads-the-published-bundle"
    )
    def test_a_bundle_identity_includes_its_network(self):
        one = replace(runtime.current(), roads=_network("t_one", {(1, 1)}))
        two = replace(runtime.current(), roads=_network("t_two", {(2, 2)}))

        self.assertNotEqual(one.identity, two.identity)

    def test_a_synthetic_geography_publication_clears_the_road_cells(self):
        from dataclasses import replace as replace_bundle

        before = runtime.current()
        runtime.publish(
            replace_bundle(
                before, roads=_network("t_before_publication", {(1, 1)})
            )
        )
        self.assertIn((1, 1), road_network.road_cells())

        publish_geography(before.geography)

        self.assertEqual(road_network.road_cells(), frozenset())
        self.assertFalse(road_network.is_road_cell((0, 0)))

    def test_a_synthetic_patching_scope_applies_geography_without_roads(self):
        from world.tests.synthetic_data.patching import synthetic_registries

        with synthetic_registries("regions"):
            self.assertEqual(road_network.road_cells(), frozenset())
            self.assertFalse(road_network.is_road_cell((0, 0)))


if __name__ == "__main__":
    unittest.main()
