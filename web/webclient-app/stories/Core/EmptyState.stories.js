import { h } from "vue";
import EmptyState from "../../components/EmptyState.vue";

// EmptyState (webclient-drawer-content-polish): the one presentational body
// an available but empty drawer list shows — decorative registry glyph,
// headline, one line of guidance in a solid ink frame, and an optional slot
// for a real control the host already owns. The stories are deterministic and
// offline: the default card, a headline-only card, a card carrying a host
// action, and every host's copy side by side on the drawer panel ground.

const HOSTS = [
  { glyph: "quests", headline: "目前沒有任務紀錄", guidance: "接取的任務會列在這裡。" },
  { glyph: "lore", headline: "尚未發現任何條目", guidance: "旅途中發現的條目會依分類收錄於此。" },
  { glyph: "inventory", headline: "背包裡沒有物品", guidance: "取得的物品會列在這裡。" },
  { glyph: "party", headline: "目前沒有同伴", guidance: "可從下方空位邀請當地的自由 NPC。" },
];

function ground(children) {
  return h(
    "div",
    { style: "padding: 24px; background: var(--surface-panel); min-height: 100vh; box-sizing: border-box;" },
    children,
  );
}

export default {
  title: "Core/EmptyState",
  component: EmptyState,
  parameters: {
    docs: {
      description: {
        component:
          "The shared empty guidance for an available but empty drawer list. Presentational only; an unavailable panel keeps its own registry reason instead.",
      },
    },
  },
  args: HOSTS[0],
};

export const Default = {
  render: (args) => ({
    setup: () => () => ground([h(EmptyState, args)]),
  }),
};

export const HeadlineOnly = {
  args: { glyph: null, headline: "目前沒有任務紀錄", guidance: "" },
  render: (args) => ({
    setup: () => () => ground([h(EmptyState, args)]),
  }),
};

export const WithHostAction = {
  args: HOSTS[3],
  render: (args) => ({
    setup: () => () =>
      ground([
        h(EmptyState, args, {
          default: () => h("button", { type: "button", class: "ui-btn ui-btn--sm", disabled: true }, "邀請當前 NPC…"),
        }),
      ]),
  }),
};

export const EveryHost = {
  render: () => ({
    setup: () => () =>
      ground([
        h(
          "div",
          { style: "display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px;" },
          HOSTS.map((host) => h(EmptyState, host)),
        ),
      ]),
  }),
};
