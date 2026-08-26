"""Evidence bridge: run the action-dock family gates as requirement evidence (B2).

The action-dock family contract of webclient-vue-03-showcase-action is
implemented and verified in the Node/Vue world: the action-family Vitest
suite, the deterministic component-coverage gate extended with the family's
six required components, and the Storybook showcase in which every family
component is registered as a documented story. ``covers_requirement`` can
only attach to a Python ``test_*`` function, so this module executes those
gates and asserts they pass. Following the B1 precedent, the
``@covers_requirement`` import and annotation linking this module to the new
requirement are applied at this change's archive, once the requirement ID
enters the traceability index with the delta spec synced into the main spec.

Test-to-requirement mapping:

- ``webclient-component-showcase::the-action-dock-family-presents-a-finite-keyboard-and-pointer-actionable-contract``:
  ``test_vitest_action_family_suite_passes`` (the finite framed grid, the
  guidance line, the focused/disabled cells, the preserved ``action-`` /
  ``target-`` keys, the stable ``data-testid`` cells, the exact
  server-authored card shapes with no invented payload, and the
  generating/ready, movable choice-point block are each asserted there),
  ``test_component_coverage_gate_passes_with_action_family``, and
  ``test_action_family_stories_are_registered_in_showcase`` (the offline
  rendering of the showcase stories is additionally evidenced in the browser
  shard by
  ``test_vue_foundation.VueFoundationBrowserTest.test_storybook_stories_render_offline``;
  the local-imports-only guarantee of the new stories is covered by B1's
  ``test_story_files_import_only_local_or_bundled_modules``, which walks
  every story file).
"""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from tools.spec_traceability import covers_requirement

from ._showcase_build import showcase_build_lock

REPO_ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "web/webclient-app"
STORYBOOK_OUT = REPO_ROOT / ".storybook-out"

# The six action-dock family components this change adds to the required
# component manifest (extend, don't restructure — B5 freezes the manifest).
ACTION_FAMILY_KEYS = (
    "Action/ActionDock",
    "Action/DockMenu",
    "Action/DockMenuItem",
    "Action/OptionCard",
    "Action/ChoiceCardRow",
    "Action/ChoicePointBlock",
)

# The exact showcase story registration for the action-dock family: the
# built Storybook index.json entry id for every story file/story exported by
# this change (title "Action/<Component>", deterministic story names).
ACTION_FAMILY_STORY_IDS = {
    "action-actiondock--degraded-empty-suggestions",
    "action-actiondock--exploration-dock",
    "action-actiondock--generating-suggestions",
    "action-actiondock--unavailable-suggestions",
    "action-choicecardrow--ready-row",
    "action-choicepointblock--generating",
    "action-choicepointblock--ready",
    "action-choicepointblock--stream-end",
    "action-dockmenu--exploration-frame",
    "action-dockmenu--fixed-grid-frame",
    "action-dockmenu--target-frame",
    "action-dockmenuitem--default",
    "action-dockmenuitem--disabled",
    "action-dockmenuitem--focused",
    "action-optioncard--freeform",
    "action-optioncard--known",
    "action-optioncard--known-with-hint",
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


class VueShowcaseActionEvidenceTest(unittest.TestCase):
    """Execute the B2 action-dock family gates and assert each one passes."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        # The action family stories are registered in the static Storybook
        # build; build it once per process when the checkout has none (CI
        # workspaces only build the app dist). The lock serializes against
        # the B1 evidence class, which rebuilds the same .storybook-out in
        # another parallel worker as its gate evidence.
        with showcase_build_lock():
            if not (STORYBOOK_OUT / "iframe.html").is_file():
                result = run_npm(["run", "build-storybook"], timeout=900)
                assert (
                    result.returncode == 0
                ), "Storybook build failed under action evidence:\n" \
                    + result.stdout + result.stderr

    @covers_requirement(
        "webclient-component-showcase::the-action-dock-family-presents-a-finite-keyboard-and-pointer-actionable-contract"
    )
    def test_vitest_action_family_suite_passes(self):
        """Every action-dock SFC renders its contract states under Vitest.

        The ``action`` path filter selects exactly the B2 family suites
        (``web/webclient-app/tests/action/``) — the finite framed grid, the
        guidance line and preserved shortcut legend, the focused/disabled
        cells, the preserved ``action-``/``target-`` item keys and stable
        ``data-testid`` cells, the exact server-authored card shapes (no
        invented action, payload, or freeform speech), the generating/ready
        states, and the movable, in-place-replacing choice-point block.
        """
        result = run_npm(["test", "--", "action"], timeout=600)
        self.assertEqual(
            result.returncode,
            0,
            "Vitest action-dock family suite failed:\n"
            + result.stdout
            + result.stderr,
        )
        self.assertIn("passed", result.stdout)

    @covers_requirement(
        "webclient-component-showcase::the-action-dock-family-presents-a-finite-keyboard-and-pointer-actionable-contract"
    )
    def test_component_coverage_gate_passes_with_action_family(self):
        """The manifest is the exact B3 surface and the showcase stays in lockstep.

        The set equality is the baseline for the "extend, don't restructure"
        contract: the B1 core family is preserved, the six action-dock keys
        from B2 are intact, the three data-family keys from B3
        (webclient-vue-04-showcase-data, manifest design D5) are added, the
        six world-family keys from B4 (webclient-vue-05-showcase-world) are
        added, and the four full-overlays keys from B5
        (webclient-vue-06-showcase-overlays) are added at the manifest
        freeze (design D3).
        """
        required = json.loads(
            (APP_ROOT / "component-manifest.json").read_text(encoding="utf-8")
        )["required"]
        self.assertEqual(
            set(required),
            {
                "Core/AppShell", "Core/TopBar", "Core/ConnectOverlay",
                "Core/NarrativeFeed", "Core/UnreadIndicator",
                "Core/CommandLine", "Core/QuickWordChips", "Core/HudFrame",
                "Core/SceneBackdrop",
                "Core/FullLogOverlay", "Core/HudDrawer",
                *ACTION_FAMILY_KEYS,
                "Action/RestForm", "Action/DockTabBar", "Action/DockBreadcrumb",
                "Action/SkillDetailPane",
                "Data/StatusPanel", "Data/CharacterPanel",
                "Data/CharacterHead", "Data/VitalsTrack", "Data/SkillBook",
                "Data/ConditionChips", "Data/ParticipantFrame",
                "Data/EquipmentDoll", "Data/CharacterStatusDrawer",
                "World/LocalMap", "World/ArtPanel", "World/ShopPanel",
                "World/QuestBoard", "World/LoreDrawer", "World/InventoryPanel",
                "Overlays/CreationOverlay", "Overlays/HelpOverlay",
                "Overlays/MapOverlay", "Overlays/SettingsOverlay",
                "Overlays/OverlayHost",
            },
        )
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
        "webclient-component-showcase::the-action-dock-family-presents-a-finite-keyboard-and-pointer-actionable-contract"
    )
    def test_action_family_stories_are_registered_in_showcase(self):
        """Every family component has a documented story in the built showcase."""
        with showcase_build_lock():
            self.assertTrue(
                (STORYBOOK_OUT / "index.json").is_file(),
                "missing storybook index.json",
            )
            index = json.loads(
                (STORYBOOK_OUT / "index.json").read_text(encoding="utf-8")
            )
        entries = index.get("entries", {})
        missing = ACTION_FAMILY_STORY_IDS - set(entries)
        self.assertEqual(
            missing,
            set(),
            "action-dock family stories missing from the showcase: " + ", ".join(sorted(missing)),
        )
        # Every family story title resolves to the family's six components,
        # so the coverage gate and the showcase agree on the family surface.
        family_titles = {entries[story_id]["title"] for story_id in ACTION_FAMILY_STORY_IDS}
        self.assertEqual(
            family_titles,
            {f"Action/{component}" for component in (
                "ActionDock", "DockMenu", "DockMenuItem",
                "OptionCard", "ChoiceCardRow", "ChoicePointBlock",
            )},
        )
