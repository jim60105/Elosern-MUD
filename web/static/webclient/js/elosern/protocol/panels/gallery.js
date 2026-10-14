"use strict";

// Exact gallery v3 mirror (change unified-gallery-image-contract). Display
// labels and matching facts are server-owned; every image fact is a canonical
// artwork descriptor validated by ../artwork.js. The v2 flat row fields
// (url/face_rect/stage) are deliberately absent: this validator rejects them,
// so no reader can keep a second shape alive.

var C = require("../constants.js");
var core = require("../core.js");
var artwork = require("../artwork.js");

var codePoints = core.codePoints;
var utf8Bytes = core.utf8Bytes;
var jsonByteSize = core.jsonByteSize;
var checkGlobalSafety = core.checkGlobalSafety;
var requireExactFields = core.requireExactFields;
var requireInt = core.requireInt;
var requireBool = core.requireBool;
var requireString = core.requireString;
var hasLoneSurrogate = core.hasLoneSurrogate;

var MAX_SAFE_INTEGER = C.MAX_SAFE_INTEGER;
var MAX_CANONICAL_JSON_BYTES = C.MAX_CANONICAL_JSON_BYTES;
var MAX_LIST_ITEMS = C.MAX_LIST_ITEMS;
var MAX_MEDIA_URL = C.MAX_MEDIA_URL;

// The mirrored gallery bounds. The runtime media URL ceiling is READ from the
// canonical descriptor vocabulary's origin table so the two can never drift.
var GALLERY_SCHEMA_VERSION = 3;
var GALLERY_MAX_SUBJECTS = 24;
var GALLERY_MAX_LABEL = 128;
var GALLERY_MAX_NAME = 64;
var GALLERY_MAX_CHIP = 16;
var GALLERY_MAX_URL = artwork.MEDIA_URL_LIMITS[artwork.ORIGIN_RUNTIME];
var GALLERY_MAX_WARNINGS = 5;
var GALLERY_MAX_CONDITION = 512;
var GALLERY_SLOTS = ["weapon_main", "weapon_off", "armor", "accessories"];
var GALLERY_SLOT_LABELS = ["主手", "副手", "防具", "飾品"];
var GALLERY_FIELDS = ["appearance"].concat(GALLERY_SLOTS);
var GALLERY_UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
var GALLERY_STORE_EXTENSIONS = [".png", ".webp", ".jpg", ".avif"];
// The official-entry read model's bounds, mirrored from
// web/webclient/presentation/gallery.py: a bounded list of catalog-admitted
// images, each identity inside the writers' closed grammar and each URL
// inside the shared portrait wire ceiling (MAX_MEDIA_URL).
var GALLERY_MAX_OFFICIAL_ENTRIES = 32;
var GALLERY_MAX_OFFICIAL_IDENTITY = 192;
var GALLERY_OFFICIAL_URL_PREFIX = "/art/official/";
var GALLERY_OFFICIAL_ROW_FIELDS = ["identity", "artwork", "is_current", "is_catalog_default"];
var GALLERY_CARD_FIELDS = [
  "image_id", "status", "label", "artwork", "is_default", "chips",
  "requested_fields", "binding_present", "created_at"
];
// The gallery's own stable source ranks and the committed silhouette route
// (mirror of world/art/descriptors.py and the fallback-key vocabulary).
var GALLERY_RANK_ORIGINAL = 10;
var GALLERY_RANK_ALPHA = 100;
var GALLERY_DEFAULTS_URL_PREFIX = "/art/defaults/";
var GALLERY_DEFAULTS_IDENTITY_PREFIX = "defaults/";
var GALLERY_FALLBACK_EXTENSION = ".webp";
var GALLERY_FALLBACK_KEYS = ["man", "woman", "boy", "girl", "elder", "monster_anon"];

function galleryText(value, maximum, name) {
  requireString(value, name, maximum);
  if (!value || hasLoneSurrogate(value)) throw new Error("invalid " + name);
  return value;
}

function galleryNumber(value, name) {
  if (typeof value !== "number" || !Number.isFinite(value) || Math.abs(value) > MAX_SAFE_INTEGER) {
    throw new Error("invalid " + name);
  }
  return value;
}

function gallerySubject(value) {
  galleryText(value, 128, "subject_key");

  var match = /^(portrait:(character|monster)):(.+)$/u.exec(value);
  if (!match) throw new Error("invalid gallery subject");
  var key = match[3];
  if (codePoints(key) > 64 || utf8Bytes(key) > 200 || /[|/:{}]/u.test(key) ||
      /[\p{C}\p{Z}]/u.test(key.replace(/ /g, ""))) {
    throw new Error("invalid subject key");
  }
  return { kind: match[1], directory: match[2], key: key };
}

function galleryUuid(value) {
  if (typeof value !== "string" || value.length !== 36 || !GALLERY_UUID.test(value)) throw new Error("invalid image_id");
}


// The official identity grammar, mirrored from
// world/art/gallery.py::validate_official_identity: exactly three non-empty
// slash-separated segments, none a dot segment, a known store extension,
// printable text (no C/Z category character except the plain space), and at
// most 192 code points.
function validateGalleryOfficialIdentity(value) {
  galleryText(value, GALLERY_MAX_OFFICIAL_IDENTITY, "official identity");
  if (/[\p{C}\p{Z}]/u.test(value.replace(/ /g, ""))) {
    throw new Error("invalid official identity");
  }
  var segments = value.split("/");
  if (segments.length !== 3 || !segments.every(function (part) { return part.length > 0; })) {
    throw new Error("invalid official identity");
  }
  if (segments.some(function (part) { return part === "." || part === ".."; })) {
    throw new Error("invalid official identity");
  }
  var filename = segments[2];
  var dot = filename.lastIndexOf(".");
  if (dot === -1 || GALLERY_STORE_EXTENSIONS.indexOf(filename.slice(dot)) === -1) {
    throw new Error("invalid official identity");
  }
  return value;
}


// The fingerprinted official media URL vocabulary: the closed route prefix, a
// 64-character lowercase sha256 fingerprint segment, and a non-empty
// percent-encoded identity path (ASCII printable, no space) — exactly what the
// catalog's own URL builder produces.
function validateGalleryOfficialUrl(url) {
  if (url.indexOf(GALLERY_OFFICIAL_URL_PREFIX) !== 0) {
    throw new Error("official url must name the official media route");
  }
  var rest = url.slice(GALLERY_OFFICIAL_URL_PREFIX.length);
  var slash = rest.indexOf("/");
  if (slash === -1) throw new Error("official url must carry a sha256 fingerprint");
  var fingerprint = rest.slice(0, slash);
  var tail = rest.slice(slash + 1);
  if (fingerprint.length !== 64 || /[^0-9a-f]/.test(fingerprint)) {
    throw new Error("official url must carry a sha256 fingerprint");
  }
  if (!tail || /[^\x21-\x7E]/.test(tail)) {
    throw new Error("official url must carry an identity path");
  }
  return url;
}


// The committed built-in key one alpha-terminal resource names, or a refusal.
// The one origin a gallery silhouette may carry: the fixed in-repo defaults
// route, a key of the closed fallback vocabulary, the single committed
// extension, and a URL built from that very identity.
function gallerySilhouetteKey(resource) {
  var identity = resource.resource_id;
  if (identity.indexOf(GALLERY_DEFAULTS_IDENTITY_PREFIX) !== 0) {
    throw new Error("silhouette must name the committed defaults route");
  }
  var tail = identity.slice(GALLERY_DEFAULTS_IDENTITY_PREFIX.length);
  if (tail.slice(-GALLERY_FALLBACK_EXTENSION.length) !== GALLERY_FALLBACK_EXTENSION) {
    throw new Error("silhouette must name the committed defaults route");
  }
  var key = tail.slice(0, tail.length - GALLERY_FALLBACK_EXTENSION.length);
  if (GALLERY_FALLBACK_KEYS.indexOf(key) === -1 || resource.url !== GALLERY_DEFAULTS_URL_PREFIX + tail) {
    throw new Error("silhouette must name a committed built-in key");
  }
  return key;
}


// The gallery's one permitted terminal: the subject's silhouette alpha mask,
// required on every row that carries an image so a failed preview always has
// the subject's own fallback.
function validateGalleryTerminal(terminal) {
  if (terminal === null) throw new Error("a gallery row with an image carries its alpha terminal");
  if (terminal.kind !== "alpha_mask" || terminal.rank !== GALLERY_RANK_ALPHA) {
    throw new Error("gallery terminal must be the alpha mask at its own rank");
  }
  var resource = terminal.resource;
  if (resource.origin !== artwork.ORIGIN_SILHOUETTE) {
    throw new Error("alpha terminal must be the committed silhouette");
  }
  if (terminal.source_id !== artwork.SOURCE_PREFIX.alpha + gallerySilhouetteKey(resource)) {
    throw new Error("alpha terminal must name its own fallback key");
  }
}


// One card row's descriptor: its exact original at its own rank, or its named
// fault. A stored card contributes exactly one rank-10 runtime candidate
// naming the selected subject's own image with the exact stored geometry; a
// card whose output is missing or refused contributes exactly one rank-10
// known fault for that same exact image and NO URL, so the requested card
// stays identifiable. A pending or failed row contributes neither: no
// original candidate, no geometry and no terminal.
function validateGalleryCardArtwork(row, selected) {
  var descriptor = row.artwork;
  artwork.validateArtwork(descriptor);
  var attempts = descriptor.attempts;
  if (row.status !== "card") {
    if (attempts.length > 0 || descriptor.terminal !== null) {
      throw new Error("synthetic row fabricated an image");
    }
    return;
  }
  validateGalleryTerminal(descriptor.terminal);
  var source = artwork.SOURCE_PREFIX.original + row.image_id;
  if (attempts.length !== 1 || attempts[0].source_id !== source) {
    throw new Error("a card row carries exactly one exact-original attempt");
  }
  var entry = attempts[0];
  if (entry.rank !== GALLERY_RANK_ORIGINAL) {
    throw new Error("the exact original must carry its own rank");
  }
  if (entry.type === "fault") return;
  var resource = entry.resource;
  if (resource.origin !== artwork.ORIGIN_RUNTIME) {
    throw new Error("the exact original must be a runtime resource");
  }
  // The path must name the selected subject's own image with a store
  // extension; the descriptor validator already accepted at most the one
  // closed `?v=<sha256>` cache-version suffix.
  var prefix = "/art/gallery/" + selected.directory + "/" + selected.key + "/" + row.image_id;
  var path = resource.url.split("?")[0];
  if (path.indexOf(prefix) !== 0 ||
      GALLERY_STORE_EXTENSIONS.indexOf(path.slice(prefix.length)) === -1) {
    throw new Error("url must name selected subject and image");
  }
  var geometry = resource.geometry;
  if (geometry === null || geometry.image_size === null ||
      geometry.face_rect === null || geometry.stage === null) {
    throw new Error("the exact original must carry its stored geometry");
  }
}


// One official row's descriptor: its exact official candidate plus the
// retained startup faults the source facts recorded. The candidate names the
// row's own catalog identity at the fingerprint route, carrying the admitted
// decoded size and fitted rectangle and no stage.
function validateGalleryOfficialArtwork(row) {
  var descriptor = row.artwork;
  artwork.validateArtwork(descriptor);
  validateGalleryTerminal(descriptor.terminal);
  var source = artwork.SOURCE_PREFIX.official + row.identity;
  var candidates = descriptor.attempts.filter(function (entry) { return entry.source_id === source; });
  if (candidates.length !== 1 || candidates[0].type !== "image") {
    throw new Error("an official row carries its exact official candidate");
  }
  var entry = candidates[0];
  if (entry.rank !== GALLERY_RANK_ORIGINAL) {
    throw new Error("the official candidate must carry its own rank");
  }
  var resource = entry.resource;
  if (resource.origin !== artwork.ORIGIN_OFFICIAL || resource.resource_id !== row.identity) {
    throw new Error("the official candidate must name the row identity");
  }
  validateGalleryOfficialUrl(galleryText(resource.url, MAX_MEDIA_URL, "official url"));
  var geometry = resource.geometry;
  if (geometry === null || geometry.face_rect === null || geometry.stage !== null) {
    throw new Error("the official candidate carries its fitted rectangle and no stage");
  }
}


// Exactly the official-row list: shape, bounds, vocabulary, uniqueness, and
// the at-most-one current/catalog-default invariant.
function validateGalleryOfficialEntries(value) {
  if (!Array.isArray(value) || value.length > GALLERY_MAX_OFFICIAL_ENTRIES) {
    throw new Error("invalid official entries");
  }
  var identities = new Set();
  var currents = 0, catalogDefaults = 0;
  value.forEach(function (row) {
    requireExactFields(row, "official row", GALLERY_OFFICIAL_ROW_FIELDS, []);
    var identity = validateGalleryOfficialIdentity(
      galleryText(row.identity, GALLERY_MAX_OFFICIAL_IDENTITY, "official identity")
    );
    if (identities.has(identity)) throw new Error("duplicate official identity");
    identities.add(identity);
    validateGalleryOfficialArtwork(row);
    requireBool(row.is_current, "is_current");
    requireBool(row.is_catalog_default, "is_catalog_default");
    currents += row.is_current ? 1 : 0;
    catalogDefaults += row.is_catalog_default ? 1 : 0;
  });
  if (currents > 1 || catalogDefaults > 1) {
    throw new Error("at most one current/catalog-default official row");
  }
  return value;
}


// Exact, kind-neutral mirror of actions/gallery_actions.py. Capability
// refusals belong to the server, not this schema or the future gallery UI.
// The card-reference union: a card uuid, or a validated official identity the
// adapter refuses with the stable `official_read_only` code.
function galleryCardReference(value) {
  if (typeof value === "string" && value.length === 36 && GALLERY_UUID.test(value)) {
    return value;
  }
  return validateGalleryOfficialIdentity(value);
}


function validateGalleryActionPayload(actionId, payload) {
  // The one action whose exact key set is a union: {subject_key, identity} plus
  // at least one geometry component, because the component the client omits
  // keeps whatever the record already stores for that identity.
  if (actionId === "gallery.official.geometry.set") {
    if (!core.isPlainObject(payload)) throw new Error("gallery payload must be an object");
    var allowed = ["subject_key", "identity", "face_rect", "stage"];
    Object.keys(payload).forEach(function (key) {
      if (allowed.indexOf(key) === -1) throw new Error("unexpected payload field");
    });
    if (!("subject_key" in payload) || !("identity" in payload)) {
      throw new Error("missing payload field");
    }
    if (!("face_rect" in payload) && !("stage" in payload)) {
      throw new Error("an official geometry payload carries a face_rect, a stage, or both");
    }
    gallerySubject(payload.subject_key);
    validateGalleryOfficialIdentity(payload.identity);
    if ("face_rect" in payload) artwork.validateArtworkFaceRect(payload.face_rect);
    if ("stage" in payload) artwork.validateArtworkStage(payload.stage);
    return Object.assign({}, payload);
  }
  var keys = ["subject_key"];
  if (actionId === "gallery.generate") {
    keys = keys.concat(["fields", "custom_prompt"]);
  } else if (actionId === "gallery.default.set" || actionId === "gallery.card.delete") {
    keys.push("image_id");
  } else if (actionId === "gallery.face_rect.update") {
    keys = keys.concat(["image_id", "face_rect"]);
  } else if (actionId === "gallery.stage.update") {
    keys = keys.concat(["image_id", "stage"]);
  } else if (actionId === "gallery.binding.save") {
    keys = keys.concat(["image_id", "slots"]);
  } else if (actionId === "gallery.official.select" || actionId === "gallery.official.geometry.clear") {
    keys.push("identity");
  } else if (actionId === "gallery.official.clear_selection") {
    // The subject key alone: clearing names no identity.
  } else if (actionId !== "gallery.subject.select") {
    throw new Error("unknown gallery action");
  }
  requireExactFields(payload, actionId, keys, []);
  gallerySubject(payload.subject_key);
  if (keys.indexOf("image_id") !== -1) galleryCardReference(payload.image_id);
  if (keys.indexOf("identity") !== -1) validateGalleryOfficialIdentity(payload.identity);
  if (actionId === "gallery.generate" || actionId === "gallery.binding.save") {
    var generating = actionId === "gallery.generate";
    var values = generating ? payload.fields : payload.slots;
    var catalog = generating ? GALLERY_FIELDS : GALLERY_SLOTS;
    if (!Array.isArray(values) || values.length > catalog.length ||
        (!generating && !values.length) ||
        values.some(function (value) { return typeof value !== "string" || catalog.indexOf(value) === -1; }) ||
        new Set(values).size !== values.length) {
      throw new Error("invalid gallery selection");
    }
  }
  if (actionId === "gallery.generate") {
    // Python isprintable rejects all Unicode C/Z categories except U+0020.
    requireString(payload.custom_prompt, "custom_prompt", 512);
    if (/[\p{C}\p{Z}]/u.test(payload.custom_prompt.replace(/ /g, ""))) {
      throw new Error("non-printable custom_prompt");
    }
  }
  if (actionId === "gallery.face_rect.update") artwork.validateArtworkFaceRect(payload.face_rect);
  if (actionId === "gallery.stage.update") artwork.validateArtworkStage(payload.stage);
  return Object.assign({}, payload);
}

function validateGalleryEquipment(summary) {
  requireExactFields(summary, "equipment_summary", GALLERY_SLOTS, []);
  GALLERY_SLOTS.forEach(function (slot) {
    var row = summary[slot];
    if (slot !== "accessories") {
      requireExactFields(row, "equipment slot", ["value", "display_name"], []);
      if (row.value !== null) galleryText(row.value, GALLERY_MAX_NAME, "equipment key");
      galleryText(row.display_name, GALLERY_MAX_NAME, "equipment name");
    } else {
      requireExactFields(row, "accessories", ["value", "display_names", "equipped_count"], []);
      if (!Array.isArray(row.value) || !Array.isArray(row.display_names) ||
          row.value.length > 5 || row.value.length !== row.display_names.length) {
        throw new Error("invalid accessories");
      }
      row.value.concat(row.display_names).forEach(function (value) {
        galleryText(value, GALLERY_MAX_NAME, "accessory");
      });
      // Python sorts Unicode code points, not UTF-16 code units.
      var sorted = row.value.slice().sort(compareCodePoints);
      if (JSON.stringify(sorted) !== JSON.stringify(row.value) ||
          !Number.isInteger(row.equipped_count) || row.equipped_count !== row.value.length) {
        throw new Error("invalid accessory ordering/count");
      }
    }
  });
}

function compareCodePoints(a, b) {
  var left = Array.from(a), right = Array.from(b);
  for (var i = 0; i < Math.min(left.length, right.length); i++) {
    var difference = left[i].codePointAt(0) - right[i].codePointAt(0);
    if (difference) return difference;
  }
  return left.length - right.length;
}

function validateGalleryPanel(payload) {
  requireExactFields(payload, "gallery", [
    "schema_version", "available", "kind", "subjects", "selected", "filters",
    "cards", "official_entries", "equipment_summary", "capabilities",
    "binding_warnings", "error_state"
  ], []);
  if (payload.schema_version !== GALLERY_SCHEMA_VERSION || payload.available !== true || payload.kind !== "gallery") {
    throw new Error("invalid gallery discriminator");
  }
  if (!Array.isArray(payload.subjects) || payload.subjects.length < 1 || payload.subjects.length > GALLERY_MAX_SUBJECTS) {
    throw new Error("invalid subject rail");
  }
  var subjects = new Set();
  payload.subjects.forEach(function (row, index) {
    requireExactFields(row, "subject row", ["subject_key", "kind", "display_name", "is_puppet"], []);
    var subject = gallerySubject(row.subject_key);
    if (row.kind !== subject.kind || subjects.has(row.subject_key) || row.is_puppet !== (index === 0) ||
        (index === 0 && subject.directory !== "character")) {
      throw new Error("incoherent subject rail");
    }
    galleryText(row.display_name, GALLERY_MAX_NAME, "subject display name");
    subjects.add(row.subject_key);
  });
  var selected = gallerySubject(payload.selected);
  if (!subjects.has(payload.selected)) throw new Error("selected is not in rail");
  var capability = payload.capabilities;
  requireExactFields(capability, "capabilities", [
    "supports_bindings", "supports_field_selection", "supports_free_text", "supports_personal_official_preferences", "max_cards"
  ], []);
  ["supports_bindings", "supports_field_selection", "supports_free_text", "supports_personal_official_preferences"].forEach(function (field) {
    requireBool(capability[field], field);
  });
  if (capability.max_cards !== null && capability.max_cards !== 1) throw new Error("invalid card cap");
  if (capability.supports_bindings) validateGalleryEquipment(payload.equipment_summary);
  else if (payload.equipment_summary !== null) throw new Error("unsupported equipment summary");
  validateGalleryOfficialEntries(payload.official_entries);
  if (!Array.isArray(payload.cards) || payload.cards.length > MAX_LIST_ITEMS) throw new Error("invalid cards");
  var byId = new Map(), previous = Infinity;
  var counts = { all: payload.cards.length, defaults: 0, bound: 0, pending: 0, failed: 0 };
  payload.cards.forEach(function (row) {
    requireExactFields(row, "gallery row", GALLERY_CARD_FIELDS, []);
    galleryUuid(row.image_id);
    if (byId.has(row.image_id) || ["card", "pending", "failed"].indexOf(row.status) === -1) {
      throw new Error("invalid row identity/status");
    }
    byId.set(row.image_id, row);
    galleryText(row.label, GALLERY_MAX_LABEL, "card label");
    var timestamp = galleryNumber(row.created_at, "created_at");
    if (timestamp > previous) throw new Error("cards must be newest first");
    previous = timestamp;
    requireBool(row.is_default, "is_default");
    requireBool(row.binding_present, "binding_present");
    counts.defaults += Number(row.is_default);
    counts.bound += Number(row.binding_present);
    if (row.status === "pending") counts.pending++;
    if (row.status === "failed") counts.failed++;
    var chips = row.chips, fields = row.requested_fields;
    if (!Array.isArray(chips) || chips.length > 6 || !Array.isArray(fields) || fields.length > GALLERY_FIELDS.length) {
      throw new Error("invalid chips/provenance");
    }
    chips.forEach(function (chip) { galleryText(chip, GALLERY_MAX_CHIP, "chip"); });
    fields.forEach(function (field) {
      if (typeof field !== "string" || GALLERY_FIELDS.indexOf(field) === -1) throw new Error("unknown requested field");
    });
    if (new Set(chips).size !== chips.length || new Set(fields).size !== fields.length) throw new Error("duplicate chip/field");
    if (row.status !== "card" && (row.is_default || row.binding_present || chips.length || fields.length)) {
      throw new Error("synthetic row fabricated card data");
    }
    if ((row.binding_present && !capability.supports_bindings) || (fields.length && !capability.supports_field_selection)) {
      throw new Error("unsupported card facts");
    }
    validateGalleryCardArtwork(row, selected);
    if (row.status !== "card") return;
    var slotChips = GALLERY_SLOT_LABELS.filter(function (label) { return chips.indexOf(label) !== -1; });
    var faceChips = chips.filter(function (c) { return c === "預設臉框" || c === "自訂臉框"; });
    if (faceChips.length !== 1) throw new Error("exactly one face chip required");
    var expected = slotChips.concat(faceChips, row.is_default ? ["目前預設"] : []);
    if (JSON.stringify(chips) !== JSON.stringify(expected) || Boolean(slotChips.length) !== row.binding_present) {
      throw new Error("incoherent chips");
    }
  });
  requireExactFields(payload.filters, "filters", ["all", "defaults", "bound", "pending", "failed"], []);
  Object.keys(counts).forEach(function (key) {
    requireInt(payload.filters[key], key, 0, MAX_SAFE_INTEGER);
    if (payload.filters[key] !== counts[key]) throw new Error("filter counts differ from rows");
  });
  if (counts.defaults > 1 || counts.pending > 8 || counts.failed > 1) throw new Error("too many default/pending/failed rows");
  var error = payload.error_state;
  if (error !== null) {
    requireExactFields(error, "error_state", ["code", "at"], []);
    galleryText(error.code, 64, "error code");
    if (/[^a-z0-9_]/.test(error.code)) throw new Error("invalid error identifier");
    galleryNumber(error.at, "error timestamp");
  }
  if (Boolean(counts.failed) !== (error !== null)) throw new Error("error state differs from failed row");
  var warnings = payload.binding_warnings;
  if (!Array.isArray(warnings) || warnings.length > GALLERY_MAX_WARNINGS ||
      (warnings.length && !capability.supports_bindings)) throw new Error("invalid binding warnings");
  var warningIds = [];
  warnings.forEach(function (warning) {
    requireExactFields(warning, "binding warning", ["image_id", "label", "conditions"], []);
    galleryUuid(warning.image_id);
    var card = byId.get(warning.image_id);
    if (!card || !card.binding_present || warning.label !== card.label) throw new Error("warning must name a visible bound card");
    if (!Array.isArray(warning.conditions) || warning.conditions.length < 1 || warning.conditions.length > 4) {
      throw new Error("invalid warning conditions");
    }
    warning.conditions.forEach(function (line) { galleryText(line, GALLERY_MAX_CONDITION, "condition"); });
    warningIds.push(warning.image_id);
  });
  var orderedWarnings = payload.cards.filter(function (row) { return warningIds.indexOf(row.image_id) !== -1; })
    .map(function (row) { return row.image_id; });
  if (new Set(warningIds).size !== warningIds.length || JSON.stringify(warningIds) !== JSON.stringify(orderedWarnings)) {
    throw new Error("warnings must be unique and newest first");
  }
  checkGlobalSafety(payload);
  if (jsonByteSize(payload) > MAX_CANONICAL_JSON_BYTES) throw new Error("gallery exceeds envelope size");
  return payload;
}

module.exports = {
  validateGalleryPanel: validateGalleryPanel,
  validateGalleryActionPayload: validateGalleryActionPayload,
  GALLERY_SCHEMA_VERSION: GALLERY_SCHEMA_VERSION,
  GALLERY_MAX_SUBJECTS: GALLERY_MAX_SUBJECTS,
  GALLERY_MAX_LABEL: GALLERY_MAX_LABEL,
  GALLERY_MAX_NAME: GALLERY_MAX_NAME,
  GALLERY_MAX_CHIP: GALLERY_MAX_CHIP,
  GALLERY_MAX_URL: GALLERY_MAX_URL,
  GALLERY_MAX_WARNINGS: GALLERY_MAX_WARNINGS,
  GALLERY_MAX_CONDITION: GALLERY_MAX_CONDITION,
  GALLERY_MAX_OFFICIAL_ENTRIES: GALLERY_MAX_OFFICIAL_ENTRIES,
  GALLERY_MAX_OFFICIAL_IDENTITY: GALLERY_MAX_OFFICIAL_IDENTITY,
  GALLERY_MAX_OFFICIAL_URL: MAX_MEDIA_URL,
  GALLERY_OFFICIAL_ROW_FIELDS: GALLERY_OFFICIAL_ROW_FIELDS,
  GALLERY_CARD_FIELDS: GALLERY_CARD_FIELDS,
  GALLERY_RANK_ORIGINAL: GALLERY_RANK_ORIGINAL,
  GALLERY_RANK_ALPHA: GALLERY_RANK_ALPHA,
};
