"""Action-registry coverage pin against the client command-line catalog.

The browser's display-only command catalog
(`web/static/webclient/js/elosern/command_echo.js`) must resolve a display
line — or declare an explicit silent presentation control — for every
registered mutation action, so no UI action can ship with a silent
input-echo gap. The shared manifest
(`web/static/webclient/js/tests/command_echo_coverage_manifest.json`) is the
single id source for the Node catalog gate, the Vitest per-surface behavioral
table, and this registry pin: registering or removing an action without
touching the catalog (and the manifest, reviewed together) fails CI.
"""

import json
import unittest
from pathlib import Path

from tools.spec_traceability import covers_requirement
from web.webclient.actions.registry import build_production_action_registry

# Repo-root-relative: web/webclient/actions/tests -> repo root is 5 parents up
# (tests -> actions -> webclient -> web -> repo root).
MANIFEST_PATH = (
    Path(__file__).resolve().parents[4]
    / "web"
    / "static"
    / "webclient"
    / "js"
    / "tests"
    / "command_echo_coverage_manifest.json"
)


class ActionCatalogCoveragePinTests(unittest.TestCase):
    @covers_requirement(
        "webclient-input-narrative::catalog-coverage-is-pinned-against-the-action-registry"
    )
    def test_registry_action_ids_equal_the_catalog_pinned_set(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        pinned = frozenset(manifest["registeredMutationActionIds"])
        registered = build_production_action_registry().action_ids
        missing = registered - pinned
        stale = pinned - registered
        self.assertEqual(
            registered,
            pinned,
            "action registry drifted from the command-echo coverage manifest: "
            f"new ids {sorted(missing)} must be added to the catalog resolvers "
            "(or its silent list) in "
            "web/static/webclient/js/elosern/command_echo.js, its Node coverage "
            "fixture in command_echo.test.js, and "
            "command_echo_coverage_manifest.json; removed ids "
            f"{sorted(stale)} must be dropped from all three",
        )

    def test_manifest_silent_controls_are_registered(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        silent = frozenset(manifest["silentPresentationControlIds"])
        self.assertTrue(
            silent <= build_production_action_registry().action_ids,
            "every declared silent control must be a registered action",
        )
