// C2 (webclient-vue-08-wire-bridge-contracts): the public-contract browser
// bridge (A1's frozen contract audit, design D1/D2).
//
// esbuild's CommonJS interop imports the preserved UMD logic without
// re-attaching the `window.Elosern.*` browser globals that the legacy
// `<script>` load path exposes, so the OOB contract and the existing browser
// tests would lose their façades. This module re-exposes the A1 frozen
// façade surface (docs/development/webclient-vue-frozen-contract-audit.md
// §1) over the same imported modules and the C1 store:
//
// - `window.Elosern.Protocol` / `window.Elosern.KeyboardRouter` are the
//   imported UMD modules, re-exposed byte-identical (design D1: re-exposure,
//   not re-implementation).
// - `window.Elosern.LayoutStore` is the imported versioned layout-persistence
//   UMD (browser-persistence-is-versioned-and-presentation-only), so the
//   browser-acceptance layout tests can construct a storage-bound store.
// - `window.Elosern.narrativeInput` is the store's single narrative/choice-
//   point append path: `appendInput` echoes exactly one `.inp` line through
//   `store.sendText`; the choice-point stream-end block is owned by the
//   preserved `StreamEndBlock` controller (one mounted block, the only
//   scroll/unread owner).
// - `window.Elosern.actions` is the single action-dispatch entry: `submit`
//   routes through the store's `dispatchAction` (dispatch-only, one mutation
//   in flight, design D5); `client` re-exposes the locked action-client
//   members read off the store's committed view; `sync` / `handle*` are the
//   OOB entry points the C3 evennia.js transport will feed.
//
// Document key events route through the KeyboardRouter's handle contract:
// claimed exactly when the router consumed the key, and unconsumed keys fall
// through to the text path (the live transport binds in C3; the legacy text
// console keeps its turn).

import Protocol from "./lib/protocol.js";
import KeyboardRouter from "./lib/keyboard_router.js";
import StreamEndBlock from "./lib/stream_end_block.js";
import LayoutStore from "./lib/layout_store.js";

// The claimed-when-consumed key set (webclient-desktop-shell keyboard
// routing): arrows move within the active finite menu, Enter confirms the
// focused item, Escape pops exactly one menu level, Space toggles
// multi-select, and `/` toggles the command drawer. The router's `handle`
// return value is the claim signal, so the bridge prevents the default
// exactly when the router consumed the key.
const CLAIMED_KEYS = ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Enter", "Escape", " ", "/"];

function isEditable(target) {
  if (!target || !target.tagName) {
    return false;
  }
  return (
    target.tagName === "INPUT" ||
    target.tagName === "SELECT" ||
    target.tagName === "TEXTAREA" ||
    target.isContentEditable === true
  );
}

export function createWindowBridge(store) {
  // The narrative stream-end block is owned by the preserved controller:
  // `mount`/`replace` keep at most one block at the stream end; the
  // scroll/unread decision is the controller's single owner.
  let blockController = null;

  function getBlockController() {
    if (!blockController) {
      const container = document.querySelector('[data-testid="narrative-feed"]');
      blockController = StreamEndBlock.createStreamEndBlock(container, {
        atBottom: () =>
          !!container && container.scrollTop + container.clientHeight + 2 >= container.scrollHeight,
        scrollToBottom: () => {
          if (container) {
            container.scrollTop = container.scrollHeight;
          }
        },
      });
    }
    return blockController;
  }

  // The single narrative/choice-point append path (façade note §1):
  // `appendInput` echoes one `.inp` line through the store's send path; the
  // `display` descriptor never leaks into the wire payload (the store builds
  // the envelope without it).
  const narrativeInput = {
    appendInput(text, display) {
      return store.sendText(text);
    },
    mountChoicePoint(block) {
      return getBlockController().mount(block);
    },
    replaceChoicePoint(block) {
      return getBlockController().replace(block);
    },
    unmountChoicePoint() {
      return getBlockController().unmount();
    },
  };

  function currentGeneration() {
    return store.view.generation;
  }

  // The single action-dispatch entry (façade note §1): `submit` returns a
  // request id exactly when a real request dispatched; locked or duplicate
  // submits dispatch nothing (the store's `dispatchAction` gates on
  // connected / mutationsLocked / in-flight, design D5).
  function submit(actionId, payload, display) {
    return store.dispatchAction(actionId, payload, display);
  }

  function sync() {
    const s = store.getSender();
    if (s && typeof s.sendSync === "function") {
      // The live `ui_sync` re-sync request goes out through the C3 transport
      // seam; until the transport attaches, sync is a guarded no-op (the
      // store re-syncs through the next accepted snapshot, C1 contract).
      s.sendSync();
    }
  }

  function toWireActionResult(result) {
    // A camelCase validated result (the legacy action client's normalized
    // shape) is reverse-normalized to the wire envelope: the Protocol
    // reducer's `requireExactFields` accepts only wire (snake_case) field
    // names, so a camelCase object would be silently rejected.
    if (result.requestId !== undefined && result.request_id === undefined) {
      const wire = {
        protocol_version: result.protocolVersion,
        presentation_epoch: result.epoch,
        request_id: result.requestId,
        outcome: result.outcome,
        code: result.code,
        message: result.message,
        presentation_revision: result.presentationRevision,
      };
      if (result.correlationId !== undefined) {
        wire.correlation_id = result.correlationId;
      }
      return wire;
    }
    return result;
  }

  function handleActionResult(result) {
    // C3's transport feeds either the wire envelope (`request_id`,
    // snake_case) or the reduced camelCase result (`requestId`); both are
    // routed through the store's single receive path, so one in-flight
    // request can be completed through either spelling.
    if (result && (result.requestId || result.request_id)) {
      store.receive(currentGeneration(), "ui_action_result", [toWireActionResult(result)]);
    }
  }

  function handlePresentation(presentationEnvelope) {
    if (presentationEnvelope) {
      store.receive(currentGeneration(), "ui_update", [presentationEnvelope]);
    }
  }

  function handleReconnect() {
    store.beginTransport(currentGeneration() + 1);
    store.setConnected(true);
    sync();
  }

  function handleTransportReset() {
    store.beginTransport(currentGeneration() + 1);
    store.setConnected(false);
  }

  // The locked action-client surface (façade note §1 / audit §2.1): the
  // locked / in-flight / uncertain / last-result reads come off the store's
  // committed view; the `sync` / `submit` / `on*` entries route through the
  // façades above.
  const client = {
    sync: sync,
    submit,
    onActionResult: handleActionResult,
    onPresentationAccepted: () => {
      // The C1 store releases the in-flight gate when the committed revision
      // reaches the declared presentation revision (`releaseIfReady` runs in
      // every publish); re-run the gate check on the new committed state.
      store.refreshView();
    },
    onReconnect: handleReconnect,
    onDetached() {
      // The puppet detached (OOC): the store marks the mutation uncertain and
      // the router gates follow (the C1 store's transport-lifecycle handling).
      store.setConnected(false);
    },
    onTransportReset: handleTransportReset,
    isLocked: () => {
      const v = store.view;
      return !!v.mutationsLocked || !v.connected;
    },
    isInFlight: () => store.view.dispatch.inFlight !== null,
    inFlightRequestId: () =>
      store.view.dispatch.inFlight ? store.view.dispatch.inFlight.requestId : null,
    uncertain: () => store.view.dispatch.uncertain,
    lastResult: () => store.view.lastActionResult,
  };

  // One-sync-per-episode resync guard (the legacy requestResync contract):
  // a renderer that cannot render a panel requests exactly one `ui_sync` for
  // the same failure episode; a second request in the same episode is blocked
  // so a malformed panel cannot create a sync loop. The episode resets on a
  // new transport generation (a reconnect re-arms it).
  const resyncGuard = {};

  function requestResync(panelName) {
    const generation = currentGeneration();
    let entry = resyncGuard[panelName];
    if (!entry || entry.episode !== generation) {
      entry = { episode: generation, requested: false };
      resyncGuard[panelName] = entry;
    }
    if (entry.requested) {
      return false;
    }
    entry.requested = true;
    sync();
    return true;
  }

  function resetResyncEpisode(panelName) {
    // Re-arm the one-sync guard for a panel: the harness uses this to allow
    // a fresh resync after a reconnect re-armed the transport generation.
    delete resyncGuard[panelName];
  }

  const actions = {
    client,
    sync,
    submit,
    handleActionResult,
    handlePresentation,
    handleReconnect,
    handleTransportReset,
    requestResync,
    resetResyncEpisode,
  };

  // Document keydown routes through the store's single focus entry (the
  // router is the store's focus owner, design D4): claimed exactly when the
  // router consumed the key. Unclaimed keys are not swallowed (fall through
  // to the text / command-history path; the transport text path is C3's).
  function onDocumentKeydown(event) {
    if (isEditable(event.target)) {
      // The open drawer field (or a creation form, or a rest form) owns its
      // own keys (C2-01/02/03 re-expressed contracts): the bridge does not
      // claim them.
      return;
    }
    if (event.ctrlKey || event.metaKey || event.altKey) {
      return;
    }
    // A focused native button (a choice-point card, a dock menu item)
    // activates itself on Enter; the router must not claim that Enter
    // (spec webclient-options-surface: card click handlers are native; the
    // router ignores keyboard-synthesized clicks). Arrow keys still route
    // through the router so keyboard navigation keeps working.
    const target = event.target;
    if (event.key === "Enter" && target && target.closest && target.closest("button, [role=button]")) {
      return;
    }
    const claimed = store.focusPress(event.key, !!event.repeat);
    if (claimed && CLAIMED_KEYS.includes(event.key)) {
      event.preventDefault();
    }
  }

  function installKeyRouting() {
    document.addEventListener("keydown", onDocumentKeydown);
  }

  function uninstallKeyRouting() {
    document.removeEventListener("keydown", onDocumentKeydown);
  }

  installKeyRouting();

  window.Elosern = {
    Protocol,
    KeyboardRouter,
    LayoutStore,
    narrativeInput,
    actions,
  };

  // The returned object is the installation handle (facade + store + the
  // key-routing uninstall hook); `window.Elosern` itself carries exactly the
  // four frozen façades (§1) and nothing else. The live keyboard-router
  // instance is exposed through the handle (the C4 harness re-map): browser
  // slices read `depth()` / `currentItem()` off it instead of the retired
  // `window.Elosern.keyboard` global.
  return {
    facade: window.Elosern,
    store,
    router: store.router,
    uninstall: uninstallKeyRouting,
  };
}
