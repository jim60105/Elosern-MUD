"""Tests for the deterministic bounded npc-dialogue prompt construction."""


import json
import unittest

from world.ai.npc_dialogue import (
    MAX_FIELD_LENGTH,
    MAX_IDENTITY_ENTRIES,
    MAX_MEMORY_LINES,
    MAX_TOTAL_SIZE,
    _TRUNCATION_MARKER,
    build_npc_dialogue_prompt,
)
from world.ai.tests._dialogue_helpers import (
    _memory,
    _npc_context,
    _player_context,
)

from tools.spec_traceability import covers_requirement



class NPCDialoguePromptTests(unittest.TestCase):
    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_identical_inputs_produce_byte_identical_prompts(self):
        first = build_npc_dialogue_prompt(
            _npc_context(), _player_context(), _memory()
        )
        second = build_npc_dialogue_prompt(
            _npc_context(), _player_context(), _memory()
        )
        self.assertEqual(first, second)
        self.assertEqual(first[0]["role"], "system")
        self.assertEqual(first[1]["role"], "user")
        self.assertEqual(first[0]["content"], second[0]["content"])
        self.assertEqual(first[1]["content"], second[1]["content"])

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_disguised_stats_are_injected_so_a_disguised_elf_reads_as_weak(self):
        disguised = {"atk_phys": 5, "agility": 6, "defense": 6}
        system, user = build_npc_dialogue_prompt(
            _npc_context(), _player_context(disguised=disguised), _memory()
        )
        parsed = json.loads(user["content"])
        self.assertEqual(parsed["player"]["disguised_stats"], disguised)
        self.assertIn("atk_phys", user["content"])
        self.assertNotIn("10000", user["content"])

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_oversized_memory_is_truncated_deterministically_with_a_marker(self):
        memory = [f"對話 {i}" for i in range(1, MAX_MEMORY_LINES * 3 + 1)]
        system, user = build_npc_dialogue_prompt(
            _npc_context(), _player_context(), memory
        )
        parsed = json.loads(user["content"])
        self.assertLessEqual(len(parsed["memory"]), MAX_MEMORY_LINES + 1)
        self.assertTrue(any("省略了較早的" in line for line in parsed["memory"]))
        self.assertEqual(parsed["memory"][-1], "對話 36")
        self.assertEqual(parsed["memory"][-2], "對話 35")

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_prompt_is_bounded_and_contains_no_live_entity_reference(self):
        memory = [f"x" * 500 for _ in range(MAX_MEMORY_LINES * 2)]
        system, user = build_npc_dialogue_prompt(
            _npc_context(), _player_context(), memory
        )
        self.assertLessEqual(len(user["content"]), MAX_TOTAL_SIZE)
        self.assertNotIn("<", user["content"])
        self.assertNotIn("object at", user["content"])
        parsed = json.loads(user["content"])
        self.assertLessEqual(
            max(len(line) for line in parsed["memory"]), 201
        )

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_system_message_fixes_role_language_and_output_contract(self):
        system, _ = build_npc_dialogue_prompt(
            _npc_context(), _player_context(), _memory()
        )
        content = system["content"]
        self.assertIn("艾洛希雅", content)
        self.assertIn("伊洛瑟恩大陸", content)
        self.assertIn("正體中文", content)
        self.assertIn("speech", content)
        self.assertIn("intent", content)
        self.assertIn("不得虛構", content)

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_prompt_uses_entity_keys_with_no_true_stats_present(self):
        system, user = build_npc_dialogue_prompt(
            _npc_context(), _player_context(), _memory()
        )
        self.assertIn("薇歐蕾", user["content"])
        self.assertNotIn("atk_phys", system["content"])


class AffinityPromptTests(unittest.TestCase):
    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_affinity_block_carries_the_true_value_cap_and_stage(self):
        context = {"value": 55, "cap": 99, "stage": "信賴"}
        system, user = build_npc_dialogue_prompt(
            _npc_context(), _player_context(), _memory(), affinity_context=context
        )
        parsed = json.loads(user["content"])
        self.assertEqual(
            parsed["player"]["affinity"],
            {"value": 55, "cap": 99, "stage": "信賴"},
        )

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_recordless_player_omits_the_affinity_block(self):
        _, user = build_npc_dialogue_prompt(
            _npc_context(),
            _player_context(),
            _memory(),
            affinity_context=None,
        )
        parsed = json.loads(user["content"])
        self.assertNotIn("affinity", parsed["player"])

    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_prompts_stay_byte_identical_with_and_without_the_block(self):
        context = {"value": 55, "cap": 99, "stage": "信賴"}
        first = build_npc_dialogue_prompt(
            _npc_context(), _player_context(), _memory(), affinity_context=context
        )
        second = build_npc_dialogue_prompt(
            _npc_context(), _player_context(), _memory(), affinity_context=context
        )
        self.assertEqual(first, second)
        self.assertEqual(first[1]["content"], second[1]["content"])
        without = build_npc_dialogue_prompt(_npc_context(), _player_context(), _memory())
        plain = build_npc_dialogue_prompt(
            _npc_context(), _player_context(), _memory(), affinity_context=None
        )
        self.assertEqual(without, plain)
        self.assertNotEqual(first[1]["content"], without[1]["content"])
        self.assertIn('"affinity"', first[1]["content"])


class PersonaPromptTests(unittest.TestCase):
    @covers_requirement("persona-dialogue-injection::the-npc-s-own-persona-feeds-the-dialogue-system-message")
    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_npc_persona_block_lands_in_the_system_message(self):
        block = "性格：沉穩\n人生經歷：曾在邊境服役\n習慣：清晨練劍"
        system, _ = build_npc_dialogue_prompt(
            _npc_context(), _player_context(), _memory(), npc_persona=block
        )
        self.assertIn(block, system["content"])
        self.assertNotIn("{persona}", system["content"])

    @covers_requirement("persona-dialogue-injection::the-npc-s-own-persona-feeds-the-dialogue-system-message")
    def test_absent_npc_persona_keeps_the_byte_identical_baseline(self):
        baseline = build_npc_dialogue_prompt(_npc_context(), _player_context(), _memory())
        empty = build_npc_dialogue_prompt(
            _npc_context(), _player_context(), _memory(), npc_persona=None
        )
        blank = build_npc_dialogue_prompt(
            _npc_context(), _player_context(), _memory(), npc_persona=""
        )
        self.assertEqual(baseline, empty)
        self.assertEqual(baseline, blank)
        self.assertNotIn("{persona}", baseline[0]["content"])
        self.assertNotIn("性格：", baseline[0]["content"])

    @covers_requirement("persona-dialogue-injection::the-npc-s-own-persona-feeds-the-dialogue-system-message")
    def test_persona_block_within_the_store_bound_is_injected_in_full(self):
        block = "性格：" + "字" * 1500
        system, _ = build_npc_dialogue_prompt(
            _npc_context(), _player_context(), _memory(), npc_persona=block
        )
        self.assertIn(block, system["content"])

    @covers_requirement("persona-dialogue-injection::the-player-s-persona-feeds-the-user-payload-as-player-persona")
    @covers_requirement("npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona")
    def test_player_persona_lands_beside_affinity_in_the_user_payload(self):
        block = "性格：溫柔\n人生經歷：商人世家\n習慣：夜間閱讀"
        _, user = build_npc_dialogue_prompt(
            _npc_context(),
            _player_context(),
            _memory(),
            affinity_context={"value": 55, "cap": 99, "stage": "信賴"},
            player_persona=block,
        )
        parsed = json.loads(user["content"])
        self.assertEqual(parsed["player"]["persona"], block)
        self.assertEqual(parsed["player"]["affinity"], {"value": 55, "cap": 99, "stage": "信賴"})

    @covers_requirement("persona-dialogue-injection::the-player-s-persona-feeds-the-user-payload-as-player-persona")
    def test_absent_player_persona_omits_the_block_byte_identically(self):
        baseline = build_npc_dialogue_prompt(_npc_context(), _player_context(), _memory())
        _, user = build_npc_dialogue_prompt(
            _npc_context(), _player_context(), _memory(), player_persona=None
        )
        parsed = json.loads(user["content"])
        self.assertNotIn("persona", parsed["player"])
        self.assertEqual(user["content"], baseline[1]["content"])
        # The pre-persona user payload, pinned byte-for-byte (historical
        # baseline; absent persona must reproduce it exactly).
        self.assertEqual(
            user["content"],
            '{"memory": ["第1則對話", "第2則對話", "第3則對話"], '
            '"player": {"disguised_stats": {"agility": 6, "atk_phys": 5, '
            '"defense": 6}, "name": "薇歐蕾"}}',
        )


class TitleContextPromptTests(unittest.TestCase):
    """The named title sections of the player block (title-system D6)."""

    def _payload(self, player_context):
        _, user = build_npc_dialogue_prompt(_npc_context(), player_context, _memory())
        return json.loads(user["content"])

    def test_absent_title_data_keeps_the_payload_byte_identical(self):
        plain = build_npc_dialogue_prompt(_npc_context(), _player_context(), _memory())
        self.assertNotIn("epithet", plain[1]["content"])
        self.assertNotIn("identity_entries", plain[1]["content"])

    def test_a_non_empty_epithet_becomes_the_named_section(self):
        payload = self._payload(_player_context(epithet="F級冒險者　南門新客"))
        self.assertEqual(payload["player"]["epithet"], "F級冒險者　南門新客")

    def test_blank_or_non_string_epithet_is_omitted_not_placeholdered(self):
        for value in ("", "   ", "\n", None, 7, ["F級冒險者"]):
            with self.subTest(value=value):
                payload = self._payload(_player_context(epithet=value))
                self.assertNotIn("epithet", payload["player"])

    def test_an_oversized_epithet_is_capped_with_the_truncation_marker(self):
        payload = self._payload(_player_context(epithet="長" * 500))
        epithet = payload["player"]["epithet"]
        self.assertEqual(len(epithet), MAX_FIELD_LENGTH)
        self.assertTrue(epithet.endswith(_TRUNCATION_MARKER))

    def test_identity_entries_are_bounded_and_capped(self):
        entries = [
            {"display": f"異名{i}", "basis": f"引文{i}"} for i in range(9)
        ]
        payload = self._payload(_player_context(identity_entries=entries))
        kept = payload["player"]["identity_entries"]
        self.assertEqual(len(kept), MAX_IDENTITY_ENTRIES)
        self.assertEqual(kept[0], {"display": "異名0", "basis": "引文0"})
        long_rows = [
            {"display": "短" * 500, "basis": "長" * 500}
        ]
        payload = self._payload(_player_context(identity_entries=long_rows))
        row = payload["player"]["identity_entries"][0]
        self.assertEqual(len(row["display"]), MAX_FIELD_LENGTH)
        self.assertEqual(len(row["basis"]), MAX_FIELD_LENGTH)

    def test_malformed_identity_rows_and_non_lists_are_dropped(self):
        for value in (
            None,
            "南門新客",
            [],
            [{"basis": "只有引文"}],
            [{"display": "  ", "basis": "引文"}],
            ["南門新客"],
        ):
            with self.subTest(value=value):
                payload = self._payload(_player_context(identity_entries=value))
                self.assertNotIn("identity_entries", payload["player"])
        # A row without a basis keeps only its display.
        payload = self._payload(_player_context(identity_entries=[{"display": "南門新客"}]))
        self.assertEqual(
            payload["player"]["identity_entries"], [{"display": "南門新客"}]
        )

    def test_identical_title_inputs_produce_byte_identical_prompts(self):
        context = _player_context(
            epithet="F級冒險者　南門新客",
            identity_entries=[{"display": "南門新客", "basis": "守衛的目送"}],
        )
        first = build_npc_dialogue_prompt(_npc_context(), context, _memory())
        second = build_npc_dialogue_prompt(_npc_context(), context, _memory())
        self.assertEqual(first[1]["content"], second[1]["content"])
        self.assertNotIn("true_stats", first[1]["content"])
