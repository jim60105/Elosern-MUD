"use strict";

var C = require("../constants.js");
var core = require("../core.js");

var isPlainObject = core.isPlainObject;
var jsonByteSize = core.jsonByteSize;
var requireExactFields = core.requireExactFields;
var requireInt = core.requireInt;
var requireBool = core.requireBool;
var requireString = core.requireString;
var validateIdentifier = core.validateIdentifier;
var requireNodeId = core.requireNodeId;
var requireExitRef = core.requireExitRef;

var MAX_SAFE_INTEGER = C.MAX_SAFE_INTEGER;
var MAX_CANONICAL_JSON_BYTES = C.MAX_CANONICAL_JSON_BYTES;

// ---------------------------------------------------------------------------
// exploration panel v1 validators (mirror of
// web.webclient.presentation.exploration, design D10). Shared bounds are
// guarded by a dual-direction parity test.
// ---------------------------------------------------------------------------

var EXPLORATION_MAX_MOVE_EXITS = 12;
var EXPLORATION_MAX_LOOK_ENTITIES = 32;
var EXPLORATION_MAX_LOOK_OBJECTS = 32;
var EXPLORATION_MAX_INTERACT_TARGETS = 32;
var EXPLORATION_MAX_AFFORDANCES = 8;
var EXPLORATION_MAX_SCRIPTED_KEYWORDS = 16;
var EXPLORATION_MAX_EXIT_REF = 64;
var EXPLORATION_MAX_NODE_ID = 128;
var EXPLORATION_MAX_DISPLAY_NAME = 128;
var EXPLORATION_MAX_KIND = 32;
var EXPLORATION_MAX_LABEL = 128;
var EXPLORATION_MAX_KEYWORD_ID = 64;
var EXPLORATION_MAX_KEYWORD_LABEL = 128;
var EXPLORATION_MAX_ITEM_KEY = 64;
var EXPLORATION_MAX_REASON_MESSAGE = 128;
var EXPLORATION_ACTION_KINDS = ["action", "navigate"];
var EXPLORATION_ACTION_IDS = [
  "explore.talk_scripted",
  "explore.talk_freeform",
  "explore.party_invite",
  "explore.party_leave",
  "explore.engage",
  "explore.possess",
  "explore.possess_release",
  "explore.deliver",
];
var EXPLORATION_SURFACES = ["guild", "shop"];
var EXPLORATION_ENTITY_KINDS = ["character", "npc", "monster"];



function requireIdentity(value, field) {
  return requireInt(value, field, 1, MAX_SAFE_INTEGER);
}

function validateExplorationDisabledReason(value) {
  if (value === null) {
    return null;
  }
  requireExactFields(value, "disabled_reason", ["code", "message"], []);
  validateIdentifier(value.code, "disabled_reason code");
  var reasonMessage = requireString(
    value.message,
    "disabled_reason message",
    EXPLORATION_MAX_REASON_MESSAGE
  );
  if (!reasonMessage.trim()) {
    throw new Error("disabled_reason message must be non-empty");
  }
  return value;
}

function validateExplorationKeyword(value) {
  requireExactFields(value, "scripted keyword", ["keyword_id", "label"], []);
  var keywordId = requireString(value.keyword_id, "keyword_id", EXPLORATION_MAX_KEYWORD_ID);
  if (!keywordId.trim()) {
    throw new Error("keyword_id must be non-empty");
  }
  var keywordLabel = requireString(value.label, "keyword label", EXPLORATION_MAX_KEYWORD_LABEL);
  if (!keywordLabel.trim()) {
    throw new Error("keyword label must be non-empty");
  }
  return value;
}

function validateExplorationAffordance(value) {
  if (!isPlainObject(value)) {
    throw new Error("affordance must be a JSON object");
  }
  var kind = value.kind;
  if (EXPLORATION_ACTION_KINDS.indexOf(kind) === -1) {
    throw new Error("affordance kind is not a stable value");
  }
  requireExactFields(
    value,
    "affordance",
    ["kind", "label", "enabled", "disabled_reason"],
    // `params` is the schema-version-2 delivery payload; the kind branches
    // below enforce exactly which affordance may carry it.
    ["action_id", "surface", "params"]
  );
  var label = requireString(value.label, "label", EXPLORATION_MAX_LABEL);
  if (!label.trim()) {
    throw new Error("affordance label must be non-empty");
  }
  var enabled = requireBool(value.enabled, "enabled");
  var disabledReason = validateExplorationDisabledReason(value.disabled_reason);
  if (disabledReason === null) {
    if (!enabled) {
      throw new Error("a disabled affordance requires a disabled_reason");
    }
  } else if (enabled) {
    throw new Error("an enabled affordance must not carry a disabled_reason");
  }

  if (kind === "action") {
    requireExactFields(
      value,
      "action affordance",
      ["kind", "action_id", "label", "enabled", "disabled_reason"],
      // Schema version 2 (quest-deliver-action): exactly the
      // explore.deliver affordance carries the server validator's
      // normalized dispatch payload; every other action keeps the
      // version-1 exact shape.
      ["params"]
    );
    var actionId = validateIdentifier(value.action_id, "action_id");
    if (EXPLORATION_ACTION_IDS.indexOf(actionId) === -1) {
      throw new Error("action_id is not a registered exploration action");
    }
    if (actionId !== "explore.deliver" && value.params !== undefined) {
      throw new Error("action affordance must not contain params");
    }
    var normalized = {
      kind: kind,
      action_id: actionId,
      label: label,
      enabled: enabled,
      disabled_reason: disabledReason,
    };
    if (actionId === "explore.deliver") {
      var deliverParams = value.params;
      if (!isPlainObject(deliverParams)) {
        throw new Error("explore.deliver params must be a JSON object");
      }
      requireExactFields(deliverParams, "deliver params", ["npc_id", "item_key"], []);
      requireInt(deliverParams.npc_id, "npc_id", 1, MAX_SAFE_INTEGER);
      if (
        typeof deliverParams.item_key !== "string" ||
        deliverParams.item_key.length < 1 ||
        deliverParams.item_key.length > EXPLORATION_MAX_ITEM_KEY
      ) {
        throw new Error(
          "item_key must be 1.." + EXPLORATION_MAX_ITEM_KEY + " characters"
        );
      }
      if (!/^[\x00-\x7F]*$/.test(deliverParams.item_key)) {
        throw new Error("item_key must be ASCII");
      }
      normalized.params = deliverParams;
    }
    return normalized;
  }
  if (kind === "navigate") {
    requireExactFields(
      value,
      "navigation affordance",
      ["kind", "surface", "label", "enabled", "disabled_reason"],
      []
    );
    if (EXPLORATION_SURFACES.indexOf(value.surface) === -1) {
      throw new Error("surface is not a stable value");
    }
    return {
      kind: kind,
      surface: value.surface,
      label: label,
      enabled: enabled,
      disabled_reason: disabledReason,
    };
  }
  throw new Error("affordance kind is not a stable value");
}

function validateExplorationLookEntity(value) {
  requireExactFields(
    value,
    "look entity",
    ["identity", "display_name", "kind", "portrait_ref"],
    []
  );
  requireIdentity(value.identity, "entity.identity");
  var displayName = requireString(value.display_name, "display_name", EXPLORATION_MAX_DISPLAY_NAME);
  if (!displayName.trim()) {
    throw new Error("entity display_name must be non-empty");
  }
  if (EXPLORATION_ENTITY_KINDS.indexOf(value.kind) === -1) {
    throw new Error("entity kind is not a stable value");
  }
  if (value.portrait_ref !== null) {
    throw new Error("portrait_ref must be null in this schema version");
  }
  return value;
}

function validateExplorationLookObject(value) {
  requireExactFields(value, "look object", ["identity", "display_name"], []);
  requireIdentity(value.identity, "object.identity");
  var objectName = requireString(value.display_name, "display_name", EXPLORATION_MAX_DISPLAY_NAME);
  if (!objectName.trim()) {
    throw new Error("object display_name must be non-empty");
  }
  return value;
}

function validateExplorationLookRoom(value) {
  requireExactFields(value, "look room", ["identity", "display_name", "room"], []);
  requireIdentity(value.identity, "room.identity");
  var roomName = requireString(value.display_name, "display_name", EXPLORATION_MAX_DISPLAY_NAME);
  if (!roomName.trim()) {
    throw new Error("room display_name must be non-empty");
  }
  if (value.room !== true) {
    throw new Error("room marker must be true");
  }
  return value;
}

function validateExplorationLook(value) {
  requireExactFields(value, "look", ["room", "entities", "objects"], []);
  validateExplorationLookRoom(value.room);
  if (!Array.isArray(value.entities) || value.entities.length > EXPLORATION_MAX_LOOK_ENTITIES) {
    throw new Error("look entities must be a list of at most " + EXPLORATION_MAX_LOOK_ENTITIES + " entries");
  }
  value.entities.forEach(validateExplorationLookEntity);
  if (!Array.isArray(value.objects) || value.objects.length > EXPLORATION_MAX_LOOK_OBJECTS) {
    throw new Error("look objects must be a list of at most " + EXPLORATION_MAX_LOOK_OBJECTS + " entries");
  }
  value.objects.forEach(validateExplorationLookObject);
  return value;
}

function validateExplorationInteractTarget(value) {
  requireExactFields(
    value,
    "interact target",
    ["identity", "display_name", "portrait_ref", "affordances"],
    ["keywords"]
  );
  requireIdentity(value.identity, "target.identity");
  var targetName = requireString(value.display_name, "display_name", EXPLORATION_MAX_DISPLAY_NAME);
  if (!targetName.trim()) {
    throw new Error("target display_name must be non-empty");
  }
  if (value.portrait_ref !== null) {
    throw new Error("portrait_ref must be null in this schema version");
  }
  if (
    !Array.isArray(value.affordances) ||
    value.affordances.length > EXPLORATION_MAX_AFFORDANCES
  ) {
    throw new Error("affordances must be a list of at most " + EXPLORATION_MAX_AFFORDANCES + " entries");
  }
  value.affordances.forEach(validateExplorationAffordance);
  if (Object.prototype.hasOwnProperty.call(value, "keywords")) {
    if (
      !Array.isArray(value.keywords) ||
      value.keywords.length > EXPLORATION_MAX_SCRIPTED_KEYWORDS
    ) {
      throw new Error(
        "keywords must be a list of at most " + EXPLORATION_MAX_SCRIPTED_KEYWORDS + " entries"
      );
    }
    value.keywords.forEach(validateExplorationKeyword);
    var hasScripted = value.affordances.some(function (affordance) {
      return (
        affordance.kind === "action" &&
        affordance.action_id === "explore.talk_scripted"
      );
    });
    if (value.keywords.length > 0 && !hasScripted) {
      throw new Error("keywords require a talk_scripted affordance on the target");
    }
  }
  return value;
}

function validateExplorationAvailability(value, name) {
  requireExactFields(value, name, ["available"], []);
  requireBool(value.available, "available");
  return value;
}

function validateExplorationMoveRow(value) {
  requireExactFields(
    value,
    "move row",
    ["exit_ref", "label", "destination", "enabled", "disabled_reason"],
    []
  );
  requireExitRef(value.exit_ref, "exit_ref");
  var label = requireString(value.label, "label", EXPLORATION_MAX_LABEL);
  if (!label.trim()) {
    throw new Error("exit label must be non-empty");
  }
  requireNodeId(value.destination, "destination");
  var enabled = requireBool(value.enabled, "enabled");
  var disabledReason = validateExplorationDisabledReason(value.disabled_reason);
  if (disabledReason === null) {
    if (!enabled) {
      throw new Error("a disabled exit requires a disabled_reason");
    }
  } else if (enabled) {
    throw new Error("an enabled exit must not carry a disabled_reason");
  }
  return value;
}

// Exact available exploration panel v1 schema (design D10).
function validateExplorationPanel(payload) {
  requireExactFields(
    payload,
    "exploration panel",
    [
      "schema_version",
      "available",
      "kind",
      "move",
      "look",
      "interact",
      "character",
      "quests",
      "inventory",
    ],
    []
  );
  requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
  if (payload.schema_version !== 2) {
    throw new Error("unsupported exploration schema_version");
  }
  if (payload.available !== true || payload.kind !== "exploration") {
    throw new Error("exploration panel must be available with kind exploration");
  }

  if (!Array.isArray(payload.move) || payload.move.length > EXPLORATION_MAX_MOVE_EXITS) {
    throw new Error("move must be a list of at most " + EXPLORATION_MAX_MOVE_EXITS + " rows");
  }
  payload.move.forEach(validateExplorationMoveRow);
  validateExplorationLook(payload.look);
  if (
    !Array.isArray(payload.interact) ||
    payload.interact.length > EXPLORATION_MAX_INTERACT_TARGETS
  ) {
    throw new Error("interact must be a list of at most " + EXPLORATION_MAX_INTERACT_TARGETS + " targets");
  }
  var seen = {};
  payload.interact.forEach(function (target) {
    validateExplorationInteractTarget(target);
    if (seen[target.identity]) {
      throw new Error("interact target identities must be unique");
    }
    seen[target.identity] = true;
  });
  validateExplorationAvailability(payload.character, "character");
  validateExplorationAvailability(payload.quests, "quests");
  validateExplorationAvailability(payload.inventory, "inventory");

  var result = {
    schema_version: 2,
    available: true,
    kind: "exploration",
    move: payload.move,
    look: payload.look,
    interact: payload.interact,
    character: payload.character,
    quests: payload.quests,
    inventory: payload.inventory,
  };
  // Envelope guarantee (design D10): per-field bounds are ceilings, not a
  // guarantee that any combination of them fits, so the validator enforces
  // the serialized byte size directly and fails closed over the envelope.
  if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
    throw new Error("exploration payload exceeds the OOB envelope limit");
  }
  return result;
}

module.exports = {
  validateExplorationPanel: validateExplorationPanel,
  EXPLORATION_MAX_MOVE_EXITS: EXPLORATION_MAX_MOVE_EXITS,
  EXPLORATION_MAX_LOOK_ENTITIES: EXPLORATION_MAX_LOOK_ENTITIES,
  EXPLORATION_MAX_LOOK_OBJECTS: EXPLORATION_MAX_LOOK_OBJECTS,
  EXPLORATION_MAX_INTERACT_TARGETS: EXPLORATION_MAX_INTERACT_TARGETS,
  EXPLORATION_MAX_AFFORDANCES: EXPLORATION_MAX_AFFORDANCES,
  EXPLORATION_MAX_SCRIPTED_KEYWORDS: EXPLORATION_MAX_SCRIPTED_KEYWORDS,
  EXPLORATION_MAX_EXIT_REF: EXPLORATION_MAX_EXIT_REF,
  EXPLORATION_MAX_NODE_ID: EXPLORATION_MAX_NODE_ID,
  EXPLORATION_MAX_DISPLAY_NAME: EXPLORATION_MAX_DISPLAY_NAME,
  EXPLORATION_MAX_KIND: EXPLORATION_MAX_KIND,
  EXPLORATION_MAX_LABEL: EXPLORATION_MAX_LABEL,
  EXPLORATION_MAX_KEYWORD_ID: EXPLORATION_MAX_KEYWORD_ID,
  EXPLORATION_MAX_KEYWORD_LABEL: EXPLORATION_MAX_KEYWORD_LABEL,
  EXPLORATION_MAX_REASON_MESSAGE: EXPLORATION_MAX_REASON_MESSAGE,
  EXPLORATION_ACTION_KINDS: EXPLORATION_ACTION_KINDS,
  EXPLORATION_ACTION_IDS: EXPLORATION_ACTION_IDS,
  EXPLORATION_SURFACES: EXPLORATION_SURFACES,
  EXPLORATION_ENTITY_KINDS: EXPLORATION_ENTITY_KINDS,
};
