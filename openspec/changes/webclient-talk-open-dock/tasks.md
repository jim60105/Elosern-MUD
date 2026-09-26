## 1. Preconditions

- [x] 1.1 Confirm that C8c (`webclient-retire-exploration-submenus`) and C9a (`explore-talk-open-action`) are archived and that their seams exist:
  - `openspec/specs/webclient-exploration-menu/spec.md` contains "The exploration dock is keyboard-first and roots at the scene overview" and "The exploration panel is an exact read-only version-3 presentation panel".
  - `openspec/specs/webclient-contextual-hud/spec.md` contains "A fixed-column dock pane sizes its columns to content".
  - `git grep -n "a-fixed-column-dock-pane-sizes-its-columns-to-content" web/tests/browser` matches `test_browser_combat_skills.py` (the case C9a moved there).
  - `grep -n "explore.talk_open" web/static/webclient/js/elosern/exploration_menu.js web/static/webclient/js/elosern/command_echo.js` matches both files.
  - `grep -n "keywordMenuFor\|scriptedAffordanceFor" web/static/webclient/js/elosern/exploration_menu.js` and `grep -n "exploration.keywords" web/webclient-app/stores/frame-resolvers.js` match.
  - `grep -n "\"affordance\"\|\"nav\"" web/webclient-app/components/dock-panes.js` matches both kinds.

  Stop and report if any of these is missing.

## 2. Exploration menu and store

- [x] 2.1 `web/static/webclient/js/elosern/exploration_menu.js` (design D2): delete `keywordMenuFor`, `scriptedAffordanceFor`, and their exports, and rewrite the header comment.
- [x] 2.2 `web/webclient-app/stores/frame-resolvers.js`: delete the `exploration.keywords` source and update the header comment. `web/webclient-app/stores/elosern/frames.js`:
  - Drop `"exploration.keywords"` from the `gridCols = 1` list.
  - **No new rule (design D1, revised during implementation).** `settleFrameStack` already
    returns the stack to the root on the mode change to `dialogue` through the store's one
    mode-change teardown (`syncHudDrawer` -> `resetFramesToRoot`), so a second reset in the
    dock group would be dead weight. The behaviour is pinned by tests (4.2) instead of
    re-implemented: verified with a popover open at depth 2 (snapshot and update forms, and
    the real `explore.talk_open` flow) that the commit carrying `mode: "dialogue"` leaves
    depth 1 with `dockSource === "exploration.root"`.
- [x] 2.3 `stores/elosern/interaction.js`: delete the `openKeywords` and `freeform` branches of `handleExplorationItem`, and update the `borrowDialogueCommand` and `actionId` comments. `stores/elosern/combat.js` `fillDisplayFor`: add `explore.talk_open` to the `npcLabel` family (design D3). `stores/dialogue-view.js`: fix the header comment (no `keywordMenuFor`).

## 3. Dock panes

- [x] 3.1 `web/webclient-app/components/dock-panes.js`: delete the `nav` kind and its clauses, and the `affordance` kind and its test. Update the kind-list comment.
- [x] 3.2 `web/webclient-app/components/DockMenu.vue`:
  - Delete the nav template branch (`dock-menu__nav*`), its CSS, the `nav` `sizeFn` branch (the track function becomes `1fr` for every pane with `gridCols`), and the `openKeywords` chevron clause.
  - Delete the affordance template branch (`dock-menu__aff*`), its CSS, and the `targetName` prop.
  - Update the header comment's pane-kind list.

  `web/webclient-app/AppClient.vue`: delete the `:target-name` binding on `DockMenu`.
- [x] 3.3 `web/webclient-app/stories/Action/DockMenu.stories.js`: delete or re-point any story whose rows classify as `nav` or `affordance`. Then `git grep -n "dock-menu__nav\|dock-menu__aff\|\"nav\"\|'nav'\|\"affordance\"\|'affordance'\|targetName\|target-name\|openKeywords\|keywordMenuFor\|scriptedAffordanceFor\|exploration\.keywords" web/webclient-app web/static/webclient/js -- ':!dist' ':!node_modules'` returns nothing outside the tests that 4.1 and 4.2 rewrite, and nothing at all after them. (`affordance` as a word stays in unrelated names such as `affordanceLabels` and the verb popover; the grep targets the pane-kind strings.)

## 4. Node and Vitest

- [x] 4.1 Node tests under `web/static/webclient/js/tests/`:
  - `exploration_menu.test.js`: delete the `keywordMenuFor` / `scriptedAffordanceFor` cases.
  - `keyboard_router_declarative.test.js`: rename the synthetic `exploration.keywords` source to `exploration.wait`.

  Run `node --test web/static/webclient/js/tests/*.test.js`. It must pass.
- [x] 4.2 Vitest under `web/webclient-app/tests/`:
  - `frame-resolvers.test.js`: the keyword cases become one "`exploration.keywords` resolves to the unregistered marker" case.
  - `components/dock_panes.test.js`: delete the nav cases (`kw-*`, all-look, `target-*`) and any affordance case; add one case where rows carrying `explore.engage` and `explore.party_invite` classify as `plain`.
  - `action/dock_menu_panes.test.js`: delete `navItems`, `affordanceItems`, the affordance row-order test, and the `nav` / `affordance` entries of `PANE_SELECTORS`. The track test becomes "every kind with `gridCols` emits `repeat(n, 1fr)`; no `gridCols` emits none". Its title and comment say it pins the inline template only: the combat panes are flex boxes on which that template has no effect, so the test makes no claim about equal-width columns.
  - `action/dock_menu.test.js`: delete the nav, `kw-*`, and `targetName` / affordance-head cases.
  - `store/declarative_frames.test.js`: add the D1 cases under "the conversation-open reset":
    - a popover open when the commit changes the mode to `dialogue` resets to the overview
      in that commit (the requirement the delta spec states)
    - a commit that keeps the mode `dialogue` leaves the open frame alone
    - the first commit of a dialogue session mounts the one root frame and resets nothing
    - leaving dialogue (dialogue → exploration) also returns the dock to the overview in
      that commit (the same teardown; pinned so a later narrowing is caught)
  - `store/command_echo_surfaces.test.js`: add the popover 交談 row activation (echo `talk <NPC>`) and a central-fill row (`explore.talk_open` dispatched with no descriptor echoes `talk 店長` from the committed exploration panel).
  - `dialogue_store.test.js`, `dialogue_dock.test.js`: after the popover's `talk-open` row opens a conversation, assert that the popover closed (`router.depth()` is 1) and that the free row still borrows the command line through `borrowDialogueCommand`.

  Run `pnpm test`. It must pass. Then run `pnpm run build`, `pnpm run build-storybook`, and `pnpm run showcase-coverage` (repository root). All must pass.

## 5. Browser journeys

- [x] 5.1 `web/tests/browser/test_browser_exploration_dialogue.py` (class run: 6 of 7 pass, including the new `test_talk_open_enters_the_dialogue_in_one_step` and both dock-at-overview assertions; the one failure is the known pre-existing `test_look_at_scripted_host_shows_the_affinity_stage_line`, entity- vs target-chip premise, left untouched):
  - `test_scripted_keyword_dialogue_completes` and `test_dialogue_surface_is_the_caption_and_the_dock_stays_ordinary`: after 交談, assert that the dock is back at the overview (`router.depth()` is 1) before digit `1` sends `explore.talk_scripted`.
  - Add `test_talk_open_enters_the_dialogue_in_one_step`, a keyboard-only journey at 1920x1080 annotated `webclient-exploration-menu::the-keyboard-first-exploration-dock-roots-at-the-scene-overview-and-opens-dialogue-directly` and `webclient-exploration-menu::explore-talk-open-opens-a-conversation-with-the-host-s-greeting`. One Enter on 交談 sends one `explore.talk_open` and no `explore.talk_scripted`. The next commit has mode `dialogue` and a `dialogue` panel whose line is the greeting, `router.depth()` is 1, and `✕ 結束對話` sends `explore.dialogue_leave`.
- [x] 5.2 `test_browser_services_base.py`: fix the `_open_surface` docstring (no per-keyword talk rows), and repair the walk itself (its second Enter activated the popover's leading 交談 row, so the popover closed and `service-<surface>` was gone). Both hops now use stable keys read from the committed panel, and the helper normalizes the stack back to the overview afterwards so its postcondition (the callers' depth/trail invariance across the drawer open) holds; the invariance is pinned un-normalized by the helper's inventory branch and by the quest-drawer journey in `test_browser_exploration_nav.py`. `test_browser_contextual_hud_dock.py`: drop any nav-row or affordance-pane assertion (`dock-menu__nav`, `dock-menu__aff`). `git grep -n "exploration\.keywords\|dock-menu__nav\|dock-menu__aff\|talk-scripted\|talk-freeform\|自由交談" web/tests/browser` returns nothing.

## 6. Specs and traceability

- [x] 6.1 Sync this change's deltas into the main specs.
- [x] 6.2 Re-anchor `webclient-exploration-menu::the-exploration-dock-is-keyboard-first-and-roots-at-the-scene-overview` to `webclient-exploration-menu::the-keyboard-first-exploration-dock-roots-at-the-scene-overview-and-opens-dialogue-directly`. The anchors are in `web/tests/browser/test_browser_exploration_actions.py`, `test_browser_exploration_nav.py` (every occurrence), `test_browser_exploration_state.py`, `test_browser_exploration_tiles.py` (the C8c chip-wrap test), `test_browser_exploration_dialogue.py` (if C9a's re-pointed journeys carry it), and `web/webclient/tests/test_node_suite_evidence.py`. List them with `git grep -n "the-exploration-dock-is-keyboard-first-and-roots-at-the-scene-overview"`.
- [x] 6.3 Re-anchor `webclient-contextual-hud::a-fixed-column-dock-pane-sizes-its-columns-to-content` to `webclient-contextual-hud::a-fixed-column-dock-pane-stays-inside-the-command-region` on the combat skill-frame case in `web/tests/browser/test_browser_combat_skills.py` (moved there by C9a). Keep its assertions (every row inside the pane's right edge at 1280x720, and ArrowRight reaching the second column of the fixed two-column mapping). `git grep -n "sizes-its-columns-to-content" web` returns nothing.

  For 6.2 and 6.3, confirm every ID with `uv run --locked python -m tools.spec_traceability list`, then run `uv run --locked python -m tools.spec_traceability check`. It must pass, the new dock requirement must be covered by 5.1, and the new fixed-column requirement by the 6.3 case.

## 7. Validation

- [x] 7.1 Run `node --test web/static/webclient/js/tests/*.test.js`, `pnpm test`, `pnpm run build`, `pnpm run build-storybook`, `pnpm run showcase-coverage` (repository root), `uv run --locked python -m tools.test_data_lint check`, and `uv run --locked python -m tools.spec_traceability check`. All must pass.
- [x] 7.2 Run `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.tests.test_node_suite_evidence`. It must pass.
- [x] 7.4 Check the live client at 1920x1080 with `agent-browser`: 交談 on a scripted host shows the greeting and its choices in the message window in one press, and the dock shows the overview. Close the browser afterwards.
- [x] 7.5 Run `openspec validate webclient-talk-open-dock --strict` and `git diff --check`. Both must be clean.

## 8. Notes from the apply run

- Browser classes run serially with `unittest_driver` (all green except the known
  pre-existing failure):
  - `test_browser_exploration_dialogue` — 7 tests, 1 failure
    (`test_look_at_scripted_host_shows_the_affinity_stage_line`, the known entity- vs
    target-chip premise; left untouched). The new
    `test_talk_open_enters_the_dialogue_in_one_step` and both dock-at-overview
    assertions pass.
  - `test_browser_services_shop` — 3 tests OK (the repaired walk).
  - `test_browser_services_guild.GuildTurninJourneys.test_completed_quest_turnin` — OK.
  - `test_browser_contextual_hud_dock.ContextualHudBrowserTest.test_dock_panes_render_per_kind_vocabulary`
    — OK (the re-pointed chip-field assertions).
  - `test_browser_combat_skills.CombatMenuBrowserTest.test_fixed_column_skill_pane_keeps_its_rows_inside_the_command_region`
    — OK (the re-anchored fixed-column case).
- Task 7.4: headless `agent-browser` against the built Storybook
  (`Action/DockVerbPopover` → `DialogueHost`) rendered the 交談 affordance surface:
  head 葛里安·衛登 and rows 交談 (focused) / 交易 / 查看 / 返回上一層, with no keyword
  list and no free-form row; the browser was closed afterwards. The live end-to-end
  path (one press → greeting + choices in the message window, dock at the overview) is
  the managed journey above. The story's `focusedKey` still named the retired
  `talk-scripted` row and was corrected in the same commit.
- Post-implementation rubber-duck pass (the pre-implementation pass is moot: the change
  was already implemented when the budget stop landed): verdict SAFE TO PROCEED, no
  blocking issues. Dispositions — NB1 (`_open_surface`'s normalization blinds those
  journeys to a drawer that pushes a frame): comment added naming the two un-normalized
  pins; NB2 (the D1 reset is an emergent side effect of the drawer teardown): a comment
  in `syncHudDrawer` now names the dock requirement as co-owner; NB3 restated NB1 and
  needed no further action; N1 (stale `keyboard_router.js` comment citing the deleted
  scripted-keywords machinery): re-worded; N2 was a recorded no-op.

- Verification run: `uv run --locked python -m web.tests.browser.unittest_driver
  web.tests.browser.test_browser_exploration_dialogue` -> Ran 7 tests, 1 failure
  (the known pre-existing affinity-line case). The dock-at-overview assertion after
  交談 passes in the browser, which confirms the store-level D1 finding end to end.

- Task 2.2/4.2 (design D1) were revised: the reset the design asked for already exists
  (the mode-change teardown), verified by stubbing it out. No second rule was added.
- Task 5.2 grew a repair: `test_browser_services_base.py` `_open_surface`'s fixed arrow
  walk has been broken since C9a — its second Enter activates the popover's leading 交談
  row and the mode-change teardown then closes the popover, so `service-<surface>` is not
  in the current frame. Confirmed failing identically on master (c4b3d673) with
  `test_browser_services_shop.ShopJourneys.test_buy_quantity_validation_exact_copper`.
  Both hops now use stable keys read from the committed panel.
- Task 5.2's grep cannot be literally empty: `explore-talk-scripted-...` and
  `explore-talk-freeform-...` are the surviving requirement IDs of
  `webclient-exploration-menu` and stay annotated on the journeys that exercise them.
  Every pane-kind and keyword-frame reference is gone.
