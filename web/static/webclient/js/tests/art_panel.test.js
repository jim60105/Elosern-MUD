/*
 * DOM-independent tests for the art panel model (task 6.1).
 *
 * Runs with Node 24's built-in test runner and node:assert. Covers payload
 * validation acceptance/rejection (through the protocol validator), scene
 * placeholder and pending-with-prior states, catalog reduction, focus
 * adoption/survival rules, no-focus no-card, full-view open/close, and the
 * client-local focus bus.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const ArtPanel = require("../elosern/art_panel.js");
const ArtFocus = require("../elosern/art_focus.js");
const {
  fixtureDigest,
  validArtCatalogEntry,
  validArtwork,
  validArtworkResource,
} = require("./protocol_fixtures.js");

// One canonical scene descriptor: the generated archetype artwork at rank 20
// ahead of the required bundled illustration at rank 40. The scene wrapper is
// exactly {archetype, label, alt, artwork}.
function validSceneResource(overrides) {
  var version = fixtureDigest("scene-output");
  return Object.assign(
    {
      resource_id: "scene/t_hearth_hollow.png",
      version: version,
      url: "/art/scene/t_hearth_hollow.png?v=" + version,
      origin: "runtime",
      geometry: { image_size: null, face_rect: null, stage: null, aspect_ratio: "16:9" },
    },
    overrides
  );
}

function validBundledResource(overrides) {
  var fingerprint = fixtureDigest("bundled-hearth");
  return Object.assign(
    {
      resource_id: "bundled-scene/t_hearth_hollow/" + fingerprint + ".webp",
      version: fingerprint,
      url: "/art/bundled-scene/t_hearth_hollow/" + fingerprint + ".webp",
      origin: "bundled_official",
      geometry: { image_size: null, face_rect: null, stage: null, aspect_ratio: null },
    },
    overrides
  );
}

function validSceneArtwork(overrides) {
  return Object.assign(
    {
      subject_id: "grid:t_hearth:0,0",
      revision: fixtureDigest("scene-revision"),
      generation_subject: "scene:t_hearth_hollow",
      generation_state: "done",
      attempts: [
        {
          type: "image",
          source_id: "scene.generated:scene:t_hearth_hollow",
          rank: 20,
          resource: validSceneResource(),
        },
        {
          type: "image",
          source_id: "scene.bundled:t_hearth_hollow",
          rank: 40,
          resource: validBundledResource(),
        },
      ],
      terminal: null,
      retention_sources: [
        {
          source_id: "scene.generated:scene:t_hearth_hollow",
          token: fixtureDigest("scene-retention"),
        },
      ],
    },
    overrides
  );
}

function validScene(overrides) {
  return Object.assign(
    {
      archetype: "t_hearth_hollow",
      label: "爐火合成廳",
      alt: "爐火合成廳場景",
      artwork: validSceneArtwork(),
    },
    overrides
  );
}

// One catalog value: the canonical descriptor plus its bounded display
// context. The URL/aspect facts the model reduces come from the descriptor's
// own highest-ranked image attempt.
function validEntry(overrides) {
  return validArtCatalogEntry(
    Object.assign(
      {
        artwork: validArtwork({
          attempts: [
            {
              type: "image",
              source_id: "portrait.default:1",
              rank: 30,
              resource: validArtworkResource({
                resource_id: "portrait/monster/low.png",
                version: fixtureDigest("monster-low"),
                url: "/art/portrait/monster/low.png",
              }),
            },
          ],
        }),
        context: { name: "哥布林", role: "敵方" },
      },
      overrides
    )
  );
}

function validPanel(overrides) {
  return Object.assign(
    {
      schema_version: 4,
      available: true,
      kind: "scene",
      scene: validScene(),
      portrait_catalog: {
        "1": validEntry({ context: { name: "英雄", role: "隊友" } }),
        "2": validEntry({ context: { name: "哥布林", role: "敵方" } }),
      },
    },
    overrides
  );
}

// The catalog is replaced, never deep-merged: a merged entry would silently
// regain the facts a rejection case deliberately removed.
function catalogPanel(entries) {
  const panel = validPanel();
  panel.portrait_catalog = entries;
  return panel;
}

test("the validated art payload is accepted by the protocol reducer", () => {
  const panel = Protocol.validateArtPanel(validPanel());
  assert.equal(panel.available, true);
  assert.equal(panel.kind, "scene");
});

test("malformed art payloads are rejected by the protocol validator", () => {
  assert.throws(() => Protocol.validateArtPanel(validPanel({ kind: "combat" })));
  assert.throws(() => Protocol.validateArtPanel(validPanel({ schema_version: 1 })));
  assert.throws(() => Protocol.validateArtPanel(validPanel({ schema_version: 2 })));
  assert.throws(() => Protocol.validateArtPanel(validPanel({ schema_version: 3 })));
  assert.throws(() =>
    Protocol.validateArtPanel(
      validPanel({
        scene: validScene({
          artwork: validSceneArtwork({
            attempts: [
              {
                type: "image",
                source_id: "scene.generated:scene:t_hearth_hollow",
                rank: 20,
                resource: validSceneResource({ url: "https://x.test/a.png" }),
              },
            ],
          }),
        }),
      })
    )
  );
  // The retired flat scene fields are refused outright.
  assert.throws(() => Protocol.validateArtPanel(validPanel({ scene: validScene({ status: "done" }) })));
  assert.throws(() =>
    Protocol.validateArtPanel(validPanel({ scene: validScene({ url: "/art/scene/x.png" }) }))
  );
  assert.throws(() => Protocol.validateArtPanel(catalogPanel({ x: validEntry() })));
  // A reached fault never carries a URL: the fact names the source, and the
  // retired flat field on a fault entry is refused by the shared validator.
  assert.throws(() =>
    Protocol.validateArtPanel(
      validPanel({
        scene: validScene({
          artwork: validSceneArtwork({
            generation_state: "failed",
            attempts: [
              {
                type: "fault",
                source_id: "scene.generated:scene:t_hearth_hollow",
                rank: 20,
                reason: "generation_failed",
                resource: validSceneResource(),
              },
            ],
            terminal: null,
          }),
        }),
      })
    )
  );
  // v3: the entry is exactly {artwork, context}, and the descriptor's own
  // geometry is validated — a malformed face rectangle is refused, and the
  // retired flat entry shape is refused outright.
  const withGeometry = (geometry) =>
    validEntry({
      artwork: validArtwork({
        attempts: [
          {
            type: "image",
            source_id: "portrait.default:1",
            rank: 30,
            resource: validArtworkResource({ geometry }),
          },
        ],
      }),
    });
  assert.throws(() =>
    Protocol.validateArtPanel(
      catalogPanel({
        "1": withGeometry({
          image_size: null,
          face_rect: { x: 0.25, y: 0.06, w: 0.5 },
          stage: null,
          aspect_ratio: "3:4",
        }),
      })
    )
  );
  assert.throws(() =>
    Protocol.validateArtPanel(
      catalogPanel({
        "1": withGeometry({
          image_size: null,
          face_rect: { x: 1.5, y: 0.06, w: 0.5, h: 0.5 },
          stage: null,
          aspect_ratio: "3:4",
        }),
      })
    )
  );
  assert.throws(() =>
    Protocol.validateArtPanel(
      catalogPanel({ "1": Object.assign(validEntry(), { url: "/art/portrait/monster/low.png" }) })
    )
  );
});

test("a done scene reduces to the asset state", () => {
  const panel = validPanel();
  const model = ArtPanel.reducePanel(panel, "exploration", {});
  assert.equal(model.available, true);
  assert.equal(model.scene.state, "asset");
  // The image is the descriptor's own highest-ranked candidate; the display
  // strings are the committed ones.
  assert.equal(
    model.scene.url,
    panel.scene.artwork.attempts[0].resource.url
  );
  assert.equal(model.scene.label, "爐火合成廳");
  assert.equal(model.scene.alt, "爐火合成廳場景");
  assert.equal(model.scene.status, "done");
});

test("a failed scene reduces to the placeholder state", () => {
  const panel = validPanel({
    scene: validScene({
      artwork: validSceneArtwork({
        generation_state: "failed",
        attempts: [
          {
            type: "fault",
            source_id: "scene.generated:scene:t_hearth_hollow",
            rank: 20,
            reason: "generation_failed",
          },
        ],
        terminal: null,
        retention_sources: [],
      }),
    }),
  });
  const model = ArtPanel.reducePanel(panel, "exploration", {});
  assert.equal(model.scene.state, "placeholder");
  assert.equal(model.scene.placeholderKind, "failed");
  assert.equal(model.scene.status, "failed");
  assert.equal(model.scene.url, null);
});

test("a pending scene with no prior image reduces to the placeholder state", () => {
  const panel = validPanel({
    scene: validScene({
      artwork: validSceneArtwork({
        generation_state: "pending",
        attempts: [],
        terminal: null,
      }),
    }),
  });
  const model = ArtPanel.reducePanel(panel, "exploration", {});
  assert.equal(model.scene.state, "placeholder");
  assert.equal(model.scene.status, "pending");
  assert.equal(model.scene.url, null);
});

test("a pending scene with a prior image retains it dimmed", () => {
  const prior = ArtPanel.reducePanel(validPanel(), "exploration", {});
  assert.equal(prior.scene.state, "asset");
  const pending = validPanel({
    scene: validScene({
      artwork: validSceneArtwork({
        generation_state: "pending",
        attempts: [],
        terminal: null,
      }),
    }),
  });
  const model = ArtPanel.reducePanel(pending, "exploration", prior);
  assert.equal(model.scene.state, "pending");
  // The retained image is the one this browser is already showing.
  assert.equal(model.scene.url, prior.scene.url);
});

test("catalog reduction keys entries by opaque catalog IDs", () => {
  const model = ArtPanel.reducePanel(validPanel(), "exploration", {});
  assert.deepEqual(Object.keys(model.catalog).sort(), ["1", "2"]);
  assert.equal(model.catalog["2"].name, "哥布林");
  assert.equal(model.catalog["2"].role, "敵方");
  assert.equal(model.catalog["2"].url, "/art/portrait/monster/low.png");
  assert.equal(model.catalog["2"].generationState, "done");
  assert.equal(model.catalog["2"].terminalUrl, "/art/defaults/man.webp");
});

test("focus survives when its catalog ID survives", () => {
  const initial = ArtPanel.reducePanel(validPanel(), "exploration", { focusKey: "2" });
  assert.equal(initial.focusKey, "2");
  const next = ArtPanel.reducePanel(validPanel(), "exploration", initial);
  assert.equal(next.focusKey, "2");
});

test("a vanished focus adopts the mode rule", () => {
  // Exploration: a vanished focus means no focus.
  const model = ArtPanel.reducePanel(
    catalogPanel({ "3": validEntry() }),
    "exploration",
    { focusKey: "2" }
  );
  assert.equal(model.focusKey, null);
  assert.equal(ArtPanel.focusedEntry(model), null);

  // Combat: a vanished focus selects the first valid participant.
  const combat = ArtPanel.reducePanel(
    catalogPanel({ "3": validEntry() }),
    "combat",
    { focusKey: "2" }
  );
  assert.equal(combat.focusKey, "3");
});

test("no focus means no portrait card", () => {
  const model = ArtPanel.reducePanel(validPanel(), "exploration", { focusKey: null });
  assert.equal(model.focusKey, null);
  assert.equal(ArtPanel.focusedEntry(model), null);
});

test("combat with no prior focus selects the first participant", () => {
  const model = ArtPanel.reducePanel(validPanel(), "combat", {});
  assert.equal(model.focusKey, "1");
  assert.equal(ArtPanel.focusedEntry(model).name, "英雄");
});

test("moveFocus wraps within deterministic catalog order", () => {
  const model = ArtPanel.reducePanel(validPanel(), "combat", {});
  assert.equal(ArtPanel.moveFocus(model, 1), "2");
  assert.equal(ArtPanel.moveFocus(model, -1), "2");
});

test("scene and portrait full-view state is preserved across reduction", () => {
  const previous = {
    focusKey: "2",
    sceneFullView: true,
    portraitFullView: false,
  };
  const model = ArtPanel.reducePanel(validPanel(), "exploration", previous);
  assert.equal(model.sceneFullView, true);
  assert.equal(model.portraitFullView, false);
});

test("an entry with no real candidate has no URL and keeps its terminal", () => {
  const panel = catalogPanel({
    "2": validEntry({
      artwork: validArtwork({
        subject_id: "2",
        generation_subject: null,
        generation_state: "missing",
        attempts: [
          { type: "fault", source_id: "portrait.default:1", rank: 30, reason: "generated_output_missing" },
        ],
      }),
    }),
  });
  const model = ArtPanel.reducePanel(panel, "combat", {});
  assert.equal(model.catalog["2"].url, null);
  assert.equal(model.catalog["2"].aspectRatio, null);
  assert.equal(model.catalog["2"].generationState, "missing");
  // The alpha terminal stays available for a local fallback, separately from
  // any real candidate.
  assert.equal(model.catalog["2"].terminalUrl, "/art/defaults/man.webp");
});

test("the client-local focus bus publishes and delivers without a packet", () => {
  const bus = ArtFocus.createBus();
  const seen = [];
  const unsubscribe = bus.subscribe((key) => seen.push(key));
  bus.publish("42");
  bus.publish(null);
  unsubscribe();
  bus.publish("99");
  assert.deepEqual(seen, ["42", null]);
});

test("a broken focus subscriber cannot break the bus", () => {
  const bus = ArtFocus.createBus();
  bus.subscribe(() => {
    throw new Error("boom");
  });
  const seen = [];
  bus.subscribe((key) => seen.push(key));
  assert.doesNotThrow(() => bus.publish("7"));
  assert.deepEqual(seen, ["7"]);
});
