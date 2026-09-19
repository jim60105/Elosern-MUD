"use strict";

var C = require("../constants.js");
var core = require("../core.js");
var skillDescriptor = require("./skill_descriptor.js");

var isPlainObject = core.isPlainObject;
var validateFreeformScales = skillDescriptor.validateFreeformScales;
var validateContextActionsAffordanceParams = skillDescriptor.validateContextActionsAffordanceParams;
var codePoints = core.codePoints;
var requireExactFields = core.requireExactFields;
var requireInt = core.requireInt;
var requireBool = core.requireBool;
var requireString = core.requireString;
var validateIdentifier = core.validateIdentifier;

var MAX_SAFE_INTEGER = C.MAX_SAFE_INTEGER;
var MAX_MESSAGE_CODE_POINTS = C.MAX_MESSAGE_CODE_POINTS;
var MAX_SESSION_ID_CODE_POINTS = C.MAX_SESSION_ID_CODE_POINTS;
var MAX_PARTICIPANTS = C.MAX_PARTICIPANTS;
var MAX_SKILLS = C.MAX_SKILLS;
var MAX_DISPLAY_NAME = C.MAX_DISPLAY_NAME;
var MAX_LABEL = C.MAX_LABEL;
var MAX_DESCRIPTION = C.MAX_DESCRIPTION;
var MAX_SKILL_TARGETS = C.MAX_SKILL_TARGETS;
var MAX_SHORTHANDS = C.MAX_SHORTHANDS;
var MAX_TOKEN = C.MAX_TOKEN;
var MAX_ACTION_KEYS = C.MAX_ACTION_KEYS;
var MAX_COST_KEYS = C.MAX_COST_KEYS;
var MAX_REASON_MESSAGE = C.MAX_REASON_MESSAGE;
var SESSION_MODES = C.SESSION_MODES;
var SESSION_STATES = C.SESSION_STATES;
var TEAMS = C.TEAMS;
var PARTICIPANT_STATES = C.PARTICIPANT_STATES;
var TARGET_SPECS = C.TARGET_SPECS;
var ALLOWED_SHORTHANDS = C.ALLOWED_SHORTHANDS;
var ROOT_ACTIONS = C.ROOT_ACTIONS;
var SECONDARY_ACTIONS = C.SECONDARY_ACTIONS;
var RECOVERY_SECONDARY_ACTIONS = C.RECOVERY_SECONDARY_ACTIONS;
var CONTEXT_ACTIONS_MAX_AFFORDANCES = C.CONTEXT_ACTIONS_MAX_AFFORDANCES;
var CONTEXT_ACTIONS_MAX_AFFORDANCE_LABEL = C.CONTEXT_ACTIONS_MAX_AFFORDANCE_LABEL;
var CONTEXT_ACTIONS_MAX_PARAM_KEYS = C.CONTEXT_ACTIONS_MAX_PARAM_KEYS;
var CONTEXT_ACTIONS_MAX_PARAM_STRING = C.CONTEXT_ACTIONS_MAX_PARAM_STRING;
var CONTEXT_ACTIONS_MAX_EXIT_REF = C.CONTEXT_ACTIONS_MAX_EXIT_REF;
var CONTEXT_ACTIONS_MAX_NODE_ID = C.CONTEXT_ACTIONS_MAX_NODE_ID;
var CONTEXT_ACTIONS_MAX_KEYWORD_ID = C.CONTEXT_ACTIONS_MAX_KEYWORD_ID;
var CONTEXT_ACTIONS_MAX_ITEM_KEY = C.CONTEXT_ACTIONS_MAX_ITEM_KEY;
var CONTEXT_ACTIONS_MAX_WEB_SKIP_SECONDS = C.CONTEXT_ACTIONS_MAX_WEB_SKIP_SECONDS;
var CONTEXT_ACTIONS_ACTION_CODES = C.CONTEXT_ACTIONS_ACTION_CODES;
var CONTEXT_ACTIONS_SURFACES = C.CONTEXT_ACTIONS_SURFACES;
var CONTEXT_ACTIONS_DAYPARTS = C.CONTEXT_ACTIONS_DAYPARTS;
var SKILL_CATEGORY_KEYS = C.SKILL_CATEGORY_KEYS;
var CHARACTER_MAX_KEY = C.CHARACTER_MAX_KEY;
var NODE_ID_RE = C.NODE_ID_RE;
var TOKEN_RE = C.TOKEN_RE;

var suggestions = require("./suggestions.js");
var validateSuggestions = suggestions.validateSuggestions;

function validateToken(value) {
  if (typeof value !== "string" || !TOKEN_RE.test(value) || value.length > MAX_TOKEN) {
    throw new Error("participant token must be aN or eN");
  }
  return value;
}

function validateSession(value) {
  requireExactFields(
    value,
    "combat session",
    ["session_id", "mode", "round", "state", "reason"],
    []
  );
  var sessionId = requireString(value.session_id, "session_id", MAX_SESSION_ID_CODE_POINTS);
  if (!sessionId.trim()) {
    throw new Error("session_id must be non-empty");
  }
  if (SESSION_MODES.indexOf(value.mode) === -1) {
    throw new Error("session mode must be hostile or guild_exam");
  }
  requireInt(value.round, "round", 0, MAX_SAFE_INTEGER);
  if (SESSION_STATES.indexOf(value.state) === -1) {
    throw new Error("session state must be ready or recovery");
  }
  var reason = value.reason;
  if (reason === null) {
    if (value.state !== "ready") {
      throw new Error("a recovery session requires a reason");
    }
  } else {
    var hasCorrelation = false;
    requireExactFields(reason, "session reason", ["code", "message"], []);
    validateIdentifier(reason.code, "session reason code");
    requireString(reason.message, "session reason message", MAX_REASON_MESSAGE);
    if (value.state !== "recovery") {
      throw new Error("a ready session must have a null reason");
    }
  }
  return value;
}

function validateParticipant(value) {
  requireExactFields(
    value,
    "participant",
    ["identity", "token", "display_name", "team", "state", "hp_current", "hp_maximum", "portrait_ref"],
    []
  );
  requireInt(value.identity, "identity", 1, MAX_SAFE_INTEGER);
  validateToken(value.token);
  var displayName = requireString(value.display_name, "display_name", MAX_DISPLAY_NAME);
  if (!displayName.trim()) {
    throw new Error("participant display_name must be non-empty");
  }
  if (TEAMS.indexOf(value.team) === -1) {
    throw new Error("participant team must be party or foes");
  }
  if (PARTICIPANT_STATES.indexOf(value.state) === -1) {
    throw new Error("participant state is not a stable value");
  }
  requireInt(value.hp_current, "hp_current", 0, MAX_SAFE_INTEGER);
  requireInt(value.hp_maximum, "hp_maximum", 1, MAX_SAFE_INTEGER);
  if (value.hp_current > value.hp_maximum) {
    throw new Error("participant hp_current must not exceed its maximum");
  }
  var portraitRef = value.portrait_ref;
  if (portraitRef !== null) {
    if (typeof portraitRef !== "string" || !/^[0-9]+$/.test(portraitRef)) {
      throw new Error("portrait_ref must be an opaque decimal catalog key or null");
    }
    if (portraitRef.length > 32) {
      throw new Error("portrait_ref exceeds its bound");
    }
  }
  return value;
}

function validateDisabledReason(value) {
  if (value === null) {
    return null;
  }
  requireExactFields(value, "disabled_reason", ["code", "message"], []);
  validateIdentifier(value.code, "disabled_reason code");
  requireString(value.message, "disabled_reason message", MAX_REASON_MESSAGE);
  return value;
}


function validateSkill(value) {
  requireExactFields(
    value,
    "skill",
    ["key", "label", "description", "cost", "target_spec", "element", "enabled", "disabled_reason", "targets", "shorthands"],
    ["freeform_scales"]
  );
  validateIdentifier(value.key, "skill key");
  var label = requireString(value.label, "skill label", MAX_LABEL);
  if (!label.trim()) {
    throw new Error("skill label must be non-empty");
  }
  var description = requireString(value.description, "skill description", MAX_DESCRIPTION);
  if (!description.trim()) {
    throw new Error("skill description must be non-empty");
  }
  var cost = value.cost;
  if (!isPlainObject(cost) || Object.keys(cost).length > MAX_COST_KEYS) {
    throw new Error("skill cost must be a bounded object");
  }
  Object.keys(cost).forEach(function (resource) {
    validateIdentifier(resource, "cost resource key");
    requireInt(cost[resource], "cost amount", 0, MAX_SAFE_INTEGER);
  });
  if (TARGET_SPECS.indexOf(value.target_spec) === -1) {
    throw new Error("skill target_spec is not a stable value");
  }
  if (value.element !== null) {
    validateIdentifier(value.element, "skill element");
  }
  requireBool(value.enabled, "enabled");
  var disabledReason = validateDisabledReason(value.disabled_reason);
  if (!value.enabled && disabledReason === null) {
    throw new Error("a disabled skill requires a disabled_reason");
  }
  if (value.enabled && disabledReason !== null) {
    throw new Error("an enabled skill must not carry a disabled_reason");
  }
  var targets = value.targets;
  if (!Array.isArray(targets) || targets.length > MAX_SKILL_TARGETS) {
    throw new Error("skill targets exceed their bound");
  }
  var seenTargets = {};
  targets.forEach(function (target) {
    if (typeof target !== "number" || !Number.isInteger(target) || target <= 0) {
      throw new Error("skill targets must be positive integers");
    }
    if (seenTargets[target]) {
      throw new Error("skill targets must be unique");
    }
    seenTargets[target] = true;
  });
  var shorthands = value.shorthands;
  if (!Array.isArray(shorthands) || shorthands.length > MAX_SHORTHANDS) {
    throw new Error("skill shorthands exceed their bound");
  }
  var seenShorthands = {};
  shorthands.forEach(function (shorthand) {
    if (ALLOWED_SHORTHANDS.indexOf(shorthand) === -1) {
      throw new Error("skill carries an unapproved shorthand");
    }
    if (seenShorthands[shorthand]) {
      throw new Error("skill shorthands must be unique");
    }
    seenShorthands[shorthand] = true;
  });
  if (value.target_spec !== "area" && shorthands.length > 0) {
    throw new Error("only area skills may carry shorthands");
  }
  if (value.freeform_scales !== undefined) {
    if (typeof value.cost.mp !== "number" || !Number.isInteger(value.cost.mp) || value.cost.mp <= 0) {
      throw new Error("a skill without an mp cost cannot carry freeform_scales");
    }
    validateFreeformScales(value.freeform_scales, value.cost.mp);
  }
  return value;
}

function validateActionKeys(value, name) {
  if (!Array.isArray(value) || value.length > MAX_ACTION_KEYS) {
    throw new Error(name + " exceed their bound");
  }
  var seen = {};
  value.forEach(function (key) {
    validateIdentifier(key, name + " key");
    if (seen[key]) {
      throw new Error(name + " must be unique");
    }
    seen[key] = true;
  });
  return value;
}

// Exact available context_actions combat/exploration panel v4 schema.

function validateContextActionsAffordance(value) {
  if (!isPlainObject(value)) {
    throw new Error("affordance must be a JSON object");
  }
  requireExactFields(
    value,
    "affordance",
    ["label", "navigation", "enabled", "disabled_reason"],
    ["action_id", "params", "freeform", "surface"]
  );
  var label = requireString(value.label, "label", CONTEXT_ACTIONS_MAX_AFFORDANCE_LABEL);
  if (!label.trim()) {
    throw new Error("affordance label must be non-empty");
  }
  var navigation = requireBool(value.navigation, "navigation");
  var enabled = requireBool(value.enabled, "enabled");
  var disabledReason = validateDisabledReason(value.disabled_reason);
  if (disabledReason === null) {
    if (!enabled) {
      throw new Error("a disabled affordance requires a disabled_reason");
    }
  } else if (enabled) {
    throw new Error("an enabled affordance must not carry a disabled_reason");
  }
  if (navigation) {
    requireExactFields(
      value,
      "navigation affordance",
      ["surface", "label", "navigation", "enabled", "disabled_reason"],
      []
    );
    if (CONTEXT_ACTIONS_SURFACES.indexOf(value.surface) === -1) {
      throw new Error("affordance surface is not a stable value");
    }
    return {
      surface: value.surface,
      label: label,
      navigation: true,
      enabled: enabled,
      disabled_reason: disabledReason,
    };
  }
  requireExactFields(
    value,
    "action affordance",
    ["action_id", "label", "params", "freeform", "navigation", "enabled", "disabled_reason"],
    []
  );
  var actionId = validateIdentifier(value.action_id, "action_id");
  if (CONTEXT_ACTIONS_ACTION_CODES.indexOf(actionId) === -1) {
    throw new Error("action_id is not a registered exploration action");
  }
  if (typeof value.freeform !== "boolean") {
    throw new Error("affordance freeform must be a boolean");
  }
  if (value.freeform !== (actionId === "explore.talk_freeform")) {
    throw new Error("freeform must be true exactly for explore.talk_freeform");
  }
  var params = validateContextActionsAffordanceParams(actionId, value.params);
  return {
    action_id: actionId,
    label: label,
    params: params,
    freeform: value.freeform,
    navigation: false,
    enabled: enabled,
    disabled_reason: disabledReason,
  };
}

function validateContextActionsExplorationForm(payload) {
  requireExactFields(
    payload,
    "context_actions exploration form",
    ["schema_version", "available", "kind", "affordances", "suggestions"],
    []
  );
  if (payload.available !== true || payload.kind !== "exploration") {
    throw new Error("exploration form must be available with kind exploration");
  }
  if (
    !Array.isArray(payload.affordances) ||
    payload.affordances.length > CONTEXT_ACTIONS_MAX_AFFORDANCES
  ) {
    throw new Error(
      "affordances must be a list of at most " + CONTEXT_ACTIONS_MAX_AFFORDANCES + " entries"
    );
  }
  var affordances = payload.affordances.map(validateContextActionsAffordance);
  return {
    schema_version: 5,
    available: true,
    kind: "exploration",
    affordances: affordances,
    suggestions: validateSuggestions(payload.suggestions),
  };
}

function validateContextActionsPanel(payload) {
  requireExactFields(
    payload,
    "context_actions panel",
    ["schema_version", "available", "kind"],
    ["session", "participants", "root_actions", "secondary_actions", "skills", "affordances", "suggestions"]
  );
  requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
  if (payload.schema_version !== 5) {
    throw new Error("unsupported context_actions panel schema_version");
  }
  if (payload.available !== true) {
    throw new Error("context_actions panel must be available");
  }
  if (payload.kind === "exploration") {
    return validateContextActionsExplorationForm(payload);
  }
  if (payload.kind !== "combat") {
    throw new Error("context_actions panel kind must be combat or exploration");
  }
  requireExactFields(
    payload,
    "context_actions panel",
    ["schema_version", "available", "kind", "session", "participants", "root_actions", "secondary_actions", "skills", "suggestions"],
    []
  );

  var session = validateSession(payload.session);

  var participants = payload.participants;
  if (!Array.isArray(participants) || participants.length > MAX_PARTICIPANTS) {
    throw new Error("participants exceed their bound");
  }
  participants.forEach(validateParticipant);

  var rootActions = validateActionKeys(payload.root_actions, "root_actions");
  var secondaryActions = validateActionKeys(payload.secondary_actions, "secondary_actions");

  if (session.state === "ready") {
    if (
      rootActions.length !== ROOT_ACTIONS.length ||
      rootActions.some(function (key, index) { return key !== ROOT_ACTIONS[index]; })
    ) {
      throw new Error("ready session must expose the exact root actions");
    }
    if (
      secondaryActions.length !== SECONDARY_ACTIONS.length ||
      secondaryActions.some(function (key, index) { return key !== SECONDARY_ACTIONS[index]; })
    ) {
      throw new Error("ready session must expose confirmed Forfeit");
    }
  } else {
    if (rootActions.length > 0) {
      throw new Error("recovery session exposes no cast or flee action");
    }
    if (
      secondaryActions.length !== RECOVERY_SECONDARY_ACTIONS.length ||
      secondaryActions.some(function (key, index) { return key !== RECOVERY_SECONDARY_ACTIONS[index]; })
    ) {
      throw new Error("recovery session must retain confirmed Forfeit");
    }
  }

  var skills = payload.skills;
  if (!Array.isArray(skills) || skills.length > SKILL_CATEGORY_KEYS.length) {
    throw new Error("category groups exceed their bound");
  }
  var skillViews = [];
  skills.forEach(function (category) {
    requireExactFields(
      category,
      "category group",
      ["category", "label", "groups"],
      []
    );
    validateIdentifier(category.category, "category key");
    if (SKILL_CATEGORY_KEYS.indexOf(category.category) === -1) {
      throw new Error("category key is not a registered category");
    }
    var label = requireString(category.label, "category label", MAX_LABEL);
    if (!label.trim()) {
      throw new Error("category label must be non-empty");
    }
    if (!Array.isArray(category.groups) || category.groups.length === 0) {
      throw new Error("category groups must be non-empty");
    }
    category.groups.forEach(function (subGroup) {
      requireExactFields(
        subGroup,
        "skill group",
        ["group", "label", "skills"],
        []
      );
      if (subGroup.group === null) {
        if (subGroup.label !== null) {
          throw new Error("a null group key requires a null label");
        }
      } else {
        // A bounded non-empty string, not an identifier: sexual-act
        // sub-groups are keyed by their Traditional Chinese line names
        // (獨處, 羞恥, ...), mirroring the character panel's contract.
        requireString(subGroup.group, "skill group key", CHARACTER_MAX_KEY);
        if (!subGroup.group.trim()) {
          throw new Error("a non-null group key must be non-empty");
        }
        if (typeof subGroup.label !== "string" || !subGroup.label.trim()) {
          throw new Error("a non-null group key requires a non-empty label");
        }
      }
      if (!Array.isArray(subGroup.skills) || subGroup.skills.length === 0) {
        throw new Error("skill group skills must be non-empty");
      }
      subGroup.skills.forEach(function (skill) {
        validateSkill(skill);
        skillViews.push(skill);
      });
    });
  });
  if (skillViews.length > MAX_SKILLS) {
    throw new Error("flattened skill count exceeds their bound");
  }

  var identitySet = {};
  participants.forEach(function (participant) {
    identitySet[participant.identity] = true;
  });
  skillViews.forEach(function (skill) {
    skill.targets.forEach(function (target) {
      if (!identitySet[target]) {
        throw new Error("skill targets must reference a presented participant");
      }
    });
  });
  var skillKeys = {};
  skillViews.forEach(function (skill) {
    if (skillKeys[skill.key]) {
      throw new Error("skill keys must be unique");
    }
    skillKeys[skill.key] = true;
  });
  // Combat proposals are out of scope: the combat form always reports the
  // suggestions envelope as exactly unavailable.
  var combatSuggestions = validateSuggestions(payload.suggestions);
  if (
    combatSuggestions.status !== "unavailable" ||
    Object.keys(combatSuggestions).length !== 1
  ) {
    throw new Error("combat suggestions must be exactly unavailable");
  }
  return Object.assign({}, payload, { suggestions: combatSuggestions });
}

module.exports = {
  validateContextActionsPanel: validateContextActionsPanel,
  validateContextActionsAffordanceParams: validateContextActionsAffordanceParams,
};
