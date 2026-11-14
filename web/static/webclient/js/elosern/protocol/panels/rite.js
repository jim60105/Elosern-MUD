// rite panel validator (mirror of web.webclient.presentation.rite,
// landmark-rite-panel). The panel is the committed server-owned data for one
// landmark rite; this validator enforces the exact version-1 shape and every
// bound and rejects a malformed or oversize panel whole, never trimming it
// into validity. `art` delegates to the canonical artwork descriptor
// validator (panels/travel_log.js does the same for `landmark_reached`).

"use strict";

var C = require("../constants.js");
var core = require("../core.js");
var artwork = require("../artwork.js");

var requireExactFields = core.requireExactFields;
var requireInt = core.requireInt;
var requireBool = core.requireBool;
var requireString = core.requireString;
var isPlainObject = core.isPlainObject;
var jsonByteSize = core.jsonByteSize;

var MAX_SAFE_INTEGER = C.MAX_SAFE_INTEGER;
var RITE_SCHEMA_VERSION = C.RITE_SCHEMA_VERSION;
var RITE_MAX_BYTES = C.RITE_MAX_BYTES;
var RITE_MAX_DISTRICT_KEY = C.RITE_MAX_DISTRICT_KEY;
var RITE_MAX_DISTRICT_NAME = C.RITE_MAX_DISTRICT_NAME;
var RITE_MAX_LANDMARK_NAME = C.RITE_MAX_LANDMARK_NAME;
var RITE_MAX_GUARDIAN_NAME = C.RITE_MAX_GUARDIAN_NAME;
var RITE_MAX_GUARDIAN_FORM = C.RITE_MAX_GUARDIAN_FORM;
var RITE_MAX_OPTIONS = C.RITE_MAX_OPTIONS;
var RITE_MAX_OPTION_LABEL = C.RITE_MAX_OPTION_LABEL;
var RITE_MAX_PERFORMERS = C.RITE_MAX_PERFORMERS;
var RITE_MAX_PERFORMER_NAME = C.RITE_MAX_PERFORMER_NAME;
var RITE_MAX_SEEN = C.RITE_MAX_SEEN;
var RITE_MAX_DELIVERY_ID = C.RITE_MAX_DELIVERY_ID;
var RITE_MAX_SCENE_ID = C.RITE_MAX_SCENE_ID;
var RITE_MAX_SCENE_REVISION = C.RITE_MAX_SCENE_REVISION;
var RITE_MAX_DELIVERY_NAME = C.RITE_MAX_DELIVERY_NAME;
var RITE_MAX_LINES = C.RITE_MAX_LINES;
var RITE_MAX_LINE_TEXT = C.RITE_MAX_LINE_TEXT;

var RITE_KIND = "rite";
var RITE_DELIVERY_KIND = "formal";
var SPEAKERS = ["actor", "host"];

var PANEL_FIELDS = [
  "schema_version",
  "available",
  "kind",
  "district",
  "guardian",
  "art",
  "options",
  "performers",
  "delivery",
  "seen",
];
var DISTRICT_FIELDS = ["key", "name", "landmark", "lit"];
var GUARDIAN_FIELDS = ["name", "form"];
var OPTION_FIELDS = ["key", "label", "companion"];
var PERFORMER_FIELDS = ["member_id", "name", "owner"];
var DELIVERY_FIELDS = [
  "kind",
  "delivery_id",
  "scene_id",
  "scene_revision",
  "actor_name",
  "guardian_name",
  "lines",
];
var NARRATION_FIELDS = ["kind", "text"];
var SPEECH_FIELDS = ["kind", "speaker", "text"];

function exact(value, name, fields) {
  requireExactFields(value, name, fields, []);
  return value;
}

function requireAscii(value, field, maximum) {
  // eslint-disable-next-line no-control-regex
  if (typeof value !== "string" || value.length < 1 || value.length > maximum || /[^\x00-\x7F]/.test(value)) {
    throw new Error(field + " must be 1.." + maximum + " ASCII characters");
  }
  return value;
}

function requireNonblank(value, field, maximum) {
  requireString(value, field, maximum);
  if (value.trim() === "") {
    throw new Error(field + " must be non-blank");
  }
  return value;
}

function requireText(value, field, maximum) {
  requireString(value, field, maximum);
  if (value.length < 1) {
    throw new Error(field + " must be 1.." + maximum + " code points");
  }
  return value;
}

// An authored option key. Character inspection rather than a `$`-anchored
// regex: JavaScript's `$` also matches before a trailing line terminator, so
// "a\n" would otherwise pass where Python's fullmatch rejects it.
function isOptionKey(value) {
  if (typeof value !== "string" || value.length < 1 || value.length > 32) {
    return false;
  }
  for (var index = 0; index < value.length; index += 1) {
    var code = value.charCodeAt(index);
    var lower = code >= 97 && code <= 122;
    var digit = code >= 48 && code <= 57;
    if (index === 0 ? !lower : !(lower || digit || code === 95)) {
      return false;
    }
  }
  return true;
}

function validateLines(lines) {
  if (!Array.isArray(lines) || lines.length < 1 || lines.length > RITE_MAX_LINES) {
    throw new Error("delivery.lines must be 1.." + RITE_MAX_LINES + " entries");
  }
  lines.forEach(function (line) {
    if (!isPlainObject(line) || (line.kind !== "narration" && line.kind !== "speech")) {
      throw new Error("delivery line kind is invalid");
    }
    exact(line, "delivery line", line.kind === "narration" ? NARRATION_FIELDS : SPEECH_FIELDS);
    if (line.kind === "speech" && SPEAKERS.indexOf(line.speaker) === -1) {
      throw new Error("delivery speech speaker is invalid");
    }
    requireText(line.text, "delivery line text", RITE_MAX_LINE_TEXT);
  });
}

function validateDelivery(delivery) {
  exact(delivery, "delivery", DELIVERY_FIELDS);
  if (delivery.kind !== RITE_DELIVERY_KIND) {
    throw new Error("delivery.kind must be " + RITE_DELIVERY_KIND);
  }
  requireAscii(delivery.delivery_id, "delivery.delivery_id", RITE_MAX_DELIVERY_ID);
  requireAscii(delivery.scene_id, "delivery.scene_id", RITE_MAX_SCENE_ID);
  requireAscii(delivery.scene_revision, "delivery.scene_revision", RITE_MAX_SCENE_REVISION);
  requireNonblank(delivery.actor_name, "delivery.actor_name", RITE_MAX_DELIVERY_NAME);
  requireNonblank(delivery.guardian_name, "delivery.guardian_name", RITE_MAX_DELIVERY_NAME);
  validateLines(delivery.lines);
}

function validateOptions(options) {
  if (!Array.isArray(options) || options.length < 1 || options.length > RITE_MAX_OPTIONS) {
    throw new Error("options must be 1.." + RITE_MAX_OPTIONS + " entries");
  }
  var keys = [];
  options.forEach(function (option) {
    var row = exact(option, "option", OPTION_FIELDS);
    if (!isOptionKey(row.key)) {
      throw new Error("option key is invalid");
    }
    if (keys.indexOf(row.key) !== -1) {
      throw new Error("option keys must be unique");
    }
    keys.push(row.key);
    requireNonblank(row.label, "label", RITE_MAX_OPTION_LABEL);
    requireBool(row.companion, "companion");
  });
  return keys;
}

function validatePerformers(performers) {
  if (!Array.isArray(performers) || performers.length < 1 || performers.length > RITE_MAX_PERFORMERS) {
    throw new Error("performers must be 1.." + RITE_MAX_PERFORMERS + " entries");
  }
  var memberIds = [];
  var owners = 0;
  performers.forEach(function (performer, index) {
    var row = exact(performer, "performer", PERFORMER_FIELDS);
    var memberId = row.member_id;
    if (index === 0) {
      if (memberId !== null) {
        throw new Error("the first performer must have a null member_id");
      }
    } else {
      if (memberId === null) {
        throw new Error("only the first performer may have a null member_id");
      }
      requireInt(memberId, "member_id", 1, MAX_SAFE_INTEGER);
      if (memberIds.indexOf(memberId) !== -1) {
        throw new Error("member_id values must be unique");
      }
      memberIds.push(memberId);
    }
    requireNonblank(row.name, "name", RITE_MAX_PERFORMER_NAME);
    if (requireBool(row.owner, "owner")) {
      owners += 1;
    }
  });
  if (owners > 1) {
    throw new Error("at most one performer may be the record owner");
  }
}

function validateSeen(seen, optionKeys) {
  if (!Array.isArray(seen) || seen.length > RITE_MAX_SEEN) {
    throw new Error("seen must be 0.." + RITE_MAX_SEEN + " entries");
  }
  var recorded = [];
  seen.forEach(function (key) {
    if (typeof key !== "string" || optionKeys.indexOf(key) === -1) {
      throw new Error("seen keys must name an option");
    }
    if (recorded.indexOf(key) !== -1) {
      throw new Error("seen keys must be unique");
    }
    recorded.push(key);
  });
}

function validateRitePanel(payload) {
  exact(payload, "rite", PANEL_FIELDS);
  if (payload.schema_version !== RITE_SCHEMA_VERSION) {
    throw new Error("rite schema_version does not match registered version");
  }
  requireBool(payload.available, "available");
  if (!payload.available) {
    throw new Error("rite available payload must be available");
  }
  if (payload.kind !== RITE_KIND) {
    throw new Error("kind must be " + RITE_KIND);
  }

  var district = exact(payload.district, "district", DISTRICT_FIELDS);
  requireAscii(district.key, "district.key", RITE_MAX_DISTRICT_KEY);
  requireNonblank(district.name, "district.name", RITE_MAX_DISTRICT_NAME);
  requireNonblank(district.landmark, "district.landmark", RITE_MAX_LANDMARK_NAME);
  requireBool(district.lit, "district.lit");

  var guardian = exact(payload.guardian, "guardian", GUARDIAN_FIELDS);
  requireNonblank(guardian.name, "guardian.name", RITE_MAX_GUARDIAN_NAME);
  requireNonblank(guardian.form, "guardian.form", RITE_MAX_GUARDIAN_FORM);

  if (payload.art !== null) {
    artwork.validateArtwork(payload.art);
  }

  var optionKeys = validateOptions(payload.options);
  validatePerformers(payload.performers);
  validateSeen(payload.seen, optionKeys);
  if (payload.delivery !== null) {
    validateDelivery(payload.delivery);
  }

  if (jsonByteSize(payload) > RITE_MAX_BYTES) {
    throw new Error("rite exceeds its canonical byte bound");
  }
  return payload;
}

module.exports = {
  RITE_SCHEMA_VERSION: RITE_SCHEMA_VERSION,
  RITE_MAX_OPTIONS: RITE_MAX_OPTIONS,
  RITE_MAX_PERFORMERS: RITE_MAX_PERFORMERS,
  RITE_MAX_SEEN: RITE_MAX_SEEN,
  validateRitePanel: validateRitePanel,
};