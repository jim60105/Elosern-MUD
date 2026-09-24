"""Desktop-shell acceptance: required surfaces at 1440x900 and 1280x720, stage-anchor geometry, head-card identity, minimap mode presence, the island stack anchor, and the low-HP stage hook.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    focus_action_dock,
    install_outbound_recorder,
    inject_snapshot,
    sent_action_count,
    store_state,
    valid_art_panel,
    valid_character_panel,
    valid_local_map_panel,
    valid_status_panel,
    wait_for_narrative_settled,
    wait_for_store_state,
)


REQUIRED_SURFACES = (
    '[data-testid="topbar"]',
    '[data-testid="narrative-feed"]',
    '[data-testid="command-line"]',
)


class ShellAcceptanceTest(BrowserAcceptanceTest):
    """Every required surface at 1440x900 and 1280x720, plus keyboard journeys."""
    def assert_surfaces_visible(self, page):
        surfaces_js = ", ".join(repr(s) for s in REQUIRED_SURFACES)
        wait_for_store_state(
            page,
            lambda s: bool(s.get("connected")),
            dom_readiness={
                "selector": REQUIRED_SURFACES[0],
                "predicate": (
                    "() => { const sels = [" + surfaces_js + "]; "
                    "for (const sel of sels) { if (!document.querySelector(sel)) { return false; } } "
                    "return true; }"
                ),
                "description": "guaranteed shell surfaces rendered",
            },
        )
        for selector in REQUIRED_SURFACES:
            locator = page.locator(selector)
            self.assertEqual(locator.count(), 1, f"missing surface {selector}")
            self.assertTrue(locator.is_visible(), f"{selector} is not visible")
        # H5 (task 8.6): the command line is permanently present — the input
        # field is in the DOM, visible and focusable with no opening action:
        # no entry control, no `aria-expanded` state, no closed state.
        self.assertEqual(page.locator('#inputfield').count(), 1)
        self.assertTrue(page.locator('#inputfield').is_visible(), "the command field is visible")
        self.assertEqual(page.locator('.drawer-entry').count(), 0, "no entry control")
        self.assertEqual(page.locator('[aria-expanded]').count(), 0, "no element reports aria-expanded")

    @covers_requirement(
        "webclient-desktop-shell::required-desktop-surfaces-remain-visible-and-usable"
    )
    def test_surfaces_visible_at_1440x900(self):
        page = self.logged_in_page((1440, 900))
        self.assert_surfaces_visible(page)

    @covers_requirement(
        "webclient-desktop-shell::required-desktop-surfaces-remain-visible-and-usable"
    )
    def test_surfaces_visible_at_1280x720(self):
        page = self.logged_in_page((1280, 720))
        self.assert_surfaces_visible(page)

    @covers_requirement(
        "webclient-desktop-shell::theme-and-controls-remain-accessible"
    )
    @covers_requirement(
        "webclient-contextual-hud::vitals-pair-an-icon-a-label-and-numerals-with-a-trailing-damage-bar",
    )
    def test_unavailable_placeholders_and_numeric_status(self):
        page = self.logged_in_page()
        # The art component is now the real renderer: no foundation placeholder
        # remains, and a scene without a generated asset renders the truthful
        # art placeholder inside the art surface.
        placeholders = page.locator(".elosern-placeholder").all_inner_texts()
        self.assertEqual(len(placeholders), 0, "no foundation placeholder remains")
        self.assertEqual(page.locator('[data-testid="art-panel"]').count(), 0, "art-panel absent")
        # The minimap surface renders (or gracefully reports unavailable) and
        # is no longer a placeholder.
        local_map_surface = page.locator('[data-testid="local-map"]')
        self.assertEqual(local_map_surface.count(), 1, "local-map surface present")
        self.assertTrue(local_map_surface.is_visible())

        # Inject below-max HP so the vitals island is visible and gauge rows render text
        status = valid_status_panel("艾倫·灰誓", "char-42")
        status["resources"]["hp"]["current"] = 80
        inject_snapshot(page, {"status": status})
        page.wait_for_timeout(200)

        # H2 re-map: the preserved `status-panel__gauge-value--<key>` hooks
        # now live on the vitals island's rows (the old `.status-gauge__value`
        # class-literal selector is retired in favour of the data-testid hooks).
        for key in ("hp", "mp", "sp"):
            value = page.locator(
                f'[data-testid="status-panel__gauge-value--{key}"]'
            ).inner_text()
            current, maximum = value.split(" / ")
            self.assertTrue(current.isdigit(), f"current not numeric: {current!r}")
            self.assertTrue(maximum.isdigit(), f"maximum not numeric: {maximum!r}")

        # The mockup gauge tracks complement the mandated numeric text.
        for key in ("hp", "mp", "sp"):
            self.assertEqual(
                page.locator(f'[data-testid="status-panel__gauge--{key}"]').count(),
                1,
                f"{key} gauge row present",
            )

        header_conn = page.locator(".meta-conn").inner_text()
        self.assertIn("已連線", header_conn)

    @covers_requirement(
        "webclient-status-presentation::server-time-and-location-are-read-only-presentation-data",
        "webclient-desktop-shell::required-desktop-surfaces-remain-visible-and-usable",
    )
    def test_header_shows_location_time_and_connection_dot(self):
        page = self.logged_in_page()
        state = store_state(page)
        self.assertEqual(state["mode"], "exploration")
        self.assertIsNotNone(state["serverTime"])

        # The header identifies location, world time, and the connected state;
        # the raw mode label is gone (the dock content identifies the mode).
        header = page.locator('[data-testid="topbar"]')
        self.assertEqual(header.evaluate("el => el.classList.contains('connected')"), True)
        location = page.locator('[data-testid="topbar-location"]').inner_text()
        self.assertNotEqual(location, "位置：--", "location must be synced")
        self.assertTrue(location.strip())
        clock = page.locator('[data-testid="topbar-clock"]').inner_text()
        self.assertRegex(clock, r"\d+ 日 · \d{2}:\d{2}")
        conn = page.locator(".meta-conn").inner_text()
        self.assertIn("●", conn)
        self.assertIn("已連線", conn)
        self.assertEqual(page.locator(".header-mode").count(), 0, "no raw mode label")

        # Wilderness location preference (webclient-minimap-04-island-single-affordance D5):
        # on a wilderness snapshot the top-meta location states the region name
        # from the local_map panel, not the raw room key "Wilderness" from the
        # status panel.
        wilderness_status = valid_status_panel("影行者", "42")
        wilderness_status["actor"]["location"] = {"label": "Wilderness", "identity": "17"}
        # The whole wilderness payload is injected here; the client renders
        # its region name verbatim, so the label is authored payload data,
        # not a registry row.
        wilderness_map = {
            "schema_version": 1,
            "available": True,
            "layer": "wilderness",
            "current_node": "wild:plains:60:107",
            "title": "苔影濕谷",
            "nodes": [
                {
                    "id": "wild:plains:60:107",
                    "label": "苔影濕谷",
                    "x": 60,
                    "y": 107,
                    "visibility": "current",
                    "current": True,
                    "anchor": True,
                    "landmark": False,
                    "action": None,
                }
            ],
            "edges": [],
            "legend": [],
        }
        inject_snapshot(page, {"status": wilderness_status, "local_map": wilderness_map})
        page.wait_for_timeout(300)
        loc = page.locator('[data-testid="topbar-location"]').inner_text()
        self.assertEqual(loc, "苔影濕谷")
        self.assertNotIn("Wilderness", loc)

    @covers_requirement(
        "webclient-desktop-shell::required-desktop-surfaces-remain-visible-and-usable"
    )
    def test_stage_anchors_do_not_intersect_at_both_viewports(self):
        """H1 group 8.3: the full-bleed stage's named HUD anchors must not overlap.

        The stage anchors (``hud-left``, ``hud-right``, ``feed``, ``dock``,
        ``command-line``) are absolutely positioned; any pair of *visible*
        anchors sharing a non-zero-area intersection would visually collide,
        breaking the "surfaces remain usable" contract. Verified at both
        supported desktop viewports.
        """
        for viewport in ((1440, 900), (1280, 720)):
            page = self.logged_in_page(viewport)
            overlap = page.evaluate(
                """() => {
                  const testids = ["anchor-hud-left", "anchor-hud-right", "anchor-feed",
                                   "anchor-dock", "anchor-command-line"];
                  const anchors = testids
                    .map((t) => {
                      const el = document.querySelector('[data-testid="' + t + '"]');
                      if (!el) { return null; }
                      const r = el.getBoundingClientRect();
                      const visible = r.width > 0 && r.height > 0 && el.offsetParent !== null;
                      return { testid: t, r: r, visible: visible };
                    })
                    .filter(Boolean)
                    .filter((a) => a.visible);
                  const intersecting = [];
                  for (let i = 0; i < anchors.length; i++) {
                    for (let j = i + 1; j < anchors.length; j++) {
                      const a = anchors[i].r, b = anchors[j].r;
                      const xOverlap = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
                      const yOverlap = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
                      if (xOverlap > 0 && yOverlap > 0) {
                        intersecting.push(anchors[i].testid + " <-> " + anchors[j].testid);
                      }
                    }
                  }
                  return { intersecting: intersecting };
                }"""
            )
            self.assertEqual(
                overlap["intersecting"],
                [],
                f"stage anchors intersect at {viewport[0]}x{viewport[1]}: {overlap['intersecting']}",
            )

    @covers_requirement(
        "webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone"
    )
    @covers_requirement(
        "webclient-contextual-hud::surface-visibility-is-gated-by-the-committed-game-mode"
    )
    def test_minimap_present_in_exploration_absent_in_combat(self):
        """H1 group 8.4: the minimap is visible in exploration and hidden in combat.

        The seeded exploration scene does not always carry a map-knowledge
        record, so the test injects a valid local_map panel through the
        wired reducer. The HUD mode-gating matrix (design D2) hides the
        minimap in combat (and creation) via ``display:none !important`` on
        ``data-elosern-mode``.
        """
        page = self.logged_in_page()
        # Exploration: inject an available local_map panel; the minimap renders.
        inject_snapshot(
            page, {"local_map": valid_local_map_panel()}, mode="exploration"
        )
        page.wait_for_timeout(150)
        lm = page.locator('[data-testid="local-map"]')
        self.assertEqual(lm.count(), 1, "minimap renders in exploration mode")
        self.assertTrue(lm.is_visible(), "minimap is visible in exploration mode")

        # Combat: force combat mode; the minimap is hidden by the CSS mode-gate.
        inject_snapshot(page, {"local_map": valid_local_map_panel()}, mode="combat")
        page.wait_for_timeout(150)
        lm = page.locator('[data-testid="local-map"]')
        self.assertEqual(lm.count(), 1, "the minimap element remains in the DOM")
        hidden = page.evaluate(
            "() => { const el = document.querySelector('[data-testid=\"local-map\"]'); "
            "return el ? (el.offsetParent === null) : false; }"
        )
        self.assertTrue(hidden, "the minimap is hidden (display:none) in combat mode")

    @covers_requirement(
        "webclient-contextual-hud::the-webclient-renders-a-full-bleed-cinematic-stage-with-anchored-hud-surfaces",
    )
    @covers_requirement(
        "webclient-contextual-hud::the-hud-island-stack-renders-as-bounded-floating-islands-not-column-cards",
    )
    def test_populated_island_stack_fits_its_anchor_at_both_viewports(self):
        """H2 task 9.5: at 1440x900 and 1280x720, the left island stack,
        the minimap island, the narrative caption, and the dock must not
        intersect — with the condition overflow disclosed."""
        for viewport in ((1440, 900), (1280, 720)):
            with self.subTest(viewport=viewport):
                page = self.new_page(viewport)
                from .browser_helpers import login_and_open

                login_and_open(page, self.webclient_url, self.base_url)
                # An 8-condition status panel makes the +N overflow chip
                # render, so the assertion runs with the overflow disclosed.
                status = valid_status_panel("艾倫·灰誓", "char-42")
                status["resources"]["hp"]["current"] = 80
                status["conditions"] = [
                    {
                        "code": f"cond_{i}",
                        "label": f"狀態{i + 1}",
                        "severity": ["beneficial", "informational", "warning", "harmful", "critical"][i % 5],
                        **({"remaining_seconds": i * 10} if i % 4 == 0 else {}),
                    }
                    for i in range(8)
                ]
                inject_snapshot(
                    page,
                    {
                        "status": status,
                        "local_map": valid_local_map_panel(),
                        "art": valid_art_panel(),
                    },
                    mode="exploration",
                )
                page.wait_for_timeout(300)
                overflow = page.locator('[data-testid="status-panel__condition-overflow"]')
                if overflow.count() > 0:
                    overflow.click()
                    page.wait_for_timeout(200)

                def intersect(sel_a, sel_b):
                    return page.evaluate(
                        """(sels) => {
                          const a = document.querySelector(sels[0]);
                          const b = document.querySelector(sels[1]);
                          if (!a || !b) return false;
                          const ra = a.getBoundingClientRect();
                          const rb = b.getBoundingClientRect();
                          const T = 1;
                          return !(ra.right <= rb.left + T || rb.right <= ra.left + T ||
                                  ra.bottom <= rb.top + T || rb.bottom <= ra.top + T);
                        }""",
                        [sel_a, sel_b],
                    )

                selectors = [
                    '[data-testid="status-panel"]',
                    '[data-testid="local-map"]',
                    '[data-testid="narrative-feed"]',
                    "#action-dock",
                ]
                for i in range(len(selectors)):
                    for j in range(i + 1, len(selectors)):
                        self.assertFalse(
                            intersect(selectors[i], selectors[j]),
                            f"{selectors[i]} intersects {selectors[j]} at {viewport}",
                        )
                page.close()

    @covers_requirement(
        "webclient-contextual-hud::the-vitals-island-is-shown-only-in-combat-or-while-a-vital-or-a-condition-needs-attention",
    )
    def test_vitals_island_hides_at_full_health_outside_combat(self):
        """The vitals island hides with display:none at full health outside combat."""
        page = self.logged_in_page()
        # 1. Full vitals with no conditions outside combat: status-panel is attached but not visible (display:none)
        full_status = valid_status_panel("艾倫·灰誓", "char-42")
        full_status["resources"]["hp"]["current"] = full_status["resources"]["hp"]["maximum"]
        full_status["resources"]["mp"]["current"] = full_status["resources"]["mp"]["maximum"]
        full_status["resources"]["sp"]["current"] = full_status["resources"]["sp"]["maximum"]
        full_status["conditions"] = []
        inject_snapshot(page, {"status": full_status}, mode="exploration")
        page.wait_for_timeout(200)
        panel = page.locator('[data-testid="status-panel"]')
        self.assertEqual(panel.count(), 1)
        self.assertFalse(panel.is_visible(), "vitals island hidden at full health outside combat")

        # 2. Full vitals with only a beneficial condition: still not visible
        beneficial_status = dict(full_status)
        beneficial_status["conditions"] = [
            {"code": "defense_instinct_defense_bonus", "label": "防禦本能", "severity": "beneficial"}
        ]
        inject_snapshot(page, {"status": beneficial_status}, mode="exploration")
        page.wait_for_timeout(200)
        self.assertFalse(panel.is_visible(), "vitals island stays hidden with only beneficial conditions")

        # 3. Full vitals with one harmful condition: visible with that chip
        harmful_status = dict(full_status)
        harmful_status["conditions"] = [
            {"code": "poison", "label": "中毒", "severity": "harmful"}
        ]
        inject_snapshot(page, {"status": harmful_status}, mode="exploration")
        page.wait_for_timeout(200)
        self.assertTrue(panel.is_visible(), "vitals island visible with harmful condition")
        self.assertEqual(page.locator('[data-testid="status-panel__condition--poison"]').count(), 1)

        # 4. MP below max with no condition: visible
        injured_status = dict(full_status)
        injured_status["resources"] = dict(full_status["resources"])
        injured_status["resources"]["mp"] = {"current": 40, "maximum": 60}
        injured_status["conditions"] = []
        inject_snapshot(page, {"status": injured_status}, mode="exploration")
        page.wait_for_timeout(200)
        self.assertTrue(panel.is_visible(), "vitals island visible when mp below max")
        page.close()

    @covers_requirement(
        "webclient-contextual-hud::the-low-hp-presentation-state-is-derived-client-side-and-drives-the-stage-hook",
    )
    def test_low_hp_state_drives_the_stage_hook(self):
        """H2 low-HP: the client derives the low-HP presentation state from
        the committed hp ratio against the 25% display threshold and drives
        the stage's red vignette through the existing low-HP hook. A low
        ratio (hp 20/100 = 0.2) sets data-lowhp="true"; a healthy ratio
        (hp 100/100 = 1.0) sets data-lowhp="false"."""
        page = self.logged_in_page()

        def inject_status(hp_current: int, hp_maximum: int) -> None:
            st = valid_status_panel("艾倫·灰誓", "char-42")
            st["resources"] = {
                "hp": {"current": hp_current, "maximum": hp_maximum},
                "mp": {"current": 50, "maximum": 50},
                "sp": {"current": 20, "maximum": 20},
            }
            inject_snapshot(page, {"status": st})
            page.wait_for_timeout(300)

        # Low hp (0.2 <= 0.25): the stage root carries the low-HP state.
        inject_status(20, 100)
        self.assertEqual(
            page.locator('[data-testid="elosern-stage"]').get_attribute("data-lowhp"),
            "true",
            "a committed hp ratio at or below the 25% threshold must light the stage",
        )
        # Healthy hp (1.0 > 0.25): the stage returns to its ordinary state.
        inject_status(100, 100)
        self.assertEqual(
            page.locator('[data-testid="elosern-stage"]').get_attribute("data-lowhp"),
            "false",
            "a committed hp ratio above the threshold must clear the stage state",
        )
        page.close()
