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

  // -------------------------------------------------------------------------
  // Rendering the combat dock from the validated panel.
  // -------------------------------------------------------------------------

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

    var controls = makeElement("div", "combat-controls");
    controls.setAttribute("role", "group");
    controls.setAttribute("aria-label", "戰鬥動作");
    panel.root_actions.forEach(function (actionKey) {
      var button = makeElement("button", "combat-control combat-control-" + actionKey);
      button.type = "button";
      button.setAttribute("data-action", actionKey);
      setText(button, actionLabel(actionKey));
      controls.appendChild(button);
    });
    root.appendChild(controls);

    var detail = makeElement("div", "combat-detail");
    detail.id = "combat-detail";
    detail.setAttribute("role", "region");
    detail.setAttribute("aria-label", "動作說明");
    root.appendChild(detail);

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
          renderCombatDock(root, panel);
          pushCombatMenus(panel);
          root.setAttribute("data-mode", "combat");
        } else if (root.getAttribute("data-mode") === "combat") {
          // Leave combat mode: return to the foundation guidance, which the
          // goldenlayout renderer owns from initial layout.
          root.setAttribute("data-mode", "exploration");
          var keyboard = getKeyboard();
          if (keyboard) {
            keyboard.reset(null);
          }
          pushCombatMenus._lastSignature = null;
        }
        previousMode = mode;
      });
    },
  };

  window.Elosern = window.Elosern || {};
  window.Elosern.combatDock = plugin;
  if (window.plugin_handler) {
    window.plugin_handler.add("elosern_combat_dock", plugin);
  }
})();
