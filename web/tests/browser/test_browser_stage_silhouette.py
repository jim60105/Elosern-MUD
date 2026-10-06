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
# The figure's own edges, told apart from the fill's drop shadow and the floor
# glow that share the element's box and sit within the loose tolerance above.
# Masked edges are the art's own soft rim rather than a hard cut, so a filled
# edge sits ~4px inside the alpha bounds the mask was cut from at this frame;
# FIGURE_EDGE_TOLERANCE_PX leaves room for that. A stretched fill moves this
# frame's horizontal edges ~17px (15-23px across the committed keys) and a
# `cover` fit cuts the figure's own top away, so both stay outside it. The
# ratio check is the scale-free half of the same claim and the area check
# catches a fill that fades or erodes inside those edges: this frame's own
# mask measures ~0.91 of the expected alpha area, the missing part being the
# art's soft rim, so the floor leaves that room.
FILL_STRICT_TOLERANCE = 4
FIGURE_EDGE_TOLERANCE_PX = 8.0
FIGURE_RATIO_TOLERANCE = 0.06
FIGURE_AREA_FLOOR = 0.7


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

    def _painted_rect(
        self, page
    ) -> tuple[tuple[float, float, float, float], int]:
        """The filled figure's bounds and pixel count, from the element's screenshot."""
        image = Image.open(io.BytesIO(page.locator(MASK_FILL).screenshot())).convert("RGBA")
        width, height = image.size
        xs: list[int] = []
        ys: list[int] = []
        painted = 0
        for x in range(0, width):
            for y in range(0, height):
                red, green, blue, alpha = image.getpixel((x, y))
                if alpha > 200 and all(
                    abs(channel - target) <= FILL_STRICT_TOLERANCE
                    for channel, target in zip((red, green, blue), FILL_RGB)
                ):
                    painted += 1
                    xs.append(x)
                    ys.append(y)
        self.assertTrue(painted, "the mask paints the figure")
        rect = (min(xs) / width, min(ys) / height, max(xs) / width, max(ys) / height)
        return rect, painted

    def _source_alpha_box(self, page) -> dict:
        """The mask image's own alpha bounds, from the browser's own decode.

        The frame is asked to render this image's proportions, so the
        expectation is read from the very resource the mask binds — the same
        URL the probe image carries — rather than copied into the test.
        """
        return page.evaluate(
            """async (sel) => {
              const fill = document.querySelector(sel);
              const probe = fill.parentElement.querySelector('.reference-artwork__mask-probe');
              const image = new Image();
              image.src = probe.src;
              await image.decode();
              const canvas = document.createElement('canvas');
              canvas.width = image.naturalWidth;
              canvas.height = image.naturalHeight;
              const ctx = canvas.getContext('2d');
              ctx.drawImage(image, 0, 0);
              const pixels = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
              let left = canvas.width;
              let top = canvas.height;
              let right = -1;
              let bottom = -1;
              let painted = 0;
              for (let y = 0; y < canvas.height; y += 1) {
                for (let x = 0; x < canvas.width; x += 1) {
                  if (pixels[(y * canvas.width + x) * 4 + 3] > 200) {
                    painted += 1;
                    if (x < left) left = x;
                    if (y < top) top = y;
                    if (x > right) right = x;
                    if (y > bottom) bottom = y;
                  }
                }
              }
              if (right < 0) {
                throw new Error('the mask image carries no alpha');
              }
              return {
                width: canvas.width,
                height: canvas.height,
                left: left,
                top: top,
                right: right,
                bottom: bottom,
                pixels: painted,
              };
            }""",
            MASK_FILL,
        )

    @staticmethod
    def _contained_figure_rect(geometry: dict, source: dict) -> tuple[float, float, float, float]:
        """The figure's bounds under a contained, bottom-centered mask.

        `contain` scales the image uniformly to fit the box, so the image's
        alpha bounds map linearly onto it; the mask is anchored at the box's
        bottom-center, so the image's bottom edge is the box's.
        """
        box_width = geometry["boxWidth"]
        box_height = geometry["boxHeight"]
        scale = min(box_width / source["width"], box_height / source["height"])
        rendered_width = source["width"] * scale
        rendered_height = source["height"] * scale
        origin_x = (box_width - rendered_width) / 2
        origin_y = box_height - rendered_height
        return (
            (origin_x + source["left"] * scale) / box_width,
            (origin_y + source["top"] * scale) / box_height,
            (origin_x + source["right"] * scale) / box_width,
            (origin_y + source["bottom"] * scale) / box_height,
        )

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
        """The figure stands on the stage floor at its own proportions.

        `contain` fits the whole image inside the actor's box with one uniform
        scale and `bottom center` anchors it at the box's floor — pinned above
        by the computed style and the box's own bottom edge — so the figure
        keeps the committed image's proportions: the filled pixels must occupy
        the box-space the image's own alpha bounds imply, at their own area.
        A stretched mask would widen the figure to the box and a `cover` fit
        would cut its top away. The committed silhouettes carry their own alpha
        from near their top edge, so the frame above the figure is not uniform
        — this measures the geometry those bounds imply instead of assuming an
        empty top strip.
        """
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
                boxWidth: box.width,
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
        source = self._source_alpha_box(page)
        expected = self._contained_figure_rect(geometry, source)
        painted, painted_pixels = self._painted_rect(page)
        sizes = (
            geometry["boxWidth"],
            geometry["boxHeight"],
            geometry["boxWidth"],
            geometry["boxHeight"],
        )
        for index, edge in enumerate(("left", "top", "right", "bottom")):
            with self.subTest(edge=edge):
                self.assertAlmostEqual(
                    painted[index] * sizes[index],
                    expected[index] * sizes[index],
                    delta=FIGURE_EDGE_TOLERANCE_PX,
                    msg=(
                        f"the figure's {edge} edge must carry the image's own alpha "
                        "bounds, uniformly scaled and floored"
                    ),
                )
        # The same claim without the letterbox origin: the figure's own
        # width-to-height ratio is the image's alpha bounds' ratio, which a
        # stretched mask would widen by ~20%.
        painted_ratio = ((painted[2] - painted[0]) * geometry["boxWidth"]) / (
            (painted[3] - painted[1]) * geometry["boxHeight"]
        )
        expected_ratio = ((expected[2] - expected[0]) * geometry["boxWidth"]) / (
            (expected[3] - expected[1]) * geometry["boxHeight"]
        )
        self.assertAlmostEqual(
            painted_ratio / expected_ratio,
            1.0,
            delta=FIGURE_RATIO_TOLERANCE,
            msg="the figure keeps the image's own proportions, never stretched",
        )
        # And it is the figure's whole area rather than an eroded or faded copy
        # of it: `contain` scales the source uniformly, so the filled pixels are
        # the source's own alpha pixels at that scale.
        scale = min(
            geometry["boxWidth"] / source["width"],
            geometry["boxHeight"] / source["height"],
        )
        self.assertGreaterEqual(
            painted_pixels,
            source["pixels"] * scale * scale * FIGURE_AREA_FLOOR,
            "the mask paints the figure's own alpha area",
        )
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
