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
      schema_version: 1,
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
      schema_version: 1,
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

// A full 15 x 15 wilderness window (225 nodes, 8-neighbour edges): its edge
// list exceeds the 320-item frame ceiling, so it always travels in parts.
function wildernessArea(overrides) {
  const nodes = [];
  const edges = [];
  const origin = 100;
  for (let dy = 0; dy < 15; dy++) {
    for (let dx = 0; dx < 15; dx++) {
      const current = dx === 7 && dy === 7;
      nodes.push({
        id: `wild:elosern:${origin + dx}:${origin + dy}`,
        label: current ? "合成曠野中心" : `曠野${dx}-${dy}`,
        x: origin + dx + 0.5,
        y: origin + dy + 0.5,
        visibility: current ? "current" : dx % 3 === 0 ? "visited" : "seen",
        visited: current || dx % 3 === 0,
        gateway: null,
        action: null,
      });
      if (dx > 0) edges.push({ source: `wild:elosern:${origin + dx - 1}:${origin + dy}`, destination: `wild:elosern:${origin + dx}:${origin + dy}` });
      if (dy > 0) edges.push({ source: `wild:elosern:${origin + dx}:${origin + dy - 1}`, destination: `wild:elosern:${origin + dx}:${origin + dy}` });
    }
  }
  return Object.assign(
    {
      schema_version: 1,
      available: true,
      layer: "wilderness",
      map_id: "elosern",
      frame: { key: "elosern", unit: "km" },
      current_node: `wild:elosern:${origin + 7}:${origin + 7}`,
      title: "合成曠野",
      nodes,
      edges,
      quest_markers: [],
      district_name: "合成地區",
      cell_km: 1,
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
  worldMap,
  largeWorldMap,
  worldMapOfBytes,
  ring,
  square,
  hole,
  encodeParts,
};
