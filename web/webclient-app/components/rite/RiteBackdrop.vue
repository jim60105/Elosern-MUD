<script setup>
// RiteBackdrop (landmark-rite-surfaces design D5; landmark rites design
// §12.2): the rite stage's ground. The archetype art fills the stage under
// an ink wash that keeps the figures and the panel readable; without art it
// is quiet ink, never substitute art. A plate at the top right names the
// landmark and the guardian in text. It has no interaction and emits
// nothing.
import { computed } from "vue";
import ArtworkPreview from "../ArtworkPreview.vue";

const props = defineProps({
  // The committed `rite` panel.
  rite: { type: Object, required: true },
  // The committed art panel: the availability the descriptor is judged by.
  artPanel: { type: Object, default: null },
});

const hasArt = computed(() => !!props.rite.art);
</script>

<template>
  <div class="rite-backdrop" :class="{ 'is-empty': !hasArt }" data-testid="rite-backdrop">
    <div v-if="hasArt" class="rite-backdrop__art" aria-hidden="true">
      <ArtworkPreview :artwork="rite.art" :panel="artPanel" />
    </div>
    <p class="rite-backdrop__plate" data-testid="rite-backdrop-plate">
      <span class="rite-backdrop__gem" aria-hidden="true">◆</span>
      <span class="rite-backdrop__names">{{ rite.district.landmark }}<span
        class="rite-backdrop__sep">・</span><span class="rite-backdrop__guardian">{{ rite.guardian.name }}</span></span>
    </p>
  </div>
</template>

<style>
/* The stage ground: the art full-bleed under an ink wash darker at the left
   (the party's side) and the foot (the band), so the figures, the panel and
   the message window stay readable over any painting. */
.rite-backdrop {
  position: absolute;
  inset: 0;
  overflow: hidden;
  background:
    radial-gradient(70% 60% at 50% 45%, rgba(185, 154, 96, 0.1), transparent 70%),
    linear-gradient(180deg, #1b1a20, #0c0d11);
}
.rite-backdrop__art {
  position: absolute;
  inset: 0;
}
.rite-backdrop__art > .artwork-preview {
  position: absolute;
  inset: 0;
}
.rite-backdrop::after {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(90deg, rgba(8, 9, 12, 0.5), rgba(8, 9, 12, 0.08) 45%, rgba(8, 9, 12, 0.3)),
    linear-gradient(180deg, rgba(8, 9, 12, 0.2), rgba(8, 9, 12, 0) 30%, rgba(8, 9, 12, 0.7));
}
/* No art: a quiet horizon line across the ink. */
.rite-backdrop.is-empty::before {
  content: "";
  position: absolute;
  left: 18%;
  right: 18%;
  top: 46%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(228, 200, 142, 0.3), transparent);
}
.rite-backdrop__plate {
  position: absolute;
  z-index: 1;
  /* The stage runs under the header bar: the plate starts where the HUD's
     top anchors do, below the bar. */
  right: calc(24px * var(--ui-scale));
  top: calc(var(--header-h) + var(--stage-inset-y));
  display: inline-flex;
  align-items: baseline;
  gap: calc(8px * var(--ui-scale));
  max-width: 40%;
  margin: 0;
  padding: calc(6px * var(--ui-scale)) calc(14px * var(--ui-scale));
  border: 1px solid rgba(228, 200, 142, 0.35);
  border-radius: var(--radius-sm);
  background: rgba(12, 13, 17, 0.62);
  box-shadow: 0 calc(8px * var(--ui-scale)) calc(24px * var(--ui-scale)) calc(-12px * var(--ui-scale)) rgba(0, 0, 0, 0.9);
  font: var(--text-md)/1.3 var(--f-display);
  letter-spacing: 0.14em;
  color: var(--paper-50);
  text-shadow: 0 1px 4px #000;
}
.rite-backdrop__gem {
  color: var(--gold-400);
  font-size: var(--text-sm);
}
.rite-backdrop__sep {
  color: var(--gold-500);
}
.rite-backdrop__guardian {
  color: var(--gold-300);
}
</style>
