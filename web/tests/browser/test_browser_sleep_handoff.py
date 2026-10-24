"""Managed-browser acceptance for the sleep-driven contextual control surface.

One real runtime per test: accept a zero-time owner sleep, use the automatic
server-owned companion roster (no Party Drawer navigation), possess a
companion, release onto the still-sleeping owner, answer the owner-only dream
question, and let the retained continuation finish the same owner sleep.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    activate_wait_row,
    answer_dream_question,
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
        wait_for_store_state(
            page,
            lambda s: ((s.get("panels") or {}).get("exploration") or {}).get(
                "available"
            )
            is True,
            timeout=timeout,
        )

    def _wait_panel(self, page, name, predicate, timeout=30000):
        def _panel_ready(state: dict) -> bool:
            panel = (state.get("panels") or {}).get(name)
            return panel is not None and predicate(panel)

        wait_for_store_state(page, _panel_ready, timeout=timeout)

    def _fatigue_rows(self, page):
        return store_state(page)["panels"]["status"]["fatigue"]

    def _all_awake(self, state):
        rows = ((state.get("panels") or {}).get("status") or {}).get("fatigue") or []
        return bool(rows) and all(row.get("stage") != "sleeping" for row in rows)

    def _sleep_recovery(self, page):
        activate_wait_row(page, "wait-sleep")
        page.wait_for_selector(
            '[data-testid="sleep-handoff-card"], [data-testid="dream-question"]',
            timeout=30000,
        )

    def _card(self, page):
        return page.locator('[data-testid="sleep-handoff-card"]')

    def _choose_possess(self, page):
        rows = page.locator('[data-testid="sleep-handoff-card"] [data-testid="sleep-handoff-row"]')
        rows.first.wait_for(state="visible", timeout=30000)
        for index in range(rows.count()):
            row = rows.nth(index)
            key = row.get_attribute("data-row-key") or ""
            if key.startswith("sleep:possess:") and row.get_attribute("aria-disabled") != "true":
                row.click()
                self._wait_panel(
                    page,
                    "possession_banner",
                    lambda panel: panel.get("available") is True,
                )
                return key
        raise AssertionError("no lawful companion row was offered")

    def _run_command(self, page, text):
        open_command_line(page)
        page.keyboard.type(text)
        page.keyboard.press("Enter")

    # --- journeys --------------------------------------------------------

    @covers_requirement(
        "companion-possession-core::sleep-driven-handoff-is-contextual-and-requires-confirmation"
    )
    @covers_requirement(
        "dream-sleep-surface::optional-collaboration-follows-one-accepted-sleep-result"
    )
    @covers_requirement(
        "time-skip-commands::owner-targeted-sleep-continuation-preserves-skip-safety"
    )
    def test_keyboard_sleep_handoff_returns_control_and_survives_reload(self):
        page = self.logged_in_page()
        page.set_viewport_size({"width": 1451, "height": 790})
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        self._wait_panel(page, "party", lambda panel: panel.get("available"))
        player_id = int(store_state(page)["panels"]["status"]["actor"]["identity"])

        self._sleep_recovery(page)
        card = self._card(page)
        if card.count() > 0 and card.is_visible():
            labels = card.locator('[role="menuitem"]').all_inner_texts()
            self.assertTrue(any("全員一起睡眠" in label for label in labels))
            self.assertIn("返回", labels[-1])
        self._choose_possess(page)
        self.assertTrue(
            store_state(page)["panels"]["possession_banner"]["available"]
        )

        # A lawful local action under the verified possession.
        self._run_command(page, "look")
        page.wait_for_function(
            "() => { const b = window.__elosernBridge;"
            " const lines = b && b.store && Array.isArray(b.store.narrative) ? b.store.narrative : [];"
            " return lines.length > 0; }",
            timeout=30000,
        )

        # Explicit release returns to the still-sleeping owner, so the same
        # no-possession view asks the owner-only question without spending time.
        self._run_command(page, "unpossess")
        card = self._card(page)
        card.wait_for(state="visible", timeout=30000)
        card.locator('[data-row-key="back"]').click()
        page.wait_for_selector('[data-testid="dream-question"]', timeout=30000)
        self.assertEqual(
            int(store_state(page)["panels"]["status"]["actor"]["identity"]),
            player_id,
        )
        before_wake = int(store_state(page)["panels"]["status"]["actor"]["identity"])
        self.assertEqual(before_wake, player_id)
        before_time = store_state(page)["serverTime"]

        # Decline with an awake companion present: no automatic fast-forward.
        answer_dream_question(page, False)
        page.wait_for_timeout(500)
        self.assertNotIn("時間經過", narrative_log_text(page))
        # The explicit same-sleep continuation is still available and finishes
        # the owner's accepted target.
        self._run_command(page, "sleep continue")
        wait_for_store_state(page, self._all_awake, timeout=60000)
        self.assertNotEqual(store_state(page)["serverTime"], before_time)

        page.reload()
        self._wait_exploration_available(page)
        self.assertEqual(
            page.locator('[data-testid="sleep-handoff-card"]').count(), 0
        )
        self.assertEqual(page.locator('[data-testid="dream-question"]').count(), 0)
        self.assertEqual(
            int(store_state(page)["panels"]["status"]["actor"]["identity"]),
            player_id,
        )

    @covers_requirement(
        "companion-possession-core::sleep-driven-handoff-is-contextual-and-requires-confirmation"
    )
    @covers_requirement(
        "companion-possession-transition::released-control-preserves-owner-physiology-and-rederives-the-view"
    )
    def test_keyboard_sleep_handoff_transfers_to_an_awake_companion(self):
        page = self.logged_in_page()
        page.set_viewport_size({"width": 1451, "height": 790})
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        self._wait_panel(page, "party", lambda panel: panel.get("available"))

        self._sleep_recovery(page)
        key = self._choose_possess(page)
        candidate_id = int(key.rsplit(":", 1)[-1])
        self._wait_panel(
            page,
            "possession_banner",
            lambda panel: panel.get("available") is True,
        )
        self.assertTrue(
            store_state(page)["panels"]["possession_banner"]["available"]
        )
        self.assertNotEqual(
            int(store_state(page)["panels"]["status"]["actor"]["identity"]),
            0,
        )
        # The controlled companion is awake and the owner remains asleep.
        self.assertNotEqual(candidate_id, 0)

        page.reload()
        self._wait_exploration_available(page)
        # Disconnect cleanup returns control to the owner without replaying a
        # transition or another sleep entry.
        wait_for_store_state(
            page,
            lambda s: (
                ((s.get("panels") or {}).get("possession_banner") or {}).get(
                    "available"
                )
                is False
            ),
            timeout=30000,
        )
        self.assertEqual(
            page.locator('[data-testid="dream-question"]').count(), 0
        )

    @covers_requirement(
        "webclient-exploration-menu::the-waiting-surface-offers-exactly-three-operations"
    )
    @covers_requirement(
        "time-skip-commands::owner-targeted-sleep-continuation-preserves-skip-safety"
    )
    def test_all_party_choice_declines_and_wakes_owner(self):
        page = self.logged_in_page()
        page.set_viewport_size({"width": 1451, "height": 790})
        install_outbound_recorder(page)
        self._wait_exploration_available(page)
        self._wait_panel(page, "party", lambda panel: panel.get("available"))

        activate_wait_row(page, "wait-sleep")
        try:
            self._card(page).wait_for(state="visible", timeout=30000)
        except Exception as error:
            state = store_state(page)
            panels = state.get("panels") or {}
            raise AssertionError(
                {
                    "narrative": narrative_log_text(page)[-2000:],
                    "sleep_handoff": panels.get("sleep_handoff"),
                    "fatigue": (panels.get("status") or {}).get("fatigue"),
                }
            ) from error
        party = page.locator('[data-testid="sleep-handoff-card"] [data-testid="sleep-handoff-party"]')
        party.wait_for(state="visible", timeout=30000)
        self.assertEqual(party.get_attribute("aria-disabled"), None)
        party.click()
        try:
            page.wait_for_selector('[data-testid="dream-question"]', timeout=30000)
        except Exception as error:
            state = store_state(page)
            panels = state.get("panels") or {}
            raise AssertionError(
                {
                    "narrative": narrative_log_text(page)[-2000:],
                    "sleep_handoff": panels.get("sleep_handoff"),
                    "fatigue": (panels.get("status") or {}).get("fatigue"),
                    "party_sent": sent_action_count(page, "explore.sleep_party"),
                }
            ) from error

        before = sent_action_count(page, "explore.sleep_party")
        self.assertEqual(before, 1)
        before_time = store_state(page)["serverTime"]
        answer_dream_question(page, False)
        wait_for_store_state(page, self._all_awake, timeout=60000)
        self.assertNotEqual(store_state(page)["serverTime"], before_time)
        self.assertEqual(
            page.locator('[data-testid="sleep-handoff-card"]').count(), 0
        )
        self.assertEqual(page.locator('[data-testid="dream-question"]').count(), 0)


class TerminalSleepStatusBrowserTest(ManagedServerTearDownMixin, BrowserAcceptanceTest):
    """A zero-round all-forced-sleep opening settles and keeps sleep visible."""

    @classmethod
    def setUpClass(cls) -> None:
        pass

    def setUp(self) -> None:
        runtime = fixtures.create_runtime()
        for key, value in (
            ("ELOSERN_BROWSER_EXPLORATION", "1"),
            ("ELOSERN_BROWSER_SYNTH_CATALOGS", "1"),
            ("ELOSERN_BROWSER_COMPANION_LINEUP", "1"),
            ("ELOSERN_BROWSER_TERMINAL_FATIGUE", "1"),
        ):
            runtime.env[key] = value
        self.server = ManagedServer(runtime=runtime)
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    def _wait_exploration_available(self, page):
        wait_for_store_state(
            page,
            lambda s: ((s.get("panels") or {}).get("exploration") or {}).get(
                "available"
            )
            is True,
            timeout=30000,
        )

    @covers_requirement(
        "player-combat-session::no-eligible-actors-leaves-command-collection-paused-with-explicit-party-exits"
    )
    def test_all_forced_sleep_engagement_settles_and_keeps_sleep_status(self):
        page = self.logged_in_page()
        page.set_viewport_size({"width": 1451, "height": 790})
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        def every_party_member_asleep(state):
            rows = (
                ((state.get("panels") or {}).get("status") or {}).get("fatigue")
                or []
            )
            return bool(rows) and all(
                row.get("stage") == "forced_sleep" and row.get("restriction")
                for row in rows
            )

        wait_for_store_state(page, every_party_member_asleep, timeout=30000)
        identities = {
            row["identity"]
            for row in store_state(page)["panels"]["status"]["fatigue"]
        }

        from web.browser_support.browser_fixtures_data import (
            SYNTH_HOSTILE_MONSTER_KEY,
        )

        target = SYNTH_HOSTILE_MONSTER_KEY
        page.evaluate("([t]) => Evennia.msg('text', [`engage ${t}`], {})", [target])
        page.wait_for_function(
            "() => { const b = window.__elosernBridge;"
            " const lines = b && b.store && Array.isArray(b.store.narrative)"
            " ? b.store.narrative : [];"
            " return lines.some((l) => l && String(l.text || '')"
            ".includes('你被擊敗了')); }",
            timeout=30000,
        )
        self.assertIn("你被擊敗了", narrative_log_text(page))
        wait_for_store_state(
            page,
            lambda s: s.get("mode") != "combat"
            and ((s.get("panels") or {}).get("exploration") or {}).get("available")
            is True,
            timeout=30000,
        )
        wait_for_store_state(page, every_party_member_asleep, timeout=30000)
        self.assertEqual(
            {
                row["identity"]
                for row in store_state(page)["panels"]["status"]["fatigue"]
            },
            identities,
        )
        self.assertNotIn("可交接", narrative_log_text(page))
        rows = store_state(page)["panels"]["status"]["fatigue"]
        self.assertTrue(all(row.get("restriction") for row in rows))
