"""Map-district partition mechanics over miniature synthetic continents.

Every fixture here is a file-local ASCII raster, one character per
one-kilometre cell, drawn north row first:

* ``~`` sea;
* ``a`` / ``b`` walkable land of nominal nation a / b;
* ``A`` / ``B`` blocked land (ridge, river or footprint) of nation a / b;
* ``f`` / ``g`` walkable land of the ``forest`` region in nation a / b.

Every other land cell is the ``plain`` region. Frames are a whole number of
5 km tiles. Expected owners are drawn independently in the tests, never
derived from the partitioner. Shipped geography is covered by the production
recomputation test in ``world.maps.tests.test_map_district_partition``.
"""

import json
import unittest

import numpy as np

from tools.map_district_partition import (
    MIXED,
    DistrictSeed,
    Partition,
    PartitionError,
    PartitionInput,
    compute_outlines,
    compute_partition,
    encode,
    generate,
    serialize,
)
from tools.spec_traceability import covers_requirement
from world.maps.district_partition import decode_partition

_PARTITION = "map-district-partition::offline-partition-assigns-every-land-cell-once-without-crossing-barriers"
_FROZEN = "map-district-partition::frozen-partition-and-outlines-reproduce-deterministically-offline"

_NATIONS = ("a", "b")
_REGIONS = ("forest", "plain")


def _input(rows, *districts):
    """Rasterize ``rows`` (north first) into a partition input."""
    size = len(rows)
    assert all(len(row) == size for row in rows), "fixtures are square"
    land = np.zeros((size, size), dtype=bool)
    walkable = np.zeros((size, size), dtype=bool)
    nation = np.zeros((size, size), dtype=np.uint8)
    region = np.zeros((size, size), dtype=np.uint8)
    for index, row in enumerate(rows):
        y = size - 1 - index
        for x, char in enumerate(row):
            if char == "~":
                continue
            land[y, x] = True
            walkable[y, x] = char in "abfg"
            nation[y, x] = 1 if char in "aAf" else 2
            region[y, x] = 1 if char in "fg" else 2
    return PartitionInput(size, land, walkable, nation, _NATIONS, region, _REGIONS, tuple(districts))


def _seed(key, x, y):
    return DistrictSeed(key, "voronoi", (x, y))


def _owners(partition, rows):
    """The owner raster drawn back as text rows (north first), sea as ``.``."""
    letters = {key: key[0] for key in partition.keys}
    size = len(rows)
    drawn = []
    for index in range(size):
        y = size - 1 - index
        drawn.append(
            "".join(
                letters[partition.owner_at((x, y))] if partition.owner_at((x, y)) else "."
                for x in range(size)
            )
        )
    return drawn


def _segments(rings):
    for ring in rings:
        points = list(zip(ring[::2], ring[1::2]))
        for index, point in enumerate(points):
            yield point, points[(index + 1) % len(points)]


class BarrierPropagationTests(unittest.TestCase):
    @covers_requirement(_PARTITION)
    def test_national_border_splits_a_tile_and_stays_closed_at_a_ford(self):
        # A border river (blocked A cells) with a ford gap at x=7 separates
        # nation a (south) from nation b (north). The ford lets travellers
        # cross, but the national border closes it for the partition, so
        # nation b needs its own seed and mixed tiles carry exact owners.
        rows = [
            "bbbbbbbbbb",
            "bbbbbbbbbb",
            "bbbbbbbbbb",
            "bbbbbbbbbb",
            "bbbbbbbbbb",
            "AAAAAAAaAA",
            "aaaaaaaaaa",
            "aaaaaaaaaa",
            "aaaaaaaaaa",
            "aaaaaaaaaa",
        ]
        with self.assertRaises(PartitionError) as caught:
            compute_partition(_input(rows, _seed("south", 1, 1)))
        self.assertIn(
            "unseeded walkable component at cell (0, 5) in nation 'b' (50 cells)",
            caught.exception.problems[0],
        )
        partition = compute_partition(_input(rows, _seed("south", 1, 1), _seed("north", 8, 8)))
        self.assertEqual(_owners(partition, rows), ["n" * 10] * 5 + ["s" * 10] * 5)

    @covers_requirement(_PARTITION)
    def test_same_nation_ford_and_pass_stay_open(self):
        # The same river inside one nation: its ford joins both banks, so a
        # single southern seed reaches the northern bank and no component is
        # left unseeded. River cells take the nearest same-nation owner.
        rows = [
            "aaaaaaaaaa",
            "aaaaaaaaaa",
            "aaaaaaaaaa",
            "aaaaaaaaaa",
            "aaaaaaaaaa",
            "AAAAAAAaAA",
            "aaaaaaaaaa",
            "aaaaaaaaaa",
            "aaaaaaaaaa",
            "aaaaaaaaaa",
        ]
        partition = compute_partition(_input(rows, _seed("south", 1, 1)))
        self.assertEqual(_owners(partition, rows), ["s" * 10] * 10)
        self.assertTrue(partition.domain[4, 7])
        self.assertFalse(partition.domain[4, 0])

    @covers_requirement(_PARTITION)
    def test_diagonal_wall_rejects_corner_cutting(self):
        # A one-cell anti-diagonal ridge (x + y == 9) is 8-connected but its
        # far side touches the near side diagonally on every step. Beta sits
        # right behind the wall; alpha far in the south-west corner. Corner
        # cutting would hand beta the near side; legal steps keep every
        # south-west cell with alpha. Ridge cells tie at one kilometre from
        # both sides, so the smaller key, alpha, displays them.
        size = 10
        rows = []
        for index in range(size):
            y = size - 1 - index
            rows.append("".join("A" if x + y == 9 else "a" for x in range(size)))
        partition = compute_partition(_input(rows, _seed("alpha", 0, 0), _seed("beta", 5, 5)))
        for y in range(size):
            for x in range(size):
                expected = "beta" if x + y > 9 else "alpha"
                self.assertEqual(partition.owner_at((x, y)), expected, (x, y))
        # Tile (1, 0) straddles the wall: its diagonal neighbours (5, 3) and
        # (6, 4) fall into two fragments.
        self.assertNotEqual(partition.fragment[3, 5], partition.fragment[4, 6])

    @covers_requirement(_PARTITION)
    def test_equal_distance_goes_to_the_smaller_key(self):
        # Three tile columns in one row band: the middle tile is one coarse
        # step from both seeds, so the smaller key takes it on either side.
        rows = ["a" * 15] * 15
        for west, east, winner in (("eta", "zeta", "eta"), ("zeta", "eta", "eta")):
            with self.subTest(west=west, east=east):
                partition = compute_partition(_input(rows, _seed(west, 0, 7), _seed(east, 14, 7)))
                self.assertEqual(partition.owner_at((7, 7)), winner)
                self.assertEqual(partition.owner_at((2, 7)), west)
                self.assertEqual(partition.owner_at((12, 7)), east)

    @covers_requirement(_PARTITION)
    def test_blocked_inland_cell_takes_the_nearest_same_nation_owner(self):
        # A 3 by 3 blocked block of nation a (x 4..6) borders nation b at
        # x=7. Its eastern cell (6, 5) is one kilometre from b ground, but it
        # displays the nearest nation-a owner, two kilometres away.
        rows = []
        for index in range(10):
            y = 9 - index
            rows.append(
                "".join(
                    "b" if x >= 7 else ("A" if 4 <= x <= 6 and 4 <= y <= 6 else "a")
                    for x in range(10)
                )
            )
        partition = compute_partition(_input(rows, _seed("west", 0, 0), _seed("east", 9, 9)))
        self.assertEqual(partition.owner_at((6, 5)), "west")
        self.assertEqual(partition.owner_at((7, 5)), "east")
        self.assertFalse(partition.primary[5, 6])
        self.assertTrue(partition.primary[5, 3])


class RegionAndLandmarkTests(unittest.TestCase):
    @covers_requirement(_PARTITION)
    def test_region_district_takes_its_region_across_nations_first(self):
        # The forest band (f = nation a, g = nation b) crosses the border
        # and a mid-tile edge. Its single district owns all of it, even the
        # cells nearer the Voronoi seeds; the seeds share the rest by nation.
        rows = [
            "fffffggggg",
            "fffffggggg",
            "fffffggggg",
            "aaaaabbbbb",
            "aaaaabbbbb",
            "aaaaabbbbb",
            "aaaaabbbbb",
            "aaaaabbbbb",
            "aaaaabbbbb",
            "aaaaabbbbb",
        ]
        forest = DistrictSeed("forest_heart", "region", (8, 9), region_key="forest")
        partition = compute_partition(
            _input(rows, forest, _seed("west", 0, 0), _seed("east", 9, 0))
        )
        self.assertEqual(
            _owners(partition, rows), ["f" * 10] * 3 + ["wwwwweeeee"] * 7
        )
        # A Voronoi landmark may never sit in region land.
        with self.assertRaises(PartitionError) as caught:
            compute_partition(_input(rows, forest, _seed("west", 0, 9), _seed("east", 9, 0)))
        self.assertIn("west: landmark (0, 9) lies in region land", caught.exception.problems)

    @covers_requirement(_PARTITION)
    def test_grid_landmark_in_a_footprint_injects_at_its_routed_approach(self):
        # A settlement footprint (blocked A ring x 3..7, y 3..7) encloses a
        # walkable courtyard (5, 5). The landmark cell (4, 4) is inside the
        # footprint in 5 km tile (0, 0); its routed east approach (8, 5) lies
        # in the adjacent tile (1, 1). The western approach (1, 5) is nation
        # b ground and is ignored. Nation a also has a far seed, so the
        # approach is what wins the ground east of the town.
        rows = []
        for index in range(15):
            y = 14 - index
            row = ""
            for x in range(15):
                if x <= 1:
                    row += "b"
                elif 3 <= x <= 7 and 3 <= y <= 7 and (x, y) != (5, 5):
                    row += "A"
                else:
                    row += "a"
            rows.append(row)
        footprint = frozenset(
            (x, y) for x in range(3, 8) for y in range(3, 8) if (x, y) != (5, 5)
        )
        town = DistrictSeed(
            "town", "voronoi", (4, 4), approaches=((8, 5), (1, 5)), footprint=footprint
        )
        partition = compute_partition(
            _input(rows, town, _seed("far", 14, 14), _seed("west", 0, 0))
        )
        self.assertEqual(partition.sources["town"], (int(partition.fragment[5, 8]),))
        for cell in footprint | {(5, 5), (8, 5), (9, 5)}:
            self.assertEqual(partition.owner_at(cell), "town", cell)
        self.assertTrue(all(partition.primary[y, x] for x, y in footprint))
        self.assertEqual(partition.owner_at((1, 5)), "west")
        self.assertEqual(partition.owner_at((14, 14)), "far")

    @covers_requirement(_PARTITION)
    def test_footprint_conflicts_and_border_mismatch_fail(self):
        rows = ["a" * 5 + "b" * 5] * 10
        rows = [row[:4] + "AB" + row[6:] if 3 <= i <= 4 else row for i, row in enumerate(rows)]
        footprint = frozenset({(4, 5), (5, 5), (4, 6), (5, 6)})
        cases = {
            "crosses a national border": (
                DistrictSeed("town", "voronoi", (4, 5), approaches=((3, 5),), footprint=footprint),
            ),
            "holds the landmark of 'keep'": (
                DistrictSeed(
                    "town", "voronoi", (4, 5), approaches=((3, 5),),
                    footprint=frozenset({(4, 5), (4, 6)}),
                ),
                DistrictSeed(
                    "keep", "voronoi", (4, 6), approaches=((3, 6),),
                    footprint=frozenset({(4, 5), (4, 6)}),
                ),
            ),
            "no routed same-nation walkable gateway approach": (
                DistrictSeed("town", "voronoi", (4, 5), approaches=((7, 5),)),
            ),
        }
        for rule, districts in cases.items():
            with self.subTest(rule=rule), self.assertRaises(PartitionError) as caught:
                compute_partition(_input(rows, *districts, _seed("east", 9, 0)))
            self.assertIn(rule, "\n".join(caught.exception.problems))


class FrozenEncodingTests(unittest.TestCase):
    _ROWS = [
        "~~~bbbbbbb",
        "~~~bbbbbbb",
        "~~aabbbbbb",
        "~aaaabbbbb",
        "~aaaaabbbb",
        "~aaaaabbbb",
        "aaaaaaabbb",
        "aaaaaaabbb",
        "aaAaaaabbb",
        "aaaaaaabbb",
    ]

    def _input(self):
        return _input(self._ROWS, _seed("west", 0, 0), _seed("east", 9, 9))

    @covers_requirement(_FROZEN)
    def test_regeneration_is_byte_identical_and_line_oriented(self):
        first, second = generate(self._input()), generate(self._input())
        self.assertEqual(first, second)
        self.assertTrue(first.endswith("}\n"))
        document = json.loads(first)
        self.assertEqual(serialize(document), first)
        self.assertNotIn(".", json.dumps(document["outlines"]))  # integer metres only

    @covers_requirement(_FROZEN)
    def test_runs_decode_to_the_exact_ownership_with_sea_distinguished(self):
        inp = self._input()
        partition = compute_partition(inp)
        document = encode(partition, inp)
        # Tile (0, 0) is uniform (its blocked cell displays west, code 2);
        # tile (0, 1) mixes coast, nation a and nation b, so it is an
        # exception tile whose sea cells decode as 0.
        self.assertEqual(document["coarse"], [[2, 1, MIXED, 1], [MIXED, 2]])
        decoded = decode_partition(document, is_land=lambda c: bool(inp.land[c[1], c[0]]))
        self.assertEqual(decoded.owner_code((0, 9)), 0)
        for y in range(inp.size):
            for x in range(inp.size):
                self.assertEqual(decoded.district_at((x, y)), partition.owner_at((x, y)), (x, y))
        self.assertIsNone(decoded.district_at((10, 0)))

    @covers_requirement(_FROZEN)
    def test_changed_inputs_change_the_artifact(self):
        baseline = generate(self._input())
        moved = _input(self._ROWS, _seed("west", 0, 0), _seed("east", 9, 0))
        self.assertNotEqual(generate(moved), baseline)
        changed = _input([row.replace("A", "a") for row in self._ROWS], *self._input().districts)
        regenerated = generate(changed)
        self.assertNotEqual(json.loads(regenerated)["fingerprint"], json.loads(baseline)["fingerprint"])


class OutlineTests(unittest.TestCase):
    def _outlines(self, owner_rows, nation_rows=None):
        size = len(owner_rows)
        keys = tuple(sorted({c for row in owner_rows for c in row if c != "."}))
        owner = np.zeros((size, size), dtype=np.int16)
        nation = np.ones((size, size), dtype=np.uint8)
        for index, row in enumerate(owner_rows):
            y = size - 1 - index
            for x, char in enumerate(row):
                if char != ".":
                    owner[y, x] = keys.index(char) + 1
                if nation_rows is not None:
                    nation[y, x] = 1 if nation_rows[index][x] == "a" else 2
        land = owner > 0
        inp = PartitionInput(
            size, land, land, nation, _NATIONS, np.full((size, size), 2, dtype=np.uint8),
            _REGIONS, (),
        )
        partition = Partition(keys, owner, land, land, np.full((size, size), -1))
        return compute_outlines(partition, inp)

    def assertSharedBoundaries(self, outlines, size):
        edge_m = size * 1000
        segments = {
            key: set(_segments([[value for point in ring for value in point] for ring in rings]))
            for key, rings in outlines.items()
        }
        for key, own in segments.items():
            others = set().union(*(s for k, s in segments.items() if k != key))
            for start, end in own:
                # Only the outer frame (owner 0) has no neighbour ring.
                on_frame = all(p[0] in (0, edge_m) or p[1] in (0, edge_m) for p in (start, end))
                self.assertTrue(on_frame or (end, start) in others, (key, start, end))

    @covers_requirement(_FROZEN)
    def test_neighbours_share_smoothed_pieces_and_junctions_stay_exact(self):
        rows = [
            "xxxxxxxyyy",
            "xxxxxxyyyy",
            "xxxxxyyyyy",
            "xxxxyyyyyy",
            "xxxyyyyyyy",
            "xxxzzzzyyy",
            "xxzzzzzzyy",
            "xzzzzzzzzy",
            "zzzzzzzzzz",
            "zzzzzzzzzz",
        ]
        outlines = self._outlines(rows)
        self.assertSharedBoundaries(outlines, 10)
        # The x/y staircase is smoothed onto its edge midpoints: no ring
        # keeps the stair corner (4000, 6000) between two junctions.
        points = {p for rings in outlines.values() for ring in rings for p in ring}
        self.assertNotIn((4000, 6000), points)
        self.assertIn((3000, 5000), points)  # the x/y/z junction is exact

    @covers_requirement(_FROZEN)
    def test_national_enclave_keeps_exact_geometry_and_a_matching_hole(self):
        rows = ["pppppp", "pqqqpp", "pqqqpp", "pppppp", "pppppp", "pppppp"]
        nations = ["aaaaaa", "abbbaa", "abbbaa", "aaaaaa", "aaaaaa", "aaaaaa"]
        outlines = self._outlines(rows, nations)
        self.assertEqual(
            outlines["q"],
            [[(1000, 3000), (4000, 3000), (4000, 5000), (1000, 5000)]],
        )
        hole = outlines["p"][1]
        self.assertEqual(sorted(hole), sorted(outlines["q"][0]))
        self.assertSharedBoundaries(outlines, 6)

    @covers_requirement(_FROZEN)
    def test_checkerboard_vertex_splits_diagonal_cells(self):
        rows = ["rs", "sr"]
        outlines = self._outlines(rows)
        self.assertEqual(len(outlines["r"]), 2)
        self.assertEqual(len(outlines["s"]), 2)
        self.assertSharedBoundaries(outlines, 2)
