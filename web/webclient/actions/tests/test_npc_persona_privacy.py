"""Privacy, log-leaks, and maximal envelope tests for NPC persona actions."""

from unittest.mock import MagicMock, patch
from types import SimpleNamespace

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from web.webclient.actions.dispatcher import handle_ui_action
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.presentation.coordinator import attach_coordinator
from web.webclient.presentation.protocol import validate_ui_action_result
from web.webclient.presentation.registry import build_production_registry
from world.rules.clock import get_world_clock
from world.rules.npc_persona import initialize_npc_persona


class _FakeSession:
    def __init__(self, puppet):
        self.puppet = puppet
        self.ndb = SimpleNamespace()
        self.sent = []
        self.protocol_key = "websocket"

    def msg(self, **kwargs):
        self.sent.append(kwargs)


class NpcPersonaPrivacyAndBoundsTest(EvenniaTest):
    def setUp(self):
        super().setUp()
        get_world_clock()
        self.room = create_object(Room, key="保密測試大廳")
        self.player = create_object(PlayerCharacter, key="保密玩家")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room

        self.npc = create_object(NPC, key="機密NPC")
        self.npc.npc_title = "機密人物"
        self.npc.location = self.room

        self.secret_text = "極度機密絕不外流的生平與暗號"
        self.hidden_text = "暗夜刺客隱藏身分"
        self.card = {
            "identity": {"public": "普通店員", "hidden": self.hidden_text},
            "appearance": "貌不驚人，穿著樸素。",
            "personality": "沉默寡言，低調行事。",
            "speech_style": "簡短有力。",
            "life_story": self.secret_text,
            "habit": "不留指紋。",
            "social_connection": "",
        }
        initialize_npc_persona(
            self.npc,
            self.card,
            {"kind": "profile", "profile": "secret_npc"},
        )

        self.action_registry = build_production_action_registry()
        self.presentation_registry = build_production_registry()

    def _session_and_coordinator(self):
        session = _FakeSession(self.player)
        attach_coordinator(session, self.presentation_registry)
        coordinator = session.ndb.elosern_coordinator
        coordinator.full_snapshot(SimpleNamespace(actor=self.player, protocol_version=1))
        return session, coordinator

    def _dispatch(self, session, coordinator, action_id, payload, request_id="priv-1"):
        envelope = {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": request_id,
            "base_revision": coordinator.revision,
            "action_id": action_id,
            "payload": payload,
        }
        handle_ui_action(
            session,
            self.player,
            envelope,
            action_registry=self.action_registry,
            registry=self.presentation_registry,
        )
        results = [call for call in session.sent if "ui_action_result" in call]
        return results[-1]["ui_action_result"][0][0]

    @covers_requirement("npc-persona-editor::card-data-reaches-only-the-requesting-session")
    def test_observability_and_actor_msg_contain_no_card_text(self):
        session, coordinator = self._session_and_coordinator()

        # Capture log calls by patching the module bindings where log_info / log_warn are invoked
        with patch("world.rules.npc_persona.log_info") as mock_rules_info, \
             patch("world.rules.npc_persona.log_warn") as mock_rules_warn, \
             patch("world.observability.log_info") as mock_obs_info, \
             patch("world.observability.log_warn") as mock_obs_warn, \
             self.captureOnCommitCallbacks(execute=True):

            # 1. Read
            res_read = self._dispatch(session, coordinator, "npc.persona.read", {"npc_id": self.npc.id}, request_id="priv-read")
            self.assertEqual(res_read["outcome"], "success")

            # 2. Successful update
            up_card = dict(self.card)
            up_card["appearance"] = "換上了全新的偽裝外觀"
            res_up = self._dispatch(
                session,
                coordinator,
                "npc.persona.update",
                {"npc_id": self.npc.id, "expected_persona_version": 1, "persona": up_card},
                request_id="priv-up",
            )
            self.assertEqual(res_up["outcome"], "success")

            # 3. Rejected update
            # Version conflict rejected update inside update_npc_persona triggers log_info
            res_rej = self._dispatch(
                session,
                coordinator,
                "npc.persona.update",
                {"npc_id": self.npc.id, "expected_persona_version": 99, "persona": up_card},
                request_id="priv-rej",
            )
            self.assertEqual(res_rej["outcome"], "rejected")

            all_calls = (
                list(mock_rules_info.call_args_list)
                + list(mock_rules_warn.call_args_list)
                + list(mock_obs_info.call_args_list)
                + list(mock_obs_warn.call_args_list)
            )
            for call in all_calls:
                call_str = str(call)
                self.assertNotIn(self.secret_text, call_str)
                self.assertNotIn(self.hidden_text, call_str)
                self.assertNotIn("換上了全新的偽裝外觀", call_str)

    @covers_requirement("npc-persona-editor::card-data-reaches-only-the-requesting-session")
    def test_snapshot_contains_no_card_text(self):
        session, coordinator = self._session_and_coordinator()
        # Trigger full snapshot
        coordinator.full_snapshot(SimpleNamespace(actor=self.player, protocol_version=1))
        snapshots = [call for call in session.sent if "ui_snapshot" in call]
        self.assertTrue(snapshots)
        for s in snapshots:
            s_str = str(s)
            self.assertNotIn(self.secret_text, s_str)
            self.assertNotIn(self.hidden_text, s_str)

    @covers_requirement("npc-persona-editor::card-data-reaches-only-the-requesting-session")
    def test_maximal_valid_cards_fit_envelope(self):
        # Build maximal valid cards with CJK, astral, and JSON escape chars
        # Total budget <= 2000 code points
        session, coordinator = self._session_and_coordinator()
        # A maximal authored default rides every success alongside the field.
        default_patch = patch(
            "web.webclient.actions.npc_persona_actions.authored_greeting_for",
            return_value="預" * 150 + "😀" * 150,
        )
        default_patch.start()
        self.addCleanup(default_patch.stop)

        # 1. CJK maximal card
        cjk_card = {
            "identity": {"public": "華麗公會接待總管", "hidden": "深淵臥底情報員"},
            "appearance": "金" * 300,
            "personality": "善" * 300,
            "speech_style": "客" * 300,
            "life_story": "生" * 300,
            "habit": "讀" * 300,
            "social_connection": "交" * 300,
        }
        res_cjk = self._dispatch(
            session,
            coordinator,
            "npc.persona.update",
            {"npc_id": self.npc.id, "expected_persona_version": 1, "persona": cjk_card, "offline_greeting": "問" * 300},
            request_id="max-cjk",
        )
        self.assertEqual(res_cjk["outcome"], "success")

        # 2. Astral characters
        astral_card = {
            "identity": {"public": "星空旅者", "hidden": "😀" * 20},
            "appearance": "🌌" * 150,
            "personality": "✨" * 150,
            "speech_style": "🌠" * 150,
            "life_story": "🪐" * 150,
            "habit": "🚀" * 150,
            "social_connection": "🛸" * 150,
        }
        res_astral = self._dispatch(
            session,
            coordinator,
            "npc.persona.update",
            {"npc_id": self.npc.id, "expected_persona_version": 2, "persona": astral_card, "offline_greeting": "😀" * 300},
            request_id="max-astral",
        )
        self.assertEqual(res_astral["outcome"], "success")

        # 3. JSON escape characters heavy
        # 6 fields * 200 chars = 1200 chars total block <= 2000
        escape_card = {
            "identity": {"public": "符號大師", "hidden": ""},
            "appearance": '"\\/\b\f\n\r\t' * 20,
            "personality": '"\\/\b\f\n\r\t' * 20,
            "speech_style": '"\\/\b\f\n\r\t' * 20,
            "life_story": '"\\/\b\f\n\r\t' * 20,
            "habit": '"\\/\b\f\n\r\t' * 20,
            "social_connection": '"\\/\b\f\n\r\t' * 20,
        }
        res_esc = self._dispatch(
            session,
            coordinator,
            "npc.persona.update",
            {"npc_id": self.npc.id, "expected_persona_version": 3, "persona": escape_card, "offline_greeting": '"\\/\b\f\t' * 50},
            request_id="max-escape",
        )
        self.assertEqual(res_esc["outcome"], "success")

        # Validate all envelopes with server result validator
        envelope_cjk = {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": "max-cjk",
            "outcome": res_cjk["outcome"],
            "code": res_cjk["code"],
            "message": res_cjk["message"],
            "presentation_revision": coordinator.revision,
            "data": res_cjk["data"],
        }
        v_cjk = validate_ui_action_result(envelope_cjk)
        self.assertEqual(v_cjk["outcome"], "success")
        self.assertEqual(v_cjk["data"], res_cjk["data"])
        self.assertEqual(v_cjk["data"]["offline_greeting"], "問" * 300)
        self.assertEqual(len(v_cjk["data"]["default_greeting"]), 300)

        envelope_astral = {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": "max-astral",
            "outcome": res_astral["outcome"],
            "code": res_astral["code"],
            "message": res_astral["message"],
            "presentation_revision": coordinator.revision,
            "data": res_astral["data"],
        }
        v_astral = validate_ui_action_result(envelope_astral)
        self.assertEqual(v_astral["outcome"], "success")
        self.assertEqual(v_astral["data"], res_astral["data"])

        envelope_esc = {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": "max-escape",
            "outcome": res_esc["outcome"],
            "code": res_esc["code"],
            "message": res_esc["message"],
            "presentation_revision": coordinator.revision,
            "data": res_esc["data"],
        }
        v_esc = validate_ui_action_result(envelope_esc)
        self.assertEqual(v_esc["outcome"], "success")
        self.assertEqual(v_esc["data"], res_esc["data"])
