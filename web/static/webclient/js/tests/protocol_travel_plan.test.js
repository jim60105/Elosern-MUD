/*
 * The read-only route preview's exact result slot (wilderness-travel-planning-ui):
 * a successful `travel.plan` result carries exactly the planner's data, and
 * every malformed or partial plan rejects at the result envelope itself.
 * Synthetic plans only.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { actionResult } = require("./protocol_support.js");

const step = (x, stage = "normal", seconds = 1200) => ({ cell: { x, y: 4 }, seconds, fatigue_stage: stage });

function plan(overrides = {}) {
  return {
    origin: { x: 0, y: 4 },
    destination: { x: 3, y: 4 },
    steps: [step(1), step(2, "light"), step(3, "forced_sleep", 900)],
    total_seconds: 3300,
    nightfall_index: 1,
    stop_index: 2,
    stop_reason: "member_asleep",
    ...overrides,
  };
}

const result = (data, extra = {}) => actionResult({ code: "travel.plan", ...(data === undefined ? {} : { data }), ...extra });

test("a travel.plan success keeps its exact planner slot", () => {
  assert.deepEqual(Protocol.validateActionResult(result(plan())).data, plan());
  // A pace stop may precede nightfall; the indices are independent.
  assert.equal(Protocol.validateActionResult(result(plan({ nightfall_index: 2, stop_index: 0, stop_reason: "pace_threshold" }))).data.stop_index, 0);
  // The same-cell answer: no steps, no indices, the arrival reason.
  const empty = plan({ steps: [], total_seconds: 0, nightfall_index: null, stop_index: null, stop_reason: "destination_reached" });
  assert.deepEqual(Protocol.validateActionResult(result(empty)).data.steps, []);
  // Sixty steps are the bound.
  const long = Array.from({ length: 60 }, (_, i) => step(i + 1));
  assert.equal(Protocol.validateActionResult(result(plan({ steps: long, stop_index: 59, nightfall_index: null }))).data.steps.length, 60);
});

test("a malformed travel.plan success rejects at the envelope", () => {
  const missing = plan();
  delete missing.stop_reason;
  const bad = [
    undefined,
    missing,
    { ...plan(), extra: 1 },
    plan({ origin: { x: 0 } }),
    plan({ destination: { x: 1.5, y: 0 } }),
    plan({ steps: Array.from({ length: 61 }, (_, i) => step(i + 1)), stop_index: 60, nightfall_index: null }),
    plan({ steps: [{ ...step(1), extra: true }], stop_index: 0, nightfall_index: null }),
    plan({ steps: [step(1, "weary")], stop_index: 0, nightfall_index: null }),
    plan({ steps: [step(1, "normal", -1)], stop_index: 0, nightfall_index: null }),
    plan({ total_seconds: -5 }),
    plan({ stop_index: 3 }),
    plan({ stop_index: null }),
    plan({ nightfall_index: 3 }),
    plan({ stop_reason: null }),
    plan({ stop_reason: "tired" }),
    plan({ steps: [], total_seconds: 0, nightfall_index: null, stop_index: 0, stop_reason: "destination_reached" }),
    plan({ steps: [], total_seconds: 0, nightfall_index: null, stop_index: null, stop_reason: "nightfall" }),
  ];
  for (const data of bad) {
    assert.throws(() => Protocol.validateActionResult(result(data)), undefined, JSON.stringify(data ?? "missing slot"));
  }
});

test("only the travel.plan success is bound to the planner slot", () => {
  // A refusal stays data-free under the generic rule; another code keeps the
  // generic slot.
  const refused = Protocol.validateActionResult(
    actionResult({ code: "plan_unreachable", outcome: "rejected", message: "無法抵達" })
  );
  assert.equal(refused.data, undefined);
  assert.deepEqual(Protocol.validateActionResult(actionResult({ code: "completed", data: { anything: 1 } })).data, { anything: 1 });
});
