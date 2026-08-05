/*
 * Elosern DOM-independent art panel model.
 *
 * Reduces a validated `art` panel into the logical scene + portrait-catalog
 * model consumed by the GoldenLayout art renderer: scene view reduction
 * (asset / placeholder / pending-with-prior dimmed retention), a catalog
 * keyed by opaque catalog IDs, client-local focus state with the approved
 * snapshot-adoption rule (keep on survival; else exploration has no focus and
 * combat selects the first valid participant in deterministic presenter
 * order), and open/close full-view state for the scene and portrait.
 *
 * No `document` or `window` access at load time; Node tests exercise the
 * model directly. The browser never constructs a subject key, URL, status, or
 * alternative text: focus selects a supplied catalog value, and no focus
 * mutation is ever sent.
 */
(function (root, factory) {
  "use strict";
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
  } else {
    root.Elosern = root.Elosern || {};
    root.Elosern.ArtPanel = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var MAX_FOCUS = 1;

  // -------------------------------------------------------------------------
  // Scene reduction.
  // -------------------------------------------------------------------------

  // Reduce the validated scene payload into a render view. The scene is
  // either an asset (done), a truthful placeholder, or -- when the current
  // scene is pending and a prior image was already rendered -- a dimmed
  // retained image explicitly labelled `目前場景圖片生成中`. `previous` is the
  // prior reduced scene view (or null); without a prior image a pending scene
  // degrades to the placeholder.
  function reduceScene(scene, previous) {
    scene = scene || {};
    var status = scene.status || null;
    var placeholder = scene.placeholder || null;
    var view = {
      archetype: scene.archetype || null,
      label: scene.label || "",
      status: status,
      url: scene.url || null,
      aspectRatio: scene.aspect_ratio || null,
      alt: scene.alt || "",
      placeholderKind: placeholder ? placeholder.kind : null,
      placeholderLabel: placeholder ? placeholder.label : null,
      state: "placeholder",
    };
    if (status === "done" && scene.url) {
      view.state = "asset";
    } else if (status === "pending" && previous && previous.url && previous.state === "asset") {
      // Pending with a prior rendered image: retain it visibly dimmed.
      view.state = "pending";
      view.url = previous.url;
    }
    return view;
  }

  // -------------------------------------------------------------------------
  // Catalog model.
  // -------------------------------------------------------------------------

  function catalogModel(panel) {
    var catalog = (panel && panel.portrait_catalog) || {};
    var entries = {};
    var order = [];
    Object.keys(catalog).forEach(function (key) {
      var entry = catalog[key];
      entries[key] = {
        id: key,
        subjectKey: entry.subject_key || null,
        status: entry.status || null,
        url: entry.url || null,
        aspectRatio: entry.aspect_ratio || null,
        alt: entry.alt || "",
        placeholderKind: entry.placeholder ? entry.placeholder.kind : null,
        placeholderLabel: entry.placeholder ? entry.placeholder.label : null,
        name: entry.context ? entry.context.name : "",
        role: entry.context ? entry.context.role : "",
      };
      order.push(key);
    });
    return { entries: entries, order: order };
  }

  // -------------------------------------------------------------------------
  // Focus adoption.
  // -------------------------------------------------------------------------

  // The approved snapshot-adoption rule: keep the current focus when its
  // catalog ID survives the new catalog; otherwise exploration has no focus
  // and combat selects the first valid participant in deterministic presenter
  // order. `mode` and the previous focus ID are supplied by the reducer.
  function adoptFocus(mode, previousFocus, model) {
    if (previousFocus !== null && Object.prototype.hasOwnProperty.call(model.entries, previousFocus)) {
      return previousFocus;
    }
    if (mode === "combat" && model.order.length > 0) {
      return model.order[0];
    }
    return null;
  }

  // -------------------------------------------------------------------------
  // Stateful model reducer.
  // -------------------------------------------------------------------------

  // `state` holds the client-local focus and full-view state. It is mutable
  // so the renderer can update focus without re-reducing the whole panel; the
  // reducer only replaces it when the panel changes.
  function createArtState() {
    return {
      focusKey: null,
      sceneFullView: false,
      portraitFullView: false,
    };
  }

  function reducePanel(panel, mode, previous) {
    previous = previous || {};
    var scene = reduceScene(panel && panel.scene, previous.scene);
    var catalog = catalogModel(panel);
    var priorFocus = previous.focusKey === undefined ? null : previous.focusKey;
    var focusKey = adoptFocus(mode, priorFocus, catalog);
    return {
      available: !!(panel && panel.available === true),
      kind: panel && panel.kind || null,
      scene: scene,
      catalog: catalog.entries,
      catalogOrder: catalog.order,
      focusKey: focusKey,
      sceneFullView: !!previous.sceneFullView,
      portraitFullView: !!previous.portraitFullView,
    };
  }

  function focusedEntry(model) {
    if (model.focusKey === null) {
      return null;
    }
    return model.catalog[model.focusKey] || null;
  }

  // -------------------------------------------------------------------------
  // Focus movement helpers (client-local; no packet).
  // -------------------------------------------------------------------------

  // Move focus by one catalog step in `direction` (+1 / -1), wrapping within
  // the deterministic presenter order. Returns the new focus key or null.
  function moveFocus(model, direction) {
    var order = model.catalogOrder || [];
    if (order.length === 0) {
      return null;
    }
    var index = order.indexOf(model.focusKey);
    if (index === -1) {
      return direction > 0 ? order[0] : order[order.length - 1];
    }
    var next = (index + direction + order.length) % order.length;
    return order[next];
  }

  return {
    MAX_FOCUS: MAX_FOCUS,
    reduceScene: reduceScene,
    reducePanel: reducePanel,
    adoptFocus: adoptFocus,
    focusedEntry: focusedEntry,
    moveFocus: moveFocus,
    createArtState: createArtState,
  };
});
