// The leg panel (wilderness-travel-leg-ui, task 3.1): the pure `legView`
// projection with independent literal expectations, and the mounted panel
// in the live shell — the gauge from the server's capacity, the persisted
// pace radio and nightfall switch, and the guarded 環顧, 紮營, 出發 and 停步.

import { afterEach, describe, expect, it, vi } from "vitest";
import { legView, MAX_GAUGE_TICKS } from "../../components/travel/leg-model.js";
import { stageDisplay } from "../../components/travel/stage-display.js";
import { liveTravel, tick, walkArea, walkCapacity, walkPanels } from "./support.js";

vi.setConfig({ testTimeout: 60000 });

const CAPACITY = {
  capacity: { normal: 2, light: 1, moderate: 1, severe: 1 },
  neighbours: [
    { exit_ref: "e_east", seconds: 1200 },
    { exit_ref: "e_fly", seconds: 0 },
    { exit_ref: "e_hidden", seconds: null },
  ],
  at_pace: { cautious: false, standard: false },
};
const AIM = { direction: "east", word: "東方", enabled: true, reason: null, exitRef: "e_east" };
const PLAN = {
  steps: [
    { cell: { x: 1, y: 0 }, seconds: 1200, fatigue_stage: "normal" },
    { cell: { x: 2, y: 0 }, seconds: 1200, fatigue_stage: "light" },
    { cell: { x: 3, y: 0 }, seconds: 1500, fatigue_stage: "moderate" },
    { cell: { x: 4, y: 0 }, seconds: 1500, fatigue_stage: "severe" },
    { cell: { x: 5, y: 0 }, seconds: 2400, fatigue_stage: "forced_sleep" },
  ],
  total_seconds: 7800,
  nightfall_index: 2,
  stop_index: 4,
  stop_reason: "member_asleep",
  label: "灰石崗",
};
const NOON = { hour: 12, minute: 0, second: 0 };

describe("the intent line follows the documented precedence", () => {
  const all = {
    mapStatus: "unavailable",
    error: { kind: "refused", message: "前方的河水太深。" },
    walking: { kind: "direction", direction: "east", word: "東方", progress: 2 },
    aim: AIM,
    plan: PLAN,
    capacity: { ...CAPACITY, at_pace: { cautious: true, standard: true } },
    phase: "night",
    preferences: { pace: "standard", stopAtNight: true },
    serverTime: NOON,
  };
  const order = [
    ["mapStatus", "ready", "stale"],
    ["error", null, "refused"],
    ["walking", null, "walking"],
    ["aim", null, "aim"],
    ["plan", null, "plan"],
    ["capacity", CAPACITY, "advice"],
    ["phase", "day", "night"],
  ];

  it("selects each state only once every higher one is gone", () => {
    let input = { ...all };
    for (const [field, cleared, expected] of order) {
      expect(legView(input).intent.kind).toBe(expected);
      input = { ...input, [field]: cleared };
    }
    expect(legView(input).intent.kind).toBe("idle");
  });

  it("the night advisory needs the supplied night phase and the nightfall stop", () => {
    const base = { capacity: CAPACITY, phase: "night" };
    expect(legView({ ...base, preferences: { pace: "standard", stopAtNight: true } }).intent.title).toBe("夜裡只看得見身邊");
    expect(legView({ ...base, preferences: { pace: "standard", stopAtNight: false } }).intent.kind).toBe("idle");
    expect(legView({ ...base, phase: null }).intent.kind).toBe("idle");
  });

  it("the pace threshold reads only the chosen pace's supplied flag", () => {
    const capacity = { ...CAPACITY, at_pace: { cautious: true, standard: false } };
    expect(legView({ capacity, preferences: { pace: "cautious", stopAtNight: false } }).intent.kind).toBe("advice");
    expect(legView({ capacity, preferences: { pace: "standard", stopAtNight: false } }).intent.kind).toBe("idle");
    expect(legView({ capacity, preferences: { pace: "forced", stopAtNight: false } }).intent.kind).toBe("idle");
  });

  it("an aim quotes its own row's supplied minutes, or none", () => {
    const quote = (exitRef) => legView({ aim: { ...AIM, exitRef }, capacity: CAPACITY }).intent.detail;
    expect(legView({ aim: AIM, capacity: CAPACITY }).intent.title).toBe("瞄準東方・一步");
    expect(quote("e_east")).toMatch(/^約 20 分鐘/);
    expect(quote("e_fly")).toMatch(/^轉眼即至/);
    // A withheld destination (null) and a row without a quote are unknown,
    // never zero minutes.
    expect(quote("e_hidden")).toMatch(/^所需時間未明/);
    expect(quote("e_other")).toMatch(/^所需時間未明/);
    expect(legView({ aim: AIM, capacity: null }).intent.detail).toMatch(/^所需時間未明/);
    const blocked = legView({ aim: { ...AIM, enabled: false, reason: "斷崖擋住了去路。" } }).intent;
    expect([blocked.kind, blocked.detail]).toEqual(["blocked", "斷崖擋住了去路。"]);
    expect(legView({ aim: { ...AIM, enabled: false, reason: null } }).intent.detail).toBe("無法通行");
  });

  it("a plan states its steps, total duration and stop clock from committed time", () => {
    const intent = legView({ plan: PLAN, serverTime: NOON }).intent;
    expect(intent.title).toBe("前往灰石崗");
    // stop_index 4 → 5 steps; 7800 s = 2 h 10 min after 12:00.
    expect(intent.detail).toBe("5 步・2 小時 10 分・14:10 停");
    const late = legView({ plan: PLAN, serverTime: { hour: 22, minute: 30, second: 0 } }).intent;
    expect(late.detail).toBe("5 步・2 小時 10 分・隔天 00:40 停");
  });
});

describe("the gauge", () => {
  it("draws the server's capacity by stage with the pace's stop marked", () => {
    const view = legView({ capacity: CAPACITY, preferences: { pace: "standard", stopAtNight: true } });
    expect(view.gauge.source).toBe("capacity");
    expect(view.gauge.ticks.map((t) => t.bucket)).toEqual(["normal", "normal", "light", "moderate", "severe"]);
    // Standard stops at the first moderate step; the rest lies beyond it.
    expect(view.gauge.ticks.map((t) => t.camp)).toEqual([false, false, false, true, false]);
    expect(view.gauge.ticks.map((t) => t.beyond)).toEqual([false, false, false, false, true]);
    expect(view.legend.entries.map((e) => [e.bucket, e.count])).toEqual([["normal", 2], ["light", 1], ["moderate", 1], ["severe", 1]]);
    expect(view.legend.stop).toBe("依節制紮營");

    const cautious = legView({ capacity: CAPACITY, preferences: { pace: "cautious", stopAtNight: true } });
    expect(cautious.gauge.ticks.findIndex((t) => t.camp)).toBe(2);
    const forced = legView({ capacity: CAPACITY, preferences: { pace: "forced", stopAtNight: true } });
    expect(forced.gauge.ticks.some((t) => t.camp || t.beyond)).toBe(false);
    expect(forced.legend.stop).toBeNull();
  });

  it("states pending and unavailable capacity explicitly", () => {
    const pending = legView({});
    expect([pending.gauge.source, pending.gauge.ticks.length, pending.gauge.summary]).toEqual(["pending", 0, "正在估算腳程"]);
    const none = legView({ capacity: null });
    expect([none.gauge.source, none.gauge.summary]).toEqual(["unavailable", "無法估算腳程"]);
    const spent = legView({ capacity: { ...CAPACITY, capacity: { normal: 0, light: 0, moderate: 0, severe: 0 } } });
    expect(spent.gauge.ticks).toEqual([]);
    expect(spent.intent.detail).toBe("精力已不足以再走");
  });

  it("follows a supplied plan's stages with spent, night, moon and camp ticks", () => {
    const view = legView({ plan: PLAN, progress: 2, capacity: CAPACITY });
    expect(view.gauge.source).toBe("plan");
    const ticks = view.gauge.ticks;
    expect(ticks.map((t) => t.stage)).toEqual(["normal", "light", "moderate", "severe", "forced_sleep"]);
    expect(ticks.map((t) => t.done)).toEqual([true, true, false, false, false]);
    expect(ticks.map((t) => t.moon)).toEqual([false, false, true, false, false]);
    expect(ticks.map((t) => t.night)).toEqual([false, false, true, true, true]);
    // The canonical forced_sleep step keeps its enum, is drawn in the severe
    // bucket with the crescent and carries the sleep label.
    expect([ticks[4].bucket, ticks[4].sleep, ticks[4].label, ticks[4].camp]).toEqual(["severe", true, "力竭倒下", true]);
    expect(legView({ plan: PLAN, labels: { forced_sleep: "倒地昏睡" } }).gauge.ticks[4].label).toBe("倒地昏睡");
    expect(view.legend.entries.map((e) => [e.bucket, e.count])).toEqual([["normal", 1], ["light", 1], ["moderate", 1], ["severe", 2]]);
    expect(view.legend.stop).toBe("精力不足以再走");
  });

  it("an exact-zero plan is one severe sleep tick; an arrival has no camp line", () => {
    const zero = legView({
      plan: { steps: [{ cell: { x: 1, y: 0 }, seconds: 2400, fatigue_stage: "forced_sleep" }], total_seconds: 2400, nightfall_index: null, stop_index: 0, stop_reason: "member_asleep" },
    });
    expect(zero.gauge.ticks.map((t) => [t.stage, t.bucket, t.sleep, t.camp])).toEqual([["forced_sleep", "severe", true, true]]);
    const arrival = legView({ plan: { ...PLAN, stop_reason: "destination_reached" } });
    expect(arrival.gauge.ticks.some((t) => t.camp)).toBe(false);
    expect(arrival.legend.stop).toBe("抵達目的地");
    // Steps past the stop are drawn beyond it and left out of the counts.
    const short = legView({ plan: { ...PLAN, stop_index: 1, stop_reason: "pace_threshold" } });
    expect(short.gauge.ticks.map((t) => t.beyond)).toEqual([false, false, true, true, true]);
    expect(short.legend.entries.map((e) => [e.bucket, e.count])).toEqual([["normal", 1], ["light", 1]]);
  });

  it("draws at most the bounded tick count while the legend keeps exact counts", () => {
    const big = { ...CAPACITY, capacity: { normal: 50, light: 30, moderate: 0, severe: 0 } };
    const view = legView({ capacity: big });
    expect(view.gauge.ticks).toHaveLength(MAX_GAUGE_TICKS);
    expect(view.gauge.hidden).toBe(80 - MAX_GAUGE_TICKS);
    expect(view.legend.entries.map((e) => e.count)).toEqual([50, 30]);
  });

  it("maps each canonical stage to one display bucket", () => {
    expect(["normal", "light", "moderate", "severe", "forced_sleep", "sleeping", "x"].map(stageDisplay)).toEqual([
      { bucket: "normal", sleep: false },
      { bucket: "light", sleep: false },
      { bucket: "moderate", sleep: false },
      { bucket: "severe", sleep: false },
      { bucket: "severe", sleep: true },
      { bucket: "severe", sleep: true },
      null,
    ]);
  });
});

describe("controls and actions", () => {
  it("出發 needs a current locked plan, a supplied capacity and a live map", () => {
    const depart = (input) => legView(input).actions.primary;
    expect(depart({ capacity: CAPACITY })).toMatchObject({ kind: "depart", enabled: false, reason: "尚未鎖定路線" });
    expect(depart({ capacity: CAPACITY, plan: PLAN, locked: false }).enabled).toBe(false);
    expect(depart({ capacity: CAPACITY, plan: PLAN, locked: true }).enabled).toBe(true);
    expect(depart({ plan: PLAN, locked: true }).reason).toBe("正在估算腳程");
    expect(depart({ capacity: null, plan: PLAN, locked: true }).reason).toBe("無法估算腳程");
    expect(depart({ capacity: CAPACITY, plan: PLAN, locked: true, busy: true }).enabled).toBe(false);
    expect(depart({ capacity: CAPACITY, plan: PLAN, locked: true, mapStatus: "invalid" }).reason).toBe("地圖尚未更新");
    // A malformed plan is the working no-plan state.
    expect(depart({ capacity: CAPACITY, plan: { steps: [] }, locked: true }).reason).toBe("尚未鎖定路線");
  });

  it("a walk turns 出發 into an always-usable 停步 and freezes the preferences", () => {
    for (const mapStatus of ["ready", "refreshing", "unavailable"]) {
      const view = legView({ walking: { kind: "direction", word: "東方", progress: 0 }, mapStatus, capacity: undefined });
      expect(view.actions.primary).toMatchObject({ kind: "stop", enabled: true });
      expect(view.controls.enabled).toBe(false);
      expect(view.actions.camp.enabled).toBe(false);
      expect(view.actions.look.enabled).toBe(false);
    }
    expect(legView({ holding: true }).actions.primary.kind).toBe("stop");
  });

  it("a stale map disables everything but 停步; a refresh disables nothing", () => {
    const stale = legView({ capacity: CAPACITY, mapStatus: "retired" });
    expect([stale.controls.enabled, stale.actions.camp.enabled, stale.actions.look.enabled]).toEqual([false, false, false]);
    expect(stale.controls.reason).toBe("地圖尚未更新");
    const refreshing = legView({ capacity: CAPACITY, mapStatus: "refreshing" });
    expect([refreshing.controls.enabled, refreshing.actions.camp.enabled, refreshing.actions.look.enabled]).toEqual([true, true, true]);
  });
});

// ── the mounted panel ───────────────────────────────────────────────────

const CX = 60;
const CY = 80;
let wrappers = [];
afterEach(() => {
  vi.useRealTimers();
  for (const w of wrappers) w.unmount();
  wrappers = [];
  document.body.innerHTML = "";
  window.localStorage.clear();
}, 60000);

async function stage(capacity = walkCapacity()) {
  const h = liveTravel({ wrappers, panels: walkPanels(CX, CY, { capacity }) });
  await tick();
  await h.answerMap(walkArea(CX, CY));
  // Every fixture update carries the default status; commit the cell's own
  // status (with its travel capacity) again after the map.
  h.publish({ status: walkPanels(CX, CY, { capacity }).status });
  await tick();
  const panel = () => h.w.get('[data-testid="leg-panel"]');
  const sent = (id) => h.sender.sent.actions.filter((a) => a.action_id === id);
  return { ...h, panel, sent };
}

describe("the mounted leg panel", () => {
  it("draws the supplied capacity and quotes the aimed row", async () => {
    const s = await stage(walkCapacity({ normal: 3, light: 2, moderate: 1, severe: 1, quotes: { east: 1500 } }));
    expect(s.panel().attributes("data-gauge")).toBe("capacity");
    const ticks = s.w.findAll('[data-testid="leg-tick"]');
    expect(ticks.map((t) => t.attributes("data-bucket"))).toEqual(["normal", "normal", "normal", "light", "light", "moderate", "severe"]);
    expect(s.w.findAll('[data-testid="leg-camp-mark"]')).toHaveLength(1);
    expect(s.w.get('[data-testid="leg-gauge"]').attributes("aria-label")).toContain("中度 1 格");
    s.store.aimTravel("east");
    await tick();
    expect(s.w.get('[data-testid="leg-intent-detail"]').text()).toMatch(/^約 25 分鐘/);
  });

  it("the pace radio and nightfall switch persist through the store", async () => {
    const s = await stage();
    const standard = s.w.get('[data-testid="leg-pace-standard"]');
    expect(standard.attributes("aria-checked")).toBe("true");
    expect(standard.attributes("tabindex")).toBe("0");
    expect(s.w.get('[data-testid="leg-pace-forced"]').attributes("tabindex")).toBe("-1");
    standard.element.focus();
    await standard.trigger("keydown", { key: "ArrowRight" });
    await tick();
    expect(s.store.view.travel.preferences.pace).toBe("forced");
    expect(document.activeElement).toBe(s.w.get('[data-testid="leg-pace-forced"]').element);
    expect(s.w.get('[data-testid="leg-pace-forced"]').attributes("aria-checked")).toBe("true");
    const night = s.w.get('[data-testid="leg-night"]');
    expect(night.attributes("role")).toBe("switch");
    await night.trigger("click");
    await tick();
    expect(s.store.view.travel.preferences.stopAtNight).toBe(false);
    expect(night.attributes("aria-checked")).toBe("false");
    expect(JSON.parse(window.localStorage.getItem("elosern.layout")).preferences).toMatchObject({ travelPace: "forced", travelStopAtNight: false });
  });

  it("環顧 sends exactly the existing room look; 出發 sends nothing without a plan", async () => {
    const s = await stage();
    const depart = s.w.get('[data-testid="leg-depart"]');
    expect(depart.attributes("aria-disabled")).toBe("true");
    const before = s.sender.sent.actions.length;
    await depart.trigger("click");
    await tick();
    expect(s.sender.sent.actions.length).toBe(before);
    await s.w.get('[data-testid="leg-look"]').trigger("click");
    await tick();
    const looks = s.sent("explore.look");
    expect(looks).toHaveLength(1);
    expect(looks[0].payload).toEqual({ room: true });
  });

  it("紮營 opens the existing sleep form and closing it returns focus to 紮營", async () => {
    const s = await stage();
    const camp = s.w.get('[data-testid="leg-camp"]');
    camp.element.focus();
    await camp.trigger("click");
    await tick();
    expect(s.w.find('[data-testid="sleep-card"]').exists()).toBe(true);
    // No request leaves for opening it.
    expect(s.sender.sent.actions.filter((a) => a.action_id !== "map.view")).toHaveLength(0);
    s.store.closeRoomCard();
    await tick();
    await tick();
    expect(s.w.find('[data-testid="sleep-card"]').exists()).toBe(false);
    expect(document.activeElement).toBe(s.w.get('[data-testid="leg-camp"]').element);
  });

  it("while walking the preferences stay fixed and 停步 stays usable through a refresh", async () => {
    vi.useFakeTimers();
    const s = await stage();
    s.store.setTravelPace("cautious");
    s.store.holdTravel("east");
    vi.advanceTimersByTime(400);
    await tick();
    expect(s.store.view.travel.walking).not.toBeNull();
    const radio = s.w.get('[data-testid="leg-pace-standard"]');
    expect(radio.attributes("aria-disabled")).toBe("true");
    await radio.trigger("click");
    await s.w.get('[data-testid="leg-night"]').trigger("click");
    expect(s.store.view.travel.preferences).toEqual({ pace: "cautious", stopAtNight: true });
    s.store.setTravelMap({ status: "refreshing", area: s.store.view.travel.area });
    await tick();
    const stop = s.w.get('[data-testid="leg-stop"]');
    expect(stop.attributes("aria-disabled")).toBeUndefined();
    await stop.trigger("click");
    await tick();
    expect(s.store.view.travel.walking).toBeNull();
  });
});
