// suggestions envelope validator (mirror of web.webclient.presentation.options).
// Split from the combat panel module.

"use strict";

var C = require("../constants.js");
var core = require("../core.js");
var skillDescriptor = require("./skill_descriptor.js");

var validateContextActionsAffordanceParams = skillDescriptor.validateContextActionsAffordanceParams;
var isPlainObject = core.isPlainObject;
var codePoints = core.codePoints;
var requireExactFields = core.requireExactFields;
var requireString = core.requireString;
var validateIdentifier = core.validateIdentifier;

var MAX_SAFE_INTEGER = C.MAX_SAFE_INTEGER;
var CONTEXT_ACTIONS_ACTION_CODES = C.CONTEXT_ACTIONS_ACTION_CODES;
var OPTIONS_STATUSES = C.OPTIONS_STATUSES;
var OPTIONS_CARD_KINDS = C.OPTIONS_CARD_KINDS;
var MAX_OPTION_CARDS = C.MAX_OPTION_CARDS;
var MAX_OPTION_LABEL = C.MAX_OPTION_LABEL;
var MAX_OPTION_HINT = C.MAX_OPTION_HINT;
var MAX_OPTION_PARAMS = C.MAX_OPTION_PARAMS;
var OPTIONS_FREEFORM_ACTION_CODE = C.OPTIONS_FREEFORM_ACTION_CODE;
var OPTIONS_MAX_PARAM_STRING = C.OPTIONS_MAX_PARAM_STRING;


// Whether a label contains at least one CJK Unified Ideograph.
function hasCjk(text) {
  if (typeof text !== "string") {
    return false;
  }
  for (var index = 0; index < text.length; index++) {
    var code = text.charCodeAt(index);
    if (code >= 0x4e00 && code <= 0x9fff) {
      return true;
    }
  }
  return false;
}

// Validate one suggestion card's params: for a known_action card the
// canonical validator-normalized payload of its action (safe ints, bounded
// strings, plus the literal boolean true for the explore.look room-survey
// form — any other boolean rejected); for a freeform card the exact
// {"npc_id": positive int} binding.
function validateSuggestionParams(actionCode, kind, params) {
  if (!isPlainObject(params)) {
    throw new Error("suggestion params must be a JSON object");
  }
  var keys = Object.keys(params);
  if (keys.length < 1 || keys.length > MAX_OPTION_PARAMS) {
    throw new Error("suggestion params exceed their bound");
  }
  if (kind === "freeform") {
    return validateContextActionsAffordanceParams(actionCode, params);
  }
  for (var i = 0; i < keys.length; i++) {
    var child = params[keys[i]];
    if (typeof child === "boolean") {
      if (actionCode === "explore.look" && params.room === true && keys.length === 1) {
        continue;
      }
      throw new Error("suggestion params carry an unsupported boolean");
    }
    if (typeof child === "number") {
      if (!Number.isInteger(child) || child < 0 || child > MAX_SAFE_INTEGER) {
        throw new Error("suggestion params integer is out of bounds");
      }
      continue;
    }
    if (typeof child === "string") {
      if (codePoints(child) > OPTIONS_MAX_PARAM_STRING) {
        throw new Error("suggestion params string exceeds its bound");
      }
      continue;
    }
    throw new Error("suggestion params carry an unsupported value type");
  }
  return validateContextActionsAffordanceParams(actionCode, params);
}

function validateSuggestionCard(value) {
  requireExactFields(
    value,
    "suggestion card",
    ["kind", "action_code", "label", "params"],
    ["hint"]
  );
  var kind = value.kind;
  if (OPTIONS_CARD_KINDS.indexOf(kind) === -1) {
    throw new Error("suggestion card kind is not a stable value");
  }
  var actionCode = validateIdentifier(value.action_code, "action_code");
  if (CONTEXT_ACTIONS_ACTION_CODES.indexOf(actionCode) === -1) {
    throw new Error("action_code is not a registered exploration action");
  }
  if ((kind === "freeform") !== (actionCode === OPTIONS_FREEFORM_ACTION_CODE)) {
    throw new Error("freeform cards must carry exactly explore.talk_freeform");
  }
  var label = requireString(value.label, "label", MAX_OPTION_LABEL);
  var labelPoints = codePoints(label);
  if (labelPoints < 1 || labelPoints > MAX_OPTION_LABEL) {
    throw new Error("suggestion label must be 1..24 code points");
  }
  if (!hasCjk(label)) {
    throw new Error("suggestion label must contain a CJK code point");
  }
  var params = validateSuggestionParams(actionCode, kind, value.params);
  var hint = null;
  if (
    Object.prototype.hasOwnProperty.call(value, "hint") &&
    value.hint !== null
  ) {
    hint = requireString(value.hint, "hint", MAX_OPTION_HINT);
  }
  return {
    kind: kind,
    action_code: actionCode,
    label: label,
    params: params,
    hint: hint,
  };
}

// Validate one exact suggestions envelope: status decides the exact key set
// (status alone for generating/unavailable; status + cards for
// ready/degraded); ready sets number 3..5, degraded sets 0..5.
function validateSuggestions(value) {
  if (!isPlainObject(value)) {
    throw new Error("suggestions must be a JSON object");
  }
  var status = value.status;
  if (OPTIONS_STATUSES.indexOf(status) === -1) {
    throw new Error("suggestions status is not a stable value");
  }
  if (status === "generating" || status === "unavailable") {
    var statusKeys = Object.keys(value);
    if (statusKeys.length !== 1 || statusKeys[0] !== "status") {
      throw new Error("generating/unavailable suggestions carry only status");
    }
    return { status: status };
  }
  var keys = Object.keys(value);
  if (keys.length !== 2 || keys.indexOf("status") === -1 || keys.indexOf("cards") === -1) {
    throw new Error("ready/degraded suggestions carry exactly status and cards");
  }
  if (!Array.isArray(value.cards)) {
    throw new Error("suggestions cards must be an array");
  }
  var minimum = status === "ready" ? 3 : 0;
  if (value.cards.length < minimum || value.cards.length > MAX_OPTION_CARDS) {
    throw new Error(
      "suggestions cards must number " + minimum + ".." + MAX_OPTION_CARDS
    );
  }
  var cards = value.cards.map(validateSuggestionCard);
  return { status: status, cards: cards };
}

module.exports = {
  validateSuggestions: validateSuggestions,
  validateSuggestionCard: validateSuggestionCard,
};
