"""Contract tests for the MP cost-tier lookup."""

from dataclasses import replace
import unittest

from world.skills.cost_tiers import MP_COST_TIERS, spell_tier_for
from world.skills.registry import SKILL_REGISTRY


class SpellTierLookupTests(unittest.TestCase):
    def test_existing_spells_map_to_their_cost_bands(self):
        self.assertEqual(spell_tier_for(SKILL_REGISTRY["fire_ball"]), "術師")
        self.assertEqual(spell_tier_for(SKILL_REGISTRY["wind_blade"]), "術師")

    def test_non_spell_skills_are_never_gated(self):
        for key in (
            "basic_attack",
            "shadow_slash",
            "dual_wield_style",
            "status_disguise",
            "fire_mastery",
            "flight",
        ):
            with self.subTest(key=key):
                self.assertIsNone(spell_tier_for(SKILL_REGISTRY[key]))

    def test_target_spec_column_resolves_overlapping_bands(self):
        single20 = replace(SKILL_REGISTRY["fire_ball"], cost={"mp": 20})
        area20 = replace(SKILL_REGISTRY["wind_blade"], cost={"mp": 20})
        self.assertEqual(spell_tier_for(single20), "術師")
        self.assertEqual(spell_tier_for(area20), "學徒")

    def test_cost_in_the_opposite_column_falls_back_within_the_tier(self):
        area70 = replace(SKILL_REGISTRY["wind_blade"], cost={"mp": 70})
        self.assertEqual(spell_tier_for(area70), "賢者")
        single85 = replace(SKILL_REGISTRY["fire_ball"], cost={"mp": 85})
        self.assertEqual(spell_tier_for(single85), "賢者")
        single17 = replace(SKILL_REGISTRY["fire_ball"], cost={"mp": 17})
        self.assertEqual(spell_tier_for(single17), "學徒")

    def test_self_target_spells_use_the_single_direct_column(self):
        self_spell = replace(
            SKILL_REGISTRY["status_disguise"],
            element="wind",
            cost={"mp": 22},
        )
        self.assertEqual(spell_tier_for(self_spell), "術師")

    def test_out_of_band_cost_fails_closed(self):
        for cost in (5, 115, 200):
            with self.subTest(cost=cost):
                with self.assertRaises(ValueError):
                    spell_tier_for(
                        replace(SKILL_REGISTRY["fire_ball"], cost={"mp": cost})
                    )

    def test_malformed_elemental_cost_fails_closed(self):
        for cost in (0, -3, "20"):
            with self.subTest(cost=cost):
                with self.assertRaises(ValueError):
                    spell_tier_for(
                        replace(SKILL_REGISTRY["fire_ball"], cost={"mp": cost})
                    )

    def test_tier_tables_share_the_five_rank_titles(self):
        from world.rules.progression import MAGIC_TIER_THRESHOLDS

        self.assertEqual(
            set(MP_COST_TIERS),
            set(MAGIC_TIER_THRESHOLDS),
            "cost tiers and cast-gate thresholds must stay keyed identically",
        )
        # 主宰's cost band starts at 90 while its cast gate sits at 91 — a
        # deliberate split documented in element-mastery-cast-gate design.md.
        self.assertEqual(MP_COST_TIERS["主宰"].min_level, 90)
        self.assertEqual(MAGIC_TIER_THRESHOLDS["主宰"], 91)
