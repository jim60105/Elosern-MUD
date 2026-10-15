/*
 * Elosern DOM-independent art panel model.
 *
 * Reduces a validated `art` panel into the logical scene + portrait-catalog
 * model consumed by the GoldenLayout art renderer: scene view reduction
 * (asset / placeholder / pending-with-prior dimmed retention), a catalog
 * keyed by opaque catalog IDs and reduced from each entry's canonical artwork
 * descriptor, client-local focus state with the approved snapshot-adoption
 * rule (keep on survival; else exploration has no focus and combat selects the
 * first valid participant in deterministic presenter order), and open/close
 * full-view state for the scene and portrait.
 *
 * The catalog value is exactly `{artwork, context}` (change
 * unified-portrait-image-contract): the model reads the presented real image
 * from the descriptor's highest-ranked image attempt and the terminal from its
 * own terminal fact, so it holds no selector of its own and never reads a
 * retired flat field.
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

  // Reduce the validated scene payload into a render view.
  //
  // The scene block is exactly `{archetype, label, alt, artwork}`: the view's
  // image is the descriptor's own highest-ranked image attempt (rank decides
  // priority), its status is the descriptor's recorded generation truth, and
  // the archetype/label/alt are the committed display strings. `previous` is
  // the prior reduced scene view (or null); a pending regeneration of the SAME
  // logical place and generation subject keeps the prior image, which is
  // exactly the retention the descriptor's own authorization expresses.
  function reduceScene(scene, previous) {
    scene = scene || {};
    var artwork = scene.artwork || null;
    var candidate = originalOf(artwork);
    var status = artwork && artwork.generation_state ? artwork.generation_state : null;
    var view = {
      archetype: scene.archetype || null,
      label: scene.label || "",
      status: status,
      url: candidate ? candidate.resource.url : null,
      aspectRatio:
        candidate && candidate.resource.geometry ? candidate.resource.geometry.aspect_ratio : null,
      alt: scene.alt || "",
      artwork: artwork,
      placeholderKind: candidate ? null : status === "failed" ? "failed" : "missing",
      placeholderLabel: candidate ? null : status === "failed" ? "場景圖像生成失敗" : "場景圖像尚未生成",
      state: candidate ? "asset" : "placeholder",
    };
    var sameScene =
      previous &&
      previous.artwork &&
      artwork &&
      previous.artwork.subject_id === artwork.subject_id &&
      previous.artwork.generation_subject === artwork.generation_subject;
    if (!candidate && status === "pending" && previous && previous.url && previous.state === "asset" && sameScene) {
      // Pending with a prior rendered image of this same scene: retain it.
      view.state = "pending";
      view.url = previous.url;
      view.placeholderKind = null;
      view.placeholderLabel = null;
    }
    return view;
  }

  // -------------------------------------------------------------------------
  // Catalog model.
  // -------------------------------------------------------------------------

  // The descriptor's presented real candidate: its highest-ranked image
  // attempt (rank decides priority; ties keep declaration order), or null when
  // no real image resolves.
  function originalOf(artwork) {
    var attempts = artwork && Array.isArray(artwork.attempts) ? artwork.attempts : [];
    var best = null;
    attempts.forEach(function (attempt) {
      if (!attempt || attempt.type !== "image" || !attempt.resource) {
        return;
      }
      if (best === null || attempt.rank < best.rank) {
        best = attempt;
      }
    });
    return best;
  }

  function catalogModel(panel) {
    var catalog = (panel && panel.portrait_catalog) || {};
    var entries = {};
    var order = [];
    Object.keys(catalog).forEach(function (key) {
      var entry = catalog[key];
      var artwork = entry.artwork;
      var original = originalOf(artwork);
      var terminal = artwork.terminal;
      entries[key] = {
        id: key,
        artwork: artwork,
        subjectId: artwork.subject_id,
        generationSubject: artwork.generation_subject,
        generationState: artwork.generation_state,
        url: original ? original.resource.url : null,
        aspectRatio: original ? original.resource.geometry.aspect_ratio : null,
        terminalUrl: terminal ? terminal.resource.url : null,
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
