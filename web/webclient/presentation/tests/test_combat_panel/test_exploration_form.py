import unittest
from tools.spec_traceability import covers_requirement
from web.webclient.presentation.combat_panel import (
    CONTEXT_ACTIONS_SCHEMA_VERSION,
    ContextActionsError,
    validate_context_actions,
)
from web.webclient.presentation.protocol import ProtocolValidationError

from ._support import _exploration_panel, _valid_category_group, _valid_panel, _valid_participant



class ContextActionsExplorationFormTests(unittest.TestCase):
    @covers_requirement("webclient-context-actions::context-actions-is-an-exact-read-only-version-5-panel")
    def test_valid_exploration_form_passes(self):
        normalized = validate_context_actions(_exploration_panel())
        self.assertEqual(normalized["schema_version"], CONTEXT_ACTIONS_SCHEMA_VERSION)
        self.assertTrue(normalized["available"])
        self.assertEqual(normalized["kind"], "exploration")
        self.assertEqual(normalized["affordances"][0]["params"], {"room": True})
        self.assertEqual(
            normalized["affordances"][1]["params"],
            {"npc_id": 5, "keyword_id": "註冊"},
        )
        self.assertTrue(normalized["affordances"][2]["navigation"])
        self.assertNotIn("surface", normalized["affordances"][0])
        self.assertNotIn("action_id", normalized["affordances"][2])

    def test_combat_fields_in_the_exploration_form_reject(self):
        payload = _exploration_panel(session={"session_id": "x"}, skills=[])
        with self.assertRaises(ProtocolValidationError):
            validate_context_actions(payload)

    def test_exploration_fields_in_the_combat_form_reject(self):
        payload = _valid_panel(affordances=[_exploration_panel()["affordances"][0]])
        with self.assertRaises(ProtocolValidationError):
            validate_context_actions(payload)

    def test_wrong_kind_and_version_reject(self):
        with self.assertRaises(Exception):
            validate_context_actions(_exploration_panel(kind="combat"))
        with self.assertRaises(ContextActionsError):
            validate_context_actions(_exploration_panel(schema_version=4))
        with self.assertRaises(Exception):
            validate_context_actions(_exploration_panel(kind="bogus"))

    def test_affordance_bounds_reject(self):
        from web.webclient.presentation.combat_panel import MAX_CONTEXT_AFFORDANCES

        payload = _exploration_panel(
            affordances=[_exploration_panel()["affordances"][0]]
            * (MAX_CONTEXT_AFFORDANCES + 1)
        )
        with self.assertRaises(ContextActionsError):
            validate_context_actions(payload)
        payload = _exploration_panel(affordances=42)
        with self.assertRaises(Exception):
            validate_context_actions(payload)

    def test_affordance_entry_shapes_reject(self):
        valid = _exploration_panel()["affordances"][0]
        cases = (
            {**valid, "action_id": "explore.take"},
            {**valid, "action_id": "explore.interact"},
            {**valid, "freeform": "yes"},
            {**valid, "freeform": True},
            {
                **valid,
                "action_id": "explore.talk_freeform",
                "freeform": False,
                "params": {"npc_id": 9},
            },
            {**valid, "params": {"room": "yes"}},
            {**valid, "params": {"room": True, "extra": 1}},
            {**valid, "label": " "},
            {**valid, "enabled": False, "disabled_reason": None},
            {**valid, "enabled": True, "disabled_reason": {"code": "x", "message": "說明"}},
            {**valid, "navigation": "false"},
            {**valid, "navigation": True},
            {
                "surface": "bank",
                "label": "公會",
                "navigation": True,
                "enabled": True,
                "disabled_reason": None,
            },
            {
                "surface": "guild",
                "label": "公會服務",
                "navigation": True,
                "enabled": True,
                "disabled_reason": None,
                "action_id": "explore.look",
            },
            {
                "action_id": "explore.look",
                "label": "南門",
                "params": {"room": True},
                "freeform": False,
                "navigation": False,
                "enabled": True,
                "disabled_reason": None,
                "surface": "guild",
            },
            {**valid, "params": "room"},
            {**valid, "params": {"room": True, "target_id": 1}},
        )
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(Exception):
                    validate_context_actions(_exploration_panel(affordances=[payload]))

    def test_freeform_entry_params_are_exactly_the_binding_shape(self):
        valid = _exploration_panel()["affordances"][0]
        entry = {
            **valid,
            "action_id": "explore.talk_freeform",
            "freeform": True,
            "params": {"npc_id": 9},
        }
        normalized = validate_context_actions(_exploration_panel(affordances=[entry]))
        self.assertEqual(normalized["affordances"][0]["params"], {"npc_id": 9})
        for bad in (
            {**entry, "params": {"npc_id": 9, "speech": "你好"}},
            {**entry, "params": {"npc_id": 0}},
            {**entry, "params": {}},
        ):
            with self.assertRaises(Exception):
                validate_context_actions(_exploration_panel(affordances=[bad]))

    def test_combat_form_is_byte_identical_to_version_4_plus_suggestions(self):
        version4 = {
            "schema_version": 4,
            "available": True,
            "kind": "combat",
            "session": {
                "session_id": "hostile:1:0",
                "mode": "hostile",
                "round": 0,
                "state": "ready",
                "reason": None,
            },
            "participants": [_valid_participant()],
            "root_actions": ["attack", "skills", "items", "defend", "flee"],
            "secondary_actions": ["forfeit"],
            "skills": [_valid_category_group()],
        }
        version5 = _valid_panel()
        self.assertEqual(version4["schema_version"], 4)
        self.assertEqual(version5["schema_version"], 5)
        # Every combat field serializes exactly as at version 4; only the
        # version field and the suggestions envelope are added.
        self.assertEqual(
            {
                key: value
                for key, value in version5.items()
                if key not in ("schema_version", "suggestions")
            },
            {
                key: value
                for key, value in version4.items()
                if key != "schema_version"
            },
        )
        self.assertEqual(version5["suggestions"], {"status": "unavailable"})
        normalized = validate_context_actions(version5)
        self.assertEqual(normalized["schema_version"], 5)
        self.assertEqual(normalized["session"], version4["session"])
        self.assertEqual(normalized["participants"], version4["participants"])
        self.assertEqual(normalized["root_actions"], version4["root_actions"])
        self.assertEqual(normalized["secondary_actions"], version4["secondary_actions"])
        self.assertEqual(normalized["skills"], version4["skills"])
        self.assertEqual(normalized["suggestions"], {"status": "unavailable"})
        # A version-4 payload is rejected by the version-5 validator.
        with self.assertRaises(ProtocolValidationError):
            validate_context_actions(version4)

    def test_over_envelope_exploration_form_fails_closed(self):
        wide = "寬" * 128
        affordances = [
            {
                "action_id": "explore.look",
                "label": wide,
                "params": {"room": True},
                "freeform": False,
                "navigation": False,
                "enabled": True,
                "disabled_reason": None,
            }
            for _ in range(320)
        ]
        with self.assertRaises(ContextActionsError):
            validate_context_actions(
                _exploration_panel(affordances=affordances)
            )

    def test_unavailable_form_differs_only_in_schema_version(self):
        from web.webclient.presentation.protocol import unavailable_payload

        version4 = unavailable_payload(4, "presentation_unavailable", "目前無法顯示此介面")
        version5 = unavailable_payload(5, "presentation_unavailable", "目前無法顯示此介面")
        self.assertEqual(
            {key: value for key, value in version5.items() if key != "schema_version"},
            {key: value for key, value in version4.items() if key != "schema_version"},
        )
        self.assertEqual(version5["schema_version"], 5)
        # The common unavailable form carries exactly schema_version,
        # available, and reason — never a suggestions field (design D-1
        # amendment; the shared builder in presentation/registry.py is
        # unchanged).
        self.assertEqual(
            set(version5),
            {"schema_version", "available", "reason"},
        )
        self.assertNotIn("suggestions", version5)


if __name__ == "__main__":
    unittest.main()
