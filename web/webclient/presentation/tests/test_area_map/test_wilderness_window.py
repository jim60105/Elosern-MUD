"""The area_map wilderness journeys (wilderness window)."""

from unittest import mock
from tools.spec_traceability import covers_requirement
from web.webclient.presentation import area_map as area_map_module
from web.webclient.presentation.map_panels import WILDERNESS_WINDOW
from web.webclient.presentation.protocol import json_byte_size
from world.rules.clock import get_world_clock
from world.rules.map_knowledge import parse_knowledge
from ..test_local_map._support import EAST_APPROACH, EAST_GATE_XYZ, _T_MAP_KEY, _live, _t_anchor_display, _t_grid_id, _t_region_display_for, _t_wild_id
from ._support import _render, _by_id, _edge_set, _decode_overview, _js_accepts, _decode_rows


from ._wilderness_fixture import _WildernessFixture

class WildernessWindowTests(_WildernessFixture):
    """One wilderness reading rule per journey."""

    @covers_requirement(
        "webclient-area-map::wilderness-area-maps-cover-a-revealed-forty-one-cell-neighbourhood"
    )
    def test_window_is_centred_run_length_encoded_and_flags_visits(self):
        start = self._away()
        self._at_wild(start)
        self._pin({start: 3, (start[0] - 1, start[1]): 0})
        payload = _render(self.char1)
        self.assertEqual(payload["schema_version"], 4)
        self.assertEqual(payload["layer"], "wilderness")
        self.assertEqual(payload["frame"]["unit"], "km")
        half = WILDERNESS_WINDOW // 2
        self.assertEqual(WILDERNESS_WINDOW, 41)
        self.assertEqual(
            payload["window"],
            {"min_x": start[0] - half, "min_y": start[1] - half, "width": 41, "height": 41},
        )
        self.assertEqual(len(payload["rows"]), 41)
        for runs in payload["rows"]:
            self.assertEqual(sum(run["length"] for run in runs), 41)
        cells = _decode_rows(payload)
        in_disc = _live("world.rules.sight", "in_ground_disc")
        for cell, facts in cells.items():
            expected = in_disc(start, cell, 3) or cell == (start[0] - 1, start[1])
            self.assertEqual(facts is not None, expected, cell)
        km = _live("world.maps.wilderness_provider", "WILDERNESS_KM_PER_CELL")
        nodes = _by_id(payload)
        current = nodes[_t_wild_id(*start)]
        self.assertEqual((current["visibility"], current["visited"]), ("current", True))
        self.assertEqual((current["x"], current["y"]), ((start[0] + 0.5) * km, (start[1] + 0.5) * km))
        west = nodes[_t_wild_id(start[0] - 1, start[1])]
        self.assertEqual((west["visibility"], west["visited"]), ("visited", True))
        # Every node sits on a revealed cell; nothing outside the window.
        for node in payload["nodes"]:
            if node["id"].startswith("wild:"):
                parts = node["id"].split(":")
                self.assertIsNotNone(cells[(int(parts[2]), int(parts[3]))], node["id"])
        district_at = _live("world.maps.district_partition", "district_at")
        districts = _live("world.lore.map_districts", "current")().districts
        self.assertEqual(payload["district_name"], districts[district_at(start)].district_name_zh)
        self.assertEqual(payload["title"], _t_region_display_for(*start))
        self.assertEqual(payload["cell_km"], km)
        self.assertIn(payload["light_phase"], ("day", "dusk", "night", "dawn"))
        self.assertTrue(_js_accepts(payload))

    @covers_requirement(
        "wilderness-area-map-reveal::a-lit-current-district-publishes-a-coarse-overview"
    )
    def test_a_lit_current_district_publishes_a_bounded_overview(self):
        start = self._away()
        self._at_wild(start)
        # An unlit district (no landmark visit) publishes no overview at all.
        self._pin({start: 2})
        unlit = _render(self.char1)
        self.assertIsNone(unlit["district"])
        key, payload = self._lit_overview(start)
        overview = payload["district"]
        self.assertIsNotNone(overview)
        self.assertEqual(overview["key"], key)
        self.assertEqual(
            overview["name_zh"],
            _live("world.lore.map_districts", "current")().districts[key].district_name_zh,
        )
        self.assertIn(overview["cell_km"], area_map_module.DISTRICT_OVERVIEW_CELL_KM)
        cells = _decode_overview(payload)
        self.assertLessEqual(len(cells), area_map_module.DISTRICT_OVERVIEW_MAX_CELLS)
        self.assertGreaterEqual(sum(len(row) for row in overview["rows"]), 1)
        self.assertLessEqual(
            sum(len(row) for row in overview["rows"]),
            area_map_module.DISTRICT_OVERVIEW_MAX_RUNS,
        )
        self.assertLessEqual(
            json_byte_size(overview), area_map_module.DISTRICT_OVERVIEW_MAX_BYTES
        )
        # The fine 41-cell window is unchanged beside the coarse record.
        half = WILDERNESS_WINDOW // 2
        self.assertEqual(
            payload["window"],
            {"min_x": start[0] - half, "min_y": start[1] - half, "width": 41, "height": 41},
        )
        self.assertTrue(_js_accepts(payload))

    @covers_requirement(
        "wilderness-area-map-reveal::a-lit-current-district-publishes-a-coarse-overview",
        "wilderness-area-map-reveal::the-overview-reveals-only-the-lit-district-s-cells",
    )
    def test_the_overview_spans_exact_ownership_and_the_party(self):
        start = self._away()
        self._at_wild(start)
        key, payload = self._lit_overview(start)
        overview = payload["district"]
        cell_km = overview["cell_km"]
        window = overview["window"]
        bounds = _live("world.maps.district_partition", "district_bounds")(key)
        self.assertIsNotNone(bounds)
        min_km_x, min_km_y, max_km_x, max_km_y = bounds
        self.assertLessEqual(window["min_x"], min_km_x // cell_km)
        self.assertLessEqual(window["min_y"], min_km_y // cell_km)
        self.assertGreaterEqual(window["min_x"] + window["width"], -(-max_km_x // cell_km))
        self.assertGreaterEqual(window["min_y"] + window["height"], -(-max_km_y // cell_km))
        self.assertTrue(
            window["min_x"] <= start[0] // cell_km < window["min_x"] + window["width"]
        )
        self.assertTrue(
            window["min_y"] <= start[1] // cell_km < window["min_y"] + window["height"]
        )
        district_at = _live("world.maps.district_partition", "district_at")
        for (cx, cy), facts in _decode_overview(payload).items():
            sample = (cx * cell_km + cell_km // 2, cy * cell_km + cell_km // 2)
            owned = district_at(sample) == key
            self.assertEqual(facts is not None, owned, (cx, cy))
            if facts is not None:
                self.assertEqual(
                    set(facts), {"terrain", "band", "passable"}
                )
                self.assertNotEqual(facts["terrain"], "sea")

    @covers_requirement(
        "wilderness-area-map-reveal::a-lit-current-district-publishes-a-coarse-overview"
    )
    def test_an_unowned_current_cell_publishes_no_overview(self):
        start = self._away()
        self._at_wild(start)
        with mock.patch.object(area_map_module, "_district_key", return_value=None):
            payload = _render(self.char1)
        self.assertIsNone(payload["district"])
        self.assertTrue(payload["rows"])

    @covers_requirement(
        "wilderness-area-map-reveal::the-overview-reveals-only-the-lit-district-s-cells"
    )
    def test_an_adjacent_owner_and_a_hidden_anchor_never_leak(self):
        class _Partition:
            frame_cells = 2700

            def district_bounds(self, key):
                return (0, 0, 10, 5)

            def district_at(self, cell):
                return "t_owner" if cell[0] < 5 else "t_other"

        class _Oracle:
            def facts(self, cell):
                if cell == (2, 2):
                    # A hidden anchor's footprint keeps its underlying
                    # regional terrain and is not a disclosed settlement.
                    return {"terrain": "woodland", "band": 3, "passable": False}
                return {"terrain": "hills", "band": 4, "passable": True}

        overview = area_map_module._build_district_overview(
            _Partition(),
            "t_owner",
            "合成領地",
            _Oracle(),
            (2, 2),
            {"terrain": "open_ground", "band": 2, "passable": True},
            force_party=True,
        )
        cells = _decode_overview({"district": overview})
        for (cx, _cy), facts in cells.items():
            self.assertEqual(facts is not None, cx < 5, (cx, _cy))
        self.assertEqual(cells[(2, 2)], {"terrain": "woodland", "band": 3, "passable": False})
        for row in overview["rows"]:
            for run in row:
                self.assertLessEqual(
                    set(run),
                    {"length", "kind", "terrain", "band", "passable"},
                )

    @covers_requirement(
        "wilderness-area-map-reveal::the-overview-is-bounded-by-an-adaptive-kilometre-ladder"
    )
    def test_even_rung_sampling_uses_cell_km_over_two(self):
        class _Partition:
            frame_cells = 2700

            def district_bounds(self, key):
                return (0, 0, 60, 60)

            def district_at(self, cell):
                return "t_owner"

        class _Oracle:
            def facts(self, cell):
                return {"terrain": "hills", "band": (cell[0] + cell[1]) % 16, "passable": True}

        with mock.patch.object(area_map_module, "DISTRICT_OVERVIEW_MAX_CELLS", 1_000), mock.patch.object(
            area_map_module, "DISTRICT_OVERVIEW_MAX_BYTES", 10_000_000
        ):
            overview = area_map_module._build_district_overview(
                _Partition(),
                "t_owner",
                "合成領地",
                _Oracle(),
                (0, 0),
                None,
                force_party=False,
            )
        # 60 x 60 one-kilometre cells exceed the patched 1000-cell budget; the
        # 2 km rung (900 cells) is the finest that fits and samples at +1.
        self.assertEqual(overview["cell_km"], 2)
        cells = _decode_overview({"district": overview})
        for (cx, cy), facts in cells.items():
            sample = (cx * 2 + 1, cy * 2 + 1)
            self.assertEqual(facts["band"], (sample[0] + sample[1]) % 16)

    def test_the_party_cell_is_forced_without_mutating_the_cached_base(self):
        class _Partition:
            frame_cells = 2700

            def district_bounds(self, key):
                return (0, 0, 60, 60)

            def district_at(self, cell):
                x, y = cell
                # Every 2 km centre sample is owned except a 2 x 2 unknown
                # block around the party's coarse sample; the party cell
                # (4, 4) itself is owned.
                if cell == (4, 4):
                    return "t_owner"
                blocked = {(5, 5), (5, 7), (7, 5), (7, 7)}
                return "t_owner" if x % 2 == 1 and y % 2 == 1 and cell not in blocked else None

        class _Oracle:
            def facts(self, cell):
                return {"terrain": "open_ground", "band": 2, "passable": True}

        current = {"terrain": "hills", "band": 7, "passable": True}
        with mock.patch.object(area_map_module, "DISTRICT_OVERVIEW_MAX_CELLS", 1_000), mock.patch.object(
            area_map_module, "DISTRICT_OVERVIEW_MAX_BYTES", 10_000_000
        ):
            base = area_map_module._build_district_overview(
                _Partition(), "t_owner", "合成領地", _Oracle(), (4, 4), current, force_party=False
            )
            self.assertEqual(base["cell_km"], 2)
            # The party cell (4, 4) is owned but its coarse centre sample
            # (5, 5) is not: the base has a hole that the force fills.
            self.assertIsNone(_decode_overview({"district": base})[(2, 2)])
            patched = area_map_module._force_party_cell(base, _Partition(), "t_owner", (4, 4), current)
            self.assertEqual(_decode_overview({"district": patched})[(2, 2)], current)
            self.assertIsNone(_decode_overview({"district": base})[(2, 2)])
            forced = area_map_module._build_district_overview(
                _Partition(), "t_owner", "合成領地", _Oracle(), (4, 4), current, force_party=True
            )
            self.assertEqual(_decode_overview({"district": forced})[(2, 2)], current)

    @covers_requirement(
        "wilderness-area-map-reveal::the-overview-is-bounded-by-an-adaptive-kilometre-ladder"
    )
    def test_the_forced_party_cell_respects_the_run_cap(self):
        class _Partition:
            frame_cells = 2700

            def district_bounds(self, key):
                return (0, 0, 60, 60)

            def district_at(self, cell):
                x, y = cell
                if cell == (4, 4):
                    return "t_owner"
                blocked = {(5, 5), (5, 7), (7, 5), (7, 7)}
                return "t_owner" if x % 2 == 1 and y % 2 == 1 and cell not in blocked else None

        class _Oracle:
            def facts(self, cell):
                return {"terrain": "hills", "band": (cell[0] + cell[1]) % 16, "passable": True}

        current = {"terrain": "open_ground", "band": 3, "passable": True}
        # Measure the unforced run count, then make it the exact cap: forcing
        # the party cell splits its row and pushes the forced copy to a
        # coarser rung.
        with mock.patch.object(area_map_module, "DISTRICT_OVERVIEW_MAX_CELLS", 1_000), mock.patch.object(
            area_map_module, "DISTRICT_OVERVIEW_MAX_RUNS", 10_000
        ), mock.patch.object(area_map_module, "DISTRICT_OVERVIEW_MAX_BYTES", 10_000_000):
            probe = area_map_module._build_district_overview(
                _Partition(), "t_owner", "合成領地", _Oracle(), (4, 4), current, force_party=False
            )
        self.assertEqual(probe["cell_km"], 2)
        runs = sum(len(row) for row in probe["rows"])
        self.assertGreater(runs, 0)
        with mock.patch.object(area_map_module, "DISTRICT_OVERVIEW_MAX_CELLS", 1_000), mock.patch.object(
            area_map_module, "DISTRICT_OVERVIEW_MAX_RUNS", runs
        ), mock.patch.object(area_map_module, "DISTRICT_OVERVIEW_MAX_BYTES", 10_000_000):
            base = area_map_module._build_district_overview(
                _Partition(), "t_owner", "合成領地", _Oracle(), (4, 4), current, force_party=False
            )
            self.assertEqual(base["cell_km"], 2)
            self.assertEqual(sum(len(row) for row in base["rows"]), runs)
            forced = area_map_module._build_district_overview(
                _Partition(), "t_owner", "合成領地", _Oracle(), (4, 4), current, force_party=True
            )
        self.assertEqual(forced["cell_km"], 5)
        # The forced party cell is terrain at the coarser rung too.
        self.assertIsNotNone(_decode_overview({"district": forced})[(0, 0)])

    @covers_requirement(
        "wilderness-area-map-reveal::the-overview-is-bounded-by-an-adaptive-kilometre-ladder"
    )
    def test_every_shipped_district_fits_a_rung_with_terrain(self):
        from world.lore import map_districts

        partition = _live("world.maps.district_partition", "frozen_partition")()
        oracle = area_map_module._TerrainOracle()
        for key, declaration in map_districts.current().districts.items():
            with self.subTest(district=key):
                overview = area_map_module._build_district_overview(
                    partition,
                    key,
                    declaration.district_name_zh,
                    oracle,
                    (0, 0),
                    None,
                    force_party=False,
                )
                self.assertIsNotNone(overview)
                self.assertIn(overview["cell_km"], area_map_module.DISTRICT_OVERVIEW_CELL_KM)
                window = overview["window"]
                self.assertLessEqual(
                    window["width"] * window["height"],
                    area_map_module.DISTRICT_OVERVIEW_MAX_CELLS,
                )
                self.assertLessEqual(
                    sum(len(row) for row in overview["rows"]),
                    area_map_module.DISTRICT_OVERVIEW_MAX_RUNS,
                )
                self.assertLessEqual(
                    json_byte_size(overview),
                    area_map_module.DISTRICT_OVERVIEW_MAX_BYTES,
                )
                self.assertTrue(
                    any(
                        run["kind"] == "terrain"
                        for row in overview["rows"]
                        for run in row
                    ),
                    key,
                )

    def test_overview_cache_follows_partition_elevation_and_policy(self):
        start = self._away()
        key = _live("world.maps.district_partition", "district_at")(start)
        self.assertIsNotNone(key)
        cached = area_map_module._district_overview_base
        cached.cache_clear()
        arguments = (key, "binding", "partition-1", "elevation-1", 1)
        self.assertIsNotNone(cached(*arguments))
        self.assertIs(cached(*arguments), cached(*arguments))
        misses = cached.cache_info().misses
        for changed in (
            (key, "binding", "partition-2", "elevation-1", 1),
            (key, "binding", "partition-1", "elevation-2", 1),
            (key, "binding", "partition-1", "elevation-1", 2),
            (key, "binding-2", "partition-1", "elevation-1", 1),
        ):
            with self.subTest(arguments=changed):
                self.assertIsNotNone(cached(*changed))
                self.assertGreater(cached.cache_info().misses, misses)
                misses = cached.cache_info().misses
        cached.cache_clear()

    @covers_requirement(
        "webclient-map-panel-protocol::district-overview-records-have-an-exact-bounded-shape"
    )
    def test_an_over_bound_overview_is_null_and_the_window_still_publishes(self):
        start = self._away()
        self._at_wild(start)
        area_map_module._district_overview_base.cache_clear()
        with mock.patch.object(area_map_module, "DISTRICT_OVERVIEW_MAX_CELLS", 1), mock.patch.object(
            area_map_module, "log_warn"
        ) as log_warn:
            key, payload = self._lit_overview(start)
        self.assertIsNone(payload["district"])
        self.assertTrue(payload["rows"])
        self.assertTrue(_js_accepts(payload))
        events = [call.args[0] for call in log_warn.call_args_list]
        self.assertIn("area_map_district_overview_over_bound", events)
        area_map_module._district_overview_base.cache_clear()

    def test_reading_a_lit_district_overview_writes_nothing(self):
        start = self._away()
        self._at_wild(start)
        key, _payload = self._lit_overview(start)
        clock = get_world_clock()
        before = (self.char1.location, parse_knowledge(self.char1), clock.tick)
        for _ in range(2):
            payload = _render(self.char1)
            self.assertEqual(payload["district"]["key"], key)
        self.assertEqual((self.char1.location, parse_knowledge(self.char1), clock.tick), before)

    @covers_requirement(
        "webclient-area-map::wilderness-area-maps-cover-a-revealed-forty-one-cell-neighbourhood"
    )
    def test_only_legal_revealed_immediate_steps_are_actionable(self):
        start = self._away()
        self._at_wild(start)
        neighbor = _live("world.maps.wilderness_destination", "wilderness_neighbor")
        directions = _live("world.maps.wilderness_destination", "DIRECTION_DELTAS")
        legal = {_t_wild_id(*cell) for cell in (neighbor(*start, d) for d in directions) if cell is not None}
        self.assertTrue(legal)
        # Radius 1 reveals all eight neighbours: every legal step acts.
        self._pin({start: 1})
        payload = _render(self.char1)
        actionable = {node["id"] for node in payload["nodes"] if node["action"] is not None}
        self.assertEqual(actionable, legal)
        for node in payload["nodes"]:
            if node["action"] is not None:
                self.assertEqual(node["action"]["destination"], node["id"])
        self.assertEqual(
            _edge_set(payload), {frozenset((_t_wild_id(*start), node_id)) for node_id in legal}
        )
        # Radius 0 reveals only the current cell: no neighbour is a node and
        # unknown steps stay opaque directional controls elsewhere.
        self._pin({start: 0})
        payload = _render(self.char1)
        self.assertEqual([node["id"] for node in payload["nodes"]], [_t_wild_id(*start)])
        self.assertEqual(payload["edges"], [])
        self.assertTrue(_js_accepts(payload))

    @covers_requirement(
        "webclient-area-map::wilderness-area-maps-cover-a-revealed-forty-one-cell-neighbourhood"
    )
    @covers_requirement(
        "webclient-area-map::area-maps-reveal-visited-nodes-and-one-step-frontier-across-all-layers"
    )
    def test_gateway_step_replaces_its_cell_with_the_gate_room(self):
        self._at_wild(EAST_APPROACH)
        payload = _render(self.char1)
        grid = [node for node in payload["nodes"] if node["id"].startswith("grid:")]
        self.assertEqual([node["id"] for node in grid], [_t_grid_id(*EAST_GATE_XYZ[:2])])
        self.assertEqual(grid[0]["gateway"], {"leads_to": _t_anchor_display(_T_MAP_KEY)})
        self.assertEqual(grid[0]["action"]["destination"], grid[0]["id"])
        positions = [(node["x"], node["y"]) for node in payload["nodes"]]
        self.assertEqual(len(positions), len(set(positions)), "a replaced cell is never doubled")
        for node in payload["nodes"]:
            if node["id"].startswith("wild:"):
                self.assertIsNone(node["gateway"])
        self.assertTrue(_js_accepts(payload))
        # A woodland-night radius 0 leaves the gate cell unrevealed: no gate
        # room, label or far side is published; the step stays an opaque
        # directional control on the exploration rows.
        self._pin({EAST_APPROACH: 0})
        payload = _render(self.char1)
        self.assertEqual([node["id"] for node in payload["nodes"]], [payload["current_node"]])
        # (The current cell itself is revealed; its own approach name is its
        # location metadata, not the unrevealed gate's.)
        self.assertTrue(all(node["gateway"] is None for node in payload["nodes"]))
        self.assertEqual(payload["edges"], [])
        self.assertTrue(_js_accepts(payload))
