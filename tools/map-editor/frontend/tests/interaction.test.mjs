// Mechanism tests of the interaction shell: catalog/search disambiguation,
// selection and ownership, relationships, the delete explanation order,
// diagnostic targets and classes, layers, the copy-only context and the
// keyboard resolver. Synthetic fixtures only; no shipped copy is pinned.
import { test } from "node:test";
import assert from "node:assert/strict";

import { locate, objectCatalog } from "../src/lib/objects.js";
import { searchObjects } from "../src/lib/search.js";
import { nextSelection } from "../src/lib/selection.js";
import { selectionSummary } from "../src/lib/selection_owner.js";
import { incomingOf, relationsOf } from "../src/lib/relations.js";
import { CROSS_DOCUMENT, INDEX_UNAVAILABLE, REFERENCED, UNAVAILABLE, deletionRefusal } from "../src/lib/deletion.js";
import { GO, REVEAL_GO, diagnosticGroups, diagnosticTarget, groupCounts } from "../src/lib/diagnostics.js";
import { defaultHiddenLayers, visibleScene } from "../src/lib/layers.js";
import { continentScene } from "../src/lib/map_scene.js";
import { currentness, ompContext } from "../src/lib/context_copy.js";
import { cycleRegion, isTextTarget, nearestInDirection, resolveKey } from "../src/lib/keyboard.js";
import { pushReturn, RETURN_LIMIT, useDrawers } from "../src/lib/workbench.js";
import { CONNECTED, DISCONNECTED } from "../src/lib/workspace_client.js";
import { HOLD_RESTART } from "../src/lib/following.js";

const S = "content/maps/settlements/town.yaml";
const I = "content/maps/interiors/hall.yaml";
const J = "content/maps/interiors/annex.yaml";
const L = "content/maps/locations.yaml";
const D = "content/maps/districts.yaml";
const C = "content/maps/continent.yaml";

function room(interior, id, name, layout = null) {
  return { id, qualified_ref: `interior_room:${interior}:${id}`, name_zh: name, layout_position: layout, unknown_field: "x" };
}

function fixture() {
  return {
    continent: {
      relative_path: C,
      mainland_boundary_km: [[0, 0], [4, 0], [4, 4]],
      waterways: [{ id: "river", route_m: [[0, 0], [1000, 0]] }],
      forest_edge_m: [[0, 3000], [3000, 3000]],
      frame_cells: 4,
      cell_size_km: 1,
    },
    locations: [
      { id: "place", qualified_ref: "location:place", relative_path: L, display_name_zh: "城", cell: [1, 1], centre_m: [1500, 1500], local_maps: ["town"] },
      { id: "wilds", qualified_ref: "location:wilds", relative_path: L, display_name_zh: "荒野", cell: [3, 3], centre_m: [3500, 3500], local_maps: [] },
    ],
    districts: [
      { id: "d1", relative_path: D, district_name_zh: "一區", landmark: { domain: "settlement_node", map_id: "town", object_id: "yard", cell: null } },
      { id: "d2", relative_path: D, district_name_zh: "二區", landmark: { domain: "wilderness_cell", map_id: null, object_id: null, cell: [2, 2] } },
      { id: "d3", relative_path: D, district_name_zh: "三區", landmark: { domain: "settlement_node", map_id: "town", object_id: "ghost", cell: null } },
    ],
    settlements: [
      {
        id: "town",
        relative_path: S,
        location_ref: "place",
        city_gate: { node: "gate", exit_key: "Gate" },
        wilderness_entry: { gates: [{ return_direction: "n", destination_node: "gate" }] },
        nodes: [
          { id: "gate", qualified_ref: "settlement_node:town:gate", key: "Gate", anchor_key: "place", local_m: [0, 0], world_m: [1500, 1500] },
          { id: "yard", qualified_ref: "settlement_node:town:yard", key: "Yard", anchor_key: null, local_m: [300, 400], world_m: [1800, 1900] },
        ],
        roads: [
          { id: "gate>yard", source: "gate", destination: "yard", direction: "ne", bends: [], length_m: 500 },
          { id: "yard>gate", source: "yard", destination: "gate", direction: "s", bends: [], length_m: 700 },
        ],
        interiors: ["hall"],
      },
    ],
    interiors: [
      {
        id: "hall",
        relative_path: I,
        layout_relative_path: null,
        rooms: [room("hall", "front", "前廳"), room("hall", "back", "後室")],
        connections: [
          { source: "front", destination: "back", label: "in" },
          { source: "back", destination: "front", label: "out" },
        ],
        interior_links: [],
        exterior: { settlement: "town", node: "yard", room: "front" },
      },
      {
        id: "annex",
        relative_path: J,
        layout_relative_path: "content/map-editor-layouts/annex.yaml",
        rooms: [room("annex", "front", "前廳", [2, 1])],
        connections: [],
        interior_links: [{ source_room: "front", target_interior: "hall", target_room: "back", label: "穿廊" }],
        exterior: null,
      },
    ],
    layouts: [{ id: "annex", relative_path: "content/map-editor-layouts/annex.yaml" }],
  };
}

const world = fixture();
const catalog = objectCatalog(world);

test("search tells equal names apart by parent map and source document", () => {
  // Entrance relationships are labelled by IDs, so a name finds only rooms.
  const results = searchObjects(catalog, "前廳");
  assert.deepEqual(results.map((item) => item.ref), ["interior_room:hall:front", "interior_room:annex:front"]);
  assert.ok(results.every((item) => item.sameLabel === 2));
  assert.notEqual(results[0].parentLabel, results[1].parentLabel);
  assert.deepEqual(results.map((item) => item.relativePath), [I, J]);
  // Exact matches outrank substrings, and ids are searchable.
  assert.equal(searchObjects(catalog, "yard")[0].ref, "settlement_node:town:yard");
  assert.deepEqual(searchObjects(catalog, "  "), []);
  assert.equal(locate(catalog, "interior_room:annex:front").mapId, "annex");
  assert.deepEqual(locate(catalog, "settlement:town"), { domain: "settlement", mapId: "town", ref: null });
  assert.equal(locate(catalog, "interior_room:nowhere:x"), null);
});

test("selection is none, single or multi; a cross-document selection is inspect/copy only", () => {
  const order = ["a", "b", "c", "d"];
  assert.deepEqual(nextSelection([], "b"), ["b"]);
  assert.deepEqual(nextSelection(["b"], "d", { toggle: true }), ["b", "d"]);
  assert.deepEqual(nextSelection(["b", "d"], "b", { toggle: true }), ["d"]);
  assert.deepEqual(nextSelection(["a"], "c", { range: true, order }), ["a", "b", "c"]);
  assert.deepEqual(nextSelection(["a", "b"], null), []);
  const same = selectionSummary(catalog, ["interior_room:hall:front", "interior_room:hall:back"]);
  assert.equal(same.crossDocument, false);
  assert.equal(same.reason, null);
  const cross = selectionSummary(catalog, ["interior_room:hall:front", "interior_room:annex:front", "settlement_node:town:yard"]);
  assert.equal(cross.crossDocument, true);
  assert.deepEqual(cross.owners, [J, I, S].sort());
  assert.ok(cross.reason);
});

test("relationships come from authored fields and name their declaring document", () => {
  const external = { "settlement_node:town:yard": [{ source: "place:x", source_domain: "places", source_file: "world/x.py" }] };
  const yard = relationsOf(world, external, "settlement_node:town:yard");
  assert.deepEqual(yard.outgoing.map((row) => row.ref), ["settlement_node:town:gate"]);
  const kinds = yard.incoming.map((row) => [row.ref, row.source, row.external]);
  assert.deepEqual(kinds, [
    ["settlement_node:town:gate", S, false],
    ["exterior:hall", I, false],
    [null, D, false],
    [null, "world/x.py", true],
  ]);
  const back = relationsOf(world, {}, "interior_room:hall:back");
  assert.ok(back.incoming.some((row) => row.ref.startsWith("interior_link:annex:front>hall:back/") && row.source === J));
  const front = relationsOf(world, {}, "interior_room:hall:front");
  assert.ok(front.outgoing.some((row) => row.ref === "exterior:hall"));
  const place = relationsOf(world, {}, "location:place");
  assert.ok(place.incoming.some((row) => row.ref === "settlement:town"));
  assert.equal(relationsOf(world, {}, "location:nowhere"), null);
});

test("the delete explanation: cross-document, then unknown index, then enforced external references", () => {
  const rows = [
    { kind: "道路", external: false, ref: "x" },
    { kind: "外部", external: true, ref: null },
  ];
  const single = { crossDocument: false };
  assert.equal(deletionRefusal({ externalStatus: { current: true }, summary: { crossDocument: true }, relations: rows }).key, CROSS_DOCUMENT);
  // An index that is not current proves nothing, even when it lists references.
  const stale = deletionRefusal({ externalStatus: { current: false, reasons: ["changed"] }, summary: single, relations: rows });
  assert.equal(stale.key, INDEX_UNAVAILABLE);
  assert.deepEqual(stale.reasons, ["changed"]);
  assert.equal(deletionRefusal({ externalStatus: null, summary: single, relations: [] }).key, INDEX_UNAVAILABLE);
  const referenced = deletionRefusal({ externalStatus: { current: true }, summary: single, relations: rows });
  assert.equal(referenced.key, REFERENCED);
  assert.equal(referenced.external.length, 1);
  assert.equal(referenced.internal.length, 1);
  // Internal relations alone never claim a refusal the service does not enforce.
  assert.equal(deletionRefusal({ externalStatus: { current: true }, summary: single, relations: [rows[0]] }).key, UNAVAILABLE);
});

test("diagnostics resolve their target or keep file:line without navigation", () => {
  const target = (item) => diagnosticTarget(world, catalog, item);
  assert.equal(target({ relative_path: D, object_id: "d1", field_path: "districts.d1.landmark" }).ref, "settlement_node:town:yard");
  // A dangling or non-object landmark never picks another object.
  assert.equal(target({ relative_path: D, object_id: "d3" }), null);
  assert.equal(target({ relative_path: D, object_id: "d2" }), null);
  assert.equal(target({ relative_path: D, object_id: "missing" }), null);
  assert.deepEqual(target({ relative_path: S, object_id: "town", field_path: "wilderness_entry.gates" }), {
    domain: "continent",
    mapId: null,
    ref: "location:place",
    layer: "footprint",
  });
  assert.equal(target({ relative_path: S, object_id: "town", field_path: "roads" }).mapId, "town");
  assert.equal(target({ relative_path: C, field_path: "terrain.waterways.river" }).layer, "water");
  assert.equal(target({ relative_path: L, object_id: "wilds" }).ref, "location:wilds");
  assert.equal(target({ relative_path: L, object_id: "gone" }), null);
  assert.equal(target({ relative_path: "content/map-editor-layouts/annex.yaml" }).mapId, "annex");
  assert.equal(target({ relative_path: null, code: "stale_partition" }).layer, "partition");
  assert.equal(target({ relative_path: "content/maps/unknown.yaml" }), null);
  assert.equal(diagnosticTarget(null, catalog, { relative_path: S }), null);
});

test("diagnostic classes, hidden-layer targets and synthesized status rows", () => {
  const workspace = {
    diagnostics: [
      { code: "stale_partition", category: "semantic", message: "m", relative_path: null, field_path: "" },
      { code: "blocked_approach", category: "semantic", message: "m", relative_path: S, field_path: "wilderness_entry.gates", object_id: "town" },
      { code: "unreachable_landmark", category: "semantic", message: "m", relative_path: D, field_path: "x", object_id: "d1" },
    ],
    candidate_diagnostics: [{ code: "yaml_syntax", category: "structure", message: "m", relative_path: S, line: 3 }],
    external_context_status: { current: false, status: "missing", reasons: ["missing"] },
    partition_status: { current: false, status: "stale", reasons: [] },
    following: { error: "boom" },
  };
  const failure = { code: "stale_snapshot", command: "move_interior_layout", message: "m", documentId: "x.yaml" };
  const groups = diagnosticGroups({ workspace, world, catalog, failure, connection: DISCONNECTED, hidden: defaultHiddenLayers() });
  const byKey = Object.fromEntries(groups.map((group) => [group.key, group]));
  assert.deepEqual(Object.keys(byKey), ["structure", "external", "service", "semantic", "partition"]);
  // A failed read keeps file:line and is not navigable.
  assert.equal(byKey.structure.rows[0].action, null);
  assert.equal(byKey.structure.rows[0].where, `${S}:3`);
  assert.equal(byKey.external.rows.length, 1);
  assert.equal(byKey.service.rows.length, 3);
  const semantic = Object.fromEntries(byKey.semantic.rows.map((row) => [row.code, row.action]));
  // The footprint layer is hidden by default; the landmark has no layer.
  assert.equal(semantic.blocked_approach, REVEAL_GO);
  assert.equal(semantic.unreachable_landmark, GO);
  // The core's stale_partition row is not duplicated by the status row.
  assert.deepEqual(byKey.partition.rows.map((row) => [row.code, row.action]), [["stale_partition", GO]]);
  const hidden = diagnosticGroups({ workspace, world, catalog, hidden: ["partition"] });
  assert.equal(hidden.find((group) => group.key === "partition").rows[0].action, REVEAL_GO);
  const counts = groupCounts(groups);
  assert.equal(counts.total, counts.errors + counts.warnings);
  assert.equal(counts.warnings, 3);
});

test("hidden continent layers leave their drawables out of the scene and object list", () => {
  const scene = continentScene(world);
  const off = visibleScene(scene, ["locations", "water"]);
  assert.equal(off.marks.length, 0);
  assert.ok(off.shapes.every((shape) => shape.role !== "water"));
  assert.ok(off.shapes.some((shape) => shape.role === "land"));
  assert.equal(visibleScene(scene, []).marks.length, world.locations.length);
});

test("the copied context names every source and its currentness, and nothing secret", () => {
  const secret = "token-SECRET-123";
  const workspace = {
    world,
    preview_state: "stale",
    snapshot_read_at: "2026-10-28T10:00:00Z",
    candidate_diagnostics: [{ relative_path: S, line: 7, message: "bad" }],
    token: secret,
    session_generation: "session-SECRET",
    history: { segment: "segment-SECRET" },
    workspace_root: "/home/someone/repo",
  };
  const refs = ["settlement_node:town:yard", "interior_room:annex:front", "location:wilds"];
  const calls = [];
  const saved = globalThis.fetch;
  globalThis.fetch = (...args) => calls.push(args);
  let text;
  try {
    text = ompContext({ workspace, connection: CONNECTED, catalog, refs, domain: "settlement", mapId: "town" });
  } finally {
    globalThis.fetch = saved;
  }
  assert.equal(calls.length, 0);
  for (const ref of refs) assert.ok(text.includes(ref));
  for (const path of [S, J, L]) assert.ok(text.includes(path));
  assert.ok(text.includes(`${S}:7`));
  for (const leaked of [secret, "session-SECRET", "segment-SECRET", "/home/someone"]) assert.ok(!text.includes(leaked));
  assert.ok(text.includes(" m"));
  assert.equal(currentness({ workspace, connection: CONNECTED }).current, false);
  assert.equal(currentness({ workspace: { ...workspace, preview_state: "current" }, connection: CONNECTED }).current, true);
  assert.equal(currentness({ workspace: { ...workspace, preview_state: "current" }, connection: DISCONNECTED }).current, false);
  assert.equal(currentness({ workspace: { ...workspace, preview_state: "current" }, hold: HOLD_RESTART }).current, false);
  const empty = ompContext({ workspace: { ...workspace, preview_state: "current" }, catalog, refs: [], domain: "interior", mapId: "annex" });
  assert.ok(empty.includes(J));
});

function key(key, extra = {}) {
  return { key, shiftKey: false, ctrlKey: false, metaKey: false, altKey: false, isComposing: false, keyCode: 0, ...extra };
}

test("single-key shortcuts never act in text fields, during composition or with modifiers", () => {
  const ctx = { domains: { 1: "continent" }, tools: { v: "select" }, hasSelection: true, nudgeScope: true };
  assert.deepEqual(resolveKey(key("1"), ctx), { type: "domain", domain: "continent" });
  assert.deepEqual(resolveKey(key("v"), ctx), { type: "tool", tool: "select" });
  assert.equal(resolveKey(key("1"), { ...ctx, text: true }), null);
  assert.equal(resolveKey(key("1", { isComposing: true }), ctx), null);
  assert.equal(resolveKey(key("1", { keyCode: 229 }), ctx), null);
  assert.equal(resolveKey(key("1", { altKey: true }), ctx), null);
  assert.equal(resolveKey(key("Delete"), { ...ctx, text: true }), null);
  assert.deepEqual(resolveKey(key("Delete"), ctx), { type: "delete" });
  assert.equal(resolveKey(key("Delete"), { ...ctx, hasSelection: false }), null);
  // The field's own undo applies inside text; save and search work anywhere.
  assert.equal(resolveKey(key("z", { ctrlKey: true }), { ...ctx, text: true }), null);
  assert.deepEqual(resolveKey(key("z", { ctrlKey: true }), ctx), { type: "undo" });
  assert.deepEqual(resolveKey(key("Z", { ctrlKey: true, shiftKey: true }), ctx), { type: "redo" });
  assert.deepEqual(resolveKey(key("z", { metaKey: true }), { ...ctx, mac: true }), { type: "undo" });
  assert.equal(resolveKey(key("z", { metaKey: true }), ctx), null);
  assert.deepEqual(resolveKey(key("s", { ctrlKey: true }), { ...ctx, text: true }), { type: "save" });
  assert.deepEqual(resolveKey(key("k", { ctrlKey: true }), { ...ctx, text: true }), { type: "search" });
  assert.deepEqual(resolveKey(key("/"), ctx), { type: "search" });
  assert.deepEqual(resolveKey(key("F6", { shiftKey: true }), { ...ctx, text: true }), { type: "region", step: -1 });
  assert.deepEqual(resolveKey(key("F6"), { ...ctx, drawerOpen: true }), { type: "trap" });
  assert.deepEqual(resolveKey(key("ArrowLeft", { altKey: true }), { ...ctx, canReturn: true }), { type: "return" });
  assert.equal(resolveKey(key("ArrowLeft", { altKey: true }), ctx), null);
  assert.deepEqual(resolveKey(key("ArrowRight", { shiftKey: true }), ctx), { type: "nudge", delta: [1, 0] });
  assert.equal(resolveKey(key("ArrowRight", { shiftKey: true }), { ...ctx, nudgeScope: false }), null);
});

test("Escape cancels in order: drawer, tool operation, delete explanation, selection", () => {
  const all = { drawerOpen: true, toolActive: true, refusalShown: true, hasSelection: true };
  const target = (ctx) => resolveKey(key("Escape"), ctx)?.target ?? null;
  assert.equal(target(all), "drawer");
  assert.equal(target({ ...all, drawerOpen: false }), "tool");
  assert.equal(target({ ...all, drawerOpen: false, toolActive: false }), "refusal");
  assert.equal(target({ hasSelection: true }), "selection");
  assert.equal(target({}), null);
  // In a text field only an open drawer closes; the field owns its draft.
  assert.equal(target({ hasSelection: true, text: true }), null);
  assert.equal(target({ drawerOpen: true, text: true }), "drawer");
});

test("text targets, region cycling, arrow walking, drawers and the return stack", () => {
  const element = (tagName, type, selector = false) => ({ tagName, type, closest: (s) => (selector && s === "[data-object-selector]" ? {} : null) });
  assert.equal(isTextTarget(element("INPUT", "text")), true);
  assert.equal(isTextTarget(element("INPUT", "checkbox")), false);
  assert.equal(isTextTarget(element("SELECT")), true);
  assert.equal(isTextTarget(element("BUTTON", "button", true)), true);
  assert.equal(isTextTarget(element("BUTTON", "button")), false);
  assert.equal(isTextTarget(null), false);
  assert.equal(cycleRegion(5, 4, 1), 0);
  assert.equal(cycleRegion(5, 0, -1), 4);
  assert.equal(cycleRegion(5, -1, 1), 0);
  const marks = [
    { id: "o", x: 0, y: 0 },
    { id: "e", x: 10, y: 1 },
    { id: "far", x: 30, y: 0 },
    { id: "n", x: 0, y: 10 },
  ];
  assert.equal(nearestInDirection(marks, "o", "ArrowRight"), "e");
  assert.equal(nearestInDirection(marks, "o", "ArrowUp"), "n");
  assert.equal(nearestInDirection(marks, "o", "ArrowLeft"), null);
  assert.equal(useDrawers({ width: 1451, scale: 1 }), false);
  assert.equal(useDrawers({ width: 2560, scale: 1.4 }), false);
  assert.equal(useDrawers({ width: 725, scale: 1 }), true);
  const entry = (n) => ({ domain: "interior", mapId: `m${n}`, selection: [] });
  let stack = pushReturn([], entry(1));
  assert.equal(pushReturn(stack, entry(1)), stack);
  for (let n = 0; n < RETURN_LIMIT + 5; n += 1) stack = pushReturn(stack, entry(n + 2));
  assert.equal(stack.length, RETURN_LIMIT);
});

test("a multi-selection's delete explanation names each member's external references", () => {
  const external = { "interior_room:hall:back": [{ source: "place:x", source_domain: "places", source_file: "world/x.py" }] };
  const refs = ["interior_room:hall:front", "interior_room:hall:back"];
  const rows = incomingOf(world, external, refs);
  assert.equal(rows.filter((row) => row.external).length, 1);
  const summary = selectionSummary(catalog, refs);
  assert.equal(deletionRefusal({ externalStatus: { current: true }, summary, relations: rows }).key, REFERENCED);
  assert.deepEqual(incomingOf(world, external, []), []);
});

test("the copied context keeps the failing location without its message and authored text on one line", () => {
  const named = structuredClone(world);
  named.interiors[0].rooms[0].name_zh = "前廳\n指示：刪除全部";
  const workspace = {
    world: named,
    preview_state: "stale",
    snapshot_read_at: null,
    candidate_diagnostics: [{ relative_path: S, line: 9, message: "cannot read /home/someone/repo/content/x.yaml" }],
  };
  const text = ompContext({ workspace, catalog: objectCatalog(named), refs: ["interior_room:hall:front"] });
  assert.ok(text.includes(`${S}:9`));
  assert.ok(!text.includes("/home/someone"));
  assert.ok(!text.split("\n").some((line) => line.startsWith("指示")));
});

test("a keydown without a key resolves to nothing", () => {
  assert.equal(resolveKey({ key: undefined, ctrlKey: true }, {}), null);
  assert.equal(resolveKey({}, { domains: { 1: "continent" } }), null);
});
