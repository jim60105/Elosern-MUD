"""Stage silhouette acceptance (builtin-silhouette-stage-fallback).

The stage actors draw the server-resolved built-in silhouette as the committed
image's own alpha mask: each fallback key paints its own figure, floor-aligned
and aspect-preserved at the entry's stage position, with the actor's name and
the truthful state label outside the decorative mask; a resolved real image
replaces it; an image-load failure returns to the carried silhouette without
claiming generation success; and a failed bundled mask keeps the actor name and
the truthful label with a usable frame.

Everything is deterministic and local: the dialogue host's catalog entry is
injected as a schema-valid payload, and the committed `/art/defaults/` images
are served by the managed server's own media route (no remote request, no
image service).
"""

from __future__ import annotations

import io

from PIL import Image

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import inject_snapshot, valid_local_map_panel
from ._journey_support import _SCENE_PNG_BYTES, _wait_mode

SCENE_URL = "/art/scene.png"
REAL_URL = "/art/portrait_7.png"
BROKEN_URL = "/art/broken_7.png"
# The committed built-in silhouettes, served by the real media route.
FALLBACK_KEYS = ("man", "woman", "boy", "girl", "elder", "monster_anon")
FALLBACK_FACE_RECT = {"x": 0.35, "y": 0.03, "w": 0.29, "h": 0.16}
STAGE_TRIPLE = {"scale": 1.0, "x": 0.0, "y": 0.0}
FACE_RECT = {"x": 0.25, "y": 0.06, "w": 0.5, "h": 0.5}

# The active host actor (a leaving crossfade copy is inert).
ACTOR = '[data-anchor="actor-right"] [data-testid="stage-actor"]:not([inert])'
MASK = ACTOR + " .reference-artwork__mask"
MASK_FILL = ACTOR + " .reference-artwork__mask-fill"
PLACEHOLDER_CARD = ACTOR + " .reference-artwork__chest"

# ReferenceArtwork's dark silhouette fill (`#17191f`), with the tolerance an
# antialiased alpha edge needs.
FILL_RGB = (23, 25, 31)
FILL_TOLERANCE = 26


def _fallback(key: str) -> dict:
    return {"key": key, "url": f"/art/defaults/{key}.webp", "face_rect": dict(FALLBACK_FACE_RECT)}


def _entry(**overrides) -> dict:
    """One schema-valid host catalog entry (a silhouette placeholder row)."""
    value = {
        "subject_key": "npc_7",
        "status": "pending",
        "url": None,
        "aspect_ratio": None,
        "alt": "店長的肖像",
        "placeholder": {"kind": "missing", "label": "肖像生成中"},
        "face_rect": None,
        "stage": None,
        "origin": "silhouette",
        "fallback": _fallback("elder"),
        "context": {"name": "店長", "role": "對話對象"},
    }
    value.update(overrides)
    return value


def _art_panel(entry: dict) -> dict:
    return {
        "schema_version": 2,
        "available": True,
        "kind": "scene",
        "scene": {
            "archetype": None,
            "label": "南門街道",
            "subject_key": None,
            "status": "done",
            "url": SCENE_URL,
            "aspect_ratio": "16:9",
            "alt": "當前場景",
            "placeholder": None,
            "stage": dict(STAGE_TRIPLE),
        },
        "portrait_catalog": {"7": entry},
    }


def _dialogue_panel() -> dict:
    return {
        "schema_version": 2,
        "available": True,
        "kind": "dialogue",
        "host": {"identity": 7, "display_name": "店長", "portrait_ref": "7"},
        "bond_stage": "熟識",
        "line": "又見面了。今晚爐火正旺。",
        "choices": [{"keyword_id": "news", "label": "最近有什麼消息？"}],
    }


class StageSilhouetteBrowserTest(BrowserAcceptanceTest):
    """The built-in silhouette on the real stage, on the shared server."""

    def _serve_scene(self, page) -> None:
        """Fulfil the scene image so the backdrop never races a load failure."""
        page.route(
            "**/art/scene.png",
            lambda route: route.fulfill(
                status=200, content_type="image/png", body=_SCENE_PNG_BYTES
            ),
        )

    def _stand_host(self, page, entry: dict) -> None:
        inject_snapshot(
            page,
            {
                "local_map": valid_local_map_panel(),
                "art": _art_panel(entry),
                "dialogue": _dialogue_panel(),
            },
            mode="dialogue",
        )
        _wait_mode(page, "dialogue")
        page.wait_for_selector(ACTOR, timeout=15000)

    def _open_dialogue(self, entry: dict, motion_level: str = "off"):
        page = self.logged_in_page((1451, 790), motion_level)
        self._serve_scene(page)
        self._stand_host(page, entry)
        return page

    def _masked_url(self, page) -> str:
        return page.evaluate(
            "(sel) => { const s = getComputedStyle(document.querySelector(sel));"
            " return s.maskImage || s.webkitMaskImage || ''; }",
            MASK_FILL,
        )

    def _fill_share(self, page, fraction: dict) -> float:
        """The share of sampled pixels inside ``fraction`` painted with the fill.

        ``fraction`` gives each edge as a share of the element's own box, so a
        caller can ask about the top strip, the floor band, or the body.
        """
        image = Image.open(io.BytesIO(page.locator(MASK_FILL).screenshot())).convert("RGBA")
        return self._painted_share(image, fraction)

    @staticmethod
    def _painted_share(image, fraction: dict) -> float:
        width, height = image.size
        x0 = int(width * fraction["left"])
        x1 = max(x0 + 1, int(width * fraction["right"]))
        y0 = int(height * fraction["top"])
        y1 = max(y0 + 1, int(height * fraction["bottom"]))
        painted = 0
        sampled = 0
        for x in range(x0, x1, 2):
            for y in range(y0, y1, 2):
                sampled += 1
                red, green, blue, alpha = image.getpixel((x, y))
                if alpha > 200 and all(
                    abs(channel - target) <= FILL_TOLERANCE
                    for channel, target in zip((red, green, blue), FILL_RGB)
                ):
                    painted += 1
        return painted / sampled if sampled else 0.0

    @covers_requirement(
        "webclient-art-panel::the-reference-artwork-frame-presents-a-portrait-entry-truthfully-through-cover-fit-and-rect-crop"
    )
    @covers_requirement(
        "webclient-contextual-hud::standing-portraits-retain-contours-and-truthful-grounded-fallbacks"
    )
    def test_each_built_in_key_paints_its_own_alpha_mask_on_the_stage(self):
        """Acceptance 7/8: adult male/female, boy/girl, elder, and monster
        actors show the built-in silhouette their server-resolved key selects
        — never one shared shape — drawn as the committed image's own alpha
        mask, with the former inline SVG gone and the actor's name and state
        label outside the decorative mask."""
        page = self._open_dialogue(_entry(fallback=_fallback(FALLBACK_KEYS[0])))
        page.wait_for_selector(MASK_FILL, timeout=15000)
        first = page.evaluate(
            """(sel) => {
              const actor = document.querySelector(sel);
              const fill = actor.querySelector('.reference-artwork__mask-fill');
              const style = getComputedStyle(fill);
              return {
                maskImage: style.maskImage || style.webkitMaskImage,
                maskSize: style.maskSize,
                background: style.backgroundColor,
                chestOutside: !fill.querySelector('.reference-artwork__chest'),
                svg: fill.parentElement.querySelector('svg') !== null,
                label: actor.querySelector('.reference-artwork__placeholder-label').textContent,
                name: actor.querySelector('.reference-artwork__identity').textContent,
                decorative: actor.querySelector('.reference-artwork__mask').getAttribute('aria-hidden'),
              };
            }""",
            ACTOR,
        )
        # The masked fill is the committed built-in image, alpha-only.
        self.assertIn("/art/defaults/man.webp", first["maskImage"])
        self.assertEqual(first["background"], "rgb(23, 25, 31)")
        self.assertEqual(first["maskSize"], "contain")
        self.assertTrue(first["chestOutside"], "labels render outside the mask")
        self.assertFalse(first["svg"], "the former inline SVG is gone")
        self.assertEqual(first["decorative"], "true")
        self.assertEqual(first["name"], "店長")
        self.assertEqual(first["label"], "肖像生成中")
        for key in FALLBACK_KEYS:
            with self.subTest(key=key):
                self._stand_host(page, _entry(fallback=_fallback(key)))
                page.wait_for_selector(MASK_FILL, timeout=15000)
                self.assertIn(f"/art/defaults/{key}.webp", self._masked_url(page))
        page.close()

    @covers_requirement(
        "webclient-art-panel::the-reference-artwork-frame-presents-a-portrait-entry-truthfully-through-cover-fit-and-rect-crop"
    )
    def test_the_masked_figure_is_floor_aligned_aspect_preserved_and_unstretched(self):
        """The figure stands on the stage floor at its own proportions: the
        mask is contained and bottom-centered inside the actor's box, so the
        frame above the figure stays unpainted while the floor band carries
        the figure — a stretched fill would paint the whole box."""
        page = self._open_dialogue(_entry(fallback=_fallback("woman")))
        page.wait_for_selector(MASK_FILL, timeout=15000)
        page.wait_for_timeout(200)
        geometry = page.evaluate(
            """(sel) => {
              const fill = document.querySelector(sel);
              const style = getComputedStyle(fill);
              const actor = fill.closest('[data-testid="stage-actor"]');
              const box = fill.getBoundingClientRect();
              const stage = actor.getBoundingClientRect();
              return {
                size: style.maskSize,
                position: style.maskPosition,
                repeat: style.maskRepeat,
                boxBottom: box.bottom,
                boxHeight: box.height,
                stageBottom: stage.bottom,
                stageHeight: stage.height,
              };
            }""",
            MASK_FILL,
        )
        self.assertEqual(geometry["size"], "contain")
        self.assertEqual(geometry["position"], "50% 100%")
        self.assertEqual(geometry["repeat"], "no-repeat")
        # The figure's box bottoms out on the stage floor: the actor's bottom.
        self.assertAlmostEqual(geometry["boxBottom"], geometry["stageBottom"], delta=1.5)
        self.assertGreaterEqual(geometry["boxHeight"], geometry["stageHeight"] - 1.5)
        top = self._fill_share(page, {"left": 0.0, "right": 1.0, "top": 0.0, "bottom": 0.06})
        floor = self._fill_share(page, {"left": 0.2, "right": 0.8, "top": 0.94, "bottom": 1.0})
        body = self._fill_share(page, {"left": 0.3, "right": 0.7, "top": 0.4, "bottom": 0.7})
        self.assertLess(top, 0.02, "the frame above the figure must stay unpainted")
        self.assertGreater(floor, 0.02, "the figure must reach the stage floor")
        self.assertGreater(body, 0.2, "the figure's own proportions must paint the body band")
        page.close()

    @covers_requirement(
        "webclient-art-panel::the-reference-artwork-frame-presents-a-portrait-entry-truthfully-through-cover-fit-and-rect-crop"
    )
    def test_a_resolved_image_replaces_the_silhouette_and_failure_returns_to_it(self):
        """Acceptance 8: the stage transitions to a real image when one
        resolves, and an image-load failure returns to the already-carried
        silhouette with the load-failure label — one media request for the
        failed URL and no generation claim."""
        requests: list[str] = []
        page = self._open_dialogue(_entry())
        page.route(
            f"**{REAL_URL}",
            lambda route: route.fulfill(
                status=200, content_type="image/png", body=_SCENE_PNG_BYTES
            ),
        )
        self._stand_host(
            page,
            _entry(
                status="done",
                url=REAL_URL,
                aspect_ratio="3:4",
                placeholder=None,
                face_rect=dict(FACE_RECT),
                stage=dict(STAGE_TRIPLE),
                origin="runtime",
            ),
        )
        page.wait_for_selector(f'{ACTOR} img[src$="{REAL_URL}"]', timeout=15000)
        self.assertEqual(page.locator(MASK).count(), 0, "the real image stands alone")

        def _abort(route):
            requests.append(route.request.url)
            route.abort("failed")

        # A later snapshot hands the same subject a URL that fails to load:
        # the frame returns to the silhouette the payload already carried.
        page.route(f"**{BROKEN_URL}", _abort)
        self._stand_host(
            page,
            _entry(
                status="done",
                url=BROKEN_URL,
                aspect_ratio="3:4",
                placeholder=None,
                face_rect=dict(FACE_RECT),
                stage=dict(STAGE_TRIPLE),
                origin="runtime",
            ),
        )
        page.wait_for_selector(MASK_FILL, timeout=15000)
        state = page.evaluate(
            """(sel) => {
              const actor = document.querySelector(sel);
              return {
                status: actor.querySelector('figure').dataset.status,
                label: actor.querySelector('.reference-artwork__placeholder-label').textContent,
                mask: (getComputedStyle(actor.querySelector('.reference-artwork__mask-fill')).maskImage || ''),
                text: actor.innerText,
              };
            }""",
            ACTOR,
        )
        self.assertEqual(state["status"], "load-failed")
        self.assertEqual(state["label"], "肖像載入失敗")
        self.assertIn("/art/defaults/elder.webp", state["mask"])
        self.assertNotIn("已生成", state["text"])
        # The carried silhouette was already resolved: the failed URL is the
        # only media request the frame made for this entry.
        self.assertEqual(len(requests), 1, requests)
        self.assertTrue(requests[0].endswith(BROKEN_URL), requests)
        page.close()

    @covers_requirement(
        "webclient-art-panel::the-reference-artwork-frame-presents-a-portrait-entry-truthfully-through-cover-fit-and-rect-crop"
    )
    def test_a_failed_bundled_mask_keeps_the_frame_usable(self):
        """A missing bundled resource keeps the actor name and the truthful
        label with no figure standing in for it, and the frame stays usable."""
        page = self.logged_in_page((1451, 790), "off")
        self._serve_scene(page)
        page.route("**/art/defaults/**", lambda route: route.abort("failed"))
        self._stand_host(page, _entry())
        page.wait_for_selector(PLACEHOLDER_CARD, timeout=15000)
        page.wait_for_timeout(300)
        self.assertEqual(page.locator(MASK).count(), 0)
        self.assertEqual(page.locator(MASK_FILL).count(), 0)
        card = page.locator(PLACEHOLDER_CARD).first.inner_text()
        self.assertIn("店長", card)
        self.assertIn("肖像生成中", card)
        # Nothing dark stands in for the missing figure: the actor's box is
        # sampled above the ground shadow's own band.
        box = page.locator(ACTOR).bounding_box()
        self.assertIsNotNone(box)
        self.assertGreater(box["width"], 0)
        self.assertGreater(box["height"], 0)
        screenshot = page.locator(ACTOR).screenshot()
        image = Image.open(io.BytesIO(screenshot)).convert("RGBA")
        dark = self._painted_share(
            image, {"left": 0.0, "right": 1.0, "top": 0.0, "bottom": 0.92}
        )
        self.assertLess(dark, 0.05, "no solid fill stands in for the figure")
        # The frame stays reachable: the actor carries no focusable surface.
        self.assertEqual(
            page.locator(
                f'{ACTOR} :is(button, a, input, textarea, select, [tabindex])'
            ).count(),
            0,
        )
        page.close()
