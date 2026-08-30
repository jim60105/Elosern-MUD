"""Title-codex big-window browser acceptance (title-codex-removal, task 4.4).

Three deterministic journeys on one dedicated managed server seeded with the
``ELOSERN_BROWSER_TITLES=1`` codex fixture (two banked guild fixed titles,
two epithets — the older auto-equipped — and one pending nomination ballot):
the window renders the committed ``title_codex`` panel verbatim (locked rows
carry the authored hint, unlocked rows their equip affordance, the ★ mark and
the server-computed ``can_remove`` flag alone decides the 移除 control); both
equip paths dispatch exactly one ``title.equip`` and update the full-title
preview; the removal confirm card cancels with nothing dispatched, its
confirmation dispatches exactly one ``title.remove`` and shrinks the panel,
and the 提名中 tab answers the ballot with the numbered choice only. Fixed
seeded state; no live LLM, Stable Diffusion, or other network service.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    install_outbound_recorder,
    login_and_open,
    sent_action_count,
    store_state,
    wait_for_store_state,
)
from .harness import ManagedServer
from . import fixtures
from .test_browser_contextual_hud import _wait_mode
from .test_browser_input_narrative import _wait_inp_line


def _codex_panel(state: dict) -> dict:
    return (state.get("panels") or {}).get("title_codex") or {}


class TitleCodexBrowserTest(BrowserAcceptanceTest):
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

    def tearDown(self) -> None:
        super().tearDown()
        if getattr(self, "server", None) is not None:
            try:
                self.server.stop()
            finally:
                self.server = None

    # -- helpers ---------------------------------------------------------------

    def _opened_codex_page(self):
        """A logged-in page whose codex window is open on the fixture state."""
        page = self.logged_in_page()
        _wait_mode(page, "exploration")
        wait_for_store_state(
            page,
            lambda s: _codex_panel(s).get("available") is True,
        )
        page.locator('[data-testid="command-line-codex"]').click()
        page.wait_for_selector('[data-testid="title-codex-panel"]', timeout=15000)
        return page

    def _wait_codex(self, page, predicate, timeout=30000):
        wait_for_store_state(
            page, lambda s: predicate(_codex_panel(s)), timeout=timeout
        )

    # -- journeys ---------------------------------------------------------------

    @covers_requirement(
        "title-system::the-codex-oob-payload-and-webclient-window-are-server-authored"
    )
    def test_codex_window_renders_rows_flags_and_ballot_tab_verbatim(self):
        """Locked hints, unlocked affordances, the ★ mark, can_remove buttons."""
        page = self.logged_in_page()
        _wait_mode(page, "exploration")
        self._wait_codex(
            page, lambda p: p.get("available") is True and p.get("epithet_rows")
        )
        page.locator('[data-testid="command-line-codex"]').click()
        page.wait_for_selector('[data-testid="title-codex-panel"]', timeout=15000)
        # Header preview + counters come straight from the committed view.
        self.assertEqual(
            page.locator('[data-testid="title-codex-preview"]').inner_text(),
            "F級冒險者　南門新客",
        )
        panel = _codex_panel(store_state(page))
        # The two header spans render on separate DOM lines; join with one
        # space while preserving the U+3000 full-width separator.
        self.assertEqual(
            " ".join(
                page.locator('[data-testid="title-codex-header"]')
                .inner_text()
                .splitlines()
            ),
            f"F級冒險者　南門新客 已收集 {panel['unlocked']} / {panel['total']}",
        )

        # Guild tab (default): banked rows carry equip affordances.
        self.assertEqual(
            page.locator('[data-testid="title-codex-fixed-equip-g_f_rank"]').count(), 1
        )
        self.assertEqual(
            page.locator('[data-testid="title-codex-fixed-equip-g_e_rank"]').count(), 1
        )
        # Locked rows carry the authored hint and no equip affordance.
        locked = page.locator('[data-testid="title-codex-fixed-locked-g_s_rank"]')
        self.assertIn("S級傳說", locked.inner_text())
        self.assertIn("通過 S 級公會考核即可獲得。", locked.inner_text())
        self.assertEqual(
            page.locator('[data-testid="title-codex-fixed-equip-g_s_rank"]').count(), 0
        )

        # Epithet block: the server's can_remove flag alone gates the button.
        page.locator('[data-testid="title-codex-tab-epithet"]').click()
        self.assertEqual(
            page.locator('[data-testid="title-codex-epithet-remove-0"]').count(), 1,
            "the newest, unequipped epithet is removable",
        )
        self.assertEqual(
            page.locator('[data-testid="title-codex-epithet-remove-1"]').count(), 0,
            "the equipped starter epithet renders no removal control",
        )
        self.assertEqual(
            page.locator('[data-testid="title-codex-star"]').count(), 1,
            "exactly the equipped row carries the ★ mark",
        )

        # A pending ballot adds the 提名中 tab and its numbered row.
        self.assertEqual(
            page.locator('[data-testid="title-codex-tab-ballot"]').count(), 1
        )
        page.locator('[data-testid="title-codex-tab-ballot"]').click()
        self.assertIn(
            "夜襲之人",
            page.locator('[data-testid="title-codex-ballot-0"]').inner_text(),
        )

    def test_both_equip_paths_swap_slots_and_update_the_preview(self):
        """One dispatch per click, the typed-command echo, the live preview."""
        page = self.logged_in_page()
        _wait_mode(page, "exploration")
        self._wait_codex(page, lambda p: p.get("available") is True)
        install_outbound_recorder(page)
        page.locator('[data-testid="command-line-codex"]').click()
        page.wait_for_selector('[data-testid="title-codex-panel"]', timeout=15000)

        # Fixed path: the card click dispatches exactly one title.equip and
        # echoes the typed command; the preview re-composes from the panel.
        page.locator('[data-testid="title-codex-fixed-equip-g_e_rank"]').click()
        self.assertEqual(sent_action_count(page, "title.equip"), 1)
        _wait_inp_line(page, 1, "title equip fixed g_e_rank", exact=True)
        self._wait_codex(page, lambda p: p["full_title"] == "E級斥候　南門新客")
        self.assertEqual(
            page.locator('[data-testid="title-codex-preview"]').inner_text(),
            "E級斥候　南門新客",
        )

        # Epithet path: the same affordance on a banked row swaps the slot.
        page.locator('[data-testid="title-codex-tab-epithet"]').click()
        page.locator('[data-testid="title-codex-epithet-equip-0"]').click()
        self.assertEqual(sent_action_count(page, "title.equip"), 2)
        _wait_inp_line(page, 2, "title equip epithet 破城先鋒", exact=True)
        self._wait_codex(page, lambda p: p["full_title"] == "E級斥候　破城先鋒")
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
                {"kind": "fixed", "identifier": "g_e_rank"},
                {"kind": "epithet", "identifier": "破城先鋒"},
            ],
        )

    def test_removal_card_cancels_then_confirms_and_the_ballot_answers(self):
        """Cancel dispatches nothing; confirm deletes one row; accept banks."""
        page = self._opened_codex_page()
        install_outbound_recorder(page)
        page.locator('[data-testid="title-codex-tab-epithet"]').click()

        # Cancel: the review card is client-local and dispatches NOTHING.
        page.locator('[data-testid="title-codex-epithet-remove-0"]').click()
        card = page.locator('[data-testid="title-codex-removal-card"]')
        self.assertIn("破城先鋒", card.inner_text())
        self.assertIn("此操作不可恢復。", card.inner_text())
        page.locator('[data-testid="title-codex-removal-cancel"]').click()
        self.assertEqual(card.count(), 0)
        self.assertEqual(sent_action_count(page), 0)

        # Confirm: exactly one title.remove, the typed echo with the literal
        # confirm token, and the committed panel loses that one row.
        page.locator('[data-testid="title-codex-epithet-remove-0"]').click()
        page.locator('[data-testid="title-codex-removal-confirm"]').click()
        self.assertEqual(sent_action_count(page, "title.remove"), 1)
        _wait_inp_line(page, 1, "title remove epithet 破城先鋒 confirm", exact=True)
        self._wait_codex(
            page,
            lambda p: [row["display"] for row in p["epithet_rows"]] == ["南門新客"],
        )

        # Ballot tab: the numbered accept dispatches title.accept and banks
        # the chosen epithet as the newest row (no free text anywhere).
        page.locator('[data-testid="title-codex-tab-ballot"]').click()
        page.locator('[data-testid="title-codex-ballot-accept-0"]').click()
        self.assertEqual(sent_action_count(page, "title.accept"), 1)
        _wait_inp_line(page, 2, "title accept 1", exact=True)
        self._wait_codex(
            page,
            lambda p: p["pending_ballot"] == []
            and [row["display"] for row in p["epithet_rows"]]
            == ["夜襲之人", "南門新客"],
        )
