// Declarative-frame resolver registry (webclient-frame-resolver-registry,
// design doc D-A/D-B/D-C): maps a frame descriptor `{source, params}` to a
// menu derived from the COMMITTED presentation state at the moment of the
// call. Resolvers read only the state the protocol reducer has atomically
// committed under the revision gate (via the injected `getState`) and reuse
// the shipped menu builders verbatim — no label, row, or payload synthesis
// beyond what those builders already produce (root entries and `back` rows
// included, so reproducing them is not fabrication).
//
// This change implements exactly the exploration family (8 sources) and ships
// the registry without dock consumers; the cutover changes replace the
// copy-based push sites with `resolve` calls and add their own table waves.
//
// Purity contract: resolving twice against one committed state returns deep-
// equal menus and mutates nothing — the builders are pure over their inputs,
// and every resolver here only reads `getState()` and calls them.
//
// Degradation is data, never an exception: an unregistered source, an absent
// identity/index, an unavailable panel form, a withdrawn suggestions
// envelope, or a resolver that throws all return the shared marker
// `{unresolvable: true, reason}`. `reason` prefers the committed panel's
// server-authored `reason.message` verbatim; otherwise it is null and the
// CONSUMER chooses the local fallback line when rendering. Pop-versus-
// disabled handling belongs to the stack rules of the dependent change, not
// to this registry.

import ExplorationMenu from "../lib/exploration_menu.js";

// The one degradation marker shape. Frozen so a consumer can never mutate
// the shared instance into a payload.
export const UNRESOLVABLE = Object.freeze({ unresolvable: true, reason: null });

// The suggestions statuses the frame may resolve while open (the
// options-surface statuses minus `unavailable`, which forbids any pane — an
// open suggestions frame at that status must degrade so the stack rule can
// leave it).
const SUGGESTIONS_RESOLVABLE = ["generating", "ready", "degraded"];

function marker(reasonMessage) {
  if (typeof reasonMessage !== "string" || reasonMessage === "") return UNRESOLVABLE;
  return Object.freeze({ unresolvable: true, reason: reasonMessage });
}

// Ownership isolation (duck finding 2): builders hand out rows that reference
// committed panel objects (`disabledReason`, the target frame's `target`,
// suggestion card params). A consumer must never gain a write channel into
// committed state, so every resolvable menu leaves the registry as an
// independent deep copy — values verbatim, references never.
function isolate(menu) {
  return structuredClone(menu);
}

// The committed panel's server-authored message, when the panel is in its
// unavailable form (the common discriminator: available false + bounded
// reason). Available or absent panels carry no authored reason here.
function panelReasonMessage(panel) {
  if (panel && panel.available === false && panel.reason && typeof panel.reason.message === "string") {
    return panel.reason.message;
  }
  return null;
}

/**
 * Build the frame resolver over the committed presentation state.
 *
 * @param {{getState: () => object}} deps — `getState` returns the protocol
 *     reducer's committed state (`{mode, panels, ...}`). Resolvers bind their
 *     reads through it at CALL time, never earlier.
 * @returns {{resolve: (descriptor: {source: string, params?: object}) => object}}
 */
export function createFrameResolver(deps) {
  function committed() {
    return (deps && typeof deps.getState === "function" && deps.getState()) || {};
  }

  // The shared exploration build: the same ExplorationMenu model the copy
  // push sites produce today, from the panels committed right now.
  function explorationModel() {
    const state = committed();
    const panels = state.panels || {};
    const panel = panels.exploration || {};
    const currentNode = (panels.local_map && panels.local_map.current_node) || null;
    const suggestions = (panels.context_actions && panels.context_actions.suggestions) || null;
    return { panel, model: ExplorationMenu.buildMenus(panel, { currentNode, suggestions }) };
  }

  // A source whose owning panel committed its unavailable form degrades with
  // the server message; an absent panel behaves the same way.
  function requireExplorationPanel() {
    const state = committed();
    const panel = (state.panels && state.panels.exploration) || null;
    if (!panel || panel.available === false) {
      return { ok: false, reason: marker(panelReasonMessage(panel)) };
    }
    return { ok: true, panel };
  }

  const explorationMenuSource = (menuKey) => () => {
    const gate = requireExplorationPanel();
    if (!gate.ok) return gate.reason;
    const { model } = explorationModel();
    return isolate(model.menus[menuKey]);
  };

  // A target/keywords descriptor names its subject by the SAME server-
  // authored identity the rows carry; an identity the committed panel no
  // longer lists is the identity-loss degradation.
  function targetForIdentity(params) {
    const gate = requireExplorationPanel();
    if (!gate.ok) return { ok: false, reason: gate.reason };
    const identity = params && params.identity;
    if (identity === undefined || identity === null) {
      return { ok: false, reason: marker(null) };
    }
    const { model } = explorationModel();
    const target = ExplorationMenu.targetById(model, identity);
    if (!target) {
      return { ok: false, reason: marker(null) };
    }
    return { ok: true, model, target };
  }

  const table = {
    "exploration.root": explorationMenuSource("root"),
    "exploration.move": explorationMenuSource("move"),
    "exploration.look": explorationMenuSource("look"),
    "exploration.interact": explorationMenuSource("interact"),
    "exploration.wait": explorationMenuSource("wait"),
    "exploration.target": (params) => {
      const found = targetForIdentity(params);
      if (!found.ok) return found.reason;
      const menu = ExplorationMenu.targetMenuFor(found.model, found.target);
      return menu ? isolate(menu) : marker(null);
    },
    "exploration.keywords": (params) => {
      const found = targetForIdentity(params);
      if (!found.ok) return found.reason;
      const scripted = ExplorationMenu.scriptedAffordanceFor(found.target);
      const menu = ExplorationMenu.keywordMenuFor(found.model, found.target, scripted);
      return menu ? isolate(menu) : marker(null);
    },
    "exploration.suggestions": () => {
      // The frame belongs to the exploration family: an unavailable
      // exploration panel degrades like every other source.
      const gate = requireExplorationPanel();
      if (!gate.ok) return gate.reason;
      const state = committed();
      const contextActions = (state.panels && state.panels.context_actions) || null;
      if (!contextActions || contextActions.available === false) {
        // The common unavailable form carries the server-authored reason.
        return marker(panelReasonMessage(contextActions));
      }
      const suggestions = contextActions.suggestions || null;
      const status = suggestions && suggestions.status;
      if (SUGGESTIONS_RESOLVABLE.indexOf(status) === -1) {
        // `unavailable` (or no envelope at all) is the no-pane rule: degrade
        // so the consumer-side stack rule can leave the frame. `generating`
        // resolves to the builder's one muted row.
        return marker(null);
      }
      return isolate(ExplorationMenu.suggestionsMenu(suggestions));
    },
  };

  function resolve(descriptor) {
    try {
      const source = descriptor && descriptor.source;
      const entry = typeof source === "string" && Object.prototype.hasOwnProperty.call(table, source)
        ? table[source]
        : null;
      if (!entry) return marker(null);
      const menu = entry((descriptor && descriptor.params) || {});
      return menu === undefined || menu === null ? marker(null) : menu;
    } catch (err) {
      // Exception protection (design D-C): a throwing resolver degrades to
      // the marker with the committed exploration panel's authored reason
      // when it carries one; no exception ever reaches a caller.
      let reasonMessage = null;
      try {
        const state = committed();
        const panel = (state.panels && state.panels.exploration) || null;
        reasonMessage = panelReasonMessage(panel);
      } catch (inner) {
        // Even the reason read failed: degrade with a null reason.
        reasonMessage = null;
      }
      return marker(reasonMessage);
    }
  }

  return { resolve };
}

export default { createFrameResolver, UNRESOLVABLE };
