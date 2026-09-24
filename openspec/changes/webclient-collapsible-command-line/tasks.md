## 1. Preconditions

- [ ] 1.1 Confirm C4c (`webclient-avg-stage-hud-anchors`) is archived, or will be before this change (archive order C1 → C2 → C3 → C4a → C4b → C4c → C5).
  - If a requirement text this change builds on changed after it was written, re-sync this change's block to it and keep only this change's edits (design D9). Those texts are C4c's visibility block, C4b's required-desktop-surfaces block, C3's "map, settings, and help" block, and C3's echo requirement.
  - Confirm `tests/desktop_navigation.test.js` (added by C4b) exists, and that `HudFrame.vue` carries C4a's `command-line` anchor rule (`bottom: var(--band-h)`).
- [ ] 1.2 List every consumer to update. Stop and report any hit outside the files named in sections 2–5.
  - `grep -rn "command-line-lineage\|command-line-lore\|command-line-codex\|command-line-settings\|command-line-help\|gallery-opener\|galleryAvailable\|gallery-available\|cmdutil" web --include='*.vue' --include='*.js' --include='*.py' --include='*.css'` (excluding `dist/` and `node_modules/`)
  - `grep -rnE 'inputfield|command-line-input-field|command-line\\?"|anchor-command-line' web/tests/browser web/webclient-app/tests`
  - `grep -rn "permanently present\|always-present\|never closed" web/webclient-app --include='*.vue' --include='*.js'` (excluding `dist/`)

## 2. Collapsible command line

- [ ] 2.1 `components/CommandLine.vue`:
  - delete `span.cmdutil` with its buttons (lineage, lore, codex, settings, help, and C3's gallery button), `onOpenOverlay`, `onOpenDrawer`, the `open-overlay` / `open-drawer` emits, the `galleryAvailable` prop, and the `.cmdutil*` CSS
  - add `id="command-line-bar"` to the root
  - emit a new `sent` event inside `submit()` at the exact point where the draft is cleared (design D3)
  - `.cmdline` becomes `height: 100%`
  - rewrite the header comment (collapsible, no utility controls)
- [ ] 2.2 `components/HudFrame.vue`:
  - add the `commandLineExpanded` prop and `:data-expanded` on `[data-anchor="command-line"]`
  - add `[data-anchor="command-line"][data-expanded="false"] { display: none; }`
  - update the header comment

  `styles/tokens.css`: `--command-line-h: 44px`, with a comment naming design §5.5.
- [ ] 2.3 `components/AppShell.vue` (design D2, D5, D7):
  - add `commandLineExpanded = ref(false)` and pass it to `HudFrame`
  - `focusCommandField` becomes the async expand-then-focus path
  - `releaseCommandField(restoreFocus)` restores dock focus, then collapses
  - map `@sent` to `releaseCommandField(true)`
  - the mode watcher collapses the line on `nextMode === "creation"` after the existing rescue
  - render the ⌨ `command-line-toggle` button after `NarrativeFeed` in `#band-message`, with `onToggleCommandLine`
  - drop the `galleryAvailable` prop and pass-through
  - `defineExpose` keeps `focusCommandField`, `releaseCommandField`, and `restoreDockFocus`
  - rewrite the header and inline comments

  `styles/app-shell.css`: add the toggle placement and the `[data-anchor="band-message"] .narrative-scroll { padding-bottom: 36px }` rule.
- [ ] 2.4 Comment-only updates:
  - `composables/use-shell-focus.js` (both watchers now open or close the line)
  - `stores/elosern/frames.js` (`toggle-drawer`)
  - `stores/elosern/interaction.js` (`borrowDialogueCommand`, the `item.freeform` branch)
  - `stores/elosern/transport.js` (the `drawerCloseRequest` comment)
  - `components/HudDrawer.vue`, and the description text in `stories/Core/HudDrawer.stories.js` (the 44px inset)

  Check: `grep -rn "permanently present\|always-present" web/webclient-app --include='*.vue' --include='*.js'` (excluding `dist/`) returns nothing.

## 3. Top-bar tool group

- [ ] 3.1 `components/DesktopNavigation.vue` (design D6):
  - add the `galleryAvailable` prop, the `drawer` emit, and `data-testid="nav-settings"` on 設定
  - after 設定, add the `desktop-navigation__tools` group (`role="group"`, `aria-label="工具"`, `data-testid="nav-tools"`) with `nav-tool-lineage`, `nav-tool-lore`, `nav-tool-codex`, `gallery-opener` (`v-if="galleryAvailable"`), and `nav-tool-help`, in that order. Each has `aria-label` and `title` equal to its label. The SVGs are copied from the deleted `CommandLine` markup, plus a new portrait-frame glyph for the gallery.
  - add the 38px icon-button and divider CSS
- [ ] 3.2 `AppClient.vue`:
  - bind `:gallery-available="panelAvailable('gallery')"` and `@drawer="onOpenDrawer"` on `DesktopNavigation`
  - delete the `galleryAvailable` binding on `AppShell`

  `lib/controls-reference.js`: rewrite the `/`, Enter, and Esc rows per design D8.
- [ ] 3.3 Stories:
  - `stories/Core/DesktopNavigation.stories.js`: keep `Exploration` / `Combat`, and add `WithGallery` (`galleryAvailable: true`)
  - `stories/Core/CommandLine.stories.js`: keep the story IDs, and update the descriptions (no utility controls)
  - `stories/Core/AppShell.stories.js`: add `CommandLineExpanded`, which calls the exposed `focusCommandField` in `play`
  - `stories/Core/HudFrame.stories.js`: pass `commandLineExpanded` and describe both states

  Run `pnpm run build-storybook` and `pnpm run showcase-coverage` (repository root); both green. The manifest is unchanged.

## 4. Vitest

- [ ] 4.1 `tests/command_line.test.js`:
  - delete the utility-cluster cases, including the lore / codex case at the `command-line-lore` / `command-line-codex` selectors
  - add: `sent` is emitted once on an accepted submit, and is not emitted when `mutationsLocked`, `inFlight`, or `!connected` (the draft is kept)
  - add: the bar renders no `cmdutil`, `gallery-opener`, or `command-line-settings` element
- [ ] 4.2 `tests/app.test.js`, `tests/preserved_contract.test.js`, `tests/bridge/app_shell_bridge.test.js`, `tests/app_client_completion.test.js`:
  - on mount, `[data-anchor="command-line"]` has `data-expanded="false"`, `command-line-toggle` has `aria-expanded="false"`, and `#inputfield` still exists inside `.inputfieldwrapper`
  - `focusCommandField()` sets `data-expanded="true"` and, after `nextTick`, focuses `#inputfield`
  - `focus-parent` restores `#action-dock` focus and collapses
  - an accepted Enter collapses and focuses the dock; a locked Enter stays expanded with the text
  - the toggle expands, then collapses while leaving focus on the toggle
  - entering creation collapses the line

  Rewrite the "permanently present" comments in these files.
- [ ] 4.3 `tests/hud_frame.test.js`: `data-expanded` follows the prop, and the stage CSS hides the collapsed anchor. `tests/hud_drawer.test.js`: unchanged assertion on `var(--command-line-h)`; re-run it.
- [ ] 4.4 `tests/desktop_navigation.test.js` (C4b's file):
  - the tool group renders its four permanent buttons in order with `aria-label` = `title`
  - `gallery-opener` renders only with `galleryAvailable`
  - clicks emit `overlay` `lineage` / `codex` / `gallery` / `help` and `drawer` `lore`
  - `nav-settings` emits `overlay` `settings`

  Re-point these to the nav buttons, mounting through `AppClient` so opener capture and focus return are exercised:
  - `tests/app_client_gallery.test.js`
  - `tests/overlays/lineage_panel.test.js` (`nav-tool-lineage`)
  - `tests/overlays/title_codex_panel.test.js` (`nav-tool-codex`)
  - `tests/overlays/deferred_surfaces_absent.test.js` (`nav-settings`, `nav-tool-help`)

  `tests/overlays/help_overlay.test.js`: assert the new `/` and Esc wording.

  Run `pnpm test` (repository root); green.

## 5. Browser tests

- [ ] 5.1 `web/tests/browser/browser_helpers.py`:
  - add `open_command_line(page)`, which presses `/` outside an editable control and waits until `document.activeElement` is `#inputfield`
  - `REQUIRED_SURFACES` names `[data-testid="command-line-toggle"]` instead of `[data-testid="command-line"]`, and its comment is rewritten

  For every hit of 1.2's `inputfield` grep, open the line before `fill` / `click` / `type`, or keep it as a presence-only `count()` check, or turn it into a collapsed-state assertion. Files: `test_browser_actions.py`, `test_browser_shell_narrative.py`, `test_browser_exploration_dialogue.py`, `test_browser_input_narrative.py`, `test_browser_shell_command_line.py`, `test_browser_layout.py`, `test_browser_contextual_hud_stage.py`, `test_browser_shell_surfaces.py`, `test_vue_foundation.py`. A journey that sends a second command opens the line again first.
- [ ] 5.2 `test_browser_shell_command_line.py`:
  - rewrite `test_keyboard_field_focus_send_cancel_and_focus_restoration`: collapsed on load, `/` expands and focuses, a send clears, collapses, and focuses `#action-dock`, then `/`, Escape with a draft collapses and keeps the draft on the next `/`
  - rewrite `test_pointer_focused_field_sends_on_enter`: click `command-line-toggle`, type, Enter; one send, then collapsed and dock focus
  - add `test_rejected_send_keeps_the_line_open`: inject a mutation lock, send, then the text is kept, focus stays in the field, and the row stays visible
  - add `test_toggle_collapses_and_keeps_focus`

  Annotate them with `webclient-desktop-shell::the-collapsible-command-line-preserves-ordinary-text-control` and `webclient-contextual-hud::the-command-line-is-a-collapsible-row-docked-on-the-message-region-s-top-edge`.
- [ ] 5.3 `test_browser_contextual_hud_stage.py`:
  - `test_surface_visibility_gated_by_committed_game_mode`: collapsed in exploration, combat, and dialogue; hidden with its toggle in creation; collapsed after returning from creation
  - `test_command_line_never_overlaps_dock_caption_or_hud`: expand first, then assert the row is 44px (±1px), sits on the band's top edge, and spans `--left-column` to the message region's right edge at 1280x720 and 1920x1080
  - `test_h5_overlay_triggers_exclusion_and_focus_restoration`: use `nav-settings` / `nav-tool-help`

  `test_browser_layout.py::test_mode_gating_hides_and_restores_surfaces` and `test_browser_shell_surfaces.py` (`#inputfield` visibility at both viewports): assert the toggle is visible and the field is visible only after `open_command_line`.
- [ ] 5.4 Re-point the tool-group selectors:
  - `test_browser_contextual_hud_drawers.py`: `command-line-lore` / `command-line-codex` → `nav-tool-lore` / `nav-tool-codex`
  - `test_browser_title_codex.py` (`nav-tool-codex`), `test_browser_lineage.py` (`nav-tool-lineage`), `test_browser_input_narrative.py` (`nav-settings`)

  Add `test_top_bar_tool_group_fits_and_opens_with_line_collapsed` to `test_browser_contextual_hud_stage.py`, annotated `webclient-desktop-shell::the-top-navigation-bar-carries-the-tool-group`:
  - at 1280x720 with a maximum-length current-character name and an available `gallery` panel, every `nav-tools` button lies inside the 48px bar, and no `.desktop-navigation` button intersects `.topbar-right`
  - Tab reaches each tool; Enter on each opens its surface and Escape returns focus to it
  - `/` then ArrowUp in the field walks history, while ArrowUp on the dock with the line collapsed is claimed by the router (the pointer-activation scenario)
- [ ] 5.5 Re-anchor the traceability annotations listed in design D9 to the three new IDs. Run `uv run --locked python -m tools.spec_traceability list` to confirm the new IDs after sync.
  - `test_browser_input_narrative.py`, `test_browser_shell_command_line.py`, `test_browser_exploration_dialogue.py`, and `web/webclient/tests/test_node_suite_evidence.py` go to `…::the-collapsible-command-line-preserves-ordinary-text-control`, or to the contextual-hud row ID for the one permanent-bar annotation.
  - `test_browser_contextual_hud_drawers.py` goes to `webclient-lore-codex-panel::the-codex-opens-from-the-top-navigation-bar-not-from-the-quest-drawer`.

  Add a `test_node_suite_evidence.py` case running `tests/desktop_navigation.test.js`, annotated with the tool-group ID.
- [ ] 5.6 `.github/browser-shards.json`: add the new tests to the shards that hold their modules. Run the modules on a local server and get green:
  - `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_shell_command_line web.tests.browser.test_browser_input_narrative web.tests.browser.test_browser_layout web.tests.browser.test_browser_contextual_hud_stage web.tests.browser.test_browser_shell_surfaces web.tests.browser.test_browser_shell_narrative web.tests.browser.test_browser_actions web.tests.browser.test_browser_exploration_dialogue web.tests.browser.test_vue_foundation web.tests.browser.test_browser_contextual_hud_drawers web.tests.browser.test_browser_title_codex web.tests.browser.test_browser_lineage web.tests.browser.test_browser_reconnect`

## 6. Specs and traceability

- [ ] 6.1 Sync this change's deltas (`openspec archive` at the end, or `openspec-sync-specs` first).
  - `grep -rn "permanently present\|command-line utility strip" openspec/specs` returns nothing.
  - Run `uv run --locked python -m tools.spec_traceability check`; green.

## 7. Validation

- [ ] 7.1 Run every gate from the repository root, all green:
  - `node --test web/static/webclient/js/tests/*.test.js`
  - `pnpm test`
  - `pnpm run build`
  - `pnpm run build-storybook`
  - `pnpm run showcase-coverage`
  - `uv run --locked python -m tools.test_data_lint check`
  - `uv run --locked python -m tools.spec_traceability check`
  - `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.tests.test_node_suite_evidence web.webclient.tests.test_vue_showcase_data_evidence`
- [ ] 7.2 Run `agent-browser` against the running client at 1920x1080 and 1280x720:
  - On load no command row covers the portrait's feet, and ⌨ sits at the message window's bottom-right without covering its last line.
  - `/` opens a 44px row above the message text. `look` + Enter closes it and the dock is focused.
  - Escape closes the row and keeps the draft.
  - 技能系譜 / 圖鑑 / 稱號冊 / 說明 open from the top bar with the line closed.

  Close the browser when done.
- [ ] 7.3 Run `openspec validate webclient-collapsible-command-line --strict` and `git diff --check`; both clean.
