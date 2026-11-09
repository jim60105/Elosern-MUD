"""Evidence bridge: run the Vitest suites of the handbook's shared parts.

handbook-primitives adds the grouped roving-focus ``TileWall`` and the
``DetailFooter`` that the quest detail now renders its pinned footer through.
handbook-titles-tab adds the 手帳's titles tab (``TitleCodexTab``,
``CodexMedalGrid``), its route request and its close guard.
handbook-codex-tab adds the 手帳's codex tab (``LoreCodexTab``,
``CodexTileGrid``, ``CodexArt``, the codex view of ``CodexDetail`` and the
``lore-codex-model`` view model), which replaces the world-codex drawer.
Their behavior is implemented and verified in the Vue layer, and
``covers_requirement`` can only attach to a Python ``test_*`` function, so
this module executes the relevant Vitest component files and asserts every
test passes. The requirement annotations were applied at each change's archive,
once its delta requirements were synced into the main spec.
"""

from pathlib import Path
import subprocess
import unittest

from tools.spec_traceability import covers_requirement

REPO_ROOT = Path(__file__).resolve().parents[3]
TESTS_DIR = REPO_ROOT / "web/webclient-app/tests"


def _run_vitest(*test_files):
    """Run the named Vitest component files and return the finished process."""
    args = [str(REPO_ROOT / p) for p in test_files]
    return subprocess.run(
        ["npx", "--no-install", "vitest", "run", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )


def _assert_vitest_passes(result, label):
    assert result.returncode == 0, (
        f"{label} Vitest suite failed:\n{result.stdout}\n{result.stderr}"
    )
    assert "pass" in result.stdout, f"{label}: expected a passing suite summary"


class VueHandbookEvidenceTest(unittest.TestCase):
    @covers_requirement(
        "webclient-window-primitives::tilewall-is-a-grouped-roving-focus-listbox"
    )
    def test_tile_wall_roving_focus(self):
        # One tab stop (the selected item, else the first); arrow keys, Home
        # and End move focus in reading order across groups without
        # selecting; Enter, Space and click select once; a non-selectable
        # item stays focusable, carries aria-disabled and never selects.
        _assert_vitest_passes(
            _run_vitest(TESTS_DIR / "handbook" / "tile_wall.test.js"),
            "tile wall roving focus",
        )

    @covers_requirement(
        "webclient-window-primitives::detailfooter-renders-descriptor-buttons-and-a-committed-reason"
    )
    def test_detail_footer_contract(self):
        # A disabled button stays focusable with aria-disabled and emits
        # nothing, a toggle keeps native disabled, an enabled button emits
        # press with its key, and the quest detail renders its footer through
        # DetailFooter with unchanged testids, focus moves and actions.
        _assert_vitest_passes(
            _run_vitest(
                TESTS_DIR / "components" / "detail_footer.test.js",
                TESTS_DIR / "world" / "quest_detail.test.js",
            ),
            "detail footer contract",
        )


    # -- handbook-titles-tab ---------------------------------------------------

    @covers_requirement(
        "webclient-quest-drawer::the-quest-drawer-is-a-two-level-icon-tabbed-surface"
    )
    def test_handbook_tab_set_follows_the_mode(self):
        # Outside combat the first-level tabs are the book, counter and
        # titles; in combat only the titles tab, without overwriting a
        # remembered book; the existing book and counter behavior is intact.
        _assert_vitest_passes(
            _run_vitest(TESTS_DIR / "world" / "quest_drawer.test.js"),
            "handbook tab set",
        )

    @covers_requirement("webclient-quest-drawer::a-handbook-route-request-opens-the-drawer-on-the-named-tab")
    def test_handbook_route_request_opens_the_named_tab(self):
        # The store's handbook entry opens the drawer on the named tab, a new
        # request switches an open drawer, an unknown or out-of-mode tab is
        # refused, a consumed request is never re-applied, and the request
        # reads no provider beyond a plain opening.
        _assert_vitest_passes(
            _run_vitest(
                TESTS_DIR / "store" / "hud_drawer.test.js",
                TESTS_DIR / "world" / "quest_drawer.test.js",
                TESTS_DIR / "app_client_drawers.test.js",
            ),
            "handbook route request",
        )

    @covers_requirement("webclient-quest-drawer::the-titles-tab-organizes-the-committed-title-codex-by-rail")
    def test_titles_tab_rail_and_medal_wall(self):
        # The rail follows the closed category order with unlocked counts,
        # adds the hot ballot entry only while a ballot is pending and falls
        # back to the epithet entry when it clears; locked medals keep their
        # name and hint; medals walk by keyboard.
        _assert_vitest_passes(
            _run_vitest(
                TESTS_DIR / "handbook" / "title_codex_tab.test.js",
                TESTS_DIR / "handbook" / "codex_medal_grid.test.js",
                TESTS_DIR / "handbook" / "title_codex_model.test.js",
            ),
            "titles tab rail and medal wall",
        )

    @covers_requirement("webclient-quest-drawer::the-titles-tab-equips-through-the-detail-footer")
    def test_titles_tab_equips_through_the_detail_footer(self):
        # One title.equip per activation (fixed by key, epithet by display),
        # disabled with a reason for locked and equipped entries, and the
        # full title in the head only on the titles tab.
        _assert_vitest_passes(
            _run_vitest(
                TESTS_DIR / "handbook" / "title_codex_tab.test.js",
                TESTS_DIR / "world" / "quest_drawer.test.js",
            ),
            "titles tab equip",
        )

    @covers_requirement("webclient-quest-drawer::epithet-removal-takes-two-steps-and-any-close-attempt-cancels-it")
    def test_titles_tab_two_step_removal_and_close_guard(self):
        # The remove control follows can_remove; arming moves focus to cancel;
        # confirm emits one title.remove; a selection, rail or close attempt
        # disarms without emitting and the close attempt keeps the drawer open.
        _assert_vitest_passes(
            _run_vitest(
                TESTS_DIR / "handbook" / "title_codex_tab.test.js",
                TESTS_DIR / "world" / "quest_drawer.test.js",
                TESTS_DIR / "app_client_drawers.test.js",
            ),
            "titles tab removal",
        )

    @covers_requirement("webclient-quest-drawer::the-titles-tab-answers-a-pending-ballot")
    def test_titles_tab_answers_the_ballot(self):
        # Accept emits one title.accept with the one-based nominee index and
        # decline one title.decline with an empty payload.
        _assert_vitest_passes(
            _run_vitest(TESTS_DIR / "handbook" / "title_codex_tab.test.js"),
            "titles tab ballot",
        )

    @covers_requirement("webclient-quest-drawer::the-titles-tab-degrades-honestly")
    def test_titles_tab_degrades_honestly(self):
        # The absent empty state before the first commit, the unavailable
        # panel disabling the tab with its reason, and a vanished selection
        # falling back to the first row or the empty detail.
        _assert_vitest_passes(
            _run_vitest(
                TESTS_DIR / "handbook" / "title_codex_tab.test.js",
                TESTS_DIR / "world" / "quest_drawer.test.js",
            ),
            "titles tab degradation",
        )


    # -- handbook-codex-tab ----------------------------------------------------
    # The requirement annotations are applied at this change's archive, once
    # its ADDED requirements are synced into the main spec.

    def test_codex_tab_renders_the_committed_panel_as_a_grouped_tile_wall(self):
        # One rail entry per shipped category with its discovered count; the
        # selected category's groups in order with headings only for
        # non-null labels; placeholders focusable but never selected; arrow,
        # Home and End roving; the card rendered verbatim under readable
        # names; per-category selection memory; nothing dispatched.
        _assert_vitest_passes(
            _run_vitest(
                TESTS_DIR / "handbook" / "lore_codex_tab.test.js",
                TESTS_DIR / "handbook" / "codex_tile_grid.test.js",
                TESTS_DIR / "handbook" / "lore_codex_model.test.js",
            ),
            "codex tab tile wall",
        )

    def test_codex_tab_marks_research_stages_by_shape_with_a_legend(self):
        # Filled, hollow and ？ marks with distinct data-stage values; the
        # legend with its three marks only on the monster wall, as the
        # scroller's last child; the two-step research track following the
        # stage, its second step naming the locked fields.
        _assert_vitest_passes(
            _run_vitest(
                TESTS_DIR / "handbook" / "codex_tile_grid.test.js",
                TESTS_DIR / "handbook" / "codex_detail.test.js",
                TESTS_DIR / "handbook" / "lore_codex_model.test.js",
            ),
            "codex tab stage marks",
        )

    def test_codex_tab_shows_locked_fields_without_values(self):
        # One locked box per locked field, in order, with no value; none for
        # a defeated entry.
        _assert_vitest_passes(
            _run_vitest(
                TESTS_DIR / "handbook" / "codex_detail.test.js",
                TESTS_DIR / "handbook" / "lore_codex_model.test.js",
            ),
            "codex tab locked fields",
        )

    def test_codex_hero_art_falls_back_to_the_category_emblem(self):
        # A null art shows the emblem, a failed single attempt with no
        # terminal falls back to it, and a loaded image replaces it.
        _assert_vitest_passes(
            _run_vitest(
                TESTS_DIR / "handbook" / "codex_art.test.js",
                TESTS_DIR / "handbook" / "codex_detail.test.js",
                TESTS_DIR / "handbook" / "lore_codex_tab.test.js",
            ),
            "codex hero art fallback",
        )

    def test_codex_tab_degrades_honestly(self):
        # The absent empty state before the first commit, the unavailable
        # panel disabling the tab with its reason, the full placeholder wall
        # with the empty guidance, and a vanished selection falling back.
        _assert_vitest_passes(
            _run_vitest(
                TESTS_DIR / "handbook" / "lore_codex_tab.test.js",
                TESTS_DIR / "world" / "quest_drawer.test.js",
            ),
            "codex tab degradation",
        )

if __name__ == "__main__":
    unittest.main()
