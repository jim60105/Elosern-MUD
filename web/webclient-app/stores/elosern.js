// C1 (webclient-vue-07-wire-store): the single-writer reactive store over the
// preserved DOM-independent logic (roadmap Wave C start; the store is the
// "strict and atomic, subscribers see only committed state" invariant from
// webclient-desktop-shell). The store is driven in tests by raw reducer
// inputs (design D5); the live evennia.js OOB binding (C3), the browser-bridge
// (C2), and the component re-binding (C4) all consume the slices exposed here.
//
// Architecture (design D1-D5, the A2 store-slice contract in
// docs/development/frontend-vue-architecture.md):
// - D1: the preserved `Protocol` reducer (`lib/protocol.js`) is the store's
//   core; epoch/revision/panel semantics are delegated to it, never
//   re-implemented.
// - D2: every reducer commit publishes one new committed view object, replaced
//   wholesale — no subscriber ever observes a partially applied panel state.
// - D4: the remaining preserved modules are consumed through the A2 lib
//   wrappers (the keyboard router for focus, the narrative markup pipeline for
//   narrative tokens, the local-map model, and the choice-point / option-card
//   logic) rather than being re-implemented.
// - D5: the transport transport is an attachable `setSender` seam; a single
//   dispatch entry routes every mutation (dispatch-only, one mutation in
//   flight) with the tested lock semantics.

import { computed, ref } from "vue";
import { defineStore } from "pinia";

import Protocol from "../lib/protocol.js";
import KeyboardRouter from "../lib/keyboard_router.js";
import NarrativeMarkup from "../lib/narrative_markup.js";
import LocalMap from "../lib/local_map.js";
import ChoicePointLogic from "../lib/choicepoint.js";
import OptionCards from "../lib/option_cards.js";
import CombatMenu from "../lib/combat_menu.js";
import CreationMenu from "../lib/creation_menu.js";
import { actionIntentForItem, disabledReasonText, dockItemKeys } from "../components/dock-items.js";

const NARRATIVE_KINDS = ["in", "out", "sys", "err"];
const MAX_NARRATIVE_LINES = 500;
const MAX_COMMAND_HISTORY = 50;
// The registered production panel allowlist (mirrors the UMD allowlist in
// elosern/protocol.js and web/webclient/presentation/protocol.py).
const PANEL_ALLOWLIST = [
  "art",
  "status",
  "context_actions",
  "local_map",
  "services",
  "creation",
  "exploration",
  "character",
];

// Stable JSON with sorted keys: content comparison that is insensitive to
// key order, so committed panels can be compared across reducer commits. A
// `seen` set makes it safe on the reactive (proxied) view objects: a cycle
// is rendered as `~` instead of recursing forever.
function stableStringify(value, seen) {
  if (value === null || typeof value !== "object") {
    return JSON.stringify(value);
  }
  seen = seen || new Set();
  if (seen.has(value)) {
    return "~";
  }
  seen.add(value);
  let s;
  if (Array.isArray(value)) {
    s = "[" + value.map((item) => stableStringify(item, seen)).join(",") + "]";
  } else {
    const keys = Object.keys(value).sort();
    s = "{" + keys.map((key) => JSON.stringify(key) + ":" + stableStringify(value[key], seen)).join(",") + "}";
  }
  seen.delete(value);
  return s;
}

// Display conversion of the committed `server_time` (unit conversion at
// display only, mirroring the B1 TopBar `timeLabel` fixture shape).
function formatTimeLabel(serverTime) {
  if (!serverTime) {
    return null;
  }
  const hour = String(serverTime.hour).padStart(2, "0");
  const minute = String(serverTime.minute).padStart(2, "0");
  return `${serverTime.season_label} ${serverTime.day_in_season} 日 · ${hour}:${minute}`;
}

// The committed transport phase maps to the ConnectOverlay status slice the
// B1 component accepts (connecting/waiting/offline/ready).
function connectionStatusFor(connected, phase) {
  if (!connected) {
    return "offline";
  }
  if (phase === "active") {
    return "ready";
  }
  if (phase === "detached") {
    return "waiting";
  }
  return "connecting";
}

// The focus-frame items from the committed `context_actions` panel: the
// exploration form's affordances (action + navigation entries) or the combat
// form's participants (target entries).
function focusItemsFor(panel) {
  if (!panel || panel.available !== true) {
    return [];
  }
  if (panel.kind === "exploration") {
    return Array.isArray(panel.affordances) ? panel.affordances : [];
  }
  if (panel.kind === "combat") {
    // Combat participants carry a numeric `identity` and a `display_name`;
    // normalize them to the preserved target-entry shape the B2 dock-items
    // contract expects ({ identity, label, enabled }).
    const participants = Array.isArray(panel.participants) ? panel.participants : [];
    return participants.map((p) => ({
      identity: p.identity == null ? "" : String(p.identity),
      label: p.display_name || p.label || "",
      enabled: p.enabled !== false,
    }));
  }
  return [];
}

export const useElosernStore = defineStore("elosern", () => {
  // D1: the preserved reducer is the store core (CJS-interop import; the UMD
  // source and its Node gate are never edited).
  const reducer = Protocol.createStore();

  // D5: client-local dispatch bookkeeping (the tested legacy action-client
  // semantics; the transport send is an attachable seam).
  let inFlight = null; // {requestId, presentationRevision}
  let uncertain = false;
  let requestCounter = 0;
  let sender = null; // { sendAction(envelope), sendText(text) } — C3 attaches evennia.js
  let lastSurface = null;
  let lastTarget = null;
  // The confirm source ("pointer" or "keyboard") of the latest router confirm;
  // a pointer confirm is a client-local target selection (no OOB dispatch),
  // while a keyboard confirm submits the OOB cast (spec: selection is
  // client-local until submission).
  let lastConfirmSource = "keyboard";
  // A dispatched OOB mutation that has not yet been confirmed (its result
  // was withheld or the presentation has not committed). Set on dispatch,
  // cleared only when the in-flight gate releases; a transport loss while it
  // is set marks the mutation uncertain (spec: submitted-but-unconfirmed
  // before transport loss is treated as unconfirmed, shown by the notice).
  let mutationSubmitted = false;
  // The request ID of the last dispatched OOB mutation, used to correlate the
  // client's observed result with the specific in-flight request (a prior
  // result for a different request ID does not confirm the current one).
  let lastSubmittedRequestId = null;
  let prompt = "";
  // The raw committed item behind each focus key (the router's submit event
  // carries only the projected {label, enabled, description, key}; intents,
  // surfaces, and identities are read back from the raw item, never invented).
  let dockRawByKey = {};
  // The preserved CombatMenu tree for the active combat panel (client-local
  // skill/scale/target selection state), or null outside combat mode.
  let combat = null;

  // The legacy character-creation dock port (the preserved CreationMenu model
  // driving the keyboard router in creation mode, design D4): the current dock
  // stage (root/presets/custom/confirm), the built menus, and the save awaiting
  // its confirmation. Null outside creation mode.
  let creation = null; // {view, menus, confirmItems, pendingActivate, pendingActivateKey, pendingSaveRequestId, panelSig}

  // D4: the imported keyboard router owns the focus state; its events are
  // routed through the same store actions (a broken renderer must never
  // break the reducer).
  const router = KeyboardRouter.createRouter({
    onEvent: onRouterEvent,
  });

  // G1 re-home: the test helpers (and a user Escape at the root frame) call
  // `router.reset()` with no menu, which empties the frame stack and leaves
  // Arrow/Enter as no-ops. Wrap the preserved router's `reset` so a menu-less
  // reset immediately re-homes the root frame from the committed
  // `context_actions` panel — a dead keyboard frame can never survive a reset.
  {
    const originalReset = router.reset;
    router.reset = function (menu) {
      const depth = originalReset.call(router, menu);
      if (!menu && router.depth() === 0) {
        rehomeFrame(reducer.getState());
      }
      return depth;
    };
  }

  // The active sub-dock surface (null | "character" | "services"): which
  // re-homed sub-dock currently owns the action-dock surface. The
  // suggestions section must never render while one is active (spec
  // webclient-options-surface). Set by the sub-dock panels on mount/unmount.
  // Declared before the initial view so `buildView` can read it.
  const activeSubDock = ref(null);
  function setActiveSubDock(value) {
    activeSubDock.value = value;
    // Publish so `store.view.activeSubDock` (read by the action dock)
    // reflects the change; the view is a rebuilt snapshot, not live-bound.
    publishView();
  }

  const view = ref(initialView());
  const narrative = ref([]);
  const commandHistory = ref([]);
  const seenIndex = ref(0);
  // C4: the last OOB `ui_snapshot` / `ui_update` receive result. A rejected
  // (malformed) presentation is the "renderer cannot render" signal that
  // triggers the one-sync-per-episode auto-resync.
  const lastPanelRejection = ref(null);

  // Open one skill's target (or 威力 scale) menu from the root/skills menu,
  // mirroring the legacy plugin's `openCombatSkill`.
  function openCombatSkill(skillKey) {
    if (!combat) {
      return;
    }
    combat.focusSkillKey = skillKey;
    const menu = CombatMenu.openSkill(combat, skillKey);
    if (menu) {
      router.pushMenu(menu);
      if (menu.items.length > 0 && menu.items[0].scaleChoice) {
        // The freeform scale step preselects 威力×1 (the default behavior).
        router.focusItemByKey("scale-1");
      }
    }
    publishView();
  }

  function onRouterEvent(name, payload) {
    if (name === "focus" || name === "disabled") {
      if (name === "focus" && combat) {
        // A combat target-row focus is a client-local selection (spec: focus
        // and selection remain client-local until submission); record the
        // selected identity without dispatching any OOB action.
        const item = payload && payload.item;
        if (
          item &&
          typeof item.key === "string" &&
          item.key.startsWith("target-") &&
          item.payload &&
          Array.isArray(item.payload.target_ids) &&
          item.payload.target_ids.length > 0
        ) {
          lastTarget = String(item.payload.target_ids[0]);
        }
      }
      publishView();
      return;
    }
    if (name === "menu-closed" || name === "escape-root") {
      if (creation) {
        handleCreationMenuEvent(name);
      }
      return;
    }
    if (name !== "submit" && name !== "space") {
      return;
    }
    const item = payload && payload.item;
    if (!item) {
      return;
    }
    // The creation dock owns the router in creation mode (the legacy
    // creation_dock.js keyboard journey): submenu opens, preset-card saves,
    // confirmation dispatches, and cancel pops one level.
    if (creation && handleCreationItem(item)) {
      return;
    }
    // Combat keyboard hierarchy (the preserved CombatMenu model, mirroring the
    // legacy elosern_ui plugin's routing): open-skill / attack open a skill's
    // scale or target frame, skills / forfeit open their submenus, Space
    // toggles AREA candidates, and confirm submits the exact payload.
    if (combat) {
      if (name === "space") {
        if (item.actionId === "toggle-target" && item.payload && combat.focusSkillKey) {
          CombatMenu.toggleArea(combat, combat.focusSkillKey, item.payload.identity);
          publishView();
        }
        return;
      }
      // "open" items push a submenu (no OOB packet is sent).
      if (item.actionId === "open-skill" && item.payload) {
        openCombatSkill(item.payload.skillKey);
        return;
      }
      if (item.actionId === "choose-scale" && item.payload) {
        if (combat.focusSkillKey && CombatMenu.chooseScale(combat, combat.focusSkillKey, item.payload.scale)) {
          const targetMenu = CombatMenu.openSkillTargets(combat, combat.focusSkillKey);
          if (targetMenu) {
            router.pushMenu(targetMenu);
            publishView();
          }
        }
        return;
      }
      if (item.actionId === "choose-shorthand" && item.payload) {
        if (combat.focusSkillKey) {
          CombatMenu.chooseShorthand(combat, combat.focusSkillKey, item.payload.shorthand);
          publishView();
        }
        return;
      }
      if (item.key === "attack") {
        openCombatSkill(CombatMenu.BASIC_ATTACK_KEY);
        return;
      }
      if (item.key === "skills") {
        router.pushMenu(combat.menus.skills);
        publishView();
        return;
      }
      if (item.key === "forfeit") {
        router.pushMenu(combat.menus.forfeit);
        publishView();
        return;
      }
      // AREA confirm: build the exact payload from the live selection.
      if (item.confirm && combat.focusSkillKey) {
        const skill = combat.skillByKey[combat.focusSkillKey];
        if (skill && skill.targetSpec === "area") {
          const areaPayload = CombatMenu.areaPayload(skill);
          if (areaPayload) {
            dispatchAction("combat.cast", areaPayload);
          }
          return;
        }
      }
      // SINGLE-target rows: the selection is client-local (records the
      // identity). A keyboard confirm submits the OOB cast; a pointer confirm
      // is a selection only (no OOB dispatch, per the spec's client-local
      // selection-until-submission rule).
      if (
        typeof item.key === "string" &&
        item.key.startsWith("target-") &&
        item.payload &&
        Array.isArray(item.payload.target_ids) &&
        item.payload.target_ids.length > 0
      ) {
        lastTarget = String(item.payload.target_ids[0]);
        if (lastConfirmSource === "keyboard") {
          dispatchAction("combat.cast", item.payload);
        }
        publishView();
        return;
      }
      // Real OOB action items (combat.cast / combat.flee / combat.forfeit).
      if (item.actionId) {
        dispatchAction(item.actionId, item.payload || {});
        return;
      }
    }
    // The router's submit event carries only the projected menu item
    // ({label, enabled, description, key}); the OOB intent, navigation
    // surface, and target identity are read back from the raw committed
    // item looked up by the preserved focus key — never re-derived from the
    // projected item (which lacks `action_id`/`surface`/`identity`).
    const raw = (item.key !== undefined && dockRawByKey[item.key]) || item;
    const intent = actionIntentForItem(raw);
    if (intent) {
      dispatchAction(intent.action_id, intent.payload);
      return;
    }
    if (raw.navigation === true && typeof raw.surface === "string") {
      lastSurface = raw.surface;
    } else if (raw.identity !== undefined) {
      lastTarget = String(raw.identity);
    }
    publishView();
  }

  function handleTransportLifecycle(prev, rs) {
    if (rs.generation !== prev.generation) {
      inFlight = null;
      requestCounter = 0;
      // `uncertain` is intentionally NOT cleared here: a mutation whose result
      // was withheld by a mid-flight detach stays flagged across the
      // reconnect (the C3 transport's `clearUncertain` releases it only when
      // the result is observed).
    }
    if (prev.phase !== "detached" && rs.phase === "detached" && inFlight) {
      uncertain = true;
      inFlight = null;
    }
  }

  // D5: the in-flight lock releases with the tested legacy action-client
  // semantics. A matching `ui_action_result` (same request id, same epoch)
  // sets the declared presentation revision; the lock then releases only
  // when the committed revision reaches that revision (immediately when none
  // was declared, unconditionally for a `no_puppet` rejection; a `stale`
  // outcome keeps the lock until the recovery snapshot commits — the
  // `ui_sync` re-request itself is the C3 transport's job).
  function handleActionResult(prev, rs) {
    if (!inFlight) {
      return;
    }
    const result = rs.lastActionResult;
    const prevResult = prev ? prev.lastActionResult : null;
    if (stableStringify(result) === stableStringify(prevResult)) {
      return;
    }
    if (!result || result.requestId !== inFlight.requestId) {
      return;
    }
    if (result.epoch !== rs.activeEpoch) {
      return;
    }
    // A cached duplicate or a result for a foreign request never unlocks.
    inFlight.presentationRevision = result.presentationRevision;
    if (result.outcome === "rejected" && result.code === "no_puppet") {
      // The puppet is gone; no presentation will ever gate this rejection,
      // so the lock is released unconditionally.
      inFlight = null;
      // A no-puppet rejection is terminal: the mutation is resolved, so a later
      // transport loss must not re-flag it as uncertain.
      mutationSubmitted = false;
    }
  }

  // Read the legacy action client's in-flight gate. Returns true while a
  // submitted mutation is unconfirmed (its result has not been observed by the
  // client), false when confirmed (result observed, gate released), or null
  // when the client is unavailable (mid re-bootstrap).
  function clientInFlight() {
    const c =
      typeof window !== "undefined" &&
      window.Elosern &&
      window.Elosern.actions &&
      window.Elosern.actions.client;
    return c && c.isInFlight ? c.isInFlight() : null;
  }

  // The revision-gated release: the lock releases once the committed
  // revision reaches the in-flight request's declared presentation revision.
  // A not-yet-declared target (no result received yet) keeps the lock held,
  // exactly like the legacy action client's `releaseIfReady`/
  // `onPresentationAccepted` pair.
  function releaseIfReady(rs) {
    if (!inFlight) {
      return;
    }
    const target = inFlight.presentationRevision;
    if (target !== null && rs.revision !== null && rs.revision >= target) {
      inFlight = null;
      // The store's gate releasing means the committed revision reached the
      // declared presentation revision. If the client's gate is also released
      // (the client observed the result = confirmed), the mutation is resolved,
      // so a later transport loss must not re-flag it as uncertain.
      if (clientInFlight() === false) {
        mutationSubmitted = false;
      }
    }
  }

  // D4: the focus menu is rebuilt only when the committed `context_actions`
  // content changes (stable-stringified comparison against the signature of
  // the last built menu — a store-local signature, NOT the stale previous
  // view, which would re-trigger the rebuild through the router's focus
  // events and re-enter publishView forever), preserving the component
  // dock's preserved `action-`/`target-` item keys as the single key
  // contract.
  let lastMenuSig = null;
  // G1 re-home: repopulate the root frame from the committed `context_actions`
  // panel after a menu-less `router.reset()` emptied the stack. Called by the
  // wrapped `router.reset` (synchronous) and by `rebuildFocusMenu`'s re-home
  // path (the commit-driven safety net).
  function rehomeFrame(rs) {
    const panel = (rs.panels && rs.panels.context_actions) || null;
    if (panel && panel.kind === "combat") {
      const previous = combat
        ? { skillKey: combat.focusSkillKey, page: combat.page || 0, skillByKey: combat.skillByKey }
        : {};
      combat = CombatMenu.rebuildForPanel(combat, panel, previous);
      lastMenuSig = stableStringify(combat.menus.root.items);
      router.replaceMenu({ items: combat.menus.root.items, grid: true, gridCols: combat.menus.root.gridCols });
      return;
    }
    const rawItems = panel ? focusItemsFor(panel) : [];
    lastMenuSig = stableStringify(panel);
    // Leaving combat mode: the exploration root frame owns the keyboard
    // router now.
    combat = null;
    if (rawItems.length === 0) {
      if (router.depth() > 0) {
        // A committed panel without focusable items clears the frame stack
        // (the wrapped reset re-homes synchronously; the depth guard keeps
        // the re-home from recursing).
        router.reset();
      }
      return;
    }
    const keys = dockItemKeys(rawItems);
    dockRawByKey = {};
    const items = rawItems.map((raw, index) => {
      const item = KeyboardRouter.menuItem(raw.label, raw.enabled !== false, disabledReasonText(raw));
      item.key = keys[index];
      dockRawByKey[keys[index]] = raw;
      return item;
    });
    router.replaceMenu({ items, grid: false });
  }

  function rebuildFocusMenu(prev, rs) {
    const panel = (rs.panels && rs.panels.context_actions) || null;
    const kind = (panel && panel.kind) || null;
    if (kind === "combat") {
      // The combat keyboard hierarchy (root/skills/forfeit menus) is built by
      // the preserved CombatMenu model; selection state (skill/scale/target)
      // is rebuilt deterministically across a panel replacement. The signature
      // guard is essential: without it, replaceMenu -> notifyFocus ->
      // publishView -> rebuildFocusMenu would recurse (replaceMenu resets
      // focus, which re-enters publishView).
      const previous = combat
        ? {
            skillKey: combat.focusSkillKey,
            page: combat.page || 0,
            skillByKey: combat.skillByKey,
          }
        : {};
      const probe = CombatMenu.buildMenus(panel, { skillKey: previous.skillKey, page: previous.page || 0 });
      const sig = stableStringify(probe.menus.root.items);
      const rehomeNeeded = router.depth() === 0;
      if (sig === lastMenuSig && !rehomeNeeded) {
        // Panel unchanged and the router frame is alive: keep the existing
        // combat tree so the in-progress client-local selection state
        // (chosen skill, 威力 scale, AREA shorthand/candidates) set by the
        // keyboard flow survives publishView cycles. Only a genuine panel
        // replacement — or a router reset (depth 0, the test helper's
        // `router.reset()` re-home) — rebuilds.
        return;
      }
      lastMenuSig = sig;
      rehomeFrame(rs);
      return;
    }
    // The committed `context_actions` panel (affordances/participants AND the
    // sibling `suggestions` envelope) is the menu frame's content: any change
    // to the committed panel resets the router focus to the first item, while
    // an identical re-commit preserves the focus position.
    const sig = stableStringify(panel);
    const rehomeNeeded = router.depth() === 0 && focusItemsFor(panel).length > 0;
    if (sig === lastMenuSig && !rehomeNeeded) {
      return;
    }
    rehomeFrame(rs);
  }

  // ------------------------------------------------------------------ creation

  // The committed `creation` panel, or null unless the session is in creation
  // mode with an available panel (the legacy `panelAvailable` check).
  function creationPanelOf(rs) {
    const panel = (rs.panels && rs.panels.creation) || null;
    if (!panel || panel.available !== true || rs.mode !== "creation") {
      return null;
    }
    return panel;
  }

  // The legacy `_panelSignature`: the preset keys, the race keys, and the
  // canonical draft. Any change rebuilds the creation menus and resumes the
  // server-persisted stage.
  function creationPanelSignature(panel) {
    const custom = panel.custom || {};
    return stableStringify({
      presets: (panel.presets || []).map((card) => card.key),
      races: (custom.races || []).map((race) => race.key),
      draft: panel.draft || null,
    });
  }

  // Open the confirmation stage for the just-saved draft (preset/custom) or
  // the destructive reset, pushing the confirm items as the single router
  // frame (the legacy `_openPendingConfirm` / `_openResetConfirm`). The stage
  // the player was on is remembered so cancel restores exactly that view.
  function openCreationConfirm(kind, presetKey, returnStage) {
    if (!creation || creation.view === "confirm") {
      return;
    }
    creation.pendingActivate = kind;
    creation.pendingActivateKey = kind === "preset" ? presetKey || null : null;
    creation.pendingSaveRequestId = null;
    creation.returnStage = returnStage || creation.view || "root";
    const menu =
      kind === "reset"
        ? CreationMenu.confirmMenu("確認清除角色草稿？此操作無法回復。", CreationMenu.RESET_ACTION, {}, null)
        : CreationMenu.activateConfirm(kind === "preset" ? presetKey : null);
    creation.confirmItems = menu.items;
    creation.view = "confirm";
    router.pushMenu({ items: creation.confirmItems, focusKey: null });
  }

  // Router submit for a creation item (the legacy `handleItem`): submenu opens,
  // preset-card saves, confirm dispatches, and cancel pops one level. Returns
  // true when the item belonged to the creation dock.
  function handleCreationItem(item) {
    if (!creation || !creation.menus) {
      return false;
    }
    if (item.openSubmenu === "presets") {
      creation.view = "presets";
      router.pushMenu(creation.menus.menus.presets);
      return true;
    }
    if (item.openSubmenu === "custom") {
      creation.view = "custom";
      // A marker menu gives Escape a level to pop without discarding values.
      router.pushMenu({ items: [], focusKey: null });
      return true;
    }
    if (item.presetKey) {
      const requestId = dispatchAction(CreationMenu.PRESET_ACTION, {
        preset_key: item.presetKey,
      });
      if (requestId !== null) {
        creation.pendingSaveRequestId = requestId;
        creation.pendingActivate = "preset";
        creation.pendingActivateKey = item.presetKey;
      }
      return true;
    }
    if (
      item.actionId === CreationMenu.ACTIVATE_ACTION ||
      item.actionId === CreationMenu.RESET_ACTION
    ) {
      dispatchAction(item.actionId, item.payload || {});
      return true;
    }
    if (item.key && item.key.indexOf("cancel-") === 0) {
      router.popMenu();
      creation.view = creation.pendingActivate === "preset" ? "presets" : "custom";
      creation.pendingActivate = null;
      creation.pendingActivateKey = null;
      return true;
    }
    return false;
  }

  // Router escape/menu-closed for creation: pop exactly one menu level and
  // restore the matching view without discarding the server draft (the legacy
  // `onRouterEvent` menu handling). The custom form's marker menu and the
  // confirm screens all restore to root / presets / custom.
  function handleCreationMenuEvent(name) {
    if (!creation) {
      return;
    }
    if (creation.view === "presets") {
      creation.view = "root";
    } else if (creation.view === "confirm") {
      // Restore exactly the stage the confirmation was opened from (a reset
      // confirm opened on the preset page returns to presets, one opened on
      // the custom form returns to custom, ...).
      creation.view = creation.returnStage || "root";
      creation.returnStage = null;
      creation.pendingActivate = null;
      creation.pendingActivateKey = null;
      creation.confirmItems = [];
    } else if (creation.view === "custom") {
      creation.view = "root";
    }
    if (name === "escape-root") {
      // escape-root does not pop a router level: re-sync the router to the
      // menu matching the restored view.
      const menus = creation.menus;
      if (creation.view === "presets") {
        router.replaceMenu(menus.menus.presets);
      } else if (creation.view === "custom") {
        router.replaceMenu({ items: [], focusKey: null });
      } else {
        router.replaceMenu(menus.menus.root);
      }
    }
    publishView();
  }

  // Rebuild the creation dock state for the committed view (the legacy
  // creation_dock.js subscribe/mount logic): mount on entering creation mode,
  // rebuild menus when the panel signature changes, resume the server-
  // persisted draft stage, and resolve the pending save's confirmation.
  function rebuildCreationDock(prev, rs) {
    const panel = creationPanelOf(rs);
    if (!panel) {
      if (creation) {
        creation = null;
      }
      return;
    }
    if (!creation) {
      creation = {
        view: "root",
        menus: null,
        confirmItems: [],
        pendingActivate: null,
        pendingActivateKey: null,
        pendingSaveRequestId: null,
        returnStage: null,
        panelSig: null,
      };
    }
    // Resolve a pending save's confirmation BEFORE the panel-signature
    // refresh (the legacy dock's ordering): the just-saved draft's panel
    // arrives with or right after the save result, so the refresh must open
    // — and never clobber — the confirmation for the just-saved draft
    // (fix-creation-finalization-safety D1): success opens the confirmation;
    // rejection or error stays on the current view.
    if (creation.pendingSaveRequestId !== null) {
      const result = rs.lastActionResult || null;
      const prevResult = prev ? prev.lastActionResult || null : null;
      if (result && result !== prevResult && result.requestId === creation.pendingSaveRequestId) {
        creation.pendingSaveRequestId = null;
        if (result.outcome === "success") {
          const kind = creation.pendingActivate || "preset";
          // A successful preset save opens the confirmation from the preset
          // list; a custom/concept save from the form.
          openCreationConfirm(
            kind,
            creation.pendingActivateKey,
            kind === "preset" ? "presets" : "custom",
          );
          return;
        }
        creation.pendingActivate = null;
        creation.pendingActivateKey = null;
      }
    }
    const sig = creationPanelSignature(panel);
    if (creation.panelSig !== sig) {
      creation.panelSig = sig;
      creation.menus = CreationMenu.buildMenus(panel);
      const draft = panel.draft || null;
      if (draft && draft.mode === "preset") {
        openCreationConfirm("preset", draft.preset_key || null, "presets");
      } else if (draft && (draft.mode === "custom" || draft.mode === "concept")) {
        if (creation.view !== "confirm") {
          creation.view = "custom";
          router.reset({ items: [], focusKey: null });
        }
      } else if (creation.view !== "confirm") {
        creation.view = "root";
        router.reset({ items: creation.menus.menus.root.items, focusKey: null });
      }
    }
  }

  function syncRouterGates() {
    router.setMutationInFlight(!!inFlight);
    router.setAwaitingRevision(inFlight && inFlight.presentationRevision !== null ? inFlight.presentationRevision : null);
  }

  function initialView() {
    return buildView(null, reducer.getState());
  }

  function buildView(prev, rs) {
    const panels = rs.panels || {};
    const panel = panels.context_actions || null;
    const suggestions = panel && panel.suggestions ? panel.suggestions : null;
    const prevChoiceState = prev && prev.choicePoint ? prev.choicePoint.state : "absent";
    const choiceState = ChoicePointLogic.nextChoicePointState(prevChoiceState, suggestions);
    const currentItem = router.currentItem();

    return {
      generation: rs.generation,
      phase: rs.phase,
      epoch: rs.activeEpoch,
      revision: rs.revision,
      mode: rs.mode,
      layoutVersion: rs.layoutVersion,
      serverTime: rs.serverTime,
      panels,
      mutationsLocked: rs.mutationsLocked,
      protocolError: rs.protocolError,
      lastActionResult: rs.lastActionResult,
      retiredEpochCount: rs.retiredEpochCount,
      connected: rs.connected,

      connectionStatus: connectionStatusFor(rs.connected, rs.phase),
      statusSlice: {
        connected: rs.connected,
        locationLabel:
          panels.status && panels.status.actor && panels.status.actor.location
            ? panels.status.actor.location.label
            : null,
        timeLabel: formatTimeLabel(rs.serverTime),
      },
      prompt,
      lastSurface,
      lastTarget,
      activeSubDock: activeSubDock.value,

      contextActions: panel,
      suggestions,
      suggestionsView: OptionCards.buildOptionsView(panel || {}),
      suggestionsSignature: OptionCards.suggestionsSignature(suggestions),
      choicePoint: { state: choiceState, suggestions },
      localMapModel: panels.local_map
        ? { ...LocalMap.reducePanel(panels.local_map), available: panels.local_map.available !== false }
        : null,
      // The keyboard router's current combat menu frame (root/skills/scale/
      // target) so the visible dock follows keyboard navigation (Option B).
      combatMenu: router.currentMenu(),
      // The focused AREA skill's selected candidate identities (the client-
      // local selection the Space toggle mutates); drives the "✓" marker.
      combatSelected:
        combat && combat.focusSkillKey && combat.skillByKey[combat.focusSkillKey]
          ? combat.skillByKey[combat.focusSkillKey].selected
          : [],

      // The character-creation dock stage (the legacy creation dock port): the
      // keyboard-router menu the overlay mirrors. Null outside creation mode.
      creationView: creation
        ? {
            stage: creation.view,
            confirmItems: creation.confirmItems,
            confirmLabel:
              creation.confirmItems.length > 0 ? creation.confirmItems[0].label : null,
            confirmAction:
              creation.confirmItems.length > 0 ? creation.confirmItems[0].actionId : null,
            pendingPresetKey: creation.pendingActivateKey,
          }
        : null,

      focus: currentItem
        ? {
            key: currentItem.key !== undefined ? currentItem.key : currentItem.label,
            label: currentItem.label,
            enabled: currentItem.enabled,
            description: currentItem.description,
          }
        : { key: null, label: null, enabled: null, description: null },

      dispatch: {
        inFlight: inFlight ? { requestId: inFlight.requestId, presentationRevision: inFlight.presentationRevision } : null,
        uncertain,
        submittedRequestId: lastSubmittedRequestId,
        // Whether a mutation was submitted and its result not yet confirmed
        // (the client-local uncertain-marking precondition, exposed for the
        // browser harness).
        mutationSubmitted,
      },
    };
  }

  function publishView() {
    const prev = view.value;
    const rs = reducer.getState();
    handleTransportLifecycle(prev, rs);
    handleActionResult(prev, rs);
    releaseIfReady(rs);
    rebuildFocusMenu(prev, rs);
    rebuildCreationDock(prev, rs);
    syncRouterGates();
    view.value = buildView(prev, rs);
  }

  reducer.subscribe(() => {
    publishView();
  });

  // ---------------------------------------------------------------- actions

  function receive(messageGeneration, messageName, args, kwargs) {
    const result = reducer.receive(messageGeneration, messageName, args || [], kwargs || {});
    // Track presentation receive results. A genuine "cannot render" rejection
    // — a malformed `ui_snapshot` / `ui_update` the reducer refused to commit
    // (`reason === "invalid"`), or a transport-corruption missing-envelope
    // rejection (`reason === "missing_envelope") — drives the C4 one-sync-
    // per-episode auto-resync. Ordering / lifecycle rejections
    // (stale_generation, not_newer, different_epoch, retired_epoch,
    // update_cannot_establish_epoch) and an accepted presentation do NOT set
    // the signal.
    if (messageName === "ui_snapshot" || messageName === "ui_update") {
      if (result && result.accepted) {
        lastPanelRejection.value = null;
      } else if (
        result &&
        !result.accepted &&
        (result.reason === "invalid" || result.reason === "missing_envelope")
      ) {
        lastPanelRejection.value = { messageName, reason: result.reason, detail: result.detail || null };
      }
    }
    return result;
  }

  function beginTransport(nextGeneration) {
    const res = reducer.beginTransport(nextGeneration);
    // A new transport generation is a fresh failure episode: clear the
    // presentation-rejection signal so the next generation's malformed initial
    // snapshot can auto-request one ui_sync.
    lastPanelRejection.value = null;
    return res;
  }

  function setConnected(connected) {
    const res = reducer.setConnected(connected);
    // A transport disconnect (connection_close) while an OOB mutation was
    // submitted and the client's in-flight gate is still held (the result has
    // NOT been observed by the client): the outcome may or may not have been
    // applied server-side, so the mutation is marked uncertain (client-local;
    // released only when the result is observed or by `clearUncertain`).
    // The client's gate is held (true) or the client is unavailable mid
    // re-bootstrap (null): the mutation is unconfirmed, so a transport loss
    // marks it uncertain. Only a released gate (false, result observed)
    // means the mutation is confirmed and must not be re-flagged.
    if (!connected && mutationSubmitted && clientInFlight() !== false) {
      uncertain = true;
      inFlight = null;
      router.setMutationInFlight(false);
      router.setAwaitingRevision(null);
      publishView();
    }
    return res;
  }

  function setSender(next) {
    sender = next || null;
  }

  function setPrompt(text) {
    prompt = typeof text === "string" ? text : "";
    publishView();
  }

  function appendText(kind, text) {
    if (NARRATIVE_KINDS.indexOf(kind) === -1) {
      throw new TypeError("narrative kind must be one of in/out/sys/err");
    }
    const line = {
      kind,
      text: String(text == null ? "" : text),
      tokens: kind === "out" ? NarrativeMarkup.tokenize(String(text == null ? "" : text)) : null,
    };
    narrative.value.push(line);
    while (narrative.value.length > MAX_NARRATIVE_LINES) {
      narrative.value.shift();
      seenIndex.value = Math.max(0, seenIndex.value - 1);
    }
    return line;
  }

  function sendText(text) {
    if (!view.value.connected) {
      return false;
    }
    const value = String(text == null ? "" : text);
    appendText("in", value);
    commandHistory.value.push(value);
    while (commandHistory.value.length > MAX_COMMAND_HISTORY) {
      commandHistory.value.shift();
    }
    if (sender && typeof sender.sendText === "function") {
      sender.sendText(value);
    }
    return true;
  }

  function dispatchAction(actionId, payload) {
    const v = view.value;
    if (!v.connected || v.mutationsLocked || v.phase !== "active" || inFlight) {
      return null;
    }
    const requestId = "session:" + (++requestCounter);
    const envelope = {
      protocol_version: 1,
      presentation_epoch: v.epoch,
      request_id: requestId,
      base_revision: v.revision,
      action_id: actionId,
      payload: payload === undefined || payload === null ? {} : payload,
    };
    inFlight = { requestId, presentationRevision: null };
    mutationSubmitted = true;
    lastSubmittedRequestId = requestId;
    // A custom save tracks its request so the result resolution opens the
    // confirmation for the just-saved draft (fix-creation-finalization-safety
    // D1); the preset path records the same markers on router submit.
    if (actionId === CreationMenu.CUSTOM_ACTION && creation) {
      creation.pendingSaveRequestId = requestId;
      creation.pendingActivate = "custom";
      creation.pendingActivateKey = null;
    }
    router.setMutationInFlight(true);
    try {
      if (sender && typeof sender.sendAction === "function") {
        sender.sendAction(envelope);
      }
    } catch (err) {
      // A synchronous transport failure (a closing WebSocket, a failed
      // adapter): mark the mutation uncertain, release the in-flight gate
      // (no declared presentation revision to await) so the dispatch lock
      // never sticks, and publish so the committed view reflects the failed
      // send (the C3 transport re-asserts or the `clearUncertain` path
      // recovers the flag).
      uncertain = true;
      inFlight = null;
      router.setMutationInFlight(false);
      router.setAwaitingRevision(null);
    } finally {
      publishView();
    }
    return requestId;
  }

  // Open the destructive-reset confirmation (the creation dock's reset button
  // never dispatches `creation.reset` directly): the confirm stage renders the
  // `creation-confirm` screen and the router carries the confirm menu.
  function requestCreationReset() {
    if (!creation || !creation.menus) {
      return false;
    }
    openCreationConfirm("reset", null, creation.view);
    publishView();
    return true;
  }

  function focusPress(key, repeat) {
    // A keyboard confirm (Enter) records the keyboard source so the target-row
    // submit path can distinguish it from a pointer confirm.
    if (key === "Enter") {
      lastConfirmSource = "keyboard";
    }
    return router.press(key, !!repeat);
  }

  function focusConfirm(source) {
    lastConfirmSource = source || "keyboard";
    return router.confirm({ source: lastConfirmSource });
  }

  function focusEscape() {
    return router.escape();
  }

  function focusItemByKey(key) {
    return router.focusItemByKey(key);
  }

  function markNarrativeSeen() {
    seenIndex.value = narrative.value.length;
  }

  const unreadCount = computed(() =>
    narrative.value
      .slice(seenIndex.value)
      .filter((line) => line.kind === "out")
      .length
  );

  function clearUncertain() {
    uncertain = false;
    mutationSubmitted = false;
    publishView();
  }

  // Expose the attached transport seam so the C2 browser-bridge can route the
  // OOB entry points (ui_sync requests, reconnect resync) through the same
  // sender C3 will later attach (the store's sender is the single transport
  // seam; the bridge never re-implements sending).
  function getSender() {
    return sender;
  }

  // Re-run the committed-view publish (releaseIfReady + router-gate sync) so
  // the presentation gate is re-evaluated on a new committed state; the C2
  // bridge calls it from the `handlePresentation`/`onPresentationAccepted`
  // entry points.
  function refreshView() {
    publishView();
  }

  return {
    view,
    narrative,
    commandHistory,
    unreadCount,
    receive,
    beginTransport,
    setConnected,
    setSender,
    setPrompt,
    appendText,
    sendText,
    dispatchAction,
    requestCreationReset,
    focusPress,
    focusConfirm,
    focusEscape,
    focusItemByKey,
    markNarrativeSeen,
    clearUncertain,
    getSender,
    refreshView,
    // The live keyboard-router instance (C4 harness re-map): the managed
    // browser suite reads `depth()` / `currentItem()` off it; the store owns
    // the focus router (design D4), so it is exposed read-only for the harness.
    router,
    // C4: the last rejected `ui_snapshot` / `ui_update` (the "renderer cannot
    // render" signal) so the AppClient auto-resync watcher can request one
    // ui_sync per failure episode.
    lastPanelRejection,
    // The protocol store's subscription seam (the C4 harness re-map): browser
    // tests observe `beginTransport` notifications (the transport-reset state
    // with a null epoch and empty panels) to gate on deterministic state.
    subscribe: (listener) => reducer.subscribe(listener),
    // Set which re-homed sub-dock currently owns the action-dock surface
    // (null clears). The sub-dock panels set/clear this on mount/unmount;
    // the suggestions section hides while one is active.
    setActiveSubDock,
  };
});
