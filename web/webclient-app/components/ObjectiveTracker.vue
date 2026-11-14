<script setup>
// ObjectiveTracker (webclient-align-09-objective-tracker-ui;
// webclient-avg-stage-hud-anchors design D2; objective-tracker-instrument-panel):
// the objective line under the minimap in the stage's `map` anchor, worn as
// an instrument panel (instrument-panel.css) that spans the column. 目標 is
// the region's accessible name only; no visible label renders. For the FIRST
// committed `objectives.rows` entry (the presenter's tracked order) the line
// carries: the completion lozenge `.bx` (an open gold outline while in
// progress, filled with a check once `stage_progress >= objective_quantity`,
// its accessible name 進行中 / 已達成, so the state is shape and text, never
// colour alone); the objective line (truncated with an ellipsis, the full
// text kept as its text and tooltip); the readout `.pr` (tabular `n / m`
// when `objective_quantity > 1`, else `+reward_copper` in gold mono when
// non-null, else empty); then the further-rows count as a stacked-lines
// glyph plus the number, named 另有 N 項追蹤目標, so it never reads as a
// second `+N`. A counted objective restates its quantity under the line as
// one tick per unit (up to TICK_LIMIT) or, above it, one stroke tapering to
// a point. Further rows and every deadline live in the quest drawer; the
// stage hides the line outside exploration (HudFrame.vue, via `.obj`).
// Display-only: dispatches no actions and renders no mutation controls.
import { computed } from "vue";
import "./instrument-panel.css";

const props = defineProps({
  // The committed `objectives.rows` array from the `objectives` panel.
  rows: { type: Array, default: () => [] },
});

const safeRows = computed(() => (Array.isArray(props.rows) ? props.rows : []));
const first = computed(() => safeRows.value[0] || null);
const rest = computed(() => Math.max(0, safeRows.value.length - 1));

function isDone(row) {
  return (
    typeof row?.stage_progress === "number" &&
    typeof row?.objective_quantity === "number" &&
    row.stage_progress >= row.objective_quantity
  );
}

// One tick per unit reads up to this many; above it the quantity is one
// continuous stroke, so the ticks never shrink below a readable width.
const TICK_LIMIT = 12;

// Same type rule as isDone: only a number counts, so the marks and the
// completion state never disagree about a non-numeric payload field.
const quantity = computed(() => {
  const value = first.value?.objective_quantity;
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
});
const counted = computed(() => quantity.value > 1);
const progress = computed(() => {
  const value = first.value?.stage_progress;
  const reached = typeof value === "number" && Number.isFinite(value) ? value : 0;
  return Math.max(0, Math.min(quantity.value, reached));
});
const done = computed(() => isDone(first.value));
const ticked = computed(() => counted.value && quantity.value <= TICK_LIMIT);
const ratio = computed(() => (quantity.value > 0 ? progress.value / quantity.value : 0));
</script>

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

<style scoped>
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
</style>
