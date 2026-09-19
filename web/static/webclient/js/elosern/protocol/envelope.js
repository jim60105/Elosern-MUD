"use strict";

var C = require("./constants.js");
var core = require("./core.js");

var isPlainObject = core.isPlainObject;
var validatePanelName = core.validatePanelName;
var requireExactFields = core.requireExactFields;
var requireInt = core.requireInt;
var requireBool = core.requireBool;
var validateEpoch = core.validateEpoch;
var validateIdentifier = core.validateIdentifier;
var validateRequestId = core.validateRequestId;
var validateMessage = core.validateMessage;
var validateCorrelationId = core.validateCorrelationId;
var validateResultData = core.validateResultData;
var validateServerTime = core.validateServerTime;

var MAX_SAFE_INTEGER = C.MAX_SAFE_INTEGER;
var MODES = C.MODES;
var OUTCOMES = C.OUTCOMES;
var PANEL_ALLOWLIST = C.PANEL_ALLOWLIST;
var MAX_PANEL_COUNT = C.MAX_PANEL_COUNT;
var MAX_LAYOUT_VERSION = C.MAX_LAYOUT_VERSION;
var PROTOCOL_VERSION = C.PROTOCOL_VERSION;
var PROTOCOL_ERROR_CODES = C.PROTOCOL_ERROR_CODES;

// Panel discriminator dispatch: the unavailable form is common to every
// registered panel; the available form is validated against its schema.
function validateUnavailablePanel(payload, schemaVersion) {
  // The common unavailable discriminator: exactly schema_version, available
  // false, and a bounded reason. schema_version matches the panel's
  // registered version (so a v2 panel like context_actions is accepted).
  requireExactFields(payload, "panel", ["schema_version", "available", "reason"], []);
  requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
  if (payload.schema_version !== schemaVersion) {
    throw new Error("unsupported panel schema_version");
  }
  if (payload.available !== false) {
    throw new Error("available must be false for the unavailable form");
  }
  var reason = payload.reason;
  var hasCorrelation = Object.prototype.hasOwnProperty.call(reason, "correlation_id");
  requireExactFields(
    reason,
    "panel reason",
    ["code", "message"],
    hasCorrelation ? ["correlation_id"] : []
  );
  validateIdentifier(reason.code, "reason.code");
  validateMessage(reason.message, "reason.message");
  if (hasCorrelation) {
    validateCorrelationId(reason.correlation_id);
  }
  return payload;
}

// Panel dispatch table — one require per domain module (SRP split).
var combat = require("./panels/combat.js");
var statusPanel = require("./panels/status.js");
var localMap = require("./panels/local_map.js");
var services = require("./panels/services.js");
var creation = require("./panels/creation.js");
var exploration = require("./panels/exploration.js");
var character = require("./panels/character.js");
var art = require("./panels/art.js");
var titles = require("./panels/titles.js");
var misc = require("./panels/misc.js");
var exotic = require("./panels/exotic.js");

var PANEL_VALIDATORS = {
  art: art.validateArtPanel,
  gallery: art.validateGalleryPanel,
  exploration: exploration.validateExplorationPanel,
  character: character.validateCharacterPanel,
  title_codex: titles.validateTitleCodexPanel,
  status: statusPanel.validateStatusPanel,
  context_actions: combat.validateContextActionsPanel,
  local_map: localMap.validateLocalMapPanel,
  party: misc.validatePartyPanel,
  objectives: misc.validateObjectivesPanel,
  quest_log: misc.validateQuestLogPanel,
  dialogue: misc.validateDialoguePanel,
  services: services.validateServicesPanel,
  creation: creation.validateCreationPanel,
  lineage: localMap.validateLineagePanel,
  title_ballot: titles.validateTitleBallotPanel,
  roster: misc.validateRosterPanel,
  possession_banner: exotic.validatePossessionBannerPanel,
  lore_codex: exotic.validateLoreCodexPanel,
};


function validatePanel(name, schemaVersion, payload) {
  if (!isPlainObject(payload)) {
    throw new Error("panel " + name + " must be a JSON object");
  }
  requireInt(payload.schema_version, "panel schema_version", 1, MAX_SAFE_INTEGER);
  // Every panel (character included, since render-equipment-
  // breakdown-webclient retired the transitional character v4 branch)
  // must match its registered version exactly.
  if (payload.schema_version !== schemaVersion) {
    throw new Error(
      "panel " + name + " schema_version does not match registered version"
    );
  }
  if (payload.available === false) {
    return validateUnavailablePanel(payload, schemaVersion);
  }
  if (payload.available !== true) {
    throw new Error("panel " + name + " is missing the availability discriminator");
  }
  var validator = Object.prototype.hasOwnProperty.call(PANEL_VALIDATORS, name)
    ? PANEL_VALIDATORS[name]
    : null;
  if (validator === null) {
    throw new Error("panel " + name + " has no registered schema");
  }
  return validator(payload);
}

function validatePanels(value, knownPanels, nonempty) {
  if (!isPlainObject(value)) {
    throw new Error("panels must be a JSON object");
  }
  if (nonempty && Object.keys(value).length === 0) {
    throw new Error("panels must not be empty");
  }
  if (Object.keys(value).length > MAX_PANEL_COUNT) {
    throw new Error("panels exceeds the maximum of " + MAX_PANEL_COUNT + " panels");
  }
  var normalized = {};
  var names = Object.keys(value);
  for (var i = 0; i < names.length; i++) {
    var name = validatePanelName(names[i]);
    if (!Object.prototype.hasOwnProperty.call(knownPanels, name)) {
      throw new Error("panels contains unknown panel name " + name);
    }
    normalized[name] = validatePanel(name, knownPanels[name], value[name]);
  }
  return normalized;
}

function validateCommonMetadata(payload, name, knownPanels, panelsNonempty) {
  requireExactFields(
    payload,
    name,
    ["protocol_version", "presentation_epoch", "revision", "mode", "panels", "layout_version", "server_time"],
    []
  );
  requireInt(payload.protocol_version, "protocol_version", 1, 1);
  if (payload.protocol_version !== PROTOCOL_VERSION) {
    throw new Error("unsupported protocol_version");
  }
  var epoch = validateEpoch(payload.presentation_epoch);
  var revision = requireInt(payload.revision, "revision", 1, MAX_SAFE_INTEGER);
  if (MODES.indexOf(payload.mode) === -1) {
    throw new Error("mode must be one of " + MODES.join(","));
  }
  var layoutVersion = requireInt(payload.layout_version, "layout_version", 1, MAX_LAYOUT_VERSION);
  var panels = validatePanels(payload.panels, knownPanels, panelsNonempty);
  var serverTime = validateServerTime(payload.server_time);
  return {
    protocolVersion: PROTOCOL_VERSION,
    epoch: epoch,
    revision: revision,
    mode: payload.mode,
    panels: panels,
    layoutVersion: layoutVersion,
    serverTime: serverTime,
  };
}

function validateSnapshot(payload) {
  return validateCommonMetadata(payload, "ui_snapshot", PANEL_ALLOWLIST, true);
}

function validateUpdate(payload) {
  return validateCommonMetadata(payload, "ui_update", PANEL_ALLOWLIST, true);
}

function validateActionResult(payload) {
  requireExactFields(
    payload,
    "ui_action_result",
    ["protocol_version", "presentation_epoch", "request_id", "outcome", "code", "message", "presentation_revision"],
    ["correlation_id", "data"]
  );
  requireInt(payload.protocol_version, "protocol_version", 1, 1);
  validateEpoch(payload.presentation_epoch);
  validateRequestId(payload.request_id);
  if (OUTCOMES.indexOf(payload.outcome) === -1) {
    throw new Error("outcome must be one of " + OUTCOMES.join(","));
  }
  validateIdentifier(payload.code, "code");
  validateMessage(payload.message, "message");
  requireInt(payload.presentation_revision, "presentation_revision", 0, MAX_SAFE_INTEGER);
  var correlationId = null;
  if (payload.outcome === "error") {
    correlationId = validateCorrelationId(payload.correlation_id);
  } else if (Object.prototype.hasOwnProperty.call(payload, "correlation_id")) {
    throw new Error("correlation_id is forbidden for a non-error result");
  }
  var hasData = Object.prototype.hasOwnProperty.call(payload, "data");
  if (hasData && payload.outcome !== "success") {
    throw new Error("data is forbidden for a non-success result");
  }
  var result = {
    protocolVersion: PROTOCOL_VERSION,
    epoch: payload.presentation_epoch,
    requestId: payload.request_id,
    outcome: payload.outcome,
    code: payload.code,
    message: payload.message,
    presentationRevision: payload.presentation_revision,
    correlationId: correlationId,
  };
  if (hasData) {
    result.data = validateResultData(payload.data);
  }
  return result;
}

function validateProtocolError(payload) {
  requireExactFields(
    payload,
    "ui_protocol_error",
    ["protocol_version", "code", "message", "reload_required"],
    ["correlation_id"]
  );
  requireInt(payload.protocol_version, "protocol_version", 1, 1);
  validateIdentifier(payload.code, "code");
  if (PROTOCOL_ERROR_CODES.indexOf(payload.code) === -1) {
    throw new Error("unknown protocol error code");
  }
  validateMessage(payload.message, "message");
  requireBool(payload.reload_required, "reload_required");
  var correlationId = null;
  if (payload.code === "internal_error") {
    correlationId = validateCorrelationId(payload.correlation_id);
  } else if (Object.prototype.hasOwnProperty.call(payload, "correlation_id")) {
    throw new Error("correlation_id is forbidden outside internal_error");
  }
  return {
    protocolVersion: PROTOCOL_VERSION,
    code: payload.code,
    message: payload.message,
    reloadRequired: payload.reload_required,
    correlationId: correlationId,
  };
}

module.exports = {
  validateUnavailablePanel: validateUnavailablePanel,
  validatePanel: validatePanel,
  validatePanels: validatePanels,
  validateSnapshot: validateSnapshot,
  validateUpdate: validateUpdate,
  validateActionResult: validateActionResult,
  validateProtocolError: validateProtocolError,
};
