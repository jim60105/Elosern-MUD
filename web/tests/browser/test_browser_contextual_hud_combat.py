"""Contextual HUD combat-surface acceptance (webclient-contextual-hud): the participant frame, the bounded skill master-detail, and the two-step destructive confirmation.
"""

from __future__ import annotations

from tools.spec_traceability import covers_requirement
from .browser_base import BrowserAcceptanceTest
from .browser_helpers import (
    focus_action_dock,
    install_outbound_recorder,
    inject_snapshot,
    outbound_messages,
    sent_action_count,
    store_state,
    valid_character_panel,
    valid_lore_codex_panel,
    valid_local_map_panel,
    valid_status_panel,
    wait_for_store_state,
)
from ._journey_support import (
    _combat_panel,
    _art_panel,
    _inject_snapshot,
    _wait_mode,
    _press,
    _dock_depth,
)


class ContextualHudBrowserTest(BrowserAcceptanceTest):
    """Contextual HUD action-dock behavior on the shared managed server."""
    @covers_requirement(
        "webclient-contextual-hud::combat-figures-carry-glance-plates",
        "webclient-contextual-hud::combat-identity-and-status-remain-legible-without-changing-authority",
    )
    def test_combat_figure_plates_present_the_drawn_participants(self):
        """Each drawn figure but the controlled one carries its plate; no roster renders.

        webclient-combat-formation replaced the participant frame with one
        glance plate per drawn non-controlled figure in the stage's `plates`
        layer. The frame's assertions (both sides from the committed rows,
        tokens, names, numerals, no portrait strip, nothing on actor-right
        but decorative foes) move to the plates: each foe's plate states its
        name, its side and its numerals as text, the session token rides its
        accessible name, and no roster or numbers panel remains anywhere.
        """
        page = self.logged_in_page()
        _inject_snapshot(
            page,
            {
                "context_actions": _combat_panel(),
                "art": _art_panel(["1", "2"]),
            },
            mode="combat",
        )
        _wait_mode(page, "combat")

        self.assertEqual(page.locator('[data-testid="participant-frame"]').count(), 0, "no roster renders")
        self.assertFalse(page.locator('[data-anchor="map"]').is_visible(), "the map anchor is hidden in combat")

        plates = page.locator('[data-anchor="plates"] [data-testid="figure-plate"]')
        plates.first.wait_for(state="visible", timeout=15000)
        # Only the controlled player is drawn on the party side (no party
        # panel), so its values stay in the vitals dock and the two active
        # foes carry the plates, in presenter order.
        self.assertEqual(plates.count(), 2)
        labels = [plates.nth(i).get_attribute("aria-label") for i in range(plates.count())]
        self.assertEqual(labels, ["哥布林 e1，敵方，生命 60/60", "史萊姆 e2，敵方，生命 30/30"])
        self.assertEqual(
            [plates.nth(i).get_attribute("data-side") for i in range(plates.count())], ["foes", "foes"]
        )
        # The visible reading: the name, then the numerals (current / max).
        first = plates.nth(0)
        self.assertIn("哥布林", first.locator(".figure-plate__name").inner_text())
        self.assertEqual("".join(first.locator('[data-testid="figure-plate-readout"]').text_content().split()), "60/60")
        # No token shows while the names differ.
        self.assertEqual(page.locator('[data-testid="figure-plate-token"]').count(), 0)
        # The layer is one tab stop (the group 戰場, webclient-combat-figure-plates):
        # nothing inside it is in the tab order, and it takes no pointer events.
        layer = page.locator('[data-anchor="plates"]')
        self.assertEqual(layer.get_attribute("role"), "group")
        self.assertEqual(layer.get_attribute("tabindex"), "0")
        self.assertEqual(
            layer.evaluate(
                "(el) => [...el.querySelectorAll('button, a, input, textarea, select, [tabindex]')]"
                ".filter((n) => n.tabIndex >= 0).length"
            ),
            0,
        )
        self.assertEqual(layer.evaluate("(el) => getComputedStyle(el).pointerEvents"), "none")

        # actor-right holds only the foe line-up's decorative actors.
        right = page.locator('[data-anchor="actor-right"]')
        self.assertEqual(right.locator('[data-testid="foe-lineup"]').count(), 1)
        self.assertEqual(right.locator('[data-testid="foe-slot"]').count(), 2)
        self.assertNotIn("/", right.inner_text(), "actor-right states no hit-point numerals")
        self.assertEqual(
            page.locator('[data-testid="art-panel"]').count(),
            0,
            "no separate portrait strip renders",
        )

    @covers_requirement("webclient-contextual-hud::combat-details-follow-the-active-command-frame")
    @covers_requirement("webclient-combat-menu::the-combat-action-dock-follows-the-approved-keyboard-hierarchy")
    def test_command_window_scrolls_its_rows_and_details_the_current_frame(self):
        """At 1451x790 the vertical combat list walks with Up/Down, keeps its
        last row reachable above the legend, and details only the current
        frame's highlighted row (webclient-combat-command-window)."""
        page = self.logged_in_page((1451, 790))
        install_outbound_recorder(page)
        _inject_snapshot(page, {"context_actions": _combat_panel()}, mode="combat")
        _wait_mode(page, "combat")
        focus_action_dock(page)

        def focus_key():
            return store_state(page)["focus"]["key"]

        # Horizontal keys are no-ops on the vertical root.
        _press(page, "ArrowRight")
        self.assertEqual(focus_key(), "attack")
        self.assertIn("選擇一名目標", page.locator('[data-testid="combat-detail"]').inner_text())

        # Walk to the last row: it is scrolled into view inside the list,
        # above the unchanged legend strip, and the page itself never scrolls.
        legend_before = page.locator('[data-testid="action-dock-description"]').bounding_box()
        for _ in range(6):
            _press(page, "ArrowDown")
        self.assertEqual(focus_key(), "forfeit")
        geometry = page.evaluate(
            """() => {
              const list = document.querySelector('#action-dock [data-testid="dock-menu"]');
              const row = list.querySelector('[data-item-key="forfeit"]').getBoundingClientRect();
              const box = list.getBoundingClientRect();
              const legend = document.querySelector('[data-testid="action-dock-description"]').getBoundingClientRect();
              return { rowTop: row.top, rowBottom: row.bottom, listTop: box.top, listBottom: box.bottom,
                       legendTop: legend.top, page: document.scrollingElement.scrollTop };
            }"""
        )
        self.assertGreaterEqual(geometry["rowTop"], geometry["listTop"] - 1, geometry)
        self.assertLessEqual(geometry["rowBottom"], geometry["listBottom"] + 1, geometry)
        self.assertLessEqual(geometry["rowBottom"], geometry["legendTop"], geometry)
        self.assertEqual(geometry["page"], 0)
        legend_after = page.locator('[data-testid="action-dock-description"]').bounding_box()
        self.assertEqual(round(legend_after["y"]), round(legend_before["y"]), "the legend never moves")
        # Down from the last row wraps to the first.
        _press(page, "ArrowDown")
        self.assertEqual(focus_key(), "attack")

        # Open 強化術's skill frame (one sub-group), then back out: the
        # category list details the category, never the skill left behind.
        _press(page, "ArrowDown")
        _press(page, "Enter")
        _press(page, "ArrowDown")
        _press(page, "Enter")
        self.assertIn("護盾術", page.locator('[data-testid="combat-detail"]').inner_text())
        _press(page, "Escape")
        self.assertEqual(focus_key(), "skill-cat-1")
        detail = page.locator('[data-testid="combat-detail"]')
        self.assertEqual(detail.count(), 1)
        detail_text = detail.inner_text()
        self.assertIn("強化術", detail_text)
        self.assertIn("共 1 項技能", detail_text)
        self.assertNotIn("護盾術", detail_text)
        self.assertNotIn("MP", detail_text)
        self.assertEqual(sent_action_count(page), 0, "navigation submits nothing")

    @covers_requirement(
        "webclient-contextual-hud::combat-skills-are-chosen-through-a-bounded-master-detail"
    )
    def test_combat_skills_bounded_master_detail(self):
        """Combat skills are chosen through a bounded category/group/skill master-detail."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        _inject_snapshot(page, {"context_actions": _combat_panel()}, mode="combat")
        _wait_mode(page, "combat")
        focus_action_dock(page)

        # Open the Skills row (second root item) -> the category frame.
        _press(page, "ArrowDown")
        _press(page, "Enter")
        page.wait_for_timeout(150)
        self.assertEqual(_dock_depth(page), 2, "the skills tab opens the category frame")

        # The category frame lists the committed categories in panel order, each
        # carrying its own skill-descriptor count.
        pane = page.locator('[data-testid="dock-menu"]')
        pane_text = pane.inner_text()
        self.assertIn("元素魔法", pane_text, "the category frame lists the committed category labels")
        self.assertIn("強化術", pane_text)

        # Navigate to the single-group category (強化術) and open it: the skill
        # frame opens directly (no pointless single-choice group level).
        _press(page, "ArrowDown")
        _press(page, "Enter")
        page.wait_for_timeout(150)
        self.assertEqual(_dock_depth(page), 3, "the single-group category opens the skill frame directly")

        # The skill frame lists the group's descriptors over the detail strip
        # (the combat card, webclient-combat-command-card-centred),
        # which names the focused skill, its cost, description and target spec.
        detail = page.locator('[data-testid="combat-detail"]')
        self.assertEqual(detail.count(), 1, "the single-group category opens the skill frame with the detail pane")
        detail_text = detail.inner_text()
        self.assertIn("護盾術", detail_text, "the detail pane names the focused skill")
        self.assertIn("MP 8", detail_text, "the detail pane shows the skill's cost")
        self.assertIn("防禦", detail_text, "the detail pane shows the skill's description")
        self.assertIn("目標類型\n自身", detail_text, "the detail pane shows the skill's target requirement")

    @covers_requirement(
        "webclient-contextual-hud::destructive-combat-confirmation-renders-as-an-explicit-two-step-panel"
    )
    def test_destructive_combat_confirmation_two_step_panel(self):
        """Opening Surrender renders the explicit two-step confirmation card."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        _inject_snapshot(page, {"context_actions": _combat_panel()}, mode="combat")
        _wait_mode(page, "combat")
        focus_action_dock(page)

        # The combat root is one vertical list; Surrender is the last row.
        row_count = page.evaluate("document.querySelectorAll('#action-dock [data-item-key]').length")
        for _ in range(row_count - 1):
            _press(page, "ArrowDown")
        _press(page, "Enter")  # request the server-bound prompt
        page.wait_for_timeout(150)

        # Opening it submits exactly the read-only prompt request — never a
        # confirmation — and the second step is the explicit question card.
        actions = [
            args[0]
            for cmd, args, _kw in outbound_messages(page)
            if cmd == "ui_action"
        ]
        self.assertEqual([a["action_id"] for a in actions], ["combat.exit_prompt"])
        self.assertEqual(actions[0]["payload"]["operation"], "surrender")
        self.assertEqual(actions[0]["payload"]["session_id"], "browser-combat-0001")
        self.assertNotIn("confirmation_token", actions[0]["payload"])

        # The injected server prompt commits: the card states the whole
        # party's scope and the server-authored consequence, with 否 focused,
        # and the command dock beneath it is inert.
        generation = store_state(page)["generation"]
        page.evaluate(
            """([generation, rid]) => {
              const bridge = window.__elosernBridge;
              const view = bridge.store.view;
              bridge.store.receive(generation, 'ui_action_result', [{
                protocol_version: 1,
                presentation_epoch: view.epoch,
                request_id: rid,
                outcome: 'success',
                code: 'party_exit_prompt',
                message: '確認提示',
                presentation_revision: view.revision,
                data: {
                  operation: 'surrender',
                  confirmation_token: 'S-0-browsertoken9f8e7d6c',
                  scope: 'party',
                  consequence: '全隊退出戰鬥，並結算目前已累積的戰鬥時間。',
                },
              }], {});
            }""",
            [generation, actions[0]["request_id"]],
        )
        card = page.locator('[data-testid="party-exit-question"]')
        card.wait_for(state="visible", timeout=15000)
        self.assertIn(
            "確定要全隊投降？",
            card.locator('[data-testid="question-card-question"]').inner_text(),
        )
        self.assertIn(
            "全隊退出戰鬥",
            card.locator('[data-testid="question-card-detail"]').inner_text(),
        )
        self.assertEqual(
            page.evaluate(
                "() => { const el = document.activeElement; "
                "return el && el.closest('[data-testid=\"party-exit-question\"]') ? el.textContent.trim() : null; }"
            ),
            "否",
            "the safe answer holds focus",
        )
        self.assertTrue(
            page.evaluate("() => !!document.querySelector('#action-dock').closest('[inert]')"),
            "the dock is inert beneath the card",
        )

        # Escape cancels exactly like 否: no confirmation is sent, the card
        # closes, and combat continues at the row that opened it.
        _press(page, "Escape")
        card.wait_for(state="detached", timeout=15000)
        self.assertEqual(sent_action_count(page, "combat.exit_confirm"), 0)
        self.assertEqual(store_state(page)["focus"]["key"], "surrender")
        self.assertEqual(_dock_depth(page), 1)
