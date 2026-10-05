/*
 * roster panel v1 mirror: portraits, characters, panels, rejections.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { VALID_EPOCH, serverTime } = require("./protocol_support.js");
const { validRosterCharacter, validRosterPanel, validRosterPortrait } = require("./protocol_fixtures.js");



test("roster available form validates cleanly", () => {
  assert.deepEqual(
    Protocol.validateRosterPanel(validRosterPanel()),
    validRosterPanel()
  );
});

test("roster validator enforces exact one current row invariant", () => {
  // 0 current rows -> rejected
  const zeroCurrent = validRosterPanel({
    characters: [validRosterCharacter({ current: false })],
  });
  assert.throws(
    () => Protocol.validateRosterPanel(zeroCurrent),
    /must contain exactly one current character/
  );

  // 2 current rows -> rejected
  const twoCurrent = validRosterPanel({
    characters: [
      validRosterCharacter({ identity: 1, current: true }),
      validRosterCharacter({ identity: 2, current: true }),
    ],
  });
  assert.throws(
    () => Protocol.validateRosterPanel(twoCurrent),
    /must contain exactly one current character/
  );

  // Exactly 1 current among multiple -> accepted
  const validMultiple = validRosterPanel({
    characters: [
      validRosterCharacter({ identity: 1, current: true }),
      validRosterCharacter({ identity: 2, current: false }),
    ],
  });
  assert.doesNotThrow(() => Protocol.validateRosterPanel(validMultiple));
});

test("roster validator enforces reciprocal lock/reason invariant", () => {
  // switch_locked: false with non-null reason -> rejected
  assert.throws(
    () =>
      Protocol.validateRosterPanel(
        validRosterPanel({ switch_locked: false, lock_reason: "戰鬥中無法切換角色" })
      ),
    /lock_reason must be null when switch_locked is false/
  );

  // switch_locked: true with null reason -> rejected
  assert.throws(
    () =>
      Protocol.validateRosterPanel(
        validRosterPanel({ switch_locked: true, lock_reason: null })
      ),
    /lock_reason must be '戰鬥中無法切換角色' when switch_locked is true/
  );

  // switch_locked: true with wrong string -> rejected
  assert.throws(
    () =>
      Protocol.validateRosterPanel(
        validRosterPanel({ switch_locked: true, lock_reason: "非戰鬥原因" })
      ),
    /lock_reason must be '戰鬥中無法切換角色' when switch_locked is true/
  );

  // switch_locked: true with exact ROSTER_LOCK_REASON -> accepted
  assert.doesNotThrow(() =>
    Protocol.validateRosterPanel(
      validRosterPanel({
        switch_locked: true,
        lock_reason: "戰鬥中無法切換角色",
      })
    )
  );
});

test("roster validator mirrors server drift and bound rejections", () => {
  for (const bad of [
    validRosterPanel({ schema_version: 1 }),
    validRosterPanel({ available: false }),
    validRosterPanel({ characters: "not-a-list" }),
    // Duplicate identities
    validRosterPanel({
      characters: [
        validRosterCharacter({ identity: 1, current: true }),
        validRosterCharacter({ identity: 1, current: false }),
      ],
    }),
    // Non-ascending identities
    validRosterPanel({
      characters: [
        validRosterCharacter({ identity: 2, current: true }),
        validRosterCharacter({ identity: 1, current: false }),
      ],
    }),
    // Over row bound (11 rows)
    validRosterPanel({
      characters: Array.from({ length: 11 }, (_, i) =>
        validRosterCharacter({ identity: i + 1, current: i === 0 })
      ),
    }),
    // Invalid portrait URL prefix
    validRosterPanel({
      characters: [
        validRosterCharacter({
          portrait: validRosterPortrait({ url: "https://evil.com/pic.png" }),
        }),
      ],
    }),
    // Both URL and placeholder set
    validRosterPanel({
      characters: [
        validRosterCharacter({
          portrait: validRosterPortrait({
            url: "/art/pic.png",
            placeholder: { kind: "missing", label: "未生成" },
          }),
        }),
      ],
    }),
    // Neither URL nor placeholder set
    validRosterPanel({
      characters: [
        validRosterCharacter({
          portrait: validRosterPortrait({
            url: null,
            placeholder: null,
          }),
        }),
      ],
    }),
    // A url-bearing portrait without a face rectangle
    validRosterPanel({
      characters: [
        validRosterCharacter({
          portrait: validRosterPortrait({ face_rect: null }),
        }),
      ],
    }),
    // A face rectangle with a non-numeric coordinate
    validRosterPanel({
      characters: [
        validRosterCharacter({
          portrait: validRosterPortrait({ face_rect: { x: 0.3, y: 0.1, w: 0.4, h: "0.4" } }),
        }),
      ],
    }),
    // A coordinate outside [0, 1]
    validRosterPanel({
      characters: [
        validRosterCharacter({
          portrait: validRosterPortrait({ face_rect: { x: 0.3, y: 0.1, w: 1.4, h: 0.4 } }),
        }),
      ],
    }),
    // Invalid aspect_ratio
    validRosterPanel({
      characters: [
        validRosterCharacter({
          portrait: validRosterPortrait({ aspect_ratio: "16:9" }),
        }),
      ],
    }),
    // Non-positive identity
    validRosterPanel({
      characters: [validRosterCharacter({ identity: 0 })],
    }),
    // Empty or surrogate name
    validRosterPanel({
      characters: [validRosterCharacter({ name: "  " })],
    }),
    validRosterPanel({
      characters: [validRosterCharacter({ name: "bad\ud800name" })],
    }),
    // Extra field on panel
    validRosterPanel({ extra_field: 123 }),
  ]) {
    assert.throws(() => Protocol.validateRosterPanel(bad));
  }
});

test("roster is in the production panel allowlist and rejects atomically", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.roster, 2);
  const envelope = {
    protocol_version: 1,
    presentation_epoch: VALID_EPOCH,
    revision: 5,
    mode: "exploration",
    panels: {
      roster: { schema_version: 2, available: true, characters: "not-a-list" },
    },
    layout_version: 1,
    server_time: serverTime(),
  };
  assert.throws(() => Protocol.validateSnapshot(envelope));
  envelope.panels = { roster: validRosterPanel() };
  envelope.revision = 6;
  assert.doesNotThrow(() => Protocol.validateSnapshot(envelope));
  envelope.panels = {
    roster: {
      schema_version: 2,
      available: false,
      reason: { code: "presentation_unavailable", message: "目前無法顯示此介面" },
    },
  };
  envelope.revision = 7;
  assert.doesNotThrow(() => Protocol.validateSnapshot(envelope));
});

test("possession_banner is in the production panel allowlist and validates available/unavailable shapes", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.possession_banner, 1);
  const validAvailable = {
    schema_version: 1,
    available: true,
    host_name: "小艾",
    since_tick: 100,
  };
  assert.deepEqual(Protocol.validatePossessionBannerPanel(validAvailable), validAvailable);

  const unavailable = {
    schema_version: 1,
    available: false,
    reason: { code: "not_possessing", message: "目前未處於附身狀態" },
  };
  const envelope = {
    protocol_version: 1,
    presentation_epoch: VALID_EPOCH,
    revision: 8,
    mode: "exploration",
    panels: { possession_banner: validAvailable },
    layout_version: 1,
    server_time: serverTime(),
  };
  assert.doesNotThrow(() => Protocol.validateSnapshot(envelope));
  envelope.panels = { possession_banner: unavailable };
  envelope.revision = 9;
  assert.doesNotThrow(() => Protocol.validateSnapshot(envelope));

  assert.throws(() => Protocol.validatePossessionBannerPanel({ schema_version: 2, available: true }));
  assert.throws(() => Protocol.validatePossessionBannerPanel({ schema_version: 1, available: true, host_name: "" }));
  assert.throws(() => Protocol.validatePossessionBannerPanel({ schema_version: 1, available: true, host_name: "小艾", since_tick: -1 }));
  assert.throws(() => Protocol.validatePossessionBannerPanel({ schema_version: 1, available: true, host_name: "小艾", since_tick: 100, extra: true }));
});


// The roster row carries the art panel's own origin discriminator under the
// same coherence rules (official-art-resolution): the closed vocabulary,
// coupled to the row's own media, and never a generated status beside an
// official image. Both validator sides share the rule.
test("the roster portrait origin vocabulary is enforced", () => {
  const placeholderPortrait = (overrides) =>
    validRosterPortrait(Object.assign({
      subject_key: null, status: null, url: null, aspect_ratio: null,
      alt: "無肖像", placeholder: { kind: "unavailable", label: "無肖像" },
      face_rect: null, stage: null, origin: "placeholder",
    }, overrides));
  const panel = (portrait) =>
    validRosterPanel({ characters: [validRosterCharacter({ portrait })] });
  const accepts = {
    runtime: validRosterPortrait(),
    official: validRosterPortrait({
      subject_key: "portrait:character:42", status: null,
      url: "/art/official/" + "a".repeat(64) + "/preset/t_synth_preset/hero.webp",
      alt: "portrait:character:42", origin: "official",
    }),
    silhouette: placeholderPortrait({
      status: "missing",
      placeholder: { kind: "missing", label: "未生成" },
      origin: "silhouette",
    }),
    placeholder: placeholderPortrait(),
  };
  Object.keys(accepts).forEach((origin) => {
    assert.doesNotThrow(() => Protocol.validateRosterPanel(panel(accepts[origin])), origin);
  });
  const rejects = {
    "unknown origin": validRosterPortrait({ origin: "generated" }),
    "blank origin": validRosterPortrait({ origin: "" }),
    "official without a url": placeholderPortrait({ origin: "official" }),
    "official claiming a done portrait": validRosterPortrait({
      origin: "official",
      url: "/art/official/" + "a".repeat(64) + "/preset/t_synth_preset/hero.webp",
    }),
    "runtime without a url": placeholderPortrait({ origin: "runtime" }),
    "silhouette hiding a real url": validRosterPortrait({ origin: "silhouette" }),
  };
  Object.keys(rejects).forEach((label) => {
    assert.throws(() => Protocol.validateRosterPanel(panel(rejects[label])), label);
  });
  const absent = validRosterPortrait();
  delete absent.origin;
  assert.throws(() => Protocol.validateRosterPanel(panel(absent)), /required field origin/);
});
