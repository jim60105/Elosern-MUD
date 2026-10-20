// webclient-shop-window: the shop window in the running client. It mounts
// under the `shop` drawer key on its own WindowFrame, shares the party
// window's viewed member, selects through `party.view_member {tab: "shop"}`,
// trades through one `shop.buy` / `shop.sell` naming the recipient or seller,
// and states the committed refusal of its own trade (possessed_shop).
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import AppClient from "../AppClient.vue";
import { resetPartyWindowMemory } from "../components/party-window-memory.js";
import { useElosernStore } from "../stores/elosern.js";
import * as fx from "./store/protocol_fixtures.js";
import {
  SHOP_ELLA_ID,
  SHOP_HOLDINGS_POTION,
  SHOP_KAHN_ID,
  SHOP_PARTY_SAMPLE,
  SHOP_SERVICES_SAMPLE,
} from "../stories/fixtures/shop_window_panels.js";

describe("the shop window in AppClient (webclient-shop-window)", () => {
  let store;
  let wrapper;
  let sender;

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    resetPartyWindowMemory();
    sender = fx.createFakeSender();
    store.setSender(sender);
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
    document.body.innerHTML = "";
  });

  async function mountWith(panels) {
    const host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    wrapper = mount(AppClient, { attachTo: host });
    store.beginTransport(1);
    store.setConnected(true);
    store.receive(1, "ui_snapshot", [
      fx.snapshot({ mode: "exploration", panels: { status: fx.statusPanel(), exploration: fx.explorationPanel(), ...panels } }),
    ]);
    store.openHudDrawer("shop");
    await wrapper.vm.$nextTick();
  }

  const sent = (id) => sender.sent.actions.filter((envelope) => envelope.action_id === id);
  const get = (id) => wrapper.get(`[data-testid="${id}"]`);

  it("mounts its own WindowFrame under the shop key, with no generic drawer body", async () => {
    await mountWith({ services: SHOP_SERVICES_SAMPLE, party: SHOP_PARTY_SAMPLE });
    const drawer = wrapper.get('[data-testid="hud-drawer"]');
    expect(drawer.find('[data-testid="window-frame"]').exists()).toBe(true);
    expect(drawer.find('[data-testid="shop-window"]').exists()).toBe(true);
    expect(wrapper.findAll('[data-testid="hud-drawer"]')).toHaveLength(1);
  });

  it("a rail selection and a row selection each send one party.view_member with tab shop", async () => {
    await mountWith({ services: SHOP_SERVICES_SAMPLE, party: SHOP_PARTY_SAMPLE, item_holdings: SHOP_HOLDINGS_POTION });
    await get("shop-rows__row--steel_shortsword").trigger("click");
    expect(sent("party.view_member").map((envelope) => envelope.payload)).toEqual([
      { member_id: SHOP_ELLA_ID, tab: "shop", skill_key: null, item_key: "steel_shortsword" },
    ]);
    // The admitted request shows its row while in flight.
    await wrapper.vm.$nextTick();
    expect(get("shop-window__title").text()).toBe("鋼製短劍");
    store.receive(1, "ui_action_result", [fx.actionResult({ request_id: sent("party.view_member")[0].request_id, presentation_revision: 1 })]);
    await wrapper.vm.$nextTick();
    await get(`member-rail__entry--${SHOP_KAHN_ID}`).trigger("click");
    expect(sent("party.view_member").at(-1).payload).toEqual({
      member_id: SHOP_KAHN_ID,
      tab: "shop",
      skill_key: null,
      item_key: "steel_shortsword",
    });
    expect(get(`member-rail__entry--${SHOP_KAHN_ID}`).attributes("aria-busy")).toBe("true");
  });

  it("buys for the viewed companion and states the committed possessed_shop refusal", async () => {
    await mountWith({ services: SHOP_SERVICES_SAMPLE, party: SHOP_PARTY_SAMPLE, item_holdings: SHOP_HOLDINGS_POTION });
    const input = get("shop-window__quantity");
    input.element.value = "3";
    await input.trigger("input");
    await input.trigger("change");
    await get("action-bar__btn--trade").trigger("click");
    expect(sent("shop.buy").map((envelope) => envelope.payload)).toEqual([
      { item_key: "potion_heal", quantity: 3, recipient_id: SHOP_ELLA_ID },
    ]);
    expect(get("action-bar__btn--trade").attributes("aria-busy")).toBe("true");
    store.receive(1, "ui_action_result", [
      fx.actionResult({
        request_id: sent("shop.buy")[0].request_id,
        outcome: "rejected",
        code: "possessed_shop",
        message: "附身狀態下無法進行交易。",
        presentation_revision: 1,
      }),
    ]);
    await wrapper.vm.$nextTick();
    const reason = get("action-bar__reason");
    expect(reason.text()).toBe("附身狀態下無法進行交易。");
    expect(reason.attributes("data-reason-code")).toBe("possessed_shop");
  });

  it("closes through the drawer close route and leaves no shop surface in the DOM", async () => {
    await mountWith({ services: SHOP_SERVICES_SAMPLE, party: SHOP_PARTY_SAMPLE });
    await get("hud-drawer-close").trigger("click");
    await wrapper.vm.$nextTick();
    expect(store.view.hudDrawer).toBe(null);
    expect(wrapper.find('[data-testid="shop-window"]').exists()).toBe(false);
  });
});
