// The offline capture contract: coordinate frames, camera arithmetic and the
// per-view layer classification. Synthetic scenes only — no repository map
// content, no DOM. Real painted geometry (fonts, cards, labels, containment)
// is measured in web/tests/browser/test_map_capture_surface.py.
import { test } from "node:test";
import assert from "node:assert/strict";

import { continentScene, interiorScene, settlementScene } from "../src/lib/map_scene.js";
import {
  CAPTURE_LAYERS,
  FIT_TOLERANCE,
  boxContains,
  boxOfView,
  captureAxes,
  captureLayers,
  captureScene,
  captureUnits,
  convergeFit,
  expandToAspect,
  frameBoundsOf,
  normalizedHidden,
  sceneExtent,
  sceneFrameBounds,
  unionBox,
  viewOfBox,
} from "../src/lib/capture.js";

// `+ 0` folds negative zero into 0 so a rounded extent compares plainly.
const round = (values) => values.map((value) => Math.round(value * 1e6) / 1e6 + 0);

// A synthetic projection: one 1 km cell, one river with a ford, a ridge wall
// and a pass, a harbour site, one settlement footprint, one district outline
// and one derived national border. Every continent layer owns a drawable.
function continentWorld() {
  return {
    continent: {
      cell_size_km: 1,
      frame_cells: 40,
      mainland_boundary_km: [
        [0, 0],
        [40, 0],
        [40, 40],
        [0, 40],
      ],
      waterways: [{ id: "river", route_m: [[20000, 20000], [0, 20000]], fords_m: [[10000, 20000]], border_river_key: "river" }],
      forest_edge_m: [[0, 30000], [39000, 30000]],
      harbor_sites: [{ id: "harbour", display_name: "港", centre_m: [35000, 5000] }],
      terrain_preview: {
        status: "current",
        columns: 50,
        rows: 50,
        step: 1,
        ridge_walls: [[[[10, 10], [10, 11]]]],
        national_borders: [{ nation_keys: ["a", "b"], points: [[20, 20], [20, 21]] }],
        passes: [{ index: 0, centre: [10, 10], y_min: 9, y_max: 11 }],
      },
    },
    settlements: [{ id: "town", footprint: { cells: [[3, 3]] } }],
    locations: [{ qualified_ref: "location:town", display_name_zh: "城", centre_m: [5000, 5000], local_m: [5000, 5000], local_maps: [] }],
    districts: [{ id: "d1", district_name_zh: "區" }],
  };
}

const PARTITION = { outlines: { d1: [[0, 0, 10, 0, 10, 10, 0, 10]] } };

function continent() {
  return continentScene(continentWorld(), [], PARTITION);
}

function interiorWorld() {
  const interior = {
    id: "hall",
    relative_path: "content/maps/interiors/hall.yaml",
    rooms: [
      { id: "front", qualified_ref: "interior_room:hall:front", name_zh: "前廳", layout_position: [0, 0] },
      { id: "back", qualified_ref: "interior_room:hall:back", name_zh: "後室", layout_position: [1, 0] },
    ],
    connections: [
      { source: "front", destination: "back", label: "in" },
      { source: "back", destination: "front", label: "out" },
    ],
    exterior: { settlement: "town", node: "yard", room: "front", doorway_key: "Door", doorway_aliases: [] },
  };
  return {
    interiors: [interior],
    settlements: [
      {
        id: "town",
        relative_path: "content/maps/settlements/town.yaml",
        nodes: [{ id: "yard", qualified_ref: "settlement_node:town:yard", key: "Yard", local_m: [0, 0] }],
        roads: [],
        wilderness_entry: null,
        city_gate: null,
      },
    ],
  };
}

function settlement() {
  return settlementScene({
    id: "town",
    city_gate: { node: "gate" },
    wilderness_entry: null,
    nodes: [
      { id: "gate", qualified_ref: "settlement_node:town:gate", key: "Gate", local_m: [0, 0] },
      { id: "yard", qualified_ref: "settlement_node:town:yard", key: "Yard", local_m: [300, 400] },
    ],
    roads: [
      { id: "gate>yard", source: "gate", destination: "yard", direction: "ne", bends: [[300, 0]], length_m: 500 },
      { id: "yard>gate", source: "yard", destination: "gate", direction: "s", bends: [], length_m: 500 },
    ],
  });
}

function drawablesOf(scene) {
  return {
    shapeLayers: scene.shapes.map((shape) => shape.layer),
    markLayers: scene.marks.map((mark) => mark.layer),
    linkKinds: scene.links.map((link) => link.kind ?? null),
    raster: scene.raster?.layer ?? null,
  };
}

test("continent kilometre bounds convert to scene metres and expand to the frame aspect", () => {
  const requested = sceneFrameBounds("continent", [0, 0, 10, 20]);
  assert.deepEqual(requested, { minX: 0, minY: 0, maxX: 10000, maxY: 20000 });
  const frame = { width: 200, height: 100 };
  const expanded = expandToAspect(requested, frame.width, frame.height);
  assert.deepEqual(expanded, { minX: -15000, minY: 0, maxX: 25000, maxY: 20000 });
  const camera = viewOfBox(expanded, frame);
  assert.deepEqual(camera, { cx: 5000, cy: 10000, span: 40000 });
  // The whole requested extent is inside the image, and the reported frame is
  // the input frame again: kilometres, centre kept, uniform scale only.
  const covered = boxOfView(camera, frame);
  assert.ok(boxContains(covered, expanded, 0));
  assert.equal((covered.maxX - covered.minX) / (covered.maxY - covered.minY), 2, "one uniform scale on both axes");
  assert.deepEqual(round(frameBoundsOf("continent", covered)), [-15, 0, 25, 20]);
  assert.equal(captureUnits("continent"), "km");
  assert.deepEqual(captureAxes("continent"), { x: "east", y: "north" });
});

test("an out-of-map region is neither clamped nor recentred", () => {
  const requested = sceneFrameBounds("continent", [-100, -100, 10, 20]);
  const frame = { width: 400, height: 100 };
  const expanded = expandToAspect(requested, frame.width, frame.height);
  // 110 km wide against 120 km tall at a 4:1 frame: the taller axis wins and
  // X grows to 480 km around the requested centre.
  assert.deepEqual(round(frameBoundsOf("continent", expanded)), [-285, -100, 195, 20]);
  assert.equal((expanded.minX + expanded.maxX) / 2, -45000);
  assert.equal((expanded.minY + expanded.maxY) / 2, -40000);
});

test("a region that contains no objects still reports exactly that region", () => {
  // A 1 km square in the empty south-west of the synthetic continent: no
  // location, ford, pass or road lies inside it, and no content may pull the
  // camera towards it.
  const requested = sceneFrameBounds("continent", [0, 0, 1, 1]);
  const frame = { width: 320, height: 240 };
  const expanded = expandToAspect(requested, frame.width, frame.height);
  // 4:3 output: the kilometre square grows only on X, around its own centre.
  assert.deepEqual(round([expanded.minX, expanded.minY, expanded.maxX, expanded.maxY]), [-166.666667, 0, 1166.666667, 1000]);
  const camera = viewOfBox(expanded, frame);
  assert.deepEqual(round([camera.cx, camera.cy, camera.span]), [500, 500, 1333.333333]);
  assert.deepEqual(round(frameBoundsOf("continent", boxOfView(camera, frame))), [-0.166667, 0, 1.166667, 1]);
});

test("settlement bounds stay in local metres", () => {
  const requested = sceneFrameBounds("settlement", [0, 0, 30, 40]);
  assert.deepEqual(requested, { minX: 0, minY: 0, maxX: 30, maxY: 40 });
  const frame = { width: 100, height: 100 };
  const expanded = expandToAspect(requested, frame.width, frame.height);
  assert.deepEqual(round(frameBoundsOf("settlement", expanded)), [-5, 0, 35, 40]);
  assert.equal(captureUnits("settlement"), "m");
  assert.deepEqual(captureAxes("settlement"), { x: "east", y: "north" });
});

test("interior bounds invert Y for the scene and report back down-positive", () => {
  const requested = sceneFrameBounds("interior", [1, 2, 5, 8]);
  assert.deepEqual(requested, { minX: 1, minY: -8, maxX: 5, maxY: -2 });
  const frame = { width: 100, height: 100 };
  const expanded = expandToAspect(requested, frame.width, frame.height);
  assert.deepEqual(expanded, { minX: 0, minY: -8, maxX: 6, maxY: -2 });
  const camera = viewOfBox(expanded, frame);
  assert.deepEqual(camera, { cx: 3, cy: -5, span: 6 });
  assert.deepEqual(round(frameBoundsOf("interior", boxOfView(camera, frame))), [0, 2, 6, 8]);
  assert.equal(captureUnits("interior"), "layout");
  assert.deepEqual(captureAxes("interior"), { x: "right", y: "down" });
});

test("a malformed request frame is refused instead of clamped", () => {
  assert.throws(() => sceneFrameBounds("continent", [0, 0, -1, 2]), RangeError);
  assert.throws(() => sceneFrameBounds("continent", [0, 0, 1]), TypeError);
  assert.throws(() => sceneFrameBounds("continent", [0, 0, 1, Number.NaN]), TypeError);
  assert.throws(() => captureUnits("village"), RangeError);
  assert.equal(sceneFrameBounds("interior", null), null);
});

test("full-map fitting grows monotonically until the painted surface is inside", async () => {
  // A paint whose content adds a fixed pixel padding around the geometry: the
  // scene extent it covers grows as the scale shrinks.
  const geometry = { minX: 0, minY: 0, maxX: 100, maxY: 80 };
  const seen = [];
  const paint = (bounds) => {
    seen.push(bounds);
    const pad = ((bounds.maxX - bounds.minX) / 1000) * 40;
    return {
      minX: geometry.minX - pad,
      maxX: geometry.maxX + pad,
      minY: geometry.minY - pad,
      maxY: geometry.maxY + pad,
    };
  };
  const { bounds, converged } = await convergeFit(geometry, paint);
  assert.equal(converged, true);
  for (let i = 1; i < seen.length; i += 1) {
    assert.ok(seen[i].minX <= seen[i - 1].minX && seen[i].maxX >= seen[i - 1].maxX, "growth must be monotone");
  }
  assert.ok(boxContains(bounds, paint(bounds), FIT_TOLERANCE), "the settled extent holds its own painted content");
  assert.ok(bounds.maxX > geometry.maxX, "pixel padding grew the fitted extent");
});

test("full-map fitting stays bounded when a frame cannot hold the surface", async () => {
  let paints = 0;
  const { bounds, converged, iterations } = await convergeFit(
    { minX: 0, minY: 0, maxX: 1, maxY: 1 },
    (bounds) => {
      paints += 1;
      return { minX: bounds.minX - 1, minY: bounds.minY - 1, maxX: bounds.maxX + 1, maxY: bounds.maxY + 1 };
    },
    { maxIterations: 3 },
  );
  assert.equal(converged, false);
  assert.equal(iterations, 3);
  assert.equal(paints, 3);
  assert.deepEqual(bounds, { minX: -3, minY: -3, maxX: 4, maxY: 4 });
});

test("the reference extent carries road bends, raster corners and cards", () => {
  const scene = settlement();
  const extent = sceneExtent(scene);
  // The bent road reaches y = 400 through its authored bend at (300, 0).
  assert.deepEqual(extent, { minX: 0, minY: 0, maxX: 300, maxY: 400 });

  const withRaster = continent();
  const rasterExtent = sceneExtent(withRaster);
  // The preview raster covers 50 x 50 cells, past the authored 40 km frame.
  assert.equal(rasterExtent.maxX, 50000);
  assert.equal(rasterExtent.maxY, 50000);

  const interior = interiorScene(interiorWorld().interiors[0], [], interiorWorld());
  // The exterior card sits one layout column left of its room.
  const card = sceneExtent(interior);
  assert.deepEqual(round([card.minX, card.minY, card.maxX, card.maxY]), [-1, 0, 1, 0]);
});

test("every continent layer owns its drawables and hiding it leaves the rest", () => {
  const scene = continent();
  const before = drawablesOf(scene);
  assert.ok(before.shapeLayers.includes("terrain"));
  assert.ok(before.shapeLayers.includes("water"));
  assert.ok(before.shapeLayers.includes("ridge"));
  assert.ok(before.shapeLayers.includes("partition"));
  assert.ok(before.shapeLayers.includes("footprint"));
  assert.ok(before.markLayers.includes("locations"));
  assert.equal(before.raster, "terrain");

  const expected = {
    terrain: { shapeLayers: ["water", "ridge", "partition", "partition", "footprint"], markLayers: ["locations", "locations", "ridge", "ridge"], linkKinds: [], raster: null },
    water: { shapeLayers: ["terrain", "terrain", "ridge", "partition", "partition", "footprint"], markLayers: ["locations", "locations", "ridge", "ridge"], linkKinds: [], raster: "terrain" },
    ridge: { shapeLayers: ["terrain", "water", "terrain", "partition", "partition", "footprint"], markLayers: ["locations", "locations"], linkKinds: [], raster: "terrain" },
    locations: { shapeLayers: before.shapeLayers, markLayers: ["ridge", "ridge"], linkKinds: [], raster: "terrain" },
    footprint: { shapeLayers: ["terrain", "water", "terrain", "ridge", "partition", "partition"], markLayers: before.markLayers, linkKinds: [], raster: "terrain" },
    partition: { shapeLayers: ["terrain", "water", "terrain", "ridge", "footprint"], markLayers: before.markLayers, linkKinds: [], raster: "terrain" },
  };
  for (const [layer, after] of Object.entries(expected)) {
    const hidden = captureScene(scene, "continent", [layer]);
    assert.deepEqual(drawablesOf(hidden), after, `hiding ${layer}`);
  }
});

test("hiding labels keeps geometry, cards and direction indicators", () => {
  const continentHidden = captureScene(continent(), "continent", ["labels"]);
  const continentBefore = continent();
  assert.equal(continentHidden.shapes.length, continentBefore.shapes.length);
  assert.equal(continentHidden.marks.length, continentBefore.marks.length);
  assert.ok(continentHidden.shapes.every((shape) => shape.showLabel === false));
  assert.ok(continentHidden.marks.every((mark) => mark.showLabel === false));

  const interiorBefore = interiorScene(interiorWorld().interiors[0], [], interiorWorld());
  const interiorHidden = captureScene(interiorBefore, "interior", ["labels"]);
  assert.equal(interiorHidden.marks.length, interiorBefore.marks.length);
  assert.equal(interiorHidden.links.length, interiorBefore.links.length);
  assert.equal(interiorHidden.links.filter((link) => link.curve).length, 2, "curved connections keep their chevron");

  // Geometry hiding removes its own labels with it.
  const locationsHidden = captureScene(continent(), "continent", ["locations"]);
  assert.equal(locationsHidden.marks.filter((mark) => mark.layer === "locations").length, 0);
});

test("settlement nodes and roads are independent layers", () => {
  const scene = settlement();
  assert.equal(drawablesOf(scene).markLayers.length, 2);
  assert.equal(drawablesOf(scene).linkKinds.length, 2);

  const noNodes = captureScene(scene, "settlement", ["nodes"]);
  assert.equal(noNodes.marks.length, 0);
  assert.equal(noNodes.links.length, 2, "hiding nodes never hides roads");

  const noRoads = captureScene(scene, "settlement", ["roads"]);
  assert.equal(noRoads.marks.length, 2, "hiding roads never hides nodes");
  assert.equal(noRoads.links.length, 0);

  const noLabels = captureScene(scene, "settlement", ["labels"]);
  assert.equal(noLabels.marks.length, 2);
  assert.equal(noLabels.links.length, 2);
  assert.ok(noLabels.marks.every((mark) => mark.showLabel === false));
});

test("interior rooms, connections and the exterior card are three layers", () => {
  const scene = interiorScene(interiorWorld().interiors[0], [], interiorWorld());
  assert.equal(scene.marks.length, 3, "two rooms and the exterior card");
  assert.equal(scene.links.length, 3, "two connections and the exterior link");

  const noRooms = captureScene(scene, "interior", ["rooms"]);
  assert.deepEqual(noRooms.marks.map((mark) => mark.kind), ["exterior"]);
  assert.equal(noRooms.links.length, 3, "connections survive hiding rooms");

  const noConnections = captureScene(scene, "interior", ["connections"]);
  assert.deepEqual(noConnections.links.map((link) => link.kind).sort(), ["exterior"]);
  assert.equal(noConnections.marks.length, 3);

  const noExterior = captureScene(scene, "interior", ["exterior"]);
  assert.deepEqual(noExterior.marks.map((mark) => mark.kind), ["room", "room"]);
  assert.equal(noExterior.links.filter((link) => link.kind === "exterior").length, 0);
  assert.equal(noExterior.links.length, 2);
});

test("everything hidden leaves the background at the unfiltered camera", () => {
  for (const [view, scene] of [
    ["continent", continent()],
    ["settlement", settlement()],
    ["interior", interiorScene(interiorWorld().interiors[0], [], interiorWorld())],
  ]) {
    const all = captureLayers(view);
    assert.deepEqual(all, CAPTURE_LAYERS[view]);
    const hidden = captureScene(scene, view, all);
    assert.equal(hidden.shapes.length, 0);
    assert.equal(hidden.marks.length, 0);
    assert.equal(hidden.links.length, 0);
    assert.equal(hidden.raster, null);
    assert.equal(hidden.unit, scene.unit, "the background's unit survives");
    assert.equal(sceneExtent(hidden), null, "nothing is painted to measure");
    // The camera comes from the unfiltered scene: an unfiltered extent is a
    // pure function of the projection, computed before any hiding.
    assert.equal(sceneExtent(captureScene(scene, view, [])).minX, sceneExtent(scene).minX);
  }
});

test("unknown layer names are ignored rather than guessed", () => {
  assert.deepEqual(normalizedHidden("settlement", ["terrain", "labels"]), ["labels"]);
  const scene = settlement();
  const unchanged = captureScene(scene, "settlement", ["terrain", "rooms"]);
  assert.equal(unchanged.marks.length, scene.marks.length);
  assert.equal(unchanged.links.length, scene.links.length);
  assert.equal(unionBox(null, sceneExtent(scene)).maxX, 300);
});
