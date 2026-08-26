<script setup>
// MapOverlay (B5 overlays family): the body content of the shared full-screen
// overlay surface (H5, webclient-hud-05-overlays-and-command-line, task 6.1).
// The modal chrome (position, z-index, close button, aria-modal) now belongs
// to the OverlayHost surface; this component renders only the `local_map`
// payload's branch — the available lattice (reused LocalMap) or the
// registry-owned unavailable reason. The host's focus trap, Escape, and the
// labelled close control own the surface's behaviour. Actionable adjacent
// nodes forward a `move` event so the C-wire store can consume the OOB
// `explore.move` intent.
import { computed } from "vue";
import LocalMap from "./LocalMap.vue";

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

// The island's full-map trigger (task 6.2): forward to the parent's
// overlay slice so the map overlay opens through the shared surface.
function handleOpenMap() {
  emit("open-map");
}
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
      <LocalMap :local-map="localMap" @move="handleMove" @open-map="handleOpenMap" />
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
  justify-content: center;
}
</style>
