import { h } from "vue";
import EquipmentDoll from "../../components/EquipmentDoll.vue";
import { CHARACTER_PANEL_SAMPLE } from "../fixtures.js";

// EquipmentDoll (H4, webclient-hud-04-reference-drawers, task 6.6): the
// equipment doll. Stories: the doll with every named slot filled, the doll
// with empty slots, the doll with three accessories, and the doll with an
// unrecognised slot key (labelled passthrough, not dropped).

function characterWith(equipment) {
  return { ...CHARACTER_PANEL_SAMPLE, equipment };
}

function filledSlots() {
  return characterWith([
    { slot: "weapon_main", item_key: "short_sword_lost", display_name: "短劍 · 拾遺", held: 1, equipped: true },
    { slot: "weapon_off", item_key: "dagger_moon", display_name: "月牙短匕", held: 1, equipped: true },
    { slot: "armor", item_key: "leather_armor", display_name: "皮甲", held: 1, equipped: true },
  ]);
}

function emptySlots() {
  return characterWith([]);
}

function threeAccessories() {
  return characterWith([
    { slot: "weapon_main", item_key: "short_sword_lost", display_name: "短劍 · 拾遺", held: 1, equipped: true },
    { slot: "accessory", item_key: "fog_talisman", display_name: "霧隱護符", held: 1, equipped: true },
    { slot: "accessory", item_key: "speed_charm", display_name: "迅捷護符", held: 2, equipped: false },
    { slot: "accessory", item_key: "guard_amulet", display_name: "防禦護身", held: 1, equipped: false },
  ]);
}

function unrecognisedSlot() {
  return characterWith([
    { slot: "weapon_main", item_key: "short_sword_lost", display_name: "短劍 · 拾遺", held: 1, equipped: true },
    { slot: "mount", item_key: "mount_ash", display_name: "灰驛", held: 1, equipped: false },
  ]);
}

const renderDoll = (args) => ({
  render: () =>
    h("div", { style: "border: 1px solid var(--ink-700); border-radius: 12px; padding: 12px;" }, [
      h(EquipmentDoll, args),
    ]),
});

export default {
  title: "Data/EquipmentDoll",
  component: EquipmentDoll,
};

export const EverySlotFilled = {
  render: renderDoll,
  args: { character: filledSlots() },
};

export const EmptySlots = {
  render: renderDoll,
  args: { character: emptySlots() },
};

export const ThreeAccessories = {
  render: renderDoll,
  args: { character: threeAccessories() },
};

export const UnrecognisedSlot = {
  render: renderDoll,
  args: { character: unrecognisedSlot() },
};
