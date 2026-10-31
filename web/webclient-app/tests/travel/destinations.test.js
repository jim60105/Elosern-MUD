// Travel destination input (wilderness-travel-planning-ui, design "Map and
// keyboard interactions"): the mounted shell, the real composed store and its
// own area refresh owner, synthetic wilderness panels, pointer intents from
// the map and keyboard events on the focused map. Neighbour single-step
// precedence stays the walking slice's; only disclosed far cells preview or
// lock, and the Shift-arrow cursor reaches the same lock as a pointer click.

import { afterEach, describe, expect, it, vi } from "vitest";
import TravelMap from "../../components/travel/TravelMap.vue";
import { liveTravel, tick, walkArea, walkNode, walkPanels } from "./support.js";

vi.setConfig({ testTimeout: 60000 });

const CX = 60;
const CY = 80;
const FAR = { x: CX + 3, y: CY + 1 };

let wrappers = [];
afterEach(() => {
  vi.useRealTimers();
  for (const w of wrappers) w.unmount();
  wrappers = [];
  document.body.innerHTML = "";
  localStorage.clear();
}, 60000);

async function stage({ panels = walkPanels(CX, CY) } = {}) {
  const h = liveTravel({ wrappers, panels });
  await tick();
  await h.answerMap(walkArea(CX, CY, { reveal: 4 }));
  await tick();
  expect(h.store.view.travel.mapStatus).toBe("ready");
  const map = () => h.w.get('[data-testid="travel-map"]');
  const travelMap = () => h.w.findComponent(TravelMap);
  const moves = () => h.sender.sent.actions.filter((a) => a.action_id === "explore.move");
  const plans = () => h.sender.sent.actions.filter((a) => a.action_id === "travel.plan");
  const press = async (key, init = {}) => {
    const event = new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true, ...init });
    map().element.dispatchEvent(event);
    await tick();
    return event;
  };
  const pointer = async (name, cell) => {
    travelMap().vm.$emit(name, cell);
    await tick();
  };
  return { ...h, map, moves, plans, press, pointer, travel: () => h.store.view.travel };
}

describe("pointer destinations", () => {
  it("a far disclosed click locks and asks once without moving", async () => {
    const s = await stage();
    await s.pointer("pick", FAR);
    expect(s.travel().lockedDestination).toEqual(FAR);
    expect(s.plans().map((r) => r.payload.destination)).toEqual([FAR]);
    expect(s.moves()).toHaveLength(0);
    // A second click on the locked cell is route-ui's departure: nothing here.
    await s.pointer("pick", FAR);
    expect(s.plans()).toHaveLength(1);
    expect(s.moves()).toHaveLength(0);
    expect(s.w.get('[data-testid="leg-depart"]').attributes("aria-disabled")).toBe("true");
  });

  it("unknown and party clicks manufacture nothing", async () => {
    const s = await stage();
    await s.pointer("pick", { x: CX + 9, y: CY });
    await s.pointer("pick", { x: CX, y: CY });
    await s.pointer("hover", { x: CX + 9, y: CY });
    vi.useFakeTimers();
    vi.advanceTimersByTime(500);
    vi.useRealTimers();
    expect(s.travel()).toMatchObject({ lockedDestination: null, hover: null, plan: null });
    expect(s.plans()).toHaveLength(0);
    expect(s.moves()).toHaveLength(0);
  });

  it("a neighbour hover aims and its click steps, even with a destination locked", async () => {
    const s = await stage();
    await s.pointer("pick", FAR);
    await s.pointer("hover", { x: CX + 1, y: CY });
    expect(s.travel().aim).toBe("east");
    expect(s.travel().lockedDestination).toEqual(FAR);
    // The planner holds the gate until its answer; the step then goes.
    await s.pointer("pick", { x: CX + 1, y: CY });
    expect(s.moves()).toHaveLength(0);
    expect(s.travel().lockedDestination).toEqual(FAR);
  });

  it("a withheld-destination neighbour still steps through its direction row", async () => {
    const s = await stage({ panels: walkPanels(CX, CY, { withheld: ["north"] }) });
    await s.pointer("pick", { x: CX, y: CY + 1 });
    expect(s.moves().map((m) => m.payload)).toEqual([{ exit_ref: "e_wild_n", current_node: walkNode(CX, CY) }]);
    expect(s.travel().lockedDestination).toBeNull();
    expect(s.plans()).toHaveLength(0);
  });

  it("a gated neighbour refuses its step and never becomes a destination", async () => {
    const s = await stage({ panels: walkPanels(CX, CY, { disabled: { east: "城門已經關上。" } }) });
    await s.pointer("pick", { x: CX + 1, y: CY });
    expect(s.moves()).toHaveLength(0);
    expect(s.travel().notice?.message).toBe("城門已經關上。");
    expect(s.travel().lockedDestination).toBeNull();
    expect(s.plans()).toHaveLength(0);
  });
});

describe("keyboard destination cursor", () => {
  it("Shift-arrows plus Enter lock the same cell as a pointer click", async () => {
    const s = await stage();
    for (const key of ["ArrowRight", "ArrowRight", "ArrowRight", "ArrowUp"]) {
      const event = await s.press(key, { shiftKey: true });
      expect(event.defaultPrevented).toBe(true);
    }
    expect(s.w.find('[data-testid="travel-map__cursor"]').exists()).toBe(true);
    expect(s.travel().aim).toBeNull();
    await s.press("Enter");
    expect(s.travel().lockedDestination).toEqual(FAR);
    expect(s.plans().map((r) => r.payload.destination)).toEqual([FAR]);
    expect(s.moves()).toHaveLength(0);
    // The lock left cursor mode.
    expect(s.w.find('[data-testid="travel-map__cursor"]').exists()).toBe(false);
    // A later Enter with no aim and no cursor departs nothing.
    await s.press("Enter");
    expect(s.moves()).toHaveLength(0);
    expect(s.plans()).toHaveLength(1);
  });

  it("Enter on a neighbour cursor locks it and asks at once, without a step", async () => {
    const s = await stage();
    await s.press("ArrowRight", { shiftKey: true });
    // A neighbour is never hover-previewed; Enter asks for it directly.
    expect(s.plans()).toHaveLength(0);
    await s.press("Enter");
    expect(s.travel().lockedDestination).toEqual({ x: CX + 1, y: CY });
    expect(s.plans().map((r) => r.payload.destination)).toEqual([{ x: CX + 1, y: CY }]);
    expect(s.moves()).toHaveLength(0);
  });

  it("an unknown or party cursor cell is only inspected", async () => {
    const s = await stage();
    // Toward the party's own cell: one step out and back.
    await s.press("ArrowRight", { shiftKey: true });
    await s.press("ArrowLeft", { shiftKey: true });
    expect(s.w.findComponent(TravelMap).props("cursor")).toMatchObject({ party: true, lockable: false });
    expect(s.w.get('[data-testid="leg-intent"]').element.closest('[data-testid="leg-panel"]').dataset.intent).toBe("cursor");
    await s.press("Enter");
    expect(s.travel().lockedDestination).toBeNull();
    for (let i = 0; i < 6; i += 1) await s.press("ArrowRight", { shiftKey: true });
    expect(s.w.findComponent(TravelMap).props("cursor")).toMatchObject({ known: false, lockable: false });
    expect(s.w.get('[data-testid="travel-map__cursor"]').classes()).toContain("is-fog");
    await s.press("Enter");
    expect(s.travel().lockedDestination).toBeNull();
    expect(s.plans()).toHaveLength(0);
    expect(s.moves()).toHaveLength(0);
  });

  it("the cursor stays inside the current window", async () => {
    const s = await stage();
    for (let i = 0; i < 30; i += 1) await s.press("ArrowUp", { shiftKey: true });
    const grid = s.travel().map;
    const cursor = s.w.findComponent(TravelMap).props("cursor");
    expect(cursor.y).toBe(grid.origin.y + grid.height - 1);
    expect(cursor.x).toBe(CX);
  });

  it("an ordinary aim keeps Enter's single step over the cursor", async () => {
    const s = await stage();
    await s.press("ArrowRight", { shiftKey: true });
    await s.press("ArrowRight", { shiftKey: true });
    await s.press("ArrowRight");
    s.map().element.dispatchEvent(new KeyboardEvent("keyup", { key: "ArrowRight", bubbles: true }));
    await tick();
    expect(s.travel().aim).toBe("east");
    expect(s.w.find('[data-testid="travel-map__cursor"]').exists()).toBe(false);
    await s.press("Enter");
    expect(s.moves().map((m) => m.payload)).toEqual([{ exit_ref: "e_wild_e", current_node: walkNode(CX, CY) }]);
    expect(s.travel().lockedDestination).toBeNull();
  });

  it("Escape clears the aim, then the cursor, then the lock, then bubbles", async () => {
    const s = await stage();
    await s.pointer("pick", FAR);
    await s.press("ArrowRight", { shiftKey: true });
    await s.press("ArrowLeft");
    s.map().element.dispatchEvent(new KeyboardEvent("keyup", { key: "ArrowLeft", bubbles: true }));
    await tick();
    expect(s.travel().aim).toBe("west");
    await s.press("Escape");
    expect(s.travel().aim).toBeNull();
    expect(s.travel().lockedDestination).toEqual(FAR);
    await s.press("ArrowDown", { shiftKey: true });
    expect(s.w.find('[data-testid="travel-map__cursor"]').exists()).toBe(true);
    await s.press("Escape");
    expect(s.w.find('[data-testid="travel-map__cursor"]').exists()).toBe(false);
    expect(s.travel().lockedDestination).toEqual(FAR);
    const lockEscape = await s.press("Escape");
    expect(lockEscape.defaultPrevented).toBe(true);
    expect(s.travel()).toMatchObject({ lockedDestination: null, plan: null, planTarget: null });
    const bare = await s.press("Escape");
    expect(bare.defaultPrevented).toBe(false);
  });
});
