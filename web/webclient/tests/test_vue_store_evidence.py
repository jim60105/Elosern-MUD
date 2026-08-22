"""Evidence bridge: run the C1 store gates as requirement evidence (C1).

The reactive-store contract of webclient-vue-07-wire-store is implemented
and verified in the Node/Vue world: the store Vitest suite (the single-writer
commit, the lock semantics, and the focus slices) and the Vite build that
bundles the store into the stable offline dist. ``covers_requirement`` can
only attach to a Python ``test_*`` function, so this module executes those
gates and asserts they pass.

Following the B1/B2 precedent, the ``@covers_requirement`` import and the
annotation linking this module to the C1 requirement (
``webclient-vue-application::the-vue-app-binds-the-preserved-strict-dom-independent-logic-to-a-reactive-store``)
are applied at this change's archive, once the requirement ID enters the
traceability index when the delta spec syncs into the main spec.

Test-to-requirement mapping:

- ``webclient-vue-application::the-vue-app-binds-the-preserved-strict-dom-independent-logic-to-a-reactive-store``:
  ``test_store_suite_passes`` (the commit atomicity, the stale-epoch /
  stale-revision rejection, the data-backed scope, and the focus / dispatch
  slices are asserted in the store Vitest suites under
  ``web/webclient-app/tests/store/``) and ``test_app_dist_entries_still_exist``
  (the built bundle keeps serving the stable offline entries).
"""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DIST_ROOT = REPO_ROOT / "web/static/webclient/app/dist"


def run_npm(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["npm", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class VueStoreEvidenceTest(unittest.TestCase):
    """Execute the C1 store gates and assert each gate passes."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        result = run_npm(["run", "build"], timeout=600)
        assert (
            result.returncode == 0
        ), "vite build failed under C1 evidence:\n" + result.stdout + result.stderr

    def test_store_suite_passes(self):
        """The C1 store Vitest suites (store/*) pass."""
        result = run_npm(["test", "--", "store"], timeout=600)
        self.assertEqual(
            result.returncode,
            0,
            "Vitest store suite failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("passed", result.stdout)

    def test_app_dist_entries_still_exist(self):
        """The C1 store bundles into the same stable offline dist entries."""
        for entry in ("index.js", "index.css"):
            path = DIST_ROOT / entry
            self.assertTrue(path.is_file(), f"missing stable dist entry {path}")
            self.assertGreater(path.stat().st_size, 100, f"{path} looks empty")


if __name__ == "__main__":
    unittest.main()
