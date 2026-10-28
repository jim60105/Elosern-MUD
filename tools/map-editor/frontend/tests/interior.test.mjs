import { test } from "node:test";
import assert from "node:assert/strict";

import {
  arrangement,
  arrangeLayout,
  connectionLabels,
  connectionRef,
  connectionRows,
  createConnection,
  interiorRemoval,
  parseInteriorRef,
  roomBlockers,
  serviceIdentity,
} from "../src/lib/interior.js";
import { interiorScene } from "../src/lib/map_scene.js";
import { objectCatalog } from "../src/lib/objects.js";
import { inspect } from "../src/lib/world_index.js";

const room = (interiorId, id, layout = null) => ({
  id,
  qualified_ref: `interior_room:${interiorId}:${id}`,
  name_zh: `name-${id}`,
  desc_zh: "",
  scene_archetype: null,
  art_key: null,
  layout_position: layout,
});

function hall() {
  return {
    id: "hall",
    relative_path: "content/maps/interiors/hall.yaml",
    layout_relative_path: null,
    rooms: ["a", "b", "c", "d", "e"].map((id) => room("hall", id)),
    connections: [
      { source: "b", destination: "c", label: "east" },
      { source: "c", destination: "b", label: "west" },
      { source: "c", destination: "d", label: "up" },
    ],
    interior_links: [],
    exterior: { settlement: "town", node: "yard", room: "b" },
  };
}

function world() {
  const other = {
    id: "annex",
    relative_path: "content/maps/interiors/annex.yaml",
    layout_relative_path: null,
    rooms: [room("annex", "x")],
    connections: [],
    interior_links: [{ source_room: "x", target_interior: "hall", target_room: "d", label: "door" }],
    exterior: null,
  };
  return {
    locations: [],
    settlements: [],
    interiors: [hall(), other],
    districts: [{ id: "dist", district_name_zh: "區", relative_path: "content/maps/districts.yaml", landmark: { domain: "interior_room", map_id: "hall", object_id: "e" } }],
    layouts: [],
  };
}

test("connection references round-trip any label without collisions", () => {
  for (const label of ["東 / 西", "a>b", "100%", "with space", "x:y", "前往%2F"]) {
    const ref = connectionRef("hall", "a", "b", label);
    assert.deepEqual(parseInteriorRef(ref), { kind: "connection", interiorId: "hall", source: "a", destination: "b", label });
  }
  assert.notEqual(connectionRef("hall", "a", "b", "x/y"), connectionRef("hall", "a", "b", "x%2Fy"));
  assert.deepEqual(parseInteriorRef("interior_room:hall:a"), { kind: "room", interiorId: "hall", roomId: "a" });
  assert.equal(parseInteriorRef("connection:hall:a>b/%E0"), null);
  assert.equal(parseInteriorRef("road:t:a>b"), null);
});

test("a two-way pair reads once with both labels; a one-way connection keeps its own", () => {
  const labels = connectionLabels(hall());
  assert.deepEqual([...labels.values()], ["east ⇄ west", "", "up"]);
  const rows = connectionRows(hall(), "c");
  assert.deepEqual(rows.outgoing.map((row) => [row.label, row.oneWay]), [["west → name-b", false], ["up → name-d", true]]);
  assert.deepEqual(rows.incoming.map((row) => row.oneWay), [false]);
});

test("a second exit with the same name from one room is flagged, never refused", () => {
  const interior = hall();
  interior.connections.push({ source: "c", destination: "a", label: "up" });
  const flagged = connectionRows(interior, "c").outgoing.filter((row) => row.sameLabel).map((row) => row.label);
  assert.deepEqual(flagged, ["up → name-d", "up → name-a"]);
});

test("the arrangement layers rooms from the entrance and is deterministic", () => {
  const positions = arrangement(hall());
  assert.deepEqual(positions, [
    { room_id: "b", x: 0, y: 0 },
    { room_id: "c", x: 1, y: 0 },
    { room_id: "d", x: 2, y: 0 },
    // Unreached rooms follow in further columns, in authored order.
    { room_id: "a", x: 3, y: 0 },
    { room_id: "e", x: 3, y: 1 },
  ]);
  assert.deepEqual(arrangement(hall()), positions);
  const command = arrangeLayout("hall", positions);
  assert.equal(command.documentId, "content/map-editor-layouts/hall.yaml");
  assert.equal(command.name, "arrange_interior_layout");
});

test("room delete blockers name every map reference and nothing cascades", () => {
  const kinds = (ref) => roomBlockers(world(), ref).map((row) => row.kind);
  assert.deepEqual(kinds("interior_room:hall:b"), ["連接", "連接", "入口"]);
  assert.deepEqual(kinds("interior_room:hall:d"), ["連接", "室內連結"]);
  assert.deepEqual(kinds("interior_room:hall:e"), ["地標"]);
  assert.deepEqual(kinds("interior_room:hall:a"), []);
});

test("only service and host records form the read-only service identity", () => {
  const incoming = {
    "interior_room:hall:a": [
      { source: "place:a", source_domain: "places", source_file: "p.py" },
      { source: "quest:q", source_domain: "quest_definitions", source_file: "q.py" },
      { source: "service_host:h", source_domain: "service_hosts", source_file: "h.py" },
    ],
  };
  assert.deepEqual(serviceIdentity(incoming, "interior_room:hall:a").map((row) => row.source), ["place:a", "service_host:h"]);
  assert.deepEqual(serviceIdentity(incoming, "interior_room:hall:b"), []);
});

test("connections are selectable curved links, catalogued and inspected without any length", () => {
  const interior = hall();
  const selected = connectionRef("hall", "c", "d", "up");
  const scene = interiorScene(interior, [selected]);
  assert.equal(scene.unit, null);
  assert.deepEqual(scene.links.map((link) => [link.ref, link.curve, link.selected]), [
    [connectionRef("hall", "b", "c", "east"), true, false],
    [connectionRef("hall", "c", "b", "west"), true, false],
    [selected, true, true],
  ]);
  assert.ok(scene.links.every((link) => !("lengthM" in link)));
  assert.equal(scene.items.length, interior.rooms.length + interior.connections.length);
  const current = world();
  const catalog = objectCatalog(current);
  assert.equal(catalog.get(selected).mapId, "hall");
  const record = inspect(current, selected);
  assert.equal(record.relativePath, "content/maps/interiors/hall.yaml");
  assert.equal(inspect(current, connectionRef("hall", "c", "d", "missing")), null);
});

test("connection commands target the interior document; removal needs no index", () => {
  const command = createConnection("hall", "a", "b", "in", "out");
  assert.equal(command.documentId, "content/maps/interiors/hall.yaml");
  assert.deepEqual(command.arguments, { interior_id: "hall", source: "a", destination: "b", label: "in", return_label: "out" });
  assert.equal(interiorRemoval(connectionRef("hall", "a", "b", "in")).name, "delete_connection");
  assert.equal(interiorRemoval("interior_room:hall:a"), null);
});
