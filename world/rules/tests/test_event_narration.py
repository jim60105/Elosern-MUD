"""Pure tests for deterministic narration selection (no database)."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from tools.spec_traceability import covers_requirement

from world.skills.narration import (
    COMPACT_POOLS,
    CONTINUE_MESSAGE,
    DAMAGE_BAND_LINES,
    FAMILY_ROWS,
    HEAL_BAND_LINES,
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

    @covers_requirement(
        "action-narration::variant-selection-is-deterministic-and-consumes-no-gameplay-randomness"
    )
    def test_variant_index_is_stable_across_process_state(self):
        first = variant_index("scope|skill|damage|1|target|solid", 3)
        second = variant_index("scope|skill|damage|1|target|solid", 3)
        self.assertEqual(first, second)
        self.assertGreaterEqual(first, 0)
        self.assertLess(first, 3)
        self.assertEqual(variant_index("anything", 0), 0)

    @covers_requirement(
        "action-narration::variant-selection-is-deterministic-and-consumes-no-gameplay-randomness"
    )
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

    @covers_requirement(
        "action-narration::variant-selection-is-deterministic-and-consumes-no-gameplay-randomness"
    )
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

    @covers_requirement(
        "action-narration::narration-prose-contains-no-numeric-magnitude"
    )
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

    @covers_requirement(
        "action-narration::narration-prose-contains-no-numeric-magnitude"
    )
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

    @covers_requirement(
        "action-narration::sexual-verdicts-and-participant-roles-drive-the-sexual-narration"
    )
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

    @covers_requirement(
        "action-narration::sexual-verdicts-and-participant-roles-drive-the-sexual-narration"
    )
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

    @covers_requirement(
        "action-narration::sexual-verdicts-and-participant-roles-drive-the-sexual-narration"
    )
    def test_the_casters_pleasure_line_differs_from_the_targets(self):
        caster = entry_line(
            "pleasure_gain",
            {"amount": 40},
            skill_key="t_act",
            actor_key="hero",
            target_key="hero",
            actor="hero",
            target="hero",
        )
        target = entry_line(
            "pleasure_gain",
            {"amount": 40},
            skill_key="t_act",
            actor_key="hero",
            target_key="partner",
            actor="hero",
            target="partner",
        )
        self.assertIn("{actor}", caster)
        self.assertNotIn("{actor}", target)
        self.assertIn("{target}", target)
        self.assertNotEqual(caster, target)

    @covers_requirement(
        "action-narration::sexual-verdicts-and-participant-roles-drive-the-sexual-narration"
    )
    def test_the_counter_clause_reflects_who_records_it(self):
        shared_act = SimpleNamespace(
            participant_counters=frozenset({"duo_act_count"})
        )
        actor_act = SimpleNamespace(participant_counters=frozenset())
        shared = entry_line(
            "sexual_counter",
            {"counter": "duo_act_count"},
            act=shared_act,
            actor="hero",
            target="hero",
        )
        actor_only = entry_line(
            "sexual_counter",
            {"counter": "duo_act_count"},
            act=actor_act,
            actor="hero",
            target="hero",
        )
        self.assertIn("{target}", shared)
        self.assertIn("{actor}", actor_only)
        self.assertNotEqual(shared, actor_only)


class MechanicalNarrationTests(unittest.TestCase):
    @covers_requirement(
        "action-narration::mechanical-entries-narrate-qualitatively-instead-of-listing-state-changes"
    )
    def test_two_mechanical_kinds_never_read_alike(self):
        resource = entry_line(
            "resource_spend",
            {"amount": 30, "resource_key": "mp"},
            skill_key="t",
            actor="hero",
        )
        practice = entry_line(
            "skill_practice",
            {"amount": 1},
            skill_key="t",
            actor="hero",
        )
        self.assertNotEqual(resource, practice)
        for legacy in ("消耗了資源", "提升了", "{data"):
            self.assertNotIn(legacy, resource)
            self.assertNotIn(legacy, practice)

    @covers_requirement(
        "action-narration::mechanical-entries-narrate-qualitatively-instead-of-listing-state-changes"
    )
    def test_repeated_casts_can_vary_a_mechanical_line(self):
        lines = {
            entry_line(
                "resource_spend",
                {"amount": 30, "resource_key": "mp"},
                skill_key="t",
                scope=f"scope-{index}",
                actor="hero",
            )
            for index in range(30)
        }
        self.assertGreater(len(lines), 1)


class CompositionTests(unittest.TestCase):
    @covers_requirement(
        "action-narration::a-resolved-action-opens-with-its-own-skill-s-action-narration"
    )
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

    @covers_requirement(
        "action-narration::the-built-line-degrades-to-its-compact-fallback-when-names-do-not-fit"
    )
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
            action=("{actor} 的劍氣破空。",),
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
        self.assertEqual(template, "{actor} 的劍氣破空；{target} 被釘在原地。")

    def test_action_line_prefers_the_exact_row(self):
        row = NarrationRow(key="t_special", action=("{actor} 精確出手——",))
        self.assertEqual(
            action_line("t_special", None, catalog={"t_special": row}, families={}),
            "{actor} 精確出手——",
        )

    @covers_requirement(
        "action-narration::the-built-line-degrades-to-its-compact-fallback-when-names-do-not-fit"
    )
    def test_an_over_long_actor_degrades_the_action_and_marker(self):
        long_actor = "名" * 300
        self.assertEqual(
            action_line(
                "t_special",
                None,
                actor=long_actor,
                catalog={"t_special": NarrationRow("t_special", action=("{actor} 出手——",))},
                families={},
            ),
            COMPACT_POOLS["action_narration"],
        )
        self.assertEqual(
            commanded_action_line("skill", actor=long_actor),
            COMPACT_POOLS["commanded_action"],
        )

    @covers_requirement(
        "action-narration::the-built-line-degrades-to-its-compact-fallback-when-names-do-not-fit"
    )
    def test_the_exact_tier_yields_to_a_fitting_family_tier(self):
        oversized = NarrationRow(
            "t_exact",
            kind_lines={"damage": ("{target}" + "字" * 300, )},
        )
        family = NarrationRow(
            "martial_arts",
            kind_lines={"damage": ("{target} 家族的一擊。", )},
        )
        self.assertEqual(
            entry_line(
                "damage",
                {},
                skill_key="t_exact",
                family="martial_arts",
                target_key="goblin",
                actor="hero",
                target="goblin",
                catalog={"t_exact": oversized},
                families={"martial_arts": family},
            ),
            "{target} 家族的一擊。",
        )

    def test_damage_and_heal_pools_follow_the_band(self):
        self.assertIn(
            entry_line(
                "damage", {"amount": 3}, actor="a", target="t", max_hp=100
            ),
            DAMAGE_BAND_LINES["graze"],
        )
        self.assertIn(
            entry_line(
                "damage", {"amount": 90}, actor="a", target="t", max_hp=100
            ),
            DAMAGE_BAND_LINES["dire"],
        )
        self.assertIn(
            entry_line(
                "heal", {"amount": 80}, actor="a", target="t", max_hp=100
            ),
            HEAL_BAND_LINES["bountiful"],
        )

    def test_a_resisted_act_composes_an_attempt_without_contact(self):
        row = NarrationRow(
            "t_act",
            action=("{actor} 朝對方伸手。",),
        )
        template = compose_first_line(
            "t_act",
            "sexual_act:關係",
            "{target} 輕輕別過臉，拒絕了這場靠近。",
            scope="s",
            target_key="target",
            actor="hero",
            target="target",
            catalog={"t_act": row},
            families=FAMILY_ROWS,
        )
        rendered = template.format(actor="hero", target="target")
        for contact in ("拉住", "貼了上去", "落在對方肩上"):
            self.assertNotIn(contact, rendered)


class StructuralProseTests(unittest.TestCase):
    @covers_requirement(
        "action-narration::structural-combat-prose-is-authored-once-and-stays-stable"
    )
    def test_structural_lines_are_single_numberless_lines(self):
        self.assertFalse(any(ch.isdigit() for ch in CONTINUE_MESSAGE))
        for outcome in ("victory", "defeat", "fled", "exam_passed", "exam_failed", "cap"):
            line = terminal_outcome_message(outcome)
            self.assertTrue(line)
            self.assertFalse(any(ch.isdigit() for ch in line), line)
        self.assertFalse(any(ch.isdigit() for ch in overwhelm_summary_line()))
        for escaped in (True, False):
            self.assertFalse(any(ch.isdigit() for ch in party_retreat_line(escaped)))

    @covers_requirement(
        "action-narration::structural-combat-prose-is-authored-once-and-stays-stable"
    )
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

    @covers_requirement(
        "action-narration::the-built-line-degrades-to-its-compact-fallback-when-names-do-not-fit"
    )
    def test_compact_fallbacks_are_participant_free(self):
        for kind, line in COMPACT_POOLS.items():
            with self.subTest(kind=kind):
                self.assertNotIn("{actor}", line)
                self.assertNotIn("{target}", line)


if __name__ == "__main__":
    unittest.main()
