// C4 (webclient-vue-10-wire-views-browser): the Vue renderer auto-requests
// exactly one `ui_sync` per failure episode in either "renderer cannot render"
// case: (1) a locally-rejected malformed `ui_snapshot` / `ui_update` (the
// store records it in `lastPanelRejection`), or (2) a recoverable
// `ui_protocol_error` committed by the server. The bridge's guard blocks a
// second request in the same transport generation; a cleared rejection or a
// cleared protocol error (reconnect / fresh snapshot) re-arms the episode.
// This check drives the lifecycle through the store's public API
// (`beginTransport` / `setConnected` / `receive`) so the signals reach the
// view the way the real transport would set them.

import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import AppClient from "../AppClient.vue";
import { createWindowBridge } from "../bridge.js";
import { useElosernStore } from "../stores/elosern.js";
import * as fx from "./store/protocol_fixtures.js";

describe("AppClient auto-resync (C4 one-sync-per-episode)", () => {
  let store;
  let bridgeHandle;
  let reqSpy;
  let resetSpy;

  function mountAppClient() {
    const host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    return mount(AppClient, { attachTo: host });
  }

  function connect() {
    store.beginTransport(1);
    store.setConnected(true);
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    bridgeHandle = createWindowBridge(store);
    reqSpy = vi.spyOn(window.Elosern.actions, "requestResync");
    resetSpy = vi.spyOn(window.Elosern.actions, "resetResyncEpisode");
  });

  afterEach(() => {
    if (bridgeHandle) {
      bridgeHandle.uninstall();
    }
    vi.restoreAllMocks();
    document.body.innerHTML = "";
  });

  it("auto-requests one ui_sync when a malformed ui_snapshot is rejected", async () => {
    const wrapper = mountAppClient();
    await wrapper.vm.$nextTick();

    connect();
    // An unknown panel name rejects the whole presentation (the reducer's
    // exact-field / allowlist validation). The store records the rejection.
    const rejected = store.receive(1, "ui_snapshot", [fx.snapshot({ panels: { bogus_panel: {} } })]);
    expect(rejected.accepted).toBe(false);
    await wrapper.vm.$nextTick();

    // The renderer just could not render the presentation: exactly one
    // ui_sync is requested for the failure episode.
    expect(reqSpy).toHaveBeenCalledTimes(1);
    expect(reqSpy).toHaveBeenCalledWith("presentation");

    wrapper.unmount();
  });

  it("re-arms the resync episode when a fresh valid snapshot is accepted", async () => {
    const wrapper = mountAppClient();
    await wrapper.vm.$nextTick();

    connect();
    store.receive(1, "ui_snapshot", [fx.snapshot({ panels: { bogus_panel: {} } })]);
    await wrapper.vm.$nextTick();
    expect(reqSpy).toHaveBeenCalledTimes(1);

    // A valid snapshot is accepted: the rejection clears, re-arming the
    // one-sync-per-episode guard.
    const accepted = store.receive(1, "ui_snapshot", [fx.snapshot()]);
    expect(accepted.accepted).toBe(true);
    await wrapper.vm.$nextTick();

    expect(resetSpy).toHaveBeenCalledTimes(1);
    expect(resetSpy).toHaveBeenCalledWith("presentation");

    wrapper.unmount();
  });

  it("auto-requests a ui_sync for a recoverable server protocol error", async () => {
    const wrapper = mountAppClient();
    await wrapper.vm.$nextTick();

    connect();
    // `no_puppet` is recoverable (the player left the character); a fresh
    // sync can recover the presentation.
    const res = store.receive(1, "ui_protocol_error", [fx.protocolError({ code: "no_puppet" })]);
    expect(res.accepted).toBe(true);
    await wrapper.vm.$nextTick();
    expect(reqSpy).toHaveBeenCalledTimes(1);
    expect(reqSpy).toHaveBeenCalledWith("presentation");

    wrapper.unmount();
  });

  it("does NOT resync a non-recoverable protocol error (version mismatch)", async () => {
    const wrapper = mountAppClient();
    await wrapper.vm.$nextTick();

    connect();
    // `unsupported_version` cannot be fixed by a fresh sync: the graphical
    // controls stay locked and the text fallback carries the game.
    const res = store.receive(1, "ui_protocol_error", [fx.protocolError({ code: "unsupported_version" })]);
    expect(res.accepted).toBe(true);
    await wrapper.vm.$nextTick();

    expect(reqSpy).not.toHaveBeenCalled();

    wrapper.unmount();
  });

  it("a new transport generation re-arms the resync episode", async () => {
    const wrapper = mountAppClient();
    await wrapper.vm.$nextTick();

    connect(); // beginTransport(1) + setConnected(true)
    // Generation 1: a malformed snapshot is rejected → one ui_sync.
    store.receive(1, "ui_snapshot", [fx.snapshot({ panels: { bogus_panel: {} } })]);
    await wrapper.vm.$nextTick();
    expect(reqSpy).toHaveBeenCalledTimes(1);

    // Reconnect bumps the transport generation: the store clears the
    // rejection signal, re-arming the one-sync-per-episode guard.
    store.beginTransport(2);
    await wrapper.vm.$nextTick();
    expect(resetSpy).toHaveBeenCalled();

    // Generation 2: the next malformed snapshot is rejected again → the
    // fresh episode requests one ui_sync (the second request).
    const res2 = store.receive(2, "ui_snapshot", [fx.snapshot({ panels: { bogus_panel: {} } })]);
    expect(res2.accepted).toBe(false);
    await wrapper.vm.$nextTick();
    expect(reqSpy).toHaveBeenCalledTimes(2);

    wrapper.unmount();
  });

  it("auto-requests a ui_sync for a missing-envelope transport corruption", async () => {
    const wrapper = mountAppClient();
    await wrapper.vm.$nextTick();

    connect();
    // A presentation message with no envelope argument is a transport
    // corruption (`reason === "missing_envelope"); the store records it in
    // lastPanelRejection, so the renderer requests one ui_sync.
    const res = store.receive(1, "ui_snapshot", []);
    expect(res.accepted).toBe(false);
    expect(res.reason).toBe("missing_envelope");
    await wrapper.vm.$nextTick();
    expect(reqSpy).toHaveBeenCalledTimes(1);
    expect(reqSpy).toHaveBeenCalledWith("presentation");

    wrapper.unmount();
  });
});
