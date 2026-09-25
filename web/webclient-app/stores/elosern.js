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
//
// Composition (the elosern/ split): this facade owns the reducer core and the
// client-local mutable bookkeeping on `ctx`, then applies the cohesive group
// modules (stores/elosern/<group>.js) over the shared context. Every group
// contributes its state refs / actions / view-projection functions to `ctx`
// exactly as the original single-file setup declared them; the store's
// returned key set and the publish-order semantics are unchanged.

import { ref } from "vue";
import { defineStore } from "pinia";

import Protocol from "../lib/protocol.js";
import { createFrameResolver } from "./frame-resolvers.js";

import { resolveLocationLabel } from "./elosern/shared.js";
import { applyHud } from "./elosern/hud.js";
import { applyPreferences } from "./elosern/preferences.js";
import { applyToasts } from "./elosern/toasts.js";
import { applyFrames } from "./elosern/frames.js";
import { applyCombat } from "./elosern/combat.js";
import { applyCreation } from "./elosern/creation.js";
import { applyInteraction } from "./elosern/interaction.js";
import { applyTransport } from "./elosern/transport.js";
import { applyView } from "./elosern/view.js";

export { resolveLocationLabel };

export const useElosernStore = defineStore("elosern", () => {
  // The shared context every group module reads and writes.
  const ctx = {};

  // D1: the preserved reducer is the store core (CJS-interop import; the UMD
  // source and its Node gate are never edited).
  ctx.reducer = Protocol.createStore();

  // The declarative-frame resolver registry (webclient-frame-resolver-registry
  // D-A): menus derived from the reducer's committed state at call time. The
  // cutover changes route their push sites through it; this seam stays the
  // single derivation entry (`resolveFrame` below, bridge-exposed).
  ctx.frameResolver = createFrameResolver({ getState: () => ctx.reducer.getState() });

  // D5: client-local dispatch bookkeeping (the tested legacy action-client
  // semantics; the transport send is an attachable seam).
  ctx.inFlight = null; // {requestId, presentationRevision}
  ctx.uncertain = false;
  ctx.requestCounter = 0;
  ctx.sender = null; // { sendAction(envelope), sendText(text) } — C3 attaches evennia.js
  ctx.lastSurface = null;
  ctx.lastTarget = null;
  // Monotonic signal the shell watches to open the command drawer (a freeform
  // dialogue entry point requests a drawer open + field focus).
  ctx.drawerRequest = 0;
  // Monotonic signal the shell watches to CLOSE the command drawer and
  // restore action-dock focus (a successful dock-borrowed send, e.g. freeform
  // dialogue). Ordinary text sends keep the drawer open, so only the
  // borrowed (freeform) path bumps this.
  ctx.drawerCloseRequest = 0;
  // The npc identity for an active freeform dialogue; set when a freeform
  // affordance is activated, cleared when its speech is submitted.
  ctx.freeformTarget = null;
  // Monotonic signal the shell watches to open the exploration rest-duration
  // form (the wait/rest entry point).
  ctx.restFormRequest = 0;
  // A dispatched OOB mutation that has not yet been confirmed (its result
  // was withheld or the presentation has not committed). Set on dispatch,
  // cleared only when the in-flight gate releases; a transport loss while it
  // is set marks the mutation uncertain (spec: submitted-but-unconfirmed
  // before transport loss is treated as unconfirmed, shown by the notice).
  ctx.mutationSubmitted = false;
  // The request ID of the last dispatched OOB mutation, used to correlate the
  // client's observed result with the specific in-flight request (a prior
  // result for a different request ID does not confirm the current one).
  ctx.lastSubmittedRequestId = null;
  ctx.prompt = "";
  // Client-local session state (mirrors the D10 console model): the evennia.js
  // `logged_in` OOB event marks the account attached; a disconnect resets it.
  // The transport status slice needs it because the server never sends a
  // `ui_snapshot` to an anonymous session, so "connected with no snapshot"
  // means "waiting for login" until the account actually logs in.
  ctx.loggedIn = false;
  // The CombatMenu model (client-local skill/scale/AREA selection) lives in
  // the resolver registry — the ONE model home (the declared purity
  // exception); the store reaches it only through
  // `frameResolver.combatModel()`, never a second copy.

  // The legacy character-creation dock port state (the creation group owns
  // its lifecycle; see stores/elosern/creation.js). Null outside creation
  // mode; shape: {view, confirmDescriptor, pendingActivate,
  // pendingActivateKey, pendingSaveRequestId, returnStage, panelSig}.
  ctx.creation = null;

  // Set while the store drives a router stack mutation, so a focus emit that
  // re-enters the store never nests a second mutation.
  ctx.inStackMutation = false;
  // Set when the router reports a settle-driven pop during the current
  // publish window (see `settleFrameStack`).
  ctx.settlePopSeen = false;

  // The reactive view/narrative refs (the view group projects into `view`).
  ctx.view = ref(null); // assigned right after the groups are applied
  // All narrative line appends go through `appendText` (transport.js), which
  // assigns monotonic `seq` and tokenizes non-`in` lines once.
  ctx.narrative = ref([]);
  ctx.narrativeSeq = 0;
  ctx.responseMarks = ref([]);
  ctx.commandHistory = ref([]);
  ctx.seenIndex = ref(0);
  // C4: the last OOB `ui_snapshot` / `ui_update` receive result. A rejected
  // (malformed) presentation is the "renderer cannot render" signal that
  // triggers the one-sync-per-episode auto-resync.
  ctx.lastPanelRejection = ref(null);
  // The view group's computed slices (collected for the store's return).
  ctx.computed = {};

  // Apply the cohesive groups. None publishes at apply time; the
  // cross-group seams (ctx.publishView, ctx.router, ctx.hudDrawer, ...) are
  // only touched at call time, after the whole composition exists.
  applyHud(ctx);
  applyPreferences(ctx);
  applyToasts(ctx);
  applyFrames(ctx);
  applyCombat(ctx);
  applyCreation(ctx);
  applyInteraction(ctx);
  applyTransport(ctx);
  applyView(ctx);

  // The initial committed view (the original `initialView()`): built before
  // any publish so `view` is a complete snapshot from the first render.
  ctx.view.value = ctx.buildView(null, ctx.reducer.getState());

  // H5 (tasks 7.5/7.8): re-apply the persisted presentation preferences at
  // load (the original site: after the signature variables `publishView`
  // touches, so the init-time `publishView` cannot hit a
  // temporal-dead-zone).
  ctx.loadPresentationPreferences();

  ctx.reducer.subscribe(() => {
    ctx.publishView();
  });

  // Re-run the committed-view publish (releaseIfReady + router-gate sync) so
  // the presentation gate is re-evaluated on a new committed state; the C2
  // bridge calls it from the `handlePresentation`/`onPresentationAccepted`
  // entry points.
  function refreshView() {
    ctx.publishView();
  }

  return {
    view: ctx.view,
    narrative: ctx.narrative,
    responseMarks: ctx.responseMarks,
    commandHistory: ctx.commandHistory,
    unreadCount: ctx.unreadCount,
    receive: ctx.receive,
    beginTransport: ctx.beginTransport,
    setConnected: ctx.setConnected,
    setLoggedIn: ctx.setLoggedIn,
    setSender: ctx.setSender,
    setPrompt: ctx.setPrompt,
    appendText: ctx.appendText,
    sendText: ctx.sendText,
    clearFreeformTarget: ctx.clearFreeformTarget,
    borrowDialogueCommand: ctx.borrowDialogueCommand,
    captionDialoguePresented: ctx.captionDialoguePresented,
    dispatchAction: ctx.dispatchAction,
    requestCreationReset: ctx.requestCreationReset,
    focusPress: ctx.focusPress,
    focusConfirm: ctx.focusConfirm,
    focusEscape: ctx.focusEscape,
    focusItemByKey: ctx.focusItemByKey,
    tabToRootAndConfirm: ctx.tabToRootAndConfirm,
    chooseScale: ctx.chooseScale,
    chooseShorthand: ctx.chooseShorthand,
    // The single root-reset entry (replaces the deleted menu-less
    // `router.reset`): post the committed mode's root descriptor as the
    // one-frame stack. Browser helpers use it to normalize the stack.
    resetFramesToRoot: ctx.resetFramesToRoot,
    markNarrativeSeen: ctx.markNarrativeSeen,
    clearUncertain: ctx.clearUncertain,
    partyAvailable: ctx.computed.partyAvailable,
    partySlots: ctx.computed.partySlots,
    objectivesAvailable: ctx.computed.objectivesAvailable,
    objectivesRows: ctx.computed.objectivesRows,
    rosterAvailable: ctx.computed.rosterAvailable,
    rosterCharacters: ctx.computed.rosterCharacters,
    rosterCanCreate: ctx.computed.rosterCanCreate,
    rosterMaxCharacters: ctx.computed.rosterMaxCharacters,
    rosterSwitchLocked: ctx.computed.rosterSwitchLocked,
    rosterLockReason: ctx.computed.rosterLockReason,
    combatParticipants: ctx.computed.combatParticipants,
    explorationInteract: ctx.computed.explorationInteract,
    getSender: ctx.getSender,
    // The action-feedback toast queue API (webclient-action-feedback): the
    // store is the sole writer; `retool-concept-fill-navigation`'s overlay
    // pushes its success confirmation through this entry point.
    pushToast: ctx.pushToast,
    dismissToast: ctx.dismissToast,
    // The declarative-frame derivation seam (frame-resolvers.js): resolve a
    // `{source, params}` descriptor against the committed state right now.
    resolveFrame: (descriptor) => ctx.frameResolver.resolve(descriptor),
    refreshView,
    // The live keyboard-router instance (C4 harness re-map): the managed
    // browser suite reads `depth()` / `currentItem()` off it; the store owns
    // the focus router (design D4), so it is exposed read-only for the harness.
    router: ctx.router,
    lastPanelRejection: ctx.lastPanelRejection,
    // The protocol store's subscription seam (the C4 harness re-map): browser
    // tests observe `beginTransport` notifications (the transport-reset state
    // with a null epoch and empty panels) to gate on deterministic state.
    subscribe: (listener) => ctx.reducer.subscribe(listener),
    // Set which re-homed sub-dock currently owns the action-dock surface
    // (null clears). The sub-dock panels set/clear this on mount/unmount;
    // the suggestions section hides while one is active.
    setActiveSubDock: ctx.setActiveSubDock,
    // H4 (task 4.1/4.2): the reference drawer controller — the single open
    // entry (`openHudDrawer` over the closed name set, unknown names
    // rejected) and the single close entry (`closeHudDrawer`).
    openHudDrawer: ctx.openHudDrawer,
    closeHudDrawer: ctx.closeHudDrawer,
    // H5 (task 5.3): the full-screen overlay controller — the single open
    // entry (`openOverlay` over `map` / `settings` / `help` / `lineage`,
    // unknown names
    // rejected, closes any open drawer for mutual exclusion, design D8)
    // and the single close entry (`closeOverlay`). The opener element is
    // captured at open time and published as `view.hudOverlayOpener` for
    // the host's focus restoration (design D7).
    openOverlay: ctx.openOverlay,
    closeOverlay: ctx.closeOverlay,
    // H5 (task 7.8): the presentation-preferences controller — the
    // client-local presentation state the settings surface owns (prose
    // scale, text-to-HTML toggle, optional reduced-motion override,
    // colorblind palette). No setting dispatches a `ui_action`; each
    // setter applies the preference to the document's presentation tokens
    // and persists it through the versioned layout store (reloading the
    // latest validated wrapper before writing).
    setFontScale: ctx.setFontScale,
    setTextToHtml: ctx.setTextToHtml,
    setReducedMotion: ctx.setReducedMotion,
    setColorblind: ctx.setColorblind,
  };
});
