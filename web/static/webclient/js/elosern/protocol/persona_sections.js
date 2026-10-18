// Shared persona-prose and intimate-state validators (mirror of
// web/webclient/presentation/persona_sections.py). The character panel and the
// party_member panel publish the same display-only sections, so the exact
// shape rules live here once.

"use strict";

var C = require("./constants.js");
var core = require("./core.js");

var requireExactFields = core.requireExactFields;
var requireInt = core.requireInt;
var requireString = core.requireString;

var MAX_SAFE_INTEGER = C.MAX_SAFE_INTEGER;

// The four editable persona prose keys in drawer display order.
var MAX_PERSONA_FIELD = 600;
var PERSONA_FIELDS = ["background", "personality", "life_story", "habit"];

// Fixed level vocabularies (mirror of world/lore/sexual_vocab.py).
var MAX_INTIMATE_LEVEL = 128;
var INTIMATE_AROUSAL_LEVELS = ["平靜", "微興奮", "中等", "高度", "極限"];
var INTIMATE_WETNESS_LEVELS = ["乾燥", "微濕", "濕潤", "大量", "泛濫"];
var INTIMATE_SHAME_LEVELS = ["無", "輕微", "中等", "強烈", "成癮"];
var INTIMATE_EXPOSURE_LEVELS = ["極低", "低", "中等", "高", "極高"];
var INTIMATE_CLIMAX_PHASE_LEVELS = ["未達", "接近", "進行中", "餘韻"];

function validatePersona(value) {
  // Each prose key is independently nullable, whitespace-nulling, and bounded
  // at the shared 600-code-point cap. Structural keys never appear.
  requireExactFields(value, "persona", PERSONA_FIELDS, []);
  var result = {};
  for (var i = 0; i < PERSONA_FIELDS.length; i++) {
    var field = PERSONA_FIELDS[i];
    if (value[field] === null) {
      result[field] = null;
      continue;
    }
    var text = requireString(value[field], "persona." + field, MAX_PERSONA_FIELD);
    result[field] = text.trim() ? text.trim() : null;
  }
  return result;
}

function validateIntimateLevel(value, field, vocabulary) {
  var level = requireString(value, field, MAX_INTIMATE_LEVEL);
  if (vocabulary.indexOf(level) === -1) {
    throw new Error(field + " is not a member of its fixed vocabulary");
  }
  return level;
}

function validateIntimate(value) {
  if (value === null) {
    return null;
  }
  requireExactFields(
    value,
    "intimate",
    ["arousal", "wetness", "shame", "exposure", "climax_phase", "climax_today"],
    []
  );
  return {
    arousal: validateIntimateLevel(value.arousal, "intimate.arousal", INTIMATE_AROUSAL_LEVELS),
    wetness: validateIntimateLevel(value.wetness, "intimate.wetness", INTIMATE_WETNESS_LEVELS),
    shame: validateIntimateLevel(value.shame, "intimate.shame", INTIMATE_SHAME_LEVELS),
    exposure: validateIntimateLevel(value.exposure, "intimate.exposure", INTIMATE_EXPOSURE_LEVELS),
    climax_phase: validateIntimateLevel(
      value.climax_phase,
      "intimate.climax_phase",
      INTIMATE_CLIMAX_PHASE_LEVELS
    ),
    climax_today: requireInt(value.climax_today, "intimate.climax_today", 0, MAX_SAFE_INTEGER),
  };
}

module.exports = {
  MAX_PERSONA_FIELD: MAX_PERSONA_FIELD,
  PERSONA_FIELDS: PERSONA_FIELDS,
  validatePersona: validatePersona,
  validateIntimate: validateIntimate,
};
