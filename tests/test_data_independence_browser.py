"""Repository contract: the browser-test migration off real data stays closed.

The migrate-browser-tests-off-real-data change removed every ledger DEBT
exemption for the nineteen Playwright-suite files it migrated (the harness
modules ``browser_helpers.py``/``browser_settings.py``/``seed.py`` plus the
sixteen ``test_browser_*``/``test_vue_foundation`` journey files). This
contract re-derives the gate over exactly those files: none may carry a
ledger DEBT or CONTRACT exemption, and all must hold zero lint findings —
so a future edit that reintroduces a shipped identifier cannot silently
re-register debt. Every manifest file resolves game data through the
support package ``web/browser_support/browser_fixtures_data/`` (boot-mode
``SHIPPED_*``/``SYNTH_*`` vocabularies and journey-value helpers), the
synthetic kit ``world/tests/synthetic_data.py``, or values read from the
committed panel snapshots at runtime; the support module lives outside the
scanned tree, so it can name shipped vocabulary while every scanned file
stays literal-free.

The harness module ``seed.py`` was later split into the
``web/tests/browser/seed/`` package of domain slices (the
``web/browser_support/browser_fixtures_data`` package precedent applies
here): its migration-era manifest path stays in the frozen ledger
classification, and the live scans below resolve it through the package.
"""

from pathlib import Path
import unittest

from tools import test_data_lint
from tools.spec_traceability import covers_requirement
from ._data_independence_base import DataIndependenceContractMixin

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

#: The migration manifest's exact size. The scans below enumerate the live
#: directory rather than trusting this tuple, so shrinking the tuple cannot
#: shrink the contract -- and the manifest cannot silently drift from the
#: 19 files this change migrated.
MANIFEST_SIZE = 19


class BrowserTestDataMigrationContractTests(DataIndependenceContractMixin, unittest.TestCase):

    def test_manifest_covers_the_migrated_files(self):
        # The manifest is an exact, immutable list: it may not shrink (an
        # entry quietly dropped) or duplicate while the size claim holds.
        # The scans below never trust the tuple -- they enumerate the live
        # directory -- so a migrated file can never be exempted by editing
        # this test.
        self.assertEqual(len(MIGRATED_FILES), MANIFEST_SIZE)
        self.assertEqual(len(set(MIGRATED_FILES)), MANIFEST_SIZE)
        area = self._area_with_seed_package()
        self.assertEqual(
            [p for p in MIGRATED_FILES if p not in area],
            [],
            "the manifest names a module the browser area no longer has",
        )

    @covers_requirement(
        "test-data-independence::"
        "managed-browser-tests-resolve-game-data-through-"
        "synthetic-fixtures"
    )
    def test_migrated_files_hold_no_ledger_exemption(self):
        self.assert_no_ledger_exemption(self._browser_area())

    @covers_requirement(
        "test-data-independence::"
        "managed-browser-tests-resolve-game-data-through-"
        "synthetic-fixtures"
    )
    def test_migrated_files_carry_zero_findings(self):
        self.assert_zero_findings(self._browser_area(), check_exists=False)

    def _browser_area(self):
        """Every Python module in the migrated browser directory.

        The scan is recursive so every source file of the ``seed/``
        package (the former single ``seed.py``) joins the scanned area.
        """
        return sorted(
            str(path.relative_to(test_data_lint.REPO_ROOT))
            for path in (test_data_lint.REPO_ROOT / "web/tests/browser").rglob("*.py")
        )

    def _area_with_seed_package(self):
        """The live area plus retired single-module manifest paths, each
        standing in for the package or flat sibling family it became (the
        frozen ledger classification keeps naming the retired path -- the
        seed.py -> seed/ precedent applies to the six browser journey files
        split into ``test_browser_<area>_<domain>.py`` sibling families)."""
        area = set(self._browser_area())
        if "web/tests/browser/seed/__init__.py" in area:
            area.add("web/tests/browser/seed.py")
        live_names = {p.name for p in (
            test_data_lint.REPO_ROOT / "web/tests/browser").glob("*.py")}
        for stem in (
            "test_browser_combat",
            "test_browser_contextual_hud",
            "test_browser_creation",
            "test_browser_exploration",
            "test_browser_local_map",
            "test_browser_shell",
        ):
            retired = f"web/tests/browser/{stem}.py"
            if retired not in live_names and any(
                name.startswith(f"{stem}_") for name in live_names
            ):
                area.add(retired)
        return area

    def test_no_violation_naming_a_manifest_file(self):
        self.assert_no_violation_naming_manifest(MIGRATED_FILES)

    def test_freeze_ledger_seed_array_untouched_by_the_migration(self):
        self.assert_freeze_seed_untouched(MIGRATED_FILES)


if __name__ == "__main__":
    unittest.main()
