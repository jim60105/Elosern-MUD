// The travel route query owner (wilderness-travel-planning-ui, design "Single-
// flight supersession"): the real composed store behind a fake sender,
// synthetic wilderness panels and fake timers. The map is adopted through the
// store's own `setTravelMap` exactly as the refresh owner writes it, and each
// `travel.plan` is answered through the real result validator, so every case
// controls the order of results and publications.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useElosernStore } from "../../stores/elosern.js";
import { PLAN_DEBOUNCE_MS, PLAN_ERROR_TEXT } from "../../stores/elosern/travel.js";
import { fx, walkArea, walkCapacity, walkPanels } from "./support.js";

const CX = 60;
const CY = 80;
const FAR = { x: CX + 3, y: CY + 1 };
const OTHER = { x: CX - 2, y: CY - 3 };

beforeEach(() => {
  // The persisted travel preferences start from their defaults.
  localStorage.clear();
  vi.useFakeTimers();
});
afterEach(() => {
  vi.useRealTimers();
});

/** A synthetic plan from `origin` to `destination` (one step per column). */
function planData(origin, destination, { stages = ["normal", "light"], stop = null, night = null, reason = "pace_threshold" } = {}) {
  const steps = stages.map((stage, i) => ({ cell: { x: origin.x + i + 1, y: origin.y }, seconds: 1200, fatigue_stage: stage }));
  return {
    origin: { ...origin },
    destination: { ...destination },
    steps,
    total_seconds: 1200 * steps.length,
    nightfall_index: night,
    stop_index: stop ?? steps.length - 1,
    stop_reason: reason,
  };
}

function planner({ capacity = walkCapacity() } = {}) {
  setActivePinia(createPinia());
  const store = useElosernStore();
  const sender = fx.createFakeSender();
  store.setSender(sender);
  store.beginTransport(1);
  store.setConnected(true);
  const accept = (name, body) => {
    const outcome = store.receive(store.view.generation, name, [body], {});
    if (!outcome.accepted) throw new Error(`${name} rejected: ${JSON.stringify(outcome)}`);
    return outcome;
  };
  let here = { x: CX, y: CY };
  let panelOptions = { capacity };
  accept("ui_snapshot", fx.snapshot({ panels: walkPanels(CX, CY, panelOptions) }));
  const adopt = (x = here.x, y = here.y, reveal = 4) => store.setTravelMap({ status: "ready", area: walkArea(x, y, { reveal }) });
  adopt();
  const plans = () => sender.sent.actions.filter((a) => a.action_id === "travel.plan");
  const next = () => store.view.revision + 1;
  const publish = (overrides = {}) => {
    const revision = next();
    accept("ui_update", fx.update({ revision, panels: walkPanels(here.x, here.y, panelOptions), ...overrides }));
    return revision;
  };
  /** Answer travel.plan request `request` (no presentation: the current revision). */
  const answer = (request, outcome = "success", extra = {}) => {
    const { x, y } = request.payload.destination;
    const success = outcome === "success";
    return accept("ui_action_result", fx.actionResult({
      request_id: request.request_id,
      presentation_revision: store.view.revision,
      outcome,
      code: success ? "travel.plan" : extra.code ?? "plan_unreachable",
      message: success ? "已規劃行程。" : extra.message ?? "伺服器的原文訊息。",
      ...(success ? { data: extra.data ?? planData(here, { x, y }) } : {}),
    }));
  };
  const move = (x, y) => {
    here = { x, y };
    return publish();
  };
  const setPanels = (options) => {
    panelOptions = { ...panelOptions, ...options };
  };
  return { store, sender, accept, adopt, plans, publish, answer, move, setPanels, travel: () => store.view.travel };
}

describe("hover queries are debounced", () => {
  it("sends nothing at 149 ms and one exact query at 150 ms", () => {
    const p = planner();
    expect(p.store.hoverTravelCell(FAR)).toBe(true);
    expect(p.travel().hover).toEqual(FAR);
    vi.advanceTimersByTime(PLAN_DEBOUNCE_MS - 1);
    expect(p.plans()).toHaveLength(0);
    vi.advanceTimersByTime(1);
    expect(p.plans().map((r) => r.payload)).toEqual([{ destination: FAR, pace: "standard", stop_at_night: true }]);
    expect(p.travel().planPending).toBe(true);
  });

  it("a newer cell restarts the wait and only it is asked for", () => {
    const p = planner();
    p.store.hoverTravelCell(FAR);
    vi.advanceTimersByTime(100);
    p.store.hoverTravelCell(OTHER);
    vi.advanceTimersByTime(100);
    expect(p.plans()).toHaveLength(0);
    vi.advanceTimersByTime(50);
    expect(p.plans().map((r) => r.payload.destination)).toEqual([OTHER]);
  });

  it("neighbours, unknown cells, the party cell and leaving preview nothing", () => {
    const p = planner();
    for (const cell of [{ x: CX + 1, y: CY }, { x: CX + 9, y: CY }, { x: CX, y: CY }, null]) p.store.hoverTravelCell(cell);
    p.store.hoverTravelCell(FAR);
    p.store.hoverTravelCell(null);
    vi.advanceTimersByTime(1000);
    expect(p.plans()).toHaveLength(0);
    expect(p.travel()).toMatchObject({ hover: null, plan: null, planPending: false });
  });
});

describe("supersession through the single-flight gate", () => {
  it.each(["success", "rejected"])("a superseded %s result is ignored and only the latest request follows", (outcome) => {
    const p = planner();
    p.store.hoverTravelCell(FAR);
    vi.advanceTimersByTime(150);
    const first = p.plans()[0];
    p.store.hoverTravelCell(OTHER);
    vi.advanceTimersByTime(150);
    // The gate is held by the first query: nothing else leaves.
    expect(p.plans()).toHaveLength(1);
    expect(p.travel()).toMatchObject({ plan: null, planError: null, planPending: true });
    p.answer(first, outcome);
    expect(p.travel()).toMatchObject({ plan: null, planError: null });
    expect(p.plans().map((r) => r.payload.destination)).toEqual([FAR, OTHER]);
    p.answer(p.plans()[1]);
    expect(p.travel().plan.destination).toEqual(OTHER);
    expect(p.travel().planPending).toBe(false);
    vi.advanceTimersByTime(1000);
    expect(p.plans()).toHaveLength(2);
  });

  it("a superseded error never replaces a newer plan, in either order", () => {
    const p = planner();
    p.store.lockTravelDestination(FAR);
    const first = p.plans()[0];
    p.store.lockTravelDestination(OTHER);
    p.answer(first, "rejected", { code: "plan_unreachable" });
    const second = p.plans()[1];
    p.answer(second);
    // A late duplicate of the superseded refusal changes nothing.
    p.answer(first, "rejected", { code: "plan_unreachable" });
    expect(p.travel()).toMatchObject({ planError: null, lockedDestination: OTHER });
    expect(p.travel().plan.destination).toEqual(OTHER);
  });

  it("a query waits for a walk's step and sends after its gate frees", () => {
    const p = planner();
    p.store.stepTravel("east");
    p.store.lockTravelDestination(FAR);
    expect(p.plans()).toHaveLength(0);
    const step = p.sender.sent.actions.find((a) => a.action_id === "explore.move");
    p.accept("ui_action_result", fx.actionResult({ request_id: step.request_id, presentation_revision: p.store.view.revision, outcome: "rejected", code: "blocked", message: "擋住了。" }));
    expect(p.plans().map((r) => r.payload.destination)).toEqual([FAR]);
  });

  it("an answer for another origin or destination is dropped", () => {
    const p = planner();
    p.store.lockTravelDestination(FAR);
    p.answer(p.plans()[0], "success", { data: planData({ x: CX - 1, y: CY }, FAR) });
    expect(p.travel().plan).toBeNull();
    p.store.lockTravelDestination(OTHER);
    p.answer(p.plans()[1], "success", { data: planData({ x: CX, y: CY }, FAR) });
    expect(p.travel().plan).toBeNull();
  });
});

describe("locks and errors", () => {
  it("a lock asks at once and a hover under it changes nothing", () => {
    const p = planner();
    expect(p.store.lockTravelDestination(FAR)).toBe(true);
    expect(p.plans()).toHaveLength(1);
    p.answer(p.plans()[0]);
    p.store.hoverTravelCell(OTHER);
    p.store.hoverTravelCell(null);
    vi.advanceTimersByTime(1000);
    expect(p.plans()).toHaveLength(1);
    expect(p.travel()).toMatchObject({ lockedDestination: FAR, hover: null });
    expect(p.travel().plan.destination).toEqual(FAR);
  });

  it("locking the hovered destination keeps its query instead of asking again", () => {
    const p = planner();
    p.store.hoverTravelCell(FAR);
    vi.advanceTimersByTime(150);
    p.store.lockTravelDestination(FAR);
    expect(p.plans()).toHaveLength(1);
    p.answer(p.plans()[0]);
    expect(p.travel().plan.destination).toEqual(FAR);
  });

  it("only disclosed non-party cells lock; a neighbour may", () => {
    const p = planner();
    expect(p.store.lockTravelDestination({ x: CX, y: CY })).toBe(false);
    expect(p.store.lockTravelDestination({ x: CX + 9, y: CY })).toBe(false);
    expect(p.store.lockTravelDestination({ x: CX + 30, y: CY })).toBe(false);
    expect(p.plans()).toHaveLength(0);
    expect(p.store.lockTravelDestination({ x: CX + 1, y: CY + 1 })).toBe(true);
    expect(p.plans()).toHaveLength(1);
  });

  it.each(Object.keys(PLAN_ERROR_TEXT))("%s shows its stable words, clears the preview and is not retried", (code) => {
    const p = planner();
    p.store.lockTravelDestination(FAR);
    p.answer(p.plans()[0]);
    p.store.lockTravelDestination(OTHER);
    p.answer(p.plans()[1], "rejected", { code, message: "不應出現的原文。" });
    expect(p.travel().plan).toBeNull();
    expect(p.travel().planError).toEqual({ code, message: PLAN_ERROR_TEXT[code] });
    expect(p.travel().lockedDestination).toEqual(OTHER);
    p.publish();
    vi.advanceTimersByTime(5000);
    expect(p.plans()).toHaveLength(2);
    // The intent line presents it: no narrative error line per query.
    expect(p.store.narrative.filter((l) => l.kind === "err")).toHaveLength(0);
  });

  it("another refusal keeps the server's own message", () => {
    const p = planner();
    p.store.lockTravelDestination(FAR);
    p.answer(p.plans()[0], "rejected", { code: "not_exploring", message: "你不在野外探索中，無法規劃行程。" });
    expect(p.travel().planError).toEqual({ code: "not_exploring", message: "你不在野外探索中，無法規劃行程。" });
  });

  it("Esc's clear forgets the lock and the outstanding query", () => {
    const p = planner();
    p.store.lockTravelDestination(FAR);
    expect(p.store.clearTravelTarget()).toBe(true);
    p.answer(p.plans()[0]);
    expect(p.travel()).toMatchObject({ lockedDestination: null, plan: null, planPending: false, planTarget: null });
  });
});

describe("currentness", () => {
  function locked() {
    const p = planner();
    p.store.lockTravelDestination(FAR);
    p.answer(p.plans()[0]);
    expect(p.travel().plan).not.toBeNull();
    return p;
  }

  it("an unrelated publication or an identical window keeps the plan", () => {
    const p = locked();
    p.publish();
    p.store.setTravelMap({ status: "refreshing", area: p.store.view.travel.area });
    p.adopt();
    expect(p.travel().plan).not.toBeNull();
    expect(p.plans()).toHaveLength(1);
  });

  it.each([
    ["pace", (p) => p.store.setTravelPace("forced")],
    ["nightfall stop", (p) => p.store.setTravelStopAtNight(false)],
    ["member fatigue", (p) => { p.setPanels({ capacity: walkCapacity({ normal: 2 }) }); p.publish(); }],
    ["a replaced window", (p) => p.adopt(CX, CY, 5)],
  ])("a %s change forgets the plan and the lock asks once more", (_, change) => {
    const p = locked();
    change(p);
    expect(p.travel().plan).toBeNull();
    expect(p.plans()).toHaveLength(2);
    expect(p.plans()[1].payload.destination).toEqual(FAR);
    p.answer(p.plans()[1]);
    p.publish();
    expect(p.plans()).toHaveLength(2);
    expect(p.travel().plan).not.toBeNull();
  });

  it("a clock change waits for the map fetched at the new time", () => {
    const p = locked();
    const t = p.store.view.serverTime;
    p.publish({ server_time: { ...t, minute: (t.minute + 20) % 60 } });
    expect(p.travel().plan).toBeNull();
    expect(p.plans()).toHaveLength(1);
    p.store.setTravelMap({ status: "refreshing", area: p.store.view.travel.area });
    p.adopt();
    expect(p.plans()).toHaveLength(2);
  });

  it("a stale result never adopts and the new facts ask once", () => {
    const p = planner();
    p.store.lockTravelDestination(FAR);
    p.store.setTravelPace("cautious");
    p.answer(p.plans()[0]);
    expect(p.travel().plan).toBeNull();
    expect(p.plans().map((r) => r.payload.pace)).toEqual(["standard", "cautious"]);
  });

  it("a committed step keeps the lock and asks once from the new origin", () => {
    const p = locked();
    p.move(CX + 1, CY);
    expect(p.travel()).toMatchObject({ plan: null, lockedDestination: FAR });
    // The old window is not current for the new node: nothing leaves yet.
    expect(p.plans()).toHaveLength(1);
    p.store.setTravelMap({ status: "refreshing", area: p.store.view.travel.area });
    p.adopt(CX + 1, CY);
    expect(p.plans()).toHaveLength(2);
    p.answer(p.plans()[1]);
    expect(p.travel().plan.origin).toEqual({ x: CX + 1, y: CY });
  });

  it("an unlocked hover is dropped when the party moves", () => {
    const p = planner();
    p.store.hoverTravelCell(FAR);
    vi.advanceTimersByTime(150);
    p.move(CX + 1, CY);
    p.adopt(CX + 1, CY);
    vi.advanceTimersByTime(1000);
    expect(p.plans()).toHaveLength(1);
    expect(p.travel()).toMatchObject({ hover: null, plan: null, planPending: false });
  });

  it("a lock clears when the window no longer discloses it or the party reaches it", () => {
    const p = locked();
    p.adopt(CX, CY, 2);
    expect(p.travel().lockedDestination).toBeNull();
    const q = planner();
    q.store.lockTravelDestination({ x: CX + 1, y: CY });
    q.answer(q.plans()[0]);
    q.move(CX + 1, CY);
    q.adopt(CX + 1, CY);
    expect(q.travel()).toMatchObject({ lockedDestination: null, plan: null });
    expect(q.plans()).toHaveLength(1);
  });

  it("a disconnect forgets the preview and a new session clears the lock", () => {
    const p = locked();
    p.store.setConnected(false);
    expect(p.travel().plan).toBeNull();
    expect(p.plans()).toHaveLength(1);
    p.store.beginTransport(2);
    p.store.setConnected(true);
    p.accept("ui_snapshot", fx.snapshot({ presentation_epoch: fx.EPOCH_B, revision: 1, panels: walkPanels(CX, CY, { capacity: walkCapacity() }) }));
    p.adopt();
    expect(p.travel()).toMatchObject({ lockedDestination: null, plan: null, planPending: false });
    expect(p.plans()).toHaveLength(1);
  });

  it("an aim supersedes a hover preview but a lock survives it without a new query", () => {
    const p = planner();
    p.store.hoverTravelCell(FAR);
    vi.advanceTimersByTime(150);
    p.store.aimTravel("east");
    p.answer(p.plans()[0]);
    expect(p.travel()).toMatchObject({ hover: null, plan: null });
    const q = locked();
    q.store.aimTravel("east");
    expect(q.travel().plan).not.toBeNull();
    expect(q.plans()).toHaveLength(1);
  });
});
