<script setup>
// OverlayHost (H5, webclient-hud-05-overlays-and-command-line, design D7):
// the shared full-screen overlay surface. The draft's exact `.full` geometry
// (position:fixed; top:46px; left:0; right:0; bottom:0; z-index:92) keeps
// the command line visible under the overlay; the header row carries the
// icon slot, the overlay title, the subtitle, and a labelled close control.
// Focus is trapped through H4's shared `focus-trap.js` (one trap, not a
// second one). The opener element is captured at open time by the caller;
// when the open overlay name changes (one overlay replaces another) the
// trap is re-initialised with the new opener, so closing restores focus to
// the most recent trigger, never to the trigger of the replaced overlay.
// Escape closes the surface and restores focus to its trigger on every path.
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { createFocusTrap } from "./focus-trap.js";

const props = defineProps({
  // The single open-overlay name (design D8): map | settings | help | lineage | codex.
  overlay: { type: String, required: true },
  // The trigger control that opened this overlay, captured at open time
  // (design D7). Focus is restored to it on every close path.
  opener: { type: Object, default: null },
  // The committed `local_map` model, passed straight through to the `map`
  // body (design D4) so a replaced payload re-renders the available /
  // unavailable branch live.
  mapModel: { type: Object, default: null },
  // The committed location label (the status slice) for the map title.
  locationLabel: { type: String, default: "" },
});

const emit = defineEmits(["close", "move"]);

const hostRef = ref(null);
let trap = null;

// Per-overlay header copy from the binding design draft (docs/design/
// elosern-redesign/index.html). The map title carries the committed
// location label as a suffix; the other titles are static.
function titleFor(name) {
  if (name === "map") {
    return props.locationLabel ? `地圖 · ${props.locationLabel}` : "地圖";
  }
  if (name === "settings") return "設定";
  if (name === "lineage") return "技能系譜";
  if (name === "codex") return "稱號冊";
}

function subtitleFor(name) {
  if (name === "map") return "分層 · 霧戰 · 路徑";
  if (name === "settings") return "音訊 · 顯示 · 可達 · 輸入";
  if (name === "lineage") return "熟練度 · 見頂 · 前置";
  if (name === "codex") return "稱號 · 異名 · 提名中";
  return "分類 → 條目 → 子主題";
}

function initTrap() {
  // Re-initialisation (design D7): when the open overlay name or its opener
  // changes, the previous trap's opener belongs to the replaced overlay;
  // drop it and rebuild the trap with the new opener.
  trap = null;
  if (hostRef.value) {
    trap = createFocusTrap(hostRef.value, { openerEl: props.opener });
    trap.enter();
  }
}

function onKeydown(event) {
  if (event.key === "Escape") {
    // The surface owns its Escape handling: close the overlay and restore
    // focus to the opener (H4's focus-trap module owns the focus routing).
    event.stopPropagation();
    onClose();
    return;
  }
  if (event.key !== "Tab") {
    // A focus-trapped surface owns every key it receives
    // (webclient-pointer-activation): stop propagation so the document-level
    // keyboard bridge (and the router behind the surface) never consumes
    // navigation keys while the overlay holds trapped focus — "the router
    // consumes nothing behind it".
    event.stopPropagation();
  }
  if (trap) {
    trap.onKeydown(event);
  }
}

function onClose() {
  if (trap) {
    trap.restore();
    trap = null;
  }
  emit("close");
}

onMounted(() => {
  initTrap();
});
watch(
  () => [props.overlay, props.opener],
  () => {
    initTrap();
  },
  { deep: true },
);
onBeforeUnmount(() => {
  if (trap) {
    trap.restore();
    trap = null;
  }
});
</script>

<template>
  <section
    ref="hostRef"
    class="overlay-host"
    role="dialog"
    aria-modal="true"
    :aria-label="titleFor(overlay)"
    data-testid="overlay-host"
    :data-elosern-overlay="overlay"
    @keydown="onKeydown"
  >
    <header class="overlay-host__header" data-testid="overlay-host-header">
      <slot name="icon">
        <svg
          v-if="overlay === 'map'"
          class="overlay-host__icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          aria-hidden="true"
        >
          <path d="M12 21s-7-5.5-7-11a7 7 0 0 1 14 0c0 5.5-7 11-7 11Z" />
          <circle cx="12" cy="10" r="2.5" />
        </svg>
        <svg
          v-else-if="overlay === 'settings'"
          class="overlay-host__icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="3" />
          <path d="M19 12a7 7 0 0 0-.1-1l2-1.5-2-3.5-2.4 1a7 7 0 0 0-1.7-1l-.4-2.5h-4l-.4 2.5a7 7 0 0 0-1.7 1l-2.4-1-2 3.5 2 1.5a7 7 0 0 0 0 2l-2 1.5 2 3.5 2.4-1a7 7 0 0 0 1.7 1l.4 2.5h4l.4-2.5a7 7 0 0 0 1.7-1l2.4 1 2-3.5-2-1.5a7 7 0 0 0 .1-1Z" />
        </svg>
        <svg
          v-else
          class="overlay-host__icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="9" />
          <path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-1 .4-1 1.2-1 2.2M12 17h.01" stroke-linecap="round" />
        </svg>
      </slot>
      <h3 class="overlay-host__title">{{ titleFor(overlay) }}</h3>
      <span class="overlay-host__subtitle">{{ subtitleFor(overlay) }}</span>
      <button
        type="button"
        class="overlay-host__close"
        data-testid="overlay-host-close"
        aria-label="關閉"
        @click="onClose"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
          <path d="M6 6l12 12M18 6 6 18" stroke-linecap="round" />
        </svg>
      </button>
    </header>
    <div class="overlay-host__body" data-testid="overlay-host-body">
      <slot :overlay="overlay" :map-model="mapModel"></slot>
    </div>
  </section>
</template>

<style scoped>
.overlay-host {
  position: fixed;
  top: 46px;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 92;
  display: flex;
  flex-direction: column;
  background: var(--ink-950);
}

.overlay-host__header {
  flex: none;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 26px;
  border-bottom: var(--line);
  background: linear-gradient(180deg, #14101a, #0e0b12);
}

.overlay-host__icon {
  flex: none;
  width: 20px;
  height: 20px;
  color: var(--gold-400);
}

.overlay-host__title {
  margin: 0;
  font-family: var(--f-display);
  font-size: 22px;
  letter-spacing: 0.04em;
  color: var(--paper-50);
}

.overlay-host__subtitle {
  font-size: 12px;
  color: var(--paper-500);
}

.overlay-host__close {
  flex: none;
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  padding: 0;
  color: var(--paper-300);
  background: transparent;
  border: var(--line);
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.overlay-host__close svg {
  width: 16px;
  height: 16px;
}

.overlay-host__close:hover {
  color: var(--seal-400);
  border-color: var(--seal-400);
}

.overlay-host__close:focus-visible {
  color: var(--gold-400);
  border-color: var(--gold-400);
}

.overlay-host__body {
  flex: 1;
  padding: 22px 26px;
  max-width: 900px;
  width: 100%;
  margin: 0 auto;
  min-height: 0;
  overflow-y: auto;
}
</style>
