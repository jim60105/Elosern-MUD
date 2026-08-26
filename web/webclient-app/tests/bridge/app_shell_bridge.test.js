// C2 (webclient-vue-08-wire-bridge-contracts): the browser-bridge and the
// AppShell key handlers coexist safely. The bridge (document listener)
// claims the keys consumed by the keyboard router; the shell's window
// handler (H5, webclient-hud-05-overlays-and-command-line) claims `/` only
// when the target is not editable — the command line is permanently
// present, so `/` moves focus into the always-present field (no open/closed
// state to toggle). One keypress must act exactly once — no double
// activation.
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import AppClient from "../../AppClient.vue";
import { createWindowBridge } from "../../bridge.js";
import { useElosernStore } from "../../stores/elosern.js";
import * as fx from "../store/protocol_fixtures.js";

let wrapper;
let bridge;

function dispatchWindowKey(key) {
  // Dispatch on `document` (bubbling) so BOTH the bridge's document listener
  // (`createWindowBridge` -> `installKeyRouting`) and the shell's window
  // listener receive the keypress — the real coexistence path the contract
  // guards.
  document.dispatchEvent(
    new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true }),
  );
}

function mountAll() {
  const host = document.createElement("div");
  host.id = "elosern-app";
  document.body.appendChild(host);
  // Mount the full `AppClient` (the complete view-layer wiring, which includes
  // the `watch(drawerRequest) -> focusCommandField` route) rather than a bare
  // `AppShell`, so the real keypress -> store -> watcher -> focus flow is
  // exercised end-to-end.
  setActivePinia(createPinia());
  const store = useElosernStore();
  wrapper = mount(AppClient, { attachTo: host });
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
  it("`/` focuses the always-present command field exactly once per press", async () => {
    const store = mountAll();
    openActiveSession(store);

    // Press 1: the shell's window handler claims `/` (the target, `body`,
    // is not editable) and focuses the command field.
    dispatchWindowKey("/");
    await wrapper.vm.$nextTick();
    const input = wrapper.get("textarea#inputfield");
    expect(document.activeElement).toBe(input.element);

    // Press 2: the claim is idempotent (no open/closed state — the command
    // line is permanently present, design D1).
    dispatchWindowKey("/");
    await wrapper.vm.$nextTick();
    expect(document.activeElement).toBe(input.element);
  });

  it("keeps the command field owning its `/` (literal slash, no double claim)", async () => {
    const store = mountAll();
    openActiveSession(store);

    dispatchWindowKey("/");
    await wrapper.vm.$nextTick();
    let input = wrapper.get("textarea#inputfield");
    expect(document.activeElement).toBe(input.element);

    // A `/` typed into the focused field stays literal text: the bridge's
    // editable guard skips it and the shell's `!isEditable(target)` guard
    // skips it too — the field keeps the typed slash (design D2).
    const event = new KeyboardEvent("keydown", { key: "/", cancelable: true });
    input.element.dispatchEvent(event);
    input.element.value = "/";
    input.element.dispatchEvent(new Event("input", { bubbles: true }));
    await wrapper.vm.$nextTick();
    expect(input.element.value).toBe("/");
    expect(event.defaultPrevented).toBe(false);
    expect(document.activeElement).toBe(input.element);
  });

  it("Escape from the focused field returns focus to the dock; the menu depth is unchanged", async () => {
    const store = mountAll();
    openActiveSession(store);

    // Navigate the router into a submenu (depth 2) so the dock's menu level
    // state is non-trivial. H4 re-homed "character" into a reference drawer
    // (no router push); "move" is the root entry that opens a real submenu.
    store.focusItemByKey("move");
    store.focusConfirm();
    await wrapper.vm.$nextTick();
    expect(store.view.dockDepth).toBe(2);

    // `/` focuses the always-present field.
    dispatchWindowKey("/");
    await wrapper.vm.$nextTick();
    const input = wrapper.get("textarea#inputfield");
    expect(document.activeElement).toBe(input.element);

    // The field's own handler owns Escape (ladder rung 3): nothing is sent,
    // focus returns to `#action-dock`, and the dock's menu depth is
    // unchanged (the dock's menu level is rung 4 and is only reached when
    // the field does not hold focus).
    const event = new KeyboardEvent("keydown", { key: "Escape", cancelable: true });
    input.element.dispatchEvent(event);
    await wrapper.vm.$nextTick();
    expect(event.defaultPrevented).toBe(true);
    expect(document.activeElement).toBe(document.getElementById("action-dock"));
    expect(store.view.dockDepth).toBe(2, "the dock's menu level is untouched by the field's Escape");
  });

  it("ArrowDown on the single-row exploration root is a no-op move but still suppresses the default", async () => {
    const store = mountAll();
    openActiveSession(store);

    // After the snapshot, the router re-homes to the exploration root — a
    // single-row tab bar (`gridCols == items.length` → `rows == 1`), so a
    // vertical press is a no-op (unconsumed). Direction keys are always
    // claimed: even a no-op arrow press still suppresses the browser's default
    // page-scroll (G2 exploration root).
    const event = new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true, cancelable: true });
    document.dispatchEvent(event);
    await wrapper.vm.$nextTick();
    expect(event.defaultPrevented).toBe(true, "a no-op direction press is still claimed (preventDefault)");
  });
});
