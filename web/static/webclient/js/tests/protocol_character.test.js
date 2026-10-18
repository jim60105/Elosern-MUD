/*
 * character panel v7: schema, trait rows, skill category grouping, breakdown rows, full_title composition.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { T_ARMOR_LABEL, T_PASSIVE_LABEL, T_SWORD, snapshot, unavailableStatusPanel, validStatusPanel } = require("./protocol_support.js");
const { validCharacterPanel, validCharacterTraitRow } = require("./protocol_fixtures.js");



function characterCategoryGroup(keys) {
  return {
    category: "elemental_magic",
    label: "元素魔法",
    groups: [
      {
        group: null,
        label: null,
        skills: keys.map(function (key) {
          return { key: key, label: key };
        }),
      },
    ],
  };
}

test("validates the character panel available/unavailable discriminator", () => {
  // The unavailable fixture carries the registered version (8), and the real
  // validatePanel dispatch path is exercised. Only the registered version 8
  // is accepted on both forms.
  assert.deepEqual(
    Protocol.validatePanel(
      "character",
      Protocol.PANEL_ALLOWLIST.character,
      unavailableStatusPanel({ schema_version: 8 })
    ),
    unavailableStatusPanel({ schema_version: 8 })
  );
  assert.throws(() =>
    Protocol.validatePanel(
      "character",
      Protocol.PANEL_ALLOWLIST.character,
      unavailableStatusPanel({ schema_version: 4 })
    )
  );
  assert.throws(() =>
    Protocol.validatePanel(
      "character",
      Protocol.PANEL_ALLOWLIST.character,
      unavailableStatusPanel({ schema_version: 2 })
    )
  );
  assert.throws(() =>
    Protocol.validatePanel(
      "character",
      Protocol.PANEL_ALLOWLIST.character,
      unavailableStatusPanel({ schema_version: 5 })
    )
  );
  assert.throws(() =>
    Protocol.validatePanel(
      "character",
      Protocol.PANEL_ALLOWLIST.character,
      unavailableStatusPanel({ schema_version: 7 })
    )
  );
  assert.doesNotThrow(() => Protocol.validateCharacterPanel(validCharacterPanel()));
  // The normalized result carries the registered version 8 (not a stale 7).
  assert.equal(
    Protocol.validateCharacterPanel(validCharacterPanel()).schema_version,
    8
  );
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ extra: 1 })));
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ kind: "status" })));
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ schema_version: 1 })));
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ schema_version: 2 })));
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ schema_version: 3 })));
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ schema_version: 4 })));
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ schema_version: 5 })));
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ schema_version: 6 })));
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ schema_version: 7 })));
  // A legacy v4 trait row smuggled under version 6 rejects on the exact
  // breakdown-shape rules.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        traits: [{ key: "hp", label: "生命", current: 10, max: 10 }],
      })
    )
  );
  const missing = validCharacterPanel();
  delete missing.actives;
  assert.throws(() => Protocol.validateCharacterPanel(missing));
  const missingConditions = validCharacterPanel();
  delete missingConditions.conditions;
  assert.throws(() => Protocol.validateCharacterPanel(missingConditions));
  // The optional composed full-title row mirrors the status panel's contract.
  assert.doesNotThrow(() =>
    Protocol.validateCharacterPanel(validCharacterPanel({ full_title: "F級冒險者　苔徑新客" }))
  );
  assert.throws(() =>
    Protocol.validateCharacterPanel(validCharacterPanel({ full_title: "　" }))
  );
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        full_title: "長".repeat(Protocol.MAX_FULL_TITLE_CODE_POINTS + 1),
      })
    )
  );
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ full_title: 7 })));
});

test("a character unavailable snapshot at the registered version is accepted atomically", () => {
  const store = Protocol.createStore();
  store.beginTransport(1);
  const status = validStatusPanel();
  const unavailable = unavailableStatusPanel({ schema_version: 8 });
  const accepted = snapshot({ panels: { status: status, character: unavailable } });
  const result = store.receive(1, "ui_snapshot", [accepted], {});
  assert.equal(result.accepted, true);
  assert.deepEqual(store.getState().panels.status, status, "healthy status panel stays intact");
  assert.deepEqual(store.getState().panels.character, unavailable);

  // The identical snapshot at the stale version is rejected with no panel
  // replaced or merged: a different-but-valid status panel must not leak in.
  const differentStatus = validStatusPanel({
    actor: { name: "另一位旅人", identity: "9", location: null },
  });
  const stale = snapshot({
    panels: { status: differentStatus, character: unavailableStatusPanel({ schema_version: 2 }) },
  });
  assert.equal(store.receive(1, "ui_snapshot", [stale], {}).reason, "invalid");
  assert.equal(store.getState().phase, "active", "the version-8 state remains committed");
  assert.deepEqual(store.getState().panels.status, status, "status panel untouched");
  assert.deepEqual(store.getState().panels.character, unavailable, "character panel untouched");
});

test("enforces character D10 bounds and disguise honesty", () => {
  const overRows = new Array(Protocol.CHARACTER_MAX_TRAIT_ROWS + 1).fill(validCharacterTraitRow());
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        traits: overRows,
      })
    )
  );
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        traits: [validCharacterTraitRow(), validCharacterTraitRow()],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        traits: [validCharacterTraitRow({ current: 11, max: 10 })],
      })
    )
  );
  // Zero-maximum gauge row {current: 0, max: 0, effective: 0} is valid.
  const zeroGauge = validCharacterTraitRow({ current: 0, max: 0, effective: 0 });
  const validWithZero = validCharacterPanel({ traits: [zeroGauge] });
  const normalizedZero = Protocol.validateCharacterPanel(validWithZero);
  assert.equal(normalizedZero.traits[0].max, 0);
  assert.equal(normalizedZero.traits[0].current, 0);
  assert.equal(normalizedZero.traits[0].effective, 0);

  // Nonzero current on zero maximum rejects.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        traits: [validCharacterTraitRow({ current: 3, max: 0, effective: 0 })],
      })
    )
  );

  // Inconsistent effective vs zero maximum rejects.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        traits: [validCharacterTraitRow({ current: 0, max: 0, effective: 1 })],
      })
    )
  );
  // An inactive disguise must not carry displayed rows.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        disguise: {
          active: false,
          description: "",
          displayed: [{ key: "atk_phys", label: "攻擊", value: 12 }],
        },
      })
    )
  );
  // A wallet is a non-negative safe integer.
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ wallet: -1 })));
});

test("v5 breakdown layers validate exactly", () => {
  assert.doesNotThrow(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        traits: [
          validCharacterTraitRow({
            layers: [
              { source: "skill", name: `${T_PASSIVE_LABEL}（1/2）`, kind: "mult", amount: 1.5 },
              { source: "condition", name: "劇毒", kind: "pct", amount: -10 },
              { source: "equipment", name: T_ARMOR_LABEL, kind: "flat", amount: 8 },
            ],
          }),
        ],
      })
    )
  );
  const layerBad = (overrides) =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        traits: [
          validCharacterTraitRow({
            layers: [
              Object.assign({ source: "equipment", name: "鐵劍", kind: "flat", amount: 2 }, overrides),
            ],
          }),
        ],
      })
    );
  assert.throws(() => layerBad({ source: "innate" }));
  assert.throws(() => layerBad({ kind: "percent" }));
  assert.throws(() => layerBad({ amount: 0 }));
  assert.throws(() => layerBad({ amount: "2" }));
  assert.throws(() => layerBad({ amount: NaN }));
  assert.throws(() => layerBad({ amount: Infinity }));
  assert.throws(() => layerBad({ name: " " }));
  assert.throws(() => layerBad({ extra: 1 }));
  // Layer list bound and exact trait-row shape.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        traits: [
          validCharacterTraitRow({
            layers: new Array(17).fill({ source: "equipment", name: "鐵劍", kind: "flat", amount: 2 }),
          }),
        ],
      })
    )
  );
  const missingLayerField = { source: "equipment", name: "鐵劍", kind: "flat" };
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({ traits: [validCharacterTraitRow({ layers: [missingLayerField] })] })
    )
  );
  // Fractional totals ride as JSON numbers (scaled rule-table grants).
  assert.doesNotThrow(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        traits: [validCharacterTraitRow({ key: "defense", label: "防禦", base: 5, current: 7.5, max: null, effective: 7.5 })],
      })
    )
  );
  // The defining row contract: statics expose effective through current;
  // gauges carry effective == max. Contradictions reject.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        traits: [validCharacterTraitRow({ key: "atk_phys", label: "攻擊", base: 10, current: 10, max: null, effective: 15 })],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        traits: [validCharacterTraitRow({ key: "hp", label: "生命", base: 100, current: 40, max: 115, effective: 100 })],
      })
    )
  );
});

test("v5 equipment rows require the adjustment summary", () => {
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        equipment: [{ slot: "weapon_main", item_key: T_SWORD, display_name: "鐵劍" }],
      })
    )
  );
  assert.doesNotThrow(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        equipment: [{ slot: "weapon_main", item_key: T_SWORD, display_name: "鐵劍", adjustment: "" }],
      })
    )
  );
});

test("character panel v8 validates the ordered condition rows", () => {
  const rows = [
    {
      code: "t_buff",
      label: "合成增益",
      severity: "beneficial",
      remaining_seconds: 30,
      modifiers: {},
      source: "狀態",
    },
    {
      code: "t_rule",
      label: "合成警告",
      severity: "warning",
      remaining_seconds: null,
      modifiers: { agility: "-10%", defense: -2 },
      source: "裝備",
    },
  ];
  const normalized = Protocol.validateCharacterPanel(
    validCharacterPanel({ conditions: rows })
  );
  assert.deepEqual(normalized.conditions, rows, "rows normalize to themselves");
  // Exactly six fields per row; unknown and missing keys reject.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({ conditions: [{ ...rows[0], extra: 1 }] })
    )
  );
  const missing = { ...rows[0] };
  delete missing.source;
  assert.throws(() =>
    Protocol.validateCharacterPanel(validCharacterPanel({ conditions: [missing] }))
  );
  // Severity is the shared condition vocabulary, never a polarity word.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({ conditions: [{ ...rows[0], severity: "buff" }] })
    )
  );
  // remaining_seconds is null or a non-negative integer.
  for (const bad of [-1, 1.5, "30", true, Protocol.MAX_SAFE_INTEGER + 1]) {
    assert.throws(() =>
      Protocol.validateCharacterPanel(
        validCharacterPanel({ conditions: [{ ...rows[0], remaining_seconds: bad }] })
      )
    );
  }
  // The origin is a member of the closed vocabulary, never free prose.
  for (const bad of ["", "altar", "裝備來源"]) {
    assert.throws(() =>
      Protocol.validateCharacterPanel(
        validCharacterPanel({ conditions: [{ ...rows[0], source: bad }] })
      )
    );
  }
  // A modifier value is a finite number or a bounded percentage string.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({ conditions: [{ ...rows[0], modifiers: { defense: true } }] })
    )
  );
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({ conditions: [{ ...rows[0], modifiers: { defense: "  " } }] })
    )
  );
  // The row and modifier-key counts are bounded.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        conditions: Array(Protocol.CHARACTER_MAX_CONDITIONS + 1).fill(rows[0]),
      })
    )
  );
  const wideModifiers = {};
  for (let i = 0; i <= Protocol.CHARACTER_MAX_MODIFIER_KEYS; i += 1) {
    wideModifiers["key_" + i] = 1;
  }
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({ conditions: [{ ...rows[0], modifiers: wideModifiers }] })
    )
  );
});

test("character panel v8 carries member_id and drops persona/intimate", () => {
  assert.equal(
    Protocol.validateCharacterPanel(validCharacterPanel()).member_id,
    101
  );
  for (const bad of [0, -1, true, 1.5, "101", null]) {
    assert.throws(() =>
      Protocol.validateCharacterPanel(validCharacterPanel({ member_id: bad }))
    );
  }
  // Persona prose and intimate state moved to `party_member`: the exact-field
  // contract rejects both keys outright.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        persona: { background: null, personality: null, life_story: null, habit: null },
      })
    )
  );
  assert.throws(() =>
    Protocol.validateCharacterPanel(validCharacterPanel({ intimate: null }))
  );
});

test("character panel v3 validates the category-grouped skill shape", () => {
  // The null group/label pair must be consistent.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        passives: [
          {
            category: "enhancement",
            label: "強化",
            groups: [
              { group: "g", label: null, skills: [] },
            ],
          },
        ],
      })
    )
  );
  // A category group must carry a non-empty groups list.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        passives: [{ category: "enhancement", label: "強化", groups: [] }],
      })
    )
  );
  // Category-group count is bounded by the SkillCategory member count plus
  // the synthetic fallback slot; seven groups (six real categories plus the
  // "unknown" fallback) must stay acceptable, eight must not.
  assert.doesNotThrow(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        actives: Array(Protocol.CHARACTER_MAX_CATEGORY_GROUPS).fill(
          characterCategoryGroup([])
        ),
      })
    )
  );
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        actives: Array(Protocol.CHARACTER_MAX_CATEGORY_GROUPS + 1).fill(
          characterCategoryGroup([])
        ),
      })
    )
  );
  // The flattened row bound applies, not the category-group count.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        passives: [
          characterCategoryGroup(
            Array(Protocol.CHARACTER_MAX_PASSIVE_ROWS + 1).fill("skill")
          ),
        ],
      })
    )
  );
  assert.doesNotThrow(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        passives: [
          characterCategoryGroup(
            Array(Protocol.CHARACTER_MAX_PASSIVE_ROWS / 2).fill("skill")
          ),
          {
            category: "enhancement",
            label: "強化",
            groups: [
              {
                group: null,
                label: null,
                skills: Array(Protocol.CHARACTER_MAX_PASSIVE_ROWS / 2)
                  .fill("skill")
                  .map(function (key, index) {
                    return { key: "skill_" + index, label: "技能" };
                  }),
              },
            ],
          },
        ],
      })
    )
  );
});



