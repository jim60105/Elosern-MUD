# Tasks

Work only in the files named below. Commands run from the repository root. Before any browser run, run `pnpm run build`, because browser tests serve the prebuilt `dist`.

## 1. Tilde point-range formatter (design D1)

- [x] 1.1 In `web/webclient-app/composables/use-creation-custom.js`, add the exported module-scope `formatPointRange(low, high)` that returns `` `${low}~${high}` `` (verbatim from design D1). Use it in `budgetBriefing` (replace `` `${a.label} 0-${a.point_cap}` ``) and in the `capError` assignment inside `confirmCustom` (replace the `0–${outOfCap.point_cap}` token). Change no other text in either string. Verify that `grep -n "0-\${\|0–\${" web/webclient-app/composables/use-creation-custom.js` prints nothing.
- [x] 1.2 In `web/webclient-app/components/CreationCustomSteps.vue`, import `formatPointRange` from `../composables/use-creation-custom.js`. Change the help line `<p :id="`creation-axis-help-${ax.axis}`">` to end in `配點 {{ formatPointRange(0, ax.point_cap) }}`. Verify that `grep -n "0–" web/webclient-app/components/CreationCustomSteps.vue` prints nothing.
- [x] 1.3 Update the two existing range assertions from `` `0–${...point_cap}` `` to `` `0~${...point_cap}` ``: `web/webclient-app/tests/overlays/creation_overlay.test.js` (the "steps only valid allocations…" test) and `web/webclient-app/tests/overlays/creation_steps.test.js` ("an out-of-cap value is reported and focused, and nothing ships"). In `creation_steps.test.js`, add a test "renders every axis point range with a tilde". It mounts `mountDraft()`, opens the allocation step, and for each `DRAFT_PROFILE.axes` entry asserts that `#creation-axis-help-<axis>` text contains `` `0~${axis.point_cap}` `` and does not match `/0[-–]\d/`. It also asserts that `creation-budget-briefing` text contains `` `0~${DRAFT_PROFILE.axes[0].point_cap}` `` and does not match `/0[-–]\d/`. Verify with `pnpm exec vitest run web/webclient-app/tests/overlays/creation_overlay.test.js web/webclient-app/tests/overlays/creation_steps.test.js`, which must pass.

## 2. Allocation slider kept in sync (design D2, D4)

- [x] 2.1 In `CreationCustomSteps.vue`, add `:id="`creation-allocation-label-${ax.axis}`"` to the allocation `<label>`. Replace the `.creation-allocation__bar` div with the slider `<input type="range">` exactly as written in design D2, placed after the `.creation-stepper` div and before the preview `<p>`. Delete the `allocationFraction` function. In `web/webclient-app/components/creation-custom-steps.css`, delete the `.creation-allocation__bar` and `.creation-allocation__bar > span` rules and append the D4 CSS block verbatim. Verify that `grep -n "allocation__bar\|allocationFraction" web/webclient-app/components/` prints nothing.
- [x] 2.2 In `creation_steps.test.js`, add a `describe("CreationCustomSteps: allocation slider")` block with these tests, all built from `DRAFT_PROFILE`:
  - (a) For each axis, `creation-slider-<axis>` has `type="range"`, `min="0"`, `max=String(axis.point_cap)` and `step="1"`, and comes after `creation-field-<axis>` in document order (`compareDocumentPosition`).
  - (b) For an axis with `point_cap > 0`: `setValue` on the slider to a value different from the draft value changes `creation-field-<axis>`'s element value to match. `setValue` on the number field to another in-range value changes the slider's element value to match.
  - (c) Set allocations so the total equals `DRAFT_PROFILE.budget` using slider moves for at least one axis. Fill the remaining confirm prerequisites from the draft as the existing submit tests do. Submit, and assert that the single emitted `creation.custom` payload's `allocations[axis]` equals the slider value.
  - (d) The slider max equals `point_cap` even when the rail remaining count is below `point_cap`. In other words, no budget clamp.
  - (e) Same-render bound change: use a `structuredClone(PANEL)` in which `OTHER_PLAIN`'s profile has the chosen axis's `point_cap` raised to `DRAFT_PROFILE`'s cap + 2 (keep `value_at_cap` within `maximum`; raise `maximum` too if needed). In one tick, `setValue(OTHER_PLAIN.key)` on `creation-race` and set the number field to the new cap. Then assert the slider's element value equals the new cap. If the test fails, apply the `:key` fallback from design Risks.

  Verify with `pnpm exec vitest run web/webclient-app/tests/overlays/creation_steps.test.js`, which must pass. The existing "every rendered field identifier belongs to the static step map" and "out-of-cap value is reported and focused" tests must still pass unchanged, apart from 1.3.

## 3. Zero-cap lock and profile-change clearing (design D3)

- [x] 3.1 In `use-creation-custom.js`, add `clearZeroCapAllocations()` (verbatim from design D3) and call it as the last statement of `onRaceChange()`. Add `onSubraceChange()`, which calls it, and return `onSubraceChange` from `useCreationCustom`. In `CreationCustomSteps.vue`:
  - Destructure `onSubraceChange` from `props.form`.
  - Add `@change="onSubraceChange"` to the subrace `<select>`.
  - Add the D3 `editingAxis` ref and `isLocked(axis)` function.
  - Bind `:disabled="isLocked(ax)"`, `@focus="editingAxis = ax.axis"` and `@blur="editingAxis = null"` on the number input.
  - In `use-creation-custom.js` `confirmCustom`, change the budget-mismatch `formErrorFields` target to the first axis with `point_cap > 0`, exactly as design D3 shows.
  - Bind `:data-locked="isLocked(ax) ? 'true' : null"` on each `.creation-allocation` row.

  The slider's `:disabled="ax.point_cap === 0"` from 2.1 stays. Verify that `grep -n "onSubraceChange" web/webclient-app/composables/use-creation-custom.js web/webclient-app/components/CreationCustomSteps.vue` shows the definition, the return entry, the destructure and the binding.
- [x] 3.2 In `creation_steps.test.js`, add a helper `zeroCapPanel(axisKey, { race, subrace, draftValue })`. It returns a `structuredClone(PANEL)` in which the profiles matching the given race and subrace (or every profile when both are omitted) get `point_cap: 0` and `value_at_cap: <that axis's minimum>` for `axisKey`. When `draftValue` is given, it also sets `draft.allocations[axisKey] = draftValue`. Pick `axisKey` as the first `DRAFT_PROFILE.axes` entry with `point_cap > 0`; never hard-code an axis or race. Add these tests:
  - (a) With `zeroCapPanel(axisKey, { draftValue: 0 })`, the axis number field, slider and both steppers are disabled, and the row has `data-locked="true"`. After balancing the other axes to the budget and submitting, the payload carries `allocations[axisKey] === 0`.
  - (b) Race change: use a panel in which only `OTHER_PLAIN`'s profile has the zero cap, with a non-zero draft value on `axisKey`. `setValue(OTHER_PLAIN.key)` on `creation-race`, then assert that the number field value is `"0"` and the row is locked.
  - (c) Subrace change: use a panel in which only the profile for `SUBRACED.key` and `SUBRACED.subraces[0]` has the zero cap (the story fixture ships that profile). Set a non-zero value on `axisKey` first, select `SUBRACED.key`, then select `SUBRACED.subraces[0]` (if the form already shows that race and subrace, first select a different subrace so a real `change` fires), and assert that the value is zeroed and the row locked.
  - (d) Stale value: with `zeroCapPanel(axisKey, { draftValue: 1 })`, the number field is enabled, the slider is disabled and the row is not locked. Submitting emits no `creation.custom`, focuses `creation-field-<axisKey>`, and `#creation-form-message` contains `0~0`. Then focus the number field, `setValue(0)`, and assert it is still enabled while focused. Trigger `blur` and assert it becomes disabled with the row locked.
  - (e) Budget target: build a `zeroCapPanel` for `DRAFT_PROFILE.axes[0].axis` with `draftValue: 0`, unbalance another axis, and submit. Assert that no `creation.custom` is emitted, and that focus and `aria-invalid="true"` land on `creation-field-<first axis with point_cap > 0>`.

  Verify with `pnpm exec vitest run web/webclient-app/tests/overlays/creation_steps.test.js web/webclient-app/tests/overlays/creation_overlay.test.js web/webclient-app/tests/overlays/concept_fill_navigation.test.js`, which must pass.

## 4. Browser acceptance for the modified requirement

- [ ] 4.1 In `web/tests/browser/test_browser_creation_viewport_pointer.py`, add the method `test_allocation_slider_tilde_range_and_zero_cap_lock` to `ViewportCreationJourney`, decorated with `@covers_requirement("webclient-character-creation-ui::creation-controls-preserve-native-entry-and-existing-authority")`. Steps:
  1. Open the custom form exactly as the first test does (`self._login_creation((1451, 790))`, `install_outbound_recorder`, `_wait_creation_available`, `_focus_dock`, ArrowDown, Enter, then the same `wait_for_store_state` readiness).
  2. On the identity tab, select subrace index 0 if a subrace select exists, then click the allocation tab.
  3. Walk the seven axis keys `hp, mp, sp, atk_phys, agility, defense, magic_power` and take the first two whose `creation-field-<axis>` `max` attribute is greater than 0 as A and B.
  4. For A, assert the slider's `min == "0"`, `max ==` the number field's `max` and `step == "1"`. `slider.fill(t)` must make the number field's `input_value() == t`, and `number.fill(t2)` must make the slider's `input_value() == t2`, where `t` and `t2` are distinct in-range values. Assert that `#creation-axis-help-A` text contains `f"0~{max_a}"`.
  5. For B, `fill("0")` its number field. Copy `self._creation_panel(page)` with `copy.deepcopy`. In every `custom.profiles` entry, set B's `point_cap = 0` and `value_at_cap = minimum`. Send it with `inject_update(page, {"creation": panel}, mode="creation")`.
  6. Wait with `page.wait_for_function` until `creation-slider-B` has `max == "0"`. Then assert that `creation-field-B`, `creation-slider-B`, `creation-step-B-up` and `creation-step-B-down` are disabled, and that the row (the closest `.creation-allocation`) has `data-locked == "true"`.

  Verify with `pnpm run build`, then `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_creation_viewport_pointer.ViewportCreationJourney`. Both methods must pass. If the existing method's allocation no-scroll assertion fails, apply the design Risks fallback in order (row gap, then slider height, then preview margin) and re-run. Never weaken the assertion.
- [ ] 4.2 Run `uv run --locked python -m tools.spec_traceability check` and `uv run --locked python -m tools.contract_gate`. Both must exit 0 with no new uncovered requirement.

## 5. Integration check

- [ ] 5.1 Run `pnpm exec vitest run web/webclient-app/tests/overlays web/webclient-app/tests/preserved_contract.test.js` and `pnpm run build`. Both must pass. Confirm that `git status --short` lists only the files named in this task list plus this change's `tasks.md`.

## Workflow follow-up

- A human reviewer checks the design's "Human review: allocation slider and locked-axis styling" section at 1451x790 and 2560x1440 before archive.
