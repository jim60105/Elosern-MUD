"""Desktop chrome scales once from the 1080p reference.

webclient-proportional-ui-scale. Offline: the real Vue surfaces render from
the static Storybook build (its preview installs the same resize-owned
chrome factor the live client installs), so no game server runs.
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
REFERENCE = (1920, 1080)
LARGE = (2560, 1440)
RATIO = 4 / 3

MEASURE = """() => {
  const box = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { w: r.width, h: r.height };
  };
  const font = (sel) => {
    const el = document.querySelector(sel);
    return el ? parseFloat(getComputedStyle(el).fontSize) : null;
  };
  return {
    scale: getComputedStyle(document.documentElement).getPropertyValue('--ui-scale').trim(),
    nav: box('[data-testid="nav-settings"]'),
    map: box('svg.local-map__lattice'),
    place: box('[data-anchor="map"] [data-testid="place-card"]'),
    command: box('[data-anchor="band-command"]'),
    band: box('[data-anchor="band-message"]'),
    actor: box('[data-anchor="actor-left"]'),
    navFont: font('[data-testid="nav-settings"]'),
    page: font('[data-testid="message-page"]'),
    viewBox: document.querySelector('svg.local-map__lattice')?.getAttribute('viewBox') ?? null,
  };
}"""


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class ProportionalUiScaleBrowserTest(unittest.TestCase):
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

    def story(self, name, selector, viewport):
        width, height = viewport
        self.page.set_viewport_size({"width": width, "height": height})
        self.page.goto(f"{self.url}/iframe.html?id={name}&viewMode=story")
        self.page.locator(selector).first.wait_for(state="visible")
        self.page.evaluate("document.fonts.ready")
        return self.page.evaluate(MEASURE)

    def assertScaled(self, small, large, label, ratio=RATIO, delta=2):
        self.assertAlmostEqual(large, small * ratio, delta=delta, msg=f"{label}: {small} -> {large}")

    @covers_requirement("webclient-vue-application::desktop-chrome-scales-once-from-the-reference-viewport")
    def test_large_desktop_renders_the_reference_at_four_thirds(self):
        ref = self.story("core-appshell--dialogue-selector", '[data-testid="message-page"]', REFERENCE)
        big = self.story("core-appshell--dialogue-selector", '[data-testid="message-page"]', LARGE)
        self.assertEqual(ref["scale"], "1")
        self.assertAlmostEqual(float(big["scale"]), RATIO, places=3)
        # Chrome: navigation control, place card, minimap canvas.
        self.assertEqual(ref["nav"]["h"], 48)
        self.assertScaled(ref["nav"]["h"], big["nav"]["h"], "nav height")
        self.assertScaled(ref["nav"]["w"], big["nav"]["w"], "nav width")
        self.assertScaled(ref["navFont"], big["navFont"], "nav type", delta=0.5)
        self.assertScaled(ref["place"]["h"], big["place"]["h"], "place card")
        self.assertEqual((ref["map"]["w"], ref["map"]["h"]), (208, 208))
        self.assertScaled(208, big["map"]["w"], "minimap canvas")
        self.assertScaled(208, big["map"]["h"], "minimap canvas")
        # The SVG is only magnified: its user-unit viewBox is unchanged.
        self.assertEqual(ref["viewBox"], big["viewBox"])
        # Viewport-relative prose, band and art scale exactly once.
        self.assertAlmostEqual(ref["page"], 28, delta=0.1)
        self.assertScaled(ref["page"], big["page"], "page text", delta=0.1)
        self.assertScaled(ref["band"]["h"], big["band"]["h"], "band")
        self.assertScaled(ref["actor"]["h"], big["actor"]["h"], "portrait")

        # A reference drawer header scales with the chrome.
        header = '[data-testid$="__title"]'
        self.story("core-drawerheader--default", header, REFERENCE)
        ref_header = self.page.locator(header).first.locator("xpath=..").bounding_box()
        self.story("core-drawerheader--default", header, LARGE)
        big_header = self.page.locator(header).first.locator("xpath=..").bounding_box()
        self.assertScaled(ref_header["height"], big_header["height"], "drawer header")

    @covers_requirement("webclient-vue-application::desktop-chrome-scales-once-from-the-reference-viewport")
    def test_acceptance_sizes_keep_the_reference_chrome(self):
        for viewport in ((1440, 900), (1280, 720)):
            with self.subTest(viewport=viewport):
                data = self.story("core-appshell--populated-hud", '[data-testid="nav-settings"]', viewport)
                self.assertEqual(data["scale"], "1")
                self.assertEqual(data["nav"]["h"], 48)
                self.assertEqual((data["map"]["w"], data["map"]["h"]), (208, 208))

    @covers_requirement("webclient-vue-application::desktop-chrome-scales-once-from-the-reference-viewport")
    def test_prose_preference_changes_prose_but_not_chrome(self):
        before = self.story("core-appshell--dialogue-selector", '[data-testid="message-page"]', LARGE)
        self.page.evaluate("document.documentElement.style.setProperty('--prose-scale', '1.25')")
        after = self.page.evaluate(MEASURE)
        self.assertAlmostEqual(after["page"], before["page"] * 1.25, delta=0.1)
        self.assertEqual(after["nav"], before["nav"])
        self.assertEqual(after["navFont"], before["navFont"])
        self.assertEqual(after["map"], before["map"])
        self.assertEqual(after["place"], before["place"])

    @covers_requirement("webclient-vue-application::desktop-chrome-scales-once-from-the-reference-viewport")
    def test_resize_keeps_pointer_targets_live(self):
        self.story("core-appshell--combat-participant-polish", '[data-testid="action-dock"]', REFERENCE)
        for width, height in (LARGE, (1280, 720), LARGE):
            self.page.set_viewport_size({"width": width, "height": height})
            expected = "1" if height <= 1080 else "1.3333"
            self.page.wait_for_function(
                "(v) => getComputedStyle(document.documentElement).getPropertyValue('--ui-scale').trim() === v",
                arg=expected,
            )
        self.assertAlmostEqual(
            float(self.page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--ui-scale')")),
            RATIO,
            places=3,
        )
        # 攻擊 opens the target frame; the first enabled foe row sends once.
        self.page.locator('[data-testid="dock-menu"] button[role="option"]', has_text="攻擊").first.click()
        target = self.page.locator('[data-testid="dock-menu"] button[role="option"]:not([aria-disabled="true"])', has_text="灰袍盜賊").first
        target.wait_for(state="visible")
        target.click()
        actions = self.page.evaluate("window.__participantPolish.sent.actions.map((a) => a.action_code || a.code || a.action)")
        self.assertEqual(len(actions), 1, actions)

    @covers_requirement("webclient-vue-application::desktop-chrome-scales-once-from-the-reference-viewport")
    def test_a_narrow_tall_window_keeps_the_reference_chrome(self):
        data = self.story("core-appshell--populated-hud", '[data-testid="nav-settings"]', (1600, 1440))
        # 1600 / 1920 < 1: the width holds the chrome at its reference size,
        # while the band's viewport-relative height still follows the window.
        self.assertEqual(data["scale"], "1")
        self.assertEqual(data["nav"]["h"], 48)
        self.assertEqual((data["map"]["w"], data["map"]["h"]), (208, 208))
        self.assertAlmostEqual(data["band"]["h"], 400, delta=1)
