import { h, ref } from "vue";
import ActionBar from "../../components/ActionBar.vue";
import ListDetail from "../../components/ListDetail.vue";
import MemberRail from "../../components/MemberRail.vue";
import { WINDOW_RAIL_MEMBERS } from "../fixtures/window_primitives.js";
import { atFullHd, atReference, windowViewportParameters } from "../window-viewports.js";

// ListDetail (webclient-window-primitives): the window body grid — the
// member rail, a list column and a detail column. The list and the detail
// scroll independently (both are long here); the action bar stays pinned to
// the detail's bottom. `portrait` narrows the list for the 成員 nameplate.

const BODY_FRAME = [
  "height: calc(560px * var(--ui-scale));",
  "margin: calc(24px * var(--ui-scale));",
  "display: flex;",
  "background: linear-gradient(180deg, #16181dfa, #0e1014fa);",
  "border: 1px solid rgba(185, 154, 96, 0.45);",
  "color: var(--paper-200); font-size: var(--text-sm);",
].join("");

const ROW_STYLE = "padding: calc(8px * var(--ui-scale)) calc(12px * var(--ui-scale)); border-bottom: 1px dashed rgba(185, 154, 96, 0.14);";
const PARAGRAPH_STYLE = "margin: 0 0 calc(12px * var(--ui-scale)); font: var(--text-md) / 1.8 var(--f-serif); color: var(--paper-300);";

const render = (args) => ({
  setup() {
    const selected = ref(11);
    return () =>
      h("div", { style: BODY_FRAME }, [
        h(ListDetail, { variant: args.variant, listLabel: "背包物品", detailLabel: "物品詳情" }, {
          rail: () =>
            h(MemberRail, { members: WINDOW_RAIL_MEMBERS, selected: selected.value, onSelect: (id) => { selected.value = id; } }),
          list: () => Array.from({ length: args.listRows }, (_, i) => h("div", { style: ROW_STYLE }, `物品 ${i + 1}`)),
          detail: () =>
            Array.from({ length: args.detailParagraphs }, (_, i) =>
              h("p", { style: PARAGRAPH_STYLE }, `第 ${i + 1} 段：夜間採集的藥草，能在旅途中恢復些許體力。`),
            ),
          actions: () => h(ActionBar, { actions: [{ key: "use", label: "使用…", tone: "primary" }], onAction: () => {} }),
        }),
      ]);
  },
});

export default {
  title: "Core/ListDetail",
  component: ListDetail,
  parameters: windowViewportParameters,
};

const ARGS = { variant: "default", listRows: 40, detailParagraphs: 24 };

export const Reference = { render, args: ARGS, ...atReference };
export const FullHd = { render, args: ARGS, ...atFullHd };
export const Portrait = { render, args: { ...ARGS, variant: "portrait" }, ...atReference };
