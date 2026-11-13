"""Synthetic sleep-to-dream behavior and recorded/offline changed-path smoke."""

import json
import tempfile
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import override_settings
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from twisted.internet.defer import Deferred

from commands.dream import CmdDream, render_changes, render_state
from commands.skip import CmdSleep
from server import dream_service as service
from tools.spec_traceability import covers_requirement
from web.webclient.actions.dream_actions import adapter, validate
from web.webclient.actions.exploration_actions import _wait_adapter, validate_wait_payload
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.dream import dream_presenter
from world.ai import dream, guardrail
from world.art import descriptors, formats, official as official_art, subjects
from world.art.scene_definitions import (
    load_bundled_scene_catalog,
    reset_bundled_scenes,
)
from world.ai.fake_client import FakeLLMClient
from world.ai.profiles import default_profiles
from world.ai.schemas.registry import _OUTPUT_SCHEMAS
from world.narrative import dream_proposal
from world.narrative import dream_session as lifecycle
from world.narrative import dream_surface as surface
from world.narrative.models import AuthoringDraft, CreativeRequest
from world.narrative.dream_track import prospective_state
from world.narrative.threads import create_thread, resolve_thread
from world.narrative.authoring import get_draft
from world.rules.clock import get_world_clock
from world.rules.skip_safety import SkipRejectReason


class DreamSurfaceTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.actor = create_object("typeclasses.characters.PlayerCharacter", key="Synthetic sleeper", location=self.room1)
        self.other = create_object("typeclasses.characters.PlayerCharacter", key="Synthetic outsider", location=self.room1)
        self.actor.msg = Mock()
        for gauge in ("hp", "mp", "sp", "pleasure"):
            self.actor.traits.add(gauge, gauge.upper(), trait_type="gauge", base=100, current=100, rate=1)
        self.actor.db.sexual_state = {"synthetic_counter": 9}
        self.actor.db.skill_proficiency = {"synthetic_skill": 7}
        self.actor.db.relationships = {"synthetic_other": 3}
        self.clock = get_world_clock()
        self.clock.tick = 100
        self.clock._persist(100)
        self.saved_validators = {key: dict(value) for key, value in guardrail._semantic_validators.items()}
        self.saved_fallbacks = dict(guardrail._degrade_fallbacks)
        self.saved_schemas = dict(_OUTPUT_SCHEMAS)
        dream.register_dream()
        self.profiles = override_settings(LLM_PROFILES=default_profiles())
        self.profiles.enable()
        self.live_sessions = []
        sessions = patch("evennia.SESSION_HANDLER.get_sessions", side_effect=lambda **kwargs: self.live_sessions)
        sessions.start()
        self.addCleanup(sessions.stop)

    def tearDown(self):
        self.profiles.disable()
        guardrail._semantic_validators.clear()
        guardrail._semantic_validators.update(self.saved_validators)
        guardrail._degrade_fallbacks.clear()
        guardrail._degrade_fallbacks.update(self.saved_fallbacks)
        _OUTPUT_SCHEMAS.clear()
        _OUTPUT_SCHEMAS.update(self.saved_schemas)
        super().tearDown()

    def grant_sleep(self, **overrides):
        values = {
            "tick_from": 100,
            "tick_to": 700,
            "requested_seconds": 600,
        }
        values.update(overrides)
        from world.rules.sleep_receipt import (
            KIND_VOLUNTARY,
            MODE_DURATION,
            SleepReceipt,
            STATE_SLEEPING,
            read_sleep_view_generation,
            write_sleep_receipt,
        )

        self._sleep_seq = getattr(self, "_sleep_seq", 0) + 1
        sleep_id = f"synthetic-sleep-{self._sleep_seq}"
        accepted = int(values["requested_seconds"])
        receipt = SleepReceipt(
            sleep_id=sleep_id,
            body_id=int(self.actor.pk),
            owner_id=int(self.actor.pk),
            kind=KIND_VOLUNTARY,
            mode=MODE_DURATION,
            entry_tick=int(values["tick_from"]),
            target_tick=int(values["tick_from"]) + accepted,
            limit_tick=int(values["tick_from"]) + accepted,
            settled_through_tick=int(values["tick_to"]),
            revision=0,
            state=STATE_SLEEPING,
            accepted_seconds=accepted,
            partial=False,
            entry_operation_id=sleep_id,
        )
        write_sleep_receipt(self.actor, receipt)
        return sleep_id, receipt

    def enter(self, **overrides):
        from world.rules.sleep_receipt import read_sleep_view_generation

        sleep_id, receipt = self.grant_sleep(**overrides)
        return surface.enter_for_owner(
            self.actor,
            sleep_id=sleep_id,
            revision=0,
            generation=read_sleep_view_generation(self.actor),
        )

    def request(self, action, **kwargs):
        state = service.dream_state(self.actor)
        return service.act(self.actor, action, session_id=state["session_id"], revision=state["revision"], **kwargs)

    def request_payload(self, client, index=-1):
        """The bounded user message one recorded request carried, parsed."""
        return json.loads(client.calls[index].messages[1]["content"])

    def run_dream(self, arguments):
        """The text client's dream command, ready to run as the owner."""
        command = CmdDream()
        command.caller = self.actor
        command.session = None
        command.args = arguments
        self.actor.msg.reset_mock()
        return command

    def printed(self):
        """Every message the owner received since the last command ran."""
        return [call.args[0] for call in self.actor.msg.call_args_list]

    def delivered(self, index=0):
        client = FakeLLMClient()
        client.add_response(lambda descriptor: True, json.dumps({
            "scene": "合成場景：雲海王座之前，親密的身影與漫過腳踝的積水一同隨呼吸起伏。",
            "dialogue": "我們繼續商談尋找鐘聲的故事方向。",
            "phase": prospective_state(index).level,
        }, ensure_ascii=False))
        return client

    def exchange(self, edits=(), index=0):
        """A recorded collaborator response carrying exactly these edits."""
        client = FakeLLMClient()
        client.add_response(lambda descriptor: True, json.dumps({
            "scene": "合成場景：雲海王座之前，親密的身影與漫過腳踝的積水一同隨呼吸起伏。",
            "dialogue": "我們繼續商談尋找鐘聲的故事方向。",
            "phase": prospective_state(index).level,
            "edits": list(edits),
        }, ensure_ascii=False))
        return client

    def physical(self):
        return (self.clock.tick, tuple(self.actor.traits.get(key).value for key in ("hp", "mp", "sp", "pleasure")),
                deepcopy(self.actor.db.sexual_state), deepcopy(self.actor.db.buffs),
                deepcopy(self.actor.db.skill_proficiency), deepcopy(self.actor.db.relationships))

    @covers_requirement(
        "time-skip-commands::sleep-computes-its-own-duration-from-gauge-regen-capped-at-a-configured-maximum",
        "dream-sleep-surface::optional-collaboration-follows-one-accepted-sleep-result",
        "dream-sleep-surface::dream-collaboration-consumes-the-committed-elapsed-result",
    )
    def test_zero_elapsed_sleep_opens_no_dream(self):
        for gauge in ("hp", "mp", "sp"):
            trait = self.actor.traits.get(gauge)
            trait.current = trait.max
        command = CmdSleep()
        command.caller = self.actor
        command.args = ""
        command.func()
        self.assertIsNone(service.dream_state(self.actor))
        self.assertIn("完全恢復", command.caller.msg.call_args_list[-1].args[0])
        # The legacy combined text entry is gone; it is a usage refusal and
        # never opens a dream.
        command.args = "dream"
        before = self.physical()
        command.func()
        self.assertIsNone(service.dream_state(self.actor))
        self.assertEqual(before, self.physical())
        self.assertIn("用法", command.caller.msg.call_args_list[-1].args[0])

    @covers_requirement("dream-sleep-surface::optional-collaboration-follows-one-accepted-sleep-result")
    def test_browser_zero_sleep_choice_and_ordinary_rest_wait(self):
        from world.rules.time_skip import SkipResult, SleepEntry, SleepOutcome

        empty = SkipResult("synthetic-wait", 5, 5, (), voluntary=False)
        entry = SleepEntry("synthetic-sleep", self.actor, 0, False)
        zero = SkipResult(
            "synthetic-sleep", 0, 0, (), voluntary=True, woke=True
        )
        with patch("web.webclient.actions.exploration_actions.advance_wait", return_value=empty), patch(
                "web.webclient.actions.exploration_actions.begin_sleep",
                return_value=SleepOutcome(entry, zero)):
            for payload in ({"sleep": True}, {"seconds": 5}):
                self.assertEqual(
                    _wait_adapter(
                        self.actor, validate_wait_payload(payload)
                    )["outcome"],
                    "success",
                )
                self.assertIsNone(service.dream_state(self.actor))
        # The combined sleep-and-dream payload is malformed: the accepted view
        # answer is the sole dream entry surface.
        for forged in (
            {"sleep": 1, "dream": True},
            {"sleep": True, "dream": 1},
            {"sleep": True, "dream": True},
            {"sleep": True, "dream": True, "seconds": 0},
        ):
            with self.assertRaises(ValueError):
                validate_wait_payload(forged)

    @covers_requirement(
        "skip-safety-gate::the-safety-gate-rejects-outright-it-does-not-compute-a-partial-safety-shortened",
        "dream-sleep-surface::optional-collaboration-follows-one-accepted-sleep-result",
    )
    def test_rejected_sleep_never_opens_or_advances_on_either_client(self):
        command = CmdSleep()
        command.caller = self.actor
        command.args = "dream"
        with patch("commands.skip.evaluate_skip_safety", return_value=SkipRejectReason.IN_COMBAT), patch(
                "commands.skip.get_world_clock") as clock:
            command.func()
            clock.assert_not_called()
        with patch("web.webclient.actions.exploration_actions.unsafe_rejection", return_value="合成拒絕"), patch(
                "web.webclient.actions.exploration_actions.begin_sleep") as advance:
            result = _wait_adapter(self.actor, {"sleep": True, "dream": True})
            advance.assert_not_called()
        self.assertEqual(result["outcome"], "rejected")
        self.assertIsNone(service.dream_state(self.actor))

    @covers_requirement("dream-sleep-surface::optional-collaboration-follows-one-accepted-sleep-result")
    @covers_requirement("dream-sleep-surface::dream-collaboration-consumes-the-committed-elapsed-result")
    @covers_requirement(
        "dream-sleep-surface::explicit-dream-answers-have-browser-and-text-parity"
    )
    def test_interrupted_committed_result_uses_actual_ticks_on_both_clients(self):
        for browser in (False, True):
            clock = get_world_clock()
            before = clock.tick
            sleep_id, _receipt = self.grant_sleep(
                tick_from=before, tick_to=before, requested_seconds=30
            )
            if browser:
                answer = service.answer_sleep_dream(
                    self.actor,
                    decision="enter",
                    sleep_id=sleep_id,
                    revision=0,
                    generation=0,
                )
                self.assertEqual(answer["outcome"], "success")
            else:
                dream = CmdDream()
                dream.caller = self.actor
                dream.args = "enter"
                dream.session = None
                dream.func()
            state = service.dream_state(self.actor)
            self.assertEqual(state["sleep"]["seconds"], 0)
            self.assertEqual(state["sleep"]["requested_seconds"], 30)
            self.assertEqual(get_world_clock().tick, before)
            self.actor.db.dream_surface = None

    @covers_requirement(
        "dream-explicit-presentation::dream-presentation-changes-no-live-character-effects",
        "dream-explicit-presentation::dream-collaboration-uses-the-approved-explicit-frame",
        "dream-sleep-surface::dream-departure-never-settles-sleep-again",
    )
    @covers_requirement(
        "dream-sleep-surface::confirmed-dream-handoff-returns-to-playable-waking-surfaces"
    )
    def test_recorded_changed_path_sleep_exchange_draft_confirm_awaken_smoke(self):
        self.enter()
        physical = self.physical()
        client = self.delivered()
        result = self.request("say", message="在無名港尋找失落的鐘聲。", client=client).result
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(len(client.calls), 1)
        state = dream_presenter(PresentationContext(actor=self.actor, protocol_version=1))["state"]
        self.assertIn("親密", state["scene"])
        self.assertIn("鐘聲", state["dialogue"])
        self.assertEqual(state["remaining"], 5)
        self.assertEqual(state["track"]["completed"], 1)
        # The published stage facts: one accepted exchange still converses, the
        # thread choice is locked by it, and the settled report travels with
        # the proposal it describes.
        self.assertEqual(state["stage"], lifecycle.STAGE_CONVERSING)
        self.assertEqual(state["proposal"], dream_proposal.empty_proposal())
        self.assertIsNotNone(state["changes"])
        self.assertIsNone(state["thread_id"])
        self.assertFalse(state["can_choose_thread"] or state["can_edit"] or state["drafted"])
        self.assertTrue(state["can_finalize"] and state["can_input"])
        self.assertFalse(state["can_confirm"])
        with patch("world.ai.client.OpenAICompatClient", side_effect=AssertionError("escape called model")):
            self.assertEqual(self.request("finalize").result["outcome"], "success")
            self.assertEqual(self.request("draft").result["outcome"], "success")
            self.assertEqual(CreativeRequest.objects.count(), 0)
            self.assertEqual(self.request("confirm", direction="在無名港繼續尋找失落的鐘聲。").result["outcome"], "success")
            self.assertTrue(service.dream_state(self.actor)["confirmed"])
            self.assertEqual(CreativeRequest.objects.count(), 1)
            self.assertEqual(self.request("awaken").result["outcome"], "success")
        self.assertEqual(self.physical(), physical)
        self.assertIn("醒了", service.dream_state(self.actor)["ending"])

    @covers_requirement(
        "dream-session-lifecycle::only-completed-exchanges-consume-the-six-exchange-budget",
        "dream-session-lifecycle::convergence-and-exit-require-explicit-choices",
        "dream-sleep-surface::public-dream-surface-includes-the-approved-presentation-and-deterministic-escape",
    )
    def test_cap_six_text_browser_choices_remain_offline(self):
        self.enter()
        physical = self.physical()
        for index in range(6):
            state = service.dream_state(self.actor)
            payload = validate("say", {"session_id": state["session_id"], "revision": state["revision"], "message_parts": ["在無名港尋找失落的鐘聲。"]})
            with patch("world.ai.client.OpenAICompatClient", return_value=self.delivered(index)):
                result = adapter("say", self.actor, payload)
                self.assertEqual(result.result["outcome"], "success")
        state = service.dream_state(self.actor)
        self.assertEqual(state["remaining"], 0)
        self.assertFalse(state["can_input"])
        self.assertTrue(state["can_confirm"] and state["can_draft"] and state["can_awaken"])
        # The sixth settled exchange finalized the session in the same save, so
        # the published stage offers editing and confirmation, never a choice.
        self.assertEqual(state["stage"], lifecycle.STAGE_FINALIZED)
        self.assertTrue(state["can_edit"] and state["drafted"])
        self.assertFalse(state["can_finalize"] or state["can_choose_thread"])
        self.assertNotIn("dream say", render_state(state))
        refused = self.request("say", message="第七次", client=self.delivered()).result
        self.assertEqual(refused["outcome"], "rejected")
        # The sixth exchange closed the conversation: the stage, not only the
        # count, refuses the message.
        self.assertEqual(refused["code"], "dream_finalized")
        self.assertEqual(self.request("draft").result["outcome"], "success")
        self.assertEqual(self.request("awaken").result["outcome"], "success")
        self.assertEqual(self.physical(), physical)
        self.assertTrue(service.dream_state(self.actor)["ending_phase"])

    @covers_requirement(
        "dream-session-lifecycle::failures-preserve-progress-and-permit-offline-awakening",
        "dream-sleep-surface::dream-departure-never-settles-sleep-again",
    )
    @covers_requirement(
        "dream-sleep-surface::confirmed-dream-handoff-returns-to-playable-waking-surfaces"
    )
    def test_model_failure_draft_and_awaken_preserve_committed_sleep(self):
        self.enter(tick_from=90, tick_to=100, requested_seconds=10)
        physical = self.physical()
        client = FakeLLMClient()
        client.add_connection_error(lambda descriptor: True)
        self.assertEqual(self.request("say", message="保留鐘聲方向", client=client).result["outcome"], "rejected")
        self.assertGreaterEqual(len(client.calls), 1)
        self.assertTrue(service.dream_state(self.actor)["failure"])
        self.assertEqual(service.dream_state(self.actor)["remaining"], 6)
        with patch("world.ai.client.OpenAICompatClient", side_effect=AssertionError("offline escape")):
            self.request("draft")
            self.request("awaken")
        self.assertEqual(physical, self.physical())
        self.assertEqual(service.dream_state(self.actor)["sleep"]["seconds"], 10)

    @covers_requirement(
        "dream-sleep-surface::confirmed-dream-handoff-returns-to-playable-waking-surfaces"
    )
    def test_a_departure_result_always_republishes_the_dream_panel(self):
        """The client learns the dream ended even with no continuation to run."""
        self.enter()
        result = self.request("awaken").result
        self.assertEqual(result["outcome"], "success")
        # The retained-sleep settlement publishes only when it is authorized
        # for this receipt; the departure's own result is what must name the
        # surface it changed, or a client keeps showing an open dream forever.
        self.assertEqual(tuple(result["affected_panels"]), ("dream",))

    @covers_requirement('observability-logging::llm-and-narrative-diagnostic-correlation')
    def test_generation_failure_event_names_the_actual_call_and_player_input(self):
        self.enter(tick_from=90, tick_to=100, requested_seconds=10)
        unscripted = FakeLLMClient()  # no fixture: an unexpected error escapes the guardrail
        with patch("server.dream_service.log_warn") as warn, \
                patch.object(guardrail, "log_info") as info:
            result = self.request("say", message="合成的夢中提問", client=unscripted).result
        self.assertEqual(result["outcome"], "rejected")
        failed = [c.kwargs["context"] for c in warn.call_args_list
                  if c.args[0] == "dream_surface_generation_failed"]
        calls = [c.kwargs["context"] for c in info.call_args_list if c.args[0] == "llm_call"]
        self.assertEqual(failed[0]["input"], "合成的夢中提問")
        self.assertEqual(failed[0]["call_id"], calls[0]["call_id"])

    @covers_requirement("dream-sleep-surface::dream-departure-never-settles-sleep-again")
    def test_reconnect_progress_and_new_sleep_association_authority(self):
        first = self.enter()
        self.request("say", message="鐘聲", client=self.delivered())
        lifecycle.open_session(str(self.actor.pk), tick=101)
        # A newer unrelated open row must not steal this association.
        reloaded = self.actor.__class__.objects.get(pk=self.actor.pk)
        self.assertEqual(service.dream_state(reloaded)["session_id"], first["session_id"])
        self.assertEqual(service.dream_state(reloaded)["completed"], 1)
        later = self.enter(tick_from=100, tick_to=111, requested_seconds=11)
        self.assertEqual(later["session_id"], first["session_id"])
        self.assertEqual(later["completed"], 1)
        self.assertEqual(later["sleep"]["tick_to"], 111)
        self.request("draft")
        self.request("awaken")
        resumed = self.enter(tick_from=111, tick_to=119, requested_seconds=8)
        self.assertEqual(resumed["session_id"], first["session_id"])
        self.assertEqual(resumed["completed"], 1)
        self.assertEqual(resumed["sleep"]["seconds"], 8)

    def test_forged_owner_stale_revision_and_control_rejected(self):
        state = self.enter()
        for actor, revision, session in ((self.other, state["revision"], None),
                (self.actor, state["revision"] - 1, None),
                (self.actor, state["revision"], SimpleNamespace(puppet=self.other))):
            result = service.act(actor, "awaken", session_id=state["session_id"], revision=revision, session=session).result
            self.assertEqual(result["outcome"], "rejected")
        self.assertTrue(service.dream_state(self.actor)["open"])
        for payload in ({"session_id": state["session_id"], "revision": True},
                        {"session_id": state["session_id"], "revision": 1, "owner": self.actor.pk}):
            with self.assertRaises(ValueError):
                validate("awaken", payload)

    def test_pending_escape_draft_then_late_delivery_and_control_change(self):
        for departure in (False, True):
            base = self.enter()["completed"]
            pending = Deferred()
            session = SimpleNamespace(puppet=self.actor)
            self.live_sessions = [session]
            with patch("world.ai.dream.generate_dream_exchange", return_value=pending), patch("server.dream_service._refresh"):
                state = service.dream_state(self.actor)
                result = adapter("say", self.actor, {"session_id": state["session_id"], "revision": state["revision"], "message": "鐘聲"}, session)
                self.assertEqual(result["code"], "dream_pending")
                self.assertTrue(service.dream_state(self.actor)["pending"])
                self.request("draft")
                if departure:
                    self.request("awaken")
                response = dream.DreamExchange("合成場景", "合成方向", prospective_state(base).level, base + 1, "exchange")
                pending.callback(response)
                self.assertEqual(service.dream_state(self.actor)["completed"], base if departure else base + 1)
                if not departure:
                    self.request("awaken")
        base = self.enter()["completed"]
        pending = Deferred()
        with patch("world.ai.dream.generate_dream_exchange", return_value=pending), patch("server.dream_service._refresh"):
            session = SimpleNamespace(puppet=self.actor)
            self.live_sessions = [session]
            result = self.request("say", message="鐘聲", session=session, client=self.delivered())
            session.puppet = self.other
            pending.callback(dream.DreamExchange("合成場景", "合成方向", prospective_state(0).level, 1, "exchange"))
            self.assertEqual(result.result["outcome"], "rejected")
        self.assertEqual(service.dream_state(self.actor)["completed"], base)
        self.assertFalse(service.dream_state(self.actor)["pending"])

    def test_thread_direction_preferences_and_concrete_invalid_draft(self):
        self.enter()
        thread = create_thread(thread_id="synthetic-thread", origin="synthetic-origin", participants=[str(self.actor.pk)])
        create_thread(thread_id="synthetic-private-thread", origin="synthetic-other-origin", participants=[str(self.other.pk)])
        state = service.dream_state(self.actor)
        self.assertIn({"id": thread.thread_id, "label": "未命名的故事線"}, state["thread_choices"])
        self.assertNotIn("synthetic-private-thread", [choice["id"] for choice in state["thread_choices"]])
        # The choice is open only while conversing; the direction the player
        # writes afterwards may only keep it.
        self.assertEqual(
            self.request("choose_thread", thread_id=thread.thread_id).result["outcome"],
            "success",
        )
        self.assertEqual(self.request("finalize").result["outcome"], "success")
        direction = {"kind": "thread_direction", "thread_id": thread.thread_id,
                     "summary": "沿著已知故事尋找鐘聲。", "themes": ["鐘聲"],
                     "atmosphere": ["安靜"], "emphasis": ["探索"], "exclusions": ["暴力"]}
        command = CmdDream()
        command.caller = self.actor
        command.session = None
        command.args = "draft " + json.dumps(direction, ensure_ascii=False)
        self.assertEqual(command.func().result["outcome"], "success")
        old_revision = service.dream_state(self.actor)["revision"]
        command.args = "draft " + json.dumps({**direction, "summary": "改變後的方向"}, ensure_ascii=False)
        command.func()
        self.assertGreater(service.dream_state(self.actor)["revision"], old_revision)
        resolve_thread(thread_id=thread.thread_id, tick=100, actor_id=str(self.actor.pk))
        result = self.request("confirm").result
        self.assertEqual(result["code"], "invalid_direction")
        self.assertTrue(result["message"])
        self.assertEqual(CreativeRequest.objects.count(), 0)
        self.assertTrue(service.dream_state(self.actor)["open"])
        session = surface.associated_session(self.actor)
        self.assertIsNone(get_draft(session.draft_id, str(self.actor.pk)).confirmed_revision)
        payload = validate("confirm", {"session_id": session.session_id,
            "revision": service.dream_state(self.actor)["revision"],
            "direction": {**direction, "kind": "new_story", "thread_id": None}})
        self.assertEqual(adapter("confirm", self.actor, payload).result["outcome"], "success")
        self.assertTrue(service.dream_state(self.actor)["confirmed"])
        self.assertEqual(CreativeRequest.objects.count(), 1)

    def test_disconnect_with_unchanged_puppet_drops_late_response(self):
        self.enter()
        pending = Deferred()
        session = SimpleNamespace(puppet=self.actor)
        self.live_sessions = [session]
        with patch("world.ai.dream.generate_dream_exchange", return_value=pending), patch("server.dream_service._refresh"):
            result = self.request("say", message="鐘聲", session=session, client=self.delivered())
            self.live_sessions = []
            pending.callback(dream.DreamExchange("合成場景", "合成方向", prospective_state(0).level, 1, "exchange"))
        self.assertEqual(result.result["outcome"], "rejected")
        self.assertEqual(service.dream_state(self.actor)["completed"], 0)
        self.assertFalse(service.dream_state(self.actor)["pending"])

    def test_text_command_calls_shared_lifecycle_and_logs_no_prose(self):
        self.enter()
        self.assertEqual(self.request("finalize").result["outcome"], "success")
        command = CmdDream()
        command.caller = self.actor
        command.session = None
        command.args = "draft 合成秘密方向"
        with patch("server.dream_service.log_info") as info:
            self.assertEqual(command.func().result["outcome"], "success")
        self.assertNotIn("合成秘密方向", str(info.call_args_list))
        command.args = "awaken"
        self.assertEqual(command.func().result["outcome"], "success")

    def test_saved_structured_draft_survives_chat_and_bare_confirmation(self):
        self.enter()
        thread = create_thread(thread_id="synthetic-retained-thread", origin="synthetic-origin", participants=[str(self.actor.pk)])
        direction = {"kind": "thread_direction", "thread_id": thread.thread_id,
                     "summary": "在既有故事中尋找鐘聲。", "themes": ["鐘聲"],
                     "exclusions": ["暴力"]}
        self.assertEqual(
            self.request("choose_thread", thread_id=thread.thread_id).result["outcome"],
            "success",
        )
        self.assertEqual(self.request("say", message="我還想繼續討論。", client=self.delivered()).result["outcome"], "success")
        self.assertEqual(self.request("finalize").result["outcome"], "success")
        self.assertEqual(self.request("draft", direction=direction).result["outcome"], "success")
        state = service.dream_state(self.actor)
        self.assertEqual(state["proposal"]["summary"], direction["summary"])
        self.assertEqual(state["thread_id"], thread.thread_id)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.request("confirm").result["outcome"], "success")
        stored = CreativeRequest.objects.get()
        self.assertEqual(stored.direction["kind"], "thread_direction")
        self.assertEqual(stored.direction["thread_id"], thread.thread_id)
        self.assertEqual(stored.direction["summary"], direction["summary"])
        self.assertEqual(stored.direction["exclusions"], ["暴力"])
        with patch("world.narrative.dream_surface.StoryThread.objects.exclude") as query:
            self.assertEqual(service.dream_state(self.actor)["thread_choices"], [])
            query.assert_not_called()

    def test_blank_confirmation_concrete_input_refusals_and_single_text_ending(self):
        self.enter()
        # A confirmation before the conversation stops is refused with a
        # reason, and it writes nothing at all.
        self.assertEqual(self.request("confirm").result["code"], "not_finalized")
        self.assertFalse(surface.associated_session(self.actor).draft_id)
        client = self.delivered()
        self.assertEqual(self.request("say", message="", client=client).result["code"], "empty_input")
        self.assertEqual(self.request("say", message="界" * 4001, client=client).result["code"], "oversized_input")
        self.assertEqual(client.calls, [])
        # The finalize saves the (still empty) working proposal; the
        # confirmation keeps refusing to freeze a wish with no content.
        self.assertEqual(self.request("finalize").result["outcome"], "success")
        self.assertEqual(self.request("confirm").result["code"], "empty_direction")
        self.assertFalse(CreativeRequest.objects.exists())
        command = CmdDream()
        command.caller = self.actor
        command.session = None
        command.args = "awaken"
        self.actor.msg.reset_mock()
        self.assertEqual(command.func().result["outcome"], "success")
        ending = service.dream_state(self.actor)["ending"]
        self.assertEqual([call.args[0] for call in self.actor.msg.call_args_list].count(ending), 1)

    @covers_requirement(
        "dream-explicit-presentation::dream-collaboration-uses-the-approved-explicit-frame",
    )
    def test_scene_art_is_the_canonical_descriptor_of_the_dream_chain(self):
        # The stage's artwork is the SAME canonical descriptor every scene
        # surface carries: the dream's own logical subject identity (scoped to
        # this owner and this sleep session), the REQUIRED bundled dream
        # illustration and the distinct declared town terminal, with no claimed
        # generation and no retention authorization at all.
        # The bundled collection's snapshot is process-global, so this test
        # states both halves explicitly: unloaded first, then the committed
        # collection the startup step admits.
        reset_bundled_scenes()
        self.addCleanup(reset_bundled_scenes)
        state = self.enter()
        artwork = service.dream_state(self.actor)["scene_art"]
        self.assertEqual(artwork["subject_id"], f"dream:{self.actor.pk}:{state['session_id']}")
        self.assertIsNone(artwork["generation_subject"])
        self.assertIsNone(artwork["generation_state"])
        self.assertEqual(artwork["retention_sources"], [])
        self.assertEqual(
            [(entry["type"], entry["source_id"], entry["rank"]) for entry in artwork["attempts"]],
            [
                ("fault", "scene.bundled:dream_throne", 40),
                ("fault", "scene.terminal:city_street", 100),
            ],
        )
        # Both required images state their missing resource while the bundled
        # collection is unloaded: the fact is stated, never an invented image.
        self.assertEqual(
            [entry["reason"] for entry in artwork["attempts"]],
            [descriptors.REASON_REQUIRED_RESOURCE_MISSING] * 2,
        )
        self.assertIsNone(artwork["terminal"])

        # With the committed collection admitted, the stage's own two images are
        # real same-origin bundled resources and the terminal is distinct.
        load_bundled_scene_catalog()
        self.addCleanup(reset_bundled_scenes)
        artwork = service.dream_state(self.actor)["scene_art"]
        self.assertEqual(
            [(entry["type"], entry["source_id"], entry["rank"]) for entry in artwork["attempts"]],
            [("image", "scene.bundled:dream_throne", 40)],
        )
        bundled = artwork["attempts"][0]["resource"]
        self.assertEqual(bundled["origin"], "bundled_official")
        self.assertTrue(bundled["url"].startswith("/art/bundled-scene/dream_throne/"))
        self.assertEqual(artwork["terminal"]["kind"], "scene_image")
        self.assertEqual(artwork["terminal"]["source_id"], "scene.terminal:city_street")
        self.assertTrue(artwork["terminal"]["resource"]["url"].startswith("/art/bundled-scene/city_street/"))
        # The resolution is a pure read: resolving again states the same facts.
        self.assertEqual(service.dream_state(self.actor)["scene_art"], artwork)

    @covers_requirement(
        "dream-explicit-presentation::dream-collaboration-uses-the-approved-explicit-frame",
    )
    def test_scene_art_preferred_position_states_absence_rejection_and_configured_fault(self):
        # The preferred position is the OPTIONAL operator identity. Plain
        # absence is the normal no-art configuration and contributes NOTHING —
        # an undeclared image never becomes a reached failure — while an image
        # of that name refused at admission and a root the load could not use
        # are faults at exactly that position.
        from world.art import scene_definitions

        self.enter()
        identity = scene_definitions.DREAM_PREFERRED_OFFICIAL_IDENTITY

        def artwork():
            return service.dream_state(self.actor)["scene_art"]

        def preferred(descriptor):
            return [
                entry for entry in descriptor["attempts"]
                if entry["rank"] == descriptors.SCENE_RANK_OPERATOR
            ]

        # (1) No official snapshot at all: absence, and nothing else.
        self.assertEqual(preferred(artwork()), [])
        self.assertEqual(descriptors.SCENE_RANK_OPERATOR, 30)

        image = official_art.OfficialImage(
            identity=identity, kind="npc", key=scene_definitions.DREAM_PREFERRED_OFFICIAL_KEY,
            fingerprint="a" * 64, image_size={"width": 2880, "height": 1600},
            face_rect={}, stage={},
        )
        contents = {
            (image.kind, image.key): official_art.OfficialContent(
                kind=image.kind, key=image.key, default_identity=identity, images=(identity,)
            )
        }
        # (2) The identity is admitted: one official candidate at the preferred
        # position, ahead of the required bundled dream.
        with patch.object(official_art, "_CATALOG", official_art.OfficialCatalog(contents, {identity: image})):
            descriptor = artwork()
        positions = preferred(descriptor)
        self.assertEqual([(entry["type"], entry["source_id"]) for entry in positions],
                         [("image", "scene.operator:dream_throne")])
        self.assertEqual(positions[0]["resource"]["url"], f"/art/official/{'a' * 64}/{identity}")
        self.assertEqual(positions[0]["resource"]["origin"], "official")
        self.assertLessEqual(len(positions[0]["resource"]["url"]), 256)

        # (3) A file of that name was present but refused at admission: the
        # reached fact is attributed to that exact image, before the substitute.
        with patch.object(
            official_art, "_CATALOG",
            official_art.OfficialCatalog(
                {}, {}, refusals={identity: "image_undecodable"}
            ),
        ):
            positions = preferred(artwork())
        self.assertEqual(
            [(entry["type"], entry["source_id"], entry["reason"]) for entry in positions],
            [("fault", f"scene.operator:{identity}", descriptors.REASON_SOURCE_REJECTED)],
        )

        # (4) The directory itself could not be enumerated: a root I/O fact at
        # the preferred layer.
        with patch.object(
            official_art, "_CATALOG",
            official_art.OfficialCatalog(
                {},
                {},
                source_faults={
                    ("npc", scene_definitions.DREAM_PREFERRED_OFFICIAL_KEY): (
                        official_art.SourceFault(
                            official_art.SOURCE_SCOPE_SOURCE,
                            f"npc/{scene_definitions.DREAM_PREFERRED_OFFICIAL_KEY}",
                            official_art.SOURCE_REASON_UNAVAILABLE,
                        ),
                    )
                },
            ),
        ):
            positions = preferred(artwork())
        self.assertEqual(
            [(entry["type"], entry["source_id"], entry["reason"]) for entry in positions],
            [("fault", "scene.operator:dream_throne", descriptors.REASON_SOURCE_UNAVAILABLE)],
        )

        # (5) The configured root could not be used at all: the same availability
        # fact, independent of any per-directory walk.
        with patch.object(
            official_art, "_CATALOG",
            official_art.OfficialCatalog(
                {},
                {},
                official_art.RootHealth(
                    official_art.ROOT_STATE_UNAVAILABLE, True, True, "official_root_absent"
                ),
            ),
        ):
            positions = preferred(artwork())
        self.assertEqual(
            [(entry["type"], entry["source_id"], entry["reason"]) for entry in positions],
            [("fault", "scene.operator:dream_throne", descriptors.REASON_SOURCE_UNAVAILABLE)],
        )
        # ...and a directory's own manifest-declared default is never consulted:
        # it describes another image's selection, not this identity's.
        with patch.object(
            official_art, "_CATALOG",
            official_art.OfficialCatalog(
                {},
                {},
                source_faults={
                    ("npc", scene_definitions.DREAM_PREFERRED_OFFICIAL_KEY): (
                        official_art.SourceFault(
                            official_art.SOURCE_SCOPE_DEFAULT,
                            f"npc/{scene_definitions.DREAM_PREFERRED_OFFICIAL_KEY}/other.png",
                            official_art.SOURCE_REASON_REFERENCE_MISSING,
                        ),
                    )
                },
            ),
        ):
            self.assertEqual(preferred(artwork()), [])

    @covers_requirement(
        "dream-explicit-presentation::dream-collaboration-uses-the-approved-explicit-frame",
    )
    def test_dream_scene_identity_stays_catalog_admissible(self):
        # The stage artwork is resolved out of the official catalog and served
        # by the media route, so the identity must keep parsing as
        # <kind>/<key>/<file> with an admitted kind, a stable subject key, and a
        # stored extension — and the shipped admission path must actually index
        # it out of a real root. That functional half is the tripwire that
        # matters: admission is silent (a refused identity leaves the stage with
        # no artwork and no failing request anywhere), and the deferred authored
        # npc/profile provenance adds a membership check this key — deliberately
        # not an authored npc/profile — would not satisfy.
        from world.art import scene_definitions

        identity = scene_definitions.DREAM_PREFERRED_OFFICIAL_IDENTITY
        parts = identity.split("/")
        self.assertEqual(len(parts), 3)
        kind, key, filename = parts
        self.assertEqual(kind, scene_definitions.DREAM_PREFERRED_OFFICIAL_KIND)
        self.assertEqual(key, scene_definitions.DREAM_PREFERRED_OFFICIAL_KEY)
        self.assertIn(kind, official_art.OFFICIAL_CONTENT_KINDS)
        self.assertTrue(subjects.is_valid_subject_key(key))
        self.assertIn(Path(filename).suffix, formats.STORE_EXTENSIONS)
        self.enter()
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / identity
            target.parent.mkdir(parents=True)
            target.write_bytes(_synthetic_webp())
            with override_settings(ART_OFFICIAL_ROOT=root):
                official_art.reset_catalog()
                try:
                    official_art.load_catalog()
                    artwork = service.dream_state(self.actor)["scene_art"]
                    preferred = [
                        entry for entry in artwork["attempts"]
                        if entry["rank"] == descriptors.SCENE_RANK_OPERATOR
                    ]
                    self.assertEqual(len(preferred), 1)
                    self.assertTrue(preferred[0]["resource"]["url"].startswith("/art/official/"))
                    self.assertTrue(preferred[0]["resource"]["url"].endswith(identity))
                finally:
                    official_art.reset_catalog()

    @covers_requirement(
        "dream-explicit-presentation::dream-collaboration-uses-the-approved-explicit-frame",
    )
    def test_dream_art_never_inherits_the_sleeper_location_or_writes_anything(self):
        # The dream's descriptor owns its own chain: it never reads the
        # sleeper's location metadata (so no physical room background is
        # inherited and no generation job is enqueued for the sleeper's room),
        # and resolving it leaves the session, the authoring store, the art
        # records and the queue exactly as they were.
        from world.art.store import ArtAssetRecord

        self.enter()
        session = surface.associated_session(self.actor)
        def art_records():
            # Any enqueue (the one thing that could inherit the sleeper's room)
            # creates one of these records, so the exact key/status set is the
            # authoritative no-job evidence.
            return sorted(
                (record.db_key, str(record.db.status))
                for record in ArtAssetRecord.objects.all()
            )

        before = (
            art_records(),
            session.revision,
            session.draft_id,
            deepcopy(self.actor.db.dream_surface),
        )
        first = service.dream_state(self.actor)["scene_art"]
        second = service.dream_state(self.actor)["scene_art"]
        self.assertEqual(first, second)
        self.assertFalse(
            [
                entry["source_id"]
                for entry in first["attempts"]
                if entry["source_id"].startswith(("scene.room:", "scene.generated:"))
            ],
            "the dream must not inherit the sleeper's physical scene positions",
        )
        session = surface.associated_session(self.actor)
        self.assertEqual(
            (
                art_records(),
                session.revision,
                session.draft_id,
                self.actor.db.dream_surface,
            ),
            before,
        )


    @covers_requirement(
        "dream-authoring::confirmation-freezes-visible-bounded-experience-requirements",
        "webclient-dream-stage::dream-confirmation-displays-the-frozen-experience-requirements",
    )
    def test_collaborator_requirements_reach_the_surface_and_the_text_line(self):
        # The collaborator's bounded proposal is readable on both surfaces
        # before anything is frozen, and the text transport names it too.
        self.enter()
        payload = {
            "scene": "合成場景：雲海王座之前，親密的身影與漫過腳踝的積水一同隨呼吸起伏。",
            "dialogue": "我們繼續商談尋找鐘聲的故事方向。",
            "phase": prospective_state(0).level,
            "edits": [
                {
                    "command": "create",
                    "path": "requirements",
                    "file_text": (
                        "place: 南門\n"
                        "new_character: 一個女孩\n"
                        "private_commission: 帶她找媽媽"
                    ),
                }
            ],
        }
        client = FakeLLMClient()
        client.add_response(
            lambda descriptor: True, json.dumps(payload, ensure_ascii=False)
        )
        result = self.request("say", message="鐘聲", client=client)
        self.assertEqual(result.result["outcome"], "success")
        state = service.dream_state(self.actor)
        self.assertEqual(
            [row["text"] for row in state["proposal"]["requirements"]],
            ["南門", "一個女孩", "帶她找媽媽"],
        )
        rendered = render_state(state)
        self.assertIn("南門", rendered)
        self.assertIn("帶她找媽媽", rendered)
        # The rows are rendered from the working wish itself, so the text line
        # carries no review-version marker at all.
        self.assertNotIn("尚未檢視", rendered)
        self.assertNotIn("已檢視的版本", rendered)

    @covers_requirement(
        "webclient-dream-stage::dream-confirmation-displays-the-frozen-experience-requirements"
    )
    def test_the_published_version_is_what_a_bare_confirmation_confirms(self):
        self.enter()
        direction = {
            "kind": "new_story",
            "thread_id": None,
            "summary": "在南門遇見一個女孩。",
            "requirements": [{"kind": "place", "text": "南門"}],
        }
        self.assertEqual(self.request("finalize").result["outcome"], "success")
        self.assertEqual(
            self.request("draft", direction=dict(direction)).result["outcome"],
            "success",
        )
        state = service.dream_state(self.actor)
        # The rows are published once, inside the working proposal; the panel
        # carries no separate row copy and no version identity (schema 5).
        for retired in ("direction_parts", "draft_preferences", "requirements", "requirement_version"):
            self.assertNotIn(retired, state)
        self.assertEqual(state["proposal"]["requirements"], direction["requirements"])
        shown = AuthoringDraft.objects.get().direction["requirement_version"]
        self.assertTrue(shown)
        rendered = render_state(state)
        self.assertIn("南門", rendered)
        # The identity stays on the published state: the text surface renders
        # the rows, and the confirmation carries the version, not the prose.
        self.assertNotIn(shown, rendered)
        # The argument-less confirmation confirms the version the state names.
        with self.captureOnCommitCallbacks(execute=True):
            confirmed = self.request("confirm")
        self.assertEqual(confirmed.result["outcome"], "success")
        self.assertEqual(
            CreativeRequest.objects.get().direction["requirement_version"], shown
        )

    def test_a_failed_confirmation_rolls_back_work_and_compensates_the_surface(self):
        # The delta's own failure scenario: the work record fails inside the
        # confirmation transaction, so the request, the work, the session
        # closure and the surface write must all roll back together, and the
        # in-process Attribute cache must not keep serving the aborted value.
        from world.narrative.authoring import AuthoringError
        from world.narrative.models import DreamDispatch

        self.enter()
        self.assertEqual(self.request("finalize").result["outcome"], "success")
        before = surface.association(self.actor)

        def explode(*args, **kwargs):
            surface.choose_thread(self.actor, "synthetic-exploded-thread")
            raise AuthoringError("synthetic work failure")

        with patch.object(service.lifecycle, "confirm_session", side_effect=explode):
            result = self.request(
                "confirm", direction={"kind": "new_story", "summary": "合成方向"}
            )
        self.assertEqual(result.result["code"], "dream_refused")
        self.assertFalse(CreativeRequest.objects.exists())
        self.assertFalse(DreamDispatch.objects.exists())
        self.assertTrue(service.dream_state(self.actor)["open"])
        self.assertEqual(surface.association(self.actor), before)

    @covers_requirement("dream-authoring::explicit-version-confirmation-submits-once")
    @covers_requirement(
        "dream-authoring::confirmation-freezes-visible-bounded-experience-requirements",
        "webclient-dream-stage::dream-confirmation-displays-the-frozen-experience-requirements",
    )
    @covers_requirement(
        "dream-session-lifecycle::valid-confirmation-closes-the-session-without-awaiting-dispatch",
        "dream-sleep-surface::confirmed-dream-handoff-returns-to-playable-waking-surfaces",
    )
    def test_an_edited_proposal_confirms_what_was_submitted(self):
        # The finalized stage is the player's own hand: an edited summary and
        # edited requirement rows are saved as the shown version and confirmed
        # as exactly that version, in one submit and with no model call.
        self.enter()
        requirements = [
            {"kind": "place", "text": "南門"},
            {"kind": "new_character", "text": "一個女孩"},
            {"kind": "private_commission", "text": "帶她找媽媽"},
        ]
        self.assertEqual(self.request("finalize").result["outcome"], "success")
        submitted = {
            "kind": "new_story",
            "thread_id": None,
            "summary": "改寫後的念頭：在南門等一個女孩，帶她找媽媽。",
            "requirements": requirements,
            "themes": ["重逢"],
        }
        self.assertEqual(
            self.request("draft", direction=dict(submitted)).result["outcome"],
            "success",
        )
        state = service.dream_state(self.actor)
        shown = AuthoringDraft.objects.get().direction["requirement_version"]
        self.assertTrue(shown)
        # The submitted form is the working proposal and the shown version.
        wish = surface.wish_state(self.actor)
        self.assertEqual(wish["proposal"]["summary"], submitted["summary"])
        self.assertEqual(wish["proposal"]["requirements"], requirements)
        self.assertIsNone(wish["changes"])
        self.assertEqual(state["proposal"]["requirements"], requirements)
        with self.captureOnCommitCallbacks(execute=True):
            confirmed = self.request("confirm")
        self.assertEqual(confirmed.result["outcome"], "success")
        # The receipt is truthful: it reports preparation, never an arrangement
        # or an existing encounter, and it travels as ordinary output.
        receipts = [call.args[0] for call in self.actor.msg.call_args_list]
        self.assertTrue(any("正在準備中" in line for line in receipts), receipts)
        self.assertFalse(any("已有可執行的安排" in line for line in receipts), receipts)
        stored = CreativeRequest.objects.get()
        self.assertEqual(stored.direction["summary"], submitted["summary"])
        self.assertEqual(stored.direction["requirements"], requirements)
        self.assertEqual(stored.direction["requirement_version"], shown)

    def test_a_malformed_requirement_set_never_reaches_a_draft_or_the_panel(self):
        # The panel state is strict on both sides: rows the validator would
        # refuse must never be persisted, or the published payload could not be
        # rendered by any client at all. A submitted form reaches the applier
        # first, so its refusal is the finalized stage's own reason.
        self.enter()
        self.assertEqual(self.request("finalize").result["outcome"], "success")
        # The finalize saved the still-empty working proposal: that is the one
        # draft this dream has, and no malformed row may enter it.
        self.assertEqual(AuthoringDraft.objects.count(), 1)
        for rows in (
            [{"kind": "explode", "text": "南門"}],
            [{"kind": "place", "text": "南門", "extra": "x"}],
            [{"kind": "place", "text": ""}],
        ):
            with self.subTest(rows=rows):
                refused = self.request(
                    "draft",
                    direction={
                        "kind": "new_story",
                        "summary": "在南門遇見一個女孩。",
                        "requirements": rows,
                    },
                )
                self.assertEqual(refused.result["code"], "invalid_direction")
                self.assertEqual(
                    refused.result["message"], "願望的內容不完整或超出限制。"
                )
        self.assertEqual(AuthoringDraft.objects.count(), 1)
        self.assertEqual(AuthoringDraft.objects.get().direction["requirements"], [])
        state = service.dream_state(self.actor)
        self.assertEqual(state["proposal"]["requirements"], [])

    @covers_requirement(
        "dream-session-lifecycle::the-session-keeps-a-working-proposal-that-only-settled-exchanges-change"
    )
    def test_a_player_message_never_becomes_the_proposal(self):
        self.enter()
        client = self.delivered()
        self.assertEqual(
            self.request("say", message="合成的秘密鐘聲", client=client).result["outcome"],
            "success",
        )
        wish = surface.wish_state(self.actor)
        self.assertEqual(wish["proposal"], dream_proposal.empty_proposal())
        self.assertNotIn(
            "合成的秘密鐘聲", json.dumps(wish["proposal"], ensure_ascii=False)
        )
        self.assertIsNone(wish["changes"]["summary"])
        self.assertEqual(wish["changes"]["lists"]["themes"], {"added": [], "removed": []})

    @covers_requirement(
        "dream-session-lifecycle::the-session-keeps-a-working-proposal-that-only-settled-exchanges-change"
    )
    def test_edits_accumulate_across_exchanges(self):
        self.enter()
        first = self.exchange([
            {"command": "create", "path": "summary", "file_text": "在無名港尋找鐘聲。"},
        ])
        self.assertEqual(
            self.request("say", message="先寫下開頭", client=first).result["outcome"],
            "success",
        )
        self.assertEqual(
            surface.wish_state(self.actor)["proposal"]["summary"], "在無名港尋找鐘聲。"
        )
        second = self.exchange([
            {"command": "str_replace", "path": "summary",
             "old_str": "鐘聲", "new_str": "失落的鐘聲"},
        ], index=1)
        self.assertEqual(
            self.request("say", message="再補一段", client=second).result["outcome"],
            "success",
        )
        self.assertEqual(
            self.request_payload(second)["wish"]["summary"],
            [{"line": 1, "text": "在無名港尋找鐘聲。"}],
        )
        self.assertEqual(
            surface.wish_state(self.actor)["proposal"]["summary"],
            "在無名港尋找失落的鐘聲。",
        )

    @covers_requirement(
        "dream-session-lifecycle::the-session-keeps-a-working-proposal-that-only-settled-exchanges-change"
    )
    def test_the_change_report_follows_the_last_settled_exchange(self):
        self.enter()
        first = self.exchange([
            {"command": "create", "path": "themes", "file_text": "鐘聲"},
        ])
        self.assertEqual(
            self.request("say", message="加入主題", client=first).result["outcome"],
            "success",
        )
        self.assertEqual(
            surface.wish_state(self.actor)["changes"]["lists"]["themes"]["added"],
            ["鐘聲"],
        )
        self.assertEqual(
            self.request("say", message="不再改動", client=self.delivered(index=1)).result["outcome"],
            "success",
        )
        changes = surface.wish_state(self.actor)["changes"]
        self.assertIsNone(changes["summary"])
        self.assertEqual(changes["lists"]["themes"], {"added": [], "removed": []})

    @covers_requirement(
        "dream-session-lifecycle::the-session-keeps-a-working-proposal-that-only-settled-exchanges-change"
    )
    def test_failed_generation_leaves_the_proposal_and_report_unchanged(self):
        self.enter()
        first = self.exchange([
            {"command": "create", "path": "summary", "file_text": "在無名港尋找鐘聲。"},
        ])
        self.assertEqual(
            self.request("say", message="先寫下開頭", client=first).result["outcome"],
            "success",
        )
        before = surface.wish_state(self.actor)
        failed = FakeLLMClient()
        failed.add_connection_error(lambda descriptor: True)
        result = self.request("say", message="鐘聲", client=failed).result
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["code"], "dream_unavailable")
        after = surface.wish_state(self.actor)
        self.assertEqual(after["proposal"], before["proposal"])
        self.assertEqual(after["changes"], before["changes"])
        self.assertEqual(surface.associated_session(self.actor).completed_exchanges, 1)

    @covers_requirement(
        "dream-session-lifecycle::the-session-keeps-a-working-proposal-that-only-settled-exchanges-change"
    )
    def test_a_stale_response_applies_no_edits(self):
        self.enter()
        pending = Deferred()
        session = SimpleNamespace(puppet=self.actor)
        self.live_sessions = [session]
        edited = {**dream_proposal.empty_proposal(), "summary": "不該套用的方向"}
        with patch("world.ai.dream.generate_dream_exchange", return_value=pending), \
                patch("server.dream_service._refresh"):
            result = self.request("say", message="鐘聲", session=session, client=self.delivered())
            self.assertEqual(self.request("awaken").result["outcome"], "success")
            pending.callback(dream.DreamExchange(
                "合成場景", "合成對話", prospective_state(0).level, 1, "exchange",
                proposal=edited,
                changes=dream_proposal.diff(dream_proposal.empty_proposal(), edited),
            ))
        self.assertEqual(result.result["outcome"], "rejected")
        self.assertEqual(
            surface.wish_state(self.actor)["proposal"], dream_proposal.empty_proposal()
        )
        self.assertEqual(surface.associated_session(self.actor).completed_exchanges, 0)

    @covers_requirement(
        "dream-session-lifecycle::the-session-keeps-a-working-proposal-that-only-settled-exchanges-change"
    )
    def test_a_draft_saved_without_a_direction_takes_the_working_proposal(self):
        self.enter()
        thread = create_thread(
            thread_id="synthetic-working-thread",
            origin="synthetic-origin",
            participants=[str(self.actor.pk)],
        )
        self.assertEqual(
            self.request("choose_thread", thread_id=thread.thread_id).result["outcome"],
            "success",
        )
        client = self.exchange([
            {"command": "create", "path": "summary", "file_text": "在無名港尋找鐘聲。"},
            {"command": "create", "path": "themes", "file_text": "鐘聲"},
        ])
        self.assertEqual(
            self.request("say", message="鐘聲", client=client).result["outcome"], "success"
        )
        self.assertEqual(self.request("draft").result["outcome"], "success")
        draft = get_draft(
            surface.associated_session(self.actor).draft_id, str(self.actor.pk)
        )
        self.assertEqual(draft.direction["summary"], "在無名港尋找鐘聲。")
        self.assertEqual(draft.direction["themes"], ["鐘聲"])
        self.assertEqual(draft.direction["kind"], "thread_direction")
        self.assertEqual(draft.direction["thread_id"], thread.thread_id)

    @covers_requirement(
        "dream-session-lifecycle::the-session-keeps-a-working-proposal-that-only-settled-exchanges-change"
    )
    def test_awakening_saves_the_working_proposal_when_no_draft_exists(self):
        self.enter()
        client = self.exchange([
            {"command": "create", "path": "summary", "file_text": "在無名港尋找鐘聲。"},
        ])
        self.assertEqual(
            self.request("say", message="鐘聲", client=client).result["outcome"], "success"
        )
        self.assertFalse(surface.associated_session(self.actor).draft_id)
        self.assertEqual(self.request("awaken").result["outcome"], "success")
        draft = get_draft(
            surface.associated_session(self.actor).draft_id, str(self.actor.pk)
        )
        self.assertEqual(draft.direction["summary"], "在無名港尋找鐘聲。")
        self.assertEqual(draft.direction["kind"], "new_story")
        self.assertIsNone(draft.direction["thread_id"])

    @covers_requirement(
        "dream-session-lifecycle::the-session-keeps-a-working-proposal-that-only-settled-exchanges-change"
    )
    def test_resume_restores_the_proposal(self):
        first = self.enter()
        thread = create_thread(
            thread_id="synthetic-resume-thread",
            origin="synthetic-origin",
            participants=[str(self.actor.pk)],
        )
        self.assertEqual(
            self.request("choose_thread", thread_id=thread.thread_id).result["outcome"],
            "success",
        )
        client = self.exchange([
            {"command": "create", "path": "summary", "file_text": "在無名港尋找鐘聲。"},
        ])
        self.assertEqual(
            self.request("say", message="鐘聲", client=client).result["outcome"], "success"
        )
        before = surface.wish_state(self.actor)
        resumed = self.enter(tick_from=100, tick_to=111, requested_seconds=11)
        after = surface.wish_state(self.actor)
        self.assertEqual(resumed["session_id"], first["session_id"])
        self.assertEqual(after["proposal"], before["proposal"])
        self.assertEqual(after["changes"], before["changes"])
        self.assertEqual(after["thread_id"], thread.thread_id)

    @covers_requirement(
        "dream-session-lifecycle::the-session-keeps-a-working-proposal-that-only-settled-exchanges-change"
    )
    def test_resume_seeds_the_proposal_from_the_saved_draft(self):
        self.enter()
        thread = create_thread(
            thread_id="synthetic-seed-thread",
            origin="synthetic-origin",
            participants=[str(self.actor.pk)],
        )
        self.assertEqual(
            self.request("choose_thread", thread_id=thread.thread_id).result["outcome"],
            "success",
        )
        self.assertEqual(
            self.request("say", message="鐘聲", client=self.delivered()).result["outcome"],
            "success",
        )
        self.assertEqual(self.request("finalize").result["outcome"], "success")
        self.assertEqual(
            self.request("draft", direction={
                "kind": "thread_direction", "thread_id": thread.thread_id,
                "summary": "從草稿接續的鐘聲。", "themes": ["鐘聲"],
            }).result["outcome"],
            "success",
        )
        value = surface.association(self.actor)
        value.pop("proposal", None)
        value.pop("thread_locked", None)
        self.actor.db.dream_surface = value
        self.enter(tick_from=100, tick_to=121, requested_seconds=21)
        wish = surface.wish_state(self.actor)
        self.assertEqual(wish["proposal"]["summary"], "從草稿接續的鐘聲。")
        self.assertEqual(wish["proposal"]["themes"], ["鐘聲"])
        self.assertEqual(wish["thread_id"], thread.thread_id)
        self.assertTrue(wish["thread_locked"])

    @covers_requirement(
        "dream-session-lifecycle::thread-choice-precedes-the-first-message-and-then-locks"
    )
    def test_choosing_an_offered_thread_precedes_the_first_message(self):
        self.enter()
        thread = create_thread(
            thread_id="synthetic-choice-thread",
            origin="synthetic-origin",
            participants=[str(self.actor.pk)],
            factual_summary="  選擇的鐘聲線  ",
        )
        revision = service.dream_state(self.actor)["revision"]
        result = self.request("choose_thread", thread_id=thread.thread_id).result
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "dream_choose_thread")
        self.assertEqual(surface.wish_state(self.actor)["thread_id"], thread.thread_id)
        self.assertGreater(service.dream_state(self.actor)["revision"], revision)
        client = self.delivered()
        self.assertEqual(
            self.request("say", message="鐘聲", client=client).result["outcome"], "success"
        )
        self.assertEqual(self.request_payload(client)["thread"], {"label": "選擇的鐘聲線"})

    @covers_requirement(
        "dream-session-lifecycle::thread-choice-precedes-the-first-message-and-then-locks"
    )
    def test_the_default_choice_is_a_new_story(self):
        self.enter()
        client = self.delivered()
        self.assertEqual(
            self.request("say", message="鐘聲", client=client).result["outcome"], "success"
        )
        self.assertIsNone(surface.wish_state(self.actor)["thread_id"])
        self.assertNotIn("thread", self.request_payload(client))

    @covers_requirement(
        "dream-session-lifecycle::thread-choice-precedes-the-first-message-and-then-locks"
    )
    def test_the_choice_locks_after_the_first_accepted_message(self):
        self.enter()
        chosen = create_thread(
            thread_id="synthetic-locked-thread",
            origin="synthetic-origin",
            participants=[str(self.actor.pk)],
        )
        other = create_thread(
            thread_id="synthetic-other-thread",
            origin="synthetic-origin",
            participants=[str(self.actor.pk)],
        )
        self.assertEqual(
            self.request("choose_thread", thread_id=chosen.thread_id).result["outcome"],
            "success",
        )
        self.assertEqual(
            self.request("say", message="鐘聲", client=self.delivered()).result["outcome"],
            "success",
        )
        result = self.request("choose_thread", thread_id=other.thread_id).result
        self.assertEqual(result["code"], "thread_locked")
        self.assertEqual(surface.wish_state(self.actor)["thread_id"], chosen.thread_id)

    @covers_requirement(
        "dream-session-lifecycle::thread-choice-precedes-the-first-message-and-then-locks"
    )
    def test_the_choice_locks_even_when_the_first_generation_fails(self):
        self.enter()
        thread = create_thread(
            thread_id="synthetic-failed-thread",
            origin="synthetic-origin",
            participants=[str(self.actor.pk)],
        )
        failed = FakeLLMClient()
        failed.add_connection_error(lambda descriptor: True)
        self.assertEqual(
            self.request("say", message="鐘聲", client=failed).result["outcome"], "rejected"
        )
        result = self.request("choose_thread", thread_id=thread.thread_id).result
        self.assertEqual(result["code"], "thread_locked")
        self.assertIsNone(surface.wish_state(self.actor)["thread_id"])

    @covers_requirement(
        "dream-session-lifecycle::thread-choice-precedes-the-first-message-and-then-locks"
    )
    def test_an_unoffered_thread_is_refused(self):
        self.enter()
        create_thread(
            thread_id="synthetic-foreign-thread",
            origin="synthetic-origin",
            participants=[str(self.other.pk)],
        )
        ended = create_thread(
            thread_id="synthetic-ended-thread",
            origin="synthetic-origin",
            participants=[str(self.actor.pk)],
        )
        resolve_thread(thread_id=ended.thread_id, tick=100, actor_id=str(self.actor.pk))
        for thread_id in (
            "synthetic-foreign-thread",
            "synthetic-ended-thread",
            "synthetic-absent-thread",
        ):
            with self.subTest(thread_id=thread_id):
                result = self.request("choose_thread", thread_id=thread_id).result
                self.assertEqual(result["outcome"], "rejected")
                self.assertEqual(result["code"], "unknown_thread")
        self.assertIsNone(surface.wish_state(self.actor)["thread_id"])

    @covers_requirement(
        "dream-session-lifecycle::thread-choice-precedes-the-first-message-and-then-locks"
    )
    def test_a_locked_choice_survives_resume(self):
        self.enter()
        thread = create_thread(
            thread_id="synthetic-resumed-lock",
            origin="synthetic-origin",
            participants=[str(self.actor.pk)],
        )
        self.assertEqual(
            self.request("choose_thread", thread_id=thread.thread_id).result["outcome"],
            "success",
        )
        self.assertEqual(
            self.request("say", message="鐘聲", client=self.delivered()).result["outcome"],
            "success",
        )
        self.enter(tick_from=100, tick_to=111, requested_seconds=11)
        wish = surface.wish_state(self.actor)
        self.assertEqual(wish["thread_id"], thread.thread_id)
        self.assertTrue(wish["thread_locked"])
        self.assertEqual(self.request("choose_thread", thread_id=None).result["code"], "thread_locked")
        self.assertEqual(surface.wish_state(self.actor)["thread_id"], thread.thread_id)

    @covers_requirement(
        "dream-session-lifecycle::a-session-is-conversing-until-it-is-finalized"
    )
    def test_a_draft_with_content_is_refused_while_conversing(self):
        self.enter()
        submitted = {"kind": "new_story", "summary": "訴說期間寫下的願望。"}
        for direction in (submitted, submitted["summary"]):
            with self.subTest(direction=direction):
                refused = self.request("draft", direction=direction).result
                self.assertEqual(refused["outcome"], "rejected")
                self.assertEqual(refused["code"], "direction_locked")
        self.assertEqual(
            surface.wish_state(self.actor)["proposal"], dream_proposal.empty_proposal()
        )
        self.assertFalse(surface.associated_session(self.actor).draft_id)
        self.assertFalse(CreativeRequest.objects.exists())

    @covers_requirement(
        "dream-session-lifecycle::a-session-is-conversing-until-it-is-finalized"
    )
    def test_confirm_before_finalize_is_refused(self):
        self.enter()
        refused = self.request(
            "confirm", direction={"kind": "new_story", "summary": "先行確認的願望。"}
        ).result
        self.assertEqual(refused["outcome"], "rejected")
        self.assertEqual(refused["code"], "not_finalized")
        self.assertFalse(CreativeRequest.objects.exists())
        self.assertTrue(service.dream_state(self.actor)["open"])

    @covers_requirement(
        "dream-session-lifecycle::a-session-is-conversing-until-it-is-finalized"
    )
    def test_a_bare_draft_while_conversing_saves_the_working_proposal(self):
        self.enter()
        client = self.exchange([
            {"command": "create", "path": "summary", "file_text": "在無名港尋找鐘聲。"},
        ])
        self.assertEqual(
            self.request("say", message="鐘聲", client=client).result["outcome"], "success"
        )
        self.assertEqual(self.request("draft").result["outcome"], "success")
        session = surface.associated_session(self.actor)
        self.assertEqual(session.stage, lifecycle.STAGE_CONVERSING)
        draft = get_draft(session.draft_id, str(self.actor.pk))
        self.assertEqual(draft.direction["summary"], "在無名港尋找鐘聲。")
        self.assertFalse(CreativeRequest.objects.exists())

    @covers_requirement(
        "dream-session-lifecycle::a-session-is-conversing-until-it-is-finalized"
    )
    def test_finalize_closes_free_text_and_saves_the_draft(self):
        self.enter()
        client = self.exchange([
            {"command": "create", "path": "summary", "file_text": "在無名港尋找鐘聲。"},
        ])
        self.assertEqual(
            self.request("say", message="鐘聲", client=client).result["outcome"], "success"
        )
        result = self.request("finalize").result
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "dream_finalize")
        session = surface.associated_session(self.actor)
        self.assertEqual(session.stage, lifecycle.STAGE_FINALIZED)
        state = service.dream_state(self.actor)
        self.assertEqual(state["stage"], lifecycle.STAGE_FINALIZED)
        self.assertEqual(state["proposal"]["summary"], "在無名港尋找鐘聲。")
        self.assertEqual(state["changes"]["summary"], "formed")
        self.assertTrue(state["can_edit"] and state["can_confirm"] and state["drafted"])
        self.assertFalse(
            state["can_input"] or state["can_finalize"] or state["can_choose_thread"]
        )
        draft = get_draft(session.draft_id, str(self.actor.pk))
        self.assertEqual(draft.direction["summary"], "在無名港尋找鐘聲。")
        self.assertFalse(CreativeRequest.objects.exists())
        # A further message is refused without consuming an exchange.
        refused = self.request("say", message="停止後仍想說", client=self.delivered()).result
        self.assertEqual(refused["code"], "dream_finalized")
        self.assertEqual(surface.associated_session(self.actor).completed_exchanges, 1)

    @covers_requirement(
        "dream-session-lifecycle::a-session-is-conversing-until-it-is-finalized"
    )
    def test_finalize_is_refused_while_a_response_is_pending(self):
        self.enter()
        pending = Deferred()
        session = SimpleNamespace(puppet=self.actor)
        self.live_sessions = [session]
        with patch("world.ai.dream.generate_dream_exchange", return_value=pending), \
                patch("server.dream_service._refresh"):
            state = service.dream_state(self.actor)
            said = adapter(
                "say",
                self.actor,
                {"session_id": state["session_id"], "revision": state["revision"],
                 "message": "鐘聲"},
                session,
            )
            self.assertEqual(said["code"], "dream_pending")
            refused = self.request("finalize").result
        self.assertEqual(refused["outcome"], "rejected")
        self.assertEqual(refused["code"], "dream_pending_response")
        self.assertEqual(
            surface.associated_session(self.actor).stage, lifecycle.STAGE_CONVERSING
        )
        self.assertTrue(service.dream_state(self.actor)["pending"])

    @covers_requirement(
        "dream-session-lifecycle::a-session-is-conversing-until-it-is-finalized"
    )
    def test_the_sixth_exchange_finalizes_and_saves_the_proposal_it_produced(self):
        self.enter()
        for index in range(6):
            client = (
                self.exchange(
                    [{"command": "create", "path": "summary",
                      "file_text": "第六次之後的願望。"}],
                    index=index,
                )
                if index == 5
                else self.delivered(index)
            )
            self.assertEqual(
                self.request(
                    "say", message=f"第 {index + 1} 次交流", client=client
                ).result["outcome"],
                "success",
            )
        session = surface.associated_session(self.actor)
        self.assertEqual(session.completed_exchanges, 6)
        self.assertEqual(session.stage, lifecycle.STAGE_FINALIZED)
        draft = get_draft(session.draft_id, str(self.actor.pk))
        self.assertEqual(draft.direction["summary"], "第六次之後的願望。")
        self.assertFalse(CreativeRequest.objects.exists())

    @covers_requirement(
        "dream-session-lifecycle::a-session-is-conversing-until-it-is-finalized"
    )
    def test_a_finalized_form_replaces_the_proposal_and_clears_the_report(self):
        self.enter()
        client = self.exchange([
            {"command": "create", "path": "themes", "file_text": "鐘聲"},
        ])
        self.assertEqual(
            self.request("say", message="加入主題", client=client).result["outcome"],
            "success",
        )
        self.assertEqual(
            surface.wish_state(self.actor)["changes"]["lists"]["themes"]["added"], ["鐘聲"]
        )
        self.assertEqual(self.request("finalize").result["outcome"], "success")
        submitted = {
            "kind": "new_story",
            "summary": "我自己寫下的願望。",
            "themes": ["重逢"],
            "atmosphere": ["安靜"],
            "emphasis": ["探索"],
            "exclusions": ["暴力"],
            "requirements": [{"kind": "place", "text": "南門"}],
        }
        self.assertEqual(
            self.request("draft", direction=dict(submitted)).result["outcome"], "success"
        )
        wish = surface.wish_state(self.actor)
        self.assertIsNone(wish["changes"])
        self.assertEqual(wish["proposal"]["summary"], submitted["summary"])
        self.assertEqual(wish["proposal"]["themes"], ["重逢"])
        self.assertEqual(wish["proposal"]["requirements"], submitted["requirements"])
        draft = get_draft(surface.associated_session(self.actor).draft_id, str(self.actor.pk))
        self.assertEqual(draft.direction["summary"], submitted["summary"])
        self.assertEqual(draft.direction["themes"], ["重逢"])
        self.assertEqual(draft.direction["requirements"], submitted["requirements"])

    @covers_requirement(
        "dream-session-lifecycle::a-session-is-conversing-until-it-is-finalized"
    )
    def test_the_finalized_form_keeps_the_locked_thread(self):
        self.enter()
        chosen = create_thread(
            thread_id="synthetic-form-thread",
            origin="synthetic-origin",
            participants=[str(self.actor.pk)],
        )
        other = create_thread(
            thread_id="synthetic-other-form-thread",
            origin="synthetic-origin",
            participants=[str(self.actor.pk)],
        )
        self.assertEqual(
            self.request("choose_thread", thread_id=chosen.thread_id).result["outcome"],
            "success",
        )
        self.assertEqual(self.request("finalize").result["outcome"], "success")
        form = {"kind": "thread_direction", "summary": "沿著鐘聲的故事線。"}
        # An omitted thread keeps the locked choice.
        self.assertEqual(
            self.request("draft", direction=dict(form)).result["outcome"], "success"
        )
        self.assertEqual(surface.wish_state(self.actor)["thread_id"], chosen.thread_id)
        # Naming another thread is refused without a write.
        before = surface.association(self.actor)
        refused = self.request(
            "draft", direction={**form, "thread_id": other.thread_id}
        ).result
        self.assertEqual(refused["code"], "thread_locked")
        self.assertEqual(surface.association(self.actor), before)
        # A choice whose thread has ended may be released back to a new story.
        resolve_thread(thread_id=chosen.thread_id, tick=100, actor_id=str(self.actor.pk))
        released = self.request(
            "draft", direction={**form, "kind": "new_story", "thread_id": None}
        )
        self.assertEqual(released.result["outcome"], "success")
        self.assertIsNone(surface.wish_state(self.actor)["thread_id"])

    @covers_requirement(
        "dream-session-lifecycle::a-session-is-conversing-until-it-is-finalized"
    )
    def test_thread_choice_closes_with_the_stage(self):
        self.enter()
        thread = create_thread(
            thread_id="synthetic-stage-closed-choice",
            origin="synthetic-origin",
            participants=[str(self.actor.pk)],
        )
        # Finalized before any message was sent: the choice is still closed.
        self.assertEqual(self.request("finalize").result["outcome"], "success")
        refused = self.request("choose_thread", thread_id=thread.thread_id).result
        self.assertEqual(refused["outcome"], "rejected")
        self.assertEqual(refused["code"], "thread_choice_closed")
        self.assertIsNone(surface.wish_state(self.actor)["thread_id"])

    @covers_requirement(
        "dream-session-lifecycle::a-session-is-conversing-until-it-is-finalized"
    )
    def test_a_finalized_dream_stays_finalized_on_the_same_sleep(self):
        from world.rules.sleep_receipt import read_sleep_view_generation

        sleep_id, _receipt = self.grant_sleep()
        surface.enter_for_owner(
            self.actor, sleep_id=sleep_id, revision=0,
            generation=read_sleep_view_generation(self.actor),
        )
        self.assertEqual(self.request("finalize").result["outcome"], "success")
        self.assertFalse(service.dream_state(self.actor)["can_input"])
        # Reading again, and re-entering the same accepted receipt, both keep it.
        self.assertEqual(
            surface.associated_session(self.actor).stage, lifecycle.STAGE_FINALIZED
        )
        surface.enter_for_owner(
            self.actor, sleep_id=sleep_id, revision=0,
            generation=read_sleep_view_generation(self.actor),
        )
        self.assertEqual(
            surface.associated_session(self.actor).stage, lifecycle.STAGE_FINALIZED
        )
        refused = self.request(
            "say", message="同一夜的下一句話", client=self.delivered()
        ).result
        self.assertEqual(refused["code"], "dream_finalized")

    @covers_requirement(
        "dream-session-lifecycle::a-session-is-conversing-until-it-is-finalized"
    )
    def test_awakening_keeps_the_right_version(self):
        first = self.enter()
        client = self.exchange([
            {"command": "create", "path": "summary", "file_text": "醒來前留下的鐘聲。"},
        ])
        self.assertEqual(
            self.request("say", message="鐘聲", client=client).result["outcome"], "success"
        )
        self.assertEqual(self.request("awaken").result["outcome"], "success")
        session = surface.associated_session(self.actor)
        conversing = get_draft(session.draft_id, str(self.actor.pk))
        self.assertEqual(conversing.direction["summary"], "醒來前留下的鐘聲。")

        # A later sleep resumes the dream; finalizing then awakening writes
        # nothing further, so the draft keeps its identity and version.
        later = self.enter(tick_from=100, tick_to=121, requested_seconds=21)
        self.assertEqual(later["session_id"], first["session_id"])
        self.assertEqual(self.request("finalize").result["outcome"], "success")
        self.assertEqual(self.request("awaken").result["outcome"], "success")
        final = get_draft(session.draft_id, str(self.actor.pk))
        self.assertEqual(final.direction["summary"], "醒來前留下的鐘聲。")
        self.assertEqual(int(final.revision), int(conversing.revision))

    @covers_requirement(
        "dream-session-lifecycle::a-session-is-conversing-until-it-is-finalized"
    )
    def test_a_finalized_awakening_ignores_supplied_content(self):
        # A departure is not a manual edit: content a caller sends with it
        # changes neither the working proposal nor the draft the finalize saved.
        self.enter()
        client = self.exchange([
            {"command": "create", "path": "summary", "file_text": "女神寫下的方向。"},
        ])
        self.assertEqual(
            self.request("say", message="鐘聲", client=client).result["outcome"], "success"
        )
        self.assertEqual(self.request("finalize").result["outcome"], "success")
        before = surface.wish_state(self.actor)
        session = surface.associated_session(self.actor)
        draft_before = get_draft(session.draft_id, str(self.actor.pk))
        self.assertEqual(
            self.request(
                "awaken",
                direction={"kind": "new_story", "summary": "離去時偷渡的願望。"},
            ).result["outcome"],
            "success",
        )
        self.assertEqual(surface.wish_state(self.actor), before)
        draft_after = get_draft(session.draft_id, str(self.actor.pk))
        self.assertEqual(draft_after.direction, draft_before.direction)
        self.assertEqual(int(draft_after.revision), int(draft_before.revision))

    @covers_requirement(
        "dream-session-lifecycle::a-later-sleep-reopens-an-unfinalized-conversation"
    )
    def test_a_later_sleep_returns_to_conversing(self):
        first = self.enter()
        client = self.exchange([
            {"command": "create", "path": "summary", "file_text": "在無名港尋找鐘聲。"},
        ])
        self.assertEqual(
            self.request("say", message="鐘聲", client=client).result["outcome"], "success"
        )
        self.assertEqual(self.request("finalize").result["outcome"], "success")
        self.assertEqual(self.request("awaken").result["outcome"], "success")

        resumed = self.enter(tick_from=100, tick_to=121, requested_seconds=21)
        self.assertEqual(resumed["session_id"], first["session_id"])
        self.assertEqual(
            surface.associated_session(self.actor).stage, lifecycle.STAGE_CONVERSING
        )
        resumed_state = service.dream_state(self.actor)
        self.assertEqual(resumed_state["stage"], lifecycle.STAGE_CONVERSING)
        self.assertTrue(resumed_state["can_input"] and resumed_state["can_finalize"])
        # The thread choice stays locked by the exchange that was already
        # accepted, and finalizing has not happened.
        self.assertFalse(
            resumed_state["can_choose_thread"]
            or resumed_state["can_edit"]
            or resumed_state["can_confirm"]
        )
        self.assertEqual(
            surface.wish_state(self.actor)["proposal"]["summary"], "在無名港尋找鐘聲。"
        )
        self.assertEqual(
            self.request(
                "say", message="回來後繼續說", client=self.delivered(index=1)
            ).result["outcome"],
            "success",
        )
        self.assertEqual(surface.associated_session(self.actor).completed_exchanges, 2)

    @covers_requirement("dream-session-lifecycle::convergence-and-exit-require-explicit-choices")
    def test_exit_before_cap_offers_draft_preservation_and_finalize(self):
        self.enter()
        first = self.exchange([
            {"command": "create", "path": "summary", "file_text": "醒來前的願望。"},
        ])
        self.assertEqual(
            self.request("say", message="第一次交談", client=first).result["outcome"],
            "success",
        )
        self.assertEqual(
            self.request(
                "say", message="第二次交談", client=self.delivered(index=1)
            ).result["outcome"],
            "success",
        )
        # Draft preservation is available and schedules nothing; confirmation
        # only after the explicit finalize.
        self.assertEqual(self.request("draft").result["outcome"], "success")
        self.assertFalse(CreativeRequest.objects.exists())
        self.assertEqual(self.request("confirm").result["code"], "not_finalized")
        self.assertEqual(self.request("finalize").result["outcome"], "success")
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.request("confirm").result["outcome"], "success")
        self.assertEqual(CreativeRequest.objects.count(), 1)
        self.assertEqual(self.request("awaken").result["outcome"], "success")

    @covers_requirement(
        "dream-authoring::confirmation-freezes-visible-bounded-experience-requirements"
    )
    def test_a_motivating_direction_keeps_its_requirement_rows_through_confirmation(self):
        self.enter()
        client = self.exchange([
            {"command": "create", "path": "summary",
             "file_text": "在南門遇見一個女孩，幫她找媽媽。"},
            {"command": "create", "path": "requirements",
             "file_text": "place: 南門\nnew_character: 一個女孩\nprivate_commission: 帶她找媽媽"},
        ])
        self.assertEqual(
            self.request("say", message="鐘聲", client=client).result["outcome"], "success"
        )
        self.assertEqual(
            [row["text"] for row in service.dream_state(self.actor)["proposal"]["requirements"]],
            ["南門", "一個女孩", "帶她找媽媽"],
        )
        self.assertEqual(self.request("finalize").result["outcome"], "success")
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.request("confirm").result["outcome"], "success")
        stored = CreativeRequest.objects.get()
        self.assertEqual(
            [(row["kind"], row["text"]) for row in stored.direction["requirements"]],
            [
                ("place", "南門"),
                ("new_character", "一個女孩"),
                ("private_commission", "帶她找媽媽"),
            ],
        )

    @covers_requirement(
        "dream-authoring::confirmation-freezes-visible-bounded-experience-requirements"
    )
    def test_an_invalid_submitted_proposal_stays_the_unconfirmed_draft(self):
        from world.narrative.authoring import REASON_MESSAGES

        self.enter()
        self.assertEqual(self.request("finalize").result["outcome"], "success")
        submitted = {
            "kind": "new_story",
            "summary": "我想得到一枚線索。",
            "effects": ["clue"],
        }
        refused = self.request("confirm", direction=submitted).result
        self.assertEqual(refused["outcome"], "rejected")
        self.assertEqual(refused["code"], "invalid_direction")
        self.assertEqual(refused["message"], REASON_MESSAGES["unauthorized_effects"])
        self.assertFalse(CreativeRequest.objects.exists())
        session = surface.associated_session(self.actor)
        self.assertTrue(service.dream_state(self.actor)["open"])
        draft = get_draft(session.draft_id, str(self.actor.pk))
        self.assertEqual(draft.direction["summary"], submitted["summary"])
        self.assertEqual(draft.direction["effects"], ["clue"])
        self.assertIsNone(draft.confirmed_revision)

    def test_choose_thread_payload_validation(self):
        handle = {"session_id": "session:synthetic-dream", "revision": 1}
        self.assertEqual(
            validate("choose_thread", {**handle, "thread_id": "synthetic-thread"}),
            {**handle, "thread_id": "synthetic-thread"},
        )
        self.assertIsNone(
            validate("choose_thread", {**handle, "thread_id": None})["thread_id"]
        )
        for payload in (
            dict(handle),
            {**handle, "thread_id": ""},
            {**handle, "thread_id": "t" * 129},
            {**handle, "thread_id": 7},
            {**handle, "thread_id": "synthetic-thread", "extra": 1},
            {"session_id": "session:synthetic-dream", "revision": True, "thread_id": None},
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    validate("choose_thread", payload)

    def test_finalize_payload_validation(self):
        # Closing free text carries no content of its own: the exact pair names
        # the session it acts on and the revision it must still match.
        handle = {"session_id": "session:synthetic-dream", "revision": 1}
        self.assertEqual(validate("finalize", dict(handle)), handle)
        for payload in (
            {"session_id": "session:synthetic-dream"},
            {**handle, "direction": {}},
            {**handle, "thread_id": None},
            {"session_id": "session:synthetic-dream", "revision": True},
            {"session_id": "", "revision": 1},
            "finalize",
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    validate("finalize", payload)

    @covers_requirement(
        "dream-sleep-surface::text-dream-commands-reach-thread-choice-finalize-and-the-change-report"
    )
    def test_the_thread_command_chooses_an_offered_number_and_the_new_story_word(self):
        self.enter()
        for index, label in enumerate(("合成甲故事線", "合成乙故事線")):
            create_thread(
                thread_id=f"synthetic-choice-{index}",
                origin=f"synthetic-choice-origin-{index}",
                participants=[str(self.actor.pk)],
                factual_summary=label,
            )
        choices = service.dream_state(self.actor)["thread_choices"]
        self.assertEqual(len(choices), 2)
        chosen = self.run_dream("thread 2").func()
        # The shared thread-choice operation, not a local write, records it.
        self.assertEqual(chosen.result["code"], "dream_choose_thread")
        self.assertEqual(
            surface.wish_state(self.actor)["thread_id"], choices[1]["id"]
        )
        # Both spellings the listing offers resolve to a new story.
        for argument in ("new", "NEW", "0"):
            with self.subTest(argument=argument):
                self.assertEqual(
                    self.run_dream("thread 1").func().result["outcome"], "success"
                )
                self.assertEqual(
                    surface.wish_state(self.actor)["thread_id"], choices[0]["id"]
                )
                released = self.run_dream("thread " + argument).func()
                self.assertEqual(released.result["code"], "dream_choose_thread")
                self.assertIsNone(surface.wish_state(self.actor)["thread_id"])

    @covers_requirement(
        "dream-sleep-surface::text-dream-commands-reach-thread-choice-finalize-and-the-change-report"
    )
    def test_the_thread_command_without_argument_lists_the_choices_and_writes_nothing(self):
        self.enter()
        for index, label in enumerate(("合成列表甲", "合成列表乙")):
            create_thread(
                thread_id=f"synthetic-listing-{index}",
                origin=f"synthetic-listing-origin-{index}",
                participants=[str(self.actor.pk)],
                factual_summary=label,
            )
        before = service.dream_state(self.actor)
        self.assertIsNone(self.run_dream("thread").func())
        printed = self.printed()
        self.assertEqual(len(printed), 1)
        lines = printed[0].splitlines()
        self.assertEqual(len(lines), 1 + len(before["thread_choices"]))
        self.assertIn("0", lines[0])
        self.assertIn("new", lines[0])
        for number, choice in enumerate(before["thread_choices"], start=1):
            self.assertTrue(lines[number].startswith(f"{number}"), lines[number])
            self.assertIn(choice["label"], lines[number])
        after = service.dream_state(self.actor)
        self.assertEqual(after["revision"], before["revision"])
        self.assertIsNone(surface.wish_state(self.actor)["thread_id"])

    @covers_requirement(
        "dream-sleep-surface::text-dream-commands-reach-thread-choice-finalize-and-the-change-report"
    )
    def test_an_unknown_thread_argument_is_refused_without_the_shared_operation(self):
        self.enter()
        create_thread(
            thread_id="synthetic-only-thread",
            origin="synthetic-only-origin",
            participants=[str(self.actor.pk)],
            factual_summary="合成唯一故事線",
        )
        before = service.dream_state(self.actor)
        for argument in ("7", "synthetic-unoffered-thread"):
            with self.subTest(argument=argument):
                with patch("server.dream_service.act") as shared:
                    self.run_dream("thread " + argument).func()
                    shared.assert_not_called()
                printed = self.printed()
                self.assertEqual(len(printed), 1)
                self.assertTrue(printed[0])
                after = service.dream_state(self.actor)
                self.assertEqual(after["revision"], before["revision"])
                self.assertIsNone(surface.wish_state(self.actor)["thread_id"])

    @covers_requirement(
        "dream-sleep-surface::text-dream-commands-reach-thread-choice-finalize-and-the-change-report"
    )
    def test_the_finalize_command_closes_free_text_and_offers_editing(self):
        self.enter()
        before = service.dream_state(self.actor)
        self.assertTrue(before["can_input"])
        self.assertTrue(before["can_finalize"])
        # The departure carries no content of its own: anything after it is
        # a usage refusal, not a silent edit.
        self.assertIsNone(self.run_dream("finalize 現在").func())
        self.assertIn("用法", self.printed()[-1])
        self.assertEqual(service.dream_state(self.actor)["revision"], before["revision"])
        finalized = self.run_dream("finalize").func()
        self.assertEqual(finalized.result["code"], "dream_finalize")
        after = service.dream_state(self.actor)
        self.assertFalse(after["can_input"] or after["can_finalize"])
        self.assertTrue(after["can_edit"] and after["can_confirm"])
        rendered = self.printed()[-1]
        self.assertIn("dream draft", rendered)
        self.assertIn("dream confirm", rendered)
        self.assertNotIn("dream say", rendered)

    @covers_requirement(
        "dream-sleep-surface::text-dream-commands-reach-thread-choice-finalize-and-the-change-report"
    )
    def test_bare_dream_shows_the_whole_wish_its_thread_and_both_moved_items(self):
        self.enter()
        thread = create_thread(
            thread_id="synthetic-wish-thread",
            origin="synthetic-wish-origin",
            participants=[str(self.actor.pk)],
            factual_summary="合成歸屬故事線",
        )
        self.assertEqual(self.run_dream("thread 1").func().result["outcome"], "success")
        self.assertEqual(
            self.request("say", message="先說第一句", client=self.exchange([
                {"command": "create", "path": "summary", "file_text": "合成願望的摘要。"},
                {"command": "create", "path": "themes", "file_text": "合成舊主題"},
                {"command": "create", "path": "atmosphere", "file_text": "合成氛圍"},
                {"command": "create", "path": "requirements", "file_text": "place: 合成地點"},
            ])).result["outcome"],
            "success",
        )
        self.assertEqual(surface.wish_state(self.actor)["thread_id"], thread.thread_id)
        self.assertEqual(
            self.request("say", message="再說一句", client=self.exchange([
                {"command": "str_replace", "path": "themes",
                 "old_str": "合成舊主題", "new_str": "合成新主題"},
            ], index=1)).result["outcome"],
            "success",
        )
        changes = service.dream_state(self.actor)["changes"]
        self.assertEqual(changes["lists"]["themes"]["added"], ["合成新主題"])
        self.assertEqual(changes["lists"]["themes"]["removed"], ["合成舊主題"])
        self.run_dream("").func()
        printed = self.printed()
        self.assertEqual(len(printed), 1)
        rendered = printed[0]
        for value in ("合成願望的摘要。", "合成新主題", "合成氛圍", "合成地點"):
            self.assertIn(value, rendered)
        # The chosen thread, and a report that names the removed item too.
        self.assertIn("合成歸屬故事線", rendered)
        self.assertIn("合成舊主題", rendered)

    @covers_requirement(
        "dream-sleep-surface::text-dream-commands-reach-thread-choice-finalize-and-the-change-report"
    )
    def test_a_delivered_say_ends_with_the_change_summary(self):
        self.enter()
        with patch(
            "world.ai.client.OpenAICompatClient",
            return_value=self.exchange([
                {"command": "create", "path": "themes", "file_text": "合成新增主題"},
            ]),
        ):
            self.assertEqual(
                self.run_dream("say 鐘聲").func().result["outcome"], "success"
            )
        edited = service.dream_state(self.actor)
        edited_line = self.printed()[-1].splitlines()[-1]
        self.assertEqual(edited_line, render_changes(edited["changes"]))
        self.assertIn("合成新增主題", edited_line)
        with patch(
            "world.ai.client.OpenAICompatClient",
            return_value=self.delivered(index=1),
        ):
            self.assertEqual(
                self.run_dream("say 再一次").func().result["outcome"], "success"
            )
        settled = service.dream_state(self.actor)
        settled_line = self.printed()[-1].splitlines()[-1]
        self.assertEqual(settled_line, render_changes(settled["changes"]))
        self.assertNotIn("合成新增主題", settled_line)
        self.assertNotEqual(settled_line, edited_line)

    @covers_requirement(
        "dream-sleep-surface::text-dream-commands-reach-thread-choice-finalize-and-the-change-report"
    )
    def test_the_text_draft_replaces_only_the_summary_after_finalize(self):
        self.enter()
        thread = create_thread(
            thread_id="synthetic-summary-thread",
            origin="synthetic-summary-origin",
            participants=[str(self.actor.pk)],
            factual_summary="合成摘要故事線",
        )
        self.assertEqual(self.run_dream("thread 1").func().result["outcome"], "success")
        self.assertEqual(
            self.request("say", message="先說一句", client=self.exchange([
                {"command": "create", "path": "summary", "file_text": "訴說時的摘要。"},
                {"command": "create", "path": "themes", "file_text": "合成主題"},
                {"command": "create", "path": "requirements", "file_text": "place: 合成地點"},
            ])).result["outcome"],
            "success",
        )
        refused = self.run_dream("draft 訴說期間的改寫").func().result
        self.assertEqual(refused["outcome"], "rejected")
        self.assertEqual(refused["code"], "direction_locked")
        self.assertEqual(
            surface.wish_state(self.actor)["proposal"]["summary"], "訴說時的摘要。"
        )
        self.assertEqual(
            self.run_dream("finalize").func().result["outcome"], "success"
        )
        before = surface.wish_state(self.actor)["proposal"]
        self.assertEqual(
            self.run_dream("draft 斟酌後的摘要").func().result["outcome"], "success"
        )
        wish = surface.wish_state(self.actor)
        self.assertEqual(wish["proposal"]["summary"], "斟酌後的摘要")
        self.assertEqual(wish["proposal"]["themes"], before["themes"])
        self.assertEqual(wish["proposal"]["requirements"], before["requirements"])
        self.assertEqual(wish["thread_id"], thread.thread_id)

    @covers_requirement(
        "dream-sleep-surface::text-dream-commands-reach-thread-choice-finalize-and-the-change-report"
    )
    def test_the_change_renderer_names_every_moved_item_on_one_line(self):
        moved = {
            "summary": "formed",
            "lists": {
                field: {"added": [], "removed": []}
                for field in dream_proposal.LIST_FIELDS
            },
            "requirements": {
                "added": [],
                "removed": [{"kind": "place", "text": "合成舊地點"}],
            },
        }
        moved["lists"]["themes"] = {"added": ["合成新添"], "removed": ["合成劃去"]}
        rendered = render_changes(moved)
        self.assertNotIn("\n", rendered)
        self.assertIn("合成新添", rendered)
        self.assertIn("合成劃去", rendered)
        self.assertIn("合成舊地點", rendered)
        # One segment per changed field: the two moved items of a single list
        # stay together, and the changed requirements keep their own segment.
        segments = rendered.split("；")
        self.assertEqual(len(segments), 3)
        self.assertIn("合成新添", segments[1])
        self.assertIn("合成劃去", segments[1])
        self.assertIn("合成舊地點", segments[2])
        unchanged = {
            "summary": None,
            "lists": {
                field: {"added": [], "removed": []}
                for field in dream_proposal.LIST_FIELDS
            },
            "requirements": {"added": [], "removed": []},
        }
        self.assertNotEqual(render_changes(unchanged), rendered)
        self.assertNotIn("合成新添", render_changes(unchanged))
        self.assertEqual(render_changes(None), "")


def _synthetic_webp():
    """A real, decodable WebP for the catalog's header-admission probe."""
    from io import BytesIO

    from PIL import Image

    buffer = BytesIO()
    Image.new("RGB", (8, 8), (200, 200, 200)).save(buffer, format="WEBP")
    return buffer.getvalue()


class CampingDreamTests(EvenniaTest):
    """An entry-time answer binds the new owner receipt; departure settles it."""

    def setUp(self):
        super().setUp()
        from world.rules.clock import _EVENT_SOURCES
        from world.rules.fatigue import SleepPosture, write_fatigue_state

        sources = dict(_EVENT_SOURCES)
        _EVENT_SOURCES.clear()
        self.addCleanup(_EVENT_SOURCES.update, sources)
        self.addCleanup(_EVENT_SOURCES.clear)
        self.owner = self.char1
        self.owner.race = "human"
        self.owner.apply_race_baseline()
        for key in ("hp", "mp", "sp"):
            gauge = getattr(self.owner.traits, key)
            gauge.current = gauge.max
            gauge.rate = 0.0
        self.owner.location = self.room1
        self.owner.save()
        self.owner.msg = Mock()
        write_fatigue_state(self.owner, 180000, SleepPosture.AWAKE)

    def test_answered_receipt_and_departure(self):
        from world.rules.camping import commit_sleep_entry
        from world.rules.sleep_receipt import STATE_COMPLETED, read_sleep_receipt
        from world.rules.time_skip import owner_sleep_view_state

        tick = int(get_world_clock().tick)
        result = commit_sleep_entry(
            self.owner,
            scope="self",
            mode="duration",
            seconds=1800,
            answer="enter",
            operation_id="dream-entry",
        )
        self.assertTrue(result["dream_entered"])
        receipt = read_sleep_receipt(self.owner)
        state = service.dream_state(self.owner)
        # The dream binds the newly accepted receipt at zero elapsed time and
        # no question is pending for it.
        self.assertTrue(state["open"])
        self.assertEqual(state["sleep"]["seconds"], 0)
        self.assertEqual(surface.association(self.owner)["sleep_id"], receipt.sleep_id)
        self.assertEqual(result["owner_sleep_id"], receipt.sleep_id)
        self.assertFalse(owner_sleep_view_state(self.owner)["pending"])
        self.assertIsNone(service.pending_sleep_question(self.owner))
        self.assertEqual(int(get_world_clock().tick), tick)
        # Departure continues exactly this accepted sleep to its deadline.
        with self.captureOnCommitCallbacks(execute=True):
            service.act(self.owner, "awaken", session_id=state["session_id"], revision=state["revision"])
        done = read_sleep_receipt(self.owner)
        self.assertEqual(done.sleep_id, receipt.sleep_id)
        self.assertEqual(done.state, STATE_COMPLETED)
        self.assertEqual(int(get_world_clock().tick), tick + 1800)
