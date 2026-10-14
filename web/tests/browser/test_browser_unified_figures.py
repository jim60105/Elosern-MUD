"""Every figure surface presents the same admitted descriptor.

Change ``unified-portrait-image-contract`` cut the portrait wire over to the
canonical artwork descriptor (``world.art.descriptors``): the art panel's
catalog value is exactly ``{artwork, context}``, the roster row's ``portrait``
IS the descriptor, and every figure/avatar surface reads that ONE shape
through the shared loading core instead of a per-component copy of flat image
fields.

This managed journey proves the claim on the real client. One committed
exploration snapshot carries the same descriptor for the player's own roster
row, the focused target, the co-located party companion and the presence rail;
each surface renders that descriptor's own candidate URL through the shared
renderer; a later snapshot whose descriptor carries no real candidate leaves
every FIGURE surface on the descriptor's OWN committed alpha terminal (painted
by the shared alpha primitive only after that resource itself loaded, with no
local failure marker, because a fallback is not a failure) while the real-only
avatar medallion draws its identity glyph; and a committed dialogue snapshot
shows the host's standee presenting the SAME descriptor.

It drives the committed panels through the real store and the real client, so
it covers the wire shape, the admission facts and the rendering contract on
every named surface. It does NOT exercise the seeded server-side portrait
producer (the `PORTRAIT_DESCRIPTORS` seed mode) or a source failure
intercepted after server resolution: those live in the seed fixture and in
`test_browser_stage_silhouette`'s route-abort leg respectively.

Everything is deterministic and local: the descriptor payload is injected as a
schema-valid snapshot and the one portrait image is served by a route, so no
remote request and no image service is involved.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    inject_snapshot,
    open_verb_card,
    store_state,
    valid_local_map_panel,
    valid_status_panel,
)
from ._journey_support import (
    _SCENE_PNG_BYTES,
    _combat_panel,
    _artwork_descriptor,
    _artwork_resource,
    _fixture_digest,
    _wait_mode,
)

SCENE_URL = "/art/scene.png"
SHARED_URL = "/art/portrait_shared.png"
TERMINAL_URL = "/art/defaults/man.webp"
STAGE_TRIPLE = {"scale": 1.0, "x": 0.0, "y": 0.0}
FACE_RECT = {"x": 0.25, "y": 0.06, "w": 0.5, "h": 0.5}

STANDEE = '[data-anchor="actor-right"] [data-testid="stage-actor"]:not([inert])'
PLAYER_FIGURE = '[data-anchor="actor-left"] [data-testid="stage-actor"]:not([inert])'
MEDALLION = '[data-anchor="presence"] [data-testid="presence-entry-face"]'
DRAWER_ART = '[data-testid="hud-drawer"] [data-testid="reference-artwork"]'
ALPHA = '[data-testid="artwork-alpha"]'
ALPHA_FILL = '[data-testid="artwork-alpha-fill"]'
FAILURE = '[data-testid="artwork-failure"]'


def _terminal() -> dict:
    """The descriptor's own committed alpha terminal."""
    return {
        "kind": "alpha_mask",
        "source_id": "portrait.alpha:man",
        "rank": 100,
        "resource": {
            "resource_id": "defaults/man.webp",
            "version": _fixture_digest("terminal-man"),
            "url": TERMINAL_URL,
            "origin": "silhouette",
            "geometry": {
                "image_size": None,
                "face_rect": {"x": 0.35, "y": 0.03, "w": 0.29, "h": 0.16},
                "stage": None,
                "aspect_ratio": "3:4",
            },
        },
    }


def _shared_descriptor(subject_id: str, *, with_candidate: bool = True) -> dict:
    """The one descriptor every surface of this journey is handed."""
    descriptor = _artwork_descriptor(subject_id, SHARED_URL, terminal=_terminal())
    descriptor["attempts"][0]["resource"]["geometry"] = {
        "image_size": None,
        "face_rect": dict(FACE_RECT),
        "stage": dict(STAGE_TRIPLE),
        "aspect_ratio": "3:4",
    }
    if not with_candidate:
        descriptor["generation_state"] = "missing"
        descriptor["attempts"] = []
    return descriptor


def _art_panel(*, with_candidate: bool = True) -> dict:
    return {
        "schema_version": 3,
        "available": True,
        "kind": "scene",
        "scene": {
            "archetype": None,
            "label": "南門街道",
            "subject_key": None,
            "status": "done",
            "url": SCENE_URL,
            "aspect_ratio": "16:9",
            "alt": "當前場景",
            "placeholder": None,
            "stage": dict(STAGE_TRIPLE),
        },
        "portrait_catalog": {
            "7": {
                "artwork": _shared_descriptor("npc_7", with_candidate=with_candidate),
                "context": {"name": "店長", "role": "對話對象"},
            },
            # A second admitted subject outside the party lineup: focusing it
            # raises the actor-right standee instead of elevating a lineup
            # figure, so the journey covers both figure paths.
            "8": {
                "artwork": _shared_descriptor("npc_8", with_candidate=with_candidate),
                "context": {"name": "旅人", "role": "人物"},
            },
        },
    }


def _exploration_panel() -> dict:
    return {
        "schema_version": 4,
        "available": True,
        "kind": "exploration",
        "move": [],
        "character": {"available": True},
        "quests": {"available": True},
        "inventory": {"available": True},
        "look": {
            "room": {"identity": 42, "display_name": "南門街道", "room": True},
            "entities": [
                {"identity": 7, "display_name": "店長", "kind": "npc", "portrait_ref": "7"},
                {"identity": 8, "display_name": "旅人", "kind": "character", "portrait_ref": "8"},
            ],
            "objects": [],
        },
        "interact": [
            {
                "identity": 7,
                "display_name": "店長",
                "portrait_ref": "7",
                "affordances": [
                    {
                        "kind": "action",
                        "action_id": "explore.talk_open",
                        "label": "交談",
                        "enabled": True,
                        "disabled_reason": None,
                    }
                ],
            },
            {
                "identity": 8,
                "display_name": "旅人",
                "portrait_ref": "8",
                "affordances": [
                    {
                        "kind": "action",
                        "action_id": "explore.talk_open",
                        "label": "交談",
                        "enabled": True,
                        "disabled_reason": None,
                    }
                ],
            },
        ],
    }


def _roster_panel(*, with_candidate: bool = True) -> dict:
    return {
        "schema_version": 3,
        "available": True,
        "characters": [
            {
                "identity": 1,
                "name": "測試主角",
                "current": True,
                "pending": False,
                "portrait": _shared_descriptor("portrait:character:1", with_candidate=with_candidate),
            }
        ],
        "can_create": False,
        "max_characters": 3,
        "switch_locked": False,
        "lock_reason": None,
    }


def _party_panel() -> dict:
    return {
        "schema_version": 2,
        "available": True,
        "general_quota": {"used": 1, "limit": 4},
        "slots": [
            {
                "identity": 7,
                "display_name": "店長",
                "portrait_ref": "7",
                "hp_current": 100,
                "hp_maximum": 100,
                "bond_stage": "熟識",
                "membership": {"general": True, "temporary_commissions": []},
            }
        ],
    }


class UnifiedFiguresBrowserTest(BrowserAcceptanceTest):
    """Every figure/avatar surface renders the ONE admitted descriptor."""

    def _serve_media(self, page, include_portrait: bool = True) -> None:
        """Fulfil the scene (and, unless the caller routes it itself, the portrait)."""
        urls = (SCENE_URL, SHARED_URL) if include_portrait else (SCENE_URL,)
        for url in urls:
            page.route(
                f"**{url}",
                lambda route: route.fulfill(
                    status=200, content_type="image/png", body=_SCENE_PNG_BYTES
                ),
            )

    def _commit(self, page, *, with_candidate: bool = True) -> None:
        inject_snapshot(
            page,
            {
                "status": valid_status_panel("測試主角", "1"),
                "local_map": valid_local_map_panel(),
                "exploration": _exploration_panel(),
                "art": _art_panel(with_candidate=with_candidate),
                "roster": _roster_panel(with_candidate=with_candidate),
                "party": _party_panel(),
            },
            mode="exploration",
        )

    @staticmethod
    def _image_src(page, selector: str) -> str:
        return page.evaluate(
            "(sel) => { const el = document.querySelector(sel);"
            " if (!el) return null;"
            " return el.tagName === 'IMG' ? el.getAttribute('src')"
            " : (el.querySelector('img')?.getAttribute('src') ?? null); }",
            selector,
        )

    @staticmethod
    def _mask_url(page, selector: str) -> str | None:
        return page.evaluate(
            "(sel) => { const fill = document.querySelector(sel);"
            " return fill ? fill.style.getPropertyValue('--artwork-alpha-mask') : null; }",
            selector,
        )

    @covers_requirement(
        "webclient-art-panel::the-reference-artwork-frame-presents-a-portrait-entry-truthfully-through-cover-fit-and-rect-crop"
    )
    @covers_requirement(
        "webclient-character-roster::roster-portraits-resolve-through-the-named-portrait-subject-mechanism"
    )
    @covers_requirement(
        "webclient-party-panel::the-party-panel-is-an-exact-read-only-version-2-presentation-panel"
    )
    def test_exploration_dialogue_combat_and_drawer_share_descriptor(self):
        """One descriptor, every surface: the player's roster figure, the
        focused target's standee, the presence medallion, the party drawer row
        and the drawer art slot all present the SAME descriptor's candidate,
        and when that candidate disappears they all fall back to the
        descriptor's own committed alpha terminal rather than to a per-surface
        copy of the old flat fields or to a solid rectangle."""
        page = self.logged_in_page((1451, 790), "off")
        self._serve_media(page)
        self._commit(page)
        _wait_mode(page, "exploration")
        # Focus the admitted target so the actor-right standee stands, then
        # open the status drawer so its art slot renders the roster figure too.
        page.wait_for_selector('[data-anchor="presence"] [data-entry-key="target-8"]', timeout=15000)
        open_verb_card(page, 8)
        page.wait_for_selector(STANDEE, timeout=15000)
        page.evaluate(
            "() => window.__elosernBridge.store.openHudDrawer('status')"
        )
        page.wait_for_selector(
            '[data-testid="hud-drawer"][data-drawer-key="status"] [data-testid="reference-artwork"]',
            timeout=15000,
        )

        # The committed wire shape is the canonical one: the catalog value is
        # exactly {artwork, context} and the roster portrait is the descriptor.
        panels = store_state(page)["panels"]
        state = {
            "entryKeys": sorted(panels["art"]["portrait_catalog"]["7"]),
            "candidate": panels["art"]["portrait_catalog"]["7"]["artwork"]["attempts"][0]["resource"]["url"],
            "terminal": panels["art"]["portrait_catalog"]["7"]["artwork"]["terminal"]["resource"]["url"],
            "rosterPortraitKeys": sorted(panels["roster"]["characters"][0]["portrait"]),
            "partyRef": panels["party"]["slots"][0]["portrait_ref"],
            "interactRef": panels["exploration"]["interact"][0]["portrait_ref"],
        }
        self.assertEqual(state["entryKeys"], ["artwork", "context"])
        self.assertEqual(state["candidate"], SHARED_URL)
        self.assertEqual(state["terminal"], TERMINAL_URL)
        self.assertEqual(
            state["rosterPortraitKeys"],
            [
                "attempts",
                "generation_state",
                "generation_subject",
                "retention_sources",
                "revision",
                "subject_id",
                "terminal",
            ],
        )
        self.assertEqual(state["partyRef"], "7")
        self.assertEqual(state["interactRef"], "7")

        # Every figure surface presents the descriptor's own candidate.
        page.wait_for_selector(f'{STANDEE} img[src$="{SHARED_URL}"]', timeout=15000)
        self.assertEqual(self._image_src(page, PLAYER_FIGURE), SHARED_URL)
        self.assertEqual(self._image_src(page, MEDALLION), SHARED_URL)
        self.assertEqual(self._image_src(page, DRAWER_ART), SHARED_URL)
        self.assertEqual(page.locator(f"{STANDEE} {ALPHA}").count(), 0, "a real image stands alone")

        # The candidate disappears from the committed descriptor: every surface
        # falls back to the descriptor's OWN alpha terminal — painted by the
        # shared primitive, from the terminal's own URL, with no local failure
        # marker, because a committed fallback is not a failure.
        self._commit(page, with_candidate=False)
        # The FIGURE surfaces paint the descriptor's own committed alpha
        # terminal, only after that same resource loaded.
        page.wait_for_selector(f"{STANDEE} {ALPHA_FILL}", timeout=15000)
        page.wait_for_selector(f"{PLAYER_FIGURE} {ALPHA_FILL}", timeout=15000)
        page.wait_for_selector(f"{DRAWER_ART} {ALPHA_FILL}", timeout=15000)
        for surface in (STANDEE, PLAYER_FIGURE, DRAWER_ART):
            with self.subTest(surface=surface):
                self.assertEqual(
                    self._mask_url(page, f"{surface} {ALPHA_FILL}"),
                    f"url('{TERMINAL_URL}')",
                )
                self.assertEqual(page.locator(f"{surface} {FAILURE}").count(), 0)
        # The AVATAR position is real-only: a silhouette is not an avatar, so
        # the medallion draws its identity glyph instead of the terminal.
        page.wait_for_selector(
            "[data-anchor='presence'] [data-testid='presence-entry-initial']",
            state="attached",
            timeout=15000,
        )
        self.assertEqual(self._image_src(page, MEDALLION), None)
        self.assertEqual(page.locator(f"[data-anchor='presence'] {ALPHA}").count(), 0)
        self.assertEqual(page.locator(f"[data-anchor='presence'] {FAILURE}").count(), 0)

        # The DIALOGUE join reads the same descriptor: the host's reference
        # names the same catalog entry, and the actor-right standee presents it.
        page.close()
        page = self.logged_in_page((1451, 790), "off")
        self._serve_media(page)
        inject_snapshot(
            page,
            {
                "status": valid_status_panel("測試主角", "1"),
                "local_map": valid_local_map_panel(),
                "art": _art_panel(),
                "dialogue": {
                    "schema_version": 2,
                    "available": True,
                    "kind": "dialogue",
                    "host": {"identity": 7, "display_name": "店長", "portrait_ref": "7"},
                    "bond_stage": "熟識",
                    "line": "又見面了。今晚爐火正旺。",
                    "choices": [{"keyword_id": "news", "label": "最近有什麼消息？"}],
                },
            },
            mode="dialogue",
        )
        _wait_mode(page, "dialogue")
        page.wait_for_selector(f'{STANDEE} img[src$="{SHARED_URL}"]', timeout=15000)
        self.assertEqual(self._image_src(page, STANDEE), SHARED_URL)
        self.assertEqual(page.locator(f"{STANDEE} {ALPHA}").count(), 0)
        page.close()

        # The COMBAT join reads the same descriptor: the participant row's
        # committed reference names the same catalog entry, and the row's
        # real-only avatar position presents it.
        page = self.logged_in_page((1451, 790), "off")
        self._serve_media(page)
        self._commit(page)
        _wait_mode(page, "exploration")
        # The combat panel is the family's own schema-valid fixture; its first
        # participant's committed reference is rebound to the shared descriptor
        # so the row and the exploration surfaces name ONE catalog entry.
        combat_art = _art_panel()
        combat_art["portrait_catalog"]["1"] = _art_panel()["portrait_catalog"]["7"]
        inject_snapshot(
            page,
            {
                "status": valid_status_panel("測試主角", "1"),
                "local_map": valid_local_map_panel(),
                "art": combat_art,
                "context_actions": _combat_panel(),
            },
            mode="combat",
        )
        _wait_mode(page, "combat")
        page.wait_for_selector(
            '[data-testid="participant-frame"] [data-testid="reference-artwork"]',
            timeout=15000,
        )
        self.assertEqual(
            self._image_src(page, '[data-testid="participant-frame"]'),
            SHARED_URL,
            "the combat row presents the same admitted descriptor",
        )
        page.close()

        # A SOURCE ERROR injected after server resolution: the server already
        # resolved and committed the descriptor, and the browser's own request
        # for that exact resource fails. Every figure steps past the failed
        # candidate to the descriptor's own committed alpha terminal, keeps the
        # persistent local marker, shows no broken image, and leaves the
        # recorded generation truth untouched.
        page = self.logged_in_page((1451, 790), "off")
        page.route(f"**{SHARED_URL}", lambda route: route.abort("failed"))
        self._serve_media(page, include_portrait=False)
        self._commit(page)
        _wait_mode(page, "exploration")
        page.wait_for_selector('[data-anchor="presence"] [data-entry-key="target-8"]', timeout=15000)
        open_verb_card(page, 8)
        page.wait_for_selector(f"{STANDEE} {ALPHA_FILL}", timeout=15000)
        self.assertEqual(
            self._mask_url(page, f"{STANDEE} {ALPHA_FILL}"),
            f"url('{TERMINAL_URL}')",
            "the figure falls back to the descriptor's own terminal",
        )
        self.assertEqual(
            page.locator(f"{STANDEE} {FAILURE}").count(),
            1,
            "the reached fault keeps its persistent local marker",
        )
        self.assertEqual(
            self._image_src(page, f'{STANDEE} img:not([src$="{TERMINAL_URL}"])'),
            None,
            "no broken image element stands in for the figure",
        )
        after = store_state(page)["panels"]
        self.assertEqual(
            after["art"]["portrait_catalog"]["7"]["artwork"]["generation_state"],
            "done",
            "the recorded generation truth is unchanged by a browser failure",
        )
        page.close()
