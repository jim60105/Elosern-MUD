# Design

## Context

See `proposal.md`. `use-creation-form.js` owns unsent refs and guarded draft sync; `use-creation-custom.js::confirmCustom` owns age/subrace/budget/persona checks, while native controls supply their existing constraints. `use-creation-proposal.js` performs revision-gated fills and `use-creation-stage.js` mirrors the dock. Keep this ownership and watcher order. This change follows the shell/card wall cutover.

## Goals / Non-Goals

**Goals:** local steps, deterministic error focus, a persistent empty slot and a proposal-driven concept checklist.

**Non-Goals:** new browser creation validation, different bounds, canonical stats, prompt changes, portrait requests, live portrait state or generation buttons.

## Decisions

### Passive form extraction

Create `CreationCustomSteps.vue`, `CreationPortraitSlot.vue`, `CreationConceptGuide.vue` and `composables/use-creation-steps.js`. The overlay still obtains the flat bindings from `useCreationOverlay` and forwards props/events to the children; do not duplicate refs in a second form model. Keep current field `data-testid`s, ids, labels, native control types, direct numeric input and existing submit/reset/confirmation handlers.

`use-creation-steps.js` owns local `currentStep` (`identity`, `story`, `allocation`), `goToStep`, previous/next and a static `FIELD_STEP` map. Identity includes `display_name`, `sex`, `race`, `subrace`, `age`, `apparent_age` and name-roll. Story includes `affinity_elements`, `background` and `persona.personality`, `.life_story`, `.habit`. Allocation includes each `allocations.<axis>` from the existing axis vocabulary. Race description belongs to identity. The rail displays 01/02/03 and the titles from approved §6; each is a native freely navigable button. Remaining points are `currentProfile.budget - allocationTotal`, rendered on the allocation rail entry while every step is active. Invalid values are not clamped. Without a resolved profile show absence rather than fabricate a budget.

Mount fields persistently with visibility switching so native validity can be inspected even when a step is hidden. Hide inactive fields from focus and accessibility. Before the existing submit handler, reveal/focus any invalid native control in display order; otherwise reuse existing custom-error flags. Expose those existing flags/field identifiers as structured presentation data from `useCreationCustom`, rather than parse its localized `formMessage` or reimplement validation. If several existing errors apply, choose the first field in identity/story/allocation display order. Capture native `invalid` events to reveal their step. Server rejections with no field identifier remain in the existing result region; never guess a field from prose. Track an errored step with text plus shape/color, and associate each message with its field. Footer confirmation is mounted on all steps.

### Proposal navigation and guide

Pass `goToStep("identity")` into the existing proposal completion path. A fresh concept apply arriving from concept mode selects custom/identity after the existing revision gate; unchanged rebuilds/remounts do not navigate. Preserve `applyFrozen`, one completion toast, the existing nonblocking persona review and all omitted-field behavior. Show the review prompt above the form across steps.

The guide contains the approved four guiding questions, the approved fill-field list, and the sex/portrait exclusion note. These words are human-reviewed in `visual-review.md`. The completion mechanism reads the proposal’s base/optional keys, checks actual present values (numeric zero is present), and marks only represented field groups. It never marks sex or portrait and never mutates a proposal or prompt. No tests assert the shipped questions or wording.

### Empty slot and layout

The persistent slot is props-only (`name`, `silhouette`), renders `ArtworkPreview` with an alpha mask as decorative `aria-hidden`, and has no action/button. Derive its descriptor by finding the single matching entry of server `custom.silhouettes` for current sex/apparent age; do not duplicate thresholds or invent a matching row for invalid input. Invalid input keeps a neutral empty visual with no new identity validation.

Use the approved fixed portrait column, one-step body and two-column allocation layout with existing tokens. At both reference viewports each normal synthetic step fits without internal step scrolling; user-expanded text may remain scrollable within its native textarea. No new token, text below 16px × scale or page-level horizontal overflow. Styles follow components and replace obsolete three-region declarations.

## Risks / Trade-offs

The inherited transient-fill scenario that demands persona textareas “visible and editable at all times” conflicts with one-step presentation. Its delta makes them visible/editable on the story step while retaining their values elsewhere. The inherited long requirement body is shortened without removing its field-copy/affinity behavior, which remains established by its preserved scenarios.

## Acceptance and documentation

Add `tests/overlays/creation_steps.test.js`; extend `creation_overlay.test.js` and `concept_fill_navigation.test.js`. Use synthetic budgets/fields and assert nonadjacent navigation, preserved edits, zero-valued proposal completion, native and custom error focus, rail arithmetic on all steps, unchanged concept loading/toasts and no generation button. Real-component stories cover all steps, concept pending/partial proposals, errors and the empty slot; register new components. Update the frontend developer guide and record human layout/copy review in this change’s `visual-review.md`.

```text
pnpm exec vitest run web/webclient-app/tests/overlays/creation_steps.test.js web/webclient-app/tests/overlays/creation_overlay.test.js web/webclient-app/tests/overlays/concept_fill_navigation.test.js
pnpm run build
uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_creation_custom
openspec validate creation-stepped-form --strict
```

Browser acceptance remains keyboard-driven at both reference viewports, waits on committed state and checks no page-level horizontal scrolling.
