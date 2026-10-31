// The travel walking queue (wilderness-travel-walking-ui, design "Store state
// and activation"): the real composed store behind a fake sender, synthetic
// wilderness panels and fake timers. The map state is written through the
// store's own `setTravelMap`, exactly as the refresh owner writes it, so each
// case controls when the current map is adopted.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useElosernStore } from "../../stores/elosern.js";
import { fx, walkArea, walkNode, walkPanels } from "./support.js";

const CX = 60;
const CY = 80;

beforeEach(() => {
  vi.useFakeTimers();
});
afterEach(() => {
  vi.useRealTimers();
});

function walker({ panels = walkPanels(CX, CY), motion = null } = {}) {
  setActivePinia(createPinia());
  const store = useElosernStore();
  if (motion) store.setMotionLevel(motion);
  const sender = fx.createFakeSender();
  store.setSender(sender);
  store.beginTransport(1);
  store.setConnected(true);
  const accept = (name, body) => {
    const outcome = store.receive(store.view.generation, name, [body], {});
    if (!outcome.accepted) throw new Error(`${name} rejected: ${JSON.stringify(outcome)}`);
    return outcome;
  };
  accept("ui_snapshot", fx.snapshot({ panels }));
  store.setTravelMap({ status: "ready", area: walkArea(CX, CY) });
  const moves = () => sender.sent.actions.filter((a) => a.action_id === "explore.move");
  const next = () => store.view.revision + 1;
  const result = (request, revision, outcome = "success", extra = {}) =>
    accept("ui_action_result", fx.actionResult({
      request_id: request.request_id,
      presentation_revision: revision,
      outcome,
      code: outcome === "success" ? "moved" : "blocked",
      message: outcome === "success" ? "你向前走去。" : "前方的河水太深，無法涉過。",
      ...extra,
    }));
  const publish = (bodyPanels) => {
    const revision = next();
    accept("ui_update", fx.update({ revision, panels: bodyPanels }));
    return revision;
  };
  /** Commit `request` as a step to `(x, y)`, its result and publication in `order`. */
  const commit = (request, x, y, order = "result-first", panelOptions = {}) => {
    const revision = next();
    const body = () => accept("ui_update", fx.update({ revision, panels: walkPanels(x, y, panelOptions) }));
    if (order === "result-first") {
      result(request, revision);
      body();
    } else {
      body();
      result(request, revision);
    }
    return revision;
  };
  /** The refresh owner's cycle for the committed cell: refreshing, then the adopted map. */
  const refresh = (x, y) => {
    store.setTravelMap({ status: "refreshing", area: store.view.travel.area });
    store.setTravelMap({ status: "ready", area: walkArea(x, y) });
  };
  return { store, sender, accept, moves, next, result, publish, commit, refresh };
}

/** A reconnect: a new transport generation establishes a new epoch. */
function newSession(w) {
  w.store.beginTransport(2);
  w.store.setConnected(true);
  w.accept("ui_snapshot", fx.snapshot({ presentation_epoch: fx.EPOCH_B, revision: 1, panels: walkPanels(CX + 1, CY) }));
}

/** Hold `direction` past the 400 ms threshold. */
function holdPast(w, direction = "east") {
  w.store.holdTravel(direction);
  vi.advanceTimersByTime(400);
}

describe("the held walk waits for its committed step", () => {
  it("sends nothing before 400 ms and one unchanged move at 400 ms", () => {
    const w = walker();
    w.store.holdTravel("east");
    vi.advanceTimersByTime(399);
    expect(w.moves()).toHaveLength(0);
    expect(w.store.view.travel).toMatchObject({ aim: "east", holding: true, walking: null });
    vi.advanceTimersByTime(1);
    expect(w.moves().map((m) => m.payload)).toEqual([{ exit_ref: "e_wild_e", current_node: walkNode(CX, CY) }]);
    expect(w.store.view.travel.walking).toMatchObject({ kind: "direction", direction: "east", progress: 0, waiting: "commit" });
  });

  it.each(["result-first", "publication-first"])("counts the matching commit once (%s) and dwells 350 ms", (order) => {
    const w = walker();
    holdPast(w);
    const first = w.moves()[0];
    w.commit(first, CX + 1, CY, order);
    expect(w.store.view.travel.walking).toMatchObject({ progress: 1 });
    w.refresh(CX + 1, CY);
    vi.advanceTimersByTime(349);
    expect(w.moves()).toHaveLength(1);
    vi.advanceTimersByTime(1);
    expect(w.moves()).toHaveLength(2);
    expect(w.moves()[1].payload).toEqual({ exit_ref: "e_wild_e", current_node: walkNode(CX + 1, CY) });
    expect(w.store.view.travel.walking.progress).toBe(1);
  });

  it("matches a result delivered while the step is being sent", () => {
    const w = walker();
    // A synchronous transport: the server's answer arrives inside the send.
    const original = w.sender.sendAction.bind(w.sender);
    let answered = false;
    w.sender.sendAction = (env) => {
      original(env);
      if (env.action_id !== "explore.move" || answered) return;
      answered = true;
      const revision = w.next();
      w.result(env, revision);
      w.accept("ui_update", fx.update({ revision, panels: walkPanels(CX + 1, CY) }));
    };
    holdPast(w);
    expect(w.store.view.travel.walking).toMatchObject({ progress: 1, waiting: "dwell" });
  });

  it("never sends at 349 ms or before the declared revision commits", () => {
    const w = walker();
    holdPast(w);
    const first = w.moves()[0];
    // The result declares a revision the client has not committed yet.
    const revision = w.next();
    w.result(first, revision);
    vi.advanceTimersByTime(2000);
    expect(w.moves()).toHaveLength(1);
    expect(w.store.view.travel.walking).toMatchObject({ progress: 0, waiting: "commit" });
    w.accept("ui_update", fx.update({ revision, panels: walkPanels(CX + 1, CY) }));
    w.refresh(CX + 1, CY);
    vi.advanceTimersByTime(349);
    expect(w.moves()).toHaveLength(1);
    vi.advanceTimersByTime(1);
    expect(w.moves()).toHaveLength(2);
  });

  it("ignores foreign results, unrelated revisions and same-node republications", () => {
    const w = walker();
    holdPast(w);
    const first = w.moves()[0];
    // A foreign request's result and an unrelated publication that moves the node.
    w.result({ request_id: "session:999" }, w.store.view.revision);
    w.publish(walkPanels(CX + 1, CY));
    expect(w.store.view.travel.walking.progress).toBe(0);
    // The step's own result declares a later revision; the earlier node change is not it.
    const revision = w.next();
    w.result(first, revision);
    expect(w.store.view.travel.walking.progress).toBe(0);
    // Its publication keeps the node it was sent from: the step moved nothing.
    w.accept("ui_update", fx.update({ revision, panels: walkPanels(CX, CY) }));
    expect(w.store.view.travel.walking).toBeNull();
    vi.advanceTimersByTime(2000);
    expect(w.moves()).toHaveLength(1);
  });

  it("follows pooled rooms by the canonical node, not the room identity", () => {
    const w = walker({ panels: walkPanels(CX, CY, { room: 501 }) });
    holdPast(w);
    w.commit(w.moves()[0], CX + 1, CY, "result-first", { room: 501 });
    expect(w.store.view.travel.walking.progress).toBe(1);
    w.refresh(CX + 1, CY);
    vi.advanceTimersByTime(350);
    w.commit(w.moves()[1], CX + 2, CY, "publication-first", { room: 501 });
    expect(w.store.view.travel.walking.progress).toBe(2);
  });

  it("waits for the gate a map read holds and resumes on its commit", () => {
    const w = walker();
    holdPast(w);
    w.commit(w.moves()[0], CX + 1, CY);
    // The refresh owner's read takes the single dispatch gate.
    const read = w.store.dispatchAction("map.view", { scope: "area" }, null);
    expect(read).not.toBeNull();
    w.store.setTravelMap({ status: "refreshing", area: w.store.view.travel.area });
    vi.advanceTimersByTime(1000);
    expect(w.moves()).toHaveLength(1);
    const revision = w.next();
    w.accept("ui_update", fx.update({ revision, panels: { area_map: walkArea(CX + 1, CY) } }));
    w.result({ request_id: read }, revision);
    expect(w.moves()).toHaveLength(1);
    w.store.setTravelMap({ status: "ready", area: walkArea(CX + 1, CY) });
    expect(w.moves()).toHaveLength(2);
  });

  it("steps at once after the commit at motion off, and still only after it", () => {
    const w = walker({ motion: "off" });
    holdPast(w);
    vi.advanceTimersByTime(5000);
    expect(w.moves()).toHaveLength(1);
    w.commit(w.moves()[0], CX + 1, CY);
    // The old map is not the committed cell's map: the walk waits for it.
    expect(w.moves()).toHaveLength(1);
    w.refresh(CX + 1, CY);
    expect(w.moves()).toHaveLength(2);
  });
});

describe("a normal post-step refresh suspends the walk", () => {
  it("survives refreshing and sends its second step only after adoption and dwell", () => {
    const w = walker();
    holdPast(w);
    w.commit(w.moves()[0], CX + 1, CY);
    w.store.setTravelMap({ status: "refreshing", area: w.store.view.travel.area });
    vi.advanceTimersByTime(2000);
    expect(w.moves()).toHaveLength(1);
    expect(w.store.view.travel.walking).toMatchObject({ progress: 1, waiting: "map" });
    w.store.setTravelMap({ status: "ready", area: walkArea(CX + 1, CY) });
    expect(w.moves()).toHaveLength(2);
    expect(w.moves()[1].payload.current_node).toBe(walkNode(CX + 1, CY));
  });

  it("does not resume while the adopted map is another cell's", () => {
    const w = walker();
    holdPast(w);
    w.commit(w.moves()[0], CX + 1, CY);
    w.store.setTravelMap({ status: "refreshing", area: w.store.view.travel.area });
    w.store.setTravelMap({ status: "ready", area: walkArea(CX + 7, CY) });
    vi.advanceTimersByTime(2000);
    expect(w.moves()).toHaveLength(1);
  });

  it.each(["unavailable", "invalid", "retired"])("a %s map cancels instead of resuming", (status) => {
    const w = walker();
    holdPast(w);
    w.commit(w.moves()[0], CX + 1, CY);
    w.store.setTravelMap({ status: "refreshing", area: w.store.view.travel.area });
    w.store.setTravelMap({ status, area: w.store.view.travel.area });
    expect(w.store.view.travel.walking).toBeNull();
    w.store.setTravelMap({ status: "ready", area: walkArea(CX + 1, CY) });
    vi.advanceTimersByTime(2000);
    expect(w.moves()).toHaveLength(1);
  });
});

describe("the cancellation table", () => {
  const cancellations = {
    release: (w) => w.store.releaseTravel(),
    stop: (w) => w.store.stopTravel("stop"),
    disconnect: (w) => w.store.setConnected(false),
    epoch: (w) => newSession(w),
    drawer: (w) => w.store.openHudDrawer("party"),
    overlay: (w) => w.store.openOverlay("help"),
    layout: (w) => w.publish({ art: walkPanels(CX, CY, { subject: "grid:t_synth_map:2,0" }).art }),
    mode: (w) => w.accept("ui_update", fx.update({ revision: w.next(), mode: "combat", panels: {} })),
  };

  it.each(Object.keys(cancellations))("%s stops the walk and a late commit cannot restart it", (name) => {
    const w = walker();
    holdPast(w);
    const first = w.moves()[0];
    cancellations[name](w);
    expect(w.store.view.travel.walking).toBeNull();
    // The step already sent is never resent; its late commit only updates state.
    if (w.store.view.connected && w.store.view.epoch === fx.EPOCH_A && w.store.view.generation === 1) {
      w.commit(first, CX + 1, CY);
    }
    vi.advanceTimersByTime(3000);
    expect(w.moves()).toHaveLength(1);
    expect(w.store.view.travel.walking).toBeNull();
  });

  it.each(Object.keys(cancellations))("%s also drops a hold that has not fired", (name) => {
    const w = walker();
    w.store.holdTravel("east");
    vi.advanceTimersByTime(200);
    cancellations[name](w);
    vi.advanceTimersByTime(1000);
    expect(w.moves()).toHaveLength(0);
    expect(w.store.view.travel.holding).toBe(false);
  });

  it("a refusal stops the walk and keeps the server message", () => {
    const w = walker();
    holdPast(w);
    w.result(w.moves()[0], w.store.view.revision, "rejected");
    expect(w.store.view.travel.walking).toBeNull();
    expect(w.store.view.travel.notice).toEqual({ kind: "refused", message: "前方的河水太深，無法涉過。" });
    vi.advanceTimersByTime(3000);
    expect(w.moves()).toHaveLength(1);
  });

  it("a dead end or a disabled exit in the next cell stops with its reason", () => {
    const w = walker();
    holdPast(w);
    w.commit(w.moves()[0], CX + 1, CY, "result-first", { disabled: { east: "斷崖擋住了去路。" } });
    w.refresh(CX + 1, CY);
    vi.advanceTimersByTime(350);
    expect(w.moves()).toHaveLength(1);
    expect(w.store.view.travel.walking).toBeNull();
    expect(w.store.view.travel.notice).toEqual({ kind: "blocked", message: "斷崖擋住了去路。" });

    const v = walker();
    holdPast(v);
    v.commit(v.moves()[0], CX + 1, CY, "result-first", { missing: ["east"] });
    v.refresh(CX + 1, CY);
    vi.advanceTimersByTime(350);
    expect(v.moves()).toHaveLength(1);
    expect(v.store.view.travel.notice.kind).toBe("blocked");
  });

  it("walks a withheld direction through its committed row", () => {
    const w = walker({ panels: walkPanels(CX, CY, { withheld: ["east"] }) });
    holdPast(w);
    expect(w.moves().map((m) => m.payload)).toEqual([{ exit_ref: "e_wild_e", current_node: walkNode(CX, CY) }]);
  });
});

describe("aim and discrete steps", () => {
  it("keeps the aim, resolves its target and sends one step per call", () => {
    const w = walker({ panels: walkPanels(CX, CY, { disabled: { north: "門被鎖住了" } }) });
    w.store.aimTravel("northeast");
    expect(w.store.view.travel.aimTarget).toMatchObject({ direction: "northeast", word: "東北", enabled: true });
    expect(w.store.stepTravel()).toMatchObject({ sent: true });
    expect(w.moves().map((m) => m.payload.exit_ref)).toEqual(["e_wild_ne"]);
    // The gate is held until the step commits: a second call sends nothing.
    expect(w.store.stepTravel()).toMatchObject({ sent: false });
    expect(w.moves()).toHaveLength(1);
    expect(w.store.view.travel.aim).toBe("northeast");
    w.store.aimTravel("north");
    expect(w.store.view.travel.aimTarget).toMatchObject({ enabled: false, reason: "門被鎖住了" });
    w.store.aimTravel(null);
    expect(w.store.view.travel.aim).toBeNull();
  });

  it("a refused discrete step shows the server message", () => {
    const w = walker();
    w.store.stepTravel("east");
    w.result(w.moves()[0], w.store.view.revision, "rejected");
    expect(w.store.view.travel.notice).toEqual({ kind: "refused", message: "前方的河水太深，無法涉過。" });
  });

  it("an epoch change clears the aim", () => {
    const w = walker();
    w.store.aimTravel("east");
    newSession(w);
    expect(w.store.view.travel.aim).toBeNull();
  });
});
