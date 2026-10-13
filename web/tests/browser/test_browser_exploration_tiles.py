"""Keyboard-only exploration browser acceptance (webclient-exploration-menu 4.2-4.6): a crowded room folding into the presence rail and the fixed-column nav pane's track sizing at narrow viewports.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    install_outbound_recorder,
    presence_entry_keys,
    sent_action_count,
    valid_local_map_panel,
    store_state,
    wait_for_store_state,
)
from ._journey_support import (
    _interact_target,
    _exploration_panel,
    _move_row,
    _exploration_context_actions_panel,
    _inject_snapshot,
    _wait_mode,
    _press,
)
from .harness import ManagedServer, ManagedServerTearDownMixin
from . import fixtures


class ExplorationBrowserTest(ManagedServerTearDownMixin, BrowserAcceptanceTest):
    """Boots one dedicated isolated server per test with the exploration fixture."""
    @classmethod
    def setUpClass(cls) -> None:
        pass

    def setUp(self) -> None:
        runtime = fixtures.create_runtime()
        runtime.env["ELOSERN_BROWSER_EXPLORATION"] = "1"
        # Boot mode: SHIPPED catalogs (explicit override of the harness
        # synthetic default, per the creation/action-feedback precedent).
        # These journeys assert shipped fixture identity end to end and were
        # never migrated to kit seams.
        runtime.env["ELOSERN_BROWSER_SYNTH_CATALOGS"] = "0"

        self.server = ManagedServer(runtime=runtime)
        self.server.start()
        self.base_url = f"http://127.0.0.1:{self.server.runtime.http_port}"
        self.webclient_url = self.server.runtime.webclient_url
        super().setUp()

    def _wait_exploration_available(self, page, timeout=30000):
        def _exploration_available(state: dict) -> bool:
            panel = (state.get("panels") or {}).get("exploration") or {}
            return panel.get("available") is True

        wait_for_store_state(page, _exploration_available, timeout=timeout)

    def _mount_overview(self, page, exploration: dict, suggestions: dict) -> None:
        """Commit one synthetic exploration panel and settle on the overview."""
        _inject_snapshot(
            page,
            {
                "exploration": exploration,
                "context_actions": _exploration_context_actions_panel(suggestions),
                "local_map": valid_local_map_panel(),
            },
            mode="exploration",
        )
        _wait_mode(page, "exploration")

    @covers_requirement(
        "webclient-room-actions::the-exploration-screen-roots-at-the-compass-the-rail-and-room-actions"
    )
    def test_crowded_room_folds_into_the_rail_at_a_narrow_viewport(self):
        """A crowded room at the minimum supported viewport: the dock holds no
        row (its room actions are the place card's, exploration-room-actions),
        the twelve exits stay on the compass,
        and the ten people stand on the presence rail as five medallions and
        a ``＋5`` slot (exploration-presence-rail), right-aligned on the stage
        floor above the band, left of the right-hand island column, and fully
        inside the stage. The dock pane never scrolls.
        """
        page = self.logged_in_page((1451, 790))
        install_outbound_recorder(page)
        self._wait_exploration_available(page)

        labels = ["北", "南", "東", "西", "東北", "西北", "東南", "西南", "上", "下", "櫃檯門", "後院小徑"]
        exits = [
            _move_row("e%d" % index, label, "room:%d" % (100 + index))
            for index, label in enumerate(labels)
        ]
        names = ["測試人物 %d" % index for index in range(10)]
        people = [_interact_target(700 + index, name) for index, name in enumerate(names)]
        self._mount_overview(
            page,
            _exploration_panel(people, move_rows=exits),
            {"status": "unavailable"},
        )

        keys = page.evaluate(
            "() => Array.from(document.querySelectorAll('#action-dock [data-item-key]'))"
            ".map((el) => el.getAttribute('data-item-key'))"
        )
        self.assertEqual(keys, [], "the exploration root renders no dock row")
        self.assertEqual(
            page.locator('[data-anchor="map"] [data-testid="place-card-wait"]').count(),
            1,
            "the room actions stand on the place card",
        )
        self.assertEqual(
            page.locator('#action-dock [data-testid="exit-compass-pip"], #action-dock [data-testid="exit-compass-portal"]').count(),
            len(exits),
            "every exit is a compass target",
        )
        page.wait_for_selector('[data-anchor="presence"] [data-testid="presence-rail"]', timeout=15000)
        self.assertEqual(
            presence_entry_keys(page),
            ["target-%d" % (700 + index) for index in range(5)] + ["presence-more"],
            "five medallions and the ＋N slot",
        )
        self.assertIn(
            "＋5",
            page.locator('[data-anchor="presence"] [data-entry-key="presence-more"]').inner_text(),
        )
        geometry = page.evaluate(
            """() => {
              const rect = (sel) => {
                const el = document.querySelector(sel);
                if (!el) return null;
                const r = el.getBoundingClientRect();
                return { left: r.left, top: r.top, right: r.right, bottom: r.bottom };
              };
              return {
                rail: rect('[data-anchor="presence"] [data-testid="presence-rail"]'),
                band: rect('[data-testid="stage-band"]'),
                map: rect('[data-anchor="map"]'),
                stage: rect('[data-testid="elosern-stage"]'),
              };
            }"""
        )
        rail, band, island, stage = geometry["rail"], geometry["band"], geometry["map"], geometry["stage"]
        self.assertLessEqual(rail["bottom"], band["top"] + 0.5, "the rail stands above the band")
        self.assertLessEqual(rail["right"], island["left"] + 0.5, "the rail clears the island column")
        self.assertGreaterEqual(rail["left"], stage["left"], "the rail lies inside the stage")
        self.assertLessEqual(island["left"] - rail["right"], 40.0, "the rail is right-aligned against the island column")
        # The pane itself never scrolls.
        self.assertEqual(
            page.evaluate(
                "() => { const p = document.querySelector('#action-dock .action-dock__pane');"
                " return p.scrollHeight - p.clientHeight; }"
            ),
            0,
            "the dock pane must not scroll",
        )
        self.assertEqual(sent_action_count(page), 0, "nothing was submitted")

