"""Unit tests for the shared declarative condition grammar."""

from tools.spec_traceability import covers_requirement

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from world.rules.rulebook.schema import (
    DuplicateRuleIdError,
    MissingRuleIdError,
    evaluate_condition,
    load_rules,
)


def _entity_owning(*skill_keys: str):
    class _FakeSkills:
        def owned_keys(self):
            return list(skill_keys)

        def conferred_grants(self):
            return []

    class _FakeEntity:
        skills = _FakeSkills()

    return _FakeEntity()


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
        self.assertTrue(
            evaluate_condition(
                {"skill_owned": "blade_art_mastery"},
                {"entity": _entity_owning("blade_art_mastery")},
            )
        )
        combined = {"field": "level", "gte": 3, "buff_active": "fear"}
        self.assertFalse(evaluate_condition(combined, {"level": 4}))
        self.assertTrue(
            evaluate_condition(combined, {"level": 4, "active_buffs": {"fear"}})
        )

    @covers_requirement("rulebook-schema::evaluate-condition-is-the-one-shared-matcher-for-event-field-threshold", "rulebook-schema::every-rule-carries-a-required-unique-id")
    def test_missing_context_is_false_and_unknown_key_raises(self):
        self.assertFalse(evaluate_condition({"field": "level", "gte": 3}, {}))
        self.assertFalse(evaluate_condition({"skill_owned": "x"}, {}))
        with self.assertRaisesRegex(ValueError, "unknown"):
            evaluate_condition({"unknown": "x"}, {})

    @covers_requirement("rulebook-schema::schema-py-documents-itself-as-the-shared-engine-for-every-rulebook-table-not-a", "sexual-vocabulary::the-module-documents-itself-as-the-single-canonical-source-for-this-vocabulary")
    @covers_requirement("sexual-transition-rulebook::the-stamina-action-efficiency-threshold-has-no-row-in-sexual-yaml-and-is-named-for-change-6")
    def test_docstring_names_future_sexual_table(self):
        from world.rules.rulebook import schema

        self.assertIn("sexual.yaml", schema.__doc__)
