"""Handbook codex tab browser acceptance (handbook-codex-tab, task 5.2).

The 圖鑑 tool opens the 手帳 (the quest drawer) on its 圖鑑 tab, which renders
the committed ``lore_codex`` v2 panel. Each journey injects a synthetic v2
panel through the store's ``receive`` on the shared live client:

* at both reference viewports the rail, wall and detail columns fit the
  drawer body side by side, the wall never scrolls horizontally, no text is
  below ``--text-xs``, and every legend mark is ``12px × --ui-scale`` wide;
* on a monster wall large enough to overflow, the stage legend stays inside
  the wall's visible box at scroll top and at scroll bottom;
* in combat the 圖鑑 tool opens the drawer with exactly the codex and titles
  tabs.

Every key, title and field below is synthetic; the monster wall is found by
its tier-labelled group (the one category whose groups carry labels), so no
shipped category key is spelled here.
"""

from __future__ import annotations

from .browser_base import BrowserAcceptanceTest, ui_scale
from .browser_helpers import valid_lore_codex_panel
from ._journey_support import _combat_panel, _inject_snapshot, _wait_mode

CODEX = '[data-testid="handbook__codex"]'


def _monster_index(panel: dict) -> int:
    """The index of the tier-grouped category (its groups carry labels)."""
    return next(
        index
        for index, category in enumerate(panel["categories"])
        if any(group["label"] is not None for group in category["groups"])
    )


def _entry(key: str, title: str, stage: str) -> dict:
    sighted = stage == "sighted"
    card = [
        {"name": "display_name_zh", "value": title},
        {"name": "field_alpha", "value": f"{title}的合成外觀。"},
    ]
    if not sighted:
        card.append({"name": "field_beta", "value": f"{title}的合成生態。"})
    return {
        "key": key,
        "title": title,
        "stage": stage,
        "art": None,
        "card": card,
        "locked_fields": ["field_beta", "field_gamma"] if sighted else [],
    }


def _codex_panel(slots_per_tier: int = 6) -> tuple[dict, str]:
    """A valid v2 panel whose tier-grouped category holds two tiers of
    ``slots_per_tier`` slots each: a defeated and a sighted entry, then
    placeholders. Returns the panel and that category's key."""
    panel = valid_lore_codex_panel()
    index = _monster_index(panel)
    category = panel["categories"][index]
    placeholder = {"placeholder": True}
    low = [_entry("t_beast_a", "合成骨獸", "defeated"), _entry("t_beast_b", "合成霧獸", "sighted")]
    low += [dict(placeholder) for _ in range(slots_per_tier - len(low))]
    high = [dict(placeholder) for _ in range(slots_per_tier - 1)] + [_entry("t_beast_c", "合成灰獸", "sighted")]
    category["groups"] = [
        {"key": "t_tier_low", "label": "合成低階", "slots": low},
        {"key": "t_tier_high", "label": "合成高階", "slots": high},
    ]
    category["discovered"] = 3
    category["total"] = len(low) + len(high)
    panel["discovered_total"] = sum(c["discovered"] for c in panel["categories"])
    panel["total"] = sum(c["total"] for c in panel["categories"])
    return panel, category["key"]


#: Column boxes against the drawer body, the wall's horizontal overflow, the
#: smallest visible text size against the computed `--text-xs` (resolved
#: through a probe element), and the legend marks' rendered widths.
_GEOMETRY_PROBE = """
() => {
  const q = (sel) => document.querySelector(sel);
  const box = (el) => {
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height };
  };
  const codex = q('[data-testid="handbook__codex"]');
  const wall = codex.querySelector('[data-testid="handbook__codex-wall"]');
  const probe = document.createElement('span');
  probe.style.fontSize = 'var(--text-xs)';
  probe.textContent = 'x';
  codex.appendChild(probe);
  const floor = parseFloat(getComputedStyle(probe).fontSize);
  probe.remove();
  let smallest = null;
  let smallestText = null;
  const walker = document.createTreeWalker(codex, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    if (!node.textContent.trim()) continue;
    const parent = node.parentElement;
    if (!parent || parent.closest('[aria-hidden="true"]')) continue;
    const r = parent.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    const style = getComputedStyle(parent);
    if (style.visibility === 'hidden' || style.display === 'none') continue;
    const size = parseFloat(style.fontSize);
    if (smallest === null || size < smallest) {
      smallest = size;
      smallestText = node.textContent.trim();
    }
  }
  const marks = [...codex.querySelectorAll('[data-testid="handbook__codex-legend"] .codex-legend__mark')]
    .map((el) => el.getBoundingClientRect().width);
  return {
    body: box(q('[data-testid="quest-drawer"]')),
    rail: box(codex.querySelector('[data-testid="handbook__codex-rail"]')),
    wall: box(wall),
    detail: box(codex.querySelector('[data-testid="handbook__detail"]')),
    wallScroll: wall ? { scroll: wall.scrollWidth, client: wall.clientWidth } : null,
    floor,
    smallest,
    smallestText,
    marks,
  };
}
"""

#: The wall's visible box (its client area) and the legend's box, after
#: scrolling the wall to `top`, or to its end when `top` is null.
_LEGEND_PROBE = """
(top) => {
  const wall = document.querySelector('[data-testid="handbook__codex-wall"]');
  wall.scrollTop = top === null ? wall.scrollHeight : top;
  const w = wall.getBoundingClientRect();
  const l = document.querySelector('[data-testid="handbook__codex-legend"]').getBoundingClientRect();
  return {
    overflow: wall.scrollHeight - wall.clientHeight,
    scrollTop: wall.scrollTop,
    wall: { top: w.top + wall.clientTop, bottom: w.top + wall.clientTop + wall.clientHeight },
    legend: { top: l.top, bottom: l.bottom, height: l.height },
  };
}
"""


class HandbookCodexBrowserTest(BrowserAcceptanceTest):
    """The handbook codex tab on the shared managed server."""

    def _open_codex(self, page, panels: dict, mode: str = "exploration"):
        _inject_snapshot(page, panels, mode=mode)
        _wait_mode(page, mode)
        page.locator('[data-testid="nav-tool-lore"]').click()
        page.wait_for_selector(CODEX, timeout=15000)

    def _select_category(self, page, key: str):
        page.locator(f'[data-testid="handbook__codex-rail"] [data-tab-key="{key}"]').click()
        page.wait_for_selector('[data-testid="handbook__codex-legend"]', timeout=15000)
        # Let the detail column's entrance animation settle.
        page.evaluate("() => Promise.all(document.getAnimations().map((a) => a.finished))")

    def test_codex_tab_geometry_at_reference_viewports(self):
        """Three columns fit the drawer body, no horizontal scroll, no tiny
        text, and fixed-size legend marks."""
        for viewport in ((1451, 790), (2560, 1440)):
            with self.subTest(viewport=viewport):
                page = self.logged_in_page(viewport)
                panel, monster = _codex_panel()
                self._open_codex(page, {"lore_codex": panel})
                self._select_category(page, monster)
                page.wait_for_selector(f'{CODEX} [data-testid="handbook__detail"]', timeout=15000)
                fit = page.evaluate(_GEOMETRY_PROBE)
                body = fit["body"]
                for name in ("rail", "wall", "detail"):
                    column = fit[name]
                    self.assertIsNotNone(column, name)
                    self.assertGreater(column["width"], 0, name)
                    self.assertGreaterEqual(column["left"], body["left"] - 1, f"{name} left of the body")
                    self.assertLessEqual(column["right"], body["right"] + 1, f"{name} right of the body")
                    self.assertGreaterEqual(column["top"], body["top"] - 1, f"{name} above the body")
                    self.assertLessEqual(column["bottom"], body["bottom"] + 1, f"{name} below the body")
                # Side by side, in order, without overlap.
                self.assertLessEqual(fit["rail"]["right"], fit["wall"]["left"] + 1)
                self.assertLessEqual(fit["wall"]["right"], fit["detail"]["left"] + 1)
                self.assertLessEqual(fit["wallScroll"]["scroll"], fit["wallScroll"]["client"], "the wall scrolls horizontally")
                self.assertGreaterEqual(
                    fit["smallest"], fit["floor"] - 0.01, f"text below --text-xs: {fit['smallestText']!r}"
                )
                self.assertEqual(len(fit["marks"]), 3, "the legend carries three marks")
                expected = 12 * ui_scale(viewport)
                for width in fit["marks"]:
                    self.assertAlmostEqual(width, expected, delta=1, msg=f"legend mark width at {viewport}")
                page.close()

    def test_monster_legend_stays_pinned_while_tiles_scroll(self):
        """On an overflowing monster wall the legend lies inside the wall's
        visible box at scroll top and at scroll bottom."""
        page = self.logged_in_page((1451, 790))
        panel, monster = _codex_panel(slots_per_tier=48)
        self._open_codex(page, {"lore_codex": panel})
        self._select_category(page, monster)
        for top in (0, None):
            probe = page.evaluate(_LEGEND_PROBE, top)
            self.assertGreater(probe["overflow"], 0, "the synthetic wall overflows")
            if top is None:
                self.assertGreater(probe["scrollTop"], 0, "the wall scrolled to its end")
            self.assertGreater(probe["legend"]["height"], 0)
            self.assertGreaterEqual(probe["legend"]["top"], probe["wall"]["top"] - 1, f"legend above the wall at {top}")
            self.assertLessEqual(probe["legend"]["bottom"], probe["wall"]["bottom"] + 1, f"legend below the wall at {top}")
        page.close()

    def test_codex_tool_opens_the_codex_tab_in_combat(self):
        """In combat the 圖鑑 tool opens the handbook with exactly the codex
        and titles tabs, on the codex tab."""
        page = self.logged_in_page()
        panel, _ = _codex_panel()
        self._open_codex(page, {"context_actions": _combat_panel(), "lore_codex": panel}, mode="combat")
        tabs = page.evaluate(
            "() => [...document.querySelectorAll('[data-testid=\"quest-drawer__top-tabs\"] [role=\"tab\"]')]"
            ".map((tab) => tab.getAttribute('data-tab-key'))"
        )
        self.assertEqual(tabs, ["codex", "titles"])
        self.assertEqual(page.locator('[data-testid="quest-drawer"]').get_attribute("data-tab"), "codex")
        page.close()
