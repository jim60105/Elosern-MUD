// Mechanism tests of the settlement tools: editor-local road and bend
// references, schema-driven node controls, command descriptors, group moves
// with one integer delta, the scene's selectable roads and bend handles, the
// catalog, delete blockers and the node delete refusal. Synthetic projection
// fixtures only; no shipped copy is pinned.
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  bendInsertion,
  bendRef,
  createRoad,
  groupMoves,
  mixedValue,
  nodeBlockers,
  nodeFieldSpecs,
  oneDocumentNodes,
  parseSettlementRef,
  prototypeFields,
  roadRef,
  roundPoint,
  settlementRemoval,
} from "../src/lib/settlement.js";
import { settlementScene } from "../src/lib/map_scene.js";
import { objectCatalog } from "../src/lib/objects.js";
import { inspect } from "../src/lib/world_index.js";
import { selectionSummary } from "../src/lib/selection_owner.js";
import { REFERENCED, deletionRefusal } from "../src/lib/deletion.js";
import { ompContext } from "../src/lib/context_copy.js";

const S = "content/maps/settlements/town.yaml";

function node(id, x, y, extra = {}) {
  return {
    id,
    qualified_ref: `settlement_node:town:${id}`,
    key: id.toUpperCase(),
    desc: "",
    prototype_parent: "grid_room",
    anchor_key: null,
    typeclass: null,
    scene_archetype: null,
    scene_status: "none",
    local_m: [x, y],
    world_m: [x, y],
    ...extra,
  };
}

function world() {
  return {
    locations: [{ id: "place", qualified_ref: "location:place", display_name_zh: "Place", relative_path: "content/maps/locations.yaml", local_maps: ["town"], cell: [1, 1], centre_m: [1500, 1500] }],
    continent: null,
    districts: [
      { id: "d", relative_path: "content/maps/districts.yaml", district_name_zh: "D", landmark: { domain: "settlement_node", map_id: "town", object_id: "c" } },
    ],
    settlements: [
      {
        id: "town",
        relative_path: S,
        location_ref: "place",
        city_gate: { node: "a" },
        wilderness_entry: { gates: [{ return_direction: "n", destination_node: "a" }] },
        nodes: [node("a", 0, 0), node("b", 300, 400), node("c", 300, 0), node("lone", 900, 900)],
        roads: [
          { id: "a>b", source: "a", destination: "b", direction: "n", bends: [], length_m: 500 },
          { id: "b>a", source: "b", destination: "a", direction: "s", bends: [[300, 0]], length_m: 700 },
        ],
      },
      { id: "other", relative_path: "content/maps/settlements/other.yaml", location_ref: "place", city_gate: null, wilderness_entry: null, nodes: [node("x", 0, 0, { qualified_ref: "settlement_node:other:x" })], roads: [] },
    ],
    interiors: [
      { id: "hall", relative_path: "content/maps/interiors/hall.yaml", rooms: [], connections: [], exterior: { settlement: "town", node: "b", room: "front" } },
    ],
  };
}

const SCHEMA = {
  document_kinds: {
    settlement: {
      fields: {
        nodes: {
          items: {
            fields: {
              x_m: { type: "int" },
              y_m: { type: "int" },
              prototype_parent: { type: "enum", values: ["grid_room", "anchor_room"] },
              key: { type: "str", min_length: 1 },
              desc: { type: "str" },
              anchor_key: { type: "str", nullable: true },
              typeclass: { type: "str", nullable: true },
              scene_archetype: { type: "str", nullable: true },
            },
          },
        },
      },
    },
  },
};

test("road and bend references parse back to their ordered identity", () => {
  const road = roadRef("town", "a", "b");
  assert.deepEqual(parseSettlementRef(road), { kind: "road", settlementId: "town", source: "a", destination: "b", road });
  assert.deepEqual(parseSettlementRef(bendRef(road, 2)), { kind: "bend", settlementId: "town", source: "a", destination: "b", road, index: 2 });
  assert.deepEqual(parseSettlementRef("settlement_node:town:a"), { kind: "node", settlementId: "town", nodeId: "a" });
  assert.equal(parseSettlementRef("road:town:a"), null);
  assert.equal(parseSettlementRef("road:Town:a>b"), null);
});

test("node controls are typed from the core schema, without the position", () => {
  const specs = nodeFieldSpecs(SCHEMA);
  const byKey = Object.fromEntries(specs.map((spec) => [spec.key, spec]));
  assert.equal(byKey.x_m, undefined);
  assert.equal(byKey.prototype_parent.type, "select");
  assert.deepEqual(byKey.prototype_parent.options.map((option) => option.value), ["grid_room", "anchor_room"]);
  assert.equal(byKey.typeclass.type, "nullable");
  assert.equal(byKey.desc.type, "textarea");
  assert.equal(byKey.key.type, "text");
  assert.equal(byKey.anchor_key.reference, "location");
  assert.equal(byKey.scene_archetype.reference, "scene");
  // A field the schema adds is offered without a frontend change.
  const extended = structuredClone(SCHEMA);
  extended.document_kinds.settlement.fields.nodes.items.fields.weather = { type: "enum", values: ["dry"] };
  assert.equal(nodeFieldSpecs(extended).find((spec) => spec.key === "weather").type, "select");
  assert.deepEqual(nodeFieldSpecs(null), []);
});

test("a prototype switch carries the anchor rule pair", () => {
  assert.deepEqual(prototypeFields("anchor_room", "place"), { prototype_parent: "anchor_room", anchor_key: "place" });
  assert.deepEqual(prototypeFields("grid_room", "place"), { prototype_parent: "grid_room", anchor_key: null });
});

test("a bidirectional road is one command naming both authored directions", () => {
  const command = createRoad("town", "a", "c", "e", [], { direction: "w", bends: [] });
  assert.equal(command.name, "create_road");
  assert.equal(command.documentId, S);
  assert.deepEqual(command.arguments, { settlement_id: "town", source: "a", destination: "c", direction: "e", bends: [], return: { direction: "w", bends: [] } });
});

test("a group moves by one integer delta, never by per-node rounding", () => {
  const settlement = world().settlements[0];
  assert.deepEqual(groupMoves(settlement, ["a", "c"], 10.6, -3.4), [
    { node_id: "a", x_m: 11, y_m: -3 },
    { node_id: "c", x_m: 311, y_m: -3 },
  ]);
  assert.deepEqual(roundPoint({ x: -0.4, y: 2.5 }), [0, 3]);
});

test("only nodes of one settlement document form a mutable group", () => {
  assert.deepEqual(oneDocumentNodes(["settlement_node:town:a", "settlement_node:town:c"]), { settlementId: "town", nodeIds: ["a", "c"] });
  assert.equal(oneDocumentNodes(["settlement_node:town:a", "settlement_node:other:x"]), null);
  assert.equal(oneDocumentNodes(["settlement_node:town:a", roadRef("town", "a", "b")]), null);
  const summary = selectionSummary(objectCatalog(world()), ["settlement_node:town:a", "settlement_node:other:x"]);
  assert.equal(summary.crossDocument, true);
  assert.ok(summary.reason);
});

test("mixed values show a dash and shared values the value", () => {
  const nodes = world().settlements[0].nodes;
  assert.equal(mixedValue(nodes.slice(0, 2), (row) => row.prototype_parent), "grid_room");
  assert.equal(mixedValue(nodes.slice(0, 2), (row) => row.local_m[0]), "—");
});

test("bends are inserted halfway along the neighbouring segment", () => {
  const settlement = world().settlements[0];
  const back = settlement.roads[1];
  assert.deepEqual(bendInsertion(settlement, back, 0, true), { index: 0, point: [300, 200] });
  assert.deepEqual(bendInsertion(settlement, back, 0, false), { index: 1, point: [150, 0] });
  assert.deepEqual(bendInsertion(settlement, settlement.roads[0], null, false), { index: 0, point: [150, 200] });
});

test("the selected road shows its bend handles and chevrons; nodes are draggable", () => {
  const settlement = world().settlements[0];
  const road = roadRef("town", "b", "a");
  const plain = settlementScene(settlement);
  assert.equal(plain.marks.filter((mark) => mark.kind === "handle").length, 0);
  assert.ok(plain.marks.filter((mark) => mark.kind === "node").every((mark) => mark.draggable));
  assert.deepEqual(plain.links.map((link) => link.ref), [roadRef("town", "a", "b"), road]);
  const chosen = settlementScene(settlement, [road]);
  const handles = chosen.marks.filter((mark) => mark.kind === "handle");
  assert.deepEqual(handles.map((mark) => [mark.id, mark.x, mark.y]), [[bendRef(road, 0), 300, 0]]);
  assert.deepEqual(chosen.links.map((link) => link.selected), [false, true]);
  // Selecting a bend keeps its road's handles.
  assert.equal(settlementScene(settlement, [bendRef(road, 0)]).marks.filter((mark) => mark.kind === "handle").length, 1);
  // The object list holds nodes then roads.
  assert.deepEqual(chosen.items.map((item) => item.id).slice(-2), [roadRef("town", "a", "b"), road]);
});

test("an empty new map draws nothing and fabricates nothing", () => {
  const empty = { id: "camp", relative_path: "content/maps/settlements/camp.yaml", city_gate: null, wilderness_entry: null, nodes: [], roads: [] };
  const scene = settlementScene(empty);
  assert.deepEqual([scene.marks, scene.links, scene.items], [[], [], []]);
  assert.ok(Number.isFinite(scene.bounds.minX));
});

test("roads and bends are catalogued under their settlement document", () => {
  const catalog = objectCatalog(world());
  const road = roadRef("town", "b", "a");
  assert.equal(catalog.get(road).relativePath, S);
  assert.equal(catalog.get(bendRef(road, 0)).mapId, "town");
  assert.equal(inspect(world(), road).relativePath, S);
  assert.equal(inspect(world(), bendRef(road, 3)), null);
  const text = ompContext({ workspace: { world: world(), preview_state: "current" }, catalog, refs: [bendRef(road, 0)] });
  assert.match(text, /300/);
  assert.match(text, new RegExp(S.replace(/\./g, "\\.")));
});

test("a node with map references lists every blocker and refuses deletion", () => {
  const data = world();
  const rows = (refs) => nodeBlockers(data, refs);
  // a: both roads (linked), the wilderness gate and the city gate (no link).
  const forA = rows(["settlement_node:town:a"]);
  assert.equal(forA.length, 4);
  assert.deepEqual(forA.filter((row) => row.ref).map((row) => row.ref), [roadRef("town", "a", "b"), roadRef("town", "b", "a")]);
  assert.ok(forA.every((row) => row.source === S && row.external === false));
  // b: two roads and the interior exterior, declared by the interior.
  const forB = rows(["settlement_node:town:b"]);
  assert.equal(forB.length, 3);
  assert.deepEqual(forB.filter((row) => row.source !== S).map((row) => row.ref), ["interior_room:hall:front"]);
  assert.equal(nodeBlockers(data, ["settlement_node:town:c"])[0].ref, "district:d");
  assert.deepEqual(nodeBlockers(data, ["settlement_node:town:lone"]), []);
  const refusal = deletionRefusal({
    externalStatus: { current: true },
    summary: { crossDocument: false },
    relations: nodeBlockers(data, ["settlement_node:town:a"]),
    internalBlocks: true,
  });
  assert.equal(refusal.key, REFERENCED);
  assert.equal(refusal.count, 4);
});

test("road and bend removals are their own settlement commands", () => {
  const road = roadRef("town", "b", "a");
  assert.equal(settlementRemoval(road).name, "delete_road");
  assert.deepEqual(settlementRemoval(bendRef(road, 0)).arguments, { settlement_id: "town", source: "b", destination: "a", index: 0 });
  assert.equal(settlementRemoval("settlement_node:town:a"), null);
});
