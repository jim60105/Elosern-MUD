// combat_beats panel validator (mirror of
// web.webclient.presentation.combat_beats and world.rules.combat_beats,
// combat-beats-panel). One settled round's structured beats: the exact
// available form, the closed kind set, contiguous seq, non-decreasing action,
// the damage invariants, the opaque decimal catalog-key identity shape, and
// the panel's own canonical-JSON byte budget. The common unavailable form is
// handled by the shared panel dispatch, never here.

"use strict";

var C = require("../constants.js");
var core = require("../core.js");

var jsonByteSize = core.jsonByteSize;
var requireExactFields = core.requireExactFields;
var requireInt = core.requireInt;
var requireString = core.requireString;
var hasLoneSurrogate = core.hasLoneSurrogate;

var MAX_SAFE_INTEGER = C.MAX_SAFE_INTEGER;
var COMBAT_BEATS_SCHEMA_VERSION = C.COMBAT_BEATS_SCHEMA_VERSION;
var COMBAT_BEATS_MAX_BEATS = C.COMBAT_BEATS_MAX_BEATS;
var COMBAT_BEATS_MAX_TEXT = C.COMBAT_BEATS_MAX_TEXT;
var COMBAT_BEATS_MAX_ROUND = C.COMBAT_BEATS_MAX_ROUND;
var COMBAT_BEATS_MAX_BYTES = C.COMBAT_BEATS_MAX_BYTES;
var COMBAT_BEATS_MAX_REF = C.COMBAT_BEATS_MAX_REF;
var COMBAT_BEATS_KINDS = C.COMBAT_BEATS_KINDS;

// The opaque catalog key: ASCII decimal digits only, exactly the server's
// ``isascii() and isdecimal()`` pair.
var IDENTITY_RE = /^[0-9]+$/;

function validateCombatBeatsIdentity(value, field) {
  if (value === null) {
    return null;
  }
  if (
    typeof value !== "string" ||
    value.length > COMBAT_BEATS_MAX_REF ||
    !IDENTITY_RE.test(value)
  ) {
    throw new Error(
      field +
        " must be an opaque decimal catalog key of at most " +
        COMBAT_BEATS_MAX_REF +
        " characters, or null"
    );
  }
  return value;
}

function validateCombatBeatsBeat(value, seq, previousAction) {
  var name = "combat_beats beat " + seq;
  requireExactFields(
    value,
    name,
    ["seq", "action", "kind", "actor", "target", "amount", "hp_after", "text"],
    []
  );
  var position = requireInt(value.seq, "seq", 0, MAX_SAFE_INTEGER);
  if (position !== seq) {
    throw new Error("combat_beats seq must be contiguous from 0");
  }
  var action = requireInt(value.action, "action", 0, MAX_SAFE_INTEGER);
  if (action < previousAction) {
    throw new Error("combat_beats action must not decrease");
  }
  if (COMBAT_BEATS_KINDS.indexOf(value.kind) === -1) {
    throw new Error("combat_beats kind is not a stable value");
  }
  var actor = validateCombatBeatsIdentity(value.actor, name + " actor");
  var target = validateCombatBeatsIdentity(value.target, name + " target");
  var text = requireString(value.text, "text", COMBAT_BEATS_MAX_TEXT);
  if (hasLoneSurrogate(text)) {
    throw new Error(name + " text must be valid text");
  }
  var amount = null;
  var hpAfter = null;
  if (value.kind === "damage") {
    if (target === null) {
      throw new Error("a damage beat requires a target");
    }
    amount = requireInt(value.amount, "amount", 0, MAX_SAFE_INTEGER);
    hpAfter = requireInt(value.hp_after, "hp_after", 0, MAX_SAFE_INTEGER);
  } else {
    if (value.amount !== null) {
      throw new Error("a non-damage beat carries no amount");
    }
    if (value.hp_after !== null) {
      throw new Error("a non-damage beat carries no hp_after");
    }
  }
  return {
    seq: position,
    action: action,
    kind: value.kind,
    actor: actor,
    target: target,
    amount: amount,
    hp_after: hpAfter,
    text: text,
  };
}

function validateCombatBeatsPanel(payload) {
  requireExactFields(
    payload,
    "combat_beats panel",
    ["schema_version", "available", "round", "beats"],
    []
  );
  requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
  if (payload.schema_version !== COMBAT_BEATS_SCHEMA_VERSION) {
    throw new Error("unsupported combat_beats schema_version");
  }
  if (payload.available !== true) {
    throw new Error("combat_beats panel must be available");
  }
  var roundId = requireString(payload.round, "round", COMBAT_BEATS_MAX_ROUND);
  if (!roundId.trim()) {
    throw new Error("combat_beats round must be non-empty");
  }
  if (!Array.isArray(payload.beats)) {
    throw new Error("combat_beats beats must be a list");
  }
  if (payload.beats.length > COMBAT_BEATS_MAX_BEATS) {
    throw new Error(
      "combat_beats beats must hold at most " + COMBAT_BEATS_MAX_BEATS + " entries"
    );
  }
  var beats = [];
  var previousAction = 0;
  for (var index = 0; index < payload.beats.length; index++) {
    var beat = validateCombatBeatsBeat(
      payload.beats[index],
      index,
      previousAction
    );
    previousAction = beat.action;
    beats.push(beat);
  }
  var result = {
    schema_version: COMBAT_BEATS_SCHEMA_VERSION,
    available: true,
    round: roundId,
    beats: beats,
  };
  if (jsonByteSize(result) > COMBAT_BEATS_MAX_BYTES) {
    throw new Error("combat_beats payload exceeds its byte budget");
  }
  return result;
}


module.exports = {
  validateCombatBeatsPanel: validateCombatBeatsPanel,
};
