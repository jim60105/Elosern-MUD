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
)


class ReconnectTest(BrowserAcceptanceTest):
    """Transport interruption and new-generation adoption through the real store."""

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
        page.wait_for_function(
            "() => { const s = Elosern.StateController.getState(); return !s.connected; }"
        )
        page.wait_for_function(
            "() => document.getElementById('elosern-offline-overlay')"
            ".getAttribute('data-visible') === 'true'"
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
        # tick, which would otherwise race the disconnect.
        page.evaluate(
            "() => {"
            "  const client = Elosern.actions && Elosern.actions.client;"
            "  if (!client) return false;"
            "  client.onActionResult = function () { return undefined; };"
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
        # so allow a longer window than Playwright's default 30s.
        page.wait_for_function(
            "() => (document.getElementById('elosern-action-live').textContent || '')"
            ".indexOf('無法確認') !== -1",
            timeout=60_000,
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
        epoch_before = before["activeEpoch"]
        revision_before = before["revision"]

        # Inflate the active revision so the new epoch's lower revision is real.
        # Wait until every one of the four resyncs has landed (each costs one
        # server round trip and bumps the revision), so the disconnect cannot
        # cut the inflation short and let the new epoch's revision race past it.
        page.evaluate(
            "() => { for (let i = 0; i < 4; i++) { "
            "Elosern.StateController.requestResync('status'); "
            "Elosern.StateController.resetResyncEpisode('status'); } }"
        )
        page.wait_for_function(
            "(r) => { const s = Elosern.StateController.getState(); "
            "return s.revision >= r; }",
            arg=revision_before + 4,
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
            self.assertNotEqual(state["activeEpoch"], epoch_before)
            self.assertLess(state["revision"], revision_inflated)
        else:
            # The server re-auth lagged; drive the wired reducer to adopt the
            # new generation's lower-revision snapshot (the rule under test).
            adopted = page.evaluate(
                "(args) => Elosern.StateController.receive("
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
            self.assertNotEqual(state["activeEpoch"], epoch_before)

    def test_rejects_prior_generation_and_different_epoch_on_active_socket(self):
        """The live active store discards foreign generations and epochs."""
        page = self.logged_in_page()
        state = store_state(page)
        generation = state["generation"]
        epoch_active = state["activeEpoch"]
        revision = state["revision"]

        prior_generation = page.evaluate(
            "(args) => Elosern.StateController.receive("
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
            "(args) => Elosern.StateController.receive("
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
        self.assertEqual(after["activeEpoch"], epoch_active)
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
                schema_version: 1, available: true,
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


if __name__ == "__main__":
    import unittest

    unittest.main()
