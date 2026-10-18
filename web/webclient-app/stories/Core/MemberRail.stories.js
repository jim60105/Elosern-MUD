import { h, ref } from "vue";
import MemberRail from "../../components/MemberRail.vue";
import { WINDOW_RAIL_MEMBERS } from "../fixtures/window_primitives.js";
import { atFullHd, atReference, windowViewportParameters } from "../window-viewports.js";

// MemberRail (webclient-window-primitives): the party window's and the
// shop's member list, mapped from `party` v3 rows — the commander first,
// 艾拉 with the unread-unlock dot, 卡恩 knocked out (▼ 倒地), and the dashed
// 空位 entry the 成員 tab adds while a slot is free. Arrow keys, Home and End
// move focus; Enter, Space or a click selects.

const RAIL_FRAME = [
  "display: grid; grid-template-columns: calc(68px * var(--ui-scale)) calc(340px * var(--ui-scale));",
  "height: calc(560px * var(--ui-scale));",
  "margin: calc(24px * var(--ui-scale));",
  "background: #15171c;",
  "border: 1px solid rgba(185, 154, 96, 0.45);",
].join("");

const render = (args) => ({
  setup() {
    const selected = ref(args.selected);
    return () =>
      h("div", { style: RAIL_FRAME }, [
        h(MemberRail, {
          ...args,
          selected: selected.value,
          onSelect: (id) => {
            selected.value = id;
          },
        }),
        h("div", { style: "padding: calc(16px * var(--ui-scale)); color: var(--paper-400); font-size: var(--text-sm);" }, `selected: ${selected.value}`),
      ]);
  },
});

export default {
  title: "Core/MemberRail",
  component: MemberRail,
  parameters: windowViewportParameters,
};

const ARGS = { members: WINDOW_RAIL_MEMBERS, selected: 12, emptySlot: false };

export const Reference = { render, args: ARGS, ...atReference };
export const FullHd = { render, args: ARGS, ...atFullHd };
export const WithEmptySlot = { render, args: { ...ARGS, emptySlot: true, selected: "empty" }, ...atReference };
export const NothingSelected = { render, args: { ...ARGS, selected: null }, ...atReference };
