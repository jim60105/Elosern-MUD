"""Repository contract: the rules creation/progression migration stays closed.

The migrate-rules-creation-progression-tests-off-real-data change removed
every ledger exemption for the twenty-one ``world/rules/tests`` modules it
migrated (including the two zero-findings debt files, which migrated by
entry removal alone). This contract re-derives the gate over exactly those
files: none may carry a ledger DEBT exemption again, and all must report
zero lint findings — so a future edit that reintroduces a shipped identifier
cannot silently re-register debt.

Annotated with the canonical requirement id added when this change's delta
is archived/synced into ``openspec/specs``.
"""

from pathlib import Path
import unittest

from tools import test_data_lint

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The migrated modules; none may carry a ledger exemption ever again.
MIGRATED_FILES = (
    "world/rules/tests/test_character_creation.py",
    "world/rules/tests/test_cmd_cast.py",
    "world/rules/tests/test_conferral_action.py",
    "world/rules/tests/test_creation_messages.py",
    "world/rules/tests/test_creation_wizard.py",
    "world/rules/tests/test_divine_mystery_gate.py",
    "world/rules/tests/test_effective_power.py",
    "world/rules/tests/test_event_log.py",
    "world/rules/tests/test_lineage_query.py",
    "world/rules/tests/test_movement.py",
    "world/rules/tests/test_movement_settlement.py",
    "world/rules/tests/test_persona.py",
    "world/rules/tests/test_persona_edit.py",
    "world/rules/tests/test_progression.py",
    "world/rules/tests/test_race_scale.py",
    "world/rules/tests/test_skill_lineage.py",
    "world/rules/tests/test_skip_commands.py",
    "world/rules/tests/test_stat_breakdown.py",
    "world/rules/tests/test_subrace_order.py",
    "world/rules/tests/test_tier_construction.py",
    "world/rules/tests/test_time_skip.py",
)


class RulesCreationProgressionTestDataMigrationContractTests(unittest.TestCase):
    def setUp(self):
        self.ledger, fatal = test_data_lint.load_ledger(test_data_lint.REPO_ROOT)
        self.assertEqual(fatal, [], "ledger must load cleanly")

    def test_migrated_files_hold_no_ledger_exemption(self):
        debt = set(self.ledger["debt"])
        contract = {entry["path"] for entry in self.ledger["contract"]}
        for path in MIGRATED_FILES:
            self.assertNotIn(path, debt, f"{path} reintroduced into debt")
            self.assertNotIn(path, contract, f"{path} registered as contract")

    def test_migrated_files_carry_zero_findings(self):
        universe = test_data_lint.derive_universe(test_data_lint.REPO_ROOT)
        for path in MIGRATED_FILES:
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
