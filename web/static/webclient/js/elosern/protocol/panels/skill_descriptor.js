"use strict";

// Shared skill-descriptor primitives used by the combat (context_actions)
// and character panel validators. Split from protocol.js; extracted from the
// combat panel section to keep the combat <-> character modules acyclic.

var C = require("../constants.js");
var core = require("../core.js");

var requireExactFields = core.requireExactFields;
var requireInt = core.requireInt;
var requireString = core.requireString;
var MAX_SAFE_INTEGER = C.MAX_SAFE_INTEGER;
var FREEFORM_SCALES_ALLOWED = C.FREEFORM_SCALES_ALLOWED;
var FREEFORM_SCALES_MAX = C.FREEFORM_SCALES_MAX;
var FREEFORM_LABELS_ALLOWED = C.FREEFORM_LABELS_ALLOWED;

function validateFreeformScales(value, baseMp) {
  if (value === null || value === undefined) {
    return [];
  }
  if (
    baseMp === null ||
    baseMp === undefined ||
    typeof baseMp !== "number" ||
    !Number.isInteger(baseMp) ||
    baseMp <= 0
  ) {
    throw new Error("a skill without an mp cost cannot carry freeform_scales");
  }
  if (!Array.isArray(value) || value.length === 0) {
    throw new Error("freeform_scales must be a non-empty array when present");
  }
  if (value.length > FREEFORM_SCALES_MAX) {
    throw new Error("freeform_scales may not exceed the canonical scale table");
  }
  value.forEach(function (entry, index) {
    requireExactFields(entry, "freeform_scales entry", ["scale", "label", "mp_cost"], []);
    var scale = entry.scale;
    if (scale !== FREEFORM_SCALES_ALLOWED[index]) {
      throw new Error("freeform_scales must be ascending over the allowed scale set");
    }
    var label = requireString(entry.label, "freeform_scales label", 8);
    if (label !== FREEFORM_LABELS_ALLOWED[index]) {
      throw new Error("freeform_scales label must be the canonical label of its scale");
    }
    var mpCost = requireInt(entry.mp_cost, "freeform_scales mp_cost", 1, MAX_SAFE_INTEGER);
    if (mpCost !== Math.max(1, Math.floor(baseMp * scale + 0.5))) {
      throw new Error("freeform_scales mp_cost is inconsistent with the scaled base cost");
    }
  });
  return value;
}


function requireNumber(value, field, minimum, maximum) {
  // JSON numbers with the wire bounds: finite, safe-ranged, non-boolean.
  if (typeof value !== "number" || !isFinite(value)) {
    throw new Error(field + " must be a finite number");
  }
  if (value < minimum || value > maximum || Math.abs(value) > MAX_SAFE_INTEGER) {
    throw new Error(field + " must be within " + minimum + ".." + maximum);
  }
  return value;
}

var isPlainObject = core.isPlainObject;
var CONTEXT_ACTIONS_MAX_PARAM_KEYS = C.CONTEXT_ACTIONS_MAX_PARAM_KEYS;
var CONTEXT_ACTIONS_MAX_PARAM_STRING = C.CONTEXT_ACTIONS_MAX_PARAM_STRING;
var CONTEXT_ACTIONS_MAX_EXIT_REF = C.CONTEXT_ACTIONS_MAX_EXIT_REF;
var CONTEXT_ACTIONS_MAX_NODE_ID = C.CONTEXT_ACTIONS_MAX_NODE_ID;
var CONTEXT_ACTIONS_MAX_KEYWORD_ID = C.CONTEXT_ACTIONS_MAX_KEYWORD_ID;
var CONTEXT_ACTIONS_MAX_ITEM_KEY = C.CONTEXT_ACTIONS_MAX_ITEM_KEY;
var CONTEXT_ACTIONS_MAX_WEB_SKIP_SECONDS = C.CONTEXT_ACTIONS_MAX_WEB_SKIP_SECONDS;
// Shared action-parameter gate used by the context_actions affordance rows and
// the suggestion cards (one mirror of the Python affordance table).
function validateContextActionsAffordanceParams(actionId, params) {
  if (!isPlainObject(params)) {
    throw new Error("affordance params must be a JSON object");
  }
  if (Object.keys(params).length > CONTEXT_ACTIONS_MAX_PARAM_KEYS) {
    throw new Error("affordance params exceed their bound");
  }
  Object.keys(params).forEach(function (key) {
    var child = params[key];
    if (typeof child === "string" && codePoints(child) > CONTEXT_ACTIONS_MAX_PARAM_STRING) {
      throw new Error("affordance params string exceeds its bound");
    }
  });
  if (actionId === "explore.move") {
    requireExactFields(params, "move params", ["exit_ref", "current_node"], []);
    if (
      typeof params.exit_ref !== "string" ||
      params.exit_ref.length < 1 ||
      params.exit_ref.length > CONTEXT_ACTIONS_MAX_EXIT_REF
    ) {
      throw new Error("exit_ref must be 1.." + CONTEXT_ACTIONS_MAX_EXIT_REF + " ASCII characters");
    }
    if (/[^\x00-\x7F]/.test(params.exit_ref)) {
      throw new Error("exit_ref must be ASCII");
    }
    requireString(params.current_node, "current_node", CONTEXT_ACTIONS_MAX_NODE_ID);
    if (!NODE_ID_RE.test(params.current_node)) {
      throw new Error("current_node is not a canonical node ID");
    }
    return params;
  }
  if (actionId === "explore.look") {
    if (Object.keys(params).length === 1 && params.room !== undefined) {
      if (params.room !== true) {
        throw new Error("explore.look room must be the exact boolean true");
      }
      return params;
    }
    requireExactFields(params, "look params", ["target_id"], []);
    requireInt(params.target_id, "target_id", 1, MAX_SAFE_INTEGER);
    return params;
  }
  if (actionId === "explore.talk_scripted") {
    requireExactFields(params, "talk_scripted params", ["npc_id", "keyword_id"], []);
    requireInt(params.npc_id, "npc_id", 1, MAX_SAFE_INTEGER);
    var keywordId = requireString(params.keyword_id, "keyword_id", CONTEXT_ACTIONS_MAX_KEYWORD_ID);
    if (!keywordId.trim()) {
      throw new Error("keyword_id must be non-empty");
    }
    return params;
  }
  if (actionId === "explore.talk_freeform") {
    // Binding-only shape: no validator produces npc_id without speech.
    requireExactFields(params, "freeform params", ["npc_id"], []);
    requireInt(params.npc_id, "npc_id", 1, MAX_SAFE_INTEGER);
    return params;
  }
  if (actionId === "explore.party_invite") {
    requireExactFields(params, "party_invite params", ["npc_id", "message"], []);
    requireInt(params.npc_id, "npc_id", 1, MAX_SAFE_INTEGER);
    requireString(params.message, "message", MAX_MESSAGE_CODE_POINTS);
    return params;
  }
  if (actionId === "explore.party_leave") {
    requireExactFields(params, "party_leave params", ["npc_id"], []);
    requireInt(params.npc_id, "npc_id", 1, MAX_SAFE_INTEGER);
    return params;
  }
  if (actionId === "explore.engage") {
    requireExactFields(params, "engage params", ["monster_id"], []);
    requireInt(params.monster_id, "monster_id", 1, MAX_SAFE_INTEGER);
    return params;
  }
  if (actionId === "explore.possess" || actionId === "explore.possess_release") {
    requireExactFields(params, actionId + " params", ["npc_id"], []);
    requireInt(params.npc_id, "npc_id", 1, MAX_SAFE_INTEGER);
    return params;
  }
  if (actionId === "explore.deliver") {
    requireExactFields(params, "deliver params", ["npc_id", "item_key"], []);
    requireInt(params.npc_id, "npc_id", 1, MAX_SAFE_INTEGER);
    if (
      typeof params.item_key !== "string" ||
      params.item_key.length < 1 ||
      params.item_key.length > CONTEXT_ACTIONS_MAX_ITEM_KEY
    ) {
      throw new Error(
        "item_key must be 1.." + CONTEXT_ACTIONS_MAX_ITEM_KEY + " characters"
      );
    }
    if (!/^[\x00-\x7F]*$/.test(params.item_key)) {
      throw new Error("item_key must be ASCII");
    }
    return params;
  }
  if (actionId === "explore.wait") {
    if (Object.keys(params).length === 1 && params.daypart !== undefined) {
      if (CONTEXT_ACTIONS_DAYPARTS.indexOf(params.daypart) === -1) {
        throw new Error("explore.wait daypart is not a stable value");
      }
      return params;
    }
    if (Object.keys(params).length === 1 && params.seconds !== undefined) {
      requireInt(params.seconds, "seconds", 1, CONTEXT_ACTIONS_MAX_WEB_SKIP_SECONDS);
      return params;
    }
    if (Object.keys(params).length === 1 && params.sleep !== undefined) {
      if (params.sleep !== true) {
        throw new Error("explore.wait sleep must be the exact boolean true");
      }
      return params;
    }
    throw new Error("explore.wait requires exactly one of daypart, seconds, or sleep");
  }
  throw new Error("affordance params carry an unregistered action code");
}

var codePoints = core.codePoints;
var MAX_MESSAGE_CODE_POINTS = C.MAX_MESSAGE_CODE_POINTS;
var CONTEXT_ACTIONS_DAYPARTS = C.CONTEXT_ACTIONS_DAYPARTS;
var NODE_ID_RE = C.NODE_ID_RE;

module.exports = {
  validateContextActionsAffordanceParams: validateContextActionsAffordanceParams,
  validateFreeformScales: validateFreeformScales,
  requireNumber: requireNumber,
};
