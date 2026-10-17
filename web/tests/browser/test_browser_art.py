"""Art panel browser acceptance (webclient-art-panel 8.1-8.2).

Drives the real Evennia server's art panel through the Vue SPA scene
renderer and contextual portrait overlay. The seed fixture (``ELOSERN_BROWSER_ART``)
places the character in a validated scene room carrying authored scene metadata
with a generated record (done / a pending regeneration with its prior output
preserved / a failed regeneration) and a named-policy NPC plus a living monster.
Journeys assert the canonical descriptor's own facts, same-origin URL rendering,
the required bundled fallback for an ungenerated scene, the reached failure of a
failed regeneration, keyboard-only full view, portrait overlay with name/role
context, client-local focus switching with no packet, no-focus no-card, combat
results removing the catalog entry in the same update, and the
subject-eligibility payload exclusion.
"""

from __future__ import annotations

import base64
import os

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest, ui_scale
from .browser_helpers import (
    focus_action_dock,
    inject_snapshot,
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

# The art fixture's archetype/display pair for the CURRENT boot mode (kit row
# under the synthetic install, shipped row otherwise). Resolved lazily from the
# boot-mode flag the journey's own runtime sets before startup (see
# ArtSceneBrowserTest), never frozen at module import: a journey's boot mode is
# a per-class decision.
from web.browser_support.browser_fixtures_data import art_room_monster_key, art_scene_values


def _scene_archetype_key() -> str:
    """The art fixture room's archetype key for the current boot mode."""
    return art_scene_values()[0]


def _scene_label() -> str:
    """The art fixture archetype's authored display label for the current boot mode."""
    return art_scene_values()[1]


def _scene_subject() -> str:
    """The art fixture's full scene subject key for the current boot mode."""
    return f"scene:{_scene_archetype_key()}"

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
    # The plate stands 12px above the command line at the reference, scaled by
    # the chrome factor like every other inset (`.scene-backdrop__plate`'s
    # `bottom: calc(var(--stage-content-bottom) + 12px * var(--ui-scale))`).
    test.assertLessEqual(
        gap,
        12 * ui_scale(viewport) + 1,
        "the caption floats %.0fpx above the command line at %s" % (gap, size),
    )
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


def _scene_artwork(state: dict) -> dict:
    """The committed scene descriptor (the v4 wire's own fact set)."""
    scene = ((state.get("panels") or {}).get("art") or {}).get("scene") or {}
    return scene.get("artwork") or {}


def _scene_candidate(state: dict, source_prefix: str) -> dict | None:
    """The descriptor's image candidate at one chain position, or None."""
    for entry in _scene_artwork(state).get("attempts") or []:
        if entry.get("type") == "image" and str(entry.get("source_id", "")).startswith(source_prefix):
            return entry
    return None


def _art_scene_exhausted(state: dict) -> bool:
    """The chain ran out: every permitted image source failed or is absent."""
    art = (state.get("panels") or {}).get("art") or {}
    return art.get("available") is True and _scene_candidate(state, "scene.bundled:") is None


def _art_scene_failed(state: dict) -> bool:
    """The seeded art scene's recorded generation is failed."""
    return _scene_artwork(state).get("generation_state") == "failed"


def _art_scene_done(state: dict) -> bool:
    """The scene's recorded generation is done (a browser load failure keeps it done)."""
    return _scene_artwork(state).get("generation_state") == "done"


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



# H3, migrated by webclient-combat-formation: in combat mode the ArtPanel is
# hidden, the portraits stand on the stage, and each drawn figure other than
# the controlled one carries its glance plate (the participant frame's rows
# are gone). This DOM readiness targets the first figure plate.
PORTRAIT_TILE_DOM = {
    "selector": '[data-testid="figure-plate"]',
    "predicate": (
        "() => { const t = document.querySelector('[data-testid=\"figure-plate\"]'); "
        "if (!t) { return false; } "
        "const r = t.getBoundingClientRect(); "
        "return r.width > 0 && r.height > 0; }"
    ),
    "description": "a combat figure plate is rendered and visible",
}


def _plate_reading(label: str) -> tuple[str, str]:
    """A plate's accessible name split into (name and token, side label)."""
    who, side, _hp = label.split("，", 2)
    return who, side

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

    ``SYNTHETIC_CATALOGS`` selects the boot mode. A journey that renders the
    scene chain's REQUIRED bundled illustration (the pending and failed
    regeneration cases) needs the SHIPPED catalogs: the synthetic kit declares
    no bundled scene definitions, so its kit archetype has no required
    illustration and the chain has no bundled candidate at all. A journey that
    relies on the generated-only chain degrading with no bundled fallback
    (``ArtImageLoadFailureTest``) keeps the synthetic install.
    """

    #: Boot the isolated server with the synthetic kit catalogs (harness
    #: default) rather than the shipped ones.
    SYNTHETIC_CATALOGS = True

    def setUp(self) -> None:
        from .fixtures import create_runtime
        from .harness import ManagedServer

        # The boot-mode flag is set BEFORE seed and startup, on the isolated
        # runtime AND in this process: the seed/server read the runtime env,
        # while the Playwright-side fixture vocabulary
        # (``art_scene_values``/``art_room_monster_key``) reads this process's
        # environment, so the two must agree on the same shipped or kit keys.
        flag = "1" if self.SYNTHETIC_CATALOGS else "0"
        previous = os.environ.get("ELOSERN_BROWSER_SYNTH_CATALOGS")
        os.environ["ELOSERN_BROWSER_SYNTH_CATALOGS"] = flag
        self.addCleanup(self._restore_synth_flag, previous)
        runtime = create_runtime()
        runtime.env["ELOSERN_BROWSER_SYNTH_CATALOGS"] = flag
        self.server = ManagedServer(runtime=runtime)
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    @staticmethod
    def _restore_synth_flag(previous: str | None) -> None:
        if previous is None:
            os.environ.pop("ELOSERN_BROWSER_SYNTH_CATALOGS", None)
        else:
            os.environ["ELOSERN_BROWSER_SYNTH_CATALOGS"] = previous

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
        wait_for_store_state(page, _art_scene_done, timeout=20000)
        artwork = _scene_artwork(store_state(page))
        self.assertEqual(artwork["generation_subject"], _scene_subject())
        generated = _scene_candidate(store_state(page), "scene.generated:")
        self.assertIsNotNone(generated, "the done scene carries no generated candidate")
        resource = generated["resource"]
        self.assertTrue(resource["url"].startswith(f"/art/scene/{_scene_archetype_key()}.png"))
        self.assertEqual(resource["origin"], "runtime")
        # The image element is present with a same-origin src: the element the
        # shared driver issued, presenting the descriptor's own resource.
        page.wait_for_selector('[data-testid="scene-backdrop-image"]', timeout=20000)
        img = page.locator('[data-testid="scene-backdrop-image"]')
        self.assertEqual(img.count(), 1)
        self.assertEqual(img.get_attribute("src"), resource["url"])
        self.assertTrue(img.get_attribute("src").startswith("/art/"))
        self.assertNotIn("http://", img.get_attribute("src"))
        # A successfully resolved scene carries no error marker at all.
        self.assertEqual(page.locator('[data-testid="scene-backdrop-placeholder"]').count(), 0)

    @covers_requirement("webclient-art-panel::the-scene-payload-resolves-only-validated-archetypes-with-truthful-placeholders")
    def test_alternative_text_is_present_outside_the_bitmap(self):
        page = self.logged_in_page()
        # Requirement: the scene label and alternative text SHALL remain visible
        # outside the bitmap. The scene moved to the full-bleed `SceneBackdrop`
        # (H1); the label renders as DOM text (`[data-testid="scene-backdrop-label"]`).
        # The server's descriptor states ``alt == label``, and the caption never
        # repeats an identical alternative text (the archived HUD delta), so the
        # label IS the visible alternative text and no duplicate alt node renders
        # beside it.
        label = page.locator('[data-testid="scene-backdrop-label"]')
        label.wait_for(state="visible", timeout=20000)
        self.assertEqual(label.inner_text(), _scene_label())
        self.assertEqual(
            page.locator('[data-testid="scene-backdrop-alt"]').count(),
            0,
            "an alt identical to the label is not repeated",
        )
        # A descriptor whose alternative text really differs from its label
        # states both, still outside the bitmap. The distinct alt is injected
        # through the committed descriptor (the same panel with one changed
        # bounded display string), never a fabricated artwork fact.
        distinct = "夜裡的酒館大廳，昏黃的燈火與木頭的氣味"
        panel = store_state(page)["panels"]["art"]
        scene = dict(panel["scene"], alt=distinct)
        inject_snapshot(page, {"art": dict(panel, scene=scene)}, mode="exploration")
        alt = page.locator('[data-testid="scene-backdrop-alt"]')
        alt.wait_for(state="visible", timeout=15000)
        self.assertEqual(alt.inner_text(), distinct)
        self.assertEqual(
            page.locator('[data-testid="scene-backdrop-label"]').inner_text(),
            _scene_label(),
        )

    @covers_requirement("webclient-art-panel::art-panel-browser-acceptance-is-keyboard-first-accessible-and-desktop-bounded")
    def test_scene_caption_and_status_usable_at_the_reference_viewport(self):
        page = self.logged_in_page((1451, 790))
        # The done scene image, its caption label and alt, and the pending
        # status line remain visible at the reference viewport.
        img = page.locator('[data-testid="scene-backdrop-image"]')
        self.assertEqual(img.count(), 1)
        self.assertTrue(img.is_visible())
        self.assertEqual(page.locator('[data-testid="scene-backdrop-label"]').inner_text(), _scene_label())
        # The scene's own alternative text equals its label here, so the caption
        # states it once and renders no duplicate alt node.
        self.assertEqual(page.locator('[data-testid="scene-backdrop-alt"]').count(), 0)
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
    # The pending regeneration presents the scene's REQUIRED bundled
    # illustration, which only the shipped catalogs declare.
    SYNTHETIC_CATALOGS = False

    def setUp(self) -> None:
        os.environ["ELOSERN_BROWSER_ART"] = "pending"
        super().setUp()
        os.environ.pop("ELOSERN_BROWSER_ART", None)

    @covers_requirement("webclient-art-panel::the-scene-payload-resolves-only-validated-archetypes-with-truthful-placeholders")
    @covers_requirement("webclient-contextual-hud::the-scene-backdrop-renders-the-art-payload-truthfully-behind-the-stage")
    def test_pending_scene_shows_its_own_bundled_art_with_progress(self):
        page = self.logged_in_page()
        wait_for_store_state(
            page,
            lambda state: _scene_artwork(state).get("generation_state") == "pending",
            timeout=20000,
        )
        artwork = _scene_artwork(store_state(page))
        # A pending regeneration claims no generated candidate at all, and its
        # own REQUIRED bundled illustration is the current attempt.
        self.assertIsNone(_scene_candidate(store_state(page), "scene.generated:"))
        bundled = _scene_candidate(store_state(page), "scene.bundled:")
        self.assertIsNotNone(bundled, "the pending scene carries no bundled candidate")
        page.wait_for_selector('[data-testid="scene-backdrop-image"]', timeout=20000)
        self.assertEqual(
            page.locator('[data-testid="scene-backdrop-image"]').first.get_attribute("src"),
            bundled["resource"]["url"],
        )
        # Expected absence carries no error styling, and the caption states the
        # factual progress.
        self.assertEqual(page.locator('[data-testid="scene-backdrop-placeholder"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="scene-backdrop-failure"]').count(), 0)
        self.assertTrue(page.locator('[data-testid="scene-backdrop-generating"]').count())
        self.assertIsNotNone(artwork.get("generation_subject"))

    @covers_requirement("webclient-contextual-hud::the-scene-backdrop-renders-the-art-payload-truthfully-behind-the-stage")
    def test_pending_generating_notice_clears_dock_and_command_line(self):
        """A pending scene with a prior image renders the explicit generating
        notice; its bounding box stays above the action dock's and the command
        line's top edges at both supported viewports.
        """
        for viewport in ((1451, 790), (2560, 1440)):
            with self.subTest(viewport=viewport):
                page = self.logged_in_page(viewport)
                wait_for_store_state(
                    page,
                    lambda state: _scene_artwork(state).get("generation_state") == "pending",
                    timeout=20000,
                )
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
    # The failed regeneration keeps the scene's REQUIRED bundled illustration on
    # the stage beside its reached-failure caption, so it needs the shipped
    # catalogs that declare it.
    SYNTHETIC_CATALOGS = False

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
    def test_failed_regeneration_keeps_a_visible_reached_failure(self):
        page = self.logged_in_page()
        # Drain the queue with the failing image-generation client, then refresh
        # presentation: the recorded failure is a real reached fact.
        page.evaluate("Evennia.msg('text', ['@art run --limit 1'], {})")
        page.wait_for_timeout(1500)
        page.evaluate("Evennia.msg('text', ['look'], {})")
        # A failed regeneration keeps the scene chain's REQUIRED bundled
        # illustration on the stage and states the reached failure beside it in
        # the caption; only an EXHAUSTED chain (no image at all) degrades to the
        # non-image placeholder. The gate is the shared bounded-wait helper:
        # the committed art-panel store state plus a single-node DOM-readiness
        # descriptor, within one bounded deadline.
        wait_for_store_state(
            page,
            _art_scene_failed,
            {
                "selector": '[data-testid="scene-backdrop-failure"]',
                "predicate": (
                    "() => { const el = document.querySelector('[data-testid=\"scene-backdrop-failure\"]'); "
                    "if (!el) { return false; } const r = el.getBoundingClientRect(); "
                    "return r.width > 0 && r.height > 0 && el.offsetParent !== null; }"
                ),
                "description": "visible reached-failure caption",
            },
            timeout=20000,
        )
        # The reached regeneration failure keeps the healthy bundled fallback
        # displayed beside it — never hidden, and never a broken image.
        self.assertEqual(_scene_artwork(store_state(page)).get("generation_state"), "failed")
        bundled = _scene_candidate(store_state(page), "scene.bundled:")
        self.assertIsNotNone(
            bundled, "the failed regeneration keeps the required bundled illustration"
        )
        image = page.locator('[data-testid="scene-backdrop-image"]')
        image.wait_for(state="visible", timeout=20000)
        self.assertEqual(image.first.get_attribute("src"), bundled["resource"]["url"])
        failure = page.locator('[data-testid="scene-backdrop-failure"]')
        failure.wait_for(state="visible", timeout=20000)
        self.assertTrue(failure.inner_text().strip())
        # The chain is not exhausted, so the non-image placeholder is absent.
        self.assertEqual(
            page.locator('[data-testid="scene-backdrop-placeholder"]').count(),
            0,
            "a failed regeneration with a healthy bundled fallback is not a placeholder state",
        )


class ArtExhaustedSceneTest(ArtSceneBrowserTest):
    """A scene whose every permitted source is unavailable.

    The seeded record is missing, so the descriptor carries no generated
    candidate; the journey additionally makes the bundled illustration
    unavailable, which is the one case that degrades to a non-image state.
    """

    def _exhaust_bundled(self, page) -> None:
        """Fail every committed bundled scene illustration, and nothing else.

        A bundled URL carries the collection's content fingerprint, so the
        route matches the path family the running server serves it from; the
        registration happens BEFORE the page loads so the first request for it
        is the one that fails.
        """
        page.route(
            "**/art/bundled-scene/**",
            lambda route: route.fulfill(status=404, content_type="text/plain", body=b"missing"),
        )

    def setUp(self) -> None:
        os.environ["ELOSERN_BROWSER_ART"] = "missing"
        super().setUp()
        os.environ.pop("ELOSERN_BROWSER_ART", None)

    @covers_requirement(
        "webclient-art-panel::art-degradation-never-blocks-gameplay-or-leaks-rejected-content",
        "webclient-browser-verification::browser-test-waits-gate-on-deterministic-state-within-a-bounded-deadline",
        "webclient-contextual-hud::the-scene-backdrop-renders-the-art-payload-truthfully-behind-the-stage",
    )
    def test_exhausted_scene_uses_one_placeholder_and_play_continues(self):
        from .browser_helpers import login_and_open

        page = self.new_page()
        self._exhaust_bundled(page)
        login_and_open(page, self.webclient_url, self.base_url)
        # The missing-scene placeholder is gated on the committed art-panel
        # store state and the scene-frame-scoped single-node DOM, within one
        # bounded deadline — not a single raw `.count()` sample that a
        # snapshot-refresh double-node window under a loaded CI runner would
        # race.
        wait_for_store_state(
            page,
            _art_scene_exhausted,
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
                from .browser_helpers import login_and_open

                page = self.new_page(viewport)
                self._exhaust_bundled(page)
                login_and_open(page, self.webclient_url, self.base_url)
                # The degraded badge is gated on the committed art-panel
                # store state and the scene-frame-scoped single-node DOM, within one
                # bounded deadline.
                wait_for_store_state(
                    page,
                    _art_scene_exhausted,
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

    def _generated_path(self) -> str:
        """The generated scene output's stable path for the current boot mode.

        Its bounded cache version is part of the URL, so the route matches the
        path and counts every request the browser makes for it.
        """
        return f"/art/scene/{_scene_archetype_key()}.png"

    def _abort_art_media(self, page) -> None:
        """Abort the generated scene media and count its requests."""
        self._art_requests = []

        def _handler(route):
            if route.request.url.split("?")[0].endswith(self._generated_path()):
                self._art_requests.append(route.request.url)
                route.abort("failed")
            else:
                route.continue_()

        # Abort the generated output's own path, before the shared local-only
        # guard is consulted.
        page.route("**/art/scene/**", _handler)

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
            "image_load_failed",
            "an image load failure states the browser's own load fact",
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
        # The combat figures carry their plates (webclient-combat-formation):
        # each names its participant and its side. Scope to the first plate.
        wait_for_store_state(page, _art_portrait_ready, PORTRAIT_TILE_DOM, timeout=15000)
        name, role = _plate_reading(page.locator('[data-testid="figure-plate"]').first.get_attribute("aria-label"))
        self.assertTrue(name.strip())
        self.assertIn(role, ("我方", "敵方"))
        # No focus packet was ever sent.
        self.assertEqual(sent_action_count(page, None), 0)

    @covers_requirement("webclient-art-panel::contextual-portrait-focus-is-client-local-and-verified")
    def test_portrait_overlay_usable_at_the_reference_viewport(self):
        page = self.logged_in_page((1451, 790))
        self._engage(page)
        wait_for_store_state(page, _art_portrait_ready, PORTRAIT_TILE_DOM, timeout=15000)
        # The figures' plates are visible at the reference viewport; scope to
        # the first plate to avoid a strict-mode violation.
        plate = page.locator('[data-testid="figure-plate"]').first
        self.assertTrue(plate.is_visible())
        self.assertTrue(_plate_reading(plate.get_attribute("aria-label"))[0].strip())
        self.assertTrue(page.locator('[data-testid="scene-backdrop-image"]').is_visible())

    @covers_requirement("webclient-art-panel::contextual-portrait-focus-is-client-local-and-verified")
    @covers_requirement("webclient-browser-verification::art-panel-portrait-keyboard-journeys-establish-dock-focus-before-key-presses")
    @covers_requirement("webclient-contextual-hud::basic-attack-starts-focused-on-an-eligible-opposing-candidate")
    def test_keyboard_focus_switches_the_portrait_without_a_packet(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        # The figures' plates are up (webclient-combat-formation).
        wait_for_store_state(page, _art_portrait_ready, PORTRAIT_TILE_DOM, timeout=15000)
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
        # After navigating to the enemy target, the monster's own plate
        # carries the focused-target cue (a non-colour cue, client-local), and
        # no other plate does; its accessible name names the monster.
        wait_for_store_state(
            page,
            _art_portrait_ready,
            {
                "selector": f'[data-testid="figure-plate"][data-identity="{monster_id}"][data-target="true"]',
                "predicate": (
                    f"() => !!document.querySelector("
                    f"'[data-testid=\"figure-plate\"][data-identity=\"{monster_id}\"][data-target=\"true\"]')"
                ),
                "description": "the focused foe's plate carries the target cue",
            },
            timeout=15000,
        )
        targeted = page.locator('[data-testid="figure-plate"][data-target="true"]')
        self.assertEqual(targeted.count(), 1)
        self.assertIn(monster_name, targeted.first.get_attribute("aria-label"))
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
        # Surrender the battle deterministically (no dice roll): the terminal
        # settlement clears the session and the catalog entry disappears in the
        # same combat update.
        # The combat root is one vertical list (webclient-combat-command-
        # window), so the surrender row is reached with ArrowDown. Root order:
        # attack, skills, items, 背包 (the client-local drawer row), defend,
        # dodge, taunt, retreat, surrender.
        self._focus_combat_dock(page)
        for _ in range(8):
            page.keyboard.press("ArrowDown")
            page.wait_for_timeout(60)
        self.assertEqual(
            store_state(page).get("focus", {}).get("key"),
            "surrender",
            "the surrender row is the focused root cell",
        )
        page.keyboard.press("Enter")  # request the server-bound prompt
        # The confirmation card mounts before the confirming Yes.
        card = page.locator('[data-testid="party-exit-question"]')
        card.wait_for(state="visible", timeout=30000)
        card.locator('[data-testid="question-card-yes"]').click()
        wait_for_store_state(page, _out_of_combat_mode, timeout=15000)
        art = store_state(page)["panels"]["art"]
        self.assertNotIn(str(monster_id), art["portrait_catalog"])


if __name__ == "__main__":
    import unittest

    unittest.main()
