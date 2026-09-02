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

// The drawer-layer wallet figure (the same validation `AppClient` applies):
// the committed `character` panel's integer copper when the `services` panel
// is available and its inventory section present, else null. It feeds both
// the head subtitle (thousands-grouped via the shared `character-identity.js`
// formatter) and the body's `金錢` row, so the two story renderings can
// never disagree (unavailable forms render neither — never a zero).
function walletCopper(services, character) {
  const servicesAvailable = !!services && services.available !== false;
  const inventorySection = services ? (services.inventory ?? null) : null;
  if (!servicesAvailable || inventorySection === null) {
    return null;
  }
  if (!character || character.available === false) {
    return null;
  }
  const wallet = character.wallet;
  if (typeof wallet !== "number" || !Number.isInteger(wallet) || wallet < 0) {
    return null;
  }
  return wallet;
}

function walletSubtitle(services, character) {
  const wallet = walletCopper(services, character);
  return wallet === null ? "" : `錢袋 ${formatCopper(wallet)} 銅`;
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
                  wallet: walletCopper(args.services, character),
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

// The render-equipment-breakdown-webclient joined-adjustment state: the
// bag carries a row sharing the character panel's `knight_platemail`
// item_key (the inspector prints the SAME server string the doll shows)
// beside a bag-only 繩索 row (no character row → no adjustment line). The
// play function focuses the plate-mail tile so the story deterministically
// shows the joined line.
function adjustmentBag() {
  const rows = [
    {
      item_key: "knight_platemail",
      display_name: "騎士全套板甲",
      held: 1,
      equipped: true,
      presentation: { kind: "armor", icon_key: "armor", rarity: "rare", summary: "厚重的騎士板甲。" },
    },
    {
      item_key: "loose_rope",
      display_name: "繩索",
      held: 2,
      equipped: false,
      presentation: { kind: "misc", icon_key: "misc", rarity: "common", summary: "一捆結實的麻繩。" },
    },
  ];
  return {
    ...SERVICES_PANEL_SAMPLE,
    inventory: { rows, wallet: 3240 },
    pagination: { ...SERVICES_PANEL_SAMPLE.pagination, inventory_total: 2 },
  };
}

export const JoinedAdjustment = {
  render: renderDrawer,
  args: { services: adjustmentBag(), character: CHARACTER_PANEL_SAMPLE },
  play: async ({ canvasElement }) => {
    const tile = canvasElement.querySelector('[data-testid="inventory-panel__tile--knight_platemail"]');
    if (tile) {
      tile.focus();
      await new Promise((resolve) => setTimeout(resolve, 60));
    }
  },
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
      schema_version: 7,
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

// The mock's three-section stack (realign-inventory-drawer-layout): the
// 裝備 doll with its 裝備描述 column, the 物品 grid tagged with the shipped
// listing size, and the 金錢 section whose single row carries the same
// grouped integer copper the head subtitle renders.
function richWalletCharacter() {
  return {
    ...CHARACTER_PANEL_SAMPLE,
    equipment: [
      { slot: "weapon_main", item_key: "short_sword_lost", display_name: "短劍 · 拾遺" },
      { slot: "armor", item_key: "leather_armor", display_name: "皮甲" },
      { slot: "accessory", item_key: "fog_talisman", display_name: "霧隱護符" },
    ],
    wallet: 1284000,
  };
}

export const WalletSection = {
  render: renderDrawer,
  args: { services: SERVICES_PANEL_PRESENTATION_SAMPLE, character: richWalletCharacter() },
};

// The 金錢 section's absence: the character panel is available but carries
// no committed non-negative integer wallet — neither the head subtitle nor
// the body row renders a balance (never a zero).
export const WalletSectionAbsent = {
  render: renderDrawer,
  args: {
    services: SERVICES_PANEL_SAMPLE,
    character: { ...CHARACTER_PANEL_SAMPLE, wallet: null },
  },
};

// add-inventory-item-actions (task 6.5): the committed row action descriptor
// states. The 使用 tile opens the labelled item-use confirmation on deliberate
// activation (try it in this story); the disabled row spells its committed
// bounded reason in the shared inspector and is aria-disabled; the 裝備 tile
// toggles directly without confirmation; the null-action tile stays
// inspect-only. The panel emits every intent to its parent — the story host
// below records the emitted intent visibly instead of dispatching.
function actionBag() {
  const use = (enabled, reason = null) => ({
    action_id: "inventory.use",
    label: "使用",
    enabled,
    disabled_reason: enabled ? null : reason,
    quantity: null,
  });
  const toggle = (label) => ({
    action_id: "inventory.toggle_equip",
    label,
    enabled: true,
    disabled_reason: null,
    quantity: null,
  });
  const row = (item_key, display_name, held, equipped, presentation, action) => ({
    item_key,
    display_name,
    held,
    equipped,
    presentation,
    action,
  });
  const rows = [
    row("healing_potion", "治療藥水", 3, false,
      { kind: "potion", icon_key: "potion", rarity: "rare", summary: "盛裝於小瓶中的治療藥水。" },
      use(true)),
    row("glut_potion", "過剩藥水", 1, false,
      { kind: "potion", icon_key: "potion", rarity: "common", summary: "體力已滿時派不上用場。" },
      use(false, { code: "hp_full", message: "你的體力已滿。" })),
    row("item_iron_sword", "鐵劍", 1, true,
      { kind: "weapon", icon_key: "weapon", rarity: "uncommon", summary: "尋常鐵劍，輕巧耐用。" },
      toggle("卸下")),
    row("mystery_charm", "未知物品", 1, false, null, null),
  ];
  return {
    ...SERVICES_PANEL_SAMPLE,
    inventory: { rows, wallet: SERVICES_PANEL_SAMPLE.inventory.wallet },
    pagination: { ...SERVICES_PANEL_SAMPLE.pagination, inventory_total: rows.length },
  };
}

export const RowActionStates = {
  render: (args) => {
    const character = args.character ?? null;
    const open = ref(true);
    const lastIntent = ref(null);
    return {
      render: () =>
        h(
          "div",
          { style: "position: relative; width: 100%; height: 560px; background: var(--ink-950); overflow: hidden;" },
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
                    wallet: walletCopper(args.services, character),
                    onUse: (intent) => {
                      lastIntent.value = `use：${intent.payload.item_key}`;
                    },
                    onToggleEquip: (intent) => {
                      lastIntent.value = `${intent.action_id}：${intent.payload.item_key}`;
                    },
                  }),
              },
            ),
            h(
              "p",
              {
                style:
                  "position: absolute; left: 12px; bottom: 8px; right: 12px; color: var(--paper-500); font-size: 12px;",
              },
              lastIntent.value ? `已發出意圖：${lastIntent.value}` : "尚無已發出的背包操作意圖。",
            ),
          ],
        ),
    };
  },
  args: { services: actionBag(), character: CHARACTER_PANEL_SAMPLE },
};

// The accessory ceiling (add-inventory-item-actions): five committed
// accessory rows render in full in the doll's 飾品 group — no truncation,
// and the group label states the committed count.
function accessoryCapCharacter() {
  return {
    ...CHARACTER_PANEL_SAMPLE,
    equipment: [
      { slot: "weapon_main", item_key: "item_iron_sword", display_name: "鐵劍" },
      { slot: "armor", item_key: "item_leather_armor", display_name: "皮甲" },
      { slot: "accessory", item_key: "fog_talisman", display_name: "霧隱護符" },
      { slot: "accessory", item_key: "speed_charm", display_name: "迅捷護符" },
      { slot: "accessory", item_key: "ember_ring", display_name: "餘燼戒指" },
      { slot: "accessory", item_key: "tide_pendant", display_name: "潮聲墜" },
      { slot: "accessory", item_key: "owl_brooch", display_name: "夜鴉胸針" },
    ],
  };
}

export const AccessoryCapEquipment = {
  render: renderDrawer,
  args: { services: SERVICES_PANEL_SAMPLE, character: accessoryCapCharacter() },
};
