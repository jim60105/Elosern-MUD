## 1. Freeze the contract and record the serialize before any DOM moves

- [ ] 1.1 Amend the roadmap's delivery table (§6): H5's "Depends on" cell becomes `H1, H2, H3`, because H5 adds the minimap island's full-map control that H2's `webclient-local-map` delta deferred to this wave (roadmap §9 governance amendment, design D9)
- [ ] 1.2 Enumerate the identifiers this change must not move (`#inputfield` inside its `.inputfieldwrapper`, `#action-dock` with its `data-mode`, `tabindex` and listbox composite role, `#elosern-action-live`, `#elosern-offline-overlay`, `#narrative-unread`, `data-testid="narrative-feed"`, `data-testid="action-dock"`, the `action-*` / `target-*` item keys, and `layout_store.js`'s `REQUIRED_COMPONENTS` entry `command-drawer`) and extend `tests/preserved_contract.test.js` to assert each after the command-line rewrite
- [ ] 1.3 Grep `web/tests/browser/` for `#inputfield`, `data-testid="command-drawer"`, `drawer-entry` and `aria-expanded`, list the nine affected files in the change, and confirm `#inputfield` appears in the preserved list rather than the re-map list; the re-map lands in group 8

## 2. The persistent command line

- [ ] 2.1 Rewrite `components/CommandDrawer.vue` as `components/CommandLine.vue`: one always-rendered bar (chip cluster, `›` prompt chevron, `#inputfield` inside its preserved `.inputfieldwrapper`, hint cluster, history controls, utility controls) with no `open` prop, no `toggle` emit, no entry button and no `aria-expanded`
- [ ] 2.2 Keep the single send implementation byte-for-byte in behaviour: Enter without Shift sends exactly one command, Shift+Enter inserts a newline, a successful ordinary send clears the field and keeps focus, and a rejected send (offline or mutations locked) preserves the typed text
- [ ] 2.3 Keep the ArrowUp/ArrowDown history walk with the draft preserved across the walk, and bind the 上一筆 / 下一筆 buttons to that same walk state (one walk, two input paths; neither button submits)
- [ ] 2.4 Retire `data-testid="command-drawer"` and its `-entry` / `-input` / `-prompt` / `-send` children to `command-line` / `command-line-input` / `command-line-prompt` / `command-line-send`; leave `#inputfield` and `.inputfieldwrapper` untouched
- [ ] 2.5 Style the bar to the draft's geometry inside H1's 46px `command-line` anchor: the field is `flex:1; min-width:0` with a focus-within gold ring, the chip cluster is `flex:none`, and at narrow widths the hint cluster is dropped first, then the chip cluster scrolls — the field, the history controls and the utility controls are never dropped
- [ ] 2.6 Vitest: the field is present and focusable on mount with no opening action; no element reports `aria-expanded`; the history walk restores the draft; the history buttons emit no submit

## 3. `/`, Escape, and the borrowed dialogue

- [ ] 3.1 Replace `AppShell.vue`'s `/` toggle with a focus claim: outside an editable, `/` focuses `#inputfield` and calls `preventDefault()` so no literal `/` is inserted; inside any editable (the command field included) `/` is never claimed and types a literal slash
- [ ] 3.2 Collapse `openDrawer` / `closeDrawer` / `toggleDrawer` into `focusCommandField()` / `releaseCommandField()` and publish those through `defineExpose`, so the dock's free-form borrow has exactly one call to make; keep `restoreDockFocus()` as the single focus-rescue path
- [ ] 3.3 Escape from the focused field sends nothing and returns focus to `#action-dock`; implement the precedence ladder explicitly — topmost open overlay, then an open drawer (H4), then the focused command field, then the dock's menu level — with each rung consuming the key and stopping
- [ ] 3.4 Re-express the borrowed free-form dialogue: a successful send clears the field and returns focus to the dock; a locked send dispatches nothing, keeps the speech and keeps focus in the field; the borrow is released whenever focus leaves the field for any reason other than that dock's own successful send, and whenever a send is routed as ordinary text
- [ ] 3.5 Remove the creation-mode drawer-close branch from `AppShell.vue`'s mode watcher (there is no drawer to close) and keep the focus rescue that runs before the anchor is hidden
- [ ] 3.6 Vitest: `/` from the dock focuses the field and inserts nothing; `/` inside the field types a slash; `/` then Escape is a round trip back to `#action-dock`; a cancelled free-form dialogue cannot capture a later ordinary command

## 4. Quick-word chips

- [ ] 4.1 Add `components/QuickWordChips.vue`: buttons whose visible label is the literal command verb they insert, writing that verb plus a trailing space into the field and focusing it, never submitting
- [ ] 4.2 Populate the v1 sets from the installed command set — exploration `看` / `拿` / `說` / `交談` / `等待`, combat `說` / `施法` — and render no mnemonic key badge, because no key is bound and the label is already the verb
- [ ] 4.3 Gate the sets on the committed mode through the stage's `data-elosern-mode` attribute using `display:none`, so a chip that does not apply to the mode leaves the tab order rather than being dimmed
- [ ] 4.4 Storybook story with deterministic offline args for the exploration set, the combat set and a locked client
- [ ] 4.5 Vitest: a chip populates and focuses without emitting a submit; no combat chip is in the exploration tab order and vice versa; every chip's inserted text equals its label plus a trailing space

## 5. The shared full-overlay surface

- [ ] 5.1 Add `components/OverlayHost.vue`: a fixed full-viewport surface above the stage with the draft's `.full` header row (icon slot, title, subtitle, labelled close control) and a scrolling body slot
- [ ] 5.2 Trap focus through H4's `components/focus-trap.js` — do not write a second trap — and close on Escape and on the close control, restoring focus to the trigger on every path
- [ ] 5.3 Add the store slice: `openOverlay(name)` / `closeOverlay()` over `map | settings | help`, published as `view.hudOverlay`, with at most one overlay open, opening an overlay closing any open drawer and vice versa, and a forced close on a mode change into creation, an epoch reset and a transport loss
- [ ] 5.4 Register an open overlay into the open-surface array `AppClient.vue` already computes, so H1's `menu-open` stage recession applies with no second mechanism
- [ ] 5.5 Leave `CreationOverlay` outside the single-open stack: it is mode-driven, not player-opened, and a settings click must never dismiss a character-creation wizard
- [ ] 5.6 Storybook story and Vitest: two overlays are never open at once; Escape and the close control each restore focus to the trigger; the recession mark clears only when nothing is open

## 6. Wiring the three overlays to real triggers

- [ ] 6.1 Strip `MapOverlay.vue`, `SettingsOverlay.vue` and `HelpOverlay.vue` of their own modal chrome (`position`, `z-index`, close buttons, `aria-modal`) and mount their bodies inside `OverlayHost`
- [ ] 6.2 Add the minimap island's `展開全地圖` control to `components/LocalMap.vue` as a sibling of the lattice on the island's header row — never a wrapper around the actionable move nodes — satisfying H2's "a full-map affordance SHALL exist only once the full-map surface it opens is reachable" (the forced serialize of task 1.1)
- [ ] 6.3 Add the 設定 and 說明 controls to the command line's utility strip with accessible names, as ordinary tab stops reachable from the field
- [ ] 6.4 Mount all three overlays from `AppClient.vue` through `OverlayHost`, passing `store.view.localMapModel` to the map overlay so a replaced `local_map` payload re-renders the available/unavailable branch live — the first time `webclient-component-showcase`'s read-model-update requirement is observable outside Storybook
- [ ] 6.5 Drop the map overlay's `滾輪縮放 · 拖曳平移` hint and ship no zoom or pan; render no bearing, compass angle or distance, inheriting H2's orientation-legend rule rather than restating it
- [ ] 6.6 Add `lib/controls-reference.js` (the client's own key and command reference) and render it as the help overlay's control section, with one line stating that the game's own `help` output is reached by typing `help` into the field; leave the `guide` sections rendering only when a payload supplies them
- [ ] 6.7 Vitest: each trigger opens exactly its own overlay; the map overlay re-renders on a replaced payload with no stale state; the help overlay renders no invented game-help copy when `guide` is empty

## 7. Settings, persistence and the prose scale

- [ ] 7.1 Add `--prose-scale: 1` to `styles/tokens.css` and multiply it into the narrative and dialogue prose sizes only — the caption card's lines, the full-log overlay's lines and the prompt line — never into `--text-sm` / `--text-body` or any HUD, dock, drawer or overlay chrome
- [ ] 7.2 Replace `SettingsOverlay.vue`'s 90/100/110/125% type-scale select with the draft's A−/A/A+ segmented control at `[0.92, 1, 1.12]`, with the current step marked by a non-colour indicator
- [ ] 7.3 Remove the invented font-family select: the design system's three self-hosted faces are role-assigned and the binding design reference has no such control
- [ ] 7.4 Remove every `options.*` dispatch from `SettingsOverlay.vue`; `options.dismiss` remains the only allowlisted `options.*` action and this wave does not touch the allowlist
- [ ] 7.5 Persist the prose scale as `fontScale` and the narrative-pipeline toggle as `text2html` through `layout_store.js`'s existing harmless-display-preference lane, and add `reducedMotion` and `colorblind` to `PREFERENCE_TYPES` — additive only, no layout-version bump, because a version-1 wrapper lacking the keys already normalizes cleanly
- [ ] 7.6 Apply every preference to the document's presentation tokens at load and on change, with the reduced-motion control acting as an override over the OS `prefers-reduced-motion` query rather than replacing it
- [ ] 7.7 Scope the text-to-HTML preference to whether narrative lines run through the allowlist pipeline or render as literal text; it never widens the allowlist and the markup grammar is untouched
- [ ] 7.8 Vitest: no settings control emits a `ui_action`; each preference round-trips through the layout store and re-applies at load; an unknown stored version resets to the default with every preference re-applied rather than half-applied; the three prose-scale steps land within `fontScale`'s 0.5–2.0 bounds

## 8. Manifest, showcase gate and browser re-map

- [ ] 8.1 Rename `Core/CommandDrawer` → `Core/CommandLine` in `component-manifest.json` and add `Core/QuickWordChips` and `Overlays/OverlayHost`, renaming `stories/Core/CommandDrawer.stories.js` in the same change so the manifest and the story titles move together
- [ ] 8.2 Raise the frozen count in `tests/overlays/deferred_surfaces_absent.test.js` by exactly two from whatever count H2/H3/H4 leave — never a hard-coded number — and run `npm run build-storybook` and `npm run showcase-coverage`
- [ ] 8.3 Extend `tests/overlays/deferred_surfaces_absent.test.js` with this wave's deferrals and what each waits on: the draft's 分類 → 條目 → 子主題 game-help browser (an OOB panel carrying `help` content), the audio-volume rows (no audio subsystem), the `HUD 縮放` slider and 重映射 control, and map zoom/pan
- [ ] 8.4 Re-map `test_browser_shell.py` and `test_browser_input_narrative.py` off `.drawer-entry`, `aria-expanded`, `data-open` and the `command-drawer` testids onto the command-line hooks; delete the open/close-cycle cases and replace them with the `/`-focus, Escape-return and always-present-field cases
- [ ] 8.5 Re-map `test_vue_foundation.py` (the required-testid list at :68-69 and the entry-button open flow), `test_browser_layout.py` (:34 and :268), `browser_helpers.py` (:35), `test_browser_wait_helper.py` (the bounded-wait fixtures) and `test_browser_exploration.py`; update `test_browser_art.py`'s stale docstring at :386
- [ ] 8.6 Assert in the browser that `#inputfield` is present, visible and unchanged in exploration and combat with no opening action, and absent from the layout in creation mode per H1's matrix
- [ ] 8.7 Add browser assertions for the overlay contract: each trigger opens exactly one overlay, Escape closes it and restores focus to its trigger, opening a second closes the first, and the stage carries the recession mark only while one is open
- [ ] 8.8 Add a browser assertion that the command line does not overlap the dock, the caption or the HUD anchors at **both** 1440x900 and 1280x720, at **each** of the three prose-scale steps
- [ ] 8.9 Re-run the offline-degradation regression: bundle blocked → text playable; `local_map` unavailable → the map overlay renders only the registry-owned reason and the trigger still opens it

## 9. Gates and handoff

- [ ] 9.1 `npm test`, `npm run build`, `npm run build-storybook`, `npm run showcase-coverage` green
- [ ] 9.2 `node --test web/static/webclient/js/tests/*.test.js` green, with a case for the two added `PREFERENCE_TYPES` keys asserting a version-1 wrapper without them still normalizes and no version bump occurs
- [ ] 9.3 `uv run --locked python -m tools.spec_traceability check` green; new requirements carry `@covers_requirement` annotations
- [ ] 9.4 `openspec validate webclient-hud-05-overlays-and-command-line --strict` passes
- [ ] 9.5 Rebuild `web/static/webclient/app/dist` and verify the running client at both supported viewports: the field is typeable without an opening action, all three overlays open from their triggers, and the prose scale persists across a reload
- [ ] 9.6 Flip the roadmap's H5 Status cell to `Done`
