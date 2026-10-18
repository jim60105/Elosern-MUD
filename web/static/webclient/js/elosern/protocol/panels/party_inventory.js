"use strict";

// party_inventory panel validator (mirror of
// web.webclient.presentation.party_inventory, party-inventory-panel): the
// viewed member's equipment doll, aggregated bag rows with server-authored
// use/toggle/give descriptors, and the commander purse. Every descriptor is
// server-authored; the client never infers an enabled state.

var C = require("../constants.js");
var core = require("../core.js");

var jsonByteSize = core.jsonByteSize;
var codePoints = core.codePoints;
var requireExactFields = core.requireExactFields;
var requireInt = core.requireInt;
var requireBool = core.requireBool;
var requireString = core.requireString;
var hasLoneSurrogate = core.hasLoneSurrogate;

var MAX_SAFE_INTEGER = C.MAX_SAFE_INTEGER;
var MAX_CANONICAL_JSON_BYTES = C.MAX_CANONICAL_JSON_BYTES;
var PARTY_INVENTORY_SCHEMA_VERSION = C.PARTY_INVENTORY_SCHEMA_VERSION;
var PARTY_INVENTORY_MAX_ROWS = C.PARTY_INVENTORY_MAX_ROWS;
var PARTY_INVENTORY_MAX_KEY = C.PARTY_INVENTORY_MAX_KEY;
var PARTY_INVENTORY_MAX_DISPLAY_NAME = C.PARTY_INVENTORY_MAX_DISPLAY_NAME;
var PARTY_INVENTORY_MAX_PRESENTATION_KEY = C.PARTY_INVENTORY_MAX_PRESENTATION_KEY;
var PARTY_INVENTORY_MAX_PRESENTATION_SUMMARY =
  C.PARTY_INVENTORY_MAX_PRESENTATION_SUMMARY;
var PARTY_INVENTORY_MAX_REASON = C.PARTY_INVENTORY_MAX_REASON;
var PARTY_INVENTORY_ACCESSORY_LIMIT = C.PARTY_INVENTORY_ACCESSORY_LIMIT;

var USE_ROUTES = ["field_use", "combat_draft"];
var TOGGLE_ROUTES = ["toggle"];
var SLOT_NAMES = ["weapon_main", "weapon_off", "armor", "accessory"];

function requirePresentationKey(value, field) {
  if (
    typeof value !== "string" ||
    value.length < 1 ||
    codePoints(value) > PARTY_INVENTORY_MAX_PRESENTATION_KEY ||
    !/^[a-z_]+$/.test(value)
  ) {
    throw new Error(
      field +
        " must be 1.." +
        PARTY_INVENTORY_MAX_PRESENTATION_KEY +
        " lowercase ASCII letters or underscores"
    );
  }
  return value;
}

function validatePresentation(value) {
  if (value === null) {
    return null;
  }
  requireExactFields(
    value,
    "presentation",
    ["kind", "icon_key", "rarity", "summary"],
    []
  );
  var kind = requirePresentationKey(value.kind, "presentation.kind");
  var iconKey = requirePresentationKey(value.icon_key, "presentation.icon_key");
  var rarity = requirePresentationKey(value.rarity, "presentation.rarity");
  var summary = value.summary;
  if (typeof summary !== "string") {
    throw new Error("presentation.summary must be a string");
  }
  if (
    codePoints(summary) < 1 ||
    codePoints(summary) > PARTY_INVENTORY_MAX_PRESENTATION_SUMMARY
  ) {
    throw new Error(
      "presentation.summary must be 1.." +
        PARTY_INVENTORY_MAX_PRESENTATION_SUMMARY +
        " Unicode code points"
    );
  }
  return {
    kind: kind,
    icon_key: iconKey,
    rarity: rarity,
    summary: summary,
  };
}

function validateReason(value, name) {
  var reason = value.reason;
  if (reason === null) {
    return null;
  }
  reason = requireString(reason, "reason", PARTY_INVENTORY_MAX_REASON);
  if (reason.trim().length === 0 || hasLoneSurrogate(reason)) {
    throw new Error(name + " reason must be a non-empty bounded string");
  }
  return reason;
}

function validateDescriptor(value, name, routes) {
  requireExactFields(value, name, ["route", "enabled", "reason"], []);
  if (routes.indexOf(value.route) === -1) {
    throw new Error(name + " route must be one of " + routes.join(","));
  }
  var enabled = requireBool(value.enabled, name + " enabled");
  var reason = validateReason(value, name);
  if (enabled && reason !== null) {
    throw new Error("an enabled " + name + " carries no reason");
  }
  if (!enabled && reason === null) {
    throw new Error("a disabled " + name + " carries its reason");
  }
  return { route: value.route, enabled: enabled, reason: reason };
}

function validateGive(value) {
  requireExactFields(value, "give", ["enabled", "reason", "max_quantity"], []);
  var enabled = requireBool(value.enabled, "give enabled");
  var reason = validateReason(value, "give");
  var maxQuantity = requireInt(
    value.max_quantity,
    "give max_quantity",
    0,
    MAX_SAFE_INTEGER
  );
  if (enabled && reason !== null) {
    throw new Error("an enabled give carries no reason");
  }
  if (!enabled && reason === null) {
    throw new Error("a disabled give carries its reason");
  }
  return { enabled: enabled, reason: reason, max_quantity: maxQuantity };
}

function validateSlotKey(value, field) {
  if (value === null) {
    return null;
  }
  requireString(value, field, PARTY_INVENTORY_MAX_KEY);
  if (codePoints(value) < 1 || value.trim().length === 0) {
    throw new Error(field + " must be a non-empty string or null");
  }
  if (hasLoneSurrogate(value)) {
    throw new Error(field + " must not carry lone surrogates");
  }
  return value;
}

function validateDisplayName(value) {
  if (typeof value !== "string") {
    throw new Error("display_name must be a string");
  }
  if (
    codePoints(value) < 1 ||
    codePoints(value) > PARTY_INVENTORY_MAX_DISPLAY_NAME
  ) {
    throw new Error(
      "display_name must be 1.." +
        PARTY_INVENTORY_MAX_DISPLAY_NAME +
        " characters"
    );
  }
  if (value.trim().length === 0) {
    throw new Error("display_name must be non-empty");
  }
  if (hasLoneSurrogate(value)) {
    throw new Error("display_name must not carry lone surrogates");
  }
  return value;
}

function validateEquipment(value) {
  requireExactFields(
    value,
    "equipment",
    ["weapon_main", "weapon_off", "armor", "accessories", "accessory_limit"],
    []
  );
  var slots = {
    weapon_main: validateSlotKey(value.weapon_main, "equipment.weapon_main"),
    weapon_off: validateSlotKey(value.weapon_off, "equipment.weapon_off"),
    armor: validateSlotKey(value.armor, "equipment.armor"),
  };
  if (!Array.isArray(value.accessories)) {
    throw new Error("equipment.accessories must be a list");
  }
  if (value.accessories.length > PARTY_INVENTORY_ACCESSORY_LIMIT) {
    throw new Error("equipment.accessories exceeds the accessory cap");
  }
  var accessories = [];
  value.accessories.forEach(function (entry, index) {
    var key = validateSlotKey(entry, "equipment.accessories[" + index + "]");
    if (key === null) {
      throw new Error("equipment.accessories entries must be item keys");
    }
    if (accessories.indexOf(key) !== -1) {
      throw new Error("equipment.accessories must not repeat a key");
    }
    accessories.push(key);
  });
  var limit = requireInt(
    value.accessory_limit,
    "equipment.accessory_limit",
    PARTY_INVENTORY_ACCESSORY_LIMIT,
    PARTY_INVENTORY_ACCESSORY_LIMIT
  );
  var worn = ["weapon_main", "weapon_off", "armor"]
    .map(function (field) {
      return slots[field];
    })
    .filter(function (key) {
      return key !== null;
    });
  var seen = Object.create(null);
  worn.concat(accessories).forEach(function (key) {
    if (seen[key]) {
      throw new Error("equipment keys must occupy exactly one slot");
    }
    seen[key] = true;
  });
  return {
    weapon_main: slots.weapon_main,
    weapon_off: slots.weapon_off,
    armor: slots.armor,
    accessories: accessories,
    accessory_limit: limit,
  };
}

function wornSlots(equipment) {
  var worn = Object.create(null);
  ["weapon_main", "weapon_off", "armor"].forEach(function (field) {
    if (equipment[field] !== null) {
      worn[equipment[field]] = field;
    }
  });
  equipment.accessories.forEach(function (key) {
    worn[key] = "accessory";
  });
  return worn;
}

function validateRow(value, name, worn, seen) {
  requireExactFields(
    value,
    name,
    [
      "item_key",
      "display_name",
      "held",
      "equipped_count",
      "slot",
      "presentation",
      "use",
      "toggle",
      "give",
    ],
    []
  );
  var itemKey = validateSlotKey(value.item_key, name + ".item_key");
  if (itemKey === null) {
    throw new Error(name + ".item_key must be non-null");
  }
  if (seen[itemKey]) {
    throw new Error(name + ".item_key must be unique");
  }
  seen[itemKey] = true;
  var displayName = validateDisplayName(value.display_name);
  var held = requireInt(value.held, name + ".held", 1, MAX_SAFE_INTEGER);
  var equippedCount = requireInt(
    value.equipped_count,
    name + ".equipped_count",
    0,
    1
  );
  var slot = value.slot;
  if (slot !== null && SLOT_NAMES.indexOf(slot) === -1) {
    throw new Error(name + ".slot must be null or a known slot name");
  }
  var use =
    value.use === null
      ? null
      : validateDescriptor(value.use, name + ".use", USE_ROUTES);
  var toggle =
    value.toggle === null
      ? null
      : validateDescriptor(value.toggle, name + ".toggle", TOGGLE_ROUTES);
  var give = validateGive(value.give);
  if ((slot === null) !== (toggle === null)) {
    throw new Error(name + " must carry a toggle exactly when it has a slot");
  }
  var expectedSlot = worn[itemKey];
  if (expectedSlot === undefined) {
    if (equippedCount !== 0) {
      throw new Error(name + " is not worn but reports equipped state");
    }
  } else if (equippedCount !== 1 || slot !== expectedSlot) {
    throw new Error(name + " equipped state must match the equipment section");
  }
  return {
    item_key: itemKey,
    display_name: displayName,
    held: held,
    equipped_count: equippedCount,
    slot: slot,
    presentation: validatePresentation(value.presentation),
    use: use,
    toggle: toggle,
    give: give,
  };
}

function validatePartyInventoryPanel(payload) {
  requireExactFields(
    payload,
    "party_inventory panel",
    [
      "schema_version",
      "available",
      "kind",
      "member_id",
      "purse",
      "equipment",
      "rows",
    ],
    []
  );
  requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
  if (payload.schema_version !== PARTY_INVENTORY_SCHEMA_VERSION) {
    throw new Error("unsupported party_inventory schema_version");
  }
  if (payload.available !== true) {
    throw new Error("party_inventory panel must be available");
  }
  if (payload.kind !== "party_inventory") {
    throw new Error("kind must be 'party_inventory'");
  }
  var memberId = requireInt(
    payload.member_id,
    "member_id",
    1,
    MAX_SAFE_INTEGER
  );
  var purse = requireInt(payload.purse, "purse", 0, MAX_SAFE_INTEGER);
  var equipment = validateEquipment(payload.equipment);
  if (!Array.isArray(payload.rows)) {
    throw new Error("rows must be a list");
  }
  if (payload.rows.length > PARTY_INVENTORY_MAX_ROWS) {
    throw new Error(
      "rows must hold at most " + PARTY_INVENTORY_MAX_ROWS + " entries"
    );
  }
  var worn = wornSlots(equipment);
  var seen = Object.create(null);
  var rows = payload.rows.map(function (row, index) {
    return validateRow(row, "row " + (index + 1), worn, seen);
  });
  var result = {
    schema_version: PARTY_INVENTORY_SCHEMA_VERSION,
    available: true,
    kind: "party_inventory",
    member_id: memberId,
    purse: purse,
    equipment: equipment,
    rows: rows,
  };
  if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
    throw new Error("party_inventory payload exceeds the OOB envelope limit");
  }
  return result;
}

module.exports = {
  validatePartyInventoryPanel: validatePartyInventoryPanel,
  PARTY_INVENTORY_SCHEMA_VERSION: PARTY_INVENTORY_SCHEMA_VERSION,
  PARTY_INVENTORY_MAX_ROWS: PARTY_INVENTORY_MAX_ROWS,
  PARTY_INVENTORY_MAX_KEY: PARTY_INVENTORY_MAX_KEY,
  PARTY_INVENTORY_MAX_DISPLAY_NAME: PARTY_INVENTORY_MAX_DISPLAY_NAME,
  PARTY_INVENTORY_MAX_PRESENTATION_KEY: PARTY_INVENTORY_MAX_PRESENTATION_KEY,
  PARTY_INVENTORY_MAX_PRESENTATION_SUMMARY:
    PARTY_INVENTORY_MAX_PRESENTATION_SUMMARY,
  PARTY_INVENTORY_MAX_REASON: PARTY_INVENTORY_MAX_REASON,
  PARTY_INVENTORY_ACCESSORY_LIMIT: PARTY_INVENTORY_ACCESSORY_LIMIT,
};
