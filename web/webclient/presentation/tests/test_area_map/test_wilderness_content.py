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
from web.webclient.presentation.protocol import json_byte_size
from ..test_local_map._support import _live, _t_wild_id


from ._wilderness_fixture import _WildernessFixture

from ._support import _by_id, _decode_rows, _js_accepts, _knowledge, _render, _synthetic_visits

class WildernessContentTests(_WildernessFixture):
    """One wilderness reading rule per journey."""

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

    def _publish_network(self, cells, fingerprint="t_synthetic_road"):
        """Publish one synthetic road network over the live bundle."""
        from dataclasses import replace

        from elosern_map_core.roads_codec import RoadNetwork
        from world.maps import runtime

        previous = runtime.current()
        self.addCleanup(runtime.publish, previous)
        runtime.publish(
            replace(
                previous,
                roads=RoadNetwork(
                    fingerprint=fingerprint,
                    nodes=(),
                    roads=(),
                    cells=frozenset(tuple(cell) for cell in cells),
                ),
            )
        )

    @covers_requirement(
        "wilderness-roads::map-facts-publish-the-road-fact-within-disclosure"
    )
    def test_road_cells_publish_the_road_fact_within_disclosure(self):
        start = self._away()
        self._at_wild(start)
        self._pin({start: 2})
        neighbour = (start[0] + 1, start[1])
        self._publish_network({start, neighbour})

        payload = _render(self.char1)
        cells = _decode_rows(payload)

        self.assertTrue(cells[start]["road"])
        self.assertTrue(cells[neighbour]["road"])
        other = (start[0] + 2, start[1])
        self.assertIsNotNone(cells[other])
        self.assertFalse(cells[other]["road"])
        self.assertTrue(_js_accepts(payload))

    @covers_requirement(
        "wilderness-roads::map-facts-publish-the-road-fact-within-disclosure"
    )
    def test_an_unrevealed_road_cell_publishes_nothing(self):
        from world.maps import road_network

        start = self._away()
        self._at_wild(start)
        self._pin({start: 2})
        hidden_road = (start[0] + 15, start[1])
        self._publish_network({hidden_road})

        payload = _render(self.char1)
        cells = _decode_rows(payload)

        self.assertTrue(road_network.is_road_cell(hidden_road))
        self.assertIsNone(cells[hidden_road])
        for runs in payload["rows"]:
            for run in runs:
                if run["kind"] == "unknown":
                    self.assertEqual(set(run), {"length", "kind"})

    @covers_requirement(
        "wilderness-roads::map-facts-publish-the-road-fact-within-disclosure"
    )
    def test_a_republished_network_is_not_read_from_cache(self):
        start = self._away()
        self._at_wild(start)
        self._pin({start: 2})
        neighbour = (start[0] + 1, start[1])

        self._publish_network({start}, fingerprint="t_same_fingerprint")
        first = _decode_rows(_render(self.char1))
        self.assertTrue(first[start]["road"])
        self.assertFalse(first[neighbour]["road"])

        # A different network object over the same terrain, elevation and
        # footprints must invalidate the cached facts even with one fingerprint.
        self._publish_network({neighbour}, fingerprint="t_same_fingerprint")
        second = _decode_rows(_render(self.char1))
        self.assertFalse(second[start]["road"])
        self.assertTrue(second[neighbour]["road"])

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
