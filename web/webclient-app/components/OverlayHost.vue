<script setup>
// OverlayHost (H5, webclient-hud-05-overlays-and-command-line, design D7;
// framing unified by webclient-drawer-frame-unification): the shared
// overlay workspace — the same opaque ink panel and bounds as the reference
// drawers, under the shared DrawerHeader (registry glyph, title, subtitle,
// labelled close control). A scrim below the top navigation recesses the
// band's exposed control strip and absorbs pointer activation without
// closing the overlay; the navigation stays operable above it, so another
// trigger still replaces the open overlay.
// Focus is trapped through H4's shared `focus-trap.js` (one trap, not a
// second one). The opener element is captured at open time by the caller;
// when the open overlay name changes (one overlay replaces another) the
// trap is re-initialised with the new opener, so closing restores focus to
// the most recent trigger, never to the trigger of the replaced overlay.
// Escape closes the surface and restores focus to its trigger on every path.
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { createFocusTrap } from "./focus-trap.js";
import DrawerHeader from "./DrawerHeader.vue";
import { toolLabel } from "./nav-tools.js";

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
// location label as a suffix; a 工具 overlay's title is its opener's label
// from the shared tool model, so the header, the opener's accessible name
// and its tooltip read the same words.
function titleFor(name) {
  if (name === "map") {
    return props.locationLabel ? `地圖 · ${props.locationLabel}` : "地圖";
  }
  if (name === "settings") return "設定";
  return toolLabel(name) ?? toolLabel("help");
}

// The header glyph is the registry key of the navigation control that opens
// the overlay, so header and opener always agree.
const OVERLAY_ICONS = {
  map: "map",
  settings: "settings",
  lineage: "lineage",
  codex: "codex",
  gallery: "gallery",
  help: "help",
};
function iconFor(name) {
  return OVERLAY_ICONS[name] || null;
}

function subtitleFor(name) {
  if (name === "map") return "所在位置與相鄰路徑";
  if (name === "settings") return "閱讀偏好與輔助顯示";
  if (name === "lineage") return "熟練度 · 見頂 · 前置";
  if (name === "codex") return "稱號 · 異名 · 提名中";
  if (name === "gallery") return "記錄不同的你，也是旅途的一部分。";
  if (name === "help") return "按鍵、指令列與閱讀操作";
  return "";
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
  <div class="overlay-host-scrim" data-testid="overlay-host-scrim" aria-hidden="true"></div>
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
    <DrawerHeader
      data-testid="overlay-host-header"
      surface="overlay-host"
      :icon="iconFor(overlay)"
      :title="titleFor(overlay)"
      :subtitle="subtitleFor(overlay)"
      @close="onClose"
    />
    <div class="overlay-host__body" data-testid="overlay-host-body">
      <slot :overlay="overlay" :map-model="mapModel" :mapModel="mapModel"></slot>
    </div>
  </section>
</template>

<style scoped>
/* The scrim covers everything below the top navigation behind the overlay:
   its fill alone recesses the band's exposed control strip (blur is
   optional decoration), and it absorbs pointer activation without closing
   the overlay. It starts at the navigation's bottom edge, so the navigation
   stays uncovered and operable; it sits one step under the overlay's tier. */
.overlay-host-scrim {
  position: fixed;
  inset: var(--header-h) 0 0;
  z-index: 91;
  background: var(--surface-scrim);
}
@supports (backdrop-filter: blur(1px)) {
  .overlay-host-scrim { backdrop-filter: blur(2px) saturate(.8); }
}

/* The reference workspace, shared with the drawers: 12px under the top
   navigation, 16px side insets, `--workspace-bottom` above the viewport
   bottom, a fully opaque ink panel. The tier stays 92 (below the modal
   tier) so the gallery's teleported nested editors stack above it. */
.overlay-host {
  position: fixed;
  inset: calc(var(--header-h) + 12px) 16px var(--workspace-bottom);
  z-index: 92;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #bca57966;
  border-radius: 8px;
  background: var(--surface-panel);
  box-shadow: 0 16px 64px #000a, inset 0 1px 0 #e8d8aa14;
}

.overlay-host__body {
  flex: 1;
  box-sizing: border-box;
  padding: 28px;
  max-width: 1180px;
  width: 100%;
  margin: 0 auto;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-color: var(--gold-500) transparent;
  scrollbar-width: thin;
}

/* The full map is a picture, not a reading column: it takes the surface's
   whole width so the fitted view spends the room on the drawing. */
.overlay-host[data-elosern-overlay="map"] .overlay-host__body { max-width: none; }
.overlay-host[data-elosern-overlay="gallery"] .overlay-host__body { max-width: none; padding: 0; }

@media (max-width: 700px) {
  .overlay-host__body { padding: 16px; }
}
</style>
