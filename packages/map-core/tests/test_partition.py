"""District-partition generation and lightweight artifact mechanics.

Every fixture here is a file-local ASCII raster, one character per
one-kilometre cell, drawn north row first:

* ``~`` sea;
* ``a`` / ``b`` walkable land of nominal nation a / b;
* ``A`` / ``B`` blocked land (ridge, river or footprint) of nation a / b;
* ``f`` / ``g`` walkable land of the ``forest`` region in nation a / b.

Every other land cell is the ``plain`` region. Frames are a whole number of
5 km tiles. Expected owners are drawn independently in the tests, never
derived from the partitioner. The shipped artifact is covered by the game's
data-contract test; the runtime adapter's no-generation-import claim is
covered by ``tests.test_map_partition_independence``.
"""

from __future__ import annotations

import json
import random
import unittest

import numpy as np

from elosern_map_core.partition import (
    DistrictSeed,
    Partition,
    PartitionError,
    PartitionInput,
    PartitionInputSnapshot,
    compute_outlines,
    compute_partition,
    encode,
    generate_partition,
    partition_input,
    serialize,
)
from elosern_map_core.partition_codec import (
    MIXED,
    PARTITION_ALGORITHM_VERSION,
    PartitionDocumentError,
    decode_partition,
    partition_freshness,
    partition_source_signature,
    read_partition_metadata,
)
from elosern_map_core.sources import make_source_document
from elosern_map_core.terrain import REGION_KEYS, TerrainDefinition

_NATIONS = ("a", "b")
_REGIONS = ("forest", "plain")
_SIGNATURE = "synthetic"


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
    return PartitionInput(
        size,
        land,
        walkable,
        nation,
        _NATIONS,
        region,
        _REGIONS,
        tuple(districts),
        source_signature=_SIGNATURE,
    )


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

    def test_regeneration_is_byte_identical_and_line_oriented(self):
        first, second = generate_partition(self._input()), generate_partition(self._input())
        self.assertEqual(first, second)
        self.assertTrue(first.endswith("}\n"))
        document = json.loads(first)
        self.assertEqual(serialize(document), first)
        self.assertNotIn(".", json.dumps(document["outlines"]))  # integer metres only

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

    def test_changed_inputs_change_the_artifact(self):
        baseline = generate_partition(self._input())
        moved = _input(self._ROWS, _seed("west", 0, 0), _seed("east", 9, 0))
        self.assertNotEqual(generate_partition(moved), baseline)
        changed = _input([row.replace("A", "a") for row in self._ROWS], *self._input().districts)
        regenerated = generate_partition(changed)
        self.assertNotEqual(json.loads(regenerated)["fingerprint"], json.loads(baseline)["fingerprint"])

    def test_the_artifact_carries_the_algorithm_version_and_source_signature(self):
        inp = _input(self._ROWS, _seed("west", 0, 0), _seed("east", 9, 9))
        document = json.loads(generate_partition(inp))
        self.assertEqual(document["algorithm_version"], PARTITION_ALGORITHM_VERSION)
        self.assertEqual(document["source_signature"], _SIGNATURE)
        metadata = read_partition_metadata(document)
        self.assertEqual(metadata.algorithm_version, PARTITION_ALGORITHM_VERSION)
        self.assertEqual(metadata.source_signature, _SIGNATURE)

    def test_missing_source_signature_is_rejected(self):
        inp = PartitionInput(
            self._input().size,
            self._input().land,
            self._input().walkable,
            self._input().nation,
            _NATIONS,
            self._input().region,
            _REGIONS,
            self._input().districts,
        )
        with self.assertRaises(PartitionError) as caught:
            generate_partition(inp)
        self.assertIn("carries no source signature", caught.exception.problems[0])


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
            _REGIONS, (), source_signature=_SIGNATURE,
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

    def test_checkerboard_vertex_splits_diagonal_cells(self):
        rows = ["rs", "sr"]
        outlines = self._outlines(rows)
        self.assertEqual(len(outlines["r"]), 2)
        self.assertEqual(len(outlines["s"]), 2)
        self.assertSharedBoundaries(outlines, 2)

    def test_island_against_sea_is_one_counter_clockwise_ring(self):
        rows = [".....", ".ppp.", ".ppp.", ".ppp.", "....."]
        outlines = self._outlines(rows)
        self.assertEqual(len(outlines["p"]), 1)
        ring = outlines["p"][0]
        area2 = sum(
            x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1])
        )
        self.assertGreater(area2, 0)
        # Smoothing cuts the four corners but keeps the coast within a cell.
        for x, y in ring:
            self.assertTrue(1000 <= x <= 4000 and 1000 <= y <= 4000, (x, y))


def _oracle_owners(inp, seeds):
    """Owners by a naive cell-level Dijkstra (independent of the generator).

    With one-cell tiles every domain cell is its own fragment, so the
    generator must agree with this direct search: legal same-nation steps,
    no corner cutting, cost 1 or sqrt(2) compared exactly as integer pairs,
    ties to the smaller key. Returns ``None`` when a component is unseeded.
    """
    size = inp.size
    domain = inp.land & inp.walkable

    def legal(a, b):
        (ax, ay), (bx, by) = a, b
        if not (0 <= bx < size and 0 <= by < size) or not domain[by, bx]:
            return False
        nation = inp.nation[ay, ax]
        if inp.nation[by, bx] != nation:
            return False
        if ax != bx and ay != by:
            return all(
                domain[y, x] and inp.nation[y, x] == nation for x, y in ((bx, ay), (ax, by))
            )
        return True

    def less(p, q):
        # Is a1 + b1*sqrt(2) < a2 + b2*sqrt(2)?  Compare da against -db*sqrt(2).
        da, db = p[0] - q[0], p[1] - q[1]
        if da <= 0 and db <= 0:
            return da < 0 or db < 0
        if da >= 0 and db >= 0:
            return False
        if da < 0:  # db > 0: need -da > db*sqrt(2)
            return da * da > 2 * db * db
        return 2 * db * db > da * da  # da > 0, db < 0

    keys = sorted(seed.key for seed in seeds)
    best = {}
    for seed in seeds:
        best[seed.landmark_cell] = ((0, 0), keys.index(seed.key))
    done = {}
    while True:
        open_cells = [c for c in best if c not in done]
        if not open_cells:
            break
        current = open_cells[0]
        for cell in open_cells[1:]:
            (d, r), (bd, br) = best[cell], best[current]
            if less(d, bd) or (d == bd and (r, cell[1], cell[0]) < (br, current[1], current[0])):
                current = cell
        done[current] = best[current][1]
        (a, b), rank = best[current]
        x, y = current
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nxt = (x + dx, y + dy)
                if (dx or dy) and nxt not in done and legal(current, nxt):
                    label = ((a + (dx == 0 or dy == 0), b + (dx != 0 and dy != 0)), rank)
                    old = best.get(nxt)
                    if old is None or less(label[0], old[0]) or (label[0] == old[0] and rank < old[1]):
                        best[nxt] = label
    if int(domain.sum()) != len(done):
        return None
    return {cell: keys[rank] for cell, rank in done.items()}


class OracleAgreementTests(unittest.TestCase):
    def test_fragment_dijkstra_matches_a_naive_cell_search_on_unit_tiles(self):
        rng = random.Random(20261023)
        checked = 0
        for _ in range(12):
            size = 16
            rows = [
                "".join(
                    ("A" if rng.random() < 0.18 else "a") if x < 10 else ("B" if rng.random() < 0.18 else "b")
                    for x in range(size)
                )
                for _ in range(size)
            ]
            base = _input(rows)
            open_cells = [
                (x, y) for y in range(size) for x in range(size) if base.walkable[y, x]
            ]
            picks = rng.sample(open_cells, 5)
            seeds = tuple(_seed(f"d{index}", x, y) for index, (x, y) in enumerate(picks))
            inp = PartitionInput(
                size, base.land, base.walkable, base.nation, _NATIONS, base.region, _REGIONS,
                seeds, tile=1, source_signature=_SIGNATURE,
            )
            expected = _oracle_owners(inp, seeds)
            if expected is None:
                with self.assertRaises(PartitionError):
                    compute_partition(inp)
                continue
            partition = compute_partition(inp)
            for cell, key in expected.items():
                self.assertEqual(partition.owner_at(cell), key, cell)
            checked += 1
        self.assertGreater(checked, 0)


class FootprintPocketTests(unittest.TestCase):
    def _rows(self, pocket="a", gap=False):
        rows = []
        for index in range(10):
            y = 9 - index
            row = ""
            for x in range(10):
                in_ring = 2 <= x <= 6 and 2 <= y <= 6
                if (x, y) == (4, 4):
                    row += pocket
                elif gap and (x, y) == (6, 4):
                    row += "a"
                elif in_ring and 3 <= x <= 5 and 3 <= y <= 5:
                    row += "A"
                elif in_ring and (x in (2, 6) or y in (2, 6)):
                    row += "A"
                else:
                    row += "a"
            rows.append(row)
        return rows

    def _town(self, rows):
        footprint = frozenset(
            (x, 9 - index)
            for index, row in enumerate(rows)
            for x, char in enumerate(row)
            if char in "AB"
        )
        return DistrictSeed("town", "voronoi", (3, 3), approaches=((7, 4),), footprint=footprint)

    def test_pocket_enclosed_by_a_claimed_footprint_joins_it(self):
        rows = self._rows()
        partition = compute_partition(_input(rows, self._town(rows), _seed("far", 9, 9)))
        self.assertEqual(partition.owner_at((4, 4)), "town")

    def test_pocket_of_another_nation_or_open_to_the_outside_is_not_absorbed(self):
        rows = self._rows(pocket="b")
        with self.assertRaises(PartitionError) as caught:
            compute_partition(_input(rows, self._town(rows), _seed("far", 9, 9)))
        self.assertIn("unseeded walkable component at cell (4, 4) in nation 'b'", caught.exception.problems[0])
        # A walkable gap at (6, 4) joins the courtyard row to the outside, so
        # the pocket is ordinary reachable ground of the nearest seed.
        rows = self._rows(gap=True)
        rows = [row[:5] + ("a" if index == 5 else row[5]) + row[6:] for index, row in enumerate(rows)]
        partition = compute_partition(_input(rows, self._town(rows), _seed("far", 9, 9)))
        self.assertTrue(partition.domain[4, 4])
        self.assertIn(partition.owner_at((4, 4)), {"town", "far"})


class DecoderValidationTests(unittest.TestCase):
    def test_malformed_documents_are_rejected(self):
        inp = FrozenEncodingTests()._input()
        document = encode(compute_partition(inp), inp)
        mutations = {
            "mixed marker": lambda d: d["exceptions"][0].__setitem__(2, MIXED),
            "listed twice": lambda d: d["exceptions"].append(list(d["exceptions"][0])),
            "malformed ring": lambda d: d["outlines"]["west"][0].append(5),
            "unsupported partition version": lambda d: d.__setitem__("version", 99),
        }
        for rule, mutate in mutations.items():
            with self.subTest(rule=rule):
                broken = json.loads(json.dumps(document))
                mutate(broken)
                with self.assertRaises(PartitionDocumentError) as caught:
                    decode_partition(broken, is_land=lambda cell: True)
                self.assertIn(rule, str(caught.exception))


def _terrain(frame=20):
    return TerrainDefinition(
        frame_cells=frame,
        mainland_boundary_km=((0, 0), (frame, 0), (frame, frame), (0, frame)),
        forest_edge=((0, 12), (frame - 1, 12)),
        waterway_routes={"river": ((frame - 1, 8), (0, 8))},
        waterway_fords={},
        border_river_key="river",
        ridge_base_x=5,
        ridge_period=5,
        ridge_step=1,
        ridge_min_x=0,
        ridge_max_x=frame - 1,
        ridge_north_limit=frame - 1,
        ridge_passes=((0, 0),),
        coastal_y_max=3,
        mountain_corridor_half_width=1,
        region_flavors={key: ("x", "y") for key in REGION_KEYS},
    )


class SnapshotAssemblyTests(unittest.TestCase):
    def _snapshot(self, **overrides):
        values = {
            "terrain": _terrain(),
            "nation_names": ("altoria", "grandia", "valhalla"),
            "region_names": tuple(sorted(REGION_KEYS)),
            "footprints": frozenset({(2, 2), (3, 2)}),
            "districts": (_seed("west", 1, 1), _seed("east", 18, 18)),
            "source_signature": _SIGNATURE,
        }
        values.update(overrides)
        return PartitionInputSnapshot(**values)

    def test_the_rasters_follow_the_explicit_snapshot(self):
        from elosern_map_core.terrain import (
            is_land_cell,
            is_passable_terrain,
            nominal_nation_for_coordinates,
            region_for_coordinates,
        )

        snapshot = self._snapshot()
        inp = partition_input(snapshot)
        self.assertEqual(inp.size, snapshot.size)
        self.assertEqual(inp.source_signature, _SIGNATURE)
        for y in range(inp.size):
            for x in range(inp.size):
                cell = (x, y)
                self.assertEqual(bool(inp.land[y, x]), is_land_cell(snapshot.terrain, cell), cell)
                expected_walkable = (
                    is_passable_terrain(snapshot.terrain, cell)
                    and cell not in snapshot.footprints
                )
                self.assertEqual(bool(inp.walkable[y, x]), expected_walkable, cell)
                if inp.land[y, x]:
                    self.assertEqual(
                        inp.nation_names[inp.nation[y, x] - 1],
                        nominal_nation_for_coordinates(snapshot.terrain, x, y),
                        cell,
                    )
                    self.assertEqual(
                        inp.region_names[inp.region[y, x] - 1],
                        region_for_coordinates(snapshot.terrain, x, y),
                        cell,
                    )
        self.assertFalse(inp.walkable[2, 2])

    def test_an_undeclared_identifier_is_rejected_with_the_cell(self):
        snapshot = self._snapshot(nation_names=("altoria", "grandia"))
        with self.assertRaises(PartitionError) as caught:
            partition_input(snapshot)
        self.assertIn("undeclared nation 'valhalla'", caught.exception.problems[0])

    def test_assembly_is_deterministic_and_carries_the_signature(self):
        first, second = partition_input(self._snapshot()), partition_input(self._snapshot())
        self.assertTrue(np.array_equal(first.land, second.land))
        self.assertTrue(np.array_equal(first.walkable, second.walkable))
        self.assertTrue(np.array_equal(first.nation, second.nation))
        self.assertTrue(np.array_equal(first.region, second.region))
        self.assertEqual(first.source_signature, _SIGNATURE)


class FreshnessTests(unittest.TestCase):
    def _documents(self):
        return [
            make_source_document("content/maps/continent.yaml", "continent: 1\n"),
            make_source_document("content/maps/districts.yaml", "districts: 1\n"),
            make_source_document("content/maps/settlements/a.yaml", "settlement: 1\n"),
            make_source_document("content/maps/interiors/a.yaml", "interior: 1\n"),
        ]

    def _metadata(self, signature, algorithm=PARTITION_ALGORITHM_VERSION):
        return read_partition_metadata(
            {
                "version": 2,
                "algorithm_version": algorithm,
                "source_signature": signature,
                "fingerprint": "0" * 64,
            }
        )

    def test_the_signature_covers_partition_sources_only(self):
        baseline = partition_source_signature(self._documents())
        self.assertEqual(baseline, partition_source_signature(list(reversed(self._documents()))))
        interior_only = [
            document
            for document in self._documents()
            if document.relative_path != "content/maps/interiors/a.yaml"
        ] + [make_source_document("content/maps/interiors/a.yaml", "interior: 2\n")]
        self.assertEqual(baseline, partition_source_signature(interior_only))

    def test_a_source_edit_or_membership_change_invalidates_freshness(self):
        baseline = partition_source_signature(self._documents())
        edited = [
            make_source_document("content/maps/continent.yaml", "continent: 2\n")
            if document.relative_path == "content/maps/continent.yaml"
            else document
            for document in self._documents()
        ]
        self.assertTrue(partition_freshness(self._metadata(baseline), baseline).current)
        self.assertFalse(
            partition_freshness(self._metadata(baseline), partition_source_signature(edited)).current
        )
        removed = [
            document
            for document in self._documents()
            if document.relative_path != "content/maps/districts.yaml"
        ]
        self.assertFalse(
            partition_freshness(self._metadata(baseline), partition_source_signature(removed)).current
        )
        added = self._documents() + [
            make_source_document("content/maps/settlements/b.yaml", "settlement: 1\n")
        ]
        self.assertFalse(
            partition_freshness(self._metadata(baseline), partition_source_signature(added)).current
        )

    def test_an_algorithm_bump_or_missing_signature_is_stale(self):
        signature = partition_source_signature(self._documents())
        bumped = self._metadata(signature, algorithm=PARTITION_ALGORITHM_VERSION + 1)
        current = partition_freshness(bumped, signature)
        self.assertFalse(current.current)
        self.assertEqual(current.algorithm_version, PARTITION_ALGORITHM_VERSION + 1)
        self.assertFalse(partition_freshness(self._metadata(signature), None).current)
