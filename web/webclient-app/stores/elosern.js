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

import { computed, onScopeDispose, ref } from "vue";
import { defineStore } from "pinia";

import Protocol from "../lib/protocol.js";
import KeyboardRouter from "../lib/keyboard_router.js";
import NarrativeMarkup from "../lib/narrative_markup.js";
import LocalMap from "../lib/local_map.js";
import OptionCards from "../lib/option_cards.js";
import CombatMenu from "../lib/combat_menu.js";
import CreationMenu from "../lib/creation_menu.js";
import ServiceMenu from "../lib/service_menu.js";
import CommandEcho from "../lib/command_echo.js";
import stableStringify from "../lib/stable_stringify.js";
import { createFrameResolver } from "./frame-resolvers.js";
import { actionIntentForItem, dockItemKeys } from "../components/dock-items.js";
import { gaugeRatio, isLowHp } from "../components/vitals.js";
import LayoutStore from "../lib/layout_store.js";

const NARRATIVE_KINDS = ["in", "out", "sys", "err"];
const MAX_NARRATIVE_LINES = 500;
// The one stable fallback line for a recognized non-success action result
// that carries no usable server message (webclient-action-result-feedback
// D-D). The protocol validator guarantees a 1..512 code point message, so
// this exists only for malformed-edge safety and never paraphrases server
// text.
const ACTION_RESULT_FALLBACK_MESSAGE = "動作未生效，請重試或返回上層。";
// The non-success outcomes (mirrors the protocol OUTCOMES vocabulary); a
// recognized result with one of these speaks once through the narrative
// feed (webclient-action-result-feedback D-A/D-B).
const NON_SUCCESS_OUTCOMES = ["rejected", "stale", "error"];
const MAX_COMMAND_HISTORY = 50;
// The action-feedback toast queue (webclient-action-feedback D1): client-local
// view state — never persisted, never part of the protocol reducer snapshot.
// The bounded lifetime and FIFO cap mirror the redesign draft's queue
// (5200 ms, at most four entries).
const TOAST_LIFETIME_MS = 5200;
const TOAST_QUEUE_MAX = 4;
// The frozen tone vocabulary (webclient-action-feedback): an unknown tone is
// rejected, not coerced (the openHudDrawer precedent).
const TOAST_TONES = new Set(["info", "crit"]);
// The registered production panel allowlist (mirrors the UMD allowlist in
// elosern/protocol.js and web/webclient/presentation/protocol.py).
const PANEL_ALLOWLIST = [
  "art",
  "status",
  "context_actions",
  "local_map",
  "party",
  "services",
  "creation",
  "exploration",
  "character",
  "lineage",
  "title_ballot",
  "title_codex",
];

// D5 (webclient-minimap-04-island-single-affordance): top-meta locationLabel
// fallback resolution:
// 1. local_map panel's current node label (when available, carries
//    current_node, matches a node, and has non-empty string label)
// 2. status panel's actor.location.label
// 3. null (TopBar renders 「位置：--」)
//
// Why the map label wins: the status panel's label is the raw room
// key (「Wilderness」 for every wilderness cell), while the map
// payload's current-node label is the presenter's authored place
// name (the region display name on the wilderness layer). Neither
// payload contract changes: the shell chooses between two labels the
// server already committed at the same revision.
export function resolveLocationLabel(panels) {
  if (!panels) return null;
  const lm = panels.local_map;
  if (lm && lm.available === true && lm.current_node) {
    const node = Array.isArray(lm.nodes)
      ? lm.nodes.find((n) => n.id === lm.current_node)
      : null;
    if (node && typeof node.label === "string" && node.label !== "") {
      return node.label;
    }
  }
  const statusLabel = panels.status?.actor?.location?.label;
  if (typeof statusLabel === "string" && statusLabel !== "") {
    return statusLabel;
  }
  return null;
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
// B1 component accepts (connecting/waiting/offline/ready). `loggedIn` is the
// client-local session state delivered by the evennia.js `logged_in` OOB
// event: a connected socket that has not logged in yet waits for login
// (an anonymous session never receives a snapshot, so the phase alone cannot
// distinguish "snapshot in flight" from "not logged in").
function connectionStatusFor(connected, loggedIn, phase) {
  if (!connected) {
    return "offline";
  }
  if (!loggedIn || phase === "detached") {
    return "waiting";
  }
  if (phase === "active") {
    return "ready";
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

  // The declarative-frame resolver registry (webclient-frame-resolver-registry
  // D-A): menus derived from the reducer's committed state at call time. The
  // cutover changes route their push sites through it; this seam stays the
  // single derivation entry (`resolveFrame` below, bridge-exposed).
  const frameResolver = createFrameResolver({ getState: () => reducer.getState() });

  // D5: client-local dispatch bookkeeping (the tested legacy action-client
  // semantics; the transport send is an attachable seam).
  let inFlight = null; // {requestId, presentationRevision}
  let uncertain = false;
  let requestCounter = 0;
  let sender = null; // { sendAction(envelope), sendText(text) } — C3 attaches evennia.js
  let lastSurface = null;
   let lastTarget = null;
   // Monotonic signal the shell watches to open the command drawer (a freeform
   // dialogue entry point requests a drawer open + field focus).
   let drawerRequest = 0;
   // Monotonic signal the shell watches to CLOSE the command drawer and
   // restore action-dock focus (a successful dock-borrowed send, e.g. freeform
   // dialogue). Ordinary text sends keep the drawer open, so only the
   // borrowed (freeform) path bumps this.
   let drawerCloseRequest = 0;
   // The npc identity for an active freeform dialogue; set when a freeform
   // affordance is activated, cleared when its speech is submitted.
   let freeformTarget = null;
   // Monotonic signal the shell watches to open the exploration rest-duration
   // form (the wait/rest entry point).
   let restFormRequest = 0;
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
  // Client-local session state (mirrors the D10 console model): the evennia.js
  // `logged_in` OOB event marks the account attached; a disconnect resets it.
  // The transport status slice needs it because the server never sends a
  // `ui_snapshot` to an anonymous session, so "connected with no snapshot"
  // means "waiting for login" until the account actually logs in.
  let loggedIn = false;
  // The CombatMenu model (client-local skill/scale/AREA selection) lives in
  // the resolver registry — the ONE model home (the declared purity
  // exception); the store reaches it only through
  // `frameResolver.combatModel()`, never a second copy.

  // The legacy character-creation dock port (the preserved CreationMenu model
  // driving the keyboard router in creation mode, design D4): the current dock
  // stage (root/presets/custom/concept/confirm) and the save awaiting its
  // confirmation. The built menus and the confirm items are NOT stored: every
  // frame content resolves from the committed panel through the resolver
  // registry (webclient-services-combat-creation-frames). Null outside
  // creation mode.
  let creation = null; // {view, confirmDescriptor, pendingActivate, pendingActivateKey, pendingSaveRequestId, returnStage, panelSig}

  // D4: the imported keyboard router owns the focus state; its events are
  // routed through the same store actions (a broken renderer must never
  // break the reducer). The declarative-frame resolver is injected so every
  // read of a declarative frame resolves at access time (webclient-
  // declarative-frame-stack D-A); the router never copies a resolved menu.
  const router = KeyboardRouter.createRouter({
    onEvent: onRouterEvent,
    resolve: (descriptor) => frameResolver.resolve(descriptor),
  });

  // The exploration root descriptor (webclient-declarative-frame-stack): the
  // one source for root pushes, replaces, and teardown re-homes.
  const EXPLORATION_ROOT_DESCRIPTOR = Object.freeze({
    source: "exploration.root",
    params: Object.freeze({}),
  });
  // The per-mode root descriptors (webclient-services-combat-creation-frames):
  // teardown and the explicit root reset post EXACTLY one root frame in every
  // mode — the empty-stack `router.reset` fuse is deleted, the stack never
  // empties in a live mode.
  const MODE_ROOT_DESCRIPTORS = Object.freeze({
    exploration: EXPLORATION_ROOT_DESCRIPTOR,
    combat: Object.freeze({ source: "combat.root", params: Object.freeze({}) }),
    creation: Object.freeze({ source: "creation.root", params: Object.freeze({}) }),
  });
  function rootDescriptorFor(rs) {
    // The combat family is keyed on the committed panel form (panel.kind),
    // exactly as the deleted copy push sites were; creation on the session
    // mode; everything else on the exploration root.
    const panel = (rs && rs.panels && rs.panels.context_actions) || null;
    if (panel && panel.kind === "combat") {
      return MODE_ROOT_DESCRIPTORS.combat;
    }
    if (rs && rs.mode === "creation") {
      return MODE_ROOT_DESCRIPTORS.creation;
    }
    return MODE_ROOT_DESCRIPTORS.exploration;
  }
  // The single root-reset entry (replaces the deleted menu-less
  // `router.reset` the browser helpers used): post the committed mode's root
  // descriptor as the one-frame stack.
  function resetFramesToRoot() {
    inStackMutation = true;
    try {
      router.resetFrame(rootDescriptorFor(reducer.getState()), { openerKey: null });
    } finally {
      inStackMutation = false;
    }
  }
  // Set while the store drives a router stack mutation, so a focus emit that
  // re-enters the store never nests a second mutation.
  let inStackMutation = false;
  // Set when the router reports a settle-driven pop during the current
  // publish window (see `settleFrameStack`).
  let settlePopSeen = false;

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

   // The bounded services quantity form (webclient-service-menus: buy/sell
   // quantity validation with exact-copper outcomes). A local UI exception: the
   // player focuses a stock/sell row (a bounded trade row carrying a
   // `quantity` {min,max}), opens the form, types a digit quantity, and only
   // a valid quantity dispatches the `shop.buy` / `shop.sell` action. The
   // unsubmitted quantity is discarded on a `services` panel replacement
   // (reconnect), so the form is purely client-local.
    const quantityForm = ref(null);
     function openQuantityForm(item) {
       const qty = item.quantity;
       quantityForm.value = {
         itemKey: item.itemKey,
         actionId: item.actionId,
         // The echo label is captured at open time (the row's server-authored
         // display name) and replayed on the Enter submit
         // (complete-ui-command-echo D3).
         itemLabel: (item.commandDisplay && item.commandDisplay.itemLabel) || null,
         state: ServiceMenu.quantityState(qty.min, qty.max),
         open: true,
       };
       serviceSurface.value = "shop";
       publishView();
     }

    // H4 (webclient-hud-04-reference-drawers, design D3): the reference
    // drawer controller. `view.hudDrawer` is the single open-drawer name
    // (null | skill | inventory | shop | quest | lore | status); at most one
    // drawer is open at a time (structural: a single value). Unknown names
    // are rejected, not coerced. The store is the single writer and owns the
    // teardown on a mode change, an epoch reset, or a transport loss.
    const HUD_DRAWER_NAMES = new Set(["skill", "inventory", "shop", "quest", "lore", "status"]);
    const hudDrawer = ref(null);

    function openHudDrawer(name) {
      if (!HUD_DRAWER_NAMES.has(name)) {
        console.warn(`openHudDrawer: unknown drawer "${name}" rejected (not coerced)`);
        return false;
      }
      // Mutual exclusion (H5, design D8): opening a drawer closes the open
      // overlay so at most one focus-trapped surface exists.
      closeOverlay();
      hudDrawer.value = name;
      publishView();
      return true;
    }

    function closeHudDrawer(options = {}) {
      if (hudDrawer.value === null) {
        return false;
      }
      // make-inventory-drawer-frameless: the 背包 drawer never hosts a router
      // frame, so closing it leaves the router alone — no menu level is
      // popped and the action dock is never re-homed, whatever frame is
      // current at close time. Every other drawer keeps the teardown below
      // byte-for-byte.
      if (hudDrawer.value === "inventory") {
        hudDrawer.value = null;
        publishView();
        return true;
      }
      // A drawer hosting a service frame: closing it pops exactly one menu
      // level (the hosted/discard rules live in `settleFrameStack`; a
      // descendant pop keeps the drawer, a hosted-frame pop closes it and
      // discards its local state). A frameless drawer (status / skill / lore)
      // closes without touching the frame stack.
      let poppedHostedFrame = false;
      if (options.popFrame && currentFrameIsServiceFrame()) {
        poppedHostedFrame = true;
        inStackMutation = true;
        try {
          router.popMenu();
        } finally {
          inStackMutation = false;
        }
        // The hosted-frame teardown the settle would have performed (the
        // pop above is settle-guarded): a quest/shop drawer close discards
        // the surface record and the hosted surface's local state — the
        // quantity form (shop); the quest drawer's selection/confirmation
        // state is component-local and dies on unmount.
        if (hudDrawer.value === "quest" || hudDrawer.value === "shop") {
          setServiceSurface(null);
          if (hudDrawer.value === "shop") {
            quantityForm.value = null;
          }
          // Same settle-rule mirror as the commit-time path: when the pop
          // left a NON-service frame current, the exploration sub-dock has
          // lost everything it hosts and closes with the drawer (a hosted
          // parent frame still current keeps the sub-dock alive).
          if (
            reducer.getState().mode === "exploration" &&
            activeSubDock.value &&
            !descriptorIsServiceFrame(router.currentDescriptor())
          ) {
            setActiveSubDock(null);
          }
        }
      }
      // When closing a NON-hosted drawer while an exploration sub-dock
      // (character / services) owns the action dock, clear the sub-dock and
      // re-home the exploration root frame — the same teardown the router's
      // `escape-root` handler performs. The drawer's own Escape handler now
      // owns the key (focus is trapped in the drawer), so the router no
      // longer sees the Escape and would not clear the sub-dock. A close
      // that popped a hosted frame does NOT re-home: the popped-to frame
      // (the hosted parent, or the root via the settle cascade) stands.
      if (
        !poppedHostedFrame &&
        reducer.getState().mode === "exploration" &&
        activeSubDock.value
      ) {
        setActiveSubDock(null);
        inStackMutation = true;
        try {
          router.replaceFrame(EXPLORATION_ROOT_DESCRIPTOR, { openerKey: null });
        } finally {
          inStackMutation = false;
        }
      }
      hudDrawer.value = null;
      publishView();
      return true;
    }

    // H5 (webclient-hud-05-overlays-and-command-line, design D7/D8): the
    // full-screen overlay controller. `view.hudOverlay` is the single
    // open-overlay name (null | map | settings | help | lineage); at most one
    // overlay is open at a time (structural: a single value). Unknown names are
    // rejected, not coerced. Opening an overlay closes any open reference
    // drawer (design D8: an overlay and a drawer are never open together,
    // so at most one focus-trapped surface exists at any moment), and the
    // opener control is captured at open time so the host's focus
    // restoration returns to the trigger that opened the most recent overlay.
    // The store is the single writer and owns the teardown on a mode change
    // into creation, an epoch reset, or a transport loss (same events as
    // the drawer teardown in `syncHudDrawer`).
    const HUD_OVERLAY_NAMES = new Set(["map", "settings", "help", "lineage", "codex"]);
    const hudOverlay = ref(null);
    const hudOverlayOpener = ref(null);

    function openOverlay(name, openerEl = null) {
      if (!HUD_OVERLAY_NAMES.has(name)) {
        console.warn(`openOverlay: unknown overlay "${name}" rejected (not coerced)`);
        return false;
      }
      // Mutual exclusion (design D8): opening the overlay closes the open
      // drawer so exactly one focus-trapped surface exists.
      closeHudDrawer({});
      hudOverlay.value = name;
      // The opener is captured at open time, not in the host's onMounted:
      // an overlay that replaces another must restore focus to its own
      // trigger, never to the trigger of the closed overlay (design D7).
      hudOverlayOpener.value = openerEl;
      publishView();
      return true;
    }

    function closeOverlay() {
      if (hudOverlay.value === null) {
        return false;
      }
      hudOverlay.value = null;
      hudOverlayOpener.value = null;
      publishView();
      return true;
    }

    // H5 (webclient-hud-05-overlays-and-command-line, tasks 7.5/7.8): the
    // presentation-preferences slice. Client-local presentation state
    // (webclient-component-showcase delta): the narrative prose scale
    // (`fontScale`), the text-to-HTML narrative toggle (`text2html`), the
    // optional reduced-motion override (`reducedMotion` — `null` means no
    // override, the OS `prefers-reduced-motion` applies) and the colorblind
    // status palette (`colorblind`). No settings control dispatches a
    // `ui_action`; each preference is applied to the document's presentation
    // tokens immediately, is persisted through the versioned,
    // presentation-only layout store, and is re-applied at load. The store's
    // own LayoutStore instance is the only writer (main.js's instance stays
    // load-only): a preference save reloads the latest validated wrapper
    // before writing, so the caller's `dimensions` and `tabs` are preserved.
    const layoutPersistence = LayoutStore.createStore({ storage: window.localStorage });
    const prefs = {
      fontScale: 1,
      text2html: true,
      // Optional key: absent in the stored wrapper = no override (task 7.5).
      reducedMotion: null,
      colorblind: false,
    };

    function applyPresentationPreferences() {
      const root = document.documentElement;
      // The three prose-scale targets (design D13): the narrative caption's
      // lines, the full-log surface's lines and the prompt line read this
      // token; no HUD/dock/drawer/overlay chrome reads it.
      root.style.setProperty("--prose-scale", String(prefs.fontScale));
      if (prefs.reducedMotion) {
        root.setAttribute("data-reduced-motion", prefs.reducedMotion);
      } else {
        root.removeAttribute("data-reduced-motion");
      }
      if (prefs.colorblind) {
        root.setAttribute("data-colorblind", "on");
      } else {
        root.removeAttribute("data-colorblind");
      }
      publishView();
    }

    function persistPresentationPreferences() {
      // Reload the latest validated wrapper before writing (task 7.8): a
      // version-1 wrapper lacking the new keys normalizes cleanly (no
      // version bump, task 7.5); an unknown stored version resets to the
      // default with every preference re-applied rather than half-applied.
      const current = layoutPersistence.load();
      const wrapper = current.state;
      wrapper.preferences = {
        text2html: prefs.text2html,
        fontScale: prefs.fontScale,
        colorblind: prefs.colorblind,
      };
      // The reducedMotion key is optional (task 7.5): only write it when the
      // override is explicit. The layout store validates it as a boolean —
      // `true` forces reduced motion ("on"), `false` forces full motion
      // ("off"); absence in the stored wrapper means "no override" (the OS
      // `prefers-reduced-motion` applies).
      if (prefs.reducedMotion) {
        wrapper.preferences.reducedMotion = prefs.reducedMotion === "on";
      }
      layoutPersistence.save(wrapper);
    }

    function loadPresentationPreferences() {
      const result = layoutPersistence.load();
      const stored = (result.state && result.state.preferences) || {};
      if (typeof stored.fontScale === "number" && isFinite(stored.fontScale)) {
        prefs.fontScale = Math.min(2, Math.max(0.5, stored.fontScale));
      }
      if (typeof stored.text2html === "boolean") {
        prefs.text2html = stored.text2html;
      }
      // The `reducedMotion` key is optional (task 7.5): stored as a boolean
      // override — `true` forces reduced motion ("on"), `false` forces full
      // motion ("off"); its absence means "no override" (the OS
      // `prefers-reduced-motion` applies).
      if (typeof stored.reducedMotion === "boolean") {
        prefs.reducedMotion = stored.reducedMotion ? "on" : "off";
      }
      if (typeof stored.colorblind === "boolean") {
        prefs.colorblind = stored.colorblind;
      }
      applyPresentationPreferences();
    }

    function setFontScale(value) {
      if (typeof value !== "number" || !isFinite(value)) {
        return;
      }
      prefs.fontScale = Math.min(2, Math.max(0.5, value));
      applyPresentationPreferences();
      persistPresentationPreferences();
    }

    function setTextToHtml(on) {
      prefs.text2html = !!on;
      applyPresentationPreferences();
      persistPresentationPreferences();
    }

    function setReducedMotion(value) {
      // `null` = no override (the OS preference applies); `"on"` forces
      // reduced motion; `"off"` beats the OS `prefers-reduced-motion` media
      // query (task 7.6).
      if (value !== null && value !== "on" && value !== "off") {
        return;
      }
      prefs.reducedMotion = value;
      applyPresentationPreferences();
      persistPresentationPreferences();
    }

      function setColorblind(on) {
        prefs.colorblind = !!on;
        applyPresentationPreferences();
        persistPresentationPreferences();
      }

     // The service surface that the current service frame belongs to, recorded
    // at frame-push time (design D2's "record the surface at push time").
    // `null` when no service frame is active. Kept alongside the new
    // descriptor-derived surface so the quantity form's shop assignment and
    // the surface-owning views stay byte-for-byte.
    const serviceSurface = ref(null);
    function setServiceSurface(value) {
      serviceSurface.value = value;
    }

    // Declarative hosting (webclient-services-combat-creation-frames): the
    // current frame IS a service frame exactly when its descriptor's source
    // is a hosted services source (anything in the services family except
    // the navigation-only `services.root`). One source of truth — the
    // descriptor — never the menu title.
    const HOSTED_SERVICE_SOURCES = new Set([
      "services.guild",
      "services.board",
      "services.quests",
      "services.quest-detail",
      "services.confirm",
      "services.shop",
      "services.stock",
      "services.sell",
    ]);
    function descriptorIsServiceFrame(descriptor) {
      return !!(descriptor && HOSTED_SERVICE_SOURCES.has(descriptor.source));
    }
    function currentFrameIsServiceFrame() {
      return descriptorIsServiceFrame(router.currentDescriptor());
    }

    // The service surface -> reference drawer map (design D2): the guild
    // service frames (board / quests / quest-detail / abandon-confirm) present
    // the 任務 drawer and the shop frames (stock / sell) present the 商店
    // drawer. The 背包 drawer is not here: it opens frameless
    // (make-inventory-drawer-frameless) and never hosts a service frame.
    const SERVICE_SURFACE_DRAWERS = {
      guild: "quest",
      shop: "shop",
    };
    // The descriptor -> service-surface map: the guild-family frames carry
    // the quest surface, the shop family the shop surface.
    const SERVICE_SURFACE_FOR_SOURCE = {
      "services.guild": "guild",
      "services.board": "guild",
      "services.quests": "guild",
      "services.quest-detail": "guild",
      "services.confirm": "guild",
      "services.shop": "shop",
      "services.stock": "shop",
      "services.sell": "shop",
    };

  // The client-local toast queue (webclient-action-feedback D1). Declared
  // above the initial view because `initialView()` calls `buildView`, which
  // reads it (TDZ). The array is the ONE mutable reactive proxy: `buildView`
  // exposes the same reference on every publish, so pushes and dismisses
  // re-render consumers without a republish — and `handleActionResult`
  // pushes DURING a publish, where a nested republish would recurse.
  const toasts = ref([]); // [{id, title, sub?, tone}]
  // Per-entry auto-dismiss timers (internal bookkeeping; never reaches the
  // entry shape or the view).
  const toastTimers = new Map();
  let toastIdCounter = 0;

  // Push one toast, returning its id; a malformed entry is rejected, not
  // coerced. A full queue evicts the oldest entries first (FIFO). Every
  // pushed toast self-dismisses after TOAST_LIFETIME_MS unless clicked away
  // earlier.
  function pushToast(entry) {
    const item = entry || {};
    if (typeof item.title !== "string" || item.title.trim() === "") {
      console.warn("pushToast: missing or blank title rejected (not coerced)");
      return null;
    }
    if (!TOAST_TONES.has(item.tone)) {
      console.warn(`pushToast: unknown tone "${item.tone}" rejected (not coerced)`);
      return null;
    }
    const toast = { id: ++toastIdCounter, title: item.title, tone: item.tone };
    if (typeof item.sub === "string" && item.sub.trim() !== "") {
      toast.sub = item.sub;
    }
    toasts.value.push(toast);
    while (toasts.value.length > TOAST_QUEUE_MAX) {
      dismissToast(toasts.value[0].id);
    }
    toastTimers.set(toast.id, setTimeout(() => dismissToast(toast.id), TOAST_LIFETIME_MS));
    return toast.id;
  }

  // Remove one toast by id (also cancels its pending timer). Returns whether
  // an entry was removed; an unknown id is a no-op.
  function dismissToast(id) {
    const timer = toastTimers.get(id);
    if (timer !== undefined) {
      clearTimeout(timer);
      toastTimers.delete(id);
    }
    const index = toasts.value.findIndex((toast) => toast.id === id);
    if (index === -1) {
      return false;
    }
    toasts.value.splice(index, 1);
    return true;
  }

  // Scope-dispose teardown: a disposed store must leave no timer that can
  // fire into it later. The queue is client-local, so its entries die with
  // the store instance alongside their timers (transport resets, by
  // contrast, deliberately KEEP the queue — toasts survive a reconnect).
  onScopeDispose(() => {
    for (const timer of toastTimers.values()) {
      clearTimeout(timer);
    }
    toastTimers.clear();
    toasts.value.length = 0;
  });

  const view = ref(initialView());
  const narrative = ref([]);
  const commandHistory = ref([]);
  const seenIndex = ref(0);
  // C4: the last OOB `ui_snapshot` / `ui_update` receive result. A rejected
  // (malformed) presentation is the "renderer cannot render" signal that
  // triggers the one-sync-per-episode auto-resync.
  const lastPanelRejection = ref(null);

  // The one declarative push (webclient-services-combat-creation-frames):
  // every family mounts ONLY a descriptor; content resolves at access time.
  // `openerKey` restores the parent's focus on a degradation; `unresolvable`
  // "root" exits the whole stack (the suggestions status split).
  function pushFrame(descriptor, openerKey, unresolvable) {
    inStackMutation = true;
    try {
      router.pushFrame(descriptor, {
        openerKey: openerKey === undefined ? null : openerKey,
        unresolvableAction: unresolvable || "pop",
      });
    } finally {
      inStackMutation = false;
    }
  }

  // Open one skill's target (or 威力 scale) menu from the root/skills menu,
  // mirroring the legacy plugin's `openCombatSkill`. The frame carries only
  // the skill key; the resolver opens the skill through the shared model.
  function openCombatSkill(skillKey) {
    const combat = frameResolver.combatModel();
    if (!combat) {
      return;
    }
    combat.focusSkillKey = skillKey;
    const menu = CombatMenu.openSkill(combat, skillKey);
    if (menu) {
      pushFrame({ source: "combat.skill", params: { skillKey } }, skillKey);
      if (menu.items.length > 0 && menu.items[0].scaleChoice) {
        // The freeform scale step preselects 威力×1 (the default behavior).
        router.focusItemByKey("scale-1");
      }
    }
    publishView();
  }

  function onRouterEvent(name, payload) {
    if (name === "settle-pop") {
      settlePopSeen = true;
      return;
    }
    if (name === "focus" || name === "disabled") {
      const combat = frameResolver.combatModel();
      if (name === "focus" && combat) {
        const item = payload && payload.item;
        // A focused skill row (its key is in the committed `skillByKey`) sets
        // the focused-skill model so the detail pane renders the skill's
        // (possibly disabled) reason — even for a disabled skill whose row
        // carries no `open-skill` action.
        if (
          item &&
          typeof item.key === "string" &&
          combat.skillByKey &&
          combat.skillByKey[item.key]
        ) {
          combat.focusSkillKey = item.key;
        }
        // A combat target-row focus is a client-local selection (spec: focus
        // and selection remain client-local until submission); record the
        // selected identity without dispatching any OOB action.
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
      // Escape from an exploration re-homed sub-dock (character / services):
      // clear the sub-dock and re-home the exploration root frame.
      else if (reducer.getState().mode === "exploration" && activeSubDock.value) {
        setActiveSubDock(null);
        // The sub-dock owned the surface, not the frame stack: re-home the
        // declarative exploration root (the sub-dock frames were legacy).
        inStackMutation = true;
        try {
          router.replaceFrame(EXPLORATION_ROOT_DESCRIPTOR, { openerKey: null });
        } finally {
          inStackMutation = false;
        }
      }
      return;
    }
    if (name === "toggle-drawer") {
      // H5: the `/` key routes bridge -> router -> here. Bump `drawerRequest`
      // so the shell's watcher focuses the always-present command field (D1/D2).
      drawerRequest += 1;
      publishView();
      return;
    }
    if (name !== "submit" && name !== "space") {
      return;
    }
    const item = payload && payload.item;
    if (!item) {
      return;
    }
    // Activation reads the RAW committed row (the focus projection strips the
    // intent fields): re-sync the key map for the current frame first (the
    // frame did not change between the focus event and this activation).
    // (webclient-services-combat-creation-frames: the router emits the full
    // resolved row — the dockRawByKey re-sync seam is deleted.)
    // The creation dock owns the router in creation mode (the legacy
    // creation_dock.js keyboard journey): submenu opens, preset-card saves,
    // confirmation dispatches, and cancel pops one level.
    if (creation && handleCreationItem(item)) {
      return;
    }
    // The exploration dock owns the router in exploration mode (the G2
    // hierarchical root + submenus): root entries open Move/Look/Interact/Wait
    // submenus and the Character/Quests/Inventory sub-docks, submenu rows
    // dispatch their `explore.*` actions.
    if (handleServiceItem(item)) {
      return;
    }
    if (handleExplorationItem(item)) {
      return;
    }
    // Combat keyboard hierarchy (the preserved CombatMenu model, mirroring the
    // legacy elosern_ui plugin's routing): open-skill / attack open a skill's
    // scale or target frame, skills / forfeit open their submenus, Space
    // toggles AREA candidates, and confirm submits the exact payload. The one
    // model instance is the registry's (the declared selection home).
    const combat = frameResolver.combatModel();
    if (combat) {
      if (name === "space") {
        if (item.actionId === "toggle-target" && item.payload && combat.focusSkillKey) {
          CombatMenu.toggleArea(combat, combat.focusSkillKey, item.payload.identity);
          publishView();
        }
        return;
      }
      // An AREA candidate row activated deliberately (pointer click or Enter on
      // the row) toggles the client-local selection exactly like Space; it is
      // never an OOB action (the server registers no `toggle-target`).
      if (item.actionId === "toggle-target") {
        if (item.payload && combat.focusSkillKey) {
          CombatMenu.toggleArea(combat, combat.focusSkillKey, item.payload.identity);
        }
        publishView();
        return;
      }
      // "open" items push a submenu (no OOB packet is sent).
      if (item.actionId === "open-skill" && item.payload) {
        openCombatSkill(item.payload.skillKey);
        return;
      }
      // H3: the skills tab pushes the category frame; a category with a
      // single skill group skips the group frame (openCategory collapses it),
      // a multi-group category pushes the group frame, and a group pushes
      // that group's skill frame (open-group).
      if (item.actionId === "open-category" && item.payload) {
        pushFrame(
          { source: "combat.category", params: { categoryIndex: item.payload.categoryIndex || 0 } },
          item.key
        );
        publishView();
        return;
      }
      if (item.actionId === "open-group" && item.payload) {
        pushFrame(
          {
            source: "combat.group",
            params: { categoryIndex: item.payload.categoryIndex || 0, groupIndex: item.payload.groupIndex || 0 },
          },
          item.key
        );
        publishView();
        return;
      }
      if (item.actionId === "choose-scale" && item.payload) {
        if (combat.focusSkillKey && CombatMenu.chooseScale(combat, combat.focusSkillKey, item.payload.scale)) {
          // The scale step confirmed: the target frame mounts the same
          // focused skill key; the resolver opens targets through the model.
          pushFrame({ source: "combat.target", params: { skillKey: combat.focusSkillKey } }, item.key);
          publishView();
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
        // H3: the skills tab opens the category frame (master-detail
        // navigation), replacing the flat paginated skill list.
        pushFrame({ source: "combat.categories", params: {} }, item.key);
        publishView();
        return;
      }
      if (item.key === "forfeit") {
        pushFrame({ source: "combat.forfeit", params: {} }, item.key);
        publishView();
        return;
      }
      // The client-local 背包 drawer row (add-inventory-item-actions, task
      // 6.3): activation opens the frameless inventory drawer without a
      // dispatch, an invented gameplay action, or a router frame.
      if (item.openDrawer === "inventory") {
        openHudDrawer("inventory");
        return;
      }
      // AREA confirm: build the exact payload from the live selection.
      if (item.confirm && combat.focusSkillKey) {
        const skill = combat.skillByKey[combat.focusSkillKey];
        if (skill && skill.targetSpec === "area") {
          const areaPayload = CombatMenu.areaPayload(skill);
          if (areaPayload) {
            dispatchAction(
              "combat.cast",
              areaPayload,
              castSubmitDisplay(skill, areaPayload, item.commandDisplay)
            );
          }
          return;
        }
      }
      // SINGLE-target rows: focus and selection remain client-local until
      // submission (no focus/selection mutation is ever sent); a deliberate
      // confirmation submits the OOB cast. Pointer activation performs the
      // identical confirmation the keyboard performs — exactly one
      // `combat.cast` with the same action ID and payload
      // (webclient-pointer-activation).
      if (
        typeof item.key === "string" &&
        item.key.startsWith("target-") &&
        item.payload &&
        Array.isArray(item.payload.target_ids) &&
        item.payload.target_ids.length > 0
      ) {
        lastTarget = String(item.payload.target_ids[0]);
        const focusSkill = combat.focusSkillKey
          ? combat.skillByKey[combat.focusSkillKey]
          : null;
        dispatchAction(
          "combat.cast",
          item.payload,
          focusSkill
            ? castSubmitDisplay(focusSkill, item.payload, item.commandDisplay)
            : item.commandDisplay || null
        );
        publishView();
        return;
      }
      // Real OOB action items (combat.cast / combat.flee / combat.forfeit).
      if (item.actionId) {
        dispatchAction(item.actionId, item.payload || {}, item.commandDisplay || null);
        return;
      }
    }
    // The router emits the full resolved row (the focus PROJECTION in the
    // view is what strips intent fields, not the event): the OOB intent,
    // navigation surface, and target identity read straight off it.
    const raw = item;
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

  // Whether the creation overlay is the presenting surface: the committed
  // `creation` panel exists and is not explicitly unavailable — exactly the
  // mount predicate `AppClient` uses for `CreationOverlay` (duck finding 1:
  // the overlay's presence, not the creation-dock state `creationPanelOf`).
  // While it is mounted it renders the action result itself, so the
  // narrative feed gains no duplicate line (webclient-action-result-feedback
  // D-C).
  function creationOverlayPresenting(rs) {
    const panel = (rs.panels && rs.panels.creation) || null;
    return !!panel && panel.available !== false;
  }

  // D5: the in-flight lock releases with the tested legacy action-client
  // semantics. A matching `ui_action_result` (same request id, same epoch)
  // sets the declared presentation revision; the lock then releases only
  // when the committed revision reaches that revision (immediately when none
  // was declared, unconditionally for a `no_puppet` rejection; a `stale`
  // outcome keeps the lock until the recovery snapshot commits — the
  // `ui_sync` re-request itself is the C3 transport's job).
  function handleActionResult(rs) {
    if (!inFlight) {
      return;
    }
    const result = rs.lastActionResult;
    if (!result || result.requestId !== inFlight.requestId) {
      return;
    }
    if (result.epoch !== rs.activeEpoch) {
      return;
    }
    // Recognition/dedup unit: the in-flight request plus its own
    // handled-result fingerprint (duck findings 2/3). The old global
    // "changed from previous" equality could both re-append (a foreign
    // result delivered between two observations of this request's result)
    // and silence a legitimate match (a result that was already sitting in
    // the reducer before this dispatch started). A recognized result is
    // recorded on the in-flight record, so re-delivery / re-observation is
    // idempotent and foreign results cannot interfere. A cached duplicate
    // for a foreign request still fails the request-id match above and
    // never unlocks.
    const fingerprint = stableStringify(result);
    if (inFlight.handledResult === fingerprint) {
      return;
    }
    inFlight.handledResult = fingerprint;
    inFlight.presentationRevision = result.presentationRevision;
    // webclient-action-result-feedback: a recognized non-success result
    // (rejected / stale / error) speaks exactly once as one narrative error
    // line carrying the server-authored message verbatim. The match guards
    // above (changed-from-previous, request id, epoch) are the dedup unit;
    // the creation overlay, when mounted, already presents the result and
    // suppresses the line. The lock/uncertain/revision mechanics below are
    // untouched by the append.
    if (
      NON_SUCCESS_OUTCOMES.indexOf(result.outcome) !== -1 &&
      !creationOverlayPresenting(rs)
    ) {
      const message =
        typeof result.message === "string" && result.message.trim() !== ""
          ? result.message
          : ACTION_RESULT_FALLBACK_MESSAGE;
      appendText("err", message);
    }
    // The action-feedback crit toast (webclient-action-feedback D3): a
    // recognized non-success `creation.concept` result ALSO speaks exactly
    // once, above the overlay. This branch shares the narrative line's
    // recognition/dedup unit and non-success outcome test above, but NOT its
    // `!creationOverlayPresenting` presentation gate — a concept failure
    // necessarily lands while the creation overlay is mounted, so applying
    // the overlay gate to the toast channel would silence it everywhere it
    // matters. The channel is action-scoped by the in-flight `actionId`
    // (custom/preset results, including their stale exception, never reach
    // it). The overlay result region and narrative behavior above are
    // unchanged (toasts are additive). A success result pushes NOTHING here:
    // the success-confirmation info toast's sole writer is the form layer
    // (`retool-concept-fill-navigation`'s `applyProposal` via `pushToast`).
    if (
      NON_SUCCESS_OUTCOMES.indexOf(result.outcome) !== -1 &&
      inFlight.actionId === CreationMenu.CONCEPT_ACTION
    ) {
      pushToast({
        title:
          typeof result.message === "string" && result.message.trim() !== ""
            ? result.message
            : ACTION_RESULT_FALLBACK_MESSAGE,
        tone: "crit",
      });
    }
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

  // The committed `services` panel signature: a replacement (a reconnect
  // resync) discards the unsubmitted client-local quantity form.
  let lastServicesSig = null;
  // H5 (tasks 7.5/7.8): re-apply the persisted presentation preferences at
  // load (placed after the signature variables `publishView` touches so the
  // init-time `publishView` cannot hit a temporal-dead-zone).
  loadPresentationPreferences();

  // ---------------------------------------------------------------- frames
  //
  // Every family's frames are DECLARATIVE (webclient-declarative-frame-stack,
  // completed by webclient-services-combat-creation-frames): a push stores
  // only a `{source, params}` descriptor; every read of the frame resolves
  // through the injected registry seam at access time, so a committed push
  // ALWAYS reaches an open frame — no copy-based refresh, signature gate,
  // re-home, or raw-row resync machinery exists anywhere.

  // The exploration-family push map: a root `openSubmenu` key or submenu frame
  // title -> the descriptor of its declarative frame. The map is the ONE
  // place naming exploration frame sources; the frame content itself comes
  // only from the resolver.
  const EXPLORATION_SUBMENU_PUSHES = {
    move: { source: "exploration.move", params: {} },
    look: { source: "exploration.look", params: {} },
    interact: { source: "exploration.interact", params: {} },
    wait: { source: "exploration.wait", params: {} },
    suggestions: { source: "exploration.suggestions", params: {} },
  };
  // The suggestions frame leaves the WHOLE stack when its envelope commits
  // `unavailable` (the options-surface no-pane rule): exit to the root
  // without a reason row. Every other exploration submenu pops one level.
  const UNRESOLVABLE_ACTION = { "exploration.suggestions": "root" };

  // The declarative-frame mutation window (webclient-declarative-frame-stack
  // D-A): the ONE commit hook for the exploration dock. A committed push
  // never re-pushes anything — the next access re-resolves. This window only
  // (a) settles the stack so a degradation pops synchronously at the commit,
  // (b) discards the sub-dock / hosted service drawer the frame stack no
  // longer hosts, and (c) discards the hosted surface's local state (the
  // quantity form rides the shop drawer's removal, webclient-service-menus'
  // discard-on-replacement contract generalized to hosted-frame pops).
  // The combat/creation settle follows the same descriptor-driven rules;
  // no family has a copy-based refresh path any more.
  function settleFrameStack(rs) {
    if (inStackMutation) {
      return;
    }
    // The stack is never empty in a live mode; depth 0 only exists between
    // store creation and the first commit (the pre-session window), where
    // there is nothing to settle.
    // A settle-driven pop is observed through the router's `settle-pop`
    // event (recorded here, cleared per window): the depth BEFORE a settle
    // cannot be sampled — every accessor settles first, so a pre-read would
    // consume the very pop the rules below must observe.
    settlePopSeen = false;
    const depthBefore = router.depth();
    if (depthBefore === 0) {
      // The stack mount: an empty stack only exists before the first
      // teardown/publish, where the committed mode's root descriptor is
      // posted as the one-frame stack (it degrades to the marker-reason row
      // until its panel commits, then recovers). After this point the stack
      // never empties in a live mode.
      resetFramesToRoot();
      return;
    }
    inStackMutation = true;
    let descriptor = null;
    try {
      router.depth(); // access-time settle: pops/cascades/degrades, zero timers
      descriptor = router.currentDescriptor();
      // Family re-home: a committed panel-form switch (exploration panel ->
      // combat panel on the SAME stack) re-posts the root DESCRIPTOR of the
      // new family when the root frame is current — the declarative form of
      // the deleted combat signature gate. No copy is built; the new root
      // re-resolves from the committed state on every access.
      if (router.depth() === 1) {
        const want = rootDescriptorFor(rs);
        if (descriptor && want && descriptor.source !== want.source) {
          router.replaceFrame(want, { openerKey: null });
          descriptor = router.currentDescriptor();
        }
      }
    } finally {
      inStackMutation = false;
    }
    const popped = settlePopSeen;
    // Sub-dock rule (unchanged): a cascade that popped everything the
    // exploration sub-dock hosts leaves the root, so the sub-dock closes.
    if (
      rs.mode === "exploration" &&
      activeSubDock.value &&
      popped &&
      (!descriptor || descriptor.source === "exploration.root")
    ) {
      setActiveSubDock(null);
    }
    // Hosted-drawer rule (webclient-services-combat-creation-frames): when a
    // settle POP happened (depth decreased) and the frame now current is NOT
    // a hosted service frame, the hosted drawer closes with the frame and the
    // surface's local state is discarded through the existing cleanup (the
    // quantity form; the quest drawer's selection/confirmation state is
    // component-local and dies on unmount). A descendant pop that returns to
    // another hosted frame of the SAME surface leaves the drawer open; a
    // manually-opened drawer with no pop is never event-closed.
    if (popped && !descriptorIsServiceFrame(descriptor)) {
      const drawerName = hudDrawer.value;
      if (drawerName === "quest" || drawerName === "shop") {
        hudDrawer.value = null;
        setServiceSurface(null);
        if (drawerName === "shop") {
          quantityForm.value = null;
        }
      }
    }
  }

  // One declarative exploration push: the store mutation window covers the
  // push itself (the push-time resolve focuses the first item; an
  // immediately-unresolvable push settles per its policy before the focus
  // event reaches the store). `openerKey` is the activated row's key so a
  // later degradation restores focus to it.
  function pushExplorationFrame(descriptor, openerKey) {
    // The suggestions status split: `unavailable` exits the whole stack
    // to the root (the no-pane rule); every other submenu pops one level.
    pushFrame(descriptor, openerKey, UNRESOLVABLE_ACTION[descriptor.source] || "pop");
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
    creation.view = "confirm";
    creation.confirmDescriptor = {
      source: "creation.confirm",
      params: { kind, presetKey: kind === "preset" ? presetKey || null : null },
    };
    // The confirm frame content resolves from the committed panel every
    // access — the confirm copy (`creation.confirmItems`) is deleted.
    pushFrame(creation.confirmDescriptor, null);
  }

  // Router submit for an exploration item (the G2 hierarchical dock): the root
  // entries open submenus (Move/Look/Interact/Wait), the Character/Quests/
  // Inventory entries re-home the services/character sub-docks, submenu rows
  // dispatch their `explore.*` action, and an interact target selection pushes
  // that target's affordance menu. Returns true when the item belonged to the
  // exploration dock.
  function handleExplorationItem(item) {
    const rs = reducer.getState();
    if (rs.mode !== "exploration") {
      return false;
    }
    // A client-local drawer-open row (the frameless 背包 row, the
    // `openCharacter` precedent): open the drawer without pushing a frame,
    // switching the sub-dock, or recording a service surface.
    if (item.openDrawer === "inventory") {
      openHudDrawer("inventory");
      return true;
    }
    if (item.openSubmenu && EXPLORATION_SUBMENU_PUSHES[item.openSubmenu]) {
      // Declarative push (webclient-declarative-frame-stack): the frame is
      // ONLY the descriptor — the submenu content resolves at access time,
      // so a later commit reaches this open frame without any re-push.
      pushExplorationFrame(EXPLORATION_SUBMENU_PUSHES[item.openSubmenu], item.key);
      publishView();
      return true;
    }
    if (item.openCharacter) {
      setActiveSubDock("character");
      // H4 (task 4.2): the Character root opens the character-status drawer
      // (the re-homed character surface). The sub-dock flag is kept so the
      // dock's routing stays intact; the drawer is the new home of the
      // surface.
      openHudDrawer("status");
      return true;
    }
    if (item.openServiceSubmenu) {
      setActiveSubDock("services");
      // H4 (task 4.3): record the service surface at push time (design D2)
      // so the frame-hosting watcher routes to the matching reference drawer.
      // The submenu key maps to a service surface: "guild" / "shop" are
      // surfaces; "quests" is the guild's quest log (guild surface).
      const subKey = item.openServiceSubmenu;
      const surface =
        subKey === "quests" ? "guild" : (subKey === "guild" ? "guild" : subKey);
      setServiceSurface(surface);
      // Push the declarative service submenu (guild: register/board/quests/
      // exam; shop: 貨架/販賣) — the frame is ONLY the descriptor; content
      // resolves from the committed services panel at access time.
      pushFrame({ source: "services." + subKey, params: {} }, item.key);
      publishView();
      return true;
    }
    // A back row returns to the parent menu: pop exactly one router level
    // (the parent's focus key is its own frame state; the copy-driven dock
    // re-sync is gone — the parent frame re-resolves on the next read).
    if (item.goBack) {
      inStackMutation = true;
      try {
        router.popMenu();
      } finally {
        inStackMutation = false;
      }
      publishView();
      return true;
    }
    // An interact target row: push the target's declarative affordance frame.
    // The subject travels as the descriptor's `{identity}` — the SAME
    // server-authored identity the row carries — so the open frame follows
    // the committed panel (identity loss pops it; no client-local copy of
    // the selection is kept for exploration surfaces).
    if (item.openTarget != null) {
      pushExplorationFrame({ source: "exploration.target", params: { identity: item.openTarget } }, item.key);
      publishView();
      return true;
    }
    // The "talk-scripted" item opens the scripted-keyword menu for the target
    // of the CURRENT frame (G2: finite keyword buttons, not free text). The
    // identity comes from the open target frame's descriptor — one source,
    // never a second client-local selection.
    if (item.openKeywords) {
      const current = router.currentDescriptor();
      const identity = current && current.params ? current.params.identity : null;
      if (identity !== null && identity !== undefined) {
        pushExplorationFrame({ source: "exploration.keywords", params: { identity } }, item.key);
      }
      publishView();
      return true;
    }
    // The rest-duration item (openRestForm): opens the bounded custom-duration
    // form before any OOB action (webclient-exploration-menu: the form is the
    // sole local UI exception — confirm opens the form, no dispatch yet).
    if (item.openRestForm) {
      restFormRequest += 1;
      publishView();
      return true;
    }
    // A free-form dialogue item: open the command drawer for the selected
    // target; the typed speech submits as explore.talk_freeform with the
    // target's npc_id (the guarded dialogue seam, webclient-exploration-menu).
    if (item.freeform) {
      freeformTarget = item.npcId;
      lastTarget = String(item.npcId);
      drawerRequest += 1;
      publishView();
      return true;
    }
    // A real OOB exploration action (explore.move / look / wait / engage /
    // talk_scripted / talk_freeform): one dispatch through the single entry.
    // The item's server-authored `commandDisplay` descriptor is passed through
    // so the CommandEcho catalog resolves exactly one display line.
    if (item.actionId) {
      dispatchAction(item.actionId, item.payload || {}, item.commandDisplay || null);
      return true;
    }
    return false;
  }

  // Router submit for a services sub-dock item (the re-homed services surface):
  // board/quests/stock/sell/quest-N open bounded submenus, the 放棄 row opens the
  // explicit confirmation screen, and the action rows (register / accept / turnin /
  // exam / buy / sell) dispatch their `guild.*`/`shop.*` action. Returns true
  // when the item belonged to the services sub-dock.
  function handleServiceItem(item) {
    const rs = reducer.getState();
    if (rs.mode !== "exploration" || activeSubDock.value !== "services") {
      return false;
    }
    // A client-local drawer-open row (the services root's frameless 背包
    // row): open the drawer without pushing a frame or recording a service
    // surface (the exploration-root branch above is the same interception).
    if (item.openDrawer === "inventory") {
      openHudDrawer("inventory");
      return true;
    }
    // A bounded services submenu (board / quests / stock / sell / quest-N):
    // push the declarative submenu frame; the per-quest detail pane (詳情 /
    // 放棄 / 回報) resolves per-index through the registry.
    if (item.openSubmenu) {
      // H4 (task 4.3): record the service surface at push time — the guild
      // frames (board / quests / quest-detail) route to the 任務 drawer and
      // the shop frames (stock / sell) route to the 商店 drawer.
      const subKey = item.openSubmenu;
      let descriptor = null;
      if (
        subKey === "guild" ||
        subKey === "shop" ||
        subKey === "board" ||
        subKey === "quests" ||
        subKey === "stock" ||
        subKey === "sell"
      ) {
        setServiceSurface(SERVICE_SURFACE_FOR_SOURCE["services." + subKey]);
        descriptor = { source: "services." + subKey, params: {} };
      } else if (subKey.startsWith("quest-")) {
        setServiceSurface("guild");
        // The quest-detail frame names its quest by the row INDEX the guild
        // quest rows carry (`quest-<i>`); the resolver re-reads that row from
        // the committed panel at every access (a vanished index pops it).
        const questIndex = Number(subKey.split("-")[1]);
        if (Number.isInteger(questIndex) && questIndex >= 0) {
          descriptor = { source: "services.quest-detail", params: { questIndex } };
        }
      }
      if (descriptor) {
        pushFrame(descriptor, item.key);
        publishView();
        return true;
      }
    }
    // The quest-detail 放棄 row: push the explicit confirmation menu (the
    // `.services-confirm` screen renders behind it; no mutation is sent yet).
    if (item.confirmActionId) {
      // H4 (task 4.3): the abandon confirmation frame belongs to the guild
      // (quest) surface.
      setServiceSurface("guild");
      // The confirmation frame names its quest by the CURRENT quest-detail
      // frame's index (the row the 放棄 belongs to) — the resolver composes
      // the same confirm menu from that row's server-authored fields on
      // every access. Falling back to index 0 only when no quest-detail
      // frame is current (unreachable through the UI; the row only exists
      // inside a quest-detail frame).
      const current = router.currentDescriptor();
      const questIndex =
        current && current.source === "services.quest-detail" && current.params
          ? current.params.questIndex
          : 0;
      pushFrame({ source: "services.confirm", params: { questIndex } }, item.key);
      publishView();
      return true;
    }
    // A bounded trade row (a stock/sell row carrying a `quantity` {min,max}):
    // open the local quantity form; the typed quantity is validated against the
    // bounds before the `shop.buy` / `shop.sell` dispatch.
    if (item.quantity) {
      openQuantityForm(item);
      return true;
    }
    // A services action row (guild.register / quest_accept / quest_turnin /
    // exam_start / shop.buy / shop.sell): dispatch the exact OOB action,
    // forwarding the row's server-authored display descriptor (buy/sell rows
    // carry `itemLabel`; the guild rows resolve from the payload alone).
    if (item.actionId) {
      dispatchAction(item.actionId, item.payload || {}, item.commandDisplay || null);
      return true;
    }
    return false;
  }

  // Router submit for a creation item (the legacy `handleItem`): submenu opens,
  // preset-card saves, confirm dispatches, and cancel pops one level. Returns
  // true when the item belonged to the creation dock.
  function handleCreationItem(item) {
    if (!creation) {
      return false;
    }
    if (item.openSubmenu === "presets") {
      creation.view = "presets";
      pushFrame({ source: "creation.presets", params: {} }, item.key);
      return true;
    }
    if (item.openSubmenu === "custom") {
      creation.view = "custom";
      // A marker frame gives Escape a level to pop without discarding values.
      pushFrame({ source: "creation.form", params: { view: "custom" } }, item.key);
      return true;
    }
    if (item.openSubmenu === "concept") {
      creation.view = "concept";
      // The concept entry point opens the free-text concept field; a marker
      // frame gives Escape a level to pop without discarding typed values.
      pushFrame({ source: "creation.form", params: { view: "concept" } }, item.key);
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
      dispatchAction(item.actionId, item.payload || {}, item.commandDisplay || null);
      return true;
    }
    if (item.key && item.key.indexOf("cancel-") === 0) {
      inStackMutation = true;
      try {
        router.popMenu();
      } finally {
        inStackMutation = false;
      }
      creation.view = creation.pendingActivate === "preset" ? "presets" : "custom";
      creation.pendingActivate = null;
      creation.pendingActivateKey = null;
      creation.confirmDescriptor = null;
      // The guarded pop suppresses the focus-driven publish; publish the
      // restored view here so the overlay slice loses the confirm rows.
      publishView();
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
      creation.confirmDescriptor = null;
    } else if (creation.view === "custom") {
      creation.view = "root";
    } else if (creation.view === "concept") {
      creation.view = "root";
    }
    if (name === "escape-root") {
      // escape-root does not pop a router level: re-sync the router to the
      // frame matching the restored view (declaratively).
      pushOrReplaceFrameForView(creation.view);
    }
    publishView();
  }

  // The creation stage -> frame descriptor map (the one source for the
  // root-reset and escape-root re-syncs).
  function descriptorForCreationView(viewName) {
    if (viewName === "presets") {
      return { source: "creation.presets", params: {} };
    }
    if (viewName === "custom" || viewName === "concept") {
      return { source: "creation.form", params: { view: viewName } };
    }
    if (viewName === "confirm" && creation && creation.confirmDescriptor) {
      return creation.confirmDescriptor;
    }
    return { source: "creation.root", params: {} };
  }

  function pushOrReplaceFrameForView(viewName) {
    const descriptor = descriptorForCreationView(viewName);
    inStackMutation = true;
    try {
      if (router.depth() > 0) {
        router.replaceFrame(descriptor, { openerKey: null });
      } else {
        router.pushFrame(descriptor, { openerKey: null });
      }
    } finally {
      inStackMutation = false;
    }
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
        confirmDescriptor: null,
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
      const draft = panel.draft || null;
      if (draft && draft.mode === "preset") {
        openCreationConfirm("preset", draft.preset_key || null, "presets");
      } else if (draft && (draft.mode === "custom" || draft.mode === "concept")) {
        if (creation.view !== "confirm") {
          creation.view = "custom";
          // The custom-form marker frame is the one-frame stack (Escape
          // resumes the root). Declarative: the frame is the descriptor.
          router.resetFrame({ source: "creation.form", params: { view: "custom" } }, { openerKey: null });
        }
      } else if (creation.view !== "confirm") {
        creation.view = "root";
        // The root frame re-posts from the committed panel on every genuine
        // signature change (same reset semantics; no menu copy is built).
        router.resetFrame({ source: "creation.root", params: {} }, { openerKey: null });
      }
    }
  }

   function syncRouterGates() {
     router.setMutationInFlight(!!inFlight);
     router.setAwaitingRevision(inFlight && inFlight.presentationRevision !== null ? inFlight.presentationRevision : null);
   }

   // H4 (task 4.3/4.4): the drawer controller's commit-path sync. Runs on
   // every committed view (the store is the single writer). It (a) tears
   // down the drawers on a mode change out of exploration, an epoch reset, or
   // a transport loss (design D3), and (b) hosts the router's service frames
   // inside the matching reference drawer (design D2): while a service frame
   // is the router's current frame the drawer is open and renders that
   // frame's rows; leaving the surface closes the drawer. The status drawer's
   // payload is available in every mode, so it stays openable in combat.
   function syncHudDrawer(prev, rs) {
      // Re-entrancy guard: a router stack mutation emits `focus`, which
      // re-enters `publishView`. The old signature gates stopped that loop
      // for the copy path; with declarative frames the guard is explicit —
      // the outer mutation already applied the teardown, a nested pass must
      // mutate nothing (the legacy copy families' rebuilds were exactly the
      // recursion the old `lastMenuSig` existed to break).
      if (inStackMutation) {
        return;
      }
      const modeChanged = !!prev && prev.mode !== rs.mode;
      const epochChanged = !!prev && prev.epoch !== rs.activeEpoch;
      const transportLost = !!prev && prev.connected && !rs.connected;
      // No-puppet detach is a teardown event in its own right: the reducer
      // retains the epoch and the mode on a `no_puppet` protocol error, so
      // the three transitions above never fire for it. Without this
      // condition a depth >1 exploration stack would survive the character
      // leaving the puppet.
      const detached = !!prev && prev.phase !== "detached" && rs.phase === "detached";

      if (modeChanged || epochChanged || transportLost || detached) {
        // A committed mode change out of exploration, an epoch reset, or a
        // transport loss each close the services-backed drawers and discard
        // local selection, quantity, and confirmation state (the quantity
        // form is also nulled by the panel-replacement logic above).
        const d = hudDrawer.value;
        if (d === "quest" || d === "shop" || d === "inventory") {
          hudDrawer.value = null;
        }
        if (transportLost || epochChanged || detached) {
          if (hudDrawer.value) {
            hudDrawer.value = null;
          }
        }
        // H5 (webclient-hud-05-overlays-and-command-line, design D7): the
        // open full-screen overlay is force-closed on the same three events
        // (mode change into creation, epoch reset, transport loss); the host
        // restores focus to the overlay's own trigger (the opener element
        // captured at open time, design D7).
        if (hudOverlay.value !== null) {
          hudOverlay.value = null;
          hudOverlayOpener.value = null;
        }
        setServiceSurface(null);
        // Teardown final form (webclient-services-combat-creation-frames):
        // every event above yields EXACTLY one root frame — the committed
        // mode's declarative root descriptor. The mode the teardown targets
        // may not have its panel committed yet; the root then degrades to the
        // marker-reason row and recovers on the next commit (no copy rebuild,
        // no empty-stack fuse).
        resetFramesToRoot();
        return;
      }

      // Frame hosting (design D2): while a service frame is the router's
      // current frame, ensure the matching reference drawer is open (the
      // invariant: no state where a service frame is current while its drawer
      // is closed). Declarative hosting: the CURRENT FRAME'S DESCRIPTOR is
      // the one source — a hosted services source maps to its drawer. A
      // service drawer opened manually (e.g. the combat 狀態 opener or a
      // user action) stays open when no service frame is current until an
      // explicit close or a teardown event.
      // The surface still gates the OPEN side: a frame pushed outside a
      // production handler (no surface recorded — the frameless-bag
      // defensive state) never steals a manually-opened drawer.
      const hostedSource = router.currentDescriptor();
      if (descriptorIsServiceFrame(hostedSource) && serviceSurface.value) {
        const drawerName = SERVICE_SURFACE_DRAWERS[SERVICE_SURFACE_FOR_SOURCE[hostedSource.source]];
        if (drawerName && hudDrawer.value !== drawerName) {
          hudDrawer.value = drawerName;
        }
      }
    }

   function initialView() {
     return buildView(null, reducer.getState());
   }

  function buildView(prev, rs) {
    const panels = rs.panels || {};
    const panel = panels.context_actions || null;
    const suggestions = panel && panel.suggestions ? panel.suggestions : null;
    // Pre-session totality: before the first publish mounts the root
    // descriptor the stack is empty (the mount point is `settleFrameStack`),
    // where frame-content reads would throw. `mounted` guards every read.
    const mounted = router.depth() > 0;
    const currentItem = mounted ? router.currentItem() : null;
    // The combat selection reads resolve through the resolver's one model —
    // calling it here is the adoption point; outside combat form it is null.
    const combatNow = panel && panel.kind === "combat" ? frameResolver.combatModel() : null;
    // The creation confirm copy is deleted: the overlay's confirm intent
    // resolves through the current confirm descriptor at view-build time.
    const resolvedConfirmItems =
      creation && creation.view === "confirm" && creation.confirmDescriptor
        ? (() => {
            const menu = frameResolver.resolve(creation.confirmDescriptor);
            return menu && !menu.unresolvable && Array.isArray(menu.items) ? menu.items : [];
          })()
        : [];

    // The derived vitals slice (H2, design D5): the three gauge ratios plus
    // the low-HP presentation state, computed from the committed `status`
    // payload alone — no new payload field, no server call. An unavailable
    // status panel yields null ratios and `lowHp: false` (not true by
    // default); the state is non-load-bearing, so the numerals and the 危險
    // marker carry the same information at every value.
    const statusPanel = panels.status;
    const vitals =
      statusPanel && statusPanel.available !== false && statusPanel.resources
        ? {
            hp: gaugeRatio(statusPanel.resources.hp),
            mp: gaugeRatio(statusPanel.resources.mp),
            sp: gaugeRatio(statusPanel.resources.sp),
            lowHp: isLowHp(statusPanel.resources),
          }
        : { hp: null, mp: null, sp: null, lowHp: false };

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
      loggedIn,

       connectionStatus: connectionStatusFor(rs.connected, loggedIn, rs.phase),
       vitals,
       statusSlice: {
        connected: rs.connected,
        locationLabel: resolveLocationLabel(panels),
        timeLabel: formatTimeLabel(rs.serverTime),
      },
       prompt,
       lastSurface,
       lastTarget,
       drawerRequest,
       drawerCloseRequest,
       restFormRequest,
        activeSubDock: activeSubDock.value,
        // H4 (task 4.1): the single open-drawer name (null | skill | inventory
        // | shop | quest | lore | status); at most one drawer is open at a
        // time (structural: one value).
        hudDrawer: hudDrawer.value,
        // H5 (task 5.2): the single open-overlay name (null | map | settings
        // | help | lineage), plus the opener element captured at open time —
        // the anchor
        // for the host's focus restoration (design D7).
        hudOverlay: hudOverlay.value,
        hudOverlayOpener: hudOverlayOpener.value,
        // H5 (task 7.5/7.8): the client-local presentation preferences the
        // settings surface owns — the narrative prose scale, the text-to-HTML
        // narrative toggle, the optional reduced-motion override and the
        // colorblind status palette. No setting dispatches a `ui_action`; the
        // store applies each to the document's presentation tokens and
        // persists it through the versioned layout store.
        fontScale: prefs.fontScale,
        textToHtml: prefs.text2html,
        reducedMotion: prefs.reducedMotion,
        colorblind: prefs.colorblind,

       contextActions: panel,
      suggestions,
      suggestionsView: OptionCards.buildOptionsView(panel || {}),
      suggestionsSignature: OptionCards.suggestionsSignature(suggestions),
       localMapModel: panels.local_map
         ? {
             ...LocalMap.reducePanel(panels.local_map),
             available: panels.local_map.available !== false,
             // The registry-owned unavailable reason so the island and the map
             // overlay can render it (H5 offline-degradation, task 8.9).
             reason: panels.local_map.reason,
           }
         : null,
       // The keyboard router's current combat menu frame (root/skills/scale/
       // target) so the visible dock follows keyboard navigation (Option B).
       combatMenu: mounted ? router.currentMenu() : null,
       // H3 (task 3.2): the root frame's menu — the dock's tab bar renders
       // the root frame's items while the pane follows the current frame,
       // both from one commit. Null while the root is degraded: the marker
       // row is pane content (below), never a tab (the router keeps it out
       // of `rootMenu` for exactly this reason).
       rootMenu: mounted ? router.rootMenu() : null,
       // The degraded-root presentation (webclient-frame-resolution): the
       // single disabled marker-reason row the pane host renders while the
       // root frame itself is unresolvable; null in every normal state.
       degradedRoot: mounted ? router.degradedRoot() : null,
       // The keyboard router's menu depth (1 = the root frame, 2+ = a submenu
       // frame is active). The action dock's detail pane renders only at
       // depth 2+ (or in combat mode), not at the exploration root.
       dockDepth: router.depth(),
       // H3: the full frame stack (root -> current), the data source for
       // the dock's breadcrumb (HudFrame's crumb strip renders these).
       dockTrail: mounted ? router.trail() : [],
       // The focused AREA skill's selected candidate identities (the client-
       // local selection the Space toggle mutates); drives the "✓" marker.
       combatSelected:
         combatNow && combatNow.focusSkillKey && combatNow.skillByKey[combatNow.focusSkillKey]
           ? combatNow.skillByKey[combatNow.focusSkillKey].selected
           : [],
       // H3 (task 6.5): the focused skill model for the master-detail pane —
       // the `SkillDetailPane` renders this committed model, never inventing
       // a `戰鬥外` badge (design D14).
       focusedSkill:
         combatNow && combatNow.focusSkillKey && combatNow.skillByKey[combatNow.focusSkillKey]
           ? combatNow.skillByKey[combatNow.focusSkillKey]
           : null,

      // The character-creation dock stage (the legacy creation dock port): the
      // keyboard-router menu the overlay mirrors. Null outside creation mode.
      creationView: creation
        ? {
            stage: creation.view,
            confirmItems: resolvedConfirmItems,
            confirmLabel: resolvedConfirmItems.length > 0 ? resolvedConfirmItems[0].label : null,
            confirmAction:
              resolvedConfirmItems.length > 0 ? resolvedConfirmItems[0].actionId : null,
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

      // The live client-local toast queue (webclient-action-feedback D1): the
      // same reactive array reference on every publish; the reducer's
      // committed snapshot never carries it and nothing persists it.
      toasts: toasts.value,
    };
  }

  function publishView() {
    const prev = view.value;
    const rs = reducer.getState();
    // The unsubmitted quantity form is client-local (spec webclient-service-menus):
    // a replaced `services` panel (e.g. a reconnect resync) discards it.
    const servicesPanel = (rs.panels && rs.panels.services) || null;
    const servicesSig = stableStringify(servicesPanel);
    if (quantityForm.value && servicesSig !== lastServicesSig) {
      quantityForm.value = null;
    }
    lastServicesSig = servicesSig;
    handleTransportLifecycle(prev, rs);
    handleActionResult(rs);
    releaseIfReady(rs);
    rebuildCreationDock(prev, rs);
    syncRouterGates();
    settleFrameStack(rs);
    // The settle MUST precede the drawer sync: the hosting read in
    // `syncHudDrawer` is itself an access-time settle trigger, which would
    // otherwise pop the stack BEFORE the settle observes the depth decrease
    // (its hosted-drawer close and sub-dock rules would never fire) and then
    // leave a drawer open that hosts nothing.
    syncHudDrawer(prev, rs);
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
    // A disconnect ends the authenticated session (mirrors the D10 console
    // model): the next socket starts waiting for login again. Reset before
    // the reducer commit so the synchronous publish sees the cleared flag.
    if (!connected) {
      loggedIn = false;
    }
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

  function setLoggedIn(value) {
    loggedIn = !!value;
    publishView();
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

  // Clear the pending freeform dialogue target (a cancelled drawer must not
  // capture later ordinary commands as dialogue speech).
  function clearFreeformTarget() {
    if (freeformTarget != null) {
      freeformTarget = null;
      publishView();
    }
  }

  function sendText(text) {
    if (!view.value.connected) {
      return false;
    }
    const value = String(text == null ? "" : text);
    commandHistory.value.push(value);
    while (commandHistory.value.length > MAX_COMMAND_HISTORY) {
      commandHistory.value.shift();
    }
    // An active freeform dialogue target routes the typed speech through the
    // guarded dialogue seam (explore.talk_freeform) with the target's npc_id,
    // never as ordinary narrative text. The NPC's server-authored display name
    // is read from the committed exploration panel and passed as the
    // `commandDisplay` descriptor so the CommandEcho catalog resolves the line.
    if (freeformTarget != null) {
      const rs = reducer.getState();
      const panel = (rs.panels && rs.panels.exploration) || {};
      let npcLabel = "";
      for (const target of panel.interact || []) {
        if (String(target.identity) === String(freeformTarget)) {
          npcLabel = target.display_name || "";
          break;
        }
      }
      const sent = dispatchAction("explore.talk_freeform", { npc_id: freeformTarget, speech: value }, { npcLabel });
      // A successful dock-borrowed send closes the drawer and restores
      // action-dock focus (webclient-desktop-shell: the borrowed-drawer send
      // returns focus to the dock); a rejected send keeps the drawer open.
      if (sent !== null) {
        drawerCloseRequest += 1;
      }
      freeformTarget = null;
      publishView();
      return true;
    }
    // Ordinary text command: the typed command line is part of the narrative
    // stream (a player input line), never a mutation echo.
    appendText("in", value);
    if (sender && typeof sender.sendText === "function") {
      sender.sendText(value);
    }
    return true;
  }

  // The participant display names (server-authored committed combat panel
  // rows) for one payload-ordered identity list; `null` when any identity has
  // no committed row, so a partial target list is never echoed as complete
  // (D3b).
  function participantNamesByIdentity(identities) {
    const rs = reducer.getState();
    const panel = (rs.panels && rs.panels.context_actions) || {};
    const byId = new Map();
    if (panel.kind !== "combat") {
      return null;
    }
    (Array.isArray(panel.participants) ? panel.participants : []).forEach((p) => {
      if (p && typeof p.display_name === "string" && p.display_name !== "") {
        byId.set(String(p.identity), p.display_name);
      }
    });
    const names = [];
    for (const identity of identities) {
      const name = byId.get(String(identity));
      if (!name) {
        return null;
      }
      names.push(name);
    }
    return names;
  }

  // The echo descriptor for one combat.cast submit (D3): the row descriptor
  // plus the chosen NON-DEFAULT freeform magnitude label and — for payloads
  // with explicit selected targets — the payload-ordered target labels
  // (D3b). Display-only: the payload is never touched here.
  function castSubmitDisplay(skill, payload, baseDisplay) {
    const display = Object.assign({}, baseDisplay || {});
    if (!display.skillLabel && typeof skill.label === "string" && skill.label !== "") {
      display.skillLabel = skill.label;
    }
    if (
      display.scaleLabel === undefined &&
      Array.isArray(skill.freeformScales) &&
      skill.freeformScales.length > 0 &&
      skill.scale !== 1
    ) {
      const scaleLabel = CombatMenu.scaleLabelFor(skill);
      if (scaleLabel !== null) {
        display.scaleLabel = scaleLabel;
      }
    }
    if (
      display.targetLabel === undefined &&
      display.targetLabels === undefined &&
      Array.isArray(payload.target_ids) &&
      payload.target_ids.length > 0 &&
      !payload.target_shorthand
    ) {
      const names = participantNamesByIdentity(payload.target_ids);
      if (names !== null) {
        display.targetLabels = names;
      }
    }
    return display;
  }

  // One committed exploration interact target's server-authored display name
  // by identity, or null (the freeform-talk lookup, factored out).
  function explorationTargetName(identity) {
    if (identity === undefined || identity === null) {
      return null;
    }
    const rs = reducer.getState();
    const panel = (rs.panels && rs.panels.exploration) || {};
    for (const target of panel.interact || []) {
      if (String(target.identity) === String(identity)) {
        return typeof target.display_name === "string" && target.display_name !== ""
          ? target.display_name
          : null;
      }
    }
    return null;
  }

  // The committed combat-form `context_actions` panel's skill label for one
  // skill key (the v3 nested categories -> groups -> skills shape flattened),
  // or null.
  function combatSkillLabel(skillKey) {
    if (typeof skillKey !== "string" || skillKey === "") {
      return null;
    }
    const rs = reducer.getState();
    const panel = (rs.panels && rs.panels.context_actions) || {};
    if (panel.kind !== "combat") {
      return null;
    }
    for (const category of panel.skills || []) {
      for (const group of category.groups || []) {
        for (const skill of group.skills || []) {
          if (skill && skill.key === skillKey) {
            return typeof skill.label === "string" && skill.label !== ""
              ? skill.label
              : null;
          }
        }
      }
    }
    return null;
  }

  // The central descriptor fill (complete-ui-command-echo D3, intent
  // surfaces): component intents carry only {action_id, payload}, so missing
  // echo labels are read VERBATIM from committed store state at dispatch time
  // (the freeform-talk branch generalized). The fill never overwrites an
  // explicitly provided field, never composes or invents a label, and feeds
  // only the catalog call — the `ui_action` envelope is untouched. Absent
  // state leaves the field absent (catalog silence, audited by the
  // per-surface table).
  function fillDisplayFor(actionId, payload, display) {
    const base = display || null;
    const filled = Object.assign({}, base || {});
    // Declared-field semantics: an empty array counts as ABSENT (a caller
    // handing over `targetLabels: []` has no labels, and committed state may
    // supply them); any other present value — including falsy strings — is
    // never overwritten.
    const has = (field) => {
      const value = base && base[field];
      if (Array.isArray(value)) {
        return value.length > 0;
      }
      return value !== undefined && value !== null && value !== "";
    };
    const panels = (reducer.getState().panels) || {};
    if (actionId === "shop.buy" || actionId === "shop.sell") {
      if (!has("itemLabel")) {
        const shop = (panels.services && panels.services.shop) || {};
        const rows =
          (actionId === "shop.buy" ? shop.stock : shop.sellable) || [];
        for (const row of rows) {
          if (
            row &&
            row.item_key === payload.item_key &&
            typeof row.display_name === "string" &&
            row.display_name !== ""
          ) {
            filled.itemLabel = row.display_name;
            break;
          }
        }
      }
    } else if (
      actionId === "explore.talk_scripted" ||
      actionId === "explore.talk_freeform" ||
      actionId === "explore.party_invite" ||
      actionId === "explore.party_leave"
    ) {
      if (!has("npcLabel")) {
        const name = explorationTargetName(payload.npc_id);
        if (name !== null) {
          filled.npcLabel = name;
        }
      }
    } else if (actionId === "explore.engage" || actionId === "explore.look") {
      if (!has("targetLabel")) {
        // `explore.engage` carries `monster_id`; `explore.look` carries
        // `target_id` (both are interact-target identities in the committed
        // exploration panel).
        const identity =
          actionId === "explore.engage" ? payload.monster_id : payload.target_id;
        const name = explorationTargetName(identity);
        if (name !== null) {
          filled.targetLabel = name;
        }
      }
    } else if (actionId === "combat.cast") {
      if (!has("skillLabel")) {
        const label = combatSkillLabel(payload.skill_key);
        if (label !== null) {
          filled.skillLabel = label;
        }
      }
      if (
        !has("targetLabel") &&
        !has("targetLabels") &&
        Array.isArray(payload.target_ids) &&
        payload.target_ids.length > 0 &&
        !payload.target_shorthand
      ) {
        const names = participantNamesByIdentity(payload.target_ids);
        if (names !== null) {
          filled.targetLabels = names;
        }
      }
    } else if (actionId === "creation.activate" || actionId === "creation.reset") {
      // The creation overlay's confirm intent emits only {action_id, payload}
      // — the descriptor rides the confirmation item resolved from the
      // current confirm descriptor at echo time (no stored confirm copy).
      let confirmItem = null;
      if (creation && creation.view === "confirm" && creation.confirmDescriptor) {
        const menu = frameResolver.resolve(creation.confirmDescriptor);
        if (menu && !menu.unresolvable && Array.isArray(menu.items) && menu.items.length > 0) {
          confirmItem = menu.items[0];
        }
      }
      const carried = confirmItem && confirmItem.commandDisplay;
      if (carried) {
        for (const field of Object.keys(carried)) {
          if (!has(field)) {
            filled[field] = carried[field];
          }
        }
      }
    }
    return filled;
  }

  function dispatchAction(actionId, payload, display) {
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
    inFlight = { requestId, actionId, presentationRevision: null, handledResult: null };
    // `handledResult` is the per-request dedup unit
    // (webclient-action-result-feedback): the fingerprint of the result this
    // in-flight dispatch has already recognized. Re-observation (publishView
    // re-runs, reducer replays of the identical result) never re-appends; a
    // foreign result cannot erase the record, so a re-delivery of THIS
    // request's result stays silent even after another request's result
    // passed through the reducer.
    // `actionId` (webclient-action-feedback D3): the local correlation the
    // concept crit trigger reads; the exposed `view.dispatch.inFlight` copy
    // keeps its frozen two-field shape.
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
        // The display command line (webclient-input-narrative): resolve exactly
        // one bounded echo line from the pure catalog and append it as a literal
        // text line; a rejected result leaves the line in place. Intent
        // surfaces get their missing labels filled from committed state first
        // (fillDisplayFor); the filled descriptor feeds the catalog ONLY — the
        // envelope above is already built and untouched.
        const echoDisplay = fillDisplayFor(actionId, envelope.payload, display);
        const line = CommandEcho.commandLine(actionId, envelope.payload, echoDisplay);
        if (line) {
          appendText("in", line);
        }
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
    if (!creation) {
      return false;
    }
    openCreationConfirm("reset", null, creation.view);
    publishView();
    return true;
  }

  function focusPress(key, repeat) {
    // The bounded services quantity form (a local UI exception) captures its
    // own keys before the keyboard router: digits and Backspace edit the
    // bounded quantity, Enter submits a valid quantity (or keeps the form open
    // when the value is out of bounds), and Escape closes it.
    const q = quantityForm.value;
    if (q && q.open) {
      if (key >= "0" && key <= "9") {
        ServiceMenu.quantityInput(q.state, key);
        publishView();
        return true;
      }
      if (key === "Backspace") {
        ServiceMenu.quantityBackspace(q.state);
        publishView();
        return true;
      }
      if (key === "Escape") {
        q.open = false;
        publishView();
        return true;
      }
      if (key === "Enter") {
        const value = ServiceMenu.validateQuantity(q.state);
        if (value !== null) {
          dispatchAction(
            q.actionId,
            { item_key: q.itemKey, quantity: value },
            q.itemLabel ? { itemLabel: q.itemLabel } : null
          );
          q.open = false;
        }
        publishView();
        return true;
      }
      // Any other key while the form is open is consumed locally.
      return true;
    }
    // The dock's positional row picks (webclient-align-01-dock-chrome): the
    // legend `數字鍵 1-4 · Enter 執行 · Esc 返回` names the first four rows
    // of the current dock frame as reachable by the top-row number keys. A
    // digit moves the frame's focus onto its row (1-indexed, rendered
    // order) and activates it through the same confirm path Enter uses
    // (disabled rows show their explanation, in-flight rows stay locked,
    // repeats are suppressed by the router's guard). Focus moving is the
    // consumption signal: a digit whose row does not exist (a frame with
    // fewer rows, or the pre-session empty stack) is unclaimed and falls
    // through to the text / command-history path. Implemented entirely
    // through the frozen router façade members — the UMD source is not
    // edited (design D1).
    if (key === "1" || key === "2" || key === "3" || key === "4") {
      const slot = Number(key) - 1;
      if (router.depth() === 0) {
        return false;
      }
      const menu = router.currentMenu();
      const item = menu && menu.items ? menu.items[slot] : null;
      if (!item) {
        return false;
      }
      const itemKey = item.key !== undefined ? item.key : item.label;
      if (!router.focusItemByKey(itemKey)) {
        return false;
      }
      // The activation itself may decline (disabled, locked, or the
      // held-repeat guard) after the focus moved; the key was still
      // consumed, exactly as a focused Enter that shows an explanation.
      router.confirm({ source: "keyboard" });
      return true;
    }
    return router.press(key, !!repeat);
  }

  function focusConfirm(source) {
    return router.confirm({ source: source || "keyboard" });
  }

  function focusEscape() {
    // The Escape-key operation through the preserved public key-entry adapter
    // (`press` is a frozen façade member; the internal `escape` function is
    // not on the frozen instance surface). H3's breadcrumb back chevron and
    // the creation cancel-confirm both route through this same path.
    return router.press(KeyboardRouter.ESCAPE);
  }

  function focusItemByKey(key) {
    return router.focusItemByKey(key);
  }

  // H3 (task 4.5): the pointer tab click — return the router to the root
  // frame (bounded pop loop, task 8.7: exactly one deliberate activation,
  // no stray `ui_action`), focus the clicked tab's item, and confirm it with
  // `source="pointer"`.
  function tabToRootAndConfirm(itemKey, source) {
    while (router.depth() > 1) {
      router.popMenu();
    }
    if (router.focusItemByKey(itemKey)) {
      focusConfirm(source || "pointer");
    }
    publishView();
  }

  // H3 (task 6.6): the 威力 scale step and the AREA shorthand step — the
  // pointer path mirrors the keyboard `choose-scale` / `choose-shorthand`
  // dispatch (the store is the single writer).
  function chooseScale(scale) {
    const combat = frameResolver.combatModel();
    if (combat && combat.focusSkillKey && CombatMenu.chooseScale(combat, combat.focusSkillKey, scale)) {
      // The pointer path mirrors the keyboard step: the target frame is the
      // declarative `{skillKey}` descriptor; content resolves at access.
      pushFrame({ source: "combat.target", params: { skillKey: combat.focusSkillKey } }, null);
      publishView();
    }
  }

  function chooseShorthand(shorthand) {
    const combat = frameResolver.combatModel();
    if (combat && combat.focusSkillKey) {
      CombatMenu.chooseShorthand(combat, combat.focusSkillKey, shorthand);
      publishView();
    }
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
    setLoggedIn,
    setSender,
    setPrompt,
    appendText,
    sendText,
    clearFreeformTarget,
    dispatchAction,
    requestCreationReset,
    focusPress,
     focusConfirm,
     focusEscape,
     focusItemByKey,
     tabToRootAndConfirm,
     chooseScale,
     chooseShorthand,
     // The single root-reset entry (replaces the deleted menu-less
     // `router.reset`): post the committed mode's root descriptor as the
     // one-frame stack. Browser helpers use it to normalize the stack.
     resetFramesToRoot,
     markNarrativeSeen,
    clearUncertain,
    getSender,
    // The action-feedback toast queue API (webclient-action-feedback): the
    // store is the sole writer; `retool-concept-fill-navigation`'s overlay
    // pushes its success confirmation through this entry point.
    pushToast,
    dismissToast,
    // The declarative-frame derivation seam (frame-resolvers.js): resolve a
    // `{source, params}` descriptor against the committed state right now.
    resolveFrame: (descriptor) => frameResolver.resolve(descriptor),
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
      // The bounded services quantity form (a local UI exception): exposed so
      // the services panels can sync their per-row quantity control to the
      // activated item (the `services-quantity` testid follows the form's
      // item_key). Discarded (nulled) on a `services` panel replacement.
      quantityForm,
      // H4 (task 4.1/4.2): the reference drawer controller — the single open
      // entry (`openHudDrawer` over the closed name set, unknown names
      // rejected) and the single close entry (`closeHudDrawer`, which pops
      // one menu level when the drawer hosts a service frame).
       openHudDrawer,
       closeHudDrawer,
        // H5 (task 5.3): the full-screen overlay controller — the single open
        // entry (`openOverlay` over `map` / `settings` / `help` / `lineage`,
        // unknown names
        // rejected, closes any open drawer for mutual exclusion, design D8)
        // and the single close entry (`closeOverlay`). The opener element is
        // captured at open time and published as `view.hudOverlayOpener` for
        // the host's focus restoration (design D7).
        openOverlay,
        closeOverlay,
        // H5 (task 7.8): the presentation-preferences controller — the
        // client-local presentation state the settings surface owns (prose
        // scale, text-to-HTML toggle, optional reduced-motion override,
        // colorblind palette). No setting dispatches a `ui_action`; each
        // setter applies the preference to the document's presentation tokens
        // and persists it through the versioned layout store (reloading the
        // latest validated wrapper before writing).
        setFontScale,
        setTextToHtml,
        setReducedMotion,
        setColorblind,
        // H4 (R3, webclient-hud-04-reference-drawers): whether the keyboard
        // router's current frame is a service frame (guild / shop)
        // so the drawer layer can render that frame's rows through the shared
        // row renderer beside the surface's own presentation.
        currentFrameIsServiceFrame,
     };
});
