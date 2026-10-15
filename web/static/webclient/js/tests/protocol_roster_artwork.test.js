/*
 * The migrated portrait surfaces agree on ONE canonical descriptor shape
 * (change unified-portrait-image-contract).
 *
 * The art panel's catalog value is exactly `{artwork, context}` and the roster
 * row's `portrait` is exactly the descriptor itself. Both are validated by the
 * same shared mirror (`elosern/protocol/artwork.js`), so this file proves the
 * properties the two wires must hold TOGETHER:
 *
 *   * the retired flat portrait object is refused on both wires, with no
 *     dual-shape adaptation anywhere;
 *   * the full terminal and fault field sets ride the wire (a fault carries no
 *     resource and so no URL; a terminal carries its own kind/source/rank and
 *     resource, and never a second copy of a listed candidate's bytes);
 *   * recorded generation truth is INDEPENDENT of the presented image's origin;
 *   * the retention authorization list is bounded and shaped exactly.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const {
  fixtureDigest,
  validArtCatalogEntry,
  validArtwork,
  validArtworkResource,
  validArtworkTerminal,
  validRosterCharacter,
  validRosterPanel,
} = require("./protocol_fixtures.js");


// One canonical scene descriptor: the wire this file's art panels carry beside
// the portrait descriptor under test. The scene is exactly
// {archetype, label, alt, artwork}, so a portrait fact that leaked into the
// scene block could not be mistaken for a scene fact.
function validSceneArtwork() {
  const fingerprint = fixtureDigest("scene-bundled");
  return {
    subject_id: "grid:t_south_gate:0,0",
    revision: fixtureDigest("scene-revision"),
    generation_subject: "scene:t_south_gate",
    generation_state: "done",
    attempts: [
      {
        type: "image",
        source_id: "scene.bundled:t_south_gate",
        rank: 40,
        resource: {
          resource_id: `bundled-scene/t_south_gate/${fingerprint}.webp`,
          version: fingerprint,
          url: `/art/bundled-scene/t_south_gate/${fingerprint}.webp`,
          origin: "bundled_official",
          geometry: { image_size: null, face_rect: null, stage: null, aspect_ratio: null },
        },
      },
    ],
    terminal: null,
    retention_sources: [],
  };
}

// The same descriptor, placed on both wires: an art catalog value wraps it with
// its display context, a roster row carries it bare.
function bothWires(artwork) {
  const artPanel = {
    schema_version: 4,
    available: true,
    kind: "scene",
    scene: {
      archetype: null,
      label: "南門街道",
      alt: "當前場景",
      artwork: validSceneArtwork(),
    },
    portrait_catalog: { "1": validArtCatalogEntry({ artwork }) },
  };
  const rosterPanel = validRosterPanel({
    characters: [validRosterCharacter({ portrait: artwork })],
  });
  return { artPanel, rosterPanel };
}

function acceptsBoth(label, artwork) {
  const { artPanel, rosterPanel } = bothWires(artwork);
  assert.doesNotThrow(() => Protocol.validateArtPanel(artPanel), label + " (art)");
  assert.doesNotThrow(() => Protocol.validateRosterPanel(rosterPanel), label + " (roster)");
}

function rejectsBoth(label, artwork) {
  const { artPanel, rosterPanel } = bothWires(artwork);
  assert.throws(() => Protocol.validateArtPanel(artPanel), label + " (art)");
  assert.throws(() => Protocol.validateRosterPanel(rosterPanel), label + " (roster)");
}

// The one descriptor every case below varies.
const BASE = validArtwork();

test("both portrait wires refuse the retired flat shape", () => {
  const flat = {
    subject_key: "portrait:character:1",
    status: "done",
    url: "/art/portrait/character/1.png",
    aspect_ratio: "3:4",
    alt: "英雄肖像",
    placeholder: null,
    face_rect: { x: 0.3, y: 0.1, w: 0.4, h: 0.4 },
    stage: { scale: 1, x: 0, y: 0 },
    origin: "runtime",
  };
  // The art catalog entry is exactly {artwork, context}: a flat entry fails
  // its exact-key check.
  assert.throws(() =>
    Protocol.validateArtPanel({
      schema_version: 4,
      available: true,
      kind: "scene",
      scene: {
        archetype: null,
        label: "南門街道",
        alt: "當前場景",
        artwork: validSceneArtwork(),
      },
      
      portrait_catalog: { "1": flat },
    })
  );
  // The roster row's portrait IS the descriptor: the same flat object fails.
  assert.throws(() =>
    Protocol.validateRosterPanel(
      validRosterPanel({ characters: [validRosterCharacter({ portrait: flat })] })
    )
  );
  // A descriptor that keeps a retired flat field beside the canonical facts is
  // refused too — there is no tolerant middle shape.
  rejectsBoth("flat field beside the canonical facts", Object.assign({}, BASE, { url: "/art/x.png" }));
  rejectsBoth("retired placeholder field", Object.assign({}, BASE, { placeholder: { kind: "missing", label: "未生成" } }));
  rejectsBoth("retired origin field", Object.assign({}, BASE, { origin: "runtime" }));
  rejectsBoth("retired subject_key field", Object.assign({}, BASE, { subject_key: "portrait:character:1" }));
});

test("both portrait wires carry the full terminal and fault field sets", () => {
  acceptsBoth("a real candidate beside the alpha terminal", BASE);
  acceptsBoth("an alpha-only row", validArtwork({
    generation_subject: null,
    generation_state: "missing",
    attempts: [],
  }));
  acceptsBoth("a faulted row with no terminal", validArtwork({
    generation_state: "failed",
    attempts: [
      { type: "fault", source_id: "portrait.default:1", rank: 30, reason: "generated_output_missing" },
      { type: "fault", source_id: "portrait.official:preset/t_synth_preset", rank: 50, reason: "configuration_invalid" },
    ],
    terminal: null,
  }));
  acceptsBoth("a terminal with its own source and rank", validArtwork({
    terminal: validArtworkTerminal({ source_id: "portrait.alpha:monster_anon", rank: 100 }),
  }));

  // A fault entry is exactly its four fields and never carries a URL.
  rejectsBoth("a fault carrying a resource", validArtwork({
    attempts: [
      {
        type: "fault",
        source_id: "portrait.default:1",
        rank: 30,
        reason: "generated_output_missing",
        resource: validArtworkResource(),
      },
    ],
  }));
  rejectsBoth("a fault with no reason", validArtwork({
    attempts: [{ type: "fault", source_id: "portrait.default:1", rank: 30 }],
  }));
  rejectsBoth("a fault with an unknown reason", validArtwork({
    attempts: [{ type: "fault", source_id: "portrait.default:1", rank: 30, reason: "kaboom" }],
  }));
  // A terminal is exactly its four fields, names a permitted kind, and is a
  // fallback rather than a second copy of a listed candidate.
  rejectsBoth("a terminal missing its resource", validArtwork({
    terminal: { kind: "alpha_mask", source_id: "portrait.alpha:man", rank: 100 },
  }));
  rejectsBoth("a terminal with an unknown kind", validArtwork({
    terminal: validArtworkTerminal({ kind: "cover" }),
  }));
  rejectsBoth("a terminal duplicating a candidate's bytes", validArtwork({
    terminal: validArtworkTerminal({ resource: validArtworkResource() }),
  }));
  rejectsBoth("a negative attempt rank", validArtwork({
    attempts: [
      { type: "image", source_id: "portrait.default:1", rank: -1, resource: validArtworkResource() },
    ],
  }));
  rejectsBoth("a duplicate attempt at one source position", validArtwork({
    attempts: [
      { type: "image", source_id: "portrait.default:1", rank: 30, resource: validArtworkResource() },
      { type: "image", source_id: "portrait.default:1", rank: 30, resource: validArtworkResource() },
    ],
  }));
});

test("recorded generation truth is independent of the presented image's origin", () => {
  const officialCandidate = {
    type: "image",
    source_id: "portrait.official:preset/t_synth_preset",
    rank: 50,
    resource: validArtworkResource({
      resource_id: "preset/t_synth_preset/hero.webp",
      url: "/art/official/" + "a".repeat(64) + "/preset/t_synth_preset/hero.webp",
      origin: "official",
      geometry: {
        image_size: null,
        face_rect: { x: 0.3, y: 0.1, w: 0.4, h: 0.4 },
        stage: { scale: 1, x: 0, y: 0 },
        aspect_ratio: "3:4",
      },
    }),
  };
  // Every recorded state may ride beside an official candidate: a read-only
  // catalog default says nothing about the subject's own generation.
  ["missing", "pending", "done", "failed", null].forEach((state) => {
    acceptsBoth("official candidate with generation " + state, validArtwork({
      generation_subject: "portrait:character:1",
      generation_state: state,
      attempts: [officialCandidate],
    }));
  });
  // A generated-state row with no candidate at all is truthful too: the state
  // describes the recorded job, not the visible image.
  acceptsBoth("pending generation with no candidate", validArtwork({
    generation_state: "pending",
    attempts: [],
  }));
  // The retired raw recorded status never rides the wire.
  rejectsBoth("the raw in_progress status", validArtwork({ generation_state: "in_progress" }));
  rejectsBoth("an unknown generation state", validArtwork({ generation_state: "queued" }));
  // Deliberately disabled generation is a factual null, never a claim.
  acceptsBoth("no generation claim at all", validArtwork({
    generation_subject: null,
    generation_state: null,
    attempts: [],
    terminal: null,
  }));
});

test("the retention authorization list is bounded and shaped exactly", () => {
  const entry = (index) => ({
    source_id: "portrait.classic:" + index,
    token: fixtureDigest("retention" + index),
  });
  acceptsBoth("a bounded retention list", validArtwork({
    retention_sources: [entry(1), entry(2)],
  }));
  acceptsBoth("the retention ceiling itself", validArtwork({
    retention_sources: Array.from({ length: 16 }, (_, i) => entry(i)),
  }));
  rejectsBoth("one entry past the retention ceiling", validArtwork({
    retention_sources: Array.from({ length: 17 }, (_, i) => entry(i)),
  }));
  rejectsBoth("a retention token that is not a digest", validArtwork({
    retention_sources: [{ source_id: "portrait.classic:1", token: "short" }],
  }));
  rejectsBoth("a retention entry with a second field", validArtwork({
    retention_sources: [{ source_id: "portrait.classic:1", token: fixtureDigest("t"), rank: 40 }],
  }));
  rejectsBoth("a duplicated retention source", validArtwork({
    retention_sources: [entry(1), entry(1)],
  }));
  // A portrait carries no retention authorization in this change: the backend
  // authorizes none, so the list is exactly empty on every shipped row.
  assert.deepEqual(validArtwork().retention_sources, []);
});
