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
