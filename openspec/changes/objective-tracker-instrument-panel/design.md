# Design

## Context

- `web/webclient-app/components/ObjectiveTracker.vue` (HEAD 20b9f0c4): root `<div v-if="first" class="obj" data-testid="objective-tracker" role="region" aria-label="目標">` holding `.obj__label` (visible 目標), `.bx` (`objective-tracker__box--{quest_id}`, class `done` and a check SVG only when done), `.txt` (`objective-tracker__text--{quest_id}`, `title`), `.pr` (`objective-tracker__progress--{quest_id}` with `{{stage_progress}}/{{objective_quantity}}`, or `objective-tracker__reward--{quest_id}` with `+{{reward_copper}}`), `.n` (`objective-tracker__more`, `+{{rest}}`, `title`). Scoped `.obj` is a 32px boxed pill (`height`, `align-self: flex-end`, padding, `--panel` fill with a gold wash, blur, `border: var(--line)`, radius, shadow).
- `HudFrame.vue` hides the line outside exploration with `.elosern-stage:not([data-elosern-mode="exploration"]) [data-anchor="map"] .obj { display: none }`, so the root must keep the class `obj`.
- `place-card-instrument-panel` created `components/instrument-panel.css` (`.instrument-panel`, padding 12/26/6/10 × S by default). `local-map-instrument-panel` changed the anchor's second child to `local-map-panel`.
- The approved prototype is `docs/design/map-column-instrument-panels/ObjectiveLineInstrument.vue`.

## Goals / Non-Goals

**Goals:**

- The tracker as an instrument panel with the prototype's line, completion lozenge, quantity strokes, tabular readout and glyph count, keeping every existing `data-testid`.

**Non-Goals:**

- Any change to the `rows` prop, the first-row-only rule, the display-only contract, `AppClient.vue`'s `showObjectiveTracker` gate, the quest drawer or the `objectives` panel.
- A tooltip or disclosure for further rows (they stay in the quest drawer).
- Animating progress changes.

## Decisions

### D1. Script

Keep `safeRows`, `first`, `rest`, `isDone`. Add, verbatim:

```js
import "./instrument-panel.css";

// One tick per unit reads up to this many; above it the quantity is one
// continuous stroke, so the ticks never shrink below a readable width.
const TICK_LIMIT = 12;

const quantity = computed(() => {
  const value = Number(first.value?.objective_quantity);
  return Number.isFinite(value) ? value : 0;
});
const counted = computed(() => quantity.value > 1);
const progress = computed(() => {
  const value = Number(first.value?.stage_progress);
  return Math.max(0, Math.min(quantity.value, Number.isFinite(value) ? value : 0));
});
const done = computed(() => isDone(first.value));
const ticked = computed(() => counted.value && quantity.value <= TICK_LIMIT);
const ratio = computed(() => (quantity.value > 0 ? progress.value / quantity.value : 0));
```

Rewrite the header comment: the tracker is an instrument panel (objective-tracker-instrument-panel); 目標 is the region's accessible name only; the lozenge states completion by shape and accessible name; counted objectives restate the quantity as ticks (≤ 12) or one tapering stroke; the further-rows count is a stacked-lines glyph with an accessible name.

### D2. Template

```html
<template>
  <div
    v-if="first"
    class="obj instrument-panel"
    :class="{ 'obj--done': done }"
    data-testid="objective-tracker"
    role="region"
    aria-label="目標"
  >
    <div class="obj__line">
      <span
        class="bx"
        :class="{ done }"
        role="img"
        :aria-label="done ? '已達成' : '進行中'"
        :data-testid="`objective-tracker__box--${first.quest_id}`"
      >
        <svg viewBox="0 0 12 12" aria-hidden="true">
          <path class="bx__lozenge" d="M6 .9 11.1 6 6 11.1 .9 6Z" />
          <path v-if="done" class="bx__check" d="M3.6 6.2 5.4 7.9 8.5 4.4" />
        </svg>
      </span>
      <span
        class="txt"
        :data-testid="`objective-tracker__text--${first.quest_id}`"
        :title="first.objective_line"
      >{{ first.objective_line }}</span>
      <span
        v-if="counted"
        class="pr pr--count"
        :data-testid="`objective-tracker__progress--${first.quest_id}`"
      ><b>{{ first.stage_progress }}</b><i>/ {{ first.objective_quantity }}</i></span>
      <span
        v-else-if="first.reward_copper != null"
        class="pr pr--reward"
        :data-testid="`objective-tracker__reward--${first.quest_id}`"
      >+{{ first.reward_copper }}</span>
      <span
        v-if="rest > 0"
        class="n"
        data-testid="objective-tracker__more"
        role="img"
        :aria-label="`另有 ${rest} 項追蹤目標`"
        :title="`另有 ${rest} 項追蹤目標`"
      ><svg viewBox="0 0 12 12" aria-hidden="true"><path d="M1.5 3h9M1.5 6h9M1.5 9h9" /></svg>{{ rest }}</span>
    </div>
    <div v-if="ticked" class="obj__ticks" data-testid="objective-tracker__ticks" aria-hidden="true">
      <span
        v-for="n in quantity"
        :key="n"
        class="obj__tick"
        :class="{ 'obj__tick--on': n <= progress }"
        data-testid="objective-tracker__tick"
      ></span>
    </div>
    <div v-else-if="counted" class="obj__stroke" data-testid="objective-tracker__stroke" aria-hidden="true">
      <span
        class="obj__fill"
        data-testid="objective-tracker__stroke-fill"
        :style="{ width: `${ratio * 100}%` }"
      ></span>
    </div>
  </div>
</template>
```

The readout renders the payload values verbatim (no clamping in text); only the tick and stroke drawing use the clamped `progress`. Alternative considered for the further-rows count: keeping `+N` and adding a label. Rejected (approved decision 5): beside a `+reward` a second `+N` reads as more copper.

### D3. Scoped styles

Replace the whole `<style scoped>` block with (class names from D2; values from the prototype):

```css
/* The objective line as an instrument panel: the shared chrome
   (instrument-panel.css) carries the ground, the fitting and the padding;
   this block only lays out the content. */
.obj {
  box-sizing: border-box;
  flex: none;
  align-self: stretch;
  width: 100%;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: calc(5px * var(--ui-scale));
  font-family: var(--f-serif);
  color: var(--paper-100);
}
/* One phrase set from the spine: it ends at the right edge and grows to the
   left, never stretched across the column. */
.obj__line {
  max-width: 100%;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: calc(8px * var(--ui-scale));
  white-space: nowrap;
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.8), 0 0 calc(8px * var(--ui-scale)) rgba(11, 13, 16, 0.7);
}
.bx {
  flex: none;
  display: grid;
  place-items: center;
  width: calc(12px * var(--ui-scale));
  height: calc(12px * var(--ui-scale));
}
.bx svg {
  width: 100%;
  height: 100%;
  overflow: visible;
  filter: drop-shadow(0 1px 1px rgba(0, 0, 0, 0.8));
}
.bx__lozenge {
  fill: none;
  stroke: var(--gold-400);
  stroke-width: 1.2;
}
.bx__check {
  fill: none;
  stroke: var(--ink-950);
  stroke-width: 1.6;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.bx.done .bx__lozenge {
  fill: var(--buff);
  stroke: var(--buff);
}
.txt {
  flex: 0 1 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: var(--text-sm);
  line-height: 1.3;
  letter-spacing: 0.04em;
}
.pr,
.n {
  flex: none;
  font-family: var(--f-mono);
  font-variant-numeric: tabular-nums lining-nums;
  line-height: 1.2;
}
.pr--count b {
  font-weight: 600;
  font-size: var(--text-sm);
  color: var(--paper-50);
}
.pr--count i {
  margin-left: calc(4px * var(--ui-scale));
  font-style: normal;
  font-size: var(--text-xs);
  color: var(--paper-500);
}
.pr--reward {
  font-size: var(--text-xs);
  color: var(--gold-400);
}
/* The further-rows count: a stacked-lines glyph, so it never reads as a
   second `+N` beside a reward. */
.n {
  display: inline-flex;
  align-items: center;
  gap: calc(3px * var(--ui-scale));
  font-size: var(--text-xs);
  color: var(--paper-300);
}
.n svg {
  width: calc(11px * var(--ui-scale));
  height: calc(11px * var(--ui-scale));
  fill: none;
  stroke: currentColor;
  stroke-width: 1.2;
  stroke-linecap: round;
}
/* Quantity as strokes: one 3px tick per unit, a 2px seam, slanted ends. The
   empty tick is a faint paper wash, the reached one the gauge gold. */
.obj__ticks {
  display: flex;
  gap: calc(2px * var(--ui-scale));
  filter: drop-shadow(0 1px 1px rgba(0, 0, 0, 0.7));
}
.obj__tick {
  width: calc(13px * var(--ui-scale));
  height: calc(3px * var(--ui-scale));
  background: rgba(231, 224, 209, 0.18);
  clip-path: polygon(calc(2px * var(--ui-scale)) 0, 100% 0, calc(100% - 2px * var(--ui-scale)) 100%, 0 100%);
}
.obj__tick--on {
  background: var(--gold-400);
}
.obj--done .obj__tick--on {
  background: var(--buff);
}
/* Above the tick limit: one continuous stroke, its far (left) end tapering
   to a point. */
.obj__stroke {
  width: calc(180px * var(--ui-scale));
  max-width: 100%;
  height: calc(3px * var(--ui-scale));
  background: linear-gradient(270deg, rgba(231, 224, 209, 0.16), rgba(231, 224, 209, 0.07));
  clip-path: polygon(calc(10px * var(--ui-scale)) 0, 100% 0, 100% 100%, calc(10px * var(--ui-scale)) 100%, 0 50%);
  filter: drop-shadow(0 1px 1px rgba(0, 0, 0, 0.7));
}
.obj__fill {
  display: block;
  height: 100%;
  background: var(--gold-400);
}
.obj--done .obj__fill {
  background: var(--buff);
}
```

Note: the stroke fills from its left (tapered) end, as the prototype does. The `.obj` rule declares no padding, background, border, radius, shadow or `position`, so the shared `.instrument-panel` rule (lower specificity than the scoped `.obj[data-v-…]`) is never overridden.

### D4. Unit tests

- `web/webclient-app/tests/overlays/objective_tracker.test.js`:
  - Replace "renders the 目標 label and a +N count for further rows" with: no `.obj__label` and the root's visible text does not contain `目標`; root `aria-label` is `目標` and `role` is `region`; root classes include `obj` and `instrument-panel`; `objective-tracker__more` text is `2`, its `aria-label` and `title` are `另有 2 項追蹤目標`, it contains an `svg` and no `+`; a single row renders no `objective-tracker__more`.
  - Done/not-done test (lines ~80-95): the done box has class `done`, `aria-label` `已達成` and a `.bx__check`; the not-done box lacks `done`, has `aria-label` `進行中`, has the lozenge `svg` and no `.bx__check`.
  - Progress/reward test (lines ~130-150): the progress element's `b` text is `2` and `i` text is `/ 5`; reward text stays `+80`.
  - New `it("draws one tick per unit up to twelve, reached ticks first")`: quantity 5 / progress 2 → 5 `objective-tracker__tick`, the first 2 with class `obj__tick--on`, `objective-tracker__ticks` has `aria-hidden="true"`, no stroke; quantity 12 / progress 15 → 12 ticks all on (clamped); quantity 5 / progress 5 → root has `obj--done`.
  - New `it("draws one stroke above twelve units, filled to the ratio")`: quantity 30 / progress 12 → no ticks, `objective-tracker__stroke` with `aria-hidden="true"`, fill `style` width `40%`; progress -3 → `0%`.
  - New `it("draws no quantity marks for a single-count objective")`: quantity 1, and quantity missing → neither ticks nor stroke.
  - New source test: `ObjectiveTracker.vue` contains `import "./instrument-panel.css";` and its `.obj {` rule contains none of `height:`, `padding`, `background`, `border`, `border-radius`, `box-shadow`, `backdrop-filter`.
- `web/webclient-app/tests/overlays/objective_tracker_integration.test.js`: re-run; update any `+N` or `n/m` text expectations to the D2 markup (the child-order expectation was already updated by `local-map-instrument-panel`).

### D5. Browser tests

- `web/tests/browser/test_browser_contextual_hud_stage.py`, `test_objective_line_shows_only_in_exploration` (lines ~1365-1395): `belowMinimap` measures against `[data-testid="local-map-panel"]` instead of `local-map`; drop `assertLessEqual(state["height"], 34, …)` and instead assert that `[data-testid="objective-tracker__text--q_1042"]`'s rect height is at most `1.3 * 17 * S + 2` (one text row of `--text-sm` at line-height 1.3; S = 1 at 1451x790); `more` becomes `(state["more"] or "").strip() == "1"` and add an `aria-label` read asserting `另有 1 項追蹤目標`; replace `assertIn("1/3", …)` with a read of the progress element's `b` and `i` texts (`1`, `/ 3`); keep the later-rows, deadline and mode assertions.
- `web/tests/browser/test_browser_map_column_instruments.py`, new method `test_objective_line_is_an_instrument_panel_with_quantity_strokes`, decorated `@covers_requirement("webclient-contextual-hud::the-objective-tracker-island-presents-the-committed-objectives-only", "webclient-contextual-hud::an-instrument-panel-wears-a-feathered-ground-and-one-brass-fitting-instead-of-a-box")`. Live client at `(1280, 720)`, `(1451, 790)`, `(2560, 1440)` with `status`, `local_map`, `art` and an `objectives` panel whose first row has quantity 5 and progress 2 and a second row with `reward_copper` 80:
  - `[data-testid="objective-tracker"]`: border widths `0px`, radius `0px`, `box-shadow` `none`, `background-color` `rgba(0, 0, 0, 0)`, `::before` mask not `none`; left/right equal the place card's (delta 1.0); every descendant element's right edge `<= tracker.right - 14 * S + 0.5`.
  - No visible text `目標` inside the tracker (`innerText` excludes it) while `aria-label` is `目標`; the box `aria-label` is `進行中`.
  - Exactly 5 `objective-tracker__tick`, the first 2 with class `obj__tick--on`, each with a rect width of `13 * S` (delta 1.0).
  - Inject a replacement objectives panel with quantity 30 / progress 12: no ticks; `objective-tracker__stroke-fill` rect width divided by `objective-tracker__stroke` rect width is `0.4` (delta `1 / stroke width + 0.01`).
  - Inject quantity 5 / progress 5: box `aria-label` `已達成`, a `.bx__check` exists.
  - Register it with `uv run --locked python -m tools.shard_register fix`.

### D6. Stories

`web/webclient-app/stories/Overlays/ObjectiveTracker.stories.js`: the dashed placeholder above the tracker becomes the minimap canvas's footprint (`align-self: flex-end; width: 240px; height: 120px; margin-right: 22px;` keeping its dashed border) and the column gap becomes `10px`; rewrite the header comment (instrument panel; no visible 目標; ticks and stroke; the glyph count). Add two stories with the same frame: `CountReached` (one row, `objective_quantity: 5`, `stage_progress: 5`, `reward_copper: null`) and `LongCount` (one row, `objective_quantity: 30`, `stage_progress: 12`, `reward_copper: null`), each with a distinct invented `quest_id`, `display_name` and `objective_line`. Keep every existing export.

### D7. Visual review (human-reviewed)

Review document: the approved prototype `docs/design/map-column-instrument-panels/ObjectiveLineInstrument.vue` (Storybook `Design/MapColumnInstrument`) against live-client screenshots and the updated stories. The human checks: the line set from the spine, the lozenge's open and filled states, tick rhythm and slant, the tapered stroke above 12, the readout's two weights, and that the glyph count never reads as `+N` beside a reward. The implementer captures live screenshots at 1280x720, 1451x790 and 2560x1440 (counted, reached and above-12 forms) with `agent-browser` into the session scratchpad and lists their paths in the apply report; no test asserts the look.

## Risks / Trade-offs

- [A counted objective is taller than the old 32px line] → the populated column still fits at 1451x790 and 2560x1440 (`test_populated_island_stack_fits_its_anchor_at_both_viewports`, re-run in the tasks); at 1280x720 the geometry change's edge fade covers an overflow.
- [The stroke's width is fixed at 180px × S] → `max-width: 100%` keeps it inside the panel on a narrower column.
- [Text of the readout changes from `2/5` to `2/ 5`] → only the two tests that read it are updated; the accessible text of the region is unchanged otherwise.

## Migration Plan

None (pre-release, client-only presentation).
