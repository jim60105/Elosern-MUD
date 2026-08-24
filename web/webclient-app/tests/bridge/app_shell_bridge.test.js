// C2 (webclient-vue-08-wire-bridge-contracts): the browser-bridge and the
// AppShell key handlers coexist safely. The bridge (document listener)
// claims the keys consumed by the keyboard router; the shell (window
// listener) keeps the drawer-open state. One keypress must toggle or act
// exactly once — no double activation.
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import AppShell from "../../components/AppShell.vue";
import { createWindowBridge } from "../../bridge.js";
import { useElosernStore } from "../../stores/elosern.js";
import * as fx from "../store/protocol_fixtures.js";

let wrapper;
let bridge;

function dispatchWindowKey(key) {
  window.dispatchEvent(new KeyboardEvent("keydown", { key, cancelable: true }));
}

function mountAll() {
  const host = document.createElement("div");
  host.id = "elosern-app";
  document.body.appendChild(host);
  wrapper = mount(AppShell, { attachTo: host });
  setActivePinia(createPinia());
  const store = useElosernStore();
  bridge = createWindowBridge(store);
  return store;
}

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

afterEach(() => {
  if (bridge) {
    bridge.uninstall();
    bridge = null;
  }
  wrapper?.unmount();
  wrapper = null;
  document.body.innerHTML = "";
});

describe("bridge + AppShell key-routing coexistence (one effect per keypress)", () => {
  it("toggles the drawer exactly once per `/` press with the bridge installed", async () => {
    const store = mountAll();
    openActiveSession(store);
    const drawer = () => wrapper.get('[data-testid="command-drawer"]');
    expect(drawer().attributes("data-open")).toBe("false");

    // Press 1: the bridge claims `/` (the router's toggle-drawer); the
    // shell's window handler opens the drawer — exactly one toggle.
    dispatchWindowKey("/");
    await wrapper.vm.$nextTick();
    expect(drawer().attributes("data-open")).toBe("true");

    // Press 2: exactly one close.
    dispatchWindowKey("/");
    await wrapper.vm.$nextTick();
    expect(drawer().attributes("data-open")).toBe("false");
  });

  it("keeps the open drawer field owning its `/` (literal slash, no double toggle)", async () => {
    const store = mountAll();
    openActiveSession(store);

    dispatchWindowKey("/");
    await wrapper.vm.$nextTick();
    let input = wrapper.get("textarea#inputfield");
    expect(document.activeElement).toBe(input.element);

    // A `/` typed into the focused field stays literal text: the bridge's
    // editable guard skips it and the shell's `!isEditable(target)` guard
    // skips it too — the drawer stays open.
    const event = new KeyboardEvent("keydown", { key: "/", cancelable: true });
    input.element.dispatchEvent(event);
    input.element.value = "/";
    input.element.dispatchEvent(new Event("input", { bubbles: true }));
    await wrapper.vm.$nextTick();
    expect(input.element.value).toBe("/");
    expect(event.defaultPrevented).toBe(false);
    expect(wrapper.get('[data-testid="command-drawer"]').attributes("data-open")).toBe("true");
    expect(document.activeElement).toBe(input.element);
  });

  it("on Escape closes the open drawer and pops exactly one menu level", async () => {
    const store = mountAll();
    openActiveSession(store);

    // Open the drawer, then move focus back to the narrative feed.
    dispatchWindowKey("/");
    await wrapper.vm.$nextTick();
    wrapper.get('[data-testid="narrative-feed"]').element.focus();

    // The bridge claims Escape through the router (menu pops one level);
    // the shell closes the drawer and restores focus to the feed. Both
    // effects happen exactly once per press.
    const event = new KeyboardEvent("keydown", { key: "Escape", cancelable: true });
    window.dispatchEvent(event);
    await wrapper.vm.$nextTick();
    expect(event.defaultPrevented).toBe(true);
    expect(wrapper.get('[data-testid="command-drawer"]').attributes("data-open")).toBe("false");
    expect(document.activeElement).toBe(wrapper.get('[data-testid="narrative-feed"]').element);
    expect(store.view.focus.key).toBe("move");
  });
});
