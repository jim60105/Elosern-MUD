import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import ShopPanel from "../../components/ShopPanel.vue";
import {
  SERVICES_PANEL_MINIMAL_SAMPLE,
  SERVICES_PANEL_SAMPLE,
  SERVICES_PANEL_SHOP_ROWS_SAMPLE,
  SERVICES_PANEL_UNAVAILABLE_SAMPLE,
} from "../../stories/fixtures.js";

describe("ShopPanel (B4 world / services family)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountPanel(props = {}) {
    wrapper = mount(ShopPanel, {
      props: {
        services: SERVICES_PANEL_SAMPLE,
        ...props,
      },
    });
    return wrapper;
  }

  it("renders the open/closed status line from the payload's shop.open", () => {
    const open = mountPanel().get('[data-testid="shop-panel__open"]');
    expect(open.text()).toBe("營業中");
    expect(open.attributes("data-open")).toBe("true");

    const closedServices = {
      ...SERVICES_PANEL_SAMPLE,
      shop: { ...SERVICES_PANEL_SAMPLE.shop, open: false },
    };
    const closed = mountPanel({ services: closedServices }).get('[data-testid="shop-panel__open"]');
    expect(closed.text()).toBe("已打烊");
    expect(closed.attributes("data-open")).toBe("false");
  });

  it("renders every stock row with the payload's own values (no invented numbers)", () => {
    const w = mountPanel();
    const sword = w.get('[data-testid="shop-panel__stock--item_iron_sword"]');
    expect(sword.find(".shop-row__name").text()).toBe("鐵劍");
    // One price per row kind: a stock row shows the buy price only.
    const swordPrices = sword.findAll(".shop-row__price");
    expect(swordPrices.map((p) => p.text())).toEqual(["120 銅"]);
    // Stock level cell renders "stock / max_stock" (no invented defaults).
    expect(sword.find(".shop-row__stock").text()).toBe("庫存 8 / 24");
    expect(sword.find(".shop-row__icon").attributes("data-rarity")).toBe("uncommon");

    const potion = w.get('[data-testid="shop-panel__stock--item_heal_potion"]');
    expect(potion.find(".shop-row__name").text()).toBe("治療劑");
    expect(potion.findAll(".shop-row__price").map((p) => p.text())).toEqual(["45 銅"]);
    expect(potion.find(".shop-row__stock").text()).toBe("庫存 30 / 30");

    expect(w.get('[data-testid="shop-panel__stock--item_iron_sword"]').exists()).toBe(true);
    expect(w.get('[data-testid="shop-panel__stock--item_heal_potion"]').exists()).toBe(true);
  });

  it("shows the disabled buy reason text and a non-clickable control", () => {
    const w = mountPanel();
    const row = w.get('[data-testid="shop-panel__stock--item_heal_potion"]');
    const reason = row.find(".shop-row__reason");
    expect(reason.text()).toBe("錢包餘額不足");
    const buy = row.find(".shop-row__buy");
    expect(buy.attributes("disabled")).toBeDefined();

    const swordRow = w.get('[data-testid="shop-panel__stock--item_iron_sword"]');
    expect(swordRow.find(".shop-row__reason").exists()).toBe(false);
    const swordBuy = swordRow.find(".shop-row__buy");
    expect(swordBuy.attributes("disabled")).toBeUndefined();
  });

  it("emits a shop.buy intent with the payload's item_key and within action quantity bounds", async () => {
    const w = mountPanel();
    const row = w.get('[data-testid="shop-panel__stock--item_iron_sword"]');

    const qty = row.find("input.shop-row__qty");
    // The quantity control's bounds come from the payload's own action.
    expect(qty.attributes("min")).toBe("1");
    expect(qty.attributes("max")).toBe("8");
    expect(qty.element.value).toBe("1");

    qty.setValue(3);
    await row.find(".shop-row__buy").trigger("click");
    expect(w.emitted("buy")).toEqual([
      [{
        action_id: "shop.buy",
        payload: { item_key: "item_iron_sword", quantity: 3, recipient_id: 7 },
      }],
    ]);

   // Out-of-bounds quantities set without a change event are not emitted (no invented values).
   qty.element.value = "9";
   await qty.trigger("input");
    await row.find(".shop-row__buy").trigger("click");
    expect(w.emitted("buy")).toEqual([
      [{
        action_id: "shop.buy",
        payload: { item_key: "item_iron_sword", quantity: 3, recipient_id: 7 },
      }],
    ]);
  });

  it("focusing a stock row quantity entry marks that row with services-quantity and services-quantity-value", async () => {
   const w = mountPanel();
   const row = w.get('[data-testid="shop-panel__stock--item_iron_sword"]');
   const qty = row.find("input.shop-row__qty");

   expect(w.find('[data-testid="services-quantity"]').exists()).toBe(false);
   expect(w.find('[data-testid="services-quantity-value"]').exists()).toBe(false);

   await qty.trigger("focusin");
   expect(w.find('[data-testid="services-quantity"]').exists()).toBe(true);
   expect(w.find('[data-testid="services-quantity-value"]').exists()).toBe(true);
   expect(row.find('[data-testid="services-quantity"]').exists()).toBe(true);
  });

  it("clamps quantity on change above max to max and below min or empty to min", async () => {
   const w = mountPanel();
   const row = w.get('[data-testid="shop-panel__stock--item_iron_sword"]');
   const qty = row.find("input.shop-row__qty");
   expect(qty.attributes("min")).toBe("1");
   expect(qty.attributes("max")).toBe("8");

   // Change above max (e.g. 10 -> clamps to 8)
   await qty.setValue(10);
   await qty.trigger("change");
   expect(qty.element.value).toBe("8");

   // Change below min (e.g. 0 or -1 -> clamps to 1)
   await qty.setValue(0);
   await qty.trigger("change");
   expect(qty.element.value).toBe("1");

   // Empty or non-integer -> clamps to min (1)
   await qty.setValue("");
   await qty.trigger("change");
   expect(qty.element.value).toBe("1");
  });

  it("buyNow and sellNow emit nothing for an out-of-bounds value set without a change event", async () => {
   const w = mountPanel();
   const stockRow = w.get('[data-testid="shop-panel__stock--item_iron_sword"]');
   const stockQty = stockRow.find("input.shop-row__qty");

   // Setting an out-of-bounds value without a change event (input only)
   stockQty.element.value = "99";
   await stockQty.trigger("input");
   await stockRow.find(".shop-row__buy").trigger("click");
   expect(w.emitted("buy")).toBeUndefined();

   // Same for sellNow
   const sellRow = w.get('[data-testid="shop-panel__sellable--item_herb_moon"]');
   const sellQty = sellRow.find("input.shop-row__qty");
   sellQty.element.value = "99";
   await sellQty.trigger("input");
   await sellRow.find(".shop-row__sell").trigger("click");
   expect(w.emitted("sell")).toBeUndefined();
  });

  it("tab order reaches every enabled row's entry and button, and disabled button stays rendered with reason", () => {
   const w = mountPanel();
   const stockRows = w.findAll('.shop-panel__section:first-of-type .shop-row');
   expect(stockRows.length).toBeGreaterThan(0);

   for (const row of stockRows) {
     const input = row.find("input.shop-row__qty");
     const button = row.find("button.shop-row__buy");
     expect(input.exists()).toBe(true);
     expect(button.exists()).toBe(true);
     expect(input.attributes("tabindex")).not.toBe("-1");
     if (button.attributes("disabled") !== undefined) {
       const reason = row.find(".shop-row__reason");
       expect(reason.exists()).toBe(true);
       expect(reason.text().length).toBeGreaterThan(0);
     } else {
       expect(button.attributes("tabindex")).not.toBe("-1");
     }
   }
  });

  it("renders the sellable row and emits a shop.sell intent with payload values", async () => {
    const w = mountPanel();
    const sellable = w.get('[data-testid="shop-panel__sellable--item_herb_moon"]');
    expect(sellable.find(".shop-row__name").text()).toBe("月光草");
    // One price per row kind: a sellable row shows the sell price only.
    expect(sellable.findAll(".shop-row__price").map((p) => p.text())).toEqual(["25 銅"]);
    expect(sellable.find(".shop-row__held").text()).toBe("可售 3");

    const qty = sellable.find("input.shop-row__qty");
    expect(qty.attributes("min")).toBe("1");
    expect(qty.attributes("max")).toBe("3");
    qty.setValue(2);
    await sellable.find(".shop-row__sell").trigger("click");
    expect(w.emitted("sell")).toEqual([
      [{
        action_id: "shop.sell",
        payload: { item_key: "item_herb_moon", quantity: 2, seller_id: 7 },
      }],
    ]);
   // Above the held-count bound set without a change event: not emitted.
   qty.element.value = "4";
   await qty.trigger("input");
    await sellable.find(".shop-row__sell").trigger("click");
    expect(w.emitted("sell")).toEqual([
      [{
        action_id: "shop.sell",
        payload: { item_key: "item_herb_moon", quantity: 2, seller_id: 7 },
      }],
    ]);
  });

  it("names shop.member_id as recipient and seller, never the controlled figure", async () => {
    const services = SERVICES_PANEL_SHOP_ROWS_SAMPLE;
    const w = mountPanel({ services, memberName: "艾拉" });
    expect(w.get('[data-testid="shop-panel__stock-title"]').text()).toBe("為艾拉挑選");
    expect(w.get('[data-testid="shop-panel__sellable-title"]').text()).toBe("艾拉可出售的物品");
    await w.get('[data-testid="shop-panel__stock--steel_shortsword"]').find(".shop-row__buy").trigger("click");
    await w.get('[data-testid="shop-panel__sellable--potion_heal"]').find(".shop-row__sell").trigger("click");
    expect(w.emitted("buy")[0][0].payload).toEqual({ item_key: "steel_shortsword", quantity: 1, recipient_id: 102 });
    expect(w.emitted("sell")[0][0].payload).toEqual({ item_key: "potion_heal", quantity: 1, seller_id: 102 });
  });

  it("emits nothing when shop.member_id is not a positive safe integer", async () => {
    // A malformed member id never invents a member: both trades stay silent.
    for (const memberId of [null, 0, -1, 1.5, "7"]) {
      const services = { ...SERVICES_PANEL_SAMPLE, shop: { ...SERVICES_PANEL_SAMPLE.shop, member_id: memberId } };
      const w = mountPanel({ services });
      const stockRow = w.get('[data-testid="shop-panel__stock--item_iron_sword"]');
      await stockRow.find(".shop-row__buy").trigger("click");
      expect(w.emitted("buy")).toBeUndefined();
      const sellRow = w.get('[data-testid="shop-panel__sellable--item_herb_moon"]');
      await sellRow.find(".shop-row__sell").trigger("click");
      expect(w.emitted("sell")).toBeUndefined();
      w.unmount();
      wrapper = null;
    }
  });

  it("renders the viewed member's server delta or held count, never computing either", () => {
    const w = mountPanel({ services: SERVICES_PANEL_SHOP_ROWS_SAMPLE });
    const facts = (key) => w.get(`[data-testid="shop-panel__stock--${key}"]`);
    const deltas = (key) => facts(key).findAll('[data-testid="shop-row__delta"]').map((d) => d.text());
    expect(deltas("steel_shortsword")).toEqual(["▲ 攻擊 +6"]);
    // A mixed swap keeps the shape prefix and a true minus sign.
    expect(deltas("iron_longsword")).toEqual(["▲ 攻擊 +4", "▼ 敏捷 −2"]);
    expect(facts("iron_longsword").findAll(".shop-row__delta.is-down")).toHaveLength(1);
    expect(deltas("moonstone_ring")).toEqual(["無法裝備"]);
    // The worn copy compares as no change and still shows the held count.
    expect(deltas("birch_staff")).toEqual(["±0"]);
    expect(facts("birch_staff").get('[data-testid="shop-row__held"]').text()).toBe("持有 1");
    // A consumable shows the held count and no delta.
    expect(deltas("potion_heal")).toEqual([]);
    expect(facts("potion_heal").get('[data-testid="shop-row__held"]').text()).toBe("持有 2");
    expect(facts("steel_shortsword").find('[data-testid="shop-row__held"]').exists()).toBe(false);
    // Sold out is spelled, not only dimmed.
    expect(facts("shortbow").find(".shop-row__stock").text()).toBe("售完");
    expect(facts("shortbow").classes()).toContain("is-sold-out");
    // The sellable list's count is the unequipped count, labelled apart.
    expect(w.get('[data-testid="shop-panel__sellable--potion_heal"]').find(".shop-row__held").text()).toBe("可售 2");
  });

  it("re-defaults every quantity entry when the services panel is replaced", async () => {
    const w = mountPanel({ services: SERVICES_PANEL_SHOP_ROWS_SAMPLE });
    const input = () => w.get('[data-testid="shop-panel__stock--potion_heal"]').find("input.shop-row__qty");
    await input().setValue(5);
    expect(input().element.value).toBe("5");
    await w.setProps({ services: { ...SERVICES_PANEL_SHOP_ROWS_SAMPLE } });
    expect(input().element.value).toBe("1");
  });

  it("omits the wallet line (H4 task 7.1: the wallet now lives in CharacterStatusDrawer — the single wallet rendering)", () => {
    // The full and minimal payloads both carry a wallet value in
    // `player.wallet_copper`, but ShopPanel no longer renders it.
    expect(mountPanel().find('[data-testid="shop-panel__wallet"]').exists()).toBe(false);
    expect(mountPanel({ services: SERVICES_PANEL_MINIMAL_SAMPLE }).find('[data-testid="shop-panel__wallet"]').exists()).toBe(false);
  });

  it("section absent: only the honest wallet line and the absence marker (no invented stock/sellable rows)", () => {
    const w = mountPanel({ services: SERVICES_PANEL_MINIMAL_SAMPLE });
    const absent = w.get('[data-testid="shop-panel__shop-absent"]');
    expect(absent.text()).toBe("目前沒有營業中的商店");
    expect(w.find('[data-testid="shop-panel__stock--item_iron_sword"]').exists()).toBe(false);
    expect(w.find('[data-testid="shop-panel__stock--item_heal_potion"]').exists()).toBe(false);
    expect(w.find('[data-testid="shop-panel__sellable--item_herb_moon"]').exists()).toBe(false);
    expect(w.find('[data-testid="shop-panel__open"]').exists()).toBe(false);
  });

  it("unavailable services: renders only the registry-owned reason, no sections or invented values", () => {
    const w = mountPanel({ services: SERVICES_PANEL_UNAVAILABLE_SAMPLE });
    const reason = w.get('[data-testid="shop-panel__unavailable"]');
    expect(reason.attributes("data-reason-code")).toBe("services_unavailable");
    expect(reason.text()).toBe("服務選單目前無法顯示");
    expect(w.find('[data-testid="shop-panel__open"]').exists()).toBe(false);
    expect(w.find('[data-testid="shop-panel__shop-absent"]').exists()).toBe(false);
    expect(w.find('[data-testid="shop-panel__stock--item_iron_sword"]').exists()).toBe(false);
    expect(w.find('[data-testid="shop-panel__wallet"]').exists()).toBe(false);
  });
});
