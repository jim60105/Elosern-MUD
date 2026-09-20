"""Repository contract: the rules creation/progression migration stays closed.

The migrate-rules-creation-progression-tests-off-real-data change removed
every ledger exemption for the ``world/rules/tests`` modules it migrated
(including the two zero-findings debt files, which migrated by entry removal
alone). ``test_conferral_action.py`` left the closure when
``conferral-grant-store`` retired the module's event-context contract in the
same branch. This contract re-derives the gate over exactly the remaining
files: none may carry a ledger DEBT exemption again, and all must report zero
lint findings — so a future edit that reintroduces a shipped identifier cannot
silently re-register debt.

Annotated with the canonical requirement id added when this change's delta
is archived/synced into ``openspec/specs``.
"""

from pathlib import Path
import unittest

from tools import test_data_lint
from tools.spec_traceability import covers_requirement
from ._data_independence_base import DataIndependenceContractMixin

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The migrated modules; none may carry a ledger exemption ever again.
MIGRATED_FILES = (
    "world/rules/tests/test_character_creation.py",
    "world/rules/tests/test_cmd_cast.py",
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

#: Oversized modules later split into same-named packages (rules test split).
#: The ledger/seed checks stay pinned on the original flat paths; the
#: zero-findings scan below expands each split path onto its package slices so
#: the guarantee covers every slice verbatim.
_SPLIT_PACKAGES = (
    "test_character_creation",
    "test_progression",
)


def _finding_scan_files() -> tuple[str, ...]:
    """Every manifest file to scan, following split modules into slices."""
    files: list[str] = []
    for rel in MIGRATED_FILES:
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


class RulesCreationProgressionTestDataMigrationContractTests(DataIndependenceContractMixin, unittest.TestCase):

    @covers_requirement(
        "test-data-independence::"
        "creation-progression-and-lineage-behavior-tests-resolve-game-data-"
        "through-synthetic-fixtures"
    )
    def test_migrated_files_hold_no_ledger_exemption(self):
        self.assert_no_ledger_exemption(MIGRATED_FILES)

    def test_migrated_files_carry_zero_findings(self):
        self.assert_zero_findings(_finding_scan_files())

    def test_gate_is_green_and_reports_no_violation_for_migrated_files(self):
        self.assert_gate_green_for_manifest()

    def test_freeze_ledger_seed_array_untouched_by_the_migration(self):
        self.assert_freeze_seed_untouched(MIGRATED_FILES, exact_order=False)


if __name__ == "__main__":
    unittest.main()
