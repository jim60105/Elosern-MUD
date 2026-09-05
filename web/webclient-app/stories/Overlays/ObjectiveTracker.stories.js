import { h } from "vue";
import ObjectiveTracker from "../../components/ObjectiveTracker.vue";
import {
  OBJECTIVES_PANEL_SAMPLE,
  OBJECTIVES_PANEL_EMPTY_SAMPLE,
} from "../fixtures.js";

// ObjectiveTracker (webclient-align-09-objective-tracker-ui):
// the bottom-right `.obj` objective tracker island stories — active objectives,
// single completed objective, progress counter, reward tag, and deadline line.

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
          "position: relative; width: 320px; min-height: 200px; padding: 20px; background: var(--ink-950, #0d0a12);",
      },
      [h(ObjectiveTracker, args)],
    ),
});

export const ActiveObjectives = {
  render: renderTracker,
  args: {
    rows: OBJECTIVES_PANEL_SAMPLE.rows,
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
