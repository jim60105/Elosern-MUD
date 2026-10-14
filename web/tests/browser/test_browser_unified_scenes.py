"""Unified scene rendering browser acceptance (change ``unified-scene-rendering``).

Two real journeys on per-test isolated servers with the shipped catalogs (the
seed fixture's authored room metadata, its operator content directories and its
generated scene record are all admitted by the running server, never by the
client):

* the room-aware source chain, same-place mode changes, same-scene
  regeneration retention, a real binding removal, a real move and the shared
  full view;
* browser-side failures injected AFTER the server resolved and serialized the
  committed descriptor: a delayed preferred source with a latent provisional
  failure, the preferred source winning without an unrelated fault, the reached
  lower fault persisting once its position arrives (with no duplicate request
  for the reused provisional resource) and the exhausted chain degrading
  without a broken image.

Every backend state change goes through the family's bounded test-only
transition command (``world.art.queue`` writers and the map-owned room
attributes) followed by the normal presentation refresh; no journey ever
mutates the browser store to claim a server fact.
"""

from __future__ import annotations

import time

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import open_command_line, store_state, wait_for_store_state
from .fixtures import create_runtime
from .harness import ManagedServer, ManagedServerTearDownMixin

# The room-aware chain's positions, as the descriptor's own source ids state
# them. A journey asserts WHICH position is presented, never a guessed URL.
ROOM_SOURCE = "scene.room:"
GENERATED_SOURCE = "scene.generated:"

IMAGE = '[data-testid="scene-backdrop-image"]'
PLACEHOLDER = '[data-testid="scene-backdrop-placeholder"]'
PLACEHOLDER_LABEL = '[data-testid="scene-backdrop-placeholder-label"]'
FAILURE = '[data-testid="scene-backdrop-failure"]'
GENERATING = '[data-testid="scene-backdrop-generating"]'
CONTROL = '[data-testid="scene-backdrop-control"]'
FULLVIEW = '[data-testid="scene-backdrop-fullview"]'


class UnifiedScenesBrowserTest(ManagedServerTearDownMixin, BrowserAcceptanceTest):
    """Scene rendering journeys on a per-test isolated server."""

    def setUp(self) -> None:
        # Shipped catalogs, the scene seed flag and the fixture's operator
        # content are all set BEFORE seed and server startup.
        runtime = create_runtime()
        runtime.env["ELOSERN_BROWSER_SYNTH_CATALOGS"] = "0"
        runtime.env["ELOSERN_BROWSER_UNIFIED_SCENES"] = "1"
        runtime.env["ELOSERN_BROWSER_ART"] = "done"
        self.server = ManagedServer(runtime=runtime)
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        self.requests: list[str] = []
        super().setUp()

    @classmethod
    def setUpClass(cls) -> None:
        # Each test boots its own isolated server; never the shared one.
        pass

    # --- helpers ---------------------------------------------------------

    def _art(self, page) -> dict:
        return store_state(page)["panels"]["art"]["scene"]["artwork"]

    def _displayed(self, page) -> str | None:
        image = page.locator(IMAGE)
        if not image.count():
            return None
        return image.first.get_attribute("src")

    def _wait_displayed(self, page, timeout: int = 30000) -> str:
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            url = self._displayed(page)
            if url:
                return url
            page.wait_for_timeout(200)
        raise AssertionError("no scene image was ever presented")

    def _wait_source(self, page, source_prefix: str, timeout: int = 30000) -> str:
        """Wait until the presented resource belongs to one chain position."""
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            artwork = self._art(page)
            attempts = [entry for entry in artwork["attempts"] if entry["type"] == "image"]
            displayed = self._displayed(page)
            for entry in attempts:
                if (
                    entry["source_id"].startswith(source_prefix)
                    and entry["resource"]["url"] == displayed
                ):
                    return entry["resource"]["url"]
            page.wait_for_timeout(200)
        raise AssertionError(f"the {source_prefix} position was never presented")

    def _transition(self, page, name: str) -> None:
        open_command_line(page)
        page.keyboard.type(f"uieditor_transition {name}")
        page.keyboard.press("Enter")
        page.wait_for_timeout(400)

    def _wait_mode(self, page, mode: str, timeout: int = 30000) -> None:
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            if store_state(page)["mode"] == mode:
                return
            page.wait_for_timeout(250)
        raise AssertionError(f"mode {mode!r} never committed")

    def _engage(self, page) -> None:
        # The seeded art room's OWN living monster, addressed by the fixture's
        # own key, so the engagement is a real server transition.
        from web.browser_support.browser_fixtures_data import art_room_monster_key

        target = art_room_monster_key()
        page.evaluate("([t]) => Evennia.msg('text', [`engage ${t}`], {})", [target])
        self._wait_mode(page, "combat")


    # --- journeys --------------------------------------------------------

    @covers_requirement(
        "webclient-contextual-hud::the-scene-backdrop-renders-the-art-payload-truthfully-behind-the-stage"
    )
    def test_room_precedence_retention_movement_and_fullview(self) -> None:
        page = self.logged_in_page()
        page.on("request", lambda request: self.requests.append(request.url))

        # (1) The authored per-room override is the first chain position and it
        # wins: the presented resource IS that admitted operator image.
        room_url = self._wait_source(page, ROOM_SOURCE)
        artwork = self._art(page)
        room_entries = [
            entry
            for entry in artwork["attempts"]
            if entry["source_id"].startswith(ROOM_SOURCE)
        ]
        self.assertEqual(room_entries[0]["rank"], 10)
        self.assertEqual(room_entries[0]["resource"]["origin"], "official")
        label = store_state(page)["panels"]["art"]["scene"]["label"]
        self.assertTrue(page.locator('[data-testid="scene-backdrop-label"]').inner_text().strip())

        # (2) A same-place mode change never changes the artwork: the real
        # engagement into combat (through the ordinary text transport) commits
        # mode `combat` while the committed descriptor — and therefore the
        # presented bitmap — stays exactly what it was.
        self._engage(page)
        self.assertEqual(self._displayed(page), room_url)
        self.assertEqual(store_state(page)["panels"]["art"]["scene"]["label"], label)
        self.assertEqual(self._art(page)["revision"], artwork["revision"])

        # (3) A real binding removal drops the override; the chain continues to
        # the scene's own generated artwork.
        self._transition(page, "remove_room_binding")
        generated_url = self._wait_source(page, GENERATED_SOURCE)
        self.assertNotEqual(generated_url, room_url)

        # (4) A same-scene regeneration retains the good generated image: the
        # descriptor commits with no generated candidate (pending) while the
        # browser keeps the pixels it is authorized to hold, with the factual
        # progress notice and no error.
        self._transition(page, "pending_scene")
        wait_for_store_state(
            page,
            lambda state: (
                state["panels"]["art"]["scene"]["artwork"]["generation_state"] == "pending"
            ),
            timeout=30000,
        )
        page.wait_for_timeout(600)
        self.assertEqual(self._displayed(page), generated_url)
        self.assertTrue(page.locator(GENERATING).count(), "the progress notice is missing")
        self.assertEqual(page.locator(FAILURE).count(), 0)
        self.assertEqual(page.locator(PLACEHOLDER).count(), 0)

        # (5) A failed regeneration stays visible beside the healthy bundled
        # fallback: the retained image remains and the reached failure is
        # locally indicated.
        self._transition(page, "failed_scene")
        wait_for_store_state(
            page,
            lambda state: (
                state["panels"]["art"]["scene"]["artwork"]["generation_state"] == "failed"
            ),
            timeout=30000,
        )
        page.wait_for_selector(FAILURE, timeout=30000)
        self.assertEqual(self._displayed(page), generated_url)
        self.assertEqual(page.locator(PLACEHOLDER).count(), 0)

        # (6) A move to a different logical place discards the previous place's
        # pixels at the commit and shows only the new place's own background.
        self._transition(page, "move_scene")
        wait_for_store_state(
            page,
            lambda state: (
                state["panels"]["art"]["scene"]["artwork"]["subject_id"] != artwork["subject_id"]
            ),
            timeout=30000,
        )
        page.wait_for_timeout(600)
        moved = self._art(page)
        self.assertNotEqual(moved["subject_id"], artwork["subject_id"])
        displayed = self._displayed(page)
        if displayed is not None:
            admitted = {
                entry["resource"]["url"]
                for entry in moved["attempts"]
                if entry["type"] == "image"
            }
            self.assertIn(
                displayed,
                admitted,
                "the previous place's image survived the move",
            )
            self.assertNotEqual(displayed, generated_url)

        # (7) The full view shares the same displayed resource and failure
        # state, and it closes back to the opener.
        displayed = self._wait_displayed(page)
        page.locator(CONTROL).click()
        page.wait_for_selector(FULLVIEW, timeout=15000)
        fullview_image = page.locator('[data-testid="scene-backdrop-fullview-image"]')
        self.assertEqual(fullview_image.get_attribute("src"), displayed)
        page.keyboard.press("Escape")
        page.wait_for_selector(FULLVIEW, state="detached", timeout=15000)

    @covers_requirement(
        "webclient-contextual-hud::the-scene-backdrop-renders-the-art-payload-truthfully-behind-the-stage"
    )
    def test_provisional_and_terminal_failures_are_reached_once(self) -> None:
        page = self.logged_in_page()
        page.on("request", lambda request: self.requests.append(request.url))

        # The committed descriptor is resolved by the server first; only then
        # does the journey intercept the media it names. The preferred room
        # override is DELAYED, and the scene's own required bundled
        # illustration — the provisional background — fails.
        artwork = self._art(page)
        bundled = next(
            entry["resource"]["url"]
            for entry in artwork["attempts"]
            if entry["source_id"].startswith("scene.bundled:")
        )
        generated = next(
            entry["resource"]["url"]
            for entry in artwork["attempts"]
            if entry["source_id"].startswith(GENERATED_SOURCE)
        )
        room = next(
            entry["resource"]["url"]
            for entry in artwork["attempts"]
            if entry["source_id"].startswith(ROOM_SOURCE)
        )
        released: list[bool] = []

        def serve_bundled(route):
            route.fulfill(status=404, content_type="text/plain", body=b"missing")

        def serve_room(route):
            # Hold the preferred source until the journey releases it, so the
            # provisional failure is observed while it is still in flight.
            deadline = time.monotonic() + 10
            while not released and time.monotonic() < deadline:
                time.sleep(0.05)
            route.continue_()

        page.route(bundled, serve_bundled)
        page.route(room, serve_room)

        # (1) The provisional failure is LATENT: no error is claimed while the
        # preferred source is still loading, and the stage is simply resolving.
        page.wait_for_timeout(1500)
        self.assertEqual(page.locator(FAILURE).count(), 0)
        self.assertEqual(page.locator(PLACEHOLDER).count(), 0)

        # (2) The preferred room source wins without an unrelated provisional
        # fault: releasing it presents the room image and claims no failure.
        released.append(True)
        self._wait_source(page, ROOM_SOURCE, timeout=30000)
        page.wait_for_timeout(600)
        self.assertEqual(page.locator(FAILURE).count(), 0)

        # (3) The lower positions are reached once the override goes away: the
        # generated artwork is intercepted too, so the chain walks past it and
        # reuses the ALREADY-FAILED provisional resource at its own position —
        # without requesting it a second time.
        page.route(generated, serve_bundled)
        self._transition(page, "remove_room_binding")
        page.wait_for_selector(FAILURE, timeout=30000)
        page.wait_for_timeout(1000)
        self.assertEqual(
            sum(1 for url in self.requests if url == bundled),
            1,
            "the failed provisional resource was requested more than once",
        )
        # The reached failure is a real one from the chain, and the permitted
        # terminal is still presented (one labelled state, no broken image).
        self.assertGreater(page.locator(IMAGE).count() + page.locator(PLACEHOLDER).count(), 0)

        # (4) Exhausting every permitted source degrades to one labelled
        # non-image state with no broken image.
        for entry in artwork["attempts"] + ([artwork["terminal"]] if artwork["terminal"] else []):
            resource = entry.get("resource") if isinstance(entry, dict) else None
            if resource and resource.get("url"):
                page.route(resource["url"], serve_bundled)
        self._transition(page, "done_scene")
        page.wait_for_selector(PLACEHOLDER, timeout=30000)
        page.wait_for_timeout(1000)
        self.assertEqual(page.locator(IMAGE).count(), 0)
        self.assertEqual(page.locator(PLACEHOLDER).count(), 1)
        self.assertTrue(page.locator(PLACEHOLDER_LABEL).inner_text().strip())
