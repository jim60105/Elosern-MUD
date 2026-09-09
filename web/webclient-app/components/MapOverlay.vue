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
import { computed, onMounted, ref, watch } from "vue";
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
const body = ref(null);
const currentNodeId = computed(() =>
  props.localMap.nodes?.find((node) => node.visibility === "current")?.id,
);

function revealCurrentNode() {
  const node = body.value?.querySelector('[data-visibility="current"]');
  const viewport = node?.closest(".local-map__viewport");
  if (!node || !viewport || typeof node.scrollIntoView !== "function") return;
  const bounds = node.getBoundingClientRect();
  const visible = viewport.getBoundingClientRect();
  if (bounds.top < visible.top + 20 || bounds.bottom > visible.bottom - 20) {
    node.scrollIntoView({ block: "center", inline: "nearest" });
  }
}

// Recenter only on opening or actual travel; ordinary updates must not
// interrupt a player scrolling through remembered locations.
onMounted(revealCurrentNode);
watch(currentNodeId, revealCurrentNode, { flush: "post" });

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
  <div ref="body" class="map-overlay-body" data-testid="map-overlay">
    <p
      v-if="!available"
      class="map-overlay__unavailable"
      data-testid="map-overlay-unavailable"
    >
      {{ reasonMessage }}
    </p>
    <div v-else class="map-overlay__content" data-testid="map-overlay-content">
      <div class="map-overlay__guide">
        <p>點選可通行的相鄰節點，繼續探索。</p>
        <span>Tab 切換路徑 · Enter 確認移動</span>
      </div>
      <!-- Both model-selected layouts use the same renderer. Tall city
           streets and dense interior graphs stay scrollable at a readable
           scale instead of shrinking the whole diagram to viewport height. -->
      <MapLattice
        :local-map="localMap"
        :variant="localMap.layoutVariant || 'lattice'"
        :col-pitch="280"
        :row-pitch="212"
        :label-max="10"
        :label-font="14"
        :marker-scale="2.2"
        :max-width="848"
        :max-height="null"
        :fill-width="true"
        :overlay-chrome="true"
        :marker-names="true"
        :marker-name-font="11"
        @move="handleMove"
      />
    </div>
  </div>
</template>

<style scoped>
.map-overlay-body {
  height: 100%;
  min-height: 360px;
}

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
  gap: 20px;
  height: 100%;
}

.map-overlay__content :deep(.local-map__viewport--canvas) {
  flex: 1;
  min-height: 160px;
}

.map-overlay__guide {
  flex: none;
  order: -2;
  width: 100%;
  max-width: 848px;
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px 20px;
}

.map-overlay__guide p {
  margin: 0;
  color: var(--paper-100);
  font-family: var(--f-serif);
}

.map-overlay__guide span {
  color: var(--paper-300);
  font-size: 12px;
}

.map-overlay__content :deep(.local-map__legend) {
  flex: none;
  order: -1;
  width: 100%;
  max-width: 848px;
  box-sizing: border-box;
  padding: 16px;
  border: var(--line);
  border-radius: var(--radius);
  background: var(--ink-900);
  box-shadow: 0 4px 16px #0006;
}

.map-overlay__content :deep(.local-map__lattice--canvas) {
  border-color: var(--gold-500);
  box-shadow: inset 0 0 60px #0005;
}
</style>
