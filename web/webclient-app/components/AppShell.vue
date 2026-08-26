<script setup>
// AppShell (H1 contextual HUD, webclient-hud-01-shell-and-scene): the
// full-bleed cinematic stage (design D1). The old four-row grid and the
// 300px/1fr/300px main row are replaced by `HudFrame` — a
// `position:relative; overflow:hidden` stage with named, absolutely
// positioned anchors (`hud-left`, `hud-right`, `feed`, `dock`,
// `command-line`), sized from `--dock-h` (design D1/D10).
//
// Mode gating (design D2): the committed mode renders on the stage root as
// `data-elosern-mode`; surface visibility is CSS-only `display:none`, so
// hidden surfaces leave the accessibility tree and the tab order.
//
// Preserved DOM contract (design D6): `#action-dock` (with `data-mode`,
// `tabindex` and the listbox composite role, rendered by the dock),
// `#elosern-action-live`, `#elosern-offline-overlay`, `#inputfield`
// (inside the command line), `#narrative-unread` (inside the feed), and the
// `action-*` / `target-*` item keys all remain.
//
// Shell-owned view behavior (H5, webclient-hud-05-overlays-and-command-line):
// the command line is a permanently present bar — `/` moves focus into the
// field (no literal slash, design D2); Escape from the field returns focus
// to `#action-dock` (the field's own handler owns the key, design D3's
// ladder: open overlay → open drawer → focused command field → dock menu
// level). The mount retires the replaced text fallback (hidden, not removed).
// A mode change that hides the surface holding focus moves focus to the
// action dock *before* the CSS hides it (design D2; the side-effect-free
// `restoreDockFocus` path — no second focus path).
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import ConnectOverlay from "./ConnectOverlay.vue";
import CommandLine from "./CommandLine.vue";
import HudFrame from "./HudFrame.vue";
import NarrativeFeed from "./NarrativeFeed.vue";
import TopBar from "./TopBar.vue";
import { retireReplacedFallback } from "../fallback.js";

const props = defineProps({
  // The contextual mode slice (the store's committed mode: exploration /
  // combat / creation). Rendered on the stage root as data-elosern-mode.
  mode: { type: String, default: "exploration" },
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
  // overlay as `data-uncertain` so the uncertain-result notice is
  // DOM-observable.
  uncertain: { type: Boolean, default: false },
  prompt: { type: String, default: "" },
  commandHistory: { type: Array, default: () => [] },
  // The committed `context_actions.suggestions` envelope — the narrative
  // stream-end choice-point block renders at the feed's end through this
  // slice.
  suggestions: { type: Object, default: null },
  // The store's mutation-lock flag (connection-loss or a reload-required
  // protocol error locks all graphical mutations). Passed to the drawer so a
  // rejected send preserves the typed speech.
  mutationsLocked: { type: Boolean, default: false },
  // The open-surface registry (design D9): overlay surfaces the parent
  // (AppClient) tracks — e.g. "full-log", "creation". The drawer is owned
  // here and merged in before reaching the frame.
  openSurfaces: { type: Array, default: () => [] },
  // The derived low-HP presentation state (H2, design D5): forwarded onto
  // HudFrame's already-declared `lowhp` prop — one prop declaration and one
  // attribute binding, no structural edit to the frame. The stage then
  // renders its red vignette and the HP fill renders its pulse.
  lowHp: { type: Boolean, default: false },
  // The client-local text-to-HTML narrative preference (H5): forwarded to
  // the command line's prompt line — when off, the prompt renders as literal
  // text (the preference chooses whether the markup pipeline runs, never
  // what it permits).
  textToHtml: { type: Boolean, default: true },
  // The action client's in-flight mutation flag (H5, webclient-input-narrative):
  // forwarded to the command line so a send blocked by an in-flight mutation
  // keeps the typed speech in the field.
  inFlight: { type: Boolean, default: false },
});

const emit = defineEmits(["submit-command", "choice-action", "open-full-log", "open-overlay", "focus-lost"]);

const commandLine = ref(null);
const feed = ref(null);

// The open-surface registry (design D9): AppClient computes the set of open
// surfaces (full-log, creation, and H4's `hudDrawer`). The command line
// has no open/closed state (design D1), so the registry passes through
// unchanged.
const frameOpenSurfaces = computed(() => props.openSurfaces);

function isEditable(target) {
  if (!target || typeof target.closest !== "function") {
    return false;
  }
  return (
    target.isContentEditable === true ||
    !!target.closest("input, textarea, select, [contenteditable='true'], [contenteditable='']")
  );
}

// Side-effect-free focus rescue (task 3.5): the existing `dock.focus()`
// path, extracted so the mode watcher can reuse it without the drawer-close
// side effects (no `drawer-closed` emit, no drawer state change).
function restoreDockFocus() {
  const dock = document.getElementById("action-dock");
  if (dock && typeof dock.focus === "function") {
    dock.focus();
  }
}

// The persistent command line has no open/closed state (design D1): the
// field is always in the DOM. The shell's single focus API: `/` and the
// dock's free-form borrow (design D6) both route through `focusCommandField`.
function focusCommandField() {
  commandLine.value?.focusField();
}

// Escape from the focused field (the field's own handler emits
// `focus-parent`): nothing is sent and focus is returned to `#action-dock`
// — the only key that leaves the field (design D2). The `restoreDockFocus`
// path stays the single focus-rescue path.
function releaseCommandField(restoreFocus) {
  if (restoreFocus) {
    restoreDockFocus();
  }
}

function onSubmit(text) {
  // One deliberate send through the single dispatch entry (the store routes
  // it at C1; the transport carries ordinary text, never ui_action).
  emit("submit-command", text);
}

function onChoiceAction(intent) {
  // The narrative stream-end choice-point card/dismiss actions route through
  // the same single dispatch entry as the dock (store is the sole writer).
  emit("choice-action", intent);
}

function onOpenOverlay(name) {
  // The command line's 設定/說明 utility controls (H5, design D10): open the
  // settings/help overlays through the parent's overlay slice.
  emit("open-overlay", name);
}

// Shell-wide key claims (H5, design D2/D3): outside any editable control,
// `/` moves focus into the field — the claim is unconditional for key
// repeat (a repeated `/` still prevents a literal slash and re-focuses the
// always-present field, idempotently). Escape is NOT claimed here: the
// topmost open full-screen overlay, the open drawer (H4), the focused
// command field (its own `focus-parent` emit), and the dock's menu level
// (the router) each own that key at their rung of the precedence ladder.
// Unclaimed keys fall through untouched.
function onWindowKeydown(event) {
  if (event.ctrlKey || event.metaKey || event.altKey) {
    return;
  }
  const key = event.key;
  if (key === "/" && !isEditable(event.target)) {
    // The focus itself routes bridge -> router -> store (`toggle-drawer` ->
    // `drawerRequest` -> the shell's `focusCommandField` watcher). This window
    // binding only suppresses the browser's default (a literal `/`), so the key
    // claim and the focus both go through the public keyboard bridge contract.
    event.preventDefault();
  }
}

// A mode change that hides the surface holding focus moves focus to the
// action dock BEFORE the CSS hides the surface (design D2/D10): the
// `display:none` gate runs when the `data-elosern-mode` attribute updates,
// so the rescue must happen in the pre-update phase of the watcher.
const HIDDEN_BY_MODE = {
  creation: "[data-anchor='feed'], [data-anchor='hud-left'], [data-anchor='command-line'], .local-map",
  combat: ".local-map",
  exploration: "",
};

watch(
  () => props.mode,
  (nextMode, prevMode) => {
    const active = document.activeElement;
    const hiddenSelector = HIDDEN_BY_MODE[nextMode] || HIDDEN_BY_MODE.exploration;
    if (active && active.closest && hiddenSelector && active.closest(hiddenSelector)) {
      restoreDockFocus();
    }
    // A creation transition closes the open overlay (the store's syncHudDrawer
    // clears `hudOverlay`); route focus to the action dock so it is never lost
    // into a hidden or unmounted surface (webclient-contextual-hud: "A creation
    // transition closes the overlays ... focus is routed to the action dock").
    if (nextMode === "creation" && active && active.closest && active.closest(".overlay-host")) {
      restoreDockFocus();
    }
    // The command line is now permanent (design D1 — no drawer to close): a
    // mode change into creation only runs the pre-hide focus rescue; the CSS
    // then hides the `command-line` anchor itself (H1's matrix).
  },
);

onMounted(() => {
  window.addEventListener("keydown", onWindowKeydown);
  retireReplacedFallback();
});

onBeforeUnmount(() => {
  window.removeEventListener("keydown", onWindowKeydown);
});

// Expose the command-line focus API (H5, design D6): the store-driven
// freeform dialogue entry point (a freeform affordance activation) focuses
// the field via `focusCommandField`, and a successful dock-borrowed send
// returns focus to `#action-dock` via `releaseCommandField(true)`.
defineExpose({ focusCommandField, releaseCommandField, restoreDockFocus });
</script>

<template>
  <section
    class="elosern elosern-app-shell"
    data-testid="elosern-vue-root"
    data-elosern-stage="contextual-hud"
    :data-elosern-mode="mode"
  >
    <HudFrame
      :mode="mode"
      :open-surfaces="frameOpenSurfaces"
      :lowhp="lowHp"
    >
      <template #backdrop>
        <slot name="backdrop" />
      </template>
      <template #hud-left>
        <slot name="panel-left" />
      </template>
      <template #hud-right>
        <slot name="panel-right" />
      </template>
      <template #feed>
        <NarrativeFeed
          ref="feed"
          :lines="props.narrative"
          :suggestions="props.suggestions"
          @choice-action="onChoiceAction"
          @open-full-log="() => emit('open-full-log')"
        />
      </template>
      <template #dock>
        <slot name="action-dock" />
      </template>
      <template #command-line>
        <CommandLine
          ref="commandLine"
          :mode="props.mode"
          :prompt="props.prompt"
          :history="props.commandHistory"
          :connected="props.connected"
          :mutations-locked="props.mutationsLocked"
          :in-flight="props.inFlight"
          :text-to-html="props.textToHtml"
          @submit="onSubmit"
          @focus-parent="releaseCommandField(true)"
          @open-overlay="onOpenOverlay"
          @focus-lost="() => emit('focus-lost')"
        />
      </template>
    </HudFrame>

    <!-- The header split (design D5): the top-left brand element and the
         top-right meta pill, both anchored in the stage's top band. -->
    <TopBar
      :connected="connected"
      :location-label="locationLabel"
      :time-label="timeLabel"
    />

    <div
      id="elosern-action-live"
      class="elosern-live"
      role="status"
      aria-live="polite"
      aria-atomic="true"
      data-testid="action-live-region"
    ></div>

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
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

/* The stage (HudFrame) fills the shell; anchors are absolutely positioned
   and sized from --dock-h (design D1/D10). */
.elosern-app-shell .elosern-stage {
  position: absolute;
  inset: 0;
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
