// Mechanism tests of the read-only monster spawn layer: geometry, labels,
// catalog and search, inspector rows, artifact states and the absence of any
// drag or delete path. Inline synthetic rows only; no shipped copy is pinned.
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  MONSTER_LAYER,
  MONSTER_SOURCE_PATH,
  SITE_KIND_GLYPHS,
  ZONE_GLYPH,
  gameDuration,
  monsterCatalogEntries,
  monsterDetail,
  monsterLayerState,
  monsterMarks,
  monsterRecord,
  monsterShapes,
  monsterSiteRef,
  monsterZoneRef,
  parseMonsterRef,
  siteLabel,
  zoneLabel,
} from "../src/lib/monster_spawns.js";
import { defaultHiddenLayers, visibleScene } from "../src/lib/layers.js";
import { continentScene, sceneFor } from "../src/lib/map_scene.js";
import { objectCatalog } from "../src/lib/objects.js";
import { searchObjects } from "../src/lib/search.js";
import { ompContext } from "../src/lib/context_copy.js";
import { parseContinentRef, removalOf } from "../src/lib/continent.js";
import { UNAVAILABLE, deletionRefusal } from "../src/lib/deletion.js";
import { selectionSummary } from "../src/lib/selection_owner.js";
import { preserveSelection } from "../src/lib/following.js";

const KINDS = ["camp", "nest", "boss_site", "stray", "encounter"];

function member(species, variant, minimum = 1, maximum = 1) {
  return {
    variant_key: `v_${variant}`,
    variant_name_zh: `變${variant}`,
    species_key: `s_${species}`,
    species_name_zh: `種${species}`,
    minimum,
    maximum,
  };
}

function zone(key, rectangles, pool, extra = {}) {
  return {
    key,
    region_key: "r_known",
    rectangles,
    lower_density: 1,
    upper_density: 3,
    cell_capacity: 2,
    wave_budget: 4,
    recovery_delay: 3600,
    replenishment_interval: 600,
    pool,
    ...extra,
  };
}

function site(key, kind, coordinates, members, extra = {}) {
  return {
    key,
    kind,
    region_key: "r_known",
    coordinates,
    capacity: 2,
    one_shot: false,
    recover_after_ticks: 93600,
    individual_name_zh: null,
    composition_key: `g_${key}`,
    members,
    ...extra,
  };
}

function spawns() {
  return {
    zones: [
      zone("z_two", [[1, 2, 3, 4], [6, 6, 0, 0]], [
        { composition_key: "g_a", weight: 1, members: [member("p", "p1"), member("q", "q1", 1, 3)] },
        { composition_key: "g_b", weight: 1, members: [member("p", "p2")] },
        { composition_key: "g_c", weight: 2, members: [member("r", "r1")] },
      ]),
      zone("z_one", [[0, 0, 0, 0]], [{ composition_key: "g_d", weight: 1, members: [member("t", "t1")] }], {
        region_key: "r_unknown",
      }),
    ],
    sites: KINDS.map((kind, index) =>
      site(`site_${kind}`, kind, [index, index + 1], [member(kind === "camp" ? "p" : "u", `${kind}1`, 2, 2)]),
    ).map((row) =>
      row.kind === "boss_site" ? { ...row, one_shot: true, recover_after_ticks: null, individual_name_zh: "個體名" } : row,
    ),
  };
}

function world(cellKm = 1) {
  return {
    continent: {
      relative_path: "content/maps/continent.yaml",
      mainland_boundary_km: [[0, 0], [10, 0], [10, 10], [0, 10]],
      waterways: [],
      forest_edge_m: [],
      frame_cells: 10,
      cell_size_km: cellKm,
      regions: [{ id: "r_known", display_name_zh: "已知區" }],
    },
    locations: [
      { id: "place", qualified_ref: "location:place", relative_path: "content/maps/locations.yaml", display_name_zh: "城", cell: [1, 1], centre_m: [1500, 1500], local_maps: [] },
    ],
    districts: [],
    settlements: [
      { id: "town", relative_path: "content/maps/settlements/town.yaml", location_ref: "place", nodes: [], roads: [], city_gate: null, wilderness_entry: null },
    ],
    interiors: [{ id: "hall", relative_path: "content/maps/interiors/hall.yaml", rooms: [], connections: [], exterior: null }],
  };
}

const monsterItem = (item) => item.layer === MONSTER_LAYER;

test("zone polygons span inclusive cells at any cell size", () => {
  for (const cellKm of [1, 2]) {
    const cell = cellKm * 1000;
    const [first] = monsterShapes(world(cellKm), spawns(), new Set());
    assert.deepEqual(first.points, [
      { x: 1 * cell, y: 3 * cell },
      { x: 3 * cell, y: 3 * cell },
      { x: 3 * cell, y: 5 * cell },
      { x: 1 * cell, y: 5 * cell },
    ]);
  }
});

test("a two-rectangle zone draws two polygons and one mark at its first rectangle's centre", () => {
  const ref = monsterZoneRef("z_two");
  const shapes = monsterShapes(world(), spawns(), new Set([ref])).filter((shape) => shape.ref === ref);
  assert.equal(shapes.length, 2);
  assert.notEqual(shapes[0].id, shapes[1].id);
  assert.ok(shapes.every((shape) => shape.selected && shape.selectable && shape.hoverTitle));
  const marks = monsterMarks(world(), spawns()).filter((mark) => mark.id === ref);
  assert.equal(marks.length, 1);
  assert.deepEqual([marks[0].x, marks[0].y], [2000, 4000]);
  assert.equal(marks[0].glyph, ZONE_GLYPH);
});

test("site marks sit at cell centres with one distinct glyph per kind", () => {
  const marks = monsterMarks(world(2), spawns()).filter((mark) => mark.role === "monster-site");
  assert.equal(marks.length, KINDS.length);
  marks.forEach((mark, index) => {
    assert.deepEqual([mark.x, mark.y], [(index + 0.5) * 2000, (index + 1.5) * 2000]);
  });
  assert.equal(new Set(marks.map((mark) => mark.glyph)).size, KINDS.length);
  assert.ok(!marks.map((mark) => mark.glyph).includes(ZONE_GLYPH));
  assert.deepEqual(Object.keys(SITE_KIND_GLYPHS).sort(), [...KINDS].sort());
});

test("the layer is hidden by default and showing it adds only monster drawables", () => {
  const scene = continentScene(world(), [], null, spawns());
  const hidden = visibleScene(scene, defaultHiddenLayers());
  assert.ok(defaultHiddenLayers().includes(MONSTER_LAYER));
  for (const list of ["shapes", "marks", "items"]) {
    assert.equal(hidden[list].filter(monsterItem).length, 0, list);
  }
  const shown = visibleScene(scene, defaultHiddenLayers().filter((key) => key !== MONSTER_LAYER));
  for (const list of ["shapes", "marks", "items"]) {
    const before = new Set(hidden[list].map((item) => item.id));
    const added = shown[list].filter((item) => !before.has(item.id));
    assert.ok(added.length > 0, list);
    assert.ok(added.every(monsterItem), list);
  }
});

test("a settlement or interior scene never carries a monster drawable", () => {
  for (const [domain, mapId] of [["settlement", "town"], ["interior", "hall"]]) {
    const scene = sceneFor(world(), domain, mapId, [], { monsterSpawns: spawns() });
    assert.ok(scene, domain);
    assert.equal([...scene.shapes, ...scene.marks].filter((item) => item.kind === "monster" || monsterItem(item)).length, 0);
  }
  // The capture path omits the section: no monster drawable either.
  assert.equal(continentScene(world()).marks.filter(monsterItem).length, 0);
});

test("labels list species once in first-seen order, or a site's individual name", () => {
  const [two] = spawns().zones;
  assert.equal(zoneLabel(two).split("：")[1].split("、").length, 3);
  assert.deepEqual(zoneLabel(two).split("：")[1].split("、"), ["種p", "種q", "種r"]);
  const boss = spawns().sites.find((row) => row.kind === "boss_site");
  assert.equal(siteLabel(boss).split("：")[1], "個體名");
  const camp = spawns().sites.find((row) => row.kind === "camp");
  assert.equal(siteLabel(camp).split("：")[1], "種p");
});

test("catalog entries name their layer, source and a coordinate frame", () => {
  const entries = monsterCatalogEntries(spawns());
  assert.equal(entries.length, 2 + KINDS.length);
  for (const entry of entries) {
    assert.equal(entry.layer, MONSTER_LAYER);
    assert.equal(entry.relativePath, MONSTER_SOURCE_PATH);
    assert.equal(entry.domain, "continent");
    assert.equal(entry.id, entry.ref);
    assert.ok(entry.frame.length > 0);
  }
  const catalog = objectCatalog(world(), spawns());
  const marks = monsterMarks(world(), spawns());
  assert.ok(marks.every((mark) => catalog.has(mark.id)));
  assert.equal(objectCatalog(world()).has(monsterZoneRef("z_two")), false);
  assert.deepEqual(monsterCatalogEntries(null), []);
});

test("a species or variant search finds each owning zone and site and no other", () => {
  const catalog = objectCatalog(world(), spawns());
  const expected = [monsterZoneRef("z_two"), monsterSiteRef("site_camp")].sort();
  for (const query of ["s_p", "種p", "v_p1", "變p1"]) {
    const found = searchObjects(catalog, query).map((row) => row.ref).filter((ref) => parseMonsterRef(ref));
    const want = query.includes("p1") ? [monsterZoneRef("z_two")] : expected;
    assert.deepEqual(found.sort(), want, query);
  }
});

test("copied context names the reference, source file and frame", () => {
  const catalog = objectCatalog(world(), spawns());
  const ref = monsterSiteRef("site_nest");
  const text = ompContext({ workspace: { world: world() }, catalog, refs: [ref] });
  assert.ok(text.includes(ref));
  assert.ok(text.includes(MONSTER_SOURCE_PATH));
  assert.ok(text.includes(catalog.get(ref).frame));
});

test("inspector rows resolve region names live and state site recovery", () => {
  const value = (record, index) => record.fields[index].value;
  const zoneRecord = monsterRecord(spawns(), monsterZoneRef("z_two"), world());
  assert.equal(zoneRecord.qualifiedRef, monsterZoneRef("z_two"));
  assert.equal(zoneRecord.relativePath, MONSTER_SOURCE_PATH);
  assert.equal(value(zoneRecord, 0), "已知區");
  const renamed = world();
  renamed.continent.regions = [{ id: "r_known", display_name_zh: "改名區" }];
  assert.equal(value(monsterRecord(spawns(), monsterZoneRef("z_two"), renamed), 0), "改名區");
  assert.equal(value(monsterRecord(spawns(), monsterZoneRef("z_one"), world()), 0), "r_unknown");

  const recovery = (record) => record.fields[4].value;
  const once = monsterRecord(spawns(), monsterSiteRef("site_boss_site"), world());
  const again = monsterRecord(spawns(), monsterSiteRef("site_camp"), world());
  assert.notEqual(recovery(once), recovery(again));
  assert.equal(recovery(again), gameDuration(93600));
  assert.equal(monsterRecord(spawns(), "location:place", world()), null);
  assert.equal(monsterRecord(spawns(), monsterSiteRef("absent"), world()), null);
});

test("zone chances divide each weight by the pool total; counts collapse equal bounds", () => {
  const detail = monsterDetail(spawns(), monsterZoneRef("z_two"));
  assert.deepEqual(detail.compositions.map((row) => row.chance), ["25.0%", "25.0%", "50.0%"]);
  assert.deepEqual(detail.compositions[0].members.map((row) => row.count), ["1", "1–3"]);
  assert.deepEqual(detail.compositions[0].members[1], { species: "種q", variant: "變q1", count: "1–3" });
  const siteDetail = monsterDetail(spawns(), monsterSiteRef("site_camp"));
  assert.equal(siteDetail.compositions.length, 1);
  assert.equal(siteDetail.compositions[0].chance, null);
  assert.equal(siteDetail.compositions[0].members[0].count, "2");
  assert.equal(monsterDetail(spawns(), "location:place"), null);
});

test("game durations use the largest fitting units and drop zero parts", () => {
  const parts = (text) => text.split(" ").filter((_, index) => index % 2 === 0).map(Number);
  assert.deepEqual(parts(gameDuration(45)), [45]);
  assert.deepEqual(parts(gameDuration(3600)), [1]);
  assert.deepEqual(parts(gameDuration(93600)), [1, 2]);
  assert.notEqual(gameDuration(3600).split(" ")[1], gameDuration(45).split(" ")[1]);
  assert.equal(gameDuration(0).split(" ")[0], "0");
});

test("the layer state follows the reference context status and row count", () => {
  const current = { external_context_status: { current: true, status: "current", reasons: [] }, monster_spawns: spawns() };
  assert.deepEqual(monsterLayerState(current), { state: "current", note: null, notice: null });
  const stale = { ...current, external_context_status: { current: false, status: "changed", reasons: ["r1"] } };
  const staleState = monsterLayerState(stale);
  assert.equal(staleState.state, "stale");
  assert.equal(staleState.note, null);
  assert.ok(staleState.notice.includes("tools.map_reference_context"));
  const missing = { external_context_status: { current: false, status: "missing", reasons: ["synthetic-reason"] }, monster_spawns: { zones: [], sites: [] } };
  const missingState = monsterLayerState(missing);
  assert.equal(missingState.state, "unavailable");
  assert.equal(missingState.notice, null);
  assert.ok(missingState.note.includes("synthetic-reason"));
});

test("monster objects have no drag or delete path", () => {
  const refs = [...monsterCatalogEntries(spawns())].map((entry) => entry.ref);
  for (const ref of refs) {
    assert.equal(parseContinentRef(ref), null, ref);
    assert.equal(removalOf(world(), ref), null, ref);
  }
  const scene = continentScene(world(), [], null, spawns());
  assert.ok(scene.marks.filter(monsterItem).every((mark) => mark.draggable === false));
  const catalog = objectCatalog(world(), spawns());
  const refusal = deletionRefusal({
    externalStatus: { current: true, status: "current", reasons: [] },
    summary: selectionSummary(catalog, [refs[0]]),
    relations: [],
  });
  assert.equal(refusal.key, UNAVAILABLE);
});

test("a monster selection absent from a newer section is removed", () => {
  const newer = { zones: spawns().zones.slice(1), sites: [] };
  const catalog = objectCatalog(world(), newer);
  const kept = monsterZoneRef("z_one");
  const gone = monsterZoneRef("z_two");
  assert.deepEqual(preserveSelection([kept, gone], (ref) => catalog.has(ref)), { kept: [kept], removed: [gone] });
});
