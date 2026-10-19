// webclient-party-bag-tab: the party window's 背包 tab. The doll filters the
// bag by slot, a row selection asks the server for that item (the requested
// row shows only while its request is in flight), the holdings strip renders
// only the committed answer for the shown item, the stepper is bounded by the
// row's committed give count, every give/use/equip names the viewed member,
// and disabled controls carry their committed reasons.
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import Protocol from "../../../static/webclient/js/elosern/protocol.js";
import PartyBagTab from "../../components/PartyBagTab.vue";
import { useIntentHandlers } from "../../composables/intents.js";
import {
  PARTY_BAG_HOLDINGS_COMBAT,
  PARTY_BAG_HOLDINGS_CONSUMABLE,
  PARTY_BAG_HOLDINGS_EQUIPMENT,
  PARTY_BAG_HOLDINGS_NONE,
  PARTY_BAG_INVENTORY_COMBAT_SAMPLE,
  PARTY_BAG_INVENTORY_SAMPLE,
  TRANSFER_IN_COMBAT_REASON,
} from "../../stories/fixtures/party_panels.js";

const MEMBERS = [
  { id: 42, name: "影行者" },
  { id: 101, name: "蕾娜" },
  { id: 102, name: "幽" },
  { id: 103, name: "蓋文" },
];

describe("PartyBagTab (webclient-party-bag-tab)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
    document.body.innerHTML = "";
  });

  // A host that owns the window-local quantity like PartyWindow does.
  function mountTab(props = {}) {
    wrapper = mount(PartyBagTab, {
      attachTo: document.body,
      props: {
        partyInventory: PARTY_BAG_INVENTORY_SAMPLE,
        itemHoldings: PARTY_BAG_HOLDINGS_CONSUMABLE,
        members: MEMBERS,
        memberId: 101,
        quantity: 1,
        ...props,
        "onSet-quantity": (value) => wrapper.setProps({ quantity: value }),
      },
    });
    return wrapper;
  }

  const get = (id) => wrapper.get(`[data-testid="${id}"]`);
  const find = (id) => wrapper.find(`[data-testid="${id}"]`);
  const rowKeys = () =>
    wrapper.findAll('[role="option"]').map((node) => node.attributes("data-testid").replace("party-bag-tab__row--", ""));
  const actions = () => (wrapper.emitted("action") ?? []).map(([intent]) => intent);

  it("the story fixtures are valid party_inventory and item_holdings v1 payloads", () => {
    for (const panel of [PARTY_BAG_INVENTORY_SAMPLE, PARTY_BAG_INVENTORY_COMBAT_SAMPLE]) {
      expect(Protocol.validatePartyInventoryPanel(panel)).toEqual(panel);
    }
    for (const panel of [PARTY_BAG_HOLDINGS_CONSUMABLE, PARTY_BAG_HOLDINGS_EQUIPMENT, PARTY_BAG_HOLDINGS_COMBAT, PARTY_BAG_HOLDINGS_NONE]) {
      expect(Protocol.validateItemHoldingsPanel(panel)).toEqual(panel);
    }
  });

  it("draws the committed doll and filters the bag by the pressed slot", async () => {
    mountTab();
    expect(get("party-bag-tab__slot-name--weapon_main").text()).toBe("鐵製長劍");
    expect(get("party-bag-tab__slot-name--weapon_off").text()).toBe("—");
    expect(get("party-bag-tab__slot-name--armor").text()).toBe("旅人長袍");
    expect(get("party-bag-tab__slot-name--accessory").text()).toBe("銀月戒指");
    expect(get("party-bag-tab__slot-count--accessory").text()).toBe("1/5");
    expect(rowKeys()).toHaveLength(8);
    expect(get("party-bag-tab__count").text()).toBe("8 種");

    await get("party-bag-tab__slot--weapon_main").trigger("click");
    expect(get("party-bag-tab__slot--weapon_main").attributes("aria-pressed")).toBe("true");
    expect(rowKeys()).toEqual(["iron_longsword", "steel_shortsword"]);
    expect(get("party-bag-tab__count").text()).toBe("主手 ‧ 2 種");
    // An empty slot filters to nothing, stated as a state.
    await get("party-bag-tab__slot--weapon_off").trigger("click");
    expect(rowKeys()).toEqual([]);
    expect(get("party-bag-tab__filter-empty").text()).toBe("沒有副手的物品。");
    // Pressing the slot again clears the filter; filtering sent nothing.
    await get("party-bag-tab__slot--weapon_off").trigger("click");
    expect(rowKeys()).toHaveLength(8);
    expect(wrapper.emitted("select-item")).toBeUndefined();
  });

  it("asks for the selected item and shows the requested row only while its request is in flight", async () => {
    mountTab({ itemHoldings: PARTY_BAG_HOLDINGS_NONE });
    expect(find("party-bag-tab__idle").exists()).toBe(true);
    await get("party-bag-tab__row--potion_heal").trigger("click");
    expect(wrapper.emitted("select-item")).toEqual([["potion_heal"]]);

    // In flight: the requested row and its committed facts show, the strip waits.
    await wrapper.setProps({ selectedItemKey: "potion_heal", pendingItemKey: "potion_heal" });
    expect(get("party-bag-tab__row--potion_heal").attributes("aria-selected")).toBe("true");
    expect(get("party-bag-tab__row--potion_heal").attributes("aria-busy")).toBe("true");
    expect(get("party-bag-tab__title").text()).toBe("苦艾藥水");
    expect(get("party-bag-tab__summary").text()).toContain("紅色藥水");
    expect(find("holdings-strip").exists()).toBe(false);
    expect(get("party-bag-tab__holdings-wait").attributes("aria-busy")).toBe("true");

    // The request ends refused or rejected: the committed (no) selection rules.
    await wrapper.setProps({ pendingItemKey: null });
    expect(find("party-bag-tab__title").exists()).toBe(false);
    expect(wrapper.findAll('[role="option"][aria-selected="true"]')).toHaveLength(0);

    // The server adopts it: the committed answer is the selection.
    await wrapper.setProps({ itemHoldings: PARTY_BAG_HOLDINGS_CONSUMABLE });
    expect(get("party-bag-tab__title").text()).toBe("苦艾藥水");
    // Activating the shown row again sends nothing.
    await get("party-bag-tab__row--potion_heal").trigger("click");
    expect(wrapper.emitted("select-item")).toHaveLength(1);
  });

  it("renders every member's committed count and never another item's answer", async () => {
    mountTab();
    const counts = wrapper.findAll('[data-testid="holdings-strip__count"]').map((node) => node.text());
    expect(counts).toEqual(["2", "5", "0", "1"]);
    expect(get("holdings-strip__cell--101").text()).toContain("持有者");
    // While 黑麥麵包 is requested, the potion's answer is not reused for it.
    await wrapper.setProps({ selectedItemKey: "rye_bread", pendingItemKey: "rye_bread" });
    expect(get("party-bag-tab__title").text()).toBe("黑麥麵包");
    expect(find("holdings-strip").exists()).toBe(false);
    // An unavailable holdings panel: while the request still waits, the
    // wait state shows rather than a stale reason; once it ends, the
    // requested row states the registry reason only.
    await wrapper.setProps({
      itemHoldings: { schema_version: 1, available: false, reason: { code: "holdings_unavailable", message: "持有量目前無法顯示。" } },
    });
    expect(find("party-bag-tab__holdings-unavailable").exists()).toBe(false);
    expect(find("party-bag-tab__holdings-wait").exists()).toBe(true);
    await wrapper.setProps({ pendingItemKey: null });
    expect(get("party-bag-tab__title").text()).toBe("黑麥麵包");
    expect(get("party-bag-tab__holdings-unavailable").text()).toBe("持有量目前無法顯示。");
    expect(find("holdings-strip").exists()).toBe(false);
  });

  it("keeps focus in the window when a changed descriptor retires the confirmation", async () => {
    mountTab();
    await get("action-bar__btn--use").trigger("click");
    await wrapper.vm.$nextTick();
    expect(document.activeElement).toBe(get("party-bag-tab__confirm-ok").element);
    const gated = {
      ...PARTY_BAG_INVENTORY_SAMPLE,
      rows: PARTY_BAG_INVENTORY_SAMPLE.rows.map((row) =>
        row.item_key === "potion_heal" ? { ...row, use: { route: "field_use", enabled: false, reason: "現在不需要。" } } : row,
      ),
    };
    await wrapper.setProps({ partyInventory: gated });
    await wrapper.vm.$nextTick();
    expect(find("party-bag-tab__confirm-dialog").exists()).toBe(false);
    expect(wrapper.element.contains(document.activeElement)).toBe(true);
    expect(actions()).toEqual([]);
  });

  it("shows equipment deltas verbatim from the server", () => {
    mountTab({ itemHoldings: PARTY_BAG_HOLDINGS_EQUIPMENT });
    expect(get("party-bag-tab__ribbon").text()).toBe("武器 ‧ 主手");
    expect(get("holdings-strip__cell--42").text()).toContain("▲ 攻擊 +6");
    expect(get("holdings-strip__cell--101").text()).toContain("▼ 攻擊 −2");
    expect(get("holdings-strip__cell--101").text()).toContain("▲ 敏捷 +3");
    expect(get("holdings-strip__cell--102").text()).toContain("無法裝備");
    expect(get("holdings-strip__cell--102").text()).toContain("幽無法使用這類武器。");
    // Equipment gives one: no stepper, no ×n on the give control.
    expect(find("party-bag-tab__stepper").exists()).toBe(false);
    expect(get("holdings-strip__give--42").text()).toBe("交給影行者");
  });

  it("bounds the stepper by the committed give count and resets it with the item", async () => {
    mountTab();
    expect(get("party-bag-tab__quantity").text()).toBe("1");
    expect(get("party-bag-tab__stepper-down").attributes("aria-disabled")).toBe("true");
    for (let i = 0; i < 7; i += 1) await get("party-bag-tab__stepper-up").trigger("click");
    expect(get("party-bag-tab__quantity").text()).toBe("5");
    expect(get("party-bag-tab__stepper-up").attributes("aria-disabled")).toBe("true");
    expect(get("holdings-strip__give--42").text()).toBe("交給影行者 ×5");
    // A snapshot that lowers the give count clamps the shown quantity.
    const fewer = {
      ...PARTY_BAG_INVENTORY_SAMPLE,
      rows: PARTY_BAG_INVENTORY_SAMPLE.rows.map((row) =>
        row.item_key === "potion_heal" ? { ...row, held: 2, give: { ...row.give, max_quantity: 2 } } : row,
      ),
    };
    await wrapper.setProps({ partyInventory: fewer });
    expect(get("party-bag-tab__quantity").text()).toBe("2");
    expect(wrapper.props("quantity")).toBe(2);
    // Another item resets it to one.
    await wrapper.setProps({ itemHoldings: { ...PARTY_BAG_HOLDINGS_CONSUMABLE, item_key: "rye_bread" } });
    expect(get("party-bag-tab__quantity").text()).toBe("1");
  });

  it("sends exactly one party.transfer with the viewed member as giver", async () => {
    mountTab();
    await get("party-bag-tab__stepper-up").trigger("click");
    await get("party-bag-tab__stepper-up").trigger("click");
    await get("holdings-strip__give--42").trigger("click");
    expect(actions()).toEqual([
      { action_id: "party.transfer", payload: { giver_id: 101, receiver_id: 42, item_key: "potion_heal", quantity: 3 } },
    ]);
    expect(Object.keys(actions()[0].payload).sort()).toEqual(["giver_id", "item_key", "quantity", "receiver_id"]);
  });

  it("offers no give to a disabled receiver and keeps its committed reason", () => {
    mountTab();
    expect(find("holdings-strip__give--103").exists()).toBe(false);
    expect(get("holdings-strip__cell--103").get('[data-testid="holdings-strip__reason"]').text()).toBe("對方不在這裡。");
    // The viewed member's own cell has no give either.
    expect(find("holdings-strip__give--101").exists()).toBe(false);
  });

  it("states an equipped row's committed give reason and offers 卸下", async () => {
    mountTab({ itemHoldings: { ...PARTY_BAG_HOLDINGS_EQUIPMENT, item_key: "iron_longsword", rows: PARTY_BAG_HOLDINGS_EQUIPMENT.rows.map((row) => ({ ...row, held: row.member_id === 101 ? 1 : 0, equipped: row.member_id === 101, delta: row.member_id === 101 ? { equippable: true, changes: [] } : row.delta, receive: row.member_id === 101 ? row.receive : { enabled: false, reason: "已裝備的物品無法交換；請先卸下。" } })) } });
    expect(get("action-bar__reason").text()).toBe("已裝備的物品無法交換；請先卸下。");
    expect(get("action-bar__btn--toggle").text()).toBe("卸下");
    expect(find("party-bag-tab__stepper").exists()).toBe(false);
  });

  it("names the replaced main hand and toggles for the viewed member", async () => {
    mountTab({ itemHoldings: PARTY_BAG_HOLDINGS_EQUIPMENT });
    expect(get("action-bar__btn--toggle").text()).toBe("裝備（替換 鐵製長劍）");
    expect(find("action-bar__btn--use").exists()).toBe(false);
    await get("action-bar__btn--toggle").trigger("click");
    expect(actions()).toEqual([{ action_id: "inventory.toggle_equip", payload: { item_key: "steel_shortsword", actor_id: 101 } }]);
  });

  it("equips an accessory without naming a client-chosen accessory", () => {
    const ring = {
      ...PARTY_BAG_INVENTORY_SAMPLE,
      equipment: { ...PARTY_BAG_INVENTORY_SAMPLE.equipment, accessories: [] },
      rows: PARTY_BAG_INVENTORY_SAMPLE.rows.map((row) =>
        row.item_key === "silver_ring" ? { ...row, equipped_count: 0, give: { enabled: true, reason: null, max_quantity: 1 } } : row,
      ),
    };
    mountTab({
      partyInventory: ring,
      itemHoldings: { ...PARTY_BAG_HOLDINGS_EQUIPMENT, item_key: "silver_ring" },
    });
    expect(get("action-bar__btn--toggle").text()).toBe("裝備");
  });

  it("uses an item only after the labelled confirmation, for the viewed member", async () => {
    mountTab();
    await get("action-bar__btn--use").trigger("click");
    expect(actions()).toEqual([]);
    const dialog = get("party-bag-tab__confirm-dialog");
    expect(dialog.attributes("role")).toBe("dialog");
    expect(dialog.attributes("aria-label")).toBe("使用 苦艾藥水");
    expect(get("party-bag-tab__confirm-text").text()).toBe("確定要讓蕾娜使用「苦艾藥水」？");
    // The content behind it is inert while it is open.
    expect(get("list-detail").attributes("inert")).toBeDefined();
    await wrapper.vm.$nextTick();
    expect(document.activeElement).toBe(get("party-bag-tab__confirm-ok").element);
    // Escape cancels and does not reach the window.
    let bubbled = false;
    wrapper.element.parentElement.addEventListener("keydown", () => {
      bubbled = true;
    });
    await dialog.trigger("keydown", { key: "Escape" });
    expect(bubbled).toBe(false);
    expect(find("party-bag-tab__confirm-dialog").exists()).toBe(false);
    expect(actions()).toEqual([]);
    // Confirming sends exactly one inventory.use.
    await get("action-bar__btn--use").trigger("click");
    await get("party-bag-tab__confirm-ok").trigger("click");
    expect(actions()).toEqual([{ action_id: "inventory.use", payload: { item_key: "potion_heal", actor_id: 101 } }]);
    expect(find("party-bag-tab__confirm-dialog").exists()).toBe(false);
  });

  it("keeps Tab inside the confirmation and retires it when the member changes", async () => {
    mountTab();
    await get("action-bar__btn--use").trigger("click");
    await wrapper.vm.$nextTick();
    const ok = get("party-bag-tab__confirm-ok").element;
    const cancel = get("party-bag-tab__confirm-cancel").element;
    await get("party-bag-tab__confirm-dialog").trigger("keydown", { key: "Tab" });
    expect(document.activeElement).toBe(cancel);
    await get("party-bag-tab__confirm-dialog").trigger("keydown", { key: "Tab", shiftKey: true });
    expect(document.activeElement).toBe(ok);
    await wrapper.setProps({ memberId: 42, partyInventory: { ...PARTY_BAG_INVENTORY_SAMPLE, member_id: 42 } });
    expect(find("party-bag-tab__confirm-dialog").exists()).toBe(false);
    expect(actions()).toEqual([]);
  });

  it("shows a disabled use's committed reason and sends nothing", async () => {
    mountTab({ itemHoldings: { ...PARTY_BAG_HOLDINGS_CONSUMABLE, item_key: "potion_mana" } });
    const use = get("action-bar__btn--use");
    expect(use.attributes("aria-disabled")).toBe("true");
    expect(get("action-bar__reason").text()).toBe("魔力已經是滿的。");
    await use.trigger("click");
    expect(find("party-bag-tab__confirm-dialog").exists()).toBe(false);
    expect(actions()).toEqual([]);
  });

  it("offers neither use nor equip for an item without descriptors", () => {
    mountTab({ itemHoldings: { ...PARTY_BAG_HOLDINGS_CONSUMABLE, item_key: "moon_herb" } });
    expect(find("action-bar__btn--use").exists()).toBe(false);
    expect(find("action-bar__btn--toggle").exists()).toBe(false);
    expect(find("party-bag-tab__stepper").exists()).toBe(true);
  });

  it("shows counts only in combat, with the committed reason and no give or exploration use", async () => {
    mountTab({ partyInventory: PARTY_BAG_INVENTORY_COMBAT_SAMPLE, itemHoldings: PARTY_BAG_HOLDINGS_COMBAT, combat: true });
    expect(get("holdings-strip").attributes("data-combat")).toBe("true");
    expect(wrapper.findAll('[data-testid^="holdings-strip__give--"]')).toHaveLength(0);
    expect(wrapper.findAll('[data-testid="holdings-strip__delta"]')).toHaveLength(0);
    expect(find("party-bag-tab__stepper").exists()).toBe(false);
    expect(find("action-bar__btn--use").exists()).toBe(false);
    expect(get("action-bar__reason").text()).toBe(TRANSFER_IN_COMBAT_REASON);
    // Every member's committed count stays readable.
    expect(wrapper.findAll('[data-testid="holdings-strip__count"]').map((node) => node.text())).toEqual(["2", "5", "0", "1"]);
  });

  it("turns 使用 into the viewed member's round choice and sends nothing itself", async () => {
    mountTab({ partyInventory: PARTY_BAG_INVENTORY_COMBAT_SAMPLE, itemHoldings: PARTY_BAG_HOLDINGS_COMBAT, combat: true });
    const draft = get("action-bar__btn--draft");
    expect(draft.text()).toBe("設為 蕾娜 本回合的行動…");
    expect(draft.attributes("aria-disabled")).toBeUndefined();
    await draft.trigger("click");
    expect(wrapper.emitted("combat-item")).toEqual([[{ memberId: 101, itemKey: "potion_heal" }]]);
    // No confirmation opens: the combat item review/target step is the confirmation.
    expect(find("party-bag-tab__confirm").exists()).toBe(false);
    expect(actions()).toEqual([]);
  });

  it("keeps a disabled round choice's committed reason and emits nothing", async () => {
    mountTab({
      partyInventory: PARTY_BAG_INVENTORY_COMBAT_SAMPLE,
      itemHoldings: { ...PARTY_BAG_HOLDINGS_COMBAT, item_key: "potion_mana" },
      combat: true,
    });
    const draft = get("action-bar__btn--draft");
    expect(draft.attributes("aria-disabled")).toBe("true");
    expect(wrapper.findAll('[data-testid="action-bar__reason"]').map((node) => node.text())).toContain("魔力已經是滿的。");
    await draft.trigger("click");
    expect(wrapper.emitted("combat-item")).toBeUndefined();
    expect(actions()).toEqual([]);
  });

  it("keeps every member's equipment toggle free in combat", async () => {
    mountTab({
      partyInventory: PARTY_BAG_INVENTORY_COMBAT_SAMPLE,
      itemHoldings: { ...PARTY_BAG_HOLDINGS_COMBAT, item_key: "steel_shortsword" },
      combat: true,
    });
    expect(find("action-bar__btn--draft").exists()).toBe(false);
    const toggle = get("action-bar__btn--toggle");
    expect(toggle.attributes("aria-disabled")).toBeUndefined();
    await toggle.trigger("click");
    expect(actions()).toEqual([{ action_id: "inventory.toggle_equip", payload: { item_key: "steel_shortsword", actor_id: 101 } }]);
  });

  it("never offers the round choice outside combat or a field use in combat", async () => {
    // A transient disagreement between the mode and the descriptor route
    // offers neither control.
    mountTab({ partyInventory: PARTY_BAG_INVENTORY_COMBAT_SAMPLE, itemHoldings: PARTY_BAG_HOLDINGS_COMBAT, combat: false });
    expect(find("action-bar__btn--draft").exists()).toBe(false);
    expect(find("action-bar__btn--use").exists()).toBe(false);
    await wrapper.setProps({ partyInventory: PARTY_BAG_INVENTORY_SAMPLE, combat: true });
    expect(find("action-bar__btn--draft").exists()).toBe(false);
    expect(find("action-bar__btn--use").exists()).toBe(false);
  });

  it("states the bag panel's reason and invents no rows", () => {
    mountTab({ partyInventory: { schema_version: 1, available: false, reason: { code: "inventory_unavailable", message: "背包目前無法顯示。" } } });
    expect(get("party-window__tab-unavailable").text()).toBe("背包目前無法顯示。");
    expect(wrapper.findAll('[role="option"]')).toHaveLength(0);
    expect(find("party-bag-tab__doll").exists()).toBe(false);
    expect(find("action-bar").exists()).toBe(false);
  });

  it("shows no rows for a bag that describes another member", () => {
    mountTab({ memberId: 42 });
    expect(wrapper.findAll('[role="option"]')).toHaveLength(0);
    expect(find("party-bag-tab__doll").exists()).toBe(false);
  });

  it("moves focus along the rows with the arrow keys", async () => {
    mountTab();
    const rows = wrapper.findAll('[role="option"]');
    expect(rows.filter((row) => row.attributes("tabindex") === "0")).toHaveLength(1);
    rows[0].element.focus();
    await get("party-bag-tab__rows").trigger("keydown", { key: "ArrowDown" });
    expect(document.activeElement).toBe(rows[1].element);
    await get("party-bag-tab__rows").trigger("keydown", { key: "End" });
    expect(document.activeElement).toBe(rows.at(-1).element);
    await get("party-bag-tab__rows").trigger("keydown", { key: "Home" });
    expect(document.activeElement).toBe(rows[0].element);
  });

  it("has no possession input and renders identically for the same panels", () => {
    expect(Object.keys(PartyBagTab.props)).not.toContain("possessing");
    mountTab();
    const first = wrapper.html();
    wrapper.unmount();
    mountTab();
    expect(wrapper.html()).toBe(first);
    expect(wrapper.text()).not.toMatch(/你|自己|操控中/);
  });
});

describe("onPartyBagAction (webclient-party-bag-tab)", () => {
  function handlers(mode) {
    const sent = [];
    const store = { view: { mode }, pushToast: () => {} };
    const { onPartyBagAction } = useIntentHandlers(store, (actionId, payload) => sent.push({ actionId, payload }));
    return { onPartyBagAction, sent };
  }

  it("forwards the closed bag set and nothing else", () => {
    const { onPartyBagAction, sent } = handlers("exploration");
    onPartyBagAction({ action_id: "party.transfer", payload: { giver_id: 101, receiver_id: 42, item_key: "potion_heal", quantity: 1 } });
    onPartyBagAction({ action_id: "inventory.use", payload: { item_key: "potion_heal", actor_id: 101 } });
    onPartyBagAction({ action_id: "inventory.toggle_equip", payload: { item_key: "steel_shortsword", actor_id: 101 } });
    onPartyBagAction({ action_id: "shop.buy", payload: {} });
    expect(sent.map((entry) => entry.actionId)).toEqual(["party.transfer", "inventory.use", "inventory.toggle_equip"]);
  });

  it("never sends an exploration use or a give in combat", () => {
    const { onPartyBagAction, sent } = handlers("combat");
    onPartyBagAction({ action_id: "inventory.use", payload: { item_key: "potion_heal", actor_id: 101 } });
    onPartyBagAction({ action_id: "party.transfer", payload: { giver_id: 101, receiver_id: 42, item_key: "potion_heal", quantity: 1 } });
    onPartyBagAction({ action_id: "inventory.toggle_equip", payload: { item_key: "steel_shortsword", actor_id: 101 } });
    expect(sent.map((entry) => entry.actionId)).toEqual(["inventory.toggle_equip"]);
  });
});

describe("onPartyBagCombatItem (webclient-party-bag-retire)", () => {
  function handlers(mode, result = true) {
    const calls = [];
    const toasts = [];
    const store = {
      view: { mode },
      pushToast: (entry) => toasts.push(entry),
      useCombatItem: (itemKey, actorId) => {
        calls.push({ itemKey, actorId });
        return result;
      },
    };
    const { onPartyBagCombatItem } = useIntentHandlers(store, () => {
      throw new Error("the round choice never dispatches from the bag");
    });
    return { onPartyBagCombatItem, calls, toasts };
  }

  it("hands the viewed member's item to the combat item flow", () => {
    const { onPartyBagCombatItem, calls, toasts } = handlers("combat");
    onPartyBagCombatItem({ memberId: 101, itemKey: "potion_mana" });
    expect(calls).toEqual([{ itemKey: "potion_mana", actorId: 101 }]);
    expect(toasts).toEqual([]);
  });

  it("states a refusal and ignores the intent outside combat", () => {
    const refused = handlers("combat", false);
    refused.onPartyBagCombatItem({ memberId: 101, itemKey: "potion_mana" });
    expect(refused.toasts.map((toast) => toast.title)).toEqual(["這件物品目前無法由這名成員使用。"]);
    const outside = handlers("exploration");
    outside.onPartyBagCombatItem({ memberId: 101, itemKey: "potion_mana" });
    expect(outside.calls).toEqual([]);
  });
});
