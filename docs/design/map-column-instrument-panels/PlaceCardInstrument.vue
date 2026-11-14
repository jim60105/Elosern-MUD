<script setup>
// PlaceCardInstrument (design prototype, reference only): PlaceCard as its
// own instrument panel (instrument-panel.css): no box, a feathered ink
// ground and one brass fitting at its top-right corner. The place and the time read as two right-aligned lines standing
// against the column's spine; the two room actions lose their outlined pills
// and gain a brass tick under the hovered or focused one. 休息 keeps its
// visible word: it is an action the player must discover, and an hourglass
// alone reads as "time", not as "rest". Same props and the `look-room` / `wait` / `hover`
// events as the live card; nothing is dispatched.
import { computed } from "vue";
import "./instrument-panel.css";

const props = defineProps({
  locationLabel: { type: String, default: null },
  timeLabel: { type: String, default: null },
  motionLevel: { type: String, default: "full" },
  actionsEnabled: { type: Boolean, default: false },
});

const emit = defineEmits(["look-room", "wait", "hover"]);

const location = computed(() => props.locationLabel || "位置：--");
const time = computed(() => props.timeLabel || "時間：--");
</script>

<template>
  <section
    class="icp-panel icp-place"
    :class="{ 'icp-place--actions': actionsEnabled }"
    data-testid="place-card"
    aria-label="目前位置"
  >
    <Transition name="icp-place" :css="motionLevel !== 'off'">
      <h1 :key="location" class="icp-place__location" :title="location">{{ location }}</h1>
    </Transition>
    <button
      v-if="actionsEnabled"
      type="button"
      class="icp-place__action icp-place__action--look"
      aria-label="查看房間"
      title="查看房間"
      @click="emit('look-room')"
      @mouseenter="emit('hover', 'look')"
      @mouseleave="emit('hover', null)"
      @focus="emit('hover', 'look')"
      @blur="emit('hover', null)"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" aria-hidden="true">
        <circle cx="10.5" cy="10.5" r="6" />
        <path d="M15 15l5.5 5.5" />
      </svg>
    </button>
    <span class="icp-place__rule" aria-hidden="true"></span>
    <p class="icp-place__time">{{ time }}</p>
    <button
      v-if="actionsEnabled"
      type="button"
      class="icp-place__action icp-place__action--wait"
      @click="emit('wait', $event.currentTarget)"
      @mouseenter="emit('hover', 'wait')"
      @mouseleave="emit('hover', null)"
      @focus="emit('hover', 'wait')"
      @blur="emit('hover', null)"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M7 3h10M7 21h10M8 3c0 5 8 5 8 9s-8 4-8 9M16 3c0 5-8 5-8 9s8 4 8 9" />
      </svg>
      <span class="icp-place__action-label">休息</span>
    </button>
  </section>
</template>

<style scoped>
.icp-place {
  box-sizing: border-box;
  flex: none;
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: auto auto auto;
  row-gap: calc(5px * var(--ui-scale));
  /* The heading's slide stays inside the island. */
  overflow: hidden;
}
.icp-place--actions {
  grid-template-columns: minmax(0, 1fr) auto;
  column-gap: calc(6px * var(--ui-scale));
}
.icp-place__location,
.icp-place__time {
  margin: 0;
  min-width: 0;
  text-align: right;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  /* Crisp edges on any art, where the ground has thinned out. */
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.8), 0 0 calc(8px * var(--ui-scale)) rgba(11, 13, 16, 0.7);
}
.icp-place__location {
  grid-area: 1 / 1;
  align-self: center;
  font: 400 var(--text-lg)/1.25 var(--f-serif);
  letter-spacing: 0.12em;
  /* The tracking adds air after the last glyph; pull it back so the glyph
     edge, not the tracking, meets the right-aligned edge. */
  margin-right: -0.12em;
  color: var(--paper-50);
}
.icp-place__rule {
  grid-area: 2 / 1 / 3 / -1;
  justify-self: end;
  display: block;
  width: calc(56px * var(--ui-scale));
  height: 1px;
  background: linear-gradient(270deg, var(--gold-400), rgba(228, 200, 142, 0));
  opacity: 0.75;
}
.icp-place__time {
  grid-area: 3 / 1;
  align-self: center;
  font: var(--text-sm)/1.35 var(--f-num);
  font-variant-numeric: tabular-nums lining-nums;
  letter-spacing: 0.04em;
  color: var(--paper-500);
}

/* Chromeless actions: no pill, no fill, no border. The live card's 30px hit
   box, the glyph at rest opacity .86, and a brass tick under the active one. */
.icp-place__action {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: calc(3px * var(--ui-scale));
  box-sizing: border-box;
  min-width: calc(30px * var(--ui-scale));
  height: calc(30px * var(--ui-scale));
  font: var(--text-xs)/1 var(--f-serif);
  letter-spacing: 0.06em;
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.8);
  /* Optical alignment: the hit box has 4px of air around the glyph, so pull
     it towards the spine to line the glyph's edge up with the text edge. */
  margin-right: calc(-4px * var(--ui-scale));
  padding: 0 calc(4px * var(--ui-scale));
  border: 0;
  background: none;
  color: var(--gold-400);
  opacity: 0.86;
  cursor: pointer;
  transition:
    opacity var(--motion-fast) var(--ease-standard),
    color var(--motion-fast) var(--ease-standard);
}
.icp-place__action--look { grid-area: 1 / 2; align-self: center; }
.icp-place__action--wait { grid-area: 3 / 2; align-self: center; }
.icp-place__action svg {
  width: calc(18px * var(--ui-scale));
  height: calc(18px * var(--ui-scale));
  filter: drop-shadow(0 1px 1px rgba(0, 0, 0, 0.8));
}
.icp-place__action::after {
  content: "";
  position: absolute;
  left: 50%;
  bottom: calc(2px * var(--ui-scale));
  width: calc(10px * var(--ui-scale));
  height: 1px;
  margin-left: calc(-5px * var(--ui-scale));
  background: var(--gold-500);
  opacity: 0;
  transition: opacity var(--motion-fast) var(--ease-standard);
}
.icp-place__action:hover,
.icp-place__action:focus-visible {
  opacity: 1;
  color: var(--paper-50);
}
.icp-place__action:hover::after,
.icp-place__action:focus-visible::after {
  opacity: 1;
}
.icp-place__action:focus-visible {
  outline: none;
  box-shadow: var(--focus);
  border-radius: var(--radius-sm);
}

/* A new place slides in from the anchored (right) edge while the old name
   fades where it stands. */
.icp-place-enter-active {
  transition:
    opacity calc(var(--motion-reveal) * 0.7) var(--ease-standard) calc(var(--motion-reveal) * 0.3),
    transform var(--motion-reveal) var(--ease-enter);
}
.icp-place-leave-active {
  transition: opacity calc(var(--motion-reveal) * 0.5) var(--ease-standard);
}
.icp-place-enter-from {
  opacity: 0;
  transform: translateX(calc(var(--motion-shift-lg) * var(--motion-travel)));
}
.icp-place-leave-to {
  opacity: 0;
}
</style>
