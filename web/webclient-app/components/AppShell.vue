<script setup>
// AppShell (H1 contextual HUD, webclient-hud-01-shell-and-scene): the
// full-bleed cinematic stage (design D1). `HudFrame` is a
// `position:absolute; overflow:clip` stage with named anchors: the island
// anchors `vitals` and `map` (webclient-avg-stage-hud-anchors design D1;
// `map` opens with PlaceCard — location and world time,
// place-card-relocation design D2), the portrait
// anchors (`actor-left`,
// `actor-right`), the dialogue `choices` anchor (webclient-dialogue-choices-
// overlay D6), the fixed-height bottom band's message and command
// regions (`band-message` holds the paged message window and the `[日誌] [⌨]`
// control strip, `band-command` the action dock), and the `command-line` row
// docked on the message region (webclient-avg-stage-shell design D1/D3/D6;
// webclient-message-window-swap design D1).
//
// Mode gating (design D2): the committed mode renders on the stage root as
// `data-elosern-mode`; surface visibility is CSS-only `display:none`, so
// hidden surfaces leave the accessibility tree and the tab order. The one
// exception is the command region in dialogue (webclient-mode-transitions
// D1): it is inert from the commit and slides out, then `visibility:
// hidden`.
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
// send restores focus to the mode's focus home (`#action-dock`, or in
// dialogue the choice list while it is shown, else the message page) and
// collapses the line (design D3's
// ladder: open overlay → open drawer → focused command field → dock menu
// level). The mount retires the replaced text fallback (hidden, not removed).
// A mode change that hides the surface holding focus moves focus to the
// incoming mode's focus home *before* the CSS hides it (design D2; the
// side-effect-free `restoreFocusHome` path — no second focus path; entering
// dialogue collapses the command region and re-homes focus on the message
// window, webclient-dialogue-stage-actors D5), and entering creation mode
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
  // verbatim to the message window, whose name plate names the host (null
  // outside the available dialogue window).
  dialogue: { type: Object, default: null },
  // The client-local prose scale (`store.view.fontScale`), forwarded to
  // MessageWindow so a scale change re-measures pages.
  fontScale: { type: Number, default: 1 },
  // The reading preferences (webclient-typewriter-reading-prefs):
  // `store.view.textSpeed`, `store.view.autoAdvance`, and the effective
  // motion level `store.view.motionLevel`, forwarded to MessageWindow.
  textSpeed: { type: String, default: "normal" },
  autoAdvance: { type: Boolean, default: false },
  motionLevel: { type: String, default: "full" },
  // The playing combat round (`store.view.beatPlayback`,
  // webclient-combat-beat-queue), forwarded to MessageWindow: its beat pages,
  // and the queue's own report of a shown beat and of the player ending the
  // round.
  beatPlayback: { type: Object, default: null },
  // The live mode-change signal (webclient-mode-transitions D2, from
  // composables/use-mode-change.js): `modeChange` names the last live
  // transition and is rendered on the stage root; `modeHydrating` is true
  // across a reconnect's null edges, so the name plate appears and goes
  // with no fade there.
  modeChange: { type: String, default: null },
  // The terminal-round hold (`store.view.beatHold`,
  // webclient-combat-beat-choreography D6), forwarded to HudFrame.
  beatHold: { type: Boolean, default: false },
  modeHydrating: { type: Boolean, default: false },
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
  // protocol error locks all graphical mutations). The top bar's switcher
  // locks with it.
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
  // The command line's accept rule (webclient-dialogue-choices-overlay D9):
  // `store.view.commandAccepts`, the same predicate the dispatch path applies
  // to the send the field would make, so a rejected send keeps its text.
  commandAccepts: { type: Boolean, default: false },
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
  "reading-change",
  "beat-shown",
  "beat-skip",
  "switch-character",
  "create-character",
]);

const commandLine = ref(null);
const messageWindow = ref(null);
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

const CHOICE_LIST_SELECTOR = '[data-anchor="choices"] [data-testid="dialogue-choices"]';

function messagePage() {
  return messageWindow.value?.$el?.querySelector?.('[data-testid="message-page"]') ?? null;
}

// Park focus on the message page (webclient-dialogue-choices-overlay D7):
// the choice list calls this before an activation dispatches, so the list's
// removal on the next render never drops focus to the body.
function focusMessagePage() {
  messageWindow.value?.focusHome?.();
}

// The mode's focus home (webclient-dialogue-stage-actors design D5): the
// side-effect-free rescue every return path shares (no drawer-close side
// effects, no `drawer-closed` emit). In every mode but dialogue it is
// `#action-dock`. In dialogue the command region is collapsed and the home
// is the choice list while it is shown, else the message page
// (webclient-dialogue-choices-overlay D7). The page takes focus at once —
// it is always rendered in dialogue — and the list takes it after the next
// render: a return path can run between a dispatch and the render that
// removes the list (an accepted borrowed send), so the list is only trusted
// once that render has happened.
function restoreFocusHome() {
  if (props.mode === "dialogue") {
    focusMessagePage();
    void nextTick(() => {
      const active = document.activeElement;
      const list = document.querySelector(CHOICE_LIST_SELECTOR);
      if (props.mode === "dialogue" && list && (active === messagePage() || focusIsLost(active))) {
        list.focus({ preventScroll: true });
      }
    });
    return;
  }
  // `preventScroll`: leaving dialogue focuses the dock while its region still
  // starts its slide back from beyond the stage's right edge; the focus must
  // never scroll an ancestor towards it (the stage clips, never scrolls).
  const dock = document.getElementById("action-dock");
  if (dock && typeof dock.focus === "function") {
    dock.focus({ preventScroll: true });
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
// restore focus to the mode's focus home first (so `blur` fires `focus-lost` and
// releases any borrow) and then collapse the command line.
function releaseCommandField(restoreFocus) {
  if (restoreFocus) {
    restoreFocusHome();
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
// incoming mode's focus home BEFORE the CSS hides it (design D2/D10): the
// `display:none` gate runs when the `data-elosern-mode` attribute updates,
// so the rescue must happen in the pre-update phase of the watcher (the
// prop is already the new mode; the DOM still shows the old one).
const HIDDEN_BY_MODE = {
  creation: "[data-anchor='band-message'], [data-anchor='vitals'], [data-anchor='map'], [data-anchor='command-line']",
  combat: ".local-map",
  exploration: "",
  // webclient-dialogue-stage-actors (design D4): dialogue collapses the
  // command region together with the dock inside it. (The objective line is
  // hidden too, but carries no tab stop.) Cockpit anchors leave with it.
  dialogue: "[data-anchor='band-command'], [data-anchor='vitals'], [data-anchor='map']",
};

// Focus fell out of the rendered layout: the body, a removed element, or an
// element inside a surface the committed mode hides (`hiddenSelector`), which
// a browser may not have blurred yet.
function focusIsLost(active, hiddenSelector = "") {
  return (
    !active ||
    active === document.body ||
    active === document.documentElement ||
    !active.isConnected ||
    (!!hiddenSelector && typeof active.closest === "function" && !!active.closest(hiddenSelector))
  );
}

watch(
  () => props.mode,
  async (nextMode, prevMode) => {
    const active = document.activeElement;
    if (nextMode === "dialogue" && prevMode !== "dialogue") {
      // Entering dialogue (design D5), in two phases. Pre-flush: focus held in
      // any outgoing anchor moves to the page surface, visible in both
      // variants' layout, so the browser never blurs it to the body. After
      // the flush the dialogue rows exist: the window's focus home takes it.
      // A drawer or the command field that holds focus keeps it.
      const outgoing = active?.closest?.(HIDDEN_BY_MODE.dialogue);
      if (outgoing) {
        focusMessagePage();
      }
      await nextTick();
      const now = document.activeElement;
      if (
        focusIsLost(now) ||
        now?.matches?.('[data-testid="message-page"]') ||
        now?.closest?.(HIDDEN_BY_MODE.dialogue)
      ) {
        restoreFocusHome();
      }
      return;
    }
    const hiddenSelector = HIDDEN_BY_MODE[nextMode] || HIDDEN_BY_MODE.exploration;
    if (active && active.closest && hiddenSelector && active.closest(hiddenSelector)) {
      restoreFocusHome();
    }
    // A creation transition closes the open overlay (the store's syncHudDrawer
    // clears `hudOverlay`); route focus to the action dock so it is never lost
    // into a hidden or unmounted surface (webclient-contextual-hud: "A creation
    // transition closes the overlays ... focus is routed to the action dock").
    if (nextMode === "creation" && active && active.closest && active.closest(".overlay-host")) {
      restoreFocusHome();
    }
    // Entering creation collapses the command line after the pre-hide focus
    // rescue so returning to exploration starts collapsed (design D7).
    if (nextMode === "creation") {
      commandLineExpanded.value = false;
    }
    if (prevMode === "dialogue") {
      // Leaving dialogue (design D5): the choice list is gone after the
      // flush, so focus held in the message region or the `choices` anchor
      // (or already dropped to the body) returns to the dock. The command
      // region cleared `inert` in the same patch and is sliding back in
      // (webclient-mode-transitions D6): an entering element is in reach
      // from its first frame.
      await nextTick();
      const now = document.activeElement;
      if (
        focusIsLost(now, hiddenSelector) ||
        now?.closest?.("[data-anchor='band-message'], [data-anchor='choices']")
      ) {
        restoreFocusHome();
      }
    }
  },
);

// Pre-flush focus rescue for data-driven vitals island hide (design D3):
// when the island hides outside combat (all vitals full and conditions cleared),
// any focus held inside the island is restored to the mode's focus home before
// display:none (the message window in dialogue).
watch(
  () => props.vitalsVisible,
  (nextVisible, prevVisible) => {
    if (prevVisible && !nextVisible) {
      const active = document.activeElement;
      if (active && active.closest && active.closest('[data-testid="status-panel"]')) {
        restoreFocusHome();
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
// the field via `focusCommandField`, a successful borrowed send returns focus
// to the mode's focus home via `releaseCommandField(true)`, and the dock's
// popover-close watcher re-homes focus through `restoreFocusHome`.
defineExpose({ focusCommandField, releaseCommandField, restoreFocusHome, focusMessagePage });
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
      :mode-change="modeChange"
      :beat-hold="beatHold"
      :open-surfaces="frameOpenSurfaces"
      :lowhp="lowHp"
      :command-line-expanded="commandLineExpanded"
    >
      <template #backdrop>
        <slot name="backdrop" />
      </template>
      <template #vitals>
        <slot name="vitals" />
      </template>
      <template #map>
        <PlaceCard :location-label="locationLabel" :time-label="timeLabel" :motion-level="props.motionLevel" />
        <slot name="map" />
      </template>
      <template #actor-left>
        <slot name="actor-left" />
      </template>
      <template #actor-right>
        <slot name="actor-right" />
      </template>
      <template #choices>
        <slot name="choices" />
      </template>
      <template #band-message>
        <MessageWindow
          ref="messageWindow"
          :lines="props.narrative"
          :marks="props.responseMarks"
          :mode="props.mode"
          :dialogue="props.dialogue"
          :font-scale="props.fontScale"
          :text-speed="props.textSpeed"
          :auto-advance="props.autoAdvance"
          :motion-level="props.motionLevel"
          :mode-hydrating="props.modeHydrating"
          :held="props.openSurfaces.length > 0"
          :beat-playback="props.beatPlayback"
          @beat-shown="(index) => emit('beat-shown', index)"
          @beat-skip="() => emit('beat-skip')"
          @reading-change="(complete) => emit('reading-change', complete)"
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
          :accepting="props.commandAccepts"
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
/* `overflow: clip` (like the stage's): the shell clips but is never a scroll
   container, so no focus move or `scrollIntoView` can shift it sideways. */
.elosern-app-shell {
  position: relative;
  box-sizing: border-box;
  height: 100%;
  min-height: 0;
  overflow: clip;
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
   - .message-window__marker: right: 104px (MessageWindow.vue)
   Both buttons are centred in the band's shared control strip
   (`--band-strip-h` above `--band-pad-bottom`), the strip the dock's legend
   also fills, so the two regions' controls share one baseline
   (webclient-band-material-pass). */
.elosern-app-shell .message-log-open {
  position: absolute;
  right: calc(58px * var(--ui-scale));
  bottom: calc(var(--band-pad-bottom) + (var(--band-strip-h) - calc(30px * var(--ui-scale))) / 2);
  height: calc(30px * var(--ui-scale));
  z-index: 1;
  box-sizing: border-box;
  padding: 0 calc(10px * var(--ui-scale));
  display: inline-flex;
  align-items: center;
  justify-content: center;
  /* One control family with ⌨ (webclient-band-material-pass): the same
     ground, rule, and corner radius. */
  background: var(--panel-solid);
  border: var(--line);
  border-radius: var(--radius-sm);
  color: var(--paper-300);
  font: var(--text-xs)/1 var(--f-sans);
  letter-spacing: 0.08em;
  cursor: pointer;
}

.elosern-app-shell .message-log-open:hover {
  border-color: var(--gold-500);
  background: var(--ink-780);
  color: var(--paper-50);
}

.elosern-app-shell .command-line-toggle {
  position: absolute;
  right: calc(22px * var(--ui-scale));
  bottom: calc(var(--band-pad-bottom) + (var(--band-strip-h) - calc(30px * var(--ui-scale))) / 2);
  width: calc(30px * var(--ui-scale));
  height: calc(30px * var(--ui-scale));
  z-index: 1;
  box-sizing: border-box;
  padding: 0;
  display: grid;
  place-items: center;
  border: var(--line);
  border-radius: var(--radius-sm);
  background: var(--panel-solid);
  color: var(--paper-300);
  font: var(--text-md)/1 var(--f-sans);
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
  border-left: calc(3px * var(--ui-scale)) solid var(--seal-500);
  padding-left: calc(8px * var(--ui-scale));
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
  padding: calc(32px * var(--ui-scale));
}

.elosern-app-shell #elosern-offline-overlay[data-visible="true"] {
  display: block;
}

.elosern-app-shell #elosern-offline-overlay .offline-title {
  margin-top: 18vh;
  font-family: var(--f-display);
  font-size: calc(22px * var(--ui-scale));
  font-weight: 600;
  color: var(--seal-400);
}

.elosern-app-shell #elosern-offline-overlay .offline-note {
  margin-top: var(--sp-3);
  color: var(--paper-500);
}
</style>
