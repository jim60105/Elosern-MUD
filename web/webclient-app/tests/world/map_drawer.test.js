// MapDrawer and its session workflow (OpenSpec change redesign-map-drawer).
// Each top-level describe block maps one-to-one to a webclient-map-drawer
// requirement; tests/test_map_client_contracts.py MapDrawerContracts checks
// that each block ran and passed. The store is a small reactive stand-in
// with the real admission rule (one in-flight request; the lock releases
// only once the committed revision reaches the result's declared revision).

import { existsSync, readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { defineComponent, h, nextTick, reactive, ref } from "vue";
import { createPinia, setActivePinia } from "pinia";
import AppClient from "../../AppClient.vue";
import { useElosernStore } from "../../stores/elosern.js";
import * as fx from "../store/protocol_fixtures.js";
import {
  LOCAL_MAP_ALTORIA_PLAZA_SAMPLE,
  LOCAL_MAP_ALTORIA_SOUTH_GATE_SAMPLE,
  LOCAL_MAP_SAMPLE,
  LOCAL_MAP_WILDERNESS_METRIC_SAMPLE,
  LOCAL_MAP_WILDERNESS_RETURN_SAMPLE,
  LOCAL_MAP_WILDERNESS_SAMPLE,
  localMapModelFor,
} from "../../stories/fixtures.js";
import MapFixtures from "../../../static/webclient/js/tests/map_panel_fixtures.js";
import MapDrawer from "../../components/MapDrawer.vue";
import MapLattice from "../../components/MapLattice.vue";
import MapNodeGlyph from "../../components/MapNodeGlyph.vue";
import AreaMapView from "../../components/AreaMapView.vue";
import WorldMapView from "../../components/WorldMapView.vue";
import { AREA_CELL_GLYPH_SCALE, ISLAND_GLYPH_SCALE, gatePath } from "../../lib/map_marker_geometry.js";
import { spanLimits, wildernessStops } from "../../lib/map_viewport.js";
import { viewSignature } from "../../lib/area_map_view.js";
import OverlayHost from "../../components/OverlayHost.vue";
import { areaMemoryKey, scopeForLayer, useMapDrawer } from "../../composables/use-map-drawer.js";
import { project, usableRect } from "../../lib/map_viewport.js";
import MapPanels from "../../../static/webclient/js/elosern/protocol/panels/map_panels.js";
import { TOWN_IDS, WILD_GATE_ID, dungeonArea, interiorArea, townArea, townFromEastArea, wildernessArea } from "../../stories/fixtures/area_map.js";
import { QUEST_IDS, newLight, worldBase, worldNewLight } from "../../stories/fixtures/world_map.js";

const { validateAreaMapPanel, validateWorldMapPanel } = MapPanels;
const APP_DIR = resolve(__dirname, "../..");

let wrappers = [];
afterEach(() => {
  for (const w of wrappers) w.unmount();
  wrappers = [];
  document.body.innerHTML = "";
  document.documentElement.style.removeProperty("--motion-district-reveal");
});

// ── fake store ──────────────────────────────────────────────────────────

function fakeStore({ layer = "grid" } = {}) {
  let counter = 0;
  const store = reactive({
    sent: [],
    view: {
      generation: 1,
      epoch: "epoch-a",
      revision: 10,
      connected: true,
      phase: "active",
      mutationsLocked: false,
      hudOverlay: null,
      localMapModel: { layer },
      lastActionResult: null,
      maps: {},
      dispatch: { inFlight: null, beatLocked: false },
    },
    dispatchAction(actionId, payload) {
      const v = store.view;
      if (!v.connected || v.mutationsLocked || v.phase !== "active" || v.dispatch.inFlight || v.dispatch.beatLocked) {
        return null;
      }
      counter += 1;
      const requestId = `session:${counter}`;
      store.sent.push({ actionId, payload, requestId });
      v.dispatch = { ...v.dispatch, inFlight: { requestId, presentationRevision: null } };
      return requestId;
    },
  });
  // The server answers the in-flight request at `revision`, committing the
  // presentation (and any maps) in the same publication.
  store.answer = (outcome = "success", code = "ok", maps = null) => {
    const v = store.view;
    const flight = v.dispatch.inFlight;
    const revision = v.revision + 1;
    v.lastActionResult = { epoch: v.epoch, requestId: flight.requestId, outcome, code, message: "", presentationRevision: revision };
    if (maps) v.maps = { ...v.maps, ...maps };
    v.revision = revision;
    v.dispatch = { ...v.dispatch, inFlight: null };
  };
  // A result whose presentation has not committed yet (lock still held).
  store.resultOnly = (outcome = "success", code = "moved") => {
    const v = store.view;
    const flight = v.dispatch.inFlight;
    v.lastActionResult = { epoch: v.epoch, requestId: flight.requestId, outcome, code, message: "", presentationRevision: v.revision + 1 };
    v.dispatch = { ...v.dispatch, inFlight: { ...flight, presentationRevision: v.revision + 1 } };
  };
  store.commit = () => {
    const v = store.view;
    v.revision += 1;
    v.dispatch = { ...v.dispatch, inFlight: null };
  };
  return store;
}

function mapViews(store) {
  return store.sent.filter((entry) => entry.actionId === "map.view").map((entry) => entry.payload.scope);
}

function withDrawer(store) {
  const moves = [];
  let api = null;
  const Host = defineComponent({
    setup() {
      api = useMapDrawer(store, {
        onMapMove: (payload) => {
          moves.push(payload);
          return store.dispatchAction("explore.move", { exit_ref: payload.exit_ref, current_node: payload.current_node });
        },
      });
      return () => h("div");
    },
  });
  const w = mount(Host);
  wrappers.push(w);
  return { api: () => api, moves, wrapper: w };
}

const tick = async () => {
  await nextTick();
  await nextTick();
};

// ── drawer mount ────────────────────────────────────────────────────────

function blankMemory() {
  return reactive({ area: { key: null, view: undefined, selected: undefined }, world: { view: undefined, selected: undefined } });
}

function mountDrawer(props = {}) {
  const host = document.createElement("div");
  host.style.cssText = "position:relative;width:1200px;height:700px";
  document.body.appendChild(host);
  const memory = props.memory ?? blankMemory();
  const state = reactive({ tab: props.tab ?? "area" });
  const emitted = { move: [], close: 0 };
  const w = mount(
    defineComponent({
      setup() {
        return () =>
          h(MapDrawer, {
            area: props.area === undefined ? validateAreaMapPanel(townArea()) : props.area,
            world: props.world === undefined ? validateWorldMapPanel(worldBase()) : props.world,
            tab: state.tab,
            memory,
            epoch: props.epoch ?? "1|epoch-a",
            locationLabel: "灰岩鎮",
            busy: props.busy ?? false,
            "onUpdate:tab": (tab) => {
              state.tab = tab;
            },
            onMove: (payload) => emitted.move.push(payload),
            onClose: () => {
              emitted.close += 1;
            },
          });
      },
    }),
    { attachTo: host },
  );
  wrappers.push(w);
  return { w, memory, state, emitted };
}

async function selectAreaNode(w, id) {
  const el = w.findAll('[data-testid="area-map__node"]').find((n) => n.attributes("data-node-id") === id);
  await el.trigger("pointerdown", { button: 0, clientX: 5, clientY: 5 });
  await el.trigger("pointerup", { button: 0, clientX: 5, clientY: 5 });
}

function key(el, name, extra = {}) {
  return el.trigger("keydown", { key: name, ...extra });
}

// ───────────────────────────────────────────────────────────────────────

describe("the map drawer opens the appropriate scope and preserves session views", () => {
  it("opens on the area tab in settlements, dungeons and interiors and on the world tab in the wilderness", () => {
    expect(scopeForLayer("grid")).toBe("area");
    expect(scopeForLayer("instance")).toBe("area");
    expect(scopeForLayer("interior")).toBe("area");
    expect(scopeForLayer("wilderness")).toBe("world");
  });

  it("chooses the scope by the current layer on every opening", async () => {
    const store = fakeStore({ layer: "wilderness" });
    const { api } = withDrawer(store);
    store.view.hudOverlay = "map";
    await tick();
    expect(api().mapTab.value).toBe("world");
    expect(mapViews(store)).toEqual(["world"]);
    store.answer();
    store.view.hudOverlay = null;
    await tick();
    store.view.localMapModel = { layer: "grid" };
    store.view.hudOverlay = "map";
    await tick();
    expect(api().mapTab.value).toBe("area");
    expect(mapViews(store)).toEqual(["world", "area"]);
  });

  it("keeps each tab's pan, zoom and selection for the session and across reopening", async () => {
    const { w, memory, state } = mountDrawer();
    await tick();
    const areaView = { signature: "grid|story_town|m", cx: 450, cy: 320, span: 700 };
    memory.area.view = areaView;
    memory.area.selected = TOWN_IDS.east;
    await tick();
    expect(w.find('[data-testid="area-map__svg"]').exists()).toBe(true);
    await w.find('[data-testid="map-drawer-tab--world"]').trigger("click");
    await tick();
    expect(state.tab).toBe("world");
    expect(w.find('[data-testid="world-map"]').exists()).toBe(true);
    const worldView = memory.world.view;
    expect(worldView?.signature).toBe("world|elosern|km");
    await w.find('[data-testid="map-drawer-tab--area"]').trigger("click");
    await tick();
    expect(memory.area.view).toEqual(areaView);
    expect(memory.area.selected).toBe(TOWN_IDS.east);
    expect(w.find('[data-testid="area-map-detail__title"]').text()).toBe("銅匠街");
    expect(memory.world.view).toEqual(worldView);
  });

  it("opens a new world view at 國 around the player and fits a tracked commission within 800 km", async () => {
    const { w, memory } = mountDrawer({ tab: "world" });
    await tick();
    expect(memory.world.view.span).toBe(800);
    expect(w.find('[data-testid="world-map__stop"]').text()).toBe("國");
    // The tracked commission (護送藥草商人, about 175 km away) is on screen.
    expect(w.findAll('[data-testid="world-map__quest"]').some((q) => q.attributes("data-quest") === QUEST_IDS.exact)).toBe(true);
  });

  it("retires every view, selection and pending request on a new epoch", async () => {
    const store = fakeStore();
    const { api } = withDrawer(store);
    store.view.hudOverlay = "map";
    await tick();
    api().mapMemory.area.view = { signature: "grid|story_town|m", cx: 1, cy: 2, span: 300 };
    api().mapMemory.world.selected = "quest:q";
    store.view.epoch = "epoch-b";
    await tick();
    expect(api().mapMemory.area.view).toBeUndefined();
    expect(api().mapMemory.world.selected).toBeUndefined();
    expect(api().mapEpoch.value).toBe("1|epoch-b");
  });

  it("puts the drawer header in place of the host header, with ARIA tabs and one close control", async () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    let closed = 0;
    const w = mount(OverlayHost, {
      props: { overlay: "map", ownHeader: true, locationLabel: "灰岩鎮", onClose: () => (closed += 1) },
      slots: {
        default: (slot) =>
          h(MapDrawer, {
            area: validateAreaMapPanel(townArea()),
            world: null,
            tab: "area",
            memory: blankMemory(),
            onClose: slot.close,
          }),
      },
      attachTo: host,
    });
    wrappers.push(w);
    await tick();
    expect(w.findAll(".drawer-header")).toHaveLength(1);
    expect(w.findAll('[data-testid="overlay-host-close"]')).toHaveLength(1);
    const tabs = w.findAll('[role="tab"]');
    expect(tabs.map((t) => t.text())).toEqual(["區域1", "世界2"]);
    expect(tabs[0].attributes("aria-selected")).toBe("true");
    expect(tabs[0].attributes("aria-keyshortcuts")).toBe("1");
    expect(w.find('[role="tabpanel"]').attributes("aria-labelledby")).toBe(tabs[0].attributes("id"));
    expect(w.find(".drawer-header__subtitle").text()).toBe("灰岩鎮街道圖");
    // The trap's first stop is the active tab.
    expect(document.activeElement).toBe(tabs[0].element);
    await w.find('[data-testid="overlay-host-close"]').trigger("click");
    expect(closed).toBe(1);
  });

  it("brings the player back into view after a move on the same map, keeping the zoom", async () => {
    const memory = blankMemory();
    const area = ref(validateAreaMapPanel(townArea()));
    const host = document.createElement("div");
    document.body.appendChild(host);
    const w = mount(
      defineComponent({
        setup: () => () => h(MapDrawer, { area: area.value, world: null, tab: "area", memory }),
      }),
      { attachTo: host },
    );
    wrappers.push(w);
    await tick();
    // A view parked far west of the town, at 400 m across.
    memory.area.view = Object.freeze({ signature: "grid|story_town|m", cx: -2000, cy: 300, span: 400 });
    await tick();
    area.value = validateAreaMapPanel(townFromEastArea());
    await tick();
    await tick();
    expect(memory.area.view.span).toBe(400);
    expect(Math.abs(memory.area.view.cx - 520)).toBeLessThan(400);
  });

  it.each(["frame", "epoch"])("discards queued follow work after %s retirement", async (retirement) => {
    const memory = blankMemory();
    const area = ref(validateAreaMapPanel(townArea()));
    const epoch = ref("epoch-a");
    const w = mount(defineComponent({
      setup: () => () => h(MapDrawer, { area: area.value, world: null, tab: "area", memory, epoch: epoch.value }),
    }));
    wrappers.push(w);
    await tick();
    memory.area.view = Object.freeze({ signature: "grid|story_town|m", cx: -2000, cy: 300, span: 400 });
    await tick();
    area.value = validateAreaMapPanel(townFromEastArea());
    // Retire a movement and its coordinate frame within the same publication.
    if (retirement === "frame") area.value = validateAreaMapPanel(interiorArea());
    else {
      epoch.value = "epoch-b";
      area.value = null;
    }
    memory.area.view = undefined;
    await tick();
    if (retirement === "frame") {
      expect(memory.area.view.signature).toBe("interior|room:120|none");
      expect(Math.abs(memory.area.view.cx)).toBeLessThan(400);
    } else expect(memory.area.view).toBeUndefined();
  });

  it("opens with focus on the selected tab even when it is not the first", async () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    const w = mount(OverlayHost, {
      props: { overlay: "map", ownHeader: true },
      slots: {
        default: () =>
          h(MapDrawer, { area: null, world: validateWorldMapPanel(worldBase()), tab: "world", memory: blankMemory() }),
      },
      attachTo: host,
    });
    wrappers.push(w);
    await tick();
    expect(document.activeElement).toBe(w.find('[data-testid="map-drawer-tab--world"]').element);
  });
});

describe("map requests follow explicit scope and committed moves only while open", () => {
  function liveDrawer(layer = "wilderness") {
    setActivePinia(createPinia());
    const store = useElosernStore();
    const sender = fx.createFakeSender();
    store.setSender(sender);
    store.beginTransport(1);
    store.setConnected(true);
    const local = layer === "wilderness" ? LOCAL_MAP_WILDERNESS_METRIC_SAMPLE : fx.localMapPanel();
    expect(store.receive(1, "ui_snapshot", [fx.snapshot({
      panels: { status: fx.statusPanel(), context_actions: fx.explorationActions(), local_map: local },
    })], {}).accepted).toBe(true);
    const w = mount(AppClient, { attachTo: document.body });
    wrappers.push(w);
    const receive = (name, body) => expect(store.receive(store.view.generation, name, [body], {}).accepted).toBe(true);
    const publish = (world, revision = store.view.revision + 1) => {
      receive("ui_update", fx.update({ revision, panels: { world_map: world } }));
      return revision;
    };
    const result = (request, revision, outcome = "success", code = "completed") =>
      receive("ui_action_result", fx.actionResult({
        request_id: request.request_id, presentation_revision: revision, outcome, code,
      }));
    const reply = async (world, order = "body-first", outcome = "success") => {
      const request = sender.sent.actions.at(-1);
      const revision = store.view.revision + 1;
      if (order === "result-first") { result(request, revision, outcome); await tick(); }
      publish(world, revision);
      await tick();
      if (order === "body-first") { result(request, revision, outcome); await tick(); }
    };
    return { store, sender, w, receive, publish, result, reply };
  }

  it.each(["body-first", "result-first"])("cached reopen waits for its own silent fresh baseline (%s)", async (order) => {
    const { store, sender, w, receive, reply } = liveDrawer();
    store.openOverlay("map");
    await tick();
    await reply(worldBase(), order);
    const drawer = w.findComponent(MapDrawer);
    const saved = { signature: "world|elosern|km", cx: 1100, cy: 1200, span: 420 };
    drawer.props("memory").world.view = saved;
    await tick();
    store.closeOverlay();
    await tick();
    // A committed movement while closed publishes no expensive map.
    receive("ui_snapshot", fx.snapshot({ revision: store.view.revision + 1, panels: { status: fx.statusPanel(), local_map: LOCAL_MAP_WILDERNESS_METRIC_SAMPLE } }));
    store.openOverlay("map");
    await tick();
    expect(w.find('[data-testid="world-map"]').exists()).toBe(false);
    const mark = store.view.mapPublications.world_map;
    receive("ui_snapshot", fx.snapshot({ revision: store.view.revision + 1, panels: { status: fx.statusPanel(), local_map: LOCAL_MAP_WILDERNESS_METRIC_SAMPLE } }));
    await tick();
    expect(store.view.mapPublications.world_map).toBe(mark);
    expect(w.find('[data-testid="world-map"]').exists()).toBe(false);
    await reply(worldNewLight(), order);
    expect(w.find('[data-testid="world-map"]').exists()).toBe(true);
    expect(w.find('[data-testid="world-map__ink"]').exists()).toBe(false);
    expect(w.get('[data-testid="world-map__discovery"]').text()).toBe("");
    expect(w.findComponent(MapDrawer).props("memory").world.view).toEqual(saved);
    const count = sender.sent.actions.length;
    const revision = store.view.revision + 1;
    receive("ui_update", fx.update({ revision, panels: { world_map: worldNewLight() } }));
    await tick();
    expect(w.get('[data-testid="world-map__discovery"]').text()).toBe("");
    expect(sender.sent.actions).toHaveLength(count);
  });

  it.each(["body-first", "result-first"])("retains a pending movement refresh after the opening baseline (%s)", async (order) => {
    document.documentElement.style.setProperty("--motion-district-reveal", "600ms");
    const { store, sender, w, receive, reply } = liveDrawer();
    // A movement was dispatched before the drawer opened. Its result can
    // arrive before the baseline, and its refresh obligation survives it.
    const moveId = store.dispatchAction("explore.move", { exit_ref: "east", current_node: LOCAL_MAP_WILDERNESS_METRIC_SAMPLE.current_node });
    store.openOverlay("map");
    await tick();
    const move = sender.sent.actions.at(-1);
    expect(move.request_id).toBe(moveId);
    const rev = store.view.revision + 1;
    receive("ui_action_result", fx.actionResult({ request_id: moveId, code: "moved", presentation_revision: rev }));
    receive("ui_update", fx.update({ revision: rev, panels: { status: fx.statusPanel() } }));
    await tick();
    expect(sender.sent.actions.filter(a => a.action_id === "map.view")).toHaveLength(1);
    await reply(worldBase(), order);
    const view = w.find('[data-testid="world-map"]').element;
    expect(w.get('[data-testid="world-map__discovery"]').text()).toBe("");
    // A later committed move triggers exactly one while-open refresh.
    const movementRevision = store.view.revision + 1;
    const requestId = store.dispatchAction("explore.move", { exit_ref: "east", current_node: LOCAL_MAP_WILDERNESS_METRIC_SAMPLE.current_node });
    receive("ui_action_result", fx.actionResult({ request_id: requestId, code: "moved", presentation_revision: movementRevision }));
    receive("ui_update", fx.update({ revision: movementRevision, panels: { status: fx.statusPanel() } }));
    await tick();
    expect(sender.sent.actions.filter(a => a.action_id === "map.view")).toHaveLength(2);
    expect(w.find('[data-testid="world-map"]').element).toBe(view);
    await reply(worldNewLight(), order);
    expect(w.find('[data-testid="world-map"]').element).toBe(view);
    expect(w.findAll('[data-testid="world-map__ink"]')).toHaveLength(1);
    expect(w.get('[data-testid="world-map__discovery"]').text()).toBe(`已探明：${newLight().name}`);
  });

  it("old openings, partial transfers and failed results never qualify cached knowledge", async () => {
    const { store, sender, w, publish, result, receive, reply } = liveDrawer();
    store.openOverlay("map");
    await tick();
    const oldRequest = sender.sent.actions.at(-1);
    store.closeOverlay();
    store.openOverlay("map");
    await tick();
    const oldRevision = publish(worldNewLight());
    result(oldRequest, oldRevision);
    await tick();
    expect(w.find('[data-testid="world-map"]').exists()).toBe(false);
    const own = sender.sent.actions.at(-1);
    expect(own.request_id).not.toBe(oldRequest.request_id);
    const revision = store.view.revision + 1;
    result(own, revision);
    const parts = MapFixtures.encodeParts(worldBase(), "P".repeat(22));
    // A part frame carries exactly its one panel: the shared snapshot fixture
    // would otherwise merge its default status panel in beside it.
    const partFrame = (part) => ({ ...fx.update({ revision }), panels: { world_map: part } });
    receive("ui_update", partFrame(parts[0]));
    await tick();
    expect(store.view.mapPublications.world_map).toBe(oldRevision);
    expect(w.find('[data-testid="world-map"]').exists()).toBe(false);
    for (const part of parts.slice(1)) receive("ui_update", partFrame(part));
    await tick();
    expect(w.find('[data-testid="world-map"]').exists()).toBe(true);
    expect(store.view.mapPublications.world_map).toBe(revision);
    store.closeOverlay();
    store.openOverlay("map");
    await tick();
    await reply(worldNewLight(), "result-first", "rejected");
    expect(w.find('[data-testid="world-map"]').exists()).toBe(false);
    store.beginTransport(2);
    await tick();
    expect(w.find('[data-testid="world-map__ink"]').exists()).toBe(false);
  });

  it("area-first requests only the active scope and qualifies world independently", async () => {
    const { store, sender, w, receive, result, reply } = liveDrawer("interior");
    store.openOverlay("map");
    await tick();
    expect(sender.sent.actions.map(a => a.payload.scope)).toEqual(["area"]);
    const request = sender.sent.actions.at(-1);
    const revision = store.view.revision + 1;
    receive("ui_update", fx.update({ revision, panels: { area_map: interiorArea() } }));
    result(request, revision);
    await tick();
    await w.get('[data-testid="map-drawer-tab--world"]').trigger("click");
    expect(sender.sent.actions.map(a => a.payload.scope)).toEqual(["area", "world"]);
    expect(w.find('[data-testid="world-map"]').exists()).toBe(false);
    await reply(worldNewLight());
    expect(w.get('[data-testid="world-map__discovery"]').text()).toBe("");
  });

  it("sends one map.view for the active scope on open and on each tab switch", async () => {
    const store = fakeStore();
    const { api } = withDrawer(store);
    expect(mapViews(store)).toEqual([]);
    store.view.hudOverlay = "map";
    await tick();
    expect(mapViews(store)).toEqual(["area"]);
    store.answer();
    api().mapTab.value = "world";
    await tick();
    expect(mapViews(store)).toEqual(["area", "world"]);
    expect(store.sent.every((entry) => entry.actionId === "map.view" && Object.keys(entry.payload).join() === "scope")).toBe(true);
  });

  it("waits for the lock instead of queueing, and sends the latest scope once", async () => {
    const store = fakeStore();
    const { api } = withDrawer(store);
    store.dispatchAction("explore.look", {});
    store.view.hudOverlay = "map";
    await tick();
    api().mapTab.value = "world";
    await tick();
    expect(mapViews(store)).toEqual([]);
    store.answer();
    await tick();
    expect(mapViews(store)).toEqual(["world"]);
  });

  it("refreshes the active scope once after a committed move, never on input", async () => {
    const store = fakeStore();
    const { api } = withDrawer(store);
    store.view.hudOverlay = "map";
    await tick();
    store.answer();
    await tick();
    api().mapTab.value = "world";
    await tick();
    store.answer();
    await tick();
    expect(mapViews(store)).toEqual(["area", "world"]);
    api().onMapDrawerMove({ exit_ref: "e1", destination: "grid:t:1:1", current_node: "grid:t:0:0" });
    await tick();
    // In flight: nothing more is sent on input.
    expect(mapViews(store)).toEqual(["area", "world"]);
    store.resultOnly("success", "moved");
    await tick();
    // The result arrived but its presentation has not committed yet.
    expect(mapViews(store)).toEqual(["area", "world"]);
    store.commit();
    await tick();
    expect(mapViews(store)).toEqual(["area", "world", "world"]);
    store.answer();
    await tick();
    expect(mapViews(store)).toEqual(["area", "world", "world"]);
  });

  it("does not refresh for a rejected move, an earlier move or a closed drawer", async () => {
    const store = fakeStore();
    const { api } = withDrawer(store);
    // A move committed before the drawer opened is never replayed.
    store.dispatchAction("explore.move", {});
    store.answer("success", "moved");
    store.view.hudOverlay = "map";
    await tick();
    store.answer();
    await tick();
    expect(mapViews(store)).toEqual(["area"]);
    api().onMapDrawerMove({ exit_ref: "e1", destination: "x", current_node: "y" });
    store.answer("rejected", "no_exit");
    await tick();
    expect(mapViews(store)).toEqual(["area"]);
    store.view.hudOverlay = null;
    await tick();
    store.dispatchAction("explore.move", {});
    store.answer("success", "moved");
    await tick();
    expect(mapViews(store)).toEqual(["area"]);
  });

  it("drops the pending request on close and on disconnect", async () => {
    const store = fakeStore();
    withDrawer(store);
    store.dispatchAction("explore.look", {});
    store.view.hudOverlay = "map";
    await tick();
    store.view.hudOverlay = null;
    await tick();
    store.answer();
    await tick();
    expect(mapViews(store)).toEqual([]);
    store.dispatchAction("explore.look", {});
    store.view.hudOverlay = "map";
    await tick();
    store.view.connected = false;
    await tick();
    store.answer();
    store.view.connected = true;
    await tick();
    expect(mapViews(store)).toEqual([]);
  });

  it("holds 前往 while a request is unsettled instead of having it refused", async () => {
    const store = fakeStore();
    const { api, moves } = withDrawer(store);
    store.view.hudOverlay = "map";
    await tick();
    expect(api().mapBusy.value).toBe(true);
    expect(api().onMapDrawerMove({ exit_ref: "e1", destination: "x", current_node: "y" })).toBeNull();
    expect(moves).toEqual([]);
    store.answer();
    await tick();
    expect(api().mapBusy.value).toBe(false);
    expect(api().onMapDrawerMove({ exit_ref: "e1", destination: "x", current_node: "y" })).toMatch(/^session:/);
    expect(moves).toHaveLength(1);
  });
});

describe("floating map chrome avoids selected details", () => {
  it("floats the commission list, the control pill and the scale bar over a full-bleed map", async () => {
    const { w } = mountDrawer();
    await tick();
    expect(w.find('[data-testid="map-drawer-quests-toggle"]').exists()).toBe(true);
    const pill = w.find('[data-testid="map-drawer-pill"]');
    expect(pill.findAll("button").map((b) => b.attributes("aria-label") ?? b.text())).toEqual([
      "縮小",
      "放大",
      "回到目前位置",
      "全圖",
      "圖例",
    ]);
    expect(w.find('[data-testid="map-drawer-stop"]').text()).not.toBe("");
    expect(w.find('[data-testid="area-map__scale-bar"]').exists()).toBe(true);
    expect(pill.attributes("style") ?? "").not.toContain("right");
  });

  it("opens the ~360 px detail only on selection and moves the pill left of it", async () => {
    const { w } = mountDrawer();
    await tick();
    expect(w.find('[data-testid="area-map-detail"]').exists()).toBe(false);
    await selectAreaNode(w, TOWN_IDS.east);
    await tick();
    expect(w.find('[data-testid="area-map-detail"]').exists()).toBe(true);
    expect(w.find(".area-map__detail").attributes("style")).toContain("width: 360px");
    expect(w.find('[data-testid="map-drawer-pill"]').attributes("style")).toContain("right: calc(360px");
  });

  it("mirrors every commission of the tab as text, tracked first", async () => {
    const { w } = mountDrawer({ tab: "world" });
    await tick();
    await w.find('[data-testid="map-drawer-quests-toggle"]').trigger("click");
    await tick();
    const rows = w.findAll('[data-testid="map-drawer-quest"]');
    expect(rows.map((r) => r.attributes("data-quest"))).toEqual([QUEST_IDS.exact, QUEST_IDS.approximate, QUEST_IDS.nearApproximate]);
    expect(rows[0].text()).toContain("追蹤中");
    expect(rows[1].text()).toContain("大致方位");
  });

  it("states an area commission in fog or elsewhere as text only", async () => {
    const { w } = mountDrawer({ area: validateAreaMapPanel(dungeonArea()) });
    await tick();
    await w.find('[data-testid="map-drawer-quests-toggle"]').trigger("click");
    await tick();
    expect(w.find('[data-testid="map-drawer-quest"]').text()).toContain("尚未探明");
    expect(w.findAll('[data-testid="map-edge-pointer"]')).toHaveLength(0);
  });

  it("points at an off-screen commission and shows it when activated", async () => {
    const { w, memory } = mountDrawer({ tab: "world" });
    await tick();
    // 調查帝都古文書 lies about 680 km east, outside the 國 view.
    const pointers = w.findAll('[data-testid="map-edge-pointer"]');
    const far = pointers.find((p) => p.attributes("data-quest") === QUEST_IDS.approximate);
    expect(far).toBeTruthy();
    expect(far.attributes("data-side")).toBe("right");
    expect(far.attributes("aria-label")).toMatch(/^委託 調查帝都古文書，大致方位 · 東方/);
    await far.trigger("click");
    await tick();
    expect(memory.world.selected).toBe(`quest:${QUEST_IDS.approximate}`);
    expect(w.find('[data-testid="world-map-detail__title"]').text()).toBe("調查帝都古文書");
  });

  async function activateOutsideCommission(w) {
    await tick();
    await w.find('[data-testid="map-drawer-quests-toggle"]').trigger("click");
    await tick();
    const far = w.findAll('[data-testid="map-drawer-quest"]').find((r) => r.attributes("data-quest") === "q_story_far");
    expect(far.text()).toContain("區域外");
    await far.trigger("click");
    await tick();
  }

  function worldWithOutsideCommission() {
    const world = worldBase();
    const marker = world.quest_markers.find((item) => item.id === QUEST_IDS.approximate);
    world.quest_markers = [{ ...marker, id: "q_story_far", title: "霧谷的失蹤羊群" }];
    return validateWorldMapPanel(world);
  }

  it.each(["unloaded", "stale"])("reveals an area commission after an initially %s world response", async (initial) => {
    const props = reactive({ world: initial === "unloaded" ? null : validateWorldMapPanel(worldBase()) });
    const { w, memory, state } = mountDrawer(props);
    memory.world.selected = `quest:${QUEST_IDS.exact}`;
    await activateOutsideCommission(w);
    expect(state.tab).toBe("world");
    expect(memory.world.selected).toBeNull();
    expect(w.find('[data-testid="world-map-detail"]').exists()).toBe(false);
    props.world = worldWithOutsideCommission();
    await tick();
    expect(memory.world.selected).toBe("quest:q_story_far");
    expect(w.find('[data-testid="world-map-detail__title"]').text()).toBe("霧谷的失蹤羊群");
    expect(w.find('[data-testid="world-map__approx"][data-quest="q_story_far"]').exists()).toBe(true);
    const map = w.findComponent(MapDrawer).vm.viewRef;
    const point = project(map.view, map.frame, props.world.quest_markers[0]);
    const rect = usableRect(map.frame, { drawerOpen: true });
    expect(point.x).toBeGreaterThanOrEqual(rect.left);
    expect(point.x).toBeLessThanOrEqual(rect.right);
    expect(point.y).toBeGreaterThanOrEqual(rect.top);
    expect(point.y).toBeLessThanOrEqual(rect.bottom);
  });

  it.each(["epoch", "missing", "unavailable"])("retires unresolved commission intent after %s without inventing a position", async (retirement) => {
    const props = reactive({ world: null, epoch: "epoch-a" });
    const { w, memory } = mountDrawer(props);
    await activateOutsideCommission(w);
    if (retirement === "epoch") props.epoch = "epoch-b";
    else props.world = retirement === "missing"
      ? validateWorldMapPanel(worldBase())
      : { available: false, reason: { code: "unavailable", message: "世界地圖目前無法顯示" } };
    await tick();
    expect(memory.world.selected).toBeNull();
    expect(w.find('[data-testid="world-map-detail"]').exists()).toBe(false);
    props.world = worldWithOutsideCommission();
    await tick();
    expect(memory.world.selected).toBeNull();
    expect(w.find('[data-testid="world-map-detail"]').exists()).toBe(false);
  });
});

describe("map keyboard and pointer interaction remains modal and accessible", () => {
  it("unwinds Escape: legend, then the selection, then the map", async () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    let closed = 0;
    const memory = blankMemory();
    const w = mount(OverlayHost, {
      props: { overlay: "map", ownHeader: true, onClose: () => (closed += 1) },
      slots: {
        default: (slot) =>
          h(MapDrawer, { area: validateAreaMapPanel(townArea()), world: null, tab: "area", memory, onClose: slot.close }),
      },
      attachTo: host,
    });
    wrappers.push(w);
    await tick();
    await selectAreaNode(w, TOWN_IDS.east);
    await tick();
    await w.find('[data-testid="map-drawer-legend-toggle"]').trigger("click");
    await tick();
    expect(w.find('[data-testid="map-drawer-legend"]').isVisible()).toBe(true);
    const toggle = w.find('[data-testid="map-drawer-legend-toggle"]');
    toggle.element.focus();
    await key(toggle, "Escape");
    await tick();
    expect(w.find('[data-testid="map-drawer-legend"]').isVisible()).toBe(false);
    expect(memory.area.selected).toBe(TOWN_IDS.east);
    expect(closed).toBe(0);
    await key(toggle, "Escape");
    await tick();
    expect(memory.area.selected).toBeNull();
    expect(w.find('[data-testid="area-map-detail"]').exists()).toBe(false);
    expect(closed).toBe(0);
    await key(toggle, "Escape");
    expect(closed).toBe(1);
  });

  it("drives the view from the keyboard and keeps the keys away from the game", async () => {
    const { w, state } = mountDrawer({ tab: "world" });
    await tick();
    const stage = w.find('[data-testid="map-drawer-pill"]');
    const span = () => Number(w.find('[data-testid="world-map__svg"]').attributes("data-span"));
    let reachedDocument = 0;
    const spy = () => (reachedDocument += 1);
    document.addEventListener("keydown", spy);
    try {
      expect(span()).toBe(800);
      await key(stage, "+");
      await tick();
      expect(span()).toBe(200);
      await key(stage, "-");
      await tick();
      expect(span()).toBe(800);
      await key(stage, "0");
      await tick();
      expect(span()).toBeGreaterThan(800);
      const before = w.find('[data-testid="world-map__svg"] [data-layer="current"]').attributes("transform");
      await key(stage, "ArrowRight");
      await tick();
      expect(w.find('[data-testid="world-map__svg"] [data-layer="current"]').attributes("transform")).not.toBe(before);
      await key(stage, "c");
      await tick();
      await key(stage, "1");
      await tick();
      expect(state.tab).toBe("area");
      expect(document.activeElement).toBe(w.find('[data-testid="map-drawer-tab--area"]').element);
      // Modified keys pass through untouched.
      await key(w.find('[data-testid="map-drawer-tab--area"]'), "2", { ctrlKey: true });
      await tick();
      expect(state.tab).toBe("area");
    } finally {
      document.removeEventListener("keydown", spy);
    }
    // Without the OverlayHost section this mount lets keys bubble; inside
    // the product the host section stops every non-Tab key (asserted below).
    expect(reachedDocument).toBeGreaterThan(0);
  });

  it("stops every map key at the modal host so background commands never see it", async () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    const w = mount(OverlayHost, {
      props: { overlay: "map", ownHeader: true },
      slots: { default: () => h(MapDrawer, { area: validateAreaMapPanel(townArea()), world: null, tab: "area", memory: blankMemory() }) },
      attachTo: host,
    });
    wrappers.push(w);
    await tick();
    let reached = 0;
    const spy = () => (reached += 1);
    document.addEventListener("keydown", spy);
    try {
      for (const name of ["c", "C", "1", "2", "ArrowUp", "+", "0", "m", "p"]) {
        await key(w.find('[data-testid="map-drawer-recentre"]'), name);
      }
    } finally {
      document.removeEventListener("keydown", spy);
    }
    expect(reached).toBe(0);
  });

  it("forwards the selected adjacent exit's exact move with the drawn current node", async () => {
    const { w, emitted } = mountDrawer();
    await tick();
    await selectAreaNode(w, TOWN_IDS.east);
    await tick();
    await w.find('[data-testid="area-map-detail__go"]').trigger("click");
    expect(emitted.move).toEqual([
      { exit_ref: "e_square_e", destination: TOWN_IDS.east, current_node: TOWN_IDS.square, label: "銅匠街" },
    ]);
  });

  it("never offers 前往 for a remote node and holds it while busy", async () => {
    const { w, emitted } = mountDrawer({ busy: true });
    await tick();
    await selectAreaNode(w, TOWN_IDS.academy);
    await tick();
    expect(w.find('[data-testid="area-map-detail__go"]').exists()).toBe(false);
    await selectAreaNode(w, TOWN_IDS.east);
    await tick();
    const go = w.find('[data-testid="area-map-detail__go"]');
    expect(go.attributes("aria-disabled")).toBe("true");
    await go.trigger("click");
    expect(emitted.move).toEqual([]);
  });

  it("closes the commission list on Escape and returns focus to its toggle", async () => {
    const { w } = mountDrawer({ tab: "world" });
    await tick();
    const toggle = w.find('[data-testid="map-drawer-quests-toggle"]');
    await toggle.trigger("click");
    await tick();
    expect(toggle.attributes("aria-expanded")).toBe("true");
    const first = w.find('[data-testid="map-drawer-quest"]');
    expect(document.activeElement).toBe(first.element);
    await key(first, "ArrowDown");
    expect(document.activeElement).toBe(w.findAll('[data-testid="map-drawer-quest"]')[1].element);
    await key(first, "Escape");
    await tick();
    expect(toggle.attributes("aria-expanded")).toBe("false");
    expect(document.activeElement).toBe(toggle.element);
  });
});

describe("the old full-map lattice has no remaining consumer", () => {
  it("removes the overlay, its view math and composable with no alias", () => {
    for (const path of ["components/MapOverlay.vue", "lib/map_view.js", "composables/use-map-view.js"]) {
      expect(existsSync(resolve(APP_DIR, path)), path).toBe(false);
    }
  });

  it("leaves the shared lattice renderer with only its island parameters", () => {
    const props = Object.keys(MapLattice.props);
    for (const retired of ["fitView", "overlayChrome", "colPitch", "rowPitch", "edgeMarkers"]) {
      expect(props, retired).not.toContain(retired);
    }
  });

  it("renders the real area and world views inside the map surface", async () => {
    const { w } = mountDrawer();
    await tick();
    expect(w.find('[data-testid="area-map"]').exists()).toBe(true);
    expect(w.find('[data-testid="local-map__lattice"]').exists()).toBe(false);
  });
});

describe("area view memory resets on coordinate-frame changes", () => {
  it("keys area memory by map_id and frame key/unit", () => {
    expect(areaMemoryKey(townArea())).toBe("story_town|story_town|m");
    expect(areaMemoryKey({ available: false })).toBeNull();
  });

  async function walk(bodies) {
    const store = fakeStore();
    const { api } = withDrawer(store);
    store.view.hudOverlay = "map";
    await tick();
    const seen = [];
    for (const body of bodies) {
      api().mapMemory.area.view = Object.freeze({ signature: "stale", cx: 1, cy: 1, span: 1 });
      api().mapMemory.area.selected = "stale-node";
      store.view.maps = { ...store.view.maps, area_map: body };
      // The reset is synchronous: no frame renders the old view on the new map.
      seen.push({ key: api().mapMemory.area.key, view: api().mapMemory.area.view, selected: api().mapMemory.area.selected });
    }
    return seen;
  }

  it("clears view and selection from city to wilderness to interior", async () => {
    const seen = await walk([townArea(), wildernessArea(), interiorArea()]);
    expect(seen.map((entry) => entry.key)).toEqual([areaMemoryKey(townArea()), areaMemoryKey(wildernessArea()), areaMemoryKey(interiorArea())]);
    for (const entry of seen) {
      expect(entry.view).toBeUndefined();
      expect(entry.selected).toBeUndefined();
    }
  });

  it("clears view and selection between two settlements, even with one frame signature", async () => {
    const other = townArea({ map_id: "t_other_town" });
    const seen = await walk([townArea(), other]);
    expect(seen[1].key).toBe("t_other_town|story_town|m");
    expect(seen[1].view).toBeUndefined();
  });

  it("keeps the view while the same map republishes", async () => {
    const store = fakeStore();
    const { api } = withDrawer(store);
    store.view.maps = { area_map: townArea() };
    const kept = Object.freeze({ signature: "grid|story_town|m", cx: 2, cy: 3, span: 400 });
    api().mapMemory.area.view = kept;
    store.view.maps = { area_map: townArea({ current_node: TOWN_IDS.east }) };
    expect(api().mapMemory.area.view).toBe(kept);
  });

  it("opens each new frame on its current node and adjacency at the right unit", async () => {
    for (const [body, signature] of [
      [townArea(), "grid|story_town|m"],
      [wildernessArea(), null],
      [interiorArea(), null],
    ]) {
      const { memory } = mountDrawer({ area: validateAreaMapPanel(body) });
      await tick();
      const view = memory.area.view;
      expect(view.signature).toBe(signature ?? `${body.layer}|${body.frame.key}|${body.frame.unit}`);
      expect(view.span).toBeGreaterThan(0);
    }
  });
});

describe("the drawer current marker makes one truthful position claim", () => {
  it("draws one concentric, inert current ring on the area map", async () => {
    const { w } = mountDrawer();
    await tick();
    const current = w.findAll('[data-testid="area-map__node"]').filter((n) => n.attributes("aria-current") === "location");
    expect(current).toHaveLength(1);
    const group = current[0].find("g");
    const rings = group.findAll(".map-glyph__here-glow, .map-glyph__here-ring, .map-glyph__here-dot");
    expect(rings).toHaveLength(3);
    for (const ring of rings) {
      expect(ring.attributes("cx") ?? "0").toBe("0");
      expect(ring.attributes("cy") ?? "0").toBe("0");
      expect(ring.attributes("role")).toBeUndefined();
      expect(ring.attributes("aria-label")).toBeUndefined();
    }
    // The connectors leave the current node's centre, outside its ring.
    const roads = w.findAll(".area-map__road-core");
    expect(roads.length).toBeGreaterThan(0);
    expect(w.findAll(".area-map__nodes .map-glyph__here-ring")).toHaveLength(1);
  });

  it("draws the island's current node with the same here-seal at the island scale", () => {
    const w = mount(MapLattice, { props: { localMap: localMapModelFor(LOCAL_MAP_SAMPLE) } });
    wrappers.push(w);
    const glows = w.findAll(".map-glyph__here-glow");
    const rings = w.findAll(".map-glyph__here-ring");
    const dots = w.findAll(".map-glyph__here-dot");
    expect([glows.length, rings.length, dots.length]).toEqual([1, 1, 1]);
    expect([glows[0], rings[0], dots[0]].map((c) => c.attributes("r"))).toEqual(["14", "10", "6"]);
    // One glyph group, scaled as a whole by the island glyph scale; the ring
    // keeps the island's current-marker hook and no second current shape.
    const group = rings[0].element.parentElement;
    expect(group.getAttribute("transform")).toBe(`scale(${ISLAND_GLYPH_SCALE})`);
    expect(group.contains(glows[0].element) && group.contains(dots[0].element)).toBe(true);
    expect(rings[0].classes()).toContain("local-map__marker--current");
    expect(w.findAll(".local-map__marker--current")).toHaveLength(1);
  });

  it("draws one current marker on the world map with no identity of its own", async () => {
    const { w } = mountDrawer({ tab: "world" });
    await tick();
    const layer = w.findAll('[data-layer="current"]');
    expect(layer).toHaveLength(1);
    expect(layer[0].attributes("data-pick")).toBeUndefined();
    expect(layer[0].findAll("[data-pick]")).toHaveLength(0);
  });
});

// ── shared glyph sources ────────────────────────────────────────────────

const COMPONENTS = resolve(APP_DIR, "components");
const source = (name) => readFileSync(resolve(COMPONENTS, name), "utf-8");
const ownStyle = (sfc) => [...sfc.matchAll(/<style scoped>([\s\S]*?)<\/style>/g)].map((m) => m[1]).join("\n");

// One glyph group's drawn shapes as a scale-free signature: tag, glyph
// classes, radius and path data.
function glyphSignature(group) {
  return [...group.querySelectorAll("circle, path")].map((el) => ({
    tag: el.tagName.toLowerCase(),
    cls: [...el.classList].filter((c) => c.startsWith("map-glyph__") || c === "is-seen").sort().join(" "),
    r: el.getAttribute("r"),
    d: el.getAttribute("d"),
  }));
}

// Glyph groups keyed by the state they draw (halo excluded from the key).
function glyphsByKind(root) {
  const out = new Map();
  for (const group of root.querySelectorAll("g.map-glyph")) {
    const shapes = glyphSignature(group);
    const primary = shapes.find((sh) => sh.cls.includes("here-ring") || sh.cls.includes("gate") || sh.cls.includes("dot"));
    const kind = [primary.cls, shapes.some((sh) => sh.cls.includes("halo")) ? "+travel" : ""].join("");
    if (!out.has(kind)) out.set(kind, { shapes, transform: group.getAttribute("transform") });
  }
  return out;
}

function wildernessWithCornerQuest() {
  const area = wildernessArea();
  area.quest_markers = [
    ...area.quest_markers,
    { id: "q_story_here", title: "就地調查", tracked: false, destination: { kind: "node", node_id: area.current_node } },
  ];
  return area;
}

describe("every map surface draws a shared map concept from its one glyph source", () => {
  it("scales a node glyph as one group around base-unit shapes", () => {
    const host = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    document.body.appendChild(host);
    const w = mount(MapNodeGlyph, { props: { state: "current", travel: true, size: 0.5 }, attachTo: host });
    wrappers.push(w);
    const root = w.element;
    expect(root.tagName.toLowerCase()).toBe("g");
    expect(root.getAttribute("transform")).toBe("scale(0.5)");
    expect([...root.querySelectorAll("circle")].map((c) => c.getAttribute("r"))).toEqual(["15", "14", "10", "6"]);
    const gate = mount(MapNodeGlyph, { props: { state: "visited", gate: true, size: 0.5 }, attachTo: host });
    wrappers.push(gate);
    expect(gate.get(".map-glyph__gate").attributes("d")).toBe("M-8 8 V-2 A8 8 0 0 1 8 -2 V8 Z");
    expect(gate.element.getAttribute("transform")).toBe("scale(0.5)");
    // Strokes and dashes scale with the group: no shape opts out.
    expect(source("MapNodeGlyph.vue")).not.toMatch(/vector-effect/);
    expect(source("MapCommissionGlyph.vue")).not.toMatch(/vector-effect/);
  });

  it("draws the island's and the area map's node glyphs identically up to each surface's scale", async () => {
    const island = new Map();
    for (const sample of [
      LOCAL_MAP_SAMPLE,
      LOCAL_MAP_ALTORIA_PLAZA_SAMPLE,
      LOCAL_MAP_ALTORIA_SOUTH_GATE_SAMPLE,
      LOCAL_MAP_WILDERNESS_SAMPLE,
      LOCAL_MAP_WILDERNESS_METRIC_SAMPLE,
      LOCAL_MAP_WILDERNESS_RETURN_SAMPLE,
    ]) {
      const w = mount(MapLattice, { props: { localMap: localMapModelFor(sample) } });
      wrappers.push(w);
      for (const [kind, glyph] of glyphsByKind(w.element)) if (!island.has(kind)) island.set(kind, glyph);
      // The island applies no paint of its own and draws no extra shape.
      expect(w.findAll(".local-map__landmark")).toHaveLength(0);
      for (const gateGlyph of w.findAll(".local-map__gate-glyph")) expect(gateGlyph.attributes("d")).toBe(gatePath());
    }
    const { w } = mountDrawer();
    await tick();
    const area = glyphsByKind(w.find(".area-map__nodes").element);
    for (const kind of ["map-glyph__here-ring", "map-glyph__dot", "map-glyph__dot+travel", "is-seen map-glyph__gate+travel"]) {
      expect(island.has(kind), `island draws ${kind}`).toBe(true);
    }
    let compared = 0;
    for (const [kind, glyph] of island) {
      expect(glyph.transform).toBe(`scale(${ISLAND_GLYPH_SCALE})`);
      if (!area.has(kind)) continue;
      expect(area.get(kind).transform).toBeNull();
      expect(glyph.shapes).toEqual(area.get(kind).shapes);
      compared += 1;
    }
    expect(compared).toBeGreaterThanOrEqual(3);
  });

  it("marks wilderness cells with the shared here-seal, gate arch and commission diamond", () => {
    const area = validateAreaMapPanel(wildernessWithCornerQuest());
    const host = document.createElement("div");
    document.body.appendChild(host);
    // The widest zoom the map allows: the 周邊 stop's span at the zoom-out
    // limit, on the 960 × 600 fallback frame.
    const span = spanLimits(wildernessStops({ width: 960, height: 600 })).max;
    const here = area.nodes.find((n) => n.id === area.current_node);
    const view = { signature: viewSignature(area), cx: here.x / area.cell_km, cy: here.y / area.cell_km, span };
    const w = mount(AreaMapView, { props: { area, view }, attachTo: host });
    wrappers.push(w);
    const cellNode = (id) => w.findAll('[data-testid="area-map__node"]').find((n) => n.attributes("data-node-id") === id);
    const current = cellNode(area.current_node);
    const seal = current.get("g.map-glyph");
    expect(seal.attributes("transform")).toBe(`scale(${AREA_CELL_GLYPH_SCALE})`);
    expect(seal.findAll(".map-glyph__here-glow, .map-glyph__here-ring, .map-glyph__here-dot").map((c) => c.attributes("r"))).toEqual(["14", "10", "6"]);
    // The commission beside the seal: the shared diamond at the cell scale,
    // moved to the cell's corner.
    const corner = current.get("g.map-commission");
    expect(corner.attributes("transform")).toBe(`scale(${AREA_CELL_GLYPH_SCALE})`);
    expect(corner.element.parentElement.getAttribute("transform")).toBe("translate(11 -11)");
    expect(corner.get(".area-map__quest").attributes("d")).toBe("M0 -7.5 L5.5 0 L0 7.5 L-5.5 0 Z");
    const gate = cellNode(WILD_GATE_ID).get(".map-glyph__gate");
    expect(gate.attributes("d")).toBe(gatePath());
    expect(gate.classes()).toContain("is-seen");
    expect(gate.element.parentElement.getAttribute("transform")).toBe(`scale(${AREA_CELL_GLYPH_SCALE})`);
    const questCell = cellNode(area.quest_markers[0].destination.node_id);
    expect(questCell.get("g.map-commission").attributes("transform")).toBe(`scale(${AREA_CELL_GLYPH_SCALE})`);
    // No private cell seal, arch or pin remains.
    expect(w.findAll('[class*="area-map__here-"], .area-map__gate')).toHaveLength(0);
    for (const path of w.findAll("path")) expect(path.attributes("d")).not.toBe("M0 -9 L5.5 -2 L0 4 L-5.5 -2 Z");
    // The scaled here-glow (14 × 0.875 = 12.25) fits half the smallest cell
    // side even at the widest zoom.
    const sides = w.findAll(".area-map__cell").flatMap((c) => [Number(c.attributes("width")), Number(c.attributes("height"))]);
    expect(Math.min(...sides) / 2).toBeGreaterThanOrEqual(14 * AREA_CELL_GLYPH_SCALE);
  });

  it("paints the legend's road and commission samples with the area map's own sources", async () => {
    const { w } = mountDrawer();
    await tick();
    const legend = w.get('[data-testid="map-drawer-legend"]');
    for (const variant of ["is-walked", "is-frontier"]) {
      const road = legend.get(`g.area-map__road.${variant}`);
      expect(road.find(".area-map__road-casing").exists()).toBe(true);
      expect(road.find(".area-map__road-core").exists()).toBe(true);
    }
    const commission = legend.get("g.map-commission .area-map__quest");
    const onMap = w.find(".area-map__nodes .area-map__quest");
    expect(commission.attributes("d")).toBe("M0 -7.5 L5.5 0 L0 7.5 L-5.5 0 Z");
    if (onMap.exists()) expect(onMap.attributes("d")).toBe(commission.attributes("d"));
    // The drawer holds no road or commission paint values of its own; it
    // includes the area map's ink instead.
    const drawer = source("MapDrawer.vue");
    expect(ownStyle(drawer)).not.toMatch(/area-map__road|area-map__quest|lg-road|lg-quest/);
    expect(drawer).toContain('<style scoped src="./area-map-ink.css"></style>');
    expect(source("AreaMapView.vue")).toContain('<style scoped src="./area-map-ink.css"></style>');
  });

  it("instantiates one hatch pattern definition on the world map and in its legend", async () => {
    const { w } = mountDrawer({ tab: "world" });
    await tick();
    await w.find('[data-testid="map-drawer-legend-toggle"]').trigger("click");
    const hatches = w.findAll("pattern").filter((p) => p.find(".world-map__hatch-line").exists());
    expect(hatches).toHaveLength(2);
    const ids = hatches.map((p) => p.attributes("id"));
    expect(new Set(ids).size).toBe(2);
    for (const p of hatches) {
      expect(p.attributes("patternTransform")).toBe("rotate(45)");
      expect([p.attributes("width"), p.attributes("height"), p.attributes("patternUnits")]).toEqual(["8", "8", "userSpaceOnUse"]);
    }
    const legend = w.get('[data-testid="map-drawer-legend"]');
    const legendHatch = hatches.find((p) => legend.element.contains(p.element));
    expect(legend.find(`[fill="url(#${legendHatch.attributes("id")})"]`).exists()).toBe(true);
    const mapHatch = hatches.find((p) => p !== legendHatch);
    expect(w.find(`[data-testid="world-map__hatch"][fill="url(#${mapHatch.attributes("id")})"]`).exists()).toBe(true);
  });

  it("scales the world map's point glyphs as a whole with the UI scale", async () => {
    document.documentElement.style.setProperty("--ui-scale", "1.25");
    try {
      const host = document.createElement("div");
      document.body.appendChild(host);
      const w = mount(WorldMapView, { props: { world: validateWorldMapPanel(worldBase()) }, attachTo: host });
      wrappers.push(w);
      await tick();
      const groups = w.findAll('[data-testid="world-map__landmark"], [data-testid="world-map__place"], [data-testid="world-map__quest"], [data-layer="current"]');
      expect(groups.length).toBeGreaterThan(3);
      for (const g of groups) {
        expect(g.attributes("transform")).toMatch(/scale\(1\.25\)$/);
        expect(g.find("g.world-glyph").exists()).toBe(true);
      }
      // Glyph strokes scale with that group: no shape opts out.
      expect(source("WorldMapGlyph.vue")).not.toMatch(/vector-effect/);
    } finally {
      document.documentElement.style.removeProperty("--ui-scale");
    }
  });

  it("keeps each shared concept's geometry and paint in its one source", () => {
    const files = readdirSync(COMPONENTS).filter((f) => f.endsWith(".vue") || f.endsWith(".css"));
    const sources = Object.fromEntries(files.map((f) => [f, source(f)]));
    const holders = (pattern) => files.filter((f) => pattern.test(sources[f])).sort();
    // The unlit hatch pattern is declared only by WorldHatchPattern (other
    // <pattern>s, the area dot field and the world swell, are not hatching).
    expect(holders(/patternTransform="rotate\(45\)"/)).toEqual(["WorldHatchPattern.vue"]);
    expect(holders(/world-map__hatch-line/)).toEqual(["WorldHatchPattern.vue"]);
    // The gate arch comes only from gatePath(); no component spells an arch.
    expect(holders(/A8 8 0 0 1|A7 7 0 0 1/)).toEqual([]);
    expect(readFileSync(resolve(APP_DIR, "lib/map_marker_geometry.js"), "utf-8")).toMatch(/export function gatePath\(\)/);
    // The commission diamond lives only in MapCommissionGlyph.
    expect(holders(/M0 -7\.5 L5\.5 0/)).toEqual(["MapCommissionGlyph.vue"]);
    // The road ink lives only in area-map-ink.css.
    expect(holders(/\.area-map__road-casing\s*\{/)).toEqual(["area-map-ink.css"]);
    // No approximation or private redraw remains anywhere.
    expect(holders(/\.lg-road|\.lg-quest|lg-road__|\blg-quest\b|\.lg--|class="lg lg|area-map__here-|area-map__gate\b/)).toEqual([]);
  });
});

describe("map legend samples are drawn by the map they explain", () => {
  it("draws the area legend's samples with the area map's own glyphs", async () => {
    const { w } = mountDrawer();
    await tick();
    const legend = w.get('[data-testid="map-drawer-legend"]');
    const items = legend.findAll(".map-drawer__legend-list li");
    expect(items.map((li) => li.text())).toEqual([
      "目前位置", "到過的地點", "看過，尚未到訪", "相鄰，可前往", "城門與出入口", "走過的路", "看見但未走過的路", "委託目的地",
    ]);
    for (const li of items) {
      expect(li.findAll("svg.lg-svg")).toHaveLength(1);
      expect(li.get("svg.lg-svg").attributes("viewBox")).toBe("-16 -16 32 32");
    }
    expect(legend.findAll(".lg, [class*='lg-road'], .lg-quest")).toHaveLength(0);
    // The gate sample is the map's very arch.
    const mapGate = w.get(".area-map__nodes .map-glyph__gate");
    expect(legend.get(".map-glyph__gate").attributes("d")).toBe(mapGate.attributes("d"));
    expect(items[2].find(".map-glyph__dot.is-seen").exists()).toBe(true);
    expect(items[3].find(".map-glyph__halo").exists()).toBe(true);
    // Samples are drawn at the map's base glyph size (no group scale).
    for (const g of legend.findAll("g.map-glyph")) expect(g.attributes("transform")).toBeUndefined();
  });

  it("draws the world legend's samples with the world map's glyphs and ink", async () => {
    const { w } = mountDrawer({ tab: "world" });
    await tick();
    const legend = w.get('[data-testid="map-drawer-legend"]');
    const items = legend.findAll(".map-drawer__legend-list li");
    expect(items.map((li) => li.text())).toEqual([
      "目前位置", "已探明的分區", "未探明的分區", "國界", "走過的足跡", "分區地標", "城鎮與地點", "委託目的地", "委託大致方位",
    ]);
    for (const li of items) expect(li.findAll("svg.lg-svg")).toHaveLength(1);
    expect(legend.findAll(".lg, [class*='lg--']")).toHaveLength(0);
    for (const cls of [
      "here-ring", "wash", "land", "district.is-lit", "district.is-unlit", "nation-casing", "nation-border",
      "trail-casing", "trail-line", "spire", "place-glyph", "quest-pin", "approx-ring",
    ]) {
      expect(legend.find(`.world-map__${cls}`).exists(), cls).toBe(true);
    }
    expect(legend.find("pattern .world-map__hatch-line").exists()).toBe(true);
    const svg = w.get(".world-map__svg");
    for (const cls of ["spire", "quest-pin"]) {
      const onMap = svg.findAll(`.world-map__${cls}`).find((el) => !legend.element.contains(el.element));
      expect(onMap, cls).toBeDefined();
      expect(legend.get(`.world-map__${cls}`).attributes("d")).toBe(onMap.attributes("d"));
    }
    // The approximate ring fits the 32-unit sample with the map's paint.
    expect(legend.get(".world-map__approx-ring").attributes("r")).toBe("14");
    expect(legend.get(".world-map__approx-fill").attributes("r")).toBe("14");
  });

  it("sizes every sample box at 32 units times the UI scale", () => {
    const style = ownStyle(source("MapDrawer.vue"));
    const rule = /\.lg-svg\s*\{([^}]*)\}/.exec(style)[1];
    expect(rule).toMatch(/width:\s*calc\(32px \* var\(--ui-scale\)\)/);
    expect(rule).toMatch(/height:\s*calc\(32px \* var\(--ui-scale\)\)/);
  });
});
