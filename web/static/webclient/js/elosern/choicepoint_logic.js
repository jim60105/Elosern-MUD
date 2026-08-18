/*
 * Elosern narrative choice-point state machine (webclient-options-choicepoints).
 *
 * The narrative stream is the AI-only surface: it renders `generating` and
 * `ready` suggestions and nothing else. `nextChoicePointState` is the pure
 * reducer over the finite states `absent | generating | ready`, driven solely
 * by the committed `context_actions.suggestions` envelope (or the sentinel
 * `null` when the committed panel is absent, not exploration, or carries no
 * suggestions section). `transitionEdge` maps a (previous, next) pair to the
 * DOM operation the render adapter must perform, so every transition is a pure
 * function of (old status, new status, new cards) and the whole table is
 * Node-testable without a DOM.
 *
 * Transition contract (design.md §Decisions):
 * - generating -> generating and ready -> ready are no-ops.
 * - generating -> ready replaces the line in place; ready -> generating
 *   replaces the stale group with the fresh line in place.
 * - any other transition (degraded, unavailable, the `none` sentinel, or an
 *   unknown status) resolves to `absent` and removes the block.
 */
(function (root, factory) {
  "use strict";
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
  } else {
    root.Elosern = root.Elosern || {};
    root.Elosern.ChoicePointLogic = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var ABSENT = "absent";
  var GENERATING = "generating";
  var READY = "ready";

  // The next choice-point state from the committed suggestions envelope.
  // `committed` is the validated `{status, cards}` object or the sentinel
  // `null` (panel absent / not exploration / no suggestions section). Anything
  // outside the two stream statuses is elimination, never rendered.
  function nextChoicePointState(previous, committed) {
    if (!committed || typeof committed.status !== "string") {
      return ABSENT;
    }
    if (committed.status === GENERATING) {
      return GENERATING;
    }
    if (committed.status === READY) {
      return READY;
    }
    return ABSENT;
  }

  // The DOM operation the render adapter must perform for a (previous, next)
  // transition: "mount" (insert a fresh block at the stream end), "replace"
  // (swap the mounted block in place), "unmount" (remove it), or "none".
  function transitionEdge(previous, next) {
    if (previous === next) {
      return "none";
    }
    if (next === ABSENT) {
      return "unmount";
    }
    if (previous === ABSENT) {
      return "mount";
    }
    return "replace";
  }

  return {
    ABSENT: ABSENT,
    GENERATING: GENERATING,
    READY: READY,
    nextChoicePointState: nextChoicePointState,
    transitionEdge: transitionEdge,
  };
});
