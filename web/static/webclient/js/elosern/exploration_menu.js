/*
 * Elosern DOM-independent exploration-menu model.
 *
 * Reduces a validated `exploration` panel into the logical keyboard menus
 * consumed by KeyboardRouter: the stable Move/Look/Interact/Character/Quests/
 * Inventory root, the bounded exit list, the look room/entity/object list, the
 * present interact targets, and each target's server-authored affordances
 * (scripted keyword buttons, free-form dialogue, engage, or a navigate-kind
 * guild/shop service entry). Move payloads carry the canonical `current_node`
 * supplied by the local-map panel so `explore.move` passes its stale guard.
 *
 * The `navigate`-kind service affordance is dock-navigation only: it opens an
 * existing `services` submenu and is never submitted as an action. Disabled
 * entries stay focusable so their server-provided reason is readable, and
 * every server string is display text -- never parsed narrative.
 *
 * No `document` or `window` access at load time; Node tests exercise the model
 * directly and the GoldenLayout exploration dock binds it to the keyboard
 * router.
 */
(function (root, factory) {
  "use strict";
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
  } else {
    root.Elosern = root.Elosern || {};
    root.Elosern.ExplorationMenu = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

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

  // The final cell of every exploration submenu: a pointer affordance that
  // pops exactly one router frame back to the parent menu (Escape remains
  // the keyboard fast path). Never rendered on the root, which has no
  // parent to return to.
  function backItem() {
    return {
      key: "back",
      label: "返回上一層",
      enabled: true,
      actionId: null,
      payload: null,
      goBack: true,
    };
  }

  // Parent mapping for the back row and dock stack bookkeeping. Unknown keys
  // fall back to the root so a stale key can never throw.
  function parentKeyFor(menuKey) {
    if (
      menuKey === "move" ||
      menuKey === "look" ||
      menuKey === "interact" ||
      menuKey === "wait"
    ) {
      return "root";
    }
    if (menuKey && menuKey.indexOf("target-") === 0) {
      return "interact";
    }
    if (menuKey && menuKey.indexOf("keywords-") === 0) {
      return "target-" + menuKey.slice("keywords-".length);
    }
    return "root";
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

  // -------------------------------------------------------------------------
  // Root menu.
  // -------------------------------------------------------------------------

  function rootItems(panel) {
    var items = [
      openItem("move", "移動", "move"),
      openItem("look", "查看", "look"),
      openItem("interact", "互動", "interact"),
      {
        key: "character",
        label: "角色狀態",
        enabled: true,
        actionId: null,
        payload: null,
        openCharacter: true,
      },
    ];
    // A root whose capability surface is absent must not render as a dead
    // functional entry.
    if (panel.quests && panel.quests.available) {
      items.push({
        key: "quests",
        label: "任務",
        enabled: true,
        actionId: null,
        payload: null,
        openServiceSubmenu: "quests",
      });
    }
    if (panel.inventory && panel.inventory.available) {
      items.push({
        key: "inventory",
        label: "背包",
        enabled: true,
        actionId: null,
        payload: null,
        openServiceSubmenu: "inventory",
      });
    }
    items.push(openItem("wait", "等待/休息", "wait"));
    return items;
  }

  // -------------------------------------------------------------------------
  // Wait/rest submenu.
  // -------------------------------------------------------------------------

  function waitItems() {
    var items = [
      {
        key: "wait-midnight",
        label: "等待至午夜",
        enabled: true,
        actionId: "explore.wait",
        payload: { daypart: "midnight" },
      },
      {
        key: "wait-dawn",
        label: "等待至黎明",
        enabled: true,
        actionId: "explore.wait",
        payload: { daypart: "dawn" },
      },
      {
        key: "wait-noon",
        label: "等待至正午",
        enabled: true,
        actionId: "explore.wait",
        payload: { daypart: "noon" },
      },
      {
        key: "wait-dusk",
        label: "等待至黃昏",
        enabled: true,
        actionId: "explore.wait",
        payload: { daypart: "dusk" },
      },
      {
        key: "wait-rest",
        label: "休息一段時間（自訂秒數）",
        enabled: true,
        actionId: null,
        payload: null,
        openRestForm: true,
      },
      {
        key: "wait-sleep",
        label: "睡眠至恢復",
        enabled: true,
        actionId: "explore.wait",
        payload: { sleep: true },
      },
    ];
    items.push(backItem());
    return items;
  }

  // -------------------------------------------------------------------------
  // Move submenu.
  // -------------------------------------------------------------------------

  function moveItems(panel, currentNode) {
    var rows = (panel && panel.move) || [];
    var mapAvailable = currentNode !== null && currentNode !== undefined && currentNode !== "";
    var items = [];
    rows.forEach(function (row) {
      var canSubmit = row.enabled && mapAvailable;
      var item = {
        key: "exit-" + row.exit_ref,
        label: row.label + (row.enabled ? "" : "（無法通行）"),
        enabled: canSubmit,
        actionId: canSubmit ? "explore.move" : null,
        payload: null,
        description: row.enabled
          ? null
          : (row.disabled_reason && row.disabled_reason.message) ||
            (mapAvailable ? null : "地圖資料尚未同步。"),
        disabledReason: row.disabled_reason || null,
      };
      if (canSubmit) {
        item.payload = { exit_ref: row.exit_ref, current_node: currentNode };
        // Exit traversal has no `move` command; the server label is the
        // documented action description fed to the command-line catalog.
        item.commandDisplay = { exitLabel: row.label };
      }
      items.push(item);
    });
    if (items.length === 0) {
      items.push(disabledItem("move-empty", "這裡沒有可以通行的出口。", null));
    }
    items.push(backItem());
    return items;
  }

  // -------------------------------------------------------------------------
  // Look submenu.
  // -------------------------------------------------------------------------

  function lookItems(panel) {
    var look = (panel && panel.look) || { room: null, entities: [], objects: [] };
    var items = [];
    if (look.room) {
      items.push({
        key: "look-room",
        label: "查看房間",
        enabled: true,
        actionId: "explore.look",
        payload: { room: true },
        description: look.room.display_name || null,
        commandDisplay: { room: true },
      });
    }
    (look.entities || []).forEach(function (entity) {
      items.push({
        key: "entity-" + entity.identity,
        label: entity.display_name,
        enabled: true,
        actionId: "explore.look",
        payload: { target_id: entity.identity },
        kind: entity.kind,
        description: null,
        commandDisplay: { targetLabel: entity.display_name },
      });
    });
    (look.objects || []).forEach(function (obj) {
      items.push({
        key: "object-" + obj.identity,
        label: obj.display_name,
        enabled: true,
        actionId: "explore.look",
        payload: { target_id: obj.identity },
        description: null,
        commandDisplay: { targetLabel: obj.display_name },
      });
    });
    items.push(backItem());
    return items;
  }

  // -------------------------------------------------------------------------
  // Interact target list.
  // -------------------------------------------------------------------------

  function interactItems(panel) {
    var targets = (panel && panel.interact) || [];
    var items = [];
    targets.forEach(function (target) {
      var affordances = target.affordances || [];
      items.push({
        key: "target-" + target.identity,
        label: target.display_name,
        enabled: affordances.length > 0,
        actionId: null,
        payload: null,
        openTarget: affordances.length > 0 ? target.identity : null,
        description:
          affordances.length > 0 ? null : "此對象沒有可用的互動。",
      });
    });
    if (items.length === 0) {
      items.push(disabledItem("interact-empty", "這裡沒有可以互動的對象。", null));
    }
    items.push(backItem());
    return items;
  }

  // -------------------------------------------------------------------------
  // Target affordance menus.
  // -------------------------------------------------------------------------

  function targetMenuFor(model, target) {
    var affordances = (target && target.affordances) || [];
    var items = [];
    affordances.forEach(function (affordance) {
      if (affordance.kind === "action") {
        if (affordance.action_id === "explore.talk_scripted") {
          if (affordance.enabled) {
            items.push({
              key: "talk-scripted",
              label: affordance.label || "交談",
              enabled: true,
              actionId: null,
              payload: null,
              openKeywords: true,
            });
          } else {
            items.push({
              key: "talk-scripted",
              label: affordance.label || "交談",
              enabled: false,
              actionId: null,
              payload: null,
              description:
                (affordance.disabled_reason && affordance.disabled_reason.message) || null,
              disabledReason: affordance.disabled_reason || null,
            });
          }
        } else if (affordance.action_id === "explore.talk_freeform") {
          items.push({
            key: "talk-freeform",
            label: affordance.label || "自由交談",
            enabled: !!affordance.enabled,
            actionId: null,
            payload: null,
            freeform: true,
            npcId: target.identity,
            npcLabel: target.display_name,
            description: null,
            disabledReason: affordance.disabled_reason || null,
          });
        } else if (affordance.action_id === "explore.engage") {
          items.push({
            key: "engage",
            label: affordance.label || "戰鬥",
            enabled: !!affordance.enabled,
            actionId: affordance.enabled ? "explore.engage" : null,
            payload: affordance.enabled ? { monster_id: target.identity } : null,
            description: affordance.enabled
              ? null
              : (affordance.disabled_reason && affordance.disabled_reason.message) || null,
            disabledReason: affordance.disabled_reason || null,
          });
          if (affordance.enabled) {
            items[items.length - 1].commandDisplay = {
              targetLabel: target.display_name,
            };
          }
        }
      } else if (affordance.kind === "navigate") {
        // A navigate-kind service affordance is dock-navigation only; it is
        // never submitted as an action and never carries an action_id.
        items.push({
          key: "service-" + affordance.surface,
          label: affordance.label || (affordance.surface === "guild" ? "公會服務" : "商店"),
          enabled: !!affordance.enabled,
          actionId: null,
          payload: null,
          openServiceSubmenu: affordance.surface,
          description: null,
          disabledReason: affordance.disabled_reason || null,
        });
      }
    });
    if (items.length === 0) {
      items.push(disabledItem("target-empty", "此對象沒有可用的互動。", null));
    }
    items.push(backItem());
    return { items: items, focusKey: null, target: target, grid: true, gridCols: 2 };
  }

  function keywordMenuFor(model, target, scriptedAffordance) {
    void scriptedAffordance;
    // Scripted keyword buttons live on the target descriptor so the interact
    // payload stays within the global JSON-depth bound.
    var keywords = (target && target.keywords) || [];
    var items = keywords.map(function (keyword) {
      return {
        key: "kw-" + keyword.keyword_id,
        label: keyword.label,
        enabled: true,
        actionId: "explore.talk_scripted",
        payload: { npc_id: target.identity, keyword_id: keyword.keyword_id },
        description: null,
        commandDisplay: {
          npcLabel: target.display_name,
          keywordLabel: keyword.label,
        },
      };
    });
    if (items.length === 0) {
      items.push(disabledItem("keywords-empty", "對方目前沒有可以交談的話題。", null));
    }
    items.push(backItem());
    return { items: items, focusKey: null, target: target, grid: true, gridCols: 2 };
  }

  // -------------------------------------------------------------------------
  // Menu model builder.
  // -------------------------------------------------------------------------

  function buildMenus(panel, options) {
    options = options || {};
    var currentNode = options.currentNode || null;
    var model = {
      panel: panel,
      currentNode: currentNode,
      menus: {
        root: { items: rootItems(panel), focusKey: null, grid: true, gridCols: 7 },
        move: { items: moveItems(panel, currentNode), focusKey: null, grid: true, gridCols: 2 },
        look: { items: lookItems(panel), focusKey: null, grid: true, gridCols: 2 },
        interact: { items: interactItems(panel), focusKey: null, grid: true, gridCols: 2 },
        wait: { items: waitItems(), focusKey: null, grid: true, gridCols: 2 },
      },
    };
    return model;
  }

  function targetById(model, identity) {
    var targets = (model.panel && model.panel.interact) || [];
    for (var i = 0; i < targets.length; i++) {
      if (targets[i].identity === identity) {
        return targets[i];
      }
    }
    return null;
  }

  function scriptedAffordanceFor(target) {
    var affordances = (target && target.affordances) || [];
    for (var i = 0; i < affordances.length; i++) {
      if (
        affordances[i].kind === "action" &&
        affordances[i].action_id === "explore.talk_scripted"
      ) {
        return affordances[i];
      }
    }
    return null;
  }

  return {
    buildMenus: buildMenus,
    rootItems: rootItems,
    moveItems: moveItems,
    lookItems: lookItems,
    interactItems: interactItems,
    waitItems: waitItems,
    targetMenuFor: targetMenuFor,
    keywordMenuFor: keywordMenuFor,
    parentKeyFor: parentKeyFor,
    targetById: targetById,
    scriptedAffordanceFor: scriptedAffordanceFor,
  };
});
