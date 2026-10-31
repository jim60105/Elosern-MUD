// The travel stage's area refresh owner (wilderness-travel-interface, design
// "Current-protocol adapter and refresh owner"), driven through the real
// composed store and a fake sender with the mounted shell.

import { afterEach, describe, expect, it, vi } from "vitest";
import { LOCAL_MAP_WILDERNESS_RETURN_SAMPLE } from "../../stories/fixtures.js";
import { townArea } from "../../stories/fixtures/area_map.js";
import { TOWN_SUBJECT, WILD_SUBJECT, artFor, fx, liveTravel, panelsAt, tick, wildernessArea } from "./support.js";

vi.setConfig({ testTimeout: 60000 });

let wrappers = [];
afterEach(() => {
  for (const w of wrappers) w.unmount();
  wrappers = [];
  document.body.innerHTML = "";
}, 60000);

const unavailableArea = () => ({
  schema_version: 2, available: false, reason: { code: "map_unavailable", message: "這一帶的地圖目前無法顯示" },
});

function travel(store) {
  return store.view.travel;
}

async function ready(harness) {
  await tick();
  await harness.answerMap(wildernessArea());
  expect(travel(harness.store).mapStatus).toBe("ready");
}

describe("the travel stage requests its own area map", () => {
  it("asks once on entry with the drawer closed and shows fog until adoption", async () => {
    const h = liveTravel({ wrappers });
    await tick();
    expect(h.mapViews().map((a) => a.payload)).toEqual([{ scope: "area" }]);
    expect(travel(h.store)).toMatchObject({ mapStatus: "refreshing", mapReady: false, map: null, area: null });
    const map = h.w.get('[data-testid="travel-map"]');
    expect(map.attributes("data-map-shown")).toBe("false");
    // Nothing else asks while the request is out.
    await tick();
    expect(h.mapViews()).toHaveLength(1);
  });

  it("sends one request for every cause one publication raises", async () => {
    const h = liveTravel({ wrappers, subject: TOWN_SUBJECT });
    await tick();
    expect(h.mapViews()).toHaveLength(0);
    // Entry, a new current node and a recovery snapshot at once.
    h.accept("ui_snapshot", fx.snapshot({
      revision: h.next(),
      panels: panelsAt(WILD_SUBJECT, { local_map: LOCAL_MAP_WILDERNESS_RETURN_SAMPLE }),
    }));
    await tick();
    expect(h.mapViews()).toHaveLength(1);
    await h.answerMap(wildernessArea());
    expect([travel(h.store).mapStatus, h.mapViews().length, h.store.view.dispatch.inFlight]).toEqual(["ready", 1, null]);
  });

  it.each(["body-first", "result-first"])("adopts only its own complete body (%s)", async (order) => {
    const h = liveTravel({ wrappers });
    await tick();
    const request = h.mapViews().at(-1);
    // A body published by another publication before the answer is not this
    // request's body, and cannot make the stage ready.
    h.publish({ area_map: wildernessArea() });
    await tick();
    expect(travel(h.store).mapStatus).toBe("refreshing");
    await h.answerMap(wildernessArea(), order);
    expect(travel(h.store)).toMatchObject({ mapStatus: "ready", mapReady: true });
    expect(travel(h.store).map.party).toEqual({ x: 100, y: 200 });
    expect(h.w.get('[data-testid="travel-map"]').attributes("data-map-shown")).toBe("true");
    expect(h.w.find('[data-testid="travel-map"] [data-testid="area-map"]').exists()).toBe(true);
    // A result for another request id leaves the adopted state alone.
    expect(() => h.result({ request_id: "session:999" }, h.store.view.revision)).not.toThrow();
    await tick();
    expect(travel(h.store).mapStatus).toBe("ready");
    expect(h.mapViews()).toEqual([request]);
  });

  it("refreshes after a committed step, coalescing steps that land while it waits", async () => {
    const h = liveTravel({ wrappers });
    await ready(h);
    const shown = travel(h.store).area;
    // A committed step: the canonical current node changes.
    const move = h.store.dispatchAction("explore.move", { exit_ref: "east", current_node: "wild:elosern:858:1071" });
    const revision = h.next();
    h.result({ request_id: move }, revision, "success", "moved");
    h.publish({ local_map: LOCAL_MAP_WILDERNESS_RETURN_SAMPLE });
    await tick();
    expect(h.mapViews()).toHaveLength(2);
    // The last map stays, dimmed, while the next one settles.
    expect(travel(h.store)).toMatchObject({ mapStatus: "refreshing", mapReady: false, area: shown });
    expect(h.w.get('[data-testid="travel-map"]').attributes("data-map-status")).toBe("refreshing");
    // Two more committed changes while that request is out owe one more.
    h.publish({}, { server_time: fx.serverTime({ minute: 10 }) });
    h.publish({}, { server_time: fx.serverTime({ minute: 20 }) });
    await tick();
    expect(h.mapViews()).toHaveLength(2);
    await h.answerMap(wildernessArea());
    // The answered map is adopted, but the stage still owes the later one.
    expect(travel(h.store).mapStatus).toBe("refreshing");
    expect(h.mapViews()).toHaveLength(3);
    await h.answerMap(wildernessArea(), "result-first");
    expect(travel(h.store).mapStatus).toBe("ready");
    await tick();
    expect(h.mapViews()).toHaveLength(3);
  });

  it("never refreshes for a refused move, a render or an unchanged commit", async () => {
    const h = liveTravel({ wrappers });
    await ready(h);
    const move = h.store.dispatchAction("explore.move", { exit_ref: "east", current_node: "wild:elosern:858:1071" });
    h.result({ request_id: move }, h.store.view.revision, "rejected", "blocked");
    await tick();
    // An unrelated committed panel at the same place and time.
    h.publish({ status: fx.statusPanel({ resources: { hp: { current: 70, maximum: 100 } } }) });
    await tick();
    window.dispatchEvent(new Event("resize"));
    await tick();
    expect(h.mapViews()).toHaveLength(1);
    expect(travel(h.store).mapStatus).toBe("ready");
  });

  it("refreshes after a completed room look", async () => {
    const h = liveTravel({ wrappers });
    await ready(h);
    const look = h.store.dispatchAction("explore.look", {}, null);
    await tick();
    const revision = h.next();
    h.result({ request_id: look }, revision);
    h.publish({});
    await tick();
    expect(h.mapViews()).toHaveLength(2);
  });

  it("waits for an open drawer or overlay and asks once it closes", async () => {
    const h = liveTravel({ wrappers });
    await ready(h);
    h.store.openOverlay("settings");
    await tick();
    h.publish({ local_map: LOCAL_MAP_WILDERNESS_RETURN_SAMPLE });
    await tick();
    expect(h.mapViews()).toHaveLength(1);
    expect(travel(h.store).mapStatus).toBe("refreshing");
    h.store.closeOverlay();
    await tick();
    expect(h.mapViews()).toHaveLength(2);
  });
});

describe("failed reads and recovery", () => {
  it("stops on an unavailable map and recovers once at the same position", async () => {
    const h = liveTravel({ wrappers });
    await tick();
    await h.answerMap(unavailableArea());
    expect(travel(h.store).mapStatus).toBe("unavailable");
    expect(h.w.find('[data-testid="travel-map__state"]').exists()).toBe(true);
    // No polling: time passing in the client asks nothing.
    await new Promise((resolve) => setTimeout(resolve, 30));
    await tick();
    expect(h.mapViews()).toHaveLength(1);
    // An external full snapshot at the very same position and time.
    h.accept("ui_snapshot", fx.snapshot({ revision: h.next(), panels: panelsAt(WILD_SUBJECT) }));
    await tick();
    expect(h.mapViews()).toHaveLength(2);
    expect(travel(h.store).mapStatus).toBe("refreshing");
    await h.answerMap(wildernessArea());
    expect(travel(h.store).mapStatus).toBe("ready");
    // The owner's own map completion is an update, never a recovery.
    await tick();
    expect(h.mapViews()).toHaveLength(2);
  });

  it("states a refused read and a body it cannot use, each with one explicit retry", async () => {
    const h = liveTravel({ wrappers });
    await tick();
    h.result(h.mapViews().at(-1), h.store.view.revision, "rejected", "busy");
    await tick();
    expect(travel(h.store).mapStatus).toBe("unavailable");
    await h.w.get('[data-testid="travel-map__retry"]').trigger("click");
    await tick();
    expect(h.mapViews()).toHaveLength(2);
    // A settlement body cannot be read as the travel grid.
    await h.answerMap(townArea());
    expect(travel(h.store).mapStatus).toBe("invalid");
    expect(h.w.get('[data-testid="travel-map__state"]').text()).toContain("重新整理");
  });

  it("retires the map on a new epoch and asks again for that epoch's snapshot", async () => {
    const h = liveTravel({ wrappers });
    await ready(h);
    // A reconnect: a new transport generation establishes a new epoch.
    h.store.beginTransport(2);
    h.store.setConnected(true);
    await tick();
    h.accept("ui_snapshot", fx.snapshot({ presentation_epoch: fx.EPOCH_B, revision: 1, panels: panelsAt(WILD_SUBJECT) }));
    await tick();
    // The new session asked once; the previous epoch's map is gone.
    expect(travel(h.store).area).toBeNull();
    expect(h.mapViews()).toHaveLength(2);
    expect(h.mapViews().at(-1).presentation_epoch).toBe(fx.EPOCH_B);
  });

  it("drops its map on leaving, so a later entry starts from fog", async () => {
    const h = liveTravel({ wrappers });
    await ready(h);
    h.publish({ art: artFor(TOWN_SUBJECT) });
    await tick();
    expect(travel(h.store)).toMatchObject({ layout: false, area: null });
    h.publish({ art: artFor(WILD_SUBJECT) });
    await tick();
    expect(travel(h.store)).toMatchObject({ layout: true, area: null, mapStatus: "refreshing" });
    expect(h.mapViews()).toHaveLength(2);
  });
});

describe("movement waits for the current map", () => {
  it("suspends the compass while refreshing and stops it on a failed read", async () => {
    const h = liveTravel({ wrappers });
    await tick();
    const compass = () => h.w.findComponent({ name: "ExitCompass" });
    const props = () => (compass().exists() ? compass().props() : null);
    expect(compass().exists()).toBe(true);
    expect(props().busy).toBe(true);
    await h.answerMap(wildernessArea());
    await tick();
    expect(props().busy).toBe(false);
    expect(props().active).toBe(true);
    h.publish({ local_map: LOCAL_MAP_WILDERNESS_RETURN_SAMPLE });
    await tick();
    expect(props().busy).toBe(true);
    await h.answerMap(unavailableArea());
    await tick();
    expect(props().active).toBe(false);
  });
});
