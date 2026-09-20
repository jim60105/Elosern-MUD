"""Repository contract: the rules/combat test migration off shipped data stays closed.

The migrate-rules-combat-core-tests-off-real-data change removed every ledger
exemption for the eighteen ``world/rules/tests`` modules it migrated. This
contract re-derives the gate over exactly those files: they must carry no
ledger DEBT or CONTRACT exemption, and all eighteen must carry zero lint
findings — so a future edit that reintroduces a shipped identifier cannot
silently re-register debt. ``test_combat_modifiers.py`` was later converted
from a registered Data-contract file to a pure behavior suite: its rule-bound
tests derive triggers and expectations from the loaded rule table at runtime,
so it holds no ledger exemption either.

Annotated with the canonical requirement id added when this change's delta
was archived/synced into ``openspec/specs``.
"""

from pathlib import Path
import unittest

from tools import test_data_lint
from tools.spec_traceability import covers_requirement
from ._data_independence_base import DataIndependenceContractMixin

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

#: All manifest files are pure behavior tests: zero findings allowed.
BEHAVIOR_FILES = MIGRATED_FILES

#: Oversized modules later split into same-named packages (rules test split).
#: The ledger/seed checks stay pinned on the original flat paths; the
#: file-level checks below expand each split path onto its package slices so
#: the zero-findings guarantee covers every slice verbatim.
_SPLIT_PACKAGES = (
    "test_combat_session_flow",
    "test_freeform_casting",
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


class RulesCombatTestDataMigrationContractTests(DataIndependenceContractMixin, unittest.TestCase):

    @covers_requirement(
        "test-data-independence::"
        "combat-core-behavior-tests-resolve-game-data-through-synthetic-fixtures"
    )
    def test_migrated_files_hold_no_ledger_exemption(self):
        self.assert_no_ledger_exemption(MIGRATED_FILES)

    def test_migrated_files_carry_zero_findings(self):
        self.assert_zero_findings(_finding_scan_files(BEHAVIOR_FILES))

    def test_gate_is_green_and_reports_no_violation_for_migrated_files(self):
        self.assert_gate_green_for_manifest()

    def test_freeze_ledger_seed_array_untouched_by_the_migration(self):
        self.assert_freeze_seed_untouched(MIGRATED_FILES, exact_order=False)


if __name__ == "__main__":
    unittest.main()
