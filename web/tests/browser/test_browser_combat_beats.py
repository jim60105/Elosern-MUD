"""A combat round plays beat by beat (webclient-combat-beat-queue, C13b).

Each journey boots its own isolated server with a real combat session and casts
exactly one basic attack through the live dock, then reads the published
playback, the message window, and the vitals through the committed store. No
assertion is made against elapsed wall time: the journeys poll the store's own
committed slices, so a slow runner can only lengthen a window, never skip one.
"""

from __future__ import annotations

import time

from tools.spec_traceability import covers_requirement
from web.browser_support.browser_fixtures_data import combat_journey_values

from ._journey_support import _press
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    evaluate_tolerating_navigation,
    focus_action_dock,
    install_outbound_recorder,
    sent_action_count,
    store_state,
    store_state_or_none,
    wait_for_page_shown,
    wait_for_presentation_settled,
    wait_for_shell_active,
)
from .harness import ManagedServerTearDownMixin

# The closing line `world.rules.combat_result.CONTINUE_MESSAGE` sends after a
# settled ordinary round; it is the first line after the beats.
ROUND_CLOSING_LINE = "行動完成，繼續戰鬥。"


class CombatBeatsBrowserTest(ManagedServerTearDownMixin, BrowserAcceptanceTest):
    """One basic attack per journey against a dedicated isolated server.

    An active combat session leaves the Evennia server session in a state a
    later fresh login on the same server cannot reuse cleanly, so these
    journeys never share a server with each other.
    """

    def setUp(self) -> None:
        from .harness import ManagedServer

        self.server = ManagedServer()
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    @classmethod
    def setUpClass(cls) -> None:
        # Each test boots its own isolated server; never the shared one.
        pass

    # -- seams ---------------------------------------------------------------

    def _engage(self, page) -> None:
        """Engage the boot mode's first living combat monster through text."""
        target = combat_journey_values()["engage_target"]
        page.evaluate("([t]) => Evennia.msg('text', [`engage ${t}`], {})", [target])
        self._wait_combat_mode(page)

    def _wait_combat_mode(self, page, timeout=30000) -> dict:
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            state = store_state(page)
            panel = state["panels"] and state["panels"].get("context_actions")
            if state["mode"] == "combat" and panel and panel.get("available") is True:
                return panel
            page.wait_for_timeout(250)
        raise AssertionError("combat mode never became available")

    def _combat_panel(self, page) -> dict:
        return store_state(page)["panels"]["context_actions"]

    def _ui_actions(self, page) -> list:
        sent = page.evaluate("window.__elosernSent || []")
        return [(cmd, args, kwargs) for cmd, args, kwargs in sent if cmd == "ui_action"]

    def _basic_attack_target_identity(self, page) -> str:
        for participant in self._combat_panel(page)["participants"]:
            if participant["team"] == "foes":
                return participant["identity"]
        raise AssertionError("no enemy participant")

    def _cast_basic_attack(self, page) -> str:
        """One basic attack through the dock: the attack opener, then the foe.

        The keyboard path only: the root's first item opens the target menu,
        and the foe's own row is focused by its key (the committed
        `target-<identity>` contract) rather than by a press count, because a
        synthetic preset arrives with a companion on the target frame.
        """
        self._wait_combat_mode(page)
        wait_for_presentation_settled(page)
        focus_action_dock(page)
        page.keyboard.press("Enter")  # attack (the root's first item) -> target menu
        page.wait_for_timeout(120)
        target = self._basic_attack_target_identity(page)
        focused = page.evaluate(
            "(key) => window.__elosernBridge.store.focusItemByKey(key)",
            f"target-{target}",
        )
        self.assertTrue(focused, "the target frame holds the foe's own row")
        page.keyboard.press("Enter")  # select the monster target
        page.wait_for_timeout(120)
        return target

    def _playback(self, page):
        return store_state(page).get("beatPlayback")

    def _wait_round(self, page, predicate, description: str, timeout: int = 30000) -> dict:
        """Poll the committed store until `predicate(view)` holds, returning the view."""
        deadline = time.monotonic() + timeout / 1000
        view = None
        while time.monotonic() < deadline:
            view = store_state_or_none(page)
            if view is not None and predicate(view):
                return view
            page.wait_for_timeout(100)
        raise AssertionError(f"{description}; view={view!r}")

    def _page_texts(self, page) -> list:
        """Turn every page of the response on screen with Enter, in order."""
        surface = page.locator('[data-testid="message-page"]')
        total = int(surface.get_attribute("data-pages") or "0")
        texts = []
        for index in range(total):
            wait_for_page_shown(page)
            texts.append(surface.inner_text())
            if index + 1 < total:
                page.focus('[data-testid="message-page"]')
                page.keyboard.press("Enter")
                page.wait_for_timeout(80)
        return texts

    # -- journeys ------------------------------------------------------------

    @covers_requirement("webclient-combat-menu::a-combat-round-plays-beat-by-beat")
    def test_round_pages_beats_at_off(self):
        """At `off` the round is text pages the reader turns, and never a lock."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        self._cast_basic_attack(page)

        # The published round carries the beats, is already done, and holds no
        # displayed hit points: nothing plays by itself at `off`.
        view = self._wait_round(
            page,
            lambda v: v.get("beatPlayback") is not None
            and v["beatPlayback"].get("phase") == "done",
            "the round never bound at the off level",
        )
        playback = view["beatPlayback"]
        self.assertFalse(playback["auto"], playback)
        self.assertEqual(playback["phase"], "done")
        self.assertEqual(playback["count"], len(self._beats(page)))
        self.assertIsNone(view.get("displayHp"))
        self.assertFalse(view["dispatch"]["beatLocked"])

        # The declared revision is accepted and the round is done, so the dock
        # accepts again; the attack is the only ui_action of the round.
        wait_for_presentation_settled(page)
        self.assertEqual(sent_action_count(page), 1)
        self.assertIsNone(store_state(page)["dispatch"]["inFlight"])

        texts = self._page_texts(page)
        beats = [beat["text"] for beat in self._beats(page)]
        # One page per beat, in the beats' order...
        index = 0
        for text in texts:
            if index < len(beats) and text.strip() == beats[index].strip():
                index += 1
        self.assertEqual(index, len(beats), f"beat pages in order; pages={texts!r}")
        # ...and the round's closing line follows them, in the log untouched.
        self.assertIn(ROUND_CLOSING_LINE, texts[-1])
        self.assertIn(ROUND_CLOSING_LINE, self._log_text(page))

    @covers_requirement("webclient-combat-menu::a-combat-round-plays-beat-by-beat")
    @covers_requirement("webclient-combat-menu::combat-results-update-canonical-panels-and-preserve-narrative-logs")
    @covers_requirement("webclient-contextual-hud::presentation-timing-never-gates-committed-state-or-input")
    def test_round_plays_and_skips_reduced(self):
        """At `reduced` the round plays itself, holds the dock, and a click ends it."""
        page = self.logged_in_page((1920, 1080), motion_level="reduced")
        self.assertEqual(
            page.evaluate("() => document.documentElement.getAttribute('data-motion')"),
            "reduced",
        )
        # The beat pause the script reads stays 400ms at `reduced` (design D2):
        # the level drops the motion, never the order or the pauses.
        self.assertEqual(
            page.evaluate(
                "() => getComputedStyle(document.documentElement)"
                ".getPropertyValue('--motion-beat').trim()"
            ),
            "400ms",
        )
        install_outbound_recorder(page)
        self._engage(page)
        self._cast_basic_attack(page)

        # The round binds and plays by itself: it is not done yet.
        self._wait_round(
            page,
            lambda v: v.get("beatPlayback") is not None
            and v["beatPlayback"].get("phase") != "done",
            "the round never played at the reduced level",
        )
        self.assertTrue(store_state(page)["dispatch"]["beatLocked"])
        # The dock is locked: an Enter on it submits nothing.
        focus_action_dock(page)
        before = sent_action_count(page)
        _press(page, "Enter")
        page.wait_for_timeout(250)
        self.assertEqual(sent_action_count(page), before, "a playing round refuses the dock")

        # The store's own index advances beat by beat.
        view = self._wait_round(
            page,
            lambda v: (
                (v.get("beatPlayback") or {}).get("index", 0) >= 1
                or (v.get("beatPlayback") or {}).get("phase") == "done"
            ),
            "the playing round neither advanced nor ended",
        )
        playback = view["beatPlayback"]
        self.assertTrue(
            playback["index"] >= 1 or playback["count"] == 1,
            f"the store's index never advanced: {playback!r}",
        )

        # A click on the message window ends the round at once.
        page.locator('[data-testid="message-window"]').click()
        view = self._wait_round(
            page,
            lambda v: v["beatPlayback"].get("phase") == "done",
            "the click did not end the round",
            timeout=5000,
        )
        self.assertFalse(view["dispatch"]["beatLocked"], "the playback lock cleared at once")
        # Every displayed value is the committed value again.
        self.assertIsNone(view["displayHp"])
        resources = view["panels"]["status"]["resources"]["hp"]
        numerals = page.locator('[data-testid="status-panel__gauge-value--hp"]').inner_text()
        self.assertEqual(numerals, f"{resources['current']} / {resources['maximum']}")
        # The command panel accepts again once the round has ended.
        wait_for_presentation_settled(page)
        self.assertIsNone(store_state(page)["dispatch"]["inFlight"])

    @covers_requirement("webclient-combat-menu::a-combat-round-plays-beat-by-beat")
    def test_reconnect_replays_no_round(self):
        """A reload after a round presents none of it again."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        self._cast_basic_attack(page)
        self._wait_round(
            page,
            lambda v: v.get("beatPlayback") is not None,
            "the round never bound before the reload",
        )

        page.reload()
        wait_for_shell_active(page)
        view = store_state(page)
        self.assertIsNone(view.get("beatPlayback"), "a reconnect presented no round")
        self.assertIsNone(view.get("displayHp"))
        self.assertFalse(view["dispatch"]["beatLocked"])
        # The window opens on the last page of the last response, fully shown.
        wait_for_page_shown(page)
        surface = page.locator('[data-testid="message-page"]')
        self.assertEqual(surface.get_attribute("data-page"), surface.get_attribute("data-pages"))
        self.assertIn(ROUND_CLOSING_LINE, self._log_text(page))

    # -- readers -------------------------------------------------------------

    def _beats(self, page) -> list:
        panel = store_state(page)["panels"].get("combat_beats")
        self.assertIsNotNone(panel, "the round's beats panel must be committed")
        self.assertTrue(panel["available"], panel)
        return panel["beats"]

    def _log_text(self, page) -> str:
        return evaluate_tolerating_navigation(
            page,
            "() => { const b = window.__elosernBridge;"
            " const lines = b && b.store && Array.isArray(b.store.narrative) ? b.store.narrative : null;"
            " return lines ? lines.map((l) => (l && l.text != null ? String(l.text) : '')).join('\\n') : ''; }",
        )
