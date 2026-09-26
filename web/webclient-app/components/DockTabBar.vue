<script setup>
// DockTabBar (H3 webclient-hud-03-action-dock, task 4.3): the combat dock's
// fixed bar — the root frame's items rendered as tabs (glyph, label, count
// badge) with the seal-red gradient fill on the open/focused tab. At depth 1
// the tab bar carries the preserved listbox composite: `role="listbox"`, a
// single tab stop, `aria-activedescendant`, and `data-testid="dock-menu"`
// (the active row container at depth 1 — the dock-menu testid moves to the
// pane container at depth ≥ 2).
//
// Only the combat root renders this bar (webclient-scene-overview-swap D3,
// the `tabBar` prop on ActionDock): the exploration and dialogue root is the
// scene overview. The shortcut legend is no longer the bar's trailing hint —
// it is the dock's own strip (ActionDock's `.action-dock__legend`), so it
// shows in every non-creation mode including combat.
//
// Non-current tab click (task 4.5): a click on a different tab pops the
// router back to the root frame, focuses that tab's item, and confirms it
// ("pointer"), bounded by `router.depth()`; a click on the already-open tab
// is a no-op. The store owns the router — this component only emits.
import { computed } from "vue";
import { glyphPath, glyphAttrs } from "./dock-icons.js";
import { badgeCount, badgeVisible } from "./dock-panes.js";

const props = defineProps({
  // The root frame's items (the normalized dock items: key, label,
  // action_id/params, navigation, disabled_reason, cost_text…).
  items: { type: Array, required: true },
  // The focused tab key (the store's committed focus).
  focusedKey: { type: String, default: null },
  // The committed view slice (the badge counts derive from the committed
  // payload only — task 4.4).
  view: { type: Object, default: null },
  // The router's menu depth. The tab bar carries `data-testid="dock-menu"`
  // only while it is the active row container (depth 1); at depth ≥ 2 the
  // pane container takes over the hook (task 1.1).
  depth: { type: Number, default: 1 },
});

const emit = defineEmits(["tab-click"]);

// Badge surface for each root item key (task 4.4): the combat root's 技能
// tab; every other key carries no badge. The bar only renders for the combat
// root (webclient-scene-overview-swap), whose root items are
// attack/skills/items/bag/defend/flee/forfeit.
const BADGE_SURFACES = {
  skills: "skills",
};

const tabs = computed(() =>
  props.items.map((item) => {
    const key = item.key;
    const badge = BADGE_SURFACES[key];
    const count = badge ? badgeCount(badge, props.view) : 0;
    return {
      key,
      label: item.label,
      enabled: item.enabled !== false,
      focused: key === props.focusedKey,
      glyph: glyphPath(key),
      showBadge: badge ? badgeVisible(count) : false,
      badgeCount: count,
    };
  }),
);

// The action tabs (move/look/interact/wait) open a router submenu; they are
// "open" when the current frame (the last `dockTrail` entry) is that tab's
// submenu.
const NAV_TAB_TITLES = {
  move: "移動",
  look: "查看",
  interact: "互動",
  wait: "等待",
};

function isTabOpen(tab) {
  const view = props.view || {};
  const title = NAV_TAB_TITLES[tab.key];
  if (title && view.dockDepth >= 2 && Array.isArray(view.dockTrail) && view.dockTrail.length >= 2) {
    return view.dockTrail[view.dockTrail.length - 1] === title;
  }
  return false;
}

function onTabClick(tab) {
  // A click on a tab whose target is already open is a no-op (task 4.5); a
  // click on a non-current tab requests the router pop-to-root + focus +
  // confirm (task 4.5/8.7: one deliberate activation, no stray `ui_action`).
  if (isTabOpen(tab)) {
    return;
  }
  emit("tab-click", tab.key);
}
</script>

<template>
  <div
    class="dock-tab-bar"
    v-if="tabs.length > 0"
    role="listbox"
    tabindex="0"
    :aria-activedescendant="focusedKey ? `dock-tab-${focusedKey}` : null"
    v-bind="depth === 1 ? { 'data-testid': 'dock-menu' } : {}"
  >
     <button
       v-for="tab in tabs"
       :id="`dock-tab-${tab.key}`"
       type="button"
       role="option"
       :aria-selected="tab.focused"
       class="dock-tab-bar__tab"
       :class="{
         'dock-tab-bar__tab--on': tab.focused,
         'dock-menu-item--focused': tab.focused,
       }"
       :data-item-key="tab.key"
       :disabled="!tab.enabled"
       tabindex="-1"
       @click="onTabClick(tab)"
     >
      <svg
        v-if="tab.glyph"
        class="dock-tab-bar__icon"
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        aria-hidden="true"
      >
         <path :d="tab.glyph" stroke="currentColor" stroke-width="1.9" v-bind="glyphAttrs(tab.key)" />
      </svg>
      <span class="dock-tab-bar__label">{{ tab.label }}</span>
      <span v-if="tab.showBadge" class="dock-tab-bar__badge">{{ tab.badgeCount }}</span>
    </button>
  </div>
</template>

<style scoped>
/* The floating panel's fixed bar (the draft's `.bar` row): a single row of
   tabs, the hint pinned to the trailing edge. */
.dock-tab-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 38px;
  flex: none;
}

.dock-tab-bar:focus {
  outline: 2px solid var(--gold-400);
  outline-offset: 2px;
}

.dock-tab-bar__tab {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  height: 38px;
  padding: 0 12px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 10px;
  color: var(--paper-300);
  font-family: var(--f-sans);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.12s;
}

.dock-tab-bar__tab:hover {
  color: var(--paper-50);
  background: var(--ink-700);
}

/* The open/focused tab carries the seal-red gradient fill (the draft's
   `.tab.on`). */
.dock-tab-bar__tab--on {
  background: var(--gold-glow);
  border-color: var(--gold-400);
  color: var(--gold-400);
}

.dock-tab-bar__tab--on .dock-tab-bar__icon {
  color: var(--gold-400);
}

.dock-tab-bar__tab[disabled] {
  opacity: 0.5;
  cursor: default;
}

.dock-tab-bar__icon {
  flex: none;
  color: var(--gold-400);
}

.dock-tab-bar__badge {
  position: absolute;
  top: -5px;
  right: -5px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  display: grid;
  place-items: center;
  background: var(--seal-500);
  border-radius: 99px;
  font-family: var(--f-mono);
  font-size: 10px;
  color: #fff;
}

</style>
