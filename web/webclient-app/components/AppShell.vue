<script setup>
// AppShell (H1 contextual HUD, webclient-hud-01-shell-and-scene): the
// full-bleed cinematic stage (design D1). `HudFrame` is a
// `position:relative; overflow:hidden` stage with named anchors: the place
// card (`place`, holding PlaceCard — location and world time,
// webclient-avg-place-card-top-bar design D3), the island anchors `vitals`
// and `map` (webclient-avg-stage-hud-anchors design D1), the portrait
// anchors (`actor-left`,
// `actor-right`), the fixed-height bottom band's message and command
// regions (`band-message` holds the paged message window and the `[日誌] [⌨]`
// control strip, `band-command` the action dock), and the `command-line` row
// docked on the message region (webclient-avg-stage-shell design D1/D3/D6;
// webclient-message-window-swap design D1).
//
// Mode gating (design D2): the committed mode renders on the stage root as
// `data-elosern-mode`; surface visibility is CSS-only `display:none`, so
// hidden surfaces leave the accessibility tree and the tab order.
//
// Preserved DOM contract (design D6): `#action-dock` (with `data-mode`,
// `tabindex` and the listbox composite role, rendered by the dock),
// `#elosern-action-live`, `#elosern-offline-overlay`, `#inputfield`
// (inside the command line), and the
// `action-*` / `target-*` item keys all remain.
//
// Shell-owned view behavior (H5, webclient-hud-05-overlays-and-command-line;
// webclient-collapsible-command-line design D1/D2/D5/D7):
// the command line is collapsed by default (`commandLineExpanded = false`).
// `/` outside an editable control, the ⌨ toggle in `#band-message`, or the
// free-form dialogue borrow expands the line and focuses `#inputfield` after
// the DOM update (no literal slash). Escape from the field or an accepted
// send restores focus to `#action-dock` and collapses the line (design D3's
// ladder: open overlay → open drawer → focused command field → dock menu
// level). The mount retires the replaced text fallback (hidden, not removed).
// A mode change that hides the surface holding focus moves focus to the
// action dock *before* the CSS hides it (design D2; the side-effect-free
// `restoreDockFocus` path — no second focus path), and entering creation mode
// collapses the command line.
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import ConnectOverlay from "./ConnectOverlay.vue";
import CommandLine from "./CommandLine.vue";
import HudFrame from "./HudFrame.vue";
import MessageWindow from "./MessageWindow.vue";
import PlaceCard from "./PlaceCard.vue";
import TopBar from "./TopBar.vue";
import { retireReplacedFallback } from "../fallback.js";

const props = defineProps({
  // The contextual mode slice (the store's committed mode: exploration /
  // combat / creation). Rendered on the stage root as data-elosern-mode.
  mode: { type: String, default: "exploration" },
  connected: { type: Boolean, default: false },
  // The store's resolved location and world-time labels, stated only by the
  // place card (null renders its placeholders).
  locationLabel: { type: String, default: null },
  timeLabel: { type: String, default: null },
  narrative: { type: Array, default: () => [] },
  // The store's dispatch-time response marks (`store.responseMarks`),
  // forwarded to MessageWindow so silent actions segment responses.
  responseMarks: { type: Array, default: () => [] },
  // The dialogue view model (webclient-align-08-dialogue-surface): forwarded
  // verbatim to the message window's dialogue variant (null outside the
  // available dialogue window).
  dialogue: { type: Object, default: null },
  // The committed `art` panel — the dialogue variant's portrait catalog source.
  artPanel: { type: Object, default: null },
  // The client-local prose scale (`store.view.fontScale`), forwarded to
  // MessageWindow so a scale change re-measures pages.
  fontScale: { type: Number, default: 1 },
  // The reading preferences (webclient-typewriter-reading-prefs):
  // `store.view.textSpeed`, `store.view.autoAdvance`, and the reduced-motion
  // override `store.view.reducedMotion`, forwarded to MessageWindow.
  textSpeed: { type: String, default: "normal" },
  autoAdvance: { type: Boolean, default: false },
  reducedMotion: { type: [String, null], default: null },
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
  // Vitals island visibility derived client-side (design D1/D2/D3).
  // Focus is rescued before the island hides with display:none.
  vitalsVisible: { type: Boolean, default: true },
  // The client-local text-to-HTML narrative preference (H5): forwarded to
  // the command line's prompt line — when off, the prompt renders as literal
  // text (the preference chooses whether the markup pipeline runs, never
  // what it permits).
  textToHtml: { type: Boolean, default: true },
  // The action client's in-flight mutation flag (H5, webclient-input-narrative):
  // forwarded to the command line so a send blocked by an in-flight mutation
  // keeps the typed speech in the field.
  inFlight: { type: Boolean, default: false },
  // Extra Tab-completion candidates (webclient-align-02-quickbar-shortcuts):
  // the committed exploration panel's exit labels and interact-target display
  // names, forwarded untouched to the command line.
  completionCandidates: { type: Array, default: () => [] },
  // MC5 (multichar-05-topbar-switcher-ui): committed account roster read model
  rosterAvailable: { type: Boolean, default: false },
  rosterCharacters: { type: Array, default: () => [] },
  rosterCanCreate: { type: Boolean, default: false },
  rosterSwitchLocked: { type: Boolean, default: false },
  rosterLockReason: { type: String, default: null },
  epoch: { type: [Number, String], default: null },
  possessionBanner: { type: Object, default: null },
});

const emit = defineEmits([
  "submit-command",
  "open-full-log",
  "focus-lost",
  "dialogue-pick",
  "dialogue-freeform",
  "dialogue-leave",
  "switch-character",
  "create-character",
]);

const commandLine = ref(null);
const commandLineExpanded = ref(false);

// The open-surface registry (design D9): AppClient computes the set of open
// surfaces (full-log, creation, and H4's `hudDrawer`). Expanding the command
// line does not recess the stage, so the registry passes through unchanged.
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

// The shell's single command-line expand-and-focus API
// (webclient-collapsible-command-line design D2): `/`, the ⌨ toggle, and the
// dock's free-form borrow all route through `focusCommandField`. Render the
// row first (`commandLineExpanded = true`), then focus `#inputfield` after
// the DOM update so focus never lands on a `display:none` field. Ignored in
// creation mode so returning from creation starts collapsed (design D7).
async function focusCommandField() {
  if (props.mode === "creation") {
    return;
  }
  commandLineExpanded.value = true;
  await nextTick();
  commandLine.value?.focusField();
}

// Collapse path (design D2): Escape from the focused field (`focus-parent`),
// an accepted send (`sent`), and the store's `drawerCloseRequest` watcher
// restore focus to `#action-dock` first (so `blur` fires `focus-lost` and
// releases any borrow) and then collapse the command line.
function releaseCommandField(restoreFocus) {
  if (restoreFocus) {
    restoreDockFocus();
  }
  commandLineExpanded.value = false;
}

function onToggleCommandLine() {
  if (commandLineExpanded.value) {
    commandLineExpanded.value = false;
    return;
  }
  focusCommandField();
}

function onSubmit(text) {
  // One deliberate send through the single dispatch entry (the store routes
  // it at C1; the transport carries ordinary text, never ui_action).
  emit("submit-command", text);
}

// Shell-wide key claims (H5, design D2/D3): outside any editable control,
// `/` expands the command line and moves focus into the field — the claim is
// unconditional for key repeat (a repeated `/` still prevents a literal
// slash and focuses the field, idempotently). Escape is NOT claimed here: the
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
    return;
  }
}

// A mode change that hides the surface holding focus moves focus to the
// action dock BEFORE the CSS hides the surface (design D2/D10): the
// `display:none` gate runs when the `data-elosern-mode` attribute updates,
// so the rescue must happen in the pre-update phase of the watcher.
const HIDDEN_BY_MODE = {
  creation: "[data-anchor='place'], [data-anchor='band-message'], [data-anchor='vitals'], [data-anchor='map'], [data-anchor='command-line']",
  combat: ".local-map",
  exploration: "",
  // webclient-align-08-dialogue-surface: dialogue keeps the whole cockpit
  // visible (the matrix's dialogue column). Only the objective line is
  // hidden there (and in combat), and it has no tab stop
  // (webclient-avg-stage-hud-anchors design D2), so a mode flip into/out of
  // dialogue never strands focus.
  dialogue: "",
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
    // Entering creation collapses the command line after the pre-hide focus
    // rescue so returning to exploration starts collapsed (design D7).
    if (nextMode === "creation") {
      commandLineExpanded.value = false;
    }
  },
);

// Pre-flush focus rescue for data-driven vitals island hide (design D3):
// when the island hides outside combat (all vitals full and conditions cleared),
// any focus held inside the island is restored to the action dock before display:none.
watch(
  () => props.vitalsVisible,
  (nextVisible, prevVisible) => {
    if (prevVisible && !nextVisible) {
      const active = document.activeElement;
      if (active && active.closest && active.closest('[data-testid="status-panel"]')) {
        restoreDockFocus();
      }
    }
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
      :command-line-expanded="commandLineExpanded"
    >
      <template #backdrop>
        <slot name="backdrop" />
      </template>
      <template #place>
        <PlaceCard :location-label="locationLabel" :time-label="timeLabel" />
      </template>
      <template #vitals>
        <slot name="vitals" />
      </template>
      <template #map>
        <slot name="map" />
      </template>
      <template #actor-left>
        <slot name="actor-left" />
      </template>
      <template #actor-right>
        <slot name="actor-right" />
      </template>
      <template #band-message>
        <MessageWindow
          :lines="props.narrative"
          :marks="props.responseMarks"
          :mode="props.mode"
          :dialogue="props.dialogue"
          :art-panel="props.artPanel"
          :font-scale="props.fontScale"
          :text-speed="props.textSpeed"
          :auto-advance="props.autoAdvance"
          :reduced-motion="props.reducedMotion"
          :held="props.openSurfaces.length > 0"
          @dialogue-pick="(pick) => emit('dialogue-pick', pick)"
          @dialogue-freeform="() => emit('dialogue-freeform')"
          @dialogue-leave="() => emit('dialogue-leave')"
          @open-full-log="() => emit('open-full-log')"
        />
        <button
          type="button"
          class="message-log-open"
          data-testid="message-log-open"
          aria-label="完整日誌"
          title="完整日誌"
          @click="emit('open-full-log')"
          @keydown.enter.stop
          @keydown.space.stop
        >日誌</button>
        <button
          type="button"
          class="command-line-toggle"
          data-testid="command-line-toggle"
          aria-label="指令列"
          title="指令列 (/)"
          aria-controls="command-line-bar"
          :aria-expanded="commandLineExpanded ? 'true' : 'false'"
          @click="onToggleCommandLine"
          @keydown.enter.stop
          @keydown.space.stop
        >⌨</button>
      </template>
      <template #band-command>
        <slot name="action-dock" />
      </template>
      <template #command-line>
        <CommandLine
          ref="commandLine"
          :prompt="props.prompt"
          :history="props.commandHistory"
          :connected="props.connected"
          :mutations-locked="props.mutationsLocked"
          :in-flight="props.inFlight"
          :text-to-html="props.textToHtml"
          :completion-candidates="props.completionCandidates"
          @submit="onSubmit"
          @sent="releaseCommandField(true)"
          @focus-parent="releaseCommandField(true)"
          @focus-lost="() => emit('focus-lost')"
        />
      </template>
    </HudFrame>

    <!-- The 48px top band (design D5; webclient-avg-place-card-top-bar D1):
         the top-left brand element, the navigation row, and the top-right
         switcher and connection pill. -->
    <slot name="navigation" />
    <TopBar
      :connected="connected"
      :roster-available="rosterAvailable"
      :roster-characters="rosterCharacters"
      :roster-can-create="rosterCanCreate"
      :roster-switch-locked="rosterSwitchLocked"
      :roster-lock-reason="rosterLockReason"
      :locked="mutationsLocked || !connected"
      :epoch="epoch"
      :possession-banner="possessionBanner"
      @switch-character="emit('switch-character', $event)"
      @create-character="emit('create-character')"
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

/* The stage (HudFrame) fills the shell; its anchors are positioned from the
   fixed band-height token (webclient-avg-stage-shell design D1/D2). */
.elosern-app-shell .elosern-stage {
  position: absolute;
  inset: 0;
}

/* Control-strip layout coupling in #band-message (design §5.1 / C6c D1):
   - .command-line-toggle (⌨): right: 22px, width: 30px (occupies 22..52px)
   - .message-log-open (日誌): right: 58px, height: 30px (occupies 58..102px)
   - .message-window__marker: right: 104px (MessageWindow.vue) */
.elosern-app-shell .message-log-open {
  position: absolute;
  right: 58px;
  bottom: 18px;
  height: 30px;
  z-index: 1;
  box-sizing: border-box;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--ink-780);
  border: 1px solid var(--ink-600);
  border-radius: 99px;
  color: var(--paper-300);
  font: 12px/1 var(--f-sans);
  letter-spacing: 0;
  cursor: pointer;
}

.elosern-app-shell .message-log-open:hover {
  border-color: var(--gold-500);
  color: var(--paper-50);
}

.elosern-app-shell .command-line-toggle {
  position: absolute;
  right: 22px;
  bottom: 18px;
  width: 30px;
  height: 30px;
  z-index: 1;
  box-sizing: border-box;
  padding: 0;
  display: grid;
  place-items: center;
  border: var(--line);
  border-radius: var(--radius-sm);
  background: var(--panel-solid);
  color: var(--paper-300);
  font: 14px/1 var(--f-mono);
  cursor: pointer;
}

.elosern-app-shell .command-line-toggle:hover,
.elosern-app-shell .command-line-toggle[aria-expanded="true"] {
  color: var(--gold-400);
  border-color: var(--gold-500);
  background: var(--ink-780);
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
  z-index: var(--z-offline);
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
