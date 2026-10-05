/*
 * art panel v1 mirror: allowlist, available payloads, malformed rejection, media-url bound.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { T_SCENE, T_SCENE_LABEL, deepMerge } = require("./protocol_support.js");
const { validRosterCharacter, validRosterPanel, validRosterPortrait } = require("./protocol_fixtures.js");


function validArtScene(overrides) {
  return deepMerge(
    {
      archetype: T_SCENE,
      stage: { scale: 1, x: 0, y: 0 },
      label: T_SCENE_LABEL,
      subject_key: `scene:${T_SCENE}`,
      status: "done",
      url: `/art/scene/${T_SCENE}.png`,
      aspect_ratio: "16:9",
      alt: `${T_SCENE_LABEL}場景`,
      placeholder: null,
    },
    overrides
  );
}

function validArtCatalogEntry(overrides) {
  return deepMerge(
    {
      subject_key: "portrait:monster:low",
      status: "done",
      url: "/art/portrait/monster/low.png",
      aspect_ratio: "3:4",
      alt: "低階魔物",
      placeholder: null,
      face_rect: { x: 0.25, y: 0.06, w: 0.5, h: 0.5 },
      stage: { scale: 1, x: 0, y: 0 },
      origin: "runtime",
      // The decorative built-in silhouette the server resolved: it rides
      // beside the real fields and never fills them
      // (builtin-silhouette-stage-fallback).
      fallback: {
        key: "monster_anon",
        url: "/art/defaults/monster_anon.webp",
        face_rect: { x: 0.3403, y: 0.02, w: 0.3194, h: 0.18 },
      },
      context: { name: "哥布林", role: "敵方" },
    },
    overrides
  );
}

function validArtPanel(overrides) {
  return deepMerge(
    {
      schema_version: 2,
      available: true,
      kind: "scene",
      scene: validArtScene(),
      portrait_catalog: { "42": validArtCatalogEntry() },
    },
    overrides
  );
}

test("art is in the production panel allowlist and validates the available payload", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.art, 2);
  assert.doesNotThrow(() => Protocol.validateArtPanel(validArtPanel()));
  assert.doesNotThrow(() =>
    Protocol.validateArtPanel(
      validArtPanel({
        scene: validArtScene({
          archetype: "t_fen_walk",
          status: "pending",
          url: null,
          stage: null,
          placeholder: { kind: "missing", label: "未生成" },
        }),
        portrait_catalog: {
          "7": validArtCatalogEntry({
            subject_key: null,
            status: null,
            url: null,
            aspect_ratio: null,
            face_rect: null,
            stage: null,
            origin: "silhouette",
            placeholder: { kind: "unavailable", label: "無法提供" },
            context: { name: "旅店主人", role: "對話對象" },
          }),
        },
      })
    )
  );
});

test("rejects malformed art panels atomically", () => {
  assert.throws(() =>
    Protocol.validatePanel("art", Protocol.PANEL_ALLOWLIST.art, {
      schema_version: 2,
      available: false,
    })
  );
  assert.throws(() => Protocol.validateArtPanel(validArtPanel({ kind: "combat" })));
  assert.throws(() => Protocol.validateArtPanel(validArtPanel({ schema_version: 1 })));
  assert.throws(() => Protocol.validateArtPanel(validArtPanel({ schema_version: 3 })));
  // v2: the face rectangle exists exactly when the entry carries a media URL.
  assert.throws(() =>
    Protocol.validateArtPanel(
      validArtPanel({ portrait_catalog: { "42": validArtCatalogEntry({ face_rect: null }) } })
    )
  );
  assert.throws(() =>
    Protocol.validateArtPanel(
      validArtPanel({
        portrait_catalog: {
          "42": validArtCatalogEntry({
            url: null,
            stage: null,
            origin: "silhouette",
            placeholder: { kind: "unavailable", label: "無法提供" },
          }),
        },
      })
    )
  );
  assert.throws(() =>
    Protocol.validateArtPanel(
      validArtPanel({
        portrait_catalog: {
          "42": validArtCatalogEntry({ face_rect: { x: 0.25, y: 0.06, w: 0.5, h: null } }),
        },
      })
    )
  );
  assert.throws(() =>
    Protocol.validateArtPanel(
      validArtPanel({
        portrait_catalog: {
          "42": validArtCatalogEntry({ face_rect: { x: -0.1, y: 0.06, w: 0.5, h: 0.5 } }),
        },
      })
    )
  );
  // A pending scene without a placeholder is untruthful.
  assert.throws(() =>
    Protocol.validateArtPanel(
      validArtPanel({
        scene: validArtScene({ status: "pending", url: null, placeholder: null }),
      })
    )
  );
  // A done scene must not carry a placeholder.
  assert.throws(() =>
    Protocol.validateArtPanel(
      validArtPanel({ scene: validArtScene({ placeholder: { kind: "missing", label: "未生成" } }) })
    )
  );
  // A same-origin URL restriction is enforced.
  assert.throws(() =>
    Protocol.validateArtPanel(
      validArtPanel({ scene: validArtScene({ url: "https://evil.test/x.png" }) })
    )
  );
  // Catalog keys must be opaque decimal strings.
  assert.throws(() =>
    Protocol.validateArtPanel(validArtPanel({ portrait_catalog: { abc: validArtCatalogEntry() } }))
  );
  // A malformed context role is rejected.
  assert.throws(() =>
    Protocol.validateArtPanel(
      validArtPanel({ portrait_catalog: { "42": validArtCatalogEntry({ context: { name: "x", role: "boss" } }) } })
    )
  );
});

// The portrait origin vocabulary and the decorative fallback reference are
// mirrored on both validator sides (builtin-silhouette-stage-fallback): a
// payload that names a silhouette without carrying its identity, hides a real
// URL behind a silhouette origin, or fills a fallback from the wrong route is
// rejected here exactly as the Python validator rejects it.
test("the catalog origin vocabulary and its decorative fallback are enforced", () => {
  const rect = { x: 0.3576, y: 0.03, w: 0.2847, h: 0.16 };
  const panel = (entry) => validArtPanel({ portrait_catalog: { "42": entry } });
  const placeholder = { kind: "unavailable", label: "無法提供" };
  const accepts = {
    runtime: validArtCatalogEntry(),
    silhouette: validArtCatalogEntry({
      subject_key: null, status: "missing", url: null, aspect_ratio: null,
      face_rect: null, stage: null, origin: "silhouette",
      placeholder, fallback: { key: "woman", url: "/art/defaults/woman.webp", face_rect: rect },
    }),
    placeholder: validArtCatalogEntry({
      subject_key: null, status: null, url: null, aspect_ratio: null,
      face_rect: null, stage: null, origin: "placeholder",
      placeholder, fallback: null,
    }),
  };
  Object.keys(accepts).forEach((origin) => {
    assert.doesNotThrow(() => Protocol.validateArtPanel(panel(accepts[origin])), origin);
  });
  const absentOrigin = validArtCatalogEntry();
  delete absentOrigin.origin;
  const silhouetteEntry = (overrides) =>
    validArtCatalogEntry(Object.assign({
      subject_key: null, status: "missing", url: null, aspect_ratio: null,
      face_rect: null, stage: null, origin: "silhouette", placeholder,
      fallback: { key: "woman", url: "/art/defaults/woman.webp", face_rect: rect },
    }, overrides));
  const rejects = {
    "unknown origin": validArtCatalogEntry({ origin: "official" }),
    "missing origin": absentOrigin,
    "silhouette hiding a real url": validArtCatalogEntry({ origin: "silhouette" }),
    "placeholder carrying a fallback": silhouetteEntry({ origin: "placeholder" }),
    "silhouette claiming a done portrait": silhouetteEntry({ status: "done", placeholder: null }),
    "silhouette origin without an identity": silhouetteEntry({ fallback: null }),
    "runtime origin without a url": validArtCatalogEntry({
      subject_key: null, status: "missing", url: null, aspect_ratio: null,
      face_rect: null, stage: null, origin: "runtime", placeholder,
    }),
    "fallback outside the defaults route": validArtCatalogEntry({
      fallback: { key: "man", url: "/art/portrait/man.webp", face_rect: rect },
    }),
    "fallback without a rectangle": validArtCatalogEntry({
      fallback: { key: "man", url: "/art/defaults/man.webp" },
    }),
    "fallback with an unknown field": validArtCatalogEntry({
      fallback: { key: "man", url: "/art/defaults/man.webp", face_rect: rect, identity: "x" },
    }),
    "fallback with an out-of-range rectangle": validArtCatalogEntry({
      fallback: { key: "man", url: "/art/defaults/man.webp", face_rect: { x: 0.5, y: 0.5, w: 1.5, h: 0.9 } },
    }),
    // The scene wire block is unchanged by this change: the two new fields
    // belong to the portrait catalog only.
    "scene carrying an origin": validArtPanel({ scene: validArtScene({ origin: "runtime" }) }),
    "scene carrying a fallback": validArtPanel({ scene: validArtScene({ fallback: null }) }),
  };
  Object.keys(rejects).forEach((label) => {
    assert.throws(() => Protocol.validateArtPanel(rejects[label]), label);
  });
});

test("media url bound admits the worst-case gallery identity in both mirrors", () => {
  // /art/gallery/character/<64-char key>/<uuid36>.avif = 129 chars.
  const worst = "/art/gallery/character/" + "k".repeat(64) + "/" + "0".repeat(36) + ".avif";
  assert.equal(worst.length, 129);
  const panel = validArtPanel({
    portrait_catalog: { "42": validArtCatalogEntry({ url: worst }) },
  });
  assert.doesNotThrow(() => Protocol.validateArtPanel(panel));
  const tooLong = "/art/" + "p".repeat(256 - "/art/".length + 1);
  assert.throws(() =>
    Protocol.validateArtPanel(
      validArtPanel({
        portrait_catalog: { "42": validArtCatalogEntry({ url: tooLong }) },
      })
    )
  );
  assert.doesNotThrow(() =>
    Protocol.validateRosterPanel(
      validRosterPanel({
        characters: [validRosterCharacter({ portrait: validRosterPortrait({ url: worst }) })],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateRosterPanel(
      validRosterPanel({
        characters: [
          validRosterCharacter({ portrait: validRosterPortrait({ url: tooLong }) }),
        ],
      })
    )
  );
});

