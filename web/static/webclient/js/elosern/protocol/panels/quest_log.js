// quest_log panel validator (mirror of web.webclient.presentation.quest_log).
// Split from the misc panel module.

"use strict";

var C = require("../constants.js");
var core = require("../core.js");

var jsonByteSize = core.jsonByteSize;
var requireExactFields = core.requireExactFields;
var requireInt = core.requireInt;
var requireString = core.requireString;
var hasLoneSurrogate = core.hasLoneSurrogate;

var MAX_SAFE_INTEGER = C.MAX_SAFE_INTEGER;
var MAX_CANONICAL_JSON_BYTES = C.MAX_CANONICAL_JSON_BYTES;
var QUEST_LOG_SCHEMA_VERSION = C.QUEST_LOG_SCHEMA_VERSION;
var QUEST_LOG_MAX_ROWS = C.QUEST_LOG_MAX_ROWS;
var QUEST_LOG_MAX_QUEST_ID = C.QUEST_LOG_MAX_QUEST_ID;
var QUEST_LOG_MAX_KEY = C.QUEST_LOG_MAX_KEY;
var QUEST_LOG_MAX_DISPLAY_NAME = C.QUEST_LOG_MAX_DISPLAY_NAME;
var QUEST_LOG_MAX_ISSUER_KEY = C.QUEST_LOG_MAX_ISSUER_KEY;
var QUEST_LOG_MAX_LABEL = C.QUEST_LOG_MAX_LABEL;
var QUEST_LOG_MAX_OBJECTIVE_LINE = C.QUEST_LOG_MAX_OBJECTIVE_LINE;
var QUEST_LOG_MAX_DEADLINE_LINE = C.QUEST_LOG_MAX_DEADLINE_LINE;
var QUEST_LOG_MAX_DETAIL = C.QUEST_LOG_MAX_DETAIL;
var QUEST_LOG_MAX_REWARD_LINE = C.QUEST_LOG_MAX_REWARD_LINE;
var QUEST_LOG_MAX_TRACK_LABEL = C.QUEST_LOG_MAX_TRACK_LABEL;

// Quest log panel validator (mirror of
// web.webclient.presentation.quest_log, quest-issuer-model change 8). At
// most MAX_QUEST_ROWS stored records in quest-log order; settlement and
// reward_line are null when the record's issuance can no longer be
// resolved; same surrogate guards as the party and objectives mirrors.
var QUEST_LOG_STATES = ["in_progress", "completed", "failed"];
var QUEST_LOG_SETTLEMENTS = ["counter", "auto"];

function validateQuestLogBoundedLine(value, name, field, maximum) {
  var line = requireString(value, field, maximum);
  if (!line.trim() || hasLoneSurrogate(line)) {
    throw new Error(name + " " + field + " must be non-empty");
  }
  return line;
}

function validateQuestLogIssuer(value, name) {
  requireExactFields(value, name + " issuer", ["kind", "key", "label"], []);
  if (value.kind !== "guild" && value.kind !== "npc") {
    throw new Error(name + " issuer kind must be guild or npc");
  }
  var issuerKey = validateQuestLogBoundedLine(
    value.key,
    name,
    "issuer key",
    QUEST_LOG_MAX_ISSUER_KEY
  );
  // Closed issuer-key grammar (mirror of world.rules.quest_issuance
  // parse_issuer_key): exactly one ':' separator, a guild or npc
  // namespace, and an npc remainder that is '#<positive digits>' or a
  // non-digit-only content key. The declared kind must match the
  // namespace, so a producer bug cannot ship a contradictory identity.
  var separator = issuerKey.indexOf(":");
  var namespace = separator === -1 ? null : issuerKey.slice(0, separator);
  var remainder = separator === -1 ? null : issuerKey.slice(separator + 1);
  if (
    separator === -1 ||
    issuerKey.indexOf(":", separator + 1) !== -1 ||
    namespace !== value.kind ||
    !remainder
  ) {
    throw new Error(name + " issuer key is not grammar-valid");
  }
  if (namespace === "npc" && remainder.charAt(0) === "#") {
    var pk = remainder.slice(1);
    if (!/^[0-9]+$/.test(pk) || parseInt(pk, 10) <= 0) {
      throw new Error(name + " npc issuer key must carry a positive pk");
    }
  } else if (namespace === "npc" && /^[0-9]+$/.test(remainder)) {
    throw new Error(name + " authored npc issuer key cannot be digit-only");
  }
  validateQuestLogBoundedLine(
    value.label,
    name,
    "issuer label",
    QUEST_LOG_MAX_LABEL
  );
  return value;
}

function validateQuestLogTrack(value, name) {
  requireExactFields(
    value,
    name + " track descriptor",
    ["action_id", "label", "enabled", "disabled_reason", "quantity"],
    []
  );
  if (value.action_id !== "guild.quest_track") {
    throw new Error(name + " track must be guild.quest_track");
  }
  validateQuestLogBoundedLine(
    value.label,
    name,
    "track label",
    QUEST_LOG_MAX_TRACK_LABEL
  );
  if (value.enabled !== true) {
    throw new Error(name + " track is always enabled");
  }
  if (value.disabled_reason !== null) {
    throw new Error(name + " enabled track must not carry a disabled_reason");
  }
  if (value.quantity !== null) {
    throw new Error(name + " track must not carry quantity bounds");
  }
  return value;
}

function validateQuestLogRow(value, index) {
  var name = "quest_log row " + index;
  requireExactFields(
    value,
    name,
    [
      "quest_id",
      "definition_key",
      "display_name",
      "state",
      "stage_index",
      "stage_total",
      "stage_progress",
      "objective_quantity",
      "objective_line",
      "deadline_line",
      "detail",
      "tracked",
      "issuer",
      "settlement",
      "reward_line",
      "track",
    ],
    []
  );
  validateQuestLogBoundedLine(
    value.quest_id,
    name,
    "quest_id",
    QUEST_LOG_MAX_QUEST_ID
  );
  validateQuestLogBoundedLine(
    value.definition_key,
    name,
    "definition_key",
    QUEST_LOG_MAX_KEY
  );
  validateQuestLogBoundedLine(
    value.display_name,
    name,
    "display_name",
    QUEST_LOG_MAX_DISPLAY_NAME
  );
  if (QUEST_LOG_STATES.indexOf(value.state) === -1) {
    throw new Error(name + " state is not a stable value");
  }
  requireInt(value.stage_index, "stage_index", 0, MAX_SAFE_INTEGER);
  requireInt(value.stage_total, "stage_total", 1, MAX_SAFE_INTEGER);
  requireInt(value.stage_progress, "stage_progress", 0, MAX_SAFE_INTEGER);
  requireInt(value.objective_quantity, "objective_quantity", 1, MAX_SAFE_INTEGER);
  validateQuestLogBoundedLine(
    value.objective_line,
    name,
    "objective_line",
    QUEST_LOG_MAX_OBJECTIVE_LINE
  );
  if (value.deadline_line !== null) {
    validateQuestLogBoundedLine(
      value.deadline_line,
      name,
      "deadline_line",
      QUEST_LOG_MAX_DEADLINE_LINE
    );
  }
  validateQuestLogBoundedLine(value.detail, name, "detail", QUEST_LOG_MAX_DETAIL);
  if (typeof value.tracked !== "boolean") {
    throw new Error(name + " tracked must be a boolean");
  }
  validateQuestLogIssuer(value.issuer, name);
  if (
    value.settlement !== null &&
    QUEST_LOG_SETTLEMENTS.indexOf(value.settlement) === -1
  ) {
    throw new Error(name + " settlement is not a stable value");
  }
  if (value.reward_line !== null) {
    validateQuestLogBoundedLine(
      value.reward_line,
      name,
      "reward_line",
      QUEST_LOG_MAX_REWARD_LINE
    );
  }
  // Commission coherence (mirror of the Python validator): the settlement
  // and the reward line are null together or present together.
  if ((value.settlement === null) !== (value.reward_line === null)) {
    throw new Error(
      name + " settlement and reward_line must be null together or present together"
    );
  }
  validateQuestLogTrack(value.track, name);
  return value;
}

function validateQuestLogPanel(payload) {
  requireExactFields(
    payload,
    "quest_log panel",
    ["schema_version", "available", "rows"],
    []
  );
  requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
  if (payload.schema_version !== QUEST_LOG_SCHEMA_VERSION) {
    throw new Error("unsupported quest_log schema_version");
  }
  if (payload.available !== true) {
    throw new Error("quest_log panel must be available");
  }
  var rows = payload.rows;
  if (!Array.isArray(rows)) {
    throw new Error("quest_log rows must be a list");
  }
  if (rows.length > QUEST_LOG_MAX_ROWS) {
    throw new Error(
      "quest_log rows must hold at most " + QUEST_LOG_MAX_ROWS + " entries"
    );
  }
  var normalized = [];
  var seen = {};
  for (var i = 0; i < rows.length; i++) {
    var row = validateQuestLogRow(rows[i], i + 1);
    if (Object.prototype.hasOwnProperty.call(seen, row.quest_id)) {
      throw new Error("quest_log quest_ids must be unique");
    }
    seen[row.quest_id] = true;
    normalized.push(row);
  }
  var result = {
    schema_version: QUEST_LOG_SCHEMA_VERSION,
    available: true,
    rows: normalized,
  };
  // Envelope guarantee mirrors the Python validator's closing check.
  if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
    throw new Error("quest_log payload exceeds the OOB envelope limit");
  }
  return result;
}


module.exports = {
  validateQuestLogPanel: validateQuestLogPanel,
};
