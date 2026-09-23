"use strict";

var C = require("../constants.js");
var core = require("../core.js");
var skillDescriptor = require("./skill_descriptor.js");

var requireNumber = skillDescriptor.requireNumber;
var validateFreeformScales = skillDescriptor.validateFreeformScales;
var isPlainObject = core.isPlainObject;
var codePoints = core.codePoints;
var jsonByteSize = core.jsonByteSize;
var requireExactFields = core.requireExactFields;
var requireInt = core.requireInt;
var requireBool = core.requireBool;
var requireString = core.requireString;
var validateIdentifier = core.validateIdentifier;

var CHARACTER_MAX_KEY = C.CHARACTER_MAX_KEY;
var MAX_SAFE_INTEGER = C.MAX_SAFE_INTEGER;
var MAX_CANONICAL_JSON_BYTES = C.MAX_CANONICAL_JSON_BYTES;
var MAX_FULL_TITLE_CODE_POINTS = C.MAX_FULL_TITLE_CODE_POINTS;
var MAX_COST_KEYS = C.MAX_COST_KEYS;
var TARGET_SPECS = C.TARGET_SPECS;

// ---------------------------------------------------------------------------
// character panel v1 validators (mirror of
// web.webclient.presentation.character, design D10). Shared bounds are
// guarded by a dual-direction parity test.
// ---------------------------------------------------------------------------

var CHARACTER_MAX_TRAIT_ROWS = 32;
var CHARACTER_MAX_ACTIVE_ROWS = 32;
var CHARACTER_MAX_PASSIVE_ROWS = 32;
var CHARACTER_MAX_EQUIPMENT_ROWS = 32;
var CHARACTER_MAX_DISPLAYED_ROWS = 32;
// The category-group count bound equals len(SkillCategory) plus one on the
// server: the extra slot is the synthetic "unknown" fallback group that
// holds keys absent from SKILL_REGISTRY.
var CHARACTER_MAX_CATEGORY_GROUPS = 8;
// CHARACTER_MAX_KEY is shared with the context_actions skill-group rows.
var CHARACTER_MAX_LABEL = 128;
var CHARACTER_MAX_DESCRIPTION = 256;
var CHARACTER_MAX_SLOT = 32;
// v5 breakdown bounds (mirror of web.webclient.presentation.character):
// the per-stat layer bound, the P3 adjustment-summary bound, and the
// closed source/kind alphabets.
var CHARACTER_MAX_LAYERS = 16;
var CHARACTER_MAX_ADJUSTMENT = CHARACTER_MAX_DESCRIPTION;
var CHARACTER_LAYER_SOURCES = ["skill", "condition", "equipment"];
var CHARACTER_LAYER_KINDS = ["mult", "flat", "pct"];
// Fixed level vocabularies for the character panel's intimate section
// (mirror of world/lore/sexual_vocab.py, the shared vocabulary source).
var CHARACTER_INTIMATE_AROUSAL_LEVELS = ["平靜", "微興奮", "中等", "高度", "極限"];
var CHARACTER_INTIMATE_WETNESS_LEVELS = ["乾燥", "微濕", "濕潤", "大量", "泛濫"];
var CHARACTER_INTIMATE_SHAME_LEVELS = ["無", "輕微", "中等", "強烈", "成癮"];
var CHARACTER_INTIMATE_EXPOSURE_LEVELS = ["極低", "低", "中等", "高", "極高"];
var CHARACTER_INTIMATE_CLIMAX_PHASE_LEVELS = ["未達", "接近", "進行中", "餘韻"];

function validateCharacterKey(value, field) {
  var key = validateIdentifier(value, field);
  if (codePoints(key) > CHARACTER_MAX_KEY) {
    throw new Error(field + " exceeds its bound");
  }
  return key;
}


// Breakdown row pieces (expose-stat-breakdown-read-model): the exact
// {source, name, kind, amount} layer and the seven-field trait row. The
// numeric fields accept JSON numbers (a scaled rule-table grant produces
// fractional values such as 2.5), never booleans or non-finite numbers.
function validateCharacterBreakdownLayer(value) {
  requireExactFields(value, "breakdown layer", ["source", "name", "kind", "amount"], []);
  if (CHARACTER_LAYER_SOURCES.indexOf(value.source) === -1) {
    throw new Error("breakdown layer source is not a stable value");
  }
  var name = requireString(value.name, "name", CHARACTER_MAX_LABEL);
  if (!name.trim()) {
    throw new Error("breakdown layer name must be non-empty");
  }
  if (CHARACTER_LAYER_KINDS.indexOf(value.kind) === -1) {
    throw new Error("breakdown layer kind is not a stable value");
  }
  var amount = requireNumber(
    value.amount,
    "breakdown layer amount",
    -MAX_SAFE_INTEGER,
    MAX_SAFE_INTEGER
  );
  if (amount === 0) {
    throw new Error("breakdown layer amount must be non-zero");
  }
  return value;
}

function validateCharacterTraitRow(value) {
  requireExactFields(
    value,
    "trait row",
    ["key", "label", "base", "current", "max", "effective", "layers"],
    []
  );
  validateCharacterKey(value.key, "trait key");
  var label = requireString(value.label, "label", CHARACTER_MAX_LABEL);
  if (!label.trim()) {
    throw new Error("trait label must be non-empty");
  }
  requireInt(value.base, "base", 0, MAX_SAFE_INTEGER);
  requireNumber(value.current, "current", 0, MAX_SAFE_INTEGER);
  if (value.max !== null) {
    requireInt(value.max, "max", 1, MAX_SAFE_INTEGER);
    if (value.current > value.max) {
      throw new Error("trait current must not exceed maximum");
    }
  }
  requireNumber(value.effective, "effective", 0, MAX_SAFE_INTEGER);
  // The defining row contract: a gauge row's effective value IS its
  // maximum; a static row exposes its authoritative effective total through
  // the total-display field. A payload contradicting either is rejected at
  // the boundary instead of letting two incompatible totals diverge.
  if (value.max !== null) {
    if (value.effective !== value.max) {
      throw new Error("gauge trait effective must equal its maximum");
    }
  } else if (value.current !== value.effective) {
    throw new Error("static trait current must equal effective");
  }
  if (!Array.isArray(value.layers) || value.layers.length > CHARACTER_MAX_LAYERS) {
    throw new Error(
      "layers must be a list of at most " + CHARACTER_MAX_LAYERS + " rows"
    );
  }
  value.layers.forEach(validateCharacterBreakdownLayer);
  return value;
}

function validateCharacterPassiveRow(value) {
  requireExactFields(value, "passive row", ["key", "label"], []);
  validateCharacterKey(value.key, "passive key");
  var label = requireString(value.label, "label", CHARACTER_MAX_LABEL);
  if (!label.trim()) {
    throw new Error("passive label must be non-empty");
  }
  return value;
}

function validateCharacterActiveSkillRow(value) {
  requireExactFields(
    value,
    "active skill row",
    ["key", "label"],
    ["cost", "target_spec", "usable_out_of_combat", "freeform_scales"]
  );
  validateCharacterKey(value.key, "active key");
  var label = requireString(value.label, "label", CHARACTER_MAX_LABEL);
  if (!label.trim()) {
    throw new Error("active skill label must be non-empty");
  }
  var cost = value.cost;
  if (cost !== undefined) {
    if (!isPlainObject(cost) || Object.keys(cost).length > MAX_COST_KEYS) {
      throw new Error("skill cost must be a bounded object");
    }
    Object.keys(cost).forEach(function (resource) {
      validateIdentifier(resource, "cost resource key");
      requireInt(cost[resource], "cost amount", 0, MAX_SAFE_INTEGER);
    });
  }
  if (value.target_spec !== undefined && TARGET_SPECS.indexOf(value.target_spec) === -1) {
    throw new Error("skill target_spec is not a stable value");
  }
  if (value.usable_out_of_combat !== undefined && typeof value.usable_out_of_combat !== "boolean") {
    throw new Error("skill usable_out_of_combat must be a boolean");
  }
  var baseMp =
    isPlainObject(cost) && Number.isInteger(cost.mp) && cost.mp > 0 ? cost.mp : null;
  if (value.freeform_scales !== undefined) {
    validateFreeformScales(value.freeform_scales, baseMp);
  }
  // Python omits the field when it is null; normalize identically.
  if (value.freeform_scales === null) {
    delete value.freeform_scales;
  }
  return value;
}

function validateCharacterSkillGroup(value, rowValidator) {
  requireExactFields(value, "skill group", ["group", "label", "skills"], []);
  if (value.group !== null) {
    var group = requireString(value.group, "group", CHARACTER_MAX_KEY);
    if (!group.trim()) {
      throw new Error("group must be non-empty when set");
    }
  }
  if (value.label !== null) {
    var label = requireString(value.label, "label", CHARACTER_MAX_LABEL);
    if (!label.trim()) {
      throw new Error("label must be non-empty when set");
    }
  }
  if ((value.group === null) !== (value.label === null)) {
    throw new Error("group and label must both be set or both be null");
  }
  if (!Array.isArray(value.skills)) {
    throw new Error("skills must be a list");
  }
  value.skills.forEach(rowValidator || validateCharacterPassiveRow);
  return value;
}

function validateCharacterCategoryGroup(value, rowValidator) {
  requireExactFields(value, "category group", ["category", "label", "groups"], []);
  validateCharacterKey(value.category, "category key");
  var label = requireString(value.label, "label", CHARACTER_MAX_LABEL);
  if (!label.trim()) {
    throw new Error("category label must be non-empty");
  }
  if (!Array.isArray(value.groups) || value.groups.length === 0) {
    throw new Error("a category group must carry a non-empty groups list");
  }
  value.groups.forEach(function (group) {
    validateCharacterSkillGroup(group, rowValidator);
  });
  return value;
}

function characterFlattenedSkillCount(categoryGroups) {
  var count = 0;
  categoryGroups.forEach(function (category) {
    category.groups.forEach(function (group) {
      count += group.skills.length;
    });
  });
  return count;
}

// Equipment row: the identity fields plus the required (possibly empty)
// server-formatted adjustment summary.
function validateCharacterEquipmentRow(value) {
  requireExactFields(
    value,
    "equipment row",
    ["slot", "item_key", "display_name", "adjustment"],
    []
  );
  var slot = requireString(value.slot, "slot", CHARACTER_MAX_SLOT);
  if (!slot.trim()) {
    throw new Error("slot must be non-empty");
  }
  validateCharacterKey(value.item_key, "item_key");
  var displayName = requireString(value.display_name, "display_name", CHARACTER_MAX_LABEL);
  if (!displayName.trim()) {
    throw new Error("equipment display_name must be non-empty");
  }
  requireString(value.adjustment, "adjustment", CHARACTER_MAX_ADJUSTMENT);
  return value;
}

function validateCharacterDisplayedRow(value) {
  requireExactFields(value, "displayed row", ["key", "label", "value"], []);
  validateCharacterKey(value.key, "displayed key");
  var label = requireString(value.label, "label", CHARACTER_MAX_LABEL);
  if (!label.trim()) {
    throw new Error("displayed label must be non-empty");
  }
  requireInt(value.value, "value", 0, MAX_SAFE_INTEGER);
  return value;
}

function validateCharacterDisguise(value) {
  requireExactFields(value, "disguise", ["active", "description", "displayed"], []);
  var active = requireBool(value.active, "active");
  var description = requireString(value.description, "description", CHARACTER_MAX_DESCRIPTION);
  if (!Array.isArray(value.displayed) || value.displayed.length > CHARACTER_MAX_DISPLAYED_ROWS) {
    throw new Error("displayed must be a list of at most " + CHARACTER_MAX_DISPLAYED_ROWS + " rows");
  }
  value.displayed.forEach(validateCharacterDisplayedRow);
  if (!active && value.displayed.length > 0) {
    throw new Error("an undisguised actor must have an empty displayed list");
  }
  if (active && !description.trim()) {
    throw new Error("disguise description must be non-empty when active");
  }
  return value;
}

function validateCharacterGuild(value) {
  requireExactFields(value, "guild", ["rank", "merit"], []);
  if (value.rank !== null) {
    var rank = requireString(value.rank, "rank", CHARACTER_MAX_KEY);
    if (!rank.trim()) {
      throw new Error("rank must be non-empty when set");
    }
  }
  requireInt(value.merit, "merit", 0, MAX_SAFE_INTEGER);
  return value;
}

var CHARACTER_MAX_PERSONA = 600;
var CHARACTER_PERSONA_FIELDS = [
  "background",
  "personality",
  "life_story",
  "habit",
];

function validateCharacterPersona(value) {
  // The four editable persona prose keys (persona-editing D3): each is
  // independently nullable, whitespace-nulling, and bounded at the shared
  // 600-code-point cap. Structural keys never appear in this section.
  requireExactFields(value, "persona", CHARACTER_PERSONA_FIELDS, []);
  var result = {};
  for (var i = 0; i < CHARACTER_PERSONA_FIELDS.length; i++) {
    var field = CHARACTER_PERSONA_FIELDS[i];
    if (value[field] === null) {
      result[field] = null;
      continue;
    }
    var text = requireString(
      value[field],
      "persona." + field,
      CHARACTER_MAX_PERSONA
    );
    result[field] = text.trim() ? text.trim() : null;
  }
  return result;
}

// Nullable intimate section of the character panel (webclient-intimate-status-section).
// `null` means the actor has no sexual-state record; otherwise the section
// carries exactly the six intimate fields, each level field checked against
// its fixed vocabulary and `climax_today` as a non-negative safe integer.
function validateCharacterIntimateLevel(value, field, vocabulary) {
  var level = requireString(value, field, CHARACTER_MAX_LABEL);
  if (vocabulary.indexOf(level) === -1) {
    throw new Error(field + " is not a member of its fixed vocabulary");
  }
  return level;
}

function validateCharacterIntimate(value) {
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
    arousal: validateCharacterIntimateLevel(value.arousal, "intimate.arousal", CHARACTER_INTIMATE_AROUSAL_LEVELS),
    wetness: validateCharacterIntimateLevel(value.wetness, "intimate.wetness", CHARACTER_INTIMATE_WETNESS_LEVELS),
    shame: validateCharacterIntimateLevel(value.shame, "intimate.shame", CHARACTER_INTIMATE_SHAME_LEVELS),
    exposure: validateCharacterIntimateLevel(value.exposure, "intimate.exposure", CHARACTER_INTIMATE_EXPOSURE_LEVELS),
    climax_phase: validateCharacterIntimateLevel(value.climax_phase, "intimate.climax_phase", CHARACTER_INTIMATE_CLIMAX_PHASE_LEVELS),
    climax_today: requireInt(value.climax_today, "intimate.climax_today", 0, MAX_SAFE_INTEGER),
  };
}

// Exact available character panel v7 schema (design D10: skill category
// grouping + the intimate-status section; expose-stat-breakdown-read-model
// added the breakdown trait rows and the adjustment-bearing equipment
// rows; render-equipment-breakdown-webclient closed the transitional v4
// tolerance window; title-system added the optional composed full_title).
// Shared bounds are guarded by a dual-direction parity test.
function validateCharacterAvailablePanel(payload) {
  requireExactFields(
    payload,
    "character panel",
    [
      "schema_version",
      "available",
      "kind",
      "traits",
      "actives",
      "passives",
      "equipment",
      "disguise",
      "guild",
      "wallet",
      "persona",
      "intimate",
    ],
    ["full_title"]
  );
  var fullTitle = null;
  if (Object.prototype.hasOwnProperty.call(payload, "full_title")) {
    fullTitle = requireString(
      payload.full_title,
      "full_title",
      MAX_FULL_TITLE_CODE_POINTS
    );
    if (!fullTitle.trim()) {
      throw new Error("full_title must be non-empty when present");
    }
  }
  if (payload.schema_version !== 7) {
    throw new Error("unsupported character schema_version");
  }
  if (payload.available !== true || payload.kind !== "character") {
    throw new Error("character panel must be available with kind character");
  }
  if (!Array.isArray(payload.traits) || payload.traits.length > CHARACTER_MAX_TRAIT_ROWS) {
    throw new Error("traits must be a list of at most " + CHARACTER_MAX_TRAIT_ROWS + " rows");
  }
  var traitKeys = {};
  payload.traits.forEach(function (row) {
    validateCharacterTraitRow(row);
    if (traitKeys[row.key]) {
      throw new Error("trait keys must be unique");
    }
    traitKeys[row.key] = true;
  });
  if (!Array.isArray(payload.actives) || payload.actives.length > CHARACTER_MAX_CATEGORY_GROUPS) {
    throw new Error(
      "actives must be a list of at most " + CHARACTER_MAX_CATEGORY_GROUPS + " category groups"
    );
  }
  payload.actives.forEach(function (group) {
    validateCharacterCategoryGroup(group, validateCharacterActiveSkillRow);
  });
  if (characterFlattenedSkillCount(payload.actives) > CHARACTER_MAX_ACTIVE_ROWS) {
    throw new Error(
      "actives must contain at most " + CHARACTER_MAX_ACTIVE_ROWS + " skill rows in total"
    );
  }
  if (!Array.isArray(payload.passives) || payload.passives.length > CHARACTER_MAX_CATEGORY_GROUPS) {
    throw new Error(
      "passives must be a list of at most " + CHARACTER_MAX_CATEGORY_GROUPS + " category groups"
    );
  }
  payload.passives.forEach(function (group) {
    validateCharacterCategoryGroup(group, validateCharacterPassiveRow);
  });
  if (characterFlattenedSkillCount(payload.passives) > CHARACTER_MAX_PASSIVE_ROWS) {
    throw new Error(
      "passives must contain at most " + CHARACTER_MAX_PASSIVE_ROWS + " skill rows in total"
    );
  }
  if (!Array.isArray(payload.equipment) || payload.equipment.length > CHARACTER_MAX_EQUIPMENT_ROWS) {
    throw new Error("equipment must be a list of at most " + CHARACTER_MAX_EQUIPMENT_ROWS + " rows");
  }
  payload.equipment.forEach(validateCharacterEquipmentRow);
  validateCharacterDisguise(payload.disguise);
  validateCharacterGuild(payload.guild);
  requireInt(payload.wallet, "wallet", 0, MAX_SAFE_INTEGER);
  var persona = validateCharacterPersona(payload.persona);

  var intimate = validateCharacterIntimate(payload.intimate);
  var result = {
    schema_version: 7,
    available: true,
    kind: "character",
    traits: payload.traits,
    actives: payload.actives,
    passives: payload.passives,
    equipment: payload.equipment,
    disguise: payload.disguise,
    guild: payload.guild,
    wallet: payload.wallet,
    persona: persona,
    intimate: intimate,
  };
  if (fullTitle !== null) {
    result.full_title = fullTitle;
  }
  // Envelope guarantee (design D10): an over-limit payload fails closed.
  if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
    throw new Error("character payload exceeds the OOB envelope limit");
  }
  return result;
}

function validateCharacterPanel(payload) {
  // Version gate (mirror of the server validator): 7 is the only accepted
  // schema version (persona-editing four-key persona section).
  requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
  if (payload.schema_version !== 7) {
    throw new Error("unsupported character schema_version");
  }
  return validateCharacterAvailablePanel(payload);
}

module.exports = {
  CHARACTER_MAX_TRAIT_ROWS: CHARACTER_MAX_TRAIT_ROWS,
  CHARACTER_MAX_ACTIVE_ROWS: CHARACTER_MAX_ACTIVE_ROWS,
  CHARACTER_MAX_PASSIVE_ROWS: CHARACTER_MAX_PASSIVE_ROWS,
  CHARACTER_MAX_CATEGORY_GROUPS: CHARACTER_MAX_CATEGORY_GROUPS,
  CHARACTER_MAX_EQUIPMENT_ROWS: CHARACTER_MAX_EQUIPMENT_ROWS,
  CHARACTER_MAX_DISPLAYED_ROWS: CHARACTER_MAX_DISPLAYED_ROWS,
  CHARACTER_MAX_KEY: CHARACTER_MAX_KEY,
  CHARACTER_MAX_LABEL: CHARACTER_MAX_LABEL,
  CHARACTER_MAX_DESCRIPTION: CHARACTER_MAX_DESCRIPTION,
  CHARACTER_MAX_SLOT: CHARACTER_MAX_SLOT,
  validateCharacterPanel: validateCharacterPanel,
  validateCharacterTraitRow: validateCharacterTraitRow,
  validateCharacterEquipmentRow: validateCharacterEquipmentRow,
  validateCharacterBreakdownLayer: validateCharacterBreakdownLayer,
  validateCharacterActiveSkillRow: validateCharacterActiveSkillRow,
  CHARACTER_MAX_PERSONA: CHARACTER_MAX_PERSONA,
  CHARACTER_PERSONA_FIELDS: CHARACTER_PERSONA_FIELDS,
};
