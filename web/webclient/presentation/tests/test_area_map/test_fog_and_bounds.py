"""The on-demand ``area_map`` presenter and the ``map.view`` action (fog and bounds)."""

import subprocess
import unittest
from tools.spec_traceability import covers_requirement
from web.webclient.presentation.area_map import bearing_and_distance, fog_of_war
from web.webclient.presentation.map_panels import AREA_MAX_BYTES, validate_area_map
from web.webclient.presentation.map_parts import decode_map_parts, encode_map_parts
from web.webclient.presentation.protocol import ProtocolValidationError, json_byte_size


from ._support import ROOT, NODE_TEST, _undirected, _largest_grid_body

class FogOfWarTests(unittest.TestCase):
    """known = visited ∪ adjacent(visited); roads need a visited end."""

    # A line a-b-c-d-e-f with a side branch c-x-y.
    GRAPH = _undirected(
        [("t_a", "t_b"), ("t_b", "t_c"), ("t_c", "t_d"), ("t_d", "t_e"), ("t_e", "t_f"), ("t_c", "t_x"), ("t_x", "t_y")]
    )

    @covers_requirement(
        "webclient-area-map::area-maps-reveal-visited-nodes-and-one-step-frontier-across-all-layers"
    )
    def test_whole_visited_graph_and_one_step_frontier(self):
        # Visited far beyond two hops from the current node.
        known, visited, edges = fog_of_war(self.GRAPH, {"t_a", "t_b", "t_c", "t_d", "t_e"}, "t_a")
        self.assertEqual(set(known), {"t_a", "t_b", "t_c", "t_d", "t_e", "t_f", "t_x"})
        self.assertEqual(visited, {"t_a", "t_b", "t_c", "t_d", "t_e"})
        self.assertNotIn("t_y", known, "an unseen deeper branch is never emitted")
        self.assertIn(("t_c", "t_x"), edges)
        self.assertIn(("t_e", "t_f"), edges)

    @covers_requirement(
        "webclient-area-map::area-maps-reveal-visited-nodes-and-one-step-frontier-across-all-layers"
    )
    def test_seen_to_seen_roads_are_never_emitted(self):
        graph = _undirected([("t_a", "t_b"), ("t_a", "t_c"), ("t_b", "t_c")])
        known, _, edges = fog_of_war(graph, set(), "t_a")
        self.assertEqual(set(known), {"t_a", "t_b", "t_c"})
        self.assertEqual(set(edges), {("t_a", "t_b"), ("t_a", "t_c")})

    def test_current_counts_as_visited_and_foreign_visits_are_ignored(self):
        known, visited, _ = fog_of_war(self.GRAPH, {"t_elsewhere"}, "t_f")
        self.assertEqual(visited, {"t_f"})
        self.assertEqual(set(known), {"t_e", "t_f"})

    def test_edges_are_unique_unordered_pairs(self):
        _, _, edges = fog_of_war(self.GRAPH, set(self.GRAPH), "t_a")
        self.assertEqual(len(edges), len({frozenset(edge) for edge in edges}))
        self.assertEqual(len(edges), 7)

class BearingTests(unittest.TestCase):
    @covers_requirement(
        "webclient-area-map::area-commission-markers-distinguish-same-map-identity-from-elsewhere"
    )
    def test_bearing_is_clockwise_from_north_and_wraps_after_rounding(self):
        self.assertEqual(bearing_and_distance((10, 10), (10, 20), 1), (0.0, 10.0))
        self.assertEqual(bearing_and_distance((10, 10), (20, 10), 1), (90.0, 10.0))
        self.assertEqual(bearing_and_distance((10, 10), (10, 0), 2), (180.0, 20.0))
        self.assertEqual(bearing_and_distance((10, 10), (0, 10), 1), (270.0, 10.0))
        # 359.97 degrees rounds to 360.0 and must wrap to 0.0.
        bearing, _ = bearing_and_distance((0, 0), (-1, 2000), 1)
        self.assertEqual(bearing, 0.0)
        self.assertEqual(bearing_and_distance((5, 5), (5, 5), 1), (0.0, 0.0))

class AreaBoundsTests(unittest.TestCase):
    @covers_requirement(
        "webclient-area-map::area-maps-reveal-visited-nodes-and-one-step-frontier-across-all-layers"
    )
    def test_largest_supported_graph_fits_and_travels_in_parts(self):
        body = validate_area_map(_largest_grid_body())
        size = json_byte_size(body)
        self.assertLess(size, AREA_MAX_BYTES)
        parts = encode_map_parts("area_map", body)
        self.assertGreater(len(parts), 1)
        self.assertEqual(decode_map_parts("area_map", parts), body)

    def test_ceilings_reject_rather_than_truncate(self):
        body = _largest_grid_body()
        body["nodes"].append(dict(body["nodes"][-1], id="grid:t_large:1:1", x=1, y=1))
        with self.assertRaises(ProtocolValidationError):
            validate_area_map(body)

class AreaMapNodeEvidenceTests(unittest.TestCase):
    @covers_requirement(
        "webclient-area-map::area-maps-reveal-visited-nodes-and-one-step-frontier-across-all-layers"
    )
    @covers_requirement(
        "wilderness-area-map-reveal::wilderness-runs-disclose-only-revealed-terrain"
    )
    def test_browser_area_map_validator_suite_passes(self):
        result = subprocess.run(
            ["node", "--test", NODE_TEST], cwd=ROOT, capture_output=True, text=True, timeout=300
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(result.stdout, r"(?m)^\S* ?fail 0$")
