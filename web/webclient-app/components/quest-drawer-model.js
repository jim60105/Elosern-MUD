// quest-drawer-model (quest-drawer-book-tab, design Decision 1): every
// decision the quest drawer makes, as pure functions over the committed
// `quest_log` v2 and `services` panels. The components only render the view
// models these return.
//
// Honesty rules kept here:
// - Only committed fields render; no row, reward, or action is invented.
// - Counter actions (abandon, turn-in) come only from the `services` guild
//   quest row with the same `quest_id`, mirrored exactly; `quest_id` is the
//   single join between the two panels.
// - Fixed client copy (無期限, the settlement notes, the action-bar reasons)
//   is stable text that never paraphrases server prose.

export const BOOK_STATES = Object.freeze([
  Object.freeze({ key: "in_progress", label: "進行中", glyph: "quest_in_progress", guidance: "接取的委託會列在這裡。" }),
  Object.freeze({ key: "completed", label: "已完成", glyph: "quest_completed", guidance: "達成的委託會列在這裡。" }),
  Object.freeze({ key: "failed", label: "失敗", glyph: "quest_failed", guidance: "失敗或放棄的委託會列在這裡。" }),
]);

const CATEGORY_LABELS = Object.freeze({
  gather: "採集",
  defeat: "討伐",
  escort: "護衛",
  explore: "探索",
  emergency: "緊急",
});

const SETTLEMENT_NOTES = Object.freeze({
  counter: "回公會櫃檯領取",
  auto: "完成即結算",
});

// The fixed counter-tab reason when the services panel is available but no
// guild section resolves (no guild clerk here).
export const COUNTER_CLERK_REASON = "需在公會職員面前才能辦理";

export const ABANDON_WARNING = (name) => `放棄「${name}」後任務會判定失敗，且無法回復。`;

const REASON_CLAIMED = "報酬已領取";
const REASON_RETURN_TO_COUNTER = "回到公會櫃檯即可交付並領取報酬。";
const REASON_FAILED = "此委託已失敗，沒有報酬。";

// Pips render up to this many objective units; larger targets use a bar.
export const PIP_LIMIT = 12;

// `absent` before the first commit, `unavailable` for the registry-owned
// degraded form, otherwise `available`.
export function bookStatus(questLog) {
  if (!questLog) return "absent";
  if (questLog.available === false) return "unavailable";
  return "available";
}

// Rows grouped by stored state, panel order preserved within each state.
export function rowsByState(questLog) {
  const groups = Object.fromEntries(BOOK_STATES.map((state) => [state.key, []]));
  if (bookStatus(questLog) !== "available") return groups;
  for (const row of questLog.rows ?? []) {
    groups[row?.state]?.push(row);
  }
  return groups;
}

export function stateCounts(groups) {
  return Object.fromEntries(BOOK_STATES.map((state) => [state.key, groups[state.key]?.length ?? 0]));
}

// The counter side of the merge. An unavailable services panel, or one with
// no guild section, contributes no rows, so no counter action renders.
export function counterRowsById(services) {
  const map = new Map();
  if (!services || services.available === false) return map;
  for (const row of services.guild?.quests ?? []) {
    if (row && typeof row.quest_id === "string") map.set(row.quest_id, row);
  }
  return map;
}

// The completed tab's count is emphasized only while some completed row can
// be turned in at the counter right now.
export function turninHot(groups, counterRows) {
  return (groups.completed ?? []).some((row) => counterRows.get(row.quest_id)?.turnin?.enabled === true);
}

// The guild counter tab: enabled only with a usable guild section; otherwise
// disabled with the panel's own reason or the fixed clerk line.
export function counterTab(services) {
  if (services && services.available === false) {
    return {
      enabled: false,
      reason: services.reason?.message ?? null,
      reasonCode: services.reason?.code ?? null,
    };
  }
  if (services && services.guild != null) {
    return { enabled: true, reason: null, reasonCode: null };
  }
  return { enabled: false, reason: COUNTER_CLERK_REASON, reasonCode: null };
}

function percent(value, target) {
  if (!(target > 0)) return 0;
  return Math.round((Math.min(Math.max(value, 0), target) / target) * 100);
}

function categoryGlyph(category) {
  return CATEGORY_LABELS[category] ? `cat_${category}` : null;
}

function issuerSummary(row) {
  const issuer = row.issuer?.kind === "guild" ? "公會委託" : (row.issuer?.label ?? "");
  return row.deadline_line ? `${issuer} · ${row.deadline_line}` : issuer;
}

// One list row: category glyph, name, tracked flag, grade, and either the
// in-progress bar or the issuer summary.
export function bookListRow(row) {
  const inProgress = row.state === "in_progress";
  return {
    id: row.quest_id,
    name: row.display_name,
    state: row.state,
    glyph: categoryGlyph(row.category),
    tracked: inProgress && row.tracked === true,
    grade: row.grade ?? null,
    progress: inProgress
      ? {
          value: row.stage_progress,
          target: row.objective_quantity,
          pct: percent(row.stage_progress, row.objective_quantity),
        }
      : null,
    sub: inProgress ? null : issuerSummary(row),
  };
}

function rewardView(row) {
  const reward = row.reward;
  if (!reward) return null;
  const cells = [{ kind: "copper", glyph: "reward_copper", value: reward.copper, unit: "銅" }];
  if (reward.merit > 0) {
    cells.push({ kind: "merit", glyph: "reward_merit", value: reward.merit, unit: "功績" });
  }
  for (const item of reward.items ?? []) {
    cells.push({ kind: "item", glyph: "reward_item", key: item.item_key, name: item.display_name, quantity: item.quantity });
  }
  return { cells, settlement: SETTLEMENT_NOTES[row.settlement] ?? null };
}

// The detail view model of one book row. Null-sourced sections are omitted
// (rationale, reward) or carry a fixed fallback (issuer letter, deadline).
export function bookDetail(row) {
  const category = CATEGORY_LABELS[row.category] ?? null;
  const privateCommission = row.issuer?.kind !== "guild";
  let progress = null;
  if (row.state === "in_progress") {
    const target = row.objective_quantity;
    progress = {
      stage: row.stage_index + 1,
      stages: row.stage_total,
      value: row.stage_progress,
      target,
      mode: target <= PIP_LIMIT ? "pips" : "bar",
      pct: percent(row.stage_progress, target),
    };
  }
  const STAMPS = { completed: { kind: "completed", label: "達成" }, failed: { kind: "failed", label: "失敗" } };
  return {
    id: row.quest_id,
    name: row.display_name,
    state: row.state,
    ribbon: {
      glyph: categoryGlyph(row.category),
      label: category ? (privateCommission ? `${category} · 私人委託` : `${category}委託`) : privateCommission ? "私人委託" : "委託",
    },
    objective: row.objective_line,
    note: row.objective_note ?? null,
    grade: row.grade ?? null,
    stamp: STAMPS[row.state] ?? null,
    progress,
    rationale: row.rationale ?? null,
    deadline: row.deadline_line
      ? { line: row.deadline_line, note: "超過期限即判定失敗。", open: false }
      : { line: "無期限", note: "這份委託沒有時間限制。", open: true },
    issuer: {
      kind: row.issuer?.kind ?? null,
      label: row.issuer?.label ?? "",
      letter: row.flavor ?? null,
      fallback: row.flavor ? null : "委託人沒有留下說明。",
    },
    reward: rewardView(row),
  };
}

function mirrored(descriptor, questId) {
  return { action_id: descriptor.action_id, label: descriptor.label, payload: { quest_id: questId } };
}

// The action bar (design §3.8). Tracking renders for in-progress rows from
// the row's own descriptor; abandon and turn-in render only from the matched
// counter row's enabled descriptor. A row without an enabled action states
// why, from the counter's reason first.
export function bookActions(row, counterRow) {
  const result = { track: null, abandon: null, turnin: null, reason: null };
  if (!row) return result;
  if (row.state === "in_progress") {
    if (row.track) {
      const tracked = row.tracked === true;
      result.track = {
        enabled: row.track.enabled === true,
        pressed: tracked,
        label: tracked ? "追蹤中" : (row.track.label ?? "追蹤"),
        action_id: row.track.action_id,
        payload: { quest_id: row.quest_id, tracked: !tracked },
        reason: row.track.enabled ? null : (row.track.disabled_reason?.message ?? null),
      };
    }
    const abandon = counterRow?.abandon;
    if (abandon?.enabled) {
      result.abandon = mirrored(abandon, row.quest_id);
    } else if (abandon) {
      result.reason = abandon.disabled_reason?.message ?? null;
    }
    if (!result.reason && result.track?.reason) result.reason = result.track.reason;
    return result;
  }
  if (row.state === "completed") {
    const turnin = counterRow?.turnin;
    if (turnin?.enabled) {
      result.turnin = mirrored(turnin, row.quest_id);
    } else if (turnin?.disabled_reason?.message) {
      result.reason = turnin.disabled_reason.message;
    } else if (row.reward_claimed === true) {
      result.reason = REASON_CLAIMED;
    } else if (row.settlement === "counter" && row.reward_claimed === false && row.reward) {
      result.reason = REASON_RETURN_TO_COUNTER;
    }
    return result;
  }
  if (row.state === "failed") result.reason = REASON_FAILED;
  return result;
}
