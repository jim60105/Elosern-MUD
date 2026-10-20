"""Drawer content acceptance (webclient-drawer-content-polish): honest art
placement and the party window's 狀態 hero, the shared empty guidance giving way
to an unavailable reason, and lineage rows identified by their supplied root
names with progress beside them.

Every surface is driven by injected, schema-valid panels through the store's
own ``receive`` path, so the checks exercise the real client layout.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    inject_update,
    valid_character_panel,
    valid_local_map_panel,
    valid_lore_codex_panel,
    valid_status_panel,
)
from ._journey_support import _inject_snapshot, _wait_mode


def _open_drawer(page, name):
    page.evaluate(
        "(name) => { const s = window.__elosernBridge && window.__elosernBridge.store; if (s) s.openHudDrawer(name); }",
        name,
    )
    page.wait_for_selector(f'[data-testid="hud-drawer"][data-drawer-key="{name}"]', timeout=15000)


def _close_drawer(page):
    page.evaluate(
        "() => { const s = window.__elosernBridge && window.__elosernBridge.store; if (s) s.closeHudDrawer(); }"
    )
    page.wait_for_function(
        "() => document.querySelector('[data-testid=\"hud-drawer\"]') === null", timeout=15000
    )


_ART_PROBE = """() => {
  const drawer = document.querySelector('[data-testid="hud-drawer"]');
  const workspace = drawer.querySelector('.hud-drawer__workspace').getBoundingClientRect();
  const art = drawer.querySelector('.hud-drawer__art');
  const body = drawer.querySelector('.hud-drawer__body').getBoundingClientRect();
  return {
    workspaceWidth: workspace.width,
    artWidth: art ? art.getBoundingClientRect().width : null,
    artText: art ? art.innerText.trim() : null,
    bodyWidth: body.width,
  };
}"""

def _commander_party_panel() -> dict:
    """A committed party v3 panel of the commander alone, the viewed member."""
    return {
        "schema_version": 3,
        "available": True,
        "general_quota": {"used": 0, "limit": 4},
        "viewed_member_id": 42,
        "slots": [{
            "identity": 42, "display_name": "燼行者", "portrait_ref": None,
            "hp_current": 100, "hp_maximum": 100, "mp_current": 50, "mp_maximum": 50,
            "sp_current": 40, "sp_maximum": 40, "role": "commander", "knocked_out": False,
            "unread": False, "bond_stage": None, "membership": None,
        }],
    }


_LINEAGE_NODE = {
    "owned": True, "usable": True, "ready": False, "level": 1,
    "xp_into_level": 3.0, "xp_to_next_level": 7.0, "capped": False,
    "prereq_text_zh": "", "depth": 0,
}


def _same_label_lineage_panel() -> dict:
    """Two fixture-authored graphs that share the element label 燼 but carry
    distinct root-node display names (the client resolves nothing)."""
    def graph(key, name, owned, total):
        return {
            "graph_id": key,
            "group_label_zh": "燼",
            "root_keys": [key],
            "owned_count": owned,
            "total_count": total,
            "consumed": False,
            "nodes": [{"skill_key": key, "display_name_zh": name, **_LINEAGE_NODE}],
            "edges": [],
        }
    return {
        "schema_version": 2,
        "available": True,
        "kind": "lineage",
        "completed_count": 0,
        "total_count": 2,
        "graphs": [
            graph("t_content_root_arrow", "燼影箭", 1, 3),
            graph("t_content_root_burst", "燼心爆", 2, 4),
        ],
    }


class DrawerContentBrowserTest(BrowserAcceptanceTest):
    """Drawer content hierarchy on the shared managed server."""

    @covers_requirement(
        "webclient-contextual-hud::drawer-art-and-identity-match-the-subject",
        "webclient-party-window::the-status-tab-shows-true-values-with-a-trait-waterfall",
    )
    def test_status_opens_the_party_window_hero_and_no_drawer_stands_art(self):
        """The 狀態 opener opens the party window on its 狀態 tab, whose hero
        names the viewed member with the supplied title and guild rank; the
        quest and codex drawers carry no art and use the whole workspace
        width (webclient-party-status-tab)."""
        for viewport in ((1451, 790), (2560, 1440)):
            with self.subTest(viewport=viewport):
                page = self.logged_in_page(viewport)
                _inject_snapshot(
                    page,
                    {
                        "local_map": valid_local_map_panel(),
                        "status": valid_status_panel("燼行者", "42"),
                        "character": valid_character_panel(member_id=42, full_title="見習冒險者　灰燼旅人"),
                        "party": _commander_party_panel(),
                        "lore_codex": valid_lore_codex_panel(),
                    },
                    mode="exploration",
                )
                _wait_mode(page, "exploration")

                page.evaluate(
                    "() => { const s = window.__elosernBridge && window.__elosernBridge.store; if (s) s.openHudDrawer('status'); }"
                )
                page.wait_for_selector('[data-testid="party-status-tab"]', timeout=15000)
                self.assertEqual(
                    page.locator('[data-testid="hud-drawer"]').get_attribute("data-drawer-key"), "party"
                )
                self.assertIsNone(page.evaluate(_ART_PROBE)["artWidth"], "the party window stands no art column")
                hero = page.locator('[data-testid="party-status-tab__hero"]')
                self.assertEqual(hero.locator('[data-testid="party-status-tab__name"]').inner_text(), "燼行者")
                self.assertEqual(
                    hero.locator('[data-testid="party-status-tab__title"]').inner_text(),
                    "見習冒險者　灰燼旅人",
                )
                self.assertEqual(
                    hero.locator('[data-testid="party-status-tab__guild"] [role="img"]').get_attribute("aria-label"),
                    "公會階級 銀牌",
                )
                self.assertIn("120", hero.locator('[data-testid="party-status-tab__merit"]').inner_text())
                # The true trait and its waterfall are on screen; the gauges
                # carry their numbers.
                self.assertEqual(
                    page.locator('[data-testid="party-status-tab__effective--magic_power"]').inner_text(), "27"
                )
                self.assertIn(
                    "100 / 100", page.locator('[data-testid="party-status-tab__gauge--hp"]').inner_text()
                )
                _close_drawer(page)

                for name in ("quest", "lore"):
                    _open_drawer(page, name)
                    probe = page.evaluate(_ART_PROBE)
                    self.assertIsNone(probe["artWidth"], f"the {name} drawer carries no art column")
                    self.assertGreaterEqual(probe["bodyWidth"], probe["workspaceWidth"] - 1)
                    _close_drawer(page)
                page.close()

    @covers_requirement("webclient-contextual-hud::empty-drawer-guidance-preserves-unavailable-reasons")
    @covers_requirement(
        "webclient-quest-drawer::the-quest-drawer-degrades-honestly",
        "webclient-quest-drawer::the-quest-book-shows-one-quest-state-at-a-time",
    )
    def test_empty_quest_guidance_gives_way_to_the_unavailable_reason(self):
        """An available empty quest book shows the shared guidance card; a
        committed unavailable panel replaces it with its registry reason."""
        page = self.logged_in_page()
        _inject_snapshot(
            page,
            {"local_map": valid_local_map_panel(), "quest_log": {"schema_version": 2, "available": True, "rows": []}},
            mode="exploration",
        )
        _wait_mode(page, "exploration")
        _open_drawer(page, "quest")
        empty = page.locator('[data-testid="quest-drawer__empty"]')
        empty.wait_for(timeout=15000)
        self.assertEqual(empty.locator(".empty-state__headline").inner_text(), "這裡還沒有任務。")
        self.assertEqual(empty.locator("button").count(), 0)

        inject_update(page, {
            "quest_log": {
                "schema_version": 2,
                "available": False,
                "reason": {"code": "quest_log_unavailable", "message": "任務簿目前無法顯示"},
            },
        })
        page.wait_for_selector('[data-testid="quest-drawer__unavailable"]', timeout=15000)
        self.assertEqual(page.locator('[data-testid="quest-drawer__empty"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="quest-drawer"] .empty-state').count(), 0)
        self.assertEqual(
            page.locator('[data-testid="quest-drawer__unavailable"]').inner_text().strip(), "任務簿目前無法顯示"
        )
        self.assertEqual(page.locator('[data-testid^="quest-drawer__row--"]').count(), 0)
        _close_drawer(page)

        # The codex with nothing discovered shares the same guidance form.
        codex = valid_lore_codex_panel()
        for category in codex["categories"]:
            category["entries"] = []
            category["count"] = 0
        codex["discovered_total"] = 0
        inject_update(page, {"lore_codex": codex})
        _open_drawer(page, "lore")
        empty = page.locator('[data-testid="lore-codex-drawer__empty"]')
        empty.wait_for(timeout=15000)
        self.assertEqual(empty.locator(".empty-state__headline").inner_text(), "尚未發現任何條目")
        self.assertEqual(empty.locator(".empty-state__glyph").get_attribute("aria-hidden"), "true")
        self.assertEqual(page.locator('[data-testid="lore-codex-drawer__unavailable"]').count(), 0)
        page.close()

    @covers_requirement("webclient-contextual-hud::lineage-identity-and-inventory-rarity-use-backed-fields")
    def test_same_label_lineage_rows_carry_their_root_names_beside_counts(self):
        """Two graphs sharing an element label read apart by their supplied
        root names under one heading of the party window's 系譜 tab, each
        compact row keeping its owned/total count in the shared end column
        and rendering no chain meter (webclient-party-lineage-tab)."""
        page = self.logged_in_page((1451, 790))
        _inject_snapshot(
            page,
            {"party": _commander_party_panel(), "lineage": _same_label_lineage_panel()},
            mode="exploration",
        )
        _wait_mode(page, "exploration")
        page.locator('[data-nav-slot="party"]').focus()
        page.keyboard.press("l")
        page.wait_for_selector('[data-testid="party-lineage-tab"]', timeout=15000)
        self.assertEqual(
            page.locator('[data-testid="party-lineage-tab__group-label"]').all_inner_texts(), ["燼"]
        )
        rows = page.evaluate(
            """() => Array.from(document.querySelectorAll('[data-testid="party-lineage-tab__row"]')).map((row) => {
                const count = row.querySelector('[data-testid="party-lineage-tab__count"]').getBoundingClientRect();
                return {
                    root: row.querySelector('[data-testid="party-lineage-tab__row-name"]').textContent.trim(),
                    count: row.querySelector('[data-testid="party-lineage-tab__count"]').textContent.trim(),
                    height: row.getBoundingClientRect().height,
                    countRight: Math.round(count.right),
                    meters: row.querySelectorAll('.lineage-chain__meter').length,
                };
            })"""
        )
        self.assertEqual([r["root"] for r in rows], ["燼影箭", "燼心爆"])
        self.assertEqual([r["count"] for r in rows], ["1 / 3", "2 / 4"])
        self.assertEqual(len({r["countRight"] for r in rows}), 1, rows)
        for row in rows:
            self.assertLessEqual(row["height"], 72, row)
            self.assertEqual(row["meters"], 0, row)
        page.close()
