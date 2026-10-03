"""Behavior tests for narrative context assembly, rendered budgets, and immutable snapshots.

Synthetic fixtures only; all generative paths run offline through FakeLLMClient.
"""

from __future__ import annotations

import json
from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTestCase
from django.db import transaction

from world.ai import guardrail as guardrail_module
from world.ai.fake_client import FakeLLMClient
from world.ai.guardrail import guarded_call
from world.ai.profiles import LLMProfile
from world.ai.schemas import ChatRequestDescriptor
from world.narrative.context import (
    RENDERING_VERSION,
    SECTION_ORDER,
    ContextBudgetExceededError,
    ContextPermissionError,
    ContextProvenanceError,
    SnapshotNotFoundError,
    assemble_narrative_context,
    build_budget_profile,
    build_request_descriptor,
    estimate_tokens,
    get_context_snapshot,
    persist_context_snapshot,
    reuse_snapshot_for_retry,
)
from world.narrative.memory import (
    get_owner_generation,
    get_owner_memories,
    record_memory,
    revise_memory,
)
from world.narrative.models import NarrativeContextSnapshot

from tools.spec_traceability import covers_requirement

REPLY_SCHEMA = {
    "type": "object",
    "required": ["reply"],
    "properties": {"reply": {"type": "string"}},
}


def await_result(d):
    """Return an already-resolved Deferred's result, swallowing its errback."""
    result = d.result
    d.addErrback(lambda f: None)
    return result


def _capturing_facade(calls: list, real) -> None:
    """Facade wrapper that captures (event, context) and still writes the real log.

    Patching only the caller-module binding and calling the pre-patch real
    function keeps the privacy assertions non-vacuous: the actual facade body
    executes for every event.
    """

    def capture(event, *, exc=None, context=None):
        if not isinstance(event, str) or not event.replace("_", "").isalnum():
            raise AssertionError(f"event {event!r} is not snake_case")
        if not isinstance(context, dict):
            raise AssertionError(f"event {event!r} context must be a dict")
        calls.append((event, dict(context or {})))
        real(event, exc=exc, context=context)

    return capture


class NarrativeContextAssemblyTests(EvenniaTestCase):
    """Rendered budgets, permissioned composition, and reproducible ordering."""

    def setUp(self):
        super().setUp()
        self.owner_id = "npc_yohanna_ctx"
        self.llm_profile = LLMProfile(
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
        self.budget_profile = build_budget_profile(
            self.llm_profile,
            context_window=2000,
            deep_recall_reservation=300,
            safety_margin=100,
        )

    def _assemble(self, **overrides):
        kwargs = dict(
            capability="npc-dialogue",
            prompt_version="v1.0",
            owner_id=self.owner_id,
            requester_id=self.owner_id,
            budget_profile=self.budget_profile,
            global_rules="規則：必須以正體中文回覆。",
            capability_contract="契約：僅提供對話，不執行交易。",
            character_anchor="人物：尤漢娜，繼承家業的熱心木桶匠。",
        )
        kwargs.update(overrides)
        return assemble_narrative_context(**kwargs)

    @covers_requirement("narrative-context::rendered-context-obeys-profile-budgets")
    def test_repeated_assembly_is_deterministic_and_stably_ordered(self):
        """Identical inputs assemble to identical rendered output in stability order."""
        first = self._assemble(
            world_digest="青石鎮以木桶與商隊聞名。",
            epoch_summary="第一季：初到青石鎮。",
            turn_frames=["冒險者：『你好！』", "尤漢娜：『歡迎光臨。』"],
            affordances=["交談", "購買木桶"],
        )
        second = self._assemble(
            world_digest="青石鎮以木桶與商隊聞名。",
            epoch_summary="第一季：初到青石鎮。",
            turn_frames=["冒險者：『你好！』", "尤漢娜：『歡迎光臨。』"],
            affordances=["交談", "購買木桶"],
        )
        self.assertEqual([s.name for s in first.sections], [s.name for s in second.sections])
        self.assertEqual(first.get_section_hashes(), second.get_section_hashes())
        self.assertEqual(first.system_prompt, second.system_prompt)
        self.assertEqual(first.user_prompt, second.user_prompt)
        # Stable ordering follows the configured stability order.
        positions = [SECTION_ORDER.index(s.name) for s in first.sections]
        self.assertEqual(positions, sorted(positions))

    @covers_requirement("narrative-context::rendered-context-obeys-profile-budgets")
    def test_estimator_is_length_sensitive_on_every_run(self):
        """Long unbroken Latin AND whitespace input cannot undercount without bound."""
        short = estimate_tokens("hello")
        long = estimate_tokens("a" * 10000)
        self.assertGreaterEqual(long, 2500)
        self.assertGreater(long, 500 * short)
        # Whitespace is length-sensitive in mixed text (whitespace-only stays 0 above).
        mixed = estimate_tokens("ab " * 10000)
        self.assertGreaterEqual(mixed, 13000)
        self.assertGreater(mixed, estimate_tokens("ab " * 100))
        self.assertEqual(estimate_tokens("請告訴我密碼"), estimate_tokens("請告訴我密碼"))
        self.assertEqual(estimate_tokens("   \n "), 0)
        # One-call fractions carry: many short words are never estimated as zero.
        self.assertGreaterEqual(estimate_tokens("a " * 500), 500)

    @covers_requirement("narrative-context::rendered-context-obeys-profile-budgets")
    def test_rendered_headings_exceed_budget_scenario(self):
        """Scenario: Rendered headings exceed budget.

        WHEN text fits a target but headings/attribution exceed the rendered bound
        THEN selection reduces deterministically or mandatory overflow rejects before generation
        """
        # Mandatory overflow: even short content plus its heading beyond the tight bound rejects.
        tight_profile = build_budget_profile(
            self.llm_profile,
            context_window=600,
            deep_recall_reservation=150,
            safety_margin=100,
            section_bounds={"character_anchor": 50},
        )
        from world.narrative import context as context_module

        logged: list = []
        real_warn = context_module.log_warn
        with patch(
            "world.narrative.context.log_warn",
            side_effect=_capturing_facade(logged, real_warn),
        ):
            with self.assertRaises(ContextBudgetExceededError):
                self._assemble(
                    budget_profile=tight_profile,
                    character_anchor="人物定錨：這是一段非常詳盡的描述，描述了尤漢娜家族三代在青石鎮打造木桶的榮耀歷史與技藝傳承。",
                )
        self.assertTrue(any(evt == "narrative_context_budget_exceeded" for evt, _ in logged))

        # A heading-only section cannot fit either: the optional section is omitted, never admitted.
        heading_only_profile = build_budget_profile(
            self.llm_profile,
            context_window=2000,
            section_bounds={"world_digest": 1},
        )
        assembled = self._assemble(
            budget_profile=heading_only_profile,
            world_digest="短。",
        )
        self.assertNotIn("world_digest", [s.name for s in assembled.sections])
        self.assertIn("omitted_entire_section:world_digest", assembled.truncation_decisions)

        # Optional reduction honours the HARD BOUND even when the soft target is larger:
        # every admitted section's rendered representation (heading included) fits
        # its bound, and the total fits the aggregate input budget.
        inverted_profile = build_budget_profile(
            self.llm_profile,
            context_window=1000,
            deep_recall_reservation=200,
            safety_margin=100,
            section_targets={"turn_frames": 4000},
            section_bounds={"turn_frames": 200},
        )
        long_turns = [
            f"冒險者：『這是第 {i} 次交談，我們來聊聊城裡的各種八卦和歷史故事吧！』"
            for i in range(10)
        ]
        assembled = self._assemble(
            budget_profile=inverted_profile,
            global_rules="規則：正常對話。",
            capability_contract="契約：NPC問答。",
            character_anchor="人物：尤漢娜。",
            turn_frames=long_turns,
        )
        self.assertTrue(assembled.truncation_decisions)
        turn = next(s for s in assembled.sections if s.name == "turn_frames")
        self.assertLessEqual(turn.token_count, 200)  # hard bound, rendered representation
        self.assertLess(
            assembled.budget_accounting["total_rendered_tokens"],
            assembled.budget_accounting["max_input_budget"] + 1,
        )

    @covers_requirement("narrative-context::rendered-context-obeys-profile-budgets")
    def test_aggregate_budget_bounds_the_exact_joined_messages(self):
        """Per-section floor-rounded estimates can understate the joined prompt;
        the aggregate bound is enforced on the sent representation itself."""
        for window in range(140, 620, 13):
            profile = build_budget_profile(
                self.llm_profile,
                context_window=window,
                deep_recall_reservation=30,
                safety_margin=30,
            )
            try:
                assembled = self._assemble(
                    budget_profile=profile,
                    world_digest="青石鎮以木桶與商隊聞名，鎮民純樸。",
                    epoch_summary="第一季：初到青石鎮，結識木桶匠。",
                    turn_frames=["冒險者：『你好！』", "尤漢娜：『歡迎光臨。』"],
                )
            except ContextBudgetExceededError:
                continue  # mandatory-only overflow legitimately rejects
            joined = (
                estimate_tokens(assembled.system_prompt)
                + estimate_tokens(assembled.user_prompt)
            )
            self.assertEqual(
                assembled.budget_accounting["total_rendered_tokens"], joined
            )
            self.assertLessEqual(
                joined, assembled.budget_accounting["max_input_budget"]
            )
        # (Determinism of the joined-vs-accounting invariant above is the load-bearing
        # assertion; per-window reductions are exercised by the budget scenario test.)

    @covers_requirement("narrative-context::generation-retains-an-immutable-source-snapshot")
    def test_permissioned_composition_and_thin_descriptor(self):
        """Cross-owner requests reject; inaccessible memories are excluded, thin descriptor binds."""
        with self.assertRaises(ContextPermissionError):
            self._assemble(requester_id="unauthorized_intruder")

        # Foreign private memory is excluded; a genuinely public one may be composed.
        record_memory(
            owner_id="secret_director",
            content={"summary": "機密劇情暗線：鎮長密謀。"},
            tick=5,
            category="secret",
            tier="working",
            salience=5,
            knowledge_scope="witnessed",
            confidence=1.0,
            subjects=["mayor"],
            source_id="secret_plot_001",
        )
        record_memory(
            owner_id="town_chronicle",
            content={"summary": "青石鎮建鎮百年慶典公告。"},
            tick=6,
            category="observation",
            tier="working",
            salience=1,
            knowledge_scope="public",
            confidence=1.0,
            subjects=["festival"],
            source_id="public_notice_002",
        )
        self.record, _, _ = record_memory(
            owner_id=self.owner_id,
            content={"summary": "與冒險者在青石鎮初次相遇。"},
            tick=10,
            category="observation",
            tier="working",
            salience=3,
            knowledge_scope="witnessed",
            confidence=1.0,
            subjects=["barrel"],
            source_id="test_encounter_101",
        )
        candidates = get_owner_memories(owner_id=self.owner_id)
        candidates += get_owner_memories(owner_id="secret_director")
        candidates += get_owner_memories(owner_id="town_chronicle")

        assembled = self._assemble(recalled_memories=candidates, turn_frames=["冒險者：『你好！』"])

        owners = {s.owner_id for s in assembled.sources}
        self.assertEqual(owners, {self.owner_id, "town_chronicle"})
        source_ids = {s.source_id for s in assembled.sources}
        self.assertNotIn("secret_plot_001", source_ids)
        self.assertIn("public_notice_002", source_ids)
        self.assertIn("test_encounter_101", source_ids)
        self.assertEqual(len(assembled.sources), 2)

        snapshot = persist_context_snapshot(assembled)
        descriptor = build_request_descriptor(assembled, snapshot, trace_id="trace_t_1")
        self.assertEqual(descriptor.capability, "npc-dialogue")
        self.assertEqual(descriptor.snapshot_id, snapshot.snapshot_id)
        self.assertEqual(descriptor.trace_id, "trace_t_1")
        self.assertEqual(descriptor.owner_generation, assembled.owner_generation)
        self.assertEqual([m["role"] for m in descriptor.messages], ["system", "user"])

    @covers_requirement("narrative-context::generation-retains-an-immutable-source-snapshot")
    def test_descriptor_rejects_unrelated_snapshot_provenance(self):
        """A descriptor cannot bind one context to another snapshot's identity OR content."""
        assembled_a = self._assemble(character_anchor="人物：尤漢娜。")
        assembled_b = self._assemble(capability="correspondence-reply", prompt_version="v2.0")
        snapshot_b = persist_context_snapshot(assembled_b)
        with self.assertRaises(ContextProvenanceError):
            build_request_descriptor(assembled_a, snapshot_b)
        # Same metadata, different content: pairing must still reject on captured-message
        # disagreement, or the first request and its retries would disagree.
        assembled_c = self._assemble(turn_frames=["冒險者：『甲版本內容。』"])
        assembled_d = self._assemble(turn_frames=["冒險者：『乙版本內容。』"])
        snapshot_d = persist_context_snapshot(assembled_d)
        with self.assertRaises(ContextProvenanceError):
            build_request_descriptor(assembled_c, snapshot_d)


class NarrativeContextSnapshotTests(EvenniaTestCase):
    """Immutable snapshots, generation invalidation, offline reconstruction."""

    def setUp(self):
        super().setUp()
        self.owner_id = "npc_yohanna_snap"
        self.llm_profile = LLMProfile(
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
        self.budget_profile = build_budget_profile(
            self.llm_profile,
            context_window=2000,
            deep_recall_reservation=300,
            safety_margin=100,
        )

    def _assemble(self, **overrides):
        kwargs = dict(
            capability="npc-dialogue",
            prompt_version="v1.0",
            owner_id=self.owner_id,
            requester_id=self.owner_id,
            budget_profile=self.budget_profile,
            global_rules="規則：繁體中文。",
            capability_contract="契約：日常對話。",
            character_anchor="人物：尤漢娜。",
        )
        kwargs.update(overrides)
        return assemble_narrative_context(**kwargs)

    @covers_requirement("narrative-context::generation-retains-an-immutable-source-snapshot")
    def test_sources_change_before_retry_scenario(self):
        """Scenario: Sources change before retry.

        WHEN effective memory changes after capture
        THEN retry uses captured revisions while new generation sees the changed generation
        """
        diary, _, _ = record_memory(
            owner_id=self.owner_id,
            content={"summary": "尤漢娜記得祖父留下的圖紙。"},
            tick=10,
            category="observation",
            tier="working",
            salience=4,
            knowledge_scope="witnessed",
            confidence=1.0,
            subjects=["blueprint"],
            source_id="test_blueprint_101",
        )
        initial_gen = get_owner_generation(self.owner_id)
        assembled1 = self._assemble(
            recalled_memories=get_owner_memories(owner_id=self.owner_id),
            turn_frames=["冒險者：『你好。』"],
        )
        self.assertEqual(assembled1.owner_generation, initial_gen)
        captured_source = next(
            s for s in assembled1.sources if s.source_id == "test_blueprint_101"
        )
        self.assertEqual(captured_source.revision_number, 1)
        self.assertIn("祖父留下的圖紙", assembled1.user_prompt)

        snapshot = persist_context_snapshot(assembled1)

        # Effective memory changes: a revision bumps the read revision and the generation.
        revise_memory(record=diary, tier="core")
        record_memory(
            owner_id=self.owner_id,
            content={"summary": "尤漢娜發現了新的家族秘密日記。"},
            tick=20,
            category="observation",
            tier="core",
            salience=5,
            knowledge_scope="witnessed",
            confidence=1.0,
            subjects=["secret_diary"],
            source_id="test_diary_202",
        )
        new_gen = get_owner_generation(self.owner_id)
        self.assertGreater(new_gen, initial_gen)

        # Retry reconstructs the EXACT captured messages from the authoritative row.
        retry_desc = reuse_snapshot_for_retry(
            snapshot,
            attempt=1,
            trace_id="retry_trace_001",
            validation_error_message={"role": "user", "content": "格式錯誤：請回覆JSON。"},
        )
        self.assertEqual(
            retry_desc.messages[:2],
            tuple({"role": m["role"], "content": m["content"]} for m in assembled1.to_messages()),
        )
        self.assertEqual(retry_desc.messages[2]["content"], "格式錯誤：請回覆JSON。")
        self.assertNotIn("新的家族秘密日記", retry_desc.messages[1]["content"])
        self.assertEqual(retry_desc.owner_generation, initial_gen)
        persisted = get_context_snapshot(snapshot.snapshot_id)
        self.assertEqual(
            [s["revision_number"] for s in persisted.sources
             if s["source_id"] == "test_blueprint_101"],
            [1],
        )

        # A new generation sees the changed generation, new memory, and read revision 2.
        assembled2 = self._assemble(
            recalled_memories=get_owner_memories(owner_id=self.owner_id),
            turn_frames=["冒險者：『你好。』"],
        )
        self.assertEqual(assembled2.owner_generation, new_gen)
        self.assertIn("新的家族秘密日記", assembled2.user_prompt)
        changed_source = next(
            s for s in assembled2.sources if s.source_id == "test_blueprint_101"
        )
        self.assertEqual(changed_source.revision_number, 2)

    @covers_requirement("narrative-context::generation-retains-an-immutable-source-snapshot")
    def test_offline_reconstruction_scenario(self):
        """Scenario: Offline reconstruction.

        WHEN the process restarts with services disabled
        THEN retained snapshots reconstruct and permitted recall remains deterministic

        Evennia's test harness cannot fork a real restarted process, so this
        exercises the restart-equivalent path: a database-only reload (no
        generation, no services) of the persisted row.
        """
        record, _, _ = record_memory(
            owner_id=self.owner_id,
            content={"summary": "離線重建驗證記憶。"},
            tick=30,
            category="observation",
            tier="working",
            salience=2,
            knowledge_scope="witnessed",
            confidence=1.0,
            subjects=["offline"],
            source_id="test_offline_303",
        )
        assembled = self._assemble(
            global_rules="規則：離線重建驗證。",
            capability_contract="契約：純離線模式。",
            character_anchor="人物：尤漢娜（離線）。",
            recalled_memories=get_owner_memories(owner_id=self.owner_id),
            turn_frames=["冒險者：『離線狀態測試。』"],
        )
        snap = persist_context_snapshot(assembled)

        # Restart-equivalent: retrieve from the database only, no services.
        loaded = get_context_snapshot(snap.snapshot_id)
        self.assertEqual(loaded.capability, "npc-dialogue")
        self.assertEqual(loaded.prompt_version, "v1.0")
        self.assertEqual(loaded.rendering_version, RENDERING_VERSION)
        self.assertEqual(loaded.section_hashes, assembled.get_section_hashes())
        rebuilt = reuse_snapshot_for_retry(loaded, attempt=0, trace_id="restart_trace")
        self.assertEqual(rebuilt.messages, assembled.to_messages())

        # Permitted recall stays deterministic after reconstruction.
        reassembled = self._assemble(
            global_rules="規則：離線重建驗證。",
            capability_contract="契約：純離線模式。",
            character_anchor="人物：尤漢娜（離線）。",
            recalled_memories=get_owner_memories(owner_id=self.owner_id),
            turn_frames=["冒險者：『離線狀態測試。』"],
        )
        self.assertEqual(reassembled.get_section_hashes(), assembled.get_section_hashes())

        # Immutability: instance writes, deletes, and bulk ORM paths all refuse.
        loaded.prompt_version = "v2.0"
        with self.assertRaises(ValueError):
            loaded.save()
        with self.assertRaises(ValueError):
            loaded.delete()
        with self.assertRaises(ValueError), transaction.atomic():
            NarrativeContextSnapshot.objects.filter(
                snapshot_id=snap.snapshot_id
            ).update(capability="tampered")
        with self.assertRaises(ValueError), transaction.atomic():
            NarrativeContextSnapshot.objects.filter(
                snapshot_id=snap.snapshot_id
            ).delete()
        tamper = get_context_snapshot(snap.snapshot_id)
        tamper.capability = "tampered"
        with self.assertRaises(ValueError), transaction.atomic():
            NarrativeContextSnapshot.objects.bulk_update([tamper], ["capability"])
        fresh = NarrativeContextSnapshot(snapshot_id=snap.snapshot_id, capability="tampered",
                                        prompt_version="v9", rendering_version=RENDERING_VERSION,
                                        owner_id=self.owner_id)
        with self.assertRaises(ValueError), transaction.atomic():
            NarrativeContextSnapshot.objects.bulk_create(
                [fresh],
                update_conflicts=True,
                update_fields=["capability"],
                unique_fields=["snapshot_id"],
            )
        self.assertEqual(
            get_context_snapshot(snap.snapshot_id).capability, "npc-dialogue"
        )
        self.assertEqual(record.source_id, "test_offline_303")

    @covers_requirement("narrative-context::generation-retains-an-immutable-source-snapshot")
    def test_retry_trusts_persisted_history_over_caller_mutation(self):
        """A caller-mutated in-memory snapshot cannot substitute content for history."""
        assembled = self._assemble(turn_frames=["冒險者：『原版內容。』"])
        snap = persist_context_snapshot(assembled)

        snap.rendered_payload = {"system_prompt": "注入", "user_prompt": "替換"}
        snap.owner_generation = 999

        retry_desc = reuse_snapshot_for_retry(snap, attempt=1, trace_id="t")
        self.assertEqual(retry_desc.messages[:2], assembled.to_messages())
        self.assertNotEqual(retry_desc.owner_generation, 999)

    @covers_requirement("narrative-context::generation-retains-an-immutable-source-snapshot")
    def test_missing_payload_fails_named_instead_of_substituting(self):
        """Hashes alone never stand in for reconstructible captured content."""
        hollow = NarrativeContextSnapshot.objects.create(
            snapshot_id="snap_hollow_1",
            capability="npc-dialogue",
            prompt_version="v1.0",
            rendering_version=RENDERING_VERSION,
            owner_id=self.owner_id,
        )
        with self.assertRaises(ContextProvenanceError):
            reuse_snapshot_for_retry(hollow, attempt=1, trace_id="t")
        with self.assertRaises(SnapshotNotFoundError):
            get_context_snapshot("snap_absent_404")

    @covers_requirement("narrative-context::rendered-context-obeys-profile-budgets")
    def test_retry_feedback_overflow_rejects_before_generation(self):
        """Oversized retry feedback rejects against the captured budget, never overruns it."""
        tight = build_budget_profile(
            self.llm_profile,
            context_window=700,
            deep_recall_reservation=100,
            safety_margin=100,
        )
        assembled = self._assemble(
            budget_profile=tight,
            global_rules="規則：正常。",
            capability_contract="契約：對話。",
            character_anchor="人物：尤漢娜，青石鎮木桶匠。",
            turn_frames=["冒險者：『近滿預算的一長段對話記錄內容。』"],
        )
        snap = persist_context_snapshot(assembled)
        logged: list = []
        from world.narrative import context as context_module

        real_warn = context_module.log_warn
        with patch(
            "world.narrative.context.log_warn",
            side_effect=_capturing_facade(logged, real_warn),
        ):
            with self.assertRaises(ContextBudgetExceededError):
                reuse_snapshot_for_retry(
                    snap,
                    attempt=1,
                    trace_id="overflow_trace",
                    validation_error_message={"role": "user", "content": "x" * 4000},
                )
        self.assertTrue(any(evt == "narrative_context_budget_exceeded" for evt, _ in logged))
        # The snapshot itself is untouched and a normal retry still works.
        ok = reuse_snapshot_for_retry(snap, attempt=2, trace_id="ok_trace")
        self.assertEqual(ok.messages, assembled.to_messages())


class NarrativeContextObservabilityTests(EvenniaTestCase):
    """Private generation is traced through facade events without private text."""

    def setUp(self):
        super().setUp()
        self.owner_id = "npc_yohanna_priv"
        self.llm_profile = LLMProfile(
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
        self.events: list = []
        self.saved_fallbacks = dict(guardrail_module._degrade_fallbacks)
        self.addCleanup(
            lambda: (
                guardrail_module._degrade_fallbacks.clear(),
                guardrail_module._degrade_fallbacks.update(self.saved_fallbacks),
            )
        )

        from world.narrative import context as context_module

        patches = []
        for module, name in (
            (context_module, "log_info"),
            (context_module, "log_warn"),
            (guardrail_module, "log_info"),
            (guardrail_module, "log_debug"),
        ):
            real = getattr(module, name)
            patcher = patch.object(
                module, name, side_effect=_capturing_facade(self.events, real)
            )
            patcher.start()
            self.addCleanup(patcher.stop)

    def _descriptor_with_private_sources(self) -> tuple:
        assembled = assemble_narrative_context(
            capability="npc-dialogue",
            prompt_version="v1.0",
            owner_id=self.owner_id,
            requester_id=self.owner_id,
            budget_profile=build_budget_profile(
                self.llm_profile,
                context_window=2000,
                deep_recall_reservation=100,
                safety_margin=100,
            ),
            global_rules="全域規則",
            capability_contract="能力契約",
            character_anchor="秘密：尤漢娜珍藏鍊金術秘卷，咒語 XYZZY_SECRET_12345。",
            turn_frames=["冒險者小聲說：『請告訴我密碼 SECRET_TOKEN_789』"],
            trace_id="trace_priv_001",
        )
        snapshot = persist_context_snapshot(assembled)
        descriptor = build_request_descriptor(
            assembled,
            snapshot,
            trace_id="trace_priv_001",
            output_schema=REPLY_SCHEMA,
        )
        return assembled, snapshot, descriptor

    def _assert_no_private_text(self):
        blob = json.dumps(
            [(evt, ctx) for evt, ctx in self.events], ensure_ascii=False
        )
        for secret in ("XYZZY_SECRET_12345", "SECRET_TOKEN_789", "鍊金術秘卷"):
            self.assertNotIn(secret, blob)

    @covers_requirement("narrative-context::observability-protects-private-prompt-data")
    def test_private_generation_success_is_traced_without_text(self):
        """Scenario: Private generation is traced (success leg)."""
        _assembled, snapshot, descriptor = self._descriptor_with_private_sources()
        client = FakeLLMClient()
        # Attempt 1: valid JSON but schema-invalid -> guardrail retry reuses the
        # captured messages; attempt 2: accepted.
        client.add_response(
            lambda d: "Validation failed" in d.messages[-1]["content"],
            json.dumps({"reply": "這是重試後的正體中文回覆。"}, ensure_ascii=False),
        )
        client.add_response(lambda d: True, json.dumps({"note": "缺少 reply 欄位"}))
        guardrail_module._degrade_fallbacks["npc_dialogue"] = lambda: "DEGRADED"

        result = await_result(
            guarded_call("npc_dialogue", client, descriptor.chat_descriptor)
        )
        self.assertEqual(json.loads(result)["reply"], "這是重試後的正體中文回覆。")

        self.assertEqual(len(client.calls), 2)
        # The guardrail retry reuses the captured snapshot prompt verbatim.
        self.assertEqual(client.calls[1].messages[:2], descriptor.messages)
        events = [evt for evt, _ in self.events]
        self.assertIn("narrative_context_assembled", events)
        self.assertIn("narrative_snapshot_persisted", events)
        self.assertIn("llm_call", events)
        call_ctx = next(ctx for evt, ctx in self.events if evt == "llm_call")
        self.assertEqual(call_ctx.get("result"), "ok")
        assembled_ctx = next(
            ctx for evt, ctx in self.events if evt == "narrative_context_assembled"
        )
        self.assertEqual(assembled_ctx["trace_id"], "trace_priv_001")
        self.assertGreater(assembled_ctx["rendered_tokens"], 0)
        self.assertEqual(assembled_ctx["owner_id"], self.owner_id)
        persisted_ctx = next(
            ctx for evt, ctx in self.events if evt == "narrative_snapshot_persisted"
        )
        self.assertEqual(persisted_ctx["snapshot_id"], snapshot.snapshot_id)
        self._assert_no_private_text()

    @covers_requirement("narrative-context::observability-protects-private-prompt-data")
    def test_private_generation_degrade_is_traced_without_text(self):
        """Scenario: Private generation is traced (degrade leg)."""
        _assembled, _snapshot, descriptor = self._descriptor_with_private_sources()
        client = FakeLLMClient()
        client.add_response(lambda d: True, json.dumps({"note": "始終不合契約"}))
        guardrail_module._degrade_fallbacks["npc_dialogue"] = lambda: "DEGRADED"

        result = await_result(guarded_call("npc_dialogue", client, descriptor.chat_descriptor))
        self.assertEqual(result, "DEGRADED")

        call_ctxs = [ctx for evt, ctx in self.events if evt == "llm_call"]
        self.assertEqual(len(call_ctxs), 1)
        self.assertEqual(call_ctxs[0].get("result"), "degraded")
        self.assertEqual(call_ctxs[0].get("reason"), "invalid_output")
        self.assertIn("npc_dialogue", str([ctx.get("layer") for ctx in call_ctxs]))
        self._assert_no_private_text()
