import { h, ref } from "vue";
import HudDrawer from "../../components/HudDrawer.vue";
import InventoryPanel from "../../components/InventoryPanel.vue";
import { formatCopper } from "../../components/character-identity.js";
import {
  SERVICES_PANEL_MINIMAL_SAMPLE,
  SERVICES_PANEL_SAMPLE,
  SERVICES_PANEL_UNAVAILABLE_SAMPLE,
  SERVICES_PANEL_PRESENTATION_SAMPLE,
  CHARACTER_PANEL_SAMPLE,
} from "../fixtures.js";

// InventoryPanel (H4, webclient-hud-04-reference-drawers, task 6.6;
// relocate-inventory-drawer-essentials; redesign-inventory-item-grid): the
// 背包 · 裝備 drawer body, shown inside the open shared `HudDrawer` chrome
// (the real drawer width, header icon and wallet subtitle) instead of an
// unframed body. The equipment doll and the single drawer-layer wallet
// were relocated here from the character-status drawer, so the story set
// deterministically covers: filled equipment, empty equipment, the
// character panel's unavailable form, the unknown-slot passthrough, the
// services 32-row ceiling, the services unavailable form, and — since
// redesign-inventory-item-grid — the presentation-backed tile grid (every
// closed icon key and rarity), the neutral unknown-item state, long
// labels, equipped/un-equipped markers, and the keyboard-focused
// inspection shared with pointer hover.

function emptyBag() {
  return {
    ...SERVICES_PANEL_SAMPLE,
    inventory: { rows: [], wallet: 0 },
    pagination: { ...SERVICES_PANEL_SAMPLE.pagination, inventory_total: 0 },
  };
}

function ceilingBag() {
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

// The header wallet subtitle: thousands-grouped integer copper from the
// committed `character` panel (the shared `character-identity.js`
// formatter), blank when the `services` panel is in its unavailable form or
// its inventory section is absent (the bag states its registry-owned reason
// / absent message and fabricates no wallet), or when the `character` panel
// is missing/unavailable (never a zero).
function walletSubtitle(services, character) {
  const servicesAvailable = !!services && services.available !== false;
  const inventorySection = services ? (services.inventory ?? null) : null;
  if (!servicesAvailable || inventorySection === null) {
    return "";
  }
  if (!character || character.available === false) {
    return "";
  }
  const wallet = character.wallet;
  if (typeof wallet !== "number" || !Number.isInteger(wallet) || wallet < 0) {
    return "";
  }
  return `錢袋 ${formatCopper(wallet)} 銅`;
}

// The component story title must be the first title key in the file, because
// the component-coverage gate keys off the first match. Placing the default
// export before the render helper guarantees the gate sees the manifest name.
export default {
  title: "World/InventoryPanel",
  component: InventoryPanel,
};

function renderDrawer(args) {
  const character = args.character ?? null;
  // The drawer opens on mount; Escape / the close control / the scrim each
  // emit `close`, which flips the reactive open state so the drawer visibly
  // closes and the drawer's focus trap restores focus to the opener.
  const open = ref(true);
  return {
    render: () =>
      h(
        "div",
        { style: "position: relative; width: 100%; height: 520px; background: var(--ink-950); overflow: hidden;" },
        [
          h(
            HudDrawer,
            {
              open: open.value,
              title: "背包 · 裝備",
              subtitle: walletSubtitle(args.services, character),
              icon: "inventory",
              drawerKey: "inventory",
              onClose: () => {
                open.value = false;
              },
            },
            {
              default: () =>
                h(InventoryPanel, {
                  services: args.services,
                  character: character,
                }),
            },
          ),
        ],
      ),
  };
}

// The presentation-backed bag (redesign-inventory-item-grid): every row
// carries committed `presentation` metadata, so the grid renders mapped
// local SVGs, per-rarity borders, and the inspector's kind/rarity words.
// The row set covers all nine closed icon keys and all five rarities.
export const AllRarities = {
  render: renderDrawer,
  args: { services: SERVICES_PANEL_PRESENTATION_SAMPLE, character: CHARACTER_PANEL_SAMPLE },
};

// Unknown-item bag: every row has `presentation: null` — each tile shows
// the neutral unknown-item icon, the visible 未知 marker, the row's real
// name, and its held count, with no inferred icon, kind, rarity, summary,
// statistic, or action control.
function unknownBag() {
  const rows = [
    { item_key: "mystery_relic", display_name: "遺物", held: 1, equipped: false, presentation: null },
    { item_key: "stray_coin_pouch", display_name: "零錢袋", held: 6, equipped: false, presentation: null },
  ];
  return {
    ...SERVICES_PANEL_SAMPLE,
    inventory: { rows, wallet: 3240 },
    pagination: { ...SERVICES_PANEL_SAMPLE.pagination, inventory_total: 2 },
  };
}

export const UnknownItem = {
  render: renderDrawer,
  args: { services: unknownBag(), character: CHARACTER_PANEL_SAMPLE },
};

// Long localised labels: a long CJK display name wraps in the unknown tile
// and the inspector without truncating the accessible name.
function longLabelBag() {
  const rows = [
    {
      item_key: "ferry_lantern_commission_token",
      display_name: "渡河燈油補充委託信物",
      held: 1,
      equipped: false,
      presentation: null,
    },
  ];
  return {
    ...SERVICES_PANEL_SAMPLE,
    inventory: { rows, wallet: 3240 },
    pagination: { ...SERVICES_PANEL_SAMPLE.pagination, inventory_total: 1 },
  };
}

export const LongLabels = {
  render: renderDrawer,
  args: { services: longLabelBag(), character: CHARACTER_PANEL_SAMPLE },
};

// Equipped and un-equipped items: the non-colour equipped check marker
// renders only on equipped rows; the inspector spells the equipped state.
function equippedBag() {
  const rows = [
    {
      item_key: "plain_sword",
      display_name: "普通劍",
      held: 1,
      equipped: true,
      presentation: { kind: "weapon", icon_key: "weapon", rarity: "common", summary: "鍛鐵打造的普通劍。" },
    },
    {
      item_key: "healing_potion",
      display_name: "治療藥水",
      held: 3,
      equipped: false,
      presentation: { kind: "potion", icon_key: "potion", rarity: "rare", summary: "盛裝於小瓶中的治療藥水。" },
    },
  ];
  return {
    ...SERVICES_PANEL_SAMPLE,
    inventory: { rows, wallet: 3240 },
    pagination: { ...SERVICES_PANEL_SAMPLE.pagination, inventory_total: 2 },
  };
}

export const EquippedAndUnequipped = {
  render: renderDrawer,
  args: { services: equippedBag(), character: CHARACTER_PANEL_SAMPLE },
};

// Focused inspection: the `play` function moves keyboard focus to a
// presentation-backed tile so the story deterministically shows the
// keyboard-equivalent inspector state (the hover path shows the same
// committed content).
export const FocusedInspection = {
  render: renderDrawer,
  args: { services: SERVICES_PANEL_PRESENTATION_SAMPLE, character: CHARACTER_PANEL_SAMPLE },
  play: async ({ canvasElement }) => {
    const tile = canvasElement.querySelector('[data-testid="inventory-panel__tile--healing_potion"]');
    if (tile) {
      tile.focus();
      await new Promise((resolve) => setTimeout(resolve, 60));
    }
  },
};

// Filled equipment: the CHARACTER_PANEL_SAMPLE's own equipment rows
// (主手 short_sword_lost, armor 皮甲, 飾品 霧隱護符) render in the doll.
export const MixedBag = {
  render: renderDrawer,
  args: { services: SERVICES_PANEL_SAMPLE, character: CHARACTER_PANEL_SAMPLE },
};

// Empty equipment: the committed character panel carries no equipment rows,
// so the doll shows its explicit empty slot states.
export const EmptyBag = {
  render: renderDrawer,
  args: {
    services: emptyBag(),
    character: { ...CHARACTER_PANEL_SAMPLE, equipment: [] },
  },
};

// The 32-row ceiling: the worded ceiling note renders; the doll still
// composes before the held rows.
export const CeilingBag = {
  render: renderDrawer,
  args: { services: ceilingBag(), character: CHARACTER_PANEL_SAMPLE },
};

// The services panel's inventory section is absent: only the absent message
// renders, and the doll is not mounted (no fabricated equipment state).
export const SectionAbsent = {
  render: renderDrawer,
  args: { services: SERVICES_PANEL_MINIMAL_SAMPLE, character: CHARACTER_PANEL_SAMPLE },
};

// The services panel commits its unavailable form: only the registry-owned
// reason renders, and the header renders no wallet subtitle (the bag
// fabricates no wallet while it is unavailable — no balance, no zero).
export const Unavailable = {
  render: renderDrawer,
  args: { services: SERVICES_PANEL_UNAVAILABLE_SAMPLE, character: CHARACTER_PANEL_SAMPLE },
};

// A character panel in its registry-owned unavailable form: the held rows
// still render and the doll shows its registered unavailable message; the
// header subtitle stays blank (no balance, no zero).
export const CharacterUnavailable = {
  render: renderDrawer,
  args: {
    services: SERVICES_PANEL_SAMPLE,
    character: {
      schema_version: 4,
      available: false,
      kind: "character",
      reason: { code: "no_puppet", message: "你已離開角色" },
    },
  },
};

// An unrecognised server-authored slot key: the doll's labelled passthrough
// renders the `mount` row instead of dropping it.
export const UnknownSlotEquipment = {
  render: renderDrawer,
  args: {
    services: SERVICES_PANEL_SAMPLE,
    character: {
      ...CHARACTER_PANEL_SAMPLE,
      equipment: [
        { slot: "weapon_main", item_key: "short_sword_lost", display_name: "短劍 · 拾遺" },
        { slot: "mount", item_key: "mount_ash", display_name: "灰驛" },
      ],
    },
  },
};

// Multi-accessory equipment (restyle-inventory-equipment-slots): the doll's
// 飾品 summary cell states the committed count and the retained detail group
// lists every accessory row inside the composed drawer.
function multiAccessoryCharacter() {
  return {
    ...CHARACTER_PANEL_SAMPLE,
    equipment: [
      { slot: "weapon_main", item_key: "short_sword_lost", display_name: "短劍 · 拾遺" },
      { slot: "armor", item_key: "leather_armor", display_name: "皮甲" },
      { slot: "accessory", item_key: "fog_talisman", display_name: "霧隱護符" },
      { slot: "accessory", item_key: "speed_charm", display_name: "迅捷護符" },
      { slot: "accessory", item_key: "guard_amulet", display_name: "防禦護身" },
    ],
  };
}

export const MultiAccessoryEquipment = {
  render: renderDrawer,
  args: { services: SERVICES_PANEL_SAMPLE, character: multiAccessoryCharacter() },
};

// Long equipment display names wrap below the square cells in the drawer
// (the 1280x720 / 1440x900 drawer composition reviewed with agent-browser).
function longEquipmentLabelCharacter() {
  return {
    ...CHARACTER_PANEL_SAMPLE,
    equipment: [
      { slot: "weapon_main", item_key: "ferry_lantern_commission_blade", display_name: "渡河燈油補充委託信劍" },
      { slot: "weapon_off", item_key: "ferry_lantern_commission_dagger", display_name: "渡河燈油補充委託短匕" },
    ],
  };
}

export const LongEquipmentLabels = {
  render: renderDrawer,
  args: { services: SERVICES_PANEL_SAMPLE, character: longEquipmentLabelCharacter() },
};
