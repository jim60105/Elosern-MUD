/*
 * creation panel v3/v5 mirror: drafts, proposals, per-field bounds, byte gate, allowlist atomicity.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { T_DARK_LABEL, T_EARTH_LABEL, T_EL_LIGHTNING, T_FIRE_LABEL, T_ICE_LABEL, T_LIGHTNING_LABEL, T_LIGHT_LABEL, T_PRESET_A, T_PRESET_A_DISPLAY, T_PRESET_B, T_PRESET_B_DISPLAY, T_SR_COMMONER, T_SR_GALE, T_SR_LEAF, T_WATER_LABEL, T_WIND_LABEL, VALID_EPOCH, deepMerge, serverTime } = require("./protocol_support.js");

const CREATION_DIGEST = "a".repeat(64);

function alphaArtwork(subjectId, key) {
  return {
    subject_id: subjectId,
    revision: CREATION_DIGEST,
    generation_subject: null,
    generation_state: null,
    attempts: [],
    terminal: {
      kind: "alpha_mask",
      source_id: "portrait.alpha:" + key,
      rank: 100,
      resource: {
        resource_id: "defaults/" + key + ".webp",
        version: CREATION_DIGEST,
        url: "/art/defaults/" + key + ".webp",
        origin: "silhouette",
        geometry: {
          image_size: null,
          face_rect: { x: 0.35, y: 0.02, w: 0.28, h: 0.16 },
          stage: null,
          aspect_ratio: "3:4",
        },
      },
    },
    retention_sources: [],
  };
}

function presetArtwork(key, withOfficial) {
  const art = alphaArtwork("creation:preset:" + key, "woman");
  if (withOfficial) {
    art.attempts.push({
      type: "image",
      source_id: "portrait.official:preset/" + key,
      rank: 50,
      resource: {
        resource_id: "preset/" + key + "/hero.png",
        version: CREATION_DIGEST,
        url: "/art/official/" + CREATION_DIGEST + "/preset/" + key + "/hero.png",
        origin: "official",
        geometry: {
          image_size: { width: 8, height: 8 },
          face_rect: { x: 0.2, y: 0.1, w: 0.4, h: 0.5 },
          stage: { scale: 1.25, x: 0.1, y: -0.1 },
          aspect_ratio: "3:4",
        },
      },
    });
  }
  return art;
}

function silhouetteTable() {
  const bands = [
    [0, 12],
    [13, 59],
    [60, 10000],
  ];
  const keys = {
    female: ["girl", "woman", "elder"],
    male: ["boy", "man", "elder"],
    other: ["woman", "man", "elder"],
  };
  const table = [];
  ["female", "male", "other"].forEach((sex) => {
    bands.forEach((band, index) => {
      table.push({
        sex,
        apparent_age_minimum: band[0],
        apparent_age_maximum: band[1],
        artwork: alphaArtwork(
          `creation:silhouette:1:${sex}:${band[0]}:${band[1]}`,
          keys[sex][index]
        ),
      });
    });
  });
  return table;
}


function validCreationPanel(overrides) {
  const axes = Protocol.CREATION_AXES.map((axis) => ({
    axis,
    label: axis === "hp" ? "生命值" : "配點",
    explanation: "測試說明",
    minimum: 0,
    maximum: 100,
  }));
  return deepMerge(
    {
      schema_version: 7,
      available: true,
      kind: "creation",
      draft: null,
      presets: [
        {
          key: T_PRESET_A,
          display_name: T_PRESET_A_DISPLAY,
          race: "human",
          race_description: "平原族",
          subrace: T_SR_COMMONER,
          emphasis: "均衡",
          background: "旅人",
          artwork: presetArtwork(T_PRESET_A, true),
        },
        {
          key: T_PRESET_B,
          display_name: T_PRESET_B_DISPLAY,
          race: "elf",
          race_description: "林語族",
          subrace: T_SR_LEAF,
          emphasis: "守護",
          background: "護衛",
          artwork: presetArtwork(T_PRESET_B, false),
        },
      ],
      custom: {
        name: { min_length: 1, max_length: 64 },
        age: {
          age_minimum: 0,
          age_maximum: 10000,
          apparent_age_minimum: 0,
          apparent_age_maximum: 10000,
        },
        races: [
          { key: "human", display_name_zh: "平原族民", description: "平原族", subraces: [T_SR_COMMONER] },
          { key: "elf", display_name_zh: "森生林語族", description: "林語族", subraces: [T_SR_LEAF, T_SR_GALE] },
        ],
        subraces: {
          human_commoner: { display_name_zh: "竈生民", common_name_zh: "尋常竈生", specialty: "工匠" },
          fionnen: { display_name_zh: "影葉族", common_name_zh: "林影林語族", specialty: "射術" },
          ciaran: { display_name_zh: "巒族", common_name_zh: "暮窟林語族", specialty: "劍術" },
        },
        profiles: [
          { race: "human", subrace: T_SR_COMMONER, budget: 224, axes },
          { race: "elf", subrace: T_SR_LEAF, budget: 437, axes },
          { race: "elf", subrace: T_SR_GALE, budget: 437, axes },
        ],
        affinity: {
          human: {
            maximum: 2,
            elements: [
              { key: "fire", label: T_FIRE_LABEL },
              { key: "water", label: T_WATER_LABEL },
              { key: "wind", label: T_WIND_LABEL },
              { key: "earth", label: T_EARTH_LABEL },
              { key: T_EL_LIGHTNING, label: T_LIGHTNING_LABEL },
              { key: "ice", label: T_ICE_LABEL },
              { key: "light", label: T_LIGHT_LABEL },
              { key: "dark", label: T_DARK_LABEL },
            ],
          },
          beastfolk: {
            maximum: 1,
            elements: [
              { key: "fire", label: T_FIRE_LABEL },
              { key: "water", label: T_WATER_LABEL },
              { key: "wind", label: T_WIND_LABEL },
              { key: "earth", label: T_EARTH_LABEL },
              { key: T_EL_LIGHTNING, label: T_LIGHTNING_LABEL },
              { key: "ice", label: T_ICE_LABEL },
              { key: "light", label: T_LIGHT_LABEL },
              { key: "dark", label: T_DARK_LABEL },
            ],
          },
          elf: {
            maximum: 0,
            elements: [
              { key: "fire", label: T_FIRE_LABEL },
              { key: "water", label: T_WATER_LABEL },
              { key: "wind", label: T_WIND_LABEL },
              { key: "earth", label: T_EARTH_LABEL },
              { key: T_EL_LIGHTNING, label: T_LIGHTNING_LABEL },
              { key: "ice", label: T_ICE_LABEL },
              { key: "light", label: T_LIGHT_LABEL },
              { key: "dark", label: T_DARK_LABEL },
            ],
          },
        },
        sex: [
          { key: "female", label: "女性" },
          { key: "male", label: "男性" },
          { key: "other", label: "其他" },
        ],
        silhouettes: silhouetteTable(),
      },
    },
    overrides
  );
}

test("accepts a valid creation panel and the common unavailable form", () => {
  assert.doesNotThrow(() => Protocol.validateCreationPanel(validCreationPanel()));
  assert.doesNotThrow(() =>
    Protocol.validatePanel(
      "creation",
      Protocol.PANEL_ALLOWLIST.creation,
      {
        schema_version: 7,
        available: false,
        reason: { code: "creation_unavailable", message: "角色建立畫面目前無法顯示" },
      }
    )
  );
});

test("creation panel rejects malformed and unknown-node fields", () => {
  assert.throws(() => Protocol.validateCreationPanel(validCreationPanel({ extra: 1 })));
  assert.throws(() => Protocol.validateCreationPanel(validCreationPanel({ kind: "services" })));
  assert.throws(() => Protocol.validateCreationPanel(validCreationPanel({ schema_version: 1 })));
  // v4 is the pre-age-rename version and v3 the pre-sex version: hard
  // cutover, the exact gate rejects both.
  assert.throws(() => Protocol.validateCreationPanel(validCreationPanel({ schema_version: 3 })));
  assert.throws(() => Protocol.validateCreationPanel(validCreationPanel({ schema_version: 4 })));
  assert.throws(() => Protocol.validateCreationPanel(validCreationPanel({ schema_version: 5 })));
  // v6 is the pre-artwork version: the exact gate rejects it.
  assert.throws(() => Protocol.validateCreationPanel(validCreationPanel({ schema_version: 6 })));
  assert.throws(() => Protocol.validateCreationPanel(validCreationPanel({ schema_version: 2 })));
  const badDraft = validCreationPanel({ draft: { mode: "preset", stage: "custom_filled", preset_key: "x" } });
  assert.throws(() => Protocol.validateCreationPanel(badDraft));
  const personaCard = validCreationPanel();
  personaCard.presets[0].persona = "forbidden";
  assert.throws(() => Protocol.validateCreationPanel(personaCard));
  const unknownProfile = validCreationPanel();
  unknownProfile.custom.profiles[0].axes[0].axis = "luck";
  assert.throws(() => Protocol.validateCreationPanel(unknownProfile));
  const wrongAxes = validCreationPanel();
  wrongAxes.custom.profiles[0].axes = wrongAxes.custom.profiles[0].axes.slice(0, 6);
  assert.throws(() => Protocol.validateCreationPanel(wrongAxes));
});

test("creation panel enforces race display_name_zh and preset race reference", () => {
  // Missing display_name_zh
  const missingName = validCreationPanel();
  delete missingName.custom.races[0].display_name_zh;
  assert.throws(() => Protocol.validateCreationPanel(missingName));

  // Blank display_name_zh
  const blankName = validCreationPanel();
  blankName.custom.races[0].display_name_zh = "   ";
  assert.throws(() => Protocol.validateCreationPanel(blankName));

  // Preset references absent race
  const badPresetRace = validCreationPanel();
  badPresetRace.presets[0].race = "non_existent_race";
  assert.throws(() => Protocol.validateCreationPanel(badPresetRace), /non-existent race/);
});

test("creation panel v5 carries the draft persona, sex, and the proposal slot", () => {
  const customDraft = {
    mode: "custom",
    stage: "custom_filled",
    display_name: "新角色",
    age: 20,
    apparent_age: 20,
    race: "human",
    subrace: T_SR_COMMONER,
    background: null,
    allocations: { hp: 50, mp: 50, sp: 50, atk_phys: 10, agility: 10, defense: 11, magic_power: 43 },
    affinity_elements: [],
    sex: "other",
    persona: { personality: "沉穩", life_story: "來自邊境的小村", habit: "清晨練劍" },
  };
  const proposal = {
    revision: 3,
    race: "human",
    subrace: T_SR_COMMONER,
    allocations: { hp: 50, mp: 50, sp: 50, atk_phys: 10, agility: 10, defense: 11, magic_power: 43 },
    persona: { personality: "沉穩", life_story: "來自邊境的小村", habit: "清晨練劍" },
  };
  const payload = validCreationPanel({ draft: customDraft, proposal });
  const validated = Protocol.validateCreationPanel(payload);
  assert.equal(validated.schema_version, 7);
  assert.equal(validated.draft.sex, "other");
  assert.deepEqual(validated.draft.persona, customDraft.persona);
  assert.deepEqual(validated.proposal, proposal);
  // A draft with an explicit null persona is valid.
  assert.doesNotThrow(() =>
    Protocol.validateCreationPanel(
      validCreationPanel({ draft: { ...customDraft, persona: null } })
    )
  );
  // The retired concept draft shape is rejected.
  assert.throws(() =>
    Protocol.validateCreationPanel(
      validCreationPanel({
        draft: { mode: "concept", stage: "concept_filled", race: "human", subrace: T_SR_COMMONER, background: null, allocations: proposal.allocations, background_generated: true },
      })
    )
  );
  // Malformed persona blocks reject on both the draft and the proposal.
  assert.throws(() =>
    Protocol.validateCreationPanel(
      validCreationPanel({ draft: { ...customDraft, persona: { personality: "沉穩" } } })
    ),
    /persona/
  );
  assert.throws(() =>
    Protocol.validateCreationPanel(
      validCreationPanel({ draft: { ...customDraft, persona: { ...customDraft.persona, habit: "長".repeat(601) } } })
    ),
    /persona/
  );
  assert.throws(() =>
    Protocol.validateCreationPanel(
      validCreationPanel({ draft: { ...customDraft, persona: { ...customDraft.persona, personality: "  " } } })
    ),
    /persona/
  );
  // The proposal key is present-only: a null value is never legal.
  assert.throws(() =>
    Protocol.validateCreationPanel(validCreationPanel({ draft: null, proposal: null }))
  );
  // A proposal persona must be a block; a non-positive revision rejects.
  assert.throws(() =>
    Protocol.validateCreationPanel(
      validCreationPanel({ proposal: { ...proposal, persona: null } })
    ),
    /persona/
  );
  assert.throws(() =>
    Protocol.validateCreationPanel(validCreationPanel({ proposal: { ...proposal, revision: 0 } }))
  );
  assert.throws(() =>
    Protocol.validateCreationPanel(
      validCreationPanel({ proposal: { ...proposal, extra: 1 } })
    ),
    /unknown/
  );
  // A worst-case proposal (three 600-code-point fields) fits the envelope.
  const worst = validCreationPanel({
    proposal: {
      ...proposal,
      persona: { personality: "長".repeat(600), life_story: "長".repeat(600), habit: "長".repeat(600) },
    },
  });
  assert.doesNotThrow(() => Protocol.validateCreationPanel(worst));
});

test("creation proposal v3 carries the optional transient-fill keys", () => {
  const proposal = {
    revision: 3,
    race: "human",
    subrace: T_SR_COMMONER,
    allocations: { hp: 50, mp: 50, sp: 50, atk_phys: 10, agility: 10, defense: 11, magic_power: 43 },
    persona: { personality: "沉穩", life_story: "來自邊境的小村", habit: "清晨練劍" },
  };
  const fill = {
    display_name: "莉雅",
    age: 25,
    apparent_age: 22,
    background: "邊境孤女，隨商隊長大",
    affinity_elements: ["fire", "water"],
  };
  const validated = Protocol.validateCreationPanel(
    validCreationPanel({ proposal: { ...proposal, ...fill } })
  );
  assert.deepEqual(validated.proposal, { ...proposal, ...fill });
  // Absent optional keys stay absent — never null-valued copies.
  const bare = Protocol.validateCreationPanel(validCreationPanel({ proposal }));
  for (const key of Object.keys(fill)) {
    assert.ok(!(key in bare.proposal));
  }
  // A carried EMPTY affinity set (the normalized elf value) round-trips.
  const emptied = Protocol.validateCreationPanel(
    validCreationPanel({ proposal: { ...proposal, affinity_elements: [] } })
  );
  assert.deepEqual(emptied.proposal.affinity_elements, []);
  // Every transient-fill key rejects a null value.
  for (const key of Object.keys(fill)) {
    assert.throws(
      () =>
        Protocol.validateCreationPanel(
          validCreationPanel({ proposal: { ...proposal, [key]: null } })
        ),
      `proposal ${key} must not accept null`
    );
  }
  // Bound violations reject on the mirrored validator.
  const rejects = [
    { age: -1 },
    { age: 10001 },
    { age: 25.5 },
    { age: "25" },
    { age: true },
    { apparent_age: -1 },
    { display_name: "" },
    { display_name: "莉".repeat(65) },
    { background: "" },
    { background: "長".repeat(601) },
    { affinity_elements: ["fire", "water", "wind", "earth", T_EL_LIGHTNING, "ice", "light", "dark", "fire"] },
    { affinity_elements: ["wood"] },
    { affinity_elements: ["fire", "fire"] },
    { affinity_elements: "fire" },
  ];
  for (const bad of rejects) {
    assert.throws(
      () =>
        Protocol.validateCreationPanel(
          validCreationPanel({ proposal: { ...proposal, ...bad } })
        ),
      `proposal must reject ${JSON.stringify(bad)}`
    );
  }
  // The v3 all-ceilings proposal — 3×600 persona, a 600 background, a 64
  // four-byte-scalar name, both ages, and an eight-element affinity set —
  // still fits the canonical envelope.
  assert.doesNotThrow(() =>
    Protocol.validateCreationPanel(
      validCreationPanel({
        proposal: {
          ...proposal,
          persona: {
            personality: "😀".repeat(600),
            life_story: "😀".repeat(600),
            habit: "😀".repeat(600),
          },
          display_name: "😀".repeat(64),
          age: 10000,
          apparent_age: 10000,
          background: "😀".repeat(600),
          affinity_elements: ["fire", "water", "wind", "earth", T_EL_LIGHTNING, "ice", "light", "dark"],
        },
      })
    )
  );
  // Contract pin: the transient-fill prose fields are bounded NON-EMPTY
  // (1..N code points), deliberately not NON-BLANK like the persona block —
  // whitespace-only values keep passing on both mirrors.
  const blank = Protocol.validateCreationPanel(
    validCreationPanel({ proposal: { ...proposal, display_name: " ", background: "  " } })
  );
  assert.equal(blank.proposal.display_name, " ");
  assert.equal(blank.proposal.background, "  ");
});

test("creation panel enforces per-field bounds", () => {
  assert.throws(() =>
    Protocol.validateCreationPanel(validCreationPanel({ presets: [] }))
  );
  const oversizePresets = validCreationPanel();
  while (oversizePresets.presets.length < Protocol.CREATION_MAX_PRESETS + 1) {
    oversizePresets.presets.push(oversizePresets.presets[0]);
  }
  assert.throws(() => Protocol.validateCreationPanel(oversizePresets));
  const longPresetKey = validCreationPanel();
  longPresetKey.presets[0].key = "x".repeat(Protocol.CREATION_MAX_PRESET_KEY + 1);
  assert.throws(() => Protocol.validateCreationPanel(longPresetKey));
  const outOfRangeDraft = validCreationPanel({
    draft: {
      mode: "custom",
      stage: "custom_filled",
      display_name: "新角色",
      age: -1,
      apparent_age: 20,
      race: "human",
      subrace: T_SR_COMMONER,
      background: null,
      allocations: { hp: 0, mp: 0, sp: 0, atk_phys: 0, agility: 0, defense: 0, magic_power: 0 },
      persona: null,
      affinity_elements: [],
      sex: "other",
    },
  });
  assert.throws(() => Protocol.validateCreationPanel(outOfRangeDraft));
  const badAllocations = validCreationPanel({
    draft: {
      mode: "custom",
      stage: "custom_filled",
      display_name: "新角色",
      age: 20,
      apparent_age: 20,
      race: "human",
      subrace: T_SR_COMMONER,
      background: null,
      allocations: { hp: 0 },
      persona: null,
      affinity_elements: [],
      sex: "other",
    },
  });
  assert.throws(() => Protocol.validateCreationPanel(badAllocations));
  // A custom draft missing the required persona key rejects (v2 exact-set).
  const { persona, ...draftWithoutPersona } = outOfRangeDraft.draft;
  assert.throws(() =>
    Protocol.validateCreationPanel({ ...outOfRangeDraft, draft: draftWithoutPersona })
  );
});

test("custom.sex mirrors the server vocabulary and the draft gate requires it", () => {
  const base = validCreationPanel();
  const validated = Protocol.validateCreationPanel(base);
  assert.deepEqual(validated.custom.sex, [
    { key: "female", label: "女性" },
    { key: "male", label: "男性" },
    { key: "other", label: "其他" },
  ]);
  const reordered = validCreationPanel();
  reordered.custom.sex.reverse();
  assert.throws(() => Protocol.validateCreationPanel(reordered));
  const fabricated = validCreationPanel();
  fabricated.custom.sex[0] = { key: "dwarf", label: "女性" };
  assert.throws(() => Protocol.validateCreationPanel(fabricated));
  const extraField = validCreationPanel();
  extraField.custom.sex[0].default = true;
  assert.throws(() => Protocol.validateCreationPanel(extraField));
  assert.throws(() =>
    Protocol.validateCreationPanel({
      ...validCreationPanel(),
      custom: { ...validCreationPanel().custom, sex: [] },
    })
  );
  // Draft sex: required concrete member (v2-shaped drafts never validate).
  const draft = {
    mode: "custom",
    stage: "custom_filled",
    display_name: "新角色",
    age: 20,
    apparent_age: 20,
    race: "human",
    subrace: T_SR_COMMONER,
    background: null,
    allocations: { hp: 0, mp: 0, sp: 0, atk_phys: 0, agility: 0, defense: 0, magic_power: 0 },
    affinity_elements: [],
    persona: null,
    sex: "female",
  };
  const carrier = Protocol.validateCreationPanel(validCreationPanel({ draft }));
  assert.equal(carrier.draft.sex, "female");
  assert.throws(() =>
    Protocol.validateCreationPanel(
      validCreationPanel({ draft: { ...draft, sex: "nope" } })
    )
  );
  const { sex, ...draftWithoutSex } = draft;
  assert.throws(() =>
    Protocol.validateCreationPanel(validCreationPanel({ draft: draftWithoutSex }))
  );
});

test("creation v7 carries preset artwork and the custom silhouette table", () => {
  const validated = Protocol.validateCreationPanel(validCreationPanel());
  assert.equal(validated.schema_version, 7);
  const card = validated.presets[0];
  assert.equal(card.artwork.subject_id, "creation:preset:" + T_PRESET_A);
  assert.equal(card.artwork.attempts.length, 1);
  assert.equal(card.artwork.attempts[0].resource.origin, "official");
  assert.equal(card.artwork.terminal.kind, "alpha_mask");
  assert.equal(card.artwork.generation_subject, null);
  assert.equal(card.artwork.retention_sources.length, 0);
  const silhouettes = validated.custom.silhouettes;
  assert.equal(silhouettes.length, 9);
  const sexes = validated.custom.sex.map((option) => option.key);
  assert.deepEqual(
    silhouettes.map((entry) => entry.sex),
    sexes.flatMap((sex) => [sex, sex, sex])
  );
  for (const entry of silhouettes) {
    assert.deepEqual(entry.artwork.attempts, []);
    assert.equal(entry.artwork.terminal.kind, "alpha_mask");
    assert.equal(entry.artwork.generation_subject, null);
  }
});

test("creation panel rejects malformed preset artwork", () => {
  const clone = () => JSON.parse(JSON.stringify(validCreationPanel()));
  const cases = [
    ["missing artwork", (panel) => { delete panel.presets[0].artwork; }],
    ["null artwork", (panel) => { panel.presets[0].artwork = null; }],
    [
      "non same-origin url",
      (panel) => {
        panel.presets[0].artwork.attempts[0].resource.url = "https://example.invalid/art/x.png";
      },
    ],
    [
      "non-official origin",
      (panel) => {
        panel.presets[0].artwork.attempts[0].resource.origin = "runtime";
      },
    ],
    [
      "fault attempt",
      (panel) => {
        panel.presets[0].artwork.attempts.push({
          type: "fault",
          source_id: "portrait.official:preset/other",
          rank: 50,
          reason: "source_unavailable",
        });
      },
    ],
    [
      "two image attempts",
      (panel) => {
        const second = JSON.parse(JSON.stringify(panel.presets[0].artwork.attempts[0]));
        second.source_id = "portrait.official:preset/other";
        second.resource.resource_id = "preset/other/hero.png";
        panel.presets[0].artwork.attempts.push(second);
      },
    ],
    [
      "claimed generation",
      (panel) => {
        panel.presets[0].artwork.generation_subject = "portrait:character:1";
        panel.presets[0].artwork.generation_state = "pending";
      },
    ],
    [
      "retention",
      (panel) => {
        panel.presets[0].artwork.retention_sources = [
          { source_id: "portrait.official:x", token: CREATION_DIGEST },
        ];
      },
    ],
    ["missing terminal", (panel) => { panel.presets[0].artwork.terminal = null; }],
    [
      "terminal wrong route",
      (panel) => {
        panel.presets[0].artwork.terminal.resource.origin = "runtime";
        panel.presets[0].artwork.terminal.resource.url = "/art/runtime/x.png";
      },
    ],
    [
      "wrong subject id",
      (panel) => {
        panel.presets[0].artwork.subject_id = "creation:preset:another";
      },
    ],
  ];
  for (const [label, mutate] of cases) {
    const panel = clone();
    mutate(panel);
    assert.throws(() => Protocol.validateCreationPanel(panel), undefined, label);
  }
});

test("creation panel rejects malformed silhouette tables", () => {
  const clone = () => JSON.parse(JSON.stringify(validCreationPanel()));
  const cases = [
    ["empty table", (panel) => { panel.custom.silhouettes = []; }],
    [
      "over-bound table",
      (panel) => {
        panel.custom.silhouettes = panel.custom.silhouettes.concat(
          JSON.parse(JSON.stringify(panel.custom.silhouettes))
        );
      },
    ],
    ["unknown sex", (panel) => { panel.custom.silhouettes[0].sex = "dwarf"; }],
    [
      "noninteger endpoint",
      (panel) => { panel.custom.silhouettes[0].apparent_age_minimum = 1.5; },
    ],
    [
      "boolean endpoint",
      (panel) => { panel.custom.silhouettes[0].apparent_age_minimum = true; },
    ],
    [
      "reversed interval",
      (panel) => {
        panel.custom.silhouettes[0].apparent_age_minimum = 500;
        panel.custom.silhouettes[0].apparent_age_maximum = 100;
      },
    ],
    [
      "out-of-range endpoint",
      (panel) => { panel.custom.silhouettes[0].apparent_age_minimum = -1; },
    ],
    [
      "gap",
      (panel) => { panel.custom.silhouettes[0].apparent_age_maximum = 11; },
    ],
    [
      "overlap",
      (panel) => { panel.custom.silhouettes[0].apparent_age_maximum = 13; },
    ],
    [
      "extra entry field",
      (panel) => { panel.custom.silhouettes[0].extra = true; },
    ],
    [
      "missing advertised sex",
      (panel) => {
        panel.custom.silhouettes = panel.custom.silhouettes.filter(
          (entry) => entry.sex !== "male"
        );
      },
    ],
    [
      "terminal removed",
      (panel) => { panel.custom.silhouettes[0].artwork.terminal = null; },
    ],
    [
      "terminal wrong route",
      (panel) => {
        panel.custom.silhouettes[0].artwork.terminal.resource.origin = "runtime";
        panel.custom.silhouettes[0].artwork.terminal.resource.url = "/art/runtime/x.png";
      },
    ],
    [
      "attempt present",
      (panel) => {
        panel.custom.silhouettes[0].artwork.attempts.push({
          type: "fault",
          source_id: "portrait.official:preset/other",
          rank: 50,
          reason: "source_unavailable",
        });
      },
    ],
    [
      "subject id mismatch",
      (panel) => {
        panel.custom.silhouettes[0].artwork.subject_id =
          "creation:silhouette:1:male:0:12";
      },
    ],
    [
      "retention present",
      (panel) => {
        panel.custom.silhouettes[0].artwork.retention_sources = [
          { source_id: "portrait.alpha:woman", token: CREATION_DIGEST },
        ];
      },
    ],
  ];
  for (const [label, mutate] of cases) {
    const panel = clone();
    mutate(panel);
    assert.throws(() => Protocol.validateCreationPanel(panel), undefined, label);
  }
});

test("a structurally maximal realistic creation payload fits the envelope", () => {
  const payload = validCreationPanel();
  assert.ok(Protocol.jsonByteSize(payload) < Protocol.MAX_CANONICAL_JSON_BYTES / 4);
});

test("creation payload maximizing every string field fails the byte gate", () => {
  const huge = "x".repeat(Protocol.CREATION_MAX_EXPLANATION);
  const axes = Protocol.CREATION_AXES.map((axis, index) => ({
    axis,
    label: "x".repeat(Protocol.CREATION_MAX_LABEL - 1) + String(index),
    explanation: huge,
    minimum: 0,
    maximum: 10000,
  }));
  const card = {
    key: "p".repeat(Protocol.CREATION_MAX_PRESET_KEY),
    display_name: "x".repeat(Protocol.CREATION_MAX_DISPLAY_NAME),
    race: "r".repeat(Protocol.CREATION_MAX_RACE_KEY),
    race_description: "x".repeat(Protocol.CREATION_MAX_DESCRIPTION),
    subrace: "s".repeat(Protocol.CREATION_MAX_SUBRACE_KEY),
    emphasis: "x".repeat(Protocol.CREATION_MAX_EMPHASIS),
    background: "x".repeat(Protocol.CREATION_MAX_BACKGROUND),
    artwork: presetArtwork("p".repeat(Protocol.CREATION_MAX_PRESET_KEY), true),
  };
  const race = {
    key: "r".repeat(Protocol.CREATION_MAX_RACE_KEY),
    display_name_zh: "x".repeat(Protocol.CREATION_MAX_DISPLAY_NAME),
    description: "x".repeat(Protocol.CREATION_MAX_DESCRIPTION),
    subraces: Array(Protocol.CREATION_MAX_SUBRACES).fill("s".repeat(Protocol.CREATION_MAX_SUBRACE_KEY)),
  };
  const subraceEntry = {
    display_name_zh: "x".repeat(Protocol.CREATION_MAX_SPECIALTY),
    common_name_zh: "x".repeat(Protocol.CREATION_MAX_SPECIALTY),
    specialty: "x".repeat(Protocol.CREATION_MAX_SPECIALTY),
  };
  const subraces = {};
  for (let i = 0; i < Protocol.CREATION_MAX_SUBRACES; i++) {
    subraces["s" + i] = Object.assign({}, subraceEntry);
  }
  const profile = {
    race: "r".repeat(Protocol.CREATION_MAX_RACE_KEY),
    subrace: "s".repeat(Protocol.CREATION_MAX_SUBRACE_KEY),
    budget: 999999,
    axes,
  };
  const affinityElement = {
    key: "fire",
    label: "x".repeat(Protocol.CREATION_MAX_LABEL),
  };
  const affinityElements = ["fire", "water", "wind", "earth", T_EL_LIGHTNING, "ice", "light", "dark"].map(
    (key) => Object.assign({}, affinityElement, { key })
  );
  const payload = {
    schema_version: 7,
    available: true,
    kind: "creation",
    draft: null,
    presets: Array(Protocol.CREATION_MAX_PRESETS).fill(Object.assign({}, card)),
    custom: {
      name: { min_length: 1, max_length: 64 },
      age: {
        age_minimum: 0,
        age_maximum: 10000,
        apparent_age_minimum: 0,
        apparent_age_maximum: 10000,
      },
      races: Array(Protocol.CREATION_MAX_RACES).fill(Object.assign({}, race)),
      subraces,
      profiles: Array(Protocol.CREATION_MAX_PROFILES).fill(Object.assign({}, profile)),
      affinity: {
        human: { maximum: 2, elements: affinityElements },
        beastfolk: { maximum: 1, elements: affinityElements },
        elf: { maximum: 0, elements: affinityElements },
      },
      sex: Protocol.CREATION_SEX_VALUES.map((key) => ({
        key,
        label: "x".repeat(Protocol.CREATION_MAX_LABEL),
      })),
      silhouettes: silhouetteTable(),
    },
  };
  assert.ok(Protocol.jsonByteSize(payload) > Protocol.MAX_CANONICAL_JSON_BYTES);
  assert.throws(() => Protocol.validateCreationPanel(payload), /envelope/);
});

test("creation is in the production panel allowlist and a bad panel rejects atomically", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.creation, 7);
  const envelope = {
    protocol_version: 1,
    presentation_epoch: VALID_EPOCH,
    revision: 1,
    mode: "creation",
    panels: { creation: { ...validCreationPanel(), kind: "bogus" } },
    layout_version: 1,
    server_time: serverTime(),
  };
  const store = Protocol.createStore();
  store.beginTransport(1);
  const accepted = store.receive(1, "ui_snapshot", [envelope], {});
  assert.equal(accepted.accepted, false);
  assert.equal(accepted.reason, "invalid");
  assert.equal(store.getState().phase, "awaiting_initial_snapshot");
});

test("the Storybook creation fixture validates against schema 7", async () => {
  const { CREATION_PANEL_SAMPLE } = await import(
    "../../../../webclient-app/stories/fixtures/creation_panels.js"
  );
  assert.doesNotThrow(() => Protocol.validateCreationPanel(CREATION_PANEL_SAMPLE));
});

