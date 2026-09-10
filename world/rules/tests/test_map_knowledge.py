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
            f"wild:{self.wild}:224:0",  # x beyond WILDERNESS_MAX_X
            f"wild:{self.wild}:0:224",  # y beyond WILDERNESS_MAX_Y
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
        record = {
            "schema_version": 1,
            "visited": {
                "room:99": {"first_seen_tick": 40, "last_seen_tick": 80},
                f"grid:{self.map}:2:0": {
                    "first_seen_tick": 10,
                    "last_seen_tick": 10,
                },
                f"wild:{self.wild}:1:1": {"first_seen_tick": 20, "last_seen_tick": 60},
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
                NodeVisit(f"wild:{self.wild}:1:1", 20, 60),
            ],
        )

    @covers_requirement("map-knowledge::parse-knowledge-isolates-corrupt-records-without-resetting-them")
    def test_corrupt_records_raise_and_are_not_reset(self):
        corrupt = [
            None,
            {"schema_version": 2, "visited": {}},
            {"schema_version": 1},
            {"schema_version": 1, "visited": []},
            {
                "schema_version": 1,
                "visited": {f"grid:{self.map}:2:0": {"first_seen_tick": "x", "last_seen_tick": 1}},
            },
            {
                "schema_version": 1,
                "visited": {"unknown:1": {"first_seen_tick": 1, "last_seen_tick": 1}},
            },
            {
                "schema_version": 1,
                "visited": {"room:5": {"first_seen_tick": -1, "last_seen_tick": 1}},
            },
            {
                "schema_version": 1,
                "visited": {"room:5": {"first_seen_tick": 1}},
            },
        ]
        for record in corrupt:
            with self.subTest(record=record):
                character = self._character(record)
                with self.assertRaises(KnowledgeError):
                    parse_knowledge(character)
                self.assertEqual(character.attributes.get("map_knowledge"), record)


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
