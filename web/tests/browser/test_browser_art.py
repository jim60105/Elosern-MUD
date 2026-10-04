"""Art panel browser acceptance (webclient-art-panel 8.1-8.2).

Drives the real Evennia server's art panel through the Vue SPA scene
renderer and contextual portrait overlay. The seed fixture (``ELOSERN_BROWSER_ART``)
places the character in a validated scene room with a done/pending/failed scene
record and a named-policy NPC plus a living monster. Journeys assert same-origin
URL rendering, truthful placeholders, keyboard-only full view, portrait overlay
with name/role context, client-local focus switching with no packet, no-focus
no-card, combat results removing the catalog entry in the same update, and the
subject-eligibility payload exclusion.
"""

from __future__ import annotations

import base64
import os

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    focus_action_dock,
    install_outbound_recorder,
    narrative_log_length,
    narrative_log_text,
    open_command_line,
    sent_action_count,
    store_state,
    wait_for_store_state,
)
from .harness import ManagedServerTearDownMixin
from .seed import FIXTURE_VALID_PNG

# The art fixture's archetype/display pair for the CURRENT boot mode (kit
# row under the synthetic install; the seed fixture places the character in
# a room carrying exactly this archetype).
from web.browser_support.browser_fixtures_data import art_room_monster_key, art_scene_values

SCENE_ARCHETYPE_KEY, SCENE_LABEL = art_scene_values()
SCENE_URL = f"/art/scene/{SCENE_ARCHETYPE_KEY}.png"

# A same-origin-free image URL (the seed fixture's minimal valid 4x4 PNG as a
# data URL) so the pending-scene generating notice can be seeded without any
# network request (the harness guards non-local requests).
PRIOR_IMAGE_DATA_URL = "data:image/png;base64," + base64.b64encode(FIXTURE_VALID_PNG).decode()


def _rect(page, selector):
    """The page-coordinate bounding box of a selector (None when absent from the DOM)."""
    return page.evaluate(
        """(sel) => {
          const el = document.querySelector(sel);
          return el ? el.getBoundingClientRect() : null;
        }""",
        selector,
    )


def _boxes_overlap(a, b):
    """True when two page-coordinate boxes intersect."""
    return not (
        a["right"] <= b["left"] or b["right"] <= a["left"]
        or a["bottom"] <= b["top"] or b["bottom"] <= a["top"]
    )


_CAPTION_GEOMETRY_JS = """() => {
  const box = (el) => {
    if (!el) { return null; }
    const r = el.getBoundingClientRect();
    return { left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height };
  };
  const q = (sel) => document.querySelector(sel);
  const parts = {};
  for (const id of ["scene-backdrop-label", "scene-backdrop-alt", "scene-backdrop-control"]) {
    const el = q('[data-testid="' + id + '"]');
    if (!el) { continue; }
    const b = box(el);
    // The element painted at the part's centre is the part itself (or its
    // text), so no HUD surface above the backdrop covers it.
    const hit = document.elementFromPoint((b.left + b.right) / 2, (b.top + b.bottom) / 2);
    parts[id] = { box: b, onTop: !!hit && (hit === el || el.contains(hit)) };
  }
  return {
    parts,
    plate: box(q(".scene-backdrop__plate")),
    backdrop: box(q('[data-testid="scene-backdrop"]')),
    band: box(q('[data-testid="stage-band"]')),
    commandLine: box(q('[data-anchor="command-line"]')),
    actorLeft: box(q('[data-anchor="actor-left"]')),
    actorRight: box(q('[data-anchor="actor-right"]')),
  };
}"""


def assert_scene_caption_on_stage_floor(test, page, viewport):
    """The scene caption plate (label, alt text, full-view control) sits on
    the stage box's lower edge, 12px above the expanded command-line row,
    centred in the open stage between the two portrait anchors' boxes, and
    no portrait or HUD surface paints over any of its parts. The portraits
    are pointer-transparent, so their clearance is a box check; every other
    surface is caught by the hit test.
    """
    geo = page.evaluate(_CAPTION_GEOMETRY_JS)
    size = "%dx%d" % viewport
    test.assertIn("scene-backdrop-label", geo["parts"], "the scene label renders at %s" % size)
    plate = geo["plate"]
    cmd = geo["commandLine"]
    band = geo["band"]
    test.assertIsNotNone(plate, "the caption plate renders at %s" % size)
    # The backdrop box ends at the band's top edge; the plate stands just
    # above the command-line row docked on that edge (not a band-height up).
    test.assertAlmostEqual(geo["backdrop"]["bottom"], band["top"], delta=1.0)
    test.assertAlmostEqual(cmd["bottom"], band["top"], delta=1.0)
    gap = cmd["top"] - plate["bottom"]
    test.assertGreaterEqual(gap, 0, "the caption intrudes into the command line at %s" % size)
    test.assertLessEqual(gap, 16, "the caption floats %.0fpx above the command line at %s" % (gap, size))
    # Centred in the open stage between the portrait anchors' boxes.
    left_edge = geo["actorLeft"]["right"]
    right_edge = geo["actorRight"]["left"]
    test.assertAlmostEqual(
        (plate["left"] + plate["right"]) / 2, (left_edge + right_edge) / 2, delta=1.5,
        msg="the caption is not centred between the portraits at %s" % size,
    )
    for testid, part in geo["parts"].items():
        b = part["box"]
        test.assertGreater(b["width"], 0, "%s is rendered at %s" % (testid, size))
        test.assertGreaterEqual(b["left"], left_edge, "%s slips under the player portrait at %s" % (testid, size))
        test.assertLessEqual(b["right"], right_edge, "%s slips under the right portrait at %s" % (testid, size))
        test.assertLessEqual(b["bottom"], cmd["top"], "%s intrudes into the command line at %s" % (testid, size))
        test.assertTrue(part["onTop"], "%s is covered by another surface at %s" % (testid, size))


def _art_portrait_ready(state: dict) -> bool:
    """A portrait tile renders only when the art panel is available and its catalog has entries."""
    art = (state.get("panels") or {}).get("art") or {}
    return (
        art.get("available") is not False
        and len(art.get("portrait_catalog") or {}) > 0
    )


def _art_missing_placeholder(state: dict) -> bool:
    """The missing-scene fixture: the art panel is available and the scene placeholder kind is 'missing'."""
    art = (state.get("panels") or {}).get("art") or {}
    scene = art.get("scene") or {}
    placeholder = scene.get("placeholder") or {}
    return art.get("available") is True and placeholder.get("kind") == "missing"


def _art_scene_failed(state: dict) -> bool:
    """The seeded art scene has reached the failed status."""
    scene = ((state.get("panels") or {}).get("art") or {}).get("scene") or {}
    return scene.get("status") == "failed"


def _art_scene_done(state: dict) -> bool:
    """The art scene is a done asset (a client-side load failure keeps it done)."""
    scene = ((state.get("panels") or {}).get("art") or {}).get("scene") or {}
    return scene.get("status") == "done"


def _in_combat_mode(state: dict) -> bool:
    """The client is in combat mode (a seeded monster was engaged)."""
    return state.get("mode") == "combat"


def _out_of_combat_mode(state: dict) -> bool:
    """Combat has ended (the forfeit settlement cleared the session)."""
    return state.get("mode") != "combat"


def _mutations_unlocked(state: dict) -> bool:
    """The action client's submission gate is closed (no mutation in flight)."""
    return state.get("mutationsLocked") is not True


def _connected_active(state: dict) -> bool:
    """The transport is connected and the client has left the snapshot/detached phases."""
    return bool(state.get("connected")) and state.get("phase") == "active"



# H3: in combat mode the ArtPanel is hidden and the portraits render in the
# ParticipantFrame (the 我方/敵方 token rows). This DOM readiness targets the
# participant frame's rows.
PORTRAIT_TILE_DOM = {
    "selector": ".participant-frame__row",
    "predicate": (
        "() => { const t = document.querySelector('.participant-frame__row'); "
        "if (!t) { return false; } "
        "const r = t.getBoundingClientRect(); "
        "return r.width > 0 && r.height > 0; }"
    ),
    "description": "a combat participant row is rendered and visible",
}

SCENE_PLACEHOLDER_DOM = {
    "selector": '[data-testid="scene-backdrop-placeholder"]',
    "predicate": (
        "() => { const p = document.querySelector('[data-testid=\"scene-backdrop-placeholder\"]'); "
        "if (!p) { return false; } "
        "const r = p.getBoundingClientRect(); "
        "return r.width > 0 && r.height > 0; }"
    ),
    "description": "scene placeholder (load-failure fallback) rendered and visible",
}


class ArtSceneBrowserTest(ManagedServerTearDownMixin, BrowserAcceptanceTest):
    """Scene renderer journeys on a per-test isolated server.

    Each test boots its own isolated server so the seeded art mode (done /
    pending / failed / missing) is deterministic per journey.
    """

    def setUp(self) -> None:
        from .harness import ManagedServer

        self.server = ManagedServer()
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    @classmethod
    def setUpClass(cls) -> None:
        # Each test boots its own isolated server; never the shared one.
        pass

class ArtDoneSceneTest(ArtSceneBrowserTest):
    """A done scene renders the same-origin media URL and full view."""

    def setUp(self) -> None:
        os.environ["ELOSERN_BROWSER_ART"] = "done"
        super().setUp()
        os.environ.pop("ELOSERN_BROWSER_ART", None)

    @covers_requirement("webclient-art-panel::the-scene-payload-resolves-only-validated-archetypes-with-truthful-placeholders")
    @covers_requirement("webclient-contextual-hud::the-scene-backdrop-renders-the-art-payload-truthfully-behind-the-stage")
    def test_done_scene_renders_same_origin_image(self):
        page = self.logged_in_page()
        state = store_state(page)
        panel = state["panels"]["art"]
        self.assertTrue(panel["available"])
        self.assertEqual(panel["scene"]["status"], "done")
        self.assertEqual(panel["scene"]["url"], SCENE_URL)
        self.assertEqual(panel["scene"]["aspect_ratio"], "16:9")
        self.assertIsNone(panel["scene"]["placeholder"])
        # The image element is present with a same-origin src.
        img = page.locator('[data-testid="scene-backdrop-image"]')
        self.assertEqual(img.count(), 1)
        self.assertTrue(img.get_attribute("src").startswith("/art/"))
        self.assertNotIn("http://", img.get_attribute("src"))

    @covers_requirement("webclient-art-panel::the-scene-payload-resolves-only-validated-archetypes-with-truthful-placeholders")
    def test_alternative_text_is_present_outside_the_bitmap(self):
        page = self.logged_in_page()
        # Requirement: the scene label and alternative text SHALL remain visible
        # outside the bitmap. The scene moved to the full-bleed `SceneBackdrop`
        # (H1); the label/alt render as DOM text nodes
        # (`[data-testid="scene-backdrop-label"]`, `[data-testid="scene-backdrop-alt"]`),
        # so the alt text is the `scene-backdrop-alt` node, not the img `alt` attribute.
        alt = page.locator('[data-testid="scene-backdrop-alt"]').inner_text()
        self.assertTrue(alt.strip(), "scene alternative text must be meaningful and non-empty")
        caption = page.locator('[data-testid="scene-backdrop-label"]').inner_text()
        self.assertEqual(caption, SCENE_LABEL)

    @covers_requirement("webclient-art-panel::art-panel-browser-acceptance-is-keyboard-first-accessible-and-desktop-bounded")
    def test_scene_caption_and_status_usable_at_the_reference_viewport(self):
        page = self.logged_in_page((1451, 790))
        # The done scene image, its caption label and alt, and the pending
        # status line remain visible at the reference viewport.
        img = page.locator('[data-testid="scene-backdrop-image"]')
        self.assertEqual(img.count(), 1)
        self.assertTrue(img.is_visible())
        self.assertEqual(page.locator('[data-testid="scene-backdrop-label"]').inner_text(), SCENE_LABEL)
        self.assertTrue(page.locator('[data-testid="scene-backdrop-alt"]').inner_text().strip())
        self.assertTrue(page.locator('[data-testid="scene-backdrop"]').is_visible())

    @covers_requirement("webclient-contextual-hud::the-scene-backdrop-renders-the-art-payload-truthfully-behind-the-stage")
    def test_scene_caption_sits_on_the_stage_floor_between_the_portraits(self):
        """The done scene's caption plate stands on the stage's lower edge just
        above the expanded command-line row, centred between the portraits and
        covered by nothing, at every supported viewport."""
        page = self.logged_in_page((1451, 790))
        open_command_line(page)
        for viewport in ((1451, 790), (1741, 948), (2560, 1440)):
            with self.subTest(viewport=viewport):
                page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
                page.wait_for_function(
                    "([w, h]) => innerWidth === w && innerHeight === h", arg=list(viewport), timeout=5000
                )
                assert_scene_caption_on_stage_floor(self, page, viewport)



class ArtPendingSceneTest(ArtSceneBrowserTest):
    def setUp(self) -> None:
        os.environ["ELOSERN_BROWSER_ART"] = "pending"
        super().setUp()
        os.environ.pop("ELOSERN_BROWSER_ART", None)

    @covers_requirement("webclient-art-panel::the-scene-payload-resolves-only-validated-archetypes-with-truthful-placeholders")
    @covers_requirement("webclient-contextual-hud::the-scene-backdrop-renders-the-art-payload-truthfully-behind-the-stage")
    def test_pending_scene_without_prior_image_uses_placeholder(self):
        page = self.logged_in_page()
        panel = store_state(page)["panels"]["art"]
        self.assertEqual(panel["scene"]["status"], "pending")
        self.assertIsNone(panel["scene"]["url"])
        # Without a prior image, the scene placeholder renders (no image).
        self.assertEqual(page.locator('[data-testid="scene-backdrop-image"]').count(), 0)
        placeholder = page.locator('[data-testid="scene-backdrop-placeholder"]').inner_text()
        self.assertTrue(placeholder.strip())

    @covers_requirement("webclient-contextual-hud::the-scene-backdrop-renders-the-art-payload-truthfully-behind-the-stage")
    def test_pending_generating_notice_clears_dock_and_command_line(self):
        """A pending scene with a prior image renders the explicit generating
        notice; its bounding box stays above the action dock's and the command
        line's top edges at both supported viewports.
        """
        for viewport in ((1451, 790), (2560, 1440)):
            with self.subTest(viewport=viewport):
                page = self.logged_in_page(viewport)
                panel = store_state(page)["panels"]["art"]
                self.assertEqual(panel["scene"]["status"], "pending")
                # Bounded-wait for the bridge backdrop hook (the SceneBackdrop
                # instance registered by AppClient on mount; a plain property on
                # the bridge, not a getter).
                page.wait_for_function(
                    "() => { const b = window.__elosernBridge && window.__elosernBridge.backdrop; "
                    "return !!(b && typeof b.setPriorImage === 'function'); }",
                    timeout=15000,
                )
                # Seed the client-local prior-image memory with the fixture's valid
                # PNG as a data URL (no network request; the dimmed prior image and
                # the generating notice then render deterministically).
                seeded = page.evaluate(
                    """(url) => {
                      const b = window.__elosernBridge.backdrop;
                      if (b && typeof b.setPriorImage === "function") {
                        b.setPriorImage(url);
                        return true;
                      }
                      return false;
                    }""",
                    PRIOR_IMAGE_DATA_URL,
                )
                self.assertTrue(seeded, "the bridge's backdrop hook was available")
                # The pending notice renders above the dock.
                page.wait_for_selector('[data-testid="scene-backdrop-generating"]', timeout=15000)
                open_command_line(page)
                notice = _rect(page, '[data-testid="scene-backdrop-generating"]')
                dock = _rect(page, '[data-testid="action-dock"]')
                cmd_line = _rect(page, '[data-testid="command-line"]')
                self.assertIsNotNone(notice, "the generating notice is rendered")
                self.assertIsNotNone(dock, "the action dock panel is rendered")
                self.assertIsNotNone(cmd_line, "the command line is rendered")
                self.assertLessEqual(
                    notice["bottom"],
                    dock["top"],
                    "the generating notice intrudes into the action dock at %dx%d" % (viewport[0], viewport[1]),
                )
                self.assertLessEqual(
                    notice["bottom"],
                    cmd_line["top"],
                    "the generating notice intrudes into the command line at %dx%d" % (viewport[0], viewport[1]),
                )
                self.assertFalse(
                    _boxes_overlap(notice, dock),
                    "the generating notice box intersects the action dock at %dx%d" % (viewport[0], viewport[1]),
                )
                self.assertFalse(
                    _boxes_overlap(notice, cmd_line),
                    "the generating notice box intersects the command line at %dx%d" % (viewport[0], viewport[1]),
                )


class ArtFailedSceneTest(ArtSceneBrowserTest):
    def setUp(self) -> None:
        # Point the image-generation client at the deterministic failing
        # double, so ``@art run`` produces a real failed record at runtime (a
        # seed-failed record would be re-enqueued by the startup sync).
        os.environ["ELOSERN_BROWSER_ART"] = "pending"
        os.environ["ELOSERN_BROWSER_SD_CLIENT"] = (
            "web.tests.browser.fake_sd_client.FailingSDWebUIClient"
        )
        super().setUp()
        for key in (
            "ELOSERN_BROWSER_ART",
            "ELOSERN_BROWSER_SD_CLIENT",
        ):
            os.environ.pop(key, None)

    @covers_requirement("webclient-art-panel::art-degradation-never-blocks-gameplay-or-leaks-rejected-content")
    @covers_requirement("webclient-contextual-hud::the-scene-backdrop-renders-the-art-payload-truthfully-behind-the-stage")
    def test_failed_scene_uses_the_placeholder(self):
        page = self.logged_in_page()
        # Drain the queue with the failing image-generation client, then refresh
        # presentation.
        page.evaluate("Evennia.msg('text', ['@art run --limit 1'], {})")
        page.wait_for_timeout(1500)
        page.evaluate("Evennia.msg('text', ['look'], {})")
        # The failed-scene placeholder-count assertion is gated on the shared
        # bounded-wait helper: the committed art-panel store state plus a
        # single-node DOM-readiness descriptor, within one bounded deadline —
        # not a single raw `.count()` sample that a snapshot-refresh or Vue
        # re-render double-node window under a loaded runner would race.
        wait_for_store_state(
            page,
            _art_scene_failed,
            {
                "selector": '[data-testid="scene-backdrop"] [data-testid="scene-backdrop-placeholder"]',
                "predicate": (
                    "() => { const els = document.querySelectorAll('[data-testid=\"scene-backdrop\"] [data-testid=\"scene-backdrop-placeholder\"]'); "
                    "if (els.length !== 1) { return false; } "
                    "const el = els[0]; const r = el.getBoundingClientRect(); "
                    "return r.width > 0 && r.height > 0 && el.offsetParent !== null; }"
                ),
                "description": "single visible scene placeholder inside the scene frame",
            },
            timeout=20000,
        )
        self.assertEqual(store_state(page)["panels"]["art"]["scene"]["status"], "failed")
        self.assertIsNone(store_state(page)["panels"]["art"]["scene"]["url"])
        self.assertEqual(page.locator('[data-testid="scene-backdrop-image"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="scene-backdrop-placeholder"]').count(), 1)


class ArtMissingSceneTest(ArtSceneBrowserTest):
    def setUp(self) -> None:
        os.environ["ELOSERN_BROWSER_ART"] = "missing"
        super().setUp()
        os.environ.pop("ELOSERN_BROWSER_ART", None)

    @covers_requirement(
        "webclient-art-panel::art-degradation-never-blocks-gameplay-or-leaks-rejected-content",
        "webclient-browser-verification::browser-test-waits-gate-on-deterministic-state-within-a-bounded-deadline",
        "webclient-contextual-hud::the-scene-backdrop-renders-the-art-payload-truthfully-behind-the-stage",
    )
    def test_missing_scene_uses_the_placeholder_and_play_continues(self):
        page = self.logged_in_page()
        # The missing-scene placeholder is gated on the committed art-panel
        # store state and the scene-frame-scoped single-node DOM, within one
        # bounded deadline — not a single raw `.count()` sample that a
        # snapshot-refresh double-node window under a loaded CI runner would
        # race.
        wait_for_store_state(
            page,
            _art_missing_placeholder,
            dom_readiness={
                "selector": "[data-testid=\"scene-backdrop\"] [data-testid=\"scene-backdrop-placeholder\"]",
                "predicate": (
                    "() => { const els = document.querySelectorAll('[data-testid=\"scene-backdrop\"] [data-testid=\"scene-backdrop-placeholder\"]'); "
                    "if (els.length !== 1) { return false; } "
                    "const el = els[0]; const r = el.getBoundingClientRect(); "
                    "return r.width > 0 && r.height > 0 && el.offsetParent !== null; }"
                ),
                "description": "single visible scene placeholder inside the scene frame",
            },
        )
        # Movement through the ordinary transport still works. The narrative
        # assertion is gated on the shared bounded store-state + log path
        # (no fixed sleep) so it stays stable under a loaded CI runner.
        before = narrative_log_length(page)
        page.evaluate("Evennia.msg('text', ['look'], {})")
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected"))
            and s.get("phase") == "active"
            and narrative_log_length(page) > before,
        )
        narrative = narrative_log_text(page)
        self.assertTrue(narrative.strip())

    @covers_requirement("webclient-contextual-hud::the-scene-backdrop-renders-the-art-payload-truthfully-behind-the-stage")
    def test_scene_backdrop_captions_clear_dock_and_command_line(self):
        """The degraded scene renders exactly one status badge, and that badge
        stays clear of the bottom band, the action dock, and the command line
        at both supported viewports (fix-webclient-scene-backdrop-placeholder-overlap).
        Under the caption-consolidation contract (webclient-stage-caption-and-hold-backdrop)
        no scene caption row, label, alternative text, or full-view control
        renders at all while no scene image is on the stage; the caption plate
        standing on the stage floor is the done-scene journey's assertion
        (test_scene_caption_sits_on_the_stage_floor_between_the_portraits).
        """
        for viewport in ((1451, 790), (2560, 1440)):
            with self.subTest(viewport=viewport):
                page = self.logged_in_page(viewport)
                # The missing-scene placeholder is gated on the committed art-panel
                # store state and the scene-frame-scoped single-node DOM, within one
                # bounded deadline.
                wait_for_store_state(
                    page,
                    _art_missing_placeholder,
                    {
                        "selector": "[data-testid=\"scene-backdrop\"] [data-testid=\"scene-backdrop-placeholder\"]",
                        "predicate": (
                            "() => { const els = document.querySelectorAll('[data-testid=\"scene-backdrop\"] [data-testid=\"scene-backdrop-placeholder\"]'); "
                            "if (els.length !== 1) { return false; } "
                            "const el = els[0]; const r = el.getBoundingClientRect(); "
                            "return r.width > 0 && r.height > 0 && el.offsetParent !== null; }"
                        ),
                        "description": "single visible scene placeholder inside the scene frame",
                    },
                )
                open_command_line(page)
                dock = _rect(page, '[data-testid="action-dock"]')
                cmd_line = _rect(page, '[data-testid="command-line"]')
                band = _rect(page, '[data-testid="stage-band"]')
                self.assertIsNotNone(dock, "the action dock panel is rendered")
                self.assertIsNotNone(cmd_line, "the command line is rendered")
                for testid in (
                    "scene-backdrop-placeholder",
                    "scene-backdrop-label",
                    "scene-backdrop-alt",
                    "scene-backdrop-control",
                ):
                    box = _rect(page, '[data-testid="%s"]' % testid)
                    if box is None:
                        continue
                    self.assertLessEqual(
                        box["bottom"],
                        dock["top"],
                        "%s intrudes into the action dock at %dx%d" % (testid, viewport[0], viewport[1]),
                    )
                    self.assertLessEqual(
                        box["bottom"],
                        cmd_line["top"],
                        "%s intrudes into the command line at %dx%d" % (testid, viewport[0], viewport[1]),
                    )
                    self.assertLessEqual(
                        box["bottom"],
                        band["top"],
                        "%s intrudes into the bottom band at %dx%d" % (testid, viewport[0], viewport[1]),
                    )
                    self.assertFalse(
                        _boxes_overlap(box, dock),
                        "%s box intersects the action dock at %dx%d" % (testid, viewport[0], viewport[1]),
                    )
                    self.assertFalse(
                        _boxes_overlap(box, cmd_line),
                        "%s box intersects the command line at %dx%d" % (testid, viewport[0], viewport[1]),
                    )
                # The caption-consolidation contract: the degraded scene renders
                # exactly one status badge (checked post-expansion, where the
                # DOM-readiness gate above only proves the pre-expansion frame)
                # and no scene caption row at all.
                self.assertEqual(
                    page.locator('[data-testid="scene-backdrop-caption"]').count(),
                    0,
                    "a degraded scene renders no scene caption row at %dx%d"
                    % (viewport[0], viewport[1]),
                )
                self.assertEqual(
                    page.locator(
                        '[data-testid="scene-backdrop"] '
                        '[data-testid="scene-backdrop-placeholder"]'
                    ).count(),
                    1,
                    "the degraded scene renders exactly one status badge at %dx%d"
                    % (viewport[0], viewport[1]),
                )
                # The message window sits in the band's left two thirds beside
                # the action dock and below the expanded command line, intersecting neither.
                feed = _rect(page, '[data-testid="message-window"]')
                if feed is not None:
                    self.assertLessEqual(
                        feed["right"],
                        dock["left"],
                        "the message window intrudes into the action dock at %dx%d" % (viewport[0], viewport[1]),
                    )
                    self.assertFalse(
                        _boxes_overlap(feed, dock),
                        "the message window box intersects the action dock at %dx%d" % (viewport[0], viewport[1]),
                    )
                    self.assertFalse(
                        _boxes_overlap(feed, cmd_line),
                        "the message window box intersects the command line at %dx%d" % (viewport[0], viewport[1]),
                    )


class ArtImageLoadFailureTest(ArtSceneBrowserTest):
    """A done scene whose media URL fails to load degrades to fallback.

    The scene image request is aborted to simulate a browser image-load
    failure; the panel must show a truthful fallback instead of a broken
    image and must not repeatedly re-fetch the same URL (webclient-art-panel
    6/7 image-load degradation requirement).
    """

    def setUp(self) -> None:
        os.environ["ELOSERN_BROWSER_ART"] = "done"
        super().setUp()
        os.environ.pop("ELOSERN_BROWSER_ART", None)

    def _abort_art_media(self, page) -> None:
        # Track how often the scene image URL is requested.
        self._art_requests = []

        def _handler(route):
            if route.request.url.endswith(SCENE_URL):
                self._art_requests.append(route.request.url)
                route.abort("failed")
            else:
                route.continue_()

        # Abort the art media URL before the shared local-only guard is
        # consulted by registering a more specific route after it.
        page.route("**/art/**", _handler)

    @covers_requirement("webclient-art-panel::art-degradation-never-blocks-gameplay-or-leaks-rejected-content")
    def test_image_load_failure_shows_fallback_without_refetch(self):
        page = self.new_page()
        self._abort_art_media(page)
        from .browser_helpers import login_and_open

        login_and_open(page, self.webclient_url, self.base_url)
        # The panel resolves the done scene but the image load fails, so the
        # truthful fallback replaces the broken image inside the asset pane.
        wait_for_store_state(
            page,
            _art_scene_done,
            SCENE_PLACEHOLDER_DOM,
            timeout=20000,
        )
        self.assertEqual(page.locator('[data-testid="scene-backdrop-image"]').count(), 0)
        placeholder = page.locator('[data-testid="scene-backdrop-placeholder"]')
        self.assertTrue(placeholder.inner_text().strip())
        self.assertEqual(
            placeholder.get_attribute("data-kind"),
            "load_failed",
            "an image load failure shows the load_failed placeholder kind",
        )
        # The aborted request was attempted exactly once.
        self.assertEqual(len(self._art_requests), 1)
        # A later snapshot refresh must not re-request the failed URL.
        page.evaluate("Evennia.msg('text', ['look'], {})")
        page.wait_for_timeout(800)
        page.evaluate("Evennia.msg('text', ['look'], {})")
        page.wait_for_timeout(800)
        self.assertEqual(len(self._art_requests), 1)
        # Play continues deterministically.
        narrative = narrative_log_text(page)
        self.assertTrue(narrative.strip())



class ArtCombatBrowserTest(ArtSceneBrowserTest):
    """Combat portrait overlay and catalog removal journeys.

    These tests engage the seeded monster through the real server and therefore
    boot one isolated server per test, like the combat-menu browser tests.
    """

    def setUp(self) -> None:
        os.environ["ELOSERN_BROWSER_ART"] = "done"
        super().setUp()
        os.environ.pop("ELOSERN_BROWSER_ART", None)

    def _engage(self, page):
        target = art_room_monster_key()
        page.evaluate("([t]) => Evennia.msg('text', [`engage ${t}`], {})", [target])
        wait_for_store_state(page, _in_combat_mode)
        return store_state(page)

    def _focus_combat_dock(self, page) -> None:
        """Focus the action dock and wait for the mounted, unlocked router.

        At the combat root (depth 1) the active row container is the pane's
        vertical command list, which carries ``data-testid="dock-menu"`` like
        every other frame's row container. Waiting for that container
        proves the KeyboardRouter frame is mounted; waiting for
        ``isMutationInFlight()`` false closes the submission gate. Together
        they guarantee a subsequent Enter press reaches the KeyboardRouter and
        is never swallowed by the command-line field (H5: the retired
        command drawer's successor, webclient-hud-05-overlays-and-command-line).
        """
        focus_action_dock(page)
        page.wait_for_function(
            "() => !!document.querySelector('[data-testid=\"dock-menu\"]')",
            timeout=15000,
        )
        wait_for_store_state(page, _mutations_unlocked, timeout=15000)

    def _wait_combat_row_key(
        self, page, key: str, timeout: int = 15000, row_zero: bool = False
    ) -> None:
        """Wait until a mounted combat row in the action dock carries a key.

        With ``row_zero`` the predicate is scoped to the first combat row
        (``#combat-row-0``, the menu frame's first cell); otherwise any
        ``#combat-row-*`` row matching the exact key qualifies (the focused
        cell after navigation).
        """
        if row_zero:
            page.wait_for_function(
                "(key) => (() => {"
                "  const row = document.querySelector('#combat-row-0');"
                "  return row && row.dataset.itemKey && "
                "    row.dataset.itemKey.indexOf(key) === 0;"
                "})()",
                arg=key,
                timeout=timeout,
            )
            return
        page.wait_for_function(
            "(key) => (() => {"
            "  var rows = document.querySelectorAll('#action-dock [data-item-key]');"
            "  for (var i = 0; i < rows.length; i++) {"
            "    if (rows[i].dataset.itemKey === key) { return true; }"
            "  }"
            "  return false;"
            "})()",
            arg=key,
            timeout=timeout,
        )

    @covers_requirement("webclient-art-panel::contextual-portrait-focus-is-client-local-and-verified")
    def test_combat_portrait_overlay_shows_name_and_role(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        state = self._engage(page)
        art = state["panels"]["art"]
        # The combat catalog mirrors the participants.
        combat = state["panels"]["context_actions"]
        self.assertEqual(
            set(art["portrait_catalog"]),
            {str(p["identity"]) for p in combat["participants"]},
        )
        # H3: the combat portrait renders in the ParticipantFrame (the 我方/敵方
        # token rows). Scope to the first (focused) row to avoid a strict-mode
        # violation.
        wait_for_store_state(page, _art_portrait_ready, PORTRAIT_TILE_DOM, timeout=15000)
        name = page.locator(".participant-frame__name").first.inner_text()
        role = page.locator(".participant-frame__group-label").first.inner_text()
        self.assertTrue(name.strip())
        self.assertIn(role, ("我方", "敵方"))
        # No focus packet was ever sent.
        self.assertEqual(sent_action_count(page, None), 0)

    @covers_requirement("webclient-art-panel::contextual-portrait-focus-is-client-local-and-verified")
    def test_portrait_overlay_usable_at_the_reference_viewport(self):
        page = self.logged_in_page((1451, 790))
        self._engage(page)
        wait_for_store_state(page, _art_portrait_ready, PORTRAIT_TILE_DOM, timeout=15000)
        # H3: the combat portrait renders in the ParticipantFrame; scope the
        # assertions to the first participant row to avoid a strict-mode
        # violation.
        self.assertTrue(page.locator(".participant-frame__row").first.is_visible())
        self.assertTrue(page.locator(".participant-frame__name").first.inner_text().strip())
        self.assertTrue(page.locator('[data-testid="scene-backdrop-image"]').is_visible())

    @covers_requirement("webclient-art-panel::contextual-portrait-focus-is-client-local-and-verified")
    @covers_requirement("webclient-browser-verification::art-panel-portrait-keyboard-journeys-establish-dock-focus-before-key-presses")
    @covers_requirement("webclient-contextual-hud::basic-attack-starts-focused-on-an-eligible-opposing-candidate")
    def test_keyboard_focus_switches_the_portrait_without_a_packet(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        # H3: the combat participant frame (ParticipantFrame) publishes the
        # first party participant's portrait/name.
        wait_for_store_state(page, _art_portrait_ready, PORTRAIT_TILE_DOM, timeout=15000)
        first_name = page.locator(".participant-frame__name").first.inner_text()
        combat = store_state(page)["panels"]["context_actions"]
        monster_id = next(
            p["identity"]
            for p in combat["participants"]
            if p["team"] == "foes"
        )
        monster_name = next(
            p["display_name"] for p in combat["participants"] if p["team"] == "foes"
        )
        # Focus the root "攻擊" action and open its target menu: the focused
        # target descriptor resolves to that participant's portrait. The dock
        # is focused and its router frame mounted (and unlocked) first, so the
        # Enter press is never swallowed by the command drawer or an editable
        # field. Basic attack opens focused on the first enabled foe the
        # server listed (webclient-combat-command-window), so no key is needed
        # to reach the enemy target.
        self._focus_combat_dock(page)
        page.keyboard.press("Enter")
        # The basic-attack target menu mounts (its first cell is a target row)
        # before navigating it.
        self._wait_combat_row_key(page, "target-", row_zero=True)
        self._wait_combat_row_key(page, "target-" + str(monster_id))
        wait_for_store_state(
            page,
            lambda state: state.get("focus", {}).get("key") == "target-" + str(monster_id),
        )
        # H3: after navigating to the enemy target, the participant frame
        # (ParticipantFrame) shows the monster's name in the 敵方 group.
        wait_for_store_state(
            page,
            _art_portrait_ready,
            {
                "selector": "[data-testid=\"participant-frame\"]",
                "predicate": (
                    f"() => {{ const f = document.querySelector('[data-testid=\"participant-frame\"]');"
                    f" if (!f) {{ return false; }}"
                    f" const names = Array.from(f.querySelectorAll('.participant-frame__name')).map((n) => n.textContent);"
                    f" return names.some((n) => n && n.indexOf('{monster_name}') !== -1); }}"
                ),
                "description": "the participant frame (map anchor island) shows the monster's name",
            },
            timeout=15000,
        )
        # The participant frame's 敵方 row shows the monster's name, distinct
        # from the party's first name.
        monster_name_shown = page.evaluate(
            f"() => {{ const f = document.querySelector('[data-testid=\"participant-frame\"]');"
            f" if (!f) {{ return null; }}"
            f" const names = Array.from(f.querySelectorAll('.participant-frame__name')).map((n) => n.textContent);"
            f" return names.find((n) => n && n.indexOf('{monster_name}') !== -1) || null; }}"
        )
        self.assertNotEqual(monster_name_shown, first_name)
        # No focus packet was ever sent.
        self.assertEqual(sent_action_count(page, None), 0)

    @covers_requirement("webclient-combat-menu::combat-results-update-canonical-panels-and-preserve-narrative-logs")
    @covers_requirement("webclient-browser-verification::art-panel-portrait-keyboard-journeys-establish-dock-focus-before-key-presses")
    def test_defeated_participant_leaves_the_catalog_in_the_same_update(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        combat = store_state(page)["panels"]["context_actions"]
        monster_id = next(
            p["identity"]
            for p in combat["participants"]
            if p["team"] == "foes"
        )
        # Forfeit the battle deterministically (no dice roll): the terminal
        # settlement clears the session and the catalog entry disappears in the
        # same combat update.
        # The combat root is one vertical list (webclient-combat-command-
        # window), so the forfeit row is reached with ArrowDown. Root order:
        # attack, skills, items, 背包 (the client-local drawer row), defend,
        # flee, forfeit.
        self._focus_combat_dock(page)
        for _ in range(6):
            page.keyboard.press("ArrowDown")
            page.wait_for_timeout(60)
        self.assertEqual(
            store_state(page).get("focus", {}).get("key"),
            "forfeit",
            "the forfeit row is the focused root cell",
        )
        page.keyboard.press("Enter")  # open the secondary Forfeit menu
        # The confirmation frame mounts before the confirming Enter.
        self._wait_combat_row_key(page, "confirm-forfeit")
        page.keyboard.press("Enter")  # confirm-forfeit
        wait_for_store_state(page, _out_of_combat_mode, timeout=15000)
        art = store_state(page)["panels"]["art"]
        self.assertNotIn(str(monster_id), art["portrait_catalog"])


if __name__ == "__main__":
    import unittest

    unittest.main()
