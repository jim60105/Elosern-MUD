/*
 * dream panel v3 mirror: bounded shown experience requirements and the
 * canonical scene descriptor.
 *
 * The dream stage's sheet displays the server-authored requirement rows and
 * echoes them back with their version identity, so the panel contract is
 * exactly the published shape: the rows and the identity are required fields
 * of the state, and a malformed row must be refused before the sheet can
 * render — or confirm — something the authoring store could never have shown.
 * The stage's artwork is the SAME canonical scene descriptor every other scene
 * surface carries (the shared artwork validator owns its facts), so the retired
 * raw-URL shape is refused instead of adapted.
 * Shared fixtures live in ./protocol_support.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");

function requirement(kind, text) {
  return { kind: kind, text: text };
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
      can_confirm: true,
      can_draft: true,
      can_awaken: true,
      pending: false,
      open: true,
      confirmed: false,
      failure: false,
      opening: "合成白色夢境",
      scene: "合成場景描述",
      dialogue: "合成對話",
      scene_art: dreamDescriptor(),
      direction_parts: ["合成方向"],
      thread_choices: [],
      draft_preferences: null,
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
      requirements: [],
      requirement_version: null,
    },
    overrides || {}
  );
}

function dreamPanel(state) {
  return { schema_version: 3, available: true, state: state === undefined ? dreamState() : state };
}

test("dream accepts the published requirement rows with and without an identity", () => {
  const proposed = dreamPanel(
    dreamState({
      requirements: [
        requirement("place", "合成地點"),
        requirement("new_character", "合成角色"),
        requirement("private_commission", "合成委託"),
      ],
      requirement_version: null,
    })
  );
  // A proposal the store has not persisted yet is a legal published shape.
  assert.deepEqual(Protocol.validatePanel("dream", 3, proposed), proposed);

  const shown = dreamPanel(
    dreamState({
      requirements: [requirement("place", "合成地點")],
      requirement_version: "t_dream_session:v1",
    })
  );
  assert.deepEqual(Protocol.validatePanel("dream", 3, shown), shown);
});

test("dream requires the requirement fields and an exact row shape", () => {
  for (const rows of [
    [requirement("explode", "合成地點")],
    [requirement("place", "")],
    [requirement("place", "   ")],
    [{ kind: "place" }],
    [{ kind: "place", text: "合成地點", extra: "x" }],
    [requirement("place", "長".repeat(201))],
    [requirement("place", "合成地點")].concat(
      Array.from({ length: 8 }, () => requirement("place", "合成地點"))
    ),
    "not-a-list",
  ]) {
    assert.throws(
      () => Protocol.validatePanel("dream", 3, dreamPanel(dreamState({ requirements: rows }))),
      undefined,
      JSON.stringify(rows)
    );
  }
  const missing = dreamState();
  delete missing.requirements;
  assert.throws(() => Protocol.validatePanel("dream", 3, dreamPanel(missing)));
  const missingVersion = dreamState();
  delete missingVersion.requirement_version;
  assert.throws(() => Protocol.validatePanel("dream", 3, dreamPanel(missingVersion)));
});

test("dream bounds the shown version identity and still refuses unknown fields", () => {
  for (const version of ["", 7, "v".repeat(129)]) {
    assert.throws(() =>
      Protocol.validatePanel(
        "dream",
        3,
        dreamPanel(dreamState({ requirement_version: version }))
      )
    );
  }
  assert.doesNotThrow(() =>
    Protocol.validatePanel(
      "dream",
      3,
      dreamPanel(
        dreamState({ requirements: [requirement("place", "合成地點")], requirement_version: "v".repeat(128) })
      )
    )
  );
  assert.throws(() =>
    Protocol.validatePanel("dream", 3, dreamPanel(dreamState({ requirement_rows: [] })))
  );
});

test("dream is in the production panel allowlist at its registered version", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.dream, 3);
  assert.throws(() => Protocol.validatePanel("dream", 2, dreamPanel()));
});

test("dream carries the canonical scene descriptor and refuses the retired raw URL", () => {
  const descriptor = dreamDescriptor();
  const panel = dreamPanel(dreamState({ scene_art: descriptor }));
  assert.deepEqual(Protocol.validatePanel("dream", 3, panel), panel);
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
  assert.doesNotThrow(() => Protocol.validatePanel("dream", 3, dreamPanel(dreamState({ scene_art: refused }))));

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
      Protocol.validatePanel("dream", 3, dreamPanel(dreamState({ scene_art: retired })))
    );
  }
});
