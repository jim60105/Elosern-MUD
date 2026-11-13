/*
 * dream panel v4 mirror: the two-stage wish, its bounded proposal and change
 * report, and the canonical scene descriptor.
 *
 * The dream stage's sheet displays the server-authored requirement rows and
 * echoes them back with their version identity, so the panel contract is
 * exactly the published shape: the rows and the identity are required fields
 * of the state, and a malformed row must be refused before the sheet can
 * render — or confirm — something the authoring store could never have shown.
 * v4 adds the session stage, the working proposal, the last settled change
 * report, the chosen thread and the per-stage flags; each is validated as one
 * consistent set, because a flag the stage forbids is an offer no surface may
 * make. The stage's artwork is the SAME canonical scene descriptor every other
 * scene surface carries (the shared artwork validator owns its facts), so the
 * retired raw-URL shape is refused instead of adapted.
 * Shared fixtures live in ./protocol_support.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");

function requirement(kind, text) {
  return { kind: kind, text: text };
}

// The bounded working proposal of world.narrative.dream_proposal.
function proposal(overrides) {
  return Object.assign(
    {
      summary: "合成願望：在無名港尋找鐘聲。",
      themes: ["鐘聲"],
      atmosphere: ["霧"],
      participants: ["失散的騎士"],
      emphasis: ["重逢"],
      exclusions: ["暴力"],
      requirements: [requirement("place", "無名港")],
    },
    overrides || {}
  );
}

// The change report of one settled exchange, in the applier's exact shape.
function changeReport(overrides) {
  return Object.assign(
    {
      summary: "formed",
      lists: {
        themes: { added: ["鐘聲"], removed: [] },
        atmosphere: { added: [], removed: [] },
        participants: { added: ["失散的騎士"], removed: [] },
        emphasis: { added: [], removed: [] },
        exclusions: { added: [], removed: [] },
      },
      requirements: { added: [requirement("place", "無名港")], removed: [] },
    },
    overrides || {}
  );
}

// The terminal position's scene key: this fixture is a wire-shape fixture, so
// it uses the reserved synthetic vocabulary rather than a shipped scene key.
const TERMINAL_KEY = "t_terminal_scene";

function digest(label) {
  let out = "";
  for (let i = 0; i < 64; i += 1) {
    out += "0123456789abcdef"[(label.charCodeAt(i % label.length) + i) % 16];
  }
  return out;
}

// One bundled dream illustration: the repository's own fingerprinted identity.
function bundledResource(key) {
  const fingerprint = digest("bundled-" + key);
  return {
    resource_id: "bundled-scene/" + key + "/" + fingerprint + ".webp",
    version: fingerprint,
    url: "/art/bundled-scene/" + key + "/" + fingerprint + ".webp",
    origin: "bundled_official",
    geometry: { image_size: { width: 1536, height: 864 }, face_rect: null, stage: null, aspect_ratio: null },
  };
}

// The dream stage's canonical descriptor: the optional preferred operator
// identity, the required bundled dream illustration and the distinct town
// terminal.
function dreamDescriptor(overrides) {
  const fingerprint = digest("dream-preferred");
  return Object.assign(
    {
      subject_id: "dream:1:4f0f7a4e6b2c4c8d9a1e0b7d3c5f2a60",
      revision: digest("dream-revision"),
      generation_subject: null,
      generation_state: null,
      attempts: [
        {
          type: "image",
          source_id: "scene.operator:dream_throne",
          rank: 30,
          resource: {
            resource_id: "npc/dream_goddess/dream-throne.webp",
            version: fingerprint,
            url: "/art/official/" + fingerprint + "/npc/dream_goddess/dream-throne.webp",
            origin: "official",
            geometry: { image_size: null, face_rect: null, stage: null, aspect_ratio: null },
          },
        },
        {
          type: "image",
          source_id: "scene.bundled:dream_throne",
          rank: 40,
          resource: bundledResource("dream_throne"),
        },
      ],
      terminal: {
        kind: "scene_image",
        source_id: "scene.terminal:" + TERMINAL_KEY,
        rank: 100,
        resource: bundledResource(TERMINAL_KEY),
      },
      retention_sources: [],
    },
    overrides || {}
  );
}

function dreamState(overrides) {
  return Object.assign(
    {
      session_id: "t_dream_session",
      revision: 3,
      completed: 1,
      remaining: 5,
      can_input: true,
      can_confirm: false,
      can_finalize: true,
      can_choose_thread: true,
      can_edit: false,
      can_draft: true,
      can_awaken: true,
      pending: false,
      open: true,
      confirmed: false,
      failure: false,
      drafted: false,
      opening: "合成白色夢境",
      scene: "合成場景描述",
      dialogue: "合成對話",
      scene_art: dreamDescriptor(),
      thread_choices: [],
      stage: "conversing",
      proposal: proposal(),
      changes: null,
      thread_id: null,
      track: {
        version: 1,
        completed: 1,
        pleasure: 10,
        level: "微溫",
        ordinal: 0,
        climax_phase: "未達",
        converging: false,
      },
      sleep: { tick_from: 90, tick_to: 100, requested_seconds: 10, seconds: 10, event_kinds: [] },
      ending: "",
      ending_phase: "",
    },
    overrides || {}
  );
}

function dreamPanel(state) {
  return { schema_version: 5, available: true, state: state === undefined ? dreamState() : state };
}

test("dream refuses the retired stage-3 keys and the schema-4 envelope", () => {
  for (const [key, value] of [
    ["direction_parts", ["合成方向"]],
    ["draft_preferences", null],
    ["requirements", []],
    ["requirement_version", null],
  ]) {
    assert.throws(
      () => Protocol.validatePanel("dream", 5, dreamPanel(dreamState({ [key]: value }))),
      undefined,
      key
    );
  }
  assert.throws(() => Protocol.validatePanel("dream", 5, dreamPanel(dreamState({ requirement_rows: [] }))));
  assert.throws(() => Protocol.validatePanel("dream", 4, { ...dreamPanel(), schema_version: 4 }));
  assert.throws(() => Protocol.validatePanel("dream", 5, { ...dreamPanel(), schema_version: 4 }));
});

test("dream checks the requirement rows of the proposal and of the report", () => {
  const rows = [
    requirement("place", "合成地點"),
    requirement("new_character", "合成角色"),
    requirement("private_commission", "合成委託"),
  ];
  const panel = dreamPanel(dreamState({
    proposal: proposal({ requirements: rows }),
    changes: changeReport({ requirements: { added: rows.slice(0, 1), removed: rows.slice(1) } }),
  }));
  assert.deepEqual(Protocol.validatePanel("dream", 5, panel), panel);
  for (const bad of [
    [requirement("explode", "合成地點")],
    [requirement("place", "")],
    [requirement("place", "   ")],
    [{ kind: "place" }],
    [{ kind: "place", text: "合成地點", extra: "x" }],
    [requirement("place", "長".repeat(201))],
  ]) {
    assert.throws(
      () => Protocol.validatePanel("dream", 5, dreamPanel(dreamState({ proposal: proposal({ requirements: bad }) }))),
      undefined,
      JSON.stringify(bad)
    );
    assert.throws(
      () => Protocol.validatePanel("dream", 5, dreamPanel(dreamState({
        changes: changeReport({ requirements: { added: [], removed: bad } }),
      }))),
      undefined,
      JSON.stringify(bad)
    );
  }
});

test("dream is in the production panel allowlist at its registered version", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.dream, 5);
  assert.throws(() => Protocol.validatePanel("dream", 2, dreamPanel()));
});

test("dream carries the canonical scene descriptor and refuses the retired raw URL", () => {
  const descriptor = dreamDescriptor();
  const panel = dreamPanel(dreamState({ scene_art: descriptor }));
  assert.deepEqual(Protocol.validatePanel("dream", 5, panel), panel);
  // The reachable facts a dream descriptor carries: the optional preferred
  // operator position, the required bundled illustration and the distinct
  // terminal, with no generation claim at all.
  assert.equal(descriptor.generation_subject, null);
  assert.equal(descriptor.generation_state, null);
  assert.deepEqual(
    descriptor.attempts.map((entry) => [entry.type, entry.source_id, entry.rank]),
    [
      ["image", "scene.operator:dream_throne", 30],
      ["image", "scene.bundled:dream_throne", 40],
    ]
  );
  assert.equal(descriptor.terminal.kind, "scene_image");
  assert.equal(descriptor.terminal.source_id, "scene.terminal:" + TERMINAL_KEY);

  // A reached fault names its source and reason, never a URL.
  const refused = dreamDescriptor({
    attempts: [
      {
        type: "fault",
        source_id: "scene.operator:npc/dream_goddess/dream-throne.webp",
        rank: 30,
        reason: "source_rejected",
      },
      descriptor.attempts[1],
    ],
  });
  assert.doesNotThrow(() => Protocol.validatePanel("dream", 5, dreamPanel(dreamState({ scene_art: refused }))));

  // The retired shapes and the unbounded/incorrect facts are all refused.
  for (const retired of [
    "",
    "/art/official/" + "0".repeat(64) + "/npc/dream_goddess/dream-throne.webp",
    null,
    "not-a-descriptor",
    dreamDescriptor({ attempts: [{ type: "fault", source_id: "x", rank: 30, reason: "not_a_reason" }] }),
    dreamDescriptor({ attempts: [{ type: "fault", source_id: "x".repeat(257), rank: 30, reason: "source_rejected" }] }),
  ]) {
    assert.throws(() =>
      Protocol.validatePanel("dream", 5, dreamPanel(dreamState({ scene_art: retired })))
    );
  }
});

test("dream accepts a conversing wish and a finalized one", () => {
  // Conversing: the collaborator's proposal with no report yet, free text,
  // thread choice and finalizing all offered, editing and confirmation not.
  const conversing = dreamPanel(
    dreamState({
      thread_id: "t_synthetic_thread",
      thread_choices: [{ id: "t_synthetic_thread", label: "合成已知故事" }],
    })
  );
  assert.deepEqual(Protocol.validatePanel("dream", 5, conversing), conversing);

  // Finalized: the report of the last settled exchange, editing and
  // confirmation offered, free text, thread choice and finalizing not.
  const finalized = dreamPanel(
    dreamState({
      stage: "finalized",
      can_input: false,
      can_confirm: true,
      can_finalize: false,
      can_choose_thread: false,
      can_edit: true,
      drafted: true,
      changes: changeReport(),
    })
  );
  assert.deepEqual(Protocol.validatePanel("dream", 5, finalized), finalized);
});

test("dream refuses every rule the wish stage wire states", () => {
  const cases = [];
  const push = (label, state) => cases.push([label, state]);

  // The stage itself is one of the two the lifecycle stores.
  push("unknown stage", dreamState({ stage: "wishing" }));
  const missingStage = dreamState();
  delete missingStage.stage;
  push("missing stage", missingStage);

  // The proposal is exactly the applier's bounded shape.
  push("proposal extra field", dreamState({ proposal: proposal({ rewritten: true }) }));
  const missingField = dreamState();
  delete missingField.proposal.emphasis;
  push("proposal missing field", missingField);
  push("proposal summary not text", dreamState({ proposal: proposal({ summary: 7 }) }));
  push("proposal summary over bound", dreamState({ proposal: proposal({ summary: "長".repeat(2001) }) }));
  push("proposal item blank", dreamState({ proposal: proposal({ themes: ["  "] }) }));
  push("proposal item over bound", dreamState({ proposal: proposal({ themes: ["長".repeat(201)] }) }));
  push("proposal list over bound", dreamState({
    proposal: proposal({ themes: Array.from({ length: 33 }, (_, index) => "主題" + index) }),
  }));
  push("proposal requirement text over bound", dreamState({
    proposal: proposal({ requirements: [requirement("place", "長".repeat(201))] }),
  }));
  push("proposal requirements over bound", dreamState({
    proposal: proposal({
      requirements: Array.from({ length: 9 }, (_, index) => requirement("place", "合成" + index)),
    }),
  }));
  push("proposal is not an object", dreamState({ proposal: "summary" }));

  // The report is null or the exact three-part delta.
  push("changes unknown summary", dreamState({ changes: changeReport({ summary: "rewritten" }) }));
  push("changes extra field", dreamState({ changes: changeReport({ rewritten: true }) }));
  const missingList = changeReport();
  delete missingList.lists.emphasis;
  push("changes list missing", dreamState({ changes: missingList }));
  const missingHalf = changeReport();
  delete missingHalf.lists.themes.removed;
  push("changes list half missing", dreamState({ changes: missingHalf }));
  const halfNotList = changeReport();
  halfNotList.lists.themes.added = "鐘聲";
  push("changes list half not a list", dreamState({ changes: halfNotList }));
  push("changes item blank", dreamState({
    changes: changeReport({ lists: { ...changeReport().lists, atmosphere: { added: [" "], removed: [] } } }),
  }));
  push("changes requirements over bound", dreamState({
    changes: changeReport({
      requirements: {
        added: Array.from({ length: 9 }, (_, index) => requirement("place", "合成" + index)),
        removed: [],
      },
    }),
  }));

  // The chosen thread is null or one bounded identifier.
  push("empty thread id", dreamState({ thread_id: "" }));
  push("thread id over bound", dreamState({ thread_id: "t".repeat(129) }));
  push("thread id not text", dreamState({ thread_id: 7 }));

  // Every flag is a boolean, and the stage decides which may be true.
  push("flag not boolean", dreamState({ can_finalize: "yes" }));
  push("drafted flag not boolean", dreamState({ drafted: 1 }));
  push("input while finalized", dreamState({
    stage: "finalized", can_input: true, can_confirm: true,
    can_finalize: false, can_choose_thread: false,
  }));
  push("finalize while pending", dreamState({ pending: true, can_input: false, can_finalize: true }));
  push("finalize while finalized", dreamState({
    stage: "finalized", can_finalize: true, can_confirm: true, can_choose_thread: false,
  }));
  push("thread choice while finalized", dreamState({
    stage: "finalized", can_finalize: false, can_choose_thread: true, can_confirm: true,
  }));
  push("edit while conversing", dreamState({ can_edit: true }));
  push("confirm while conversing", dreamState({ can_confirm: true }));
  push("capped but conversing", dreamState({
    completed: 6, remaining: 0, can_input: false, can_finalize: false,
  }));

  for (const [label, state] of cases) {
    assert.throws(
      () => Protocol.validatePanel("dream", 5, dreamPanel(state)),
      undefined,
      label
    );
  }
});
