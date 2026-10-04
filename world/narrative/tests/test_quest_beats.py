"""Synthetic recorded/offline quest-seed generation and publication tests."""

import json
from unittest.mock import patch

from django.test import override_settings

from tools.spec_traceability import covers_requirement
from typeclasses.components import GuildStaff, QuestIssuer
from world.ai.fake_client import FakeLLMClient
from world.ai.scenario_director import QuestBlueprint, register_scenario_director
from world.ai.scenario_director.generation import generate_beat_quest_blueprint, generate_quest_blueprint
from world.narrative.director import attempt_decision, settle_decision, OUTCOME_NO_CONTENT, OUTCOME_STALE
from world.narrative.quest_beats import PreparedQuestBeat, quest_context
from world.narrative.tests.test_story_director_beats import StoryDirectorBeatsTestCase, _recorded
from world.narrative.authoring import save_draft, confirm_draft
from world.narrative.models import ScheduledBeat, StoryThread
from world.quests.generated_quest_store import list_payloads
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.quests.runtime import read_records
from world.quests.tests._compile_helpers import CompileRegistryIsolation, _defeat_payload, _raw
from world.rules.guild import register_adventurer
from world.rules.tests._combat_session_helpers import open_synthetic_scope


class QuestBeatTests(CompileRegistryIsolation, StoryDirectorBeatsTestCase):
    def setUp(self):
        open_synthetic_scope(self, "items", "guild_branches", "archetypes", "anchors", "anchor_placements")
        super().setUp()
        register_scenario_director()
        self.payload = _defeat_payload()
        self.owner.location = self.room1
        self.room1.anchor_key = self.payload["stages"][0]["location_req"]["anchor_key"]
        self.npc.location = self.room1
        self.npc.components.add(GuildStaff.create(self.npc, service_id="test", branch_key=self.payload["issuer"]))
        with patch("world.rules.guild.get_display_value", return_value=100):
            register_adventurer(self.owner, self.npc)

    def recorded(self, payload=None):
        client = _recorded("quest_seed")
        client.add_response(lambda request: request.schema_id == "scenario_director",
                            json.dumps(payload or self.payload, ensure_ascii=False))
        return client

    def prepared(self, invocation=None, proposal=None, payload=None):
        invocation = invocation or self.prepare()
        proposal = proposal or self.proposal("quest_seed")
        context, issuer_id = quest_context(invocation, proposal)
        return PreparedQuestBeat(json.dumps(context, ensure_ascii=False, sort_keys=True),
                                 json.dumps(payload or self.payload, ensure_ascii=False), issuer_id)

    @covers_requirement("narrative-quest-compilation::quest-seed-beats-compile-only-through-existing-owners")
    def test_recorded_publication_and_restart_replay_leave_gameplay_untouched(self):
        selection = self.candidate()
        client = self.recorded()
        with patch("world.narrative.quest_beats.log_info") as info, self.captureOnCommitCallbacks(execute=True):
            first = attempt_decision(self.owner.pk, client=client, quest_client=client,
                                     candidate=selection, now_tick=self.now).result
        self.assertTrue(first.scheduled)
        provenance = first.beat.payload["quest"]
        self.assertIn(provenance["definition_key"], QUEST_DEFINITION_REGISTRY)
        self.assertEqual(provenance["snapshot_id"], first.decision.snapshot_id)
        self.assertEqual(provenance["blueprint"], QuestBlueprint.from_payload(self.payload).to_payload())
        self.assertEqual(read_records(self.owner), [])
        self.assertEqual(len(list_payloads()), 1)
        self.assertEqual(info.call_args.args, ("quest_beat_published",))
        self.assertNotIn("summary", info.call_args.kwargs["context"])
        from world.quests.bootstrap import restore_generated_quests
        from world.quests.compile.registration import (
            GUILD_OFFER_REGISTRY, QUEST_ISSUANCE_REGISTRY, SCENE_REQUIREMENT_REGISTRY,
        )
        for registry in (QUEST_DEFINITION_REGISTRY, GUILD_OFFER_REGISTRY,
                         QUEST_ISSUANCE_REGISTRY, SCENE_REQUIREMENT_REGISTRY):
            registry.clear()
        restore_generated_quests()
        self.assertIn(provenance["definition_key"], QUEST_DEFINITION_REGISTRY)
        # Fresh ORM instance and a client with no recordings represent a restart delivery.
        replay = attempt_decision(self.owner.pk, client=FakeLLMClient(), candidate=selection).result
        self.assertEqual(replay.beat.beat_id, first.beat.beat_id)
        self.assertEqual(len(list_payloads()), 1)
        self.assertEqual(ScheduledBeat.objects.count(), 1)

    def confirmed_request(self):
        draft = save_draft(owner_id=str(self.owner.pk), direction={
            "summary": self.proposal().summary, "themes": [], "atmosphere": [],
            "participants": [], "emphasis": [], "exclusions": [], "kind": "new_story",
            "thread_id": None, "effects": [], "revisions": [],
        }, sources=[], tick=self.now)
        return confirm_draft(draft_id=draft.draft_id, owner_id=str(self.owner.pk), tick=self.now)

    @covers_requirement("story-director-beats::director-schedules-at-most-one-eligible-beat",
                        "narrative-quest-compilation::quest-seed-beats-compile-only-through-existing-owners")
    def test_confirmed_direction_compiles_one_linked_quest(self):
        request = self.confirmed_request()
        client = self.recorded()
        result = attempt_decision(self.owner.pk, client=client, quest_client=client,
                                  request=request).result
        self.assertTrue(result.scheduled)
        self.assertEqual(result.decision.source_ref, request.submission_key)
        self.assertIn("quest", result.beat.payload)
        self.assertEqual(read_records(self.owner), [])

    def test_changed_request_version_cannot_publish_old_snapshot(self):
        from dataclasses import replace
        from world.narrative.director import prepare_decision, resolve_source

        request = self.confirmed_request()
        source = resolve_source(self.owner.pk, request=request)
        invocation = prepare_decision(self.owner.pk, source=source)
        invocation = replace(invocation, source=replace(source, revision=source.revision + 1))
        before = StoryThread.objects.count()
        result = settle_decision(invocation=invocation, proposals=[self.proposal("quest_seed")],
                                 prepared_quest=self.prepared(invocation))
        self.assertEqual(result.outcome, OUTCOME_STALE)
        self.assertEqual(StoryThread.objects.count(), before)
        self.assertEqual(list_payloads(), [])

    @covers_requirement("narrative-quest-compilation::quest-seed-beats-compile-only-through-existing-owners")
    def test_stale_rank_rejects_without_publication(self):
        invocation = self.prepare()
        prepared = self.prepared(invocation)
        self.owner.guild_rank = "E"
        result = settle_decision(invocation=invocation, proposals=[self.proposal("quest_seed")], prepared_quest=prepared)
        self.assertEqual(result.outcome, OUTCOME_STALE)
        self.assertEqual(list_payloads(), [])
        self.assertEqual(ScheduledBeat.objects.count(), 0)

    def assert_stale_change(self, change):
        invocation = self.prepare()
        prepared = self.prepared(invocation)
        change()
        result = settle_decision(invocation=invocation, proposals=[self.proposal("quest_seed")],
                                 prepared_quest=prepared)
        self.assertEqual(result.outcome, OUTCOME_STALE)
        self.assertEqual(list_payloads(), [])
        self.assertEqual(ScheduledBeat.objects.count(), 0)

    def test_changed_anchor_rejects(self):
        self.assert_stale_change(lambda: setattr(self.room1, "anchor_key", None))

    def test_removed_registration_rejects(self):
        self.assert_stale_change(lambda: setattr(self.owner.db, "guild_registration", None))

    def test_changed_thread_rejects(self):
        from world.narrative.threads import record_thread_development
        self.assert_stale_change(lambda: record_thread_development(
            thread_id=self.thread.thread_id, tick=self.now, actor_id=str(self.owner.pk)))

    @covers_requirement("scenario-director::semantic-validators-bound-rank-reward-archetype-npc-tier-and-every-world-reference")
    def test_invalid_scene_reference_cannot_publish(self):
        payload = _defeat_payload()
        payload["stages"][0]["location_req"]["archetype"] = "t_missing_archetype"
        invocation = self.prepare()
        result = settle_decision(invocation=invocation, proposals=[self.proposal("quest_seed")],
                                 prepared_quest=self.prepared(invocation, payload=payload))
        self.assertEqual(result.outcome, OUTCOME_NO_CONTENT)
        self.assertEqual(list_payloads(), [])
        self.assertEqual(ScheduledBeat.objects.count(), 0)

    def test_private_participant_issuer_is_revalidated(self):
        self.npc.components.add(QuestIssuer.create(self.npc))
        proposal = self.proposal("quest_seed", recipient=str(self.npc.pk))
        invocation = self.prepare()
        context, _ = quest_context(invocation, proposal)
        payload = _defeat_payload(issuer=context["issuer_branch"])
        payload["reward"]["merit"] = 0
        prepared = self.prepared(invocation, proposal, payload)
        self.npc.components.remove(self.npc.components.get(QuestIssuer.get_component_slot()))
        result = settle_decision(invocation=invocation, proposals=[proposal], prepared_quest=prepared)
        self.assertEqual(result.outcome, OUTCOME_STALE)
        self.assertEqual(list_payloads(), [])

    def test_forged_prepared_rank_and_issuer_are_rejected_by_owner(self):
        invocation = self.prepare()
        payload = _defeat_payload(rank="E")
        result = settle_decision(invocation=invocation, proposals=[self.proposal("quest_seed")],
                                 prepared_quest=self.prepared(invocation, payload=payload))
        self.assertEqual(result.outcome, OUTCOME_NO_CONTENT)
        self.assertEqual(list_payloads(), [])

    def test_publication_failure_restores_durable_store_and_registries(self):
        invocation = self.prepare()
        before = dict(QUEST_DEFINITION_REGISTRY)
        with patch("world.narrative.threads.record_thread_development", side_effect=ValueError("synthetic failure")):
            with self.assertRaises(ValueError):
                settle_decision(invocation=invocation, proposals=[self.proposal("quest_seed")], prepared_quest=self.prepared(invocation))
        self.assertEqual(list_payloads(), [])
        self.assertEqual(QUEST_DEFINITION_REGISTRY, before)
        self.assertEqual(ScheduledBeat.objects.count(), 0)
        from world.quests.generated_quest_store import get_store
        store = get_store()
        store.attributes.reset_cache()
        self.assertEqual(list_payloads(), [])
        retry = settle_decision(invocation=invocation, proposals=[self.proposal("quest_seed")], prepared_quest=self.prepared(invocation))
        self.assertTrue(retry.scheduled)

    @covers_requirement("scenario-director::the-hand-written-template-pool-provides-offline-quest-generation",
                        "narrative-quest-compilation::beat-context-failure-creates-no-template-replacement",
                        "scenario-director::beat-scoped-blueprint-generation-does-not-substitute-template-filler")
    def test_offline_beat_no_content_generic_template_stays(self):
        context, _ = quest_context(self.prepare(), self.proposal("quest_seed"))
        client = FakeLLMClient()
        with override_settings(LLM_PROFILES=_raw(scenario_director={"enabled": False})), patch(
            "world.ai.scenario_director.generation.get_template_pool", return_value=(QuestBlueprint.from_payload(self.payload),)
        ) as templates:
            self.assertIsNone(generate_beat_quest_blueprint(client, context=context).result)
            templates.assert_not_called()
            self.assertIsInstance(generate_quest_blueprint(client, context=context).result, QuestBlueprint)
        self.assertEqual(client.calls, [])

    @covers_requirement("narrative-quest-compilation::beat-context-failure-creates-no-template-replacement",
                        "scenario-director::beat-scoped-blueprint-generation-does-not-substitute-template-filler")
    def test_misfit_and_exhaustion_never_draw_templates(self):
        context, _ = quest_context(self.prepare(), self.proposal("quest_seed"))
        for payload in ({**self.payload, "rank": "E"}, {"not": "a blueprint"}):
            with self.subTest(payload=payload):
                client = self.recorded(payload)
                with patch("world.ai.scenario_director.generation.get_template_pool", side_effect=AssertionError("no filler")):
                    self.assertIsNone(generate_beat_quest_blueprint(client, context=context).result)
        self.assertEqual(list_payloads(), [])

    @covers_requirement("narrative-quest-compilation::beat-context-failure-creates-no-template-replacement")
    def test_unreachable_generation_keeps_thread_and_creates_no_filler(self):
        client = _recorded("quest_seed")
        client.add_connection_error(lambda request: request.schema_id == "scenario_director")
        revision = self.thread.revision
        with patch("world.ai.scenario_director.generation.get_template_pool", side_effect=AssertionError("no filler")):
            result = attempt_decision(self.owner.pk, client=client, quest_client=client,
                                      candidate=self.candidate()).result
        self.assertEqual(result.outcome, OUTCOME_NO_CONTENT)
        self.thread.refresh_from_db()
        self.assertEqual(self.thread.revision, revision)
        self.assertEqual(list_payloads(), [])
        self.assertEqual(read_records(self.owner), [])

    @covers_requirement("narrative-quest-compilation::beat-context-failure-creates-no-template-replacement")
    def test_disabled_beat_generation_leaves_no_publication(self):
        client = _recorded("quest_seed")
        with override_settings(LLM_PROFILES=_raw(scenario_director={"enabled": False})):
            result = attempt_decision(self.owner.pk, client=client, candidate=self.candidate()).result
        self.assertEqual(result.outcome, OUTCOME_NO_CONTENT)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(list_payloads(), [])

    @covers_requirement("narrative-quest-compilation::quest-seed-beats-compile-only-through-existing-owners")
    def test_completion_prose_cannot_accept_or_progress_a_quest(self):
        from world.ai.story_director import BeatProposal

        proposal = BeatProposal(kind="quest_seed", summary="The quest was already completed.")
        invocation = self.prepare()
        result = settle_decision(invocation=invocation, proposals=[proposal],
                                 prepared_quest=self.prepared(invocation, proposal))
        self.assertTrue(result.scheduled)
        self.assertEqual(read_records(self.owner), [])
        self.assertEqual(self.story_beat_events().count(), 0)

    def test_private_issuer_publication_remains_an_unaccepted_offer(self):
        self.npc.components.add(QuestIssuer.create(self.npc))
        proposal = self.proposal("quest_seed", recipient=str(self.npc.pk))
        invocation = self.prepare()
        context, _ = quest_context(invocation, proposal)
        payload = _defeat_payload(issuer=context["issuer_branch"])
        payload["reward"]["merit"] = 0
        result = settle_decision(invocation=invocation, proposals=[proposal],
                                 prepared_quest=self.prepared(invocation, proposal, payload))
        self.assertTrue(result.scheduled)
        self.assertEqual(result.beat.payload["quest"]["issuer_key"], context["issuer_branch"])
        self.assertEqual(read_records(self.owner), [])

    def test_outer_settlement_failure_restores_quest_publication(self):
        invocation = self.prepare()
        before = dict(QUEST_DEFINITION_REGISTRY)
        with patch("world.narrative.director._announce", side_effect=RuntimeError("outer failure")):
            with self.assertRaises(RuntimeError):
                settle_decision(invocation=invocation, proposals=[self.proposal("quest_seed")],
                                 prepared_quest=self.prepared(invocation))
        self.assertEqual(ScheduledBeat.objects.count(), 0)
        self.assertEqual(list_payloads(), [])
        self.assertEqual(QUEST_DEFINITION_REGISTRY, before)

    def test_default_quest_client_comes_from_its_own_composition_profile(self):
        story_client = _recorded("quest_seed")
        quest_client = self.recorded()
        with patch("server.ai_director_service.build_scenario_director_client",
                   return_value=quest_client) as build:
            result = attempt_decision(self.owner.pk, client=story_client,
                                      candidate=self.candidate()).result
        self.assertTrue(result.scheduled)
        build.assert_called_once_with()
        self.assertEqual(len(story_client.calls), 1)
        self.assertEqual(len(quest_client.calls), 1)
        self.assertEqual(quest_client.calls[0].schema_id, "scenario_director")

    def test_rejection_exception_does_not_log_proposal_prose(self):
        invocation = self.prepare()
        with patch("world.narrative.quest_beats.compile_quest_blueprint",
                   side_effect=ValueError("private proposal sentence")), patch(
            "world.narrative.quest_beats.log_warn"
        ) as warning:
            result = settle_decision(invocation=invocation, proposals=[self.proposal("quest_seed")],
                                     prepared_quest=self.prepared(invocation))
        self.assertEqual(result.outcome, OUTCOME_NO_CONTENT)
        self.assertNotIn("private proposal", str(warning.call_args))
        self.assertIsNone(warning.call_args.kwargs["exc"].__context__)
