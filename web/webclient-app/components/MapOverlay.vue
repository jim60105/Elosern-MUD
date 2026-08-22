<script setup>
// MapOverlay (B5 overlays family): a full-viewport dialog frame that hosts
// the B4 LocalMap panel (the `local_map` OOB-backed surface). It reuses —
// not re-implements — LocalMap: the lattice, the visibility states, the
// legend, and the detail line all come from that component. Actionable
// adjacent nodes forward a `move` event so the C-wire store can consume the
// OOB `explore.move` intent. The close button is client-local UI: it emits
// `close` and hides the overlay (no OOB envelope). When the payload is the
// registry-owned unavailable form, the frame renders only
// `localMap.reason.message`; nothing is invented.
import { ref, watch } from "vue";
import LocalMap from "./LocalMap.vue";

const props = defineProps({
  // The committed `local_map` v1 panel payload (the available form or the
  // registry-owned unavailable form).
  localMap: { type: Object, required: true },
  // Client-local overlay visibility; the store (C-wire) toggles this.
  open: { type: Boolean, default: true },
});

const emit = defineEmits(["move", "close"]);

// Local visibility mirrors the prop; closing hides the overlay root and the
// parent can resync by flipping `open` back to true.
const openNow = ref(props.open);
watch(
  () => props.open,
  (value) => {
    openNow.value = value;
  },
);

const available = props.localMap.available === true;
const reasonMessage = props.localMap.reason?.message ?? "";

// Re-emit LocalMap's move intent ({ exit_ref, destination }) so the C-wire
// store can consume the OOB explore.move action.
function handleMove(payload) {
  emit("move", payload);
}

function handleClose() {
  openNow.value = false;
  emit("close");
}
</script>

<template>
  <section
    v-if="openNow"
    class="elosern map-overlay"
    role="dialog"
    aria-label="區域地圖"
    data-testid="map-overlay"
  >
    <div class="map-overlay__frame" data-testid="map-overlay-frame">
      <header class="map-overlay__header" data-testid="map-overlay-header">
        <h2 class="map-overlay__title" data-testid="map-overlay-title">
          區域地圖
        </h2>
        <button
          type="button"
          class="map-overlay__close"
          data-testid="map-overlay-close"
          @click="handleClose"
        >
          關閉
        </button>
      </header>

      <p
        v-if="!available"
        class="map-overlay__unavailable"
        data-testid="map-overlay-unavailable"
      >
        {{ reasonMessage }}
      </p>
      <div v-else class="map-overlay__content" data-testid="map-overlay-content">
        <LocalMap :local-map="localMap" @move="handleMove" />
      </div>
    </div>
  </section>
</template>

<style scoped>
.map-overlay {
  position: absolute;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--panel);
}

.map-overlay__frame {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  width: min(720px, 92vw);
  padding: var(--sp-4);
  background: var(--panel-solid);
  border: var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}

.map-overlay__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
}

.map-overlay__title {
  margin: 0;
  color: var(--paper-100);
  font-family: var(--f-display);
  font-size: var(--text-body);
}

.map-overlay__close {
  flex: none;
  padding: var(--sp-1) var(--sp-2);
  color: var(--paper-300);
  border: var(--line);
  border-radius: var(--radius-sm);
  font-family: var(--f-mono);
  font-size: var(--text-sm);
  cursor: pointer;
}

.map-overlay__close:hover {
  color: var(--seal-400);
  border-color: var(--seal-400);
}

.map-overlay__close:focus-visible {
  color: var(--gold-400);
  border-color: var(--gold-400);
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
  flex: 1;
  min-height: 0;
}
</style>
