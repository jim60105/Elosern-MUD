"""Pure tests for the map-knowledge node-ID grammar and record parser."""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch
import unittest

from world.maps import wilderness_provider
from world.rules.map_knowledge import (
    KnowledgeError,
    NodeIDError,
    NodeVisit,
    decode_node,
    encode_grid,
    encode_room,
    encode_wild,
    parse_knowledge,
    has_visited,
    visits_in_bounds,
    validate_node,
)

from ._knowledge_probes import live_map_key

# Grid node IDs must name a map the xyzgrid extent scan actually knows, and
# wilderness IDs must name the registered wilderness — both resolve inside
# every test (never at module import) so a game-data rework (renamed map or
# wilderness) cannot break this grammar suite — or even its import — while
# every assertion still exercises the registered-component rule.


class _RegisteredVocabularyTests(unittest.TestCase):
    """Resolves the registered map/wilderness vocabulary per test run."""

    def setUp(self):
        self.map = live_map_key()
        self.wild = getattr(wilderness_provider, "WILDERNESS_NAME")


class NodeIDGrammarTests(_RegisteredVocabularyTests):
    @covers_requirement("map-knowledge::node-ids-use-strict-per-layer-grammar-with-registered-bounded-components")
    def test_grid_round_trip_within_registered_bounds(self):
        with patch(
            "world.rules.map_knowledge._registered_grid_bounds",
            return_value=(4, 4),
        ):
            node_id = encode_grid(self.map, 2, 0)
            self.assertEqual(node_id, f"grid:{self.map}:2:0")
            decoded = decode_node(node_id)
            self.assertEqual(
                decoded,
                {"prefix": "grid", "z_map_key": self.map, "x": 2, "y": 0},
            )
            self.assertTrue(validate_node(node_id))

    def test_wild_round_trip(self):
        node_id = encode_wild(self.wild, 10, 15)
        self.assertEqual(node_id, f"wild:{self.wild}:10:15")
        decoded = decode_node(node_id)
        self.assertEqual(
            decoded, {"prefix": "wild", "name": self.wild, "x": 10, "y": 15}
        )

    def test_room_round_trip(self):
        node_id = encode_room(42)
        self.assertEqual(node_id, "room:42")
        decoded = decode_node(node_id)
        self.assertEqual(decoded, {"prefix": "room", "dbref": 42})

    @covers_requirement("map-knowledge::node-ids-use-strict-per-layer-grammar-with-registered-bounded-components")
    def test_malformed_and_out_of_bounds_ids_are_rejected(self):
        invalid = [
            f"grid:{self.map}:2",  # missing component
            f"grid:{self.map}:2:0:1",  # extra component
            f"grid:{self.map}:two:0",  # non-integer coordinate
            f"grid:{self.map}:2:0.5",
            "grid:other:2:0",  # unregistered z-map-key
            f"grid:{self.map}:-1:0",  # negative coordinate
            "wild:other:1:2",  # unregistered wilderness name
            f"wild:{self.wild}:2700:0",  # x beyond WILDERNESS_MAX_X
            f"wild:{self.wild}:0:2700",  # y beyond WILDERNESS_MAX_Y
            f"wild:{self.wild}:1:2:3",  # extra component
            "room:0",  # zero dbref
            "room:-5",
            "room:abc",
            "room:true",
            "map:1:2",  # unknown prefix
            "grid",  # no components
            "",
            f"grid:{self.map}:2:0:0:0",
        ]
        for node_id in invalid:
            with self.subTest(node_id=node_id):
                with self.assertRaises(NodeIDError):
                    decode_node(node_id)
                self.assertFalse(validate_node(node_id))

    def test_coordinate_outside_registered_grid_bounds_is_rejected(self):
        with patch(
            "world.rules.map_knowledge._registered_grid_bounds",
            return_value=(4, 4),
        ):
            self.assertFalse(validate_node(f"grid:{self.map}:5:0"))
            self.assertFalse(validate_node(f"grid:{self.map}:0:5"))
            with self.assertRaises(NodeIDError):
                decode_node(f"grid:{self.map}:5:0")

    def test_room_dbref_must_be_positive_int(self):
        for bad in (0, -1, 1.5, "5", True):
            with self.subTest(bad=bad):
                with self.assertRaises(NodeIDError):
                    encode_room(bad)

    def test_grid_encode_rejects_non_registered_shapes(self):
        with self.assertRaises(NodeIDError):
            encode_grid("a:b", 1, 2)
        with self.assertRaises(NodeIDError):
            encode_grid("x" * 65, 1, 2)
        with self.assertRaises(NodeIDError):
            encode_grid(self.map, -1, 2)
        with self.assertRaises(NodeIDError):
            encode_grid(self.map, 1, True)

    def test_overlong_node_id_rejected(self):
        with patch(
            "world.rules.map_knowledge._registered_grid_bounds",
            return_value=(4, 4),
        ):
            with self.assertRaises(NodeIDError):
                decode_node(f"grid:{self.map}:" + "9" * 130 + ":0")


class KnowledgeParseTests(_RegisteredVocabularyTests):
    def _character(self, record):
        return _FakeCharacter(record)

    def test_valid_record_parses_in_deterministic_order(self):
        # x=1, y=1 -> chunk 0:0, offset = (1%64)*64 + 1%64 = 65
        record = {
            "schema_version": 2,
            "visited": {
                "room:99": {"first_seen_tick": 40, "last_seen_tick": 80},
                f"grid:{self.map}:2:0": {
                    "first_seen_tick": 10,
                    "last_seen_tick": 10,
                },
            },
            "wilderness": {
                self.wild: {
                    "0:0": {
                        "65": {"first_seen_tick": 20, "last_seen_tick": 60, "sight": 3}
                    }
                }
            },
        }
        with patch(
            "world.rules.map_knowledge._registered_grid_bounds",
            return_value=(4, 4),
        ):
            visits = parse_knowledge(self._character(record))
        self.assertEqual(
            visits,
            [
                NodeVisit(f"grid:{self.map}:2:0", 10, 10),
                NodeVisit("room:99", 40, 80),
                NodeVisit(f"wild:{self.wild}:1:1", 20, 60, sight=3),
            ],
        )

    @covers_requirement(
        "map-knowledge::parse-knowledge-isolates-corrupt-records-without-resetting-them",
        "wilderness-knowledge-chunks::wilderness-observations-are-chunk-addressed",
    )
    def test_corrupt_records_raise_and_are_not_reset(self):
        corrupt = [
            None,
            # Schema 1 rejection
            {"schema_version": 1},
            {"schema_version": 1, "visited": []},
            {"schema_version": 1, "visited": {}, "wilderness": {}},
            {"schema_version": 1, "visited": {}},
            # Schema 2 missing wilderness
            {"schema_version": 2, "visited": {}},
            # Schema 2 extra key
            {"schema_version": 2, "visited": {}, "wilderness": {}, "extra": True},
            # wild: prefix in visited mapping is rejected
            {
                "schema_version": 2,
                "visited": {f"wild:{self.wild}:1:1": {"first_seen_tick": 1, "last_seen_tick": 1}},
                "wilderness": {},
            },
            # Non-integer tick in visited
            {
                "schema_version": 2,
                "visited": {f"grid:{self.map}:2:0": {"first_seen_tick": "x", "last_seen_tick": 1}},
                "wilderness": {},
            },
            # Boolean tick in visited
            {
                "schema_version": 2,
                "visited": {f"grid:{self.map}:2:0": {"first_seen_tick": True, "last_seen_tick": 1}},
                "wilderness": {},
            },
            # first_seen > last_seen
            {
                "schema_version": 2,
                "visited": {"room:5": {"first_seen_tick": 10, "last_seen_tick": 5}},
                "wilderness": {},
            },
            # unknown wilderness name
            {"schema_version": 2, "visited": {}, "wilderness": {"unknown": {}}},
            # empty chunk
            {"schema_version": 2, "visited": {}, "wilderness": {self.wild: {"0:0": {}}}},
            # invalid chunk key format
            {
                "schema_version": 2,
                "visited": {},
                "wilderness": {self.wild: {"0:0:0": {"0": {"first_seen_tick": 1, "last_seen_tick": 1, "sight": 0}}}},
            },
            # non-canonical decimal in chunk key (e.g. 00:1)
            {
                "schema_version": 2,
                "visited": {},
                "wilderness": {self.wild: {"00:1": {"0": {"first_seen_tick": 1, "last_seen_tick": 1, "sight": 0}}}},
            },
            # invalid sight (> 8)
            {
                "schema_version": 2,
                "visited": {},
                "wilderness": {self.wild: {"0:0": {"0": {"first_seen_tick": 1, "last_seen_tick": 1, "sight": 9}}}},
            },
            # boolean sight
            {
                "schema_version": 2,
                "visited": {},
                "wilderness": {self.wild: {"0:0": {"0": {"first_seen_tick": 1, "last_seen_tick": 1, "sight": True}}}},
            },
            # offset out of bounds
            {
                "schema_version": 2,
                "visited": {},
                "wilderness": {self.wild: {"0:0": {"4096": {"first_seen_tick": 1, "last_seen_tick": 1, "sight": 0}}}},
            },
            # excessively long non-canonical integer key (> 10 digits)
            {
                "schema_version": 2,
                "visited": {},
                "wilderness": {self.wild: {"1" * 5000 + ":0": {"0": {"first_seen_tick": 1, "last_seen_tick": 1, "sight": 0}}}},
            },
        ]
        for record in corrupt:
            with self.subTest(record=record):
                character = self._character(record)
                with self.assertRaises(KnowledgeError):
                    parse_knowledge(character)
                self.assertEqual(character.attributes.get("map_knowledge"), record)

    @covers_requirement(
        "map-knowledge::map-knowledge-py-is-the-sole-writer-of-a-versioned-visited-node-record",
        "wilderness-knowledge-chunks::wilderness-observations-are-chunk-addressed",
    )
    def test_has_visited_and_visits_in_bounds(self):
        # Build record with 2 distant chunks: chunk 0:0 and chunk 10:10
        # In chunk 0:0, cell (1, 2) -> offset = 2 * 64 + 1 = 129
        # In chunk 10:10, cell (641, 642) -> cx=10, cy=10, local_x=1, local_y=2, offset=129
        record = {
            "schema_version": 2,
            "visited": {
                "room:10": {"first_seen_tick": 5, "last_seen_tick": 5},
            },
            "wilderness": {
                self.wild: {
                    "0:0": {
                        "129": {"first_seen_tick": 10, "last_seen_tick": 15, "sight": 2}
                    },
                    "10:10": {
                        "129": {"first_seen_tick": 30, "last_seen_tick": 40, "sight": 5}
                    },
                }
            },
        }
        char = self._character(record)
        self.assertTrue(has_visited(char, "room:10"))
        self.assertFalse(has_visited(char, "room:20"))
        self.assertTrue(has_visited(char, f"wild:{self.wild}:1:2"))
        self.assertFalse(has_visited(char, f"wild:{self.wild}:1:3"))
        self.assertTrue(has_visited(char, f"wild:{self.wild}:641:642"))

        # Bounded query around chunk 0:0 (bounds 0, 0, 10, 10)
        visits = visits_in_bounds(char, (0, 0, 10, 10))
        self.assertEqual(len(visits), 1)
        self.assertEqual(visits[0].node_id, f"wild:{self.wild}:1:2")
        self.assertEqual(visits[0].sight, 2)

        # Bounded query around chunk 10:10
        visits_far = visits_in_bounds(char, (640, 640, 650, 650))
        self.assertEqual(len(visits_far), 1)
        self.assertEqual(visits_far[0].node_id, f"wild:{self.wild}:641:642")
        self.assertEqual(visits_far[0].sight, 5)

        # Bounded query with padding: bounds=(633, 634, 633, 634) with padding=8 covers (641, 642)
        visits_padded = visits_in_bounds(char, (633, 634, 633, 634), padding=8)
        self.assertEqual(len(visits_padded), 1)
        self.assertEqual(visits_padded[0].node_id, f"wild:{self.wild}:641:642")

        # Multi-chunk query covering both chunk 0:0 and chunk 1:1
        # Add cell (65, 65) -> cx=1, cy=1, offset=(1*64)+1 = 65
        record_multi = {
            "schema_version": 2,
            "visited": {},
            "wilderness": {
                self.wild: {
                    "0:0": {"65": {"first_seen_tick": 1, "last_seen_tick": 1, "sight": 0}},
                    "1:1": {"65": {"first_seen_tick": 2, "last_seen_tick": 2, "sight": 1}},
                }
            },
        }
        char_multi = self._character(record_multi)
        multi_visits = visits_in_bounds(char_multi, (0, 0, 70, 70))
        self.assertEqual(len(multi_visits), 2)
        self.assertEqual(multi_visits[0].node_id, f"wild:{self.wild}:1:1")
        self.assertEqual(multi_visits[1].node_id, f"wild:{self.wild}:65:65")

        # Non-intersecting query returns empty
        self.assertEqual(visits_in_bounds(char, (200, 200, 210, 210)), [])

    @covers_requirement(
        "map-knowledge::map-knowledge-py-is-the-sole-writer-of-a-versioned-visited-node-record",
        "wilderness-knowledge-chunks::wilderness-observations-are-chunk-addressed",
    )
    def test_bounded_query_ignores_distant_corrupt_chunk_entries(self):
        # Distant chunk 10:10 has a corrupt entry (sight=99), but chunk 0:0 is valid.
        # visits_in_bounds for chunk 0:0 must succeed without inspecting chunk 10:10's entries.
        # parse_knowledge must fail because it decodes all chunks.
        record = {
            "schema_version": 2,
            "visited": {},
            "wilderness": {
                self.wild: {
                    "0:0": {
                        "65": {"first_seen_tick": 1, "last_seen_tick": 1, "sight": 1}
                    },
                    "10:10": {
                        "129": {"first_seen_tick": 1, "last_seen_tick": 1, "sight": 99}
                    },
                }
            },
        }
        char = self._character(record)
        # Query intersecting only chunk 0:0
        results = visits_in_bounds(char, (0, 0, 5, 5))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].node_id, f"wild:{self.wild}:1:1")

        # Query intersecting chunk 10:10 raises KnowledgeError
        with self.assertRaises(KnowledgeError):
            visits_in_bounds(char, (640, 640, 650, 650))

        # parse_knowledge raises KnowledgeError
        with self.assertRaises(KnowledgeError):
            parse_knowledge(char)

    @covers_requirement(
        "map-knowledge::map-knowledge-py-is-the-sole-writer-of-a-versioned-visited-node-record",
        "wilderness-knowledge-chunks::wilderness-observations-are-chunk-addressed",
    )
    def test_edge_padding_and_frame_boundary_validation(self):
        max_x = wilderness_provider.WILDERNESS_MAX_X
        max_y = wilderness_provider.WILDERNESS_MAX_Y
        cx = max_x // 64
        cy = max_y // 64
        out_of_bounds_local_x = (max_x % 64) + 1
        if out_of_bounds_local_x < 64:
            bad_offset = out_of_bounds_local_x
            record = {
                "schema_version": 2,
                "visited": {},
                "wilderness": {
                    self.wild: {
                        f"{cx}:{cy}": {
                            str(bad_offset): {"first_seen_tick": 1, "last_seen_tick": 1, "sight": 0}
                        }
                    }
                },
            }
            char = self._character(record)
            with self.assertRaises(KnowledgeError):
                parse_knowledge(char)

    @covers_requirement("map-knowledge::map-knowledge-py-is-the-sole-writer-of-a-versioned-visited-node-record")
    def test_node_visit_backwards_compatibility(self):
        visit = NodeVisit("room:1", 10, 20)
        self.assertEqual(visit.node_id, "room:1")
        self.assertEqual(visit.first_seen_tick, 10)
        self.assertEqual(visit.last_seen_tick, 20)
        self.assertEqual(visit.sight, 0)
        visit_with_sight = NodeVisit("wild:elosern:1:1", 10, 20, sight=5)
        self.assertEqual(visit_with_sight.sight, 5)


class _FakeCharacter:
    """Minimal fake player exposing Evennia's attribute surface used by the parser."""

    def __init__(self, record):
        self.attributes = _FakeAttributes(record)


class _FakeAttributes:
    def __init__(self, value):
        self._value = value

    def get(self, key, default=None):
        return self._value

    def has(self, key):
        return self._value is not None


if __name__ == "__main__":
    unittest.main()
