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
  // The unavailable fixture carries the registered version (7), and the real
  // validatePanel dispatch path is exercised. The transitional character v4
  // tolerance is closed (render-equipment-breakdown-webclient): only the
  // registered version 7 is accepted on both forms.
  assert.deepEqual(
    Protocol.validatePanel(
      "character",
      Protocol.PANEL_ALLOWLIST.character,
      unavailableStatusPanel({ schema_version: 7 })
    ),
    unavailableStatusPanel({ schema_version: 7 })
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
      unavailableStatusPanel({ schema_version: 6 })
    )
  );
  assert.doesNotThrow(() => Protocol.validateCharacterPanel(validCharacterPanel()));
  // The normalized result carries the registered version 7 (not a stale 6).
  assert.equal(
    Protocol.validateCharacterPanel(validCharacterPanel()).schema_version,
    7
  );
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ extra: 1 })));
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ kind: "status" })));
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ schema_version: 1 })));
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ schema_version: 2 })));
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ schema_version: 3 })));
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ schema_version: 4 })));
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ schema_version: 5 })));
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ schema_version: 6 })));
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
  const missingIntimate = validCharacterPanel();
  delete missingIntimate.intimate;
  assert.throws(() => Protocol.validateCharacterPanel(missingIntimate));
  // The optional composed full-title row mirrors the status panel's contract.
  assert.doesNotThrow(() =>
    Protocol.validateCharacterPanel(validCharacterPanel({ full_title: "F級冒險者　南門新客" }))
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
  const unavailable = unavailableStatusPanel({ schema_version: 7 });
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
  assert.equal(store.getState().phase, "active", "the version-7 state remains committed");
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

test("character panel v5 validates the intimate status section", () => {
  // A null intimate section (no sexual-state record) is valid.
  assert.doesNotThrow(() =>
    Protocol.validateCharacterPanel(validCharacterPanel({ intimate: null }))
  );
  const intimate = {
    arousal: "中等",
    wetness: "濕潤",
    shame: "輕微",
    exposure: "低",
    climax_phase: "未達",
    climax_today: 0,
  };
  const normalized = Protocol.validateCharacterPanel(validCharacterPanel({ intimate }));
  assert.deepEqual(normalized.intimate, intimate, "a valid intimate section normalizes to itself");
  // A level outside its fixed vocabulary is rejected.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({ intimate: { ...intimate, arousal: "極高" } })
    )
  );
  // An over-long level string is rejected.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({ intimate: { ...intimate, wetness: "a".repeat(129) } })
    )
  );
  // climax_today must be a non-negative integer.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({ intimate: { ...intimate, climax_today: -1 } })
    )
  );
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({ intimate: { ...intimate, climax_today: 1.5 } })
    )
  );
  // A missing or unknown field in the intimate section is rejected.
  const missingField = { ...intimate };
  delete missingField.shame;
  assert.throws(() => Protocol.validateCharacterPanel(validCharacterPanel({ intimate: missingField })));
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({ intimate: { ...intimate, extra: 1 } })
    )
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

test("character panel v7 persona round-trips the four bounded prose keys", () => {
  const four = {
    background: "  在公會登記的新人冒險者  ",
    personality: "沉穩",
    life_story: "來自邊境的小村",
    habit: "清晨練劍",
  };
  const withPersona = Protocol.validateCharacterPanel(
    validCharacterPanel({ persona: four })
  );
  assert.deepEqual(withPersona.persona, {
    background: "在公會登記的新人冒險者",
    personality: "沉穩",
    life_story: "來自邊境的小村",
    habit: "清晨練劍",
  });
  // Each key is independently nullable and whitespace-nulling.
  const blank = Protocol.validateCharacterPanel(
    validCharacterPanel({
      persona: { background: "   ", personality: null, life_story: " 邊境 ", habit: null },
    })
  );
  assert.deepEqual(blank.persona, {
    background: null,
    personality: null,
    life_story: "邊境",
    habit: null,
  });
  // The section is exactly the four keys: structural keys never render.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        persona: { background: null, personality: null, life_story: null, habit: null, identity: {} },
      })
    ),
    /persona/
  );
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        persona: { background: null, personality: null, life_story: null },
      })
    ),
    /persona/
  );
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        persona: { background: null, personality: null, life_story: null, habit: null, extra: 1 },
      })
    ),
    /persona/
  );
  // Bound at the shared 600-code-point cap, per key.
  assert.throws(() =>
    Protocol.validateCharacterPanel(
      validCharacterPanel({
        persona: { background: null, personality: null, life_story: null, habit: "x".repeat(Protocol.CHARACTER_MAX_PERSONA + 1) },
      })
    ),
    /exceeds/
  );
});

