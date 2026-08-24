import { h } from "vue";
import HudFrame from "../../components/HudFrame.vue";

// HudFrame (H1, webclient-hud-01-shell-and-scene): the full-bleed cinematic
// stage with named, absolutely positioned anchors. Deterministic offline
// args: each committed mode renders its stage gradient; the mode × surface
// visibility matrix gates surfaces with `display:none`; the open-surface
// registry drives the stage recession.

const renderFrame = (args) => ({ render: () => h(HudFrame, args) });

export default {
  title: "Core/HudFrame",
  component: HudFrame,
  parameters: {
    docs: {
      description: {
        component:
          "The full-bleed stage: `position:relative; overflow:hidden` root with " +
          "named anchors (`hud-left`, `hud-right`, `feed`, `dock`, `command-line`), " +
          "sized from the `--dock-h` token. Mode gating is CSS-only on " +
          "`data-elosern-mode` (display:none), and the open-surface registry " +
          "drives the stage recession behind open drawers and overlays.",
      },
    },
  },
};

export const ExplorationStage = {
  render: renderFrame,
  args: { mode: "exploration" },
};

export const CombatStage = {
  render: renderFrame,
  args: { mode: "combat" },
};

export const CreationStage = {
  render: renderFrame,
  args: { mode: "creation" },
};

export const MenuOpenRecession = {
  render: renderFrame,
  args: { mode: "exploration", openSurfaces: ["full-log"] },
};
