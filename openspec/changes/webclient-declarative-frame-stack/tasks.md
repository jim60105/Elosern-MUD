# Tasks — webclient-declarative-frame-stack

## 1. Failing regression first

- [ ] 1.1 Extend the existing exploration browser class (`web/tests/browser/test_browser_exploration.py`, three-exit south-gate fixture from `1de5d1d`): open 移動, activate the south exit, assert the move frame lists the new room's exits and re-activation submits the new `exit_ref`/`current_node`; confirm it fails red against the current copy-based router and record the failure as root-cause confirmation

## 2. Declarative router core (UMD, same commit as its Node gate)

- [ ] 2.1 Rework `web/static/webclient/js/elosern/keyboard_router.js`: accept `{descriptor, focusKey}` frames beside the transitional legacy `{menu, focusRow, focusCol}` shape (unknown shapes throw); `createRouter({resolve})`; declarative reads (`currentMenu`/`itemAt`/`move`/`confirm`/`trail`/geometry) resolve at access; legacy frames behave exactly as today
- [ ] 2.2 Declarative focus: same-key geometry, nearest-row fallback with earlier tie, null on empty, confirm writes the activated key back before dispatch, push focuses the first item
- [ ] 2.3 Stack degradation: unresolvable declarative frame pops one level restoring opener focus, cascades while unresolvable, ends at the root frame; an unresolvable root renders the single disabled marker-reason row (fallback 「畫面狀態已更新，請返回上層」) that submits nothing; zero timers
- [ ] 2.4 Update `keyboard_router.test.js`, `ui_contract.test.js`, `hud_dock_menus.test.js` for the dual-frame contract; `node --test web/static/webclient/js/tests/*.test.js` green

## 3. Store exploration cutover

- [ ] 3.1 Convert the exploration push sites in `web/webclient-app/stores/elosern.js` (root, move, look, interact, wait, target `openTarget`, keywords, suggestions) to descriptor pushes through `resolveFrame`
- [ ] 3.2 Delete `rebuildFocusMenu`, `lastMenuSig`, `lastSuggSig`, and `replaceSuggestionsFrameInPlace`; the suggestions frame becomes declarative with the status split (`generating|ready|degraded` resolve to content, `unavailable` exits the frame to the exploration root without a reason row); leave `rehomeFrame`, `dockRawByKey`, and the `router.reset` fuse for the follow-up change
- [ ] 3.3 Teardown decision point posts a one-frame stack: declarative exploration root for exploration, the legacy root copy for combat/creation until their families migrate
- [ ] 3.4 Derive `view.rootMenu`/`view.dockTrail` from the frame stack keeping item shapes; audit `DockMenu.vue`, `ActionDock.vue`, `DockMenuItem.vue`, `DockBreadcrumb.vue` — change bindings only where a source shifted

## 4. Vitest + fixtures

- [ ] 4.1 Store-level Vitest: snapshot commit updates an open Move frame with key-tracked focus; vanished target identity pops one level with opener focus restored; whole-stack loss cascades to root; suggestions `generating` keeps the frame and `unavailable` returns to root with no reason row; pointer pick writes `focusKey` before dispatch; mode switch yields the one-frame stack
- [ ] 4.2 Update `stories/fixtures.js` and affected stories; `npm test`, `npm run build-storybook`, `npm run showcase-coverage` green

## 5. Browser verification and traceability

- [ ] 5.1 Green the 1.1 regression plus browser methods for focus-key survival, one-level pop and cascade (identity loss via fabricated committed snapshots over the test transport where live play cannot produce it), unresolvable-root disabled row, and suggestions `unavailable` exit-to-root — within the one-class local budget; the full managed browser suite stays CI
- [ ] 5.2 After the delta syncs into `openspec/specs/` at archive time: annotate the covering browser methods with `covers_requirement` (IDs from `uv run --locked python -m tools.spec_traceability list`); `tools.spec_traceability check` green

## 6. Gates

- [ ] 6.1 `node --test web/static/webclient/js/tests/*.test.js`, `npm test`, `tools.spec_traceability check`, and `git diff --check` clean; the options-surface and exploration-menu suites run untouched as oracles of the restated contracts
