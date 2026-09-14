"""Data-contract test: MP cost-tier assignment contract
Contract tests for the MP cost-tier lookup."""

from dataclasses import replace
import unittest

from tools.spec_traceability import covers_requirement

from world.skills.cost_tiers import MP_COST_TIERS, spell_tier_for
from world.skills.registry import SKILL_REGISTRY

from world.tests.synthetic_data import SYNTH_SKILLS


class SpellTierLookupTests(unittest.TestCase):
    def test_existing_spells_map_to_their_cost_bands(self):
        self.assertEqual(spell_tier_for(SKILL_REGISTRY["fire_ball"]), "學徒")
        self.assertEqual(spell_tier_for(SKILL_REGISTRY["wind_blade"]), "學徒")

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
        for cost in (5, 115, 261, 300):
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
        """The five mortal rank titles match between progression and cost tiers."""
        from world.rules.progression import MAGIC_TIER_THRESHOLDS

        # The five mortal rank titles match between progression and cost tiers;
        # 神格 is the label-only sixth cost tier with no level band or cast gate.
        self.assertEqual(
            set(MP_COST_TIERS) - {"神格"},
            set(MAGIC_TIER_THRESHOLDS),
            "mortal cost tiers and cast-gate thresholds must stay keyed identically",
        )
        self.assertIsNone(MP_COST_TIERS["神格"].min_level)
        self.assertIsNone(MP_COST_TIERS["神格"].max_level)
        # 主宰's cost band starts at 90 while its cast gate sits at 91 — a
        # deliberate split documented in element-mastery-cast-gate design.md.
        self.assertEqual(MP_COST_TIERS["主宰"].min_level, 90)
        self.assertEqual(MAGIC_TIER_THRESHOLDS["主宰"], 91)

    @covers_requirement("skill-registry::spell-cost-labels-include-a-sixth-tier-with-deterministic-column-precedence")
    def test_divinity_tier_overlap_honors_shape(self):
        """Synthetic SINGLE and AREA 180 MP resolve by target-shape column first."""
        single180 = replace(SKILL_REGISTRY["fire_ball"], cost={"mp": 180})
        area180 = replace(SKILL_REGISTRY["wind_blade"], cost={"mp": 180})
        self.assertEqual(spell_tier_for(single180), "神格")
        self.assertEqual(spell_tier_for(area180), "主宰")

    def test_divinity_tier_boundaries_and_fallback_edges(self):
        """Area and single endpoints in the sixth band resolve to 神格."""
        for mp in (200, 240, 260):
            with self.subTest(shape="area", mp=mp):
                spell = replace(SKILL_REGISTRY["wind_blade"], cost={"mp": mp})
                self.assertEqual(spell_tier_for(spell), "神格")

        for mp in (180, 200, 220):
            with self.subTest(shape="single", mp=mp):
                spell = replace(SKILL_REGISTRY["fire_ball"], cost={"mp": mp})
                self.assertEqual(spell_tier_for(spell), "神格")

        # Fallback edges bridging columns
        single179 = replace(SKILL_REGISTRY["fire_ball"], cost={"mp": 179})
        self.assertEqual(spell_tier_for(single179), "主宰")
        single221 = replace(SKILL_REGISTRY["fire_ball"], cost={"mp": 221})
        self.assertEqual(spell_tier_for(single221), "神格")
        area190 = replace(SKILL_REGISTRY["wind_blade"], cost={"mp": 190})
        self.assertEqual(spell_tier_for(area190), "神格")

    def test_synthetic_skill_configuration_uses_generic_mechanism(self):
        """A second, fully synthetic skill configuration validates the generic mechanism."""
        synth_single = replace(
            SYNTH_SKILLS["t_hush_mend"],
            cost={"mp": 180},
        )
        synth_area = replace(
            SYNTH_SKILLS["t_glowmire_bloom"],
            cost={"mp": 200},
        )
        self.assertEqual(spell_tier_for(synth_single), "神格")
        self.assertEqual(spell_tier_for(synth_area), "神格")

class SpellTierLabelCatalogTests(unittest.TestCase):
    """Every element's representative per-band spells keep their catalog label.

    Relocated from the retired ``SpellTierLabelTests`` in the progression
    suite: the magic-XP gate is gone (magic-xp-engine-retirement), so the
    tier label a spell belongs to is purely shipped catalog data and belongs
    in this registered data-contract file.
    """

    def _assert_labels(self, spell_tiers: dict[str, tuple[str, ...]]) -> None:
        for tier, spell_keys in spell_tiers.items():
            for key in spell_keys:
                with self.subTest(tier=tier, spell=key):
                    self.assertEqual(spell_tier_for(SKILL_REGISTRY[key]), tier)

    @covers_requirement("skill-registry::skill-registry-contains-the-full-火-element-spell-set")
    def test_fire_spell_tier_labels_match_the_catalog(self):
        self._assert_labels(
            {
                "術師": ("firestorm", "scorching_wave"),
                "大師": ("lava_burst", "flame_shroud"),
                "賢者": ("dragon_flame", "hellfire"),
                "主宰": ("sacrificial_flame", "final_blaze"),
            }
        )

    @covers_requirement("skill-registry::skill-registry-contains-the-full-水-element-spell-set")
    def test_water_spell_tier_labels_match_the_catalog(self):
        self._assert_labels(
            {
                "術師": ("healing_spring", "water_shield"),
                "大師": ("abyssal_whirlpool", "wellspring_of_life"),
                "賢者": ("tsunami", "tidal_revival"),
                "主宰": ("sea_of_life", "abyssal_tide"),
            }
        )

    @covers_requirement("skill-registry::skill-registry-contains-the-full-土-element-spell-set")
    def test_earth_spell_tier_labels_match_the_catalog(self):
        self._assert_labels(
            {
                "術師": ("stone_armor", "dust_veil"),
                "大師": ("earth_bind", "rockslide"),
                "賢者": ("earthquake", "earthen_ward"),
                "主宰": ("mountain_collapse", "earths_judgment"),
            }
        )

    @covers_requirement("skill-registry::skill-registry-contains-the-full-風-element-spell-set")
    def test_wind_spell_tier_labels_match_the_catalog(self):
        self._assert_labels(
            {
                "術師": ("tornado_blade",),
                "大師": ("storm_domain", "gale_dance_strike"),
                "賢者": ("heavens_wrath_storm", "haste_domain"),
                "主宰": ("vacuum_severance", "sky_tempest"),
            }
        )

    @covers_requirement("skill-registry::skill-registry-contains-the-full-雷-element-spell-set")
    def test_lightning_spell_tier_labels_match_the_catalog(self):
        self._assert_labels(
            {
                "術師": ("chain_lightning", "paralyzing_bolt"),
                "大師": ("thunder_combo", "lightning_strike"),
                "賢者": ("heavens_thunder", "thunder_gods_haste"),
                "主宰": ("judgement_thunder", "divine_lightning_slaughter"),
            }
        )

    @covers_requirement("skill-registry::skill-registry-contains-the-full-冰-element-spell-set")
    def test_ice_spell_tier_labels_match_the_catalog(self):
        self._assert_labels(
            {
                "術師": ("ice_wall", "frost_arrow_rain"),
                "大師": ("permafrost_domain", "ice_prison"),
                "賢者": ("blizzard", "absolute_tundra"),
                "主宰": ("absolute_zero", "eternal_ice_field"),
            }
        )

    @covers_requirement("skill-registry::skill-registry-contains-the-full-暗-element-spell-set")
    def test_dark_spell_tier_labels_match_the_catalog(self):
        self._assert_labels(
            {
                "術師": ("curse", "dark_burst"),
                "大師": ("dark_corrosion_domain", "shadow_torture"),
                "賢者": ("abyss_devour", "dark_dominion"),
                "主宰": ("void_annihilation", "underworld_judgment"),
            }
        )
