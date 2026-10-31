// travel_log panel validator (mirror of
// web.webclient.presentation.travel_log, wilderness-travel-log-ui). Every
// notice is server-identified and server-rendered; this validator only
// enforces the exact closed kind/params union and its bounds, and a
// malformed batch is rejected whole, never trimmed into validity.

"use strict";

var C = require("../constants.js");
var core = require("../core.js");
var artwork = require("../artwork.js");

var requireExactFields = core.requireExactFields;
var requireInt = core.requireInt;
var requireBool = core.requireBool;
var requireString = core.requireString;
var requireNodeId = core.requireNodeId;
var isPlainObject = core.isPlainObject;
var jsonByteSize = core.jsonByteSize;

var MAX_SAFE_INTEGER = C.MAX_SAFE_INTEGER;
var TRAVEL_LOG_SCHEMA_VERSION = C.TRAVEL_LOG_SCHEMA_VERSION;
var TRAVEL_LOG_MAX_ENTRIES = C.TRAVEL_LOG_MAX_ENTRIES;
var MAX_NAME = C.TRAVEL_LOG_MAX_NAME;
var MAX_PROSE = C.TRAVEL_LOG_MAX_PROSE;

var FATIGUE_STAGES = ["normal", "light", "moderate", "severe", "sleeping", "forced_sleep"];

var PARAM_FIELDS = {
  region_entered: ["name"],
  woodland_entered: ["name"],
  ford_crossed: ["name"],
  hostile_sighted: ["name", "count", "threat"],
  landmark_sighted: ["name", "bearing", "distance_km"],
  landmark_reached: ["arrival_node", "name", "lit_district", "prose", "artwork"],
  fatigue_stage: ["member_id", "name", "stage", "label"],
  dusk: [],
  nightfall: [],
  camp_result: ["summary"],
  look: ["prose"],
};

var ENTRY_FIELDS = ["id", "kind", "tick", "day", "time", "text", "params"];

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
    throw new Error(field + " must not be blank");
  }
  return value;
}

function optionalName(value, field) {
  if (value !== null) {
    requireString(value, field, MAX_NAME);
  }
}

function validateParams(kind, params) {
  requireExactFields(params, kind + " params", PARAM_FIELDS[kind], []);
  switch (kind) {
    case "region_entered":
    case "woodland_entered":
    case "ford_crossed":
      requireString(params.name, "name", MAX_NAME);
      break;
    case "hostile_sighted":
      requireString(params.name, "name", MAX_NAME);
      requireInt(params.count, "count", 1, MAX_SAFE_INTEGER);
      optionalName(params.threat, "threat");
      break;
    case "landmark_sighted":
      optionalName(params.name, "name");
      requireString(params.bearing, "bearing", MAX_NAME);
      requireInt(params.distance_km, "distance_km", 0, MAX_SAFE_INTEGER);
      break;
    case "landmark_reached":
      requireNodeId(params.arrival_node, "arrival_node");
      if (params.arrival_node.length > C.TRAVEL_LOG_MAX_NODE_ID) {
        throw new Error("arrival_node exceeds its bound");
      }
      requireString(params.name, "name", MAX_NAME);
      optionalName(params.lit_district, "lit_district");
      requireString(params.prose, "prose", MAX_PROSE);
      if (params.artwork !== null) {
        artwork.validateArtwork(params.artwork);
      }
      break;
    case "fatigue_stage":
      requireAscii(params.member_id, "member_id", C.TRAVEL_LOG_MAX_MEMBER_ID);
      requireString(params.name, "name", MAX_NAME);
      if (FATIGUE_STAGES.indexOf(params.stage) === -1) {
        throw new Error("stage must be a canonical fatigue stage");
      }
      requireString(params.label, "label", MAX_NAME);
      break;
    case "camp_result":
      requireString(params.summary, "summary", MAX_NAME);
      break;
    case "look":
      requireString(params.prose, "prose", MAX_PROSE);
      break;
    default:
      break;
  }
}

function validateEntry(entry, seen) {
  requireExactFields(entry, "travel_log entry", ENTRY_FIELDS, []);
  requireAscii(entry.id, "id", C.TRAVEL_LOG_MAX_ID);
  if (seen[entry.id]) {
    throw new Error("travel_log entry ids must be unique");
  }
  seen[entry.id] = true;
  if (typeof entry.kind !== "string" || !Object.prototype.hasOwnProperty.call(PARAM_FIELDS, entry.kind)) {
    throw new Error("travel_log entry kind is unknown");
  }
  requireInt(entry.tick, "tick", 0, MAX_SAFE_INTEGER);
  requireInt(entry.day, "day", 0, MAX_SAFE_INTEGER);
  requireNonblank(entry.time, "time", C.TRAVEL_LOG_MAX_TIME);
  requireNonblank(entry.text, "text", C.TRAVEL_LOG_MAX_TEXT);
  if (!isPlainObject(entry.params)) {
    throw new Error("travel_log entry params must be an object");
  }
  validateParams(entry.kind, entry.params);
}

function validateTravelLogPanel(payload) {
  requireExactFields(payload, "travel_log", ["schema_version", "available", "entries"], []);
  if (payload.schema_version !== TRAVEL_LOG_SCHEMA_VERSION) {
    throw new Error("travel_log schema_version does not match registered version");
  }
  requireBool(payload.available, "available");
  if (!payload.available) {
    throw new Error("travel_log available payload must be available");
  }
  if (!Array.isArray(payload.entries) || payload.entries.length > TRAVEL_LOG_MAX_ENTRIES) {
    throw new Error("travel_log entries exceed their bound");
  }
  var seen = Object.create(null);
  payload.entries.forEach(function (entry) {
    validateEntry(entry, seen);
  });
  if (jsonByteSize(payload) > C.TRAVEL_LOG_MAX_BYTES) {
    throw new Error("travel_log exceeds its canonical byte bound");
  }
  return payload;
}

module.exports = {
  TRAVEL_LOG_SCHEMA_VERSION: TRAVEL_LOG_SCHEMA_VERSION,
  TRAVEL_LOG_MAX_ENTRIES: TRAVEL_LOG_MAX_ENTRIES,
  TRAVEL_LOG_KINDS: Object.keys(PARAM_FIELDS),
  validateTravelLogPanel: validateTravelLogPanel,
};
