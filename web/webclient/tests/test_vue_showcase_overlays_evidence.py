"""Evidence bridge: run the full-overlays family gates as requirement evidence (B5).

The full-overlays contracts of webclient-vue-06-showcase-overlays are
implemented and verified in the Node/Vue world: the overlays-family Vitest
suite (`npm test -- overlays` — the `web/webclient-app/tests/overlays/`
directory), the component-coverage gate executing under the **frozen**
required-component manifest, and the Storybook showcase in which every
overlays family component has documented offline stories. ``covers_requirement``
can only attach to a Python ``test_*`` function, so this module executes
those gates and asserts they pass. Following the B1/B2/B3/B4 precedent,
the ``@covers_requirement`` import and the annotation linking this module to
the new ``webclient-component-showcase`` full-overlays + deferred-absent +
frozen-manifest requirement are applied at this change's archive (syncing the
delta spec's requirement into the main spec makes the requirement ID valid in
the traceability index).

Test-to-requirement mapping (applied at archive):

- ``webclient-component-showcase::the-full-overlays-are-complete-the-deferred-surfaces-are-absent-and-the-manifest-is-frozen``:
  ``test_vitest_overlays_family_suite_passes`` (every overlays SFC: settings
  `options.*` emission, creation wizard with the both-fields adult gate,
  map overlay reusing B4's LocalMap and the static help overlay,
  ``test_component_coverage_gate_enforces_frozen_manifest`` (the
  frozen manifest plus the gate's complete-set enforcement, including the
  deferred-absent assertions), ``test_overlays_family_stories_are_registered_in_showcase``
  (every overlays family story registered in the built static showcase), and
  ``test_overlays_family_stories_make_no_non_local_requests`` (the
  local-imports-only guarantee scoped to the Overlays family's story files).
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

# The full-overlays family components this change adds to the required
# component manifest (B5 extends it to the complete set and then freezes
# it; design D3).
OVERLAYS_FAMILY_KEYS = (
    "Overlays/MapOverlay",
    "Overlays/SettingsOverlay",
    "Overlays/HelpOverlay",
    "Overlays/CreationOverlay",
    "Overlays/OverlayHost",
)

# The exact showcase story registration for the full overlays family: the
# built Storybook index.json entry ids for every story exported by this
# change (title "Overlays/<Component>", deterministic story names).
OVERLAYS_STORY_IDS = {
    "overlays-mapoverlay--full-lattice",
    "overlays-mapoverlay--minimal",
    "overlays-mapoverlay--unavailable",
    "overlays-settingsoverlay--default",
    "overlays-settingsoverlay--reduced-motion-on",
    "overlays-settingsoverlay--html-narrative",
    "overlays-settingsoverlay--colorblind",
    "overlays-helpoverlay--default",
    "overlays-creationoverlay--default",
    "overlays-creationoverlay--preset-draft",
    "overlays-creationoverlay--custom-draft",
    "overlays-creationoverlay--custom-sex-roll",
    "overlays-creationoverlay--proposal",
    "overlays-creationoverlay--unavailable",
}

# The deferred surfaces (roadmap §7): no dedicated Party panel, no
# intimate/adult status collapsible, no full inventory bag, no event-log
# Toasts surface. These patterns must not appear in the required set or in
# any registered story title once the manifest is frozen.
# Whole-word (word-boundary) matching: a bare substring would false-positive
# on legitimate names (e.g. "Bag" inside "Baggage"), so the deferred check must
# match the complete token and let future legitimate components through.
DEFERRED_TITLE_PATTERNS = (
    re.compile(r"\bParty\b", re.IGNORECASE),
    re.compile(r"\bIntimate\b", re.IGNORECASE),
    re.compile(r"\bBag\b", re.IGNORECASE),
    re.compile(r"\bEventLog\b", re.IGNORECASE),
    re.compile(r"\bToasts?\b", re.IGNORECASE),
)

# The required-set baseline with the overlays family keys removed: the B1
# core, B2 action-dock, B3 data, and B4 world + services keys, plus the
# H1–H3 HUD wave keys (HudFrame, SceneBackdrop, FullLogOverlay, RestForm,
# DockTabBar, DockBreadcrumb, SkillDetailPane, CharacterHead, VitalsTrack,
# ConditionChips, ParticipantFrame) and the `World/MapLattice` key the
# improve-webclient-map-overlay-scale change added to the frozen set. The
# Feedback/ToastQueue key from the add-action-feedback-toasts change joins
# it at the manifest's refreeze at 42.
PREVIOUS_MANIFEST_KEYS = {
    "Core/AppShell",
    "Core/TopBar",
    "Core/ConnectOverlay",
    "Core/NarrativeFeed",
    "Core/UnreadIndicator",
    "Core/CommandLine",
    "Core/QuickWordChips",
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
    "Data/CharacterHead",
    "Data/VitalsTrack",
    "Data/SkillBook",
    "Data/ConditionChips",
    "Data/ParticipantFrame",
    "Data/EquipmentDoll",
    "Data/CharacterStatusDrawer",
    "World/LocalMap",
    "World/ArtPanel",
    "World/ShopPanel",
    "World/QuestBoard",
    "World/LoreDrawer",
    "World/InventoryPanel",
    "World/MapLattice",
    # The client-local action-feedback toast queue joined the frozen set
    # when add-action-feedback-toasts refroze the manifest at 42.
    "Feedback/ToastQueue",
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


class VueShowcaseOverlaysEvidenceTest(unittest.TestCase):
    """Execute the B5 full-overlays family gates and assert each passes."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        # The overlays family stories are registered in the static Storybook
        # build; build it once per process when the checkout has none (CI
        # workspaces only build the app dist). The lock serializes against the
        # B1/B2/B3/B4 evidence classes, which rebuild the same .storybook-out
        # in other parallel workers as their gate evidence.
        with showcase_build_lock():
            if not (STORYBOOK_OUT / "iframe.html").is_file():
                result = run_npm(["run", "build-storybook"], timeout=900)
                assert (
                    result.returncode == 0
                ), "Storybook build failed under overlays evidence:\n" \
                    + result.stdout + result.stderr

    @covers_requirement(
        "webclient-component-showcase::the-full-overlays-are-complete-the-deferred-surfaces-are-absent-and-the-manifest-is-frozen"
    )
    def test_vitest_overlays_family_suite_passes(self):
        """Every overlays family SFC renders its contract states under Vitest.

        The ``overlays`` path filter selects exactly the B5 family suites
        (``web/webclient-app/tests/overlays/``): the settings overlay's
        `options.*` envelopes and reduced-motion token reflection, the
        creation wizard's presets/custom/concept sub-states with the
        both-fields adult gate and `creation.*` intents, the map overlay
        reusing B4's LocalMap (lattice states, legend, detail line,
        actionable nodes), the help overlay's static control reference, and
        the deferred-absent / frozen-manifest contract test in the same
        directory — each asserted only from the mock OOB payloads (no
        invented data).
        """
        result = run_npm(["test", "--", "overlays"], timeout=600)
        # A zero exit code is sufficient evidence: Vitest exits non-zero when
        # the `overlays` filter matches no test files or any test fails, so no
        # separate human-readable "passed" string is asserted (the summary
        # format is an implementation detail of the Vitest reporter).
        self.assertEqual(
            result.returncode,
            0,
            "Vitest overlays family suite failed:\n"
            + result.stdout
            + result.stderr,
        )

    @covers_requirement(
        "webclient-component-showcase::the-full-overlays-are-complete-the-deferred-surfaces-are-absent-and-the-manifest-is-frozen"
    )
    def test_component_coverage_gate_enforces_frozen_manifest(self):
        """The manifest is frozen at the complete set and the gate enforces it.

        The set equality asserts the B5 extension keeps B1-B4's keys and adds
        exactly the four full overlays (design D3: freeze, don't restructure).
        The gate now reads the manifest's ``frozen`` flag: because B5 set it
        true, the gate reports it is "enforcing the frozen manifest (complete
        required set)". The deferred surfaces (roadmap §7) are asserted
        absent from the manifest and from the story titles (design D2).
        """
        manifest = json.loads(
            (APP_ROOT / "component-manifest.json").read_text(encoding="utf-8")
        )
        required = manifest["required"]
        self.assertTrue(manifest.get("frozen") is True, "manifest not frozen")
        self.assertEqual(
            set(required) - set(OVERLAYS_FAMILY_KEYS),
            PREVIOUS_MANIFEST_KEYS,
        )
        # No deferred surface sneaks into the frozen required set.
        for title in required:
            for pattern in DEFERRED_TITLE_PATTERNS:
                self.assertFalse(
                    pattern.search(title),
                    f"required component {title} looks like a deferred surface",
                )
        result = run_node(["scripts/component-coverage.mjs"], timeout=120)
        self.assertEqual(
            result.returncode,
            0,
            "component coverage gate failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn(
            f"component coverage: all {len(required)} required component(s) "
            "have stories and every one of the "
            f"{len(required)} registered story title(s) is listed",
            result.stdout,
        )
        self.assertIn("enforcing the frozen manifest", result.stdout)

    @covers_requirement(
        "webclient-component-showcase::the-full-overlays-are-complete-the-deferred-surfaces-are-absent-and-the-manifest-is-frozen"
    )
    def test_overlays_family_stories_are_registered_in_showcase(self):
        """Every overlays family component has a documented story in the built showcase."""
        with showcase_build_lock():
            self.assertTrue(
                (STORYBOOK_OUT / "index.json").is_file(),
                "missing storybook index.json",
            )
            index = json.loads(
                (STORYBOOK_OUT / "index.json").read_text(encoding="utf-8")
            )
        entries = index.get("entries", {})
        missing = OVERLAYS_STORY_IDS - set(entries)
        self.assertEqual(
            missing,
            set(),
            "overlays family stories missing from the showcase: "
            + ", ".join(sorted(missing)),
        )
        # Every family story title resolves to the family's four components,
        # so the coverage gate and the showcase agree on the family surface.
        family_titles = {entries[story_id]["title"] for story_id in OVERLAYS_STORY_IDS}
        self.assertEqual(
            family_titles,
            {f"Overlays/{component}" for component in (
                "MapOverlay", "SettingsOverlay", "HelpOverlay", "CreationOverlay",
            )},
        )

    @covers_requirement(
        "webclient-component-showcase::the-full-overlays-are-complete-the-deferred-surfaces-are-absent-and-the-manifest-is-frozen"
    )
    def test_overlays_family_stories_make_no_non_local_requests(self):
        """The Overlays family stories import only local or bundled modules.

        The roadmap gate (task 2.3: "no story makes a non-local request") is
        enforced app-wide by B1's ``test_story_files_import_only_local_or_bundled_modules``;
        this test scopes the same scan to the Overlays family's story files
        so the B5 evidence stands on its own: every import must be ``vue``
        (the locked, bundled runtime) or a relative path.
        """
        overlays_story_files = sorted(
            (APP_ROOT / "stories/Overlays").glob("*.stories.js")
        )
        self.assertEqual(len(overlays_story_files), len(OVERLAYS_FAMILY_KEYS))
        import_re = re.compile(
            r'(?:^|\n)\s*(?:import\s+(?:[\w${},*\s]+\s+from\s+)?|export\s+[\w{},*\s]+\s+from\s+)["\']([^"\']+)["\']'
        )
        for path in overlays_story_files:
            source = path.read_text(encoding="utf-8")
            for module in import_re.findall(source):
                self.assertTrue(
                    module.startswith(("./", "../")) or module == "vue",
                    f"{path.name} imports a non-local module: {module}",
                )


if __name__ == "__main__":
    unittest.main()
