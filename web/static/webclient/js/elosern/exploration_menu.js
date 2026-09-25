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
 * The `navigate`-kind service affordance is dock-navigation only: it opens a
 * frameless drawer (guild -> quest, shop -> shop) and is never
 * submitted as an action. Disabled entries stay focusable so their
 * server-provided reason is readable, and every server string is display
 * text -- never parsed narrative.
 *
 * The AVG scene overview (webclient-scene-overview-component, AVG stage
 * design §7): `overviewMenu` flattens the exits, the people, the objects,
 * and a footer (查看房間 · 等待／休息 · 建議) into ONE reading-order menu
 * with a `sections` index and `geometry: "sections"` for the router, and
 * `verbMenuFor` is a person chip's verb popover (the target's affordances
 * plus 查看). Neither is called by a resolver until the swap change.
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

  // The exploration panel's navigation-presented rows (webclient-scene-
  // overview-swap): the character status, quest, and inventory surfaces. They
  // are NOT a dock frame any more — the scene overview deliberately carries no
  // navigation entry — so the top navigation bar owns them as their sole
  // keyboard-visible stop and derives them from the committed panel's own
  // capability flags. A root whose capability surface is absent must not
  // render as a dead functional entry, so 任務 and 背包 appear only while the
  // panel reports them available.
  function navigationItems(panel) {
    panel = panel || {};
    var items = [
      {
        key: "character",
        label: "角色狀態",
        enabled: true,
        actionId: null,
        payload: null,
        openCharacter: true,
      },
    ];
    if (panel.quests && panel.quests.available) {
      // 任務 is a client-local drawer open (the 背包 precedent):
      // activating it opens the 任務 drawer without pushing a keyboard
      // frame or switching the action dock.
      items.push({
        key: "quests",
        label: "任務",
        enabled: true,
        actionId: null,
        payload: null,
        openDrawer: "quest",
      });
    }
    if (panel.inventory && panel.inventory.available) {
      // 背包 is a client-local drawer open (the frameless precedent of the
      // 角色狀態 row): activating it opens the 背包 · 裝備 drawer without
      // pushing a keyboard frame or switching the action dock.
      items.push({
        key: "inventory",
        label: "背包",
        enabled: true,
        actionId: null,
        payload: null,
        openDrawer: "inventory",
      });
    }
    return items;
  }

  function rootItems(panel, suggestions) {
    var items = [
      openItem("move", "移動", "move"),
      openItem("look", "查看", "look"),
      openItem("interact", "互動", "interact"),
    ];
    // The navigation-presented rows share one builder with the top
    // navigation bar (webclient-scene-overview-swap): the retired tab root
    // carried them in its own order, the bar derives them from the same
    // source.
    Array.prototype.push.apply(items, navigationItems(panel));
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
        key: "wait-dawn",
        label: "等待直到黎明",
        enabled: true,
        actionId: "explore.wait",
        payload: { daypart: "dawn" },
      },
      {
        key: "wait-sleep",
        label: "睡眠至完全恢復",
        enabled: true,
        actionId: "explore.wait",
        payload: { sleep: true },
      },
      {
        key: "wait-rest",
        label: "休息 N 小時",
        enabled: true,
        actionId: null,
        payload: null,
        openRestForm: true,
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
        } else if (affordance.action_id === "explore.deliver") {
          // The delivery payload is the server-normalized affordance params
          // (npc_id + item_key) forwarded byte-for-byte; the menu never
          // reconstructs a bound quest payload from the target identity.
          items.push({
            key: "deliver",
            label: affordance.label || "交付",
            enabled: !!affordance.enabled,
            actionId: affordance.enabled ? "explore.deliver" : null,
            payload: affordance.enabled
              ? {
                  npc_id: affordance.params && affordance.params.npc_id,
                  item_key: affordance.params && affordance.params.item_key,
                }
              : null,
            description: affordance.enabled
              ? null
              : (affordance.disabled_reason && affordance.disabled_reason.message) || null,
            disabledReason: affordance.disabled_reason || null,
          });
          if (affordance.enabled) {
            items[items.length - 1].commandDisplay = {
              // The echo is the server-authored affordance label ("交付
              // <item> 給 <recipient>"): the recipient identity exists only
              // as a bound id, so the exact typed command cannot be composed
              // here without guessing names (explore.move precedent).
              actionLabel: affordance.label,
            };
          }
        }
      } else if (affordance.kind === "navigate") {
        // A navigate-kind service affordance is dock-navigation only; it is
        // never submitted as an action and never carries an action_id.
        // Both guild and shop surfaces open client-local frameless drawers
        // (openDrawer: "quest" | "shop", the 背包 precedent), leaving the
        // router's frame stack untouched.
        var drawerMap = { guild: "quest", shop: "shop" };
        var drawerName = drawerMap[affordance.surface] || affordance.surface;
        var labelFallback = affordance.surface === "guild" ? "公會服務" : "商店";
        items.push({
          key: "service-" + affordance.surface,
          label: affordance.label || labelFallback,
          enabled: !!affordance.enabled,
          actionId: null,
          payload: null,
          openDrawer: drawerName,
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

  // -------------------------------------------------------------------------
  // Verb popover (webclient-scene-overview-component design D2): the target's
  // affordance rows in payload order (the same mapping as `targetMenuFor`),
  // then 查看, then the back row. A target with no mapped affordance yields
  // 查看 and back only. A vertical list: no grid geometry.
  // -------------------------------------------------------------------------

  function verbMenuFor(model, target) {
    var base = targetMenuFor(model, target);
    var items = base.items.filter(function (item) {
      return item.key !== "target-empty" && item.key !== "back";
    });
    var identity = target && target.identity;
    var name = (target && target.display_name) || "";
    items.push({
      key: "look-target",
      label: "查看",
      enabled: true,
      actionId: "explore.look",
      payload: { target_id: identity },
      description: null,
      commandDisplay: { targetLabel: name },
    });
    items.push(backItem());
    return {
      items: items,
      focusKey: null,
      target: target,
      title: name || "互動",
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
  // Scene overview (webclient-scene-overview-component design D1).
  // -------------------------------------------------------------------------

  // One flat menu in reading order — 出口, 人物, 物件, then the label-less
  // footer — with `sections: [{key, label, count}]` naming the non-empty
  // rows. Item shapes reuse the existing builders so payloads stay
  // byte-identical. `geometry: "sections"` tells the router how the arrow
  // keys cross rows; the menu carries no `grid` flag, so focus projects as a
  // list (the focus index is the reading-order index).
  function overviewMenu(panel, options) {
    options = options || {};
    var currentNode = options.currentNode || null;
    var suggestions = options.suggestions || null;
    var sections = [];
    var items = [];

    function addSection(key, label, rows) {
      if (rows.length === 0) {
        return;
      }
      sections.push({ key: key, label: label, count: rows.length });
      Array.prototype.push.apply(items, rows);
    }

    // 出口: the move rows without the back row or the empty placeholder
    // (the section is omitted instead). A chip's label is the plain server
    // label: the chip renderer adds the disabled marker, so the
    // `（無法通行）` suffix is not baked in.
    var moveRows = (panel && panel.move) || [];
    var exits = moveItems(panel, currentNode)
      .filter(function (item) {
        return item.key !== "back" && item.key !== "move-empty";
      })
      .map(function (item, index) {
        var row = moveRows[index];
        if (row && typeof row.label === "string") {
          item.label = row.label;
        }
        return item;
      });
    addSection("exits", "出口", exits);

    // 人物: every interact target opens its verb popover (always enabled:
    // the popover has at least 查看), then a look chip for each present
    // entity that has no interact descriptor.
    var targets = (panel && panel.interact) || [];
    var interactIds = {};
    var people = targets.map(function (target) {
      interactIds[target.identity] = true;
      return {
        key: "target-" + target.identity,
        label: target.display_name,
        enabled: true,
        actionId: null,
        payload: null,
        openTarget: target.identity,
        description: null,
      };
    });
    var lookRows = lookItems(panel);
    lookRows.forEach(function (item) {
      if (item.key.indexOf("entity-") === 0 && !interactIds[item.payload.target_id]) {
        people.push(item);
      }
    });
    addSection("people", "人物", people);

    // 物件: the look rows for objects.
    addSection(
      "objects",
      "物件",
      lookRows.filter(function (item) {
        return item.key.indexOf("object-") === 0;
      })
    );

    // Footer: 查看房間, 等待／休息, and 建議 (N) while suggestions are not
    // `unavailable`. The 查看房間 chip is `lookItems`' room row, which needs
    // `look.room`: the OOB v2 schema guarantees a non-null room on every
    // available panel (`validateExplorationLook` requires the exact room
    // fields), and `wait` is unconditional, so the footer is never empty.
    var footer = lookRows.filter(function (item) {
      return item.key === "look-room";
    });
    footer.push({
      key: "wait",
      label: "等待／休息",
      enabled: true,
      actionId: null,
      payload: null,
      openSubmenu: "wait",
    });
    var status = suggestions && suggestions.status;
    if (status && status !== "unavailable") {
      var cards =
        (status === "ready" || status === "degraded") && Array.isArray(suggestions.cards)
          ? suggestions.cards.length
          : 0;
      footer.push({
        key: "suggestions",
        label: cards > 0 ? "建議 (" + cards + ")" : "建議",
        enabled: true,
        actionId: null,
        payload: null,
        openSubmenu: "suggestions",
      });
    }
    addSection("footer", null, footer);

    return {
      items: items,
      sections: sections,
      geometry: "sections",
      focusKey: null,
      title: "場景",
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
          gridCols: null,
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
     navigationItems: navigationItems,
     rootItems: rootItems,
     moveItems: moveItems,
     lookItems: lookItems,
     interactItems: interactItems,
     waitItems: waitItems,
     targetMenuFor: targetMenuFor,
     verbMenuFor: verbMenuFor,
     overviewMenu: overviewMenu,
     keywordMenuFor: keywordMenuFor,
     parentKeyFor: parentKeyFor,
     targetById: targetById,
     scriptedAffordanceFor: scriptedAffordanceFor,
     normalizeDirection: normalizeDirection,
     suggestionsMenu: suggestionsMenu,
   };
});
