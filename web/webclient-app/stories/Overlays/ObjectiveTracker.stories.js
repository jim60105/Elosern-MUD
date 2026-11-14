import { h } from "vue";
import ObjectiveTracker from "../../components/ObjectiveTracker.vue";
import {
  OBJECTIVES_PANEL_SAMPLE,
  OBJECTIVES_PANEL_EMPTY_SAMPLE,
} from "../fixtures.js";

// ObjectiveTracker (webclient-align-09-objective-tracker-ui;
// webclient-avg-stage-hud-anchors design D2; objective-tracker-instrument-panel):
// the objective line under the minimap, worn as an instrument panel that spans
// the column, with no visible 目標 label (it is the region's accessible name).
// Stories: three tracked (`ActiveObjectives`: the first row plus the
// stacked-lines glyph count of 2), a completed objective, a progress counter
// with its ticks, a reached count (`CountReached`), a count above twelve drawn
// as one tapering stroke (`LongCount`), a reward tag, a row whose deadline
// stays in the quest drawer, a long line that truncates, and empty rows
// (renders nothing). The frame mimics the `map` anchor at 1451x790: its 291px
// column under the 240px minimap canvas's footprint, 10px apart.

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
              "width: 291px; display: flex; flex-direction: column; align-items: stretch; gap: 10px;",
          },
          [
            h("div", {
              "aria-hidden": "true",
              style:
                "align-self: flex-end; width: 240px; height: 120px; margin-right: 22px; box-sizing: border-box; " +
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

export const CountReached = {
  render: renderTracker,
  args: {
    rows: [
      {
        quest_id: "q_reached",
        display_name: "採集蘆葦",
        objective_line: "割下渡口的蘆葦",
        stage_index: 1,
        stage_total: 1,
        stage_progress: 5,
        objective_quantity: 5,
        reward_copper: null,
        deadline_line: null,
      },
    ],
  },
};

export const LongCount = {
  render: renderTracker,
  args: {
    rows: [
      {
        quest_id: "q_long_count",
        display_name: "清點貨箱",
        objective_line: "清點碼頭倉庫的貨箱",
        stage_index: 1,
        stage_total: 1,
        stage_progress: 12,
        objective_quantity: 30,
        reward_copper: null,
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
