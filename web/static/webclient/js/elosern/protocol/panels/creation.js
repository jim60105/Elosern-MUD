"use strict";

var C = require("../constants.js");
var core = require("../core.js");
var artwork = require("../artwork.js");

var isPlainObject = core.isPlainObject;
var codePoints = core.codePoints;
var jsonByteSize = core.jsonByteSize;
var requireExactFields = core.requireExactFields;
var requireInt = core.requireInt;
var requireString = core.requireString;
var validateIdentifier = core.validateIdentifier;

var MAX_SAFE_INTEGER = C.MAX_SAFE_INTEGER;
var MAX_CANONICAL_JSON_BYTES = C.MAX_CANONICAL_JSON_BYTES;
var CREATION_MAX_PRESETS = C.CREATION_MAX_PRESETS;
var CREATION_MAX_RACES = C.CREATION_MAX_RACES;
var CREATION_MAX_SUBRACES = C.CREATION_MAX_SUBRACES;
var CREATION_MAX_PROFILES = C.CREATION_MAX_PROFILES;
var CREATION_MIN_NAME_LENGTH = C.CREATION_MIN_NAME_LENGTH;
var CREATION_MAX_NAME_LENGTH = C.CREATION_MAX_NAME_LENGTH;
var CREATION_AGE_MINIMUM = C.CREATION_AGE_MINIMUM;
var CREATION_AGE_MAXIMUM = C.CREATION_AGE_MAXIMUM;
var CREATION_APPARENT_AGE_MINIMUM = C.CREATION_APPARENT_AGE_MINIMUM;
var CREATION_APPARENT_AGE_MAXIMUM = C.CREATION_APPARENT_AGE_MAXIMUM;
var CREATION_MAX_PRESET_KEY = C.CREATION_MAX_PRESET_KEY;
var CREATION_MAX_DISPLAY_NAME = C.CREATION_MAX_DISPLAY_NAME;
var CREATION_MAX_RACE_KEY = C.CREATION_MAX_RACE_KEY;
var CREATION_MAX_PROPOSAL_NAME = C.CREATION_MAX_PROPOSAL_NAME;
var CREATION_MAX_DESCRIPTION = C.CREATION_MAX_DESCRIPTION;
var CREATION_MAX_EMPHASIS = C.CREATION_MAX_EMPHASIS;
var CREATION_MAX_BACKGROUND = C.CREATION_MAX_BACKGROUND;
var CREATION_MAX_PERSONA_BACKGROUND = C.CREATION_MAX_PERSONA_BACKGROUND;
var CREATION_MAX_SUBRACE_KEY = C.CREATION_MAX_SUBRACE_KEY;
var CREATION_MAX_SPECIALTY = C.CREATION_MAX_SPECIALTY;
var CREATION_MAX_LABEL = C.CREATION_MAX_LABEL;
var CREATION_MAX_EXPLANATION = C.CREATION_MAX_EXPLANATION;
var CREATION_AXES = C.CREATION_AXES;
var CREATION_PRESET_STAGE = C.CREATION_PRESET_STAGE;
var CREATION_CUSTOM_STAGE = C.CREATION_CUSTOM_STAGE;
var CREATION_PERSONA_KEYS = C.CREATION_PERSONA_KEYS;
var CREATION_SEX_VALUES = C.CREATION_SEX_VALUES;
var CREATION_MAX_SEX_OPTIONS = C.CREATION_MAX_SEX_OPTIONS;
var CREATION_SCHEMA_VERSION = C.CREATION_SCHEMA_VERSION;
var CREATION_MAX_SILHOUETTES = C.CREATION_MAX_SILHOUETTES;
var CREATION_MAX_PORTRAIT_REASON = C.CREATION_MAX_PORTRAIT_REASON;
var CREATION_MAX_AFFINITY_ELEMENTS = C.CREATION_MAX_AFFINITY_ELEMENTS;
var CREATION_AFFINITY_ELEMENTS = C.CREATION_AFFINITY_ELEMENTS;
var CREATION_AFFINITY_RACES = C.CREATION_AFFINITY_RACES;
var CREATION_AFFINITY_MAXIMUMS = C.CREATION_AFFINITY_MAXIMUMS;

// ---------------------------------------------------------------------------
// creation panel v8 validator (mirror of web.webclient.presentation.creation).
// ---------------------------------------------------------------------------

function validateCreationPreviewArtworkSemantics(value, field) {
  // A creation preview is not a generated subject and carries no backend
  // retention authorization, so both claims stay explicitly empty and the
  // terminal is the built-in alpha mask.
  if (value.generation_subject !== null || value.generation_state !== null) {
    throw new Error(field + " must claim no generation");
  }
  if (value.retention_sources.length !== 0) {
    throw new Error(field + " must carry no retention");
  }
  if (value.terminal === null || value.terminal.kind !== "alpha_mask") {
    throw new Error(field + " must carry an alpha terminal");
  }
  if (
    value.terminal.resource.origin !== artwork.ORIGIN_SILHOUETTE ||
    value.terminal.resource.url.indexOf("/art/defaults/") !== 0
  ) {
    throw new Error(field + " terminal must name the built-in silhouette route");
  }
}

function validateCreationPresetArtwork(value, key) {
  var checked = artwork.validateArtwork(value);
  if (checked.subject_id !== "creation:preset:" + key) {
    throw new Error("preset artwork subject_id does not match the card");
  }
  validateCreationPreviewArtworkSemantics(checked, "preset artwork");
  var images = checked.attempts.filter(function (attempt) {
    return attempt.type === "image";
  });
  if (images.length !== checked.attempts.length || images.length > 1) {
    throw new Error("preset artwork must carry at most one image attempt and no fault");
  }
  if (images.length === 1) {
    if (images[0].resource.origin !== artwork.ORIGIN_OFFICIAL) {
      throw new Error("preset artwork attempt must be official");
    }
    if (images[0].resource.url.indexOf("/art/official/") !== 0) {
      throw new Error("preset artwork attempt must name the official art route");
    }
  }
  return checked;
}

function validateCreationPresetCard(value) {
  requireExactFields(
    value,
    "preset card",
    ["key", "display_name", "race", "race_description", "subrace", "emphasis", "background", "artwork"],
    []
  );
  var key = validateIdentifier(value.key, "preset key");
  if (codePoints(key) > CREATION_MAX_PRESET_KEY) {
    throw new Error("preset key exceeds its bound");
  }
  requireString(value.display_name, "display_name", CREATION_MAX_DISPLAY_NAME);
  var race = validateIdentifier(value.race, "preset race");
  if (codePoints(race) > CREATION_MAX_RACE_KEY) {
    throw new Error("preset race exceeds its bound");
  }
  requireString(value.race_description, "race_description", CREATION_MAX_DESCRIPTION);
  if (value.subrace !== null) {
    var subrace = validateIdentifier(value.subrace, "preset subrace");
    if (codePoints(subrace) > CREATION_MAX_SUBRACE_KEY) {
      throw new Error("preset subrace exceeds its bound");
    }
  }
  requireString(value.emphasis, "emphasis", CREATION_MAX_EMPHASIS);
  requireString(value.background, "background", CREATION_MAX_BACKGROUND);
  validateCreationPresetArtwork(value.artwork, key);
  return value;
}

function validateCreationName(value) {
  requireExactFields(value, "name bounds", ["min_length", "max_length"], []);
  var minimum = requireInt(value.min_length, "min_length", 1, MAX_SAFE_INTEGER);
  var maximum = requireInt(value.max_length, "max_length", 1, MAX_SAFE_INTEGER);
  if (
    minimum !== CREATION_MIN_NAME_LENGTH ||
    maximum !== CREATION_MAX_NAME_LENGTH
  ) {
    throw new Error("name bounds do not match the advertised contract");
  }
  return value;
}

function validateCreationAge(value) {
  requireExactFields(
    value,
    "age bounds",
    ["age_minimum", "age_maximum", "apparent_age_minimum", "apparent_age_maximum"],
    []
  );
  var ageMinimum = requireInt(value.age_minimum, "age_minimum", 0, MAX_SAFE_INTEGER);
  var ageMaximum = requireInt(value.age_maximum, "age_maximum", 0, MAX_SAFE_INTEGER);
  var apparentMinimum = requireInt(
    value.apparent_age_minimum,
    "apparent_age_minimum",
    0,
    MAX_SAFE_INTEGER
  );
  var apparentMaximum = requireInt(
    value.apparent_age_maximum,
    "apparent_age_maximum",
    0,
    MAX_SAFE_INTEGER
  );
  if (
    ageMinimum !== CREATION_AGE_MINIMUM ||
    ageMaximum !== CREATION_AGE_MAXIMUM ||
    apparentMinimum !== CREATION_APPARENT_AGE_MINIMUM ||
    apparentMaximum !== CREATION_APPARENT_AGE_MAXIMUM
  ) {
    throw new Error("age bounds do not match the advertised contract");
  }
  return value;
}

function validateCreationRaceOption(value) {
  requireExactFields(value, "race option", ["key", "display_name_zh", "description", "subraces"], []);
  var displayNameZh = requireString(value.display_name_zh, "display_name_zh", CREATION_MAX_DISPLAY_NAME);
  if (!displayNameZh.trim()) {
    throw new Error("race display_name_zh must be non-empty");
  }
  var key = validateIdentifier(value.key, "race key");
  if (codePoints(key) > CREATION_MAX_RACE_KEY) {
    throw new Error("race key exceeds its bound");
  }
  requireString(value.description, "description", CREATION_MAX_DESCRIPTION);
  if (value.subraces !== null) {
    if (!Array.isArray(value.subraces) || value.subraces.length > CREATION_MAX_SUBRACES) {
      throw new Error("race subraces must be a list or null within its bound");
    }
    value.subraces.forEach(function (entry) {
      var subrace = validateIdentifier(entry, "race subrace");
      if (codePoints(subrace) > CREATION_MAX_SUBRACE_KEY) {
        throw new Error("race subrace exceeds its bound");
      }
    });
  }
  return value;
}

function validateCreationSubraces(value) {
  if (!isPlainObject(value) || Object.keys(value).length > CREATION_MAX_SUBRACES) {
    throw new Error("subraces must be an object within its bound");
  }
  var keys = Object.keys(value);
  for (var i = 0; i < keys.length; i++) {
    var subraceKey = validateIdentifier(keys[i], "subrace key");
    if (codePoints(subraceKey) > CREATION_MAX_SUBRACE_KEY) {
      throw new Error("subrace key exceeds its bound");
    }
    var entry = value[keys[i]];
    requireExactFields(
      entry,
      "subrace entry",
      ["display_name_zh", "common_name_zh", "specialty"],
      []
    );
    requireString(entry.display_name_zh, "display_name_zh", CREATION_MAX_SPECIALTY);
    requireString(entry.common_name_zh, "common_name_zh", CREATION_MAX_SPECIALTY);
    requireString(entry.specialty, "specialty", CREATION_MAX_SPECIALTY);
  }
  return value;
}

function validateCreationAxis(value) {
  requireExactFields(
    value,
    "allocation axis",
    ["axis", "label", "explanation", "minimum", "maximum"],
    []
  );
  var axis = validateIdentifier(value.axis, "axis");
  if (CREATION_AXES.indexOf(axis) === -1) {
    throw new Error("axis " + axis + " is not an allocatable starting axis");
  }
  requireString(value.label, "label", CREATION_MAX_LABEL);
  requireString(value.explanation, "explanation", CREATION_MAX_EXPLANATION);
  var minimum = requireInt(value.minimum, "minimum", 0, MAX_SAFE_INTEGER);
  var maximum = requireInt(value.maximum, "maximum", 0, MAX_SAFE_INTEGER);
  if (minimum > maximum) {
    throw new Error("axis minimum must not exceed maximum");
  }
  return value;
}

function validateCreationProfile(value) {
  requireExactFields(value, "profile", ["race", "subrace", "budget", "axes"], []);
  var race = validateIdentifier(value.race, "profile race");
  if (codePoints(race) > CREATION_MAX_RACE_KEY) {
    throw new Error("profile race exceeds its bound");
  }
  if (value.subrace !== null) {
    var subrace = validateIdentifier(value.subrace, "profile subrace");
    if (codePoints(subrace) > CREATION_MAX_SUBRACE_KEY) {
      throw new Error("profile subrace exceeds its bound");
    }
  }
  requireInt(value.budget, "budget", 0, MAX_SAFE_INTEGER);
  if (!Array.isArray(value.axes) || value.axes.length !== 7) {
    throw new Error("profile axes must contain exactly seven axes");
  }
  var axisKeys = {};
  value.axes.forEach(function (axis) {
    validateCreationAxis(axis);
    axisKeys[axis.axis] = true;
  });
  var expected = {};
  CREATION_AXES.forEach(function (axis) {
    expected[axis] = true;
  });
  var keyCount = Object.keys(axisKeys).length;
  var expectedCount = Object.keys(expected).length;
  if (keyCount !== expectedCount) {
    throw new Error("profile axes must match the seven starting axes");
  }
  return value;
}

function validateCreationSilhouetteArtwork(value, sex, minimum, maximum) {
  // The actor segment is position-stable but not bound: the panel payload
  // carries no actor identity, so only its non-emptiness is checkable here.
  var checked = artwork.validateArtwork(value);
  var prefix = "creation:silhouette:";
  var suffix = ":" + sex + ":" + minimum + ":" + maximum;
  var subjectId = checked.subject_id;
  if (subjectId.indexOf(prefix) !== 0 || subjectId.slice(-suffix.length) !== suffix) {
    throw new Error("silhouette artwork subject_id does not match the entry");
  }
  if (subjectId.slice(prefix.length, subjectId.length - suffix.length) === "") {
    throw new Error("silhouette artwork subject_id is empty");
  }
  validateCreationPreviewArtworkSemantics(checked, "silhouette artwork");
  if (checked.attempts.length !== 0) {
    throw new Error("silhouette artwork must carry no attempt");
  }
  return checked;
}

function validateCreationSilhouettes(value, sexKeys, age) {
  // Mirror of creation._validate_silhouettes: every advertised sex carries a
  // complete, gap-free partition of the advertised apparent-age range, and
  // every descriptor is a canonical alpha-only preview.
  if (
    !Array.isArray(value) ||
    value.length === 0 ||
    value.length > CREATION_MAX_SILHOUETTES
  ) {
    throw new Error("silhouettes must be a non-empty bounded entry list");
  }
  var advertised = Object.create(null);
  sexKeys.forEach(function (key) {
    advertised[key] = true;
  });
  var apparentMinimum = age.apparent_age_minimum;
  var apparentMaximum = age.apparent_age_maximum;
  var bySex = Object.create(null);
  value.forEach(function (entry) {
    requireExactFields(
      entry,
      "silhouette entry",
      ["sex", "apparent_age_minimum", "apparent_age_maximum", "artwork"],
      []
    );
    var sex = validateIdentifier(entry.sex, "silhouette sex");
    if (codePoints(sex) > CREATION_MAX_SUBRACE_KEY) {
      throw new Error("silhouette sex exceeds its bound");
    }
    if (!advertised[sex]) {
      throw new Error("silhouette sex is not an advertised sex option");
    }
    var minimum = requireInt(
      entry.apparent_age_minimum,
      "apparent_age_minimum",
      apparentMinimum,
      apparentMaximum
    );
    var maximum = requireInt(
      entry.apparent_age_maximum,
      "apparent_age_maximum",
      apparentMinimum,
      apparentMaximum
    );
    if (minimum > maximum) {
      throw new Error("silhouette interval minimum must not exceed maximum");
    }
    var checked = validateCreationSilhouetteArtwork(
      entry.artwork,
      sex,
      minimum,
      maximum
    );
    if (!bySex[sex]) {
      bySex[sex] = [];
    }
    bySex[sex].push({
      sex: sex,
      apparent_age_minimum: minimum,
      apparent_age_maximum: maximum,
      artwork: checked,
    });
  });
  var coveredSexes = Object.keys(bySex);
  if (coveredSexes.length !== sexKeys.length) {
    throw new Error("silhouettes must cover every advertised sex exactly once");
  }
  var normalized = [];
  sexKeys.forEach(function (sex) {
    if (!bySex[sex]) {
      throw new Error("silhouettes must cover every advertised sex exactly once");
    }
    bySex[sex].sort(function (left, right) {
      return left.apparent_age_minimum - right.apparent_age_minimum;
    });
    var expected = apparentMinimum;
    bySex[sex].forEach(function (entry) {
      if (entry.apparent_age_minimum !== expected) {
        throw new Error(
          "silhouette intervals must be contiguous without gaps or overlaps"
        );
      }
      expected = entry.apparent_age_maximum + 1;
      normalized.push(entry);
    });
    if (expected !== apparentMaximum + 1) {
      throw new Error(
        "silhouette intervals must cover the advertised apparent-age range"
      );
    }
  });
  return normalized;
}

function validateCreationCustom(value) {
  requireExactFields(
    value,
    "custom",
    ["name", "age", "races", "subraces", "profiles", "affinity", "sex", "silhouettes"],
    []
  );
  validateCreationName(value.name);
  validateCreationAge(value.age);
  if (!Array.isArray(value.races) || value.races.length === 0 || value.races.length > CREATION_MAX_RACES) {
    throw new Error("races must be a non-empty list within its bound");
  }
  value.races.forEach(validateCreationRaceOption);
  validateCreationSubraces(value.subraces);
  if (!Array.isArray(value.profiles) || value.profiles.length === 0 || value.profiles.length > CREATION_MAX_PROFILES) {
    throw new Error("profiles must be a non-empty list within its bound");
  }
  value.profiles.forEach(validateCreationProfile);
  validateCreationAffinity(value.affinity);
  validateCreationSex(value.sex);
  validateCreationSilhouettes(
    value.silhouettes,
    value.sex.map(function (option) {
      return option.key;
    }),
    value.age
  );
  return value;
}

function validateCreationSex(value) {
  // Mirror of web.webclient.presentation.creation._validate_sex_options:
  // the list is exactly the sex vocabulary, in registry order, each option
  // carrying exactly {key, label} with a non-empty bounded label.
  if (
    !Array.isArray(value) ||
    value.length === 0 ||
    value.length > CREATION_MAX_SEX_OPTIONS
  ) {
    throw new Error("sex must be a non-empty bounded option list");
  }
  var keys = [];
  value.forEach(function (entry) {
    requireExactFields(entry, "sex option", ["key", "label"], []);
    var key = validateIdentifier(entry.key, "sex key");
    if (codePoints(key) > CREATION_MAX_SUBRACE_KEY) {
      throw new Error("sex key exceeds its bound");
    }
    requireString(entry.label, "sex label", CREATION_MAX_LABEL);
    if (!entry.label.trim()) {
      throw new Error("sex label must be non-empty");
    }
    keys.push(key);
  });
  if (keys.join(",") !== CREATION_SEX_VALUES.join(",")) {
    throw new Error("sex options must be exactly the sex vocabulary in order");
  }
}

function validateCreationAffinity(value) {
  if (!isPlainObject(value)) {
    throw new Error("affinity must be an object");
  }
  var keys = Object.keys(value).sort().join(",");
  if (keys !== CREATION_AFFINITY_RACES.slice().sort().join(",")) {
    throw new Error("affinity must map human, beastfolk, and elf");
  }
  CREATION_AFFINITY_RACES.forEach(function (raceKey) {
    validateCreationRaceAffinity(value[raceKey], raceKey);
  });
}

function validateCreationRaceAffinity(value, raceKey) {
  requireExactFields(value, "affinity " + raceKey, ["maximum", "elements"], []);
  var maximum = requireInt(value.maximum, "maximum", 0, MAX_SAFE_INTEGER);
  if (maximum !== CREATION_AFFINITY_MAXIMUMS[raceKey]) {
    throw new Error(
      "affinity " + raceKey + " maximum does not match the race bound"
    );
  }
  if (
    !Array.isArray(value.elements) ||
    value.elements.length === 0 ||
    value.elements.length > CREATION_MAX_AFFINITY_ELEMENTS
  ) {
    throw new Error("affinity elements must be a non-empty bounded list");
  }
  var seen = {};
  var elementKeys = [];
  value.elements.forEach(function (entry) {
    requireExactFields(entry, "affinity element", ["key", "label"], []);
    var key = validateIdentifier(entry.key, "affinity key");
    if (CREATION_AFFINITY_ELEMENTS.indexOf(key) === -1) {
      throw new Error("affinity key " + key + " is not a lore element");
    }
    if (seen[key]) {
      throw new Error("affinity element keys must be unique");
    }
    seen[key] = true;
    elementKeys.push(key);
    requireString(entry.label, "affinity label", CREATION_MAX_LABEL);
    if (!entry.label.trim()) {
      throw new Error("affinity element label must be non-empty");
    }
  });
  var expected = CREATION_AFFINITY_ELEMENTS.slice().sort();
  if (elementKeys.slice().sort().join(",") !== expected.join(",")) {
    throw new Error("affinity elements must be exactly the eight lore elements");
  }
}

function validateCreationDraftAffinity(value, raceKey) {
  if (value === null) {
    return [];
  }
  if (!Array.isArray(value)) {
    throw new Error("affinity_elements must be a list or null");
  }
  if (value.length > CREATION_MAX_AFFINITY_ELEMENTS) {
    throw new Error("affinity_elements exceeds its bound");
  }
  if (raceKey === "elf" && value.length > 0) {
    throw new Error(
      "an elf must not supply affinity_elements; the subrace is the authority"
    );
  }
  if (value.length > CREATION_AFFINITY_MAXIMUMS[raceKey]) {
    throw new Error(
      "affinity_elements exceeds the " + raceKey + " maximum of " +
      CREATION_AFFINITY_MAXIMUMS[raceKey]
    );
  }
  var seen = {};
  value.forEach(function (entry) {
    if (CREATION_AFFINITY_ELEMENTS.indexOf(entry) === -1) {
      throw new Error("unknown affinity element " + entry);
    }
    if (seen[entry]) {
      throw new Error("duplicate affinity element " + entry);
    }
    seen[entry] = true;
  });
  return value.slice();
}

function validateCreationPersona(value) {
  // One required nullable persona block: null is the explicit "no persona"
  // value; any other value carries exactly the three prose fields, each a
  // 1..600 code-point non-blank string.
  if (value === null) {
    return null;
  }
  if (!isPlainObject(value)) {
    throw new Error("persona must be null or a JSON object");
  }
  requireExactFields(value, "persona", CREATION_PERSONA_KEYS, []);
  var persona = {};
  CREATION_PERSONA_KEYS.forEach(function (key) {
    var text = value[key];
    if (typeof text !== "string" || !text.trim()) {
      throw new Error("persona." + key + " must be non-empty text");
    }
    if (codePoints(text) > CREATION_MAX_PERSONA_BACKGROUND) {
      throw new Error("persona." + key + " exceeds its bound");
    }
    persona[key] = text;
  });
  return persona;
}

function validateCreationDraft(value) {
  if (value === null) {
    return value;
  }
  if (!isPlainObject(value)) {
    throw new Error("draft must be a JSON object or null");
  }
  if (value.mode === "preset") {
    requireExactFields(value, "preset draft", ["mode", "stage", "preset_key"], []);
    if (value.stage !== CREATION_PRESET_STAGE) {
      throw new Error("unsupported preset draft stage");
    }
    var presetKey = validateIdentifier(value.preset_key, "draft preset_key");
    if (codePoints(presetKey) > CREATION_MAX_PRESET_KEY) {
      throw new Error("draft preset_key exceeds its bound");
    }
    return {
      mode: "preset",
      stage: CREATION_PRESET_STAGE,
      preset_key: presetKey,
    };
  }
  if (value.mode === "custom") {
    requireExactFields(
      value,
      "custom draft",
      ["mode", "stage", "display_name", "age", "apparent_age", "race", "subrace", "allocations", "background", "affinity_elements", "persona", "sex"],
      []
    );
    if (value.stage !== CREATION_CUSTOM_STAGE) {
      throw new Error("unsupported custom draft stage");
    }
    requireString(value.display_name, "display_name", CREATION_MAX_DISPLAY_NAME);
    requireInt(value.age, "age", CREATION_AGE_MINIMUM, CREATION_AGE_MAXIMUM);
    requireInt(
      value.apparent_age,
      "apparent_age",
      CREATION_APPARENT_AGE_MINIMUM,
      CREATION_APPARENT_AGE_MAXIMUM
    );
    var race = validateIdentifier(value.race, "draft race");
    if (codePoints(race) > CREATION_MAX_RACE_KEY) {
      throw new Error("draft race exceeds its bound");
    }
    var subrace = validateIdentifier(value.subrace, "draft subrace");
    if (codePoints(subrace) > CREATION_MAX_SUBRACE_KEY) {
      throw new Error("draft subrace exceeds its bound");
    }
    var background = value.background;
    if (background !== null) {
      background = requireString(background, "draft background", CREATION_MAX_PERSONA_BACKGROUND);
      if (!background.trim()) {
        background = null;
      }
    }
    // The draft stores the concrete normalized member (mirror of the
    // wizard normalizer and _validate_draft; namegen-creation-ui D2/D3).
    if (CREATION_SEX_VALUES.indexOf(value.sex) === -1) {
      throw new Error("draft sex is not a vocabulary member");
    }
    return {
      mode: "custom",
      stage: CREATION_CUSTOM_STAGE,
      display_name: value.display_name,
      age: value.age,
      apparent_age: value.apparent_age,
      race: race,
      subrace: subrace,
      allocations: validateCreationDraftAllocations(value),
      background: background,
      affinity_elements: validateCreationDraftAffinity(value.affinity_elements, race),
      persona: validateCreationPersona(value.persona),
      sex: value.sex,
    };
  }
  throw new Error("draft has an unknown mode");
}

function validateCreationDraftAllocations(value) {
  var allocations = value.allocations;
  if (!isPlainObject(allocations)) {
    throw new Error("draft allocations must be an object");
  }
  var allocationKeys = Object.keys(allocations).slice().sort();
  var expectedKeys = CREATION_AXES.slice().sort();
  if (allocationKeys.join(",") !== expectedKeys.join(",")) {
    throw new Error("draft allocations must contain exactly the seven axes");
  }
  CREATION_AXES.forEach(function (axis) {
    requireInt(allocations[axis], axis, 0, 10000);
  });
  return allocations;
}

function validateCreationProposal(value) {
  // The optional top-level transient concept proposal: exactly revision (a
  // positive session-monotonic sequence number), race, nullable subrace,
  // the seven axes, and a mandatory three-field persona block, plus five
  // optional transient-fill keys present only when the validated proposal
  // carried a value — an absent key is never encoded as null
  // (bump-creation-panel-proposal-v3 D1).
  requireExactFields(
    value,
    "proposal",
    ["revision", "race", "subrace", "allocations", "persona"],
    ["display_name", "age", "apparent_age", "background", "affinity_elements"]
  );
  var revision = requireInt(value.revision, "revision", 1, MAX_SAFE_INTEGER);
  var race = validateIdentifier(value.race, "proposal race");
  if (codePoints(race) > CREATION_MAX_RACE_KEY) {
    throw new Error("proposal race exceeds its bound");
  }
  var subrace = null;
  if (value.subrace !== null) {
    subrace = validateIdentifier(value.subrace, "proposal subrace");
    if (codePoints(subrace) > CREATION_MAX_SUBRACE_KEY) {
      throw new Error("proposal subrace exceeds its bound");
    }
  }
  var persona = validateCreationPersona(value.persona);
  if (persona === null) {
    throw new Error("proposal persona must be a block");
  }
  var checked = {
    revision: revision,
    race: race,
    subrace: subrace,
    allocations: validateCreationDraftAllocations(value),
    persona: persona,
  };
  if (value.display_name !== undefined) {
    var displayName = value.display_name;
    if (typeof displayName !== "string" || !displayName) {
      throw new Error("proposal display_name must be non-empty text");
    }
    if (codePoints(displayName) > CREATION_MAX_PROPOSAL_NAME) {
      throw new Error("proposal display_name exceeds its bound");
    }
    checked.display_name = displayName;
  }
  if (value.age !== undefined) {
    checked.age = requireInt(value.age, "age", CREATION_AGE_MINIMUM, CREATION_AGE_MAXIMUM);
  }
  if (value.apparent_age !== undefined) {
    checked.apparent_age = requireInt(
      value.apparent_age,
      "apparent_age",
      CREATION_APPARENT_AGE_MINIMUM,
      CREATION_APPARENT_AGE_MAXIMUM
    );
  }
  if (value.background !== undefined) {
    var background = value.background;
    if (typeof background !== "string" || !background) {
      throw new Error("proposal background must be non-empty text");
    }
    if (codePoints(background) > CREATION_MAX_PERSONA_BACKGROUND) {
      throw new Error("proposal background exceeds its bound");
    }
    checked.background = background;
  }
  if (value.affinity_elements !== undefined) {
    var elements = value.affinity_elements;
    if (!Array.isArray(elements) || elements.length > CREATION_MAX_AFFINITY_ELEMENTS) {
      throw new Error(
        "proposal affinity_elements must be a list of at most " +
        CREATION_MAX_AFFINITY_ELEMENTS + " element keys"
      );
    }
    var seen = {};
    elements.forEach(function (entry) {
      if (CREATION_AFFINITY_ELEMENTS.indexOf(entry) === -1) {
        throw new Error("proposal affinity_elements has unknown element " + entry);
      }
      if (seen[entry]) {
        throw new Error("proposal affinity_elements duplicates element " + entry);
      }
      seen[entry] = true;
    });
    checked.affinity_elements = elements.slice();
  }
  return checked;
}

// The exact closed portrait union (mirror of _PORTRAIT_FIELDS): each status's
// required keys; nothing is optional or nullable.
var CREATION_PORTRAIT_FIELDS = {
  empty: ["status"],
  pending: ["status"],
  ready: ["status", "artwork"],
  failed: ["status", "reason"],
  unavailable: ["status", "reason"],
};

function validateCreationPortrait(value) {
  if (!isPlainObject(value)) {
    throw new Error("portrait must be an object");
  }
  var status = value.status;
  if (typeof status !== "string" || !Object.prototype.hasOwnProperty.call(CREATION_PORTRAIT_FIELDS, status)) {
    throw new Error("portrait status is not a known state");
  }
  requireExactFields(value, "portrait", CREATION_PORTRAIT_FIELDS[status], []);
  if (status === "ready") {
    return { status: status, artwork: artwork.validateArtwork(value.artwork) };
  }
  if (status === "failed" || status === "unavailable") {
    var reason = requireString(value.reason, "reason", CREATION_MAX_PORTRAIT_REASON);
    if (reason.trim() === "") {
      throw new Error("portrait reason must be non-empty");
    }
    return { status: status, reason: reason };
  }
  return { status: status };
}

function validateCreationPanel(payload) {
  requireExactFields(
    payload,
    "creation panel",
    ["schema_version", "available", "kind", "draft", "presets", "custom", "portrait"],
    ["proposal"]
  );
  requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
  if (payload.schema_version !== CREATION_SCHEMA_VERSION) {
    throw new Error("unsupported creation schema_version");
  }
  if (payload.available !== true || payload.kind !== "creation") {
    throw new Error("creation panel must be available with kind creation");
  }
  if (!Array.isArray(payload.presets) || payload.presets.length === 0 || payload.presets.length > CREATION_MAX_PRESETS) {
    throw new Error("presets must be a non-empty list within its bound");
  }
  validateCreationCustom(payload.custom);
  payload.presets.forEach(validateCreationPresetCard);
  var raceKeys = {};
  (payload.custom.races || []).forEach(function (r) {
    raceKeys[r.key] = true;
  });
  for (var i = 0; i < payload.presets.length; i++) {
    var card = payload.presets[i];
    if (!raceKeys[card.race]) {
      throw new Error("preset " + card.key + " references non-existent race " + card.race);
    }
  }
  var draft = validateCreationDraft(payload.draft);
  var portrait = validateCreationPortrait(payload.portrait);
  var result = {
    schema_version: CREATION_SCHEMA_VERSION,
    available: true,
    kind: "creation",
    draft: draft,
    presets: payload.presets,
    custom: payload.custom,
    portrait: portrait,
  };
  // The proposal key ships only while the session slot holds a proposal;
  // a null value is never legal (the presenter omits the key).
  if (payload.proposal !== undefined) {
    result.proposal = validateCreationProposal(payload.proposal);
  }
  // Envelope guarantee (design D2): per-field bounds are ceilings, not a
  // guarantee that any combination of them fits, so the validator enforces
  // the serialized byte size directly and fails closed over the envelope.
  if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
    throw new Error("creation payload exceeds the OOB envelope limit");
  }
  return result;
}

module.exports = {
  validateCreationPanel: validateCreationPanel,
  validateCreationPortrait: validateCreationPortrait,
  validateCreationPersona: validateCreationPersona,
  validateCreationProposal: validateCreationProposal,
};
