import { h } from "vue";
import ObjectiveTracker from "../../components/ObjectiveTracker.vue";
import {
  OBJECTIVES_PANEL_SAMPLE,
  OBJECTIVES_PANEL_EMPTY_SAMPLE,
} from "../fixtures.js";

// ObjectiveTracker (webclient-align-09-objective-tracker-ui;
// webclient-avg-stage-hud-anchors design D2): the one-line objective under the
// minimap. Stories: three tracked (`ActiveObjectives`: the first row plus `+2`), a completed
// objective, a progress counter, a reward tag, a row whose deadline stays in
// the quest drawer, a long line that truncates, and empty rows (renders
// nothing). The frame mimics the `map` anchor at 1920x1080: a 332px
// right-aligned column under a 218px minimap-sized card.

export default {
  title: "Overlays/ObjectiveTracker",
  component: ObjectiveTracker,
};

const renderTracker = (args) => ({
  render: () =>
    h(
      "div",
      {
        style:
          "padding: 20px; background: linear-gradient(135deg, #2b3440, #151920);",
      },
      [
        h(
          "div",
          {
            style:
              "width: 332px; display: flex; flex-direction: column; align-items: stretch; gap: 14px;",
          },
          [
            h("div", {
              "aria-hidden": "true",
              style:
                "align-self: flex-end; width: 218px; height: 120px; box-sizing: border-box; " +
                "border: 1px dashed #bda47766; border-radius: var(--radius);",
            }),
            h(ObjectiveTracker, args),
          ],
        ),
      ],
    ),
});

export const ActiveObjectives = {
  render: renderTracker,
  args: {
    rows: OBJECTIVES_PANEL_SAMPLE.rows,
  },
};

export const LongLine = {
  render: renderTracker,
  args: {
    rows: [
      {
        quest_id: "q_long",
        display_name: "北岸的委託",
        objective_line: "在第三個滿月之前，把灰婆婆託付的封蠟信件交給北岸燈塔的守望人",
        stage_index: 2,
        stage_total: 3,
        stage_progress: 0,
        objective_quantity: 1,
        reward_copper: 120,
        deadline_line: "剩餘 4 日",
      },
      OBJECTIVES_PANEL_SAMPLE.rows[1],
    ],
  },
};

export const SingleCompleted = {
  render: renderTracker,
  args: {
    rows: [
      {
        quest_id: "q_done",
        display_name: "抵達渡口",
        objective_line: "抵達霧骨渡口",
        stage_index: 1,
        stage_total: 1,
        stage_progress: 1,
        objective_quantity: 1,
        reward_copper: null,
        deadline_line: null,
      },
    ],
  },
};

export const ProgressCounter = {
  render: renderTracker,
  args: {
    rows: [
      {
        quest_id: "q_progress",
        display_name: "討伐水妖",
        objective_line: "討伐渡口水妖",
        stage_index: 1,
        stage_total: 1,
        stage_progress: 3,
        objective_quantity: 10,
        reward_copper: 200,
        deadline_line: null,
      },
    ],
  },
};

export const WithDeadline = {
  render: renderTracker,
  args: {
    rows: [
      {
        quest_id: "q_deadline",
        display_name: "緊急信件",
        objective_line: "將信件送達市政廳",
        stage_index: 1,
        stage_total: 1,
        stage_progress: 0,
        objective_quantity: 1,
        reward_copper: 80,
        deadline_line: "剩餘 12 小時",
      },
    ],
  },
};

export const EmptyRows = {
  render: renderTracker,
  args: {
    rows: OBJECTIVES_PANEL_EMPTY_SAMPLE.rows,
  },
};
