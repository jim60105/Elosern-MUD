"""Action-feedback toast queue browser evidence (webclient-action-feedback).

The Vitest suite is outside the spec-traceability index, so the two main-spec
requirements of the new `webclient-action-feedback` capability are evidenced
here, driving the real queue in a managed browser (the precedent for this
Python evidence-bridge pattern is `web/webclient/tests/test_vue_showcase_evidence.py`).
Requirement mapping (canonical IDs are slug-derived from the delta-spec titles;
the `covers_requirement` annotations are applied at the archive sync that
enters these IDs into the traceability index — the same procedure
test_vue_showcase_evidence.py documents):

- webclient-action-feedback::the-client-owns-a-bounded-action-feedback-toast-queue
    -> queue bounds/FIFO/click-dismiss/auto-dismiss/reload-empty journeys
- webclient-action-feedback::the-concept-apply-surfaces-exactly-one-confirmation-or-one-failure-toast
    -> the real-server `creation.concept` rejection journey (verbatim crit
       above the mounted creation overlay, overlay result region and feed
       channels unchanged)

Each journey boots its own dedicated isolated server (deterministic offline
fixtures; no LLM or image service involved). The failure journey dispatches a
real `creation.concept` with an invalid payload through the store's public
dispatch API, so the server's own payload validator answers with a real
rejected envelope carrying a server-authored message.
"""

from __future__ import annotations

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import wait_for_store_state
from .harness import ManagedServer
from . import fixtures
from .seed import CREATION_ACCOUNT_PASSWORD, CREATION_ACCOUNT_USERNAME

# The store's TOAST_LIFETIME_MS is 5200; journeys tolerate CI latency with a
# generous upper bound but must never see the entry linger much past it.
_AUTO_DISMISS_CEILING_MS = 12000


class ActionFeedbackBrowserTest(BrowserAcceptanceTest):
    """Boots one dedicated isolated server per test with a creation fixture."""

    @classmethod
    def setUpClass(cls) -> None:
        # Each test boots its own isolated server; never the shared one.
        pass

    def setUp(self) -> None:
        runtime = fixtures.create_runtime()
        runtime.env["ELOSERN_BROWSER_CREATION"] = "1"
        self.server = ManagedServer(runtime=runtime)
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    def tearDown(self) -> None:
        server = getattr(self, "server", None)
        super().tearDown()
        if server is not None:
            try:
                server.stop()
            finally:
                self.server = None

    # -- helpers --------------------------------------------------------------

    def _login_creation(self):
        page = self.new_page((1440, 900))
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

        def _creation_ready(state):
            if not state.get("connected") or state.get("mode") != "creation":
                return False
            panel = (state.get("panels") or {}).get("creation")
            return bool(panel and panel.get("available") is not False)

        wait_for_store_state(page, _creation_ready, timeout=60000)
        return page

    def _dispatch_bad_concept(self, page):
        """Real round-trip: an invalid concept payload gets the server's own
        rejected envelope (server-authored message, malformed payload)."""
        page.evaluate(
            "() => window.__elosernBridge.store.dispatchAction('creation.concept', {})"
        )

        captured = {}

        def _settled(state):
            result = state.get("lastActionResult")
            if result is not None and result.get("outcome") != "success":
                captured["result"] = result
                return True
            return False

        wait_for_store_state(page, _settled, timeout=30000)
        return captured["result"]

    def _toast_nodes(self, page):
        return page.locator('[data-testid^="feedback-toast-"]:not([data-testid="feedback-toast-queue"])')

    def _feed_err_count(self, page):
        return page.evaluate(
            "() => window.__elosernBridge.store.narrative.filter((l) => l.kind === 'err').length"
        )

    # -- journeys ---------------------------------------------------------------

    def test_failed_concept_surfaces_one_crit_toast_above_the_overlay(self):
        """One recognized concept failure = exactly one crit toast, verbatim,
        painted above the mounted creation overlay; the overlay result region
        and the narrative feed keep their existing behavior; the entry
        self-dismisses on the real clock."""
        page = self._login_creation()
        err_before = self._feed_err_count(page)
        result = self._dispatch_bad_concept(page)

        toast = self._toast_nodes(page)
        toast.first.wait_for(state="visible", timeout=10000)
        self.assertEqual(toast.count(), 1, "exactly one crit toast")
        entry = toast.first
        self.assertEqual(entry.get_attribute("data-tone"), "crit")
        self.assertEqual(entry.get_attribute("role"), "alert")
        # Verbatim: the toast title equals the server-authored envelope
        # message — read dynamically, never a hardcoded string. Compared
        # against the raw interpolated DOM text node (`.tt`'s last child):
        # `inner_text()` normalizes rendered whitespace, which a route to a
        # "verbatim" claim must not silently depend on. Only the template's
        # own lead space (the condensed indentation before the mustache) is
        # stripped — interior whitespace of the message stays compared.
        title_text = entry.locator(".tt").evaluate("el => el.lastChild.textContent")
        self.assertEqual(title_text.strip(), result["message"])
        # Additive channels unchanged: the overlay result region still shows
        # its own line, and the feed gains no err line while the overlay is
        # the presenting surface.
        overlay_line = page.locator('[data-testid="creation-result-message"]')
        self.assertEqual(overlay_line.count(), 1)
        self.assertEqual(overlay_line.text_content().strip(), result["message"])
        self.assertEqual(err_before, 0)
        self.assertEqual(
            self._feed_err_count(page), err_before,
            "the feed-line suppression is unchanged",
        )

        # Paint-order proof (the jsdom tiers cannot establish this): the
        # topmost painted element at the toast center lives inside the queue,
        # even though the creation overlay covers the same viewport region.
        box = entry.bounding_box()
        topmost = page.evaluate(
            """(args) => {
              const el = document.elementFromPoint(args.x, args.y);
              const queue = document.querySelector('[data-testid=\"feedback-toast-queue\"]');
              return { hit: !!el && !!queue && (el === queue || queue.contains(el)) };
            }""",
            {"x": box["x"] + box["width"] / 2, "y": box["y"] + box["height"] / 2},
        )
        self.assertTrue(topmost["hit"], "the crit toast paints above the creation overlay")

        # Self-dismiss on the real clock: gone shortly after its ~5200 ms
        # lifetime and never lingering past the ceiling.
        page.wait_for_selector(
            '[data-testid="feedback-toast-queue"] .toast',
            state="detached",
            timeout=_AUTO_DISMISS_CEILING_MS,
        )
        self.assertEqual(self._toast_nodes(page).count(), 0)

    def test_queue_bounds_order_dismiss_and_reload(self):
        """Cap 4 with FIFO eviction, monotonic ids, click dismisses exactly
        one entry, and a reload shows an empty queue (client-local state is
        never persisted)."""
        page = self._login_creation()

        # Everything after the pushes runs inside one CDP round-trip per
        # step: the entries' 5200 ms lifetime races the journey, so no
        # multi-call locator loop may sit between the click and the read.
        def _queue_state():
            return page.evaluate(
                """() => Array.from(
                     document.querySelectorAll(
                       '[data-testid^="feedback-toast-"]:not([data-testid="feedback-toast-queue"])'))
                   .map((el) => ({ id: el.getAttribute('data-testid').slice('feedback-toast-'.length),
                                   text: el.innerText }))"""
            )

        pushed = page.evaluate(
            """() => [1, 2, 3, 4, 5].map(
                 (n) => window.__elosernBridge.store.pushToast({ title: '佇列測試 ' + n, tone: 'info' }))"""
        )
        self.assertEqual(len(pushed), 5, "every push returns its id")
        self.assertEqual(pushed, sorted(pushed), "ids are monotonic")
        state = _queue_state()
        self.assertEqual(len(state), 4, "the queue caps at four")
        self.assertEqual([s["id"] for s in state], [str(i) for i in pushed[1:]],
                         "the oldest entry was evicted first (FIFO)")
        self.assertEqual([s["text"] for s in state],
                         ["佇列測試 2", "佇列測試 3", "佇列測試 4", "佇列測試 5"])

        # Click dismisses exactly that entry (the second visible one).
        clicked = state[1]["id"]
        page.evaluate(
            "(id) => document.querySelector(`[data-testid=\"feedback-toast-${id}\"]`).click()",
            arg=clicked,
        )
        page.wait_for_function(
            "(id) => !document.querySelector(`[data-testid=\"feedback-toast-${id}\"]`)",
            arg=clicked,
            timeout=5000,
        )
        remaining = _queue_state()
        self.assertEqual([s["text"] for s in remaining],
                         ["佇列測試 2", "佇列測試 4", "佇列測試 5"],
                         "click dismisses exactly the clicked entry")

        # Reload: the queue renders empty — nothing persisted it.
        page.reload()
        page.wait_for_selector('[data-testid="feedback-toast-queue"]', state="attached", timeout=30000)
        self.assertEqual(self._toast_nodes(page).count(), 0)
