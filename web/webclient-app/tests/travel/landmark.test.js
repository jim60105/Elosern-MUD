// The landmark arrival card (wilderness-travel-route-ui, design "Landmark
// card"): the real composed store and its travel log adoption behind a fake
// sender, the real travel_log validator, the LandmarkCard component and the
// mounted AppClient. Every arrival is a synthetic typed notice; nothing is
// read from prose or from the interrupt flag.

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import LandmarkCard from "../../components/travel/LandmarkCard.vue";
import { useElosernStore } from "../../stores/elosern.js";
import { sceneDescriptor } from "../../stories/fixtures/art_panels.js";
import { fx, liveTravel, tick, walkArea, walkCapacity, walkNode, walkPanels } from "./support.js";

vi.setConfig({ testTimeout: 60000 });

const CX = 60;
const CY = 80;
let serial = 0;

/** One typed `landmark_reached` notice reached at `node`. */
function arrival(node, { id = null, lit = null, artwork = null, name = "合成古塔" } = {}) {
  serial += 1;
  return {
    id: id ?? `${"a".repeat(32)}:t${String(serial).padStart(4, "0")}.0`,
    kind: "landmark_reached",
    tick: 1000 + serial,
    day: 3,
    time: "09:40",
    text: `抵達${name}。`,
    params: { arrival_node: node, name, lit_district: lit, prose: "風從塔頂的缺口灌進來。", artwork },
  };
}

const log = (entries) => ({ travel_log: { schema_version: 1, available: true, entries } });

function harness() {
  setActivePinia(createPinia());
  const store = useElosernStore();
  store.setMotionLevel("off");
  const sender = fx.createFakeSender();
  store.setSender(sender);
  store.beginTransport(1);
  store.setConnected(true);
  const accept = (name, body) => {
    const outcome = store.receive(store.view.generation, name, [body], {});
    if (!outcome.accepted) throw new Error(`${name} rejected: ${JSON.stringify(outcome)}`);
    return outcome;
  };
  accept("ui_snapshot", fx.snapshot({ panels: walkPanels(CX, CY, { capacity: walkCapacity() }) }));
  store.setTravelMap({ status: "ready", area: walkArea(CX, CY, { reveal: 5 }) });
  const publish = (panels) => accept("ui_update", fx.update({ revision: store.view.revision + 1, panels }));
  const moves = () => sender.sent.actions.filter((a) => a.action_id === "explore.move");
  return { store, sender, accept, publish, moves, travel: () => store.view.travel };
}

describe("committed arrival state", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("opens one card for a typed arrival bound to the current node", () => {
    const h = harness();
    expect(h.travel().arrival).toBeNull();
    const entry = arrival(walkNode(CX, CY), { lit: "合成東麓" });
    h.publish(log([entry]));
    expect(h.travel().arrival).toEqual({ id: entry.id, name: "合成古塔", litDistrict: "合成東麓", prose: "風從塔頂的缺口灌進來。", artwork: null });
  });

  it("a repeated arrival never reopens once dismissed, even after a new epoch replays it", () => {
    const h = harness();
    const entry = arrival(walkNode(CX, CY));
    h.publish(log([entry]));
    expect(h.store.dismissTravelArrival(entry.id)).toBe(true);
    // A second close does nothing.
    expect(h.store.dismissTravelArrival(entry.id)).toBe(false);
    h.publish(log([entry]));
    expect(h.travel().arrival).toBeNull();
    h.store.beginTransport(2);
    h.store.setConnected(true);
    h.accept("ui_snapshot", fx.snapshot({ presentation_epoch: fx.EPOCH_B, revision: 1, panels: { ...walkPanels(CX, CY), ...log([entry]) } }));
    expect(h.travel().arrival).toBeNull();
  });

  it("a newer arrival on the same cell replaces the older one", () => {
    const h = harness();
    const first = arrival(walkNode(CX, CY));
    const second = arrival(walkNode(CX, CY), { name: "合成新塔" });
    h.publish(log([first]));
    h.publish(log([first, second]));
    expect(h.travel().arrival.id).toBe(second.id);
    expect(h.store.dismissTravelArrival(first.id)).toBe(false);
  });

  it("a delayed arrival delivered after another move never opens, whatever its name or art", () => {
    const h = harness();
    // The party already stands one cell further on.
    h.publish(walkPanels(CX + 1, CY));
    h.publish(log([arrival(walkNode(CX, CY), { artwork: sceneDescriptor() })]));
    expect(h.travel().arrival).toBeNull();
    // Coming back to that cell later does not resurrect it.
    h.publish(walkPanels(CX, CY));
    expect(h.travel().arrival).toBeNull();
  });

  it("a later move or an epoch change retires a held arrival", () => {
    const h = harness();
    h.publish(log([arrival(walkNode(CX, CY))]));
    expect(h.travel().arrival).not.toBeNull();
    h.publish(walkPanels(CX + 1, CY));
    expect(h.travel().arrival).toBeNull();
    const g = harness();
    g.publish(log([arrival(walkNode(CX, CY))]));
    g.store.beginTransport(2);
    g.store.setConnected(true);
    g.accept("ui_snapshot", fx.snapshot({ presentation_epoch: fx.EPOCH_B, revision: 1, panels: walkPanels(CX, CY) }));
    expect(g.travel().arrival).toBeNull();
  });

  it("an arrival during a walk stops it before any next send", () => {
    const h = harness();
    h.store.holdTravel("east");
    vi.advanceTimersByTime(400);
    expect(h.moves()).toHaveLength(1);
    const request = h.moves()[0];
    const revision = h.store.view.revision + 1;
    h.accept("ui_update", fx.update({ revision, panels: { ...walkPanels(CX + 1, CY), ...log([arrival(walkNode(CX + 1, CY))]) } }));
    h.accept("ui_action_result", fx.actionResult({
      request_id: request.request_id, presentation_revision: revision, outcome: "success", code: "moved",
      message: "你向前走去。", data: { interrupts: [] },
    }));
    h.store.setTravelMap({ status: "ready", area: walkArea(CX + 1, CY) });
    vi.advanceTimersByTime(2000);
    expect(h.moves()).toHaveLength(1);
    expect(h.travel().walking).toBeNull();
    expect(h.travel().arrival).not.toBeNull();
  });

  it("the interrupt flag alone opens nothing", () => {
    const h = harness();
    h.store.stepTravel("east");
    const request = h.moves()[0];
    const revision = h.store.view.revision + 1;
    h.accept("ui_action_result", fx.actionResult({
      request_id: request.request_id, presentation_revision: revision, outcome: "success", code: "moved",
      message: "你向前走去。", data: { interrupts: ["landmark_reached"] },
    }));
    h.accept("ui_update", fx.update({ revision, panels: walkPanels(CX + 1, CY) }));
    expect(h.travel().arrival).toBeNull();
  });
});

describe("LandmarkCard", () => {
  let wrappers = [];
  afterEach(() => {
    for (const w of wrappers) w.unmount();
    wrappers = [];
    document.body.innerHTML = "";
  });

  function card(props) {
    const w = mount(LandmarkCard, {
      attachTo: document.body,
      props: { arrival: { id: "x", name: "合成古塔", litDistrict: null, prose: "風。", artwork: null, ...props }, artPanel: { available: true } },
    });
    wrappers.push(w);
    return w;
  }

  it("shows the supplied art and the district line only when this arrival lit it", () => {
    const plain = card({});
    expect(plain.find('[data-testid="artwork-preview"]').exists()).toBe(false);
    expect(plain.find('[data-testid="landmark-card-lit"]').exists()).toBe(false);
    expect(plain.get('[data-testid="landmark-card-name"]').text()).toBe("合成古塔");
    const lit = card({ litDistrict: "合成東麓", artwork: sceneDescriptor() });
    expect(lit.find('[data-testid="artwork-preview"]').exists()).toBe(true);
    expect(lit.get('[data-testid="landmark-card-lit"]').text()).toContain("合成東麓");
    expect(lit.get('[data-testid="landmark-card"]').attributes()).toMatchObject({ role: "dialog", "aria-modal": "true" });
  });

  it.each(["Enter", "Escape"])("%s closes once and stays inside the card", async (key) => {
    const w = card({});
    expect(document.activeElement).toBe(w.get('[data-testid="landmark-card-continue"]').element);
    const reached = vi.fn();
    document.addEventListener("keydown", reached);
    await w.get('[data-testid="landmark-card"]').trigger("keydown", { key });
    await w.get('[data-testid="landmark-card"]').trigger("keydown", { key });
    document.removeEventListener("keydown", reached);
    expect(w.emitted("continue")).toHaveLength(1);
    expect(reached).not.toHaveBeenCalled();
  });

  it("Continue closes once and Tab keeps focus inside", async () => {
    const w = card({});
    const go = w.get('[data-testid="landmark-card-continue"]');
    await w.get('[data-testid="landmark-card"]').trigger("keydown", { key: "Tab" });
    expect(document.activeElement).toBe(go.element);
    await go.trigger("click");
    await go.trigger("click");
    expect(w.emitted("continue")).toHaveLength(1);
  });
});

describe("the mounted card", () => {
  let wrappers = [];
  afterEach(() => {
    for (const w of wrappers) w.unmount();
    wrappers = [];
    document.body.innerHTML = "";
    localStorage.clear();
  }, 60000);

  function sleepHandoffPanel() {
    return {
      schema_version: 1,
      available: true,
      owner_id: 42,
      controlled_body_id: 42,
      transition_id: "42:v:1",
      selection: {
        available: true,
        rows: [{ kind: "possess", identity: 2, name: "同伴", reserve_percent: 100, stage: "normal", label: "接手 同伴（精力 100%）", enabled: true, reason: null }],
      },
      party: { label: "全員一起睡眠", enabled: true, reason: null },
      controlled_sleep: { sleep_id: "sleep-1", revision: 0 },
      owner_sleep: {
        sleep_id: "sleep-1", revision: 0, generation: 1, dream_pending: false, continuation: "none",
        continuation_available: false, continuation_reason: null,
      },
    };
  }

  async function stage() {
    const h = liveTravel({ wrappers, panels: walkPanels(CX, CY) });
    await tick();
    await h.answerMap(walkArea(CX, CY));
    await tick();
    const map = () => h.w.get('[data-testid="travel-map"]');
    const cardEl = () => h.w.find('[data-testid="landmark-card"]');
    return { ...h, map, cardEl };
  }

  it("takes focus, closes on Enter and returns focus to the map without a step", async () => {
    const s = await stage();
    s.map().element.focus();
    s.publish(log([arrival(walkNode(CX, CY))]));
    await tick();
    expect(s.cardEl().exists()).toBe(true);
    expect(document.activeElement).toBe(s.w.get('[data-testid="landmark-card-continue"]').element);
    await s.cardEl().trigger("keydown", { key: "Enter" });
    await tick();
    await tick();
    expect(s.cardEl().exists()).toBe(false);
    expect(document.activeElement).toBe(s.map().element);
    expect(s.sender.sent.actions.filter((a) => a.action_id === "explore.move")).toHaveLength(0);
    expect(s.store.view.travel.walking).toBeNull();
  });

  it("waits behind the sleep handoff and opens after it only while its cell is current", async () => {
    const s = await stage();
    s.publish({ sleep_handoff: sleepHandoffPanel() });
    await tick();
    expect(s.w.find('[data-testid="sleep-handoff-card"]').exists()).toBe(true);
    s.publish({ ...log([arrival(walkNode(CX, CY))]), sleep_handoff: sleepHandoffPanel() });
    await tick();
    // The higher-priority card keeps the anchor and its focus.
    expect(s.cardEl().exists()).toBe(false);
    expect(s.w.find('[data-testid="sleep-handoff-card"]').exists()).toBe(true);
    s.accept("ui_update", fx.update({ revision: s.next(), panels: {}, removed_panels: ["sleep_handoff"] }));
    await tick();
    expect(s.cardEl().exists()).toBe(true);
  });

  it("an arrival held behind a higher-priority card is discarded once the party moved on", async () => {
    const s = await stage();
    s.publish({ ...log([arrival(walkNode(CX, CY))]), sleep_handoff: sleepHandoffPanel() });
    await tick();
    expect(s.cardEl().exists()).toBe(false);
    // The party moved on before the higher-priority card closed.
    s.publish({ ...walkPanels(CX + 1, CY), sleep_handoff: sleepHandoffPanel() });
    s.accept("ui_update", fx.update({ revision: s.next(), panels: walkPanels(CX + 1, CY), removed_panels: ["sleep_handoff"] }));
    await tick();
    expect(s.cardEl().exists()).toBe(false);
    expect(s.store.view.travel.arrival).toBeNull();
  });
});
