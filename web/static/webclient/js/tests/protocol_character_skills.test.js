/*
 * character panel active skill row growth facts and registry detail (v9).
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
  // registry-resolvable active skill row: identity, the six growth facts,
  // and the registry-backed detail fields.
  return {
    key: key,
    label: label,
    level: 2,
    xp_into_level: 10,
    xp_to_next_level: 40,
    capped: false,
    fresh: true,
    booked: false,
    cost: { mp: 14 },
    target_spec: "single",
    usable_out_of_combat: true,
  };
}

function bareActiveRow(key) {
  // The unregistered-key fallback: the six growth facts, zero-valued, and no
  // registry-backed detail.
  return {
    key: key,
    label: key,
    level: 0,
    xp_into_level: 0,
    xp_to_next_level: 0,
    capped: false,
    fresh: false,
    booked: false,
  };
}

test("character active skill rows require the six growth facts", () => {
  assert.doesNotThrow(() =>
    Protocol.validateCharacterActiveSkillRow(enrichedActiveRow(T_SKILL, T_SKILL_LABEL))
  );
  assert.doesNotThrow(() =>
    Protocol.validateCharacterActiveSkillRow(bareActiveRow("no_such_skill"))
  );
  // A bare {key, label} row is the retired v8 fallback shape.
  assert.throws(() =>
    Protocol.validateCharacterActiveSkillRow({ key: "no_such_skill", label: "no_such_skill" })
  );
  for (const field of [
    "level",
    "xp_into_level",
    "xp_to_next_level",
    "capped",
    "fresh",
    "booked",
  ]) {
    const row = enrichedActiveRow(T_SKILL, T_SKILL_LABEL);
    delete row[field];
    assert.throws(
      () => Protocol.validateCharacterActiveSkillRow(row),
      /missing required field/,
      field
    );
  }
  // Types and bounds are exact, and a capped row's next-level band is zero.
  assert.throws(() =>
    Protocol.validateCharacterActiveSkillRow(
      Object.assign({}, enrichedActiveRow(T_SKILL, T_SKILL_LABEL), { level: -1 })
    )
  );
  assert.throws(() =>
    Protocol.validateCharacterActiveSkillRow(
      Object.assign({}, enrichedActiveRow(T_SKILL, T_SKILL_LABEL), { fresh: "yes" })
    )
  );
  assert.throws(() =>
    Protocol.validateCharacterActiveSkillRow(
      Object.assign({}, enrichedActiveRow(T_SKILL, T_SKILL_LABEL), {
        capped: true,
        xp_to_next_level: 40,
      })
    ),
    /xp_to_next_level/
  );
  assert.doesNotThrow(() =>
    Protocol.validateCharacterActiveSkillRow(
      Object.assign({}, enrichedActiveRow(T_SKILL, T_SKILL_LABEL), {
        level: 10,
        xp_into_level: 0,
        xp_to_next_level: 0,
        capped: true,
      })
    )
  );
});

test("character active skill rows reject malformed detail and the retired ladder", () => {
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
  // v9 moves the ladder to selected_skill: a row carrying the v8 field fails
  // the exact-field contract.
  assert.throws(() =>
    Protocol.validateCharacterActiveSkillRow(
      Object.assign({}, enrichedActiveRow(T_SKILL, T_SKILL_LABEL), {
        freeform_scales: [{ scale: 1, label: "1", mp_cost: 14 }],
      })
    )
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
  const row = validated.actives[0].groups[0].skills[0];
  assert.deepEqual(row.cost, { mp: 14 });
  assert.equal(row.usable_out_of_combat, true);
  assert.equal(row.target_spec, "single");
  assert.equal(row.level, 2);
  assert.equal(row.fresh, true);
  assert.equal(row.booked, false);
  assert.equal(row.freeform_scales, undefined);
  assert.deepEqual(validated.passives[0].groups[0].skills[0], {
    key: T_PASSIVE,
    label: T_PASSIVE_LABEL,
  });
  // The passive validator still rejects a growth field on a passive row.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        passives: [
          {
            category: "enhancement",
            label: "強化",
            groups: [
              {
                group: null,
                label: null,
                skills: [
                  {
                    key: T_PASSIVE,
                    label: T_PASSIVE_LABEL,
                    level: 1,
                  },
                ],
              },
            ],
          },
        ],
      })
    )
  );
});

test("character active row parity with the Python presenter (optional detail)", () => {
  // A registry-resolvable row may omit cost/target_spec/usable_out_of_combat
  // (the presenter always emits them, but the schema keeps them optional);
  // the growth facts stay required either way.
  const optional = validCharacterPanel({
    actives: [
      {
        category: "elemental_magic",
        label: "元素魔法",
        groups: [
          {
            group: "fire",
            label: T_FIRE_LABEL,
            skills: [
              {
                key: T_SKILL,
                label: T_SKILL_LABEL,
                level: 0,
                xp_into_level: 0,
                xp_to_next_level: 50,
                capped: false,
                fresh: false,
                booked: true,
              },
            ],
          },
        ],
      },
    ],
  });
  const validated = Protocol.validateCharacterPanel(optional);
  const row = validated.actives[0].groups[0].skills[0];
  assert.equal(row.cost, undefined);
  assert.equal(row.booked, true);
});
