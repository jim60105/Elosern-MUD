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

  // Canonical direction words the exit label can carry, mapped to one
  // canonical token. A label outside the table (a named door or a dynamic
  // wilderness gateway) returns null — the renderer shows it verbatim in the
  // glyph slot and never guesses a direction (H3 design D9).
  var DIRECTION_ALIASES = {
    n: "north",
    north: "north",
    北: "north",
    s: "south",
    south: "south",
    南: "south",
    e: "east",
    east: "east",
    東: "east",
    w: "west",
    west: "west",
    西: "west",
    ne: "northeast",
    northeast: "northeast",
    東北: "northeast",
    nw: "northwest",
    northwest: "northwest",
    西北: "northwest",
    se: "southeast",
    southeast: "southeast",
    東南: "southeast",
    sw: "southwest",
    southwest: "southwest",
    西南: "southwest",
    up: "up",
    上: "up",
    down: "down",
    下: "down"
  };

  function normalizeDirection(label) {
    if (typeof label !== "string") {
      return null;
    }
    var key = label.trim().toLowerCase();
    return key in DIRECTION_ALIASES ? DIRECTION_ALIASES[key] : null;
  }

  function rootItems(panel, suggestions) {
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
    // The suggestions root entry (H3 webclient-hud-03-action-dock): present
    // whenever the committed `suggestions` envelope is not `unavailable`;
    // `unavailable` renders no entry at all (today's "renders nothing").
    var status = suggestions && suggestions.status;
    if (status && status !== "unavailable") {
      items.push({
        key: "suggestions",
        label: "建議",
        enabled: true,
        actionId: null,
        payload: null,
        openSubmenu: "suggestions",
      });
    }
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
         // H3: the renderer's exit outlet reads these directly instead of
         // re-parsing the exit label (H3 design D9): the canonical direction
         // (null for named doors / dynamic wilderness gates) and the
         // destination node id the server re-derived for this exit.
         direction: normalizeDirection(row.label),
         destination: row.destination || null,
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
        } else if (affordance.action_id === "explore.party_invite") {
          items.push({
            key: "party-invite",
            label: affordance.label || "邀請",
            enabled: !!affordance.enabled,
            actionId: affordance.enabled ? "explore.party_invite" : null,
            payload: affordance.enabled ? { npc_id: target.identity, message: "" } : null,
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
        } else if (affordance.action_id === "explore.party_leave") {
          items.push({
            key: "party-leave",
            label: affordance.label || "解散",
            enabled: !!affordance.enabled,
            actionId: affordance.enabled ? "explore.party_leave" : null,
            payload: affordance.enabled ? { npc_id: target.identity } : null,
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
     // The breadcrumb's current segment is the target's own display name
     // (H3 design D3): a target-scoped frame is labelled by its target.
     return {
       items: items,
       focusKey: null,
       target: target,
       grid: true,
       gridCols: 2,
       title: (target && target.display_name) || "互動",
     };
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
    return {
      items: items,
      focusKey: null,
      target: target,
      grid: true,
      gridCols: 2,
      title: (target && target.display_name) || "交談",
    };
  }

  // -------------------------------------------------------------------------
  // Suggestions menu (H3 webclient-hud-03-action-dock): the `建議` root
  // entry's frame — the committed `context_actions.suggestions` envelope
  // becomes a keyboard-reachable router frame: cards as rows, the `✕ 清除建議`
  // dismiss row (`options.dismiss`, `{}`), and a back row. `generating` is
  // one disabled row; `degraded` keeps its muted note and the zero-card
  // empty-state line; `unavailable` means the root entry is absent.
  // -------------------------------------------------------------------------

  function cardItems(suggestions) {
    var cards = (suggestions && Array.isArray(suggestions.cards)
      ? suggestions.cards
      : []);
    var items = [];
    var used = {};
    function uniqueKey(base) {
      var key = base;
      for (var n = 2; used[key]; n += 1) {
        key = base + "-" + n;
      }
      used[key] = true;
      return key;
    }
    cards.forEach(function (card) {
      var item;
      if (card.kind === "freeform") {
        // A freeform card speaks its label as the `explore.talk_freeform`
        // speech (the options surface contract: the speech is always the
        // label text).
        item = {
          key: uniqueKey("action-explore.talk_freeform"),
          label: card.label,
          hint: card.hint || null,
          enabled: true,
          actionId: "explore.talk_freeform",
          payload: {
            npc_id: card.params && card.params.npc_id,
            speech: card.label,
          },
        };
      } else {
        // A known_action card dispatches its validator-normalized payload
        // as-is.
        item = {
          key: uniqueKey("action-" + card.action_code),
          label: card.label,
          hint: card.hint || null,
          enabled: true,
          actionId: card.action_code,
          payload: card.params || {},
        };
      }
      items.push(item);
    });
    return items;
  }

  function suggestionsMenu(suggestions) {
    var status = suggestions && suggestions.status;
    var items = [];
    if (status === "generating") {
      items.push({
        key: "suggestions-generating",
        label: "AI 正在構思建議…",
        enabled: false,
        actionId: null,
        payload: null,
        description: "AI 正在構思建議…",
        disabledReason: { code: "generating", message: "AI 正在構思建議…" },
      });
    } else if (status === "ready" || status === "degraded") {
      items = cardItems(suggestions);
      if (status === "degraded" && items.length === 0) {
        items.push({
          key: "suggestions-empty",
          label: "現在沒有什麼值得做的動作",
          enabled: false,
          actionId: null,
          payload: null,
          description: "現在沒有什麼值得做的動作",
          disabledReason: { code: "empty", message: "現在沒有什麼值得做的動作" },
        });
      }
      items.push({
        key: "action-options.dismiss",
        label: "✕ 清除建議",
        enabled: true,
        actionId: "options.dismiss",
        payload: {},
      });
    }
    items.push(backItem());
    return {
      items: items,
      focusKey: null,
      title: "建議",
      grid: true,
      gridCols: items.length,
    };
  }

  // -------------------------------------------------------------------------
  // Menu model builder.
  // -------------------------------------------------------------------------

  function buildMenus(panel, options) {
    options = options || {};
    var currentNode = options.currentNode || null;
    var suggestions = options.suggestions || null;
    var rootItemsList = rootItems(panel, suggestions);
    // The root is a single-row tab bar: the column count equals the item
    // count (H3 design D12) so arrow-key geometry matches the rendered
    // order.
    var model = {
      panel: panel,
      currentNode: currentNode,
      menus: {
        root: {
          items: rootItemsList,
          focusKey: null,
          grid: true,
          gridCols: rootItemsList.length,
          title: "探索",
        },
        move: {
          items: moveItems(panel, currentNode),
          focusKey: null,
          grid: true,
          gridCols: 2,
          title: "移動",
        },
        look: {
          items: lookItems(panel),
          focusKey: null,
          grid: true,
          gridCols: 2,
          title: "查看",
        },
        interact: {
          items: interactItems(panel),
          focusKey: null,
          grid: true,
          gridCols: 2,
          title: "互動",
        },
        wait: {
          items: waitItems(),
          focusKey: null,
          grid: true,
          gridCols: 2,
          title: "等待",
        },
      },
    };
    if (suggestions && suggestions.status && suggestions.status !== "unavailable") {
      model.menus.suggestions = suggestionsMenu(suggestions);
    }
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
     normalizeDirection: normalizeDirection,
     suggestionsMenu: suggestionsMenu,
   };
});
