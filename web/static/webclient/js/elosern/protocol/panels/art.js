"use strict";

var C = require("../constants.js");
var core = require("../core.js");

var isPlainObject = core.isPlainObject;
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

// Panel discriminator dispatch: the unavailable form is common to every
// registered panel; the available form is validated against its schema.

// Exact available art panel v1 schema (mirror of
// web.webclient.presentation.art, webclient-art-panel D1).
var ART_PLACEHOLDER_KINDS = ["missing", "unavailable"];
var ART_ROLES = ["隊友", "敵方", "對話對象", "人物"];

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
    ["archetype", "label", "subject_key", "status", "url", "aspect_ratio", "alt", "placeholder"],
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
  if (placeholder === null && status !== "done") {
    throw new Error("scene placeholder must be present unless done");
  }
  if (placeholder !== null && status === "done") {
    throw new Error("a done scene must not carry a placeholder");
  }
  return {
    archetype: value.archetype,
    label: label,
    subject_key: value.subject_key,
    status: status,
    url: url,
    aspect_ratio: value.aspect_ratio,
    alt: alt,
    placeholder: placeholder,
  };
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

function validateArtCatalogEntry(value) {
  requireExactFields(
    value,
    "art catalog entry",
    ["subject_key", "status", "url", "aspect_ratio", "alt", "placeholder", "face_rect", "context"],
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
  if (url !== null && faceRect === null) {
    throw new Error("a catalog entry with a url carries a face_rect");
  }
  if (url === null && faceRect !== null) {
    throw new Error("a catalog placeholder carries no face_rect");
  }
  return value;
}

// Exact gallery v1 mirror. Display labels and matching facts are server-owned.
var GALLERY_SCHEMA_VERSION = 1;
var GALLERY_MAX_SUBJECTS = 24;
var GALLERY_MAX_LABEL = 128;
var GALLERY_MAX_NAME = 64;
var GALLERY_MAX_CHIP = 16;
var GALLERY_MAX_URL = 129;
var GALLERY_MAX_WARNINGS = 5;
var GALLERY_MAX_CONDITION = 512;
var GALLERY_SLOTS = ["weapon_main", "weapon_off", "armor", "accessories"];
var GALLERY_SLOT_LABELS = ["主手", "副手", "防具", "飾品"];
var GALLERY_FIELDS = ["appearance"].concat(GALLERY_SLOTS);
var GALLERY_UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

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

function validateGalleryFaceRect(value) {
  var rect = validateArtFaceRect(value);
  if (!rect || rect.w <= 0 || rect.h <= 0 || rect.x + rect.w > 1 || rect.y + rect.h > 1) {
    throw new Error("invalid face_rect");
  }
  return rect;
}

// Exact, kind-neutral mirror of actions/gallery_actions.py. Capability
// refusals belong to the server, not this schema or the future gallery UI.
function validateGalleryActionPayload(actionId, payload) {
  var keys = ["subject_key"];
  if (actionId === "gallery.generate") {
    keys = keys.concat(["fields", "custom_prompt"]);
  } else if (actionId === "gallery.default.set" || actionId === "gallery.card.delete") {
    keys.push("image_id");
  } else if (actionId === "gallery.face_rect.update") {
    keys = keys.concat(["image_id", "face_rect"]);
  } else if (actionId === "gallery.binding.save") {
    keys = keys.concat(["image_id", "slots"]);
  } else if (actionId !== "gallery.subject.select") {
    throw new Error("unknown gallery action");
  }
  requireExactFields(payload, actionId, keys, []);
  gallerySubject(payload.subject_key);
  if (keys.indexOf("image_id") !== -1) galleryUuid(payload.image_id);
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
  if (actionId === "gallery.face_rect.update") validateGalleryFaceRect(payload.face_rect);
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
    "cards", "equipment_summary", "capabilities", "binding_warnings", "error_state"
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
    "supports_bindings", "supports_field_selection", "supports_free_text", "max_cards"
  ], []);
  ["supports_bindings", "supports_field_selection", "supports_free_text"].forEach(function (field) {
    requireBool(capability[field], field);
  });
  if (capability.max_cards !== null && capability.max_cards !== 1) throw new Error("invalid card cap");
  if (capability.supports_bindings) validateGalleryEquipment(payload.equipment_summary);
  else if (payload.equipment_summary !== null) throw new Error("unsupported equipment summary");
  if (!Array.isArray(payload.cards) || payload.cards.length > MAX_LIST_ITEMS) throw new Error("invalid cards");
  var byId = new Map(), previous = Infinity;
  var counts = { all: payload.cards.length, defaults: 0, bound: 0, pending: 0, failed: 0 };
  payload.cards.forEach(function (row) {
    requireExactFields(row, "gallery row", [
      "image_id", "status", "label", "url", "face_rect", "is_default", "chips",
      "requested_fields", "binding_present", "created_at"
    ], []);
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
    if (row.status !== "card") {
      if (row.url !== null || row.face_rect !== null || row.is_default || row.binding_present || chips.length || fields.length) {
        throw new Error("synthetic row fabricated card data");
      }
      return;
    }
    var url = galleryText(row.url, GALLERY_MAX_URL, "gallery url");
    var prefix = "/art/gallery/" + selected.directory + "/" + selected.key + "/" + row.image_id;
    if (url.indexOf(prefix) !== 0 || [".png", ".webp", ".jpg", ".avif"].indexOf(url.slice(prefix.length)) === -1) {
      throw new Error("url must name selected subject and image");
    }
    var rect = validateGalleryFaceRect(row.face_rect);
    var slotChips = GALLERY_SLOT_LABELS.filter(function (label) { return chips.indexOf(label) !== -1; });
    var faceChip = rect.x === 0.25 && rect.y === 0.06 && rect.w === 0.5 && rect.h === 0.5 ? "預設臉框" : "自訂臉框";
    var expected = slotChips.concat([faceChip], row.is_default ? ["目前預設"] : []);
    if (JSON.stringify(chips) !== JSON.stringify(expected) || Boolean(slotChips.length) !== row.binding_present) {
      throw new Error("incoherent chips");
    }
    if ((row.binding_present && !capability.supports_bindings) || (fields.length && !capability.supports_field_selection)) {
      throw new Error("unsupported card facts");
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
  validateGalleryPanel: validateGalleryPanel,
  validateGalleryActionPayload: validateGalleryActionPayload,
  validateArtFaceRect: validateArtFaceRect,
  GALLERY_SCHEMA_VERSION: GALLERY_SCHEMA_VERSION,
  GALLERY_MAX_SUBJECTS: GALLERY_MAX_SUBJECTS,
  GALLERY_MAX_LABEL: GALLERY_MAX_LABEL,
  GALLERY_MAX_NAME: GALLERY_MAX_NAME,
  GALLERY_MAX_CHIP: GALLERY_MAX_CHIP,
  GALLERY_MAX_URL: GALLERY_MAX_URL,
  GALLERY_MAX_WARNINGS: GALLERY_MAX_WARNINGS,
  GALLERY_MAX_CONDITION: GALLERY_MAX_CONDITION,
};
