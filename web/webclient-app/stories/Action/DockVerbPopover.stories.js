import { h } from "vue";
import DockVerbPopover from "../../components/DockVerbPopover.vue";
import SceneOverview from "../../components/SceneOverview.vue";
import {
  AFFORDANCES,
  explorationPanelFixture,
  localMapFixture,
  overviewArgs,
  verbArgs,
} from "../fixtures/scene_overview.js";

// DockVerbPopover: a person chip's verb menu, anchored to the bottom edge
// of the command panel over the (inert) scene overview. Rows come from the
// real `verbMenuFor` through the shared derived-shape helper: the target's
// affordances in payload order, 查看, then 返回上一層. Props: menu,
// focusedKey, idPrefix. Events: focus-change, activate ({key, item}, enabled
// rows only), back (a press on the layer outside the card).

const PANEL = explorationPanelFixture({
  exits: [
    { label: "北", destination: "room:901" },
    { label: "東", destination: "room:902" },
  ],
  targets: [
    { identity: 11, name: "葛里安·衛登", affordances: [AFFORDANCES.talk, AFFORDANCES.trade] },
    { identity: 13, name: "霧狼", kind: "monster", affordances: [AFFORDANCES.engage] },
    { identity: 14, name: "沉睡的醉漢", affordances: [] },
  ],
  objects: [{ identity: 31, name: "任務板" }],
});

const OVERVIEW = overviewArgs(PANEL, {
  localMap: localMapFixture([
    ["room:901", "北岸大道"],
    ["room:902", "公會櫃檯"],
  ]),
  active: false,
});

// The command panel at 1920×1080 (640×300), positioned so the popover's
// layer fills it, with the inactive overview underneath.
const overPanel = (story) => ({
  render: () =>
    h(
      "div",
      {
        style: {
          position: "relative",
          width: "640px",
          height: "300px",
          boxSizing: "border-box",
          overflow: "hidden",
          background: "linear-gradient(0deg, #0c0a0e, #141019 70%, var(--panel))",
          borderTop: "var(--line)",
        },
      },
      [
        h("div", { style: { padding: "12px 14px" } }, [h(SceneOverview, OVERVIEW)]),
        h(story()),
      ],
    ),
});

const render = (args) => ({ render: () => h(DockVerbPopover, args) });

export default {
  title: "Action/DockVerbPopover",
  component: DockVerbPopover,
  decorators: [overPanel],
};

// A dialogue host: 交談, 交易, 查看, and back.
export const DialogueHost = {
  render,
  args: verbArgs(PANEL, 11, { focusedKey: "talk-open" }),
};

// A hostile target: 戰鬥, 查看, and back.
export const HostileTarget = {
  render,
  args: verbArgs(PANEL, 13, { focusedKey: "engage" }),
};

// A target with no mapped affordance: 查看 and back only.
export const LookOnly = {
  render,
  args: verbArgs(PANEL, 14, { focusedKey: "look-target" }),
};
