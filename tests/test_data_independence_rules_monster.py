"""Repository contract: the monster/aftermath test migration stays closed.

The migrate-rules-monster-tests-off-real-data change removed every ledger
exemption for the fourteen ``world/rules/tests`` modules it migrated. This
contract re-derives the gate over exactly those files: none may carry a ledger
DEBT or CONTRACT exemption, and all must hold zero lint findings — so a future
edit that reintroduces a shipped identifier cannot silently re-register debt.
Every manifest file is a pure behavior suite: the shipped-content claims that
had to survive relocation (rulebook tier-archetype mechanics, flee thresholds,
restock/causality mechanics) are exercised through runtime vocabulary probes
and file-local synthetic rows instead of registered contract files, so the
whole manifest stays debt-free and finding-free.
"""

from pathlib import Path
import unittest

from tools import test_data_lint
from tools.spec_traceability import covers_requirement
from ._data_independence_base import DataIndependenceContractMixin

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The migrated modules; none may carry a ledger exemption ever again.
MIGRATED_FILES = (
    "world/rules/tests/test_defeat_aftermath_core.py",
    "world/rules/tests/test_defeat_aftermath_digest.py",
    "world/rules/tests/test_defeat_aftermath_violation.py",
    "world/rules/tests/test_monster_behaviour_determinism.py",
    "world/rules/tests/test_monster_behaviour_golden.py",
    "world/rules/tests/test_monster_behaviour_integration.py",
    "world/rules/tests/test_monster_behaviour_policy.py",
    "world/rules/tests/test_monster_behaviour_selection.py",
    "world/rules/tests/test_monster_flee_decision.py",
    "world/rules/tests/test_monster_scale.py",
    "world/rules/tests/test_monster_sexual_baseline.py",
    "world/rules/tests/test_overwhelm_compression.py",
    "world/rules/tests/test_overwhelm_resolution.py",
    "world/rules/tests/test_overwhelm_threshold.py",
)

#: Oversized modules later split into same-named packages (rules test split).
#: The ledger/seed checks stay pinned on the original flat paths; the
#: file-level checks below expand each split path onto its package slices so
#: the zero-findings guarantee covers every slice verbatim.
_SPLIT_PACKAGES = (
    "test_defeat_aftermath_core",
    "test_defeat_aftermath_violation",
)


def _finding_scan_files(paths) -> tuple[str, ...]:
    """Every manifest file to scan, following split modules into slices."""
    files: list[str] = []
    for rel in paths:
        name = rel.rsplit("/", 1)[-1][: -len(".py")]
        if name in _SPLIT_PACKAGES:
            package = (REPO_ROOT / rel).with_suffix("")
            files.extend(
                str(path.relative_to(REPO_ROOT))
                for path in sorted(package.rglob("*.py"))
                if "__pycache__" not in path.parts
            )
        else:
            files.append(rel)
    return tuple(files)


class RulesMonsterTestDataMigrationContractTests(DataIndependenceContractMixin, unittest.TestCase):

    @covers_requirement(
        "test-data-independence::"
        "monster-and-aftermath-behavior-tests-resolve-game-data-through-synthetic-fixtures"
    )
    def test_migrated_files_hold_no_ledger_exemption(self):
        self.assert_no_ledger_exemption(MIGRATED_FILES)

    @covers_requirement(
        "test-data-independence::"
        "monster-and-aftermath-behavior-tests-resolve-game-data-through-synthetic-fixtures"
    )
    def test_migrated_files_carry_zero_findings(self):
        self.assert_zero_findings(_finding_scan_files(MIGRATED_FILES))

    def test_no_violation_naming_a_manifest_file(self):
        self.assert_no_violation_naming_manifest(_finding_scan_files(MIGRATED_FILES))

    def test_freeze_ledger_seed_array_untouched_by_the_migration(self):
        self.assert_freeze_seed_untouched(MIGRATED_FILES)


if __name__ == "__main__":
    unittest.main()
