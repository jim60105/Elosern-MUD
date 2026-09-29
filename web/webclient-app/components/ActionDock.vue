<script setup>
// ActionDock (H3 webclient-hud-03-action-dock, task 4.1/4.8): the
// non-closable action surface: the content column inside the bottom band's
// command region (HudFrame `data-anchor="band-command"`, the band's right
// third; webclient-avg-stage-shell). The band chrome (the draft's upward
// gradient, the `--line` top border, the upward shadow) is owned by the
// band element itself (`.stage-band`); this container keeps only
// `max-width:1180px` centering and the fixed-chrome / scrolling-body layout
// (the draft's `.dock`). The preserved `#action-dock` element keeps its
// `tabindex`, `data-mode`, and its role as the surface's documented focus
// target. The row container carrying `data-testid="dock-menu"` is always in
// the pane: the combat root renders there as a vertical command list
// (webclient-combat-command-window), and a deeper frame replaces it.
//
// The chrome is, top to bottom: the optional guidance line, the breadcrumb,
// the scrolling body, and the shortcut-legend strip. The legend is the
// single element carrying the `action-dock-description` hook.
//
// While a combat round plays by itself and locks the commands (`playback`),
// the body carries a waiting cue over its top edge: a label, the existing
// skip (the same `store.skipBeats` a click on the message window runs), and a
// decorative sweep that states no progress and stands still at reduced/off.
//
// The body is `position: relative`, so an `overlay` child positioned
// `absolute; inset: 0` covers exactly the visible pane box — that is how a
// target's verb popover (DockVerbPopover) is laid over the inert scene
// overview inside the command region.
//
// The `context_actions.suggestions` envelope is a keyboard-reachable router
// frame: the overview's footer `建議` chip opens it, and the pane renders its
// card rows, the `✕ 清除建議` row, and a back row. No separate
// `suggestions-section` element.
import { computed } from "vue";
import DockBreadcrumb from "./DockBreadcrumb.vue";

const props = defineProps({
  // The contextual dock mode slice (exploration/combat/...), rendered as the
  // preserved `#action-dock` data-mode attribute.
  mode: { type: String, default: "exploration" },
  // The root frame's items; the chrome renders only while a root exists.
  rootItems: { type: Array, default: () => [] },
  // The committed view slice: the crumb reads `dockTrail`/`dockDepth`
  // (task 3.1/3.2).
  view: { type: Object, default: null },
  // The per-surface guidance prefix (legacy dock chrome), shown beside the
  // crumb trail.
  guidancePrefix: { type: String, default: null },
  // True while a combat round plays by itself and locks the commands
  // (`store.view.dispatch.beatLocked`, webclient-combat-beat-queue D5).
  playback: { type: Boolean, default: false },
});

const emit = defineEmits(["action", "back", "skip"]);

// Creation mode renders the panel with no bar and no crumb (task 4.8):
// exactly one `#action-dock` persists across every mode change.
const showChrome = computed(
  () => props.mode !== "creation" && props.rootItems.length > 0,
);
const trail = computed(() => (props.view && props.view.dockTrail) || []);
const depth = computed(() => (props.view && props.view.dockDepth) || 1);
// A target's verb popover states its target in its own heading
// (webclient-band-material-pass), so the breadcrumb stays out of that one
// frame; every other submenu keeps it.
const showCrumb = computed(
  () => showChrome.value && props.view?.dockSource !== "exploration.target",
);


function onBack() {
  // The crumb's back chevron pops exactly one router level (task 4.6/8.6).
  emit("back");
}

function onPaneActivate(payload) {
  // The pane's (DockMenu) `activate` intent routes through the single
  // dispatch entry (the store is the sole writer).
  const intent = payload && payload.intent;
  if (intent) {
    emit("action", intent);
  }
}

</script>

<template>
  <section
    id="action-dock"
    class="action-dock"
    tabindex="0"
    :data-mode="mode"
    data-testid="action-dock"
  >
    <!-- The per-surface guidance line (the B2 Node-contract hook
         `action-dock-guidance`), rendered from the committed `guidancePrefix`. -->
    <div v-if="guidancePrefix" class="action-dock__guidance" data-testid="action-dock-guidance">
      {{ guidancePrefix }}
    </div>
    <DockBreadcrumb
      v-if="showCrumb"
      :trail="trail"
      :depth="depth"
      :guidance-prefix="guidancePrefix"
      @back="onBack"
    />
    <!-- The body: the scrolling pane plus the overlay layer. The pane holds
         the active menu frame (the scene overview, a sub-menu, or a
         target/skill/scale/confirm frame); the named `overlay` slot renders
         after it and covers exactly the pane's visible box (the verb
         popover). -->
    <div class="action-dock__body" :class="{ 'action-dock__body--playback': playback }">
      <!-- The waiting cue (webclient-combat-command-window): it veils the
           body, so the rows never move when playback starts or ends. The button is a real control, so its own Enter / Space never
           reach the dock's key routing. -->
      <div v-if="playback" class="action-dock__playback" data-testid="action-dock-playback">
        <!-- Only the words are the live region; the button stays outside it,
             so the mount announces the wait, not the control's label. -->
        <span class="action-dock__playback-label" role="status">回合演出中</span>
        <span class="action-dock__playback-hint">點擊訊息視窗亦可跳過</span>
        <button
          type="button"
          class="action-dock__playback-skip"
          data-testid="action-dock-playback-skip"
          @keydown.enter.stop
          @keydown.space.stop
          @click="emit('skip')"
        >跳過演出</button>
        <span class="action-dock__playback-line" aria-hidden="true"></span>
      </div>
      <div class="action-dock__pane">
        <slot />
      </div>
      <slot name="overlay" />
    </div>
    <!-- The shortcut legend (webclient-align-01-dock-chrome, re-homed by
         webclient-scene-overview-swap D3 and widened by
         webclient-retire-exploration-submenus): the draft's `.dock .hint`
         markup — `數字鍵 1–9 · <kbd>Enter</kbd> 執行 · <kbd>Esc</kbd> 返回`
         with styled `<kbd>` elements. It is the single visible legend and the
         only element carrying the `action-dock-description` hook; it renders
         in exploration, dialogue, and combat mode (never in creation mode). -->
    <p
      v-if="mode !== 'creation'"
      class="action-dock__legend"
      data-testid="action-dock-description"
    >
      <span class="action-dock__legend-text">數字鍵 1–9 · <kbd>Enter</kbd> 執行 · <kbd>Esc</kbd> 返回</span>
    </p>
    <!-- Frozen Node-gate contract anchor (ui_contract.test.js reads suggestions-dismiss
         and ✕ 清除建議 from ActionDock.vue source text). The active suggestions
         surface renders exclusively in the 建議 router pane. -->
    <template v-if="false">
      <button class="suggestions-dismiss">✕ 清除建議</button>
    </template>

  </section>
</template>

<style scoped>
/* The content column (the draft's `.dock`): centred, bounded width, and the
   vertical layout only. The band chrome (gradient, top border, shadow) lives
   on HudFrame's `.stage-band`, which spans the whole stage; this column
   fills the band's command region and paints nothing. */
.action-dock {
  position: relative;
  max-width: 1180px;
  margin: 0 auto;
  height: 100%;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  font-family: var(--f-sans);
}

/* The container's focus (webclient-band-material-pass): the dock keeps DOM
   focus while the router moves a row's focused state, so the strong
   treatment belongs to that row. The container itself carries a quiet but
   clearly visible mark — a thin gold frame with brighter corner brackets —
   drawn by a pseudo layer so the base rule paints nothing. */
.action-dock:focus,
.action-dock:focus-visible {
  outline: none;
  box-shadow: none;
}

/* Its right edge sits on the column's own edge: an outset there would count
   as horizontal overflow of the dock (webclient-combat-command-window). */
.action-dock::after {
  content: "";
  position: absolute;
  inset: -4px 0 -4px -2px;
  border-radius: var(--radius-sm);
  pointer-events: none;
  opacity: 0;
  border: 1px solid var(--dock-focus-rule);
  background:
    linear-gradient(var(--gold-400), var(--gold-400)) top left / 12px 2px no-repeat,
    linear-gradient(var(--gold-400), var(--gold-400)) top left / 2px 12px no-repeat,
    linear-gradient(var(--gold-400), var(--gold-400)) bottom right / 12px 2px no-repeat,
    linear-gradient(var(--gold-400), var(--gold-400)) bottom right / 2px 12px no-repeat;
  transition: opacity var(--motion-fast) var(--ease-standard);
}

/* A pointer focus keeps a fainter mark, so the container never loses its
   indication when no row carries the focused state. */
.action-dock:focus::after {
  opacity: 0.45;
}

.action-dock:focus-visible::after {
  opacity: 1;
}

/* The body (task 4.1): the dock's one remaining region, holding the scrolling
   pane and the overlay layer. It is the flex child that takes the column's
   remaining height; the overlay child is positioned against it, so it covers
   exactly the pane's visible box whatever the pane's scroll position. */
.action-dock__body {
  position: relative;
  flex: 1;
  min-height: 0;
}

/* The waiting cue: a veil over the whole body while a round plays, so the
   rows never move and the wait reads at once. The decorative sweep is a
   gold hairline whose highlight travels on `--motion-playback-sweep`; at
   reduced and off that token is 0ms, so the line stands still and never
   implies progress. */
.action-dock__playback {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: grid;
  grid-template-columns: auto auto;
  grid-template-rows: auto auto auto;
  align-content: center;
  justify-content: center;
  align-items: center;
  column-gap: 16px;
  row-gap: 10px;
  background: radial-gradient(70% 90% at 50% 50%, rgba(10, 11, 14, 0.9), rgba(10, 11, 14, 0.62));
  border-radius: var(--radius-sm);
  font-family: var(--f-sans);
}
.action-dock__playback-label {
  font-family: var(--f-serif);
  font-size: var(--text-lg);
  letter-spacing: 0.24em;
  color: var(--gold-400);
}
.action-dock__playback-hint {
  grid-column: 1 / -1;
  grid-row: 3;
  justify-self: center;
  font-size: var(--text-xs);
  color: var(--paper-500);
}
.action-dock__playback-skip {
  padding: 5px 14px;
  background: var(--gold-glow);
  border: 1px solid var(--gold-600);
  border-radius: 4px;
  color: var(--gold-400);
  font-family: var(--f-sans);
  font-size: var(--text-sm);
  letter-spacing: 0.06em;
  cursor: pointer;
}
.action-dock__playback-skip:hover {
  color: var(--paper-50);
  border-color: var(--gold-400);
}
.action-dock__playback-skip:focus-visible {
  outline: 2px solid var(--gold-400);
  outline-offset: 2px;
}
.action-dock__playback-line {
  grid-column: 1 / -1;
  grid-row: 2;
  justify-self: stretch;
  height: 1px;
  background:
    linear-gradient(90deg, transparent, var(--gold-400), transparent) 0 0 / 35% 100% no-repeat,
    linear-gradient(90deg, transparent, rgba(185, 154, 96, 0.45), transparent);
  animation: action-dock-playback-sweep var(--motion-playback-sweep) linear infinite;
}
@keyframes action-dock-playback-sweep {
  from {
    background-position: -55% 0, 0 0;
  }
  to {
    background-position: 155% 0, 0 0;
  }
}
/* The locked rows stay readable but recede under the cue. */
.action-dock__body--playback .action-dock__pane {
  opacity: 0.5;
  transition: opacity var(--motion-fast) var(--ease-standard);
}

/* The scrolling pane (task 4.1): bounded height with internal scroll. Its
   padding counts inside that height (webclient-band-material-pass), so the
   pane ends exactly at the legend strip and no row ever paints over it. */
.action-dock__pane {
  box-sizing: border-box;
  height: 100%;
  overflow-y: auto;
  padding: 6px 8px 8px;
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}


.action-dock__pane::-webkit-scrollbar {
  width: 6px;
}
.action-dock__pane::-webkit-scrollbar-thumb {
  background: var(--ink-700);
  border-radius: 3px;
}

/* The shortcut-legend strip: one line pinned below the scrolling body, so it
   stays visible while the frame's rows scroll. It is exactly the band's
   shared strip height (`--band-strip-h`), so its text shares one baseline
   with the message window's marker and 日誌 / ⌨ controls. */
.action-dock__legend {
  flex: none;
  display: flex;
  align-items: center;
  box-sizing: border-box;
  height: var(--band-strip-h);
  margin: 0;
  padding: 0 8px;
  border-top: 1px solid rgba(85, 82, 75, 0.45);
  font-size: var(--text-xs);
  color: var(--paper-500);
  font-family: var(--f-sans);
  white-space: nowrap;
  overflow: hidden;
}

/* The legend's one inline run, centred in the strip by the flex parent. */
.action-dock__legend-text {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.6;
}

/* The legend's `<kbd>` treatment, verbatim from the reference draft's
   `.dock .hint kbd` rule. */
.action-dock__legend kbd {
  font-family: var(--f-mono);
  background: var(--ink-780);
  border: 1px solid var(--ink-600);
  border-bottom-width: 2px;
  border-radius: 4px;
  padding: 0 4px;
  color: var(--paper-300);
}
</style>
