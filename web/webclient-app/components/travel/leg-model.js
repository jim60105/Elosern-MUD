// The leg panel's pure projection (OpenSpec change wilderness-travel-leg-ui;
// interface design §7). No Vue, no DOM, no rules: every value comes from the
// supplied committed facts — the aim's committed exit row, the server's
// travel capacity and neighbour quotes (status v6), a `travel.plan` result
// once planning-ui supplies one, the walking queue, the persisted travel
// preferences, the supplied light phase and the committed world time. It
// never predicts fatigue, eligibility or duration and never advances time.

import { BUCKET_LABELS, STAGE_BUCKETS, bucketRank, stageDisplay } from "./stage-display.js";

/** The persisted pace values, in radio order (mirrored by layout_store.js). */
export const TRAVEL_PACES = Object.freeze(["cautious", "standard", "forced"]);

/** The radio options: label and the one-line hint each control describes. */
export const PACE_OPTIONS = Object.freeze([
  Object.freeze({ key: "cautious", label: "保守", hint: "出現輕度疲勞就停下" }),
  Object.freeze({ key: "standard", label: "標準", hint: "出現中度疲勞才停下" }),
  Object.freeze({ key: "forced", label: "強行", hint: "不因疲勞停下" }),
]);

export const DEFAULT_TRAVEL_PREFERENCES = Object.freeze({ pace: "standard", stopAtNight: true });

/** The display bucket each pace stops at (forced has no voluntary stop). */
const PACE_STOP_BUCKET = Object.freeze({ cautious: "light", standard: "moderate", forced: null });

/** The stop reason a plan's `stop_reason` is told as (design §7 legend). */
export const STOP_TEXT = Object.freeze({
  pace_threshold: "依節制在此紮營",
  nightfall: "入夜即停",
  member_asleep: "精力不足以再走",
  preflight_refused: "精力不足以再走",
  destination_reached: "抵達目的地",
});

/** The capacity legend's pace stop (the camp line on the estimate). */
export const CAPACITY_STOP_TEXT = "依節制紮營";

/** At most this many ticks are drawn; the legend keeps the exact counts. */
export const MAX_GAUGE_TICKS = 60;

const STALE_MAP = new Set(["unavailable", "invalid", "retired"]);
/** Each disabled state's code and the reason it is told as. */
const REASONS = Object.freeze({
  walking: "行進中無法變更",
  moving: "行進中",
  stale: "地圖尚未更新",
  no_plan: "尚未鎖定路線",
  capacity_pending: "正在估算腳程",
  capacity_unavailable: "無法估算腳程",
  busy: "上一個行動尚未完成，請稍候。",
});
const SLEEP_TICK_LABEL = "力竭倒下";

function pad(n) {
  return String(n).padStart(2, "0");
}

/** The structured quote of one neighbour step: instant, minutes or unknown. */
export function stepQuote(seconds) {
  if (seconds === 0) return Object.freeze({ kind: "instant", minutes: 0 });
  if (Number.isInteger(seconds) && seconds > 0) return Object.freeze({ kind: "minutes", minutes: Math.max(1, Math.round(seconds / 60)) });
  return Object.freeze({ kind: "unknown", minutes: null });
}

/** The stop clock `seconds` after the committed time: `{hour, minute, dayOffset}` or null. */
export function stopClock(serverTime, seconds) {
  if (!serverTime || !Number.isInteger(serverTime.hour) || !Number.isInteger(serverTime.minute)) return null;
  const start = serverTime.hour * 3600 + serverTime.minute * 60 + (Number.isInteger(serverTime.second) ? serverTime.second : 0);
  const at = start + Math.max(0, seconds);
  const inDay = at % 86400;
  return Object.freeze({ hour: Math.floor(inDay / 3600), minute: Math.floor((inDay % 3600) / 60), dayOffset: Math.floor(at / 86400) });
}

/** "N 小時 M 分" (minutes rounded up) for a positive duration in seconds. */
export function formatDuration(seconds) {
  const minutes = Math.ceil(Math.max(0, seconds) / 60);
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h && m) return `${h} 小時 ${m} 分`;
  if (h) return `${h} 小時`;
  return `${m} 分`;
}

/**
 * The clock `seconds` after the committed world time, as "HH:MM" (with 隔天
 * when it falls on a later day). Display only: no time is advanced.
 */
export function clockAfter(serverTime, seconds) {
  const clock = stopClock(serverTime, seconds);
  if (!clock) return null;
  const text = `${pad(clock.hour)}:${pad(clock.minute)}`;
  return clock.dayOffset > 0 ? `隔天 ${text}` : text;
}

/** A neighbour step's quote as words. */
export function quoteText(quote) {
  if (quote.kind === "instant") return "轉眼即至";
  if (quote.kind === "minutes") return `約 ${quote.minutes} 分鐘`;
  return "所需時間未明";
}

function capacityState(capacity) {
  if (capacity === undefined) return "pending";
  if (capacity === null || typeof capacity !== "object" || !capacity.capacity) return "unavailable";
  return "ready";
}

function capacityTotal(capacity) {
  return STAGE_BUCKETS.reduce((sum, bucket) => sum + (capacity.capacity[bucket] || 0), 0);
}

function validPlan(plan) {
  return !!plan && Array.isArray(plan.steps) && plan.steps.length > 0 && Number.isInteger(plan.stop_index);
}

function quoteFor(capacity, exitRef) {
  if (capacityState(capacity) !== "ready" || !Array.isArray(capacity.neighbours) || !exitRef) return undefined;
  const quote = capacity.neighbours.find((n) => n.exit_ref === exitRef);
  return quote ? quote.seconds : undefined;
}

function planTicks(plan, progress, labels) {
  return plan.steps.map((step, index) => {
    const display = stageDisplay(step.fatigue_stage) ?? { bucket: "normal", sleep: false };
    return Object.freeze({
      stage: step.fatigue_stage,
      bucket: display.bucket,
      sleep: display.sleep,
      label: display.sleep ? labels.forced_sleep ?? SLEEP_TICK_LABEL : BUCKET_LABELS[display.bucket],
      done: index < progress,
      beyond: index > plan.stop_index,
      night: Number.isInteger(plan.nightfall_index) && index >= plan.nightfall_index,
      moon: index === plan.nightfall_index,
      camp: index === plan.stop_index && plan.stop_reason !== "destination_reached",
    });
  });
}

function capacityTicks(capacity, pace) {
  const ticks = [];
  for (const bucket of STAGE_BUCKETS) {
    for (let i = 0; i < capacity.capacity[bucket]; i += 1) {
      ticks.push({ stage: bucket, bucket, sleep: false, label: BUCKET_LABELS[bucket], done: false, beyond: false, night: false, moon: false, camp: false });
    }
  }
  const stopBucket = PACE_STOP_BUCKET[pace] ?? null;
  const stopAt = stopBucket ? ticks.findIndex((t) => bucketRank(t.bucket) >= bucketRank(stopBucket)) : -1;
  if (stopAt >= 0) {
    ticks[stopAt].camp = true;
    for (let i = stopAt + 1; i < ticks.length; i += 1) ticks[i].beyond = true;
  }
  return { ticks: ticks.map((t) => Object.freeze(t)), stopAt };
}

function intentFor(s) {
  if (s.stale) {
    return { kind: "stale", title: "地圖尚未更新", detail: "等待下一份地圖，行程暫停" };
  }
  if (s.error?.message || s.error?.kind) {
    return {
      kind: s.error.kind === "refused" ? "refused" : "blocked",
      title: "無法前進",
      detail: s.error.message || "這一步沒有走出去",
    };
  }
  if (s.walking || s.holding) {
    const walk = s.walking;
    const route = walk?.kind === "route" && s.plan;
    const title = route
      ? `前往${s.plan.label || "目的地"}`
      : `朝${walk?.word || s.aim?.word || ""}前進`;
    const progress = walk && walk.progress > 0 ? `・已走 ${walk.progress} 步` : "";
    return { kind: "walking", title, detail: `行進中・任意鍵停步${progress}` };
  }
  if (s.aim) {
    if (s.aim.enabled) {
      const quote = stepQuote(quoteFor(s.capacity, s.aim.exitRef));
      return { kind: "aim", title: `瞄準${s.aim.word}・一步`, detail: `${quoteText(quote)}・Enter 前進`, quote };
    }
    return { kind: "blocked", title: `瞄準${s.aim.word}`, detail: s.aim.reason || "無法通行" };
  }
  if (s.plan) {
    const steps = s.plan.stop_index + 1;
    const clock = clockAfter(s.serverTime, s.plan.total_seconds);
    const parts = [`${steps} 步`, formatDuration(s.plan.total_seconds)];
    if (clock) parts.push(`${clock} 停`);
    return {
      kind: "plan",
      title: `前往${s.plan.label || "目的地"}`,
      detail: parts.join("・"),
      leg: Object.freeze({
        steps,
        minutes: Math.ceil(Math.max(0, s.plan.total_seconds) / 60),
        stop: stopClock(s.serverTime, s.plan.total_seconds),
      }),
    };
  }
  // A sleeper zeroes the capacity because nobody may walk, not because the
  // party is spent; a possessing owner's sleeping body alone does not.
  if (s.asleep && s.capacityState === "ready" && capacityTotal(s.capacity) === 0) {
    return { kind: "asleep", title: "有同伴正在沉睡", detail: "等待甦醒，或紮營休息" };
  }
  if (s.capacityState === "ready" && s.capacity.at_pace?.[s.pace] === true) {
    return { kind: "advice", title: "已到今天的節制門檻", detail: "建議紮營" };
  }
  if (s.phase === "night" && s.stopAtNight) {
    return { kind: "night", title: "夜裡只看得見身邊", detail: "建議紮營到天亮" };
  }
  let detail = "方向鍵瞄準・Enter 前進一步";
  let total = null;
  if (s.capacityState === "ready") {
    total = capacityTotal(s.capacity);
    detail = total > 0 ? `腳程還夠走約 ${total} 格・方向鍵瞄準` : "精力已不足以再走";
  } else if (s.capacityState === "pending") {
    detail = "正在估算腳程…";
  }
  return { kind: "idle", title: "選擇相鄰的一格", detail, capacity: total };
}

/**
 * The leg panel view: `{ intent, gauge, legend, controls, actions }`.
 *
 * - `aim`: the published aim target (`{direction, word, enabled, reason,
 *   exitRef}`) or null.
 * - `plan`/`locked`: a `travel.plan` result and whether it is the locked
 *   current one (planning-ui); absence is the working no-plan state.
 * - `walking`/`holding`/`progress`: the store's walking queue.
 * - `capacity`: the status v6 `travel_capacity` object, null when the
 *   server supplies none, undefined while no status is committed.
 * - `preferences`: `{pace, stopAtNight}`; `phase`: the supplied light phase
 *   or null; `error`: the queue's notice; `serverTime`: the committed time.
 * - `mapStatus`: the stage map's status; a failed read disables the panel
 *   but never 停步. `busy`: the dispatch gate is closed.
 * - `labels`: optional supplied stage labels (`forced_sleep`).
 * - `asleep`: a committed status fatigue row is asleep; with a zero
 *   capacity the intent then says a companion sleeps instead of reading the
 *   zero as exhaustion.
 */
export function legView({
  aim = null,
  plan = null,
  locked = false,
  walking = null,
  holding = false,
  progress = 0,
  capacity,
  preferences = DEFAULT_TRAVEL_PREFERENCES,
  phase = null,
  error = null,
  serverTime = null,
  mapStatus = "ready",
  busy = false,
  labels = {},
  asleep = false,
} = {}) {
  const pace = TRAVEL_PACES.includes(preferences?.pace) ? preferences.pace : DEFAULT_TRAVEL_PREFERENCES.pace;
  const stopAtNight = typeof preferences?.stopAtNight === "boolean" ? preferences.stopAtNight : DEFAULT_TRAVEL_PREFERENCES.stopAtNight;
  const usablePlan = validPlan(plan) ? plan : null;
  const state = {
    aim, plan: usablePlan, walking, holding, capacity, pace, stopAtNight, phase, error, serverTime, asleep: !!asleep,
    stale: STALE_MAP.has(mapStatus),
    capacityState: capacityState(capacity),
  };
  const moving = !!walking || !!holding;

  // ── gauge and legend ──
  let gauge;
  let legend;
  if (usablePlan) {
    const ticks = planTicks(usablePlan, Math.max(0, progress | 0), labels);
    const counts = Object.fromEntries(STAGE_BUCKETS.map((b) => [b, 0]));
    ticks.forEach((t, i) => {
      if (i <= usablePlan.stop_index) counts[t.bucket] += 1;
    });
    gauge = { source: "plan", ticks: ticks.slice(0, MAX_GAUGE_TICKS), hidden: Math.max(0, ticks.length - MAX_GAUGE_TICKS) };
    legend = {
      caption: "今日行程",
      entries: STAGE_BUCKETS.filter((b) => counts[b] > 0).map((b) => ({ bucket: b, label: BUCKET_LABELS[b], count: counts[b] })),
      stop: STOP_TEXT[usablePlan.stop_reason] ?? null,
      stopReason: usablePlan.stop_reason ?? null,
    };
  } else if (state.capacityState === "ready") {
    const { ticks, stopAt } = capacityTicks(capacity, pace);
    gauge = { source: "capacity", ticks: ticks.slice(0, MAX_GAUGE_TICKS), hidden: Math.max(0, ticks.length - MAX_GAUGE_TICKS) };
    legend = {
      caption: "腳程估計",
      entries: STAGE_BUCKETS.filter((b) => capacity.capacity[b] > 0).map((b) => ({ bucket: b, label: BUCKET_LABELS[b], count: capacity.capacity[b] })),
      // The capacity gauge marks where the chosen pace would camp.
      stop: stopAt >= 0 ? CAPACITY_STOP_TEXT : null,
      stopReason: stopAt >= 0 ? "pace_threshold" : null,
    };
  } else {
    gauge = { source: state.capacityState, ticks: [], hidden: 0 };
    legend = { caption: "腳程估計", entries: [], stop: null, stopReason: null };
  }
  const total = legend.entries.reduce((sum, e) => sum + e.count, 0);
  let summary;
  if (gauge.source === "pending") summary = "正在估算腳程";
  else if (gauge.source === "unavailable") summary = "無法估算腳程";
  else {
    const parts = legend.entries.map((e) => `${e.label} ${e.count} 格`);
    summary = `${legend.caption}：${total > 0 ? parts.join("、") : "已無法再走"}${legend.stop ? `，${legend.stop}` : ""}`;
  }
  gauge = Object.freeze({ ...gauge, summary });

  const controlsCode = moving ? "walking" : state.stale ? "stale" : null;
  const controls = Object.freeze({
    pace, stopAtNight, enabled: controlsCode === null, code: controlsCode, reason: REASONS[controlsCode] ?? null,
  });

  // ── actions ──
  let primary;
  if (moving) {
    primary = { kind: "stop", label: "停步", hint: "任意鍵", enabled: true, code: null, reason: null };
  } else {
    let code = null;
    if (state.stale) code = "stale";
    else if (!usablePlan || !locked) code = "no_plan";
    else if (state.capacityState !== "ready") code = `capacity_${state.capacityState}`;
    else if (busy) code = "busy";
    primary = { kind: "depart", label: "出發", hint: "Enter", enabled: code === null, code, reason: REASONS[code] ?? null };
  }
  const sideCode = moving ? "moving" : state.stale ? "stale" : busy ? "busy" : null;
  const side = Object.freeze({ enabled: sideCode === null, code: sideCode, reason: REASONS[sideCode] ?? null });
  const actions = Object.freeze({
    primary: Object.freeze(primary),
    camp: side,
    look: side,
  });

  return Object.freeze({
    intent: Object.freeze(intentFor(state)),
    gauge,
    legend: Object.freeze(legend),
    controls,
    actions,
  });
}
