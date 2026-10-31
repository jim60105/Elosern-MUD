<script setup>
// TravelWalkControls (OpenSpec change wilderness-travel-walking-ui; design
// "Working intermediate surface"): the travel band-command's temporary
// movement controls until LegPanel replaces them. It reads `view.travel`
// only and states the movement intent: the walk in progress, the aimed
// neighbour (or its committed reason), a stop's server message, or the quiet
// idle line. The intent line is the channel for aim and walking; the 停步
// button emits `stop`. It sends nothing and keeps no movement state.
import { computed } from "vue";
import { DIRECTIONS } from "./travel-walk-model.js";

const props = defineProps({
  // The published `view.travel` slice.
  travel: { type: Object, default: null },
  motionLevel: { type: String, default: "full" },
});
const emit = defineEmits(["stop"]);

const walking = computed(() => props.travel?.walking ?? null);
const holding = computed(() => !!props.travel?.holding);
const target = computed(() => props.travel?.aimTarget ?? null);
const notice = computed(() => props.travel?.notice ?? null);
const lit = computed(() => walking.value?.direction ?? target.value?.direction ?? null);
const stoppable = computed(() => !!walking.value || holding.value);

const WAITING = Object.freeze({ commit: "前進中", dwell: "前進中", map: "等待地圖更新", gate: "等待中" });

const intent = computed(() => {
  const walk = walking.value;
  if (walk) {
    return {
      kind: "walking",
      title: `朝${walk.word}連續前進`,
      detail: `${WAITING[walk.waiting] ?? "前進中"}・已走 ${walk.progress} 步`,
    };
  }
  if (notice.value?.message) {
    return { kind: notice.value.kind === "refused" ? "refused" : "blocked", title: "無法前進", detail: notice.value.message };
  }
  const aim = target.value;
  if (aim) {
    if (aim.enabled) return { kind: "aim", title: `瞄準${aim.word}・一步`, detail: "Enter 前進一步" };
    return { kind: "blocked", title: `瞄準${aim.word}`, detail: aim.reason || "無法通行" };
  }
  return { kind: "none", title: "選擇相鄰的一格", detail: "方向鍵瞄準・點選鄰格前進" };
});

// The decorative rose: eight spokes at their bearings, the lit one gold.
const SPOKE = 30;
const spokes = DIRECTIONS.map((d) => {
  const rad = (d.angle * Math.PI) / 180;
  const long = d.angle % 90 === 0;
  const r = long ? SPOKE : SPOKE * 0.72;
  return { key: d.key, x: Math.sin(rad) * r, y: -Math.cos(rad) * r, long };
});

function onStop() {
  if (stoppable.value) emit("stop");
}
</script>

<template>
  <div
    class="travel-walk"
    :class="[`travel-walk--${intent.kind}`, { 'is-walking': !!walking }]"
    data-testid="travel-walk-controls"
    :data-intent="intent.kind"
    :data-motion-level="motionLevel"
  >
    <svg class="travel-walk__rose" viewBox="-40 -40 80 80" aria-hidden="true" focusable="false">
      <circle class="travel-walk__ring" r="34" />
      <line
        v-for="s in spokes"
        :key="s.key"
        class="travel-walk__spoke"
        :class="{ 'is-lit': s.key === lit, 'is-long': s.long }"
        x1="0"
        y1="0"
        :x2="s.x"
        :y2="s.y"
      />
      <path
        v-for="s in spokes"
        v-show="s.key === lit"
        :key="`tip-${s.key}`"
        class="travel-walk__tip"
        :transform="`translate(${s.x} ${s.y})`"
        d="M0 -4.5 L4.5 0 L0 4.5 L-4.5 0 Z"
      />
      <circle class="travel-walk__hub" r="5.5" />
    </svg>
    <div class="travel-walk__intent" role="status" aria-live="polite" data-testid="travel-walk-intent">
      <p class="travel-walk__title" data-testid="travel-walk-title">{{ intent.title }}</p>
      <p class="travel-walk__detail" data-testid="travel-walk-detail">{{ intent.detail }}</p>
    </div>
    <button
      type="button"
      class="travel-walk__stop"
      data-testid="travel-walk-stop"
      :aria-disabled="stoppable ? null : 'true'"
      @click="onStop"
      @keydown.enter.stop
      @keydown.space.stop
    >停步</button>
  </div>
</template>

<style scoped>
/* A quiet ink plate in the band's command column: the rose, the intent
   line and the 停步 control, framed by the shared gold hairline. */
.travel-walk {
  box-sizing: border-box;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr) auto;
  column-gap: calc(10px * var(--ui-scale));
  row-gap: calc(10px * var(--ui-scale));
  align-items: center;
  width: 100%;
  height: 100%;
  min-height: 0;
  padding: calc(10px * var(--ui-scale)) calc(12px * var(--ui-scale));
  border: 1px solid rgba(185, 154, 96, 0.28);
  border-radius: var(--radius);
  background:
    radial-gradient(120% 90% at 0% 0%, rgba(185, 154, 96, 0.08), transparent 60%),
    rgba(11, 13, 16, 0.42);
  font-family: var(--f-sans);
}

.travel-walk__rose {
  grid-row: 1;
  width: calc(58px * var(--ui-scale));
  height: calc(58px * var(--ui-scale));
}
.travel-walk__ring {
  fill: rgba(11, 13, 16, 0.6);
  stroke: rgba(185, 154, 96, 0.45);
  stroke-width: 0.9;
}
.travel-walk__spoke {
  stroke: rgba(186, 181, 174, 0.32);
  stroke-width: 1.2;
  stroke-linecap: round;
}
.travel-walk__spoke.is-long {
  stroke: rgba(186, 181, 174, 0.5);
}
.travel-walk__spoke.is-lit {
  stroke: var(--gold-400);
  stroke-width: 2.2;
}
.travel-walk__tip {
  fill: var(--gold-400);
  stroke: var(--ink-950);
  stroke-width: 0.8;
}
.travel-walk__hub {
  fill: var(--seal-600);
  stroke: var(--gold-500);
  stroke-width: 1;
}
.travel-walk--blocked .travel-walk__spoke.is-lit,
.travel-walk--refused .travel-walk__spoke.is-lit {
  stroke: var(--paper-500);
  stroke-dasharray: 2.5 2.5;
}
.travel-walk--blocked .travel-walk__tip,
.travel-walk--refused .travel-walk__tip {
  fill: none;
  stroke: var(--paper-500);
  stroke-dasharray: 2 1.5;
}
/* Walking: the lit spoke breathes, and stands still at motion off. */
.travel-walk.is-walking .travel-walk__spoke.is-lit,
.travel-walk.is-walking .travel-walk__tip {
  animation: travel-walk-breathe calc(var(--motion-scene) * 2) var(--ease-standard) infinite alternate;
}
.travel-walk[data-motion-level="off"] .travel-walk__spoke.is-lit,
.travel-walk[data-motion-level="off"] .travel-walk__tip {
  animation: none;
}
@keyframes travel-walk-breathe {
  from { opacity: 1; }
  to { opacity: 0.55; }
}

.travel-walk__intent {
  grid-row: 1;
  display: flex;
  flex-direction: column;
  gap: calc(4px * var(--ui-scale));
  min-width: 0;
  padding-left: calc(10px * var(--ui-scale));
  border-left: 2px solid var(--gold-500);
}
.travel-walk__title {
  margin: 0;
  font: var(--text-md)/1.3 var(--f-display);
  letter-spacing: 0.04em;
  color: var(--paper-50);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.travel-walk__detail {
  margin: 0;
  font-size: var(--text-xs);
  line-height: 1.4;
  color: var(--paper-400);
  font-variant-numeric: tabular-nums;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  overflow-wrap: anywhere;
}
.travel-walk--none .travel-walk__intent {
  border-left-color: var(--ink-600);
}
.travel-walk--none .travel-walk__title {
  color: var(--paper-400);
}
.travel-walk--walking .travel-walk__detail {
  color: var(--gold-300);
}
.travel-walk--blocked .travel-walk__intent,
.travel-walk--refused .travel-walk__intent {
  border-left-color: var(--seal-500);
}
.travel-walk--refused .travel-walk__detail,
.travel-walk--blocked .travel-walk__detail {
  color: var(--paper-200);
}

.travel-walk__stop {
  grid-column: 1 / -1;
  grid-row: 2;
  justify-self: stretch;
  min-height: calc(38px * var(--ui-scale));
  padding: 0 calc(16px * var(--ui-scale));
  border: 1px solid var(--gold-600);
  border-radius: var(--radius-sm);
  background: rgba(185, 154, 96, 0.12);
  color: var(--gold-300);
  font: 600 var(--text-sm)/1 var(--f-sans);
  letter-spacing: 0.3em;
  text-indent: 0.3em;
  cursor: pointer;
  transition:
    background var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard),
    color var(--motion-fast) var(--ease-standard);
}
.travel-walk__stop:hover:not([aria-disabled="true"]) {
  background: rgba(185, 154, 96, 0.22);
  border-color: var(--gold-400);
}
.travel-walk__stop[aria-disabled="true"] {
  border-color: var(--ink-600);
  background: transparent;
  color: var(--paper-500);
  cursor: default;
}
.travel-walk__stop:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}
</style>
