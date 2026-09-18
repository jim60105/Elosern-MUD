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
from ._data_independence_base import DataIndependenceContractMixin

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


class SkillsTestDataMigrationContractTests(DataIndependenceContractMixin, unittest.TestCase):

    @covers_requirement(
        "test-data-independence::skills-package-behavior-tests-resolve-game-data-through-synthetic-fixtures"
    )
    def test_migrated_files_hold_no_ledger_exemption(self):
        self.assert_no_ledger_exemption(MIGRATED_FILES)

    @covers_requirement(
        "test-data-independence::skills-package-behavior-tests-resolve-game-data-through-synthetic-fixtures"
    )
    def test_migrated_files_carry_zero_findings(self):
        self.assert_zero_findings(MIGRATED_FILES)

    @covers_requirement(
        "test-data-independence::skills-package-behavior-tests-resolve-game-data-through-synthetic-fixtures"
    )
    def test_gate_is_green_and_reports_no_violation_for_migrated_files(self):
        self.assert_gate_green_for_manifest()

    @covers_requirement(
        "test-data-independence::skills-package-behavior-tests-resolve-game-data-through-synthetic-fixtures"
    )
    def test_freeze_ledger_seed_array_untouched_by_the_migration(self):
        self.assert_freeze_seed_untouched(MIGRATED_FILES, exact_order=False)


if __name__ == "__main__":
    unittest.main()
