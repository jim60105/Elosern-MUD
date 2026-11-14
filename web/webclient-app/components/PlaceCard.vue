<script setup>
// PlaceCard (webclient-avg-place-card-top-bar design D3;
// place-card-relocation design D2): the place card in the `map` anchor at
// the top of the right-hand island column. It states
// the current location as the stage's one top-level heading and the world
// date/time beneath it — the only surface that states either value. The
// location is resolved by the store (`statusSlice.locationLabel`: the
// committed `local_map` current-node label, else the status panel's actor
// location); the card only renders it, with the `位置：--` / `時間：--`
// placeholders when nothing is committed.
//
// Display-first (exploration-room-actions design D3): the card states the
// place and the time, and only while `actionsEnabled` (exploration mode with
// the exploration panel available) it carries two room actions — a 查看房間
// magnifier button beside the heading and a 休息 hourglass button beside the
// time (redesign-rest-entry; it opens the two-layer rest entry). They emit `look-room` and `wait`; the card dispatches nothing itself.
// Each reports its readout content through `hover` (null when the pointer or
// focus leaves) and Tab / Shift+Tab through `tab`, so the exploration screen
// can chain its zones. In every other state the card has no control and no
// tab stop. The card sizes to its content (heading, rule, time) at the
// column's width; an overlong label is truncated with an ellipsis while the
// heading keeps the full text for assistive technology (and as its
// `title`); the buttons never squeeze the heading's accessible name.
//
// A new location (webclient-scene-transitions, design D3;
// place-card-instrument-panel) slides the new heading in from the right, the
// column's anchored edge, while the previous one fades out in the same grid
// cell, inert from the commit on. The heading is keyed by its label, so a
// change of the world time alone never animates.
//
// The card is an instrument panel (place-card-instrument-panel design D2):
// it wears the shared `instrument-panel` chrome (a feathered ink ground and
// one brass fitting, no box) and right-aligns its two lines against the
// fitting's spine.
import { computed } from "vue";
import { inertWhileLeaving } from "../lib/transition_hooks.js";
import { PLACE_LOOK_READOUT, PLACE_WAIT_READOUT } from "./exploration-readout.js";
import "./instrument-panel.css";

const props = defineProps({
  locationLabel: { type: String, default: null },
  timeLabel: { type: String, default: null },
  // The EFFECTIVE motion level (`store.view.motionLevel`,
  // webclient-scene-transitions D1): at `off` the transition has no CSS
  // phase, so the final state is on screen in the commit's frame (a CSS
  // phase would outlive the commit by a double frame even at 0s).
  motionLevel: { type: String, default: "full" },
  // The room actions render only while true (exploration-room-actions).
  actionsEnabled: { type: Boolean, default: false },
});

const emit = defineEmits(["look-room", "wait", "hover", "tab"]);

function onTab(event, which) {
  if (event.key !== "Tab" || event.ctrlKey || event.altKey || event.metaKey) {
    return;
  }
  emit("tab", { event, which, backward: event.shiftKey });
}

const location = computed(() => props.locationLabel || "位置：--");
const time = computed(() => props.timeLabel || "時間：--");

const transitionCss = computed(() => props.motionLevel !== "off");
</script>

<template>
  <section
    class="place-card instrument-panel"
    :class="{ 'place-card--actions': actionsEnabled }"
    data-testid="place-card"
    aria-label="目前位置"
  >
    <Transition name="place-card" :css="transitionCss" v-bind="inertWhileLeaving">
      <h1
        :key="location"
        class="place-card__location"
        data-testid="place-card__location"
        :title="location"
      >{{ location }}</h1>
    </Transition>
    <button
      v-if="actionsEnabled"
      type="button"
      class="place-card__action place-card__action--look"
      data-testid="place-card-look"
      aria-label="查看房間"
      title="查看房間"
      @click="emit('look-room')"
      @keydown.enter.stop
      @keydown.space.stop
      @keydown="onTab($event, 'look')"
      @mouseenter="emit('hover', PLACE_LOOK_READOUT)"
      @mouseleave="emit('hover', null)"
      @focus="emit('hover', PLACE_LOOK_READOUT)"
      @blur="emit('hover', null)"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-hidden="true">
        <circle cx="10.5" cy="10.5" r="6" />
        <path d="M15 15l5.5 5.5" />
      </svg>
    </button>
    <span class="place-card__rule" data-testid="place-card__rule" aria-hidden="true"></span>
    <p class="place-card__time" data-testid="place-card__time">{{ time }}</p>
    <button
      v-if="actionsEnabled"
      type="button"
      class="place-card__action place-card__action--wait"
      data-testid="place-card-wait"
      @click="emit('wait', $event.currentTarget)"
      @keydown.enter.stop
      @keydown.space.stop
      @keydown="onTab($event, 'wait')"
      @mouseenter="emit('hover', PLACE_WAIT_READOUT)"
      @mouseleave="emit('hover', null)"
      @focus="emit('hover', PLACE_WAIT_READOUT)"
      @blur="emit('hover', null)"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M7 3h10M7 21h10M8 3c0 5 8 5 8 9s-8 4-8 9M16 3c0 5-8 5-8 9s8 4 8 9" />
      </svg>
      <span class="place-card__action-label">休息</span>
    </button>
  </section>
</template>

<style>
/* The place card as an instrument panel (place-card-instrument-panel
   design D3): the `.instrument-panel` class (instrument-panel.css) paints
   the feathered ink ground and the brass fitting, so these rules declare no
   padding, fill, blur, border, radius or shadow of their own and never
   override it. The heading and the time line align right, toward the
   spine, with a quiet gold rule between them that fades toward the left;
   the room actions are chromeless glyphs with a brass tick under the
   active one. */
.place-card {
  width: 100%;
  /* An island in the `map` column's flex stack: never squeezed below its
     content when the column is short (the column scrolls instead). */
  flex: none;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: auto auto auto;
  align-content: start;
  row-gap: calc(5px * var(--ui-scale));
  /* The heading's slide stays inside the panel. */
  overflow: hidden;
}
.place-card__location,
.place-card__time {
  margin: 0;
  min-width: 0;
  text-align: right;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  /* Crisp edges on any art, where the ground has thinned out. */
  text-shadow: 0 1px 1px rgba(0, 0, 0, 0.8), 0 0 calc(8px * var(--ui-scale)) rgba(11, 13, 16, 0.7);
}
.place-card__location {
  grid-area: 1 / 1;
  align-self: center;
  font: 400 var(--text-lg)/1.25 var(--f-serif);
  letter-spacing: 0.12em;
  /* The tracking adds air after the last glyph; pull it back so the glyph
     edge, not the tracking, meets the right-aligned edge. */
  margin-right: -0.12em;
  color: var(--paper-50);
}
.place-card__rule {
  grid-area: 2 / 1 / 3 / -1;
  justify-self: end;
  display: block;
  width: calc(56px * var(--ui-scale));
  height: 1px;
  background: linear-gradient(270deg, var(--gold-400), rgba(228, 200, 142, 0));
  opacity: 0.75;
}
.place-card__time {
  grid-area: 3 / 1;
  align-self: center;
  font: var(--text-sm)/1.35 var(--f-num);
  font-variant-numeric: tabular-nums lining-nums;
  letter-spacing: 0.04em;
  color: var(--paper-500);
}
.place-card--actions {
  grid-template-columns: minmax(0, 1fr) auto;
  column-gap: calc(6px * var(--ui-scale));
}
/* Chromeless actions: no pill, no fill, no border. The 30px hit box, the
   glyph at rest opacity .86, and a brass tick under the active one. */
.place-card__action {
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
.place-card__action--look { grid-area: 1 / 2; align-self: center; }
.place-card__action--wait { grid-area: 3 / 2; align-self: center; }
.place-card__action svg {
  flex: none;
  width: calc(18px * var(--ui-scale));
  height: calc(18px * var(--ui-scale));
  filter: drop-shadow(0 1px 1px rgba(0, 0, 0, 0.8));
}
.place-card__action::after {
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
.place-card__action:hover,
.place-card__action:focus-visible {
  opacity: 1;
  color: var(--paper-50);
}
.place-card__action:hover::after,
.place-card__action:focus-visible::after {
  opacity: 1;
}
.place-card__action:focus-visible {
  outline: none;
  box-shadow: var(--focus);
  border-radius: var(--radius-sm);
}
/* The location change: a new place slides in from the anchored (right)
   edge while the old name fades where it stands. Without travel (reduced)
   both are plain fades; at `off` the transition has no CSS phase. */
.place-card-enter-active {
  transition:
    opacity calc(var(--motion-reveal) * 0.7) var(--ease-standard) calc(var(--motion-reveal) * 0.3),
    transform var(--motion-reveal) var(--ease-enter);
}
.place-card-leave-active {
  transition: opacity calc(var(--motion-reveal) * 0.5) var(--ease-standard);
}
.place-card-enter-from {
  opacity: 0;
  transform: translateX(calc(var(--motion-shift-lg) * var(--motion-travel)));
}
.place-card-leave-to {
  opacity: 0;
}
</style>
