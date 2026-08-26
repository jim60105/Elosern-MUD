"""Evidence bridge: run the world + services family gates as requirement evidence (B4).

The world + services family contracts of webclient-vue-05-showcase-world are
implemented and verified in the Node/Vue world: the world-family Vitest
suite, the deterministic component-coverage gate extended with the family's
six required components, and the Storybook showcase in which every family
component has documented offline stories. ``covers_requirement`` can only
attach to a Python ``test_*`` function, so this module executes those gates
and asserts they pass. Following the B1/B2/B3 precedent, the
``@covers_requirement`` import and the annotation linking this module to the
new ``webclient-component-showcase`` map/art/services requirement were
applied at this change's archive (the delta spec's requirement synced into
the main spec at archive time makes the requirement ID valid in the
traceability index).

Test-to-requirement mapping (applied at archive):

- ``webclient-component-showcase::the-map-art-and-services-surfaces-render-oob-backed-data-truthfully``:
  ``test_vitest_world_family_suite_passes`` (lattice states + legend + detail
  line + actionable nodes; art truthful placeholder; shop/quest/lore/inventory
  rendered only from the mock services payload),
  ``test_component_coverage_gate_passes_with_world_family`` (the manifest
  extended in lockstep; no full bag or dedicated party panel is present),
  and ``test_world_family_stories_are_registered_in_showcase`` (every family
  story is registered in the built static showcase; the local-imports-only
  guarantee of the new stories is evidenced by B1's
  ``test_story_files_import_only_local_or_bundled_modules``, which walks
  every story file, plus ``test_world_family_stories_make_no_non_local_requests``,
  which scopes that check to the World family's six story files).
"""

from __future__ import annotations

import glob
import json
import re
import subprocess
import unittest
from pathlib import Path

from ._showcase_build import showcase_build_lock
from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "web/webclient-app"
STORYBOOK_OUT = REPO_ROOT / ".storybook-out"

# The world + services family components this change adds to the required
# component manifest (extend, don't restructure — B5 freezes the manifest;
# design D5).
WORLD_FAMILY_KEYS = (
    "World/LocalMap",
    "World/ArtPanel",
    "World/ShopPanel",
    "World/QuestBoard",
    "World/LoreDrawer",
    "World/InventoryPanel",
)

# The exact showcase story registration for the world + services family: the
# built Storybook index.json entry ids for every story exported by this
# change (title "World/<Component>", deterministic story names).
WORLD_FAMILY_STORY_IDS = {
    "world-artpanel--full-payload",
    "world-artpanel--pending",
    "world-artpanel--unavailable",
    "world-inventorypanel--empty-bag",
    "world-inventorypanel--mixed-bag",
    "world-inventorypanel--ceiling-bag",
    "world-inventorypanel--section-absent",
    "world-inventorypanel--unavailable",
    "world-localmap--full-lattice",
    "world-localmap--minimal",
    "world-localmap--unavailable",
    "world-loredrawer--bare",
    "world-loredrawer--full-lore",
    "world-loredrawer--section-unavailable",
    "world-questboard--full-guild",
    "world-questboard--no-guild",
    "world-questboard--section-unavailable",
    "world-shoppanel--full-payload",
    "world-shoppanel--section-absent",
    "world-shoppanel--section-unavailable",
}

# The exact manifest baseline before this change (B1 core, B2 action-dock,
# B3 data families). The four full-overlays keys from B5
# (webclient-vue-06-showcase-overlays) are added at the manifest freeze
# (design D3): after B5 the frozen manifest carries the complete required
# set, so this baseline must extend — not restructure. The H1/H2/H3 HUD
# waves added eleven more keys (HudFrame, SceneBackdrop, FullLogOverlay,
# RestForm, DockTabBar, DockBreadcrumb, SkillDetailPane, CharacterHead,
# VitalsTrack, ConditionChips, ParticipantFrame), which this baseline now
# carries as well.
PREVIOUS_MANIFEST_KEYS = {
    "Core/AppShell",
    "Core/TopBar",
    "Core/ConnectOverlay",
    "Core/NarrativeFeed",
    "Core/UnreadIndicator",
    "Core/CommandDrawer",
    "Core/HudFrame",
    "Core/SceneBackdrop",
    "Core/FullLogOverlay",
    "Core/HudDrawer",
    "Action/ActionDock",
    "Action/DockMenu",
    "Action/DockMenuItem",
    "Action/OptionCard",
    "Action/RestForm",
    "Action/ChoiceCardRow",
    "Action/ChoicePointBlock",
    "Action/DockTabBar",
    "Action/DockBreadcrumb",
    "Action/SkillDetailPane",
    "Data/StatusPanel",
    "Data/CharacterPanel",
    "Data/CharacterHead",
    "Data/VitalsTrack",
    "Data/SkillBook",
    "Data/ConditionChips",
    "Data/ParticipantFrame",
    "Data/EquipmentDoll",
    "Data/CharacterStatusDrawer",
    "Overlays/CreationOverlay",
    "Overlays/HelpOverlay",
    "Overlays/MapOverlay",
    "Overlays/SettingsOverlay",
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


class VueShowcaseWorldEvidenceTest(unittest.TestCase):
    """Execute the B4 world + services family gates and assert each passes."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        # The world family stories are registered in the static Storybook
        # build; build it once per process when the checkout has none (CI
        # workspaces only build the app dist). The lock serializes against
        # the B1/B2/B3 evidence classes, which rebuild the same
        # .storybook-out in another parallel worker as their gate evidence.
        with showcase_build_lock():
            if not (STORYBOOK_OUT / "iframe.html").is_file():
                result = run_npm(["run", "build-storybook"], timeout=900)
                assert (
                    result.returncode == 0
                ), "Storybook build failed under world evidence:\n" \
                    + result.stdout + result.stderr

    @covers_requirement(
        "webclient-component-showcase::the-map-art-and-services-surfaces-render-oob-backed-data-truthfully"
    )
    def test_vitest_world_family_suite_passes(self):
        """Every world + services family SFC renders its contract states under Vitest.

        The ``world`` path filter selects exactly the B4 family suites
        (``web/webclient-app/tests/world/``) — the local-map lattice states
        with legend and detail line plus the actionable adjacent nodes, the
        art 16:9 cover plus truthful placeholder, the shop stock/sellable
        and equipped-only inventory, the guild board/quest-detail board, and
        the services-backed lore drawer — each asserted only from the mock
        payloads (no invented bag or party panel).
        """
        result = run_npm(["test", "--", "world"], timeout=600)
        self.assertEqual(
            result.returncode,
            0,
            "Vitest world family suite failed:\n"
            + result.stdout
            + result.stderr,
        )
        self.assertIn("passed", result.stdout)

    @covers_requirement(
        "webclient-component-showcase::the-map-art-and-services-surfaces-render-oob-backed-data-truthfully"
    )
    def test_component_coverage_gate_passes_with_world_family(self):
        """The manifest carries the world + services family and the showcase stays in lockstep.

        The set equality asserts the extend-don't-restructure contract at
        this change's step: the B1 core, B2 action-dock, and B3 data-family
        keys are preserved and exactly the six world + services family keys
        are added. B5, which freezes the manifest, updates the baseline
        deliberately. The deferred surfaces — a full inventory bag and a
        dedicated party/companion panel (roadmap design doc section 7) are
        asserted absent from the manifest and from the story titles.
        """
        required = json.loads(
            (APP_ROOT / "component-manifest.json").read_text(encoding="utf-8")
        )["required"]
        self.assertEqual(
            set(required) - set(WORLD_FAMILY_KEYS),
            PREVIOUS_MANIFEST_KEYS,
        )
        # No full bag or dedicated party panel in the required set.
        self.assertNotIn("World/Bag", required)
        self.assertNotIn("World/PartyPanel", required)
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
        # The reverse lint in the gate already fails the build when a story
        # title is unlisted; the story-title scan below additionally asserts
        # that no bag/party panel story exists in the app.
        for story_path in sorted(glob.glob(str(APP_ROOT / "stories/**/*.stories.js"))):
            source = Path(story_path).read_text(encoding="utf-8")
            title = re.search(r'title:\s*["\']([^"\']+)["\']', source)
            self.assertNotIn(
                "World/Bag", [title.group(1) if title else None]
            )
            self.assertNotIn(
                "World/PartyPanel", [title.group(1) if title else None]
            )

    @covers_requirement(
        "webclient-component-showcase::the-map-art-and-services-surfaces-render-oob-backed-data-truthfully"
    )
    def test_world_family_stories_are_registered_in_showcase(self):
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
        missing = WORLD_FAMILY_STORY_IDS - set(entries)
        self.assertEqual(
            missing,
            set(),
            "world + services family stories missing from the showcase: "
            + ", ".join(sorted(missing)),
        )
        # Every family story title resolves to the family's six components,
        # so the coverage gate and the showcase agree on the family surface.
        family_titles = {entries[story_id]["title"] for story_id in WORLD_FAMILY_STORY_IDS}
        self.assertEqual(
            family_titles,
            {f"World/{component}" for component in (
                "LocalMap", "ArtPanel", "ShopPanel",
                "QuestBoard", "LoreDrawer", "InventoryPanel",
            )},
        )

    @covers_requirement(
        "webclient-component-showcase::the-map-art-and-services-surfaces-render-oob-backed-data-truthfully"
    )
    def test_world_family_stories_make_no_non_local_requests(self):
        """The World family stories import only local or bundled modules.

        The gate in the roadmap (task 2.2: "no story makes a non-local
        request") is enforced for the whole app by B1's
        ``test_story_files_import_only_local_or_bundled_modules``; this test
        scopes the same scan to the World family's story files so the B4
        evidence stands on its own: every import must be ``vue`` (the locked,
        bundled runtime) or a relative path.
        """
        world_story_files = sorted(
            (APP_ROOT / "stories/World").glob("*.stories.js")
        )
        self.assertEqual(len(world_story_files), len(WORLD_FAMILY_KEYS))
        import_re = re.compile(
            r'(?:^|\n)\s*(?:import\s+(?:[\w${},*\s]+\s+from\s+)?|export\s+[\w{},*\s]+\s+from\s+)["\']([^"\']+)["\']'
        )
        for path in world_story_files:
            source = path.read_text(encoding="utf-8")
            for module in import_re.findall(source):
                self.assertTrue(
                    module.startswith(("./", "../")) or module == "vue",
                    f"{path.name} imports a non-local module: {module}",
                )


if __name__ == "__main__":
    unittest.main()
