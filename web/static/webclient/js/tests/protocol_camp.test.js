/*
 * The whole-party camp's exact result slots (wilderness-camping): a
 * successful `explore.camp_preview` or `explore.camp` result carries exactly
 * its bounded data, and every malformed sample the Python boundary refuses
 * also rejects here. Synthetic values only.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { actionResult } = require("./protocol_support.js");

const clone = (value) => JSON.parse(JSON.stringify(value));

function preview() {
  const member = {
    member_id: "7",
    name: "同伴",
    current_reserve: 180000,
    predicted_reserve: 360000,
    reserve_max: 360000,
    current_percent: 50,
    predicted_percent: 100,
    wake_tick: 900,
    wake_time: "第 1 日 06:00",
  };
  return {
    available: true,
    refusal: null,
    dream_offerable: true,
    default_mode: "until-dawn",
    current_tick: 100,
    current_time: "第 1 日 20:00",
    modes: [
      { mode: "until-dawn", available: true, refusal: null, dream_offerable: true, wake_tick: 900, wake_time: "第 1 日 06:00", members: [member] },
      {
        mode: "until-recovered",
        available: false,
        refusal: { code: "party_unavailable", message: "無法入睡。" },
        dream_offerable: false,
        wake_tick: null,
        wake_time: null,
        members: [],
      },
    ],
  };
}

function camp(overrides = {}) {
  return {
    camp_id: "a".repeat(64),
    phase: "complete",
    timing: { elapsed_seconds: 800, result_tick: 900, result_time: "第 1 日 06:00", wake_tick: 900, wake_time: "第 1 日 06:00" },
    members: [
      { member_id: "7", name: "同伴", reserve_before: 1, reserve_after: 2, reserve_max: 360000, before_percent: 0, after_percent: 0, sleeping: false, wake_tick: 900 },
    ],
    events: [{ kind: "daily_reset", due_tick: 864, interactive: false, text: null }],
    interrupted: false,
    interruption_reason: null,
    ...overrides,
  };
}

const previewResult = (data) => actionResult({ code: "explore.camp_preview", ...(data === undefined ? {} : { data }) });
const campResult = (data) => actionResult({ code: "explore.camp", ...(data === undefined ? {} : { data }) });

test("camp preview and camp successes keep their exact slots", () => {
  assert.deepEqual(Protocol.validateActionResult(previewResult(preview())).data, preview());
  assert.deepEqual(Protocol.validateActionResult(campResult(camp())).data, camp());
  const interrupted = camp({
    phase: "interrupted",
    interrupted: true,
    interruption_reason: "interactive_event",
    timing: { elapsed_seconds: 10, result_tick: 110, result_time: "第 1 日 20:10", wake_tick: null, wake_time: null },
  });
  assert.equal(Protocol.validateActionResult(campResult(interrupted)).data.interruption_reason, "interactive_event");
  const dream = camp({ phase: "dream", events: [], timing: { elapsed_seconds: 0, result_tick: 100, result_time: "x", wake_tick: null, wake_time: null } });
  assert.equal(Protocol.validateActionResult(campResult(dream)).data.phase, "dream");
  // A rejected camp carries no data at all.
  assert.equal(Protocol.validateActionResult(actionResult({ code: "explore.camp", outcome: "rejected", message: "附近有怪物。" })).data, undefined);
});

test("malformed camp preview data rejects at the envelope", () => {
  const mutations = [
    (d) => (d.extra = 1),
    (d) => (d.available = 1),
    (d) => (d.default_mode = "recovery"),
    (d) => d.modes.reverse(),
    (d) => (d.modes[1].members = [d.modes[0].members[0]]),
    (d) => (d.modes[0].refusal = { code: "x", message: "y" }),
    (d) => (d.modes[0].members[0].predicted_percent = 101),
    (d) => (d.modes[0].members[0].current_reserve = true),
    (d) => (d.available = false),
  ];
  assert.throws(() => Protocol.validateActionResult(previewResult(undefined)));
  for (const mutate of mutations) {
    const value = clone(preview());
    mutate(value);
    assert.throws(() => Protocol.validateActionResult(previewResult(value)), undefined, JSON.stringify(value));
  }
});

test("malformed camp result data rejects at the envelope", () => {
  const bad = [
    undefined,
    camp({ extra: 1 }),
    camp({ phase: "done" }),
    camp({ interrupted: true }),
    camp({ interruption_reason: "interactive_event" }),
    camp({ events: [{ kind: "x", due_tick: -1, interactive: false, text: null }] }),
    camp({ members: [{ member_id: "7" }] }),
    camp({ phase: "dream" }),
    camp({ timing: { elapsed_seconds: 1, result_tick: 1, result_time: "x", wake_tick: 5, wake_time: null } }),
    camp({ elapsed_seconds: 800 }),
  ];
  for (const value of bad) {
    assert.throws(() => Protocol.validateActionResult(campResult(value)), undefined, JSON.stringify(value));
  }
});
