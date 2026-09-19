"use strict";

var C = require("./constants.js");

var MAX_DEPTH = C.MAX_DEPTH;
var MAX_FIELDS = C.MAX_FIELDS;
var MAX_LIST_ITEMS = C.MAX_LIST_ITEMS;
var MAX_STRING_CODE_POINTS = C.MAX_STRING_CODE_POINTS;
var MAX_SAFE_INTEGER = C.MAX_SAFE_INTEGER;
var MAX_CANONICAL_JSON_BYTES = C.MAX_CANONICAL_JSON_BYTES;
var MAX_MESSAGE_CODE_POINTS = C.MAX_MESSAGE_CODE_POINTS;
var MAX_RETIRED_EPOCHS = C.MAX_RETIRED_EPOCHS;
var MAX_RESULT_DATA_FIELDS = C.MAX_RESULT_DATA_FIELDS;
var MAX_RESULT_DATA_BYTES = C.MAX_RESULT_DATA_BYTES;
var EPOCH_RE = C.EPOCH_RE;
var EPOCH_LENGTH = C.EPOCH_LENGTH;
var IDENTIFIER_RE = C.IDENTIFIER_RE;
var PANEL_NAME_RE = C.PANEL_NAME_RE;
var REQUEST_ID_RE = C.REQUEST_ID_RE;
var CORRELATION_RE = C.CORRELATION_RE;
var NODE_ID_RE = C.NODE_ID_RE;
var FORBIDDEN_RESULT_DATA_KEYS = C.FORBIDDEN_RESULT_DATA_KEYS;

// ---------------------------------------------------------------------------
// Small value helpers.
// ---------------------------------------------------------------------------

// Bounded in-memory set of retired epochs (presentation-only).
function createRetiredEpochSet() {
  var order = [];
  var members = {};
  return {
    add: function (epoch) {
      if (Object.prototype.hasOwnProperty.call(members, epoch)) {
        return;
      }
      members[epoch] = true;
      order.push(epoch);
      while (order.length > MAX_RETIRED_EPOCHS) {
        var oldest = order.shift();
        delete members[oldest];
      }
    },
    has: function (epoch) {
      return Object.prototype.hasOwnProperty.call(members, epoch);
    },
    clear: function () {
      order = [];
      members = {};
    },
    size: function () {
      return order.length;
    },
  };
}

function isPlainObject(value) {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value)
  );
}

// Count Unicode code points (handles surrogate pairs correctly).
function codePoints(value) {
  if (typeof value !== "string") {
    return 0;
  }
  var count = 0;
  for (var index = 0; index < value.length; index++) {
    var charCode = value.charCodeAt(index);
    if (charCode >= 0xd800 && charCode <= 0xdbff) {
      index += 1;
    }
    count += 1;
  }
  return count;
}

// UTF-8 byte length of a string (code points above U+007F take 2-4 bytes).
function utf8Bytes(value) {
  var bytes = 0;
  for (var index = 0; index < value.length; index++) {
    var charCode = value.charCodeAt(index);
    if (charCode >= 0xd800 && charCode <= 0xdbff) {
      index += 1;
      var high = charCode;
      var low = value.charCodeAt(index);
      var point = (high - 0xd800) * 0x400 + (low - 0xdc00) + 0x10000;
      bytes += point > 0xffff ? 4 : 3;
    } else if (charCode > 0x7ff) {
      bytes += 3;
    } else if (charCode > 0x7f) {
      bytes += 2;
    } else {
      bytes += 1;
    }
  }
  return bytes;
}

// Canonical JSON serialization: no whitespace, sorted keys, like the server.
function canonicalJson(value) {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) {
    return "[" + value.map(canonicalJson).join(",") + "]";
  }
  var keys = Object.keys(value).sort();
  var parts = [];
  for (var i = 0; i < keys.length; i++) {
    parts.push(
      JSON.stringify(keys[i]) + ":" + canonicalJson(value[keys[i]])
    );
  }
  return "{" + parts.join(",") + "}";
}

function jsonByteSize(value) {
  return utf8Bytes(canonicalJson(value));
}

// ---------------------------------------------------------------------------
// Global JSON-safety bound table (mirror of protocol.check_json_safety).
// ---------------------------------------------------------------------------

function checkGlobalSafety(value, depth) {
  depth = depth || 0;
  if (depth > MAX_DEPTH) {
    throw new Error("nesting exceeds maximum depth " + MAX_DEPTH);
  }
  if (isPlainObject(value)) {
    var keys = Object.keys(value);
    if (keys.length > MAX_FIELDS) {
      throw new Error("object exceeds maximum of " + MAX_FIELDS + " fields");
    }
    for (var i = 0; i < keys.length; i++) {
      if (codePoints(keys[i]) > MAX_STRING_CODE_POINTS) {
        throw new Error("object key exceeds the maximum string length");
      }
      checkGlobalSafety(value[keys[i]], depth + 1);
    }
  } else if (Array.isArray(value)) {
    if (value.length > MAX_LIST_ITEMS) {
      throw new Error("list exceeds maximum of " + MAX_LIST_ITEMS + " items");
    }
    for (var j = 0; j < value.length; j++) {
      checkGlobalSafety(value[j], depth + 1);
    }
  } else if (typeof value === "number") {
    if (!isFinite(value)) {
      throw new Error("non-finite numbers are forbidden");
    }
    if (Number.isInteger(value)) {
      if (value < -MAX_SAFE_INTEGER || value > MAX_SAFE_INTEGER) {
        throw new Error("integer is outside the JavaScript-safe range");
      }
    }
  } else if (typeof value === "string") {
    if (codePoints(value) > MAX_STRING_CODE_POINTS) {
      throw new Error(
        "string exceeds the maximum of " + MAX_STRING_CODE_POINTS + " code points"
      );
    }
  }
}

function checkEnvelope(value) {
  checkGlobalSafety(value);
  if (jsonByteSize(value) > MAX_CANONICAL_JSON_BYTES) {
    throw new Error("canonical JSON exceeds " + MAX_CANONICAL_JSON_BYTES + " bytes");
  }
}

// ---------------------------------------------------------------------------
// Exact-field helpers.
// ---------------------------------------------------------------------------

function requireExactFields(payload, name, required, optional) {
  if (!isPlainObject(payload)) {
    throw new Error(name + " must be a JSON object");
  }
  // Null prototype: an own "__proto__"/"constructor"/"toString" key from a
  // JSON-parsed payload must read as unknown, not inherit a truthy value
  // from Object.prototype (webclient-align-04 final review — every panel's
  // exact-shape gate relies on this helper).
  var known = Object.create(null);
  required.forEach(function (field) {
    known[field] = true;
  });
  optional.forEach(function (field) {
    known[field] = true;
  });
  var unknown = Object.keys(payload).filter(function (field) {
    return !known[field];
  });
  if (unknown.length > 0) {
    throw new Error(name + " has unknown fields " + unknown.join(","));
  }
  required.forEach(function (field) {
    if (!Object.prototype.hasOwnProperty.call(payload, field)) {
      throw new Error(name + " is missing required field " + field);
    }
  });
  // Optional fields may be present or absent; the caller enforces the
  // conditional requirement itself.
}

function requireInt(value, field, minimum, maximum) {
  if (typeof value !== "number" || !Number.isInteger(value)) {
    throw new Error(field + " must be an integer");
  }
  if (value < minimum || value > maximum || value > MAX_SAFE_INTEGER) {
    throw new Error(field + " must be within " + minimum + ".." + maximum);
  }
  return value;
}

function requireBool(value, field) {
  if (typeof value !== "boolean") {
    throw new Error(field + " must be a boolean");
  }
  return value;
}

function requireString(value, field, maximum) {
  if (typeof value !== "string") {
    throw new Error(field + " must be a string");
  }
  if (codePoints(value) > maximum) {
    throw new Error(field + " exceeds the maximum of " + maximum + " code points");
  }
  return value;
}

function validateEpoch(value) {
  if (typeof value !== "string" || !EPOCH_RE.test(value)) {
    throw new Error(
      "presentation_epoch must be exactly " + EPOCH_LENGTH + " URL-safe ASCII characters"
    );
  }
  return value;
}

function validateIdentifier(value, field) {
  if (typeof value !== "string" || !IDENTIFIER_RE.test(value)) {
    throw new Error(
      field + " must be a 1..64 lowercase dotted or underscored identifier"
    );
  }
  return value;
}

function validatePanelName(value) {
  if (typeof value !== "string" || !PANEL_NAME_RE.test(value)) {
    throw new Error("panel names must be 1..64 lowercase identifier characters");
  }
  return value;
}

function validateRequestId(value) {
  if (typeof value !== "string" || !REQUEST_ID_RE.test(value)) {
    throw new Error(
      "request_id must be 1..64 characters of ASCII letters, digits, colon, underscore, or hyphen"
    );
  }
  return value;
}

function validateMessage(value, field) {
  var length = codePoints(value);
  if (length < 1 || length > MAX_MESSAGE_CODE_POINTS) {
    throw new Error(
      field + " must be 1.." + MAX_MESSAGE_CODE_POINTS + " Unicode code points"
    );
  }
  return value;
}

function validateCorrelationId(value) {
  if (typeof value !== "string" || !CORRELATION_RE.test(value)) {
    throw new Error(
      "correlation_id must be exactly 32 lowercase hexadecimal characters"
    );
  }
  return value;
}

function isForbiddenResultDataKey(name) {
  var segments = String(name).split(".");
  for (var i = 0; i < segments.length; i++) {
    if (FORBIDDEN_RESULT_DATA_KEYS.indexOf(segments[i]) !== -1) {
      return true;
    }
  }
  return false;
}

// Mirror of web.webclient.presentation.protocol._validate_result_data.
function validateResultData(value) {
  if (!isPlainObject(value)) {
    throw new Error("data must be a JSON object");
  }
  var keys = Object.keys(value);
  if (keys.length > MAX_RESULT_DATA_FIELDS) {
    throw new Error(
      "data exceeds the maximum of " + MAX_RESULT_DATA_FIELDS + " fields"
    );
  }
  var rejectReserved = function (name) {
    validateIdentifier(name, "data field name");
    if (isForbiddenResultDataKey(name)) {
      throw new Error("data field name '" + name + "' carries a reserved state key");
    }
  };
  var walk = function (node) {
    if (Array.isArray(node)) {
      for (var j = 0; j < node.length; j++) {
        walk(node[j]);
      }
      return;
    }
    if (node === null || node === undefined) {
      return;
    }
    var kind = typeof node;
    if (kind === "object") {
      // Dates, RegExps, Maps, and class instances reach the wire as `{}` or
      // worse; the Python validator rejects them as unsupported types.
      if (Object.prototype.toString.call(node) !== "[object Object]") {
        throw new Error("data contains an unsupported JSON value type");
      }
      var nodeKeys = Object.keys(node);
      for (var k = 0; k < nodeKeys.length; k++) {
        rejectReserved(nodeKeys[k]);
        walk(node[nodeKeys[k]]);
      }
      return;
    }
    if (kind !== "string" && kind !== "number" && kind !== "boolean") {
      throw new Error("data contains an unsupported JSON value type");
    }
  };
  walk(value);
  // Depth 1 is the slot's own position inside the envelope, mirroring the
  // Python check so a data leaf can never sit deeper than MAX_DEPTH
  // measured from the envelope root.
  checkGlobalSafety(value, 1);
  if (utf8Bytes(canonicalJson(value)) > MAX_RESULT_DATA_BYTES) {
    throw new Error(
      "data canonical JSON exceeds " + MAX_RESULT_DATA_BYTES + " bytes"
    );
  }
  return value;
}

function validateServerTime(value) {
  requireExactFields(
    value,
    "server_time",
    ["year", "season_index", "season_label", "day_in_season", "hour", "minute", "second"],
    []
  );
  requireInt(value.year, "year", 0, MAX_SAFE_INTEGER);
  requireInt(value.season_index, "season_index", 0, 3);
  var seasonLabel = requireString(value.season_label, "season_label", 32);
  if (!seasonLabel.trim()) {
    throw new Error("season_label must be non-empty");
  }
  requireInt(value.day_in_season, "day_in_season", 1, 90);
  requireInt(value.hour, "hour", 0, 23);
  requireInt(value.minute, "minute", 0, 59);
  requireInt(value.second, "second", 0, 59);
  return {
    year: value.year,
    season_index: value.season_index,
    season_label: seasonLabel,
    day_in_season: value.day_in_season,
    hour: value.hour,
    minute: value.minute,
    second: value.second,
  };
}
// not valid JSON text and cannot survive the Python UTF-8 byte check.
function hasLoneSurrogate(value) {
  var pendingHigh = false;
  for (var i = 0; i < value.length; i++) {
    var code = value.charCodeAt(i);
    if (pendingHigh) {
      if (code < 0xdc00 || code > 0xdfff) {
        return true;
      }
      pendingHigh = false;
      continue;
    }
    if (code >= 0xd800 && code <= 0xdbff) {
      pendingHigh = true;
    } else if (code >= 0xdc00 && code <= 0xdfff) {
      return true;
    }
  }
  return pendingHigh;
}

// Unified node-id / exit-ref helpers. The pre-split file carried two
// byte-identical copies (local_map and exploration sections; the bounds were
// equal — 128 and 64 — and hoisting made the later copy authoritative for
// both). One shared copy preserves the exact behaviour.
function requireNodeId(value, field) {
  requireString(value, field, C.LOCAL_MAP_MAX_NODE_ID);
  if (!NODE_ID_RE.test(value)) {
    throw new Error(field + " is not a canonical node ID");
  }
  return value;
}

function requireExitRef(value, field) {
  var maximum = C.LOCAL_MAP_MAX_EXIT_REF;
  if (typeof value !== "string" || value.length < 1 || value.length > maximum) {
    throw new Error(field + " must be 1.." + maximum + " ASCII characters");
  }
  // eslint-disable-next-line no-control-regex
  if (/[^\x00-\x7F]/.test(value)) {
    throw new Error(field + " must be ASCII");
  }
  return value;
}

module.exports = {
  createRetiredEpochSet: createRetiredEpochSet,
  isPlainObject: isPlainObject,
  codePoints: codePoints,
  utf8Bytes: utf8Bytes,
  canonicalJson: canonicalJson,
  jsonByteSize: jsonByteSize,
  checkGlobalSafety: checkGlobalSafety,
  checkEnvelope: checkEnvelope,
  requireExactFields: requireExactFields,
  requireInt: requireInt,
  requireBool: requireBool,
  requireString: requireString,
  validateEpoch: validateEpoch,
  validateIdentifier: validateIdentifier,
  validatePanelName: validatePanelName,
  validateRequestId: validateRequestId,
  validateMessage: validateMessage,
  validateCorrelationId: validateCorrelationId,
  validateResultData: validateResultData,
  validateServerTime: validateServerTime,
  hasLoneSurrogate: hasLoneSurrogate,
  requireNodeId: requireNodeId,
  requireExitRef: requireExitRef,
};
