// C2 (webclient-vue-08-wire-bridge-contracts) browser-bridge check: the A1
// frozen façade surface re-exposed as `window.Elosern.*`; the single narrative
// append path, the single action dispatch entry, and the claim-exactly-when-
// consumed key routing through the store's keyboard router. The live evennia
// transport binding is C3's; this check drives the façades over the C1 store
// and the imported UMD modules with no duplicated append or action path.

import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { createWindowBridge } from "../../bridge.js";
import { useElosernStore } from "../../stores/elosern.js";
import * as fx from "../store/protocol_fixtures.js";

const NARRATIVE_INPUT_MEMBERS = [
  "appendInput",
  "mountChoicePoint",
  "replaceChoicePoint",
  "unmountChoicePoint",
];
 const ACTIONS_MEMBERS = [
   "client",
   "sync",
   "submit",
   "handleActionResult",
   "handlePresentation",
   "handleReconnect",
   "handleTransportReset",
   "requestResync",
   "resetResyncEpisode",
 ];
const ACTIONS_CLIENT_MEMBERS = [
  "sync",
  "submit",
  "onActionResult",
  "onPresentationAccepted",
  "onReconnect",
  "onDetached",
  "onTransportReset",
  "isLocked",
  "isInFlight",
  "inFlightRequestId",
  "uncertain",
  "lastResult",
];

let activeUninstall = null;

function installBridge() {
  if (activeUninstall) {
    activeUninstall();
  }
  setActivePinia(createPinia());
  const store = useElosernStore();
  const bridge = createWindowBridge(store);
  activeUninstall = bridge.uninstall;
  return { store, facade: bridge.facade };
}

afterEach(() => {
  if (activeUninstall) {
    activeUninstall();
    activeUninstall = null;
  }
});

function openActiveSession(store) {
  store.beginTransport(1);
  store.setConnected(true);
  const result = store.receive(1, "ui_snapshot", [
    fx.snapshot({
      panels: {
        status: fx.statusPanel(),
        exploration: fx.explorationPanel(),
        local_map: fx.localMapPanel(),
      },
    }),
  ]);
  expect(result.accepted).toBe(true);
  expect(store.view.phase).toBe("active");
}

function press(key, options = {}) {
  const event = new KeyboardEvent("keydown", { key, cancelable: true, ...options });
  document.dispatchEvent(event);
  return event;
}

describe("window.Elosern bridge", () => {
  it("re-exposes the frozen A1 façade surface on window.Elosern", () => {
    const { facade } = installBridge();
    expect(window.Elosern).toBe(facade);
    expect(Object.keys(facade).sort()).toEqual(
      ["KeyboardRouter", "Protocol", "LayoutStore", "actions", "narrativeInput"].sort(),
    );

    // Protocol = the imported UMD module, byte-identical re-exposure (D1).
    expect(facade.Protocol.PROTOCOL_VERSION).toBe(1);
    expect(typeof facade.Protocol.createStore).toBe("function");
    expect(typeof facade.Protocol.validateSnapshot).toBe("function");
    // LayoutStore = the imported versioned layout-persistence UMD (D1).
    expect(typeof facade.LayoutStore.createStore).toBe("function");

    // KeyboardRouter = the imported UMD module (claim-contract constants).
    expect(typeof facade.KeyboardRouter.createRouter).toBe("function");
    expect(facade.KeyboardRouter.ENTER).toBe("Enter");
    expect(facade.KeyboardRouter.SPACE).toBe(" ");

    // narrativeInput / actions carry exactly the frozen member sets (§1).
    expect(Object.keys(facade.narrativeInput).sort()).toEqual(NARRATIVE_INPUT_MEMBERS.sort());
    expect(Object.keys(facade.actions).sort()).toEqual(ACTIONS_MEMBERS.sort());
    expect(Object.keys(facade.actions.client).sort()).toEqual(ACTIONS_CLIENT_MEMBERS.sort());
  });

  it("routes narrative input through the single store append path", () => {
    const { store, facade } = installBridge();
    openActiveSession(store);

    expect(facade.narrativeInput.appendInput("look")).toBe(true);
    expect(store.narrative).toHaveLength(1);
    expect(store.narrative[0].kind).toBe("in");
    expect(store.commandHistory).toEqual(["look"]);

    // The display-only descriptor never reaches the store's wire payload; a
    // second append adds exactly one line (no duplicated append path).
    expect(facade.narrativeInput.appendInput("look 2", { display: { label: "look2" } })).toBe(true);
    expect(store.narrative).toHaveLength(2);
    expect(store.commandHistory).toEqual(["look", "look 2"]);
  });

  it("mountChoicePoint, replaceChoicePoint, unmountChoicePoint are safe no-ops returning false", () => {
    const { facade } = installBridge();
    expect(facade.narrativeInput.mountChoicePoint({})).toBe(false);
    expect(facade.narrativeInput.replaceChoicePoint({})).toBe(false);
    expect(facade.narrativeInput.unmountChoicePoint()).toBe(false);
  });

  it("exposes exactly one action-dispatch entry, with a one-mutation-in-flight gate", () => {
    const { store, facade } = installBridge();
    openActiveSession(store);
    const sender = fx.createFakeSender();
    store.setSender(sender);

    const id1 = facade.actions.submit("explore.wait", { daypart: "dusk" });
    expect(id1).toBe("session:1");

    // A duplicate submit while the first mutation is in flight dispatches nothing.
    expect(facade.actions.submit("explore.wait", { sleep: true })).toBeNull();
    expect(sender.sent.actions).toHaveLength(1);
    const envelope = sender.sent.actions[0];
    expect(envelope.protocol_version).toBe(1);
    expect(envelope.request_id).toBe(id1);
    expect(envelope.action_id).toBe("explore.wait");
    expect(envelope.payload).toEqual({ daypart: "dusk" });
    expect(envelope.presentation_epoch).toBe(fx.EPOCH_A);
    expect("display" in envelope).toBe(false);

    const client = facade.actions.client;
    expect(client.isInFlight()).toBe(true);
    expect(client.inFlightRequestId()).toBe(id1);

    // The result updates the gate; the presentation update releases it.
    const result = store.receive(1, "ui_action_result", [fx.actionResult()]);
    expect(result.accepted).toBe(true);
    expect(client.isInFlight()).toBe(true);
    expect(client.uncertain()).toBe(false);
    facade.actions.handlePresentation(fx.update({ revision: 2 }));
    expect(client.isInFlight()).toBe(false);
    // The reducer normalizes the wire `request_id` to `requestId` in the
    // committed result.
    expect(client.lastResult().requestId).toBe(id1);

    // A second in-flight request can be completed through the camelCase
    // (reducer-normalized) spelling of the same result shape — the bridge
    // reverse-normalizes it to the wire envelope before the single receive
    // path.
    const id2 = facade.actions.submit("explore.wait", { sleep: true });
    expect(id2).toBe("session:2");
    expect(client.isInFlight()).toBe(true);
    client.onActionResult({
      protocolVersion: 1,
      epoch: store.view.epoch,
      requestId: id2,
      outcome: "success",
      code: "completed",
      message: "完成",
      presentationRevision: 2,
    });
    // The committed revision (2) already reaches the declared presentation
    // revision, so the gate releases inside the same publish
    // (`releaseIfReady` runs on every publish, line 348 of the store).
    expect(client.isInFlight()).toBe(false);
    expect(client.inFlightRequestId()).toBeNull();
    expect(client.lastResult().requestId).toBe(id2);
  });

  it("routes document key events through the router, claimed exactly when consumed", () => {
    const { store, facade } = installBridge();
    openActiveSession(store);

    // Initial focus is the first G2 root item.
    expect(store.view.focus.key).toBe("move");

    // An unclaimed key (a plain letter) is not swallowed by the bridge.
    const unclaimed = press("l");
    expect(unclaimed.defaultPrevented).toBe(false);

    // `/` is consumed by the router (H5, webclient-hud-05-overlays-and-command-line:
    // the command line is permanently present, so `/` moves focus into the
    // always-present field — no toggle state); the bridge claims it and
    // prevents the default so the character never falls through to the text
    // path.
    const slash = press("/");
    expect(slash.defaultPrevented).toBe(true);

    // A consumed key (ArrowRight) moves focus along the G2 single-row root
    // grid (7-column, one row); ArrowDown is a no-op in a single-row grid.
    const right = press("ArrowRight");
    expect(right.defaultPrevented).toBe(true);
    expect(store.view.focus.key).toBe("look");
    expect(store.view.focus.enabled).toBe(true);

    // A second ArrowRight reaches "interact"; a plain letter is left unclaimed.
    press("ArrowRight");
    expect(store.view.focus.key).toBe("interact");
    const unclaimed2 = press("m");
    expect(unclaimed2.defaultPrevented).toBe(false);

    // The "character" root entry re-homes the character sub-dock (a local
    // surface intent, no `ui_action` dispatched).
    press("ArrowRight");
    expect(store.view.focus.key).toBe("character");
    const enterChar = press("Enter");
    expect(enterChar.defaultPrevented).toBe(true);
    expect(store.view.activeSubDock).toBe("character");

    // Escape leaves the character sub-dock and re-homes the exploration root.
    const escape = press("Escape");
    expect(escape.defaultPrevented).toBe(true);
    expect(store.view.activeSubDock).toBe(null);
    expect(store.view.focus.key).toBe("move");
  });

  it("lets editable controls keep their keys", () => {
    const { facade } = installBridge();
    const field = document.createElement("input");
    document.body.appendChild(field);
    const event = new KeyboardEvent("keydown", { key: "/", cancelable: true });
    Object.defineProperty(event, "target", { value: field });
    document.dispatchEvent(event);
    // The open drawer field (or a form) owns its keys: the bridge does not
    // claim them, so a literal `/` stays typeable.
    expect(event.defaultPrevented).toBe(false);
    document.body.removeChild(field);
  });
});
