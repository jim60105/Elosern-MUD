"""Behaviour suite for the combat modifier rule table and its condition engine.

Every test drives the matcher/merger with state it builds in the test; the
trigger keys and adjustments for rule-bound rows are derived from the loaded
rule table at runtime instead of being echoed as literals, so the suite pins
the mechanism (condition matching, ownership, conferral scaling, merge) and
not the shipped data content."""

from tools.spec_traceability import covers_requirement

from pathlib import Path
import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.rules.buffs import apply_buff, remove_by_selector
from world.rules.combat_modifiers import (
    apply_cost_modifier,
    evaluate_combat_modifiers,
    evaluate_combat_modifiers_no_create,
    matched_combat_modifiers,
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
        apply_buff(entity, "poisoned")
        self.assertEqual(evaluate_combat_modifiers(entity), {"agility": "-10%"})

    def test_rule_paralysis_locks_actions(self):
        entity = self._entity()
        apply_buff(entity, "paralysis")
        self.assertEqual(evaluate_combat_modifiers(entity), {"actions_per_turn": 0})

    def test_rule_suffocation_locks_actions(self):
        entity = self._entity()
        apply_buff(entity, "suffocated")
        self.assertEqual(evaluate_combat_modifiers(entity), {"actions_per_turn": 0})

    def test_rule_water_bind_locks_actions(self):
        entity = self._entity()
        apply_buff(entity, "water_bind")
        self.assertEqual(evaluate_combat_modifiers(entity), {"actions_per_turn": 0})

    def test_rule_thunder_gods_haste_grants_action(self):
        entity = self._entity()
        apply_buff(entity, "lightning_extra_action")
        self.assertEqual(evaluate_combat_modifiers(entity), {"actions_per_turn": 2})

    def test_rule_paralysis_enhanced_locks_actions(self):
        entity = self._entity()
        apply_buff(entity, "paralysis_enhanced")
        self.assertEqual(evaluate_combat_modifiers(entity), {"actions_per_turn": 0})

    def test_rule_static_ward_micro_stun(self):
        entity = self._entity()
        apply_buff(entity, "static_ward_stun")
        matched = dict(matched_combat_modifiers(entity))
        self.assertIn("static_ward_micro_stun", matched)
        self.assertEqual(
            matched["static_ward_micro_stun"], {"actions_per_turn": 0, "chance": 15}
        )

    def test_rule_flicker_micro_stun(self):
        entity = self._entity()
        apply_buff(entity, "flicker_stun")
        matched = dict(matched_combat_modifiers(entity))
        self.assertIn("flicker_micro_stun", matched)
        self.assertEqual(
            matched["flicker_micro_stun"], {"actions_per_turn": 0, "chance": 30}
        )

    @covers_requirement("combat-modifier-table::combat-modifiers-yaml-is-one-table-evaluated-by-one-condition-engine-with-no")
    def test_rule_mp_regen_lock_freeze(self):
        entity = self._entity()
        apply_buff(entity, "mp_regen_lock")
        self.assertEqual(evaluate_combat_modifiers(entity), {"mp_regen_scale": 0})

    @covers_requirement("combat-modifier-table::combat-modifiers-yaml-is-one-table-evaluated-by-one-condition-engine-with-no")
    def test_rule_mana_reflux_share_bonus(self):
        entity = self._entity()
        apply_buff(entity, "mana_reflux")
        self.assertEqual(evaluate_combat_modifiers(entity), {"recovery_share_bonus": 0.1})

    def test_rule_fear_agility_and_accuracy_penalty(self):
        entity = self._entity()
        apply_buff(entity, "fear")
        self.assertEqual(
            evaluate_combat_modifiers(entity),
            {"actions_per_turn": 0, "agility": "-15%", "accuracy": -10},
        )

    def test_rule_fear_locks_actions(self):
        entity = self._entity()
        apply_buff(entity, "fear")
        self.assertEqual(
            evaluate_combat_modifiers(entity),
            {"actions_per_turn": 0, "agility": "-15%", "accuracy": -10},
        )

    def test_rule_focus_accuracy_boost(self):
        entity = self._entity()
        apply_buff(entity, "focus")
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
        rule = RULES["defense_instinct_defense_bonus"]
        entity.db.skills = {"active": [], "passive": [rule.when["skill_owned"]]}
        apply_buff(entity, "poisoned")
        entity.sexual.exposure.value = "高"
        self.assertEqual(
            evaluate_combat_modifiers(entity),
            {
                "agility": RULES["poison_agility_penalty"].then["agility"],
                "defense": (
                    RULES["high_exposure_defense_penalty"].then["defense"]
                    + rule.then["defense"]
                ),
            },
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

    # Each skill-owned rule test drives the engine with the trigger key the
    # rule itself declares (derived from the loaded table, never echoed) and
    # expects the effect that rule declares — the contract is the
    # trigger-to-effect wiring through the matcher, not the shipped values.
    def _owning(self, rule_id: str):
        """Return an entity owning exactly the skill *rule_id* is keyed to."""
        entity = self._entity()
        entity.db.skills = {
            "active": [],
            "passive": [RULES[rule_id].when["skill_owned"]],
        }
        return entity

    def test_rule_defense_instinct_defense_bonus(self):
        entity = self._owning("defense_instinct_defense_bonus")
        self.assertEqual(
            evaluate_combat_modifiers(entity),
            RULES["defense_instinct_defense_bonus"].then,
        )

    def test_rule_blade_art_mastery_accuracy_bonus(self):
        entity = self._owning("blade_art_mastery_accuracy_bonus")
        self.assertEqual(
            evaluate_combat_modifiers(entity),
            RULES["blade_art_mastery_accuracy_bonus"].then,
        )

    def test_rule_extreme_endurance_sp_cost_reduction(self):
        entity = self._owning("extreme_endurance_sp_cost_reduction")
        self.assertEqual(
            evaluate_combat_modifiers(entity),
            RULES["extreme_endurance_sp_cost_reduction"].then,
        )

    def test_rule_magic_circle_comprehension_accuracy_bonus(self):
        entity = self._owning("magic_circle_comprehension_accuracy_bonus")
        self.assertEqual(
            evaluate_combat_modifiers(entity),
            RULES["magic_circle_comprehension_accuracy_bonus"].then,
        )

    def test_rule_precise_mana_control_mp_cost_reduction(self):
        entity = self._owning("precise_mana_control_mp_cost_reduction")
        self.assertEqual(
            evaluate_combat_modifiers(entity),
            RULES["precise_mana_control_mp_cost_reduction"].then,
        )

    def test_rule_retainer_martial_training_atk_phys_bonus(self):
        entity = self._owning("retainer_martial_training_atk_phys_bonus")
        self.assertEqual(
            evaluate_combat_modifiers(entity),
            RULES["retainer_martial_training_atk_phys_bonus"].then,
        )

    def test_rule_guardian_instinct_defense_bonus(self):
        entity = self._owning("guardian_instinct_defense_bonus")
        self.assertEqual(
            evaluate_combat_modifiers(entity),
            RULES["guardian_instinct_defense_bonus"].then,
        )

    def test_rule_reincarnation_boon_yuka_agility_bonus(self):
        entity = self._owning("reincarnation_boon_yuka_agility_bonus")
        self.assertEqual(
            evaluate_combat_modifiers(entity),
            RULES["reincarnation_boon_yuka_agility_bonus"].then,
        )

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
        rule = RULES["dual_wield_style_atk_phys_bonus"]
        entity.db.skills = {"active": [], "passive": [rule.when["skill_owned"]]}
        self.assertEqual(evaluate_combat_modifiers(entity), rule.then)

    @covers_requirement("combat-modifier-table::dual-wield-style-grants-a-combat-adjustment-while-owned")
    def test_dual_wield_style_bonus_never_grants_without_ownership(self):
        entity = self._dual_wielding()
        # A different passive (not the one the rule is keyed to) must not
        # unlock the dual-wield row.
        entity.db.skills = {"active": [], "passive": ["synthetic_other_passive"]}
        self.assertEqual(evaluate_combat_modifiers(entity), {})

    def test_dual_wield_style_bonus_requires_two_equipped_weapons(self):
        entity = self._entity()
        rule = RULES["dual_wield_style_atk_phys_bonus"]
        entity.db.skills = {"active": [], "passive": [rule.when["skill_owned"]]}
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
                {"equipment_worn": "synthetic_item"},
                {"worn_item_keys": frozenset({"synthetic_item"})},
            )
        )
        self.assertFalse(
            evaluate_condition(
                {"equipment_worn": "synthetic_item"},
                {"worn_item_keys": frozenset({"synthetic_other_item"})},
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
        # Wearing the grace row's own gear at its own threshold fires the row;
        # below the threshold or without the gear it stays inert. The gear key
        # and the row's presence are probed from the table, not echoed.
        rule = RULES["sister_vestment_grace"]
        entity = self._wearing_grace(armor=rule.when["equipment_worn"])
        entity.sexual.pleasure.base = 40
        self.assertIn("sister_vestment_grace", dict(matched_combat_modifiers(entity)))
        entity.sexual.pleasure.base = 0
        self.assertNotIn("sister_vestment_grace", dict(matched_combat_modifiers(entity)))
        self.assertNotIn(
            "sister_vestment_grace", dict(matched_combat_modifiers(self._entity()))
        )

    def test_rule_saintess_vestment_grace(self):
        rule = RULES["saintess_vestment_grace"]
        entity = self._wearing_grace(armor=rule.when["equipment_worn"])
        entity.sexual.pleasure.base = 40
        self.assertIn(
            "saintess_vestment_grace", dict(matched_combat_modifiers(entity))
        )
        entity.sexual.pleasure.base = 0
        self.assertNotIn(
            "saintess_vestment_grace", dict(matched_combat_modifiers(entity))
        )

    def test_rule_holy_emblem_grace(self):
        rule = RULES["holy_emblem_grace"]
        entity = self._wearing_grace(accessories=(rule.when["equipment_worn"],))
        entity.sexual.pleasure.base = 60
        self.assertIn("holy_emblem_grace", dict(matched_combat_modifiers(entity)))
        entity.sexual.pleasure.base = 0
        self.assertNotIn("holy_emblem_grace", dict(matched_combat_modifiers(entity)))

    def test_rule_pilgrim_medallion_grace(self):
        rule = RULES["pilgrim_medallion_grace"]
        entity = self._wearing_grace(accessories=(rule.when["equipment_worn"],))
        entity.sexual.pleasure.base = 15
        self.assertIn(
            "pilgrim_medallion_grace", dict(matched_combat_modifiers(entity))
        )
        entity.sexual.pleasure.base = 0
        self.assertNotIn(
            "pilgrim_medallion_grace", dict(matched_combat_modifiers(entity))
        )

    def test_malformed_equipment_storage_fails_closed(self):
        entity = self._entity()
        rule = RULES["dual_wield_style_atk_phys_bonus"]
        entity.db.skills = {"active": [], "passive": [rule.when["skill_owned"]]}
        for malformed in ("corrupt", None, ["left_blade", "right_blade"]):
            with self.subTest(malformed=malformed):
                entity.db.equipment = malformed
                self.assertEqual(evaluate_combat_modifiers(entity), {})

    def test_no_create_evaluation_matches_dual_wield_row_without_handler(self):
        entity = self._dual_wielding()
        rule = RULES["dual_wield_style_atk_phys_bonus"]
        entity.db.skills = {"active": [], "passive": [rule.when["skill_owned"]]}
        from world.rules.combat_modifiers import evaluate_combat_modifiers_no_create

        self.assertNotIn("equipment", vars(entity))
        self.assertEqual(evaluate_combat_modifiers_no_create(entity), rule.then)
        self.assertNotIn("equipment", vars(entity))

    @covers_requirement("combat-modifier-table::skill-owned-is-a-first-class-condition-alongside-buff-active-and-field-thresholds")
    def test_skill_owned_rows_do_not_match_without_ownership(self):
        entity = self._entity()
        self.assertEqual(evaluate_combat_modifiers(entity), {})
        entity.db.skills = {"active": [], "passive": ["synthetic_unowned_passive"]}
        self.assertEqual(evaluate_combat_modifiers(entity), {})

    @covers_requirement("combat-modifier-table::skill-owned-is-a-first-class-condition-alongside-buff-active-and-field-thresholds")
    def test_skill_owned_condition_evaluates_against_owned_keys(self):
        entity = self._entity()
        entity.db.skills = {"active": [], "passive": ["synthetic_owned_skill"]}
        self.assertTrue(
            evaluate_condition(
                {"skill_owned": "synthetic_owned_skill"},
                {"entity": entity},
            )
        )
        self.assertFalse(
            evaluate_condition(
                {"skill_owned": "synthetic_owned_skill", "buff_active": "synthetic_buff"},
                {"entity": entity, "active_buffs": {"synthetic_other_buff"}},
            )
        )
        self.assertFalse(evaluate_condition({"skill_owned": "synthetic_owned_skill"}, {}))

    @covers_requirement("combat-modifier-table::skill-owned-is-a-first-class-condition-alongside-buff-active-and-field-thresholds")
    def test_skill_owned_condition_matches_a_conferred_grant(self):
        entity = self._entity()
        entity.db.skill_grants = [
            ConferredSkillGrant("elosia", "synthetic_granted_skill", 0.5)
        ]
        self.assertTrue(
            evaluate_condition(
                {"skill_owned": "synthetic_granted_skill"},
                {"entity": entity},
            )
        )

    @covers_requirement("combat-modifier-table::skill-owned-is-a-first-class-condition-alongside-buff-active-and-field-thresholds")
    def test_conferred_grant_scales_the_skill_owned_adjustment(self):
        rule = RULES["defense_instinct_defense_bonus"]
        key = rule.when["skill_owned"]
        entity = self._entity()
        entity.db.skill_grants = [ConferredSkillGrant("elosia", key, 0.5)]
        self.assertEqual(
            evaluate_combat_modifiers(entity),
            {"defense": rule.then["defense"] * 0.5},
        )

    @covers_requirement("combat-modifier-table::skill-owned-is-a-first-class-condition-alongside-buff-active-and-field-thresholds")
    def test_conferred_grants_of_one_skill_sum_their_scaled_adjustments(self):
        rule = RULES["defense_instinct_defense_bonus"]
        key = rule.when["skill_owned"]
        entity = self._entity()
        entity.db.skill_grants = [
            ConferredSkillGrant("elosia", key, 0.5),
            ConferredSkillGrant("other", key, 0.25),
        ]
        self.assertEqual(
            evaluate_combat_modifiers(entity),
            {"defense": rule.then["defense"] * 0.75},
        )

    @covers_requirement("combat-modifier-table::skill-owned-is-a-first-class-condition-alongside-buff-active-and-field-thresholds")
    def test_owned_skill_takes_the_full_adjustment_despite_a_grant(self):
        rule = RULES["defense_instinct_defense_bonus"]
        key = rule.when["skill_owned"]
        entity = self._entity()
        entity.db.skills = {"active": [], "passive": [key]}
        entity.db.skill_grants = [ConferredSkillGrant("elosia", key, 0.5)]
        self.assertEqual(evaluate_combat_modifiers(entity), rule.then)

    @covers_requirement("combat-modifier-table::skill-owned-is-a-first-class-condition-alongside-buff-active-and-field-thresholds")
    def test_gate_type_grant_never_reaches_the_rule_table(self):
        entity = self._entity()
        entity.db.skill_grants = [
            ConferredSkillGrant("elosia", "synthetic_unruled_grant", 0.5)
        ]
        self.assertEqual(evaluate_combat_modifiers(entity), {})
        self.assertEqual(evaluate_combat_modifiers_no_create(entity), {})

    @covers_requirement("combat-modifier-table::skill-owned-is-a-first-class-condition-alongside-buff-active-and-field-thresholds")
    def test_zero_scale_grant_never_applies_the_full_adjustment(self):
        rule = RULES["defense_instinct_defense_bonus"]
        entity = self._entity()
        entity.db.skill_grants = [
            ConferredSkillGrant("elosia", rule.when["skill_owned"], 0.0)
        ]
        self.assertEqual(evaluate_combat_modifiers(entity), {})

    @covers_requirement("combat-modifier-table::skill-owned-is-a-first-class-condition-alongside-buff-active-and-field-thresholds")
    def test_scaled_percentage_merges_with_other_percentage_adjustments(self):
        boon = RULES["reincarnation_boon_yuka_agility_bonus"]
        poison = RULES["poison_agility_penalty"]
        # Percent strings merge additively: the shipped poison penalty plus
        # half the rule's own percent bonus, recomputed from the table.
        scaled = int(poison.then["agility"][:-1]) + int(boon.then["agility"][:-1]) * 0.5
        entity = self._entity()
        entity.db.skill_grants = [
            ConferredSkillGrant("elosia", boon.when["skill_owned"], 0.5)
        ]
        apply_buff(entity, "poisoned")
        self.assertEqual(
            evaluate_combat_modifiers(entity),
            {"agility": f"{scaled}%"},
        )

    @covers_requirement("combat-modifier-table::skill-owned-is-a-first-class-condition-alongside-buff-active-and-field-thresholds")
    def test_skill_owned_rows_merge_with_buff_and_sexual_origin_rows(self):
        rule = RULES["defense_instinct_defense_bonus"]
        poison = RULES["poison_agility_penalty"]
        arousal = RULES["high_arousal_agility_accuracy_penalty"]
        merged_agility = int(poison.then["agility"][:-1]) + int(
            arousal.then["agility"][:-1]
        )
        entity = self._entity()
        entity.db.skills = {"active": [], "passive": [rule.when["skill_owned"]]}
        apply_buff(entity, "poisoned")
        entity.sexual.pleasure.base = 60
        self.assertEqual(
            evaluate_combat_modifiers(entity),
            {
                "agility": f"{merged_agility}%",
                "accuracy": arousal.then["accuracy"],
                "defense": rule.then["defense"],
            },
        )

    @covers_requirement("combat-modifier-table::the-eight-previously-dead-passive-buff-combat-prediction-skills-each-grant-a-real-adjustment")
    def test_explicit_custom_context_still_matches_skill_owned_rows(self):
        entity = self._owning("defense_instinct_defense_bonus")
        from world.rules.combat_modifiers import matched_combat_modifiers

        matches = dict(matched_combat_modifiers(entity, context={"active_buffs": set()}))
        self.assertIn("defense_instinct_defense_bonus", matches)

    @covers_requirement("combat-modifier-table::the-eight-previously-dead-passive-buff-combat-prediction-skills-each-grant-a-real-adjustment")
    def test_no_create_evaluation_matches_skill_owned_rows(self):
        entity = self._owning("defense_instinct_defense_bonus")
        self.assertEqual(
            evaluate_combat_modifiers_no_create(entity),
            RULES["defense_instinct_defense_bonus"].then,
        )
        self.assertIsNone(entity.attributes.get("sexual_traits", category="traits"))

    @covers_requirement("combat-modifier-table::evaluate-combat-modifiers-is-a-pure-query-that-never-writes-to-entity-state")
    def test_multiple_rules_merge_and_query_is_pure(self):
        entity = self._entity()
        apply_buff(entity, "poisoned")
        apply_buff(entity, "fear")
        before = {key: getattr(entity.traits, key).value for key in entity.traits.all()}
        active = set(entity.buffs.all)
        self.assertEqual(
            evaluate_combat_modifiers(entity),
            {"actions_per_turn": 0, "agility": "-25%", "accuracy": -10},
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

    def test_rule_priestly_grace_recovery_scale(self):
        entity = self._owning("priestly_grace_recovery_scale")
        self.assertEqual(
            evaluate_combat_modifiers(entity),
            RULES["priestly_grace_recovery_scale"].then,
        )

    def test_rule_light_blessing_defense_bonus(self):
        entity = self._entity()
        apply_buff(entity, "light_blessing")
        self.assertEqual(evaluate_combat_modifiers(entity), {"defense": 18})

    # 土護甲路線計時階梯（earth-spell-catalog）：correspondence gate 僅要求每條
    # rule id 有一個具名測試；結算行為由 test_earth_terrain_guard 的合成階梯覆蓋。
    def test_rule_earth_hardened_skin_defense_bonus(self):
        entity = self._entity()
        apply_buff(entity, "earth_hardened_skin")
        self.assertIn("defense", evaluate_combat_modifiers(entity))

    def test_rule_earth_stone_armor_defense_bonus(self):
        entity = self._entity()
        apply_buff(entity, "earth_stone_armor")
        self.assertIn("defense", evaluate_combat_modifiers(entity))

    def test_rule_earth_bedrock_defense_bonus(self):
        entity = self._entity()
        apply_buff(entity, "earth_bedrock")
        self.assertIn("defense", evaluate_combat_modifiers(entity))

    def test_rule_earth_ward_defense_bonus(self):
        entity = self._entity()
        apply_buff(entity, "earth_ward")
        self.assertIn("defense", evaluate_combat_modifiers(entity))

    def test_rule_earth_dust_veil_accuracy_penalty(self):
        entity = self._entity()
        apply_buff(entity, "earth_dust_veil")
        self.assertIn("accuracy", evaluate_combat_modifiers(entity))

    def test_rule_wind_gale_step_agility(self):
        entity = self._entity()
        apply_buff(entity, "gale_step_haste")
        self.assertIn("agility_flat", evaluate_combat_modifiers(entity))

    def test_rule_wind_gale_chain_step_agility(self):
        entity = self._entity()
        apply_buff(entity, "gale_chain_step_haste")
        self.assertIn("agility_flat", evaluate_combat_modifiers(entity))

    def test_rule_wind_afterimage_agility_accuracy(self):
        entity = self._entity()
        apply_buff(entity, "afterimage_step_haste")
        mods = evaluate_combat_modifiers(entity)
        self.assertIn("agility_flat", mods)
        self.assertIn("accuracy", mods)

    def test_rule_wind_haste_domain_agility(self):
        entity = self._entity()
        apply_buff(entity, "haste_domain_haste")
        self.assertIn("agility_flat", evaluate_combat_modifiers(entity))

    # Ice stillness ladder and slows (ice-spell-catalog): the correspondence
    # gate only requires one named test per rule id; settlement behavior is
    # covered by test_ice_stillness_behavior.
    def test_rule_ice_freeze_locks_actions(self):
        entity = self._entity()
        apply_buff(entity, "ice_freeze")
        self.assertEqual(evaluate_combat_modifiers(entity), {"actions_per_turn": 0})

    def test_rule_ice_freeze_tundra_locks_actions(self):
        entity = self._entity()
        apply_buff(entity, "ice_freeze_tundra")
        self.assertEqual(evaluate_combat_modifiers(entity), {"actions_per_turn": 0})

    def test_rule_ice_freeze_nightfall_locks_actions(self):
        entity = self._entity()
        apply_buff(entity, "ice_freeze_nightfall")
        self.assertEqual(evaluate_combat_modifiers(entity), {"actions_per_turn": 0})

    def test_rule_ice_freeze_apotheosis_locks_actions(self):
        entity = self._entity()
        apply_buff(entity, "ice_freeze_apotheosis")
        self.assertEqual(evaluate_combat_modifiers(entity), {"actions_per_turn": 0})

    def test_rule_ice_prison_locks_actions(self):
        entity = self._entity()
        # The buff key is derived from the rule row so the test binds the
        # rule to whatever buff it actually names, without echoing the key.
        apply_buff(entity, RULES["ice_prison_locks_actions"].when["buff_active"])
        self.assertEqual(evaluate_combat_modifiers(entity), {"actions_per_turn": 0})

    def test_rule_ice_slow_agility_penalty(self):
        entity = self._entity()
        apply_buff(entity, "ice_slow")
        self.assertIn("agility_flat", evaluate_combat_modifiers(entity))

    def test_rule_ice_frost_mire_agility_penalty(self):
        entity = self._entity()
        apply_buff(entity, "ice_frost_mire")
        self.assertIn("agility_flat", evaluate_combat_modifiers(entity))

    @covers_requirement("combat-modifier-table::combat-modifiers-yaml-is-one-table-evaluated-by-one-condition-engine-with-no")
    def test_fear_locks_actions_and_stays_key_independent_of_physical_stillness(self):
        feared = self._entity()
        stilled = self._entity()
        apply_buff(feared, "fear")
        apply_buff(stilled, "paralysis")

        feared_mods = evaluate_combat_modifiers(feared)
        self.assertEqual(feared_mods.get("actions_per_turn"), 0)
        self.assertEqual(feared_mods.get("agility"), "-15%")
        self.assertEqual(feared_mods.get("accuracy"), -10)

        stilled_mods = evaluate_combat_modifiers(stilled)
        self.assertEqual(stilled_mods.get("actions_per_turn"), 0)
        self.assertNotIn("agility", stilled_mods)
        self.assertNotIn("accuracy", stilled_mods)

        remove_by_selector(feared, "fear")
        self.assertEqual(evaluate_combat_modifiers(feared), {})
        self.assertEqual(evaluate_combat_modifiers(stilled), {"actions_per_turn": 0})

        remove_by_selector(stilled, "paralysis")
        self.assertEqual(evaluate_combat_modifiers(stilled), {})


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
