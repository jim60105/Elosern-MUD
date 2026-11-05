"""The area_map wilderness journeys (wilderness content)."""

import json
import os
import statistics
import time
from types import SimpleNamespace
import unittest
from unittest import mock
from tools.spec_traceability import covers_requirement
from web.webclient.presentation import area_map as area_map_module
from web.webclient.presentation.map_panels import AREA_MAX_BYTES, WILDERNESS_WINDOW
from web.webclient.presentation.map_parts import decode_map_parts, encode_map_parts
from web.webclient.presentation.map_quest_destinations import DestinationEvidence, DestinationFamily, QuestDestination
from web.webclient.presentation.protocol import json_byte_size
from web.webclient.presentation.registry import PanelUnavailableError
from world.rules.map_knowledge import encode_grid
from ..test_local_map._support import _live, _t_anchor_display, _t_wild_id
from ._support import _render, _by_id, _js_accepts, _decode_rows, _knowledge, _synthetic_visits


from ._wilderness_fixture import _WildernessFixture

class WildernessContentTests(_WildernessFixture):
    """One wilderness reading rule per journey."""

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

    def test_every_wire_terrain_class_has_a_server_label(self):
        from web.webclient.presentation.map_panels import AREA_TERRAIN_CLASSES

        self.assertEqual(set(area_map_module.WILDERNESS_TERRAIN_LABELS), set(AREA_TERRAIN_CLASSES))
        self.assertTrue(all(label.strip() for label in area_map_module.WILDERNESS_TERRAIN_LABELS.values()))

    @covers_requirement("webclient-travel-window::travel-consumes-the-shared-current-wilderness-window")
    def test_display_annotations_ride_only_revealed_runs_and_disclosed_districts(self):
        start = self._away()
        self._at_wild(start)
        self._pin({start: 6})
        district_at = _live("world.maps.district_partition", "district_at")
        here = district_at(start)
        with mock.patch.object(area_map_module, "_lit_landmarks", return_value={}):
            payload = _render(self.char1)
        cells = _decode_rows(payload)
        labels = area_map_module.WILDERNESS_TERRAIN_LABELS
        seen_keys = set()
        for runs in payload["rows"]:
            for run in runs:
                if run["kind"] == "unknown":
                    self.assertEqual(set(run), {"length", "kind"})
                    continue
                display = run["display"]
                self.assertEqual(display["terrain_label"], labels[run["terrain"]])
                self.assertEqual(display["settlement"], run["terrain"] == "settlement")
                self.assertEqual(display["ford_label"] is not None, run["ford"])
                self.assertEqual(display["district_key"] is None, display["district_name"] is None)
                seen_keys.add(display["district_key"])
        # With nothing lit only the current cell's own district is disclosed.
        self.assertLessEqual(seen_keys - {None}, {here})
        for cell, facts in cells.items():
            if facts is not None and district_at(cell) != here:
                self.assertIsNone(facts["display"]["district_key"], cell)
        self.assertEqual(cells[start]["display"]["district_key"], here)
        # Lighting another district (by its exact landmark) discloses it too.
        others = {district_at(cell) for cell, facts in cells.items() if facts is not None} - {here, None}
        if others:
            other = sorted(others)[0]
            with mock.patch.object(area_map_module, "_lit_landmarks", return_value={other: "grid:t_none:0:0"}):
                lit_cells = _decode_rows(_render(self.char1))
            disclosed = {facts["display"]["district_key"] for facts in lit_cells.values() if facts is not None}
            self.assertIn(other, disclosed)
        self.assertTrue(_js_accepts(payload))

    @covers_requirement("webclient-travel-window::travel-consumes-the-shared-current-wilderness-window")
    def test_only_a_lit_landmark_names_its_own_wild_node(self):
        start = self._away()
        self._at_wild(start)
        self._pin({start: 2})
        current = _t_wild_id(*start)
        rows = dict(area_map_module._district_rows())
        rows["t_lit"] = SimpleNamespace(district_name_zh="合成區", landmark_name_zh="合成石標")
        with mock.patch.object(area_map_module, "_district_rows", return_value=rows), \
                mock.patch.object(area_map_module, "_lit_landmarks", return_value={"t_lit": current}):
            payload = _render(self.char1)
        nodes = _by_id(payload)
        self.assertEqual(nodes[current]["landmark"], {"name": "合成石標"})
        self.assertTrue(all(node["landmark"] is None for node in payload["nodes"] if node["id"] != current))
        with mock.patch.object(area_map_module, "_lit_landmarks", return_value={}):
            plain = _render(self.char1)
        self.assertTrue(all(node["landmark"] is None for node in plain["nodes"]))
        self.assertTrue(_js_accepts(payload))

    def test_entities_carry_one_count_and_their_canonical_threat(self):
        from world.maps.wilderness_population import PopulationFact, threat_label

        start = self._away()
        self._at_wild(start)
        self._pin({start: 4})
        tier = sorted(_live("world.lore.monsters", "MONSTER_TIER_REGISTRY"))[0]
        facts = (
            PopulationFact("population:a", start, "monster", True, "合成狼", threat_tier=tier, danger_grade="D"),
            PopulationFact("population:b", start, "monster", True, "合成狼", threat_tier=None),
            PopulationFact("object:9", start, "npc", False, "合成旅人", threat_tier=tier),
        )
        with mock.patch("world.maps.wilderness_population.population_view", return_value=facts):
            payload = _render(self.char1)
        self.assertEqual(
            [(e["label"], e["count"], e["threat"]) for e in payload["entities"]],
            [("合成狼", 1, threat_label(tier, "D")), ("合成狼", 1, None), ("合成旅人", 1, None)],
        )
        self.assertIsNotNone(threat_label(tier, "D"))
        self.assertNotEqual(threat_label(tier, "D"), threat_label(tier, None))
        self.assertIsNone(threat_label("t_unknown_tier", "D"))
        self.assertTrue(_js_accepts(payload))

    def test_entity_annotations_are_actual_living_individuals_only(self):
        from world.maps.wilderness_population import threat_label
        from world.rules.monster_individual import construct_species_individual

        start = self._away()
        self._at_wild(start)
        self._pin({start: 6})
        variants = _live("world.lore.monster_species", "MONSTER_VARIANT_REGISTRY")
        key, variant = next(
            (key, row)
            for key, row in sorted(variants.items())
            if row.danger_grade is not None
        )

        # A configured, revealed cell without a registered individual carries
        # no entity annotation; no commission marker is fabricated into one.
        target = (start[0] + 1, start[1])
        before = _render(self.char1)
        self.assertNotIn(
            {"x": target[0], "y": target[1]},
            [entity["cell"] for entity in before["entities"]],
        )
        self.assertEqual(before["quest_markers"], [])

        monster = construct_species_individual(variant.species_key, key)
        wilderness = self.char1.location.wilderness
        wilderness.db.itemcoordinates[monster] = target
        token = area_map_module.entity_token(f"object:{monster.pk}")
        payload = _render(self.char1)
        self.assertEqual(
            [
                (entity["cell"], entity["label"], entity["count"], entity["threat"])
                for entity in payload["entities"]
                if entity["id"] == token
            ],
            [
                (
                    {"x": target[0], "y": target[1]},
                    monster.key,
                    1,
                    threat_label(variant.threat_tier, variant.danger_grade),
                )
            ],
        )
        self.assertEqual(payload["quest_markers"], [])

        # The annotation follows the actual registration, not the old cell.
        moved_target = (start[0], start[1] + 1)
        wilderness.db.itemcoordinates[monster] = moved_target
        moved = _render(self.char1)
        self.assertEqual(
            [
                entity["cell"]
                for entity in moved["entities"]
                if entity["id"] == token
            ],
            [{"x": moved_target[0], "y": moved_target[1]}],
        )

    def test_dense_real_windows_stay_inside_the_byte_ceiling(self):
        """Measured, not pinned: fully revealed windows at spread positions
        publish (or degrade to unavailable) within the unchanged cap."""
        start = self._away()
        sizes = []
        for dx, dy in ((0, 0), (40, 0), (0, 40), (-40, -20)):
            cell = (start[0] + dx, start[1] + dy)
            try:
                self._at_wild(cell)
            except AssertionError:
                continue
            self._pin({cell: 8, (cell[0] + 12, cell[1]): 8, (cell[0] - 12, cell[1]): 8,
                       (cell[0], cell[1] + 12): 8, (cell[0], cell[1] - 12): 8})
            payload = _render(self.char1)
            sizes.append(json_byte_size(payload))
        print(f"area_map schema-3 dense window bytes: {sizes}")
        self.assertTrue(sizes)
        self.assertLessEqual(max(sizes), AREA_MAX_BYTES)

    @covers_requirement(
        "webclient-area-map::map-view-requests-publish-the-requested-area-without-changing-gameplay"
    )
    @covers_requirement(
        "wilderness-area-map-reveal::existing-maps-consume-bounded-atomic-reveal-payloads"
    )
    def test_the_window_reads_only_its_own_chunks_and_writes_nothing(self):
        from world.rules import map_knowledge
        from world.rules.map_knowledge import CHUNK_CELLS, KNOWLEDGE_ATTR

        start = self._away()
        self._at_wild(start)
        visits = _synthetic_visits(start, 20_000)
        self._pin(visits)
        from evennia.utils.dbserialize import deserialize

        def stored():
            return json.dumps(deserialize(self.char1.attributes.get(KNOWLEDGE_ATTR)), sort_keys=True)

        before = stored()
        decoded = []
        real = map_knowledge._decode_chunk_entries

        def spy(chunk_key, chunk_data):
            decoded.append(chunk_key)
            return real(chunk_key, chunk_data)

        with mock.patch.object(map_knowledge, "_decode_chunk_entries", spy):
            payload = _render(self.char1)
        reach = WILDERNESS_WINDOW // 2 + map_knowledge.MAX_SIGHT
        allowed = {
            f"{x // CHUNK_CELLS}:{y // CHUNK_CELLS}"
            for x in range(start[0] - reach, start[0] + reach + 1)
            for y in range(start[1] - reach, start[1] + reach + 1)
        }
        # Exact landmark membership (lit districts) reads one selected chunk
        # per district landmark, never the whole record.
        landmarks = _live("world.lore.map_districts", "landmark_node_ids")()
        for node_id in landmarks.values():
            if node_id.startswith("wild:"):
                _, _, x, y = node_id.split(":")
                allowed.add(f"{int(x) // CHUNK_CELLS}:{int(y) // CHUNK_CELLS}")
        stored_chunks = set(_knowledge(visits)["wilderness"][_live("world.maps.wilderness_provider", "WILDERNESS_NAME")])
        self.assertGreater(len(stored_chunks - allowed), 0, "the record holds chunks far from the window")
        self.assertTrue(decoded)
        self.assertLessEqual(set(decoded), allowed)
        self.assertEqual(before, stored())
        # The bounded body travels whole through the shared part codec.
        parts = encode_map_parts("area_map", payload)
        self.assertEqual(decode_map_parts("area_map", parts), payload)

    @unittest.skipUnless(os.environ.get("MUD_AREA_MAP_BENCHMARK") == "1", "timing benchmark: set MUD_AREA_MAP_BENCHMARK=1")
    def test_warmed_window_with_twenty_thousand_visits_is_within_fifty_ms(self):
        start = self._away()
        self._at_wild(start)
        self._pin(_synthetic_visits(start, 20_000))
        _render(self.char1)  # warm caches; setup excluded from the samples
        samples = []
        for _ in range(20):
            began = time.perf_counter()
            _render(self.char1)
            samples.append((time.perf_counter() - began) * 1000)
        median = statistics.median(samples)
        print(f"area_map wilderness benchmark: median {median:.1f} ms over 20 samples")
        self.assertLessEqual(median, 50.0)
