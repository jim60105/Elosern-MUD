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
        "webclient-contextual-hud::the-combat-participant-frame-presents-the-session-s-participants-and-their-portraits"
    )
    def test_combat_participant_frame_presents_participants_and_portraits(self):
        """The combat participant frame presents the session's participants and portraits."""
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

        frame = page.locator('[data-testid="participant-frame"]')
        self.assertEqual(frame.count(), 1, "the participant frame mounts in the HUD area")
        self.assertTrue(frame.is_visible())

        # Both sides render from the committed participants, in presenter order.
        frame_text = frame.inner_text()
        self.assertIn("我方", frame_text, "the player's side renders")
        self.assertIn("敵方", frame_text, "the opposing side renders")
        self.assertIn("a1", frame_text, "the participant token renders")
        self.assertIn("勇者", frame_text, "the participant display name renders")
        self.assertIn("100/100", frame_text, "the current/maximum HP render as numerals")
        # A non-active participant carries an explicit text state marker.
        self.assertIn("倒地", frame_text, "a knocked-out participant is marked in text, not colour alone")

        # Portraits resolve only through the committed art portrait catalog.
        imgs = frame.locator("img.participant-frame__portrait")
        placeholders = frame.locator('[data-testid="participant-portrait-placeholder"]')
        self.assertEqual(imgs.count(), 2, "resolvable portrait references render the catalog image")
        self.assertEqual(placeholders.count(), 0, "a null portrait_ref renders no placeholder card")
        # While the participant frame is mounted, no separate portrait strip renders.
        self.assertEqual(
            page.locator('[data-testid="art-panel"]').count(),
            0,
            "while the participant frame is mounted, no separate portrait strip renders",
        )

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

        # Open the Skills tab (second root item) -> the category frame.
        _press(page, "ArrowRight")
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
        _press(page, "ArrowRight")
        _press(page, "Enter")
        page.wait_for_timeout(150)
        self.assertEqual(_dock_depth(page), 3, "the single-group category opens the skill frame directly")

        # The skill frame lists the group's descriptors beside the detail pane,
        # which names the focused skill, its cost, description and target spec.
        detail = page.locator('[data-testid="combat-detail"]')
        self.assertEqual(detail.count(), 1, "the single-group category opens the skill frame with the detail pane")
        detail_text = detail.inner_text()
        self.assertIn("護盾術", detail_text, "the detail pane names the focused skill")
        self.assertIn("MP 8", detail_text, "the detail pane shows the skill's cost")
        self.assertIn("防禦", detail_text, "the detail pane shows the skill's description")
        self.assertIn("self", detail_text, "the detail pane shows the skill's target requirement")

    @covers_requirement(
        "webclient-contextual-hud::destructive-combat-confirmation-renders-as-an-explicit-two-step-panel"
    )
    def test_destructive_combat_confirmation_two_step_panel(self):
        """Opening Forfeit renders an explicit two-step confirmation panel."""
        page = self.logged_in_page()
        install_outbound_recorder(page)
        _inject_snapshot(page, {"context_actions": _combat_panel()}, mode="combat")
        _wait_mode(page, "combat")
        focus_action_dock(page)

        # The combat root is a single-row tab bar; Forfeit is the last tab.
        tab_count = page.evaluate("document.querySelectorAll('#action-dock [data-item-key]').length")
        for _ in range(tab_count - 1):
            _press(page, "ArrowRight")
        _press(page, "Enter")  # open the Forfeit confirmation frame
        page.wait_for_timeout(150)

        # The confirmation frame renders as an explicit warning panel with a
        # cancel row and a confirm row; opening it submits nothing.
        pane = page.locator('[data-testid="dock-menu"]')
        pane_text = pane.inner_text()
        self.assertIn("確認投降", pane_text, "the confirmation frame renders the confirm row")
        self.assertIn("取消", pane_text, "the confirmation frame renders the cancel row")
        self.assertEqual(sent_action_count(page), 0, "opening Forfeit submits no mutation")

        # Escape closes exactly one level without submitting.
        _press(page, "Escape")
        page.wait_for_timeout(150)
        self.assertEqual(_dock_depth(page), 1, "Escape pops exactly one level")
        self.assertEqual(sent_action_count(page), 0, "leaving the confirmation submits nothing")

        # Re-open Forfeit and activate the confirm row: exactly one
        # combat.forfeit action is emitted carrying the current session id.
        # After the first Escape the root frame's focus is already on the
        # Forfeit tab (the parent focus is restored by the router), so a single
        # Enter re-opens the confirmation frame.
        _press(page, "Enter")
        page.wait_for_timeout(150)
        page.locator('[data-testid="dock-menu"] button[data-item-key="confirm-forfeit"]').click()
        page.wait_for_timeout(200)
        self.assertEqual(
            sent_action_count(page, "combat.forfeit"),
            1,
            "activating the confirm row emits exactly one combat.forfeit",
        )
        sent = page.evaluate("window.__elosernSent || []")
        forfeit = [
            args[0]
            for cmd, args, _kw in sent
            if cmd == "ui_action" and args and args[0].get("action_id") == "combat.forfeit"
        ]
        self.assertEqual(
            forfeit[0]["payload"]["session_id"],
            "browser-combat-0001",
            "the forfeit action carries the current session identifier",
        )
