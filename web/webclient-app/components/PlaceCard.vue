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
// magnifier button beside the heading and a 等待 hourglass button beside the
// time. They emit `look-room` and `wait`; the card dispatches nothing itself.
// Each reports its readout content through `hover` (null when the pointer or
// focus leaves) and Tab / Shift+Tab through `tab`, so the exploration screen
// can chain its zones. In every other state the card has no control and no
// tab stop. The card sizes to its content (heading, rule, time) at the
// column's width; an overlong label is truncated with an ellipsis while the
// heading keeps the full text for assistive technology (and as its
// `title`); the buttons never squeeze the heading's accessible name.
//
// A new location (webclient-scene-transitions, design D3) slides the new
// heading in from the left while the previous one fades out in the same grid
// cell, inert from the commit on. The heading is keyed by its label, so a
// change of the world time alone never animates.
import { computed } from "vue";
import { inertWhileLeaving } from "../lib/transition_hooks.js";
import { PLACE_LOOK_READOUT, PLACE_WAIT_READOUT } from "./exploration-readout.js";

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
    class="place-card"
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
      <span class="place-card__action-label">等待</span>
    </button>
  </section>
</template>

<style>
/* The HUD island chrome from the shared tokens (the translucent panel fill,
   the backdrop blur, the hairline border, the shared radius and shadow),
   declared here so the card carries it wherever it is mounted. A faint
   warm wash from the left edge and a quiet gold rule between the heading
   and the time line echo the band's hairline vocabulary and set the two
   rows on two levels (webclient-chrome-navigation-polish): the place is the
   title, the time a subordinate line in the numeral face. */
.place-card {
  box-sizing: border-box;
  width: 100%;
  /* An island in the `map` column's flex stack: never squeezed below its
     content when the column is short (the column scrolls instead). */
  flex: none;
  /* Three content-sized rows: the heading, the rule, then the
     time. The heading row is one grid cell that an entering and a leaving
     heading share during a location change, so neither moves the time
     line. */
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: auto auto auto;
  align-content: start;
  row-gap: calc(6px * var(--ui-scale));
  padding: calc(11px * var(--ui-scale)) calc(14px * var(--ui-scale)) calc(10px * var(--ui-scale));
  overflow: hidden;
  background: linear-gradient(90deg, #bda47714, transparent 55%), var(--panel);
  backdrop-filter: blur(calc(9px * var(--ui-scale)));
  -webkit-backdrop-filter: blur(calc(9px * var(--ui-scale)));
  border: var(--line);
  border-radius: var(--radius);
  box-shadow: inset 0 1px 0 #ffffff06, var(--shadow);
}
.place-card__location,
.place-card__time {
  margin: 0;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.place-card__location {
  grid-area: 1 / 1;
  font: 400 var(--text-lg)/1.25 var(--f-serif);
  letter-spacing: 0.12em;
  color: #ead8b9;
  text-shadow: 0 1px calc(6px * var(--ui-scale)) #000c;
}
.place-card__rule {
  grid-area: 2 / 1;
  display: block;
  width: calc(40px * var(--ui-scale));
  height: 1px;
  background: linear-gradient(90deg, var(--gold-400), #d8bb7800);
  opacity: 0.75;
}
/* The time line starts at its first value (no leading glyph or rule) and
   sets its figures in the numeral face as tabular lining numerals, so the
   clock never jitters as the minutes turn. */
.place-card__time {
  grid-area: 3 / 1;
  align-self: center;
  font: var(--text-sm)/1.35 var(--f-num);
  font-variant-numeric: tabular-nums lining-nums;
  letter-spacing: 0.06em;
  color: var(--paper-500);
}

/* The room actions (exploration-room-actions design D3): a second column
   holds the 查看房間 magnifier beside the heading and the 等待 hourglass
   beside the time. The heading and the time keep the first column, so the
   buttons never truncate the heading's accessible name (its ellipsis is the
   visible text only). Quiet outlined controls with the band's 3:1 rule. */
.place-card--actions {
  grid-template-columns: minmax(0, 1fr) auto;
  column-gap: calc(8px * var(--ui-scale));
}
.place-card--actions .place-card__rule {
  grid-column: 1 / -1;
}
.place-card__action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: calc(4px * var(--ui-scale));
  box-sizing: border-box;
  height: calc(30px * var(--ui-scale));
  min-width: calc(30px * var(--ui-scale));
  padding: 0 calc(6px * var(--ui-scale));
  background: transparent;
  border: 1px solid #736b5c;
  border-radius: var(--radius-sm);
  color: var(--paper-200);
  font: var(--text-xs)/1 var(--f-sans);
  letter-spacing: 0.06em;
  cursor: pointer;
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard),
    color var(--motion-fast) var(--ease-standard);
}
.place-card__action--look {
  grid-area: 1 / 2;
  align-self: center;
}
.place-card__action--wait {
  grid-area: 3 / 2;
  align-self: center;
  padding-right: calc(8px * var(--ui-scale));
}
.place-card__action svg {
  flex: none;
  width: calc(18px * var(--ui-scale));
  height: calc(18px * var(--ui-scale));
}
.place-card__action:hover,
.place-card__action:focus-visible {
  border-color: var(--gold-500);
  background: var(--gold-glow);
  color: var(--paper-50);
  outline: none;
}
.place-card__action:focus-visible {
  box-shadow: 0 0 0 1px var(--gold-400);
}

/* The location change (webclient-scene-transitions, design D3). The two
   names hand over rather than overlap: the old name fades out where it
   stands within the first half of the reveal, while the new one slides in
   from the left at once, decelerating into place, and fades in from a third
   of the way through, when the old one is nearly gone. The card's own
   `overflow: hidden` keeps the travel inside the island. Without travel (the
   reduced level) both are plain fades; at `off` there is no phase at all. */
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
  transform: translateX(calc(-1 * var(--motion-shift-lg) * var(--motion-travel)));
}
.place-card-leave-to {
  opacity: 0;
}
</style>
