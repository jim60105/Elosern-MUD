/*
 * character panel v9 `selected_skill`: lineage position and freeform ladder.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { validCharacterPanel } = require("./protocol_fixtures.js");


const LADDER = [
  { scale: 0.25, label: "1/4", mp_cost: 4 },
  { scale: 0.5, label: "1/2", mp_cost: 7 },
  { scale: 1, label: "1", mp_cost: 14 },
  { scale: 2, label: "2", unlock_level: 6 },
  { scale: 4, label: "4", unlock_level: 10 },
];

function selectedSkill(overrides) {
  return Object.assign(
    {
      key: "t_selected_skill",
      lineage: {
        prerequisites: [{ key: "t_parent", label: "合成前置", level: 1 }],
        next: [{ key: "t_child", label: "合成後續", min_level: 3 }],
      },
      freeform_ladder: LADDER.map(function (rung) {
        return Object.assign({}, rung);
      }),
    },
    overrides || {}
  );
}

function panel(selected) {
  return validCharacterPanel({ selected_skill: selected });
}

test("selected_skill is required, nullable, and exact", () => {
  assert.equal(Protocol.validateCharacterPanel(panel(null)).selected_skill, null);
  assert.doesNotThrow(() => Protocol.validateCharacterPanel(panel(selectedSkill())));
  const missing = validCharacterPanel();
  delete missing.selected_skill;
  assert.throws(() => Protocol.validateCharacterPanel(missing), /selected_skill/);
  assert.throws(() =>
    Protocol.validateCharacterPanel(panel(Object.assign(selectedSkill(), { extra: 1 })))
  );
  assert.throws(() =>
    Protocol.validateCharacterPanel(panel(selectedSkill({ lineage: { prerequisites: [] } })))
  );
});

test("each lineage side is bounded and typed", () => {
  const rows = function (levelField, count) {
    const list = [];
    for (let i = 0; i < count; i += 1) {
      const row = { key: "t_edge_" + i, label: "合成邊" };
      row[levelField] = 1;
      list.push(row);
    }
    return list;
  };
  for (const pair of [
    ["prerequisites", "level"],
    ["next", "min_level"],
  ]) {
    const field = pair[0];
    const levelField = pair[1];
    const over = { prerequisites: [], next: [] };
    over[field] = rows(levelField, Protocol.CHARACTER_MAX_SELECTED_LINEAGE_ROWS + 1);
    assert.throws(
      () => Protocol.validateCharacterPanel(panel(selectedSkill({ lineage: over }))),
      new RegExp(field)
    );
    const atBound = { prerequisites: [], next: [] };
    atBound[field] = rows(levelField, Protocol.CHARACTER_MAX_SELECTED_LINEAGE_ROWS);
    assert.doesNotThrow(() =>
      Protocol.validateCharacterPanel(panel(selectedSkill({ lineage: atBound })))
    );
    for (const bad of [0, -1, 1.5, "1", true]) {
      const lineage = { prerequisites: [], next: [] };
      const row = { key: "t_edge", label: "合成邊" };
      row[levelField] = bad;
      lineage[field] = [row];
      assert.throws(() =>
        Protocol.validateCharacterPanel(panel(selectedSkill({ lineage: lineage })))
      );
    }
    const wrong = levelField === "level" ? "min_level" : "level";
    const lineage = { prerequisites: [], next: [] };
    const row = { key: "t_edge", label: "合成邊" };
    row[wrong] = 1;
    lineage[field] = [row];
    assert.throws(() =>
      Protocol.validateCharacterPanel(panel(selectedSkill({ lineage: lineage })))
    );
  }
});

test("the ladder is the canonical five rungs in order", () => {
  assert.equal(
    Protocol.CHARACTER_MAX_FREEFORM_LADDER_RUNGS,
    5
  );
  const short = LADDER.slice(0, 4);
  const long = LADDER.concat([{ scale: 8, label: "8", mp_cost: 56 }]);
  const swapped = [LADDER[1], LADDER[0], LADDER[2], LADDER[3], LADDER[4]];
  const tailSwapped = [LADDER[0], LADDER[1], LADDER[2], LADDER[4], LADDER[3]];
  for (const ladder of [short, long, swapped, tailSwapped]) {
    assert.throws(() =>
      Protocol.validateCharacterPanel(panel(selectedSkill({ freeform_ladder: ladder })))
    );
  }
  const relabelled = LADDER.map(function (rung) {
    return Object.assign({}, rung);
  });
  relabelled[2].label = LADDER[1].label;
  assert.throws(() =>
    Protocol.validateCharacterPanel(panel(selectedSkill({ freeform_ladder: relabelled })))
  );
});

test("each rung carries exactly one of mp_cost and unlock_level", () => {
  const both = LADDER.map(function (rung) {
    return Object.assign({}, rung);
  });
  both[3].mp_cost = 28;
  const neither = LADDER.map(function (rung) {
    return Object.assign({}, rung);
  });
  delete neither[3].unlock_level;
  const extra = LADDER.map(function (rung) {
    return Object.assign({}, rung);
  });
  extra[0].extra = 1;
  for (const ladder of [both, neither, extra]) {
    assert.throws(
      () => Protocol.validateCharacterPanel(panel(selectedSkill({ freeform_ladder: ladder }))),
      /exactly one of mp_cost and unlock_level|unknown field/
    );
  }
});

test("costs and unlock levels are bounded; the ladder is omittable", () => {
  const free = LADDER.map(function (rung) {
    return Object.assign({}, rung);
  });
  free[0].mp_cost = 0;
  assert.doesNotThrow(() =>
    Protocol.validateCharacterPanel(panel(selectedSkill({ freeform_ladder: free })))
  );
  for (const change of [
    [0, "mp_cost", -1],
    [3, "unlock_level", 0],
    [3, "unlock_level", 1.5],
  ]) {
    const ladder = LADDER.map(function (rung) {
      return Object.assign({}, rung);
    });
    ladder[change[0]][change[1]] = change[2];
    assert.throws(() =>
      Protocol.validateCharacterPanel(panel(selectedSkill({ freeform_ladder: ladder })))
    );
  }
  const without = selectedSkill();
  delete without.freeform_ladder;
  const normalized = Protocol.validateCharacterPanel(panel(without));
  assert.equal(normalized.selected_skill.freeform_ladder, undefined);
  // Present-but-null is not the omission.
  assert.throws(() =>
    Protocol.validateCharacterPanel(panel(selectedSkill({ freeform_ladder: null })))
  );
});
