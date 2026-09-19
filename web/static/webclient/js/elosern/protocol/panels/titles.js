"use strict";

var C = require("../constants.js");
var core = require("../core.js");

var codePoints = core.codePoints;
var jsonByteSize = core.jsonByteSize;
var requireExactFields = core.requireExactFields;
var requireInt = core.requireInt;
var requireBool = core.requireBool;
var requireString = core.requireString;
var validateIdentifier = core.validateIdentifier;

var MAX_SAFE_INTEGER = C.MAX_SAFE_INTEGER;
var MAX_CANONICAL_JSON_BYTES = C.MAX_CANONICAL_JSON_BYTES;
var TITLE_BALLOT_MAX_CANDIDATES = C.TITLE_BALLOT_MAX_CANDIDATES;
var TITLE_BALLOT_MAX_DISPLAY = C.TITLE_BALLOT_MAX_DISPLAY;
var TITLE_BALLOT_MAX_BASIS = C.TITLE_BALLOT_MAX_BASIS;
var TITLE_CODEX_MAX_ROWS = C.TITLE_CODEX_MAX_ROWS;
var TITLE_CODEX_MAX_DISPLAY = C.TITLE_CODEX_MAX_DISPLAY;
var TITLE_CODEX_MAX_BASIS = C.TITLE_CODEX_MAX_BASIS;
var TITLE_CODEX_MAX_FULL_TITLE = C.TITLE_CODEX_MAX_FULL_TITLE;
var TITLE_CODEX_MAX_BALLOT = C.TITLE_CODEX_MAX_BALLOT;
var TITLE_CODEX_BASIS_WIRE_MAX = C.TITLE_CODEX_BASIS_WIRE_MAX;
var TITLE_CODEX_CATEGORIES = C.TITLE_CODEX_CATEGORIES;

// -------------------------------------------------------------------------
// title_ballot panel validator (mirror of web.webclient.presentation.
// title_ballot, title-epithet-nomination D4). Zero candidates is the
// legitimate idle form; the rules layer never truncates the basis, and
// neither does this mirror.
// -------------------------------------------------------------------------

function validateTitleBallotCandidate(value, position) {
  requireExactFields(
    value,
    "title ballot candidate",
    ["index", "display", "basis"],
    []
  );
  requireInt(value.index, "candidate index", 1, TITLE_BALLOT_MAX_CANDIDATES);
  if (value.index !== position) {
    throw new Error("candidate indices must be strictly 1..n ascending");
  }
  requireString(value.display, "candidate display", TITLE_BALLOT_MAX_DISPLAY);
  if (codePoints(value.display) < 1) {
    throw new Error("candidate display must be non-empty");
  }
  requireString(value.basis, "candidate basis", TITLE_BALLOT_MAX_BASIS);
  if (codePoints(value.basis) < 1) {
    throw new Error("candidate basis must be non-empty");
  }
  return {
    index: value.index,
    display: value.display,
    basis: value.basis,
  };
}

// Exact available title_ballot panel v1 schema.
function validateTitleBallotPanel(payload) {
  requireExactFields(
    payload,
    "title_ballot panel",
    ["schema_version", "available", "kind", "candidates"],
    []
  );
  requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
  if (payload.schema_version !== 1) {
    throw new Error("unsupported title_ballot schema_version");
  }
  if (payload.available !== true || payload.kind !== "title_ballot") {
    throw new Error(
      "title_ballot panel must be available with kind title_ballot"
    );
  }
  var candidates = payload.candidates;
  if (!Array.isArray(candidates)) {
    throw new Error("title ballot candidates must be a list");
  }
  if (candidates.length > TITLE_BALLOT_MAX_CANDIDATES) {
    throw new Error(
      "title ballot candidates must hold at most " +
        TITLE_BALLOT_MAX_CANDIDATES +
        " entries"
    );
  }
  var normalized = [];
  for (var i = 0; i < candidates.length; i++) {
    normalized.push(validateTitleBallotCandidate(candidates[i], i + 1));
  }
  var result = {
    schema_version: 1,
    available: true,
    kind: "title_ballot",
    candidates: normalized,
  };
  // Envelope guarantee: the per-field ceilings keep any legal ballot far
  // below the envelope limit; an over-limit payload can only come from a
  // producer bug and fails closed.
  if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
    throw new Error("title_ballot payload exceeds the OOB envelope limit");
  }
  return result;
}

// -------------------------------------------------------------------------
// title_codex panel validator (mirror of web.webclient.presentation.
// title_codex, title-codex-removal D5/D7). Bounds are owned by
// world/rules/title_view.py; the hint/flavor exclusivity and the category
// closed set are re-asserted here exactly as the Python validator does.
// -------------------------------------------------------------------------

function inCategorySet(value) {
  for (var i = 0; i < TITLE_CODEX_CATEGORIES.length; i++) {
    if (TITLE_CODEX_CATEGORIES[i] === value) {
      return true;
    }
  }
  return false;
}

function validateTitleCodexFixedRow(value, position) {
  var label = "title codex fixed row " + position;
  requireExactFields(
    value,
    label,
    [
      "key",
      "display",
      "category",
      "hint",
      "flavor",
      "unlocked",
      "granted_tick",
    ],
    []
  );
  validateIdentifier(value.key, label + " key");
  requireString(value.display, label + " display", TITLE_CODEX_MAX_DISPLAY);
  if (codePoints(value.display.trim()) < 1) {
    throw new Error(label + " display must be non-empty");
  }
  requireString(value.category, label + " category", 32);
  if (!inCategorySet(value.category)) {
    throw new Error(label + " category is outside the closed set");
  }
  var unlocked = requireBool(value.unlocked, label + " unlocked");
  var hint = requireString(value.hint, label + " hint", TITLE_CODEX_MAX_BASIS);
  var flavor = requireString(
    value.flavor,
    label + " flavor",
    TITLE_CODEX_MAX_BASIS
  );
  if (unlocked && codePoints(hint) > 0) {
    throw new Error(label + " unlocked row must not carry a hint");
  }
  if (!unlocked && codePoints(flavor) > 0) {
    throw new Error(label + " locked row must not carry flavor");
  }
  requireInt(value.granted_tick, label + " granted_tick", 0, MAX_SAFE_INTEGER);
  return {
    key: value.key,
    display: value.display,
    category: value.category,
    hint: hint,
    flavor: flavor,
    unlocked: unlocked,
    granted_tick: value.granted_tick,
  };
}

function validateTitleCodexEpithetRow(value, position) {
  var label = "title codex epithet row " + position;
  requireExactFields(
    value,
    label,
    ["display", "basis", "granted_tick", "equipped", "can_remove"],
    []
  );
  requireString(value.display, label + " display", TITLE_CODEX_MAX_DISPLAY);
  if (codePoints(value.display.trim()) < 1) {
    throw new Error(label + " display must be non-empty");
  }
  requireString(value.basis, label + " basis", TITLE_CODEX_MAX_BASIS);
  requireInt(value.granted_tick, label + " granted_tick", 0, MAX_SAFE_INTEGER);
  var equipped = requireBool(value.equipped, label + " equipped");
  // The server owns the gate verdict; the client renders the flag and
  // evaluates no removal rule of its own.
  var canRemove = requireBool(value.can_remove, label + " can_remove");
  return {
    display: value.display,
    basis: value.basis,
    granted_tick: value.granted_tick,
    equipped: equipped,
    can_remove: canRemove,
  };
}

function validateTitleCodexBallotEntry(value, position) {
  var label = "title codex pending ballot " + position;
  requireExactFields(value, label, ["display", "basis"], []);
  requireString(value.display, label + " display", TITLE_CODEX_MAX_DISPLAY);
  if (codePoints(value.display.trim()) < 1) {
    throw new Error(label + " display must be non-empty");
  }
  requireString(value.basis, label + " basis", TITLE_CODEX_BASIS_WIRE_MAX);
  return { display: value.display, basis: value.basis };
}

function validateTitleCodexEquipped(value) {
  requireExactFields(value, "title codex equipped", ["fixed", "epithet"], []);
  if (value.fixed !== null) {
    validateIdentifier(value.fixed, "equipped.fixed");
  }
  if (value.epithet !== null) {
    requireString(value.epithet, "equipped.epithet", TITLE_CODEX_MAX_DISPLAY);
    if (codePoints(value.epithet) < 1) {
      throw new Error("equipped.epithet must be non-empty or null");
    }
  }
  return { fixed: value.fixed, epithet: value.epithet };
}

// Exact available title_codex panel v1 schema.
function validateTitleCodexPanel(payload) {
  requireExactFields(
    payload,
    "title_codex panel",
    [
      "schema_version",
      "available",
      "kind",
      "fixed_rows",
      "epithet_rows",
      "equipped",
      "full_title",
      "unlocked",
      "total",
      "pending_ballot",
    ],
    []
  );
  requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
  if (payload.schema_version !== 1) {
    throw new Error("unsupported title_codex schema_version");
  }
  if (payload.available !== true || payload.kind !== "title_codex") {
    throw new Error(
      "title_codex panel must be available with kind title_codex"
    );
  }
  if (!Array.isArray(payload.fixed_rows)) {
    throw new Error("title codex fixed_rows must be a list");
  }
  if (payload.fixed_rows.length > TITLE_CODEX_MAX_ROWS) {
    throw new Error(
      "title codex fixed_rows must hold at most " + TITLE_CODEX_MAX_ROWS + " entries"
    );
  }
  if (!Array.isArray(payload.epithet_rows)) {
    throw new Error("title codex epithet_rows must be a list");
  }
  if (payload.epithet_rows.length > TITLE_CODEX_MAX_ROWS) {
    throw new Error(
      "title codex epithet_rows must hold at most " +
        TITLE_CODEX_MAX_ROWS +
        " entries"
    );
  }
  if (!Array.isArray(payload.pending_ballot)) {
    throw new Error("title codex pending_ballot must be a list");
  }
  if (payload.pending_ballot.length > TITLE_CODEX_MAX_BALLOT) {
    throw new Error(
      "title codex pending_ballot must hold at most " +
        TITLE_CODEX_MAX_BALLOT +
        " entries"
    );
  }
  var unlocked = requireInt(payload.unlocked, "unlocked", 0, MAX_SAFE_INTEGER);
  var total = requireInt(payload.total, "total", 0, MAX_SAFE_INTEGER);
  if (unlocked > total) {
    throw new Error("unlocked must not exceed total");
  }
  requireString(payload.full_title, "full_title", TITLE_CODEX_MAX_FULL_TITLE);
  var fixedRows = [];
  for (var f = 0; f < payload.fixed_rows.length; f++) {
    fixedRows.push(validateTitleCodexFixedRow(payload.fixed_rows[f], f + 1));
  }
  var epithetRows = [];
  for (var e = 0; e < payload.epithet_rows.length; e++) {
    epithetRows.push(
      validateTitleCodexEpithetRow(payload.epithet_rows[e], e + 1)
    );
  }
  var ballot = [];
  for (var b = 0; b < payload.pending_ballot.length; b++) {
    ballot.push(validateTitleCodexBallotEntry(payload.pending_ballot[b], b + 1));
  }
  var result = {
    schema_version: 1,
    available: true,
    kind: "title_codex",
    fixed_rows: fixedRows,
    epithet_rows: epithetRows,
    equipped: validateTitleCodexEquipped(payload.equipped),
    full_title: payload.full_title,
    unlocked: unlocked,
    total: total,
    pending_ballot: ballot,
  };
  // Envelope guarantee mirrors the Python validator's closing check.
  if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
    throw new Error("title_codex payload exceeds the OOB envelope limit");
  }
  return result;
}

// Party panel validator (mirror of web.webclient.presentation.party).
// Rows reuse the NPC wire vocabulary; the raw affinity number can never
// appear because bond_stage is a bounded non-empty string; HP fields are
// zero-clamped bounds with NO current/maximum cross assertion (traits are
// truth — the Python validator documents the same rule).

module.exports = {
  validateTitleBallotPanel: validateTitleBallotPanel,
  validateTitleCodexPanel: validateTitleCodexPanel,
};
