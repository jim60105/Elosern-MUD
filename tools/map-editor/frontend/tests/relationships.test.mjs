// Mechanism tests of the entrance relationships: editor-local references,
// the view of both endpoints with their meaning, the 前往另一端 rule, the
// qualified-object selector's choices, the single-owner command descriptors,
// the catalog/scene entries and the delete blockers that locate each
// relationship. Synthetic fixtures only; no shipped copy is pinned.
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  editCommand,
  editableRoles,
  endpointChoices,
  endpointRule,
  entranceRequest,
  exteriorCardPosition,
  linkRef,
  otherEnd,
  ownerMap,
  parseRelationshipRef,
  relationshipRefs,
  relationshipRemoval,
  relationshipView,
} from "../src/lib/relationships.js";
import { objectCatalog, locate } from "../src/lib/objects.js";
import { interiorScene, settlementScene } from "../src/lib/map_scene.js";
import { inspect } from "../src/lib/world_index.js";
import { nodeBlockers } from "../src/lib/settlement.js";
import { roomBlockers } from "../src/lib/interior.js";
import { diagnosticTarget } from "../src/lib/diagnostics.js";
import { toolKeys } from "../src/lib/workbench.js";

const S = "content/maps/settlements/town.yaml";
const T = "content/maps/settlements/port.yaml";
const I = "content/maps/interiors/hall.yaml";
const J = "content/maps/interiors/annex.yaml";

const node = (settlement, id, key, local) => ({
  id, qualified_ref: `settlement_node:${settlement}:${id}`, key, local_m: local, world_m: local, anchor_key: null,
});
const room = (interior, id, name) => ({ id, qualified_ref: `interior_room:${interior}:${id}`, name_zh: name, layout_position: null });
const LABEL = "穿:廊>/x";

function world() {
  return {
    continent: { relative_path: "content/maps/continent.yaml", mainland_boundary_km: [], forest_edge: [], forest_edge_m: [], waterways: [], harbor_sites: [], regions: [], frame_cells: 40, cell_size_km: 1 },
    locations: [{ id: "place", qualified_ref: "location:place", relative_path: "content/maps/locations.yaml", display_name_zh: "城", local_maps: ["town"] }],
    districts: [],
    settlements: [
      {
        id: "town",
        relative_path: S,
        location_ref: "place",
        footprint: { shape: ["#"], origin: [5, 5], cells: [[5, 5]] },
        wilderness_entry: { shape: ["#"], origin: { cell_x: 5, cell_y: 5 }, gates: [{ return_direction: "w", destination_node: "gate", approach_cell: [5, 5] }] },
        city_gate: { node: "gate", exit_key: "Gate", exit_aliases: ["in"] },
        nodes: [node("town", "gate", "Gate", [0, 0]), node("town", "yard", "Square", [300, 400])],
        roads: [],
      },
      { id: "port", relative_path: T, location_ref: "place", footprint: null, wilderness_entry: null, city_gate: null, nodes: [node("port", "yard", "Square", [0, 0])], roads: [] },
    ],
    interiors: [
      {
        id: "hall",
        relative_path: I,
        rooms: [room("hall", "front", "前廳"), room("hall", "back", "後室")],
        connections: [],
        interior_links: [{ source_room: "back", target_interior: "annex", target_room: "lobby", label: LABEL, return_label: "回" }],
        exterior: { settlement: "town", node: "yard", room: "front", doorway_key: "Door", doorway_aliases: ["door"] },
      },
      { id: "annex", relative_path: J, rooms: [room("annex", "lobby", "前廳")], connections: [], interior_links: [], exterior: null },
    ],
    layouts: [],
  };
}

const LINK = linkRef("hall", world().interiors[0].interior_links[0]);

test("relationship references round-trip, labels with : > / included", () => {
  assert.deepEqual(parseRelationshipRef("gate:town:w"), { kind: "gate", settlementId: "town", direction: "w" });
  assert.deepEqual(parseRelationshipRef("city_gate:town"), { kind: "city_gate", settlementId: "town" });
  assert.deepEqual(parseRelationshipRef("exterior:hall"), { kind: "exterior", interiorId: "hall" });
  assert.deepEqual(parseRelationshipRef(LINK), {
    kind: "interior_link", interiorId: "hall", source: "back", targetInterior: "annex", targetRoom: "lobby", label: LABEL,
  });
  assert.equal(parseRelationshipRef("settlement_node:town:gate"), null);
  assert.deepEqual(ownerMap(LINK), { domain: "interior", mapId: "hall" });
  assert.deepEqual(relationshipRefs(world()), ["gate:town:w", "city_gate:town", "exterior:hall", LINK]);
});

test("each view names one owner record, both endpoints and the direction meaning", () => {
  const data = world();
  const exterior = relationshipView(data, "exterior:hall");
  assert.equal(exterior.ownerPath, I);
  assert.equal(exterior.twoWay, true);
  assert.deepEqual(exterior.endpoints.map((end) => [end.role, end.ref, end.mapId]), [
    ["node", "settlement_node:town:yard", "town"],
    ["room", "interior_room:hall:front", "hall"],
  ]);
  const start = relationshipView(data, "city_gate:town");
  assert.equal(start.twoWay, false);
  assert.equal(start.oneWayFixed, true);
  assert.equal(start.endpoints[0].ref, null);
  const gate = relationshipView(data, "gate:town:w");
  assert.equal(gate.ownerPath, S);
  // The wilderness end is the core's approach cell, reached via the footprint.
  assert.equal(gate.endpoints[0].ref, "footprint:town");
  assert.match(gate.endpoints[0].position, /5, 5/);
  const link = relationshipView(data, LINK);
  assert.equal(link.twoWay, true);
  assert.deepEqual(link.endpoints.map((end) => end.ref), ["interior_room:hall:back", "interior_room:annex:lobby"]);
  data.interiors[0].interior_links[0].return_label = null;
  assert.equal(relationshipView(data, LINK).twoWay, false);
  assert.equal(relationshipView(data, "gate:town:n"), null);
});

test("the other end is the far endpoint of the map on display, else the target", () => {
  const data = world();
  const exterior = relationshipView(data, "exterior:hall");
  assert.equal(otherEnd(exterior, { domain: "interior", mapId: "hall" }).ref, "settlement_node:town:yard");
  assert.equal(otherEnd(exterior, { domain: "settlement", mapId: "town" }).ref, "interior_room:hall:front");
  assert.equal(otherEnd(relationshipView(data, LINK), { domain: "interior", mapId: "hall" }).ref, "interior_room:annex:lobby");
  assert.equal(otherEnd(relationshipView(data, "gate:town:w"), { domain: "settlement", mapId: "town" }).ref, "footprint:town");
  // The starting room is no map object: the start entry's only navigable end is its node.
  assert.equal(otherEnd(relationshipView(data, "city_gate:town"), { domain: "settlement", mapId: "town" }).ref, "settlement_node:town:gate");
  data.settlements[0].footprint = null;
  assert.equal(otherEnd(relationshipView(data, "gate:town:w"), { domain: "settlement", mapId: "town" }).ref, "settlement_node:town:gate");
});

test("the selector offers only allowed objects, tells equal names apart and yields qualified IDs", () => {
  const catalog = objectCatalog(world());
  const exterior = relationshipView(world(), "exterior:hall");
  assert.deepEqual(editableRoles(exterior), ["node", "room"]);
  const nodes = endpointChoices(catalog, endpointRule(exterior, "node"), "square");
  assert.deepEqual(nodes.map((choice) => choice.ref), ["settlement_node:town:yard", "settlement_node:port:yard"]);
  assert.ok(nodes.every((choice) => choice.sameLabel === 2));
  assert.notEqual(nodes[0].parent, nodes[1].parent);
  // The exterior's room must be a room of its own interior.
  assert.deepEqual(endpointChoices(catalog, endpointRule(exterior, "room")).map((choice) => choice.ref), [
    "interior_room:hall:front", "interior_room:hall:back",
  ]);
  // A gate lands in its own settlement only.
  const gate = relationshipView(world(), "gate:town:w");
  assert.ok(endpointChoices(catalog, endpointRule(gate, "node")).every((choice) => choice.ref.startsWith("settlement_node:town:")));
  // A link target may be any interior's room.
  const targets = endpointChoices(catalog, endpointRule(relationshipView(world(), LINK), "target"), "前廳");
  assert.deepEqual(targets.map((choice) => choice.ref), ["interior_room:hall:front", "interior_room:annex:lobby"]);
});

test("every edit and removal is one command on the owning document with qualified endpoints", () => {
  const data = world();
  const exterior = relationshipView(data, "exterior:hall");
  const moved = editCommand(exterior, { node: "settlement_node:port:yard" });
  assert.equal(moved.descriptor.documentId, I);
  assert.equal(moved.descriptor.name, "set_exterior");
  assert.equal(moved.descriptor.arguments.value.node, "settlement_node:port:yard");
  assert.equal(moved.ref, "exterior:hall");
  const gate = editCommand(relationshipView(data, "gate:town:w"), { direction: "e" });
  assert.equal(gate.descriptor.documentId, S);
  assert.deepEqual(gate.descriptor.arguments.value, { return_direction: "e", node: "settlement_node:town:gate" });
  assert.equal(gate.ref, "gate:town:e");
  const relabelled = editCommand(relationshipView(data, LINK), { label: "stair", return_label: null });
  assert.equal(relabelled.descriptor.arguments.label, LABEL);
  assert.equal(relabelled.descriptor.arguments.value.return_label, null);
  assert.equal(parseRelationshipRef(relabelled.ref).label, "stair");
  // The start entry's value never carries a return field.
  const start = editCommand(relationshipView(data, "city_gate:town"), { exit_key: "Way" });
  assert.deepEqual(Object.keys(start.descriptor.arguments.value).sort(), ["exit_aliases", "exit_key", "node"]);
  assert.deepEqual(
    ["gate:town:w", "city_gate:town", "exterior:hall", LINK].map((ref) => {
      const removal = relationshipRemoval(data, ref);
      return [removal.name, removal.documentId];
    }),
    [["delete_wilderness_gate", S], ["set_city_gate", S], ["set_exterior", I], ["delete_interior_link", I]],
  );
  assert.equal(relationshipRemoval(data, "city_gate:town").arguments.value, null);
});

test("relationships are catalogued on their owner map, inspectable and searchable by ID only", () => {
  const data = world();
  const catalog = objectCatalog(data);
  for (const ref of relationshipRefs(data)) {
    const entry = catalog.get(ref);
    assert.equal(entry.kind, "relationship");
    assert.deepEqual({ domain: entry.domain, mapId: entry.mapId }, ownerMap(ref));
    assert.deepEqual(locate(catalog, ref), { ...ownerMap(ref), ref });
    assert.ok(!entry.label.includes("前廳"));
  }
  const record = inspect(data, "exterior:hall");
  assert.equal(record.relativePath, I);
  assert.equal(record.qualifiedRef, "exterior:hall");
});

test("the interior draws a fixed dashed exterior card; the settlement lists its entrances", () => {
  const data = world();
  const scene = interiorScene(data.interiors[0], ["exterior:hall"], data);
  const card = scene.marks.find((mark) => mark.id === "exterior:hall");
  const front = scene.marks.find((mark) => mark.id === "interior_room:hall:front");
  assert.equal(card.draggable, false);
  assert.deepEqual([card.x, card.y], [exteriorCardPosition(front).x, front.y]);
  assert.ok(scene.links.some((link) => link.ref === "exterior:hall" && link.selected));
  assert.ok(scene.items.some((item) => item.id === LINK));
  assert.equal(interiorScene(data.interiors[1], [], data).marks.some((mark) => mark.kind === "exterior"), false);
  assert.deepEqual(settlementScene(data.settlements[0]).items.slice(-2).map((item) => item.id), ["gate:town:w", "city_gate:town"]);
});

test("delete blockers locate each relationship for its separate removal", () => {
  const data = world();
  assert.deepEqual(nodeBlockers(data, ["settlement_node:town:gate"]).map((row) => row.ref), ["gate:town:w", "city_gate:town"]);
  assert.deepEqual(nodeBlockers(data, ["settlement_node:town:yard"]).map((row) => [row.ref, row.source]), [["exterior:hall", I]]);
  assert.deepEqual(roomBlockers(data, "interior_room:annex:lobby").map((row) => [row.ref, row.source]), [[LINK, I]]);
  assert.deepEqual(roomBlockers(data, "interior_room:hall:front").map((row) => row.ref), ["exterior:hall"]);
});

test("entrance diagnostics locate the relationship; the E tool is registered on both screens", () => {
  const data = world();
  const catalog = objectCatalog(data);
  assert.equal(diagnosticTarget(data, catalog, { relative_path: I, field_path: "exterior.node" }).ref, "exterior:hall");
  assert.equal(diagnosticTarget(data, catalog, { relative_path: S, field_path: "city_gate.node" }).ref, "city_gate:town");
  assert.equal(diagnosticTarget(data, catalog, { relative_path: I, field_path: "connections" }).ref, null);
  assert.equal(toolKeys("settlement").e, "entrance");
  assert.equal(toolKeys("interior").e, "entrance");
  assert.equal(entranceRequest("town", "yard", "settlement").defaults.node, "settlement_node:town:yard");
  assert.equal(entranceRequest("hall", "front").defaults.room, "interior_room:hall:front");
});
