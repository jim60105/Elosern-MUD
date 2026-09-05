<script setup>
// ObjectiveTracker (webclient-align-09-objective-tracker-ui, design D1/D2):
// the bottom-right `.obj` objective tracker island on the cinematic stage.
// Renders the committed `objectives.rows` (up to 3 tracked active quests) with
// header `目標` and mono-gold count `N 追蹤`, stage completion checkbox `.bx`
// (SVG checkmark when `stage_progress >= objective_quantity`), objective line,
// right-aligned mono-gold slot `.pr` (`n/m` when `objective_quantity > 1`, else
// `+reward_copper` when non-null, else empty), and muted deadline line when present.
// Display-only: dispatches no actions and renders no mutation controls.
import { computed } from "vue";

const props = defineProps({
  // The committed `objectives.rows` array from the `objectives` panel.
  rows: { type: Array, default: () => [] },
});

const safeRows = computed(() => (Array.isArray(props.rows) ? props.rows : []));

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
    v-if="safeRows.length > 0"
    class="obj"
    data-testid="objective-tracker"
    role="region"
    aria-label="目標"
  >
    <div class="oh" data-testid="objective-tracker__header">
      <span>目標</span>
      <span class="n tracked" data-testid="objective-tracker__count" title="追蹤中">
        {{ safeRows.length }} 追蹤
      </span>
    </div>
    <div
      v-for="row in safeRows"
      :key="row.quest_id"
      class="row"
      :data-testid="`objective-tracker__row--${row.quest_id}`"
    >
      <span
        class="bx"
        :class="{ done: isDone(row) }"
        :data-testid="`objective-tracker__box--${row.quest_id}`"
      >
        <svg
          v-if="isDone(row)"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="3"
        >
          <path d="M5 13l4 4L19 7" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
      </span>
      <div class="row-content">
        <div class="row-head">
          <span class="txt" :data-testid="`objective-tracker__text--${row.quest_id}`">
            {{ row.objective_line }}
          </span>
          <span
            v-if="row.objective_quantity > 1"
            class="pr"
            :data-testid="`objective-tracker__progress--${row.quest_id}`"
          >
            {{ row.stage_progress }}/{{ row.objective_quantity }}
          </span>
          <span
            v-else-if="row.reward_copper != null"
            class="pr"
            :data-testid="`objective-tracker__reward--${row.quest_id}`"
          >
            +{{ row.reward_copper }}
          </span>
        </div>
        <div
          v-if="row.deadline_line"
          class="dl"
          :data-testid="`objective-tracker__deadline--${row.quest_id}`"
        >
          {{ row.deadline_line }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.obj {
  position: absolute;
  z-index: 4;
  bottom: calc(var(--dock-h) + 60px);
  right: 16px;
  width: 238px;
  background: var(--panel);
  backdrop-filter: blur(8px);
  border: var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 10px 12px;
  box-sizing: border-box;
}

.obj .oh {
  font-size: 10px;
  letter-spacing: 0.14em;
  color: var(--paper-500);
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 7px;
}

.obj .oh .n {
  margin-left: auto;
  font-family: var(--f-mono);
  color: var(--gold-400);
}

.obj .row {
  display: flex;
  gap: 9px;
  font-size: 12px;
  line-height: 1.35;
  margin-bottom: 7px;
  color: var(--paper-100);
}

.obj .row:last-child {
  margin-bottom: 0;
}

.obj .bx {
  width: 15px;
  height: 15px;
  flex: none;
  margin-top: 1px;
  border-radius: 4px;
  border: 1px solid var(--ink-600);
  display: grid;
  place-items: center;
  background: var(--ink-780);
}

.obj .bx.done {
  background: rgba(127, 191, 127, 0.2);
  border-color: rgba(127, 191, 127, 0.5);
}

.obj .bx svg {
  width: 10px;
  height: 10px;
  color: var(--buff);
}

.obj .row-content {
  flex: 1;
  min-width: 0;
}

.obj .row-head {
  display: flex;
  align-items: baseline;
  gap: 6px;
}

.obj .txt {
  flex: 1;
  min-width: 0;
  word-break: break-word;
}

.obj .pr {
  margin-left: auto;
  font-family: var(--f-mono);
  font-size: 11px;
  color: var(--gold-400);
  flex: none;
}

.obj .dl {
  font-size: 10px;
  color: var(--paper-500);
  margin-top: 2px;
  line-height: 1.3;
}

@media (max-width: 1180px) {
  .obj {
    width: 210px;
  }
}
</style>
