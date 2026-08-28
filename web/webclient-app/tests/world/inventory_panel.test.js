import { readFileSync } from "node:fs";
import { join } from "node:path";
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { afterEach, describe, expect, it } from "vitest";
import InventoryPanel from "../../components/InventoryPanel.vue";
import {
  SERVICES_PANEL_MINIMAL_SAMPLE,
  SERVICES_PANEL_SAMPLE,
  SERVICES_PANEL_UNAVAILABLE_SAMPLE,
  SERVICES_PANEL_PRESENTATION_SAMPLE,
  CHARACTER_PANEL_SAMPLE,
} from "../../stories/fixtures.js";

const CHARACTER_UNAVAILABLE = {
  schema_version: 4,
  available: false,
  kind: "character",
  reason: { code: "no_puppet", message: "你已離開角色" },
};

describe("InventoryPanel (redesign-inventory-item-grid: the held-item tile grid)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountPanel(props = {}) {
    // Attach to a host in the document so `.focus()` updates
    // `document.activeElement` (the drawer's focus-trap contract relies on it).
    const host = document.createElement("div");
    document.body.appendChild(host);
    wrapper = mount(InventoryPanel, {
      attachTo: host,
      props: {
        services: SERVICES_PANEL_SAMPLE,
        character: CHARACTER_PANEL_SAMPLE,
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

  it("renders every committed row as a native-button tile with a lower-corner held count", () => {
    const w = mountPanel({ services: SERVICES_PANEL_PRESENTATION_SAMPLE });
    const tiles = w.findAll('[data-testid^="inventory-panel__tile--"]');
    expect(tiles).toHaveLength(9);
    for (const tile of tiles) {
      const key = tile.element.dataset.key;
      const count = w.get(`[data-testid="inventory-panel__count--${key}"]`).text();
      const row = SERVICES_PANEL_PRESENTATION_SAMPLE.inventory.rows.find((r) => r.item_key === key);
      expect(count).toBe(String(row.held));
      expect(tile.element.tagName.toLowerCase()).toBe("button");
    }
  });

  it("renders the equipped check marker only on equipped rows (non-colour state)", () => {
    const w = mountPanel({ services: SERVICES_PANEL_PRESENTATION_SAMPLE });
    // Three equipped rows (plain_sword, leather_armor, mist_amulet).
    expect(w.get('[data-testid="inventory-panel__equipped--plain_sword"]').exists()).toBe(true);
    expect(w.get('[data-testid="inventory-panel__equipped--leather_armor"]').exists()).toBe(true);
    expect(w.get('[data-testid="inventory-panel__equipped--mist_amulet"]').exists()).toBe(true);
    expect(w.find('[data-testid="inventory-panel__equipped--healing_potion"]').exists()).toBe(false);
  });

  it("drives the per-rarity border treatment from committed row metadata", () => {
    const w = mountPanel({ services: SERVICES_PANEL_PRESENTATION_SAMPLE });
    expect(w.get('[data-testid="inventory-panel__tile--meal"]').attributes("data-rarity")).toBe("common");
    expect(w.get('[data-testid="inventory-panel__tile--leather_armor"]').attributes("data-rarity")).toBe("uncommon");
    expect(w.get('[data-testid="inventory-panel__tile--healing_potion"]').attributes("data-rarity")).toBe("rare");
    expect(w.get('[data-testid="inventory-panel__tile--mist_amulet"]').attributes("data-rarity")).toBe("epic");
    expect(w.get('[data-testid="inventory-panel__tile--travel_pack"]').attributes("data-rarity")).toBe("legendary");
  });

  it("renders the neutral unknown-item tile for presentation: null without inference", () => {
    const w = mountPanel();
    const tile = w.get('[data-testid="inventory-panel__tile--item_iron_sword"]');
    expect(tile.attributes("data-rarity")).toBe("unknown");
    expect(tile.attributes("data-unknown")).toBe("true");
    // The unknown marker, the real name, and the held count render; no kind,
    // rarity, or summary is invented from the item key or display name.
    expect(w.get('[data-testid="inventory-panel__unknown--item_iron_sword"]').text()).toBe("未知");
    expect(w.get('[data-testid="inventory-panel__name--item_iron_sword"]').text()).toBe("鐵劍");
    expect(w.get('[data-testid="inventory-panel__count--item_iron_sword"]').text()).toBe("1");
  });

  it("shows the inspector with the identical committed content for hover and focus", async () => {
    const w = mountPanel({ services: SERVICES_PANEL_PRESENTATION_SAMPLE });
    const potionTile = w.get('[data-testid="inventory-panel__tile--healing_potion"]');
    const row = SERVICES_PANEL_PRESENTATION_SAMPLE.inventory.rows.find((r) => r.item_key === "healing_potion");

    // Pointer hover path.
    potionTile.trigger("pointerenter");
    await nextTick();
    const inspector = w.get('[data-testid="inventory-panel__inspector"]');
    const hoverContent = {
      name: w.get('[data-testid="inventory-panel__inspector-name"]').text(),
      rarity: w.get('[data-testid="inventory-panel__inspector-rarity"]').text(),
      kind: w.get('[data-testid="inventory-panel__inspector-kind"]').text(),
      summary: w.get('[data-testid="inventory-panel__inspector-summary"]').text(),
      held: w.get('[data-testid="inventory-panel__inspector-held"]').text(),
      equipped: w.get('[data-testid="inventory-panel__inspector-equipped"]').text(),
    };
    expect(hoverContent).toEqual({
      name: row.display_name,
      rarity: "稀有",
      kind: "藥水",
      summary: row.presentation.summary,
      held: String(row.held),
      equipped: "未裝備",
    });

    // Pointer leave with focus elsewhere clears the inspector.
    potionTile.trigger("pointerleave");
    await nextTick();
    expect(w.find('[data-testid="inventory-panel__inspector"]').exists()).toBe(false);

    // Keyboard focus path: the same committed content renders again.
    potionTile.element.focus();
    await nextTick();
    const focusContent = {
      name: w.get('[data-testid="inventory-panel__inspector-name"]').text(),
      rarity: w.get('[data-testid="inventory-panel__inspector-rarity"]').text(),
      kind: w.get('[data-testid="inventory-panel__inspector-kind"]').text(),
      summary: w.get('[data-testid="inventory-panel__inspector-summary"]').text(),
      held: w.get('[data-testid="inventory-panel__inspector-held"]').text(),
      equipped: w.get('[data-testid="inventory-panel__inspector-equipped"]').text(),
    };
    expect(focusContent).toEqual(hoverContent);
  });

  it("links the selected tile to the inspector via aria-describedby and clears it when absent", async () => {
    const w = mountPanel({ services: SERVICES_PANEL_PRESENTATION_SAMPLE });
    const potionTile = w.get('[data-testid="inventory-panel__tile--healing_potion"]');
    expect(potionTile.attributes("aria-describedby")).toBeUndefined();
    potionTile.element.focus();
    await nextTick();
    expect(potionTile.attributes("aria-describedby")).toBe("inventory-panel-inspector");
    // Blur to a non-tile element: the inspector hides and the link clears.
    const other = document.createElement("button");
    document.body.appendChild(other);
    other.focus();
    await nextTick();
    expect(w.find('[data-testid="inventory-panel__inspector"]').exists()).toBe(false);
    expect(potionTile.attributes("aria-describedby")).toBeUndefined();
  });

  it("offers no state-changing control (no use/consume/equip/drag/sort/filter/search)", async () => {
    const w = mountPanel({ services: SERVICES_PANEL_PRESENTATION_SAMPLE });
    // The only buttons are the item tiles themselves; no input or select.
    const buttons = w.findAll("button");
    expect(buttons).toHaveLength(9);
    expect(w.find("input").exists()).toBe(false);
    expect(w.find("select").exists()).toBe(false);
    // The inspector is non-interactive: no control lives inside it.
    w.get('[data-testid="inventory-panel__tile--healing_potion"]').element.focus();
    await nextTick();
    const inspector = w.get('[data-testid="inventory-panel__inspector"]');
    expect(inspector.find("button").exists()).toBe(false);
    expect(inspector.find("input").exists()).toBe(false);
    expect(inspector.attributes("role")).toBe("tooltip");
  });

  it("resets the local selection when the committed panel data is replaced", async () => {
    const w = mountPanel({ services: SERVICES_PANEL_PRESENTATION_SAMPLE });
    const potionTile = w.get('[data-testid="inventory-panel__tile--healing_potion"]');
    potionTile.element.focus();
    await nextTick();
    expect(w.find('[data-testid="inventory-panel__inspector"]').exists()).toBe(true);
    // Replace the panel with a payload that no longer contains the focused row.
    await w.setProps({ services: SERVICES_PANEL_SAMPLE });
    await nextTick();
    expect(w.find('[data-testid="inventory-panel__inspector"]').exists()).toBe(false);
    expect(w.find('[data-testid="inventory-panel__tile--healing_potion"]').exists()).toBe(true);
    expect(w.find('[data-testid="inventory-panel__tile--item_heal_potion"]').exists()).toBe(true);
  });

  it("states the 32-row ceiling in words only at the bound; no total otherwise", () => {
    const w = mountPanel();
    expect(w.find('[data-testid="inventory-panel__ceiling"]').exists()).toBe(false);
    const wCeiling = mountPanel({ services: ceilingServices() });
    const ceiling = wCeiling.get('[data-testid="inventory-panel__ceiling"]');
    expect(ceiling.exists()).toBe(true);
    expect(ceiling.text()).toContain("32");
    expect(wCeiling.findAll('[data-testid^="inventory-panel__tile--"]').length).toBe(32);
  });

  it("section absent: renders the registry-owned absence message, no invented bag contents", () => {
    const w = mountPanel({ services: SERVICES_PANEL_MINIMAL_SAMPLE });
    const absent = w.get('[data-testid="inventory-panel__absent"]');
    expect(absent.text()).toBe("背包目前是空的。");
    expect(w.find('[data-testid^="inventory-panel__tile--"]').exists()).toBe(false);
    expect(w.find('[data-testid="inventory-panel__ceiling"]').exists()).toBe(false);
  });

  it("unavailable services: renders only the registry-owned reason, no fabricated wallet, row or slot", () => {
    const w = mountPanel({ services: SERVICES_PANEL_UNAVAILABLE_SAMPLE });
    const reason = w.get('[data-testid="inventory-panel__unavailable"]');
    expect(reason.text()).toBe("服務選單目前無法顯示");
    expect(w.find('[data-testid="inventory-panel__absent"]').exists()).toBe(false);
    expect(w.find('[data-testid="inventory-panel__ceiling"]').exists()).toBe(false);
    expect(w.findAll('[data-testid^="inventory-panel__tile--"]').length).toBe(0);
  });

  it("composes the equipment doll before the held-item grid", () => {
    const w = mountPanel({ services: SERVICES_PANEL_PRESENTATION_SAMPLE });
    const doll = w.get('[data-testid="equipment-doll"]').element;
    const grid = w.get('[data-testid="inventory-panel__grid"]').element;
    const pos = doll.compareDocumentPosition(grid);
    expect(pos & Node.DOCUMENT_POSITION_FOLLOWING).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    expect(w.get('[data-testid="equipment-doll__slot--weapon_main"]').text()).toContain("短劍 · 拾遺");
  });

  it("renders no equipment doll when the character panel is unavailable; the held grid remains", () => {
    const w = mountPanel({ character: CHARACTER_UNAVAILABLE, services: SERVICES_PANEL_PRESENTATION_SAMPLE });
    expect(w.findAll('[data-testid^="inventory-panel__tile--"]').length).toBe(9);
    expect(w.get('[data-testid="equipment-doll__unavailable"]').text()).toBe("你已離開角色");
  });

  it("renders no doll (and no fabricated empty slots) when the character panel is missing", () => {
    const w = mountPanel({ character: null, services: SERVICES_PANEL_PRESENTATION_SAMPLE });
    expect(w.findAll('[data-testid^="inventory-panel__tile--"]').length).toBe(9);
    expect(w.find('[data-testid="equipment-doll"]').exists()).toBe(false);
  });

  it("gates its transitions through the motion tokens (reduced motion is instant)", () => {
    // The cell outline and inspector transitions/animation use the existing
    // `--motion-fast` token; the reduced-motion override sets the token to
    // 1ms, making every transition effectively instant.
    const source = readFileSync(
      join(process.cwd(), "web/webclient-app/components/InventoryPanel.vue"),
      "utf-8",
    );
    expect(source).toContain("var(--motion-fast)");
    expect(source).toContain("var(--ease-standard)");
    expect(source).toContain("inventory-inspector-in");
  });
});
