"""Tests named one-to-one with combat modifier rule IDs."""

from tools.spec_traceability import covers_requirement

from pathlib import Path

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.buffs import _add_buff
from world.rules.combat_modifiers import evaluate_combat_modifiers
from world.rules.rulebook.schema import evaluate_condition, load_rules

RULES = {
    rule.id: rule
    for rule in load_rules(
        Path(__file__).parents[1] / "rulebook" / "combat_modifiers.yaml"
    )
}


class CombatModifierTests(EvenniaTest):
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
        entity.sexual.arousal.value = "高度"
        self.assertEqual(
            evaluate_combat_modifiers(entity), {"agility": "-20%", "accuracy": -15}
        )
        rule = RULES["high_arousal_agility_accuracy_penalty"]
        entity.sexual.arousal.value = "中等"
        self.assertFalse(evaluate_condition(rule.when, {"arousal": entity.sexual.arousal}))
        entity.sexual.arousal.value = "極限"
        self.assertTrue(evaluate_condition(rule.when, {"arousal": entity.sexual.arousal}))
        self.assertEqual(rule.then, {"agility": "-20%", "accuracy": -15})

    def test_rule_climax_in_progress_locks_actions(self):
        entity = self._entity()
        entity.sexual.climax_phase.value = "進行中"
        self.assertEqual(evaluate_combat_modifiers(entity), {"actions_per_turn": 0})

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
    def test_skill_owned_rows_merge_with_buff_and_sexual_origin_rows(self):
        entity = self._entity()
        entity.db.skills = {"active": [], "passive": ["defense_instinct"]}
        _add_buff(entity, "poisoned")
        entity.sexual.arousal.value = "高度"
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
        from world.rules.combat_modifiers import evaluate_combat_modifiers_no_create

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
