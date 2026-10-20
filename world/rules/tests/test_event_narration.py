"""Pure tests for deterministic narration selection (no database)."""

from __future__ import annotations

import unittest

from world.skills.narration import (
    COMPACT_POOLS,
    CONTINUE_MESSAGE,
    FAMILY_ROWS,
    KIND_POOLS,
    MAX_RENDERED_CODE_POINTS,
    NARRATION_KINDS,
    NarrationRow,
    band_for_entry,
    commanded_action_line,
    compose_first_line,
    engagement_opening_line,
    entry_line,
    narration_seed,
    overwhelm_summary_line,
    party_retreat_line,
    terminal_outcome_message,
    variant_index,
)
from world.skills.narration.select import action_line


class SeedSelectionTests(unittest.TestCase):
    def test_the_seed_order_is_fixed(self):
        self.assertEqual(
            narration_seed("scope", "skill", "damage", 3, "target", "solid"),
            "scope|skill|damage|3|target|solid",
        )
        self.assertEqual(
            narration_seed("", "", "roll", 0, "", ""),
            "||roll|0||",
        )

    def test_variant_index_is_stable_across_process_state(self):
        first = variant_index("scope|skill|damage|1|target|solid", 3)
        second = variant_index("scope|skill|damage|1|target|solid", 3)
        self.assertEqual(first, second)
        self.assertGreaterEqual(first, 0)
        self.assertLess(first, 3)
        self.assertEqual(variant_index("anything", 0), 0)

    def test_the_same_inputs_select_the_same_line(self):
        first = entry_line(
            "damage",
            {"amount": 10},
            skill_key="t",
            scope="s|1|0",
            ordinal=1,
            target_key="goblin",
            actor="hero",
            target="goblin",
            max_hp=100,
        )
        second = entry_line(
            "damage",
            {"amount": 10},
            skill_key="t",
            scope="s|1|0",
            ordinal=1,
            target_key="goblin",
            actor="hero",
            target="goblin",
            max_hp=100,
        )
        self.assertEqual(first, second)

    def test_a_different_scope_can_select_a_different_variant(self):
        lines = {
            entry_line(
                "damage",
                {},
                skill_key="t",
                scope=f"scope-{index}",
                target_key="goblin",
                actor="hero",
                target="goblin",
            )
            for index in range(30)
        }
        self.assertGreater(len(lines), 1)


class BandTests(unittest.TestCase):
    def test_damage_bands_follow_the_target_maximum(self):
        self.assertEqual(band_for_entry("damage", {"amount": 5}, 100), "graze")
        self.assertEqual(band_for_entry("damage", {"amount": 10}, 100), "light")
        self.assertEqual(band_for_entry("damage", {"amount": 20}, 100), "solid")
        self.assertEqual(band_for_entry("damage", {"amount": 40}, 100), "heavy")
        self.assertEqual(band_for_entry("damage", {"amount": 90}, 100), "dire")

    def test_heal_and_pleasure_bands(self):
        self.assertEqual(band_for_entry("heal", {"amount": 5}, 100), "minor")
        self.assertEqual(band_for_entry("heal", {"amount": 25}, 100), "restoring")
        self.assertEqual(band_for_entry("heal", {"amount": 80}, 100), "bountiful")
        self.assertEqual(band_for_entry("pleasure_gain", {"amount": 5}, None), "faint")
        self.assertEqual(band_for_entry("pleasure_gain", {"amount": 55}, None), "strong")

    def test_a_missing_maximum_degrades_to_the_middle_band(self):
        self.assertEqual(band_for_entry("damage", {"amount": 10}, None), "solid")
        self.assertEqual(band_for_entry("heal", {"amount": 10}, 0), "restoring")


class NumberlessProseTests(unittest.TestCase):
    def _data_for(self, kind: str) -> dict:
        return {
            "roll": {"raw_roll": 92, "hit": True},
            "damage": {"amount": 450698},
            "heal": {"amount": 1200},
            "self_heal": {"amount": 1200},
            "resource_spend": {"amount": 30, "resource_key": "mp"},
            "trait_delta": {"trait_key": "mp", "delta": -30},
            "pleasure_gain": {"amount": 40},
            "sexual_counter": {"counter": "duo_act_count"},
            "sexual_resist": {"resisted": True, "auto_comply": False, "roll": 3},
            "sexual_transition": {"event": "climax_ends"},
            "gauge_transfer": {"gauge": "mp", "direction": "drain", "amount": 9},
        }.get(kind, {})

    def test_every_kind_renders_without_a_digit(self):
        for kind in NARRATION_KINDS:
            with self.subTest(kind=kind):
                template = entry_line(
                    kind,
                    self._data_for(kind),
                    skill_key="t",
                    scope="s",
                    target_key="goblin",
                    actor="hero",
                    target="goblin",
                    max_hp=100,
                )
                rendered = template.format(actor="hero", target="goblin")
                self.assertFalse(
                    any(character.isdigit() for character in rendered),
                    rendered,
                )
                self.assertNotIn("{data", template)

    def test_a_miss_still_reads_as_a_miss(self):
        hit = entry_line(
            "roll",
            {"raw_roll": 92, "hit": True},
            target_key="goblin",
            actor="hero",
            target="goblin",
        )
        miss = entry_line(
            "roll",
            {"raw_roll": 3, "hit": False},
            target_key="goblin",
            actor="hero",
            target="goblin",
        )
        self.assertNotEqual(hit, miss)
        for template in (hit, miss):
            self.assertNotIn("92", template)

    def test_a_resisted_act_reads_as_a_refusal(self):
        template = entry_line(
            "sexual_resist",
            {"resisted": True, "auto_comply": False, "roll": None},
            skill_key="t_act",
            target_key="target",
            actor="hero",
            target="target",
        )
        self.assertIn("拒絕", template.format(actor="hero", target="target"))

    def test_a_complied_act_does_not_read_as_a_refusal(self):
        template = entry_line(
            "sexual_resist",
            {"resisted": False, "auto_comply": False, "roll": 55},
            skill_key="t_act",
            target_key="target",
            actor="hero",
            target="target",
        )
        self.assertNotIn("別過臉", template)


class CompositionTests(unittest.TestCase):
    def test_the_action_clause_opens_the_first_line(self):
        template = compose_first_line(
            "t_missing",
            "martial_arts",
            "{target} 的傷勢浮現。",
            scope="s",
            target_key="goblin",
            actor="hero",
            target="goblin",
            catalog={},
            families=FAMILY_ROWS,
        )
        rendered = template.format(actor="hero", target="goblin")
        self.assertTrue(rendered.endswith("{target} 的傷勢浮現。".format(target="goblin")))
        self.assertGreater(len(rendered), len("goblin 的傷勢浮現。"))

    def test_an_over_long_name_degrades_to_the_compact_line(self):
        long_name = "名" * 300
        template = compose_first_line(
            "t_missing",
            "martial_arts",
            "{target} 的傷勢浮現。",
            scope="s",
            target_key=long_name,
            actor="hero",
            target=long_name,
            catalog={},
            families=FAMILY_ROWS,
        )
        self.assertLessEqual(
            sum(1 for _ in template.format(actor="hero", target=long_name)),
            MAX_RENDERED_CODE_POINTS,
        )

    def test_an_authored_override_composes_with_the_action(self):
        row = NarrationRow(
            key="t_special",
            action=("{actor} 的劍氣破空——",),
            kind_lines={"damage": ("{target} 被釘在原地。",)},
        )
        template = compose_first_line(
            "t_special",
            None,
            "{target} 被釘在原地。",
            scope="s",
            target_key="goblin",
            actor="hero",
            target="goblin",
            catalog={"t_special": row},
            families={},
        )
        self.assertEqual(template, "{actor} 的劍氣破空——{target} 被釘在原地。")

    def test_action_line_prefers_the_exact_row(self):
        row = NarrationRow(key="t_special", action=("{actor} 精確出手——",))
        self.assertEqual(
            action_line("t_special", None, catalog={"t_special": row}, families={}),
            "{actor} 精確出手——",
        )


class StructuralProseTests(unittest.TestCase):
    def test_structural_lines_are_single_numberless_lines(self):
        self.assertFalse(any(ch.isdigit() for ch in CONTINUE_MESSAGE))
        for outcome in ("victory", "defeat", "fled", "exam_passed", "exam_failed", "cap"):
            line = terminal_outcome_message(outcome)
            self.assertTrue(line)
            self.assertFalse(any(ch.isdigit() for ch in line), line)
        self.assertFalse(any(ch.isdigit() for ch in overwhelm_summary_line()))
        for escaped in (True, False):
            self.assertFalse(any(ch.isdigit() for ch in party_retreat_line(escaped)))

    def test_the_engagement_opening_names_the_foe(self):
        self.assertEqual(
            engagement_opening_line("哥布林"),
            "你搶先一步，朝哥布林逼了上去。",
        )

    def test_the_commanded_marker_carries_no_payload_field(self):
        for action_kind in ("skill", "item"):
            template = commanded_action_line(action_kind, actor="hero")
            self.assertNotIn("{data", template)
            self.assertFalse(any(ch.isdigit() for ch in template))

    def test_compact_fallbacks_are_participant_free(self):
        for kind, line in COMPACT_POOLS.items():
            with self.subTest(kind=kind):
                self.assertNotIn("{actor}", line)
                self.assertNotIn("{target}", line)


if __name__ == "__main__":
    unittest.main()
