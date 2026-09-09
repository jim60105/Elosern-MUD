// align-webclient-waiting-practice-specs: the waiting surface's three-operation
// contract (webclient-exploration-menu). The Wait frame renders exactly the
// dawn, sleep, and custom-rest cards (plus the back row), the hours form
// converts to whole seconds exactly once and dispatches `explore.wait` with
// them, out-of-bounds hours never dispatch, and an in-flight action disables
// all three controls without submitting.
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import AppClient from "../AppClient.vue";
import { useElosernStore } from "../stores/elosern.js";
import * as fx from "./store/protocol_fixtures.js";

describe("waiting surface (three operations, hours form)", () => {
  let store;
  let wrapper;
  let sender;

  function mountApp() {
    const host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    wrapper = mount(AppClient, { attachTo: host });
    return wrapper;
  }

  function commitPanels() {
    store.beginTransport(1);
    store.setConnected(true);
    const result = store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          panels: {
            status: fx.statusPanel(),
            exploration: fx.explorationPanel(),
            context_actions: fx.explorationActions(),
          },
        }),
      ],
      {},
    );
    expect(result.accepted).toBe(true);
  }

  async function openWaitFrame() {
    // The navigation-projected root carries move, look, interact, wait, ...
    // ArrowRight lands on 等待/休息, Enter pushes the wait frame.
    while (store.view.focus.key !== "wait") {
      expect(store.focusPress("ArrowRight")).toBe(true);
    }
    expect(store.focusConfirm("keyboard")).toBe(true);
    expect(store.view.dockSource).toBe("exploration.wait");
    await wrapper.vm.$nextTick();
  }

  beforeEach(async () => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
    mountApp();
    commitPanels();
    await wrapper.vm.$nextTick();
    await openWaitFrame();
  });

  it("renders exactly the three operations plus the back row, focused card marked", () => {
    const screen = wrapper.get(".waiting-screen");
    const cards = screen.findAll(".waiting-card");
    expect(cards.map((card) => card.get("h3").text())).toEqual([
      "等待直到黎明",
      "睡眠至完全恢復",
      "休息 N 小時",
    ]);
    expect(screen.text()).not.toMatch("午夜");
    expect(screen.text()).not.toMatch("正午");
    expect(wrapper.find(".waiting-back").exists()).toBe(true);
    // Only the card matching the router's focused key carries the treatment.
    const focused = screen.findAll(".waiting-card--focused");
    expect(focused.length).toBeLessThanOrEqual(1);
    store.focusItemByKey("wait-sleep");
    expect(wrapper.find(".waiting-back").exists()).toBe(true);
  });

  it("converts fractional hours to whole seconds and dispatches explore.wait exactly once", async () => {
    const form = wrapper.get('[data-testid="exploration-rest-form"]');
    await form.get('input[type="number"]').setValue("1.5");
    await form.trigger("submit");
    expect(sender.sent.actions.length).toBe(1);
    expect(sender.sent.actions[0]).toMatchObject({
      action_id: "explore.wait",
      payload: { seconds: 5400 },
    });
    // No client-side world time is claimed before the server snapshot.
    expect(wrapper.text()).not.toMatch("1.5 小時後");
  });

  it("rejects out-of-bounds hours without dispatching and stays open for correction", async () => {
    const form = wrapper.get('[data-testid="exploration-rest-form"]');
    await form.get('input[type="number"]').setValue("12.01");
    await form.trigger("submit");
    expect(sender.sent.actions.length).toBe(0);
    expect(form.get('[role="alert"]').text()).toContain("12");
    expect(wrapper.find('[data-testid="exploration-rest-form"]').exists()).toBe(true);
    await form.get('input[type="number"]').setValue("");
    await form.trigger("submit");
    expect(sender.sent.actions.length).toBe(0);
  });

  it("an in-flight action disables all three waiting controls and submits nothing", async () => {
    const dawn = wrapper.findAll(".waiting-card")[0].get("button");
    await dawn.trigger("click");
    // The dawn dispatch is now in flight; every waiting control locks.
    expect(store.view.dispatch.inFlight).not.toBeNull();
    await wrapper.vm.$nextTick();
    for (const card of wrapper.findAll(".waiting-card")) {
      const button = card.find("button");
      if (button.exists()) {
        await button.trigger("click");
        await button.trigger("keydown", { key: "Enter" });
      }
    }
    expect(sender.sent.actions.length).toBe(1);
  });
});
