"use strict";

// The art panel's own validators (scene + portrait catalog). The gallery
// panel's wire validator moved to ./gallery.js in the gallery v2 -> v3 cutover
// (change unified-gallery-image-contract) and consumes the canonical artwork
// descriptor through ../artwork.js — the same shared validator this panel's
// catalog entries now use.

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
var MAX_MEDIA_URL = C.MAX_MEDIA_URL;
var ART_SCHEMA_VERSION = C.ART_SCHEMA_VERSION;

// Panel discriminator dispatch: the unavailable form is common to every
// registered panel; the available form is validated against its schema.

// Exact available art panel schema (mirror of
// web.webclient.presentation.art, webclient-art-panel).
var ART_PLACEHOLDER_KINDS = ["missing", "unavailable"];
var ART_ROLES = ["隊友", "敵方", "對話對象", "人物"];
var ART_MAX_CONTEXT_NAME = 64;
var ART_MAX_CONTEXT_ROLE = 16;

function validateArtPlaceholder(value) {
  if (value === null) {
    return null;
  }
  requireExactFields(value, "art placeholder", ["kind", "label"], []);
  if (ART_PLACEHOLDER_KINDS.indexOf(value.kind) === -1) {
    throw new Error("placeholder kind is not a stable value");
  }
  var label = requireString(value.label, "placeholder label", 128);
  if (!label.trim()) {
    throw new Error("placeholder label must be non-empty");
  }
  return { kind: value.kind, label: label };
}

function validateArtScene(value) {
  requireExactFields(
    value,
    "art scene",
    ["archetype", "label", "subject_key", "status", "url", "aspect_ratio", "alt", "placeholder", "stage"],
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
  if (value.subject_key !== null) {
    requireString(value.subject_key, "scene subject_key", 128);
  }
  var status = value.status;
  if (status !== null) {
    requireString(status, "scene status", 16);
    if (["missing", "pending", "failed", "done"].indexOf(status) === -1) {
      throw new Error("scene status is not a stable value");
    }
  }
  var url = value.url;
  if (url !== null) {
    requireString(url, "scene url", MAX_MEDIA_URL);
    if (url.indexOf("/art/") !== 0) {
      throw new Error("scene url must be a same-origin media URL");
    }
  }
  if (value.aspect_ratio !== null && value.aspect_ratio !== "16:9") {
    throw new Error("scene aspect_ratio must be 16:9");
  }
  var alt = requireString(value.alt, "scene alt", 512);
  if (!alt.trim()) {
    throw new Error("scene alt must be non-empty");
  }
  var placeholder = validateArtPlaceholder(value.placeholder);
  var stage = validateArtStage(value.stage, url);
  if (placeholder === null && status !== "done") {
    throw new Error("scene placeholder must be present unless done");
  }
  if (placeholder !== null && status === "done") {
    throw new Error("a done scene must not carry a placeholder");
  }
  return {
    archetype: value.archetype,
    stage: stage,
    label: label,
    subject_key: value.subject_key,
    status: status,
    url: url,
    aspect_ratio: value.aspect_ratio,
    alt: alt,
    placeholder: placeholder,
  };
}

function validateArtStage(value, url) {
  if (url === null) {
    if (value !== null) throw new Error("a placeholder carries no stage");
    return null;
  }
  requireExactFields(value, "stage", ["scale", "x", "y"], []);
  ["scale", "x", "y"].forEach(function (name) {
    var coordinate = value[name];
    var lower = name === "scale" ? 0.2 : -0.5;
    var upper = name === "scale" ? 2 : 0.5;
    if (typeof coordinate !== "number" || !Number.isFinite(coordinate) || coordinate < lower || coordinate > upper) {
      throw new Error("invalid stage." + name);
    }
  });
  return { scale: value.scale, x: value.x, y: value.y };
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
  validateArtPlaceholder: validateArtPlaceholder,
  validateArtPanel: validateArtPanel,
  validateArtStage: validateArtStage,
};
