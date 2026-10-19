// webclient-party-window-member-tab: the party window in the running client.
// It mounts under the `party` drawer key; a companion figure on the stage
// lineup opens 成員 with that companion (one `party.view_member`, pending
// until the server adopts it); a rail selection sends the open tab; 人物卡
// opens the NPC persona editor; 附身 dispatches its descriptor; the window
// closes with the party panel.
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import AppClient from "../AppClient.vue";
import { rememberPartyWindowTab, resetPartyWindowMemory } from "../components/party-window-memory.js";
import { useElosernStore } from "../stores/elosern.js";
import * as fx from "./store/protocol_fixtures.js";
import {
  PARTY_BAG_HOLDINGS_CONSUMABLE,
  PARTY_BAG_HOLDINGS_NONE,
  PARTY_BAG_INVENTORY_SAMPLE,
  PARTY_MEMBER_COMPANION_SAMPLE,
  PARTY_MEMBER_PANEL_SAMPLE,
  PARTY_WINDOW_PANEL_SAMPLE,
} from "../stories/fixtures/party_panels.js";

const COMMANDER_VIEW = { ...PARTY_WINDOW_PANEL_SAMPLE, viewed_member_id: 42 };

describe("the party window in AppClient (webclient-party-window-member-tab)", () => {
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

  async function mountWith(panels, mode = "exploration") {
    const host = document.createElement("div");
    host.id = "elosern-app";
    document.body.appendChild(host);
    wrapper = mount(AppClient, { attachTo: host });
    store.beginTransport(1);
    store.setConnected(true);
    store.receive(1, "ui_snapshot", [
      fx.snapshot({ mode, panels: { status: fx.statusPanel(), exploration: fx.explorationPanel(), ...panels } }),
    ]);
    await wrapper.vm.$nextTick();
  }

  const viewRequests = () => sender.sent.actions.filter((envelope) => envelope.action_id === "party.view_member");
  const entry = (id) => wrapper.get(`[data-testid="member-rail__entry--${id}"]`);

  it("opens 成員 with the activated lineup companion, pending until the server adopts it", async () => {
    await mountWith({ party: COMMANDER_VIEW, party_member: PARTY_MEMBER_PANEL_SAMPLE });
    const hits = wrapper.findAll('[data-testid="companion-member-hit"]').map((node) => Number(node.attributes("data-identity")));
    // Every companion figure, never the commander's own.
    expect(hits.sort()).toEqual([101, 102, 103]);
    await wrapper.get('[data-testid="companion-member-hit"][data-identity="102"]').trigger("click");
    expect(store.view.hudDrawer).toBe("party");
    expect(wrapper.get('[data-testid="party-window"]').attributes("data-tab")).toBe("member");
    expect(viewRequests()).toHaveLength(1);
    expect(viewRequests()[0].payload).toEqual({ member_id: 102, tab: "member", skill_key: null, item_key: null });
    expect(entry(102).attributes("aria-busy")).toBe("true");
    expect(entry(42).attributes("aria-current")).toBe("true");
    store.receive(1, "ui_action_result", [fx.actionResult({ request_id: viewRequests()[0].request_id, presentation_revision: 2 })]);
    store.receive(1, "ui_update", [
      fx.update({
        revision: 2,
        panels: {
          party: { ...PARTY_WINDOW_PANEL_SAMPLE, viewed_member_id: 102 },
          party_member: { ...PARTY_MEMBER_COMPANION_SAMPLE, member_id: 102, companion: { ...PARTY_MEMBER_COMPANION_SAMPLE.companion, actions: PARTY_MEMBER_COMPANION_SAMPLE.companion.actions.map((a) => ({ ...a, params: { npc_id: 102 } })) } },
        },
      }),
    ]);
    await wrapper.vm.$nextTick();
    expect(entry(102).attributes("aria-current")).toBe("true");
    expect(entry(102).attributes("aria-busy")).toBeUndefined();
  });

  it("opens on 成員 without a request for the already viewed companion, and only in exploration", async () => {
    await mountWith({ party: PARTY_WINDOW_PANEL_SAMPLE, party_member: PARTY_MEMBER_COMPANION_SAMPLE });
    await wrapper.get('[data-testid="companion-member-hit"][data-identity="101"]').trigger("click");
    expect(store.view.hudDrawer).toBe("party");
    expect(viewRequests()).toHaveLength(0);
    wrapper.unmount();
    document.body.innerHTML = "";
    setActivePinia(createPinia());
    store = useElosernStore();
    await mountWith({ party: PARTY_WINDOW_PANEL_SAMPLE }, "dialogue");
    expect(wrapper.find('[data-testid="companion-member-hit"]').exists()).toBe(false);
  });

  it("sends one party.view_member with the open tab for a rail selection, and none while busy", async () => {
    await mountWith({ party: PARTY_WINDOW_PANEL_SAMPLE, party_member: PARTY_MEMBER_COMPANION_SAMPLE });
    store.openHudDrawer("party");
    await wrapper.vm.$nextTick();
    await wrapper.get('[data-testid="icon-tabs__tab--status"]').trigger("click");
    await entry(42).trigger("click");
    expect(viewRequests().map((envelope) => envelope.payload)).toEqual([
      { member_id: 42, tab: "status", skill_key: null, item_key: null },
    ]);
    // The single dispatch slot is busy: the next selection is refused with
    // the busy toast and marks nothing pending.
    await entry(103).trigger("click");
    expect(viewRequests()).toHaveLength(1);
    expect(entry(103).attributes("aria-busy")).toBeUndefined();
    expect(store.view.toasts.some((toast) => toast.title === "目前無法執行此操作，請稍後再試。")).toBe(true);
  });

  it("opens the NPC persona editor from 人物卡 and dispatches 附身 from its descriptor", async () => {
    await mountWith({ party: PARTY_WINDOW_PANEL_SAMPLE, party_member: PARTY_MEMBER_COMPANION_SAMPLE });
    store.openHudDrawer("party");
    await wrapper.vm.$nextTick();
    await wrapper.get('[data-testid="action-bar__btn--possess"]').trigger("click");
    expect(sender.sent.actions.at(-1).action_id).toBe("explore.possess");
    expect(sender.sent.actions.at(-1).payload).toEqual({ npc_id: 101 });
    store.receive(1, "ui_action_result", [fx.actionResult({ request_id: sender.sent.actions.at(-1).request_id, outcome: "rejected", code: "nope", message: "不行。", presentation_revision: 1 })]);
    await wrapper.vm.$nextTick();
    await wrapper.get('[data-testid="action-bar__btn--npc-persona"]').trigger("click");
    await wrapper.vm.$nextTick();
    expect(store.view.hudDrawer).toBe("npc_persona");
  });

  it("closes the window when the party panel becomes unavailable", async () => {
    await mountWith({ party: PARTY_WINDOW_PANEL_SAMPLE, party_member: PARTY_MEMBER_COMPANION_SAMPLE });
    store.openHudDrawer("party");
    await wrapper.vm.$nextTick();
    expect(wrapper.find('[data-testid="party-window"]').exists()).toBe(true);
    store.receive(1, "ui_update", [
      fx.update({ revision: 2, panels: { party: { schema_version: 3, available: false, reason: { code: "party_unavailable", message: "隊伍資訊目前無法顯示" } } } }),
    ]);
    await wrapper.vm.$nextTick();
    expect(store.view.hudDrawer).toBe(null);
    expect(wrapper.find('[data-testid="party-window"]').exists()).toBe(false);
  });

  // webclient-party-bag-tab: the 背包 tab in the running client.
  async function openBag(holdings = PARTY_BAG_HOLDINGS_NONE, mode = "exploration") {
    await mountWith(
      { party: PARTY_WINDOW_PANEL_SAMPLE, party_member: PARTY_MEMBER_COMPANION_SAMPLE, party_inventory: PARTY_BAG_INVENTORY_SAMPLE, item_holdings: holdings },
      mode,
    );
    rememberPartyWindowTab(`${store.view.generation}|${store.view.epoch}`, "bag");
    store.openHudDrawer("party");
    await wrapper.vm.$nextTick();
  }
  const row = (key) => wrapper.get(`[data-testid="party-bag-tab__row--${key}"]`);

  it("sends one party.view_member carrying the item and marks the row pending until the server answers", async () => {
    await openBag();
    await row("potion_heal").trigger("click");
    expect(viewRequests().map((envelope) => envelope.payload)).toEqual([
      { member_id: 101, tab: "bag", skill_key: null, item_key: "potion_heal" },
    ]);
    expect(row("potion_heal").attributes("aria-busy")).toBe("true");
    expect(row("potion_heal").attributes("aria-selected")).toBe("true");
    // The rail entry is not marked pending by an item request.
    expect(entry(101).attributes("aria-busy")).toBeUndefined();
    store.receive(1, "ui_action_result", [fx.actionResult({ request_id: viewRequests()[0].request_id, presentation_revision: 2 })]);
    store.receive(1, "ui_update", [fx.update({ revision: 2, panels: { item_holdings: PARTY_BAG_HOLDINGS_CONSUMABLE } })]);
    await wrapper.vm.$nextTick();
    expect(row("potion_heal").attributes("aria-busy")).toBeUndefined();
    expect(row("potion_heal").attributes("aria-selected")).toBe("true");
    expect(wrapper.findAll('[data-testid="holdings-strip__count"]').map((node) => node.text())).toEqual(["2", "5", "0", "1"]);
  });

  it("leaves no sticky selection when the item request is rejected or refused", async () => {
    await openBag();
    await row("potion_heal").trigger("click");
    store.receive(1, "ui_action_result", [fx.actionResult({ request_id: viewRequests()[0].request_id, outcome: "rejected", code: "nope", message: "不行。", presentation_revision: 1 })]);
    await wrapper.vm.$nextTick();
    expect(wrapper.findAll('[data-testid="party-bag-tab"] [role="option"][aria-selected="true"]')).toHaveLength(0);
    // Busy: while 黑麥麵包 is in flight a click on another row is refused with
    // the busy toast, and the in-flight row stays the selection.
    await row("rye_bread").trigger("click");
    await row("potion_heal").trigger("click");
    expect(viewRequests()).toHaveLength(2);
    expect(row("potion_heal").attributes("aria-selected")).toBe("false");
    expect(row("rye_bread").attributes("aria-selected")).toBe("true");
    expect(row("rye_bread").attributes("aria-busy")).toBe("true");
    expect(store.view.toasts.some((toast) => toast.title === "目前無法執行此操作，請稍後再試。")).toBe(true);
  });

  it("keeps the requested row through the gap between the result and the update", async () => {
    await openBag();
    await row("rye_bread").trigger("click");
    store.receive(1, "ui_action_result", [fx.actionResult({ request_id: viewRequests()[0].request_id, presentation_revision: 2 })]);
    await wrapper.vm.$nextTick();
    expect(row("rye_bread").attributes("aria-selected")).toBe("true");
    store.receive(1, "ui_update", [fx.update({ revision: 2, panels: { item_holdings: { ...PARTY_BAG_HOLDINGS_CONSUMABLE, item_key: "rye_bread" } } })]);
    await wrapper.vm.$nextTick();
    expect(row("rye_bread").attributes("aria-selected")).toBe("true");
    expect(row("rye_bread").attributes("aria-busy")).toBeUndefined();
  });

  it("a rail selection replaces the pending item, and a late item result re-marks nothing", async () => {
    await openBag();
    await row("potion_heal").trigger("click");
    const itemRequest = viewRequests()[0];
    expect(row("potion_heal").attributes("aria-busy")).toBe("true");
    // The single dispatch slot admits the rail selection only once the item
    // request settles; the rail's request then owns the pending mark.
    store.receive(1, "ui_action_result", [fx.actionResult({ request_id: itemRequest.request_id, outcome: "rejected", code: "nope", message: "不行。", presentation_revision: 1 })]);
    await wrapper.vm.$nextTick();
    await entry(42).trigger("click");
    expect(viewRequests().at(-1).payload).toEqual({ member_id: 42, tab: "bag", skill_key: null, item_key: null });
    expect(entry(42).attributes("aria-busy")).toBe("true");
    expect(wrapper.findAll('[data-testid="party-bag-tab"] [role="option"][aria-busy="true"]')).toHaveLength(0);
    // A duplicate late result for the old item request changes nothing.
    store.receive(1, "ui_action_result", [fx.actionResult({ request_id: itemRequest.request_id, outcome: "rejected", code: "nope", message: "不行。", presentation_revision: 1 })]);
    await wrapper.vm.$nextTick();
    expect(wrapper.findAll('[data-testid="party-bag-tab"] [role="option"][aria-busy="true"]')).toHaveLength(0);
    expect(entry(42).attributes("aria-busy")).toBe("true");
  });

  it("dispatches the give with the viewed member as giver and the use with its actor", async () => {
    await openBag(PARTY_BAG_HOLDINGS_CONSUMABLE);
    await wrapper.get('[data-testid="party-bag-tab__stepper-up"]').trigger("click");
    await wrapper.get('[data-testid="holdings-strip__give--42"]').trigger("click");
    const transfer = sender.sent.actions.at(-1);
    expect(transfer.action_id).toBe("party.transfer");
    expect(transfer.payload).toEqual({ giver_id: 101, receiver_id: 42, item_key: "potion_heal", quantity: 2 });
    store.receive(1, "ui_action_result", [fx.actionResult({ request_id: transfer.request_id, outcome: "rejected", code: "nope", message: "不行。", presentation_revision: 1 })]);
    await wrapper.vm.$nextTick();
    await wrapper.get('[data-testid="action-bar__btn--use"]').trigger("click");
    await wrapper.get('[data-testid="party-bag-tab__confirm-ok"]').trigger("click");
    const use = sender.sent.actions.at(-1);
    expect(use.action_id).toBe("inventory.use");
    expect(use.payload).toEqual({ item_key: "potion_heal", actor_id: 101 });
  });
});
