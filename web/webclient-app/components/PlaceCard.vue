<script setup>
// PlaceCard (webclient-avg-place-card-top-bar design D3): the stage's place
// card in the `place` anchor at the stage box's top-left corner. It states
// the current location as the stage's one top-level heading and the world
// date/time beneath it — the only surface that states either value. The
// location is resolved by the store (`statusSlice.locationLabel`: the
// committed `local_map` current-node label, else the status panel's actor
// location); the card only renders it, with the `位置：--` / `時間：--`
// placeholders when nothing is committed.
//
// Display-only: no control, no tab stop, no dispatch. The card fills its
// fixed-height anchor whatever the label lengths; an overlong label is
// truncated with an ellipsis while the heading keeps the full text for
// assistive technology (and as its `title`).
//
// A new location (webclient-scene-transitions, design D3) slides the new
// heading in from the left while the previous one fades out in the same grid
// cell, inert from the commit on. The heading is keyed by its label, so a
// change of the world time alone never animates.
import { computed } from "vue";
import { inertWhileLeaving } from "../lib/transition_hooks.js";

const props = defineProps({
  locationLabel: { type: String, default: null },
  timeLabel: { type: String, default: null },
  // The EFFECTIVE motion level (`store.view.motionLevel`,
  // webclient-scene-transitions D1): at `off` the transition has no CSS
  // phase, so the final state is on screen in the commit's frame (a CSS
  // phase would outlive the commit by a double frame even at 0s).
  motionLevel: { type: String, default: "full" },
});

const location = computed(() => props.locationLabel || "位置：--");
const time = computed(() => props.timeLabel || "時間：--");

const transitionCss = computed(() => props.motionLevel !== "off");
</script>

<template>
  <section class="place-card" data-testid="place-card" aria-label="目前位置">
    <Transition name="place-card" :css="transitionCss" v-bind="inertWhileLeaving">
      <h1
        :key="location"
        class="place-card__location"
        data-testid="place-card__location"
        :title="location"
      >{{ location }}</h1>
    </Transition>
    <p class="place-card__time" data-testid="place-card__time">{{ time }}</p>
  </section>
</template>

<style>
/* The HUD island chrome from the shared tokens (the translucent panel fill,
   the backdrop blur, the hairline border, the shared radius and shadow),
   declared here so the card carries it wherever it is mounted. A faint
   warm wash from the left edge and a short gold rule before the time line
   echo the band's hairline vocabulary. */
.place-card {
  box-sizing: border-box;
  height: 100%;
  width: 100%;
  /* Two rows centred in the fixed anchor: the heading, then the time. The
     heading row is one grid cell that an entering and a leaving heading
     share during a location change, so neither moves the time line. */
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: auto auto;
  align-content: center;
  row-gap: 5px;
  padding: 0 16px;
  overflow: hidden;
  background: linear-gradient(90deg, #bda47714, transparent 55%), var(--panel);
  backdrop-filter: blur(9px);
  -webkit-backdrop-filter: blur(9px);
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
  font: 400 20px/1.25 var(--f-serif);
  letter-spacing: 0.12em;
  color: #ead8b9;
  text-shadow: 0 1px 6px #000c;
}
.place-card__time {
  grid-area: 2 / 1;
  font: 12px/1.4 var(--f-serif);
  letter-spacing: 0.08em;
  color: var(--paper-300);
}
.place-card__time::before {
  content: "";
  display: inline-block;
  vertical-align: middle;
  margin: -2px 8px 0 0;
  width: 14px;
  height: 1px;
  background: var(--gold-400);
  opacity: 0.7;
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
