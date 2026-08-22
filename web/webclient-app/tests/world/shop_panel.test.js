import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import ShopPanel from "../../components/ShopPanel.vue";
import {
  SERVICES_PANEL_MINIMAL_SAMPLE,
  SERVICES_PANEL_SAMPLE,
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
    const swordPrices = sword.findAll(".shop-row__price");
    expect(swordPrices[0].text()).toBe("購買 120 銅");
    expect(swordPrices[1].text()).toBe("出賣 80 銅");
    // Stock level cell renders "stock / max_stock" (no invented defaults).
    expect(sword.find(".shop-row__stock").text()).toBe("8 / 24");

    const potion = w.get('[data-testid="shop-panel__stock--item_heal_potion"]');
    expect(potion.find(".shop-row__name").text()).toBe("治療劑");
    const potionPrices = potion.findAll(".shop-row__price");
    expect(potionPrices[0].text()).toBe("購買 45 銅");
    expect(potionPrices[1].text()).toBe("出賣 30 銅");
    expect(potion.find(".shop-row__stock").text()).toBe("30 / 30");

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
      [{ action_id: "shop.buy", payload: { item_key: "item_iron_sword", quantity: 3 } }],
    ]);

    // Out-of-bounds quantities are not emitted (no invented values).
    qty.setValue(9);
    await row.find(".shop-row__buy").trigger("click");
    expect(w.emitted("buy")).toEqual([
      [{ action_id: "shop.buy", payload: { item_key: "item_iron_sword", quantity: 3 } }],
    ]);
  });

  it("renders the sellable row and emits a shop.sell intent with payload values", async () => {
    const w = mountPanel();
    const sellable = w.get('[data-testid="shop-panel__sellable--item_herb_moon"]');
    expect(sellable.find(".shop-row__name").text()).toBe("月光草");
    expect(sellable.findAll(".shop-row__price")[0].text()).toBe("出賣 25 銅");
    expect(sellable.find(".shop-row__held").text()).toBe("3");

    const qty = sellable.find("input.shop-row__qty");
    expect(qty.attributes("min")).toBe("1");
    expect(qty.attributes("max")).toBe("3");
    qty.setValue(2);
    await sellable.find(".shop-row__sell").trigger("click");
    expect(w.emitted("sell")).toEqual([
      [{ action_id: "shop.sell", payload: { item_key: "item_herb_moon", quantity: 2 } }],
    ]);
    // Above the held-count bound: not emitted.
    qty.setValue(4);
    await sellable.find(".shop-row__sell").trigger("click");
    expect(w.emitted("sell")).toEqual([
      [{ action_id: "shop.sell", payload: { item_key: "item_herb_moon", quantity: 2 } }],
    ]);
  });

  it("renders the wallet line in integer copper with thousands separators (no float money)", () => {
    expect(mountPanel().get('[data-testid="shop-panel__wallet"]').text()).toBe("3,240 銅");
    expect(mountPanel({ services: SERVICES_PANEL_MINIMAL_SAMPLE }).get('[data-testid="shop-panel__wallet"]').text()).toBe("0 銅");
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
