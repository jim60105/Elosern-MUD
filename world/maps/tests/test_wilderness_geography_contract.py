"""Data-contract test: authored continental terrain, waterway and anchor-region data contract

The shipped geography is checked through invariants derived from the authored
data itself: classifier joins, walkability and connectivity of every authored
site, ford and river-cell semantics, nominal-claim agreement and the political
lines' derivation. No authored coordinate, count or area share is copied here,
so moving a site, river or edge vertex needs no test edit unless it breaks an
invariant. Mechanics stay in ``world/maps/tests/test_wilderness_provider.py``.
"""

from tools.spec_traceability import covers_requirement

import math
import unittest
from collections import deque
from collections.abc import Iterator

from elosern_map_core.terrain import rasterize_routes, ridge_center_x, ridge_span, ridge_spans

from world.lore.wilderness_regions import (
    mainland_boundary_km,
    regions,
)
from world.maps import geography, wilderness_provider
from world.maps.wilderness_provider import (
    border_river_row,
    forest_edge_row,
    is_closed_ridge_cell,
    is_inland_water_cell,
    is_land_cell,
    is_valid_wilderness_cell,
    national_borders,
    nominal_nation_for_coordinates,
    region_for_coordinates,
    terrain_description,
)


def terrain():
    return geography.current().terrain


def setUpModule():
    from world.tests.geography_fixture import publish_shipped_geography

    publish_shipped_geography()


def _rule_cells(region_key: str, rule: object) -> Iterator[tuple[int, int]]:
    """The region's walkable cells one ambient rule's authored window covers."""
    from world.maps.wilderness_population import species_rule_for_coordinates

    x_min, x_max, y_min, y_max = wilderness_provider.region_search_boxes()[region_key]
    for x in range(x_min, x_max + 1):
        for y in range(y_min, y_max + 1):
            if wilderness_provider.region_for_coordinates(x, y) != region_key:
                continue
            if not is_valid_wilderness_cell((x, y)):
                continue
            if species_rule_for_coordinates(x, y) != rule:
                continue
            yield (x, y)


class AuthoredTerrainContractTests(unittest.TestCase):
    @covers_requirement("wilderness-terrain::the-coordinate-classifier-is-a-pure-deterministic-function-over-the-whole-bounded-map")
    def test_central_mountain_region_bends_with_the_authored_corridor(self):
        # Rows come from the authored stem itself; the probes sit one cell
        # outside the authored corridor half-width on both sides.
        half_width = terrain().mountain_corridor_half_width
        rows = [
            y
            for _, y in terrain().ridge_stem
            if y < forest_edge_row(ridge_center_x(terrain(), y))
        ]
        self.assertTrue(rows, "the stem must have rows south of the forest edge")
        for y in rows:
            centre = ridge_center_x(terrain(), y)
            with self.subTest(y=y):
                self.assertEqual(region_for_coordinates(centre, y), "central_mountains")
                self.assertNotEqual(
                    region_for_coordinates(centre - half_width - 1, y), "central_mountains"
                )
                self.assertNotEqual(
                    region_for_coordinates(centre + half_width + 1, y), "central_mountains"
                )

    @covers_requirement("wilderness-terrain::terrain-and-political-control-derive-from-authored-geography")
    def test_anchor_centres_resolve_their_authored_terrain(self):
        # Every declared location cell classifies into one of the declared
        # regions: the roster itself is authored data, so this checks the
        # identity/classifier join rather than a copied row table.
        from world.lore.anchors import anchor_geography, anchors

        self.assertTrue(anchor_geography())
        for anchor_key, geography_view in anchor_geography().items():
            with self.subTest(anchor=anchor_key):
                self.assertIn(anchor_key, anchors())
                self.assertIn(region_for_coordinates(*geography_view.cell), regions())

    @covers_requirement("wilderness-terrain::terrain-description-is-a-pure-deterministic-function-with-no-llm-or-randomness")
    def test_description_follows_the_region_and_the_fixed_formula(self):
        for x, y in ((860, 1080), (60, 100), (2000, 1000), (1250, 2420)):
            with self.subTest(cell=(x, y)):
                region = region_for_coordinates(x, y)
                variants = regions()[region].terrain_flavor_zh
                self.assertEqual(
                    terrain_description(x, y),
                    variants[(x * 92821 + y * 68917) % len(variants)],
                )

    @covers_requirement("wilderness-terrain::terrain-and-political-control-derive-from-authored-geography")
    @covers_requirement(
        "wilderness-terrain::"
        "the-physical-ridge-is-a-continuous-forked-barrier"
    )
    def test_unexempted_stem_rows_and_arm_tips_are_closed_walls(self):
        # Derived from the authored stem and its declared pass rows: every
        # active stem row outside a pass is walled at its centre.
        stem = terrain().ridge_stem
        passes = terrain().ridge_passes
        for y in range(stem[0][1], stem[-1][1] + 1):
            if any(low <= y <= high for low, high in passes):
                continue
            centre = (ridge_center_x(terrain(), y), y)
            self.assertTrue(is_closed_ridge_cell(centre), y)
            self.assertFalse(is_valid_wilderness_cell(centre), y)
        # The stem's crotch and both arm tips are closed cliff walls.
        self.assertTrue(is_closed_ridge_cell(stem[-1]))
        for crest in ("west", "east"):
            tip = terrain().ridge_branches[crest][-1]
            self.assertTrue(is_closed_ridge_cell(tip), crest)
            self.assertFalse(is_closed_ridge_cell((tip[0], tip[1] + 1)), crest)

    @covers_requirement("wilderness-terrain::terrain-and-political-control-derive-from-authored-geography")
    def test_rivers_are_authored_water_with_declared_fords(self):
        # Every ford lies on its own river and is walkable land; every other
        # land cell of any river is impassable inland water.
        from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY

        entries = list(WILDERNESS_ENTRY_REGISTRY.values())
        routes = terrain().waterway_routes
        all_fords = {ford for fords in terrain().waterway_fords.values() for ford in fords}
        for name, fords in terrain().waterway_fords.items():
            raster = rasterize_routes({name: routes[name]})
            for ford in fords:
                self.assertIn(ford, raster, name)
                self.assertFalse(is_inland_water_cell(ford), name)
                self.assertTrue(is_land_cell(ford), name)
                # Walkable land is the requirement's own claim: in frame, on
                # the mainland and free of a closed ridge wall.
                self.assertTrue(wilderness_provider.is_walkable_cell(ford), name)
                if any(ford in entry.footprint_cells for entry in entries):
                    # A settlement may own its ford as the gateway cell the
                    # town grew at: the footprint then covers the crossing and
                    # travellers enter through the gate. The cell is claimed,
                    # never silently reclassified, so it must be invalid for
                    # ordinary wilderness steps.
                    self.assertFalse(is_valid_wilderness_cell(ford), name)
                else:
                    self.assertTrue(is_valid_wilderness_cell(ford), name)
        land_water = [
            cell for cell in rasterize_routes(routes) - all_fords if is_land_cell(cell)
        ]
        self.assertTrue(land_water)
        for cell in land_water:
            self.assertTrue(is_inland_water_cell(cell), cell)
            self.assertFalse(is_valid_wilderness_cell(cell), cell)

    @covers_requirement("wilderness-map-provider::the-continent-remains-virtual-with-bounded-local-lookup")
    def test_anchor_and_port_centres_are_land_side(self):
        from world.lore.anchors import anchor_geography
        from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
        from world.lore.wilderness_regions import harbor_sites

        for anchor in anchor_geography().values():
            self.assertTrue(is_land_cell(anchor.cell), anchor.anchor_key)
        for harbor in harbor_sites().values():
            self.assertTrue(is_land_cell(harbor.cell), harbor.key)
        # Declaration reveals nothing: no settlement map is invented for the
        # unbuilt anchors.
        self.assertLessEqual(
            set(WILDERNESS_ENTRY_REGISTRY), set(anchor_geography())
        )


# --- Border river, forest edge and nominal claims (author-border-river-and-forest-edge)

#: Sample stride for land-share estimates (a 5 km lattice, ~200,000 land cells).
_SHARE_STRIDE = 5


def _land_sample():
    for y in range(0, wilderness_provider.WILDERNESS_MAX_Y + 1, _SHARE_STRIDE):
        for x in range(0, wilderness_provider.WILDERNESS_MAX_X + 1, _SHARE_STRIDE):
            if is_land_cell((x, y)):
                yield x, y


def _mainland_row_intervals(y: int) -> list[tuple[int, int]]:
    """Inclusive land-cell X intervals of row ``y`` (cell centres in polygon).

    Uses the same even-odd crossing rule as ``is_on_mainland`` at the row's
    centre line; callers cross-check every interval end against
    ``is_land_cell``.
    """
    north = y + 0.5
    vertices = mainland_boundary_km()
    crossings = []
    for index, (start_east, start_north) in enumerate(vertices):
        end_east, end_north = vertices[(index + 1) % len(vertices)]
        if (start_north > north) == (end_north > north):
            continue
        crossings.append(
            (end_east - start_east) * (north - start_north) / (end_north - start_north)
            + start_east
        )
    crossings.sort()
    intervals = []
    for west, east in zip(crossings[::2], crossings[1::2]):
        low = math.ceil(west - 0.5)
        high = math.floor(east - 0.5)
        if low <= high:
            intervals.append((max(low, 0), min(high, wilderness_provider.WILDERNESS_MAX_X)))
    return intervals


class _RunComponents:
    """Exact 4-connected components of walkable cells, as row runs.

    ``wilderness_neighbor`` only allows a diagonal step when both orthogonal
    cells are walkable, so 8-direction reachability equals 4-connectivity of
    ``is_valid_wilderness_cell`` cells. Each row is its mainland intervals
    minus the cells the shared validity rule rejects; runs in adjacent rows
    that share a column are joined. ``extra_blocked`` adds hypothetical
    obstacles (for example, the fords) to prove what they control.
    """

    def __init__(self, testcase, extra_blocked=frozenset()):
        from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY

        candidates: dict[int, set[int]] = {}
        for x, y in rasterize_routes(terrain().waterway_routes):
            candidates.setdefault(y, set()).add(x)
        for entry in WILDERNESS_ENTRY_REGISTRY.values():
            for x, y in entry.footprint_cells:
                candidates.setdefault(y, set()).add(x)
        self.runs: list[tuple[int, int, int]] = []
        self.row_runs: dict[int, list[int]] = {}
        self.parent: list[int] = []
        previous: list[int] = []
        for y in range(wilderness_provider.WILDERNESS_MAX_Y + 1):
            row_candidates = set(candidates.get(y, ()))
            for low, high in ridge_spans(terrain(), y):
                row_candidates.update(range(low, high + 1))
            row_candidates |= {x for x, row in extra_blocked if row == y}
            current: list[int] = []
            for west, east in _mainland_row_intervals(y):
                testcase.assertTrue(is_land_cell((west, y)), (west, y))
                testcase.assertTrue(is_land_cell((east, y)), (east, y))
                testcase.assertFalse(is_land_cell((west - 1, y)), (west - 1, y))
                testcase.assertFalse(is_land_cell((east + 1, y)), (east + 1, y))
                blocked = sorted(
                    x
                    for x in row_candidates
                    if west <= x <= east
                    and ((x, y) in extra_blocked or not is_valid_wilderness_cell((x, y)))
                )
                start = west
                for x in blocked + [east + 1]:
                    if x > start:
                        current.append(self._add_run(y, start, x - 1))
                    start = x + 1
            self.row_runs[y] = current
            for run in current:
                _, run_low, run_high = self.runs[run]
                for other in previous:
                    _, other_low, other_high = self.runs[other]
                    if run_low <= other_high and other_low <= run_high:
                        self._union(run, other)
            previous = current

    def _add_run(self, y, low, high):
        self.runs.append((y, low, high))
        self.parent.append(len(self.parent))
        return len(self.runs) - 1

    def _find(self, run):
        while self.parent[run] != run:
            self.parent[run] = self.parent[self.parent[run]]
            run = self.parent[run]
        return run

    def _union(self, first, second):
        self.parent[self._find(first)] = self._find(second)

    def component(self, cell):
        x, y = cell
        for run in self.row_runs.get(y, ()):
            _, low, high = self.runs[run]
            if low <= x <= high:
                return self._find(run)
        return None


def _bounded_reachable(start, goal, box, blocked=frozenset()):
    """Oracle BFS through ``wilderness_neighbor`` inside an inclusive box."""
    from world.maps.wilderness_destination import (
        DIRECTION_DELTAS,
        wilderness_neighbor,
    )

    x_min, x_max, y_min, y_max = box
    seen = {start}
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        if cell == goal:
            return True
        for direction, (dx, dy) in DIRECTION_DELTAS.items():
            target = wilderness_neighbor(cell[0], cell[1], direction)
            if target is None or target in seen or target in blocked:
                continue
            if dx and dy and (
                (cell[0] + dx, cell[1]) in blocked or (cell[0], cell[1] + dy) in blocked
            ):
                continue
            if not (x_min <= target[0] <= x_max and y_min <= target[1] <= y_max):
                continue
            seen.add(target)
            queue.append(target)
    return False


def _anchor_targets(anchor_key, cell):
    """The walkable cells that stand for an anchor on the wilderness."""
    from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY

    if is_valid_wilderness_cell(cell):
        return (cell,)
    entry = WILDERNESS_ENTRY_REGISTRY[anchor_key]
    return tuple(entry.approach_cell(gate) for gate in entry.gates)


class BorderRiverContractTests(unittest.TestCase):
    @covers_requirement("wilderness-terrain::the-border-river-controls-western-crossing-and-classification")
    def test_river_course_stays_in_the_authored_band_from_corridor_to_coast(self):
        route = terrain().waterway_routes["border_river"]
        source, mouth = route[0], route[-1]
        # Source in the western hills, west of the authored stem centre; the
        # course runs west to the coast.
        self.assertEqual(region_for_coordinates(*source), "western_hills_valleys")
        self.assertLess(source[0], ridge_center_x(terrain(), source[1]))
        self.assertLess(mouth[0], source[0])
        # The mouth is the last land cell of its row; its western neighbour is
        # sea, so the river reaches the coast instead of stopping inland.
        self.assertTrue(is_land_cell(mouth))
        self.assertFalse(is_land_cell((mouth[0] - 1, mouth[1])))
        # Outside the river's span the end rows continue: the source row runs
        # east to the ridge as the claim line, the mouth row west to the sea.
        self.assertEqual(border_river_row(source[0] + 50), source[1])
        self.assertEqual(border_river_row(mouth[0] - 50), mouth[1])
        for bend in route:
            self.assertLessEqual(abs(border_river_row(bend[0]) - bend[1]), 10, bend)
        # One water cell per column, exactly the classifier's river row.
        raster = rasterize_routes({"border_river": route})
        columns = {}
        for x, y in raster:
            columns.setdefault(x, set()).add(y)
        self.assertEqual(set(columns), set(range(mouth[0], source[0] + 1)))
        for x, rows in columns.items():
            self.assertEqual(rows, {border_river_row(x)}, x)
            self.assertGreaterEqual(border_river_row(x), min(row for _, row in route))
            self.assertLessEqual(border_river_row(x), max(row for _, row in route))
        # No other waterway, ridge cell or anchor footprint is touched.
        others = rasterize_routes(
            {name: points for name, points in terrain().waterway_routes.items() if name != "border_river"}
        )
        self.assertFalse(raster & others)
        self.assertFalse(any(is_closed_ridge_cell(cell) for cell in raster))

    @covers_requirement("wilderness-terrain::the-border-river-controls-western-crossing-and-classification")
    def test_border_fords_are_the_only_walkable_river_cells(self):
        fords = terrain().waterway_fords["border_river"]
        self.assertTrue(fords)
        self.assertEqual(len(set(fords)), len(fords))
        raster = rasterize_routes({"border_river": terrain().waterway_routes["border_river"]})
        for ford in fords:
            self.assertIn(ford, raster)
            self.assertTrue(is_valid_wilderness_cell(ford), ford)
        water = {cell for cell in raster if is_inland_water_cell(cell)}
        self.assertEqual(raster - water, set(fords))

    @covers_requirement("wilderness-terrain::the-border-river-controls-western-crossing-and-classification")
    def test_river_cells_block_steps_and_the_ford_permits_the_crossing(self):
        from world.maps.wilderness_destination import wilderness_neighbor

        ford = terrain().waterway_fords["border_river"][1]
        x, y = ford
        # Ordinary foot movement into a river cell is refused, straight or
        # diagonally across the one-cell line.
        river_cell = (x + 3, border_river_row(x + 3))
        self.assertTrue(is_inland_water_cell(river_cell))
        below = (river_cell[0], river_cell[1] - 1)
        self.assertIsNone(wilderness_neighbor(*below, "n"))
        for column in range(x + 2, x + 40):
            row = border_river_row(column)
            for direction in ("ne", "nw"):
                self.assertIsNone(wilderness_neighbor(column, row - 1, direction), column)
        # The ford is ordinary ground: south bank -> ford -> north bank.
        self.assertEqual(wilderness_neighbor(x, y - 1, "n"), ford)
        self.assertEqual(wilderness_neighbor(x, y, "n"), (x, y + 1))
        self.assertTrue(
            _bounded_reachable((x, y - 20), (x, y + 20), (x - 40, x + 40, y - 30, y + 30))
        )
        self.assertFalse(
            _bounded_reachable(
                (x, y - 20), (x, y + 20), (x - 40, x + 40, y - 30, y + 30), frozenset({ford})
            )
        )

    @covers_requirement("wilderness-terrain::the-border-river-controls-western-crossing-and-classification")
    def test_west_of_the_corridor_only_the_fords_cross_the_border(self):
        # Cut the continent along the river's source column. West of the cut
        # the river is a complete barrier except at its declared fords; the
        # bank cells beside one ford stand for the two sides of the border.
        fords = frozenset(terrain().waterway_fords["border_river"])
        source_x = terrain().waterway_routes["border_river"][0][0]
        cut = frozenset((source_x, y) for y in range(wilderness_provider.WILDERNESS_MAX_Y + 1))
        ford_x, ford_y = terrain().waterway_fords["border_river"][0]
        south, north = (ford_x, ford_y - 1), (ford_x, ford_y + 1)
        self.assertTrue(is_valid_wilderness_cell(south), south)
        self.assertTrue(is_valid_wilderness_cell(north), north)
        self.assertLess(ford_x, source_x)
        for blocked, connected in (
            (frozenset(), True),
            (fords, True),
            (cut, True),
            (cut | fords, False),
        ):
            components = _RunComponents(self, blocked)
            self.assertEqual(
                components.component(south) == components.component(north),
                connected,
                (len(blocked), connected),
            )
        # Each ford alone is enough to cross west of the cut.
        for ford in fords:
            components = _RunComponents(self, cut | (fords - {ford}))
            self.assertEqual(components.component(south), components.component(north), ford)

    @covers_requirement("wilderness-terrain::the-border-river-controls-western-crossing-and-classification")
    def test_classifier_and_claims_flip_across_the_river(self):
        route = terrain().waterway_routes["border_river"]
        source_x, mouth_x = route[0][0], route[-1][0]
        for x in range(mouth_x + 1, source_x, max(1, (source_x - mouth_x) // 6)):
            row = border_river_row(x)
            self.assertEqual(region_for_coordinates(x, row - 1), "western_hills_valleys")
            self.assertEqual(region_for_coordinates(x, row + 1), "northwest_highland_forest")
            self.assertEqual(nominal_nation_for_coordinates(x, row), "altoria")
            self.assertEqual(nominal_nation_for_coordinates(x, row + 1), "valhalla")
        # Between the source and the ridge the source row continues as the
        # claim line; east of the ridge everything is Grandia.
        junction_row = terrain().waterway_routes["border_river"][0][1]
        centre = ridge_center_x(terrain(), junction_row)
        self.assertEqual(nominal_nation_for_coordinates(centre, junction_row), "altoria")
        self.assertEqual(nominal_nation_for_coordinates(centre, junction_row + 1), "valhalla")
        self.assertEqual(nominal_nation_for_coordinates(centre + 1, junction_row + 1), "grandia")

    @covers_requirement("wilderness-terrain::the-border-river-controls-western-crossing-and-classification")
    def test_region_consumers_follow_the_amended_boundaries(self):
        # Monster placement and species-hunt region scoping consume cells on
        # both banks of the river and both sides of the forest edge.
        from world.lore.monster_placement import AMBIENT_PLACEMENT_REGISTRY
        from world.maps.wilderness_population import (
            population_for_coordinates,
            species_rule_for_coordinates,
        )
        from world.quests.room_observation import resolve_room_region

        probes = []
        for x in range(150, 2200, 97):
            for row in (border_river_row(x), forest_edge_row(x)):
                probes.extend((x, row + offset) for offset in (-2, -1, 1, 2))
        for cell in probes:
            if not is_valid_wilderness_cell(cell):
                continue
            region = region_for_coordinates(*cell)
            self.assertIn(region, regions(), cell)
            self.assertEqual(resolve_room_region(None, coordinates=cell), region, cell)
            self.assertEqual(
                species_rule_for_coordinates(*cell), AMBIENT_PLACEMENT_REGISTRY.get(region), cell
            )
            population_for_coordinates(*cell)  # every region has a tier row
        # Species placement windows enumerate only their amended region: the
        # highland forest lies north of the river and south of the forest edge.
        rule = AMBIENT_PLACEMENT_REGISTRY["northwest_highland_forest"]
        cells = _rule_cells("northwest_highland_forest", rule)
        for _ in range(200):
            x, y = next(cells)
            self.assertGreater(y, border_river_row(x))
            self.assertLess(y, forest_edge_row(x))
        hills = AMBIENT_PLACEMENT_REGISTRY["western_hills_valleys"]
        cells = _rule_cells("western_hills_valleys", hills)
        for _ in range(200):
            x, y = next(cells)
            self.assertLessEqual(y, border_river_row(x))


class ForestEdgeAndClaimContractTests(unittest.TestCase):
    @covers_requirement("wilderness-terrain::terrain-and-political-control-derive-from-authored-geography")
    def test_forest_edge_spans_the_frame_and_starts_the_deep_forest(self):
        xs = [x for x, _ in terrain().forest_edge]
        self.assertEqual(xs, sorted(set(xs)))
        self.assertEqual((xs[0], xs[-1]), (0, wilderness_provider.WILDERNESS_MAX_X))
        for x in range(0, wilderness_provider.WILDERNESS_MAX_X + 1, 97):
            row = forest_edge_row(x)
            self.assertEqual(region_for_coordinates(x, row), "north_deep_forest", x)
            self.assertNotEqual(region_for_coordinates(x, row - 1), "north_deep_forest", x)

    @covers_requirement("wilderness-terrain::terrain-and-political-control-derive-from-authored-geography")
    @covers_requirement(
        "wilderness-terrain::"
        "the-physical-ridge-is-a-continuous-forked-barrier"
    )
    def test_forest_around_the_inland_tips_stays_walkable(self):
        from world.rules.travel_cost import WILDERNESS_TERRAIN

        # The stem ends at its crotch; the arms end inland and the very next
        # row north of each tip is walkable deep forest (the intended detour).
        crotch_y = terrain().ridge_stem[-1][1]
        self.assertIsNone(ridge_span(terrain(), crotch_y + 1))
        for crest in ("west", "east"):
            tip = terrain().ridge_branches[crest][-1]
            north = (tip[0], tip[1] + 1)
            self.assertFalse(is_closed_ridge_cell(north), crest)
            self.assertTrue(is_valid_wilderness_cell(north), crest)
            self.assertEqual(region_for_coordinates(*north), "north_deep_forest", crest)
        self.assertEqual(WILDERNESS_TERRAIN["north_deep_forest"], "woodland")

    @covers_requirement("wilderness-terrain::terrain-and-political-control-derive-from-authored-geography")
    def test_every_anchor_and_harbour_is_walkable_and_mutually_reachable(self):
        from world.lore.anchors import anchor_geography
        from world.lore.wilderness_regions import harbor_sites

        components = _RunComponents(self)
        hub_key = sorted(anchor_geography())[0]
        hub = components.component(
            _anchor_targets(hub_key, anchor_geography()[hub_key].cell)[0]
        )
        self.assertIsNotNone(hub)
        for key, anchor in anchor_geography().items():
            for cell in _anchor_targets(key, anchor.cell):
                self.assertTrue(is_valid_wilderness_cell(cell), (key, cell))
                self.assertEqual(components.component(cell), hub, (key, cell))
        for key, harbour in harbor_sites().items():
            self.assertTrue(is_valid_wilderness_cell(harbour.cell), key)
            self.assertEqual(components.component(harbour.cell), hub, key)

    @covers_requirement("wilderness-terrain::terrain-and-political-control-derive-from-authored-geography")
    def test_every_land_cell_has_one_nominal_nation_agreeing_with_its_region(self):
        from world.lore.nations import NATION_REGISTRY

        seen_by_region = {}
        for x, y in _land_sample():
            nation = nominal_nation_for_coordinates(x, y)
            self.assertIn(nation, NATION_REGISTRY, (x, y))
            region = region_for_coordinates(x, y)
            self.assertIn(
                nation, regions()[region].nominal_nation_keys, (x, y)
            )
            seen_by_region.setdefault(region, set()).add(nation)
        for key, region in regions().items():
            self.assertEqual(seen_by_region[key], set(region.nominal_nation_keys), key)
            if region.nation_key is not None:
                self.assertEqual(region.nominal_nation_keys, (region.nation_key,), key)

    @covers_requirement("wilderness-terrain::terrain-and-political-control-derive-from-authored-geography")
    def test_displayed_borders_derive_from_ridge_and_river_outside_the_forest(self):
        borders = {border.nation_keys: border.points for border in national_borders()}
        self.assertEqual(
            set(borders),
            {("altoria", "valhalla"), ("altoria", "grandia"), ("grandia", "valhalla")},
        )
        river = borders[("altoria", "valhalla")]
        self.assertEqual(river[: len(terrain().waterway_routes["border_river"])],
                         tuple(reversed(terrain().waterway_routes["border_river"])))
        source_row = terrain().waterway_routes["border_river"][0][1]
        self.assertEqual(river[-1], (ridge_center_x(terrain(), source_row), source_row))
        south = borders[("altoria", "grandia")]
        north = borders[("grandia", "valhalla")]
        self.assertTrue(is_land_cell(south[0]))
        self.assertFalse(is_land_cell((south[0][0], south[0][1] - 1)))
        self.assertEqual(south[-1], north[0])
        self.assertEqual(north[0], river[-1])
        # The ridge line stops at the forest edge: no point lies in the forest
        # and the next row north of the last point is forest.
        for line in borders.values():
            for point in line:
                self.assertNotEqual(region_for_coordinates(*point), "north_deep_forest", point)
        end_x, end_y = north[-1]
        self.assertEqual(
            region_for_coordinates(ridge_center_x(terrain(), end_y + 1), end_y + 1), "north_deep_forest"
        )
        # Every ridge-line point is the ridge centre of its row, and the cells
        # beside each line resolve to the line's two nations.
        for keys in (("altoria", "grandia"), ("grandia", "valhalla")):
            for x, y in borders[keys]:
                self.assertEqual(x, ridge_center_x(terrain(), y))
                if (x, y) == river[-1]:
                    continue  # the three-way junction with the river line
                self.assertEqual(
                    {nominal_nation_for_coordinates(x, y), nominal_nation_for_coordinates(x + 1, y)},
                    set(keys),
                )


if __name__ == "__main__":
    unittest.main()
