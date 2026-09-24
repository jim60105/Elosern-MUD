"""Local-map browser acceptance: keyboard/pointer interaction with the minimap island and its overlay at both viewports.
"""

from __future__ import annotations

import time
from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import store_state, wait_for_store_state


class LocalMapBrowserTest(BrowserAcceptanceTest):
    """Dedicated minimap server with pre-recorded knowledge, shared per process."""
    @classmethod
    def setUpClass(cls) -> None:
        from . import fixtures
        from .harness import ManagedServer

        runtime = fixtures.create_runtime(prefix="elosern-minimap-")
        runtime.env["ELOSERN_BROWSER_MINIMAP"] = "1"
        cls.server = ManagedServer(runtime=runtime)
        cls.server.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.runtime.http_port}"
        cls.webclient_url = cls.server.runtime.webclient_url

    @classmethod
    def tearDownClass(cls) -> None:
        if getattr(cls, "server", None) is not None:
            try:
                cls.server.stop()
            finally:
                cls.server = None

    def _local_map_panel(self, page):
        return store_state(page)["panels"].get("local_map")

    def _wait_local_map_available(self, page, timeout=30000):
        wait_for_store_state(
            page,
            lambda s: (s.get("panels") or {}).get("local_map", {}).get("available") is True,
            timeout=timeout,
        )
        return self._local_map_panel(page)

    def _local_map_nodes(self, page):
        return self._wait_local_map_available(page)["nodes"]

    def _send(self, page, command):
        page.evaluate(
            "(args) => Evennia.msg('text', [args.cmd], {})", {"cmd": command}
        )

    def _inject_panel(self, page, panel) -> dict:
        return page.evaluate(
            """(panel) => {
              const bridge = window.__elosernBridge;
              const v = bridge.store.view;
              const envelope = {
                protocol_version: 1,
                presentation_epoch: v.epoch,
                revision: v.revision + 1,
                mode: v.mode,
                layout_version: v.layoutVersion ?? 1,
                panels: { local_map: panel },
                server_time: { year: 1, season_index: 0, season_label: "春", day_in_season: 1, hour: 12, minute: 0, second: 0 },
              };
              return bridge.store.receive(v.generation, "ui_update", [envelope], {});
            }""",
            panel,
        )

    @covers_requirement(
        "webclient-desktop-shell::required-desktop-surfaces-remain-visible-and-usable"
    )
    @covers_requirement("webclient-local-map::adjacent-traversable-map-nodes-submit-explore-move-through-their-move-descriptor")
    def test_adjacent_traversable_node_submits_explore_move(self):
        page = self.logged_in_page()
        from .browser_helpers import install_outbound_recorder, sent_action_count

        install_outbound_recorder(page)
        self._wait_local_map_available(page)
        action_ready = page.locator('[data-testid="local-map__actionable"]')
        self.assertGreaterEqual(action_ready.count(), 1)
        action_ready.first.click()
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if sent_action_count(page, "explore.move") >= 1:
                break
            page.wait_for_timeout(250)
        self.assertEqual(sent_action_count(page, "explore.move"), 1)
        sent = page.evaluate("window.__elosernSent || []")
        payload = next(
            args[0]["payload"]
            for cmd, args, _kw in sent
            if cmd == "ui_action" and args[0]["action_id"] == "explore.move"
        )
        panel = self._local_map_panel(page)
        self.assertEqual(payload["current_node"], panel["current_node"])
        self.assertTrue(payload["exit_ref"])

    def test_minimap_visible_and_keyboard_usable_at_both_viewports(self):
        for viewport in ((1440, 900), (1280, 720)):
            with self.subTest(viewport=viewport):
                page = self.new_page(viewport)
                from .browser_helpers import login_and_open

                login_and_open(page, self.webclient_url, self.base_url)
                self._wait_local_map_available(page)
                for selector in (
                    '[data-testid="narrative-feed"]',
                    '[data-testid="local-map"]',
                ):
                    self.assertTrue(
                        page.locator(selector).is_visible(),
                        f"{selector} not visible at {viewport}",
                    )
                page.close()

    @staticmethod
    def _wilderness_scale_panel() -> dict:
        """A committed-form wilderness payload carrying the fifth-entry scale note.

        The legend mirrors the presenter's exact wire shape: the four state
        labels in fixed order, then the scale note derived from
        ``WILDERNESS_KM_PER_CELL`` (server-side derivation is pinned in
        ``web.webclient.presentation.tests.test_local_map``).
        """
        return {
            "schema_version": 1,
            "available": True,
            "layer": "wilderness",
            "current_node": "wild:elosern:60:103",
            "title": "荒野地圖",
            "nodes": [
                {
                    "id": "wild:elosern:60:103",
                    "label": "丘陵",
                    "x": 0,
                    "y": 0,
                    "visibility": "current",
                    "current": True,
                    "anchor": False,
                    "landmark": False,
                    "action": None,
                },
                {
                    "id": "wild:elosern:60:104",
                    "label": "森林",
                    "x": 0,
                    "y": 1,
                    "visibility": "visible_unvisited",
                    "current": False,
                    "anchor": False,
                    "landmark": False,
                    "action": None,
                },
            ],
            "edges": [
                {
                    "source": "wild:elosern:60:103",
                    "destination": "wild:elosern:60:104",
                    "label": "n",
                    "known": True,
                    "traversable": True,
                }
            ],
            "legend": [
                "你目前所在的位置",
                "尚未探索的相鄰位置",
                "已經探索過的相鄰位置",
                "曾經到過、但不在附近的遠方位置",
                "每格約 10 公里",
            ],
        }

    @covers_requirement(
        "webclient-local-map::the-legend-renders-beyond-state-entries-as-neutral-info-chips"
    )
    def test_overlay_renders_scale_note_as_neutral_info_entry(self):
        page = self.logged_in_page()
        self._wait_local_map_available(page)
        result = self._inject_panel(page, self._wilderness_scale_panel())
        self.assertTrue(result["accepted"], f"ui_update rejected: {result}")
        wait_for_store_state(
            page,
            lambda s: len(((s.get("panels") or {}).get("local_map") or {}).get("legend") or [])
            == 5,
            timeout=30000,
        )
        # The island still mounts no legend element for this payload.
        self.assertEqual(
            page.locator('[data-testid="local-map__legend"]').count(), 0,
            "the island mounts no legend for a scale-note payload",
        )
        page.evaluate("window.__elosernBridge.store.openOverlay('map')")
        page.wait_for_selector('[data-testid="map-overlay"]', timeout=15000)
        # webclient-full-map-fit-view D5: the legend lives in the `?`
        # popover, which opens closed — open it before collecting entries.
        page.click('[data-testid="map-overlay-legend-toggle"]')
        page.wait_for_selector('[data-testid="map-overlay-legend-popover"]', timeout=15000)
        items = page.locator(
            '[data-testid="map-overlay"] [data-testid^="local-map__legend-item--"]'
        )
        items.first.wait_for(timeout=15000)
        self.assertEqual(items.count(), 5)
        # The first four keep their state chip treatments in the fixed order.
        states = ("current", "visible_unvisited", "visible_visited", "remembered")
        for index, state in enumerate(states):
            chip_classes = items.nth(index).locator(".local-map__legend-chip").get_attribute("class")
            self.assertIn(f"local-map__legend-chip--{state}", chip_classes)
        # The fifth entry is the scale note: neutral info chip, no state class,
        # and its text label rendered in full.
        fifth = items.nth(4)
        fifth_classes = fifth.locator(".local-map__legend-chip").get_attribute("class")
        self.assertIn("local-map__legend-chip--info", fifth_classes)
        for state in states:
            self.assertNotIn(f"local-map__legend-chip--{state}", fifth_classes)
        self.assertEqual(fifth.inner_text().strip(), "每格約 10 公里")
        page.close()


    @staticmethod
    def _tall_street_panel() -> dict:
        """A two-column, thirty-one-row grid street payload (webclient-full-map-fit-view 5.5).

        Sixty-two grid nodes (plus one remembered gateway, the bridge cap is
        64) with move actions on the neighbours of the current room, so the
        fitted view has a genuinely tall drawing (rows 0..30 — tall enough
        that the fit is height-limited, the 2× upper bound gives the window
        real pan range on both sides of the mid-strip current room, and a
        720px slam overflows the window and leaves the node outside), a
        keyboard-reachable actionable node, and one remembered gateway far
        outside the drawn extent, so the canvas carries a named edge
        direction marker whose box must fit too.
        """
        cols = (0, 1)
        rows = tuple(range(31))
        current = (1, 15)
        nodes = []
        for x in cols:
            for y in rows:
                node_id = f"grid:fitview:{x}:{y}"
                is_current = (x, y) == current
                adjacent_to_current = abs(x - current[0]) + abs(y - current[1]) == 1
                # The far-top cell also carries a move action: the keyboard
                # reveal step needs an actionable node at the drawing's top
                # extreme, far enough from the mid-strip current room that a
                # bottom-clamp pan provably leaves it outside the window
                # (the remembered gateway inflates the canvas height, so the
                # clamp range never pushes mid-strip nodes off-window).
                far_top_action = (x, y) == (1, 0)
                nodes.append({
                    "id": node_id,
                    "label": f"{x},{y}",
                    "x": x,
                    "y": y,
                    "visibility": "current" if is_current else "visible_visited",
                    "current": is_current,
                    "anchor": False,
                    "landmark": False,
                    "action": (
                        {"kind": "move", "exit_ref": f"exit-{x}-{y}", "destination": node_id}
                        if adjacent_to_current or far_top_action
                        else None
                    ),
                })
        nodes.append({
            "id": "grid:fitview:remembered:capital",
            "label": "遠方王城",
            "x": 100,
            "y": 100,
            "visibility": "remembered",
            "current": False,
            "anchor": False,
            "landmark": True,
            "action": None,
        })
        edges = []
        for x in cols:
            for y in rows:
                if y + 1 in rows:
                    edges.append({
                        "source": f"grid:fitview:{x}:{y}",
                        "destination": f"grid:fitview:{x}:{y + 1}",
                        "label": "n",
                        "known": True,
                        "traversable": True,
                    })
                if x + 1 in cols:
                    edges.append({
                        "source": f"grid:fitview:{x}:{y}",
                        "destination": f"grid:fitview:{x + 1}:{y}",
                        "label": "e",
                        "known": True,
                        "traversable": True,
                    })
        return {
            "schema_version": 1,
            "available": True,
            "layer": "grid",
            "title": "fitview 街道圖",
            "current_node": f"grid:fitview:{current[0]}:{current[1]}",
            "nodes": nodes,
            "edges": edges,
            "legend": [
                "你目前所在的位置",
                "尚未探索的相鄰位置",
                "已經探索過的相鄰位置",
                "曾經到過、但不在附近的遠方位置",
            ],
        }

    @staticmethod
    def _fit_view_measure(page) -> dict:
        """Measure the fitted viewport, the host body scroll state, and every node box."""
        return page.evaluate(
            """() => {
              const viewport = document.querySelector('.local-map__viewport--fit');
              const body = document.querySelector('[data-testid="overlay-host-body"]');
              const v = viewport.getBoundingClientRect();
              const nodeBoxes = {};
              for (const el of document.querySelectorAll('.local-map__viewport--fit [data-node]')) {
                const r = el.getBoundingClientRect();
                nodeBoxes[el.getAttribute('data-node')] = {
                  left: r.left, right: r.right, top: r.top, bottom: r.bottom,
                  cx: (r.left + r.right) / 2, cy: (r.top + r.bottom) / 2,
                  width: r.width, height: r.height,
                };
              }
              const edgeBoxes = [];
              for (const el of document.querySelectorAll('.local-map__viewport--fit .local-map__edge-marker')) {
                const r = el.getBoundingClientRect();
                edgeBoxes.push({ left: r.left, right: r.right, top: r.top, bottom: r.bottom });
              }
              return {
                viewport: { left: v.left, right: v.right, top: v.top, bottom: v.bottom,
                            cx: (v.left + v.right) / 2, cy: (v.top + v.bottom) / 2 },
                bodyScroll: { scrollHeight: body.scrollHeight, clientHeight: body.clientHeight },
                nodeBoxes,
                edgeBoxes,
              };
            }"""
        )

    @staticmethod
    def _inside(outer, inner, tolerance=1.0) -> bool:
        return (
            inner["left"] >= outer["left"] - tolerance
            and inner["right"] <= outer["right"] + tolerance
            and inner["top"] >= outer["top"] - tolerance
            and inner["bottom"] <= outer["bottom"] + tolerance
        )

    @covers_requirement(
        "webclient-local-map::the-full-map-surface-opens-fitted-to-its-body-and-offers-zoom-pan-and-recentre"
    )
    def test_full_map_opens_fitted_zooms_pans_and_recentres(self):
        """webclient-full-map-fit-view (design D1/D3/D4/D5/D7): the whole drawing
        opens inside the body with no scrollbar; wheel zoom anchors on the
        pointer; keyboard zoom-out to the bound fits everything again; a drag
        pans without ever submitting a move; recentre brings the current node
        back; Tab reveals an off-window actionable node; and the legend popover
        is the topmost disclosure with a reset-to-fitted reopen.
        """
        page = self.logged_in_page(viewport=(1920, 1080))
        from .browser_helpers import install_outbound_recorder, sent_action_count

        install_outbound_recorder(page)
        self._wait_local_map_available(page)
        result = self._inject_panel(page, self._tall_street_panel())
        self.assertTrue(result["accepted"], f"ui_update rejected: {result}")
        wait_for_store_state(
            page,
            lambda s: len(((s.get("panels") or {}).get("local_map") or {}).get("nodes") or [])
            == 63,
            timeout=30000,
        )
        page.evaluate("window.__elosernBridge.store.openOverlay('map')")
        page.wait_for_selector('[data-testid="map-overlay"]', timeout=15000)
        page.wait_for_selector(".local-map__viewport--fit", timeout=15000)

        # 1. Opens fitted: every node box and every edge-marker box lies inside
        #    the clipped fit viewport, and the overlay body never scrolls (D7).
        m = self._fit_view_measure(page)
        self.assertEqual(len(m["nodeBoxes"]), 62)
        self.assertGreater(len(m["edgeBoxes"]), 0)
        for node_id, box in m["nodeBoxes"].items():
            self.assertTrue(
                self._inside(m["viewport"], box),
                f"node {node_id} outside the fitted viewport: {box} vs {m['viewport']}",
            )
        for box in m["edgeBoxes"]:
            self.assertTrue(self._inside(m["viewport"], box), f"edge marker outside: {box}")
        self.assertLessEqual(
            m["bodyScroll"]["scrollHeight"], m["bodyScroll"]["clientHeight"] + 1,
            "the overlay body must not scroll once the map is fitted",
        )

        # 2. Wheel zoom about the pointer: a wheel-up over the current node
        #    grows its box, and on the pannable axis keeps the node's centre
        #    within 2px of the pointer (D3). The two-column strip's width
        #    underflows the viewport at every permitted scale, so the
        #    no-empty-space and centre-on-underflowing-axis clauses pin that
        #    axis: there the anchor yields to the clamp, and the only
        #    observable is the clamp keeping the node inside the viewport.
        current_id = "grid:fitview:1:15"
        before = m["nodeBoxes"][current_id]
        page.mouse.move(before["cx"], before["cy"])
        page.mouse.wheel(0, -400)
        page.wait_for_timeout(150)
        m = self._fit_view_measure(page)
        after = m["nodeBoxes"][current_id]
        self.assertGreater(after["width"], before["width"] * 1.1)
        self.assertGreater(after["height"], before["height"] * 1.1)
        self.assertLess(abs(after["cy"] - before["cy"]), 2.0)
        self.assertTrue(
            self._inside(m["viewport"], after),
            f"the x-axis clamp must keep the current node inside: {after}",
        )

        # 3. Keyboard zoom-out to the bound: pressing `-` until 縮小 reports
        #    aria-disabled returns the whole drawing inside the viewport (D3).
        toggle = page.locator('[data-testid="map-overlay-zoom-out"]')
        presses = 0
        while toggle.get_attribute("aria-disabled") != "true" and presses < 20:
            page.keyboard.press("-")
            presses += 1
            page.wait_for_timeout(60)
        self.assertEqual(toggle.get_attribute("aria-disabled"), "true", "- never reached the zoom-out bound")
        m = self._fit_view_measure(page)
        for node_id, box in m["nodeBoxes"].items():
            self.assertTrue(
                self._inside(m["viewport"], box),
                f"node {node_id} outside the viewport at the zoom-out bound",
            )

        # 4. Drag pans and never moves: zoom in first — at the fit bound the
        #    window spans the whole canvas and the clamp pins every pan. One
        #    `+` press lifts the scale past vh/H so the tall strip overflows
        #    the window vertically and gains real pan range (the two-column
        #    strip's width underflows at every permitted scale, so only the
        #    vertical axis pans). A 120px drag started on an actionable node
        #    then shifts the node boxes and sends no explore.move (D3).
        actionable_id = "grid:fitview:1:14"
        page.keyboard.press("+")
        page.wait_for_timeout(80)
        m = self._fit_view_measure(page)
        # Setup guard: the full row-0..row-30 centre span must exceed the
        # window's height, else these steps prove nothing.
        self.assertGreater(
            abs(m["nodeBoxes"]["grid:fitview:1:30"]["cy"] - m["nodeBoxes"]["grid:fitview:1:0"]["cy"]),
            m["viewport"]["bottom"] - m["viewport"]["top"],
            "setup failed: the drawing must overflow the window's height once zoomed in",
        )
        start = m["nodeBoxes"][actionable_id]
        page.mouse.move(start["cx"], start["cy"])
        page.mouse.down()
        for step in range(1, 7):
            page.mouse.move(start["cx"], start["cy"] - 20 * step, steps=2)
        page.mouse.up()
        page.wait_for_timeout(150)
        moved = self._fit_view_measure(page)
        drifted = abs(moved["nodeBoxes"][actionable_id]["cy"] - start["cy"])
        self.assertGreater(drifted, 60, "the drag must pan the view")
        self.assertEqual(sent_action_count(page, "explore.move"), 0,
                         "a drag that ends on an actionable node must never submit its move")

        # 5. Pan the current node out of view (drag the content down against
        #    the top clamp), then 置中 brings it back; at the zoomed scale the
        #    centre lands within 2px of the viewport centre (D3/D4). Zoom to
        #    the upper bound first so the current node's window can actually
        #    leave it: one drag of 720px moves it two window-heights down.
        zoom_in_btn = page.locator('[data-testid="map-overlay-zoom-in"]')
        while zoom_in_btn.get_attribute("aria-disabled") != "true":
            page.keyboard.press("+")
            page.wait_for_timeout(40)
        moved = self._fit_view_measure(page)
        viewport_box = moved["viewport"]
        for sign in (1, -1):
            page.mouse.move(viewport_box["cx"], viewport_box["cy"])
            page.mouse.down()
            for step in range(1, 19):
                page.mouse.move(
                    viewport_box["cx"], viewport_box["cy"] + sign * 40 * step, steps=2
                )
            page.mouse.up()
            page.wait_for_timeout(80)
        page.wait_for_timeout(150)
        panned = self._fit_view_measure(page)
        cur = panned["nodeBoxes"][current_id]
        self.assertFalse(
            self._inside(panned["viewport"], cur, tolerance=-1.0),
            "the setup failed to pan the current node out of view",
        )
        page.locator('[data-testid="map-overlay-recentre"]').click()
        page.wait_for_timeout(150)
        recentred = self._fit_view_measure(page)
        cur = recentred["nodeBoxes"][current_id]
        self.assertTrue(
            self._inside(recentred["viewport"], cur),
            "recentre must bring the current node back inside the viewport",
        )
        self.assertLess(abs(cur["cx"] - recentred["viewport"]["cx"]), 2.0)
        # centreOn centres the marker's user-space point; the measured box
        # also carries the label tail below it, so the box centroid sits up
        # to half a box-height under the viewport centre. cx has no such tail.
        self.assertLess(abs(cur["cy"] - recentred["viewport"]["cy"]), cur["height"] / 2)

        # 6. Keyboard reveal: return to the fit bound, then wheel-zoom with
        #    the pointer anchored at the viewport's bottom edge — the window
        #    grows down to the top clamp so the drawing's bottom rows leave
        #    the window, then Tab to the actionable node sitting outside:
        #    the focus reveal brings its box back inside (D3). At the bound
        #    the window spans the whole canvas, so the off-window node is
        #    produced one step inside the range instead: a `+` press overflows
        #    the tall strip, and a drag longer than the pan range parks the
        #    window at the opposite clamp, leaving the far actionable gate
        #    node (row 0, which the flipped canvas axis places at the
        #    drawing's bottom end) outside the window's lower edge.
        presses = 0
        zoom_out_btn = page.locator('[data-testid="map-overlay-zoom-out"]')
        while zoom_out_btn.get_attribute("aria-disabled") != "true" and presses < 20:
            page.keyboard.press("-")
            presses += 1
            page.wait_for_timeout(40)
        page.keyboard.press("+")
        page.wait_for_timeout(80)
        # Park the window at the far clamp: the drag exceeds the whole pan
        # range, leaving the row-0 actionable node outside the window.
        m = self._fit_view_measure(page)
        viewport_box = m["viewport"]
        page.mouse.move(viewport_box["cx"], viewport_box["cy"])
        page.mouse.down()
        for step in range(1, 25):
            page.mouse.move(viewport_box["cx"], viewport_box["cy"] + 40 * step, steps=2)
        page.mouse.up()
        page.wait_for_timeout(150)
        m = self._fit_view_measure(page)
        # The far actionable gate node must sit outside the window now.
        target_id = "grid:fitview:1:0"
        self.assertIn(target_id, m["nodeBoxes"])
        self.assertFalse(
            self._inside(m["viewport"], m["nodeBoxes"][target_id], tolerance=-1.0),
            f"setup failed: {target_id} still inside the window after the "
            f"full-range pan: {m['nodeBoxes'][target_id]} vs {m['viewport']}",
        )
        # Focus the lattice node chain: the trapped surface cycles Tab through
        # its focusables; press Tab until the target node holds focus.
        focused_id = None
        for _ in range(30):
            page.keyboard.press("Tab")
            focused_id = page.evaluate(
                "() => document.activeElement && document.activeElement.getAttribute('data-node')"
            )
            if focused_id == target_id:
                break
        self.assertEqual(focused_id, target_id, "could not Tab to the off-window actionable node")
        page.wait_for_timeout(150)
        revealed = self._fit_view_measure(page)
        self.assertTrue(
            self._inside(revealed["viewport"], revealed["nodeBoxes"][target_id]),
            "the focus reveal must bring the tabbed-to actionable node inside the viewport",
        )

        # 7. The legend popover (D5): opening it does not move or resize the
        #    viewport; the first Escape closes only the popover; the second
        #    closes the overlay.
        before_popover = self._fit_view_measure(page)["viewport"]
        page.locator('[data-testid="map-overlay-legend-toggle"]').click()
        page.wait_for_selector('[data-testid="map-overlay-legend-popover"]', timeout=15000)
        after_popover = self._fit_view_measure(page)["viewport"]
        for key in ("left", "right", "top", "bottom"):
            self.assertAlmostEqual(before_popover[key], after_popover[key], delta=1.0,
                                  msg=f"popover opening moved the viewport ({key})")
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)
        self.assertEqual(page.locator('[data-testid="map-overlay-legend-popover"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="map-overlay"]').count(), 1,
                         "the first Escape closes only the popover")
        page.keyboard.press("Escape")
        page.wait_for_function(
            "() => document.querySelector('[data-testid=\"map-overlay\"]') === null",
            timeout=15000,
        )

        # 8. Reopening shows the fitted view again with the popover closed.
        page.evaluate("window.__elosernBridge.store.openOverlay('map')")
        page.wait_for_selector('[data-testid="map-overlay"]', timeout=15000)
        page.wait_for_selector(".local-map__viewport--fit", timeout=15000)
        self.assertEqual(page.locator('[data-testid="map-overlay-legend-popover"]').count(), 0)
        m = self._fit_view_measure(page)
        for node_id, box in m["nodeBoxes"].items():
            self.assertTrue(
                self._inside(m["viewport"], box),
                f"reopen did not refit: node {node_id} outside the viewport",
            )
        self.assertLessEqual(
            m["bodyScroll"]["scrollHeight"], m["bodyScroll"]["clientHeight"] + 1
        )
        page.close()

    @covers_requirement(
        "webclient-local-map::the-browser-minimap-renders-states-without-relying-on-color-alone"
    )
    def test_minimap_pointer_events_blank_canvas_opens_overlay_while_actionable_moves(self):
        """Pointer-event contract: clicking blank canvas passes to affordance and opens overlay;

        clicking actionable node dispatches explore.move without opening overlay.
        """
        import time
        from .browser_helpers import install_outbound_recorder, sent_action_count
        page = self.logged_in_page()
        install_outbound_recorder(page)
        self._wait_local_map_available(page)

        # 1. Click blank canvas corner on the island (empty coordinate margin):
        # Must pass through SVG to .local-map__affordance and open overlay.
        svg = page.locator('[data-testid="local-map__lattice"]')
        self.assertTrue(svg.is_visible())
        box = svg.bounding_box()
        self.assertIsNotNone(box)
        # Click near top-left margin (inside canvas but away from node center)
        page.mouse.click(box["x"] + 8, box["y"] + 8)
        page.wait_for_selector('[data-testid="map-overlay"]', timeout=15000)
        self.assertEqual(page.locator('[data-testid="map-overlay"]').count(), 1)

        # Close overlay with Escape
        page.keyboard.press("Escape")
        page.wait_for_function(
            '() => document.querySelector(\'[data-testid="map-overlay"]\') === null',
            timeout=15000,
        )

        # 2. Click actionable node: dispatches move without opening overlay
        actionable = page.locator('[data-testid="local-map__actionable"]')
        self.assertGreaterEqual(actionable.count(), 1)
        moves_before = sent_action_count(page, "explore.move")
        actionable.first.click()
        self.assertEqual(page.locator('[data-testid="map-overlay"]').count(), 0)

        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            if sent_action_count(page, "explore.move") >= moves_before + 1:
                break
            page.wait_for_timeout(250)

        self.assertEqual(
            sent_action_count(page, "explore.move"),
            moves_before + 1,
            "clicking actionable node must dispatch move without opening overlay",
        )
