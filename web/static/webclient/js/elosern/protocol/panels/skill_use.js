"use strict";

// skill_use panel (mirror of web.webclient.presentation.skill_use,
// skillbook-authoritative-casting D2): the on-demand SkillBook use preview of
// one owned active skill at one selected scale. The browser re-checks the
// exact version-1 form, unique bounded identities, the opening line-up cross
// references, and the enabled/disabled_reason pairing before any renderer
// observes it; a malformed panel never authorizes a cast.

var C = require("../constants.js");
var core = require("../core.js");

var requireExactFields = core.requireExactFields;
var requireInt = core.requireInt;
var requireBool = core.requireBool;
var requireString = core.requireString;
var validateIdentifier = core.validateIdentifier;
var MAX_SAFE_INTEGER = C.MAX_SAFE_INTEGER;

var SKILL_USE_SCHEMA_VERSION = 1;
var SKILL_USE_MAX_CHOICES = 64;
var SKILL_USE_MAX_LABEL = 128;
var SKILL_USE_MAX_DESCRIPTION = 512;
var SKILL_USE_MAX_COST_KEYS = 8;
var SKILL_USE_MAX_REASON_CODE = 64;
var SKILL_USE_MAX_REASON_MESSAGE = 512;
var SKILL_USE_TARGET_SPECS = ["none", "self", "single", "area"];

function label(value, name) {
  var text = requireString(value, name + " label", SKILL_USE_MAX_LABEL);
  if (!text.trim()) {
    throw new Error(name + " label must be non-empty");
  }
  return text;
}

function reasonPair(enabled, reason, name) {
  if (reason === null) {
    if (!enabled) {
      throw new Error("a disabled " + name + " requires a disabled_reason");
    }
    return;
  }
  if (enabled) {
    throw new Error("an enabled " + name + " must not carry a disabled_reason");
  }
  requireExactFields(reason, "disabled_reason", ["code", "message"], []);
  validateIdentifier(reason.code, "disabled_reason code");
  if (reason.code.length > SKILL_USE_MAX_REASON_CODE) {
    throw new Error("disabled_reason code exceeds its bound");
  }
  var message = requireString(reason.message, "disabled_reason message", SKILL_USE_MAX_REASON_MESSAGE);
  if (!message.trim()) {
    throw new Error("disabled_reason message must be non-empty");
  }
}

function choices(value, name, opening) {
  if (!Array.isArray(value) || value.length > SKILL_USE_MAX_CHOICES) {
    throw new Error(name + " must be a list of at most " + SKILL_USE_MAX_CHOICES);
  }
  var fields = ["identity", "label", "enabled", "disabled_reason"];
  if (opening) {
    fields = fields.concat(["target_ids"]);
  }
  var seen = Object.create(null);
  value.forEach(function (entry) {
    requireExactFields(entry, name, fields, []);
    var identity = requireInt(entry.identity, name + " identity", 1, MAX_SAFE_INTEGER);
    if (seen[identity]) {
      throw new Error(name + " identities must be unique");
    }
    seen[identity] = true;
    label(entry.label, name);
    var enabled = requireBool(entry.enabled, name + " enabled");
    reasonPair(enabled, entry.disabled_reason, name);
    if (opening) {
      var ids = entry.target_ids;
      if (!Array.isArray(ids) || ids.length < 1 || ids.length > SKILL_USE_MAX_CHOICES) {
        throw new Error("opening target_ids must hold 1..64 identities");
      }
      var unique = Object.create(null);
      ids.forEach(function (item) {
        requireInt(item, "opening target id", 1, MAX_SAFE_INTEGER);
        if (unique[item]) {
          throw new Error("opening target_ids must be unique");
        }
        unique[item] = true;
      });
      if (!unique[identity]) {
        throw new Error("an opening's target_ids must include its anchor");
      }
    }
  });
  return value;
}

// Shape-only rung check: the panel's `cost` is the modifier-adjusted
// selected-scale amount, so rung costs cannot be cross-checked against it;
// the server validator checks them against the registry base cost.
function freeformScales(value) {
  if (value === undefined) {
    return;
  }
  if (!Array.isArray(value) || value.length === 0 || value.length > C.FREEFORM_SCALES_MAX) {
    throw new Error("freeform_scales must be a non-empty bounded array when present");
  }
  value.forEach(function (entry, index) {
    requireExactFields(entry, "freeform_scales entry", ["scale", "label", "mp_cost"], []);
    if (entry.scale !== C.FREEFORM_SCALES_ALLOWED[index]) {
      throw new Error("freeform_scales must be ascending over the allowed scale set");
    }
    if (entry.label !== C.FREEFORM_LABELS_ALLOWED[index]) {
      throw new Error("freeform_scales label must be the canonical label of its scale");
    }
    requireInt(entry.mp_cost, "freeform_scales mp_cost", 1, MAX_SAFE_INTEGER);
  });
}

function validateSkillUsePanel(payload) {
  requireExactFields(payload, "skill_use", ["schema_version", "available", "kind", "skill", "scale"], []);
  if (payload.schema_version !== 1) {
    throw new Error("skill_use schema_version mismatch");
  }
  if (payload.available !== true || payload.kind !== "skill_use") {
    throw new Error("skill_use available form discriminator mismatch");
  }
  if (payload.scale !== 1 && C.FREEFORM_SCALES_ALLOWED.indexOf(payload.scale) === -1) {
    throw new Error("skill_use scale must be a member of the closed scale set");
  }
  var skill = payload.skill;
  requireExactFields(
    skill,
    "skill_use skill",
    ["key", "label", "description", "target_spec", "usable_out_of_combat", "cost", "enabled", "disabled_reason", "targets", "openings"],
    ["freeform_scales"]
  );
  validateIdentifier(skill.key, "skill key");
  label(skill.label, "skill");
  var description = requireString(skill.description, "skill description", SKILL_USE_MAX_DESCRIPTION);
  if (!description.trim()) {
    throw new Error("skill description must be non-empty");
  }
  if (SKILL_USE_TARGET_SPECS.indexOf(skill.target_spec) === -1) {
    throw new Error("skill target_spec is not a stable value");
  }
  requireBool(skill.usable_out_of_combat, "skill usable_out_of_combat");
  if (!core.isPlainObject(skill.cost) || Object.keys(skill.cost).length > SKILL_USE_MAX_COST_KEYS) {
    throw new Error("skill cost must be a bounded object");
  }
  Object.keys(skill.cost).forEach(function (resource) {
    validateIdentifier(resource, "cost resource key");
    requireInt(skill.cost[resource], "skill cost amount", 0, MAX_SAFE_INTEGER);
  });
  var enabled = requireBool(skill.enabled, "skill enabled");
  reasonPair(enabled, skill.disabled_reason, "skill");
  var targets = choices(skill.targets, "target", false);
  var openings = choices(skill.openings, "opening", true);
  var spec = skill.target_spec;
  if (spec === "none" && targets.length > 0) {
    throw new Error("a NONE skill carries no targets");
  }
  if (spec === "self" && targets.length !== 1) {
    throw new Error("a SELF skill carries exactly the actor binding");
  }
  if ((spec === "none" || spec === "self") && openings.length > 0) {
    throw new Error("NONE/SELF skills carry no monster openings");
  }
  var anchors = Object.create(null);
  openings.forEach(function (row) {
    anchors[row.identity] = true;
  });
  targets.forEach(function (row) {
    if (anchors[row.identity]) {
      throw new Error("a monster opening is never an ordinary target");
    }
  });
  openings.forEach(function (row) {
    row.target_ids.forEach(function (id) {
      if (!anchors[id]) {
        throw new Error("an opening line-up must name advertised monsters");
      }
    });
    if (spec === "single" && (row.target_ids.length !== 1 || row.target_ids[0] !== row.identity)) {
      throw new Error("a SINGLE opening engages its anchor alone");
    }
  });
  if (spec === "single" || spec === "area") {
    var anyChoice = targets.concat(openings).some(function (row) {
      return row.enabled;
    });
    if (anyChoice !== enabled) {
      throw new Error("skill enabled must equal the existence of a legal choice");
    }
  } else if (spec === "self" && targets[0].enabled !== enabled) {
    throw new Error("a SELF binding must match the skill verdict");
  }
  freeformScales(skill.freeform_scales);
  return payload;
}

module.exports = {
  SKILL_USE_SCHEMA_VERSION: SKILL_USE_SCHEMA_VERSION,
  SKILL_USE_MAX_CHOICES: SKILL_USE_MAX_CHOICES,
  validateSkillUsePanel: validateSkillUsePanel,
};
