"""Art panel browser acceptance (webclient-art-panel 8.1-8.2).

Drives the real Evennia server's art panel through the GoldenLayout scene
renderer and contextual portrait overlay. The seed fixture (``ELOSERN_BROWSER_ART``)
places the character in a validated scene room with a done/pending/failed scene
record and a named-policy NPC plus a living monster. Journeys assert same-origin
URL rendering, truthful placeholders, keyboard-only full view, portrait overlay
with name/role context, client-local focus switching with no packet, no-focus
no-card, combat results removing the catalog entry in the same update, and the
adult-gate payload exclusion.
"""

from __future__ import annotations

import os
import time

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    install_outbound_recorder,
    sent_action_count,
    store_state,
)


class ArtSceneBrowserTest(BrowserAcceptanceTest):
    """Scene renderer journeys on a per-test isolated server.

    Each test boots its own isolated server so the seeded art mode (done /
    pending / failed / missing) is deterministic per journey.
    """

    def setUp(self) -> None:
        from .harness import ManagedServer

        self.server = ManagedServer()
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    @classmethod
    def setUpClass(cls) -> None:
        # Each test boots its own isolated server; never the shared one.
        pass

    def tearDown(self) -> None:
        super().tearDown()
        if getattr(self, "server", None) is not None:
            try:
                self.server.stop()
            finally:
                self.server = None


class ArtDoneSceneTest(ArtSceneBrowserTest):
    """A done scene renders the same-origin media URL and full view."""

    def setUp(self) -> None:
        os.environ["ELOSERN_BROWSER_ART"] = "done"
        super().setUp()
        os.environ.pop("ELOSERN_BROWSER_ART", None)

    @covers_requirement("webclient-art-panel::the-scene-payload-resolves-only-validated-archetypes-with-truthful-placeholders")
    def test_done_scene_renders_same_origin_image(self):
        page = self.logged_in_page()
        state = store_state(page)
        panel = state["panels"]["art"]
        self.assertTrue(panel["available"])
        self.assertEqual(panel["scene"]["status"], "done")
        self.assertEqual(panel["scene"]["url"], "/art/scene/tavern_interior.png")
        self.assertEqual(panel["scene"]["aspect_ratio"], "16:9")
        self.assertIsNone(panel["scene"]["placeholder"])
        # The image element is present with a same-origin src.
        img = page.locator(".art-scene .art-scene-image")
        self.assertEqual(img.count(), 1)
        self.assertTrue(img.get_attribute("src").startswith("/art/"))
        self.assertNotIn("http://", img.get_attribute("src"))

    @covers_requirement("webclient-art-panel::art-panel-browser-acceptance-is-keyboard-first-accessible-and-desktop-bounded")
    def test_keyboard_full_view_opens_and_closes(self):
        page = self.logged_in_page()
        img = page.locator(".art-scene .art-scene-image")
        img.focus()
        page.keyboard.press("Enter")
        page.wait_for_selector(".art-fullview")
        self.assertEqual(page.locator(".art-fullview").count(), 1)
        page.keyboard.press("Escape")
        page.wait_for_function("() => !document.querySelector('.art-fullview')")
        self.assertEqual(page.locator(".art-fullview").count(), 0)
        # Focus returns to the scene image.
        page.wait_for_function(
            "() => document.activeElement === document.querySelector('.art-scene-image')"
        )

    @covers_requirement("webclient-art-panel::the-scene-payload-resolves-only-validated-archetypes-with-truthful-placeholders")
    def test_alternative_text_is_present_outside_the_bitmap(self):
        page = self.logged_in_page()
        alt = page.locator(".art-scene .art-scene-image").get_attribute("alt")
        self.assertTrue(alt and alt.strip())
        caption = page.locator(".art-caption-label").inner_text()
        self.assertEqual(caption, "酒館內部")

    @covers_requirement("webclient-art-panel::art-panel-browser-acceptance-is-keyboard-first-accessible-and-desktop-bounded")
    def test_scene_caption_and_status_usable_at_1280x720(self):
        page = self.logged_in_page((1280, 720))
        # The done scene image, its caption label and alt, and the pending
        # status line remain visible at the smaller supported viewport.
        img = page.locator(".art-scene .art-scene-image")
        self.assertEqual(img.count(), 1)
        self.assertTrue(img.is_visible())
        self.assertEqual(page.locator(".art-caption-label").inner_text(), "酒館內部")
        self.assertTrue(page.locator(".art-caption-alt").inner_text().strip())
        self.assertTrue(page.locator(".art-scene").is_visible())

    @covers_requirement("webclient-art-panel::art-panel-browser-acceptance-is-keyboard-first-accessible-and-desktop-bounded")
    def test_keyboard_full_view_usable_at_1280x720(self):
        page = self.logged_in_page((1280, 720))
        img = page.locator(".art-scene .art-scene-image")
        img.focus()
        page.keyboard.press("Enter")
        page.wait_for_selector(".art-fullview")
        self.assertTrue(page.locator(".art-fullview").is_visible())
        page.keyboard.press("Escape")
        page.wait_for_function("() => !document.querySelector('.art-fullview')")
        page.wait_for_function(
            "() => document.activeElement === document.querySelector('.art-scene-image')"
        )


class ArtPendingSceneTest(ArtSceneBrowserTest):
    def setUp(self) -> None:
        os.environ["ELOSERN_BROWSER_ART"] = "pending"
        super().setUp()
        os.environ.pop("ELOSERN_BROWSER_ART", None)

    @covers_requirement("webclient-art-panel::the-scene-payload-resolves-only-validated-archetypes-with-truthful-placeholders")
    def test_pending_scene_without_prior_image_uses_placeholder(self):
        page = self.logged_in_page()
        panel = store_state(page)["panels"]["art"]
        self.assertEqual(panel["scene"]["status"], "pending")
        self.assertIsNone(panel["scene"]["url"])
        # Without a prior image, the scene placeholder renders (no image).
        self.assertEqual(page.locator(".art-scene .art-scene-image").count(), 0)
        placeholder = page.locator(".art-scene-placeholder").inner_text()
        self.assertTrue(placeholder.strip())


class ArtFailedSceneTest(ArtSceneBrowserTest):
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
    def test_failed_scene_uses_the_placeholder(self):
        page = self.logged_in_page()
        # Drain the queue with the failing image-generation client, then refresh
        # presentation.
        page.evaluate("Evennia.msg('text', ['@art run --limit 1'], {})")
        page.wait_for_timeout(1500)
        page.evaluate("Evennia.msg('text', ['look'], {})")
        deadline = __import__("time").monotonic() + 20
        while __import__("time").monotonic() < deadline:
            panel = store_state(page)["panels"]["art"]
            if panel["scene"]["status"] == "failed":
                break
            page.wait_for_timeout(500)
        self.assertEqual(store_state(page)["panels"]["art"]["scene"]["status"], "failed")
        self.assertIsNone(store_state(page)["panels"]["art"]["scene"]["url"])
        self.assertEqual(page.locator(".art-scene .art-scene-image").count(), 0)
        self.assertEqual(page.locator(".art-scene-placeholder").count(), 1)


class ArtMissingSceneTest(ArtSceneBrowserTest):
    def setUp(self) -> None:
        os.environ["ELOSERN_BROWSER_ART"] = "missing"
        super().setUp()
        os.environ.pop("ELOSERN_BROWSER_ART", None)

    @covers_requirement("webclient-art-panel::art-degradation-never-blocks-gameplay-or-leaks-rejected-content")
    def test_missing_scene_uses_the_placeholder_and_play_continues(self):
        page = self.logged_in_page()
        panel = store_state(page)["panels"]["art"]
        self.assertTrue(panel["available"])
        self.assertEqual(panel["scene"]["placeholder"]["kind"], "missing")
        self.assertEqual(page.locator(".art-scene-placeholder").count(), 1)
        # Movement through the ordinary transport still works.
        page.evaluate("Evennia.msg('text', ['look'], {})")
        page.wait_for_timeout(500)
        narrative = page.locator(".elosern-narrative").inner_text()
        self.assertTrue(narrative.strip())


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

    def _abort_art_media(self, page) -> None:
        # Track how often the scene image URL is requested.
        self._art_requests = []

        def _handler(route):
            if route.request.url.endswith("/art/scene/tavern_interior.png"):
                self._art_requests.append(route.request.url)
                route.abort("failed")
            else:
                route.continue_()

        # Abort the art media URL before the shared local-only guard is
        # consulted by registering a more specific route after it.
        page.route("**/art/**", _handler)

    @covers_requirement("webclient-art-panel::art-degradation-never-blocks-gameplay-or-leaks-rejected-content")
    def test_image_load_failure_shows_fallback_without_refetch(self):
        page = self.new_page()
        self._abort_art_media(page)
        from .browser_helpers import login_and_open

        login_and_open(page, self.webclient_url, self.base_url)
        # The panel resolves the done scene but the image load fails, so the
        # truthful fallback replaces the broken image inside the asset pane.
        page.wait_for_function(
            "() => !!document.querySelector('.art-scene .art-scene-empty')",
            timeout=20000,
        )
        self.assertEqual(page.locator(".art-scene-image").count(), 0)
        fallback = page.locator(".art-scene .art-scene-empty").inner_text()
        self.assertTrue(fallback.strip())
        self.assertIn("載入失敗", fallback)
        # The aborted request was attempted exactly once.
        self.assertEqual(len(self._art_requests), 1)
        # A later snapshot refresh must not re-request the failed URL.
        page.evaluate("Evennia.msg('text', ['look'], {})")
        page.wait_for_timeout(800)
        page.evaluate("Evennia.msg('text', ['look'], {})")
        page.wait_for_timeout(800)
        self.assertEqual(len(self._art_requests), 1)
        # Play continues deterministically.
        narrative = page.locator(".elosern-narrative").inner_text()
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
        page.evaluate("Evennia.msg('text', ['engage 酒館灰狼'], {})")
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            state = store_state(page)
            if state["mode"] == "combat":
                return state
            page.wait_for_timeout(250)
        raise AssertionError("combat mode never became available")

    def _focus_combat_dock(self, page) -> None:
        """Focus the action dock and wait for the mounted, unlocked router.

        The combat dock renders its first row synchronously inside the router
        reset's focus emission, so a mounted ``#combat-row-0`` proves the
        KeyboardRouter frame exists; waiting for ``isMutationInFlight()`` to be
        false closes the router's submission gate. Together they guarantee a
        subsequent Enter press reaches the KeyboardRouter and is never
        swallowed by the command-drawer field or an unfocused editable target.
        """
        page.evaluate("document.getElementById('action-dock').focus()")
        page.wait_for_function(
            "() => !!document.querySelector('#combat-row-0')", timeout=15000
        )
        page.wait_for_function(
            "() => !window.__elosernBridge.facade.actions.client.isInFlight()", timeout=15000
        )

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
        # The art renderer subscribes to the client-local focus published by
        # the combat dock, so a portrait card with name/role renders.
        page.wait_for_function(
            "() => !!document.querySelector('.art-portrait')", timeout=15000
        )
        name = page.locator(".art-portrait-name").inner_text()
        role = page.locator(".art-portrait-role").inner_text()
        self.assertTrue(name.strip())
        self.assertIn(role, ("隊友", "敵方"))
        # No focus packet was ever sent.
        self.assertEqual(sent_action_count(page, None), 0)

    @covers_requirement("webclient-art-panel::contextual-portrait-focus-is-client-local-and-verified")
    def test_no_focus_means_no_portrait_card_in_exploration(self):
        page = self.logged_in_page()
        # Exploration mode has no contextual focus source yet, so no card.
        page.wait_for_function("() => !!document.querySelector('.elosern-art')")
        page.wait_for_timeout(500)
        self.assertEqual(page.locator(".art-portrait").count(), 0)

    @covers_requirement("webclient-art-panel::art-panel-browser-acceptance-is-keyboard-first-accessible-and-desktop-bounded")
    def test_portrait_overlay_usable_at_1280x720(self):
        page = self.logged_in_page((1280, 720))
        self._engage(page)
        page.wait_for_function(
            "() => !!document.querySelector('.art-portrait')", timeout=15000
        )
        self.assertTrue(page.locator(".art-portrait").is_visible())
        self.assertTrue(page.locator(".art-portrait-name").inner_text().strip())
        self.assertTrue(page.locator(".art-scene").is_visible())

    @covers_requirement("webclient-art-panel::contextual-portrait-focus-is-client-local-and-verified")
    @covers_requirement("webclient-browser-verification::art-panel-portrait-keyboard-journeys-establish-dock-focus-before-key-presses")
    def test_keyboard_focus_switches_the_portrait_without_a_packet(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        # The combat dock publishes the first party participant's portrait.
        page.wait_for_function(
            "() => !!document.querySelector('.art-portrait')", timeout=15000
        )
        first_name = page.locator(".art-portrait-name").inner_text()
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
        # field. The single-target menu lists the actor first (presenter
        # order), so move past it to the enemy target like the combat-menu
        # journeys do.
        self._focus_combat_dock(page)
        page.keyboard.press("Enter")
        # The basic-attack target menu mounts (its first cell is a target row)
        # before navigating it.
        self._wait_combat_row_key(page, "target-", row_zero=True)
        page.keyboard.press("ArrowRight")  # past the actor to the enemy target
        self._wait_combat_row_key(page, "target-" + str(monster_id))
        page.wait_for_function(
            "(n) => document.querySelector('.art-portrait-name') && "
            "document.querySelector('.art-portrait-name').innerText === n",
            arg=monster_name,
            timeout=15000,
        )
        self.assertNotEqual(
            page.locator(".art-portrait-name").inner_text(), first_name
        )
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
        # Forfeit the battle deterministically (no dice roll): the terminal
        # settlement clears the session and the catalog entry disappears in the
        # same combat update.
        # Root order: attack, skills, items, defend, flee, forfeit.
        self._focus_combat_dock(page)
        for _ in range(5):
            page.keyboard.press("ArrowDown")
            page.wait_for_timeout(60)
        page.keyboard.press("Enter")  # open the secondary Forfeit menu
        # The confirmation frame mounts before the confirming Enter.
        self._wait_combat_row_key(page, "confirm-forfeit")
        page.keyboard.press("Enter")  # confirm-forfeit
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            state = store_state(page)
            if state["mode"] != "combat":
                break
            page.wait_for_timeout(250)
        else:
            raise AssertionError("combat never ended after forfeit")
        art = store_state(page)["panels"]["art"]
        self.assertNotIn(str(monster_id), art["portrait_catalog"])


if __name__ == "__main__":
    import unittest

    unittest.main()
