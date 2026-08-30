"""Skill-lineage big-window browser acceptance (skill-lineage-panel, task V6).

Two deterministic journeys on the shared managed server: the committed
``lineage`` panel renders its full ledger through the 技能系譜 icon (collapsed
chain meter → expanded per-node levels, 見頂 marks, XP meters, and prerequisite
lines, all read verbatim from the payload), and an unavailable payload renders
only the registry reason with no invented chain. Fixed injected snapshots; no
live LLM, Stable Diffusion, or other network service.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement

from .browser_base import BrowserAcceptanceTest
from .test_browser_contextual_hud import _inject_snapshot, _wait_mode


def _lineage_node(
    skill_key: str,
    display_name_zh: str,
    *,
    owned: bool,
    usable: bool,
    level: int,
    xp_into_level: float,
    xp_to_next_level: float,
    capped: bool,
    prereq_text_zh: str = "",
) -> dict:
    """One schema-valid lineage node (exact field set of the panel contract)."""
    return {
        "skill_key": skill_key,
        "display_name_zh": display_name_zh,
        "owned": owned,
        "usable": usable,
        "level": level,
        "xp_into_level": xp_into_level,
        "xp_to_next_level": xp_to_next_level,
        "capped": capped,
        "prereq_text_zh": prereq_text_zh,
    }


def _available_lineage_panel() -> dict:
    """A schema-valid available lineage payload: one fire chain, three nodes."""
    return {
        "schema_version": 1,
        "available": True,
        "kind": "lineage",
        "completed_count": 0,
        "total_count": 1,
        "chains": [
            {
                "root_skill_key": "fire_arrow",
                "element_or_style_zh": "火",
                "consumed": False,
                "meter": 0.3,
                "nodes": [
                    _lineage_node(
                        "fire_arrow",
                        "火焰箭",
                        owned=True,
                        usable=True,
                        level=1,
                        xp_into_level=23.0,
                        xp_to_next_level=27.0,
                        capped=False,
                    ),
                    _lineage_node(
                        "fire_ball",
                        "火球術",
                        owned=True,
                        usable=True,
                        level=3,
                        xp_into_level=0.0,
                        xp_to_next_level=0.0,
                        capped=True,
                    ),
                    _lineage_node(
                        "scorching_wave",
                        "灼熱波動",
                        owned=False,
                        usable=False,
                        level=0,
                        xp_into_level=0.0,
                        xp_to_next_level=50.0,
                        capped=False,
                        prereq_text_zh="需「火球術 Lv.3」",
                    ),
                ],
            }
        ],
    }


def _unavailable_lineage_panel() -> dict:
    """A schema-valid unavailable lineage payload (common unavailable form)."""
    return {
        "schema_version": 1,
        "available": False,
        "reason": {
            "code": "lineage_unavailable",
            "message": "技能系譜目前無法顯示",
        },
    }


class LineagePanelBrowserTest(BrowserAcceptanceTest):
    """The lineage window on the shared managed server."""

    @covers_requirement("skill-lineage-panel::the-webclient-renders-the-lineage-window-from-the-view-alone")
    def test_lineage_window_renders_the_committed_ledger_verbatim(self):
        """Icon opens the window; collapsed meter and expanded rows match the payload."""
        page = self.logged_in_page()
        _inject_snapshot(page, {"lineage": _available_lineage_panel()}, mode="exploration")
        _wait_mode(page, "exploration")

        # The 技能系譜 icon on the command line opens the big window.
        page.locator('[data-testid="command-line-lineage"]').click()
        page.wait_for_selector('[data-testid="lineage-panel"]', timeout=15000)

        # Header counts come straight from the payload.
        self.assertEqual(
            page.locator('[data-testid="lineage-panel-header"]').inner_text(),
            "已完成 0 / 1 樹",
        )

        # Collapsed by default: the chain head shows its aggregate meter only.
        toggle = page.locator('[data-testid="lineage-chain-toggle-fire_arrow"]')
        self.assertEqual(toggle.get_attribute("aria-expanded"), "false")
        self.assertEqual(
            page.locator('[data-testid="lineage-chain-meter-fire_arrow"]').get_attribute(
                "aria-label"
            ),
            "進度 30%",
        )
        self.assertEqual(
            page.locator('[data-testid="lineage-chain-nodes-fire_arrow"]').count(), 0
        )

        # Expanding renders the per-node rows with payload-owned values.
        toggle.click()
        page.wait_for_selector('[data-testid="lineage-chain-nodes-fire_arrow"]', timeout=15000)
        self.assertEqual(toggle.get_attribute("aria-expanded"), "true")
        self.assertEqual(
            page.locator('[data-testid="lineage-node-meter-fire_arrow"]').inner_text(),
            "23/50 → 下一階",
        )
        self.assertEqual(
            page.locator('[data-testid="lineage-node-tip"]').count(),
            1,
            "only the capped node carries the 見頂 mark",
        )
        self.assertIn(
            "（見頂）",
            page.locator('[data-testid="lineage-node-fire_ball"]').inner_text(),
        )
        self.assertEqual(
            page.locator('[data-testid="lineage-node-prereq-scorching_wave"]').inner_text(),
            "需「火球術 Lv.3」",
        )

        # Closing the shared overlay host retires the window.
        page.locator('[data-testid="overlay-host-close"]').click()
        page.wait_for_function(
            "() => document.querySelector('[data-testid=\"lineage-panel\"]') === null",
            timeout=15000,
        )

    @covers_requirement("skill-lineage-panel::the-webclient-renders-the-lineage-window-from-the-view-alone")
    def test_unavailable_lineage_renders_only_the_registry_reason(self):
        """The unavailable payload renders its reason line and no placeholder tree."""
        page = self.logged_in_page()
        _inject_snapshot(page, {"lineage": _unavailable_lineage_panel()}, mode="exploration")
        _wait_mode(page, "exploration")

        page.locator('[data-testid="command-line-lineage"]').click()
        page.wait_for_selector('[data-testid="lineage-panel"]', timeout=15000)
        self.assertEqual(
            page.locator('[data-testid="lineage-panel-unavailable"]').inner_text(),
            "技能系譜目前無法顯示",
        )
        self.assertEqual(
            page.locator('[data-testid^="lineage-chain-"]').count(),
            0,
            "the client invents no placeholder chain",
        )
        self.assertEqual(page.locator('[data-testid="lineage-panel-header"]').count(), 0)
