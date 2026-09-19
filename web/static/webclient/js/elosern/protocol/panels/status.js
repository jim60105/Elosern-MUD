// status panel validator (mirror of web.webclient.presentation.status_panel).
// Split from the combat panel module.

"use strict";

var C = require("../constants.js");
var core = require("../core.js");

var isPlainObject = core.isPlainObject;
var checkGlobalSafety = core.checkGlobalSafety;
var requireExactFields = core.requireExactFields;
var requireInt = core.requireInt;
var requireBool = core.requireBool;
var requireString = core.requireString;
var validateIdentifier = core.validateIdentifier;

var MAX_SAFE_INTEGER = C.MAX_SAFE_INTEGER;
var MAX_ACTOR_NAME = C.MAX_ACTOR_NAME;
var MAX_ACTOR_IDENTITY = C.MAX_ACTOR_IDENTITY;
var MAX_FULL_TITLE_CODE_POINTS = C.MAX_FULL_TITLE_CODE_POINTS;
var MAX_LOCATION_LABEL = C.MAX_LOCATION_LABEL;
var MAX_CONDITION_COUNT = C.MAX_CONDITION_COUNT;
var MAX_CONDITION_LABEL = C.MAX_CONDITION_LABEL;
var MAX_MODIFIER_KEYS = C.MAX_MODIFIER_KEYS;
var COMBAT_MODES = C.COMBAT_MODES;
var SEVERITIES = C.SEVERITIES;


function validateStatusCondition(value) {
  if (!isPlainObject(value)) {
    throw new Error("conditions entries must be JSON objects");
  }
  var hasRemaining = Object.prototype.hasOwnProperty.call(value, "remaining_seconds");
  var hasModifiers = Object.prototype.hasOwnProperty.call(value, "modifiers");
  var conditional = [];
  if (hasRemaining) {
    conditional.push("remaining_seconds");
  }
  if (hasModifiers) {
    conditional.push("modifiers");
  }
  requireExactFields(value, "condition", ["code", "label", "severity"], conditional);
  validateIdentifier(value.code, "condition.code");
  requireString(value.label, "condition.label", MAX_CONDITION_LABEL);
  if (SEVERITIES.indexOf(value.severity) === -1) {
    throw new Error("condition.severity is not a stable severity");
  }
  if (hasRemaining) {
    requireInt(value.remaining_seconds, "condition.remaining_seconds", 0, MAX_SAFE_INTEGER);
  }
  if (hasModifiers) {
    checkGlobalSafety(value.modifiers);
    var modifierKeys = Object.keys(value.modifiers);
    if (modifierKeys.length > MAX_MODIFIER_KEYS) {
      throw new Error(
        "condition.modifiers exceeds the maximum of " + MAX_MODIFIER_KEYS + " keys"
      );
    }
  }
  return value;
}

// Exact available status panel v2 schema (composed full title optional).
function validateStatusPanel(payload) {
  requireExactFields(
    payload,
    "status panel",
    ["schema_version", "available", "actor", "resources", "conditions", "disguise_active", "combat"],
    []
  );
  requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
  if (payload.schema_version !== 2) {
    throw new Error("unsupported status panel schema_version");
  }

  var actor = payload.actor;
  requireExactFields(actor, "actor", ["name", "identity", "location"], ["full_title"]);
  requireString(actor.name, "actor.name", MAX_ACTOR_NAME);
  requireString(actor.identity, "actor.identity", MAX_ACTOR_IDENTITY);
  if (Object.prototype.hasOwnProperty.call(actor, "full_title")) {
    requireString(
      actor.full_title,
      "actor.full_title",
      MAX_FULL_TITLE_CODE_POINTS
    );
    if (!actor.full_title.trim()) {
      throw new Error("actor.full_title must be non-empty when present");
    }
  }
  if (actor.location !== null) {
    requireExactFields(actor.location, "actor.location", ["label", "identity"], []);
    requireString(actor.location.label, "actor.location.label", MAX_LOCATION_LABEL);
    requireString(actor.location.identity, "actor.location.identity", MAX_ACTOR_IDENTITY);
  }

  var resources = payload.resources;
  if (!isPlainObject(resources)) {
    throw new Error("resources must be a JSON object");
  }
  var resourceKeys = Object.keys(resources);
  if (resourceKeys.length !== 3) {
    throw new Error("resources must contain exactly hp, mp, and sp");
  }
  ["hp", "mp", "sp"].forEach(function (key) {
    var gauge = resources[key];
    requireExactFields(gauge, "resource " + key, ["current", "maximum"], []);
    requireInt(gauge.current, "resource " + key + ".current", 0, MAX_SAFE_INTEGER);
    requireInt(gauge.maximum, "resource " + key + ".maximum", 1, MAX_SAFE_INTEGER);
    if (gauge.current > gauge.maximum) {
      throw new Error(
        "resource " + key + ".current must not exceed its maximum"
      );
    }
  });

  var conditions = payload.conditions;
  if (!Array.isArray(conditions)) {
    throw new Error("conditions must be an array");
  }
  if (conditions.length > MAX_CONDITION_COUNT) {
    throw new Error(
      "conditions exceeds the maximum of " + MAX_CONDITION_COUNT + " entries"
    );
  }
  for (var index = 0; index < conditions.length; index++) {
    validateStatusCondition(conditions[index]);
  }

  requireBool(payload.disguise_active, "disguise_active");
  if (payload.combat !== null) {
    requireExactFields(payload.combat, "combat", ["mode", "round"], []);
    if (COMBAT_MODES.indexOf(payload.combat.mode) === -1) {
      throw new Error("combat.mode must be hostile or guild_exam");
    }
    requireInt(payload.combat.round, "combat.round", 0, MAX_SAFE_INTEGER);
  }

  return payload;
}

module.exports = {
  validateStatusPanel: validateStatusPanel,
};
