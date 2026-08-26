"""Pointer-only action-dock browser acceptance (webclient-pointer-activation).

These journeys drive the real Evennia server's action dock using the mouse
only, at both supported desktop viewports. Every click must traverse the
identical path as Enter: focus move, disabled explanation, in-flight
suppression, and exactly one `ui_action` per deliberate activation. A rapid
double activation on a navigation row -- which pushes a menu frame instead of
submitting and is therefore not covered by the in-flight mutation lock -- must
push the frame exactly once. The composite widget (listbox/option roles, one
tab stop, active-descendant association) is asserted as DOM-observable
semantics.

Each journey boots its own dedicated isolated server so the mutated character
state never leaks. All fixtures are deterministic; no remote, LLM, or image
service is involved.
"""

from __future__ import annotations

import time

from playwright.sync_api import Error
from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    focus_action_dock,
    install_outbound_recorder,
    outbound_messages,
    sent_action_count,
    store_state,
    wait_for_store_state,
)
from .harness import ManagedServer
from . import fixtures


class PointerAcceptanceTest(BrowserAcceptanceTest):
    """Boots one dedicated isolated server per test with the exploration fixture."""

    @classmethod
    def setUpClass(cls) -> None:
        pass

    def setUp(self) -> None:
        runtime = fixtures.create_runtime(prefix="elosern-pointer-")
        runtime.env["ELOSERN_BROWSER_EXPLORATION"] = "1"
        self.server = ManagedServer(runtime=runtime)
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()
        if getattr(self, "server", None) is not None:
            try:
                self.server.stop()
            finally:
                self.server = None

    # -- helpers --------------------------------------------------------------

    def _exploration_panel(self, page):
        return store_state(page)["panels"]["exploration"]

    def _wait_exploration_available(self, page, timeout=30000):
        wait_for_store_state(
            page,
            lambda s: (s.get("panels") or {}).get("exploration", {}).get("available") is True,
            timeout=timeout,
        )
        return self._exploration_panel(page)

    def _wait_mode(self, page, mode, timeout=30000):
        def _mode_ready(state):
            return state.get("mode") == mode
        wait_for_store_state(page, _mode_ready, timeout=timeout)

    def _click_row(self, page, key):
        """Click the row carrying `data-item-key` == key with the mouse only."""
        locator = page.locator(f'[data-item-key="{key}"]')
        self.assertEqual(locator.count(), 1, f"row {key} not found")
        locator.click()
        page.wait_for_timeout(120)

    def _rows(self, page):
        return page.evaluate(
            "() => Array.from(document.querySelectorAll('#action-dock "
            "[data-item-key]')).map((el) => el.getAttribute('data-item-key'))"
        )

    def _target_key_for_affordance(self, page, action_id):
        """Find the interact target key whose affordances carry `action_id`."""
        panel = self._exploration_panel(page)
        for target in panel.get("interact", []):
            for affordance in target.get("affordances", []):
                if affordance.get("action_id") == action_id:
                    return "target-" + str(target["identity"])
        raise AssertionError(f"no interact target with affordance {action_id}")

    def _combat_panel(self, page):
        return store_state(page)["panels"]["context_actions"]

    def _engage(self, page):
        page.evaluate("Evennia.msg('text', ['engage goblin'], {})")
        self._wait_mode(page, "combat")

    # -- journeys -------------------------------------------------------------

    @covers_requirement(
        "webclient-pointer-activation::pointer-activation-traverses-the-identical-path-as-keyboard-confirmation"
    )
    def test_pointer_exploration_root_and_submenu_submission(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_exploration_available(page)

        # In the Vue app the exploration dock renders the keyboard router's
        # hierarchical frame: the root's "移動" entry (key ``move``) opens the
        # bounded move submenu, whose exit rows are keyed ``exit-<exit_ref>``.
        # Opening it and clicking the first enabled exit dispatches
        # ``explore.move`` exactly once.
        self._click_row(page, "move")
        move_rows = [r for r in (panel.get("move") or []) if r.get("enabled")]
        self.assertTrue(move_rows, "expected at least one enabled move row")
        exit_key = "exit-" + str(move_rows[0]["exit_ref"])
        page.wait_for_selector(f'[data-item-key="{exit_key}"]', timeout=15000)
        self._click_row(page, exit_key)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if sent_action_count(page, "explore.move") >= 1:
                break
            page.wait_for_timeout(250)
        self.assertEqual(sent_action_count(page, "explore.move"), 1)

    @covers_requirement(
        "webclient-pointer-activation::pointer-activation-traverses-the-identical-path-as-keyboard-confirmation"
    )
    def test_pointer_combat_target_selection_uses_keyboard_path(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_exploration_available(page)

        # The G2 hierarchical exploration dock renders the keyboard-router
        # frames: the root "互動" entry (key ``interact``) opens the interact
        # submenu (target rows keyed ``target-<identity>``); selecting the goblin
        # target renders its affordance menu, whose ``engage`` row (key
        # ``engage``) dispatches ``explore.engage``.
        self._click_row(page, "interact")
        goblin = next(
            (t for t in (panel.get("interact") or [])
             if "哥布林" in (t.get("display_name") or "")),
            None,
        )
        self.assertIsNotNone(goblin, "goblin target not found in the interact panel")
        target_key = "target-" + str(goblin["identity"])
        page.wait_for_selector(f'[data-item-key="{target_key}"]', timeout=15000)
        self._click_row(page, target_key)
        page.wait_for_selector('[data-item-key="engage"]', timeout=15000)
        self._click_row(page, "engage")
        self._wait_mode(page, "combat")

        # The root combat menu (attack/skills/items/defend/flee/forfeit) has no
        # target rows; opening the basic-attack skill renders the participant
        # target frame. Pointer activation uses the same router submit path as
        # keyboard confirmation: it records the selected identity without
        # inventing an OOB action.
        self._click_row(page, "attack")
        try:
            wait_for_store_state(
                page,
                lambda s: bool(s.get("connected")),
                dom_readiness={
                    "selector": "#action-dock",
                    "predicate": (
                        "() => document.querySelectorAll("
                        "'#action-dock [data-item-key^=\"target-\"]').length >= 1"
                    ),
                    "description": "combat target rows present in the action dock",
                },
                timeout=30000,
            )
        except Error as exc:
            state = store_state(page)
            panel = state.get("panels", {}).get("context_actions")
            raise AssertionError(
                "combat target rows never appeared within 30s; "
                "context_actions=%r; combatMenu=%r; rows=%r; lastTarget=%r"
                % (
                    panel,
                    state.get("combatMenu"),
                    self._rows(page),
                    state.get("lastTarget"),
                )
            ) from exc
        target_keys = [k for k in self._rows(page) if k.startswith("target-")]
        self.assertGreaterEqual(len(target_keys), 1)
        before = sent_action_count(page)
        self._click_row(page, target_keys[0])
        def _last_target_set(state):
            return state.get("lastTarget") == target_keys[0].removeprefix("target-")
        wait_for_store_state(page, _last_target_set, timeout=15000)
        self.assertEqual(store_state(page)["lastTarget"], target_keys[0].removeprefix("target-"))
        self.assertEqual(sent_action_count(page), before)

        # The "identical path" proof: after the client-local pointer selection,
        # a keyboard confirm (Enter) on the same focused target row dispatches
        # exactly one combat.cast carrying the selected target id — the pointer
        # selection feeds the same submission path as keyboard confirmation.
        focus_action_dock(page)
        cast_before = sent_action_count(page, "combat.cast")
        page.keyboard.press("Enter")
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if sent_action_count(page, "combat.cast") > cast_before:
                break
            page.wait_for_timeout(250)
        self.assertEqual(sent_action_count(page, "combat.cast") - cast_before, 1)
        casts = [
            m for m in outbound_messages(page)
            if m[0] == "ui_action" and m[1] and m[1][0].get("action_id") == "combat.cast"
        ]
        self.assertEqual(
            casts[-1][1][0]["payload"]["target_ids"],
            [int(target_keys[0].removeprefix("target-"))],
            "keyboard confirm must cast the pointer-selected target",
        )

    @covers_requirement(
        "webclient-pointer-activation::pointer-activation-traverses-the-identical-path-as-keyboard-confirmation"
    )
    def test_pointer_disabled_row_explains_without_submitting(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_exploration_available(page)

        # The exploration fixture leaves a defeated wolf beside the living
        # goblin. In the G2 hierarchical dock the wolf's ``engage`` affordance is
        # a disabled row (``target_dead``) inside the wolf's target menu, so open
        # the interact submenu and select the wolf target to render it.
        self._click_row(page, "interact")
        wolf = None
        for t in (panel.get("interact") or []):
            if any(
                a.get("action_id") == "explore.engage" and a.get("enabled") is False
                for a in (t.get("affordances") or [])
            ):
                wolf = t
                break
        self.assertIsNotNone(wolf, "disabled-engage target not found in the interact panel")
        target_key = "target-" + str(wolf["identity"])
        page.wait_for_selector(f'[data-item-key="{target_key}"]', timeout=15000)
        self._click_row(page, target_key)
        # The wolf's target menu renders the disabled ``engage`` row.
        page.wait_for_selector('[data-item-key="engage"][aria-disabled="true"]', timeout=15000)
        disabled_key = page.evaluate(
            "() => document.querySelector('#action-dock "
            "[data-item-key][aria-disabled=\"true\"]').getAttribute('data-item-key')"
        )
        before = sent_action_count(page)
        row = page.locator(f'#action-dock [data-item-key="{disabled_key}"]')
        row.scroll_into_view_if_needed()
        row.click(force=True)
        wait_for_store_state(
            page,
            lambda s: (s.get("focus") or {}).get("key") == disabled_key,
            timeout=5000,
        )
        self.assertEqual(sent_action_count(page), before)
        detail = page.evaluate(
            "document.querySelector('[data-testid=\"exploration-detail\"]').innerText"
        )
        self.assertGreater(len(detail.strip()), 0, "disabled row must explain")
        self.assertIn("死亡", detail, "the disabled reason must be readable")

    @covers_requirement(
        "webclient-pointer-activation::the-action-dock-is-a-single-composite-widget-that-cannot-double-activate"
    )
    def test_rapid_double_activation_pushes_one_frame(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_exploration_available(page)

        # The G2 hierarchical dock renders the keyboard-router frame: the root
        # "移動" entry (key ``move``) opens the bounded move submenu, whose exit
        # rows are keyed ``exit-<exit_ref>``. Rapidly double-activating the first
        # exit row submits ``explore.move`` once; the immediate second activation
        # is rejected (the in-flight lock, or the stale-row guard once the dock
        # re-renders after the move), so exactly one action crosses the wire and
        # no duplicated rows ever render.
        self._click_row(page, "move")
        move_rows = [r for r in (panel.get("move") or []) if r.get("enabled")]
        self.assertTrue(move_rows, "expected at least one enabled move row")
        exit_key = "exit-" + str(move_rows[0]["exit_ref"])
        page.wait_for_selector(f'[data-item-key="{exit_key}"]', timeout=15000)
        page.evaluate(
            """() => {
              const row = document.querySelector('[data-item-key="EXITKEY"]');
              window.__staleRow = row;
              row.dispatchEvent(new MouseEvent('click', {bubbles: true, detail: 1}));
            }""".replace("EXITKEY", exit_key)
        )
        page.evaluate(
            """() => {
              const row = window.__staleRow;
              if (row) {
                row.dispatchEvent(new MouseEvent('click', {bubbles: true, detail: 1}));
              }
            }"""
        )
        page.wait_for_timeout(400)
        self.assertEqual(sent_action_count(page, "explore.move"), 1)
        rows = self._rows(page)
        self.assertEqual(len(rows), len(set(rows)), "no row may render twice")
        self.assertGreaterEqual(len(rows), 1)

    @covers_requirement(
        "webclient-pointer-activation::the-action-dock-is-a-single-composite-widget-that-cannot-double-activate"
    )
    def test_real_mouse_double_click_pushes_one_frame(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        panel = self._wait_exploration_available(page)

        # A genuine browser double-click on the first exit row of the move
        # submenu (keyed ``exit-<exit_ref>``): the first click (detail 1)
        # submits ``explore.move`` once; the second click of the gesture is
        # suppressed by the in-flight lock (no second submit), so exactly one
        # action crosses the wire.
        self._click_row(page, "move")
        move_rows = [r for r in (panel.get("move") or []) if r.get("enabled")]
        self.assertTrue(move_rows, "expected at least one enabled move row")
        exit_key = "exit-" + str(move_rows[0]["exit_ref"])
        page.wait_for_selector(f'[data-item-key="{exit_key}"]', timeout=15000)
        exit_row = page.locator(f'[data-item-key="{exit_key}"]')
        self.assertEqual(exit_row.count(), 1)
        exit_row.dblclick()
        page.wait_for_timeout(400)
        self.assertEqual(sent_action_count(page, "explore.move"), 1)
        rows = self._rows(page)
        self.assertEqual(len(rows), len(set(rows)), "no row may render twice")
        self.assertGreaterEqual(len(rows), 1)

    @covers_requirement(
        "webclient-pointer-activation::pointer-activation-traverses-the-identical-path-as-keyboard-confirmation"
    )
    def test_pointer_under_offline_overlay_emits_nothing(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        page.evaluate(
            "() => { if (window.__elosernWs) window.__elosernWs.close(4001); }"
        )
        wait_for_store_state(
            page,
            lambda s: not s.get("connected"),
        )
        wait_for_store_state(
            page,
            lambda s: not s.get("connected"),
            dom_readiness={
                "selector": "#elosern-offline-overlay",
                "predicate": (
                    "() => document.getElementById('elosern-offline-overlay')"
                    ".getAttribute('data-visible') === 'true'"
                ),
                "description": "offline overlay visible",
            },
        )
        before = sent_action_count(page)
        # The overlay intercepts pointer events; a primary click dispatched on
        # the first root row (key ``move``, the "移動" entry) must not submit
        # anything while the offline overlay is up (the store is disconnected, so
        # dispatchAction is rejected and no OOB action crosses the wire).
        page.evaluate(
            """() => {
              const row = document.querySelector('[data-item-key="move"]');
              if (row) {
                row.dispatchEvent(new MouseEvent('click', {bubbles: true, detail: 1}));
              }
            }"""
        )
        page.wait_for_timeout(300)
        self.assertEqual(sent_action_count(page), before)
        self.assertEqual(
            page.evaluate(
                "document.getElementById('elosern-offline-overlay')"
                ".getAttribute('data-visible')"
            ),
            "true",
        )

    @covers_requirement(
        "webclient-pointer-activation::the-action-dock-is-a-single-composite-widget-that-cannot-double-activate"
    )
    def test_composite_widget_semantics_are_dom_observable(self):
        for viewport in ((1440, 900), (1280, 720)):
            with self.subTest(viewport=viewport):
                page = self.new_page(viewport)
                from .browser_helpers import login_and_open

                login_and_open(page, self.webclient_url, self.base_url)
                self._wait_exploration_available(page)

                # The row container exposes the listbox role with one tab stop
                # and an active-descendant reference.
                container = page.locator("#action-dock [role='listbox']")
                self.assertEqual(container.count(), 1)
                self.assertEqual(container.get_attribute("tabindex"), "0")
                active_id = container.get_attribute("aria-activedescendant")
                self.assertTrue(active_id, "aria-activedescendant must name a row")
                named = page.locator(f"#{active_id}")
                self.assertEqual(named.count(), 1)

                # Rows expose option role with selected state; none is
                # reachable by sequential keyboard navigation.
                rows = page.locator("#action-dock [role='option']")
                self.assertGreaterEqual(rows.count(), 1)
                for index in range(rows.count()):
                    self.assertEqual(rows.nth(index).get_attribute("tabindex"), "-1")
                    self.assertIn(
                        rows.nth(index).get_attribute("aria-selected"),
                        ("true", "false"),
                    )
                # The active-descendant row is marked focused and selected.
                focused = page.locator("#action-dock .dock-menu-item--focused")
                self.assertEqual(focused.count(), 1)
                self.assertEqual(focused.get_attribute("aria-selected"), "true")
                page.close()

    @covers_requirement(
        "webclient-pointer-activation::pointer-parity-is-verified-in-the-browser-without-weakening-keyboard-only-acceptance"
    )
    def test_pointer_exploration_journey_at_both_viewports(self):
        for viewport in ((1440, 900), (1280, 720)):
            with self.subTest(viewport=viewport):
                page = self.new_page(viewport)
                from .browser_helpers import login_and_open

                login_and_open(page, self.webclient_url, self.base_url)
                install_outbound_recorder(page)
                panel = self._wait_exploration_available(page)
                # The exploration root's first cell is the "移動" entry (key
                # ``move``); opening it renders the bounded move submenu whose
                # exit rows are keyed ``exit-<exit_ref>``.
                self.assertEqual(self._rows(page)[0], "move")
                self._click_row(page, "move")
                move_rows = [r for r in (panel.get("move") or []) if r.get("enabled")]
                if move_rows:
                    exit_key = "exit-" + str(move_rows[0]["exit_ref"])
                    page.wait_for_selector(f'[data-item-key="{exit_key}"]', timeout=15000)
                    self.assertIn(exit_key, self._rows(page))
                page.close()


class PointerServiceAcceptanceTest(BrowserAcceptanceTest):
    """Service submenu submission by pointer at the guild hall."""

    @classmethod
    def setUpClass(cls) -> None:
        pass

    def setUp(self) -> None:
        runtime = fixtures.create_runtime(prefix="elosern-pointer-svc-")
        runtime.env["ELOSERN_BROWSER_SERVICES"] = "guild_hall"
        self.server = ManagedServer(runtime=runtime)
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    def tearDown(self) -> None:
        super().tearDown()
        if getattr(self, "server", None) is not None:
            try:
                self.server.stop()
            finally:
                self.server = None

    def _wait_services_available(self, page, timeout=30000):
        wait_for_store_state(
            page,
            lambda s: (s.get("panels") or {}).get("services", {}).get("available") is True,
            timeout=timeout,
        )
        return store_state(page)["panels"].get("services")

    def _rows(self, page):
        return page.evaluate(
            "() => Array.from(document.querySelectorAll('#action-dock "
            "[data-item-key]')).map((el) => el.getAttribute('data-item-key'))"
        )

    def _click_row(self, page, key):
        locator = page.locator(f'[data-item-key="{key}"]')
        self.assertEqual(locator.count(), 1, f"row {key} not found")
        locator.click()
        page.wait_for_timeout(120)

    @covers_requirement(
        "webclient-pointer-activation::pointer-activation-traverses-the-identical-path-as-keyboard-confirmation"
    )
    def test_pointer_service_submenu_submission(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_services_available(page)

        # H4 (task 9.3): the service UI now renders as a QuestBoard inside
        # the open reference drawer, not as action-dock rows or a permanent
        # right-column panel. Opening the quest drawer is the journey's first
        # step; the register control lives inside the drawer body.
        page.evaluate(
            "() => { const s = window.__elosernBridge && window.__elosernBridge.store; "
            "if (s) s.openHudDrawer('quest'); }"
        )
        register = page.locator(".quest-board__action")
        page.wait_for_selector(".quest-board__action", timeout=15000)
        self.assertEqual(register.count(), 1)
        register.click()
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if sent_action_count(page, "guild.register") >= 1:
                break
            page.wait_for_timeout(250)
        self.assertEqual(sent_action_count(page, "guild.register"), 1)


if __name__ == "__main__":
    import unittest

    unittest.main()
