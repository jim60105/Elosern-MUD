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


class ArtImportsPromptsTestDataMigrationContractTests(unittest.TestCase):
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

    def test_no_violation_naming_a_manifest_file(self):
        # Whole-repo greenness is owned by the ``tools.test_data_lint check``
        # gate itself; inside the Evennia test runner a process-wide universe
        # can pick up lazily-registered vocabulary and name unrelated files.
        # What must never regress is a violation whose path belongs to this
        # migration's manifest.
        report = test_data_lint.check_repo(test_data_lint.REPO_ROOT)
        mine = set(MIGRATED_FILES)
        self.assertEqual(
            [
                f"{v.path}: {v.rule}: {v.detail}"
                for v in report.violations
                if v.path in mine
            ],
            [],
        )

    def test_freeze_ledger_seed_array_untouched_by_the_migration(self):
        # The migration removed debt entries only; the carried classification
        # still lists every seeded debt path in its exact committed order
        # (shrink-only ratchet design; a reorder is a regression too).
        seed = test_data_lint.load_seed(test_data_lint.REPO_ROOT)
        seed_debt = set(seed["seedDebtPaths"])
        for path in MIGRATED_FILES:
            self.assertIn(path, seed_debt)
        self.assertEqual(self.ledger["seedDebtPaths"], seed["seedDebtPaths"])


if __name__ == "__main__":
    unittest.main()
