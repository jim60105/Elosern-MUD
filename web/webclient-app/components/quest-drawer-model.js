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
// - The guild board reads grades only from the guild section's
//   `rank_ladder` and the holder's rank (quest-drawer-guild-board-tab).
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

const ISSUER_FALLBACK = "委託人沒有留下說明。";

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

function rewardView(row, settlement = row.settlement) {
  const reward = row.reward;
  if (!reward) return null;
  const cells = [{ kind: "copper", glyph: "reward_copper", value: reward.copper, unit: "銅" }];
  if (reward.merit > 0) {
    cells.push({ kind: "merit", glyph: "reward_merit", value: reward.merit, unit: "功績" });
  }
  for (const item of reward.items ?? []) {
    cells.push({ kind: "item", glyph: "reward_item", key: item.item_key, name: item.display_name, quantity: item.quantity });
  }
  return { cells, settlement: SETTLEMENT_NOTES[settlement] ?? null };
}

function deadlineView(line) {
  return line
    ? { line, note: "超過期限即判定失敗。", open: false }
    : { line: "無期限", note: "這份委託沒有時間限制。", open: true };
}

function issuerView(kind, label, flavor) {
  return { kind, label, letter: flavor ?? null, fallback: flavor ? null : ISSUER_FALLBACK };
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
    kind: "book",
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
    condition: null,
    rationale: row.rationale ?? null,
    deadline: deadlineView(row.deadline_line),
    issuer: issuerView(row.issuer?.kind ?? null, row.issuer?.label ?? "", row.flavor),
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
  const result = { track: null, abandon: null, turnin: null, accept: null, reason: null };
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

// ── The guild board (quest-drawer-guild-board-tab) ──────────────────────
// Grades come only from the guild section's `rank_ladder` and the holder's
// rank; the client encodes no grade order or rank rule of its own.

export const GRADE_REASON_OWN = "你的等級";
export const GRADE_REASON_LOCKED = "尚未開放";
export const OFFER_SETTLEMENT = "counter";

export const lockedGradeLine = (grade) => `${grade} 級委託要等你的公會等級提升後才會開放。`;
export const emptyGradeLine = (grade) => `目前沒有 ${grade} 級委託。`;

// The holder's rank as the services panel's player summary states it.
export function holderRank(services) {
  return services?.player?.guild_rank ?? null;
}

// Board rows grouped under every ladder key, in ladder order; panel order is
// kept within a grade. A row whose grade is not on the ladder is dropped.
export function offersByGrade(board, ladder) {
  const groups = Object.fromEntries((ladder ?? []).map((grade) => [grade, []]));
  for (const row of board ?? []) {
    groups[row?.rank]?.push(row);
  }
  return groups;
}

// A grade is locked above the holder's rank. A rank missing from the ladder
// locks nothing (the server still lists only eligible offers).
export function gradeLocked(ladder, rank, grade) {
  const holder = (ladder ?? []).indexOf(rank);
  return holder >= 0 && ladder.indexOf(grade) > holder;
}

// The memory basis a remembered grade belongs to: the ladder and the
// holder's rank. A change in either drops the remembered grade.
export function boardBasis(ladder, rank) {
  return `${(ladder ?? []).join(",")}|${rank ?? ""}`;
}

// The highest grade at or below the holder's rank that has offers, else the
// holder's own grade. Without a ladder rank: the highest grade with offers,
// else the first grade.
export function defaultGrade(ladder, rank, groups) {
  const keys = ladder ?? [];
  const holder = keys.indexOf(rank);
  const top = holder >= 0 ? holder : keys.length - 1;
  for (let index = top; index >= 0; index -= 1) {
    if (groups[keys[index]]?.length > 0) return keys[index];
  }
  return holder >= 0 ? rank : (keys[0] ?? null);
}

// The grade rail's IconTabs entries. A locked grade shows no count and is not
// dimmed, so it never implies hidden offers; it stays selectable.
export function gradeTabs(ladder, rank, groups) {
  return (ladder ?? []).map((grade) => {
    const locked = gradeLocked(ladder, rank, grade);
    const count = groups[grade]?.length ?? 0;
    const own = grade === rank;
    return {
      key: grade,
      label: `${grade} 級`,
      count: locked ? undefined : count,
      mark: own,
      dim: !locked && count === 0,
      locked,
      reason: own ? GRADE_REASON_OWN : locked ? GRADE_REASON_LOCKED : undefined,
    };
  });
}

function guildSummary(deadline) {
  return deadline ? `公會委託 · ${deadline}` : "公會委託";
}

export function offerListRow(row) {
  return {
    id: row.definition_key,
    name: row.display_name,
    state: "offer",
    glyph: categoryGlyph(row.category),
    tracked: false,
    grade: row.rank ?? null,
    progress: null,
    sub: guildSummary(row.deadline_line),
  };
}

// The offer detail: the book detail's layout without progress or stamp, the
// acceptance condition in place of the rationale cell, the branch as the
// commissioner, and the reward settled at the counter.
export function offerDetail(row, branchLabel) {
  const category = CATEGORY_LABELS[row.category] ?? null;
  return {
    kind: "offer",
    id: row.definition_key,
    name: row.display_name,
    state: "offer",
    ribbon: { glyph: categoryGlyph(row.category), label: category ? `${category}委託` : "委託" },
    objective: row.objective_summary,
    note: row.objective_note ?? null,
    grade: row.rank ?? null,
    stamp: null,
    progress: null,
    condition: { line: `公會等級 ${row.rank} 級以上`, text: row.rationale ?? null },
    rationale: null,
    deadline: deadlineView(row.deadline_line),
    issuer: issuerView("guild", branchLabel ?? "", row.flavor),
    reward: rewardView(row, OFFER_SETTLEMENT),
  };
}

// The offer's accept descriptor as the primary action; a disabled one keeps
// its control (aria-disabled) and states its reason.
export function offerActions(row) {
  const result = { track: null, abandon: null, turnin: null, accept: null, reason: null };
  const accept = row?.accept;
  if (!accept) return result;
  result.accept = {
    enabled: accept.enabled === true,
    label: accept.label,
    action_id: accept.action_id,
    payload: { definition_key: row.definition_key },
  };
  if (!result.accept.enabled) result.reason = accept.disabled_reason?.message ?? null;
  return result;
}
