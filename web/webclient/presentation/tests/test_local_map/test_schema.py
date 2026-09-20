from tools.spec_traceability import covers_requirement
import unittest
from unittest.mock import patch
from web.webclient.presentation.local_map import (
    COORD_MAX,
    COORD_MIN,
    LOCAL_MAP_SCHEMA_VERSION,
    MAX_EDGES,
    MAX_EXIT_REF_CHARS,
    MAX_LEGEND,
    MAX_NODES,
    MAX_STRING_CODE_POINTS,
    MAX_TITLE_CODE_POINTS,
    validate_local_map,
)
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    ProtocolValidationError,
    json_byte_size,
)

from ._support import _T_MAP_KEY, _valid_edge, _valid_node, _valid_panel



class LocalMapSchemaTests(unittest.TestCase):
    def test_valid_interior_panel_passes(self):
        normalized = validate_local_map(_valid_panel())
        self.assertEqual(normalized["schema_version"], LOCAL_MAP_SCHEMA_VERSION)
        self.assertTrue(normalized["available"])
        self.assertEqual(normalized["layer"], "interior")
        self.assertEqual(normalized["current_node"], "room:5")

    def test_rejects_unknown_and_missing_fields(self):
        payload = _valid_panel()
        payload["bogus"] = 1
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(payload)

        payload = _valid_panel()
        del payload["nodes"]
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(payload)

    def test_rejects_more_than_one_current_node(self):
        payload = _valid_panel()
        payload["nodes"][1]["current"] = True
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(payload)

    def test_rejects_current_node_absent_from_nodes(self):
        payload = _valid_panel()
        payload["current_node"] = "room:999"
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(payload)

    def test_layer_must_match_current_node_prefix(self):
        payload = _valid_panel()
        payload["layer"] = "grid"
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(payload)
        payload = _valid_panel(layer="wilderness")
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(payload)

    def test_rejects_unknown_layer_and_visibility(self):
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(layer="dungeon"))
        nodes = [_valid_node(visibility="hidden")]
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(nodes=nodes))

    def test_edges_must_reference_presented_nodes(self):
        payload = _valid_panel()
        payload["edges"][0]["source"] = "room:999"
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(payload)

    def test_action_descriptor_is_null_or_exact_move(self):
        nodes = [
            _valid_node(),
            _valid_node(
                id="room:6",
                label="走廊",
                x=1,
                y=0,
                visibility="visible_unvisited",
                current=False,
                action={
                    "kind": "move",
                    "exit_ref": "42",
                    "destination": "room:6",
                },
            ),
        ]
        self.assertTrue(validate_local_map(_valid_panel(nodes=nodes)))
        bad_kind = list(nodes)
        bad_kind[1] = dict(bad_kind[1])
        bad_kind[1]["action"] = {"kind": "teleport", "exit_ref": "42", "destination": "room:6"}
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(nodes=bad_kind))
        bad_ref = list(nodes)
        bad_ref[1] = dict(bad_ref[1])
        bad_ref[1]["action"] = {"kind": "move", "exit_ref": "好".encode().decode(), "destination": "room:6"}
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(nodes=bad_ref))

    @covers_requirement("webclient-local-map::local-map-is-a-read-only-version-1-presentation-panel")
    def test_every_d10a_bound_is_enforced(self):
        self.assertLessEqual(MAX_NODES, 128)
        self.assertLessEqual(MAX_EDGES, 128)
        # Node/edge/legend strings capped at 256 code points.
        node = _valid_node(label="x" * (MAX_STRING_CODE_POINTS + 1))
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(nodes=[node]))
        # Title capped at 128.
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(title="x" * (MAX_TITLE_CODE_POINTS + 1)))
        # Node ID capped at 128 chars.
        long_id = f"grid:{_T_MAP_KEY}:" + "9" * 130
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(current_node=long_id))
        # Coordinates within -1024..1024.
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(nodes=[_valid_node(x=COORD_MAX + 1)]))
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(nodes=[_valid_node(y=COORD_MIN - 1)]))
        # exit_ref 1..64 ASCII.
        nodes = [
            _valid_node(),
            _valid_node(
                id="room:6",
                label="走廊",
                x=1,
                y=0,
                visibility="visible_unvisited",
                current=False,
                action={
                    "kind": "move",
                    "exit_ref": "x" * (MAX_EXIT_REF_CHARS + 1),
                    "destination": "room:6",
                },
            ),
        ]
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(nodes=nodes))

    def test_legend_bounded_at_16(self):
        legend = ["x" * 10] * (MAX_LEGEND + 1)
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(legend=legend))

    def test_schema_version_mismatch_is_rejected(self):
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(schema_version=2))

    def test_available_false_is_rejected_by_the_available_validator(self):
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(available=False))

    def test_empty_title_and_empty_labels_are_rejected(self):
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(title="   "))
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(nodes=[_valid_node(label="  ")]))

    def test_missing_or_duplicate_current_node_is_rejected(self):
        nodes = [_valid_node(current=False, visibility="visible_unvisited")]
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(nodes=nodes))
        nodes = [
            _valid_node(),
            _valid_node(id="room:6", label="走廊", x=1, y=0, current=False, visibility="visible_unvisited"),
            _valid_node(id="room:6", label="走廊", x=2, y=0, current=False, visibility="remembered"),
        ]
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(nodes=nodes))

    def test_edges_must_be_a_list_and_legend_entries_non_empty(self):
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(edges="nope"))
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(legend=["", "x"]))

    def test_action_missing_field_is_rejected(self):
        nodes = [
            _valid_node(),
            _valid_node(
                id="room:6",
                label="走廊",
                x=1,
                y=0,
                visibility="visible_unvisited",
                current=False,
                action={"kind": "move", "exit_ref": "42"},
            ),
        ]
        with self.assertRaises(ProtocolValidationError):
            validate_local_map(_valid_panel(nodes=nodes))

    def test_worst_case_legal_payload_fits_the_envelope(self):
        from unittest.mock import patch

        # The structural maxima the schema allows -- 64 nodes, 128 edges, 16
        # legend entries -- with realistic bounded content (canonical grid node
        # IDs, room-name labels, direction edge labels, fixed legend text).
        node_ids = [
            f"grid:{_T_MAP_KEY}:{index % 8}:{index // 8}"
            for index in range(MAX_NODES)
        ]
        nodes = []
        for index in range(MAX_NODES):
            nodes.append(
                _valid_node(
                    id=node_ids[index],
                    label="南門街道" * 4,
                    x=-1024 if index % 2 else 1024,
                    y=1024 if index % 2 else -1024,
                    visibility="remembered" if index else "current",
                    current=(index == 0),
                    action=(
                        None
                        if index == 0
                        else {
                            "kind": "move",
                            "exit_ref": f"e{index}",
                            "destination": node_ids[index],
                        }
                    ),
                )
            )
        edges = [
            _valid_edge(
                source=node_ids[index % MAX_NODES],
                destination=node_ids[(index + 1) % MAX_NODES],
                label="n",
            )
            for index in range(MAX_EDGES)
        ]
        payload = _valid_panel(
            layer="grid",
            current_node=node_ids[0],
            title="測試街道圖",
            nodes=nodes,
            edges=edges,
            legend=["你目前所在的位置", "尚未探索的相鄰位置"] * 8,
        )
        with patch(
            "world.rules.map_knowledge._registered_grid_bounds",
            return_value=(8, 8),
        ):
            normalized = validate_local_map(payload)
        size = json_byte_size(normalized)
        self.assertLessEqual(size, MAX_CANONICAL_JSON_BYTES)

    @covers_requirement("webclient-local-map::local-map-is-a-read-only-version-1-presentation-panel")
    def test_byte_budget_fails_closed_on_the_theoretical_worst_case(self):
        # The per-field ceilings (256-code-point strings on every node/edge)
        # are schema bounds, not a guarantee that any combination fits the
        # envelope. A payload with max-length CJK strings on every node and
        # edge at once serializes far beyond 65,536 bytes, so the validator
        # MUST reject it -- conformance is enforced on serialized size (D10a).
        from unittest.mock import patch

        node_ids = [
            f"grid:{_T_MAP_KEY}:{index % 8}:{index // 8}"
            for index in range(MAX_NODES)
        ]
        nodes = []
        for index in range(MAX_NODES):
            nodes.append(
                _valid_node(
                    id=node_ids[index],
                    label="字" * MAX_STRING_CODE_POINTS,
                    x=COORD_MAX,
                    y=COORD_MIN,
                    visibility="remembered" if index else "current",
                    current=(index == 0),
                    action=(
                        None
                        if index == 0
                        else {
                            "kind": "move",
                            "exit_ref": "e" * MAX_EXIT_REF_CHARS,
                            "destination": node_ids[index],
                        }
                    ),
                )
            )
        edges = [
            _valid_edge(
                source=node_ids[index % MAX_NODES],
                destination=node_ids[(index + 1) % MAX_NODES],
                label="字" * MAX_STRING_CODE_POINTS,
            )
            for index in range(MAX_EDGES)
        ]
        payload = _valid_panel(
            layer="grid",
            current_node=node_ids[0],
            title="字" * MAX_TITLE_CODE_POINTS,
            nodes=nodes,
            edges=edges,
            legend=["字" * MAX_STRING_CODE_POINTS] * MAX_LEGEND,
        )
        with patch(
            "world.rules.map_knowledge._registered_grid_bounds",
            return_value=(8, 8),
        ):
            with self.assertRaises(ProtocolValidationError):
                validate_local_map(payload)


if __name__ == "__main__":
    unittest.main()
