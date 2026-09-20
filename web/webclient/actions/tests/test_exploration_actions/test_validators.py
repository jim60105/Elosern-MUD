"""Exact exploration payload validators (pure unit tests)."""
from web.webclient.actions.exploration_actions import (
    MAX_EXIT_REF_CHARS,
    MAX_ITEM_KEY_CHARS,
    MAX_KEYWORD_ID_CHARS,
    MAX_NODE_ID_CHARS,
    MAX_SPEECH_CODE_POINTS,
    ExplorationActionError,
    _current_node,
    _dialogue_leave_adapter,
    _deliver_adapter,
    _engage_adapter,
    _look_adapter,
    _move_adapter,
    _party_invite_adapter,
    _party_leave_adapter,
    _present_by_id,
    _resolve_exit,
    _talk_freeform_adapter,
    _talk_scripted_adapter,
    _wait_adapter,
    validate_engage_payload,
    validate_deliver_payload,
    validate_dialogue_leave_payload,
    validate_look_payload,
    validate_move_payload,
    validate_party_invite_payload,
    validate_party_leave_payload,
    validate_talk_freeform_payload,
    validate_talk_scripted_payload,
    validate_wait_payload,
)
from world.rules.time_skip import MAX_WEB_SKIP_SECONDS
import unittest
from ._support import _T_ITEM


class ExplorationValidatorTests(unittest.TestCase):
    def test_move_payload_exact(self):
        self.assertEqual(
            validate_move_payload({"exit_ref": "42", "current_node": "room:5"}),
            {"exit_ref": "42", "current_node": "room:5"},
        )
        for bad in (
            None,
            {"exit_ref": "42"},
            {"exit_ref": "42", "current_node": "room:5", "extra": 1},
            {"exit_ref": "x" * (MAX_EXIT_REF_CHARS + 1), "current_node": "room:5"},
            {"exit_ref": "中文", "current_node": "room:5"},
            {"exit_ref": "42", "current_node": "not:a:node"},
            {"exit_ref": "42", "current_node": "x" * (MAX_NODE_ID_CHARS + 1)},
        ):
            with self.assertRaises(ExplorationActionError):
                validate_move_payload(bad)

    def test_look_payload_exact(self):
        self.assertEqual(validate_look_payload({"room": True}), {"room": True})
        self.assertEqual(validate_look_payload({"target_id": 7}), {"target_id": 7})
        for bad in (
            None,
            {"room": True, "target_id": 7},
            {"room": "yes"},
            {"target_id": 0},
            {"target_id": "7"},
            {},
        ):
            with self.assertRaises(ExplorationActionError):
                validate_look_payload(bad)

    def test_talk_scripted_payload_exact(self):
        self.assertEqual(
            validate_talk_scripted_payload({"npc_id": 3, "keyword_id": "公會"}),
            {"npc_id": 3, "keyword_id": "公會"},
        )
        for bad in (
            None,
            {"npc_id": 3},
            {"npc_id": 0, "keyword_id": "公會"},
            {"npc_id": True, "keyword_id": "公會"},
            {"npc_id": 3, "keyword_id": ""},
            {"npc_id": 3, "keyword_id": "x" * (MAX_KEYWORD_ID_CHARS + 1)},
            {"npc_id": 3, "keyword_id": "公會", "extra": 1},
        ):
            with self.assertRaises(ExplorationActionError):
                validate_talk_scripted_payload(bad)

    def test_talk_freeform_payload_exact(self):
        self.assertEqual(
            validate_talk_freeform_payload({"npc_id": 3, "speech": "你好"}),
            {"npc_id": 3, "speech": "你好"},
        )
        for bad in (
            None,
            {"npc_id": 3},
            {"npc_id": 3, "speech": ""},
            {"npc_id": 3, "speech": "你" * (MAX_SPEECH_CODE_POINTS + 1)},
            {"npc_id": 3, "speech": "你好", "actor": "x"},
        ):
            with self.assertRaises(ExplorationActionError):
                validate_talk_freeform_payload(bad)

    def test_dialogue_leave_payload_exact(self):
        self.assertEqual(
            validate_dialogue_leave_payload({"npc_id": 3}), {"npc_id": 3}
        )
        for bad in (
            None,
            {},
            {"npc_id": 0},
            {"npc_id": True},
            {"npc_id": "3"},
            {"npc_id": 3, "extra": 1},
        ):
            with self.assertRaises(ExplorationActionError):
                validate_dialogue_leave_payload(bad)

    def test_party_invite_payload_exact(self):
        self.assertEqual(
            validate_party_invite_payload({"npc_id": 3, "message": ""}),
            {"npc_id": 3, "message": ""},
        )
        self.assertEqual(
            validate_party_invite_payload({"npc_id": 3, "message": "你願意嗎？"}),
            {"npc_id": 3, "message": "你願意嗎？"},
        )
        for bad in (
            None,
            {"npc_id": 3},
            {"npc_id": 3, "message": None},
            {"npc_id": 3, "message": "你" * (MAX_SPEECH_CODE_POINTS + 1)},
            {"npc_id": 0, "message": ""},
            {"npc_id": 3, "message": "", "extra": 1},
        ):
            with self.assertRaises(ExplorationActionError):
                validate_party_invite_payload(bad)

    def test_party_leave_payload_exact(self):
        self.assertEqual(
            validate_party_leave_payload({"npc_id": 9}), {"npc_id": 9}
        )
        for bad in (
            None,
            {"npc_id": 0},
            {"npc_id": "9"},
            {"npc_id": True},
            {},
            {"npc_id": 9, "x": 1},
        ):
            with self.assertRaises(ExplorationActionError):
                validate_party_leave_payload(bad)

    def test_engage_payload_exact(self):
        self.assertEqual(validate_engage_payload({"monster_id": 9}), {"monster_id": 9})
        for bad in (
            None,
            {"monster_id": 0},
            {"monster_id": "9"},
            {"monster_id": True},
            {},
            {"monster_id": 9, "x": 1},
        ):
            with self.assertRaises(ExplorationActionError):
                validate_engage_payload(bad)

    def test_wait_payload_exact(self):
        self.assertEqual(validate_wait_payload({"daypart": "dawn"}), {"daypart": "dawn"})
        self.assertEqual(validate_wait_payload({"seconds": 3600}), {"seconds": 3600})
        self.assertEqual(validate_wait_payload({"sleep": True}), {"sleep": True})
        for bad in (
            None,
            {"daypart": "tea"},
            {"seconds": 0},
            {"seconds": MAX_WEB_SKIP_SECONDS + 1},
            {"seconds": "3600"},
            {"sleep": "yes"},
            {"daypart": "dawn", "seconds": 60},
            {},
        ):
            with self.assertRaises(ExplorationActionError):
                validate_wait_payload(bad)

    def test_no_payload_accepts_actor_host_session_destination_price_or_clock(self):
        for field in (
            "actor",
            "host",
            "session_id",
            "destination",
            "destination_room",
            "price",
            "stock",
            "clock",
            "tick",
        ):
            for validator in (
                validate_move_payload,
                validate_look_payload,
                validate_talk_scripted_payload,
                validate_talk_freeform_payload,
                validate_party_invite_payload,
                validate_party_leave_payload,
                validate_engage_payload,
                validate_wait_payload,
                validate_deliver_payload,
            ):
                with self.assertRaises(ExplorationActionError):
                    validator({field: "x"})

    def test_deliver_payload_exact(self):
        self.assertEqual(
            validate_deliver_payload({"npc_id": 5, "item_key": _T_ITEM}),
            {"npc_id": 5, "item_key": _T_ITEM},
        )
        bad = (
            {},
            {"npc_id": 5},
            {"item_key": _T_ITEM},
            {"npc_id": 5, "item_key": _T_ITEM, "extra": 1},
            {"npc_id": 0, "item_key": _T_ITEM},
            {"npc_id": -1, "item_key": _T_ITEM},
            {"npc_id": 1.5, "item_key": _T_ITEM},
            {"npc_id": "5", "item_key": _T_ITEM},
            {"npc_id": True, "item_key": _T_ITEM},
            {"npc_id": None, "item_key": _T_ITEM},
            {"npc_id": 5, "item_key": ""},
            {"npc_id": 5, "item_key": "非識別鍵"},
            {"npc_id": 5, "item_key": "x" * (MAX_ITEM_KEY_CHARS + 1)},
            {"npc_id": 5, "item_key": 7},
            {"npc_id": 5, "item_key": None},
            "not an object",
            None,
            ["npc_id"],
        )
        for payload in bad:
            with self.assertRaises(ExplorationActionError, msg=payload):
                validate_deliver_payload(payload)

if __name__ == "__main__":
    unittest.main()
