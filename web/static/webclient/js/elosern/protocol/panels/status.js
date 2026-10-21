// Status v4 presenter wire contract, including read-model provenance and the
// physiological fatigue subject rows.
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
var STATUS_FATIGUE_MAX_SUBJECTS = C.STATUS_FATIGUE_MAX_SUBJECTS;
var STATUS_FATIGUE_MAX_RESTRICTION = C.STATUS_FATIGUE_MAX_RESTRICTION;
var STATUS_FATIGUE_STAGES = C.STATUS_FATIGUE_STAGES;
var COMBAT_MODES = C.COMBAT_MODES;
var SEVERITIES = C.SEVERITIES;


function validateProvenance(value) {
  requireExactFields(value, "condition.provenance", ["kind", "equipment_sources"], []);
  if (["equipment", "non_equipment", "mixed", "unknown"].indexOf(value.kind) === -1) {
    throw new Error("condition.provenance.kind is invalid");
  }
  var sources = value.equipment_sources;
  if (!Array.isArray(sources) || sources.length > 8) {
    throw new Error("condition.provenance.equipment_sources exceeds its bound");
  }
  if ((sources.length > 0) !== (value.kind === "equipment" || value.kind === "mixed")) {
    throw new Error("condition.provenance sources disagree with kind");
  }
  var previous = "";
  sources.forEach(function (source) {
    requireExactFields(source, "equipment source", ["item_key", "label"], []);
    validateIdentifier(source.item_key, "equipment source.item_key");
    requireString(source.label, "equipment source.label", 128);
    if (source.label.length === 0) {
      throw new Error("equipment source.label must be nonempty");
    }
    if (source.item_key <= previous) {
      throw new Error("equipment sources must be unique and item-key sorted");
    }
    previous = source.item_key;
  });
}

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
  requireExactFields(value, "condition", ["code", "label", "severity", "provenance"], conditional);
  validateIdentifier(value.code, "condition.code");
  requireString(value.label, "condition.label", MAX_CONDITION_LABEL);
  if (SEVERITIES.indexOf(value.severity) === -1) {
    throw new Error("condition.severity is not a stable severity");
  }
  validateProvenance(value.provenance);
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

// One physiological subject row: the member's own identity, display-rounded
// reserve percent, the exact-units stage, and the fixed restriction line.
function validateFatigueSubject(value) {
  requireExactFields(
    value,
    "fatigue subject",
    ["identity", "name", "reserve_percent", "stage", "label", "severity", "restriction"],
    []
  );
  requireString(value.identity, "fatigue subject.identity", MAX_ACTOR_IDENTITY);
  if (value.identity.length === 0) {
    throw new Error("fatigue subject.identity must be nonempty");
  }
  requireString(value.name, "fatigue subject.name", MAX_ACTOR_NAME);
  if (value.name.length === 0) {
    throw new Error("fatigue subject.name must be nonempty");
  }
  requireInt(value.reserve_percent, "fatigue subject.reserve_percent", 0, 100);
  requireString(value.stage, "fatigue subject.stage", 32);
  if (STATUS_FATIGUE_STAGES.indexOf(value.stage) === -1) {
    throw new Error("fatigue subject.stage is not a stable stage");
  }
  requireString(value.label, "fatigue subject.label", MAX_CONDITION_LABEL);
  if (!value.label.trim()) {
    throw new Error("fatigue subject.label must be nonempty");
  }
  if (SEVERITIES.indexOf(value.severity) === -1) {
    throw new Error("fatigue subject.severity is not a stable severity");
  }
  var sleepingStage =
    value.stage === "forced_sleep" || value.stage === "sleeping";
  if (sleepingStage !== (value.restriction !== null)) {
    throw new Error("fatigue subject.restriction disagrees with its stage");
  }
  if (value.restriction !== null) {
    requireString(
      value.restriction,
      "fatigue subject.restriction",
      STATUS_FATIGUE_MAX_RESTRICTION
    );
    if (!value.restriction.trim()) {
      throw new Error("fatigue subject.restriction must be nonempty");
    }
  }
  return value;
}

// Exact available status panel v4 schema (composed full title optional).
function validateStatusPanel(payload) {
  requireExactFields(
    payload,
    "status panel",
    [
      "schema_version",
      "available",
      "actor",
      "resources",
      "conditions",
      "fatigue",
      "disguise_active",
      "combat",
    ],
    []
  );
  requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
  if (payload.schema_version !== 4) {
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
    requireInt(gauge.maximum, "resource " + key + ".maximum", 0, MAX_SAFE_INTEGER);
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

  var fatigue = payload.fatigue;
  if (!Array.isArray(fatigue) || fatigue.length < 1) {
    throw new Error("fatigue must name at least the status source's body");
  }
  if (fatigue.length > STATUS_FATIGUE_MAX_SUBJECTS) {
    throw new Error(
      "fatigue exceeds the maximum of " + STATUS_FATIGUE_MAX_SUBJECTS + " subjects"
    );
  }
  var seenIdentities = {};
  for (var fatigueIndex = 0; fatigueIndex < fatigue.length; fatigueIndex++) {
    validateFatigueSubject(fatigue[fatigueIndex]);
    var identity = fatigue[fatigueIndex].identity;
    if (Object.prototype.hasOwnProperty.call(seenIdentities, identity)) {
      throw new Error("fatigue subjects must identify distinct bodies");
    }
    seenIdentities[identity] = true;
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
