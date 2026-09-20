"""Repository contract: the webclient presentation test migration stays closed.

The migrate-webclient-presentation-tests-off-real-data change removed every
ledger DEBT exemption for the eighteen ``web/webclient/presentation/tests``
modules it migrated. This contract re-derives the gate over exactly those
files: none may carry a ledger DEBT or CONTRACT exemption, and all must hold
zero lint findings — so a future edit that reintroduces a shipped identifier
cannot silently re-register debt. Every manifest file resolves game data
through the synthetic kit (scoped catalogs, kit rows, runtime vocabulary
probes) or file-local synthetic fixtures, so the whole manifest stays
debt-free and finding-free.
"""

from pathlib import Path
import unittest

from tools import test_data_lint
from tools.spec_traceability import covers_requirement
from ._data_independence_base import DataIndependenceContractMixin

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The migrated modules; none may carry a ledger exemption ever again.
MIGRATED_FILES = (
    "web/webclient/presentation/tests/test_affordances.py",
    "web/webclient/presentation/tests/test_art_panel.py",
    "web/webclient/presentation/tests/test_art_push.py",
    "web/webclient/presentation/tests/test_character_panel.py",
    "web/webclient/presentation/tests/test_combat_panel.py",
    "web/webclient/presentation/tests/test_creation_panel.py",
    "web/webclient/presentation/tests/test_dialogue_panel.py",
    "web/webclient/presentation/tests/test_exploration_panel.py",
    "web/webclient/presentation/tests/test_lineage_panel.py",
    "web/webclient/presentation/tests/test_local_map.py",
    "web/webclient/presentation/tests/test_lore_codex_panel.py",
    "web/webclient/presentation/tests/test_objectives_panel.py",
    "web/webclient/presentation/tests/test_party_panel.py",
    "web/webclient/presentation/tests/test_possession_presentation.py",
    "web/webclient/presentation/tests/test_presentation_context.py",
    "web/webclient/presentation/tests/test_quest_log_panel.py",
    "web/webclient/presentation/tests/test_services_panel.py",
    "web/webclient/presentation/tests/test_title_codex_panel.py",
)

#: Oversized modules later split into same-named packages (presentation test
#: split). The ledger/seed checks stay pinned on the original flat paths; the
#: file-level checks below expand each split path onto its package slices so
#: the zero-findings guarantee covers every slice verbatim.
_SPLIT_PACKAGES = ("test_combat_panel", "test_exploration_panel", "test_local_map")


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


class WebclientPresentationTestDataMigrationContractTests(DataIndependenceContractMixin, unittest.TestCase):

    @covers_requirement(
        "test-data-independence::"
        "webclient-presentation-behavior-tests-resolve-game-data-through-"
        "synthetic-fixtures"
    )
    def test_migrated_files_hold_no_ledger_exemption(self):
        self.assert_no_ledger_exemption(MIGRATED_FILES)

    @covers_requirement(
        "test-data-independence::"
        "webclient-presentation-behavior-tests-resolve-game-data-through-"
        "synthetic-fixtures"
    )
    def test_migrated_files_carry_zero_findings(self):
        self.assert_zero_findings(_finding_scan_files())

    def test_no_violation_naming_a_manifest_file(self):
        self.assert_no_violation_naming_manifest(_finding_scan_files())

    def test_freeze_ledger_seed_array_untouched_by_the_migration(self):
        self.assert_freeze_seed_untouched(MIGRATED_FILES)


if __name__ == "__main__":
    unittest.main()
