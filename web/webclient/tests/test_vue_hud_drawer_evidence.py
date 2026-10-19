"""Evidence bridge: run the Vue Vitest component suite for the H4 reference
drawers and link each ``webclient-contextual-hud`` main-spec requirement to an
executed, passing Vitest evidence record.

The six reference surfaces (skill book, bag, shop, quest board, lore,
character status) moved into right-anchored drawers (H4). Their behavior is
implemented and verified in the Vue layer. ``covers_requirement`` can only
attach to a Python ``test_*`` function, so this module executes the relevant
Vitest component files and asserts every test passes; the annotation then
links each main-spec requirement to the substantively matching, executed
evidence record.
"""

from pathlib import Path
import subprocess
import unittest

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[3]
TESTS_DIR = REPO_ROOT / "web/webclient-app/tests"


def _run_vitest(*test_files):
    """Run the named Vitest component files and assert the whole suite passes."""
    args = [str(REPO_ROOT / p) for p in test_files]
    result = subprocess.run(
        ["npx", "--no-install", "vitest", "run", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    return result


def _assert_vitest_passes(result, label):
    assert result.returncode == 0, (
        f"{label} Vitest suite failed:\n{result.stdout}\n{result.stderr}"
    )
    assert "pass" in result.stdout, f"{label}: expected a passing suite summary"


class VueHudDrawerEvidenceTest(unittest.TestCase):
    @covers_requirement(
        "webclient-contextual-hud::reference-surfaces-render-in-a-bounded-workspace-drawer-with-one-modal-contract"
    )
    def test_reference_drawer_modal_contract(self):
        # The drawer chrome (right-anchored, single-open, focus trap, Escape /
        # close-control / scrim close, focus restoration, reduced-motion) is
        # asserted by the drawer + focus-trap component suites. Since
        # align-drawer-chrome-symbols the modified clauses — the
        # --command-line-h top inset over a bottom edge at the stage bottom
        # with the whole-stage scrim, and the reference's 20px / .04em head
        # title with the 11px subtitle — are pinned selector-level by the
        # drawer component suite's CSS-rule-block test. The 技能-tab
        # scenarios (webclient-party-skill-tab: the tab's glyph and honest
        # 主動/被動 counts, one window title, no cast-syntax footer, and the
        # companion cast closing the window before the dock) are asserted by
        # the AppClient drawer-layer suite.
        _assert_vitest_passes(
            _run_vitest(
                TESTS_DIR / "hud_drawer.test.js",
                TESTS_DIR / "focus_trap.test.js",
                TESTS_DIR / "app_client_drawers.test.js",
            ),
            "reference-drawer modal contract",
        )

    @covers_requirement(
        "webclient-contextual-hud::the-reference-surfaces-have-no-permanently-visible-home-and-are-reached-from-the-top-navigation-or-the-dock"
    )
    def test_reference_surfaces_demand_opened_from_dock(self):
        # No reference surface is mounted while closed; each is reached from the
        # dock in at most two actions (the dock is the single listbox + tab stop).
        _assert_vitest_passes(
            _run_vitest(TESTS_DIR / "app_client_drawers.test.js"),
            "reference-surfaces demand-opened from the dock",
        )

    @covers_requirement(
        "webclient-contextual-hud::reference-drawers-present-no-router-frame-and-never-host-a-dock-row-region"
    )
    def test_reference_drawers_frameless_no_dock_region(self):
        # Reference drawers present no router frame: opening any reference
        # drawer pushes no frame and switches no sub-dock, closing pops nothing,
        # and no drawer body renders dock-menu or dock-detail.
        _assert_vitest_passes(
            _run_vitest(
                TESTS_DIR / "store" / "hud_drawer.test.js",
                TESTS_DIR / "app_client_frameless_shop.test.js",
            ),
            "reference drawers present no router frame and never host a dock row region",
        )

    @covers_requirement(
        "webclient-party-window::the-bag-tab-presents-the-viewed-member-s-doll-bag-and-holdings",
    )
    def test_bag_tab_rows_and_doll(self):
        # The party window's 背包 tab renders the committed `party_inventory`
        # doll (主手, 副手, 盔甲, 飾品 n/limit) above the viewed member's rows
        # (name, held count, equipped tag), a doll slot filters the rows
        # locally, rarity is the committed presentation's, and every control
        # follows a committed descriptor.
        _assert_vitest_passes(
            _run_vitest(TESTS_DIR / "data" / "party_bag_tab.test.js"),
            "bag tab rows and doll",
        )

    @covers_requirement(
        "webclient-party-window::the-status-tab-shows-true-values-with-a-trait-waterfall",
        "webclient-party-window::the-status-tab-shows-conditions-and-an-honest-disguise",
    )
    def test_party_status_tab_waterfall_conditions_and_disguise(self):
        # The party window's 狀態 tab (webclient-party-status-tab) selects the
        # first layered trait, lists the waterfall layers in payload order
        # with their source labels, signs raised and lowered totals, shows no
        # gem without a rank, details a condition's source, remaining time
        # and modifiers, keeps every true row under an active disguise, and
        # renders the committed values in combat.
        _assert_vitest_passes(
            _run_vitest(
                TESTS_DIR / "data" / "party_status_tab.test.js",
                TESTS_DIR / "data" / "breakdown_rendering.test.js",
            ),
            "party window status tab",
        )

    @covers_requirement(
        "webclient-contextual-hud::the-party-purse-renders-exactly-once-per-window"
    )
    def test_drawer_layer_single_wallet(self):
        # Across the whole drawer layer the party purse renders exactly once
        # (webclient-party-bag-retire): in the party window's header, from the
        # committed `party_inventory` panel; the bag tab body renders no 金錢
        # row, no other drawer renders a balance, and an unavailable panel
        # renders no balance (never a zero).
        _assert_vitest_passes(
            _run_vitest(TESTS_DIR / "app_client_drawers.test.js"),
            "drawer-layer single wallet",
        )

    @covers_requirement(
        "webclient-contextual-hud::mutations-issued-from-a-drawer-keep-the-dispatch-and-confirmation-contract"
    )
    @covers_requirement("webclient-quest-drawer::the-guild-board-is-organized-by-difficulty-grade-tabs")
    @covers_requirement("webclient-quest-drawer::the-counter-tab-shows-the-rank-card-above-the-board")
    @covers_requirement("webclient-quest-drawer::selecting-a-board-offer-shows-its-detail-and-the-accept-action")
    @covers_requirement("webclient-quest-drawer::an-unregistered-holder-sees-registration-instead-of-the-board")
    def test_drawer_mutations_dispatch_and_confirmation(self):
        # Drawer affordances emit the server-authored action id + payload through
        # the single dispatch entry, locked with in-flight / epoch / revision
         # gates; the destructive abandon sits behind an explicit confirmation;
         # the quantity entry clamps on change to the server-advertised bounds.
        _assert_vitest_passes(
            _run_vitest(
                 TESTS_DIR / "world" / "guild_rank_card.test.js",
                 TESTS_DIR / "world" / "quest_detail.test.js",
                 TESTS_DIR / "world" / "quest_drawer.test.js",
                TESTS_DIR / "world" / "shop_panel.test.js",
                TESTS_DIR / "store" / "store_dispatch_focus.test.js",
            ),
            "drawer mutations dispatch + confirmation",
        )

    @covers_requirement(
        "persona-editing::the-party-window-member-tab-shows-and-edits-the-four-persona-sections"
    )
    def test_persona_member_tab_sections_and_single_action_edit(self):
        # The party window's 成員 tab renders the commander's persona area as
        # four labelled sections (個性／生平／習慣／背景) with the localized
        # 未設定 placeholder for nulls and no structural persona key, and its
        # 編輯人物設定 editor submits exactly one character.persona.update
        # action per section (a blank draft submits null); the AppClient
        # composition test asserts the one envelope and the refreshed-panel
        # re-render.
        _assert_vitest_passes(
            _run_vitest(
                TESTS_DIR / "data" / "party_member_tab.test.js",
                TESTS_DIR / "app_client_drawers.test.js",
            ),
            "persona member-tab sections + single-action edit",
        )


if __name__ == "__main__":
    unittest.main()
