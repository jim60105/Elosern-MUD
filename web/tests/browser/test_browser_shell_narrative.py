"""Desktop-shell acceptance: narrative prose rendering, wide-row soft wrap, and keyboard-navigation noise.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    focus_action_dock,
    install_outbound_recorder,
    inject_snapshot,
    sent_action_count,
    store_state,
    valid_art_panel,
    valid_character_panel,
    valid_local_map_panel,
    valid_status_panel,
    wait_for_narrative_settled,
    wait_for_store_state,
)


def _wait_field_focused(page, timeout=30000):
    """Gate on the command field ``#inputfield`` being focused (after ``/``)."""
    wait_for_store_state(
        page,
        lambda s: bool(s.get("connected")),
        dom_readiness={
            "selector": "#inputfield",
            "predicate": (
                "() => document.activeElement === "
                "document.getElementById('inputfield')"
            ),
            "description": "#inputfield focused",
        },
        timeout=timeout,
    )


def _wait_narrative_grew(page, before_len, timeout=30000):
    """Gate on the narrative feed's text length exceeding a previous length."""
    wait_for_store_state(
        page,
        lambda s: bool(s.get("connected")),
        dom_readiness={
            "selector": '[data-testid="narrative-feed"]',
            "predicate": (
                "() => { const n = document.querySelector('[data-testid=\"narrative-feed\"]');"
                " return n && n.innerText.length > %d; }" % before_len
            ),
            "description": "narrative feed text grew past the previous length",
        },
        timeout=timeout,
    )


class ShellAcceptanceTest(BrowserAcceptanceTest):
    """Every required surface at 1440x900 and 1280x720, plus keyboard journeys."""
    @covers_requirement(
        "webclient-narrative-markup::the-narrative-renders-the-transport-stream-through-a-strict-allowlist-markup-pipeline"
    )
    @covers_requirement(
        "webclient-narrative-markup::the-narrative-palette-is-generated-with-a-contrast-floor-and-honors-reduced-motion"
    )
    def test_narrative_renders_styled_prose_not_markup_source(self):
        page = self.logged_in_page()
        narrative_before = page.locator('[data-testid="narrative-feed"]').inner_text()

        # A real room look through the server; the narrative must grow with
        # the room's prose. The *visible text* must never show element or
        # entity source characters (the DOM may legitimately contain rendered
        # span elements -- that is the pipeline working).
        page.evaluate("Evennia.msg('text', ['look'], {})")
        _wait_narrative_grew(page, narrative_before.__len__())
        page.wait_for_timeout(300)
        narrative_text = page.locator('[data-testid="narrative-feed"]').inner_text()
        self.assertNotIn("&lt;", narrative_text)
        self.assertNotIn("&amp;", narrative_text)
        self.assertNotIn("<span", narrative_text)
        self.assertNotIn("</span>", narrative_text)

        # A converted colored line renders with a palette class, never as
        # markup source.
        page.evaluate(
            "() => window.__elosernBridge.store.appendText('out', '|r南大道|n|g 綠|n')"
        )
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": '[data-testid="narrative-feed"]',
                "predicate": (
                    "() => document.querySelectorAll("
                    "'[data-testid=\"narrative-feed\"] span[class*=\"color-\"]').length >= 2"
                ),
                "description": "colored palette spans rendered in the narrative feed",
            },
        )
        colored = page.locator('[data-testid="narrative-feed"] span[class*="color-"]')
        self.assertGreaterEqual(colored.count(), 2)
        for index in range(colored.count()):
            cls = colored.nth(index).get_attribute("class")
            self.assertRegex(cls, r"(?:^|\s)color-\d{3}(?:\s|$)")
        # The styled text is visible, not its source.
        text = page.locator('[data-testid="narrative-feed"]').inner_text()
        self.assertIn("南大道", text)
        self.assertNotIn("<span", text)

    @covers_requirement(
        "webclient-narrative-markup::the-narrative-palette-is-generated-with-a-contrast-floor-and-honors-reduced-motion"
    )
    def test_narrative_wide_row_soft_wraps_inside_the_pane(self):
        page = self.logged_in_page()
        # Baseline: the Vue SPA desktop shell itself may carry a small fixed
        # layout overflow; the wide row must not add to it.
        baseline_scroll = page.evaluate(
            "() => document.documentElement.scrollWidth - "
            "document.documentElement.clientWidth"
        )
        # A row wider than the narrative pane's content width soft-wraps
        # inside the pane: no clipping, no additional page-level scroll.
        wide = "X" * 400 + " 尾部"
        page.evaluate(
            "(text) => window.__elosernBridge.store.appendText('out', text)", wide
        )
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": '[data-testid="narrative-feed"]',
                "predicate": (
                    "() => { const outs = document.querySelectorAll("
                    "'[data-testid=\"narrative-feed\"] .out');"
                    " const last = outs[outs.length - 1];"
                    " return last && last.innerText.indexOf('尾部') !== -1; }"
                ),
                "description": "wide narrative row rendered in the feed",
            },
        )
        # The full text is present (nothing clipped from the DOM).
        text = page.locator('[data-testid="narrative-feed"] .out').last.inner_text()
        self.assertIn("尾部", text)
        # The wide row did not widen the page.
        horizontal_scroll = page.evaluate(
            "() => document.documentElement.scrollWidth - "
            "document.documentElement.clientWidth"
        )
        self.assertEqual(
            horizontal_scroll,
            baseline_scroll,
            "a wide narrative row must soft-wrap without widening the page",
        )

    @covers_requirement(
        "webclient-pointer-activation::keyboard-input-is-dispatched-through-the-webclient-plugin-contract"
    )
    def test_keydown_noise_is_gone_during_keyboard_navigation(self):
        page = self.logged_in_page()
        console_messages = []
        page.on("console", lambda msg: console_messages.append(msg.text))

        # Navigate the action dock with the keyboard: arrows, Enter, Escape,
        # and command-line typing must never report an unhandled keydown.
        focus_action_dock(page)
        for _ in range(3):
            page.keyboard.press("ArrowDown")
        page.keyboard.press("ArrowUp")
        page.keyboard.press("Escape")
        page.keyboard.press("/")
        _wait_field_focused(page)
        page.keyboard.type("look")
        page.keyboard.press("Enter")
        page.wait_for_timeout(300)

        noise = [
            message
            for message in console_messages
            if "NO plugin handled this Keydown" in message
        ]
        self.assertEqual(
            noise,
            [],
            "the plugin must claim exactly the events its router consumed",
        )
