/*
 * roster panel v3 mirror: portraits, characters, panels, rejections.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 *
 * v3 (change unified-portrait-image-contract) makes a row's `portrait` the
 * complete canonical artwork descriptor — the same one shape the art panel's
 * catalog entries carry — instead of a copied subset of flat image fields.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { VALID_EPOCH, serverTime } = require("./protocol_support.js");
const {
  fixtureDigest,
  validArtwork,
  validArtworkResource,
  validRosterCharacter,
  validRosterPanel,
  validRosterPortrait,
} = require("./protocol_fixtures.js");


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
  const cases = [
    validRosterPanel({ switch_locked: true, lock_reason: null }),
    validRosterPanel({ switch_locked: true, lock_reason: "other reason" }),
    validRosterPanel({ switch_locked: false, lock_reason: "戰鬥中無法切換角色" }),
  ];
  cases.forEach((bad) => assert.throws(() => Protocol.validateRosterPanel(bad)));
  assert.doesNotThrow(() =>
    Protocol.validateRosterPanel(
      validRosterPanel({ switch_locked: true, lock_reason: "戰鬥中無法切換角色" })
    )
  );
  assert.doesNotThrow(() =>
    Protocol.validateRosterPanel(validRosterPanel({ switch_locked: false, lock_reason: null }))
  );
});

test("roster validator mirrors server drift and bound rejections", () => {
  const portraitWith = (overrides) =>
    validRosterPanel({
      characters: [validRosterCharacter({ portrait: validRosterPortrait(overrides) })],
    });
  for (const bad of [
    validRosterPanel({ schema_version: 1 }),
    validRosterPanel({ schema_version: 2 }),
    validRosterPanel({ schema_version: 4 }),
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
    // The retired flat portrait object is refused outright: the row portrait
    // is the canonical descriptor, with no dual-shape adaptation.
    validRosterPanel({
      characters: [
        validRosterCharacter({
          portrait: {
            subject_key: "character:1",
            status: "done",
            url: "/art/portraits/character_1.png",
            aspect_ratio: "3:4",
            alt: "英雄肖像",
            placeholder: null,
            face_rect: { x: 0.3, y: 0.1, w: 0.4, h: 0.4 },
            stage: { scale: 1, x: 0, y: 0 },
            origin: "runtime",
          },
        }),
      ],
    }),
    // A resource URL outside the same-origin art route
    portraitWith({
      attempts: [
        {
          type: "image",
          source_id: "portrait.default:1",
          rank: 30,
          resource: validArtworkResource({ url: "https://evil.com/pic.png" }),
        },
      ],
    }),
    // A resource version that is not a digest
    portraitWith({
      attempts: [
        {
          type: "image",
          source_id: "portrait.default:1",
          rank: 30,
          resource: validArtworkResource({ version: "v1" }),
        },
      ],
    }),
    // A revision that is not a digest
    portraitWith({ revision: "nope" }),
    // An unknown generation state (the raw recorded status never rides the wire)
    portraitWith({ generation_state: "in_progress" }),
    // A face rectangle with a non-numeric coordinate
    portraitWith({
      attempts: [
        {
          type: "image",
          source_id: "portrait.default:1",
          rank: 30,
          resource: validArtworkResource({
            geometry: {
              image_size: null,
              face_rect: { x: 0.3, y: 0.1, w: 0.4, h: "0.4" },
              stage: null,
              aspect_ratio: "3:4",
            },
          }),
        },
      ],
    }),
    // A coordinate outside [0, 1]
    portraitWith({
      attempts: [
        {
          type: "image",
          source_id: "portrait.default:1",
          rank: 30,
          resource: validArtworkResource({
            geometry: {
              image_size: null,
              face_rect: { x: 0.3, y: 0.1, w: 1.4, h: 0.4 },
              stage: null,
              aspect_ratio: "3:4",
            },
          }),
        },
      ],
    }),
    // A malformed aspect-ratio token (the canonical descriptor bounds the
    // SHAPE of the token rather than pinning one ratio: the retired flat wire's
    // 3:4 pin is gone, and an official image may legitimately declare another)
    portraitWith({
      attempts: [
        {
          type: "image",
          source_id: "portrait.default:1",
          rank: 30,
          resource: validArtworkResource({
            geometry: {
              image_size: null,
              face_rect: { x: 0.3, y: 0.1, w: 0.4, h: 0.4 },
              stage: null,
              aspect_ratio: "3/4",
            },
          }),
        },
      ],
    }),
    // A terminal duplicating a candidate resource
    portraitWith({ terminal: validRosterPortrait().terminal && {
      kind: "alpha_mask",
      source_id: "portrait.alpha:man",
      rank: 100,
      resource: validArtworkResource(),
    } }),
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
  assert.equal(Protocol.PANEL_ALLOWLIST.roster, 3);
  const envelope = {
    protocol_version: 1,
    presentation_epoch: VALID_EPOCH,
    revision: 5,
    mode: "exploration",
    panels: {
      roster: { schema_version: 3, available: true, characters: "not-a-list" },
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
      schema_version: 3,
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


// The roster row's portrait is the canonical descriptor, validated by the ONE
// shared mirror, so its facts obey exactly the rules the art catalog and the
// gallery enforce: the terminal is a fallback (never a second copy of a listed
// candidate), a fault never carries a URL, an official candidate keeps its
// origin without claiming a generated state, and the pending-creation row's
// empty descriptor is a truthful no-media row.
test("the roster portrait is the complete canonical descriptor", () => {
  const panel = (portrait) =>
    validRosterPanel({ characters: [validRosterCharacter({ portrait })] });
  const attempt = (overrides) => ({
    type: "image",
    source_id: "portrait.official:preset/t_synth_preset",
    rank: 50,
    resource: validArtworkResource(
      Object.assign(
        {
          resource_id: "preset/t_synth_preset/hero.webp",
          url: "/art/official/" + "a".repeat(64) + "/preset/t_synth_preset/hero.webp",
          origin: "official",
        },
        overrides || {}
      )
    ),
  });

  const accepts = {
    // A resolved runtime candidate with its own independent generation truth.
    runtime: validRosterPortrait(),
    // The official read-only default: its own origin, and no generated state.
    official: validRosterPortrait({
      generation_subject: "portrait:character:42",
      generation_state: null,
      attempts: [attempt()],
    }),
    // An admitted subject with no real candidate: no attempt, no generated
    // subject key, and the attribute-selected alpha terminal.
    alphaOnly: validRosterPortrait({
      generation_subject: null,
      generation_state: "missing",
      attempts: [],
    }),
    // A reached fault keeps its own position and never a URL.
    faulted: validRosterPortrait({
      generation_state: "failed",
      attempts: [
        { type: "fault", source_id: "portrait.default:1", rank: 30, reason: "generated_output_missing" },
      ],
      terminal: null,
    }),
    // A pending-creation row: the EMPTY canonical descriptor.
    pendingShell: validArtwork({
      subject_id: "1",
      generation_subject: null,
      generation_state: null,
      attempts: [],
      terminal: null,
    }),
  };
  Object.keys(accepts).forEach((label) => {
    assert.doesNotThrow(() => Protocol.validateRosterPanel(panel(accepts[label])), label);
  });

  const rejects = {
    // NOTE: an official candidate beside a generated state is NOT a rejection.
    // The canonical descriptor keeps recorded generation truth independent of
    // the presented image's origin, so a subject whose own generation is done
    // while its presented image is the mounted official default is a truthful
    // row — the retired flat wire's origin/status coupling is gone.
    "a fault attempt carrying a resource": validRosterPortrait({
      attempts: [
        {
          type: "fault",
          source_id: "portrait.default:1",
          rank: 30,
          reason: "generated_output_missing",
          resource: validArtworkResource(),
        },
      ],
    }),
    "an unknown fault reason": validRosterPortrait({
      attempts: [{ type: "fault", source_id: "portrait.default:1", rank: 30, reason: "boom" }],
    }),
    "a terminal whose bytes duplicate a candidate": validRosterPortrait({
      terminal: {
        kind: "alpha_mask",
        source_id: "portrait.alpha:man",
        rank: 100,
        resource: validArtworkResource(),
      },
    }),
    "a missing terminal resource": validRosterPortrait({
      terminal: { kind: "alpha_mask", source_id: "portrait.alpha:man", rank: 100 },
    }),
    "a retention entry with a malformed token": validRosterPortrait({
      retention_sources: [{ source_id: "portrait.classic:1", token: "t" }],
    }),
    "an unknown descriptor field": validRosterPortrait({ status: "done" }),
  };
  Object.keys(rejects).forEach((label) => {
    assert.throws(() => Protocol.validateRosterPanel(panel(rejects[label])), label);
  });

  const absent = validRosterPortrait();
  delete absent.generation_subject;
  assert.throws(
    () => Protocol.validateRosterPanel(panel(absent)),
    /required field generation_subject/
  );
});
