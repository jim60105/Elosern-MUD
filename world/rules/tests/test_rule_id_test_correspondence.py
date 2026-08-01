"""Mechanical one-test-per-rule checks."""

from tools.spec_traceability import covers_requirement

import inspect
from pathlib import Path
from unittest import TestCase

from world.rules.buffs import BUFF_DEFINITIONS
from world.rules.rulebook.schema import load_rules
from world.rules.tests import test_buffs, test_combat_modifiers


class RuleCorrespondenceTests(TestCase):
    @covers_requirement("buff-handler-integration::every-buff-key-in-buffs-yaml-has-exactly-one-corresponding-unit-test", "combat-modifier-table::every-rule-id-in-combat-modifiers-yaml-has-exactly-one-corresponding-unit-test", "sexual-transition-rulebook::every-rule-id-has-exactly-one-matching-test-structurally-enforced")
    def test_every_rule_and_buff_has_exactly_one_named_test(self):
        combat_names = [
            name for name, _ in inspect.getmembers(
                test_combat_modifiers.CombatModifierTests, inspect.isfunction
            )
        ]
        rules = load_rules(
            Path(__file__).parents[1] / "rulebook" / "combat_modifiers.yaml"
        )
        for rule in rules:
            self.assertEqual(combat_names.count(f"test_rule_{rule.id}"), 1, rule.id)

        buff_names = [
            name for name, _ in inspect.getmembers(
                test_buffs.BuffIntegrationTests, inspect.isfunction
            )
        ]
        for key in BUFF_DEFINITIONS:
            self.assertEqual(buff_names.count(f"test_buff_{key}"), 1, key)
