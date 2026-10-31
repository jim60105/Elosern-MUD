// The guarded route walk (wilderness-travel-route-ui, design "Departed plan
// and guarded dispatch" and "Stop state and replanning"): the real composed
// store behind a fake sender, synthetic wilderness panels and fake timers.
// Each `travel.plan` and `explore.move` is answered through the real result
// validators, the window is adopted through `setTravelMap` exactly as the
// refresh owner writes it, and every plan is synthetic with independently
// known indices.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useElosernStore } from "../../stores/elosern.js";
import { ROUTE_CHANGED_LINE } from "../../stores/elosern/travel.js";
import { fx, liveTravel, tick, walkArea, walkCapacity, walkNode, walkPanels } from "./support.js";

const CX = 60;
const CY = 80;
const DEST = { x: CX + 4, y: CY };
const FLAGS = ["landmark_reached", "district_lit", "landmark_sighted", "hostile_in_sight", "pace_threshold", "nightfall", "member_asleep"];

beforeEach(() => {
  localStorage.clear();
  vi.useFakeTimers();
});
afterEach(() => {
  vi.useRealTimers();
});

/** A synthetic eastward plan from `origin`: one step per column, `stop` inclusive. */
function eastPlan(origin, count, stop) {
  const steps = Array.from({ length: count }, (_, i) => ({ cell: { x: origin.x + i + 1, y: origin.y }, seconds: 1200, fatigue_stage: "normal" }));
  return {
    origin: { ...origin },
    destination: { ...steps[count - 1].cell },
    steps,
    total_seconds: 1200 * (stop + 1),
    nightfall_index: null,
    stop_index: stop,
    stop_reason: stop === count - 1 ? "destination_reached" : "pace_threshold",
  };
}

/** `walkPanels` whose committed exit references carry `prefix` instead of `e`. */
function renamedPanels(x, y, prefix, options = {}) {
  const panels = walkPanels(x, y, options);
  const rename = (ref) => ref.replace(/^e_/, `${prefix}_`);
  panels.exploration = {
    ...panels.exploration,
    move: panels.exploration.move.map((row) => ({ ...row, exit_ref: rename(row.exit_ref) })),
  };
  panels.local_map = {
    ...panels.local_map,
    nodes: panels.local_map.nodes.map((n) => (n.action ? { ...n, action: { ...n.action, exit_ref: rename(n.action.exit_ref) } } : n)),
  };
  return panels;
}

function router({ motion = "off" } = {}) {
  setActivePinia(createPinia());
  const store = useElosernStore();
  store.setMotionLevel(motion);
  const sender = fx.createFakeSender();
  store.setSender(sender);
  store.beginTransport(1);
  store.setConnected(true);
  const accept = (name, body) => {
    const outcome = store.receive(store.view.generation, name, [body], {});
    if (!outcome.accepted) throw new Error(`${name} rejected: ${JSON.stringify(outcome)}`);
    return outcome;
  };
  const capacity = walkCapacity();
  accept("ui_snapshot", fx.snapshot({ panels: walkPanels(CX, CY, { capacity }) }));
  const adopt = (x, y) => store.setTravelMap({ status: "ready", area: walkArea(x, y, { reveal: 5 }) });
  adopt(CX, CY);
  const plans = () => sender.sent.actions.filter((a) => a.action_id === "travel.plan");
  const moves = () => sender.sent.actions.filter((a) => a.action_id === "explore.move");
  const next = () => store.view.revision + 1;
  /** Answer the last travel.plan with `data`. */
  const answer = (data) =>
    accept("ui_action_result", fx.actionResult({
      request_id: plans().at(-1).request_id, presentation_revision: store.view.revision,
      outcome: "success", code: "travel.plan", message: "已規劃行程。", data,
    }));
  /**
   * Commit the last move as a step to `(x, y)`: its successful result with
   * `interrupts` (null: no data slot) and the next cell's panels, in
   * `order`; then, unless `adoptMap` is false, the new cell's window.
   */
  const commit = (x, y, { interrupts = [], order = "result-first", panels = null, adoptMap = true, request = moves().at(-1) } = {}) => {
    const revision = next();
    const body = () => accept("ui_update", fx.update({ revision, panels: panels ?? walkPanels(x, y, { capacity }) }));
    const result = () =>
      accept("ui_action_result", fx.actionResult({
        request_id: request.request_id, presentation_revision: revision, outcome: "success", code: "moved",
        message: "你向前走去。", ...(interrupts === null ? {} : { data: { interrupts } }),
      }));
    if (order === "result-first") {
      result();
      body();
    } else {
      body();
      result();
    }
    if (adoptMap) adopt(x, y);
    return revision;
  };
  /** Lock the plan's destination and answer its query with `plan`. */
  const lockWith = (plan) => {
    store.lockTravelDestination(plan.destination);
    answer(plan);
  };
  return { store, sender, accept, adopt, plans, moves, answer, commit, lockWith, travel: () => store.view.travel };
}

describe("departure", () => {
  it("departs only a locked, current, answered plan with an executable prefix", () => {
    const r = router();
    expect(r.store.departTravel()).toMatchObject({ departed: false, reason: "no_plan" });
    r.store.lockTravelDestination(DEST);
    // The query flies (and holds the gate): nothing departs on a pending answer.
    expect(r.store.departTravel().departed).toBe(false);
    r.answer(eastPlan({ x: CX, y: CY }, 4, 3));
    // An aim keeps Enter's single step: the store refuses to depart over it.
    r.store.aimTravel("north");
    expect(r.store.departTravel()).toMatchObject({ departed: false, reason: "aim" });
    r.store.aimTravel(null);
    expect(r.moves()).toHaveLength(0);
    expect(r.store.departTravel()).toEqual({ departed: true });
    expect(r.moves()).toHaveLength(1);
    expect(r.travel().walking).toMatchObject({ kind: "route", progress: 0, stopIndex: 3 });
    expect(r.travel().departedPlan.stop_index).toBe(3);
    // A walk departs nothing again.
    expect(r.store.departTravel()).toMatchObject({ departed: false, reason: "walking" });
  });

  it("an unlocked hover preview and a plan whose facts moved do not depart", () => {
    const r = router();
    r.store.hoverTravelCell(DEST);
    vi.advanceTimersByTime(200);
    r.answer(eastPlan({ x: CX, y: CY }, 4, 3));
    expect(r.travel().plan).not.toBeNull();
    expect(r.store.departTravel()).toMatchObject({ departed: false, reason: "no_plan" });
    r.store.lockTravelDestination(DEST);
    // A preference change forgets the plan; the lock asks again.
    r.store.setTravelPace("cautious");
    expect(r.travel().plan).toBeNull();
    expect(r.store.departTravel().departed).toBe(false);
    expect(r.moves()).toHaveLength(0);
  });

  it("refuses an empty plan or one without an integer stop", () => {
    for (const data of [
      { ...eastPlan({ x: CX, y: CY }, 4, 3), stop_index: null },
      { ...eastPlan({ x: CX, y: CY }, 4, 3), steps: [], stop_index: null, total_seconds: 0 },
    ]) {
      const r = router();
      r.store.lockTravelDestination(DEST);
      try {
        r.answer(data);
      } catch {
        // The result validator may refuse the shape outright: no plan either way.
      }
      expect(r.store.departTravel().departed).toBe(false);
      expect(r.moves()).toHaveLength(0);
    }
  });
});

describe("the inclusive executable prefix", () => {
  it.each([
    [4, 1, 2],
    [4, 0, 1],
    [3, 2, 3],
  ])("a %i-step plan stopping at index %i sends exactly %i steps", (count, stop, sent) => {
    const r = router();
    r.lockWith(eastPlan({ x: CX, y: CY }, count, stop));
    r.store.departTravel();
    for (let i = 1; i <= sent; i += 1) {
      expect(r.moves()).toHaveLength(i);
      expect(r.moves()[i - 1].payload.current_node).toBe(walkNode(CX + i - 1, CY));
      r.commit(CX + i, CY);
      vi.advanceTimersByTime(1000);
    }
    expect(r.moves()).toHaveLength(sent);
    expect(r.travel().walking).toBeNull();
    if (stop < count - 1) {
      // A short stop keeps the lock and asks once from the new position…
      expect(r.travel().lockedDestination).toEqual(DEST);
      expect(r.plans()).toHaveLength(2);
      expect(r.plans()[1].payload.destination).toEqual(DEST);
      // …and the new plan is never departed by itself.
      r.answer(eastPlan({ x: CX + sent, y: CY }, count - sent, count - sent - 1));
      vi.advanceTimersByTime(2000);
      expect(r.moves()).toHaveLength(sent);
      expect(r.travel().plan.origin).toEqual({ x: CX + sent, y: CY });
    } else {
      // Reaching the destination clears the lock.
      expect(r.travel().lockedDestination).toBeNull();
    }
  });

  it("the leg's spent progress advances once per counted commit", () => {
    const r = router();
    r.lockWith(eastPlan({ x: CX, y: CY }, 4, 3));
    r.store.departTravel();
    r.commit(CX + 1, CY);
    expect(r.travel().walking.progress).toBe(1);
    // A same-revision republication of the same cell counts nothing more.
    r.accept("ui_update", fx.update({ revision: r.store.view.revision + 1, panels: walkPanels(CX + 1, CY) }));
    expect(r.travel().walking.progress).toBe(1);
    vi.advanceTimersByTime(1000);
    r.commit(CX + 2, CY);
    expect(r.travel().walking.progress).toBe(2);
    // The departed plan stays exactly the captured one.
    expect(r.travel().departedPlan.origin).toEqual({ x: CX, y: CY });
  });

  it("each send uses the CURRENT descriptor, even when the exit references change", () => {
    const r = router();
    r.lockWith(eastPlan({ x: CX, y: CY }, 3, 2));
    r.store.departTravel();
    expect(r.moves()[0].payload.exit_ref).toBe("e_wild_e");
    r.commit(CX + 1, CY, { panels: renamedPanels(CX + 1, CY, "r2") });
    vi.advanceTimersByTime(1000);
    expect(r.moves()[1].payload).toMatchObject({ exit_ref: "r2_wild_e", current_node: walkNode(CX + 1, CY) });
    r.commit(CX + 2, CY, { panels: renamedPanels(CX + 2, CY, "r3") });
    vi.advanceTimersByTime(1000);
    expect(r.moves()[2].payload.exit_ref).toBe("r3_wild_e");
  });

  it("a step without a matching current row stops and keeps the lock", () => {
    const r = router();
    r.lockWith(eastPlan({ x: CX, y: CY }, 3, 2));
    r.store.departTravel();
    // The next cell's east row is gone: no descriptor for the next step.
    r.commit(CX + 1, CY, { panels: walkPanels(CX + 1, CY, { missing: ["east", "northeast", "southeast"] }) });
    vi.advanceTimersByTime(1000);
    expect(r.moves()).toHaveLength(1);
    expect(r.travel().walking).toBeNull();
    expect(r.travel().notice.kind).toBe("blocked");
    expect(r.travel().lockedDestination).toEqual({ x: CX + 3, y: CY });
  });

  it("a row whose disclosed destination is not the step's cell stops the walk", () => {
    const r = router();
    r.lockWith(eastPlan({ x: CX, y: CY }, 3, 2));
    r.store.departTravel();
    const panels = walkPanels(CX + 1, CY);
    panels.exploration = {
      ...panels.exploration,
      move: panels.exploration.move.map((row) => (row.exit_ref === "e_wild_e" ? { ...row, destination: null } : row)),
    };
    r.commit(CX + 1, CY, { panels });
    vi.advanceTimersByTime(1000);
    expect(r.moves()).toHaveLength(1);
    expect(r.travel().notice).toEqual({ kind: "blocked", message: ROUTE_CHANGED_LINE });
  });
});

describe("walk context", () => {
  it("every route step carries the preferences frozen at departure", () => {
    const r = router();
    r.store.setTravelPace("cautious");
    r.store.setTravelStopAtNight(false);
    r.lockWith(eastPlan({ x: CX, y: CY }, 3, 2));
    r.store.departTravel();
    // Preferences cannot change while walking.
    r.store.setTravelPace("forced");
    r.commit(CX + 1, CY);
    vi.advanceTimersByTime(1000);
    expect(r.moves().map((m) => m.payload.walk)).toEqual([
      { pace: "cautious", stop_at_night: false },
      { pace: "cautious", stop_at_night: false },
    ]);
  });

  it("a discrete neighbour step keeps the ordinary two-field payload", () => {
    const r = router();
    r.store.stepTravel("east");
    expect(r.moves()[0].payload).toEqual({ exit_ref: "e_wild_e", current_node: walkNode(CX, CY) });
  });

  it("a held direction walk sends the walk context and stops on a flag", () => {
    const r = router();
    r.store.holdTravel("east");
    vi.advanceTimersByTime(400);
    expect(r.moves()[0].payload.walk).toEqual({ pace: "standard", stop_at_night: true });
    r.commit(CX + 1, CY, { interrupts: ["hostile_in_sight"] });
    vi.advanceTimersByTime(2000);
    expect(r.moves()).toHaveLength(1);
    expect(r.travel().notice).toEqual({ kind: "interrupted", flags: ["hostile_in_sight"] });
  });
});

describe("every stop cause", () => {
  const cases = [...FLAGS.map((flag) => [flag, [flag]]), ["combined", ["landmark_sighted", "hostile_in_sight", "nightfall"]]];
  for (const order of ["result-first", "publication-first"]) {
    it.each(cases)(`%s stops before any next send (${order})`, (_name, flags) => {
      const r = router();
      r.lockWith(eastPlan({ x: CX, y: CY }, 4, 3));
      r.store.departTravel();
      r.commit(CX + 1, CY, { interrupts: flags, order });
      vi.advanceTimersByTime(5000);
      expect(r.moves()).toHaveLength(1);
      expect(r.travel().walking).toBeNull();
      expect(r.travel().notice).toEqual({ kind: "interrupted", flags });
      // A short stop replans its surviving lock once, without departing.
      expect(r.travel().lockedDestination).toEqual(DEST);
      expect(r.plans()).toHaveLength(2);
      r.answer(eastPlan({ x: CX + 1, y: CY }, 3, 2));
      vi.advanceTimersByTime(5000);
      expect(r.moves()).toHaveLength(1);
      expect(r.plans()).toHaveLength(2);
    });
  }

  it("an empty flag list continues", () => {
    const r = router();
    r.lockWith(eastPlan({ x: CX, y: CY }, 4, 3));
    r.store.departTravel();
    r.commit(CX + 1, CY, { interrupts: [] });
    vi.advanceTimersByTime(1000);
    expect(r.moves()).toHaveLength(2);
  });

  it("hostile_in_sight prevents the next send even when the dwell already elapsed", () => {
    const r = router({ motion: "full" });
    r.lockWith(eastPlan({ x: CX, y: CY }, 4, 3));
    r.store.departTravel();
    // The step's publication commits and its map is adopted; the dwell runs
    // out before the step's own result (carrying the flag) arrives.
    const request = r.moves()[0];
    const revision = r.store.view.revision + 1;
    r.accept("ui_update", fx.update({ revision, panels: walkPanels(CX + 1, CY, { capacity: walkCapacity() }) }));
    r.adopt(CX + 1, CY);
    vi.advanceTimersByTime(2000);
    expect(r.moves()).toHaveLength(1);
    r.accept("ui_action_result", fx.actionResult({
      request_id: request.request_id, presentation_revision: revision, outcome: "success", code: "moved",
      message: "你向前走去。", data: { interrupts: ["hostile_in_sight"] },
    }));
    vi.advanceTimersByTime(2000);
    expect(r.moves()).toHaveLength(1);
    expect(r.travel().walking).toBeNull();
  });

  it("a route step result without a flag list stops the route", () => {
    const r = router();
    r.lockWith(eastPlan({ x: CX, y: CY }, 4, 3));
    r.store.departTravel();
    r.commit(CX + 1, CY, { interrupts: null });
    vi.advanceTimersByTime(1000);
    expect(r.moves()).toHaveLength(1);
    expect(r.travel().walking).toBeNull();
  });

  it("a refusal stops it, keeps the lock and leaves one refusal entry", () => {
    const r = router();
    r.lockWith(eastPlan({ x: CX, y: CY }, 4, 3));
    r.store.departTravel();
    r.accept("ui_action_result", fx.actionResult({
      request_id: r.moves()[0].request_id, presentation_revision: r.store.view.revision, outcome: "rejected",
      code: "blocked", message: "前方的河水太深，無法涉過。",
    }));
    vi.advanceTimersByTime(2000);
    expect(r.moves()).toHaveLength(1);
    expect(r.travel().walking).toBeNull();
    expect(r.travel().notice).toMatchObject({ kind: "refused", message: "前方的河水太深，無法涉過。" });
    expect(r.travel().lockedDestination).toEqual(DEST);
    expect(r.travel().entries.filter((e) => e.kind === "refusal")).toHaveLength(1);
  });

  it.each(["stop", "dwell"])("Stop (%s) never lets a late result restart it", (when) => {
    const r = router({ motion: "full" });
    r.lockWith(eastPlan({ x: CX, y: CY }, 4, 3));
    r.store.departTravel();
    if (when === "dwell") {
      r.commit(CX + 1, CY);
      vi.advanceTimersByTime(100);
      r.store.stopTravel("stop");
    } else {
      r.store.stopTravel("stop");
      r.commit(CX + 1, CY);
    }
    vi.advanceTimersByTime(5000);
    expect(r.moves()).toHaveLength(1);
    expect(r.travel().walking).toBeNull();
    // The lock survives the stop; its fresh plan never departs by itself.
    expect(r.travel().lockedDestination).toEqual(DEST);
    r.answer(eastPlan({ x: CX + 1, y: CY }, 3, 2));
    vi.advanceTimersByTime(5000);
    expect(r.moves()).toHaveLength(1);
  });

  it("a disconnect and an epoch change stop it", () => {
    const r = router();
    r.lockWith(eastPlan({ x: CX, y: CY }, 4, 3));
    r.store.departTravel();
    r.store.setConnected(false);
    expect(r.travel().walking).toBeNull();
    const s = router();
    s.lockWith(eastPlan({ x: CX, y: CY }, 4, 3));
    s.store.departTravel();
    s.store.beginTransport(2);
    s.store.setConnected(true);
    s.accept("ui_snapshot", fx.snapshot({ presentation_epoch: fx.EPOCH_B, revision: 1, panels: walkPanels(CX, CY) }));
    vi.advanceTimersByTime(2000);
    expect(s.travel().walking).toBeNull();
    expect(s.moves()).toHaveLength(1);
  });
});

describe("the mounted input", () => {
  let wrappers = [];
  afterEach(() => {
    for (const w of wrappers) w.unmount();
    wrappers = [];
    document.body.innerHTML = "";
  });

  async function stage() {
    vi.useRealTimers();
    const h = liveTravel({ wrappers, panels: walkPanels(CX, CY, { capacity: walkCapacity() }) });
    await tick();
    await h.answerMap(walkArea(CX, CY, { reveal: 5 }));
    // The update fixture carries a default status: restore the capacity.
    h.publish({ status: walkPanels(CX, CY, { capacity: walkCapacity() }).status });
    await tick();
    h.store.lockTravelDestination(DEST);
    const query = h.sender.sent.actions.filter((a) => a.action_id === "travel.plan").at(-1);
    h.accept("ui_action_result", fx.actionResult({
      request_id: query.request_id, presentation_revision: h.store.view.revision,
      outcome: "success", code: "travel.plan", message: "已規劃行程。", data: eastPlan({ x: CX, y: CY }, 4, 3),
    }));
    await tick();
    const map = () => h.w.get('[data-testid="travel-map"]');
    const moves = () => h.sender.sent.actions.filter((a) => a.action_id === "explore.move");
    const key = async (el, type, k, init = {}) => {
      const event = new KeyboardEvent(type, { key: k, bubbles: true, cancelable: true, ...init });
      el.dispatchEvent(event);
      await tick();
      return event;
    };
    return { ...h, map, moves, key };
  }

  it("Enter departs, a later Enter only stops, and its repeat departs nothing", async () => {
    const s = await stage();
    s.map().element.focus();
    await s.key(s.map().element, "keydown", "Enter");
    expect(s.moves()).toHaveLength(1);
    expect(s.store.view.travel.walking?.kind).toBe("route");
    // The departing press's native repeat is the same press.
    await s.key(s.map().element, "keydown", "Enter", { repeat: true });
    expect(s.store.view.travel.walking?.kind).toBe("route");
    await s.key(s.map().element, "keydown", "Enter");
    expect(s.store.view.travel.walking).toBeNull();
    await s.key(s.map().element, "keydown", "Enter", { repeat: true });
    expect(s.store.view.travel.walking).toBeNull();
    expect(s.moves()).toHaveLength(1);
  });

  it("出發 departs over a hovered aim; a key that stops on it never re-departs", async () => {
    const s = await stage();
    s.store.aimTravel("north");
    await tick();
    const depart = s.w.get('[data-testid="leg-depart"]');
    expect(depart.attributes("aria-disabled")).toBeUndefined();
    await depart.trigger("click");
    await tick();
    expect(s.moves()).toHaveLength(1);
    expect(s.store.view.travel.aim).toBeNull();
    const stop = s.w.get('[data-testid="leg-stop"]');
    stop.element.focus();
    // Space stops on keydown; the keyup's native click lands on 出發.
    await s.key(stop.element, "keydown", " ");
    expect(s.store.view.travel.walking).toBeNull();
    await s.key(stop.element, "keyup", " ");
    await s.w.get('[data-testid="leg-depart"]').trigger("click");
    await tick();
    expect(s.moves()).toHaveLength(1);
    expect(s.store.view.travel.walking).toBeNull();
    // Once released, 出發 works again (the stopped step is still in flight).
    await new Promise((resolve) => setTimeout(resolve, 5));
    expect(s.store.departTravel().departed).toBe(false);
  });

  it("a second click on the locked cell departs", async () => {
    const s = await stage();
    const { default: TravelMap } = await import("../../components/travel/TravelMap.vue");
    s.w.findComponent(TravelMap).vm.$emit("pick", DEST);
    await tick();
    expect(s.moves()).toHaveLength(1);
    expect(s.moves()[0].payload.walk).toEqual({ pace: "standard", stop_at_night: true });
  });
});
