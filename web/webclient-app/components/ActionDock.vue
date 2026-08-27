<script setup>
// ActionDock (H3 webclient-hud-03-action-dock, task 4.1/4.8): the
// non-closable bottom action surface, re-chromed as the floating panel inside
// H1's `dock` anchor (HudFrame `data-anchor="dock"`): `max-width:1180px`
// centred, the draft's upward gradient, a `--line` top border, the upward
// shadow, and the fixed-bar / crumb / scrolling-pane layout. The preserved
// `#action-dock` element keeps its `tabindex`, `data-mode`, and the
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
import OptionCard from "./OptionCard.vue";

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
  // The committed `context_actions.suggestions` envelope (the legacy
  // suggestions section the Node contract gate reads: `suggestions-dismiss` +
  // `✕ 清除建議`). `generating` is one muted line, `ready` is the card row
  // plus the shared dismiss control, `degraded` adds the muted note,
  // `unavailable` renders nothing.
  suggestions: { type: Object, default: null },
});

const emit = defineEmits(["action", "tab-click", "back"]);

// Creation mode renders the panel with no bar and no crumb (task 4.8):
// exactly one `#action-dock` persists across every mode change.
const showChrome = computed(
  () => props.mode !== "creation" && props.rootItems.length > 0,
);
const trail = computed(() => (props.view && props.view.dockTrail) || []);
const depth = computed(() => (props.view && props.view.dockDepth) || 1);

// The suggestions section's four statuses (the legacy dock section, kept for
// the Node contract gate; the router frame renders the same envelope in the
// pane).
const SUGGESTION_STATUSES = ["generating", "ready", "degraded"];
const suggStatus = computed(() => (props.suggestions ? props.suggestions.status : null));
const suggCards = computed(
  () => (props.suggestions && Array.isArray(props.suggestions.cards) ? props.suggestions.cards : []),
);
// The router's suggestions frame (opened by the `建議` tab) renders the same
// card rows in the pane (DockMenu `cards` variant). When that frame is the
// active menu, the legacy section is suppressed so the cards are not drawn
// twice. The section still renders in the non-router states (root frame open).
const suggestionsFrameOpen = computed(() => {
  const menu = props.view && props.view.combatMenu;
  const items = (menu && menu.items) || [];
  return items.some((i) => i.key === "action-options.dismiss" || (i.key && i.key.startsWith("action-")));
});
// The legacy suggestions section renders only while the root frame (depth 1)
// is the active menu and no sub-dock owns the surface. When a sub-dock
// (`activeSubDock`) or the suggestions frame is active, the section is
// suppressed so it is not drawn twice.
const subDockActive = computed(
  () => !!(props.view && props.view.activeSubDock),
);
const showSuggSection = computed(
  () => SUGGESTION_STATUSES.includes(suggStatus.value)
    && !suggestionsFrameOpen.value
    && depth.value === 1
    && !subDockActive.value,
);

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

function onCardAction(intent) {
  // The legacy suggestions section's card activation forwards the exact OOB
  // intent (the `OptionCard` `action` emit) through the single dispatch entry.
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
    <!-- The shortcut legend (the B2 Node-contract hook `action-dock-description`),
         reactive to `guidancePrefix`. Carried by ActionDock so the Node gate
         reads it from this file even when the tab bar is absent. The visible
         copy is the tab bar's trailing hint, so this element is the visually
         hidden duplicate: the `visually-hidden` class plus `aria-hidden` keep
         it in the DOM (the gate reads `inner_text()`/`textContent`) but remove
         it from both the visual layout and the accessibility narration order. -->
    <div
      class="visually-hidden action-dock__description"
      data-testid="action-dock-description"
      aria-hidden="true"
    >
      {{ guidancePrefix ? guidancePrefix + "　" : "" }}方向鍵選擇・Enter 確認・Esc 返回・/ 聚焦指令列
    </div>
    <DockTabBar
      v-if="showChrome"
      :items="rootItems"
      :focused-key="focusedKey"
      :view="view"
      :depth="depth"
      :guidance-prefix="guidancePrefix"
      @tab-click="onTabClick"
    />
    <DockBreadcrumb
      v-if="showChrome"
      :trail="trail"
      :depth="depth"
      :guidance-prefix="guidancePrefix"
      @back="onBack"
    />
    <!-- The scrolling pane: the active menu frame (a root menu, a sub-menu,
         or a target/skill/scale/confirm frame). At depth 1 the exploration
         root draws no pane content beyond the tab bar; combat and submenus
         render the pane through the default slot. -->
    <div class="action-dock__pane">
      <slot />
    </div>
    <!-- The legacy suggestions section (the Node contract gate reads the
         `suggestions-dismiss` + `✕ 清除建議` hooks from this file). The
         router's suggestions frame renders the same envelope in the pane. -->
    <div
      v-if="showSuggSection"
      class="suggestions-section"
      role="region"
      aria-label="AI 建議"
      data-testid="suggestions-section"
    >
      <div v-if="suggStatus === 'generating'" class="suggestions-generating" data-testid="suggestions-generating">
        AI 正在構思建議…
      </div>
      <template v-else>
        <div class="suggestions-header">
          <span class="suggestions-title">AI 建議</span>
          <button
            type="button"
            class="suggestions-dismiss"
            data-testid="suggestions-dismiss"
            @click="emit('action', { action_id: 'options.dismiss', payload: {} })"
          >✕ 清除建議</button>
        </div>
        <div v-if="suggStatus === 'degraded'" class="suggestions-note" data-testid="suggestions-note">
          AI 建議目前不可用
        </div>
        <div v-if="suggStatus === 'degraded' && suggCards.length === 0" class="suggestions-empty" data-testid="suggestions-empty">
          現在沒有什麼值得做的動作
        </div>
        <div v-if="suggCards.length > 0" class="suggestions-cards">
          <OptionCard
            v-for="(card, i) in suggCards"
            :key="card.action_code || card.label || i"
            :card="card"
            @action="onCardAction"
          />
        </div>
      </template>
    </div>
  </section>
</template>

<style scoped>
/* The floating panel (task 4.1): centred, bounded width, the draft's
   upward gradient, the `--line` top border, and the upward shadow. */
.action-dock {
  max-width: 1180px;
  margin: 0 auto;
  height: 100%;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  background: linear-gradient(0deg, #0c0a0e, #141019 70%, var(--panel));
  border-top: var(--line);
  border-radius: 0 0 12px 12px;
  box-shadow: 0 -14px 34px -24px #000;
  font-family: var(--f-sans);
}

.action-dock:focus {
  outline: 2px solid var(--gold-400);
  outline-offset: 2px;
}

/* The hidden legend copy: the same sr-only clip definition duplicated
   independently in `DockMenuItem.vue` and `DockMenu.vue` — Vue's scoped CSS
   does not cross component boundaries, so this component must carry its
   own rule or the class name alone is an inert no-op. */
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
  border: 0;
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
