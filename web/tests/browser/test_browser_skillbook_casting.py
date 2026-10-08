"""SkillBook graphical skill use (skillbook-authoritative-casting): live-client journeys.

Isolated localhost managed servers with every external service blocked. The
read-only journeys (book hierarchy and geometry at both acceptance viewports,
preview disclosure, cancel/back, tampered payloads) share the managed server;
the journeys that actually cast — and therefore spend resources, advance the
clock, or start a fight — each boot a dedicated server, exactly like the
combat-menu journeys.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

import os
import time

from web.browser_support.browser_fixtures_data import combat_journey_values
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    install_outbound_recorder,
    outbound_messages,
    sent_action_count,
    store_state,
)
from .harness import ManagedServerTearDownMixin

# Optional evidence captures for manual review (unset in CI).
SHOTS = os.environ.get("ELOSERN_SKILLBOOK_SHOTS", "")

# Kit roles (the browser fixture character's grant set).
UTILITY_SINGLE = "t_cinder_cleave"
SELF_BUFF = "t_moss_veil"
NONE_BREATH = "t_cinder_breath"


class _SkillBookJourney:
    def _shot(self, page, name):
        if SHOTS:
            page.screenshot(path=f"{SHOTS}/{name}.png")

    def _press(self, page, key, wait=80):
        page.keyboard.press(key)
        page.wait_for_timeout(wait)

    def _open_book(self, page):
        page.evaluate("() => window.__elosernBridge.store.openHudDrawer('skill')")
        page.wait_for_selector('[data-testid="skill-book"]', timeout=15000)

    def _select_by_search(self, page, label):
        """Keyboard-only: `/` → search → ↓ into the tree → Enter to the actions."""
        self._press(page, "/")
        page.keyboard.type(label)
        page.wait_for_timeout(120)
        self._press(page, "ArrowDown")
        self._press(page, "Enter")

    def _skill_label(self, page, key):
        character = store_state(page)["panels"]["character"]
        for category in character["actives"]:
            for group in category["groups"]:
                for row in group["skills"]:
                    if row["key"] == key:
                        return row["label"]
        raise AssertionError(f"{key} is not an owned active skill")

    def _wait(self, page, predicate, what, timeout=30.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            state = store_state(page)
            if predicate(state):
                return state
            page.wait_for_timeout(150)
        raise AssertionError(f"timed out waiting for {what}")

    def _wait_flow(self, page, skill_key):
        return self._wait(
            page,
            lambda s: (s.get("skillUse") or {}).get("skillKey") == skill_key
            and not s.get("dispatch", {}).get("inFlight"),
            f"the dock-owned flow for {skill_key}",
        )

    def _wait_idle(self, page):
        return self._wait(page, lambda s: not s.get("dispatch", {}).get("inFlight"), "the dispatch lock")

    def _actions(self, page, action_id):
        return [
            args[0]
            for cmd, args, _kwargs in outbound_messages(page)
            if cmd == "ui_action" and args and args[0].get("action_id") == action_id
        ]

    def _focused_key(self, page):
        return store_state(page)["focus"]["key"]

    def _focus_dock_key(self, page, predicate, limit=16):
        for _ in range(limit):
            if predicate(self._focused_key(page) or ""):
                return
            self._press(page, "ArrowDown")
        raise AssertionError("no dock row matched while walking down")


class SkillBookCastingBrowserTest(_SkillBookJourney, BrowserAcceptanceTest):
    """Read-only SkillBook journeys on the shared managed server."""

    @covers_requirement("webclient-skillbook-casting::skillbook-redesign-is-apply-owned-and-availability-is-truthful")
    def test_book_hierarchy_geometry_and_focus_at_both_viewports(self):
        for viewport in ((1451, 790), (2560, 1440)):
            with self.subTest(viewport=viewport):
                page = self.logged_in_page(viewport)
                self._open_book(page)
                page.wait_for_timeout(200)
                self._shot(page, f"book-{viewport[0]}")
                geometry = page.evaluate(
                    """() => {
                      const r = (sel) => { const el = document.querySelector(sel); return el ? el.getBoundingClientRect().toJSON() : null; };
                      const body = document.querySelector('.skill-book');
                      return {
                        drawer: r('[data-testid="hud-drawer"]'),
                        list: r('.skill-book__list'),
                        detail: r('[data-testid="skill-book__detail"]'),
                        use: r('[data-testid="skill-book__use"]'),
                        practice: r('[data-testid="skill-book__practice"]'),
                        overflowX: body.scrollWidth - body.clientWidth,
                        footer: !!document.querySelector('[data-testid="skill-book-cast-hint"]'),
                        hint: (document.querySelector('[data-testid="skill-book-key-hint"]') || {}).textContent || '',
                        combatBadge: /\\bcombat\\b/.test(body.textContent),
                        chevronMs: getComputedStyle(document.querySelector('.skill-book__category-chevron')).transitionDuration,
                      };
                    }"""
                )
                drawer, list_, detail = geometry["drawer"], geometry["list"], geometry["detail"]
                self.assertLessEqual(geometry["overflowX"], 1, "the book must not scroll horizontally")
                # Master–detail: the card sits beside the list, inside the drawer.
                self.assertLessEqual(list_["right"], detail["left"])
                self.assertGreaterEqual(detail["left"], drawer["left"])
                self.assertLessEqual(detail["right"], drawer["right"])
                # The two actions sit side by side inside the card, never overlapping.
                self.assertLessEqual(geometry["use"]["right"], geometry["practice"]["left"])
                self.assertLessEqual(geometry["practice"]["right"], detail["right"])
                self.assertFalse(geometry["footer"], "the retired cast-syntax footer must be gone")
                self.assertIn("Enter 前往動作", geometry["hint"])
                self.assertFalse(geometry["combatBadge"], "no literal `combat` badge")
                # The suite runs at the `off` motion level: no transition plays.
                self.assertIn(geometry["chevronMs"], ("0s", "0ms"))
                # Keyboard: the tree holds a single tab stop and Enter goes to 施放.
                page.locator('[data-testid="skill-book__tree"] [tabindex="0"]').focus()
                self._press(page, "Enter")
                active = page.evaluate("() => document.activeElement.getAttribute('data-testid')")
                self.assertIn(active, ("skill-book__use", "skill-book__practice"))
                ring = page.evaluate("() => getComputedStyle(document.activeElement).boxShadow")
                self.assertNotEqual(ring, "none", "the focused action carries a visible focus ring")

    @covers_requirement("webclient-skillbook-casting::skillbook-use-shares-one-keyboard-owner-and-preserves-practice")
    def test_cancel_back_returns_to_the_book_without_casting(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._open_book(page)
        self._select_by_search(page, self._skill_label(page, UTILITY_SINGLE))
        self.assertEqual(page.evaluate("() => document.activeElement.getAttribute('data-testid')"), "skill-book__use")
        self._press(page, "Enter")
        self._wait_flow(page, UTILITY_SINGLE)
        page.wait_for_selector('[data-testid="skill-use-dock"]', timeout=15000)
        page.wait_for_timeout(150)
        self.assertTrue(
            page.evaluate("() => document.activeElement && document.activeElement.id === 'action-dock'"),
            "the dock owns focus once the book hands over",
        )
        self.assertEqual(page.locator('[data-testid="hud-drawer-scrim"]').count(), 0)
        # Navigate, then back out.
        self._press(page, "ArrowDown")
        self._press(page, "Escape")
        page.wait_for_selector('[data-testid="skill-book"]', timeout=15000)
        page.wait_for_timeout(200)
        self.assertEqual(
            page.evaluate("() => document.activeElement.getAttribute('data-testid')"),
            "skill-book__use",
        )
        selected = page.locator('[data-testid="skill-book__skill"][aria-selected="true"]').get_attribute("data-key")
        self.assertEqual(selected, UTILITY_SINGLE)
        self.assertEqual(len(self._actions(page, "explore.cast")), 0)
        self.assertEqual(len(self._actions(page, "explore.skill_preview")), 1)
        self.assertEqual(sent_action_count(page), 1, "only the read-only preview was sent")

    def test_monster_openings_disclose_the_whole_line_up(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        ladder = combat_journey_values()["ladder_key"]
        self._open_book(page)
        self._select_by_search(page, self._skill_label(page, ladder))
        self._press(page, "Enter")
        state = self._wait_flow(page, ladder)
        panel = state["panels"]["skill_use"]
        openings = panel["skill"]["openings"]
        self.assertGreaterEqual(len(openings), 2)
        line_up = sorted(row["identity"] for row in openings)
        for row in openings:
            self.assertEqual(sorted(row["target_ids"]), line_up)
            self.assertIn("全體開戰", row["label"])
        # A damaging AREA skill offers no ordinary target, only an explanation.
        keys = [item["key"] for item in state["combatMenu"]["items"]]
        self.assertIn("targets-damage-only", keys)
        self.assertTrue(all(not key.startswith("area-") for key in keys))
        self._focus_dock_key(page, lambda key: key.startswith("opening-"))
        page.wait_for_timeout(120)
        consequence = page.locator('[data-testid="skill-use-detail__consequence"]').inner_text()
        self.assertIn(f"全場 {len(line_up)} 名敵人", consequence)
        self._shot(page, "dock-area-openings")
        self.assertEqual(len(self._actions(page, "explore.cast")), 0)

    def test_tampered_cast_shapes_are_rejected_without_casting(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        mp_before = store_state(page)["panels"]["status"]["resources"]["mp"]["current"]
        for payload in (
            {"skill_key": UTILITY_SINGLE, "target_ids": [1], "opening_target_id": 2},
            {"skill_key": UTILITY_SINGLE, "target_ids": [1, 1]},
            {"skill_key": UTILITY_SINGLE, "target_shorthand": "all"},
            {"skill_key": UTILITY_SINGLE, "actor_id": 1},
        ):
            with self.subTest(payload=payload):
                self._wait_idle(page)
                request = page.evaluate(
                    "(p) => window.__elosernBridge.store.dispatchAction('explore.cast', p)", payload
                )
                self.assertIsNotNone(request)
                state = self._wait(
                    page,
                    lambda s, r=request: (s.get("lastActionResult") or {}).get("requestId") == r,
                    "the tampered request's result",
                )
                self.assertEqual(state["lastActionResult"]["code"], "malformed_payload")
        self._wait_idle(page)
        self.assertEqual(store_state(page)["panels"]["status"]["resources"]["mp"]["current"], mp_before)
        self.assertEqual(store_state(page)["mode"], "exploration")


class SkillBookFieldCastJourneyTest(_SkillBookJourney, ManagedServerTearDownMixin, BrowserAcceptanceTest):
    """Journeys that cast: each boots its own isolated managed server."""

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

    def _cast_from_book(self, page, key):
        self._open_book(page)
        self._select_by_search(page, self._skill_label(page, key))
        self._press(page, "Enter")
        return self._wait_flow(page, key)

    def _wait_cast_done(self, page, what):
        return self._wait(
            page,
            lambda s: s.get("skillUse") is None and not s["dispatch"]["inFlight"],
            what,
        )

    @covers_requirement("webclient-skillbook-casting::skillbook-use-shares-one-keyboard-owner-and-preserves-practice")
    def test_keyboard_self_none_and_single_utility_casts(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        actor = int(store_state(page)["panels"]["status"]["actor"]["identity"])

        # SELF: one explicit confirmation, no target field.
        state = self._cast_from_book(page, SELF_BUFF)
        self.assertEqual([item["key"] for item in state["combatMenu"]["items"]], ["cast-self"])
        self._press(page, "Enter")
        state = self._wait_cast_done(page, "the SELF cast")
        self.assertEqual(state["lastActionResult"]["outcome"], "success", state["lastActionResult"])
        self.assertEqual(self._actions(page, "explore.cast")[-1]["payload"], {"skill_key": SELF_BUFF})
        # The committed cast retires the flow without reopening the book.
        self.assertIsNone(state["hudDrawer"])

        # SINGLE ordinary: the server identity of the chosen row, nothing else.
        self._cast_from_book(page, UTILITY_SINGLE)
        self.assertEqual(self._focused_key(page), f"target-{actor}")
        self._press(page, "Enter")
        self._wait_cast_done(page, "the SINGLE cast")
        self.assertEqual(
            self._actions(page, "explore.cast")[-1]["payload"],
            {"skill_key": UTILITY_SINGLE, "target_ids": [actor]},
        )

        # NONE: one explicit confirmation carrying only the skill.
        self._cast_from_book(page, NONE_BREATH)
        self._press(page, "Enter")
        self._wait_cast_done(page, "the NONE cast")
        self.assertEqual(self._actions(page, "explore.cast")[-1]["payload"], {"skill_key": NONE_BREATH})
        self.assertEqual(store_state(page)["mode"], "exploration")
        self.assertEqual(len(self._actions(page, "explore.cast")), 3)

    @covers_requirement("webclient-skillbook-casting::skillbook-use-shares-one-keyboard-owner-and-preserves-practice", "webclient-skillbook-casting::skill-use-lifecycle-and-acceptance-cover-canonical-recovery")
    def test_area_opening_at_a_chosen_scale_starts_combat_then_book_hands_off(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        ladder = combat_journey_values()["ladder_key"]
        state = self._cast_from_book(page, ladder)
        monsters = sorted(row["identity"] for row in state["panels"]["skill_use"]["skill"]["openings"])
        # 威力: the opener row, a rung, a fresh server preview at that scale.
        self.assertEqual(state["combatMenu"]["items"][0]["key"], "scale-open")
        self._focus_dock_key(page, lambda key: key == "scale-open")
        self._press(page, "Enter")
        self._focus_dock_key(page, lambda key: key == "scale-1/2")
        self._press(page, "Enter")
        self._wait(
            page,
            lambda s: ((s.get("panels") or {}).get("skill_use") or {}).get("scale") == 0.5
            and not s["dispatch"]["inFlight"],
            "the 1/2 scale preview",
        )
        self.assertEqual(
            self._actions(page, "explore.skill_preview")[-1]["payload"],
            {"skill_key": ladder, "scale": 0.5},
        )
        self._shot(page, "dock-scaled")
        # The opening asks once more before the fight starts.
        self._focus_dock_key(page, lambda key: key.startswith("opening-"))
        anchor = int(self._focused_key(page).split("-", 1)[1])
        self._press(page, "Enter")
        page.wait_for_selector('[data-testid="skill-use-dock"][data-frame="opening"]', timeout=15000)
        self._shot(page, "dock-opening-confirm")
        self.assertEqual(len(self._actions(page, "explore.cast")), 0)
        self._press(page, "Enter")
        state = self._wait(
            page,
            lambda s: s.get("mode") == "combat"
            and ((s.get("panels") or {}).get("context_actions") or {}).get("kind") == "combat"
            and not s["dispatch"]["inFlight"],
            "combat to start from the opening",
            timeout=45.0,
        )
        cast = self._actions(page, "explore.cast")
        self.assertEqual(len(cast), 1)
        self.assertEqual(cast[0]["payload"], {"skill_key": ladder, "scale": 0.5, "opening_target_id": anchor})
        foes = sorted(
            p["identity"] for p in state["panels"]["context_actions"]["participants"] if p["team"] == "foes"
        )
        self.assertEqual(foes, monsters, "the AREA opening engaged the whole disclosed line-up")
        self.assertIsNone(state["skillUse"])

        # In combat the book's action only hands focus to the combat 技能 entry.
        sent_before = sent_action_count(page)
        self._open_book(page)
        # The character panel is withheld in combat: the book states the
        # server reason and offers only the hand-off.
        self.assertTrue(page.locator('[data-testid="skill-book__unavailable"]').is_visible())
        button = page.locator('[data-testid="skill-book__combat-handoff"]')
        self.assertEqual(button.inner_text(), "改用戰鬥指令")
        self._shot(page, "book-combat")
        button.click()
        page.wait_for_timeout(300)
        state = store_state(page)
        self.assertIsNone(state["hudDrawer"])
        self.assertEqual(state["focus"]["key"], "skills")
        self.assertTrue(page.evaluate("() => document.activeElement && document.activeElement.id === 'action-dock'"))
        self.assertEqual(sent_action_count(page), sent_before, "the hand-off sends nothing")
