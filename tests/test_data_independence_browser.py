"""Repository contract: the browser-test migration off real data stays closed.

The migrate-browser-tests-off-real-data change removed every ledger DEBT
exemption for the nineteen Playwright-suite files it migrated (the harness
modules ``browser_helpers.py``/``browser_settings.py``/``seed.py`` plus the
sixteen ``test_browser_*``/``test_vue_foundation`` journey files). This
contract re-derives the gate over exactly those files: none may carry a
ledger DEBT or CONTRACT exemption, and all must hold zero lint findings —
so a future edit that reintroduces a shipped identifier cannot silently
re-register debt. Every manifest file resolves game data through the
support module ``web/browser_support/browser_fixtures_data.py`` (boot-mode
``SHIPPED_*``/``SYNTH_*`` vocabularies and journey-value helpers), the
synthetic kit ``world/tests/synthetic_data.py``, or values read from the
committed panel snapshots at runtime; the support module lives outside the
scanned tree, so it can name shipped vocabulary while every scanned file
stays literal-free.
"""

from pathlib import Path
import unittest

from tools import test_data_lint

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The migrated modules; none may carry a ledger exemption ever again.
MIGRATED_FILES = (
    "web/tests/browser/browser_helpers.py",
    "web/tests/browser/browser_settings.py",
    "web/tests/browser/seed.py",
    "web/tests/browser/test_browser_art.py",
    "web/tests/browser/test_browser_combat.py",
    "web/tests/browser/test_browser_combat_rejection.py",
    "web/tests/browser/test_browser_contextual_hud.py",
    "web/tests/browser/test_browser_creation.py",
    "web/tests/browser/test_browser_exploration.py",
    "web/tests/browser/test_browser_input_narrative.py",
    "web/tests/browser/test_browser_inventory_actions.py",
    "web/tests/browser/test_browser_inventory_grid.py",
    "web/tests/browser/test_browser_lineage.py",
    "web/tests/browser/test_browser_local_map.py",
    "web/tests/browser/test_browser_pointer.py",
    "web/tests/browser/test_browser_services.py",
    "web/tests/browser/test_browser_shell.py",
    "web/tests/browser/test_browser_title_codex.py",
    "web/tests/browser/test_vue_foundation.py",
)


class BrowserTestDataMigrationContractTests(unittest.TestCase):
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
        # gate itself; inside a process-wide universe lazily-registered
        # vocabulary can name unrelated files. What must never regress is a
        # violation whose path belongs to this migration's manifest.
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
        # Manifest-membership check only: every migrated path must remain in
        # the carried seed classification, and the live ledger's seed array
        # must equal the live seed file (the authoritative ratchet against
        # the committed history is the gate's own check_ledger, exercised via
        # check_repo in the violation test above).
        seed = test_data_lint.load_seed(test_data_lint.REPO_ROOT)
        seed_debt = set(seed["seedDebtPaths"])
        for path in MIGRATED_FILES:
            self.assertIn(path, seed_debt)
        self.assertEqual(self.ledger["seedDebtPaths"], seed["seedDebtPaths"])


if __name__ == "__main__":
    unittest.main()
