import { h } from "vue";
import DockTabBar from "../../components/DockTabBar.vue";

// DockTabBar (H3 webclient-hud-03-action-dock, task 4.9): the COMBAT dock's
// fixed bar — the combat root's items as tabs (glyph, label, count badge)
// with the seal-red gradient fill on the open/focused tab. At depth 1 it
// carries the listbox role, the single tab stop, `aria-activedescendant`, and
// `data-testid="dock-menu"`. The exploration and dialogue root renders the
// scene overview instead, so only the combat root is shown here
// (webclient-scene-overview-swap D3). The shortcut legend is the dock's own
// strip (ActionDock's `.action-dock__legend`), not a tab-bar hint.

const TAB_ITEMS_COMBAT = [
  { key: "attack", label: "攻擊", enabled: true },
  { key: "skills", label: "技能", enabled: true },
  { key: "items", label: "物品", enabled: false },
  { key: "defend", label: "防禦", enabled: false },
  { key: "flee", label: "逃亡", enabled: true },
  { key: "forfeit", label: "投降", enabled: true },
];

// The committed view slice drives the tab badges (task 4.4): 技能 = the
// flattened skill-descriptor count. Only the combat root renders this bar, so
// it is the only badge this story exercises.
function makeView(overrides) {
  const base = {
    panels: {
      context_actions: {
        kind: "combat",
        skills: [
          {
            category: "elemental_magic",
            groups: [
              { skills: [{}, {}, {}], label: "火" },
              { skills: [{}, {}], label: "水" },
            ],
          },
        ],
      },
    },
    dockTrail: ["戰鬥"],
    dockDepth: 1,
  };
  return Object.assign(base, overrides || {});
}

const renderTabBar = (args) => ({
  render: () =>
    h("div", { style: "height: 48px; background: var(--ink-900); padding: 4px; border-radius: 8px;" }, [
      h(DockTabBar, args),
    ]),
});

export default {
  title: "Action/DockTabBar",
  component: DockTabBar,
};

// The combat root (attack/skills/…/forfeit), one tab focused, the 技能 badge
// equal to the committed skill count (task 4.9).
export const CombatRoot = {
  render: renderTabBar,
  args: {
    items: TAB_ITEMS_COMBAT,
    focusedKey: "skills",
    view: makeView(),
    depth: 1,
  },
};

// One combat tab open at depth ≥ 2 (the seal-red gradient fill on the open
// tab, task 4.9).
export const OneTabOpenAtDepth2 = {
  render: renderTabBar,
  args: {
    items: TAB_ITEMS_COMBAT,
    focusedKey: "skills",
    view: makeView({ dockTrail: ["戰鬥", "技能"], dockDepth: 2 }),
    depth: 2,
  },
};

// Creation's empty bar (no tabs, task 4.9): the panel renders with no bar
// (task 4.8) — the story shows the empty-state contract.
export const CreationEmptyBar = {
  render: renderTabBar,
  args: {
    items: [],
    focusedKey: null,
    view: makeView(),
    depth: 1,
  },
};
