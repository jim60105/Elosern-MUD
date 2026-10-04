"""Desktop chrome scales once from the 1451x790 reference.

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

from .browser_base import ui_scale

ROOT = Path(__file__).resolve().parents[3]
REFERENCE = (1451, 790)
UNCAPPED = (1741, 948)
LARGE = (2560, 1440)
RATIO = 1.4

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
    def test_large_desktop_renders_the_reference_at_the_chrome_cap(self):
        # The populated exploration cockpit: hud-dialogue-declutter made the
        # map island recede during dialogue, so the minimap canvas that this
        # test magnifies only renders in the exploration mode's full island
        # stack (the vitals island rides along, as the dialogue story once did).
        ref = self.story("core-appshell--populated-hud", '[data-testid="nav-settings"]', REFERENCE)
        big = self.story("core-appshell--populated-hud", '[data-testid="nav-settings"]', LARGE)
        self.assertEqual(ref["scale"], "1")
        self.assertAlmostEqual(float(big["scale"]), RATIO, places=3)
        # Chrome: navigation control, place card, minimap canvas.
        self.assertEqual(ref["nav"]["h"], 48)
        self.assertScaled(ref["nav"]["h"], big["nav"]["h"], "nav height")
        self.assertScaled(ref["nav"]["w"], big["nav"]["w"], "nav width")
        self.assertScaled(ref["navFont"], big["navFont"], "nav type", delta=0.5)
        # The place card compacts under the short-viewport media query
        # (max-height: 820px) that the reference activates, so its ratio is
        # measured between the two query-inactive acceptance sizes.
        mid = self.story("core-appshell--populated-hud", '[data-testid="nav-settings"]', UNCAPPED)
        self.assertScaled(
            mid["place"]["h"], big["place"]["h"], "place card",
            ratio=RATIO / ui_scale(UNCAPPED),
        )
        self.assertEqual((ref["map"]["w"], ref["map"]["h"]), (240, 240))
        self.assertScaled(240, big["map"]["w"], "minimap canvas")
        self.assertScaled(240, big["map"]["h"], "minimap canvas")
        # The SVG is only magnified: its user-unit viewBox is unchanged.
        self.assertEqual(ref["viewBox"], big["viewBox"])
        # Viewport-relative prose scales exactly once: the page reads at the
        # 16px floor times the default prose step (A = 1.125) at the reference,
        # and at the same product times the chrome factor at the cap.
        self.assertAlmostEqual(ref["page"], 16 * 1.125, delta=0.1)
        self.assertScaled(ref["page"], big["page"], "page text", delta=0.1)
        # Band and stage art are viewport-relative (`vh`), never multiplied by
        # the chrome factor: the band lands on 27.85% of the height inside its
        # px bounds, and the portrait on 62vh inside the stage box.
        self.assertAlmostEqual(ref["band"]["h"], 0.2785 * 790, delta=1.0)
        self.assertAlmostEqual(big["band"]["h"], 0.2785 * 1440, delta=1.0)
        self.assertAlmostEqual(ref["actor"]["h"], 0.62 * 790, delta=1.0)
        self.assertAlmostEqual(big["actor"]["h"], 0.62 * 1440, delta=1.0)

        # A reference drawer header scales with the chrome.
        header = '[data-testid$="__title"]'
        self.story("core-drawerheader--default", header, REFERENCE)
        ref_header = self.page.locator(header).first.locator("xpath=..").bounding_box()
        self.story("core-drawerheader--default", header, LARGE)
        big_header = self.page.locator(header).first.locator("xpath=..").bounding_box()
        self.assertScaled(ref_header["height"], big_header["height"], "drawer header")

    @covers_requirement("webclient-vue-application::desktop-chrome-scales-once-from-the-reference-viewport")
    def test_acceptance_viewports_render_at_the_contract_scale(self):
        for viewport in (REFERENCE, UNCAPPED, LARGE):
            with self.subTest(viewport=viewport):
                data = self.story("core-appshell--populated-hud", '[data-testid="nav-settings"]', viewport)
                scale = ui_scale(viewport)
                self.assertEqual(data["scale"], "%g" % scale)
                self.assertAlmostEqual(data["nav"]["h"], 48 * scale, delta=0.5)
                self.assertAlmostEqual(data["map"]["w"], 240 * scale, delta=1)
                self.assertAlmostEqual(data["map"]["h"], 240 * scale, delta=1)

    @covers_requirement("webclient-vue-application::desktop-chrome-scales-once-from-the-reference-viewport")
    def test_prose_preference_changes_prose_but_not_chrome(self):
        before = self.story("core-appshell--dialogue-selector", '[data-testid="message-page"]', LARGE)
        before_scale = float(
            self.page.evaluate(
                "() => getComputedStyle(document.documentElement)"
                ".getPropertyValue('--prose-scale').trim()"
            )
        )
        self.page.evaluate("document.documentElement.style.setProperty('--prose-scale', '1.25')")
        after = self.page.evaluate(MEASURE)
        # The page text multiplies the token exactly once, whatever the step
        # it started from.
        self.assertAlmostEqual(
            after["page"], before["page"] * 1.25 / before_scale, delta=0.1
        )
        self.assertEqual(after["nav"], before["nav"])
        self.assertEqual(after["navFont"], before["navFont"])
        self.assertEqual(after["map"], before["map"])
        self.assertEqual(after["place"], before["place"])

    @covers_requirement("webclient-vue-application::desktop-chrome-scales-once-from-the-reference-viewport")
    def test_resize_keeps_pointer_targets_live(self):
        self.story("core-appshell--combat-participant-polish", '[data-testid="action-dock"]', REFERENCE)
        for viewport in (LARGE, REFERENCE, LARGE):
            width, height = viewport
            self.page.set_viewport_size({"width": width, "height": height})
            expected = "%g" % ui_scale(viewport)
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
        data = self.story("core-appshell--populated-hud", '[data-testid="nav-settings"]', (1280, 1440))
        # 1280 / 1451 < 1: the width holds the chrome at its reference size,
        # while the band's viewport-relative height still follows the window.
        self.assertEqual(data["scale"], "1")
        self.assertEqual(data["nav"]["h"], 48)
        self.assertEqual((data["map"]["w"], data["map"]["h"]), (240, 240))
        self.assertAlmostEqual(data["band"]["h"], 400, delta=1)
