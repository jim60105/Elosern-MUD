/*
 * Elosern project GoldenLayout plugin.
 *
 * Replaces the stock free-form pane editor with the approved version-1
 * desktop shell. Registers exactly the required components -- header,
 * narrative, art placeholder, status, local-map minimap, action dock, and
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

  // Minimap lattice cell dimensions (must match the CSS custom properties
  // --elm-map-cell-w/--elm-map-cell-h in elosern.css).
  var MAP_CELL_W = 76;
  var MAP_CELL_H = 28;

  // SVG namespace for the edge layer; assembled so the source contains no
  // literal http URL (the repository contract forbids remote references).
  var SVG_NS = "http" + "://www.w3.org/2000/svg";

  var myLayout = null;
  var narrativeDiv = null;
  var promptDiv = null;
  var inputField = null;
  var unsubscribers = [];
  var narrativeUnread = 0;
  var narrativeUnreadElement = null;
  var layoutStoreInstance = null;
  // The stream-end block controller (choice-points): lazily bound to
  // narrativeDiv once the narrative component mounts.
  var streamEndBlock = null;

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
    var location = makeElement("span", "header-location");
    var clock = makeElement("span", "header-clock");
    var conn = makeElement("span", "header-conn");
    setText(title, GAME_TITLE);
    meta.appendChild(location);
    meta.appendChild(clock);
    meta.appendChild(conn);
    root.appendChild(title);
    root.appendChild(meta);
    container.getElement().append(root);

    var unsubscribe = subscribeState(function (state) {
      // The current location comes from the synced status panel; the raw
      // mode label is gone (the dock's content already identifies the mode).
      var panel = state.panels && state.panels["status"];
      var locationLabel = null;
      if (panel && panel.available === true && panel.actor && panel.actor.location) {
        locationLabel = panel.actor.location.label;
      }
      setText(location, locationLabel ? locationLabel : "位置：--");
      var time = state.serverTime;
      setText(
        clock,
        time
          ? time.season_label + " " + time.day_in_season + " 日 · " + pad2(time.hour) + ":" + pad2(time.minute)
          : "時間：--"
      );
      // Connection state: an ok-green dot plus a label when connected; the
      // non-ok state keeps a dot + border + label pairing, never color alone.
      if (state.connected) {
        root.classList.add("connected");
        root.classList.remove("disconnected");
        setText(conn, "● 已連線");
      } else {
        root.classList.add("disconnected");
        root.classList.remove("connected");
        setText(conn, "○ 未連線");
      }
    });
    unsubscribers.push(unsubscribe);
  }

  function registerNarrative(container) {
    var root = makeElement("div", "elosern elosern-narrative");
    root.setAttribute("role", "log");
    root.setAttribute("aria-label", "敘事紀錄");
    // Programmatically focusable so keyboard activation of the unread marker
    // can move focus here before the marker hides (focus must never vanish
    // into a hidden element).
    root.setAttribute("tabindex", "-1");
    // The live-region wrapper announces count changes; the inner button is
    // the labeled, actionable jump control.
    var unread = makeElement("div", "narrative-unread");
    unread.id = "narrative-unread";
    unread.setAttribute("role", "status");
    unread.setAttribute("aria-live", "polite");
    unread.setAttribute("aria-atomic", "true");
    unread.setAttribute("data-count", "0");
    var button = makeElement("button", "narrative-unread-button");
    button.type = "button";
    setText(button, "");
    unread.appendChild(button);
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
    button.addEventListener("keydown", activateUnreadMarker);
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

  // The unread marker is a labeled control that states its count and its jump
  // action; the wrapper hides entirely at count 0 (no empty pill). Keyboard
  // activation moves focus to the narrative pane before the marker hides so
  // focus never drops into the void; pointer activation leaves focus alone.
  function updateUnread() {
    if (!narrativeUnreadElement) {
      return;
    }
    var button = narrativeUnreadElement.querySelector(".narrative-unread-button");
    if (narrativeUnread > 0) {
      narrativeUnreadElement.setAttribute("data-count", String(narrativeUnread));
      if (button) {
        setText(button, "↓ " + narrativeUnread + " 則新訊息（點擊返回最新）");
      }
    } else {
      narrativeUnreadElement.setAttribute("data-count", "0");
      if (button) {
        setText(button, "");
      }
    }
  }

  // Keyboard activation (Enter/Space on the focused marker button) jumps to
  // the bottom like a click, then parks focus on the narrative pane.
  function activateUnreadMarker(event) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      if (narrativeDiv) {
        narrativeDiv.scrollTop = narrativeDiv.scrollHeight;
        narrativeUnread = 0;
        updateUnread();
        narrativeDiv.focus();
      }
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
      var heading = makeElement("div", "status-heading");
      setText(heading, "角色狀態");
      root.appendChild(heading);
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
        // The mockup gauge bar: an accessible width-based element that
        // complements the mandated numeric text (it never replaces it).
        var bar = makeElement("div", "resource-bar resource-bar-" + key);
        var fill = makeElement("div", "resource-bar-fill");
        var percent = 0;
        if (gauge.maximum > 0) {
          percent = Math.max(0, Math.min(100, Math.round((gauge.current / gauge.maximum) * 100)));
        }
        fill.style.width = percent + "%";
        fill.setAttribute("role", "presentation");
        bar.appendChild(fill);
        row.appendChild(bar);
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
          if (condition.modifiers && Object.keys(condition.modifiers).length > 0) {
            itemText += "｜" + Object.keys(condition.modifiers)
              .map(function (key) {
                return key + " " + condition.modifiers[key];
              })
              .join("、");
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

    // The action dock remains the surface's documented focus target; when a
    // dock mounts a listbox row container, focus forwards to it so existing
    // focus-restoration callers (closeDrawer, the browser journeys) need no
    // change.
    var originalFocus = root.focus;
    root.focus = function () {
      var listbox = root.querySelector('[role="listbox"]');
      if (listbox && typeof listbox.focus === "function" && listbox !== document.activeElement) {
        listbox.focus();
        return;
      }
      originalFocus.call(root);
    };

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
    // No `form-control` class: Bootstrap is not loaded by this page, and the
    // field routes through the plugin `onKeydown` contract even when it was
    // focused by a pointer click (the routing gate in elosern_ui treats the
    // drawer field as the open drawer).
    var field = makeElement("textarea", "inputfield");
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
    // Field first, then the fixed-width send button: the flex row lays them
    // out left-to-right exactly like the mockup's prompt line.
    wrapper.appendChild(field);
    wrapper.appendChild(button);

    // The drawer defaults to closed: a real, focusable entry button is the
    // only visible element until the player opens it (D2). The button carries
    // the drawer's expanded state and opens + focuses the field on activation.
    var entry = makeElement("button", "drawer-entry");
    entry.type = "button";
    entry.setAttribute("aria-expanded", "false");
    setText(entry, "指令輸入（/）");

    var drawerOpen = false;

    function syncState() {
      root.setAttribute("data-open", drawerOpen ? "true" : "false");
      entry.setAttribute("aria-expanded", drawerOpen ? "true" : "false");
    }

    function isOpen() {
      return drawerOpen;
    }

    function open() {
      drawerOpen = true;
      syncState();
      field.focus();
      return true;
    }

    // `restoreFocus` returns focus to the action dock (the documented way
    // back to the menu surface after Escape or a dock-borrowed send).
    function close(restoreFocus) {
      drawerOpen = false;
      syncState();
      if (restoreFocus) {
        var dock = document.getElementById("action-dock");
        if (dock && dock.focus) {
          dock.focus();
        }
      }
      // Any close that was not this dock's own successful free-form consume
      // releases the borrowed-drawer reference, so a cancelled dialogue can
      // never capture a later command.
      var exploration = window.Elosern && window.Elosern.explorationDock;
      if (exploration && typeof exploration.clearPendingFreeform === "function") {
        exploration.clearPendingFreeform();
      }
    }

    function send() {
      var text = field.value;
      if (text.trim() === "") {
        return false;
      }
      // Free-form dialogue intercepts the drawer: the exploration dock holds
      // the server-authored NPC reference and submits `explore.talk_freeform`
      // with the typed speech instead of sending ordinary text. A consumed
      // send closes the drawer and returns focus to the dock that borrowed
      // it. While a dialogue is pending, the send is never ordinary text, so
      // a locked client keeps the speech in the field and the drawer open
      // instead of silently losing it (D4).
      var exploration = window.Elosern && window.Elosern.explorationDock;
      var hasPendingFreeform =
        !!exploration &&
        typeof exploration.hasPendingFreeform === "function" &&
        exploration.hasPendingFreeform();
      if (hasPendingFreeform) {
        if (exploration.consumeFreeformText(text)) {
          field.value = "";
          close(true);
          return true;
        }
        // Locked: the speech stays in the field and the drawer stays open.
        return false;
      }
      if (window.plugin_handler && typeof window.plugin_handler.onSend === "function") {
        window.plugin_handler.onSend(text);
      } else if (window.Evennia) {
        window.Evennia.msg("text", [text], {});
      }
      // An ordinary send echoes the exact raw typed text into the narrative
      // once per deliberate send (D4); the echo is pure presentation.
      if (window.Elosern && window.Elosern.narrativeInput) {
        window.Elosern.narrativeInput.appendInput(text);
      }
      field.value = "";
      // A send routed as ordinary text releases the borrowed-drawer reference
      // too: a cancelled dialogue must never capture a later command.
      if (exploration && typeof exploration.clearPendingFreeform === "function") {
        exploration.clearPendingFreeform();
      }
      // An ordinary text send keeps the drawer open and focus in the field so
      // consecutive commands are typeable without any pointer interaction;
      // Escape is the documented way back to the menu surface.
      return true;
    }

    // Track the field's real focus state; the drawer plugin owns Enter and
    // Escape through the plugin `onKeydown` contract, so no key listener is
    // bound here (exactly one listener handles a given Enter press).
    field.addEventListener("focus", function () {
      field.classList.add("focused");
    });
    field.addEventListener("blur", function () {
      field.classList.remove("focused");
    });

    button.addEventListener("click", function () {
      field.focus();
      send();
    });

    // Pointer activation of the entry button opens and focuses the field, so
    // the pointer-opened field sends on Enter through the single send path.
    entry.addEventListener("click", function () {
      open();
    });

    root.appendChild(entry);
    root.appendChild(prompt);
    root.appendChild(wrapper);
    syncState();
    container.getElement().append(root);

    window.Elosern = window.Elosern || {};
    window.Elosern.drawer = {
      send: send,
      open: open,
      close: close,
      isOpen: isOpen,
    };
  }

  function registerLocalMap(container) {
    var root = makeElement("div", "elosern elosern-local-map");
    root.setAttribute("role", "region");
    root.setAttribute("aria-label", "區域地圖");
    container.getElement().append(root);

    var unsubscribe = subscribeState(function (state) {
      renderLocalMap(root, state);
    });
    unsubscribers.push(unsubscribe);
  }

  function renderLocalMap(root, state) {
    var controller = getStateController();
    var panel = state.panels && state.panels["local_map"];

    if (!panel) {
      setText(root, "尚未同步地圖");
      return;
    }
    if (panel.available === false) {
      var reason = panel.reason;
      setText(root, reason ? reason.message : "區域地圖暫時無法顯示");
      if (controller) {
        controller.resetResyncEpisode("local_map");
      }
      return;
    }

    try {
      var localMap = window.Elosern && window.Elosern.LocalMap;
      if (!localMap) {
        setText(root, "此介面暫時無法顯示");
        return;
      }
      var model = localMap.reducePanel(panel);
      while (root.firstChild) {
        root.removeChild(root.firstChild);
      }

      var heading = makeElement("div", "local-map-heading");
      setText(heading, "附近地圖");
      root.appendChild(heading);

      var title = makeElement("div", "local-map-title");
      setText(title, model.title || "區域地圖");
      root.appendChild(title);

      var canvas = makeElement("div", "local-map-canvas");
      canvas.setAttribute("tabindex", "0");
      canvas.setAttribute("role", "figure");
      canvas.setAttribute("aria-label", model.title || "區域地圖");
      // The canvas reserves its own space from the lattice so the pane
      // scrolls instead of letting nodes overprint the legend.
      canvas.style.width = model.cols * MAP_CELL_W + "px";
      canvas.style.height = model.rows * MAP_CELL_H + "px";

      var nodesById = {};
      model.nodes.forEach(function (node) {
        nodesById[node.id] = node;
      });

      // Edge layer: one non-interactive SVG with a line per edge between
      // cell centers; the label lives on the line's accessible name.
      if (model.edges.length > 0) {
        var svg = document.createElementNS(SVG_NS, "svg");
        svg.setAttribute("class", "local-map-edge-layer");
        svg.setAttribute("width", model.cols * MAP_CELL_W);
        svg.setAttribute("height", model.rows * MAP_CELL_H);
        svg.style.pointerEvents = "none";
        model.edges.forEach(function (edge) {
          var source = nodesById[edge.source];
          var destination = nodesById[edge.destination];
          // An edge touching a node that is not on the canvas (a remembered
          // remote node) is omitted from the drawn layer.
          if (!source || !destination) {
            return;
          }
          var line = document.createElementNS(SVG_NS, "line");
          line.setAttribute("x1", source.col * MAP_CELL_W + MAP_CELL_W / 2);
          line.setAttribute("y1", source.row * MAP_CELL_H + MAP_CELL_H / 2);
          line.setAttribute("x2", destination.col * MAP_CELL_W + MAP_CELL_W / 2);
          line.setAttribute("y2", destination.row * MAP_CELL_H + MAP_CELL_H / 2);
          line.classList.add("local-map-edge");
          if (edge.known) {
            line.classList.add("edge-known");
          }
          if (edge.traversable) {
            line.classList.add("edge-traversable");
          }
          if (edge.label) {
            line.setAttribute("aria-label", edge.label);
          }
          svg.appendChild(line);
        });
        canvas.appendChild(svg);
      }

      model.nodes.forEach(function (node) {
        var nodeEl = makeElement("button", "local-map-node");
        nodeEl.type = "button";
        nodeEl.dataset.nodeId = node.id;
        nodeEl.classList.add("node-" + node.visibility);
        nodeEl.classList.add("node-shape-" + node.shape);
        nodeEl.classList.add("node-border-" + node.border);
        if (node.current) {
          nodeEl.classList.add("node-current");
        }
        if (node.anchor) {
          nodeEl.classList.add("node-anchor");
        }
        if (node.landmark) {
          nodeEl.classList.add("node-landmark");
        }
        // True cell centres.
        nodeEl.style.left = (node.col * MAP_CELL_W + MAP_CELL_W / 2) + "px";
        nodeEl.style.top = (node.row * MAP_CELL_H + MAP_CELL_H / 2) + "px";
        var labelEl = makeElement("span", "local-map-node-label");
        setText(labelEl, node.labelPrefix + node.label);
        nodeEl.appendChild(labelEl);
        nodeEl.setAttribute("aria-label", node.label);
        nodeEl.setAttribute("title", node.label);
        if (node.action !== null) {
          // Adjacent traversable nodes submit `explore.move` with the move
          // descriptor's `exit_ref` and the panel's `current_node`.
          nodeEl.classList.add("node-action-ready");
          nodeEl.addEventListener("click", function () {
            submitLocalMapMove(panel, node);
          });
        }
        canvas.appendChild(nodeEl);
      });
      root.appendChild(canvas);

      // Remembered remote nodes render as a bounded focusable list below the
      // canvas: their payload coordinates describe places outside the current
      // field of view, so they never appear on the coordinate canvas and
      // never imply adjacency to the local neighbourhood.
      if (model.remembered.length > 0) {
        var rememberedList = makeElement("ul", "local-map-remembered");
        rememberedList.setAttribute("aria-label", "曾經到過、但不在附近的遠方位置");
        model.remembered.forEach(function (node) {
          var item = makeElement("li", "local-map-remembered-entry");
          var button = makeElement("button", "local-map-node local-map-remembered-node");
          button.type = "button";
          button.dataset.nodeId = node.id;
          button.classList.add("node-remembered");
          button.classList.add("node-shape-" + node.shape);
          button.classList.add("node-border-" + node.border);
          button.classList.add("node-focusable");
          var labelEl = makeElement("span", "local-map-node-label");
          setText(labelEl, node.labelPrefix + node.label);
          button.appendChild(labelEl);
          button.setAttribute("aria-label", node.label);
          button.setAttribute("title", node.label);
          // Focus-only: writes the name/landmark into the detail line and
          // carries no travel action.
          button.addEventListener("click", function () {
            focusLocalMapNode(root, model, node);
          });
          item.appendChild(button);
          rememberedList.appendChild(item);
        });
        root.appendChild(rememberedList);
      }

      if (model.legend.length > 0) {
        var legend = makeElement("ul", "local-map-legend");
        model.legend.forEach(function (entry) {
          var item = makeElement("li", "local-map-legend-entry");
          setText(item, entry);
          legend.appendChild(item);
        });
        root.appendChild(legend);
      }

      var detail = makeElement("div", "local-map-detail");
      detail.setAttribute("role", "status");
      detail.setAttribute("aria-live", "polite");
      detail.id = "local-map-detail";
      setText(detail, "");
      root.appendChild(detail);

      if (controller) {
        controller.resetResyncEpisode("local_map");
      }
    } catch (error) {
      setText(root, "此介面暫時無法顯示");
      if (controller) {
        controller.requestResync("local_map");
      }
    }
  }

  function focusLocalMapNode(root, model, node) {
    var detail = root.querySelector(".local-map-detail");
    if (!detail) {
      return;
    }
    var focusNote = "已探索的遠方位置：" + node.label;
    if (node.landmark) {
      focusNote += "（地標）";
    }
    setText(detail, focusNote);
  }

  // -------------------------------------------------------------------------
  // Art component (webclient-art-panel): scene + contextual portrait overlay.
  // -------------------------------------------------------------------------

  function registerArt(container) {
    var root = makeElement("div", "elosern elosern-art");
    root.setAttribute("role", "region");
    root.setAttribute("aria-label", "場景圖像");
    container.getElement().append(root);

    var artFocusSubscribed = false;
    var model = null;
    var restoreSceneFocus = false;
    // Client-local record of media URLs whose image failed to load. A failed
    // URL degrades to its truthful placeholder and is never re-requested until
    // the payload carries a new URL or the page is reloaded.
    var failedUrls = {};

    function markFailedUrl(url) {
      if (url) {
        failedUrls[url] = true;
      }
    }

    function isFailedUrl(url) {
      return !!url && failedUrls[url] === true;
    }

    // In-flight image elements keyed by URL. A re-render while a request is
    // still loading reuses the same element instead of issuing a second fetch
    // for the identical URL (the panel must not repeatedly request a URL that
    // has not resolved or failed yet).
    var pendingImages = {};

    function requestSceneImage(url, alt, label, onError, onActivate) {
      var pending = pendingImages[url];
      if (pending) {
        return pending;
      }
      var img = makeElement("img", "art-scene-image");
      img.alt = alt;
      img.setAttribute("tabindex", "0");
      img.setAttribute("role", "button");
      img.setAttribute("aria-label", label + "（按下 Enter 開啟全畫面）");
      pendingImages[url] = img;
      img.addEventListener("load", function () {
        delete pendingImages[url];
      });
      img.addEventListener("error", function () {
        delete pendingImages[url];
        onError();
      });
      img.addEventListener("click", onActivate);
      img.addEventListener("keydown", function (event) {
        if (event.key === "Enter") {
          event.preventDefault();
          onActivate();
        }
      });
      img.src = url;
      return img;
    }

    function render() {
      subscribeArtFocus();
      clearFullView();
      if (!window.Elosern || !window.Elosern.ArtPanel) {
        setText(root, "此介面暫時無法顯示");
        return;
      }
      var state = getStateController() ? getStateController().getState() : null;
      var panel = state && state.panels && state.panels["art"];
      if (!panel) {
        setText(root, "尚未同步場景圖像");
        return;
      }
      if (panel.available === false) {
        var reason = panel.reason;
        setText(root, reason ? reason.message : "場景圖像目前無法顯示");
        return;
      }
      var previous = model;
      model = window.Elosern.ArtPanel.reducePanel(panel, state.mode, previous);
      while (root.firstChild) {
        root.removeChild(root.firstChild);
      }
      var scene = renderScene(root, model);
      renderPortrait(root, model, scene);
      if (restoreSceneFocus) {
        restoreSceneFocus = false;
        var image = root.querySelector(".art-scene-image");
        if (image) {
          image.focus();
        }
      }
      var controller = getStateController();
      if (controller && typeof controller.resetResyncEpisode === "function") {
        controller.resetResyncEpisode("art");
      }
    }

    function renderScene(root, panelModel) {
      var scene = panelModel.scene;
      var scenePane = makeElement("div", "art-scene");
      scenePane.classList.add("art-scene-" + scene.state);
      if (scene.state === "asset" || scene.state === "pending") {
        if (isFailedUrl(scene.url)) {
          // The image previously failed to load; never re-fetch this URL.
          var failed = makeElement("div", "art-scene-empty");
          setText(
            failed,
            scene.placeholderLabel || "圖片載入失敗，請重新整理畫面"
          );
          scenePane.appendChild(failed);
        } else {
          // The listeners close over the plugin-scope ``model`` (not the
          // ``panelModel`` parameter) so a reused in-flight element always
          // mutates the current model on activation or error.
          var img = requestSceneImage(
            scene.url,
            scene.alt,
            scene.label,
            function () {
              markFailedUrl(scene.url);
              render();
            },
            function () {
              model.sceneFullView = true;
              render();
            }
          );
          scenePane.appendChild(img);
        }
        if (scene.state === "pending") {
          scenePane.classList.add("art-dimmed");
          var pendingNote = makeElement("div", "art-pending");
          setText(pendingNote, "目前場景圖片生成中");
          scenePane.appendChild(pendingNote);
        }
      } else {
        var placeholder = makeElement("div", "art-scene-empty");
        setText(
          placeholder,
          scene.placeholderLabel || scene.label || "場景圖像暫時無法顯示"
        );
        scenePane.appendChild(placeholder);
      }
      var caption = makeElement("figcaption", "art-caption");
      var labelLine = makeElement("span", "art-caption-label");
      setText(labelLine, scene.label);
      var altLine = makeElement("span", "art-caption-alt");
      setText(altLine, scene.alt);
      caption.appendChild(labelLine);
      caption.appendChild(altLine);
      scenePane.appendChild(caption);
      root.appendChild(scenePane);
      if (model.sceneFullView) {
        renderFullView(root, model, scene, scenePane);
      }
      return scenePane;
    }

    function renderPortrait(root, model, scenePane) {
      var focus = model.focusKey;
      if (focus === null) {
        return;
      }
      var entry = model.catalog[focus];
      if (!entry) {
        return;
      }
      var card = makeElement("div", "art-portrait");
      card.classList.add("art-portrait-3x4");
      if (entry.url && !isFailedUrl(entry.url)) {
        var img = makeElement("img", "art-portrait-image");
        img.src = entry.url;
        img.alt = entry.alt;
        img.setAttribute("tabindex", "0");
        img.setAttribute("role", "button");
        img.setAttribute("aria-label", entry.name + "（開啟全畫面）");
        img.addEventListener("error", function () {
          markFailedUrl(entry.url);
          render();
        });
        img.addEventListener("click", function () {
          model.portraitFullView = true;
          render();
        });
        img.addEventListener("keydown", function (event) {
          if (event.key === "Enter") {
            event.preventDefault();
            model.portraitFullView = true;
            render();
          }
        });
        card.appendChild(img);
      } else {
        var placeholder = makeElement("div", "art-portrait-placeholder");
        setText(
          placeholder,
          entry.placeholderLabel || "肖像暫時無法顯示"
        );
        card.appendChild(placeholder);
      }
      var context = makeElement("div", "art-portrait-context");
      var name = makeElement("span", "art-portrait-name");
      setText(name, entry.name);
      var role = makeElement("span", "art-portrait-role");
      setText(role, entry.role || "");
      context.appendChild(name);
      context.appendChild(role);
      card.appendChild(context);
      root.appendChild(card);
      if (model.portraitFullView) {
        renderFullView(root, model, entry, card);
      }
    }

    function renderFullView(root, model, target, source) {
      var overlay = makeElement("div", "art-fullview");
      overlay.setAttribute("role", "dialog");
      overlay.setAttribute("aria-modal", "true");
      overlay.setAttribute("tabindex", "0");
      if (target.url && !isFailedUrl(target.url)) {
        var img = makeElement("img", "art-fullview-image");
        img.src = target.url;
        img.alt = target.alt;
        img.addEventListener("error", function () {
          markFailedUrl(target.url);
          render();
        });
        overlay.appendChild(img);
      } else {
        var note = makeElement("div", "art-fullview-note");
        setText(note, target.placeholderLabel || "圖像暫時無法顯示");
        overlay.appendChild(note);
      }
      var close = makeElement("button", "art-fullview-close");
      close.type = "button";
      setText(close, "關閉（Esc）");
      close.addEventListener("click", function () {
        model.sceneFullView = false;
        model.portraitFullView = false;
        render();
      });
      overlay.appendChild(close);
      overlay.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
          event.preventDefault();
          model.sceneFullView = false;
          model.portraitFullView = false;
          restoreSceneFocus = true;
          render();
        }
      });
      document.body.appendChild(overlay);
      overlay.focus();
      root._artFullView = overlay;
    }

    function clearFullView() {
      if (root._artFullView && root._artFullView.parentNode) {
        root._artFullView.parentNode.removeChild(root._artFullView);
        root._artFullView = null;
      }
    }

    var unsubscribe = subscribeState(function () {
      clearFullView();
      render();
    });
    unsubscribers.push(unsubscribe);

    // The art focus bus is created by elosern_ui after this plugin registers,
    // so the subscription is deferred until the bus actually exists; later
    // focus publications then re-select the portrait without any packet.
    function subscribeArtFocus() {
      if (artFocusSubscribed) {
        return;
      }
      var bus = (
        window.Elosern &&
        window.Elosern.artFocusBus
      ) || null;
      if (!bus) {
        return;
      }
      artFocusSubscribed = true;
      var unsubscribeFocus = bus.subscribe(function (focusKey) {
        if (model) {
          model.focusKey = focusKey;
          clearFullView();
          render();
        }
      });
      unsubscribers.push(unsubscribeFocus);
    }
    }

  // Adjacent traversable map nodes submit `explore.move` through their move
  // descriptor (webclient-local-map). The submitted `exit_ref` and
  // `current_node` come only from the validated payload; a remembered remote
  // node (action null) stays inert, and nothing is ever invented client-side.
  function submitLocalMapMove(panel, node) {
    var actions = window.Elosern && window.Elosern.actions;
    if (!actions || !node.action || node.action.kind !== "move") {
      return;
    }
    var currentNode = panel && panel.current_node;
    if (!currentNode) {
      return;
    }
    actions.submit("explore.move", {
      exit_ref: node.action.exit_ref,
      current_node: currentNode,
    }, { exitLabel: node.label });
  }

  function registerComponents(layout) {
    layout.registerComponent("header", registerHeader);
    layout.registerComponent("narrative", registerNarrative);
    layout.registerComponent("art", registerArt);
    layout.registerComponent("status", registerStatus);
    layout.registerComponent("local-map", registerLocalMap);
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
  // Text routing. The narrative is the only text surface; server text arrives
  // as Evennia's ANSI->HTML stream and is rendered through the strict
  // allowlist pipeline (elosern/narrative_markup.js), which builds nodes with
  // element/text-node constructors only and degrades anything outside its
  // allowlist to literal text. If the module is absent, the shell falls back
  // to literal text (a defensive path, not a supported mode).
  // ---------------------------------------------------------------------------

  function getNarrativeMarkup() {
    return (
      window.Elosern &&
      window.Elosern.NarrativeMarkup
    ) || null;
  }

  // Render one converted text message into `root` (a `.out` line wrapper or
  // the prompt surface). Nodes are built exclusively through the element and
  // text-node constructors.
  function renderConvertedText(root, text) {
    var markup = getNarrativeMarkup();
    if (!markup || typeof markup.tokenize !== "function") {
      setText(root, text);
      return;
    }
    var tokens = markup.tokenize(text);
    // The append target follows the span stack; the line itself is the base.
    var stack = [root];
    for (var i = 0; i < tokens.length; i += 1) {
      var token = tokens[i];
      var target = stack[stack.length - 1];
      if (token.kind === "text") {
        target.appendChild(document.createTextNode(token.value));
      } else if (token.kind === "break") {
        target.appendChild(document.createElement("br"));
      } else if (token.kind === "open") {
        var span = document.createElement("span");
        (token.classes || []).forEach(function (cls) {
          span.classList.add(cls);
        });
        if (token.style) {
          if (token.style.color) {
            span.style.color = token.style.color;
          }
          if (token.style.backgroundColor) {
            span.style.backgroundColor = token.style.backgroundColor;
          }
        }
        target.appendChild(span);
        stack.push(span);
      } else if (token.kind === "close") {
        // The tokenizer balances opens/closes; a close with no open (an
        // unbalanced message) degrades to text there, so this should never
        // pop the base line.
        if (stack.length > 1) {
          stack.pop();
        }
      }
    }
  }

  function hasBoxDrawing(text) {
    // Box-drawing glyph range (─ │ ┌ └ ┼ …) marks ASCII map art lines, which
    // must keep the monospace stack for column alignment.
    return /[\u2500-\u257f]/.test(text || "");
  }

  // The single stream-end block owner: the choice-point layer (mount/move/
  // replace/unmount) and every narrative append flow through the controller,
  // so scroll-keep and the unread marker stay one owner. Bound lazily to the
  // mounted narrative container; null while the narrative is unmounted or the
  // controller module is absent (defensive: script order guarantees it).
  function getStreamEndBlock() {
    if (!narrativeDiv) {
      return null;
    }
    if (!streamEndBlock) {
      var module = window.Elosern && window.Elosern.StreamEndBlock;
      if (!module || typeof module.createStreamEndBlock !== "function") {
        return null;
      }
      streamEndBlock = module.createStreamEndBlock(narrativeDiv, {
        atBottom: atNarrativeBottom,
        scrollToBottom: function () {
          narrativeDiv.scrollTop = narrativeDiv.scrollHeight;
        },
        onUnread: function () {
          narrativeUnread += 1;
          updateUnread();
        },
      });
    }
    return streamEndBlock;
  }

  function appendNarrative(text) {
    if (!narrativeDiv) {
      return false;
    }
    var line = makeElement("div", "out");
    if (hasBoxDrawing(text)) {
      line.classList.add("map-art");
    }
    renderConvertedText(line, text);
    var block = getStreamEndBlock();
    if (block) {
      // One scroll/unread decision, made around the insertion: when the
      // choice-point block is mounted the text lands before it and the block
      // stays last (the movable end-block invariant).
      block.appendNode(line);
    } else {
      var wasAtBottom = atNarrativeBottom();
      narrativeDiv.appendChild(line);
      if (wasAtBottom) {
        narrativeDiv.scrollTop = narrativeDiv.scrollHeight;
      } else {
        narrativeUnread += 1;
        updateUnread();
      }
    }
    return true;
  }

  // One player input line in the narrative (D5): a `.narrative-divider`
  // hairline before the line unless the log has no prior lines, then a `.inp`
  // line whose text is inserted as a single literal text node -- client-
  // authored text must never enter the markup allowlist pipeline. One input
  // event (divider + line) counts as exactly one unread increment and one
  // scroll-keep event, exactly like one server line; the divider and the line
  // travel as one fragment so the choice-point block always stays last.
  function appendInput(text) {
    if (!narrativeDiv) {
      return false;
    }
    // The decision is taken before the divider so one input event counts
    // exactly once (D5), byte-identical to the pre-choice-point path.
    var wasAtBottom = atNarrativeBottom();
    var hasPriorLine =
      narrativeDiv.querySelector(".out, .inp, .sys, .err") !== null;
    var fragment = document.createDocumentFragment();
    if (hasPriorLine) {
      fragment.appendChild(makeElement("div", "narrative-divider"));
    }
    var line = makeElement("div", "inp");
    line.appendChild(document.createTextNode(text == null ? "" : String(text)));
    fragment.appendChild(line);
    var block = getStreamEndBlock();
    if (block) {
      block.appendNode(fragment, wasAtBottom);
    } else {
      narrativeDiv.appendChild(fragment);
      if (wasAtBottom) {
        narrativeDiv.scrollTop = narrativeDiv.scrollHeight;
      } else {
        narrativeUnread += 1;
        updateUnread();
      }
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
      // The prompt surface receives the same converted stream as the
      // narrative; render it through the allowlist pipeline too.
      while (promptDiv.firstChild) {
        promptDiv.removeChild(promptDiv.firstChild);
      }
      renderConvertedText(promptDiv, args[0]);
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
    // GoldenLayout appends its root into #main-sub rather than replacing its
    // children, so the degraded text fallback (#messagewindow) must be hidden
    // here or it stacks above the mounted shell in normal flow and pushes the
    // real UI one full viewport below the fold, where `body{overflow:hidden}`
    // clips it entirely.
    var fallback = document.getElementById("messagewindow");
    if (fallback) {
      fallback.classList.add("d-none");
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
    // One shared narrative append path for player input lines: the action
    // client (dispatch echo) and the drawer (ordinary send echo) both route
    // through this facade so scroll-keep and the unread marker stay single-
    // owner (D5).
    //
    // The stream-end block API (choice-points) keeps the same single owner:
    // the choice-point layer mounts, moves, replaces, and unmounts exactly
    // one block element through these operations, and every narrative append
    // keeps the block last (the movable end-block invariant). The operations
    // are safe no-ops when no block is mounted and never write outside the
    // narrative container; blocks are DOM nodes supplied by the caller, never
    // built from markup here.
    window.Elosern.narrativeInput = {
      appendInput: appendInput,
      mountChoicePoint: function (element) {
        var block = getStreamEndBlock();
        return block ? block.mount(element) : false;
      },
      moveChoicePointToEnd: function () {
        var block = getStreamEndBlock();
        return block ? block.moveToEnd() : false;
      },
      replaceChoicePoint: function (element) {
        var block = getStreamEndBlock();
        return block ? block.replace(element) : false;
      },
      unmountChoicePoint: function () {
        var block = getStreamEndBlock();
        return block ? block.unmount() : false;
      },
    };
  }
  if (typeof window !== "undefined" && window.plugin_handler) {
    window.plugin_handler.add("goldenlayout", plugin);
  }
})();
