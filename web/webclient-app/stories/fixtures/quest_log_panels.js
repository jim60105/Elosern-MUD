// Story fixture slices: see stories/fixtures.js (facade) for the public surface.

// ---------------------------------------------------------------------------
// quest_log panel fixtures (the change-8 read model; the quest-drawer-split
// quest book renders them). Rows mirror the exact 16-field schema of
// web/webclient/presentation/quest_log.py — settlement and reward_line are
// null together (unresolvable issuance), never one without the other.

const QUEST_LOG_TRACK = Object.freeze({
  action_id: "guild.quest_track",
  label: "追蹤",
  enabled: true,
  disabled_reason: null,
  quantity: null,
});

export const QUEST_LOG_PANEL_SAMPLE = Object.freeze({
  schema_version: 1,
  available: true,
  rows: Object.freeze([
    // In-progress guild commission, tracked, with a deadline. The services
    // sample's guild.quests row q_1042 matches this quest_id, so the book
    // row gains the counter's abandon and turn-in descriptors.
    Object.freeze({
      quest_id: "q_1042",
      definition_key: "quest_mill_grain",
      display_name: "磨坊糧運",
      state: "in_progress",
      stage_index: 1,
      stage_total: 3,
      stage_progress: 3,
      objective_quantity: 10,
      objective_line: "將十袋糧食運往磨坊（3／10）",
      deadline_line: "剩餘 2 日",
      detail: "老周把三袋糧食交給你，要求天亮前送到磨坊。",
      tracked: true,
      issuer: Object.freeze({ kind: "guild", key: "guild:southgate", label: "南門公會" }),
      settlement: "counter",
      reward_line: "400 銅＋公會功績 25",
      track: QUEST_LOG_TRACK,
    }),
    // In-progress private commission: auto settlement, no counter-side row,
    // so the row offers tracking only even in front of a clerk.
    Object.freeze({
      quest_id: "q_2077",
      definition_key: "quest_harbor_light",
      display_name: "燈塔燈油",
      state: "in_progress",
      stage_index: 0,
      stage_total: 2,
      stage_progress: 0,
      objective_quantity: 1,
      objective_line: "為渡口燈塔補足燈油",
      deadline_line: null,
      detail: "守塔人付了訂金，請你把燈油送到燈塔。",
      tracked: false,
      issuer: Object.freeze({ kind: "npc", key: "npc:lighthouse_keeper", label: "守塔人" }),
      settlement: "auto",
      reward_line: "220 銅",
      track: QUEST_LOG_TRACK,
    }),
    // Completed, unclaimed, untracked: the canonical turn-in candidate.
    Object.freeze({
      quest_id: "q_0301",
      definition_key: "quest_mill_grain",
      display_name: "磨坊糧運",
      state: "completed",
      stage_index: 3,
      stage_total: 3,
      stage_progress: 10,
      objective_quantity: 10,
      objective_line: "將十袋糧食運往磨坊（10／10）",
      deadline_line: null,
      detail: "糧食已送達磨坊，等著回去回報。",
      tracked: false,
      issuer: Object.freeze({ kind: "guild", key: "guild:southgate", label: "南門公會" }),
      settlement: "counter",
      reward_line: "400 銅＋公會功績 25",
      track: QUEST_LOG_TRACK,
    }),
    // Failed commission: every field intact, nothing invented.
    Object.freeze({
      quest_id: "q_0099",
      definition_key: "quest_harbor_light",
      display_name: "燈塔燈油",
      state: "failed",
      stage_index: 0,
      stage_total: 2,
      stage_progress: 0,
      objective_quantity: 1,
      objective_line: "為渡口燈塔補足燈油",
      deadline_line: "期限已過",
      detail: "燈油沒有在期限內送到。",
      tracked: false,
      issuer: Object.freeze({ kind: "guild", key: "guild:southgate", label: "南門公會" }),
      settlement: "counter",
      reward_line: "220 銅＋公會功績 15",
      track: QUEST_LOG_TRACK,
    }),
  ]),
});

export const QUEST_LOG_PANEL_EMPTY_SAMPLE = Object.freeze({
  schema_version: 1,
  available: true,
  rows: Object.freeze([]),
});

export const QUEST_LOG_PANEL_UNAVAILABLE_SAMPLE = Object.freeze({
  schema_version: 1,
  available: false,
  reason: Object.freeze({
    code: "quest_log_unavailable",
    message: "任務簿目前無法顯示",
  }),
});