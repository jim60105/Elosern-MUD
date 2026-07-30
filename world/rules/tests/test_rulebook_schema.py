"""Unit tests for the shared declarative condition grammar."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from world.rules.rulebook.schema import (
    DuplicateRuleIdError,
    MissingRuleIdError,
    evaluate_condition,
    load_rules,
)


class RulebookSchemaTests(TestCase):
    def _rules(self, content):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "rules.yaml"
            path.write_text(content, encoding="utf-8")
            return load_rules(path)

    def test_loader_requires_unique_ids_and_accepts_opaque_effects(self):
        with self.assertRaises(MissingRuleIdError):
            self._rules("- when: {}\n  then: {}\n")
        with self.assertRaises(DuplicateRuleIdError):
            self._rules(
                "- {id: same, when: {}, then: {}}\n"
                "- {id: same, when: {}, then: {}}\n"
            )
        rules = self._rules(
            "- {id: combat, when: {event: x}, then: {agility: '-20%'}}\n"
            "- {id: sexual, when: {event: y}, then: {field: arousal, delta: 1}}\n"
        )
        self.assertEqual([rule.id for rule in rules], ["combat", "sexual"])

    def test_every_condition_kind_and_implicit_and(self):
        self.assertTrue(evaluate_condition({"event": "x"}, {"event": "x"}))
        self.assertTrue(
            evaluate_condition({"field": "phase", "equals": "進行中"}, {"phase": "進行中"})
        )
        self.assertTrue(evaluate_condition({"field": "level", "gte": 3}, {"level": 4}))
        self.assertTrue(
            evaluate_condition(
                {"field_changed": "arousal", "direction": "up"},
                {"_changed": {"arousal": "up"}},
            )
        )
        self.assertTrue(
            evaluate_condition(
                {"buff_active": "fear"}, {"active_buffs": {"fear"}}
            )
        )
        combined = {"field": "level", "gte": 3, "buff_active": "fear"}
        self.assertFalse(evaluate_condition(combined, {"level": 4}))
        self.assertTrue(
            evaluate_condition(combined, {"level": 4, "active_buffs": {"fear"}})
        )

    def test_missing_context_is_false_and_unknown_key_raises(self):
        self.assertFalse(evaluate_condition({"field": "level", "gte": 3}, {}))
        with self.assertRaisesRegex(ValueError, "unknown"):
            evaluate_condition({"unknown": "x"}, {})

    def test_docstring_names_future_sexual_table(self):
        from world.rules.rulebook import schema

        self.assertIn("sexual.yaml", schema.__doc__)
