// align-webclient-waiting-practice-specs, migrated by exploration-room-actions:
// the waiting surface's three-operation contract (webclient-exploration-menu).
// The place card's 等待 opens the centred wait card, which renders exactly the
// dawn, sleep, and custom-rest rows (plus the trailing `✕ 返回`); the hours
// form converts to whole seconds exactly once and dispatches `explore.wait`
// with them, out-of-bounds hours never dispatch, and an in-flight action
// disables every wait row without submitting.
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import AppClient from "../AppClient.vue";
import { useElosernStore } from "../stores/elosern.js";
import * as fx from "./store/protocol_fixtures.js";

describe("waiting surface (the wait card: three operations, hours form)", () => {
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
  const rows = () => waitCard().findAll('[role="menuitem"]');

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

  it("renders exactly the three operations plus the back row, the active row marked", () => {
    expect(waitCard().exists()).toBe(true);
    expect(rows().map((row) => row.text().replace(/^\d/, ""))).toEqual([
      "等待直到黎明",
      "睡眠至完全恢復",
      "休息 N 小時",
      "返回",
    ]);
    expect(waitCard().text()).not.toMatch("午夜");
    expect(waitCard().text()).not.toMatch("正午");
    expect(waitCard().text()).not.toMatch("夢境");
    // Exactly one row carries the active-row treatment, and it is the row
    // `aria-activedescendant` names.
    const active = rows().filter((row) => row.attributes("data-active") === "true");
    expect(active).toHaveLength(1);
    expect(waitCard().attributes("aria-activedescendant")).toBe(active[0].attributes("id"));
    // Opening the card sent nothing.
    expect(sender.sent.actions).toHaveLength(0);
  });

  it("converts fractional hours to whole seconds and dispatches explore.wait exactly once", async () => {
    await rows()[2].trigger("click");
    await settle();
    const form = wrapper.get('[data-anchor="choices"] [data-testid="exploration-rest-form"]');
    expect(sender.sent.actions).toHaveLength(0);
    await form.get('input[type="number"]').setValue("1.5");
    await form.trigger("submit");
    await settle();
    expect(sender.sent.actions).toHaveLength(1);
    expect(sender.sent.actions[0]).toMatchObject({
      action_id: "explore.wait",
      payload: { seconds: 5400 },
    });
    // The form and the card close; no client-side world time is claimed.
    expect(wrapper.find('[data-testid="exploration-rest-form"]').exists()).toBe(false);
    expect(waitCard().exists()).toBe(false);
    expect(wrapper.text()).not.toMatch("1.5 小時後");
  });

  it("rejects out-of-bounds hours without dispatching and stays open for correction", async () => {
    await rows()[2].trigger("click");
    await settle();
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

  it("an in-flight action disables every wait row and submits nothing", async () => {
    // Another action is in flight (the place card's 查看房間).
    expect(store.activateRoomLook()).toMatchObject({ sent: true });
    expect(store.view.dispatch.inFlight).not.toBeNull();
    await settle();
    const waitRows = rows().slice(0, 3);
    for (const row of waitRows) {
      expect(row.attributes("aria-disabled")).toBe("true");
      expect(row.text()).toContain("上一個行動尚未完成");
      await row.trigger("click");
    }
    const card = waitCard().element;
    card.focus();
    for (const digit of ["1", "2", "3"]) {
      card.dispatchEvent(new KeyboardEvent("keydown", { key: digit, bubbles: true, cancelable: true }));
    }
    await settle();
    expect(sender.sent.actions).toHaveLength(1);
    expect(wrapper.find('[data-testid="dream-question"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="exploration-rest-form"]').exists()).toBe(false);
  });
});
