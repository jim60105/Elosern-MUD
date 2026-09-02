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
        "webclient-contextual-hud::reference-surfaces-render-in-a-right-anchored-drawer-with-one-modal-contract"
    )
    def test_reference_drawer_modal_contract(self):
        # The drawer chrome (right-anchored, single-open, focus trap, Escape /
        # close-control / scrim close, focus restoration, reduced-motion) is
        # asserted by the drawer + focus-trap component suites. Since
        # align-drawer-chrome-symbols the modified clauses — the
        # --command-line-h top inset over a bottom edge at the stage bottom
        # with the whole-stage scrim, and the reference's 20px / .04em head
        # title with the 11px subtitle — are pinned selector-level by the
        # drawer component suite's CSS-rule-block test.
        _assert_vitest_passes(
            _run_vitest(
                TESTS_DIR / "hud_drawer.test.js",
                TESTS_DIR / "focus_trap.test.js",
            ),
            "reference-drawer modal contract",
        )

    @covers_requirement(
        "webclient-contextual-hud::the-reference-surfaces-have-no-permanently-visible-home-and-are-reached-from-the-dock"
    )
    def test_reference_surfaces_demand_opened_from_dock(self):
        # No reference surface is mounted while closed; each is reached from the
        # dock in at most two actions (the dock is the single listbox + tab stop).
        _assert_vitest_passes(
            _run_vitest(TESTS_DIR / "app_client_drawers.test.js"),
            "reference-surfaces demand-opened from the dock",
        )

    @covers_requirement(
        "webclient-contextual-hud::a-drawer-hosting-a-dock-frame-renders-that-frame-rather-than-a-second-navigation-model"
    )
    def test_drawer_hosts_router_frame_no_second_nav_model(self):
        # The store-level invariant: no state where a service frame is current
        # while its drawer is closed; closing the drawer pops exactly one menu
        # level. The drawer renders the frame's rows through the dock's shared
        # row renderer (AppClient wires DockMenu into the drawer body).
        _assert_vitest_passes(
            _run_vitest(TESTS_DIR / "store" / "hud_drawer.test.js"),
            "drawer hosts the router frame",
        )

    @covers_requirement(
        "webclient-contextual-hud::the-bag-renders-the-bounded-inventory-rows-without-inventing-a-total-or-a-rarity"
    )
    def test_bag_bounded_inventory_rows(self):
        # The bag renders the committed services inventory rows (name / held /
        # equipped), states the row ceiling in words, and fabricates no total /
        # rarity / use-equip control. Since realign-inventory-drawer-layout the
        # available body is the mock's three-section stack (equipment doll,
        # `物品` heading tagged with the shipped listing size over the tile
        # grid, and a `金錢` section whose single row carries the committed
        # grouped integer wallet) on the bare drawer body, with no sort /
        # filter / search pill reproduced.
        _assert_vitest_passes(
            _run_vitest(TESTS_DIR / "world" / "inventory_panel.test.js"),
            "bag bounded inventory rows",
        )

    @covers_requirement(
        "webclient-contextual-hud::the-equipment-doll-renders-only-server-authored-slots-and-drops-nothing"
    )
    def test_equipment_doll_server_authored_slots(self):
        # The equipment doll renders the server's three singleton slots and the
        # accessory summary as four named positions in a compact two-column
        # square layout (restyle-inventory-equipment-slots). Since
        # realign-inventory-drawer-layout the section is titled `裝備` with the
        # `真值 · 偽裝不影響` tag (never `裝備人偶`) and the square grid sits in
        # the mock's `.doll` flex row beside a 裝備描述 column whose labelled
        # entries carry the committed display names (slot label + name; every
        # accessory row groups under the 飾品 label), while the accessory
        # summary still states the committed count (a duplicate committed row
        # for a recognised singleton slot renders as a labelled overflow row)
        # and any unrecognised slot key renders as a labelled fallback row
        # rather than being discarded. Each position renders only a fixed local
        # SVG selected by its server-authored slot role (the off-hand position
        # is the iconless position); a vacant singleton slot renders its
        # explicit dashed empty state. No item statistic, rarity, item icon,
        # summary, or comparison is invented.
        _assert_vitest_passes(
            _run_vitest(TESTS_DIR / "data" / "equipment_doll.test.js"),
            "equipment doll server-authored slots",
        )

    @covers_requirement(
        "webclient-contextual-hud::the-character-status-drawer-degrades-section-by-section-and-never-substitutes-a-disguise"
    )
    def test_character_status_drawer_section_degradation(self):
        # The character-status drawer renders vitals + conditions from the
        # ``status`` panel in every mode, marks the ``character`` sections with the
        # registry-owned reason when unavailable, and presents a disguise as a
        # labelled comparison beside the true trait rows (never a substitution).
        _assert_vitest_passes(
            _run_vitest(TESTS_DIR / "data" / "character_status_drawer.test.js"),
            "character-status drawer section degradation",
        )

    @covers_requirement(
        "webclient-contextual-hud::the-drawer-layer-renders-the-wallet-exactly-once"
    )
    def test_drawer_layer_single_wallet(self):
        # Across the whole drawer layer the wallet renders in exactly two
        # places per opening of the inventory drawer (realign-inventory-
        # drawer-layout): the shared header subtitle and the single row of the
        # `金錢` body section — both the same thousands-grouped integer copper
        # read from the committed character panel, never the services-side
        # figure; no other drawer or body element renders a balance, and an
        # unavailable panel renders no balance (never a zero).
        _assert_vitest_passes(
            _run_vitest(TESTS_DIR / "app_client_drawers.test.js"),
            "drawer-layer single wallet",
        )

    @covers_requirement(
        "webclient-contextual-hud::mutations-issued-from-a-drawer-keep-the-dispatch-and-confirmation-contract"
    )
    def test_drawer_mutations_dispatch_and_confirmation(self):
        # Drawer affordances emit the server-authored action id + payload through
        # the single dispatch entry, locked with in-flight / epoch / revision
        # gates; the destructive abandon sits behind an explicit confirmation; the
        # quantity form keeps the server-advertised min/max.
        _assert_vitest_passes(
            _run_vitest(
                TESTS_DIR / "world" / "quest_board.test.js",
                TESTS_DIR / "world" / "shop_panel.test.js",
                TESTS_DIR / "store" / "store_dispatch_focus.test.js",
            ),
            "drawer mutations dispatch + confirmation",
        )

    @covers_requirement(
        "persona-editing::the-character-drawer-shows-and-edits-the-four-persona-sections"
    )
    def test_persona_drawer_sections_and_single_action_edit(self):
        # The drawer renders the persona area as four labelled sections
        # (個性／生平／習慣／背景) with the localized 未設定 placeholder for
        # nulls and no structural persona key, and each section's inline
        # editor submits exactly one character.persona.update action (a blank
        # draft submits null); the AppClient composition test asserts the one
        # envelope and the refreshed-panel re-render.
        _assert_vitest_passes(
            _run_vitest(
                TESTS_DIR / "data" / "character_status_drawer.test.js",
                TESTS_DIR / "app_client_drawers.test.js",
            ),
            "persona drawer sections + single-action edit",
        )


if __name__ == "__main__":
    unittest.main()
