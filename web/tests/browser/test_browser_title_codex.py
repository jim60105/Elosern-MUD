"""Handbook titles tab browser acceptance (handbook-titles-tab, task 5).

The 稱號冊 tool opens the 手帳 (the quest drawer) on its 稱號 tab, which renders
the committed ``title_codex`` v1 panel. Four deterministic journeys on one
dedicated managed server seeded with the ``ELOSERN_BROWSER_TITLES=1`` codex
fixture (two banked fixed titles, two epithets — the older auto-equipped —
and one pending nomination ballot):

* the tab renders the committed panel verbatim: the full title in the head,
  each banked medal on its category rail, the locked medal with its authored
  hint and a disabled equip, the ★ mark on exactly the equipped epithet, the
  server-computed ``can_remove`` flag alone deciding the 移除 control, and the
  hot 提名 rail entry;
* both equip paths dispatch exactly one ``title.equip`` and update the full
  title;
* the two-step removal cancels with nothing dispatched, a close attempt
  (Escape) while armed disarms instead of closing, the confirmation dispatches
  exactly one ``title.remove``, and the ballot answers with the numbered
  choice only;
* at both reference viewports the rail, list and detail columns fit the
  drawer body without horizontal overflow and no text is below ``--text-xs``.

TileWall owns each medal's option cell (``data-tile``); the
``handbook__medal--<key>`` testid marks the medal face inside it. Fixed seeded
state; no live LLM, Stable Diffusion, or other network service.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

from web.browser_support.browser_fixtures_data import title_codex_values

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    install_outbound_recorder,
    sent_action_count,
    wait_for_store_state,
)
from .harness import ManagedServer, ManagedServerTearDownMixin
from . import fixtures
from ._journey_support import _wait_mode
from .test_browser_input_narrative import _wait_inp_line

CODEX = title_codex_values()
#: The fixture banks this explicitly synthetic epithet as its auto-equipped
#: row (the seed banks the same two epithets in both boot modes); it is
#: authored test data and never the shipped starter declaration's spelling.
STARTER_EPITHET = "苔徑新客"
NEWEST_EPITHET = "破城先鋒"
NOMINEE = "夜襲之人"

TITLES = '[data-testid="handbook__titles"]'

#: The geometry probe: column boxes against the drawer body, horizontal
#: overflow of the list column, and the smallest visible text size against the
#: computed `--text-xs` (resolved through a probe element, since the custom
#: property itself is an unresolved calc() expression).
_GEOMETRY_PROBE = """
() => {
  const q = (sel) => document.querySelector(sel);
  const box = (el) => {
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height };
  };
  const titles = q('[data-testid="handbook__titles"]');
  const list = titles.querySelector('[data-testid="handbook__medals"]')
    || titles.querySelector('[data-testid="quest-drawer__list"]');
  const probe = document.createElement('span');
  probe.style.fontSize = 'var(--text-xs)';
  probe.textContent = 'x';
  titles.appendChild(probe);
  const floor = parseFloat(getComputedStyle(probe).fontSize);
  probe.remove();
  let smallest = null;
  let smallestText = null;
  const walker = document.createTreeWalker(titles, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    if (!node.textContent.trim()) continue;
    const parent = node.parentElement;
    if (!parent || parent.closest('[aria-hidden="true"]')) continue;
    const r = parent.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    const style = getComputedStyle(parent);
    if (style.visibility === 'hidden' || style.display === 'none') continue;
    const size = parseFloat(style.fontSize);
    if (smallest === null || size < smallest) {
      smallest = size;
      smallestText = node.textContent.trim();
    }
  }
  return {
    body: box(q('[data-testid="quest-drawer"]')),
    rail: box(titles.querySelector('[data-testid="handbook__titles-rail"]')),
    list: box(list),
    detail: box(titles.querySelector('[data-testid="handbook__detail"]')),
    listScroll: list ? { scroll: list.scrollWidth, client: list.clientWidth } : null,
    floor,
    smallest,
    smallestText,
  };
}
"""


def _codex_panel(state: dict) -> dict:
    return (state.get("panels") or {}).get("title_codex") or {}


class TitleCodexBrowserTest(ManagedServerTearDownMixin, BrowserAcceptanceTest):
    """Boots one dedicated codex-fixture server per test."""

    @classmethod
    def setUpClass(cls) -> None:
        # Each test boots its own isolated server; never the shared one.
        pass

    def setUp(self) -> None:
        runtime = fixtures.create_runtime()
        runtime.env["ELOSERN_BROWSER_TITLES"] = "1"
        self.server = ManagedServer(runtime=runtime)
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    # -- helpers ---------------------------------------------------------------

    def _ready_page(self, viewport=None, predicate=None):
        """A logged-in page whose committed codex satisfies ``predicate``."""
        page = self.logged_in_page(viewport) if viewport else self.logged_in_page()
        _wait_mode(page, "exploration")
        self._wait_codex(page, predicate or (lambda p: p.get("available") is True))
        return page

    def _open_titles(self, page):
        """Open the handbook on its titles tab through the 稱號冊 tool."""
        if page.locator(TITLES).count() == 0:
            page.locator('[data-testid="nav-tool-codex"]').click()
            page.wait_for_selector(TITLES, timeout=15000)

    def _rail(self, page, key):
        page.locator(f'[data-testid="handbook__titles-rail"] [data-tab-key="{key}"]').click()

    def _medal(self, page, key):
        return page.locator(f'{TITLES} [data-tile="{key}"]')

    def _row(self, page, display):
        return page.locator(f'{TITLES} [data-quest-id="{display}"]')

    def _testid(self, page, suffix):
        return page.locator(f'[data-testid="handbook__{suffix}"]')

    def _wait_codex(self, page, predicate, timeout=30000):
        wait_for_store_state(
            page, lambda s: predicate(_codex_panel(s)), timeout=timeout
        )

    def _active_testid(self, page):
        return page.evaluate(
            "document.activeElement && document.activeElement.getAttribute('data-testid')"
        )

    # -- journeys ---------------------------------------------------------------

    @covers_requirement(
        "title-system::the-codex-oob-payload-and-webclient-window-are-server-authored"
    )
    def test_codex_window_renders_rows_flags_and_ballot_tab_verbatim(self):
        """Full title, banked and locked medals, the ★ mark, can_remove, ballot."""
        page = self._ready_page(
            predicate=lambda p: p.get("available") is True and p.get("epithet_rows")
        )
        self._open_titles(page)
        self.assertEqual(
            page.locator('[data-testid="quest-drawer__top-tabs"] [aria-selected="true"]').get_attribute(
                "data-tab-key"
            ),
            "titles",
        )
        # The full title comes straight from the committed panel.
        self.assertIn(
            f"{CODEX['banked_displays'][0]}　{STARTER_EPITHET}",
            self._testid(page, "full-title").inner_text(),
        )

        # Each banked row is an unlocked medal on its own category rail; the
        # first banked row is the equipped one, so its equip is disabled.
        for index, category in enumerate(CODEX["banked_categories"]):
            key = CODEX["banked_keys"][index]
            self._rail(page, category)
            self.assertEqual(self._testid(page, f"medal--{key}").get_attribute("data-locked"), "false")
            self._medal(page, key).click()
            self.assertEqual(self._medal(page, key).get_attribute("aria-selected"), "true")
            self.assertIn(CODEX["banked_displays"][index], self._testid(page, "detail").inner_text())
        self._rail(page, CODEX["banked_categories"][0])
        self._medal(page, CODEX["banked_keys"][0]).click()
        self.assertEqual(self._testid(page, "equip").get_attribute("aria-disabled"), "true")

        # The locked row keeps its name, carries the authored hint, and its
        # equip is disabled.
        self._rail(page, CODEX["locked_category"])
        locked = self._testid(page, f"medal--{CODEX['locked_key']}")
        self.assertEqual(locked.get_attribute("data-locked"), "true")
        self.assertIn(CODEX["locked_display"], locked.inner_text())
        self._medal(page, CODEX["locked_key"]).click()
        detail = self._testid(page, "detail").inner_text()
        self.assertIn(CODEX["locked_display"], detail)
        self.assertIn(CODEX["locked_hint"], detail)
        self.assertEqual(self._testid(page, "equip").get_attribute("aria-disabled"), "true")

        # Epithets: the server's can_remove flag alone gates the control, and
        # exactly the equipped row carries the ★ mark.
        self._rail(page, "epithet")
        self._row(page, NEWEST_EPITHET).click()
        self.assertEqual(self._testid(page, "remove").count(), 1, "the newest, unequipped epithet is removable")
        self._row(page, STARTER_EPITHET).click()
        self.assertEqual(self._testid(page, "remove").count(), 0, "the equipped starter epithet renders no removal control")
        self.assertIn("★", self._row(page, STARTER_EPITHET).inner_text())
        self.assertNotIn("★", self._row(page, NEWEST_EPITHET).inner_text())

        # A pending ballot adds the hot 提名 rail entry and its nominee.
        self._rail(page, "ballot")
        self.assertIn(NOMINEE, self._row(page, NOMINEE).inner_text())
        self.assertEqual(self._testid(page, "ballot-accept").count(), 1)

    def test_both_equip_paths_swap_slots_and_update_the_preview(self):
        """One dispatch per equip, the typed-command echo, the live full title."""
        page = self._ready_page()
        install_outbound_recorder(page)
        self._open_titles(page)

        # Fixed path: equip from the detail footer dispatches exactly one
        # title.equip and the full title re-composes from the panel.
        second_key = CODEX["banked_keys"][1]
        second_display = CODEX["banked_displays"][1]
        self._rail(page, CODEX["banked_categories"][1])
        self._medal(page, second_key).click()
        self._testid(page, "equip").click()
        self.assertEqual(sent_action_count(page, "title.equip"), 1)
        self._wait_codex(
            page, lambda p: p["full_title"] == f"{second_display}　{STARTER_EPITHET}"
        )
        self.assertIn(f"{second_display}　{STARTER_EPITHET}", self._testid(page, "full-title").inner_text())

        # Epithet path: the same footer control on a banked row swaps the slot.
        self._rail(page, "epithet")
        self._row(page, NEWEST_EPITHET).click()
        self._testid(page, "equip").click()
        self.assertEqual(sent_action_count(page, "title.equip"), 2)
        self._wait_codex(page, lambda p: p["full_title"] == f"{second_display}　{NEWEST_EPITHET}")
        envelopes = [
            args[0]
            for cmdname, args, _kwargs in page.evaluate("window.__elosernSent || []")
            if cmdname == "ui_action"
            and args
            and args[0].get("action_id") == "title.equip"
        ]
        self.assertEqual(
            [env["payload"] for env in envelopes],
            [
                {"kind": "fixed", "identifier": second_key},
                {"kind": "epithet", "identifier": NEWEST_EPITHET},
            ],
        )
        # The input echo replays both typed commands in order.
        page.keyboard.press("Escape")
        page.wait_for_selector(TITLES, state="detached", timeout=15000)
        _wait_inp_line(page, 2, f"title equip epithet {NEWEST_EPITHET}", exact=True)

    def test_removal_card_cancels_then_confirms_and_the_ballot_answers(self):
        """Cancel and Escape dispatch nothing; confirm deletes one row; accept banks."""
        page = self._ready_page()
        install_outbound_recorder(page)
        self._open_titles(page)
        self._rail(page, "epithet")
        self._row(page, NEWEST_EPITHET).click()

        # Cancel: arming moves focus to cancel and dispatches NOTHING.
        self._testid(page, "remove").click()
        self.assertEqual(self._active_testid(page), "handbook__remove-cancel")
        self.assertIn("移除後無法恢復", self._testid(page, "action-reason").inner_text())
        self._testid(page, "remove-cancel").click()
        self.assertEqual(self._testid(page, "remove-confirm").count(), 0)
        self.assertEqual(sent_action_count(page), 0)

        # Escape while armed disarms instead of closing the drawer.
        self._testid(page, "remove").click()
        self.assertEqual(self._active_testid(page), "handbook__remove-cancel")
        page.keyboard.press("Escape")
        self.assertEqual(self._testid(page, "remove-confirm").count(), 0)
        self.assertEqual(page.locator(TITLES).count(), 1, "the armed close attempt keeps the drawer open")
        self.assertEqual(sent_action_count(page), 0)

        # Confirm: exactly one title.remove, and the committed panel loses
        # that one row.
        self._testid(page, "remove").click()
        self._testid(page, "remove-confirm").click()
        self.assertEqual(sent_action_count(page, "title.remove"), 1)
        self._wait_codex(
            page,
            lambda p: [row["display"] for row in p["epithet_rows"]] == [STARTER_EPITHET],
        )

        # Ballot: the numbered accept dispatches title.accept and banks the
        # chosen epithet as the newest row (no free text anywhere).
        self._rail(page, "ballot")
        self._row(page, NOMINEE).click()
        self._testid(page, "ballot-accept").click()
        self.assertEqual(sent_action_count(page, "title.accept"), 1)
        self._wait_codex(
            page,
            lambda p: p["pending_ballot"] == []
            and [row["display"] for row in p["epithet_rows"]] == [NOMINEE, STARTER_EPITHET],
        )
        page.keyboard.press("Escape")
        page.wait_for_selector(TITLES, state="detached", timeout=15000)
        _wait_inp_line(page, 2, "title accept 1", exact=True)

    def test_titles_tab_geometry_at_reference_viewports(self):
        """Three columns fit the drawer body, no horizontal scroll, no tiny text."""
        for viewport in ((1451, 790), (2560, 1440)):
            with self.subTest(viewport=viewport):
                page = self._ready_page(viewport)
                self._open_titles(page)
                page.wait_for_selector(f'{TITLES} [data-testid="handbook__detail"]', timeout=15000)
                for rail in (CODEX["banked_categories"][0], "epithet"):
                    self._rail(page, rail)
                    # Let the detail column's entrance animation settle.
                    page.evaluate("() => Promise.all(document.getAnimations().map((a) => a.finished))")
                    fit = page.evaluate(_GEOMETRY_PROBE)
                    body = fit["body"]
                    for name in ("rail", "list", "detail"):
                        column = fit[name]
                        self.assertIsNotNone(column, name)
                        self.assertGreater(column["width"], 0, name)
                        self.assertGreaterEqual(column["left"], body["left"] - 1, f"{rail}: {name} left of the body")
                        self.assertLessEqual(column["right"], body["right"] + 1, f"{rail}: {name} right of the body")
                        self.assertGreaterEqual(column["top"], body["top"] - 1, f"{rail}: {name} above the body")
                        self.assertLessEqual(column["bottom"], body["bottom"] + 1, f"{rail}: {name} below the body")
                    # Side by side, in order, without overlap.
                    self.assertLessEqual(fit["rail"]["right"], fit["list"]["left"] + 1)
                    self.assertLessEqual(fit["list"]["right"], fit["detail"]["left"] + 1)
                    self.assertLessEqual(
                        fit["listScroll"]["scroll"], fit["listScroll"]["client"], f"{rail} list scrolls horizontally"
                    )
                    self.assertGreaterEqual(
                        fit["smallest"], fit["floor"] - 0.01, f"text below --text-xs: {fit['smallestText']!r}"
                    )
