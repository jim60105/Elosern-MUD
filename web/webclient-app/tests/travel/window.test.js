// The shared wilderness window decoder and the travel stage's live window
// (wilderness-travel-window-ui). Synthetic schema-3 bodies are built here and
// validated by the real wire validator; both map consumers decode them
// through lib/wilderness-grid.js. Nothing here names shipped content.

import { afterEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { mount } from "@vue/test-utils";
import MapPanels from "../../../static/webclient/js/elosern/protocol/panels/map_panels.js";
import TravelMap from "../../components/travel/TravelMap.vue";
import { decodeDistrictOverview, decodeWildernessGrid, wildernessCellAt } from "../../lib/wilderness-grid.js";
import { decodeTravelGrid, travelCellAt } from "../../lib/travel-grid.js";
import { LIGHT_PHASE_NAMES, decodeWindow } from "../../lib/area_map_view.js";
import { paintSignature } from "../../lib/travel-paint.js";
import { travelPlace } from "../../components/travel/travel-model.js";
import { useElosernStore } from "../../stores/elosern.js";
import { WILD_SUBJECT, fx, liveTravel, panelsAt, tick, walkArea, walkPanels, wildernessArea } from "./support.js";

vi.setConfig({ testTimeout: 60000 });

const { validateAreaMapPanel } = MapPanels;
const WINDOW = 41;
const CX = 60;
const CY = 80;
const wild = (x, y) => `wild:elosern:${x}:${y}`;
const clone = (value) => JSON.parse(JSON.stringify(value));

let wrappers = [];
afterEach(() => {
  for (const w of wrappers) w.unmount();
  wrappers = [];
  document.body.innerHTML = "";
}, 60000);

// One synthetic display annotation; `district` null leaves it undisclosed.
function display(terrain, { district = "t_east", ford = false } = {}) {
  return {
    terrain_label: `合成${terrain}`,
    district_key: district,
    district_name: district === null ? null : `合成${district}區`,
    settlement: terrain === "settlement",
    ford_label: ford ? "合成渡口" : null,
  };
}

// One row of the window: `known` maps a column to its revealed run facts.
function row(known) {
  const runs = [];
  for (let col = 0; col < WINDOW; col += 1) {
    const facts = known.get(col);
    const run = facts
      ? { length: 1, kind: "terrain", passable: true, band: 4, tier: 1, road: false, ford: false, ...facts, display: display(facts.terrain, facts.d ?? {}) }
      : { length: 1, kind: "unknown" };
    delete run.d;
    const last = runs.at(-1);
    if (last && JSON.stringify({ ...last, length: 0 }) === JSON.stringify({ ...run, length: 0 })) last.length += 1;
    else runs.push(run);
  }
  return runs;
}

// A window centred on (CX, CY): open ground at the party, woodland to its
// north, a ford to its east (in an undisclosed district), hills to its
// south; a lit landmark stands on the woodland cell and a gateway north-east.
// Two hostiles stand in live sight, one without a stated threat.
function body({ phase = "dusk", radius = 3 } = {}) {
  const minX = CX - 20;
  const minY = CY - 20;
  const rows = [];
  for (let r = 0; r < WINDOW; r += 1) {
    const y = minY + r;
    const known = new Map();
    if (y === CY) {
      known.set(20, { terrain: "open_ground" });
      known.set(21, { terrain: "water", passable: false, ford: true, d: { district: null, ford: true } });
    }
    if (y === CY + 1) {
      known.set(20, { terrain: "woodland" });
      known.set(21, { terrain: "settlement", passable: false });
    }
    if (y === CY - 1) known.set(20, { terrain: "hills", band: 6 });
    rows.push(row(known));
  }
  const node = (x, y, fields) => ({
    id: wild(x, y), label: "合成荒原", x: x + 0.5, y: y + 0.5,
    visibility: "seen", visited: false, gateway: null, action: null, landmark: null, ...fields,
  });
  const gate = "grid:t_town:1:1";
  return {
    schema_version: 4,
    available: true,
    layer: "wilderness",
    map_id: "elosern",
    frame: { key: "elosern", unit: "km" },
    current_node: wild(CX, CY),
    title: "合成荒原",
    nodes: [
      node(CX, CY - 1, { action: { kind: "move", exit_ref: "e_s", destination: wild(CX, CY - 1) } }),
      node(CX, CY, { visibility: "current", visited: true }),
      node(CX, CY + 1, { visibility: "visited", visited: true, landmark: { name: "合成石標" } }),
      { id: gate, label: "合成城門", x: CX + 1.5, y: CY + 1.5, visibility: "seen", visited: false,
        gateway: { leads_to: "合成城" }, action: { kind: "move", exit_ref: "e_gate", destination: gate }, landmark: null },
    ],
    edges: [
      { source: wild(CX, CY), destination: wild(CX, CY - 1) },
      { source: wild(CX, CY), destination: gate },
    ],
    quest_markers: [],
    district_name: "合成t_east區",
    district: {
      key: "t_east",
      name_zh: "合成東區",
      cell_km: 5,
      window: { min_x: 10, min_y: 14, width: 5, height: 5 },
      rows: [
        [{ length: 5, kind: "unknown" }],
        [{ length: 5, kind: "unknown" }],
        [
          { length: 1, kind: "unknown" },
          { length: 1, kind: "terrain", terrain: "hills", band: 5, passable: true },
          { length: 3, kind: "unknown" },
        ],
        [{ length: 5, kind: "unknown" }],
        [{ length: 5, kind: "unknown" }],
      ],
    },
    cell_km: 1,
    window: { min_x: minX, min_y: minY, width: WINDOW, height: WINDOW },
    rows,
    light_phase: phase,
    ground_radius: radius,
    entities: [
      { id: "0123456789abcdef", cell: { x: CX, y: CY - 1 }, kind: "hostile", hostile: true, label: "合成狼", count: 1, threat: "合成中階" },
      { id: "fedcba9876543210", cell: { x: CX, y: CY + 1 }, kind: "hostile", hostile: true, label: "合成豬", count: 1, threat: null },
    ],
    sightings: [{ bearing: "北", distance_km: 15, silhouette_zh: "合成塔影", name: null }],
  };
}

describe("one decoder for both map consumers", () => {
  it("lays the runs out row-major from the southern edge with exact totals", () => {
    const area = validateAreaMapPanel(body());
    const window = decodeWildernessGrid(area);
    expect([window.origin, window.width, window.height]).toEqual([{ x: CX - 20, y: CY - 20 }, 41, 41]);
    expect(window.cells).toHaveLength(41 * 41);
    // South of the party is the row below it, north the row above.
    expect(wildernessCellAt(window, CX, CY - 1).terrain).toBe("hills");
    expect(wildernessCellAt(window, CX, CY + 1).terrain).toBe("woodland");
    expect(wildernessCellAt(window, CX + 5, CY + 5)).toBeNull();
    expect(wildernessCellAt(window, CX + 30, CY)).toBeUndefined();
    // Both consumers share the decoded cells and their facts.
    const grid = decodeTravelGrid(area);
    const drawer = new Map(decodeWindow(area).map((cell) => [cell.key, cell]));
    const known = grid.cells.filter((cell) => cell.known);
    expect(known.map((c) => `${c.x}:${c.y}`).sort()).toEqual([...drawer.keys()].sort());
    for (const cell of known) {
      const d = drawer.get(`${cell.x}:${cell.y}`);
      expect([cell.terrain, cell.band, cell.tier, cell.road, cell.ford, cell.display]).toEqual([d.terrain, d.band, d.tier, d.road, d.ford, d.display]);
    }
    expect(travelCellAt(grid, CX, CY - 1).band).toBe(6);
    expect(drawer.get(`${CX}:${CY}`).state).toBe("current");
    expect(drawer.get(`${CX}:${CY + 1}`).state).toBe("sighted");
  });

  it("decodes the coarse district overview and carries it on the travel grid", () => {
    const area = validateAreaMapPanel(body());
    const overview = decodeDistrictOverview(area);
    expect([overview.key, overview.cellKm, overview.origin, overview.width, overview.height]).toEqual([
      "t_east",
      5,
      { x: 10, y: 14 },
      5,
      5,
    ]);
    expect(overview.rows).toHaveLength(5);
    expect(overview.cells.filter(Boolean)).toHaveLength(1);
    expect(overview.cells.find(Boolean)).toMatchObject({
      x: 11,
      y: 16,
      terrain: "hills",
      band: 5,
      passable: true,
    });
    expect(decodeTravelGrid(area).district).toBe(overview);
    // A null record is the exact unlit/no-district form; the fine window
    // still decodes.
    const plain = clone(body());
    plain.district = null;
    expect(decodeDistrictOverview(plain)).toBeNull();
    expect(decodeWildernessGrid(plain)).not.toBeNull();
  });

  it("keeps sparse nodes verbatim and invents nothing on unknown ground", () => {
    const area = validateAreaMapPanel(body());
    const grid = decodeTravelGrid(area);
    const gate = travelCellAt(grid, CX + 1, CY + 1).node;
    expect(gate).toBe(area.nodes.find((n) => n.id === "grid:t_town:1:1"));
    expect(travelCellAt(grid, CX, CY - 1).node.action.exit_ref).toBe("e_s");
    expect(travelCellAt(grid, CX, CY + 1).node.landmark).toEqual({ name: "合成石標" });
    const unknown = travelCellAt(grid, CX - 4, CY);
    expect(unknown).toMatchObject({ known: false, terrain: null, band: null, tier: null, road: false, ford: false, node: null, display: null });
    // A ford in an undisclosed district carries no district at all.
    expect(travelCellAt(grid, CX + 1, CY).display).toMatchObject({ district_key: null, district_name: null, ford_label: "合成渡口" });
  });

  it.each([
    ["a short row", (a) => (a.rows[0] = [{ length: 40, kind: "unknown" }])],
    ["a long row", (a) => (a.rows[0] = [{ length: 42, kind: "unknown" }])],
    ["a missing row", (a) => a.rows.pop()],
    ["metadata on an unknown run", (a) => (a.rows[0] = [{ length: 41, kind: "unknown", terrain: "sea" }])],
    ["a revealed run without display", (a) => delete a.rows[20].find((r) => r.kind === "terrain").display],
    ["a display with a private key", (a) => (a.rows[20].find((r) => r.kind === "terrain").display.source_key = "x")],
    ["a schema-2 body", (a) => (a.schema_version = 2)],
    ["a schema-3 body", (a) => (a.schema_version = 3)],
    ["a malformed district section", (a) => (a.district.rows[0][0].length = 4)],
    ["a node-form wilderness body", (a) => delete a.rows],
  ])("refuses %s in the validator and in both consumers", (_name, mutate) => {
    const area = clone(body());
    mutate(area);
    expect(() => validateAreaMapPanel(area)).toThrow();
    expect(decodeWildernessGrid(area)).toBeNull();
    expect(decodeTravelGrid(area)).toBeNull();
    expect(decodeWindow(area)).toEqual([]);
  });

  it("passes the supplied phase, radius, entities and sightings through", () => {
    const dusk = decodeTravelGrid(validateAreaMapPanel(body({ phase: "dusk", radius: 3 })));
    const night = decodeTravelGrid(validateAreaMapPanel(body({ phase: "night", radius: 1 })));
    expect([dusk.lightPhase, dusk.groundRadius]).toEqual(["dusk", 3]);
    expect([night.lightPhase, night.groundRadius]).toEqual(["night", 1]);
    expect(dusk.entities.map((e) => [e.label, e.count, e.threat])).toEqual([["合成狼", 1, "合成中階"], ["合成豬", 1, null]]);
    expect(dusk.sightings).toEqual([{ bearing: "北", distance_km: 15, silhouette_zh: "合成塔影", name: null }]);
    // Only the supplied facts differ, and the painted signature follows them.
    expect(paintSignature(dusk)).not.toBe(paintSignature(night));
    const sameFacts = decodeTravelGrid(validateAreaMapPanel(body({ phase: "dusk", radius: 3 })));
    expect(paintSignature(sameFacts)).toBe(paintSignature(dusk));
  });
});

describe("annotations on the stage", () => {
  function stage(props) {
    const w = mount(TravelMap, { props: { status: "ready", ...props }, attachTo: document.body });
    wrappers.push(w);
    return w;
  }

  it("draws live hostiles with their threat, or an explicit unknown one, and the lit landmark", async () => {
    const grid = decodeTravelGrid(validateAreaMapPanel(body()));
    const w = stage({ grid });
    await tick();
    const chips = w.findAll('[data-testid="travel-map__hostile-chip"]').map((c) => c.text());
    expect(chips).toHaveLength(2);
    expect(chips[0]).toContain("合成狼");
    expect(chips[0]).toContain("合成中階");
    expect(chips[1]).toContain("合成豬");
    expect(w.findAll('[data-testid="travel-map__hostile-chip"]')[1].find(".tm-chip__unknown").exists()).toBe(true);
    expect(w.findAll('[data-testid="travel-map__hostile"]')).toHaveLength(2);
    expect(w.findAll('[data-testid="travel-map__landmark"]')).toHaveLength(1);
    expect(w.text()).toContain("合成石標");
    expect(w.text()).toContain("合成渡口");
  });

  it("reads the aim readout from the supplied terrain label and says 未探明 for unknown ground", async () => {
    const grid = decodeTravelGrid(validateAreaMapPanel(body()));
    const w = stage({ grid, aim: "south" });
    await tick();
    expect(w.find('[data-testid="travel-map__aim-chip"]').text()).toContain(travelCellAt(grid, CX, CY - 1).display.terrain_label);
    await w.setProps({ aim: "west" });
    await tick();
    expect(w.find('[data-testid="travel-map__aim-chip"]').text()).toContain("未探明");
  });

  it("states the place card from the party cell's disclosed run and the supplied phase", () => {
    const grid = decodeTravelGrid(validateAreaMapPanel(body({ phase: "night", radius: 1 })));
    const here = travelCellAt(grid, CX, CY).display;
    expect(travelPlace(grid, "合成時刻")).toEqual({
      location: `${here.district_name}・${here.terrain_label}`,
      time: `合成時刻・${LIGHT_PHASE_NAMES.night}`,
    });
    // No disclosed district on the party cell: the window's caption stands in.
    const area = clone(body());
    area.rows[20] = row(new Map([[20, { terrain: "open_ground", d: { district: null } }]]));
    area.entities = [];
    area.nodes = area.nodes.filter((n) => Math.floor(n.y) === CY);
    area.edges = [];
    const bare = decodeTravelGrid(validateAreaMapPanel(area));
    expect(travelPlace(bare, null)).toEqual({ location: `${area.district_name}・${travelCellAt(bare, CX, CY).display.terrain_label}`, time: null });
    expect(travelPlace(null, "合成時刻")).toBeNull();
  });
});

describe("the live window's lifecycle", () => {
  it("shows the place card's travel lines only once the current window is adopted", async () => {
    const h = liveTravel({ wrappers });
    await tick();
    const ordinary = h.w.find('[data-testid="place-card__location"]').text();
    const area = wildernessArea();
    await h.answerMap(area);
    const grid = h.store.view.travel.map;
    const expected = travelPlace(grid, h.store.view.statusSlice.timeLabel);
    expect(expected.location).not.toBe(ordinary);
    expect(h.w.find('[data-testid="place-card__location"]').text()).toBe(expected.location);
    expect(h.w.find('[data-testid="place-card"]').text()).toContain(LIGHT_PHASE_NAMES[area.light_phase]);
  });

  it("recovers with exactly one correlated read after a same-position snapshot", async () => {
    const h = liveTravel({ wrappers });
    await tick();
    await h.answerMap(wildernessArea());
    expect(h.store.view.travel.mapStatus).toBe("ready");
    expect(h.mapViews()).toHaveLength(1);
    h.accept("ui_snapshot", fx.snapshot({ revision: h.next(), panels: panelsAt(WILD_SUBJECT) }));
    await tick();
    expect(h.mapViews()).toHaveLength(2);
    expect(h.store.view.travel.mapStatus).toBe("refreshing");
    await h.answerMap(wildernessArea());
    expect(h.store.view.travel.mapStatus).toBe("ready");
    // Adopting the recovery map is an update, never another recovery.
    await tick();
    await tick();
    expect(h.mapViews()).toHaveLength(2);
  });

  it("continues a queued walk after a normal refresh but never on a stale cell's window", () => {
    vi.useFakeTimers();
    try {
      setActivePinia(createPinia());
      const store = useElosernStore();
      const sender = fx.createFakeSender();
      store.setSender(sender);
      store.beginTransport(1);
      store.setConnected(true);
      const accept = (name, payload) => {
        const outcome = store.receive(store.view.generation, name, [payload], {});
        if (!outcome.accepted) throw new Error(`${name} rejected`);
      };
      accept("ui_snapshot", fx.snapshot({ panels: walkPanels(CX, CY) }));
      store.setTravelMap({ status: "ready", area: validateAreaMapPanel(walkArea(CX, CY)) });
      const moves = () => sender.sent.actions.filter((a) => a.action_id === "explore.move");
      store.holdTravel("east");
      vi.advanceTimersByTime(400);
      expect(moves()).toHaveLength(1);
      const revision = store.view.revision + 1;
      accept("ui_action_result", fx.actionResult({ request_id: moves()[0].request_id, presentation_revision: revision, outcome: "success", code: "moved", message: "你向前走去。" }));
      accept("ui_update", fx.update({ revision, panels: walkPanels(CX + 1, CY) }));
      // Refreshing suspends the walk without cancelling it.
      store.setTravelMap({ status: "refreshing", area: store.view.travel.area });
      vi.advanceTimersByTime(2000);
      expect(moves()).toHaveLength(1);
      expect(store.view.travel.walking).not.toBeNull();
      // A window for another cell is stale: the walk keeps waiting.
      store.setTravelMap({ status: "ready", area: validateAreaMapPanel(walkArea(CX + 9, CY)) });
      vi.advanceTimersByTime(2000);
      expect(moves()).toHaveLength(1);
      // The committed cell's own window resumes it.
      store.setTravelMap({ status: "ready", area: validateAreaMapPanel(walkArea(CX + 1, CY)) });
      vi.advanceTimersByTime(400);
      expect(moves()).toHaveLength(2);
    } finally {
      vi.useRealTimers();
    }
  });
});
