"use strict";

var C = require("../constants.js");
var core = require("../core.js");
var artwork = require("../artwork.js");

var jsonByteSize = core.jsonByteSize;
var requireExactFields = core.requireExactFields;
var requireInt = core.requireInt;
var requireBool = core.requireBool;
var requireString = core.requireString;
var hasLoneSurrogate = core.hasLoneSurrogate;
var validateArtwork = artwork.validateArtwork;

var MAX_SAFE_INTEGER = C.MAX_SAFE_INTEGER;
var MAX_CANONICAL_JSON_BYTES = C.MAX_CANONICAL_JSON_BYTES;
var LORE_CODEX_SCHEMA_VERSION = C.LORE_CODEX_SCHEMA_VERSION;
var LORE_CODEX_MAX_SLOTS_PER_CATEGORY = C.LORE_CODEX_MAX_SLOTS_PER_CATEGORY;
var LORE_CODEX_MAX_TOTAL_SLOTS = C.LORE_CODEX_MAX_TOTAL_SLOTS;
var LORE_CODEX_MAX_GROUPS_PER_CATEGORY = C.LORE_CODEX_MAX_GROUPS_PER_CATEGORY;
var LORE_CODEX_MAX_CARD_FIELDS = C.LORE_CODEX_MAX_CARD_FIELDS;
var LORE_CODEX_MAX_VARIANT_LINES = C.LORE_CODEX_MAX_VARIANT_LINES;
var LORE_CODEX_MAX_KEY_CODE_POINTS = C.LORE_CODEX_MAX_KEY_CODE_POINTS;
var LORE_CODEX_MAX_TITLE_CODE_POINTS = C.LORE_CODEX_MAX_TITLE_CODE_POINTS;
var LORE_CODEX_MAX_LABEL_CODE_POINTS = C.LORE_CODEX_MAX_LABEL_CODE_POINTS;
var LORE_CODEX_MAX_FIELD_NAME_CODE_POINTS = C.LORE_CODEX_MAX_FIELD_NAME_CODE_POINTS;
var LORE_CODEX_MAX_FIELD_VALUE_CODE_POINTS = C.LORE_CODEX_MAX_FIELD_VALUE_CODE_POINTS;
var LORE_CODEX_CATEGORIES = C.LORE_CODEX_CATEGORIES;

// ---------------------------------------------------------------------------
// possession_banner panel v1 (mirror of web.webclient.presentation.possession_banner)
// ---------------------------------------------------------------------------

var POSSESSION_BANNER_SCHEMA_VERSION = 1;
var POSSESSION_BANNER_MAX_HOST_NAME = 64;

function validatePossessionBannerPanel(payload) {
  if (!payload || typeof payload !== "object") {
    throw new Error("possession_banner panel must be an object");
  }
  requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
  if (payload.schema_version !== POSSESSION_BANNER_SCHEMA_VERSION) {
    throw new Error("unsupported possession_banner schema_version");
  }
  requireBool(payload.available, "available");
  if (payload.available !== true) {
    throw new Error("possession_banner panel must be available");
  }
  requireExactFields(payload, "possession_banner", ["schema_version", "available", "host_name", "since_tick"], []);
  var hostName = requireString(payload.host_name, "host_name", POSSESSION_BANNER_MAX_HOST_NAME);
  var sinceTick = requireInt(payload.since_tick, "since_tick", 0, MAX_SAFE_INTEGER);
  return {
    schema_version: POSSESSION_BANNER_SCHEMA_VERSION,
    available: true,
    host_name: hostName,
    since_tick: sinceTick,
  };
}

// ---------------------------------------------------------------------------
// lore_codex panel v2 validator (mirror of web.webclient.presentation.lore_codex,
// webclient-lore-codex-panel). Shared bounds are guarded by a dual-direction
// parity test. A slot is either exactly {placeholder: true} (an undiscovered
// entry discloses only its count and position) or an entry slot.
// ---------------------------------------------------------------------------

var LORE_CODEX_MONSTER_CATEGORY = "monster";
var LORE_CODEX_SPECIES_STAGES = ["sighted", "defeated"];
var LORE_CODEX_VARIANTS_FIELD = "variants";

function rejectLoreLoneSurrogate(value, field) {
  if (hasLoneSurrogate(value)) {
    throw new Error(field + " contains an unpaired surrogate code point");
  }
  return value;
}

function validateLoreCodexKey(value, field) {
  // Registry keys are opaque domain identities, not protocol action identifiers.
  var key = requireString(value, field, LORE_CODEX_MAX_KEY_CODE_POINTS);
  if (!key || key.indexOf(":") !== -1) {
    throw new Error(field + " must be non-empty and contain no colon");
  }
  return rejectLoreLoneSurrogate(key, field);
}

function validateLoreCodexLabel(value, field) {
  var text = requireString(value, field, LORE_CODEX_MAX_LABEL_CODE_POINTS);
  if (!text.trim()) {
    throw new Error(field + " must be non-empty");
  }
  return rejectLoreLoneSurrogate(text, field);
}

function validateLoreCodexCardField(value, index) {
  var label = "card field[" + index + "]";
  requireExactFields(value, label, ["name", "value"], []);
  var name = requireString(value.name, label + " name", LORE_CODEX_MAX_FIELD_NAME_CODE_POINTS);
  if (!name.trim()) {
    throw new Error(label + " name must be non-empty");
  }
  rejectLoreLoneSurrogate(name, label + " name");
  var val = requireString(value.value, label + " value", LORE_CODEX_MAX_FIELD_VALUE_CODE_POINTS);
  rejectLoreLoneSurrogate(val, label + " value");
  if (name === LORE_CODEX_VARIANTS_FIELD && val.split("\n").length > LORE_CODEX_MAX_VARIANT_LINES) {
    throw new Error(
      label + " variants must hold at most " + LORE_CODEX_MAX_VARIANT_LINES + " lines"
    );
  }
  return { name: name, value: val };
}

function validateLoreCodexLockedFields(value, label, cardNames) {
  if (!Array.isArray(value)) {
    throw new Error(label + " locked_fields must be a list");
  }
  if (value.length > LORE_CODEX_MAX_CARD_FIELDS) {
    throw new Error(
      label + " locked_fields must hold at most " + LORE_CODEX_MAX_CARD_FIELDS + " items"
    );
  }
  var locked = [];
  for (var i = 0; i < value.length; i++) {
    var field = label + " locked_fields[" + i + "]";
    var name = requireString(value[i], field, LORE_CODEX_MAX_FIELD_NAME_CODE_POINTS);
    if (!name.trim()) {
      throw new Error(field + " must be non-empty");
    }
    rejectLoreLoneSurrogate(name, field);
    if (locked.indexOf(name) !== -1) {
      throw new Error(field + " duplicates '" + name + "'");
    }
    if (cardNames.indexOf(name) !== -1) {
      throw new Error(field + " '" + name + "' is also a card field");
    }
    locked.push(name);
  }
  return locked;
}

function validateLoreCodexEntrySlot(value, label, monster) {
  requireExactFields(value, label, ["key", "title", "stage", "art", "card", "locked_fields"], []);
  var key = validateLoreCodexKey(value.key, label + " key");
  var title = requireString(value.title, label + " title", LORE_CODEX_MAX_TITLE_CODE_POINTS);
  if (!title.trim()) {
    throw new Error(label + " title must be non-empty");
  }
  rejectLoreLoneSurrogate(title, label + " title");
  var stage = value.stage;
  if (monster) {
    if (LORE_CODEX_SPECIES_STAGES.indexOf(stage) === -1) {
      throw new Error(label + " stage must be sighted or defeated");
    }
  } else if (stage !== null) {
    throw new Error(label + " stage must be null outside the monster category");
  }
  var art = value.art === null ? null : validateArtwork(value.art);
  if (!Array.isArray(value.card)) {
    throw new Error(label + " card must be a list");
  }
  if (value.card.length > LORE_CODEX_MAX_CARD_FIELDS) {
    throw new Error(label + " card must hold at most " + LORE_CODEX_MAX_CARD_FIELDS + " fields");
  }
  var card = [];
  var cardNames = [];
  for (var i = 0; i < value.card.length; i++) {
    var field = validateLoreCodexCardField(value.card[i], i);
    if (cardNames.indexOf(field.name) !== -1) {
      throw new Error(label + " card field names must be unique");
    }
    cardNames.push(field.name);
    card.push(field);
  }
  var locked = validateLoreCodexLockedFields(value.locked_fields, label, cardNames);
  if (locked.length > 0 && stage !== "sighted") {
    throw new Error(label + " locked_fields must be empty unless the stage is sighted");
  }
  return { key: key, title: title, stage: stage, art: art, card: card, locked_fields: locked };
}

function validateLoreCodexSlot(value, label, monster) {
  if (value && typeof value === "object" && !Array.isArray(value) &&
      Object.prototype.hasOwnProperty.call(value, "placeholder")) {
    requireExactFields(value, label, ["placeholder"], []);
    if (value.placeholder !== true) {
      throw new Error(label + " placeholder must be true");
    }
    return { placeholder: true };
  }
  return validateLoreCodexEntrySlot(value, label, monster);
}

function validateLoreCodexGroup(value, label, monster) {
  requireExactFields(value, label, ["key", "label", "slots"], []);
  var key = validateLoreCodexKey(value.key, label + " key");
  var groupLabel = value.label;
  if (monster) {
    groupLabel = validateLoreCodexLabel(value.label, label + " label");
  } else if (groupLabel !== null) {
    throw new Error(label + " label must be null outside the monster category");
  }
  if (!Array.isArray(value.slots)) {
    throw new Error(label + " slots must be a list");
  }
  var slots = [];
  for (var i = 0; i < value.slots.length; i++) {
    slots.push(validateLoreCodexSlot(value.slots[i], label + " slot[" + i + "]", monster));
  }
  return { key: key, label: groupLabel, slots: slots };
}

function validateLoreCodexCategory(value, index, expectedKey) {
  var label = "category[" + index + "]";
  requireExactFields(value, label, ["key", "label", "discovered", "total", "groups"], []);
  var key = requireString(value.key, label + " key", LORE_CODEX_MAX_KEY_CODE_POINTS);
  if (key !== expectedKey) {
    throw new Error(label + " key must be '" + expectedKey + "', got '" + key + "'");
  }
  var monster = key === LORE_CODEX_MONSTER_CATEGORY;
  var categoryLabel = validateLoreCodexLabel(value.label, label + " label");
  if (!Array.isArray(value.groups)) {
    throw new Error(label + " groups must be a list");
  }
  if (monster) {
    if (value.groups.length > LORE_CODEX_MAX_GROUPS_PER_CATEGORY) {
      throw new Error(
        label + " groups must hold at most " + LORE_CODEX_MAX_GROUPS_PER_CATEGORY + " items"
      );
    }
  } else if (value.groups.length !== 1) {
    throw new Error(label + " must hold exactly one group");
  }
  var groups = [];
  var groupKeys = [];
  var entryKeys = [];
  var slotCount = 0;
  for (var g = 0; g < value.groups.length; g++) {
    var group = validateLoreCodexGroup(value.groups[g], label + " group[" + g + "]", monster);
    if (groupKeys.indexOf(group.key) !== -1) {
      throw new Error(label + " group keys must be unique");
    }
    groupKeys.push(group.key);
    for (var s = 0; s < group.slots.length; s++) {
      if (group.slots[s].placeholder !== true) {
        if (entryKeys.indexOf(group.slots[s].key) !== -1) {
          throw new Error(label + " entry keys must be unique");
        }
        entryKeys.push(group.slots[s].key);
      }
    }
    slotCount += group.slots.length;
    groups.push(group);
  }
  var total = requireInt(value.total, label + " total", 0, MAX_SAFE_INTEGER);
  if (total > LORE_CODEX_MAX_SLOTS_PER_CATEGORY) {
    throw new Error(label + " must hold at most " + LORE_CODEX_MAX_SLOTS_PER_CATEGORY + " slots");
  }
  if (slotCount > total) {
    throw new Error(label + " holds " + slotCount + " slots, more than its total (" + total + ")");
  }
  var discovered = requireInt(value.discovered, label + " discovered", 0, MAX_SAFE_INTEGER);
  if (discovered !== entryKeys.length) {
    throw new Error(
      label + " discovered (" + discovered + ") does not match its entry slots (" +
        entryKeys.length + ")"
    );
  }
  return {
    category: { key: key, label: categoryLabel, discovered: discovered, total: total, groups: groups },
    slotCount: slotCount,
  };
}

function validateLoreCodexPanel(payload) {
  requireExactFields(
    payload,
    "lore_codex panel",
    ["schema_version", "available", "discovered_total", "total", "categories"],
    []
  );
  if (payload.schema_version !== LORE_CODEX_SCHEMA_VERSION) {
    throw new Error("unsupported lore_codex schema_version");
  }
  requireBool(payload.available, "available");
  if (payload.available !== true) {
    throw new Error("available must be true for the codex form");
  }
  if (!Array.isArray(payload.categories) || payload.categories.length !== LORE_CODEX_CATEGORIES.length) {
    throw new Error(
      "categories must be a list of exactly " + LORE_CODEX_CATEGORIES.length + " categories"
    );
  }
  var categories = [];
  var expectedDiscovered = 0;
  var expectedTotal = 0;
  var slotCount = 0;
  for (var c = 0; c < payload.categories.length; c++) {
    var validated = validateLoreCodexCategory(payload.categories[c], c, LORE_CODEX_CATEGORIES[c]);
    categories.push(validated.category);
    expectedDiscovered += validated.category.discovered;
    expectedTotal += validated.category.total;
    slotCount += validated.slotCount;
  }
  var discoveredTotal = requireInt(payload.discovered_total, "discovered_total", 0, MAX_SAFE_INTEGER);
  if (discoveredTotal !== expectedDiscovered) {
    throw new Error(
      "discovered_total (" + discoveredTotal + ") does not equal the sum of category discovered counts (" +
        expectedDiscovered + ")"
    );
  }
  var total = requireInt(payload.total, "total", 0, MAX_SAFE_INTEGER);
  if (total !== expectedTotal) {
    throw new Error(
      "total (" + total + ") does not equal the sum of category totals (" + expectedTotal + ")"
    );
  }
  // The top-level total bounds the untrimmed slot count, and therefore the
  // shipped slot count as well (each category holds at most its total).
  if (total > LORE_CODEX_MAX_TOTAL_SLOTS || slotCount > LORE_CODEX_MAX_TOTAL_SLOTS) {
    throw new Error("the codex must hold at most " + LORE_CODEX_MAX_TOTAL_SLOTS + " slots in total");
  }
  var result = {
    schema_version: LORE_CODEX_SCHEMA_VERSION,
    available: true,
    discovered_total: discoveredTotal,
    total: total,
    categories: categories,
  };
  if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
    throw new Error("lore_codex payload exceeds the OOB envelope limit");
  }
  return result;
}

module.exports = {
  validatePossessionBannerPanel: validatePossessionBannerPanel,
  validateLoreCodexPanel: validateLoreCodexPanel,
  POSSESSION_BANNER_SCHEMA_VERSION: POSSESSION_BANNER_SCHEMA_VERSION,
  POSSESSION_BANNER_MAX_HOST_NAME: POSSESSION_BANNER_MAX_HOST_NAME,
  LORE_CODEX_SCHEMA_VERSION: LORE_CODEX_SCHEMA_VERSION,
  LORE_CODEX_MAX_SLOTS_PER_CATEGORY: LORE_CODEX_MAX_SLOTS_PER_CATEGORY,
  LORE_CODEX_MAX_TOTAL_SLOTS: LORE_CODEX_MAX_TOTAL_SLOTS,
  LORE_CODEX_MAX_GROUPS_PER_CATEGORY: LORE_CODEX_MAX_GROUPS_PER_CATEGORY,
  LORE_CODEX_MAX_CARD_FIELDS: LORE_CODEX_MAX_CARD_FIELDS,
  LORE_CODEX_MAX_VARIANT_LINES: LORE_CODEX_MAX_VARIANT_LINES,
  LORE_CODEX_MAX_KEY_CODE_POINTS: LORE_CODEX_MAX_KEY_CODE_POINTS,
  LORE_CODEX_MAX_TITLE_CODE_POINTS: LORE_CODEX_MAX_TITLE_CODE_POINTS,
  LORE_CODEX_MAX_LABEL_CODE_POINTS: LORE_CODEX_MAX_LABEL_CODE_POINTS,
  LORE_CODEX_MAX_FIELD_NAME_CODE_POINTS: LORE_CODEX_MAX_FIELD_NAME_CODE_POINTS,
  LORE_CODEX_MAX_FIELD_VALUE_CODE_POINTS: LORE_CODEX_MAX_FIELD_VALUE_CODE_POINTS,
};
