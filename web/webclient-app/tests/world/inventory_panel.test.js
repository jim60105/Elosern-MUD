import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import InventoryPanel from "../../components/InventoryPanel.vue";
import {
  SERVICES_PANEL_MINIMAL_SAMPLE,
  SERVICES_PANEL_SAMPLE,
  SERVICES_PANEL_UNAVAILABLE_SAMPLE,
} from "../../stories/fixtures.js";

describe("InventoryPanel (H4 背包 · 裝備 drawer body)", () => {
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

  function ceilingServices() {
    const rows = Array.from({ length: 32 }, (_, i) => ({
      item_key: `item_ceiling_${i + 1}`,
      display_name: `物品 ${i + 1}`,
      held: 1,
      equipped: i < 3,
      presentation: null,
    }));
    return {
      ...SERVICES_PANEL_SAMPLE,
      inventory: { rows, wallet: 3240 },
      pagination: { ...SERVICES_PANEL_SAMPLE.pagination, inventory_total: 32 },
    };
  }

  it("renders the full bag (no equipped filter) with an equipped marker on equipped rows", () => {
    const w = mountPanel();
    // All three bag rows render (the non-equipped 治療劑 now shows too).
    expect(w.get('[data-testid="inventory-panel__row--item_iron_sword"]').exists()).toBe(true);
    expect(w.get('[data-testid="inventory-panel__row--item_leather_armor"]').exists()).toBe(true);
    expect(w.get('[data-testid="inventory-panel__row--item_heal_potion"]').exists()).toBe(true);

    // The equipped marker renders only on the equipped rows.
    const sword = w.get('[data-testid="inventory-panel__row--item_iron_sword"]');
    expect(sword.text()).toContain("裝備中");
    const potion = w.get('[data-testid="inventory-panel__row--item_heal_potion"]');
    expect(potion.text()).not.toContain("裝備中");
  });

  it("renders no field the payload lacks (only display_name / held / equipped)", () => {
    const w = mountPanel();
    // No rarity border, no per-item stats line, no use/consume/equip control.
    const row = w.get('[data-testid="inventory-panel__row--item_iron_sword"]');
    // The row carries exactly the payload's fields: name + held (+ marker).
    expect(row.text()).toContain("鐵劍");
    expect(row.text()).toContain("1");
    expect(w.text()).not.toContain("稀有");
    expect(w.find("input").exists()).toBe(false);
    expect(w.find("button").exists()).toBe(false);
  });

  it("states the 32-row ceiling in words only at the bound; no total otherwise", () => {
    // Below the ceiling: no ceiling note.
    const w = mountPanel();
    expect(w.find('[data-testid="inventory-panel__ceiling"]').exists()).toBe(false);
    // At the ceiling (32 rows): the worded ceiling note renders.
    const wCeiling = mountPanel({ services: ceilingServices() });
    const ceiling = wCeiling.get('[data-testid="inventory-panel__ceiling"]');
    expect(ceiling.exists()).toBe(true);
    expect(ceiling.text()).toContain("32");
  });

  it("section absent: renders the honest empty state, no invented bag contents", () => {
    const w = mountPanel({ services: SERVICES_PANEL_MINIMAL_SAMPLE });
    const absent = w.get('[data-testid="inventory-panel__absent"]');
    expect(absent.text()).toBe("背包目前是空的。");
    expect(w.find('[data-testid="inventory-panel__row--item_iron_sword"]').exists()).toBe(false);
    expect(w.find('[data-testid="inventory-panel__ceiling"]').exists()).toBe(false);
  });

  it("unavailable services: renders only the registry-owned reason, no fabricated wallet, row or slot", () => {
    const w = mountPanel({ services: SERVICES_PANEL_UNAVAILABLE_SAMPLE });
    const reason = w.get('[data-testid="inventory-panel__unavailable"]');
    expect(reason.text()).toBe("服務選單目前無法顯示");
    expect(w.find('[data-testid="inventory-panel__absent"]').exists()).toBe(false);
    expect(w.find('[data-testid="inventory-panel__ceiling"]').exists()).toBe(false);
    expect(w.findAll('[data-testid^="inventory-panel__row--"]')).toHaveLength(0);
  });
});
