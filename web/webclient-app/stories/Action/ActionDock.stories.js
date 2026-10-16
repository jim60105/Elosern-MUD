import { h } from "vue";
import ActionDock from "../../components/ActionDock.vue";
import DockMenu from "../../components/DockMenu.vue";
import SkillDetailPane from "../../components/SkillDetailPane.vue";
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
// for a row activation), back, skip. `card` presents the dock as the narrow
// combat command card (webclient-combat-command-card-centred): the shared card
// frame, a one-line breadcrumb, the rows over a three-line detail strip, and
// the wrapping legend.

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

// The combat command card (webclient-combat-command-card-centred): the real
// resolver's root and category rows, normalized to the DockMenu contract the
// live dock passes (`command`, the committed `count`, the local copy, the
// disabled reason), in the card the stage stands at its dead centre — a
// 264×400 host (the 1451x790 reference) over a dim stage ground.
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

// The AREA target frame's tokens (the router's `toggle-target` rows, the
// client-local `✓` selection) and the 威力 step's rows, in the shapes the
// live dock normalizes them to.
const AREA_TARGETS = [
  ["灰袍盜賊", 31, true],
  ["盜賊頭目", 32, true],
  ["蒙面刺客", 33, false],
  ["北境巡防隊長", 34, false],
].map(([label, identity, selected]) => ({
  key: `target-${identity}`,
  label,
  enabled: true,
  action_id: "toggle-target",
  params: { identity },
  team: "foes",
  selected,
}));
const FIREBALL_SCALES = [
  { scale: 0.25, label: "1/4", mp_cost: 4 },
  { scale: 0.5, label: "1/2", mp_cost: 7 },
  { scale: 1, label: "1", mp_cost: 14 },
  { scale: 2, label: "2", mp_cost: 28 },
  { scale: 4, label: "4", mp_cost: 56 },
];
const SCALE_ROWS = FIREBALL_SCALES.map((entry) => ({
  key: `scale-${entry.label}`,
  label: `威力×${entry.label}`,
  description: `MP ${entry.mp_cost}`,
  enabled: true,
  action_id: "choose-scale",
  params: { scale: entry.scale },
  scaleChoice: true,
}));
const FIREBALL = {
  key: "fireball",
  label: "火球",
  description: "凝聚火焰魔力，對單一敵人造成魔法傷害。",
  costText: "MP 14",
  targetSpec: "single",
  element: "fire",
  enabled: true,
  disabledReason: null,
};
const MEND_GLOW = {
  key: "mend_glow",
  label: "微光治癒",
  description: "以柔和的水光治癒自己。",
  costText: "MP 11",
  targetSpec: "self",
  element: "water",
  enabled: false,
  disabledReason: { code: "insufficient_mp", message: "魔力不足，無法施展這道治癒之光。" },
};
const WATER_SKILLS = [
  { key: "skill-mend_glow", label: "微光治癒", enabled: false, action_id: "open-skill", params: {}, cost_text: "MP 11", disabled_reason: { ...MEND_GLOW.disabledReason } },
  { key: "skill-tide_ward", label: "潮汐護壁", enabled: true, action_id: "open-skill", params: {}, cost_text: "MP 9" },
];

const renderCommandWindow = ({ items, focusedKey, crumb, skill, scales, ...args }) => ({
  render: () =>
    h(
      "div",
      {
        style:
          "width: 360px; padding: 28px 48px; box-sizing: border-box; " +
          "background: radial-gradient(90% 70% at 50% 30%, #2a1a1f, #0c0b0e 80%);",
      },
      [
        h("div", { style: "width: 264px; height: 400px; display: flex; flex-direction: column;" }, [
          h(ActionDock, { mode: "combat", card: true, rootItems: COMBAT_ROOT, view: { dockTrail: crumb, dockDepth: crumb.length }, ...args }, {
            default: () => [
              h("div", { class: "dock-pane-host dock-pane-host--bounded" }, [
                h(DockMenu, {
                  items,
                  focusedKey,
                  idPrefix: "combat-row",
                  detailTestId: "combat-detail",
                  depth: crumb.length,
                  hideGenericDetail: !!skill,
                }),
                skill ? h(SkillDetailPane, { skill, scales: scales || [], scale: 1, focusKey: focusedKey }) : null,
              ]),
            ],
          }),
        ]),
      ],
    ),
});

// The root: one vertical column — glyph, label, the neutral 技能 count — with
// the highlighted command's explanation in the strip below it.
export const CombatDock = {
  render: renderCommandWindow,
  args: { items: COMBAT_ROOT, focusedKey: "attack", crumb: ["戰鬥"] },
};

// A disabled command keeps its focus and shows its reason in the strip.
export const CombatDisabledCommand = {
  render: renderCommandWindow,
  args: { items: COMBAT_ROOT, focusedKey: "defend", crumb: ["戰鬥"] },
};

// The skill categories replace the root list: each row with its own count.
export const CombatCategories = {
  render: renderCommandWindow,
  args: { items: COMBAT_CATEGORIES, focusedKey: "skill-cat-1", crumb: ["戰鬥", "技能"] },
};

// The AREA target frame: the token grid keeps its two columns in the card.
export const CombatTargets = {
  render: renderCommandWindow,
  args: { items: AREA_TARGETS, focusedKey: "target-33", crumb: ["戰鬥", "技能", "元素魔法", "火風暴", "目標"] },
};

// The 威力 step: one column per scale; the strip states the focused scale's
// cost, the target requirement and the element.
export const CombatMasterScale = {
  render: renderCommandWindow,
  args: { items: SCALE_ROWS, focusedKey: "scale-2", crumb: ["戰鬥", "技能", "元素魔法", "火球", "威力"], skill: FIREBALL, scales: FIREBALL_SCALES },
};

// A disabled skill: the strip states its server-authored reason in place of
// the description.
export const CombatDisabledDetail = {
  render: renderCommandWindow,
  args: { items: WATER_SKILLS, focusedKey: "skill-mend_glow", crumb: ["戰鬥", "技能", "元素魔法", "水"], skill: MEND_GLOW },
};

// A round playing by itself: the waiting cue veils the card's body with the
// existing skip; the sweep stands still at reduced and off.
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

