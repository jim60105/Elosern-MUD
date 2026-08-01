"""Structural tripwires against combat-specific resolver branches."""

from tools.spec_traceability import covers_requirement

import inspect
from pathlib import Path
import unittest

from world.rules import action, event_log, targeting


class NoCombatBranchingTests(unittest.TestCase):
    @covers_requirement("action-resolution-pipeline::neither-actionresolver-nor-targeting-branches-on-combat-state")
    @covers_requirement("battlefield-commit-surface::the-no-combat-branching-tripwire-remains-unaffected-by-the-battlefield-surface-addition")
    def test_no_forbidden_combat_state_tokens(self):
        root = Path(__file__).resolve().parents[3]
        for relative in (
            "world/rules/action.py",
            "world/rules/targeting.py",
            "world/rules/event_log.py",
        ):
            source = (root / relative).read_text(encoding="utf-8")
            for token in (
                "in_combat",
                "is_combat",
                "combat_state",
                "isinstance(context, Battlefield",
            ):
                self.assertNotIn(token, source, relative)

    def test_public_callables_have_no_combat_shaped_parameters(self):
        forbidden = {"in_combat", "combat_state", "turn", "is_combat"}
        for module in (action, targeting, event_log):
            for name, value in vars(module).items():
                if name.startswith("_") or not inspect.isfunction(value):
                    continue
                self.assertTrue(
                    forbidden.isdisjoint(inspect.signature(value).parameters),
                    f"{module.__name__}.{name}",
                )
