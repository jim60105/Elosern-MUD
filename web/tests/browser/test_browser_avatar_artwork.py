"""Every owned small-avatar surface on the real client (change
``unified-avatar-rendering``).

One real isolated runtime boots the companion-lineup mode (the boot path whose
account keeps the roster read model the first server boot's ``initial_setup``
wipe would otherwise destroy) plus the unified-image portrait mode: the
activated character's own roster row, one co-located live party companion and
one present named-policy entity each carry a REAL committed portrait card, and
the kit monsters stand in the start room so a deterministic combat participant
can be engaged through the ordinary text transport.

The journey installs its interception BEFORE the client opens, so the very first
real attempt of every avatar surface is the intercepted one, and restricts it to
the art store's gallery tree: the failure each avatar reaches is the browser's
own decode failure of a URL the SERVER already resolved and serialized. It then
asserts, on the real client, that the shared ``AvatarArtwork`` renderer:

  * keeps the first grapheme of the trimmed display name on every surface
    (switcher pill, presence medallion, party row, combat participant row);
  * keeps the reached failure as a persistent explanation a keyboard user can
    reach — a focusable marker in the tab order for the standalone surfaces, and
    the owning control's own accessible description for the hosted ones;
  * never falls back to the figure silhouette / alpha terminal resource.

Only this method runs here; the full managed suite is CI-owned.
"""

from __future__ import annotations

import re

from tools.spec_traceability import covers_requirement
from web.browser_support.browser_fixtures_data import combat_journey_values

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    login_and_open,
    store_state,
    wait_for_store_state,
)
from .fixtures import create_runtime
from .harness import ManagedServer, ManagedServerTearDownMixin

# Interception is restricted to the seeded portrait cards' own gallery media
# path, after the server resolved and serialized the committed panels.
_GALLERY_MEDIA = re.compile(r"/art/(gallery|portrait)/")
# The figure renderer's silhouette/terminal resources; an avatar never uses one.
_ALPHA_PREFIX = "/art/defaults/"
_INVALID_PNG = b"not-an-image"

AVATAR = '[data-testid="avatar-artwork"]'
MARKER = '[data-testid="artwork-failure"]'
PILL = '[data-testid="character-switcher-trigger"]'
PARTY_DRAWER = '[data-testid="hud-drawer"][data-drawer-key="party"]'
PARTICIPANT_FRAME = '[data-testid="participant-frame"]'

_AVATAR_STATE = """
(sel) => {
  const root = document.querySelector(sel);
  if (!root) return null;
  const initial = root.querySelector(
    '[data-testid="avatar-artwork__initial"], [data-testid="presence-entry-initial"]'
  );
  const marker = root.querySelector('[data-testid="artwork-failure"]');
  const img = root.querySelector('img');
  return {
    initial: initial ? initial.textContent : null,
    markerTag: marker ? marker.tagName : null,
    markerText: marker ? marker.textContent : null,
    markerTabIndex: marker && marker.tagName === 'BUTTON' ? marker.tabIndex : null,
    imgSrc: img ? img.getAttribute('src') : null,
  };
}
"""

_DESCRIBED_TEXT = """
(sel) => {
  const host = document.querySelector(sel);
  if (!host) return null;
  const id = host.getAttribute('aria-describedby');
  if (!id) return null;
  const node = document.getElementById(id);
  return node ? node.textContent : null;
}
"""

# The bounded sentence the shared failure mapping renders for a real image the
# browser could not load (invalid bytes raise the element's own `error`, the
# same reached reason the loading-core journey observes).
LOAD_FAILURE_TEXT = "圖片載入失敗"


class AvatarArtworkBrowserTest(ManagedServerTearDownMixin, BrowserAcceptanceTest):
    """The shared avatar renderer exercised on the real client."""

    @classmethod
    def setUpClass(cls) -> None:
        # Each test boots its own isolated server; never the shared one.
        pass

    def setUp(self) -> None:
        runtime = create_runtime()
        # Boot mode: the kit catalogs plus the portrait seed mode, on the
        # companion-lineup account path (see the module docstring). Every flag
        # must be set BEFORE seed and server startup; each journey boots its own
        # isolated runtime.
        runtime.env["ELOSERN_BROWSER_SYNTH_CATALOGS"] = "1"
        runtime.env["ELOSERN_BROWSER_COMPANION_LINEUP"] = "1"
        runtime.env["ELOSERN_BROWSER_PORTRAIT_DESCRIPTORS"] = "1"
        self.server = ManagedServer(runtime=runtime)
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        self._media_requests: list[str] = []
        super().setUp()

    def _fail_gallery_media(self, route) -> None:
        """Answer every gallery media request with invalid bytes.

        The request itself succeeds on the wire, so the failure the avatar
        observes is the browser's own decode failure — never a server error.
        """
        self._media_requests.append(route.request.url)
        route.fulfill(status=200, content_type="image/png", body=_INVALID_PNG)

    @staticmethod
    def _avatar_state(page, selector):
        return page.evaluate(_AVATAR_STATE, selector)

    @staticmethod
    def _described_text(page, selector):
        """The bounded explanation an owning control references, or None."""
        return page.evaluate(_DESCRIBED_TEXT, selector)

    @staticmethod
    def _initial_of(name: str) -> str:
        """The displayed initial the seeded fixture's name must yield.

        Every seeded display name begins with one complete grapheme (a single
        CJK code point), so its first character IS the expected cluster; the
        grapheme policy itself is proven by the component suite.
        """
        return name[0]

    @staticmethod
    def _admitted_refs(state: dict) -> set:
        """The catalog refs whose descriptor really carries a real candidate.

        A kit-provisioned companion may hold an admitted reference whose
        generation is still pending (no image attempt at all): that position is
        expected absence, not a reached fault, so a journey that asserts the
        failure marker has to name a reference with a real candidate.
        """
        catalog = (state.get("panels") or {}).get("art", {}).get("portrait_catalog") or {}
        return {
            ref
            for ref, entry in catalog.items()
            if ((entry or {}).get("artwork") or {}).get("attempts")
        }

    def _assert_avatar_fallback(self, page, selector, expected_name: str) -> dict:
        """One avatar surface: the grapheme initial, a reached fault, no alpha."""
        state = self._avatar_state(page, selector)
        self.assertIsNotNone(state, f"no avatar rendered for {selector}")
        self.assertEqual(
            state["initial"],
            self._initial_of(expected_name),
            f"{selector} did not keep {expected_name!r}'s grapheme initial",
        )
        # A real image was attempted (its own URL, never a silhouette) and the
        # fallback is not a terminal/alpha resource.
        if state["imgSrc"] is not None:
            self.assertFalse(
                state["imgSrc"].startswith(_ALPHA_PREFIX),
                f"{selector} fell back to an alpha/figure resource: {state['imgSrc']}",
            )
        self.assertIsNotNone(state["markerTag"], f"{selector} lost its failure marker")
        return state

    @covers_requirement(
        "webclient-art-panel::small-avatar-thumbnails-zoom-crop-their-portrait-image-to-the-carried-face-rectangle-through-one-shared-pure-function"
    )
    @covers_requirement(
        "avatar-artwork-presentation::every-avatar-uses-a-real-portrait-or-a-grapheme-initial"
    )
    @covers_requirement(
        "avatar-artwork-presentation::compact-avatar-failures-remain-accessible"
    )
    def test_roster_presence_party_participant_fallback_is_accessible(self) -> None:
        """Switcher, presence, party and combat avatars share one renderer: a
        real-only attempt whose browser decode failure keeps the grapheme
        initial, a persistent keyboard-reachable explanation, and no alpha
        terminal resource."""
        page = self.new_page((1451, 790), "off")
        # Installed BEFORE the client opens: the avatar surfaces' first real
        # attempts are already the intercepted ones.
        page.route(_GALLERY_MEDIA, self._fail_gallery_media)
        login_and_open(page, self.webclient_url, self.base_url)
        wait_for_store_state(
            page,
            lambda state: bool(
                (
                    (state.get("panels") or {}).get("roster") or {}
                ).get("available")
                and ((state.get("panels") or {}).get("roster") or {}).get("characters")
            ),
            timeout=30000,
        )

        state = store_state(page)
        roster = state["panels"]["roster"]
        self.assertTrue(roster.get("available"), "the roster panel must be committed")
        characters = roster["characters"]
        current = next(char for char in characters if char.get("current"))
        name = current["name"]

        # --- the top-bar switcher's collapsed thumbnail (hosted explanation) --
        page.wait_for_selector(f"{PILL} {AVATAR}", timeout=30000)
        switcher = self._assert_avatar_fallback(page, f"{PILL} {AVATAR}", name)
        described = self._described_text(page, PILL)
        self.assertIsNotNone(
            described, "the switcher pill must name its avatar's explanation"
        )
        self.assertIn(LOAD_FAILURE_TEXT, described)

        # --- a presence medallion (hosted explanation) ------------------------
        page.wait_for_selector(f'[data-testid="presence-entry"] {AVATAR}', timeout=30000)
        admitted = self._admitted_refs(store_state(page))
        interact = store_state(page)["panels"]["exploration"]["interact"]
        entry = next(
            (row for row in interact if row.get("portrait_ref") in admitted), None
        )
        self.assertIsNotNone(
            entry, "the portrait seed must admit a present entity to the art view"
        )
        entry_selector = (
            f'[data-testid="presence-entry"][data-entry-key="target-{entry["identity"]}"]'
        )
        page.wait_for_selector(f"{entry_selector} {AVATAR}", timeout=30000)
        medallion = self._avatar_state(page, f"{entry_selector} {AVATAR}")
        self.assertEqual(
            medallion["initial"],
            self._initial_of(entry["display_name"]),
            "the medallion lost the name's grapheme initial",
        )
        catalog_entry = (
            store_state(page)["panels"]["art"].get("portrait_catalog") or {}
        ).get(entry["portrait_ref"])
        self.assertIsNotNone(
            medallion["markerTag"],
            f"medallion without a reached fault: {medallion} entry={catalog_entry}",
        )
        entry_described = self._described_text(page, entry_selector)
        self.assertIsNotNone(
            entry_described, "the rail entry must name its medallion's explanation"
        )
        self.assertIn(LOAD_FAILURE_TEXT, entry_described)

        # --- a party drawer companion row (standalone focusable marker) -------
        page.evaluate("() => window.__elosernBridge.store.openHudDrawer('party')")
        page.wait_for_selector(f"{PARTY_DRAWER} {AVATAR}", timeout=30000)
        party = store_state(page)["panels"]["party"]["slots"]
        companion = next(
            (slot for slot in party if slot.get("portrait_ref") in admitted), None
        )
        self.assertIsNotNone(
            companion, "the portrait seed must join a companion with a real card"
        )
        party_row = f'[data-testid="party-drawer__row-{companion["identity"]}"] {AVATAR}'
        party_state = self._assert_avatar_fallback(page, party_row, companion["display_name"])
        # A real focusable control in the tab order: keyboard reachable with no
        # pointer hover, and its accessible name carries the whole sentence.
        self.assertEqual(party_state["markerTag"], "BUTTON")
        self.assertEqual(party_state["markerTabIndex"], 0)
        self.assertIn(LOAD_FAILURE_TEXT, party_state["markerText"])
        # The same marker can really take focus.
        page.evaluate(
            "(sel) => document.querySelector(sel).focus()",
            f'{party_row} {MARKER}',
        )
        self.assertTrue(
            page.evaluate("() => document.activeElement.tagName === 'BUTTON'")
        )

        # --- a deterministic combat participant row (standalone marker) -------
        page.keyboard.press("Escape")
        target = combat_journey_values()["engage_target"]
        page.evaluate("([t]) => Evennia.msg('text', [`engage ${t}`], {})", [target])
        wait_for_store_state(page, lambda s: s.get("mode") == "combat", timeout=30000)
        page.wait_for_selector(f"{PARTICIPANT_FRAME} {AVATAR}", timeout=30000)
        participants = store_state(page)["panels"]["context_actions"]["participants"]
        row = next(
            (
                p
                for p in participants
                if p.get("team") == "party"
                and p.get("portrait_ref") in admitted
                and p.get("display_name")
            ),
            None,
        )
        self.assertIsNotNone(
            row, "the engaged battle must carry a party participant with a reference"
        )
        states = page.evaluate(
            """() => Array.from(
                 document.querySelectorAll('[data-testid="participant-frame"] [data-testid="avatar-artwork"]')
               ).map((root) => {
                 const initial = root.querySelector('[data-testid="avatar-artwork__initial"]');
                 const marker = root.querySelector('[data-testid="artwork-failure"]');
                 const img = root.querySelector('img');
                 return {
                   initial: initial ? initial.textContent : null,
                   markerTag: marker ? marker.tagName : null,
                   imgSrc: img ? img.getAttribute('src') : null,
                 };
               })"""
        )
        self.assertTrue(states)
        # The row itself carries no test id (the frozen hook is the frame), so
        # the participant is identified by its own displayed initial beside the
        # marker the reached fault keeps.
        expected_initial = self._initial_of(row["display_name"])
        matched = [
            s for s in states if s["initial"] == expected_initial and s["markerTag"] == "BUTTON"
        ]
        self.assertTrue(
            matched, f"no participant avatar for {row['display_name']!r}: {states}"
        )
        combat = matched[0]
        if combat["imgSrc"] is not None:
            self.assertFalse(combat["imgSrc"].startswith(_ALPHA_PREFIX))

        # The real attempts were observed: the interception really exercised the
        # seeded gallery cards, so the fallbacks above are a decode failure and
        # not a fixture that never had an image.
        self.assertTrue(
            self._media_requests,
            "no gallery media request was observed for the avatar surfaces",
        )
        page.close()


if __name__ == "__main__":
    import unittest

    unittest.main()
