# Tasks: webclient-align-03-narrative-feed

## 1. Caption shell to draft

- [ ] 1.1 Restyle `NarrativeFeed.vue` caption to the draft's `.feed-inner`: panel fill +
  `backdrop-filter: blur(7px)`, hairline border, radius, shadow, and the left `::before`
  gradient hairline; keep bounded width/height and internal scrolling.
- [ ] 1.2 Add the head row: committed-mode label (`敘述` / `戰鬥日誌`) on the left with the unread
  indicator beside it; move the existing full-log control into the head as the `完整日誌` capsule
  (`--ink-780`, radius 99, gold hover border). Keep its open/focus-trap/Escape/focus-restore
  wiring and the same markup renderer untouched.

## 2. Semantic line classes

- [ ] 2.1 Mount the draft's semantic classes from committed line kinds at the existing render
  mount point: `sys` kind → sans + secondary size/colour + `◈ ` `::before` seal marker; prose
  emphasis → gold `--gold-400`; plain prose stays serif. Tokenize pipeline, `.inp` echo +
  divider, and `.map-art` untouched; markers absent from live-region accessible names.
- [ ] 2.2 Vitest: sys line carries the class and marker is decorative; emphasis gold; plain
  lines gain no semantic class.

## 3. Condition island empty state

- [ ] 3.1 `ConditionChips.vue`: render no island at all when the committed condition list is
  empty (delete the `無條件` statement path); update the contextual-hud empty-state tests.

## 4. Suggestion surface dedupe

- [ ] 4.1 Remove the stream choice-point: delete `ChoicePointBlock.vue`, `lib/choicepoint.js`,
  and the app-side `lib/stream_end_block.js` wrapper; drop its construction from `bridge.js`
  (frozen UMD under `web/static/webclient/js/` untouched); remove the store's choice-point
  layer and the feed-end pinning watcher's block-specific branches (keep plain scroll pinning).
- [ ] 4.2 Ensure the dock 建議 pane is the sole suggestion surface and carries the full status
  contract (generating line in-pane → ready cards in place, degraded rule cards + muted note,
  unavailable/foreign-kind/absent → nothing, `✕ 清除建議` dismiss contract, digit-key picks,
  tab count badge, transport-reset retirement).
- [ ] 4.3 Remove the component from `component-manifest.json` and delete
  `stories/Action/ChoicePointBlock.stories.js` in the same change; run
  `npm run showcase-coverage` to prove the frozen manifest and story tree agree.
- [ ] 4.4 Migrate `tests/action/choice_point_block.test.js` assertions onto the dock pane
  (generating→ready in place, no stream cards, dispatch identity, degraded-only-in-pane,
  dismiss invariant, transport-reset retirement) and delete the old JS test file; retarget the
  evidence-harness paths in `web/webclient/tests/test_node_suite_evidence.py` to the surviving
  vitest files keeping their OLD choice-point ID annotations until archive/sync (checker green),
  then retarget annotations to the new dock-pane IDs at the sync commit (magic-xp P1 precedent).
- [ ] 4.5 Delete `web/tests/browser/test_browser_choicepoints.py` and remove the
  `options-choicepoints` block (index 13) from `.github/browser-shards.json` in the same change;
  keep `ActionLockingTest` coverage by moving it into a surviving shard entry.

## 5. Verification

- [ ] 5.1 Focused Vitest suites (feed, chips, suggestions pane, manifest/deferred gates).
- [ ] 5.2 `uv run --locked python -m tools.spec_traceability check` — the gap for removed IDs
  appears only after archive-sync, so run `check` against the active deltas' expectations.
- [ ] 5.3 Live browser check 1600x900: head labels per mode, sys `◈` lines, empty conditions →
  no island, ready suggestions render only in the 建議 pane with the tab badge counting them.
