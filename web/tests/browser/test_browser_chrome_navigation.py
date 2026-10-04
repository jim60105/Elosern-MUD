"""Top navigation placement, the shared tool tooltip, and the place card's hierarchy.

webclient-chrome-navigation-polish. Offline: the real Vue surfaces render from
the static Storybook build, so no game server or generation service runs.
"""
from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import threading
import unittest

from playwright.sync_api import sync_playwright
from tools.spec_traceability import covers_requirement

ROOT = Path(__file__).resolve().parents[3]
VIEWPORTS = ((1451, 790), (1741, 948), (2560, 1440))

MEASURE_NAV = """() => {
  const box = (el) => el ? el.getBoundingClientRect() : null;
  const settings = box(document.querySelector('[data-testid="nav-settings"]'));
  const tools = box(document.querySelector('[data-testid="nav-tools"]'));
  const cluster = box(document.querySelector('.topbar-right'));
  const buttons = [...document.querySelectorAll('.desktop-navigation button')];
  return {
    settings: settings && settings.left,
    tools: tools && tools.left,
    slots: [...document.querySelectorAll('[data-testid="nav-primary"] > *')].map((e) => e.dataset.navSlot),
    placeholders: document.querySelectorAll('.desktop-navigation [aria-disabled], .desktop-navigation [hidden], .desktop-navigation button:disabled').length,
    clipped: [...document.querySelectorAll('[data-testid="nav-primary"] > button > span')]
      .filter((e) => e.scrollWidth > e.clientWidth + 0.5).map((e) => e.textContent),
    overlap: cluster ? buttons.filter((b) => b.getBoundingClientRect().right > cluster.left).map((b) => b.textContent.trim() || b.getAttribute('aria-label')) : [],
  };
}"""


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class ChromeNavigationBrowserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        out = ROOT / ".storybook-out"
        if not (out / "index.json").exists():
            subprocess.run(["pnpm", "run", "build-storybook"], cwd=ROOT, check=True, timeout=300)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_QuietHandler, directory=str(out)))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"
        cls.addClassCleanup(cls.server.server_close)
        cls.addClassCleanup(cls.server.shutdown)

    def setUp(self):
        self.playwright = sync_playwright().start()
        self.addCleanup(self.playwright.stop)
        self.browser = self.playwright.chromium.launch(headless=True)
        self.addCleanup(self.browser.close)
        self.page = self.browser.new_page()
        self.page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(self.url + "/") else route.abort())

    def story(self, name, selector):
        self.page.goto(f"{self.url}/iframe.html?id={name}&viewMode=story")
        self.page.locator(selector).first.wait_for(state="visible")
        self.page.evaluate("document.fonts.ready")

    def active_testid(self):
        return self.page.evaluate("document.activeElement && document.activeElement.getAttribute('data-testid')")

    @covers_requirement("webclient-desktop-shell::top-navigation-retains-stable-tool-placement-while-respecting-mode-availability")
    def test_settings_and_tools_hold_their_place_from_exploration_to_combat(self):
        for width, height in VIEWPORTS:
            with self.subTest(viewport=(width, height)):
                self.page.set_viewport_size({"width": width, "height": height})
                self.story("core-appshell--populated-hud", '[data-testid="nav-tools"]')
                explore = self.page.evaluate(MEASURE_NAV)
                self.story("core-appshell--dialogue-selector", '[data-testid="nav-tools"]')
                dialogue = self.page.evaluate(MEASURE_NAV)
                self.story("core-appshell--combat-hud", '[data-testid="nav-tools"]')
                combat = self.page.evaluate(MEASURE_NAV)
                self.assertEqual(explore["slots"], ["character", "quests", "inventory", "map", "settings"])
                # Combat drops 角色狀態, 任務 and 地圖 outright; 背包 stands before 設定.
                self.assertEqual(combat["slots"], ["inventory", "settings"])
                for data in (explore, dialogue, combat):
                    self.assertEqual(data["placeholders"], 0)
                    self.assertEqual(data["overlap"], [])
                    # Every label fits its control whole in the compact
                    # (up to 1350px) and the full padding.
                    self.assertEqual(data["clipped"], [])
                    self.assertAlmostEqual(explore["settings"], data["settings"], delta=1)
                    self.assertAlmostEqual(explore["tools"], data["tools"], delta=1)
                # The absent entries are out of the tab order as well.
                self.page.locator('[data-testid="nav-settings"]').focus()
                self.page.keyboard.press("Shift+Tab")
                self.assertEqual(self.page.evaluate("document.activeElement.textContent.trim()"), "背包")

    @covers_requirement("webclient-desktop-shell::top-navigation-retains-stable-tool-placement-while-respecting-mode-availability")
    def test_unavailable_quest_entry_leaves_no_placeholder(self):
        self.story("core-desktopnavigation--exploration", '[data-testid="nav-tools"]')
        full = self.page.evaluate(MEASURE_NAV)
        self.story("core-desktopnavigation--quests-unavailable", '[data-testid="nav-tools"]')
        partial_nav = self.page.evaluate(MEASURE_NAV)
        self.assertEqual(partial_nav["slots"], ["character", "inventory", "map", "settings"])
        self.assertEqual(partial_nav["placeholders"], 0)
        self.assertAlmostEqual(full["settings"], partial_nav["settings"], delta=1)
        self.assertAlmostEqual(full["tools"], partial_nav["tools"], delta=1)

    @covers_requirement("webclient-desktop-shell::top-navigation-retains-stable-tool-placement-while-respecting-mode-availability")
    def test_tab_focus_tooltip_dismisses_on_escape_and_the_next_escape_reaches_the_dock(self):
        self.page.set_viewport_size({"width": 1451, "height": 790})
        self.story("core-appshell--populated-hud", '[data-testid="nav-tools"]')
        # The dock's keyboard bridge listens for keydown on the document in
        # the bubble phase (bridge.js installKeyRouting); a probe in the same
        # phase sees exactly the Escapes the router would.
        self.page.evaluate("""() => {
          window.__escapes = 0;
          document.addEventListener('keydown', (e) => { if (e.key === 'Escape') window.__escapes += 1; });
        }""")
        self.page.locator('[data-testid="nav-settings"]').focus()
        self.page.keyboard.press("Tab")
        self.assertEqual(self.active_testid(), "nav-tool-lineage")
        tip = self.page.locator('[data-testid="nav-tooltip"]')
        tip.wait_for(state="visible")
        self.assertEqual(tip.inner_text(), "技能系譜")
        self.assertEqual(tip.get_attribute("aria-hidden"), "true")
        # The tooltip hangs under the 48px bar, inside the viewport.
        box = tip.bounding_box()
        self.assertGreaterEqual(box["y"], 47)
        self.assertLessEqual(box["x"] + box["width"], 1451)

        self.page.keyboard.press("Escape")
        self.assertEqual(tip.count(), 0)
        self.assertEqual(self.active_testid(), "nav-tool-lineage")
        self.assertEqual(self.page.evaluate("window.__escapes"), 0)
        self.page.keyboard.press("Escape")
        self.assertEqual(self.page.evaluate("window.__escapes"), 1)
        self.assertEqual(tip.count(), 0)

    @covers_requirement("webclient-desktop-shell::top-navigation-retains-stable-tool-placement-while-respecting-mode-availability")
    def test_pointer_tooltip_is_hoverable_and_hides_on_activation(self):
        self.page.set_viewport_size({"width": 1451, "height": 790})
        self.story("core-appshell--populated-hud", '[data-testid="nav-tools"]')
        self.page.hover('[data-testid="nav-tool-codex"]')
        tip = self.page.locator('[data-testid="nav-tooltip"]')
        tip.wait_for(state="visible")
        self.assertEqual(tip.inner_text(), "稱號冊")
        tip.hover()
        self.page.wait_for_timeout(100)
        self.assertEqual(tip.inner_text(), "稱號冊")
        self.page.click('[data-testid="nav-tool-codex"]')
        self.assertEqual(tip.count(), 0)

    @covers_requirement("webclient-contextual-hud::the-place-card-names-the-current-location-and-the-world-time")
    def test_place_card_sets_heading_rule_and_tabular_time(self):
        for width, height in VIEWPORTS:
            with self.subTest(viewport=(width, height)):
                self.page.set_viewport_size({"width": width, "height": height})
                self.story("core-appshell--populated-hud", '[data-testid="place-card"]')
                card = self.page.evaluate("""() => {
                  const q = (s) => document.querySelector(s);
                  const box = (s) => q(s).getBoundingClientRect();
                  const time = q('[data-testid="place-card__time"]');
                  const style = getComputedStyle(time);
                  return {
                    card: box('[data-testid="place-card"]'),
                    anchor: box('[data-testid="anchor-map"]'),
                    heading: box('[data-testid="place-card__location"]'),
                    rule: box('[data-testid="place-card__rule"]'),
                    time: box('[data-testid="place-card__time"]'),
                    ruleHidden: q('[data-testid="place-card__rule"]').getAttribute('aria-hidden'),
                    before: getComputedStyle(time, '::before').content,
                    text: time.textContent,
                    size: parseFloat(style.fontSize),
                    family: style.fontFamily,
                    numeric: style.fontVariantNumeric,
                  };
                }""")
                # The card heads the `map` anchor's column at its full width,
                # sized to its content (place-card-relocation design D2).
                self.assertAlmostEqual(card["card"]["top"], card["anchor"]["top"], delta=0.5)
                self.assertAlmostEqual(card["card"]["width"], card["anchor"]["width"], delta=0.5)
                self.assertGreaterEqual(card["heading"]["top"], card["card"]["top"])
                self.assertLessEqual(card["heading"]["bottom"], card["rule"]["top"])
                self.assertLessEqual(card["rule"]["bottom"], card["time"]["top"])
                self.assertLessEqual(card["time"]["bottom"], card["card"]["bottom"])
                self.assertEqual(card["ruleHidden"], "true")
                self.assertEqual(card["before"], "none")
                self.assertEqual(card["text"], "春季 3 日 ‧ 12:00")
                self.assertGreaterEqual(card["size"], 12)
                self.assertIn("Noto Sans TC", card["family"])
                self.assertIn("tabular-nums", card["numeric"])
                self.assertIn("lining-nums", card["numeric"])
