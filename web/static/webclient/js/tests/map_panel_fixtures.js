/*
 * Synthetic schema-valid area_map / world_map fixtures and a part encoder for
 * the map panel protocol tests (define-map-panel-protocol).
 *
 * Not a test file: the Node gate collects `tests/*.test.js` only. Every
 * identity is invented (t_-keyed); the geometry is small but real (closed,
 * oriented rings), never prototype data.
 */

"use strict";

const Protocol = require("../elosern/protocol.js");
const core = require("../elosern/protocol/core.js");

const MAP = "t_map";

function gridNode(x, y, overrides) {
  return Object.assign(
    {
      id: `grid:${MAP}:${x}:${y}`,
      label: `合成街角${x}-${y}`,
      x: x * 10,
      y: y * 10,
      visibility: "seen",
      gateway: null,
      action: null,
    },
    overrides || {}
  );
}

function gridArea(overrides) {
  return Object.assign(
    {
      schema_version: 2,
      available: true,
      layer: "grid",
      map_id: MAP,
      frame: { key: MAP, unit: "m" },
      current_node: `grid:${MAP}:1:1`,
      title: "合成城鎮",
      nodes: [
        gridNode(1, 1, { visibility: "current" }),
        gridNode(1, 2, {
          visibility: "visited",
          action: { kind: "move", exit_ref: "n", destination: `grid:${MAP}:1:2` },
        }),
        gridNode(2, 1, { gateway: { leads_to: "合成荒野" } }),
      ],
      edges: [
        { source: `grid:${MAP}:1:1`, destination: `grid:${MAP}:1:2` },
        { source: `grid:${MAP}:1:1`, destination: `grid:${MAP}:2:1` },
      ],
      quest_markers: [
        {
          id: "t_errand:1",
          title: "合成委託",
          tracked: true,
          destination: { kind: "node", node_id: `grid:${MAP}:1:2` },
        },
        {
          id: "t_errand:2",
          title: "遠方委託",
          tracked: false,
          destination: { kind: "bearing", bearing_deg: 45.5, distance_km: 12.25 },
        },
      ],
    },
    overrides || {}
  );
}

function interiorArea(overrides) {
  return Object.assign(
    {
      schema_version: 2,
      available: true,
      layer: "interior",
      map_id: "room:40",
      frame: { key: "room:40", unit: "none" },
      current_node: "room:41",
      title: "合成館內",
      nodes: [
        { id: "room:41", label: "大廳", visibility: "current", gateway: null, action: null },
        { id: "room:42", label: "迴廊", visibility: "seen", gateway: null, action: null },
      ],
      edges: [{ source: "room:41", destination: "room:42" }],
      quest_markers: [],
    },
    overrides || {}
  );
}

// A schema-2 wilderness window (41 x 41, wilderness-area-map-reveal) around
// cell (120, 120): a revealed disc of radius 6 drawn as merged terrain runs
// (a west ridge, a river with a ford, woodland in the north), unknown runs
// everywhere else, a short visited trail with one node per visit, the eight
// actionable neighbours, two hostile entities inside the radius-4 ground
// sight and one distant sighting. Its encoded body exceeds one part.
const WILD_C = 120;
const WILD_MIN = WILD_C - 20;
function wildTerrainAt(x, y) {
  const dx = x - WILD_C;
  const dy = y - WILD_C;
  if (dx * dx + dy * dy > 6.5 * 6.5) return null;
  if (dx === -5) return { terrain: "ridge", passable: false, band: 9, tier: 2, road: false, ford: false };
  if (dx === 3) return dy === 0
    ? { terrain: "open_ground", passable: true, band: 2, tier: 0, road: false, ford: true }
    : { terrain: "water", passable: false, band: 1, tier: 0, road: false, ford: false };
  if (dy >= 3) return { terrain: "woodland", passable: true, band: 4, tier: 0, road: false, ford: false };
  return { terrain: "open_ground", passable: true, band: 3 + (dx > 0 ? 1 : 0), tier: 0, road: false, ford: false };
}
function wildRowsFor(terrainAt) {
  const rows = [];
  for (let row = 0; row < 41; row++) {
    const runs = [];
    for (let col = 0; col < 41; col++) {
      const facts = terrainAt(WILD_MIN + col, WILD_MIN + row);
      const run = facts ? Object.assign({ length: 1, kind: "terrain" }, facts) : { length: 1, kind: "unknown" };
      const last = runs[runs.length - 1];
      const same = last && JSON.stringify(Object.assign({}, last, { length: 0 })) === JSON.stringify(Object.assign({}, run, { length: 0 }));
      if (same) last.length += 1;
      else runs.push(run);
    }
    rows.push(runs);
  }
  return rows;
}
function wildNode(x, y, overrides) {
  return Object.assign(
    {
      id: `wild:elosern:${x}:${y}`,
      label: "合成曠野",
      x: x + 0.5,
      y: y + 0.5,
      visibility: "seen",
      visited: false,
      gateway: null,
      action: null,
    },
    overrides || {}
  );
}
function wildernessArea(overrides) {
  const current = `wild:elosern:${WILD_C}:${WILD_C}`;
  const nodes = [wildNode(WILD_C, WILD_C, { label: "合成曠野中心", visibility: "current", visited: true })];
  for (const [x, y] of [[119, 119], [118, 118], [117, 118], [116, 117]]) {
    nodes.push(wildNode(x, y, { visibility: "visited", visited: true }));
  }
  const edges = [];
  for (const [dx, dy, ref] of [[0, 1, "n"], [1, 1, "ne"], [1, 0, "e"], [1, -1, "se"], [0, -1, "s"], [-1, 0, "w"], [-1, 1, "nw"]]) {
    const id = `wild:elosern:${WILD_C + dx}:${WILD_C + dy}`;
    nodes.push(wildNode(WILD_C + dx, WILD_C + dy, { action: { kind: "move", exit_ref: ref, destination: id } }));
    edges.push({ source: current, destination: id });
  }
  const sw = nodes.find((node) => node.id === "wild:elosern:119:119");
  sw.action = { kind: "move", exit_ref: "sw", destination: sw.id };
  edges.push({ source: current, destination: sw.id });
  return Object.assign(
    {
      schema_version: 2,
      available: true,
      layer: "wilderness",
      map_id: "elosern",
      frame: { key: "elosern", unit: "km" },
      current_node: current,
      title: "合成曠野",
      nodes,
      edges,
      quest_markers: [],
      district_name: "合成地區",
      cell_km: 1,
      window: { min_x: WILD_MIN, min_y: WILD_MIN, width: 41, height: 41 },
      rows: wildRowsFor(wildTerrainAt),
      light_phase: "day",
      ground_radius: 4,
      entities: [
        { id: "0123456789abcdef", cell: { x: 122, y: 121 }, kind: "hostile", hostile: true, label: "合成野狼" },
        { id: "fedcba9876543210", cell: { x: 118, y: 122 }, kind: "npc", hostile: false, label: "合成旅人" },
      ],
      sightings: [{ bearing: "北北東", distance_km: 25, silhouette_zh: "一座合成石塔", name: null }],
    },
    overrides || {}
  );
}

function square(x, y, size) {
  // Counter-clockwise with north-positive y.
  return [[x, y], [x + size, y], [x + size, y + size], [x, y + size], [x, y]];
}

function hole(x, y, size) {
  return square(x, y, size).reverse();
}

function worldMap(overrides) {
  return Object.assign(
    {
      schema_version: 1,
      available: true,
      common: {
        coastline: square(0, 0, 1000),
        borders: [[[500, 0], [500, 1000]]],
        nations: [
          { id: "t_west", name: "西合成國", x: 250, y: 500 },
          { id: "t_east", name: "東合成國", x: 750, y: 500 },
        ],
      },
      districts: [
        { id: "t_dark", lit: false, outline: [square(0, 0, 100)] },
        {
          id: "t_lit",
          lit: true,
          name: "明合成區",
          outline: [square(100, 100, 200), hole(150, 150, 20)],
          landmark: { name: "合成塔", x: 200, y: 200 },
          nations: ["t_west"],
          terrain: [{ region: "t_meadow", polygons: [square(120, 120, 50)] }],
          rivers: [[[100, 100], [300, 300]]],
          ridge: [],
          roads: [[[110, 110], [120.5, 130.25]]],
          places: [{ id: "t_town", name: "合成鎮", kind: "settlement", x: 180, y: 220 }],
        },
      ],
      trail: { resolution_km: 1, rows: [[3, [[0, 2], [5, 1]]], [4, [[1, 3]]]] },
      visited_places: [{ id: "t_grove", name: "隱密林地", kind: "hidden", x: 10, y: 20 }],
      current: { x: 101.5, y: 102.5 },
      quest_markers: [
        { id: "t_errand:3", title: "精確委託", tracked: true, x: 180.5, y: 220.25, approximate: false },
        { id: "t_errand:4", title: "概略委託", tracked: false, x: 650, y: 100, approximate: true },
      ],
    },
    overrides || {}
  );
}

// A counter-clockwise ring of `points` vertices (closed) around (cx, cy).
function ring(cx, cy, radius, points) {
  const out = [];
  for (let index = 0; index < points; index++) {
    const angle = (2 * Math.PI * index) / points;
    out.push([
      Math.round((cx + radius * Math.cos(angle)) * 10) / 10,
      Math.round((cy + radius * Math.sin(angle)) * 10) / 10,
    ]);
  }
  out.push(out[0].slice());
  return out;
}

// A synthetic schema-valid world_map of at least `minBytes` canonical bytes
// (transport-world-map-panel): the small fixture plus unlit districts whose
// dense synthetic outlines push the body past one generic 64 KB frame. The
// result is deterministic for a given `minBytes`.
function largeWorldMap(minBytes, overrides) {
  const body = worldMap();
  // Each pushed district adds its own canonical size plus one comma.
  for (let index = 0, bytes = core.jsonByteSize(body); bytes < minBytes; index++) {
    const district = {
      id: "t_far_" + index,
      lit: false,
      outline: [ring(500 + (index % 8) * 60, 500 + Math.floor(index / 8) * 60, 25, 600)],
    };
    body.districts.push(district);
    bytes += core.jsonByteSize(district) + 1;
  }
  return Object.assign(body, overrides || {});
}

// A synthetic world_map of exactly `target` canonical bytes: a large map
// below the target, then visited places whose ASCII names close the gap.
function worldMapOfBytes(target) {
  const body = largeWorldMap(target - 20000);
  const place = (index, length) => ({
    id: "t_pad_" + index, name: "p".repeat(length), kind: "hidden", x: 1, y: 2,
  });
  // A row of name length L adds overhead + L bytes (its comma included).
  for (let index = 0; ; index++) {
    const gap = target - core.jsonByteSize(body);
    const overhead = core.jsonByteSize(place(index, 1));
    if (gap - overhead <= 256) {
      body.visited_places.push(place(index, gap - overhead));
      break;
    }
    // Leave room for one more complete row after this one.
    body.visited_places.push(place(index, Math.min(256, gap - 2 * overhead - 8)));
  }
  if (core.jsonByteSize(body) !== target) {
    throw new Error("worldMapOfBytes missed its target");
  }
  return body;
}

// Split a logical body into exact part wire values (mirror of the Python
// encoder: canonical JSON, fixed 1536-byte slices, padded base64).
function encodeParts(body, transferId) {
  const raw = Buffer.from(core.canonicalJson(body), "utf8");
  const size = Protocol.MAP_PART_RAW_BYTES;
  const count = Math.ceil(raw.length / size);
  const parts = [];
  for (let index = 0; index < count; index++) {
    parts.push({
      schema_version: 1,
      available: true,
      part: {
        transfer_id: transferId,
        index,
        count,
        byte_length: raw.length,
        chunk: raw.subarray(index * size, (index + 1) * size).toString("base64"),
      },
    });
  }
  return parts;
}

module.exports = {
  MAP,
  gridNode,
  gridArea,
  interiorArea,
  wildernessArea,
  wildNode,
  wildRowsFor,
  WILD_C,
  WILD_MIN,
  worldMap,
  largeWorldMap,
  worldMapOfBytes,
  ring,
  square,
  hole,
  encodeParts,
};
