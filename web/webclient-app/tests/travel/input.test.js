// The travel stage's movement input (wilderness-travel-walking-ui, design
// "Input ownership"): the mounted shell, the real composed store and its
// own area refresh owner, synthetic wilderness panels, and keyboard events
// on the focused map.

import { afterEach, describe, expect, it, vi } from "vitest";
import TravelMap from "../../components/travel/TravelMap.vue";
import { fx, liveTravel, tick, walkArea, walkNode, walkPanels } from "./support.js";

vi.setConfig({ testTimeout: 60000 });

const CX = 60;
const CY = 80;

let wrappers = [];
afterEach(() => {
  vi.useRealTimers();
  for (const w of wrappers) w.unmount();
  wrappers = [];
  document.body.innerHTML = "";
}, 60000);

async function stage({ panels = walkPanels(CX, CY) } = {}) {
  const h = liveTravel({ wrappers, panels });
  await tick();
  await h.answerMap(walkArea(CX, CY));
  await tick();
  expect(h.store.view.travel.mapStatus).toBe("ready");
  const map = () => h.w.get('[data-testid="travel-map"]');
  const moves = () => h.sender.sent.actions.filter((a) => a.action_id === "explore.move");
  const key = async (type, init, target = map().element) => {
    const event = new KeyboardEvent(type, { bubbles: true, cancelable: true, ...init });
    target.dispatchEvent(event);
    await tick();
    return event;
  };
  const press = (k, init = {}) => key("keydown", { key: k, ...init });
  const lift = (k) => key("keyup", { key: k });
  return { ...h, map, moves, key, press, lift };
}

describe("the map owns movement in the travel layout", () => {
  it("focuses the map on entry and mounts no compass", async () => {
    const s = await stage();
    expect(s.w.findComponent({ name: "ExitCompass" }).exists()).toBe(false);
    expect(s.w.find('[data-testid="travel-walk-controls"]').exists()).toBe(true);
    expect(document.activeElement).toBe(s.map().element);
    expect(s.map().attributes("role")).toBe("application");
  });

  it("keeps the compass outside travel", async () => {
    const h = liveTravel({ wrappers, subject: "grid:t_synth_map:2,0" });
    await tick();
    expect(h.w.findComponent({ name: "ExitCompass" }).exists()).toBe(true);
    expect(h.w.find('[data-testid="travel-walk-controls"]').exists()).toBe(false);
  });
});

describe("aim, step and cancel", () => {
  it("a short arrow release plus Enter sends exactly one unchanged move", async () => {
    const s = await stage();
    await s.press("ArrowRight");
    await s.press("ArrowRight", { repeat: true });
    await s.lift("ArrowRight");
    expect(s.moves()).toHaveLength(0);
    expect(s.store.view.travel.aim).toBe("east");
    await s.press("Enter");
    await s.press("Enter", { repeat: true });
    await s.lift("Enter");
    expect(s.moves().map((m) => m.payload)).toEqual([{ exit_ref: "e_wild_e", current_node: walkNode(CX, CY) }]);
    // A second Enter while that step is unconfirmed is refused by the gate.
    await s.press("Enter");
    expect(s.moves()).toHaveLength(1);
  });

  it("two arrows aim a diagonal that survives a staggered release", async () => {
    const s = await stage();
    await s.press("ArrowUp");
    await s.press("ArrowRight");
    await s.lift("ArrowUp");
    await s.lift("ArrowRight");
    expect(s.store.view.travel.aim).toBe("northeast");
    expect(s.store.view.travel.aimTarget).toMatchObject({ direction: "northeast", enabled: true });
    expect(s.moves()).toHaveLength(0);
  });

  it("Escape clears the aim; a bare Escape bubbles", async () => {
    const s = await stage();
    await s.press("ArrowLeft");
    await s.lift("ArrowLeft");
    const consumed = await s.press("Escape");
    expect(consumed.defaultPrevented).toBe(true);
    expect(s.store.view.travel.aim).toBeNull();
    const bare = await s.press("Escape");
    expect(bare.defaultPrevented).toBe(false);
  });

  it("ignores modified keys and keys outside the focused map", async () => {
    const s = await stage();
    await s.press("ArrowRight", { ctrlKey: true });
    await s.press("ArrowRight", { shiftKey: true });
    expect(s.store.view.travel.aim).toBeNull();
    const input = document.createElement("input");
    document.body.appendChild(input);
    input.focus();
    await s.key("keydown", { key: "ArrowRight" }, input);
    await s.key("keydown", { key: "Enter" }, input);
    expect(s.store.view.travel.aim).toBeNull();
    expect(s.moves()).toHaveLength(0);
    // An open drawer owns input: nothing reaches the map's intents.
    s.store.openHudDrawer("party");
    await tick();
    await s.key("keydown", { key: "ArrowRight" }, document.body);
    expect(s.store.view.travel.aim).toBeNull();
  });

  it("an aim the committed row refuses is drawn blocked with its reason", async () => {
    const s = await stage({ panels: walkPanels(CX, CY, { disabled: { north: "斷崖擋住了去路。" } }) });
    const states = () => s.w.findAll('[data-testid="travel-map__neighbour"]').map((n) => n.attributes("data-state"));
    await s.press("ArrowUp");
    await s.lift("ArrowUp");
    expect(states()).toContain("blocked");
    expect(states()).not.toContain("aimed");
    expect(s.w.get('[data-testid="travel-map__aim-chip"]').text()).toContain("斷崖擋住了去路。");
    await s.press("ArrowRight");
    await s.lift("ArrowRight");
    expect(states()).toContain("aimed");
  });

  it("a neighbour click steps once; the party cell and far cells do nothing", async () => {
    const s = await stage();
    const map = s.w.findComponent(TravelMap);
    map.vm.$emit("pick", { x: CX, y: CY });
    map.vm.$emit("pick", { x: CX + 5, y: CY });
    await tick();
    expect(s.moves()).toHaveLength(0);
    map.vm.$emit("hover", { x: CX, y: CY + 1 });
    await tick();
    expect(s.store.view.travel.aim).toBe("north");
    map.vm.$emit("pick", { x: CX - 1, y: CY - 1 });
    await tick();
    expect(s.moves().map((m) => m.payload.exit_ref)).toEqual(["e_wild_sw"]);
  });
});

describe("the held walk", () => {
  async function walking() {
    const s = await stage();
    vi.useFakeTimers();
    await s.press("ArrowRight");
    vi.advanceTimersByTime(399);
    await tick();
    expect(s.moves()).toHaveLength(0);
    vi.advanceTimersByTime(1);
    await tick();
    expect(s.moves()).toHaveLength(1);
    expect(s.store.view.travel.walking).toMatchObject({ direction: "east" });
    return s;
  }

  it("arrow auto-repeat continues and the release stops it", async () => {
    const s = await walking();
    await s.press("ArrowRight", { repeat: true });
    expect(s.store.view.travel.walking).not.toBeNull();
    await s.lift("ArrowRight");
    expect(s.store.view.travel.walking).toBeNull();
    vi.advanceTimersByTime(3000);
    expect(s.moves()).toHaveLength(1);
  });

  it("a new key stops the walk first and does not also step", async () => {
    const s = await walking();
    const enter = await s.press("Enter");
    expect(s.store.view.travel.walking).toBeNull();
    expect(enter.defaultPrevented).toBe(true);
    expect(s.moves()).toHaveLength(1);
    // The stopping event reaches the document listeners unchanged.
    const s2 = await walking();
    const other = await s2.key("keydown", { key: "x" });
    expect(other.defaultPrevented).toBe(false);
    expect(s2.store.view.travel.walking).toBeNull();
    expect(s2.store.view.travel.aim).toBe("east");
  });

  it("another arrow stops the walk without re-aiming or stepping", async () => {
    const s = await walking();
    await s.press("ArrowUp");
    expect(s.store.view.travel.walking).toBeNull();
    expect(s.store.view.travel.aim).toBe("east");
    expect(s.moves()).toHaveLength(1);
  });

  it("停步 stops it and returns focus to the map", async () => {
    const s = await walking();
    const stop = s.w.get('[data-testid="travel-walk-stop"]');
    expect(stop.attributes("aria-disabled")).toBeUndefined();
    stop.element.focus();
    await stop.trigger("click");
    await tick();
    expect(s.store.view.travel.walking).toBeNull();
    expect(document.activeElement).toBe(s.map().element);
    expect(stop.attributes("aria-disabled")).toBe("true");
  });

  it("blur and a window blur stop it", async () => {
    const s = await walking();
    s.map().element.blur();
    await tick();
    expect(s.store.view.travel.walking).toBeNull();
    const s2 = await walking();
    window.dispatchEvent(new Event("blur"));
    await tick();
    expect(s2.store.view.travel.walking).toBeNull();
  });

  it("a committed step refreshes the map and the walk resumes after it", async () => {
    const s = await walking();
    const step = s.moves()[0];
    const revision = s.next();
    s.result(step, revision, "success", "moved");
    s.accept("ui_update", fx.update({ revision, panels: walkPanels(CX + 1, CY) }));
    await tick();
    expect(s.store.view.travel.walking.progress).toBe(1);
    expect(s.store.view.travel.mapStatus).toBe("refreshing");
    vi.advanceTimersByTime(1000);
    await tick();
    expect(s.moves()).toHaveLength(1);
    await s.answerMap(walkArea(CX + 1, CY));
    await tick();
    expect(s.moves()).toHaveLength(2);
    expect(s.moves()[1].payload.current_node).toBe(walkNode(CX + 1, CY));
  });
});
