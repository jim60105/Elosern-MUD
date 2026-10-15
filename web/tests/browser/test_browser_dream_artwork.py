"""Dream stage artwork browser acceptance (change ``unified-dream-rendering``).

One journey with two real boots of a per-test isolated server, both with the
shipped catalogs and the dream entered through the committed sleep surface (the
wait card's 放棄／睡眠 row and the 進入夢境協作？ question):

* the operator root holds no preferred image, so the REQUIRED bundled dream
  illustration is what the stage presents — never the sleeper's own room
  background and never a failure marker;
* the operator root DOES admit the exact preferred identity, whose media the
  browser then cannot load: the interception happens AFTER the backend resolved
  and serialized the committed descriptor, so the reached failure is the
  browser's own local fact. The bundled dream stands in for it, the failure
  marker stays accessible, the shared full view opens on exactly the displayed
  resource and the same failure, the reply bar and the awakening stay usable,
  and no generation is queued for the sleeper's room.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import activate_wait_row, store_state
from .fixtures import create_runtime
from .harness import ManagedServer, ManagedServerTearDownMixin

PANEL = '[data-testid="dream-panel"]'
ART_IMAGE = '[data-testid="dream-scene-art"]'
ART_FAILURE = '[data-testid="dream-art-failure"]'
ART_CONTROL = '[data-testid="dream-art-control"]'
ART_VIEW = '[data-testid="dream-art-view"]'
ART_VIEW_IMAGE = '[data-testid="dream-art-view-image"]'
ART_VIEW_FAILURE = '[data-testid="dream-art-view-failure"]'
REPLY = '[data-testid="dream-reply"] textarea'
REPLY_SEND = '[data-testid="dream-reply"] button[type="submit"]'

# The dream chain's own positions and identities.
PREFERRED_PATH = "/npc/dream_goddess/dream-throne.webp"
PREFERRED_SOURCE = "scene.operator:dream_throne"
BUNDLED_SOURCE = "scene.bundled:dream_throne"
BUNDLED_PREFIX = "/art/bundled-scene/dream_throne/"
# The physical-scene positions the dream must never inherit.
ROOM_SOURCES = ("scene.room:", "scene.generated:")


class DreamArtworkBrowserTest(ManagedServerTearDownMixin, BrowserAcceptanceTest):
    """The dream stage's picture on per-test isolated servers."""

    @classmethod
    def setUpClass(cls) -> None:
        # Each phase boots its own isolated server; never the shared one.
        pass

    def setUp(self) -> None:
        self.servers: list[ManagedServer] = []
        # The mixin's own stop targets ``self.server``; every server this test
        # boots is stopped by the cleanup below instead.
        self.server = None
        super().setUp()
        self.addCleanup(self._stop_servers)

    def _stop_servers(self) -> None:
        for server in self.servers:
            server.stop()
        self.servers = []

    # --- helpers ---------------------------------------------------------

    def boot(self, **env: str):
        """Boot one isolated shipped-catalog server and open a logged-in page."""
        runtime = create_runtime()
        runtime.env["ELOSERN_BROWSER_SYNTH_CATALOGS"] = "0"
        for key, value in env.items():
            runtime.env[key] = value
        server = ManagedServer(runtime=runtime)
        server.start()
        self.servers.append(server)
        self.base_url = f"http://127.0.0.1:{server.runtime.http_port}"
        self.webclient_url = server.runtime.webclient_url
        return server

    def enter_dream(self, page) -> None:
        """Enter the committed dream through the wait card's sleep question."""
        activate_wait_row(page, "wait-sleep", dream=True, timeout=60000)
        page.wait_for_selector(PANEL, state="visible", timeout=60000)

    def dream(self, page) -> dict:
        return store_state(page)["panels"]["dream"]["state"]

    def descriptor(self, page) -> dict:
        return self.dream(page)["scene_art"]

    def art_scene(self, page):
        """The art panel's committed scene descriptor, or ``None``."""
        panel = (store_state(page)["panels"] or {}).get("art") or {}
        return ((panel.get("scene") or {}).get("artwork")) or None

    def displayed(self, page) -> str:
        image = page.locator(ART_IMAGE)
        assert image.count() == 1, "the dream stage presents exactly one layer"
        return image.get_attribute("src")

    # --- the journey -----------------------------------------------------

    @covers_requirement(
        "webclient-dream-stage::the-dream-is-a-full-stage-avg-scene-over-its-official-artwork"
    )
    def test_offline_dream_and_official_failure_use_shared_scene(self):
        # ---- phase 1: the operator root holds no preferred image --------
        self.boot()
        page = self.logged_in_page()
        art_before = self.art_scene(page)
        self.enter_dream(page)
        descriptor = self.descriptor(page)
        self.assertTrue(descriptor["subject_id"].startswith("dream:"))
        # The chain is exactly the dream's own positions: the preferred
        # operator identity is ABSENT (normal no-art configuration, no reached
        # failure), and neither the sleeper's room override nor a generated job
        # appears anywhere.
        self.assertEqual(
            [(entry["type"], entry["source_id"]) for entry in descriptor["attempts"]],
            [("image", BUNDLED_SOURCE)],
        )
        self.assertEqual(
            [entry for entry in descriptor["attempts"] if entry["source_id"].startswith(ROOM_SOURCES)],
            [],
        )
        self.assertIsNone(descriptor["generation_subject"])
        self.assertIsNone(descriptor["generation_state"])
        self.assertEqual(descriptor["retention_sources"], [])
        # The REQUIRED bundled dream is what the stage presents, with no error
        # styling at all.
        self.assertTrue(self.displayed(page).startswith(BUNDLED_PREFIX), self.displayed(page))
        self.assertEqual(page.locator(ART_FAILURE).count(), 0)
        # The physical room's own art state did not move while the dream
        # resolved; the dream queued no job for it.
        self.assertEqual(self.art_scene(page), art_before)

        # ---- phase 2: a configured preferred image the browser cannot load ----
        self.boot(ELOSERN_BROWSER_DREAM_ART="1")
        page2 = self.logged_in_page()
        art_before2 = self.art_scene(page2)
        # The interception is registered on the exact admitted path, so it can
        # only ever answer a request the backend ALREADY resolved and
        # serialized into the committed descriptor.
        page2.route(
            "**" + PREFERRED_PATH,
            lambda route: route.fulfill(
                status=200, content_type="image/webp", body=b"not an image at all"
            ),
        )
        self.enter_dream(page2)
        descriptor2 = self.descriptor(page2)
        preferred = [
            entry for entry in descriptor2["attempts"] if entry["source_id"] == PREFERRED_SOURCE
        ]
        self.assertEqual(len(preferred), 1, "the operator identity was not admitted")
        self.assertTrue(
            preferred[0]["resource"]["url"].startswith("/art/official/"),
            preferred[0]["resource"]["url"],
        )
        # The browser's own load failure is a LOCAL fact: the marker stays
        # visible and stated while the required bundled dream stands in.
        marker = page2.locator(ART_FAILURE)
        marker.wait_for(state="visible", timeout=60000)
        self.assertTrue(marker.inner_text().strip())
        self.assertTrue(self.displayed(page2).startswith(BUNDLED_PREFIX), self.displayed(page2))
        reached = [
            entry for entry in self.descriptor(page2)["attempts"] if entry["type"] == "fault"
        ]
        self.assertEqual([entry["reason"] for entry in reached], ["image_load_failed"])

        # The shared full view opens on exactly the displayed resource and the
        # same failure, and Escape closes it.
        page2.locator(ART_CONTROL).click()
        page2.locator(ART_VIEW).wait_for(state="visible", timeout=30000)
        self.assertEqual(page2.locator(ART_VIEW_IMAGE).get_attribute("src"), self.displayed(page2))
        self.assertEqual(page2.locator(ART_VIEW_FAILURE).inner_text(), marker.inner_text())
        page2.keyboard.press("Escape")
        page2.locator(ART_VIEW).wait_for(state="detached", timeout=30000)

        # The dialogue surface and the awakening stay usable under the failed
        # preferred image: the reply bar edits and readies its send, and the
        # 醒來 exit ends the committed dream.
        reply = page2.locator(REPLY)
        reply.fill("合成夢境對話")
        self.assertTrue(reply.is_enabled())
        self.assertTrue(page2.locator(REPLY_SEND).is_enabled())
        reply.fill("")
        page2.locator("[data-row='awaken']").click()
        page2.wait_for_selector(PANEL, state="detached", timeout=60000)
        # Nothing was queued for the physical room across either phase.
        self.assertEqual(self.art_scene(page2), art_before2)
