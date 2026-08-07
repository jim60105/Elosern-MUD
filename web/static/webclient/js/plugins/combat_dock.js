/*
 * Elosern combat action-dock renderer.
 *
 * Replaces the foundation action-dock guidance with accessible controls and
 * detail panes driven only by the validated `context_actions` panel and the
 * DOM-independent combat-menu model. Outside combat mode the foundation
 * guidance remains; every server string is rendered through text APIs, never
 * trusted HTML. Focus changes emit only client-local events, and with
 * `portrait_ref: null` no focus packet is ever sent.
 */
(function () {
  "use strict";

  var GUIDANCE_TEXT = "圖形化動作選單尚未開放。請使用底部指令輸入列輸入指令。";

  function el(id) {
    return document.getElementById(id);
  }

  function setText(element, text) {
    if (!element) {
      return;
    }
    while (element.firstChild) {
      element.removeChild(element.firstChild);
    }
    element.appendChild(document.createTextNode(text == null ? "" : String(text)));
  }

  function makeElement(tag, className) {
    var element = document.createElement(tag);
    if (className) {
      element.className = className;
    }
    return element;
  }

  function getController() {
    return (
      window.Elosern &&
      window.Elosern.StateController
    ) || null;
  }

  function getKeyboard() {
    return (
      window.Elosern &&
      window.Elosern.keyboard
    ) || null;
  }

  function getActions() {
    return (
      window.Elosern &&
      window.Elosern.actions
    ) || null;
  }

  function getArtFocus() {
    return (
      window.Elosern &&
      window.Elosern.artFocusBus
    ) || null;
  }

  // -------------------------------------------------------------------------
  // Client-local portrait focus publication (webclient-art-panel D6). The dock
  // publishes the highlighted participant's opaque catalog key (its
  // server-authored `portrait_ref`) through the in-memory bus; no packet is
  // ever sent and the browser never constructs a subject key or URL. Leaving
  // combat clears the focus so no portrait card lingers.
  // -------------------------------------------------------------------------

  function publishCombatFocus(panel) {
    var artFocus = getArtFocus();
    if (!artFocus) {
      return;
    }
    if (!panel || panel.available !== true) {
      artFocus.publish(null);
      return;
    }
    // The first participant in deterministic presenter order that carries a
    // server-authored catalog key is the highlighted target. No focus packet
    // is ever sent and the browser never constructs a subject key or URL.
    var participants = panel.participants || [];
    var focus = null;
    for (var index = 0; index < participants.length; index++) {
      if (participants[index].portrait_ref) {
        focus = participants[index].portrait_ref;
        break;
      }
    }
    artFocus.publish(focus);
  }

  // A menu descriptor that references a combat participant (a target or AREA
  // candidate item) is resolved to that participant's server-authored catalog
  // key. Other descriptors (root actions, skills, confirmations) carry no
  // catalog reference and keep the current portrait.
  var KEEP_FOCUS = "@@keep@@";

  function portraitRefForItem(item) {
    if (!item || !item.key) {
      return KEEP_FOCUS;
    }
    var identity = null;
    if (item.key.indexOf("target-") === 0) {
      identity = item.key.slice("target-".length);
    } else if (item.key.indexOf("area-") === 0) {
      identity = item.key.slice("area-".length);
    } else {
      return KEEP_FOCUS;
    }
    var controller = getController();
    var state = controller ? controller.getState() : null;
    var panel = state && state.panels && state.panels["context_actions"];
    var participants = (panel && panel.participants) || [];
    for (var index = 0; index < participants.length; index++) {
      if (String(participants[index].identity) === identity) {
        return participants[index].portrait_ref || null;
      }
    }
    return KEEP_FOCUS;
  }

  function publishFocusForItem(item) {
    var artFocus = getArtFocus();
    if (!artFocus) {
      return;
    }
    var focus = portraitRefForItem(item);
    if (focus !== KEEP_FOCUS) {
      artFocus.publish(focus);
    }
  }

  // -------------------------------------------------------------------------
  // Rendering the combat dock from the validated panel.
  // -------------------------------------------------------------------------

  // Render the router's current frame as dock rows. Every frame the player
  // can reach -- the root actions, Skills, a target list, a shorthand choice,
  // the Forfeit confirmation -- is pushed onto the router stack, so the rows
  // on screen are always exactly the items the router will navigate, explain,
  // and submit. AREA candidate rows carry the live selection marker from the
  // skill's authoritative selection state.
  function renderCombatRows(controls) {
    var keyboard = getKeyboard();
    if (!keyboard || !window.Elosern || !window.Elosern.DockSurface) {
      return;
    }
    var frame = keyboard.currentMenu();
    if (!frame) {
      return;
    }
    var combat = window.Elosern._combat;
    var skill =
      combat && combat.focusSkillKey
        ? combat.skillByKey[combat.focusSkillKey]
        : null;
    frame.items.forEach(function (item) {
      if (item.actionId === "toggle-target" && skill) {
        item.selected = skill.selected.indexOf(item.payload.identity) !== -1;
      }
    });
    var focused = keyboard.currentItem();
    window.Elosern.DockSurface.renderRows(controls, frame.items, {
      focusKey: focused && focused.key !== undefined ? focused.key : null,
      idPrefix: "combat-row",
      menu: frame,
    });
  }

  // Re-render the current frame's rows in place (used after a client-local
  // AREA toggle so the selection marker updates without a router event).
  function refreshRows() {
    var root = el("action-dock");
    if (!root || root.getAttribute("data-mode") !== "combat") {
      return;
    }
    var controls = root.querySelector(".combat-controls");
    if (controls) {
      renderCombatRows(controls);
    }
  }

  function renderCombatDock(root, panel) {
    // Re-rendering replaces the subtree; drop the previous subscription so a
    // long combat never accumulates duplicate listeners.
    if (root._elosern_unsubscribe) {
      root._elosern_unsubscribe();
      root._elosern_unsubscribe = null;
    }
    while (root.firstChild) {
      root.removeChild(root.firstChild);
    }

    if (window.Elosern && window.Elosern.DockSurface) {
      window.Elosern.DockSurface.renderGuidance(root, "技能");
    }

    var session = panel.session;
    var heading = makeElement("div", "combat-heading");
    setText(
      heading,
      "戰鬥 · " +
        (session.mode === "guild_exam" ? "公會考核" : "第 " + session.round + " 回合")
    );
    root.appendChild(heading);

    if (session.state === "recovery") {
      var recovery = makeElement("div", "combat-recovery");
      setText(
        recovery,
        (session.reason && session.reason.message) || "戰鬥狀態異常。"
      );
      root.appendChild(recovery);
      return;
    }

    // The mockup split: item grid on the left, detail pane on the right.
    var layout = makeElement("div", "combat-layout");
    var controls = makeElement("div", "combat-controls");
    controls.setAttribute("aria-label", "戰鬥動作");
    layout.appendChild(controls);
    renderCombatRows(controls);

    var detail = makeElement("div", "combat-detail");
    detail.id = "combat-detail";
    detail.setAttribute("role", "region");
    detail.setAttribute("aria-label", "動作說明");
    layout.appendChild(detail);
    root.appendChild(layout);

    var live = makeElement("div", "combat-live");
    live.id = "elosern-action-live";
    live.classList.add("elosern-live");
    live.setAttribute("role", "status");
    live.setAttribute("aria-live", "polite");
    root.appendChild(live);

    // Surface action results and client notices into the same live region,
    // resolving it by ID because re-rendering replaces the subtree.
    var controller = getController();
    if (controller && controller.subscribe) {
      root._elosern_unsubscribe = controller.subscribe(function (state) {
        var result = state.lastActionResult;
        if (result && result.message) {
          setText(el("elosern-action-live"), result.message);
        }
      });
    }
  }

  function actionLabel(key) {
    return {
      attack: "攻擊",
      skills: "技能",
      items: "道具",
      defend: "防禦",
      flee: "逃跑",
      forfeit: "投降",
    }[key] || key;
  }

  // -------------------------------------------------------------------------
  // Keyboard bridge: push the combat menu stack into the KeyboardRouter.
  // -------------------------------------------------------------------------

  function pushCombatMenus(panel) {
    var keyboard = getKeyboard();
    if (!keyboard || !window.Elosern || !window.Elosern.CombatMenu) {
      return;
    }
    // Rebuild only when the underlying panel changed; a later snapshot in the
    // same session must not tear down an in-progress menu interaction.
    var signature = panelSignature(panel);
    if (signature === pushCombatMenus._lastSignature) {
      return;
    }
    pushCombatMenus._lastSignature = signature;
    var combat = window.Elosern.CombatMenu.buildMenus(panel, {});
    window.Elosern._combat = combat;
    var rootMenu = combat.menus.root;
    rootMenu.items.forEach(function (item) {
      item.label = actionLabel(item.key) || item.label;
    });
    keyboard.reset(rootMenu);
  }

  function panelSignature(panel) {
    var session = panel.session || {};
    var participantIds = (panel.participants || [])
      .map(function (participant) {
        return participant.identity + ":" + participant.hp_current;
      })
      .join("|");
    var skillKeys = (panel.skills || [])
      .map(function (skill) {
        return (
          skill.key +
          ":" +
          (skill.enabled ? "1" : "0") +
          ":" +
          (skill.targets || []).join("+")
        );
      })
      .join("|");
    return (
      session.session_id + ":" + session.round + ":" + participantIds + ":" + skillKeys
    );
  }

  function setCombatLive(text) {
    var live = el("combat-live");
    if (live) {
      setText(live, text);
    }
  }

  // -------------------------------------------------------------------------
  // Subscribe to presentation state and render the dock.
  // -------------------------------------------------------------------------

  var plugin = {
    init: function () {
      var controller = getController();
      if (!controller || !controller.subscribe) {
        return;
      }
      var previousMode = null;
      controller.subscribe(function (state) {
        var panel = state.panels && state.panels["context_actions"];
        var mode = state.mode;
        var root = el("action-dock");
        if (!root) {
          return;
        }
        if (mode === "combat" && panel && panel.available === true) {
          // Render combat controls and rebuild the keyboard root from the
          // accepted panel. The foundation action dock (including the stable
          // #elosern-action-live element) remains untouched elsewhere.
          // `data-mode` is marked first so the router reset below (which
          // emits `focus` synchronously) is accepted by onRouterEvent and
          // re-renders the rows from the new combat root frame in the same
          // call stack -- never a stale pre-combat frame.
          root.setAttribute("data-mode", "combat");
          renderCombatDock(root, panel);
          pushCombatMenus(panel);
          publishCombatFocus(panel);
        } else if (root.getAttribute("data-mode") === "combat") {
          // Leave combat mode: return to the foundation guidance, which the
          // goldenlayout renderer owns from initial layout.
          root.setAttribute("data-mode", "exploration");
          var keyboard = getKeyboard();
          if (keyboard) {
            keyboard.reset(null);
          }
          pushCombatMenus._lastSignature = null;
          publishCombatFocus(null);
        }
        previousMode = mode;
      });
    },
    // Router event bridge (wired from elosern_ui alongside the other docks):
    // every frame change re-renders the rows from the router's current frame,
    // so submenus (skills, targets, shorthand, forfeit) become visible instead
    // of leaving the player navigating blind with only the detail pane.
    onRouterEvent: function (name) {
      if (name !== "focus" && name !== "menu-closed" && name !== "escape-root") {
        return;
      }
      var root = el("action-dock");
      if (!root || root.getAttribute("data-mode") !== "combat") {
        return;
      }
      var controls = root.querySelector(".combat-controls");
      if (controls) {
        renderCombatRows(controls);
      }
    },
  };

  window.Elosern = window.Elosern || {};
  window.Elosern.combatDock = plugin;
  // The keyboard router forwards focus events here so arrow-key navigation
  // through combat target descriptors switches the client-local portrait
  // without sending any packet.
  plugin.publishFocusForItem = publishFocusForItem;
  plugin.refreshRows = refreshRows;
  if (window.plugin_handler) {
    window.plugin_handler.add("elosern_combat_dock", plugin);
  }
})();
