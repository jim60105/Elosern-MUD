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

from ._support import (
    _T_MAP_KEY,
    _t_grid_id,
    _t_wild_id,
    _valid_edge,
    _valid_node,
    _valid_panel,
)



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
    def test_gateway_is_required_and_exactly_null_or_bounded_leads_to(self):
        # Accepted forms: null, and an exact {leads_to} object at the shared
        # 256-code-point node-string bound, normalized unchanged.
        for gateway in (None, {"leads_to": "北境"}, {"leads_to": "字" * MAX_STRING_CODE_POINTS}):
            with self.subTest(accepted=gateway):
                normalized = validate_local_map(_valid_panel(nodes=[_valid_node(gateway=gateway)], edges=[]))
                self.assertEqual(normalized["nodes"][0]["gateway"], gateway)
                self.assertEqual(set(normalized["nodes"][0]), set(_valid_node()))

        # Omission is rejected: there is no default and no alias.
        omitted = _valid_node()
        del omitted["gateway"]
        with self.assertRaisesRegex(ProtocolValidationError, "gateway|leads_to"):
            validate_local_map(_valid_panel(nodes=[omitted], edges=[]))
        aliased = _valid_node()
        aliased["gateway_leads_to"] = aliased.pop("gateway")
        with self.assertRaisesRegex(ProtocolValidationError, "gateway|leads_to"):
            validate_local_map(_valid_panel(nodes=[aliased], edges=[]))

        for malformed in (
            "北境",
            0,
            False,
            [],
            [{"leads_to": "北境"}],
            {},
            {"leads_to": "北境", "label": "北境"},
            {"to": "北境"},
            {"leads_to": ""},
            {"leads_to": "   "},
            {"leads_to": None},
            {"leads_to": 5},
            {"leads_to": ["北境"]},
            {"leads_to": "字" * (MAX_STRING_CODE_POINTS + 1)},
        ):
            with self.subTest(rejected=malformed):
                with self.assertRaisesRegex(ProtocolValidationError, "gateway|leads_to"):
                    validate_local_map(_valid_panel(nodes=[_valid_node(gateway=malformed)], edges=[]))

    def test_builder_dedup_never_loses_gateway_metadata(self):
        from web.webclient.presentation.local_map import _GraphBuilder

        gateway = {"leads_to": "北境"}
        # A node first added without metadata is enriched by a later add...
        builder = _GraphBuilder({})
        builder.add_node("room:7", "門", 0, 0, visibility="visible_unvisited")
        builder.add_node("room:7", "門", 0, 0, visibility="visible_unvisited", gateway=gateway)
        self.assertEqual(builder.nodes[0]["gateway"], gateway)
        # ...and a later null add never downgrades metadata already carried.
        builder = _GraphBuilder({})
        builder.add_node("room:7", "門", 0, 0, visibility="visible_unvisited", gateway=gateway)
        builder.add_node("room:7", "門", 0, 0, visibility="visible_unvisited")
        self.assertEqual(len(builder.nodes), 1)
        self.assertEqual(builder.nodes[0]["gateway"], gateway)
        # The builder default is null on every emitted node.
        builder = _GraphBuilder({})
        builder.add_node("room:8", "廳", 0, 0, visibility="current", current=True)
        self.assertIsNone(builder.nodes[0]["gateway"])

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
        # Coordinates within the shared metric envelope.
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

    @covers_requirement(
        "webclient-local-map::metric-coordinates-survive-authoritative-transport-and-uniform-projection"
    )
    def test_metric_settlement_and_wilderness_frames_share_one_envelope(self):
        """The wire envelope carries integer metres and the wilderness frame.

        It is a transport bound only: a settlement node at (6500, 6350) and a
        wilderness node at (2699, 2699) are both legal, while a fraction, a
        non-finite value, a numeric string or a value just past either bound
        stays rejected rather than reaching the renderer as guessed geometry.
        """
        self.assertEqual((COORD_MIN, COORD_MAX), (-10_000_000, 10_000_000))

        settlement = _valid_panel(
            layer="grid",
            current_node=_t_grid_id(6500, 6350),
            nodes=[
                _valid_node(id=_t_grid_id(6500, 6350), x=6500, y=6350),
                _valid_node(
                    id=_t_grid_id(6500, 6351),
                    label="北門",
                    x=6500,
                    y=6351,
                    visibility="visible_visited",
                    current=False,
                    action={
                        "kind": "move",
                        "exit_ref": "n",
                        "destination": _t_grid_id(6500, 6351),
                    },
                ),
            ],
            edges=[
                _valid_edge(
                    source=_t_grid_id(6500, 6350),
                    destination=_t_grid_id(6500, 6351),
                )
            ],
        )
        # The payload envelope admits integer metres; the grid identity itself
        # still resolves against the map's own registered extent. The metric
        # settlement declaration that widens that extent ships with
        # `activate-metric-settlements`, so this transport test registers a
        # synthetic extent instead of inventing a shipped coordinate.
        with patch(
            "world.rules.map_knowledge._registered_grid_bounds",
            return_value=(10_000_000, 10_000_000),
        ):
            normalized = validate_local_map(settlement)
        self.assertEqual(
            {node["id"]: (node["x"], node["y"]) for node in normalized["nodes"]},
            {
                _t_grid_id(6500, 6350): (6500, 6350),
                _t_grid_id(6500, 6351): (6500, 6351),
            },
        )

        wilderness = _valid_panel(
            layer="wilderness",
            current_node=_t_wild_id(2699, 2699),
            nodes=[
                _valid_node(id=_t_wild_id(2699, 2699), x=2699, y=2699),
                _valid_node(
                    id=_t_wild_id(2698, 2699),
                    label="林地",
                    x=2698,
                    y=2699,
                    visibility="visible_unvisited",
                    current=False,
                    action={
                        "kind": "move",
                        "exit_ref": "w",
                        "destination": _t_wild_id(2698, 2699),
                    },
                ),
            ],
            edges=[
                _valid_edge(
                    source=_t_wild_id(2699, 2699),
                    destination=_t_wild_id(2698, 2699),
                )
            ],
        )
        # The wilderness frame bounds identity through the published provider
        # projection; the envelope admits exactly those coordinates.
        with (
            patch("world.maps.wilderness_provider.WILDERNESS_MAX_X", 2699),
            patch("world.maps.wilderness_provider.WILDERNESS_MAX_Y", 2699),
        ):
            self.assertTrue(validate_local_map(wilderness)["available"])

        for malformed in (
            {"x": 100.5},
            {"x": True},
            {"x": float("nan")},
            {"y": float("inf")},
            {"x": "100"},
            {"x": COORD_MIN - 1},
            {"y": COORD_MAX + 1},
        ):
            with self.subTest(malformed=malformed):
                with self.assertRaises(ProtocolValidationError):
                    validate_local_map(
                        _valid_panel(nodes=[_valid_node(**malformed)])
                    )

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
                    # Realistic gateway metadata on every eighth node.
                    gateway=({"leads_to": "測試遠方荒原"} if index % 8 == 0 else None),
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
                    gateway={"leads_to": "字" * MAX_STRING_CODE_POINTS},
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
