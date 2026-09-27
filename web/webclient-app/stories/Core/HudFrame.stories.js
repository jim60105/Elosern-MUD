import { h, onBeforeUnmount, onMounted, ref } from "vue";
import HudFrame from "../../components/HudFrame.vue";

// HudFrame (H1, webclient-hud-01-shell-and-scene; webclient-avg-stage-shell):
// the full-bleed cinematic stage with named anchors. Deterministic offline
// args: each committed mode renders its stage gradient; the mode × surface
// visibility matrix gates surfaces with `display:none`; the open-surface
// registry drives the stage recession. Sample blocks fill every slot so the
// place card, the island anchors, the band split, the portrait anchor, and
// the collapsible command-line row (collapsed by default, expanded when
// `commandLineExpanded` is true) can be inspected in both states.

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
      "actor-right": () => (args.mode === "dialogue" ? sample("actor-right · 對話對象立繪", "background:#1a1d2099;") : null),
      // The dialogue choice list's card (webclient-dialogue-choices-overlay
      // D6): a sample of its height, centred in the `choices` anchor's span.
      choices: () =>
        args.mode === "dialogue"
          ? sample("choices · 對話選項（置中）", "height:330px;pointer-events:auto;background:#1a1d20cc;")
          : null,
      place: () => sample("place · 地點卡"),
      vitals: () => sample("vitals · 生命／狀態／同伴", "height:120px;"),
      map: () => [
        sample("map · 小地圖", "width:218px;height:200px;align-self:flex-end;"),
        sample("map · 目標（一行）", "height:32px;align-self:flex-end;padding:0 12px;"),
      ],
      "band-message": () => sample(args.mode === "dialogue" ? "band-message · 訊息視窗（全寬，名牌）" : "band-message · 訊息視窗（2/3）"),
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
          "The full-bleed stage: a `position:absolute; overflow:clip` root " +
          "with named anchors — the place card (`place`, top-left, fixed " +
          "`--place-h`), the island anchors (`vitals` below it; `map` at the " +
          "top-right: the minimap, then the one-line objective), the " +
          "portrait anchors (`actor-left`, `actor-right`) standing on the band, " +
          "the fixed-height bottom band (`--band-h`) split into `band-message` " +
          "(left 2/3) and `band-command` (right 1/3), and the `command-line` " +
          "row docked on the message region's top edge (`data-expanded` " +
          "follows `commandLineExpanded`; collapsed is `display:none`, " +
          "expanded is a 44px row). Mode gating is " +
          "CSS-only on `data-elosern-mode` (display:none): creation hides the " +
          "place card, the message region, and both island anchors, and the " +
          "command region spans the whole band; the objective line shows only " +
          "in exploration; dialogue collapses the command region " +
          "(inert at once, then a slide out over the widened message region " +
          "ending `visibility: hidden`; the dock stays mounted) so the message region " +
          "spans the band, `actor-right` carries the dialogue host, and the " +
          "`choices` anchor centres the dialogue choice list over the stage, " +
          "above the expanded command-line row. The " +
          "open-surface registry drives the stage recession behind open " +
          "drawers and overlays.",
      },
    },
  },
};

export const ExplorationStage = {
  render: renderFrame,
  args: { mode: "exploration", commandLineExpanded: false },
};

export const CombatStage = {
  render: renderFrame,
  args: { mode: "combat", commandLineExpanded: true },
};

export const CreationStage = {
  render: renderFrame,
  args: { mode: "creation" },
};

// Dialogue (webclient-dialogue-stage-actors design D4): one band column,
// the command region collapsed, both portrait anchors occupied, and the
// choice list centred over the stage (webclient-dialogue-choices-overlay).
export const DialogueStage = {
  render: renderFrame,
  args: { mode: "dialogue", commandLineExpanded: false },
};

// The borrowed command line open under the choice list: the list's span
// ends above the row.
export const DialogueCommandLine = {
  render: renderFrame,
  args: { mode: "dialogue", commandLineExpanded: true },
};

export const MenuOpenRecession = {
  render: renderFrame,
  args: { mode: "exploration", openSurfaces: ["full-log"] },
};

// The mode transitions (webclient-mode-transitions): the frame alternates
// between exploration and `target` every few seconds, with the live
// `modeChange` the client computes, so each change plays its transition.
const renderModeLoop = (args) => ({
  setup() {
    const mode = ref("exploration");
    const modeChange = ref(null);
    let timer = null;
    onMounted(() => {
      timer = setInterval(() => {
        const next = mode.value === "exploration" ? args.target : "exploration";
        modeChange.value = `${mode.value}-${next}`;
        mode.value = next;
      }, 2400);
    });
    onBeforeUnmount(() => clearInterval(timer));
    return () => h(renderFrame({ ...args, mode: mode.value, modeChange: modeChange.value }));
  },
});

// Exploration <-> dialogue: the message region widens at once while the
// command region slides out over it, then back.
export const DialogueEnter = {
  render: renderModeLoop,
  args: { target: "dialogue", commandLineExpanded: false },
};

// Exploration <-> combat: the flash, the veil, and the command region's
// content flipping to the combat root, then back.
export const CombatEnter = {
  render: renderModeLoop,
  args: { target: "combat", commandLineExpanded: false },
};
