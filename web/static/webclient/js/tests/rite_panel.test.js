// rite v1 validator (landmark-rite-panel): the mirror of
// web.webclient.presentation.rite — the exact available form, every bound, and
// the whole-panel byte ceiling, routed through the envelope's panel table.
"use strict";

var test = require("node:test");
var assert = require("node:assert/strict");

var Protocol = require("../elosern/protocol.js");

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

var VALID = {
  schema_version: 1,
  available: true,
  kind: "rite",
  district: { key: "t_district", name: "測試丘陵", landmark: "測試碑", lit: false },
  guardian: { name: "測試守護", form: "測試形體" },
  art: null,
  options: [
    { key: "solo", label: "獨自", companion: false },
    { key: "shared", label: "共行", companion: true },
  ],
  performers: [
    { member_id: null, name: "測試主角", owner: true },
    { member_id: 7, name: "測試同伴", owner: false },
  ],
  delivery: null,
  seen: [],
};

var DELIVERY = {
  kind: "formal",
  delivery_id: "rite:t_district:shared:150",
  scene_id: "t_rite.shared.watch",
  scene_revision: "r1",
  actor_name: "測試同伴",
  guardian_name: "測試守護",
  lines: [
    { kind: "narration", text: "測試旁觀敘述。" },
    { kind: "speech", speaker: "actor", text: "測試同伴之語。" },
    { kind: "speech", speaker: "host", text: "測試守護對測試同伴說話。" },
  ],
};

function validate(payload) {
  return Protocol.validatePanel("rite", 1, payload);
}

test("the valid panel and its delivery are accepted at version one", function () {
  var plain = clone(VALID);
  assert.equal(validate(plain), plain);

  var withDelivery = clone(VALID);
  withDelivery.delivery = clone(DELIVERY);
  withDelivery.seen = ["shared"];
  assert.equal(validate(withDelivery), withDelivery);

  assert.equal(Protocol.RITE_SCHEMA_VERSION, 1);
  assert.equal(Protocol.PANEL_ALLOWLIST.rite, 1);
  assert.equal(typeof Protocol.validateRitePanel, "function");
});

test("one mutation per bound rejects the whole panel", function () {
  var mutations = [
    function (p) { p.extra = 1; },
    function (p) { delete p.seen; },
    function (p) { p.schema_version = 2; },
    function (p) { p.available = false; },
    function (p) { p.available = 1; },
    function (p) { p.kind = "camp"; },
    function (p) { p.district.extra = 1; },
    function (p) { p.district.key = "測試"; },
    function (p) { p.district.key = ""; },
    function (p) { p.district.name = "  "; },
    function (p) { p.district.lit = "false"; },
    function (p) { p.guardian.extra = 1; },
    function (p) { p.guardian.name = " "; },
    function (p) { p.guardian.form = new Array(202).join("形"); },
    function (p) { p.art = { subject_id: "t_subject" }; },
    function (p) { p.options = []; },
    function (p) {
      p.options.push({ key: "third", label: "第三", companion: false });
      p.options.push({ key: "fourth", label: "第四", companion: false });
    },
    function (p) { p.options[1].key = "solo"; },
    function (p) { p.options[0].key = "Solo"; },
    function (p) { p.options[0].key = "solo\n"; },
    function (p) { p.options[0].label = "  "; },
    function (p) { p.options[1].companion = 1; },
    function (p) { p.performers = []; },
    function (p) { p.performers[0].member_id = 7; },
    function (p) { p.performers[1].member_id = null; },
    function (p) { p.performers[1].member_id = 0; },
    function (p) { p.performers[1].member_id = true; },
    function (p) { p.performers.push({ member_id: 7, name: "測試路人", owner: false }); },
    function (p) { p.performers[1].owner = true; },
    function (p) {
      p.performers = [{ member_id: null, name: "測試主角", owner: true }];
      for (var i = 1; i < 17; i += 1) {
        p.performers.push({ member_id: i, name: "測試同伴", owner: false });
      }
    },
    function (p) { p.seen = ["other"]; },
    function (p) { p.seen = ["solo", "solo"]; },
    function (p) { p.seen = ["solo", "shared", "solo", "shared"]; },
    function (p) {
      p.delivery = clone(DELIVERY);
      p.delivery.kind = "informal";
    },
    function (p) {
      p.delivery = clone(DELIVERY);
      p.delivery.lines = [];
    },
    function (p) {
      p.delivery = clone(DELIVERY);
      p.delivery.lines[1].speaker = "narrator";
    },
    function (p) {
      p.delivery = clone(DELIVERY);
      p.delivery.lines[0].speaker = "actor";
    },
    function (p) {
      p.delivery = clone(DELIVERY);
      p.delivery.lines[0].text = "";
    },
    function (p) {
      p.delivery = clone(DELIVERY);
      p.delivery.lines[0].text = new Array(2002).join("字");
    },
    function (p) {
      p.delivery = clone(DELIVERY);
      p.delivery.scene_id = new Array(98).join("a");
    },
    function (p) {
      p.delivery = clone(DELIVERY);
      p.delivery.revision = "r1";
    },
  ];

  mutations.forEach(function (mutate, index) {
    var payload = clone(VALID);
    mutate(payload);
    assert.throws(function () { validate(payload); }, "mutation " + index);
  });
});

test("the canonical byte ceiling rejects an oversize panel", function () {
  var heavy = clone(VALID);
  heavy.delivery = clone(DELIVERY);
  heavy.delivery.lines = [];
  for (var index = 0; index < 32; index += 1) {
    heavy.delivery.lines.push({
      kind: "narration",
      text: new Array(2001).join("字"),
    });
  }
  assert.throws(function () { validate(heavy); });
});