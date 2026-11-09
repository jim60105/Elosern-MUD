"""The area_map wilderness journeys (wilderness entry)."""

import json
from types import SimpleNamespace
from unittest import mock
from tools.spec_traceability import covers_requirement
from web.webclient.presentation import area_map as area_map_module
from web.webclient.presentation.map_quest_destinations import DestinationEvidence, DestinationFamily, QuestDestination
from web.webclient.presentation.registry import PanelUnavailableError
from world.rules.clock import get_world_clock
from world.rules.map_knowledge import encode_grid, parse_knowledge
from ..test_local_map._support import EAST_APPROACH, EAST_GATE_XYZ, _T_MAP_KEY, _live, _t_anchor_display, _t_grid_id, _t_wild_id


from ._wilderness_fixture import _WildernessFixture

from ._support import _by_id, _decode_rows, _edge_set, _js_accepts, _render

class WildernessEntryTests(_WildernessFixture):
    """One wilderness reading rule per journey."""

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

    def test_repeated_renders_reuse_one_gateway_table(self):
        from web.webclient.presentation.local_map import gateways
        from world.maps.published import SourceMemo

        self._at_wild(EAST_APPROACH)
        with mock.patch.object(gateways, "_GATEWAY_TABLE", SourceMemo()), mock.patch.object(
            gateways, "_build_gateway_table", wraps=gateways._build_gateway_table
        ) as builds:
            payloads = [_render(self.char1) for _ in range(3)]
        self.assertEqual(builds.call_count, 1)
        self.assertEqual(payloads[0], payloads[1])
        self.assertEqual(payloads[1], payloads[2])

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

    @covers_requirement(
        "wilderness-area-map-reveal::wilderness-runs-disclose-only-revealed-terrain"
    )
    def test_visited_cell_has_its_own_node_and_reveal_only_cell_has_none(self):
        start = self._away()
        self._at_wild(start)
        self._pin({start: 4})
        cells = _decode_rows(_render(self.char1))
        # Two cells of identical revealed terrain: one becomes a visit.
        facts = {}
        pair = None
        for cell, value in sorted(cells.items()):
            if value is None or cell == start or max(abs(cell[0] - start[0]), abs(cell[1] - start[1])) < 2:
                continue
            key = json.dumps(value, sort_keys=True)
            if key in facts:
                pair = (facts[key], cell)
                break
            facts[key] = cell
        self.assertIsNotNone(pair, "the synthetic disc holds two identical cells")
        visited, reveal_only = pair
        self._pin({start: 4, visited: 0})
        payload = _render(self.char1)
        cells = _decode_rows(payload)
        self.assertEqual(cells[visited], cells[reveal_only])
        nodes = _by_id(payload)
        node = nodes[_t_wild_id(*visited)]
        self.assertEqual((node["visited"], node["visibility"]), (True, "visited"))
        self.assertNotIn(_t_wild_id(*reveal_only), nodes)
        for runs in payload["rows"]:
            for run in runs:
                self.assertNotIn("visited", run)
        self.assertTrue(_js_accepts(payload))

    @covers_requirement(
        "wilderness-area-map-reveal::wilderness-runs-disclose-only-revealed-terrain"
    )
    def test_anti_peek_across_every_payload_branch(self):
        start = self._away()
        self._at_wild(start)
        remembered = (start[0] + 9, start[1])
        self._pin({start: 2, remembered: 3})
        seen_cells = []
        real_view = _live("world.maps.wilderness_population", "population_view")

        def spy(wilderness, cells):
            cells = list(cells)
            seen_cells.extend(cells)
            return real_view(wilderness, cells)

        with mock.patch("world.maps.wilderness_population.population_view", spy):
            payload = _render(self.char1)
        cells = _decode_rows(payload)
        in_disc = _live("world.rules.sight", "in_ground_disc")
        radius = payload["ground_radius"]
        # Unknown runs carry exactly two keys and no metadata.
        for runs in payload["rows"]:
            for run in runs:
                expected = {"length", "kind"} if run["kind"] == "unknown" else {
                    "length", "kind", "terrain", "passable", "band", "tier", "road", "ford", "display"
                }
                self.assertEqual(set(run), expected)
        # Entities are only read and published inside live sight on revealed
        # cells; the remembered disc far away carries none.
        for cell in seen_cells:
            self.assertTrue(in_disc(start, cell, radius))
            self.assertIsNotNone(cells[cell])
        for entity in payload["entities"]:
            cell = (entity["cell"]["x"], entity["cell"]["y"])
            self.assertTrue(in_disc(start, cell, radius))
            self.assertNotIn(":", entity["id"])
            self.assertFalse(in_disc(remembered, cell, 3) and not in_disc(start, cell, radius))
        self.assertIsNotNone(cells[remembered])
        # Sightings carry the four approximate fields only.
        for sighting in payload["sightings"]:
            self.assertEqual(set(sighting), {"bearing", "distance_km", "silhouette_zh", "name"})
        # A quest destination on an unrevealed cell adds no node or cell
        # detail: it is a bearing marker only.
        unknown = next(cell for cell, facts in sorted(cells.items()) if facts is None and cell[0] >= 0 and cell[1] >= 0)
        destination = QuestDestination(
            quest_id="q_far", definition_key="t_def", family=list(DestinationFamily)[0],
            world_cell=unknown, map_key=None, node_id=_t_wild_id(*unknown),
            destination_kind=DestinationEvidence.LOCATION,
        )
        definition = SimpleNamespace(display_name="合成委託")
        with mock.patch(
            "web.webclient.presentation.map_quest_destinations.accepted_destinations_with_tracking",
            return_value=([destination], set()),
        ), mock.patch.dict("world.quests.definitions.QUEST_DEFINITION_REGISTRY", {"t_def": definition}):
            quest_payload = _render(self.char1)
        self.assertEqual(quest_payload["rows"], payload["rows"])
        self.assertEqual(quest_payload["nodes"], payload["nodes"])
        self.assertEqual(quest_payload["quest_markers"][0]["destination"]["kind"], "bearing")
        self.assertTrue(_js_accepts(payload))

    @covers_requirement(
        "wilderness-map-disclosure::all-wilderness-map-publishers-enforce-reveal-boundaries"
    )
    @covers_requirement(
        "wilderness-area-map-reveal::wilderness-runs-disclose-only-revealed-terrain"
    )
    def test_hidden_entry_identity_requires_an_actual_visit(self):
        from world.maps.static_references import settlement_node_xyz

        entries = _live("world.lore.wilderness_entry", "WILDERNESS_ENTRY_REGISTRY").values()
        hidden = _live("world.rules.wilderness_disclosure", "anchor_is_hidden")
        point = next(entry for entry in entries if entry.is_point_shape and hidden(entry.anchor_key))
        hidden_name = _t_anchor_display(point.anchor_key)
        self._at_wild(point.anchor_cell)
        # Maximal reveal around the entry: terrain only, never its identity.
        self._pin({point.anchor_cell: 8})
        payload = _render(self.char1)
        self.assertFalse([node for node in payload["nodes"] if node["id"].startswith("grid:")])
        self.assertNotIn(hidden_name, json.dumps(payload, ensure_ascii=False))
        self.assertTrue(_js_accepts(payload))
        gate_xyz = settlement_node_xyz(point.gates[0].destination)
        gate_node = encode_grid(gate_xyz[2], gate_xyz[0], gate_xyz[1])
        self._pin({point.anchor_cell: 8}, visited_grid=(gate_node,))
        payload = _render(self.char1)
        node = _by_id(payload)[gate_node]
        self.assertEqual(node["gateway"], {"leads_to": hidden_name})
        self.assertEqual(node["action"]["destination"], gate_node)
        self.assertTrue(_js_accepts(payload))

    @covers_requirement(
        "wilderness-area-map-reveal::existing-maps-consume-bounded-atomic-reveal-payloads"
    )
    def test_oversized_collections_become_unavailable_without_truncation(self):
        start = self._away()
        self._at_wild(start)
        self._pin({start: 8})
        fact = SimpleNamespace(
            observation_key="population:t", cell=start, kind="monster", hostile=True, label="狼",
            threat_tier=None, danger_grade=None,
        )
        facts = [SimpleNamespace(**{**vars(fact), "observation_key": f"population:t:{i}"}) for i in range(4097)]
        with mock.patch("world.maps.wilderness_population.population_view", return_value=facts), \
                mock.patch.object(area_map_module, "log_warn") as warn:
            with self.assertRaises(PanelUnavailableError):
                _render(self.char1)
        self.assertEqual(warn.call_args[0][0], "area_map_over_bound")
        self.assertEqual(warn.call_args[1]["context"]["entities"], 4097)
        markers = [{"bearing": "北", "distance_km": 5, "silhouette_zh": "塔", "name": None}] * 257
        with mock.patch.object(area_map_module, "_distant_markers", return_value=markers), \
                mock.patch.object(area_map_module, "log_warn") as warn:
            with self.assertRaises(PanelUnavailableError):
                _render(self.char1)
        self.assertEqual(warn.call_args[1]["context"]["sightings"], 257)
