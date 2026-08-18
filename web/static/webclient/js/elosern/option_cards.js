/*
 * Elosern shared AI-suggestion card component and view model.
 *
 * One card builder renders every suggestion card as a native `<button>` from
 * the mirror-validated card fields (`kind`, `action_code`, `label`, `params`,
 * optional `hint`) — the exploration dock embeds these elements and the later
 * narrative choice-point slice reuses the same builder, so both surfaces
 * cannot diverge. The dismiss control is a separate small button rendered once
 * per section (never per card). Every label/hint is inserted as literal text
 * nodes; no card content ever enters a markup pipeline.
 *
 * `buildOptionsView(panel)` is the DOM-independent derivation of the four v5
 * `suggestions` statuses (`{status, cards, visible, emptyState}`): a missing
 * `suggestions` field maps to `visible: false` as a documented compatibility
 * guard only — never a normal v5 render case — and a zero-card `degraded`
 * payload maps to `emptyState: true` so the section can render its defined
 * fallback line instead of an empty box.
 *
 * `suggestionsSignature(suggestions)` is the change-detection key the dock
 * uses to re-render the section in place: it digests the status plus every
 * card's full validated content, so a regenerated set that keeps the same
 * action codes but changes labels or params still re-renders (a stale
 * section would keep old click payloads).
 *
 * No `document` or `window` access at load time; Node tests exercise the model
 * directly and the exploration dock binds the DOM builders to its subtree.
 */
(function (root, factory) {
  "use strict";
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
  } else {
    root.Elosern = root.Elosern || {};
    root.Elosern.OptionCards = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // The four transport states of the validated suggestions envelope.
  var STATUSES = ["generating", "ready", "degraded", "unavailable"];

  function isObject(value) {
    return value !== null && typeof value === "object";
  }

  // Build one suggestion card as a native `<button>`: the label is the
  // primary text node, the optional hint a separate plain-text line under it.
  // Clicking the button invokes `onClick(card)` with the validated card.
  function buildCard(card, onClick) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "option-card";
    if (card && card.kind === "freeform") {
      button.classList.add("option-card-freeform");
    } else {
      button.classList.add("option-card-known");
    }
    var label = document.createElement("span");
    label.className = "option-card-label";
    label.appendChild(document.createTextNode(card && card.label != null ? String(card.label) : ""));
    button.appendChild(label);
    if (card && typeof card.hint === "string" && card.hint.length > 0) {
      var hint = document.createElement("span");
      hint.className = "option-card-hint";
      hint.appendChild(document.createTextNode(card.hint));
      button.appendChild(hint);
    }
    if (typeof onClick === "function") {
      button.addEventListener("click", function () {
        // Pointer clicks and native keyboard activation (Enter/Space on the
        // focused button) both arrive here as `click`; the delegated pointer
        // bridge never touches these elements (it matches only
        // `[data-item-key]` rows), so every activation dispatches through the
        // same submission path.
        onClick(card);
      });
    }
    return button;
  }

  // Build the section-corner dismiss control ("✕ 清除建議"), one per section.
  function buildDismissButton(onClick) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "suggestions-dismiss";
    button.appendChild(document.createTextNode("✕ 清除建議"));
    if (typeof onClick === "function") {
      button.addEventListener("click", function () {
        onClick();
      });
    }
    return button;
  }

  // Derive the section view from the validated `context_actions` panel. The
  // `suggestions` field is required by the v5 contract in every payload; a
  // missing field (a pre-v5 panel or a not-yet-landed mirror) maps to
  // `visible: false` as a defensive compatibility guard, never a normal
  // render path.
  function buildOptionsView(panel) {
    var suggestions =
      isObject(panel) && isObject(panel.suggestions) ? panel.suggestions : null;
    if (!suggestions || STATUSES.indexOf(suggestions.status) === -1) {
      return { status: "unavailable", cards: [], visible: false, emptyState: false };
    }
    if (suggestions.status === "generating") {
      return { status: "generating", cards: [], visible: true, emptyState: false };
    }
    if (suggestions.status === "unavailable") {
      return { status: "unavailable", cards: [], visible: false, emptyState: false };
    }
    var cards = Array.isArray(suggestions.cards) ? suggestions.cards : [];
    return {
      status: suggestions.status,
      cards: cards,
      visible: true,
      emptyState: cards.length === 0,
    };
  }

  // A stable change-detection signature of one suggestions envelope: the
  // status, the card count, and every card's full validated content (kind,
  // action code, label, canonical params, and hint) so the dock re-renders
  // the section in place whenever the suggestions content moved -- a
  // regenerated set can change labels or params while keeping the same
  // action codes, and a stale section would keep old click payloads.
  // Returns null when the envelope is absent or not a v5-shaped object.
  function canonicalParams(params) {
    if (!isObject(params)) {
      return "";
    }
    return Object.keys(params)
      .sort()
      .map(function (key) {
        return key + "=" + String(params[key]);
      })
      .join(",");
  }

  function suggestionsSignature(suggestions) {
    if (!isObject(suggestions) || typeof suggestions.status !== "string") {
      return null;
    }
    var cards = Array.isArray(suggestions.cards) ? suggestions.cards : [];
    var parts = cards.map(function (card) {
      if (!isObject(card)) {
        return "?";
      }
      return [
        card.kind,
        card.action_code,
        card.label,
        canonicalParams(card.params),
        card.hint == null ? "" : card.hint,
      ].join("|");
    });
    return suggestions.status + ":" + cards.length + ":" + parts.join("+");
  }

  return {
    buildCard: buildCard,
    buildDismissButton: buildDismissButton,
    buildOptionsView: buildOptionsView,
    suggestionsSignature: suggestionsSignature,
    STATUSES: STATUSES.slice(),
  };
});
