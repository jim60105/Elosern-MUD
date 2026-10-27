"""Executed evidence for the host-neutral map view primitives.

``map-view-shared-foundations`` extracted the neutral projection, geometry and
glyph primitives into the local ``@elosern/map-view`` package and cut every
game map surface over to them in the same change. This module runs the
package's own dependency-free JS suite through ``node --test`` -- a real
primitive runner, not a source-presence check -- and asserts that each named
primitive test executed and passed, then checks the repository boundary: the
game tree keeps no second implementation, only the package's public entry is
imported, and the package carries no host dependency, stylesheet or design
token.

The delta requirement's canonical ID exists only after the archive sync, so no
``covers_requirement`` annotation is attached here (a delta ID would be an
unknown requirement); the tests below are the discoverable substantive
evidence for it.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import unittest

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE = REPO_ROOT / "packages/map-view"
PACKAGE_SRC = PACKAGE / "src"
PACKAGE_TESTS = PACKAGE / "tests"
GAME_DIR = REPO_ROOT / "web/webclient-app"

# The primitive evidence this slice must actually run: round-trip, zoom anchor,
# scale, glyph input, theme hook and the package's own boundary rules.
REQUIRED_TESTS = (
    "round-trips project and unproject at several views",
    "keeps the map point under the zoom anchor and the zoom reversible",
    "keeps the anchor fixed when limits clamp the requested span",
    "keeps unequal metric gaps unequal after pan and zoom",
    "sizes the scale bar from the same uniform scale",
    "returns the painted footprint of each explicit glyph input",
    "publishes a complete theme under the package namespace",
    "imports only relative sibling modules",
    "never touches the DOM, a timer, a network or host state",
    "ships no stylesheet and names no host design token",
)

# The neutral algorithms now live only in the package.
OBSOLETE_GAME_MODULES = ("lib/map_viewport.js", "lib/map_marker_geometry.js")
DUPLICATE_DEFINITIONS = (
    re.compile(r"\bfunction\s+project\s*\("),
    re.compile(r"\bfunction\s+fitBounds\s*\("),
    re.compile(r"\bfunction\s+unproject\s*\("),
    re.compile(r"\bfunction\s+gatePath\s*\("),
    re.compile(r"\bfunction\s+formatDistance\s*\("),
    re.compile(r"\bfunction\s+nearestStop\s*\("),
    re.compile(r"\bfunction\s+spanLimits\s*\("),
    re.compile(r"\bfunction\s+clampToRect\s*\("),
    re.compile(r"\bfunction\s+placeLabels\s*\("),
)
PACKAGE_IMPORT = re.compile(r'''(?:\bfrom\s*|\bimport\s*\()\s*["']@elosern/map-view["']''')
DEEP_IMPORT = re.compile(r'''["']@elosern/map-view/''')
HOST_TOKENS = re.compile(r"--gold-|--paper-|--seal-|--map-label-|--motion-|--ui-scale|--text-|--f-")
HOST_GLOBALS = re.compile(
    r"\b(document|window|globalThis|localStorage|sessionStorage|fetch|WebSocket|XMLHttpRequest|"
    r"setTimeout|setInterval|requestAnimationFrame|navigator|process)\b"
)


def js_files(directory: Path) -> list[Path]:
    return sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and path.suffix in {".js", ".vue", ".mjs"}
        and "node_modules" not in path.parts
    )


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def strip_comments(source: str) -> str:
    source = re.sub(r"/\*[\s\S]*?\*/", "", source)
    return re.sub(r"^[ \t]*//.*$", "", source, flags=re.MULTILINE)


class PrimitiveRunnerMixin(unittest.TestCase):
    """Runs the package suite once; each method inspects the same TAP result."""

    passed: set[str]
    failures: list[str]
    result: subprocess.CompletedProcess

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        suites = sorted(PACKAGE_TESTS.glob("*.test.js"))
        assert suites, f"no primitive suite under {PACKAGE_TESTS}"
        cls.result = subprocess.run(
            ["node", "--test", "--test-reporter=tap", *[str(path) for path in suites]],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=300,
        )
        cls.passed, cls.failures = cls.parse_tap(cls.result.stdout)

    @staticmethod
    def parse_tap(output: str) -> tuple[set[str], list[str]]:
        """Collect top-level TAP results; nested describe output is indented."""
        passed: set[str] = set()
        failures: list[str] = []
        for line in output.splitlines():
            match = re.match(r"^(not ok|ok) \d+ - (.+)$", line)
            if not match:
                continue
            status, name = match.group(1), match.group(2).strip()
            if " # SKIP" in name or " # TODO" in name:
                failures.append(f"skipped evidence: {name}")
                continue
            if status == "ok":
                passed.add(name)
            else:
                failures.append(name)
        return passed, failures

    def assert_suite_green(self):
        self.assertEqual(
            self.result.returncode,
            0,
            "the @elosern/map-view suite must pass:\n"
            + self.result.stdout[-4000:]
            + self.result.stderr[-2000:],
        )
        self.assertFalse(self.failures, f"primitive tests failed or were skipped: {self.failures}")
        self.assertGreaterEqual(len(self.passed), 40, f"only {len(self.passed)} primitive tests ran")


class PrimitiveEvidenceTests(PrimitiveRunnerMixin):
    def test_round_trip_anchor_and_scale_primitives_run(self):
        # The real runner executed the package's round-trip, zoom-anchor,
        # fit/scale and unequal-gap tests; an exit code alone is not evidence.
        self.assert_suite_green()
        for name in REQUIRED_TESTS:
            self.assertIn(name, self.passed, f"primitive test did not run: {name}")

    def test_glyph_inputs_and_theme_hooks_run(self):
        # The glyph footprint comes from an explicit host descriptor and the
        # theme hook is complete and namespaced: both proved by executed tests.
        self.assert_suite_green()
        self.assertIn("returns the painted footprint of each explicit glyph input", self.passed)
        self.assertIn("scales the whole glyph footprint by the surface scale", self.passed)
        self.assertIn("rejects an unknown role and an empty value", self.passed)
        self.assertIn("never fabricates coordinates for a coordinate-free layer", self.passed)


class RepositoryBoundaryTests(unittest.TestCase):
    def test_game_tree_keeps_no_second_implementation(self):
        for relative in OBSOLETE_GAME_MODULES:
            self.assertFalse((GAME_DIR / relative).exists(), f"obsolete module still present: {relative}")
        offenders = []
        for path in js_files(GAME_DIR):
            source = strip_comments(read(path))
            for pattern in DUPLICATE_DEFINITIONS:
                if pattern.search(source):
                    offenders.append(f"{path.relative_to(REPO_ROOT)}: {pattern.pattern}")
        self.assertEqual(offenders, [], "a game module still defines an extracted algorithm")

    def test_only_the_public_entry_is_imported(self):
        importers = []
        for path in js_files(GAME_DIR):
            source = read(path)
            self.assertIsNone(
                DEEP_IMPORT.search(source),
                f"{path.relative_to(REPO_ROOT)} imports past the package's public entry",
            )
            if PACKAGE_IMPORT.search(source):
                importers.append(str(path.relative_to(REPO_ROOT)))
        # The same cutover migrated every area/world/minimap consumer.
        self.assertGreaterEqual(len(importers), 8, f"too few package consumers: {importers}")
        for consumer in (
            "web/webclient-app/components/AreaMapView.vue",
            "web/webclient-app/components/WorldMapView.vue",
            "web/webclient-app/components/MapDrawer.vue",
            "web/webclient-app/lib/area_map_view.js",
            "web/webclient-app/lib/minimap_projection.js",
        ):
            self.assertIn(consumer, importers)

    def test_package_never_reaches_host_state_or_host_ink(self):
        sources = sorted(PACKAGE_SRC.glob("*.js"))
        self.assertGreaterEqual(len(sources), 8)
        for path in sources:
            code = strip_comments(read(path))
            self.assertIsNone(HOST_GLOBALS.search(code), f"{path.name} reaches a host global")
            self.assertIsNone(HOST_TOKENS.search(code), f"{path.name} names a host design token")
            self.assertNotRegex(code, r'from\s+"\.\./', f"{path.name} imports outside the package")
            # Only the package's own `--map-view` namespace may appear.
            for token in re.findall(r"--[a-z0-9-]+", code):
                self.assertTrue(token.startswith("--map-view"), f"{path.name} publishes {token}")

    def test_build_and_lock_integration_is_declared(self):
        package = json.loads(read(PACKAGE / "package.json"))
        self.assertEqual(package["name"], "@elosern/map-view")
        self.assertEqual(package["type"], "module")
        self.assertNotIn("dependencies", package)
        self.assertNotIn("peerDependencies", package)
        root = json.loads(read(REPO_ROOT / "package.json"))
        # The workspace link is a locked dev dependency; the game bundle keeps
        # no runtime package dependency.
        self.assertEqual(root["devDependencies"]["@elosern/map-view"], "workspace:*")
        self.assertIn("node --test packages/map-view/tests/*.test.js", root["scripts"]["test:map-view"])
        workspace = yaml.safe_load(read(REPO_ROOT / "pnpm-workspace.yaml"))
        self.assertIn("packages/*", workspace["packages"])
        self.assertEqual(workspace["allowBuilds"], {"esbuild": True})
        lock = read(REPO_ROOT / "pnpm-lock.yaml")
        self.assertIn("@elosern/map-view", lock)
        self.assertIn("workspace:*", lock)

    def test_frontend_gate_runs_the_primitive_suite(self):
        workflow = yaml.safe_load(read(REPO_ROOT / ".github/workflows/quality-gate.yml"))
        steps = {step["name"]: step for step in workflow["jobs"]["frontend"]["steps"]}
        self.assertIn("pnpm run test:map-view", steps["Run map-view primitive tests"]["run"])


if __name__ == "__main__":
    unittest.main()
