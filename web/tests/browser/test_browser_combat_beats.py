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
    submit_combat_command,
    wait_for_page_shown,
    wait_for_presentation_settled,
    wait_for_shell_active,
    wait_for_store_state,
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

    def _cast_basic_attack(self, page) -> int:
        """Command the round's actors; returns the ui_action count.

        The player's own actor takes the keyboard path: the root's first item
        opens the target menu, and the foe's own row is focused by its key (the
        committed `target-<identity>` contract) rather than by a press count,
        because a synthetic preset arrives with a companion on the target frame.

        Under the v7 party protocol a round commits only when the durable draft
        holds every required actor's command (webclient-combat-menu: "Party
        protocol publishes bounded actor choices and durable progress"): one
        submission saves the draft (`draft_saved`, 指令已確認，等待其他成員) and
        the server republishes the next missing member as the requested actor.
        Every other member is therefore commanded too — with the non-damaging
        Defend tactic, so the round holds exactly one attack and the foe stays
        above its flee boundary (a second attack would cross it and settle the
        fight terminally instead of in an ordinary round).
        """
        self._wait_combat_mode(page)
        panel = self._wait_commandable(page)
        required = list(panel["draft"]["required_actor_ids"])
        self.assertTrue(required, "an active draft names its required actors")
        started_round = int(panel["session"]["round"])
        controlled = int(
            store_state(page)["panels"]["status"]["actor"]["identity"]
        )
        commands = 0
        for _actor in required:
            wait_for_presentation_settled(page)
            requested = int(self._wait_commandable(page)["choices"]["actor_id"])
            if commands == 0:
                self.assertEqual(
                    requested, controlled, "the player's own actor opens the round"
                )
                focus_action_dock(page)
                page.keyboard.press("Enter")  # attack (the first root item)
                page.wait_for_timeout(120)
                target = self._basic_attack_target_identity(page)
                focused = page.evaluate(
                    "(key) => window.__elosernBridge.store.focusItemByKey(key)",
                    f"target-{target}",
                )
                self.assertTrue(focused, "the target frame holds the foe's own row")
                page.keyboard.press("Enter")  # select the monster target
            else:
                submit_combat_command(page, {"key": "defend"}, kind="tactic")
            commands += 1
            # The command is admitted asynchronously: gate on the committed
            # panel showing it (the actor's own draft entry, or the round it
            # committed) before commanding the next member.
            wait_for_store_state(
                page,
                lambda s, a=requested: self._command_landed(s, a, started_round),
            )
        return commands

    @staticmethod
    def _command_landed(state: dict, actor_id: int, started_round: int) -> bool:
        """Whether one submitted command reached the committed presentation."""
        panel = (state.get("panels") or {}).get("context_actions") or {}
        if int((panel.get("session") or {}).get("round") or 0) > started_round:
            return True
        entries = ((panel.get("draft") or {}).get("entries")) or []
        return any(entry.get("actor_id") == actor_id for entry in entries)

    def _wait_commandable(self, page, timeout: int = 30000) -> dict:
        """Gate on the committed panel carrying the dock's draft and choices.

        The committed panel is not always the commandable form the walk drives:
        an active session is also publishable in the recovery form (`choices`
        and `draft` null, with no personal command surface; webclient-combat-
        menu: "Unreconstructable participant offers safe recovery"), and the
        engage transition can commit `mode: combat` while the exploration form
        is still committed. A transient read is never taken for the draft.
        """

        def _commandable(state: dict) -> bool:
            panel = (state.get("panels") or {}).get("context_actions") or {}
            return (
                state.get("mode") == "combat"
                and panel.get("available") is True
                and isinstance(panel.get("choices"), dict)
                and isinstance(panel.get("draft"), dict)
            )

        wait_for_store_state(page, _commandable, timeout=timeout)
        return self._combat_panel(page)

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
        commands = self._cast_basic_attack(page)

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
        # Nothing locks at `off`, so the command region shows no waiting cue.
        self.assertEqual(page.locator('[data-testid="action-dock-playback"]').count(), 0)

        # The declared revision is accepted and the round is done, so the dock
        # accepts again; the round's ui_actions are exactly the commands the
        # walk sent — the player's attack and, for every other required member,
        # the Defend tactic — and nothing else was sent.
        wait_for_presentation_settled(page)
        self.assertEqual(sent_action_count(page), commands)
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
    @covers_requirement("webclient-contextual-hud::playback-lock-is-visible-without-inventing-progress")
    def test_round_plays_and_skips_reduced(self):
        """At `reduced` the round plays itself, holds the dock, and a click ends it."""
        page = self.logged_in_page((1451, 790), motion_level="reduced")
        self.assertEqual(
            page.evaluate("() => document.documentElement.getAttribute('data-motion')"),
            "reduced",
        )
        # The beat pause the script reads stays 400ms at `reduced` (design D2):
        # the level drops the motion, never the order or the pauses. The
        # computed value is normalized (`0.4s`), so it is read the way the
        # script's reader reads it.
        self.assertEqual(
            page.evaluate(
                "() => { const raw = getComputedStyle(document.documentElement)"
                ".getPropertyValue('--motion-beat').trim();"
                " const m = /^(\\d*\\.?\\d+)(ms|s)$/.exec(raw);"
                " return m ? Number(m[1]) * (m[2] === 's' ? 1000 : 1) : 0; }"
            ),
            400,
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
        # The command region says it is waiting and offers the existing skip;
        # its decorative line claims no progress and stands still at reduced.
        cue = page.locator('[data-testid="action-dock-playback"]')
        cue.wait_for(state="visible", timeout=5000)
        self.assertIn("回合演出中", cue.inner_text())
        self.assertEqual(cue.locator('[data-testid="action-dock-playback-skip"]').count(), 1)
        self.assertNotRegex(cue.inner_text(), r"\d+\s*%")
        self.assertEqual(cue.locator('[role="progressbar"]').count(), 0)
        self.assertEqual(
            cue.locator(".action-dock__playback-line").evaluate(
                "el => getComputedStyle(el).animationDuration"
            ),
            "0s",
        )
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
        self.assertEqual(
            page.locator('[data-testid="action-dock-playback"]').count(), 0, "the cue clears with playback"
        )
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
        """A reload after a round presents none of it again.

        The reconnect snapshot carries the unavailable `combat_beats` form
        (C12 D4), so the new epoch carries no round at all: no beat page, no
        displayed hit point, and no playback lock, and the round's lines are
        gone with the old epoch rather than presented again.
        """
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
        # The new epoch carries no available round panel either.
        panel = view["panels"].get("combat_beats") or {}
        self.assertNotEqual(panel.get("available"), True, panel)
        # The window presents the response the server delivered after the
        # reconnect, fully shown; the pre-reload log is gone with the epoch, so
        # no line of the round survives to be paged again.
        wait_for_page_shown(page)
        surface = page.locator('[data-testid="message-page"]')
        self.assertNotEqual(surface.get_attribute("data-pages"), "0")
        self.assertTrue(surface.inner_text().strip(), "the window presents the response's text")
        self.assertNotIn(ROUND_CLOSING_LINE, self._log_text(page))

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
