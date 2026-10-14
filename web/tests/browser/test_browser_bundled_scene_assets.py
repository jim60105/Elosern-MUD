"""Static-asset browser acceptance for the bundled scene art packs.

Requests the committed ``/static/art/scenes/<key>.webp`` illustrations — the
outdoor pack (``unified-scenes-outdoor-art``), the interior pack
(``unified-scenes-interior-art``), the sacred pack
(``unified-scenes-sacred-art``) and the terminal pack
(``unified-scenes-terminal-art``) — through the running application's own
static-media boundary, with no operator artwork root and no generation
service, and decodes each one in a real browser at the 1451x790 desktop
reference viewport under cover cropping.

Fixture ownership (design.md, "Concrete browser fixture ownership"): the
journey allocates its own isolated runtime, pins the shipped (non-synthetic)
startup catalogs BEFORE seeding and server startup, and boots one real managed
server per test (``ManagedServer(runtime=runtime)`` +
``ManagedServerTearDownMixin``), matching ``ArtSceneBrowserTest``'s per-test
lifecycle rather than the synthetic shared server.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest, DEFAULT_VIEWPORT
from .fixtures import create_runtime
from .harness import ManagedServer, ManagedServerTearDownMixin

# The three committed outdoor illustrations, addressed by full repository
# path. A test-path file may not carry the bare shipped scene keys (the
# test-data independence gate scans this directory), so the pack is addressed
# by the exact tracked paths the closed exception names; the keys themselves
# are pinned by world/art/tests/test_bundled_outdoor_art.py.
OUTDOOR_SCENE_ASSETS = (
    "web/static/art/scenes/wilderness_path.webp",
    "web/static/art/scenes/mountain_path.webp",
    "web/static/art/scenes/coastal_path.webp",
)

# The three committed interior illustrations, addressed by full repository
# path for the same gate reason as the outdoor pack above; the keys are pinned
# by world/art/tests/test_bundled_interior_art.py.
INTERIOR_SCENE_ASSETS = (
    "web/static/art/scenes/tavern_interior.webp",
    "web/static/art/scenes/dungeon_interior.webp",
    "web/static/art/scenes/ruin_interior.webp",
)

# The three committed sacred illustrations, addressed by full repository path
# for the same gate reason as the packs above; the keys are pinned by
# world/art/tests/test_bundled_sacred_art.py.
SACRED_SCENE_ASSETS = (
    "web/static/art/scenes/cave_interior.webp",
    "web/static/art/scenes/shrine_interior.webp",
    "web/static/art/scenes/dream_throne.webp",
)

# The two committed terminal illustrations, addressed by full repository path
# for the same gate reason as the packs above; the keys are pinned by
# world/art/tests/test_bundled_terminal_art.py.
TERMINAL_SCENE_ASSETS = (
    "web/static/art/scenes/forest_path.webp",
    "web/static/art/scenes/city_street.webp",
)

# The repository path prefix that the served ``/static/`` root strips.
STATIC_SOURCE_PREFIX = "web/static/"

# Await the browser's own image decode (not merely the load event) and report
# the decoded natural size; a broken image resolves ``false``.
_AWAIT_DECODE_JS = """async () => {
  const img = document.querySelector("img");
  if (!img) return false;
  try {
    await img.decode();
  } catch (error) {
    return false;
  }
  return img.complete && img.naturalWidth > 0 && img.naturalHeight > 0;
}"""

# Render the decoded bitmap as a full-bleed stage background and measure the
# cover crop: the element fills the viewport, and ``object-fit: cover`` scales
# the bitmap so the drawn box covers the element box in both axes (no
# letterboxing, no gap).
_COVER_CROP_JS = """() => {
  const img = document.querySelector("img");
  if (!img) return null;
  img.style.width = "100vw";
  img.style.height = "100vh";
  img.style.objectFit = "cover";
  img.style.display = "block";
  img.style.margin = "0";
  const rect = img.getBoundingClientRect();
  const scale = Math.max(
    rect.width / img.naturalWidth,
    rect.height / img.naturalHeight,
  );
  return {
    naturalWidth: img.naturalWidth,
    naturalHeight: img.naturalHeight,
    frame: {width: window.innerWidth, height: window.innerHeight},
    rect: {width: rect.width, height: rect.height, top: rect.top, left: rect.left},
    drawn: {width: img.naturalWidth * scale, height: img.naturalHeight * scale},
    objectFit: window.getComputedStyle(img).objectFit,
  };
}"""


class BundledSceneAssetsBrowserTest(ManagedServerTearDownMixin, BrowserAcceptanceTest):
    """Bundled scene static serving on a per-test isolated real server."""

    def setUp(self) -> None:
        runtime = create_runtime()
        # Shipped catalogs, pinned BEFORE the seed and server startup: this
        # journey proves the real built-in inventory, never the synthetic kit.
        runtime.env["ELOSERN_BROWSER_SYNTH_CATALOGS"] = "0"
        self.server = ManagedServer(runtime=runtime)
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    @classmethod
    def setUpClass(cls) -> None:
        # Each test boots its own isolated server; never the shared one.
        pass

    def _assert_pack_static_decode(self, assets) -> None:
        """Serve and decode one pack's committed illustrations for real.

        Shared by the per-pack journeys: one isolated real server, no operator
        artwork root, no generation service, and the browser's own decode at
        the desktop reference viewport under cover cropping.
        """
        self.assertNotIn(
            "ART_OFFICIAL_ROOT",
            self.server.runtime.env,
            "normal absence is the default root, never an environment override",
        )
        page = self.new_page(DEFAULT_VIEWPORT)
        requested: list[str] = []
        page.on("response", lambda response: requested.append(response.url))

        observed_sizes: list[str] = []
        for asset in assets:
            with self.subTest(asset=asset):
                served = f"{self.base_url}/static/{asset.removeprefix(STATIC_SOURCE_PREFIX)}"
                response = page.goto(served, wait_until="load")
                self.assertIsNotNone(
                    response, f"{asset}: the static asset request produced no response"
                )
                self.assertEqual(response.status, 200, f"{asset}: not served (status {response.status})")
                self.assertTrue(
                    response.url.startswith(f"{self.base_url}/static/"),
                    f"{asset}: served from {response.url!r}, not the project origin",
                )
                content_type = (response.headers or {}).get("content-type", "")
                self.assertTrue(
                    content_type.startswith("image/webp"),
                    f"{asset}: unexpected content type {content_type!r}",
                )

                self.assertTrue(
                    page.evaluate(_AWAIT_DECODE_JS),
                    f"{asset}: the browser could not decode the served image",
                )
                cover = page.evaluate(_COVER_CROP_JS)
                self.assertIsNotNone(cover, f"{asset}: the image document rendered no <img>")
                self.assertGreater(
                    cover["naturalWidth"], 0, f"{asset}: broken image (naturalWidth 0)"
                )
                self.assertGreater(
                    cover["naturalHeight"], 0, f"{asset}: broken image (naturalHeight 0)"
                )
                self.assertEqual(
                    cover["naturalWidth"] * 9,
                    cover["naturalHeight"] * 16,
                    f"{asset}: not a full-bleed 16:9 landscape",
                )
                self.assertEqual(cover["objectFit"], "cover")

                width, height = DEFAULT_VIEWPORT
                self.assertAlmostEqual(
                    cover["rect"]["width"], width, delta=1.0,
                    msg=f"{asset}: the cover element does not fill the viewport width",
                )
                self.assertAlmostEqual(
                    cover["rect"]["height"], height, delta=1.0,
                    msg=f"{asset}: the cover element does not fill the viewport height",
                )
                self.assertGreaterEqual(
                    cover["drawn"]["width"], cover["rect"]["width"] - 0.5,
                    f"{asset}: cover cropping leaves a horizontal gap",
                )
                self.assertGreaterEqual(
                    cover["drawn"]["height"], cover["rect"]["height"] - 0.5,
                    f"{asset}: cover cropping leaves a vertical gap",
                )

                declared = (response.headers or {}).get("content-length")
                if declared:
                    observed_sizes.append(declared)

        # Serving, not generation: no operator or generated media identity was
        # requested anywhere in this journey.
        offenders = [
            url
            for url in requested
            if "/art/" in url and "/static/art/scenes/" not in url
        ]
        self.assertEqual(offenders, [], "an operator/generated media identity was requested")
        if len(observed_sizes) == len(assets):
            self.assertEqual(
                len(set(observed_sizes)),
                len(assets),
                "the three scene URLs served identical byte counts, so one file "
                "is standing in for several keys",
            )

    @covers_requirement(
        "bundled-outdoor-scene-art::each-supported-pack-scene-has-its-own-finished-illustration",
        "bundled-outdoor-scene-art::scene-artwork-is-distributable-with-recorded-provenance",
    )
    def test_outdoor_pack_static_decode(self):
        """Every committed outdoor scene serves and decodes as its own image."""
        self._assert_pack_static_decode(OUTDOOR_SCENE_ASSETS)

    @covers_requirement(
        "bundled-interior-scene-art::each-supported-pack-scene-has-its-own-finished-illustration",
        "bundled-interior-scene-art::scene-artwork-is-distributable-with-recorded-provenance",
    )
    def test_interior_pack_static_decode(self):
        """Every committed interior scene serves and decodes as its own image."""
        self._assert_pack_static_decode(INTERIOR_SCENE_ASSETS)

    @covers_requirement(
        "bundled-sacred-scene-art::each-supported-pack-scene-has-its-own-finished-illustration",
        "bundled-sacred-scene-art::scene-artwork-is-distributable-with-recorded-provenance",
    )
    def test_sacred_pack_static_decode(self):
        """Every committed sacred scene serves and decodes as its own image."""
        self._assert_pack_static_decode(SACRED_SCENE_ASSETS)

    def test_terminal_pack_static_decode(self):
        """Every committed terminal scene serves and decodes as its own image."""
        self._assert_pack_static_decode(TERMINAL_SCENE_ASSETS)


if __name__ == "__main__":
    import unittest

    unittest.main()
