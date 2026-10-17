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
var CONTEXT_ACTIONS_SCHEMA_VERSION = C.CONTEXT_ACTIONS_SCHEMA_VERSION;
var MAX_PARTICIPANTS = C.MAX_PARTICIPANTS;
var MAX_ACTORS = C.MAX_ACTORS;
var MAX_ITEMS = C.MAX_ITEMS;
var MAX_TACTICS = C.MAX_TACTICS;
var MAX_ITEM_SUMMARY_CODE_POINTS = C.MAX_ITEM_SUMMARY_CODE_POINTS;
var MAX_PARTICIPANT_CONDITIONS = C.MAX_PARTICIPANT_CONDITIONS;
var MAX_CONDITION_LABEL = C.MAX_CONDITION_LABEL;
var SEVERITIES = C.SEVERITIES;
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
var MAX_REASON_CODE = C.MAX_REASON_CODE;
var SESSION_MODES = C.SESSION_MODES;
var SESSION_STATES = C.SESSION_STATES;
var TEAMS = C.TEAMS;
var PARTICIPANT_STATES = C.PARTICIPANT_STATES;
var TARGET_SPECS = C.TARGET_SPECS;
var ITEM_TARGET_SPECS = C.ITEM_TARGET_SPECS;
var TACTIC_KEYS = C.TACTIC_KEYS;
var ALLOWED_SHORTHANDS = C.ALLOWED_SHORTHANDS;
var ROOT_ACTIONS = C.ROOT_ACTIONS;
var SECONDARY_ACTIONS = C.SECONDARY_ACTIONS;
var RECOVERY_SECONDARY_ACTIONS = C.RECOVERY_SECONDARY_ACTIONS;
var FREEFORM_SCALES_ALLOWED = C.FREEFORM_SCALES_ALLOWED;
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
    ["session_id", "mode", "round", "round_revision", "state", "reason"],
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
  requireInt(value.round_revision, "round_revision", 0, MAX_SAFE_INTEGER);
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
    ["identity", "token", "display_name", "team", "state", "hp_current", "hp_maximum", "portrait_ref", "conditions"],
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
  validateParticipantConditions(value.conditions);
  return value;
}

// v6 participant conditions: the status panel's code, label and severity.
function validateParticipantConditions(value) {
  if (!Array.isArray(value) || value.length > MAX_PARTICIPANT_CONDITIONS) {
    throw new Error(
      "participant conditions must be a list of at most " + MAX_PARTICIPANT_CONDITIONS + " rows"
    );
  }
  value.forEach(function (row) {
    requireExactFields(row, "participant condition", ["code", "label", "severity"], []);
    validateIdentifier(row.code, "participant condition code");
    var label = requireString(row.label, "participant condition label", MAX_CONDITION_LABEL);
    if (!label.trim()) {
      throw new Error("participant condition label must be non-empty");
    }
    if (SEVERITIES.indexOf(row.severity) === -1) {
      throw new Error("participant condition severity is not a stable severity");
    }
  });
  return value;
}

function validateDisabledReason(value) {
  if (value === null) {
    return null;
  }
  requireExactFields(value, "disabled_reason", ["code", "message"], []);
  validateIdentifier(value.code, "disabled_reason code");
  if (value.code.length > MAX_REASON_CODE) {
    throw new Error("disabled_reason code exceeds its bound");
  }
  requireString(value.message, "disabled_reason message", MAX_REASON_MESSAGE);
  if (!value.message.trim()) {
    throw new Error("disabled_reason message must be non-empty");
  }
  return value;
}


function validateSkill(value) {
  requireExactFields(
    value,
    "skill",
    ["key", "label", "description", "cost", "target_spec", "element", "enabled", "disabled_reason", "targets", "shorthands", "hostile", "beneficial"],
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
  requireBool(value.hostile, "hostile");
  requireBool(value.beneficial, "beneficial");
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

// Exact available context_actions combat/exploration panel v6 schema.

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
  if (payload.schema_version !== CONTEXT_ACTIONS_SCHEMA_VERSION) {
    throw new Error("unsupported context_actions panel schema_version");
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
    // Pinned to the registered version above; never a restated literal.
    schema_version: payload.schema_version,
    available: true,
    kind: "exploration",
    affordances: affordances,
    suggestions: validateSuggestions(payload.suggestions),
  };
}


function validateActorSummary(value) {
  requireExactFields(value, "actor summary", ["identity", "commandable", "reason"], []);
  requireInt(value.identity, "identity", 1, MAX_SAFE_INTEGER);
  requireBool(value.commandable, "commandable");
  var reason = validateDisabledReason(value.reason);
  if (value.commandable && reason !== null) {
    throw new Error("a commandable actor must have a null reason");
  }
  if (!value.commandable && reason === null) {
    throw new Error("a non-commandable actor requires a reason");
  }
  return value;
}

// One bounded list of unique positive participant identities.
function validateIdentityList(value, name, allowEmpty) {
  if (!Array.isArray(value) || value.length > MAX_SKILL_TARGETS) {
    throw new Error(name + " exceed their bound");
  }
  if (!allowEmpty && value.length === 0) {
    throw new Error(name + " must be non-empty");
  }
  var seen = Object.create(null);
  value.forEach(function (target) {
    if (typeof target !== "number" || !Number.isInteger(target) || target <= 0) {
      throw new Error(name + " must be positive integers");
    }
    if (seen[target]) {
      throw new Error(name + " must be unique");
    }
    seen[target] = true;
  });
  return value;
}

// Validate the requested actor's grouped skill catalog; returns the flattened
// descriptors.
function validateChoicesSkills(skills) {
  if (!Array.isArray(skills) || skills.length > SKILL_CATEGORY_KEYS.length) {
    throw new Error("category groups exceed their bound");
  }
  var skillViews = [];
  skills.forEach(function (category) {
    requireExactFields(category, "category group", ["category", "label", "groups"], []);
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
      requireExactFields(subGroup, "skill group", ["group", "label", "skills"], []);
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
  var skillKeys = Object.create(null);
  skillViews.forEach(function (skill) {
    if (skillKeys[skill.key]) {
      throw new Error("skill keys must be unique");
    }
    skillKeys[skill.key] = true;
  });
  return skillViews;
}

function validateItemChoice(value) {
  requireExactFields(
    value,
    "item choice",
    ["item_key", "label", "summary", "quantity", "enabled", "reason", "target_spec", "targets", "hostile", "beneficial"],
    []
  );
  var itemKey = requireString(value.item_key, "item_key", CONTEXT_ACTIONS_MAX_ITEM_KEY);
  if (!itemKey.trim()) {
    throw new Error("item_key must be non-empty");
  }
  var label = requireString(value.label, "item label", MAX_LABEL);
  if (!label.trim()) {
    throw new Error("item label must be non-empty");
  }
  requireString(value.summary, "summary", MAX_ITEM_SUMMARY_CODE_POINTS);
  requireInt(value.quantity, "quantity", 0, MAX_SAFE_INTEGER);
  requireBool(value.enabled, "enabled");
  var reason = validateDisabledReason(value.reason);
  if (!value.enabled && reason === null) {
    throw new Error("a disabled item requires a reason");
  }
  if (value.enabled && reason !== null) {
    throw new Error("an enabled item must not carry a reason");
  }
  if (ITEM_TARGET_SPECS.indexOf(value.target_spec) === -1) {
    throw new Error("item target_spec is not a stable value");
  }
  validateIdentityList(value.targets, "item targets", true);
  requireBool(value.hostile, "hostile");
  requireBool(value.beneficial, "beneficial");
  return value;
}

function validateTacticChoice(value) {
  requireExactFields(
    value,
    "tactic choice",
    ["key", "label", "enabled", "reason", "targets"],
    []
  );
  if (TACTIC_KEYS.indexOf(value.key) === -1) {
    throw new Error("tactic key is not defend, dodge, or taunt");
  }
  var label = requireString(value.label, "tactic label", MAX_LABEL);
  if (!label.trim()) {
    throw new Error("tactic label must be non-empty");
  }
  requireBool(value.enabled, "enabled");
  var reason = validateDisabledReason(value.reason);
  if (!value.enabled && reason === null) {
    throw new Error("a disabled tactic requires a reason");
  }
  if (value.enabled && reason !== null) {
    throw new Error("an enabled tactic must not carry a reason");
  }
  validateIdentityList(value.targets, "tactic targets", true);
  if ((value.key === "defend" || value.key === "dodge") && value.targets.length > 0) {
    throw new Error(value.key + " tactic must have empty targets");
  }
  return value;
}

function validateChoices(value, seenActors, identitySet) {
  requireExactFields(value, "choices", ["actor_id", "skills", "items", "tactics"], []);
  requireInt(value.actor_id, "actor_id", 1, MAX_SAFE_INTEGER);
  if (!seenActors[value.actor_id]) {
    throw new Error("choices actor_id must reference an actor summary");
  }
  var skillViews = validateChoicesSkills(value.skills);
  skillViews.forEach(function (skill) {
    skill.targets.forEach(function (target) {
      if (!identitySet[target]) {
        throw new Error("skill targets must reference a presented participant");
      }
    });
  });
  if (!Array.isArray(value.items) || value.items.length > MAX_ITEMS) {
    throw new Error("item choices exceed bound");
  }
  var itemKeys = Object.create(null);
  value.items.forEach(function (item) {
    validateItemChoice(item);
    item.targets.forEach(function (target) {
      if (!identitySet[target]) {
        throw new Error("item targets must reference a presented participant");
      }
    });
    if (itemKeys[item.item_key]) {
      throw new Error("item keys must be unique");
    }
    itemKeys[item.item_key] = true;
  });
  if (!Array.isArray(value.tactics) || value.tactics.length > MAX_TACTICS) {
    throw new Error("tactic choices exceed bound");
  }
  var tacticKeys = Object.create(null);
  value.tactics.forEach(function (tactic) {
    validateTacticChoice(tactic);
    tactic.targets.forEach(function (target) {
      if (!identitySet[target]) {
        throw new Error("tactic targets must reference a presented participant");
      }
    });
    if (tacticKeys[tactic.key]) {
      throw new Error("tactic keys must be unique");
    }
    tacticKeys[tactic.key] = true;
  });
  return value;
}

// The closed v7 draft-command union: one canonical spelling per kind.
function validateDraftCommand(value) {
  requireExactFields(value, "draft command", ["kind", "payload"], []);
  var kind = value.kind;
  var payload = value.payload;
  if (!isPlainObject(payload)) {
    throw new Error("draft command payload must be a dict");
  }
  if (kind === "skill") {
    requireExactFields(payload, "skill draft command payload", ["skill_key"], ["target_ids", "target_shorthand", "scale"]);
    validateIdentifier(payload.skill_key, "skill_key");
    if (payload.skill_key === "flee") {
      throw new Error("flee is forbidden in draft entries");
    }
    var hasIds = payload.target_ids !== undefined && payload.target_ids !== null;
    var hasShorthand = payload.target_shorthand !== undefined && payload.target_shorthand !== null;
    if (hasIds && hasShorthand) {
      throw new Error("a skill draft command carries target_ids or target_shorthand, not both");
    }
    if (hasIds) {
      validateIdentityList(payload.target_ids, "skill draft target_ids", false);
    }
    if (hasShorthand && ALLOWED_SHORTHANDS.indexOf(payload.target_shorthand) === -1) {
      throw new Error("skill draft target_shorthand is not an approved shorthand");
    }
    if (payload.scale !== undefined && payload.scale !== null) {
      if (typeof payload.scale !== "number") {
        throw new Error("skill draft scale must be numeric");
      }
      if (FREEFORM_SCALES_ALLOWED.indexOf(payload.scale) === -1) {
        throw new Error("skill draft scale is not an approved scale");
      }
    }
  } else if (kind === "item") {
    requireExactFields(payload, "item draft command payload", ["item_key"], ["target_id"]);
    var itemKey = requireString(payload.item_key, "item_key", CONTEXT_ACTIONS_MAX_ITEM_KEY);
    if (!itemKey.trim()) {
      throw new Error("item_key must be non-empty");
    }
    if (payload.target_id !== undefined && payload.target_id !== null) {
      requireInt(payload.target_id, "target_id", 1, MAX_SAFE_INTEGER);
    }
  } else if (kind === "tactical") {
    requireExactFields(payload, "tactical draft command payload", ["key"], ["target_id"]);
    if (TACTIC_KEYS.indexOf(payload.key) === -1) {
      throw new Error("tactical draft key must be defend, dodge, or taunt");
    }
    var targetId = payload.target_id;
    if (payload.key === "taunt") {
      if (targetId === undefined || targetId === null) {
        throw new Error("a taunt draft command requires a target_id");
      }
      requireInt(payload.target_id, "target_id", 1, MAX_SAFE_INTEGER);
    } else if (targetId !== undefined && targetId !== null) {
      throw new Error(payload.key + " must have no target_id");
    }
  } else {
    throw new Error("unknown draft command kind " + kind);
  }
  return value;
}

function validateDraftEntry(value) {
  requireExactFields(value, "draft entry", ["actor_id", "command"], []);
  requireInt(value.actor_id, "actor_id", 1, MAX_SAFE_INTEGER);
  validateDraftCommand(value.command);
  return value;
}


function choicesHaveEnabled(choices) {
  var enabled = false;
  choices.skills.forEach(function (category) {
    category.groups.forEach(function (group) {
      group.skills.forEach(function (skill) {
        if (skill.enabled) {
          enabled = true;
        }
      });
    });
  });
  choices.items.forEach(function (item) {
    if (item.enabled) {
      enabled = true;
    }
  });
  choices.tactics.forEach(function (tactic) {
    if (tactic.enabled) {
      enabled = true;
    }
  });
  return enabled;
}


function validateReselectionReason(value) {
  requireExactFields(value, "reselection reason", ["actor_id", "reason"], []);
  requireInt(value.actor_id, "actor_id", 1, MAX_SAFE_INTEGER);
  if (validateDisabledReason(value.reason) === null) {
    throw new Error("reselection reason cannot be null");
  }
  return value;
}

function validateDraftProgress(value) {
  requireExactFields(
    value,
    "draft progress",
    ["round_revision", "draft_version", "required_actor_ids", "entries", "needs_selection_ids", "reselection_reasons"],
    []
  );
  requireInt(value.round_revision, "round_revision", 0, MAX_SAFE_INTEGER);
  requireInt(value.draft_version, "draft_version", 0, MAX_SAFE_INTEGER);

  var required = value.required_actor_ids;
  if (!Array.isArray(required) || required.length > MAX_ACTORS) {
    throw new Error("required_actor_ids exceeds actor bound");
  }
  var seenRequired = Object.create(null);
  required.forEach(function (actorId) {
    requireInt(actorId, "required actor id", 1, MAX_SAFE_INTEGER);
    if (seenRequired[actorId]) {
      throw new Error("required_actor_ids must be unique");
    }
    seenRequired[actorId] = true;
  });

  var entries = value.entries;
  if (!Array.isArray(entries) || entries.length > MAX_ACTORS) {
    throw new Error("draft entries exceed actor bound");
  }
  var seenEntries = Object.create(null);
  entries.forEach(function (entry) {
    validateDraftEntry(entry);
    if (!seenRequired[entry.actor_id]) {
      throw new Error("draft entry actor must be in required_actor_ids");
    }
    if (seenEntries[entry.actor_id]) {
      throw new Error("draft entries must have unique actor IDs");
    }
    seenEntries[entry.actor_id] = true;
  });

  var needs = value.needs_selection_ids;
  if (!Array.isArray(needs) || needs.length > MAX_ACTORS) {
    throw new Error("needs_selection_ids exceeds actor bound");
  }
  var seenNeeds = Object.create(null);
  needs.forEach(function (actorId) {
    requireInt(actorId, "needs selection actor id", 1, MAX_SAFE_INTEGER);
    if (!seenRequired[actorId]) {
      throw new Error("needs_selection_ids actor must be in required_actor_ids");
    }
    if (seenNeeds[actorId]) {
      throw new Error("needs_selection_ids must be unique");
    }
    seenNeeds[actorId] = true;
  });

  var reasons = value.reselection_reasons;
  if (!Array.isArray(reasons) || reasons.length > MAX_ACTORS) {
    throw new Error("reselection_reasons exceeds actor bound");
  }
  var seenReasons = Object.create(null);
  reasons.forEach(function (row) {
    validateReselectionReason(row);
    if (!seenRequired[row.actor_id] || !seenNeeds[row.actor_id]) {
      throw new Error("reselection reason actor must be in needs_selection_ids");
    }
    if (seenReasons[row.actor_id]) {
      throw new Error("reselection reasons must have unique actor IDs");
    }
    seenReasons[row.actor_id] = true;
  });
  return value;
}

function validateContextActionsPanel(payload) {
  requireExactFields(
    payload,
    "context_actions panel",
    ["schema_version", "available", "kind"],
    ["session", "participants", "root_actions", "secondary_actions", "actors", "choices", "draft", "affordances", "suggestions"]
  );
  requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
  if (payload.schema_version !== CONTEXT_ACTIONS_SCHEMA_VERSION) {
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
    ["schema_version", "available", "kind", "session", "participants", "root_actions", "secondary_actions", "actors", "choices", "draft", "suggestions"],
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

  var actors = payload.actors;
  if (!Array.isArray(actors) || actors.length > MAX_ACTORS) {
    throw new Error("actors exceed their bound");
  }
  var seenActors = Object.create(null);
  actors.forEach(function (actor) {
    validateActorSummary(actor);
    if (seenActors[actor.identity]) {
      throw new Error("actors must have unique identities");
    }
    seenActors[actor.identity] = true;
  });

  var identitySet = {};
  participants.forEach(function (participant) {
    identitySet[participant.identity] = true;
  });

  var choicesView = null;
  var draftView = null;
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
      throw new Error("ready session must expose confirmed Surrender");
    }
    if (payload.choices === null || payload.choices === undefined) {
      throw new Error("ready session must have choices");
    }
    choicesView = validateChoices(payload.choices, seenActors, identitySet);
    if (payload.draft === null || payload.draft === undefined) {
      throw new Error("ready session must have draft");
    }
    draftView = validateDraftProgress(payload.draft);
    if (draftView.round_revision !== session.round_revision) {
      throw new Error("draft round_revision must match session round_revision");
    }
    var allyIdentities = Object.create(null);
    var enemyIdentities = Object.create(null);
    participants.forEach(function (participant) {
      if (participant.team === "party") {
        allyIdentities[participant.identity] = true;
      } else {
        enemyIdentities[participant.identity] = true;
      }
    });
    actors.forEach(function (actor) {
      if (!allyIdentities[actor.identity]) {
        throw new Error("actor summaries must reference presented allies");
      }
    });
    draftView.required_actor_ids.forEach(function (actorId) {
      if (!allyIdentities[actorId]) {
        throw new Error("required actors must be presented allies");
      }
    });
    var chosen = actors.filter(function (actor) {
      return actor.identity === choicesView.actor_id;
    })[0];
    if (!chosen.commandable && choicesHaveEnabled(choicesView)) {
      throw new Error("a noncommandable actor must have no enabled choices");
    }
    choicesView.tactics.forEach(function (tactic) {
      if (tactic.key !== "taunt") {
        return;
      }
      tactic.targets.forEach(function (targetId) {
        if (!enemyIdentities[targetId]) {
          throw new Error("taunt targets must be presented enemies");
        }
      });
    });
  } else {
    if (rootActions.length > 0) {
      throw new Error("recovery session exposes no root actions");
    }
    if (
      secondaryActions.length !== RECOVERY_SECONDARY_ACTIONS.length ||
      secondaryActions.some(function (key, index) { return key !== RECOVERY_SECONDARY_ACTIONS[index]; })
    ) {
      throw new Error("recovery session must retain confirmed Surrender");
    }
    if (actors.length > 0) {
      throw new Error("recovery session actors must be empty");
    }
    if (payload.choices !== null) {
      throw new Error("recovery session choices must be null");
    }
    if (payload.draft !== null) {
      throw new Error("recovery session draft must be null");
    }
  }

  // Combat proposals are out of scope: the combat form always reports the
  // suggestions envelope as exactly unavailable.
  var combatSuggestions = validateSuggestions(payload.suggestions);
  if (
    combatSuggestions.status !== "unavailable" ||
    Object.keys(combatSuggestions).length !== 1
  ) {
    throw new Error("combat suggestions must be exactly unavailable");
  }
  return Object.assign({}, payload, {
    choices: choicesView,
    draft: draftView,
    suggestions: combatSuggestions,
  });
}

module.exports = {
  validateContextActionsPanel: validateContextActionsPanel,
  validateContextActionsAffordanceParams: validateContextActionsAffordanceParams,
};
