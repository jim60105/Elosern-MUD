"""Repository contract: the art/imports/prompts test migration stays closed.

The migrate-art-imports-tests-off-real-data change removed every ledger DEBT
exemption for the twenty-three ``world/art/tests``, ``world/imports/tests``
and ``world/prompts/tests`` modules it migrated. This contract re-derives the
gate over exactly those files: none may carry a ledger DEBT or CONTRACT
exemption, and all must hold zero lint findings — so a future edit that
reintroduces a shipped identifier cannot silently re-register debt. Every
manifest file resolves game data through the synthetic kit (scoped catalogs,
kit rows, runtime vocabulary probes) or file-local synthetic fixtures, so the
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
    "world/art/tests/test_art_observability.py",
    "world/art/tests/test_connectivity.py",
    "world/art/tests/test_gallery.py",
    "world/art/tests/test_gallery_fallback.py",
    "world/art/tests/test_gallery_match.py",
    "world/art/tests/test_gallery_prompt.py",
    "world/art/tests/test_gallery_seed.py",
    "world/art/tests/test_presenter.py",
    "world/art/tests/test_queue.py",
    "world/art/tests/test_scheduler.py",
    "world/art/tests/test_sd_worker.py",
    "world/art/tests/test_service.py",
    "world/art/tests/test_subjects.py",
    "world/art/tests/test_worker.py",
    "world/imports/tests/test_degraded_banner.py",
    "world/imports/tests/test_loader_trait_values.py",
    "world/imports/tests/test_profession_assembly_loader.py",
    "world/imports/tests/test_profession_assembly_schema.py",
    "world/imports/tests/test_schema.py",
    "world/imports/tests/test_validation_semantics.py",
    "world/prompts/tests/test_degrade.py",
    "world/prompts/tests/test_loader.py",
    "world/prompts/tests/test_verbatim_shipment.py",
)

#: Oversized modules later split into same-named packages (art test split).
#: The ledger/seed checks stay pinned on the original flat paths; the
#: zero-findings scan below expands each split path onto its package slices so
#: the guarantee covers every slice verbatim.
_SPLIT_PACKAGES = (
    "test_gallery",
    "test_service",
    "test_worker",
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


class ArtImportsPromptsTestDataMigrationContractTests(DataIndependenceContractMixin, unittest.TestCase):

    @covers_requirement(
        "test-data-independence::"
        "art-prompt-and-imports-behavior-tests-resolve-game-data-through-"
        "synthetic-fixtures"
    )
    def test_migrated_files_hold_no_ledger_exemption(self):
        self.assert_no_ledger_exemption(MIGRATED_FILES)

    @covers_requirement(
        "test-data-independence::"
        "art-prompt-and-imports-behavior-tests-resolve-game-data-through-"
        "synthetic-fixtures"
    )
    def test_migrated_files_carry_zero_findings(self):
        self.assert_zero_findings(_finding_scan_files())

    def test_no_violation_naming_a_manifest_file(self):
        self.assert_no_violation_naming_manifest(MIGRATED_FILES)

    def test_freeze_ledger_seed_array_untouched_by_the_migration(self):
        self.assert_freeze_seed_untouched(MIGRATED_FILES)


if __name__ == "__main__":
    unittest.main()
