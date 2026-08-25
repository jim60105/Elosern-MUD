import { h } from "vue";
import DockTabBar from "../../components/DockTabBar.vue";

// DockTabBar (H3 webclient-hud-03-action-dock, task 4.9): the dock's fixed
// bar — the root frame's items as tabs (glyph, label, count badge) with the
// seal-red gradient fill on the open/focused tab. At depth 1 it carries the
// listbox role, the single tab stop, `aria-activedescendant`, and
// `data-testid="dock-menu"`.

const TAB_ITEMS_EXPLORATION = [
  { key: "move", label: "移動", enabled: true },
  { key: "look", label: "查看", enabled: true },
  { key: "interact", label: "互動", enabled: true },
  { key: "character", label: "角色狀態", enabled: true },
  { key: "quests", label: "任務", enabled: true },
  { key: "inventory", label: "背包", enabled: true },
  { key: "wait", label: "等待/休息", enabled: true },
  { key: "suggestions", label: "建議", enabled: true },
];

const TAB_ITEMS_COMBAT = [
  { key: "attack", label: "攻擊", enabled: true },
  { key: "skills", label: "技能", enabled: true },
  { key: "items", label: "物品", enabled: false },
  { key: "defend", label: "防禦", enabled: false },
  { key: "flee", label: "逃亡", enabled: true },
  { key: "forfeit", label: "投降", enabled: true },
];

// The committed view slice drives the tab badges (task 4.4): 互動 =
// `exploration.interact.length`, 建議 = `suggestions.cards.length`,
// 技能 = the flattened skill-descriptor count.
function makeView(overrides) {
  const base = {
    panels: {
      exploration: { interact: [{ identity: 5 }, { identity: 6 }], move: [] },
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
      suggestions: { status: "ready", cards: [{}, {}, {}], },
    },
    suggestions: { status: "ready", cards: [{}, {}, {}] },
    dockTrail: ["探索"],
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

// The exploration root with the 互動 / 建議 / 技能 badges (task 4.9).
export const ExplorationRootWithBadges = {
  render: renderTabBar,
  args: {
    items: TAB_ITEMS_EXPLORATION,
    focusedKey: "interact",
    view: makeView(),
    depth: 1,
  },
};

// The combat root (attack/skills/…/forfeit), one tab focused.
export const CombatRoot = {
  render: renderTabBar,
  args: {
    items: TAB_ITEMS_COMBAT,
    focusedKey: "skills",
    view: makeView(),
    depth: 1,
  },
};

// One tab open at depth ≥ 2 (the seal-red gradient fill on the open tab,
// task 4.9).
export const OneTabOpenAtDepth2 = {
  render: renderTabBar,
  args: {
    items: TAB_ITEMS_EXPLORATION,
    focusedKey: "look",
    view: makeView({ dockTrail: ["探索", "查看"], dockDepth: 2 }),
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
