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

from commands.dream import CmdDream, render_state
from commands.skip import CmdSleep
from server import dream_service as service
from tools.spec_traceability import covers_requirement
from web.webclient.actions.dream_actions import adapter, validate
from web.webclient.actions.exploration_actions import _wait_adapter, validate_wait_payload
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.dream import dream_presenter
from world.ai import dream, guardrail
from world.art import formats, official as official_art, subjects
from world.ai.fake_client import FakeLLMClient
from world.ai.profiles import default_profiles
from world.ai.schemas.registry import _OUTPUT_SCHEMAS
from world.narrative import dream_session as lifecycle
from world.narrative import dream_surface as surface
from world.narrative.models import CreativeRequest
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

    def enter(self, **overrides):
        values = {"tick_from": 100, "tick_to": 100, "requested_seconds": 0}
        values.update(overrides)
        return service.enter_after_sleep(self.actor, **values)

    def request(self, action, **kwargs):
        state = service.dream_state(self.actor)
        return service.act(self.actor, action, session_id=state["session_id"], revision=state["revision"], **kwargs)

    def delivered(self, index=0):
        client = FakeLLMClient()
        client.add_response(lambda descriptor: True, json.dumps({
            "scene": "合成場景：雲海王座之前，親密的身影與漫過腳踝的積水一同隨呼吸起伏。",
            "dialogue": "我們繼續商談尋找鐘聲的故事方向。",
            "phase": prospective_state(index).level,
        }, ensure_ascii=False))
        return client

    def physical(self):
        return (self.clock.tick, tuple(self.actor.traits.get(key).value for key in ("hp", "mp", "sp", "pleasure")),
                deepcopy(self.actor.db.sexual_state), deepcopy(self.actor.db.buffs),
                deepcopy(self.actor.db.skill_proficiency), deepcopy(self.actor.db.relationships))

    @covers_requirement(
        "time-skip-commands::sleep-computes-its-own-duration-from-gauge-regen-capped-at-a-configured-maximum",
        "dream-sleep-surface::optional-collaboration-follows-one-accepted-sleep-result",
    )
    def test_zero_duration_real_sleep_and_ordinary_sleep(self):
        for gauge in ("hp", "mp", "sp"):
            trait = self.actor.traits.get(gauge)
            trait.current = trait.max
        command = CmdSleep()
        command.caller = self.actor
        command.args = ""
        with patch("commands.skip._maybe_nominate_after_rest"):
            command.func()
        self.assertIsNone(service.dream_state(self.actor))
        command.args = "dream"
        before = self.physical()
        with patch("commands.skip._maybe_nominate_after_rest"):
            command.func()
        state = service.dream_state(self.actor)
        self.assertEqual(state["sleep"]["seconds"], 0)
        self.assertEqual(state["remaining"], 6)
        self.assertEqual(before, self.physical())
        self.assertIn("dream awaken", render_state(state))

    @covers_requirement("dream-sleep-surface::optional-collaboration-follows-one-accepted-sleep-result")
    def test_browser_zero_sleep_choice_and_ordinary_rest_wait(self):
        for payload in ({"sleep": True}, {"seconds": 5}, {"daypart": "dawn"}):
            clock = SimpleNamespace(tick=100, calendar=self.clock.calendar)
            with patch("web.webclient.actions.exploration_actions.advance_skip", return_value=[]), patch(
                    "web.webclient.actions.exploration_actions.get_world_clock", return_value=clock), patch(
                    "server.title_nomination_service.schedule_rest_boundary_nomination"):
                self.assertEqual(_wait_adapter(self.actor, validate_wait_payload(payload))["outcome"], "success")
            self.assertIsNone(service.dream_state(self.actor))
        with patch("web.webclient.actions.exploration_actions.seconds_to_full_regen", return_value=0), patch(
                "server.title_nomination_service.schedule_rest_boundary_nomination"):
            result = _wait_adapter(self.actor, validate_wait_payload({"sleep": True, "dream": True}))
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(service.dream_state(self.actor)["sleep"]["seconds"], 0)
        for forged in ({"sleep": 1, "dream": True}, {"sleep": True, "dream": 1}, {"sleep": True, "dream": True, "seconds": 0}):
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
                "web.webclient.actions.exploration_actions.advance_skip") as advance:
            result = _wait_adapter(self.actor, {"sleep": True, "dream": True})
            advance.assert_not_called()
        self.assertEqual(result["outcome"], "rejected")
        self.assertIsNone(service.dream_state(self.actor))

    @covers_requirement("dream-sleep-surface::optional-collaboration-follows-one-accepted-sleep-result")
    def test_interrupted_committed_result_uses_actual_ticks_on_both_clients(self):
        for browser in (False, True):
            clock = SimpleNamespace(tick=100)
            def advance(*args, **kwargs):
                clock.tick = 107
                return [SimpleNamespace(kind="synthetic_interrupt")]
            if browser:
                with patch("web.webclient.actions.exploration_actions.get_world_clock", return_value=clock), patch(
                        "web.webclient.actions.exploration_actions.advance_skip", side_effect=advance) as call, patch(
                        "web.webclient.actions.exploration_actions.seconds_to_full_regen", return_value=30), patch(
                        "server.title_nomination_service.schedule_rest_boundary_nomination"):
                    _wait_adapter(self.actor, {"sleep": True, "dream": True})
            else:
                clock.advance = Mock(side_effect=advance)
                call = clock.advance
                command = CmdSleep()
                command.caller = self.actor
                command.args = "dream"
                with patch("commands.skip.get_world_clock", return_value=clock), patch(
                        "commands.skip._seconds_to_full_regen", return_value=30), patch("commands.skip._maybe_nominate_after_rest"):
                    command.func()
            self.assertEqual(call.call_count, 1)
            state = service.dream_state(self.actor)
            self.assertEqual(state["sleep"]["seconds"], 7)
            self.assertEqual(state["sleep"]["requested_seconds"], 30)
            self.assertEqual(state["sleep"]["event_kinds"], ["synthetic_interrupt"])
            self.assertIn("時間經過了 7 秒。", [call.args[0] for call in self.actor.msg.call_args_list])
            self.assertEqual(self.request("awaken").result["outcome"], "success")
            self.assertEqual(clock.tick, 107)

    @covers_requirement(
        "dream-explicit-presentation::dream-presentation-changes-no-live-character-effects",
        "dream-explicit-presentation::dream-collaboration-uses-the-approved-explicit-frame",
        "dream-sleep-surface::dream-departure-never-settles-sleep-again",
    )
    def test_recorded_changed_path_sleep_exchange_draft_confirm_awaken_smoke(self):
        command = CmdSleep()
        command.caller = self.actor
        command.args = "dream"
        with patch("commands.skip._seconds_to_full_regen", return_value=0), patch("commands.skip._maybe_nominate_after_rest"):
            command.func()
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
        with patch("world.ai.client.OpenAICompatClient", side_effect=AssertionError("escape called model")):
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
        self.assertNotIn("dream say", render_state(state))
        self.assertEqual(self.request("say", message="第七次", client=self.delivered()).result["outcome"], "rejected")
        self.assertEqual(self.request("draft").result["outcome"], "success")
        self.assertEqual(self.request("awaken").result["outcome"], "success")
        self.assertEqual(self.physical(), physical)
        self.assertTrue(service.dream_state(self.actor)["ending_phase"])

    @covers_requirement(
        "dream-session-lifecycle::failures-preserve-progress-and-permit-offline-awakening",
        "dream-sleep-surface::dream-departure-never-settles-sleep-again",
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
        self.assertEqual(self.request("draft", direction=direction).result["outcome"], "success")
        self.assertEqual(self.request("say", message="我還想繼續討論。", client=self.delivered()).result["outcome"], "success")
        state = service.dream_state(self.actor)
        self.assertEqual("".join(state["direction_parts"]), direction["summary"])
        self.assertEqual(state["draft_preferences"]["thread_id"], thread.thread_id)
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
        self.assertEqual(self.request("confirm").result["code"], "empty_direction")
        self.assertFalse(surface.associated_session(self.actor).draft_id)
        client = self.delivered()
        self.assertEqual(self.request("say", message="", client=client).result["code"], "empty_input")
        self.assertEqual(self.request("say", message="界" * 4001, client=client).result["code"], "oversized_input")
        self.assertEqual(client.calls, [])
        command = CmdDream()
        command.caller = self.actor
        command.session = None
        command.args = "awaken"
        self.actor.msg.reset_mock()
        self.assertEqual(command.func().result["outcome"], "success")
        ending = service.dream_state(self.actor)["ending"]
        self.assertEqual([call.args[0] for call in self.actor.msg.call_args_list].count(ending), 1)
        self.assertFalse(surface.associated_session(self.actor).draft_id)

    @covers_requirement(
        "dream-explicit-presentation::dream-collaboration-uses-the-approved-explicit-frame",
    )
    def test_scene_art_resolves_only_from_the_official_catalog(self):
        # The dream stage's artwork is an external official asset: the panel
        # carries the catalog URL only while the official snapshot admits the
        # identity, and an empty snapshot (offline/absent folder) yields "".
        self.enter()
        identity = surface.DREAM_GODDESS_SCENE_IDENTITY
        self.assertTrue(identity.startswith("npc/" + surface.DREAM_GODDESS_NPC_KEY + "/"))
        self.assertEqual(service.dream_state(self.actor)["scene_art"], "")
        image = official_art.OfficialImage(
            identity=identity, kind="npc", key=surface.DREAM_GODDESS_NPC_KEY,
            fingerprint="a" * 64, image_size={"width": 2880, "height": 1600},
            face_rect={}, stage={},
        )
        with patch.object(
            official_art, "_CATALOG",
            official_art.OfficialCatalog(
                {(image.kind, image.key): official_art.OfficialContent(
                    kind=image.kind, key=image.key, default_identity=identity,
                    images=(identity,))},
                {identity: image},
            ),
        ):
            url = service.dream_state(self.actor)["scene_art"]
        self.assertEqual(url, f"/art/official/{'a' * 64}/{identity}")
        self.assertLessEqual(len(url), 256)

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
        parts = surface.DREAM_GODDESS_SCENE_IDENTITY.split("/")
        self.assertEqual(len(parts), 3)
        kind, key, filename = parts
        self.assertIn(kind, official_art.OFFICIAL_CONTENT_KINDS)
        self.assertTrue(subjects.is_valid_subject_key(key))
        self.assertIn(Path(filename).suffix, formats.STORE_EXTENSIONS)
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / surface.DREAM_GODDESS_SCENE_IDENTITY
            target.parent.mkdir(parents=True)
            target.write_bytes(_synthetic_webp())
            with override_settings(ART_OFFICIAL_ROOT=root):
                official_art.reset_catalog()
                try:
                    official_art.load_catalog()
                    self.assertTrue(surface.scene_art_url())
                finally:
                    official_art.reset_catalog()


def _synthetic_webp():
    """A real, decodable WebP for the catalog's header-admission probe."""
    from io import BytesIO

    from PIL import Image

    buffer = BytesIO()
    Image.new("RGB", (8, 8), (200, 200, 200)).save(buffer, format="WEBP")
    return buffer.getvalue()
