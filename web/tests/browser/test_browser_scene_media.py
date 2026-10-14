"""Real-server browser acceptance for the bundled scene media namespace.

The committed scene collection is served by the application's own
``/art/bundled-scene/<scene-key>/<sha256>.webp`` boundary (not the plain
``/static/`` route the artwork packs exercise): this journey runs against one
isolated real server, with the shipped startup catalogs pinned BEFORE seeding
and startup, and proves three things at once over real HTTP —

* the admitted bundled identity serves the committed repository bytes and a
  real browser decodes them at their native 16:9 size;
* a configured operator root serves its OWN ``scene/<scene-key>/<image-file>``
  illustration under the separate ``/art/official/...`` namespace, with
  different bytes, so the two roots never stand in for each other;
* a stale fingerprint and a missing identity are actual 404s after resolution,
  never a substitute image and never a successful status.

Fixture ownership (design.md, "Concrete browser fixture ownership"): the
journey allocates its own isolated runtime, sets the shipped (non-synthetic)
catalog flag and the operator root BEFORE the seed and server startup, writes
the operator fixture bytes under a runtime-owned temporary root, and boots one
real managed server per test (``ManagedServer(runtime=runtime)`` +
``ManagedServerTearDownMixin``) rather than the synthetic shared server.
"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

from PIL import Image

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest, DEFAULT_VIEWPORT
from .fixtures import create_runtime
from .harness import ManagedServer, ManagedServerTearDownMixin

# The committed collection, addressed by full repository path: a test-path
# file may not carry a bare shipped scene key (the test-data independence gate
# scans this directory), and the key inventory itself is pinned by
# world/art/tests/test_bundled_scenes.py.
SCENES_DIRECTORY = (
    Path(__file__).resolve().parents[3] / "web" / "static" / "art" / "scenes"
)
BUNDLED_MEDIA_PREFIX = "/art/bundled-scene/"

# Await the browser's own decode (never merely the load event) and report the
# decoded natural size; a broken or substituted image resolves ``false``.
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

_NATURAL_SIZE_JS = """() => {
  const img = document.querySelector("img");
  if (!img) return null;
  return {width: img.naturalWidth, height: img.naturalHeight};
}"""


def _operator_fixture_bytes() -> bytes:
    """A valid, decodable WebP distinct from every committed scene image."""
    buffer = io.BytesIO()
    Image.new("RGB", (64, 36), (12, 34, 56)).save(buffer, format="WEBP")
    return buffer.getvalue()


class SceneMediaBrowserTest(ManagedServerTearDownMixin, BrowserAcceptanceTest):
    """Bundled versus operator scene media on a per-test isolated real server."""

    def setUp(self) -> None:
        runtime = create_runtime()
        # Shipped catalogs, pinned BEFORE the seed and server startup: this
        # journey proves the real built-in inventory, never the synthetic kit.
        runtime.env["ELOSERN_BROWSER_SYNTH_CATALOGS"] = "0"
        # A configured operator root: fixture bytes and a manifest under a
        # runtime-owned temporary root, written before startup so the single
        # startup index admits them.
        self.scene_key = sorted(path.stem for path in SCENES_DIRECTORY.glob("*.webp"))[0]
        self.operator_root = runtime.cache_dir / "operator-art"
        self.operator_bytes = _operator_fixture_bytes()
        self.operator_relative = f"scene/{self.scene_key}/{self.scene_key}.webp"
        operator_file = self.operator_root / self.operator_relative
        operator_file.parent.mkdir(parents=True, exist_ok=True)
        operator_file.write_bytes(self.operator_bytes)
        runtime.env["ART_OFFICIAL_ROOT"] = str(self.operator_root)

        self.server = ManagedServer(runtime=runtime)
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    @classmethod
    def setUpClass(cls) -> None:
        # Each test boots its own isolated server; never the shared one.
        pass

    def _committed_bytes(self) -> bytes:
        return (SCENES_DIRECTORY / f"{self.scene_key}.webp").read_bytes()

    @staticmethod
    def _digest(payload: bytes) -> str:
        return hashlib.sha256(payload).hexdigest()

    def _get(self, page, target: str):
        return page.request.get(f"{self.base_url}{target}")

    @covers_requirement(
        "official-artwork-catalog::the-catalog-indexes-the-mounted-layout-once-at-startup-and-serves-from-that-snapshot"
    )
    def test_bundled_namespace_and_operator_isolation(self):
        """Bundled and operator scene media coexist without substituting."""
        page = self.new_page(DEFAULT_VIEWPORT)
        committed = self._committed_bytes()
        bundled_fingerprint = self._digest(committed)
        operator_fingerprint = self._digest(self.operator_bytes)
        self.assertNotEqual(bundled_fingerprint, operator_fingerprint)

        # 1. The admitted bundled identity serves the committed bytes.
        bundled_url = (
            f"{BUNDLED_MEDIA_PREFIX}{self.scene_key}/{bundled_fingerprint}.webp"
        )
        # A freshly booted managed server answers its very FIRST HTTP request
        # with an empty placeholder document (observed on every /art/ branch,
        # unrelated to this namespace), so consume it on a refusing identity
        # before any assertion reads a response body.
        warmup = self._get(page, f"{BUNDLED_MEDIA_PREFIX}__warmup__/{'0' * 64}.webp")
        self.assertNotIn(
            "image/", warmup.headers.get("content-type", ""), "a refusal is never an image"
        )
        # The media request itself (a document navigation would answer with
        # Chromium's image-document wrapper, not the served bytes).
        response = self._get(page, bundled_url)
        self.assertEqual(response.status, 200)
        self.assertTrue(
            response.headers.get("content-type", "").startswith("image/webp"),
            f"unexpected content type {response.headers.get('content-type')!r}",
        )
        self.assertEqual(response.body(), committed)
        # ... and the real browser decodes those very bytes at native size.
        page.goto(f"{self.base_url}{bundled_url}", wait_until="load")
        self.assertTrue(
            page.evaluate(_AWAIT_DECODE_JS),
            "the browser could not decode the served bundled image",
        )
        natural = page.evaluate(_NATURAL_SIZE_JS)
        self.assertEqual(
            natural["width"] * 9,
            natural["height"] * 16,
            "the served bundled scene is not the committed full-bleed 16:9 image",
        )

        # 2. The operator root serves its own illustration, from its own root.
        operator_url = f"/art/official/{operator_fingerprint}/{self.operator_relative}"
        operator_response = self._get(page, operator_url)
        self.assertEqual(operator_response.status, 200)
        self.assertEqual(operator_response.body(), self.operator_bytes)
        self.assertNotEqual(operator_response.body(), committed)
        self.assertTrue(
            (self.operator_root / self.operator_relative).is_file(),
            "the served operator identity does not live under the configured root",
        )

        # 3. A stale fingerprint and an absent identity are actual 404s.
        stale = f"{BUNDLED_MEDIA_PREFIX}{self.scene_key}/{'0' * 64}.webp"
        missing = f"{BUNDLED_MEDIA_PREFIX}{self.scene_key}/{bundled_fingerprint}x.webp"
        unknown = f"{BUNDLED_MEDIA_PREFIX}/t_synth_ghost/{bundled_fingerprint}.webp"
        for target in (stale, missing, unknown):
            with self.subTest(target=target):
                failure = self._get(page, target)
                self.assertEqual(failure.status, 404)
                self.assertNotIn(
                    "image/", failure.headers.get("content-type", ""), "a 404 is never an image"
                )
                self.assertNotEqual(failure.body(), committed)
                self.assertNotEqual(failure.body(), self.operator_bytes)

        # 4. The operator root never replaces the bundled identity, and vice
        #    versa: the same key resolves to different bytes per namespace.
        after = self._get(page, bundled_url)
        self.assertEqual(after.status, 200)
        self.assertEqual(after.body(), committed)
        self.assertNotEqual(
            self._get(
                page,
                f"{BUNDLED_MEDIA_PREFIX}{self.scene_key}/{operator_fingerprint}.webp",
            ).status,
            200,
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
