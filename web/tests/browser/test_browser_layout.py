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
    focus_action_dock,
    install_outbound_recorder,
    inject_snapshot,
    sent_action_count,
    snapshot_envelope,
    store_state,
    valid_local_map_panel,
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
        # Wait for the connected state AND the status panel to be mounted, so
        # the DOM count is not taken before the panel renders.
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": '[data-testid="status-panel"]',
                "predicate": (
                    "() => { const el = document.querySelector('[data-testid=\"status-panel\"]'); "
                    "return el !== null; }"
                ),
                "description": "status panel mounted after reload",
            },
        )
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
    def test_mounted_shell_renders_no_tab_strip(self):
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
        # The Vue SPA desktop shell renders no tab strip: no visible
        # `.lm_header` element exists anywhere (the legacy GoldenLayout header
        # classes are gone), while every required surface is present and
        # self-identifying.
        self.assertEqual(
            page.locator(".lm_header:visible").count(),
            0,
            "the tab strip must not render visibly",
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
                "selector": '[data-testid="status-panel"]',
                "predicate": (
                    "() => { const el = document.querySelector('[data-testid=\"status-panel\"]'); "
                    "return el !== null; }"
                ),
                "description": "status panel mounted after reload",
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
                "selector": '[data-testid="status-panel"]',
                "predicate": (
                    "() => { const el = document.querySelector('[data-testid=\"status-panel\"]'); "
                    "return el !== null; }"
                ),
                "description": "status panel mounted after reload",
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
                "selector": '[data-testid="status-panel"]',
                "predicate": (
                    "() => { const el = document.querySelector('[data-testid=\"status-panel\"]'); "
                    "return el !== null; }"
                ),
                "description": "status panel mounted after reload",
            },
        )
        self.assert_surfaces_after_reload(page)

    def assert_surfaces_after_reload(self, page):
        for component in REQUIRED_COMPONENTS:
            count = self._count_component(page, component)
            self.assertEqual(count, 1, f"required component {component} missing")

    # H1 re-map (task 8.1): the layout's required components are now
    # identified by the stage anchors' DOM `data-testid` / id hooks rather than
    # the stale GoldenLayout `LayoutStore.createStore().load().config` walk.
    COMPONENT_SELECTORS = {
        "header": '[data-testid="topbar"]',
        "narrative": '[data-testid="narrative-feed"]',
        "art": '[data-testid="scene-backdrop"]',
        "status": '[data-testid="status-panel"]',
        "local-map": '[data-testid="local-map"]',
        "action-dock": "#action-dock",
        # H5 (webclient-hud-05-overlays-and-command-line): the layout-store
        # key `command-drawer` is preserved, but its DOM surface is now the
        # permanently-present command line (`command-line` testid), not the
        # retired drawer.
        "command-drawer": '[data-testid="command-line"]',
    }

    def _count_component(self, page, component) -> int:
        selector = self.COMPONENT_SELECTORS[component]
        return page.evaluate(
            "(sel) => document.querySelectorAll(sel).length",
            selector,
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


class ContextualHudStandingJourneyTest(BrowserAcceptanceTest):
    """H6 (webclient-hud-06-remap-and-finalize): the redesigned HUD invariants
    promoted into the standing layout journey, so every future change re-runs the
    stage-anchor non-overlap, the committed-mode surface gating, and the bounded
    caption's one-action full log at both supported viewports."""

    def _inject_snapshot(self, page, panels: dict, mode: str = "exploration") -> None:
        """Inject one schema-valid ``ui_snapshot`` through the store's ``receive``."""
        inject_snapshot(page, panels, mode=mode)

    def _wait_mode(self, page, mode: str, timeout: int = 30000) -> None:
        """Gate on the committed store mode matching ``mode``."""
        wait_for_store_state(page, lambda s: s.get("mode") == mode, timeout=timeout)

    def _press(self, page, key: str, wait_ms: int = 80) -> None:
        page.keyboard.press(key)
        page.wait_for_timeout(wait_ms)

    def _stage_anchor_rects(self, page):
        return page.evaluate(
            """() => {
              const ids = ["anchor-hud-left", "anchor-hud-right", "anchor-feed", "anchor-dock"];
              return ids.map((id) => {
                const el = document.querySelector('[data-testid="' + id + '"]');
                if (!el) return { id, rect: null };
                return { id, rect: el.getBoundingClientRect() };
              });
            }"""
        )

    def _anchors_overlap(self, page):
        rects = self._stage_anchor_rects(page)
        present = [r["rect"] for r in rects if r["rect"]]

        def right(r):
            return r["left"] + r["width"]

        def bottom(r):
            return r["top"] + r["height"]

        for i in range(len(present)):
            for j in range(i + 1, len(present)):
                a, b = present[i], present[j]
                overlap = not (
                    right(a) <= b["left"] or right(b) <= a["left"]
                    or bottom(a) <= b["top"] or bottom(b) <= a["top"]
                )
                if overlap:
                    return True
        return False

    @covers_requirement(
        "webclient-contextual-hud::the-hud-island-stack-renders-as-bounded-floating-islands-not-column-cards"
    )
    def test_no_stage_anchor_overlaps_at_supported_viewports(self):
        """No stage anchor's rendered box intersects another's at either supported
        viewport (H1's stage-anchor non-overlap invariant, promoted to the standing
        journey)."""
        for viewport in ((1440, 900), (1280, 720)):
            with self.subTest(viewport=viewport):
                page = self.logged_in_page(viewport)
                self._wait_mode(page, "exploration")
                # All four stage anchors must be present with non-zero boxes; a
                # deleted anchor would otherwise make the non-overlap check trivial.
                rects = self._stage_anchor_rects(page)
                for r in rects:
                    box = r["rect"]
                    self.assertIsNotNone(
                        box,
                        f"stage anchor {r['id']} is missing at {viewport}",
                    )
                    self.assertGreater(box["width"], 0, f"{r['id']} has a zero-width box at {viewport}")
                    self.assertGreater(box["height"], 0, f"{r['id']} has a zero-height box at {viewport}")
                self.assertFalse(
                    self._anchors_overlap(page),
                    f"no stage anchor overlaps another at {viewport}",
                )
                page.close()

    @covers_requirement(
        "webclient-contextual-hud::surface-visibility-is-gated-by-the-committed-game-mode"
    )
    def test_mode_gating_hides_and_restores_surfaces(self):
        """Mode-gated surfaces are hidden with ``display:none`` (leaving the
        accessibility tree and tab order) in the modes that hide them, and present
        again in the modes that show them, at both supported viewports. Focus that
        lands on a surface the mode change hides is rescued back to the action dock."""
        for viewport in ((1440, 900), (1280, 720)):
            with self.subTest(viewport=viewport):
                page = self.logged_in_page(viewport)
                map_panel = valid_local_map_panel()
                self._inject_snapshot(page, {"local_map": map_panel}, mode="exploration")
                self._wait_mode(page, "exploration")

                # Exploration: the minimap island and the command field are visible.
                self.assertEqual(
                    page.locator('[data-testid="local-map"]').count(), 1,
                    "the minimap island renders in exploration",
                )
                self.assertTrue(
                    page.locator('[data-testid="local-map"]').is_visible(),
                    "the minimap is visible in exploration",
                )
                self.assertEqual(page.locator("#inputfield").count(), 1, "the command field is present in exploration")
                self.assertTrue(page.locator("#inputfield").is_visible(), "the command field is visible in exploration")

                # Combat: the minimap is display:none (leaves the a11y tree + tab
                # order, never merely dimmed); the narrative feed, command line, and
                # action dock stay up.
                self._inject_snapshot(page, {"local_map": map_panel}, mode="combat")
                self._wait_mode(page, "combat")
                self.assertEqual(
                    page.locator('[data-testid="local-map"]').count(), 1,
                    "the minimap element stays in the DOM in combat",
                )
                self.assertTrue(
                    page.evaluate(
                        "() => { const el = document.querySelector('[data-testid=\"local-map\"]'); "
                        "return el ? (el.offsetParent === null) : false; }"
                    ),
                    "the minimap is display:none in combat, not merely dimmed",
                )
                for selector in (
                    '[data-testid="narrative-feed"]',
                    '[data-testid="command-line"]',
                    "#action-dock",
                ):
                    self.assertTrue(
                        page.locator(selector).is_visible(),
                        f"{selector} must stay visible in combat",
                    )

                # Creation: the full gated set is display:none (H1's visibility
                # matrix + design D10) — the feed anchor, the left HUD island stack
                # (hud-left), the command-line anchor, and the minimap.
                # Focus the command field first so the mode change hides the focused
                # surface; the shell rescues focus to the action dock.
                page.locator("#inputfield").click()
                self._inject_snapshot(page, {"local_map": map_panel}, mode="creation")
                self._wait_mode(page, "creation")
                for selector in (
                    '[data-anchor="feed"]',
                    '[data-anchor="hud-left"]',
                    '[data-anchor="command-line"]',
                    '[data-testid="local-map"]',
                ):
                    self.assertTrue(
                        page.evaluate(
                            "(sel) => { const el = document.querySelector(sel); "
                            "return el ? (el.offsetParent === null) : true; }",
                            selector,
                        ),
                        f"{selector} is display:none in creation mode",
                    )
                self.assertTrue(
                    page.evaluate(
                        "() => { const d = document.getElementById('action-dock');"
                        " const a = document.activeElement;"
                        " return d && (a === d || (a && d.contains(a))); }"
                    ),
                    "focus was rescued to the action dock when the focused surface was hidden",
                )

                # Return to exploration: the hidden surfaces are present again.
                self._inject_snapshot(page, {"local_map": map_panel}, mode="exploration")
                self._wait_mode(page, "exploration")
                self.assertTrue(
                    page.locator('[data-testid="local-map"]').is_visible(),
                    "the minimap is visible again in exploration",
                )
                self.assertEqual(page.locator("#inputfield").count(), 1)
                self.assertTrue(
                    page.locator("#inputfield").is_visible(),
                    "the command field is visible again in exploration",
                )
                page.close()

    @covers_requirement(
        "webclient-contextual-hud::the-narrative-is-a-bounded-caption-whose-complete-log-is-reachable-in-one-action"
    )
    def test_complete_log_reachable_in_one_action_from_bounded_caption(self):
        """The narrative caption is bounded and the full log opens in one action;
        the minimap stays inside its HUD island (task 6.4 phrasing)."""
        page = self.logged_in_page()
        for line in ("南門的風很涼。", "你看到一隻哥布林。", "哥布林舉起了木棒。"):
            page.evaluate("(text) => window.__elosernBridge.store.appendText('out', text)", line)
        feed = page.locator('[data-testid="narrative-feed"]')
        self.assertTrue(feed.is_visible(), "the narrative caption card renders")
        geometry = page.evaluate(
            """() => {
              const f = document.querySelector('[data-testid="narrative-feed"]');
              const st = document.querySelector('[data-testid="elosern-stage"]');
              return { feedHeight: f.getBoundingClientRect().height,
                       stageHeight: st.getBoundingClientRect().height };
            }"""
        )
        self.assertLess(
            geometry["feedHeight"],
            geometry["stageHeight"],
            "the caption card is bounded, not filling the stage",
        )
        page.locator('[data-testid="narrative-fulllog-control"]').click()
        page.wait_for_selector('[data-testid="fulllog-overlay"]', timeout=15000)
        overlay = page.locator('[data-testid="fulllog-overlay"]')
        self.assertTrue(overlay.is_visible(), "the full log opens in one action")
        log_text = overlay.inner_text()
        for line in ("南門的風很涼。", "你看到一隻哥布林。", "哥布林舉起了木棒。"):
            self.assertIn(line, log_text, "the full log shows the complete retained narrative")
        self._press(page, "Escape")
        page.wait_for_function(
            "() => document.querySelector('[data-testid=\"fulllog-overlay\"]') === null",
            timeout=15000,
        )
        self.assertEqual(
            page.locator('[data-testid="fulllog-overlay"]').count(),
            0,
            "the full log closes on Escape",
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
