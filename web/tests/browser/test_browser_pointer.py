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

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    install_outbound_recorder,
    sent_action_count,
    store_state,
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
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            panel = self._exploration_panel(page)
            if panel and panel.get("available") is True:
                return panel
            page.wait_for_timeout(250)
        raise AssertionError("exploration panel never became available")

    def _wait_mode(self, page, mode, timeout=30000):
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            if store_state(page)["mode"] == mode:
                return
            page.wait_for_timeout(250)
        raise AssertionError(f"mode never became {mode}")

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
        self._wait_exploration_available(page)

        # Root rows are clickable; a navigation row (Move) pushes a frame.
        self._click_row(page, "move")
        self.assertIn("exit-", self._rows(page)[0])

        # The first exit submits explore.move exactly once.
        exit_keys = [k for k in self._rows(page) if k.startswith("exit-")]
        self.assertGreaterEqual(len(exit_keys), 1)
        self._click_row(page, exit_keys[0])
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if sent_action_count(page, "explore.move") >= 1:
                break
            page.wait_for_timeout(250)
        self.assertEqual(sent_action_count(page, "explore.move"), 1)

    @covers_requirement(
        "webclient-pointer-activation::pointer-activation-traverses-the-identical-path-as-keyboard-confirmation"
    )
    def test_pointer_combat_root_action_and_submenu_selection(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # Interact -> the goblin -> 戰鬥 (engage affordance), all by click.
        self._click_row(page, "interact")
        engage_target = self._target_key_for_affordance(page, "explore.engage")
        self._click_row(page, engage_target)
        self._click_row(page, "engage")
        self._wait_mode(page, "combat")

        # The combat dock renders the router's current frame as rows.
        page.wait_for_function(
            "() => document.querySelectorAll('#action-dock [data-item-key]').length >= 2",
            timeout=15000,
        )
        # Click a root action that opens a submenu: Skills.
        self._click_row(page, "skills")
        # The skills frame renders the router's current frame: one row per
        # owned skill, keyed by the skill key (fire_ball first).
        page.wait_for_function(
            "() => document.querySelector('[data-item-key=\"fire_ball\"]') !== null",
            timeout=15000,
        )
        self._click_row(page, "fire_ball")
        target_keys = [k for k in self._rows(page) if k.startswith("target-")]
        self.assertGreaterEqual(len(target_keys), 1)
        self._click_row(page, target_keys[0])
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if sent_action_count(page, "combat.cast") >= 1:
                break
            page.wait_for_timeout(250)
        self.assertEqual(sent_action_count(page, "combat.cast"), 1)

    @covers_requirement(
        "webclient-pointer-activation::pointer-activation-traverses-the-identical-path-as-keyboard-confirmation"
    )
    def test_pointer_disabled_row_explains_without_submitting(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # Engage combat through the dock, then click a disabled root row
        # (items): it explains in the combat detail pane and emits nothing.
        self._click_row(page, "interact")
        engage_target = self._target_key_for_affordance(page, "explore.engage")
        self._click_row(page, engage_target)
        self._click_row(page, "engage")
        self._wait_mode(page, "combat")
        page.wait_for_function(
            "() => document.querySelector('[data-item-key=\"items\"]') !== null",
            timeout=15000,
        )
        self.assertEqual(
            page.locator('[data-item-key="items"]').get_attribute("aria-disabled"),
            "true",
        )
        before = sent_action_count(page)
        # A disabled-row click focuses the row (re-rendering it) and explains
        # without submitting; dispatch the primary click directly.
        page.evaluate(
            """() => {
              const row = document.querySelector('[data-item-key="items"]');
              row.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, detail: 1}));
              row.dispatchEvent(new MouseEvent('click', {bubbles: true, detail: 1}));
            }"""
        )
        page.wait_for_timeout(300)
        self.assertEqual(sent_action_count(page), before)
        detail = page.evaluate(
            "document.getElementById('combat-detail').innerText"
        )
        self.assertGreater(len(detail.strip()), 0, "disabled row must explain")

    @covers_requirement(
        "webclient-pointer-activation::the-action-dock-is-a-single-composite-widget-that-cannot-double-activate"
    )
    def test_rapid_double_activation_pushes_one_frame(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # The first activation of a navigation row (Move) pushes the frame;
        # the re-render detaches the old rows synchronously. Dispatch a second
        # primary click on the now-detached row element: the stale-row guard
        # must reject it, so exactly one frame is pushed and one Escape
        # returns to the root.
        page.evaluate(
            """() => {
              const row = document.querySelector('[data-item-key="move"]');
              window.__staleRow = row;
              row.dispatchEvent(new MouseEvent('click', {bubbles: true, detail: 1}));
            }"""
        )
        page.wait_for_function(
            "() => document.querySelectorAll('#action-dock [data-item-key]').length >= 1"
        )
        self.assertIn("exit-", self._rows(page)[0])
        page.evaluate(
            """() => {
              const row = window.__staleRow;
              row.dispatchEvent(new MouseEvent('click', {bubbles: true, detail: 1}));
            }"""
        )
        page.wait_for_timeout(300)
        self.assertIn("exit-", self._rows(page)[0])
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        rows = self._rows(page)
        self.assertIn("move", rows)
        self.assertIn("look", rows)
        self.assertNotIn("exit-", rows)

    @covers_requirement(
        "webclient-pointer-activation::the-action-dock-is-a-single-composite-widget-that-cannot-double-activate"
    )
    def test_real_mouse_double_click_pushes_one_frame(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        # A genuine browser double-click on a navigation row: the first click
        # (detail 1) pushes the frame and re-renders the rows; the second
        # click of the gesture has detail 2 and must be rejected, so exactly
        # one frame is pushed and one Escape returns to the root.
        move = page.locator('[data-item-key="move"]')
        self.assertEqual(move.count(), 1)
        move.dblclick()
        page.wait_for_timeout(400)
        rows = self._rows(page)
        self.assertIn("exit-", rows[0])
        # The second click of the gesture did not activate a row in the new
        # frame (no submission, no second frame push).
        self.assertEqual(sent_action_count(page), 0)
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        rows = self._rows(page)
        self.assertIn("move", rows)
        self.assertIn("look", rows)
        self.assertNotIn("exit-", rows)

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
        page.wait_for_function(
            "() => { const s = Elosern.StateController.getState(); return !s.connected; }"
        )
        page.wait_for_function(
            "() => document.getElementById('elosern-offline-overlay')"
            ".getAttribute('data-visible') === 'true'"
        )
        before = sent_action_count(page)
        # The overlay intercepts pointer events; a primary click dispatched on
        # a row position must not submit anything.
        page.evaluate(
            """() => {
              const row = document.querySelector('[data-item-key="move"]');
              row.dispatchEvent(new MouseEvent('click', {bubbles: true, detail: 1}));
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
                focused = page.locator("#action-dock .dock-row.focused")
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
                self._wait_exploration_available(page)
                self._click_row(page, "move")
                self.assertIn("exit-", self._rows(page)[0])
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
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            panel = store_state(page)["panels"].get("services")
            if panel and panel.get("available") is True:
                return panel
            page.wait_for_timeout(250)
        raise AssertionError("services panel never became available")

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

        # Interact -> the guild staff host -> the navigate service entry
        # re-homes the services dock; the register row submits on click.
        self._click_row(page, "interact")
        target_keys = [k for k in self._rows(page) if k.startswith("target-")]
        self.assertGreaterEqual(len(target_keys), 1)
        self._click_row(page, target_keys[0])
        service_keys = [k for k in self._rows(page) if k.startswith("service-")]
        self.assertGreaterEqual(len(service_keys), 1)
        self._click_row(page, service_keys[0])

        # The re-homed services root renders rows; the first enabled row
        # (guild register) submits exactly one action on click.
        rows = self._rows(page)
        self.assertGreaterEqual(len(rows), 1)
        register = page.locator('[data-item-key="register"]')
        if register.count() == 1:
            register.click()
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if sent_action_count(page) >= 1:
                    break
                page.wait_for_timeout(250)
            self.assertEqual(sent_action_count(page), 1)


if __name__ == "__main__":
    import unittest

    unittest.main()
