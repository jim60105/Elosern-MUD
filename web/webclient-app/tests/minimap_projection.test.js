// compute-minimap-auto-scale-projection: the minimap island's pure metric
// projection (approved design 2026-10-22-minimap-auto-scale-design §3–§5,
// §6.3, §8). Every case is a fixed input; no DOM or Vue is involved.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import {
  CANVAS_SIZE,
  CENTRE,
  DEFAULT_LEVEL,
  EQUAL_RADIUS,
  EXIT_FOOTPRINT,
  LEVELS,
  MAX_SPREAD_DEG,
  R_MAX,
  R_MIN,
  WILDERNESS_CELL_METRES,
  mapKeyOf,
  previousLevelFor,
  projectIsland,
  rememberLevel,
  selectScale,
} from "../lib/minimap_projection.js";
import { HALO_R } from "../composables/use-map-lattice-geometry.js";

const Z = "altoria";

function node(id, x, y, extra = {}) {
  return { id, label: id, x, y, visibility: "visible_unvisited", action: null, gateway: null, ...extra };
}

function gridId(x, y, z = Z) {
  return `grid:${z}:${x}:${y}`;
}

function current(id, x, y, extra = {}) {
  return node(id, x, y, { visibility: "current", current: true, ...extra });
}

function move(destination) {
  return { kind: "move", exit_ref: `#${destination}`, destination };
}

// A grid model: the current node at (cx, cy) and labelled exits at the given
// metre offsets, plus optional unlabelled star-edge context.
function gridModel(cx, cy, exits, context = []) {
  const cur = current(gridId(cx, cy), cx, cy);
  const nodes = [cur];
  const edges = [];
  exits.forEach(([dx, dy, extra], i) => {
    const id = gridId(cx + dx, cy + dy);
    nodes.push(node(id, cx + dx, cy + dy, { action: move(id), ...(extra || {}) }));
    edges.push({ source: cur.id, destination: id, label: `exit-${i}`, known: true, traversable: true });
  });
  context.forEach(([dx, dy]) => {
    const id = gridId(cx + dx, cy + dy);
    nodes.push(node(id, cx + dx, cy + dy));
    edges.push({ source: cur.id, destination: id, label: "", known: true, traversable: false });
  });
  return { nodes, edges, currentNode: cur.id };
}

function byId(projection, id) {
  return projection.nodes.find((entry) => entry.id === id);
}

function radiusOf(entry) {
  return Math.hypot(entry.x - CENTRE, entry.y - CENTRE);
}

function bearingOf(entry) {
  const theta = (Math.atan2(entry.x - CENTRE, CENTRE - entry.y) * 180) / Math.PI;
  return ((theta % 360) + 360) % 360;
}

function exitsOf(projection) {
  return projection.nodes.filter((entry) => entry.tier === "exit");
}

function allFinite(projection) {
  return projection.nodes.every((entry) => Number.isFinite(entry.x) && Number.isFinite(entry.y));
}

describe("constants", () => {
  it("centralizes the canvas, radii, ladder and default level", () => {
    expect(CANVAS_SIZE).toBe(240);
    expect(CENTRE).toBe(120);
    expect(R_MIN).toBe(36);
    expect(R_MAX).toBe(88);
    expect(LEVELS).toEqual([10, 15, 20, 30, 50, 75, 100, 150, 200, 300, 500, 750, 1000, 1500, 2000, 3000, 5000]);
    expect(Object.isFrozen(LEVELS)).toBe(true);
    expect(DEFAULT_LEVEL).toBe(100);
    expect(EQUAL_RADIUS).toBe(66);
    expect(MAX_SPREAD_DEG).toBe(20);
    expect(WILDERNESS_CELL_METRES).toBe(1000);
  });

  it("measures the exit footprint from the existing marker geometry", () => {
    expect(EXIT_FOOTPRINT).toBe(2 * HALO_R);
  });

  it("adjacent ladder levels differ by at most 1.67x", () => {
    for (let i = 1; i < LEVELS.length; i += 1) {
      expect(LEVELS[i] / LEVELS[i - 1]).toBeLessThanOrEqual(5 / 3 + 1e-9);
    }
  });

  it("the module imports nothing from Vue and touches no DOM global", () => {
    const source = readFileSync(resolve(process.cwd(), "web/webclient-app/lib/minimap_projection.js"), "utf8");
    const imports = [...source.matchAll(/^import .* from "([^"]+)";$/gm)].map((match) => match[1]);
    expect(imports).toEqual(["./local_map.js"]);
    expect(source).not.toMatch(/\b(document|window|globalThis|requestAnimationFrame)\b/);
  });
});

describe("tiers and coordinate frames", () => {
  it("places the current node at the centre and classifies exits and context", () => {
    const model = gridModel(3000, 3000, [[0, 900]], [[600, 0]]);
    const projection = projectIsland(model, null);
    expect(projection.nodes[0]).toEqual({ id: gridId(3000, 3000), x: 120, y: 120, tier: "current", gateway: null });
    expect(byId(projection, gridId(3000, 3900)).tier).toBe("exit");
    expect(byId(projection, gridId(3600, 3000)).tier).toBe("context");
  });

  it("a labelled exit with a null action is still an exit, in either edge direction", () => {
    const model = gridModel(1000, 1000, [[0, 500, { action: null }]]);
    const west = node(gridId(500, 1000), 500, 1000);
    model.nodes.push(west);
    model.edges.push({ source: west.id, destination: model.currentNode, label: "東", known: true, traversable: false });
    const projection = projectIsland(model, null);
    expect(byId(projection, gridId(1000, 1500)).tier).toBe("exit");
    expect(byId(projection, west.id).tier).toBe("exit");
  });

  it("star edges with an empty label only supply context", () => {
    const model = gridModel(1000, 1000, [], [[0, 400], [400, 0]]);
    const projection = projectIsland(model, null);
    expect(exitsOf(projection)).toEqual([]);
    expect(projection.nodes.filter((entry) => entry.tier === "context")).toHaveLength(2);
  });

  it("grid deltas are metres: exits keep exact bearings", () => {
    const model = gridModel(2000, 2000, [[0, 800], [800, 0], [0, -800], [-600, -600]]);
    const projection = projectIsland(model, null);
    expect(projection.level).toBe(1000);
    expect(bearingOf(byId(projection, gridId(2000, 2800)))).toBeCloseTo(0, 6);
    expect(bearingOf(byId(projection, gridId(2800, 2000)))).toBeCloseTo(90, 6);
    expect(bearingOf(byId(projection, gridId(2000, 1200)))).toBeCloseTo(180, 6);
    expect(bearingOf(byId(projection, gridId(1400, 1400)))).toBeCloseTo(225, 6);
  });

  it("wilderness cell deltas are one kilometre: the 3x3 neighbourhood selects 2000", () => {
    const cx = 1200;
    const cy = 900;
    const cur = current(`wild:wilderness:${cx}:${cy}`, cx, cy);
    const nodes = [cur];
    const edges = [];
    for (const [dx, dy] of [[0, 1], [1, 1], [1, 0], [1, -1], [0, -1], [-1, -1], [-1, 0], [-1, 1]]) {
      const id = `wild:wilderness:${cx + dx}:${cy + dy}`;
      nodes.push(node(id, cx + dx, cy + dy, { action: move(id) }));
      edges.push({ source: cur.id, destination: id, label: "n", known: true, traversable: true });
    }
    const payloadCopy = JSON.parse(JSON.stringify(nodes));
    const projection = projectIsland({ nodes, edges, currentNode: cur.id }, null);
    expect(projection.mode).toBe("uniform");
    expect(projection.level).toBe(2000);
    const radii = exitsOf(projection).map(radiusOf);
    expect(radii.filter((r) => Math.abs(r - 50) < 1e-6)).toHaveLength(4);
    expect(radii.filter((r) => Math.abs(r - 50 * Math.SQRT2) < 1e-6)).toHaveLength(4);
    // The payload coordinates are never rewritten, and no legend is read.
    expect(nodes).toEqual(payloadCopy);
    expect(projection.grid.metres).toBe(400);
  });
});

describe("level selection", () => {
  it("Altoria plaza exits at about 850–1090 m choose 1500 with radii about 57–72", () => {
    const model = gridModel(3500, 3480, [[0, 850], [1090, 0], [-700, -600], [0, -1000]]);
    const projection = projectIsland(model, null);
    expect(projection.mode).toBe("uniform");
    expect(projection.level).toBe(1500);
    const radii = exitsOf(projection).map(radiusOf);
    expect(Math.min(...radii)).toBeCloseTo(850 / 15, 6);
    expect(Math.max(...radii)).toBeCloseTo(1090 / 15, 6);
    expect(Math.min(...radii)).toBeGreaterThan(56);
    expect(Math.max(...radii)).toBeLessThan(73);
  });

  it("chooses the smallest fitting level along the whole ladder", () => {
    for (const level of LEVELS) {
      const exact = projectIsland(gridModel(10000, 10000, [[0, level * 0.88]]), null);
      expect(exact.level).toBe(level);
      expect(radiusOf(exitsOf(exact)[0])).toBeCloseTo(88, 6);
    }
  });

  it("a nearest radius exactly 36 stays uniform; just below is compressed", () => {
    const exact = projectIsland(gridModel(5000, 5000, [[0, 360], [0, -880]]), null);
    expect(exact.mode).toBe("uniform");
    expect(exact.level).toBe(1000);
    expect(radiusOf(byId(exact, gridId(5000, 5360)))).toBeCloseTo(36, 9);
    const below = projectIsland(gridModel(5000, 5000, [[0, 359], [0, -880]]), null);
    expect(below.mode).toBe("compressed");
    expect(below.level).toBe(1000);
  });

  it("a farthest radius exactly 88 at level 5000 fits; beyond 4400 m compresses", () => {
    const exact = projectIsland(gridModel(5000, 5000, [[0, 4400], [0, -2000]]), null);
    expect(exact.mode).toBe("uniform");
    expect(exact.level).toBe(5000);
    expect(radiusOf(byId(exact, gridId(5000, 9400)))).toBeCloseTo(88, 9);
    const over = projectIsland(gridModel(5000, 5000, [[0, 4401], [0, -2000]]), null);
    expect(over.mode).toBe("compressed");
    expect(over.level).toBe(5000);
    expect(exitsOf(over).every((entry) => radiusOf(entry) <= R_MAX + 1e-9)).toBe(true);
  });

  it("an 80 m exit beside a 1200 m exit triggers compression", () => {
    const projection = projectIsland(gridModel(3000, 3000, [[80, 0], [0, -1200]]), null);
    expect(projection.mode).toBe("compressed");
    expect(projection.level).toBe(1500);
  });
});

describe("hysteresis", () => {
  const model = () => gridModel(3000, 3000, [[0, 850], [0, -1000]]);

  it("keeps a previous level one step coarser that still fits", () => {
    expect(projectIsland(model(), 1500).level).toBe(1500);
    expect(projectIsland(model(), 2000).level).toBe(2000);
  });

  it("replaces a level two steps coarser by the ideal", () => {
    expect(projectIsland(model(), 3000).level).toBe(1500);
  });

  it("replaces an insufficient previous level by the ideal", () => {
    expect(projectIsland(model(), 1000).level).toBe(1500);
  });

  it("replaces a one-step-coarser level that would put the nearest exit inside R_MIN", () => {
    // Ideal 1000 puts 360 m at exactly 36; at 1500 it would be 24.
    const tight = gridModel(3000, 3000, [[0, 360], [0, -880]]);
    expect(projectIsland(tight, 1500).level).toBe(1000);
    expect(projectIsland(tight, 1500).mode).toBe("uniform");
  });

  it("ignores a previous value that is not a ladder level", () => {
    expect(selectScale([1000], 1234)).toEqual({ mode: "uniform", level: 1500 });
  });

  it("a compressed result's level is a valid input to the next call", () => {
    const over = projectIsland(gridModel(5000, 5000, [[0, 6000], [0, -100]]), null);
    expect(LEVELS).toContain(over.level);
    const next = projectIsland(model(), over.level);
    expect(next.level).toBe(1500);
  });

  it("the caller helper resets the previous level only when the map key changes", () => {
    const first = projectIsland(model(), null);
    const memory = rememberLevel(gridId(3000, 3000), first);
    expect(memory).toEqual({ mapKey: `grid:${Z}`, level: 1500 });
    // An ordinary move on the same map keeps the remembered level.
    expect(previousLevelFor(memory, gridId(3010, 3000))).toBe(1500);
    // A different grid map or layer discards it before selection.
    expect(previousLevelFor(memory, gridId(10, 10, "ciaran"))).toBeNull();
    expect(previousLevelFor(memory, "wild:wilderness:5:5")).toBeNull();
    expect(previousLevelFor(null, gridId(1, 1))).toBeNull();
    const reset = projectIsland(gridModel(3000, 3000, [[0, 850]], []), previousLevelFor(memory, gridId(1, 1, "ciaran")));
    expect(reset.level).toBe(1000);
  });

  it("derives map keys from the canonical node-id grammar", () => {
    expect(mapKeyOf("grid:altoria:3500:3480")).toBe("grid:altoria");
    expect(mapKeyOf("wild:wilderness:1:2")).toBe("wild:wilderness");
    expect(mapKeyOf("room:42")).toBe("room");
    expect(mapKeyOf("")).toBeNull();
    expect(mapKeyOf(null)).toBeNull();
  });
});

describe("compressed mapping", () => {
  it("maps exits logarithmically from 36 to 88 with unchanged bearings and order", () => {
    const model = gridModel(3000, 3000, [[80, 0], [0, 300], [0, -1200]], [[-40, 0]]);
    const projection = projectIsland(model, null);
    expect(projection.mode).toBe("compressed");
    const near = byId(projection, gridId(3080, 3000));
    const mid = byId(projection, gridId(3000, 3300));
    const far = byId(projection, gridId(3000, 1800));
    expect(radiusOf(near)).toBeCloseTo(36, 9);
    expect(radiusOf(far)).toBeCloseTo(88, 9);
    expect(radiusOf(mid)).toBeCloseTo(36 + (52 * Math.log(300 / 80)) / Math.log(1200 / 80), 9);
    expect(bearingOf(near)).toBeCloseTo(90, 6);
    expect(bearingOf(mid)).toBeCloseTo(0, 6);
    expect(bearingOf(far)).toBeCloseTo(180, 6);
    // Context closer than d_min maps linearly inside R_MIN.
    expect(radiusOf(byId(projection, gridId(2960, 3000)))).toBeCloseTo((36 * 40) / 80, 9);
  });

  it("the mapping is monotonic in distance", () => {
    const distances = [20, 80, 150, 400, 900, 1200];
    const model = gridModel(3000, 3000, [[80, 0], [0, -1200]], distances.map((d) => [-d, 1]));
    const projection = projectIsland(model, null);
    const radii = distances.map((d) => radiusOf(byId(projection, gridId(3000 - d, 3001))));
    for (let i = 1; i < radii.length; i += 1) expect(radii[i]).toBeGreaterThan(radii[i - 1]);
  });

  it("equal positive exit distances in compressed mode sit at radius 66", () => {
    const projection = projectIsland(gridModel(6000, 6000, [[0, 5000], [5000, 0], [0, -5000]]), null);
    expect(projection.mode).toBe("compressed");
    for (const entry of exitsOf(projection)) expect(radiusOf(entry)).toBeCloseTo(66, 9);
    expect(allFinite(projection)).toBe(true);
  });
});

describe("sparse and coincident inputs", () => {
  it("with no exits, drawable context supplies the level", () => {
    const projection = projectIsland(gridModel(3000, 3000, [], [[0, 850], [400, 0]]), null);
    expect(projection.level).toBe(1000);
    expect(exitsOf(projection)).toEqual([]);
  });

  it("context-only inputs follow the same compression policy", () => {
    const projection = projectIsland(gridModel(3000, 3000, [], [[0, 50], [1200, 0]]), null);
    expect(projection.mode).toBe("compressed");
  });

  it("with no positive distance, the default level applies and current stays centred", () => {
    const alone = projectIsland(gridModel(3000, 3000, []), 1500);
    expect(alone.level).toBe(DEFAULT_LEVEL);
    expect(alone.mode).toBe("uniform");
    expect(alone.nodes).toEqual([{ id: gridId(3000, 3000), x: 120, y: 120, tier: "current", gateway: null }]);
  });

  it("a missing current node yields an empty, finite projection", () => {
    const projection = projectIsland({ nodes: [], edges: [], currentNode: null }, null);
    expect(projection.nodes).toEqual([]);
    expect(projection.level).toBe(DEFAULT_LEVEL);
  });

  it("zero-distance exits take evenly spaced bearings north first at R_MIN", () => {
    const cur = current(gridId(3000, 3000), 3000, 3000);
    const ids = ["a", "b", "c"].map((suffix) => `grid:${Z}:3000:3000${suffix}`);
    // Distinct ids at the same coordinates (a defensive input shape).
    const nodes = [cur, ...ids.map((id) => node(id, 3000, 3000, { action: move(id) }))];
    const edges = ids.map((id) => ({ source: cur.id, destination: id, label: "x", known: true, traversable: true }));
    const projection = projectIsland({ nodes, edges, currentNode: cur.id }, null);
    expect(projection.level).toBe(DEFAULT_LEVEL);
    expect(allFinite(projection)).toBe(true);
    const placed = ids.map((id) => byId(projection, id));
    placed.forEach((entry) => expect(radiusOf(entry)).toBeCloseTo(R_MIN, 9));
    expect(bearingOf(placed[0])).toBeCloseTo(0, 6);
    expect(bearingOf(placed[1])).toBeCloseTo(120, 6);
    expect(bearingOf(placed[2])).toBeCloseTo(240, 6);
  });

  it("a zero-distance exit beside real exits keeps the scale from the positive ones", () => {
    const model = gridModel(3000, 3000, [[0, 850]]);
    const zid = `grid:${Z}:3000:3000z`;
    model.nodes.push(node(zid, 3000, 3000));
    model.edges.push({ source: model.currentNode, destination: zid, label: "上", known: true, traversable: false });
    const projection = projectIsland(model, null);
    expect(projection.level).toBe(1000);
    expect(radiusOf(byId(projection, zid))).toBeCloseTo(R_MIN, 9);
    expect(bearingOf(byId(projection, zid))).toBeCloseTo(0, 6);
  });

  it("omits context outside the canvas", () => {
    const projection = projectIsland(gridModel(3000, 3000, [[0, 880]], [[0, 1300], [1300, 1300], [300, 0]]), null);
    expect(byId(projection, gridId(3000, 4300))).toBeUndefined();
    expect(byId(projection, gridId(4300, 4300))).toBeUndefined();
    expect(byId(projection, gridId(3300, 3000)).tier).toBe("context");
    projection.nodes.forEach((entry) => {
      expect(entry.x).toBeGreaterThanOrEqual(0);
      expect(entry.x).toBeLessThanOrEqual(CANVAS_SIZE);
      expect(entry.y).toBeGreaterThanOrEqual(0);
      expect(entry.y).toBeLessThanOrEqual(CANVAS_SIZE);
    });
  });

  it("skips remembered nodes: they keep the edge-direction markers", () => {
    const model = gridModel(3000, 3000, [[0, 850]]);
    const far = node(gridId(3000, 9000), 3000, 9000, { visibility: "remembered" });
    model.nodes.push(far);
    model.edges.push({ source: model.currentNode, destination: far.id, label: "北", known: true, traversable: false });
    const projection = projectIsland(model, null);
    expect(byId(projection, far.id)).toBeUndefined();
    expect(projection.level).toBe(1000);
  });
});

describe("overlap spreading", () => {
  it("spreads coincident-bearing exits symmetrically about their mean within ±20°", () => {
    const model = gridModel(3000, 3000, [[0, 800], [0, 820], [800, 0]]);
    const projection = projectIsland(model, null);
    const a = byId(projection, gridId(3000, 3800));
    const b = byId(projection, gridId(3000, 3820));
    const east = byId(projection, gridId(3800, 3000));
    const ba = bearingOf(a) > 180 ? bearingOf(a) - 360 : bearingOf(a);
    const bb = bearingOf(b) > 180 ? bearingOf(b) - 360 : bearingOf(b);
    expect(ba + bb).toBeCloseTo(0, 6);
    expect(Math.abs(ba)).toBeLessThanOrEqual(MAX_SPREAD_DEG + 1e-9);
    expect(Math.abs(ba)).toBeGreaterThan(0);
    expect(Math.hypot(a.x - b.x, a.y - b.y)).toBeGreaterThanOrEqual(EXIT_FOOTPRINT - 1e-6);
    // Radii and the unaffected exit's bearing stay exact.
    expect(radiusOf(a)).toBeCloseTo(80, 9);
    expect(radiusOf(b)).toBeCloseTo(82, 9);
    expect(bearingOf(east)).toBeCloseTo(90, 9);
  });

  it("a group straddling north keeps its members' order", () => {
    // Bearings about 357° and 3° at radius ~80 overlap across north.
    const model = gridModel(3000, 3000, [[-40, 799], [40, 799]]);
    const projection = projectIsland(model, null);
    const west = byId(projection, gridId(2960, 3799));
    const east = byId(projection, gridId(3040, 3799));
    const bw = bearingOf(west) - 360;
    const be = bearingOf(east);
    expect(bw).toBeLessThan(0);
    expect(be).toBeGreaterThan(0);
    expect(bw + be).toBeCloseTo(0, 6);
    expect(be).toBeLessThanOrEqual(MAX_SPREAD_DEG);
  });

  it("caps a large coincident group at ±20°", () => {
    const model = gridModel(3000, 3000, [[0, 800], [0, 801], [0, 802], [0, 803], [0, 804]]);
    const projection = projectIsland(model, null);
    const bearings = exitsOf(projection).map((entry) => {
      const b = bearingOf(entry);
      return b > 180 ? b - 360 : b;
    });
    expect(Math.max(...bearings)).toBeCloseTo(20, 6);
    expect(Math.min(...bearings)).toBeCloseTo(-20, 6);
  });

  it("accepts an explicit footprint", () => {
    // About 25 units apart: clear of the default 20, inside a 30 footprint.
    const model = gridModel(3000, 3000, [[0, 800], [250, 800]]);
    expect(bearingOf(byId(projectIsland(model, null), gridId(3000, 3800)))).toBeCloseTo(0, 9);
    const wide = projectIsland(model, null, { footprint: 30 });
    expect(bearingOf(byId(wide, gridId(3000, 3800)))).not.toBeCloseTo(0, 3);
  });

  it("context never spreads and draws no invented route", () => {
    const projection = projectIsland(gridModel(3000, 3000, [[0, 800]], [[0, 810]]), null);
    expect(bearingOf(byId(projection, gridId(3000, 3810)))).toBeCloseTo(0, 9);
    expect(bearingOf(byId(projection, gridId(3000, 3800)))).toBeCloseTo(0, 9);
    expect(Object.keys(projection)).not.toContain("edges");
  });
});

describe("gateway stubs", () => {
  // A city gate: current grid node hosting a gateway, with the wilderness
  // target at a renderer-local slot one lattice cell away.
  function gateModel(slot) {
    const cur = current(gridId(3500, 0), 3500, 0, { gateway: { leads_to: "南方荒野" } });
    const wildId = "wild:wilderness:1200:880";
    const wildAction = move(wildId);
    const nodes = [
      cur,
      node(gridId(3500, 900), 3500, 900, { action: move(gridId(3500, 900)) }),
      node(gridId(4400, 0), 4400, 0, { action: null }),
      node(wildId, 3500, -slot, { action: wildAction }),
    ];
    const edges = [
      { source: cur.id, destination: gridId(3500, 900), label: "北", known: true, traversable: true },
      { source: cur.id, destination: gridId(4400, 0), label: "東", known: true, traversable: false },
      { source: cur.id, destination: wildId, label: "南", known: true, traversable: true },
    ];
    return { model: { nodes, edges, currentNode: cur.id }, wildAction };
  }

  it("excludes the cross-layer target from nodes and scale; the slot offset changes nothing", () => {
    const near = gateModel(10);
    const far = gateModel(900);
    const a = projectIsland(near.model, null);
    const b = projectIsland(far.model, null);
    expect(a.nodes.map((entry) => entry.id)).not.toContain("wild:wilderness:1200:880");
    expect(a.level).toBe(1500);
    expect(b.level).toBe(a.level);
    expect(b.mode).toBe(a.mode);
    expect(b.nodes).toEqual(a.nodes);
  });

  it("yields a stub with the bearing, the current gate's 通往 label and the original action", () => {
    const { model, wildAction } = gateModel(10);
    const { exitStubs } = projectIsland(model, null);
    expect(exitStubs).toHaveLength(1);
    expect(exitStubs[0].bearing).toBeCloseTo(180, 9);
    expect(exitStubs[0].label).toBe("通往 南方荒野");
    expect(exitStubs[0].action).toBe(wildAction);
  });

  it("keeps a null action on a locked gate stub", () => {
    const { model } = gateModel(10);
    model.nodes[3].action = null;
    expect(projectIsland(model, null).exitStubs[0].action).toBeNull();
  });

  it("a wilderness return stub takes its label from the city gate target", () => {
    const cur = current("wild:wilderness:1200:880", 1200, 880);
    const gateId = gridId(3500, 0);
    const gateAction = move(gateId);
    const nodes = [
      cur,
      node("wild:wilderness:1200:879", 1200, 879, { action: move("wild:wilderness:1200:879") }),
      node(gateId, 1200, 881, { action: gateAction, gateway: { leads_to: "雅托利亞" } }),
    ];
    const edges = [
      { source: cur.id, destination: "wild:wilderness:1200:879", label: "south", known: true, traversable: true },
      { source: cur.id, destination: gateId, label: "north", known: true, traversable: true },
    ];
    const projection = projectIsland({ nodes, edges, currentNode: cur.id }, null);
    expect(projection.exitStubs).toEqual([{ bearing: 0, label: "通往 雅托利亞", action: gateAction }]);
    expect(projection.exitStubs[0].action).toBe(gateAction);
    // Only the 1 km same-layer exit sets the scale.
    expect(projection.level).toBe(1500);
    expect(byId(projection, gateId)).toBeUndefined();
  });

  it("prefers the current gate's metadata when both carry one, then falls back to the target label", () => {
    const { model } = gateModel(10);
    model.nodes[3].gateway = { leads_to: "反向" };
    expect(projectIsland(model, null).exitStubs[0].label).toBe("通往 南方荒野");
    model.nodes[0].gateway = null;
    model.nodes[3].gateway = null;
    model.nodes[3].label = "荒野入口";
    expect(projectIsland(model, null).exitStubs[0].label).toBe("通往 荒野入口");
  });

  it("emits stubs in payload order and none for a non-exit cross-layer node", () => {
    const { model } = gateModel(10);
    const second = "wild:wilderness:1201:880";
    model.nodes.push(node(second, 3510, 0, { action: move(second) }));
    model.edges.push({ source: model.currentNode, destination: second, label: "東南", known: true, traversable: true });
    model.nodes.push(node("wild:wilderness:9:9", 3600, 0));
    const { exitStubs } = projectIsland(model, null);
    expect(exitStubs.map((stub) => stub.bearing.toFixed(3))).toEqual(["180.000", "90.000"]);
  });
});

describe("background", () => {
  it("uniform dots are anchored to integer world multiples of M/5", () => {
    const at = (x, y) => projectIsland(gridModel(x, y, [[0, 850], [0, -1000]]), null);
    const a = at(3000, 3000);
    expect(a.level).toBe(1500);
    expect(a.grid).toEqual({ kind: "dots", spacing: 20, metres: 300, offsetX: 0, offsetY: 0 });
    expect(a.scaleLabel).toBe("格距 300 m");
    // Moving 100 m east and 60 m north slides the dot phase with the ground.
    const b = at(3100, 3060);
    expect(b.level).toBe(1500);
    expect(b.grid.offsetX).toBeCloseTo(20 - (100 / 300) * 20, 9);
    expect(b.grid.offsetY).toBeCloseTo((60 / 300) * 20, 9);
    // A world dot at (3300, 3300) metres sits on that lattice in both frames.
    for (const [frame, cx, cy] of [[a, 3000, 3000], [b, 3100, 3060]]) {
      const sx = 120 + ((3300 - cx) * 100) / 1500;
      const sy = 120 - ((3300 - cy) * 100) / 1500;
      expect((((sx - frame.grid.offsetX) % 20) + 20) % 20).toBeCloseTo(0, 6);
      expect((((sy - frame.grid.offsetY) % 20) + 20) % 20).toBeCloseTo(0, 6);
    }
  });

  it("captions kilometre spacing at the coarsest level", () => {
    const projection = projectIsland(gridModel(5000, 5000, [[0, 4400], [0, -2000]]), null);
    expect(projection.scaleLabel).toBe("格距 1 km");
  });

  it("compressed rings sit at real distances through the same mapping", () => {
    const model = gridModel(3000, 3000, [[80, 0], [0, -1200]]);
    const projection = projectIsland(model, null);
    expect(projection.grid.kind).toBe("rings");
    expect(projection.grid).not.toHaveProperty("spacing");
    expect(projection.scaleLabel).toBe("距離壓縮");
    const rings = projection.grid.rings;
    expect(rings.map((ring) => ring.label)).toEqual(["100 m", "300 m", "1 km", "3 km"]);
    for (const ring of rings) {
      const expected = 36 + (52 * Math.log(ring.distance / 80)) / Math.log(1200 / 80);
      expect(ring.radius).toBeCloseTo(expected, 9);
      expect(ring.radius).toBeLessThanOrEqual(CENTRE);
    }
    for (let i = 1; i < rings.length; i += 1) {
      expect(rings[i].radius - rings[i - 1].radius).toBeGreaterThanOrEqual(16);
    }
  });

  it("over-capacity rings stay bounded and on the canvas", () => {
    const projection = projectIsland(gridModel(6000, 6000, [[0, 6000], [0, -100]]), null);
    expect(projection.grid.rings.length).toBeGreaterThan(0);
    expect(projection.grid.rings.length).toBeLessThanOrEqual(4);
    projection.grid.rings.forEach((ring) => expect(ring.radius).toBeLessThanOrEqual(CENTRE));
    expect(allFinite(projection)).toBe(true);
  });
});
