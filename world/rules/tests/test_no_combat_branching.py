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
        # The resolver module became the world/rules/action/ package; the
        # tripwire scans every module of it plus the sibling scanned modules.
        sources = sorted(
            p.relative_to(root).as_posix()
            for p in (root / "world/rules/action").rglob("*.py")
        ) + [
            "world/rules/targeting.py",
            "world/rules/event_log.py",
        ]
        for relative in sources:
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

        The only conditionals that read ``context.battlefield`` to distinguish
        combat from non-combat behaviour are the usable_out_of_combat gate
        (resolver site in ``action/gates.py``) and the damaging-action gate (shared
        predicate body in ``action_gates.py``, consumed by the resolver and
        the preview). Each carries its marker comment; the shorthand roster
        guard in ``targeting.py`` reads the battlefield through a local
        binding and is a capability read sanctioned by the
        battlefield-action-context spec, not a combat-behaviour branch.
        """
        root = Path(__file__).resolve().parents[3]
        action_src = (root / "world/rules/action/gates.py").read_text(encoding="utf-8")
        gates_src = (root / "world/rules/action_gates.py").read_text(encoding="utf-8")
        targeting_src = (root / "world/rules/targeting.py").read_text(encoding="utf-8")
        # Exactly one `context.battlefield is None` conditional at the resolver
        # gate site and one in the shared gate body; none anywhere else in the
        # scanned modules (the shorthand roster guard uses a local binding).
        self.assertEqual(
            action_src.count("context.battlefield is None"), 1, "action/gates.py"
        )
        self.assertEqual(
            gates_src.count("context.battlefield is None"), 1, "action_gates.py"
        )
        self.assertEqual(
            targeting_src.count("context.battlefield is None"), 0, "targeting.py"
        )
        # Each gate is explicitly marked at its site.
        self.assertIn("Sanctioned combat-state gate 1 of 2", action_src)
        self.assertIn("Sanctioned combat-state gate site 2 of 2", action_src)
        self.assertIn("Sanctioned combat-state gate body", gates_src)

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
