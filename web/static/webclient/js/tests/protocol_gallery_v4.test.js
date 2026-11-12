/*
 * gallery v4 validator gate (change gallery-v4-validators).
 *
 * The version-4 panel carries one category at a time. Its JS mirror
 * `validateGalleryPanelV4` is exported beside v3 but NOT registered:
 * PANEL_ALLOWLIST keeps gallery at version 3 until the cutover. The Python
 * mirror (web/webclient/presentation/gallery.py::validate_gallery_v4) is
 * asserted against the same case shapes by GalleryV4ParityTests in
 * web/webclient/presentation/tests/test_gallery_panel.py.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");

const SUBJECT = "portrait:character:7001";
const IMAGE_ID = "10000000-0000-4000-8000-000000000001";
const DIGEST = "b".repeat(64);
const RECT = { x: 0.25, y: 0.06, w: 0.5, h: 0.375 };
const SIZE = { width: 768, height: 1024 };

function alpha(key = "woman") {
  return {
    kind: "alpha_mask",
    source_id: `gallery.alpha:${key}`,
    rank: 100,
    resource: {
      resource_id: `defaults/${key}.webp`,
      version: DIGEST,
      url: `/art/defaults/${key}.webp`,
      origin: "silhouette",
      geometry: { image_size: null, face_rect: RECT, stage: null, aspect_ratio: "3:4" },
    },
  };
}

function descriptor(subject = SUBJECT, imageId = IMAGE_ID) {
  const directory = subject.split(":")[1];
  const key = subject.split(":")[2];
  return {
    subject_id: `${DIGEST}:${imageId}`,
    revision: "c".repeat(64),
    generation_subject: subject,
    generation_state: "done",
    attempts: [{
      type: "image",
      source_id: `gallery.original:${imageId}`,
      rank: 10,
      resource: {
        resource_id: `gallery/${directory}/${key}/${imageId}.webp`,
        version: DIGEST,
        url: `/art/gallery/${directory}/${key}/${imageId}.webp`,
        origin: "runtime",
        geometry: { image_size: SIZE, face_rect: RECT, stage: { scale: 1, x: 0, y: 0 }, aspect_ratio: "3:4" },
      },
    }],
    terminal: alpha(),
    retention_sources: [{ source_id: `gallery.original:${imageId}`, token: DIGEST }],
  };
}

function tile(subjectKey = SUBJECT, changes = {}) {
  return {
    subject_key: subjectKey,
    kind: `portrait:${subjectKey.split(":")[1]}`,
    display_name: "夜行者",
    is_current: false,
    card_count: 1,
    artwork: descriptor(subjectKey),
    ...changes,
  };
}

function group(key, subjects, changes = {}) {
  return { key, label: null, seen: null, total: null, expanded: true, count: subjects.length, subjects, ...changes };
}

const CAPABILITIES = {
  supports_bindings: true, supports_field_selection: true, supports_free_text: true,
  supports_personal_official_preferences: true, supports_face_rect: true,
  supports_stage: true, supports_card_delete: true, max_cards: null,
};

function panel() {
  return {
    schema_version: 4, available: true, kind: "gallery",
    categories: [
      { key: "mine", count: 1, enabled: true, reason: null },
      { key: "party", count: 0, enabled: true, reason: null },
      { key: "people", count: 0, enabled: false, reason: "尚未開放" },
      { key: "monster", count: 0, enabled: true, reason: null },
      { key: "scene", count: 0, enabled: false, reason: "尚未開放" },
    ],
    category: "mine",
    groups: [group("mine", [tile(SUBJECT, { is_current: true })])],
    selected: SUBJECT,
    description: null,
    cards: [{
      image_id: IMAGE_ID, status: "card", label: "肖像", artwork: descriptor(),
      is_default: true, chips: ["預設臉框", "目前預設"], requested_fields: ["appearance"],
      binding_present: false, created_at: 100,
    }],
    official_entries: [],
    equipment_summary: {
      weapon_main: { value: null, display_name: "未裝備" },
      weapon_off: { value: null, display_name: "未裝備" },
      armor: { value: null, display_name: "未裝備" },
      accessories: { value: [], display_names: [], equipped_count: 0 },
    },
    capabilities: { ...CAPABILITIES },
    binding_warnings: [],
    error_state: null,
  };
}

function variant(modify) {
  const value = panel();
  modify(value);
  return value;
}

function empty(value, category = "party") {
  value.category = category;
  value.categories[0].count = 0;
  value.groups = [];
  Object.assign(value, {
    selected: null, description: null, cards: [], official_entries: [], binding_warnings: [],
    equipment_summary: null, capabilities: null, error_state: null,
  });
}

function subjects(value, count) {
  const rows = Array.from({ length: count }, (_, index) => tile(
    index === 0 ? SUBJECT : `portrait:character:t_${index}`,
    { is_current: index === 0, artwork: null },
  ));
  value.groups = [group("mine", rows)];
  value.categories[0].count = count;
}

const accepts = (value) => assert.doesNotThrow(() => Protocol.validateGalleryPanelV4(value));
const rejects = (value) => assert.throws(() => Protocol.validateGalleryPanelV4(value));

test("v4 is exported beside v3 and not registered", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.gallery, 3);
  assert.equal(Protocol.GALLERY_SCHEMA_VERSION, 3);
  assert.equal(Protocol.GALLERY_V4_SCHEMA_VERSION, 4);
  assert.deepEqual([...Protocol.GALLERY_CATEGORY_KEYS], ["mine", "party", "people", "monster", "scene"]);
  assert.equal(Protocol.GALLERY_MAX_PANEL_SUBJECTS, 256);
  assert.ok(Object.isFrozen(Protocol.GALLERY_CATEGORY_KEYS));
  accepts(panel());
  // Neither validator admits the other version.
  assert.throws(() => Protocol.validateGalleryPanel(panel()));
  rejects(variant((p) => { p.schema_version = 3; }));
});

test("the category list is closed, ordered, and names an enabled category", () => {
  rejects(variant((p) => { p.category = "people"; }));
  rejects(variant((p) => { p.category = ["mine"]; }));
  rejects(variant((p) => { p.categories.pop(); }));
  rejects(variant((p) => { [p.categories[1], p.categories[3]] = [p.categories[3], p.categories[1]]; }));
  rejects(variant((p) => { p.categories[1].reason = "原因"; }));
  rejects(variant((p) => { p.categories[2].reason = null; }));
  rejects(variant((p) => { p.categories[1].count = 257; }));
});

test("groups carry ordered subjects or a collapsed count", () => {
  const collapsed = (p) => {
    p.groups.push(group("place:t_hall", [], { label: "測試大廳", expanded: false, count: 7 }));
    p.categories[0].count += 7;
  };
  accepts(variant(collapsed));
  rejects(variant((p) => { p.groups[0].expanded = false; }));
  rejects(variant((p) => { p.categories[0].count = 2; }));
  rejects(variant((p) => { p.groups[0].key = "mine\n"; }));
  rejects(variant((p) => { p.groups[0].key = "Mine"; }));
  accepts(variant((p) => { Object.assign(p.groups[0], { seen: 1, total: 3 }); }));
  rejects(variant((p) => { p.groups[0].seen = 1; }));
  rejects(variant((p) => { Object.assign(p.groups[0], { seen: 4, total: 3 }); }));
  rejects(variant((p) => { p.groups[0].subjects[0].kind = "portrait:monster"; }));
  rejects(variant((p) => {
    p.groups.push(group("tier:b", [tile(SUBJECT)]));
    p.categories[0].count += 1;
  }));
  rejects(variant((p) => {
    p.groups.push(group("tier:b", [tile("portrait:monster:t_beast", { is_current: true })]));
    p.categories[0].count += 1;
  }));
});

test("selection decides the card fields", () => {
  accepts(variant((p) => empty(p)));
  rejects(variant((p) => { empty(p); p.capabilities = { ...CAPABILITIES }; }));
  rejects(variant((p) => { empty(p); p.description = "測試"; }));
  rejects(variant((p) => { p.selected = null; }));
  rejects(variant((p) => { p.capabilities = null; }));
  rejects(variant((p) => { p.selected = "portrait:character:absent"; }));
  for (const field of ["supports_face_rect", "supports_stage", "supports_card_delete"]) {
    rejects(variant((p) => { delete p.capabilities[field]; }));
    rejects(variant((p) => { p.capabilities[field] = 1; }));
  }
  accepts(variant((p) => { p.description = "景".repeat(512); }));
  rejects(variant((p) => { p.description = "景".repeat(513); }));
  rejects(variant((p) => { p.filters = { all: 1 }; }));
});

test("the subject ceiling fails closed and no frame-sized byte limit applies", () => {
  accepts(variant((p) => subjects(p, 256)));
  rejects(variant((p) => subjects(p, 257)));
  const large = variant((p) => {
    subjects(p, 256);
    p.groups[0].subjects.forEach((row) => { row.artwork = descriptor(row.subject_key); });
  });
  assert.ok(Protocol.jsonByteSize(large) > Protocol.MAX_CANONICAL_JSON_BYTES);
  accepts(large);
});

test("the client may send the v4 navigation actions", () => {
  for (const category of Protocol.GALLERY_CATEGORY_KEYS) {
    assert.deepEqual(
      Protocol.validateGalleryActionPayload("gallery.category.select", { category }),
      { category },
    );
  }
  const reject = (actionId, payload) => assert.throws(() => Protocol.validateGalleryActionPayload(actionId, payload));
  reject("gallery.category.select", { category: "pets" });
  reject("gallery.category.select", { category: "mine", subject_key: SUBJECT });
  reject("gallery.category.select", {});
  assert.deepEqual(
    Protocol.validateGalleryActionPayload("gallery.group.select", { group: "place:t_hall" }),
    { group: "place:t_hall" },
  );
  reject("gallery.group.select", { group: "Hall" });
  reject("gallery.group.select", { group: "k".repeat(97) });
  reject("gallery.group.select", { group: 7 });
  reject("gallery.group.select", { group: "a", extra: 1 });
});
