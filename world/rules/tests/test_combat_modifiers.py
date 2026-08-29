"""Tests named one-to-one with combat modifier rule IDs."""

from tools.spec_traceability import covers_requirement

from pathlib import Path
import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.rules.buffs import _add_buff
from world.rules.combat_modifiers import (
    apply_cost_modifier,
    evaluate_combat_modifiers,
    evaluate_combat_modifiers_no_create,
)
from world.rules.rulebook.schema import evaluate_condition, load_rules
from world.skills.handler import ConferredSkillGrant

RULES = {
    rule.id: rule
    for rule in load_rules(
        Path(__file__).parents[1] / "rulebook" / "combat_modifiers.yaml"
    )
}


class CombatModifierTests(EvenniaTestCase):
    def _entity(self):
        entity = create_object(PlayerCharacter, key="modifier target")
        entity.race = "human"
        entity.apply_race_baseline()
        return entity

    def test_rule_poison_agility_penalty(self):
        entity = self._entity()
        _add_buff(entity, "poisoned")
        self.assertEqual(evaluate_combat_modifiers(entity), {"agility": "-10%"})

    def test_rule_paralysis_locks_actions(self):
        entity = self._entity()
        _add_buff(entity, "paralysis")
        self.assertEqual(evaluate_combat_modifiers(entity), {"actions_per_turn": 0})

    def test_rule_fear_agility_and_accuracy_penalty(self):
        entity = self._entity()
        _add_buff(entity, "fear")
        self.assertEqual(
            evaluate_combat_modifiers(entity), {"agility": "-15%", "accuracy": -10}
        )

    def test_rule_focus_accuracy_boost(self):
        entity = self._entity()
        _add_buff(entity, "focus")
        self.assertEqual(evaluate_combat_modifiers(entity), {"accuracy": 10})

    @covers_requirement("combat-modifier-table::combat-modifiers-yaml-is-one-table-evaluated-by-one-condition-engine-with-no", "rulebook-schema::the-effect-then-clause-is-opaque-to-the-shared-schema-module")
    def test_rule_high_arousal_agility_accuracy_penalty(self):
        entity = self._entity()
        entity.sexual.pleasure.base = 60
        self.assertEqual(
            evaluate_combat_modifiers(entity), {"agility": "-20%", "accuracy": -15}
        )
        rule = RULES["high_arousal_agility_accuracy_penalty"]
        entity.sexual.pleasure.base = 35
        self.assertFalse(evaluate_condition(rule.when, {"arousal": entity.sexual.arousal}))
        entity.sexual.pleasure.base = 85
        self.assertTrue(evaluate_condition(rule.when, {"arousal": entity.sexual.arousal}))
        self.assertEqual(rule.then, {"agility": "-20%", "accuracy": -15})

    def test_rule_climax_in_progress_locks_actions(self):
        entity = self._entity()
        entity.sexual.climax_phase.value = "進行中"
        self.assertEqual(evaluate_combat_modifiers(entity), {"actions_per_turn": 0})

    @covers_requirement(
        "combat-modifier-table::high-exposure-defense-penalty-prices-raised-exposure-as-a-combat-cost",
        "rulebook-schema::the-effect-then-clause-is-opaque-to-the-shared-schema-module",
    )
    def test_rule_high_exposure_defense_penalty(self):
        entity = self._entity()
        entity.sexual.exposure.value = "高"
        self.assertEqual(evaluate_combat_modifiers(entity), {"defense": -15})
        rule = RULES["high_exposure_defense_penalty"]
        entity.sexual.exposure.value = "中等"
        self.assertFalse(evaluate_condition(rule.when, {"exposure": entity.sexual.exposure}))
        entity.sexual.exposure.value = "極高"
        self.assertTrue(evaluate_condition(rule.when, {"exposure": entity.sexual.exposure}))
        self.assertEqual(rule.then, {"defense": -15})

    def test_rule_high_exposure_defense_penalty_below_threshold(self):
        entity = self._entity()
        for level in ("極低", "低"):
            with self.subTest(level=level):
                entity.sexual.exposure.value = level
                self.assertEqual(evaluate_combat_modifiers(entity), {})

    def test_rule_high_exposure_defense_penalty_merges_with_other_origins(self):
        entity = self._entity()
        entity.db.skills = {"active": [], "passive": ["defense_instinct"]}
        _add_buff(entity, "poisoned")
        entity.sexual.exposure.value = "高"
        self.assertEqual(
            evaluate_combat_modifiers(entity),
            {"agility": "-10%", "defense": -10},
        )

    def test_high_exposure_defense_penalty_applies_through_real_damage_resolution(self):
        from world.rules.combat import _adjusted_defense

        entity = self._entity()
        entity.sexual.exposure.value = "高"
        self.assertEqual(
            _adjusted_defense(entity),
            float(entity.skills.effective_value("defense")) - 15,
        )
        entity.sexual.exposure.value = "低"
        self.assertEqual(
            _adjusted_defense(entity),
            float(entity.skills.effective_value("defense")),
        )

    def test_high_exposure_defense_penalty_no_create_parity(self):
        entity = self._entity()
        entity.sexual.exposure.value = "高"
        self.assertEqual(evaluate_combat_modifiers_no_create(entity), {"defense": -15})
        entity.sexual.exposure.value = "低"
        self.assertEqual(evaluate_combat_modifiers_no_create(entity), {})

    def test_rule_defense_instinct_defense_bonus(self):
        entity = self._entity()
        entity.db.skills = {"active": [], "passive": ["defense_instinct"]}
        self.assertEqual(evaluate_combat_modifiers(entity), {"defense": 5})

    def test_rule_blade_art_mastery_accuracy_bonus(self):
        entity = self._entity()
        entity.db.skills = {"active": [], "passive": ["blade_art_mastery"]}
        self.assertEqual(evaluate_combat_modifiers(entity), {"accuracy": 5})

    def test_rule_extreme_endurance_sp_cost_reduction(self):
        entity = self._entity()
        entity.db.skills = {"active": [], "passive": ["extreme_endurance"]}
        self.assertEqual(evaluate_combat_modifiers(entity), {"sp_cost": "-10%"})

    def test_rule_magic_circle_comprehension_accuracy_bonus(self):
        entity = self._entity()
        entity.db.skills = {"active": [], "passive": ["magic_circle_comprehension"]}
        self.assertEqual(evaluate_combat_modifiers(entity), {"accuracy": 5})

    def test_rule_precise_mana_control_mp_cost_reduction(self):
        entity = self._entity()
        entity.db.skills = {"active": [], "passive": ["precise_mana_control"]}
        self.assertEqual(evaluate_combat_modifiers(entity), {"mp_cost": "-10%"})

    def test_rule_retainer_martial_training_atk_phys_bonus(self):
        entity = self._entity()
        entity.db.skills = {"active": [], "passive": ["retainer_martial_training"]}
        self.assertEqual(evaluate_combat_modifiers(entity), {"atk_phys": 5})

    def test_rule_guardian_instinct_defense_bonus(self):
        entity = self._entity()
        entity.db.skills = {"active": [], "passive": ["guardian_instinct"]}
        self.assertEqual(evaluate_combat_modifiers(entity), {"defense": 5})

    def test_rule_reincarnation_boon_yuka_agility_bonus(self):
        entity = self._entity()
        entity.db.skills = {"active": [], "passive": ["reincarnation_boon_yuka"]}
        self.assertEqual(evaluate_combat_modifiers(entity), {"agility": "+5%"})

    def _dual_wielding(self):
        entity = self._entity()
        entity.db.equipment = {"weapon_main": "left_blade", "weapon_off": "right_blade"}
        return entity

    @covers_requirement(
        "combat-modifier-table::dual-wield-style-grants-a-combat-adjustment-while-owned",
        "skill-registry::dual-wield-style-is-a-passive-stance-not-a-castable-active-skill",
    )
    def test_rule_dual_wield_style_atk_phys_bonus(self):
        entity = self._dual_wielding()
        entity.db.skills = {"active": [], "passive": ["dual_wield_style"]}
        self.assertEqual(evaluate_combat_modifiers(entity), {"atk_phys": 5})

    @covers_requirement("combat-modifier-table::dual-wield-style-grants-a-combat-adjustment-while-owned")
    def test_dual_wield_style_bonus_never_grants_without_ownership(self):
        entity = self._dual_wielding()
        entity.db.skills = {"active": [], "passive": ["elf_longevity"]}
        self.assertEqual(evaluate_combat_modifiers(entity), {})

    def test_dual_wield_style_bonus_requires_two_equipped_weapons(self):
        entity = self._entity()
        entity.db.skills = {"active": [], "passive": ["dual_wield_style"]}
        entity.db.equipment = {"weapon_main": "left_blade", "weapon_off": None}
        self.assertEqual(evaluate_combat_modifiers(entity), {})

    def test_dual_wielding_condition_matches_a_context_value(self):
        self.assertTrue(
            evaluate_condition(
                {"dual_wielding": True},
                {"dual_wielding": True},
            )
        )
        self.assertFalse(
            evaluate_condition(
                {"dual_wielding": True},
                {"dual_wielding": False},
            )
        )
        self.assertFalse(evaluate_condition({"dual_wielding": True}, {}))
        with self.assertRaisesRegex(ValueError, "boolean"):
            evaluate_condition({"dual_wielding": "yes"}, {"dual_wielding": True})

    def test_equipment_worn_condition_matches_a_context_value(self):
        self.assertTrue(
            evaluate_condition(
                {"equipment_worn": "sister_vestments"},
                {"worn_item_keys": frozenset({"sister_vestments"})},
            )
        )
        self.assertFalse(
            evaluate_condition(
                {"equipment_worn": "sister_vestments"},
                {"worn_item_keys": frozenset({"saintess_vestments"})},
            )
        )
        # A context lacking the fact must fail the condition closed, and a
        # malformed fact (None or a bare string) must never crash or match
        # by substring accident (P5 D2).
        self.assertFalse(evaluate_condition({"equipment_worn": "x"}, {}))
        self.assertFalse(
            evaluate_condition({"equipment_worn": "x"}, {"worn_item_keys": None})
        )
        self.assertFalse(
            evaluate_condition({"equipment_worn": "x"}, {"worn_item_keys": "x"})
        )
        with self.assertRaisesRegex(ValueError, "string item key"):
            evaluate_condition({"equipment_worn": 123}, {"worn_item_keys": set()})

    def _wearing_grace(self, *, armor=None, accessories=()):
        entity = self._entity()
        entity.db.equipment = {
            "weapon_main": None,
            "weapon_off": None,
            "armor": armor,
            "accessories": list(accessories),
        }
        return entity

    def test_rule_sister_vestment_grace(self):
        # 修女聖袍 (sister_vestments) + arousal >= 中等 (35..59) → defense +4.
        entity = self._wearing_grace(armor="sister_vestments")
        entity.sexual.pleasure.base = 40
        # The robe's own equipment heal_gain +10% merges beside the grace.
        self.assertEqual(
            evaluate_combat_modifiers(entity), {"defense": 4, "heal_gain": "+10%"}
        )
        # Same habit at 平靜 arousal: no grace.
        entity.sexual.pleasure.base = 0
        self.assertEqual(evaluate_combat_modifiers(entity), {"heal_gain": "+10%"})
        # Same arousal without the habit: no grace.
        self.assertEqual(evaluate_combat_modifiers(self._entity()), {})

    def test_rule_saintess_vestment_grace(self):
        # 聖女聖袍 (saintess_vestments) + arousal >= 中等 → defense +6 on top
        # of the robe's own equipment defense -3; the merged bundle is +3.
        entity = self._wearing_grace(armor="saintess_vestments")
        entity.sexual.pleasure.base = 40
        self.assertEqual(
            evaluate_combat_modifiers(entity), {"defense": 3, "heal_gain": "+25%"}
        )
        entity.sexual.pleasure.base = 0
        # Equipment defense -3 still applies without the grace.
        self.assertEqual(
            evaluate_combat_modifiers(entity), {"defense": -3, "heal_gain": "+25%"}
        )

    def test_rule_holy_emblem_grace(self):
        # 光輝聖徽 (radiant_holy_emblem) + arousal >= 高度 (60..84) →
        # heal_gain +10% on top of the emblem's own +20%.
        entity = self._wearing_grace(accessories=("radiant_holy_emblem",))
        entity.sexual.pleasure.base = 60
        bundle = evaluate_combat_modifiers(entity)
        # Arousal 高度 also fires the high-arousal penalty row.
        self.assertEqual(
            bundle, {"heal_gain": "+30%", "agility": "-20%", "accuracy": -15}
        )
        entity.sexual.pleasure.base = 0
        self.assertEqual(evaluate_combat_modifiers(entity), {"heal_gain": "+20%"})

    def test_rule_pilgrim_medallion_grace(self):
        # 朝聖者銅符 (pilgrim_medallion) + arousal >= 微興奮 (15..34) → defense +2.
        entity = self._wearing_grace(accessories=("pilgrim_medallion",))
        entity.sexual.pleasure.base = 15
        self.assertEqual(
            evaluate_combat_modifiers(entity), {"defense": 2, "heal_gain": "+5%"}
        )
        entity.sexual.pleasure.base = 0
        self.assertEqual(evaluate_combat_modifiers(entity), {"heal_gain": "+5%"})

    def test_malformed_equipment_storage_fails_closed(self):
        entity = self._entity()
        entity.db.skills = {"active": [], "passive": ["dual_wield_style"]}
        for malformed in ("corrupt", None, ["left_blade", "right_blade"]):
            with self.subTest(malformed=malformed):
                entity.db.equipment = malformed
                self.assertEqual(evaluate_combat_modifiers(entity), {})

    def test_no_create_evaluation_matches_dual_wield_row_without_handler(self):
        entity = self._dual_wielding()
        entity.db.skills = {"active": [], "passive": ["dual_wield_style"]}
        from world.rules.combat_modifiers import evaluate_combat_modifiers_no_create

        self.assertNotIn("equipment", vars(entity))
        self.assertEqual(evaluate_combat_modifiers_no_create(entity), {"atk_phys": 5})
        self.assertNotIn("equipment", vars(entity))

    @covers_requirement("combat-modifier-table::skill-owned-is-a-first-class-condition-alongside-buff-active-and-field-thresholds")
    def test_skill_owned_rows_do_not_match_without_ownership(self):
        entity = self._entity()
        self.assertEqual(evaluate_combat_modifiers(entity), {})
        entity.db.skills = {"active": [], "passive": ["elf_longevity"]}
        self.assertEqual(evaluate_combat_modifiers(entity), {})

    @covers_requirement("combat-modifier-table::skill-owned-is-a-first-class-condition-alongside-buff-active-and-field-thresholds")
    def test_skill_owned_condition_evaluates_against_owned_keys(self):
        entity = self._entity()
        entity.db.skills = {"active": [], "passive": ["defense_instinct"]}
        self.assertTrue(
            evaluate_condition(
                {"skill_owned": "defense_instinct"},
                {"entity": entity},
            )
        )
        self.assertFalse(
            evaluate_condition(
                {"skill_owned": "defense_instinct", "buff_active": "focus"},
                {"entity": entity, "active_buffs": {"fear"}},
            )
        )
        self.assertFalse(evaluate_condition({"skill_owned": "defense_instinct"}, {}))

    @covers_requirement("combat-modifier-table::skill-owned-is-a-first-class-condition-alongside-buff-active-and-field-thresholds")
    def test_skill_owned_condition_matches_a_conferred_grant(self):
        entity = self._entity()
        entity.db.skill_grants = [
            ConferredSkillGrant("elosia", "defense_instinct", 0.5)
        ]
        self.assertTrue(
            evaluate_condition(
                {"skill_owned": "defense_instinct"},
                {"entity": entity},
            )
        )

    @covers_requirement("combat-modifier-table::skill-owned-is-a-first-class-condition-alongside-buff-active-and-field-thresholds")
    def test_conferred_grant_scales_the_skill_owned_adjustment(self):
        entity = self._entity()
        entity.db.skill_grants = [
            ConferredSkillGrant("elosia", "defense_instinct", 0.5)
        ]
        self.assertEqual(evaluate_combat_modifiers(entity), {"defense": 2.5})

    @covers_requirement("combat-modifier-table::skill-owned-is-a-first-class-condition-alongside-buff-active-and-field-thresholds")
    def test_conferred_grants_of_one_skill_sum_their_scaled_adjustments(self):
        entity = self._entity()
        entity.db.skill_grants = [
            ConferredSkillGrant("elosia", "defense_instinct", 0.5),
            ConferredSkillGrant("other", "defense_instinct", 0.25),
        ]
        self.assertEqual(evaluate_combat_modifiers(entity), {"defense": 3.75})

    @covers_requirement("combat-modifier-table::skill-owned-is-a-first-class-condition-alongside-buff-active-and-field-thresholds")
    def test_owned_skill_takes_the_full_adjustment_despite_a_grant(self):
        entity = self._entity()
        entity.db.skills = {"active": [], "passive": ["defense_instinct"]}
        entity.db.skill_grants = [
            ConferredSkillGrant("elosia", "defense_instinct", 0.5)
        ]
        self.assertEqual(evaluate_combat_modifiers(entity), {"defense": 5})

    @covers_requirement("combat-modifier-table::skill-owned-is-a-first-class-condition-alongside-buff-active-and-field-thresholds")
    def test_gate_type_grant_never_reaches_the_rule_table(self):
        entity = self._entity()
        entity.db.skill_grants = [
            ConferredSkillGrant("elosia", "fire_mastery", 0.5)
        ]
        self.assertEqual(evaluate_combat_modifiers(entity), {})
        self.assertEqual(evaluate_combat_modifiers_no_create(entity), {})

    @covers_requirement("combat-modifier-table::skill-owned-is-a-first-class-condition-alongside-buff-active-and-field-thresholds")
    def test_zero_scale_grant_never_applies_the_full_adjustment(self):
        entity = self._entity()
        entity.db.skill_grants = [
            ConferredSkillGrant("elosia", "defense_instinct", 0.0)
        ]
        self.assertEqual(evaluate_combat_modifiers(entity), {})

    @covers_requirement("combat-modifier-table::skill-owned-is-a-first-class-condition-alongside-buff-active-and-field-thresholds")
    def test_scaled_percentage_merges_with_other_percentage_adjustments(self):
        entity = self._entity()
        entity.db.skill_grants = [
            ConferredSkillGrant("elosia", "reincarnation_boon_yuka", 0.5)
        ]
        _add_buff(entity, "poisoned")
        self.assertEqual(
            evaluate_combat_modifiers(entity),
            {"agility": "-7.5%"},
        )

    @covers_requirement("combat-modifier-table::skill-owned-is-a-first-class-condition-alongside-buff-active-and-field-thresholds")
    def test_skill_owned_rows_merge_with_buff_and_sexual_origin_rows(self):
        entity = self._entity()
        entity.db.skills = {"active": [], "passive": ["defense_instinct"]}
        _add_buff(entity, "poisoned")
        entity.sexual.pleasure.base = 60
        self.assertEqual(
            evaluate_combat_modifiers(entity),
            {"agility": "-30%", "accuracy": -15, "defense": 5},
        )

    @covers_requirement("combat-modifier-table::the-eight-previously-dead-passive-buff-combat-prediction-skills-each-grant-a-real-adjustment")
    def test_explicit_custom_context_still_matches_skill_owned_rows(self):
        entity = self._entity()
        entity.db.skills = {"active": [], "passive": ["defense_instinct"]}
        from world.rules.combat_modifiers import matched_combat_modifiers

        matches = dict(matched_combat_modifiers(entity, context={"active_buffs": set()}))
        self.assertIn("defense_instinct_defense_bonus", matches)

    @covers_requirement("combat-modifier-table::the-eight-previously-dead-passive-buff-combat-prediction-skills-each-grant-a-real-adjustment")
    def test_no_create_evaluation_matches_skill_owned_rows(self):
        entity = self._entity()
        entity.db.skills = {"active": [], "passive": ["defense_instinct"]}
        self.assertEqual(evaluate_combat_modifiers_no_create(entity), {"defense": 5})
        self.assertIsNone(entity.attributes.get("sexual_traits", category="traits"))

    @covers_requirement("combat-modifier-table::evaluate-combat-modifiers-is-a-pure-query-that-never-writes-to-entity-state")
    def test_multiple_rules_merge_and_query_is_pure(self):
        entity = self._entity()
        _add_buff(entity, "poisoned")
        _add_buff(entity, "fear")
        before = {key: getattr(entity.traits, key).value for key in entity.traits.all()}
        active = set(entity.buffs.all)
        self.assertEqual(
            evaluate_combat_modifiers(entity),
            {"agility": "-25%", "accuracy": -10},
        )
        self.assertEqual(active, set(entity.buffs.all))
        self.assertEqual(
            before, {key: getattr(entity.traits, key).value for key in entity.traits.all()}
        )

    @covers_requirement("buff-handler-integration::entity-buffs-is-mounted-as-the-real-buffhandler-replacing-the-change-3-placeholder")
    def test_no_state_returns_empty_and_sexual_rules_are_inert(self):
        self.assertEqual(evaluate_combat_modifiers(self._entity()), {})

    @covers_requirement("combat-modifier-table::the-no-create-preview-path-resolves-the-derived-arousal-level-from-stored-pleasure-not-a-raw-arousal-key")
    def test_no_create_preview_reflects_live_pleasure_on_materialized_entity(self):
        entity = self._entity()
        entity.sexual.pleasure.base = 61
        live = evaluate_combat_modifiers(entity)
        preview = evaluate_combat_modifiers_no_create(entity)
        self.assertEqual(live, {"agility": "-20%", "accuracy": -15})
        self.assertEqual(preview, live)

    @covers_requirement("combat-modifier-table::the-no-create-preview-path-resolves-the-derived-arousal-level-from-stored-pleasure-not-a-raw-arousal-key")
    def test_no_create_preview_falls_back_to_baseline_without_materializing(self):
        entity = self._entity()
        entity.db.sexual = {
            "arousal": "極限",
            "wetness": "乾燥",
            "shame": "無",
            "exposure": "極低",
            "climax_phase": "未達",
            "sensitivity": {},
            "climax_today": 0,
            "virgin": True,
            "experience_types": [],
        }
        self.assertIsNone(entity.attributes.get("sexual_traits", category="traits"))
        self.assertEqual(
            evaluate_combat_modifiers_no_create(entity),
            {"agility": "-20%", "accuracy": -15},
        )
        self.assertIsNone(
            entity.attributes.get("sexual_traits", category="traits"),
            "no-create preview must not materialize the sexual handler",
        )

    @covers_requirement("combat-modifier-table::the-no-create-preview-path-resolves-the-derived-arousal-level-from-stored-pleasure-not-a-raw-arousal-key")
    def test_no_create_preview_tracks_a_ceilinged_stored_base(self):
        # CounterTrait.base's setter clamps writes into [0, 100]; the
        # no-create reader must resolve the stored base exactly as the live
        # trait.value read does, including at the ceiling.
        entity = self._entity()
        entity.sexual.pleasure.base = 95
        entity.sexual.pleasure.base += 14
        self.assertEqual(entity.sexual.pleasure.value, 100)
        self.assertEqual(
            evaluate_combat_modifiers_no_create(entity),
            evaluate_combat_modifiers(entity),
        )

    @covers_requirement("combat-modifier-table::the-no-create-preview-path-resolves-the-derived-arousal-level-from-stored-pleasure-not-a-raw-arousal-key")
    def test_no_create_preview_rejects_a_boolean_stored_base(self):
        entity = self._entity()
        entity.sexual.pleasure.base = 60
        raw = dict(entity.attributes.get("sexual_traits", category="traits"))
        raw["pleasure"] = dict(raw["pleasure"])
        raw["pleasure"]["base"] = True
        entity.attributes.add("sexual_traits", raw, category="traits")
        self.assertEqual(evaluate_combat_modifiers_no_create(entity), {})


class ApplyCostModifierTests(unittest.TestCase):
    """Unit tests for the shared cost-adjustment helper (floor, zero clamp)."""

    def test_no_modifier_returns_amount_unchanged(self):
        self.assertEqual(apply_cost_modifier(10, None), 10)
        self.assertEqual(apply_cost_modifier(0, None), 0)

    def test_integer_percentages_round_down_on_reduction(self):
        self.assertEqual(apply_cost_modifier(10, "-10%"), 9)
        self.assertEqual(apply_cost_modifier(10, "+10%"), 11)
        self.assertEqual(apply_cost_modifier(10, "-100%"), 0)
        self.assertEqual(apply_cost_modifier(10, "+100%"), 20)
        self.assertEqual(apply_cost_modifier(0, "-10%"), 0)

    def test_fractional_percentage_floors_deterministically(self):
        self.assertEqual(apply_cost_modifier(10, "-5%"), 9)
        self.assertEqual(apply_cost_modifier(10, "-2.5%"), 9)
        self.assertEqual(apply_cost_modifier(10, "+2.5%"), 10)

    def test_zero_clamp_never_goes_negative(self):
        self.assertEqual(apply_cost_modifier(10, "-100%"), 0)
        self.assertEqual(apply_cost_modifier(10, "-150%"), 0)
        self.assertEqual(apply_cost_modifier(10, "-1500%"), 0)
        self.assertEqual(apply_cost_modifier(4, "-10%"), 3)

    def test_malformed_percentage_raises(self):
        for malformed in ("10%", "5", "-10", "%", "abc", "-1.2.3%", "  -10%"):
            with self.subTest(malformed=malformed):
                with self.assertRaises(ValueError):
                    apply_cost_modifier(10, malformed)

    def test_non_string_values_raise_value_error_not_type_error(self):
        for malformed in (5, 2.5, -10, {}, []):
            with self.subTest(malformed=malformed):
                with self.assertRaises(ValueError):
                    apply_cost_modifier(10, malformed)

    def test_floor_not_truncation_on_fractional_product(self):
        self.assertEqual(apply_cost_modifier(10, "-5%"), 9)
        self.assertEqual(apply_cost_modifier(9, "-10%"), 8)
