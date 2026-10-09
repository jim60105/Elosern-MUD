"""Drawer content acceptance (webclient-drawer-content-polish): honest art
placement and the character-status hero, the shared empty guidance giving way
to an unavailable reason, and lineage rows identified by their supplied root
names with progress beside them.

Every surface is driven by injected, schema-valid panels through the store's
own ``receive`` path, so the checks exercise the real client layout.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest, ui_scale
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

_LINEAGE_NODE = {
    "owned": True, "usable": True, "level": 1, "xp_into_level": 3.0,
    "xp_to_next_level": 7.0, "capped": False, "prereq_text_zh": "",
}


def _same_label_lineage_panel() -> dict:
    """Two fixture-authored chains that share the element label 燼 but carry
    distinct root-node display names (the client resolves nothing)."""
    def chain(key, name, meter):
        return {
            "root_skill_key": key,
            "element_or_style_zh": "燼",
            "consumed": False,
            "meter": meter,
            "nodes": [{"skill_key": key, "display_name_zh": name, **_LINEAGE_NODE}],
        }
    return {
        "schema_version": 1,
        "available": True,
        "kind": "lineage",
        "completed_count": 0,
        "total_count": 2,
        "chains": [
            chain("t_content_root_arrow", "燼影箭", 0.3),
            chain("t_content_root_burst", "燼心爆", 0.7),
        ],
    }


class DrawerContentBrowserTest(BrowserAcceptanceTest):
    """Drawer content hierarchy on the shared managed server."""

    @covers_requirement(
        "webclient-contextual-hud::drawer-art-and-identity-match-the-subject",
        "webclient-contextual-hud::the-character-status-drawer-degrades-section-by-section-and-never-substitutes-a-disguise",
    )
    def test_only_character_drawers_stand_a_bounded_portrait_beside_the_hero(self):
        """The status drawer bounds its portrait column and names the
        committed character; the quest and codex drawers carry no art and
        use the whole workspace width; the stat cards share equal tracks."""
        for viewport in ((1451, 790), (2560, 1440)):
            with self.subTest(viewport=viewport):
                page = self.logged_in_page(viewport)
                portrait_url = "/art/t_drawer_full_figure.svg"
                page.route(
                    "**" + portrait_url,
                    lambda route: route.fulfill(
                        content_type="image/svg+xml",
                        body='<svg xmlns="http://www.w3.org/2000/svg" width="300" height="1200">'
                        '<rect width="300" height="1200" fill="seagreen"/>'
                        '<rect width="300" height="100" fill="goldenrod"/></svg>',
                    ),
                )
                status = valid_status_panel("燼行者", "42")
                status["actor"]["full_title"] = "見習冒險者　灰燼旅人"
                _inject_snapshot(
                    page,
                    {
                        "local_map": valid_local_map_panel(),
                        "status": status,
                        "character": valid_character_panel(),
                        "lore_codex": valid_lore_codex_panel(),
                        "roster": {
                            "schema_version": 2,
                            "available": True,
                            "characters": [{
                                "identity": 42, "name": "燼行者", "current": True, "pending": False,
                                "portrait": {
                                    "subject_key": None, "status": "done", "url": portrait_url,
                                    "aspect_ratio": "3:4", "alt": "測試全身立繪",
                                    "placeholder": None,
                                    "face_rect": {"x": 0.25, "y": 0.0, "w": 0.5, "h": 0.1},
                                    "stage": {"scale": 0.6, "x": 0.0, "y": 0.0},
                                    "origin": "runtime",
                                },
                            }],
                            "can_create": False, "max_characters": 3,
                            "switch_locked": False, "lock_reason": None,
                        },
                    },
                    mode="exploration",
                )
                _wait_mode(page, "exploration")

                _open_drawer(page, "status")
                page.wait_for_function(
                    """() => {
                      const image = document.querySelector('.hud-drawer__art .reference-artwork--stage img');
                      return image && image.naturalWidth === 300 && image.naturalHeight === 1200;
                    }"""
                )
                # Object fitting happens before the saved transform. Recover
                # the painted bounds from the transformed box, not the box
                # alone: a cover-cropped image can have an in-bounds box.
                painted = page.evaluate(
                    """() => {
                      const art = document.querySelector('.hud-drawer__art').getBoundingClientRect();
                      const image = document.querySelector('.hud-drawer__art .reference-artwork--stage img');
                      const box = image.getBoundingClientRect();
                      const style = getComputedStyle(image);
                      const fit = (style.objectFit === 'contain' ? Math.min : Math.max)(
                        image.clientWidth / image.naturalWidth,
                        image.clientHeight / image.naturalHeight);
                      const width = image.naturalWidth * fit * box.width / image.clientWidth;
                      const height = image.naturalHeight * fit * box.height / image.clientHeight;
                      return {
                        top: box.bottom - height, bottom: box.bottom,
                        left: (box.left + box.right - width) / 2,
                        right: (box.left + box.right + width) / 2,
                        artTop: art.top, artBottom: art.bottom,
                        artLeft: art.left, artRight: art.right,
                        position: style.objectPosition,
                      };
                    }"""
                )
                self.assertEqual(painted["position"], "50% 100%")
                self.assertGreaterEqual(painted["top"], painted["artTop"] - 1, painted)
                self.assertLessEqual(painted["bottom"], painted["artBottom"] + 1, painted)
                self.assertGreaterEqual(painted["left"], painted["artLeft"] - 1, painted)
                self.assertLessEqual(painted["right"], painted["artRight"] + 1, painted)
                probe = page.evaluate(_ART_PROBE)
                # `.hud-drawer__art` is `flex: 0 0 min(360px * var(--ui-scale), 28%)`,
                # so the bound scales with the chrome factor at every size. The
                # scaled literal is rounded to a subpixel: the layout engine
                # rounds 360px * 1.4 to 504, and the float product's tail must
                # not decide the assertion.
                bound = min(
                    round(360 * ui_scale(viewport), 3),
                    0.28 * probe["workspaceWidth"],
                )
                self.assertIsNotNone(probe["artWidth"], "the status drawer stands its portrait column")
                self.assertLessEqual(probe["artWidth"], bound + 1)
                self.assertNotIn("肖像生成中", probe["artText"] or "")
                hero = page.locator('[data-testid="character-status-drawer__hero"]')
                self.assertEqual(hero.locator('[data-testid="character-status-drawer__name"]').inner_text(), "燼行者")
                self.assertEqual(
                    hero.locator('[data-testid="character-status-drawer__full-title"]').inner_text(),
                    "見習冒險者　灰燼旅人",
                )
                self.assertEqual(
                    hero.locator('[data-testid="character-status-drawer__hero-rank"]').inner_text(),
                    "公會階級 銀牌",
                )
                # The secondary openers sit in the hero's one action row (the
                # party opener joins it only while a party panel is present).
                self.assertEqual(
                    hero.locator('[role="group"] [data-testid="character-status-drawer__open-skill"]').count(), 1
                )
                # The drawer title renders once, in the shared header only.
                body_text = page.locator('[data-testid="character-status-drawer"]').inner_text()
                self.assertNotIn("角色狀態", body_text)
                # The vitals cards share equal-width tracks.
                widths = page.evaluate(
                    """() => Array.from(document.querySelectorAll(
                        '[data-testid="character-status-drawer__vitals"] .character-status-drawer__statrow'
                    )).map((el) => Math.round(el.getBoundingClientRect().width))"""
                )
                self.assertEqual(len(widths), 3)
                self.assertLessEqual(max(widths) - min(widths), 1, widths)
                _close_drawer(page)

                for name in ("quest", "lore"):
                    _open_drawer(page, name)
                    probe = page.evaluate(_ART_PROBE)
                    self.assertIsNone(probe["artWidth"], f"the {name} drawer carries no art column")
                    self.assertGreaterEqual(probe["bodyWidth"], probe["workspaceWidth"] - 1)
                    _close_drawer(page)
                page.close()

    @covers_requirement("webclient-contextual-hud::empty-drawer-guidance-preserves-unavailable-reasons")
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
        empty = page.locator('[data-testid="quest-log__empty"]')
        empty.wait_for(timeout=15000)
        self.assertEqual(empty.locator(".empty-state__headline").inner_text(), "目前沒有任務紀錄")
        self.assertEqual(empty.locator("button").count(), 0)

        inject_update(page, {
            "quest_log": {
                "schema_version": 2,
                "available": False,
                "reason": {"code": "quest_log_unavailable", "message": "任務簿目前無法顯示"},
            },
        })
        page.wait_for_selector('[data-testid="quest-log__unavailable"]', timeout=15000)
        self.assertEqual(page.locator('[data-testid="quest-log__empty"]').count(), 0)
        self.assertEqual(page.locator('[data-testid="quest-log"] .empty-state').count(), 0)
        self.assertEqual(
            page.locator('[data-testid="quest-log__unavailable"]').inner_text().strip(), "任務簿目前無法顯示"
        )
        self.assertEqual(page.locator('[data-testid^="quest-log__row--"]').count(), 0)
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
    def test_same_label_lineage_rows_carry_their_root_names_beside_progress(self):
        """Two chains sharing an element label read apart by their supplied
        root names, each compact row placing its meter (at most 320px) right
        after the shared identity column."""
        page = self.logged_in_page((1451, 790))
        _inject_snapshot(page, {"lineage": _same_label_lineage_panel()}, mode="exploration")
        _wait_mode(page, "exploration")
        page.locator('[data-testid="nav-tool-lineage"]').click()
        page.wait_for_selector('[data-testid="lineage-panel"]', timeout=15000)
        rows = page.evaluate(
            """() => Array.from(document.querySelectorAll('.lineage-chain__head')).map((head) => {
                const id = head.querySelector('.lineage-chain__identity').getBoundingClientRect();
                const meter = head.querySelector('.lineage-chain__meter').getBoundingClientRect();
                const root = head.querySelector('.lineage-chain__root');
                return {
                    root: root ? root.textContent.trim() : null,
                    height: head.getBoundingClientRect().height,
                    gap: meter.left - id.right,
                    meterWidth: meter.width,
                };
            })"""
        )
        self.assertEqual([r["root"] for r in rows], ["燼影箭", "燼心爆"])
        for row in rows:
            self.assertLessEqual(row["height"], 60, row)
            self.assertLessEqual(row["meterWidth"], 320.5, row)
            self.assertGreaterEqual(row["gap"], 0, row)
            self.assertLessEqual(row["gap"], 16.5, row)
        page.close()
