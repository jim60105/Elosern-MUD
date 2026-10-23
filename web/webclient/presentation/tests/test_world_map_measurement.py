"""Data-contract test: the shipped continental geography fits the measured world-map bound.

transport-world-map-panel measures the real ``world_map`` payload assembled
by ``tools.world_map_payload`` from the frozen district partition, the
derived borders, the waterways, the anchors and the harbours. This module
pins that the measured cases are schema-valid, above one generic 64 KB
frame (so the scoped allowance is load-bearing), and inside the selected
``WORLD_MAX_BYTES`` with headroom, and that the intact frames pass the
scoped world-map envelope check.
"""

import unittest

from tools import world_map_payload
from tools.spec_traceability import covers_requirement

from web.webclient.presentation import map_panels
from web.webclient.presentation.map_panels import check_world_map_envelope, validate_world_map
from web.webclient.presentation.protocol import MAX_CANONICAL_JSON_BYTES

TRANSPORT_REQUIREMENT = "webclient-oob-protocol::continental-map-transport-is-measured-end-to-end"


def _frame(body: dict) -> dict:
    return {
        "protocol_version": 1,
        "presentation_epoch": "w" * 22,
        "revision": 2,
        "mode": "exploration",
        "panels": {"world_map": body},
        "layout_version": 1,
        "server_time": {
            "year": 1, "season_index": 0, "season_label": "春",
            "day_in_season": 1, "hour": 0, "minute": 0, "second": 0,
        },
    }


class WorldMapMeasurementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.representative = world_map_payload.representative_payload()
        cls.worst = world_map_payload.worst_payload()

    @covers_requirement(TRANSPORT_REQUIREMENT)
    def test_measured_payloads_are_valid_and_canonical(self):
        for name, body in (("representative", self.representative), ("worst", self.worst)):
            with self.subTest(case=name):
                validated = validate_world_map(body)
                # The tool emits integral numbers as integers, so its bytes are
                # what the browser re-serializes after decoding.
                self.assertEqual(world_map_payload.canonical_bytes(validated), world_map_payload.canonical_bytes(body))
                self.assertEqual(check_world_map_envelope(_frame(body)), validated)

    @covers_requirement(TRANSPORT_REQUIREMENT)
    def test_real_continental_data_exceeds_one_frame_and_fits_the_bound(self):
        representative = len(world_map_payload.canonical_bytes(self.representative))
        worst = len(world_map_payload.canonical_bytes(self.worst))
        self.assertGreater(representative, MAX_CANONICAL_JSON_BYTES)
        self.assertGreater(worst, representative)
        # The bound keeps at least a quarter of headroom over the measured
        # worst case for the presenter's terrain washes and roads.
        self.assertLessEqual(worst * 5 // 4, map_panels.WORLD_MAX_BYTES)

    @covers_requirement(TRANSPORT_REQUIREMENT)
    def test_worst_case_lights_every_district_and_fills_every_cap(self):
        districts = self.worst["districts"]
        self.assertEqual(len(districts), len(world_map_payload.district_keys()))
        self.assertTrue(all(row["lit"] for row in districts))
        runs = sum(len(row[1]) for row in self.worst["trail"]["rows"])
        self.assertEqual(runs, map_panels.TRAIL_MAX_RUNS)
        self.assertEqual(len(self.worst["quest_markers"]), map_panels.WORLD_MAX_QUEST_MARKERS)
        lit = [row for row in self.representative["districts"] if row["lit"]]
        self.assertEqual(len(lit), world_map_payload.REPRESENTATIVE_LIT_DISTRICTS)
