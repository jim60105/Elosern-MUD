"use strict";

var C = require("../constants.js");
var core = require("../core.js");

var isPlainObject = core.isPlainObject;
var codePoints = core.codePoints;
var jsonByteSize = core.jsonByteSize;
var requireExactFields = core.requireExactFields;
var requireInt = core.requireInt;
var requireBool = core.requireBool;
var requireString = core.requireString;
var validateIdentifier = core.validateIdentifier;

var MAX_SAFE_INTEGER = C.MAX_SAFE_INTEGER;
var MAX_CANONICAL_JSON_BYTES = C.MAX_CANONICAL_JSON_BYTES;
var SERVICES_MAX_BOARD_ROWS = C.SERVICES_MAX_BOARD_ROWS;
var SERVICES_MAX_QUEST_ROWS = C.SERVICES_MAX_QUEST_ROWS;
var SERVICES_MAX_STOCK_ROWS = C.SERVICES_MAX_STOCK_ROWS;
var SERVICES_MAX_SELLABLE_ROWS = C.SERVICES_MAX_SELLABLE_ROWS;
var SERVICES_MAX_INVENTORY_ROWS = C.SERVICES_MAX_INVENTORY_ROWS;
var SERVICES_MAX_KEY = C.SERVICES_MAX_KEY;
var SERVICES_MAX_DISPLAY_NAME = C.SERVICES_MAX_DISPLAY_NAME;
var SERVICES_MAX_SUMMARY = C.SERVICES_MAX_SUMMARY;
var SERVICES_MAX_DETAIL = C.SERVICES_MAX_DETAIL;
var SERVICES_MAX_DEADLINE_LINE = C.SERVICES_MAX_DEADLINE_LINE;
var SERVICES_MAX_RANK_KEY = C.SERVICES_MAX_RANK_KEY;
var SERVICES_MAX_HOST_DISPLAY_NAME = C.SERVICES_MAX_HOST_DISPLAY_NAME;
var SERVICES_MAX_LABEL = C.SERVICES_MAX_LABEL;
var SERVICES_MAX_REASON_MESSAGE = C.SERVICES_MAX_REASON_MESSAGE;
var SERVICES_MAX_QUANTITY = C.SERVICES_MAX_QUANTITY;
var SERVICES_MIN_QUANTITY = C.SERVICES_MIN_QUANTITY;
var SERVICES_MAX_PRESENTATION_KEY = C.SERVICES_MAX_PRESENTATION_KEY;
var SERVICES_MAX_PRESENTATION_SUMMARY = C.SERVICES_MAX_PRESENTATION_SUMMARY;
var SERVICES_QUEST_STATES = C.SERVICES_QUEST_STATES;
var SERVICES_ACTIONS = C.SERVICES_ACTIONS;
var SERVICES_BUY = C.SERVICES_BUY;
var SERVICES_SELL = C.SERVICES_SELL;

// -------------------------------------------------------------------------
// services panel validator (mirror of web.webclient.presentation.services,
// design D4). Shared bounds are guarded by a dual-direction parity test.
// -------------------------------------------------------------------------

function validateServicesAction(value) {
  requireExactFields(
    value,
    "service action",
    ["action_id", "label", "enabled", "disabled_reason", "quantity"],
    []
  );
  validateIdentifier(value.action_id, "action_id");
  if (SERVICES_ACTIONS.indexOf(value.action_id) === -1) {
    throw new Error("service action_id is not a registered service action");
  }
  var label = requireString(value.label, "label", SERVICES_MAX_LABEL);
  if (!label.trim()) {
    throw new Error("action label must be non-empty");
  }
  var enabled = requireBool(value.enabled, "enabled");
  var disabledReason = value.disabled_reason;
  if (disabledReason === null) {
    if (!enabled) {
      throw new Error("a disabled action requires a disabled_reason");
    }
  } else {
    requireExactFields(
      disabledReason,
      "disabled_reason",
      ["code", "message"],
      []
    );
    validateIdentifier(disabledReason.code, "disabled_reason code");
    var message = requireString(
      disabledReason.message,
      "disabled_reason message",
      SERVICES_MAX_REASON_MESSAGE
    );
    if (!message.trim()) {
      throw new Error("disabled_reason message must be non-empty");
    }
    if (enabled) {
      throw new Error("an enabled action must not carry a disabled_reason");
    }
  }
  var quantity = value.quantity;
  if (quantity === null) {
    if (
      enabled &&
      (value.action_id === SERVICES_BUY || value.action_id === SERVICES_SELL)
    ) {
      throw new Error("a buy/sell action requires quantity bounds");
    }
  } else {
    if (
      value.action_id !== SERVICES_BUY &&
      value.action_id !== SERVICES_SELL
    ) {
      throw new Error("only buy/sell actions may carry quantity bounds");
    }
    requireExactFields(quantity, "quantity bounds", ["min", "max"], []);
    var minimum = requireInt(
      quantity.min,
      "quantity.min",
      SERVICES_MIN_QUANTITY,
      SERVICES_MAX_QUANTITY
    );
    var maximum = requireInt(
      quantity.max,
      "quantity.max",
      SERVICES_MIN_QUANTITY,
      SERVICES_MAX_QUANTITY
    );
    if (minimum > maximum) {
      throw new Error("quantity min must not exceed max");
    }
  }
  return value;
}

function validateServicesRegistration(value) {
  requireExactFields(value, "registration", ["registered", "register"], []);
  var registered = requireBool(value.registered, "registered");
  var register = validateServicesAction(value.register);
  if (register.action_id !== "guild.register") {
    throw new Error("registration.register must be guild.register");
  }
  if (registered === register.enabled) {
    throw new Error(
      "registration.register enabled state must contradict registered"
    );
  }
  return value;
}

function validateServicesBoardRow(value) {
  requireExactFields(
    value,
    "board row",
    ["definition_key", "display_name", "objective_summary", "reward_summary", "rank", "accept"],
    []
  );
  var definitionKey = requireString(value.definition_key, "definition_key", SERVICES_MAX_KEY);
  if (!definitionKey.trim()) {
    throw new Error("board definition_key must be non-empty");
  }
  var boardDisplayName = requireString(value.display_name, "display_name", SERVICES_MAX_DISPLAY_NAME);
  if (!boardDisplayName.trim()) {
    throw new Error("board display_name must be non-empty");
  }
  var objectiveSummary = requireString(value.objective_summary, "objective_summary", SERVICES_MAX_SUMMARY);
  if (!objectiveSummary.trim()) {
    throw new Error("board objective_summary must be non-empty");
  }
  var rewardSummary = requireString(value.reward_summary, "reward_summary", SERVICES_MAX_SUMMARY);
  if (!rewardSummary.trim()) {
    throw new Error("board reward_summary must be non-empty");
  }
  var boardRank = requireString(value.rank, "rank", SERVICES_MAX_RANK_KEY);
  if (!boardRank.trim()) {
    throw new Error("board rank must be non-empty");
  }
  var accept = validateServicesAction(value.accept);
  if (accept.action_id !== "guild.quest_accept") {
    throw new Error("board accept must be guild.quest_accept");
  }
  return value;
}

function validateServicesQuestRow(value) {
  requireExactFields(
    value,
    "quest row",
    [
      "quest_id",
      "definition_key",
      "display_name",
      "state",
      "stage_index",
      "stage_progress",
      "objective_summary",
      "deadline_line",
      "detail",
      "abandon",
      "turnin",
      "tracked",
    ],
    []
  );
  var questId = requireString(value.quest_id, "quest_id", SERVICES_MAX_KEY);
  if (!questId.trim()) {
    throw new Error("quest_id must be non-empty");
  }
  var questDefinitionKey = requireString(value.definition_key, "definition_key", SERVICES_MAX_KEY);
  if (!questDefinitionKey.trim()) {
    throw new Error("quest definition_key must be non-empty");
  }
  var questDisplayName = requireString(value.display_name, "display_name", SERVICES_MAX_DISPLAY_NAME);
  if (!questDisplayName.trim()) {
    throw new Error("quest display_name must be non-empty");
  }
  if (SERVICES_QUEST_STATES.indexOf(value.state) === -1) {
    throw new Error("quest state is not a stable value");
  }
  requireInt(value.stage_index, "stage_index", 0, MAX_SAFE_INTEGER);
  requireInt(value.stage_progress, "stage_progress", 0, MAX_SAFE_INTEGER);
  var questObjective = requireString(value.objective_summary, "objective_summary", SERVICES_MAX_SUMMARY);
  if (!questObjective.trim()) {
    throw new Error("quest objective_summary must be non-empty");
  }
  if (value.deadline_line !== null) {
    var deadline = requireString(
      value.deadline_line,
      "deadline_line",
      SERVICES_MAX_DEADLINE_LINE
    );
    if (!deadline.trim()) {
      throw new Error("deadline_line must be non-empty when set");
    }
  }
  var detail = requireString(value.detail, "detail", SERVICES_MAX_DETAIL);
  if (!detail.trim()) {
    throw new Error("quest detail must be non-empty");
  }
  var abandon = validateServicesAction(value.abandon);
  var turnin = validateServicesAction(value.turnin);
  if (abandon.action_id !== "guild.quest_abandon") {
    throw new Error("quest abandon must be guild.quest_abandon");
  }
  if (turnin.action_id !== "guild.quest_turnin") {
    throw new Error("quest turnin must be guild.quest_turnin");
  }
  requireBool(value.tracked, "tracked");
  return value;
}

function validateServicesRank(value) {
  requireExactFields(
    value,
    "rank",
    ["rank", "merit", "next_rank", "next_threshold", "eligible", "exam_start"],
    []
  );
  if (value.rank !== null) {
    var rankKey = requireString(value.rank, "rank", SERVICES_MAX_RANK_KEY);
    if (!rankKey.trim()) {
      throw new Error("rank must be non-empty when set");
    }
  }
  requireInt(value.merit, "merit", 0, MAX_SAFE_INTEGER);
  if (value.next_rank !== null) {
    requireString(value.next_rank, "next_rank", SERVICES_MAX_RANK_KEY);
  }
  if (value.next_threshold !== null) {
    requireInt(value.next_threshold, "next_threshold", 1, MAX_SAFE_INTEGER);
  }
  if ((value.next_rank === null) !== (value.next_threshold === null)) {
    throw new Error(
      "next_rank and next_threshold must both be set or null"
    );
  }
  var eligible = requireBool(value.eligible, "eligible");
  var examStart = validateServicesAction(value.exam_start);
  if (examStart.action_id !== "guild.exam_start") {
    throw new Error("rank exam_start must be guild.exam_start");
  }
  if (eligible !== examStart.enabled) {
    throw new Error("rank eligible must match exam_start enabled");
  }
  return value;
}

function validateServicesGuild(value) {
  requireExactFields(value, "guild", ["registration", "board", "quests", "rank"], []);
  validateServicesRegistration(value.registration);
  if (!Array.isArray(value.board) || value.board.length > SERVICES_MAX_BOARD_ROWS) {
    throw new Error("board must be a list of at most " + SERVICES_MAX_BOARD_ROWS + " rows");
  }
  value.board.forEach(validateServicesBoardRow);
  if (!Array.isArray(value.quests) || value.quests.length > SERVICES_MAX_QUEST_ROWS) {
    throw new Error("quests must be a list of at most " + SERVICES_MAX_QUEST_ROWS + " rows");
  }
  value.quests.forEach(validateServicesQuestRow);
  if (value.rank !== null) {
    validateServicesRank(value.rank);
  }
  return value;
}

function validateServicesStockRow(value) {
  requireExactFields(
    value,
    "stock row",
    ["item_key", "display_name", "buy_copper", "sell_copper", "stock", "max_stock", "buy"],
    []
  );
  var stockItemKey = requireString(value.item_key, "item_key", SERVICES_MAX_KEY);
  if (!stockItemKey.trim()) {
    throw new Error("stock item_key must be non-empty");
  }
  var stockDisplayName = requireString(value.display_name, "display_name", SERVICES_MAX_DISPLAY_NAME);
  if (!stockDisplayName.trim()) {
    throw new Error("stock display_name must be non-empty");
  }
  requireInt(value.buy_copper, "buy_copper", 0, MAX_SAFE_INTEGER);
  requireInt(value.sell_copper, "sell_copper", 0, MAX_SAFE_INTEGER);
  requireInt(value.stock, "stock", 0, MAX_SAFE_INTEGER);
  requireInt(value.max_stock, "max_stock", 1, MAX_SAFE_INTEGER);
  var buy = validateServicesAction(value.buy);
  if (buy.action_id !== SERVICES_BUY) {
    throw new Error("stock buy must be shop.buy");
  }
  return value;
}

function validateServicesSellableRow(value) {
  requireExactFields(
    value,
    "sellable row",
    ["item_key", "display_name", "sell_copper", "held", "sell"],
    []
  );
  var sellableItemKey = requireString(value.item_key, "item_key", SERVICES_MAX_KEY);
  if (!sellableItemKey.trim()) {
    throw new Error("sellable item_key must be non-empty");
  }
  var sellableDisplayName = requireString(value.display_name, "display_name", SERVICES_MAX_DISPLAY_NAME);
  if (!sellableDisplayName.trim()) {
    throw new Error("sellable display_name must be non-empty");
  }
  requireInt(value.sell_copper, "sell_copper", 0, MAX_SAFE_INTEGER);
  requireInt(value.held, "held", 1, MAX_SAFE_INTEGER);
  var sell = validateServicesAction(value.sell);
  if (sell.action_id !== SERVICES_SELL) {
    throw new Error("sellable sell must be shop.sell");
  }
  return value;
}

function validateServicesShop(value) {
  requireExactFields(value, "shop", ["open", "stock", "sellable"], []);
  requireBool(value.open, "open");
  if (!Array.isArray(value.stock) || value.stock.length > SERVICES_MAX_STOCK_ROWS) {
    throw new Error("stock must be a list of at most " + SERVICES_MAX_STOCK_ROWS + " rows");
  }
  value.stock.forEach(validateServicesStockRow);
  if (
    !Array.isArray(value.sellable) ||
    value.sellable.length > SERVICES_MAX_SELLABLE_ROWS
  ) {
    throw new Error(
      "sellable must be a list of at most " + SERVICES_MAX_SELLABLE_ROWS + " rows"
    );
  }
  value.sellable.forEach(validateServicesSellableRow);
  return value;
}

function requirePresentationKey(value, field) {
  if (
    typeof value !== "string" ||
    value.length < 1 ||
    value.length > SERVICES_MAX_PRESENTATION_KEY ||
    !/^[a-z_]+$/.test(value)
  ) {
    throw new Error(
      field + " must be 1.." + SERVICES_MAX_PRESENTATION_KEY + " lowercase ASCII letters or underscores"
    );
  }
  return value;
}

function requirePresentation(value, field) {
  if (value === null) {
    return null;
  }
  if (!isPlainObject(value)) {
    throw new Error(field + " must be a JSON object or null");
  }
  requireExactFields(value, field, ["kind", "icon_key", "rarity", "summary"], []);
  var kind = requirePresentationKey(value.kind, field + ".kind");
  var iconKey = requirePresentationKey(value.icon_key, field + ".icon_key");
  var rarity = requirePresentationKey(value.rarity, field + ".rarity");
  var summary = value.summary;
  if (typeof summary !== "string") {
    throw new Error(field + ".summary must be a string");
  }
  if (codePoints(summary) < 1 || codePoints(summary) > SERVICES_MAX_PRESENTATION_SUMMARY) {
    throw new Error(
      field + ".summary must be 1.." + SERVICES_MAX_PRESENTATION_SUMMARY + " Unicode code points"
    );
  }
  return value;
}

function validateServicesInventory(value) {
  requireExactFields(value, "inventory", ["rows", "wallet"], []);
  var rows = value.rows;
  if (!Array.isArray(rows) || rows.length > SERVICES_MAX_INVENTORY_ROWS) {
    throw new Error(
      "inventory rows must be a list of at most " + SERVICES_MAX_INVENTORY_ROWS + " entries"
    );
  }
  requireInt(value.wallet, "wallet", 0, MAX_SAFE_INTEGER);
  rows.forEach(function (row) {
    requireExactFields(
      row,
      "inventory row",
      [
        "item_key",
        "display_name",
        "held",
        "equipped",
        "presentation",
        "action",
      ],
      []
    );
    var inventoryItemKey = requireString(row.item_key, "item_key", SERVICES_MAX_KEY);
    if (!inventoryItemKey.trim()) {
      throw new Error("inventory item_key must be non-empty");
    }
    var inventoryDisplayName = requireString(row.display_name, "display_name", SERVICES_MAX_DISPLAY_NAME);
    if (!inventoryDisplayName.trim()) {
      throw new Error("inventory display_name must be non-empty");
    }
    requireInt(row.held, "held", 1, MAX_SAFE_INTEGER);
    requireBool(row.equipped, "equipped");
    requirePresentation(row.presentation, "inventory row.presentation");
    if (row.action !== null) {
      validateServicesAction(row.action);
      if (
        row.action.action_id !== "inventory.use" &&
        row.action.action_id !== "inventory.toggle_equip"
      ) {
        throw new Error("inventory row action id is not allowed");
      }
    }
  });
  return value;
}

function validateServicesPagination(value) {
  requireExactFields(
    value,
    "pagination",
    ["board_total", "quest_total", "stock_total", "sellable_total", "inventory_total"],
    []
  );
  requireInt(value.board_total, "board_total", 0, SERVICES_MAX_BOARD_ROWS);
  requireInt(value.quest_total, "quest_total", 0, SERVICES_MAX_QUEST_ROWS);
  requireInt(value.stock_total, "stock_total", 0, SERVICES_MAX_STOCK_ROWS);
  requireInt(value.sellable_total, "sellable_total", 0, SERVICES_MAX_SELLABLE_ROWS);
  requireInt(value.inventory_total, "inventory_total", 0, SERVICES_MAX_INVENTORY_ROWS);
  return value;
}

// Exact available services panel v2 schema (design D4).
function validateServicesPanel(payload) {
  requireExactFields(
    payload,
    "services panel",
    [
      "schema_version",
      "available",
      "kind",
      "host",
      "player",
      "guild",
      "shop",
      "inventory",
      "pagination",
    ],
    []
  );
  requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
  if (payload.schema_version !== 4) {
    throw new Error("unsupported services schema_version");
  }
  if (payload.available !== true || payload.kind !== "services") {
    throw new Error("services panel must be available with kind services");
  }

  if (payload.host !== null) {
    requireExactFields(payload.host, "host", ["identity", "display_name"], []);
    var identity = payload.host.identity;
    if (
      typeof identity !== "string" ||
      identity.length < 1 ||
      identity.length > SERVICES_MAX_KEY ||
      !/^[\x00-\x7F]+$/.test(identity)
    ) {
      throw new Error("host.identity must be 1..64 opaque ASCII characters");
    }
    requireString(
      payload.host.display_name,
      "host.display_name",
      SERVICES_MAX_HOST_DISPLAY_NAME
    );
  }

  var player = payload.player;
  requireExactFields(
    player,
    "player",
    ["wallet", "guild_registered", "guild_rank", "guild_merit", "next_rank", "next_threshold"],
    []
  );
  requireInt(player.wallet, "wallet", 0, MAX_SAFE_INTEGER);
  var guildRegistered = requireBool(player.guild_registered, "guild_registered");
  if (player.guild_rank !== null) {
    requireString(player.guild_rank, "guild_rank", SERVICES_MAX_RANK_KEY);
  }
  requireInt(player.guild_merit, "guild_merit", 0, MAX_SAFE_INTEGER);
  if (player.next_rank !== null) {
    requireString(player.next_rank, "next_rank", SERVICES_MAX_RANK_KEY);
  }
  if (player.next_threshold !== null) {
    requireInt(player.next_threshold, "next_threshold", 1, MAX_SAFE_INTEGER);
  }
  if ((player.next_rank === null) !== (player.next_threshold === null)) {
    throw new Error(
      "player next_rank and next_threshold must both be set or null"
    );
  }
  if (player.guild_rank === null && guildRegistered) {
    throw new Error(
      "an unregistered player must not carry a guild rank in the summary"
    );
  }

  var guild = payload.guild;
  var shop = payload.shop;
  var inventory = payload.inventory;
  if (guild !== null) {
    validateServicesGuild(guild);
  }
  if (shop !== null) {
    validateServicesShop(shop);
  }
  if (inventory !== null) {
    validateServicesInventory(inventory);
  }
  var pagination = validateServicesPagination(payload.pagination);
  validateServicesPaginationTotals(pagination, guild, shop, inventory);

  var result = {
    schema_version: 4,
    available: true,
    kind: "services",
    host: payload.host,
    player: {
      wallet: player.wallet,
      guild_registered: guildRegistered,
      guild_rank: player.guild_rank,
      guild_merit: player.guild_merit,
      next_rank: player.next_rank,
      next_threshold: player.next_threshold,
    },
    guild: guild,
    shop: shop,
    inventory: inventory,
    pagination: pagination,
  };
  // Envelope guarantee (design D4): per-field bounds are ceilings, not a
  // guarantee that any combination of them fits, so the validator enforces
  // the serialized byte size directly and fails closed over the envelope.
  if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
    throw new Error("services payload exceeds the OOB envelope limit");
  }
  return result;
}

function validateServicesPaginationTotals(pagination, guild, shop, inventory) {
  if (guild === null) {
    if (pagination.board_total !== 0 || pagination.quest_total !== 0) {
      throw new Error(
        "pagination board/quest totals must be zero when guild is null"
      );
    }
  } else {
    if (pagination.board_total !== guild.board.length) {
      throw new Error("pagination board_total must match shipped rows");
    }
    if (pagination.quest_total !== guild.quests.length) {
      throw new Error("pagination quest_total must match shipped rows");
    }
  }
  if (shop === null) {
    if (pagination.stock_total !== 0 || pagination.sellable_total !== 0) {
      throw new Error(
        "pagination stock/sellable totals must be zero when shop is null"
      );
    }
  } else {
    if (pagination.stock_total !== shop.stock.length) {
      throw new Error("pagination stock_total must match shipped rows");
    }
    if (pagination.sellable_total !== shop.sellable.length) {
      throw new Error("pagination sellable_total must match shipped rows");
    }
  }
  if (inventory === null) {
    if (pagination.inventory_total !== 0) {
      throw new Error(
        "pagination inventory_total must be zero when inventory is null"
      );
    }
  } else if (pagination.inventory_total !== inventory.rows.length) {
    throw new Error("pagination inventory_total must match shipped rows");
  }
}

module.exports = {
  validateServicesPanel: validateServicesPanel,
};
