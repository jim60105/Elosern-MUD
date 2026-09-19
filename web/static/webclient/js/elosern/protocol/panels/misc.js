// party / objectives / dialogue / roster panel validators (mirrors of the
// same-named presentation modules). quest_log and each domain keep their
// own module; this file wires them for the envelope dispatch.

"use strict";

var C = require("../constants.js");
var core = require("../core.js");

var jsonByteSize = core.jsonByteSize;
var requireExactFields = core.requireExactFields;
var requireInt = core.requireInt;
var requireBool = core.requireBool;
var requireString = core.requireString;
var hasLoneSurrogate = core.hasLoneSurrogate;

var MAX_SAFE_INTEGER = C.MAX_SAFE_INTEGER;
var MAX_CANONICAL_JSON_BYTES = C.MAX_CANONICAL_JSON_BYTES;
var PARTY_SCHEMA_VERSION = C.PARTY_SCHEMA_VERSION;
var PARTY_MAX_ROWS = C.PARTY_MAX_ROWS;
var PARTY_MAX_DISPLAY_NAME = C.PARTY_MAX_DISPLAY_NAME;
var OBJECTIVES_SCHEMA_VERSION = C.OBJECTIVES_SCHEMA_VERSION;
var OBJECTIVES_MAX_ROWS = C.OBJECTIVES_MAX_ROWS;
var OBJECTIVES_MAX_QUEST_ID = C.OBJECTIVES_MAX_QUEST_ID;
var OBJECTIVES_MAX_DISPLAY_NAME = C.OBJECTIVES_MAX_DISPLAY_NAME;
var OBJECTIVES_MAX_OBJECTIVE_LINE = C.OBJECTIVES_MAX_OBJECTIVE_LINE;
var OBJECTIVES_MAX_DEADLINE_LINE = C.OBJECTIVES_MAX_DEADLINE_LINE;
var QUEST_LOG_SCHEMA_VERSION = C.QUEST_LOG_SCHEMA_VERSION;
var QUEST_LOG_MAX_ROWS = C.QUEST_LOG_MAX_ROWS;
var DIALOGUE_SCHEMA_VERSION = C.DIALOGUE_SCHEMA_VERSION;
var DIALOGUE_MAX_CHOICES = C.DIALOGUE_MAX_CHOICES;
var DIALOGUE_MAX_KEYWORD_ID = C.DIALOGUE_MAX_KEYWORD_ID;
var DIALOGUE_MAX_KEYWORD_LABEL = C.DIALOGUE_MAX_KEYWORD_LABEL;
var DIALOGUE_MAX_LINE = C.DIALOGUE_MAX_LINE;
var ROSTER_SCHEMA_VERSION = C.ROSTER_SCHEMA_VERSION;
var ROSTER_MAX_ROWS = C.ROSTER_MAX_ROWS;
var ROSTER_MAX_NAME = C.ROSTER_MAX_NAME;
var ROSTER_MAX_SUBJECT_KEY = C.ROSTER_MAX_SUBJECT_KEY;
var MAX_MEDIA_URL = C.MAX_MEDIA_URL;
var ROSTER_MAX_ALT = C.ROSTER_MAX_ALT;
var ROSTER_MAX_STATUS = C.ROSTER_MAX_STATUS;
var ROSTER_LOCK_REASON = C.ROSTER_LOCK_REASON;
var art = require("./art.js");
var validateArtFaceRect = art.validateArtFaceRect;
var validateArtPlaceholder = art.validateArtPlaceholder;
var questLog = require("./quest_log.js");
var validateQuestLogPanel = questLog.validateQuestLogPanel;

function validatePartySlot(value, index) {
  var name = "party slot " + index;
  requireExactFields(
    value,
    name,
    ["identity", "display_name", "portrait_ref", "hp_current", "hp_maximum", "bond_stage"],
    []
  );
  var identity = requireInt(value.identity, "identity", 1, MAX_SAFE_INTEGER);
  var displayName = requireString(value.display_name, "display_name", PARTY_MAX_DISPLAY_NAME);
  if (displayName.length === 0 || hasLoneSurrogate(displayName)) {
    throw new Error("slot display_name must be non-empty");
  }
  if (value.portrait_ref !== null) {
    throw new Error("portrait_ref must be null in this schema version");
  }
  var hpCurrent = requireInt(value.hp_current, "hp_current", 0, MAX_SAFE_INTEGER);
  var hpMaximum = requireInt(value.hp_maximum, "hp_maximum", 0, MAX_SAFE_INTEGER);
  var bondStage = requireString(value.bond_stage, "bond_stage", PARTY_MAX_DISPLAY_NAME);
  if (bondStage.length === 0 || hasLoneSurrogate(bondStage)) {
    throw new Error("slot bond_stage must be a non-empty stage name");
  }
  return {
    identity: identity,
    display_name: displayName,
    portrait_ref: null,
    hp_current: hpCurrent,
    hp_maximum: hpMaximum,
    bond_stage: bondStage,
  };
}

function validatePartyPanel(payload) {
  requireExactFields(payload, "party panel", ["schema_version", "available", "slots"], []);
  requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
  if (payload.schema_version !== PARTY_SCHEMA_VERSION) {
    throw new Error("unsupported party schema_version");
  }
  if (payload.available !== true) {
    throw new Error("party panel must be available");
  }
  var slots = payload.slots;
  if (!Array.isArray(slots)) {
    throw new Error("party slots must be a list");
  }
  if (slots.length > PARTY_MAX_ROWS) {
    throw new Error("party slots must hold at most " + PARTY_MAX_ROWS + " rows");
  }
  var normalized = [];
  var seen = {};
  for (var i = 0; i < slots.length; i++) {
    var row = validatePartySlot(slots[i], i + 1);
    if (Object.prototype.hasOwnProperty.call(seen, row.identity)) {
      throw new Error("party slot identities must be unique");
    }
    seen[row.identity] = true;
    normalized.push(row);
  }
  var result = {
    schema_version: PARTY_SCHEMA_VERSION,
    available: true,
    slots: normalized,
  };
  // Envelope guarantee mirrors the Python validator's closing check.
  if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
    throw new Error("party payload exceeds the OOB envelope limit");
  }
  return result;
}

// Objectives panel validator (mirror of
// web.webclient.presentation.objectives, webclient-align-06). At most three
// tracked quest rows in quest-log order; reward_copper is a non-negative
// integer or null; same surrogate guards as the party mirror.
function validateObjectivesRow(value, index) {
  var name = "objective row " + index;
  requireExactFields(
    value,
    name,
    [
      "quest_id",
      "display_name",
      "objective_line",
      "stage_index",
      "stage_total",
      "stage_progress",
      "objective_quantity",
      "reward_copper",
      "deadline_line",
    ],
    []
  );
  var questId = requireString(value.quest_id, "quest_id", OBJECTIVES_MAX_QUEST_ID);
  if (!questId.trim() || hasLoneSurrogate(questId)) {
    throw new Error(name + " quest_id must be non-empty");
  }
  var displayName = requireString(
    value.display_name,
    "display_name",
    OBJECTIVES_MAX_DISPLAY_NAME
  );
  if (!displayName.trim() || hasLoneSurrogate(displayName)) {
    throw new Error(name + " display_name must be non-empty");
  }
  var objectiveLine = requireString(
    value.objective_line,
    "objective_line",
    OBJECTIVES_MAX_OBJECTIVE_LINE
  );
  if (!objectiveLine.trim() || hasLoneSurrogate(objectiveLine)) {
    throw new Error(name + " objective_line must be non-empty");
  }
  requireInt(value.stage_index, "stage_index", 0, MAX_SAFE_INTEGER);
  requireInt(value.stage_total, "stage_total", 1, MAX_SAFE_INTEGER);
  requireInt(value.stage_progress, "stage_progress", 0, MAX_SAFE_INTEGER);
  requireInt(value.objective_quantity, "objective_quantity", 1, MAX_SAFE_INTEGER);
  if (value.reward_copper !== null) {
    requireInt(value.reward_copper, "reward_copper", 0, MAX_SAFE_INTEGER);
  }
  if (value.deadline_line !== null) {
    var deadline = requireString(
      value.deadline_line,
      "deadline_line",
      OBJECTIVES_MAX_DEADLINE_LINE
    );
    if (!deadline.trim() || hasLoneSurrogate(deadline)) {
      throw new Error(name + " deadline_line must be non-empty when set");
    }
  }
  return value;
}

function validateObjectivesPanel(payload) {
  requireExactFields(
    payload,
    "objectives panel",
    ["schema_version", "available", "rows"],
    []
  );
  requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
  if (payload.schema_version !== OBJECTIVES_SCHEMA_VERSION) {
    throw new Error("unsupported objectives schema_version");
  }
  if (payload.available !== true) {
    throw new Error("objectives panel must be available");
  }
  var rows = payload.rows;
  if (!Array.isArray(rows)) {
    throw new Error("objectives rows must be a list");
  }
  if (rows.length > OBJECTIVES_MAX_ROWS) {
    throw new Error(
      "objectives rows must hold at most " + OBJECTIVES_MAX_ROWS + " entries"
    );
  }
  var normalized = [];
  var seen = {};
  for (var i = 0; i < rows.length; i++) {
    var row = validateObjectivesRow(rows[i], i + 1);
    if (Object.prototype.hasOwnProperty.call(seen, row.quest_id)) {
      throw new Error("objective quest_ids must be unique");
    }
    seen[row.quest_id] = true;
    normalized.push(row);
  }
  var result = {
    schema_version: OBJECTIVES_SCHEMA_VERSION,
    available: true,
    rows: normalized,
  };
  // Envelope guarantee mirrors the Python validator's closing check.
  if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
    throw new Error("objectives payload exceeds the OOB envelope limit");
  }
  return result;
}

// Dialogue panel validator (mirror of web.webclient.presentation.dialogue,
// webclient-align-10). Available form is exactly schema_version, available,
// kind, host (party-row triple with a null portrait_ref), bond_stage (a
// stage NAME or null — never a number), a bounded line, and at most
// DIALOGUE_MAX_CHOICES unique {keyword_id, label} rows. Every string
// rejects lone surrogates exactly like the Python validator; over-bound or
// corrupt values reject, never truncate.
function validateDialoguePanel(payload) {
  requireExactFields(
    payload,
    "dialogue panel",
    ["schema_version", "available", "kind", "host", "bond_stage", "line", "choices"],
    []
  );
  requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
  if (payload.schema_version !== DIALOGUE_SCHEMA_VERSION) {
    throw new Error("unsupported dialogue schema_version");
  }
  if (payload.available !== true) {
    throw new Error("dialogue panel must be available");
  }
  if (payload.kind !== "dialogue") {
    throw new Error("dialogue kind must be dialogue");
  }
  requireExactFields(
    payload.host,
    "dialogue host",
    ["identity", "display_name", "portrait_ref"],
    []
  );
  requireInt(payload.host.identity, "identity", 1, MAX_SAFE_INTEGER);
  var hostName = requireString(
    payload.host.display_name,
    "display_name",
    PARTY_MAX_DISPLAY_NAME
  );
  if (!hostName.trim() || hasLoneSurrogate(hostName)) {
    throw new Error("host display_name must be non-empty");
  }
  if (payload.host.portrait_ref !== null) {
    throw new Error("portrait_ref must be null in this schema version");
  }
  if (payload.bond_stage !== null) {
    var bondStage = requireString(
      payload.bond_stage,
      "bond_stage",
      PARTY_MAX_DISPLAY_NAME
    );
    if (!bondStage.trim() || hasLoneSurrogate(bondStage)) {
      throw new Error("bond_stage must be non-empty when set");
    }
  }
  var line = requireString(payload.line, "line", DIALOGUE_MAX_LINE);
  if (!line.trim() || hasLoneSurrogate(line)) {
    throw new Error("dialogue line must be non-empty");
  }
  var choices = payload.choices;
  if (!Array.isArray(choices)) {
    throw new Error("dialogue choices must be a list");
  }
  if (choices.length > DIALOGUE_MAX_CHOICES) {
    throw new Error(
      "dialogue choices must hold at most " + DIALOGUE_MAX_CHOICES + " entries"
    );
  }
  // Prototype-null registry: a plain object would let a literal
  // "__proto__" keyword_id defeat the own-property duplicate check.
  var seen = Object.create(null);
  for (var i = 0; i < choices.length; i++) {
    var choice = choices[i];
    var name = "dialogue choice " + (i + 1);
    requireExactFields(choice, name, ["keyword_id", "label"], []);
    var keywordId = requireString(
      choice.keyword_id,
      "keyword_id",
      DIALOGUE_MAX_KEYWORD_ID
    );
    if (!keywordId.trim() || hasLoneSurrogate(keywordId)) {
      throw new Error(name + " keyword_id must be non-empty");
    }
    var label = requireString(
      choice.label,
      "label",
      DIALOGUE_MAX_KEYWORD_LABEL
    );
    if (!label.trim() || hasLoneSurrogate(label)) {
      throw new Error(name + " label must be non-empty");
    }
    if (Object.prototype.hasOwnProperty.call(seen, keywordId)) {
      throw new Error("dialogue choice keyword ids must be unique");
    }
    seen[keywordId] = true;
  }
  var result = {
    schema_version: DIALOGUE_SCHEMA_VERSION,
    available: true,
    kind: "dialogue",
    host: payload.host,
    bond_stage: payload.bond_stage,
    line: line,
    choices: choices,
  };
  // Envelope guarantee mirrors the Python validator's closing check.
  if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
    throw new Error("dialogue payload exceeds the OOB envelope limit");
  }
  return result;
}

// Exact available roster panel v2 schema (mirror of
// web.webclient.presentation.roster, webclient-character-roster).
function validateRosterPortrait(value) {
  requireExactFields(
    value,
    "roster portrait",
    ["subject_key", "status", "url", "aspect_ratio", "alt", "placeholder", "face_rect"],
    []
  );
  if (value.subject_key !== null) {
    requireString(value.subject_key, "portrait subject_key", ROSTER_MAX_SUBJECT_KEY);
  }
  var status = value.status;
  if (status !== null) {
    requireString(status, "portrait status", ROSTER_MAX_STATUS);
    if (["missing", "pending", "failed", "done"].indexOf(status) === -1) {
      throw new Error("portrait status is not a stable value");
    }
  }
  var url = value.url;
  if (url !== null) {
    requireString(url, "portrait url", MAX_MEDIA_URL);
    if (url.indexOf("/art/") !== 0) {
      throw new Error("portrait url must be a same-origin media URL");
    }
  }
  if (value.aspect_ratio !== null && value.aspect_ratio !== "3:4") {
    throw new Error("portrait aspect_ratio must be 3:4");
  }
  var alt = requireString(value.alt, "portrait alt", ROSTER_MAX_ALT);
  if (!alt.trim()) {
    throw new Error("portrait alt must be non-empty");
  }
  var placeholder = validateArtPlaceholder(value.placeholder);
  if (url !== null && placeholder !== null) {
    throw new Error("portrait cannot carry both url and placeholder");
  }
  if (url === null && placeholder === null) {
    throw new Error("portrait must carry either url or placeholder");
  }
  var faceRect = validateArtFaceRect(value.face_rect);
  if (url !== null && faceRect === null) {
    throw new Error("a portrait with a url carries a face_rect");
  }
  if (url === null && faceRect !== null) {
    throw new Error("a placeholder portrait carries no face_rect");
  }
  return {
    subject_key: value.subject_key,
    status: status,
    url: url,
    aspect_ratio: value.aspect_ratio,
    alt: alt,
    placeholder: placeholder,
    face_rect: faceRect,
  };
}

function validateRosterCharacter(value, index) {
  var name = "roster character row " + index;
  requireExactFields(
    value,
    name,
    ["identity", "name", "current", "pending", "portrait"],
    []
  );
  var identity = requireInt(value.identity, "identity", 1, MAX_SAFE_INTEGER);
  var charName = requireString(value.name, "name", ROSTER_MAX_NAME);
  if (!charName.trim() || hasLoneSurrogate(charName)) {
    throw new Error(name + " name must be non-empty");
  }
  var current = requireBool(value.current, "current");
  var pending = requireBool(value.pending, "pending");
  var portrait = validateRosterPortrait(value.portrait);
  return {
    identity: identity,
    name: charName,
    current: current,
    pending: pending,
    portrait: portrait,
  };
}

function validateRosterPanel(payload) {
  requireExactFields(
    payload,
    "roster panel",
    [
      "schema_version",
      "available",
      "characters",
      "max_characters",
      "can_create",
      "switch_locked",
      "lock_reason",
    ],
    []
  );
  requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
  if (payload.schema_version !== ROSTER_SCHEMA_VERSION) {
    throw new Error("unsupported roster schema_version");
  }
  if (payload.available !== true) {
    throw new Error("roster panel must be available");
  }
  var characters = payload.characters;
  if (!Array.isArray(characters)) {
    throw new Error("roster characters must be a list");
  }
  if (characters.length > ROSTER_MAX_ROWS) {
    throw new Error(
      "roster characters must hold at most " + ROSTER_MAX_ROWS + " entries"
    );
  }
  var lastIdentity = 0;
  var normalizedCharacters = [];
  var currentCount = 0;
  for (var i = 0; i < characters.length; i++) {
    var row = validateRosterCharacter(characters[i], i + 1);
    if (row.identity <= lastIdentity) {
      throw new Error("roster character identities must be strictly ascending");
    }
    lastIdentity = row.identity;
    if (row.current) {
      currentCount++;
    }
    normalizedCharacters.push(row);
  }
  if (currentCount !== 1) {
    throw new Error(
      "roster characters must contain exactly one current character, found " + currentCount
    );
  }
  var maxCharacters = requireInt(
    payload.max_characters,
    "max_characters",
    1,
    MAX_SAFE_INTEGER
  );
  var canCreate = requireBool(payload.can_create, "can_create");
  var switchLocked = requireBool(payload.switch_locked, "switch_locked");
  var lockReason = payload.lock_reason;
  if (switchLocked) {
    if (lockReason !== ROSTER_LOCK_REASON) {
      throw new Error(
        "lock_reason must be '" + ROSTER_LOCK_REASON + "' when switch_locked is true"
      );
    }
  } else {
    if (lockReason !== null) {
      throw new Error("lock_reason must be null when switch_locked is false");
    }
  }
  var result = {
    schema_version: ROSTER_SCHEMA_VERSION,
    available: true,
    characters: normalizedCharacters,
    max_characters: maxCharacters,
    can_create: canCreate,
    switch_locked: switchLocked,
    lock_reason: lockReason,
  };
  if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
    throw new Error("roster payload exceeds the OOB envelope limit");
  }
  return result;
}

module.exports = {
  validatePartyPanel: validatePartyPanel,
  validateObjectivesPanel: validateObjectivesPanel,
  validateQuestLogPanel: validateQuestLogPanel,
  validateDialoguePanel: validateDialoguePanel,
  validateRosterPanel: validateRosterPanel,
  PARTY_SCHEMA_VERSION: PARTY_SCHEMA_VERSION,
  PARTY_MAX_ROWS: PARTY_MAX_ROWS,
  PARTY_MAX_DISPLAY_NAME: PARTY_MAX_DISPLAY_NAME,
  OBJECTIVES_SCHEMA_VERSION: OBJECTIVES_SCHEMA_VERSION,
  OBJECTIVES_MAX_ROWS: OBJECTIVES_MAX_ROWS,
  QUEST_LOG_SCHEMA_VERSION: QUEST_LOG_SCHEMA_VERSION,
  QUEST_LOG_MAX_ROWS: QUEST_LOG_MAX_ROWS,
  DIALOGUE_SCHEMA_VERSION: DIALOGUE_SCHEMA_VERSION,
  DIALOGUE_MAX_CHOICES: DIALOGUE_MAX_CHOICES,
  ROSTER_SCHEMA_VERSION: ROSTER_SCHEMA_VERSION,
  ROSTER_MAX_ROWS: ROSTER_MAX_ROWS,
  ROSTER_MAX_NAME: ROSTER_MAX_NAME,
  ROSTER_LOCK_REASON: ROSTER_LOCK_REASON,
};
