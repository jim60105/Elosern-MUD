"use strict";

var C = require("../constants.js");
var core = require("../core.js");
var skillDescriptor = require("./skill_descriptor.js");

var requireNumber = skillDescriptor.requireNumber;
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
var SEVERITIES = C.SEVERITIES;
var FREEFORM_SCALES_ALLOWED = C.FREEFORM_SCALES_ALLOWED;
var FREEFORM_LABELS_ALLOWED = C.FREEFORM_LABELS_ALLOWED;

// ---------------------------------------------------------------------------
// character panel v1 validators (mirror of
// web.webclient.presentation.character, design D10). Shared bounds are
// guarded by a dual-direction parity test.
// ---------------------------------------------------------------------------

var CHARACTER_MAX_TRAIT_ROWS = 32;
// Actives absorb the act-catalogue unlock flood; passives do not, so the
// two flattened-row bounds are deliberately asymmetric (mirror of the
// server's MAX_ACTIVE_ROWS/MAX_PASSIVE_ROWS).
var CHARACTER_MAX_ACTIVE_ROWS = 96;
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
// v8 condition-row bounds (mirror of web.webclient.presentation.character):
// at most 32 ordered rows, a 128-code-point label, at most 16 modifier pairs
// and a bounded origin label. A modifier value is the rulebook's canonical
// adjustment scalar: a finite number or a bounded authored percentage string.
var CHARACTER_MAX_CONDITIONS = 32;
var CHARACTER_MAX_CONDITION_LABEL = 128;
var CHARACTER_MAX_MODIFIER_KEYS = 16;
var CHARACTER_MAX_CONDITION_SOURCE = 32;
var CHARACTER_MAX_MODIFIER_TEXT = 16;
// The closed origin vocabulary (mirror of CONDITION_SOURCE_LABELS).
var CHARACTER_CONDITION_SOURCES = ["裝備", "狀態", "裝備、狀態", "未知"];
// v9 selected-skill bounds (mirror of web.webclient.presentation.character):
// each lineage side is bounded, and the ladder is the closed canonical table.
var CHARACTER_MAX_SELECTED_LINEAGE_ROWS = 8;
var CHARACTER_MAX_FREEFORM_LADDER_RUNGS = 5;

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
    requireInt(value.max, "max", 0, MAX_SAFE_INTEGER);
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
    [
      "key",
      "label",
      "level",
      "xp_into_level",
      "xp_to_next_level",
      "capped",
      "fresh",
      "booked",
    ],
    ["cost", "target_spec", "usable_out_of_combat"]
  );
  validateCharacterKey(value.key, "active key");
  var label = requireString(value.label, "label", CHARACTER_MAX_LABEL);
  if (!label.trim()) {
    throw new Error("active skill label must be non-empty");
  }
  requireInt(value.level, "level", 0, MAX_SAFE_INTEGER);
  requireNumber(value.xp_into_level, "xp_into_level", 0, MAX_SAFE_INTEGER);
  requireNumber(value.xp_to_next_level, "xp_to_next_level", 0, MAX_SAFE_INTEGER);
  var capped = requireBool(value.capped, "capped");
  if (capped && value.xp_to_next_level !== 0) {
    throw new Error("a capped skill's xp_to_next_level must be zero");
  }
  requireBool(value.fresh, "fresh");
  requireBool(value.booked, "booked");
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
  return value;
}

function validateCharacterLineageEdge(value, levelField) {
  requireExactFields(value, "lineage edge", ["key", "label", levelField], []);
  validateCharacterKey(value.key, "lineage key");
  var label = requireString(value.label, "label", CHARACTER_MAX_LABEL);
  if (!label.trim()) {
    throw new Error("lineage edge label must be non-empty");
  }
  requireInt(value[levelField], levelField, 1, MAX_SAFE_INTEGER);
  return value;
}

function validateCharacterLineage(value) {
  requireExactFields(value, "lineage", ["prerequisites", "next"], []);
  [
    ["prerequisites", "level"],
    ["next", "min_level"],
  ].forEach(function (pair) {
    var rows = value[pair[0]];
    if (!Array.isArray(rows) || rows.length > CHARACTER_MAX_SELECTED_LINEAGE_ROWS) {
      throw new Error(
        pair[0] +
          " must be a list of at most " +
          CHARACTER_MAX_SELECTED_LINEAGE_ROWS +
          " edges"
      );
    }
    rows.forEach(function (row) {
      validateCharacterLineageEdge(row, pair[1]);
    });
  });
  return value;
}

function validateCharacterFreeformLadder(value) {
  if (
    !Array.isArray(value) ||
    value.length !== CHARACTER_MAX_FREEFORM_LADDER_RUNGS
  ) {
    throw new Error(
      "freeform_ladder must carry exactly " +
        CHARACTER_MAX_FREEFORM_LADDER_RUNGS +
        " rungs"
    );
  }
  value.forEach(function (entry, index) {
    if (!isPlainObject(entry)) {
      throw new Error("freeform_ladder rung must be an object");
    }
    var hasCost = Object.prototype.hasOwnProperty.call(entry, "mp_cost");
    var hasLevel = Object.prototype.hasOwnProperty.call(entry, "unlock_level");
    if (hasCost === hasLevel) {
      throw new Error(
        "a freeform_ladder rung carries exactly one of mp_cost and unlock_level"
      );
    }
    var levelField = hasCost ? "mp_cost" : "unlock_level";
    requireExactFields(entry, "freeform_ladder rung", ["scale", "label", levelField], []);
    if (entry.scale !== FREEFORM_SCALES_ALLOWED[index]) {
      throw new Error("freeform_ladder must be in canonical ascending scale order");
    }
    if (entry.label !== FREEFORM_LABELS_ALLOWED[index]) {
      throw new Error(
        "freeform_ladder label must be the canonical label of its scale"
      );
    }
    if (hasCost) {
      requireInt(entry.mp_cost, "mp_cost", 0, MAX_SAFE_INTEGER);
    } else {
      // The entry rung unlocks at level 0, so a locked rung's level is >= 1.
      requireInt(entry.unlock_level, "unlock_level", 1, MAX_SAFE_INTEGER);
    }
  });
  return value;
}

function validateCharacterSelectedSkill(value) {
  if (value === null) {
    return null;
  }
  requireExactFields(
    value,
    "selected skill",
    ["key", "lineage"],
    ["freeform_ladder"]
  );
  validateCharacterKey(value.key, "selected skill key");
  validateCharacterLineage(value.lineage);
  if (Object.prototype.hasOwnProperty.call(value, "freeform_ladder")) {
    validateCharacterFreeformLadder(value.freeform_ladder);
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

// One canonical adjustment scalar: a finite number (flat/mult amounts) or a
// bounded authored percentage string ("-10%"), carried verbatim from the
// status read model. Anything else fails closed.
function validateCharacterModifierValue(value, field) {
  if (typeof value === "string") {
    if (!value.trim() || codePoints(value) > CHARACTER_MAX_MODIFIER_TEXT) {
      throw new Error(field + " must be a bounded string");
    }
    return value;
  }
  return requireNumber(value, field, -MAX_SAFE_INTEGER, MAX_SAFE_INTEGER);
}

// One exact v8 condition row. Severity is the shared condition-severity
// vocabulary; remaining_seconds is null for an indefinite condition;
// modifiers is the canonical adjustment map; source is the bounded origin
// label (the character panel carries it instead of structured provenance).
function validateCharacterConditionRow(value) {
  requireExactFields(
    value,
    "condition row",
    ["code", "label", "severity", "remaining_seconds", "modifiers", "source"],
    []
  );
  validateCharacterKey(value.code, "condition code");
  var label = requireString(value.label, "label", CHARACTER_MAX_CONDITION_LABEL);
  if (!label.trim()) {
    throw new Error("condition label must be non-empty");
  }
  if (SEVERITIES.indexOf(value.severity) === -1) {
    throw new Error("condition severity is not a stable severity");
  }
  if (value.remaining_seconds !== null) {
    requireInt(value.remaining_seconds, "remaining_seconds", 0, MAX_SAFE_INTEGER);
  }
  if (!isPlainObject(value.modifiers)) {
    throw new Error("condition modifiers must be an object");
  }
  var modifierKeys = Object.keys(value.modifiers);
  if (modifierKeys.length > CHARACTER_MAX_MODIFIER_KEYS) {
    throw new Error(
      "condition modifiers exceeds the maximum of " +
        CHARACTER_MAX_MODIFIER_KEYS +
        " keys"
    );
  }
  modifierKeys.forEach(function (key) {
    validateCharacterKey(key, "condition modifier key");
    validateCharacterModifierValue(
      value.modifiers[key],
      "condition modifier " + key
    );
  });
  var source = requireString(value.source, "source", CHARACTER_MAX_CONDITION_SOURCE);
  if (CHARACTER_CONDITION_SOURCES.indexOf(source) === -1) {
    throw new Error("condition source is not a stable origin");
  }
  return value;
}

// Exact available character panel v9 schema (design D10). v8 builds the panel
// for the viewed party member with `member_id` and the ordered `conditions`
// rows (persona/intimate belong to party_member). v9 requires the six growth
// facts on every active row and drops the per-row `freeform_scales`; the one
// selected skill's lineage position and ladder ride `selected_skill`. Shared
// bounds are guarded by a dual-direction parity test.
function validateCharacterAvailablePanel(payload) {
  requireExactFields(
    payload,
    "character panel",
    [
      "schema_version",
      "available",
      "kind",
      "member_id",
      "traits",
      "conditions",
      "actives",
      "passives",
      "equipment",
      "disguise",
      "guild",
      "wallet",
      "selected_skill",
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
  if (payload.schema_version !== 9) {
    throw new Error("unsupported character schema_version");
  }
  if (payload.available !== true || payload.kind !== "character") {
    throw new Error("character panel must be available with kind character");
  }
  requireInt(payload.member_id, "member_id", 1, MAX_SAFE_INTEGER);
  validateCharacterSelectedSkill(payload.selected_skill);
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
  if (!Array.isArray(payload.conditions) || payload.conditions.length > CHARACTER_MAX_CONDITIONS) {
    throw new Error(
      "conditions must be a list of at most " + CHARACTER_MAX_CONDITIONS + " rows"
    );
  }
  payload.conditions.forEach(validateCharacterConditionRow);
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

  var result = {
    schema_version: 9,
    available: true,
    kind: "character",
    member_id: payload.member_id,
    traits: payload.traits,
    conditions: payload.conditions,
    actives: payload.actives,
    passives: payload.passives,
    equipment: payload.equipment,
    disguise: payload.disguise,
    guild: payload.guild,
    wallet: payload.wallet,
    selected_skill: payload.selected_skill,
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
  // Version gate (mirror of the server validator): 9 is the only accepted
  // schema version (growth rows; the selected skill's lineage and ladder).
  requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
  if (payload.schema_version !== 9) {
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
  CHARACTER_MAX_CONDITIONS: CHARACTER_MAX_CONDITIONS,
  CHARACTER_MAX_CONDITION_LABEL: CHARACTER_MAX_CONDITION_LABEL,
  CHARACTER_MAX_MODIFIER_KEYS: CHARACTER_MAX_MODIFIER_KEYS,
  CHARACTER_MAX_CONDITION_SOURCE: CHARACTER_MAX_CONDITION_SOURCE,
  CHARACTER_MAX_MODIFIER_TEXT: CHARACTER_MAX_MODIFIER_TEXT,
  CHARACTER_CONDITION_SOURCES: CHARACTER_CONDITION_SOURCES,
  CHARACTER_MAX_SELECTED_LINEAGE_ROWS: CHARACTER_MAX_SELECTED_LINEAGE_ROWS,
  CHARACTER_MAX_FREEFORM_LADDER_RUNGS: CHARACTER_MAX_FREEFORM_LADDER_RUNGS,
  validateCharacterPanel: validateCharacterPanel,
  validateCharacterTraitRow: validateCharacterTraitRow,
  validateCharacterConditionRow: validateCharacterConditionRow,
  validateCharacterEquipmentRow: validateCharacterEquipmentRow,
  validateCharacterBreakdownLayer: validateCharacterBreakdownLayer,
  validateCharacterActiveSkillRow: validateCharacterActiveSkillRow,
  validateCharacterSelectedSkill: validateCharacterSelectedSkill,
};
