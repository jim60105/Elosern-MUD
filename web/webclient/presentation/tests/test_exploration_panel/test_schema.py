from tools.spec_traceability import covers_requirement
import unittest
from web.webclient.presentation.exploration import (
    EXPLORATION_SCHEMA_VERSION,
    MAX_AFFORDANCES,
    MAX_EXIT_REF_CHARS,
    MAX_INTERACT_TARGETS,
    MAX_LABEL_CODE_POINTS,
    MAX_LOOK_ENTITIES,
    MAX_LOOK_OBJECTS,
    MAX_MOVE_EXITS,
    MAX_NODE_ID_CHARS,
    ExplorationPanelError,
    validate_exploration,
)
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    ProtocolValidationError,
    json_byte_size,
)

from ._support import _affordance, _entity, _move_row, _object, _target, _valid_panel



class ExplorationSchemaTests(unittest.TestCase):
    def test_valid_panel_passes(self):
        normalized = validate_exploration(_valid_panel())
        self.assertEqual(normalized["schema_version"], EXPLORATION_SCHEMA_VERSION)
        self.assertTrue(normalized["available"])
        self.assertEqual(normalized["kind"], "exploration")
        self.assertEqual(normalized["look"]["room"]["room"], True)
        self.assertEqual(len(normalized["interact"][0]["affordances"]), 1)

    def test_rejects_unknown_and_missing_fields(self):
        payload = _valid_panel(bogus=1)
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(payload)
        payload = _valid_panel()
        del payload["interact"]
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(payload)

    def test_rejects_wrong_kind_and_version(self):
        with self.assertRaises(ExplorationPanelError):
            validate_exploration(_valid_panel(kind="services"))
        # The version-2 panel is a protocol error in v3, as is any other version.
        with self.assertRaises(ExplorationPanelError):
            validate_exploration(_valid_panel(schema_version=2))
        with self.assertRaises(ExplorationPanelError):
            validate_exploration(_valid_panel(schema_version=4))

    def test_rejects_duplicate_interact_identities(self):
        payload = _valid_panel(
            interact=[_target(), _target(identity=5)]
        )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(payload)

    def test_exit_ref_bound_enforced(self):
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(move=[_move_row(exit_ref="x" * (MAX_EXIT_REF_CHARS + 1))])
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(_valid_panel(move=[_move_row(exit_ref="非ascii")]))

    def test_destination_must_be_canonical_node(self):
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(_valid_panel(move=[_move_row(destination="not:a:node")]))

    def test_locked_move_row_requires_reason(self):
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(move=[_move_row(enabled=False, disabled_reason=None)])
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    move=[
                        _move_row(
                            enabled=True,
                            disabled_reason={"code": "locked", "message": "此出口目前無法通行。"},
                        )
                    ]
                )
            )

    def test_affordance_kind_shapes_are_exact(self):
        # navigate must not carry action_id.
        payload = _valid_panel(
            interact=[
                _target(
                    affordances=[
                        {
                            "kind": "navigate",
                            "action_id": "explore.talk_open",
                            "surface": "guild",
                            "label": "公會服務",
                            "enabled": True,
                            "disabled_reason": None,
                        }
                    ]
                )
            ]
        )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(payload)
        # navigate is never a registered adapter: only action kind carries action_id.
        payload = _valid_panel(
            interact=[
                _target(
                    affordances=[
                        {
                            "kind": "action",
                            "surface": "guild",
                            "label": "公會服務",
                            "enabled": True,
                            "disabled_reason": None,
                        }
                    ]
                )
            ]
        )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(payload)

    def test_a_keywords_field_is_rejected(self):
        # The version-3 target descriptor is exact: the deleted keyword list
        # (with or without a talk affordance) is a protocol error.
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    interact=[
                        _target(keywords=[{"keyword_id": "公會", "label": "公會"}])
                    ]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(_valid_panel(interact=[_target(keywords=[])]))

    def test_action_id_closed_set(self):
        for action_id in (
            "explore.take",
            # The in-conversation codes left the target descriptor in v3: a
            # host's talk is exactly one explore.talk_open 交談 row.
            "explore.talk_scripted",
            "explore.talk_freeform",
        ):
            with self.subTest(action_id=action_id):
                payload = _valid_panel(
                    interact=[
                        _target(
                            affordances=[
                                {
                                    "kind": "action",
                                    "action_id": action_id,
                                    "label": "拾取",
                                    "enabled": True,
                                    "disabled_reason": None,
                                }
                            ]
                        )
                    ]
                )
                with self.assertRaises(ProtocolValidationError):
                    validate_exploration(payload)

    def test_affordance_count_bound(self):
        payload = _valid_panel(
            interact=[
                _target(
                    affordances=[
                        {
                            "kind": "action",
                            "action_id": "explore.engage",
                            "label": "戰鬥",
                            "enabled": True,
                            "disabled_reason": None,
                        }
                    ]
                    * (MAX_AFFORDANCES + 1)
                )
            ]
        )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(payload)

    def test_list_count_bounds(self):
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    move=[_move_row(exit_ref=str(i), destination=f"room:{i}") for i in range(MAX_MOVE_EXITS + 1)]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    look={
                        **_valid_panel()["look"],
                        "entities": [
                            _entity(identity=i) for i in range(MAX_LOOK_ENTITIES + 1)
                        ],
                    }
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    look={
                        **_valid_panel()["look"],
                        "objects": [
                            _object(identity=i) for i in range(MAX_LOOK_OBJECTS + 1)
                        ],
                    }
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    interact=[_target(identity=i) for i in range(MAX_INTERACT_TARGETS + 1)]
                )
            )

    @covers_requirement("webclient-exploration-menu::portrait-focus-stays-client-local-against-the-art-catalog-seam")
    def test_portrait_ref_must_be_null(self):
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    interact=[_target(portrait_ref="catalog:goblin")]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(_valid_panel(look={
                **_valid_panel()["look"],
                "entities": [_entity(portrait_ref="catalog:goblin")],
            }))

    def test_disguise_like_availability_entries_are_exact(self):
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(_valid_panel(character={"available": True, "extra": 1}))
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(_valid_panel(quests={"available": "yes"}))

    def test_worst_case_legal_payload_fits_the_envelope(self):
        # The structural maxima the schema allows -- 12 exits, 32 entities,
        # 32 objects, 32 targets with 8 affordances each -- with realistic
        # bounded content.
        move = [
            _move_row(
                exit_ref=f"e{i}",
                label="東邊出口" * 2,
                destination=f"room:{i + 1000}",
            )
            for i in range(MAX_MOVE_EXITS)
        ]
        entities = [
            _entity(identity=i + 1, display_name="南門守衛" * 2)
            for i in range(MAX_LOOK_ENTITIES)
        ]
        objects = [
            _object(identity=1000 + i, display_name="木箱") for i in range(MAX_LOOK_OBJECTS)
        ]
        interact = []
        for i in range(MAX_INTERACT_TARGETS):
            affordances = [_affordance()]
            for _ in range(MAX_AFFORDANCES - 1):
                affordances.append(
                    {
                        "kind": "action",
                        "action_id": "explore.engage",
                        "label": "戰鬥",
                        "enabled": True,
                        "disabled_reason": None,
                    }
                )
            interact.append(
                _target(
                    identity=i + 1,
                    display_name="守衛",
                    affordances=affordances,
                )
            )
        payload = _valid_panel(
            move=move,
            look={
                "room": {"identity": 3, "display_name": "南門", "room": True},
                "entities": entities,
                "objects": objects,
            },
            interact=interact,
        )
        normalized = validate_exploration(payload)
        size = json_byte_size(normalized)
        self.assertLessEqual(size, MAX_CANONICAL_JSON_BYTES)

    def test_byte_budget_fails_closed_on_the_theoretical_worst_case(self):
        # Per-field ceilings are bounds, not a guarantee any combination fits.
        # A payload with 8 max-label affordances on every one of 32 targets
        # serializes far beyond the envelope, so the validator MUST reject it --
        # conformance is enforced on serialized size (D10).
        wide = "😀" * MAX_LABEL_CODE_POINTS
        interact = []
        for i in range(MAX_INTERACT_TARGETS):
            interact.append(
                _target(
                    identity=i + 1,
                    display_name=wide,
                    affordances=[
                        _affordance(label=wide) for _ in range(MAX_AFFORDANCES)
                    ],
                )
            )
        payload = _valid_panel(interact=interact)
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(payload)

    def test_rejects_blank_labels_and_bad_branch_shapes(self):
        wide_node = "x" * (MAX_NODE_ID_CHARS + 1)
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(move=[_move_row(exit_ref="e1", destination=wide_node)])
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    interact=[
                        _target(
                            affordances=[
                                {
                                    "kind": "action",
                                    "action_id": "explore.engage",
                                    "label": "戰鬥",
                                    "enabled": False,
                                    "disabled_reason": {"code": "locked", "message": " "},
                                }
                            ],
                        )
                    ]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(interact=[_target(affordances=[42])])
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    interact=[
                        _target(
                            affordances=[
                                {
                                    "kind": "cast",
                                    "action_id": "explore.engage",
                                    "label": "戰鬥",
                                    "enabled": True,
                                    "disabled_reason": None,
                                }
                            ]
                        )
                    ]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    interact=[
                        _target(
                            affordances=[
                                {
                                    "kind": "action",
                                    "action_id": "explore.engage",
                                    "label": " ",
                                    "enabled": True,
                                    "disabled_reason": None,
                                }
                            ]
                        )
                    ]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    interact=[
                        _target(
                            affordances=[
                                {
                                    "kind": "action",
                                    "action_id": "explore.engage",
                                    "label": "戰鬥",
                                    "enabled": False,
                                    "disabled_reason": None,
                                }
                            ],
                        )
                    ]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    interact=[
                        _target(
                            affordances=[
                                {
                                    "kind": "action",
                                    "action_id": "explore.engage",
                                    "label": "戰鬥",
                                    "enabled": True,
                                    "disabled_reason": {
                                        "code": "locked",
                                        "message": "此出口目前無法通行。",
                                    },
                                }
                            ],
                        )
                    ]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    interact=[
                        _target(
                            affordances=[
                                {
                                    "kind": "navigate",
                                    "surface": "bank",
                                    "label": "公會",
                                    "enabled": True,
                                    "disabled_reason": None,
                                }
                            ]
                        )
                    ]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    look={
                        "room": {"identity": 1, "display_name": "南門", "room": True},
                        "entities": [_entity(display_name=" ")],
                        "objects": [],
                    }
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    look={
                        "room": {"identity": 1, "display_name": "南門", "room": True},
                        "entities": [_entity(kind="goblin")],
                        "objects": [],
                    }
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    look={
                        "room": {"identity": 1, "display_name": "南門", "room": True},
                        "entities": [],
                        "objects": [_object(display_name=" ")],
                    }
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    look={
                        "room": {"identity": 1, "display_name": " ", "room": True},
                        "entities": [],
                        "objects": [],
                    }
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    look={
                        "room": {"identity": 1, "display_name": "南門", "room": False},
                        "entities": [],
                        "objects": [],
                    }
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(
                _valid_panel(
                    interact=[_target(identity=1, display_name=" ")]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_exploration(_valid_panel(move=[_move_row(label=" ")]))
        with self.assertRaises(ExplorationPanelError):
            validate_exploration(_valid_panel(available=False))

    def test_over_envelope_fails_closed(self):
        wide = "😀" * MAX_LABEL_CODE_POINTS
        interact = []
        for i in range(MAX_INTERACT_TARGETS):
            interact.append(
                _target(
                    identity=i + 1,
                    display_name=wide,
                    affordances=[
                        _affordance(label=wide)
                        for _ in range(MAX_AFFORDANCES)
                    ],
                )
            )
        payload = _valid_panel(
            move=[_move_row(exit_ref=f"e{i}", label=wide) for i in range(MAX_MOVE_EXITS)],
            interact=interact,
        )
        with self.assertRaises(ExplorationPanelError):
            validate_exploration(payload)


if __name__ == "__main__":
    unittest.main()
