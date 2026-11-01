<script setup>
// LandmarkCard (OpenSpec change wilderness-travel-route-ui; interface design
// §10): the landmark arrival card in the `choices` anchor. It is bound to one
// committed typed `landmark_reached` notice the store publishes as
// `view.travel.arrival` ({id, name, litDistrict, prose, artwork}) and shows
// exactly what the notice supplied: the reached room's scene descriptor in a
// 16:6 frame through ArtworkPreview (no descriptor: a quiet ink frame, never
// substitute art), 抵達地標, the name, `◆ <district>已探明` only when this
// arrival lit it, the prose and 繼續.
//
// Focus starts on 繼續 and Tab stays inside the card (the shared focus-trap
// contract). 繼續, Enter and Escape emit `continue` once; the host closes the
// card through the store and returns focus to the map. Every key the card
// handles is consumed before it can reach the document keyboard bridge.
import { computed, onMounted, ref, useId } from "vue";
import ArtworkPreview from "../ArtworkPreview.vue";
import { createFocusTrap } from "../focus-trap.js";

const props = defineProps({
  arrival: { type: Object, required: true },
  // The committed art panel: the availability the descriptor is judged by.
  artPanel: { type: Object, default: null },
  entrance: { type: Boolean, default: true },
});
const emit = defineEmits(["continue"]);

const root = ref(null);
const go = ref(null);
const titleId = useId();
const proseId = useId();
const still = !props.entrance;
let trap = null;
let closed = false;

const hasArt = computed(() => !!props.arrival.artwork);

function close() {
  if (closed) return;
  closed = true;
  emit("continue");
}

function onKeydown(event) {
  if (event.ctrlKey || event.altKey || event.metaKey || event.isComposing) return;
  if (event.key === "Tab") {
    event.stopPropagation();
    trap?.onKeydown(event);
    return;
  }
  if (event.key === "Enter" || event.key === "Escape") {
    event.preventDefault();
    event.stopPropagation();
    if (!event.repeat) close();
    return;
  }
  // Space reaches the focused 繼續 natively; every other key stays inside.
  if (event.key !== " ") event.stopPropagation();
}

onMounted(() => {
  trap = createFocusTrap(root.value, { initialFocusEl: go.value });
  trap.enter();
});
</script>

<template>
  <section
    ref="root"
    class="choice-card landmark-card"
    :class="{ 'choice-card--still': still }"
    role="dialog"
    aria-modal="true"
    :aria-labelledby="titleId"
    :aria-describedby="proseId"
    tabindex="-1"
    data-testid="landmark-card"
    :data-arrival="arrival.id"
    @keydown="onKeydown"
  >
    <span class="choice-card__corners" aria-hidden="true"></span>
    <div class="landmark-card__art" :class="{ 'is-empty': !hasArt }" data-testid="landmark-card-art">
      <ArtworkPreview
        v-if="hasArt"
        :artwork="arrival.artwork"
        :panel="artPanel"
        :alt="arrival.name"
      />
      <p class="landmark-card__kicker"><span class="landmark-card__gem" aria-hidden="true"></span>抵達地標</p>
    </div>
    <div class="landmark-card__body">
      <h2 :id="titleId" class="landmark-card__title" data-testid="landmark-card-name">{{ arrival.name }}</h2>
      <p v-if="arrival.litDistrict" class="landmark-card__lit" data-testid="landmark-card-lit">
        <span aria-hidden="true">◆</span> {{ arrival.litDistrict }}已探明
      </p>
      <p :id="proseId" class="landmark-card__prose" data-testid="landmark-card-prose">{{ arrival.prose }}</p>
      <button
        ref="go"
        type="button"
        class="landmark-card__go"
        data-testid="landmark-card-continue"
        @click="close"
      >
        <span>繼續</span><kbd aria-hidden="true">Enter</kbd>
      </button>
    </div>
  </section>
</template>

<style>
/* The arrival card: the shared card frame around a 16:6 scene band whose
   foot fades into the ink body, the name in the display face over the
   fade, the gold district line and the serif prose. Every text run keeps
   the 16px x scale floor. */
/* The frame is the card's own (the doubled class wins over the shared
   `choice-card` block whichever stylesheet loads last), so the card reads
   the same wherever it is hosted: an opaque ink panel with a gold hairline
   that lifts it clear of the painted map beneath. */
.landmark-card.choice-card {
  position: relative;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  align-self: center;
  width: min(100%, calc(560px * var(--ui-scale)));
  max-height: 100%;
  padding: 0;
  overflow: hidden auto;
  background:
    radial-gradient(120% 60% at 50% 100%, rgba(185, 154, 96, 0.08), transparent 70%),
    linear-gradient(180deg, rgba(20, 20, 25, 0.98), rgba(11, 12, 16, 0.98));
  border: 1px solid rgba(185, 154, 96, 0.5);
  border-radius: var(--radius);
  box-shadow:
    var(--shadow-lg),
    0 0 0 100vmax rgba(6, 7, 10, 0.34),
    inset 0 0 0 1px rgba(0, 0, 0, 0.55);
  outline: none;
  pointer-events: auto;
}
.landmark-card.choice-card:focus-visible {
  border-color: rgba(228, 200, 142, 0.72);
}
.landmark-card__art {
  position: relative;
  flex: none;
  aspect-ratio: 16 / 6;
  overflow: hidden;
  border-radius: var(--radius) var(--radius) 0 0;
  background:
    radial-gradient(80% 120% at 50% 110%, rgba(185, 154, 96, 0.14), transparent 70%),
    linear-gradient(180deg, #1b1a20, #0e0f13);
}
/* No supplied descriptor: no empty picture frame, only a short engraved
   header band carrying the kicker over a quiet horizon line. */
.landmark-card__art.is-empty {
  aspect-ratio: auto;
  height: calc(64px * var(--ui-scale));
}
.landmark-card__art.is-empty + .landmark-card__body {
  margin-top: calc(4px * var(--ui-scale));
}
.landmark-card__art.is-empty::before {
  content: "";
  position: absolute;
  left: 12%;
  right: 12%;
  top: 58%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(228, 200, 142, 0.35), transparent);
}
.landmark-card__art::after {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: linear-gradient(180deg, rgba(12, 13, 17, 0) 38%, rgba(12, 13, 17, 0.97));
}
.landmark-card__art > .artwork-preview {
  position: absolute;
  inset: 0;
}
.landmark-card__kicker {
  position: absolute;
  left: calc(22px * var(--ui-scale));
  top: calc(16px * var(--ui-scale));
  z-index: 1;
  display: inline-flex;
  align-items: center;
  gap: calc(8px * var(--ui-scale));
  margin: 0;
  padding: calc(4px * var(--ui-scale)) calc(10px * var(--ui-scale));
  border: 1px solid rgba(228, 200, 142, 0.35);
  border-radius: var(--radius-sm);
  background: rgba(12, 13, 17, 0.62);
  font: var(--text-xs)/1 var(--f-sans);
  letter-spacing: 0.3em;
  color: var(--gold-300);
  text-shadow: 0 1px 4px #000;
}
.landmark-card__gem {
  width: calc(7px * var(--ui-scale));
  height: calc(7px * var(--ui-scale));
  background: var(--gold-400);
  transform: rotate(45deg);
  box-shadow: 0 0 calc(6px * var(--ui-scale)) var(--gold-glow);
}
.landmark-card__body {
  position: relative;
  z-index: 1;
  display: grid;
  gap: calc(10px * var(--ui-scale));
  margin-top: calc(-38px * var(--ui-scale));
  padding: 0 calc(26px * var(--ui-scale)) calc(22px * var(--ui-scale));
}
.landmark-card__title {
  margin: 0;
  font: var(--text-3xl)/1.2 var(--f-display);
  letter-spacing: 0.06em;
  color: var(--paper-50);
  text-shadow: 0 2px 8px #000;
}
.landmark-card__lit {
  margin: 0;
  font: var(--text-sm)/1.3 var(--f-sans);
  letter-spacing: 0.08em;
  color: var(--gold-400);
}
.landmark-card__prose {
  margin: 0;
  max-height: calc(9.5em * 1.7);
  overflow-y: auto;
  white-space: pre-line;
  font: var(--text-md)/var(--lh-narrative) var(--f-serif);
  color: var(--paper-200);
}
.landmark-card__go {
  justify-self: end;
  display: inline-flex;
  align-items: center;
  gap: calc(12px * var(--ui-scale));
  min-width: calc(160px * var(--ui-scale));
  min-height: calc(42px * var(--ui-scale));
  margin-top: calc(4px * var(--ui-scale));
  padding: 0 calc(18px * var(--ui-scale));
  justify-content: center;
  border: 1px solid var(--gold-600);
  border-radius: var(--radius-sm);
  background: rgba(185, 154, 96, 0.14);
  color: var(--paper-50);
  font: var(--text-md)/1 var(--f-sans);
  letter-spacing: 0.16em;
  cursor: pointer;
  transition:
    background-color var(--motion-fast) var(--ease-standard),
    border-color var(--motion-fast) var(--ease-standard);
}
.landmark-card__go kbd {
  font: var(--text-xs)/1 var(--f-sans);
  letter-spacing: 0.04em;
  color: var(--gold-300);
  padding: calc(3px * var(--ui-scale)) calc(6px * var(--ui-scale));
  border: 1px solid rgba(228, 200, 142, 0.35);
  border-radius: calc(3px * var(--ui-scale));
}
.landmark-card__go:hover,
.landmark-card__go:focus-visible {
  border-color: var(--gold-400);
  background: var(--gold-glow);
  outline: none;
}
.landmark-card__go:focus-visible {
  box-shadow: 0 0 0 1px var(--gold-400), var(--focus);
}
</style>
