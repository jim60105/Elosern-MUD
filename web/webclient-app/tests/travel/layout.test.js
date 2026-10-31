// Travel selection and the shell remap (wilderness-travel-interface): the
// pure selection over committed panels, then the mounted shell switching its
// slots on committed changes only.

import { afterEach, describe, expect, it, vi } from "vitest";
import { travelRoom, travelSelection } from "../../components/travel/travel-model.js";
import { DIALOGUE_PANEL_SAMPLE } from "../../stories/fixtures.js";
import { TOWN_SUBJECT, WILD_SUBJECT, artFor, fx, liveTravel, panelsAt, tick } from "./support.js";

vi.setConfig({ testTimeout: 60000 });

let wrappers = [];
afterEach(() => {
  for (const w of wrappers) w.unmount();
  wrappers = [];
  document.body.innerHTML = "";
}, 60000);

describe("travel selection follows committed room identity", () => {
  it("selects only a committed wilderness scene in exploration", () => {
    const wild = { art: artFor(WILD_SUBJECT) };
    expect(travelSelection({ mode: "exploration", panels: wild })).toEqual({
      mode: true, layout: true, room: { subject_id: WILD_SUBJECT },
    });
    expect(travelSelection({ mode: "exploration", panels: { art: artFor(TOWN_SUBJECT) } })).toMatchObject({
      mode: false, layout: false, room: { subject_id: TOWN_SUBJECT },
    });
    // The server keeps the exploration mode; any other mode is not travel.
    for (const mode of ["combat", "dialogue", "creation", null]) {
      expect(travelSelection({ mode, panels: wild }).layout).toBe(false);
    }
  });

  it("never fabricates travel without an admitted scene descriptor", () => {
    expect(travelRoom(null)).toBeNull();
    expect(travelRoom({ available: false, reason: { code: "art_unavailable", message: "x" } })).toBeNull();
    const art = artFor(WILD_SUBJECT);
    expect(travelRoom({ ...art, scene: { ...art.scene, artwork: { ...art.scene.artwork, subject_id: 7 } } })).toBeNull();
    expect(travelSelection({ mode: "exploration", panels: {} })).toEqual({ mode: false, layout: false, room: null });
  });

  it("gives the stage back to a conversation, a dream or creation", () => {
    const art = artFor(WILD_SUBJECT);
    const talking = travelSelection({ mode: "exploration", panels: { art, dialogue: { available: true, kind: "dialogue" } } });
    expect([talking.mode, talking.layout]).toEqual([true, false]);
    const dreaming = travelSelection({ mode: "exploration", panels: { art, dream: { state: { open: true } } } });
    expect(dreaming.layout).toBe(false);
    expect(travelSelection({ mode: "exploration", panels: { art }, creation: true }).layout).toBe(false);
    // An unavailable conversation panel does not hold the stage.
    expect(travelSelection({ mode: "exploration", panels: { art, dialogue: { available: false } } }).layout).toBe(true);
  });
});

describe("the shell remaps its slots for travel", () => {
  const anchors = (w) => ({
    map: w.find('[data-testid="travel-map"]').exists(),
    medallions: w.find('[data-testid="party-medallions"]').exists(),
    lineup: w.find('[data-testid="anchor-actor-left"] [data-testid="stage-actor"]').exists(),
    right: w.find('[data-testid="anchor-actor-right"] [data-testid="stage-actor"]').exists(),
    minimap: w.find('[data-testid="anchor-map"] .local-map').exists(),
    travel: w.find('[data-testid="elosern-stage"]').attributes("data-travel") ?? null,
  });

  it("enters and leaves travel only on committed identity changes", async () => {
    const { w, publish, store } = liveTravel({ wrappers });
    await tick();
    expect(store.view.travel.layout).toBe(true);
    expect(anchors(w)).toEqual({ map: true, medallions: true, lineup: false, right: false, minimap: false, travel: "true" });
    // The scene backdrop stays mounted under the map for the region's art.
    expect(w.find('[data-testid="anchor-actor-left"]').element.children).toHaveLength(0);

    // A committed settlement identity restores the ordinary composition.
    publish({ art: artFor(TOWN_SUBJECT) });
    await tick();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(store.view.travel.layout).toBe(false);
    const town = anchors(w);
    expect([town.medallions, town.lineup, town.minimap, town.travel]).toEqual([false, true, true, null]);

    // Back out of the gate: travel returns on the next commit.
    publish({ art: artFor(WILD_SUBJECT) });
    await tick();
    expect(anchors(w).medallions).toBe(true);
    expect(anchors(w).lineup).toBe(false);
  });

  it("lets a conversation in the wilderness use its own layout and returns after it", async () => {
    const { w, publish, store } = liveTravel({ wrappers });
    await tick();
    publish({ dialogue: DIALOGUE_PANEL_SAMPLE }, { mode: "dialogue" });
    await tick();
    expect(store.view.travel).toMatchObject({ mode: false, layout: false });
    expect(w.find('[data-testid="party-medallions"]').exists()).toBe(false);
    expect(w.find('[data-testid="anchor-actor-left"] [data-testid="stage-actor"]').exists()).toBe(true);
    publish({ dialogue: { schema_version: DIALOGUE_PANEL_SAMPLE.schema_version, available: false, reason: { code: "dialogue_unavailable", message: "目前沒有對話" } } }, { mode: "exploration" });
    await tick();
    expect(store.view.travel.layout).toBe(true);
    expect(w.find('[data-testid="party-medallions"]').exists()).toBe(true);
  });

  it("lands every switch in the commit's frame at motion off", async () => {
    const { w, publish, store } = liveTravel({ wrappers });
    store.setMotionLevel("off");
    await tick();
    publish({ art: artFor(TOWN_SUBJECT) });
    await tick();
    // No leaving copy lingers: the map is gone in the same render.
    expect(w.find('[data-testid="travel-map"]').exists()).toBe(false);
    publish({ art: artFor(WILD_SUBJECT) });
    await tick();
    expect(w.find('[data-testid="travel-map"]').exists()).toBe(true);
    expect(w.find(".travel-stage-enter-active").exists()).toBe(false);
  });

  it("selects nothing while the scene descriptor is unavailable", async () => {
    const { w, store } = liveTravel({
      wrappers,
      panels: panelsAt(WILD_SUBJECT, { art: { schema_version: 4, available: false, reason: { code: "art_unavailable", message: "場景圖像目前無法顯示" } } }),
    });
    await tick();
    expect(store.view.travel).toMatchObject({ mode: false, layout: false, room: null });
    expect(w.find('[data-testid="travel-map"]').exists()).toBe(false);
    expect(fx.EPOCH_A).toBe(store.view.epoch);
  });
});
