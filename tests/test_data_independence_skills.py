"""Repository contract: the skills test migration off shipped data stays closed.

The migrate-skills-tests-off-real-data change removed every exemption for the
seven ``world/skills/tests`` modules from the test-data-independence ledger.
This contract re-derives the gate over exactly those files: they must carry no
ledger exemption (debt or contract) AND zero lint findings, so a future edit
that reintroduces a shipped identifier cannot silently re-register debt.
"""

from pathlib import Path
import unittest

from tools import test_data_lint
from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The migrated modules; none may carry a ledger exemption ever again.
MIGRATED_FILES = tuple(
    f"world/skills/tests/test_{name}.py"
    for name in (
        "conferral",
        "disguise_effect",
        "effects",
        "equipment",
        "handler",
        "inventory",
        "skill_casts",
    )
)


class SkillsTestDataMigrationContractTests(unittest.TestCase):
    def setUp(self):
        self.ledger, fatal = test_data_lint.load_ledger(test_data_lint.REPO_ROOT)
        self.assertEqual(fatal, [], "ledger must load cleanly")

    @covers_requirement(
        "test-data-independence::skills-package-behavior-tests-resolve-game-data-through-synthetic-fixtures"
    )
    def test_migrated_files_hold_no_ledger_exemption(self):
        debt = set(self.ledger["debt"])
        contract = {entry["path"] for entry in self.ledger["contract"]}
        for path in MIGRATED_FILES:
            self.assertNotIn(path, debt, f"{path} reintroduced into debt")
            self.assertNotIn(path, contract, f"{path} registered as contract")

    @covers_requirement(
        "test-data-independence::skills-package-behavior-tests-resolve-game-data-through-synthetic-fixtures"
    )
    def test_migrated_files_carry_zero_findings(self):
        universe = test_data_lint.derive_universe(test_data_lint.REPO_ROOT)
        for path in MIGRATED_FILES:
            with self.subTest(path=path):
                self.assertTrue((test_data_lint.REPO_ROOT / path).is_file())
                self.assertEqual(
                    test_data_lint.scan_file(test_data_lint.REPO_ROOT, path, universe),
                    [],
                )

    @covers_requirement(
        "test-data-independence::skills-package-behavior-tests-resolve-game-data-through-synthetic-fixtures"
    )
    def test_gate_is_green_and_reports_no_violation_for_migrated_files(self):
        report = test_data_lint.check_repo(test_data_lint.REPO_ROOT)
        self.assertTrue(
            report.ok,
            "\n".join(
                f"{v.path}: {v.rule}: {v.detail}" for v in report.violations
            ),
        )

    @covers_requirement(
        "test-data-independence::skills-package-behavior-tests-resolve-game-data-through-synthetic-fixtures"
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
