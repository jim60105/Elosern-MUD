"""Synthetic behavior tests for story thread lifecycle, linkage, and revisions.

Everything here is deterministic and offline: synthetic actors, synthetic
provenance rows, no model or image service. Delta-only requirement ids land at
archive sync, so substantive tests are annotated against the existing canonical
main ids they establish.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement

from world.ai.profiles import LLMProfile
from world.narrative.context import (
    assemble_narrative_context,
    build_budget_profile,
    get_context_snapshot,
    persist_context_snapshot,
)
from world.narrative.correspondence import send_letter
from world.narrative.dialogue import submit_turn
from world.narrative.events import record_narrative_event
from world.narrative.memory import get_owner_memories, record_memory
from world.narrative.models import (
    DialogueTurn,
    NarrativeEvent,
    StoryThread,
    StoryThreadLink,
    StoryThreadRevision,
)
from world.narrative.recall import fast_recall
from world.narrative.threads import (
    NarrativeThreadAccessError,
    NarrativeThreadCommitmentError,
    NarrativeThreadError,
    NarrativeThreadSourceError,
    NarrativeThreadStateError,
    abandon_thread,
    apply_inactivity,
    create_thread,
    establish_commitment,
    get_thread,
    link_dialogue_turn_to_thread,
    link_event_to_thread,
    link_letter_to_thread,
    link_memory_to_thread,
    link_quest_to_thread,
    link_thread_source,
    link_thread_statement,
    note_thread_quest_completion,
    revise_thread_facts,
    transition_thread,
)
from world.rules.clock import get_world_clock


def _llm_profile() -> LLMProfile:
    return LLMProfile(
        base_url="http://127.0.0.1:11434",
        path="/v1/chat/completions",
        headers={"Content-Type": ("application/json",)},
        model="test-model",
        temperature=0.7,
        max_tokens=250,
        timeout_seconds=60,
        max_retries=2,
        supports_response_format=False,
        enabled=True,
    )


class StoryThreadTestCase(EvenniaTest):
    """Shared synthetic actors, a fixed clock, and helper builders."""

    def setUp(self):
        super().setUp()
        self.owner = create_object(
            "typeclasses.characters.PlayerCharacter",
            key="Synthetic thread owner",
            location=self.room1,
        )
        self.other = create_object(
            "typeclasses.characters.PlayerCharacter", key="Synthetic other owner"
        )
        self.npc = create_object("typeclasses.npcs.NPC", key="Synthetic thread npc")
        self.clock = get_world_clock()
        self.clock._persist(100)
        self.clock.tick = 100

    def create_owner_thread(self, thread_id: str, **overrides):
        kwargs = dict(
            thread_id=thread_id,
            origin=f"event:synthetic:{thread_id}:origin",
            participants=[str(self.owner.pk), str(self.npc.pk)],
            tick=100,
        )
        kwargs.update(overrides)
        return create_thread(**kwargs)


class StoryThreadLifecycleTests(StoryThreadTestCase):
    """Facts stay separate from plans; inactivity and quests never resolve a thread."""

    @covers_requirement(
        "narrative-memory::revision-history-remains-recoverable",
        "narrative-memory::cognition-is-owner-scoped-and-provenance-preserving",
    )
    def test_facts_and_plans_stay_separate_with_recoverable_revisions(self):
        """Facts (summary + committed gameplay) never absorb plans or open questions."""
        thread = self.create_owner_thread(
            "thread_barrel_01",
            factual_summary="護送商隊抵達驛站。",
            unresolved_questions=["誰搬走了貨物？"],
            proposed_plans=["下週再訪驛站。"],
        )
        self.assertEqual(thread.state, "active")
        self.assertEqual(thread.revision, 1)
        self.assertEqual(thread.commitments, [])
        self.assertEqual(thread.unresolved_questions, ["誰搬走了貨物？"])
        self.assertEqual(thread.proposed_plans, ["下週再訪驛站。"])
        self.assertEqual(thread.development_ticks, [100])

        record_narrative_event(
            source_id="synthetic:thread:protect:1",
            event_type="encounter_protection",
            content={"encounter_outcome": "victory"},
            participants=[self.owner.pk, self.npc.pk],
            tick=100,
        )
        thread = establish_commitment(
            thread_id="thread_barrel_01",
            source_event_id="synthetic:thread:protect:1",
            text="已答應護送尤漢娜返家。",
            tick=101,
        )
        self.assertEqual(thread.commitments, ["已答應護送尤漢娜返家。"])
        self.assertIn("護送商隊抵達驛站。", thread.factual_summary)
        self.assertEqual(thread.unresolved_questions, ["誰搬走了貨物？"])

        # Replaying an identical commitment is not an effective change.
        replayed_revision = get_thread("thread_barrel_01").revision
        establish_commitment(
            thread_id="thread_barrel_01",
            source_event_id="synthetic:thread:protect:1",
            text="已答應護送尤漢娜返家。",
            tick=101,
        )
        self.assertEqual(get_thread("thread_barrel_01").revision, replayed_revision)

        revision = revise_thread_facts(
            thread_id="thread_barrel_01",
            unresolved_questions=["貨物是誰搬走的？"],
            proposed_plans=["在市集日再訪。", "下週再訪驛站。"],
            tick=102,
        )
        self.assertEqual(revision, 3)

        stored = get_thread("thread_barrel_01")
        self.assertEqual(stored.commitments, ["已答應護送尤漢娜返家。"])
        self.assertNotIn("下週再訪驛站。", stored.commitments)
        history = list(
            StoryThreadRevision.objects.filter(thread=stored)
            .order_by("revision_number")
            .values_list("revision_number", "operation")
        )
        self.assertEqual(
            history,
            [(1, "created"), (2, "commitment_established"), (3, "revised")],
        )

    @covers_requirement("narrative-memory::revision-history-remains-recoverable")
    def test_thread_rows_are_immutable_and_append_only(self):
        """Durable thread, link, and revision rows reject mutation and deletion."""
        thread = self.create_owner_thread("thread_immutable_01")
        memory, _, _ = record_memory(
            owner_id=str(self.owner.pk),
            content={"summary": "不可變更的合成記憶。"},
            tick=100,
            source_id="synthetic:thread:immutable:memory:1",
        )
        link_memory_to_thread(record=memory, thread_id="thread_immutable_01", tick=100)

        with self.assertRaises(ValueError):
            StoryThread.objects.filter(pk=thread.pk).delete()
        with self.assertRaises(ValueError):
            StoryThread.objects.filter(pk=thread.pk).update(state="resolved")
        with self.assertRaises(ValueError):
            StoryThreadLink.objects.filter(thread=thread).delete()
        with self.assertRaises(ValueError):
            StoryThreadRevision.objects.filter(thread=thread).update(operation="edited")

        thread.origin = "event:synthetic:rewritten:origin"
        with self.assertRaises(ValueError):
            thread.save()

    @covers_requirement("narrative-memory::cognition-is-owner-scoped-and-provenance-preserving")
    def test_quest_completion_never_resolves_the_parent_thread(self):
        """Scenario: quest completes with open questions while the thread stays open."""
        self.create_owner_thread(
            "thread_quest_01",
            unresolved_questions=["委託人為何沉默？"],
        )
        link_quest_to_thread(
            thread_id="thread_quest_01", quest_id="quest_synthetic_deliver", tick=100
        )
        before = get_thread("thread_quest_01").revision

        after = note_thread_quest_completion(
            thread_id="thread_quest_01", quest_id="quest_synthetic_deliver", tick=140
        )
        self.assertEqual(after.state, "active")
        self.assertEqual(after.unresolved_questions, ["委託人為何沉默？"])
        self.assertGreater(after.revision, before)
        completed_link = StoryThreadLink.objects.get(
            thread=after, source_kind="quest", relation="quest_completion"
        )
        self.assertEqual(completed_link.source_ref, "quest_synthetic_deliver")

        # Replay is idempotent: no new revision, still no automatic resolution.
        revision = get_thread("thread_quest_01").revision
        note_thread_quest_completion(
            thread_id="thread_quest_01", quest_id="quest_synthetic_deliver", tick=141
        )
        self.assertEqual(get_thread("thread_quest_01").revision, revision)
        self.assertEqual(get_thread("thread_quest_01").state, "active")

        # An unlinked quest identity cannot be noted as completed.
        with self.assertRaises(NarrativeThreadSourceError):
            note_thread_quest_completion(
                thread_id="thread_quest_01", quest_id="quest_unknown", tick=140
            )

    @covers_requirement("narrative-memory::revision-history-remains-recoverable")
    def test_long_inactivity_dormants_but_never_abandons(self):
        """Scenario: long inactivity alone is not proof of abandonment."""
        self.create_owner_thread("thread_idle_01")

        self.assertFalse(
            apply_inactivity(
                thread_id="thread_idle_01", current_tick=150, dormant_after_ticks=100
            )
        )
        self.assertTrue(
            apply_inactivity(
                thread_id="thread_idle_01", current_tick=250, dormant_after_ticks=100
            )
        )
        self.assertEqual(get_thread("thread_idle_01").state, "dormant")

        # Even extreme further inactivity cannot abandon it.
        self.assertFalse(
            apply_inactivity(
                thread_id="thread_idle_01", current_tick=999_999, dormant_after_ticks=100
            )
        )
        self.assertEqual(get_thread("thread_idle_01").state, "dormant")

        # Recent development resets dormancy, and abandonment needs a stated reason.
        revise_thread_facts(thread_id="thread_idle_01", factual_summary="新的進展。", tick=1_000_000)
        self.assertFalse(
            apply_inactivity(
                thread_id="thread_idle_01", current_tick=1_000_050, dormant_after_ticks=100
            )
        )
        with self.assertRaises(NarrativeThreadStateError):
            abandon_thread(thread_id="thread_idle_01", tick=1_000_100)
        abandon_thread(thread_id="thread_idle_01", tick=1_000_100, reason="作者明確結束此線。")
        self.assertEqual(get_thread("thread_idle_01").state, "abandoned")

        # Terminal states accept no further lifecycle change.
        with self.assertRaises(NarrativeThreadStateError):
            transition_thread(
                thread_id="thread_idle_01", new_state="active", reason="revive", tick=1_000_200
            )

    @covers_requirement("narrative-memory::revision-history-remains-recoverable")
    def test_duplicate_creation_and_invalid_transitions_are_typed_errors(self):
        self.create_owner_thread("thread_duplicate_01")
        with self.assertRaises(NarrativeThreadError):
            self.create_owner_thread("thread_duplicate_01")
        with self.assertRaises(NarrativeThreadStateError):
            transition_thread(
                thread_id="thread_duplicate_01", new_state="haunting", reason="", tick=100
            )
        with self.assertRaises(NarrativeThreadStateError):
            transition_thread(
                thread_id="thread_duplicate_01", new_state="active", reason="no-op", tick=100
            )


class StoryThreadLinkageTests(StoryThreadTestCase):
    """Real cross-channel linkage, provenance, and statement/commitment separation."""

    @covers_requirement(
        "narrative-memory::cognition-is-owner-scoped-and-provenance-preserving",
        "correspondence-memory::letters-preserve-claims-and-channel-provenance",
    )
    def test_correspondence_willingness_links_as_statement_not_commitment(self):
        """Scenario: letter willingness is linked as speech/plan, never a commitment."""
        self.create_owner_thread("thread_letters_01")
        letter = send_letter(
            sender_id=self.npc.pk,
            recipient_id=self.owner.pk,
            body="我願意在下個市集日與你同行。",
            source_id="synthetic:letter:willing:1",
        )
        link = link_thread_statement(
            thread_id="thread_letters_01",
            source_kind="letter",
            source_ref=letter.source_id,
            tick=100,
        )
        self.assertEqual(link.relation, "statement")
        self.assertEqual(link.source_ref, "synthetic:letter:willing:1")
        self.assertEqual(get_thread("thread_letters_01").commitments, [])

        # The delivery occurrence is a statement channel: it cannot commit anyone.
        record_narrative_event(
            source_id="correspondence:synthetic:letter:willing:1:delivered",
            event_type="correspondence_delivery",
            content={"letter_source_id": letter.source_id, "status": "delivered"},
            participants=[str(self.npc.pk), str(self.owner.pk)],
            tick=100,
            visibility="private",
        )
        with self.assertRaises(NarrativeThreadCommitmentError):
            establish_commitment(
                thread_id="thread_letters_01",
                source_event_id="correspondence:synthetic:letter:willing:1:delivered",
                text="同意同行。",
                tick=100,
            )
        self.assertEqual(get_thread("thread_letters_01").commitments, [])

    @covers_requirement("correspondence-memory::letters-preserve-claims-and-channel-provenance")
    def test_every_statement_channel_is_rejected_as_a_commitment_source(self):
        """The statement-channel deny list is enforced per channel, not by shape."""
        self.create_owner_thread("thread_channels_01")
        statement_channels = (
            "claim_receipt",
            "correspondence_delivery",
            "correspondence_read",
            "private_authoring",
        )
        for index, event_type in enumerate(statement_channels):
            with self.subTest(event_type=event_type):
                source_id = f"synthetic:thread:channel:{index}"
                record_narrative_event(
                    source_id=source_id,
                    event_type=event_type,
                    content={"statement": "合成聲明。"},
                    participants=[self.owner.pk],
                    tick=100,
                    visibility="private",
                )
                with self.assertRaises(NarrativeThreadCommitmentError):
                    establish_commitment(
                        thread_id="thread_channels_01",
                        source_event_id=source_id,
                        text=f"由 {event_type} 建立的承諾。",
                        tick=100,
                    )
        self.assertEqual(get_thread("thread_channels_01").commitments, [])

    @covers_requirement("narrative-memory::cognition-is-owner-scoped-and-provenance-preserving")
    def test_real_linkage_across_channels_preserves_durable_provenance(self):
        """Events, letters, dialogue turns, and memories link by durable identity."""
        self.create_owner_thread("thread_links_01")
        event, _, _ = record_narrative_event(
            source_id="synthetic:thread:links:event:1",
            event_type="encounter_protection",
            content={"encounter_outcome": "victory"},
            participants=[self.owner.pk, self.npc.pk],
            tick=100,
        )
        letter = send_letter(
            sender_id=self.npc.pk,
            recipient_id=self.owner.pk,
            body="合成書信內容。",
            source_id="synthetic:thread:links:letter:1",
        )
        submission_id = submit_turn(self.npc, self.owner, "合成對話內容。")
        turn = DialogueTurn.objects.get(submission_id=submission_id, kind="player")
        memory, _, _ = record_memory(
            owner_id=str(self.npc.pk),
            content={"summary": "與商隊有關的合成記憶。"},
            tick=100,
            source_id="synthetic:thread:links:memory:1",
        )

        link_event_to_thread(thread_id="thread_links_01", event=event, tick=100)
        link_letter_to_thread(thread_id="thread_links_01", letter=letter, tick=100)
        link_dialogue_turn_to_thread(thread_id="thread_links_01", turn=turn, tick=100)
        link_memory_to_thread(record=memory, thread_id="thread_links_01", tick=100)

        thread = get_thread("thread_links_01")
        self.assertEqual(
            sorted(thread.links.values_list("source_kind", flat=True)),
            ["dialogue", "event", "letter", "memory"],
        )
        self.assertEqual(thread.memory_references, [f"mem:{memory.pk}"])
        self.assertEqual(
            StoryThreadLink.objects.get(
                thread=thread, source_kind="event"
            ).provenance,
            {"event_type": "encounter_protection"},
        )
        self.assertEqual(
            get_owner_memories(owner_id=str(self.npc.pk))[0].relations["thread_id"],
            "thread_links_01",
        )

        # Repeat links are idempotent: the revision must not advance again.
        revision = get_thread("thread_links_01").revision
        link_event_to_thread(thread_id="thread_links_01", event=event, tick=100)
        link_memory_to_thread(record=memory, thread_id="thread_links_01", tick=100)
        self.assertEqual(get_thread("thread_links_01").revision, revision)

        # Unknown sources and invalid shapes are rejected, not silently stored.
        with self.assertRaises(NarrativeThreadSourceError):
            link_event_to_thread(
                thread_id="thread_links_01",
                event=NarrativeEvent(source_id="synthetic:thread:links:missing:1", event_type="x"),
                tick=100,
            )
        with self.assertRaises(NarrativeThreadSourceError):
            link_thread_statement(
                thread_id="thread_links_01",
                source_kind="event",
                source_ref="synthetic:thread:links:event:1",
                tick=100,
            )
        with self.assertRaises(NarrativeThreadCommitmentError):
            link_thread_source(
                thread_id="thread_links_01",
                source_kind="event",
                source_ref="synthetic:thread:links:event:1",
                relation="commitment",
                tick=100,
            )

    @covers_requirement("narrative-fast-recall::permissions-and-explicit-scope-precede-recall-scoring")
    def test_inaccessible_thread_content_never_enters_recall(self):
        """Scenario: requested thread is private -> no private thread content enters recall."""
        create_thread(
            thread_id="thread_private_02",
            origin="event:synthetic:thread:private:origin",
            participants=[str(self.other.pk)],
            visible_to=[str(self.other.pk)],
            tick=100,
        )
        memory, _, _ = record_memory(
            owner_id=str(self.other.pk),
            content={"summary": "私人合成記憶的商隊內容。"},
            tick=100,
            tier="core",
            salience=90,
            source_id="synthetic:thread:private:memory:1",
        )
        link_memory_to_thread(record=memory, thread_id="thread_private_02", tick=100)

        # The permitted owner reads the thread-scoped cognition.
        allowed = fast_recall(
            owner_id=str(self.other.pk),
            requester_id=str(self.other.pk),
            query="私人合成記憶的商隊內容",
            thread_id="thread_private_02",
        )
        self.assertTrue(allowed.all_selected)

        # A different owner gets nothing: the ACL gate runs before ranking.
        denied = fast_recall(
            owner_id=str(self.owner.pk),
            requester_id=str(self.owner.pk),
            query="私人合成記憶的商隊內容",
            thread_id="thread_private_02",
        )
        self.assertEqual(denied.all_selected, ())
        self.assertEqual(denied.thread_revision, 0)

        # Even direct linking by an unauthorized actor is refused.
        with self.assertRaises(NarrativeThreadAccessError):
            link_event_to_thread(
                thread_id="thread_private_02",
                event=NarrativeEvent(source_id="synthetic:thread:private:event:1", event_type="x"),
                actor_id=str(self.owner.pk),
                tick=100,
            )


class StoryThreadRevisionTests(StoryThreadTestCase):
    """Thread revisions invalidate future context while history keeps its read."""

    @covers_requirement("narrative-context::generation-retains-an-immutable-source-snapshot")
    def test_thread_revision_change_after_capture_keeps_historical_read_revision(self):
        """Scenario: thread linkage/summary changes after capture."""
        self.create_owner_thread(
            "thread_rev_01", factual_summary="初始合成事實摘要。"
        )
        memory, _, _ = record_memory(
            owner_id=str(self.owner.pk),
            content={"summary": "與商隊有關的合成記憶內容。"},
            tick=100,
            category="observation",
            tier="working",
            salience=3,
            knowledge_scope="witnessed",
            confidence=1.0,
            source_id="synthetic:thread:rev:memory:1",
        )
        link_memory_to_thread(record=memory, thread_id="thread_rev_01", tick=100)
        link_revision = get_thread("thread_rev_01").revision
        self.assertEqual(link_revision, 2)

        budget = build_budget_profile(
            _llm_profile(), context_window=2000, deep_recall_reservation=300, safety_margin=100
        )

        def assemble():
            return assemble_narrative_context(
                capability="npc_dialogue",
                prompt_version="v1",
                owner_id=str(self.owner.pk),
                requester_id=str(self.owner.pk),
                budget_profile=budget,
                global_rules="規則：繁體中文。",
                capability_contract="契約：日常對話。",
                character_anchor="人物：合成。",
                recalled_memories=get_owner_memories(owner_id=str(self.owner.pk)),
                thread_id="thread_rev_01",
            )

        first = assemble()
        self.assertEqual(first.thread_id, "thread_rev_01")
        self.assertEqual(first.thread_revision, link_revision)
        source = next(s for s in first.sources if s.source_id == "synthetic:thread:rev:memory:1")
        self.assertEqual(source.thread_revision, link_revision)

        snapshot = persist_context_snapshot(first)
        self.assertEqual(
            get_context_snapshot(snapshot.snapshot_id).thread_revisions,
            {"thread_rev_01": link_revision},
        )
        persisted_source = next(
            row
            for row in get_context_snapshot(snapshot.snapshot_id).sources
            if row["source_id"] == "synthetic:thread:rev:memory:1"
        )
        self.assertEqual(persisted_source["thread_revision"], link_revision)

        # An effective thread change advances the revision...
        new_revision = revise_thread_facts(
            thread_id="thread_rev_01", factual_summary="更新後的合成事實摘要。", tick=120
        )
        self.assertEqual(new_revision, link_revision + 1)

        # ...the next generation reads the new revision...
        second = assemble()
        self.assertEqual(second.thread_revision, new_revision)
        second_source = next(
            s for s in second.sources if s.source_id == "synthetic:thread:rev:memory:1"
        )
        self.assertEqual(second_source.thread_revision, new_revision)

        # ...while the historical capture keeps the revision it read.
        self.assertEqual(
            get_context_snapshot(snapshot.snapshot_id).thread_revisions,
            {"thread_rev_01": link_revision},
        )


class StoryThreadObservabilityTests(StoryThreadTestCase):
    """Boundary events carry identifiers and counts, never player or thread prose."""

    @covers_requirement("narrative-context::observability-protects-private-prompt-data")
    def test_thread_events_are_traced_without_prose(self):
        from world.narrative import threads as threads_module

        calls: list[tuple[str, dict]] = []

        def capture(event, *, context=None, exc=None):
            calls.append((event, dict(context or {})))

        secret_summary = "不應寫入日誌的合成劇情摘要。"
        with (
            patch.object(threads_module, "log_info", side_effect=capture),
            self.captureOnCommitCallbacks(execute=True),
        ):
            create_thread(
                thread_id="thread_log_01",
                origin="event:synthetic:thread:log:origin",
                participants=[str(self.owner.pk)],
                tick=100,
                factual_summary=secret_summary,
            )
            record_narrative_event(
                source_id="synthetic:thread:log:event:1",
                event_type="encounter_protection",
                content={"encounter_outcome": "victory"},
                participants=[self.owner.pk],
                tick=100,
            )
            establish_commitment(
                thread_id="thread_log_01",
                source_event_id="synthetic:thread:log:event:1",
                text="合成承諾內容。",
                tick=101,
            )

        events = [event for event, _ in calls]
        self.assertEqual(events[0], "narrative_thread_created")
        self.assertIn("narrative_thread_revised", events)
        for _event, context in calls:
            self.assertNotIn(secret_summary, json.dumps(context, ensure_ascii=False))
            self.assertNotIn("合成承諾內容。", json.dumps(context, ensure_ascii=False))
        created_context = calls[0][1]
        self.assertEqual(created_context["thread_id"], "thread_log_01")
        self.assertEqual(created_context["participants"], 1)

    @covers_requirement("narrative-fast-recall::permissions-and-explicit-scope-precede-recall-scoring")
    def test_denied_thread_scope_emits_a_warn_event(self):
        from world.narrative import recall as recall_module

        create_thread(
            thread_id="thread_log_private_01",
            origin="event:synthetic:thread:log:private:origin",
            participants=[str(self.other.pk)],
            tick=100,
        )
        warn_calls: list[tuple[str, dict]] = []

        def capture(event, *, context=None, exc=None):
            warn_calls.append((event, dict(context or {})))

        with patch.object(recall_module, "log_warn", side_effect=capture):
            fast_recall(
                owner_id=str(self.owner.pk),
                requester_id=str(self.owner.pk),
                query="任何查詢",
                thread_id="thread_log_private_01",
            )
        self.assertEqual(warn_calls[0][0], "narrative_thread_recall_denied")
        self.assertEqual(warn_calls[0][1]["thread_id"], "thread_log_private_01")
