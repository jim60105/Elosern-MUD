/*
 * gallery v3 + canonical artwork descriptor gate (change
 * unified-gallery-image-contract).
 *
 * The gallery panel no longer carries flat url/face_rect/stage row fields:
 * every image fact is a canonical descriptor validated by
 * ../elosern/protocol/artwork.js, and this file pins both halves — the
 * descriptor's closed vocabulary and the gallery row's exact use of it. The
 * Python mirror (web/webclient/presentation/artwork.py +
 * presentation/gallery.py) is asserted against the same cases by
 * web/webclient/presentation/tests/test_gallery_panel.py.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const artwork = require("../elosern/protocol/artwork.js");

const SUBJECT = "portrait:character:7001";
const IMAGE_ID = "10000000-0000-4000-8000-000000000001";
const FINGERPRINT = "a".repeat(64);
const DIGEST = "b".repeat(64);
const RECT = { x: 0.25, y: 0.06, w: 0.5, h: 0.375 };
const SIZE = { width: 768, height: 1024 };

function alpha(key = "woman", rect = RECT) {
  return {
    kind: "alpha_mask",
    source_id: `gallery.alpha:${key}`,
    rank: 100,
    resource: {
      resource_id: `defaults/${key}.webp`,
      version: DIGEST,
      url: `/art/defaults/${key}.webp`,
      origin: "silhouette",
      geometry: { image_size: null, face_rect: rect, stage: null, aspect_ratio: "3:4" },
    },
  };
}

function cardDescriptor(changes = {}) {
  return {
    subject_id: `${DIGEST}:${IMAGE_ID}`,
    revision: "c".repeat(64),
    generation_subject: SUBJECT,
    generation_state: "done",
    attempts: [{
      type: "image",
      source_id: `gallery.original:${IMAGE_ID}`,
      rank: 10,
      resource: {
        resource_id: `gallery/character/7001/${IMAGE_ID}.webp`,
        version: DIGEST,
        url: `/art/gallery/character/7001/${IMAGE_ID}.webp`,
        origin: "runtime",
        geometry: { image_size: SIZE, face_rect: RECT, stage: { scale: 1, x: 0, y: 0 }, aspect_ratio: "3:4" },
      },
    }],
    terminal: alpha(),
    retention_sources: [{ source_id: `gallery.original:${IMAGE_ID}`, token: DIGEST }],
    ...changes,
  };
}

function card(changes = {}) {
  return {
    image_id: IMAGE_ID,
    status: "card",
    label: "肖像",
    artwork: cardDescriptor(),
    is_default: true,
    chips: ["預設臉框", "目前預設"],
    requested_fields: ["appearance"],
    binding_present: false,
    created_at: 100,
    ...changes,
  };
}

function panel(changes = {}) {
  return {
    schema_version: 3,
    available: true,
    kind: "gallery",
    subjects: [{ subject_key: SUBJECT, kind: "portrait:character", display_name: "夜行者", is_puppet: true }],
    selected: SUBJECT,
    filters: { all: 1, defaults: 1, bound: 0, pending: 0, failed: 0 },
    capabilities: { supports_bindings: true, supports_field_selection: true, supports_free_text: true, supports_personal_official_preferences: true, max_cards: null },
    cards: [card()],
    equipment_summary: {
      weapon_main: { value: null, display_name: "未裝備" },
      weapon_off: { value: null, display_name: "未裝備" },
      armor: { value: null, display_name: "未裝備" },
      accessories: { value: [], display_names: [], equipped_count: 0 },
    },
    binding_warnings: [],
    error_state: null,
    official_entries: [],
    ...changes,
  };
}

function withCard(changes) {
  return panel({ cards: [card(changes)] });
}

test("gallery v3 is in the production allowlist and the canonical panel validates", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.gallery, 3);
  assert.equal(Protocol.GALLERY_SCHEMA_VERSION, 3);
  assert.doesNotThrow(() => Protocol.validateGalleryPanel(panel()));
  // The v2 shape is gone: the old version is rejected outright.
  assert.throws(() => Protocol.validateGalleryPanel(panel({ schema_version: 2 })));
});

test("a card row carries no flat url, face_rect or stage field", () => {
  for (const field of ["url", "face_rect", "stage", "image_size"]) {
    assert.throws(
      () => Protocol.validateGalleryPanel(withCard({ [field]: null })),
      new RegExp(`unknown fields ${field}`),
      `the v2 row field ${field} must be rejected`,
    );
  }
});

test("the exact original is pinned to its own source and rank", () => {
  const foreign = cardDescriptor();
  foreign.attempts[0].source_id = "gallery.original:10000000-0000-4000-8000-000000000002";
  assert.throws(() => Protocol.validateGalleryPanel(withCard({ artwork: foreign })));
  const wrongRank = cardDescriptor();
  wrongRank.attempts[0].rank = 20;
  assert.throws(() => Protocol.validateGalleryPanel(withCard({ artwork: wrongRank })));
  // A second candidate would let another card stand in for the requested one.
  const extra = cardDescriptor();
  extra.attempts.push(structuredClone(extra.attempts[0]));
  assert.throws(() => Protocol.validateGalleryPanel(withCard({ artwork: extra })));
});

test("a vanished original becomes a named fault with no URL", () => {
  const faulted = cardDescriptor({
    attempts: [{
      type: "fault",
      source_id: `gallery.original:${IMAGE_ID}`,
      rank: 10,
      reason: "generated_output_missing",
    }],
    retention_sources: [],
  });
  assert.doesNotThrow(() => Protocol.validateGalleryPanel(withCard({ artwork: faulted })));
  // A fault never carries a resource, so it can never carry a URL.
  const withUrl = structuredClone(faulted);
  withUrl.attempts[0].resource = { resource_id: "x", version: DIGEST, url: "/art/x.png", origin: "runtime", geometry: null };
  assert.throws(() => Protocol.validateGalleryPanel(withCard({ artwork: withUrl })));
  // The reason vocabulary is closed.
  const badReason = structuredClone(faulted);
  badReason.attempts[0].reason = "not_a_reason";
  assert.throws(() => Protocol.validateGalleryPanel(withCard({ artwork: badReason })));
});

test("an exact original keeps the selected subject's own runtime route", () => {
  const foreign = cardDescriptor();
  foreign.attempts[0].resource.url = `/art/gallery/character/7002/${IMAGE_ID}.webp`;
  assert.throws(() => Protocol.validateGalleryPanel(withCard({ artwork: foreign })));
  const wrongOrigin = cardDescriptor();
  wrongOrigin.attempts[0].resource.origin = "official";
  assert.throws(() => Protocol.validateGalleryPanel(withCard({ artwork: wrongOrigin })));
  const unsupportedExtension = cardDescriptor();
  unsupportedExtension.attempts[0].resource.url = `/art/gallery/character/7001/${IMAGE_ID}.svg`;
  assert.throws(() => Protocol.validateGalleryPanel(withCard({ artwork: unsupportedExtension })));
});

test("candidate geometry is validated exactly", () => {
  const cases = {
    "zero width": { face_rect: { x: 0, y: 0, w: 0, h: 0.5 } },
    "rectangle overflow": { face_rect: { x: 0.9, y: 0, w: 0.5, h: 0.5 } },
    "stage out of bounds": { stage: { scale: 2.5, x: 0, y: 0 } },
    "oversized decoded size": { image_size: { width: 8192, height: 8192 } },
    "extra geometry key": { aspect_ratio: "3:4", extra: 1 },
  };
  for (const [name, change] of Object.entries(cases)) {
    const descriptor = cardDescriptor();
    descriptor.attempts[0].resource.geometry = { ...descriptor.attempts[0].resource.geometry, ...change };
    assert.throws(
      () => Protocol.validateGalleryPanel(withCard({ artwork: descriptor })),
      undefined,
      `candidate geometry case "${name}" must be rejected`,
    );
  }
  // A card row's exact original must carry its stored geometry in full.
  const missingStage = cardDescriptor();
  missingStage.attempts[0].resource.geometry.stage = null;
  assert.throws(() => Protocol.validateGalleryPanel(withCard({ artwork: missingStage })));
});

test("the terminal is the committed silhouette alpha mask at its own rank", () => {
  const notAlpha = cardDescriptor({ terminal: { ...alpha(), kind: "scene_image" } });
  assert.throws(() => Protocol.validateGalleryPanel(withCard({ artwork: notAlpha })));
  const wrongRank = cardDescriptor({ terminal: { ...alpha(), rank: 10 } });
  assert.throws(() => Protocol.validateGalleryPanel(withCard({ artwork: wrongRank })));
  const foreignKey = cardDescriptor({ terminal: { ...alpha(), source_id: "gallery.alpha:absent" } });
  assert.throws(() => Protocol.validateGalleryPanel(withCard({ artwork: foreignKey })));
  const foreignRoute = cardDescriptor();
  foreignRoute.terminal.resource.url = "/art/gallery/character/7001/x.webp";
  assert.throws(() => Protocol.validateGalleryPanel(withCard({ artwork: foreignRoute })));
  // A card row with an image always carries its fallback.
  assert.throws(() => Protocol.validateGalleryPanel(withCard({ artwork: cardDescriptor({ terminal: null }) })));
});

test("a synthetic row carries no image at all", () => {
  const pending = card({
    status: "pending",
    label: "肖像（生成中）",
    is_default: false,
    chips: [],
    requested_fields: [],
    artwork: {
      subject_id: `${DIGEST}:${IMAGE_ID}`,
      revision: "d".repeat(64),
      generation_subject: SUBJECT,
      generation_state: "pending",
      attempts: [],
      terminal: null,
      retention_sources: [],
    },
  });
  assert.doesNotThrow(() => Protocol.validateGalleryPanel(panel({
    cards: [pending],
    filters: { all: 1, defaults: 0, bound: 0, pending: 1, failed: 0 },
  })));
  const fabricated = structuredClone(pending);
  fabricated.artwork.attempts = cardDescriptor().attempts;
  assert.throws(() => Protocol.validateGalleryPanel(panel({
    cards: [fabricated],
    filters: { all: 1, defaults: 0, bound: 0, pending: 1, failed: 0 },
  })));
});

test("descriptor containers and identities are bounded", () => {
  const tooMany = cardDescriptor();
  tooMany.attempts = Array.from({ length: 17 }, () => ({
    type: "fault",
    source_id: `gallery.original:${IMAGE_ID}`,
    rank: 10,
    reason: "source_rejected",
  }));
  assert.throws(() => artwork.validateArtwork(tooMany));

  const longSubject = cardDescriptor({ subject_id: "x".repeat(129) });
  assert.throws(() => artwork.validateArtwork(longSubject));

  const badRevision = cardDescriptor({ revision: "C".repeat(64) });
  assert.throws(() => artwork.validateArtwork(badRevision));

  const badState = cardDescriptor({ generation_state: "in_progress" });
  assert.throws(() => artwork.validateArtwork(badState));

  const badRetention = cardDescriptor({
    retention_sources: [{ source_id: `gallery.original:${IMAGE_ID}`, token: "short" }],
  });
  assert.throws(() => artwork.validateArtwork(badRetention));

  const duplicated = cardDescriptor();
  duplicated.terminal = {
    kind: "alpha_mask",
    source_id: duplicated.attempts[0].source_id,
    rank: 100,
    resource: structuredClone(duplicated.attempts[0].resource),
  };
  assert.throws(() => artwork.validateArtwork(duplicated), /terminal duplicates/);
});

test("media URLs stay same-origin with only the closed cache-version query", () => {
  assert.doesNotThrow(() => artwork.validateArtworkMediaUrl("/art/gallery/character/7001/a.webp", "runtime"));
  assert.doesNotThrow(() => artwork.validateArtworkMediaUrl(`/art/x.png?v=${DIGEST}`, "runtime"));
  assert.throws(() => artwork.validateArtworkMediaUrl("https://example.invalid/art/x.png", "runtime"));
  assert.throws(() => artwork.validateArtworkMediaUrl("/art/x.png?other=1", "runtime"));
  assert.throws(() => artwork.validateArtworkMediaUrl("/art/x.png?v=short", "runtime"));
  assert.throws(() => artwork.validateArtworkMediaUrl("/art/../secret.png", "runtime"));
  assert.throws(() => artwork.validateArtworkMediaUrl(`/art/${"x".repeat(130)}.png`, "runtime"));
  // The official route keeps the wider ceiling because it embeds a filename.
  const wideOfficial = `/art/official/${FINGERPRINT}/${"x".repeat(150)}.png`;
  assert.ok(wideOfficial.length > 129 && wideOfficial.length <= 256, wideOfficial.length);
  assert.doesNotThrow(() => artwork.validateArtworkMediaUrl(wideOfficial, "official"));
  assert.throws(() => artwork.validateArtworkMediaUrl(wideOfficial, "runtime"));
  assert.throws(() => artwork.validateArtworkMediaUrl("/art/x.png", "placeholder"));
});

test("an official row carries its exact candidate and no stage", () => {
  const identity = "preset/synthetic_preset/dawn.webp";
  const row = {
    identity,
    artwork: {
      subject_id: `${DIGEST}:${DIGEST.slice(0, 36)}`,
      revision: "e".repeat(64),
      generation_subject: SUBJECT,
      generation_state: "done",
      attempts: [{
        type: "image",
        source_id: `gallery.official:${identity}`,
        rank: 10,
        resource: {
          resource_id: identity,
          version: FINGERPRINT,
          url: `/art/official/${FINGERPRINT}/${identity}`,
          origin: "official",
          geometry: { image_size: SIZE, face_rect: RECT, stage: null, aspect_ratio: "3:4" },
        },
      }],
      terminal: alpha("elder"),
      retention_sources: [{ source_id: `gallery.official:${identity}`, token: DIGEST }],
    },
    is_current: false,
    is_catalog_default: true,
  };
  const official = panel({ cards: [], official_entries: [row], filters: { all: 0, defaults: 0, bound: 0, pending: 0, failed: 0 } });
  assert.doesNotThrow(() => Protocol.validateGalleryPanel(official));
  // The retired flat row shape is rejected on this row kind too.
  assert.throws(() => Protocol.validateGalleryPanel(panel({
    cards: [],
    filters: { all: 0, defaults: 0, bound: 0, pending: 0, failed: 0 },
    official_entries: [{ ...row, url: row.artwork.attempts[0].resource.url }],
  })));
  // A candidate that names another identity is refused.
  const foreign = structuredClone(official);
  foreign.official_entries[0].artwork.attempts[0].resource.resource_id = "preset/other/dusk.webp";
  assert.throws(() => Protocol.validateGalleryPanel(foreign));
});
