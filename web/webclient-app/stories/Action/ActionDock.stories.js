import { h } from "vue";
import ActionDock from "../../components/ActionDock.vue";
import DockMenu from "../../components/DockMenu.vue";
import DockVerbPopover from "../../components/DockVerbPopover.vue";
import SceneOverview from "../../components/SceneOverview.vue";
import CombatMenu from "../../lib/combat_menu.js";
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
// prefix, rendered on its own line and by the breadcrumb), rootItems, view
// (the committed slice), and playback (a combat round playing by itself: the
// waiting cue with its skip). Slots: default (the active frame's rows — the
// scene overview, a submenu, or a combat frame's command list) and overlay (a
// target's verb popover card). Events: action (the exact OOB action intent
// for a row activation), back, skip.

// The exploration root's scene overview, from the shared derived-shape helper
// (the same `overviewMenu` the live resolver returns).
const OVERVIEW_PANEL = explorationPanelFixture({
  exits: [
    { label: "北", destination: "room:901" },
    { label: "東", destination: "room:902" },
  ],
  targets: [
    { identity: 11, name: "葛里安‧衛登", affordances: [AFFORDANCES.talk, AFFORDANCES.trade] },
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
      h("div", { style: "padding: 8px; font-family: var(--f-mono); color: var(--paper-500); font-size: 16px;" },
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
      h("div", { style: "padding: 8px; font-family: var(--f-mono); color: var(--paper-500); font-size: 16px;" },
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
      h("div", { style: "padding: 8px; font-family: var(--f-mono); color: var(--paper-500); font-size: 16px;" },
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
    focusedKey: "exit-0",
  },
};

export const VerbPopoverOverOverview = {
  render: renderPopover,
  args: {
    mode: "exploration",
    guidancePrefix: "場景",
    rootItems: [],
    focusedKey: "talk-scripted",
  },
};

// The combat command window (webclient-combat-command-window): the real
// resolver's root and category rows, normalized to the DockMenu contract the
// live dock passes (`command`, the committed `count`, the local copy, the
// disabled reason), inside a box the size of the command region at the
// 1451x790 reference (484×220).
const COMBAT_SKILL_COUNT = 5;
const commandItems = (items) =>
  items.map((item) => ({
    key: item.key,
    label: item.label,
    enabled: item.enabled !== false,
    command: true,
    ...(item.actionId ? { action_id: item.actionId, params: item.payload || {} } : { navigation: true, surface: item.key }),
    ...(item.description ? { description: item.description } : {}),
    ...(item.disabledReason ? { disabled_reason: { ...item.disabledReason } } : {}),
    ...(item.key === "skills" ? { count: COMBAT_SKILL_COUNT } : {}),
    ...(item.skillCount ? { count: item.skillCount } : {}),
  }));
const COMBAT_ROOT = commandItems(CombatMenu.rootItems({ session: { state: "ready" } }));
const COMBAT_CATEGORIES = commandItems(
  CombatMenu.categoryItems({
    skills: [
      { label: "武技", groups: [{ skills: [{}, {}] }] },
      { label: "元素魔法", groups: [{ skills: [{}] }, { skills: [{}] }] },
      { label: "神聖術", groups: [{ skills: [{}] }] },
    ],
  }),
);

const renderCommandWindow = ({ items, focusedKey, crumb, ...args }) => ({
  render: () =>
    h(
      "div",
      {
        style:
          "width: 484px; height: 220px; box-sizing: border-box; padding: 10px 14px 0; " +
          "background: linear-gradient(180deg, #16161a, #0c0d10); border-top: 1px solid rgba(185,154,96,.45);",
      },
      [
        h(ActionDock, { mode: "combat", rootItems: COMBAT_ROOT, view: { dockTrail: crumb, dockDepth: crumb.length }, ...args }, {
          default: () => [
            h("div", { class: "dock-pane-host dock-pane-host--bounded", style: "display:flex;gap:12px;flex:1;min-height:0;align-items:stretch;" }, [
              h(DockMenu, { items, focusedKey, idPrefix: "combat-row", detailTestId: "combat-detail", depth: crumb.length }),
            ]),
          ],
        }),
      ],
    ),
});

// The root: one vertical column — glyph, label, the neutral 技能 count — with
// the highlighted command's local explanation beside it.
export const CombatDock = {
  render: renderCommandWindow,
  args: { items: COMBAT_ROOT, focusedKey: "attack", crumb: ["戰鬥"] },
};

// A disabled command keeps its focus and shows its reason in the detail.
export const CombatDisabledCommand = {
  render: renderCommandWindow,
  args: { items: COMBAT_ROOT, focusedKey: "defend", crumb: ["戰鬥"] },
};

// The skill categories replace the root list: each row with its own count.
export const CombatCategories = {
  render: renderCommandWindow,
  args: { items: COMBAT_CATEGORIES, focusedKey: "skill-cat-1", crumb: ["戰鬥", "技能"] },
};

// A round playing by itself: the waiting cue overlays the list's top edge
// with the existing skip; the sweep stands still at reduced and off.
export const CombatPlayback = {
  render: renderCommandWindow,
  args: { items: COMBAT_ROOT, focusedKey: "attack", crumb: ["戰鬥"], playback: true },
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

