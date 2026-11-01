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
    validate_talk_open_payload,
    validate_talk_scripted_descriptor,
    validate_talk_scripted_payload,
    validate_wait_payload,
)
from world.lore.dialogue.codec import make_generated_topic_id
from world.rules.time_skip import MAX_WEB_SKIP_SECONDS
import unittest
from tools.spec_traceability import covers_requirement
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
            validate_talk_scripted_payload(
                {"npc_id": 3, "topic_id": "guild_staff.topic_01", "context_id": "c1", "selection_id": "s1"}
            ),
            {"npc_id": 3, "topic_id": "guild_staff.topic_01", "context_id": "c1", "selection_id": "s1"},
        )
        for bad in (
            None,
            {"npc_id": 3},
            {"npc_id": 0, "topic_id": "guild_staff.topic_01", "context_id": "c1", "selection_id": "s1"},
            {"npc_id": True, "topic_id": "guild_staff.topic_01", "context_id": "c1", "selection_id": "s1"},
            {"npc_id": 3, "topic_id": "", "context_id": "c1", "selection_id": "s1"},
            {"npc_id": 3, "topic_id": "x" * 2049, "context_id": "c1", "selection_id": "s1"},
            {"npc_id": 3, "topic_id": "guild_staff.topic_01", "context_id": "c1", "selection_id": ""},
            {"npc_id": 3, "topic_id": "guild_staff.topic_01", "context_id": "c1", "selection_id": "s1", "extra": 1},
        ):
            with self.assertRaises(ExplorationActionError):
                validate_talk_scripted_payload(bad)

    @covers_requirement(
        "authored-dialogue-availability::locked-presentation-treats-generated-identities-as-opaque"
    )
    def test_talk_scripted_admits_a_full_generated_topic_identity_verbatim(self):
        topic_id = make_generated_topic_id("套" * 64, "r" * 64, "phase_1", "locked_intro")
        self.assertGreater(len(topic_id), 96)
        self.assertLessEqual(len(topic_id), 2048)
        payload = validate_talk_scripted_payload(
            {"npc_id": 3, "topic_id": topic_id, "context_id": "c1", "selection_id": "s1"}
        )
        self.assertEqual(payload["topic_id"], topic_id)
        descriptor = validate_talk_scripted_descriptor(
            {"npc_id": 3, "topic_id": topic_id, "context_id": "c1"}
        )
        self.assertEqual(descriptor["topic_id"], topic_id)

    def test_talk_open_payload_exact(self):
        self.assertEqual(validate_talk_open_payload({"npc_id": 1}), {"npc_id": 1})
        for bad in (
            None,
            {},
            {"npc_id": 1, "keyword_id": "公會"},
            {"npc_id": 1, "speech": "你好"},
            {"npc_id": 0},
            {"npc_id": True},
            {"npc_id": "1"},
        ):
            with self.assertRaises(ExplorationActionError):
                validate_talk_open_payload(bad)

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
        # Scope and mode default to self/recovery at dispatch; absent fields
        # stay absent so the adapter can tell an explicit request apart.
        self.assertEqual(validate_wait_payload({"sleep": True}), {"sleep": True})
        self.assertEqual(
            validate_wait_payload({"sleep": True, "sleep_scope": "party"}),
            {"sleep": True, "sleep_scope": "party"},
        )
        self.assertEqual(
            validate_wait_payload(
                {"sleep": True, "sleep_mode": "duration", "seconds": 7200}
            ),
            {"sleep": True, "sleep_mode": "duration", "seconds": 7200},
        )
        for bad in (
            None,
            {"sleep": True, "dream": True},
            {"daypart": "tea"},
            {"seconds": 0},
            {"seconds": MAX_WEB_SKIP_SECONDS + 1},
            {"seconds": "3600"},
            {"sleep": "yes"},
            {"daypart": "dawn", "seconds": 60},
            {},
            {"sleep": False},
            {"sleep": True, "sleep_scope": "all"},
            {"sleep": True, "sleep_mode": "until-recovered"},
            {"sleep": True, "sleep_mode": "duration"},
            {"sleep": True, "seconds": 60},
            {"sleep": True, "sleep_mode": "duration", "seconds": True},
            {"sleep": True, "sleep_mode": "duration", "seconds": 0},
            {"sleep": True, "sleep_mode": "duration", "seconds": MAX_WEB_SKIP_SECONDS + 1},
            {"sleep": True, "unknown": 1},
            {"sleep": True, "sleep_scope": "party", "daypart": "dawn"},
            {"sleep": True, "sleep_scope": "party", "dream": True},
            {"sleep": True, "dream": True, "seconds": 60},
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
                validate_talk_open_payload,
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


class CampingValidatorTests(unittest.TestCase):
    """Camp and dawn/dream sleep payloads and result data stay exact."""

    def test_camp_payloads_and_sleep_grammar(self):
        from web.webclient.actions.exploration_actions import (
            validate_camp_payload,
            validate_camp_preview_payload,
            validate_sleep_party_payload,
        )

        self.assertEqual(validate_camp_preview_payload({}), {})
        for bad in (None, [], {"mode": "until-dawn"}, {"x": 1}):
            with self.assertRaises(ExplorationActionError, msg=bad):
                validate_camp_preview_payload(bad)
        self.assertEqual(
            validate_camp_payload({"mode": "until-dawn", "dream": False}),
            {"mode": "until-dawn", "dream": False},
        )
        for bad in (
            {},
            {"mode": "until-dawn"},
            {"dream": True},
            {"mode": "until-noon", "dream": False},
            {"mode": "recovery", "dream": False},
            {"mode": "until-dawn", "dream": 1},
            {"mode": "until-dawn", "dream": 0},
            {"mode": "until-dawn", "dream": "yes"},
            {"mode": "until-dawn", "dream": False, "seconds": 60},
            {"mode": "until-dawn", "dream": False, "request_identity": {}},
            None,
        ):
            with self.assertRaises(ExplorationActionError, msg=bad):
                validate_camp_payload(bad)

        # Dawn and the explicit opt-in on the existing sleep grammar.
        self.assertEqual(
            validate_wait_payload({"sleep": True, "sleep_mode": "until-dawn"}),
            {"sleep": True, "sleep_mode": "until-dawn"},
        )
        self.assertEqual(
            validate_wait_payload(
                {"sleep": True, "sleep_mode": "duration", "seconds": 60, "dream": True}
            ),
            {"sleep": True, "sleep_mode": "duration", "seconds": 60, "dream": True},
        )
        self.assertEqual(validate_sleep_party_payload({}), {})
        self.assertEqual(
            validate_sleep_party_payload({"sleep_mode": "until-dawn", "dream": False}),
            {"sleep_mode": "until-dawn", "dream": False},
        )
        for bad in (
            {"sleep": True, "sleep_mode": "until-dawn", "seconds": 60},
            {"sleep": True, "sleep_mode": "until-dawn", "dream": 1},
            {"sleep": True, "dream": False},
        ):
            with self.assertRaises(ExplorationActionError, msg=bad):
                validate_wait_payload(bad)
        for bad in (
            {"dream": True},
            {"seconds": 60},
            {"sleep_mode": "duration"},
            {"sleep_mode": "until-dawn", "dream": "no"},
            {"sleep_mode": "until-dawn", "extra": 1},
            None,
        ):
            with self.assertRaises(ExplorationActionError, msg=bad):
                validate_sleep_party_payload(bad)

    @staticmethod
    def _preview():
        member = {
            "member_id": "7", "name": "同伴", "current_reserve": 180000,
            "predicted_reserve": 360000, "reserve_max": 360000,
            "current_percent": 50, "predicted_percent": 100,
            "wake_tick": 900, "wake_time": "第 1 日 06:00",
        }
        return {
            "available": True, "refusal": None, "dream_offerable": True,
            "default_mode": "until-dawn", "current_tick": 100,
            "current_time": "第 1 日 20:00",
            "modes": [
                {"mode": "until-dawn", "available": True, "refusal": None,
                 "dream_offerable": True, "wake_tick": 900,
                 "wake_time": "第 1 日 06:00", "members": [member]},
                {"mode": "until-recovered", "available": False,
                 "refusal": {"code": "party_unavailable", "message": "無法入睡。"},
                 "dream_offerable": False, "wake_tick": None, "wake_time": None,
                 "members": []},
            ],
        }

    @staticmethod
    def _result(**overrides):
        value = {
            "camp_id": "a" * 64, "phase": "complete",
            "timing": {"elapsed_seconds": 800, "result_tick": 900,
                       "result_time": "第 1 日 06:00", "wake_tick": 900,
                       "wake_time": "第 1 日 06:00"},
            "members": [{"member_id": "7", "name": "同伴", "reserve_before": 1,
                         "reserve_after": 2, "reserve_max": 360000,
                         "before_percent": 0, "after_percent": 0,
                         "sleeping": False, "wake_tick": 900}],
            "events": [{"kind": "daily_reset", "due_tick": 864, "interactive": False, "text": None}],
            "interrupted": False, "interruption_reason": None,
        }
        value.update(overrides)
        return value

    def test_camp_result_data_shapes(self):
        import copy

        from web.webclient.actions.exploration_actions import (
            validate_camp_preview_data,
            validate_camp_result_data,
        )

        validate_camp_preview_data(self._preview())
        validate_camp_result_data(self._result())
        validate_camp_result_data(
            self._result(phase="interrupted", interrupted=True, interruption_reason="interactive_event",
                         timing={"elapsed_seconds": 10, "result_tick": 110, "result_time": "x",
                                 "wake_tick": None, "wake_time": None})
        )
        bad_previews = []
        for mutate in (
            lambda d: d.update(extra=1),
            lambda d: d.update(available=1),
            lambda d: d.update(default_mode="recovery"),
            lambda d: d["modes"].reverse(),
            lambda d: d["modes"][1].update(members=[d["modes"][0]["members"][0]]),
            lambda d: d["modes"][0].update(refusal={"code": "x", "message": "y"}),
            lambda d: d["modes"][0]["members"][0].update(predicted_percent=101),
            lambda d: d["modes"][0]["members"][0].update(current_reserve=True),
            lambda d: d.update(available=False),
        ):
            value = copy.deepcopy(self._preview())
            mutate(value)
            bad_previews.append(value)
        for value in bad_previews:
            with self.assertRaises(ExplorationActionError, msg=value):
                validate_camp_preview_data(value)
        for value in (
            self._result(extra=1),
            self._result(phase="done"),
            self._result(interrupted=True),
            self._result(interruption_reason="interactive_event"),
            self._result(events=[{"kind": "x", "due_tick": -1, "interactive": False, "text": None}]),
            self._result(members=[{"member_id": "7"}]),
            self._result(phase="dream"),
            self._result(timing={"elapsed_seconds": 1, "result_tick": 1, "result_time": "x",
                                 "wake_tick": 5, "wake_time": None}),
        ):
            with self.assertRaises(ExplorationActionError, msg=value):
                validate_camp_result_data(value)

if __name__ == "__main__":
    unittest.main()
