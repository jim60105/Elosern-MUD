/*
 * Elosern project GoldenLayout plugin.
 *
 * Replaces the stock free-form pane editor with the approved version-1
 * desktop shell. Registers exactly the required components -- header,
 * narrative, art placeholder, status, local-map placeholder, action dock, and
 * command drawer -- and exposes only the minimal layout operations the shell
 * needs. Required components and the action dock are never closable.
 *
 * The layout configuration comes from `elosern/layout_store.js` (versioned,
 * presentation-only persistence); narrative text is inserted through text
 * APIs rather than HTML interpolation.
 */
(function () {
  "use strict";

  var GAME_TITLE = "Elosern";

  var myLayout = null;
  var narrativeDiv = null;
  var promptDiv = null;
  var inputField = null;
  var unsubscribers = [];
  var narrativeUnread = 0;
  var narrativeUnreadElement = null;
  var layoutStoreInstance = null;

  function getStateController() {
    return (
      window.Elosern &&
      window.Elosern.StateController
    ) || null;
  }

  function getLayoutStore() {
    var module = getLayoutModule();
    if (!module) {
      return null;
    }
    if (!layoutStoreInstance) {
      layoutStoreInstance = module.createStore({ storage: window.localStorage });
    }
    return layoutStoreInstance;
  }

  function getLayoutModule() {
    return (
      window.Elosern &&
      window.Elosern.LayoutStore
    ) || null;
  }

  // Replace every child of `element` with a single text node.
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

  // ---------------------------------------------------------------------------
  // Component factories.
  // ---------------------------------------------------------------------------

  function registerHeader(container) {
    var root = makeElement("div", "elosern elosern-header");
    var title = makeElement("div", "header-title");
    var meta = makeElement("div", "header-meta");
    var mode = makeElement("span", "header-mode");
    var clock = makeElement("span", "header-clock");
    var conn = makeElement("span", "header-conn");
    setText(title, GAME_TITLE);
    meta.appendChild(mode);
    meta.appendChild(clock);
    meta.appendChild(conn);
    root.appendChild(title);
    root.appendChild(meta);
    container.getElement().append(root);

    var unsubscribe = subscribeState(function (state) {
      setText(mode, state.mode ? "模式：" + state.mode : "模式：--");
      var time = state.serverTime;
      setText(
        clock,
        time
          ? time.season_label + " " + time.day_in_season + " 日 · " + pad2(time.hour) + ":" + pad2(time.minute)
          : "時間：--"
      );
      setText(conn, state.connected ? "已連線" : "未連線");
    });
    unsubscribers.push(unsubscribe);
  }

  function registerNarrative(container) {
    var root = makeElement("div", "elosern elosern-narrative");
    root.setAttribute("role", "log");
    root.setAttribute("aria-label", "敘事紀錄");
    var unread = makeElement("div", "narrative-unread");
    unread.id = "narrative-unread";
    unread.setAttribute("role", "status");
    unread.setAttribute("aria-live", "polite");
    setText(unread, "");
    narrativeUnreadElement = unread;
    root.appendChild(unread);
    container.getElement().append(root);
    narrativeDiv = root;

    // Clicking the unread marker or scrolling to the bottom clears it.
    root.addEventListener("scroll", function () {
      var atBottom = root.scrollHeight - root.scrollTop - root.clientHeight < 8;
      if (atBottom && narrativeUnread > 0) {
        narrativeUnread = 0;
        updateUnread();
      }
    });
    unread.addEventListener("click", function () {
      root.scrollTop = root.scrollHeight;
      narrativeUnread = 0;
      updateUnread();
    });
  }

  function atNarrativeBottom() {
    if (!narrativeDiv) {
      return true;
    }
    return (
      narrativeDiv.scrollHeight - narrativeDiv.scrollTop - narrativeDiv.clientHeight <
      8
    );
  }

  function updateUnread() {
    if (narrativeUnreadElement) {
      setText(narrativeUnreadElement, narrativeUnread > 0 ? "未讀 " + narrativeUnread : "");
    }
  }

  // Art and local-map placeholders explicitly identify unavailable later
  // delivery units; they never fabricate image or map data.
  function registerUnavailable(container, label, note) {
    var root = makeElement("div", "elosern elosern-placeholder");
    var heading = makeElement("div", "placeholder-heading");
    var body = makeElement("div", "placeholder-body");
    setText(heading, label + "（尚未開放）");
    setText(body, note);
    root.appendChild(heading);
    root.appendChild(body);
    container.getElement().append(root);
  }

  function registerStatus(container) {
    var root = makeElement("div", "elosern elosern-status");
    container.getElement().append(root);

    var unsubscribe = subscribeState(function (state) {
      renderStatus(root, state);
    });
    unsubscribers.push(unsubscribe);
  }

  function renderStatus(root, state) {
    var controller = getStateController();
    var panel = state.panels && state.panels["status"];

    if (!panel) {
      setText(root, "尚未同步狀態");
      return;
    }
    if (panel.available === false) {
      var reason = panel.reason;
      setText(root, reason ? reason.message : "狀態暫時無法顯示");
      return;
    }

    try {
      while (root.firstChild) {
        root.removeChild(root.firstChild);
      }
      var actor = panel.actor;
      var actorLine = makeElement("div", "status-actor");
      var name = makeElement("span", "status-name");
      setText(name, actor.name);
      actorLine.appendChild(name);
      if (actor.location) {
        var location = makeElement("span", "status-location");
        setText(location, " @ " + actor.location.label);
        actorLine.appendChild(location);
      }
      root.appendChild(actorLine);

      var resources = makeElement("div", "status-resources");
      ["hp", "mp", "sp"].forEach(function (key) {
        var gauge = panel.resources[key];
        var row = makeElement("div", "resource resource-" + key);
        var label = makeElement("span", "resource-label");
        var value = makeElement("span", "resource-value");
        setText(label, key.toUpperCase());
        setText(value, gauge.current + " / " + gauge.maximum);
        row.appendChild(label);
        row.appendChild(value);
        resources.appendChild(row);
      });
      root.appendChild(resources);

      if (panel.conditions.length > 0) {
        var list = makeElement("ul", "status-conditions");
        panel.conditions.forEach(function (condition) {
          var item = makeElement("li", "condition condition-" + condition.severity);
          var itemText = condition.label;
          if (typeof condition.remaining_seconds === "number") {
            itemText += "（剩餘 " + condition.remaining_seconds + " 秒）";
          }
          setText(item, itemText);
          list.appendChild(item);
        });
        root.appendChild(list);
      }

      if (panel.disguise_active) {
        var disguise = makeElement("div", "status-disguise");
        setText(disguise, "目前有偽裝狀態");
        root.appendChild(disguise);
      }

      if (panel.combat) {
        var combat = makeElement("div", "status-combat");
        setText(combat, "戰鬥 · 第 " + panel.combat.round + " 回合");
        root.appendChild(combat);
      }

      if (controller) {
        controller.resetResyncEpisode("status");
      }
    } catch (error) {
      setText(root, "此介面暫時無法顯示");
      if (controller) {
        controller.requestResync("status");
      }
    }
  }

  function registerActionDock(container) {
    var root = makeElement("div", "elosern elosern-action-dock");
    root.id = "action-dock";
    root.setAttribute("tabindex", "0");
    var guidance = makeElement("p", "action-guidance");
    guidance.id = "action-dock-guidance";
    var guideNote = makeElement("span", "action-guidance-note");
    guideNote.id = "action-dock-description";
    setText(guideNote, "圖形化動作選單尚未開放。請使用底部指令輸入列輸入指令。");
    guidance.appendChild(guideNote);
    root.appendChild(guidance);

    var live = makeElement("div", "elosern-live");
    live.id = "elosern-action-live";
    live.setAttribute("role", "status");
    live.setAttribute("aria-live", "polite");
    live.setAttribute("aria-atomic", "true");
    root.appendChild(live);

    container.getElement().append(root);

    var unsubscribe = subscribeState(function (state) {
      var result = state.lastActionResult;
      if (result) {
        setText(live, result.message);
      }
    });
    unsubscribers.push(unsubscribe);
  }

  function registerCommandDrawer(container) {
    var root = makeElement("div", "elosern elosern-drawer");
    var prompt = makeElement("div", "prompt");
    promptDiv = prompt;
    var field = makeElement("textarea", "inputfield form-control");
    field.setAttribute("aria-label", "指令輸入");
    field.setAttribute("spellcheck", "false");
    field.id = "inputfield";
    field.classList.add("focused");
    inputField = field;

    var button = makeElement("button", "inputsend");
    button.type = "button";
    button.setAttribute("aria-label", "送出指令");
    setText(button, ">");

    var wrapper = makeElement("div", "inputfieldwrapper");
    wrapper.appendChild(button);
    wrapper.appendChild(field);

    function sendCurrent() {
      var text = field.value;
      if (text.trim() === "") {
        return;
      }
      if (window.plugin_handler && typeof window.plugin_handler.onSend === "function") {
        window.plugin_handler.onSend(text);
      } else if (window.Evennia) {
        window.Evennia.msg("text", [text], {});
      }
      field.value = "";
      var ui = window.Elosern && window.Elosern.ui;
      if (ui && typeof ui.closeDrawer === "function") {
        ui.closeDrawer(true);
      }
    }

    field.addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendCurrent();
      } else if (event.key === "Escape") {
        event.preventDefault();
        var ui = window.Elosern && window.Elosern.ui;
        if (ui && typeof ui.closeDrawer === "function") {
          ui.closeDrawer(true);
        } else {
          field.blur();
        }
      }
    });

    button.addEventListener("click", function () {
      field.focus();
      sendCurrent();
    });

    root.appendChild(prompt);
    root.appendChild(wrapper);
    container.getElement().append(root);
  }

  function registerComponents(layout) {
    layout.registerComponent("header", registerHeader);
    layout.registerComponent("narrative", registerNarrative);
    layout.registerComponent("art", function (container) {
      registerUnavailable(container, "場景圖像", "場景圖像的生成與顯示尚未開放。");
    });
    layout.registerComponent("status", registerStatus);
    layout.registerComponent("local-map", function (container) {
      registerUnavailable(container, "區域地圖", "區域地圖的顯示尚未開放。");
    });
    layout.registerComponent("action-dock", registerActionDock);
    layout.registerComponent("command-drawer", registerCommandDrawer);
  }

  function subscribeState(listener) {
    var controller = getStateController();
    if (controller && typeof controller.subscribe === "function") {
      return controller.subscribe(listener);
    }
    return function () {};
  }

  function pad2(value) {
    return (value < 10 ? "0" : "") + value;
  }

  // ---------------------------------------------------------------------------
  // Text routing. The narrative is the only text surface; server text is
  // inserted as text nodes, never trusted HTML.
  // ---------------------------------------------------------------------------

  function appendNarrative(text) {
    if (!narrativeDiv) {
      return false;
    }
    var wasAtBottom = atNarrativeBottom();
    var line = makeElement("div", "out");
    setText(line, text);
    narrativeDiv.appendChild(line);
    if (wasAtBottom) {
      narrativeDiv.scrollTop = narrativeDiv.scrollHeight;
    } else {
      // Preserve scrollback position and surface an unread count instead of
      // forcing the viewport to the bottom.
      narrativeUnread += 1;
      updateUnread();
    }
    return true;
  }

  function onText(args, kwargs) {
    if (!Array.isArray(args) || typeof args[0] !== "string") {
      return false;
    }
    return appendNarrative(args[0]);
  }

  function onPrompt(args, kwargs) {
    if (!Array.isArray(args) || typeof args[0] !== "string") {
      return false;
    }
    if (promptDiv) {
      setText(promptDiv, args[0]);
      return true;
    }
    return false;
  }

  // Persist only the bounded per-component dimensions when the user resizes.
  function saveLayoutDimensions() {
    var store = getLayoutStore();
    if (!store || !myLayout) {
      return;
    }
    var current = store.load().state;
    store.save({
      layout_version: store.currentVersion,
      dimensions: store.extractDimensions(myLayout.toConfig()),
      tabs: current.tabs,
      preferences: current.preferences,
    });
  }

  function buildLayout() {
    var store = getLayoutStore();
    var module = getLayoutModule();
    var config = store ? store.load().config : module.buildConfig(
      module.defaultWrapper()
    );
    return config;
  }

  function initLayout() {
    var mainsub = document.getElementById("main-sub");
    if (!mainsub) {
      return;
    }
    myLayout = new window.GoldenLayout(buildLayout(), mainsub);
    registerComponents(myLayout);
    myLayout.init();
    myLayout.on("stateChanged", saveLayoutDimensions);
    myLayout.on("itemDestroyed", function (item) {
      if (item.config && item.config.isClosable === false) {
        // Required components must survive user interactions; rebuild if one
        // is removed, keeping every required component present.
        window.setTimeout(function () {
          var store = getLayoutStore();
          var module = getLayoutModule();
          if (store && myLayout) {
            myLayout.root.getItemsByType("component").forEach(function (component) {
              if (
                component.config.componentName &&
                module.REQUIRED_COMPONENTS.indexOf(component.config.componentName) !== -1 &&
                !component.config.isClosable
              ) {
                component.config.isClosable = false;
              }
            });
          }
        }, 0);
      }
    });
  }

  var plugin = {
    init: initLayout,
    postInit: function () {},
    onText: onText,
    onPrompt: onPrompt,
    getGL: function () {
      return myLayout;
    },
  };

  if (typeof window !== "undefined") {
    window.Elosern = window.Elosern || {};
    window.Elosern.goldenlayout = plugin;
  }
  if (typeof window !== "undefined" && window.plugin_handler) {
    window.plugin_handler.add("goldenlayout", plugin);
  }
})();
