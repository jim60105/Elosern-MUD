// travel_log v1 validator (wilderness-travel-log-ui): the mirror of
// web.webclient.presentation.travel_log — the exact closed kind/params union,
// its field bounds and the independent count and byte ceilings.
"use strict";

var test = require("node:test");
var assert = require("node:assert/strict");

var Protocol = require("../elosern/protocol.js");

var VALID = {
  region_entered: { name: "甲原" },
  woodland_entered: { name: "甲原" },
  ford_crossed: { name: "甲原" },
  hostile_sighted: { name: "灰狼", count: 2, threat: null },
  landmark_sighted: { name: null, bearing: "東北", distance_km: 4 },
  landmark_reached: { arrival_node: "wild:elosern:1:2", name: "合成塔", lit_district: "合成塔", prose: "塔。", artwork: null },
  fatigue_stage: { member_id: "7", name: "伊蓮", stage: "light", label: "微倦" },
  dusk: {},
  nightfall: {},
  camp_result: { summary: "一夜無事。" },
  look: { prose: "草原。\n<b>風</b>" },
};

function entry(kind, params, overrides) {
  return Object.assign(
    { id: "x:1.0", kind: kind, tick: 90000, day: 2, time: "01:00", text: "一則旅途紀錄。", params: params },
    overrides || {}
  );
}

function panel(entries) {
  return { schema_version: 1, available: true, entries: entries };
}

function validate(payload) {
  return Protocol.validatePanel("travel_log", 1, payload);
}

test("every kind adopts exactly its params", function () {
  Object.keys(VALID).forEach(function (kind) {
    var payload = panel([entry(kind, JSON.parse(JSON.stringify(VALID[kind])))]);
    assert.equal(validate(payload), payload);
  });
  assert.deepEqual(Protocol.TRAVEL_LOG_SCHEMA_VERSION, 1);
});

test("extra or missing kind-specific fields reject", function () {
  Object.keys(VALID).forEach(function (kind) {
    var extra = Object.assign({}, VALID[kind], { source: "hidden" });
    assert.throws(function () { validate(panel([entry(kind, extra)])); }, kind + " extra");
    var keys = Object.keys(VALID[kind]);
    if (keys.length) {
      var missing = Object.assign({}, VALID[kind]);
      delete missing[keys[0]];
      assert.throws(function () { validate(panel([entry(kind, missing)])); }, kind + " missing");
    }
  });
});

test("malformed entries reject the whole batch", function () {
  var cases = [
    entry("camp_started", {}),
    entry("dusk", {}, { text: "  " }),
    entry("dusk", {}, { id: "甲" }),
    entry("dusk", {}, { id: new Array(82).join("x") }),
    entry("dusk", {}, { extra: 1 }),
    entry("hostile_sighted", Object.assign({}, VALID.hostile_sighted, { count: 0 })),
    entry("fatigue_stage", Object.assign({}, VALID.fatigue_stage, { stage: "tired" })),
    entry("landmark_reached", Object.assign({}, VALID.landmark_reached, { arrival_node: "合成塔" })),
    entry("region_entered", { name: null }),
    entry("look", { prose: new Array(2051).join("字") }),
  ];
  cases.forEach(function (bad, index) {
    assert.throws(function () { validate(panel([bad])); }, "case " + index);
  });
  assert.throws(function () { validate(panel([entry("dusk", {}), entry("dusk", {})])); }, "duplicate id");
  assert.throws(function () { validate(Object.assign(panel([]), { cursor: 1 })); }, "extra top-level");
});

test("count and byte ceilings hold independently of field bounds", function () {
  var many = [];
  for (var i = 0; i < 65; i += 1) many.push(entry("dusk", {}, { id: "x:1." + i }));
  assert.throws(function () { validate(panel(many)); });
  var heavy = [];
  for (var j = 0; j < 40; j += 1) heavy.push(entry("look", { prose: new Array(2001).join("字") }, { id: "x:1." + j }));
  assert.throws(function () { validate(panel(heavy)); });
});
