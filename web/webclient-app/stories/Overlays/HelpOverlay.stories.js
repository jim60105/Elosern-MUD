import { h } from "vue";
import HelpOverlay from "../../components/HelpOverlay.vue";

// HelpOverlay (B5 full-overlays family): the full-viewport help dialog. The
// body is the client's own control reference — the keys this client binds
// and static party rules, with the path to the game's `help` output.

const renderOverlay = (args) => ({ render: () => h(HelpOverlay, args) });

export default {
  title: "Overlays/HelpOverlay",
  component: HelpOverlay,
};

export const Default = {
  render: renderOverlay,
  args: {},
};

export const PartyRules = {
  render: renderOverlay,
  args: {},
  parameters: {
    docs: {
      description: {
        story: "隊伍規則集中於說明，包含同行、物品交換、戰鬥限制、系譜圖例、商店價格與視窗快捷鍵。",
      },
    },
  },
};
