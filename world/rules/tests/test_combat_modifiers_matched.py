"""Regression tests for the read-only matched combat-modifier query (3.1)."""

from pathlib import Path
import unittest

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.buffs import _add_buff
from world.rules.combat_modifiers import evaluate_combat_modifiers, matched_combat_modifiers
from world.rules.rulebook.schema import load_rules

RULES = {
    rule.id: rule
    for rule in load_rules(Path(__file__).parents[1] / "rulebook" / "combat_modifiers.yaml")
}


class MatchedCombatModifiersTests(EvenniaTest):
    def _entity(self):
        entity = create_object(PlayerCharacter, key="matched target")
        entity.race = "human"
        entity.apply_race_baseline()
        return entity

    def test_matched_sequence_matches_merged_evaluation_for_each_rule(self):
        entity = self._entity()
        _add_buff(entity, "poisoned")
        matches = dict(matched_combat_modifiers(entity))
        self.assertEqual(matches["poison_agility_penalty"], {"agility": "-10%"})
        merged = evaluate_combat_modifiers(entity)
        expected = {}
        for adjustments in matches.values():
            from world.rules.combat_modifiers import _merge_adjustments

            expected = _merge_adjustments(expected, adjustments)
        self.assertEqual(merged, expected)

    def test_sexual_rule_matches_are_exposed(self):
        entity = self._entity()
        entity.sexual.arousal.value = "高度"
        matches = dict(matched_combat_modifiers(entity))
        self.assertEqual(
            matches["high_arousal_agility_accuracy_penalty"],
            {"agility": "-20%", "accuracy": -15},
        )

    def test_merged_combination_identical_to_evaluate(self):
        entity = self._entity()
        _add_buff(entity, "poisoned")
        _add_buff(entity, "fear")
        entity.sexual.arousal.value = "高度"
        matches = matched_combat_modifiers(entity)
        ids = [rule_id for rule_id, _ in matches]
        self.assertEqual(
            ids,
            [
                "poison_agility_penalty",
                "fear_agility_and_accuracy_penalty",
                "high_arousal_agility_accuracy_penalty",
            ],
        )
        expected = {}
        for _, adjustments in matches:
            from world.rules.combat_modifiers import _merge_adjustments

            expected = _merge_adjustments(expected, adjustments)
        self.assertEqual(evaluate_combat_modifiers(entity), expected)

    def test_query_is_pure(self):
        entity = self._entity()
        _add_buff(entity, "fear")
        before = {key: getattr(entity.traits, key).value for key in entity.traits.all()}
        active = set(entity.buffs.all)
        matched_combat_modifiers(entity)
        self.assertEqual(active, set(entity.buffs.all))
        self.assertEqual(
            before, {key: getattr(entity.traits, key).value for key in entity.traits.all()}
        )

    def test_explicit_context_supplies_sexual_state(self):
        from world.rules.sexual_state import AROUSAL_LEVELS
        from world.rules.status_query import _LevelRef

        entity = self._entity()
        context = {"active_buffs": set()}
        self.assertEqual(matched_combat_modifiers(entity, context=context), ())
        context["arousal"] = _LevelRef(AROUSAL_LEVELS.index("極限"), AROUSAL_LEVELS)
        matches = dict(matched_combat_modifiers(entity, context=context))
        self.assertIn("high_arousal_agility_accuracy_penalty", matches)


if __name__ == "__main__":
    unittest.main()
