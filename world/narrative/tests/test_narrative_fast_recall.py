"""Unit and integration tests for Fast Recall, BM25, Tokenizer, and Calibration.

Covers requirements:
- narrative-fast-recall::permissions-and-explicit-scope-precede-recall-scoring
- narrative-fast-recall::metadata-cannot-create-unrelated-recall
- narrative-fast-recall::project-labeled-evidence-determines-recall-gates
"""

from __future__ import annotations

from unittest.mock import patch
from evennia.utils.test_resources import EvenniaTestCase
from tools.spec_traceability import covers_requirement

from world.narrative.calibration_corpus import (
    CALIBRATION_TEST_CASES,
    SYNTHETIC_CALIBRATION_CORPUS,
)
from world.narrative.calibration_runner import (
    populate_synthetic_corpus,
    run_calibration,
)
from world.narrative.events import record_narrative_event
from world.narrative.memory import (
    MemoryRecord,
    MemoryRevision,
    get_owner_generation,
    project_narrative_event_to_memories,
    record_memory,
    supersede_memory,
)
from world.narrative.ranker import (
    DEFAULT_B,
    DEFAULT_K1,
    MIN_LEXICAL_THRESHOLD,
    BM25Index,
    DocumentTokens,
)
from world.narrative.recall import fast_recall
from world.narrative.tokenizer import extract_entities, tokenize
from world.observability import log_info


class NarrativeFastRecallTests(EvenniaTestCase):
    """Test suite for Fast Recall, BM25 lexical ranking, and calibrated precision."""

    def setUp(self):
        super().setUp()
        populate_synthetic_corpus()

    @covers_requirement("narrative-fast-recall::permissions-and-explicit-scope-precede-recall-scoring")
    def test_scenario_informed_and_uninformed_ask_same_question(self):
        """Scenario: Informed and uninformed ask the same question.

        WHEN two roles ask about protection but only one knows the event
        THEN only the eligible observer can retrieve the episode
        """
        query = "那天在溪谷遭遇野獸襲擊，你保護了我"

        # 1. Yohanna (informed observer) queries
        yohanna_res = fast_recall(
            owner_id="npc_yohanna_101",
            query=query,
        )
        self.assertTrue(len(yohanna_res.recalled) > 0)
        top_recalled = yohanna_res.recalled[0]
        self.assertEqual(top_recalled.view.source_id, "corpus:encounter:prot:1")

        # 2. Guard (uninformed) queries the same question
        guard_res = fast_recall(
            owner_id="npc_guard_202",
            query=query,
        )
        # Guard does not know the event -> recalled must be empty
        self.assertEqual(len(guard_res.recalled), 0)

        # 3. Unauthorized third-party requester trying to query Yohanna's private cognition
        unauth_res = fast_recall(
            owner_id="npc_yohanna_101",
            requester_id="npc_guard_202",
            query=query,
        )
        # Cross-owner cognition access blocked -> empty
        self.assertEqual(len(unauth_res.recalled), 0)

    @covers_requirement("narrative-fast-recall::permissions-and-explicit-scope-precede-recall-scoring")
    def test_scenario_rebuilding_preserves_results(self):
        """Scenario: Rebuilding preserves results.

        WHEN an index is rebuilt offline from identical effective records and versions
        THEN ordered selected source IDs are unchanged
        """
        query = "那天在溪谷遭遇野獸襲擊，你保護了我"

        # First recall
        res1 = fast_recall(
            owner_id="npc_yohanna_101",
            query=query,
        )
        sources1 = [sm.view.source_id for sm in res1.recalled]
        all_sources1 = [v.source_id for v in res1.all_selected]

        # Re-run recall (rebuilding BM25 over the views)
        res2 = fast_recall(
            owner_id="npc_yohanna_101",
            query=query,
        )
        sources2 = [sm.view.source_id for sm in res2.recalled]
        all_sources2 = [v.source_id for v in res2.all_selected]

        self.assertEqual(sources1, sources2)
        self.assertEqual(all_sources1, all_sources2)

    @covers_requirement("narrative-fast-recall::permissions-and-explicit-scope-precede-recall-scoring")
    def test_explicit_thread_scope_filtering(self):
        """Explicit thread scope filters candidate memories before scoring."""
        # Create a record with explicit thread relation
        rec, _, _ = record_memory(
            owner_id="npc_yohanna_101",
            tick=150,
            category="dialogue",
            content={"summary": "討論商隊前往驛站的行程安排"},
            salience=60,
            tier="working",
            source_id="corpus:thread:caravan:1",
            relations={"thread_id": "thread_caravan_99"},
        )

        query = "商隊前往驛站的行程安排"

        # Query with matching thread_id
        res_matching = fast_recall(
            owner_id="npc_yohanna_101",
            query=query,
            thread_id="thread_caravan_99",
        )
        recalled_ids = [sm.view.source_id for sm in res_matching.recalled]
        self.assertIn("corpus:thread:caravan:1", recalled_ids)

        # Query with non-matching thread_id
        res_other_thread = fast_recall(
            owner_id="npc_yohanna_101",
            query=query,
            thread_id="thread_other_00",
        )
        self.assertEqual(len(res_other_thread.recalled), 0)

    @covers_requirement("narrative-fast-recall::permissions-and-explicit-scope-precede-recall-scoring")
    def test_actual_projected_protection_event_is_recalled(self):
        """Real projected protection event is recalled by Traditional Chinese question."""
        actor_id = "real_actor_505"
        companion_id = "real_companion_606"

        event, _, _ = record_narrative_event(
            source_id="real:encounter:protection:event:1",
            event_type="encounter_protection",
            tick=200,
            salience=85,
            participants=[actor_id, companion_id],
            content={
                "encounter_outcome": "victory",
                "protected_keys": [companion_id],
                "mode": "round",
                "rounds_elapsed": 2,
            },
        )
        project_narrative_event_to_memories(event)

        # Query using Traditional Chinese protection question
        query = "那天遭遇戰鬥時你保護了我"
        res = fast_recall(
            owner_id=companion_id,
            query=query,
        )
        self.assertTrue(len(res.recalled) > 0)
        self.assertEqual(res.recalled[0].view.source_id, "real:encounter:protection:event:1")

    @covers_requirement("narrative-fast-recall::metadata-cannot-create-unrelated-recall")
    def test_scenario_salient_unrelated_episode_loses(self):
        """Scenario: Salient unrelated episode loses.

        WHEN an unrelated salient episode competes with a related protection episode
        THEN only lexical candidates qualify
        """
        # Yohanna has an intensely salient personal memory (lost pendant, salience 98)
        # Querying about protection must only qualify the protection episode
        query = "在溪谷時感謝你對我的援護與守護"
        res = fast_recall(
            owner_id="npc_yohanna_101",
            query=query,
        )

        recalled_ids = [sm.view.source_id for sm in res.recalled]
        self.assertIn("corpus:encounter:prot:1", recalled_ids)
        self.assertNotIn("corpus:personal:pendant:1", recalled_ids)
        self.assertNotIn("corpus:gossip:tournament:1", recalled_ids)

    @covers_requirement("narrative-fast-recall::metadata-cannot-create-unrelated-recall")
    def test_scenario_all_episodes_are_unrelated(self):
        """Scenario: All episodes are unrelated.

        WHEN a query concerns a subject absent from permitted memory
        THEN no recalled memory is returned
        """
        # Absent subject: astrology, astronomy, star charts
        query = "占星術與星相運行的十二星宮古代星圖"
        res = fast_recall(
            owner_id="npc_yohanna_101",
            query=query,
        )

        # Must return empty recalled memories intentionally
        self.assertEqual(len(res.recalled), 0)
        self.assertEqual(res.recalled, ())
        self.assertTrue(len(res.core) > 0)

    @covers_requirement("narrative-fast-recall::project-labeled-evidence-determines-recall-gates")
    def test_scenario_calibration_covers_negative_and_historical_cases(self):
        """Scenario: Calibration covers negative and historical cases.

        WHEN the corpus is evaluated
        THEN the report includes all measurements and normal inactive exclusion versus historical retrieval
        """
        report = run_calibration()

        # 1. Verify gates
        self.assertGreaterEqual(report.metrics.recall_at_1, report.calibrated_gates["min_recall_at_1"])
        self.assertGreaterEqual(report.metrics.recall_at_2, report.calibrated_gates["min_recall_at_2"])
        self.assertLessEqual(report.metrics.false_positive_rate, report.calibrated_gates["max_false_positive_rate"])
        self.assertLessEqual(report.metrics.p95_latency_ms, report.calibrated_gates["max_p95_latency_ms"])

        # 2. Verify historical vs normal exclusion for both superseded and inactive
        hist_cases = {c.case_id: c for c in report.cases}
        self.assertIn("hist_normal_excludes_superseded", hist_cases)
        self.assertIn("hist_historical_includes_superseded", hist_cases)
        self.assertIn("hist_normal_excludes_inactive", hist_cases)
        self.assertIn("hist_historical_includes_inactive", hist_cases)

        # Normal access excludes superseded and inactive records
        self.assertEqual(len(hist_cases["hist_normal_excludes_superseded"].recalled_source_ids), 0)
        self.assertEqual(len(hist_cases["hist_normal_excludes_inactive"].recalled_source_ids), 0)

        # Historical access retrieves superseded and inactive records
        self.assertIn("corpus:history:courier:old", hist_cases["hist_historical_includes_superseded"].recalled_source_ids)
        self.assertIn("corpus:inactive:outdated:1", hist_cases["hist_historical_includes_inactive"].recalled_source_ids)

    @covers_requirement("narrative-fast-recall::metadata-cannot-create-unrelated-recall")
    def test_metadata_bonus_only_reranks_lexical_qualifiers(self):
        """Metadata bonus only applies to candidates that pass the lexical threshold."""
        query = "清晨林地採集止血草與藍花藥草"
        res = fast_recall(
            owner_id="npc_yohanna_101",
            query=query,
        )

        recalled_ids = [sm.view.source_id for sm in res.recalled]
        self.assertEqual(recalled_ids, ["corpus:routine:herb:1"])

        herb_sm = res.recalled[0]
        self.assertGreaterEqual(herb_sm.lexical_score, MIN_LEXICAL_THRESHOLD)
        self.assertGreater(herb_sm.metadata_bonus, 0.0)
        self.assertEqual(herb_sm.final_score, herb_sm.lexical_score + herb_sm.metadata_bonus)
