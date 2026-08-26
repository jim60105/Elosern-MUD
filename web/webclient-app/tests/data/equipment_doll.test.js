import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import EquipmentDoll from "../../components/EquipmentDoll.vue";
import { CHARACTER_PANEL_SAMPLE } from "../../stories/fixtures.js";

describe("EquipmentDoll (H4 equipment doll)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function characterWith(equipment) {
    return { ...CHARACTER_PANEL_SAMPLE, equipment };
  }

  function mountDoll(props = {}) {
    wrapper = mount(EquipmentDoll, {
      props: {
        character: CHARACTER_PANEL_SAMPLE,
        ...props,
      },
    });
    return wrapper;
  }

  it("renders an explicit empty state for each named slot box when the slot is unfilled", () => {
    const w = mountDoll({ character: characterWith([
      { slot: "weapon_main", item_key: "short_sword_lost", display_name: "短劍 · 拾遺", held: 1, equipped: true },
    ]) });
    // 副手 and 盔甲 are unfilled → their boxes show the empty state.
    expect(w.get('[data-testid="equipment-doll__slot-empty--weapon_off"]').text()).toBe("未裝備");
    expect(w.get('[data-testid="equipment-doll__slot-empty--armor"]').text()).toBe("未裝備");
    // 主手 is filled → shows the item name.
    expect(w.get('[data-testid="equipment-doll__slot--weapon_main"]').text()).toContain("短劍 · 拾遺");
    expect(w.find('[data-testid="equipment-doll__slot-empty--weapon_main"]').exists()).toBe(false);
  });

  it("renders the accessory group for 0..3 accessory rows", () => {
    const w = mountDoll({ character: characterWith([
      { slot: "weapon_main", item_key: "short_sword_lost", display_name: "短劍 · 拾遺", held: 1, equipped: true },
      { slot: "accessory", item_key: "fog_talisman", display_name: "霧隱護符", held: 1, equipped: true },
      { slot: "accessory", item_key: "speed_charm", display_name: "迅捷護符", held: 2, equipped: false },
       { slot: "accessory", item_key: "guard_amulet", display_name: "防禦護身", held: 1, equipped: false },
     ]) });
    const accessories = w.findAll('[data-testid^="equipment-doll__accessory--"]');
    expect(accessories).toHaveLength(3);
    expect(w.get('[data-testid="equipment-doll__accessories"]').exists()).toBe(true);
  });

  it("renders an unrecognised slot key as a labelled passthrough row, not dropped", () => {
    const w = mountDoll({ character: characterWith([
      { slot: "weapon_main", item_key: "short_sword_lost", display_name: "短劍 · 拾遺", held: 1, equipped: true },
       { slot: "mount", item_key: "mount_ash", display_name: "灰驛", held: 1, equipped: false },
     ]) });
    // The unrecognised `mount` slot renders a labelled passthrough row.
    const row = w.get('[data-testid="equipment-doll__slot-row--mount"]');
    expect(row.exists()).toBe(true);
    expect(row.attributes("data-slot")).toBe("mount");
    expect(row.text()).toContain("灰驛");
    // The named-slot boxes still render; the unrecognised slot is not folded
    // into a named box.
    expect(w.get('[data-testid="equipment-doll__slot--weapon_main"]').exists()).toBe(true);
  });

  it("renders no field the payload lacks (no rarity border, stats line, or equip control)", () => {
    const w = mountDoll();
    // No use/consume/equip control, no rarity, no per-item stats.
    expect(w.find("button").exists()).toBe(false);
    expect(w.text()).not.toContain("稀有");
  });

  it("unavailable character: renders the registry-owned reason, no fabricated slots", () => {
    const w = mountDoll({ character: {
      schema_version: 3, available: false, kind: "character",
       reason: { code: "no_puppet", message: "你已離開角色" },
     } });
    const reason = w.get('[data-testid="equipment-doll__unavailable"]');
    expect(reason.text()).toBe("你已離開角色");
    expect(w.findAll('[data-testid^="equipment-doll__slot--"]').length).toBe(0);
    expect(w.find('[data-testid="equipment-doll__empty"]').exists()).toBe(false);
  });
});
