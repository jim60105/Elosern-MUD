"use strict";

// item_holdings panel validator (mirror of
// web.webclient.presentation.item_holdings, item-holdings-panel): for one
// selected item, every party member's held count, the server-computed
// equipment delta against that member's current slot occupant, and the
// transfer verdict. Every value is server-authored; the client computes
// neither counts nor deltas.

var C = require("../constants.js");
var core = require("../core.js");

var jsonByteSize = core.jsonByteSize;
var codePoints = core.codePoints;
var requireExactFields = core.requireExactFields;
var requireInt = core.requireInt;
var requireBool = core.requireBool;
var requireString = core.requireString;
var hasLoneSurrogate = core.hasLoneSurrogate;

var MAX_SAFE_INTEGER = C.MAX_SAFE_INTEGER;
var MAX_CANONICAL_JSON_BYTES = C.MAX_CANONICAL_JSON_BYTES;
var ITEM_HOLDINGS_SCHEMA_VERSION = C.ITEM_HOLDINGS_SCHEMA_VERSION;
var ITEM_HOLDINGS_MAX_ROWS = C.ITEM_HOLDINGS_MAX_ROWS;
var ITEM_HOLDINGS_MAX_CHANGES = C.ITEM_HOLDINGS_MAX_CHANGES;
var ITEM_HOLDINGS_MAX_KEY = C.ITEM_HOLDINGS_MAX_KEY;
var ITEM_HOLDINGS_MAX_LABEL = C.ITEM_HOLDINGS_MAX_LABEL;
var ITEM_HOLDINGS_MAX_REASON = C.ITEM_HOLDINGS_MAX_REASON;

// The explicit blank-string vocabulary shared with the server validator:
// Python's str.strip and JavaScript's String.trim disagree on Unicode
// whitespace (U+0085, U+FEFF), so both use this closed ASCII set.
function isBlank(value) {
  return value.replace(/[ \t\n\r\v\f]/g, "").length === 0;
}

function boundedText(value, field, maximum) {
  requireString(value, field, maximum);
  if (codePoints(value) < 1 || isBlank(value)) {
    throw new Error(field + " must be a non-empty bounded string");
  }
  if (hasLoneSurrogate(value)) {
    throw new Error(field + " must not carry lone surrogates");
  }
  return value;
}

function itemKey(value, field) {
  if (value === null) {
    return null;
  }
  return boundedText(value, field, ITEM_HOLDINGS_MAX_KEY);
}

function amount(value, field) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new Error(field + " must be a finite number");
  }
  if (value === 0) {
    throw new Error(field + " must be non-zero");
  }
  if (Math.abs(value) > MAX_SAFE_INTEGER) {
    throw new Error(field + " exceeds the safe integer bound");
  }
  return value;
}

function validateChange(value, name) {
  requireExactFields(value, name, ["key", "label", "amount"], []);
  return {
    key: boundedText(value.key, name + ".key", ITEM_HOLDINGS_MAX_KEY),
    label: boundedText(value.label, name + ".label", ITEM_HOLDINGS_MAX_LABEL),
    amount: amount(value.amount, name + ".amount"),
  };
}

function validateDelta(value, name) {
  if (value === null) {
    return null;
  }
  if (typeof value !== "object" || Array.isArray(value)) {
    throw new Error(name + " must be a JSON object or null");
  }
  var equippable = value.equippable;
  if (typeof equippable !== "boolean") {
    throw new Error(name + ".equippable must be a boolean");
  }
  if (equippable) {
    requireExactFields(value, name, ["equippable", "changes"], []);
    if (!Array.isArray(value.changes)) {
      throw new Error(name + ".changes must be a list");
    }
    if (value.changes.length > ITEM_HOLDINGS_MAX_CHANGES) {
      throw new Error(
        name +
          ".changes must hold at most " +
          ITEM_HOLDINGS_MAX_CHANGES +
          " entries"
      );
    }
    return {
      equippable: true,
      changes: value.changes.map(function (change, index) {
        return validateChange(change, name + ".changes[" + index + "]");
      }),
    };
  }
  requireExactFields(value, name, ["equippable", "reason"], []);
  return {
    equippable: false,
    reason: boundedText(value.reason, name + ".reason", ITEM_HOLDINGS_MAX_REASON),
  };
}

function validateReceive(value, name, ownRow) {
  requireExactFields(value, name, ["enabled", "reason"], []);
  var enabled = requireBool(value.enabled, name + ".enabled");
  var reason = value.reason;
  if (reason !== null) {
    reason = boundedText(reason, name + ".reason", ITEM_HOLDINGS_MAX_REASON);
  }
  if (ownRow && enabled) {
    throw new Error(
      name + " on the viewed member's own row must be disabled"
    );
  }
  if (enabled && reason !== null) {
    throw new Error("an enabled " + name + " carries no reason");
  }
  if (!enabled && reason === null && !ownRow) {
    throw new Error("a disabled " + name + " carries its reason");
  }
  return { enabled: enabled, reason: reason };
}

function validateRow(value, name, giverId) {
  requireExactFields(
    value,
    name,
    ["member_id", "held", "equipped", "delta", "receive"],
    []
  );
  var memberId = requireInt(
    value.member_id,
    name + ".member_id",
    1,
    MAX_SAFE_INTEGER
  );
  var held = requireInt(value.held, name + ".held", 0, MAX_SAFE_INTEGER);
  var equipped = requireBool(value.equipped, name + ".equipped");
  return {
    member_id: memberId,
    held: held,
    equipped: equipped,
    delta: validateDelta(value.delta, name + ".delta"),
    receive: validateReceive(value.receive, name + ".receive", memberId === giverId),
  };
}

function validateItemHoldingsPanel(payload) {
  requireExactFields(
    payload,
    "item_holdings panel",
    ["schema_version", "available", "kind", "item_key", "giver_id", "rows"],
    []
  );
  requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
  if (payload.schema_version !== ITEM_HOLDINGS_SCHEMA_VERSION) {
    throw new Error("unsupported item_holdings schema_version");
  }
  if (payload.available !== true) {
    throw new Error("item_holdings panel must be available");
  }
  if (payload.kind !== "item_holdings") {
    throw new Error("kind must be 'item_holdings'");
  }
  var itemKeyValue = itemKey(payload.item_key, "item_key");
  var giverId = requireInt(
    payload.giver_id,
    "giver_id",
    1,
    MAX_SAFE_INTEGER
  );
  if (!Array.isArray(payload.rows)) {
    throw new Error("rows must be a list");
  }
  if (payload.rows.length > ITEM_HOLDINGS_MAX_ROWS) {
    throw new Error(
      "rows must hold at most " + ITEM_HOLDINGS_MAX_ROWS + " entries"
    );
  }
  var rows = payload.rows.map(function (row, index) {
    return validateRow(row, "row " + (index + 1), giverId);
  });
  var seen = Object.create(null);
  rows.forEach(function (row) {
    if (seen[row.member_id]) {
      throw new Error("rows must name each member once");
    }
    seen[row.member_id] = true;
  });
  if ((itemKeyValue === null) !== (rows.length === 0)) {
    throw new Error(
      "no selected item must publish no rows, and a selected item must name its members"
    );
  }
  if (rows.length > 0 && !seen[giverId]) {
    throw new Error("rows must include the viewed member");
  }
  var result = {
    schema_version: ITEM_HOLDINGS_SCHEMA_VERSION,
    available: true,
    kind: "item_holdings",
    item_key: itemKeyValue,
    giver_id: giverId,
    rows: rows,
  };
  if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
    throw new Error("item_holdings payload exceeds the OOB envelope limit");
  }
  return result;
}

module.exports = {
  validateItemHoldingsPanel: validateItemHoldingsPanel,
  ITEM_HOLDINGS_SCHEMA_VERSION: ITEM_HOLDINGS_SCHEMA_VERSION,
  ITEM_HOLDINGS_MAX_ROWS: ITEM_HOLDINGS_MAX_ROWS,
  ITEM_HOLDINGS_MAX_CHANGES: ITEM_HOLDINGS_MAX_CHANGES,
  ITEM_HOLDINGS_MAX_KEY: ITEM_HOLDINGS_MAX_KEY,
  ITEM_HOLDINGS_MAX_LABEL: ITEM_HOLDINGS_MAX_LABEL,
  ITEM_HOLDINGS_MAX_REASON: ITEM_HOLDINGS_MAX_REASON,
};
