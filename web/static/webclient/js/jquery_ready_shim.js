/*
 * Minimal `$(document).ready` shim for the Vue SPA branch (D10 spike result).
 *
 * Transport-bootstrap spike (webclient-vue-01-foundation): Evennia 6.1's
 * stock `evennia.js` is jQuery-free on every transport path except its final
 * load-time bootstrap, which calls `$(document).ready(...)` once to start
 * `Evennia.init()`. The Vue branch never loads jQuery, so this scoped shim
 * supplies that single surface. It is loaded only in `base.html`'s Vue branch
 * (mutually exclusive with the full pinned jQuery in the legacy branch) and
 * must never be loaded alongside full jQuery.
 */
(function () {
  "use strict";
  if (window.jQuery) {
    return;
  }
  function ready(fn) {
    if (typeof fn !== "function") {
      return;
    }
    if (document.readyState !== "loading") {
      fn();
      return;
    }
    document.addEventListener("DOMContentLoaded", fn, { once: true });
  }
  function selectorQuery(target) {
    if (target === document) {
      return { ready: ready };
    }
    return null;
  }
  if (!window.$) {
    window.$ = selectorQuery;
  }
})();
