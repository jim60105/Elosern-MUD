"""Tests for the epithet-nomination composition-root service (change G).

Covers the fire-and-forget scheduling contract (never raises, never blocks,
no client consulted offline), rest-point gating (logout/rest/exam/quest
observers through ``transaction.on_commit``), the suppression short-circuit
(single ballot + decline cooldown, accept never cools down), persistence
delegated to the rules writer, and the bounded panel push. The LLM is always
the ``FakeLLMClient`` double — never a live call.
"""

import json
from types import SimpleNamespace
from unittest.mock import patch

from django.db import transaction
from django.test import override_settings

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from server import title_nomination_service as service
from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from world.ai.fake_client import FakeLLMClient
from world.ai.profiles import default_profiles
from world.ai.title_nomination import register_title_nomination
from world.rules import guild_exams
from world.rules import titles as title_rules
from world.quests import runtime as quest_runtime


def _profiles(**overrides):
    raw = default_profiles()
    for layer, values in overrides.items():
        raw[layer].update(values)
    return raw


def await_result(d):
    result = d.result
    d.addErrback(lambda f: None)
    return result


def _reply(candidates):
    return json.dumps({"candidates": list(candidates)}, ensure_ascii=False)


def _good_client():
    client = FakeLLMClient()
    client.add_response(
        lambda descriptor: True,
        _reply(
            [
                {"display": "火焰之心", "basis": "焚盡匪寨"},
                {"display": "破曉之刃", "basis": "曙間退敵"},
                {"display": "沉默守望", "basis": "夜守村口"},
                {"display": "荒野行者", "basis": "穿林三日"},
                {"display": "月影之舞", "basis": "月下退賊"},
            ]
        ),
    )
    return client


class _NoPush:
    """Patch target recorder for the bounded panel push."""

    def __init__(self):
        self.calls = []

    def __call__(self, entity, watchers):
        self.calls.append((entity, watchers))


class NominationSchedulingTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        # The test runner does not boot the server hooks; install the layer
        # registration the same way at_server_start does (idempotent).
        register_title_nomination()
        self.player = create_object(PlayerCharacter, key="nominee")
        self.push = _NoPush()
        self.push_patcher = patch.object(service, "_push_ballot_panel", self.push)
        self.push_patcher.start()
        self.addCleanup(self.push_patcher.stop)

    def _schedule(self, client, **kwargs):
        with override_settings(LLM_PROFILES=_profiles()):
            deferred = service.schedule_epithet_nomination(
                self.player, client=client, **kwargs
            )
        if deferred is not None:
            await_result(deferred)
        return deferred

    @covers_requirement("title-system::ballot-persistence-acceptance-and-decline-are-rules-layer-writers-only")
    def test_happy_path_persists_and_pushes(self):
        deferred = self._schedule(_good_client(), watchers=(("session", "epoch"),))
        self.assertIsNotNone(deferred)
        self.assertEqual(
            title_rules.safe_pending_ballot(self.player),
            (
                {"display": "火焰之心", "basis": "焚盡匪寨"},
                {"display": "破曉之刃", "basis": "曙間退敵"},
                {"display": "沉默守望", "basis": "夜守村口"},
            ),
        )
        self.assertEqual(self.push.calls, [(self.player, (("session", "epoch"),))])

    @covers_requirement("title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled")
    def test_pending_ballot_suppresses_without_touching_transport(self):
        self.assertTrue(
            title_rules.persist_nomination_ballot(
                self.player, [{"display": "先來", "basis": "一"}]
            )
        )
        client = _good_client()
        self.assertIsNone(self._schedule(client))
        self.assertEqual(client.calls, [])
        self.assertEqual(
            title_rules.safe_pending_ballot(self.player),
            ({"display": "先來", "basis": "一"},),
        )

    @covers_requirement("title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled")
    def test_decline_cooldown_suppresses_then_expires(self):
        self.assertTrue(
            title_rules.persist_nomination_ballot(
                self.player, [{"display": "甲名", "basis": "一"}]
            )
        )
        title_rules.decline_epithet_ballot(self.player)
        client = _good_client()
        self.assertIsNone(self._schedule(client))
        self.assertEqual(client.calls, [])
        # Past the second day boundary the same trigger fires again.
        day = title_rules._DAY_SECONDS
        clock = SimpleNamespace(tick=10 * day)
        with patch("world.rules.titles.get_world_clock", return_value=clock):
            self.assertIsNotNone(self._schedule(_good_client()))

    @covers_requirement("title-system::ballot-persistence-acceptance-and-decline-are-rules-layer-writers-only")
    def test_decline_digest_flows_into_the_prompt(self):
        # The durable decline log is the prompt's soft-learning feed: the
        # declined displays must appear in the next round's user message.
        self.assertTrue(
            title_rules.persist_nomination_ballot(
                self.player, [{"display": "已拒之名", "basis": "一"}]
            )
        )
        title_rules.decline_epithet_ballot(self.player)
        client = _good_client()
        clock = SimpleNamespace(tick=10 * title_rules._DAY_SECONDS)
        with patch("world.rules.titles.get_world_clock", return_value=clock):
            self._schedule(client)
        self.assertEqual(len(client.calls), 1)
        user_text = client.calls[0].messages[1]["content"]
        self.assertIn("已拒之名", user_text)

    def test_push_passes_the_captured_epoch(self):
        # The unpatched push path hands publish_panel_update the epoch
        # captured at trigger time (the coordinator's own guard test pins
        # the mismatch behavior; this pins the wiring). Suspend the
        # class-level push stub first.
        self.push_patcher.stop()
        self.addCleanup(self.push_patcher.start)
        from web.webclient.presentation.context import PresentationContext

        with (
            patch(
                "web.webclient.presentation.coordinator.publish_panel_update",
                return_value=None,
            ) as publish,
            patch(
                "web.webclient.presentation.ingress.build_presentation_context",
                return_value=PresentationContext(
                    actor=self.player, protocol_version=1
                ),
            ),
        ):
            service._push_ballot_panel(self.player, (("session", "epoch-7"),))
        self.assertEqual(publish.call_count, 1)
        self.assertEqual(publish.call_args.kwargs["expected_epoch"], "epoch-7")
        self.assertEqual(publish.call_args.args[0], "session")

    @covers_requirement("title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled")
    def test_accept_never_starts_a_cooldown(self):
        self.assertTrue(
            title_rules.persist_nomination_ballot(
                self.player, [{"display": "甲名", "basis": "一"}]
            )
        )
        title_rules.accept_epithet(self.player, 1)
        self.assertIsNotNone(self._schedule(_good_client()))

    def test_disabled_profile_fires_nothing(self):
        client = _good_client()
        with override_settings(
            LLM_PROFILES=_profiles(title_nomination={"enabled": False})
        ):
            deferred = service.schedule_epithet_nomination(self.player, client=client)
            if deferred is not None:
                await_result(deferred)
        self.assertEqual(title_rules.safe_pending_ballot(self.player), ())
        self.assertEqual(client.calls, [])
        self.assertFalse(self.player.attributes.has(title_rules.PENDING_BALLOT_KEY))

    @covers_requirement("title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled")
    def test_offline_client_builder_yields_no_call(self):
        with override_settings(
            LLM_PROFILES=_profiles(title_nomination={"enabled": False})
        ):
            self.assertIsNone(service.schedule_epithet_nomination(self.player))

    @covers_requirement("title-system::the-nomination-pipeline-is-5-candidates-through-schema-and-collision-filters")
    def test_void_rounds_store_nothing(self):
        cases = ["{not json", _reply([{"display": "甲名", "basis": "一"}])]
        for text in cases:
            with self.subTest(text=text[:16]):
                client = FakeLLMClient()
                client.add_response(lambda descriptor: True, text)
                self._schedule(client)
                self.assertFalse(
                    self.player.attributes.has(title_rules.PENDING_BALLOT_KEY)
                )

    @covers_requirement("title-system::the-nomination-pipeline-is-5-candidates-through-schema-and-collision-filters")
    def test_all_filtered_candidates_store_nothing(self):
        client = FakeLLMClient()
        client.add_response(
            lambda descriptor: True,
            _reply([{"display": "南門新客", "basis": "撞名"}] * 5),
        )
        title_rules.grant_starter_pair(self.player)
        self._schedule(client)
        self.assertFalse(self.player.attributes.has(title_rules.PENDING_BALLOT_KEY))
        self.assertEqual(self.push.calls, [])

    def test_non_player_and_malformed_state_never_raise(self):
        npc = create_object(PlayerCharacter, key="nominee-2")
        npc.attributes.add(title_rules.TITLE_COLLECTION_KEY, "damaged")
        with override_settings(LLM_PROFILES=_profiles()):
            self.assertIsNone(
                service.schedule_epithet_nomination(None, client=_good_client())
            )
            self.assertIsNone(
                service.schedule_epithet_nomination(
                    "not-an-entity", client=_good_client()
                )
            )
            self.assertIsNone(
                service.schedule_epithet_nomination(npc, client=_good_client())
            )

    def test_synchronous_build_failure_is_swallowed(self):
        client = _good_client()
        with (
            override_settings(LLM_PROFILES=_profiles()),
            patch.object(
                service, "_build_context", side_effect=RuntimeError("boom")
            ),
        ):
            self.assertIsNone(
                service.schedule_epithet_nomination(self.player, client=client)
            )


class RestBoundaryTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.player = create_object(PlayerCharacter, key="rest-nominee")

    @covers_requirement("title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled")
    def test_only_day_boundary_events_trigger_scheduling(self):
        crossed = [SimpleNamespace(kind="daily_reset", due_tick=86400, payload={})]
        quiet = [SimpleNamespace(kind="buff_expiry", due_tick=10, payload={})]
        with patch.object(
            service, "schedule_epithet_nomination"
        ) as schedule:
            service.schedule_rest_boundary_nomination(self.player, quiet)
            schedule.assert_not_called()
            service.schedule_rest_boundary_nomination(self.player, crossed)
            self.assertEqual(schedule.call_count, 1)
            self.assertIs(schedule.call_args.args[0], self.player)

    def test_helper_never_raises(self):
        with patch.object(
            service, "schedule_epithet_nomination", side_effect=RuntimeError("boom")
        ):
            service.schedule_rest_boundary_nomination(
                self.player, [SimpleNamespace(kind="daily_reset")]
            )


class ObserverWiringTests(EvenniaTest):
    """Exam/quest observers schedule only after the settlement commits."""

    def setUp(self):
        super().setUp()
        self.player = create_object(PlayerCharacter, key="observed-nominee")

    def test_registration_is_idempotent_and_observers_are_installed(self):
        saved_exam = list(guild_exams._EXAM_PASS_OBSERVERS)
        saved_quest = list(quest_runtime._QUEST_COMPLETION_OBSERVERS)
        self.addCleanup(
            lambda: (
                guild_exams._EXAM_PASS_OBSERVERS.__setitem__(slice(None), saved_exam),
                quest_runtime._QUEST_COMPLETION_OBSERVERS.__setitem__(
                    slice(None), saved_quest
                ),
            )
        )
        service._TRIGGERS_REGISTERED = False
        service.register_nomination_triggers()
        service.register_nomination_triggers()
        self.assertEqual(
            guild_exams._EXAM_PASS_OBSERVERS.count(service._on_exam_pass), 1
        )
        self.assertEqual(
            quest_runtime._QUEST_COMPLETION_OBSERVERS.count(
                service._on_quest_completion
            ),
            1,
        )

    @covers_requirement("title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled")
    def test_observers_defer_to_on_commit(self):
        with patch.object(service, "schedule_epithet_nomination") as schedule:
            with transaction.atomic():
                with self.captureOnCommitCallbacks(execute=False):
                    service._on_exam_pass(self.player, "E")
                    service._on_quest_completion(self.player, object(), object())
            schedule.assert_not_called()
        with patch.object(service, "schedule_epithet_nomination") as schedule:
            with self.captureOnCommitCallbacks(execute=True):
                service._on_exam_pass(self.player, "E")
            self.assertEqual(schedule.call_count, 1)
            self.assertIs(schedule.call_args.args[0], self.player)

    @covers_requirement("title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled")
    def test_rolled_back_transactions_schedule_nothing(self):
        # A settlement whose transaction rolls back never reaches commit, so
        # the on_commit scheduling must not fire for either observer.
        with patch.object(service, "schedule_epithet_nomination") as schedule:
            try:
                with transaction.atomic():
                    service._on_exam_pass(self.player, "E")
                    raise RuntimeError("rollback")
            except RuntimeError:
                pass
            schedule.assert_not_called()
        with patch.object(service, "schedule_epithet_nomination") as schedule:
            try:
                with transaction.atomic():
                    service._on_quest_completion(self.player, object(), object())
                    raise RuntimeError("rollback")
            except RuntimeError:
                pass
            schedule.assert_not_called()
