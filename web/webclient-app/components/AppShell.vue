<script setup>
// AppShell (the B1 root/layout component): composes the core narrative
// family — TopBar, the center NarrativeFeed, the persistent CommandDrawer,
// the ConnectOverlay, the preserved action live region and offline overlay —
// into the ink-night fullscreen desktop shell.
//
// B1 is offline and mock-driven (design D3): every surface renders only the
// slice passed in and emits user-intent events (`submit-command`) — no store
// and no transport yet (C1/C3). The empty side slots are where the B2–B4
// panel families mount at wiring; they render nothing while empty (a surface
// with no backing read model is never shown).
//
// Shell-owned view behavior (pre-store): the `/` key toggles the drawer and
// focuses the field (slash-as-text inside editables is untouched), Escape
// releases a focused drawer back to the narrative pane, and the mount
// retires the replaced text fallback (hidden, not removed) so the shell
// cannot stack below the viewport.
import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import ConnectOverlay from "./ConnectOverlay.vue";
import CommandDrawer from "./CommandDrawer.vue";
import NarrativeFeed from "./NarrativeFeed.vue";
import TopBar from "./TopBar.vue";
import { retireReplacedFallback } from "../fallback.js";

const props = defineProps({
  // The contextual mode slice (world/combat/dialogue/menu/creation); the
  // B5 waves gate panels on it. Rendered as data-elosern-mode.
  mode: { type: String, default: "explore" },
  connected: { type: Boolean, default: false },
  locationLabel: { type: String, default: null },
  timeLabel: { type: String, default: null },
  narrative: { type: Array, default: () => [] },
  connectionStatus: {
    type: String,
    default: "connecting",
    validator: (value) =>
      ["connecting", "waiting", "offline", "ready"].includes(value),
  },
  offline: { type: Boolean, default: false },
  // The action client's uncertain-mutation flag (a dispatched mutation whose
  // result was withheld by a mid-flight detach). Exposed on the offline
  // overlay as `data-uncertain` so the uncertain-result notice is DOM-observable.
  uncertain: { type: Boolean, default: false },
  prompt: { type: String, default: "" },
  commandHistory: { type: Array, default: () => [] },
});

const emit = defineEmits(["submit-command"]);

const drawerOpen = ref(false);
const drawer = ref(null);
const feed = ref(null);

function isEditable(target) {
  if (!target || typeof target.closest !== "function") {
    return false;
  }
  return (
    target.isContentEditable === true ||
    !!target.closest("input, textarea, select, [contenteditable='true'], [contenteditable='']")
  );
}

function openDrawer() {
  drawerOpen.value = true;
  void nextTick().then(() => drawer.value?.focusField());
}

function closeDrawer(restoreFocus) {
  drawerOpen.value = false;
  if (restoreFocus) {
    feed.value?.focus();
  }
}

function toggleDrawer() {
  if (drawerOpen.value) {
    closeDrawer(true);
  } else {
    openDrawer();
  }
}

function onFocusParent() {
  // The drawer's own Escape path (field focus).
  closeDrawer(true);
}

function onSubmit(text) {
  // One deliberate send through the single dispatch entry (the store routes
  // it at C1; the transport carries ordinary text, never ui_action).
  emit("submit-command", text);
}

// The shell-wide key claims before the wiring wave: `/` toggles the drawer,
// Escape releases an open drawer. Unclaimed keys fall through untouched.
function onWindowKeydown(event) {
  if (event.ctrlKey || event.metaKey || event.altKey) {
    return;
  }
  const key = event.key;
  if (key === "/" && !isEditable(event.target)) {
    if (event.repeat) {
      return;
    }
    event.preventDefault();
    toggleDrawer();
    return;
  }
  if (key === "Escape" && drawerOpen.value) {
    // The drawer field's own handler runs first (target bubble) and already
    // released it; this covers drawer focus that is not on the field.
    if (!drawerOpen.value) {
      return;
    }
    event.preventDefault();
    closeDrawer(true);
  }
}

onMounted(() => {
  window.addEventListener("keydown", onWindowKeydown);
  retireReplacedFallback();
});

onBeforeUnmount(() => {
  window.removeEventListener("keydown", onWindowKeydown);
});
</script>

<template>
  <section
    class="elosern elosern-app-shell"
    data-testid="elosern-vue-root"
    data-elosern-stage="showcase-core"
    :data-elosern-mode="mode"
  >
    <TopBar
      :connected="connected"
      :location-label="locationLabel"
      :time-label="timeLabel"
    />

    <div class="app-shell__main">
      <aside class="app-shell__panel app-shell__panel-left" aria-label="左側面板">
        <slot name="panel-left" />
      </aside>
      <main class="app-shell__center">
        <NarrativeFeed ref="feed" :lines="props.narrative" />
      </main>
      <aside class="app-shell__panel app-shell__panel-right" aria-label="右側面板">
        <slot name="panel-right" />
      </aside>
    </div>

    <div
      id="elosern-action-live"
      class="elosern-live"
      role="status"
      aria-live="polite"
      aria-atomic="true"
      data-testid="action-live-region"
    ></div>

    <!-- C3 (webclient-vue-09-wire-transport-mount): the store-bound
         ActionDock mounts here; the keyboard router keeps focusing the
         preserved #action-dock target rendered by the dock. -->
    <slot name="action-dock" />

    <CommandDrawer
      ref="drawer"
      :open="drawerOpen"
      :prompt="props.prompt"
      :history="props.commandHistory"
      @submit="onSubmit"
      @toggle="toggleDrawer"
      @focus-parent="onFocusParent"
    />

    <div
      id="elosern-offline-overlay"
      class="elosern-offline"
      role="alert"
      aria-live="assertive"
      :data-visible="offline ? 'true' : 'false'"
      :data-uncertain="uncertain ? 'true' : 'false'"
    >
      <div class="offline-title">連線中斷</div>
      <div class="offline-note">已暫停圖形化操作，等待重新連線。</div>
    </div>

    <ConnectOverlay :status="props.connectionStatus" />
  </section>
</template>

<style>
.elosern-app-shell {
  position: relative;
  box-sizing: border-box;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto auto;
  height: 100%;
  min-height: 0;
}

.elosern-app-shell .app-shell__main {
  display: grid;
  grid-template-columns: minmax(0, 300px) minmax(0, 1fr) minmax(0, 300px);
  grid-template-rows: 100%;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
}

/* The side panels own their content within the bounded main row: they scroll
   internally instead of forcing the 1fr row to grow (which pushed the
   action-dock and command-drawer below the supported viewports). */
.elosern-app-shell .app-shell__panel {
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

/* Empty in B1: the B2–B4 panel families own their own slots at wiring; an
   empty panel renders nothing (no surface without a backing read model). */
.elosern-app-shell .app-shell__panel:empty {
  display: none;
}

.elosern-app-shell .app-shell__center {
  display: flex;
  flex-direction: column;
  min-height: 0;
  min-width: 0;
}

.elosern-app-shell .app-shell__center .elosern-narrative {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.elosern-app-shell .elosern-live {
  min-height: 0;
  color: var(--paper-100);
  border-left: 3px solid var(--seal-500);
  padding-left: 0.5rem;
  font-size: var(--text-sm);
  /* Announcement-only: never intercepts pointer events. */
  pointer-events: none;
}

.elosern-app-shell .elosern-live:empty {
  display: none;
}

.elosern-app-shell #elosern-offline-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: none;
  background: rgba(8, 7, 10, 0.82);
  color: var(--paper-100);
  font-family: var(--f-sans);
  text-align: center;
  padding: 2rem;
}

.elosern-app-shell #elosern-offline-overlay[data-visible="true"] {
  display: block;
}

.elosern-app-shell #elosern-offline-overlay .offline-title {
  margin-top: 18vh;
  font-family: var(--f-display);
  font-size: 1.4rem;
  font-weight: 600;
  color: var(--seal-400);
}

.elosern-app-shell #elosern-offline-overlay .offline-note {
  margin-top: var(--sp-3);
  color: var(--paper-500);
}
</style>
