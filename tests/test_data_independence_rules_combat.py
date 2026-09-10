"""Repository contract: the rules/combat test migration off shipped data stays closed.

The migrate-rules-combat-core-tests-off-real-data change removed every ledger
exemption for the eighteen ``world/rules/tests`` modules it migrated. This
contract re-derives the gate over exactly those files: they must carry no
ledger DEBT exemption, and the seventeen migrated as behavior tests must carry
zero lint findings — so a future edit that reintroduces a shipped identifier
cannot silently re-register debt. ``test_combat_modifiers.py`` is the one
manifest file whose claims are shipped-content rulebook bindings: it migrated
to a registered Data-contract file instead (its debt entry is still gone).

Deliberately shipped WITHOUT a ``@covers_requirement`` annotation: the
requirement id does not exist in the traceability index until the change
delta is archived/synced; the archive step adds the canonical id.
"""

from pathlib import Path
import unittest

from tools import test_data_lint

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The migrated modules; none may carry a ledger exemption ever again.
MIGRATED_FILES = (
    "world/rules/tests/_combat_session_helpers.py",
    "world/rules/tests/test_affinity.py",
    "world/rules/tests/test_combat_initiation.py",
    "world/rules/tests/test_combat_modifiers.py",
    "world/rules/tests/test_combat_modifiers_matched.py",
    "world/rules/tests/test_combat_result.py",
    "world/rules/tests/test_combat_session_flow.py",
    "world/rules/tests/test_combat_session_recovery.py",
    "world/rules/tests/test_combat_session_targeting.py",
    "world/rules/tests/test_combat_view.py",
    "world/rules/tests/test_disengage.py",
    "world/rules/tests/test_disengage_integration.py",
    "world/rules/tests/test_freeform_casting.py",
    "world/rules/tests/test_friendly_fire.py",
    "world/rules/tests/test_golden_combat.py",
    "world/rules/tests/test_initiative_and_turn_loop.py",
    "world/rules/tests/test_phase4_integration.py",
    "world/rules/tests/test_targeting.py",
)

#: The manifest file whose shipped-content claims moved to a registered
#: Data-contract file instead of synthetic fixtures.
CONTRACT_FILE = "world/rules/tests/test_combat_modifiers.py"
#: The remaining manifest files: pure behavior tests, zero findings allowed.
BEHAVIOR_FILES = tuple(p for p in MIGRATED_FILES if p != CONTRACT_FILE)


class RulesCombatTestDataMigrationContractTests(unittest.TestCase):
    def setUp(self):
        self.ledger, fatal = test_data_lint.load_ledger(test_data_lint.REPO_ROOT)
        self.assertEqual(fatal, [], "ledger must load cleanly")

    def test_migrated_files_hold_no_ledger_exemption(self):
        debt = set(self.ledger["debt"])
        contract = {entry["path"] for entry in self.ledger["contract"]}
        for path in MIGRATED_FILES:
            self.assertNotIn(path, debt, f"{path} reintroduced into debt")
            if path == CONTRACT_FILE:
                self.assertIn(path, contract, f"{path} lost its contract entry")
            else:
                self.assertNotIn(path, contract, f"{path} registered as contract")

    def test_migrated_files_carry_zero_findings(self):
        universe = test_data_lint.derive_universe(test_data_lint.REPO_ROOT)
        for path in BEHAVIOR_FILES:
            with self.subTest(path=path):
                self.assertTrue((test_data_lint.REPO_ROOT / path).is_file())
                self.assertEqual(
                    test_data_lint.scan_file(test_data_lint.REPO_ROOT, path, universe),
                    [],
                )

    def test_gate_is_green_and_reports_no_violation_for_migrated_files(self):
        report = test_data_lint.check_repo(test_data_lint.REPO_ROOT)
        self.assertTrue(
            report.ok,
            "\n".join(
                f"{v.path}: {v.rule}: {v.detail}" for v in report.violations
            ),
        )

    def test_freeze_ledger_seed_array_untouched_by_the_migration(self):
        # The migration removed debt entries only; the carried classification
        # still lists every seeded debt path (shrink-only ratchet design).
        seed = test_data_lint.load_seed(test_data_lint.REPO_ROOT)
        seed_debt = set(seed["seedDebtPaths"])
        for path in MIGRATED_FILES:
            self.assertIn(path, seed_debt)
        self.assertEqual(
            sorted(self.ledger["seedDebtPaths"]), sorted(seed["seedDebtPaths"])
        )


if __name__ == "__main__":
    unittest.main()
