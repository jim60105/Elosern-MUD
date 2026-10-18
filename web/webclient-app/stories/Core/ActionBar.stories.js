import { h } from "vue";
import ActionBar from "../../components/ActionBar.vue";
import { atFullHd, atReference, windowViewportParameters } from "../window-viewports.js";

// ActionBar (webclient-window-primitives): the bar pinned to a window's
// detail column. Its left slot shows committed state feedback only — the
// caller's reason (the combat 戰鬥中無法交換物品) and each disabled control's
// own reason — and the buttons sit at the right end. A disabled control
// stays focusable and emits nothing.

const DETAIL_FRAME = [
  "width: calc(720px * var(--ui-scale));",
  "margin: calc(24px * var(--ui-scale));",
  "padding: calc(16px * var(--ui-scale)) calc(20px * var(--ui-scale));",
  "background: linear-gradient(180deg, #16181dfa, #0e1014fa);",
  "border: 1px solid rgba(185, 154, 96, 0.45);",
].join("");

const render = (args) => ({
  render: () => h("div", { style: DETAIL_FRAME }, [h(ActionBar, { ...args, onAction: () => {} })]),
});

export default {
  title: "Core/ActionBar",
  component: ActionBar,
  parameters: windowViewportParameters,
};

// The bag outside combat: equip naming the replaced item, and a use that is
// disabled for a knocked-out member with its committed reason.
const BAG_ARGS = {
  actions: [
    { key: "equip", label: "裝備（替換鐵製長劍）", tone: "gold", glyph: "sword" },
    { key: "use", label: "使用…", tone: "primary", enabled: false, reason: "卡恩倒地，無法使用物品。" },
  ],
};

// The bag in combat: no give controls, the combat reason, and use becoming
// the member's round command.
const COMBAT_ARGS = {
  reason: { code: "transfer_in_combat", message: "戰鬥中無法交換物品" },
  actions: [{ key: "draft", label: "設為艾拉本回合的行動…", tone: "primary" }],
};

// A disabled give with its reason (the spec scenario).
const DISABLED_GIVE_ARGS = {
  actions: [{ key: "give", label: "交給艾拉", tone: "primary", enabled: false, reason: "戰鬥中無法交換物品" }],
};

export const Reference = { render, args: BAG_ARGS, ...atReference };
export const FullHd = { render, args: BAG_ARGS, ...atFullHd };
export const InCombat = { render, args: COMBAT_ARGS, ...atReference };
export const DisabledGive = { render, args: DISABLED_GIVE_ARGS, ...atReference };
