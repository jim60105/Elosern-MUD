## 0. Ground rules (apply to every task)

- Frontend-only (`web/webclient-app/**`); zero visual change; run JS gates with pnpm, never
  the Evennia suite. `pnpm test` from the repo root (per AGENTS.md), never CI shard commands.
- No file renames; `pnpm run showcase-coverage` required-set manifest untouched.

## 1. Condition label util

- [x] 1.1 Create `web/webclient-app/lib/condition_label.js` exporting
  `conditionLabel(condition)` — byte-identical body of `ConditionChips.vue:50-62` (zh-TW
  `剩 ${...} 秒` and `，` join preserved).
- [x] 1.2 Replace `ConditionChips.vue::chipName` (lines 50-62) and
  `CharacterStatusDrawer.vue::conditionName` (lines 147-159) with imports + one-line
  delegates (`const chipName = conditionLabel;` / `const conditionName = conditionLabel;`),
  keeping each component's explanatory comment. Verify:
  `pnpm test -- tests/data/condition_chips.test.js tests/data/character_status_drawer.test.js tests/data/breakdown_rendering.test.js`
  (paths relative to `web/webclient-app/`; adjust to the actual test paths —
  `condition_chips.test.js` and `character_status_drawer.test.js` live under
  `tests/data/`).
- [x] 1.3 Add `web/webclient-app/tests/data/condition_label.test.js` pinning the extracted
  rule directly: label-else-code fallback, `剩 N 秒` suffix only for numeric
  `remaining_seconds`, modifier pairs joined, `，` separator (fails pre-extraction only in
  the sense that it now guards the single copy). Verify: `pnpm test`.

## 2. Narrative line util

- [x] 2.1 Create `web/webclient-app/lib/narrative_line_nodes.js` exporting
  `lineText(line)` and `narrativeLineNodes(line, index)` per design D2 (imports `h` from vue,
  `NarrativeMarkup` from `./narrative_markup.js`, `renderNarrativeTokens` from
  `../components/narrative-renderer.js`; `BOX_DRAWING = /[\u2500-\u257f]/` once).
- [x] 2.2 Delete the local `BOX_DRAWING`/`lineText`/`lineNodes` copies in
  `FullLogOverlay.vue` (lines 82-120) and `NarrativeFeed.vue` (lines 70, 73-77, 146-178),
  importing the util instead; keep each component's design-note comment. Verify:
  `pnpm test -- tests/narrative_feed.test.js tests/full_log_overlay.test.js`
  (paths relative to `web/webclient-app/tests/`).
- [x] 2.3 Add `web/webclient-app/tests/narrative_line_nodes.test.js`: an `in` line at
  index 0 renders no divider, at index > 0 renders `narrative-divider` before the literal
  `.inp` line; a box-drawing line gets the `map-art` class; the escaped `BOX_DRAWING` form
  agrees with the literal-glyph form `/[─-╿]/` on both a `─` sample and a CJK sample
  (design D2's equivalence assertion). Verify: `pnpm test` (full Vitest suite green).
- [x] 2.4 Build gate: `pnpm run build` succeeds (new lib modules enter the Vite graph) and
  `pnpm run showcase-coverage` passes unchanged.

## 3. Store `readPanel` helper

- [x] 3.1 In `web/webclient-app/stores/elosern.js`, add the module-private
  `readPanel(rs, key)` per design D3 and replace the five
  `(rs.panels && rs.panels.<key>) || null` reads in `buildView`
  (`status`/vitals if it uses the same shape, `party`, `objectives`, `roster`,
  `exploration`; locate via `grep -n "rs.panels && rs.panels" stores/elosern.js`). Leave
  every `available === true` / `available !== false` / `Array.isArray` guard verbatim.
  Verify: `pnpm test -- tests/store tests/app_client_drawers.test.js tests/app_client_gallery.test.js`
  — then full `pnpm test`.

## 4. Close-out

- [x] 4.1 `git diff --stat` names only `web/webclient-app/**`; `git diff --check` clean.
- [x] 4.2 Full `pnpm test` green with ZERO test-file edits besides the two new test files.
