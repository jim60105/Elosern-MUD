## 1. Preconditions

- [ ] 1.1 Confirm that C8c (`webclient-retire-exploration-submenus`) and C9a (`explore-talk-open-action`) are archived and that their seams exist:
  - `openspec/specs/webclient-exploration-menu/spec.md` contains "The exploration dock is keyboard-first and roots at the scene overview" and "The exploration panel is an exact read-only version-3 presentation panel".
  - `openspec/specs/webclient-contextual-hud/spec.md` contains "A fixed-column dock pane sizes its columns to content".
  - `grep -n "explore.talk_open" web/static/webclient/js/elosern/exploration_menu.js web/static/webclient/js/elosern/command_echo.js` matches both files.
  - `grep -n "keywordMenuFor\|scriptedAffordanceFor" web/static/webclient/js/elosern/exploration_menu.js` and `grep -n "exploration.keywords" web/webclient-app/stores/frame-resolvers.js` match.
  - `grep -n "\"affordance\"\|\"nav\"" web/webclient-app/components/dock-panes.js` matches both kinds.

  Stop and report if any of these is missing.

## 2. Exploration menu and store

- [ ] 2.1 `web/static/webclient/js/elosern/exploration_menu.js` (design D2): delete `keywordMenuFor`, `scriptedAffordanceFor`, and their exports, and rewrite the header comment.
- [ ] 2.2 `web/webclient-app/stores/frame-resolvers.js`: delete the `exploration.keywords` source and update the header comment. `web/webclient-app/stores/elosern/frames.js`:
  - Drop `"exploration.keywords"` from the `gridCols = 1` list.
  - Add the design-D1 rule to `settleFrameStack`: track `ctx.lastMode`, and reset to `EXPLORATION_ROOT_DESCRIPTOR` inside `inStackMutation` when the mode changes from `exploration` to `dialogue` at depth > 1. Initialize `ctx.lastMode = null` beside `ctx.lastRoomIdentity`.
- [ ] 2.3 `stores/elosern/interaction.js`: delete the `openKeywords` and `freeform` branches of `handleExplorationItem`, and update the `borrowDialogueCommand` and `actionId` comments. `stores/elosern/combat.js` `fillDisplayFor`: add `explore.talk_open` to the `npcLabel` family (design D3). `stores/dialogue-view.js`: fix the header comment (no `keywordMenuFor`).

## 3. Dock panes

- [ ] 3.1 `web/webclient-app/components/dock-panes.js`: delete the `nav` kind and its clauses, and the `affordance` kind and its test. Update the kind-list comment.
- [ ] 3.2 `web/webclient-app/components/DockMenu.vue`:
  - Delete the nav template branch (`dock-menu__nav*`), its CSS, the `nav` `sizeFn` branch (the track function becomes `1fr` for every pane with `gridCols`), and the `openKeywords` chevron clause.
  - Delete the affordance template branch (`dock-menu__aff*`), its CSS, and the `targetName` prop.
  - Update the header comment's pane-kind list.

  `web/webclient-app/AppClient.vue`: delete the `:target-name` binding on `DockMenu`.
- [ ] 3.3 `web/webclient-app/stories/Action/DockMenu.stories.js`: delete or re-point any story whose rows classify as `nav` or `affordance`. Then `git grep -n "dock-menu__nav\|dock-menu__aff\|\"nav\"\|'nav'\|\"affordance\"\|'affordance'\|targetName\|target-name\|openKeywords\|keywordMenuFor\|scriptedAffordanceFor\|exploration\.keywords" web/webclient-app web/static/webclient/js -- ':!dist' ':!node_modules'` returns nothing outside the tests that 4.1 and 4.2 rewrite, and nothing at all after them. (`affordance` as a word stays in unrelated names such as `affordanceLabels` and the verb popover; the grep targets the pane-kind strings.)

## 4. Node and Vitest

- [ ] 4.1 Node tests under `web/static/webclient/js/tests/`:
  - `exploration_menu.test.js`: delete the `keywordMenuFor` / `scriptedAffordanceFor` cases.
  - `keyboard_router_declarative.test.js`: rename the synthetic `exploration.keywords` source to `exploration.wait`.

  Run `node --test web/static/webclient/js/tests/*.test.js`. It must pass.
- [ ] 4.2 Vitest under `web/webclient-app/tests/`:
  - `frame-resolvers.test.js`: the keyword cases become one "`exploration.keywords` resolves to the unregistered marker" case.
  - `components/dock_panes.test.js`: delete the nav cases (`kw-*`, all-look, `target-*`) and any affordance case; add one case where rows carrying `explore.engage` and `explore.party_invite` classify as `plain`.
  - `action/dock_menu_panes.test.js`: delete `navItems`, `affordanceItems`, the affordance row-order test, and the `nav` / `affordance` entries of `PANE_SELECTORS`. The track test becomes "every kind with `gridCols` emits `repeat(n, 1fr)`; no `gridCols` emits none".
  - `action/dock_menu.test.js`: delete the nav, `kw-*`, and `targetName` / affordance-head cases.
  - `store/declarative_frames.test.js`: add D1 cases:
    - a popover open when the commit changes the mode to `dialogue` resets to the root
    - a dialogue → exploration commit and a dialogue → dialogue commit never reset
    - the first commit never resets
  - `store/command_echo_surfaces.test.js`: add the popover 交談 row activation (echo `talk <NPC>`) and a central-fill row (`explore.talk_open` dispatched with no descriptor echoes `talk 店長` from the committed exploration panel).
  - `dialogue_store.test.js`, `dialogue_dock.test.js`: after the popover's `talk-open` row opens a conversation, assert that the popover closed (`router.depth()` is 1) and that the free row still borrows the command line through `borrowDialogueCommand`.

  Run `pnpm test`. It must pass. Then run `pnpm run build`, `pnpm run build-storybook`, and `pnpm run showcase-coverage` (repository root). All must pass.

## 5. Browser journeys

- [ ] 5.1 `web/tests/browser/test_browser_exploration_dialogue.py`:
  - `test_scripted_keyword_dialogue_completes` and `test_dialogue_surface_is_the_caption_and_the_dock_stays_ordinary`: after 交談, assert that the dock is back at the overview (`router.depth()` is 1) before digit `1` sends `explore.talk_scripted`.
  - Add `test_talk_open_enters_the_dialogue_in_one_step`, a keyboard-only journey at 1920x1080 annotated `webclient-exploration-menu::the-keyboard-first-exploration-dock-roots-at-the-scene-overview-and-opens-dialogue-directly` and `webclient-exploration-menu::explore-talk-open-opens-a-conversation-with-the-host-s-greeting`. One Enter on 交談 sends one `explore.talk_open` and no `explore.talk_scripted`. The next commit has mode `dialogue` and a `dialogue` panel whose line is the greeting, `router.depth()` is 1, and `✕ 結束對話` sends `explore.dialogue_leave`.
- [ ] 5.2 `test_browser_services_base.py`: fix the `_open_surface` docstring (no per-keyword talk rows). `test_browser_contextual_hud_dock.py`: drop any nav-row or affordance-pane assertion (`dock-menu__nav`, `dock-menu__aff`). `git grep -n "exploration\.keywords\|dock-menu__nav\|dock-menu__aff\|talk-scripted\|talk-freeform\|自由交談" web/tests/browser` returns nothing.

## 6. Specs and traceability

- [ ] 6.1 Sync this change's deltas into the main specs.
- [ ] 6.2 Re-anchor `webclient-exploration-menu::the-exploration-dock-is-keyboard-first-and-roots-at-the-scene-overview` to `webclient-exploration-menu::the-keyboard-first-exploration-dock-roots-at-the-scene-overview-and-opens-dialogue-directly`. The anchors are in `web/tests/browser/test_browser_exploration_actions.py`, `test_browser_exploration_nav.py` (every occurrence), `test_browser_exploration_state.py`, `test_browser_exploration_tiles.py` (the C8c chip-wrap test), `test_browser_exploration_dialogue.py` (if C9a's re-pointed journeys carry it), and `web/webclient/tests/test_node_suite_evidence.py`. List them with `git grep -n "the-exploration-dock-is-keyboard-first-and-roots-at-the-scene-overview"`.

  Confirm every ID with `uv run --locked python -m tools.spec_traceability list`, then run `uv run --locked python -m tools.spec_traceability check`. It must pass, and the new dock requirement must be covered by 5.1.

## 7. Validation

- [ ] 7.1 Run `node --test web/static/webclient/js/tests/*.test.js`, `pnpm test`, `pnpm run build`, `pnpm run build-storybook`, `pnpm run showcase-coverage` (repository root), `uv run --locked python -m tools.test_data_lint check`, and `uv run --locked python -m tools.spec_traceability check`. All must pass.
- [ ] 7.2 Run `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.tests.test_node_suite_evidence`. It must pass.
- [ ] 7.3 Run `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_exploration_dialogue web.tests.browser.test_browser_exploration_nav web.tests.browser.test_browser_exploration_state web.tests.browser.test_browser_exploration_tiles web.tests.browser.test_browser_exploration_actions web.tests.browser.test_browser_input_narrative web.tests.browser.test_browser_services_base web.tests.browser.test_browser_contextual_hud_dock web.tests.browser.test_browser_combat_skills web.tests.browser.test_browser_options_surface`. It must pass.
- [ ] 7.4 Check the live client at 1920x1080 with `agent-browser`: 交談 on a scripted host shows the greeting and its choices in the message window in one press, and the dock shows the overview. Close the browser afterwards.
- [ ] 7.5 Run `openspec validate webclient-talk-open-dock --strict` and `git diff --check`. Both must be clean.
