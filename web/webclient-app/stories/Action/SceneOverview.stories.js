import { h } from "vue";
import SceneOverview from "../../components/SceneOverview.vue";
import {
  AFFORDANCES,
  DIRECTION_LABELS,
  explorationPanelFixture,
  overviewArgs,
} from "../fixtures/scene_overview.js";

// SceneOverview: the chip rows of the exploration root pane (AVG stage
// design §7), in the right column beside the exit compass
// (exploration-exit-compass). Chip rows 人物 / 物件 and a label-less footer
// (查看房間 ‧ 等待／休息 ‧ 建議), built by the real `overviewMenu` through the
// shared derived-shape helper; exits are the compass's, never chips. Props:
// menu, focusedKey, idPrefix, active.
// Events: focus-change (every click), activate ({key, item}, enabled chips
// only). Each story renders inside a box the size of the command panel at
// 1451x790 (484×220) that scrolls like the dock pane.

const commandPanel = (story) => ({
  render: () =>
    h(
      "div",
      {
        style: {
          width: "484px",
          height: "220px",
          boxSizing: "border-box",
          padding: "12px 14px",
          overflowY: "auto",
          overflowX: "hidden",
          background: "linear-gradient(0deg, #0c0a0e, #141019 70%, var(--panel))",
          borderTop: "var(--line)",
        },
      },
      [h(story())],
    ),
});

const render = (args) => ({ render: () => h(SceneOverview, args) });

export default {
  title: "Action/SceneOverview",
  component: SceneOverview,
  decorators: [commandPanel],
};

const FULL_ROOM = explorationPanelFixture({
  exits: [
    { label: "北", destination: "room:901" },
    { label: "東", destination: "room:902" },
    { label: "酒館門", destination: "room:903", enabled: false, reason: "酒館打烊了，門從裡面上了閂。" },
  ],
  targets: [
    { identity: 11, name: "葛里安‧衛登", affordances: [AFFORDANCES.talk, AFFORDANCES.guild] },
    { identity: 12, name: "布蘭", affordances: [AFFORDANCES.talk, AFFORDANCES.trade] },
  ],
  entities: [{ identity: 21, name: "旅人艾拉" }],
  objects: [{ identity: 31, name: "任務板" }, { identity: 32, name: "壁爐" }],
});

const READY_SUGGESTIONS = {
  status: "ready",
  cards: [
    { kind: "known_action", label: "查看任務板", action_code: "explore.look", params: { target_id: 31 } },
    { kind: "known_action", label: "與布蘭交談", action_code: "explore.look", params: { target_id: 12 } },
  ],
};

// Every row present: people (two hosts and a look-only traveller), objects,
// and the footer with 建議 (2). The room's three exits are the compass's.
export const FullRoom = {
  render,
  args: overviewArgs(FULL_ROOM, {
    suggestions: READY_SUGGESTIONS,
    focusedKey: "target-11",
  }),
};

// Nobody and nothing here: only the footer renders.
export const EmptyRows = {
  render,
  args: overviewArgs(explorationPanelFixture({ exits: [{ label: "南", destination: "room:904" }] })),
};

// A crowded crossroads: 10 people wrap inside the panel's width with no
// horizontal scroll (a taller room scrolls the panel).
export const Overflowing = {
  render,
  args: overviewArgs(
    explorationPanelFixture({
      exits: [
        ...DIRECTION_LABELS.map((label, i) => ({ label, destination: `room:${910 + i}` })),
        { label: "地下水道入口" },
        { label: "舊城牆缺口", enabled: false, reason: "崩落的石塊堵住了缺口。" },
      ],
      targets: Array.from({ length: 10 }, (_, i) => ({
        identity: 40 + i,
        name: ["哨兵", "攤販", "吟遊詩人", "巡邏隊長", "乞丐", "藥師", "鐵匠學徒", "信差", "修女", "賞金獵人"][i],
        affordances: i % 3 === 0 ? [AFFORDANCES.engage] : [AFFORDANCES.talk],
      })),
    }),
    {
      suggestions: { status: "generating" },
      focusedKey: "target-45",
    },
  ),
};
