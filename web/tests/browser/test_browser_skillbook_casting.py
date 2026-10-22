"""技能-tab graphical skill use (skillbook-authoritative-casting,
webclient-party-skill-tab): live-client journeys through the party window's
技能 tab, which replaced the SkillBook drawer.

Isolated localhost managed servers with every external service blocked. The
read-only journeys (book hierarchy and geometry at both acceptance viewports,
preview disclosure, cancel/back, tampered payloads) share the managed server;
the journeys that actually cast — and therefore spend resources, advance the
clock, or start a fight — each boot a dedicated server, exactly like the
combat-menu journeys.
"""

from __future__ import annotations

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
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
        # The retired skill-book drawer name opens the party window on 技能.
        page.evaluate("() => window.__elosernBridge.store.openHudDrawer('skill')")
        page.wait_for_selector('[data-testid="party-skill-tab"]', timeout=15000)
        page.wait_for_selector('[data-testid="party-skill-tab__tree"]', timeout=15000)

    def _select_by_search(self, page, label):
        """Keyboard-only: `/` → search → ↓ into the tree → Enter to the actions.

        Every handover is waited for, never slept through, because each key
        belongs to whichever element holds focus when it lands and a key sent
        to the wrong one is swallowed without a trace.

        The last wait is the row's own selection: ↓ starts a `party.view_member`
        request, and while it is unanswered the tab disables both actions, so
        an Enter arriving in that window is a no-op that leaves focus on the
        row. Enter is pressed only once an action is actually available — the
        same state that hands focus to it.
        """
        page.keyboard.press("/")
        page.wait_for_function(
            "() => document.activeElement"
            " && document.activeElement.getAttribute('data-testid') === 'party-skill-tab__search'",
            timeout=15000,
        )
        page.keyboard.type(label)
        page.wait_for_function(
            "(label) => { const el = document.activeElement;"
            " return !!el && el.value === label"
            " && document.querySelectorAll("
            "'[data-testid=\"party-skill-tab__tree\"] [data-node-id^=\"skill:\"]').length > 0; }",
            arg=label,
            timeout=15000,
        )
        page.keyboard.press("ArrowDown")
        page.wait_for_function(
            "() => { const el = document.activeElement;"
            " return !!el && (el.getAttribute('data-node-id') || '').startsWith('skill:'); }",
            timeout=15000,
        )
        try:
            page.wait_for_function(
                """() => {
                  const tab = document.querySelector('[data-testid="party-skill-tab"]');
                  if (!tab) return false;
                  return ['cast', 'practice'].some((key) => {
                    const button = tab.querySelector(`[data-testid="action-bar__btn--${key}"]`);
                    return !!button && button.getAttribute('aria-disabled') !== 'true';
                  });
                }""",
                timeout=15000,
            )
        except PlaywrightTimeoutError as exc:
            raise AssertionError(
                f"no action was ever available for {label!r}: {self._focus_snapshot(page)}"
            ) from exc
        page.keyboard.press("Enter")
        self._wait_focus(page, ("action-bar__btn--cast", "action-bar__btn--practice"))

    def _wait_focus(self, page, testids, timeout=30000):
        """Wait for keyboard focus to land on one of ``testids``.

        The budget is a load allowance, not a behavioural bound: a timeout
        reports the focus and selection state it ended in, so a stranded flow
        names its own cause instead of expiring silently.
        """
        try:
            page.wait_for_function(
                """(ids) => {
                  const el = document.activeElement;
                  return !!el && ids.includes(el.getAttribute('data-testid'));
                }""",
                arg=list(testids),
                timeout=timeout,
            )
        except PlaywrightTimeoutError as exc:
            raise AssertionError(
                f"focus never reached {list(testids)}: {self._focus_snapshot(page)}"
            ) from exc

    def _focus_snapshot(self, page):
        """The keyboard and selection state a stranded journey ended in."""
        return page.evaluate(
            """() => {
              const el = document.activeElement;
              const tab = document.querySelector('[data-testid="party-skill-tab"]');
              const q = (sel) => document.querySelector(sel);
              const buttons = [...(tab ? tab.querySelectorAll('[data-testid^="action-bar__btn--"]') : [])];
              const row = q('[data-testid="party-skill-tab__row"][aria-selected="true"]');
              const state = (window.__elosernBridge && window.__elosernBridge.store.view) || {};
              const segment = q('[data-testid="party-skill-tab__segment--active"]');
              return {
                focus: el ? (el.getAttribute('data-testid') || el.getAttribute('data-node-id') || el.tagName) : null,
                drawer: q('[data-testid="hud-drawer"]')?.getAttribute('data-drawer-key') ?? null,
                search: q('[data-testid="party-skill-tab__search"]')?.value ?? null,
                selected: row ? row.getAttribute('data-key') : null,
                segmentActive: segment ? segment.getAttribute('aria-pressed') : 'absent',
                mode: state.mode ?? null,
                actions: buttons.map((b) => ({
                  testid: b.getAttribute('data-testid'),
                  ariaDisabled: b.getAttribute('aria-disabled'),
                  disabled: b.disabled,
                })),
                skillUse: (state.skillUse || {}).skillKey ?? null,
                inFlight: !!(state.dispatch || {}).inFlight,
              };
            }"""
        )

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
    """Read-only 技能-tab journeys on the shared managed server."""

    @covers_requirement("webclient-skillbook-casting::the-skill-tab-follows-the-approved-prototype-and-availability-is-truthful")
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
                      const body = document.querySelector('[data-testid="party-skill-tab"]');
                      return {
                        drawer: r('[data-testid="hud-drawer"]'),
                        list: r('[data-testid="party-skill-tab"] [data-testid="list-detail__list"]'),
                        detail: r('[data-testid="party-skill-tab"] [data-testid="list-detail__detail"]'),
                        use: r('[data-testid="action-bar__btn--cast"]'),
                        practice: r('[data-testid="action-bar__btn--practice"]'),
                        overflowX: body.scrollWidth - body.clientWidth,
                        footer: !!document.querySelector('[data-testid="skill-book-cast-hint"]'),
                        titles: document.querySelectorAll('.drawer-header__title').length,
                        combatBadge: /\\bcombat\\b/.test(body.textContent),
                        chevronMs: getComputedStyle(document.querySelector('.party-skill-tab__chevron')).transitionDuration,
                      };
                    }"""
                )
                drawer, list_, detail = geometry["drawer"], geometry["list"], geometry["detail"]
                self.assertLessEqual(geometry["overflowX"], 1, "the tab must not scroll horizontally")
                # Master–detail: the card sits beside the list, inside the drawer.
                self.assertLessEqual(list_["right"], detail["left"])
                self.assertGreaterEqual(detail["left"], drawer["left"])
                self.assertLessEqual(detail["right"], drawer["right"])
                # The two actions sit side by side in the bar, never overlapping.
                self.assertLessEqual(geometry["practice"]["right"], geometry["use"]["left"])
                self.assertLessEqual(geometry["use"]["right"], detail["right"])
                self.assertFalse(geometry["footer"], "the retired cast-syntax footer must be gone")
                self.assertEqual(geometry["titles"], 1, "the window title renders once")
                self.assertFalse(geometry["combatBadge"], "no literal `combat` badge")
                # The suite runs at the `off` motion level: no transition plays.
                self.assertIn(geometry["chevronMs"], ("0s", "0ms"))
                # Keyboard: the tree holds a single tab stop and Enter goes to 施放.
                page.locator('[data-testid="party-skill-tab__tree"] [tabindex="0"]').focus()
                self._press(page, "Enter")
                self._wait_focus(
                    page, ("action-bar__btn--cast", "action-bar__btn--practice")
                )
                active = page.evaluate("() => document.activeElement.getAttribute('data-testid')")
                self.assertIn(active, ("action-bar__btn--cast", "action-bar__btn--practice"))
                ring = page.evaluate("() => getComputedStyle(document.activeElement).boxShadow")
                self.assertNotEqual(ring, "none", "the focused action carries a visible focus ring")

    @covers_requirement("webclient-skillbook-casting::skill-tab-use-shares-one-keyboard-owner-and-preserves-practice")
    def test_cancel_back_returns_to_the_book_without_casting(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._open_book(page)
        self._select_by_search(page, self._skill_label(page, UTILITY_SINGLE))
        self._wait_focus(
            page, ("action-bar__btn--cast", "action-bar__btn--practice")
        )
        self.assertEqual(page.evaluate("() => document.activeElement.getAttribute('data-testid')"), "action-bar__btn--cast")
        self._press(page, "Enter")
        self._wait_flow(page, UTILITY_SINGLE)
        page.wait_for_selector('[data-testid="skill-use-dock"]', timeout=15000)
        page.wait_for_timeout(150)
        self.assertTrue(
            page.evaluate("() => document.activeElement && document.activeElement.id === 'action-dock'"),
            "the dock owns focus once the window hands over",
        )
        self.assertEqual(page.locator('[data-testid="hud-drawer-scrim"]').count(), 0)
        # Navigate, then back out.
        self._press(page, "ArrowDown")
        self._press(page, "Escape")
        page.wait_for_selector('[data-testid="party-skill-tab"]', timeout=15000)
        page.wait_for_timeout(200)
        self._wait_focus(
            page, ("action-bar__btn--cast", "action-bar__btn--practice")
        )
        self.assertEqual(
            page.evaluate("() => document.activeElement.getAttribute('data-testid')"),
            "action-bar__btn--cast",
        )
        selected = page.locator('[data-testid="party-skill-tab__row"][aria-selected="true"]').get_attribute("data-key")
        self.assertEqual(selected, UTILITY_SINGLE)
        self.assertEqual(len(self._actions(page, "explore.cast")), 0)
        self.assertEqual(len(self._actions(page, "explore.skill_preview")), 1)
        # Besides the tab's read-only selection requests (party.view_member,
        # tab skills), only the read-only preview was sent.
        selections = self._actions(page, "party.view_member")
        self.assertTrue(all(a["payload"]["tab"] == "skills" for a in selections))
        self.assertEqual(sent_action_count(page) - len(selections), 1, "only the read-only preview was sent")

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
            {"actor_id": 1, "skill_key": UTILITY_SINGLE, "target_ids": [1], "opening_target_id": 2},
            {"actor_id": 1, "skill_key": UTILITY_SINGLE, "target_ids": [1, 1]},
            {"actor_id": 1, "skill_key": UTILITY_SINGLE, "target_shorthand": "all"},
            {"skill_key": UTILITY_SINGLE},
            {"skill_key": UTILITY_SINGLE, "actor_id": "1"},
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

    @covers_requirement("webclient-skillbook-casting::skill-tab-use-shares-one-keyboard-owner-and-preserves-practice")
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
        self.assertEqual(
            self._actions(page, "explore.cast")[-1]["payload"],
            {"actor_id": actor, "skill_key": SELF_BUFF},
        )
        # The committed cast retires the flow without reopening the window.
        self.assertIsNone(state["hudDrawer"])

        # SINGLE ordinary: the server identity of the chosen row, nothing else.
        self._cast_from_book(page, UTILITY_SINGLE)
        self.assertEqual(self._focused_key(page), f"target-{actor}")
        self._press(page, "Enter")
        self._wait_cast_done(page, "the SINGLE cast")
        self.assertEqual(
            self._actions(page, "explore.cast")[-1]["payload"],
            {"actor_id": actor, "skill_key": UTILITY_SINGLE, "target_ids": [actor]},
        )

        # NONE: one explicit confirmation carrying only the skill.
        self._cast_from_book(page, NONE_BREATH)
        self._press(page, "Enter")
        self._wait_cast_done(page, "the NONE cast")
        self.assertEqual(
            self._actions(page, "explore.cast")[-1]["payload"],
            {"actor_id": actor, "skill_key": NONE_BREATH},
        )
        self.assertEqual(store_state(page)["mode"], "exploration")
        self.assertEqual(len(self._actions(page, "explore.cast")), 3)

    @covers_requirement("webclient-skillbook-casting::skill-tab-use-shares-one-keyboard-owner-and-preserves-practice", "webclient-skillbook-casting::skill-use-lifecycle-and-acceptance-cover-canonical-recovery")
    def test_area_opening_at_a_chosen_scale_starts_combat_then_book_hands_off(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        actor = int(store_state(page)["panels"]["status"]["actor"]["identity"])
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
            {"actor_id": actor, "skill_key": ladder, "scale": 0.5},
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
        self.assertEqual(
            cast[0]["payload"],
            {
                "actor_id": actor,
                "skill_key": ladder,
                "scale": 0.5,
                "opening_target_id": anchor,
            },
        )
        foes = sorted(
            p["identity"] for p in state["panels"]["context_actions"]["participants"] if p["team"] == "foes"
        )
        self.assertEqual(foes, monsters, "the AREA opening engaged the whole disclosed line-up")
        self.assertIsNone(state["skillUse"])

        # In combat the 技能 tab keeps the committed rows, but 施放 and
        # 排入修煉 are disabled with their committed reasons and send
        # nothing: combat casting stays on the command card.
        self._wait_idle(page)
        self._open_book(page)
        sent_before = sent_action_count(page)
        cast = page.locator('[data-testid="action-bar__btn--cast"]')
        practice = page.locator('[data-testid="action-bar__btn--practice"]')
        self.assertEqual(cast.get_attribute("aria-disabled"), "true")
        self.assertEqual(practice.get_attribute("aria-disabled"), "true")
        reasons = page.locator('[data-testid="action-bar__reason"]').all_inner_texts()
        self.assertIn("戰鬥中請使用指令卡", reasons)
        self.assertIn("戰鬥中無法排入修煉。", reasons)
        self._shot(page, "book-combat")
        # aria-disabled controls keep focus but refuse activation; force the
        # pointer through Playwright's actionability check.
        cast.click(force=True)
        practice.click(force=True)
        page.wait_for_timeout(300)
        self.assertEqual(store_state(page)["hudDrawer"], "party")
        self.assertEqual(sent_action_count(page), sent_before, "the disabled actions send nothing")


class CompanionFieldCastJourneyTest(_SkillBookJourney, ManagedServerTearDownMixin, BrowserAcceptanceTest):
    """A companion casts a field heal from the party window's 技能 tab.

    Its own isolated server with the companion-field-cast seed: the bound
    kit companion owns the out-of-combat SINGLE heal and the commander
    starts wounded.
    """

    HEAL = "t_hush_mend"

    def setUp(self) -> None:
        from .harness import ManagedServer

        self.server = ManagedServer()
        self.server.runtime.env["ELOSERN_BROWSER_COMPANION_FIELD_CAST"] = "1"
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    @classmethod
    def setUpClass(cls) -> None:
        pass

    @covers_requirement(
        "webclient-party-window::the-skill-tab-casts-and-books-for-the-viewed-member",
        "webclient-skillbook-casting::skill-tab-use-shares-one-keyboard-owner-and-preserves-practice",
    )
    def test_companion_casts_a_field_heal_from_the_skill_tab(self):
        page = self.logged_in_page()
        install_outbound_recorder(page)
        state = store_state(page)
        commander = int(state["panels"]["status"]["actor"]["identity"])
        companions = [
            row["identity"] for row in state["panels"]["party"]["slots"] if row["identity"] != commander
        ]
        self.assertTrue(companions, "the seed binds a companion")
        companion = companions[0]

        # Open the window on 技能 and select the companion on the rail.
        self._open_book(page)
        page.locator(f'[data-testid="member-rail__entry--{companion}"]').click()
        self._wait(
            page,
            lambda s: (s["panels"].get("character") or {}).get("member_id") == companion
            and not s["dispatch"]["inFlight"],
            "the companion's character panel",
        )
        selection = self._actions(page, "party.view_member")[-1]["payload"]
        self.assertEqual(selection["member_id"], companion)
        self.assertEqual(selection["tab"], "skills")
        page.locator(f'[data-testid="party-skill-tab__row"][data-key="{self.HEAL}"]').wait_for(timeout=15000)
        page.locator(f'[data-testid="party-skill-tab__row"][data-key="{self.HEAL}"]').click()
        self._wait_idle(page)
        self._shot(page, "skill-tab-companion")

        # 施放: one preview for the companion; the window closes before the dock.
        page.locator('[data-testid="action-bar__btn--cast"]').click()
        state = self._wait_flow(page, self.HEAL)
        previews = self._actions(page, "explore.skill_preview")
        self.assertEqual(len(previews), 1)
        self.assertEqual(previews[0]["payload"], {"actor_id": companion, "skill_key": self.HEAL})
        self.assertIsNone(state["hudDrawer"])
        self.assertEqual(state["panels"]["skill_use"]["actor_id"], companion)
        page.wait_for_selector('[data-testid="skill-use-dock"]', timeout=15000)

        # The dock's target flow continues for the companion: heal the commander.
        self._focus_dock_key(page, lambda key: key == f"target-{commander}")
        self._press(page, "Enter")
        state = self._wait(
            page,
            lambda s: s.get("skillUse") is None and not s["dispatch"]["inFlight"],
            "the companion's heal",
        )
        self.assertEqual(state["lastActionResult"]["outcome"], "success", state["lastActionResult"])
        casts = self._actions(page, "explore.cast")
        self.assertEqual(len(casts), 1)
        self.assertEqual(
            casts[0]["payload"],
            {"actor_id": companion, "skill_key": self.HEAL, "target_ids": [commander]},
        )
        self.assertEqual(state["mode"], "exploration")
