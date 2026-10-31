// The route preview (wilderness-travel-planning-ui, design "Preview and leg
// projection"): TravelMap and the leg projection draw a supplied synthetic
// `travel.plan` result exactly as sent. Each case states its expected marks
// independently (index by index), so nothing is derived from the code under
// test; the planner's own rules are never consulted.

import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import TravelMap from "../../components/travel/TravelMap.vue";
import { formatDuration, legView, routeSummary } from "../../components/travel/leg-model.js";
import { decodeTravelGrid } from "../../lib/travel-grid.js";
import { travelPaintStats } from "../../lib/travel-paint.js";
import { walkArea, walkCapacity } from "./support.js";

const CX = 60;
const CY = 80;
const GRID = decodeTravelGrid(walkArea(CX, CY, { reveal: 7 }));
const CAPACITY = walkCapacity();

const step = (dx, stage, seconds = 1200) => ({ cell: { x: CX + dx, y: CY }, seconds, fatigue_stage: stage });

// Every awake stage, nightfall at index 2, a voluntary stop at index 3 and
// two planned steps beyond it.
const FULL = Object.freeze({
  origin: { x: CX, y: CY },
  destination: { x: CX + 6, y: CY },
  steps: [step(1, "normal"), step(2, "light"), step(3, "moderate"), step(4, "severe"), step(5, "moderate"), step(6, "severe")],
  total_seconds: 4800,
  nightfall_index: 2,
  stop_index: 3,
  stop_reason: "pace_threshold",
});

// An admitted exact-zero arrival: the terminal forced_sleep step.
const SLEEP = Object.freeze({
  origin: { x: CX, y: CY },
  destination: { x: CX + 5, y: CY },
  steps: [step(1, "normal", 1200), step(2, "severe", 1500), step(3, "forced_sleep", 1740)],
  total_seconds: 4440,
  nightfall_index: null,
  stop_index: 2,
  stop_reason: "member_asleep",
});

const EMPTY = Object.freeze({
  origin: { x: CX, y: CY },
  destination: { x: CX, y: CY },
  steps: [],
  total_seconds: 0,
  nightfall_index: null,
  stop_index: null,
  stop_reason: "destination_reached",
});

// Manual animation frames and a no-op 2D context, so the component's own
// scheduling decides when the real painter runs.
let restore = () => {};
let frames = [];
beforeEach(() => {
  frames = [];
  const raf = globalThis.requestAnimationFrame;
  const caf = globalThis.cancelAnimationFrame;
  const getContext = HTMLCanvasElement.prototype.getContext;
  globalThis.requestAnimationFrame = (fn) => frames.push(fn);
  globalThis.cancelAnimationFrame = () => {};
  HTMLCanvasElement.prototype.getContext = function fake() {
    return new Proxy(
      { canvas: { width: this.width, height: this.height } },
      {
        get(target, key) {
          if (key in target) return target[key];
          if (key === "createImageData") return (w, h) => ({ width: w, height: h, data: new Uint8ClampedArray(w * h * 4) });
          if (key === "createRadialGradient" || key === "createLinearGradient") return () => ({ addColorStop: () => {} });
          return () => {};
        },
        set(target, key, value) {
          target[key] = value;
          return true;
        },
      },
    );
  };
  restore = () => {
    globalThis.requestAnimationFrame = raf;
    globalThis.cancelAnimationFrame = caf;
    HTMLCanvasElement.prototype.getContext = getContext;
  };
});
let wrappers = [];
afterEach(() => {
  for (const w of wrappers) w.unmount();
  wrappers = [];
  restore();
});

async function flush() {
  await nextTick();
  while (frames.length) frames.shift()();
  await nextTick();
}

async function mapWith(props) {
  const w = mount(TravelMap, { props: { grid: GRID, status: "ready", ...props }, attachTo: document.body });
  wrappers.push(w);
  await flush();
  return w;
}

const marks = (w) =>
  w.findAll('[data-testid="travel-map__route-step"]').map((g) => ({
    index: Number(g.attributes("data-index")),
    stage: g.attributes("data-stage"),
    bucket: g.attributes("data-bucket"),
    sleep: g.attributes("data-sleep") === "true",
    beyond: g.attributes("data-beyond") === "true",
    night: g.attributes("data-night") === "true",
  }));

describe("the map draws the supplied plan", () => {
  it("one stage mark per step, faint beyond the stop, dimmed from nightfall", async () => {
    const w = await mapWith({ plan: FULL, target: { x: CX + 6, y: CY, label: null, locked: false } });
    expect(marks(w)).toEqual([
      { index: 0, stage: "normal", bucket: "normal", sleep: false, beyond: false, night: false },
      { index: 1, stage: "light", bucket: "light", sleep: false, beyond: false, night: false },
      { index: 2, stage: "moderate", bucket: "moderate", sleep: false, beyond: false, night: true },
      { index: 3, stage: "severe", bucket: "severe", sleep: false, beyond: false, night: true },
      { index: 4, stage: "moderate", bucket: "moderate", sleep: false, beyond: true, night: true },
      { index: 5, stage: "severe", bucket: "severe", sleep: false, beyond: true, night: true },
    ]);
    expect(w.get('[data-testid="travel-map__route-moon"]').attributes("data-index")).toBe("2");
    expect(w.get('[data-testid="travel-map__route-camp"]').attributes("data-index")).toBe("3");
    // Each stage differs by shape: disc, diamond, ring, ring with a core.
    const glyph = (i) => w.findAll('[data-testid="travel-map__route-step"]')[i];
    expect(glyph(0).find("circle.travel-glyph__step").exists()).toBe(true);
    expect(glyph(1).find("path.travel-glyph__step").exists()).toBe(true);
    expect(glyph(2).find(".travel-glyph__ring").exists()).toBe(true);
    expect(glyph(2).find(".travel-glyph__core").exists()).toBe(false);
    expect(glyph(3).find(".travel-glyph__core").exists()).toBe(true);
    expect(glyph(4).find(".travel-glyph").classes()).toContain("is-faint");
    // A preview's destination is outlined; the route text describes the map.
    expect(w.get('[data-testid="travel-map__destination"]').attributes("data-locked")).toBe("false");
    const text = w.get('[data-testid="travel-map__route-text"]');
    expect(w.get('[data-testid="travel-map"]').attributes("aria-describedby")).toBe(text.attributes("id"));
  });

  it("an arrival has no camp mark and a lock draws the double frame", async () => {
    const w = await mapWith({
      plan: { ...FULL, nightfall_index: null, stop_index: 5, stop_reason: "destination_reached" },
      locked: true,
      target: { x: CX + 6, y: CY, label: null, locked: true },
    });
    expect(w.find('[data-testid="travel-map__route-camp"]').exists()).toBe(false);
    expect(w.find('[data-testid="travel-map__route-moon"]').exists()).toBe(false);
    expect(marks(w).every((m) => !m.beyond && !m.night)).toBe(true);
    expect(w.get('[data-testid="travel-map__destination"]').attributes("data-locked")).toBe("true");
    expect(w.findAll('[data-testid="travel-map__destination"] rect')).toHaveLength(2);
  });

  it("the terminal forced_sleep step keeps its stage and draws the severe ring with the crescent", async () => {
    const w = await mapWith({ plan: SLEEP, target: { x: CX + 3, y: CY, label: null, locked: true }, locked: true });
    const last = marks(w)[2];
    expect(last).toEqual({ index: 2, stage: "forced_sleep", bucket: "severe", sleep: true, beyond: false, night: false });
    const g = w.findAll('[data-testid="travel-map__route-step"]')[2];
    expect(g.find(".travel-glyph__ring").exists()).toBe(true);
    expect(g.find(".travel-glyph__sleep").exists()).toBe(true);
    expect(w.findAll(".travel-glyph__sleep")).toHaveLength(1);
    // A sleep stop still marks the camp at the stop.
    expect(w.get('[data-testid="travel-map__route-camp"]').attributes("data-index")).toBe("2");
  });

  it("an empty same-cell plan draws no route and describes nothing", async () => {
    const w = await mapWith({ plan: EMPTY, locked: true, target: null });
    expect(w.find('[data-testid="travel-map__route"]').exists()).toBe(false);
    expect(w.get('[data-testid="travel-map"]').attributes("aria-describedby")).toBeUndefined();
  });

  it("only the plan overlay changing never repaints the canvas", async () => {
    const w = await mapWith({});
    const start = travelPaintStats().count;
    expect(start).toBeGreaterThan(0);
    await w.setProps({ plan: FULL, target: { x: CX + 6, y: CY, label: null, locked: false } });
    await flush();
    await w.setProps({ locked: true, target: { x: CX + 6, y: CY, label: null, locked: true }, cursor: { x: CX + 2, y: CY, known: true, party: false, label: null } });
    await flush();
    await w.setProps({ plan: SLEEP, cursor: null });
    await flush();
    await w.setProps({ plan: null, locked: false, target: null });
    await flush();
    expect(travelPaintStats().count).toBe(start);
  });

  it("a hover preview keeps following the party and a lock fits the route", async () => {
    const far = { ...FULL, steps: FULL.steps.map((s, i) => ({ ...s, cell: { x: CX + i + 1, y: CY + i + 1 } })), destination: { x: CX + 6, y: CY + 6 } };
    const follow = await mapWith({});
    const before = follow.get('[data-testid="travel-map__world"]').attributes("style");
    await follow.setProps({ plan: far, target: { x: CX + 6, y: CY + 6, label: null, locked: false } });
    await flush();
    expect(follow.get('[data-testid="travel-map__world"]').attributes("style")).toBe(before);
    await follow.setProps({ locked: true, target: { x: CX + 6, y: CY + 6, label: null, locked: true } });
    await flush();
    expect(follow.get('[data-testid="travel-map__world"]').attributes("style")).not.toBe(before);
  });
});

describe("the leg follows the supplied plan", () => {
  it("ticks carry the supplied stages and indices", () => {
    const view = legView({ plan: FULL, locked: true, capacity: CAPACITY });
    expect(view.gauge.source).toBe("plan");
    expect(view.gauge.ticks.map((t) => [t.bucket, t.beyond, t.night, t.moon, t.camp])).toEqual([
      ["normal", false, false, false, false],
      ["light", false, false, false, false],
      ["moderate", false, true, true, false],
      ["severe", false, true, false, true],
      ["moderate", true, true, false, false],
      ["severe", true, true, false, false],
    ]);
    // Steps and duration are the supplied plan's, up to its stop.
    expect(view.intent.leg).toMatchObject({ steps: 4, minutes: 80 });
  });

  it("the terminal sleep tick keeps its stage, is counted and its duration is told", () => {
    const view = legView({ plan: SLEEP, locked: true, capacity: CAPACITY });
    const last = view.gauge.ticks[2];
    expect([last.stage, last.bucket, last.sleep, last.camp]).toEqual(["forced_sleep", "severe", true, true]);
    expect(view.legend.entries.find((e) => e.bucket === "severe").count).toBe(2);
    expect(view.intent.leg).toMatchObject({ steps: 3, minutes: Math.ceil(4440 / 60) });
    expect(view.gauge.summary).not.toBe(legView({ plan: { ...SLEEP, steps: SLEEP.steps.map((s) => ({ ...s, fatigue_stage: "severe" })) }, capacity: CAPACITY }).gauge.summary);
    expect(routeSummary(SLEEP)).toContain(formatDuration(1740));
  });

  it("an empty plan is the no-plan state", () => {
    const view = legView({ plan: EMPTY, locked: true, capacity: CAPACITY });
    expect(view.gauge.source).toBe("capacity");
    expect(view.actions.primary).toMatchObject({ enabled: false, code: "no_plan" });
    expect(routeSummary(EMPTY)).toBe("");
  });

  it("a locked plan waits for route-ui's route walk before 出發", () => {
    expect(legView({ plan: FULL, locked: true, capacity: CAPACITY, routeReady: false }).actions.primary).toMatchObject({ enabled: false, code: "route_pending" });
    expect(legView({ plan: FULL, locked: true, capacity: CAPACITY, routeReady: true }).actions.primary).toMatchObject({ enabled: true, code: null });
  });

  it("the intent follows the cursor, the error and the pending query", () => {
    const at = (input) => legView({ capacity: CAPACITY, ...input }).intent.kind;
    expect(at({ pending: true, target: { label: null } })).toBe("plan-pending");
    expect(at({ planError: { code: "plan_unreachable", message: "x" } })).toBe("plan-error");
    expect(at({ plan: FULL, planError: null })).toBe("plan");
    expect(at({ cursor: { known: false, party: false, label: null }, plan: FULL })).toBe("cursor");
    expect(at({ cursor: { known: true, party: false, label: null }, plan: FULL })).toBe("plan");
    // An aim keeps its precedence over all of them.
    const aim = { direction: "east", word: "東", enabled: true, reason: null, exitRef: "e_wild_e" };
    expect(at({ aim, cursor: { known: true, party: false }, plan: FULL, pending: true })).toBe("aim");
  });
});
