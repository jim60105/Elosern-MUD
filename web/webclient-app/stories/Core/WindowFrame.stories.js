import { h, ref } from "vue";
import ActionBar from "../../components/ActionBar.vue";
import HoldingsStrip from "../../components/HoldingsStrip.vue";
import ListDetail from "../../components/ListDetail.vue";
import MemberRail from "../../components/MemberRail.vue";
import WindowFrame from "../../components/WindowFrame.vue";
import { glyphAttrs, glyphPath } from "../../components/dock-icons.js";
import { ITEM_HOLDINGS_COMBAT, ITEM_HOLDINGS_CONSUMABLE, WINDOW_RAIL_MEMBERS } from "../fixtures/window_primitives.js";
import { atFullHd, atReference, windowViewportParameters } from "../window-viewports.js";

// WindowFrame (webclient-window-primitives): the shared window chrome — the
// HudDrawer seal, title and close, the first-level IconTabs and the header
// extras (the party purse) on the header rule — composed with ListDetail,
// MemberRail, HoldingsStrip and ActionBar into a 背包-like body for side by
// side review with Design/PartyMemberManagement at both viewport sizes. The
// frame keeps HudDrawer's focus trap, Escape and motion; closing here is
// inert (the story keeps the frame mounted).

export default {
  title: "Core/WindowFrame",
  component: WindowFrame,
  parameters: windowViewportParameters,
};

const TABS = [
  { key: "member", label: "成員", glyph: "member" },
  { key: "bag", label: "背包", glyph: "inventory" },
  { key: "status", label: "狀態", glyph: "status" },
  { key: "skill", label: "技能", glyph: "skills" },
  { key: "lineage", label: "系譜", glyph: "lineage" },
];

const glyph = (key) =>
  h("svg", { viewBox: "0 0 24 24", fill: "none", "aria-hidden": "true", style: "width: 1em; height: 1em;" }, [
    h("path", { d: glyphPath(key), stroke: "currentColor", "stroke-width": 1.6, ...glyphAttrs(key) }),
  ]);

const BAG_ROWS = [
  { key: "potion_heal", name: "治療藥水", glyph: "potion", held: 5 },
  { key: "ration", name: "乾糧", glyph: "ration", held: 3 },
  { key: "moon_herb", name: "月光草", glyph: "herb", held: 7 },
];

const rowStyle = (selected) =>
  [
    "display: flex; align-items: center; gap: calc(12px * var(--ui-scale)); width: 100%;",
    "padding: calc(8px * var(--ui-scale)) calc(12px * var(--ui-scale)); color: var(--paper-100);",
    "font: var(--text-sm) var(--f-serif); text-align: left; background: transparent; cursor: pointer;",
    selected
      ? "border: 1px solid var(--seal-700); border-radius: var(--radius-sm); box-shadow: inset 3px 0 0 var(--seal-500);"
      : "border: 0; border-bottom: 1px dashed rgba(185, 154, 96, 0.14);",
  ].join("");

const render = (args) => ({
  setup() {
    const tab = ref(args.modelValue);
    const member = ref(11);
    const panel = args.combat ? ITEM_HOLDINGS_COMBAT : ITEM_HOLDINGS_CONSUMABLE;
    return () =>
      h(
        WindowFrame,
        {
          title: "隊伍",
          seal: "party",
          tabs: TABS,
          tabsLabel: "隊伍分頁",
          drawerKey: "party",
          modelValue: tab.value,
          "onUpdate:modelValue": (key) => {
            tab.value = key;
          },
          onClose: () => {},
        },
        {
          extras: () => h("span", { style: "display: inline-flex; align-items: center; gap: var(--sp-1);" }, [glyph("reward_copper"), "1,240 銅"]),
          default: () =>
            h(ListDetail, { listLabel: "背包物品", detailLabel: "物品詳情" }, {
              rail: () =>
                h(MemberRail, {
                  members: WINDOW_RAIL_MEMBERS,
                  selected: member.value,
                  emptySlot: tab.value === "member",
                  onSelect: (id) => {
                    member.value = id;
                  },
                }),
              list: () =>
                BAG_ROWS.map((row, index) =>
                  h("button", { type: "button", style: rowStyle(index === 0) }, [
                    h("span", { style: "color: var(--gold-400); font-size: var(--text-lg);" }, [glyph(row.glyph)]),
                    h("span", { style: "flex: 1;" }, row.name),
                    h("span", { style: "color: var(--paper-400); font-size: var(--text-xs);" }, `×${row.held}`),
                  ]),
                ),
              detail: () => [
                h("h3", { style: "margin: 0; color: var(--paper-50); font: var(--text-3xl) var(--f-display);" }, "治療藥水"),
                h("p", { style: "margin: var(--sp-2) 0 var(--sp-5); color: var(--paper-300); font: var(--text-md) / 1.8 var(--f-serif);" }, "恢復 40 點 HP。"),
                h(HoldingsStrip, {
                  rows: panel.rows,
                  giverId: panel.giver_id,
                  members: WINDOW_RAIL_MEMBERS,
                  combat: args.combat,
                  giveQuantity: args.combat ? null : 1,
                  onGive: () => {},
                }),
              ],
              actions: () =>
                h(ActionBar, {
                  reason: args.combat ? "戰鬥中無法交換物品" : null,
                  actions: args.combat
                    ? [{ key: "draft", label: "設為莉瑟本回合的行動…", tone: "primary" }]
                    : [{ key: "use", label: "使用…", tone: "primary" }],
                  onAction: () => {},
                }),
            }),
        },
      );
  },
});

export const Reference = { render, args: { modelValue: "bag", combat: false }, ...atReference };
export const FullHd = { render, args: { modelValue: "bag", combat: false }, ...atFullHd };
export const InCombat = { render, args: { modelValue: "bag", combat: true }, ...atReference };
