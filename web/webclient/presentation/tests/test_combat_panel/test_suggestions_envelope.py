import unittest
from tools.spec_traceability import covers_requirement
from web.webclient.presentation.combat_panel import ContextActionsError, validate_context_actions
from web.webclient.presentation.protocol import ProtocolValidationError

from ._support import (
    _exploration_panel,
    _ready_suggestions,
    _suggestion_card,
    _valid_category_group,
    _valid_panel,
    _valid_skill,
    _valid_skill_group,
)



class SuggestionsEnvelopeTests(unittest.TestCase):
    """Per-status suggestions schema tests (tasks 1.3-1.4)."""

    @covers_requirement("webclient-context-actions-suggestions::the-context-actions-panel-carries-a-suggestions-envelope-at-version-5")
    def test_generating_and_unavailable_carry_only_status(self):
        for status in ("generating", "unavailable"):
            with self.subTest(status=status):
                normalized = validate_context_actions(
                    _exploration_panel(suggestions={"status": status})
                )
                self.assertEqual(normalized["suggestions"], {"status": status})

    def test_unknown_status_rejects(self):
        for status in ("bogus", "", 1, None):
            with self.subTest(status=status):
                with self.assertRaises(ProtocolValidationError):
                    validate_context_actions(
                        _exploration_panel(suggestions={"status": status, "cards": []})
                    )

    def test_generating_and_unavailable_reject_cards_and_extra_keys(self):
        for status in ("generating", "unavailable"):
            with self.subTest(status=status):
                with self.assertRaises(ProtocolValidationError):
                    validate_context_actions(
                        _exploration_panel(suggestions={"status": status, "cards": []})
                    )
                with self.assertRaises(ProtocolValidationError):
                    validate_context_actions(
                        _exploration_panel(suggestions={"status": status, "extra": 1})
                    )

    def test_ready_and_degraded_require_both_fields(self):
        with self.assertRaises(ProtocolValidationError):
            validate_context_actions(_exploration_panel(suggestions={"status": "ready"}))
        with self.assertRaises(ProtocolValidationError):
            validate_context_actions(
                _exploration_panel(suggestions={"status": "degraded"})
            )
        with self.assertRaises(ProtocolValidationError):
            validate_context_actions(
                _exploration_panel(suggestions={"status": "ready", "cards": [], "extra": 1})
            )

    def test_ready_count_bound_rejects(self):
        for count in (0, 1, 2, 6):
            with self.subTest(count=count):
                with self.assertRaises(ProtocolValidationError):
                    validate_context_actions(
                        _exploration_panel(suggestions=_ready_suggestions(count))
                    )

    def test_degraded_count_bound_accepts_zero_and_rejects_over_cap(self):
        normalized = validate_context_actions(
            _exploration_panel(suggestions={"status": "degraded", "cards": []})
        )
        self.assertEqual(normalized["suggestions"], {"status": "degraded", "cards": []})
        with self.assertRaises(ProtocolValidationError):
            validate_context_actions(
                _exploration_panel(
                    suggestions={"status": "degraded", "cards": [_suggestion_card()] * 6}
                )
            )

    def test_ready_suggestions_accept_and_normalize(self):
        payload = _ready_suggestions()
        normalized = validate_context_actions(_exploration_panel(suggestions=payload))
        self.assertEqual(normalized["suggestions"]["status"], "ready")
        self.assertEqual(len(normalized["suggestions"]["cards"]), 3)
        self.assertEqual(normalized["suggestions"]["cards"][0]["params"], {"room": True})
        self.assertEqual(
            normalized["suggestions"]["cards"][1]["params"],
            {"daypart": "noon"},
        )

    @covers_requirement("webclient-context-actions-suggestions::suggestion-cards-are-a-bounded-closed-exact-shape")
    def test_card_exact_keys_reject(self):
        valid = _suggestion_card()
        cases = (
            {**valid, "extra": 1},
            {k: v for k, v in valid.items() if k != "params"},
            {**valid, "kind": "bogus"},
            {**valid, "action_code": "explore.take"},
            {**valid, "action_code": "explore.talk_freeform"},
            {**valid, "label": " "},
            {**valid, "label": "abc"},
            {**valid, "label": "很" * 25},
            {**valid, "hint": "很" * 61},
            {**valid, "params": {"room": True, "extra": 1}},
            {**valid, "params": {"room": False}},
            {**valid, "params": {"room": "yes"}},
            {**valid, "params": {"target_id": 0}},
            {**valid, "params": {}},
            {**valid, "params": [1, 2]},
        )
        for card in cases:
            with self.subTest(card=card):
                with self.assertRaises(Exception):
                    validate_context_actions(
                        _exploration_panel(
                            suggestions={"status": "ready", "cards": [card] * 3}
                        )
                    )

    def test_freeform_card_pins_explore_talk_freeform_and_binding_params(self):
        freeform = {
            "kind": "freeform",
            "action_code": "explore.talk_freeform",
            "label": "隨意聊聊",
            "params": {"npc_id": 9},
        }
        cards = [_suggestion_card(), freeform, _suggestion_card(label="查看木箱")]
        normalized = validate_context_actions(
            _exploration_panel(suggestions={"status": "ready", "cards": cards})
        )
        self.assertEqual(normalized["suggestions"]["cards"][1]["kind"], "freeform")
        self.assertEqual(
            normalized["suggestions"]["cards"][1]["action_code"],
            "explore.talk_freeform",
        )
        self.assertEqual(normalized["suggestions"]["cards"][1]["params"], {"npc_id": 9})
        bad_freeform_cards = (
            {**freeform, "action_code": "explore.move"},
            {**freeform, "params": {"npc_id": 9, "speech": "你好"}},
            {**freeform, "params": {"npc_id": 0}},
            {**freeform, "params": {}},
        )
        for bad in bad_freeform_cards:
            with self.subTest(bad=bad):
                with self.assertRaises(Exception):
                    validate_context_actions(
                        _exploration_panel(
                            suggestions={
                                "status": "ready",
                                "cards": [_suggestion_card(), bad, _suggestion_card(label="查看木箱")],
                            }
                        )
                    )

    def test_room_survey_boolean_accepts_and_other_booleans_reject(self):
        payload = validate_context_actions(
            _exploration_panel(suggestions=_ready_suggestions())
        )
        self.assertEqual(payload["suggestions"]["cards"][0]["params"], {"room": True})
        bad = {
            "kind": "known_action",
            "action_code": "explore.wait",
            "label": "等待片刻",
            "params": {"sleep": True},
        }
        with self.assertRaises(ProtocolValidationError):
            validate_context_actions(
                _exploration_panel(
                    suggestions={
                        "status": "ready",
                        "cards": [_suggestion_card(), bad, _suggestion_card(label="查看木箱")],
                    }
                )
            )

    def test_hint_optional_and_bounded(self):
        card = {**_suggestion_card(), "hint": "可以查看整個房間。"}
        normalized = validate_context_actions(
            _exploration_panel(
                suggestions={
                    "status": "ready",
                    "cards": [card, _suggestion_card(label="查看木箱"), _suggestion_card(label="查看南門")],
                }
            )
        )
        self.assertEqual(normalized["suggestions"]["cards"][0]["hint"], "可以查看整個房間。")
        self.assertIsNone(normalized["suggestions"]["cards"][1]["hint"])

    def test_combat_form_pins_suggestions_unavailable(self):
        normalized = validate_context_actions(_valid_panel())
        self.assertEqual(normalized["suggestions"], {"status": "unavailable"})
        for suggestions in (
            {"status": "ready", "cards": [_suggestion_card()] * 3},
            {"status": "generating"},
            {"status": "degraded", "cards": []},
        ):
            with self.subTest(suggestions=suggestions):
                with self.assertRaises(ContextActionsError):
                    validate_context_actions(_valid_panel(suggestions=suggestions))

    def test_deepest_legitimate_envelope_leaf_stays_at_depth_eleven(self):
        # Design D-5: with suggestions.cards[].params present (leaf depth 7),
        # the deepest legitimate envelope leaf remains combat skills at depth
        # 11 (the freeform_scales entry value), so MAX_DEPTH = 12 needs no
        # change. Depth is measured from the ui_snapshot envelope root exactly
        # like check_json_safety.
        from web.webclient.presentation.protocol import MAX_DEPTH, check_json_safety

        payload = _valid_panel(
            skills=[
                _valid_category_group(
                    groups=[_valid_skill_group(
                        skills=[
                            _valid_skill(
                                freeform_scales=[
                                    {"scale": 0.25, "label": "1/4", "mp_cost": 5},
                                    {"scale": 0.5, "label": "1/2", "mp_cost": 10},
                                    {"scale": 1.0, "label": "1", "mp_cost": 20},
                                    {"scale": 2.0, "label": "2", "mp_cost": 40},
                                    {"scale": 4.0, "label": "4", "mp_cost": 80},
                                ]
                            )
                        ]
                    )]
                )
            ],
            suggestions={
                "status": "ready",
                "cards": [
                    {**_suggestion_card(), "hint": "查看房間"},
                    _suggestion_card(label="查看木箱"),
                    _suggestion_card(label="查看南門"),
                ],
            },
        )
        envelope = {"panels": {"context_actions": payload}}

        def _leaf_depth(value, depth=0):
            if isinstance(value, dict):
                children = value.values()
            elif isinstance(value, list):
                children = value
            else:
                return depth
            if not children:
                return depth
            return max(_leaf_depth(child, depth + 1) for child in children)

        check_json_safety(envelope)
        self.assertEqual(_leaf_depth(envelope), 11)
        self.assertLessEqual(_leaf_depth(envelope), MAX_DEPTH)


if __name__ == "__main__":
    unittest.main()
