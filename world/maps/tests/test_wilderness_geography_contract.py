"""Data-contract test: authored continental terrain, waterway and anchor-region data contract

The signed geography rows are shipped content, so this module names them: every
anchor's terrain, the bending mountain corridor and its authored pass, and the
capital/imperial waterways with their declared fords must agree with the
classifier. Mechanics (purity, bounds, pooled rooms, gate locks) stay in
``world/maps/tests/test_wilderness_provider.py`` (map-wilderness,
wilderness-anchor-footprint, rescale-wilderness-geography).
"""

from tools.spec_traceability import covers_requirement

import math
import unittest
from collections import deque

from elosern_map_core.terrain import rasterize_routes, ridge_center_x, ridge_span

from world.lore.wilderness_regions import (
    MAINLAND_BOUNDARY_KM,
    WILDERNESS_REGION_REGISTRY,
)
from world.maps.wilderness_provider import (
    NORTH_FOREST_EDGE,
    RIDGE_PASSES,
    WATERWAY_FORDS,
    WATERWAY_ROUTES,
    TERRAIN,
    WILDERNESS_MAX_X,
    WILDERNESS_MAX_Y,
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


class AuthoredTerrainContractTests(unittest.TestCase):
    @covers_requirement("wilderness-terrain::region-for-coordinates-is-a-pure-deterministic-function-covering-the-whole-bounded-map")
    def test_central_mountain_region_bends_with_the_authored_corridor(self):
        # The corridor follows the bending summit centre; it is neither a fixed
        # rectangular band nor a continuous summit wall (the pass windows below
        # are open ground).
        for y in (150, 700, 1200, 1800):
            centre = ridge_center_x(TERRAIN, y)
            self.assertEqual(region_for_coordinates(centre, y), "central_mountains")
            self.assertNotEqual(
                region_for_coordinates(centre - 300, y), "central_mountains"
            )
            self.assertNotEqual(
                region_for_coordinates(centre + 300, y), "central_mountains"
            )
        self.assertNotEqual(ridge_center_x(TERRAIN, 100), ridge_center_x(TERRAIN, 1200))

    @covers_requirement("wilderness-terrain::region-for-coordinates-is-a-pure-deterministic-function-covering-the-whole-bounded-map")
    def test_settlement_derived_anchor_cells_resolve_to_altoria_territory(self):
        from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY

        entry = WILDERNESS_ENTRY_REGISTRY["capital_altoria"]
        cells = {entry.anchor_cell} | {
            entry.approach_cell(gate) for gate in entry.gates
        }
        self.assertTrue(cells, "the capital entry must supply anchor and gate cells")
        # Delta scenario: Altoria's anchor and both gate approaches are the
        # western hills and valleys (the signed anchor relationships).
        for cell in cells:
            self.assertEqual(region_for_coordinates(*cell), "western_hills_valleys")

    @covers_requirement("wilderness-terrain::terrain-and-political-control-follow-authored-geography")
    def test_anchor_centres_resolve_their_authored_terrain(self):
        # Region keys are the terrain layer; nominal claims stay in
        # ``world.lore.nations``. The authored anchor relationships pin which
        # terrain each canonical anchor cell belongs to.
        from world.lore.anchors import ANCHOR_GEOGRAPHY_REGISTRY

        expected = {
            "capital_altoria": "western_hills_valleys",
            "capital_valhalla": "northwest_highland_forest",
            "capital_grandia": "eastern_plains",
            "village_ciaran": "central_mountains",
            "village_fionnen": "central_mountains",
            # The hidden valley sits north of the meandering forest edge.
            "village_eolas": "north_deep_forest",
            "dungeon_eternal_night": "north_deep_forest",
            "dungeon_dragon_nest": "eastern_plains",
            "dungeon_arcane_ruins": "western_hills_valleys",
        }
        for anchor_key, region_key in expected.items():
            cell = ANCHOR_GEOGRAPHY_REGISTRY[anchor_key].cell
            self.assertEqual(region_for_coordinates(*cell), region_key, anchor_key)

    @covers_requirement("wilderness-terrain::terrain-description-is-a-pure-deterministic-function-with-no-llm-or-randomness")
    def test_description_formula_is_pinned_at_a_literal_coordinate(self):
        # (860 * 92821 + 1080 * 68917) % 3 == 2 selects the third western-hills
        # variant: the arithmetic constants and the flavor text are authored.
        self.assertEqual(
            terrain_description(860, 1080),
            "低緩的丘陵覆滿灌木與野花，羊群在坡地上安靜地啃食。",
        )

    @covers_requirement("wilderness-terrain::terrain-and-political-control-follow-authored-geography")
    def test_principal_pass_is_open_mountain_trail_and_ridge_blocks_elsewhere(self):
        from world.rules.travel_cost import WILDERNESS_TERRAIN, terrain_speed_m_per_hour

        # The principal pass near (1410, 980) is open ground in the mountain
        # region, costed as mountain trail: an explicit slower crossing, never
        # an all-road shortcut.
        self.assertIn(980, range(*RIDGE_PASSES[1]))
        self.assertFalse(is_closed_ridge_cell((1410, 980)))
        self.assertEqual(region_for_coordinates(1410, 980), "central_mountains")
        mountain = terrain_speed_m_per_hour(WILDERNESS_TERRAIN["central_mountains"])
        self.assertLess(mountain, terrain_speed_m_per_hour("road"))
        # Away from an authored pass the summit ridge is a closed cliff wall.
        self.assertTrue(is_closed_ridge_cell((ridge_center_x(TERRAIN, 1200), 1200)))

    @covers_requirement("wilderness-terrain::terrain-and-political-control-follow-authored-geography")
    def test_rivers_are_authored_water_with_declared_fords(self):
        # Every ford lies on its own river, and every river starts and ends on
        # the coastal region it drains into (capital river -> southwest coast;
        # imperial rivers -> southeast coast).
        raster = rasterize_routes(WATERWAY_ROUTES)
        for name, fords in WATERWAY_FORDS.items():
            for ford in fords:
                # The ford is on its authored river before the exemption is
                # subtracted, so a typo cannot silently remove a crossing.
                self.assertIn(ford, raster, name)
                self.assertFalse(is_inland_water_cell(ford), name)
                self.assertTrue(is_land_cell(ford), name)
        capital = WATERWAY_ROUTES["capital_river"]
        self.assertEqual(region_for_coordinates(*capital[-1]), "southwest_coast")
        for name in ("imperial_river", "imperial_east_branch"):
            self.assertEqual(
                region_for_coordinates(*WATERWAY_ROUTES[name][-1]), "southeast_coast"
            )
        # A river cell is impassable water; its declared ford is ordinary land.
        river_cell = (900, 1042)
        self.assertTrue(is_inland_water_cell(river_cell))
        self.assertFalse(is_valid_wilderness_cell(river_cell))
        self.assertFalse(is_inland_water_cell(WATERWAY_FORDS["capital_river"][0]))
        self.assertTrue(is_valid_wilderness_cell(WATERWAY_FORDS["capital_river"][0]))

    @covers_requirement("wilderness-map-provider::the-continent-remains-virtual-with-bounded-local-lookup")
    def test_anchor_and_port_centres_are_land_side(self):
        from world.lore.anchors import ANCHOR_GEOGRAPHY_REGISTRY
        from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
        from world.lore.wilderness_regions import HARBOR_SITE_REGISTRY

        for anchor in ANCHOR_GEOGRAPHY_REGISTRY.values():
            self.assertTrue(is_land_cell(anchor.cell), anchor.anchor_key)
        for harbor in HARBOR_SITE_REGISTRY.values():
            self.assertTrue(is_land_cell(harbor.cell), harbor.key)
        # Declaration reveals nothing: no settlement map is invented for the
        # seven unbuilt anchors.
        self.assertLessEqual(
            set(WILDERNESS_ENTRY_REGISTRY), set(ANCHOR_GEOGRAPHY_REGISTRY)
        )


# --- Border river, forest edge and nominal claims (author-border-river-and-forest-edge)

#: Sample stride for land-share estimates (a 5 km lattice, ~200,000 land cells).
_SHARE_STRIDE = 5


def _land_sample():
    for y in range(0, WILDERNESS_MAX_Y + 1, _SHARE_STRIDE):
        for x in range(0, WILDERNESS_MAX_X + 1, _SHARE_STRIDE):
            if is_land_cell((x, y)):
                yield x, y


def _mainland_row_intervals(y: int) -> list[tuple[int, int]]:
    """Inclusive land-cell X intervals of row ``y`` (cell centres in polygon).

    Uses the same even-odd crossing rule as ``is_on_mainland`` at the row's
    centre line; callers cross-check every interval end against
    ``is_land_cell``.
    """
    north = y + 0.5
    vertices = MAINLAND_BOUNDARY_KM
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
            intervals.append((max(low, 0), min(high, WILDERNESS_MAX_X)))
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
        for x, y in rasterize_routes(WATERWAY_ROUTES):
            candidates.setdefault(y, set()).add(x)
        for entry in WILDERNESS_ENTRY_REGISTRY.values():
            for x, y in entry.footprint_cells:
                candidates.setdefault(y, set()).add(x)
        self.runs: list[tuple[int, int, int]] = []
        self.row_runs: dict[int, list[int]] = {}
        self.parent: list[int] = []
        previous: list[int] = []
        for y in range(WILDERNESS_MAX_Y + 1):
            low, high = ridge_span(TERRAIN, y)
            row_candidates = set(candidates.get(y, ())) | set(range(low, high + 1))
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
        route = WATERWAY_ROUTES["border_river"]
        source, mouth = route[0], route[-1]
        # Source in the central range's western foothills near (1300, 1410).
        self.assertEqual(source, (1320, 1410))
        self.assertEqual(region_for_coordinates(*source), "central_mountains")
        self.assertEqual(source[0], ridge_center_x(TERRAIN, source[1]) - 100)
        # The mouth is the last land cell; its western neighbour is sea.
        self.assertLessEqual(abs(mouth[0] - 170), 50)
        self.assertEqual(mouth[1], 1290)
        self.assertTrue(is_land_cell(mouth))
        self.assertFalse(is_land_cell((mouth[0] - 1, mouth[1])))
        # Outside the river's span the end rows continue: the source row runs
        # east to the ridge as the claim line, the mouth row west to the sea.
        self.assertEqual(border_river_row(source[0] + 50), source[1])
        self.assertEqual(border_river_row(mouth[0] - 50), mouth[1])
        for bend in ((1100, 1350), (900, 1380), (650, 1310), (400, 1340)):
            self.assertLessEqual(abs(border_river_row(bend[0]) - bend[1]), 10, bend)
        # One water cell per column, exactly the classifier's river row, every
        # row inside Y 1290..1410.
        raster = rasterize_routes({"border_river": route})
        columns = {}
        for x, y in raster:
            columns.setdefault(x, set()).add(y)
        self.assertEqual(set(columns), set(range(mouth[0], source[0] + 1)))
        for x, rows in columns.items():
            self.assertEqual(rows, {border_river_row(x)}, x)
            self.assertTrue(1290 <= border_river_row(x) <= 1410, x)
        # No other waterway, ridge cell or anchor footprint is touched.
        others = rasterize_routes(
            {name: points for name, points in WATERWAY_ROUTES.items() if name != "border_river"}
        )
        self.assertFalse(raster & others)
        self.assertFalse(any(is_closed_ridge_cell(cell) for cell in raster))

    @covers_requirement("wilderness-terrain::the-border-river-controls-western-crossing-and-classification")
    def test_exactly_three_fords_with_the_principal_on_the_capital_line(self):
        from world.lore.anchors import ANCHOR_GEOGRAPHY_REGISTRY

        fords = WATERWAY_FORDS["border_river"]
        self.assertEqual(len(fords), 3)
        raster = rasterize_routes({"border_river": WATERWAY_ROUTES["border_river"]})
        for ford in fords:
            self.assertIn(ford, raster)
            self.assertTrue(is_valid_wilderness_cell(ford), ford)
        water = {cell for cell in raster if is_inland_water_cell(cell)}
        self.assertEqual(raster - water, set(fords))
        upstream, principal, downstream = fords
        self.assertGreater(upstream[0], principal[0])
        self.assertLess(downstream[0], principal[0])
        self.assertLessEqual(abs(principal[0] - 830) + abs(principal[1] - 1370), 5)
        # The principal ford is on the straight line between the two capitals.
        (ax, ay) = ANCHOR_GEOGRAPHY_REGISTRY["capital_altoria"].cell
        (vx, vy) = ANCHOR_GEOGRAPHY_REGISTRY["capital_valhalla"].cell
        line_x = ax + (vx - ax) * (principal[1] - ay) / (vy - ay)
        self.assertLessEqual(abs(line_x - principal[0]), 5)

    @covers_requirement("wilderness-terrain::the-border-river-controls-western-crossing-and-classification")
    def test_river_cells_block_steps_and_the_ford_permits_the_crossing(self):
        from world.maps.wilderness_destination import wilderness_neighbor

        ford = WATERWAY_FORDS["border_river"][1]
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
        # the river is a complete barrier except at its three fords; the
        # remaining links (the mountain corridor around the source and the
        # ridge passes into Grandia) all lie east of the cut.
        from world.lore.anchors import ANCHOR_GEOGRAPHY_REGISTRY

        fords = frozenset(WATERWAY_FORDS["border_river"])
        source_x = WATERWAY_ROUTES["border_river"][0][0]
        cut = frozenset((source_x, y) for y in range(WILDERNESS_MAX_Y + 1))
        altoria = ANCHOR_GEOGRAPHY_REGISTRY["capital_altoria"]
        south = _anchor_targets("capital_altoria", altoria.cell)[0]
        north = ANCHOR_GEOGRAPHY_REGISTRY["capital_valhalla"].cell
        self.assertLess(max(south[0], north[0]), source_x)
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
        for x in (200, 450, 830, 1150, 1300):
            row = border_river_row(x)
            self.assertEqual(region_for_coordinates(x, row - 1), "western_hills_valleys")
            self.assertEqual(region_for_coordinates(x, row + 1), "northwest_highland_forest")
            self.assertEqual(nominal_nation_for_coordinates(x, row), "altoria")
            self.assertEqual(nominal_nation_for_coordinates(x, row + 1), "valhalla")
        # Between the source and the ridge the source row continues as the
        # claim line; east of the ridge everything is Grandia.
        centre = ridge_center_x(TERRAIN, 1410)
        self.assertEqual(nominal_nation_for_coordinates(centre, 1410), "altoria")
        self.assertEqual(nominal_nation_for_coordinates(centre, 1411), "valhalla")
        self.assertEqual(nominal_nation_for_coordinates(centre + 1, 1411), "grandia")

    @covers_requirement("wilderness-terrain::the-border-river-controls-western-crossing-and-classification")
    def test_region_consumers_follow_the_amended_boundaries(self):
        # Monster placement and species-hunt region scoping consume cells on
        # both banks of the river and both sides of the forest edge.
        from world.lore.monster_placement import AMBIENT_PLACEMENT_REGISTRY
        from world.maps.monster_provisioning import _candidate_cells
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
            self.assertIn(region, WILDERNESS_REGION_REGISTRY, cell)
            self.assertEqual(resolve_room_region(None, coordinates=cell), region, cell)
            self.assertEqual(
                species_rule_for_coordinates(*cell), AMBIENT_PLACEMENT_REGISTRY.get(region), cell
            )
            population_for_coordinates(*cell)  # every region has a tier row
        # Species placement windows enumerate only their amended region: the
        # highland forest lies north of the river and south of the forest edge.
        rule = AMBIENT_PLACEMENT_REGISTRY["northwest_highland_forest"]
        cells = _candidate_cells("northwest_highland_forest", rule)
        for _ in range(200):
            x, y = next(cells)
            self.assertGreater(y, border_river_row(x))
            self.assertLess(y, forest_edge_row(x))
        hills = AMBIENT_PLACEMENT_REGISTRY["western_hills_valleys"]
        cells = _candidate_cells("western_hills_valleys", hills)
        for _ in range(200):
            x, y = next(cells)
            self.assertLessEqual(y, border_river_row(x))


class ForestEdgeAndClaimContractTests(unittest.TestCase):
    @covers_requirement("wilderness-terrain::terrain-and-political-control-follow-authored-geography")
    def test_forest_edge_meanders_near_y1920_over_a_fifth_of_the_land(self):
        xs = [x for x, _ in NORTH_FOREST_EDGE]
        self.assertEqual(xs, sorted(set(xs)))
        self.assertEqual((xs[0], xs[-1]), (0, WILDERNESS_MAX_X))
        land_columns = [
            x for x in range(WILDERNESS_MAX_X + 1) if is_land_cell((x, forest_edge_row(x)))
        ]
        mean = sum(forest_edge_row(x) for x in land_columns) / len(land_columns)
        self.assertLessEqual(abs(mean - 1920), 15)
        self.assertGreater(len({forest_edge_row(x) for x in land_columns}), 20)
        land = forest = 0
        for x, y in _land_sample():
            land += 1
            forest += region_for_coordinates(x, y) == "north_deep_forest"
        self.assertLessEqual(abs(forest / land - 0.20), 0.02, round(forest / land, 4))

    @covers_requirement("wilderness-terrain::terrain-and-political-control-follow-authored-geography")
    def test_anchor_relationships_to_the_forest_edge(self):
        from world.lore.anchors import ANCHOR_GEOGRAPHY_REGISTRY

        valhalla = ANCHOR_GEOGRAPHY_REGISTRY["capital_valhalla"].cell
        self.assertEqual(valhalla, (780, 1910))
        self.assertEqual(forest_edge_row(780) - valhalla[1], 10)
        self.assertEqual(region_for_coordinates(*valhalla), "northwest_highland_forest")
        for key in ("village_eolas", "dungeon_eternal_night"):
            cell = ANCHOR_GEOGRAPHY_REGISTRY[key].cell
            self.assertEqual(region_for_coordinates(*cell), "north_deep_forest", key)
        self.assertEqual(
            nominal_nation_for_coordinates(*ANCHOR_GEOGRAPHY_REGISTRY["dungeon_eternal_night"].cell),
            "valhalla",
        )
        # The hidden valley sits inside nominal territory but stays outside
        # any nation's administration: its anchor identity keeps no nation.
        from world.lore.anchors import ANCHOR_REGISTRY

        # Altoria stays southwest in the hills and river valleys; Ciaran is on
        # the range's western flank and Fionnen on its eastern flank.
        altoria = ANCHOR_GEOGRAPHY_REGISTRY["capital_altoria"].cell
        self.assertEqual(region_for_coordinates(*altoria), "western_hills_valleys")
        self.assertEqual(nominal_nation_for_coordinates(*altoria), "altoria")
        ciaran = ANCHOR_GEOGRAPHY_REGISTRY["village_ciaran"].cell
        fionnen = ANCHOR_GEOGRAPHY_REGISTRY["village_fionnen"].cell
        self.assertLess(ciaran[0], ridge_center_x(TERRAIN, ciaran[1]))
        self.assertGreater(fionnen[0], ridge_center_x(TERRAIN, fionnen[1]))
        self.assertEqual(nominal_nation_for_coordinates(*ciaran), "altoria")
        self.assertEqual(nominal_nation_for_coordinates(*fionnen), "grandia")
        eolas = ANCHOR_GEOGRAPHY_REGISTRY["village_eolas"].cell
        self.assertEqual(nominal_nation_for_coordinates(*eolas), "grandia")
        self.assertIsNone(ANCHOR_REGISTRY["village_eolas"].nation_key)

    @covers_requirement("wilderness-terrain::terrain-and-political-control-follow-authored-geography")
    def test_ridge_northern_limit_passes_and_forest_speed_are_unchanged(self):
        from world.rules.travel_cost import WILDERNESS_TERRAIN

        self.assertEqual(RIDGE_PASSES, ((410, 425), (970, 990), (1770, 1785)))
        # The ridge still closes inside the forest up to Y 2199 and stops there.
        self.assertTrue(is_closed_ridge_cell((ridge_center_x(TERRAIN, 2199), 2199)))
        self.assertFalse(is_closed_ridge_cell((ridge_center_x(TERRAIN, 2200), 2200)))
        self.assertEqual(region_for_coordinates(ridge_center_x(TERRAIN, 2100), 2100), "north_deep_forest")
        self.assertEqual(WILDERNESS_TERRAIN["north_deep_forest"], "woodland")
        # Forest cells off the ridge stay walkable (no new movement block).
        self.assertTrue(is_valid_wilderness_cell((900, 2350)))
        self.assertTrue(is_valid_wilderness_cell((700, 1960)))

    @covers_requirement("wilderness-terrain::terrain-and-political-control-follow-authored-geography")
    def test_every_anchor_and_harbour_is_walkable_and_mutually_reachable(self):
        from world.lore.anchors import ANCHOR_GEOGRAPHY_REGISTRY
        from world.lore.wilderness_regions import HARBOR_SITE_REGISTRY

        components = _RunComponents(self)
        altoria = ANCHOR_GEOGRAPHY_REGISTRY["capital_altoria"]
        hub = components.component(_anchor_targets("capital_altoria", altoria.cell)[0])
        self.assertIsNotNone(hub)
        for key, anchor in ANCHOR_GEOGRAPHY_REGISTRY.items():
            for cell in _anchor_targets(key, anchor.cell):
                self.assertTrue(is_valid_wilderness_cell(cell), (key, cell))
                self.assertEqual(components.component(cell), hub, (key, cell))
        for key, harbour in HARBOR_SITE_REGISTRY.items():
            self.assertTrue(is_valid_wilderness_cell(harbour.cell), key)
            self.assertEqual(components.component(harbour.cell), hub, key)

    @covers_requirement("wilderness-terrain::terrain-and-political-control-follow-authored-geography")
    def test_every_land_cell_has_one_nominal_nation_with_authored_shares(self):
        from world.lore.nations import NATION_REGISTRY

        counts = {key: 0 for key in NATION_REGISTRY}
        seen_by_region = {}
        for x, y in _land_sample():
            nation = nominal_nation_for_coordinates(x, y)
            counts[nation] += 1
            region = region_for_coordinates(x, y)
            self.assertIn(
                nation, WILDERNESS_REGION_REGISTRY[region].nominal_nation_keys, (x, y)
            )
            seen_by_region.setdefault(region, set()).add(nation)
        total = sum(counts.values())
        # Deliberate geometry pins: moving a ridge, river or edge vertex
        # changes these measured shares.
        for nation, share in (("grandia", 0.43), ("altoria", 0.30), ("valhalla", 0.27)):
            measured = counts[nation] / total
            self.assertLessEqual(abs(measured - share), 0.015, (nation, round(measured, 4)))
        for key, region in WILDERNESS_REGION_REGISTRY.items():
            self.assertEqual(seen_by_region[key], set(region.nominal_nation_keys), key)
            if region.nation_key is not None:
                self.assertEqual(region.nominal_nation_keys, (region.nation_key,), key)
            else:
                self.assertGreater(len(region.nominal_nation_keys), 1, key)
        # Both shared terrain regions span several claims.
        self.assertIsNone(WILDERNESS_REGION_REGISTRY["central_mountains"].nation_key)
        self.assertIsNone(WILDERNESS_REGION_REGISTRY["north_deep_forest"].nation_key)

    @covers_requirement("wilderness-terrain::terrain-and-political-control-follow-authored-geography")
    def test_effective_rule_targets_are_unchanged(self):
        from world.lore.nations import NATION_REGISTRY

        self.assertEqual(
            {key: nation.territory_share for key, nation in NATION_REGISTRY.items()},
            {"grandia": 0.38, "altoria": 0.27, "valhalla": 0.25},
        )

    @covers_requirement("wilderness-terrain::terrain-and-political-control-follow-authored-geography")
    def test_displayed_borders_derive_from_ridge_and_river_outside_the_forest(self):
        borders = {border.nation_keys: border.points for border in national_borders()}
        self.assertEqual(
            set(borders),
            {("altoria", "valhalla"), ("altoria", "grandia"), ("grandia", "valhalla")},
        )
        river = borders[("altoria", "valhalla")]
        self.assertEqual(river[: len(WATERWAY_ROUTES["border_river"])],
                         tuple(reversed(WATERWAY_ROUTES["border_river"])))
        self.assertEqual(river[-1], (ridge_center_x(TERRAIN, 1410), 1410))
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
            region_for_coordinates(ridge_center_x(TERRAIN, end_y + 1), end_y + 1), "north_deep_forest"
        )
        # Every ridge-line point is the ridge centre of its row, and the cells
        # beside each line resolve to the line's two nations.
        for keys in (("altoria", "grandia"), ("grandia", "valhalla")):
            for x, y in borders[keys]:
                self.assertEqual(x, ridge_center_x(TERRAIN, y))
                if (x, y) == river[-1]:
                    continue  # the three-way junction with the river line
                self.assertEqual(
                    {nominal_nation_for_coordinates(x, y), nominal_nation_for_coordinates(x + 1, y)},
                    set(keys),
                )


if __name__ == "__main__":
    unittest.main()
