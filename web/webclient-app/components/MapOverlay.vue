<script setup>
// MapOverlay (B5 overlays family): the body content of the shared full-screen
// overlay surface (H5, webclient-hud-05-overlays-and-command-line, task 6.1).
// The modal chrome (position, z-index, close button, aria-modal) now belongs
// to the OverlayHost surface; this component renders only the `local_map`
// payload's branch — the available lattice (reused MapLattice at the
// overlay's own larger scale) or the registry-owned unavailable reason.
// The host's focus trap, Escape, and the labelled close control own the
// surface's behaviour. Actionable adjacent nodes forward a `move` event so
// the C-wire store can consume the OOB `explore.move` intent.
import { computed } from "vue";
import MapLattice from "./MapLattice.vue";

const props = defineProps({
  // The committed `local_map` v1 panel payload (the available form or the
  // registry-owned unavailable form). A replaced payload re-renders the
  // matching branch live (the delta's read-model-update requirement).
  localMap: { type: Object, required: true },
});

const emit = defineEmits(["move", "open-map"]);

// Reactive to OOB read-model updates: when the `local_map` payload is
// replaced (e.g. the C-wire store publishes a new snapshot), the body
// re-renders the available/unavailable branch instead of showing a stale
// state.
const available = computed(() => props.localMap.available === true);
const reasonMessage = computed(() => props.localMap.reason?.message ?? "");

// Re-emit LocalMap's move intent ({ exit_ref, destination }) so the C-wire
// store can consume the OOB explore.move action.
function handleMove(payload) {
  emit("move", payload);
}

// The `open-map` emit is kept for the parent's overlay slice (AppClient's
// `onMapExpand`); the expand trigger now lives only in the island's chrome
// (`LocalMap.vue`), so the overlay body itself no longer re-emits it.
</script>

<template>
  <div class="map-overlay-body" data-testid="map-overlay">
    <p
      v-if="!available"
      class="map-overlay__unavailable"
      data-testid="map-overlay-unavailable"
    >
      {{ reasonMessage }}
    </p>
    <div v-else class="map-overlay__content" data-testid="map-overlay-content">
      <!-- The shared lattice renderer at the overlay's larger scale: the
           pitch fills the body's 848px content width for the seed's 3-column
           lattice (900px host cap − 52px padding), labels truncate later
           than the island's 4 characters, and markers scale by the same
           factor so the crowding fix's non-collision geometry carries over.
           No height cap is passed — the host body's `overflow-y: auto` is
           the documented fallback for tall, dense payloads (design.md).
           `overlay-chrome` turns on the draft mapcanvas framing (the dark
           radial-gradient canvas + rounded ink border, pure CSS) and the
           teardrop pin anchored inside the lattice SVG above the current
           marker (webclient-map-01-draft-chrome design D4). -->
      <MapLattice
        :local-map="localMap"
        :variant="localMap.layoutVariant || 'lattice'"
        :col-pitch="280"
        :row-pitch="212"
        :label-max="10"
        :marker-scale="4.83"
        :max-width="848"
        :max-height="null"
        :fill-width="true"
        :overlay-chrome="true"
        @move="handleMove"
      />
    </div>
  </div>
</template>

<style scoped>
.map-overlay__unavailable {
  margin: 0;
  padding: var(--sp-2) var(--sp-3);
  color: var(--paper-300);
  background: var(--panel-hi);
  border: 1px dashed var(--warn);
  border-radius: var(--radius-sm);
  font-family: var(--f-mono);
  font-size: var(--text-sm);
}

.map-overlay__content {
  display: flex;
  flex-direction: column;
  align-items: center;
  /* The shared lattice renders its canvas at the body's available width and
     its state legend below it; a row-direction flex would place the legend
     beside the full-width canvas. */
}
</style>
