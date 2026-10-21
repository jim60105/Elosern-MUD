"""Managed-browser acceptance for the sleep-driven control handoff.

One real runtime per test: possess a lineup companion, let that controlled body
enter voluntary sleep (zero-time entry), read the textual offer, then confirm a
return to the owner or a transfer to an awake companion through the party
window's existing keyboard-activatable controls. A reload proves the committed
sleep and control state survive without replaying the transition.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    install_outbound_recorder,
    narrative_log_text,
    open_command_line,
    sent_action_count,
    store_state,
    wait_for_store_state,
)
from .harness import ManagedServer, ManagedServerTearDownMixin
from . import fixtures


class SleepHandoffBrowserTest(ManagedServerTearDownMixin, BrowserAcceptanceTest):
    """Boots one isolated runtime per test with the companion-lineup fixture."""

    @classmethod
    def setUpClass(cls) -> None:
        pass

    def setUp(self) -> None:
        runtime = fixtures.create_runtime()
        runtime.env["ELOSERN_BROWSER_EXPLORATION"] = "1"
        runtime.env["ELOSERN_BROWSER_SYNTH_CATALOGS"] = "1"
        runtime.env["ELOSERN_BROWSER_COMPANION_LINEUP"] = "1"
        runtime.env["ELOSERN_BROWSER_SLEEP_HANDOFF"] = "1"
        self.server = ManagedServer(runtime=runtime)
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    # --- helpers ---------------------------------------------------------

    def _wait_exploration_available(self, page, timeout=30000):
        def _exploration_available(state: dict) -> bool:
            panel = (state.get("panels") or {}).get("exploration") or {}
            return panel.get("available") is True

        wait_for_store_state(page, _exploration_available, timeout=timeout)

    def _wait_panel(self, page, name, predicate, timeout=30000):
        def _panel_ready(state: dict) -> bool:
            panel = (state.get("panels") or {}).get(name)
            return panel is not None and predicate(panel)

        wait_for_store_state(page, _panel_ready, timeout=timeout)

    def _select_party_member(self, page, member_id):
        entry = page.locator(f'[data-testid="member-rail__entry--{member_id}"]')
        entry.wait_for(timeout=30000)
        if entry.get_attribute("aria-current") != "true":
            entry.click()
        self._wait_panel(page, "party", lambda p: p.get("viewed_member_id") == member_id)
        self._wait_panel(page, "party_member", lambda p: p.get("member_id") == member_id)
        page.wait_for_selector(
            f'[data-testid="member-rail__entry--{member_id}"][aria-current="true"]',
            timeout=30000,
        )

    def _open_member_tab(self, page):
        page.evaluate("window.__elosernBridge.store.openHudDrawer('party')")
        page.locator('[data-testid="icon-tabs__tab--member"]').click()

    def _activate_keyboard(self, page, testid):
        button = page.locator(f'[data-testid="{testid}"]')
        button.wait_for(timeout=30000)
        page.wait_for_function(
            "(testid) => { const b = document.querySelector('[data-testid=\"' + testid + '\"]');"
            " return !!b && !b.disabled && b.getAttribute('aria-disabled') !== 'true'; }",
            arg=testid,
            timeout=30000,
        )
        # A native button: focusing it and pressing Enter must send exactly
        # what a pointer click would.
        button.press("Enter")

    def _wait_possess_label(self, page, label):
        """The action bar's possession control names the committed verdict."""
        page.wait_for_function(
            "(label) => { const b = document.querySelector('[data-testid=\"action-bar__btn--possess\"]');"
            " return !!b && b.innerText.trim() === label; }",
            arg=label,
            timeout=30000,
        )

    def _lawful_candidate(self, page, companion_ids):
        """Select each companion until one exposes a lawful handoff choice."""
        for member_id in companion_ids:
            self._open_member_tab(page)
            self._select_party_member(page, member_id)
            panel = (store_state(page)["panels"].get("party_member") or {})
            actions = (panel.get("companion") or {}).get("actions", [])
            if any(
                action["action_id"] == "explore.possess" and action["enabled"]
                for action in actions
            ):
                self._wait_possess_label(page, "附身")
                return member_id
        raise AssertionError("no awake co-located companion was offered")

    def _possess(self, page, member_id):
        self._open_member_tab(page)
        self._select_party_member(page, member_id)
        self._wait_panel(
            page,
            "party_member",
            lambda p: any(
                action["action_id"] == "explore.possess" and action["enabled"]
                for action in (p.get("companion") or {}).get("actions", [])
            ),
        )
        self._activate_keyboard(page, "action-bar__btn--possess")
        self._wait_panel(page, "possession_banner", lambda p: p.get("available"))

    def _sleep_until_offer(self, page):
        page.evaluate(
            "() => { const s = window.__elosernBridge && window.__elosernBridge.store; "
            "if (s && s.view && s.view.hudDrawer) s.closeHudDrawer(); }"
        )
        wait_for_store_state(page, lambda s: s.get("hudDrawer") is None)
        open_command_line(page)
        page.keyboard.type("sleep")
        page.keyboard.press("Enter")
        try:
            page.wait_for_function(
                "() => { const b = window.__elosernBridge;"
                " const lines = b && b.store && Array.isArray(b.store.narrative) ? b.store.narrative : [];"
                " return lines.some((l) => l && String(l.text || '').includes('可交接：')); }",
                timeout=30000,
            )
        except Exception as error:
            raise AssertionError(
                "no sleep handoff offer; narrative tail=%r"
                % narrative_log_text(page)[-2000:]
            ) from error
        return narrative_log_text(page)

    def _fatigue_row(self, page, identity):
        state = store_state(page)
        return next(
            row
            for row in state["panels"]["status"]["fatigue"]
            if row["identity"] == str(identity)
        )

    # --- journeys --------------------------------------------------------

    @covers_requirement(
        "webclient-possession-presentation::the-possession-controls-complete-the-action-round-trip"
    )
    @covers_requirement(
        "time-skip-commands::sleep-computes-its-own-duration-from-gauge-regen-capped-at-a-configured-maximum"
    )
    def test_keyboard_sleep_handoff_returns_control_and_survives_reload(self):
        page = self.logged_in_page()
        page.set_viewport_size({"width": 1451, "height": 790})
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        self._wait_panel(
            page, "party", lambda p: p.get("available") and len(p["slots"]) == 5
        )
        party = store_state(page)["panels"]["party"]
        player_id = int(store_state(page)["panels"]["status"]["actor"]["identity"])
        companions = [
            row["identity"] for row in party["slots"] if row.get("role") == "companion"
        ]
        # The fixture creates the rear lineup members co-located with the
        # character; a preset-bound front companion may sit elsewhere.
        sleeper_id = companions[1]

        self._possess(page, sleeper_id)
        offer = self._sleep_until_offer(page)
        self.assertIn("回到自己的身體（精神儲備 100%）", offer)
        row = self._fatigue_row(page, sleeper_id)
        self.assertEqual(row["stage"], "sleeping")
        self.assertTrue(row["restriction"])

        # Keyboard activation of the existing release control returns control
        # to the owner through the contextual confirmation.
        self._open_member_tab(page)
        self._select_party_member(page, sleeper_id)
        self._wait_possess_label(page, "解除附身")
        before = sent_action_count(page, "explore.possess_release")
        self._activate_keyboard(page, "action-bar__btn--possess")
        wait_for_store_state(
            page,
            lambda s: s.get("phase") == "active"
            and (
                ((s.get("panels") or {}).get("status") or {})
                .get("actor", {})
                .get("identity")
                == str(player_id)
            ),
        )
        self.assertGreaterEqual(
            sent_action_count(page, "explore.possess_release"), before + 1
        )
        self.assertFalse(store_state(page)["panels"]["possession_banner"]["available"])

        # Reload: the committed sleep posture and the returned control survive
        # without replaying any transition.
        page.reload()
        self._wait_exploration_available(page)
        self._wait_panel(
            page, "party", lambda p: p.get("available") and len(p["slots"]) == 5
        )
        self.assertFalse(store_state(page)["panels"]["possession_banner"]["available"])
        self.assertEqual(
            int(store_state(page)["panels"]["status"]["actor"]["identity"]), player_id
        )

    @covers_requirement(
        "companion-possession-transition::entering-possession-transfers-the-puppet-with-a-verify-then-recover-ladder"
    )
    def test_keyboard_sleep_handoff_transfers_to_an_awake_companion(self):
        page = self.logged_in_page()
        page.set_viewport_size({"width": 1451, "height": 790})
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        self._wait_panel(
            page, "party", lambda p: p.get("available") and len(p["slots"]) == 5
        )
        companions = [
            row["identity"]
            for row in store_state(page)["panels"]["party"]["slots"]
            if row.get("role") == "companion"
        ]
        sleeper_id = companions[1]

        self._possess(page, sleeper_id)
        offer = self._sleep_until_offer(page)
        self.assertIn("接手", offer)
        self.assertIn("精神儲備", offer)
        self.assertEqual(self._fatigue_row(page, sleeper_id)["stage"], "sleeping")

        candidate_id = self._lawful_candidate(
            page, [member for member in companions if member != sleeper_id]
        )
        before = sent_action_count(page, "explore.possess")
        self._activate_keyboard(page, "action-bar__btn--possess")
        self._wait_panel(
            page,
            "possession_banner",
            lambda p: p.get("available") and p.get("host_name")
            == next(
                row["display_name"]
                for row in store_state(page)["panels"]["party"]["slots"]
                if row["identity"] == candidate_id
            ),
        )
        self.assertGreaterEqual(sent_action_count(page, "explore.possess"), before + 1)

        # A reload runs the existing disconnect cleanup: control returns to the
        # owner and no dangling or doubled possession survives. The committed
        # sleep posture is untouched and never re-prompts.
        page.reload()
        self._wait_exploration_available(page)
        self._wait_panel(
            page, "party", lambda p: p.get("available") and len(p["slots"]) == 5
        )
        wait_for_store_state(
            page,
            lambda s: s.get("phase") == "active"
            and (
                ((s.get("panels") or {}).get("possession_banner") or {}).get(
                    "available"
                )
                is False
            ),
        )
        self.assertNotEqual(
            int(store_state(page)["panels"]["status"]["actor"]["identity"]),
            candidate_id,
        )
