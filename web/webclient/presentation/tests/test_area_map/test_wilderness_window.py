"""The area_map wilderness journeys (wilderness window)."""

from unittest import mock
from tools.spec_traceability import covers_requirement
from web.webclient.presentation import area_map as area_map_module
from web.webclient.presentation.map_panels import WILDERNESS_WINDOW
from web.webclient.presentation.protocol import json_byte_size
from ..test_local_map._support import _live, _t_region_display_for, _t_wild_id


from ._wilderness_fixture import _WildernessFixture

from ._support import _by_id, _decode_overview, _decode_rows, _js_accepts, _render

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
