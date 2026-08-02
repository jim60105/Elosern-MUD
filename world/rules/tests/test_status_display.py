"""Status display metadata coverage tests (foundation section 3.2)."""

import unittest

from tools.spec_traceability import covers_requirement

from world.rules.buffs import BUFF_DEFINITIONS
from world.rules.combat_modifiers import _RULES
from world.rules.status_display import STATUS_DISPLAY, display_for


class StatusDisplayCoverageTests(unittest.TestCase):
    @covers_requirement(
        "webclient-status-presentation::status-conditions-use-deterministic-matched-modifiers"
    )
    def test_every_displayable_rule_and_buff_has_exactly_one_entry(self):
        displayable = set(BUFF_DEFINITIONS) | {rule.id for rule in _RULES}
        self.assertEqual(set(STATUS_DISPLAY), displayable)
        for code, display in STATUS_DISPLAY.items():
            self.assertEqual(code, display.code)
            self.assertIn(display.severity, {"beneficial", "informational", "warning", "harmful", "critical"})
            self.assertTrue(display.label)

    def test_display_for_returns_immutable_metadata(self):
        entry = display_for("poisoned")
        self.assertEqual(entry.label, "中毒")
        self.assertEqual(entry.severity, "harmful")


if __name__ == "__main__":
    unittest.main()
