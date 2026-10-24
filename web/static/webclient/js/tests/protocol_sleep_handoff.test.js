// sleep_handoff v1 validator: the exact server-owned contextual roster,
// party option, controlled receipt identity and owner decision state.
"use strict";

var test = require("node:test");
var assert = require("node:assert/strict");

var Protocol = require("../elosern/protocol.js");

function payload(overrides) {
  return Object.assign(
    {
      schema_version: 1,
      available: true,
      owner_id: 42,
      controlled_body_id: 42,
      transition_id: "42:v:1",
      selection: {
        available: true,
        rows: [
          {
            kind: "possess",
            identity: 2,
            name: "同伴",
            reserve_percent: 100,
            stage: "normal",
            label: "接手 同伴（精神儲備 100%）",
            enabled: true,
            reason: null,
          },
          {
            kind: "possess",
            identity: 3,
            name: "沉睡者",
            reserve_percent: 5,
            stage: "sleeping",
            label: "接手 沉睡者（精神儲備 5%）",
            enabled: false,
            reason: "沉睡中，無法行動",
          },
        ],
      },
      party: { label: "全員一起睡眠", enabled: true, reason: null },
      controlled_sleep: { sleep_id: "sleep-1", revision: 0 },
      owner_sleep: {
        sleep_id: "sleep-1",
        revision: 0,
        generation: 1,
        dream_pending: true,
        continuation: "none",
        continuation_available: true,
        continuation_reason: null,
      },
    },
    overrides || {},
  );
}

test("accepts the exact available v1 payload through validatePanel", function () {
  var value = payload();
  assert.equal(Protocol.validatePanel("sleep_handoff", 1, value), value);
});

test("accepts null controlled and owner blocks outside that context", function () {
  var value = payload({ controlled_sleep: null, owner_sleep: null });
  assert.equal(Protocol.validatePanel("sleep_handoff", 1, value), value);
});

test("rejects an unknown row field", function () {
  var value = payload();
  value.selection.rows[0].extra = true;
  assert.throws(function () {
    Protocol.validatePanel("sleep_handoff", 1, value);
  });
});

test("rejects a row with an invalid kind or reserve", function () {
  var kind = payload();
  kind.selection.rows[0].kind = "owner";
  assert.throws(function () {
    Protocol.validatePanel("sleep_handoff", 1, kind);
  });
  var reserve = payload();
  reserve.selection.rows[0].reserve_percent = 101;
  assert.throws(function () {
    Protocol.validatePanel("sleep_handoff", 1, reserve);
  });
});

test("rejects a contradictory continuation or missing generation", function () {
  var continuation = payload();
  continuation.owner_sleep.continuation = "unknown";
  assert.throws(function () {
    Protocol.validatePanel("sleep_handoff", 1, continuation);
  });
  var generation = payload();
  delete generation.owner_sleep.generation;
  assert.throws(function () {
    Protocol.validatePanel("sleep_handoff", 1, generation);
  });
});

test("rejects a version mismatch and overflow rows", function () {
  assert.throws(function () {
    Protocol.validatePanel("sleep_handoff", 2, payload());
  });
  var value = payload();
  value.selection.rows = new Array(17).fill(value.selection.rows[0]);
  assert.throws(function () {
    Protocol.validatePanel("sleep_handoff", 1, value);
  });
});
