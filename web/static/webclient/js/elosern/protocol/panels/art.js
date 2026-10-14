"use strict";

// The art panel's own validators (scene + portrait catalog). The gallery
// panel's wire validator moved to ./gallery.js in the gallery v2 -> v3 cutover
// (change unified-gallery-image-contract) and consumes the canonical artwork
// descriptor through ../artwork.js.

var C = require("../constants.js");
var core = require("../core.js");

var isPlainObject = core.isPlainObject;
var jsonByteSize = core.jsonByteSize;
var requireExactFields = core.requireExactFields;
var requireInt = core.requireInt;
var requireString = core.requireString;

var MAX_SAFE_INTEGER = C.MAX_SAFE_INTEGER;
var MAX_CANONICAL_JSON_BYTES = C.MAX_CANONICAL_JSON_BYTES;
var MAX_MEDIA_URL = C.MAX_MEDIA_URL;

// Panel discriminator dispatch: the unavailable form is common to every
// registered panel; the available form is validated against its schema.

// Exact available art panel v1 schema (mirror of
// web.webclient.presentation.art, webclient-art-panel D1).
var ART_PLACEHOLDER_KINDS = ["missing", "unavailable"];
var ART_ROLES = ["隊友", "敵方", "對話對象", "人物"];
// The closed portrait-origin vocabulary (art-gallery-fallback owns it;
// official-art-resolution-contracts extends both sides with "official").
var ART_ORIGINS = ["runtime", "official", "silhouette", "placeholder"];
var ART_MAX_FALLBACK_KEY = 32;
var ART_FALLBACK_URL_PREFIX = "/art/defaults/";

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
  var name = requireString(value.name, "context name", 64);
  if (!name.trim()) {
    throw new Error("context name must be non-empty");
  }
  var role = requireString(value.role, "context role", 16);
  if (ART_ROLES.indexOf(role) === -1) {
    throw new Error("context role is not a stable value");
  }
  return { name: name, role: role };
}

// Face-rectangle validator (art catalog entries and roster portraits share
// the portrait field vocabulary): null, or exactly x, y, w, h as finite
// real numbers in [0, 1]. Placement metadata only — no crop, no second
// image (mirror of web.webclient.presentation.art._validate_face_rect).
function validateArtFaceRect(value) {
  if (value === null) {
    return null;
  }
  requireExactFields(value, "face_rect", ["x", "y", "w", "h"], []);
  var names = ["x", "y", "w", "h"];
  for (var i = 0; i < names.length; i++) {
    var coordinate = value[names[i]];
    if (typeof coordinate !== "number" || !Number.isFinite(coordinate)) {
      throw new Error("face_rect." + names[i] + " must be a real number");
    }
    if (!(coordinate >= 0 && coordinate <= 1)) {
      throw new Error("face_rect." + names[i] + " must lie in [0, 1]");
    }
  }
  return { x: value.x, y: value.y, w: value.w, h: value.h };
}

// The decorative built-in silhouette reference the server resolved for a
// still-absent portrait: exactly the committed key, its /art/defaults/
// identity and that key's rectangle. It is presentation data and never the
// entry's own media fields (mirror of
// web.webclient.presentation.art._validate_portrait_fallback).
function validateArtFallback(value) {
  if (value === null) {
    return null;
  }
  requireExactFields(value, "art fallback", ["key", "url", "face_rect"], []);
  var key = requireString(value.key, "fallback key", ART_MAX_FALLBACK_KEY);
  if (!key.trim()) {
    throw new Error("fallback key must be non-empty");
  }
  var url = requireString(value.url, "fallback url", MAX_MEDIA_URL);
  if (url.indexOf(ART_FALLBACK_URL_PREFIX) !== 0) {
    throw new Error("fallback url must name a committed built-in identity");
  }
  var faceRect = validateArtFaceRect(value.face_rect);
  if (faceRect === null) {
    throw new Error("a fallback carries a face_rect");
  }
  return { key: key, url: url, face_rect: faceRect };
}

// The server-authored origin discriminator, coherent with its own media:
// shared by the art catalog entry and the roster row portrait (mirror of
// web.webclient.presentation.art._validate_portrait_origin). It names the
// branch that produced the payload's own media, never a URL shape, so a
// silhouette or placeholder origin never carries that media URL, a runtime or
// official origin always does, and an official image (a read-only catalog
// default, not a generated asset) is never reported with a status.
function validatePortraitOrigin(field, noun, value, url, status) {
  var origin = requireString(value, field, 16);
  if (ART_ORIGINS.indexOf(origin) === -1) {
    throw new Error(field + " is not a stable value");
  }
  if (url !== null && (origin === "silhouette" || origin === "placeholder")) {
    throw new Error("a " + noun + " carrying a media URL is not a silhouette or a placeholder");
  }
  if (url === null && (origin === "runtime" || origin === "official")) {
    throw new Error("an " + origin + " origin carries the " + noun + "'s media URL");
  }
  if (origin === "official" && status !== null) {
    throw new Error("an official image is not a generated portrait");
  }
  return origin;
}

function validateArtCatalogEntry(value) {
  requireExactFields(
    value,
    "art catalog entry",
    ["subject_key", "status", "url", "aspect_ratio", "alt", "placeholder", "face_rect", "stage", "context", "origin", "fallback"],
    []
  );
  if (value.subject_key !== null) {
    requireString(value.subject_key, "catalog subject_key", 128);
  }
  var status = value.status;
  if (status !== null) {
    requireString(status, "catalog status", 16);
    if (["missing", "pending", "failed", "done"].indexOf(status) === -1) {
      throw new Error("catalog status is not a stable value");
    }
  }
  var url = value.url;
  if (url !== null) {
    requireString(url, "catalog url", MAX_MEDIA_URL);
    if (url.indexOf("/art/") !== 0) {
      throw new Error("catalog url must be a same-origin media URL");
    }
  }
  if (value.aspect_ratio !== null && value.aspect_ratio !== "3:4") {
    throw new Error("catalog aspect_ratio must be 3:4");
  }
  var alt = requireString(value.alt, "catalog alt", 512);
  if (!alt.trim()) {
    throw new Error("catalog alt must be non-empty");
  }
  validateArtPlaceholder(value.placeholder);
  validateArtContext(value.context);
  var faceRect = validateArtFaceRect(value.face_rect);
  validateArtStage(value.stage, url);
  var origin = validatePortraitOrigin("catalog origin", "catalog entry", value.origin, url, status);
  var fallback = validateArtFallback(value.fallback);
  if (url !== null && faceRect === null) {
    throw new Error("a catalog entry with a url carries a face_rect");
  }
  if (url === null && faceRect !== null) {
    throw new Error("a catalog placeholder carries no face_rect");
  }
  // The decorative reference carries a real meaning only on the silhouette
  // origin's payload, so it is required there and refused by the placeholder
  // origin.
  if (origin === "silhouette") {
    if (fallback === null) throw new Error("a silhouette origin carries its fallback identity");
    if (status === "done") throw new Error("a silhouette origin is not a done portrait");
  } else if (origin === "placeholder" && fallback !== null) {
    throw new Error("a placeholder origin carries no fallback identity");
  }
  return value;
}

function validateArtPanel(payload) {
  requireExactFields(
    payload,
    "art panel",
    ["schema_version", "available", "kind", "scene", "portrait_catalog"],
    []
  );
  requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
  if (payload.schema_version !== 2) {
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
    schema_version: 2,
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
  validateArtFallback: validateArtFallback,
  validateArtFaceRect: validateArtFaceRect,
  validateArtStage: validateArtStage,
  validatePortraitOrigin: validatePortraitOrigin,
  ART_ORIGINS: ART_ORIGINS,
};
