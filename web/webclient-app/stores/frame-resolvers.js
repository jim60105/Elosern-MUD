// Declarative-frame resolver registry (webclient-frame-resolver-registry,
// design doc D-A/D-B/D-C): maps a frame descriptor `{source, params}` to a
// menu derived from the COMMITTED presentation state at the moment of the
// call. Resolvers read only the state the protocol reducer has atomically
// committed under the revision gate (via the injected `getState`) and reuse
// the shipped menu builders verbatim — no label, row, or payload synthesis
// beyond what those builders already produce (root entries and `back` rows
// included, so reproducing them is not fabrication).
//
// The table is complete (retire-service-keyboard-frames): the exploration,
// combat, and creation families. The dock push sites mount descriptors; menu
// content exists only at resolution time.
//
// The exploration root is the scene overview (webclient-scene-overview-swap,
// AVG stage design §7): `exploration.root` resolves
// `ExplorationMenu.overviewMenu` — one reading-order menu of exits, people,
// objects, and a footer, with the router's `sections` geometry — and
// `exploration.target` resolves `ExplorationMenu.verbMenuFor`, the target's
// verb popover. The tab root (`model.menus.root`), `targetMenuFor`, and the
// move/look/interact submenus stay registered but unreachable until
// `webclient-retire-exploration-submenus` deletes them with their tests.
//
// Purity contract: resolving twice against one committed state returns deep-
// equal menus and mutates nothing — the builders are pure over their inputs,
// and every resolver here only reads `getState()` and calls them.
// The single permitted model-state exception is the combat resolver: the
// combat model (client-local skill/scale/AREA selection) lives in this
// closure and is preserved across panel replacements through the unchanged
// `CombatMenu.rebuildForPanel` seam. Repeat resolution of any combat
// descriptor against one committed state is idempotent.
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
import { NAVIGATION_ITEM_KEYS } from "./elosern/shared.js";
import CombatMenu from "../lib/combat_menu.js";
import CreationMenu from "../lib/creation_menu.js";
import stableStringify from "../lib/stable_stringify.js";

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

// The canonical `current_node` fallback when `local_map` is unavailable.
// `local_map` (the minimap) legitimately reports unavailable whenever the
// actor has no recorded map-knowledge yet (map-knowledge spec's
// "parse_knowledge isolates corrupt records" requirement treats a missing
// record the same as a corrupt one) — most notably for a freshly created
// character standing in 虛境 before its very first move. That does NOT mean
// the exit itself is untraversable: `webclient-exploration-menu`'s move-row
// `enabled` is server-authored independently of the minimap. `context_actions`
// carries the same canonical `current_node` embedded in every `explore.move`
// affordance's own `params` (`web/webclient/presentation/affordances.py`
// `_move_entries`), with no map-knowledge dependency, so it is read here as
// the fallback source instead of leaving every exit permanently disabled.
function currentNodeFromAffordances(contextActions) {
  const affordances = (contextActions && contextActions.affordances) || [];
  const moveEntry = affordances.find(
    (entry) => entry && entry.action_id === "explore.move" && entry.params,
  );
  return (moveEntry && moveEntry.params.current_node) || null;
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
    const contextActions = panels.context_actions || null;
    const currentNode =
      (panels.local_map && panels.local_map.current_node) ||
      currentNodeFromAffordances(contextActions) ||
      null;
    const suggestions = (contextActions && contextActions.suggestions) || null;
    return {
      panel,
      currentNode,
      suggestions,
      model: ExplorationMenu.buildMenus(panel, { currentNode, suggestions }),
    };
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

  // The scene overview (webclient-scene-overview-swap D1): the exploration
  // root frame. One reading-order menu of the committed panel's exits,
  // people, objects, and footer, carrying the router's `sections` geometry.
  // The same `currentNode` fallback the tab root used feeds the exit
  // payloads, so they stay byte-identical.
  const explorationOverviewSource = () => {
    const gate = requireExplorationPanel();
    if (!gate.ok) return gate.reason;
    const { panel, currentNode, suggestions } = explorationModel();
    return isolate(ExplorationMenu.overviewMenu(panel, { currentNode, suggestions }));
  };

  // The top navigation bar's exploration entries (webclient-scene-overview-
  // swap): the character status, quest, and inventory surfaces. The scene
  // overview carries no navigation entry — the bar is their sole
  // keyboard-visible stop — so the bar derives them from the same shipped
  // builder the retired tab root used, filtered to the navigation keys.
  const explorationNavigationSource = () => {
    const gate = requireExplorationPanel();
    if (!gate.ok) return gate.reason;
    const { panel, suggestions } = explorationModel();
    const menu = ExplorationMenu.buildMenus(panel, { currentNode: null, suggestions });
    return isolate({
      items: menu.menus.root.items.filter((item) => NAVIGATION_ITEM_KEYS.has(item.key)),
    });
  };

  // --- combat family helpers -------------------------------------------------

  // The preserved CombatMenu tree for the active combat panel (client-local
  // skill/scale/AREA selection). The ONE place the registry holds model
  // state — the declared exception in the purity requirement. It follows the
  // committed panel through `rebuildForPanel` exactly as the deleted copy
  // push sites did, keyed on the panel's stable content signature so repeat
  // resolution against one committed state is idempotent (no rebuild, no
  // further model change).
  let combat = null;
  let combatPanelSig = null;

  function combatPanelOf() {
    const state = committed();
    const panel = (state.panels && state.panels.context_actions) || null;
    return panel && panel.kind === "combat" ? panel : null;
  }

  // The combat model at this instant, or null outside the combat panel form.
  // A non-combat committed state CLEARS the held model: leaving combat (or a
  // teardown to another mode) can never leave stale selection state behind
  // for a re-adoption of a byte-identical panel.
  function combatModel() {
    const panel = combatPanelOf();
    if (!panel) {
      combat = null;
      combatPanelSig = null;
      return null;
    }
    const sig = stableStringify(panel);
    if (combat && sig === combatPanelSig) {
      return combat; // same committed panel: idempotent, no rebuild
    }
    const previous = combat
      ? { skillKey: combat.focusSkillKey, page: combat.page || 0, skillByKey: combat.skillByKey }
      : {};
    combat = CombatMenu.rebuildForPanel(combat, panel, previous);
    combatPanelSig = sig;
    return combat;
  }

  function indexParam(params, name) {
    const value = params && params[name];
    return typeof value === "number" && Number.isInteger(value) && value >= 0 ? value : -1;
  }

  function skillKeyParam(params) {
    const value = params && params.skillKey;
    return typeof value === "string" && value !== "" ? value : null;
  }

  // --- creation family helpers ------------------------------------------------

  function requireCreationPanel() {
    const state = committed();
    const panel = (state.panels && state.panels.creation) || null;
    if (!panel || panel.available !== true) {
      return { ok: false, reason: marker(panelReasonMessage(panel)) };
    }
    return { ok: true, panel };
  }

  const creationMenuSource = (menuKey) => () => {
    const gate = requireCreationPanel();
    if (!gate.ok) return gate.reason;
    return isolate(CreationMenu.buildMenus(gate.panel).menus[menuKey]);
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
    "exploration.root": explorationOverviewSource,
    "exploration.navigation": explorationNavigationSource,
    "exploration.move": explorationMenuSource("move"),
    "exploration.look": explorationMenuSource("look"),
    "exploration.interact": explorationMenuSource("interact"),
    "exploration.wait": explorationMenuSource("wait"),
    "exploration.target": (params) => {
      const found = targetForIdentity(params);
      if (!found.ok) return found.reason;
      const menu = ExplorationMenu.verbMenuFor(found.model, found.target);
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

    // --- combat family ------------------------------------------------------
    // The menus are the CombatMenu model's own; the model instance lives in
    // this closure (the declared selection-state exception) and follows the
    // committed `context_actions` combat panel through `rebuildForPanel`.
    "combat.root": () => {
      const combat = combatModel();
      return combat ? isolate(combat.menus.root) : marker(null);
    },
    "combat.categories": () => {
      const combat = combatModel();
      return combat ? isolate(combat.menus.categories) : marker(null);
    },
    "combat.forfeit": () => {
      const combat = combatModel();
      return combat ? isolate(combat.menus.forfeit) : marker(null);
    },
    "combat.category": (params) => {
      const combat = combatModel();
      if (!combat) return marker(null);
      // An out-of-range index is the identity-loss degradation (the builder
      // itself would render an empty frame; the table contract is the
      // marker).
      const category = ((combat.panel.skills) || [])[indexParam(params, "categoryIndex")];
      if (!category) return marker(null);
      const menu = CombatMenu.openCategory(combat, indexParam(params, "categoryIndex"));
      return menu ? isolate(menu) : marker(null);
    },
    "combat.group": (params) => {
      const combat = combatModel();
      if (!combat) return marker(null);
      const group = (((combat.panel.skills || [])[indexParam(params, "categoryIndex")] || {}).groups || [])[
        indexParam(params, "groupIndex")
      ];
      if (!group) return marker(null);
      const menu = CombatMenu.openGroup(
        combat,
        indexParam(params, "categoryIndex"),
        indexParam(params, "groupIndex")
      );
      return menu ? isolate(menu) : marker(null);
    },
    // A vanished skill key is the identity-loss degradation; a skill that
    // cannot open (disabled/terminal) resolves null like the push site.
    "combat.skill": (params) => {
      const combat = combatModel();
      if (!combat) return marker(null);
      const menu = CombatMenu.openSkill(combat, skillKeyParam(params));
      return menu ? isolate(menu) : marker(null);
    },
    "combat.target": (params) => {
      const combat = combatModel();
      if (!combat) return marker(null);
      const menu = CombatMenu.openSkillTargets(combat, skillKeyParam(params));
      return menu ? isolate(menu) : marker(null);
    },

    // --- creation family ----------------------------------------------------
    "creation.root": creationMenuSource("root"),

    "creation.presets": creationMenuSource("presets"),
    // The custom/concept forms render outside the dock (the overlay owns the
    // form); the frame exists so Escape has a level to pop. The empty marker
    // frame is the same shape the push site pushed.
    "creation.form": (params) => {
      const gate = requireCreationPanel();
      if (!gate.ok) return gate.reason;
      const view = params && params.view;
      if (view !== "custom" && view !== "concept") {
        return marker(null);
      }
      return { items: [], focusKey: null };
    },
    // The confirmation stage content: exactly the items the push site built
    // (the reset warning / the activate confirmation), never stored copies.
    "creation.confirm": (params) => {
      const gate = requireCreationPanel();
      if (!gate.ok) return gate.reason;
      const kind = params && params.kind;
      let menu;
      if (kind === "reset") {
        menu = CreationMenu.confirmMenu(
          "確認清除角色草稿？此操作無法回復。",
          CreationMenu.RESET_ACTION,
          {},
          CreationMenu.RESET_DISPLAY
        );
      } else if (kind === "preset" || kind === "custom") {
        menu = CreationMenu.activateConfirm(kind === "preset" ? (params.presetKey ?? null) : null);
      } else {
        return marker(null);
      }
      return isolate(menu);
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

  return {
    resolve,
    // The combat model accessor (the declared selection-state home): the
    // store's client-local combat interactions (focus-skill recording, AREA
    // toggle, scale/shorthand choice, submit payload building) act on this
    // one model instance — never a second copy. Null outside the combat
    // panel form; a non-combat committed state clears it (duck round-2:
    // leaving combat can never hand stale selection to a re-adoption).
    combatModel,
  };
}

export default { createFrameResolver, UNRESOLVABLE };
