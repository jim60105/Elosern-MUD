# Tasks

## 1. Glyphs and grade gem

- [x] 1.1 Add the sixteen glyph keys from design Decision 7 to `web/webclient-app/components/dock-icons.js` (paths and attrs from `docs/design/quest-drawer-redesign/QuestDrawerPrototype.vue`, plus a new `cat_gather`). Extend `tests/dock_icons.test.js` so every new key yields a path and its attrs. Verify with `pnpm exec vitest run web/webclient-app/tests/dock_icons.test.js`.
- [x] 1.2 Add `components/grade-materials.js` and `components/GradeGem.vue` (sizes `sm`/`md`/`lg`, decorative unless `label` is passed, iron fallback for unknown keys). Add `tests/components/grade_gem.test.js`, covering all seven grades' custom properties, the fallback, the letter always rendered, and the aria-hidden versus labelled forms. Add `stories/World/GradeGem.stories.js` (all grades × sizes, documented with `args`).

## 2. IconTabs

- [x] 2.1 Implement `components/IconTabs.vue` per design Decisions 1 to 4, with tokenized motion and every size in `calc(<n>px * var(--ui-scale))`.
- [x] 2.2 Add `tests/components/icon_tabs.test.js`. Cover roving tabindex, Arrow, Home, and End per orientation with wraparound, Enter and Space selection, selection not following focus, a disabled tab focusable but not selectable with its reason in `aria-describedby`, the badge hidden at zero, the count in the accessible name, `hot`/`locked`/`dim`/`mark` classes, and the `icon` slot. Verify with `pnpm exec vitest run web/webclient-app/tests/components/icon_tabs.test.js`.
- [x] 2.3 Add `stories/Core/IconTabs.stories.js`: horizontal book/counter tabs with the counter disabled and a reason, vertical quest states with badges and a hot badge, and vertical F→S grades using `GradeGem` in the slot with locked, dim, and mark states.

## 3. GuildRankCard extraction

- [x] 3.1 Move the rank block markup, logic, and styles from `GuildCounter.vue` into `components/GuildRankCard.vue` per design Decision 6. Replace `400ms` and `150ms` with `--motion-*` tokens. Render it from `GuildCounter.vue`. Verify that `tests/world/guild_counter.test.js` passes unchanged before task 3.2 moves assertions out of it, and that `tests/motion_tokens.test.js` now passes. Add `tests/world/guild_rank_card.test.js` (3.2) to the Vitest file list in `web/webclient/tests/test_vue_hud_drawer_evidence.py` next to `guild_counter.test.js`.
- [x] 3.2 Add `tests/world/guild_rank_card.test.js`, moving the rank-specific assertions from the counter test (the counter test keeps one integration case proving the card renders inside the counter and its `exam_request` reaches the counter's emit): merit meter clamping, met and short status, the top-rank crest, and the exam request emitted only when enabled. Move the rank-variant stories (`ExamRequestBelowMerit`, `ExamRequestMeritQualified`, `TopRank`, `CounterBusy`, `Unregistered`) into `stories/World/GuildRankCard.stories.js`, keeping `FullCounter`, `GuildAbsent`, and `CounterUnavailable` on the GuildCounter stories.

## 4. Showcase registration and visual review

- [x] 4.1 Add `Core/IconTabs`, `World/GradeGem`, and `World/GuildRankCard` to `web/webclient-app/component-manifest.json`, and update the pinned key sets in the showcase evidence tests (`test_vue_showcase_evidence.py`, `_world_`, `_data_`, `_action_`, `_overlays_`) following the `World/LettersPanel` precedent. Verify with `node scripts/component-coverage.mjs` and `uv run --locked pytest -q web/webclient/tests/test_vue_showcase_*evidence.py`.
- [x] 4.2 Run Storybook, capture the three components at 1451×790 and 1920×1080 with `agent-browser`, and compare them with `Design/QuestDrawerRedesign` (tab geometry, active underline and marker, badge colors, gem materials, and glyph weight). Record any intentional deviation in this change's design.md before closing the task.

## 5. Integration acceptance

- [x] 5.1 Run `pnpm test`, `node scripts/component-coverage.mjs`, `uv run --locked python -m tools.contract_gate`, and `openspec validate quest-drawer-ui-primitives --strict`. Confirm in the live client that the guild counter's rank block is visually unchanged.

## Workflow follow-up

- Do not apply, archive, or merge until the user asks.
