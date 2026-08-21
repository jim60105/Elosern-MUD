"""Evidence bridge: run the Vue showcase gates as requirement evidence (B1).

The core-family contract of webclient-vue-02-showcase-core is implemented and
verified in the Node/Vue world: the Vite build, the Vitest component suite,
the Storybook static build, and the deterministic component-coverage gate.
``covers_requirement`` can only attach to a Python ``test_*`` function, so
this module executes those gates and asserts they pass. The annotations
linking the two new capabilities (``webclient-vue-application`` and
``webclient-component-showcase``) were applied at this change's archive, when
the requirement IDs entered the traceability index with the synced delta
specs.

Test-to-requirement mapping (the browser-shard counterparts are listed where
they evidence the same requirement):

- ``webclient-vue-application::the-webclient-loads-a-self-contained-offline-vue-spa``:
  ``test_vite_build_emits_stable_offline_entries`` (the offline-load and
  bounded-render-at-each-viewport scenarios are additionally evidenced in the
  browser shard by
  ``test_vue_foundation.VueFoundationBrowserTest.test_vue_bundle_loads_from_origin_offline``
  and
  ``test_core_surfaces_render_usable_at_supported_viewports``).
- ``webclient-vue-application::the-design-system-carries-over-from-the-design-draft-and-stays-offline``:
  ``test_builtin_design_system_is_self_hosted_and_offline``,
  ``test_vitest_core_family_suite_passes`` (the status-is-not-color-only
  scenario is asserted there by the TopBar connection-state test; the
  browser bundle test additionally asserts the self-hosted fonts load from
  the project origin).
- ``webclient-component-showcase::every-required-ui-component-is-a-vue-sfc-with-a-documented-storybook-story``:
  ``test_component_coverage_gate_passes``,
  ``test_component_coverage_gate_fails_for_an_undocumented_required_story``,
  ``test_vitest_core_family_suite_passes``.
- ``webclient-component-showcase::the-component-showcase-is-completed-before-live-wiring-and-is-a-mandatory-ci-gate``:
  ``test_storybook_showcase_build_succeeds``,
  ``test_component_coverage_gate_fails_for_a_missing_required_story`` (the
  CI wiring of the gate is asserted by
  ``tests.test_frontend_toolchain_contract.VueComponentGateTests``).
- ``webclient-component-showcase::storybook-stories-use-deterministic-offline-data-only``:
  ``test_story_files_import_only_local_or_bundled_modules``,
  ``test_storybook_showcase_build_succeeds`` (the offline-rendering scenario
  is evidenced in the browser shard by
  ``test_vue_foundation.VueFoundationBrowserTest.test_storybook_stories_render_offline``).
"""

from __future__ import annotations

import glob
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "web/webclient-app"
DIST_ROOT = REPO_ROOT / "web/static/webclient/app/dist"
LEGACY_TESTS_GLOB = REPO_ROOT / "web/static/webclient/js/tests" / "*.test.js"
TEMPLATE = REPO_ROOT / "web/templates/webclient/base.html"

# URL string constants shipped inside the minified bundle that are XML
# namespace identifiers or a docs reference, never runtime requests.
KNOWN_NON_REQUEST_URL_CONSTANTS = (
    "http://www.w3.org/2000/svg",
    "http://www.w3.org/1999/xlink",
    "http://www.w3.org/1998/Math/MathML",
    "https://vuejs.org/error-reference/",
)


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


class VueShowcaseEvidenceTest(unittest.TestCase):
    """Execute the B1 showcase gates and assert each one passes."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        result = run_npm(["run", "build"], timeout=600)
        assert (
            result.returncode == 0
        ), "vite build failed under evidence:\n" + result.stdout + result.stderr

    @covers_requirement(
        "webclient-vue-application::the-webclient-loads-a-self-contained-offline-vue-spa"
    )
    def test_vite_build_emits_stable_offline_entries(self):
        """The app dist serves its stable entries from the project origin only."""
        for entry in ("index.js", "index.css"):
            path = DIST_ROOT / entry
            self.assertTrue(path.is_file(), f"missing stable dist entry {path}")
            self.assertGreater(path.stat().st_size, 100, f"{path} looks empty")
            content = path.read_text(encoding="utf-8")
            if entry == "index.js":
                # String constants that are XML namespace identifiers or a
                # docs reference, never runtime requests: stripping them keeps
                # the assertion meaningful instead of matching constants.
                for constant in KNOWN_NON_REQUEST_URL_CONSTANTS:
                    content = content.replace(constant, "")
            self.assertNotIn(
                "http://", content, f"{path} references a remote http URL"
            )
            self.assertNotIn(
                "https://", content, f"{path} references a remote https URL"
            )
        css = (DIST_ROOT / "index.css").read_text(encoding="utf-8")
        for token in ("@media (max-width", "@media(max-width"):
            self.assertNotIn(
                token,
                css,
                "the desktop-only application must not ship mobile-breakpoint "
                "media queries",
            )
        template = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("webclient/app/dist/index.js", template)
        self.assertIn("webclient/app/dist/index.css", template)

    def test_dependency_free_node_gate_still_passes(self):
        """The preserved UMD logic still verifies under bare node --test."""
        test_files = sorted(glob.glob(str(LEGACY_TESTS_GLOB)))
        self.assertTrue(test_files, "no dependency-free Node tests discovered")
        result = run_node(["--test", *test_files], timeout=300)
        self.assertEqual(
            result.returncode,
            0,
            "dependency-free Node gate failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("pass", result.stdout)

    @covers_requirement(
        "webclient-vue-application::the-design-system-carries-over-from-the-design-draft-and-stays-offline"
    )
    def test_builtin_design_system_is_self_hosted_and_offline(self):
        """The built stylesheet self-hosts its fonts and ships the motion tokens."""
        css = (DIST_ROOT / "index.css").read_text(encoding="utf-8")
        self.assertGreaterEqual(
            css.count("@font-face"),
            3,
            "display, serif, and sans typefaces must each be self-hosted",
        )
        remote_urls = [
            url
            for url in re.findall(r'url\(\s*["\']?([^)"\']+)', css)
            if url.startswith(("http://", "https://"))
        ]
        self.assertEqual(remote_urls, [], f"remote font/asset URLs: {remote_urls}")
        self.assertIn(
            "::selection",
            css,
            "the design-draft selection rule must survive into the built "
            "stylesheet",
        )
        # The reduced-motion media query must survive with its disabling rule
        # intact (nonessential motion forced to 1ms), not merely its keyword.
        # The minifier emits `@media(prefers-reduced-motion:reduce)`, so anchor
        # on the keyword and brace-match the block that follows.
        condition = css.find("prefers-reduced-motion")
        self.assertNotEqual(
            condition,
            -1,
            "the reduced-motion media query must survive into the built "
            "stylesheet",
        )
        start = css.index("{", condition)
        depth = 0
        end = start
        for i in range(start, len(css)):
            if css[i] == "{":
                depth += 1
            elif css[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        block = re.sub(r"\s+", "", css[start : end + 1])
        for token in (
            "--motion-fast:1ms",
            "--motion-base:1ms",
            "transition-duration:1ms!important",
            "animation-duration:1ms!important",
        ):
            self.assertIn(
                token,
                block,
                f"reduced motion must disable nonessential motion: {token} "
                "is not in the media block",
            )

    @covers_requirement(
        "webclient-vue-application::the-design-system-carries-over-from-the-design-draft-and-stays-offline",
        "webclient-component-showcase::every-required-ui-component-is-a-vue-sfc-with-a-documented-storybook-story",
    )
    def test_vitest_core_family_suite_passes(self):
        """Every core-family SFC renders its contract states under Vitest."""
        result = run_npm(["test"], timeout=600)
        self.assertEqual(
            result.returncode,
            0,
            "Vitest core-family suite failed:\n" + result.stdout + result.stderr,
        )
        self.assertIn("passed", result.stdout)

    @covers_requirement(
        "webclient-component-showcase::the-component-showcase-is-completed-before-live-wiring-and-is-a-mandatory-ci-gate",
        "webclient-component-showcase::storybook-stories-use-deterministic-offline-data-only",
    )
    def test_storybook_showcase_build_succeeds(self):
        """The showcase gate builds the static Storybook from local data."""
        result = run_npm(["run", "build-storybook"], timeout=900)
        self.assertEqual(
            result.returncode,
            0,
            "Storybook showcase build failed:\n" + result.stdout + result.stderr,
        )
        out_dir = REPO_ROOT / ".storybook-out"
        self.assertTrue((out_dir / "iframe.html").is_file(), "missing iframe.html")
        index = (out_dir / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("https://", index, "the showcase index references a remote URL")

    @covers_requirement(
        "webclient-component-showcase::every-required-ui-component-is-a-vue-sfc-with-a-documented-storybook-story"
    )
    def test_component_coverage_gate_passes(self):
        """The manifest and the registered stories are in complete lockstep."""
        required = json.loads(
            (APP_ROOT / "component-manifest.json").read_text(encoding="utf-8")
        )["required"]
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
        "webclient-component-showcase::the-component-showcase-is-completed-before-live-wiring-and-is-a-mandatory-ci-gate"
    )
    def test_component_coverage_gate_fails_for_a_missing_required_story(self):
        """A manifest-listed component without a story fails the gate.

        The probe runs against a temporary manifest (the gate accepts an
        alternate manifest path) so parallel processes never observe a
        mutated tracked file.
        """
        original = json.loads(
            (APP_ROOT / "component-manifest.json").read_text(encoding="utf-8")
        )
        probe = dict(original)
        probe["required"] = list(probe["required"]) + ["Core/UnlistedProbe"]
        with tempfile.TemporaryDirectory() as tmp:
            probe_path = Path(tmp) / "manifest.json"
            probe_path.write_text(json.dumps(probe), encoding="utf-8")
            result = run_node(
                ["scripts/component-coverage.mjs", str(probe_path)], timeout=120
            )
        self.assertNotEqual(
            result.returncode,
            0,
            "the coverage gate must fail when a required story is missing:\n"
            + result.stdout
            + result.stderr,
        )
        self.assertIn("Core/UnlistedProbe", result.stderr)

    @covers_requirement(
        "webclient-component-showcase::every-required-ui-component-is-a-vue-sfc-with-a-documented-storybook-story"
    )
    def test_component_coverage_gate_fails_for_an_undocumented_required_story(self):
        """A listed component whose story binds no props fails the gate.

        The probe story file is a temporary sibling under ``stories/`` (the
        gate walks that tree) and the probe manifest a temporary path, so
        parallel processes never observe mutated tracked files.
        """
        original = json.loads(
            (APP_ROOT / "component-manifest.json").read_text(encoding="utf-8")
        )
        probe = dict(original)
        probe["required"] = list(probe["required"]) + ["Core/DocProbe"]
        with tempfile.TemporaryDirectory() as tmp:
            probe_path = Path(tmp) / "manifest.json"
            probe_path.write_text(json.dumps(probe), encoding="utf-8")
            with tempfile.TemporaryDirectory(dir=str(APP_ROOT / "stories")) as probe_dir:
                (Path(probe_dir) / "DocProbe.stories.js").write_text(
                    "export default { title: 'Core/DocProbe' };\n"
                    "export const Probe = {};\n",
                    encoding="utf-8",
                )
                result = run_node(
                    ["scripts/component-coverage.mjs", str(probe_path)],
                    timeout=120,
                )
        self.assertNotEqual(
            result.returncode,
            0,
            "the coverage gate must fail when a listed story is undocumented:\n"
            + result.stdout
            + result.stderr,
        )
        self.assertIn("undocumented", result.stderr)
        self.assertIn("Core/DocProbe", result.stderr)

    @covers_requirement(
        "webclient-component-showcase::storybook-stories-use-deterministic-offline-data-only"
    )
    def test_story_files_import_only_local_or_bundled_modules(self):
        """Stories import only relative files or the locked, bundled Vue runtime.

        ``vue`` is a devDependency pinned in the lockfile and inlined by the
        Vite/Storybook build, so it is offline; anything else must be a
        relative import of a sibling source or fixture.
        """
        story_files = sorted(APP_ROOT.glob("**/*.stories.js"))
        self.assertTrue(story_files, "no story files discovered")
        import_re = re.compile(
            r'(?:^|\n)\s*(?:import\s+(?:[\w${},*\s]+\s+from\s+)?|export\s+[\w{},*\s]+\s+from\s+)["\']([^"\']+)["\']'
        )
        for path in story_files:
            source = path.read_text(encoding="utf-8")
            for module in import_re.findall(source):
                self.assertTrue(
                    module.startswith(("./", "../")) or module == "vue",
                    f"{path.name} imports a non-local module: {module}",
                )


if __name__ == "__main__":
    unittest.main()
