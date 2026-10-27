// webclient-shop-window: the shop window in the running client. It mounts
// under the `shop` drawer key on its own WindowFrame, shares the party
// window's viewed member, selects through `party.view_member {tab: "shop"}`,
// trades through one `shop.buy` / `shop.sell` naming the recipient or seller,
// refreshes the committed purse and bag, and states an ordinary refusal.
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
  SHOP_HOLDINGS_SELL,
  SHOP_KAHN_ID,
  SHOP_PARTY_SAMPLE,
  SHOP_PARTY_SELLER_SAMPLE,
  SHOP_SERVICES_SAMPLE,
  SHOP_SERVICES_SELLER_SAMPLE,
} from "../stories/fixtures/shop_window_panels.js";
import { PARTY_BAG_INVENTORY_SAMPLE } from "../stories/fixtures/party_panels.js";

describe("the shop window in AppClient (webclient-shop-window)", () => {
  let store;
  let wrapper;
  let sender;
  let answeredReads;

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
    resetPartyWindowMemory();
    sender = fx.createFakeSender();
    store.setSender(sender);
    answeredReads = new Set();
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
    settleServicesReads();
    await wrapper.vm.$nextTick();
  }

  const sent = (id) => sender.sent.actions.filter((envelope) => envelope.action_id === id);
  const get = (id) => wrapper.get(`[data-testid="${id}"]`);

  // The drawer's entry read is one `services.open`; answer it with the exact
  // targeted snapshot so the drawer renders its selection and the dispatch
  // gate reopens.
  function targetedServices(services, providerId) {
    const next = { ...services, pagination: { ...services.pagination } };
    if (next.guild && next.guild.provider_id !== providerId) {
      next.guild = null;
      next.pagination.board_total = 0;
      next.pagination.quest_total = 0;
    }
    if (next.rank && next.rank.provider_id !== providerId) next.rank = null;
    if (next.shop && next.shop.provider_id !== providerId) {
      next.shop = null;
      next.pagination.stock_total = 0;
      next.pagination.sellable_total = 0;
    }
    return next;
  }

  function settleServicesReads() {
    for (const envelope of sent("services.open")) {
      if (answeredReads.has(envelope.request_id)) continue;
      answeredReads.add(envelope.request_id);
      const providerId = envelope.payload.npc_id;
      store.receive(1, "ui_action_result", [
        fx.actionResult({
          request_id: envelope.request_id,
          presentation_revision: store.view.revision,
          data: {
            npc_id: providerId,
            services: targetedServices(store.view.panels.services, providerId),
          },
        }),
      ]);
    }
  }

  function bagFor(memberId, potionHeld, purse) {
    return {
      ...PARTY_BAG_INVENTORY_SAMPLE,
      member_id: memberId,
      purse,
      rows: PARTY_BAG_INVENTORY_SAMPLE.rows.map((row) =>
        row.item_key === "potion_heal" ? { ...row, held: potionHeld } : row,
      ),
    };
  }

  function commitTrade(requestId, panels, revision = 2) {
    store.receive(1, "ui_update", [fx.update({ revision, panels })]);
    store.receive(1, "ui_action_result", [
      fx.actionResult({ request_id: requestId, presentation_revision: revision }),
    ]);
  }

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
    // The server answers the item before settling the request.
    store.receive(1, "ui_update", [
      fx.update({ revision: 2, panels: { item_holdings: { ...SHOP_HOLDINGS_POTION, item_key: "steel_shortsword" } } }),
    ]);
    store.receive(1, "ui_action_result", [fx.actionResult({ request_id: sent("party.view_member")[0].request_id, presentation_revision: 2 })]);
    await wrapper.vm.$nextTick();
    settleServicesReads();
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

  it("buys for the viewed acting puppet and refreshes the committed purse and bag", async () => {
    await mountWith({ services: SHOP_SERVICES_SAMPLE, party: SHOP_PARTY_SAMPLE, item_holdings: SHOP_HOLDINGS_POTION });
    const input = get("shop-window__quantity");
    input.element.value = "3";
    await input.trigger("input");
    await input.trigger("change");
    await get("action-bar__btn--trade").trigger("click");
    expect(sent("shop.buy").map((envelope) => envelope.payload)).toEqual([
      { item_key: "potion_heal", quantity: 3, recipient_id: SHOP_ELLA_ID, npc_id: SHOP_SERVICES_SAMPLE.shop.provider_id },
    ]);
    expect(get("action-bar__btn--trade").attributes("aria-busy")).toBe("true");
    const requestId = sent("shop.buy")[0].request_id;
    commitTrade(requestId, {
      services: {
        ...SHOP_SERVICES_SAMPLE,
        player: { ...SHOP_SERVICES_SAMPLE.player, wallet: 1120 },
      },
      party_inventory: bagFor(SHOP_ELLA_ID, 5, 1120),
    });
    await wrapper.vm.$nextTick();
    settleServicesReads();
    await wrapper.vm.$nextTick();
    expect(get("shop-window__purse").text()).toBe("1,120 銅");
    expect(store.view.panels.party_inventory.purse).toBe(1120);
    const potion = store.view.panels.party_inventory.rows.find((row) => row.item_key === "potion_heal");
    expect(potion.held).toBe(5);
    expect(wrapper.find('[data-testid="action-bar__reason"]').exists()).toBe(false);
  });

  it("sells from the viewed acting puppet and refreshes the committed purse", async () => {
    await mountWith({
      services: SHOP_SERVICES_SELLER_SAMPLE,
      party: SHOP_PARTY_SELLER_SAMPLE,
      item_holdings: SHOP_HOLDINGS_SELL,
    });
    store.openHudDrawer("shop");
    await wrapper.vm.$nextTick();
    await get("window-frame__tabs").find('[data-tab-key="sell"]').trigger("click");
    const input = get("shop-window__quantity");
    input.element.value = "2";
    await input.trigger("input");
    await input.trigger("change");
    await get("action-bar__btn--trade").trigger("click");
    expect(sent("shop.sell").map((envelope) => envelope.payload)).toEqual([
      { item_key: "rusty_sword", quantity: 2, seller_id: SHOP_KAHN_ID, npc_id: SHOP_SERVICES_SELLER_SAMPLE.shop.provider_id },
    ]);
    const requestId = sent("shop.sell")[0].request_id;
    commitTrade(requestId, {
      services: {
        ...SHOP_SERVICES_SELLER_SAMPLE,
        player: { ...SHOP_SERVICES_SELLER_SAMPLE.player, wallet: 1330 },
      },
      party_inventory: {
        ...PARTY_BAG_INVENTORY_SAMPLE,
        member_id: SHOP_KAHN_ID,
        purse: 1330,
        rows: [],
      },
    });
    await wrapper.vm.$nextTick();
    settleServicesReads();
    await wrapper.vm.$nextTick();
    expect(get("shop-window__purse").text()).toBe("1,330 銅");
    expect(store.view.panels.party_inventory.purse).toBe(1330);
    expect(store.view.panels.party_inventory.member_id).toBe(SHOP_KAHN_ID);
  });

  it("states the committed ordinary refusal of its own trade", async () => {
    await mountWith({ services: SHOP_SERVICES_SAMPLE, party: SHOP_PARTY_SAMPLE, item_holdings: SHOP_HOLDINGS_POTION });
    await get("action-bar__btn--trade").trigger("click");
    store.receive(1, "ui_action_result", [
      fx.actionResult({
        request_id: sent("shop.buy")[0].request_id,
        outcome: "rejected",
        code: "insufficient_funds",
        message: "你的銅幣不足。",
        presentation_revision: 1,
      }),
    ]);
    await wrapper.vm.$nextTick();
    const reason = get("action-bar__reason");
    expect(reason.text()).toBe("你的銅幣不足。");
    expect(reason.attributes("data-reason-code")).toBe("insufficient_funds");
  });

  it("closes through the drawer close route and leaves no shop surface in the DOM", async () => {
    await mountWith({ services: SHOP_SERVICES_SAMPLE, party: SHOP_PARTY_SAMPLE });
    await get("hud-drawer-close").trigger("click");
    await wrapper.vm.$nextTick();
    expect(store.view.hudDrawer).toBe(null);
    expect(wrapper.find('[data-testid="shop-window"]').exists()).toBe(false);
  });

  it("reads the provider whose card opened the drawer, not the summary's other NPC", async () => {
    await mountWith({ services: SHOP_SERVICES_SAMPLE, party: SHOP_PARTY_SAMPLE });
    await get("hud-drawer-close").trigger("click");
    await wrapper.vm.$nextTick();
    // The room summary names one merchant; the presence card names another.
    const summaryProvider = store.view.panels.services.shop.provider_id;
    expect(summaryProvider).not.toBe(7);
    store.activatePresence("target-7");
    await wrapper.vm.$nextTick();
    expect(store.view.presenceCard).toMatchObject({ kind: "verbs", identity: 7 });
    const before = sent("services.open").length;
    store.openHudDrawer("shop");
    await wrapper.vm.$nextTick();
    expect(sent("services.open").slice(before).map((envelope) => envelope.payload)).toEqual([
      { npc_id: 7 },
    ]);
  });

  it("states a pending surface while its first read waits for the single-action store", async () => {
    await mountWith({ services: SHOP_SERVICES_SAMPLE, party: SHOP_PARTY_SAMPLE });
    await get("hud-drawer-close").trigger("click");
    await wrapper.vm.$nextTick();
    // Another action holds the store, so the entry read cannot dispatch yet.
    expect(store.dispatchAction("explore.wait", { daypart: "dusk" })).not.toBe(null);
    await wrapper.vm.$nextTick();
    const before = sent("services.open").length;
    store.openHudDrawer("shop");
    await wrapper.vm.$nextTick();
    expect(sent("services.open")).toHaveLength(before);
    const unavailable = get("shop-window__unavailable");
    expect(unavailable.attributes("data-reason-code")).toBe("services_pending");
    // The room summary's rows are never offered for a targeted drawer.
    expect(wrapper.find('[data-testid="shop-rows__row--steel_shortsword"]').exists()).toBe(false);
  });

  it("states a refused provider read instead of the room summary's other provider", async () => {
    await mountWith({ services: SHOP_SERVICES_SAMPLE, party: SHOP_PARTY_SAMPLE });
    expect(wrapper.find('[data-testid="shop-rows__row--steel_shortsword"]').exists()).toBe(true);
    // A purchase commits, so the open drawer reads its provider again…
    const revision = store.view.revision + 1;
    store.receive(1, "ui_update", [fx.update({ revision, panels: {} })]);
    await wrapper.vm.$nextTick();
    const refresh = sent("services.open").at(-1);
    // …and the provider has left: the drawer states that refusal and never
    // falls back to the room summary the committed panels still carry.
    store.receive(1, "ui_action_result", [
      fx.actionResult({
        request_id: refresh.request_id,
        outcome: "rejected",
        code: "no_such_target",
        message: "這裡沒有這個對象。",
        presentation_revision: revision,
      }),
    ]);
    await wrapper.vm.$nextTick();
    const unavailable = get("shop-window__unavailable");
    expect(unavailable.attributes("data-reason-code")).toBe("no_such_target");
    expect(unavailable.text()).toBe("這裡沒有這個對象。");
    expect(wrapper.find('[data-testid="shop-rows__row--steel_shortsword"]').exists()).toBe(false);
  });
});
