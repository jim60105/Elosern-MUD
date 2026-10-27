"""Data-contract test: wilderness entry data contract
Registry v2 self-consistency and validation checks (wilderness-anchor-footprint)."""

import unittest
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from elosern_map_core.references import settlement_node_ref
from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.lore.wilderness_entry import (
    WILDERNESS_ENTRY_REGISTRY,
    WildernessEntryPoint,
    WildernessGate,
    validate_wilderness_entries,
)

CAPITAL = WILDERNESS_ENTRY_REGISTRY["capital_altoria"]


def _point_entry(anchor_key="capital_altoria", anchor=(500, 500), gates=None):
    """A throwaway point-shape (cave) entry for helper/validation tests."""
    if gates is None:
        gates = (WildernessGate("n", CAPITAL.gate_for("n").destination),)
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
        self.assertEqual(CAPITAL.hash_cell_count, 40)
        self.assertEqual(CAPITAL.origin_xy, (857, 1076))
        self.assertEqual(
            [
                (gate.return_direction, gate.z_map_key, gate.destination.object_id)
                for gate in CAPITAL.gates
            ],
            [
                ("n", "capital_altoria", "south_gate"),
                ("w", "capital_altoria", "east_gate"),
            ],
        )
        village = WILDERNESS_ENTRY_REGISTRY["village_ciaran"]
        self.assertEqual(village.anchor_key, "village_ciaran")
        self.assertLess(village.hash_cell_count, CAPITAL.hash_cell_count)
        self.assertTrue(village.is_point_shape)
        self.assertEqual(
            [
                (gate.return_direction, gate.z_map_key, gate.destination.object_id)
                for gate in village.gates
            ],
            [("n", "village_ciaran", "hidden_path")],
        )
        # A point entrance contributes no footprint at all, so it can never
        # collide with the capital's mask or another village-wide obstacle.
        self.assertEqual(village.footprint_cells, frozenset())

    @covers_requirement(
        "wilderness-gateway::wilderness-entry-registry-links-a-grid-placed-anchor-to-an-authored-wilderness-footprint-and-gates"
    )
    def test_village_derived_geometry_matches_the_authored_mask(self):
        village = WILDERNESS_ENTRY_REGISTRY["village_ciaran"]
        self.assertEqual(village.origin_xy, (1340, 1220))
        self.assertEqual(village.shape, ("#",))
        self.assertEqual(village.anchor_cell, (1340, 1220))
        # Point semantics: the approach cell IS the anchor cell, and only the
        # authored direction is the gateway.
        self.assertEqual(village.approach_cell(village.gate_for("n")), (1340, 1220))
        gate = village.gate_for("n")
        # The gate returns to the village's entrance node on its own map.
        self.assertEqual(
            gate.destination,
            settlement_node_ref("village_ciaran", "hidden_path"),
        )

    @covers_requirement(
        "wilderness-gateway::wilderness-entry-registry-links-a-grid-placed-anchor-to-an-authored-wilderness-footprint-and-gates"
    )
    def test_derived_geometry_matches_the_authored_mask(self):
        # The authored mask rows are contract: 40 km² inside a 7x9 km box, the
        # plaza cell as derived anchor, and one exterior approach per gate ray.
        self.assertEqual(
            CAPITAL.shape,
            (
                "#.....#",
                "##...##",
                ".#####.",
                "#######",
                "#######",
                "####..#",
                "#..#.##",
                "####...",
                "..##...",
            ),
        )
        self.assertEqual(CAPITAL.hash_cell_count, 40)
        self.assertEqual(CAPITAL.anchor_cell, (860, 1080))
        self.assertIn(CAPITAL.anchor_cell, CAPITAL.footprint_cells)
        self.assertEqual(
            CAPITAL.footprint_cells,
            frozenset(
                (CAPITAL.origin_xy[0] + col, CAPITAL.origin_xy[1] + row)
                for row, line in enumerate(CAPITAL.shape)
                for col, char in enumerate(line)
                if char == "#"
            ),
        )
        self.assertEqual(CAPITAL.approach_cell(CAPITAL.gate_for("n")), (860, 1077))
        self.assertEqual(CAPITAL.approach_cell(CAPITAL.gate_for("w")), (864, 1080))
        self.assertFalse(CAPITAL.is_point_shape)
        # 4-connected: every mask cell is reachable from the anchor cell.
        seen = {CAPITAL.anchor_cell}
        frontier = [CAPITAL.anchor_cell]
        while frontier:
            cx, cy = frontier.pop()
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                neighbour = (cx + dx, cy + dy)
                if neighbour in CAPITAL.footprint_cells and neighbour not in seen:
                    seen.add(neighbour)
                    frontier.append(neighbour)
        self.assertEqual(seen, set(CAPITAL.footprint_cells))

    def test_point_shape_entry_expresses_cave_semantics(self):
        point = _point_entry()
        self.assertTrue(point.is_point_shape)
        self.assertEqual(point.footprint_cells, frozenset())
        self.assertEqual(point.anchor_cell, (500, 500))
        # approach_cell IS the anchor cell for a point-shape gate.
        self.assertEqual(point.approach_cell(point.gates[0]), point.anchor_cell)

    @covers_requirement(
        "wilderness-gateway::wilderness-entry-registry-links-a-grid-placed-anchor-to-an-authored-wilderness-footprint-and-gates"
    )
    def test_every_entrys_anchor_key_exists_in_anchor_placement_registry(self):
        for entry in WILDERNESS_ENTRY_REGISTRY.values():
            self.assertIn(entry.anchor_key, ANCHOR_PLACEMENT_REGISTRY)

    def test_gate_lookup_by_return_direction(self):
        self.assertEqual(CAPITAL.gate_for("n").destination.object_id, "south_gate")
        self.assertEqual(CAPITAL.gate_for("w").destination.object_id, "east_gate")
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
        self.assertIn((35, 270), extents["village_ciaran"])
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
        gate = WildernessGate("n", CAPITAL.gate_for("n").destination)
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
                WildernessEntryPoint("x", ("#", "#"), (0, 2700), (gate,)),
                "outside provider rectangle",
            ),
            (
                "disconnected footprint",
                "x",
                WildernessEntryPoint("x", ("###", "...", "###"), (600, 600), (gate,)),
                "not 4-connected",
            ),
            (
                "non-canonical return_direction",
                "x",
                WildernessEntryPoint(
                    "x", ("#####",) * 5, (600, 600), (WildernessGate("q", CAPITAL.gate_for("n").destination),)
                ),
                "non-canonical return_direction",
            ),
            (
                "duplicated return_direction",
                "x",
                WildernessEntryPoint(
                    "x",
                    ("#####",) * 5,
                    (600, 600),
                    (gate, WildernessGate("n", CAPITAL.gate_for("w").destination)),
                ),
                "duplicated return_direction",
            ),
            (
                "footprint cell on the closed ridge is not walkable terrain",
                "x",
                WildernessEntryPoint(
                    "x",
                    ("#", "#", "#"),
                    (1390, 1200),
                    (WildernessGate("e", CAPITAL.gate_for("n").destination),),
                ),
                "is not walkable terrain",
            ),
            (
                "point shape with zero gates",
                "x",
                WildernessEntryPoint("x", ("#",), (500, 500), ()),
                "exactly one gate",
            ),
            (
                "point shape with two gates",
                "x",
                _point_entry(
                    gates=(
                        WildernessGate("n", CAPITAL.gate_for("n").destination),
                        WildernessGate("w", CAPITAL.gate_for("w").destination),
                    )
                ),
                "exactly one gate",
            ),
            (
                "unresolvable destination identity",
                "x",
                WildernessEntryPoint(
                    "x",
                    ("#####",) * 5,
                    (600, 620),
                    (
                        WildernessGate(
                            "n",
                            settlement_node_ref("capital_altoria", "nowhere"),
                        ),
                    ),
                ),
                "no authored node",
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
                    "x", ("###", "##"), (600, 640), (WildernessGate("n", CAPITAL.gate_for("n").destination),)
                ),
                "ragged mask",
            ),
            (
                "illegal mask character",
                "x",
                WildernessEntryPoint(
                    "x", ("#X#", "#.#", "#.#"), (600, 660), (WildernessGate("n", CAPITAL.gate_for("n").destination),)
                ),
                "illegal mask character",
            ),
            (
                "bounding-box midpoint falls on a dot",
                "capital_altoria",
                WildernessEntryPoint(
                    "capital_altoria",
                    ("###", "#.#", "###"),
                    (600, 680),
                    (WildernessGate("n", CAPITAL.gate_for("n").destination),),
                ),
                "is not a '#' footprint cell",
            ),
            (
                "overlapping footprints",
                "x",
                WildernessEntryPoint(
                    "x", ("#", "#"), (860, 1080), (WildernessGate("e", CAPITAL.gate_for("n").destination),)
                ),
                "footprint overlaps",
            ),
            (
                "footprint contains another entry's gate approach cell",
                "x",
                WildernessEntryPoint(
                    "x", ("##",), (859, 1077), (WildernessGate("w", CAPITAL.gate_for("n").destination),)
                ),
                "lies inside footprint",
            ),
            (
                "point anchor on another entry's gate approach cell",
                "x",
                _point_entry(anchor=(864, 1080)),
                "approach cell",
            ),
            (
                "point anchor with a provider-invalid neighbor",
                "x",
                _point_entry(anchor=(1400, 990)),
                "provider-invalid neighbor",
            ),
            (
                "two gates sharing one destination room",
                "x",
                WildernessEntryPoint(
                    "x",
                    ("#####",) * 5,
                    (600, 700),
                    (
                        WildernessGate("n", ANCHOR_PLACEMENT_REGISTRY["capital_altoria"].node),
                        WildernessGate("s", ANCHOR_PLACEMENT_REGISTRY["capital_altoria"].node),
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
