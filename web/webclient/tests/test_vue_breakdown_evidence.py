"""Evidence bridge: run the breakdown-rendering gates as requirement evidence.

render-equipment-breakdown-webclient (P7) implements and verifies its
contract in the Node/Vue world: the breakdown-rendering Vitest suite
(chip order/names/kind formatting, the all-16 bound, the no-layers
equivalence, the direct-render unknown-enum defense, the verbatim doll
adjustments, the inventory item_key join, the effective-exposure pin, and
the v5-only wire rejection), the breakdown-state showcase stories on the
three frozen-manifest components, and the deterministic component-coverage
gate. ``covers_requirement`` can only attach to a Python ``test_*``
function, so this module executes those gates and asserts they pass.
Following the B3 precedent, the ``@covers_requirement`` annotations for the
two new requirement IDs

- ``webclient-vue-application::the-character-ui-renders-server-breakdown-without-recomputation``
- ``webclient-component-showcase::breakdown-state-stories-cover-the-frozen-manifest-components``

were applied at this change's spec sync, after the delta specs landed in
``openspec/specs/`` and put the IDs into the traceability index.

Test-to-requirement mapping:

- ``test_vitest_breakdown_suite_passes`` and
  ``test_legacy_node_gate_stays_v5_only`` establish the rendering
  requirement (payload-order chips, no recomputation, verbatim adjustments,
  effective exposure, and the v4-rejects-everywhere wire claim).
- ``test_component_coverage_gate_passes_with_breakdown_stories`` and
  ``test_breakdown_stories_are_registered_in_showcase`` establish the
  showcase requirement (the breakdown states ship as stories on the three
  existing manifest components; the required set stays frozen).
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from ._showcase_build import showcase_build_lock
from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "web/webclient-app"
STORYBOOK_OUT = REPO_ROOT / ".storybook-out"

# The exact showcase story registration for the breakdown states: the built
# Storybook index.json entry id for every story this change adds (title
# "<Family>/<Component>", deterministic story names).
BREAKDOWN_STORY_IDS = {
    "data-characterstatusdrawer--breakdown-chips",
    "data-equipmentdoll--adjustment-bearing-slots",
    "world-inventorypanel--joined-adjustment",
}


def run_npm(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["npm", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def run_node(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["node", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class VueBreakdownEvidenceTest(unittest.TestCase):
    """Execute the P7 breakdown gates and assert each one passes."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        # The breakdown stories are registered in the static Storybook
        # build; build it once per process when the checkout has none (CI
        # workspaces only build the app dist). The lock serializes against
        # the B1/B2/B3 evidence classes, which rebuild the same
        # .storybook-out in another parallel worker as their gate evidence.
        with showcase_build_lock():
            if not (STORYBOOK_OUT / "iframe.html").is_file():
                result = run_npm(["run", "build-storybook"], timeout=900)
                assert (
                    result.returncode == 0
                ), "Storybook build failed under breakdown evidence:\n" \
                    + result.stdout + result.stderr

    @covers_requirement(
        "webclient-vue-application::the-character-ui-renders-server-breakdown-without-recomputation"
    )
    def test_vitest_breakdown_suite_passes(self):
        """The breakdown contract renders under Vitest.

        The targeted file is exactly the P7 suite
        (``web/webclient-app/tests/data/breakdown_rendering.test.js``):
        payload-ordered verbatim chips with kind-formatted signed amounts,
        all 16 layers at the bound, no breakdown element for layer-free
        rows, the guarded gauge-max attachment, the verbatim doll
        adjustments, the inventory item_key join with the bag-only and
        empty-string absences, the effective-exposure pin with the stored
        base asserted absent, the direct-render unknown-enum 其他 defense,
        and the store-path v5-accept / v4-reject wire claim.
        """
        result = run_npm(
            ["test", "--", "web/webclient-app/tests/data/breakdown_rendering.test.js"],
            timeout=600,
        )
        self.assertEqual(
            result.returncode,
            0,
            "Vitest breakdown suite failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("passed", result.stdout)

    @covers_requirement(
        "webclient-vue-application::the-character-ui-renders-server-breakdown-without-recomputation"
    )
    def test_legacy_node_gate_stays_v5_only(self):
        """The preserved legacy client gate proves the v5-only acceptance.

        The dependency-free Node gate
        (``web/static/webclient/js/tests/*.test.js``) carries the rewritten
        v5-accept / v4-reject character-validator tests and the totals-only
        v5 character-menu rendering.
        """
        result = run_node(
            [
                "--test",
                "web/static/webclient/js/tests/protocol.test.js",
                "web/static/webclient/js/tests/character_menu.test.js",
            ],
            timeout=300,
        )
        self.assertEqual(
            result.returncode,
            0,
            "legacy Node gate failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("fail 0", result.stdout)

    @covers_requirement(
        "webclient-component-showcase::breakdown-state-stories-cover-the-frozen-manifest-components"
    )
    def test_component_coverage_gate_passes_with_breakdown_stories(self):
        """The frozen manifest is untouched and the showcase stays in lockstep.

        The breakdown states shipped as new STORIES on the three existing
        manifest components (design D6), so the required set is
        byte-unchanged and the deterministic coverage gate still reports
        every required component covered.
        """
        required = json.loads(
            (APP_ROOT / "component-manifest.json").read_text(encoding="utf-8")
        )["required"]
        for key in (
            "Data/CharacterStatusDrawer",
            "Data/EquipmentDoll",
            "World/InventoryPanel",
        ):
            self.assertIn(key, required)
        result = run_node(["scripts/component-coverage.mjs"], timeout=120)
        self.assertEqual(
            result.returncode,
            0,
            "component coverage gate failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn(
            f"component coverage: all {len(required)} required component(s) "
            "have stories",
            result.stdout,
        )

    @covers_requirement(
        "webclient-component-showcase::breakdown-state-stories-cover-the-frozen-manifest-components"
    )
    def test_breakdown_stories_are_registered_in_showcase(self):
        """Every breakdown state has a documented story in the built showcase."""
        with showcase_build_lock():
            self.assertTrue(
                (STORYBOOK_OUT / "index.json").is_file(),
                "missing storybook index.json",
            )
            index = json.loads(
                (STORYBOOK_OUT / "index.json").read_text(encoding="utf-8")
            )
        entries = index.get("entries", {})
        missing = BREAKDOWN_STORY_IDS - set(entries)
        self.assertEqual(
            missing,
            set(),
            "breakdown stories missing from the showcase: "
            + ", ".join(sorted(missing)),
        )
