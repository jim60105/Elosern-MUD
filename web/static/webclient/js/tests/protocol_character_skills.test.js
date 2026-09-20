/*
 * character panel active skill row descriptor detail.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { T_FIRE_LABEL, T_PASSIVE, T_PASSIVE_LABEL, T_SKILL, T_SKILL_LABEL } = require("./protocol_support.js");
const { validCharacterPanel } = require("./protocol_fixtures.js");


function enrichedActiveRow(key, label) {
  // Matches what Python's _serialize_active_skill_groups emits for a
  // registry-resolvable active skill row.
  return {
    key: key,
    label: label,
    cost: { mp: 14 },
    target_spec: "single",
    usable_out_of_combat: true,
    freeform_scales: [
      { scale: 0.25, label: "1/4", mp_cost: 4 },
      { scale: 0.5, label: "1/2", mp_cost: 7 },
      { scale: 1, label: "1", mp_cost: 14 },
      { scale: 2, label: "2", mp_cost: 28 },
      { scale: 4, label: "4", mp_cost: 56 },
    ],
  };
}

test("character active skill rows accept the registry-backed descriptor subset", () => {
  // A Python-serialized enriched active row validates, and a bare
  // {key, label} row (the unregistered-key fallback shape) still validates.
  assert.doesNotThrow(() =>
    Protocol.validateCharacterActiveSkillRow(enrichedActiveRow(T_SKILL, T_SKILL_LABEL))
  );
  assert.doesNotThrow(() =>
    Protocol.validateCharacterActiveSkillRow({ key: "no_such_skill", label: "no_such_skill" })
  );
  // Malformed detail fields fail closed.
  assert.throws(() =>
    Protocol.validateCharacterActiveSkillRow(
      Object.assign({}, enrichedActiveRow(T_SKILL, T_SKILL_LABEL), { target_spec: "wild" })
    ),
    /target_spec/
  );
  assert.throws(() =>
    Protocol.validateCharacterActiveSkillRow(
      Object.assign({}, enrichedActiveRow(T_SKILL, T_SKILL_LABEL), { usable_out_of_combat: "yes" })
    ),
    /boolean/
  );
  assert.throws(() =>
    Protocol.validateCharacterActiveSkillRow(
      Object.assign({}, enrichedActiveRow(T_SKILL, T_SKILL_LABEL), { cost: { mp: -1 } })
    ),
    /within/
  );
});

test("character panel wires active and passive rows through their distinct validators", () => {
  // The live-client regression guard: a full character payload carrying an
  // enriched active row and a bare passive row must pass validateCharacterPanel.
  const payload = validCharacterPanel({
    actives: [
      {
        category: "elemental_magic",
        label: "元素魔法",
        groups: [
          {
            group: "fire",
            label: T_FIRE_LABEL,
            skills: [enrichedActiveRow(T_SKILL, T_SKILL_LABEL)],
          },
        ],
      },
    ],
  });
  const validated = Protocol.validateCharacterPanel(payload);
  assert.deepEqual(validated.actives[0].groups[0].skills[0].cost, { mp: 14 });
  assert.equal(validated.actives[0].groups[0].skills[0].usable_out_of_combat, true);
  assert.equal(validated.actives[0].groups[0].skills[0].target_spec, "single");
  assert.equal(validated.actives[0].groups[0].skills[0].freeform_scales.length, 5);
  assert.deepEqual(validated.passives[0].groups[0].skills[0], {
    key: T_PASSIVE,
    label: T_PASSIVE_LABEL,
  });
  // A freeform_scales entry whose mp_cost does not match the deterministic
  // scaling of the base cost is rejected.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        actives: [
          {
            category: "elemental_magic",
            label: "元素魔法",
            groups: [
              {
                group: "fire",
                label: T_FIRE_LABEL,
                skills: [
                  Object.assign({}, enrichedActiveRow(T_SKILL, T_SKILL_LABEL), {
                    freeform_scales: [
                      { scale: 0.25, label: "1/4", mp_cost: 99 },
                      { scale: 0.5, label: "1/2", mp_cost: 7 },
                      { scale: 1, label: "1", mp_cost: 14 },
                      { scale: 2, label: "2", mp_cost: 28 },
                      { scale: 4, label: "4", mp_cost: 56 },
                    ],
                  }),
                ],
              },
            ],
          },
        ],
      })
    ),
    /inconsistent/
  );
});

test("character active row parity with the Python presenter (nullable fields, mp=0)", () => {
  // A present-but-null freeform_scales is accepted and omitted from the
  // normalized row (mirrors Python's field omission).
  const nullScales = validCharacterPanel({
    actives: [
      {
        category: "elemental_magic",
        label: "元素魔法",
        groups: [
          {
            group: "fire",
            label: T_FIRE_LABEL,
            skills: [Object.assign({}, enrichedActiveRow(T_SKILL, T_SKILL_LABEL), { freeform_scales: null })],
          },
        ],
      },
    ],
  });
  const validated = Protocol.validateCharacterPanel(nullScales);
  const row = validated.actives[0].groups[0].skills[0];
  assert.equal(row.freeform_scales, undefined, "null freeform_scales is omitted");
  assert.deepEqual(row.cost, { mp: 14 });

  // cost {mp: 0} with freeform_scales present fails closed on both ends.
  const zeroMp = validCharacterPanel({
    actives: [
      {
        category: "elemental_magic",
        label: "元素魔法",
        groups: [
          {
            group: "fire",
            label: T_FIRE_LABEL,
            skills: [
              Object.assign({}, enrichedActiveRow(T_SKILL, T_SKILL_LABEL), { cost: { mp: 0 } }),
            ],
          },
        ],
      },
    ],
  });
  assert.throws(
    () => Protocol.validateCharacterPanel(zeroMp),
    /a skill without an mp cost cannot carry freeform_scales/
  );
});

