"""Shared fixture for the creation portrait browser journeys (creation-draft-portrait).

The managed runtime opts into the ``sd_control`` channel, so a journey
decides — through acknowledged commands, never a delay — when the queue
drains, whether the probe or the generation fails, and when a held
generation is released. Every wait is on committed store state. This module
holds no test method.
"""
from __future__ import annotations

import time

from .browser_helpers import (
    install_outbound_recorder,
    outbound_messages,
    sent_action_count,
    wait_for_store_state,
)
from .sd_control import CONTROL_ENV, SDControl
from .test_browser_creation_base import CreationBrowserTest

GENERATE = "creation.portrait.generate"
SLOT = '[data-testid="creation-portrait-slot"]'
STATUS = '[data-testid="creation-portrait-status"]'
GENERATE_BUTTON = '[data-testid="creation-portrait-generate"]'
DRAWER = '[data-drawer-key="creation-portrait"]'
PROMPT = f"{DRAWER} textarea"
SUBMIT = '[data-testid="gallery-generate__submit"]'
REFRESH_IN_DRAWER = '[data-testid="gallery-generate__refresh"]'


class CreationPortraitBrowserTest(CreationBrowserTest):
    """Creation journeys on a runtime whose art client follows sd_control."""

    CREATION_DRAFT = True

    def _configure_runtime(self, runtime) -> None:
        path = runtime.cache_dir / "sd-control.json"
        self.control = SDControl(path)
        runtime.env[CONTROL_ENV] = str(path)
        runtime.env["ELOSERN_BROWSER_SD_CLIENT"] = (
            "web.tests.browser.fake_sd_client.ControlledSDWebUIClient"
        )

    # -- helpers ------------------------------------------------------------

    def _open_custom(self, viewport=None):
        page = self._login_creation(viewport)
        install_outbound_recorder(page)
        self._wait_creation_available(page)
        if page.locator(SLOT).count() == 0:
            page.click('[data-testid="creation-mode-custom"]')
        page.locator(SLOT).wait_for(state="visible", timeout=15000)
        return page

    def _portrait(self, page):
        return (self._creation_panel(page) or {}).get("portrait") or {}

    def _wait_portrait(self, page, status, timeout=60000):
        def _committed(state):
            panel = (state.get("panels") or {}).get("creation") or {}
            return (panel.get("portrait") or {}).get("status") == status

        wait_for_store_state(
            page,
            _committed,
            dom_readiness={
                "selector": STATUS,
                "predicate": (
                    "() => { const s = document.querySelector('[data-testid=\"creation-portrait-status\"]'); "
                    f"return !!s && s.getAttribute('data-state') === '{status}'; }}"
                ),
                "description": f"portrait slot shows {status}",
            },
            timeout=timeout,
        )
        return self._portrait(page)

    def _open_drawer(self, page):
        page.click(GENERATE_BUTTON)
        page.locator(PROMPT).wait_for(state="visible", timeout=15000)
        # Opening the drawer sends nothing.
        self.assertEqual(sent_action_count(page, GENERATE), self._generate_count)

    def _submit(self, page, prompt=None):
        if prompt is not None:
            page.fill(PROMPT, prompt)
        before = len(self._requests(page))
        page.click(f"{DRAWER} {SUBMIT}")
        wait_for_store_state(
            page, lambda _s: len(self._requests(page)) == before + 1, timeout=15000
        )
        self._generate_count += 1
        return self._requests(page)[-1]

    def _requests(self, page):
        return [
            args[0]
            for cmd, args, _kw in outbound_messages(page)
            if cmd == "ui_action" and args and args[0].get("action_id") == GENERATE
        ]

    def _syncs(self, page):
        return sum(1 for cmd, _args, _kw in outbound_messages(page) if cmd == "ui_sync")

    def _result_for(self, page, request):
        return self._wait_result(page, lambda r: r.get("requestId") == request["request_id"])

    def _drawer_count(self, page):
        return page.locator(DRAWER).count()

    def _in_flight(self):
        return self.control.run("in_flight")["in_flight"]

    def _drain_once(self):
        """Run every queued job (the admitted portrait among them) to settlement."""
        self.assertTrue(self._in_flight(), "the admitted portrait job is queued")
        self.assertGreaterEqual(self.control.run("drain_sync").get("dispatched"), 1)

    def _drain_when_worker_free(self, timeout=60.0):
        """Drain once the worker slot is free (a held job has settled)."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.control.run("drain_sync").get("dispatched"):
                return
            time.sleep(0.1)
        raise AssertionError("the worker never freed its slot for the next job")

    def _generate_to_ready(self, page, prompt="月光下回頭凝視"):
        self._open_drawer(page)
        request = self._submit(page, prompt)
        self.assertEqual(self._result_for(page, request)["outcome"], "success")
        self._wait_portrait(page, "pending")
        self._drain_once()
        return self._wait_ready(page)

    def _wait_ready(self, page):
        try:
            return self._wait_portrait(page, "ready")
        except AssertionError as error:
            raise AssertionError(f"{error}; control cards={self.control.run('cards')}") from error

    def _activate_confirmed(self, page):
        self._wait_confirm_ready(page)
        page.click('[data-testid="creation-confirm-ok"]')
        self._wait_exploration(page)
        self.assertEqual(sent_action_count(page, "creation.activate"), 1)

    def _go_offline(self, page):
        """Every art service fails and the cached verdict says so."""
        self.control.set(probe="fail", generate="fail")
        self.assertIs(self.control.run("probe").get("ok"), False)
        page.evaluate("() => window.__elosernBridge.store.requestPresentationSync('manual')")
        self._wait_portrait(page, "unavailable")

    def setUp(self) -> None:
        self._generate_count = 0
        super().setUp()

