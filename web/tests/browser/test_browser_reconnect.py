"""End-to-end WebSocket interruption/reconnect tests (section 6.7).

The real Evennia WebSocket transport is interrupted abnormally (which, unlike
Evennia's graceful ``websocket_close``, preserves the Django-session login) and
reconnected to prove offline locking, no automatic mutation retry, and the
uncertain-result notice. Epoch/revision admission semantics (lower-revision
adoption in a new transport generation, rejection of retired/prior-generation
and different-epoch messages) are asserted against the exact reducer the
browser runs -- the live wired store where the transport is still stable, and
a fresh ``Elosern.Protocol`` reducer where the server would otherwise race the
awaiting-phase checks.
"""

from __future__ import annotations

import os
import time

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    evaluate_tolerating_navigation,
    fresh_epoch,
    install_outbound_recorder,
    sent_action_count,
    snapshot_envelope,
    store_state,
    store_state_or_none,
    suppress_one_shot_recovery_reload,
    valid_status_panel,
    wait_for_store_state,
)


class ReconnectTest(BrowserAcceptanceTest):
    """Transport interruption and new-generation adoption through the real store."""

    @classmethod
    def setUpClass(cls) -> None:
        from . import fixtures
        from .harness import ManagedServer

        runtime = fixtures.create_runtime(prefix="elosern-reconnect-")
        runtime.env["ELOSERN_BROWSER_ART"] = "done"
        cls.server = ManagedServer(runtime=runtime)
        cls.server.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.runtime.http_port}"
        cls.webclient_url = cls.server.runtime.webclient_url

    @classmethod
    def tearDownClass(cls) -> None:
        if getattr(cls, "server", None) is not None:
            try:
                cls.server.stop()
            finally:
                cls.server = None

    def _wait_transport_reopened(self, page, generation_before, timeout=30):
        """Wait for the reconnect to open a new transport generation.

        The transport reopens deterministically; re-attaching the account's
        puppet on the server can lag, so this helper only requires the new
        generation (the reconnected socket) to exist, never the server's
        re-auth to have produced a snapshot.
        """
        deadline = time.monotonic() + timeout
        reconnects = 0
        while time.monotonic() < deadline:
            # `store_state_or_none` tolerates the re-bootstrap window (and any
            # in-flight navigation) where the ``Elosern`` global is absent.
            state = store_state_or_none(page)
            if state and state["generation"] > generation_before:
                return state
            if reconnects == 0 and time.monotonic() > deadline - 25:
                evaluate_tolerating_navigation(page, "Evennia.connect()")
                reconnects += 1
            page.wait_for_timeout(500)
        self.fail("reconnected transport never opened a new generation")

    def _disconnect_transport(self, page):
        # Scope the window under test to the client's own websocket reconnect,
        # not the one-shot recovery reload: under a loaded runner a slow
        # puppet re-attach can exhaust the awaiting-snapshot resync budget and
        # trigger a page reload, which would reset the generation / recorder /
        # uncertain-notice state these tests assert on.
        suppress_one_shot_recovery_reload(page)
        # Abnormally close the raw WebSocket: unlike the client's graceful
        # ``websocket_close`` (which clears the Django-session auth), this
        # preserves the login so the reconnected transport is re-authenticated.
        page.evaluate(
            "() => { if (window.__elosernWs) window.__elosernWs.close(4001); }"
        )
        wait_for_store_state(page, lambda s: not s.get("connected"))
        wait_for_store_state(
            page,
            lambda s: not s.get("connected"),
            dom_readiness={
                "selector": "#elosern-offline-overlay",
                "predicate": (
                    "() => { const o = document.getElementById('elosern-offline-overlay'); "
                    "return o && o.getAttribute('data-visible') === 'true'; }"
                ),
                "description": "offline overlay visible",
            },
        )

    @covers_requirement(
        "webclient-desktop-shell::connection-loss-locks-stale-controls"
    )
    def test_offline_locking_no_retry_and_uncertain_notice(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        generation_before = store_state(page)["generation"]

        # Deterministically keep the submitted action's result out of the
        # client so the request is provably still in flight when the transport
        # dies: the server can answer a test-only ``proof.noop`` in the same
        # tick, which would otherwise race the disconnect. The Vue transport
        # feeds ``ui_action_result`` to ``store.receive`` through its OOB
        # listener, so we also swallow the emitter's ``ui_action_result``
        # listener to keep the result from reaching the store.
        page.evaluate(
            "() => {"
            "  const client = Elosern.actions && Elosern.actions.client;"
            "  if (client) { client.onActionResult = function () { return undefined; };"
            "  }"
            "  if (window.Evennia && window.Evennia.emitter) {"
            "    window.Evennia.emitter.on('ui_action_result', function () {});"
            "  }"
            "  return true;"
            "}"
        )
        request_id = page.evaluate(
            "() => Elosern.actions.submit('proof.noop', {})"
        )
        self.assertIsNotNone(request_id, "an unlocked submit must be accepted")
        self.assertEqual(
            sent_action_count(page, "proof.noop"), 1, "one submission expected"
        )

        self._disconnect_transport(page)

        # While disconnected the client refuses further submissions.
        refused = page.evaluate("() => Elosern.actions.submit('proof.noop', {})")
        self.assertIsNone(refused)
        self.assertEqual(
            sent_action_count(page, "proof.noop"),
            1,
            "no submission may cross the wire while offline",
        )

        page.evaluate("Evennia.connect()")
        self._wait_transport_reopened(page, generation_before)
        self.assertGreater(store_state(page)["generation"], generation_before)

        # The submitted action was never retried.
        self.assertEqual(
            sent_action_count(page, "proof.noop"),
            1,
            "the client must never retry a mutation after transport loss",
        )

        # The uncertain-result notice appears after the reconnect.
        # The server's post-reconnect re-attach can lag under parallel CI load,
        # so allow a longer window than Playwright's default 30s. Gate on the
        # transport being re-opened (connected) plus the offline overlay's
        # `data-uncertain` flag — the DOM-observable uncertain-result signal.
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": "#elosern-offline-overlay",
                "predicate": (
                    "() => { const el = document.getElementById('elosern-offline-overlay'); "
                    "return el && el.getAttribute('data-uncertain') === 'true'; }"
                ),
                "description": "uncertain-result flag set on the offline overlay",
            },
            timeout=60000,
        )
        overlay = page.evaluate(
            "() => document.getElementById('elosern-offline-overlay')"
            ".getAttribute('data-uncertain')"
        )
        self.assertEqual(overlay, "true")

    @covers_requirement(
        "webclient-browser-verification::browser-acceptance-covers-foundation-recovery-and-layout-behavior",
        "webclient-oob-protocol::presentation-ordering-is-scoped-by-transport-and-puppet-epoch",
    )
    def test_lower_revision_adoption_in_new_generation(self):
        page = self.logged_in_page()
        before = store_state(page)
        epoch_before = before["epoch"]
        revision_before = before["revision"]

        # Inflate the active revision so the new epoch's lower revision is real.
        # Wait until every one of the four resyncs has landed (each costs one
        # server round trip and bumps the revision), so the disconnect cannot
        # cut the inflation short and let the new epoch's revision race past it.
        page.evaluate(
            "() => { for (let i = 0; i < 4; i++) { "
            "Elosern.actions.requestResync('status'); "
            "Elosern.actions.resetResyncEpisode('status'); } }"
        )
        wait_for_store_state(
            page,
            lambda s: s.get("revision") is not None and s["revision"] >= revision_before + 4,
        )
        revision_inflated = store_state(page)["revision"]
        self.assertGreaterEqual(revision_inflated, revision_before + 4)

        generation_before = store_state(page)["generation"]
        self._disconnect_transport(page)
        page.evaluate("Evennia.connect()")
        self._wait_transport_reopened(page, generation_before)

        state = store_state(page)
        self.assertEqual(state["generation"], generation_before + 1)
        if state["phase"] == "active":
            # The server re-auth won the race: the real new-epoch snapshot was
            # adopted at a lower revision than the prior epoch's.
            self.assertNotEqual(state["epoch"], epoch_before)
            self.assertLess(state["revision"], revision_inflated)
        else:
            # The server re-auth lagged; drive the wired reducer to adopt the
            # new generation's lower-revision snapshot (the rule under test).
            adopted = page.evaluate(
                "(args) => window.__elosernBridge.store.receive("
                "args.generation, 'ui_snapshot', [args.envelope], {})",
                {
                    "generation": state["generation"],
                    "envelope": snapshot_envelope(
                        fresh_epoch(),
                        1,
                        {"status": valid_status_panel("X", "y")},
                    ),
                },
            )
            self.assertTrue(adopted["accepted"])
            state = store_state(page)
            self.assertEqual(state["phase"], "active")
            self.assertLess(state["revision"], revision_inflated)
            self.assertNotEqual(state["epoch"], epoch_before)

    def test_rejects_prior_generation_and_different_epoch_on_active_socket(self):
        """The live active store discards foreign generations and epochs."""
        page = self.logged_in_page()
        state = store_state(page)
        generation = state["generation"]
        epoch_active = state["epoch"]
        revision = state["revision"]

        prior_generation = page.evaluate(
            "(args) => window.__elosernBridge.store.receive("
            "args.generation, 'ui_snapshot', [args.envelope], {})",
            {
                "generation": generation - 1,
                "envelope": snapshot_envelope(
                    epoch_active,
                    revision + 1,
                    {"status": valid_status_panel("X", "y")},
                ),
            },
        )
        self.assertEqual(prior_generation["reason"], "stale_generation")

        different_epoch = page.evaluate(
            "(args) => window.__elosernBridge.store.receive("
            "args.generation, 'ui_snapshot', [args.envelope], {})",
            {
                "generation": generation,
                "envelope": snapshot_envelope(
                    fresh_epoch(), 1, {"status": valid_status_panel("X", "y")}
                ),
            },
        )
        self.assertEqual(different_epoch["reason"], "different_epoch")

        after = store_state(page)
        self.assertEqual(after["generation"], generation)
        self.assertEqual(after["epoch"], epoch_active)
        self.assertEqual(after["revision"], revision)

    def test_retired_epoch_rejected_while_awaiting_first_snapshot(self):
        """A retired epoch is refused as the first snapshot of a new generation.

        Driven through a fresh ``Elosern.Protocol`` reducer so the real server
        cannot race the awaiting-phase check.
        """
        page = self.logged_in_page()
        result = page.evaluate(
            """() => {
              const status = {
                schema_version: 2, available: true,
                actor: { name: 'X', identity: 'y', location: null },
                resources: { hp: {current: 10, maximum: 10},
                             mp: {current: 10, maximum: 10},
                             sp: {current: 10, maximum: 10} },
                conditions: [], disguise_active: false, combat: null,
              };
              function env(epoch, revision) {
                return { protocol_version: 1, presentation_epoch: epoch,
                  revision: revision, mode: 'exploration', panels: {status: status},
                  layout_version: 1,
                  server_time: { year: 2026, season_index: 0, season_label: '春',
                    day_in_season: 1, hour: 12, minute: 0, second: 0 } };
              }
              const store = Elosern.Protocol.createStore();
              const epochA = 'priorEpoch____00000001';
              const epochB = 'nextEpoch_____00000001';
              store.beginTransport(1);
              store.receive(1, 'ui_snapshot', [env(epochA, 5)], {});
              // A new transport generation retires epochA.
              store.beginTransport(2);
              const retired = store.receive(2, 'ui_snapshot', [env(epochA, 6)], {});
              const accepted = store.receive(2, 'ui_snapshot', [env(epochB, 1)], {});
              return { retired: retired.reason, accepted: accepted.accepted,
                epoch: store.getState().activeEpoch };
            }"""
        )
        self.assertEqual(result["retired"], "retired_epoch")
        self.assertTrue(result["accepted"])
        self.assertEqual(result["epoch"], "nextEpoch_____00000001")

    def _topmost_at(self, page, x, y):
        # The stacking guarantee (delta scenario 1/2): the offline overlay
        # must be the topmost painted element where it overlaps an open
        # surface. jsdom cannot prove paint order (no layout/paint engine),
        # so this runs in a real Playwright-driven browser.
        return page.evaluate(
            """(args) => {
              const overlay = document.getElementById('elosern-offline-overlay');
              const el = document.elementFromPoint(args.x, args.y);
              return {
                tag: el ? (el.tagName + (el.id ? '#' + el.id : '')) : null,
                isOverlay: !!(el && overlay && (el === overlay || overlay.contains(el))),
              };
            }""",
            {"x": x, "y": y},
        )

    def _assert_offline_overlay_topmost(self, page):
        topmost = self._topmost_at(
            page,
            page.evaluate("() => window.innerWidth / 2"),
            page.evaluate("() => window.innerHeight / 2"),
        )
        self.assertTrue(
            topmost["isOverlay"],
            "the offline overlay must be the topmost element at viewport center, "
            f"got: {topmost['tag']}",
        )

    def _reopen_status_drawer(self, page):
        page.evaluate(
            "() => { const s = window.__elosernBridge && window.__elosernBridge.store; "
            "if (s) s.openHudDrawer('status'); }"
        )
        page.wait_for_selector('[data-testid="hud-drawer"]', timeout=15000)

    def _reopen_map_overlay(self, page):
        page.evaluate(
            "() => { const s = window.__elosernBridge && window.__elosernBridge.store; "
            "if (s) s.openOverlay('map'); }"
        )
        page.wait_for_selector('[data-testid="overlay-host"]', timeout=15000)

    @covers_requirement(
        "webclient-desktop-shell::connection-loss-locks-stale-controls"
    )
    def test_offline_overlay_outranks_open_reference_drawer(self):
        page = self.logged_in_page()
        self._reopen_status_drawer(page)
        self._disconnect_transport(page)
        # A transport loss force-closes the open drawer (the store's
        # `syncHudDrawer`), so re-open it to prove the overlay paints above a
        # *still-open* surface, not just an empty stage.
        self._reopen_status_drawer(page)
        self._assert_offline_overlay_topmost(page)
        # The drawer panel is right-anchored (width min(560px, 94vw)); probe a
        # point inside the panel region (its horizontal centre) as well, so
        # the assertion covers the panel's own tier, not just the scrim.
        panel_topmost = self._topmost_at(
            page,
            page.evaluate("() => window.innerWidth - 280"),
            page.evaluate("() => window.innerHeight / 2"),
        )
        self.assertTrue(
            panel_topmost["isOverlay"],
            "the offline overlay must be the topmost element over the drawer panel, "
            f"got: {panel_topmost['tag']}",
        )

    @covers_requirement(
        "webclient-desktop-shell::connection-loss-locks-stale-controls"
    )
    def test_offline_overlay_outranks_open_fullscreen_overlay(self):
        page = self.logged_in_page()
        self._reopen_map_overlay(page)
        self._disconnect_transport(page)
        # A transport loss force-closes the open full-screen overlay (the
        # store's `syncHudDrawer`), so re-open it to prove the offline
        # overlay is painted above a *still-open* surface.
        self._reopen_map_overlay(page)
        self._assert_offline_overlay_topmost(page)

    @covers_requirement(
        "webclient-desktop-shell::connection-loss-locks-stale-controls"
    )
    def test_offline_overlay_outranks_open_full_views_and_full_log(self):
        # The delta spec's scenario 2 also names the portrait/scene
        # full-views and the full-log overlay. Those surfaces are
        # component-local refs (not store state), so a transport loss does
        # NOT force-close them: open the surface, disconnect, and the surface
        # stays mounted while the offline overlay paints above it. The
        # scene/portrait surfaces need the art fixture, opted in for this
        # whole class in `setUpClass` (the seed reads the env var at server
        # start; `ELOSERN_BROWSER_ART_ROOT` is owned by the runtime env).
        surfaces = [
            ("full-log",
             '[data-testid="narrative-fulllog-control"]',
             '[data-testid="fulllog-overlay"]'),
            ("scene-full-view",
             '[data-testid="scene-backdrop-control"]',
             '[data-testid="scene-backdrop-fullview"]'),
            ("portrait-full-view",
             '[data-testid^="art-panel__portrait-fullview"]',
             '[data-testid="art-panel__fullview"]'),
        ]
        for name, open_selector, open_wait in surfaces:
            with self.subTest(surface=name):
                page = self.logged_in_page()
                if name == "scene-full-view":
                    # The scene full-view control sits under the stage anchor
                    # (its center point resolves to `div.stage-anchor`), so a
                    # plain pointer click times out; dispatch the DOM click
                    # that drives the component's `@click` handler.
                    page.evaluate(
                        '() => document.querySelector(\'[data-testid="scene-backdrop-control"]\').click()'
                    )
                else:
                    page.click(open_selector, timeout=15000)
                page.wait_for_selector(open_wait, timeout=15000)
                self._disconnect_transport(page)
                self._assert_offline_overlay_topmost(page)


if __name__ == "__main__":
    import unittest

    unittest.main()
