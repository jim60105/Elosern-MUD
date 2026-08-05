/*
 * Elosern client-local art focus bus (webclient-art-panel D6).
 *
 * A tiny in-memory publish/subscribe channel carrying the currently focused
 * portrait catalog key. It is entirely client-local: nothing here sends a
 * packet, constructs a subject key, or derives a portrait from entity data.
 * The combat dock publishes its highlighted participant's catalog key today;
 * the exploration dock (23d) will publish the dialogue speaker against the
 * same catalog.
 *
 * No `document` or `window` access at load time; Node tests exercise the bus
 * directly.
 */
(function (root, factory) {
  "use strict";
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
  } else {
    root.Elosern = root.Elosern || {};
    root.Elosern.ArtFocus = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  function createBus() {
    var listeners = [];

    function publish(focusKey) {
      var value = focusKey === null || focusKey === undefined ? null : String(focusKey);
      listeners.slice().forEach(function (listener) {
        try {
          listener(value);
        } catch (error) {
          // A broken subscriber must never break the bus.
        }
      });
    }

    function subscribe(listener) {
      if (typeof listener !== "function") {
        throw new Error("subscribe requires a listener function");
      }
      listeners.push(listener);
      return function unsubscribe() {
        var index = listeners.indexOf(listener);
        if (index !== -1) {
          listeners.splice(index, 1);
        }
      };
    }

    return {
      publish: publish,
      subscribe: subscribe,
    };
  }

  return {
    createBus: createBus,
  };
});
