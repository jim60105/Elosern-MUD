import { h } from "vue";
import ActionDock from "../../components/ActionDock.vue";
import DockMenu from "../../components/DockMenu.vue";
import DockVerbPopover from "../../components/DockVerbPopover.vue";
import SceneOverview from "../../components/SceneOverview.vue";
import {
  EXPLORATION_AFFORDANCES_SAMPLE,
  SUGGESTIONS_DEGRADED_EMPTY_SAMPLE,
  SUGGESTIONS_GENERATING_SAMPLE,
  SUGGESTIONS_READY_SAMPLE,
  SUGGESTIONS_UNAVAILABLE_SAMPLE,
} from "../fixtures.js";
import {
  AFFORDANCES,
  explorationPanelFixture,
  localMapFixture,
  overviewArgs,
  verbArgs,
} from "../fixtures/scene_overview.js";

// ActionDock: the non-closable bottom action surface. Props: mode (the
// preserved #action-dock data-mode), guidancePrefix (per-surface guidance
// prefix, rendered on its own line and by the breadcrumb), rootItems and
// tabBar (the combat root's tab bar; the exploration root is the scene
// overview, so it passes no bar), view (the committed slice), focusedKey.
// Slots: default (the active frame's rows — the scene overview, a submenu, or
// a combat frame) and overlay (a target's verb popover card). Event: action
// (the exact OOB action intent for a row activation).

// The exploration root's scene overview, from the shared derived-shape helper
// (the same `overviewMenu` the live resolver returns).
const OVERVIEW_PANEL = explorationPanelFixture({
  exits: [
    { label: "北", destination: "room:901" },
    { label: "東", destination: "room:902" },
  ],
  targets: [
    { identity: 11, name: "葛里安·衛登", affordances: [AFFORDANCES.talk, AFFORDANCES.trade] },
  ],
  objects: [{ identity: 31, name: "任務板" }],
});

const OVERVIEW_MAP = localMapFixture([
  ["room:901", "北岸大道"],
  ["room:902", "公會櫃檯"],
]);

const renderDock = (args) => ({
  render: () =>
    h("div", { style: "border: 1px solid var(--ink-700); border-radius: 12px; overflow: hidden;" }, [
      h("div", { style: "padding: 8px; font-family: var(--f-mono); color: var(--paper-500); font-size: 13px;" },
        "（上方為敘事區域）"),
      h(ActionDock, args, {
        default: () => [
          h(DockMenu, {
            items: EXPLORATION_AFFORDANCES_SAMPLE,
            focusedKey: "action-explore.move",
            idPrefix: "dock-row",
          }),
        ],
      }),
    ]),
});

// The exploration root: the scene overview in the pane, no tab bar, and the
// dock's own legend strip below the scrolling body.
const renderOverview = (args) => ({
  render: () =>
    h("div", { style: "border: 1px solid var(--ink-700); border-radius: 12px; overflow: hidden;" }, [
      h("div", { style: "padding: 8px; font-family: var(--f-mono); color: var(--paper-500); font-size: 13px;" },
        "（上方為敘事區域）"),
      h(ActionDock, args, {
        default: () => [
          h(SceneOverview, {
            ...overviewArgs(OVERVIEW_PANEL, {
              currentNode: "room:900",
              localMap: OVERVIEW_MAP,
              focusedKey: "exit-0",
            }),
          }),
        ],
      }),
    ]),
});

// A target's verb popover: the overview stays rendered (inert) in the pane and
// the popover's card renders in the dock's overlay slot, over the pane box.
const renderPopover = (args) => ({
  render: () =>
    h("div", { style: "border: 1px solid var(--ink-700); border-radius: 12px; overflow: hidden;" }, [
      h("div", { style: "padding: 8px; font-family: var(--f-mono); color: var(--paper-500); font-size: 13px;" },
        "（上方為敘事區域）"),
      h(ActionDock, args, {
        default: () => [
          h(SceneOverview, {
            ...overviewArgs(OVERVIEW_PANEL, {
              currentNode: "room:900",
              localMap: OVERVIEW_MAP,
              focusedKey: "target-11",
              active: false,
            }),
          }),
        ],
        overlay: () => [
          h(DockVerbPopover, {
            ...verbArgs(OVERVIEW_PANEL, 11, { focusedKey: "talk-scripted" }),
          }),
        ],
      }),
    ]),
});

export default {
  title: "Action/ActionDock",
  component: ActionDock,
};

export const SceneOverviewRoot = {
  render: renderOverview,
  args: {
    mode: "exploration",
    guidancePrefix: "場景",
    rootItems: [],
    tabBar: false,
    focusedKey: "exit-0",
  },
};

export const VerbPopoverOverOverview = {
  render: renderPopover,
  args: {
    mode: "exploration",
    guidancePrefix: "場景",
    rootItems: [],
    tabBar: false,
    focusedKey: "talk-scripted",
  },
};

// The combat root: the tab bar renders (the only mode that has one) and the
// legend strip shows below the pane, exactly as in exploration.
export const CombatDock = {
  render: renderDock,
  args: {
    mode: "combat",
    rootItems: [
      { key: "attack", label: "攻擊", enabled: true },
      { key: "skills", label: "技能", enabled: true },
      { key: "items", label: "物品", enabled: false },
      { key: "flee", label: "逃亡", enabled: true },
    ],
    tabBar: true,
    focusedKey: "attack",
    view: { dockTrail: ["戰鬥"], dockDepth: 1 },
  },
};

export const ExplorationDock = {
  render: renderDock,
  args: {
    mode: "exploration",
    guidancePrefix: "附近動作",
    suggestions: SUGGESTIONS_READY_SAMPLE,
  },
};

export const GeneratingSuggestions = {
  render: renderDock,
  args: {
    mode: "exploration",
    guidancePrefix: "附近動作",
    suggestions: SUGGESTIONS_GENERATING_SAMPLE,
  },
};

export const DegradedEmptySuggestions = {
  render: renderDock,
  args: {
    mode: "exploration",
    guidancePrefix: "附近動作",
    suggestions: SUGGESTIONS_DEGRADED_EMPTY_SAMPLE,
  },
};

export const UnavailableSuggestions = {
  render: renderDock,
  args: {
    mode: "exploration",
    guidancePrefix: "附近動作",
    suggestions: SUGGESTIONS_UNAVAILABLE_SAMPLE,
  },
};

