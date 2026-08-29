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
    // 主手 is filled: the square cell carries only its fixed symbol and
    // caption — the committed name reads in the 裝備描述 column beside the
    // grid (realign-inventory-drawer-layout).
    expect(w.get('[data-testid="equipment-doll__slot--weapon_main"]').text()).not.toContain("短劍 · 拾遺");
    expect(w.get('[data-testid="equipment-doll__description-row--weapon_main"]').text()).toContain("短劍 · 拾遺");
    expect(w.find('[data-testid="equipment-doll__slot-empty--weapon_main"]').exists()).toBe(false);
  });

  it("titles the section 裝備 with the 真值 · 偽裝不影響 tag (realign-inventory-drawer-layout)", () => {
    const w = mountDoll();
    // The mock's tracked section heading replaces the old `裝備人偶` title.
    expect(w.get('[data-testid="equipment-doll__title"]').text()).toBe("裝備真值 · 偽裝不影響");
    expect(w.get('[data-testid="equipment-doll__title-tag"]').text()).toBe("真值 · 偽裝不影響");
    expect(w.text()).not.toContain("裝備人偶");
  });

  it("renders the 裝備描述 column with one entry per primary row grouped by slot label", () => {
    const w = mountDoll({ character: characterWith([
      { slot: "weapon_main", item_key: "short_sword_lost", display_name: "短劍 · 拾遺" },
      { slot: "armor", item_key: "leather_armor", display_name: "皮甲" },
      { slot: "accessory", item_key: "fog_talisman", display_name: "霧隱護符" },
      { slot: "accessory", item_key: "speed_charm", display_name: "迅捷護符" },
    ]) });
    const description = w.get('[data-testid="equipment-doll__description"]');
    expect(description.get('[data-testid="equipment-doll__description-row--weapon_main"]').text()).toBe("主手 · 短劍 · 拾遺");
    expect(description.get('[data-testid="equipment-doll__description-row--armor"]').text()).toBe("盔甲 · 皮甲");
    // 副手 carries no committed row → no description entry is invented.
    expect(description.find('[data-testid="equipment-doll__description-row--weapon_off"]').exists()).toBe(false);
    // Every accessory row renders in the description column's accessory
    // group, under the 飾品 label.
    const accessoryGroup = description.get('[data-testid="equipment-doll__description-row--accessory"]');
    expect(accessoryGroup.text()).toContain("飾品 · 2 件");
    expect(accessoryGroup.get('[data-testid="equipment-doll__accessories"]').exists()).toBe(true);
    expect(accessoryGroup.get('[data-testid="equipment-doll__accessory--fog_talisman"]').text()).toContain("霧隱護符");
    expect(accessoryGroup.get('[data-testid="equipment-doll__accessory--speed_charm"]').text()).toContain("迅捷護符");
  });

  it("renders all five committed accessory rows (the 5-slot accessory cap)", () => {
    const rows = Array.from({ length: 5 }, (_, i) => ({
      slot: "accessory",
      item_key: `acc_cap_${i + 1}`,
      display_name: `護符 ${i + 1}`,
    }));
    const w = mountDoll({ character: characterWith(rows) });
    const group = w.get('[data-testid="equipment-doll__description-row--accessory"]');
    expect(group.text()).toContain("飾品 · 5 件");
    for (let i = 1; i <= 5; i += 1) {
      expect(group.get(`[data-testid="equipment-doll__accessory--acc_cap_${i}"]`).exists()).toBe(true);
    }
  });

  it("renders each committed row exactly once, and rows without an adjustment show no fabricated values", () => {
    // Rows WITHOUT the optional-in-hand-built-props adjustment field (the
    // wire always carries it; a missing/empty string renders no adjustment
    // element) must not fabricate any value.
    const w = mountDoll({ character: characterWith([
      { slot: "weapon_main", item_key: "short_sword_lost", display_name: "短劍 · 拾遺" },
      { slot: "weapon_main", item_key: "light_blade", display_name: "輕劍" },
      { slot: "accessory", item_key: "fog_talisman", display_name: "霧隱護符" },
      { slot: "mount", item_key: "mount_ash", display_name: "灰驛" },
    ]) });
    const text = w.text();
    expect(text).not.toContain("undefined");
    expect(text).not.toContain("NaN");
    // First row → description column; the duplicate and the unrecognised
    // slot → their labelled fallback sections only (no double rendering).
    expect(w.get('[data-testid="equipment-doll__description"]').text()).toContain("短劍 · 拾遺");
    expect(w.get('[data-testid="equipment-doll__description"]').text()).not.toContain("輕劍");
    expect(w.get('[data-testid="equipment-doll__duplicates"]').text()).toContain("輕劍");
    expect(w.get('[data-testid="equipment-doll__description"]').text()).not.toContain("灰驛");
    expect(w.get('[data-testid="equipment-doll__other-slots"]').text()).toContain("灰驛");
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
      schema_version: 5, available: false, kind: "character",
       reason: { code: "no_puppet", message: "你已離開角色" },
      } });
    const reason = w.get('[data-testid="equipment-doll__unavailable"]');
    expect(reason.text()).toBe("你已離開角色");
    expect(w.findAll('[data-testid^="equipment-doll__slot--"]').length).toBe(0);
    expect(w.find('[data-testid="equipment-doll__empty"]').exists()).toBe(false);
  });

  it("renders each fixed slot-role SVG by slot identity (restyle-inventory-equipment-slots)", () => {
    const w = mountDoll({
      character: characterWith([
        { slot: "weapon_main", item_key: "short_sword_lost", display_name: "短劍 · 拾遺", held: 1, equipped: true },
        { slot: "weapon_off", item_key: "dagger_moon", display_name: "月牙短匕", held: 1, equipped: true },
        { slot: "armor", item_key: "leather_armor", display_name: "皮甲", held: 1, equipped: true },
        { slot: "accessory", item_key: "fog_talisman", display_name: "霧隱護符", held: 1, equipped: true },
      ]),
    });
    const mainPath = w.find('[data-testid="equipment-doll__slot--weapon_main"] .equipment-doll__icon path').attributes("d");
    const armorPath = w.find('[data-testid="equipment-doll__slot--armor"] .equipment-doll__icon path').attributes("d");
    const accessoryPath = w.find('[data-testid="equipment-doll__slot--accessory"] .equipment-doll__icon path').attributes("d");
    expect(mainPath).toBe("M5 19 17 7M17 7l-3 1M5 19l2-3");
    expect(armorPath).toBe("M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3Z");
    expect(accessoryPath).toBe("M12 4a5 5 0 1 1 0 10 5 5 0 0 1 0-10zM12 14v6");
    // The off-hand position is the iconless position: no SVG in the square
    // cell; the committed display name reads in the description column.
    const offSlot = w.get('[data-testid="equipment-doll__slot--weapon_off"]');
    expect(offSlot.find("svg").exists()).toBe(false);
    expect(w.get('[data-testid="equipment-doll__description-row--weapon_off"]').text()).toContain("月牙短匕");
  });

  it("selects the slot symbol by slot identity, never by the item (source isolation)", () => {
    const w = mountDoll({
      character: characterWith([
        { slot: "weapon_main", item_key: "shared_blade", display_name: "共用短刃", held: 1 },
        { slot: "armor", item_key: "shared_blade", display_name: "共用短刃", held: 1 },
      ]),
    });
    const mainD = w.find('[data-testid="equipment-doll__slot--weapon_main"] .equipment-doll__icon path').attributes("d");
    const armorD = w.find('[data-testid="equipment-doll__slot--armor"] .equipment-doll__icon path').attributes("d");
    expect(mainD).not.toBe(armorD);
    const w2 = mountDoll({
      character: characterWith([
        { slot: "armor", item_key: "other_plate", display_name: "鋼板甲", held: 1 },
      ]),
    });
    const armorD2 = w2.find('[data-testid="equipment-doll__slot--armor"] .equipment-doll__icon path').attributes("d");
    expect(armorD2).toBe(armorD);
    w2.unmount();
  });

  it("renders the dashed explicit empty state and the accessory summary count (0..3)", () => {
    const w = mountDoll({ character: characterWith([]) });
    for (const slot of ["weapon_main", "weapon_off", "armor"]) {
      const box = w.get(`[data-testid="equipment-doll__slot--${slot}"] .equipment-doll__box`);
      expect(box.classes()).toContain("equipment-doll__box--empty");
      expect(w.get(`[data-testid="equipment-doll__slot-empty--${slot}"]`).text()).toBe("未裝備");
    }
    expect(w.get('[data-testid="equipment-doll__accessory-count"]').text()).toBe("0 件");
    expect(w.find('[data-testid="equipment-doll__accessories"]').exists()).toBe(false);
    // The empty statement renders inside the 裝備描述 column.
    expect(w.get('[data-testid="equipment-doll__description"]').text()).toContain("目前沒有裝備任何物品。");
    expect(w.get('[data-testid="equipment-doll__empty"]').text()).toBe("目前沒有裝備任何物品。");
  });

  it("states the accessory summary count and renders every accessory row", () => {
    const w = mountDoll({
      character: characterWith([
        { slot: "weapon_main", item_key: "short_sword_lost", display_name: "短劍 · 拾遺", held: 1, equipped: true },
        { slot: "accessory", item_key: "fog_talisman", display_name: "霧隱護符", held: 1, equipped: true },
        { slot: "accessory", item_key: "speed_charm", display_name: "迅捷護符", held: 2, equipped: false },
      ]),
    });
    expect(w.get('[data-testid="equipment-doll__accessory-count"]').text()).toBe("2 件");
    const rows = w.findAll('[data-testid^="equipment-doll__accessory--"]');
    expect(rows).toHaveLength(2);
    expect(w.get('[data-testid="equipment-doll__accessories"]').exists()).toBe(true);
    expect(rows[0].text()).toContain("霧隱護符");
    expect(rows[1].text()).toContain("迅捷護符");
  });

  it("renders duplicate singleton rows as labelled overflow rows (no row dropped)", () => {
    const w = mountDoll({
      character: characterWith([
        { slot: "weapon_main", item_key: "short_sword_lost", display_name: "短劍 · 拾遺", held: 1, equipped: true },
        { slot: "weapon_main", item_key: "light_blade", display_name: "輕劍", held: 1, equipped: false },
        { slot: "weapon_off", item_key: "dagger_moon", display_name: "月牙短匕", held: 1, equipped: true },
        { slot: "weapon_off", item_key: "bone_knife", display_name: "骨刀", held: 1, equipped: false },
        { slot: "armor", item_key: "leather_armor", display_name: "皮甲", held: 1, equipped: true },
        { slot: "armor", item_key: "steel_plate", display_name: "鋼板甲", held: 1, equipped: false },
      ]),
    });
    // The square grid consumes only the first row per singleton slot: the
    // first row shows in the description column; the cell keeps just its
    // symbol/caption.
    expect(w.get('[data-testid="equipment-doll__description-row--weapon_main"]').text()).toContain("短劍 · 拾遺");
    const offSlot = w.get('[data-testid="equipment-doll__slot--weapon_off"]');
    expect(offSlot.find("svg").exists()).toBe(false);
    expect(w.get('[data-testid="equipment-doll__description-row--weapon_off"]').text()).toContain("月牙短匕");
    expect(w.get('[data-testid="equipment-doll__description-row--armor"]').text()).toContain("皮甲");
    // The duplicate committed rows render as labelled overflow rows.
    const dupes = w.findAll('[data-testid^="equipment-doll__duplicate-row--"]');
    expect(dupes).toHaveLength(3);
    expect(dupes[0].attributes("data-slot")).toBe("weapon_main");
    expect(dupes[0].text()).toContain("輕劍");
    expect(dupes[1].attributes("data-slot")).toBe("weapon_off");
    expect(dupes[1].text()).toContain("骨刀");
    expect(dupes[2].attributes("data-slot")).toBe("armor");
    expect(dupes[2].text()).toContain("鋼板甲");
    expect(w.get('[data-testid="equipment-doll__duplicates"]').exists()).toBe(true);
  });

  it("preserves an unrecognised slot as a labelled row and invents no item presentation", () => {
    const w = mountDoll({
      character: characterWith([
        { slot: "weapon_main", item_key: "short_sword_lost", display_name: "短劍 · 拾遺", held: 1, equipped: true },
        { slot: "mount", item_key: "mount_ash", display_name: "灰驛", held: 1, equipped: false },
      ]),
    });
    const row = w.get('[data-testid="equipment-doll__slot-row--mount"]');
    expect(row.attributes("data-slot")).toBe("mount");
    expect(row.text()).toContain("mount");
    expect(row.text()).toContain("灰驛");
    // No rarity, no stats, no comparison, and no new focusable control.
    expect(w.text()).not.toContain("稀有");
    expect(w.text()).not.toContain("攻擊");
    expect(w.find("button").exists()).toBe(false);
    expect(w.find("a").exists()).toBe(false);
    expect(w.find("input").exists()).toBe(false);
  });
});
