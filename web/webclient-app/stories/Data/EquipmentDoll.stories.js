import { h } from "vue";
import EquipmentDoll from "../../components/EquipmentDoll.vue";
import { CHARACTER_PANEL_SAMPLE } from "../fixtures.js";

// EquipmentDoll (H4, webclient-hud-04-reference-drawers, task 6.6;
// restyle-inventory-equipment-slots): the equipment doll in the binding
// design's compact paper-doll slot language. Stories: every named slot
// filled, each singleton slot occupied on its own, empty slots, zero
// through three accessories (the summary cell states the count), the
// unrecognised slot key (labelled passthrough, not dropped), long display
// names wrapping below the square cells, and the registry-owned unavailable
// character form.

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

function mainHandOnly() {
  return characterWith([
    { slot: "weapon_main", item_key: "short_sword_lost", display_name: "短劍 · 拾遺", held: 1, equipped: true },
  ]);
}

function offHandOnly() {
  return characterWith([
    { slot: "weapon_off", item_key: "dagger_moon", display_name: "月牙短匕", held: 1, equipped: true },
  ]);
}

function armorOnly() {
  return characterWith([
    { slot: "armor", item_key: "leather_armor", display_name: "皮甲", held: 1, equipped: true },
  ]);
}

function zeroAccessories() {
  // The committed panel carries a main-hand item but no accessory rows, so
  // the 飾品 summary cell states the zero count (never a fabricated row).
  return characterWith([
    { slot: "weapon_main", item_key: "short_sword_lost", display_name: "短劍 · 拾遺", held: 1, equipped: true },
  ]);
}

function oneAccessory() {
  return characterWith([
    { slot: "weapon_main", item_key: "short_sword_lost", display_name: "短劍 · 拾遺", held: 1, equipped: true },
    { slot: "accessory", item_key: "fog_talisman", display_name: "霧隱護符", held: 1, equipped: true },
  ]);
}

function twoAccessories() {
  return characterWith([
    { slot: "weapon_main", item_key: "short_sword_lost", display_name: "短劍 · 拾遺", held: 1, equipped: true },
    { slot: "accessory", item_key: "fog_talisman", display_name: "霧隱護符", held: 1, equipped: true },
    { slot: "accessory", item_key: "speed_charm", display_name: "迅捷護符", held: 2, equipped: false },
  ]);
}

function longLabels() {
  return characterWith([
    { slot: "weapon_main", item_key: "ferry_lantern_commission_blade", display_name: "渡河燈油補充委託信劍", held: 1, equipped: true },
    { slot: "accessory", item_key: "ferry_lantern_commission_token", display_name: "渡河燈油補充委託信物", held: 1, equipped: true },
  ]);
}

function unavailableCharacter() {
  return {
    schema_version: 4,
    available: false,
    kind: "character",
    reason: { code: "no_puppet", message: "你已離開角色" },
  };
}

function duplicateSingletonSlots() {
  // Two committed rows for the same singleton slot: the square grid shows
  // the first row and the duplicate renders as a labelled overflow row.
  return characterWith([
    { slot: "weapon_main", item_key: "short_sword_lost", display_name: "短劍 · 拾遺", held: 1, equipped: true },
    { slot: "weapon_main", item_key: "light_blade", display_name: "輕劍", held: 1, equipped: false },
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

// Each occupied singleton slot on its own: the fixed slot-role symbol (or
// the iconless off-hand position) with the committed display name below the
// square cell.
export const MainHandOnly = {
  render: renderDoll,
  args: { character: mainHandOnly() },
};

export const OffHandOnly = {
  render: renderDoll,
  args: { character: offHandOnly() },
};

export const ArmorOnly = {
  render: renderDoll,
  args: { character: armorOnly() },
};

// The accessory summary cell states the committed count across 0..3
// accessories, while the retained detail group lists every row.
export const ZeroAccessories = {
  render: renderDoll,
  args: { character: zeroAccessories() },
};

export const OneAccessory = {
  render: renderDoll,
  args: { character: oneAccessory() },
};

export const TwoAccessories = {
  render: renderDoll,
  args: { character: twoAccessories() },
};

// Long localised display names wrap below the square cells without expanding
// them or overflowing horizontally.
export const LongLabels = {
  render: renderDoll,
  args: { character: longLabels() },
};

// The registry-owned unavailable form: only the reason renders; no square
// positions, no fabricated slots.
export const Unavailable = {
  render: renderDoll,
  args: { character: unavailableCharacter() },
};

// Duplicate singleton rows: the square grid consumes the first row per
// slot; the extra committed row renders as a labelled overflow row
// (the character panel validator accepts duplicate slot rows).
export const DuplicateSingletonSlots = {
  render: renderDoll,
  args: { character: duplicateSingletonSlots() },
};

// The mock's `.doll` row (realign-inventory-drawer-layout): the square slot
// grid beside the 裝備描述 column listing the committed rows under their
// slot labels — singleton first rows plus the accessory group.
function describedEquipment() {
  return characterWith([
    { slot: "weapon_main", item_key: "short_sword_lost", display_name: "短劍 · 拾遺" },
    { slot: "weapon_off", item_key: "dagger_moon", display_name: "月牙短匕" },
    { slot: "armor", item_key: "leather_armor", display_name: "皮甲" },
    { slot: "accessory", item_key: "fog_talisman", display_name: "霧隱護符" },
  ]);
}

export const WithEquipmentDescription = {
  render: renderDoll,
  args: { character: describedEquipment() },
};
