/*
 * art panel v3 mirror: allowlist, available payloads, malformed rejection, media-url bound.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 *
 * v3 (change unified-portrait-image-contract) replaces the flat catalog entry
 * with exactly `{artwork, context}` — the canonical artwork descriptor plus its
 * bounded display context — and leaves the scene block untouched until its own
 * separately versioned cutover.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { T_SCENE, T_SCENE_LABEL, deepMerge } = require("./protocol_support.js");
const {
  fixtureDigest,
  validArtCatalogEntry,
  validArtwork,
  validArtworkResource,
  validArtworkTerminal,
  validRosterCharacter,
  validRosterPanel,
  validRosterPortrait,
} = require("./protocol_fixtures.js");


// One canonical scene descriptor (the mirrored vocabulary of
// ``world.art.descriptors`` + ``web.webclient.presentation.artwork``): the
// generated archetype artwork ahead of the required bundled illustration, with
// the generated source authorized for retention. A scene resource carries no
// face rectangle and no placement triple.
function validSceneResource(overrides) {
  const version = fixtureDigest("scene-output");
  return deepMerge(
    {
      resource_id: `scene/${T_SCENE}.png`,
      version,
      url: `/art/scene/${T_SCENE}.png?v=${version}`,
      origin: "runtime",
      geometry: { image_size: null, face_rect: null, stage: null, aspect_ratio: null },
    },
    overrides
  );
}

function validBundledResource(overrides) {
  const fingerprint = fixtureDigest(`bundled-${T_SCENE}`);
  return deepMerge(
    {
      resource_id: `bundled-scene/${T_SCENE}/${fingerprint}.webp`,
      version: fingerprint,
      url: `/art/bundled-scene/${T_SCENE}/${fingerprint}.webp`,
      origin: "bundled_official",
      geometry: { image_size: null, face_rect: null, stage: null, aspect_ratio: null },
    },
    overrides
  );
}

function validSceneDescriptor(overrides) {
  return deepMerge(
    {
      subject_id: "grid:t_fen_map:0,0",
      revision: fixtureDigest("scene-revision"),
      generation_subject: `scene:${T_SCENE}`,
      generation_state: "done",
      attempts: [
        {
          type: "image",
          source_id: `scene.generated:scene:${T_SCENE}`,
          rank: 20,
          resource: validSceneResource(),
        },
        {
          type: "image",
          source_id: `scene.bundled:${T_SCENE}`,
          rank: 40,
          resource: validBundledResource(),
        },
      ],
      terminal: {
        kind: "scene_image",
        source_id: "scene.terminal:t_terminal",
        rank: 100,
        resource: validBundledResource({
          resource_id: "bundled-scene/t_terminal/" + fixtureDigest("terminal") + ".webp",
          version: fixtureDigest("terminal"),
          url: "/art/bundled-scene/t_terminal/" + fixtureDigest("terminal") + ".webp",
        }),
      },
      retention_sources: [
        {
          source_id: `scene.generated:scene:${T_SCENE}`,
          token: fixtureDigest("scene-retention"),
        },
      ],
    },
    overrides
  );
}

function validArtScene(overrides) {
  return deepMerge(
    {
      archetype: T_SCENE,
      label: T_SCENE_LABEL,
      alt: `${T_SCENE_LABEL}場景`,
      artwork: validSceneDescriptor(),
    },
    overrides
  );
}

function validArtPanel(overrides) {
  return deepMerge(
    {
      schema_version: 4,
      available: true,
      kind: "scene",
      scene: validArtScene(),
      portrait_catalog: { "42": validArtCatalogEntry() },
    },
    overrides
  );
}

// The catalog is replaced, never deep-merged: a merged entry would silently
// regain the fields a rejection case deliberately removed.
function catalogPanel(entries) {
  const panel = validArtPanel();
  panel.portrait_catalog = entries;
  return panel;
}

test("art is in the production panel allowlist and validates the available payload", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.art, 4);
  assert.doesNotThrow(() => Protocol.validateArtPanel(validArtPanel()));
  // A pending scene keeps its own unchanged shape, and an admitted entry with
  // no real candidate still carries its complete descriptor: no image attempt,
  // no generated subject key, and the attribute-selected alpha terminal.
  const pendingScene = validArtPanel({
    scene: validArtScene({
      archetype: "t_fen_walk",
      artwork: validSceneDescriptor({
        generation_state: "pending",
        attempts: [
          {
            type: "image",
            source_id: `scene.bundled:${T_SCENE}`,
            rank: 40,
            resource: validBundledResource(),
          },
        ],
      }),
    }),
  });
  pendingScene.portrait_catalog = {
    "7": validArtCatalogEntry({
      artwork: validArtwork({
        subject_id: "7",
        generation_subject: null,
        generation_state: null,
        attempts: [],
      }),
      context: { name: "旅店主人", role: "對話對象" },
    }),
  };
  assert.doesNotThrow(() => Protocol.validateArtPanel(pendingScene));
});

test("rejects malformed art panels atomically", () => {
  assert.throws(() =>
    Protocol.validatePanel("art", Protocol.PANEL_ALLOWLIST.art, {
      schema_version: 3,
      available: false,
    })
  );
  assert.throws(() => Protocol.validateArtPanel(validArtPanel({ kind: "combat" })));
  assert.throws(() => Protocol.validateArtPanel(validArtPanel({ schema_version: 1 })));
  assert.throws(() => Protocol.validateArtPanel(validArtPanel({ schema_version: 2 })));
  assert.throws(() => Protocol.validateArtPanel(validArtPanel({ schema_version: 3 })));
  assert.throws(() => Protocol.validateArtPanel(validArtPanel({ schema_version: 5 })));
  // The retired flat catalog entry is refused outright: exactly artwork and
  // context, with no dual-shape adaptation.
  assert.throws(() =>
    Protocol.validateArtPanel(
      catalogPanel({
        "42": {
          subject_key: "portrait:character:42",
          status: "done",
          url: "/art/portrait/character/42.png",
          aspect_ratio: "3:4",
          alt: "英雄肖像",
          placeholder: null,
          face_rect: { x: 0.3, y: 0.1, w: 0.4, h: 0.4 },
          stage: { scale: 1, x: 0, y: 0 },
          origin: "runtime",
          fallback: null,
          context: { name: "艾莉亞", role: "人物" },
        },
      })
    )
  );
  // ...and so is a catalog entry that tries to keep a flat field beside them.
  assert.throws(() =>
    Protocol.validateArtPanel(
      catalogPanel({ "42": Object.assign(validArtCatalogEntry(), { url: "/art/x.png" }) })
    )
  );
  // The retired flat scene fields are refused outright: the scene is exactly
  // the archetype, the two display strings and the canonical descriptor.
  for (const [retired, value] of [
    ["url", "/art/scene/t_fen.png"],
    ["subject_key", `scene:${T_SCENE}`],
    ["status", "done"],
    ["aspect_ratio", "16:9"],
    ["stage", { scale: 1, x: 0, y: 0 }],
    ["placeholder", null],
  ]) {
    assert.throws(() =>
      Protocol.validateArtPanel(validArtPanel({ scene: validArtScene({ [retired]: value }) }))
    );
  }
  // …and a scene without its descriptor is not an available scene.
  const descriptorless = validArtPanel();
  delete descriptorless.scene.artwork;
  assert.throws(() => Protocol.validateArtPanel(descriptorless));
  // An archetype-less scene IS valid: the descriptor itself states the
  // malformed metadata and carries the permitted town terminal.
  assert.doesNotThrow(() =>
    Protocol.validateArtPanel(validArtPanel({ scene: validArtScene({ archetype: null }) }))
  );
  // A same-origin URL restriction is enforced on the scene's own resources.
  assert.throws(() =>
    Protocol.validateArtPanel(
      validArtPanel({
        scene: validArtScene({
          artwork: validSceneDescriptor({
            attempts: [
              {
                type: "image",
                source_id: `scene.generated:scene:${T_SCENE}`,
                rank: 20,
                resource: validSceneResource({ url: "https://evil.test/x.png" }),
              },
            ],
          }),
        }),
      })
    )
  );
  // Catalog keys must be opaque decimal strings.
  assert.throws(() =>
    Protocol.validateArtPanel(catalogPanel({ abc: validArtCatalogEntry() }))
  );
  // A malformed context role is rejected.
  assert.throws(() =>
    Protocol.validateArtPanel(
      catalogPanel({ "42": validArtCatalogEntry({ context: { name: "x", role: "boss" } }) })
    )
  );
});

// The descriptor facts the catalog entry now carries are validated by the ONE
// shared mirror, so a malformed descriptor is refused by the art panel exactly
// as it is by the gallery: the terminal is a fallback (never a second copy of
// a listed candidate), a fault never carries a URL, and an unranked or
// unversioned resource is not a canonical fact.
test("the catalog entry validates the complete canonical descriptor", () => {
  const panel = (entry) => catalogPanel({ "42": entry });
  const entry = (artwork) => validArtCatalogEntry({ artwork });
  assert.doesNotThrow(() => Protocol.validateArtPanel(panel(validArtCatalogEntry())));

  const rejects = {
    "a terminal duplicating a candidate resource": entry(
      validArtwork({ terminal: validArtworkTerminal({ resource: validArtworkResource() }) })
    ),
    "a fault attempt carrying a resource": entry(
      validArtwork({
        attempts: [
          {
            type: "fault",
            source_id: "portrait.default:1",
            rank: 30,
            reason: "generated_output_missing",
            resource: validArtworkResource(),
          },
        ],
      })
    ),
    "an unknown fault reason": entry(
      validArtwork({
        attempts: [{ type: "fault", source_id: "portrait.default:1", rank: 30, reason: "boom" }],
      })
    ),
    "a resource version that is not a digest": entry(
      validArtwork({
        attempts: [
          {
            type: "image",
            source_id: "portrait.default:1",
            rank: 30,
            resource: validArtworkResource({ version: "v1" }),
          },
        ],
      })
    ),
    "a revision that is not a digest": entry(validArtwork({ revision: "nope" })),
    "a resource URL outside the art route": entry(
      validArtwork({
        attempts: [
          {
            type: "image",
            source_id: "portrait.default:1",
            rank: 30,
            resource: validArtworkResource({ url: "https://evil.test/x.png" }),
          },
        ],
      })
    ),
    "an unknown resource origin": entry(
      validArtwork({
        attempts: [
          {
            type: "image",
            source_id: "portrait.default:1",
            rank: 30,
            resource: validArtworkResource({ origin: "generated" }),
          },
        ],
      })
    ),
    "an unknown generation state": entry(validArtwork({ generation_state: "in_progress" })),
    "a geometry with a fifth key": entry(
      validArtwork({
        attempts: [
          {
            type: "image",
            source_id: "portrait.default:1",
            rank: 30,
            resource: validArtworkResource({
              geometry: {
                image_size: null,
                face_rect: { x: 0.3, y: 0.1, w: 0.4, h: 0.4 },
                stage: { scale: 1, x: 0, y: 0 },
                aspect_ratio: "3:4",
                crop: "face",
              },
            }),
          },
        ],
      })
    ),
    "a face rectangle outside the unit square": entry(
      validArtwork({
        attempts: [
          {
            type: "image",
            source_id: "portrait.default:1",
            rank: 30,
            resource: validArtworkResource({
              geometry: {
                image_size: null,
                face_rect: { x: -0.1, y: 0.06, w: 0.5, h: 0.5 },
                stage: null,
                aspect_ratio: "3:4",
              },
            }),
          },
        ],
      })
    ),
    "a missing terminal resource": entry(validArtwork({ terminal: { kind: "alpha_mask", source_id: "x", rank: 100 } })),
    "an unknown terminal kind": entry(validArtwork({ terminal: validArtworkTerminal({ kind: "cover" }) })),
    "a retention entry with a malformed token": entry(
      validArtwork({ retention_sources: [{ source_id: "portrait.classic:1", token: "t" }] })
    ),
  };
  Object.keys(rejects).forEach((label) => {
    assert.throws(() => Protocol.validateArtPanel(panel(rejects[label])), label);
  });
});

test("media url bound admits the worst-case gallery identity in both mirrors", () => {
  // /art/gallery/character/<64-char key>/<uuid36>.avif = 129 chars.
  const worst = "/art/gallery/character/" + "k".repeat(64) + "/" + "0".repeat(36) + ".avif";
  assert.equal(worst.length, 129);
  const candidate = (url) =>
    validArtwork({
      attempts: [
        {
          type: "image",
          source_id: "portrait.default:1",
          rank: 30,
          resource: validArtworkResource({ url, version: fixtureDigest(url) }),
        },
      ],
    });
  assert.doesNotThrow(() =>
    Protocol.validateArtPanel(catalogPanel({ "42": validArtCatalogEntry({ artwork: candidate(worst) }) }))
  );
  const tooLong = "/art/" + "p".repeat(256 - "/art/".length + 1);
  assert.throws(() =>
    Protocol.validateArtPanel(catalogPanel({ "42": validArtCatalogEntry({ artwork: candidate(tooLong) }) }))
  );
  assert.doesNotThrow(() =>
    Protocol.validateRosterPanel(
      validRosterPanel({
        characters: [
          validRosterCharacter({ portrait: validRosterPortrait({ attempts: candidate(worst).attempts }) }),
        ],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateRosterPanel(
      validRosterPanel({
        characters: [
          validRosterCharacter({ portrait: validRosterPortrait({ attempts: candidate(tooLong).attempts }) }),
        ],
      })
    )
  );
});
