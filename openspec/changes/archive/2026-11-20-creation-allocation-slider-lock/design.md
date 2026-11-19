# Design

## Context

See proposal.md, Why. Current state, observed in code:

- `web/webclient-app/components/CreationCustomSteps.vue` renders one `.creation-allocation` row per `currentProfile.axes` entry. Each row has a `<label for="creation-allocation-<axis>">`, a help line `<p id="creation-axis-help-<axis>">` ending in `配點 0–{{ ax.point_cap }}` (en dash), a `.creation-stepper` with the down button, the `type="number"` input (`data-testid="creation-field-<axis>"`, `v-model.number="allocations[ax.axis]"`, `v-bind="fieldAttrs(...)"`) and the up button. After them comes a decorative `aria-hidden` `.creation-allocation__bar` driven by `allocationFraction(axis)`, then the preview line.
- `canStep(axis, direction)` already disables both steppers when `point_cap === 0` (no step stays inside `0..0`) and for any value outside `0..point_cap`.
- `web/webclient-app/composables/use-creation-custom.js` builds `budgetBriefing` with `` `${a.label} 0-${a.point_cap}` `` (hyphen) and the out-of-cap `capError` with `` `${outOfCap.label} 配點需為 0–${outOfCap.point_cap} 的整數` `` (en dash). `onRaceChange()` is bound to the race `<select @change>`. The subrace `<select>` has no change handler. `currentProfile` is a strict `(race, subrace)` match. The facade `use-creation-overlay.js` spreads every key returned by `useCreationCustom` into the form binding, so a new returned handler reaches the SFC with no facade edit.
- `allocations` is the reactive seven-key object from `use-creation-form.js`. Race and subrace changes never reset it today.
- Focus routing (`elementOf(field)` and `submit()`) takes the FIRST element in DOM order whose `data-creation-field` matches. `submit()` skips disabled elements when it checks native validity.
- The browser test `web/tests/browser/test_browser_creation_viewport_pointer.py::ViewportCreationJourney.test_reference_viewport_keeps_creation_essentials_visible_and_literal` is already annotated with `webclient-character-creation-ui::creation-controls-preserve-native-entry-and-existing-authority`. It asserts that each step fits `.creation-steps__pages` without internal scrolling (`scrollHeight - clientHeight <= 1`) at 1451x790, 1741x948 and 2560x1440. It also focuses every enabled `input, select, textarea` and checks that each one sits above the footer.
- Traceability: only Python tests carry `@covers_requirement`. Because this change MODIFIES an existing requirement, its ID does not change, so no re-annotation is needed at archive.

## Goals / Non-Goals

**Goals:** the three behaviors in the spec delta, delivered through the existing form state with no new form model and no new validation rule.

**Non-Goals:**
- `web/static/webclient/js/elosern/creation_menu.js`: the keyboard dock keeps its own `0–` validation text.
- `commands/character_creation.py` and the text wizard.
- Server policy, protocol schema version, and decoders.
- Clamping to the remaining budget. The rail's "剩餘" count and `confirmCustom` stay the only budget surfaces.
- Changing `canStep`, `previewValue`, `confirmCustom` ordering or any `formMessage` text other than the range token.
- Tests that pin game data. Every test builds zero-cap profiles synthetically from the story fixtures.

## Decisions

### D1. One range formatter, exported from the composable

Add this to `use-creation-custom.js` (module scope, exported):

```js
// Every allocation point range in the custom form reads `low~high`.
export function formatPointRange(low, high) {
  return `${low}~${high}`;
}
```

Use it in exactly three places:
- `budgetBriefing`: `` `${a.label} ${formatPointRange(0, a.point_cap)}` ``.
- `capError`: `` `${outOfCap.label} 配點需為 ${formatPointRange(0, outOfCap.point_cap)} 的整數` ``.
- The SFC help line: `{{ ax.explanation }} ‧ 配點 {{ formatPointRange(0, ax.point_cap) }}`. Import it with `import { formatPointRange } from "../composables/use-creation-custom.js";`.

Alternative rejected: a CSS or template literal at each site. Three hand-written literals would drift again, which is what produced today's mix of `-` and `–`.

### D2. Slider replaces the decorative bar and binds the same model

In each `.creation-allocation` row, replace the `.creation-allocation__bar` div with the slider. Keep it AFTER `.creation-stepper` in DOM order so `elementOf()` still resolves the number input first.

```html
<input
  :id="`creation-slider-${ax.axis}`"
  type="range"
  class="creation-allocation__slider"
  min="0"
  :max="ax.point_cap"
  step="1"
  :aria-labelledby="`creation-allocation-label-${ax.axis}`"
  v-bind="fieldAttrs(`allocations.${ax.axis}`, `creation-axis-help-${ax.axis}`)"
  :disabled="ax.point_cap === 0"
  v-model.number="allocations[ax.axis]"
  :data-testid="`creation-slider-${ax.axis}`"
/>
```

Add `:id="`creation-allocation-label-${ax.axis}`"` to the existing `<label>`; its `for` stays on the number input. Delete `allocationFraction()` and the bar markup. In `creation-custom-steps.css`, delete the `.creation-allocation__bar` and `.creation-allocation__bar > span` rules.

The slider carries `data-creation-field`, so the existing capture-phase `onEdit` retires the allocation step's reported errors when the player drags it, and the "every rendered field identifier belongs to the static step map" test still holds because `allocations.<axis>` is already in `FIELD_STEP`.

Alternatives rejected:
- A separate slider value with watchers. It would create a second form model.
- Clamping the slider max to the remaining budget. The spec forbids new budget rules, and a moving max would confuse players.
- Keeping the bar next to the slider. Both would show the same fraction.

### D3. Lock rule and its two inputs

Add this to the SFC script:

```js
// A zero-cap axis admits no points. It locks only while its value is already
// zero, so a stale non-zero value stays correctable through the number field.
// The axis whose number field holds focus never locks mid-edit (clearing a
// stale value to 0 must not drop keyboard/IME focus); it locks on blur.
const editingAxis = ref(null);
function isLocked(axis) {
  return axis.point_cap === 0 && allocations[axis.axis] === 0 && editingAxis.value !== axis.axis;
}
```

The number input also gets `@focus="editingAxis = ax.axis"` and `@blur="editingAxis = null"` (`ref` is already imported from `vue`).

- Number input: add `:disabled="isLocked(ax)"`.
- Slider: `:disabled="ax.point_cap === 0"`. A `0..0` slider can never express a correction.
- Steppers: unchanged. `canStep` already disables both for cap 0.
- Row: add `:data-locked="isLocked(ax) ? 'true' : null"` on `.creation-allocation`.

Add this to `use-creation-custom.js` and return `onSubraceChange` from `useCreationCustom`:

```js
// A user-driven profile change zeroes the new profile's zero-cap axes so they
// lock at once. Draft sync and proposal fill never call this.
function clearZeroCapAllocations() {
  const profile = currentProfile.value;
  if (!profile) return;
  for (const axis of profile.axes) {
    if (axis.point_cap === 0) allocations[axis.axis] = 0;
  }
}
```

Call `clearZeroCapAllocations()` as the last statement of `onRaceChange()`. Add `function onSubraceChange() { clearZeroCapAllocations(); }`. In the SFC, destructure `onSubraceChange` from `props.form` and bind `@change="onSubraceChange"` on the subrace `<select data-testid="creation-subrace">`. These handlers run on user `change` events after `v-model` updates the ref, the same ordering `onRaceChange` already relies on. Because they are user input, it is correct that they mark `formTouched`.

Budget-error target: in `confirmCustom`, the budget-mismatch branch currently sets `formErrorFields.value = profile.axes?.[0] ? [...] : []`. Change it to target the first axis with `point_cap > 0`, falling back to `axes[0]` only when none exists:

```js
const target = profile.axes?.find((axis) => axis.point_cap > 0) ?? profile.axes?.[0];
formErrorFields.value = target ? [`allocations.${target.axis}`] : [];
```

Otherwise a profile whose first axis is zero-cap would point the error at a disabled field that cannot take focus.

Alternatives rejected:
- Disabling whenever `point_cap === 0`. A stale non-zero value would then be stuck behind a disabled field that `confirmCustom` points at.
- A `watch(currentProfile)`. It would also fire on draft sync and proposal fill, outside the `syncingDraft` guard, and would mark the form touched.

### D4. Styling with existing tokens only

Append to `creation-custom-steps.css`:

```css
.creation-allocation__slider {
  grid-column: 1 / -1;
  width: 100%;
  height: calc(20px * var(--ui-scale));
  margin: var(--sp-1) 0 0;
  accent-color: var(--gold-500);
  cursor: pointer;
}
.creation-allocation__slider:focus-visible { outline: none; box-shadow: var(--focus); }
.creation-stepper input:disabled,
.creation-allocation__slider:disabled { color: var(--paper-500); cursor: not-allowed; opacity: 0.55; }
.creation-allocation[data-locked="true"] .creation-allocation__label { color: var(--paper-500); }
```

Add no new text, so the 16px floor is unaffected.

## Risks / Trade-offs

- [The slider row is taller than the 3px bar, so the allocation step may overflow `.creation-steps__pages` at 1451x790] → Run the viewport browser test. If its "allocation" no-scroll assertion fails, change the `.creation-allocations` `gap` from `var(--sp-4) calc(var(--sp-6) * 2)` to `var(--sp-3) calc(var(--sp-6) * 2)`. If it still fails, also lower the slider `height` to `calc(16px * var(--ui-scale))`. If it still fails, set the preview `<p>`'s top margin to `0` by adding a `.creation-allocation__preview { margin-top: 0; }` class on that paragraph. Record the measured overflow (`scrollHeight - clientHeight`) in the apply report at each step. Do not weaken the assertion.
- [When `point_cap` and the model change in the same render (race change or draft resume), the DOM could clamp the slider value to the old `max`] → The template lists `:max` before `v-model`. Task 2.2(e) tests this case. If that test fails, add `:key="`${ax.axis}:${ax.point_cap}`"` to the slider so it is recreated with the new bound.
- [The slider shows a clamped position while the number field holds an out-of-range or empty value] → Accepted. The number field stays the source of truth, and the existing out-of-cap error path reports the value.
- [A resumed draft or proposal fill could carry a non-zero value on a zero-cap axis] → The server validates both against the same profile, so this should not happen. If it does, D3 keeps the number field enabled.
- [`inject_update` rejects a panel that is not schema-valid] → The browser test copies the live panel and changes only `point_cap`/`value_at_cap` on one axis, keeping `value_at_cap == minimum` as the decoder requires for zero cap. A rejection raises immediately, so the failure is loud.

## Human review: allocation slider and locked-axis styling

A human reviewer checks this section at 1451x790 and 2560x1440 against the existing ink/gold theme. No test checks it.
- The slider thumb and track read as part of the gold-accent theme and do not crowd the stepper column.
- Locked rows (custom elf zero-cap axes) look clearly muted but remain legible.
- Focus rings on the slider match the other creation controls.

## Migration Plan

None. The change is pre-release, client-only, and has no stored state.
