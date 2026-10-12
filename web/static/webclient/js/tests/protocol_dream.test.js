/*
 * dream panel v2 mirror: bounded shown experience requirements.
 *
 * The dream stage's sheet displays the server-authored requirement rows and
 * echoes them back with their version identity, so the panel contract is
 * exactly the published shape: the rows and the identity are required fields
 * of the state, and a malformed row must be refused before the sheet can
 * render — or confirm — something the authoring store could never have shown.
 * Shared fixtures live in ./protocol_support.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");

function requirement(kind, text) {
  return { kind: kind, text: text };
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
      scene_art: "",
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
  return { schema_version: 2, available: true, state: state === undefined ? dreamState() : state };
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
  assert.deepEqual(Protocol.validatePanel("dream", 2, proposed), proposed);

  const shown = dreamPanel(
    dreamState({
      requirements: [requirement("place", "合成地點")],
      requirement_version: "t_dream_session:v1",
    })
  );
  assert.deepEqual(Protocol.validatePanel("dream", 2, shown), shown);
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
      () => Protocol.validatePanel("dream", 2, dreamPanel(dreamState({ requirements: rows }))),
      undefined,
      JSON.stringify(rows)
    );
  }
  const missing = dreamState();
  delete missing.requirements;
  assert.throws(() => Protocol.validatePanel("dream", 2, dreamPanel(missing)));
  const missingVersion = dreamState();
  delete missingVersion.requirement_version;
  assert.throws(() => Protocol.validatePanel("dream", 2, dreamPanel(missingVersion)));
});

test("dream bounds the shown version identity and still refuses unknown fields", () => {
  for (const version of ["", 7, "v".repeat(129)]) {
    assert.throws(() =>
      Protocol.validatePanel(
        "dream",
        2,
        dreamPanel(dreamState({ requirement_version: version }))
      )
    );
  }
  assert.doesNotThrow(() =>
    Protocol.validatePanel(
      "dream",
      2,
      dreamPanel(
        dreamState({ requirements: [requirement("place", "合成地點")], requirement_version: "v".repeat(128) })
      )
    )
  );
  assert.throws(() =>
    Protocol.validatePanel("dream", 2, dreamPanel(dreamState({ requirement_rows: [] })))
  );
});

test("dream is in the production panel allowlist at its registered version", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.dream, 2);
  assert.throws(() => Protocol.validatePanel("dream", 3, dreamPanel()));
});
