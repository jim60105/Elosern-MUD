"""Rendered chrome readability and changing numeric columns in offline stories."""
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


class VueTypographyBrowserTest(unittest.TestCase):
    """No game server or generation services: exercise the real Vue surfaces."""

    @classmethod
    def setUpClass(cls):
        out = ROOT / ".storybook-out"
        if not (out / "index.json").exists():
            subprocess.run(["pnpm", "run", "build-storybook"], cwd=ROOT, check=True, timeout=300)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(out)))
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

    @covers_requirement("webclient-vue-application::chrome-type-is-legible-and-numerals-are-stable")
    def test_dense_chrome_floor_and_bounded_controls(self):
        stories = (
            ("core-appshell--populated-hud", ".vitals"),
            ("core-appshell--combat-five-foes", ".participant-frame"),
            ("core-appshell--dialogue-selector", ".dialogue-choices__row"),
            ("data-characterstatusdrawer--full", ".character-status-drawer"),
            ("overlays-creationoverlay--custom-draft", ".creation-overlay"),
            # The map chrome joined the floor with webclient-map-legibility;
            # only the drawn SVG map (node labels, marker names) stays outside.
            ("world-localmap--wilderness", ".local-map__detail"),
            ("overlays-mapoverlay--interior-with-remembered", ".map-overlay__remembered"),
        )
        for width, height in ((1920, 1080), (1440, 900), (1280, 720)):
            self.page.set_viewport_size({"width": width, "height": height})
            for story, selector in stories:
                with self.subTest(viewport=(width, height), story=story):
                    self.story(story, selector)
                    result = self.page.evaluate("""() => {
                      const exempt = 'svg,.narrative-line,.cmdfield__prompt-html,.sr-only,.visually-hidden,[aria-hidden="true"]';
                      const small = [...document.querySelectorAll('#storybook-root *')].filter(e =>
                        e.checkVisibility() && !e.closest(exempt) && e.getBoundingClientRect().width > 1 &&
                        [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()) &&
                        parseFloat(getComputedStyle(e).fontSize) < 12
                      ).map(e => ({text:e.textContent, size:getComputedStyle(e).fontSize}));
                      const clipped = [...document.querySelectorAll('.action-dock__legend,.vital .num,.creation-overlay__actions button')]
                        .filter(e => e.checkVisibility() && (e.scrollWidth > e.clientWidth + 1 || e.scrollHeight > e.clientHeight + 1))
                        .map(e => e.textContent);
                      return {small, clipped, overflow: document.documentElement.scrollWidth > innerWidth};
                    }""")
                    self.assertEqual(result, {"small": [], "clipped": [], "overflow": False})

    @covers_requirement("webclient-vue-application::chrome-type-is-legible-and-numerals-are-stable")
    def test_changed_numerals_keep_columns_and_tabular_glyph_widths(self):
        for height in (1080, 720):
            self.page.set_viewport_size({"width": 1280, "height": height})
            self.story("data-vitalstrack--changing-numerals", ".shop-row__price")
            def metrics():
                return self.page.evaluate("""() => {
                  const values = [...document.querySelectorAll('.vital .num')];
                  const stocks = [...document.querySelectorAll('[data-testid="shop-panel__stock-section"] .shop-row')];
                  return {
                    text: values.map(e => e.textContent.trim()),
                    vitals: values.map(e => ({right:e.getBoundingClientRect().right,width:e.getBoundingClientRect().width})),
                    prices: stocks.map(e => [...e.querySelectorAll('.shop-row__price')].map(n => n.getBoundingClientRect().right)),
                    fonts: [...values, ...document.querySelectorAll('.shop-row__price')].map(e => ({family:getComputedStyle(e).fontFamily,variant:getComputedStyle(e).fontVariantNumeric})),
                    clipped: [...values, ...document.querySelectorAll('.shop-row__price')].some(e=>e.scrollWidth>e.clientWidth+1)
                  };
                }""")
            before = metrics()
            self.page.get_by_test_id("change-numerals").click()
            self.page.wait_for_function("document.querySelector('.vital .num').textContent.includes('139')")
            after = metrics()
            self.assertEqual(before["text"], ["9 / 405", "111 / 999", "11 / 99"])
            self.assertEqual(after["text"], ["139 / 405", "888 / 999", "88 / 99"])
            for data in (before, after):
                self.assertFalse(data["clipped"])
                for column in range(2):
                    self.assertAlmostEqual(data["prices"][0][column], data["prices"][1][column], delta=0.5)
                for font in data["fonts"]:
                    self.assertIn("Noto Sans TC", font["family"])
                    self.assertNotIn("monospace", font["family"])
                    self.assertIn("tabular-nums", font["variant"])
                    self.assertIn("lining-nums", font["variant"])
            for index in range(3):
                self.assertAlmostEqual(before["vitals"][index]["right"], after["vitals"][index]["right"], delta=0.5)
            # Equal-length 111 -> 888 and 11 -> 88 use the loaded font's real metrics.
            for index in (1, 2):
                self.assertAlmostEqual(before["vitals"][index]["width"], after["vitals"][index]["width"], delta=0.5)

    def test_keycaps_and_command_input_keep_monospace(self):
        self.story("core-appshell--populated-hud", ".vitals")
        self.assertIn("monospace", self.page.locator("kbd").first.evaluate("e => getComputedStyle(e).fontFamily"))
        self.page.get_by_role("button", name="指令列", exact=True).click()
        field = self.page.locator("#inputfield")
        field.wait_for(state="visible")
        self.assertIn("monospace", field.evaluate("e => getComputedStyle(e).fontFamily"))
        self.assertTrue(field.evaluate("e => e === document.activeElement"))
        self.page.keyboard.press("Escape")
        self.assertTrue(self.page.locator("#action-dock").evaluate("e => e === document.activeElement"))
