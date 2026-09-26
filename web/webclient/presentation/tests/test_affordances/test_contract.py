"""The shipped affordance vocabulary contract constants and invariants."""
from web.webclient.presentation.affordances import (
    ACTION_CODE_ALLOWLIST,
    MAX_AFFORDANCES,
    MAX_CARDS,
    SUGGESTIBLE_ACTION_IDS,
    SURFACES,
    AffordanceView,
    default_cards,
    exploration_affordances,
    suggestible_candidates,
)
from world.rules.time_skip import DAYPARTS, unsafe_rejection
import unittest


class AffordanceContractTests(unittest.TestCase):
    def test_action_code_allowlist_is_exactly_the_twelve_actions(self):
        self.assertEqual(
            ACTION_CODE_ALLOWLIST,
            (
                "explore.move",
                "explore.look",
                "explore.talk_open",
                "explore.talk_scripted",
                "explore.talk_freeform",
                "explore.party_invite",
                "explore.party_leave",
                "explore.engage",
                "explore.wait",
                "explore.possess",
                "explore.possess_release",
                "explore.deliver",
            ),
        )
        self.assertNotIn("explore.interact", ACTION_CODE_ALLOWLIST)

    def test_suggestible_set_excludes_party_actions_and_talk_open(self):
        self.assertEqual(
            SUGGESTIBLE_ACTION_IDS,
            set(ACTION_CODE_ALLOWLIST) - {
                "explore.talk_open",
                "explore.party_invite",
                "explore.party_leave",
                "explore.possess",
                "explore.possess_release",
            },
        )

    def test_max_cards_is_five(self):
        self.assertEqual(MAX_CARDS, 5)

    def test_action_entry_shape_is_exact(self):
        entry = AffordanceView(
            action_id="explore.look",
            label="木箱",
            params={"target_id": 5},
            freeform=False,
            navigation=False,
            enabled=True,
            disabled_reason=None,
        )
        self.assertEqual(
            entry.as_dict(),
            {
                "action_id": "explore.look",
                "label": "木箱",
                "params": {"target_id": 5},
                "freeform": False,
                "navigation": False,
                "enabled": True,
                "disabled_reason": None,
            },
        )

    def test_navigation_entry_shape_is_exact(self):
        entry = AffordanceView(
            surface="guild",
            label="公會服務",
            navigation=True,
            enabled=True,
            disabled_reason=None,
        )
        self.assertEqual(
            entry.as_dict(),
            {
                "surface": "guild",
                "label": "公會服務",
                "navigation": True,
                "enabled": True,
                "disabled_reason": None,
            },
        )
        self.assertIsNone(entry.action_id)
        self.assertIsNone(entry.params)
        self.assertIsNone(entry.freeform)

    def test_discriminated_shapes_reject_mixed_fields(self):
        with self.assertRaises(ValueError):
            AffordanceView(
                action_id="explore.look",
                label="木箱",
                params={"target_id": 5},
                freeform=False,
                navigation=False,
                enabled=True,
                disabled_reason=None,
                surface="guild",
            )
        with self.assertRaises(ValueError):
            AffordanceView(
                surface="guild",
                label="公會服務",
                navigation=True,
                enabled=True,
                disabled_reason=None,
                action_id="explore.look",
            )
        with self.assertRaises(ValueError):
            AffordanceView(
                action_id="explore.take",
                label="拾取",
                params={},
                freeform=False,
                navigation=False,
                enabled=True,
                disabled_reason=None,
            )
        with self.assertRaises(ValueError):
            AffordanceView(
                surface="bank",
                label="公會",
                navigation=True,
                enabled=True,
                disabled_reason=None,
            )

    def test_enabled_reason_exclusion_is_enforced(self):
        with self.assertRaises(ValueError):
            AffordanceView(
                action_id="explore.look",
                label="木箱",
                params={"target_id": 5},
                freeform=False,
                navigation=False,
                enabled=False,
                disabled_reason=None,
            )
        with self.assertRaises(ValueError):
            AffordanceView(
                action_id="explore.look",
                label="木箱",
                params={"target_id": 5},
                freeform=False,
                navigation=False,
                enabled=True,
                disabled_reason=("locked", "此出口目前無法通行。"),
            )

    def test_disabled_reason_serializes_as_an_exact_object(self):
        entry = AffordanceView(
            action_id="explore.engage",
            label="戰鬥",
            params={"monster_id": 7},
            freeform=False,
            navigation=False,
            enabled=False,
            disabled_reason=("target_dead", "目標已經死亡。"),
        )
        self.assertEqual(
            entry.as_dict()["disabled_reason"],
            {"code": "target_dead", "message": "目標已經死亡。"},
        )

    def test_wait_baseline_daypart_is_a_stable_value(self):
        from web.webclient.presentation.affordances import BASELINE_WAIT_DAYPART

        self.assertIn(BASELINE_WAIT_DAYPART, DAYPARTS)

if __name__ == "__main__":
    unittest.main()
