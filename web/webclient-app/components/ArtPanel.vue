<script setup>
// ArtPanel (H1, webclient-hud-01-shell-and-scene, design D8): the art
// surface reduced to its portrait-catalog section — the scene frame is
// superseded by `SceneBackdrop` (the stage backdrop). The unmodified
// portrait requirements survive in the panel: the catalog focus flow, the
// missing-image placeholder, the portrait full-view control (MODIFIED
// `webclient-art-panel`: "the portrait SHALL have its own accessible
// full-view control"), and literal rendering of HTML-like labels.
import { computed, ref, watch } from "vue";

const props = defineProps({
  // The committed `art` v1 panel payload: `available: true` carries
  // `scene` + `portrait_catalog`; the registry-unavailable form carries
  // `available: false` + `reason`.
  art: { type: Object, required: true },
});

// Flat entry objects keyed by catalog ID, in the catalog's own order.
const portraitEntries = computed(() => {
  if (props.art?.available === false) {
    return [];
  }
  return Object.entries(props.art.portrait_catalog ?? {}).map(([id, entry]) => ({
    id,
    ...entry,
  }));
});

// The portrait full-view state (MODIFIED webclient-art-panel: the portrait
// has its own accessible full-view control). One open state for the panel;
// the opener element (the clicked control) is remembered for the focus
// restore.
const fullViewEntry = ref(null);
const fullViewOpen = ref(false);
let openerElement = null;

function openFullView(entry, opener) {
  fullViewEntry.value = entry;
  fullViewOpen.value = true;
  openerElement = opener ?? null;
}

function closeFullView(restoreFocus) {
  if (restoreFocus && openerElement && typeof openerElement.focus === "function") {
    openerElement.focus();
  }
  fullViewOpen.value = false;
  fullViewEntry.value = null;
  openerElement = null;
}

function onFullViewKeydown(event) {
  if (event.key === "Escape") {
    event.preventDefault();
    closeFullView(true);
  }
}

defineExpose({ openFullView, closeFullView });

const PORTRAIT_STYLE = {
  aspectRatio: "3 / 4",
  objectFit: "cover",
  width: "88px",
  height: "auto",
};
</script>

<template>
  <aside class="art-panel" data-testid="art-panel">
    <h3 class="art-panel__title" data-testid="art-panel__title">美術展示</h3>

    <div
      v-if="props.art?.available === false"
      class="art-panel__unavailable"
      data-testid="art-panel__unavailable"
      :data-reason="props.art?.reason?.code"
    >
      <p class="art-panel__unavailable-reason" data-testid="art-panel__unavailable-reason">
        {{ props.art?.reason?.message }}
      </p>
    </div>

    <section v-else-if="portraitEntries.length > 0" class="art-panel__portraits" data-testid="art-panel__portraits">
      <div
        v-for="entry in portraitEntries"
        :key="entry.id"
        class="art-panel__portrait-tile"
        :data-testid="`art-panel__portrait--${entry.id}`"
        :data-placeholder="String(!!(entry.placeholder))"
        :data-status="entry.status"
      >
        <img
          v-if="entry.url"
          class="art-panel__portrait-img"
          :data-testid="`art-panel__portrait-img--${entry.id}`"
          :src="entry.url"
          :alt="entry.alt"
          :style="PORTRAIT_STYLE"
        />
        <div v-else class="art-panel__portrait-placeholder" :data-testid="`art-panel__portrait-placeholder--${entry.id}`">
          <span class="art-panel__placeholder-kind">{{ entry.placeholder?.kind }}</span>
          <p class="art-panel__placeholder-label">{{ entry.placeholder?.label }}</p>
        </div>
        <p class="art-panel__portrait-context" :data-testid="`art-panel__portrait-context--${entry.id}`">
          <span class="art-panel__portrait-context-name">{{ entry.context?.name }}</span>
          <span class="art-panel__portrait-context-role">{{ entry.context?.role }}</span>
        </p>
        <!-- The portrait's own accessible full-view control (MODIFIED
             webclient-art-panel): opens a full-screen 3:4 view; Escape
             closes and restores focus. -->
        <button
          v-if="entry.url"
          type="button"
          class="art-panel__portrait-fullview"
          :data-testid="`art-panel__portrait-fullview--${entry.id}`"
          aria-label="開啟全圖"
          @click="openFullView(entry, $event.currentTarget)"
        >
          全圖
        </button>
      </div>
    </section>

    <div
      v-if="fullViewOpen && fullViewEntry"
      class="art-panel__fullview"
      data-testid="art-panel__fullview"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      @keydown="onFullViewKeydown"
    >
      <img
        class="art-panel__fullview-image"
        :data-testid="`art-panel__fullview-img--${fullViewEntry.id}`"
        :src="fullViewEntry.url"
        :alt="fullViewEntry.alt"
      />
      <p class="art-panel__fullview-label">{{ fullViewEntry.context?.name }}</p>
    </div>
  </aside>
</template>

<style scoped>
.art-panel {
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
  box-sizing: border-box;
  /* Compressible inside the capped island anchors (design D12): when the
     panel content outgrows the anchor budget the root shrinks instead of
     overflowing the budget. */
  min-height: 0;
  padding: var(--sp-3) var(--sp-4);
  background: var(--panel);
  border: var(--line);
  border-radius: var(--radius);
  font-family: var(--f-sans);
}

.art-panel__title {
  margin: 0;
  color: var(--paper-100);
  font-family: var(--f-display);
  font-size: 1em;
}

.art-panel__unavailable {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 64px;
  background: var(--panel-hi);
  border: 1px dashed var(--seal-600);
  border-radius: var(--radius-sm);
}

.art-panel__unavailable-reason {
  margin: 0;
  color: var(--paper-300);
  font-size: 0.85em;
}

.art-panel__portraits {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-3);
  padding-top: var(--sp-2);
  border-top: var(--line);
}

.art-panel__portrait-tile {
  position: relative;
  width: 88px;
  aspect-ratio: 3 / 4;
  overflow: visible;
  border-radius: var(--radius-sm);
}

.art-panel__portrait-placeholder {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: var(--sp-1);
  padding: var(--sp-2);
  height: 100%;
  background: var(--panel-hi);
  border: 1px dashed var(--seal-600);
  border-radius: var(--radius-sm);
}

.art-panel__portrait-context {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  margin: 0;
  padding: 2px var(--sp-1);
  background: var(--ink-950);
  color: var(--paper-100);
  font-family: var(--f-mono);
  font-size: 0.75em;
}

.art-panel__portrait-context-role {
  color: var(--gold-400);
}

/* The portrait's own full-view control (MODIFIED webclient-art-panel). */
.art-panel__portrait-fullview {
  position: absolute;
  top: 4px;
  right: 4px;
  background: var(--ink-780);
  border: 1px solid var(--ink-600);
  border-radius: var(--radius-sm);
  color: var(--paper-300);
  cursor: pointer;
  font-size: 0.7em;
  padding: 1px 6px;
}

.art-panel__portrait-fullview:hover {
  border-color: var(--gold-500);
  color: var(--paper-50);
}

.art-panel__fullview {
  position: fixed;
  inset: 0;
  z-index: var(--z-surface-modal);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--ink-950);
  outline: none;
}

.art-panel__fullview-image {
  max-height: 86vh;
  aspect-ratio: 3 / 4;
}

.art-panel__fullview-label {
  margin: var(--sp-3) 0 0;
  color: var(--paper-300);
  font-size: var(--text-sm);
}

.art-panel__placeholder-kind {
  color: var(--paper-500);
  font-family: var(--f-mono);
  font-size: 0.8em;
  text-transform: uppercase;
}

.art-panel__placeholder-label {
  margin: 0;
  color: var(--paper-300);
  font-size: 0.85em;
}
</style>
