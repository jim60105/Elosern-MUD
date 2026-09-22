"""Mechanical one-test-per-rule checks."""

from tools.spec_traceability import covers_requirement

import inspect
from pathlib import Path
from unittest import TestCase

from world.rules.rulebook.schema import load_rules, load_sectioned_rules
from world.rules.tests import test_combat_modifiers
from world.rules.tests import test_church_rulebook


class RuleCorrespondenceTests(TestCase):
    @covers_requirement("combat-modifier-table::every-rule-id-in-combat-modifiers-yaml-has-exactly-one-corresponding-unit-test", "sexual-transition-rulebook::every-rule-id-has-exactly-one-matching-test-structurally-enforced")
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

    @covers_requirement(
        "church-ordination::the-church-rulebook-slice-loads-behind-the-monotonicity-and-polarity-gates"
    )
    def test_every_church_rule_has_exactly_one_named_test(self):
        """The church.yaml one-row-one-test gate (same audit as combat_modifiers)."""
        church_names = [
            name
            for name, _ in inspect.getmembers(
                test_church_rulebook.ChurchTuningTests, inspect.isfunction
            )
        ]
        rows = load_sectioned_rules(
            Path(__file__).parents[1] / "rulebook" / "church.yaml"
        )
        for row in rows:
            self.assertEqual(
                church_names.count(f"test_rule_{row.id}"), 1, row.id
            )
