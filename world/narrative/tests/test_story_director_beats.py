"""Synthetic behavior tests for deterministic story-director beat settlement.

Everything here is deterministic and offline: synthetic actors, synthetic
provenance rows, ``FakeLLMClient`` recordings, and a fixed clock. No test calls
a live model or image service. The story-director capability's own requirement
ids land at archive sync, so substantive tests are annotated against the
existing canonical main ids they establish.
"""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from django.test import override_settings
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement

from world.ai.fake_client import FakeLLMClient
from world.ai.guardrail import _degrade_fallbacks, _semantic_validators
from world.ai.profiles import default_profiles
from world.ai.schemas.registry import _OUTPUT_SCHEMAS
from world.ai.story_director import BeatProposal, register_story_director
from world.narrative.attention import (
    SOURCE_REQUEST,
    SOURCE_THREAD,
    AttentionCandidate,
    AttentionConfig,
    AttentionContext,
    rank_attention,
)
from world.narrative.authoring import (
    collaborator_creative_brief,
    confirm_draft,
    save_draft,
)
from world.narrative.context import get_context_snapshot
from world.narrative.director import (
    EFFECT_LETTER_SEND,
    EFFECT_NARRATIVE_STATEMENT,
    OUTCOME_CONFLICT,
    OUTCOME_NO_CONTENT,
    OUTCOME_SCHEDULED,
    OUTCOME_STALE,
    OUTCOME_UNAUTHORIZED_WRITE,
    OUTCOME_UNSUPPORTED_EFFECT,
    OUTCOME_UNSUPPORTED_TARGET,
    DirectorSourceError,
    attempt_decision,
    find_decision,
    prepare_decision,
    resolve_source,
    settle_decision,
)
from world.narrative.models import (
    LetterSend,
    NarrativeEvent,
    ScheduledBeat,
    StoryDirectorDecision,
    StoryThread,
    StoryThreadLink,
)
from world.narrative.threads import (
    create_thread,
    get_thread_revision,
    record_thread_development,
)
from world.rules.affinity import AffinitySource, apply_affinity_change
from world.rules.affinity_config import AffinityConfig
from world.rules.clock import get_world_clock

SUMMARY = "嚮導在森林深處留下了新的線索，並邀請你再次同行。"


def _reset_all() -> None:
    _semantic_validators.clear()
    _degrade_fallbacks.clear()
    _OUTPUT_SCHEMAS.clear()


def _recorded(kind="follow_up", summary=SUMMARY, **overrides):
    client = FakeLLMClient()
    payload = {"kind": kind, "summary": summary}
    payload.update(overrides)
    client.add_response(
        lambda descriptor: descriptor.schema_id == "story_director",
        json.dumps(payload, ensure_ascii=False),
    )
    return client


class StoryDirectorBeatsTestCase(EvenniaTest):
    """Shared synthetic actors, one invested thread, and a fixed clock."""

    def setUp(self):
        super().setUp()
        _reset_all()
        register_story_director()
        self.settings = override_settings(LLM_PROFILES=default_profiles())
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        affinity = patch(
            "world.rules.affinity.get_config",
            return_value=AffinityConfig(
                invite_threshold=50,
                daily_interaction_cap=12,
                quest_completion_gain=5,
                friendly_fire_penalty_per_hit=2,
                sexual_forced_penalty=3,
                cap_breaks=(),
                stages=(),
            ),
        )
        affinity.start()
        self.addCleanup(affinity.stop)
        self.owner = create_object(
            "typeclasses.characters.PlayerCharacter", key="故事的旅人"
        )
        self.npc = create_object("typeclasses.npcs.NPC", key="森林嚮導")
        self.other_npc = create_object("typeclasses.npcs.NPC", key="不相關的商人")
        self.clock = get_world_clock()
        self.tick_to(500)
        self.thread = create_thread(
            thread_id="thread-synth",
            origin="event:synthetic:origin",
            participants=[str(self.npc.pk)],
            visible_to=[str(self.owner.pk)],
            tick=500,
            factual_summary="嚮導提到森林深處有一條被遺忘的小徑。",
            unresolved_questions=["小徑通往何處？"],
        )
        self.now = 500

    def tick_to(self, tick):
        self.now = tick
        self.clock._persist(tick)
        self.clock.tick = tick

    def candidate(self, thread_id="thread-synth"):
        candidate = AttentionCandidate(
            candidate_id=f"thread:{thread_id}",
            source_kind=SOURCE_THREAD,
            source_ref=thread_id,
            revision=get_thread_revision(thread_id),
            origin="event:synthetic:attention",
            participants=(str(self.npc.pk),),
            invested=True,
            knowledge=True,
            capability="dialogue",
        )
        decision = rank_attention(
            [candidate],
            AttentionContext(owner_id=str(self.owner.pk), now_tick=self.now),
            AttentionConfig(focus_limit=1),
        )
        return decision.selected[0]

    def prepare(self):
        source = resolve_source(self.owner.pk, candidate=self.candidate())
        return prepare_decision(self.owner.pk, source=source, now_tick=self.now)

    def proposal(self, kind="follow_up", **overrides):
        return BeatProposal(kind=kind, summary=SUMMARY, **overrides)

    def settle(self, proposals, invocation=None):
        return settle_decision(
            invocation=invocation or self.prepare(),
            proposals=proposals,
            now_tick=self.now,
        )

    def story_beat_events(self):
        return NarrativeEvent.objects.filter(event_type="story_beat")


class SingleBeatTests(StoryDirectorBeatsTestCase):
    @covers_requirement("narrative-story-threads::real-linkage-revisions-invalidate-future-context")
    def test_two_competing_proposals_schedule_exactly_one_beat(self):
        outcome = self.settle([self.proposal("follow_up"), self.proposal("clue")])
        self.assertEqual(outcome.outcome, OUTCOME_SCHEDULED)
        self.assertEqual(ScheduledBeat.objects.count(), 1)
        self.assertEqual(outcome.beat.kind, "follow_up")
        self.assertEqual(outcome.beat.effect, EFFECT_NARRATIVE_STATEMENT)
        self.assertEqual(self.story_beat_events().count(), 1)
        # The scheduled development is durably linked to its thread.
        self.assertTrue(
            StoryThreadLink.objects.filter(
                thread=self.thread, source_ref=outcome.beat.execution_ref
            ).exists()
        )

    @covers_requirement("narrative-story-threads::real-linkage-revisions-invalidate-future-context")
    def test_nothing_validates_leaves_the_thread_intact(self):
        revision = get_thread_revision(self.thread.thread_id)
        outcome = self.settle(())
        self.assertEqual(outcome.outcome, OUTCOME_NO_CONTENT)
        self.assertIsNone(outcome.beat)
        self.assertEqual(ScheduledBeat.objects.count(), 0)
        self.assertEqual(self.story_beat_events().count(), 0)
        self.assertEqual(get_thread_revision(self.thread.thread_id), revision)

    @covers_requirement("correspondence-npc-replies::correspondence-cannot-execute-physical-or-quest-actions")
    def test_unsupported_quest_seed_is_rejected_without_placeholder(self):
        revision = get_thread_revision(self.thread.thread_id)
        outcome = self.settle([self.proposal("quest_seed")])
        self.assertEqual(outcome.outcome, OUTCOME_UNSUPPORTED_EFFECT)
        self.assertIsNone(outcome.beat)
        self.assertEqual(ScheduledBeat.objects.count(), 0)
        self.assertEqual(self.story_beat_events().count(), 0)
        self.assertEqual(get_thread_revision(self.thread.thread_id), revision)
        self.assertFalse(
            StoryDirectorDecision.objects.get(decision_id=outcome.decision.decision_id).scheduled
        )

    @covers_requirement("narrative-story-threads::real-linkage-revisions-invalidate-future-context")
    def test_generator_write_claim_is_rejected_and_no_state_changes(self):
        before = (
            self.owner.db.relations_data,
            self.npc.db.relations_data,
            self.owner.db.inventory,
        )
        revision = get_thread_revision(self.thread.thread_id)
        outcome = self.settle([self.proposal(writes=("trait", "quest", "room"))])
        self.assertEqual(outcome.outcome, OUTCOME_UNAUTHORIZED_WRITE)
        self.assertIsNone(outcome.beat)
        self.assertEqual(ScheduledBeat.objects.count(), 0)
        self.assertEqual(self.story_beat_events().count(), 0)
        self.assertEqual(get_thread_revision(self.thread.thread_id), revision)
        self.assertEqual(
            (self.owner.db.relations_data, self.npc.db.relations_data, self.owner.db.inventory),
            before,
        )


class StaleAndConcurrencyTests(StoryDirectorBeatsTestCase):
    @covers_requirement("narrative-story-threads::real-linkage-revisions-invalidate-future-context")
    def test_old_snapshot_conflict_is_rejected_without_partial_state(self):
        invocation = self.prepare()
        record_thread_development(thread_id=self.thread.thread_id, tick=self.now + 1)
        revision = get_thread_revision(self.thread.thread_id)
        outcome = self.settle([self.proposal()], invocation=invocation)
        self.assertEqual(outcome.outcome, OUTCOME_STALE)
        self.assertIsNone(outcome.beat)
        self.assertEqual(ScheduledBeat.objects.count(), 0)
        self.assertEqual(self.story_beat_events().count(), 0)
        self.assertEqual(get_thread_revision(self.thread.thread_id), revision)

    @covers_requirement("narrative-story-threads::real-linkage-revisions-invalidate-future-context")
    def test_same_thread_revision_permits_no_conflicting_arrangement(self):
        revision = get_thread_revision(self.thread.thread_id)
        prior = StoryDirectorDecision.objects.create(
            decision_id="dec_concurrent",
            owner_id=str(self.owner.pk),
            source_kind=SOURCE_THREAD,
            source_ref="thread-other",
            source_revision=1,
            thread_id=self.thread.thread_id,
            thread_revision=revision,
            outcome=OUTCOME_SCHEDULED,
            scheduled=True,
        )
        ScheduledBeat.objects.create(
            beat_id="beat:concurrent",
            decision=prior,
            owner_id=str(self.owner.pk),
            thread=self.thread,
            kind="follow_up",
            effect=EFFECT_NARRATIVE_STATEMENT,
            arrangement_revision=revision,
            payload={"kind": "follow_up", "summary": SUMMARY},
            execution_ref="nbeat:concurrent",
        )
        outcome = self.settle([self.proposal("clue")])
        self.assertEqual(outcome.outcome, OUTCOME_CONFLICT)
        self.assertIsNone(outcome.beat)
        self.assertEqual(ScheduledBeat.objects.count(), 1)
        self.assertEqual(self.story_beat_events().count(), 0)

    @covers_requirement("dream-authoring::explicit-version-confirmation-submits-once")
    def test_repeated_source_after_restart_is_one_beat(self):
        # "The same accepted decision source" is one captured source revision:
        # re-settling that exact identity (a restart replay) deduplicates.
        invocation = self.prepare()
        first = self.settle([self.proposal()], invocation=invocation)
        self.assertEqual(first.outcome, OUTCOME_SCHEDULED)
        second = self.settle([self.proposal("clue")], invocation=invocation)
        self.assertEqual(second.outcome, OUTCOME_SCHEDULED)
        self.assertEqual(second.decision.decision_id, first.decision.decision_id)
        self.assertEqual(second.beat.beat_id, first.beat.beat_id)
        self.assertEqual(ScheduledBeat.objects.count(), 1)
        self.assertEqual(self.story_beat_events().count(), 1)

    def test_attempt_decision_deduplicates_before_generating(self):
        selection = self.candidate()
        client = _recorded()
        first = attempt_decision(
            self.owner.pk, client=client, candidate=selection, now_tick=self.now
        ).result
        second = attempt_decision(
            self.owner.pk, client=client, candidate=selection, now_tick=self.now
        ).result
        self.assertEqual(first.outcome, OUTCOME_SCHEDULED)
        self.assertEqual(second.beat.beat_id, first.beat.beat_id)
        self.assertEqual(ScheduledBeat.objects.count(), 1)
        self.assertEqual(len(client.calls), 1)


class EffectRoutingTests(StoryDirectorBeatsTestCase):
    @covers_requirement("correspondence-npc-replies::correspondence-cannot-execute-physical-or-quest-actions")
    def test_letter_beat_sends_a_narrative_owned_letter(self):
        outcome = self.settle(
            [self.proposal("letter", recipient=str(self.npc.pk))]
        )
        self.assertEqual(outcome.outcome, OUTCOME_SCHEDULED)
        self.assertEqual(outcome.beat.effect, EFFECT_LETTER_SEND)
        letter = LetterSend.objects.get()
        self.assertEqual((letter.sender_id, letter.recipient_id),
                         (str(self.npc.pk), str(self.owner.pk)))
        self.assertEqual(letter.body, SUMMARY)
        self.assertTrue(
            StoryThreadLink.objects.filter(
                thread=self.thread, source_kind="letter", source_ref=letter.source_id
            ).exists()
        )

    @covers_requirement("correspondence-npc-replies::correspondence-cannot-execute-physical-or-quest-actions")
    def test_relationship_proposal_routes_through_the_rules_owner(self):
        self.assertIsNone(self.npc.db.relations_data)
        outcome = self.settle(
            [
                self.proposal(
                    "invitation",
                    recipient=str(self.npc.pk),
                    relation_delta=5,
                )
            ]
        )
        self.assertEqual(outcome.outcome, OUTCOME_SCHEDULED)
        # The rules owner wrote the affinity record; narrative wrote only its
        # own event, and it never touched relations_data itself.
        self.assertEqual(self.npc.relations.affinity_for(self.owner), 5)
        self.assertIsNotNone(self.npc.db.relations_data)
        self.assertEqual(self.story_beat_events().count(), 1)
        self.assertEqual(outcome.beat.execution_ref, self.story_beat_events().get().source_id)

    def test_unavailable_target_rejected_without_partial_state(self):
        cases = (
            self.proposal("letter"),  # no recipient at all
            self.proposal("letter", recipient=str(self.other_npc.pk)),  # not a participant
            self.proposal("invitation", recipient=str(self.owner.pk), relation_delta=3),
        )
        for index, proposal in enumerate(cases):
            with self.subTest(index=index):
                invocation = self.prepare()
                revision = get_thread_revision(self.thread.thread_id)
                outcome = self.settle([proposal], invocation=invocation)
                self.assertEqual(outcome.outcome, OUTCOME_UNSUPPORTED_TARGET)
                self.assertIsNone(outcome.beat)
                self.assertEqual(LetterSend.objects.count(), 0)
                self.assertEqual(ScheduledBeat.objects.count(), 0)
                self.assertEqual(get_thread_revision(self.thread.thread_id), revision)
                # Advance the thread so the next case is a distinct source
                # revision and settles through its own path (a repeated source
                # identity would deduplicate to this case's decision).
                record_thread_development(
                    thread_id=self.thread.thread_id, tick=self.now + index + 1
                )

    def test_relationship_delta_without_a_counterpart_is_rejected(self):
        outcome = self.settle([self.proposal("follow_up", relation_delta=4)])
        self.assertEqual(outcome.outcome, OUTCOME_UNSUPPORTED_TARGET)
        self.assertEqual(self.npc.db.relations_data, None)


class SourceGatingTests(StoryDirectorBeatsTestCase):
    @covers_requirement("narrative-attention::eligibility-precedes-attention-scoring")
    def test_automatic_candidate_cannot_start_an_unrelated_story(self):
        request_candidate = AttentionCandidate(
            candidate_id="request:synthetic",
            source_kind=SOURCE_REQUEST,
            source_ref="synthetic:v1",
            revision=1,
            origin="confirmed_request",
            participants=(str(self.owner.pk),),
            confirmed=True,
            knowledge=True,
            capability="quest",
        )
        selection = rank_attention(
            [request_candidate],
            AttentionContext(owner_id=str(self.owner.pk), now_tick=self.now),
            AttentionConfig(focus_limit=1),
        ).selected[0]
        with self.assertRaises(DirectorSourceError):
            resolve_source(self.owner.pk, candidate=selection)

    def test_exactly_one_source_is_required(self):
        with self.assertRaises(DirectorSourceError):
            resolve_source(self.owner.pk)
        with self.assertRaises(DirectorSourceError):
            resolve_source(self.owner.pk, candidate=self.candidate(), request=object())


class AuthoringBoundaryTests(StoryDirectorBeatsTestCase):
    def _confirmed_new_story_request(self, summary="新故事：灰港的失蹤商隊。"):
        draft = save_draft(
            owner_id=str(self.owner.pk),
            direction={
                "summary": summary,
                "themes": ["失蹤"],
                "atmosphere": [],
                "participants": [],
                "emphasis": [],
                "exclusions": [],
                "kind": "new_story",
                "thread_id": None,
                "effects": [],
                "revisions": [],
            },
            sources=[],
            tick=self.now,
        )
        return confirm_draft(
            draft_id=draft.draft_id, owner_id=str(self.owner.pk), tick=self.now
        )

    @covers_requirement("dream-authoring::explicit-version-confirmation-submits-once")
    def test_confirmed_request_settles_a_new_story_beat(self):
        request = self._confirmed_new_story_request()
        outcome = attempt_decision(
            self.owner.pk, client=_recorded("clue"), request=request, now_tick=self.now
        ).result
        self.assertEqual(outcome.outcome, OUTCOME_SCHEDULED)
        beat = outcome.beat
        # A confirmed new-story request owns its thread: it is created once and
        # the beat hangs off it.
        self.assertEqual(beat.thread.thread_id, f"story:{beat.decision.decision_id}")
        self.assertEqual(beat.thread.origin, f"request:{request.submission_key}")
        self.assertEqual(beat.thread.visible_to, [str(self.owner.pk)])
        self.assertEqual(beat.kind, "clue")
        self.assertEqual(self.story_beat_events().count(), 1)
        # A repeated attempt of the same confirmed version schedules nothing new.
        repeated = attempt_decision(
            self.owner.pk, client=_recorded("clue"), request=request, now_tick=self.now
        ).result
        self.assertEqual(repeated.beat.beat_id, beat.beat_id)
        self.assertEqual(ScheduledBeat.objects.count(), 1)

    @covers_requirement("narrative-story-threads::real-linkage-revisions-invalidate-future-context")
    def test_rejected_new_story_decision_leaves_no_thread_behind(self):
        request = self._confirmed_new_story_request()
        threads_before = StoryThread.objects.count()
        outcome = attempt_decision(
            self.owner.pk,
            client=_recorded("quest_seed"),
            request=request,
            now_tick=self.now,
        ).result
        self.assertEqual(outcome.outcome, OUTCOME_UNSUPPORTED_EFFECT)
        self.assertIsNone(outcome.beat)
        self.assertEqual(StoryThread.objects.count(), threads_before)
        self.assertEqual(outcome.decision.thread_id, "")
        self.assertEqual(ScheduledBeat.objects.count(), 0)
        self.assertEqual(self.story_beat_events().count(), 0)

    @covers_requirement("narrative-story-threads::real-linkage-revisions-invalidate-future-context")
    def test_empty_new_story_decision_creates_no_thread(self):
        request = self._confirmed_new_story_request("新故事：無聲的鐘塔。")
        threads_before = StoryThread.objects.count()
        source = resolve_source(self.owner.pk, request=request)
        invocation = prepare_decision(
            self.owner.pk, source=source, now_tick=self.now
        )
        outcome = settle_decision(
            invocation=invocation, proposals=(), now_tick=self.now
        )
        self.assertEqual(outcome.outcome, OUTCOME_NO_CONTENT)
        self.assertIsNone(outcome.beat)
        self.assertEqual(StoryThread.objects.count(), threads_before)
        self.assertEqual(ScheduledBeat.objects.count(), 0)

    @covers_requirement("narrative-context::generation-retains-an-immutable-source-snapshot")
    def test_existing_story_candidate_settles_an_executable_beat(self):
        invocation = self.prepare()
        snapshot = get_context_snapshot(invocation.snapshot_id)
        self.assertEqual(snapshot.capability, "story_director")
        self.assertEqual(snapshot.prompt_version, "story_director_v1")
        self.assertEqual(snapshot.owner_id, str(self.owner.pk))
        outcome = settle_decision(
            invocation=invocation, proposals=[self.proposal()], now_tick=self.now
        )
        self.assertEqual(outcome.outcome, OUTCOME_SCHEDULED)
        self.assertTrue(outcome.beat.execution_ref)

    @covers_requirement("narrative-context::generation-retains-an-immutable-source-snapshot")
    def test_recorded_generation_end_to_end(self):
        outcome = attempt_decision(
            self.owner.pk, client=_recorded(), candidate=self.candidate(), now_tick=self.now
        ).result
        self.assertEqual(outcome.outcome, OUTCOME_SCHEDULED)
        event = self.story_beat_events().get()
        self.assertEqual(event.content["summary"], SUMMARY)
        self.assertEqual(outcome.beat.execution_ref, event.source_id)


class ContextSeparationTests(StoryDirectorBeatsTestCase):
    @covers_requirement("dream-authoring::creative-discussion-remains-private-authoring-data")
    def test_director_snapshot_is_separate_from_the_collaborator_brief(self):
        draft = save_draft(
            owner_id=str(self.owner.pk),
            direction={
                "summary": "新故事：霧中的燈塔。",
                "themes": ["霧"],
                "atmosphere": [],
                "participants": [],
                "emphasis": [],
                "exclusions": [],
                "kind": "new_story",
                "thread_id": None,
                "effects": [],
                "revisions": [],
            },
            sources=[],
            tick=self.now,
        )
        confirm_draft(draft_id=draft.draft_id, owner_id=str(self.owner.pk), tick=self.now)
        brief = collaborator_creative_brief(str(self.owner.pk))
        self.assertIsNotNone(brief)
        rendered = json.dumps(
            {
                "summary": brief.summary,
                "themes": list(brief.themes),
                "atmosphere": list(brief.atmosphere),
                "emphasis": list(brief.emphasis),
                "exclusions": list(brief.exclusions),
            },
            ensure_ascii=False,
        )
        # The director's private facts never enter the collaborator read model.
        self.assertNotIn("森林深處", rendered)
        self.assertNotIn("小徑", rendered)
        invocation = self.prepare()
        snapshot = get_context_snapshot(invocation.snapshot_id)
        self.assertEqual(snapshot.capability, "story_director")
        self.assertNotEqual(snapshot.capability, "dream_collaborator")
        # The scenario's premise: both capabilities may resolve to one shared
        # deployment endpoint, which still grants no shared history or facts.
        profiles = default_profiles()
        self.assertEqual(
            profiles["story_director"]["base_url"], profiles["narrator"]["base_url"]
        )
        self.assertEqual(
            profiles["story_director"]["model"], profiles["narrator"]["model"]
        )

    @covers_requirement("narrative-context::observability-protects-private-prompt-data")
    def test_boundary_events_carry_ids_only_never_prose(self):
        events = []
        with patch(
            "world.narrative.director.log_info",
            side_effect=lambda event, **kw: events.append((event, kw.get("context"))),
        ), patch(
            "world.narrative.director.log_warn",
            side_effect=lambda event, **kw: events.append((event, kw.get("context"))),
        ), self.captureOnCommitCallbacks(execute=True):
            attempt_decision(
                self.owner.pk,
                client=_recorded(),
                candidate=self.candidate(),
                now_tick=self.now,
            ).result
        names = {event for event, _ in events}
        self.assertIn("story_director_beat_scheduled", names)
        for event, context in events:
            self.assertNotIn("summary", context)
            self.assertNotIn("body", context)
            for value in context.values():
                self.assertNotIn(SUMMARY[:6], str(value))
                self.assertFalse(any("\u4e00" <= char <= "\u9fff" for char in str(value)))

    @covers_requirement("narrative-context::observability-protects-private-prompt-data")
    def test_rejection_events_record_reason_codes_only(self):
        events = []
        with patch(
            "world.narrative.director.log_warn",
            side_effect=lambda event, **kw: events.append((event, kw.get("context"))),
        ), self.captureOnCommitCallbacks(execute=True):
            self.settle([self.proposal("quest_seed")])
        self.assertEqual(events[0][0], "story_director_decision_rejected")
        self.assertEqual(events[0][1]["reason"], OUTCOME_UNSUPPORTED_EFFECT)


if __name__ == "__main__":
    unittest.main()
