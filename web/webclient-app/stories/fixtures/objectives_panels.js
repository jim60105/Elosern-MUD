// Story fixture slices: see stories/fixtures.js (facade) for the public surface.

export const OBJECTIVES_PANEL_SAMPLE = Object.freeze({
  schema_version: 1,
  available: true,
  rows: [
    {
      quest_id: "q_1042",
      display_name: "磨坊糧運",
      objective_line: "抵達霧骨渡口",
      stage_index: 1,
      stage_total: 2,
      stage_progress: 1,
      objective_quantity: 1,
      reward_copper: null,
      deadline_line: null,
    },
    {
      quest_id: "q_1043",
      display_name: "過河商議",
      objective_line: "與灰婆婆議價過河",
      stage_index: 2,
      stage_total: 2,
      stage_progress: 0,
      objective_quantity: 1,
      reward_copper: 80,
      deadline_line: "剩餘 2 日",
    },
    {
      quest_id: "q_1044",
      display_name: "清除水妖",
      objective_line: "討伐渡口水妖",
      stage_index: 1,
      stage_total: 1,
      stage_progress: 2,
      objective_quantity: 5,
      reward_copper: 150,
      deadline_line: null,
    },
  ],
});

export const OBJECTIVES_PANEL_EMPTY_SAMPLE = Object.freeze({
  schema_version: 1,
  available: true,
  rows: [],
});