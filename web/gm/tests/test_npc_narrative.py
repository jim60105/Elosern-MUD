"""Fixed-fixture reader tests: the NPC narrative tabs (tasks 3.1-3.3 / 6.1).

Establishes the delta requirements "NPC memory and dialogue inspection" and
"Two-layer immutable inspection acceptance" for the narrative surfaces: every
memory filter and the complete revision history, the newest-ten snapshot cap
with its token accounting/truncation/evidence links, multi-player dialogue
grouping with the existing S2 call links, and recall equality against a direct
authoritative ``fast_recall`` under the same canonical owner/requester without
a single persistent change. The ``gm-runtime-state::*`` requirement IDs this
module covers enter the traceability index when the change's delta spec is
synced at archive.
"""

from __future__ import annotations

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest
from typeclasses.npcs import NPC
from world.narrative.memory import get_owner_memories
from world.narrative.models import (
    DialogueEpoch,
    DialogueFrame,
    MemoryRecord,
    MemoryRevision,
    NarrativeContextSnapshot,
)
from world.narrative.recall import fast_recall
from world.rules.traits import restore_gauges_to_full

from web.gm.readers import npcs
from web.gm.readers._entities import read_attr, stored_attribute_keys
from web.gm.tests._state_support import (
    column_values,
    failed_sections,
    group_titles,
    link_ids,
    link_kinds,
    open_synthetic_scope,
    row_value,
    section_keys,
    section_of,
)

SYNTH_RACE = "t_duskmari"
CALL_ID = "ab" * 16
OWNER_CATEGORY = "observation"
SUPERSEDED_CATEGORY = "t_superseded"


class NpcNarrativeReaderTests(EvenniaTest):
    def setUp(self):
        open_synthetic_scope(self, "races", "static_tiers", "subraces")
        super().setUp()
        self.npc = create.create_object(NPC, key="t_reader_memory_npc", location=self.room1)
        self.npc.race = SYNTH_RACE
        self.npc.apply_race_baseline()
        restore_gauges_to_full(self.npc)
        self.owner = str(self.npc.pk)

    # --- fixtures ---------------------------------------------------------

    def _memory(
        self,
        *,
        tick: int,
        category: str = OWNER_CATEGORY,
        tier: str = "working",
        availability: str = "active",
        scope: str = "witnessed",
        salience: int = 1,
        revision_number: int = 1,
        revisions: int = 1,
        source_id: str = "",
        subjects: tuple[str, ...] = ("t_reader_subject",),
    ) -> MemoryRecord:
        record = MemoryRecord.objects.create(
            owner_id=self.owner,
            tick=tick,
            category=category,
            content={"note": f"合成記憶 {tick}"},
            salience=salience,
            knowledge_scope=scope,
            confidence=0.75,
            subjects=list(subjects),
            source_id=source_id,
            effective_tier=tier,
            effective_availability=availability,
            latest_revision_number=revision_number,
        )
        for number in range(1, revisions + 1):
            MemoryRevision.objects.create(
                record=record,
                revision_number=number,
                availability=availability,
                tier=tier,
                decay_metadata={"half_life": number},
                supersedes_record_id="" if number == 1 else str(record.pk),
                relations={"linked": number},
            )
        return record

    def _snapshot(self, index: int, *, with_evidence: bool = False) -> NarrativeContextSnapshot:
        payload = {
            "sections": [
                {"name": f"t_section_{index}", "heading": "合成區塊", "token_count": 12,
                 "sha256": "c" * 64}
            ],
            "call_id": CALL_ID if with_evidence else None,
            "trace_id": "t_trace" if with_evidence else None,
        }
        return NarrativeContextSnapshot.objects.create(
            snapshot_id=f"t_snapshot_{index}",
            capability="t_capability",
            prompt_version="t_prompt_v1",
            rendering_version="t_render_v1",
            owner_id=self.owner,
            owner_generation=index,
            sources=[{"source_id": f"t_source_{index}", "record_id": index}],
            budget_accounting={"used": index, "limit": 100},
            truncation_decisions=[f"t_truncated_{index}"] if index == 1 else [],
            rendered_payload=payload,
        )

    def _dialogue(self, player: str, sequence: int, *, call_id: str | None = CALL_ID) -> DialogueEpoch:
        epoch = DialogueEpoch.objects.create(
            npc_id=self.owner,
            player_id=player,
            sequence=sequence,
            version="t_version",
            reason="t_reason",
            start_turn_id=sequence,
            summary=f"合成摘要 {sequence}",
            generation_id=f"t_generation_{player}_{sequence}",
            snapshot_id=f"t_snapshot_{sequence}",
            source_refs=[],
        )
        DialogueFrame.objects.create(
            epoch=epoch,
            identity=f"t_frame_{sequence}",
            content=f"合成對話 {sequence}",
            tick=sequence,
            sources=[{"call_id": call_id}] if call_id else [],
        )
        return epoch

    # --- memory (3.1) -----------------------------------------------------

    def test_memory_list_reports_the_effective_fields_and_source_link(self):
        record = self._memory(tick=5, source_id="t_source", salience=3, revision_number=2)
        items = npcs.memory_list_items({"owner": f"#{self.owner}"})
        self.assertEqual([item["id"] for item in items], [str(record.pk)])
        item = items[0]
        self.assertEqual(item["owner"], self.owner)
        self.assertEqual(item["kind"], "memories")
        values = {field["label"]: field["value"] for field in item["fields"]}
        self.assertEqual(values["類別"], OWNER_CATEGORY)
        self.assertEqual(values["層級"], "working")
        self.assertEqual(values["可用性"], "active")
        self.assertEqual(values["知識範圍"], "witnessed")
        self.assertEqual(values["顯著度"], 3)
        self.assertEqual(values["信心"], 0.75)
        self.assertEqual(values["來源"], "t_source")
        self.assertIn("t_reader_subject", values["主體"])
        source = next(field for field in item["fields"] if field["label"] == "來源")
        self.assertEqual(source["link"]["kind"], "narrative")

    def test_memory_filters_are_applied(self):
        active = self._memory(tick=1, tier="core")
        inactive = self._memory(tick=2, availability="inactive", tier="core")
        superseded = self._memory(
            tick=3, category=SUPERSEDED_CATEGORY, availability="superseded", tier="working"
        )
        default = npcs.memory_list_items({"owner": f"#{self.owner}"})
        self.assertEqual([item["id"] for item in default], [str(active.pk)])
        with_inactive = npcs.memory_list_items(
            {"owner": f"#{self.owner}", "include_inactive": "true"}
        )
        self.assertEqual(
            {item["id"] for item in with_inactive}, {str(active.pk), str(inactive.pk)}
        )
        with_superseded = npcs.memory_list_items(
            {"owner": f"#{self.owner}", "include_superseded": "1"}
        )
        self.assertEqual(
            {item["id"] for item in with_superseded}, {str(active.pk), str(superseded.pk)}
        )
        self.assertEqual(
            [item["id"] for item in npcs.memory_list_items({"owner": f"#{self.owner}", "tier": "core"})],
            [str(active.pk)],
        )
        self.assertEqual(
            [
                item["id"]
                for item in npcs.memory_list_items(
                    {"owner": f"#{self.owner}", "category": SUPERSEDED_CATEGORY,
                     "include_superseded": "true"}
                )
            ],
            [str(superseded.pk)],
        )

    def test_memory_detail_exposes_the_complete_revision_history(self):
        record = self._memory(tick=7, revision_number=3, revisions=3)
        detail = npcs.memory_detail(str(record.pk), {"owner": f"#{self.owner}"})
        self.assertEqual(detail["kind"], "memories")
        self.assertEqual(section_keys(detail), ["identity", "content", "revisions", "subjects"])
        self.assertEqual(failed_sections(detail), {})
        identity = section_of(detail, "identity")
        self.assertEqual(row_value(identity, "紀錄"), record.pk)
        self.assertEqual(row_value(identity, "有效層級"), "working")
        self.assertEqual(row_value(identity, "最新修訂"), 3)
        revisions = section_of(detail, "revisions")
        self.assertEqual(column_values(revisions, "revision"), [3, 2, 1])
        self.assertEqual(column_values(revisions, "supersedes"), [str(record.pk), str(record.pk), "—"])
        self.assertEqual(section_of(detail, "content")["type"], "tree")
        self.assertEqual(detail["raw"]["record"]["id"], record.pk)

    def test_a_memory_revision_less_record_reports_an_empty_history(self):
        record = self._memory(tick=9, revisions=0)
        detail = npcs.memory_detail(str(record.pk), {"owner": f"#{self.owner}"})
        revisions = section_of(detail, "revisions")
        self.assertEqual(revisions["rows"], [])
        self.assertIn("沒有修訂", revisions["empty_note"])

    # --- snapshots (3.1) --------------------------------------------------

    def test_snapshot_list_is_capped_at_the_newest_ten(self):
        snapshots = [self._snapshot(index) for index in range(12)]
        items = npcs.snapshot_list_items({"owner": f"#{self.owner}"})
        self.assertEqual(len(items), npcs.MAX_SNAPSHOTS)
        expected = [snapshot.snapshot_id for snapshot in snapshots[::-1]][:10]
        self.assertEqual([item["id"] for item in items], expected)
        labels = [field["label"] for field in items[0]["fields"]]
        self.assertEqual(labels, ["能力", "擁有者世代", "建立時間", "區塊數", "截斷決策數"])

    def test_snapshot_detail_projects_sections_tokens_truncation_and_sources(self):
        snapshot = self._snapshot(1, with_evidence=True)
        detail = npcs.snapshot_detail(snapshot.snapshot_id, {"owner": f"#{self.owner}"})
        self.assertEqual(
            section_keys(detail),
            ["identity", "sections", "tokens", "truncation", "sources", "evidence"],
        )
        self.assertEqual(failed_sections(detail), {})
        sections = section_of(detail, "sections")
        self.assertEqual(column_values(sections, "name"), ["t_section_1"])
        self.assertEqual(column_values(sections, "tokens"), [12])
        self.assertEqual(section_of(detail, "tokens")["type"], "tree")
        self.assertEqual(section_of(detail, "truncation")["type"], "bullets")
        self.assertEqual(column_values(section_of(detail, "sources"), "source"), ["t_source_1"])
        evidence = section_of(detail, "evidence")
        self.assertEqual(row_value(evidence, "call_id"), CALL_ID)
        self.assertEqual(link_ids(evidence, "call"), [CALL_ID])

    def test_snapshot_without_evidence_or_truncation_reports_honest_empties(self):
        snapshot = self._snapshot(2)
        detail = npcs.snapshot_detail(snapshot.snapshot_id, {"owner": f"#{self.owner}"})
        self.assertEqual(section_of(detail, "truncation")["type"], "empty")
        evidence = section_of(detail, "evidence")
        self.assertEqual(evidence["type"], "empty")
        self.assertIn("S2", evidence["note"])

    def test_an_unknown_snapshot_is_a_404(self):
        with self.assertRaises(Exception) as missing:
            npcs.snapshot_detail("t_absent_snapshot", {"owner": f"#{self.owner}"})
        self.assertEqual(missing.exception.code, "object_not_found")

    # --- dialogue (3.2) ---------------------------------------------------

    def test_dialogue_list_groups_epochs_by_player(self):
        self._dialogue("t_player_a", 1)
        self._dialogue("t_player_a", 2)
        self._dialogue("t_player_b", 1)
        items = npcs.dialogue_list_items({"owner": f"#{self.owner}"})
        self.assertEqual([item["id"] for item in items], ["t_player_a", "t_player_b"])
        values = {field["label"]: field["value"] for field in items[0]["fields"]}
        self.assertEqual(values["紀元數"], 2)
        self.assertEqual(values["對話框數"], 2)
        self.assertEqual([epoch["sequence"] for epoch in items[0]["epochs"]], [1, 2])

    def test_dialogue_detail_marks_epochs_and_links_retained_calls(self):
        self._dialogue("t_player_a", 1)
        self._dialogue("t_player_a", 2, call_id=None)
        detail = npcs.dialogue_detail("t_player_a", {"owner": f"#{self.owner}"})
        self.assertEqual(section_keys(detail), ["identity", "epochs"])
        self.assertEqual(failed_sections(detail), {})
        epochs = section_of(detail, "epochs")
        self.assertEqual(group_titles(epochs), ["第 1 紀元", "第 2 紀元"])
        self.assertEqual(link_ids(epochs, "call"), [CALL_ID])
        self.assertLessEqual({"call"}, link_kinds(epochs))
        self.assertEqual(
            row_value(section_of(detail, "identity"), "玩家"), "t_player_a"
        )

    def test_dialogue_detail_needs_a_matching_owner(self):
        self._dialogue("t_player_a", 1)
        with self.assertRaises(Exception) as missing:
            npcs.dialogue_detail("t_player_absent", {"owner": f"#{self.owner}"})
        self.assertEqual(missing.exception.code, "object_not_found")

    def test_owner_identity_is_required_for_every_narrative_tab(self):
        for builder in (
            npcs.memory_list_items,
            npcs.snapshot_list_items,
            npcs.dialogue_list_items,
        ):
            with self.subTest(builder=builder.__name__), self.assertRaises(Exception) as raised:
                builder({})
            self.assertEqual(raised.exception.code, "invalid_filter")

    # --- recall (3.3) -----------------------------------------------------

    def test_recall_equals_a_direct_authoritative_call_and_writes_nothing(self):
        for index in range(3):
            self._memory(tick=index + 1, tier="core" if index == 0 else "working")
        before_keys = stored_attribute_keys(self.npc)
        before_rows = MemoryRecord.objects.count()
        preview = npcs.recall(f"#{self.owner}", {"query": "合成記憶"})
        direct = fast_recall(owner_id=self.owner, requester_id=self.owner, query="合成記憶")
        self.assertEqual(preview["generation"], direct.generation)
        self.assertEqual(
            [entry["id"] for entry in preview["core"]], [view.id for view in direct.core]
        )
        self.assertEqual(
            [entry["id"] for entry in preview["working"]],
            [view.id for view in direct.working],
        )
        self.assertEqual(
            [entry["id"] for entry in preview["recalled"]],
            [entry.view.id for entry in direct.recalled],
        )
        self.assertEqual(
            [entry["score"]["final"] for entry in preview["recalled"]],
            [entry.final_score for entry in direct.recalled],
        )
        self.assertEqual(preview["owner_id"], self.owner)
        self.assertEqual(stored_attribute_keys(self.npc), before_keys)
        self.assertEqual(MemoryRecord.objects.count(), before_rows)

    def test_recall_thread_and_inclusion_options_are_forwarded(self):
        self._memory(tick=1, tier="core")
        superseded = self._memory(tick=2, availability="superseded", tier="working")
        preview = npcs.recall(
            f"#{self.owner}",
            {"query": "合成記憶", "include_superseded": True, "include_inactive": True},
        )
        direct = fast_recall(
            owner_id=self.owner,
            requester_id=self.owner,
            query="合成記憶",
            include_superseded=True,
            include_inactive=True,
        )
        self.assertEqual(
            [entry["id"] for entry in preview["working"]],
            [view.id for view in direct.working],
        )
        self.assertIn(superseded.pk, [entry["id"] for entry in preview["working"]])

    def test_recall_preserves_the_thread_permission_gate(self):
        # An unknown/inaccessible thread contributes no content: the preview
        # reports exactly what the authoritative recall reports, never more.
        self._memory(tick=1, tier="core")
        preview = npcs.recall(f"#{self.owner}", {"query": "合成記憶", "thread": "t_thread"})
        direct = fast_recall(
            owner_id=self.owner,
            requester_id=self.owner,
            query="合成記憶",
            thread_id="t_thread",
        )
        self.assertEqual([entry["id"] for entry in preview["core"]], [])
        self.assertEqual([entry["id"] for entry in preview["working"]], [])
        self.assertEqual(
            [entry["id"] for entry in preview["recalled"]],
            [entry.view.id for entry in direct.recalled],
        )
        self.assertEqual(preview["thread_id"], direct.thread_id)

    def test_recall_refuses_an_oversized_query_before_execution(self):
        self._memory(tick=1)
        boundary = npcs.recall(f"#{self.owner}", {"query": "x" * 2000})
        self.assertIsInstance(boundary, dict)
        with self.assertRaises(Exception) as too_long:
            npcs.recall(f"#{self.owner}", {"query": "x" * 2001})
        self.assertEqual(too_long.exception.code, "query_too_long")

    def test_recall_refuses_a_missing_or_non_npc_target(self):
        with self.assertRaises(Exception) as malformed:
            npcs.recall("not-a-dbref", {"query": ""})
        self.assertEqual(malformed.exception.code, "invalid_filter")
        with self.assertRaises(Exception) as missing:
            npcs.recall("#999999", {"query": ""})
        self.assertEqual(missing.exception.code, "object_not_found")
        with self.assertRaises(Exception) as wrong_kind:
            npcs.recall(f"#{self.char1.pk}", {"query": ""})
        self.assertEqual(wrong_kind.exception.code, "object_not_found")

    def test_viewing_the_narrative_tabs_creates_no_attributes(self):
        self._memory(tick=1)
        self._dialogue("t_player_a", 1)
        snapshot = self._snapshot(1)
        before = stored_attribute_keys(self.npc)
        stored_rows = {
            model.__name__: model.objects.count()
            for model in (MemoryRecord, MemoryRevision, DialogueEpoch, DialogueFrame,
                          NarrativeContextSnapshot)
        }
        npcs.memory_list_items({"owner": f"#{self.owner}"})
        npcs.snapshot_list_items({"owner": f"#{self.owner}"})
        npcs.dialogue_list_items({"owner": f"#{self.owner}"})
        npcs.snapshot_detail(snapshot.snapshot_id, {"owner": f"#{self.owner}"})
        npcs.recall(f"#{self.owner}", {"query": "合成記憶"})
        self.assertEqual(stored_attribute_keys(self.npc), before)
        self.assertEqual(
            {model.__name__: model.objects.count()
             for model in (MemoryRecord, MemoryRevision, DialogueEpoch, DialogueFrame,
                           NarrativeContextSnapshot)},
            stored_rows,
        )
        self.assertIsNone(read_attr(self.npc, "dialogue_memory", default=None))
        self.assertEqual(
            len(get_owner_memories(owner_id=self.owner, requester_id=self.owner)), 1
        )
