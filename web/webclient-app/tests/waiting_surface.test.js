// align-webclient-waiting-practice-specs, migrated by exploration-room-actions
// and redesign-rest-entry: the waiting surface's three operations in two
// layers (webclient-exploration-menu). The place card's 休息 opens the rest
// entry's first layer — the 等待 and 睡眠 tiles and a close control, no rows —
// and each tile opens its form: 等待 the dawn wait and the custom-duration
// wait, 睡眠 the recovery and explicit-duration sleep. The hours form converts
// to whole seconds exactly once and dispatches `explore.wait` with them,
// out-of-bounds hours never dispatch, and an in-flight action locks the tiles
// without submitting.
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import AppClient from "../AppClient.vue";
import { useElosernStore } from "../stores/elosern.js";
import * as fx from "./store/protocol_fixtures.js";

describe("waiting surface (the rest entry: three operations in two layers)", () => {
  let store;
  let wrapper;
  let sender;

  async function settle() {
    for (let i = 0; i < 4; i += 1) {
      await nextTick();
    }
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
            local_map: fx.localMapPanel(),
            context_actions: fx.explorationActions(),
          },
        }),
      ],
      {},
    );
    expect(result.accepted).toBe(true);
  }

  const waitCard = () => wrapper.find('[data-anchor="choices"] [data-testid="wait-card"]');
  const tiles = () => waitCard().findAll('[data-testid="wait-card-tile"]');
  const tile = (key) => wrapper.get(`[data-anchor="choices"] [data-testid="wait-card-tile"][data-tile="${key}"]`);
  const waitForm = () => wrapper.find('[data-anchor="choices"] [data-testid="wait-form"]');
  const sleepForm = () => wrapper.find('[data-anchor="choices"] [data-testid="sleep-form"]');

  function key(element, name) {
    element.dispatchEvent(new KeyboardEvent("keydown", { key: name, bubbles: true, cancelable: true }));
  }

  async function back() {
    await wrapper.get('[data-testid="rest-step-back"]').trigger("click");
    await settle();
  }

  beforeEach(async () => {
    setActivePinia(createPinia());
    store = useElosernStore();
    sender = fx.createFakeSender();
    store.setSender(sender);
    wrapper = mount(AppClient, { attachTo: document.body });
    commitPanels();
    await settle();
    await wrapper.get('[data-anchor="map"] [data-testid="place-card-wait"]').trigger("click");
    await settle();
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  it("the first layer offers exactly the 等待 and 睡眠 tiles and a close control, and no row", () => {
    expect(waitCard().exists()).toBe(true);
    expect(tiles().map((t) => t.get(".time-choice__label").text())).toEqual(["等待", "睡眠"]);
    expect(waitCard().find('[data-testid="wait-card-close"]').exists()).toBe(true);
    expect(waitCard().findAll('[role="menuitem"]')).toHaveLength(0);
    expect(waitCard().text()).not.toMatch("午夜");
    expect(waitCard().text()).not.toMatch("正午");
    expect(waitCard().text()).not.toMatch("夢境");
    // No fourth quiet-rest choice or stance.
    expect(waitCard().text()).not.toMatch("靜養");
    expect(waitCard().text()).not.toMatch("調息");
    // Opening the entry sent nothing.
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("等待 leads to the dawn wait and the duration form; 睡眠 to recovery and the duration form", async () => {
    await tile("wait").trigger("click");
    await settle();
    expect(waitForm().get('[data-testid="wait-form-dawn"]').text()).toBe("等待直到黎明");
    expect(waitForm().find('input[type="number"]').exists()).toBe(true);
    expect(waitForm().get('button[type="submit"]').text()).toBe("等待此時長");
    // Every layer has a visible way back or out.
    expect(wrapper.find('[data-testid="rest-step-back"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="rest-step-close"]').exists()).toBe(true);
    await back();
    await tile("sleep").trigger("click");
    await settle();
    expect(sleepForm().get('[data-testid="sleep-form-recovery"]').text()).toBe("睡眠至完全恢復");
    expect(sleepForm().find('input[type="number"]').exists()).toBe(true);
    expect(sleepForm().get('button[type="submit"]').text()).toBe("以此時長入睡");
    expect(wrapper.find('[data-anchor="choices"]').text()).not.toMatch("夢境");
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("converts fractional hours to whole seconds and dispatches explore.wait exactly once", async () => {
    await tile("wait").trigger("click");
    await settle();
    expect(sender.sent.actions).toHaveLength(0);
    await waitForm().get('input[type="number"]').setValue("1.5");
    await waitForm().trigger("submit");
    await settle();
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({
      action_id: "explore.wait",
      payload: { seconds: 5400 },
    });
    // The form and the entry close; no client-side world time is claimed.
    expect(waitForm().exists()).toBe(false);
    expect(waitCard().exists()).toBe(false);
    expect(wrapper.text()).not.toMatch("1.5 小時後");
  });

  it("rejects out-of-bounds hours without dispatching and stays open for correction", async () => {
    await tile("wait").trigger("click");
    await settle();
    const form = waitForm();
    await form.get('input[type="number"]').setValue("12.01");
    await form.trigger("submit");
    expect(sender.sent.actions.length).toBe(0);
    expect(form.get('[role="alert"]').text()).toBe("請輸入有效時長，最短 1 秒、最長 12 小時。");
    expect(waitForm().exists()).toBe(true);
    expect(form.get('input[type="number"]').attributes("disabled")).toBeUndefined();
    await form.get('input[type="number"]').setValue("");
    await form.trigger("submit");
    expect(sender.sent.actions.length).toBe(0);
  });

  it("an in-flight action locks both tiles, states the reason, and opens or submits nothing", async () => {
    // Another action is in flight (the place card's 查看房間).
    expect(store.activateRoomLook()).toMatchObject({ sent: true });
    expect(store.view.dispatch.inFlight).not.toBeNull();
    await settle();
    const status = waitCard().get('[role="status"]');
    expect(status.text()).toBe("上一個行動尚未完成，請稍候。");
    for (const t of tiles()) {
      expect(t.attributes("aria-disabled")).toBe("true");
      expect(t.attributes("aria-describedby")).toContain(status.attributes("id"));
      await t.trigger("click");
    }
    for (const digit of ["1", "2"]) {
      key(tile("wait").element, digit);
    }
    await settle();
    expect(sender.sent.actions).toHaveLength(1);
    expect(waitForm().exists()).toBe(false);
    expect(sleepForm().exists()).toBe(false);
    expect(wrapper.find('[data-testid="dream-question"]').exists()).toBe(false);
  });

  it("every tile, form control, and corner button is focusable", async () => {
    const focusable = (el) => {
      el.focus();
      return document.activeElement === el;
    };
    for (const t of tiles()) {
      expect(focusable(t.element)).toBe(true);
    }
    expect(focusable(waitCard().get('[data-testid="wait-card-close"]').element)).toBe(true);
    for (const which of ["wait", "sleep"]) {
      await tile(which).trigger("click");
      await settle();
      const shell = wrapper.get(`[data-testid="${which === "wait" ? "wait-form-card" : "sleep-card"}"]`);
      for (const el of shell.element.querySelectorAll("button, input")) {
        expect(focusable(el)).toBe(true);
      }
      await back();
    }
  });
});
