import { h } from "vue";
import HudFrame from "../../components/HudFrame.vue";

// HudFrame (H1, webclient-hud-01-shell-and-scene; webclient-avg-stage-shell):
// the full-bleed cinematic stage with named anchors. Deterministic offline
// args: each committed mode renders its stage gradient; the mode × surface
// visibility matrix gates surfaces with `display:none`; the open-surface
// registry drives the stage recession. Sample blocks fill every slot so the
// band split, the portrait anchor, and the command-line row are visible.

const sample = (label, extra = "") =>
  h(
    "div",
    {
      style:
        "box-sizing:border-box;height:100%;display:grid;place-items:center;" +
        "border:1px dashed #bda47766;border-radius:6px;color:#cdbf9f;" +
        "font:12px var(--f-sans);letter-spacing:.08em;" + extra,
    },
    label,
  );

const renderFrame = (args) => ({
  render: () =>
    h(HudFrame, args, {
      "actor-left": () => sample("actor-left · 玩家立繪", "background:#1a1d2099;"),
      "actor-right": () => sample("actor-right（保留）"),
      "hud-left": () => sample("hud-left", "height:120px;"),
      "hud-right": () => sample("hud-right", "height:200px;"),
      "band-message": () => sample("band-message · 訊息視窗（2/3）"),
      "band-command": () => sample("band-command · 指令面板（1/3）"),
      "command-line": () => sample("command-line · 指令列"),
    }),
});

export default {
  title: "Core/HudFrame",
  component: HudFrame,
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          "The full-bleed stage: a `position:relative; overflow:hidden` root " +
          "with named anchors — the HUD islands (`hud-left`, `hud-right`), the " +
          "portrait anchors (`actor-left`, `actor-right`) standing on the band, " +
          "the fixed-height bottom band (`--band-h`) split into `band-message` " +
          "(left 2/3) and `band-command` (right 1/3), and the `command-line` " +
          "row docked on the message region's top edge. Mode gating is " +
          "CSS-only on `data-elosern-mode` (display:none): creation hides the " +
          "message region and the command region spans the whole band. The " +
          "open-surface registry drives the stage recession behind open " +
          "drawers and overlays.",
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
