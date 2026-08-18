/*
 * Elosern narrative choice-point layer (webclient-options-choicepoints).
 *
 * The narrative-stream placement of AI action suggestions: a movable stream-
 * end block driven solely by the committed `context_actions` v5 panel. The
 * stream is the AI-only surface — `generating` appends one muted line,
 * `ready` replaces it in place with the card group, and everything else
 * (degraded, unavailable, dismiss, combat/creation modes, panel absence,
 * unknown statuses, transport resets) removes the block.
 *
 * The layer subscribes to the presentation store (`subscribe` notifications,
 * post-`commitPresentation`), diffs `panels["context_actions"].suggestions`
 * against its remembered status, and runs the pure reducer from
 * `elosern/choicepoint_logic.js`. No generation-side metadata and no
 * transport hints are ever read; `beginTransport` (panels cleared) resolves
 * to absence synchronously on its own notification.
 *
 * The block itself is owned by the `window.Elosern.narrativeInput` facade
 * (goldenlayout.js): mount/move/replace/unmount through the facade keep the
 * stream's end geometry, scroll-keep, and unread marker single-owner. Cards
 * are built exclusively through the shared OptionCards factory — the same
 * DOM component and the same click/dispatch path as the dock section
 * (envelope parity), including the "✕ 清除建議" dismiss control and the
 * action-client admission rule (a stream card click while locked is rejected
 * by the same code path as a dock card click).
 */
(function (root, factory) {
  "use strict";
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
  } else {
    root.Elosern = root.Elosern || {};
    root.Elosern.ChoicePoints = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var GENERATING_LINE = "AI 正在構思建議…";
  var FACADE_OPS = [
    "mountChoicePoint",
    "moveChoicePointToEnd",
    "replaceChoicePoint",
    "unmountChoicePoint",
  ];

  function isFunction(value) {
    return typeof value === "function";
  }

  function makeElement(tag, className) {
    var element = document.createElement(tag);
    if (className) {
      element.className = className;
    }
    return element;
  }

  function setText(element, text) {
    while (element.firstChild) {
      element.removeChild(element.firstChild);
    }
    element.appendChild(document.createTextNode(text == null ? "" : String(text)));
  }

  // Extract the committed suggestions envelope from one store snapshot, or
  // the null sentinel when the stream input is absent: no `context_actions`
  // panel, an unavailable form, a non-exploration kind, or no suggestions
  // section (the compatibility guard for pre-v5 payloads; the mirror already
  // rejects out-of-contract shapes at commit time).
  function committedSuggestions(state) {
    var panel = state && state.panels && state.panels["context_actions"];
    if (!panel || panel.available !== true || panel.kind !== "exploration") {
      return null;
    }
    var suggestions = panel.suggestions;
    if (!suggestions || typeof suggestions !== "object") {
      return null;
    }
    return suggestions;
  }

  // The DOM-independent layer core: injectable readers keep every transition
  // Node-testable without a browser.
  function createChoicePointLayer(options) {
    options = options || {};
    var getFacade = options.getFacade || function () {
      return null;
    };
    var getCards = options.getCards || function () {
      return null;
    };
    var getActions = options.getActions || function () {
      return null;
    };
    var getLogic = options.getLogic || function () {
      var scope = typeof window !== "undefined"
        ? window
        : (typeof globalThis !== "undefined" ? globalThis : null);
      return (scope && scope.Elosern && scope.Elosern.ChoicePointLogic) || null;
    };
    var previous = "absent";

    function facade() {
      var f = getFacade();
      if (!f) {
        return null;
      }
      for (var i = 0; i < FACADE_OPS.length; i += 1) {
        if (!isFunction(f[FACADE_OPS[i]])) {
          return null;
        }
      }
      return f;
    }

    function cardsModule() {
      var c = getCards();
      if (!c || !isFunction(c.buildCard) || !isFunction(c.buildDismissButton)) {
        return null;
      }
      return c;
    }

    // One muted generating line as the block element: a plain text node, never
    // a markup pipeline. It carries no live-region role of its own -- the
    // narrative is a `role="log"` surface and announces the line once; a
    // nested live region would double-announce in assistive technology.
    function buildGeneratingLine() {
      var line = makeElement("div", "choicepoint-block choicepoint-generating");
      setText(line, GENERATING_LINE);
      return line;
    }

    // Dispatch one card click through the action client with the exact dock
    // envelope: `known_action` reuses the validator-normalized params as-is;
    // `freeform` composes the canonical talk payload whose speech is always
    // the label text. No display descriptor is passed, so the echo bridge
    // resolves to null exactly as it does for a dock card (envelope parity).
    function submitCard(card) {
      var actions = getActions();
      if (!actions || !isFunction(actions.submit) || !card) {
        return;
      }
      if (card.kind === "freeform") {
        actions.submit("explore.talk_freeform", {
          npc_id: card.params && card.params.npc_id,
          speech: card.label,
        });
        return;
      }
      actions.submit(card.action_code, card.params);
    }

    // Dispatch the dismiss control: `options.dismiss` with the exact empty
    // payload; removal happens on the subsequent committed `unavailable`
    // (committed-state invariant — no optimistic unmount on click).
    function submitDismiss() {
      var actions = getActions();
      if (actions && isFunction(actions.submit)) {
        actions.submit("options.dismiss", {});
      }
    }

    // The ready card group: one block node holding one card per committed
    // `cards` entry, built exclusively through the shared OptionCards factory
    // (this module never constructs card DOM itself), plus the dock's dismiss
    // control attached to the group.
    function buildReadyGroup(cardsList) {
      var module = cardsModule();
      if (!module) {
        return null;
      }
      var group = makeElement("div", "choicepoint-block choicepoint-ready");
      var wrap = makeElement("div", "choicepoint-cards");
      wrap.setAttribute("role", "group");
      wrap.setAttribute("aria-label", "建議動作");
      (cardsList || []).forEach(function (card) {
        wrap.appendChild(module.buildCard(card, submitCard));
      });
      group.appendChild(wrap);
      group.appendChild(module.buildDismissButton(submitDismiss));
      return group;
    }

    // Run the reducer and apply the edge through the facade. The block is
    // only ever touched when the remembered status actually changed, and the
    // remembered status advances only when the facade operation succeeded:
    // a failed mount (e.g. the narrative container is not mounted yet) leaves
    // `previous` unchanged so the next notification retries instead of
    // letting the choice-point vanish forever.
    function handleNotification(state) {
      var logic = getLogic();
      if (!logic || !isFunction(logic.nextChoicePointState)) {
        return;
      }
      var committed = committedSuggestions(state);
      var next = logic.nextChoicePointState(previous, committed);
      if (next === previous) {
        return;
      }
      var edge = isFunction(logic.transitionEdge)
        ? logic.transitionEdge(previous, next)
        : (next === "absent" ? "unmount" : (previous === "absent" ? "mount" : "replace"));
      var f = facade();
      if (!f) {
        return;
      }
      if (edge === "none") {
        return;
      }
      if (edge === "unmount") {
        if (f.unmountChoicePoint()) {
          previous = next;
        }
        return;
      }
      var element =
        next === "ready" ? buildReadyGroup(committed && committed.cards) : buildGeneratingLine();
      if (!element) {
        return;
      }
      var applied = edge === "mount"
        ? f.mountChoicePoint(element)
        : f.replaceChoicePoint(element);
      if (applied) {
        previous = next;
      }
    }

    return {
      handleNotification: handleNotification,
      committedSuggestions: committedSuggestions,
      previousState: function () {
        return previous;
      },
    };
  }

  // Browser wiring: one store subscription per page behind the explicit
  // readiness gate. The module is a no-op until the store, the narrative
  // facade, the shared card renderer, and the action client are all present;
  // a bounded diagnostic names the missing contract instead of failing
  // silently. No module-level retained server state.
  function createChoicePoints(options) {
    options = options || {};
    var controller = options.controller || null;
    var log = options.log || (typeof console !== "undefined" ? console : null);
    var layer = createChoicePointLayer({
      getFacade: function () {
        return window.Elosern && window.Elosern.narrativeInput;
      },
      getCards: function () {
        return window.Elosern && window.Elosern.OptionCards;
      },
      getActions: function () {
        return window.Elosern && window.Elosern.actions;
      },
    });
    var started = false;

    function diagnostic() {
      if (log && isFunction(log.error)) {
        log.error(
          "choice-points: skipped — store, narrative facade, shared card renderer, or action client missing"
        );
      }
    }

    function ready() {
      if (!controller || !isFunction(controller.subscribe)) {
        return false;
      }
      var f = window.Elosern && window.Elosern.narrativeInput;
      if (!f || !isFunction(f.appendInput)) {
        return false;
      }
      for (var i = 0; i < FACADE_OPS.length; i += 1) {
        if (!isFunction(f[FACADE_OPS[i]])) {
          return false;
        }
      }
      var cardsModule = window.Elosern && window.Elosern.OptionCards;
      if (
        !cardsModule ||
        !isFunction(cardsModule.buildCard) ||
        !isFunction(cardsModule.buildDismissButton)
      ) {
        return false;
      }
      var actions = window.Elosern && window.Elosern.actions;
      if (!actions || !isFunction(actions.submit)) {
        return false;
      }
      return true;
    }

    function start() {
      if (started) {
        return;
      }
      if (!ready()) {
        diagnostic();
        return;
      }
      controller.subscribe(function (state) {
        layer.handleNotification(state);
      });
      // One initial pass over the current snapshot: panels are empty on a
      // fresh transport generation, but a late init must never strand an
      // already-committed stream state.
      var state = controller.getState ? controller.getState() : null;
      if (state) {
        layer.handleNotification(state);
      }
      started = true;
    }

    return {
      start: start,
      layer: layer,
      ready: ready,
    };
  }

  return {
    GENERATING_LINE: GENERATING_LINE,
    FACADE_OPS: FACADE_OPS.slice(),
    createChoicePointLayer: createChoicePointLayer,
    createChoicePoints: createChoicePoints,
  };
});

// Browser plugin registration: one layer per page, started after every
// dependency (store, facade, shared renderer, action client) is wired by its
// owning plugin's init — base.html orders this module after elosern_ui.js.
(function () {
  "use strict";
  if (typeof window === "undefined") {
    return;
  }
  var plugin = {
    init: function () {
      var points = window.Elosern.ChoicePoints.createChoicePoints({
        controller: window.Elosern && window.Elosern.StateController,
      });
      points.start();
    },
  };
  if (window.plugin_handler) {
    window.plugin_handler.add("choice_points", plugin);
  }
})();
