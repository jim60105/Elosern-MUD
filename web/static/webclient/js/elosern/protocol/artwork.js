"use strict";

// The canonical artwork descriptor validator (change
// unified-gallery-image-contract). Exactly one bounded mirror of
// web/webclient/presentation/artwork.py and of the vocabulary in
// world/art/descriptors.py: the container's exact key sets, the
// identity/version/rank/retention bounds, the same-origin media URL rule with
// its per-origin ceiling and its one closed cache-version query form, and the
// applicable geometry. Every panel that carries a descriptor calls
// validateArtwork; the Python side reads the same numbers.
//
// Origin-specific route checks (an official fingerprint vocabulary, a gallery
// route bound to the selected subject and image) stay with the panel that owns
// that route, because only that panel knows which subject the descriptor
// describes.

var core = require("./core.js");

var isPlainObject = core.isPlainObject;
var codePoints = core.codePoints;
var requireExactFields = core.requireExactFields;
var requireString = core.requireString;
var hasLoneSurrogate = core.hasLoneSurrogate;

// --- Canonical bounds (mirror of world/art/descriptors.py) -----------------

var MAX_SUBJECT_ID = 128;
var MAX_SOURCE_ID = 256;
var MAX_RESOURCE_ID = 256;
var FINGERPRINT_LENGTH = 64;
var MAX_ATTEMPTS = 16;
var MAX_RETENTION_SOURCES = 16;
var MAX_ASPECT_RATIO = 16;
// The shared decoded-size ceiling, mirrored from the shipped
// ART_SD_MAX_IMAGE_DIMENSIONS / ART_SD_MAX_IMAGE_PIXELS defaults.
var MAX_IMAGE_DIMENSION = 4096;
var MAX_IMAGE_PIXELS = 16777216;

var ORIGIN_RUNTIME = "runtime";
var ORIGIN_OFFICIAL = "official";
var ORIGIN_BUNDLED_OFFICIAL = "bundled_official";
var ORIGIN_SILHOUETTE = "silhouette";
var ORIGINS = [ORIGIN_RUNTIME, ORIGIN_OFFICIAL, ORIGIN_BUNDLED_OFFICIAL, ORIGIN_SILHOUETTE];
// The same-origin media URL ceiling each origin's own route can reach.
var GENERAL_MEDIA_URL_LIMIT = 256;
var GALLERY_MEDIA_URL_LIMIT = 129;
var MEDIA_URL_LIMITS = {
  runtime: GALLERY_MEDIA_URL_LIMIT,
  official: GENERAL_MEDIA_URL_LIMIT,
  bundled_official: GENERAL_MEDIA_URL_LIMIT,
  silhouette: GALLERY_MEDIA_URL_LIMIT,
};
var VERSION_QUERY = "v";

var GENERATION_STATES = ["missing", "pending", "done", "failed"];

var FAULT_REASONS = [
  "generation_failed",
  "generated_output_missing",
  "source_unavailable",
  "source_rejected",
  "explicit_reference_missing",
  "metadata_invalid",
  "required_resource_missing",
  "configuration_invalid",
  "panel_unavailable",
  "image_load_failed",
  "image_decode_failed",
];

var TERMINAL_KINDS = ["alpha_mask", "scene_image"];

// The canonical source-identity prefixes (mirror of the builders in
// world/art/descriptors.py), so a panel never spells a source layer itself.
var SOURCE_PREFIX = {
  original: "gallery.original:",
  official: "gallery.official:",
  alpha: "gallery.alpha:",
};

// --- Exact shapes ---------------------------------------------------------

var DESCRIPTOR_FIELDS = [
  "subject_id", "revision", "generation_subject", "generation_state",
  "attempts", "terminal", "retention_sources",
];
var RESOURCE_FIELDS = ["resource_id", "version", "url", "origin", "geometry"];
var GEOMETRY_FIELDS = ["image_size", "face_rect", "stage", "aspect_ratio"];
var IMAGE_SIZE_FIELDS = ["width", "height"];
var FACE_RECT_FIELDS = ["x", "y", "w", "h"];
var STAGE_FIELDS = ["scale", "x", "y"];
var IMAGE_ATTEMPT_FIELDS = ["type", "source_id", "rank", "resource"];
var FAULT_ATTEMPT_FIELDS = ["type", "source_id", "rank", "reason"];
var TERMINAL_FIELDS = ["kind", "source_id", "rank", "resource"];
var RETENTION_FIELDS = ["source_id", "token"];
var ATTEMPT_TYPES = ["image", "fault"];

var MEDIA_URL_PREFIX = "/art/";
var FINGERPRINT_RE = /^[0-9a-f]{64}$/;
var ASPECT_RATIO_RE = /^[0-9]{1,4}:[0-9]{1,4}$/;
// The same "printable text" discipline the server's own URL builder satisfies:
// no control or exotic-separator character except the plain space, so a
// non-ASCII subject key still produces its own real URL.
var NON_PRINTABLE_RE = /[\p{C}\p{Z}]/u;
var STAGE_BOUNDS = [["scale", 0.2, 2.0], ["x", -0.5, 0.5], ["y", -0.5, 0.5]];

function artworkText(value, maximum, name) {
  requireString(value, name, maximum);
  if (!value || hasLoneSurrogate(value)) throw new Error("invalid " + name);
  return value;
}

function artworkNumber(value, name) {
  if (typeof value !== "number" || !Number.isFinite(value) || Math.abs(value) > Number.MAX_SAFE_INTEGER) {
    throw new Error("invalid " + name);
  }
  return value;
}

function artworkFingerprint(value, name) {
  if (typeof value !== "string" || !FINGERPRINT_RE.test(value)) throw new Error("invalid " + name);
  return value;
}

// One bounded same-origin media URL for `origin`: exactly the art route
// prefix, printable text only (no control character or exotic separator can
// slip through, while a non-ASCII subject key keeps its own real URL), no `..`
// segment, at most that origin's own ceiling, and an OPTIONAL cache version
// that must be the single closed `?v=<sha256>` form.
function validateArtworkMediaUrl(value, origin) {
  var limit = Object.prototype.hasOwnProperty.call(MEDIA_URL_LIMITS, origin)
    ? MEDIA_URL_LIMITS[origin]
    : null;
  if (limit === null) throw new Error("invalid origin");
  if (typeof value !== "string" || !value || codePoints(value) > limit) {
    throw new Error("invalid media url");
  }
  var mark = value.indexOf("?");
  var path = mark === -1 ? value : value.slice(0, mark);
  if (mark !== -1) {
    var query = value.slice(mark + 1);
    var equals = query.indexOf("=");
    if (equals === -1 || query.slice(0, equals) !== VERSION_QUERY ||
        !FINGERPRINT_RE.test(query.slice(equals + 1))) {
      throw new Error("invalid media url version");
    }
  }
  if (path.indexOf(MEDIA_URL_PREFIX) !== 0 || NON_PRINTABLE_RE.test(path.replace(/ /g, ""))) {
    throw new Error("media url must name the same-origin art route");
  }
  if (path.split("/").indexOf("..") !== -1) throw new Error("media url must not traverse");
  return value;
}

function validateArtworkFaceRect(value) {
  requireExactFields(value, "face_rect", FACE_RECT_FIELDS, []);
  FACE_RECT_FIELDS.forEach(function (name) {
    var number = artworkNumber(value[name], "face_rect " + name);
    if (number < 0 || number > 1) throw new Error("face_rect must lie in the unit square");
  });
  if (value.x + value.w > 1 || value.y + value.h > 1) {
    throw new Error("face_rect must lie inside the unit square");
  }
  if (value.w <= 0 || value.h <= 0) throw new Error("face_rect w and h must be positive");
  return value;
}

function validateArtworkStage(value) {
  requireExactFields(value, "stage", STAGE_FIELDS, []);
  STAGE_BOUNDS.forEach(function (bound) {
    var number = artworkNumber(value[bound[0]], "stage " + bound[0]);
    if (number < bound[1] || number > bound[2]) throw new Error("stage value out of bounds");
  });
  return value;
}

function validateArtworkGeometry(value) {
  if (value === null) return null;
  requireExactFields(value, "geometry", GEOMETRY_FIELDS, []);
  var size = value.image_size;
  if (size !== null) {
    requireExactFields(size, "image_size", IMAGE_SIZE_FIELDS, []);
    ["width", "height"].forEach(function (name) {
      var dimension = size[name];
      if (typeof dimension !== "number" || !Number.isInteger(dimension) || dimension <= 0) {
        throw new Error("invalid image_size " + name);
      }
    });
    if (size.width > MAX_IMAGE_DIMENSION || size.height > MAX_IMAGE_DIMENSION ||
        size.width * size.height > MAX_IMAGE_PIXELS) {
      throw new Error("image_size exceeds the decoded-size ceiling");
    }
  }
  if (value.face_rect !== null) validateArtworkFaceRect(value.face_rect);
  if (value.stage !== null) validateArtworkStage(value.stage);
  if (value.aspect_ratio !== null) {
    if (typeof value.aspect_ratio !== "string" || !ASPECT_RATIO_RE.test(value.aspect_ratio)) {
      throw new Error("invalid aspect_ratio");
    }
  }
  return value;
}

function validateArtworkResource(value) {
  requireExactFields(value, "resource", RESOURCE_FIELDS, []);
  artworkText(value.resource_id, MAX_RESOURCE_ID, "resource_id");
  artworkFingerprint(value.version, "resource version");
  if (ORIGINS.indexOf(value.origin) === -1) throw new Error("invalid resource origin");
  validateArtworkMediaUrl(value.url, value.origin);
  validateArtworkGeometry(value.geometry);
  return value;
}

// Exactly the seven descriptor keys, in the canonical fact vocabulary. A fault
// entry carries no resource (and so no URL), a terminal names a permitted kind,
// and a terminal whose bytes already appear among the attempts is rejected:
// the terminal is a FALLBACK, not a second copy of a listed candidate.
function validateArtwork(payload) {
  requireExactFields(payload, "artwork", DESCRIPTOR_FIELDS, []);
  artworkText(payload.subject_id, MAX_SUBJECT_ID, "subject_id");
  artworkFingerprint(payload.revision, "revision");
  if (payload.generation_subject !== null) {
    artworkText(payload.generation_subject, MAX_SUBJECT_ID, "generation_subject");
  }
  if (payload.generation_state !== null && GENERATION_STATES.indexOf(payload.generation_state) === -1) {
    throw new Error("invalid generation state");
  }
  var attempts = payload.attempts;
  if (!Array.isArray(attempts) || attempts.length > MAX_ATTEMPTS) throw new Error("invalid attempts");
  var seen = new Set();
  var resourceKeys = new Set();
  attempts.forEach(function (attempt) {
    if (!isPlainObject(attempt) || ATTEMPT_TYPES.indexOf(attempt.type) === -1) {
      throw new Error("invalid attempt");
    }
    var image = attempt.type === "image";
    requireExactFields(attempt, "attempt", image ? IMAGE_ATTEMPT_FIELDS : FAULT_ATTEMPT_FIELDS, []);
    var sourceId = artworkText(attempt.source_id, MAX_SOURCE_ID, "source_id");
    var rank = artworkNumber(attempt.rank, "attempt rank");
    if (rank < 0) throw new Error("attempt rank must be nonnegative");
    var identity = attempt.type + "\u0000" + sourceId + "\u0000" + rank;
    if (seen.has(identity)) throw new Error("duplicate attempt");
    seen.add(identity);
    if (image) {
      var resource = validateArtworkResource(attempt.resource);
      resourceKeys.add(resource.resource_id + "\u0000" + resource.version);
    } else if (FAULT_REASONS.indexOf(attempt.reason) === -1) {
      throw new Error("invalid fault reason");
    }
  });
  var terminal = payload.terminal;
  if (terminal !== null) {
    requireExactFields(terminal, "terminal", TERMINAL_FIELDS, []);
    if (TERMINAL_KINDS.indexOf(terminal.kind) === -1) throw new Error("invalid terminal kind");
    artworkText(terminal.source_id, MAX_SOURCE_ID, "terminal source_id");
    if (artworkNumber(terminal.rank, "terminal rank") < 0) {
      throw new Error("terminal rank must be nonnegative");
    }
    var terminalResource = validateArtworkResource(terminal.resource);
    if (resourceKeys.has(terminalResource.resource_id + "\u0000" + terminalResource.version)) {
      throw new Error("terminal duplicates an attempt resource");
    }
  }
  var retention = payload.retention_sources;
  if (!Array.isArray(retention) || retention.length > MAX_RETENTION_SOURCES) {
    throw new Error("invalid retention sources");
  }
  var retained = new Set();
  retention.forEach(function (entry) {
    requireExactFields(entry, "retention entry", RETENTION_FIELDS, []);
    var sourceId = artworkText(entry.source_id, MAX_SOURCE_ID, "retention source_id");
    artworkFingerprint(entry.token, "retention token");
    if (retained.has(sourceId)) throw new Error("duplicate retention source");
    retained.add(sourceId);
  });
  return payload;
}

module.exports = {
  validateArtwork: validateArtwork,
  validateArtworkResource: validateArtworkResource,
  validateArtworkGeometry: validateArtworkGeometry,
  validateArtworkFaceRect: validateArtworkFaceRect,
  validateArtworkStage: validateArtworkStage,
  validateArtworkMediaUrl: validateArtworkMediaUrl,
  MAX_SUBJECT_ID: MAX_SUBJECT_ID,
  MAX_SOURCE_ID: MAX_SOURCE_ID,
  MAX_RESOURCE_ID: MAX_RESOURCE_ID,
  FINGERPRINT_LENGTH: FINGERPRINT_LENGTH,
  MAX_ATTEMPTS: MAX_ATTEMPTS,
  MAX_RETENTION_SOURCES: MAX_RETENTION_SOURCES,
  MAX_ASPECT_RATIO: MAX_ASPECT_RATIO,
  MAX_IMAGE_DIMENSION: MAX_IMAGE_DIMENSION,
  MAX_IMAGE_PIXELS: MAX_IMAGE_PIXELS,
  ORIGIN_RUNTIME: ORIGIN_RUNTIME,
  ORIGIN_OFFICIAL: ORIGIN_OFFICIAL,
  ORIGIN_BUNDLED_OFFICIAL: ORIGIN_BUNDLED_OFFICIAL,
  ORIGIN_SILHOUETTE: ORIGIN_SILHOUETTE,
  ORIGINS: ORIGINS,
  MEDIA_URL_LIMITS: MEDIA_URL_LIMITS,
  GENERATION_STATES: GENERATION_STATES,
  FAULT_REASONS: FAULT_REASONS,
  TERMINAL_KINDS: TERMINAL_KINDS,
  SOURCE_PREFIX: SOURCE_PREFIX,
  DESCRIPTOR_FIELDS: DESCRIPTOR_FIELDS,
};
