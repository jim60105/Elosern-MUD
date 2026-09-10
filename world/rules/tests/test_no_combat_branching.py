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

    @covers_requirement("action-resolution-pipeline::neither-actionresolver-nor-targeting-branches-on-combat-state")
    def test_exactly_the_two_sanctioned_battlefield_gates_exist(self):
        """The two-gate contract: exactly two marked combat-state conditionals.

        The only conditionals in ``action.py`` and ``targeting.py`` that read
        ``context.battlefield`` to distinguish combat from non-combat
        behaviour are the usable_out_of_combat gate (resolver site) and the
        damaging-action gate (shared predicate body in ``targeting.py``,
        consumed by the resolver and the preview). Each carries its marker
        comment; the shorthand roster guard reads the battlefield through a
        local binding and is a capability read sanctioned by the
        battlefield-action-context spec, not a combat-behaviour branch.
        """
        root = Path(__file__).resolve().parents[3]
        action_src = (root / "world/rules/action.py").read_text(encoding="utf-8")
        targeting_src = (
            root / "world/rules/targeting.py"
        ).read_text(encoding="utf-8")
        # Exactly one `context.battlefield is None` conditional per file, and
        # none anywhere else in the two scanned modules.
        self.assertEqual(
            action_src.count("context.battlefield is None"), 1, "action.py"
        )
        self.assertEqual(
            targeting_src.count("context.battlefield is None"), 1, "targeting.py"
        )
        # Each gate is explicitly marked at its site.
        self.assertIn("Sanctioned combat-state gate 1 of 2", action_src)
        self.assertIn("Sanctioned combat-state gate site 2 of 2", action_src)
        self.assertIn("Sanctioned combat-state gate body", targeting_src)

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
