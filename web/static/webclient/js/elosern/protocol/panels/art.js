"use strict";

// The art panel's own validators (scene + portrait catalog). The gallery
// panel's wire validator moved to ./gallery.js in the gallery v2 -> v3 cutover
// (change unified-gallery-image-contract) and consumes the canonical artwork
// descriptor through ../artwork.js — the same shared validator this panel's
// catalog entries and its scene block now use.

var C = require("../constants.js");
var core = require("../core.js");
var artwork = require("../artwork.js");

var isPlainObject = core.isPlainObject;
var jsonByteSize = core.jsonByteSize;
var requireExactFields = core.requireExactFields;
var requireInt = core.requireInt;
var requireString = core.requireString;
var validateArtwork = artwork.validateArtwork;

var MAX_SAFE_INTEGER = C.MAX_SAFE_INTEGER;
var MAX_CANONICAL_JSON_BYTES = C.MAX_CANONICAL_JSON_BYTES;
var ART_SCHEMA_VERSION = C.ART_SCHEMA_VERSION;

// Panel discriminator dispatch: the unavailable form is common to every
// registered panel; the available form is validated against its schema.

// Exact available art panel schema (mirror of
// web.webclient.presentation.art, webclient-art-panel).
var ART_ROLES = ["隊友", "敵方", "對話對象", "人物"];
var ART_MAX_CONTEXT_NAME = 64;
var ART_MAX_CONTEXT_ROLE = 16;

// One scene wrapper: exactly the archetype the room renders from (null for a
// room whose authored metadata cannot be honored), the two bounded display
// strings the stage renders outside the bitmap, and the complete canonical
// descriptor the scene resolution produced (mirror of
// web.webclient.presentation.art._validate_scene). Every retired flat scene
// field fails the exact-key check instead of being adapted.
function validateArtScene(value) {
  requireExactFields(
    value,
    "art scene",
    ["archetype", "label", "alt", "artwork"],
    []
  );
  if (value.archetype !== null) {
    var archetype = requireString(value.archetype, "archetype", 64);
    if (!archetype.trim()) {
      throw new Error("scene archetype must be non-empty");
    }
  }
  var label = requireString(value.label, "scene label", 128);
  if (!label.trim()) {
    throw new Error("scene label must be non-empty");
  }
  var alt = requireString(value.alt, "scene alt", 512);
  if (!alt.trim()) {
    throw new Error("scene alt must be non-empty");
  }
  return {
    archetype: value.archetype,
    label: label,
    alt: alt,
    artwork: validateArtwork(value.artwork),
  };
}

function validateArtContext(value) {
  requireExactFields(value, "art context", ["name", "role"], []);
  var name = requireString(value.name, "context name", ART_MAX_CONTEXT_NAME);
  if (!name.trim()) {
    throw new Error("context name must be non-empty");
  }
  var role = requireString(value.role, "context role", ART_MAX_CONTEXT_ROLE);
  if (ART_ROLES.indexOf(role) === -1) {
    throw new Error("context role is not a stable value");
  }
  return { name: name, role: role };
}

// One catalog entry: exactly the canonical artwork descriptor plus its
// bounded display context (mirror of
// web.webclient.presentation.art._validate_catalog_entry). The descriptor is
// validated by the one shared mirror, so the art catalog and every other
// descriptor consumer accept byte-identical fact shapes; a retired flat
// portrait object fails the exact-key check instead of being adapted.
function validateArtCatalogEntry(value) {
  requireExactFields(value, "art catalog entry", ["artwork", "context"], []);
  return { artwork: validateArtwork(value.artwork), context: validateArtContext(value.context) };
}

function validateArtPanel(payload) {
  requireExactFields(
    payload,
    "art panel",
    ["schema_version", "available", "kind", "scene", "portrait_catalog"],
    []
  );
  requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
  if (payload.schema_version !== ART_SCHEMA_VERSION) {
    throw new Error("unsupported art schema_version");
  }
  if (payload.available !== true || payload.kind !== "scene") {
    throw new Error("art panel must be available with kind scene");
  }

  var scene = validateArtScene(payload.scene);
  var catalog = payload.portrait_catalog;
  if (!isPlainObject(catalog) || Object.keys(catalog).length > 32) {
    throw new Error("portrait_catalog must be a bounded object");
  }
  var entries = {};
  var keys = Object.keys(catalog);
  for (var i = 0; i < keys.length; i++) {
    var key = keys[i];
    if (!/^[0-9]+$/.test(key)) {
      throw new Error("catalog keys must be opaque decimal strings");
    }
    entries[key] = validateArtCatalogEntry(catalog[key]);
  }

  var result = {
    schema_version: ART_SCHEMA_VERSION,
    available: true,
    kind: "scene",
    scene: scene,
    portrait_catalog: entries,
  };
  // Envelope guarantee (design D7): per-field bounds are ceilings, not a
  // guarantee that any combination of them fits, so the validator enforces
  // the serialized byte size directly and fails closed over the envelope.
  if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
    throw new Error("art payload exceeds the OOB envelope limit");
  }
  return result;
}

module.exports = {
  validateArtPanel: validateArtPanel,
};
