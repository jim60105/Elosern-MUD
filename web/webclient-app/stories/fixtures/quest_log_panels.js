// Structured quest book fixtures; counter merge identities stay stable.
const QUEST_LOG_TRACK = Object.freeze({
  action_id: "guild.quest_track", label: "追蹤", enabled: true,
  disabled_reason: null, quantity: null,
});
const guild = { kind: "guild", key: "guild:guild_branch_altoria", label: "埃洛西恩冒險者公會 阿爾托利亞分會" };
const base = {
  category: "gather", grade: "F", stage_index: 0, stage_total: 1,
  stage_progress: 0, objective_quantity: 1, objective_note: null,
  deadline_line: null, rationale: null, flavor: null, tracked: false,
  issuer: guild, settlement: "counter", reward_claimed: false, track: QUEST_LOG_TRACK,
};
export const QUEST_LOG_PANEL_SAMPLE = Object.freeze({
  schema_version: 2, available: true,
  rows: Object.freeze([
    Object.freeze({
      ...base, quest_id: "q_1042", definition_key: "sparrow_hunt",
      display_name: "驅除東部平原穗鳴雀", state: "in_progress",
      category: "defeat", stage_progress: 1, objective_quantity: 2,
      objective_line: "在東部大平原討伐 2 隻穗鳴雀",
      objective_note: "計數變體：領群型、啄穗型", deadline_line: "期限：剩餘 48 小時", tracked: true,
      rationale: "低階群居鳥類，較強個體會自不同方向干擾驅趕者；個體不難應付，但數量分散，取巧不易。",
      flavor: "收穫已近尾聲，東側田區每天清晨仍有成群穗鳴雀來訪。農戶請公會處理持續侵入的族群，以免今年最後一批穀物留不下來。",
      reward: { copper: 40, merit: 20, items: [{ item_key: "healing_potion", display_name: "治療藥水", quantity: 2 }] },
    }),
    Object.freeze({
      ...base, quest_id: "q_2077", definition_key: "quest_harbor_light",
      display_name: "燈塔燈油", state: "in_progress", stage_total: 2,
      objective_line: "為渡口燈塔補足燈油", flavor: "守塔人付了訂金，請你把燈油送到燈塔。",
      issuer: { kind: "npc", key: "npc:lighthouse_keeper", label: "守塔人" },
      settlement: "auto", reward: { copper: 220, merit: 0, items: [] },
    }),
    Object.freeze({
      ...base, quest_id: "q_0301", definition_key: "quest_mill_grain",
      display_name: "磨坊糧運", state: "completed", stage_index: 2, stage_total: 3,
      stage_progress: 10, objective_quantity: 10, objective_line: "將十袋糧食運往磨坊",
      flavor: "糧食已送達磨坊，等著回去回報。", reward: { copper: 400, merit: 25, items: [] },
    }),
    Object.freeze({
      ...base, quest_id: "q_0099", definition_key: "quest_harbor_light",
      display_name: "燈塔燈油", state: "failed", stage_total: 2,
      objective_line: "為渡口燈塔補足燈油", deadline_line: "期限：已逾期",
      flavor: "燈油沒有在期限內送到。", settlement: null, reward: null,
    }),
  ]),
});
export const QUEST_LOG_PANEL_EMPTY_SAMPLE = Object.freeze({ schema_version: 2, available: true, rows: Object.freeze([]) });
export const QUEST_LOG_PANEL_UNAVAILABLE_SAMPLE = Object.freeze({
  schema_version: 2, available: false,
  reason: Object.freeze({ code: "quest_log_unavailable", message: "任務簿目前無法顯示" }),
});
