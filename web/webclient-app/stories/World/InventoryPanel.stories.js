import { h } from "vue";
import HudDrawer from "../../components/HudDrawer.vue";
import InventoryPanel from "../../components/InventoryPanel.vue";
import { formatCopper } from "../../components/character-identity.js";
import {
  SERVICES_PANEL_MINIMAL_SAMPLE,
  SERVICES_PANEL_SAMPLE,
  SERVICES_PANEL_UNAVAILABLE_SAMPLE,
  CHARACTER_PANEL_SAMPLE,
} from "../fixtures.js";

// InventoryPanel (H4, webclient-hud-04-reference-drawers, task 6.6;
// relocate-inventory-drawer-essentials): the 背包 · 裝備 drawer body, shown
// inside the open shared `HudDrawer` chrome (the real drawer width, header
// icon and wallet subtitle) instead of an unframed body. The equipment
// doll and the single drawer-layer wallet were relocated here from the
// character-status drawer, so the story set deterministically covers: filled
// equipment, empty equipment, the character panel's unavailable form, the
// unknown-slot passthrough, the services 32-row ceiling, and the services
// unavailable form.

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
  return {
    render: () =>
      h(
        "div",
        { style: "position: relative; width: 100%; height: 520px; background: var(--ink-950); overflow: hidden;" },
        [
          h(
            HudDrawer,
            {
              open: true,
              title: "背包 · 裝備",
              subtitle: walletSubtitle(args.services, character),
              icon: "inventory",
              drawerKey: "inventory",
              onClose: () => {},
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
