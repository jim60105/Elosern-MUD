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
// The exploration root is an empty, resolvable menu (exploration-room-
// actions design D2): `exploration.root` resolves `{items: [], title}` under
// the exploration panel gate, so it never degrades while the panel is
// available and no key is claimed by a root item. The exits are the exit
// compass's, read through `explorationExits`; the people and objects are the
// presence rail's, read through `explorationPresence`; an interact target's
// verbs are the client-local verb card's, read through `explorationVerbs`
// (exploration-presence-rail); and the room actions (查看房間, the wait card,
// the suggestions card) are the place card's and the 建議 pill's, read through
// `explorationRoomLook`, `explorationWait`, and `explorationSuggestions`
// (exploration-room-actions). None of them is a router frame: the retired
// `exploration.target`, `exploration.wait`, and `exploration.suggestions`
// sources are unregistered. `exploration.navigation` is the top navigation
// bar's own entry set (the character status, quest, and inventory surfaces,
// which no dock frame carries any more). The move/look/interact submenus are
// retired (webclient-retire-exploration-submenus): their sources are
// unregistered, so a stray descriptor for one degrades to the marker and
// pops, exactly like every other unregistered source.
// `ExplorationMenu.navigationItems` outlives them, because the bar keeps
// reading it.
// The scripted-keyword frame is retired the same way (webclient-talk-open-
// dock): its source is unregistered, because the v3 panel carries no keyword
// list and 交談 dispatches `explore.talk_open` in one step, so no push site
// can name it any more.
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
import CombatMenu from "../lib/combat_menu.js";
import CreationMenu from "../lib/creation_menu.js";
import SkillUseMenu from "../lib/skill_use_menu.js";
import stableStringify from "../lib/stable_stringify.js";

// The one degradation marker shape. Frozen so a consumer can never mutate
// the shared instance into a payload.
export const UNRESOLVABLE = Object.freeze({ unresolvable: true, reason: null });

// The suggestions statuses the suggestions card may present (the
// options-surface statuses minus `unavailable`, which forbids any card).
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

  // The shared exploration build: the ExplorationMenu model over the panels
  // committed right now.
  function explorationModel() {
    const state = committed();
    const panels = state.panels || {};
    const panel = panels.exploration || {};
    const contextActions = panels.context_actions || null;
    const currentNode =
      (panels.local_map && panels.local_map.current_node) ||
      currentNodeFromAffordances(contextActions) ||
      null;
    return {
      panel,
      currentNode,
      model: ExplorationMenu.buildMenus(panel, { currentNode }),
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

  // The exploration root (exploration-room-actions design D2): an empty,
  // resolvable menu. An unavailable or absent panel still degrades it into
  // the router's single marker-reason row.
  const explorationRootSource = () => {
    const gate = requireExplorationPanel();
    if (!gate.ok) return gate.reason;
    return { items: [], focusKey: null, title: "場景" };
  };

  // The exit compass's rows (exploration-exit-compass design D2/D9): the
  // committed exits, outside the router's root frame, with the SAME
  // `currentNode` the root used, so every `explore.move` payload stays
  // byte-identical. The dialogue screen's `↦ 移動…` list reads them too.
  // An unavailable or absent exploration panel has no exits, and a throwing
  // build degrades the same way (the registry's exception guard, design D-C):
  // no exception reaches the view build.
  const explorationExits = () => {
    try {
      const gate = requireExplorationPanel();
      if (!gate.ok) return { rows: [], currentNode: null };
      const { panel, currentNode } = explorationModel();
      return { rows: isolate(ExplorationMenu.exitTargets(panel, { currentNode })), currentNode };
    } catch (err) {
      return { rows: [], currentNode: null };
    }
  };

  // The presence rail's entries (exploration-presence-rail design D2): the
  // committed people and objects in the retired rows' order, outside the
  // router. `null` means the exploration panel is absent, unavailable, or
  // its build threw — distinct from `[]`, an available room with nobody and
  // nothing in it — so a degraded commit never reads as "everyone left".
  const explorationPresence = () => {
    try {
      const gate = requireExplorationPanel();
      if (!gate.ok) return null;
      return isolate(ExplorationMenu.presenceEntries(gate.panel));
    } catch (err) {
      return null;
    }
  };

  // An interact target's verb card (exploration-presence-rail design D2):
  // `verbMenuFor` over the target the committed panel lists for `identity`
  // right now, or null when the panel or the target is gone.
  const explorationVerbs = (identity) => {
    try {
      const gate = requireExplorationPanel();
      if (!gate.ok || identity === undefined || identity === null) return null;
      const { model } = explorationModel();
      const target = ExplorationMenu.targetById(model, identity);
      return target ? isolate(ExplorationMenu.verbMenuFor(model, target)) : null;
    } catch (err) {
      return null;
    }
  };

  // The place card's 查看房間 row (exploration-room-actions design D3): the
  // committed room's `lookItems` row, so its `explore.look` payload and
  // command echo are the retired footer chip's. Null when the panel is
  // unavailable or carries no room.
  const explorationRoomLook = () => {
    try {
      const gate = requireExplorationPanel();
      if (!gate.ok) return null;
      const row = ExplorationMenu.lookItems(gate.panel).find((item) => item.key === "look-room");
      return row ? isolate(row) : null;
    } catch (err) {
      return null;
    }
  };

  // The wait card's rows (exploration-room-actions design D5): `waitItems`
  // without its router back row. Null when the panel is unavailable.
  const explorationWait = () => {
    try {
      const gate = requireExplorationPanel();
      if (!gate.ok) return null;
      return isolate(ExplorationMenu.waitItems().filter((item) => !item.goBack));
    } catch (err) {
      return null;
    }
  };

  // The suggestions card's content (exploration-room-actions design D4):
  // the committed envelope's status and `suggestionsMenu` rows without the
  // router back row. Null when the exploration panel or `context_actions` is
  // unavailable or absent, or the status is `unavailable` (or missing): no
  // card and no pill exist then.
  const explorationSuggestions = () => {
    try {
      const gate = requireExplorationPanel();
      if (!gate.ok) return null;
      const state = committed();
      const contextActions = (state.panels && state.panels.context_actions) || null;
      if (!contextActions || contextActions.available === false || contextActions.kind === "combat") {
        return null;
      }
      const suggestions = contextActions.suggestions || null;
      const status = suggestions && suggestions.status;
      if (SUGGESTIONS_RESOLVABLE.indexOf(status) === -1) {
        return null;
      }
      const menu = ExplorationMenu.suggestionsMenu(suggestions);
      return isolate({ status, items: menu.items.filter((item) => !item.goBack) });
    } catch (err) {
      return null;
    }
  };

  // The top navigation bar's exploration entries (webclient-scene-overview-
  // swap): the character status, quest, and inventory surfaces. The scene
  // overview carries no navigation entry — the bar is their sole
  // keyboard-visible stop — so the bar derives them from the dedicated
  // `navigationItems` builder, which the retired tab root also consumed.
  const explorationNavigationSource = () => {
    const gate = requireExplorationPanel();
    if (!gate.ok) return gate.reason;
    const state = committed();
    const panel = (state.panels && state.panels.exploration) || null;
    return isolate({ items: ExplorationMenu.navigationItems(panel) });
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

  // Drop the held combat model outright (webclient-party-command-selection):
  // a commanded-actor switch discards every unconfirmed client-local skill,
  // scale and target selection, so the next build starts from the new actor's
  // canonical choices. Confirmed server draft entries are never touched here.
  function resetCombatSelection() {
    combat = null;
    combatPanelSig = null;
  }

  function indexParam(params, name) {
    const value = params && params[name];
    return typeof value === "number" && Number.isInteger(value) && value >= 0 ? value : -1;
  }

  function skillKeyParam(params) {
    const value = params && params.skillKey;
    return typeof value === "string" && value !== "" ? value : null;
  }

  // --- skill-use family helpers -----------------------------------------------

  // The SkillBook use model (skillbook-authoritative-casting D6): the second
  // declared model-state home, holding only the client-local AREA selection
  // for the committed `skill_use` preview. It follows the committed panel
  // through `createModel` (vanished or disabled selections drop), keyed on
  // the panel's content signature so repeat resolution is idempotent. Any
  // other committed state (no preview, another skill, a mode other than
  // exploration) clears it, so a stale selection can never be submitted.
  let skillUse = null;
  let skillUsePanelSig = null;

  function skillUseModel(skillKey) {
    const state = committed();
    const panel = (state.panels && state.panels.skill_use) || null;
    if (
      !panel ||
      panel.available !== true ||
      state.mode !== "exploration" ||
      (skillKey !== undefined && skillKey !== null && panel.skill.key !== skillKey)
    ) {
      skillUse = null;
      skillUsePanelSig = null;
      return null;
    }
    const sig = stableStringify(panel);
    if (skillUse && sig === skillUsePanelSig) {
      return skillUse;
    }
    skillUse = SkillUseMenu.createModel(panel, skillUse);
    skillUsePanelSig = sig;
    return skillUse;
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

  const table = {
    "exploration.root": explorationRootSource,
    "exploration.navigation": explorationNavigationSource,

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
    // The actor selector frame (webclient-party-command-selection): one row
    // per committed allied actor with its authoritative draft status.
    "combat.actor": () => {
      const combat = combatModel();
      return combat ? isolate(combat.menus.actor) : marker(null);
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
      const category = ((combat.panel.choices && combat.panel.choices.skills) || [])[
        indexParam(params, "categoryIndex")
      ];
      if (!category) return marker(null);
      const menu = CombatMenu.openCategory(combat, indexParam(params, "categoryIndex"));
      return menu ? isolate(menu) : marker(null);
    },
    "combat.group": (params) => {
      const combat = combatModel();
      if (!combat) return marker(null);
      const group = ((((combat.panel.choices && combat.panel.choices.skills) || [])[indexParam(params, "categoryIndex")] || {}).groups || [])[
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

    // --- skill-use family ---------------------------------------------------
    // The book's hand-over frames. A preview that is unavailable, names
    // another skill, or outlived exploration degrades them (pop).
    "skilluse.root": (params) => {
      const model = skillUseModel(skillKeyParam(params));
      return model ? isolate(SkillUseMenu.useMenu(model)) : marker(null);
    },
    "skilluse.scale": (params) => {
      const model = skillUseModel(skillKeyParam(params));
      if (!model || !(model.panel.skill.freeform_scales || []).length) return marker(null);
      return isolate(SkillUseMenu.scaleMenu(model));
    },
    "skilluse.opening": (params) => {
      const model = skillUseModel(skillKeyParam(params));
      const identity = params && params.identity;
      if (!model || typeof identity !== "number") return marker(null);
      const menu = SkillUseMenu.openingMenu(model, identity);
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
    explorationExits,
    explorationPresence,
    explorationVerbs,
    explorationRoomLook,
    explorationWait,
    explorationSuggestions,
    // The combat model accessor (the declared selection-state home): the
    // store's client-local combat interactions (focus-skill recording, AREA
    // toggle, scale/shorthand choice, submit payload building) act on this
    // one model instance — never a second copy. Null outside the combat
    // panel form; a non-combat committed state clears it (duck round-2:
    // leaving combat can never hand stale selection to a re-adoption).
    combatModel,
    // Drop the held combat model (the commanded-actor switch): the store's
    // selection home is the registry's, so only the registry can clear it.
    resetCombatSelection,
    // The SkillBook use model accessor (the second declared selection home):
    // the store's AREA toggle and confirm read this one instance. Null unless
    // an exploration `skill_use` preview for `skillKey` is committed.
    skillUseModel,
  };
}

export default { createFrameResolver, UNRESOLVABLE };
