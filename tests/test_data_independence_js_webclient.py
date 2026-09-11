"""Repository contract: the webclient JS-app test migration stays closed.

The migrate-webclient-js-app-tests-off-real-data change removed every ledger
DEBT exemption for the twenty-two JavaScript files it migrated (nine
``web/static/webclient/js/tests`` Node-gate files plus thirteen
``web/webclient-app/tests`` Vitest files). This contract re-derives the gate
over exactly those files: none may carry a ledger DEBT or CONTRACT exemption,
and all must hold zero lint findings — so a future edit that reintroduces a
shipped identifier cannot silently re-register debt. Every manifest file
resolves shipped vocabulary through the JS synthetic mirror
(``support/synthetic-data``), file-local synthetic rows, model-owned wire
constants, or values derived from the committed payload fixtures, so the whole
manifest stays debt-free and finding-free.
"""

from pathlib import Path
import unittest

from tools import test_data_lint

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The migrated modules; none may carry a ledger exemption ever again.
MIGRATED_FILES = (
    "web/static/webclient/js/tests/art_panel.test.js",
    "web/static/webclient/js/tests/character_menu.test.js",
    "web/static/webclient/js/tests/combat_menu.test.js",
    "web/static/webclient/js/tests/command_echo.test.js",
    "web/static/webclient/js/tests/creation_menu.test.js",
    "web/static/webclient/js/tests/exploration_menu.test.js",
    "web/static/webclient/js/tests/hud_dock_menus.test.js",
    "web/static/webclient/js/tests/protocol.test.js",
    "web/static/webclient/js/tests/service_menu.test.js",
    "web/webclient-app/tests/data/breakdown_rendering.test.js",
    "web/webclient-app/tests/data/equipment_doll.test.js",
    "web/webclient-app/tests/data/skill_book.test.js",
    "web/webclient-app/tests/frame-resolvers.test.js",
    "web/webclient-app/tests/overlays/creation_overlay.test.js",
    "web/webclient-app/tests/overlays/lineage_panel.test.js",
    "web/webclient-app/tests/overlays/title_codex_panel.test.js",
    "web/webclient-app/tests/preserved_contract.test.js",
    "web/webclient-app/tests/store/command_echo_surfaces.test.js",
    "web/webclient-app/tests/store/declarative_surfaces.test.js",
    "web/webclient-app/tests/store/store_dispatch_focus.test.js",
    "web/webclient-app/tests/world/inventory_panel.test.js",
    "web/webclient-app/tests/world/item_icons.test.js",
)


class WebclientJsTestDataMigrationContractTests(unittest.TestCase):
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
