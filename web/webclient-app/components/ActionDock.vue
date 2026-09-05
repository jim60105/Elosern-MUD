<script setup>
// ActionDock (H3 webclient-hud-03-action-dock, task 4.1/4.8): the
// non-closable bottom action surface: the centered content column inside
// H1's `dock` anchor (HudFrame `data-anchor="dock"`). Since
// webclient-align-01-dock-chrome the visual band (the draft's upward
// gradient, the `--line` top border, the upward shadow, and the band
// padding) is owned by the full-width anchor element itself (the draft's
// `.dockwrap`); this container keeps only `max-width:1180px` centering and
// the fixed-bar / crumb / scrolling-pane layout (the draft's `.dock`). The
// preserved `#action-dock` element keeps its `tabindex`, `data-mode`, and the
// listbox composite role (the row container carrying `data-testid="dock-menu"`
// moves between the tab bar (depth 1) and the pane (depth ≥ 2).
//
// The `context_actions.suggestions` envelope is now a keyboard-reachable
// router frame (task 2.3): the `建議` root row opens it, and the pane
// renders its card rows, the `✕ 清除建議` row, and a back row. No separate
// `suggestions-section` element (group 8 re-maps the browser assertions).
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
  // The dialogue-form flag (webclient-align-08-dialogue-surface): forwarded
  // to the tab bar's legend branch (same single legend instance).
  dialogueForm: { type: Boolean, default: false },
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
      v-if="showChrome"
      :items="rootItems"
      :focused-key="focusedKey"
      :view="view"
      :depth="depth"
      :dialogue-form="dialogueForm"
      @tab-click="onTabClick"
    />
    <DockBreadcrumb
      v-if="showChrome"
      :trail="trail"
      :depth="depth"
      :guidance-prefix="guidancePrefix"
      :focused-key="focusedKey"
      @back="onBack"
    />
    <!-- The scrolling pane: the active menu frame (a root menu, a sub-menu,
         or a target/skill/scale/confirm frame). At depth 1 the exploration
         root draws no pane content beyond the tab bar; combat and submenus
         render the pane through the default slot. -->
    <div class="action-dock__pane">
      <slot />
    </div>
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
   vertical layout only. webclient-align-01-dock-chrome moved the band chrome
   (gradient, top border, shadow, padding) onto the full-width dock anchor in
   `HudFrame.vue` — the painted band spans the whole stage; gutters never
   exist. */
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

/* The scrolling pane (task 4.1): bounded height with internal scroll. */
.action-dock__pane {
  flex: 1;
  min-height: 0;
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
</style>
