"""Browser journey for the gallery image contract (change
``unified-gallery-image-contract``).

One real committed gallery selection: the seed appends the character's exact
original card through the production writers, writes a real operator content
directory under the journey's own ``ART_OFFICIAL_ROOT`` before startup (so the
official rows come from the real catalog snapshot), and enqueues one real
pending request plus one real recorded failure on a monster subject.

The journey then intercepts *only* the selected original's own media URL after
the server resolved and serialized the committed v3 panel and answers it with
invalid bytes, and asserts the contract's boundary: the subject's silhouette
alpha mask replaces the broken figure, the reached failure keeps a persistent
keyboard-accessible marker, the card's identity/status/default and the job state
are unchanged, no substitute becomes the edited original, and the official row
is never used as the card's fallback.
"""

from __future__ import annotations

import re
import unittest
from urllib.parse import urlsplit

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    install_outbound_recorder,
    press_control,
    sent_action_count,
    store_state,
)
from .fixtures import create_runtime
from .harness import ManagedServer, ManagedServerTearDownMixin

# Interception is restricted to a character's own gallery media route, so only
# the selected original is answered with invalid bytes.
_ORIGINAL_MEDIA = re.compile(r"/art/gallery/character/\d+/[^/]+\.(png|webp|jpg|avif)$")

_GALLERY = '[data-testid="gallery-panel"]'
_DETAIL = '[data-testid="gallery-detail"]'
_MARKER = '[data-testid="artwork-failure"]'
_ALPHA = '[data-testid="artwork-alpha"]'
_FACE_BUTTON = f"{_DETAIL} button:has-text(\"臉部框選\")"


def _card(card_id: str) -> str:
    """The committed card button of one exact image id."""
    return f'{_GALLERY} [data-image-id="{card_id}"]'


def _figure(card_id: str) -> str:
    """The card's own figure element (the probe that carries the load signal)."""
    return f'{_card(card_id)} img'


def _alpha(card_id: str) -> str:
    """The card's own silhouette primitive."""
    return f'{_card(card_id)} {_ALPHA}'


class GalleryImageContractBrowserTest(ManagedServerTearDownMixin, BrowserAcceptanceTest):
    """Gallery preview journeys on a per-test isolated server."""

    def setUp(self) -> None:
        # Shipped catalogs and both family seed flags must be set BEFORE seed
        # and server startup; each journey boots its own isolated runtime. The
        # official root is this journey's own runtime child, written by the
        # seed before startup so the startup index admits it like a deployment.
        runtime = create_runtime()
        runtime.env["ELOSERN_BROWSER_SYNTH_CATALOGS"] = "0"
        runtime.env["ELOSERN_BROWSER_UNIFIED_IMAGES"] = "1"
        runtime.env["ELOSERN_BROWSER_GALLERY_ROWS"] = "1"
        runtime.env["ART_OFFICIAL_ROOT"] = str(runtime.root_dir / "official")
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
        """Answer every gallery original media request with invalid media.

        The interception happens after the server resolved and serialized the
        committed descriptor; the request itself succeeds on the wire, so the
        failure the browser observes is its own decode failure.
        """
        page.route(_ORIGINAL_MEDIA, self._serve_invalid_original)

    def _serve_invalid_original(self, route) -> None:
        self._media_requests.append(route.request.url)
        route.fulfill(status=200, content_type="image/png", body=b"not-an-image")

    def _open_gallery(self, page) -> None:
        press_control(page, '[data-testid="gallery-opener"]')
        page.wait_for_selector(_GALLERY, timeout=30000)

    def _cards(self, page) -> list[dict]:
        return store_state(page)["panels"]["gallery"]["cards"]

    @covers_requirement(
        "art-gallery-resolution::gallery-urls-are-built-only-from-validated-card-identities",
        "webclient-gallery-ui::the-gallery-surface-renders-only-committed-panel-facts",
        "webclient-gallery-ui::gallery-previews-retain-exact-image-identity-and-reached-failures",
    )
    def test_original_404_falls_back_with_local_failure(self) -> None:
        from web.browser_support.unified_image_transitions import (
            SEEDED_ORIGINAL_IMAGE_ID,
        )

        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._fail_original_media(page)
        self._open_gallery(page)

        # The committed selection is the seed's exact original card, and its
        # descriptor is the v3 canonical shape: one rank-10 runtime candidate
        # naming that exact image plus the subject's silhouette terminal.
        page.wait_for_selector(_card(SEEDED_ORIGINAL_IMAGE_ID), timeout=30000)
        committed = next(
            row for row in self._cards(page) if row["image_id"] == SEEDED_ORIGINAL_IMAGE_ID
        )
        self.assertEqual(committed["status"], "card")
        self.assertTrue(committed["is_default"])
        artwork = committed["artwork"]
        candidate = artwork["attempts"][0]["resource"]
        self.assertEqual(artwork["attempts"][0]["rank"], 10)
        self.assertEqual(candidate["origin"], "runtime")
        terminal = artwork["terminal"]["resource"]
        self.assertEqual(artwork["terminal"]["kind"], "alpha_mask")
        self.assertEqual(terminal["origin"], "silhouette")

        # The subject's silhouette replaced the broken figure, and it only
        # paints after that same mask resource itself reported a load.
        page.wait_for_selector(_alpha(SEEDED_ORIGINAL_IMAGE_ID), timeout=30000)
        figure = page.locator(_figure(SEEDED_ORIGINAL_IMAGE_ID)).first
        figure.wait_for(state="attached", timeout=30000)
        self.assertEqual(figure.get_attribute("src"), terminal["url"])
        self.assertNotEqual(figure.get_attribute("src"), candidate["url"])
        self.assertTrue(self._media_requests, "the original media URL was never requested")
        # Interception is counted by the canonical source resource's own path
        # (the browser reports the absolute request URL; the descriptor carries
        # the same-origin route).
        self.assertEqual(
            [urlsplit(url).path for url in self._media_requests], [candidate["url"]]
        )

        # The reached failure keeps a persistent, keyboard-accessible marker
        # with bounded text (never a raw URL, path or exception).
        marker = page.locator(_MARKER).first
        marker.wait_for(state="visible", timeout=30000)
        self.assertEqual(marker.get_attribute("role"), "status")
        self.assertIn("圖片載入失敗", marker.inner_text())
        self.assertNotIn(candidate["url"], marker.inner_text())

        # The exact requested card keeps its identity, status and default, and
        # the job/panel state is unchanged: nothing switched cards.
        after = next(
            row for row in self._cards(page) if row["image_id"] == SEEDED_ORIGINAL_IMAGE_ID
        )
        self.assertEqual(after, committed)
        self.assertEqual(page.locator(_card(SEEDED_ORIGINAL_IMAGE_ID)).count(), 1)
        self.assertEqual(
            store_state(page)["panels"]["gallery"]["filters"],
            {"all": 1, "defaults": 1, "bound": 0, "pending": 0, "failed": 0},
        )
        # The detail rail still presents that same exact image as the original.
        page.locator(_card(SEEDED_ORIGINAL_IMAGE_ID)).first.click()
        page.wait_for_selector(_FACE_BUTTON, timeout=30000)

        # No substitute becomes the edited original: the editor refuses to save
        # the broken exact original and nothing crosses the wire.
        page.locator(_FACE_BUTTON).first.click()
        modal = page.locator('[role="dialog"][aria-label="臉部框選"]')
        modal.wait_for(state="visible", timeout=30000)
        self.assertTrue(
            page.get_by_role("button", name="儲存框選").is_disabled(),
            "a broken exact original must never become saveable",
        )
        self.assertEqual(sent_action_count(page, "gallery.face_rect.update"), 0)
        self.assertEqual(sent_action_count(page, "gallery.default.set"), 0)
        self.assertEqual(sent_action_count(page, "gallery.card.delete"), 0)

    @covers_requirement(
        "webclient-gallery-panel::the-gallery-panel-is-an-exact-read-only-version-2-presentation-panel",
        "webclient-gallery-ui::official-entries-render-as-selectable-read-only-rows-with-personal-geometry-affordances",
    )
    def test_official_and_synthetic_rows_carry_their_own_truth(self) -> None:
        page = self.logged_in_page()
        self._open_gallery(page)
        panel = store_state(page)["panels"]["gallery"]
        # The seeded operator content directory is admitted by the real startup
        # snapshot, so the selected subject presents exactly one official row
        # whose descriptor names that exact catalog identity.
        official = panel["official_entries"]
        self.assertEqual(len(official), 1, official)
        row = official[0]
        self.assertEqual(set(row), {"identity", "artwork", "is_current", "is_catalog_default"})
        self.assertTrue(row["is_catalog_default"])
        candidate = row["artwork"]["attempts"][0]["resource"]
        self.assertEqual(candidate["resource_id"], row["identity"])
        self.assertEqual(candidate["origin"], "official")
        self.assertEqual(candidate["geometry"]["stage"], None)
        # The official row is committed presentation data, never a card.
        self.assertNotIn(row["identity"], [card["image_id"] for card in panel["cards"]])

        # The monster subject carries the seeded in-flight request and recorded
        # failure as truthful synthetic rows with no image at all. The subject
        # rail is the real selection route: clicking it dispatches the ordinary
        # `gallery.subject.select` action and the server re-publishes the panel.
        monster = next(
            subject for subject in panel["subjects"] if subject["kind"] == "portrait:monster"
        )
        page.get_by_role("button", name=monster["display_name"]).first.click()
        for _ in range(60):
            selected = store_state(page)["panels"]["gallery"]
            if selected["selected"] == monster["subject_key"] and selected["cards"]:
                break
            page.wait_for_timeout(500)
        rows = self._cards(page)
        self.assertTrue(rows, "the monster subject published no synthetic rows")
        statuses = {row["status"] for row in rows}
        self.assertIn("pending", statuses)
        self.assertIn("failed", statuses)
        for row in rows:
            if row["status"] == "card":
                continue
            self.assertEqual(row["artwork"]["attempts"], [])
            self.assertIsNone(row["artwork"]["terminal"])
            self.assertEqual(row["artwork"]["generation_state"], row["status"])
            self.assertFalse(row["is_default"])
            self.assertEqual(row["chips"], [])


if __name__ == "__main__":
    unittest.main()
