from twisted.internet import defer
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
from world.quests.tests._fixtures import QuestRegistryIsolation
from world.narrative.events import record_narrative_event
from world.tests.synthetic_data import SYNTH_STARTER_EPITHET


def _profiles(**overrides):
    raw = default_profiles()
    for layer, values in overrides.items():
        raw[layer].update(values)
    return raw


def _quest_receipt(entity, quest_id="q1", awards=()):
    """The canonical receipt the quest-transition writer hands the observer."""
    from world.quests.runtime import QuestCompletionReceipt

    return QuestCompletionReceipt(
        source_id=f"quest:{quest_id}:completion:{entity.pk}",
        actor=entity,
        actor_id=int(entity.pk),
        quest_id=quest_id,
        definition_key="dk1",
        issuer_key="npc:test_commission",
        objective={"kind": "defeat", "quantity": 1, "stage_index": 0,
                   "destination_room_id": None, "bound_identities": []},
        awards=tuple(awards),
    )


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
                {"display": "火焰之心", "basis": "焚盡匪寨", "source_ids": ["quest:test_001"]},
                {"display": "破曉之刃", "basis": "曙間退敵", "source_ids": ["quest:test_001"]},
                {"display": "沉默守望", "basis": "夜守村口", "source_ids": ["quest:test_001"]},
                {"display": "荒野行者", "basis": "穿林三日", "source_ids": ["quest:test_001"]},
                {"display": "月影之舞", "basis": "月下退賊", "source_ids": ["quest:test_001"]},
            ]
        ),
    )
    return client


def _void_client():
    """A client whose round produces no candidate and therefore no ballot."""
    client = FakeLLMClient()
    client.add_response(lambda descriptor: True, _reply([]))
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
        # The first-claim grant banks whatever the starter seam holds; patch
        # the shared synthetic declaration so a collision candidate can match
        # the banked display without pinning the shipped spelling.
        starter_seam = patch(
            "world.lore.titles.STARTER_EPITHET", SYNTH_STARTER_EPITHET
        )
        starter_seam.start()
        self.addCleanup(starter_seam.stop)
        # The test runner does not boot the server hooks; install the layer
        # registration the same way at_server_start does (idempotent).
        register_title_nomination()
        self.player = create_object(PlayerCharacter, key="nominee")
        self.push = _NoPush()
        self.push_patcher = patch.object(service, "_push_ballot_panel", self.push)
        self.push_patcher.start()
        self.addCleanup(self.push_patcher.stop)
        # Seed an authorized recent deed so the player has eligible material by default
        record_narrative_event(
            source_id="quest:test_001",
            event_type="quest_completion",
            content={"location": {"id": "", "label": ""}, "quest_id": "q1", "definition_key": "dk1", "completed_objective": "obj", "outcome": "completed"},
            participants=[self.player.pk],
            tick=100,
        )
        self.clock = SimpleNamespace(tick=100)
        self.clock_patcher = patch(
            "server.title_nomination_service.read_world_clock", return_value=self.clock
        )
        self.clock_patcher.start()
        self.addCleanup(self.clock_patcher.stop)

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
        with patch("world.rules.titles.ballot.get_world_clock", return_value=clock):
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
        with patch("world.rules.titles.ballot.get_world_clock", return_value=clock):
            self._schedule(client)
        self.assertEqual(len(client.calls), 1)
        user_text = client.calls[0].messages[1]["content"]
        self.assertIn("已拒之名", user_text)

    @covers_requirement("title-system::nomination-prompts-contain-authorized-structured-deeds-and-advisory-identity")
    def test_adult_action_structured_outcome_survives_into_prompt(self):
        # Record an authorized adult deed with field_access, actor, recipients and outcomes
        # along with a private/forbidden field on another participant
        player_pk = str(self.player.pk)
        record_narrative_event(
            source_id="adult:committed_act_001",
            event_type="adult_action",
            content={
                "location": {"id": "", "label": ""},
                "act_key": "synth_touch",
                "act_name": "撫觸測試",
                "player_id": player_pk,
                "actor": {"id": player_pk, "name": "nominee"},
                "recipients": [{"id": "npc_partner", "name": "花語者", "private_feeling": "forbidden_secret_value"}],
                "outcomes": {
                    # One committed settled effect in the admitted shape; an
                    # unsupported effect row fails the whole record closed.
                    "effects": [
                        {
                            "kind": "pleasure_gain",
                            "actor_id": player_pk,
                            "target_id": "npc_partner",
                            "target_name": "花語者",
                            "result": {"amount": 12},
                        }
                    ],
                },
                "field_access": {
                    player_pk: ["actor", "recipients", "physical_effects"],
                },
            },
            participants=[player_pk, "npc_partner"],
            tick=100,
        )
        # Record an unauthorized narrative event (player is not a participant)
        record_narrative_event(
            source_id="adult:unauthorized_act_999",
            event_type="adult_action",
            content={"location": {"id": "", "label": ""}, "act_key": "secret", "outcome": "unauthorized_outcome"},
            participants=["other_person_1", "other_person_2"],
            tick=100,
        )
        client = _good_client()
        self._schedule(client)
        self.assertEqual(len(client.calls), 1)
        user_text = client.calls[0].messages[1]["content"]
        self.assertIn("adult:committed_act_001", user_text)
        self.assertIn("synth_touch", user_text)
        self.assertIn("花語者", user_text)
        # Verify unauthorized event and private forbidden fields never enter the prompt
        self.assertNotIn("unauthorized_outcome", user_text)
        self.assertNotIn("forbidden_secret_value", user_text)

    def test_removal_digest_flows_into_the_prompt(self):
        # The durable removal log is the second soft-learning feed: the
        # removed display must appear in the next round's user message.
        title_rules.bank_epithet(self.player, "苔徑新客", "初次走入苔徑。", 1)
        title_rules.bank_epithet(self.player, "放下之名", "舊事蹟。", 2)
        title_rules.remove_epithet(self.player, "放下之名")
        client = _good_client()
        self._schedule(client)
        self.assertEqual(len(client.calls), 1)
        user_text = client.calls[0].messages[1]["content"]
        self.assertIn("放下之名", user_text)

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

    @covers_requirement("title-system::empty-and-failed-nomination-leave-deterministic-gameplay-intact")
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

    @covers_requirement("title-system::empty-and-failed-nomination-leave-deterministic-gameplay-intact")
    def test_empty_feed_skips_nomination(self):
        # Character with no recorded deeds produces no nomination attempt
        empty_player = create_object(PlayerCharacter, key="empty-nominee")
        client = _good_client()
        with override_settings(LLM_PROFILES=_profiles()):
            deferred = service.schedule_epithet_nomination(empty_player, client=client)
        self.assertIsNone(deferred)
        self.assertEqual(client.calls, [])
        self.assertFalse(empty_player.attributes.has(title_rules.PENDING_BALLOT_KEY))

    @covers_requirement("title-system::nomination-diagnostics-preserve-privacy")
    def test_nomination_diagnostics_preserve_privacy(self):
        with patch("server.title_nomination_service.log_info") as mock_info:
            deferred = self._schedule(_good_client(), trigger="wake")
            self.assertIsNotNone(deferred)
            admitted_calls = [
                call for call in mock_info.call_args_list
                if call.args and call.args[0] == "title_nomination_admitted"
            ]
            self.assertEqual(len(admitted_calls), 1)
            ctx = admitted_calls[0].kwargs.get("context", {})
            self.assertEqual(ctx.get("player"), str(self.player.pk))
            self.assertEqual(ctx.get("trigger"), "wake")
            # The admitted tick is the frozen one, never zero or a later read.
            self.assertEqual(ctx.get("frozen_tick"), 100)
            self.assertEqual(ctx.get("source_count"), 1)
            # Ensure full private deed prose is not in logging context
            for val in ctx.values():
                self.assertNotIn("completed_objective", str(val))

    @covers_requirement("title-system::the-nomination-pipeline-is-5-candidates-through-schema-and-collision-filters")
    def test_void_rounds_store_nothing(self):
        cases = ["{not json", _reply([{"display": "甲名", "basis": "一", "source_ids": ["quest:test_001"]}])]
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
            _reply([{"display": SYNTH_STARTER_EPITHET.display, "basis": "撞名", "source_ids": ["quest:test_001"]}] * 5),
        )
        title_rules.award_first_quest_epithet(self.player, source_id="test:init:first_quest")
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
    """Wake and qualifying quest boundaries trigger scheduling; midnight/exams do not."""

    def _schedule(self, client, **kwargs):
        with override_settings(LLM_PROFILES=_profiles()):
            deferred = service.schedule_epithet_nomination(
                self.player, client=client, **kwargs
            )
        if deferred is not None:
            await_result(deferred)
        return deferred

    def setUp(self):
        super().setUp()
        register_title_nomination()
        self.player = create_object(PlayerCharacter, key="rest-nominee")
        record_narrative_event(
            source_id="quest:test_rest_nominee",
            event_type="quest_completion",
            content={"location": {"id": "", "label": ""}, "quest_id": "q1", "definition_key": "dk1", "completed_objective": "obj", "outcome": "completed"},
            participants=[self.player.pk],
            tick=100,
        )
        self.clock = SimpleNamespace(tick=100)
        self.clock_patcher = patch(
            "server.title_nomination_service.read_world_clock", return_value=self.clock
        )
        self.clock_patcher.start()
        self.addCleanup(self.clock_patcher.stop)
        service.reset_nomination_triggers_for_tests()
        self.addCleanup(service.reset_nomination_triggers_for_tests)

    @covers_requirement("title-system::awakening-admission-observes-committed-player-transitions")
    def test_wake_transition_triggers_scheduling(self):
        with patch.object(service, "schedule_epithet_nomination") as schedule:
            with self.captureOnCommitCallbacks(execute=True):
                service.notify_wake_transition(self.player, occurrence_id="occ:wake:1")
            self.assertEqual(schedule.call_count, 1)
            self.assertIs(schedule.call_args.args[0], self.player)

    @covers_requirement("title-system::awakening-admission-observes-committed-player-transitions")
    def test_live_combat_wake_is_ineligible(self):
        with patch.object(service, "schedule_epithet_nomination") as schedule:
            service.notify_wake_transition(self.player, occurrence_id="occ:wake:combat", in_combat=True)
            schedule.assert_not_called()

    @covers_requirement("title-system::awakening-admission-observes-committed-player-transitions")
    def test_replaying_wake_transition_creates_no_second_attempt(self):
        with patch.object(service, "schedule_epithet_nomination", wraps=service.schedule_epithet_nomination) as schedule:
            # First wake runs
            d1 = service.schedule_epithet_nomination(self.player, occurrence_id="occ:wake:replay:1", client=_good_client())
            # Second replayed wake with same occurrence id must be ignored
            d2 = service.schedule_epithet_nomination(self.player, occurrence_id="occ:wake:replay:1", client=_good_client())
            self.assertIsNone(d2)

    @covers_requirement("title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled")
    def test_replayed_completion_notification_creates_no_second_attempt(self):
        # The occurrence identity is the committed completion's own source id;
        # replaying it after the in-flight slot cleared must still be inert.
        # The first round is deliberately void, so no pending ballot can stand
        # in for the occurrence guard being tested.
        source_id = _quest_receipt(self.player).source_id
        d1 = service.schedule_epithet_nomination(
            self.player, occurrence_id=source_id, source_id=source_id,
            client=_void_client(),
        )
        self.assertIsNotNone(d1)
        await_result(d1)
        self.assertNotIn(str(self.player.pk), service._IN_FLIGHT_PLAYERS)
        self.assertEqual(title_rules.safe_pending_ballot(self.player), ())
        d2 = service.schedule_epithet_nomination(
            self.player, occurrence_id=source_id, source_id=source_id,
            client=_good_client(),
        )
        self.assertIsNone(d2)

    @covers_requirement("title-system::nomination-has-one-in-flight-request-per-player-identity")
    def test_overlapping_wake_and_logout_makes_one_call(self):
        record_narrative_event(
            source_id="quest:in_flight_test",
            event_type="quest_completion",
            content={"location": {"id": "", "label": ""}, "quest_id": "q_in_flight", "definition_key": "dk", "completed_objective": "obj", "outcome": "completed"},
            participants=[self.player.pk],
            tick=100,
        )
        d_unblock = defer.Deferred()
        class BlockingClient:
            def get_response(self, descriptor):
                return d_unblock

        d1 = service.schedule_epithet_nomination(self.player, client=BlockingClient(), trigger="wake")
        self.assertIsNotNone(d1)
        # Concurrent logout while wake is in flight
        d2 = service.schedule_epithet_nomination(self.player, client=_good_client(), trigger="logout")
        self.assertIsNone(d2)

        # Release blocking client
        d_unblock.callback(_reply([{"display": "火焰之心", "basis": "焚盡匪寨", "source_ids": ["quest:test_001"]}]))
        await_result(d1)
        self.assertNotIn(str(self.player.pk), service._IN_FLIGHT_PLAYERS)

    @covers_requirement("title-system::nomination-has-one-in-flight-request-per-player-identity")
    def test_all_failure_paths_release_in_flight_slot(self):
        player_id = str(self.player.pk)

        # 1. Transport error
        client_err = FakeLLMClient()
        client_err.add_timeout(lambda d: True)
        d_err = service.schedule_epithet_nomination(self.player, client=client_err)
        if d_err is not None:
            await_result(d_err)
        self.assertNotIn(player_id, service._IN_FLIGHT_PLAYERS)

        # 2. Disabled profile
        with override_settings(LLM_PROFILES=_profiles(title_nomination={"enabled": False})):
            d_dis = service.schedule_epithet_nomination(self.player)
            self.assertIsNone(d_dis)
        self.assertNotIn(player_id, service._IN_FLIGHT_PLAYERS)

        # 3. Empty feed
        empty_p = create_object(PlayerCharacter, key="empty-release")
        d_empty = service.schedule_epithet_nomination(empty_p, client=_good_client())
        self.assertIsNone(d_empty)
        self.assertNotIn(str(empty_p.pk), service._IN_FLIGHT_PLAYERS)

        # 4. Void output (empty candidates survivor list)
        client_void = FakeLLMClient()
        client_void.add_response(lambda d: True, "{not valid json")
        d_void = service.schedule_epithet_nomination(self.player, client=client_void)
        if d_void is not None:
            await_result(d_void)
        self.assertNotIn(player_id, service._IN_FLIGHT_PLAYERS)

    @covers_requirement("title-system::nomination-has-one-in-flight-request-per-player-identity")
    def test_late_results_cannot_replace_existing_ballot(self):
        d_unblock = defer.Deferred()
        class BlockingClient:
            def get_response(self, descriptor):
                return d_unblock

        d1 = service.schedule_epithet_nomination(self.player, client=BlockingClient(), trigger="wake")
        self.assertIsNotNone(d1)

        # While generation is pending, an existing ballot appears (persisted)
        self.assertTrue(
            title_rules.persist_nomination_ballot(
                self.player, [{"display": "現存稱號", "basis": "先一步落庫"}]
            )
        )

        # Generation completes late
        d_unblock.callback(_reply([{"display": "火焰之心", "basis": "焚盡匪寨", "source_ids": ["quest:test_001"]}]))
        persisted = await_result(d1)
        # Rules writer must reject replacing the ballot
        self.assertFalse(persisted)
        ballot = title_rules.safe_pending_ballot(self.player)
        self.assertEqual(ballot[0]["display"], "現存稱號")

    @covers_requirement("title-system::nomination-has-one-in-flight-request-per-player-identity")
    def test_restart_retains_ballots_without_generation_resumption(self):
        self.assertTrue(
            title_rules.persist_nomination_ballot(
                self.player, [{"display": "存檔稱號", "basis": "持久化"}]
            )
        )
        # Simulate restart
        service.reset_nomination_triggers_for_tests()
        self.assertEqual(len(service._IN_FLIGHT_PLAYERS), 0)
        # Ballot is still intact
        self.assertEqual(title_rules.safe_pending_ballot(self.player)[0]["display"], "存檔稱號")


    @covers_requirement("title-system::immediate-source-suppression-uses-automatic-award-results")
    def test_immediate_source_award_suppression(self):
        from world.rules.titles.awards import AutomaticTitleAward
        player_pk = str(self.player.pk)
        record_narrative_event(
            source_id="quest:award_occ",
            event_type="quest_completion",
            content={"location": {"id": "", "label": ""}, "quest_id": "q_award", "definition_key": "dk", "completed_objective": "obj", "outcome": "completed"},
            participants=[self.player.pk],
            tick=100,
        )
        award_for_player = AutomaticTitleAward(
            source_id="quest:award_occ",
            recipient_id=player_pk,
            kind="fixed",
            title_id="test_title",
            granted_tick=100,
            display_name="測試稱號",
        )
        award_for_other = AutomaticTitleAward(
            source_id="quest:award_occ",
            recipient_id="99999",
            kind="fixed",
            title_id="test_title",
            granted_tick=100,
            display_name="他人稱號",
        )

        # Award for another does not suppress
        res_other = self._schedule(
            _good_client(),
            source_id="quest:award_occ",
            award_results=(award_for_other,),
        )
        self.assertIsNotNone(res_other)
        service._IN_FLIGHT_PLAYERS.clear()

        # Award for player suppresses immediately
        res_player = service.schedule_epithet_nomination(
            self.player,
            client=_good_client(),
            source_id="quest:award_occ",
            award_results=(award_for_player,),
        )
        self.assertIsNone(res_player)


class ObserverWiringTests(EvenniaTest):
    """Wake/quest observers schedule only after the settlement commits."""

    def setUp(self):
        super().setUp()
        register_title_nomination()
        self.player = create_object(PlayerCharacter, key="observed-nominee")
        service.reset_nomination_triggers_for_tests()
        self.addCleanup(service.reset_nomination_triggers_for_tests)

    def test_registration_is_idempotent_and_observers_are_installed(self):
        saved_quest = list(quest_runtime._QUEST_COMPLETION_OBSERVERS)
        from world.rules import fatigue as fatigue_rules
        saved_wake = list(fatigue_rules._WAKE_TRANSITION_OBSERVERS)
        self.addCleanup(
            lambda: (
                fatigue_rules._WAKE_TRANSITION_OBSERVERS.__setitem__(slice(None), saved_wake),
                quest_runtime._QUEST_COMPLETION_OBSERVERS.__setitem__(
                    slice(None), saved_quest
                ),
            )
        )
        service._TRIGGERS_REGISTERED = False
        service.register_nomination_triggers()
        service.register_nomination_triggers()
        self.assertEqual(
            fatigue_rules._WAKE_TRANSITION_OBSERVERS.count(service.notify_wake_transition), 1
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
                    service.notify_wake_transition(self.player, occurrence_id="occ:wake:commit")
                    service._on_quest_completion(_quest_receipt(self.player))
            schedule.assert_not_called()
        with patch.object(service, "schedule_epithet_nomination") as schedule:
            with self.captureOnCommitCallbacks(execute=True):
                service.notify_wake_transition(self.player, occurrence_id="occ:wake:commit2")
            self.assertEqual(schedule.call_count, 1)
            self.assertIs(schedule.call_args.args[0], self.player)

    @covers_requirement("title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled")
    def test_rolled_back_transactions_schedule_nothing(self):
        with patch.object(service, "schedule_epithet_nomination") as schedule:
            try:
                with transaction.atomic():
                    service.notify_wake_transition(self.player, occurrence_id="occ:wake:rollback")
                    raise RuntimeError("rollback")
            except RuntimeError:
                pass
            schedule.assert_not_called()
        with patch.object(service, "schedule_epithet_nomination") as schedule:
            try:
                with transaction.atomic():
                    service._on_quest_completion(_quest_receipt(self.player))
                    raise RuntimeError("rollback")
            except RuntimeError:
                pass
            schedule.assert_not_called()

    @covers_requirement("title-system::epithet-nomination-fires-only-at-rest-points-and-is-throttled")
    def test_owner_receipt_supplies_the_canonical_identity_and_envelope(self):
        # The service never rebuilds the source identity or re-reads the award
        # envelope: it forwards exactly what the quest-transition owner
        # committed, and reuses that identity as the occurrence key so a
        # replayed receipt admits no second attempt.
        receipt = _quest_receipt(self.player, quest_id="q_forward", awards=("awarded",))
        with patch.object(service, "_schedule_after_commit") as schedule:
            service._on_quest_completion(receipt)
        schedule.assert_called_once_with(
            self.player,
            source_id="quest:q_forward:completion:%s" % self.player.pk,
            award_results=("awarded",),
            occurrence_id="quest:q_forward:completion:%s" % self.player.pk,
            trigger="quest_completion",
        )


class TitleNominationSmokeTests(QuestRegistryIsolation, EvenniaTest):
    """Representative offline end-to-end smoke flow through real construction,

    source settlement, committed narrative selection, rendered prompt, fake model
    transport, committed ballot reload, untouched-recipient control, rollback
    injection, accept/decline persistence, and decline-only cooldown.
    """

    def setUp(self):
        super().setUp()
        register_title_nomination()
        self.player = create_object(PlayerCharacter, key="smoke-hero")
        self.untouched = create_object(PlayerCharacter, key="smoke-control")
        self.clock = SimpleNamespace(tick=100)
        self.clock_patcher = patch(
            "server.title_nomination_service.read_world_clock", return_value=self.clock
        )
        self.clock_patcher.start()
        self.addCleanup(self.clock_patcher.stop)
        service.reset_nomination_triggers_for_tests()
        self.addCleanup(service.reset_nomination_triggers_for_tests)

    @covers_requirement("title-system::empty-and-failed-nomination-leave-deterministic-gameplay-intact")
    def test_end_to_end_accomplishment_and_adult_smoke_with_controls(self):
        # 1. Real source settlement: a real quest completion runs through the
        # quest-owned writer, which finalizes the immutable fact together with
        # its award envelope. No narrative row is inserted by hand, and no
        # quest-completed title row is registered, so the deed is eligible.
        from world.quests.definitions import QuestStage
        from world.quests.runtime import fulfill_record
        from world.quests.tests._fixtures import accept, defeat, quest, register
        from world.quests.transitions import apply_quest_log_replacement
        from world.narrative.models import NarrativeEvent

        definition = register(
            quest("smoke_q1", stages=(QuestStage(0, defeat()),))
        )
        completing = accept(self.player, definition)
        with self.captureOnCommitCallbacks(execute=False):
            apply_quest_log_replacement(
                self.player, [fulfill_record(completing, definition)]
            )
        completion_source = (
            f"quest:{completing.quest_id}:completion:{self.player.pk}"
        )
        committed = NarrativeEvent.objects.get(source_id=completion_source)
        self.assertEqual(committed.event_type, "quest_completion")
        # The envelope is the writer's own finalized result set, not a fixture
        # claim: no quest-completed title is registered, so it grants nothing.
        self.assertEqual(committed.content["award_results"], [])

        # Real adult action settlement (authorized outcome for player)
        player_pk = str(self.player.pk)
        record_narrative_event(
            source_id="adult:smoke_act_1",
            event_type="adult_action",
            content={
                "location": {"id": "", "label": ""},
                "act_key": "deep_embrace",
                "act_name": "深情擁抱",
                "player_id": player_pk,
                "actor": {"id": player_pk, "name": "smoke-hero"},
                "recipients": [{"id": "999", "name": "companion"}],
                "outcomes": {
                    "effects": [
                        {
                            "kind": "pleasure_gain",
                            "actor_id": player_pk,
                            "target_id": "999",
                            "target_name": "companion",
                            "result": {"amount": 9},
                        }
                    ],
                },
                "field_access": {
                    player_pk: ["actor", "recipients", "physical_effects"],
                },
            },
            participants=[player_pk, "999"],
            tick=95,
        )

        # 2. Fake external model transport providing valid structured nominations
        fake_client = FakeLLMClient()
        fake_client.add_response(
            lambda descriptor: True,
            _reply([
                {"display": "平寇先鋒", "basis": "率眾平定盜匪寨", "source_ids": [completion_source]},
                {"display": "柔情守護", "basis": "患難中結下深厚羈絆", "source_ids": ["adult:smoke_act_1"]},
                {"display": "夜幕行者", "basis": "夜巡寨口", "source_ids": [completion_source]},
                {"display": "寨破之晨", "basis": "晨曦突入", "source_ids": [completion_source]},
                {"display": "信義之伴", "basis": "相守同行", "source_ids": ["adult:smoke_act_1"]},
            ]),
        )

        # 3. Trigger wake nomination for hero
        with override_settings(LLM_PROFILES=_profiles()):
            with patch.object(service, "_build_nomination_client", return_value=fake_client):
                with self.captureOnCommitCallbacks(execute=True):
                    service.notify_wake_transition(self.player, occurrence_id="occ:smoke:wake:1")

        # 4. Ballot persistence & reload: NO automatic adoption!
        ballot = title_rules.safe_pending_ballot(self.player)
        self.assertEqual(len(ballot), 3)
        self.assertEqual(ballot[0]["display"], "平寇先鋒")
        self.assertEqual(ballot[1]["display"], "柔情守護")
        self.assertEqual(ballot[2]["display"], "夜幕行者")
        # Player has not accepted yet: full title does not contain any of them
        self.assertNotIn("平寇先鋒", title_rules.safe_full_title(self.player))
        self.assertNotIn("柔情守護", title_rules.safe_full_title(self.player))

        # 5. Untouched-recipient control: untouched player has no ballot and no titles
        self.assertEqual(title_rules.safe_pending_ballot(self.untouched), ())
        self.assertEqual(title_rules.safe_full_title(self.untouched), "")

        # 6. Decline flow: decline ballot starts cooldown, does not grant epithet
        title_rules.decline_epithet_ballot(self.player)
        self.assertEqual(title_rules.safe_pending_ballot(self.player), ())
        self.assertTrue(title_rules.nomination_suppressed(self.player, now_tick=100))
        # Day boundaries pass (cooldown is 2 days = 172800 game seconds)
        self.assertFalse(title_rules.nomination_suppressed(self.player, now_tick=100 + 172801))

        # 7. Rollback injection: failure during settlement transaction leaves no deed or title
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                record_narrative_event(
                    source_id="quest:rollback_test",
                    event_type="quest_completion",
                    content={"location": {"id": "", "label": ""}, "quest_id": "rb", "definition_key": "dk", "completed_objective": "o", "outcome": "completed"},
                    participants=[self.player.pk],
                    tick=100,
                )
                raise RuntimeError("simulated rollback")

        self.assertFalse(NarrativeEvent.objects.filter(source_id="quest:rollback_test").exists())


class FrozenAdmissionTickTests(EvenniaTest):
    """The admitted world tick is frozen once and reused by every diagnostic."""

    def setUp(self):
        super().setUp()
        register_title_nomination()
        self.player = create_object(PlayerCharacter, key="frozen-tick-nominee")
        push_patcher = patch.object(service, "_push_ballot_panel", lambda *args: None)
        push_patcher.start()
        self.addCleanup(push_patcher.stop)
        record_narrative_event(
            source_id="quest:test_001",
            event_type="quest_completion",
            content={
                "location": {"id": str(self.player.pk), "label": "frozen tick room"},
                "quest_id": "q1",
                "definition_key": "dk1",
                "completed_objective": "obj",
                "outcome": "completed",
            },
            participants=[self.player.pk],
            tick=100,
        )
        self.clock = SimpleNamespace(tick=100)
        self.clock_reads = 0

        def _read_clock():
            self.clock_reads += 1
            return self.clock

        self.clock_patcher = patch(
            "server.title_nomination_service.read_world_clock",
            side_effect=_read_clock,
        )
        self.clock_patcher.start()
        self.addCleanup(self.clock_patcher.stop)
        service.reset_nomination_triggers_for_tests()
        self.addCleanup(service.reset_nomination_triggers_for_tests)

    def _schedule(self, client, **kwargs):
        with override_settings(LLM_PROFILES=_profiles()):
            deferred = service.schedule_epithet_nomination(
                self.player, client=client, **kwargs
            )
        if deferred is not None:
            await_result(deferred)
        return deferred

    @covers_requirement("title-system::nomination-diagnostics-preserve-privacy")
    def test_admission_and_completion_report_the_frozen_tick(self):
        with patch.object(service, "log_info") as info:
            deferred = self._schedule(_good_client(), trigger="wake")
            self.assertIsNotNone(deferred)
            self.assertTrue(deferred.result)

        self.assertEqual(self.clock_reads, 1)
        events = [call for call in info.call_args_list if call.args]
        names = [call.args[0] for call in events]
        self.assertIn("title_nomination_admitted", names)
        self.assertIn("title_nomination_completed", names)
        admitted = next(
            call.kwargs["context"]
            for call in events
            if call.args[0] == "title_nomination_admitted"
        )
        completed = next(
            call.kwargs["context"]
            for call in events
            if call.args[0] == "title_nomination_completed"
        )
        self.assertEqual(admitted["frozen_tick"], 100)
        self.assertEqual(completed["frozen_tick"], 100)
        self.assertEqual(admitted["source_count"], 1)
        self.assertEqual(completed["source_count"], 1)
        self.assertEqual(completed["candidate_count"], 3)
        self.assertTrue(completed["persisted"])
        self.assertTrue(title_rules.safe_pending_ballot(self.player))

    @covers_requirement("title-system::nomination-diagnostics-preserve-privacy")
    def test_explicit_tick_reads_no_clock(self):
        deferred = self._schedule(_good_client(), frozen_tick=100)
        self.assertIsNotNone(deferred)
        self.assertEqual(self.clock_reads, 0)
        self.assertTrue(title_rules.safe_pending_ballot(self.player))

    @covers_requirement("title-system::nomination-diagnostics-preserve-privacy")
    def test_clock_advancing_during_generation_keeps_the_admitted_window(self):
        clock = self.clock
        day = title_rules._DAY_SECONDS

        class AdvancingClient:
            def get_response(self, descriptor):
                # Gameplay time advances while the model round is pending.
                clock.tick = 40 * day
                return defer.succeed(
                    _reply(
                        [
                            {
                                "display": "火焰之心",
                                "basis": "焚盡匪寨",
                                "source_ids": ["quest:test_001"],
                            }
                        ]
                        * 5
                    )
                )

        with patch.object(service, "log_info") as info:
            deferred = service.schedule_epithet_nomination(
                self.player, client=AdvancingClient(), trigger="wake"
            )
            self.assertIsNotNone(deferred)
            await_result(deferred)

        self.assertEqual(self.clock_reads, 1)
        completed = next(
            call.kwargs["context"]
            for call in info.call_args_list
            if call.args and call.args[0] == "title_nomination_completed"
        )
        self.assertEqual(completed["frozen_tick"], 100)
        # The citation resolves only inside the admitted two-day window; a
        # recalculated window would have eliminated every candidate.
        self.assertTrue(title_rules.safe_pending_ballot(self.player))

    @covers_requirement("title-system::nomination-diagnostics-preserve-privacy")
    def test_generation_failure_reports_the_frozen_tick(self):
        with (
            patch(
                "world.ai.title_nomination.generate_epithet_candidates",
                side_effect=RuntimeError("model transport failed"),
            ),
            patch.object(service, "log_warn") as warn,
        ):
            deferred = service.schedule_epithet_nomination(
                self.player, client=_good_client(), trigger="wake"
            )
            self.assertIsNotNone(deferred)
            await_result(deferred)

        failures = [
            call
            for call in warn.call_args_list
            if call.args and call.args[0] == "title_nomination_generation_failed"
        ]
        self.assertEqual(len(failures), 1)
        context = failures[0].kwargs["context"]
        self.assertEqual(context["frozen_tick"], 100)
        self.assertEqual(context["trigger"], "wake")
        self.assertEqual(context["player"], str(self.player.pk))
        self.assertEqual(context["source_count"], 1)
        self.assertFalse(title_rules.safe_pending_ballot(self.player))
        self.assertFalse(title_rules.nomination_suppressed(self.player, 100))
        self.assertNotIn(str(self.player.pk), service._IN_FLIGHT_PLAYERS)

    @covers_requirement("title-system::nomination-diagnostics-preserve-privacy")
    def test_persistence_failure_reports_the_frozen_tick(self):
        with (
            patch(
                "world.rules.titles.persist_nomination_ballot",
                side_effect=RuntimeError("ballot write failed"),
            ),
            patch.object(service, "log_warn") as warn,
        ):
            deferred = service.schedule_epithet_nomination(
                self.player, client=_good_client(), trigger="logout"
            )
            self.assertIsNotNone(deferred)
            await_result(deferred)

        failures = [
            call
            for call in warn.call_args_list
            if call.args and call.args[0] == "title_nomination_generation_failed"
        ]
        self.assertEqual(len(failures), 1)
        context = failures[0].kwargs["context"]
        self.assertEqual(context["frozen_tick"], 100)
        self.assertEqual(context["trigger"], "logout")
        self.assertEqual(context["source_count"], 1)
        self.assertFalse(title_rules.safe_pending_ballot(self.player))
        self.assertFalse(title_rules.nomination_suppressed(self.player, 100))
        self.assertNotIn(str(self.player.pk), service._IN_FLIGHT_PLAYERS)

    @covers_requirement("title-system::empty-and-failed-nomination-leave-deterministic-gameplay-intact")
    def test_unavailable_clock_ends_the_workflow_without_side_effects(self):
        client = _good_client()
        title_state_before = title_rules.read_title_state(self.player)
        with (
            patch(
                "server.title_nomination_service.read_world_clock",
                return_value=None,
            ),
            patch.object(service, "log_warn") as warn,
        ):
            deferred = service.schedule_epithet_nomination(self.player, client=client)

        self.assertIsNone(deferred)
        self.assertEqual(client.calls, [])
        self.assertFalse(self.player.attributes.has(title_rules.PENDING_BALLOT_KEY))
        self.assertFalse(title_rules.nomination_suppressed(self.player, 100))
        self.assertNotIn(str(self.player.pk), service._IN_FLIGHT_PLAYERS)
        self.assertEqual(title_rules.read_title_state(self.player), title_state_before)
        unavailable = [
            call
            for call in warn.call_args_list
            if call.args and call.args[0] == "title_nomination_clock_unavailable"
        ]
        self.assertEqual(len(unavailable), 1)
