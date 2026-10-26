// C4 (webclient-vue-10-wire-views-browser) + webclient-sync-recovery: the
// renderer's automatic complete repair.
//
// The reducer records one failure episode for every failure source (exact-base
// mismatch, invalid/incomplete publication, assembly failure, recoverable
// server error, and a matching result claiming a revision this client never
// adopted). This suite drives the real chain — reducer, Pinia store, window
// bridge, AppClient's `useResync` — and asserts the bounded contract: exactly
// one automatic `ui_sync` per episode across simultaneous failures, committed
// data preserved, graphical mutations locked, no automatic retry after a failed
// repair, one further attempt for the player's own explicit synchronize, and a
// valid complete snapshot as the one repair that replaces everything and
// unlocks.
//
// The final block is the real smoke run: the live evennia.js seam
// (`wireTransport`) with a fake socket, the real store and the mounted
// application, covering the whole episode end to end under fake timers.

import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import AppClient from "../AppClient.vue";
import { createWindowBridge } from "../bridge.js";
import { wireTransport } from "../transport.js";
import { useElosernStore } from "../stores/elosern.js";
import * as fx from "./store/protocol_fixtures.js";

function makeFakeEvennia() {
  const listeners = {};
  const sent = [];
  const evennia = {
    _connected: true,
    emitter: {
      // Single listener per name (the evennia.js DefaultEmitter contract).
      on(name, fn) {
        listeners[name] = fn;
      },
    },
    msg(name, args, kwargs) {
      sent.push([name, args || [], kwargs || {}]);
    },
    isConnected() {
      return evennia._connected;
    },
  };
  function emit(name, args, kwargs) {
    if (listeners[name]) {
      listeners[name](args, kwargs);
    }
  }
  return { evennia, listeners, sent, emit };
}

const BOGUS = { panels: { bogus_panel: {} } };

function mountAppClient() {
  const host = document.createElement("div");
  host.id = "elosern-app";
  document.body.appendChild(host);
  return mount(AppClient, { attachTo: host });
}

describe("bounded complete recovery (webclient-sync-recovery)", () => {
  let store;
  let sender;
  let bridgeHandle;
  let wrapper;

  function connect(panels = { status: fx.statusPanel(), exploration: fx.explorationPanel() }) {
    store.beginTransport(1);
    store.setConnected(true);
    const result = store.receive(1, "ui_snapshot", [fx.snapshot({ panels })], {});
    expect(result.accepted).toBe(true);
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
    bridgeHandle = createWindowBridge(store);
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
      wrapper = null;
    }
    if (bridgeHandle) {
      bridgeHandle.uninstall();
      bridgeHandle = null;
    }
    window.Elosern = undefined;
    vi.useRealTimers();
    document.body.innerHTML = "";
  });

  it("sends one ui_sync for simultaneous failures and keeps the committed presentation", async () => {
    wrapper = mountAppClient();
    await wrapper.vm.$nextTick();
    connect();
    const before = store.view;
    expect(sender.sent.syncs).toBe(0);

    // Two different failure sources in the same task, before the renderer runs.
    expect(store.receive(1, "ui_update", [fx.update({ revision: 3, base_revision: 2, panels: {} })], {}).reason).toBe("base_mismatch");
    expect(store.receive(1, "ui_snapshot", [fx.snapshot({ revision: 2, ...BOGUS })], {}).reason).toBe("invalid");
    await wrapper.vm.$nextTick();

    expect(sender.sent.syncs).toBe(1);
    const after = store.view;
    expect(after.recovery.status).toBe("requested");
    expect(after.mutationsLocked).toBe(true);
    // The last complete presentation is untouched, not erased.
    expect(after.panels).toEqual(before.panels);
    expect(after.revision).toBe(before.revision);
  });

  it("keeps the episode failed and locked without another automatic sync", async () => {
    wrapper = mountAppClient();
    await wrapper.vm.$nextTick();
    connect();
    store.receive(1, "ui_update", [fx.update({ revision: 3, base_revision: 2, panels: {} })], {});
    await wrapper.vm.$nextTick();
    expect(sender.sent.syncs).toBe(1);

    // The repair response itself cannot be rendered: the episode is spent.
    store.receive(1, "ui_snapshot", [fx.snapshot({ revision: 2, ...BOGUS })], {});
    await wrapper.vm.$nextTick();
    expect(store.view.recovery.status).toBe("failed");
    expect(store.view.mutationsLocked).toBe(true);

    // Repeated parts, deltas, results and the renderer's own signal send
    // nothing further.
    for (let index = 0; index < 3; index += 1) {
      store.receive(1, "ui_snapshot", [fx.snapshot({ revision: 3 + index, ...BOGUS })], {});
      store.receive(1, "ui_update", [fx.update({ revision: 4 + index, base_revision: 1, panels: {} })], {});
      store.receive(1, "ui_action_result", [fx.actionResult({ presentation_revision: 30 })], {});
      window.Elosern.actions.requestResync("presentation");
      await wrapper.vm.$nextTick();
    }
    expect(sender.sent.syncs).toBe(1);
    expect(store.view.recovery.status).toBe("failed");
    expect(store.view.mutationsLocked).toBe(true);
  });

  it("a valid complete snapshot repairs everything and unlocks", async () => {
    wrapper = mountAppClient();
    await wrapper.vm.$nextTick();
    connect();
    store.receive(1, "ui_update", [fx.update({ revision: 3, base_revision: 2, panels: {} })], {});
    await wrapper.vm.$nextTick();
    store.receive(1, "ui_snapshot", [fx.snapshot({ revision: 2, ...BOGUS })], {});
    await wrapper.vm.$nextTick();
    expect(store.view.recovery.status).toBe("failed");

    const repaired = store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          revision: 3,
          panels: { status: fx.statusPanel({ disguise_active: true }) },
        }),
      ],
      {},
    );
    await wrapper.vm.$nextTick();
    expect(repaired.accepted).toBe(true);
    expect(store.view.recovery.status).toBe("idle");
    expect(store.view.mutationsLocked).toBe(false);
    // The complete snapshot owns the whole eager set: the omitted exploration
    // panel is gone and the named one is replaced.
    expect(Object.keys(store.view.panels)).toEqual(["status"]);
    expect(store.view.panels.status.disguise_active).toBe(true);
    expect(sender.sent.syncs).toBe(1);
  });

  it("the player's explicit synchronize is one further attempt and never resubmits a mutation", async () => {
    wrapper = mountAppClient();
    await wrapper.vm.$nextTick();
    connect();
    store.receive(1, "ui_update", [fx.update({ revision: 3, base_revision: 2, panels: {} })], {});
    await wrapper.vm.$nextTick();
    store.receive(1, "ui_snapshot", [fx.snapshot({ revision: 2, ...BOGUS })], {});
    await wrapper.vm.$nextTick();
    expect(store.view.recovery.status).toBe("failed");
    const dispatched = sender.sent.actions.length;

    window.Elosern.actions.client.sync();
    await wrapper.vm.$nextTick();
    expect(sender.sent.syncs).toBe(2);
    expect(store.view.recovery.status).toBe("requested");
    expect(store.view.mutationsLocked).toBe(true);

    // The automatic path still refuses: one request per episode.
    expect(window.Elosern.actions.requestResync("presentation")).toBe(false);
    expect(sender.sent.syncs).toBe(2);
    // No mutation is ever replayed by recovery.
    expect(sender.sent.actions.length).toBe(dispatched);
  });

  it("a matching result claiming an unadopted revision starts one repair and cannot release the action", async () => {
    wrapper = mountAppClient();
    await wrapper.vm.$nextTick();
    connect();
    const requestId = store.dispatchAction("explore.wait", { daypart: "dusk" });
    expect(requestId).toBe("session:1");
    expect(store.view.dispatch.inFlight).not.toBe(null);
    const committed = store.view.revision;
    const panels = store.view.panels;

    // The result names revision `committed + 1`, which this client never saw.
    const result = fx.actionResult({
      request_id: requestId,
      presentation_revision: committed + 1,
    });
    store.receive(1, "ui_action_result", [result], {});
    await wrapper.vm.$nextTick();

    expect(sender.sent.syncs).toBe(1);
    expect(store.view.recovery.status).toBe("requested");
    expect(store.view.mutationsLocked).toBe(true);
    expect(store.view.dispatch.inFlight).not.toBe(null);
    expect(store.view.revision).toBe(committed);
    expect(store.view.panels).toEqual(panels);

    // Re-delivery of the same result is deduplicated: no second request.
    store.receive(1, "ui_action_result", [result], {});
    await wrapper.vm.$nextTick();
    expect(sender.sent.syncs).toBe(1);

    // The missed publication arriving is the repair: the claim is satisfied,
    // the episode clears, and only then does the matched action release.
    store.receive(
      1,
      "ui_update",
      [fx.update({ revision: committed + 1, base_revision: committed, panels: {} })],
      {},
    );
    await wrapper.vm.$nextTick();
    expect(store.view.recovery.status).toBe("idle");
    expect(store.view.dispatch.inFlight).toBe(null);
    expect(store.view.mutationsLocked).toBe(false);
  });

  it("records the need without sending while disconnected", async () => {
    wrapper = mountAppClient();
    await wrapper.vm.$nextTick();
    connect();
    store.setConnected(false);
    store.receive(1, "ui_snapshot", [fx.snapshot({ revision: 2, ...BOGUS })], {});
    await wrapper.vm.$nextTick();
    expect(store.view.recovery.status).toBe("needed");
    expect(sender.sent.syncs).toBe(0);

    // The reconnect's own lifecycle starts a fresh sequence and the initial
    // snapshot repairs the presentation; no stale request is replayed.
    store.beginTransport(2);
    store.setConnected(true);
    await wrapper.vm.$nextTick();
    expect(store.view.recovery.status).toBe("idle");
    expect(sender.sent.syncs).toBe(0);
    store.receive(
      2,
      "ui_snapshot",
      [fx.snapshot({ presentation_epoch: fx.EPOCH_B, panels: { status: fx.statusPanel() } })],
      {},
    );
    await wrapper.vm.$nextTick();
    expect(store.view.mutationsLocked).toBe(false);
  });

  it("a new transport generation re-arms the episode", async () => {
    wrapper = mountAppClient();
    await wrapper.vm.$nextTick();
    connect();
    store.receive(1, "ui_update", [fx.update({ revision: 3, base_revision: 2, panels: {} })], {});
    await wrapper.vm.$nextTick();
    expect(sender.sent.syncs).toBe(1);
    store.beginTransport(2);
    await wrapper.vm.$nextTick();
    expect(store.view.recovery.status).toBe("idle");
    store.setConnected(true);
    store.receive(
      2,
      "ui_snapshot",
      [fx.snapshot({ presentation_epoch: fx.EPOCH_B, panels: { status: fx.statusPanel() } })],
      {},
    );
    await wrapper.vm.$nextTick();
    store.receive(2, "ui_update", [fx.update({ presentation_epoch: fx.EPOCH_B, revision: 2, base_revision: 9, panels: {} })], {});
    await wrapper.vm.$nextTick();
    expect(sender.sent.syncs).toBe(2);
    expect(store.view.recovery.status).toBe("requested");
  });
});

describe("complete recovery smoke run (live transport seam)", () => {
  let store;
  let fake;
  let bridgeHandle;
  let wrapper;

  function syncs() {
    return fake.sent.filter((message) => message[0] === "ui_sync").length;
  }

  beforeEach(() => {
    vi.useFakeTimers();
    setActivePinia(createPinia());
    store = useElosernStore();
    fake = makeFakeEvennia();
    window.Evennia = fake.evennia;
    expect(wireTransport(store, null)).toBe(true);
    bridgeHandle = createWindowBridge(store);
    wrapper = mountAppClient();
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
      wrapper = null;
    }
    if (bridgeHandle) {
      bridgeHandle.uninstall();
      bridgeHandle = null;
    }
    window.Elosern = undefined;
    vi.useRealTimers();
    document.body.innerHTML = "";
  });

  it("locks, coalesces, stays locked past the deadline and repairs in one snapshot", async () => {
    // A live socket: one initial sync, then the complete baseline.
    fake.emit("connection_open");
    expect(syncs()).toBe(1);
    fake.emit(
      "ui_snapshot",
      [fx.snapshot({ panels: { status: fx.statusPanel(), exploration: fx.explorationPanel() } })],
      {},
    );
    await wrapper.vm.$nextTick();
    expect(store.view.phase).toBe("active");
    expect(store.view.mutationsLocked).toBe(false);
    const panels = store.view.panels;
    const revision = store.view.revision;

    // (1) A base mismatch and an unrenderable snapshot at once: exactly one
    // repair, and the old presentation survives untouched.
    fake.emit("ui_update", [fx.update({ revision: revision + 3, base_revision: revision + 1, panels: {} })], {});
    fake.emit("ui_snapshot", [fx.snapshot({ revision: revision + 1, ...BOGUS })], {});
    await wrapper.vm.$nextTick();
    expect(syncs()).toBe(2);
    expect(store.view.recovery.status).toBe("requested");
    expect(store.view.mutationsLocked).toBe(true);
    expect(store.view.panels).toEqual(panels);
    expect(store.view.revision).toBe(revision);

    // (2) The repair response is unrenderable: failed, locked, and the
    // bounded response deadline passing changes nothing and sends nothing.
    fake.emit("ui_snapshot", [fx.snapshot({ revision: revision + 1, ...BOGUS })], {});
    await wrapper.vm.$nextTick();
    expect(store.view.recovery.status).toBe("failed");
    await vi.advanceTimersByTimeAsync(60000);
    await wrapper.vm.$nextTick();
    expect(syncs()).toBe(2);
    expect(store.view.mutationsLocked).toBe(true);

    // Ordinary text play is never gated by the graphical lock.
    fake.emit("text", ["你環顧四周。"], {});
    expect(store.narrative.some((line) => line.text === "你環顧四周。")).toBe(true);

    // (3) The valid complete repair replaces every eager panel and unlocks.
    fake.emit(
      "ui_snapshot",
      [fx.snapshot({ revision: revision + 2, panels: { status: fx.statusPanel({ disguise_active: true }) } })],
      {},
    );
    await wrapper.vm.$nextTick();
    expect(store.view.recovery.status).toBe("idle");
    expect(store.view.mutationsLocked).toBe(false);
    expect(Object.keys(store.view.panels)).toEqual(["status"]);
    expect(store.view.panels.status.disguise_active).toBe(true);
    expect(syncs()).toBe(2);

    // (4) A fresh episode gets its own single request and a bounded deadline.
    fake.emit("ui_update", [fx.update({ revision: 99, base_revision: 98, panels: {} })], {});
    await wrapper.vm.$nextTick();
    expect(syncs()).toBe(3);
    expect(store.view.recovery.status).toBe("requested");
    await vi.advanceTimersByTimeAsync(29999);
    expect(store.view.recovery.status).toBe("requested");
    expect(store.view.mutationsLocked).toBe(true);
    await vi.advanceTimersByTimeAsync(1);
    expect(store.view.recovery.status).toBe("failed");
    expect(store.view.mutationsLocked).toBe(true);
    await vi.advanceTimersByTimeAsync(60000);
    expect(syncs()).toBe(3);
  });
});
