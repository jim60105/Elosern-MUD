<script setup>
// ObjectiveTracker (webclient-align-09-objective-tracker-ui, design D1/D2;
// webclient-avg-stage-hud-anchors design D2): the one-line objective under
// the minimap in the stage's `map` anchor. It renders the `目標` label, then
// for the FIRST committed `objectives.rows` entry (the presenter's tracked
// order): the stage completion box `.bx` (SVG checkmark when
// `stage_progress >= objective_quantity`), the objective line (truncated with
// an ellipsis, the full text kept as its text and tooltip), and the mono-gold
// slot `.pr` (`n/m` when `objective_quantity > 1`, else `+reward_copper` when
// non-null, else empty); then a `+N` count of the further rows. Further rows
// and every deadline live in the quest drawer. One fixed row height; the
// stage hides the line outside exploration (HudFrame.vue).
// Display-only: dispatches no actions and renders no mutation controls.
import { computed } from "vue";

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
</script>

<template>
  <div
    v-if="first"
    class="obj"
    data-testid="objective-tracker"
    role="region"
    aria-label="目標"
  >
    <span class="obj__label">目標</span>
    <span
      class="bx"
      :class="{ done: isDone(first) }"
      :data-testid="`objective-tracker__box--${first.quest_id}`"
    >
      <svg
        v-if="isDone(first)"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="3"
        aria-hidden="true"
      >
        <path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </span>
    <span
      class="txt"
      :data-testid="`objective-tracker__text--${first.quest_id}`"
      :title="first.objective_line"
    >{{ first.objective_line }}</span>
    <span
      v-if="first.objective_quantity > 1"
      class="pr"
      :data-testid="`objective-tracker__progress--${first.quest_id}`"
    >{{ first.stage_progress }}/{{ first.objective_quantity }}</span>
    <span
      v-else-if="first.reward_copper != null"
      class="pr"
      :data-testid="`objective-tracker__reward--${first.quest_id}`"
    >+{{ first.reward_copper }}</span>
    <span
      v-if="rest > 0"
      class="n"
      data-testid="objective-tracker__more"
      :title="`另有 ${rest} 項追蹤目標`"
    >+{{ rest }}</span>
  </div>
</template>

<style scoped>
/* One fixed-height line, right-aligned under the minimap card and sized to
   its content up to the anchor's width (design D2). `align-self` is needed:
   the anchor's `.elosern-root` override stretches its children. The chrome
   is the island vocabulary, with the place card's gold wash mirrored so it
   warms the edge the line hangs from. */
.obj {
  box-sizing: border-box;
  height: calc(32px * var(--ui-scale));
  align-self: flex-end;
  max-width: 100%;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: calc(8px * var(--ui-scale));
  padding: 0 calc(11px * var(--ui-scale)) 0 calc(12px * var(--ui-scale));
  white-space: nowrap;
  overflow: hidden;
  background: linear-gradient(270deg, #bda47714, transparent 60%), var(--panel);
  backdrop-filter: blur(calc(8px * var(--ui-scale)));
  -webkit-backdrop-filter: blur(calc(8px * var(--ui-scale)));
  border: var(--line);
  border-radius: var(--radius);
  box-shadow: inset 0 1px 0 #ffffff06, var(--shadow);
  font-family: var(--f-serif);
  color: var(--paper-100);
}

.obj__label {
  flex: none;
  padding-right: calc(9px * var(--ui-scale));
  border-right: 1px solid #bda47740;
  font-size: var(--text-xs);
  line-height: 1.2;
  letter-spacing: 0.18em;
  color: var(--gold-400);
}

.bx {
  flex: none;
  width: calc(13px * var(--ui-scale));
  height: calc(13px * var(--ui-scale));
  box-sizing: border-box;
  border-radius: var(--radius-sm);
  border: 1px solid var(--ink-600);
  display: grid;
  place-items: center;
  background: var(--ink-780);
}

.bx.done {
  background: rgba(127, 191, 127, 0.2);
  border-color: rgba(127, 191, 127, 0.5);
}

.bx svg {
  width: calc(9px * var(--ui-scale));
  height: calc(9px * var(--ui-scale));
  color: var(--buff);
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

.pr {
  flex: none;
  font-family: var(--f-num);
  font-size: var(--text-xs);
  font-variant-numeric: tabular-nums lining-nums;
  color: var(--gold-400);
}

.n {
  flex: none;
  padding: 2px calc(6px * var(--ui-scale));
  border: 1px solid #bda47738;
  border-radius: var(--radius-pill);
  font-family: var(--f-num);
  font-size: var(--text-xs);
  line-height: 1.2;
  color: var(--paper-300);
  font-variant-numeric: tabular-nums lining-nums;
}
</style>
