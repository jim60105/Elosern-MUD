// Mechanism tests of the continent tools: editor-local references, stored
// frames and input mapping, command descriptors, the scene's authored versus
// derived drawables, the catalog and the location delete refusal. Synthetic
// projection fixtures only; no shipped copy is pinned.
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  FRAME_CELL,
  FRAME_KM,
  MAINLAND,
  cellOfMetres,
  commandFeature,
  documentCommand,
  featurePoints,
  footprintGrid,
  frameOf,
  insertionIndex,
  movePoint,
  neighbourPoint,
  nextId,
  parseContinentRef,
  pointRef,
  previewPixels,
  removalOf,
  storedFromMetres,
  waterwayRef,
} from "../src/lib/continent.js";
import { continentScene } from "../src/lib/map_scene.js";
import { visibleScene } from "../src/lib/layers.js";
import { objectCatalog } from "../src/lib/objects.js";
import { inspect } from "../src/lib/world_index.js";
import { REFERENCED, UNAVAILABLE, deletionRefusal } from "../src/lib/deletion.js";
import { ompContext } from "../src/lib/context_copy.js";

const C = "content/maps/continent.yaml";
const S = "content/maps/settlements/town.yaml";

function world() {
  return {
    continent: {
      relative_path: C,
      frame_cells: 40,
      cell_size_km: 1,
      mainland_boundary_km: [[0, 0], [40, 0], [40, 40], [0, 40]],
      forest_edge: [[0, 30], [39, 30]],
      forest_edge_m: [[500, 30500], [39500, 30500]],
      waterways: [
        { id: "river", route: [[20, 20], [0, 20]], route_m: [[20500, 20500], [500, 20500]], fords: [[10, 20]], fords_m: [[10500, 20500]] },
      ],
      border_river_key: "river",
      harbor_sites: [{ id: "port", display_name: "Port", cell: [2, 3], centre_m: [2500, 3500], role: "Trade" }],
      regions: [{ id: "eastern_plains", display_name_zh: "東", nation_key: null, terrain_flavor_zh: ["a", "b"], nominal_nation_keys: [], scene_archetype: null }],
      ridge: { base_x: 10, passes: [{ y_min: 4, y_max: 5 }] },
      coastal_y_max: 10,
      terrain_preview: {
        status: "current",
        step: 20,
        columns: 2,
        rows: 2,
        regions: ["a", "b"],
        surfaces: ["sea", "land", "water", "ridge"],
        samples: [1, 2, 3, 4],
        ridge_walls: [[[10, 0], [10, 3]]],
        passes: [{ index: 0, y_min: 4, y_max: 5, centre: [10, 4] }],
        national_borders: [{ nation_keys: ["a", "b"], points: [[10, 0], [10, 20]] }],
        borders_reason: null,
      },
    },
    locations: [
      { id: "place", qualified_ref: "location:place", relative_path: "content/maps/locations.yaml", display_name_zh: "城", cell: [5, 5], centre_m: [5500, 5500], local_maps: ["town"], kind: "capital" },
      { id: "wilds", qualified_ref: "location:wilds", relative_path: "content/maps/locations.yaml", display_name_zh: "荒野", cell: [30, 12], centre_m: [30500, 12500], local_maps: [], kind: "dungeon" },
    ],
    districts: [{ id: "d1", relative_path: "content/maps/districts.yaml", district_name_zh: "一區", kind: "voronoi", region_key: null, landmark: { domain: "location", map_id: null, object_id: "wilds", cell: null } }],
    settlements: [
      {
        id: "town",
        relative_path: S,
        location_ref: "place",
        binding: { anchor_cell: [5, 5], local_anchor_m: [0, 0] },
        footprint: { shape: ["#."], origin: [5, 5], cells: [[5, 5]] },
        nodes: [{ id: "gate", qualified_ref: "settlement_node:town:gate", key: "Gate", anchor_key: "place", local_m: [0, 0], world_m: [5500, 5500] }],
        roads: [],
        interiors: [],
      },
    ],
    interiors: [],
  };
}

test("references parse into feature, point and declaration kinds", () => {
  assert.deepEqual(parseContinentRef("continent:waterway:river#2"), { kind: "waterway", id: "river", index: 2, feature: "continent:waterway:river" });
  assert.deepEqual(parseContinentRef(MAINLAND), { kind: "mainland", id: null, index: null, feature: MAINLAND });
  assert.equal(parseContinentRef("continent:pass#1").index, 1);
  assert.equal(parseContinentRef("footprint:town").kind, "footprint");
  assert.equal(parseContinentRef("location:place"), null);
  assert.equal(parseContinentRef("continent:waterway:Bad-Id"), null);
  assert.deepEqual(commandFeature("continent:ford:river#0"), { kind: "waterway_ford", waterway_id: "river" });
  assert.deepEqual(commandFeature("continent:forest_edge#1"), { kind: "forest_edge" });
});

test("mainland vertices are kilometres and every other point is a cell index", () => {
  const w = world();
  assert.equal(frameOf("continent:mainland#0"), FRAME_KM);
  assert.equal(frameOf("continent:waterway:river#0"), FRAME_CELL);
  assert.deepEqual(storedFromMetres(w, "continent:mainland#1", { x: 38_400, y: 1_600 }), [38, 2]);
  assert.deepEqual(storedFromMetres(w, "continent:waterway:river#0", { x: 20_999, y: 25_000 }), [20, 25]);
  assert.deepEqual(cellOfMetres(w, { x: 0, y: 999 }), [0, 0]);
  const points = featurePoints(w, waterwayRef("river"));
  assert.deepEqual(points.map((p) => p.stored), [[20, 20], [0, 20]]);
  assert.deepEqual(points[0].m, { x: 20500, y: 20500 });
});

test("the insertion index follows the nearest segment, extends ends and closes rings", () => {
  const line = [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 20, y: 0 }];
  assert.equal(insertionIndex(line, { x: 15, y: 1 }), 2);
  assert.equal(insertionIndex(line, { x: -5, y: 0 }), 0);
  assert.equal(insertionIndex(line, { x: 30, y: 0 }), 3);
  const ring = [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }, { x: 0, y: 10 }];
  assert.equal(insertionIndex(ring, { x: -1, y: 5 }, { closed: true }), 4);
  assert.deepEqual(neighbourPoint([{ stored: [0, 0] }, { stored: [10, 4] }], 1, true), [5, 2]);
  assert.deepEqual(neighbourPoint([{ stored: [0, 0] }], 0, false), [1, 0]);
  assert.equal(nextId("location", ["location_1", "location_3"]), "location_2");
});

test("descriptors name one document and take the fingerprint at send time", () => {
  const descriptor = movePoint("continent:waterway:river#1", [3, 4]);
  assert.deepEqual(descriptor, {
    name: "move_control_point",
    documentId: C,
    arguments: { feature: { kind: "waterway_route", waterway_id: "river" }, index: 1, point: [3, 4] },
  });
  const workspace = { documents: [{ relative_path: C, fingerprint: "f".repeat(64) }] };
  assert.equal(documentCommand(workspace, descriptor).expected, "f".repeat(64));
  assert.equal(documentCommand({ documents: [] }, descriptor).expected, "absent");
  assert.equal(removalOf(world(), "continent:pass#0").name, "remove_ridge_pass");
  assert.equal(removalOf(world(), "continent:waterway:river").name, "remove_waterway");
  assert.equal(removalOf(world(), MAINLAND), null);
  assert.equal(removalOf(world(), "continent:region:eastern_plains"), null);
});

test("handles appear only for the selected feature; derived output has none", () => {
  const w = world();
  const plain = continentScene(w);
  assert.equal(plain.marks.filter((mark) => mark.kind === "handle").length, 0);
  const selected = continentScene(w, ["continent:waterway:river#1"]);
  const handles = selected.marks.filter((mark) => mark.kind === "handle");
  assert.deepEqual(handles.map((mark) => mark.id), [pointRef(waterwayRef("river"), 0), pointRef(waterwayRef("river"), 1)]);
  assert.ok(handles.every((mark) => mark.draggable && mark.layer === "water"));
  const borders = selected.shapes.filter((shape) => shape.role === "border");
  assert.equal(borders.length, 1);
  assert.ok(borders.every((shape) => !shape.selectable && shape.ref === null && shape.layer === "partition"));
  assert.ok(selected.marks.every((mark) => mark.layer !== "partition"));
  assert.equal(selected.raster.layer, "terrain");
  assert.equal(selected.marks.find((mark) => mark.kind === "pass").draggable, false);
  const hidden = visibleScene(selected, ["terrain", "partition"]);
  assert.equal(hidden.raster, null);
  assert.ok(hidden.shapes.every((shape) => shape.layer !== "partition"));
  assert.ok(hidden.items.every((item) => item.layer !== "terrain"));
});

test("an unavailable preview draws no derived terrain", () => {
  const w = world();
  w.continent.terrain_preview = { status: "unavailable", reason: "x" };
  const scene = continentScene(w);
  assert.equal(scene.raster, null);
  assert.ok(scene.shapes.every((shape) => shape.role !== "ridge" && shape.role !== "border"));
});

test("the preview raster is north row first in image order", () => {
  const pixels = previewPixels(world().continent.terrain_preview);
  // Sample 0 (south-west, land) lands on the image's bottom-left pixel.
  assert.equal(pixels.length, 16);
  assert.equal(pixels[2 * 4 + 3] > 0, true);
  // Sample 1 (south-east) is water.
  assert.deepEqual([...pixels.slice(3 * 4, 3 * 4 + 4)], [60, 96, 120, 200]);
});

test("the catalog keeps continental refs with owner, layer and frame", () => {
  const catalog = objectCatalog(world());
  const point = catalog.get("continent:mainland#2");
  assert.equal(point.relativePath, C);
  assert.match(point.frame, /km 地理/);
  assert.equal(catalog.get("district:d1").relativePath, "content/maps/districts.yaml");
  assert.equal(catalog.get("footprint:town").relativePath, S);
  assert.equal(catalog.get("continent:ford:river#0").layer, "ridge");
  const text = ompContext({ workspace: { world: world(), preview_state: "current" }, catalog, refs: ["continent:waterway:river#0"] });
  assert.match(text, /1 km 格/);
  assert.match(text, /continent:waterway:river#0/);
});

test("records exist only for points that still exist", () => {
  const w = world();
  assert.equal(inspect(w, "continent:waterway:river#1").title.includes("2"), true);
  assert.equal(inspect(w, "continent:waterway:river#5"), null);
  assert.equal(inspect(w, "continent:waterway:river#1").owner, "continent:waterway:river");
  assert.equal(inspect(w, "footprint:town").relativePath, S);
});

test("a location's map-internal references refuse its deletion", () => {
  const summary = { crossDocument: false };
  const current = { current: true };
  const internal = [{ kind: "本地圖", label: "town", external: false }];
  const refused = deletionRefusal({ externalStatus: current, summary, relations: internal, internalBlocks: true });
  assert.equal(refused.key, REFERENCED);
  assert.equal(refused.count, 1);
  const free = deletionRefusal({ externalStatus: current, summary, relations: [], internalBlocks: true });
  assert.equal(free.key, UNAVAILABLE);
  // Without internalBlocks (rooms, nodes) internal rows only accompany.
  assert.equal(deletionRefusal({ externalStatus: current, summary, relations: internal }).key, UNAVAILABLE);
});

test("the footprint grid has a one-cell margin, north row first", () => {
  const grid = footprintGrid({ shape: ["#.", "##"], origin: [10, 10], cells: [[10, 10], [10, 11], [11, 11]] });
  assert.deepEqual([grid.west, grid.east, grid.south, grid.north], [9, 12, 9, 12]);
  assert.equal(grid.rows[0].y, 12);
  assert.equal(grid.rows.at(-1).y, 9);
  const row11 = grid.rows.find((row) => row.y === 11);
  assert.deepEqual(row11.cells.filter((cell) => cell.filled).map((cell) => cell.x), [10, 11]);
});
