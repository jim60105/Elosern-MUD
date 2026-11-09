"""Evidence bridge: run the Vitest suites of the handbook's shared parts.

handbook-primitives adds the grouped roving-focus ``TileWall`` and the
``DetailFooter`` that the quest detail now renders its pinned footer through.
Their behavior is implemented and verified in the Vue layer, and
``covers_requirement`` can only attach to a Python ``test_*`` function, so
this module executes the relevant Vitest component files and asserts every
test passes. The requirement annotations were applied at the change's archive,
once its delta requirements were synced into the main spec.
"""

from pathlib import Path
import subprocess
import unittest

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[3]
TESTS_DIR = REPO_ROOT / "web/webclient-app/tests"


def _run_vitest(*test_files):
    """Run the named Vitest component files and return the finished process."""
    args = [str(REPO_ROOT / p) for p in test_files]
    return subprocess.run(
        ["npx", "--no-install", "vitest", "run", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )


def _assert_vitest_passes(result, label):
    assert result.returncode == 0, (
        f"{label} Vitest suite failed:\n{result.stdout}\n{result.stderr}"
    )
    assert "pass" in result.stdout, f"{label}: expected a passing suite summary"


class VueHandbookEvidenceTest(unittest.TestCase):
    @covers_requirement(
        "webclient-window-primitives::tilewall-is-a-grouped-roving-focus-listbox"
    )
    def test_tile_wall_roving_focus(self):
        # One tab stop (the selected item, else the first); arrow keys, Home
        # and End move focus in reading order across groups without
        # selecting; Enter, Space and click select once; a non-selectable
        # item stays focusable, carries aria-disabled and never selects.
        _assert_vitest_passes(
            _run_vitest(TESTS_DIR / "handbook" / "tile_wall.test.js"),
            "tile wall roving focus",
        )

    @covers_requirement(
        "webclient-window-primitives::detailfooter-renders-descriptor-buttons-and-a-committed-reason"
    )
    def test_detail_footer_contract(self):
        # A disabled button stays focusable with aria-disabled and emits
        # nothing, a toggle keeps native disabled, an enabled button emits
        # press with its key, and the quest detail renders its footer through
        # DetailFooter with unchanged testids, focus moves and actions.
        _assert_vitest_passes(
            _run_vitest(
                TESTS_DIR / "components" / "detail_footer.test.js",
                TESTS_DIR / "world" / "quest_detail.test.js",
            ),
            "detail footer contract",
        )


if __name__ == "__main__":
    unittest.main()
