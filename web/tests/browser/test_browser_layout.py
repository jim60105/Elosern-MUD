"""Layout migration, malformed-panel degradation, and protocol mismatch tests
(section 6.8).

Layout persistence is versioned and presentation-only: a known layout version
persists across reloads, unknown/malformed/oversized values reset to the
approved default with every required component, and a malformed panel degrades
without a sync loop. An incompatible protocol version locks graphical actions
while ordinary text commands keep working.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    fresh_epoch,
    install_outbound_recorder,
    sent_action_count,
    snapshot_envelope,
    store_state,
    valid_status_panel,
    wait_for_store_state,
)

LAYOUT_KEY = "elosern.layout"
REQUIRED_COMPONENTS = (
    "header",
    "narrative",
    "art",
    "status",
    "local-map",
    "action-dock",
    "command-drawer",
)


class LayoutMigrationTest(BrowserAcceptanceTest):
    """Versioned layout persistence, migration, and reset behavior."""

    def _set_layout(self, page, value) -> None:
        page.evaluate(
            "(args) => localStorage.setItem(args.key, JSON.stringify(args.value))",
            {"key": LAYOUT_KEY, "value": value},
        )

    def _layout(self, page):
        return page.evaluate(
            "(key) => { const raw = localStorage.getItem(key); "
            "return raw === null ? null : JSON.parse(raw); }",
            LAYOUT_KEY,
        )

    @covers_requirement(
        "webclient-desktop-shell::browser-persistence-is-versioned-and-presentation-only"
    )
    def test_known_layout_version_persists_across_reload(self):
        page = self.logged_in_page()
        wrapper = {
            "layout_version": 1,
            "dimensions": {"narrative": 55},
            "tabs": {"status": True},
            "preferences": {"text2html": True},
        }
        self._set_layout(page, wrapper)
        page.reload()
        wait_for_store_state(page, lambda s: bool(s.get("connected")))
        for component in REQUIRED_COMPONENTS:
            count = self._count_component(page, component)
            self.assertEqual(
                count, 1, f"required component {component} missing after reload"
            )
        saved = self._layout(page)
        self.assertEqual(saved["layout_version"], 1)
        # The reload re-persists the full dimension set from the live layout;
        # the stored narrative dimension and tab state must survive it.
        self.assertEqual(saved["dimensions"]["narrative"], 55)
        self.assertTrue(saved["tabs"]["status"])

    @covers_requirement(
        "webclient-desktop-shell::the-webclient-loads-a-local-vue-spa-desktop-shell"
    )
    def test_mounted_shell_renders_no_goldenlayout_tab_strip(self):
        page = self.logged_in_page()
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": "#action-dock",
                "predicate": (
                    "() => { const d = document.getElementById('action-dock'); "
                    "if (!d) { return false; } "
                    "const r = d.getBoundingClientRect(); "
                    "return r.width > 0 && r.height > 0 && d.offsetParent !== null; }"
                ),
                "description": "#action-dock rendered and visible",
            },
        )
        # `settings.hasHeaders: false` hides the tab strip entirely: no
        # visible `.lm_header` element exists anywhere (GoldenLayout keeps the
        # hidden header nodes in the DOM), while every required surface is
        # present and self-identifying.
        self.assertEqual(
            page.locator(".lm_header:visible").count(),
            0,
            "the GoldenLayout tab strip must not render visibly",
        )
        for component in REQUIRED_COMPONENTS:
            count = self._count_component(page, component)
            self.assertEqual(count, 1, f"required component {component} missing")

    def test_migration_registry_migrates_known_prior_version(self):
        page = self.logged_in_page()
        # A stored prior version (0) with a known migration is migrated to the
        # current version and the migrated wrapper is persisted.
        result = page.evaluate(
            """() => {
              const key = 'elosern.migration-probe';
              localStorage.setItem(key, JSON.stringify({
                layout_version: 0, dimensions: {}, tabs: {}, preferences: {},
              }));
              const store = Elosern.LayoutStore.createStore({
                storage: window.localStorage,
                key: key,
                currentVersion: 1,
                migrations: { 0: function (raw) {
                  raw.dimensions = { narrative: 42 }; return raw; } },
              });
              const loaded = store.load();
              const stored = JSON.parse(localStorage.getItem(key));
              return { migrated: loaded.state.layout_version,
                storedVersion: stored.layout_version,
                storedDim: stored.dimensions };
            }"""
        )
        self.assertEqual(result["migrated"], 1)
        self.assertEqual(result["storedVersion"], 1)
        self.assertEqual(result["storedDim"], {"narrative": 42})

    @covers_requirement(
        "webclient-desktop-shell::browser-persistence-is-versioned-and-presentation-only"
    )
    def test_unknown_malformed_layout_resets(self):
        page = self.logged_in_page()
        page.goto(self.webclient_url)
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": "#action-dock",
                "predicate": (
                    "() => { const d = document.getElementById('action-dock'); "
                    "if (!d) { return false; } "
                    "const r = d.getBoundingClientRect(); "
                    "return r.width > 0 && r.height > 0 && d.offsetParent !== null; }"
                ),
                "description": "#action-dock rendered and visible",
            },
        )

        # Non-JSON garbage resets to the default with all required components.
        page.evaluate(
            "(args) => localStorage.setItem(args.key, args.value)",
            {"key": LAYOUT_KEY, "value": "{{not json"},
        )
        page.reload()
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": "#action-dock",
                "predicate": (
                    "() => { const d = document.getElementById('action-dock'); "
                    "if (!d) { return false; } "
                    "const r = d.getBoundingClientRect(); "
                    "return r.width > 0 && r.height > 0 && d.offsetParent !== null; }"
                ),
                "description": "#action-dock rendered and visible",
            },
        )
        self.assert_surfaces_after_reload(page)

        # A JSON wrapper with an unknown layout version resets.
        self._set_layout(
            page,
            {
                "layout_version": 99,
                "dimensions": {},
                "tabs": {},
                "preferences": {},
            },
        )
        page.reload()
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": "#action-dock",
                "predicate": (
                    "() => { const d = document.getElementById('action-dock'); "
                    "if (!d) { return false; } "
                    "const r = d.getBoundingClientRect(); "
                    "return r.width > 0 && r.height > 0 && d.offsetParent !== null; }"
                ),
                "description": "#action-dock rendered and visible",
            },
        )
        self.assert_surfaces_after_reload(page)
        stored = self._layout(page)
        self.assertEqual(stored["layout_version"], 1, "unknown version resets")

        # An oversized wrapper resets regardless of content.
        self._set_layout(
            page,
            {
                "layout_version": 1,
                "dimensions": {"narrative": 50},
                "tabs": {},
                "preferences": {},
                "junk": "x" * 4096,
            },
        )
        page.reload()
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": "#action-dock",
                "predicate": (
                    "() => { const d = document.getElementById('action-dock'); "
                    "if (!d) { return false; } "
                    "const r = d.getBoundingClientRect(); "
                    "return r.width > 0 && r.height > 0 && d.offsetParent !== null; }"
                ),
                "description": "#action-dock rendered and visible",
            },
        )
        self.assert_surfaces_after_reload(page)

    def assert_surfaces_after_reload(self, page):
        for component in REQUIRED_COMPONENTS:
            count = self._count_component(page, component)
            self.assertEqual(count, 1, f"required component {component} missing")

    def _count_component(self, page, component) -> int:
        return page.evaluate(
            """(c) => {
              const store = Elosern.LayoutStore.createStore(
                { storage: window.localStorage });
              const config = store.load().config;
              let found = 0;
              (function walk(item) {
                if (item.type === 'component' && item.componentName === c) found++;
                if (item.content) item.content.forEach(walk);
              })(config);
              return found;
            }""",
            component,
        )

    def test_one_sync_malformed_panel_degrades_without_loop(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        generation = store_state(page)["generation"]

        malformed = snapshot_envelope(
            fresh_epoch(),
            100,
            {"status": {"schema_version": 1, "available": True, "actor": "nope"}},
        )
        result = page.evaluate(
            "(args) => window.__elosernBridge.store.receive("
            "args.generation, 'ui_snapshot', [args.envelope], {})",
            {"generation": generation, "envelope": malformed},
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason"], "invalid")

        # The panel renderer requests one resync; a second request in the same
        # episode is blocked, so a malformed panel cannot create a sync loop.
        first = page.evaluate(
            "() => Elosern.actions.requestResync('status')"
        )
        second = page.evaluate(
            "() => Elosern.actions.requestResync('status')"
        )
        self.assertTrue(first)
        self.assertFalse(second)

        # Ordinary text play continues.
        narrative_before = len(page.locator('[data-testid="narrative-feed"]').inner_text())
        page.evaluate("Evennia.msg('text', ['look'], {})")
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": '[data-testid="narrative-feed"]',
                "predicate": (
                    "() => { const el = document.querySelector('[data-testid=\"narrative-feed\"]'); "
                    "return el && el.innerText.length > %d; }"
                    ) % narrative_before,
                "description": "narrative feed grew past the pre-command length",
            },
        )


class ProtocolMismatchTest(BrowserAcceptanceTest):
    """An incompatible protocol version locks actions while text still works."""

    @covers_requirement(
        "webclient-oob-protocol::protocol-failures-degrade-without-disabling-text-play",
        "webclient-browser-verification::browser-acceptance-covers-foundation-recovery-and-layout-behavior",
    )
    def test_incompatible_protocol_locks_actions_but_text_continues(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        generation = store_state(page)["generation"]
        revision_before = store_state(page)["revision"]

        # A snapshot with an unsupported protocol version is rejected atomically.
        v2 = snapshot_envelope(
            fresh_epoch(), 1, {"status": valid_status_panel("X", "y")},
            protocol_version=2,
        )
        rejected = page.evaluate(
            "(args) => window.__elosernBridge.store.receive("
            "args.generation, 'ui_snapshot', [args.envelope], {})",
            {"generation": generation, "envelope": v2},
        )
        self.assertFalse(rejected["accepted"])
        self.assertEqual(store_state(page)["revision"], revision_before)

        # The server's protocol-error reply locks every graphical mutation.
        page.evaluate(
            "(args) => window.__elosernBridge.store.receive("
            "args.generation, 'ui_protocol_error', [args.envelope], {})",
            {
                "generation": generation,
                "envelope": {
                    "protocol_version": 1,
                    "code": "unsupported_version",
                    "message": "不支援的協定版本",
                    "reload_required": True,
                },
            },
        )
        self.assertTrue(store_state(page)["mutationsLocked"])

        refused = page.evaluate("() => Elosern.actions.submit('proof.noop', {})")
        self.assertIsNone(refused)
        self.assertEqual(sent_action_count(page), 0)

        # Ordinary text input remains fully operational.
        narrative_before = len(page.locator('[data-testid="narrative-feed"]').inner_text())
        page.evaluate("Evennia.msg('text', ['look'], {})")
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": '[data-testid="narrative-feed"]',
                "predicate": (
                    "() => { const el = document.querySelector('[data-testid=\"narrative-feed\"]'); "
                    "return el && el.innerText.length > %d; }"
                    ) % narrative_before,
                "description": "narrative feed grew past the pre-command length",
            },
        )
        self.assertGreater(
            len(page.locator('[data-testid="narrative-feed"]').inner_text()), narrative_before
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
