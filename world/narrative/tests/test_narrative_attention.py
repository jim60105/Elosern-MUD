"""Synthetic behavior tests for deterministic narrative attention.

Everything here is deterministic and offline: synthetic actors, synthetic
provenance rows, no model or image service (attention calls none). Delta-only
requirement ids land at archive sync, so substantive tests are annotated
against the existing canonical main ids they establish.
"""

from __future__ import annotations

import json
import socket
import unittest
from dataclasses import asdict
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement

from world.narrative.attention import (
    DEFAULT_ATTENTION_CONFIG,
    REASON_BELOW_FOCUS_LIMIT,
    REASON_IN_COOLDOWN,
    REASON_LOCATION_UNREACHABLE,
    REASON_NOT_EXECUTABLE,
    REASON_NOT_INVESTED,
    REASON_SCHEDULE_BLOCKED,
    REASON_SELECTED,
    REASON_SUPERSEDED_REQUEST,
    REASON_UNKNOWN_TO_OWNER,
    SOURCE_REQUEST,
    SOURCE_THREAD,
    AttentionCandidate,
    AttentionConfig,
    AttentionContext,
    EngagementSignals,
    build_attention_candidates,
    build_context,
    collect_quest_deadlines,
    collect_schedule_blocks,
    extract_engagement,
    rank_attention,
    thread_required_location,
)
from world.narrative.attention_calibration import (
    DEFAULT_REPORT_PATH,
    run_calibration,
)
from world.narrative.authoring import confirm_draft, latest_confirmed_request, save_draft
from world.narrative.correspondence import send_letter
from world.narrative.dialogue import submit_turn
from world.narrative.events import record_narrative_event
from world.narrative.memory import record_memory
from world.narrative.models import LetterSend, LetterState, NarrativeEvent, StoryThread
from world.narrative.threads import (
    create_thread,
    link_event_to_thread,
    link_letter_to_thread,
    link_memory_to_thread,
)
from world.rules.clock import get_world_clock

OWNER_LOCATION = "room:hall"
FIXTURE_PROSE = "尤漢娜的私人祕密"


def _candidate(candidate_id: str, **overrides) -> AttentionCandidate:
    fields = dict(
        candidate_id=candidate_id,
        source_kind=SOURCE_THREAD,
        source_ref=candidate_id.split(":", 1)[1],
        revision=1,
        origin="event:synthetic:attention",
        participants=("201",),
        invested=True,
        confirmed=False,
        knowledge=True,
        required_location=OWNER_LOCATION,
        capability="dialogue",
        unresolved_stakes=1,
    )
    fields.update(overrides)
    return AttentionCandidate(**fields)


def _context(**overrides) -> AttentionContext:
    fields = dict(
        owner_id="101",
        now_tick=1_000_000,
        owner_location=OWNER_LOCATION,
        reachable_locations=frozenset(),
        blocked_participants=frozenset(),
    )
    fields.update(overrides)
    return AttentionContext(**fields)


class AttentionRankingTests(unittest.TestCase):
    """Pure, offline ranking behavior for every delta scenario."""

    @covers_requirement("narrative-attention::eligibility-precedes-attention-scoring")
    def test_unrelated_high_salience_candidate_is_ineligible_before_scoring(self):
        """A known-but-uninvested automatic candidate never competes on salience."""
        unrelated = _candidate(
            "thread:unrelated",
            invested=False,
            confirmed=False,
            unresolved_stakes=3,
            salience=9,
        )
        invested = _candidate("thread:invested", unresolved_stakes=1)
        decision = rank_attention([unrelated, invested], _context())
        self.assertEqual(
            [item.candidate_id for item in decision.selected], ["thread:invested"]
        )
        excluded = {item.candidate.candidate_id: item.reasons for item in decision.excluded}
        self.assertEqual(excluded["thread:unrelated"], (REASON_NOT_INVESTED,))
        self.assertNotIn("thread:unrelated", [item.candidate_id for item in decision.ranked])

    @covers_requirement("narrative-attention::eligibility-precedes-attention-scoring")
    def test_unavailable_candidate_excluded_regardless_of_score(self):
        """Location, schedule, and capability failures are filtered before scoring."""
        importable = _candidate(
            "thread:far",
            participants=("202",),
            required_location="room:distant",
            unresolved_stakes=3,
        )
        blocked = _candidate("thread:busy", participants=("201",), unresolved_stakes=3)
        not_executable = _candidate(
            "thread:dragon",
            participants=("203",),
            capability="summon_dragon",
            unresolved_stakes=3,
        )
        context = _context(
            reachable_locations=frozenset({"room:annex"}),
            blocked_participants=frozenset({"201"}),
        )
        decision = rank_attention([importable, blocked, not_executable], context)
        self.assertEqual(decision.selected, ())
        self.assertEqual(decision.ranked, ())
        reasons = {item.candidate.candidate_id: item.reasons for item in decision.excluded}
        self.assertEqual(reasons["thread:far"], (REASON_LOCATION_UNREACHABLE,))
        self.assertEqual(reasons["thread:busy"], (REASON_SCHEDULE_BLOCKED,))
        self.assertEqual(reasons["thread:dragon"], (REASON_NOT_EXECUTABLE,))

    @covers_requirement("narrative-attention::eligibility-precedes-attention-scoring")
    def test_confirmed_request_is_eligible_as_player_direction(self):
        """A valid confirmed request competes without invested history."""
        request = _candidate(
            "request:draft:v1",
            source_kind=SOURCE_REQUEST,
            source_ref="draft:v1",
            invested=False,
            confirmed=True,
            capability="quest",
            required_location="",
            unresolved_stakes=0,
            last_activity_tick=None,
        )
        decision = rank_attention([request], _context())
        self.assertEqual(decision.excluded, ())
        self.assertEqual(
            [item.candidate_id for item in decision.selected], ["request:draft:v1"]
        )
        self.assertIn(REASON_SELECTED, decision.selected[0].reason_codes)

    @covers_requirement("narrative-attention::eligibility-precedes-attention-scoring")
    def test_superseded_request_is_excluded(self):
        superseded = _candidate(
            "request:draft:v1",
            source_kind=SOURCE_REQUEST,
            source_ref="draft:v1",
            invested=False,
            confirmed=True,
            authoritative=False,
            capability="quest",
            required_location="",
            unresolved_stakes=0,
        )
        current = _candidate(
            "request:draft:v2",
            source_kind=SOURCE_REQUEST,
            source_ref="draft:v2",
            invested=False,
            confirmed=True,
            authoritative=True,
            capability="quest",
            required_location="",
            unresolved_stakes=0,
        )
        decision = rank_attention([superseded, current], _context())
        excluded = {item.candidate.candidate_id: item.reasons for item in decision.excluded}
        self.assertEqual(excluded["request:draft:v1"], (REASON_SUPERSEDED_REQUEST,))

    @covers_requirement("narrative-attention::observable-engagement-and-calibrated-focus-bound-selection")
    def test_active_engagement_component_exceeds_passive_receipt(self):
        """The measured engagement component, not only the order, reflects action."""
        active = _candidate(
            "thread:active",
            engagement=EngagementSignals(
                dialogue_initiations=3,
                sustained_correspondence=2,
                clue_questions=1,
                participation=1,
            ),
        )
        passive = _candidate(
            "thread:passive", engagement=EngagementSignals(passive_receipts=5)
        )
        decision = rank_attention([passive, active], _context())
        self.assertEqual(
            [item.candidate_id for item in decision.selected], ["thread:active", "thread:passive"]
        )
        components = {
            item.candidate.candidate_id: {
                component.name: component.raw for component in item.components
            }
            for item in decision.ranked
        }
        self.assertGreater(components["thread:active"]["engagement"], 0.0)
        self.assertEqual(components["thread:passive"]["engagement"], 0.0)
        self.assertGreater(
            components["thread:active"]["engagement"], components["thread:passive"]["engagement"]
        )

    @covers_requirement("narrative-attention::observable-engagement-and-calibrated-focus-bound-selection")
    def test_identical_inputs_rank_identically_and_reason_data_matches(self):
        candidates = [
            _candidate("thread:b", unresolved_stakes=2),
            _candidate("thread:a", unresolved_stakes=2),
            _candidate("thread:passive", engagement=EngagementSignals(passive_receipts=3)),
        ]
        context = _context()
        first = rank_attention(candidates, context)
        second = rank_attention(candidates, context)
        self.assertEqual(
            [item.candidate_id for item in first.selected],
            [item.candidate_id for item in second.selected],
        )
        self.assertEqual(
            [item.candidate_id for item in first.ranked],
            [item.candidate_id for item in second.ranked],
        )
        self.assertEqual(first.reason_counts, second.reason_counts)
        self.assertEqual(first.snapshot_hash, second.snapshot_hash)
        self.assertGreaterEqual(len(first.snapshot_hash), 64)
        int(first.snapshot_hash, 16)

    @covers_requirement("narrative-attention::observable-engagement-and-calibrated-focus-bound-selection")
    def test_tie_break_is_stable_by_candidate_id(self):
        decision = rank_attention(
            [_candidate("thread:beta"), _candidate("thread:alpha")], _context()
        )
        self.assertEqual(
            [item.candidate_id for item in decision.selected], ["thread:alpha", "thread:beta"]
        )

    @covers_requirement("narrative-attention::observable-engagement-and-calibrated-focus-bound-selection")
    def test_focus_limit_bounds_selection_only(self):
        candidates = [
            _candidate(f"thread:c{index}", unresolved_stakes=3 - index)
            for index in range(5)
        ]
        config = AttentionConfig(focus_limit=2)
        decision = rank_attention(candidates, _context(), config)
        self.assertEqual(len(decision.selected), 2)
        self.assertEqual(len(decision.ranked), 5)
        self.assertEqual(len(decision.excluded), 0)
        below = [
            item
            for item in decision.ranked
            if REASON_BELOW_FOCUS_LIMIT in item.reason_codes
        ]
        self.assertEqual(len(below), 3)
        self.assertEqual(
            [(reason, count) for reason, count in decision.reason_counts if reason == REASON_SELECTED],
            [(REASON_SELECTED, 2)],
        )

    @covers_requirement("narrative-attention::observable-engagement-and-calibrated-focus-bound-selection")
    def test_cooldown_and_repetition_are_reported_and_penalise(self):
        fresh = _candidate(
            "thread:fresh", repetition=3, last_activity_tick=1_000_000 - 30
        )
        rested = _candidate("thread:rested", last_activity_tick=1_000_000 - 7200)
        decision = rank_attention([fresh, rested], _context())
        self.assertEqual(
            [item.candidate_id for item in decision.selected], ["thread:rested", "thread:fresh"]
        )
        by_id = {item.candidate.candidate_id: item for item in decision.ranked}
        self.assertIn(REASON_IN_COOLDOWN, by_id["thread:fresh"].reason_codes)

    @covers_requirement("narrative-attention::observable-engagement-and-calibrated-focus-bound-selection")
    def test_location_component_bands(self):
        same = _candidate("thread:same", required_location=OWNER_LOCATION)
        reachable = _candidate("thread:reachable", required_location="room:annex")
        agnostic = _candidate("thread:agnostic", required_location="")
        context = _context(reachable_locations=frozenset({"room:annex"}))
        decision = rank_attention([same, reachable, agnostic], context)
        bands = {
            item.candidate.candidate_id: {
                component.name: component.raw for component in item.components
            }["location"]
            for item in decision.ranked
        }
        self.assertEqual(bands["thread:same"], 1.0)
        self.assertEqual(bands["thread:reachable"], 0.5)
        self.assertEqual(bands["thread:agnostic"], 0.5)

    def test_rank_emits_one_privacy_safe_event(self):
        """Exactly one boundary event, carrying identifiers and counts only."""
        prose_origin = _candidate("thread:unrelated", invested=False, origin=FIXTURE_PROSE)
        with patch("world.narrative.attention.log_info") as log_info:
            decision = rank_attention([prose_origin, _candidate("thread:ok")], _context())
        self.assertTrue(decision.selected)
        log_info.assert_called_once()
        event, = log_info.call_args.args
        context = log_info.call_args.kwargs["context"]
        self.assertEqual(event, "narrative_attention_ranked")
        self.assertEqual(
            set(context),
            {
                "owner_id",
                "config_version",
                "tick",
                "candidate_count",
                "eligible_count",
                "selected_count",
                "excluded_count",
                "focus_limit",
                "snapshot_hash",
            },
        )
        self.assertNotIn(FIXTURE_PROSE, str(context))

    def test_rank_attention_performs_no_network(self):
        with patch("socket.socket", side_effect=AssertionError("no network allowed")):
            decision = rank_attention([_candidate("thread:ok")], _context())
        self.assertEqual(len(decision.selected), 1)

    @covers_requirement(
        "narrative-attention::eligibility-precedes-attention-scoring",
        "narrative-attention::observable-engagement-and-calibrated-focus-bound-selection",
    )
    def test_calibration_cases_all_match_and_report_is_current(self):
        report = run_calibration()
        self.assertEqual(report.metrics.cases_matched, report.metrics.total_cases)
        self.assertEqual(
            report.metrics.exclusions_matched, report.metrics.exclusions_expected
        )
        self.assertEqual(report.metrics.focus_precision, 1.0)
        self.assertEqual(report.metrics.focus_recall, 1.0)
        committed = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(committed, json.loads(json.dumps(asdict(report))))


class AttentionExtractionTests(EvenniaTest):
    """Durable, read-only extraction and its integration with ranking."""

    def setUp(self):
        super().setUp()
        self.owner = create_object(
            "typeclasses.characters.PlayerCharacter",
            key="Synthetic attention owner",
            location=self.room1,
        )
        self.other = create_object(
            "typeclasses.characters.PlayerCharacter", key="Synthetic attention other"
        )
        self.npc = create_object("typeclasses.npcs.NPC", key="Synthetic attention npc")
        self.clock = get_world_clock()
        self.clock._persist(100)
        self.clock.tick = 100

    @property
    def owner_id(self) -> str:
        return str(self.owner.pk)

    def _owner_thread(self, thread_id: str, **overrides) -> StoryThread:
        fields = dict(
            thread_id=thread_id,
            origin=f"event:synthetic:{thread_id}:origin",
            participants=[self.owner_id, str(self.npc.pk)],
            tick=100,
        )
        fields.update(overrides)
        return create_thread(**fields)

    def _decide(self, *, focus_limit: int = 3):
        candidates = build_attention_candidates(owner=self.owner, now_tick=100)
        config = AttentionConfig(focus_limit=focus_limit)
        return rank_attention(candidates, build_context(owner=self.owner, now_tick=100), config)

    @covers_requirement(
        "narrative-memory::cognition-is-owner-scoped-and-provenance-preserving"
    )
    def test_known_thread_without_owned_experience_is_not_invested(self):
        """Being named in the ACL makes a thread known but not yet invested."""
        self._owner_thread(
            "att_known_only",
            participants=[str(self.npc.pk)],
            visible_to=[self.owner_id],
        )
        decision = self._decide()
        excluded = {item.candidate.candidate_id: item.reasons for item in decision.excluded}
        self.assertEqual(excluded.get("thread:att_known_only"), (REASON_NOT_INVESTED,))
        self.assertNotIn("thread:att_known_only", [i.candidate_id for i in decision.ranked])

    @covers_requirement("narrative-attention::eligibility-precedes-attention-scoring")
    def test_unrelated_thread_is_unknown_and_ineligible(self):
        self._owner_thread(
            "att_foreign",
            participants=[str(self.other.pk), str(self.npc.pk)],
            visible_to=[str(self.other.pk)],
        )
        decision = self._decide()
        excluded = {item.candidate.candidate_id: item.reasons for item in decision.excluded}
        self.assertEqual(
            excluded.get("thread:att_foreign"),
            (REASON_UNKNOWN_TO_OWNER, REASON_NOT_INVESTED),
        )

    @covers_requirement("narrative-attention::eligibility-precedes-attention-scoring")
    def test_memory_linked_thread_is_invested_and_eligible(self):
        record, _, _ = record_memory(
            owner_id=self.owner_id,
            content={"summary": "護送商隊的合成記憶。"},
            tick=100,
            source_id="att:memory:1",
        )
        self._owner_thread("att_memory", participants=[str(self.npc.pk)], visible_to=[self.owner_id])
        link_memory_to_thread(
            record=record, thread_id="att_memory", actor_id=self.owner_id, tick=100
        )
        decision = self._decide()
        self.assertIn("thread:att_memory", [item.candidate_id for item in decision.ranked])

    @covers_requirement("narrative-attention::eligibility-precedes-attention-scoring")
    def test_recipient_only_letter_link_is_owned_experience(self):
        """A linked letter the owner merely received still counts as experience."""
        incoming = send_letter(
            sender_id=str(self.npc.pk),
            recipient_id=self.owner_id,
            body="合成來信內容。",
            source_id="att:letter:recipient",
        ).source_id
        letter = LetterSend.objects.get(source_id=incoming)
        self._owner_thread(
            "att_letter", participants=[str(self.npc.pk)], visible_to=[self.owner_id]
        )
        link_letter_to_thread(
            thread_id="att_letter", letter=letter, actor_id=self.owner_id, tick=100
        )
        decision = self._decide()
        self.assertIn("thread:att_letter", [item.candidate_id for item in decision.ranked])

    @covers_requirement(
        "narrative-story-threads::thread-lifecycle-preserves-facts-separately-from-plans"
    )
    def test_ranking_preserves_unselected_thread_state(self):
        """Bounding the candidate set never deletes or rewrites thread state."""
        self._owner_thread(
            "att_a", factual_summary="合成事實 A。", unresolved_questions=["問題 A？"]
        )
        self._owner_thread("att_b", factual_summary="合成事實 B。")
        self._owner_thread("att_c", factual_summary="合成事實 C。")
        before = {
            thread.thread_id: (
                thread.state,
                thread.revision,
                thread.factual_summary,
                list(thread.unresolved_questions),
            )
            for thread in StoryThread.objects.filter(state="active").order_by("id")
        }
        decision = self._decide(focus_limit=1)
        self.assertEqual(len(decision.selected), 1)
        self.assertEqual(len(decision.ranked), 3)
        self.assertEqual(StoryThread.objects.filter(state="active").count(), len(before))
        after = {
            thread.thread_id: (
                thread.state,
                thread.revision,
                thread.factual_summary,
                list(thread.unresolved_questions),
            )
            for thread in StoryThread.objects.filter(state="active").order_by("id")
        }
        self.assertEqual(before, after)

    @covers_requirement("narrative-attention::observable-engagement-and-calibrated-focus-bound-selection")
    def test_extract_engagement_counts_only_active_actions(self):
        submit_turn(self.npc, self.owner, "這條線索在哪裡？")
        submit_turn(self.npc, self.owner, "再問一次，線索在哪裡？", submission_id="att_sub_2")
        send_letter(
            sender_id=self.owner_id,
            recipient_id=str(self.npc.pk),
            body="合成信件內容。",
            source_id="att:letter:1",
        )
        incoming = send_letter(
            sender_id=str(self.npc.pk),
            recipient_id=self.owner_id,
            body="合成回信內容。",
            source_id="att:letter:2",
        ).source_id
        letter = LetterSend.objects.get(source_id=incoming)
        LetterState.objects.filter(letter=letter).update(
            status="read", read_tick=100, collection_tick=100
        )
        NarrativeEvent.objects.create(
            source_id="correspondence:att:letter:2:read",
            event_type="correspondence_read",
            content={"letter_source_id": incoming},
            participants=[self.owner_id],
            tick=100,
            visibility="private",
        )
        signals = extract_engagement(
            self.owner_id,
            participants=[str(self.npc.pk)],
            now_tick=100,
            window_ticks=100,
        )
        self.assertEqual(signals.dialogue_initiations, 2)
        self.assertEqual(signals.clue_questions, 2)
        self.assertEqual(signals.sustained_correspondence, 1)
        self.assertEqual(signals.participation, 0)
        self.assertEqual(signals.passive_receipts, 2)

    def test_engagement_is_counterpart_scoped(self):
        """A candidate with no other party is zeroed, never owner-global."""
        submit_turn(self.npc, self.owner, "線索在哪裡？")
        self.assertEqual(
            extract_engagement(self.owner_id, participants=(), now_tick=100, window_ticks=100),
            EngagementSignals(),
        )
        self.assertEqual(
            extract_engagement(
                self.owner_id,
                participants=[str(self.npc.pk)],
                now_tick=100,
                window_ticks=100,
            ).dialogue_initiations,
            1,
        )

    @covers_requirement("narrative-attention::eligibility-precedes-attention-scoring")
    def test_schedule_block_excludes_candidate(self):
        self._owner_thread("att_busy")
        self.assertEqual(collect_schedule_blocks([self.npc.pk]), frozenset())
        self.npc.db.schedule_state = "busy"
        self.assertEqual(
            collect_schedule_blocks([self.npc.pk]), frozenset({str(self.npc.pk)})
        )
        decision = self._decide()
        excluded = {item.candidate.candidate_id: item.reasons for item in decision.excluded}
        self.assertEqual(excluded.get("thread:att_busy"), (REASON_SCHEDULE_BLOCKED,))

    @covers_requirement("narrative-attention::eligibility-precedes-attention-scoring")
    def test_thread_required_location_follows_linked_event(self):
        event, _, _ = record_narrative_event(
            source_id="att:loc:1",
            event_type="visit",
            content={},
            participants=[self.owner_id, str(self.npc.pk)],
            location="room:tavern",
            tick=100,
        )
        thread = self._owner_thread("att_loc")
        link_event_to_thread(
            thread_id="att_loc", event=event, tick=100, actor_id=self.owner_id
        )
        self.assertEqual(thread_required_location(thread), "room:tavern")

    def test_corrupt_quest_log_degrades_with_warning(self):
        self.owner.db.quest_log = [{"malformed": True}]
        with patch("world.narrative.attention.log_warn") as log_warn:
            deadlines = collect_quest_deadlines(self.owner)
        self.assertEqual(deadlines, {})
        log_warn.assert_called_once()
        self.assertEqual(
            log_warn.call_args.args[0], "narrative_attention_quest_deadlines_unavailable"
        )

    @covers_requirement("narrative-attention::eligibility-precedes-attention-scoring")
    def test_latest_confirmed_request_eligible_and_older_excluded(self):
        direction = {
            "summary": "合成夢境方向：在無名港尋找失落的鐘聲。",
            "themes": ["合成主題"],
            "atmosphere": ["合成氛圍"],
            "participants": [],
            "emphasis": ["合成重點"],
            "exclusions": ["合成排除"],
            "kind": "new_story",
            "thread_id": None,
            "effects": [],
            "revisions": [],
        }
        save_draft(owner_id=self.owner_id, direction=direction, tick=100, draft_id="att_draft")
        confirm_draft(draft_id="att_draft", owner_id=self.owner_id, tick=101)
        edited = dict(direction, summary="合成夢境方向：改寫後的第二版。")
        save_draft(owner_id=self.owner_id, direction=edited, tick=102, draft_id="att_draft")
        current = confirm_draft(draft_id="att_draft", owner_id=self.owner_id, tick=103)
        self.assertEqual(latest_confirmed_request(self.owner_id).submission_key, current.submission_key)

        candidates = build_attention_candidates(owner=self.owner, now_tick=103)
        request_ids = [
            candidate.candidate_id
            for candidate in candidates
            if candidate.source_kind == SOURCE_REQUEST
        ]
        self.assertEqual(len(request_ids), 2)
        decision = rank_attention(
            candidates, build_context(owner=self.owner, now_tick=103)
        )
        excluded = {item.candidate.candidate_id: item.reasons for item in decision.excluded}
        superseded = [
            candidate_id
            for candidate_id in excluded
            if candidate_id.endswith(":v1")
        ]
        self.assertEqual(superseded, [f"request:att_draft:v1"])
        self.assertEqual(excluded[f"request:att_draft:v1"], (REASON_SUPERSEDED_REQUEST,))
        self.assertIn(f"request:{current.submission_key}", [
            item.candidate_id for item in decision.ranked
        ])

    def test_build_context_reports_reachable_and_blocked(self):
        self._owner_thread("att_ctx")
        context = build_context(owner=self.owner, now_tick=100)
        self.assertEqual(context.owner_id, self.owner_id)
        self.assertIn(str(self.room1.pk), context.reachable_locations)
        self.assertEqual(context.owner_location, str(self.room1.pk))
        self.assertEqual(context.blocked_participants, frozenset())

    def test_no_default_config_drift(self):
        self.assertEqual(DEFAULT_ATTENTION_CONFIG.version, "attention_v1")
        self.assertEqual(DEFAULT_ATTENTION_CONFIG.focus_limit, 3)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
