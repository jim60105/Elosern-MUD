"""Data-contract test: wilderness entry data contract
Registry v2 self-consistency and validation checks (wilderness-anchor-footprint)."""

import unittest
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.lore.wilderness_entry import (
    WILDERNESS_ENTRY_REGISTRY,
    WildernessEntryPoint,
    WildernessGate,
    validate_wilderness_entries,
)

CAPITAL = WILDERNESS_ENTRY_REGISTRY["capital_altoria"]


def _point_entry(anchor_key="capital_altoria", anchor=(120, 120), gates=None):
    """A throwaway point-shape (cave) entry for helper/validation tests."""
    if gates is None:
        gates = (WildernessGate("n", (3, 0), "capital_altoria"),)
    return WildernessEntryPoint(anchor_key, ("#",), anchor, gates)


class WildernessEntryRegistryShapeTests(unittest.TestCase):
    @covers_requirement(
        "village-ciaran-map::the-village-has-a-wilderness-footprint-disjoint-from-every-other-settlement"
    )
    @covers_requirement(
        "wilderness-gateway::wilderness-entry-registry-links-a-grid-placed-anchor-to-an-authored-wilderness-footprint-and-gates"
    )
    def test_registry_has_two_v2_entries_keyed_by_settlement(self):
        self.assertEqual(
            list(WILDERNESS_ENTRY_REGISTRY),
            ["capital_altoria", "village_ciaran"],
        )
        self.assertEqual(CAPITAL.anchor_key, "capital_altoria")
        self.assertEqual(CAPITAL.shape, ("#####",) * 5)
        self.assertEqual(CAPITAL.origin_xy, (58, 98))
        self.assertEqual(
            [(gate.return_direction, gate.grid_xy, gate.z_map_key) for gate in CAPITAL.gates],
            [("n", (3, 0), "capital_altoria"), ("w", (6, 3), "capital_altoria")],
        )
        village = WILDERNESS_ENTRY_REGISTRY["village_ciaran"]
        self.assertEqual(village.anchor_key, "village_ciaran")
        self.assertLess(village.hash_cell_count, CAPITAL.hash_cell_count)
        self.assertEqual(
            [(gate.return_direction, gate.grid_xy, gate.z_map_key) for gate in village.gates],
            [("n", (0, 1), "village_ciaran")],
        )
        # The village footprint is placed well clear of the capital's mask.
        self.assertFalse(village.footprint_cells & CAPITAL.footprint_cells)

    @covers_requirement(
        "wilderness-gateway::wilderness-entry-registry-links-a-grid-placed-anchor-to-an-authored-wilderness-footprint-and-gates"
    )
    def test_village_derived_geometry_matches_the_authored_mask(self):
        village = WILDERNESS_ENTRY_REGISTRY["village_ciaran"]
        self.assertEqual(village.origin_xy, (39, 139))
        self.assertEqual(village.shape, ("###", "###", "###"))
        self.assertEqual(village.anchor_cell, (40, 140))
        self.assertEqual(village.approach_cell(village.gate_for("n")), (40, 138))
        gate = village.gate_for("n")
        # The gate returns to the village's entrance node on its own map.
        self.assertEqual((gate.grid_xy, gate.z_map_key), ((0, 1), "village_ciaran"))

    @covers_requirement(
        "wilderness-gateway::wilderness-entry-registry-links-a-grid-placed-anchor-to-an-authored-wilderness-footprint-and-gates"
    )
    def test_derived_geometry_matches_the_authored_mask(self):
        self.assertEqual(
            CAPITAL.footprint_cells,
            frozenset((x, y) for x in range(58, 63) for y in range(98, 103)),
        )
        self.assertEqual(CAPITAL.anchor_cell, (60, 100))
        self.assertEqual(CAPITAL.approach_cell(CAPITAL.gate_for("n")), (60, 97))
        self.assertEqual(CAPITAL.approach_cell(CAPITAL.gate_for("w")), (63, 100))
        self.assertFalse(CAPITAL.is_point_shape)

    def test_point_shape_entry_expresses_cave_semantics(self):
        point = _point_entry()
        self.assertTrue(point.is_point_shape)
        self.assertEqual(point.footprint_cells, frozenset())
        self.assertEqual(point.anchor_cell, (120, 120))
        # approach_cell IS the anchor cell for a point-shape gate.
        self.assertEqual(point.approach_cell(point.gates[0]), point.anchor_cell)

    @covers_requirement(
        "wilderness-gateway::wilderness-entry-registry-links-a-grid-placed-anchor-to-an-authored-wilderness-footprint-and-gates"
    )
    def test_every_entrys_anchor_key_exists_in_anchor_placement_registry(self):
        for entry in WILDERNESS_ENTRY_REGISTRY.values():
            self.assertIn(entry.anchor_key, ANCHOR_PLACEMENT_REGISTRY)

    def test_gate_lookup_by_return_direction(self):
        self.assertEqual(CAPITAL.gate_for("n").grid_xy, (3, 0))
        self.assertEqual(CAPITAL.gate_for("w").grid_xy, (6, 3))
        # The capital's second gate is the 東門 since the replan; the old
        # 北門 directions are authored nowhere.
        self.assertIsNone(CAPITAL.gate_for("s"))
        self.assertIsNone(CAPITAL.gate_for("e"))

    @covers_requirement(
        "village-ciaran-map::the-village-has-a-wilderness-footprint-disjoint-from-every-other-settlement"
    )
    def test_gate_identity_is_globally_unique(self):
        keys = set()
        for entry in WILDERNESS_ENTRY_REGISTRY.values():
            for gate in entry.gates:
                pair = (entry.approach_cell(gate), gate.return_direction)
                self.assertNotIn(pair, keys)
                keys.add(pair)


class WildernessEntryValidationTests(unittest.TestCase):
    @covers_requirement(
        "wilderness-gateway::wilderness-entry-registry-authored-data-is-validated-before-persistence"
    )
    def test_shipped_registry_validates(self):
        validate_wilderness_entries()

    @covers_requirement(
        "wilderness-gateway::wilderness-entry-registry-authored-data-is-validated-before-persistence"
    )
    def test_village_gate_validates_against_the_shared_map_assembly(self):
        # The village's gate names z_map_key "village_ciaran", which only the
        # shared map assembly exposes to _iter_map_extents(): if that deferred
        # import still pointed at the capital alone, this would raise
        # "unknown z_map_key" and take the whole lore load down at startup.
        from world.lore.wilderness_entry import _iter_map_extents

        extents = _iter_map_extents()
        self.assertIn("village_ciaran", extents)
        self.assertIn((0, 1), extents["village_ciaran"])
        validate_wilderness_entries()

    def _assert_rejected(self, key, entry, fragment):
        # The probe entry keys its own anchor so the anchor_key rule is not
        # the first rejection it trips; the unknown-anchor probe patches a
        # key absent here on purpose.
        with (
            patch.dict(ANCHOR_PLACEMENT_REGISTRY, {key: ANCHOR_PLACEMENT_REGISTRY["capital_altoria"]}),
            patch.dict(WILDERNESS_ENTRY_REGISTRY, {key: entry}),
        ):
            with self.assertRaises(ValueError) as caught:
                validate_wilderness_entries()
        self.assertIn(fragment, str(caught.exception))

    def _assert_capital_rejected(self, entry, fragment):
        with patch.dict(WILDERNESS_ENTRY_REGISTRY, {"capital_altoria": entry}):
            with self.assertRaises(ValueError) as caught:
                validate_wilderness_entries()
        self.assertIn(fragment, str(caught.exception))

    @covers_requirement(
        "wilderness-gateway::wilderness-entry-registry-authored-data-is-validated-before-persistence"
    )
    def test_malformed_entries_are_each_rejected(self):
        gate = WildernessGate("n", (3, 0), "capital_altoria")
        cases = [
            ("empty mask", "x", WildernessEntryPoint("x", (), (0, 0), (gate,)), "empty mask"),
            (
                "no hash cell",
                "x",
                WildernessEntryPoint("x", ("...",), (10, 10), (gate,)),
                "no '#' cell",
            ),
            (
                "out-of-bounds hash cell",
                "x",
                WildernessEntryPoint("x", ("#", "#"), (0, 224), (gate,)),
                "outside provider rectangle",
            ),
            (
                "disconnected footprint",
                "x",
                WildernessEntryPoint("x", ("###", "...", "###"), (0, 0), (gate,)),
                "not 4-connected",
            ),
            (
                "non-canonical return_direction",
                "x",
                WildernessEntryPoint(
                    "x", ("#####",) * 5, (58, 98), (WildernessGate("q", (3, 0), "capital_altoria"),)
                ),
                "non-canonical return_direction",
            ),
            (
                "duplicated return_direction",
                "x",
                WildernessEntryPoint(
                    "x",
                    ("#####",) * 5,
                    (58, 98),
                    (gate, WildernessGate("n", (6, 3), "capital_altoria")),
                ),
                "duplicated return_direction",
            ),
            (
                "gate face ray leaves the provider rectangle (approach undefined)",
                "x",
                WildernessEntryPoint("x", ("#", "#", "#"), (0, 0), (WildernessGate("e", (3, 0), "capital_altoria"),)),
                "approach cell is undefined",
            ),
            (
                "point shape with zero gates",
                "x",
                WildernessEntryPoint("x", ("#",), (120, 120), ()),
                "exactly one gate",
            ),
            (
                "point shape with two gates",
                "x",
                _point_entry(
                    gates=(
                        WildernessGate("n", (3, 0), "capital_altoria"),
                        WildernessGate("w", (6, 3), "capital_altoria"),
                    )
                ),
                "exactly one gate",
            ),
            (
                "grid_xy outside its map extent",
                "x",
                WildernessEntryPoint(
                    "x", ("#####",) * 5, (150, 150), (WildernessGate("n", (9, 9), "capital_altoria"),)
                ),
                "outside extent",
            ),
            (
                "unknown anchor_key",
                "x",
                _point_entry(anchor_key="ghost_anchor"),
                "ANCHOR_PLACEMENT_REGISTRY",
            ),
        ]
        for label, key, entry, fragment in cases:
            with self.subTest(label):
                self._assert_rejected(key, entry, fragment)

    @covers_requirement(
        "wilderness-gateway::wilderness-entry-registry-authored-data-is-validated-before-persistence"
    )
    def test_malformed_masks_and_colliding_geometry_are_each_rejected(self):
        cases = [
            (
                "ragged mask rows",
                "x",
                WildernessEntryPoint(
                    "x", ("###", "##"), (150, 150), (WildernessGate("n", (3, 0), "capital_altoria"),)
                ),
                "ragged mask",
            ),
            (
                "illegal mask character",
                "x",
                WildernessEntryPoint(
                    "x", ("#X#", "#.#", "#.#"), (150, 150), (WildernessGate("n", (3, 0), "capital_altoria"),)
                ),
                "illegal mask character",
            ),
            (
                "bounding-box midpoint falls on a dot",
                "capital_altoria",
                WildernessEntryPoint(
                    "capital_altoria",
                    ("###", "#.#", "###"),
                    (58, 98),
                    (WildernessGate("n", (3, 0), "capital_altoria"),),
                ),
                "is not a '#' footprint cell",
            ),
            (
                "overlapping footprints",
                "x",
                WildernessEntryPoint(
                    "x", ("#", "#"), (60, 100), (WildernessGate("e", (3, 0), "capital_altoria"),)
                ),
                "footprint overlaps",
            ),
            (
                "footprint contains another entry's gate approach cell",
                "x",
                WildernessEntryPoint(
                    "x", ("#", "#"), (57, 100), (WildernessGate("w", (3, 0), "capital_altoria"),)
                ),
                "lies inside footprint",
            ),
            (
                "point anchor on another entry's gate approach cell",
                "x",
                _point_entry(anchor=(63, 100)),
                "approach cell",
            ),
            (
                "point anchor with a provider-invalid neighbor",
                "x",
                _point_entry(anchor=(0, 0)),
                "provider-invalid neighbor",
            ),
            (
                "two gates sharing one destination room",
                "x",
                WildernessEntryPoint(
                    "x",
                    ("#####",) * 5,
                    (150, 150),
                    (
                        WildernessGate("n", (3, 3), "capital_altoria"),
                        WildernessGate("s", (3, 3), "capital_altoria"),
                    ),
                ),
                "shares destination room",
            ),
        ]
        for label, key, entry, fragment in cases:
            with self.subTest(label):
                if key == "capital_altoria":
                    self._assert_capital_rejected(entry, fragment)
                else:
                    self._assert_rejected(key, entry, fragment)


class WildernessEntryBoundsTests(unittest.TestCase):
    def test_entry_cells_are_within_provider_bounds(self):
        from world.maps.wilderness_provider import WILDERNESS_MAX_X, WILDERNESS_MAX_Y

        for cell in CAPITAL.footprint_cells | {
            CAPITAL.approach_cell(gate) for gate in CAPITAL.gates
        }:
            x, y = cell
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)
            self.assertLessEqual(x, WILDERNESS_MAX_X)
            self.assertLessEqual(y, WILDERNESS_MAX_Y)

    def test_every_entry_has_gate_approach_cells_off_the_south_edge(self):
        # A gate approach cell at y == 0 would have its return exit locked
        # invalid by the contrib's own edge handling; validation's provider-
        # rectangle rule guards this, asserted here for every shipped gate.
        for entry in WILDERNESS_ENTRY_REGISTRY.values():
            for gate in entry.gates:
                self.assertGreater(entry.approach_cell(gate)[1], 0)
