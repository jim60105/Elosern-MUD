import { h } from "vue";
import ActionDock from "../../components/ActionDock.vue";
import DockMenu from "../../components/DockMenu.vue";
import ExitCompass from "../../components/ExitCompass.vue";
import ExplorationReadout from "../../components/ExplorationReadout.vue";
import { idleReadout } from "../../components/exploration-readout.js";
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
  compassArgs,
} from "../fixtures/scene_overview.js";
import { localMapAround } from "../fixtures/local_map.js";

// ActionDock: the non-closable bottom action surface. Props: mode (the
// preserved #action-dock data-mode), guidancePrefix (per-surface guidance
// prefix, rendered on its own line and by the breadcrumb), rootItems, view
// (the committed slice), and playback (a combat round playing by itself: the
// waiting cue with its skip). Slots: default (the active frame's rows — the
// exploration root pane, or a combat frame's command list) and overlay (a
// layer over the pane's visible box). Events: action (the exact OOB action intent
// for a row activation), back, skip.

// The exploration root pane (exploration-room-actions design D2), from the
// shared derived-shape helper: the exit compass (the same exit rows the live
// resolver returns) beside a right column holding the 建議 pill over the
// shared readout. The room's other actions are the place card's.
const OVERVIEW_PANEL = explorationPanelFixture({
  exits: [
    { ref: "n", label: "北", destination: "town:gate:0:1" },
    { ref: "e", label: "東", destination: "town:gate:1:0" },
  ],
  targets: [
    { identity: 11, name: "葛里安‧衛登", affordances: [AFFORDANCES.talk, AFFORDANCES.trade] },
  ],
  objects: [{ identity: 31, name: "任務板" }],
});

const OVERVIEW_MAP = localMapAround({
  layer: "grid",
  current: ["town:gate:0:0", "城門廣場", 0, 0],
  neighbours: [
    ["town:gate:0:1", "北岸大道", 0, 1],
    ["town:gate:1:0", "公會街", 1, 0],
  ],
});

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

// The exploration root: the compass, the 建議 pill, and the readout in the
// pane; no tab bar, chip row, or legend strip.
const renderOverview = ({ pillCount, ...args }) => {
  const { localMapModel, ...compass } = compassArgs(OVERVIEW_PANEL, OVERVIEW_MAP);
  return {
    render: () =>
      h("div", { style: "border: 1px solid var(--ink-700); border-radius: 12px; overflow: hidden; height: calc(240px * var(--ui-scale)); width: calc(484px * var(--ui-scale));" }, [
        h(ActionDock, args, {
          default: () => [
            h("div", { class: "dock-pane-host dock-pane-host--exploration" }, [
              h("div", { class: "exploration-root", "data-testid": "exploration-root" }, [
                h("div", { class: "exploration-root__compass" }, [h(ExitCompass, { ...compass, active: true })]),
                h("div", { class: "exploration-root__side" }, [
                  h("button", { type: "button", class: "exploration-pill", "data-testid": "suggestions-pill" }, [
                    h("span", { class: "exploration-pill__label" }, "建議"),
                    pillCount > 0 ? h("b", { class: "exploration-pill__count" }, ` ${pillCount}`) : null,
                  ]),
                  h(ExplorationReadout, { class: "exploration-root__readout", ...idleReadout(compass.targets.cycle.length, 1) }),
                ]),
              ]),
            ]),
          ],
        }),
      ]),
  };
};

export default {
  title: "Action/ActionDock",
  component: ActionDock,
};

export const ExplorationRoot = {
  render: renderOverview,
  args: {
    mode: "exploration",
    rootItems: [],
    tabStop: false,
    pillCount: 4,
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

