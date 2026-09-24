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
import { computed } from "vue";

const props = defineProps({
  locationLabel: { type: String, default: null },
  timeLabel: { type: String, default: null },
});

const location = computed(() => props.locationLabel || "位置：--");
const time = computed(() => props.timeLabel || "時間：--");
</script>

<template>
  <section class="place-card" data-testid="place-card" aria-label="目前位置">
    <h1
      class="place-card__location"
      data-testid="place-card__location"
      :title="location"
    >{{ location }}</h1>
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
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
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
  font: 400 20px/1.25 var(--f-serif);
  letter-spacing: 0.12em;
  color: #ead8b9;
  text-shadow: 0 1px 6px #000c;
}
.place-card__time {
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
</style>
