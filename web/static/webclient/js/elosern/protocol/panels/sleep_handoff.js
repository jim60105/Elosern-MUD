// sleep_handoff panel validator (mirror of
// web.webclient.presentation.sleep_handoff). The payload is the browser's
// authoritative contextual sleep-control surface: every row, reason and
// decision identity is server-authored, so this validator only enforces the
// exact bounded shape and never derives eligibility.

"use strict";

var C = require("../constants.js");
var core = require("../core.js");

var requireExactFields = core.requireExactFields;
var requireInt = core.requireInt;
var requireBool = core.requireBool;
var requireString = core.requireString;

var MAX_SAFE_INTEGER = C.MAX_SAFE_INTEGER;
var SLEEP_HANDOFF_SCHEMA_VERSION = C.SLEEP_HANDOFF_SCHEMA_VERSION;
var SLEEP_HANDOFF_MAX_ROWS = C.SLEEP_HANDOFF_MAX_ROWS;
var SLEEP_HANDOFF_MAX_NAME = C.SLEEP_HANDOFF_MAX_NAME;
var SLEEP_HANDOFF_MAX_LABEL = C.SLEEP_HANDOFF_MAX_LABEL;
var SLEEP_HANDOFF_MAX_REASON = C.SLEEP_HANDOFF_MAX_REASON;
var SLEEP_HANDOFF_MAX_SLEEP_ID = C.SLEEP_HANDOFF_MAX_SLEEP_ID;

var ROW_FIELDS = [
  "kind",
  "identity",
  "name",
  "reserve_percent",
  "stage",
  "label",
  "enabled",
  "reason",
];

var CONTINUATIONS = ["none", "pending", "paused", "complete"];

function optionalBoundedString(value, field, maximum) {
  if (value === null) {
    return;
  }
  requireString(value, field, maximum);
}

function validateSelectionRow(row) {
  requireExactFields(row, "sleep selection row", ROW_FIELDS, []);
  if (row.kind !== "return" && row.kind !== "possess") {
    throw new Error("sleep selection row kind is invalid");
  }
  requireInt(row.identity, "row identity", 1, MAX_SAFE_INTEGER);
  requireString(row.name, "row name", SLEEP_HANDOFF_MAX_NAME);
  requireString(row.stage, "row stage", 64);
  requireString(row.label, "row label", SLEEP_HANDOFF_MAX_LABEL);
  requireBool(row.enabled, "row enabled");
  if (row.reserve_percent !== null) {
    requireInt(row.reserve_percent, "row reserve_percent", 0, 100);
  }
  optionalBoundedString(row.reason, "row reason", SLEEP_HANDOFF_MAX_REASON);
  return row;
}

function validateSleepHandoffPanel(payload) {
  requireExactFields(
    payload,
    "sleep_handoff",
    [
      "schema_version",
      "available",
      "owner_id",
      "controlled_body_id",
      "transition_id",
      "selection",
      "party",
      "controlled_sleep",
      "owner_sleep",
    ],
    []
  );
  if (payload.schema_version !== SLEEP_HANDOFF_SCHEMA_VERSION) {
    throw new Error("sleep_handoff schema_version does not match registered version");
  }
  requireBool(payload.available, "available");
  if (!payload.available) {
    throw new Error("sleep_handoff available payload must be available");
  }
  requireInt(payload.owner_id, "owner_id", 1, MAX_SAFE_INTEGER);
  requireInt(payload.controlled_body_id, "controlled_body_id", 1, MAX_SAFE_INTEGER);
  requireString(payload.transition_id, "transition_id", SLEEP_HANDOFF_MAX_SLEEP_ID);

  var selection = payload.selection;
  requireExactFields(selection, "selection", ["available", "rows"], []);
  requireBool(selection.available, "selection.available");
  if (!Array.isArray(selection.rows) || selection.rows.length > SLEEP_HANDOFF_MAX_ROWS) {
    throw new Error("selection.rows exceeds its bound");
  }
  selection.rows.forEach(validateSelectionRow);

  var party = payload.party;
  requireExactFields(party, "party", ["label", "enabled", "reason"], []);
  requireString(party.label, "party label", SLEEP_HANDOFF_MAX_LABEL);
  requireBool(party.enabled, "party enabled");
  optionalBoundedString(party.reason, "party reason", SLEEP_HANDOFF_MAX_REASON);

  if (payload.controlled_sleep !== null) {
    requireExactFields(
      payload.controlled_sleep,
      "controlled_sleep",
      ["sleep_id", "revision"],
      []
    );
    requireString(
      payload.controlled_sleep.sleep_id,
      "controlled_sleep sleep_id",
      SLEEP_HANDOFF_MAX_SLEEP_ID
    );
    requireInt(
      payload.controlled_sleep.revision,
      "controlled_sleep revision",
      0,
      MAX_SAFE_INTEGER
    );
  }

  if (payload.owner_sleep !== null) {
    var owner = payload.owner_sleep;
    requireExactFields(
      owner,
      "owner_sleep",
      [
        "sleep_id",
        "revision",
        "generation",
        "dream_pending",
        "continuation",
        "continuation_available",
        "continuation_reason",
      ],
      []
    );
    requireString(owner.sleep_id, "owner_sleep sleep_id", SLEEP_HANDOFF_MAX_SLEEP_ID);
    requireInt(owner.revision, "owner_sleep revision", 0, MAX_SAFE_INTEGER);
    requireInt(owner.generation, "owner_sleep generation", 0, MAX_SAFE_INTEGER);
    requireBool(owner.dream_pending, "owner_sleep dream_pending");
    if (CONTINUATIONS.indexOf(owner.continuation) === -1) {
      throw new Error("owner_sleep continuation is invalid");
    }
    requireBool(
      owner.continuation_available,
      "owner_sleep continuation_available"
    );
    optionalBoundedString(
      owner.continuation_reason,
      "owner_sleep continuation_reason",
      SLEEP_HANDOFF_MAX_REASON
    );
  }
  return payload;
}

module.exports = {
  SLEEP_HANDOFF_SCHEMA_VERSION: SLEEP_HANDOFF_SCHEMA_VERSION,
  SLEEP_HANDOFF_MAX_ROWS: SLEEP_HANDOFF_MAX_ROWS,
  validateSleepHandoffPanel: validateSleepHandoffPanel,
};
