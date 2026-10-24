// webclient-shop-window: the shop window renders committed services v7 rows
// and item_holdings facts only, selects through party.view_member, and sends
// one shop.buy / shop.sell naming shop.member_id.
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import Protocol from "../../../static/webclient/js/elosern/protocol.js";
import ShopWindow from "../../components/ShopWindow.vue";
import {
  clampQuantity,
  deltaFacts,
  quantityBounds,
  tradePreview,
} from "../../components/shop-window-model.js";
import {
  SERVICES_PANEL_MINIMAL_SAMPLE,
  SERVICES_PANEL_UNAVAILABLE_SAMPLE,
  SHOP_CHARACTER_SAMPLE,
  SHOP_COMMANDER_ID,
  SHOP_ELLA_ID,
  SHOP_HOLDINGS_EQUIPMENT,
  SHOP_HOLDINGS_POTION,
  SHOP_HOLDINGS_SELL,
  SHOP_KAHN_ID,
  SHOP_PARTY_SAMPLE,
  SHOP_PARTY_SELLER_SAMPLE,
  SHOP_SERVICES_CLOSED_SAMPLE,
  SHOP_SERVICES_SAMPLE,
  SHOP_SERVICES_SELLER_SAMPLE,
} from "../../stories/fixtures.js";

// The potion row's committed display name, read from the fixture.
const POTION_NAME = SHOP_SERVICES_SAMPLE.shop.stock.find((r) => r.item_key === "potion_heal").display_name;

// One local asymmetric offer for the price-authority regression: the potion
// buys at 8 and sells at 6. Six is not half of eight (half of eight is four),
// so a view that read the other field would render or total a different
// number. The shared story fixtures keep their own pairs untouched.
const POTION_BUY_COPPER = 8;
const POTION_SELL_COPPER = 6;

function withAsymmetricPotion(panel) {
  return {
    ...panel,
    shop: {
      ...panel.shop,
      stock: panel.shop.stock.map((row) =>
        row.item_key === "potion_heal" ? { ...row, buy_copper: POTION_BUY_COPPER } : row
      ),
      sellable: panel.shop.sellable.map((row) =>
        row.item_key === "potion_heal" ? { ...row, sell_copper: POTION_SELL_COPPER } : row
      ),
    },
  };
}

const SHOP_SERVICES_ASYMMETRIC_BUY = withAsymmetricPotion(SHOP_SERVICES_SAMPLE);
const SHOP_SERVICES_ASYMMETRIC_SELL = withAsymmetricPotion(SHOP_SERVICES_SELLER_SAMPLE);

// 卡恩's committed answer for the potion he is selling: the potion's held
// counts and non-equipment facts, with his own row refusing a receive.
const SHOP_HOLDINGS_ASYMMETRIC_SELL = {
  ...SHOP_HOLDINGS_POTION,
  giver_id: SHOP_KAHN_ID,
  rows: SHOP_HOLDINGS_POTION.rows.map((row) => ({
    ...row,
    receive: { enabled: row.member_id !== SHOP_KAHN_ID, reason: null },
  })),
};

describe("ShopWindow (webclient-shop-window)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
    document.body.innerHTML = "";
  });

  function mountWindow(props = {}) {
    const host = document.createElement("div");
    document.body.appendChild(host);
    wrapper = mount(ShopWindow, {
      attachTo: host,
      props: {
        services: SHOP_SERVICES_SAMPLE,
        party: SHOP_PARTY_SAMPLE,
        itemHoldings: SHOP_HOLDINGS_EQUIPMENT,
        character: SHOP_CHARACTER_SAMPLE,
        ...props,
      },
    });
    return wrapper;
  }

  const get = (id) => wrapper.get(`[data-testid="${id}"]`);
  const find = (id) => wrapper.find(`[data-testid="${id}"]`);
  const row = (key) => get(`shop-rows__row--${key}`);
  const priceTexts = () => wrapper.findAll('[data-testid="shop-rows__price"]').map((n) => n.text());
  const priceValues = () =>
    wrapper.findAll('[data-testid="shop-rows__price"]').map((n) => Number(n.text().replace(/\D/g, "")));

  it("the fixtures are exact committed payloads", () => {
    for (const panel of [SHOP_SERVICES_SAMPLE, SHOP_SERVICES_SELLER_SAMPLE, SHOP_SERVICES_CLOSED_SAMPLE]) {
      expect(Protocol.validateServicesPanel(panel)).toEqual(panel);
    }
    for (const panel of [SHOP_HOLDINGS_EQUIPMENT, SHOP_HOLDINGS_POTION, SHOP_HOLDINGS_SELL]) {
      expect(Protocol.validateItemHoldingsPanel(panel)).toEqual(panel);
    }
    for (const panel of [SHOP_PARTY_SAMPLE, SHOP_PARTY_SELLER_SAMPLE]) {
      expect(Protocol.validatePartyPanel(panel)).toEqual(panel);
    }
  });

  it("renders the frame: host title, open state, 購買/出售 tabs, the purse once in the header, no category rail", () => {
    mountWindow();
    expect(wrapper.get(".drawer-header__title").text()).toBe("鐵匠鋪");
    expect(wrapper.text()).toContain("營業中");
    const tabs = wrapper.findAll('[data-testid="window-frame__tabs"] [role="tab"]');
    expect(tabs.map((tab) => tab.text())).toEqual(["購買", "出售"]);
    expect(get("shop-window__purse").text()).toBe("1,240 銅");
    expect(wrapper.findAll('[data-testid="shop-window__purse"]')).toHaveLength(1);
    expect(find("shop-window__category").exists()).toBe(false);
  });

  it("carries the party window's selection: the rail shows the viewed member as the recipient", () => {
    mountWindow();
    const selected = wrapper.get('.member-rail [aria-current="true"]');
    expect(selected.text()).toContain("艾拉");
    expect(get("shop-window__list-title").text()).toBe("為艾拉挑選");
    expect(get("action-bar__btn--trade").text()).toBe("買給艾拉");
  });

  it("a rail selection emits one view-member with the shown item, and dims the facts while it is in flight", async () => {
    mountWindow();
    const kahn = wrapper.findAll(".member-rail button").find((button) => button.text().includes("卡恩"));
    await kahn.trigger("click");
    expect(wrapper.emitted("view-member")).toEqual([[{ memberId: SHOP_KAHN_ID, itemKey: "steel_shortsword" }]]);
    // The rail never switches optimistically.
    expect(wrapper.get('.member-rail [aria-current="true"]').text()).toContain("艾拉");
    await wrapper.setProps({ pendingMemberId: SHOP_KAHN_ID });
    expect(row("steel_shortsword").get('[data-testid="shop-rows__fact"]').classes()).toContain("is-stale");
    expect(get("action-bar__btn--trade").attributes("aria-disabled")).toBe("true");
  });

  it("each 購買 row shows icon, name, stock and the buy price only, plus the recipient's delta or held count", () => {
    mountWindow();
    const sword = row("steel_shortsword");
    expect(sword.text()).toContain("鋼製短劍");
    expect(sword.get('[data-testid="shop-rows__stock"]').text()).toBe("庫存 3");
    expect(sword.get('[data-testid="shop-rows__price"]').text()).toContain("320");
    expect(sword.findAll('[data-testid="shop-rows__delta"]').map((n) => n.text())).toEqual(["▲ 攻擊 +6"]);
    expect(row("iron_longsword").findAll('[data-testid="shop-rows__delta"]').map((n) => n.text())).toEqual(["▲ 攻擊 +4", "▼ 敏捷 −2"]);
    const ring = row("moonstone_ring").get('[data-testid="shop-rows__delta"]');
    expect(ring.text()).toBe("無法裝備");
    expect(ring.attributes("data-reason-code")).toBe("accessory_slots_full");
    expect(row("birch_staff").get('[data-testid="shop-rows__delta"]').text()).toBe("±0");
    expect(row("potion_heal").get('[data-testid="shop-rows__member-held"]').text()).toBe("持有 2");
    expect(row("shortbow").get('[data-testid="shop-rows__stock"]').text()).toBe("售完");
  });

  it("the 購買 view shows no sell price anywhere", () => {
    mountWindow();
    const text = get("shop-window").text();
    // The potion's sell price (15) is not rendered; its buy price is.
    expect(row("potion_heal").get('[data-testid="shop-rows__price"]').text()).toContain("30");
    expect(text).not.toContain("賣價");
    expect(wrapper.findAll('[data-testid="shop-rows__price"]').map((n) => n.text().replace(/\D/g, ""))).toEqual(
      SHOP_SERVICES_SAMPLE.shop.stock.map((r) => String(r.buy_copper)),
    );
  });

  it("selects a row through view-item and shows it once the request is admitted", async () => {
    mountWindow({ itemHoldings: null });
    expect(find("shop-window__idle").exists()).toBe(true);
    await row("potion_heal").trigger("click");
    expect(wrapper.emitted("view-item")).toEqual([[{ memberId: SHOP_ELLA_ID, itemKey: "potion_heal" }]]);
    // A refused request (nothing in flight) leaves no selection.
    expect(find("shop-window__idle").exists()).toBe(true);
    await wrapper.setProps({ pendingItemKey: "potion_heal" });
    expect(get("shop-window__title").text()).toBe(POTION_NAME);
    expect(find("shop-window__holdings-wait").exists()).toBe(true);
    await wrapper.setProps({ pendingItemKey: null, itemHoldings: SHOP_HOLDINGS_POTION });
    expect(get("shop-window__title").text()).toBe(POTION_NAME);
  });

  it("a row request that ends without its answer hands the selection back to the committed item", async () => {
    mountWindow({ itemHoldings: SHOP_HOLDINGS_POTION });
    await row("steel_shortsword").trigger("click");
    await wrapper.setProps({ pendingItemKey: "steel_shortsword" });
    expect(get("shop-window__title").text()).toBe("鋼製短劍");
    // Rejected: the request ends and item_holdings still answers the potion.
    await wrapper.setProps({ pendingItemKey: null });
    expect(get("shop-window__title").text()).toBe(POTION_NAME);
  });

  it("an entry holding no valid count disables the trade and hides the preview", async () => {
    mountWindow({ itemHoldings: SHOP_HOLDINGS_POTION });
    const input = get("shop-window__quantity");
    input.element.value = "";
    await input.trigger("input");
    expect(get("action-bar__btn--trade").attributes("aria-disabled")).toBe("true");
    expect(find("shop-window__sum").exists()).toBe(false);
  });

  it("the equipment detail compares the recipient's committed values with the server change lines and chips the other members", () => {
    mountWindow();
    expect(get("shop-window__current").text()).toContain("艾拉");
    expect(get("shop-window__current").text()).toContain("攻擊18");
    expect(get("shop-window__after").text()).toContain("鋼製短劍");
    expect(get("shop-window__after").text()).toContain("▲ 攻擊 +6");
    const chips = wrapper.findAll('[data-testid^="holdings-strip__chip--"]');
    expect(chips.map((chip) => chip.attributes("data-testid"))).toEqual([
      `holdings-strip__chip--${SHOP_COMMANDER_ID}`,
      `holdings-strip__chip--${SHOP_KAHN_ID}`,
    ]);
    expect(chips[0].text()).toContain("▲ 攻擊 +2");
    expect(chips[1].text()).toContain("▼ 攻擊 −4");
  });

  it("renders the recipient's current value without binary float noise", () => {
    // A percentage fold (6 × (1 − 5%)) arrives as 5.699999999999999; the
    // comparison prints the display value 5.7.
    const noisy = {
      ...SHOP_CHARACTER_SAMPLE,
      traits: SHOP_CHARACTER_SAMPLE.traits.map((row) =>
        row.key === "atk_phys"
          ? { ...row, current: 5.699999999999999, effective: 5.699999999999999 }
          : row
      ),
    };
    mountWindow({ character: noisy });
    const current = get("shop-window__current").text();
    expect(current).toContain("攻擊5.7");
    expect(current).not.toContain("5.699999");
  });

  it("chips render only an item_holdings answer for exactly the shown item and recipient", async () => {
    mountWindow({ itemHoldings: { ...SHOP_HOLDINGS_EQUIPMENT, giver_id: SHOP_KAHN_ID } });
    expect(find("shop-window__idle").exists()).toBe(true);
    await wrapper.setProps({ itemHoldings: SHOP_HOLDINGS_POTION });
    const chips = wrapper.findAll('[data-testid^="holdings-strip__chip--"]');
    expect(chips.map((chip) => chip.get('[data-testid="holdings-strip__count"]').text())).toEqual(["3", "2", "1"]);
    await chips[2].trigger("click");
    expect(wrapper.emitted("view-member")).toEqual([[{ memberId: SHOP_KAHN_ID, itemKey: "potion_heal" }]]);
  });

  it("the stepper is bounded by the committed maximum and a typed out-of-range value is clamped on leaving", async () => {
    mountWindow({ itemHoldings: SHOP_HOLDINGS_POTION });
    const input = get("shop-window__quantity");
    expect(input.element.value).toBe("1");
    expect(get("shop-window__quantity-max").text()).toBe("/ 12");
    // Typing raises input events only; the entry commits on leaving.
    input.element.value = "30";
    await input.trigger("input");
    // Out of bounds: the trade sends nothing until the entry is corrected.
    await get("action-bar__btn--trade").trigger("click");
    expect(wrapper.emitted("trade")).toBeUndefined();
    await input.trigger("blur");
    expect(input.element.value).toBe("12");
    await input.setValue("abc");
    await input.trigger("change");
    expect(input.element.value).toBe("12");
    await get("shop-window__stepper-up").trigger("click");
    expect(input.element.value).toBe("12");
    await input.setValue("0");
    await input.trigger("blur");
    expect(input.element.value).toBe("1");
    await get("shop-window__stepper-down").trigger("click");
    expect(input.element.value).toBe("1");
  });

  it("buying three potions for 艾拉 sends exactly one shop.buy naming her and shows the labelled remaining purse", async () => {
    mountWindow({
      itemHoldings: SHOP_HOLDINGS_POTION,
      services: {
        ...SHOP_SERVICES_SAMPLE,
        shop: {
          ...SHOP_SERVICES_SAMPLE.shop,
          stock: SHOP_SERVICES_SAMPLE.shop.stock.map((r) => (r.item_key === "potion_heal" ? { ...r, buy_copper: 40 } : r)),
        },
      },
    });
    await get("shop-window__quantity").setValue("3");
    expect(get("shop-window__total").text()).toBe("120");
    expect(get("shop-window__remaining").text()).toBe("剩餘 1,120 銅");
    expect(get("shop-window__purse").text()).toBe("1,240 銅");
    expect(get("action-bar__btn--trade").text()).toBe("買給艾拉");
    await get("action-bar__btn--trade").trigger("click");
    expect(wrapper.emitted("trade")).toEqual([
      [{ action_id: "shop.buy", payload: { item_key: "potion_heal", quantity: 3, recipient_id: SHOP_ELLA_ID } }],
    ]);
  });

  it("selling two rusty swords for 卡恩 sends one shop.sell naming him and shows no buy price", async () => {
    mountWindow({
      services: SHOP_SERVICES_SELLER_SAMPLE,
      party: SHOP_PARTY_SELLER_SAMPLE,
      itemHoldings: SHOP_HOLDINGS_SELL,
      initialTab: "sell",
    });
    expect(get("shop-window__list-title").text()).toBe("卡恩可出售的物品");
    const sword = row("rusty_sword");
    expect(sword.get('[data-testid="shop-rows__held"]').text()).toBe("持有 2");
    expect(sword.get('[data-testid="shop-rows__price"]').text()).toContain("45");
    expect(sword.find('[data-testid="shop-rows__fact"]').exists()).toBe(false);
    await get("shop-window__quantity").setValue("2");
    expect(get("shop-window__total").text()).toBe("90");
    expect(get("shop-window__remaining").text()).toBe("剩餘 1,330 銅");
    expect(get("shop-window").text()).not.toContain("售價");
    await get("action-bar__btn--trade").trigger("click");
    expect(wrapper.emitted("trade")).toEqual([
      [{ action_id: "shop.sell", payload: { item_key: "rusty_sword", quantity: 2, seller_id: SHOP_KAHN_ID } }],
    ]);
  });

  it("an asymmetric configured pair keeps the 購買 view on its own price and totals", async () => {
    const services = SHOP_SERVICES_ASYMMETRIC_BUY;
    mountWindow({ services, itemHoldings: SHOP_HOLDINGS_POTION });
    expect(Protocol.validateServicesPanel(services)).toEqual(services);
    // Every rendered price is the row's own buy field and its label; the
    // potion's sell value is one complete price no row publishes here.
    expect(priceTexts()).toEqual(services.shop.stock.map((r) => `售價${r.buy_copper}`));
    expect(priceValues()).not.toContain(POTION_SELL_COPPER);
    expect(row("potion_heal").get('[data-testid="shop-rows__price"]').text()).toBe(
      `售價${POTION_BUY_COPPER}`,
    );
    await get("shop-window__quantity").setValue("3");
    expect(get("shop-window__total").text()).toBe("24");
    expect(get("shop-window__remaining").text()).toBe("剩餘 1,216 銅");
    expect(get("action-bar__btn--trade").text()).toBe("買給艾拉");
    await get("action-bar__btn--trade").trigger("click");
    expect(wrapper.emitted("trade")).toEqual([
      [{ action_id: "shop.buy", payload: { item_key: "potion_heal", quantity: 3, recipient_id: SHOP_ELLA_ID } }],
    ]);
  });

  it("an asymmetric configured pair keeps the 出售 view on its own price and proceeds", async () => {
    const services = SHOP_SERVICES_ASYMMETRIC_SELL;
    mountWindow({
      services,
      party: SHOP_PARTY_SELLER_SAMPLE,
      itemHoldings: SHOP_HOLDINGS_ASYMMETRIC_SELL,
      initialTab: "sell",
    });
    expect(Protocol.validateServicesPanel(services)).toEqual(services);
    expect(Protocol.validateItemHoldingsPanel(SHOP_HOLDINGS_ASYMMETRIC_SELL)).toEqual(
      SHOP_HOLDINGS_ASYMMETRIC_SELL,
    );
    expect(priceTexts()).toEqual(services.shop.sellable.map((r) => `賣價${r.sell_copper}`));
    expect(priceValues()).not.toContain(POTION_BUY_COPPER);
    expect(row("potion_heal").get('[data-testid="shop-rows__price"]').text()).toBe(
      `賣價${POTION_SELL_COPPER}`,
    );
    expect(get("shop-window__quantity").element.value).toBe("1");
    expect(get("shop-window__total").text()).toBe("6");
    expect(get("shop-window__remaining").text()).toBe("剩餘 1,246 銅");
    await get("action-bar__btn--trade").trigger("click");
    expect(wrapper.emitted("trade")).toEqual([
      [{ action_id: "shop.sell", payload: { item_key: "potion_heal", quantity: 1, seller_id: SHOP_KAHN_ID } }],
    ]);
  });

  it("a disabled descriptor keeps its committed reason, offers no stepper and sends nothing", async () => {
    mountWindow({
      services: SHOP_SERVICES_SELLER_SAMPLE,
      party: SHOP_PARTY_SELLER_SAMPLE,
      itemHoldings: { ...SHOP_HOLDINGS_SELL, item_key: "iron_buckler" },
      initialTab: "sell",
    });
    expect(find("shop-window__stepper").exists()).toBe(false);
    expect(get("action-bar__reason").text()).toBe("商店收購上限已滿。");
    await get("action-bar__btn--trade").trigger("click");
    expect(wrapper.emitted("trade")).toBeUndefined();
  });

  it("a closed shop shows only its state and the committed closed reason on every control", async () => {
    mountWindow({ services: SHOP_SERVICES_CLOSED_SAMPLE });
    expect(wrapper.text()).toContain("已打烊");
    const reason = get("action-bar__reason");
    expect(reason.text()).toBe("商店目前沒有營業。");
    expect(reason.attributes("data-reason-code")).toBe("closed");
    expect(get("action-bar__btn--trade").attributes("aria-disabled")).toBe("true");
    await get("action-bar__btn--trade").trigger("click");
    expect(wrapper.emitted("trade")).toBeUndefined();
    expect(wrapper.text()).not.toMatch(/營業時間|開門|打烊時/);
  });

  it("states the committed ordinary refusal without changing the rows", async () => {
    mountWindow({ itemHoldings: SHOP_HOLDINGS_POTION });
    const before = get("shop-rows").html();
    await wrapper.setProps({ tradeNotice: { code: "insufficient_funds", message: "你的銅幣不足。" } });
    expect(get("shop-rows").html()).toBe(before);
    const reason = get("action-bar__reason");
    expect(reason.text()).toBe("你的銅幣不足。");
    expect(reason.attributes("data-reason-code")).toBe("insufficient_funds");
    // The refusal belongs to that trade: another row drops it.
    await wrapper.setProps({ pendingItemKey: "steel_shortsword" });
    expect(wrapper.emitted("clear-notice")).toHaveLength(1);
  });

  it("trading is off while the rail and the rows name different members", async () => {
    mountWindow({ itemHoldings: SHOP_HOLDINGS_POTION, party: { ...SHOP_PARTY_SAMPLE, viewed_member_id: SHOP_KAHN_ID } });
    expect(get("action-bar__btn--trade").attributes("aria-disabled")).toBe("true");
  });

  it("an unavailable services panel or no shop renders only its state, no rows or purse", () => {
    mountWindow({ services: SERVICES_PANEL_UNAVAILABLE_SAMPLE });
    expect(get("shop-window__unavailable").text()).toBe("服務選單目前無法顯示");
    expect(find("shop-rows").exists()).toBe(false);
    expect(find("shop-window__purse").exists()).toBe(false);
    wrapper.unmount();
    mountWindow({ services: SERVICES_PANEL_MINIMAL_SAMPLE });
    expect(find("shop-window__absent").exists()).toBe(true);
    expect(find("shop-rows").exists()).toBe(false);
  });

  it("explains no rules: no rule prose in any state", async () => {
    for (const props of [{}, { itemHoldings: SHOP_HOLDINGS_POTION }, { services: SHOP_SERVICES_CLOSED_SAMPLE }]) {
      mountWindow(props);
      expect(wrapper.text()).not.toMatch(/規則|一半|半價|附身時|才能|只能|說明/);
      wrapper.unmount();
    }
    wrapper = undefined;
  });
});

describe("shop-window-model", () => {
  it("reads committed quantity bounds only", () => {
    expect(quantityBounds({ quantity: { min: 1, max: 3 } })).toEqual({ min: 1, max: 3 });
    expect(quantityBounds({ quantity: null })).toBe(null);
    expect(quantityBounds({ quantity: { min: 2, max: 1 } })).toBe(null);
  });

  it("clamps typed values and falls back for non-integers", () => {
    const b = { min: 1, max: 5 };
    expect(clampQuantity("9", b)).toBe(5);
    expect(clampQuantity("0", b)).toBe(1);
    expect(clampQuantity("", b, 3)).toBe(3);
    expect(clampQuantity("2.5", b, 4)).toBe(4);
    expect(clampQuantity("1e1", b)).toBe(5);
  });

  it("states deltas with shape prefixes and keeps reason codes as data", () => {
    expect(deltaFacts(null)).toEqual({ kind: "none" });
    expect(deltaFacts({ equippable: false, reason: "accessory_slots_full" })).toEqual({ kind: "blocked", code: "accessory_slots_full" });
    expect(deltaFacts({ equippable: true, changes: [] })).toEqual({ kind: "same" });
    expect(deltaFacts({ equippable: true, changes: [{ key: "agility", label: "敏捷", amount: -2 }] }).changes[0].text).toBe("▼ 敏捷 −2");
  });

  it("previews the remaining purse from committed integers only", () => {
    expect(tradePreview(1240, 40, 3, "buy")).toEqual({ total: 120, remaining: 1120 });
    expect(tradePreview(1240, 45, 2, "sell")).toEqual({ total: 90, remaining: 1330 });
    expect(tradePreview(null, 45, 2, "sell")).toEqual({ total: 90, remaining: null });
    expect(tradePreview(1240, null, 2, "buy")).toBe(null);
  });
});
