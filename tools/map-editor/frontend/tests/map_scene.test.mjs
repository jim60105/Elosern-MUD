import { test } from "node:test";
import assert from "node:assert/strict";

import { interiorPositions, sceneFor, settlementScene } from "../src/lib/map_scene.js";
import { priorityBanner } from "../src/lib/status.js";
import { inspect } from "../src/lib/world_index.js";
import { DISCONNECTED, CONNECTED } from "../src/lib/workspace_client.js";

const settlement = {
  id: "m",
  relative_path: "content/maps/settlements/m.yaml",
  city_gate: { node: "a" },
  wilderness_entry: null,
  nodes: [
    { id: "a", qualified_ref: "settlement_node:m:a", key: "A", desc: "<b>x</b>", local_m: [0, 0], world_m: [10, 10], prototype_parent: "p", scene_archetype: null },
    { id: "b", qualified_ref: "settlement_node:m:b", key: "B", desc: "", local_m: [30, 40], world_m: [40, 50], prototype_parent: "p", scene_archetype: null },
  ],
  roads: [
    { id: "a>b", source: "a", destination: "b", direction: "ne", bends: [[30, 0]], length_m: 70 },
  ],
};

test("roads follow their authored bends and mark one-way travel", () => {
  const scene = settlementScene(settlement);
  assert.deepEqual(scene.links[0].points, [{ x: 0, y: 0 }, { x: 30, y: 0 }, { x: 30, y: 40 }]);
  assert.equal(scene.links[0].twoWay, false);
  assert.equal(scene.marks.find((mark) => mark.id === "settlement_node:m:a").gateway, true);
  assert.deepEqual(scene.bounds, { minX: 0, minY: 0, maxX: 30, maxY: 40 });
});

test("interior rooms use layout positions or list order, never a metric unit", () => {
  const interior = {
    id: "i",
    rooms: [
      { id: "r1", layout_position: null },
      { id: "r2", layout_position: [5, 2] },
      { id: "r3", layout_position: null },
      { id: "r4", layout_position: null },
    ],
    connections: [],
  };
  const positions = interiorPositions(interior);
  assert.deepEqual(positions.get("r2"), { x: 5, y: -2 });
  assert.deepEqual(positions.get("r4"), { x: 0, y: -1 });
  assert.equal(sceneFor({ interiors: [{ ...interior, rooms: interior.rooms.map((r) => ({ ...r, qualified_ref: r.id })) }] }, "interior", "i").unit, null);
});

test("inspection keeps authored prose as plain text", () => {
  const world = { locations: [], settlements: [settlement], interiors: [] };
  const record = inspect(world, "settlement_node:m:a");
  assert.equal(record.relativePath, settlement.relative_path);
  assert.equal(record.fields.find((field) => field.label === "描述").value, "<b>x</b>");
  assert.equal(inspect(world, "settlement_node:m:missing"), null);
});

test("the banner shows the single highest-priority condition", () => {
  const stale = { preview_state: "stale", snapshot_read_at: null, candidate_diagnostics: [{ relative_path: "a.yaml", line: 3, message: "bad" }] };
  assert.equal(priorityBanner(stale, DISCONNECTED).key, "disconnected");
  const banner = priorityBanner(stale, CONNECTED);
  assert.equal(banner.key, "stale");
  assert.match(banner.text, /a\.yaml:3/);
  assert.equal(priorityBanner({ preview_state: "unavailable", candidate_diagnostics: [] }, CONNECTED).key, "unavailable");
  assert.equal(priorityBanner({ preview_state: "current" }, CONNECTED), null);
});
