"use strict";

var C = require("./constants.js");

var MAX_DEPTH = C.MAX_DEPTH;
var MAX_FIELDS = C.MAX_FIELDS;
var MAX_LIST_ITEMS = C.MAX_LIST_ITEMS;
var MAX_STRING_CODE_POINTS = C.MAX_STRING_CODE_POINTS;
var MAX_SAFE_INTEGER = C.MAX_SAFE_INTEGER;
var MAX_CANONICAL_JSON_BYTES = C.MAX_CANONICAL_JSON_BYTES;
var DIALOGUE_PANEL_MAX_BYTES = C.DIALOGUE_PANEL_MAX_BYTES;
var DIALOGUE_ENVELOPE_MAX_BYTES = C.DIALOGUE_ENVELOPE_MAX_BYTES;
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

function carriesAvailableDialogue(payload) {
  if (!isPlainObject(payload)) {
    return false;
  }
  var panels = payload.panels;
  if (!isPlainObject(panels)) {
    return false;
  }
  var dialogue = panels.dialogue;
  if (!isPlainObject(dialogue)) {
    return false;
  }
  var schemaVersion = dialogue.schema_version;
  if (typeof schemaVersion !== "number" || !Number.isInteger(schemaVersion) || schemaVersion !== 3) {
    return false;
  }
  return dialogue.available === true && dialogue.kind === "dialogue";
}

function checkEnvelope(value) {
  checkGlobalSafety(value);
  if (carriesAvailableDialogue(value)) {
    if (jsonByteSize(value) > DIALOGUE_ENVELOPE_MAX_BYTES) {
      throw new Error(
        "canonical JSON exceeds " + DIALOGUE_ENVELOPE_MAX_BYTES + " bytes"
      );
    }
    var dialogue = value.panels.dialogue;
    if (jsonByteSize(dialogue) > DIALOGUE_PANEL_MAX_BYTES) {
      throw new Error(
        "dialogue panel canonical JSON exceeds " + DIALOGUE_PANEL_MAX_BYTES + " bytes"
      );
    }
    var strippedPanels = Object.create(null);
    var keys = Object.keys(value.panels);
    for (var i = 0; i < keys.length; i++) {
      var k = keys[i];
      if (k !== "dialogue") {
        strippedPanels[k] = value.panels[k];
      }
    }
    var strippedEnvelope = Object.assign({}, value, { panels: strippedPanels });
    if (jsonByteSize(strippedEnvelope) > MAX_CANONICAL_JSON_BYTES) {
      throw new Error(
        "dialogue-removed envelope canonical JSON exceeds " + MAX_CANONICAL_JSON_BYTES + " bytes"
      );
    }
  } else {
    if (jsonByteSize(value) > MAX_CANONICAL_JSON_BYTES) {
      throw new Error("canonical JSON exceeds " + MAX_CANONICAL_JSON_BYTES + " bytes");
    }
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

// Party combat command transport: the guarded combat result codes. Only the
// exit prompt may carry the bounded success data slot; every other combat
// code stays data-free, so a missing, extra or oversized field rejects at the
// result envelope itself. Mirror of
// web.webclient.actions.combat_actions.validate_party_exit_prompt_data and
// its ``DATA_CARRYING_CODES`` / ``_success_result`` guard.
var PARTY_EXIT_PROMPT_FIELDS = [
  "operation",
  "confirmation_token",
  "scope",
  "consequence",
];
var PARTY_EXIT_PROMPT_CODE = "party_exit_prompt";
var PARTY_EXIT_OPERATIONS = ["retreat", "surrender"];
var PARTY_EXIT_SCOPE = "party";
var PARTY_EXIT_MAX_TOKEN_CODE_POINTS = 128;
var PARTY_EXIT_MAX_CONSEQUENCE_CODE_POINTS = 512;
var URL_SAFE_TOKEN_RE = /^[A-Za-z0-9_-]+$/;
var COMBAT_DATA_FREE_CODES = [
  "actor_choices",
  "draft_saved",
  "needs_selection",
  "already_committed",
  "round_committed",
  "combat_terminal",
  "stale_command",
];

function validatePartyExitPromptData(value) {
  requireExactFields(value, "party exit prompt data", PARTY_EXIT_PROMPT_FIELDS, []);
  if (PARTY_EXIT_OPERATIONS.indexOf(value.operation) === -1) {
    throw new Error("party exit prompt operation must be retreat or surrender");
  }
  var token = value.confirmation_token;
  if (
    typeof token !== "string" ||
    !URL_SAFE_TOKEN_RE.test(token) ||
    codePoints(token) > PARTY_EXIT_MAX_TOKEN_CODE_POINTS
  ) {
    throw new Error(
      "party exit prompt confirmation_token must be 1.." +
        PARTY_EXIT_MAX_TOKEN_CODE_POINTS +
        " URL-safe ASCII characters"
    );
  }
  if (value.scope !== PARTY_EXIT_SCOPE) {
    throw new Error("party exit prompt scope must be 'party'");
  }
  var consequence = value.consequence;
  var consequenceLength = codePoints(consequence);
  if (
    typeof consequence !== "string" ||
    consequenceLength < 1 ||
    consequenceLength > PARTY_EXIT_MAX_CONSEQUENCE_CODE_POINTS
  ) {
    throw new Error(
      "party exit prompt consequence must be 1.." +
        PARTY_EXIT_MAX_CONSEQUENCE_CODE_POINTS +
        " code points"
    );
  }
  return value;
}

function validateCombatResultData(code, hasData, data) {
  if (code === PARTY_EXIT_PROMPT_CODE) {
    if (!hasData) {
      throw new Error("party_exit_prompt requires its exact data slot");
    }
    validatePartyExitPromptData(data);
    return;
  }
  if (hasData && COMBAT_DATA_FREE_CODES.indexOf(code) !== -1) {
    throw new Error("combat result " + code + " must not carry data");
  }
}

// The read-only route preview (wilderness-travel-planning-ui): a successful
// `travel.plan` result carries exactly the planner's bounded data slot,
// mirror of world.rules.travel_plan.TravelPlan.as_data. Indices are
// zero-based and nullable; a same-cell query has no steps, no indices and
// the destination_reached reason. The stop and nightfall indices are
// independent (a pace stop may precede nightfall), and the durations are the
// server's own (their sum is never re-derived here). Every other code keeps
// the generic slot rules only.
var TRAVEL_PLAN_CODE = "travel.plan";
var TRAVEL_PLAN_FIELDS = [
  "origin",
  "destination",
  "steps",
  "total_seconds",
  "nightfall_index",
  "stop_index",
  "stop_reason",
];
var TRAVEL_PLAN_MAX_STEPS = 60;
var TRAVEL_PLAN_STOP_REASONS = [
  "member_asleep",
  "preflight_refused",
  "pace_threshold",
  "nightfall",
  "destination_reached",
];

function requireTravelCell(value, field) {
  requireExactFields(value, field, ["x", "y"], []);
  requireInt(value.x, field + ".x", -MAX_SAFE_INTEGER, MAX_SAFE_INTEGER);
  requireInt(value.y, field + ".y", -MAX_SAFE_INTEGER, MAX_SAFE_INTEGER);
  return value;
}

function requireTravelIndex(value, field, length) {
  if (value === null) {
    return null;
  }
  return requireInt(value, field, 0, length - 1);
}

function validateTravelPlanData(value) {
  requireExactFields(value, "travel.plan data", TRAVEL_PLAN_FIELDS, []);
  requireTravelCell(value.origin, "travel.plan origin");
  requireTravelCell(value.destination, "travel.plan destination");
  var steps = value.steps;
  if (!Array.isArray(steps) || steps.length > TRAVEL_PLAN_MAX_STEPS) {
    throw new Error("travel.plan steps must be an array of at most " + TRAVEL_PLAN_MAX_STEPS);
  }
  for (var i = 0; i < steps.length; i++) {
    var step = steps[i];
    requireExactFields(step, "travel.plan step", ["cell", "seconds", "fatigue_stage"], []);
    requireTravelCell(step.cell, "travel.plan step cell");
    requireInt(step.seconds, "travel.plan step seconds", 0, MAX_SAFE_INTEGER);
    if (C.STATUS_FATIGUE_STAGES.indexOf(step.fatigue_stage) === -1) {
      throw new Error("travel.plan step fatigue_stage is not a canonical stage");
    }
  }
  requireInt(value.total_seconds, "travel.plan total_seconds", 0, MAX_SAFE_INTEGER);
  if (TRAVEL_PLAN_STOP_REASONS.indexOf(value.stop_reason) === -1) {
    throw new Error("travel.plan stop_reason is not a stable reason");
  }
  if (steps.length === 0) {
    if (value.nightfall_index !== null || value.stop_index !== null || value.stop_reason !== "destination_reached") {
      throw new Error("an empty travel.plan has no indices and only reaches its destination");
    }
    return value;
  }
  requireTravelIndex(value.nightfall_index, "travel.plan nightfall_index", steps.length);
  if (value.stop_index === null) {
    throw new Error("a travel.plan with steps names its stop_index");
  }
  requireTravelIndex(value.stop_index, "travel.plan stop_index", steps.length);
  return value;
}

function validateTravelResultData(code, outcome, hasData, data) {
  if (code !== TRAVEL_PLAN_CODE || outcome !== "success") {
    return;
  }
  if (!hasData) {
    throw new Error("a travel.plan success requires its exact data slot");
  }
  validateTravelPlanData(data);
}

// The whole-party camp (wilderness-camping): the read-only preview and the
// committed camp each carry one exact data slot on success, mirror of
// web/webclient/actions/exploration_actions.py validate_camp_preview_data /
// validate_camp_result_data. The camp's time fields nest under `timing`
// because a data slot carries at most eight top-level fields.
var CAMP_PREVIEW_CODE = "explore.camp_preview";
var CAMP_CODE = "explore.camp";
var CAMP_MODES = ["until-dawn", "until-recovered"];
var CAMP_PHASES = ["dream", "complete", "interrupted"];
var CAMP_MAX_MEMBERS = 64;
var CAMP_MAX_EVENTS = 48;

function requireCampAscii(value, field, maximum) {
  if (typeof value !== "string" || value.length < 1 || value.length > maximum || !/^[\x00-\x7f]+$/.test(value)) {
    throw new Error(field + " must be 1.." + maximum + " ASCII characters");
  }
  return value;
}

function requireCampText(value, field, maximum) {
  requireString(value, field, maximum);
  if (!value.trim()) {
    throw new Error(field + " must not be blank");
  }
  return value;
}

function requireCampRefusal(value, field) {
  if (value === null) {
    return;
  }
  requireExactFields(value, field, ["code", "message"], []);
  requireCampAscii(value.code, field + ".code", 64);
  requireCampText(value.message, field + ".message", 512);
}

function requireCampReserves(row, field, reserves, percents) {
  var maximum = requireInt(row.reserve_max, field + ".reserve_max", 1, MAX_SAFE_INTEGER);
  reserves.forEach(function (key) {
    requireInt(row[key], field + "." + key, 0, maximum);
  });
  percents.forEach(function (key) {
    requireInt(row[key], field + "." + key, 0, 100);
  });
}

function validateCampPreviewData(value) {
  requireExactFields(
    value,
    "camp preview",
    ["available", "refusal", "dream_offerable", "default_mode", "current_tick", "current_time", "modes"],
    []
  );
  requireBool(value.available, "camp preview available");
  requireBool(value.dream_offerable, "camp preview dream_offerable");
  if (CAMP_MODES.indexOf(value.default_mode) === -1) {
    throw new Error("camp preview default_mode is not a stable value");
  }
  requireInt(value.current_tick, "camp preview current_tick", 0, MAX_SAFE_INTEGER);
  requireCampText(value.current_time, "camp preview current_time", 32);
  requireCampRefusal(value.refusal, "camp preview refusal");
  if ((value.refusal === null) !== value.available) {
    throw new Error("camp preview refusal must accompany unavailability");
  }
  var modes = value.modes;
  if (!Array.isArray(modes) || modes.length !== 2) {
    throw new Error("camp preview modes must be dawn then recovered");
  }
  var anyAvailable = false;
  modes.forEach(function (mode, index) {
    requireExactFields(
      mode,
      "camp preview mode",
      ["mode", "available", "refusal", "dream_offerable", "wake_tick", "wake_time", "members"],
      []
    );
    if (mode.mode !== CAMP_MODES[index]) {
      throw new Error("camp preview modes must be dawn then recovered");
    }
    requireBool(mode.available, "camp preview mode available");
    requireBool(mode.dream_offerable, "camp preview mode dream_offerable");
    requireCampRefusal(mode.refusal, "camp preview mode refusal");
    if (!Array.isArray(mode.members) || mode.members.length > CAMP_MAX_MEMBERS) {
      throw new Error("camp preview members exceed their bound");
    }
    if (mode.available) {
      anyAvailable = true;
      if (mode.refusal !== null || mode.wake_tick === null) {
        throw new Error("an available camp mode names its wake and no refusal");
      }
      requireInt(mode.wake_tick, "camp preview wake_tick", 0, MAX_SAFE_INTEGER);
      requireCampText(mode.wake_time, "camp preview wake_time", 32);
    } else if (
      mode.refusal === null ||
      mode.wake_tick !== null ||
      mode.wake_time !== null ||
      mode.members.length > 0 ||
      mode.dream_offerable
    ) {
      throw new Error("an unavailable camp mode carries only its refusal");
    }
    mode.members.forEach(function (row) {
      requireExactFields(
        row,
        "camp preview member",
        [
          "member_id",
          "name",
          "current_reserve",
          "predicted_reserve",
          "reserve_max",
          "current_percent",
          "predicted_percent",
          "wake_tick",
          "wake_time",
        ],
        []
      );
      requireCampAscii(row.member_id, "camp preview member_id", 64);
      requireCampText(row.name, "camp preview name", 256);
      requireCampReserves(row, "camp preview member", ["current_reserve", "predicted_reserve"], ["current_percent", "predicted_percent"]);
      requireInt(row.wake_tick, "camp preview member wake_tick", 0, MAX_SAFE_INTEGER);
      requireCampText(row.wake_time, "camp preview member wake_time", 32);
    });
  });
  if (anyAvailable !== value.available) {
    throw new Error("camp preview availability must match its modes");
  }
  return value;
}

function validateCampData(value) {
  requireExactFields(
    value,
    "camp result",
    ["camp_id", "phase", "timing", "members", "events", "interrupted", "interruption_reason"],
    []
  );
  requireCampAscii(value.camp_id, "camp result camp_id", 80);
  if (CAMP_PHASES.indexOf(value.phase) === -1) {
    throw new Error("camp result phase is not a stable value");
  }
  var timing = value.timing;
  requireExactFields(timing, "camp result timing", ["elapsed_seconds", "result_tick", "result_time", "wake_tick", "wake_time"], []);
  requireInt(timing.elapsed_seconds, "camp result elapsed_seconds", 0, MAX_SAFE_INTEGER);
  requireInt(timing.result_tick, "camp result result_tick", 0, MAX_SAFE_INTEGER);
  requireCampText(timing.result_time, "camp result result_time", 32);
  if ((timing.wake_tick === null) !== (timing.wake_time === null)) {
    throw new Error("camp result wake tick and time travel together");
  }
  if (timing.wake_tick !== null) {
    requireInt(timing.wake_tick, "camp result wake_tick", 0, MAX_SAFE_INTEGER);
    requireCampText(timing.wake_time, "camp result wake_time", 32);
  }
  requireBool(value.interrupted, "camp result interrupted");
  if (value.interrupted !== (value.phase === "interrupted")) {
    throw new Error("camp result interruption must match its phase");
  }
  if (value.interrupted) {
    requireCampAscii(value.interruption_reason, "camp result interruption_reason", 64);
  } else if (value.interruption_reason !== null) {
    throw new Error("only an interrupted camp names a reason");
  }
  if (!Array.isArray(value.members) || value.members.length > CAMP_MAX_MEMBERS) {
    throw new Error("camp result members exceed their bound");
  }
  value.members.forEach(function (row) {
    requireExactFields(
      row,
      "camp result member",
      ["member_id", "name", "reserve_before", "reserve_after", "reserve_max", "before_percent", "after_percent", "sleeping", "wake_tick"],
      []
    );
    requireCampAscii(row.member_id, "camp result member_id", 64);
    requireCampText(row.name, "camp result name", 256);
    requireCampReserves(row, "camp result member", ["reserve_before", "reserve_after"], ["before_percent", "after_percent"]);
    requireBool(row.sleeping, "camp result sleeping");
    if (row.wake_tick !== null) {
      requireInt(row.wake_tick, "camp result member wake_tick", 0, MAX_SAFE_INTEGER);
    }
  });
  if (!Array.isArray(value.events) || value.events.length > CAMP_MAX_EVENTS) {
    throw new Error("camp result events exceed their bound");
  }
  value.events.forEach(function (event) {
    requireExactFields(event, "camp result event", ["kind", "due_tick", "interactive", "text"], []);
    requireCampAscii(event.kind, "camp result event kind", 64);
    requireInt(event.due_tick, "camp result event due_tick", 0, MAX_SAFE_INTEGER);
    requireBool(event.interactive, "camp result event interactive");
    if (event.text !== null) {
      requireCampText(event.text, "camp result event text", 256);
    }
  });
  if (value.phase === "dream" && (timing.elapsed_seconds !== 0 || value.events.length > 0 || timing.wake_tick !== null)) {
    throw new Error("a dream camp result is pending at zero elapsed time");
  }
  return value;
}

function validateCampResultData(code, outcome, hasData, data) {
  if ((code !== CAMP_PREVIEW_CODE && code !== CAMP_CODE) || outcome !== "success") {
    return;
  }
  if (!hasData) {
    throw new Error("a " + code + " success requires its exact data slot");
  }
  if (code === CAMP_PREVIEW_CODE) {
    validateCampPreviewData(data);
  } else {
    validateCampData(data);
  }
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
  carriesAvailableDialogue: carriesAvailableDialogue,
  requireExactFields: requireExactFields,
  validateCombatResultData: validateCombatResultData,
  validatePartyExitPromptData: validatePartyExitPromptData,
  validateTravelResultData: validateTravelResultData,
  validateTravelPlanData: validateTravelPlanData,
  validateCampResultData: validateCampResultData,
  validateCampPreviewData: validateCampPreviewData,
  validateCampData: validateCampData,
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
