import { h } from "vue";
import FullLogOverlay from "../../components/FullLogOverlay.vue";
import { NARRATIVE_SAMPLE } from "../fixtures.js";

// FullLogOverlay (H1, webclient-hud-01-shell-and-scene, design D4): the
// full-screen, scrollable view of the complete retained narrative. It
// renders the same line stream through the preserved `narrative-renderer.js`
// (one markup path), traps focus while open, closes on Escape, and
// restores focus to the control that opened it.

const renderOverlay = (args) => ({
  render: () =>
    h(
      "div",
      { style: "position: relative; width: 100%; height: 420px; background: var(--ink-950); overflow: auto;" },
      [h(FullLogOverlay, args)],
    ),
});

export default {
  title: "Core/FullLogOverlay",
  component: FullLogOverlay,
  parameters: {
    docs: {
      description: {
        component:
          "The complete retained narrative, reachable in one action from the " +
          "caption card's `完整日誌` control. Scrollable, focus-trapped, " +
          "Escape-closing, with focus restored to the opener.",
      },
    },
  },
};

export const FullLog = {
  render: renderOverlay,
  args: { lines: NARRATIVE_SAMPLE },
};
