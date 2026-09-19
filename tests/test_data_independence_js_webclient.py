"""Repository contract: the webclient JS-app test migration stays closed.

The migrate-webclient-js-app-tests-off-real-data change removed every ledger
DEBT exemption for the twenty-two JavaScript files it migrated (nine
``web/static/webclient/js/tests`` Node-gate files plus thirteen
``web/webclient-app/tests`` Vitest files). This contract re-derives the gate
over exactly those files: none may carry a ledger DEBT or CONTRACT exemption,
and all must hold zero lint findings — so a future edit that reintroduces a
shipped identifier cannot silently re-register debt. Every manifest file
resolves shipped vocabulary in its SOURCE through the JS synthetic mirror
(``support/synthetic-data``), file-local synthetic rows, model-owned wire
constants, or values read from the committed payload fixture objects at
runtime — the gate scans source text only, so a fixture module keeping its
shipped rows cannot reintroduce a literal into a manifest file, so the whole
manifest stays debt-free and finding-free.
"""

from pathlib import Path
import unittest

from tools import test_data_lint
from tools.spec_traceability import covers_requirement
from ._data_independence_base import DataIndependenceContractMixin

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


class WebclientJsTestDataMigrationContractTests(DataIndependenceContractMixin, unittest.TestCase):

    @covers_requirement(
        "test-data-independence::"
        "webclient-javascript-tests-resolve-game-data-through-"
        "synthetic-fixtures"
    )
    def test_migrated_files_hold_no_ledger_exemption(self):
        self.assert_no_ledger_exemption(MIGRATED_FILES)

    @covers_requirement(
        "test-data-independence::"
        "webclient-javascript-tests-resolve-game-data-through-"
        "synthetic-fixtures"
    )
    def test_migrated_files_carry_zero_findings(self):
        self.assert_zero_findings(MIGRATED_FILES)

    def test_no_violation_naming_a_manifest_file(self):
        self.assert_no_violation_naming_manifest(MIGRATED_FILES)

    def test_freeze_ledger_seed_array_untouched_by_the_migration(self):
        self.assert_freeze_seed_untouched(MIGRATED_FILES)


if __name__ == "__main__":
    unittest.main()
