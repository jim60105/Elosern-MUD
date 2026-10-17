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

import re
import time

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    narrative_log_text,
    open_command_line,
    store_state,
    wait_for_store_state,
)
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
        state = store_state(page)
        panel = (state.get("panels") or {}).get("art") or {}
        scene = panel.get("scene") or {}
        artwork = scene.get("artwork") or {}
        raise AssertionError(
            "no scene image was ever presented: "
            f"mode={state['mode']} available={panel.get('available')} "
            f"reason={panel.get('reason')} "
            f"generation={artwork.get('generation_state')} "
            f"attempts={[(entry.get('type'), entry.get('rank'), entry.get('source_id')) for entry in artwork.get('attempts') or []]} "
            f"terminal={bool(artwork.get('terminal'))} "
            f"layers={page.locator('img[data-role]').evaluate_all('(els) => els.map((e) => e.getAttribute(\"src\"))')} "
            f"badge={page.locator(PLACEHOLDER).count()} "
            f"art_responses={[item for item in getattr(self, 'responses', []) if '/art/' in item][-4:]} "
            f"art_requests={[url for url in self.requests if '/art/' in url][-4:]}"
        )

    def _wait_source(self, page, source_prefix: str, timeout: int = 30000) -> str:
        """Wait until the presented resource belongs to one chain position."""
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            artwork = self._art(page)
            attempts = [entry for entry in artwork["attempts"] if entry["type"] == "image"]
            if artwork.get("terminal"):
                # The permitted terminal is its own position, never an attempt
                # entry: it is matched here exactly like one.
                attempts = attempts + [artwork["terminal"]]
            displayed = self._displayed(page)
            for entry in attempts:
                if (
                    entry["source_id"].startswith(source_prefix)
                    and entry["resource"]["url"] == displayed
                ):
                    return entry["resource"]["url"]
            page.wait_for_timeout(200)
        artwork = self._art(page)
        raise AssertionError(
            f"the {source_prefix} position was never presented: "
            f"displayed={self._displayed(page)} "
            f"attempts={[(e.get('type'), e.get('rank'), e.get('source_id')) for e in artwork.get('attempts') or []]} "
            f"terminal={(artwork.get('terminal') or {}).get('source_id')} "
            f"badge={page.locator(PLACEHOLDER).count()} "
            f"layers={page.locator('img[data-role]').evaluate_all('(els) => els.map((e) => [e.getAttribute(\"data-role\"), e.getAttribute(\"src\")])')} "
            f"art_requests={[url for url in self.requests if '/art/' in url][-4:]} "
            f"art_responses={[item for item in getattr(self, 'responses', []) if '/art/' in item][-4:]}"
        )

    def _transition(self, page, name: str) -> None:
        open_command_line(page)
        page.keyboard.type(f"uieditor_transition {name}")
        page.keyboard.press("Enter")
        page.wait_for_timeout(400)

    def _admitted_urls(self, page) -> set[str]:
        """Every media URL the committed scene descriptor itself names."""
        artwork = self._art(page)
        urls = {
            entry["resource"]["url"]
            for entry in artwork.get("attempts") or []
            if entry.get("type") == "image" and entry.get("resource")
        }
        terminal = artwork.get("terminal")
        if terminal and terminal.get("resource"):
            urls.add(terminal["resource"]["url"])
        return urls

    def _wait_badge(self, page, timeout: int = 30000) -> None:
        """Wait until the standalone status badge is on the page.

        The badge is the state the exhausted chain degrades to; it is awaited by
        its own presence (a real DOM fact) rather than by Playwright's
        visibility heuristic, and a timeout reports the committed facts.
        """
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            if page.locator(PLACEHOLDER).count():
                return
            page.wait_for_timeout(250)
        artwork = self._art(page)
        raise AssertionError(
            "the exhausted chain never rendered its status badge: "
            f"displayed={self._displayed(page)} "
            f"attempts={[(e.get('type'), e.get('rank'), e.get('source_id')) for e in artwork.get('attempts') or []]} "
            f"terminal={(artwork.get('terminal') or {}).get('source_id')} "
            f"layers={page.locator('img[data-role]').evaluate_all('(els) => els.map((e) => [e.getAttribute(\"data-role\"), e.getAttribute(\"src\")])')} "
            f"art_responses={[item for item in getattr(self, 'responses', []) if '/art/' in item][-4:]}"
        )

    def _wait_mode(self, page, mode: str, timeout: int = 30000) -> None:
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            if store_state(page)["mode"] == mode:
                return
            page.wait_for_timeout(250)
        raise AssertionError(
            f"mode {mode!r} never committed; the committed state is "
            f"{store_state(page)['mode']!r} and the narrative reads "
            f"{self._narrative(page)!r}"
        )

    def _wait_surrender_token(self, page, timeout: int = 30000) -> str:
        """Return the confirmation token the party-surrender prompt prints.

        The prompt binds the session and the round revision and states the
        exact confirmation syntax, so the journey reads the token the server
        itself issued rather than inventing one.
        """
        pattern = re.compile(r"combat forfeit confirm (\S+)")
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            found = pattern.search(narrative_log_text(page))
            if found is not None:
                return found.group(1)
            page.wait_for_timeout(100)
        raise AssertionError("the forfeit prompt never printed a confirmation token")

    def _narrative(self, page) -> list[str]:
        """The narrative rows the committed store carries (diagnostics)."""
        state = store_state(page)
        narrative = page.evaluate(
            "() => { const log = document.querySelector('[data-testid=\"message-page\"]')"
            " || document.querySelector('[data-testid=\"message-log\"]');"
            " return log ? log.innerText : ''; }"
        )
        return [
            f"store_keys={sorted(state)}",
            f"narrative={(narrative or '').strip()[-400:]!r}",
        ]

    def _fixture_monster_key(self) -> str:
        """The monster key the SEED created, decided by the runtime's own env.

        The seed process reads the runtime's environment, so the journey must
        read the same source: the test process's ambient environment may carry
        a different catalog mode.
        """
        from web.browser_support.browser_fixtures_data.fixture_values import (
            SHIPPED_SCENE_MONSTER_KEY,
            SYNTH_SCENE_MONSTER_KEY,
        )

        synth = str(self.server.runtime.env.get("ELOSERN_BROWSER_SYNTH_CATALOGS", "0")) == "1"
        return SYNTH_SCENE_MONSTER_KEY if synth else SHIPPED_SCENE_MONSTER_KEY

    def _absolute(self, url: str) -> str:
        """The absolute form of one committed media URL.

        The descriptor carries same-origin (root-relative) URLs while Playwright
        routes and request URLs are absolute, so both routing and request
        counting go through here.
        """
        return url if url.startswith("http") else f"{self.base_url}{url}"

    def _catalog_identity(self, page, role: str | None, subject_prefix: str) -> int:
        """The identity of one admitted catalog member.

        The member is addressed by the facts the panel itself commits — its
        display role (``None`` to accept any) and the subject family its
        descriptor names (``portrait:monster:`` for the present monster, whose
        exploration role is the generic one) — never by a guessed dbref.
        """
        catalog = store_state(page)["panels"]["art"]["portrait_catalog"]
        for identity, entry in catalog.items():
            context_role = (entry.get("context") or {}).get("role")
            subject = (entry.get("artwork") or {}).get("generation_subject") or ""
            if role is not None and context_role != role:
                continue
            if not subject.startswith(subject_prefix):
                continue
            return int(identity)
        raise AssertionError(
            f"no admitted catalog member matches role={role!r} subject={subject_prefix!r}"
        )

    def _talk(self, page) -> None:
        """Open the conversation through the production ``explore.talk_open``.

        The client dispatches exactly the action the dock's 交談 row sends, with
        the host identity the committed catalog admits as the dialogue role, and
        the server's own gates decide: the committed snapshot then carries mode
        ``dialogue``.
        """
        host = self._catalog_identity(page, "對話對象", "portrait:character:")
        page.evaluate(
            "([id]) => window.__elosernBridge.store.dispatchAction('explore.talk_open', { npc_id: id }, null)",
            [host],
        )
        self._wait_mode(page, "dialogue")

    def _leave_dialogue(self, page) -> None:
        """End the conversation through the production leave seam."""
        host = self._catalog_identity(page, "對話對象", "portrait:character:")
        page.evaluate(
            "([id]) => window.__elosernBridge.store.dispatchAction('explore.dialogue_leave', { npc_id: id }, null)",
            [host],
        )
        self._wait_mode(page, "exploration")

    def _engage(self, page) -> None:
        """Engage the present monster through the production engage command.

        ``engage <target>`` is the same text command the combat journeys use;
        the monster is addressed by the fixture's own key, so the server's own
        resolution decides and the committed snapshot carries mode ``combat``.
        """
        page.evaluate(
            "([key]) => Evennia.msg('text', [`engage ${key}`], {})",
            [self._fixture_monster_key()],
        )
        self._wait_mode(page, "combat")


    # --- journeys --------------------------------------------------------

    @covers_requirement(
        "webclient-contextual-hud::the-scene-backdrop-renders-the-art-payload-truthfully-behind-the-stage"
    )
    @covers_requirement(
        "scene-artwork-presentation::retention-is-scoped-to-unchanged-scene-and-generation-subject"
    )
    @covers_requirement(
        "scene-artwork-presentation::full-view-shares-resolved-scene-truth"
    )
    def test_room_precedence_retention_movement_and_fullview(self) -> None:
        page = self.logged_in_page()
        page.on("request", lambda request: self.requests.append(request.url))
        self.responses: list[str] = []
        page.on(
            "response",
            lambda response: self.responses.append(f"{response.status} {response.url}"),
        )

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

        # (2) Same-place mode changes never change the artwork: the real
        # dialogue transition (through the production talk action) and back,
        # then a real engagement into combat — the committed descriptor, and
        # therefore the presented bitmap, stays exactly what it was.
        self._talk(page)
        self.assertEqual(self._displayed(page), room_url)
        self._leave_dialogue(page)
        self.assertEqual(self._displayed(page), room_url)
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
        badge = page.locator(PLACEHOLDER)
        self.assertEqual(
            badge.count(),
            0,
            "a status badge rendered while the retained image is on screen: "
            f"kind={badge.first.get_attribute('data-kind') if badge.count() else None} "
            f"label={badge.first.inner_text() if badge.count() else None} "
            f"displayed={self._displayed(page)}",
        )

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
        # ONE local indication: the retained image stays with the reached
        # failure stated by the caption row, never by a second status badge.
        badge = page.locator(PLACEHOLDER)
        self.assertEqual(
            badge.count(),
            0,
            "a second indication rendered: "
            f"kind={badge.first.get_attribute('data-kind') if badge.count() else None} "
            f"label={badge.first.inner_text() if badge.count() else None} "
            f"displayed={self._displayed(page)} "
            f"layers={page.locator('img[data-role]').evaluate_all('(els) => els.map((e) => e.getAttribute("src"))')} "
            f"mode={store_state(page)['mode']}",
        )
        self.assertTrue(page.locator(FAILURE).inner_text().strip())

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

        # (7) Re-entering the place the character left commits that EXISTING
        # logical identity again: whatever is on screen belongs to its own
        # descriptor, and the identity is the one the browser left. A live
        # engagement forbids movement, so the fight is surrendered first
        # through the production commands: a bare forfeit only returns the
        # party-scope prompt (§6 — nothing mutates without the confirmation),
        # and the token that prompt carries is what settles the session.
        page.evaluate("() => Evennia.msg('text', ['combat forfeit'], {})")
        token = self._wait_surrender_token(page)
        page.evaluate(
            "([token]) => Evennia.msg('text', [`combat forfeit confirm ${token}`], {})",
            [token],
        )
        self._wait_mode(page, "exploration")
        self._transition(page, "reuse_place")
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if self._art(page).get("subject_id") == artwork["subject_id"]:
                break
            page.wait_for_timeout(250)
        else:
            raise AssertionError(
                "re-entering the left place never committed its identity: "
                f"committed={self._art(page).get('subject_id')!r} "
                f"expected={artwork['subject_id']!r} "
                f"mode={store_state(page)['mode']} "
                f"narrative={self._narrative(page)!r}"
            )
        page.wait_for_timeout(800)
        reentered = self._displayed(page)
        if reentered is not None:
            self.assertIn(reentered, self._admitted_urls(page))

        # (8) The full view shares the same displayed resource and failure
        # state, and it closes back to the opener.
        displayed = self._wait_displayed(page)
        caption_label = page.locator('[data-testid="scene-backdrop-label"]').inner_text()
        page.locator(CONTROL).click()
        page.wait_for_selector(FULLVIEW, timeout=15000)
        fullview_image = page.locator('[data-testid="scene-backdrop-fullview-image"]')
        self.assertEqual(fullview_image.get_attribute("src"), displayed)
        self.assertIn(
            caption_label.strip(),
            page.locator(FULLVIEW).inner_text(),
            "the full view names the scene the caption names",
        )
        page.keyboard.press("Escape")
        page.wait_for_selector(FULLVIEW, state="detached", timeout=15000)
        # Escape restores focus to the control that opened the view.
        self.assertEqual(
            page.evaluate(
                "() => (document.activeElement && document.activeElement.getAttribute('data-testid')) || null"
            ),
            "scene-backdrop-control",
        )

    @covers_requirement(
        "webclient-contextual-hud::the-scene-backdrop-renders-the-art-payload-truthfully-behind-the-stage"
    )
    @covers_requirement(
        "scene-artwork-presentation::provisional-backgrounds-never-change-precedence"
    )
    @covers_requirement(
        "scene-artwork-presentation::full-view-shares-resolved-scene-truth"
    )
    def test_provisional_and_terminal_failures_are_reached_once(self) -> None:
        # The routes are installed BEFORE the page loads, on the path families
        # the server serves the chain from, so the very first resolution is the
        # intercepted one. The preferred room override is HELD (the request is
        # left pending and released from the journey body — never by blocking
        # the route handler), the scene's own provisional bundled illustration
        # fails, and every lower position fails too.
        page = self.new_page()
        page.on("request", lambda request: self.requests.append(request.url))
        held: dict[str, object] = {}

        def hold_room(route):
            held["route"] = route

        # A URL glob's `*` does not cross a path separator, so each family is
        # matched with `**` on both sides of the fingerprint segment.
        page.route("**/art/official/**/room/**", hold_room)
        page.route(
            "**/art/bundled-scene/**",
            lambda route: route.fulfill(status=404, content_type="text/plain", body=b"missing"),
        )
        page.route(
            "**/art/scene/**",
            lambda route: route.fulfill(status=404, content_type="text/plain", body=b"missing"),
        )
        page.route(
            "**/art/official/**/scene/**",
            lambda route: route.fulfill(status=404, content_type="text/plain", body=b"missing"),
        )
        from .browser_helpers import login_and_open

        # The preferred source is held, so the document's `load` event cannot
        # complete: the shell readiness check is the journey's gate instead.
        login_and_open(
            page, self.webclient_url, self.base_url, wait_until="domcontentloaded"
        )
        artwork = self._art(page)
        bundled = next(
            entry["resource"]["url"]
            for entry in artwork["attempts"]
            if entry["source_id"].startswith("scene.bundled:")
        )

        # (1) The provisional failure is LATENT: while the preferred source is
        # still in flight nothing is claimed — no error, no badge claiming
        # absence, no image.
        page.wait_for_timeout(1500)
        self.assertEqual(page.locator(FAILURE).count(), 0)
        badge = page.locator(PLACEHOLDER)
        self.assertEqual(
            badge.count(),
            0,
            "a badge rendered while the preferred source is held: "
            f"kind={badge.first.get_attribute('data-kind') if badge.count() else None} "
            f"label={badge.first.inner_text() if badge.count() else None}",
        )
        self.assertEqual(
            page.locator(IMAGE).count(),
            0,
            "an image was presented while every permitted source fails: "
            f"displayed={self._displayed(page)} "
            f"attempts={[(e.get('type'), e.get('rank'), e.get('source_id')) for e in (self._art(page).get('attempts') or [])]} "
            f"layers={page.locator('img[data-role]').evaluate_all('(els) => els.map((e) => e.getAttribute(\"src\"))')}",
        )

        # (2) The preferred room source wins without an unrelated provisional
        # fault: releasing it presents the room image and claims no failure.
        self.assertIn("route", held, "the preferred room source was never requested")
        held["route"].continue_()
        room_url = self._wait_source(page, ROOM_SOURCE, timeout=30000)
        page.wait_for_timeout(600)
        self.assertEqual(page.locator(FAILURE).count(), 0)

        # (3) The lower positions are reached once the override goes away. The
        # generated and operator sources fail, so the chain walks to the
        # already-failed provisional bundled resource — REUSED at its own
        # position, requested exactly once — and then selects the descriptor's
        # DISTINCT terminal image exactly once.
        terminal = artwork["terminal"]["resource"]["url"]
        page.unroute("**/art/bundled-scene/**")
        page.route(self._absolute(terminal), lambda route: route.continue_())
        self._transition(page, "remove_room_binding")
        self._wait_source(page, "scene.terminal:", timeout=30000)
        page.wait_for_timeout(800)
        self.assertEqual(
            sum(1 for url in self.requests if url == self._absolute(bundled)),
            1,
            "the failed provisional resource was requested more than once",
        )
        self.assertEqual(
            sum(1 for url in self.requests if url == self._absolute(terminal)),
            1,
            "the distinct terminal was attempted more than once",
        )
        # The reached lower faults stay visible beside the terminal image, and
        # the full view shares that same state: the same displayed resource and
        # the same reached-failure text, with focus returning to the opener.
        failure_text = page.locator(FAILURE).inner_text().strip()
        self.assertTrue(failure_text)
        self.assertNotEqual(self._art(page)["revision"], artwork["revision"])
        terminal_url = self._displayed(page)
        page.locator(CONTROL).click()
        page.wait_for_selector(FULLVIEW, timeout=15000)
        self.assertEqual(
            page.locator('[data-testid="scene-backdrop-fullview-image"]').get_attribute("src"),
            terminal_url,
        )
        self.assertIn(failure_text, page.locator(FULLVIEW).inner_text())
        page.keyboard.press("Escape")
        page.wait_for_selector(FULLVIEW, state="detached", timeout=15000)
        self.assertEqual(
            page.evaluate(
                "() => (document.activeElement && document.activeElement.getAttribute('data-testid')) || null"
            ),
            "scene-backdrop-control",
        )

        # (4) A move commits a different logical place: the committed
        # descriptor is a new identity, and whatever is on screen belongs to
        # THAT descriptor's own positions — never to the place the browser
        # came from.
        previous_identity = artwork["subject_id"]
        previous_urls = {
            entry["resource"]["url"]
            for entry in artwork["attempts"]
            if entry.get("type") == "image"
        }
        self._transition(page, "move_scene")
        wait_for_store_state(
            page,
            lambda state: (
                (state["panels"]["art"]["scene"]["artwork"] or {}).get("subject_id")
                != previous_identity
            ),
            timeout=30000,
        )
        page.wait_for_timeout(800)
        moved = self._art(page)
        admitted = self._admitted_urls(page)
        displayed_after_move = self._displayed(page)
        if displayed_after_move is not None:
            self.assertIn(
                displayed_after_move,
                admitted,
                "the moved place presented a resource its own descriptor does not name",
            )
        self.assertNotIn(
            moved["subject_id"],
            (previous_identity,),
            "the move did not commit a new logical place",
        )

        # (5) The moved place loaded in a FRESH browser context (no cached
        # media) exhausts: every permitted source fails, so the chain shows ONE
        # labelled non-image condition and never a broken image.
        fresh = self.new_page()
        fresh_requests: list[str] = []
        fresh.on("request", lambda request: fresh_requests.append(request.url))
        for pattern in ("**/art/scene/**", "**/art/official/**/scene/**", "**/art/bundled-scene/**"):
            fresh.route(
                pattern,
                lambda route: route.fulfill(
                    status=404, content_type="text/plain", body=b"missing"
                ),
            )
        login_and_open(fresh, self.webclient_url, self.base_url)
        # The fresh context committed the SAME moved place (a real reused
        # identity) and its own available panel.
        wait_for_store_state(
            fresh,
            lambda state: (
                (state["panels"]["art"]["scene"]["artwork"] or {}).get("subject_id")
                == moved["subject_id"]
            ),
            timeout=30000,
        )
        self.assertTrue(store_state(fresh)["panels"]["art"]["available"])
        self._wait_badge(fresh)
        fresh.wait_for_timeout(1000)
        # Settled exhaustion: nothing presented, no probe still fetching, and
        # the final permitted resource was really attempted (and failed).
        self.assertEqual(fresh.locator(IMAGE).count(), 0)
        self.assertEqual(fresh.locator('img[data-role]').count(), 0)
        self.assertEqual(fresh.locator(PLACEHOLDER).count(), 1)
        self.assertTrue(fresh.locator(PLACEHOLDER_LABEL).inner_text().strip())
        terminal_url = moved["terminal"]["resource"]["url"]
        self.assertIn(self._absolute(terminal_url), fresh_requests)
        fresh.close()
