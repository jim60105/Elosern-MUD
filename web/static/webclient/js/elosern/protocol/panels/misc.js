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
var PARTY_GENERAL_LIMIT = C.PARTY_GENERAL_LIMIT;
var PARTY_MAX_SLOTS = C.PARTY_MAX_SLOTS;
var PARTY_MAX_ROWS = C.PARTY_MAX_ROWS;
var PARTY_MAX_COMMISSION_LABEL = C.PARTY_MAX_COMMISSION_LABEL;
var PARTY_MAX_DISPLAY_NAME = C.PARTY_MAX_DISPLAY_NAME;
var PARTY_MEMBER_SCHEMA_VERSION = C.PARTY_MEMBER_SCHEMA_VERSION;
var PARTY_MEMBER_MAX_BOND_STAGE = C.PARTY_MEMBER_MAX_BOND_STAGE;
var PARTY_MEMBER_MAX_REASON = C.PARTY_MEMBER_MAX_REASON;
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
var ROSTER_LOCK_REASON = C.ROSTER_LOCK_REASON;
var artwork = require("../artwork.js");
var validateArtwork = artwork.validateArtwork;
var personaSections = require("../persona_sections.js");
var validatePersona = personaSections.validatePersona;
var validateIntimate = personaSections.validateIntimate;
var questLog = require("./quest_log.js");
var validateQuestLogPanel = questLog.validateQuestLogPanel;

function validateCommissionRef(value, name) {
  requireExactFields(value, name, ["quest_id", "role_id", "label"], []);
  function bounded(field) {
    var text = requireString(value[field], field, PARTY_MAX_COMMISSION_LABEL);
    if (text.length === 0 || hasLoneSurrogate(text)) {
      throw new Error(name + " " + field + " must be non-empty");
    }
    return text;
  }
  return { quest_id: bounded("quest_id"), role_id: bounded("role_id"), label: bounded("label") };
}

function validatePartyMembership(value, name) {
  requireExactFields(value, name, ["general", "temporary_commissions"], []);
  var general = requireBool(value.general, "general");
  if (!Array.isArray(value.temporary_commissions)) {
    throw new Error(name + " temporary_commissions must be a list");
  }
  var commissions = [];
  var seen = {};
  for (var i = 0; i < value.temporary_commissions.length; i++) {
    var ref = validateCommissionRef(value.temporary_commissions[i], name + " commission " + (i + 1));
    var key = ref.quest_id + "\u0000" + ref.role_id;
    if (Object.prototype.hasOwnProperty.call(seen, key)) {
      throw new Error(name + " temporary commission references must be unique");
    }
    seen[key] = true;
    commissions.push(ref);
  }
  return { general: general, temporary_commissions: commissions };
}

function validatePartySlot(value, index) {
  var name = "party slot " + index;
  requireExactFields(
    value,
    name,
    [
      "identity", "display_name", "portrait_ref",
      "hp_current", "hp_maximum", "mp_current", "mp_maximum", "sp_current", "sp_maximum",
      "role", "knocked_out", "unread", "bond_stage", "membership",
    ],
    []
  );
  var identity = requireInt(value.identity, "identity", 1, MAX_SAFE_INTEGER);
  var displayName = requireString(value.display_name, "display_name", PARTY_MAX_DISPLAY_NAME);
  if (displayName.length === 0 || hasLoneSurrogate(displayName)) {
    throw new Error("slot display_name must be non-empty");
  }
  var portraitRef = value.portrait_ref;
  if (portraitRef !== null && (
    typeof portraitRef !== "string" || portraitRef.length > 32 || !/^[0-9]+$/.test(portraitRef)
  )) {
    throw new Error("portrait_ref must be a bounded decimal string or null");
  }
  // Bounds only — zero is legal and the current/maximum ordering is trait
  // truth, exactly like the Python mirror.
  function gauge(key) {
    return [
      requireInt(value[key + "_current"], key + "_current", 0, MAX_SAFE_INTEGER),
      requireInt(value[key + "_maximum"], key + "_maximum", 0, MAX_SAFE_INTEGER),
    ];
  }
  var hp = gauge("hp");
  var mp = gauge("mp");
  var sp = gauge("sp");
  var role = value.role;
  if (role !== "commander" && role !== "companion") {
    throw new Error("role must be commander or companion");
  }
  var knockedOut = requireBool(value.knocked_out, "knocked_out");
  var unread = requireBool(value.unread, "unread");
  var bondStage = null;
  var membership = null;
  if (role === "commander") {
    // The commander row is the player's own: no bond stage, no party
    // membership, and never knocked out.
    if (value.bond_stage !== null) {
      throw new Error("the commander row carries no bond_stage");
    }
    if (value.membership !== null) {
      throw new Error("the commander row carries no membership");
    }
    if (knockedOut) {
      throw new Error("the commander row is never knocked out");
    }
  } else {
    bondStage = requireString(value.bond_stage, "bond_stage", PARTY_MAX_DISPLAY_NAME);
    if (bondStage.length === 0 || hasLoneSurrogate(bondStage)) {
      throw new Error("slot bond_stage must be a non-empty stage name");
    }
    membership = validatePartyMembership(value.membership, name + " membership");
  }
  return {
    identity: identity,
    display_name: displayName,
    portrait_ref: portraitRef,
    hp_current: hp[0],
    hp_maximum: hp[1],
    mp_current: mp[0],
    mp_maximum: mp[1],
    sp_current: sp[0],
    sp_maximum: sp[1],
    role: role,
    knocked_out: knockedOut,
    unread: unread,
    bond_stage: bondStage,
    membership: membership,
  };
}

function validatePartyPanel(payload) {
  requireExactFields(
    payload,
    "party panel",
    ["schema_version", "available", "slots", "general_quota", "viewed_member_id"],
    []
  );
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
  // Exactly one commander row, and it is row 0 (the rail's own ordering).
  var commanders = [];
  for (var c = 0; c < normalized.length; c++) {
    if (normalized[c].role === "commander") {
      commanders.push(c);
    }
  }
  if (commanders.length !== 1 || commanders[0] !== 0) {
    throw new Error("the party panel carries exactly one commander row, first");
  }
  var quota = payload.general_quota;
  requireExactFields(quota, "general quota", ["used", "limit"], []);
  var used = requireInt(quota.used, "used", 0, MAX_SAFE_INTEGER);
  var limit = requireInt(quota.limit, "limit", 0, MAX_SAFE_INTEGER);
  if (used > limit) {
    throw new Error("general quota used exceeds the limit");
  }
  var viewedMemberId = requireInt(
    payload.viewed_member_id, "viewed_member_id", 1, MAX_SAFE_INTEGER
  );
  if (!Object.prototype.hasOwnProperty.call(seen, viewedMemberId)) {
    throw new Error("viewed_member_id must name a presented row");
  }
  var result = {
    schema_version: PARTY_SCHEMA_VERSION,
    available: true,
    general_quota: { used: used, limit: limit },
    slots: normalized,
    viewed_member_id: viewedMemberId,
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
// webclient-align-10; schema version 2 adds the host's opaque art catalog
// key — dialogue-panel-host-portrait). Available form is exactly
// schema_version, available, kind, host (party-row triple whose portrait_ref
// is a nullable decimal catalog key, the combat participant vocabulary),
// bond_stage (a stage NAME or null — never a number), a bounded line, and at
// most DIALOGUE_MAX_CHOICES choices. Every string rejects lone surrogates.
function validateDialoguePanel(payload) {
  if (payload && payload.schema_version !== DIALOGUE_SCHEMA_VERSION) {
    throw new Error("unsupported dialogue schema_version");
  }
  requireExactFields(
    payload,
    "dialogue panel",
    [
      "schema_version",
      "available",
      "kind",
      "host",
      "actor",
      "bond_stage",
      "context_id",
      "delivery",
      "choices",
      "pure_chain",
      "reading_revision",
      "completed_topic_ids",
      "unlock_batch",
    ],
    []
  );
  if (payload.available !== true) {
    throw new Error("dialogue panel must be available");
  }
  if (payload.kind !== "dialogue") {
    throw new Error("dialogue kind must be dialogue");
  }

  function validateEntity(entity, role) {
    requireExactFields(entity, "dialogue " + role, ["identity", "display_name", "portrait_ref"], []);
    requireInt(entity.identity, "identity", 1, MAX_SAFE_INTEGER);
    var name = requireString(entity.display_name, "display_name", PARTY_MAX_DISPLAY_NAME);
    if (!name.trim() || hasLoneSurrogate(name)) {
      throw new Error(role + " display_name must be non-empty");
    }
    var portraitRef = entity.portrait_ref;
    if (portraitRef !== null) {
      if (typeof portraitRef !== "string" || !/^[0-9]+$/.test(portraitRef)) {
        throw new Error("portrait_ref must be an opaque decimal catalog key or null");
      }
      if (portraitRef.length > 32) {
        throw new Error("portrait_ref exceeds its bound");
      }
    }
  }

  validateEntity(payload.host, "host");
  validateEntity(payload.actor, "actor");

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

  var contextId = requireString(payload.context_id, "context_id", 64);
  if (!contextId.trim() || hasLoneSurrogate(contextId)) {
    throw new Error("dialogue context_id must be non-empty");
  }

  if (payload.delivery !== null) {
    var deliv = payload.delivery;
    requireExactFields(
      deliv,
      "dialogue delivery",
      ["delivery_id", "context_id", "topic_id", "scene_id", "scene_revision", "phase_revision", "kind", "lines"],
      []
    );
    requireString(deliv.delivery_id, "delivery_id", 64);
    requireString(deliv.context_id, "context_id", 64);
    if (deliv.topic_id !== null) {
      requireString(deliv.topic_id, "topic_id", 2048);
    }
    requireString(deliv.scene_id, "scene_id", 2048);
    requireString(deliv.scene_revision, "scene_revision", 64);
    if (deliv.kind !== "formal" && deliv.kind !== "refusal" && deliv.kind !== "opening" && deliv.kind !== "service") {
      throw new Error("invalid delivery kind");
    }
    if (!Array.isArray(deliv.lines)) {
      throw new Error("delivery lines must be an array");
    }
    for (var li = 0; li < deliv.lines.length; li++) {
      var line = deliv.lines[li];
      if (line.kind === "speech") {
        requireExactFields(line, "speech line", ["kind", "speaker", "text"], []);
        if (line.speaker !== "actor" && line.speaker !== "host") {
          throw new Error("speech speaker must be actor or host");
        }
        var stext = requireString(line.text, "text", 2000);
        if (!stext.trim() || hasLoneSurrogate(stext)) throw new Error("speech text must be non-empty");
      } else if (line.kind === "narration") {
        requireExactFields(line, "narration line", ["kind", "text"], []);
        var ntext = requireString(line.text, "text", 2000);
        if (!ntext.trim() || hasLoneSurrogate(ntext)) throw new Error("narration text must be non-empty");
      } else {
        throw new Error("unknown line kind");
      }
    }
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
  var seenTopics = Object.create(null);
  for (var i = 0; i < choices.length; i++) {
    var choice = choices[i];
    var name = "dialogue choice " + (i + 1);
    requireExactFields(
      choice,
      name,
      ["topic_id", "keyword_id", "label", "availability", "requirement_hint", "unread", "predecessors", "action_payload"],
      []
    );
    var topicId = requireString(choice.topic_id, "topic_id", 2048);
    if (!topicId.trim() || hasLoneSurrogate(topicId)) {
      throw new Error(name + " topic_id must be non-empty");
    }
    if (Object.prototype.hasOwnProperty.call(seenTopics, topicId)) {
      throw new Error("dialogue choice topic ids must be unique");
    }
    seenTopics[topicId] = true;

    var keywordId = requireString(choice.keyword_id, "keyword_id", DIALOGUE_MAX_KEYWORD_ID);
    if (!keywordId.trim() || hasLoneSurrogate(keywordId)) {
      throw new Error(name + " keyword_id must be non-empty");
    }
    var label = requireString(choice.label, "label", DIALOGUE_MAX_KEYWORD_LABEL);
    if (!label.trim() || hasLoneSurrogate(label)) {
      throw new Error(name + " label must be non-empty");
    }
    if (choice.availability !== "open" && choice.availability !== "locked" && choice.availability !== "hidden") {
      throw new Error(name + " availability invalid");
    }
    requireBool(choice.unread, "unread");
    if (!Array.isArray(choice.predecessors)) {
      throw new Error(name + " predecessors must be an array");
    }
    requireExactFields(choice.action_payload, "action_payload", ["npc_id", "topic_id", "context_id"], []);
    requireInt(choice.action_payload.npc_id, "npc_id", 1, MAX_SAFE_INTEGER);
    requireString(choice.action_payload.topic_id, "topic_id", 2048);
    if (choice.action_payload.context_id !== null) {
      requireString(choice.action_payload.context_id, "context_id", 64);
    }
  }

  if (!Array.isArray(payload.pure_chain) || payload.pure_chain.length > 15) {
    throw new Error("pure_chain must be a list of at most 15 entries");
  }
  requireInt(payload.reading_revision, "reading_revision", 0, MAX_SAFE_INTEGER);
  if (!Array.isArray(payload.completed_topic_ids) || payload.completed_topic_ids.length > 16) {
    throw new Error("completed_topic_ids must be a list of at most 16 entries");
  }
  if (payload.unlock_batch !== null) {
    requireExactFields(payload.unlock_batch, "unlock_batch", ["batch_id", "host_id", "context_id", "topic_ids"], []);
  }

  if (jsonByteSize(payload) > 24576) {
    throw new Error("dialogue payload exceeds 24576 bytes");
  }
  return payload;
}

// Exact available roster panel v3 schema (mirror of
// web.webclient.presentation.roster, webclient-character-roster): a row's
// portrait IS the complete canonical artwork descriptor, validated by the one
// shared mirror, so the roster and the art catalog cannot drift and a retired
// flat portrait object fails the exact-key check instead of being adapted.
function validateRosterPortrait(value) {
  return validateArtwork(value);
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

// party_member panel validator (mirror of
// web.webclient.presentation.party_member, party-member-panel): the viewed
// member's exact member-tab facts. Exactly one of the companion/commander
// sections is non-null; descriptors are server-authored and carry their
// verdict's bounded reason, never a client-inferred availability.
var PARTY_MEMBER_ACTION_POSSESS = "explore.possess";
var PARTY_MEMBER_ACTION_RELEASE = "explore.possess_release";
var PARTY_MEMBER_ACTION_LEAVE = "explore.party_leave";
var PARTY_MEMBER_ACTION_NPC_PERSONA = "npc.persona.read";
var PARTY_MEMBER_ACTION_COMMANDER_PERSONA = "character.persona.update";
var PARTY_MEMBER_COMPANION_ACTIONS = [
  PARTY_MEMBER_ACTION_POSSESS,
  PARTY_MEMBER_ACTION_LEAVE,
  PARTY_MEMBER_ACTION_NPC_PERSONA,
];
var PARTY_MEMBER_POSSESSION_ACTIONS = [
  PARTY_MEMBER_ACTION_POSSESS,
  PARTY_MEMBER_ACTION_RELEASE,
];
var PARTY_MEMBER_COMMANDER_ACTIONS = [PARTY_MEMBER_ACTION_COMMANDER_PERSONA];

function validatePartyMemberBond(value) {
  requireExactFields(value, "bond", ["stage", "step", "steps"], []);
  var stage = requireString(value.stage, "bond.stage", PARTY_MEMBER_MAX_BOND_STAGE);
  if (stage.trim().length === 0 || hasLoneSurrogate(stage)) {
    throw new Error("bond.stage must be non-empty");
  }
  var steps = requireInt(value.steps, "bond.steps", 1, MAX_SAFE_INTEGER);
  var step = requireInt(value.step, "bond.step", 1, steps);
  return { stage: stage, step: step, steps: steps };
}

function validatePartyMemberDescriptor(value, name, actionIds, params) {
  requireExactFields(value, name, ["action_id", "params", "enabled", "reason"], []);
  if (actionIds.indexOf(value.action_id) === -1) {
    throw new Error(name + " action_id must be one of " + actionIds.join(","));
  }
  requireExactFields(value.params, name + " params", Object.keys(params), []);
  Object.keys(params).forEach(function (field) {
    if (value.params[field] !== params[field]) {
      throw new Error(name + " params." + field + " must name the viewed member");
    }
  });
  var enabled = requireBool(value.enabled, name + " enabled");
  var reason = value.reason;
  if (reason !== null) {
    reason = requireString(reason, name + " reason", PARTY_MEMBER_MAX_REASON);
    if (reason.trim().length === 0 || hasLoneSurrogate(reason)) {
      throw new Error(name + " reason must be non-empty when set");
    }
  }
  if (enabled && reason !== null) {
    throw new Error("an enabled descriptor carries no reason");
  }
  if (!enabled && reason === null) {
    throw new Error("a disabled descriptor carries its reason");
  }
  return {
    action_id: value.action_id,
    params: params,
    enabled: enabled,
    reason: reason,
  };
}

function validatePartyMemberActions(value, memberId, order) {
  if (!Array.isArray(value) || value.length !== order.length) {
    throw new Error("actions must hold exactly " + order.length + " descriptors");
  }
  var descriptors = [];
  for (var i = 0; i < order.length; i++) {
    var actionId = order[i];
    var params =
      actionId === PARTY_MEMBER_ACTION_COMMANDER_PERSONA
        ? {}
        : { npc_id: memberId };
    var actionIds =
      actionId === PARTY_MEMBER_ACTION_POSSESS
        ? PARTY_MEMBER_POSSESSION_ACTIONS
        : [actionId];
    descriptors.push(
      validatePartyMemberDescriptor(
        value[i],
        "party_member action " + (i + 1),
        actionIds,
        params
      )
    );
  }
  return descriptors;
}

function validatePartyMemberCompanion(value, memberId) {
  requireExactFields(
    value,
    "companion",
    ["bond", "membership", "intimate", "actions"],
    []
  );
  var bond = validatePartyMemberBond(value.bond);
  var membership = validatePartyMembership(value.membership, "companion membership");
  var intimate = validateIntimate(value.intimate);
  var actions = validatePartyMemberActions(
    value.actions,
    memberId,
    PARTY_MEMBER_COMPANION_ACTIONS
  );
  return { bond: bond, membership: membership, intimate: intimate, actions: actions };
}

function validatePartyMemberCommander(value, memberId) {
  requireExactFields(value, "commander", ["persona", "intimate", "actions"], []);
  var persona = validatePersona(value.persona);
  var intimate = validateIntimate(value.intimate);
  var actions = validatePartyMemberActions(
    value.actions,
    memberId,
    PARTY_MEMBER_COMMANDER_ACTIONS
  );
  return { persona: persona, intimate: intimate, actions: actions };
}

function validatePartyMemberPanel(payload) {
  requireExactFields(
    payload,
    "party_member panel",
    ["schema_version", "available", "kind", "member_id", "role", "companion", "commander"],
    []
  );
  requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
  if (payload.schema_version !== PARTY_MEMBER_SCHEMA_VERSION) {
    throw new Error("unsupported party_member schema_version");
  }
  if (payload.available !== true) {
    throw new Error("party_member panel must be available");
  }
  if (payload.kind !== "party_member") {
    throw new Error("kind must be 'party_member'");
  }
  var memberId = requireInt(payload.member_id, "member_id", 1, MAX_SAFE_INTEGER);
  var role = payload.role;
  if (role !== "commander" && role !== "companion") {
    throw new Error("role must be commander or companion");
  }
  var companion = null;
  var commander = null;
  if (role === "commander") {
    if (payload.companion !== null) {
      throw new Error("a commander panel carries no companion section");
    }
    if (payload.commander === null) {
      throw new Error("a commander panel requires its section");
    }
    commander = validatePartyMemberCommander(payload.commander, memberId);
  } else {
    if (payload.commander !== null) {
      throw new Error("a companion panel carries no commander section");
    }
    if (payload.companion === null) {
      throw new Error("a companion panel requires its section");
    }
    companion = validatePartyMemberCompanion(payload.companion, memberId);
  }
  var result = {
    schema_version: PARTY_MEMBER_SCHEMA_VERSION,
    available: true,
    kind: "party_member",
    member_id: memberId,
    role: role,
    companion: companion,
    commander: commander,
  };
  if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
    throw new Error("party_member payload exceeds the OOB envelope limit");
  }
  return result;
}

module.exports = {
  validatePartyPanel: validatePartyPanel,
  validatePartyMemberPanel: validatePartyMemberPanel,
  validateObjectivesPanel: validateObjectivesPanel,
  validateQuestLogPanel: validateQuestLogPanel,
  validateDialoguePanel: validateDialoguePanel,
  validateRosterPanel: validateRosterPanel,
  PARTY_SCHEMA_VERSION: PARTY_SCHEMA_VERSION,
  PARTY_MEMBER_SCHEMA_VERSION: PARTY_MEMBER_SCHEMA_VERSION,
  PARTY_GENERAL_LIMIT: PARTY_GENERAL_LIMIT,
  PARTY_MAX_SLOTS: PARTY_MAX_SLOTS,
  PARTY_MAX_ROWS: PARTY_MAX_ROWS,
  PARTY_MAX_COMMISSION_LABEL: PARTY_MAX_COMMISSION_LABEL,
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
