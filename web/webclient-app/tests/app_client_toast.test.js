// add-action-feedback-toasts (task 2.3): the toast queue mounts at the client
// root above the overlay layer — asserted as a DOM-order contract (the shared
// modal-tier z-index itself is pinned in tests/z_index_scale.test.js; the
// paint-order proof is browser-owned in test_browser_action_feedback.py).
// Driving the store's public push/dismiss API through the mounted AppClient
// also pins the wiring: :toasts binding, @dismiss handler, and the always-
// mounted empty state.

import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import AppClient from "../AppClient.vue";
import { useElosernStore } from "../stores/elosern.js";
import { CREATION_PANEL_SAMPLE } from "../stories/fixtures.js";
import * as fx from "./store/protocol_fixtures.js";

describe("AppClient toast queue mount (webclient-action-feedback D2)", () => {
  let store;
  let host;

  function mountAppClient() {
    host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    return mount(AppClient, { attachTo: host });
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
  });

  afterEach(() => {
    document.body.innerHTML = "";
    host = null;
  });

  it("is always mounted and renders nothing while the queue is empty", async () => {
    const wrapper = mountAppClient();
    await wrapper.vm.$nextTick();
    // Before any session: the queue surface exists (client-local state needs
    // no committed panel) with zero entries.
    const queue = wrapper.find('[data-testid="feedback-toast-queue"]');
    expect(queue.exists()).toBe(true);
    expect(queue.findAll(".toast")).toHaveLength(0);
    wrapper.unmount();
  });

  it("stacks above the creation overlay in DOM order and dismisses through the store", async () => {
    const wrapper = mountAppClient();
    await wrapper.vm.$nextTick();
    store.beginTransport(1);
    store.setConnected(true);
    expect(
      store.receive(1, "ui_snapshot", [fx.snapshot({ panels: { creation: CREATION_PANEL_SAMPLE } })]).accepted,
    ).toBe(true);
    await wrapper.vm.$nextTick();

    const overlay = host.querySelector('[data-testid="creation-overlay"]');
    const queue = host.querySelector('[data-testid="feedback-toast-queue"]');
    expect(overlay).not.toBe(null);
    expect(queue).not.toBe(null);
    // The tie-break contract: the queue is the LAST child of the client root,
    // after every overlay sibling (equal-tier surfaces stack by DOM order).
    expect(overlay.compareDocumentPosition(queue) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(queue.parentElement).toBe(host.querySelector('[data-testid="elosern-client-root"]'));

    // A store push renders through the :toasts binding into the queue.
    const id = store.pushToast({ title: "概念服務目前無法使用，請稍後再試。", tone: "crit" });
    await wrapper.vm.$nextTick();
    const entry = host.querySelector(`[data-testid="feedback-toast-${id}"]`);
    expect(entry).not.toBe(null);
    expect(entry.classList.contains("crit")).toBe(true);
    expect(entry.textContent).toContain("概念服務目前無法使用，請稍後再試。");

    // Click routes through @dismiss to store.dismissToast (the store is the
    // sole writer).
    entry.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await wrapper.vm.$nextTick();
    expect(host.querySelector(`[data-testid="feedback-toast-${id}"]`)).toBe(null);
    expect(store.view.toasts).toEqual([]);
    wrapper.unmount();
  });
});
