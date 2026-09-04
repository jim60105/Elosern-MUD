import { h } from "vue";
import HelpOverlay from "../../components/HelpOverlay.vue";

// HelpOverlay (B5 full-overlays family): the full-viewport help dialog. The
// body is the client's own control reference — the keys this client binds
// and how the game's own `help` output is reached. There is no authored
// game-help payload; the component renders exactly the client-owned data.

const renderOverlay = (args) => ({ render: () => h(HelpOverlay, args) });

export default {
  title: "Overlays/HelpOverlay",
  component: HelpOverlay,
};

export const Default = {
  render: renderOverlay,
  args: {},
};
