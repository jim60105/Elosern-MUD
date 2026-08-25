"""Art panel browser acceptance (webclient-art-panel 8.1-8.2).

Drives the real Evennia server's art panel through the Vue SPA scene
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

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    focus_action_dock,
    install_outbound_recorder,
    sent_action_count,
    store_state,
    wait_for_store_state,
)


def _art_panel_available(state: dict) -> bool:
    """The art panel renders when its committed payload is present and not unavailable."""
    art = (state.get("panels") or {}).get("art")
    return art is not None and art.get("available") is not False


def _art_portrait_ready(state: dict) -> bool:
    """A portrait tile renders only when the art panel is available and its catalog has entries."""
    art = (state.get("panels") or {}).get("art") or {}
    return (
        art.get("available") is not False
        and len(art.get("portrait_catalog") or {}) > 0
    )


def _art_missing_placeholder(state: dict) -> bool:
    """The missing-scene fixture: the art panel is available and the scene placeholder kind is 'missing'."""
    art = (state.get("panels") or {}).get("art") or {}
    scene = art.get("scene") or {}
    placeholder = scene.get("placeholder") or {}
    return art.get("available") is True and placeholder.get("kind") == "missing"


def _art_scene_failed(state: dict) -> bool:
    """The seeded art scene has reached the failed status."""
    scene = ((state.get("panels") or {}).get("art") or {}).get("scene") or {}
    return scene.get("status") == "failed"


def _art_scene_done(state: dict) -> bool:
    """The art scene is a done asset (a client-side load failure keeps it done)."""
    scene = ((state.get("panels") or {}).get("art") or {}).get("scene") or {}
    return scene.get("status") == "done"


def _in_combat_mode(state: dict) -> bool:
    """The client is in combat mode (a seeded monster was engaged)."""
    return state.get("mode") == "combat"


def _out_of_combat_mode(state: dict) -> bool:
    """Combat has ended (the forfeit settlement cleared the session)."""
    return state.get("mode") != "combat"


def _mutations_unlocked(state: dict) -> bool:
    """The action client's submission gate is closed (no mutation in flight)."""
    return state.get("mutationsLocked") is not True


def _connected_active(state: dict) -> bool:
    """The transport is connected and the client has left the snapshot/detached phases."""
    return bool(state.get("connected")) and state.get("phase") == "active"


ART_PANEL_DOM = {
    "selector": '[data-testid="art-panel"]',
    "predicate": (
        "() => { const p = document.querySelector('[data-testid=\"art-panel\"]'); "
        "if (!p) { return false; } "
        "const r = p.getBoundingClientRect(); "
        "return r.width > 0 && r.height > 0; }"
    ),
    "description": "art panel rendered and visible",
}

PORTRAIT_TILE_DOM = {
    "selector": ".art-panel__portrait-tile",
    "predicate": (
        "() => { const t = document.querySelector('.art-panel__portrait-tile'); "
        "if (!t) { return false; } "
        "const r = t.getBoundingClientRect(); "
        "return r.width > 0 && r.height > 0; }"
    ),
    "description": "a portrait tile is rendered and visible",
}

SCENE_PLACEHOLDER_DOM = {
    "selector": '[data-testid="scene-backdrop-placeholder"]',
    "predicate": (
        "() => { const p = document.querySelector('[data-testid=\"scene-backdrop-placeholder\"]'); "
        "if (!p) { return false; } "
        "const r = p.getBoundingClientRect(); "
        "return r.width > 0 && r.height > 0; }"
    ),
    "description": "scene placeholder (load-failure fallback) rendered and visible",
}


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
    @covers_requirement("webclient-contextual-hud::the-scene-backdrop-renders-the-art-payload-truthfully-behind-the-stage")
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
        img = page.locator('[data-testid="scene-backdrop-image"]')
        self.assertEqual(img.count(), 1)
        self.assertTrue(img.get_attribute("src").startswith("/art/"))
        self.assertNotIn("http://", img.get_attribute("src"))

    @covers_requirement("webclient-art-panel::the-scene-payload-resolves-only-validated-archetypes-with-truthful-placeholders")
    def test_alternative_text_is_present_outside_the_bitmap(self):
        page = self.logged_in_page()
        # Requirement: the scene label and alternative text SHALL remain visible
        # outside the bitmap. The scene moved to the full-bleed `SceneBackdrop`
        # (H1); the label/alt render as DOM text nodes
        # (`[data-testid="scene-backdrop-label"]`, `[data-testid="scene-backdrop-alt"]`),
        # so the alt text is the `scene-backdrop-alt` node, not the img `alt` attribute.
        alt = page.locator('[data-testid="scene-backdrop-alt"]').inner_text()
        self.assertTrue(alt.strip(), "scene alternative text must be meaningful and non-empty")
        caption = page.locator('[data-testid="scene-backdrop-label"]').inner_text()
        self.assertEqual(caption, "酒館內部")

    @covers_requirement("webclient-art-panel::art-panel-browser-acceptance-is-keyboard-first-accessible-and-desktop-bounded")
    def test_scene_caption_and_status_usable_at_1280x720(self):
        page = self.logged_in_page((1280, 720))
        # The done scene image, its caption label and alt, and the pending
        # status line remain visible at the smaller supported viewport.
        img = page.locator('[data-testid="scene-backdrop-image"]')
        self.assertEqual(img.count(), 1)
        self.assertTrue(img.is_visible())
        self.assertEqual(page.locator('[data-testid="scene-backdrop-label"]').inner_text(), "酒館內部")
        self.assertTrue(page.locator('[data-testid="scene-backdrop-alt"]').inner_text().strip())
        self.assertTrue(page.locator('[data-testid="scene-backdrop"]').is_visible())



class ArtPendingSceneTest(ArtSceneBrowserTest):
    def setUp(self) -> None:
        os.environ["ELOSERN_BROWSER_ART"] = "pending"
        super().setUp()
        os.environ.pop("ELOSERN_BROWSER_ART", None)

    @covers_requirement("webclient-art-panel::the-scene-payload-resolves-only-validated-archetypes-with-truthful-placeholders")
    @covers_requirement("webclient-contextual-hud::the-scene-backdrop-renders-the-art-payload-truthfully-behind-the-stage")
    def test_pending_scene_without_prior_image_uses_placeholder(self):
        page = self.logged_in_page()
        panel = store_state(page)["panels"]["art"]
        self.assertEqual(panel["scene"]["status"], "pending")
        self.assertIsNone(panel["scene"]["url"])
        # Without a prior image, the scene placeholder renders (no image).
        self.assertEqual(page.locator('[data-testid="scene-backdrop-image"]').count(), 0)
        placeholder = page.locator('[data-testid="scene-backdrop-placeholder"]').inner_text()
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
    @covers_requirement("webclient-contextual-hud::the-scene-backdrop-renders-the-art-payload-truthfully-behind-the-stage")
    def test_failed_scene_uses_the_placeholder(self):
        page = self.logged_in_page()
        # Drain the queue with the failing image-generation client, then refresh
        # presentation.
        page.evaluate("Evennia.msg('text', ['@art run --limit 1'], {})")
        page.wait_for_timeout(1500)
        page.evaluate("Evennia.msg('text', ['look'], {})")
        # The failed-scene placeholder-count assertion is gated on the shared
        # bounded-wait helper: the committed art-panel store state plus a
        # single-node DOM-readiness descriptor, within one bounded deadline —
        # not a single raw `.count()` sample that a snapshot-refresh or Vue
        # re-render double-node window under a loaded runner would race.
        wait_for_store_state(
            page,
            _art_scene_failed,
            {
                "selector": '[data-testid="scene-backdrop"] [data-testid="scene-backdrop-placeholder"]',
                "predicate": (
                    "() => { const els = document.querySelectorAll('[data-testid=\"scene-backdrop\"] [data-testid=\"scene-backdrop-placeholder\"]'); "
                    "if (els.length !== 1) { return false; } "
                    "const el = els[0]; const r = el.getBoundingClientRect(); "
                    "return r.width > 0 && r.height > 0 && el.offsetParent !== null; }",
                ),
                "description": "single visible scene placeholder inside the scene frame",
            },
            timeout=20000,
        )
        self.assertEqual(store_state(page)["panels"]["art"]["scene"]["status"], "failed")
        self.assertIsNone(store_state(page)["panels"]["art"]["scene"]["url"])
        self.assertEqual(page.locator('[data-testid="scene-backdrop-image"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="scene-backdrop-placeholder"]').count(), 1)


class ArtMissingSceneTest(ArtSceneBrowserTest):
    def setUp(self) -> None:
        os.environ["ELOSERN_BROWSER_ART"] = "missing"
        super().setUp()
        os.environ.pop("ELOSERN_BROWSER_ART", None)

    @covers_requirement(
        "webclient-art-panel::art-degradation-never-blocks-gameplay-or-leaks-rejected-content",
        "webclient-browser-verification::browser-test-waits-gate-on-deterministic-state-within-a-bounded-deadline",
        "webclient-contextual-hud::the-scene-backdrop-renders-the-art-payload-truthfully-behind-the-stage",
    )
    def test_missing_scene_uses_the_placeholder_and_play_continues(self):
        page = self.logged_in_page()
        # The missing-scene placeholder is gated on the committed art-panel
        # store state and the scene-frame-scoped single-node DOM, within one
        # bounded deadline — not a single raw `.count()` sample that a
        # snapshot-refresh double-node window under a loaded CI runner would
        # race.
        wait_for_store_state(
            page,
            _art_missing_placeholder,
            dom_readiness={
                "selector": "[data-testid=\"scene-backdrop\"] [data-testid=\"scene-backdrop-placeholder\"]",
                "predicate": (
                    "() => { const els = document.querySelectorAll('[data-testid=\"scene-backdrop\"] [data-testid=\"scene-backdrop-placeholder\"]'); "
                    "if (els.length !== 1) { return false; } "
                    "const el = els[0]; const r = el.getBoundingClientRect(); "
                    "return r.width > 0 && r.height > 0 && el.offsetParent !== null; }"
                ),
                "description": "single visible scene placeholder inside the scene frame",
            },
        )
        # Movement through the ordinary transport still works. The narrative
        # assertion is gated on the shared bounded store-state + DOM path
        # (no fixed sleep) so it stays stable under a loaded CI runner.
        before = len(page.locator(".elosern-narrative").inner_text())
        page.evaluate("Evennia.msg('text', ['look'], {})")
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")) and s.get("phase") == "active",
            dom_readiness={
                "selector": ".elosern-narrative",
                "predicate": (
                    f"() => {{ const f = document.querySelector('.elosern-narrative'); "
                    f"return f && f.innerText.trim().length > {before}; }}"
                ),
                "description": "narrative feed length grew past the pre-look baseline",
            },
        )
        narrative = page.locator('[data-testid="narrative-feed"]').inner_text()
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
        wait_for_store_state(
            page,
            _art_scene_done,
            SCENE_PLACEHOLDER_DOM,
            timeout=20000,
        )
        self.assertEqual(page.locator('[data-testid="scene-backdrop-image"]').count(), 0)
        placeholder = page.locator('[data-testid="scene-backdrop-placeholder"]')
        self.assertTrue(placeholder.inner_text().strip())
        self.assertEqual(
            placeholder.get_attribute("data-kind"),
            "load_failed",
            "an image load failure shows the load_failed placeholder kind",
        )
        # The aborted request was attempted exactly once.
        self.assertEqual(len(self._art_requests), 1)
        # A later snapshot refresh must not re-request the failed URL.
        page.evaluate("Evennia.msg('text', ['look'], {})")
        page.wait_for_timeout(800)
        page.evaluate("Evennia.msg('text', ['look'], {})")
        page.wait_for_timeout(800)
        self.assertEqual(len(self._art_requests), 1)
        # Play continues deterministically.
        narrative = page.locator('[data-testid="narrative-feed"]').inner_text()
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
        wait_for_store_state(page, _in_combat_mode)
        return store_state(page)

    def _focus_combat_dock(self, page) -> None:
        """Focus the action dock and wait for the mounted, unlocked router.

        The combat dock renders its first row synchronously inside the router
        reset's focus emission, so a mounted ``#combat-row-0`` proves the
        KeyboardRouter frame exists; waiting for ``isMutationInFlight()`` to be
        false closes the router's submission gate. Together they guarantee a
        subsequent Enter press reaches the KeyboardRouter and is never
        swallowed by the command-drawer field or an unfocused editable target.
        """
        focus_action_dock(page)
        page.wait_for_function(
            "() => !!document.querySelector('#combat-row-0')", timeout=15000
        )
        wait_for_store_state(page, _mutations_unlocked, timeout=15000)

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
        # the combat dock, so a portrait card with name/role renders. The
        # combat catalog holds one entry per participant (actor + monster), so
        # the focused portrait is the first tile; scope to it to avoid a
        # strict-mode violation.
        wait_for_store_state(page, _art_portrait_ready, PORTRAIT_TILE_DOM, timeout=15000)
        name = page.locator(".art-panel__portrait-context-name").first.inner_text()
        role = page.locator(".art-panel__portrait-context-role").first.inner_text()
        self.assertTrue(name.strip())
        self.assertIn(role, ("隊友", "敵方"))
        # No focus packet was ever sent.
        self.assertEqual(sent_action_count(page, None), 0)

    @covers_requirement("webclient-art-panel::contextual-portrait-focus-is-client-local-and-verified")
    def test_exploration_portrait_tiles_match_the_catalog(self):
        page = self.logged_in_page()
        # The exploration room seeds a present dialogue host, which the server
        # authors into the portrait catalog. The renderer shows exactly one
        # portrait tile per catalog entry — no extra client-built cards.
        panel = store_state(page)["panels"]["art"]
        expected = len(panel.get("portrait_catalog") or {})
        wait_for_store_state(page, _art_panel_available, ART_PANEL_DOM)
        self.assertEqual(page.locator(".art-panel__portrait-tile").count(), expected)

    @covers_requirement("webclient-art-panel::art-panel-browser-acceptance-is-keyboard-first-accessible-and-desktop-bounded")
    def test_portrait_overlay_usable_at_1280x720(self):
        page = self.logged_in_page((1280, 720))
        self._engage(page)
        wait_for_store_state(page, _art_portrait_ready, PORTRAIT_TILE_DOM, timeout=15000)
        # The combat catalog has one entry per participant, so scope the
        # assertions to the first (focused) tile to avoid a strict-mode violation.
        self.assertTrue(page.locator(".art-panel__portrait-tile").first.is_visible())
        self.assertTrue(page.locator(".art-panel__portrait-context-name").first.inner_text().strip())
        self.assertTrue(page.locator('[data-testid="scene-backdrop-image"]').is_visible())

    @covers_requirement("webclient-art-panel::contextual-portrait-focus-is-client-local-and-verified")
    @covers_requirement("webclient-browser-verification::art-panel-portrait-keyboard-journeys-establish-dock-focus-before-key-presses")
    def test_keyboard_focus_switches_the_portrait_without_a_packet(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._engage(page)
        # The combat dock publishes the first party participant's portrait.
        wait_for_store_state(page, _art_portrait_ready, PORTRAIT_TILE_DOM, timeout=15000)
        first_name = page.locator(".art-panel__portrait-context-name").first.inner_text()
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
        wait_for_store_state(
            page,
            _art_portrait_ready,
            {
                "selector": f'[data-testid="art-panel__portrait-context--{monster_id}"]',
                "predicate": (
                    f"() => {{ const el = document.querySelector('[data-testid=\"art-panel__portrait-context--{monster_id}\"]'); "
                    f"if (!el) {{ return false; }} "
                    f"const name = el.querySelector('.art-panel__portrait-context-name'); "
                    f"return name && name.textContent === '{monster_name}'; }}"
                ),
                "description": "focused portrait context shows the monster's name",
            },
            timeout=15000,
        )
        # After navigating to the enemy target, the focused portrait switches
        # to that participant's tile. Scope to the monster's tile.
        monster_name_shown = page.get_by_test_id(
            f"art-panel__portrait--{str(monster_id)}"
        ).locator(".art-panel__portrait-context-name").inner_text()
        self.assertNotEqual(monster_name_shown, first_name)
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
        wait_for_store_state(page, _out_of_combat_mode, timeout=15000)
        art = store_state(page)["panels"]["art"]
        self.assertNotIn(str(monster_id), art["portrait_catalog"])


if __name__ == "__main__":
    import unittest

    unittest.main()
