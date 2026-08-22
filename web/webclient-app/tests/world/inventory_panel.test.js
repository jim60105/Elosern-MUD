import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import InventoryPanel from "../../components/InventoryPanel.vue";
import {
  SERVICES_PANEL_MINIMAL_SAMPLE,
  SERVICES_PANEL_SAMPLE,
  SERVICES_PANEL_UNAVAILABLE_SAMPLE,
} from "../../stories/fixtures.js";

describe("InventoryPanel (B4 world / services family)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountPanel(props = {}) {
    wrapper = mount(InventoryPanel, {
      props: {
        services: SERVICES_PANEL_SAMPLE,
        ...props,
      },
    });
    return wrapper;
  }

  it("renders only equipped rows (no full bag)", () => {
    const w = mountPanel();
    // The two equipped rows each render their own row testid; the bag row does not.
    expect(w.get('[data-testid="inventory-panel__row--item_iron_sword"]').exists()).toBe(true);
    expect(w.get('[data-testid="inventory-panel__row--item_leather_armor"]').exists()).toBe(true);

    const sword = w.get('[data-testid="inventory-panel__row--item_iron_sword"]');
    expect(sword.find('[data-testid="inventory-panel__row-name--item_iron_sword"]').text()).toBe("鐵劍");
    expect(sword.find('[data-testid="inventory-panel__row-held--item_iron_sword"]').text()).toBe("1");

    const armor = w.get('[data-testid="inventory-panel__row--item_leather_armor"]');
    expect(armor.find('[data-testid="inventory-panel__row-name--item_leather_armor"]').text()).toBe("皮甲");
    expect(armor.find('[data-testid="inventory-panel__row-held--item_leather_armor"]').text()).toBe("1");

    // The non-equipped bag row (治療劑) must not render: the full bag is
    // deferred (no backing read model).
    expect(w.find('[data-testid="inventory-panel__row--item_heal_potion"]').exists()).toBe(false);
    expect(w.text()).not.toContain("治療劑");
  });

  it("renders the wallet from inventory.wallet in integer copper (no float money)", () => {
    expect(mountPanel().get('[data-testid="inventory-panel__wallet"]').text()).toBe("3,240 銅");
  });

  it("section absent: renders the honest empty state, no invented bag contents", () => {
    const w = mountPanel({ services: SERVICES_PANEL_MINIMAL_SAMPLE });
    const absent = w.get('[data-testid="inventory-panel__absent"]');
    expect(absent.text()).toBe("尚未有裝備物品");
    expect(w.find('[data-testid="inventory-panel__row--item_iron_sword"]').exists()).toBe(false);
    expect(w.find('[data-testid="inventory-panel__row--item_leather_armor"]').exists()).toBe(false);
    expect(w.find('[data-testid="inventory-panel__row--item_heal_potion"]').exists()).toBe(false);
    expect(w.find('[data-testid="inventory-panel__wallet"]').exists()).toBe(false);
  });

  it("unavailable services: renders only the registry-owned reason, no invented rows or wallet value", () => {
    const w = mountPanel({ services: SERVICES_PANEL_UNAVAILABLE_SAMPLE });
    const reason = w.get('[data-testid="inventory-panel__unavailable"]');
    expect(reason.text()).toBe("服務選單目前無法顯示");
    expect(w.find('[data-testid="inventory-panel__absent"]').exists()).toBe(false);
    expect(w.find('[data-testid="inventory-panel__wallet"]').exists()).toBe(false);
    expect(w.findAll('[data-testid^="inventory-panel__row--"]')).toHaveLength(0);
  });
});
