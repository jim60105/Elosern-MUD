"""Browser journey for the shared image loading core (change
``unified-image-loading-core``).

One real original card is seeded into the activated character's gallery and
served from the runtime art store. The journey then intercepts *only* that
card's media URL after the server resolved and serialized the committed gallery
panel, opens the real face-rectangle editor over it, and asserts the local
failure state: the broken original and its crop are removed, the keyboard /
assistive explanation persists, and no geometry write crosses the wire. It
finishes by driving the family's bounded test-only transition through the real
command line and asserting the exact repaired card identity becomes the
committed default — a real server writer, never a client-injected snapshot.
"""

from __future__ import annotations

import re
import unittest

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    install_outbound_recorder,
    open_command_line,
    press_control,
    sent_action_count,
    store_state,
    wait_for_store_state,
)
from .fixtures import create_runtime
from .harness import ManagedServer, ManagedServerTearDownMixin

# Interception is restricted to the seeded original's own gallery media URL.
_ORIGINAL_MEDIA = re.compile(r"/art/gallery/character/\d+/[^/]+\.(png|webp|jpg|avif)$")

_FACE_MODAL = '[role="dialog"][aria-label="臉部框選"]'
_FACE_ORIGINAL = f"{_FACE_MODAL} .gallery-face__original > img"
_FACE_CROP = f"{_FACE_MODAL} .gallery-face__preview img"
_FAILURE_MARKER = f'{_FACE_MODAL} [data-testid="artwork-failure"]'

_FACE_BUTTON = '[data-testid="gallery-detail"] button:has-text("臉部框選")'


class ImageLoadingCoreBrowserTest(ManagedServerTearDownMixin, BrowserAcceptanceTest):
    """Editor original-loading journeys on a per-test isolated server."""

    def setUp(self) -> None:
        # Shipped catalogs and the family's seed flag must be set BEFORE seed
        # and server startup; each journey boots its own isolated runtime.
        runtime = create_runtime()
        runtime.env["ELOSERN_BROWSER_SYNTH_CATALOGS"] = "0"
        runtime.env["ELOSERN_BROWSER_UNIFIED_IMAGES"] = "1"
        self.server = ManagedServer(runtime=runtime)
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        self._media_requests: list[str] = []
        super().setUp()

    @classmethod
    def setUpClass(cls) -> None:
        # Each test boots its own isolated server; never the shared one.
        pass

    def _fail_original_media(self, page) -> None:
        """Answer the seeded original's media request with invalid media.

        The interception happens after the server resolved and serialized the
        committed panel; the request itself succeeds on the wire, so the
        failure the editor observes is the browser's own decode failure.
        """
        page.route(_ORIGINAL_MEDIA, self._serve_invalid_original)

    def _serve_invalid_original(self, route) -> None:
        self._media_requests.append(route.request.url)
        route.fulfill(status=200, content_type="image/png", body=b"not-an-image")

    def _open_face_editor(self, page) -> None:
        press_control(page, '[data-testid="gallery-opener"]')
        page.wait_for_selector('[data-testid="gallery-panel"]', timeout=30000)
        page.wait_for_selector(_FACE_BUTTON, timeout=30000)
        page.locator(_FACE_BUTTON).first.click()
        page.wait_for_selector(_FACE_MODAL, timeout=30000)

    @covers_requirement(
        "image-attempt-lifecycle::unexpected-failures-remain-locally-accessible"
    )
    def test_original_failure_has_persistent_local_state(self) -> None:
        from web.browser_support.unified_image_transitions import (
            REPAIRED_ORIGINAL_IMAGE_ID,
            SEEDED_ORIGINAL_IMAGE_ID,
        )

        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._fail_original_media(page)
        self._open_face_editor(page)

        # The reached failure removed the broken original and its crop, and the
        # local explanation is available without hover or color-only meaning.
        marker = page.locator(_FAILURE_MARKER)
        marker.wait_for(state="visible", timeout=30000)
        self.assertEqual(page.locator(_FACE_ORIGINAL).count(), 0)
        self.assertEqual(page.locator(_FACE_CROP).count(), 0)
        self.assertIn("圖片載入失敗", marker.inner_text())
        self.assertEqual(marker.get_attribute("role"), "status")
        self.assertTrue(self._media_requests, "the original media URL was never requested")

        # Saving stays impossible and nothing crosses the wire.
        self.assertTrue(page.get_by_role("button", name="儲存框選").is_disabled())
        self.assertEqual(sent_action_count(page, "gallery.face_rect.update"), 0)

        # Real gallery recovery: the bounded test-only transition appends a
        # distinct original through the production writer and selects it.
        page.keyboard.press("Escape")
        page.wait_for_selector(_FACE_MODAL, state="detached", timeout=30000)
        page.wait_for_selector('[data-testid="gallery-panel"]', timeout=30000)
        open_command_line(page)
        page.keyboard.type("uieditor_transition repaired_original")
        page.keyboard.press("Enter")
        wait_for_store_state(
            page,
            lambda state: any(
                card.get("image_id") == REPAIRED_ORIGINAL_IMAGE_ID
                for card in ((state.get("panels") or {}).get("gallery") or {}).get("cards") or []
            ),
            timeout=30000,
        )
        cards = store_state(page)["panels"]["gallery"]["cards"]
        repaired = next(card for card in cards if card["image_id"] == REPAIRED_ORIGINAL_IMAGE_ID)
        self.assertTrue(repaired["is_default"], "the repaired original is not the committed default")
        self.assertNotEqual(REPAIRED_ORIGINAL_IMAGE_ID, SEEDED_ORIGINAL_IMAGE_ID)


if __name__ == "__main__":
    unittest.main()
