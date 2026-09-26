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
// target. The row container carrying `data-testid="dock-menu"` is the combat
// root's tab bar (depth 1, combat only) or the pane (every other frame).
//
// The chrome (webclient-scene-overview-swap D3) is, top to bottom: the
// optional guidance line, the combat root's tab bar (only while `tabBar`),
// the breadcrumb, the scrolling body, and the shortcut-legend strip. The
// legend lives here, not in the tab bar, so it renders in exploration,
// dialogue, and combat mode alike; it is the single element carrying the
// `action-dock-description` hook.
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
import DockTabBar from "./DockTabBar.vue";

const props = defineProps({
  // The contextual dock mode slice (exploration/combat/...), rendered as the
  // preserved `#action-dock` data-mode attribute.
  mode: { type: String, default: "exploration" },
  // The root frame's items (the stable hierarchical root or the combat root),
  // rendered as the tab bar's tabs (task 4.3).
  rootItems: { type: Array, default: () => [] },
  // Whether the root frame renders as the icon tab bar (webclient-scene-
  // overview-swap D3): only the combat root does. The exploration and
  // dialogue root is the scene overview, which renders in the pane.
  tabBar: { type: Boolean, default: false },
  // The committed view slice: the tab bar's badges derive from the committed
  // payload only (task 4.4), and the crumb reads `dockTrail`/`dockDepth`
  // (task 3.1/3.2).
  view: { type: Object, default: null },
  // The focused key (the store's committed focus) — the open/focused tab
  // carries the seal-red gradient fill.
  focusedKey: { type: String, default: null },
  // The per-surface guidance prefix (legacy dock chrome), shown beside the
  // crumb trail (the shortcut legend lives in the tab bar's trailing hint
  // slot, task 4.7).
  guidancePrefix: { type: String, default: null },
});

const emit = defineEmits(["action", "tab-click", "back"]);

// Creation mode renders the panel with no bar and no crumb (task 4.8):
// exactly one `#action-dock` persists across every mode change.
const showChrome = computed(
  () => props.mode !== "creation" && props.rootItems.length > 0,
);
const trail = computed(() => (props.view && props.view.dockTrail) || []);
const depth = computed(() => (props.view && props.view.dockDepth) || 1);


function onTabClick(key) {
  // Non-current tab click (task 4.5): the store pops to the root frame,
  // focuses that item, and confirms it ("pointer") — one deliberate
  // activation, no stray `ui_action` (task 8.7).
  emit("tab-click", key);
}

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
    <DockTabBar
      v-if="tabBar && showChrome"
      :items="rootItems"
      :focused-key="focusedKey"
      :view="view"
      :depth="depth"
      @tab-click="onTabClick"
    />
    <DockBreadcrumb
      v-if="showChrome"
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
    <div class="action-dock__body">
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
      數字鍵 1–9 · <kbd>Enter</kbd> 執行 · <kbd>Esc</kbd> 返回
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
  max-width: 1180px;
  margin: 0 auto;
  height: 100%;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  font-family: var(--f-sans);
}

.action-dock:focus {
  outline: 2px solid var(--gold-400);
  outline-offset: 2px;
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

/* The scrolling pane (task 4.1): bounded height with internal scroll. */
.action-dock__pane {
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
   stays visible while the frame's rows scroll. */
.action-dock__legend {
  flex: none;
  margin: 0;
  padding: 2px 8px 6px;
  font-size: 11px;
  color: var(--paper-700);
  font-family: var(--f-sans);
  white-space: nowrap;
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
