/*
 * Elosern DOM-independent service-menu model.
 *
 * Reduces a validated `services` panel into the logical keyboard menus
 * consumed by KeyboardRouter: a Services root, per-surface submenus (Guild,
 * Shop, Inventory), bounded row lists (Board, Quests, Rank, Stock, Sell,
 * Items), quest-detail panes, a bounded quantity-form state for buy/sell, and
 * an explicit confirmation screen before the destructive `guild.quest_abandon`.
 * The module preserves deterministic ordering, keeps disabled rows focusable so
 * their server-provided reason is readable (they never submit), and keeps every
 * server string as display text without parsing narrative.
 *
 * No `document` or `window` access at load time; Node tests exercise the model
 * directly and the GoldenLayout services dock binds it to the keyboard router.
 */
(function (root, factory) {
  "use strict";
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
  } else {
    root.Elosern = root.Elosern || {};
    root.Elosern.ServiceMenu = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var SURFACE_ORDER = ["guild", "shop", "inventory"];

  // -------------------------------------------------------------------------
  // Small helpers.
  // -------------------------------------------------------------------------

  function panelSection(panel, name) {
    return panel && panel[name] !== undefined ? panel[name] : null;
  }

  function actionRow(panel, surface, row, actionKey, defaults) {
    // One focusable row item from an action descriptor, preserving the
    // server-provided label and disabled reason.
    var action = (row && row[actionKey]) || {};
    var item = {
      key: (defaults && defaults.key) || row.key || "row",
      label: action.label || (row && row.display_name) || "",
      enabled: !!action.enabled,
      actionId: action.enabled ? action.action_id : null,
      payload: null,
      description: action.enabled
        ? (defaults && defaults.enabledDescription) || null
        : (action.disabled_reason && action.disabled_reason.message) || null,
      disabledReason: action.disabled_reason || null,
    };
    if (action.enabled && defaults && defaults.buildPayload) {
      item.payload = defaults.buildPayload(row);
    }
    return item;
  }

  function disabledItem(key, label, message) {
    return {
      key: key,
      label: label,
      enabled: false,
      actionId: null,
      payload: null,
      description: message || null,
      disabledReason: message ? { code: "unavailable", message: message } : null,
    };
  }

  function openItem(key, label, submenu) {
    return {
      key: key,
      label: label,
      enabled: true,
      actionId: null,
      payload: null,
      openSubmenu: submenu,
    };
  }

  // -------------------------------------------------------------------------
  // Surface availability.
  // -------------------------------------------------------------------------

  function surfaces(panel) {
    var available = [];
    SURFACE_ORDER.forEach(function (key) {
      if (panelSection(panel, key) !== null) {
        available.push(key);
      }
    });
    return available;
  }

  // -------------------------------------------------------------------------
  // Root menu.
  // -------------------------------------------------------------------------

  function rootItems(panel) {
    var items = [];
    var present = surfaces(panel);
    if (present.indexOf("guild") !== -1) {
      items.push(openItem("guild", "公會", "guild"));
    } else {
      items.push(disabledItem("guild", "公會", "公會服務目前無法使用。"));
    }
    if (present.indexOf("shop") !== -1) {
      items.push(openItem("shop", "商店", "shop"));
    } else {
      items.push(disabledItem("shop", "商店", "商店服務目前無法使用。"));
    }
    if (present.indexOf("inventory") !== -1) {
      items.push(openItem("inventory", "背包", "inventory"));
    }
    return items;
  }

  // -------------------------------------------------------------------------
  // Guild submenus.
  // -------------------------------------------------------------------------

  function guildItems(panel) {
    var guild = panelSection(panel, "guild");
    if (guild === null) {
      return [disabledItem("guild-unavailable", "公會", "公會服務目前無法使用。")];
    }
    var items = [];
    var registration = guild.registration || {};
    items.push(
      actionRow(panel, guild, registration, "register", {
        key: "register",
        buildPayload: function () {
          return {};
        },
      })
    );
    var boardCount = (guild.board || []).length;
    items.push(
      openItem(
        "board",
        "任務板" + (boardCount > 0 ? "（" + boardCount + "）" : ""),
        "board"
      )
    );
    var questCount = (guild.quests || []).length;
    items.push(
      openItem(
        "quests",
        "任務記錄" + (questCount > 0 ? "（" + questCount + "）" : ""),
        "quests"
      )
    );
    if (guild.rank !== null && guild.rank !== undefined) {
      var exam = guild.rank.exam_start || {};
      var rankItem = {
        key: "exam_start",
        label: exam.label || "升階考核",
        enabled: !!exam.enabled,
        actionId: exam.enabled ? exam.action_id : null,
        payload: null,
        description: exam.enabled
          ? "考核目標：" + (guild.rank.next_rank || "?")
          : (exam.disabled_reason && exam.disabled_reason.message) || null,
        disabledReason: exam.disabled_reason || null,
      };
      if (exam.enabled) {
        rankItem.payload = { target_rank: guild.rank.next_rank };
      }
      items.push(rankItem);
    }
    return items;
  }

  function boardItems(panel) {
    var guild = panelSection(panel, "guild");
    var rows = (guild && guild.board) || [];
    var items = [];
    rows.forEach(function (row, index) {
      var accept = row.accept || {};
      var item = {
        key: "board-" + index,
        label: row.display_name,
        enabled: !!accept.enabled,
        actionId: accept.enabled ? accept.action_id : null,
        payload: null,
        description:
          (row.objective_summary || "") + " " + (row.reward_summary || ""),
        disabledReason: accept.disabled_reason || null,
      };
      if (accept.enabled) {
        item.payload = { definition_key: row.definition_key };
      }
      items.push(item);
    });
    if (items.length === 0) {
      items.push(disabledItem("board-empty", "任務板目前沒有適合你的任務。", null));
    }
    return items;
  }

  function questItems(panel) {
    var guild = panelSection(panel, "guild");
    var rows = (guild && guild.quests) || [];
    var items = [];
    rows.forEach(function (row, index) {
      items.push({
        key: "quest-" + index,
        label: row.display_name + "（" + (row.state || "") + "）",
        enabled: true,
        actionId: null,
        payload: null,
        openSubmenu: "quest-" + index,
        questId: row.quest_id,
      });
    });
    if (items.length === 0) {
      items.push(disabledItem("quests-empty", "你的任務記錄是空的。", null));
    }
    return items;
  }

  function questDetailMenu(panel, questRow) {
    var items = [];
    items.push({
      key: "quest-detail",
      label: "詳情",
      enabled: true,
      actionId: null,
      payload: null,
      openDetail: questRow.quest_id,
      detail: questRow.detail || "",
    });
    var abandon = questRow.abandon || {};
    items.push({
      key: "quest-abandon-" + questRow.quest_id,
      label: abandon.label || "放棄",
      enabled: !!abandon.enabled,
      actionId: null,
      payload: null,
      confirmActionId: abandon.enabled ? abandon.action_id : null,
      confirmPayload: abandon.enabled ? { quest_id: questRow.quest_id } : null,
      confirmLabel: "確認放棄",
      description: abandon.enabled
        ? "放棄後任務會失敗，且無法回復。"
        : (abandon.disabled_reason && abandon.disabled_reason.message) || null,
      disabledReason: abandon.disabled_reason || null,
    });
    var turnin = questRow.turnin || {};
    items.push({
      key: "quest-turnin-" + questRow.quest_id,
      label: turnin.label || "回報",
      enabled: !!turnin.enabled,
      actionId: turnin.enabled ? turnin.action_id : null,
      payload: turnin.enabled ? { quest_id: questRow.quest_id } : null,
      description: turnin.enabled
        ? "領取完成任務的獎勵。"
        : (turnin.disabled_reason && turnin.disabled_reason.message) || null,
      disabledReason: turnin.disabled_reason || null,
    });
    return items;
  }

  // -------------------------------------------------------------------------
  // Shop submenus.
  // -------------------------------------------------------------------------

  function shopItems(panel) {
    var shop = panelSection(panel, "shop");
    if (shop === null) {
      return [disabledItem("shop-unavailable", "商店", "商店服務目前無法使用。")];
    }
    var state = shop.open ? "營業中" : "休息中";
    return [
      openItem("stock", "貨架（" + state + "）", "stock"),
      openItem("sell", "販賣", "sell"),
    ];
  }

  function stockItems(panel) {
    var shop = panelSection(panel, "shop");
    var rows = (shop && shop.stock) || [];
    var items = [];
    rows.forEach(function (row, index) {
      var buy = row.buy || {};
      var item = {
        key: "stock-" + index,
        label:
          row.display_name +
          "（買 " +
          row.buy_copper +
          " 銅 / 庫存 " +
          row.stock +
          "）",
        enabled: !!buy.enabled,
        actionId: null,
        payload: null,
        description: buy.enabled
          ? "購買單價 " + row.buy_copper + " 銅。"
          : (buy.disabled_reason && buy.disabled_reason.message) || null,
        disabledReason: buy.disabled_reason || null,
        quantity: buy.enabled ? buy.quantity : null,
      };
      if (buy.enabled) {
        item.actionId = buy.action_id;
        item.itemKey = row.item_key;
        item.commandDisplay = { itemLabel: row.display_name };
      }
      items.push(item);
    });
    if (items.length === 0) {
      items.push(disabledItem("stock-empty", "貨架上沒有任何商品。", null));
    }
    return items;
  }

  function sellableItems(panel) {
    var shop = panelSection(panel, "shop");
    var rows = (shop && shop.sellable) || [];
    var items = [];
    rows.forEach(function (row, index) {
      var sell = row.sell || {};
      var item = {
        key: "sell-" + index,
        label:
          row.display_name +
          "（賣 " +
          row.sell_copper +
          " 銅 / 持有 " +
          row.held +
          "）",
        enabled: !!sell.enabled,
        actionId: null,
        payload: null,
        description: sell.enabled
          ? "販賣單價 " + row.sell_copper + " 銅。"
          : (sell.disabled_reason && sell.disabled_reason.message) || null,
        disabledReason: sell.disabled_reason || null,
        quantity: sell.enabled ? sell.quantity : null,
      };
      if (sell.enabled) {
        item.actionId = sell.action_id;
        item.itemKey = row.item_key;
        item.commandDisplay = { itemLabel: row.display_name };
      }
      items.push(item);
    });
    if (items.length === 0) {
      items.push(disabledItem("sell-empty", "沒有可以販賣的物品。", null));
    }
    return items;
  }

  // -------------------------------------------------------------------------
  // Inventory submenu.
  // -------------------------------------------------------------------------

  function inventoryItems(panel) {
    var inventory = panelSection(panel, "inventory");
    var rows = (inventory && inventory.rows) || [];
    var items = [];
    rows.forEach(function (row, index) {
      var equipped = row.equipped ? "（已裝備）" : "";
      items.push({
        key: "item-" + index,
        label: row.display_name + " ×" + row.held + equipped,
        enabled: false,
        actionId: null,
        payload: null,
        description: "持有 " + row.held + " 個。",
        // No use/consume/equip control exists in this schema version.
      });
    });
    if (items.length === 0) {
      items.push(disabledItem("items-empty", "背包是空的。", null));
    }
    return items;
  }

  // -------------------------------------------------------------------------
  // Quantity form state.
  // -------------------------------------------------------------------------

  function quantityState(minimum, maximum) {
    return {
      min: minimum,
      max: maximum,
      raw: "",
      // The committed integer, or null while editing.
      value: null,
    };
  }

  function quantityInput(state, char) {
    if (char.length !== 1) {
      return state;
    }
    if (char < "0" || char > "9") {
      // Non-digit keyboard input is ignored by the model.
      return state;
    }
    var next = state.raw + char;
    if (next.length > 4) {
      return state;
    }
    state.raw = next;
    state.value = parseInt(next, 10);
    return state;
  }

  function quantityBackspace(state) {
    state.raw = state.raw.slice(0, -1);
    state.value = state.raw === "" ? null : parseInt(state.raw, 10);
    return state;
  }

  // Returns the normalized integer when the current input is a complete valid
  // quantity within the advertised bounds; otherwise null.
  function validateQuantity(state) {
    if (!state || state.raw === "" || state.value === null) {
      return null;
    }
    if (!Number.isInteger(state.value)) {
      return null;
    }
    if (state.value < state.min || state.value > state.max) {
      return null;
    }
    return state.value;
  }

  // -------------------------------------------------------------------------
  // Confirmation menu.
  // -------------------------------------------------------------------------

  function confirmMenu(label, actionId, payload, itemLabel) {
    return {
      items: [
        {
          key: "confirm-" + actionId,
          label: label || "確認",
          enabled: true,
          actionId: actionId,
          payload: payload,
        },
        {
          key: "cancel-" + actionId,
          label: "取消",
          enabled: true,
          actionId: null,
          payload: null,
        },
      ],
      itemLabel: itemLabel || null,
    };
  }

  // -------------------------------------------------------------------------
  // Menu model builder.
  // -------------------------------------------------------------------------

  function buildMenus(panel) {
    var present = surfaces(panel);
    var model = {
      panel: panel,
      surfaces: present,
      menus: {
        root: { items: rootItems(panel), focusKey: null },
        guild: { items: guildItems(panel), focusKey: null, grid: true, gridCols: 2 },
        board: { items: boardItems(panel), focusKey: null, grid: true, gridCols: 2 },
        quests: { items: questItems(panel), focusKey: null, grid: true, gridCols: 2 },
        shop: { items: shopItems(panel), focusKey: null, grid: true, gridCols: 2 },
        stock: { items: stockItems(panel), focusKey: null, grid: true, gridCols: 2 },
        sell: { items: sellableItems(panel), focusKey: null, grid: true, gridCols: 2 },
        inventory: { items: inventoryItems(panel), focusKey: null, grid: true, gridCols: 2 },
      },
    };
    return model;
  }

  function questMenuFor(model, questRow) {
    return { items: questDetailMenu(model.panel, questRow), focusKey: null, grid: true, gridCols: 2 };
  }

  return {
    SURFACE_ORDER: SURFACE_ORDER.slice(),
    surfaces: surfaces,
    buildMenus: buildMenus,
    rootItems: rootItems,
    guildItems: guildItems,
    boardItems: boardItems,
    questItems: questItems,
    questDetailMenu: questDetailMenu,
    questMenuFor: questMenuFor,
    shopItems: shopItems,
    stockItems: stockItems,
    sellableItems: sellableItems,
    inventoryItems: inventoryItems,
    quantityState: quantityState,
    quantityInput: quantityInput,
    quantityBackspace: quantityBackspace,
    validateQuantity: validateQuantity,
    confirmMenu: confirmMenu,
  };
});
