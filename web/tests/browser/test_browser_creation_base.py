"""Shared character-creation browser fixture: the creation-dock login/panel/wait helpers every creation journey class inherits.
"""

from __future__ import annotations

from web.browser_support.browser_fixtures_data import (
    concept_placeholder_values,
    custom_draft_form_values,
)
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    focus_creation_action_dock,
    install_outbound_recorder,
    inject_update,
    outbound_messages,
    sent_action_count,
    store_state,
    wait_for_store_state,
)
from .harness import ManagedServer, ManagedServerTearDownMixin
from . import fixtures
from .seed import CREATION_ACCOUNT_PASSWORD, CREATION_ACCOUNT_USERNAME


class CreationBrowserTest(ManagedServerTearDownMixin, BrowserAcceptanceTest):
    """Boots one dedicated isolated server per test with a creation fixture.

    Boot mode: SHIPPED catalogs (explicit per-runtime override of the
    harness's synthetic default). The creation panel's wire vocabulary is
    frozen shipped schema: both endpoints of the contract -- the server
    presenter validator and the production client validator
    (``web/static/webclient/js/elosern/protocol.js``, the shipped browser
    itself) -- pin the race affinity trio and the eight lore elements as
    fixed wire constants (schema v5). The t_-only install therefore cannot
    present the creation panel at all, and relaxing either endpoint would
    be a production protocol redesign this change does not own. Every
    journey stays boot-mode agnostic anyway: races, subraces, budgets,
    allocations, preset cards, and placeholder values are all re-derived
    from the panel the running server presents -- never a literal.
    """

    CREATION_DRAFT = False
    CREATION_PRESET_DRAFT = False
    @classmethod
    def setUpClass(cls) -> None:
        # Each test boots its own isolated server; never the shared one.
        pass

    def setUp(self) -> None:
        runtime = fixtures.create_runtime()
        runtime.env["ELOSERN_BROWSER_SYNTH_CATALOGS"] = "0"
        runtime.env["ELOSERN_BROWSER_CREATION"] = "1"
        runtime.env["ELOSERN_DEBUG_UIACTION"] = "/tmp/uiaction_dbg.log"
        if self.CREATION_DRAFT:
            runtime.env["ELOSERN_BROWSER_CREATION_DRAFT"] = "1"
        if self.CREATION_PRESET_DRAFT:
            runtime.env["ELOSERN_BROWSER_CREATION_PRESET_DRAFT"] = "1"
        self.server = ManagedServer(runtime=runtime)
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    def tearDown(self) -> None:
        server = getattr(self, "server", None)
        self.server = None
        super().tearDown()
        self._stop_managed_server(server)

    # -- navigation helpers ---------------------------------------------------

    def _login_creation(self, viewport=None):
        """Open a guarded page, log in as the pending account, wait for creation."""
        page = self.new_page(viewport if viewport else (1440, 900))
        login_url = f"{self.base_url}/auth/login/"
        attempts = 4
        for attempt in range(attempts):
            page.goto(login_url)
            try:
                page.wait_for_selector("#id_username", timeout=20000)
                break
            except Exception:
                if attempt == attempts - 1:
                    raise
                page.wait_for_timeout(1500)
        page.fill("#id_username", CREATION_ACCOUNT_USERNAME)
        page.fill("#id_password", CREATION_ACCOUNT_PASSWORD)
        page.click('input[type="submit"]')
        page.wait_for_load_state("networkidle")
        page.goto(self.webclient_url)
        self._wait_creation_available(page)
        return page

    def _creation_panel(self, page):
        panels = store_state(page)["panels"]
        return panels.get("creation")

    def _panel_driven_draft_values(self, page, **kwargs):
        """(race, subrace, allocations) for a keyboard custom-form journey,
        derived from the panel the server is currently presenting — the
        advertised race/subrace the keyboard path lands on, with one exact
        budget spend."""
        return custom_draft_form_values(self._creation_panel(page), **kwargs)

    def _panel_valid_custom_payload(self, page, *, display_name, age=20, apparent_age=20):
        """A structurally valid custom payload for the CURRENT registry: the
        first advertised race with its first profile and one exact greedy
        budget spend — so protocol-level journeys (age gates, stale,
        duplicate) never name a shipped race key or a shipped budget split,
        and only the field under test deviates."""
        custom = self._creation_panel(page)["custom"]
        race_key = custom["races"][0]["key"]
        profile = next(p for p in custom["profiles"] if p["race"] == race_key)
        remaining = profile["budget"]
        allocations: dict[str, int] = {}
        for axis in profile["axes"]:
            value = min(axis["maximum"] - axis["minimum"], remaining)
            allocations[axis["axis"]] = value
            remaining -= value
        if remaining != 0:
            raise AssertionError("profile budget exceeds allocatable axis spans")
        return {
            "display_name": display_name,
            "age": age,
            "apparent_age": apparent_age,
            "race": race_key,
            "subrace": profile["subrace"],
            "background": None,
            "affinity_elements": None,
            "persona": None,
            "allocations": allocations,
        }

    def _dock_mode(self, page):
        return page.locator("#action-dock").get_attribute("data-mode", timeout=5000)

    def _wait_creation_available(self, page, timeout=60000):
        captured = {}

        def _creation_ready(state):
            if not state.get("connected") or state.get("mode") != "creation":
                return False
            panel = (state.get("panels") or {}).get("creation")
            if panel and panel.get("available") is True:
                captured["panel"] = panel
                return True
            return False

        wait_for_store_state(
            page,
            _creation_ready,
            dom_readiness={
                "selector": '[data-testid="creation-overlay"]',
                "predicate": (
                    "() => { const o = document.querySelector('[data-testid=\"creation-overlay\"]'); "
                    "const d = document.querySelector('#action-dock'); "
                    "if (!o) { return false; } "
                    "if (!d || d.getAttribute('data-mode') !== 'creation') { return false; } "
                    "const r = d.getBoundingClientRect(); "
                    "return r.width > 0 && r.height > 0 && d.offsetParent !== null; }"
                ),
                "description": "creation overlay mounted and creation-mode action-dock visible",
            },
            timeout=timeout,
        )
        return captured["panel"]

    def _wait_exploration(self, page, timeout=60000):
        def _exploration_ready(state):
            return state.get("connected") and state.get("mode") == "exploration"

        wait_for_store_state(page, _exploration_ready, timeout=timeout)

    def _wait_confirm_ready(self, page, timeout=30000):
        """Wait until the confirmation frame is mounted and the router unlocked.

        The confirm screen renders synchronously with the submit, but the
        router rejects Enter while the just-sent mutation is still in flight
        (``confirm()`` emits ``locked``); on a loaded runner the server
        response can arrive after the test's fixed delay and swallow the
        confirmation. Polling for an unlocked router with the confirm frame
        mounted makes the confirmation deterministic. The store gate covers
        the deterministic side: connected, phase active, mutations unlocked,
        and the just-sent action result committed to ``lastActionResult``.
        """
        def _confirm_ready(state):
            if not state.get("connected") or state.get("phase") != "active":
                return False
            if state.get("mutationsLocked") is True:
                return False
            return state.get("lastActionResult") is not None

        wait_for_store_state(
            page,
            _confirm_ready,
            dom_readiness={
                "selector": '[data-testid="creation-confirm"]',
                "predicate": (
                    "() => { const c = document.querySelector('[data-testid=\"creation-confirm\"]'); "
                    "return c !== null; }"
                ),
                "description": "creation confirmation frame mounted",
            },
            timeout=timeout,
        )

    def _wait_result(self, page, predicate, timeout=30000):
        captured = {}

        def _result_ready(state):
            result = state.get("lastActionResult")
            if result is not None and predicate(result):
                captured["result"] = result
                return True
            return False

        wait_for_store_state(page, _result_ready, timeout=timeout)
        return captured["result"]

    def _focus_dock(self, page):
        focus_creation_action_dock(page)

    def _sent_payloads(self, page, action_id):
        payloads = []
        for cmd, args, _kw in outbound_messages(page):
            if cmd == "ui_action" and args and args[0].get("action_id") == action_id:
                payloads.append(args[0].get("payload"))
        return payloads

    def _wait_draft_name_restored(self, page, timeout=30000):
        def _draft_restored(state):
            panel = (state.get("panels") or {}).get("creation") or {}
            draft = panel.get("draft")
            return bool(draft and draft.get("display_name") == "草稿角色")

        wait_for_store_state(
            page,
            _draft_restored,
            dom_readiness={
                "selector": '[data-testid="creation-field-displayName"]',
                "predicate": (
                    "() => { const f = document.querySelector('[data-testid=\"creation-field-displayName\"]'); "
                    "return f && f.value === '草稿角色'; }"
                ),
                "description": "creation name field shows the restored draft",
            },
            timeout=timeout,
        )
