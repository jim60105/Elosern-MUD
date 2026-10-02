"""Unit and integration tests for NPC persona author actions."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from web.webclient.actions.dispatcher import handle_ui_action
from web.webclient.actions.npc_persona_actions import (
    CODE_NOT_ALLOWED,
    CODE_NO_TARGET,
    CODE_UNAVAILABLE,
    CODE_VERSION_CONFLICT,
    NpcPersonaActionError,
    read_npc_persona_adapter,
    update_npc_persona_adapter,
    validate_read_payload,
    validate_update_payload,
)
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.presentation.coordinator import attach_coordinator
from web.webclient.presentation.registry import build_production_registry
from world.lore.npc_card import normalize_card
from world.rules.clock import get_world_clock
from world.rules.npc_persona import initialize_npc_persona, read_npc_persona


def _valid_card_dict():
    return {
        "identity": {"public": "公會侍者", "hidden": "秘密情報員"},
        "appearance": "金髮藍眼，身材修長。",
        "personality": "隨和熱心，善於傾聽。",
        "speech_style": "客氣得體，條理分明。",
        "life_story": "在公會服務五年，熟悉城中大小事。",
        "habit": "工作時習慣擦拭玻璃杯。",
        "social_connection": "與公會會長及多名冒險者相熟。",
    }


class _FakeSession:
    def __init__(self, puppet):
        self.puppet = puppet
        self.ndb = SimpleNamespace()
        self.sent = []
        self.protocol_key = "websocket"

    def msg(self, **kwargs):
        self.sent.append(kwargs)


class _NpcPersonaActionsFixture:
    """Shared room/actor/NPC setup and dispatch helpers (no test methods)."""

    def setUp(self):
        super().setUp()
        get_world_clock()
        self.room = create_object(Room, key="公會大廳")
        self.player = create_object(PlayerCharacter, key="測試玩家")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room

        self.npc = create_object(NPC, key="接待員愛麗絲")
        self.npc.npc_title = "資深接待員"
        self.npc.location = self.room
        initialize_npc_persona(
            self.npc,
            _valid_card_dict(),
            {"kind": "profile", "profile": "alice_waitress"},
        )


    def _session_and_coordinator(self, actor=None):
        target_actor = actor or self.player
        session = _FakeSession(target_actor)
        self.presentation_registry = build_production_registry()
        self.action_registry = build_production_action_registry()
        attach_coordinator(session, self.presentation_registry)
        coordinator = session.ndb.elosern_coordinator
        coordinator.full_snapshot(SimpleNamespace(actor=target_actor, protocol_version=1))
        return session, coordinator

    def _envelope(self, coordinator, action_id, payload, request_id="req-1"):
        return {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": request_id,
            "base_revision": coordinator.revision,
            "action_id": action_id,
            "payload": payload,
        }

    def _dispatch(self, session, coordinator, action_id, payload, request_id="req-1", actor=None):
        target_actor = actor or self.player
        envelope = self._envelope(coordinator, action_id, payload, request_id=request_id)
        handle_ui_action(
            session,
            target_actor,
            envelope,
            action_registry=self.action_registry,
            registry=self.presentation_registry,
        )
        results = [call for call in session.sent if "ui_action_result" in call]
        return results[-1]["ui_action_result"][0][0]

    def _update(self, session, coordinator, version, card=None, greeting=None, request_id="g-up"):
        payload = {
            "npc_id": self.npc.id,
            "expected_persona_version": version,
            "persona": card or _valid_card_dict(),
        }
        if greeting is not None:
            payload["offline_greeting"] = greeting
        return self._dispatch(session, coordinator, "npc.persona.update", payload, request_id=request_id)


class NpcPersonaActionsAdmissionAndMutationTest(_NpcPersonaActionsFixture, EvenniaTest):
    """Tests for admission, reads, updates, and deduplication of NPC persona actions."""

    @covers_requirement("npc-persona-editor::author-editing-admits-only-a-co-located-npc-for-the-session-s-own-active-character")
    def test_read_success_in_exploration_mode(self):
        session, coordinator = self._session_and_coordinator()
        result = self._dispatch(
            session, coordinator, "npc.persona.read", {"npc_id": self.npc.id}
        )
        self.assertEqual(result["outcome"], "success")
        data = result["data"]
        self.assertEqual(data["npc_id"], self.npc.id)
        self.assertEqual(data["display_name"], "接待員愛麗絲")
        self.assertEqual(data["npc_title"], "資深接待員")
        self.assertEqual(data["persona_version"], 1)
        self.assertEqual(data["persona"]["identity"]["hidden"], "秘密情報員")

    @covers_requirement("npc-persona-editor::author-editing-admits-only-a-co-located-npc-for-the-session-s-own-active-character")
    def test_read_success_in_dialogue_mode(self):
        session, coordinator = self._session_and_coordinator()
        # In dialogue mode, in_exploration_mode is true
        other_npc = create_object(NPC, key="對話NPC")
        other_npc.location = self.room
        from world.rules.dialogue import open_or_refresh_dialogue
        open_or_refresh_dialogue(self.player, other_npc, "你好")

        result = self._dispatch(
            session, coordinator, "npc.persona.read", {"npc_id": self.npc.id}
        )
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["data"]["npc_id"], self.npc.id)

    @covers_requirement("npc-persona-editor::author-editing-admits-only-a-co-located-npc-for-the-session-s-own-active-character")
    def test_rejections_for_forbidden_modes(self):
        session, coordinator = self._session_and_coordinator()

        # 1. Creation pending
        self.player.creation_pending = True
        res = self._dispatch(
            session, coordinator, "npc.persona.read", {"npc_id": self.npc.id}, request_id="cp-read"
        )
        self.assertEqual(res["outcome"], "rejected")
        self.assertEqual(res["code"], CODE_NOT_ALLOWED)
        self.assertNotIn("data", res)

        res_up = self._dispatch(
            session,
            coordinator,
            "npc.persona.update",
            {"npc_id": self.npc.id, "expected_persona_version": 1, "persona": _valid_card_dict()},
            request_id="cp-up",
        )
        self.assertEqual(res_up["outcome"], "rejected")
        self.assertEqual(res_up["code"], CODE_NOT_ALLOWED)
        self.player.creation_pending = False

        # 2. In active combat
        with patch("world.rules.combat_session.is_in_active_session", return_value=True):
            res_c = self._dispatch(
                session, coordinator, "npc.persona.read", {"npc_id": self.npc.id}, request_id="combat-read"
            )
            self.assertEqual(res_c["outcome"], "rejected")
            self.assertEqual(res_c["code"], CODE_NOT_ALLOWED)

        # 3. Possessed NPC
        with patch("web.webclient.actions.npc_persona_actions.is_possessed_actor", return_value=True):
            res_p = self._dispatch(
                session, coordinator, "npc.persona.read", {"npc_id": self.npc.id}, request_id="pos-read"
            )
            self.assertEqual(res_p["outcome"], "rejected")
            self.assertEqual(res_p["code"], CODE_NOT_ALLOWED)

    @covers_requirement("npc-persona-editor::author-editing-admits-only-a-co-located-npc-for-the-session-s-own-active-character")
    def test_rejections_for_forbidden_targets(self):
        session, coordinator = self._session_and_coordinator()

        # Forged/nonexistent id
        res = self._dispatch(session, coordinator, "npc.persona.read", {"npc_id": 999999}, request_id="r-none")
        self.assertEqual(res["outcome"], "rejected")
        self.assertEqual(res["code"], CODE_NO_TARGET)
        self.assertNotIn("data", res)

        # Another player character
        other_player = create_object(PlayerCharacter, key="其他玩家")
        other_player.location = self.room
        res_op = self._dispatch(session, coordinator, "npc.persona.read", {"npc_id": other_player.id}, request_id="r-op")
        self.assertEqual(res_op["outcome"], "rejected")
        self.assertEqual(res_op["code"], CODE_NO_TARGET)

        # Monster
        monster = create_object(Monster, key="哥布林")
        monster.location = self.room
        res_m = self._dispatch(session, coordinator, "npc.persona.read", {"npc_id": monster.id}, request_id="r-m")
        self.assertEqual(res_m["outcome"], "rejected")
        self.assertEqual(res_m["code"], CODE_NO_TARGET)

        # Remote NPC (different room)
        other_room = create_object(Room, key="其他房間")
        remote_npc = create_object(NPC, key="遠方NPC")
        remote_npc.location = other_room
        initialize_npc_persona(remote_npc, _valid_card_dict(), {"kind": "profile", "profile": "remote_npc"})
        res_rn = self._dispatch(session, coordinator, "npc.persona.read", {"npc_id": remote_npc.id}, request_id="r-rn")
        self.assertEqual(res_rn["outcome"], "rejected")
        self.assertEqual(res_rn["code"], CODE_NO_TARGET)

        # NPC moved after read
        self.npc.location = other_room
        res_moved = self._dispatch(
            session,
            coordinator,
            "npc.persona.update",
            {"npc_id": self.npc.id, "expected_persona_version": 1, "persona": _valid_card_dict()},
            request_id="up-moved",
        )
        self.assertEqual(res_moved["outcome"], "rejected")
        self.assertEqual(res_moved["code"], CODE_NO_TARGET)
        self.npc.location = self.room

        # NPC deleted
        deleted_npc = create_object(NPC, key="被刪除NPC")
        deleted_npc.location = self.room
        del_id = deleted_npc.id
        deleted_npc.delete()
        res_del = self._dispatch(session, coordinator, "npc.persona.read", {"npc_id": del_id}, request_id="r-del")
        self.assertEqual(res_del["outcome"], "rejected")
        self.assertEqual(res_del["code"], CODE_NO_TARGET)

    @covers_requirement("npc-persona-editor::npc-persona-read-returns-a-private-editor-snapshot-with-the-offline-greeting")
    def test_uninitialized_npc_is_unavailable(self):
        session, coordinator = self._session_and_coordinator()
        uninit_npc = create_object(NPC, key="未初始化NPC")
        uninit_npc.location = self.room

        res = self._dispatch(session, coordinator, "npc.persona.read", {"npc_id": uninit_npc.id}, request_id="r-uninit")
        self.assertEqual(res["outcome"], "rejected")
        self.assertEqual(res["code"], CODE_UNAVAILABLE)
        self.assertNotIn("data", res)

    @covers_requirement("webclient-action-dispatch::stale-presentation-state-prevents-adapter-invocation")
    def test_stale_presentation_epoch_rejected_before_adapter(self):
        session, coordinator = self._session_and_coordinator()
        valid_epoch = coordinator.epoch
        envelope = {
            "protocol_version": 1,
            "presentation_epoch": valid_epoch,
            "request_id": "r-stale",
            "base_revision": coordinator.revision - 1,
            "action_id": "npc.persona.read",
            "payload": {"npc_id": self.npc.id},
        }
        handle_ui_action(
            session,
            self.player,
            envelope,
            action_registry=self.action_registry,
            registry=self.presentation_registry,
        )
        results = [call for call in session.sent if "ui_action_result" in call]
        res = results[-1]["ui_action_result"][0][0]
        self.assertEqual(res["outcome"], "stale")
        self.assertEqual(res["code"], "stale")

    @covers_requirement("webclient-action-dispatch::ui-actions-use-an-exact-bounded-request-envelope")
    def test_malformed_payload_rejects_without_invoking_adapter(self):
        session, coordinator = self._session_and_coordinator()
        # Missing expected_persona_version
        res = self._dispatch(
            session,
            coordinator,
            "npc.persona.update",
            {"npc_id": self.npc.id, "persona": _valid_card_dict()},
            request_id="malformed-1",
        )
        self.assertEqual(res["outcome"], "rejected")
        self.assertEqual(res["code"], "malformed_payload")

    @covers_requirement("npc-persona-editor::npc-persona-update-replaces-the-card-and-offline-greeting-under-a-version-check")
    def test_update_advances_version_and_touches_only_selected_npc(self):
        session, coordinator = self._session_and_coordinator()

        # Create a second NPC with the same profile
        npc2 = create_object(NPC, key="接待員鮑勃")
        npc2.location = self.room
        initialize_npc_persona(npc2, _valid_card_dict(), {"kind": "profile", "profile": "alice_waitress"})

        # Record baseline state of player
        clock_before = get_world_clock().tick
        npc2_card_before = read_npc_persona(npc2).card.to_record()
        npc2_version_before = read_npc_persona(npc2).version

        changed_card = _valid_card_dict()
        changed_card["appearance"] = "銀白短髮，身材高挑。"

        res = self._dispatch(
            session,
            coordinator,
            "npc.persona.update",
            {"npc_id": self.npc.id, "expected_persona_version": 1, "persona": changed_card},
            request_id="up-1",
        )
        self.assertEqual(res["outcome"], "success")
        data = res["data"]
        self.assertEqual(data["persona_version"], 2)
        self.assertEqual(data["persona"]["appearance"], "銀白短髮，身材高挑。")

        # Verify NPC1 updated in db
        snap1 = read_npc_persona(self.npc)
        self.assertEqual(snap1.version, 2)
        self.assertEqual(snap1.card.appearance, "銀白短髮，身材高挑。")

        # Verify NPC2 untouched
        snap2 = read_npc_persona(npc2)
        self.assertEqual(snap2.version, npc2_version_before)
        self.assertEqual(snap2.card.to_record(), npc2_card_before)

        # Clock untouched
        self.assertEqual(get_world_clock().tick, clock_before)

    @covers_requirement("npc-persona-editor::npc-persona-update-replaces-the-card-and-offline-greeting-under-a-version-check")
    def test_identical_card_update_returns_success_unchanged(self):
        session, coordinator = self._session_and_coordinator()
        res = self._dispatch(
            session,
            coordinator,
            "npc.persona.update",
            {"npc_id": self.npc.id, "expected_persona_version": 1, "persona": _valid_card_dict()},
            request_id="up-ident",
        )
        self.assertEqual(res["outcome"], "success")
        self.assertEqual(res["data"]["persona_version"], 1)
        self.assertEqual(res["message"], "設定未變更。")

    @covers_requirement("npc-persona-editor::npc-persona-update-replaces-the-card-and-offline-greeting-under-a-version-check")
    def test_version_conflict_rejection(self):
        session, coordinator = self._session_and_coordinator()
        res = self._dispatch(
            session,
            coordinator,
            "npc.persona.update",
            {"npc_id": self.npc.id, "expected_persona_version": 99, "persona": _valid_card_dict()},
            request_id="up-conflict",
        )
        self.assertEqual(res["outcome"], "rejected")
        self.assertEqual(res["code"], CODE_VERSION_CONFLICT)
        self.assertIn("目前第 1 版", res["message"])
        self.assertNotIn("data", res)

    @covers_requirement("npc-persona-editor::npc-persona-update-replaces-the-card-and-offline-greeting-under-a-version-check")
    def test_field_violation_maps_to_field_specific_code(self):
        session, coordinator = self._session_and_coordinator()

        # Empty speech_style
        card = _valid_card_dict()
        card["speech_style"] = ""
        res = self._dispatch(
            session,
            coordinator,
            "npc.persona.update",
            {"npc_id": self.npc.id, "expected_persona_version": 1, "persona": card},
            request_id="up-empty-speech",
        )
        self.assertEqual(res["outcome"], "rejected")
        self.assertEqual(res["code"], "npc_persona.required_empty.speech_style")
        self.assertNotIn("data", res)

        # Leaf too long (> 600)
        card = _valid_card_dict()
        card["appearance"] = "A" * 601
        res = self._dispatch(
            session,
            coordinator,
            "npc.persona.update",
            {"npc_id": self.npc.id, "expected_persona_version": 1, "persona": card},
            request_id="up-long-app",
        )
        self.assertEqual(res["outcome"], "rejected")
        self.assertEqual(res["code"], "npc_persona.leaf_too_long.appearance")

        # Identity section too long (> 600 total rendered identity)
        card = _valid_card_dict()
        card["identity"]["public"] = "公" * 300
        card["identity"]["hidden"] = "隱" * 300
        res = self._dispatch(
            session,
            coordinator,
            "npc.persona.update",
            {"npc_id": self.npc.id, "expected_persona_version": 1, "persona": card},
            request_id="up-id-overflow",
        )
        self.assertEqual(res["outcome"], "rejected")
        self.assertEqual(res["code"], "npc_persona.identity_section_too_long.identity")

        # Card block total > 2000
        card = _valid_card_dict()
        for f_key in ("appearance", "personality", "speech_style", "life_story", "habit", "social_connection"):
            card[f_key] = "字" * 330
        res = self._dispatch(
            session,
            coordinator,
            "npc.persona.update",
            {"npc_id": self.npc.id, "expected_persona_version": 1, "persona": card},
            request_id="up-total-overflow",
        )
        self.assertEqual(res["outcome"], "rejected")
        self.assertEqual(res["code"], "npc_persona.card_too_long")

    @covers_requirement("npc-persona-editor::npc-persona-update-replaces-the-card-and-offline-greeting-under-a-version-check")
    def test_deduplicated_request_id_returns_cached_result_without_second_write(self):
        session, coordinator = self._session_and_coordinator()
        changed_card = _valid_card_dict()
        changed_card["appearance"] = "紅色長髮。"

        res1 = self._dispatch(
            session,
            coordinator,
            "npc.persona.update",
            {"npc_id": self.npc.id, "expected_persona_version": 1, "persona": changed_card},
            request_id="dedup-test-1",
        )
        self.assertEqual(res1["outcome"], "success")
        self.assertEqual(res1["data"]["persona_version"], 2)

        # Re-dispatching with the same request_id
        res2 = self._dispatch(
            session,
            coordinator,
            "npc.persona.update",
            {"npc_id": self.npc.id, "expected_persona_version": 1, "persona": changed_card},
            request_id="dedup-test-1",
        )
        self.assertEqual(res2["outcome"], "success")
        self.assertEqual(res2["data"]["persona_version"], 2)
        # Version remained 2, no second write occurred
        self.assertEqual(read_npc_persona(self.npc).version, 2)


def _t_profile(key: str, greeting: str | None):
    """A file-local synthetic profile whose voice carries ``greeting``."""
    from world.lore.npc_card import NpcCard, NpcCardIdentity
    from world.lore.npc_profiles.shape import NpcProfile, NpcVoiceLines

    return NpcProfile(
        key=key,
        card=NpcCard(
            identity=NpcCardIdentity(public="測試者", hidden=""),
            appearance="外觀",
            personality="性格",
            speech_style="語氣",
            life_story="經歷",
            habit="習慣",
            social_connection="",
        ),
        age=25,
        apparent_age=25,
        voice=NpcVoiceLines(greeting=greeting),
    )


class NpcPersonaOfflineGreetingActionsTest(_NpcPersonaActionsFixture, EvenniaTest):
    """The offline-greeting extension of the editor transport (window change, design §13a)."""

    def setUp(self):
        super().setUp()
        # Every greeting test resolves the profile provenance against a
        # file-local synthetic registry entry (no shipped content).
        self._registry_patch = patch(
            "world.lore.npc_profiles.NPC_PROFILE_REGISTRY",
            {"alice_waitress": _t_profile("alice_waitress", "「歡迎來到公會。」")},
        )
        self._registry_patch.start()
        self.addCleanup(self._registry_patch.stop)

    @covers_requirement("npc-persona-editor::npc-persona-read-returns-a-private-editor-snapshot-with-the-offline-greeting")
    def test_read_returns_exactly_seven_keys_with_field_and_profile_default(self):
        self.npc.db.npc_offline_greeting = "自訂開場白。"
        session, coordinator = self._session_and_coordinator()
        result = self._dispatch(session, coordinator, "npc.persona.read", {"npc_id": self.npc.id})
        self.assertEqual(result["outcome"], "success")
        data = result["data"]
        self.assertEqual(
            set(data),
            {"npc_id", "display_name", "npc_title", "persona_version", "persona", "offline_greeting", "default_greeting"},
        )
        self.assertEqual(data["offline_greeting"], "自訂開場白。")
        self.assertEqual(data["default_greeting"], "「歡迎來到公會。」")
        # Reading wrote nothing: the default never lands in the field.
        self.assertEqual(self.npc.db.npc_offline_greeting, "自訂開場白。")

    @covers_requirement("npc-persona-editor::npc-persona-read-returns-a-private-editor-snapshot-with-the-offline-greeting")
    def test_table_greeting_wins_the_default_and_is_never_projected(self):
        session, coordinator = self._session_and_coordinator()
        with patch("world.rules.dialogue.greeting_for", return_value="「表格裡的問候。」"):
            result = self._dispatch(session, coordinator, "npc.persona.read", {"npc_id": self.npc.id})
        data = result["data"]
        self.assertEqual(data["default_greeting"], "「表格裡的問候。」")
        self.assertEqual(data["offline_greeting"], "")
        self.assertFalse(self.npc.attributes.has("npc_offline_greeting"))

    @covers_requirement("npc-persona-editor::npc-persona-read-returns-a-private-editor-snapshot-with-the-offline-greeting")
    def test_free_form_npc_reads_two_empty_greetings(self):
        free = create_object(NPC, key="無名旅人")
        free.location = self.room
        initialize_npc_persona(free, _valid_card_dict(), {"kind": "import", "record": "t_free_form"})
        session, coordinator = self._session_and_coordinator()
        result = self._dispatch(session, coordinator, "npc.persona.read", {"npc_id": free.id})
        self.assertEqual(result["data"]["offline_greeting"], "")
        self.assertEqual(result["data"]["default_greeting"], "")
        self.assertFalse(free.attributes.has("npc_offline_greeting"))

    @covers_requirement("npc-persona-editor::npc-persona-update-replaces-the-card-and-offline-greeting-under-a-version-check")
    def test_greeting_only_save_advances_once_and_clearing_restores_the_default(self):
        from world.rules.dialogue import resolve_greeting

        session, coordinator = self._session_and_coordinator()
        res = self._update(session, coordinator, 1, greeting="  「今天也辛苦了。」\r\n", request_id="g-1")
        self.assertEqual(res["outcome"], "success")
        self.assertEqual(res["code"], "updated")
        self.assertEqual(res["data"]["persona_version"], 2)
        self.assertEqual(res["data"]["offline_greeting"], "「今天也辛苦了。」")
        self.assertEqual(resolve_greeting(self.npc).text, "「今天也辛苦了。」")
        self.assertTrue(resolve_greeting(self.npc).is_override)
        self.assertEqual(read_npc_persona(self.npc).card.to_record(), normalize_card(_valid_card_dict()).to_record())

        # The identical card and greeting is a no-op at the same version.
        same = self._update(session, coordinator, 2, greeting="「今天也辛苦了。」", request_id="g-2")
        self.assertEqual(same["code"], "unchanged")
        self.assertEqual(same["data"]["persona_version"], 2)

        # Clearing removes the override; the authored default answers again.
        cleared = self._update(session, coordinator, 2, greeting="", request_id="g-3")
        self.assertEqual(cleared["data"]["persona_version"], 3)
        self.assertEqual(cleared["data"]["offline_greeting"], "")
        self.assertEqual(cleared["data"]["default_greeting"], "「歡迎來到公會。」")
        self.assertFalse(self.npc.attributes.has("npc_offline_greeting"))
        self.assertEqual(resolve_greeting(self.npc).text, "「歡迎來到公會。」")
        self.assertFalse(resolve_greeting(self.npc).is_override)

    @covers_requirement("npc-persona-editor::npc-persona-update-replaces-the-card-and-offline-greeting-under-a-version-check")
    def test_card_and_greeting_change_together_advances_once(self):
        session, coordinator = self._session_and_coordinator()
        card = _valid_card_dict()
        card["habit"] = "閒暇時替盆栽澆水。"
        res = self._update(session, coordinator, 1, card=card, greeting="「有事嗎？」")
        self.assertEqual(res["data"]["persona_version"], 2)
        self.assertEqual(res["data"]["persona"]["habit"], "閒暇時替盆栽澆水。")
        self.assertEqual(res["data"]["offline_greeting"], "「有事嗎？」")

    @covers_requirement("npc-persona-editor::npc-persona-update-replaces-the-card-and-offline-greeting-under-a-version-check")
    def test_invalid_greeting_is_rejected_without_writing(self):
        session, coordinator = self._session_and_coordinator()
        card = _valid_card_dict()
        card["habit"] = "改過的習慣。"
        for index, greeting in enumerate(("問" * 301, "第一段。\n第二段。")):
            with self.subTest(index=index):
                res = self._update(session, coordinator, 1, card=card, greeting=greeting, request_id=f"g-bad-{index}")
                self.assertEqual(res["outcome"], "rejected")
                self.assertEqual(res["code"], "npc_persona.greeting_invalid")
                self.assertIn("離線問候語", res["message"])
                self.assertNotIn("data", res)
        snapshot = read_npc_persona(self.npc)
        self.assertEqual(snapshot.version, 1)
        self.assertEqual(snapshot.card.habit, _valid_card_dict()["habit"])
        self.assertFalse(self.npc.attributes.has("npc_offline_greeting"))

    @covers_requirement("npc-persona-editor::npc-persona-update-replaces-the-card-and-offline-greeting-under-a-version-check")
    def test_non_text_greeting_is_a_malformed_payload(self):
        session, coordinator = self._session_and_coordinator()
        with patch("web.webclient.actions.npc_persona_actions.update_npc_persona") as service:
            res = self._update(session, coordinator, 1, greeting=42, request_id="g-num")
        self.assertEqual(res["code"], "malformed_payload")
        service.assert_not_called()

    @covers_requirement("npc-persona-editor::npc-persona-update-replaces-the-card-and-offline-greeting-under-a-version-check")
    def test_greeting_edit_affects_only_the_selected_npc(self):
        npc2 = create_object(NPC, key="接待員鮑勃")
        npc2.location = self.room
        initialize_npc_persona(npc2, _valid_card_dict(), {"kind": "profile", "profile": "alice_waitress"})
        session, coordinator = self._session_and_coordinator()
        self._update(session, coordinator, 1, greeting="「只對愛麗絲。」")
        self.assertEqual(read_npc_persona(npc2).version, 1)
        self.assertFalse(npc2.attributes.has("npc_offline_greeting"))


class NpcPersonaVisibilityAdmissionTest(_NpcPersonaActionsFixture, EvenniaTest):
    """Visibility revalidation on read and update (npc-persona-visible-targets)."""

    CODE_NO_TARGET = "npc_persona.no_target"

    @covers_requirement("npc-persona-editor::persona-target-admission-revalidates-current-room-visibility")
    def test_view_denied_npc_cannot_expose_card_or_accept_update(self):
        self.npc.locks.add("view:false();search:true()")
        session, coordinator = self._session_and_coordinator()

        # Read rejected as no_target without card or data
        res_read = self._dispatch(session, coordinator, "npc.persona.read", {"npc_id": self.npc.id}, request_id="v-read-1")
        self.assertEqual(res_read["outcome"], "rejected")
        self.assertEqual(res_read["code"], self.CODE_NO_TARGET)
        self.assertNotIn("data", res_read)

        # Update rejected as no_target without persisting
        card = _valid_card_dict()
        card["habit"] = "新習慣。"
        res_up = self._update(session, coordinator, 1, card=card, request_id="v-up-1")
        self.assertEqual(res_up["outcome"], "rejected")
        self.assertEqual(res_up["code"], self.CODE_NO_TARGET)
        self.assertNotIn("data", res_up)
        self.assertEqual(read_npc_persona(self.npc).version, 1)
        self.assertEqual(read_npc_persona(self.npc).card.habit, _valid_card_dict()["habit"])

    @covers_requirement("npc-persona-editor::persona-target-admission-revalidates-current-room-visibility")
    def test_search_denied_npc_cannot_expose_card_or_accept_update(self):
        self.npc.locks.add("view:true();search:false()")
        session, coordinator = self._session_and_coordinator()

        res_read = self._dispatch(session, coordinator, "npc.persona.read", {"npc_id": self.npc.id}, request_id="s-read-1")
        self.assertEqual(res_read["outcome"], "rejected")
        self.assertEqual(res_read["code"], self.CODE_NO_TARGET)
        self.assertNotIn("data", res_read)

        card = _valid_card_dict()
        card["habit"] = "新習慣。"
        res_up = self._update(session, coordinator, 1, card=card, request_id="s-up-1")
        self.assertEqual(res_up["outcome"], "rejected")
        self.assertEqual(res_up["code"], self.CODE_NO_TARGET)
        self.assertNotIn("data", res_up)
        self.assertEqual(read_npc_persona(self.npc).version, 1)

    @covers_requirement("npc-persona-editor::persona-target-admission-revalidates-current-room-visibility")
    def test_visibility_lost_after_opening_invalidates_save(self):
        session, coordinator = self._session_and_coordinator()

        # Successfully read while visible
        res_read = self._dispatch(session, coordinator, "npc.persona.read", {"npc_id": self.npc.id}, request_id="loss-read")
        self.assertEqual(res_read["outcome"], "success")
        self.assertIn("data", res_read)

        # Deny view access before update
        self.npc.locks.add("view:false()")
        card = _valid_card_dict()
        card["appearance"] = "新的外貌描述。"
        res_up = self._update(session, coordinator, 1, card=card, greeting="「新開場白。」", request_id="loss-up-view")
        self.assertEqual(res_up["outcome"], "rejected")
        self.assertEqual(res_up["code"], self.CODE_NO_TARGET)
        self.assertNotIn("data", res_up)
        self.assertEqual(read_npc_persona(self.npc).version, 1)
        self.assertEqual(read_npc_persona(self.npc).card.appearance, _valid_card_dict()["appearance"])
        self.assertFalse(self.npc.attributes.has("npc_offline_greeting"))

        # Restore view, test search loss after opening
        self.npc.locks.add("view:true();search:false()")
        res_up_search = self._update(session, coordinator, 1, card=card, greeting="「新開場白。」", request_id="loss-up-search")
        self.assertEqual(res_up_search["outcome"], "rejected")
        self.assertEqual(res_up_search["code"], self.CODE_NO_TARGET)
        self.assertNotIn("data", res_up_search)
        self.assertEqual(read_npc_persona(self.npc).version, 1)
        self.assertEqual(read_npc_persona(self.npc).card.appearance, _valid_card_dict()["appearance"])
        self.assertFalse(self.npc.attributes.has("npc_offline_greeting"))

    @covers_requirement("npc-persona-editor::persona-target-admission-revalidates-current-room-visibility")
    def test_visible_sleeping_npc_remains_author_editable(self):
        # Explicitly ensure permissive search (no search lock) and ordinary view
        self.npc.locks.add("view:true()")
        if "search" in self.npc.locks.locks:
            del self.npc.locks.locks["search"]

        # Sleeping/busy schedule blocks talking via schedule_state
        self.npc.db.schedule_state = "resting"

        session, coordinator = self._session_and_coordinator()
        res_read = self._dispatch(session, coordinator, "npc.persona.read", {"npc_id": self.npc.id}, request_id="sleep-read")
        self.assertEqual(res_read["outcome"], "success")
        self.assertEqual(res_read["data"]["persona_version"], 1)

        card = _valid_card_dict()
        card["habit"] = "夢遊中擦桌子。"
        res_up = self._update(session, coordinator, 1, card=card, greeting="「呼嚕嚕……」", request_id="sleep-up")
        self.assertEqual(res_up["outcome"], "success")
        self.assertEqual(res_up["data"]["persona_version"], 2)
        self.assertEqual(res_up["data"]["persona"]["habit"], "夢遊中擦桌子。")
        self.assertEqual(read_npc_persona(self.npc).version, 2)
