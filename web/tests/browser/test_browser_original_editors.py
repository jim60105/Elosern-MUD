"""Browser journey for the gallery original editors (change
``unified-gallery-original-editors``).

One real original card is seeded into the activated character's gallery and
served from the runtime art store. The journey drives both original editors —
the face-rectangle crop and the stage transform — through the real gallery and
official controls after the server resolved and serialized the committed panel,
and asserts the boundary the change owns:

* with no decoded exact original neither dialog can dispatch geometry, however
  the save is attempted (a broken original is removed, keeps a persistent local
  explanation, and the keyboard route writes nothing);
* a distinct repaired original appended through the production gallery writers
  decodes with its real dimensions and enables exactly one save;
* the fixed adult reference is intercepted on its own: it reports its own local
  failure and is removed from the preview while the healthy original stays the
  only save target and its identity is unchanged.
"""

from __future__ import annotations

import re
import time
import unittest

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    install_outbound_recorder,
    open_command_line,
    outbound_messages,
    sent_action_count,
    store_state,
    wait_for_store_state,
)
from .fixtures import create_runtime
from .harness import ManagedServer, ManagedServerTearDownMixin

# Interception is restricted to a character's own gallery media route, so only
# the selected exact original is answered with invalid bytes.
_ORIGINAL_MEDIA = re.compile(r"/art/gallery/character/\d+/[^/]+\.(png|webp|jpg|avif)$")
# The fixed adult-size ruler the stage editor always observes behind the figure.
_ADULT_REFERENCE_MEDIA = re.compile(r"/art/defaults/man\.webp$")

_GALLERY = '[data-testid="gallery-panel"]'
_DETAIL = '[data-testid="gallery-detail"]'
_FACE_BUTTON = f"{_DETAIL} button:has-text(\"臉部框選\")"
_STAGE_BUTTON = f"{_DETAIL} button:has-text(\"比例調整\")"
# Both dialogs are addressed by their own ARIA role plus their own surface
# class, so a selector never depends on the other dialog's markup.
_FACE_MODAL = '[role="dialog"][aria-label="臉部框選"]'
# The stage dialog carries `比例調整` as its accessible title and the stage
# surface's own class on a descendant, so it is addressed without borrowing the
# face dialog's markup.
_STAGE_MODAL = '[role="dialog"]:has(.stage-transform__body)'
_FACE_CLOSE = f'{_FACE_MODAL} button[aria-label="關閉臉部框選"]'
_STAGE_CLOSE = f'{_STAGE_MODAL} button[aria-label="關閉"]'
_FACE_ORIGINAL = f"{_FACE_MODAL} .gallery-face__original > img"
_FACE_CROP = f"{_FACE_MODAL} .gallery-face__preview img"
_FACE_MARKER = f'{_FACE_MODAL} [data-testid="artwork-failure"]'
# Each dialog's own primary save control: addressed by its surface class so a
# label that changes while a save is in flight cannot address the wrong button.
_FACE_SAVE = f"{_FACE_MODAL} footer .gallery-primary"
_STAGE_FIGURE = f"{_STAGE_MODAL} .stage-transform__figure"
_STAGE_ADULT = f"{_STAGE_MODAL} .stage-transform__adult"
_STAGE_SAVE = f"{_STAGE_MODAL} .stage-transform__footer .gallery-primary"
_STAGE_RULER_MARKER = (
    f'{_STAGE_MODAL} .stage-transform__ruler-status [data-testid="artwork-failure"]'
)


def _card(card_id: str) -> str:
    """The committed card button of one exact image id."""
    return f'{_GALLERY} [data-image-id="{card_id}"]'


def _wait_for_actions(page, action_id: str, count: int, timeout: int = 30000) -> None:
    """Wait (bounded) until ``count`` actions of one id crossed the wire."""
    deadline = time.monotonic() + timeout / 1000
    while time.monotonic() < deadline:
        if sent_action_count(page, action_id) >= count:
            return
        page.wait_for_timeout(100)
    raise AssertionError(
        f"{action_id} did not reach {count} sent actions "
        f"(got {sent_action_count(page, action_id)})"
    )


def _wait_enabled(locator, timeout: int = 30000) -> None:
    """Wait (bounded) until one control is enabled, i.e. its gate opened."""
    deadline = time.monotonic() + timeout / 1000
    while time.monotonic() < deadline:
        if not locator.is_disabled():
            return
        locator.page.wait_for_timeout(100)
    raise AssertionError(f"{locator} never became enabled")


def _action_envelopes(page, action_id: str) -> list[dict]:
    """The recorded ``ui_action`` envelopes of one action id (the outbound boundary)."""
    return [
        args[0]
        for cmdname, args, _kwargs in outbound_messages(page)
        if cmdname == "ui_action" and args and args[0].get("action_id") == action_id
    ]


def _action_payloads(page, action_id: str) -> list[dict]:
    """The recorded ``ui_action`` payloads of one action id, in order."""
    return [envelope.get("payload") for envelope in _action_envelopes(page, action_id)]


def _seeded_original_image_id() -> str:
    """The seeded exact original's id (imported lazily: the helper needs settings)."""
    from web.browser_support.unified_image_transitions import SEEDED_ORIGINAL_IMAGE_ID

    return SEEDED_ORIGINAL_IMAGE_ID


class OriginalEditorsBrowserTest(ManagedServerTearDownMixin, BrowserAcceptanceTest):
    """Original-editor eligibility journeys on a per-test isolated server."""

    def setUp(self) -> None:
        # Shipped catalogs and the family's seed flag must be set BEFORE seed
        # and server startup; each journey boots its own isolated runtime. The
        # official root stays the runtime's own uncreated child (normal
        # absence), so the committed rows come from the bundled inventory.
        runtime = create_runtime()
        runtime.env["ELOSERN_BROWSER_SYNTH_CATALOGS"] = "0"
        runtime.env["ELOSERN_BROWSER_UNIFIED_IMAGES"] = "1"
        self.server = ManagedServer(runtime=runtime)
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        self._original_requests: list[str] = []
        self._ruler_requests: list[str] = []
        super().setUp()

    @classmethod
    def setUpClass(cls) -> None:
        # Each test boots its own isolated server; never the shared one.
        pass

    def _fail_original_media(self, page) -> None:
        """Answer the seeded original's own media request with invalid media.

        The interception happens after the server resolved and serialized the
        committed descriptor; the request itself succeeds on the wire, so the
        failure each editor observes is its own decode failure. Every other
        gallery original (a repaired replacement, for instance) is served for
        real, so one journey can observe a failure and then observe recovery.
        """
        page.route(_ORIGINAL_MEDIA, self._serve_original)

    def _serve_original(self, route) -> None:
        self._original_requests.append(route.request.url)
        if _seeded_original_image_id() in route.request.url:
            route.fulfill(status=200, content_type="image/png", body=b"not-an-image")
        else:
            route.continue_()

    def _fail_adult_reference(self, page) -> None:
        """Answer the fixed adult reference's own request with invalid media."""
        page.route(_ADULT_REFERENCE_MEDIA, self._serve_invalid_ruler)

    def _serve_invalid_ruler(self, route) -> None:
        self._ruler_requests.append(route.request.url)
        route.fulfill(status=200, content_type="image/webp", body=b"not-an-image")

    def _open_gallery(self, page) -> None:
        from .browser_helpers import press_control

        press_control(page, '[data-testid="gallery-opener"]')
        page.wait_for_selector(_GALLERY, timeout=30000)

    def _cards(self, page) -> list[dict]:
        return store_state(page)["panels"]["gallery"]["cards"]

    def _open_card_editor(self, page, card_id: str, button: str, modal: str) -> None:
        """Select one committed card and open its own editor dialog.

        The card grid and the detail rail are the real selection/editing
        controls; the dialog is only opened through them.
        """
        page.locator(_card(card_id)).first.click()
        page.wait_for_selector(button, timeout=30000)
        page.locator(button).first.click()
        page.wait_for_selector(modal, timeout=30000)

    @covers_requirement(
        "image-attempt-lifecycle::unexpected-failures-remain-locally-accessible",
        "webclient-gallery-ui::the-face-rect-modal-stores-geometry-over-the-original-image",
        "webclient-gallery-ui::stage-saves-reuse-correlated-lifecycle-and-accessible-gallery-chrome",
    )
    @covers_requirement(
        "original-image-edit-eligibility::only-decoded-original-dimensions-enable-saving",
        "original-image-edit-eligibility::editing-failures-have-distinct-visible-states",
    )
    def test_failed_original_never_saves(self) -> None:
        from web.browser_support.unified_image_transitions import (
            SEEDED_ORIGINAL_IMAGE_ID,
        )

        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._fail_original_media(page)
        self._open_gallery(page)

        # The committed selection is the seed's exact original card: one rank-10
        # runtime candidate naming that exact image.
        page.wait_for_selector(_card(SEEDED_ORIGINAL_IMAGE_ID), timeout=30000)
        committed = next(
            row for row in self._cards(page) if row["image_id"] == SEEDED_ORIGINAL_IMAGE_ID
        )
        self.assertEqual(committed["status"], "card")
        candidate = committed["artwork"]["attempts"][0]["resource"]
        self.assertEqual(committed["artwork"]["attempts"][0]["rank"], 10)
        self.assertEqual(candidate["origin"], "runtime")

        # --- The face-rectangle crop dialog cannot save the broken original.
        self._open_card_editor(page, SEEDED_ORIGINAL_IMAGE_ID, _FACE_BUTTON, _FACE_MODAL)
        marker = page.locator(_FACE_MARKER)
        marker.wait_for(state="visible", timeout=30000)
        self.assertEqual(marker.get_attribute("role"), "status")
        self.assertIn("圖片載入失敗", marker.inner_text())
        self.assertNotIn(candidate["url"], marker.inner_text())
        # The broken original and its crop preview are both gone.
        self.assertEqual(page.locator(_FACE_ORIGINAL).count(), 0)
        self.assertEqual(page.locator(_FACE_CROP).count(), 0)
        self.assertTrue(self._original_requests, "the original media URL was never requested")

        # The disabled control is not what makes it safe: a forced activation of
        # the editor's own save handler still refuses, so no geometry write can
        # leave a dialog whose original never decoded (a disabled control is also
        # unreachable from the keyboard path).
        save = page.locator(_FACE_SAVE)
        self.assertTrue(save.is_disabled())
        save.dispatch_event("click")
        self.assertEqual(sent_action_count(page, "gallery.face_rect.update"), 0)
        # Close through the dialog's own control: the shared gallery overlay is
        # never reached by an unowned Escape.
        page.locator(_FACE_CLOSE).click()
        page.wait_for_selector(_FACE_MODAL, state="detached", timeout=30000)

        # --- The stage dialog cannot save it either, and keeps only the ruler.
        self._open_card_editor(page, SEEDED_ORIGINAL_IMAGE_ID, _STAGE_BUTTON, _STAGE_MODAL)
        # The failure settles asynchronously: the broken figure is removed first.
        page.wait_for_selector(_STAGE_FIGURE, state="detached", timeout=30000)
        self.assertEqual(page.locator(_STAGE_ADULT).count(), 1)
        stage_save = page.locator(_STAGE_SAVE)
        self.assertTrue(stage_save.is_disabled())
        stage_save.dispatch_event("click")
        self.assertEqual(sent_action_count(page, "gallery.stage.update"), 0)

        # The edited card kept its exact identity and status, and the job state
        # never moved: nothing switched cards and no substitute became the
        # edited original.
        after = next(
            row for row in self._cards(page) if row["image_id"] == SEEDED_ORIGINAL_IMAGE_ID
        )
        self.assertEqual(after, committed)

    @covers_requirement(
        "webclient-gallery-ui::the-face-rect-modal-stores-geometry-over-the-original-image",
        "webclient-gallery-ui::stage-saves-reuse-correlated-lifecycle-and-accessible-gallery-chrome",
    )
    @covers_requirement(
        "original-image-edit-eligibility::only-decoded-original-dimensions-enable-saving",
        "original-image-edit-eligibility::editing-failures-have-distinct-visible-states",
    )
    def test_new_original_recovers_and_ruler_failure_is_local(self) -> None:
        from web.browser_support.unified_image_transitions import (
            ORIGINAL_IMAGE_SIZE,
            REPAIRED_ORIGINAL_IMAGE_ID,
            SEEDED_ORIGINAL_IMAGE_ID,
        )

        page = self.logged_in_page()
        install_outbound_recorder(page)
        # Only the SEEDED original's media is broken; the repaired replacement
        # this journey publishes afterwards is served for real.
        self._fail_original_media(page)
        self._fail_adult_reference(page)
        self._open_gallery(page)
        page.wait_for_selector(_card(SEEDED_ORIGINAL_IMAGE_ID), timeout=30000)
        subject_key = store_state(page)["panels"]["gallery"]["selected"]

        # This session observes the failure first, in both original editors.
        self._open_card_editor(page, SEEDED_ORIGINAL_IMAGE_ID, _FACE_BUTTON, _FACE_MODAL)
        page.locator(_FACE_MARKER).wait_for(state="visible", timeout=30000)
        self.assertTrue(page.locator(_FACE_SAVE).is_disabled())
        page.locator(_FACE_CLOSE).click()
        page.wait_for_selector(_FACE_MODAL, state="detached", timeout=30000)
        self._open_card_editor(page, SEEDED_ORIGINAL_IMAGE_ID, _STAGE_BUTTON, _STAGE_MODAL)
        # The failure settles asynchronously: wait for the broken figure to be
        # removed before asserting the editor's own gate.
        page.wait_for_selector(_STAGE_FIGURE, state="detached", timeout=30000)
        self.assertTrue(page.locator(_STAGE_SAVE).is_disabled())
        page.locator(_STAGE_CLOSE).click()
        page.wait_for_selector(_STAGE_MODAL, state="detached", timeout=30000)
        self.assertEqual(sent_action_count(page, "gallery.face_rect.update"), 0)
        self.assertEqual(sent_action_count(page, "gallery.stage.update"), 0)

        # Real gallery recovery: the bounded test-only transition appends a
        # distinct original through the production writer and selects it, so a
        # new exact original — never a client-injected snapshot — is committed.
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
        repaired = next(
            row for row in self._cards(page) if row["image_id"] == REPAIRED_ORIGINAL_IMAGE_ID
        )
        self.assertTrue(repaired["is_default"], "the repaired original is not the committed default")
        repaired_candidate = repaired["artwork"]["attempts"][0]["resource"]
        self.assertEqual(repaired_candidate["geometry"]["image_size"], ORIGINAL_IMAGE_SIZE)
        self.assertNotEqual(REPAIRED_ORIGINAL_IMAGE_ID, SEEDED_ORIGINAL_IMAGE_ID)

        # The repaired original's own decode, observed by the browser, is what
        # re-enables the save.
        self._open_card_editor(page, REPAIRED_ORIGINAL_IMAGE_ID, _FACE_BUTTON, _FACE_MODAL)
        save = page.locator(_FACE_SAVE)
        _wait_enabled(save)
        self.assertEqual(
            page.locator(_FACE_ORIGINAL).evaluate("el => [el.naturalWidth, el.naturalHeight]"),
            [ORIGINAL_IMAGE_SIZE["width"], ORIGINAL_IMAGE_SIZE["height"]],
        )
        # A real numeric edit is what dispatches, and its payload names the exact
        # edited card and the squared geometry the browser measured.
        page.get_by_role("spinbutton", name="寬度").fill("0.3")
        save.click()
        _wait_for_actions(page, "gallery.face_rect.update", 1)
        # The dialog closes only on its own successful result and the committed
        # presentation revision that carries it, and exactly one save left it.
        page.wait_for_selector(_FACE_MODAL, state="detached", timeout=30000)
        face_saves = _action_payloads(page, "gallery.face_rect.update")
        self.assertEqual(len(face_saves), 1, face_saves)
        # Only the edited component crosses the wire for the exact edited card.
        self.assertEqual(set(face_saves[0]), {"subject_key", "image_id", "face_rect"})
        self.assertEqual(face_saves[0]["subject_key"], subject_key)
        self.assertEqual(face_saves[0]["image_id"], REPAIRED_ORIGINAL_IMAGE_ID)
        self.assertEqual(set(face_saves[0]["face_rect"]), {"x", "y", "w", "h"})
        self.assertAlmostEqual(face_saves[0]["face_rect"]["w"], 0.3, places=3)
        self.assertAlmostEqual(face_saves[0]["face_rect"]["h"], 0.3, places=3)

        # --- The ruler's own failure: its own indication, never the original's.
        self._open_card_editor(page, REPAIRED_ORIGINAL_IMAGE_ID, _STAGE_BUTTON, _STAGE_MODAL)
        ruler_marker = page.locator(_STAGE_RULER_MARKER)
        ruler_marker.wait_for(state="visible", timeout=30000)
        self.assertEqual(ruler_marker.get_attribute("role"), "status")
        self.assertIn("圖片載入失敗", ruler_marker.inner_text())
        self.assertTrue(self._ruler_requests, "the adult reference was never requested")
        # Only once the ruler's own failure has settled is its fill gone.
        self.assertEqual(page.locator(_STAGE_ADULT).count(), 0)

        # The healthy original is still the one save target, and it dispatches
        # exactly once even though the ruler is broken.
        stage_save = page.locator(_STAGE_SAVE)
        _wait_enabled(stage_save)
        self.assertEqual(page.locator(_STAGE_FIGURE).count(), 1)
        page.locator(f'{_STAGE_MODAL} input[type="range"]').first.fill("0.6")
        stage_save.click()
        _wait_for_actions(page, "gallery.stage.update", 1)
        page.wait_for_selector(_STAGE_MODAL, state="detached", timeout=30000)
        self.assertEqual(
            _action_payloads(page, "gallery.stage.update"),
            [{
                "subject_key": subject_key,
                "image_id": REPAIRED_ORIGINAL_IMAGE_ID,
                "stage": {"scale": 0.6, "x": 0, "y": 0},
            }],
        )

        # The ruler's failure changed nothing about the edited original: the
        # same exact card is still committed, with the same exact resource.
        after = next(
            row for row in self._cards(page) if row["image_id"] == REPAIRED_ORIGINAL_IMAGE_ID
        )
        self.assertEqual(after["image_id"], REPAIRED_ORIGINAL_IMAGE_ID)
        self.assertEqual(after["status"], "card")
        self.assertTrue(after["is_default"])
        self.assertEqual(
            after["artwork"]["attempts"][0]["resource"]["resource_id"],
            repaired_candidate["resource_id"],
        )


if __name__ == "__main__":
    unittest.main()
