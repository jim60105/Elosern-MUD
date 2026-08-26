"""Evidence bridge: run the data-family gates as requirement evidence (B3).

The data-family contract of webclient-vue-04-showcase-data is implemented
and verified in the Node/Vue world: the data-family Vitest suite, the
deterministic component-coverage gate extended with the family's three
required components, and the Storybook showcase in which every family
component is registered as a documented story. ``covers_requirement`` can
only attach to a Python ``test_*`` function, so this module executes those
gates and asserts they pass. Following the B1/B2 precedent, the
``@covers_requirement`` import and annotation linking this module to the
new ``webclient-component-showcase`` status/character/skill requirement
were applied at this change's archive, after the delta spec synced into the
main spec put the requirement ID into the traceability index.

Test-to-requirement mapping (applied at archive):

- ``webclient-component-showcase::the-status-character-and-skill-surfaces-present-truthful-non-color-only-state``:
  ``test_vitest_data_family_suite_passes`` (the gauges/counters/statics/
  wallet paired with symbols and numeric values, the conditions with their
  derived modifiers, the true-vs-displayed disguise contrast, the skill
  book's tabs/search/detail cells rendered only when the payload provides
  the field, and the asserted-absent intimate/adult block are each asserted
  there), ``test_component_coverage_gate_passes_with_data_family``, and
  ``test_data_family_stories_are_registered_in_showcase`` (the offline
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

from ._showcase_build import showcase_build_lock
from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "web/webclient-app"
STORYBOOK_OUT = REPO_ROOT / ".storybook-out"

# The data-family components this change adds to the required component
# manifest (extend, don't restructure — B5 freezes the manifest; design D5).
DATA_FAMILY_KEYS = (
    "Data/StatusPanel",
    "Data/SkillBook",
)

# The exact showcase story registration for the data family: the built
# Storybook index.json entry id for every story exported by this change
# (title "Data/<Component>", deterministic story names).
DATA_FAMILY_STORY_IDS = {
    "data-skillbook--active-tab",
    "data-skillbook--passive-tab",
    "data-skillbook--search-filtered",
    "data-statuspanel--combat-rounds",
    "data-statuspanel--full-payload",
    "data-statuspanel--minimal",
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


class VueShowcaseDataEvidenceTest(unittest.TestCase):
    """Execute the B3 data-family gates and assert each one passes."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        # The data family stories are registered in the static Storybook
        # build; build it once per process when the checkout has none (CI
        # workspaces only build the app dist). The lock serializes against
        # the B1/B2 evidence classes, which rebuild the same .storybook-out
        # in another parallel worker as their gate evidence.
        with showcase_build_lock():
            if not (STORYBOOK_OUT / "iframe.html").is_file():
                result = run_npm(["run", "build-storybook"], timeout=900)
                assert (
                    result.returncode == 0
                ), "Storybook build failed under data evidence:\n" \
                    + result.stdout + result.stderr

    @covers_requirement(
        "webclient-component-showcase::the-status-character-and-skill-surfaces-present-truthful-non-color-only-state"
    )
    def test_vitest_data_family_suite_passes(self):
        """Every data-family SFC renders its contract states under Vitest.

        The ``data`` path filter selects exactly the B3 family suites
        (``web/webclient-app/tests/data/``) — the not-color-only gauges and
        conditions with derived modifiers, the counters/statics/wallet from
        the character payload, the true-vs-displayed disguise contrast with
        the true trait rows never substituted, the skill book's tabs,
        search, payload ordering, and detail cells rendered only when the
        payload provides the field, and the asserted-absent intimate/adult
        block.
        """
        result = run_npm(["test", "--", "data"], timeout=600)
        self.assertEqual(
            result.returncode,
            0,
            "Vitest data family suite failed:\n"
            + result.stdout
            + result.stderr,
        )
        self.assertIn("passed", result.stdout)

    @covers_requirement(
        "webclient-component-showcase::the-status-character-and-skill-surfaces-present-truthful-non-color-only-state"
    )
    def test_component_coverage_gate_passes_with_data_family(self):
        """The manifest carries the data family and the showcase stays in lockstep.

        The set equality asserts the extend-don't-restructure contract at
        this change's step: the B1 core and B2 action-dock keys are
        preserved and exactly the three data-family keys are added; the six
        world-family keys from B4 (webclient-vue-05-showcase-world) joined
        the baseline at its merge, and the four full-overlays keys from B5
        (webclient-vue-06-showcase-overlays) joined the baseline at its
        manifest freeze (design D3).
        """
        required = json.loads(
            (APP_ROOT / "component-manifest.json").read_text(encoding="utf-8")
        )["required"]
        self.assertIn("Data/StatusPanel", required)
        self.assertIn("Data/SkillBook", required)
        self.assertEqual(
            set(required) - set(DATA_FAMILY_KEYS),
            {
                "Core/AppShell", "Core/TopBar", "Core/ConnectOverlay",
                "Core/NarrativeFeed", "Core/UnreadIndicator",
                "Core/CommandLine", "Core/QuickWordChips", "Core/HudFrame",
                "Core/SceneBackdrop",
                "Core/FullLogOverlay", "Core/HudDrawer",
                "Action/ActionDock", "Action/DockMenu", "Action/DockMenuItem",
                "Action/OptionCard", "Action/RestForm", "Action/ChoiceCardRow",
                "Action/ChoicePointBlock", "Action/DockTabBar",
                "Action/DockBreadcrumb", "Action/SkillDetailPane",
                "Data/CharacterHead", "Data/VitalsTrack", "Data/ConditionChips",
                "Data/ParticipantFrame", "Data/EquipmentDoll", "Data/CharacterStatusDrawer",
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
        "webclient-component-showcase::the-status-character-and-skill-surfaces-present-truthful-non-color-only-state"
    )
    def test_data_family_stories_are_registered_in_showcase(self):
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
        missing = DATA_FAMILY_STORY_IDS - set(entries)
        self.assertEqual(
            missing,
            set(),
            "data family stories missing from the showcase: " + ", ".join(sorted(missing)),
        )
        # Every family story title resolves to the family's components,
        # so the coverage gate and the showcase agree on the family surface.
        family_titles = {entries[story_id]["title"] for story_id in DATA_FAMILY_STORY_IDS}
        self.assertEqual(
            family_titles,
            {f"Data/{component}" for component in (
                "StatusPanel", "SkillBook",
            )},
        )
