# Tasks

## 1. Step model and custom extraction

- [x] 1.1 Add `use-creation-steps.js` and `CreationCustomSteps.vue` with the exact field map in design, preserving existing refs, handlers and test ids. Add `tests/overlays/creation_steps.test.js` for free navigation, unsent value retention, rail budget subtraction and footer confirmation on every step; the focused Vitest command in design must pass.
- [x] 1.2 Expose existing custom-validation error fields without parsing messages; reveal/focus native-invalid controls before invoking the existing submit pipeline. Test identity/story/allocation error destinations and unchanged rejection rules in the same component suite. Expected state is no additional validator and no silent input repair.
- [x] 1.3 Add props-only `CreationPortraitSlot.vue` for the empty state and table lookup in its host; preserve slot across steps and offer no generation button. Extend component tests for table-driven sex/age selection and unnamed/current-name display semantics without pinning wording.

## 2. Concept extraction

- [x] 2.1 Add `CreationConceptGuide.vue`, proposal-presence indicators and identity-step completion navigation in the existing proposal path. Extend `concept_fill_navigation.test.js` for omitted fields, zero values, unchanged revisions/remounts, pending pin, review prompt and one toast. Expected state is no concept text copied into a portrait prompt and no autosave.
- [x] 2.2 Split component CSS, remove obsolete simultaneous-region layout and update real overlay stories for every step, error, guide state and empty slot; register new components. Update the frontend developer guide and produce this change’s human-reviewed `visual-review.md` for approved §§6/8/11. No test asserts questions, copy, shipped data or literal markup.

## 3. Integration acceptance

- [x] 3.1 Run the focused component command in design; build with `pnpm run build` before its focused custom browser module. Verify keyboard completion and no page-level horizontal overflow at both reference viewports, plus normal-step content fitting without internal step scrolling.
- [x] 3.2 Run `pnpm run build-storybook` and `pnpm run showcase-coverage`; register new browser methods via `uv run --locked python -m tools.shard_register fix`, then run `uv run --locked python -m tools.contract_gate` and `openspec validate creation-stepped-form --strict`. All gates must pass without warnings.
