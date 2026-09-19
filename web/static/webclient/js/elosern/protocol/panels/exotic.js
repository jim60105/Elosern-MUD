"use strict";

var C = require("../constants.js");
var core = require("../core.js");

var codePoints = core.codePoints;
var jsonByteSize = core.jsonByteSize;
var requireExactFields = core.requireExactFields;
var requireInt = core.requireInt;
var requireBool = core.requireBool;
var requireString = core.requireString;
var validateIdentifier = core.validateIdentifier;
var hasLoneSurrogate = core.hasLoneSurrogate;

var MAX_SAFE_INTEGER = C.MAX_SAFE_INTEGER;
var MAX_CANONICAL_JSON_BYTES = C.MAX_CANONICAL_JSON_BYTES;
var LORE_CODEX_SCHEMA_VERSION = C.LORE_CODEX_SCHEMA_VERSION;
var LORE_CODEX_MAX_ENTRIES_PER_CATEGORY = C.LORE_CODEX_MAX_ENTRIES_PER_CATEGORY;
var LORE_CODEX_MAX_TOTAL_ENTRIES = C.LORE_CODEX_MAX_TOTAL_ENTRIES;
var LORE_CODEX_MAX_CARD_FIELDS = C.LORE_CODEX_MAX_CARD_FIELDS;
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
// lore_codex panel validator (mirror of web.webclient.presentation.lore_codex,
// webclient-lore-codex-panel). Shared bounds are guarded by a dual-direction
// parity test.
// ---------------------------------------------------------------------------

function validateLoreCodexCardField(value, index) {
  var label = "card field[" + index + "]";
  requireExactFields(value, label, ["name", "value"], []);
  var name = requireString(
    value.name,
    label + " name",
    LORE_CODEX_MAX_FIELD_NAME_CODE_POINTS
  );
  if (!name.trim()) {
    throw new Error(label + " name must be non-empty");
  }
  if (hasLoneSurrogate(name)) {
    throw new Error(label + " name contains an unpaired surrogate code point");
  }
  var val = requireString(
    value.value,
    label + " value",
    LORE_CODEX_MAX_FIELD_VALUE_CODE_POINTS
  );
  if (hasLoneSurrogate(val)) {
    throw new Error(label + " value contains an unpaired surrogate code point");
  }
  return { name: name, value: val };
}

function validateLoreCodexEntry(value, index) {
  var label = "lore codex entry[" + index + "]";
  requireExactFields(value, label, ["key", "title", "card"], []);
  var rawKey = validateIdentifier(value.key, label + " key");
  if (codePoints(rawKey) > LORE_CODEX_MAX_KEY_CODE_POINTS) {
    throw new Error(label + " key exceeds its bound");
  }
  if (hasLoneSurrogate(rawKey)) {
    throw new Error(label + " key contains an unpaired surrogate code point");
  }
  var title = requireString(
    value.title,
    label + " title",
    LORE_CODEX_MAX_TITLE_CODE_POINTS
  );
  if (!title.trim()) {
    throw new Error(label + " title must be non-empty");
  }
  if (hasLoneSurrogate(title)) {
    throw new Error(label + " title contains an unpaired surrogate code point");
  }
  if (!Array.isArray(value.card)) {
    throw new Error(label + " card must be a list");
  }
  if (value.card.length > LORE_CODEX_MAX_CARD_FIELDS) {
    throw new Error(
      label + " card must hold at most " + LORE_CODEX_MAX_CARD_FIELDS + " fields"
    );
  }
  var validatedCard = [];
  for (var i = 0; i < value.card.length; i++) {
    validatedCard.push(validateLoreCodexCardField(value.card[i], i));
  }
  return { key: rawKey, title: title, card: validatedCard };
}

function validateLoreCodexCategory(value, index, expectedKey) {
  var label = "category group[" + index + "]";
  requireExactFields(value, label, ["key", "label", "count", "entries"], []);
  var key = requireString(value.key, label + " key");
  if (key !== expectedKey) {
    throw new Error(
      label + " key must be '" + expectedKey + "', got '" + key + "'"
    );
  }
  var catLabel = requireString(
    value.label,
    label + " label",
    LORE_CODEX_MAX_LABEL_CODE_POINTS
  );
  if (!catLabel.trim()) {
    throw new Error(label + " label must be non-empty");
  }
  if (hasLoneSurrogate(catLabel)) {
    throw new Error(label + " label contains an unpaired surrogate code point");
  }
  if (!Array.isArray(value.entries)) {
    throw new Error(label + " entries must be a list");
  }
  if (value.entries.length > LORE_CODEX_MAX_ENTRIES_PER_CATEGORY) {
    throw new Error(
      label +
        " entries must hold at most " +
        LORE_CODEX_MAX_ENTRIES_PER_CATEGORY +
        " items"
    );
  }
  var count = requireInt(value.count, label + " count", 0, MAX_SAFE_INTEGER);
  if (count !== value.entries.length) {
    throw new Error(
      label +
        " count (" +
        count +
        ") does not match entries length (" +
        value.entries.length +
        ")"
    );
  }
  var validatedEntries = [];
  for (var e = 0; e < value.entries.length; e++) {
    validatedEntries.push(validateLoreCodexEntry(value.entries[e], e));
  }
  return {
    key: key,
    label: catLabel,
    count: count,
    entries: validatedEntries,
  };
}

function validateLoreCodexPanel(payload) {
  requireExactFields(
    payload,
    "lore_codex panel",
    ["schema_version", "available", "categories", "discovered_total"],
    []
  );
  if (payload.schema_version !== LORE_CODEX_SCHEMA_VERSION) {
    throw new Error("unsupported lore_codex schema_version");
  }
  if (payload.available !== true) {
    throw new Error("available must be true for the codex form");
  }
  if (
    !Array.isArray(payload.categories) ||
    payload.categories.length !== LORE_CODEX_CATEGORIES.length
  ) {
    throw new Error(
      "categories must be a list of exactly " +
        LORE_CODEX_CATEGORIES.length +
        " groups"
    );
  }
  var validatedCategories = [];
  var expectedTotal = 0;
  for (var c = 0; c < payload.categories.length; c++) {
    var group = validateLoreCodexCategory(
      payload.categories[c],
      c,
      LORE_CODEX_CATEGORIES[c]
    );
    validatedCategories.push(group);
    expectedTotal += group.count;
  }
  var discoveredTotal = requireInt(
    payload.discovered_total,
    "discovered_total",
    0,
    MAX_SAFE_INTEGER
  );
  if (discoveredTotal !== expectedTotal) {
    throw new Error(
      "discovered_total (" +
        discoveredTotal +
        ") does not equal sum of group counts (" +
        expectedTotal +
        ")"
    );
  }
  if (discoveredTotal > LORE_CODEX_MAX_TOTAL_ENTRIES) {
    throw new Error(
      "discovered_total exceeds the maximum of " + LORE_CODEX_MAX_TOTAL_ENTRIES
    );
  }
  var result = {
    schema_version: LORE_CODEX_SCHEMA_VERSION,
    available: true,
    categories: validatedCategories,
    discovered_total: discoveredTotal,
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
  LORE_CODEX_MAX_ENTRIES_PER_CATEGORY: LORE_CODEX_MAX_ENTRIES_PER_CATEGORY,
  LORE_CODEX_MAX_TOTAL_ENTRIES: LORE_CODEX_MAX_TOTAL_ENTRIES,
  LORE_CODEX_MAX_CARD_FIELDS: LORE_CODEX_MAX_CARD_FIELDS,
  LORE_CODEX_MAX_KEY_CODE_POINTS: LORE_CODEX_MAX_KEY_CODE_POINTS,
  LORE_CODEX_MAX_TITLE_CODE_POINTS: LORE_CODEX_MAX_TITLE_CODE_POINTS,
  LORE_CODEX_MAX_LABEL_CODE_POINTS: LORE_CODEX_MAX_LABEL_CODE_POINTS,
  LORE_CODEX_MAX_FIELD_NAME_CODE_POINTS: LORE_CODEX_MAX_FIELD_NAME_CODE_POINTS,
  LORE_CODEX_MAX_FIELD_VALUE_CODE_POINTS: LORE_CODEX_MAX_FIELD_VALUE_CODE_POINTS,
};
